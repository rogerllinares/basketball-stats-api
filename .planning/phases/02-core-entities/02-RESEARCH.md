# Phase 2: Core entities + public read — Research

**Researched:** 2026-05-20
**Confidence:** HIGH (post-Phase 1 ship, stack proven in production at https://basketball-stats-api-banq.onrender.com)
**For:** gsd-planner consumption

## TL;DR

- **GENERATED columns work as locked in D2-06.** The val expression literally references `(reb_of + reb_def)` and NOT the `reb` GENERATED column — this is **required** by Postgres 16 (a generated column cannot reference another generated column in the same row). D2-06 already handles this correctly; do not "simplify" the val expression to use `reb` during execution.
- **Both Computed columns MUST pass `persisted=True`** in SQLAlchemy 2.0.49 to render `STORED` in DDL deterministically (Postgres 18 will default to VIRTUAL otherwise; warning emitted on PG ≤17 if omitted).
- **D2-20's composite index `(competition_id, season_id, avg_stat DESC)` is impossible as literally written** — `avg_stat` is computed on-the-fly via window function, NOT a stored column. The actual index is `(competition_id, season_id)` on `box_scores` (covers the PARTITION BY); the `DESC avg_stat` part is informational naming, not SQL. Flagged in §9.
- **Alembic autogenerate does NOT reliably detect `Computed()` expressions** — write `0002_core_entities.py` BY HAND from the model declarations, not via `alembic revision --autogenerate`. Round-trip downgrade drops tables in reverse FK order; no special handling for GENERATED columns (they drop with the table).
- **Relationships MUST declare `lazy="raise_on_sql"` everywhere** + queries use `selectinload(...)`/`joinedload(...)` explicitly. Inherited P1 pitfall P1.2 — non-negotiable for async sessions. Every model relationship + every repository query in P2 follows this.
- **testcontainers infra is ALREADY built in P1** (`tests/integration/conftest.py`): session-scoped `postgres_container`, session-scoped `_run_alembic_upgrade` autouse, function-scoped `db_session`. P2 reuses as-is and adds ONE new fixture: `seed_minimal` (session-scoped) for window-function tests needing 12 box-scores.
- **FastAPI `X-Total-Count` header**: inject via `response: Response` parameter (NOT via headers in Response() constructor — breaks response_model). Verified pattern below.
- **Pydantic v2 examples**: use `model_config = ConfigDict(from_attributes=True, json_schema_extra={"examples": [...]})` at class level. `from_attributes=True` IS required for ORM mapping (v1's `orm_mode`). Multiple examples in the list render as a dropdown in Swagger UI.

---

## 1. SQLAlchemy 2.0 + GENERATED COLUMN STORED

### Computed column declaration (verbatim)

```python
# src/basketball_stats/models/box_score.py
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

    # GENERATED COLUMNS — Postgres 16 STORED. persisted=True is mandatory:
    # SQLAlchemy 2.1+/Postgres 18 default to VIRTUAL otherwise.
    # NOTE: val expression uses (reb_of + reb_def), NOT `reb`. Postgres forbids
    # one generated column from referencing another in the same row.
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

    # Relationships — every collection MUST be lazy="raise_on_sql" (P1.2).
    game: Mapped["Game"] = relationship(back_populates="box_scores", lazy="raise_on_sql")
    player: Mapped["Player"] = relationship(back_populates="box_scores", lazy="raise_on_sql")
    team: Mapped["Team"] = relationship(lazy="raise_on_sql")
```

### Alembic migration (manual, not autogenerate)

```python
# migrations/versions/0002_core_entities.py
"""Phase 2 core entities — 9 tables + 2 GENERATED COLUMNS + composite indexes.

Revision ID: 0002_core_entities
Revises: 0001_baseline
Create Date: 2026-05-XX

NOTE: Written by hand. `alembic revision --autogenerate` does NOT reliably
emit `Computed()` expressions or some Postgres-specific clauses; manual write
guarantees the val/reb expressions match D2-06 verbatim.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_core_entities"
down_revision: str | Sequence[str] | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ... (clubs, seasons, competitions, teams, players, coaches,
    #      rosters, coaching_assignments, games first — FK order) ...

    op.create_table(
        "box_scores",
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("plus_minus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fg2m", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fg2a", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fg3m", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fg3a", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ftm", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fta", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reb_of", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reb_def", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ast", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tap", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("per", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fouls_drawn", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocks_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "reb",
            sa.Integer(),
            sa.Computed("reb_of + reb_def", persisted=True),
        ),
        sa.Column(
            "val",
            sa.Integer(),
            sa.Computed(
                "pts + (reb_of + reb_def) + ast + rec + tap + fouls_drawn"
                " - (fg2a - fg2m) - (fg3a - fg3m) - (fta - ftm)"
                " - per - fc - blocks_received",
                persisted=True,
            ),
        ),
    )

    # Composite index for leaderboards window function PARTITION BY.
    # NOTE: cannot index `val DESC` as an expression on the GENERATED column
    # in a composite — Postgres supports it, but b-tree direction matters only
    # for the inner ORDER BY of the window. Use simple composite that covers
    # PARTITION BY columns; the engine sorts within partitions cheaply.
    op.create_index(
        "ix_box_scores_player_game",
        "box_scores",
        ["player_id", "game_id"],
    )
    op.create_index(
        "ix_games_competition_date",
        "games",
        [sa.text("game_date DESC"), "competition_id"],
    )


def downgrade() -> None:
    # FK order reverse — drop dependent tables first. GENERATED columns
    # drop with the table; no special handling needed.
    op.drop_index("ix_games_competition_date", table_name="games")
    op.drop_index("ix_box_scores_player_game", table_name="box_scores")
    op.drop_table("box_scores")
    op.drop_table("coaching_assignments")
    op.drop_table("rosters")
    op.drop_table("games")
    op.drop_table("coaches")
    op.drop_table("players")
    op.drop_table("teams")
    op.drop_table("competitions")
    op.drop_table("seasons")
    op.drop_table("clubs")
```

### Pitfalls

- **`persisted=True` is MANDATORY.** Without it: deprecation warning on Postgres ≤17, and Postgres 18+ default switches to VIRTUAL (no STORED). Always specify explicitly.
- **GENERATED cannot reference GENERATED in same row** ([Postgres 16 docs](https://www.postgresql.org/docs/16/ddl-generated-columns.html)). The val expression therefore references `(reb_of + reb_def)` directly, not `reb`. D2-06 is correct as written.
- **Alembic autogenerate ignores `Computed()` reliably.** Write `0002_core_entities.py` manually — do not run `alembic revision --autogenerate -m "core entities"` and trust it. The migration is large enough (9 tables + 2 GENERATED + 2 composite indexes) that hand-writing is acceptable.
- **`relationship(lazy="raise_on_sql")`** on every collection AND every scalar — any implicit lazy-load in an async session raises `MissingGreenlet`. Inherited from P1.2; the model authoring convention is hard.
- **`mapped_column(Computed(..., persisted=True))` is type-compatible with `Mapped[int]`** — `val` is `Mapped[int]` and read-only in practice (don't write to it in tests, the database rejects).

### Verification commands

```bash
# After alembic upgrade head, confirm STORED in Postgres metadata:
psql "$DATABASE_URL_DIRECT" -c "\d+ box_scores" | grep -E "generated (always )?as"
# Expected output contains: "generated always as ... stored"

# Confirm round-trip works (P1 D-08 CI gate already wired for this):
alembic upgrade head && alembic downgrade base && alembic upgrade head

# Confirm insert + read derives val correctly:
psql "$DATABASE_URL_DIRECT" -c "
  INSERT INTO box_scores (game_id, player_id, team_id, pts, reb_of, reb_def, ast,
                          rec, tap, fouls_drawn, fg2a, fg2m, fg3a, fg3m, fta, ftm,
                          per, fc, blocks_received)
  VALUES (1, 1, 1, 10, 3, 2, 4, 2, 1, 2, 5, 4, 3, 1, 2, 1, 1, 2, 0)
  RETURNING reb, val;"
# Expected: reb=5, val=10+5+4+2+1+2-1-2-1-1-2-0 = 17
```

---

## 2. Window Functions + Composite Indexes

### Standings query (verbatim — STAT-01 + SC1)

```python
# src/basketball_stats/repositories/standings.py
"""Standings repository.

Showcase: PostgreSQL window function ``RANK() OVER (PARTITION BY ... ORDER BY ...)``
visible at the SQL of this query. Implements STAT-01 + SC1.

Defense for interview: "wins, points_for and points_against are derived on-the-fly
from the games table via a UNION ALL — no materialized standings table — because
amateur scale (~30 games per season) is sub-100ms. The RANK() with tie-breakers
(wins DESC, point-diff DESC, points-for DESC) is FEB-standard; ADR-0004 documents
the gap vs the FCBQ head-to-head rule and the upgrade path to v2."
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

STANDINGS_SQL = text("""
WITH per_team AS (
    -- Each game contributes one row per team (home + away via UNION ALL).
    SELECT
        home_team_id AS team_id,
        competition_id,
        CASE WHEN total_home > total_away THEN 1 ELSE 0 END AS win,
        total_home AS points_for,
        total_away AS points_against
    FROM games
    WHERE competition_id = :competition_id
    UNION ALL
    SELECT
        away_team_id AS team_id,
        competition_id,
        CASE WHEN total_away > total_home THEN 1 ELSE 0 END AS win,
        total_away AS points_for,
        total_home AS points_against
    FROM games
    WHERE competition_id = :competition_id
),
aggregated AS (
    SELECT
        team_id,
        competition_id,
        COUNT(*) AS played,
        SUM(win) AS wins,
        COUNT(*) - SUM(win) AS losses,
        SUM(points_for) AS points_for,
        SUM(points_against) AS points_against,
        SUM(points_for) - SUM(points_against) AS point_diff
    FROM per_team
    GROUP BY team_id, competition_id
)
SELECT
    a.team_id,
    t.display_name,
    a.played,
    a.wins,
    a.losses,
    a.points_for,
    a.points_against,
    a.point_diff,
    RANK() OVER (
        PARTITION BY a.competition_id
        ORDER BY a.wins DESC, a.point_diff DESC, a.points_for DESC
    ) AS position
FROM aggregated a
JOIN teams t ON t.id = a.team_id
ORDER BY position ASC;
""")


async def fetch_standings(session: AsyncSession, competition_id: int) -> list[dict]:
    result = await session.execute(STANDINGS_SQL, {"competition_id": competition_id})
    return [dict(row._mapping) for row in result.all()]
```

### Leaderboards query (verbatim — STAT-02 + SC2)

```python
# src/basketball_stats/repositories/leaderboards.py
"""Leaderboards repository.

Showcase: nested PostgreSQL window functions — AVG() over (PARTITION BY player)
to compute season averages on-the-fly, then RANK() over (PARTITION BY competition)
to rank players. Implements STAT-02 + SC2. No materialized table.

Composite index `(competition_id, season_id)` on box_scores accelerates the inner
PARTITION BY at sub-100ms for amateur scale (~500 players, ~30 games/season).
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

LEADERBOARDS_SQL_TEMPLATE = """
WITH per_player AS (
    SELECT DISTINCT
        bs.player_id,
        g.competition_id,
        c.season_id,
        AVG(bs.{stat}::numeric) OVER (
            PARTITION BY bs.player_id, c.season_id
        ) AS avg_stat,
        COUNT(*) OVER (
            PARTITION BY bs.player_id, c.season_id
        ) AS games_played
    FROM box_scores bs
    JOIN games g ON g.id = bs.game_id
    JOIN competitions c ON c.id = g.competition_id
    WHERE g.competition_id = :competition_id
)
SELECT
    pp.player_id,
    p.display_name,
    pp.games_played,
    pp.avg_stat,
    RANK() OVER (
        PARTITION BY pp.competition_id, pp.season_id
        ORDER BY pp.avg_stat DESC
    ) AS position
FROM per_player pp
JOIN players p ON p.id = pp.player_id
ORDER BY position ASC
LIMIT :limit OFFSET :offset;
"""

ALLOWED_STATS = {"val", "pts", "reb", "ast", "rec", "tap", "plus_minus"}


async def fetch_leaderboard(
    session: AsyncSession,
    competition_id: int,
    stat: str,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    if stat not in ALLOWED_STATS:
        raise ValueError(f"stat must be one of {ALLOWED_STATS}")
    sql = text(LEADERBOARDS_SQL_TEMPLATE.format(stat=stat))
    result = await session.execute(
        sql,
        {"competition_id": competition_id, "limit": limit, "offset": offset},
    )
    return [dict(row._mapping) for row in result.all()]
```

### Composite index DDL

```python
# inside migrations/versions/0002_core_entities.py upgrade():

# Accelerates leaderboards window PARTITION BY (player_id, season_id) when filtered
# by competition_id. Direction (DESC on avg_stat) is irrelevant at the index level
# because the value is computed on-the-fly — Postgres sorts within the partition.
op.create_index(
    "ix_box_scores_player_lookup",
    "box_scores",
    ["player_id"],
)
op.create_index(
    "ix_games_competition_id",
    "games",
    ["competition_id"],
)

# Calendar query (READ-06 + STAT-05): GET /competitions/{id}/games filtered by date.
# DESC on game_date matters: most-recent-first is the default sort.
op.create_index(
    "ix_games_date_competition",
    "games",
    [sa.text("game_date DESC"), "competition_id"],
)
```

### Pitfalls

- **Cannot index `avg_stat DESC` as a column.** It's a window-function output, computed per query. The "DESC" naming in D2-20 is informational; the actual index is on the PARTITION BY columns (`competition_id`, `player_id`/`season_id` via games join). See §9 Open Q1.
- **`text()` with `.format(stat=stat)`** is required because column names cannot be parameterized in SQL. **Always validate `stat` against a hardcoded allowlist** (`ALLOWED_STATS` above) — never accept user input directly. SQL-injection-safe via the whitelist.
- **`text()` SQL bypasses SQLAlchemy mapped types** — the result columns come back as raw rows; the repository materializes to dict (or to a Pydantic model in the router layer). Don't try to `selectinload` on text() results.
- **RANK() vs DENSE_RANK() vs ROW_NUMBER()** — D2-10 uses `RANK()` which gives gaps after ties (1, 1, 3) — correct for sports standings (two teams tied for 1st means next is 3rd). DENSE_RANK gives no gaps (1, 1, 2) — wrong for FEB convention. ROW_NUMBER gives no ties (1, 2, 3) — wrong, ignores actual ties.

### Verification

```bash
# Confirm index used by leaderboards:
psql "$DATABASE_URL_DIRECT" -c "EXPLAIN ANALYZE
  WITH per_player AS (
    SELECT bs.player_id, g.competition_id,
           AVG(bs.val::numeric) OVER (PARTITION BY bs.player_id) AS avg_stat
    FROM box_scores bs JOIN games g ON g.id = bs.game_id
    WHERE g.competition_id = 1
  ) SELECT * FROM per_player ORDER BY avg_stat DESC LIMIT 10;"
# Look for: "Index Scan using ix_games_competition_id" in plan. Avoid "Seq Scan on games".

# Standings sanity check (2 teams, 2 games — see test_standings_rank.py):
psql "$DATABASE_URL_DIRECT" -c "$(cat tests/sql/standings.sql)"
# Expected: 2 rows, RANK=1 for winner, RANK=2 for loser.
```

References: [Postgres 16 window functions](https://www.postgresql.org/docs/16/tutorial-window.html), [Postgres 16 RANK/DENSE_RANK](https://www.postgresql.org/docs/16/functions-window.html).

---

## 3. Pydantic v2 + OpenAPI Examples

### Read schema (verbatim — full example for CompetitionRead)

```python
# src/basketball_stats/schemas/competition.py
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


Phase = Literal["fase_previa", "segona_fase", "playoff"]


class CompetitionRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,  # ORM mode (replaces v1 orm_mode).
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "category": "1a-territorial",
                    "gender": "m",
                    "territory": "bcn",
                    "group_no": 4,
                    "season_id": 1,
                    "phase": "fase_previa",
                    "display_name": "1a Territorial Masculí · BCN · Grup 4 · 2025-26",
                },
                {
                    "id": 2,
                    "category": "super-copa",
                    "gender": "m",
                    "territory": "cat",
                    "group_no": 1,
                    "season_id": 1,
                    "phase": "playoff",
                    "display_name": "Super Copa Masculina · Playoff · 2025-26",
                },
            ]
        },
    )

    id: int
    category: str
    gender: Literal["m", "f"]
    territory: str
    group_no: int
    season_id: int
    phase: Phase
    display_name: str


class CompetitionCreate(BaseModel):
    """Draft schema — POST endpoint lands in P3 AUTH."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "category": "1a-territorial",
                "gender": "m",
                "territory": "bcn",
                "group_no": 4,
                "season_id": 1,
                "phase": "fase_previa",
            }]
        }
    )

    category: Annotated[str, Field(min_length=1, max_length=64)]
    gender: Literal["m", "f"]
    territory: Annotated[str, Field(min_length=3, max_length=8)]
    group_no: Annotated[int, Field(ge=1, le=99)]
    season_id: int
    phase: Phase
```

### PaginationParams helper (verbatim — D2-13)

```python
# src/basketball_stats/api/v1/deps.py
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field

from basketball_stats.core.db import get_db  # existing P1 re-export

__all__ = ["get_db", "PaginationParams", "PaginationDep"]


class PaginationParams(BaseModel):
    """offset/limit pagination — D2-13. Reusable across all list endpoints."""

    model_config = ConfigDict(extra="forbid")

    offset: Annotated[int, Field(ge=0, default=0)] = 0
    limit: Annotated[int, Field(ge=1, le=100, default=20)] = 20


PaginationDep = Annotated[PaginationParams, Depends()]
```

### Verification

```bash
# Confirm examples render in OpenAPI:
curl -s localhost:8000/openapi.json \
  | jq '.paths."/api/v1/competitions/{competition_id}".get.responses."200".content."application/json"'
# Expected: schema with "$ref" to CompetitionRead; the component schema contains
# the "examples" array we wrote.

# Confirm /docs Swagger UI renders them:
# Open http://localhost:8000/docs → expand GET /competitions/{id} → response panel
# shows a dropdown with 2 example payloads in Catalan.
```

### Pitfalls

- **`from_attributes=True` is REQUIRED for ORM-mapped reads.** Without it, `model_validate(box_score_orm_obj)` raises. v1's `orm_mode = True` is gone — only `model_config = ConfigDict(from_attributes=True)` works.
- **Multiple `examples` (list)** render as a dropdown in Swagger UI. Single `example` (singular) still works but is the v1 legacy form — prefer the list.
- **`Field(..., examples=[...])` per-field** is for per-field examples; for whole-payload examples use `model_config.json_schema_extra["examples"]`. D2-17 requires whole-payload, so use model_config.
- **Date/datetime** serialize to ISO 8601 strings by default in Pydantic v2 — no extra serializer needed for `game_date: date`.
- **`Annotated[int, Field(ge=0, le=100)]`** is the v2 way for numeric bounds. Bare `=Field(...)` defaults still work but `Annotated[...]` is the convention locked at P1 D-04.

Sources: [Pydantic 2.13 json_schema](https://docs.pydantic.dev/2.13/concepts/json_schema/), [FastAPI `examples`](https://fastapi.tiangolo.com/tutorial/schema-extra-example/).

---

## 4. testcontainers + pytest patterns

### Existing P1 infrastructure (reused as-is)

`tests/integration/conftest.py` already provides:

- `postgres_container` — session-scoped, `postgres:16-alpine`, `username=test/password=test/dbname=test_db`.
- `database_url_direct` / `database_url_async` — derived URLs.
- `_run_alembic_upgrade` — session-scoped, autouse, runs `alembic upgrade head` once via subprocess (R5).
- `engine` / `db_session` — function-scoped, fresh AsyncSession per test.

**P2 adds ONE new session-scoped fixture: `seed_minimal`.** Tests that need 12 box-scores for leaderboard ordering reuse it; tests that need a clean DB skip it.

### New `seed_minimal` fixture

```python
# tests/integration/conftest.py — APPEND to existing P1 file
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


@pytest_asyncio.fixture(scope="session")
async def seed_minimal(engine: AsyncEngine) -> AsyncIterator[None]:
    """Load data/seed/minimal.py once per session — for leaderboard/standings tests.

    Tests that need a clean DB explicitly skip this fixture by not requesting it.
    Truncate happens via SAVEPOINT in the per-test db_session if needed.
    """
    from basketball_stats.seed.minimal import seed  # type: ignore[import-not-found]

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed(session, force=True)
        await session.commit()
    yield
    # No teardown — session-scoped DB is destroyed by testcontainer at session end.
```

### VAL GENERATED COLUMN assertion test

```python
# tests/integration/test_val_generated_column.py
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_val_generated_column_matches_pir_fiba(db_session: AsyncSession) -> None:
    """val GENERATED column computes PIR FIBA literal on INSERT (D2-07 + SC3)."""
    # Setup: minimal FK dependencies (1 season, 1 competition, 1 club,
    # 1 team, 1 player, 1 game) — assume helpers in tests/factories.py.
    # Here we focus on the box_score INSERT and val read-back.
    await db_session.execute(text("""
        INSERT INTO clubs (id, display_name, normalized_name) VALUES (1, 'CB Test', 'CB TEST');
        INSERT INTO seasons (id, start_year, label) VALUES (1, 2025, '2025-26');
        INSERT INTO competitions (id, category, gender, territory, group_no, season_id, phase)
          VALUES (1, '1a-territorial', 'm', 'bcn', 4, 1, 'fase_previa');
        INSERT INTO teams (id, club_id, display_name, normalized_name)
          VALUES (1, 1, 'CB Test A', 'CB TEST A');
        INSERT INTO players (id, license_id, dorsal_default, display_name, normalized_name)
          VALUES (1, 99001, 5, 'Rafael Pintó', 'RAFAEL PINTO');
        INSERT INTO games (id, competition_id, matchday_no, game_date, home_team_id, away_team_id,
                           q1_home, q1_away, q2_home, q2_away, q3_home, q3_away, q4_home, q4_away,
                           total_home, total_away)
          VALUES (1, 1, 1, '2025-10-15', 1, 1, 20, 18, 22, 24, 18, 20, 20, 22, 80, 84);
    """))

    # Insert raw stats — val + reb computed by Postgres.
    await db_session.execute(text("""
        INSERT INTO box_scores
          (game_id, player_id, team_id, pts, reb_of, reb_def, ast, rec, tap,
           fouls_drawn, fg2a, fg2m, fg3a, fg3m, fta, ftm, per, fc, blocks_received)
        VALUES (1, 1, 1, 10, 3, 2, 4, 2, 1, 2, 5, 4, 3, 1, 2, 1, 1, 2, 0);
    """))

    row = (await db_session.execute(text(
        "SELECT reb, val FROM box_scores WHERE game_id = 1 AND player_id = 1"
    ))).one()

    # reb = reb_of + reb_def = 3 + 2 = 5
    assert row.reb == 5
    # val = 10 + 5 + 4 + 2 + 1 + 2 - (5-4) - (3-1) - (2-1) - 1 - 2 - 0
    #     = 10 + 5 + 4 + 2 + 1 + 2 - 1 - 2 - 1 - 1 - 2 - 0
    #     = 17
    assert row.val == 17
```

### Window-function RANK test (skeleton)

```python
# tests/integration/test_standings_rank.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.repositories.standings import fetch_standings


@pytest.mark.asyncio
async def test_standings_rank_two_teams_two_games(
    db_session: AsyncSession, seed_minimal: None
) -> None:
    """seed_minimal: 2 teams, 1 game home win → standings RANK = 1, 2."""
    standings = await fetch_standings(db_session, competition_id=1)
    assert len(standings) == 2
    assert standings[0]["position"] == 1
    assert standings[0]["wins"] >= standings[1]["wins"]
    assert standings[1]["position"] == 2
```

### ryuk off (inherited from P1)

P1 `tests/conftest.py` enforces `TESTCONTAINERS_RYUK_DISABLED=true` via pytest-env + an autouse session fixture. P2 inherits — no new work. Set in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
env = ["TESTCONTAINERS_RYUK_DISABLED=true"]
```

Sources: [testcontainers-python Postgres](https://testcontainers-python.readthedocs.io/en/latest/modules/postgres/), [pytest-asyncio](https://pytest-asyncio.readthedocs.io/en/latest/), [SQLAlchemy async transactional tests](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html).

---

## 5. normalize_name utility

### Implementation (verbatim — D2-02)

```python
# src/basketball_stats/core/text.py
"""Text normalization for entity names.

D2-02: UPPER + sense accents + TRIM. Applied to clubs/teams/players/coaches
``normalized_name`` columns. Original UTF-8 (with accents/case) is kept in
``display_name`` columns for output.

The federative FCBQ uses majuscules sense accents in official actas — normalizing
allows match-by-name across data sources without case/accent drift. Also primes
P4 tsvector + GIN for accent-insensitive search.
"""

from __future__ import annotations

import unicodedata


def normalize_name(s: str) -> str:
    """Return ``s`` uppercased, stripped, and with combining marks removed.

    >>> normalize_name("Rafael Pintó")
    'RAFAEL PINTO'
    >>> normalize_name("  L'Hospitalet  ")
    "L'HOSPITALET"
    >>> normalize_name("Núñez")
    'NUNEZ'
    """
    decomposed = unicodedata.normalize("NFD", s)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return stripped.upper().strip()
```

### Unit test cases (verbatim)

```python
# tests/unit/test_normalize_name.py
import pytest

from basketball_stats.core.text import normalize_name


@pytest.mark.parametrize(
    ("input_", "expected"),
    [
        # Basic Catalan accents
        ("Rafael Pintó", "RAFAEL PINTO"),
        ("Núñez", "NUNEZ"),
        ("Albà", "ALBA"),
        # Catalan ç → C (Mn-strip doesn't touch ç directly; it's a separate codepoint)
        ("Barça", "BARÇA"),  # NOTE: ç is NOT Mn, stays as Ç. Flagged §9 if Roger wants Ç→C.
        # Apostrophes / punctuation pass through (D2-02 says only accents stripped)
        ("L'Hospitalet", "L'HOSPITALET"),
        ("S. Joan", "S. JOAN"),
        # Whitespace trim
        ("  CB Granollers  ", "CB GRANOLLERS"),
        # Already uppercase
        ("CB ARTÉS", "CB ARTES"),
        # Empty / single char
        ("", ""),
        ("a", "A"),
        # ñ → N
        ("España", "ESPANA"),
    ],
)
def test_normalize_name(input_: str, expected: str) -> None:
    assert normalize_name(input_) == expected
```

### Edge cases — resolved + flagged

| Input | Output | Status |
|---|---|---|
| `"Rafael Pintó"` | `"RAFAEL PINTO"` | Resolved — combining tilde stripped. |
| `"L'Hospitalet"` | `"L'HOSPITALET"` | Resolved — apostrophe preserved (D2-02 says accents only). |
| `"España"` | `"ESPANA"` | Resolved — ñ decomposes to n + ̃. |
| `"Barça"` | `"BARÇA"` | **FLAGGED §9 Q3** — ç is a precomposed code point (category `Ll`), NOT a combining mark, so it does NOT strip to C. If Roger expects "BARCA", we need an explicit `c.lower() == "ç"` replacement step. D2-02 is ambiguous. |
| `"São Paulo"` | `"SAO PAULO"` | Resolved — tilde over a strips. |
| `"ẞ"` (German sharp S) | `"SS"` (upper()) | Resolved — Python `.upper()` handles ẞ → SS natively. |

### Where to put it

`src/basketball_stats/core/text.py` — consistent with `core/db.py`, `core/config.py` from P1. Single function, no class, no module-level state.

---

## 6. FastAPI Routers + Depends + Pagination

### Router template (verbatim)

```python
# src/basketball_stats/api/v1/competitions.py
"""Competitions router — READ-01, READ-02.

D2-15: routers call repositories directly (no service layer at P2; emerges at P3).
D2-13: pagination via PaginationDep + X-Total-Count header.
D2-18: response_model on every route.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.api.v1.deps import PaginationDep, get_db
from basketball_stats.models.competition import Competition
from basketball_stats.schemas.competition import CompetitionRead

router = APIRouter(prefix="/competitions", tags=["competitions"])

SessionDep = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "",
    response_model=list[CompetitionRead],
    summary="List competitions",
    description="Paginated list of competitions. Filters: category, gender, territory, season.",
)
async def list_competitions(
    response: Response,
    pagination: PaginationDep,
    session: SessionDep,
    category: str | None = None,
    gender: str | None = None,
    territory: str | None = None,
    season_id: int | None = None,
) -> list[Competition]:
    stmt = select(Competition)
    if category:
        stmt = stmt.where(Competition.category == category)
    if gender:
        stmt = stmt.where(Competition.gender == gender)
    if territory:
        stmt = stmt.where(Competition.territory == territory)
    if season_id is not None:
        stmt = stmt.where(Competition.season_id == season_id)

    # Total count BEFORE applying limit/offset (D2-13).
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    stmt = stmt.offset(pagination.offset).limit(pagination.limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{competition_id}",
    response_model=CompetitionRead,
    responses={404: {"description": "Competition not found"}},
)
async def get_competition(
    competition_id: int,
    session: SessionDep,
) -> Competition:
    comp = await session.get(Competition, competition_id)
    if comp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="competition not found")
    return comp
```

### Router registration

```python
# src/basketball_stats/api/v1/__init__.py
from fastapi import APIRouter

from basketball_stats.api.v1 import (
    competitions,
    games,
    health,
    leaderboards,
    players,
    standings,
    teams,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(competitions.router)
api_router.include_router(teams.router)
api_router.include_router(players.router)
api_router.include_router(games.router)
api_router.include_router(standings.router)
api_router.include_router(leaderboards.router)
```

```python
# src/basketball_stats/main.py — only the include_router line is new
from basketball_stats.api.v1 import api_router  # noqa
app.include_router(api_router)
```

### Pitfalls

- **`X-Total-Count` MUST go through `response: Response`** parameter, not via `JSONResponse(headers=...)` constructor — that bypasses `response_model` serialization. Pattern above is the FastAPI-canonical.
- **mypy --strict + `Annotated[..., Depends()]`** works as written. The trap: bare `def f(x: X = Depends())` triggers `disallow_any_decorated` in some mypy configs. Use `Annotated[X, Depends(...)]` — locked at P1 D-04.
- **404 NotFound** — raise `HTTPException(status.HTTP_404_NOT_FOUND, detail=...)` directly. P1 D-04's global exception handlers catch `RequestValidationError` and `Exception` (500), NOT `HTTPException` — FastAPI's built-in handler turns `HTTPException` into the appropriate JSON response. Don't try to override it.
- **`response_model=list[CompetitionRead]`** triggers automatic ORM→Pydantic conversion via `from_attributes=True` on every row. Don't manually call `model_validate` in the router — let FastAPI do it.
- **Count query BEFORE limit/offset** — `select(func.count()).select_from(stmt.subquery())` is the SQLAlchemy 2.0 idiom for getting total. Don't do `len(await session.execute(stmt).all())` — that streams the whole table.

Sources: [FastAPI Depends](https://fastapi.tiangolo.com/tutorial/dependencies/), [FastAPI Response headers](https://fastapi.tiangolo.com/advanced/response-headers/).

---

## 7. File Layout (locked per planner)

### Existing P1 files (reuse as-is)

| File | Role |
|---|---|
| `src/basketball_stats/main.py` | FastAPI app factory; P2 only adds `app.include_router(api_router)`. |
| `src/basketball_stats/core/config.py` | Settings — unchanged. |
| `src/basketball_stats/core/db.py` | Async engine + `get_db()` — unchanged. |
| `src/basketball_stats/models/base.py` | Declarative Base — receives 9 new models in P2. |
| `src/basketball_stats/api/errors.py` | Global exception handlers — unchanged. |
| `src/basketball_stats/api/v1/deps.py` | P2 ADDS `PaginationParams` + `PaginationDep` to this file. |
| `src/basketball_stats/api/v1/health.py` | Unchanged. |
| `tests/conftest.py` | Ryuk failsafe — unchanged. |
| `tests/integration/conftest.py` | testcontainers infra — P2 APPENDS `seed_minimal` fixture. |
| `migrations/env.py` | Async-aware env — unchanged. |
| `migrations/versions/0001_baseline.py` | Empty baseline — unchanged. |

### New files P2 creates

| File | Contents |
|---|---|
| `src/basketball_stats/core/text.py` | `normalize_name(s)` utility. |
| `src/basketball_stats/models/club.py` | `Club` model. |
| `src/basketball_stats/models/season.py` | `Season` model. |
| `src/basketball_stats/models/competition.py` | `Competition` model + `Phase` enum. |
| `src/basketball_stats/models/team.py` | `Team` model. |
| `src/basketball_stats/models/player.py` | `Player` model. |
| `src/basketball_stats/models/coach.py` | `Coach` model. |
| `src/basketball_stats/models/roster.py` | `Roster` association table. |
| `src/basketball_stats/models/coaching_assignment.py` | `CoachingAssignment` association table. |
| `src/basketball_stats/models/game.py` | `Game` model. |
| `src/basketball_stats/models/box_score.py` | `BoxScore` model + 2 GENERATED columns. |
| `src/basketball_stats/schemas/__init__.py` | Re-exports. |
| `src/basketball_stats/schemas/competition.py` | `CompetitionRead`/`Create`/`Update`. |
| `src/basketball_stats/schemas/team.py` | `TeamRead`/`Create`/`Update`. |
| `src/basketball_stats/schemas/player.py` | `PlayerRead`/`Create`/`Update`. |
| `src/basketball_stats/schemas/game.py` | `GameRead` + `BoxScoreRead`. |
| `src/basketball_stats/schemas/standings.py` | `StandingsRow`. |
| `src/basketball_stats/schemas/leaderboards.py` | `LeaderboardRow` + `LeaderboardStat` enum. |
| `src/basketball_stats/schemas/pagination.py` | (optional — or keep in `deps.py`). |
| `src/basketball_stats/repositories/__init__.py` | empty package marker. |
| `src/basketball_stats/repositories/standings.py` | window-function standings (STAT-01). |
| `src/basketball_stats/repositories/leaderboards.py` | nested window leaderboards (STAT-02). |
| `src/basketball_stats/repositories/games.py` | game detail + box-score query. |
| `src/basketball_stats/repositories/players.py` | player profile + season stats. |
| `src/basketball_stats/repositories/teams.py` | team detail + roster. |
| `src/basketball_stats/repositories/competitions.py` | competition list + filters. |
| `src/basketball_stats/api/v1/competitions.py` | router. |
| `src/basketball_stats/api/v1/teams.py` | router. |
| `src/basketball_stats/api/v1/players.py` | router. |
| `src/basketball_stats/api/v1/games.py` | router. |
| `src/basketball_stats/api/v1/standings.py` | router. |
| `src/basketball_stats/api/v1/leaderboards.py` | router. |
| `src/basketball_stats/api/v1/__init__.py` | NEW: aggregator `api_router`. |
| `src/basketball_stats/seed/__init__.py` | package marker. |
| `src/basketball_stats/seed/minimal.py` | seed function — 1 comp + 2 teams + 1 game + 12 box-scores + 1 coach + 2 assignments. |
| `migrations/versions/0002_core_entities.py` | full P2 migration (manual). |
| `tests/unit/test_normalize_name.py` | unit. |
| `tests/integration/test_val_generated_column.py` | val PIR assertion. |
| `tests/integration/test_standings_rank.py` | RANK assertion. |
| `tests/integration/test_leaderboards_val.py` | leaderboard ordering. |
| `tests/integration/test_pagination_offset_limit.py` | offset/limit + X-Total-Count. |
| `tests/integration/test_competition_endpoint_filters.py` | filters. |
| `tests/integration/test_games_endpoint.py` | box-score detail. |
| `docs/adr/0003-val-pir-fiba-formula.md` | ADR-0003. |
| `docs/adr/0004-standings-tie-breaker.md` | ADR-0004. |

---

## 8. Verification Commands per Success Criterion

### SC1 — `GET /competitions/{id}/standings` with `RANK()` window function

```bash
# Visual proof of SQL in code:
grep -n "RANK() OVER" src/basketball_stats/repositories/standings.py
# Expected: 1+ match. The `text()` block is unmistakable.

# Functional proof:
curl -s "http://localhost:8000/api/v1/competitions/1/standings" | jq '.[0].position'
# Expected: 1 (after seed_minimal: 1 game, home team wins, RANK=1).

# Integration test:
uv run pytest tests/integration/test_standings_rank.py -v
```

### SC2 — `GET /competitions/{id}/leaderboards?stat=val` window function + composite index

```bash
grep -n "RANK() OVER" src/basketball_stats/repositories/leaderboards.py
grep -n "ix_box_scores_player_lookup\|ix_games_competition_id" migrations/versions/0002_core_entities.py

curl -s "http://localhost:8000/api/v1/competitions/1/leaderboards?stat=val&limit=3" | jq '.[].position'
# Expected: [1, 2, 3].

uv run pytest tests/integration/test_leaderboards_val.py -v
```

### SC3 — Migration shows `VAL` as GENERATED COLUMN (FIBA PIR), not Python

```bash
grep -n "Computed(" migrations/versions/0002_core_entities.py
# Expected: 2 matches (reb + val).

# Confirm not computed in Python anywhere:
grep -rn "def.*val" src/basketball_stats/ | grep -v "schemas\|val:" | grep -v "Computed"
# Expected: 0 matches that calculate val arithmetically.

# Live DB verification:
psql "$DATABASE_URL_DIRECT" -c "\d+ box_scores" | grep "generated"
# Expected: 2 lines containing "generated always as ... stored".
```

### SC4 — `GET /games/{id}` box-score complete with Q1-Q4 marker

```bash
curl -s "http://localhost:8000/api/v1/games/1" | jq '{q1_home, q1_away, q4_home, q4_away, total_home, total_away, box_scores: (.box_scores | length)}'
# Expected: 4 quarters present, box_scores length = 12 (or 24 home+away depending on seed).
```

### SC5 — Integration tests on real Postgres + `/docs` complete

```bash
uv run pytest tests/integration/ -v --tb=short
# Expected: all tests green.

# Coverage:
uv run pytest tests/ --cov=src/basketball_stats/repositories --cov-report=term-missing
# Expected: ≥80% on repositories.

# /docs visual:
curl -s http://localhost:8000/openapi.json | jq '.paths | keys | length'
# Expected: ≥9 paths (health + 8 GET endpoints).
```

### SC6 — `data/seed/minimal.py` populates DB, READs non-empty

```bash
docker compose exec api python -m basketball_stats.seed.minimal
# Expected: stdout reports "seeded: 1 competition, 2 teams, 12 players, 1 game, 24 box_scores".

curl -s "http://localhost:8000/api/v1/competitions" | jq 'length'
# Expected: ≥1.

curl -s "http://localhost:8000/api/v1/teams" | jq 'length'
# Expected: 2.
```

### SC7 — Pydantic schemas with `json_schema_extra examples` render at `/docs`

```bash
curl -s http://localhost:8000/openapi.json \
  | jq '.components.schemas.CompetitionRead.examples'
# Expected: non-null array with ≥1 Catalan example.

# All Read schemas have examples:
grep -rn "json_schema_extra" src/basketball_stats/schemas/
# Expected: 1+ match per *.py file.
```

---

## 9. Open Questions / Flags for Roger

### Q1 — D2-20 composite index `(competition_id, season_id, avg_stat DESC)` is impossible as literally written

**Issue:** `avg_stat` is a window-function output computed on-the-fly from `box_scores.{val|pts|reb|...}`. It is NOT a stored column on `box_scores`. Postgres cannot index a non-stored expression that comes out of `AVG(stat) OVER (PARTITION BY ...)`.

**Concrete resolution proposed:** Replace D2-20's "composite index `(competition_id, season_id, avg_stat DESC)`" with two real indexes that actually accelerate the leaderboards query:

1. `ix_games_competition_id` on `games(competition_id)` — accelerates the WHERE clause.
2. `ix_box_scores_player_lookup` on `box_scores(player_id)` — accelerates the join + PARTITION BY player_id.

The "DESC ordering" of leaderboards happens inside the window function's ORDER BY clause, executed in-memory after the partition is gathered — no index needed at that level for ~500-player scale.

**Action requested:** Confirm during /gsd-plan-phase that this interpretation is acceptable. If Roger wants a literal expression index on the GENERATED column `val` itself (e.g. `CREATE INDEX ix_box_scores_val_desc ON box_scores (val DESC)`), that's a valid OPTIONAL addition for showcase value but not required by SC2. Recommend deferring unless EXPLAIN ANALYZE shows the leaderboards query >100ms at seed scale.

### Q2 — D2-02 normalize_name + Catalan `ç`

**Issue:** The `unicodedata.normalize("NFD")` + Mn-strip approach **does NOT** transliterate ç → C, because `ç` (U+00E7) is a precomposed code point of category `Ll`, not a combining mark. Result: `normalize_name("Barça")` returns `"BARÇA"`, not `"BARCA"`.

**Action requested:** Confirm during plan whether Roger wants:
- (A) Keep `ç` as `Ç` in normalized form — semantically still uppercase + no accents. Aligns with "accents only" reading of D2-02.
- (B) Add explicit `ç → c` (and `Ç → C`) replacement — semantically "letters-only" normalization. Matches FCBQ acta convention more closely.

Recommend (B) for FCBQ matching robustness, but the change is 2 extra lines. Tests above include `Barça → BARÇA` reflecting the current (A) behavior; flip if (B).

### Q3 — ADR-0003 + ADR-0004 — written when?

`02-CONTEXT.md` says ADR-0003 and ADR-0004 are **scope of P2** (not deferred to P5). The planner should schedule both ADR docs as separate tasks BEFORE `/gsd-verify-work` runs. Suggest placing each ADR task right after the related repository file lands (ADR-0003 after `box_score.py` + migration; ADR-0004 after `repositories/standings.py`).

---

## 10. References

### Postgres 16

- [PostgreSQL 16 — Generated Columns (5.3)](https://www.postgresql.org/docs/16/ddl-generated-columns.html) — STORED only on 16; expression must be IMMUTABLE; cannot reference other generated columns in same row.
- [PostgreSQL 16 — Window Functions tutorial](https://www.postgresql.org/docs/16/tutorial-window.html)
- [PostgreSQL 16 — Window Function reference (RANK/DENSE_RANK/ROW_NUMBER)](https://www.postgresql.org/docs/16/functions-window.html)

### SQLAlchemy 2.0.49

- [SQLAlchemy 2.0 — Computed columns (Column INSERT/UPDATE Defaults)](https://docs.sqlalchemy.org/en/20/core/defaults.html#computed-columns) — `Computed("expr", persisted=True)`.
- [SQLAlchemy 2.0 — Async ORM (selectinload, joinedload, lazy="raise_on_sql")](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [SQLAlchemy 2.0 — Working with relationships in async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#preventing-implicit-io-when-using-asyncsession)

### Pydantic 2.13.4

- [Pydantic 2.13 — JSON Schema customization](https://docs.pydantic.dev/2.13/concepts/json_schema/#field-level-customization) — `model_config = ConfigDict(json_schema_extra={"examples": [...]})`.
- [Pydantic 2.13 — Models / ConfigDict](https://docs.pydantic.dev/2.13/concepts/config/) — `from_attributes=True`.

### FastAPI 0.136.x

- [FastAPI — Dependencies with `Annotated[X, Depends(...)]`](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [FastAPI — Response headers (Response param)](https://fastapi.tiangolo.com/advanced/response-headers/)
- [FastAPI — Schema extras / `examples`](https://fastapi.tiangolo.com/tutorial/schema-extra-example/)

### testcontainers-python 4.14.2

- [testcontainers-python — Postgres module](https://testcontainers-python.readthedocs.io/en/latest/modules/postgres/)
- [pytest-asyncio docs](https://pytest-asyncio.readthedocs.io/en/latest/)

### Alembic 1.18.x

- [Alembic — Cookbook (manual migration writing)](https://alembic.sqlalchemy.org/en/latest/cookbook.html)
- [Alembic — Operation reference (create_table, create_index)](https://alembic.sqlalchemy.org/en/latest/ops.html)

### Project canonical refs (already locked)

- `.planning/research/STACK.md` — version pins verified 2026-05-19.
- `.planning/research/ARCHITECTURE.md` §1, §2, §5.
- `.planning/research/PITFALLS.md` P1.2, P2.1, P3.5.
- `.planning/research/FEATURES.md` §1.4, §1.7.
- `.planning/phases/01-foundation/01-CONTEXT.md` D-04, D-07, D-08, D-16, D-19, D-20.
- `.planning/phases/02-core-entities/02-CONTEXT.md` D2-01..D2-20.

---

*End of research. Confidence HIGH on all 6 areas. 3 flags for Roger in §9 — all minor and resolvable during /gsd-plan-phase.*
