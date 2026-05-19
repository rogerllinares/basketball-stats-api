"""API v1 shared dependencies.

Single import surface for v1 routers — established in P1 so P2 routers import from one
place. Currently re-exports :func:`basketball_stats.core.db.get_db`.
"""

from basketball_stats.core.db import get_db

__all__ = ["get_db"]
