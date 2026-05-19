"""baseline — empty migration to validate the pipeline before P2 adds entities.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-19
"""

from collections.abc import Sequence
from typing import Union

revision: str = "0001_baseline"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op — Phase 1 ships with an empty schema (D-06)."""
    pass


def downgrade() -> None:
    """No-op — pairs with the empty upgrade."""
    pass
