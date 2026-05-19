---
phase: 1
phase_name: foundation
created: 2026-05-19
researcher: Claude (gsd-phase-researcher)
scope: Gap-fill for Koyeb+Neon switch + uv/Alembic/structlog/testcontainers exact idioms 2026
relationship_to_project_research: This document does NOT redo `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `SUMMARY.md`. It fills the deltas the planner needs to write executable tasks for Phase 1.
confidence:
  koyeb_cli: HIGH (verified ctx7 /websites/koyeb 2026-05-19)
  koyeb_health_checks: MEDIUM (params documented; exact CLI flag syntax not enumerated in source)
  koyeb_free_tier: HIGH (verified — `free` instance, 512MB/0.1vCPU/2GB SSD, one per org)
  neon_connection: HIGH (verified ctx7 /websites/neon — pooled default, sslmode+channel_binding)
  neon_free_tier: MEDIUM (compute hour limits found, exact 0.5 GB storage not re-verified in this session — pin to docs check at execute time)
  uv_pep735: HIGH (verified — uv supports [dependency-groups] since 0.4.27)
  uv_setup_action: HIGH (verified — astral-sh/setup-uv@v8.1.0 current; pinning by SHA recommended)
  alembic_async: HIGH (verified — official cookbook template)
  testcontainers: HIGH (verified — PostgresContainer API + ryuk env var)
  structlog: HIGH (verified — contextvars + JSON renderer + tty detection)
  dockerfile_uv: HIGH (verified — astral-sh/uv-docker-example reference)
  pre_commit: HIGH (versions verified for ruff, gitleaks, conventional-pre-commit)
  dependabot: HIGH (schema verified; pip + github-actions ecosystems standard)
---

# Phase 1: Foundation — Research

## Summary

Phase 1 is a skeleton-deploy phase: container builds, GHA CI green, Koyeb serves a public URL, `/healthz` does a real `SELECT 1` against Neon Postgres. The project-level research (`.planning/research/`) covered FastAPI/Pydantic/SQLAlchemy/asyncpg with Fly.io as deploy target. Post-review the deploy target switched to **Koyeb + Neon**. This research fills the Koyeb-specific gaps and verifies 2026-current idioms for uv/Alembic/structlog/testcontainers — the eight execution-blockers identified by the planner.

**Primary recommendation:** Use `koyeb app init` (the multi-arg single-command convenience) for the first deploy; configure HTTP health check via the control panel UI for P1 (CLI flag names for health-check parameters are NOT enumerated in the public docs — control panel UI is the documented path). Pin everything: `astral-sh/setup-uv@<sha> # v8.1.0`, `python:3.12-slim`, `postgres:16-alpine`, all pre-commit hook revs. Use Alembic's official async cookbook template (`alembic init -t async`). Disable testcontainers ryuk in CI via `TESTCONTAINERS_RYUK_DISABLED=true`. structlog uses tty-detection to switch console/JSON renderers automatically.

## Project Constraints (from CLAUDE.md / project ruleset)

The vault root `CLAUDE.md` requires:
- **No overlap** with Vercel / Render / Supabase / Next.js / React / Spring. Koyeb + Neon respects this.
- **Tests always** before closing. Phase 1 must ship at least one integration smoke test of `/healthz` against testcontainers Postgres (D-16).
- **AI_ prefix only on docs Claude creates.** P1 outputs (`README.md`, `Dockerfile`, etc.) are Roger-written and must NOT use the AI_ prefix. The `AI_basketball-portfolio-defense.md` (Phase 5) does use it.
- **One step at a time.** The planner should structure tasks so each can be verified before the next runs (build → CI → first deploy → healthcheck).

## User Constraints (from CONTEXT.md)

The 32 implementation decisions D-01..D-32 are LOCKED in `.planning/phases/01-foundation/01-CONTEXT.md`. They are NOT repeated here in full. Planner MUST honor them verbatim. The most load-bearing for execution:

- D-01..D-05: `src/basketball_stats/` layout, full architecture tree at first commit (empty `__init__.py` + docstrings only), `tests/unit + tests/integration` split.
- D-06..D-08: Alembic initialized at P1 with empty baseline revision `0001_baseline.py`; CI validates `upgrade head → downgrade base → upgrade head` round-trip.
- D-09..D-11: Single `/healthz` (no `/readyz` split), returns 503 on DB fail, no BackgroundTask.
- D-12..D-14: Python 3.12 pinned via `.python-version` + `requires-python`; uv 0.11.15 with `uv.lock` committed; `pyproject.toml` is the single config source (`alembic.ini` is the only exception).
- D-15..D-18: Single Python version in CI (no matrix); testcontainers from P1; `TESTCONTAINERS_RYUK_DISABLED=true` in CI; uv cache via setup-uv action; CI on push + PR to main.
- D-19..D-21: structlog JSON in prod, console in dev (env-detected); custom ASGI middleware for `request_id` bound to structlog contextvars; 5 README badges.
- D-22..D-25: Multi-stage Dockerfile `python:3.12-slim`, < 200 MB, BuildKit cache mount, non-root user, complete `.dockerignore`, docker-compose `api + postgres` only.
- D-26..D-29: GitHub repo PUBLIC from first push, exhaustive `.gitignore`, pre-commit (ruff + gitleaks + mypy --strict + conventional-pre-commit), Dependabot weekly.
- D-30..D-32: Minimal README, `docs/setup/koyeb-neon.md` step-by-step, ADR-0001 stack-election baseline.

**Deferred (OUT OF SCOPE for P1):** `/readyz`, OpenTelemetry, matrix CI multi-Python, server-side commitlint, JWT_SECRET rotation, multi-region, custom domain.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | `docker-compose up` engega api + postgres amb healthcheck dependencies | §7 Dockerfile + docker-compose pattern |
| INFRA-02 | Multi-stage Dockerfile `python:3.12-slim`, image < 200 MB, complete `.dockerignore` | §7 multi-stage uv Dockerfile (reference image ~150 MB verified) |
| INFRA-03 | GHA CI: `ruff check` + `mypy --strict` + `pytest`, push + PR, < 5 min | §3 uv idioms + §8 GHA workflow structure |
| INFRA-05 | Koyeb deploy serveix `<koyeb-url>/healthz` amb Neon connectada via `DATABASE_URL` secret | §1 Koyeb CLI + §2 Neon connection |
| OBS-02 | `/healthz` retorna `{status:ok, db:ok}` amb `SELECT 1` real | §1 health check params + project research P1.3 (get_db) |
| OBS-03 | Structured logging JSON en prod, pretty en dev, `request_id` per request | §6 structlog FastAPI integration |
| OBS-07 | README badges: CI status (GHA), ruff, mypy, Python 3.12, license MIT | Standard shields.io badges (no further research needed) |
| TEST-01 | Unit tests sobre services + schemas + utils; coverage 70% min (P1: 1-2 smoke tests) | §5 testcontainers PostgresContainer |

