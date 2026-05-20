"""Games repository — detail with eager box-scores + list by competition.

Showcase: composite index `ix_games_date_competition` accelerates calendar
queries (STAT-05). Detail endpoint uses `selectinload(Game.box_scores)` so
the box-score collection is materialised in a single follow-up IN(...)
query, never per-row.

Defense for interview: `lazy="raise_on_sql"` (P1.2) means any implicit lazy
load raises `MissingGreenlet` at runtime in an async session. This forces
us to declare loads explicitly, so the worst case is "I forgot to eager
load" → fast failure in CI, not "production silently issued 12 queries
per request."
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from basketball_stats.models import Game


async def get_game_with_box_scores(session: AsyncSession, game_id: int) -> Game | None:
    """Full game payload — box-scores eager-loaded."""
    stmt = (
        select(Game)
        .where(Game.id == game_id)
        .options(selectinload(Game.box_scores))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_competition_games(
    session: AsyncSession,
    competition_id: int,
    *,
    matchday_no: int | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Game], int]:
    """Paginated list of games for a competition; optional matchday filter."""
    stmt = select(Game).where(Game.competition_id == competition_id)
    count_stmt = (
        select(func.count()).select_from(Game).where(Game.competition_id == competition_id)
    )

    if matchday_no is not None:
        stmt = stmt.where(Game.matchday_no == matchday_no)
        count_stmt = count_stmt.where(Game.matchday_no == matchday_no)

    stmt = stmt.order_by(Game.game_date.desc()).offset(offset).limit(limit)

    rows_result = await session.execute(stmt)
    rows = list(rows_result.scalars().all())

    count_result = await session.execute(count_stmt)
    total = int(count_result.scalar_one())

    return rows, total
