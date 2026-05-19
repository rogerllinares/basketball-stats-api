---
project: basketball-stats-api
doc: research/STACK.md
created: 2026-05-19
researched: 2026-05-19
status: prescriptive
overall_confidence: HIGH
sources:
  - PyPI JSON API (verified 2026-05-19)
  - Context7 (/fastapi/fastapi, /pydantic/pydantic, /websites/sqlalchemy_en_20)
  - postgresql.org/support/versioning
  - fly.io official docs
---

# Technology Stack — Basketball Stats API

> **Status:** LOCKED by Roger 2026-05-19. This document VERIFIES current versions (Jan-May 2026), prescribes exact pins, lists alternatives ruled out with reasons. **Do not re-debate stack choices.**

## TL;DR — Versions to pin (verified PyPI 2026-05-19)

```
python = "^3.11"          # 3.11 LTS-style, 3.12/3.13 also fine
fastapi = "0.136.1"
pydantic = "2.13.4"
pydantic-settings = "2.x"  # config from env vars
sqlalchemy = "2.0.49"
alembic = "1.18.4"
asyncpg = "0.31.0"        # async Postgres driver
psycopg = {version="3.3.4", extras=["binary"]}  # for Alembic sync runtime
uvicorn = "0.47.0"
gunicorn = "26.0.0"
python-jose = {version="3.5.0", extras=["cryptography"]}  # JWT
passlib = {version="1.7.4", extras=["argon2"]}            # password hashing
argon2-cffi = "25.1.0"
python-multipart = "0.0.29"
structlog = "25.5.0"

# dev
ruff = "0.15.13"
mypy = "2.1.0"
pytest = "9.0.3"
pytest-asyncio = "1.3.0"
httpx = "0.28.1"
testcontainers = {version="4.14.2", extras=["postgres"]}
pre-commit = "4.6.0"
polyfactory = "3.3.0"     # Pydantic-aware factories

# infra
postgres = "16.14"        # current Postgres 16 minor
redis = "7.4"             # post-MVP cache

# tooling
uv = "0.11.15"            # package manager (replaces pip/pip-tools/poetry)
```

Confidence per pin: HIGH (each verified against PyPI JSON 2026-05-19 or postgresql.org).

---

## Core stack — version-by-version verification

### Python 3.11+ — confidence HIGH

**Pin:** `^3.11` (project supports 3.11, 3.12, 3.13).

**Why:** 3.11 is the floor because (a) Roger already uses it on LinkedIn CLI, (b) `tomllib` stdlib, (c) exception groups for `asyncio.TaskGroup`, (d) faster startup. 3.13 is current stable (Oct 2024); 3.14 expected Oct 2026 but unnecessary for portfolio.

**Action:** Set `requires-python = ">=3.11"` in `pyproject.toml` and pin the CI matrix to `[3.11, 3.12, 3.13]` to show range support without adding bug surface from 3.14.

---

### FastAPI 0.136.1 — confidence HIGH

**Pin:** `fastapi = "0.136.1"` (PyPI 2026-04-23). Source: PyPI JSON + Context7 `/fastapi/fastapi`.

**Why this and not alternatives:** FastAPI is the dominant modern Python web framework for jr backend roles in 2026. Auto-generated OpenAPI `/docs` is the single best "show, don't tell" feature for recruiters opening the deploy URL. Native async, Pydantic v2 integration, dependency injection built in.

**Patterns to highlight in code (call out in README walkthrough):**
1. **Lifespan context manager** (`@asynccontextmanager`) for DB pool startup/teardown — replaces deprecated `@app.on_event`. Mandatory in 2026 idiomatic FastAPI.
2. **`Annotated[X, Depends(...)]` style** dependencies (PEP 593) — NOT the old `x: X = Depends()` style. Reviewer signal.
3. **`response_model_exclude_none=True`** + per-route `response_model` for tight contracts.
4. **`@app.exception_handler(...)`** with domain exceptions mapped to RFC 7807 Problem Details JSON.
5. **`dependency_overrides`** in tests — replace `get_db` with `testcontainers` session factory.
6. **Routers per resource** (`/teams`, `/players`, `/games`, `/leagues`) — show separation; do NOT dump everything in `main.py`.
7. **`tags` + `summary` + `description`** on every route → OpenAPI looks pro at `/docs`.