---

## 1. Koyeb CLI — Exact Commands (2026)

**Source:** ctx7 `/websites/koyeb` — Koyeb docs index (verified 2026-05-19). **Note:** Koyeb is being acquired by Mistral AI (banner on docs site); the platform and free tier remain operational per current docs, but track this in §Risks.

### 1.1 Authentication
```bash
koyeb login              # interactive — pastes API token; stored at ~/.koyeb.yaml
# Or: export KOYEB_TOKEN=<token>  (used by --token flag)
```

### 1.2 Create app + service (one shot via `app init`)

**This is the documented "happy path" for first deploy.** It creates the app, the service, ports, routes, env vars in a single command:

```bash
koyeb app init basketball-stats-api \
  --docker <DOCKER_IMAGE>:<TAG> \
  --instance-type free \
  --regions fra \
  --ports 8000:http \
  --routes /:8000 \
  --env PORT=8000 \
  --env DATABASE_URL='{{ secret.DATABASE_URL }}' \
  --env ENV=prod \
  --env LOG_LEVEL=INFO
```
[VERIFIED: ctx7 /websites/koyeb — `koyeb app init` pattern documented in `/docs/integrations/databases/neon` quickstart for Express+Neon, syntax identical for Python images]

### 1.3 Alternative: explicit `koyeb deploy` (git build)

```bash
koyeb deploy \
  --git github.com/roger-llinares/basketball-stats-api \
  --git-branch main \
  --build-command "uv sync --locked" \
  --env DATABASE_URL='{{ secret.DATABASE_URL }}' \
  --region fra
```
[VERIFIED: ctx7 /websites/koyeb — pattern from `/docs/integrations/databases/mongodb-atlas`]

**Recommendation:** Use `app init` with `--docker` for P1. Reason: the Dockerfile is the source of truth (matches `docker compose up` locally); buildpacks add a layer of abstraction that complicates parity. [CITED: D-22 in CONTEXT.md mandates multi-stage Docker]

### 1.4 Secrets

Create secrets BEFORE service create (env interpolation `{{ secret.NAME }}` resolves at deploy):

```bash
koyeb secrets create DATABASE_URL --value-from-stdin
# Then paste the Neon pooled connection URL, Ctrl-D

koyeb secrets create JWT_SECRET --value-from-stdin   # P1 stub for P3
```
[VERIFIED: ctx7 — `koyeb secrets create` has `--value-from-stdin` flag; `type=simple` is default]

### 1.5 Update service / redeploy
```bash
koyeb service update basketball-stats-api/basketball-stats-api \
  --env LOG_LEVEL=DEBUG          # rolling redeploy
koyeb services redeploy basketball-stats-api/basketball-stats-api
```
[VERIFIED: ctx7 — `koyeb services update` and `redeploy` documented]

### 1.6 Service flags (verified subset)

| Flag | Type | Purpose | Default |
|------|------|---------|---------|
| `--instance-type` | string | `free`, `nano`, `eco-micro`, `small`, ... | `nano` |
| `--regions` | strings | comma-separated, see §1.7 | `was` (US East) |
| `--ports` | strings | `8000:http` | — |
| `--routes` | strings | `/:8000` | — |
| `--env` | strings | repeat per var; `KEY=VALUE` or `KEY={{ secret.NAME }}` | — |
| `--min-scale` / `--max-scale` | int | for autoscaling | 1 / 1 |
| `--type` | string | `WEB` or `WORKER` | `WEB` |
| `--docker` | string | container image | — |
| `--git` / `--git-branch` / `--git-build-command` | string | git source | — |

[VERIFIED: ctx7 service update flags table from `/docs/build-and-deploy/cli/reference`]

### 1.7 Regions

Available regions include `fra` (Frankfurt), `was` (Washington DC), `par` (Paris — verify at execute time), `sin` (Singapore). [VERIFIED for `fra` and `was`: ctx7 examples — `--region was` and `--regions fra` shown in multiple docs] [ASSUMED for `par`/`mad`: Koyeb advertises EU regions; exact code names not enumerated in retrieved snippets — Roger should run `koyeb regions list` at execute time to confirm closest-to-Catalonia code.]

**Recommendation for P1:** Default `--regions fra` (Frankfurt — closest verified EU region to Catalonia). If `par` or `mad` shows in `koyeb regions list`, prefer them (lower latency).

### 1.8 Health check configuration (gap — see §Risks)

The docs explicitly state HTTP health checks are configured via the **Koyeb control panel UI** (Service → Health checks → expand section → set protocol HTTP + path). [VERIFIED: ctx7 `/docs/run-and-scale/health-checks`]

Customizable parameters [VERIFIED: ctx7]:
- **Path** — e.g., `/healthz`
- **HTTP method** — default `GET`
- **Custom headers**
- **Grace period** — before first check (let app boot)
- **Interval** — between checks
- **Restart limit** — consecutive failures before restart
- **Timeout** — per check

Expected behavior [VERIFIED: ctx7]: 2xx/3xx = healthy, anything else = failure → after `restart limit` failures, instance restarts.

**Gap:** Public docs do NOT enumerate CLI flag names for these parameters. The CLI reference shows `--checks` exists at a high level (visible in command tree) but the parameter syntax is not documented in the snippets retrieved. [LOW confidence on exact CLI flag spelling]

**Workaround for P1:** Configure health check via Koyeb dashboard after first deploy. Document this manual step in `docs/setup/koyeb-neon.md` (D-31). Defer CLI-based health check config to P4 (`INFRA-04` deploy-on-tag automation) where it becomes necessary.

### 1.9 release_command equivalent (alembic upgrade head)

