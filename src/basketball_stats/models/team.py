"""Team entity — DOM-02.

A team belongs to one club and plays in zero-or-more competitions across
seasons. Roster/coach assignments are temporal (rosters, coaching_assignments).
Games reference Team twice (home / away).
"""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basketball_stats.models.base import Base


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        UniqueConstraint("club_id", "normalized_name", name="uq_teams_club_normalized_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)

    club: Mapped["Club"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="teams",
        lazy="raise_on_sql",
    )
    home_games: Mapped[list["Game"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="home_team",
        foreign_keys="Game.home_team_id",
        lazy="raise_on_sql",
    )
    away_games: Mapped[list["Game"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="away_team",
        foreign_keys="Game.away_team_id",
        lazy="raise_on_sql",
    )
    rosters: Mapped[list["Roster"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="team",
        lazy="raise_on_sql",
    )
