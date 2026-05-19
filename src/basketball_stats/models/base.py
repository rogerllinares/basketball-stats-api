"""Declarative Base.

Entities (Team, Player, Game, BoxScore, League, Coach, ...) land here in Phase 2.

Exists in P1 so Alembic ``env.py`` can target ``Base.metadata`` even with zero subclasses
(D-07). The migration pipeline is validated against an empty schema (D-08: CI round-trips
``upgrade head -> downgrade base -> upgrade head``) before P2 adds the first real entities
under deadline pressure.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative Base for all SQLAlchemy 2.0 models."""

    pass
