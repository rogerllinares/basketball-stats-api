"""Standings repository.

Showcase: PostgreSQL window function ``RANK() OVER (PARTITION BY ... ORDER BY ...)``
visible at the SQL of this query. Implements STAT-01 + SC1.

Defense for interview: "wins, points_for and points_against are derived on-the-fly
from the games table via a UNION ALL — no materialised standings table — because
amateur scale (~30 games per season) is sub-100ms. The RANK() with tie-breakers
(wins DESC, point-diff DESC, points-for DESC) is FEB-standard; ADR-0004 documents
the gap vs the FCBQ head-to-head rule and the upgrade path to v2."
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

STANDINGS_SQL = text("""
WITH per_team AS (
    -- Each game contributes one row per team (home + away via UNION ALL).
    SELECT
        home_team_id AS team_id,
        competition_id,
        CASE WHEN total_home > total_away THEN 1 ELSE 0 END AS win,
        total_home AS points_for,
        total_away AS points_against
    FROM games
    WHERE competition_id = :competition_id
    UNION ALL
    SELECT
        away_team_id AS team_id,
        competition_id,
        CASE WHEN total_away > total_home THEN 1 ELSE 0 END AS win,
        total_away AS points_for,
        total_home AS points_against
    FROM games
    WHERE competition_id = :competition_id
),
aggregated AS (
    SELECT
        team_id,
        competition_id,
        COUNT(*) AS played,
        SUM(win) AS wins,
        COUNT(*) - SUM(win) AS losses,
        SUM(points_for) AS points_for,
        SUM(points_against) AS points_against,
        SUM(points_for) - SUM(points_against) AS point_diff
    FROM per_team
    GROUP BY team_id, competition_id
)
SELECT
    a.team_id,
    t.display_name,
    a.played,
    a.wins,
    a.losses,
    a.points_for,
    a.points_against,
    a.point_diff,
    RANK() OVER (
        PARTITION BY a.competition_id
        ORDER BY a.wins DESC, a.point_diff DESC, a.points_for DESC
    ) AS position
FROM aggregated a
JOIN teams t ON t.id = a.team_id
ORDER BY position ASC;
""")


async def fetch_standings(
    session: AsyncSession,
    competition_id: int,
) -> list[dict[str, Any]]:
    """Return one row per team in this competition with computed position."""
    result = await session.execute(STANDINGS_SQL, {"competition_id": competition_id})
    return [dict(row._mapping) for row in result.all()]