**Ruled out:**
- **Flask** — not async-native, no Pydantic v2 integration, no OpenAPI auto-gen, signals "legacy junior" to recruiters in 2026.
- **Django + DRF** — overkill for API-only; `Django ORM != SQLAlchemy 2.0`; loses the SQLAlchemy showcase requirement.
- **Litestar** — newer FastAPI competitor with good async story, but tiny job market footprint (~1% vs FastAPI ~25% in Python backend ads 2026). Wrong choice for a job-hunt portfolio piece.
- **Starlette directly** — FastAPI IS Starlette + Pydantic; skipping FastAPI loses the OpenAPI win.

---

### Pydantic 2.13.4 — confidence HIGH

**Pin:** `pydantic = "2.13.4"` (PyPI 2026-05-06).

**Why:** v2 has the Rust core (`pydantic-core`) — ~5–50× faster than v1. FastAPI 0.100+ requires v2. `model_config` replaces inner `Config` class; `field_validator` / `model_validator` replace `validator`. Roger MUST use v2 idioms only — no v1 leftover patterns.

**Companion lib — Pydantic Settings:** `pydantic-settings = "^2.x"`. Loads env vars / `.env` into a typed `Settings(BaseSettings)` singleton. Required to avoid `os.getenv("...")` sprinkled across the codebase. Roger should expose one `get_settings()` `lru_cache`'d dependency.

**Ruled out:**
- **dataclasses + manual validation** — no JSON schema, no FastAPI integration.
- **marshmallow** — separate schema definitions from models, FastAPI-incompatible idiomatically.
- **attrs** — fine library but no automatic FastAPI request/response binding.

---

### SQLAlchemy 2.0.49 (async) — confidence HIGH

**Pin:** `sqlalchemy = "2.0.49"` (PyPI 2026-04-03). Source: Context7 `/websites/sqlalchemy_en_20`.

**Why:** 2.0 is the modern syntax — `select()` + `session.execute(stmt)` + `Mapped[X]` typed columns. The async API is mature. The `Mapped[]` typing alone is a strong jr-portfolio signal (full type coverage, mypy passes).

**Driver choice — `asyncpg` for runtime, `psycopg[binary]` for Alembic:**
- App URL: `postgresql+asyncpg://...`
- Alembic env.py: synchronous URL `postgresql+psycopg://...` (Alembic does not need async; using async there adds complexity for zero gain).

**Patterns to highlight:**
1. `Mapped[int]` + `mapped_column(...)` everywhere — no legacy `Column(Integer)`.
2. `async_sessionmaker` + `AsyncSession` dependency injection.
3. Selectin/joined eager loading explicitly declared (no N+1 silently).
4. Raw SQL with `text()` for the showcase queries (window functions, full-text search) — comment why ORM-only would obscure intent.

**Ruled out:**
- **psycopg2** (sync only, in maintenance mode — psycopg 3 supersedes it). Recruiters reading the lockfile will spot psycopg2 as a legacy signal.
- **Tortoise ORM / Piccolo / SQLModel** — SQLModel is FastAPI author's lib but layers on top of SQLAlchemy + Pydantic with v2 friction; the showcase is SQLAlchemy 2.0, not its wrapper. Use plain SQLAlchemy.
- **Databases (encode/databases)** — abandoned in favor of native async SQLAlchemy.
- **Synchronous SQLAlchemy** — the project explicitly showcases async.

---

### Alembic 1.18.4 — confidence HIGH

**Pin:** `alembic = "1.18.4"` (PyPI 2026-02-10).

**Why:** Standard SQLAlchemy companion. Required for "migration history clean" showcase in PROJECT.md.

