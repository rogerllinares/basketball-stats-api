"""Players router — READ-05 + READ-06 + slug URL pattern.

Two lookup paths:

- ``GET /players/{license_dorsal_slug}`` — public, e.g. ``/players/99001-5-marc-soler``.
  Parses the segment with a strict regex and falls through to
  :func:`get_player_by_slug`. Pattern mismatch → 422 (not 404) because the URL
  itself is malformed.
- ``GET /players/by-id/{player_id}`` — admin/internal, integer fallback.

Splitting them avoids the trap of a regex path collision in FastAPI when a single
parameter accepts both ``int`` and the slug pattern.
"""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.api.v1.deps import get_db
from basketball_stats.repositories import players as players_repo
from basketball_stats.schemas import BoxScoreRead, PlayerRead, PlayerStatsRead

router = APIRouter(prefix="/players", tags=["players"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]

SLUG_PATTERN = re.compile(r"^(\d+)-(\d+)-([a-z0-9-]+)$")


@router.get(
    "/by-id/{player_id}",
    response_model=PlayerRead,
    responses={404: {"description": "Player not found"}},
)
async def get_player_by_id(player_id: int, session: SessionDep) -> PlayerRead:
    player = await players_repo.get_player(session, player_id)
    if player is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="player not found")
    return PlayerRead.model_validate(player)


@router.get(
    "/by-id/{player_id}/stats",
    response_model=PlayerStatsRead,
    responses={404: {"description": "Player has no box-scores for this season"}},
)
async def get_player_stats(
    player_id: int,
    session: SessionDep,
    season_id: int = 1,
) -> PlayerStatsRead:
    stats = await players_repo.get_player_season_stats(session, player_id, season_id)
    if stats is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="no box-scores for player+season")
    return stats


@router.get(
    "/by-id/{player_id}/games",
    response_model=list[BoxScoreRead],
    summary="Player game log",
    description="Most recent box-scores for a player.",
)
async def get_player_games(
    player_id: int,
    session: SessionDep,
    limit: int = 10,
) -> list[BoxScoreRead]:
    rows = await players_repo.get_player_game_log(session, player_id, limit=limit)
    return [BoxScoreRead.model_validate(row) for row in rows]


@router.get(
    "/{license_dorsal_slug}",
    response_model=PlayerRead,
    responses={
        404: {"description": "Player not found"},
        422: {"description": "Malformed slug — expected {license_id}-{dorsal}-{slug}"},
    },
)
async def get_player_by_slug(
    license_dorsal_slug: str,
    session: SessionDep,
) -> PlayerRead:
    match = SLUG_PATTERN.match(license_dorsal_slug)
    if match is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="expected {license_id}-{dorsal}-{slug}",
        )
    license_id, dorsal, slug = int(match.group(1)), int(match.group(2)), match.group(3)
    player = await players_repo.get_player_by_slug(session, license_id, dorsal, slug)
    if player is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="player not found")
    return PlayerRead.model_validate(player)
