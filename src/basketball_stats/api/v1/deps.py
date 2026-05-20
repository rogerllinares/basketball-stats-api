"""API v1 shared dependencies.

Single import surface for v1 routers — established in P1 so P2 routers import from one
place. Currently re-exports :func:`basketball_stats.core.db.get_db` and adds the shared
``PaginationParams`` helper (D2-13).
"""

from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field

from basketball_stats.core.db import get_db

__all__ = ["get_db", "PaginationParams", "PaginationDep"]


class PaginationParams(BaseModel):
    """offset/limit pagination — D2-13. Reusable across all list endpoints.

    ``extra="forbid"`` rejects unknown query-string parameters with 422, surfacing typos
    instead of silently ignoring them (defensive default for a public API).
    """

    model_config = ConfigDict(extra="forbid")

    offset: Annotated[int, Field(ge=0)] = 0
    limit: Annotated[int, Field(ge=1, le=100)] = 20


PaginationDep = Annotated[PaginationParams, Depends()]
