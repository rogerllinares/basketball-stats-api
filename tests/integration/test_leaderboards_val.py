"""Leaderboards nested window functions — STAT-02 + SC2.

`fetch_leaderboard` calls AVG() over (PARTITION BY player) then RANK() over
(PARTITION BY competition). With seed_minimal, the 12 home players + 12 away
players generate non-trivial ordering (Marc Soler with pts=18 is the top
scorer; VAL ordering varies with rebounds + assists + fouls_drawn).
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.repositories.leaderboards import (
    ALLOWED_STATS,
    fetch_leaderboard,
)


@pytest.mark.asyncio
async def test_leaderboard_val_ordering(seeded_session: AsyncSession) -> None:
    rows = await fetch_leaderboard(seeded_session, competition_id=1, stat="val", limit=10)
    assert len(rows) <= 10
    assert rows[0]["position"] == 1
    # Window function rule: row 0 has the highest avg_stat in this partition.
    for idx in range(1, len(rows)):
        assert rows[idx - 1]["avg_stat"] >= rows[idx]["avg_stat"]


@pytest.mark.asyncio
async def test_leaderboard_rejects_bad_stat(seeded_session: AsyncSession) -> None:
    with pytest.raises(ValueError):
        await fetch_leaderboard(seeded_session, competition_id=1, stat="invalid-stat")


@pytest.mark.asyncio
async def test_leaderboard_all_allowed_stats_run(seeded_session: AsyncSession) -> None:
    """Every stat name in ALLOWED_STATS should execute without SQL error."""
    for stat in ALLOWED_STATS:
        rows = await fetch_leaderboard(seeded_session, competition_id=1, stat=stat, limit=3)
        assert isinstance(rows, list)
