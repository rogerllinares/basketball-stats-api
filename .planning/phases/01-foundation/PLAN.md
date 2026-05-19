---
phase: 1
phase_name: foundation
created: 2026-05-19
planner: Claude (gsd-phase-planner)
task_count: 22
wave_count: 7
success_criteria: 5
requirements: 8
requirement_ids: [INFRA-01, INFRA-02, INFRA-03, INFRA-05, OBS-02, OBS-03, OBS-07, TEST-01]
inputs:
  - .planning/phases/01-foundation/01-CONTEXT.md
  - .planning/phases/01-foundation/RESEARCH.md
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
  - .planning/PROJECT.md
  - .planning/STATE.md
  - .planning/research/{STACK,ARCHITECTURE,PITFALLS,SUMMARY}.md
commits: conventional
budget_days: 2-3
---

# Phase 1: Foundation — Executable Plan

## Goal

Skeleton end-to-end deployable: container builds, GHA CI green (ruff + mypy --strict + pytest), Koyeb serves the image at a public URL, Neon Postgres connected, `GET /healthz` returns `{status:ok, db:ok}` with a real `SELECT 1`. Zero business logic, zero domain entities. Every piece of the pipeline (build → test → migrate → deploy → healthcheck) proven without writing a single feature.

## Success Criteria

| # | Criterion | Verified by task(s) |
|---|-----------|---------------------|
| SC1 | `docker compose up` brings up `api + postgres` locally; `curl localhost:8000/healthz` returns `{"status":"ok","db":"ok"}` with real `SELECT 1`. | Tasks 11, 14, 15 (local smoke) |
| SC2 | `git push` to `main` triggers GHA workflow running `ruff check` + `mypy --strict` + `pytest`, all green, under 5 min. | Tasks 16, 17, 21 |
| SC3 | Koyeb serves the image at a public URL; `curl <url>/healthz` confirms Neon connected. | Tasks 18, 19, 20 |
| SC4 | README shows badges: CI status, ruff, mypy, Python 3.12, license MIT. | Task 22 |
| SC5 | Structured JSON logs appear in Koyeb logs with `request_id` per request. | Tasks 9, 10, 20 |

## Out of Scope (per CONTEXT §Phase Boundary)

- Domain entities (Team, Player, Game, BoxScore, etc.) → Phase 2.
- Public endpoints beyond `/healthz` → Phase 2.
- Auth + JWT → Phase 3.
- Deploy-on-tag automation (`INFRA-04`) → Phase 4. P1 does first deploy manually via `koyeb app init`.
- README stack walkthrough complete (`OBS-04`) → Phase 5. P1 leaves a stub.
- Full ADR set → Phase 5. P1 ships `docs/adr/0001-stack-election.md` only.
- `/readyz` separate from `/healthz` → deferred (D-09).
- OpenTelemetry full stack → v2.

## Dependency Graph

```
Wave 1 (parallel, foundation, no deps):
  T01 env-bootstrap → T02 gitignore+repo → T03 pyproject+lock

Wave 2 (depends on T03):
  T04 src-tree + __init__ docstrings
  T05 core/config.py (Settings)
  T06 core/db.py (async engine + get_db)

Wave 3 (depends on T05, T06):
  T07 models/base.py (Declarative Base, no entities)
  T08 api/errors.py (global exception handlers)
  T09 core/logging.py (structlog tty-detect)
  T10 core/middleware.py (RequestIdMiddleware)

Wave 4 (depends on T07, T08, T09, T10):
  T11 api/v1/health.py + api/v1/deps.py + main.py + lifespan

Wave 5 (depends on T07):
  T12 alembic init -t async + env.py + baseline revision

Wave 6 (depends on T11, T12):
  T13 tests/conftest.py (PostgresContainer fixture)
  T14 tests/unit/test_config.py + tests/integration/test_healthz.py
  T15 Dockerfile + .dockerignore + docker-compose.yml

Wave 7 (depends on T14, T15):
  T16 .pre-commit-config.yaml + install + first cleanup commit
  T17 .github/workflows/ci.yml (ruff + mypy + pytest + migration round-trip)
  T18 docs/setup/koyeb-neon.md (manual deploy walkthrough)
  T19 Neon project + Koyeb secrets (manual, documented)
  T20 First Koyeb deploy + dashboard health-check config
  T21 .github/dependabot.yml
  T22 README.md (badges + minimal sections) + docs/adr/0001-stack-election.md + LICENSE
```

Implicit blockers: tasks T18→T19→T20 are strictly sequential (Koyeb deploy needs Neon URL + Koyeb secrets in place). T16/T17/T21/T22 can run in parallel within Wave 7 once Wave 6 lands.

---

## Tasks

### Task 1: chore(env): bootstrap local dev environment (Python 3.12, uv, koyeb CLI)

**Files:** `.python-version` (created), `SETUP.local.md` (created — gitignored note, NOT committed)
**REQ-IDs:** none direct (precondition for all others)
**Depends on:** none
**What:** Verify Roger's Windows machine has Python 3.12 (or install via `uv python install 3.12`), Docker Desktop running, `gh` CLI authed. Install `uv` (`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`) pinned to 0.11.15 and `koyeb` CLI. Write `.python-version` with `3.12` (one line). Capture install steps to a local-only scratch note (NOT committed — vault `.gitignore` already covers `SETUP.local.md`).
**Why (defense):** Reproducible toolchain — recruiter reads `.python-version` and knows the runtime. D-12.
**Acceptance:**
```powershell
python --version    # 3.12.x
uv --version        # 0.11.15
docker --version    # any
gh auth status      # logged in
koyeb version       # any recent
cat .python-version # 3.12
```
**Estimated commit:** `chore(env): pin python 3.12 via .python-version`

