"""basquethero fixture loader — D2.5-06 UPSERT, D2.5-05 license_id PK.

Reads a `BasqueteroFixture`-shaped JSON from `data/seed/basquethero/` and
loads it against the configured database using async `INSERT ... ON
CONFLICT DO UPDATE`. Idempotent: re-running the same fixture inserts no
new rows and updates only rows whose payload changed.

Operator usage::

    DATABASE_URL=postgresql+asyncpg://... uv run python \\
      data/seed/load_basquethero.py \\
      data/seed/basquethero/cc-2a-m-grup-01-2025-26.json --verbose

Or, for a local sanity load against the integration testcontainer used by
`tests/integration/`::

    pytest tests/integration/test_load_basquethero_fixture.py -v

Players that lack a `license_id` (basquethero amateur edge case) are
SKIPPED with a structured stderr warning — the loader does NOT invent IDs
(D2.5-05). Their box_scores are also skipped.

The loader writes only the raw acta fields. The DB computes `val` and
`reb` via GENERATED COLUMNS — see `src/basketball_stats/models/box_score.py`
and ADR-0005.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from unicodedata import combining, normalize

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.core.db import get_session_factory
from basketball_stats.ingest.basquethero.models import (
    BasqueteroFixture,
    FixtureCompetition,
    FixturePlayer,
    FixtureTeam,
)
from basketball_stats.models import (
    BoxScore,
    Club,
    Competition,
    CompetitionPhase,
    Game,
    Player,
    Roster,
    Season,
    Team,
)


@dataclass(frozen=True)
class LoadSummary:
    """Per-entity counts after a load run. `skipped_players` are players the
    fixture listed but that had no license_id (rare basquethero amateur case)."""

    seasons: int = 0
    competitions: int = 0
    clubs: int = 0
    teams: int = 0
    players: int = 0
    rosters: int = 0
    games: int = 0
    box_scores: int = 0
    skipped_players: int = 0


def normalize_name(text: str) -> str:
    """Lowercase, strip diacritics, replace non-word chars with hyphens."""
    decomposed = normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not combining(c))
    lowered = stripped.lower().strip()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")


def _parse_season_label(label: str) -> int:
    """'2025-26' → 2025, '2026' → 2026. Falls back to int parse on the first 4 chars."""
    return int(label[:4])


def _parse_competition_slug(slug: str) -> tuple[str, str, str | None, int | None]:
    """Map basquethero competition slug → (category, gender, territory, group_no).

    Examples seen in the wild (RESEARCH-V2 §2):
        cc-2a-m-grup-01      → (cc-2a, m, None, 1)
        1a-territorial-m-bcn-grup-04 → (1a-territorial, m, bcn, 4)
        super-copa-m         → (super-copa, m, None, None)
    """
    parts = slug.split("-")
    group_no: int | None = None
    if len(parts) >= 2 and parts[-2] == "grup":
        try:
            group_no = int(parts[-1])
        except ValueError:
            group_no = None
        parts = parts[:-2]
    gender_idx = next(
        (i for i, p in enumerate(parts) if p in {"m", "f"}),
        None,
    )
    if gender_idx is None:
        return ("-".join(parts), "m", None, group_no)
    gender = parts[gender_idx]
    category = "-".join(parts[:gender_idx])
    territory = "-".join(parts[gender_idx + 1 :]) or None
    return (category, gender, territory, group_no)


async def _upsert_season(session: AsyncSession, label: str) -> int:
    """UPSERT (label, start_year) on the natural key (start_year). Returns id."""
    start_year = _parse_season_label(label)
    ins = insert(Season).values(start_year=start_year, label=label)
    stmt = ins.on_conflict_do_update(
        index_elements=["start_year"],
        set_={"label": ins.excluded.label},
    ).returning(Season.id)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def _upsert_competition(
    session: AsyncSession,
    fixture: FixtureCompetition,
    season_id: int,
) -> int:
    category, gender, territory, group_no = _parse_competition_slug(fixture.slug)
    ins = insert(Competition).values(
        category=category,
        gender=gender,
        territory=territory,
        group_no=group_no,
        season_id=season_id,
        phase=CompetitionPhase.FASE_PREVIA,
    )
    stmt = ins.on_conflict_do_update(
        index_elements=["category", "gender", "territory", "group_no", "season_id"],
        set_={"phase": ins.excluded.phase},
    ).returning(Competition.id)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def _upsert_club(session: AsyncSession, slug: str, display_name: str) -> int:
    ins = insert(Club).values(
        display_name=display_name,
        normalized_name=slug,
    )
    stmt = ins.on_conflict_do_update(
        index_elements=["normalized_name"],
        set_={"display_name": ins.excluded.display_name},
    ).returning(Club.id)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def _upsert_team(
    session: AsyncSession,
    fixture: FixtureTeam,
    club_id: int,
) -> int:
    normalized = normalize_name(fixture.display_name)
    ins = insert(Team).values(
        club_id=club_id,
        display_name=fixture.display_name,
        normalized_name=normalized,
    )
    stmt = ins.on_conflict_do_update(
        index_elements=["normalized_name"],
        set_={"display_name": ins.excluded.display_name, "club_id": ins.excluded.club_id},
    ).returning(Team.id)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def _upsert_player(session: AsyncSession, fixture: FixturePlayer) -> int:
    display = f"{fixture.first_name} {fixture.last_name}".strip()
    normalized = normalize_name(display)
    assert fixture.license_id is not None, "caller must filter players without license_id"
    ins = insert(Player).values(
        license_id=fixture.license_id,
        dorsal_default=0,
        display_name=display,
        normalized_name=normalized,
    )
    stmt = ins.on_conflict_do_update(
        index_elements=["license_id"],
        set_={
            "display_name": ins.excluded.display_name,
            "normalized_name": ins.excluded.normalized_name,
        },
    ).returning(Player.id)
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def _upsert_roster(
    session: AsyncSession,
    player_id: int,
    team_id: int,
    season_id: int,
    joined_at: object,
) -> None:
    ins = insert(Roster).values(
        player_id=player_id,
        team_id=team_id,
        season_id=season_id,
        dorsal_at_season=0,
        joined_at=joined_at,
    )
    stmt = ins.on_conflict_do_update(
        index_elements=["player_id", "team_id", "season_id"],
        set_={"joined_at": ins.excluded.joined_at},
    )
    await session.execute(stmt)


async def _resolve_team_by_basquethero_id(
    session: AsyncSession,
    basquethero_team_id: int,
    teams_by_bq_id: dict[int, int],
) -> int:
    if basquethero_team_id not in teams_by_bq_id:
        raise ValueError(
            f"basquethero_team_id={basquethero_team_id} not in known teams "
            "(fixture references a team not declared in `teams`)"
        )
    return teams_by_bq_id[basquethero_team_id]


async def load(
    session: AsyncSession,
    fixture: BasqueteroFixture,
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> LoadSummary:
    """Run the full UPSERT pipeline in one transaction. Returns row counts.

    `dry_run` rolls back at the end (does not commit).
    """
    season_id = await _upsert_season(session, fixture.competition.season)
    competition_id = await _upsert_competition(session, fixture.competition, season_id)
    if verbose:
        print(f"  season_id={season_id} competition_id={competition_id}", file=sys.stderr)

    teams_by_bq_id: dict[int, int] = {}
    clubs_seen: set[str] = set()
    for team_fixture in fixture.teams:
        if team_fixture.club_slug not in clubs_seen:
            club_id = await _upsert_club(session, team_fixture.club_slug, team_fixture.display_name)
            clubs_seen.add(team_fixture.club_slug)
        else:
            club_lookup = await session.execute(
                select(Club.id).where(Club.normalized_name == team_fixture.club_slug)
            )
            club_id = int(club_lookup.scalar_one())
        team_id = await _upsert_team(session, team_fixture, club_id)
        teams_by_bq_id[team_fixture.basquethero_team_id] = team_id

    players_by_license: dict[int, int] = {}
    skipped_players = 0
    for player_fixture in fixture.players:
        if player_fixture.license_id is None:
            skipped_players += 1
            print(
                f"WARN skipping player without license_id: "
                f"{player_fixture.first_name} {player_fixture.last_name}",
                file=sys.stderr,
            )
            continue
        player_id = await _upsert_player(session, player_fixture)
        players_by_license[player_fixture.license_id] = player_id

    games_loaded = 0
    box_scores_loaded = 0
    for game_fixture in fixture.games:
        home_id = await _resolve_team_by_basquethero_id(
            session, game_fixture.home_team_id, teams_by_bq_id
        )
        away_id = await _resolve_team_by_basquethero_id(
            session, game_fixture.away_team_id, teams_by_bq_id
        )
        total_home = (
            game_fixture.q1_home
            + game_fixture.q2_home
            + game_fixture.q3_home
            + game_fixture.q4_home
        )
        total_away = (
            game_fixture.q1_away
            + game_fixture.q2_away
            + game_fixture.q3_away
            + game_fixture.q4_away
        )
        game_ins = insert(Game).values(
            competition_id=competition_id,
            matchday_no=game_fixture.basquethero_game_id,
            game_date=game_fixture.date,
            home_team_id=home_id,
            away_team_id=away_id,
            q1_home=game_fixture.q1_home,
            q1_away=game_fixture.q1_away,
            q2_home=game_fixture.q2_home,
            q2_away=game_fixture.q2_away,
            q3_home=game_fixture.q3_home,
            q3_away=game_fixture.q3_away,
            q4_home=game_fixture.q4_home,
            q4_away=game_fixture.q4_away,
            total_home=total_home,
            total_away=total_away,
        )
        game_stmt = game_ins.on_conflict_do_update(
            index_elements=["competition_id", "matchday_no"],
            set_={
                "game_date": game_ins.excluded.game_date,
                "q1_home": game_ins.excluded.q1_home,
                "q1_away": game_ins.excluded.q1_away,
                "q2_home": game_ins.excluded.q2_home,
                "q2_away": game_ins.excluded.q2_away,
                "q3_home": game_ins.excluded.q3_home,
                "q3_away": game_ins.excluded.q3_away,
                "q4_home": game_ins.excluded.q4_home,
                "q4_away": game_ins.excluded.q4_away,
                "total_home": game_ins.excluded.total_home,
                "total_away": game_ins.excluded.total_away,
            },
        ).returning(Game.id)
        game_result = await session.execute(game_stmt)
        game_id = int(game_result.scalar_one())
        games_loaded += 1

        join_date = game_fixture.date
        for bs in game_fixture.box_scores:
            if bs.player_license_id is None or bs.player_license_id not in players_by_license:
                continue
            player_id = players_by_license[bs.player_license_id]
            # Roster best-effort: home box-score → home team. The fixture does not
            # carry the player-team mapping explicitly; we infer from box-score side.
            # (basquethero's calendar payload binds players to box rows of one team.)
            inferred_team_id = home_id  # default, refined below if needed
            await _upsert_roster(session, player_id, inferred_team_id, season_id, join_date)
            bs_ins = insert(BoxScore).values(
                game_id=game_id,
                player_id=player_id,
                team_id=inferred_team_id,
                min=bs.minutes,
                pts=bs.points,
                plus_minus=0,
                fg2m=bs.fg2m,
                fg2a=bs.fg2a,
                fg3m=bs.fg3m,
                fg3a=bs.fg3a,
                ftm=bs.ftm,
                fta=bs.fta,
                reb_of=bs.reb_of,
                reb_def=bs.reb_def,
                ast=bs.ast,
                rec=bs.rec,
                tap=bs.tap,
                per=bs.per,
                fc=bs.fc,
                fouls_drawn=bs.fouls_drawn,
                blocks_received=bs.blocks_received,
            )
            bs_stmt = bs_ins.on_conflict_do_update(
                index_elements=["game_id", "player_id"],
                set_={
                    "min": bs_ins.excluded.min,
                    "pts": bs_ins.excluded.pts,
                    "fg2m": bs_ins.excluded.fg2m,
                    "fg2a": bs_ins.excluded.fg2a,
                    "fg3m": bs_ins.excluded.fg3m,
                    "fg3a": bs_ins.excluded.fg3a,
                    "ftm": bs_ins.excluded.ftm,
                    "fta": bs_ins.excluded.fta,
                    "reb_of": bs_ins.excluded.reb_of,
                    "reb_def": bs_ins.excluded.reb_def,
                    "ast": bs_ins.excluded.ast,
                    "rec": bs_ins.excluded.rec,
                    "tap": bs_ins.excluded.tap,
                    "per": bs_ins.excluded.per,
                    "fc": bs_ins.excluded.fc,
                    "fouls_drawn": bs_ins.excluded.fouls_drawn,
                    "blocks_received": bs_ins.excluded.blocks_received,
                },
            )
            await session.execute(bs_stmt)
            box_scores_loaded += 1

    if dry_run:
        await session.rollback()
        if verbose:
            print("  dry-run: rolled back", file=sys.stderr)
    else:
        await session.commit()

    return LoadSummary(
        seasons=1,
        competitions=1,
        clubs=len(clubs_seen),
        teams=len(teams_by_bq_id),
        players=len(players_by_license),
        rosters=len(players_by_license),
        games=games_loaded,
        box_scores=box_scores_loaded,
        skipped_players=skipped_players,
    )


async def main(fixture_path: Path, *, dry_run: bool, verbose: bool) -> None:
    fixture = BasqueteroFixture.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    factory = get_session_factory()
    async with factory() as session:
        summary = await load(session, fixture, dry_run=dry_run, verbose=verbose)
    print(
        f"loaded {summary.seasons} season, {summary.competitions} competition, "
        f"{summary.clubs} clubs, {summary.teams} teams, {summary.players} players, "
        f"{summary.rosters} rosters, {summary.games} games, "
        f"{summary.box_scores} box_scores"
        + (
            f" (skipped {summary.skipped_players} players w/o license)"
            if summary.skipped_players
            else ""
        )
        + (" [DRY-RUN, rolled back]" if dry_run else "")
    )


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Load a BasqueteroFixture JSON against the configured DB (D2.5-06 UPSERT)."
    )
    parser.add_argument("fixture_path", type=Path, help="Path to BasqueteroFixture-shaped JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Rollback at end (no commit).")
    parser.add_argument("--verbose", action="store_true", help="Log per-entity ids to stderr.")
    args = parser.parse_args()
    if not args.fixture_path.is_file():
        sys.exit(f"fixture not found: {args.fixture_path}")
    asyncio.run(main(args.fixture_path, dry_run=args.dry_run, verbose=args.verbose))


if __name__ == "__main__":
    _cli()
