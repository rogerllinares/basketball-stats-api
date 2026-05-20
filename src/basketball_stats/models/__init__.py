"""SQLAlchemy declarative models — Phase 2 entities.

Importing this module loads all entity classes onto ``Base.metadata`` so that
``alembic env.py`` (which targets ``Base.metadata``) and the test harness see
the full schema regardless of which model files have been imported elsewhere.
"""

from basketball_stats.models.base import Base
from basketball_stats.models.box_score import BoxScore
from basketball_stats.models.club import Club
from basketball_stats.models.coach import Coach
from basketball_stats.models.coaching_assignment import CoachingAssignment
from basketball_stats.models.competition import Competition, CompetitionPhase
from basketball_stats.models.game import Game
from basketball_stats.models.player import Player
from basketball_stats.models.roster import Roster
from basketball_stats.models.season import Season
from basketball_stats.models.team import Team

__all__ = [
    "Base",
    "BoxScore",
    "Club",
    "Coach",
    "CoachingAssignment",
    "Competition",
    "CompetitionPhase",
    "Game",
    "Player",
    "Roster",
    "Season",
    "Team",
]