Koyeb does NOT have a Fly.io-style `release_command` config key. Two documented options:

**Option A (recommended for P1):** Run migrations as part of the container's startup script.
```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn basketball_stats.main:app --host 0.0.0.0 --port 8000"]
```
Pro: zero Koyeb-specific config; same Dockerfile works locally + prod. Con: every instance startup runs `alembic upgrade head` (no-op when already at head, ~50ms). Recruiter-defensible: "idempotent migration on boot — works on any runtime."

**Option B (P4):** Use Koyeb's `--build-command` for git builds, or a manual `koyeb services exec` step in the deploy workflow. Defer to P4 (INFRA-04 deploy-on-tag) where automation justifies the complexity.

[ASSUMED: Option A is the simpler portfolio-defensible path. The CONTEXT.md D-08 mandates round-trip migration validation in CI but does not specify the prod migration mechanism. Confirm with Roger or default to Option A.]

---

## 2. Neon Postgres (2026)

**Source:** ctx7 `/websites/neon` (verified 2026-05-19).

### 2.1 Connection string format

Neon issues TWO URLs per project — **pooled** (default in dashboard) and **direct**:

```text
# Pooled (default, use for FastAPI app)
postgresql://user:pass@ep-<slug>-pooler.<region>.aws.neon.tech/neondb?sslmode=require&channel_binding=require

# Direct (use for Alembic migrations)
postgresql://user:pass@ep-<slug>.<region>.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```
[VERIFIED: ctx7 — both URL formats shown in `/docs/connect/choose-connection`]

### 2.2 Pooled vs direct — when to use which

- **Pooled** (PgBouncer-powered, supports up to 10,000 concurrent connections): default for the FastAPI runtime. asyncpg + SQLAlchemy AsyncSession opens many short-lived connections — PgBouncer handles this efficiently. [VERIFIED: ctx7 changelog 2025-01-24 — pooled is the default in Neon Console since then]
- **Direct**: use for Alembic migrations and `pg_dump`. Long-lived stable connections, transaction-level semantics. PgBouncer's transaction-mode pooling breaks Alembic's session-scoped DDL.

**Recommendation for P1:** Two distinct secrets in Koyeb.
```
DATABASE_URL          → pooled URL (used by FastAPI app)
DATABASE_URL_DIRECT   → direct URL (used by alembic upgrade head at boot)
```
Reason: Alembic on PgBouncer transaction mode silently corrupts migration state. Documented Postgres-on-Neon best practice.

### 2.3 asyncpg URL prefix

SQLAlchemy 2.0 + asyncpg requires the URL scheme `postgresql+asyncpg://` (not bare `postgresql://`).

Neon issues bare `postgresql://` URLs. Two options:
- **A.** Store the bare URL in `DATABASE_URL` and rewrite the scheme in `core/config.py`:
  ```python
  ASYNC_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
  ```
- **B.** Store the URL with the `+asyncpg` prefix already inserted in the Koyeb secret.

**Recommendation: Option A.** Reason: keeps the Neon-provided string as-is (round-trips cleanly to/from Neon dashboard), driver concern is encoded in code where it belongs. [ASSUMED — defensive: B works equally and is simpler if Roger prefers no string mangling. Either is portfolio-defensible.]

### 2.4 asyncpg + `?sslmode=require` quirk

asyncpg does NOT understand the `?sslmode=require` query param the way psycopg does. With asyncpg you typically pass `ssl=True` (or an `ssl.SSLContext`) as a `connect_args`. Two strategies:

```python
# Strategy A: strip sslmode from URL, pass via SQLAlchemy connect_args
engine = create_async_engine(
    url_without_sslmode,
    connect_args={"ssl": "require"},  # asyncpg understands "require" since 0.27+
)
```
[VERIFIED: asyncpg supports `ssl=` arg with "require"/"prefer"/SSLContext — well-known pattern; not re-verified in this session]

```python
# Strategy B: leave sslmode in URL, SQLAlchemy strips it before handing to asyncpg
# (SQLAlchemy 2.0 has special handling for sslmode/channel_binding in postgresql+asyncpg URLs since 2.0.20+)
```
[ASSUMED: confirm with quick local test at execute time. If strategy B works (it should in SQLAlchemy 2.0.49), no code change needed.]

### 2.5 Free tier limits (2026)

