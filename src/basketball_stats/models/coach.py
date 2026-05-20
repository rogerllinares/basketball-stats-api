"""Coach entity — DOM-07.

A coach can be assigned to multiple teams across seasons (via
coaching_assignments). license_id is optional because not every coach in the
seed dataset has a federation license recorded.
"""

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basketball_stats.models.base import Base


class Coach(Base):
    __tablename__ = "coaches"
    __table_args__ = (
        UniqueConstraint("license_id", "normalized_name", name="uq_coaches_license_normalized"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    license_id: Mapped[int | None] = mapped_column(nullable=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(120), nullable=False)

    assignments: Mapped[list["CoachingAssignment"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="coach",
        lazy="raise_on_sql",
    )
