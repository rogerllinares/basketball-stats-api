"""Allow nullable territory/group_no on competitions + COALESCE unique index.

Revision ID: 0004_competitions_nullable_territory_group
Revises: 0003_seasons_unique_start_year
Create Date: 2026-05-23

ADR-0006: nation-level FCBQ competitions (super-copa, cc) legitimately have
no territory and/or no group number. The 0002 baseline modeled these as
NOT NULL based on the divisional examples (1a-territorial-bcn-grup-04),
but the P2.5 ingest parser correctly returns NULL for slugs like
super-copa-m and cc-2a-m-grup-01. This migration aligns the schema with
the real domain.

PostgreSQL treats NULL != NULL in UNIQUE constraints, so the plain
UniqueConstraint from 0002 would allow duplicate nation-level rows. The
replacement uses a COALESCE-wrapped expression unique index so two
super-copa-m rows in the same (season, phase) still collide.

Downgrade path is best-effort: drops the new nullable + COALESCE index
and restores NOT NULL + plain UniqueConstraint. Backfill of NULLs must
be handled out-of-band before downgrade in environments with real data.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_comp_nullable_terr_group"
down_revision = "0003_seasons_unique_start_year"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_competitions_natural_key", "competitions", type_="unique")
    op.alter_column("competitions", "territory", existing_type=sa.String(length=64), nullable=True)
    op.alter_column("competitions", "group_no", existing_type=sa.Integer(), nullable=True)
    op.execute(
        "CREATE UNIQUE INDEX uq_competitions_natural_key ON competitions ("
        "category, gender, COALESCE(territory, ''), COALESCE(group_no, 0), "
        "season_id, phase)"
    )


def downgrade() -> None:
    op.drop_index("uq_competitions_natural_key", table_name="competitions")
    op.alter_column("competitions", "group_no", existing_type=sa.Integer(), nullable=False)
    op.alter_column("competitions", "territory", existing_type=sa.String(length=64), nullable=False)
    op.create_unique_constraint(
        "uq_competitions_natural_key",
        "competitions",
        ["category", "gender", "territory", "group_no", "season_id", "phase"],
    )
