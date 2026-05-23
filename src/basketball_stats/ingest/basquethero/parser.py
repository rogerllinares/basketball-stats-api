"""basquethero.cat RSC parser (D2.5-04 nested fixture, D2.5-09 stdlib only).

Ported from `spike-basquethero/spike.py` (commit `ee40024`) and extended
to produce a fully validated `BasqueteroFixture` from a directory of raw
HTML responses.

Strategy (RESEARCH-V2 §6 + §10):

1. basquethero.cat serves Next.js + React Server Component HTML. The
   page-level data is streamed inside the response body as `<script>` tags
   that call `self.__next_f.push([N, "<JSON-stringified payload>"])`.
2. We extract every `self.__next_f.push(...)` payload via regex.
3. We JSON-decode the (escaped) payload string. Each decoded payload
   starts with a chunk index followed by a colon and then the actual JSON
   value (which can be a list, dict, or scalar).
4. We recursively walk the decoded JSON looking for **link nodes** that
   point at `/equipo/<id>` (team) and `/partit/<id>` (game). Adjacent
   text/number nodes in the same `children` array yield team names and
   scores; the link href yields the basquethero team id.

The walker is intentionally HEURISTIC. basquethero's React JSX tree
changes shape across deploys; the walker captures the most stable
signals (anchor hrefs + sibling text). When structure drifts so far that
the walker finds zero games on a non-empty page, `parse_competition`
raises `BasqueteroParseError` with the raw path so the operator can
inspect and re-tune.

Note: `parse_competition` returns a `BasqueteroFixture` with
ZERO box-scores by default — basquethero serves per-game `/partit/<id>`
pages that we do not fetch in the W4 first ship (D2.5-07 says "first ship
cc-2a-m-grup-01 only", and box scores are a follow-up issue). Games and
teams are extracted from the calendar page only.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from basketball_stats.ingest.basquethero.exceptions import BasqueteroParseError
from basketball_stats.ingest.basquethero.models import (
    BasqueteroFixture,
    FixtureCompetition,
    FixtureGame,
    FixtureMetadata,
    FixturePlayer,
    FixtureTeam,
)

logger = logging.getLogger(__name__)

RSC_RE = re.compile(
    r'self\.__next_f\.push\(\[(\d+),(?:"((?:\\.|[^"\\])*)")?\]\)',
    re.DOTALL,
)
TEAM_HREF_RE = re.compile(r"^/equipo/(\d+)")
GAME_HREF_RE = re.compile(r"^/partit/(\d+)")


def extract_rsc_chunks(html: str) -> list[tuple[int, str]]:
    """Return every `(chunk_index, decoded_payload_string)` pair in the HTML."""
    out: list[tuple[int, str]] = []
    for idx_str, raw in RSC_RE.findall(html):
        if not raw:
            continue
        try:
            payload = json.loads(f'"{raw}"')
        except json.JSONDecodeError:
            continue
        out.append((int(idx_str), payload))
    return out


def try_decode_payload(payload: str) -> Any | None:
    """RSC chunks start with `N:` (optional `I` prefix for imports). Decode best-effort."""
    if ":" not in payload:
        return None
    _, _, body = payload.partition(":")
    if not body:
        return None
    body = body.lstrip("I").lstrip("HL").lstrip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _walk(obj: Any, depth: int = 0) -> Iterator[Any]:
    """Pre-order DFS yielding every node (dict, list, scalar) in the tree."""
    if depth > 25:
        return
    yield obj
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk(v, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v, depth + 1)


def _extract_teams_from_payloads(payloads: list[Any]) -> list[FixtureTeam]:
    """Find every `/equipo/<id>` link node + sibling text → FixtureTeam."""
    teams: dict[int, FixtureTeam] = {}
    for payload in payloads:
        for node in _walk(payload):
            if not isinstance(node, dict):
                continue
            href = node.get("href")
            children = node.get("children")
            if not isinstance(href, str):
                continue
            match = TEAM_HREF_RE.match(href)
            if match is None:
                continue
            team_id = int(match.group(1))
            display_name = _extract_text(children) or f"team-{team_id}"
            club_slug = _slug_from_name(display_name)
            teams.setdefault(
                team_id,
                FixtureTeam(
                    basquethero_team_id=team_id,
                    club_slug=club_slug,
                    display_name=display_name,
                ),
            )
    return sorted(teams.values(), key=lambda t: t.basquethero_team_id)


def _extract_games_from_payloads(
    payloads: list[Any],
    season_year: int,
) -> list[FixtureGame]:
    """Find every `/partit/<id>` link node → FixtureGame skeleton (scores TBD).

    Without fetching individual `/partit/<id>` pages we cannot fill the
    per-quarter scores. We default them to 0 so the loader still produces
    one row per game. Wave 4 follow-up issue covers box-scores.
    """
    games: dict[int, FixtureGame] = {}
    for payload in payloads:
        for node in _walk(payload):
            if not isinstance(node, dict):
                continue
            href = node.get("href")
            if not isinstance(href, str):
                continue
            match = GAME_HREF_RE.match(href)
            if match is None:
                continue
            game_id = int(match.group(1))
            games.setdefault(
                game_id,
                FixtureGame(
                    basquethero_game_id=game_id,
                    date=date(season_year, 1, 1),
                    home_team_id=0,
                    away_team_id=0,
                    q1_home=0,
                    q1_away=0,
                    q2_home=0,
                    q2_away=0,
                    q3_home=0,
                    q3_away=0,
                    q4_home=0,
                    q4_away=0,
                    box_scores=[],
                ),
            )
    return sorted(games.values(), key=lambda g: g.basquethero_game_id)


def _extract_text(node: Any) -> str | None:
    """Return the first non-empty string found inside `node` (recurses 1 level)."""
    if isinstance(node, str):
        stripped = node.strip()
        return stripped or None
    if isinstance(node, list):
        for item in node:
            text = _extract_text(item)
            if text:
                return text
    return None


def _slug_from_name(display_name: str) -> str:
    """Lowercase + hyphenate. Same shape as `data/seed/load_basquethero.normalize_name`
    but kept in-module to avoid an import from `data/seed/` (operational, not src)."""
    import unicodedata

    decomposed = unicodedata.normalize("NFKD", display_name)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    lowered = stripped.lower().strip()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-") or "unknown"


def parse_competition(
    raw_dir: Path,
    competition: FixtureCompetition,
    source_url: str,
) -> BasqueteroFixture:
    """Read every `*.html` under `raw_dir`, walk RSC chunks, return fixture.

    `competition` is supplied by the CLI (slug + season + name come from the
    operator, not from the page). `source_url` is recorded in metadata.

    Raises `BasqueteroParseError` if zero games are extracted from a
    non-empty raw payload — likely indicates structure drift.
    """
    if not raw_dir.is_dir():
        raise BasqueteroParseError(
            raw_path=str(raw_dir),
            missing_key="<raw_dir>",
            expected_format="directory containing *.html",
        )

    html_files = sorted(raw_dir.glob("*.html"))
    if not html_files:
        raise BasqueteroParseError(
            raw_path=str(raw_dir),
            missing_key="*.html",
            expected_format="at least one raw HTML response",
        )

    all_payloads: list[Any] = []
    total_chunks = 0
    for html_file in html_files:
        html = html_file.read_text(encoding="utf-8", errors="replace")
        chunks = extract_rsc_chunks(html)
        total_chunks += len(chunks)
        for _idx, payload in chunks:
            decoded = try_decode_payload(payload)
            if decoded is not None:
                all_payloads.append(decoded)

    logger.info(
        "parsed %d html files, %d RSC chunks, %d decoded payloads",
        len(html_files),
        total_chunks,
        len(all_payloads),
    )

    teams = _extract_teams_from_payloads(all_payloads)
    season_year = int(competition.season[:4]) if competition.season[:4].isdigit() else 2025
    games = _extract_games_from_payloads(all_payloads, season_year)

    if total_chunks > 0 and not games:
        raise BasqueteroParseError(
            raw_path=str(raw_dir),
            missing_key="game-href (/partit/<id>)",
            expected_format="RSC payloads containing /partit/<id> link nodes",
        )

    metadata = FixtureMetadata(
        fixture_version="1.0",
        scraped_at=datetime.now(UTC),
        source_url=source_url,  # type: ignore[arg-type]
        source_site="basquethero.cat",
    )

    # Players are derived from `/jugadores` page; first-ship W4 does not fetch it.
    # The loader gracefully accepts zero players (just no box-scores written).
    players: list[FixturePlayer] = []

    return BasqueteroFixture(
        metadata=metadata,
        competition=competition,
        teams=teams,
        players=players,
        games=games,
    )