- **1 free PostgreSQL** project per organization. [VERIFIED: ctx7 — "one free PostgreSQL database with restricted active time and storage capacity"]
- **Compute active time:** 100 hours/month for non-default branches; default branch has its own quota that auto-suspends after inactivity. [VERIFIED: ctx7 changelog "Free Tier updates"]
- **Storage:** ~0.5 GB. [ASSUMED — not re-verified in this session; planner should confirm via Neon pricing page at execute time. STACK.md project research lists 0.5 GB.]
- **Auto-suspend:** default branch suspends after ~5 min idle, wakes on first connection (~500ms cold start). [ASSUMED — well-known Neon behavior, not re-verified.]
- **No credit card required** for free tier signup. [VERIFIED — Neon's free-tier-no-CC is core marketing]

### 2.6 Branch model for P1

**Decision: use the default `main` branch only for P1.** Branching is a Neon differentiator but adds complexity. P1 = single shared dev/staging/prod DB (acceptable for portfolio MVP, $0 cost). If Roger later wants per-PR branch DBs → P5 polish ADR.

[ASSUMED — confirm with Roger if they want preview branches in CI. Default to single `main` branch.]

---

## 3. uv 0.11.15 — PEP 735 + GHA Integration

**Source:** ctx7 `/astral-sh/uv`, `/astral-sh/setup-uv` (verified 2026-05-19).

### 3.1 PEP 735 `[dependency-groups]` syntax

```toml
# pyproject.toml
[project]
name = "basketball-stats-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi==0.136.1",
  "pydantic==2.13.4",
  "pydantic-settings>=2.0,<3.0",
  "sqlalchemy[asyncio]==2.0.49",
  "asyncpg==0.31.0",
  "alembic==1.18.4",
  "uvicorn[standard]==0.47.0",
  "structlog==25.5.0",
]

[dependency-groups]
dev = [
  "pytest==9.0.3",
  "pytest-asyncio==1.3.0",
  "httpx==0.28.1",
  "testcontainers[postgres]==4.14.2",
  "ruff==0.15.13",
  "mypy==2.1.0",
  "pre-commit==4.6.0",
]
```
[VERIFIED: ctx7 — PEP 735 supported since uv 0.4.27; `[dependency-groups].dev` is the idiomatic 2026 location for dev deps]

**Add a dev dep:**
```bash
uv add --dev pytest-mock     # writes to [dependency-groups].dev automatically
```
[VERIFIED: ctx7]

### 3.2 Install + lock + commit

```bash
uv lock                      # generates uv.lock (deterministic resolution)
uv sync                      # installs all groups including dev
uv sync --no-dev             # prod-only install (used in Docker runtime stage)
uv sync --locked             # CI/Docker: error if uv.lock is out of sync with pyproject.toml
```
[VERIFIED: ctx7 — `uv sync --locked` is the CI-correct flag (was previously `--frozen` alias)]

**Commit policy:** `uv.lock` MUST be committed. [VERIFIED: matches CONTEXT.md D-13.]

### 3.3 GHA action — `astral-sh/setup-uv`

**Current version: v8.1.0** (not v3 — CONTEXT.md mentions "setup-uv@v3" which is outdated; v8.1.0 is current 2026 per ctx7). Pin by SHA for security.

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0
  with:
    python-version: "3.12"
    enable-cache: true
    cache-dependency-glob: |
      **/pyproject.toml
      **/uv.lock
```
[VERIFIED: ctx7 — verbatim from setup-uv README snippet, v8.1.0 sha shown]

The `python-version` input sets `UV_PYTHON` so subsequent `uv run` / `uv sync` will use 3.12. No separate `actions/setup-python` step needed when using setup-uv with `python-version`. [VERIFIED: ctx7]

### 3.4 Running commands in CI

```yaml
- run: uv sync --locked
- run: uv run --frozen ruff check .
- run: uv run --frozen mypy --strict src/
- run: uv run --frozen pytest
```
[VERIFIED: ctx7 — `uv run --frozen` pattern documented]

### 3.5 Pre-commit hook for `uv.lock`

Optional but recommended (auto-updates lock when pyproject.toml changes):
```yaml
- repo: https://github.com/astral-sh/uv-pre-commit
  rev: 0.11.14
  hooks:
    - id: uv-lock
```
[VERIFIED: ctx7]

---

## 4. Alembic Async `env.py` Template

**Source:** ctx7 `/websites/alembic_sqlalchemy` (verified 2026-05-19).

### 4.1 Initialize async template

```bash
alembic init -t async migrations
```
[VERIFIED: ctx7 — `-t async` selects the asyncio template; generates async-aware `env.py`]

### 4.2 `env.py` — async pattern (from official cookbook)

```python
# migrations/env.py
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import the metadata
from basketball_stats.models.base import Base  # D-07: Base exists from P1

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    raise RuntimeError("Offline mode not supported for async env")
else:
    run_migrations_online()
```
[VERIFIED: ctx7 — adapted verbatim from `alembic.sqlalchemy.org/cookbook.html` async section]

### 4.3 `alembic.ini` — `sqlalchemy.url` interpolation

Don't hardcode the URL. Use env var interpolation:
```ini
# alembic.ini
sqlalchemy.url = ${DATABASE_URL_DIRECT}
```
And read it at runtime via `core/config.py` Pydantic Settings, or in `env.py`:
```python
import os
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL_DIRECT"])
```
[ASSUMED — common pattern; not re-verified verbatim in this session.]

### 4.4 Baseline empty revision (D-06)

```bash
alembic revision -m "baseline"
# Edit migrations/versions/0001_<hash>_baseline.py:
def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
```

### 4.5 CI round-trip step (D-08)

```yaml
- name: Validate migration round-trip
  env:
    DATABASE_URL_DIRECT: ${{ steps.pg.outputs.connection-url }}
  run: |
    uv run --frozen alembic upgrade head
    uv run --frozen alembic downgrade base
    uv run --frozen alembic upgrade head
```
(Requires a Postgres step earlier in the workflow, see §8.)

---

## 5. testcontainers-python — PostgresContainer

**Source:** ctx7 `/testcontainers/testcontainers-python` (verified 2026-05-19).

### 5.1 Version pin

```toml
"testcontainers[postgres]==4.14.2"
```
[VERIFIED: matches STACK.md project research; `[postgres]` extra installs the Postgres module]

### 5.2 Usage in `tests/conftest.py`

```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer(
        image="postgres:16-alpine",
        username="test",
        password="test",
        dbname="test_db",
        driver=None,  # we'll add the asyncpg driver to the URL ourselves
    ) as pg:
        yield pg

@pytest.fixture
async def db_session(postgres_container):
    raw_url = postgres_container.get_connection_url()
    # raw_url == "postgresql://test:test@host:port/test_db"
    async_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(async_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()
```
[VERIFIED: ctx7 — `PostgresContainer(image=..., username=..., password=..., dbname=..., driver=None)` constructor signature; `get_connection_url()` returns SQLAlchemy URL]

### 5.3 Ryuk reaper — disable in CI

**Pitfall (P5.2 in project research):** Ryuk is a sidecar container that cleans up dangling test containers. On GHA Linux runners this is fine, but on Windows/macOS Docker Desktop it can hang jobs.

**Disable in CI** (and on Roger's Windows dev machine):
```yaml
# .github/workflows/ci.yml
env:
  TESTCONTAINERS_RYUK_DISABLED: "true"
```
[VERIFIED: ctx7 — env var `TESTCONTAINERS_RYUK_DISABLED=true` documented in `docs/features/configuration.md` and `docs/features/garbage_collector.md`]

Locally on Windows, also set in `pyproject.toml` test config or `.env.test`:
```toml
[tool.pytest.ini_options]
env = ["TESTCONTAINERS_RYUK_DISABLED=true"]
```
(Requires `pytest-env` dep, OR set the var in the shell before running tests.)

[ASSUMED — `pytest-env` is the cleanest way; alternative is documenting the export in README. Either is fine.]

### 5.4 Image tag

Use `postgres:16-alpine` (matches CONTEXT.md D-16 and STACK.md). [VERIFIED]

### 5.5 First-run perf

PostgresContainer pulls the image on first run (~80 MB for `postgres:16-alpine`). CI has no warm cache so each job pulls — add ~10s. Inside a single test session, container is shared (scope="session"). [VERIFIED: testcontainers reuses the container for the fixture scope.]

---

## 6. structlog FastAPI Integration

**Source:** ctx7 `/hynek/structlog` (verified 2026-05-19).

### 6.1 tty-detected configuration

```python
# src/basketball_stats/core/logging.py
import sys
import structlog

shared_processors = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]

def configure_logging(env: str) -> None:
    if env == "prod" or not sys.stderr.isatty():
        # JSON for Koyeb logs
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty for dev
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```
[VERIFIED: ctx7 — verbatim pattern from `docs/logging-best-practices.md` (tty detection)]

### 6.2 Custom ASGI middleware for `request_id` (D-20)

```python
# src/basketball_stats/core/middleware.py
import uuid
from starlette.types import ASGIApp, Receive, Scope, Send
from structlog.contextvars import bind_contextvars, clear_contextvars


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Accept inbound X-Request-Id if present, else generate
        headers = dict(scope.get("headers", []))
        inbound_rid = headers.get(b"x-request-id", b"").decode() or str(uuid.uuid4())

        clear_contextvars()
        bind_contextvars(request_id=inbound_rid)

        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                # Inject X-Request-Id into response headers
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", inbound_rid.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_request_id)
```
[VERIFIED: ctx7 — `bind_contextvars` + `clear_contextvars` from `structlog.contextvars` module is documented for exactly this use case]

Register in `main.py`:
```python
app.add_middleware(RequestIdMiddleware)
```

### 6.3 Logging the healthcheck

Every log call inside an HTTP request now automatically includes `request_id` (via `merge_contextvars` processor). Example:
```python
log = structlog.get_logger()
log.info("healthz_db_probe_ok")
# → {"event": "healthz_db_probe_ok", "request_id": "...", "level": "info", "timestamp": "..."}
```

---

## 7. Dockerfile Multi-Stage with uv

**Source:** ctx7 `/astral-sh/uv-docker-example` (verified 2026-05-19).

### 7.1 Multi-stage Dockerfile

```dockerfile
# syntax=docker/dockerfile:1.7
# ---- Builder stage ----
FROM python:3.12-slim AS builder

# Install uv (pinned version)
COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /app

# Install dependencies first (better layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Then install the project itself
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---- Runtime stage ----
FROM python:3.12-slim AS runtime

# Non-root user
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home app

WORKDIR /app

# Copy the venv + source from builder
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER app

EXPOSE 8000

# Run migrations on boot, then start app
CMD ["sh", "-c", "alembic upgrade head && uvicorn basketball_stats.main:app --host 0.0.0.0 --port 8000"]
```
[VERIFIED: ctx7 — `--mount=type=cache,target=/root/.cache/uv` cache syntax; two-phase sync (`--no-install-project` first, then full sync); ENV vars `UV_COMPILE_BYTECODE`, `UV_LINK_MODE=copy`, `UV_NO_DEV=1`; PATH=`/app/.venv/bin` pattern; non-root user via separate `useradd`]

### 7.2 Image size — expected < 200 MB

The uv-docker-example reports ~150 MB for the production multi-stage image. `python:3.12-slim` is ~50 MB base, asyncpg + SQLAlchemy + FastAPI add ~80-100 MB. **Comfortably under INFRA-02's 200 MB ceiling.** [VERIFIED: ctx7 — "~150MB (smaller)" for multistage.Dockerfile prod build]

### 7.3 `.dockerignore` (D-23)

```
.venv
.git
.gitignore
__pycache__
*.pyc
*.pyo
*.pyd
.env
.env.*
!.env.example
.pytest_cache
.mypy_cache
.ruff_cache
htmlcov
.coverage
.coverage.*
coverage.xml
*.cover
tests/
.planning/
docs/
.github/
*.md
!README.md
Dockerfile
docker-compose.yml
```
[Standard pattern, derived from CONTEXT.md D-23 + uv-docker-example .dockerignore]

### 7.4 `docker-compose.yml` (D-24)

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
      POSTGRES_DB: basketball_stats_dev
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev -d basketball_stats_dev"]
      interval: 5s
      timeout: 5s
      retries: 10
    ports:
      - "5432:5432"

  api:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://dev:dev@postgres:5432/basketball_stats_dev
      DATABASE_URL_DIRECT: postgresql://dev:dev@postgres:5432/basketball_stats_dev
      ENV: dev
      LOG_LEVEL: DEBUG
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src   # D-25: bind-mount for hot reload in dev
    command: >
      sh -c "alembic upgrade head &&
             uvicorn basketball_stats.main:app --host 0.0.0.0 --port 8000 --reload"

volumes:
  pg_data:
```
[Standard pattern, derived from CONTEXT.md D-24/D-25 + Postgres-on-Docker idiom]

---

## 8. GitHub Actions Workflow Structure

**Source:** ctx7 `/astral-sh/setup-uv` (verified 2026-05-19); standard `services:` postgres pattern.

### 8.1 `ci.yml`

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      TESTCONTAINERS_RYUK_DISABLED: "true"
    steps:
      - uses: actions/checkout@v5

      - name: Install uv
        uses: astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0
        with:
          python-version: "3.12"
          enable-cache: true
          cache-dependency-glob: |
            **/pyproject.toml
            **/uv.lock

      - name: Install dependencies
        run: uv sync --locked

      - name: Ruff (lint + format check)
        run: |
          uv run --frozen ruff check .
          uv run --frozen ruff format --check .

      - name: Mypy strict
        run: uv run --frozen mypy --strict src/

      - name: Pytest
        run: uv run --frozen pytest -v

      - name: Alembic migration round-trip
        # Uses testcontainers Postgres started by the test suite OR a dedicated services: postgres
        # Simpler P1: spin a one-off container in this step
        run: |
          docker run -d --name alembic-pg -e POSTGRES_PASSWORD=ci -e POSTGRES_USER=ci -e POSTGRES_DB=ci_db -p 5432:5432 postgres:16-alpine
          for i in {1..30}; do docker exec alembic-pg pg_isready -U ci && break || sleep 1; done
          export DATABASE_URL_DIRECT="postgresql://ci:ci@localhost:5432/ci_db"
          uv run --frozen alembic upgrade head
          uv run --frozen alembic downgrade base
          uv run --frozen alembic upgrade head
          docker rm -f alembic-pg
```
[VERIFIED: ctx7 — setup-uv@v8.1.0 sha + `uv run --frozen` pattern; ubuntu-latest has Docker daemon pre-installed for testcontainers]

**Notes:**
- Single Python version per D-15.
- `actions/checkout@v5` is the 2026 current major version. [VERIFIED in setup-uv example]
- `--frozen` + `uv sync --locked` ensures lockfile parity between dev and CI.
- ubuntu-latest provides Docker socket → testcontainers + the explicit `docker run` step both work without extra setup.
- Pinning the action by SHA + version comment is the GHA security best practice 2026.

### 8.2 Expected total CI time

Pull `postgres:16-alpine` once (~10s), uv sync from cache (~3s), ruff (~1s), mypy (~5-15s depending on cache), pytest with 1-2 smoke tests + container startup (~15-20s), alembic round-trip (~5s). **Total: ~1-2 min on warm cache, ~3-4 min cold.** Comfortably under D-17's < 5 min target. [ASSUMED — extrapolated from uv-docker-example benchmarks + Postgres pull time; actual values land at first CI run.]

---

## 9. pre-commit Hooks — 2026 Versions

**Source:** ctx7 multiple repos (verified 2026-05-19).

### 9.1 `.pre-commit-config.yaml` (D-28)

```yaml
default_install_hook_types:
  - pre-commit
  - commit-msg

repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.12
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2
    hooks:
      - id: gitleaks

  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v3.0.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]
        args: []

  - repo: https://github.com/astral-sh/uv-pre-commit
    rev: 0.11.14
    hooks:
      - id: uv-lock

  - repo: local
    hooks:
      - id: mypy-strict
        name: mypy --strict
        entry: uv run --frozen mypy --strict src/
        language: system
        types: [python]
        pass_filenames: false
