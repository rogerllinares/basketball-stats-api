"""Roster entry — temporal junction (player ↔ team ↔ season).

A roster row records that a player belonged to a team during a season, with
their dorsal number (which may differ from the player's `dorsal_default` if
the team needed to reassign). `joined_at` / `left_at` allow mid-season
transfers without losing history.
"""

from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basketball_stats.models.base import Base


class Roster(Base):
    __tablename__ = "rosters"

    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), primary_key=True)
    dorsal_at_season: Mapped[int] = mapped_column(nullable=False)
    joined_at: Mapped[date] = mapped_column(nullable=False)
    left_at: Mapped[date | None] = mapped_column(nullable=True)

    player: Mapped["Player"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="rosters",
        lazy="raise_on_sql",
    )
    team: Mapped["Team"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="rosters",
        lazy="raise_on_sql",
    )
