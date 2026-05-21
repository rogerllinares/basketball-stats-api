"""Games router — READ-07.

`GET /games/{id}` returns the full GameRead payload including all box-scores for
both teams. The repository uses `selectinload(Game.box_scores)` so the box-score
collection materialises in a single follow-up query (no N+1, no lazy-load
explosion under `lazy="raise_on_sql"`).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.api.v1.deps import get_db
from basketball_stats.repositories import games as games_repo
from basketball_stats.schemas import BoxScoreRead, GameRead

router = APIRouter(prefix="/games", tags=["games"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/{game_id}",
    response_model=GameRead,
    responses={404: {"description": "Game not found"}},
)
async def get_game_detail(game_id: int, session: SessionDep) -> GameRead:
    game = await games_repo.get_game_with_box_scores(session, game_id)
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="game not found")
    return GameRead.model_validate(
        {
            **{c.name: getattr(game, c.name) for c in game.__table__.columns},
            "box_scores": [BoxScoreRead.model_validate(bs) for bs in game.box_scores],
        }
    )
