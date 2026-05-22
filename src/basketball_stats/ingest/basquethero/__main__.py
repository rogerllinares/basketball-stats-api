"""argparse CLI for the basquethero ingest pipeline (W4 first ship).

Three subcommands:

    python -m basketball_stats.ingest.basquethero fetch <url-or-path> [--out FILE]
    python -m basketball_stats.ingest.basquethero parse --raw-dir DIR --slug S \
        --season Y --name "N" --gender {M,F} --category C --source-url URL [--out FILE]
    python -m basketball_stats.ingest.basquethero scrape --slug S --season Y \
        --name "N" --gender {M,F} --category C [--raw-dir DIR] [--out FILE]

`scrape` is the end-to-end happy path used by the operator: fetch the league
page, write it under `--raw-dir`, then run `parse_competition` and emit the
fixture JSON to `--out` (default: stdout). State file is created beside the
raw HTML for resumability.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from basketball_stats.ingest.basquethero.client import BasqueteroClient
from basketball_stats.ingest.basquethero.models import FixtureCompetition
from basketball_stats.ingest.basquethero.parser import parse_competition
from basketball_stats.ingest.basquethero.state import ScrapeState


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m basketball_stats.ingest.basquethero",
        description="basquethero.cat ingest CLI (fetch -> parse -> scrape).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_fetch = sub.add_parser("fetch", help="Fetch one URL and write raw bytes.")
    p_fetch.add_argument("target", help="Absolute URL or path relative to base_url.")
    p_fetch.add_argument("--out", type=Path, help="Output file (default: stdout binary).")
    p_fetch.add_argument("--base-url", default="https://www.basquethero.cat")

    for name, help_ in (("parse", "Parse a raw-dir into fixture JSON."),
                       ("scrape", "Fetch + parse end-to-end for one competition slug.")):
        p = sub.add_parser(name, help=help_)
        p.add_argument("--slug", required=True)
        p.add_argument("--season", required=True, help='e.g. "2025-26"')
        p.add_argument("--name", required=True)
        p.add_argument("--gender", choices=("M", "F"), required=True)
        p.add_argument("--category", required=True)
        p.add_argument("--out", type=Path, help="Output fixture JSON file (default: stdout).")
        if name == "parse":
            p.add_argument("--raw-dir", type=Path, required=True)
            p.add_argument("--source-url", required=True)
        else:
            p.add_argument(
                "--raw-dir",
                type=Path,
                default=None,
                help="Where to persist raw HTML (default: data/raw/basquethero/<slug>-<season>).",
            )
            p.add_argument("--base-url", default="https://www.basquethero.cat")

    return parser


def _competition_from_args(args: argparse.Namespace) -> FixtureCompetition:
    return FixtureCompetition(
        slug=args.slug,
        season=args.season,
        name=args.name,
        gender=args.gender,
        category=args.category,
    )


def _cmd_fetch(args: argparse.Namespace) -> int:
    client = BasqueteroClient(base_url=args.base_url)
    body = client.fetch(args.target)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(body)
    else:
        sys.stdout.buffer.write(body)
    return 0


def _cmd_parse(args: argparse.Namespace) -> int:
    competition = _competition_from_args(args)
    fixture = parse_competition(args.raw_dir, competition, args.source_url)
    payload = fixture.model_dump_json(indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")
    return 0


def _cmd_scrape(args: argparse.Namespace) -> int:
    raw_dir: Path = args.raw_dir or Path("data/raw/basquethero") / f"{args.slug}-{args.season}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    state = ScrapeState(raw_dir / ".scrape-state.json")

    league_path = f"/liga/{args.slug}"
    league_url = f"{args.base_url}{league_path}"

    if not state.is_completed(league_path):
        client = BasqueteroClient(base_url=args.base_url)
        try:
            body = client.fetch(league_path)
        except Exception as exc:
            state.mark_failed(league_path, repr(exc))
            raise
        (raw_dir / "liga.html").write_bytes(body)
        state.mark_completed(league_path)

    competition = _competition_from_args(args)
    fixture = parse_competition(raw_dir, competition, league_url)
    payload = fixture.model_dump_json(indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "fetch":
        return _cmd_fetch(args)
    if args.cmd == "parse":
        return _cmd_parse(args)
    if args.cmd == "scrape":
        return _cmd_scrape(args)
    parser.error(f"unknown cmd: {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
