"""Integration tests for `data/seed/load_basquethero.py` (D2.5-10, SC7).

Covers the LOCKED invariants: row counts after a fresh load, idempotency on
double load, GENERATED columns (`val`, `reb`) re-computed by Postgres,
mid-fixture updates path, and the skip-without-license behaviour (D2.5-05).

Uses the W2 `sample-mini.json` fixture under `tests/fixtures/basquethero/`.
Loader lives at `data/seed/load_basquethero.py`; the test imports the
`load()` coroutine directly rather than spawning a subprocess so the
PostgresContainer-backed `db_session` fixture is reused.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from basketball_stats.ingest.basquethero.models import BasqueteroFixture
from basketball_stats.models import (
    BoxScore,
    Club,
    Competition,
    Game,
    Player,
    Roster,
    Season,
    Team,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LOADER_PATH = REPO_ROOT / "data" / "seed" / "load_basquethero.py"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "basquethero" / "sample-mini.json"


def _import_loader() -> ModuleType:
    """Import `data/seed/load_basquethero.py` as a module (not on sys.path)."""
    if "load_basquethero" in sys.modules:
        return sys.modules["load_basquethero"]
    spec = importlib.util.spec_from_file_location("load_basquethero", LOADER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["load_basquethero"] = module
    spec.loader.exec_module(module)
    return module


def _read_fixture() -> BasqueteroFixture:
    return BasqueteroFixture.model_validate_json(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_load_sample_mini_populates_rows(db_session: AsyncSession) -> None:
    """First load: exact row counts for all entities (D2.5-04 fixture shape)."""
    loader = _import_loader()
    fixture = _read_fixture()
    summary = await loader.load(db_session, fixture)

    assert summary.seasons == 1
    assert summary.competitions == 1
    assert summary.clubs == 2
    assert summary.teams == 2
    assert summary.players == 12
    assert summary.games == 1
    assert summary.box_scores == 12
    assert summary.skipped_players == 0

    expected_db_counts = {
        Season: 1,
        Club: 2,
        Competition: 1,
        Team: 2,
        Player: 12,
        Roster: 12,
        Game: 1,
        BoxScore: 12,
    }
    for model, count in expected_db_counts.items():
        result = await db_session.execute(select(func.count()).select_from(model))
        assert int(result.scalar_one()) == count, f"{model.__name__} count mismatch"


@pytest.mark.asyncio
async def test_load_idempotent_no_duplicates(db_session: AsyncSession) -> None:
    """Second consecutive load yields identical row counts (D2.5-06 UPSERT)."""
    loader = _import_loader()
    fixture = _read_fixture()

    await loader.load(db_session, fixture)
    counts_first = {
        m.__name__: int(
            (await db_session.execute(select(func.count()).select_from(m))).scalar_one()
        )
        for m in (Season, Club, Competition, Team, Player, Roster, Game, BoxScore)
    }

    await loader.load(db_session, fixture)
    counts_second = {
        m.__name__: int(
            (await db_session.execute(select(func.count()).select_from(m))).scalar_one()
        )
        for m in (Season, Club, Competition, Team, Player, Roster, Game, BoxScore)
    }
    assert counts_first == counts_second, (
        f"second load created/deleted rows: first={counts_first} second={counts_second}"
    )


@pytest.mark.asyncio
async def test_load_recomputes_val_via_generated_column(
    db_session: AsyncSession,
) -> None:
    """`val` and `reb` are GENERATED COLUMNS — loader writes only raw inputs."""
    loader = _import_loader()
    fixture = _read_fixture()
    await loader.load(db_session, fixture)

    result = await db_session.execute(
        select(BoxScore.reb_of, BoxScore.reb_def, BoxScore.reb, BoxScore.val).where(
            BoxScore.val.is_not(None)
        )
    )
    rows = list(result.all())
    assert len(rows) == 12, f"expect 12 box-scores with val populated, got {len(rows)}"
    for reb_of, reb_def, reb, val in rows:
        assert reb == reb_of + reb_def, f"reb {reb} != reb_of+reb_def {reb_of}+{reb_def}"
        assert val is not None, "val GENERATED column populated"


@pytest.mark.asyncio
async def test_load_with_modified_fixture_updates_rows(
    db_session: AsyncSession,
) -> None:
    """Modifying a stat in-memory + re-load → row updated, no duplicate."""
    loader = _import_loader()
    fixture = _read_fixture()
    await loader.load(db_session, fixture)

    initial_count_result = await db_session.execute(select(func.count()).select_from(BoxScore))
    initial_count = int(initial_count_result.scalar_one())

    # Mutate the first box-score's `points` from 14 → 50 and re-load.
    fixture_json = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fixture_json["games"][0]["box_scores"][0]["points"] = 50
    mutated = BasqueteroFixture.model_validate(deepcopy(fixture_json))
    await loader.load(db_session, mutated)

    after_count_result = await db_session.execute(select(func.count()).select_from(BoxScore))
    after_count = int(after_count_result.scalar_one())
    assert after_count == initial_count, "re-load with mutation should not duplicate"

    pts_result = await db_session.execute(
        select(BoxScore.pts).where(BoxScore.player_id.in_(select(Player.id).limit(1)))
    )
    first_pts = pts_result.scalars().first()
    # We can't pin which player_id maps to slot 0 without re-deriving via license_id,
    # but at least one box-score row in the table should now have pts=50.
    all_pts_result = await db_session.execute(select(BoxScore.pts))
    all_pts = {int(p) for p in all_pts_result.scalars().all()}
    assert 50 in all_pts, f"mutated value 50 not found in pts {sorted(all_pts)}"
    assert first_pts is not None  # ensure query ran


@pytest.mark.asyncio
async def test_load_skips_players_without_license(
    db_session: AsyncSession,
) -> None:
    """Player with `license_id=None` is skipped with a structured warning (D2.5-05)."""
    loader = _import_loader()
    fixture_json = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fixture_json["players"][0]["license_id"] = None
    # Also drop the orphaned box-score that pointed at that license to avoid FK errors.
    fixture_json["games"][0]["box_scores"] = [
        bs for bs in fixture_json["games"][0]["box_scores"] if bs["player_license_id"] != 98001
    ]
    mutated = BasqueteroFixture.model_validate(fixture_json)

    summary = await loader.load(db_session, mutated)

    assert summary.skipped_players == 1, f"expect 1 skipped player, got {summary.skipped_players}"
    assert summary.players == 11, f"expect 11 loaded players (1 skipped), got {summary.players}"

    db_count_result = await db_session.execute(select(func.count()).select_from(Player))
    assert int(db_count_result.scalar_one()) == 11
