"""Player entity — DOM-03.

The FCBQ federation key is `(license_id, dorsal, name)` — a player can change
clubs across seasons but the license_id+name pair is stable, with dorsal
specific to a roster. The composite UNIQUE protects against duplicate
imports while staying compatible with the federation's quirks.
"""

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basketball_stats.models.base import Base


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint(
            "license_id",
            "dorsal_default",
            "normalized_name",
            name="uq_players_license_dorsal_normalized",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    license_id: Mapped[int] = mapped_column(nullable=False)
    dorsal_default: Mapped[int] = mapped_column(nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)

    box_scores: Mapped[list["BoxScore"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="player",
        lazy="raise_on_sql",
    )
    rosters: Mapped[list["Roster"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="player",
        lazy="raise_on_sql",
    )