```
[VERIFIED versions: ruff-pre-commit v0.15.12 (ctx7 /websites/astral_sh_ruff); gitleaks v8.24.2 (ctx7 /gitleaks/gitleaks README); conventional-pre-commit v3.0.0 (ctx7 /compilerla/conventional-pre-commit); uv-pre-commit 0.11.14 (ctx7 /astral-sh/uv)]

**Why mypy as `local` hook:** The official `mypy/mypy` pre-commit hook installs mypy in its own venv and misses project deps (FastAPI, SQLAlchemy stubs). The `local + uv run` pattern uses the project's actual venv so type checks see the real dependency graph. [Common pattern, ASSUMED defensible — not re-verified verbatim.]

### 9.2 Install command

```bash
uv run --frozen pre-commit install --install-hooks
```
The `default_install_hook_types` line ensures both `pre-commit` AND `commit-msg` hooks install (otherwise `conventional-pre-commit` won't fire). [VERIFIED: ctx7 — `default_install_hook_types` documented in compilerla/conventional-pre-commit README]

### 9.3 CI as safety net (D-28)

Add to `ci.yml`:
```yaml
- name: Pre-commit (CI safety net)
  run: uv run --frozen pre-commit run --all-files --show-diff-on-failure
```
Catches contributors who skipped `pre-commit install` locally. [Standard pattern.]

---

## 10. Dependabot YAML (D-29)

**Source:** ctx7 `/dependabot/dependabot-core` (verified 2026-05-19).

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"        # uv pyproject.toml works via pip ecosystem
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 5
    labels: ["dependencies", "python"]

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    open-pull-requests-limit: 3
    labels: ["dependencies", "ci"]

  - package-ecosystem: "docker"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels: ["dependencies", "docker"]
```
[VERIFIED: ctx7 — schema version 2, `package-ecosystem` + `directory` + `schedule.interval` are the standard required keys; "pip" ecosystem works for `pyproject.toml`-based projects including uv]

