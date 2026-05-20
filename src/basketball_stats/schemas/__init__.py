"""Pydantic v2 read/create schemas for Phase 2 endpoints.

Re-exports every schema so routers can write::

    from basketball_stats import schemas
    schemas.CompetitionRead.model_validate(orm_obj)
"""

from basketball_stats.schemas.coach import CoachCreate, CoachRead
from basketball_stats.schemas.competition import (
    CompetitionCreate,
    CompetitionRead,
    Phase,
)
from basketball_stats.schemas.game import BoxScoreRead, GameRead, GameSummaryRead
from basketball_stats.schemas.leaderboards import LeaderboardRow, LeaderboardStat
from basketball_stats.schemas.player import PlayerCreate, PlayerRead, PlayerStatsRead
from basketball_stats.schemas.standings import StandingsRow
from basketball_stats.schemas.team import TeamCreate, TeamDetailRead, TeamRead

__all__ = [
    "BoxScoreRead",
    "CoachCreate",
    "CoachRead",
    "CompetitionCreate",
    "CompetitionRead",
    "GameRead",
    "GameSummaryRead",
    "LeaderboardRow",
    "LeaderboardStat",
    "Phase",
    "PlayerCreate",
    "PlayerRead",
    "PlayerStatsRead",
    "StandingsRow",
    "TeamCreate",
    "TeamDetailRead",
    "TeamRead",
]
