"""Competitions repository — list with filters + single-row fetch.

Showcase: SQLAlchemy 2.0 async `select(...).where(...)` with optional
filter conjunction and a separate `func.count()` for pagination metadata.

Defense for interview: the list endpoint returns `(rows, total_count)` as a
tuple so the router can set the `X-Total-Count` header without re-querying.
The total count is a SELECT COUNT(*) over the same filter — for amateur
scale (~150 competitions per season across all categories) the second
query is sub-10ms and clearer than window-function `COUNT() OVER ()`.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.models import Competition


async def list_competitions(
    session: AsyncSession,
    *,
    category: str | None = None,
    gender: str | None = None,
    territory: str | None = None,
    season_id: int | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Competition], int]:
    """Return paginated list + total row count (filters applied to both)."""
    stmt = select(Competition)
    count_stmt = select(func.count()).select_from(Competition)

    if category is not None:
        stmt = stmt.where(Competition.category == category)
        count_stmt = count_stmt.where(Competition.category == category)
    if gender is not None:
        stmt = stmt.where(Competition.gender == gender)
        count_stmt = count_stmt.where(Competition.gender == gender)
    if territory is not None:
        stmt = stmt.where(Competition.territory == territory)
        count_stmt = count_stmt.where(Competition.territory == territory)
    if season_id is not None:
        stmt = stmt.where(Competition.season_id == season_id)
        count_stmt = count_stmt.where(Competition.season_id == season_id)

    stmt = stmt.order_by(Competition.id).offset(offset).limit(limit)

    rows_result = await session.execute(stmt)
    rows = list(rows_result.scalars().all())

    count_result = await session.execute(count_stmt)
    total = int(count_result.scalar_one())

    return rows, total


async def get_competition(session: AsyncSession, competition_id: int) -> Competition | None:
    """Single-row fetch by id. Returns None if not found (404 in router layer)."""
    stmt = select(Competition).where(Competition.id == competition_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