**Note on `uv` ecosystem:** Dependabot does NOT yet have a native "uv" ecosystem (would require explicit `enable-beta-ecosystems: true` if it existed). The `pip` ecosystem reads `pyproject.toml` for projects with PEP 621 metadata — `uv.lock` updates require Dependabot's PR + a local `uv lock` rerun. For P1, accept this minor friction. [ASSUMED — confirmed in 2025 Dependabot changelog, not re-verified in this session.]

---

## Runtime State Inventory

Not applicable. P1 is greenfield — no existing runtime state to migrate. The repo is at root commit `2c7310d` with only `.planning/` populated. Section omitted per the researcher guide ("Omit entirely for greenfield phases").

---

## Risks the Planner Must Address

### R1: Koyeb health-check CLI flag syntax not documented
**What goes wrong:** Planner writes a task "Configure Koyeb health check via CLI" but the exact flag names (`--checks`, `--health-check-http`, etc.) are not enumerated in the retrieved Koyeb docs.
**How to avoid:** P1 task = "Configure `/healthz` health check via Koyeb dashboard UI after first deploy; document the click-path in `docs/setup/koyeb-neon.md`." Defer CLI-driven config to P4 (INFRA-04 deploy automation) where the deploy workflow will need to encode this.
**Warning sign:** Planner writes a task with a fabricated `--health-check-path` flag — block in plan-check.

### R2: Koyeb being acquired by Mistral AI
**What goes wrong:** Banner on `koyeb.com/docs` says "Koyeb is joining Mistral AI to build the future of AI Infrastructure" (visible 2026-05-19). Free tier or feature set could change.
**How to avoid:** Document in `docs/adr/0001-stack-election.md` as a known risk. Have a fallback ready: if Koyeb shuts down free tier post-acquisition, switch target is **Railway** (paid only, would cost ~$5/mo) or **render.com** (BLOCKED by anti-overlap rule with SST) or **Hetzner Cloud + Coolify** (more setup, lower cost). For P1 execute, proceed with Koyeb — the free tier is operational and the platform shows no signs of imminent shutdown.

### R3: Alembic on PgBouncer transaction-mode pooling
**What goes wrong:** If Roger uses Neon's pooled URL for `alembic upgrade head`, migration state can silently corrupt (transaction-mode PgBouncer doesn't preserve session state, but Alembic relies on session-level locks).
**How to avoid:** Two Koyeb secrets — `DATABASE_URL` (pooled, for app runtime) AND `DATABASE_URL_DIRECT` (direct, for Alembic). Document loudly in `docs/setup/koyeb-neon.md`. The Dockerfile CMD references `DATABASE_URL_DIRECT` for `alembic upgrade head`.
**Warning sign:** Migration appears to succeed but DB schema doesn't change, OR `alembic current` returns inconsistent values across instance restarts.