**Patterns:**
- Every migration must have a working `downgrade()` (PROJECT.md requirement #5).
- Use `--autogenerate` but ALWAYS review the diff (autogen misses CHECK constraints, indexes on expressions, JSONB GIN indexes).
- Naming convention: `op.f("ix_games_game_date")` — set `naming_convention` in `MetaData` so generated names are stable across DBs.
- For Postgres-specific things (GIN, tsvector triggers) write the migration by hand. Note in the migration docstring why autogen couldn't help.

**Ruled out:** `aerich`, `yoyo`, raw SQL migrations — none integrate with SQLAlchemy metadata.

---

### PostgreSQL 16.14 — confidence HIGH

**Pin:** `postgres:16.14-alpine` Docker image. Source: postgresql.org/support/versioning (verified 2026-05-19).

**Why 16 and not 17?** Postgres 17 (Sep 2024 release, currently 17.x stable as of 2026) is fully production-ready, but 16 has wider hosting compatibility (Fly.io Postgres 16 cluster image is the default; Supabase still 15/16 at time of writing). Roger pins to 16 to match Fly.io default and avoid surprises. If wanting to upgrade, 17 is fine — both share the same SQL features Roger needs.

**Postgres features that MUST appear in migrations (per PROJECT.md):**
1. **Window functions** — `RANK() OVER (...)` for leaderboards (write in `text()` or use SQLAlchemy `func.rank().over(...)`).
2. **JSONB column** — `play_by_play JSONB` on `games`; add `GIN` index.
3. **Composite index** — `CREATE INDEX ix_games_league_date ON games (league_id, game_date DESC)`.
4. **Full-text search** — `tsvector` generated column on `players(full_name, alt_names)` + GIN index + `plainto_tsquery` in query.
5. **CHECK constraints** — e.g. `points >= 0`, `minutes BETWEEN 0 AND 60`.

**Ruled out:**
- **Supabase** — explicit blocker per PROJECT.md (overlap with Apostes Automatitzades).
- **SQLite for prod** — kills the SQL-showcase angle.
- **MySQL** — JSONB-equivalent (JSON) is weaker, window functions only in 8+, smaller backend Python job-ad share.
- **MongoDB** — wrong domain (relational data: leagues→teams→players→games→box_scores).

---

### Auth: python-jose 3.5.0 + passlib[argon2] 1.7.4 — confidence MEDIUM

**Pin:** `python-jose[cryptography] = "3.5.0"` + `passlib[argon2] = "1.7.4"` + `argon2-cffi = "25.1.0"`.

**Why:** FastAPI official OAuth2 docs use this combo. JWT signing with HS256 (single-key) for MVP; document RS256 migration path in an ADR.

**Caveat (read this):** `passlib` 1.7.4 was last released Oct 2020. It still works but the maintainer is inactive. `python-jose` 3.5.0 is recent (May 2025). Two reasonable alternatives Roger could pick instead, both with HIGH confidence and recent releases:
- **PyJWT 2.12.1** (Mar 2026) — simpler, actively maintained, FastAPI tutorial has examples. Recommended swap if Roger wants a "no eyebrow-raise" lockfile.
- **Authlib 1.7.2** (May 2026) — overkill for HS256 JWT but the right pick if Roger ever adds OAuth2 social login.

**Prescription:** Start with `python-jose` because the FastAPI official tutorial uses it (less friction). If a reviewer asks "why python-jose over PyJWT in 2026?" the answer is "FastAPI docs canonical example; would switch to PyJWT for a fresh project — documented in ADR-002." That answer is fine for a jr role.

**Password hashing — argon2id, NOT bcrypt:** argon2id won the Password Hashing Competition, is OWASP's recommendation as of 2026, and shows up-to-date security awareness. bcrypt is acceptable but feels 2015.

**Ruled out:**
- **Hard-coded password comparison / SHA256** — obvious junior signal red flag.
- **fastapi-users** — pre-built auth lib, but hides the OAuth2/JWT mechanics that are the whole point of the showcase.

---

### Cache: Redis 7.4 (POST-MVP) — confidence HIGH

**Pin:** `redis:7.4-alpine` Docker image, `redis = "^5.0"` Python async client.

**Why post-MVP:** PROJECT.md says optional MVP. Roger should ship without Redis first, add it for the "cache invalidation" showcase in a second milestone with a clear ADR explaining: "Standings read >>> writes; invalidate on box-score upload; TTL 1h as belt-and-braces."

**Pattern to highlight:** Decorator `@cache(ttl=3600, key="standings:{league_id}")` + explicit `cache.invalidate("standings:*")` in the upload-box-score endpoint.

---

### Tests: pytest 9.0.3 + httpx 0.28.1 + testcontainers 4.14.2 — confidence HIGH

**Pins:** verified PyPI. `pytest-asyncio = "1.3.0"` required.

**Why testcontainers (Postgres real):**
- Mocks lie about Postgres behavior (JSONB ops, window functions, tsvector).
- Testcontainers spins a real `postgres:16-alpine` per test session, applies Alembic migrations, gives you a real connection.
- This IS the differentiator vs the typical jr portfolio that uses SQLite-in-memory for tests.

**Patterns to highlight (README mention each):**
1. `conftest.py` session-scoped `postgres_container` fixture.
2. Per-test transaction rollback (faster than per-test DB recreate) via SAVEPOINT pattern.
3. `httpx.AsyncClient(transport=ASGITransport(app=app))` — no real network, in-process.
4. `dependency_overrides[get_db] = override_get_db` — clean override + reset.
5. `polyfactory` 3.3.0 for typed Pydantic factories (better than hand-built dicts).

**Ruled out:**
- **unittest** stdlib — verbose, no fixture composition.
- **SQLite in tests** — see above; defeats the showcase.
- **`pytest-postgresql`** — viable but tied to a system Postgres install; testcontainers is more portable and CI-friendly.
- **Tavern / Schemathesis** — Schemathesis worth a mention in a follow-up milestone for property-based API testing, NOT in MVP.

---

### Linting: ruff 0.15.13 + mypy 2.1.0 — confidence HIGH

**Pins:** verified PyPI.

**Why ruff:** Replaces flake8 + isort + pyupgrade + bandit + black (with `ruff format`) in one tool, written in Rust, 10–100× faster. As of 2026 it is the default in new Python projects; not picking ruff is a red flag.

**Why mypy in `--strict`:** `--strict` enables all opt-in checks. With SQLAlchemy 2.0's `Mapped[]` typing and Pydantic v2 the type coverage is achievable. This is THE quality signal — a green `mypy --strict` build proves the codebase isn't smuggling `Any` everywhere.

**Concrete config to commit:**
- `ruff.toml`: select `["E","F","I","UP","B","S","ASYNC","SIM","TCH","RUF"]`, line-length 100, target `py311`.
- `mypy.ini`: `strict = True`, `plugins = pydantic.mypy`, `disallow_untyped_decorators = False` (FastAPI decorators), explicit per-module overrides for `testcontainers`.
- `pre-commit` 4.6.0 hook runs both on every commit.

**Ruled out:**
- **pyright** — fine type checker but mypy is the de-facto standard in Python job ads in 2026. Use mypy.
- **pylint** — slow, opinionated, ruff covers 90% of useful rules.
- **black** separately — `ruff format` is fully black-compatible since ruff 0.4+.

---

### Package manager: uv 0.11.15 — confidence HIGH

**Pin:** `uv = "0.11.15"` (PyPI 2026-05-18). Use uv for the project.

**Why uv and not pip-tools / poetry:**
- **uv** (Astral, same authors as ruff) — Rust-based, ~10–100× faster than pip. Native lockfile (`uv.lock`), no separate `requirements.in`/`requirements.txt` split. As of 2026 it is the de-facto modern choice in new Python projects, and is THE answer reviewers want to hear for "what's modern in Python tooling 2026?". Single tool: install, lock, run, venv, python-version management.
- **poetry** — still common, but slower; lock format proprietary; recent governance/release-cadence concerns. Roger would not get marked down for poetry, but uv is the stronger 2026 signal.
- **pip-tools 7.5.3** — works but is 2 tools (`pip-compile` + `pip-sync`), no Python version management, no venv management. Outdated workflow.
- **Pipenv** — abandoned in practice. Do NOT use.
- **conda/mamba** — wrong tool for a web service.

**Concrete files:**
- `pyproject.toml` (PEP 621) with `[project]` + `[tool.uv]` + `[tool.ruff]` + `[tool.mypy]` + `[tool.pytest.ini_options]`.
- `uv.lock` committed to repo (reproducible builds).
- CI: `uv sync --frozen` then `uv run pytest`.
- Docker: multi-stage build, `uv pip install --system` in builder stage; copy `/usr/local/lib/python3.11/site-packages` to slim final image.

---

### Recommended extras NOT in the original LOCKED list

These are essential for a portfolio-grade FastAPI service; add them:

| Lib | Version | Purpose | Why required |
|---|---|---|---|
| `pydantic-settings` | ^2.x | Env-var loading | Otherwise `os.getenv` everywhere; bad signal. HIGH confidence. |
| `structlog` | 25.5.0 | Structured logging (JSON in prod) | Recruiters open Fly.io logs → JSON > printf. HIGH confidence. |
| `uvicorn[standard]` | 0.47.0 | ASGI server (dev + uvloop in prod) | FastAPI's recommended runner. HIGH confidence. |
| `gunicorn` | 26.0.0 | Process supervisor for uvicorn workers in prod | Fly.io best practice: `gunicorn -k uvicorn.workers.UvicornWorker`. HIGH confidence. |
| `python-multipart` | 0.0.29 | Form data parsing (OAuth2 password flow) | Required by FastAPI OAuth2PasswordBearer. HIGH confidence. |
| `greenlet` | 3.5.0 | SQLAlchemy async dependency | Transitive; pin explicitly to avoid resolver surprises. MEDIUM confidence (often auto-installed). |
| `polyfactory` | 3.3.0 | Pydantic-aware test factories | Cleaner than hand-built dicts. MEDIUM confidence (nice-to-have). |
| `argon2-cffi` | 25.1.0 | passlib argon2 backend | Required to make argon2id work. HIGH confidence. |

**Reasonable additions ruled OUT for MVP** (revisit milestone 2):
- `dependency-injector` 4.49.0 — FastAPI's native `Depends()` is enough for this scope. Adding `dependency-injector` adds learning curve with no recruiter payoff at jr level.
- `asgi-lifespan` 2.1.0 — only needed if running lifespan events outside an ASGI server (tests with `httpx.AsyncClient`). `ASGITransport(app=app)` with `lifespan="on"` handles it.
- `slowapi` (rate limiting) — show it in a "production-readiness" milestone, not MVP.
- `prometheus-fastapi-instrumentator` — same, post-MVP.
- `sentry-sdk` — free tier exists, optional add for "shows observability awareness" in v2.
- `celery` / `arq` / `taskiq` — explicit Out of Scope per PROJECT.md (no background jobs MVP).

---

### Infra: Docker Compose + GitHub Actions + Fly.io — confidence HIGH

**Docker:**
- Multi-stage `Dockerfile`: `python:3.11-slim-bookworm` base; uv install in builder; copy `.venv` to runtime. Final image <200MB.
- `docker-compose.yml`: services `api` + `postgres:16.14-alpine` + (later) `redis:7.4-alpine`. Healthchecks on each. `.env` driven config.
- One-command bring-up per PROJECT.md REQ-INFRA: `docker compose up`.

**GitHub Actions** (one workflow file `ci.yml`, two jobs):
1. `lint-and-types` — `uv sync`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy --strict app/`.
2. `test` — same setup, `uv run pytest --cov=app --cov-report=term-missing`. Coverage gate ≥80% recommended.
3. `deploy` (only on tag `v*`) — `flyctl deploy --remote-only`.

Use `actions/setup-python` + `astral-sh/setup-uv@v3` (actively maintained action).

**Fly.io free tier:**
- 3 shared-CPU VMs + 3GB persistent volume free (subject to Fly's current policy — verify at signup).
- `fly postgres create` for managed Postgres (free for small instance).
- Single region (e.g. `mad` Madrid). `fly.toml` with `internal_port = 8000`, `force_https = true`.
- **Free-tier risk:** Fly.io tightened the free tier in 2024; the "free" allowance now requires an active card on file with $0 charged for small apps. CALL OUT IN README that the deploy "stays under free-tier limits" so reviewers don't think the URL will 402.

**Ruled out:**
- **Vercel/Render** — PROJECT.md explicit ban (overlap with SST/Apostes).
- **Heroku** — no free tier since 2022.
- **AWS Fargate/ECS/Lambda** — way over budget (no free tier for the whole stack) and overkill for jr portfolio.
- **Railway** — viable, but Fly.io has the stronger devops-narrative (Dockerfile-driven, region selection, internal networking).

---

## What NOT to use — explicit blacklist with reasons

| Tool | Why NOT | If a reviewer asks "why not X?" |
|---|---|---|
| Flask | Sync-only, no Pydantic, no OpenAPI auto-gen | "Wanted to showcase async + OpenAPI auto-doc; Flask would force me to add 4 plugins." |
| Django + DRF | Overkill API-only; kills SQLAlchemy showcase | "Django's ORM is great but the brief was SQLAlchemy 2.0 typed mappings." |
| psycopg2 | Sync-only, maintenance mode | "psycopg 3 supersedes it; asyncpg is faster for async workloads." |
| pipenv | Abandoned in practice | "uv is the 2026 standard; pipenv hasn't shipped meaningful releases." |
| poetry | Slower than uv; format proprietary | "uv is faster, has Python version management, and is gaining adoption rapidly." |
| pip-tools | 2 tools, no venv/Python mgmt | "uv covers compile+sync+venv+Python in one tool." |
| SQLite for prod | Kills SQL showcase | "I need window functions, JSONB, tsvector — Postgres native." |
| SQLite in tests | Lies about Postgres semantics | "testcontainers gives a real Postgres per test session." |
| SQLModel | Wraps SQLAlchemy with v2 friction | "I want to show raw SQLAlchemy 2.0 mapped typing, not a wrapper." |
| FastAPI's older `@on_event` | Deprecated | "Lifespan context manager replaced it in 0.93+." |
| pyright | Not the Python jr-ad standard | "mypy is what the job ads ask for." |
| black separately | ruff format covers it | "ruff format is black-compatible since 0.4." |
| pytest <8 | Old, missing modern fixture features | "pytest 9.x is current." |
| dataclasses for API schemas | No JSON schema, no FastAPI binding | "Pydantic gives me OpenAPI + validation for free." |
| Supabase | PROJECT.md explicit ban | "Overlaps with my Apostes project — this piece is Postgres pur." |
| Vercel/Render | PROJECT.md explicit ban | "Already used in SST/Apostes; Fly.io is the differentiator." |
| MongoDB | Wrong shape for the data | "Stats are relational: leagues→teams→players→games." |
| fastapi-users | Hides the OAuth2/JWT mechanics | "I wanted to write the auth myself to learn it." |

---

## CI signals that prove this stack works

Reviewers landing on the GitHub repo should see at a glance:

1. **CI badge green** on README.
2. **`uv.lock` committed** + uv-based workflow in `ci.yml`.
3. **`ruff` + `mypy --strict` + `pytest --cov`** all pass.
4. **Coverage badge** (codecov.io free for public repos) ≥80%.
5. **Docker image build step** in CI (`docker build .`) — proves the Dockerfile is healthy.
6. **OpenAPI public URL** in README pointing to `https://<app>.fly.dev/docs`.

---

## Sources & confidence

| Claim | Source | Confidence |
|---|---|---|
| FastAPI 0.136.1 | PyPI JSON 2026-05-19, Context7 `/fastapi/fastapi` | HIGH |
| Pydantic 2.13.4 | PyPI JSON 2026-05-19 | HIGH |
| SQLAlchemy 2.0.49 | PyPI JSON 2026-05-19, Context7 `/websites/sqlalchemy_en_20` | HIGH |
| Alembic 1.18.4 | PyPI JSON 2026-05-19 | HIGH |
| ruff 0.15.13 | PyPI JSON 2026-05-19 | HIGH |
| mypy 2.1.0 | PyPI JSON 2026-05-19 | HIGH |
| pytest 9.0.3 | PyPI JSON 2026-05-19 | HIGH |
| httpx 0.28.1 | PyPI JSON 2026-05-19 (released 2024-12-06 — current) | HIGH |
| testcontainers 4.14.2 | PyPI JSON 2026-05-19 | HIGH |
| uv 0.11.15 | PyPI JSON 2026-05-19 | HIGH |
| asyncpg 0.31.0 / psycopg 3.3.4 | PyPI JSON 2026-05-19 | HIGH |
| python-jose 3.5.0 maintenance status | PyPI release date 2025-05-28 — last release ~12 months ago | MEDIUM (PyJWT swap recommended if reviewer pushes) |
| passlib 1.7.4 (2020-10-08) inactive | PyPI release date | MEDIUM (still works, argon2-cffi backend healthy) |
| Postgres 16.14 current minor | postgresql.org/support/versioning | HIGH |
| Fly.io free-tier policy 2026 | Verify at fly.io/docs/about/pricing before deploy | MEDIUM (policy changes have been frequent) |
| ruff replacing black/flake8/isort | Astral docs + community adoption | HIGH |
| uv replacing poetry/pip-tools in 2026 | Astral docs + Python ecosystem trend | MEDIUM-HIGH (rapidly accelerating but poetry still common) |

---

*Last updated: 2026-05-19 (research phase). Re-verify versions before each major milestone.*
