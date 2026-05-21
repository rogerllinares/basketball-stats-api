"""Standings RANK window function — STAT-01 + SC1.

seed_minimal places 1 game where the AWAY team wins 84-80. The standings
RANK must report Artés (away) at position 1, Granollers (home) at position 2.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.repositories.standings import fetch_standings


@pytest.mark.asyncio
async def test_standings_rank_two_teams_one_game(seeded_session: AsyncSession) -> None:
    standings = await fetch_standings(seeded_session, competition_id=1)

    assert len(standings) == 2
    assert standings[0]["position"] == 1
    assert standings[1]["position"] == 2
    # First row wins more (or equal); the chain is wins → diff → points_for.
    assert standings[0]["wins"] >= standings[1]["wins"]
    # Sanity: total wins across the two teams = number of decided games (1).
    assert standings[0]["wins"] + standings[1]["wins"] == 1