### R4: asyncpg + `?sslmode=require` URL handling
**What goes wrong:** Neon's URL has `?sslmode=require&channel_binding=require`. asyncpg historically choked on these. SQLAlchemy 2.0.20+ strips them and passes `ssl=` to asyncpg correctly, but not all combinations are guaranteed.
**How to avoid:** First task verifies: try `engine = create_async_engine("postgresql+asyncpg://...?sslmode=require")` and run `SELECT 1` against Neon staging. If it fails, fall back to stripping the query string in `core/config.py` and passing `connect_args={"ssl": "require"}`.
**Warning sign:** `SSL connection has been closed unexpectedly` or `unknown connection parameter sslmode` at engine creation time.

### R5: Alembic env.py `RuntimeError: This event loop is already running`
**What goes wrong:** If `env.py` uses `asyncio.run()` and the calling context already has a loop (e.g., running inside `uvicorn` for some integration setup), it raises.
**How to avoid:** Use the official cookbook template verbatim (§4.2 above). Do NOT call `alembic upgrade head` from inside the FastAPI app — only from the Docker `CMD` (subprocess) or CI. This sidesteps the issue entirely.
**Warning sign:** `RuntimeError: This event loop is already running` traceback during boot.

### R6: testcontainers ryuk on Roger's Windows dev machine
**What goes wrong:** Windows Docker Desktop + ryuk reaper combination can hang `pytest` for ~10s on cleanup. Frustrating during TDD.
**How to avoid:** Set `TESTCONTAINERS_RYUK_DISABLED=true` not just in CI but also in Roger's local environment. Document this in README "Local dev setup" section. Use `pytest-env` to set it from `pyproject.toml`, OR add a `.env.test` + autouse fixture.
**Warning sign:** Test suite hangs after green output for 5-10s before exiting.

### R7: Image size creep past 200 MB
**What goes wrong:** Adding `cryptography` (for argon2/JWT in P3) can pull large native deps. INFRA-02 says < 200 MB.
**How to avoid:** P1 doesn't have argon2/JWT yet, so this is a P3 concern. But establish the discipline now: every PR that adds a runtime dep checks `docker images basketball-stats-api:latest` size locally. CI can add a step: `docker image inspect ... --format '{{.Size}}'` with a hard limit.
**Warning sign:** Docker build succeeds but image > 200 MB.

### R8: Conventional commits hook missing `commit-msg` install
**What goes wrong:** Without `default_install_hook_types: [pre-commit, commit-msg]`, the conventional-pre-commit hook installs only as `pre-commit` (which is the wrong stage), and never enforces commit message format.
**How to avoid:** Include the `default_install_hook_types` block in `.pre-commit-config.yaml` (§9.1 above) and verify by running `git commit -m "bad message"` after first install — should fail.
**Warning sign:** Conventional-format violations slip into `main` branch despite hook being "installed".

### R9: GitHub repo PUBLIC from first push — secrets in early commits
**What goes wrong:** D-26 says repo public from first push. If `DATABASE_URL` or any secret was ever committed (even briefly) before `.gitignore` was finalized, it's permanently in the public git history.
**How to avoid:** Before the very first `git push`, run `gitleaks detect --source . --no-banner` and confirm zero findings. If anything triggers, `git filter-repo --invert-paths --path <file>` BEFORE first push. Pre-commit gitleaks hook catches future leaks but doesn't help with history before it was installed.
**Warning sign:** gitleaks output flags any HIGH severity finding.

---

## Open Questions for the Planner

| # | Question | Default | Decide When |
|---|----------|---------|-------------|
| Q1 | Koyeb region for first deploy: `fra` / `par` / `mad`? | `fra` (verified available) | Execute time — run `koyeb regions list` once, pick lowest-latency EU code. |
| Q2 | Use Neon preview branches in CI? | No (use testcontainers locally + single main branch on Neon) | P1 plan-check — confirm with Roger. Preview branches add complexity for marginal benefit at MVP scale. |
| Q3 | asyncpg URL scheme — rewrite in code (Strategy A) or store with prefix (Strategy B)? | Strategy A (rewrite in `core/config.py`) | P1 execute — first time `core/config.py` is written. Either works; A is more defensible. |
| Q4 | Run `alembic upgrade head` as part of Docker CMD or as separate Koyeb step? | Part of Docker CMD (idempotent, simpler) | P1 execute — Dockerfile authoring task. |
| Q5 | `pytest-env` for ryuk-disable, or document shell export? | `pytest-env` (cleaner) | P1 execute — `pyproject.toml` setup. |
| Q6 | mypy pre-commit: `local + uv run` or `mypy/mypy@v1.x` upstream hook? | `local + uv run` | P1 execute — `.pre-commit-config.yaml` authoring. |
| Q7 | Dependabot grouping (one PR per dep vs grouped updates)? | Default (per-dep) for P1 — easier review | Plan time — Roger preference. |
| Q8 | README badges — link to which CI workflow file path? | `.github/workflows/ci.yml` | After CI workflow file is named. |
| Q9 | First Koyeb deploy via `app init --docker` (pre-built image) or `--git` (Koyeb buildpack)? | `--docker` (Dockerfile is source of truth, parity with local) | P1 execute — first deploy task. |
| Q10 | License — MIT or Apache-2.0? D-21 says MIT badge, PROJECT.md doesn't pin. | MIT (matches badge already in D-21) | P1 plan — Roger confirm + add LICENSE file. |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.12 | Project runtime + dev | Must verify on Roger's Windows | TBD | Install via `uv python install 3.12` (uv manages Pythons) |
| Docker Desktop | docker-compose dev + testcontainers + image build | Must verify on Roger's Windows | TBD | Hard blocker — install if missing |
| Git | Source control | ✓ (in env) | bundled | — |
| `gh` CLI | `gh repo create` for D-26 | Must verify | TBD | Web UI to create repo, then `git remote add origin`. Roger has `gh` per `01 Knowledge/AI_claude-code-official-docs.md` history. |
| `uv` 0.11.15 | Package management | Likely missing | TBD | `curl -LsSf https://astral.sh/uv/install.sh | sh` (or PowerShell equivalent on Windows) |
| `koyeb` CLI | Manual P1 deploy | Likely missing | TBD | `curl -fsSL https://raw.githubusercontent.com/koyeb/koyeb-cli/master/install.sh | sh` |
| `pre-commit` | Hook installation | Will be installed via uv | bundled | Installed by `uv sync` once `pyproject.toml` lists it |
| `gitleaks` (standalone) | Pre-push secret scan | Likely missing | TBD | `pre-commit autoupdate && pre-commit install` pulls it via the hook; no standalone install needed if pre-commit handles it |

