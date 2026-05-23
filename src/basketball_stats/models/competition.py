"""Competition entity — DOM-04.

Models the FCBQ tuple (category, gender, territory, group_no, season, phase) as
a single row. Phase is an ENUM (D2-05). Each (cat,gender,territory,group,season,
phase) tuple becomes a distinct competition_id — leaderboards/standings
naturally partition by competition_id without further filters.
"""

from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basketball_stats.models.base import Base


class CompetitionPhase(StrEnum):
    """Phases that map to the FCBQ regulation (D2-05)."""

    FASE_PREVIA = "fase_previa"
    SEGONA_FASE = "segona_fase"
    PLAYOFF = "playoff"


class Competition(Base):
    __tablename__ = "competitions"
    __table_args__ = (
        # COALESCE-wrapped unique index: territory/group_no are legitimately
        # NULL for nation-level slugs (super-copa, cc) — see ADR-0006.
        # PostgreSQL treats NULL != NULL in plain UniqueConstraint, so two
        # NULL rows would dedupe-bypass. COALESCE inside the index expression
        # collapses NULL to a sentinel so uniqueness holds for those rows too.
        Index(
            "uq_competitions_natural_key",
            "category",
            "gender",
            text("COALESCE(territory, '')"),
            text("COALESCE(group_no, 0)"),
            "season_id",
            "phase",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    gender: Mapped[str] = mapped_column(String(16), nullable=False)
    territory: Mapped[str | None] = mapped_column(String(64), nullable=True)
    group_no: Mapped[int | None] = mapped_column(nullable=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
    phase: Mapped[CompetitionPhase] = mapped_column(
        Enum(
            CompetitionPhase,
            name="competition_phase",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    games: Mapped[list["Game"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="competition",
        lazy="raise_on_sql",
    )
