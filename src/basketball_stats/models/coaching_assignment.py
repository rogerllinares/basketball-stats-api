"""Coaching assignment — temporal junction (coach ↔ team ↔ season).

Mirrors `Roster` but for the coaching side. `role` allows distinguishing head
coach from assistant coach (string-typed for flexibility — no ENUM until v2 if
needed).
"""

from datetime import date

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basketball_stats.models.base import Base


class CoachingAssignment(Base):
    __tablename__ = "coaching_assignments"

    coach_id: Mapped[int] = mapped_column(ForeignKey("coaches.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[date] = mapped_column(nullable=False)
    ended_at: Mapped[date | None] = mapped_column(nullable=True)

    coach: Mapped["Coach"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="assignments",
        lazy="raise_on_sql",
    )