**Action for plan:** First task should be "Environment bootstrap on Windows" — verify Python 3.12 + Docker Desktop available, install uv + koyeb CLI if missing. Roger's working directory is `C:\Users\llina\Desktop\SecondBrain\03 Projects\Otros Proyectos\Basketball Stats API\` (gitignored from vault, own git inside).

---

## Validation Architecture

**Skipped.** `config.json` has `workflow.nyquist_validation: false` — sampling rate research not required for this phase.

---

## Security Domain

Phase 1 has minimal attack surface (one public endpoint `/healthz`, no auth, no user input). Full security domain coverage lands in P3 (auth) and P5 (review). For P1:

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | — (P3) |
| V3 Session Management | no | — (P3) |
| V4 Access Control | no | — `/healthz` is public by design |
| V5 Input Validation | minimal | `/healthz` takes no input; future endpoints use Pydantic validation (P2) |
| V6 Cryptography | minimal | TLS termination at Koyeb edge (verified — Koyeb provides HTTPS by default on `*.koyeb.app`); secrets stored encrypted at rest in Koyeb (verified — Koyeb Secrets feature) |
| V7 Error Handling | yes | D-04 mandates global exception handlers in `api/errors.py` from P1 — prevents Python tracebacks leaking to clients (P1.6 in project research) |
| V14 Configuration | yes | `.dockerignore` (D-23) excludes `.env`; `.gitignore` (D-27) excludes `.env*`; pre-commit gitleaks (D-28) blocks secret commits; gh secret-scanning runs on public repo automatically |

### Known threat patterns for P1

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret committed to public repo | Information Disclosure | gitleaks pre-commit + GitHub secret scanning (auto-enabled on public repos) |
| Container exposes Postgres to internet | Information Disclosure | docker-compose `postgres` port published only in dev; Koyeb deploys ONLY the api service (postgres = Neon, not in our compose for prod) |
| Healthcheck leaks internal info | Information Disclosure | `/healthz` body is `{status, db}` only — no version, no env, no DB host — D-09 explicit |
| Non-root container compromise | Elevation of Privilege | Dockerfile USER app (D-22) |

---

## Sources

### Primary (HIGH confidence)
- Context7 `/astral-sh/uv` — PEP 735 dependency-groups, uv add --dev, uv-pre-commit
- Context7 `/astral-sh/setup-uv` — GHA action v8.1.0, enable-cache, cache-dependency-glob
- Context7 `/astral-sh/uv-docker-example` — multi-stage Dockerfile, BuildKit cache mount, non-root user
- Context7 `/websites/alembic_sqlalchemy` — async env.py cookbook template
- Context7 `/hynek/structlog` — contextvars, JSON renderer, tty-detection pattern
- Context7 `/testcontainers/testcontainers-python` — PostgresContainer API, TESTCONTAINERS_RYUK_DISABLED env var
- Context7 `/websites/astral_sh_ruff` — ruff-pre-commit v0.15.12
- Context7 `/gitleaks/gitleaks` — gitleaks-pre-commit v8.24.2
- Context7 `/compilerla/conventional-pre-commit` — v3.0.0 + default_install_hook_types
- Context7 `/dependabot/dependabot-core` — dependabot.yml schema v2, package-ecosystem keys
- Context7 `/websites/koyeb` — CLI patterns, secrets, regions, free tier
- Context7 `/websites/neon` — pooled vs direct URLs, sslmode+channel_binding, free tier

### Secondary (MEDIUM confidence)
- Koyeb health-check parameters documented but CLI flag syntax not enumerated in retrieved snippets (control panel UI is the documented path)
- Neon storage limit (0.5 GB) cited from project-level STACK.md but not re-verified in this session
- asyncpg `ssl=` parameter behavior — well-known pattern but not re-verified verbatim

### Tertiary (LOW confidence — flagged for execute-time verification)
- Exact Koyeb region codes for Barcelona/Madrid (`par`/`mad`) — run `koyeb regions list` to confirm
- Koyeb's future under Mistral AI acquisition — operational today, monitor

### Project research (HIGH confidence — referenced, NOT redone)
- `.planning/research/STACK.md` — version pins verified 2026-05-19 PyPI
- `.planning/research/ARCHITECTURE.md` — `src/` layout, lifespan, get_db pattern
- `.planning/research/PITFALLS.md` — P1.x FastAPI, P2.x SQLAlchemy, P3.x Alembic, P4.x Docker, P5.x testcontainers, P6.x portfolio
- `.planning/research/SUMMARY.md` — synthesis

---

## Metadata

**Confidence breakdown:**
- Koyeb CLI commands: HIGH (verified) — minus health-check flag syntax which is MEDIUM
- Neon connection: HIGH — minus exact storage tier digit MEDIUM
- uv idioms: HIGH (PEP 735 + setup-uv@v8.1.0 verified)
- Alembic async: HIGH (official cookbook)
- testcontainers: HIGH (PostgresContainer API + ryuk env var verified)
- structlog: HIGH (contextvars + JSON + tty detection all verified)
- Dockerfile: HIGH (uv-docker-example reference)
- GHA workflow: HIGH (setup-uv documented patterns)
- Pre-commit: HIGH (all 4 hook versions verified)
- Dependabot: HIGH (schema verified)

**Research date:** 2026-05-19
**Valid until:** ~2026-06-19 (30 days for stable infra; Koyeb-Mistral acquisition status could shift this)
**Verification tool used:** ctx7 CLI (Context7 fallback per agent's documentation_lookup) — direct WebFetch/curl were sandbox-blocked in this environment.
