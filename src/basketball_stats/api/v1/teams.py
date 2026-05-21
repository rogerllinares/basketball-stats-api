"""Teams router — READ-04.

`GET /teams/{id}` returns the full TeamDetailRead payload — roster for the current
season + recent + upcoming games. The roster's season is implicit (latest season in
DB). At P2 the seed has one season, so the resolution is deterministic; at P3+ when
multiple seasons coexist, the router will accept a `?season_id=` query param.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.api.v1.deps import get_db
from basketball_stats.models import Season
from basketball_stats.repositories import teams as teams_repo
from basketball_stats.schemas import (
    GameSummaryRead,
    PlayerRead,
    TeamDetailRead,
)

router = APIRouter(prefix="/teams", tags=["teams"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/{team_id}",
    response_model=TeamDetailRead,
    responses={404: {"description": "Team not found"}},
)
async def get_team_detail(team_id: int, session: SessionDep) -> TeamDetailRead:
    team = await teams_repo.get_team(session, team_id)
    if team is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="team not found")

    # Resolve current season — latest by start_year.
    season_stmt = select(Season).order_by(Season.start_year.desc()).limit(1)
    season_result = await session.execute(season_stmt)
    season = season_result.scalar_one_or_none()
    season_id = season.id if season is not None else 0

    roster_pairs = await teams_repo.get_team_roster(session, team_id, season_id)
    recent = await teams_repo.get_team_recent_games(session, team_id)
    upcoming = await teams_repo.get_team_upcoming_games(session, team_id)

    return TeamDetailRead(
        id=team.id,
        club_id=team.club_id,
        display_name=team.display_name,
        normalized_name=team.normalized_name,
        roster_current=[PlayerRead.model_validate(p) for p, _ in roster_pairs],
        recent_games=[GameSummaryRead.model_validate(g) for g in recent],
        upcoming_games=[GameSummaryRead.model_validate(g) for g in upcoming],
    )
