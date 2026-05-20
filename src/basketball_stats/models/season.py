"""Season entity — DOM-04 (component).

Seasons are immutable once created. `label` is the user-facing form ("2025-26");
`start_year` is the integer for sorting and window-function partitioning.
"""

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from basketball_stats.models.base import Base


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("label", name="uq_seasons_label"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    start_year: Mapped[int] = mapped_column(nullable=False)
    label: Mapped[str] = mapped_column(String(16), nullable=False)
