"""Players repository — slug lookup + season stats + game log.

Showcase: the slug URL pattern `/players/{license_id}-{dorsal}-{slug}` maps
directly to the composite UNIQUE `(license_id, dorsal_default, normalized_name)`,
so a single equality query resolves a public URL to a player.

Defense for interview: aggregating season stats with `AVG(...)` in a single
SQL statement is cheaper than fetching all rows and computing in Python —
the database can use the `ix_box_scores_player_lookup` index and stream the
result without materialising the full set. The query is paginated only on
the game-log path, never on the season-stats path (the latter returns one
row by definition).
"""

from datetime import date

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.models import BoxScore, Game, Player
from basketball_stats.schemas import PlayerStatsRead


async def get_player(session: AsyncSession, player_id: int) -> Player | None:
    stmt = select(Player).where(Player.id == player_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_player_by_slug(
    session: AsyncSession,
    license_id: int,
    dorsal: int,
    slug: str,
) -> Player | None:
    """Resolve the public URL `/players/{license_id}-{dorsal}-{slug}`.

    `slug` is the already-normalized name; the input is the URL segment, which the
    router validates with `normalize_name()` before passing here.
    """
    stmt = select(Player).where(
        Player.license_id == license_id,
        Player.dorsal_default == dorsal,
        Player.normalized_name == slug,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_player_season_stats(
    session: AsyncSession,
    player_id: int,
    season_id: int,
) -> PlayerStatsRead | None:
    """Aggregated season stats for one player. Returns None if no box-scores."""
    stmt = (
        select(
            func.count().label("games_played"),
            func.sum(BoxScore.pts).label("pts_total"),
            func.avg(BoxScore.pts).label("pts_avg"),
            func.sum(BoxScore.reb).label("reb_total"),
            func.avg(BoxScore.reb).label("reb_avg"),
            func.avg(BoxScore.ast).label("ast_avg"),
            func.avg(BoxScore.val).label("val_avg"),
        )
        .select_from(BoxScore)
        .join(Game, Game.id == BoxScore.game_id)
        .where(BoxScore.player_id == player_id)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None or row.games_played == 0:
        return None
    return PlayerStatsRead(
        player_id=player_id,
        season_id=season_id,
        games_played=int(row.games_played),
        pts_total=int(row.pts_total or 0),
        pts_avg=float(row.pts_avg or 0.0),
        reb_total=int(row.reb_total or 0),
        reb_avg=float(row.reb_avg or 0.0),
        ast_avg=float(row.ast_avg or 0.0),
        val_avg=float(row.val_avg or 0.0),
    )


async def get_player_game_log(
    session: AsyncSession,
    player_id: int,
    limit: int = 10,
) -> list[BoxScore]:
    """Most recent box-scores for a player, ordered by game date DESC."""
    stmt = (
        select(BoxScore)
        .join(Game, Game.id == BoxScore.game_id)
        .where(BoxScore.player_id == player_id, Game.game_date <= date.today())
        .order_by(desc(Game.game_date))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
