"""Club entity — DOM-01.

A club groups multiple teams (e.g. CB Sabadell with sènior + sub-22 + junior).
The `normalized_name` is the deduplication key produced by `normalize_name()`
(NFD + filter-Mn + ç→c) — see D2-02 / D2-03.

Showcase: club is the top of the org hierarchy and unique by normalized_name.
"""

from datetime import datetime

from sqlalchemy import String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basketball_stats.models.base import Base


class Club(Base):
    __tablename__ = "clubs"
    __table_args__ = (UniqueConstraint("normalized_name", name="uq_clubs_normalized_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )

    teams: Mapped[list["Team"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="club",
        lazy="raise_on_sql",
    )
