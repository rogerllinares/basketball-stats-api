"""W3 follow-up: add UNIQUE(competition_id, matchday_no) on games.

Revision ID: 0005_games_uq_matchday
Revises: 0004_comp_nullable_terr_group
Create Date: 2026-05-23

Context
-------
W3 loader's game UPSERT targets ``(competition_id, matchday_no)`` but
Phase 2 schema (0002_core_entities) shipped the Game table with no UNIQUE
constraint at all. Postgres requires a UNIQUE (or unique index) at the
ON CONFLICT target — without it asyncpg raises
``InvalidColumnReferenceError: there is no unique or exclusion constraint
matching the ON CONFLICT specification``.

The loader stores ``basquethero_game_id`` in ``matchday_no`` (semantic
mismatch tracked separately), so values are unique per game in practice,
making this constraint hold for current ingest. A future refactor that
moves the basquethero id to its own column will revisit the natural key.
"""

import sqlalchemy as sa  # noqa: F401  (kept for symmetry with sibling revisions)
from alembic import op

revision = "0005_games_uq_matchday"
down_revision = "0004_comp_nullable_terr_group"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_games_competition_matchday",
        "games",
        ["competition_id", "matchday_no"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_games_competition_matchday", "games", type_="unique")
