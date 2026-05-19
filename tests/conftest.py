"""Top-level test config — ryuk failsafe only.

Docker-dependent fixtures (Postgres testcontainer, async engine, db_session) live in
``tests/integration/conftest.py`` so unit tests stay docker-free.

R6: ``TESTCONTAINERS_RYUK_DISABLED=true`` set via ``pytest-env`` in ``pyproject.toml``.
The autouse fixture below is a failsafe — if someone removes the pytest-env line later,
the assertion warns immediately.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True, scope="session")
def _ensure_ryuk_disabled() -> Iterator[None]:
    """Failsafe — must run with ryuk disabled (CI jobs hang otherwise — R6)."""
    if os.environ.get("TESTCONTAINERS_RYUK_DISABLED") != "true":
        raise RuntimeError(
            "TESTCONTAINERS_RYUK_DISABLED must be 'true'. Set via pyproject "
            "[tool.pytest.ini_options].env or shell export."
        )
    yield
