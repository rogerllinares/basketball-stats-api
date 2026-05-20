"""Game / Match entity — DOM-05.

Per-quarter score columns mirror the FCBQ acta format (Q1-Q4 + total).
Two FK to Team for home/away — SQLAlchemy needs `foreign_keys=` on the
relationship sides to disambiguate the two FKs.

Score columns default to 0 to make INSERT order ergonomic; a real game writes
all 10 score columns at once.
"""

from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basketball_stats.models.base import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    matchday_no: Mapped[int] = mapped_column(nullable=False)
    game_date: Mapped[date] = mapped_column(nullable=False)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)

    q1_home: Mapped[int] = mapped_column(nullable=False, default=0)
    q1_away: Mapped[int] = mapped_column(nullable=False, default=0)
    q2_home: Mapped[int] = mapped_column(nullable=False, default=0)
    q2_away: Mapped[int] = mapped_column(nullable=False, default=0)
    q3_home: Mapped[int] = mapped_column(nullable=False, default=0)
    q3_away: Mapped[int] = mapped_column(nullable=False, default=0)
    q4_home: Mapped[int] = mapped_column(nullable=False, default=0)
    q4_away: Mapped[int] = mapped_column(nullable=False, default=0)
    total_home: Mapped[int] = mapped_column(nullable=False, default=0)
    total_away: Mapped[int] = mapped_column(nullable=False, default=0)

    competition: Mapped["Competition"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="games",
        lazy="raise_on_sql",
    )
    home_team: Mapped["Team"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="home_games",
        foreign_keys=[home_team_id],
        lazy="raise_on_sql",
    )
    away_team: Mapped["Team"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="away_games",
        foreign_keys=[away_team_id],
        lazy="raise_on_sql",
    )
    box_scores: Mapped[list["BoxScore"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="game",
        lazy="raise_on_sql",
    )
