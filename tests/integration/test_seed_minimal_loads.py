"""Smoke test — seed_minimal populates expected row counts."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.models import (
    BoxScore,
    Club,
    Coach,
    CoachingAssignment,
    Competition,
    Game,
    Player,
    Roster,
    Season,
    Team,
)


@pytest.mark.asyncio
async def test_seed_minimal_loads(seeded_session: AsyncSession) -> None:
    """After seeded_session: all entity counts match the locked fixture."""
    expected = {
        Season: 1,
        Club: 2,
        Competition: 1,
        Team: 2,
        Player: 12,
        Roster: 12,
        Coach: 1,
        CoachingAssignment: 2,
        Game: 1,
        BoxScore: 24,
    }
    for model, count in expected.items():
        result = await seeded_session.execute(select(func.count()).select_from(model))
        assert int(result.scalar_one()) == count, f"{model.__name__} row count mismatch"
