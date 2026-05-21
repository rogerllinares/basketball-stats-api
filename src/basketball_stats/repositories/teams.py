"""Teams repository — single team + roster + recent/upcoming games.

Showcase: explicit eager-loading via `selectinload(...)` avoids the N+1
trap that `lazy="raise_on_sql"` (P1.2) intentionally bans at runtime. The
repository declares which collections it will read; nothing else loads.

Defense for interview: `get_team_roster` joins `rosters` ↔ `players` and
returns `(Player, dorsal_at_season)` pairs because the dorsal can differ
between seasons — a player's `dorsal_default` is metadata, the actual
roster row is source of truth. `selectinload` issues a second IN(...)
query, never a per-row SELECT.
"""

from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.models import Game, Player, Roster, Team


async def get_team(session: AsyncSession, team_id: int) -> Team | None:
    stmt = select(Team).where(Team.id == team_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_team_roster(
    session: AsyncSession,
    team_id: int,
    season_id: int,
) -> list[tuple[Player, int]]:
    """Return (Player, dorsal_at_season) tuples for the team's roster in this season."""
    stmt = (
        select(Player, Roster.dorsal_at_season)
        .join(Roster, Roster.player_id == Player.id)
        .where(Roster.team_id == team_id, Roster.season_id == season_id)
        .order_by(Roster.dorsal_at_season)
    )
    result = await session.execute(stmt)
    return [(player, dorsal) for player, dorsal in result.all()]


async def get_team_recent_games(
    session: AsyncSession,
    team_id: int,
    limit: int = 5,
) -> list[Game]:
    """Most recent games where the team played (home or away)."""
    today = date.today()
    stmt = (
        select(Game)
        .where(
            (Game.home_team_id == team_id) | (Game.away_team_id == team_id),
            Game.game_date <= today,
        )
        .order_by(desc(Game.game_date))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_team_upcoming_games(
    session: AsyncSession,
    team_id: int,
    limit: int = 5,
) -> list[Game]:
    """Upcoming games — empty at P2 (no future-dated games in seed)."""
    today = date.today()
    stmt = (
        select(Game)
        .where(
            (Game.home_team_id == team_id) | (Game.away_team_id == team_id),
            Game.game_date > today,
        )
        .order_by(Game.game_date)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
