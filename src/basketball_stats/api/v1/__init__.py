"""API v1 router aggregator.

Health stays at the root (``/healthz``) because the Render health check is wired
to that path — moving it under ``/api/v1`` would break the deploy contract. The
P2 domain endpoints are aggregated under ``/api/v1`` so the versioning prefix is
visible in every URL a client uses.
"""

from fastapi import APIRouter

from basketball_stats.api.v1 import competitions, games, players, teams

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(competitions.router)
api_router.include_router(teams.router)
api_router.include_router(players.router)
api_router.include_router(games.router)

__all__ = ["api_router"]
