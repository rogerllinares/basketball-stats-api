"""Competitions router — READ-01 + READ-02 + READ-03 + READ-08.

D2-15: routers call repositories directly (no service layer at P2).
D2-13: pagination via PaginationDep + X-Total-Count header.
D2-18: response_model on every route.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.api.v1.deps import PaginationDep, get_db
from basketball_stats.repositories import competitions as competitions_repo
from basketball_stats.repositories import games as games_repo
from basketball_stats.repositories import leaderboards as leaderboards_repo
from basketball_stats.repositories import standings as standings_repo
from basketball_stats.schemas import (
    CompetitionRead,
    GameRead,
    LeaderboardRow,
    LeaderboardStat,
    StandingsRow,
)

router = APIRouter(prefix="/competitions", tags=["competitions"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "",
    response_model=list[CompetitionRead],
    summary="List competitions",
    description="Paginated list of competitions. Filters: category, gender, territory, season_id.",
)
async def list_competitions(
    response: Response,
    pagination: PaginationDep,
    session: SessionDep,
    category: str | None = None,
    gender: str | None = None,
    territory: str | None = None,
    season_id: int | None = None,
) -> list[CompetitionRead]:
    rows, total = await competitions_repo.list_competitions(
        session,
        category=category,
        gender=gender,
        territory=territory,
        season_id=season_id,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return [CompetitionRead.model_validate(row) for row in rows]


@router.get(
    "/{competition_id}",
    response_model=CompetitionRead,
    responses={404: {"description": "Competition not found"}},
)
async def get_competition(competition_id: int, session: SessionDep) -> CompetitionRead:
    comp = await competitions_repo.get_competition(session, competition_id)
    if comp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="competition not found")
    return CompetitionRead.model_validate(comp)


@router.get(
    "/{competition_id}/standings",
    response_model=list[StandingsRow],
    summary="Standings (RANK window function)",
    description=(
        "Standings with FEB-style tie-breakers (wins → point_diff → points_for)."
        " STAT-01 + SC1."
    ),
)
async def get_standings(competition_id: int, session: SessionDep) -> list[StandingsRow]:
    rows = await standings_repo.fetch_standings(session, competition_id)
    return [StandingsRow(**row) for row in rows]


@router.get(
    "/{competition_id}/leaderboards",
    response_model=list[LeaderboardRow],
    summary="Leaderboards (nested AVG + RANK window functions)",
    description="Top players by stat. STAT-02 + SC2.",
)
async def get_leaderboards(
    competition_id: int,
    session: SessionDep,
    pagination: PaginationDep,
    stat: LeaderboardStat = "val",
) -> list[LeaderboardRow]:
    rows = await leaderboards_repo.fetch_leaderboard(
        session,
        competition_id,
        stat,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return [LeaderboardRow(**row) for row in rows]


@router.get(
    "/{competition_id}/games",
    response_model=list[GameRead],
    summary="List games in competition",
    description="Paginated games for a competition; optional matchday filter. READ-08.",
)
async def list_competition_games(
    competition_id: int,
    response: Response,
    session: SessionDep,
    pagination: PaginationDep,
    matchday_no: int | None = None,
) -> list[GameRead]:
    rows, total = await games_repo.list_competition_games(
        session,
        competition_id,
        matchday_no=matchday_no,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return [GameRead.model_validate({**row.__dict__, "box_scores": []}) for row in rows]