---

### Task 2: chore(repo): exhaustive .gitignore + create public GitHub repo

**Files:** `.gitignore`, `LICENSE` (MIT)
**REQ-IDs:** INFRA-03 (precondition), OBS-07 (license badge)
**Depends on:** T01
**What:** Author exhaustive `.gitignore` per D-27 (`.env*`, `.venv`, `__pycache__`, `*.pyc`, `htmlcov`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `dist/`, `.coverage`, `*.egg-info/`, `.idea/`, `.vscode/`). Add MIT `LICENSE` file with `Copyright (c) 2026 Roger Llinares`. Run `gitleaks detect --source . --no-banner` (via `pre-commit try-repo` or one-off Docker run) before any push to catch accidents. THEN `gh repo create roger-llinares/basketball-stats-api --public --source=. --remote=origin` but DO NOT push yet — first push happens after T22 (so the very first public commit already has README + badges + CI green).
**Why (defense):** D-26 + D-27 + R9 mitigation — public repo from day 1 with zero leak risk. License = MIT badge dependency.
**Acceptance:**
```powershell
gitleaks detect --source . --no-banner   # zero findings
gh repo view roger-llinares/basketball-stats-api  # repo exists, public
git remote -v                            # origin = github
type .gitignore | findstr ".env"         # match
type LICENSE | findstr "MIT"             # match
```
**Estimated commit:** `chore(repo): exhaustive gitignore + MIT license + public github repo`

---

### Task 3: build(uv): pyproject.toml + uv.lock (PEP 621 + PEP 735 dependency-groups)

**Files:** `pyproject.toml`, `uv.lock` (generated)
**REQ-IDs:** INFRA-02 (pin python 3.12), INFRA-03 (lockfile for deterministic CI)
**Depends on:** T01
**What:** Author `pyproject.toml` per RESEARCH §3.1 with `[project]` (name, version 0.1.0, `requires-python = ">=3.12"`), `dependencies` (FastAPI 0.136.1, Pydantic 2.13.4, pydantic-settings, sqlalchemy[asyncio] 2.0.49, asyncpg 0.31.0, alembic 1.18.4, uvicorn[standard] 0.47.0, structlog 25.5.0), `[dependency-groups].dev` (pytest 9.0.3, pytest-asyncio 1.3.0, pytest-env, httpx 0.28.1, testcontainers[postgres] 4.14.2, ruff 0.15.13, mypy 2.1.0, pre-commit 4.6.0). Include `[tool.ruff]` (line-length 100, target-version "py312", select E/F/I/UP/B/SIM), `[tool.mypy]` (strict = true, python_version "3.12"), `[tool.pytest.ini_options]` (testpaths tests, asyncio_mode auto, env `TESTCONTAINERS_RYUK_DISABLED=true` via pytest-env). Then `uv lock`.
**Why (defense):** D-13 + D-14 — single config source, lockfile committed for determinism between Roger / GHA / Koyeb builder.
**Acceptance:**
```powershell
uv sync --locked        # installs everything, exits 0
uv run python -c "import fastapi, pydantic, sqlalchemy, asyncpg, alembic, structlog; print('ok')"
type pyproject.toml | findstr "requires-python"   # ">=3.12"
test -f uv.lock         # exists
```
**Estimated commit:** `build(uv): pyproject + uv.lock with pinned deps (PEP 735 dev group)`

---

### Task 4: feat(skeleton): full architecture tree with empty __init__ docstrings (D-02/D-03)

**Files:** `src/basketball_stats/__init__.py`, `src/basketball_stats/api/__init__.py`, `src/basketball_stats/api/v1/__init__.py`, `src/basketball_stats/api/errors.py` (created Wave 3), `src/basketball_stats/core/__init__.py`, `src/basketball_stats/models/__init__.py`, `src/basketball_stats/schemas/__init__.py`, `src/basketball_stats/services/__init__.py`, `src/basketball_stats/repositories/__init__.py`, `src/basketball_stats/tasks/__init__.py`, `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`
**REQ-IDs:** INFRA-02 (src/ layout)
**Depends on:** T03
**What:** Create `src/basketball_stats/` and all subdirs per ARCHITECTURE.md §1. Each `__init__.py` carries a one-line docstring naming what will live there ("Phase 2: SQLAlchemy 2.0 models — Team, Player, Game, BoxScore, League, Coach"). NO empty subdirs, NO TODO stubs (D-03). Add `[project.scripts]` entry placeholder NOT needed yet. `tests/` split `unit/` + `integration/` (D-05).
**Why (defense):** D-02 recruiter opens repo day 1 and sees Repository+Service pattern in tree before any code. D-03 keeps the first commit honest (no fake files).
**Acceptance:**
```powershell
uv pip install -e .                                  # installs without error (src/ layout works)
uv run python -c "import basketball_stats; print('ok')"
dir src\basketball_stats                             # api, core, models, schemas, services, repositories, tasks
```
**Estimated commit:** `feat(skeleton): src/ layout with full architecture tree + docstrings`

