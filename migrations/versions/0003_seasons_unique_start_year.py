"""Add UNIQUE constraint on seasons.start_year (P2.5 W3 fix).

Revision ID: 0003_seasons_unique_start_year
Revises: 0002_core_entities
Create Date: 2026-05-23

The basquethero loader (`data/seed/load_basquethero.py`) UPSERTs seasons
ON CONFLICT (start_year), per its docstring "UPSERT on natural key
(start_year)". The 0002 baseline only declared UNIQUE(label), so the
ON CONFLICT clause errored at runtime (issue #40). label and start_year
are 1:1 (label "2025-26" ↔ start_year 2025) so declaring both unique is
consistent and lets either be used as a natural key.
"""

from __future__ import annotations

import sqlalchemy as sa  # noqa: F401  (kept for parity with sibling migrations)
from alembic import op

revision = "0003_seasons_unique_start_year"
down_revision = "0002_core_entities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_seasons_start_year", "seasons", ["start_year"])


def downgrade() -> None:
    op.drop_constraint("uq_seasons_start_year", "seasons", type_="unique")
