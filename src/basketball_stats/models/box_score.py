"""BoxScore — DOM-06.

One row per (game, player). Contains the raw acta fields and two GENERATED
COLUMNS computed by Postgres (D2-07, D2-09, STAT-04, SC3):

- ``reb = reb_of + reb_def``                                                 (D2-09)
- ``val = PIR FIBA literal``                                                 (D2-07)

Defense for interview: GENERATED COLUMN STORED moves the computation into the
storage engine, so every read of ``val`` is O(1) — no application-layer recalc,
no risk of formula drift between writer/reader paths. The index
``ix_box_scores_val_desc`` on the GENERATED column shows that "computed" does
not mean "uncacheable" or "unindexable" — it is a regular column from the
optimizer's perspective.

The val expression references ``(reb_of + reb_def)`` directly instead of
``reb`` because Postgres forbids one generated column from referencing another
in the same row (Postgres 16 DDL rule).
"""

from sqlalchemy import Computed, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from basketball_stats.models.base import Base


class BoxScore(Base):
    __tablename__ = "box_scores"

    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)

    # Raw box-score fields (acta FCBQ — what coach enters).
    min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    plus_minus: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fg2m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fg2a: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fg3m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fg3a: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ftm: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reb_of: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reb_def: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ast: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rec: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tap: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    per: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fc: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fouls_drawn: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocks_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # GENERATED COLUMNS — STORED. `persisted=True` is mandatory (research §1
    # pitfall: Postgres 18 defaults to VIRTUAL otherwise).
    reb: Mapped[int] = mapped_column(
        Integer,
        Computed("reb_of + reb_def", persisted=True),
    )
    val: Mapped[int] = mapped_column(
        Integer,
        Computed(
            "pts + (reb_of + reb_def) + ast + rec + tap + fouls_drawn"
            " - (fg2a - fg2m) - (fg3a - fg3m) - (fta - ftm)"
            " - per - fc - blocks_received",
            persisted=True,
        ),
    )

    # P1.2: every relationship MUST be lazy="raise_on_sql" so an implicit
    # lazy-load in an async session raises immediately instead of dead-locking.
    game: Mapped["Game"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="box_scores",
        lazy="raise_on_sql",
    )
    player: Mapped["Player"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="box_scores",
        lazy="raise_on_sql",
    )
    team: Mapped["Team"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        lazy="raise_on_sql",
    )