---

### Task 5: feat(core): Pydantic Settings in core/config.py

**Files:** `src/basketball_stats/core/config.py`, `.env.example`
**REQ-IDs:** INFRA-05 (DATABASE_URL handling), OBS-03 (ENV + LOG_LEVEL)
**Depends on:** T04
**What:** `Settings(BaseSettings)` reading `DATABASE_URL`, `DATABASE_URL_DIRECT`, `ENV` (default "dev"), `LOG_LEVEL` (default "INFO"). Implement async URL rewriting in a property `async_database_url` that does `self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)` (per RESEARCH Q3 default — Strategy A). `env_file = ".env"`, `env_file_encoding = "utf-8"`. Docstring at top of file: `"""Pydantic Settings — single source of runtime config. Rewrites Neon's postgresql:// to postgresql+asyncpg:// for SQLAlchemy 2.0 async engine."""`. Author `.env.example` with placeholder values (committable; the real `.env` is gitignored).
**Why (defense):** RESEARCH §2.3 Q3 — keeps Neon URL round-tripping clean to Neon dashboard; driver concern in code where it belongs.
**Acceptance:**
```powershell
uv run python -c "from basketball_stats.core.config import Settings; s = Settings(DATABASE_URL='postgresql://x:y@z/db'); assert s.async_database_url.startswith('postgresql+asyncpg://'); print('ok')"
```
**Estimated commit:** `feat(core): pydantic settings with asyncpg url rewrite`

---

### Task 6: feat(core): async engine + AsyncSessionLocal + get_db dependency

**Files:** `src/basketball_stats/core/db.py`
**REQ-IDs:** INFRA-05, OBS-02 (DB probe in /healthz uses this)
**Depends on:** T05
**What:** Create async engine via `create_async_engine(settings.async_database_url, pool_pre_ping=True, pool_size=5, max_overflow=10)`. Define `AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`. Author `get_db()` async generator dependency yielding a session with `try/finally close` (PITFALLS P1.3 template). Module docstring quotes the rationale: `"""Async engine factory + get_db dependency. Pattern from tiangolo/full-stack-fastapi-template; mitigates P1.3 (session leaked across requests)."""`.
**Why (defense):** PITFALLS P1.3 mitigation upfront — established before any endpoint exists.
**Acceptance:**
```powershell
uv run python -c "from basketball_stats.core.db import engine, AsyncSessionLocal, get_db; print('ok')"
uv run mypy --strict src/basketball_stats/core/db.py
```
**Estimated commit:** `feat(core): async engine + AsyncSessionLocal + get_db dependency`

---

### Task 7: feat(models): Declarative Base in models/base.py (no entities)

**Files:** `src/basketball_stats/models/base.py`
**REQ-IDs:** INFRA-03 (Alembic round-trip needs Base.metadata)
**Depends on:** T04
**What:** `from sqlalchemy.orm import DeclarativeBase` → `class Base(DeclarativeBase): pass`. Module docstring: `"""Declarative Base — entities (Team, Player, Game, BoxScore, ...) land here in Phase 2. Exists in P1 so Alembic env.py can target Base.metadata even with zero subclasses (validates the migration pipeline before P2 stress)."""` (rationale for D-07/D-08).
**Why (defense):** D-07 + D-08 — proves migration pipeline before P2 adds 7 entities under deadline pressure.
**Acceptance:**
```powershell
uv run python -c "from basketball_stats.models.base import Base; print(Base.metadata.tables)"   # {} (empty)
```
**Estimated commit:** `feat(models): declarative base (entities land in P2)`

---

### Task 8: feat(api): global exception handlers in api/errors.py

**Files:** `src/basketball_stats/api/errors.py`
**REQ-IDs:** OBS-03 (no tracebacks leaked → JSON-only errors)
**Depends on:** T04
**What:** Two handlers: `validation_exception_handler` (catches `RequestValidationError` → `{"detail": "<msg>", "code": "validation_error"}` 422); `unhandled_exception_handler` (catches `Exception` → `{"detail": "internal error", "code": "internal_error", "request_id": "<from contextvars>"}` 500, logs full traceback via structlog). Export `register_exception_handlers(app: FastAPI) -> None`. Module docstring: `"""Global exception handlers — mitigates P1.6 (Python tracebacks leaked to clients). Established in P1 so every future endpoint inherits sanitized error responses by default."""`.
**Why (defense):** D-04 + PITFALLS P1.6 mitigation. Recruiter looking at `api/errors.py` sees production-grade error handling existed before the first business endpoint.
**Acceptance:**
```powershell
uv run python -c "from basketball_stats.api.errors import register_exception_handlers; print('ok')"
uv run mypy --strict src/basketball_stats/api/errors.py
```
**Estimated commit:** `feat(api): global exception handlers (sanitize tracebacks)`

---

### Task 9: feat(core): structlog tty-detected JSON/console logger

