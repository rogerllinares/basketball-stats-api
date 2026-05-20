"""Leaderboards repository.

Showcase: nested PostgreSQL window functions — AVG() over (PARTITION BY player)
to compute season averages on-the-fly, then RANK() over (PARTITION BY competition)
to rank players. Implements STAT-02 + SC2. No materialised table.

Composite index `ix_box_scores_player_lookup` accelerates the inner PARTITION BY at
sub-100ms for amateur scale (~500 players, ~30 games/season).

Defense for interview: the SQL is built via `text(...).format(stat=stat)` because
column names cannot be parameterised. The `ALLOWED_STATS` set is the SQL-injection
guard — any stat not in this allowlist raises ValueError before the query is
constructed. Adding a stat requires changing two places (this allowlist + the
`LeaderboardStat` Literal in schemas/leaderboards.py); intentional friction so a
stat name never reaches the SQL layer without explicit approval.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

LEADERBOARDS_SQL_TEMPLATE = """
WITH per_player AS (
    SELECT DISTINCT
        bs.player_id,
        g.competition_id,
        c.season_id,
        AVG(bs.{stat}::numeric) OVER (
            PARTITION BY bs.player_id, c.season_id
        ) AS avg_stat,
        COUNT(*) OVER (
            PARTITION BY bs.player_id, c.season_id
        ) AS games_played
    FROM box_scores bs
    JOIN games g ON g.id = bs.game_id
    JOIN competitions c ON c.id = g.competition_id
    WHERE g.competition_id = :competition_id
)
SELECT
    pp.player_id,
    p.display_name,
    pp.games_played,
    pp.avg_stat,
    RANK() OVER (
        PARTITION BY pp.competition_id, pp.season_id
        ORDER BY pp.avg_stat DESC
    ) AS position
FROM per_player pp
JOIN players p ON p.id = pp.player_id
ORDER BY position ASC
LIMIT :limit OFFSET :offset;
"""

ALLOWED_STATS = frozenset({"val", "pts", "reb", "ast", "rec", "tap", "plus_minus"})


async def fetch_leaderboard(
    session: AsyncSession,
    competition_id: int,
    stat: str,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Return ranked rows for `stat` in this competition. Raises ValueError if stat not allowed."""
    if stat not in ALLOWED_STATS:
        raise ValueError(f"stat must be one of {sorted(ALLOWED_STATS)}")
    sql = text(LEADERBOARDS_SQL_TEMPLATE.format(stat=stat))
    result = await session.execute(
        sql,
        {"competition_id": competition_id, "limit": limit, "offset": offset},
    )
    return [dict(row._mapping) for row in result.all()]
