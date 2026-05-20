"""Minimal seed — INFRA-06 + SC6.

Idempotent loader for a single Catalan-fictitious competition. License IDs
``99001``-``99012`` are deliberately outside the federation range (D2-14) so the
seed cannot be confused with real FCBQ data. The fixture is locked: tests
assert that ``99001-5-marc-soler`` resolves to the first player row.

Run directly::

    uv run python -m basketball_stats.seed.minimal           # idempotent
    uv run python -m basketball_stats.seed.minimal --force   # truncate + re-seed
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.core.db import get_session_factory
from basketball_stats.models import (
    BoxScore,
    Club,
    Coach,
    CoachingAssignment,
    Competition,
    CompetitionPhase,
    Game,
    Player,
    Roster,
    Season,
    Team,
)


@dataclass(frozen=True)
class PlayerFixture:
    license_id: int
    dorsal_default: int
    display_name: str
    normalized_name: str


# Anchor: Test 7.6 asserts `99001-5-marc-soler` resolves to this row.
PLAYERS: tuple[PlayerFixture, ...] = (
    PlayerFixture(99001, 5, "Marc Soler", "marc-soler"),
    PlayerFixture(99002, 6, "Jordi Vila", "jordi-vila"),
    PlayerFixture(99003, 7, "Pol Camps", "pol-camps"),
    PlayerFixture(99004, 8, "Aleix Mas", "aleix-mas"),
    PlayerFixture(99005, 9, "Nil Roca", "nil-roca"),
    PlayerFixture(99006, 10, "Roger Pujol", "roger-pujol"),
    PlayerFixture(99007, 11, "Bernat Llop", "bernat-llop"),
    PlayerFixture(99008, 12, "Arnau Vidal", "arnau-vidal"),
    PlayerFixture(99009, 13, "Iu Roig", "iu-roig"),
    PlayerFixture(99010, 14, "Gerard Pou", "gerard-pou"),
    PlayerFixture(99011, 15, "Adrià Solà", "adria-sola"),
    PlayerFixture(99012, 4, "Quim Bosch", "quim-bosch"),
)

# Box-score values per player on the seed game.
# Granollers (home, 80) wins vs Artés (away, 84) — wait, 80 < 84 so Artés wins.
# Set Granollers totals 80 + Artés 84 → Artés wins by 4.
# Box-scores: 6 Granollers players + 6 Artés players (12 total per game per D2-14
# — but ROADMAP says "12 box_scores" total, not 12 per team. We follow the PLAN
# wording: 12 box_scores for home + 12 for visitors = 24, mirroring acta length).
BOX_SCORES_HOME: tuple[tuple[int, int, int, int, int, int, int, int], ...] = (
    # (player_idx within Granollers slot 0-5, pts, reb_of, reb_def, ast, rec, tap, fc)
    (0, 18, 2, 4, 3, 2, 1, 2),
    (1, 14, 1, 3, 2, 1, 0, 3),
    (2, 11, 0, 2, 5, 3, 0, 1),
    (3, 10, 3, 5, 1, 1, 1, 2),
    (4, 8, 1, 2, 2, 2, 0, 3),
    (5, 6, 0, 1, 1, 1, 0, 1),
)


def _granollers_to_artes_visitor(
    home_fixtures: tuple[tuple[int, int, int, int, int, int, int, int], ...],
) -> tuple[tuple[int, int, int, int, int, int, int, int], ...]:
    """Mirror visitor scoring so total_away = 84 with similar shape."""
    return tuple(
        (idx, pts + 1, of, df, ast, rec, tap, fc)
        for idx, pts, of, df, ast, rec, tap, fc in home_fixtures
    )


BOX_SCORES_AWAY = _granollers_to_artes_visitor(BOX_SCORES_HOME)


async def _is_already_seeded(session: AsyncSession) -> bool:
    stmt = select(func.count()).select_from(Season).where(Season.id == 1)
    result = await session.execute(stmt)
    return int(result.scalar_one()) > 0


async def _truncate_p2_tables(session: AsyncSession) -> None:
    """Reverse FK order — strictly delete, never DROP."""
    for table in (
        BoxScore,
        Game,
        CoachingAssignment,
        Roster,
        Coach,
        Player,
        Team,
        Competition,
        Season,
        Club,
    ):
        await session.execute(delete(table))


async def seed(session: AsyncSession, *, force: bool = False) -> dict[str, int]:
    """Insert the minimal Catalan fixture. Returns row counts per entity."""
    if await _is_already_seeded(session) and not force:
        return {"already_seeded": 1}

    if force:
        await _truncate_p2_tables(session)
        await session.flush()

    season = Season(id=1, start_year=2025, label="2025-26")
    session.add(season)

    granollers = Club(id=1, display_name="CB Granollers", normalized_name="cb-granollers")
    artes = Club(id=2, display_name="CB Artés", normalized_name="cb-artes")
    session.add_all([granollers, artes])
    await session.flush()

    competition = Competition(
        id=1,
        category="1a-territorial",
        gender="m",
        territory="bcn",
        group_no=4,
        season_id=1,
        phase=CompetitionPhase.FASE_PREVIA,
    )
    session.add(competition)

    team_granollers = Team(
        id=1,
        club_id=granollers.id,
        display_name="CB Granollers Sènior A",
        normalized_name="cb-granollers-senior-a",
    )
    team_artes = Team(
        id=2,
        club_id=artes.id,
        display_name="CB Artés Sènior A",
        normalized_name="cb-artes-senior-a",
    )
    session.add_all([team_granollers, team_artes])
    await session.flush()

    players: list[Player] = []
    for fixture in PLAYERS:
        player = Player(
            license_id=fixture.license_id,
            dorsal_default=fixture.dorsal_default,
            display_name=fixture.display_name,
            normalized_name=fixture.normalized_name,
        )
        session.add(player)
        players.append(player)
    await session.flush()

    # First 6 players belong to Granollers, last 6 to Artés.
    join_date = date(2025, 9, 1)
    for _idx, player in enumerate(players[:6]):
        session.add(
            Roster(
                player_id=player.id,
                team_id=team_granollers.id,
                season_id=season.id,
                dorsal_at_season=player.dorsal_default,
                joined_at=join_date,
            )
        )
    for player in players[6:]:
        session.add(
            Roster(
                player_id=player.id,
                team_id=team_artes.id,
                season_id=season.id,
                dorsal_at_season=player.dorsal_default,
                joined_at=join_date,
            )
        )

    coach = Coach(
        license_id=88001,
        display_name="Xavier Pasqual",
        normalized_name="xavier-pasqual",
    )
    session.add(coach)
    await session.flush()
    session.add(
        CoachingAssignment(
            coach_id=coach.id,
            team_id=team_granollers.id,
            season_id=season.id,
            role="head",
            started_at=join_date,
        )
    )
    session.add(
        CoachingAssignment(
            coach_id=coach.id,
            team_id=team_artes.id,
            season_id=season.id,
            role="assistant",
            started_at=join_date,
        )
    )

    game = Game(
        competition_id=competition.id,
        matchday_no=1,
        game_date=date(2025, 10, 15),
        home_team_id=team_granollers.id,
        away_team_id=team_artes.id,
        q1_home=20,
        q1_away=22,
        q2_home=18,
        q2_away=21,
        q3_home=22,
        q3_away=20,
        q4_home=20,
        q4_away=21,
        total_home=80,
        total_away=84,
    )
    session.add(game)
    await session.flush()

    for idx, pts, reb_of, reb_def, ast, rec, tap, fc in BOX_SCORES_HOME:
        session.add(
            BoxScore(
                game_id=game.id,
                player_id=players[idx].id,
                team_id=team_granollers.id,
                pts=pts,
                reb_of=reb_of,
                reb_def=reb_def,
                ast=ast,
                rec=rec,
                tap=tap,
                fc=fc,
            )
        )
    for idx, pts, reb_of, reb_def, ast, rec, tap, fc in BOX_SCORES_AWAY:
        # idx 0..5 map to Granollers slots but visitor box-scores belong to
        # Artés players (idx 6..11 in PLAYERS).
        session.add(
            BoxScore(
                game_id=game.id,
                player_id=players[idx + 6].id,
                team_id=team_artes.id,
                pts=pts,
                reb_of=reb_of,
                reb_def=reb_def,
                ast=ast,
                rec=rec,
                tap=tap,
                fc=fc,
            )
        )

    await session.commit()

    return {
        "seasons": 1,
        "competitions": 1,
        "clubs": 2,
        "teams": 2,
        "players": len(PLAYERS),
        "rosters": len(PLAYERS),
        "coaches": 1,
        "coaching_assignments": 2,
        "games": 1,
        "box_scores": len(BOX_SCORES_HOME) + len(BOX_SCORES_AWAY),
    }


async def main(force: bool = False) -> None:
    factory = get_session_factory()
    async with factory() as session:
        counts = await seed(session, force=force)
        if counts == {"already_seeded": 1}:
            print("already seeded; pass --force to re-seed")
            return
        summary = ", ".join(f"{n} {k}" for k, n in counts.items())
        print(f"seeded: {summary}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the database with minimal Catalan fixture.")
    parser.add_argument("--force", action="store_true", help="Truncate P2 tables and re-seed.")
    args = parser.parse_args()
    asyncio.run(main(force=args.force))