**Files:** `src/basketball_stats/core/logging.py`
**REQ-IDs:** OBS-03
**Depends on:** T05
**What:** Implement `configure_logging(env: str) -> None` per RESEARCH §6.1 verbatim — shared processors (`merge_contextvars`, `add_log_level`, `TimeStamper(iso)`, `StackInfoRenderer`, `format_exc_info`), env or non-tty → `JSONRenderer`, else `ConsoleRenderer(colors=True)`. `cache_logger_on_first_use=True`. Module docstring explains tty-detection rationale.
**Why (defense):** D-19 — JSON for Koyeb log aggregator parseability; pretty in dev for humans. Recruiter sees `core/logging.py` and immediately knows about contextvars + tty switching.
**Acceptance:**
```powershell
uv run python -c "from basketball_stats.core.logging import configure_logging; configure_logging('dev'); import structlog; structlog.get_logger().info('hello', foo='bar')"
# Expected: pretty console line with foo=bar
```
**Estimated commit:** `feat(core): structlog with tty-detected json/console renderer`

---

### Task 10: feat(core): RequestIdMiddleware ASGI middleware

**Files:** `src/basketball_stats/core/middleware.py`
**REQ-IDs:** OBS-03 (request_id per request)
**Depends on:** T09
**What:** Implement `RequestIdMiddleware` per RESEARCH §6.2 verbatim — accepts inbound `X-Request-Id` header, generates UUID4 fallback, `bind_contextvars(request_id=...)` then `clear_contextvars()` on entry; injects `X-Request-Id` into response headers via `send_with_request_id` wrapper. Module docstring: `"""Custom ASGI middleware binding request_id to structlog contextvars. Pre-OpenTelemetry pattern (D-20): demonstrates distributed-tracing awareness without importing full otel stack (scope creep for MVP)."""`.
**Why (defense):** D-20 — explicit "pre-OpenTelemetry" signal in code comment is interview gold.
**Acceptance:**
```powershell
uv run python -c "from basketball_stats.core.middleware import RequestIdMiddleware; print('ok')"
uv run mypy --strict src/basketball_stats/core/middleware.py
```
**Estimated commit:** `feat(core): request_id ASGI middleware bound to structlog contextvars`

---

### Task 11: feat(api): /healthz endpoint + lifespan + main.py app factory

**Files:** `src/basketball_stats/main.py`, `src/basketball_stats/api/v1/health.py`, `src/basketball_stats/api/v1/deps.py`
**REQ-IDs:** OBS-02, OBS-03
**Depends on:** T06, T07, T08, T09, T10
**What:** `api/v1/deps.py` re-exports `get_db` from `core.db` (single import surface for v1 routers — established now, used in P2). `api/v1/health.py` defines `router = APIRouter(tags=["health"])` and `@router.get("/healthz")` async handler: probes DB via `await session.execute(text("SELECT 1"))`, returns `{"status":"ok","db":"ok"}` (200) on success; on `Exception` returns `JSONResponse({"status":"degraded","db":"fail","error":"<class name only>"}, status_code=503)` per D-10 (status code is contract for Koyeb HTTP check, body is for humans). `main.py` defines `create_app()` factory: configures logging, creates `FastAPI(title="Basketball Stats API", version="0.1.0")`, registers `RequestIdMiddleware`, `register_exception_handlers(app)`, includes `health.router`, sets `@asynccontextmanager async def lifespan(app)` for engine startup/shutdown (NO `@app.on_event` — P1.2 mitigated). Export `app = create_app()` at module bottom.
**Why (defense):** D-09 + D-10 + D-11 + P1.2 + P1.6. One endpoint validates entire async chain: middleware → router → dep injection → session → SQL → response.
**Acceptance:**
```powershell
# Sanity: import + AST check
uv run python -c "from basketball_stats.main import app; print([r.path for r in app.routes])"
# Expected output contains '/healthz'
uv run mypy --strict src/basketball_stats/main.py src/basketball_stats/api/v1/health.py src/basketball_stats/api/v1/deps.py
```
**Estimated commit:** `feat(api): /healthz with real SELECT 1 + lifespan + app factory`

---

### Task 12: feat(db): alembic init -t async + env.py + 0001 baseline empty revision

**Files:** `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_<hash>_baseline.py`, `migrations/README`
**REQ-IDs:** INFRA-03 (CI round-trip), INFRA-05 (deploy needs migrations)
**Depends on:** T07
**What:** `uv run alembic init -t async migrations`. Edit `alembic.ini`: set `sqlalchemy.url = ` empty (we override in env.py from `DATABASE_URL_DIRECT`). Replace `env.py` content with RESEARCH §4.2 template verbatim, adapting import to `from basketball_stats.models.base import Base`. In `env.py` add at top: `config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL_DIRECT"])`. Create baseline: `uv run alembic revision -m "baseline"` then edit generated file to set both `upgrade()` and `downgrade()` to `pass`. Rename file to `0001_baseline.py` (drop hash prefix for clarity; update `revision = "0001_baseline"` and `down_revision = None` inside).
**Why (defense):** D-06/D-07/D-08 + R3/R5. Migration pipeline proven against an empty schema before P2 adds 7 entities. R5 sidestep: never call `alembic upgrade head` from inside FastAPI process — only Dockerfile CMD subprocess + CI.
**Acceptance:**
```powershell
# Against local docker-compose postgres (T15 will exist by Wave 6; run after T15 lands)
$env:DATABASE_URL_DIRECT="postgresql://dev:dev@localhost:5432/basketball_stats_dev"
uv run alembic upgrade head      # exits 0
uv run alembic downgrade base    # exits 0
uv run alembic upgrade head      # idempotent, exits 0
uv run alembic current           # shows 0001_baseline
```
**Estimated commit:** `feat(db): alembic async init + 0001 empty baseline revision`

---

### Task 13: test(infra): tests/conftest.py PostgresContainer + db_session fixtures

**Files:** `tests/conftest.py`
**REQ-IDs:** TEST-01, INFRA-03
**Depends on:** T11, T12
**What:** Per RESEARCH §5.2 — `postgres_container` fixture `scope="session"` using `PostgresContainer(image="postgres:16-alpine", username="test", password="test", dbname="test_db", driver=None)`. `db_session` fixture builds async engine from `pg.get_connection_url()` rewriting `postgresql://` → `postgresql+asyncpg://`. Also autouse fixture `_ensure_ryuk_disabled` that asserts `os.environ.get("TESTCONTAINERS_RYUK_DISABLED") == "true"` (failsafe: if anyone removes the pytest-env line, tests still warn).
**Why (defense):** D-16 + R6 mitigation. Testcontainers from P1 = TEST-01 wiring proven before P2 needs it for window-function coverage.
**Acceptance:**
```powershell
uv run pytest tests/conftest.py --collect-only   # no import errors
```
**Estimated commit:** `test(infra): testcontainers PostgresContainer + db_session fixtures`

---

### Task 14: test(api): unit test_config + integration test_healthz

**Files:** `tests/unit/test_config.py`, `tests/integration/test_healthz.py`
**REQ-IDs:** TEST-01, OBS-02 (verify literal `{status:ok, db:ok}` shape)
**Depends on:** T13
**What:** `tests/unit/test_config.py`: 2 tests — (a) Settings reads DATABASE_URL from env, (b) async_database_url property rewrites scheme correctly. `tests/integration/test_healthz.py`: uses `httpx.AsyncClient(transport=ASGITransport(app=app))` + the `postgres_container` fixture + monkeypatches `settings.DATABASE_URL` to container URL, runs `alembic upgrade head` programmatically (subprocess so R5 doesn't bite), then `await client.get("/healthz")` and asserts `status_code == 200` and `response.json() == {"status":"ok","db":"ok"}`. One more test: with a deliberately broken engine, asserts 503 + `db: "fail"` (D-10 contract test).
**Why (defense):** D-09 + D-10 contract tests. SC1 + SC2 anchor.
**Acceptance:**
```powershell
uv run pytest -v
# 4 tests, all green; total < 30s warm
```
**Estimated commit:** `test(api): /healthz integration test + Settings unit tests`

---

### Task 15: build(docker): multi-stage Dockerfile + .dockerignore + docker-compose.yml

**Files:** `Dockerfile`, `.dockerignore`, `docker-compose.yml`
**REQ-IDs:** INFRA-01, INFRA-02
**Depends on:** T11
**What:** `Dockerfile` per RESEARCH §7.1 verbatim — multi-stage `python:3.12-slim`, `COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /bin/`, BuildKit cache mount on `/root/.cache/uv`, two-phase sync (`--no-install-project` first, then full), non-root `app` user, `CMD ["sh", "-c", "alembic upgrade head && uvicorn basketball_stats.main:app --host 0.0.0.0 --port 8000"]` (RESEARCH Q4 default — migrations in CMD so Koyeb logs show migration failure cleanly, not buried mid-boot). `.dockerignore` per RESEARCH §7.3. `docker-compose.yml` per RESEARCH §7.4 — `postgres:16-alpine` named volume `pg_data` + `pg_isready` healthcheck + `depends_on: condition: service_healthy` (D-24, P4.4/P4.5 mitigated); api service with bind-mount `./src:/app/src` + `--reload` for dev (D-25).
**Why (defense):** D-22/D-23/D-24/D-25. Image < 200 MB (verified ~150 MB in uv-docker-example). Image build is the moment all earlier wiring becomes "real".
**Acceptance:**
```powershell
docker build -t basketball-stats-api:dev .
docker image inspect basketball-stats-api:dev --format "{{.Size}}"   # < 200000000 (200 MB)
docker compose up -d
# Wait for postgres healthy then api up
Start-Sleep -Seconds 10
curl http://localhost:8000/healthz
# {"status":"ok","db":"ok"}
docker compose down -v
```
**Estimated commit:** `build(docker): multi-stage Dockerfile + .dockerignore + docker-compose with healthcheck`

---

### Task 16: chore(hooks): .pre-commit-config.yaml + install + cleanup pass

**Files:** `.pre-commit-config.yaml`
**REQ-IDs:** INFRA-03 (CI safety-net re-runs hooks)
**Depends on:** T14, T15
**What:** Author `.pre-commit-config.yaml` per RESEARCH §9.1 verbatim. CRITICAL — include `default_install_hook_types: [pre-commit, commit-msg]` at top (R8 — without this, conventional-pre-commit silently never fires). Hooks: ruff-pre-commit v0.15.12 (`ruff-check --fix`, `ruff-format`), gitleaks v8.24.2, conventional-pre-commit v3.0.0 (`stages: [commit-msg]`), uv-pre-commit 0.11.14 (`uv-lock`), local mypy-strict hook (uses project venv via `uv run --frozen mypy --strict src/`). Then `uv run pre-commit install --install-hooks` and `uv run pre-commit run --all-files` once to clean any formatting drift.
**Why (defense):** D-28 + R8 + R9 mitigation. The `default_install_hook_types` line is the trap-door fix from RESEARCH that silent failure modes would have hit otherwise.
**Acceptance:**
```powershell
uv run pre-commit run --all-files     # all hooks pass
git commit --allow-empty -m "wip"      # SHOULD FAIL — bad commit format
git commit --allow-empty -m "chore(test): commitlint check"   # SHOULD PASS, then revert
git reset HEAD~1
```
**Estimated commit:** `chore(hooks): pre-commit (ruff + gitleaks + mypy --strict + conventional + uv-lock)`

---

### Task 17: ci(gha): .github/workflows/ci.yml with ruff + mypy + pytest + alembic round-trip

**Files:** `.github/workflows/ci.yml`
**REQ-IDs:** INFRA-03
**Depends on:** T14, T15, T16
**What:** Author per RESEARCH §8.1 verbatim. Pin `astral-sh/setup-uv@08807647e7069bb48b6ef5acd8ec9567f424441b # v8.1.0` (RESEARCH §3.3 — NOTE: CONTEXT.md D-17 references v3, but RESEARCH supersedes — see §Notes-from-planner). Triggers: push to main + PR to main (D-18). Job env `TESTCONTAINERS_RYUK_DISABLED: "true"` (R6). Steps: checkout@v5, setup-uv@v8.1.0 with `enable-cache: true` + `cache-dependency-glob`, `uv sync --locked`, `ruff check .` + `ruff format --check .`, `mypy --strict src/`, `pytest -v`, alembic round-trip step (docker run postgres:16-alpine + upgrade head → downgrade base → upgrade head + cleanup), `pre-commit run --all-files --show-diff-on-failure` as CI safety net.
**Why (defense):** D-15/D-17/D-18 + SC2. Wave 7 lands and SC2 lights up green badge on first push.
**Acceptance:**
- After T22 push: `gh run watch` → workflow `CI` finishes green in < 5 min.
- `gh run view --log` shows ruff, mypy, pytest, alembic round-trip steps all succeed.
**Estimated commit:** `ci(gha): ci workflow (ruff + mypy + pytest + alembic round-trip)`

---

### Task 18: docs(setup): docs/setup/koyeb-neon.md step-by-step manual deploy walkthrough

**Files:** `docs/setup/koyeb-neon.md`
**REQ-IDs:** INFRA-05
**Depends on:** T15
**What:** Author step-by-step doc per D-31. Sections: (1) Create Neon project (free tier, single `main` branch — Q2 default), copy BOTH connection URLs (pooled + direct). (2) `koyeb login`. (3) `koyeb secrets create DATABASE_URL --value-from-stdin` (paste pooled), `koyeb secrets create DATABASE_URL_DIRECT --value-from-stdin` (paste direct), `koyeb secrets create JWT_SECRET --value-from-stdin` (stub for P3, paste `openssl rand -hex 32`). (4) `koyeb app init` command with `--docker` (RESEARCH §1.2 + Q9 default). (5) **Health-check config via dashboard UI** — explicit screenshot-style steps with click-path: `Service → Health checks → expand → protocol HTTP, path /healthz, grace 30s, interval 10s, restart limit 5, timeout 5s`. Big yellow callout: "CLI flag syntax for health checks is NOT publicly documented as of 2026-05; configuring via UI is the documented path. P4 (INFRA-04 automation) will revisit." (R1 mitigation.) (6) Loud warning callout — "Alembic + PgBouncer transaction-mode silently corrupts state. NEVER point `DATABASE_URL_DIRECT` at the pooled URL. NEVER point `DATABASE_URL` at the direct URL except for one-off scripts." (R3 mitigation.)
**Why (defense):** D-31 + R1 + R3 mitigations documented in source-of-truth doc for next-person.
**Acceptance:**
- Doc lints clean (no broken markdown).
- Roger reads it once and can reproduce the deploy steps without asking Claude.
**Estimated commit:** `docs(setup): koyeb + neon manual deploy walkthrough`

---

### Task 19: chore(deploy): provision Neon project + Koyeb secrets (manual, follow doc)

**Files:** none committed (manual external operations); update `docs/setup/koyeb-neon.md` only if instructions need correction
**REQ-IDs:** INFRA-05
**Depends on:** T18
**What:** Execute the walkthrough in T18 step-by-step against real Neon + Koyeb accounts. Capture both Neon URLs as Koyeb secrets `DATABASE_URL` (pooled) + `DATABASE_URL_DIRECT` (direct). Run quick verification: `koyeb secrets list` shows both. Q4 confirmation: also smoke-test asyncpg + Neon SSL (R4) — run `uv run python -c "import asyncio; from sqlalchemy.ext.asyncio import create_async_engine; from sqlalchemy import text; e = create_async_engine('<neon-pooled-rewritten-to-asyncpg>'); asyncio.run((lambda: __import__('asyncio').run(<probe>)))"` (or simpler: a one-shot script in the repo's `scripts/` dir, gitignored). If `sslmode=require` fails, fall back to Strategy A connect_args per R4. Document the outcome in T18's doc.
**Why (defense):** Catches R4 before pushing config that won't work in prod. Validates assumed Strategy B.
**Acceptance:**
```powershell
koyeb secrets list   # DATABASE_URL, DATABASE_URL_DIRECT, JWT_SECRET present
# Local probe against Neon
uv run python scripts/neon_probe.py    # prints "select 1 ok"
```
**Estimated commit:** (no commit — manual external state. If neon_probe.py is useful, commit separately later.) Optional: `docs(setup): note neon ssl handling outcome` if T18 doc updated.

---

### Task 20: feat(deploy): first Koyeb deploy via app init + configure /healthz dashboard health check

**Files:** none committed (Koyeb-side state); manual operation
**REQ-IDs:** INFRA-05, OBS-03 (verify JSON logs in Koyeb)
**Depends on:** T19
**What:** Build and push image to a registry Koyeb can pull (either `ghcr.io/roger-llinares/basketball-stats-api:0.1.0-rc1` via `gh` login + `docker push`, or use Koyeb's git-build path — RESEARCH Q9 default is `--docker` for parity with local). Run `koyeb app init basketball-stats-api --docker ghcr.io/.../basketball-stats-api:0.1.0-rc1 --instance-type free --regions fra --ports 8000:http --routes /:8000 --env PORT=8000 --env DATABASE_URL='{{ secret.DATABASE_URL }}' --env DATABASE_URL_DIRECT='{{ secret.DATABASE_URL_DIRECT }}' --env ENV=prod --env LOG_LEVEL=INFO` (Q1 default fra; if `koyeb regions list` shows `par`/`mad` available, prefer the lower-latency option). Wait for service `healthy`. Open dashboard → configure HTTP health check on `/healthz` per T18 doc step 5. `curl https://basketball-stats-api-<slug>.koyeb.app/healthz` → expect `{"status":"ok","db":"ok"}`. Copy the public URL — needed for T22 README live-URL section. Tail logs: `koyeb logs basketball-stats-api/basketball-stats-api --type runtime` and verify JSON lines with `request_id` field present.
**Why (defense):** SC3 + SC5. First manual deploy is the proof point; P4 (INFRA-04) will automate this.
**Acceptance:**
```powershell
curl https://basketball-stats-api-<slug>.koyeb.app/healthz
# {"status":"ok","db":"ok"}
koyeb logs basketball-stats-api/basketball-stats-api --type runtime | findstr request_id
# JSON lines with request_id present
```
**Estimated commit:** (no commit — Koyeb state. Public URL captured for T22.)

---

### Task 21: ci(deps): .github/dependabot.yml weekly updates

**Files:** `.github/dependabot.yml`
**REQ-IDs:** INFRA-03 (keep CI green by keeping deps current)
**Depends on:** T16
**What:** Author per RESEARCH §10 verbatim — 3 ecosystems (pip, github-actions, docker), weekly Mondays, `open-pull-requests-limit: 5/3/3`, labels per ecosystem. Q7 default = per-dep PRs (easier review than grouped).
**Why (defense):** D-29 + P6.9/P6.10 mitigations. Contribution graph keeps a heartbeat even on weeks Roger doesn't push code.
**Acceptance:**
```powershell
# YAML lints — basic shape check
type .github\dependabot.yml | findstr "package-ecosystem"   # 3 matches
```
**Estimated commit:** `ci(deps): dependabot weekly pip + github-actions + docker`

---

### Task 22: docs(readme): README badges + minimal structure + ADR-0001 stack-election + first push

**Files:** `README.md`, `docs/adr/0001-stack-election.md`, `docs/adr/.gitkeep`
**REQ-IDs:** OBS-07 (badges), OBS-04 (stub), INFRA-05 (live URL)
**Depends on:** T17 (so CI badge can go green), T20 (need real Koyeb URL), T21
**What:** Author `README.md` per D-30 structure: (1) one-line pitch + `/docs` screenshot placeholder; (2) **5 badges** row: `![CI](https://github.com/roger-llinares/basketball-stats-api/actions/workflows/ci.yml/badge.svg)`, `![Ruff](https://img.shields.io/badge/lint-ruff-blue)`, `![Mypy](https://img.shields.io/badge/types-mypy--strict-blue)`, `![Python](https://img.shields.io/badge/python-3.12-blue)`, `![License](https://img.shields.io/badge/license-MIT-green)`; (3) **Live URL**: `https://basketball-stats-api-<slug-from-T20>.koyeb.app/healthz`; (4) **Local dev** section: `docker compose up` + 10s wait + `curl localhost:8000/healthz`; (5) **Deploy** pointer to `docs/setup/koyeb-neon.md`; (6) **Stack walkthrough** placeholder honest stub: "Phase 5 polish — see [docs/adr/](docs/adr/)". Author `docs/adr/0001-stack-election.md` per D-32: documents LOCKED PROJECT.md decisions (FastAPI, Postgres-pur via Neon, Koyeb, uv, testcontainers) with rationale + alternatives considered + status (accepted 2026-05-19). Add `docs/adr/.gitkeep` so the directory tracks future ADRs. THEN finally `git push -u origin main` — the first public commit history now contains README + CI green + live URL + ADR-0001, satisfying SC4 + closing the loop.
**Why (defense):** D-21/D-30/D-32 + SC4. The very first thing a recruiter sees on `github.com/roger-llinares/basketball-stats-api` is 5 green badges + working live URL + ADR baseline. Mitigates P6.6 + P6.8.
**Acceptance:**
```powershell
git push -u origin main
# Wait for CI green
gh run watch
# Open repo in browser
gh repo view --web
# Verify: 5 badges render, CI badge green, live URL clickable and responding
curl https://basketball-stats-api-<slug>.koyeb.app/healthz
# {"status":"ok","db":"ok"}
```
**Estimated commit:** `docs(readme): badges + minimal sections + ADR-0001 stack election`

---

## Decision-Tree Trace (every D-XX implemented)

| Task | Decisions implemented |
|------|-----------------------|
| T01 | D-12 |
| T02 | D-21 (license), D-26, D-27 |
| T03 | D-12, D-13, D-14 |
| T04 | D-01, D-02, D-03, D-05 |
| T05 | D-14 (config in pyproject), D-19 (env/LOG_LEVEL) |
| T06 | D-04 (core/db.py present), D-07 (Base import target shape) |
| T07 | D-07 |
| T08 | D-04 (api/errors.py), supports D-09 (sanitized /healthz errors) |
| T09 | D-19 |
| T10 | D-20 |
| T11 | D-04 (api/v1/health.py, deps.py), D-09, D-10, D-11 |
| T12 | D-06, D-07, D-08 |
| T13 | D-05, D-16 |
| T14 | D-05, D-09, D-10, D-16 |
| T15 | D-22, D-23, D-24, D-25 |
| T16 | D-28 |
| T17 | D-15, D-17, D-18, D-28 (CI safety net) |
| T18 | D-31 |
| T19 | (executes D-31; no new decision) |
| T20 | D-31 (executes the documented path) |
| T21 | D-29 |
| T22 | D-21, D-30, D-32 |

**Coverage check:** D-01..D-32 all touched. Zero orphaned decisions.

## Requirement Coverage

| REQ-ID | Tasks |
|--------|-------|
| INFRA-01 | T15 |
| INFRA-02 | T03, T04, T15 |
| INFRA-03 | T03, T12, T16, T17, T21 |
| INFRA-05 | T05, T06, T12, T18, T19, T20 |
| OBS-02 | T06, T11, T14 |
| OBS-03 | T08, T09, T10, T11, T20 |
| OBS-07 | T02, T22 |
| TEST-01 | T13, T14 |

All 8 REQ-IDs covered by ≥1 task.

## Open Questions Surfaced (with planner defaults)

| # | Question | Default in plan | Override point |
|---|----------|-----------------|----------------|
| Q1 | Koyeb region: fra / par / mad? | `fra` (verified available) | T20 — run `koyeb regions list` first; if `par` or `mad` listed, prefer them |
| Q2 | Neon preview branches in CI? | No, single `main` branch | T19 — Roger can opt in, would require extra GHA step |
| Q3 | asyncpg URL: rewrite in code or store with prefix? | Strategy A (rewrite in `core/config.py`) | T05 — embedded as the chosen design |
| Q4 | `alembic upgrade head` placement: Docker CMD vs separate Koyeb step? | Docker CMD (RESEARCH override — see §Notes) | T15 |
| Q5 | `pytest-env` vs shell export for ryuk-disable? | `pytest-env` via `[tool.pytest.ini_options].env` | T03 |
| Q6 | mypy pre-commit: local+uv run vs upstream? | `local + uv run --frozen` (sees real venv) | T16 |
| Q7 | Dependabot grouped vs per-dep? | Per-dep (easier review) | T21 |
| Q8 | README CI badge target path? | `.github/workflows/ci.yml` | T22 |
| Q9 | First deploy: `--docker` (pre-built image) vs `--git` (buildpacks)? | `--docker` (Dockerfile is source of truth) | T20 |
| Q10 | License: MIT vs Apache-2.0? | MIT (matches D-21 badge) | T02 |

All defaults are reversible — flag at execute time if Roger wants different.

## Notes from Planner (conflicts resolved)

1. **`astral-sh/setup-uv` version override.** CONTEXT.md D-17 says "setup-uv@v3". RESEARCH §3.3 explicitly flags v3 as outdated and pins v8.1.0 (SHA `08807647e7069bb48b6ef5acd8ec9567f424441b`). **RESEARCH wins** per the planning brief — more recent + verified via ctx7 `/astral-sh/setup-uv` 2026-05-19. T17 implements v8.1.0. D-17's intent (uv cache enabled in GHA) is preserved; only the action version changes.
2. **Koyeb health-check via CLI vs dashboard.** CONTEXT.md does not specify; RESEARCH §1.8 + R1 establish the dashboard UI is the documented path because CLI flag names are not public. P1 configures via dashboard (T20) and documents the click-path (T18). P4 (INFRA-04) will revisit CLI automation once the deploy workflow demands it.
3. **`alembic upgrade head` placement.** CONTEXT.md D-08 only specifies CI round-trip; does not mandate prod migration mechanism. RESEARCH §1.9 + Q4 default = Docker CMD (idempotent, single source-of-truth). Chosen for P1; the alternative (separate Koyeb step) lands naturally in P4 if needed.
4. **Roger's git scope.** Working dir `C:\Users\llina\Desktop\SecondBrain\03 Projects\Otros Proyectos\Basketball Stats API\` is gitignored from the parent vault (per Roger's memory note "Todo el código en SecondBrain"); this project has its OWN `.git`. Commits and `gh repo create` happen inside this directory, NOT against the SecondBrain vault repo. T02 assumes this layout.
5. **Phase 1 has zero domain code by design.** If during execute any task feels like it needs a domain entity to "make sense", that's a signal of scope creep — stop and surface. P1 is wiring + observability + deploy proof, nothing else.
