---
doc: architecture-research
project: basketball-stats-api
created: 2026-05-19
updated: 2026-05-19
confidence: HIGH
scope: ARCHITECTURE dimension only (stack is LOCKED upstream)
---

# Architecture Research — Basketball Stats API

**Goal:** Recruiter-legible FastAPI + Postgres + Docker + GHA + Fly.io REST API. Every choice must explain itself via folder structure + 1-line docstring/ADR pointer. **Legibility > cleverness.**

**Confidence:** HIGH — patterns are FastAPI/SQLAlchemy 2.0 community consensus 2025-2026 (FastAPI docs, `tiangolo/full-stack-fastapi-template`, `zhanymkanov/fastapi-best-practices`, SQLAlchemy 2.0 async docs).

---

## Section 1 — Project Layout

### Decision: `src/` layout (recommended)

**Why `src/` over flat:** `src/` layout prevents accidental imports of the working dir during tests (Python picks up local `./app/` even if not installed). With `src/`, you MUST install the package (`pip install -e .`) — same as production. Catches packaging bugs early. Recommended by `pypa/sampleproject` and `tiangolo/full-stack-fastapi-template` (2025 update).

### Full tree

```
basketball-stats-api/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # ruff + mypy + pytest on every push
│       └── deploy.yml                # build image + flyctl deploy on tag v*
├── .planning/                        # GSD planning (gitignored or kept)
│   ├── PROJECT.md
│   ├── ROADMAP.md
│   └── research/
├── docs/
│   ├── adr/
│   │   ├── 0001-stack-election.md
│   │   ├── 0002-auth-oauth2-jwt.md
│   │   ├── 0003-repository-pattern.md
│   │   ├── 0004-background-tasks-builtin.md
│   │   ├── 0005-cache-invalidation-strategy.md
│   │   └── 0006-deploy-fly-io.md
│   ├── STACK_WALKTHROUGH.md          # recruiter "tour" of every tool
│   └── diagrams/
│       └── architecture.png          # (optional) mermaid/excalidraw export
├── src/
│   └── basketball_stats/             # actual Python package
│       ├── __init__.py
│       ├── main.py                   # FastAPI app factory, router includes, lifespan
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py             # Pydantic Settings (env vars)
│       │   ├── db.py                 # async engine, AsyncSessionLocal, get_db()
│       │   ├── security.py           # JWT encode/decode, password hash
│       │   └── cache.py              # Redis client + key helpers (post-MVP)
│       ├── api/                      # HTTP layer — thin routers
│       │   ├── __init__.py
│       │   ├── deps.py               # FastAPI Depends() — get_db, current_user, settings
│       │   ├── v1/
│       │   │   ├── __init__.py       # APIRouter aggregator
│       │   │   ├── teams.py
│       │   │   ├── players.py
│       │   │   ├── games.py
│       │   │   ├── standings.py      # leaderboards + standings (read-heavy)
│       │   │   ├── auth.py           # /token (OAuth2 password flow)
│       │   │   └── health.py         # /healthz, /readyz
│       │   └── errors.py             # exception handlers → JSON
│       ├── models/                   # SQLAlchemy 2.0 — DB boundary
│       │   ├── __init__.py
│       │   ├── base.py               # DeclarativeBase, common columns (id, timestamps)
│       │   ├── team.py
│       │   ├── player.py
│       │   ├── game.py               # JSONB play_by_play column lives here
│       │   ├── box_score.py
│       │   └── user.py               # coach accounts
│       ├── schemas/                  # Pydantic v2 — API boundary
│       │   ├── __init__.py
│       │   ├── team.py               # TeamCreate, TeamRead, TeamUpdate
│       │   ├── player.py
│       │   ├── game.py
│       │   ├── box_score.py
│       │   ├── standings.py          # response models for leaderboards
│       │   └── auth.py               # Token, TokenPayload
│       ├── services/                 # business logic — orchestration
│       │   ├── __init__.py
│       │   ├── game_service.py       # ingest box_score + trigger recompute
│       │   ├── standings_service.py  # call repo + shape DTO
│       │   └── auth_service.py       # login, role check
│       ├── repositories/             # DB access — pure SQL/SQLAlchemy
│       │   ├── __init__.py
│       │   ├── base.py               # generic CRUD if useful
│       │   ├── team_repo.py
│       │   ├── player_repo.py
│       │   ├── game_repo.py
│       │   └── standings_repo.py     # window functions live here
│       └── tasks/                    # background jobs
│           ├── __init__.py
│           └── recompute_aggregates.py
├── migrations/                       # Alembic
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_add_jsonb_play_by_play.py
│       ├── 0003_add_tsvector_search.py
│       └── 0004_add_composite_index_standings.py
├── tests/
│   ├── conftest.py                   # testcontainers Postgres fixture, async client
│   ├── unit/
│   │   ├── test_standings_service.py
│   │   └── test_security.py
│   └── integration/
│       ├── test_games_api.py
│       ├── test_standings_api.py
│       └── test_auth_flow.py
├── scripts/
│   ├── seed.py                       # real-data seed: Roger's league
│   └── wait_for_db.py
├── .dockerignore
├── .env.example
├── .gitignore
├── .python-version                   # 3.11
├── Dockerfile                        # multi-stage, slim final image
├── docker-compose.yml                # api + postgres + redis
├── fly.toml                          # Fly.io app config
├── pyproject.toml                    # PEP 621 — deps, ruff, mypy, pytest config all here
├── alembic.ini
├── Makefile                          # make up / make test / make migrate (recruiter-friendly)
└── README.md                         # badges + 60s pitch + stack walkthrough link
```

**Single `pyproject.toml` for everything** (ruff, mypy, pytest, deps) — recruiters open one file and see all config. No scattered `.cfg`/`.ini` except `alembic.ini` (required).

---

## Section 2 — Component Boundaries

### Layer responsibilities

| Layer | Owns | Talks to | Never touches |
|---|---|---|---|
| `api/` (routers) | HTTP, status codes, request parsing, response serialization | `services/`, `schemas/`, `deps.py` | DB session directly, SQL |
| `schemas/` (Pydantic) | Wire format (request/response), validation | nothing (pure data) | DB, services |
| `services/` (business logic) | Use-case orchestration, transactions, multi-repo coordination | `repositories/`, `models/`, `core/cache.py` | FastAPI primitives (Request, Depends) |
| `repositories/` (DB access) | SQL queries, SQLAlchemy statements | `models/`, AsyncSession | HTTP, Pydantic schemas |
| `models/` (SQLAlchemy) | Table definitions, relationships | DB engine | API, services, schemas |
| `core/` | Cross-cutting infra: config, db engine, security, cache | env, libraries | domain logic |

**Hard rule:** routers never import `models/` directly. The conversion `models.Team → schemas.TeamRead` happens in services. Pydantic v2's `model_validate(orm_obj)` with `from_attributes=True` does the heavy lifting in one line.

### Pattern decision: Repository + Service (thin)

**Decision:** Use the Repository pattern for DB access, **thin Service layer** on top.

**Rationale:**
- **Repository** — isolates SQL/SQLAlchemy from business logic. Window functions, composite indexes, raw SQL hacks all live in `repositories/standings_repo.py`. **Recruiter sees `RANK() OVER (...)` in one obvious file.**
- **Service** — orchestrates 2+ repos or applies cross-entity rules (e.g., "POST /games inserts box_score AND triggers recompute"). Keeps routers under 20 lines.
- **Why not "service-only" (no repo)?** Pure service functions mixing SQL + business logic make the SQL showcases (window functions, JSONB, tsvector) invisible because they're scattered. Recruiter must hunt.
- **Why not "repo-only" (no service)?** Routers would orchestrate transactions and cross-entity rules — fat routers are an anti-pattern.

**Trap to avoid:** Don't build a generic `BaseRepository[T]` with 20 methods upfront. Start with concrete repos, extract `base.py` ONLY when 3+ repos share the same `get_by_id`/`list`/`delete` shape. YAGNI applies.

### Dependency Injection via `Depends(...)`

What goes through DI (in `api/deps.py`):

| Dependency | Scope | Why |
|---|---|---|
| `get_db() -> AsyncSession` | request | One session per request. Auto-close on response. Async context manager. |
| `get_current_user(token) -> User` | request | JWT decode + DB lookup. Reused across protected routes. |
| `require_coach(user)` | request | Role check. Composed via `Depends(get_current_user)`. |
| `get_settings() -> Settings` | process-cached | Pydantic Settings, `@lru_cache` so env parsed once. |
| `get_cache() -> Redis` | process | Singleton Redis client. |

What does NOT go through DI:
- Repositories — instantiated inside services with the injected `AsyncSession`. (Avoids `Depends(Depends(Depends(...)))` chains.)
- Services — same, instantiated by routers with their deps.

**Why:** Each `Depends()` adds a parameter to the router signature. Stop at the layer where injection actually buys testability (DB session, current user). Below that, plain constructors.

### Pydantic v2 specifics

- `BaseModel` with `model_config = ConfigDict(from_attributes=True)` for response models (replaces v1's `orm_mode`).
- Separate `*Create`, `*Read`, `*Update` per entity. Never reuse the SQLAlchemy model as a response schema (leaks internal columns like `password_hash`).
- `Annotated[str, Field(min_length=2, max_length=50)]` for validation in v2 style.

---

## Section 3 — Data Flow

### Flow A: Public read — `GET /api/v1/standings?league_id=1`

```
┌──────────┐
│  Client  │
└────┬─────┘
     │ HTTP GET /api/v1/standings?league_id=1
     ▼
┌─────────────────────────────────────────────┐
│ api/v1/standings.py :: list_standings()     │
│  - parse query (Pydantic)                   │
│  - Depends(get_db)                          │
│  - (post-MVP) Depends(get_cache) check key  │
└────┬────────────────────────────────────────┘
     │ if cache miss
     ▼
┌─────────────────────────────────────────────┐
│ services/standings_service.py               │
│  - call repo                                │
│  - shape into StandingsResponse DTO         │
└────┬────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────┐
│ repositories/standings_repo.py              │
│  SELECT team_id, wins, losses,              │
│    RANK() OVER (PARTITION BY league_id      │
│      ORDER BY wins DESC) AS position        │
│  FROM team_records WHERE league_id = :id    │
│  -- uses idx_team_records_league_wins       │
└────┬────────────────────────────────────────┘
     │ AsyncSession.execute()
     ▼
┌──────────────┐
│  Postgres    │
└────┬─────────┘
     │ rows
     ▼  service maps to schemas.StandingsRead
┌──────────┐
│  Client  │ JSON
└──────────┘
```

**Cache layer (post-MVP):** `standings:league:{id}` key, TTL 5 min, invalidated by Flow B.

### Flow B: Authenticated write — `POST /api/v1/games` (coach uploads box-score)

```
┌──────────┐
│  Coach   │ POST /api/v1/games  + Authorization: Bearer <jwt>
└────┬─────┘
     ▼
┌─────────────────────────────────────────────────┐
│ api/v1/games.py :: create_game()                │
│  - body: GameCreate (Pydantic v2 validates)     │
│  - Depends(require_coach)  ← composes:          │
│      oauth2_scheme → decode JWT → load User     │
│      → check role == "coach"                    │
│  - Depends(get_db)                              │
└────┬────────────────────────────────────────────┘
     ▼
┌─────────────────────────────────────────────────┐
│ services/game_service.py :: ingest_game()       │
│  async with session.begin():     ← transaction  │
│    game = game_repo.insert(payload)             │
│    box_repo.insert_many(payload.box_scores)     │
│  background_tasks.add_task(                     │
│    recompute_aggregates, league_id              │
│  )                                              │
│  cache.delete("standings:league:{id}")          │
└────┬────────────────────────────────────────────┘
     ▼
┌──────────────┐         ┌────────────────────────┐
│  Postgres    │         │ FastAPI BackgroundTask │
│  (committed) │         │  recompute_aggregates  │
└──────────────┘         │  - UPDATE team_records │
                         │  - refresh leaderboard │
                         └────────────────────────┘
     │
     ▼  return GameRead (201 Created)
┌──────────┐
│  Coach   │
└──────────┘
```

**Auth dependency chain (FastAPI composition):**
```
oauth2_scheme (extracts Bearer)
  → get_current_user (decodes JWT + loads User from DB)
    → require_coach (checks user.role == "coach", raises 403 otherwise)
```
Visible in `api/deps.py` — one file, 40 lines, recruiter reads end-to-end auth flow.

### Flow C: Background task — recompute aggregates

**Decision: FastAPI built-in `BackgroundTasks`** (NOT Celery/RQ/Arq for MVP).

**Rationale:**
- **Celery** — overkill. Requires broker (Redis/RabbitMQ) + separate worker process + Flower for monitoring. Adds 3 moving parts. Demonstrates infra but NOT proportional to value for "coach uploads 1 game/week".
- **RQ** — lightweight but still needs separate worker process. Same problem at smaller scale.
- **Arq** — async-native, smaller deps than Celery, but still a worker process.
- **FastAPI `BackgroundTasks`** — runs in the same process AFTER the response is sent. Zero extra infra. Demonstrates async patterns (the explicit goal in PROJECT.md). Perfect for "recompute after write" when work is <5s.

**When this breaks:** if recompute takes >30s or you have >10 writes/min. Neither applies to amateur basketball (1-10 games/week per league).

**Migration path documented in ADR-0004:** "If recompute exceeds 5s or write QPS >5, migrate to Arq" — shows recruiter you've thought about scale without over-engineering.

```
POST /games returns 201
  └─ AFTER response sent:
       BackgroundTasks runs recompute_aggregates(league_id)
         ├─ open new AsyncSession (request session is closed)
         ├─ UPDATE team_records SET wins=..., losses=... WHERE league_id=...
         ├─ (post-MVP) refresh materialized view leaderboard_mv
         └─ cache.delete("standings:league:{id}")
```

**Important:** background task must open its OWN session — `Depends(get_db)` session is closed by the time the task runs. Documented as a code comment + ADR-0004.

---

## Section 4 — Phase Sequence (for ROADMAP.md)

5 phases. Each phase ends in a green CI + deployable artifact. Each phase has a clear "showcase milestone" visible in the repo.

### Phase 1 — Foundation (skeleton + deploy hello-world)

**Goal:** Bare repo deployed to Fly.io with green CI. No business logic.

**Deliverables:**
- `pyproject.toml` with FastAPI + SQLAlchemy 2.0 async + Alembic + ruff + mypy + pytest
- `src/basketball_stats/main.py` exposes `GET /healthz` returning `{"status": "ok"}`
- `Dockerfile` (multi-stage) + `docker-compose.yml` (api + postgres + redis)
- `migrations/` initialized with empty initial revision
- `.github/workflows/ci.yml` runs ruff + mypy + pytest (1 trivial test)
- `fly.toml` + first deploy → `https://<app>.fly.dev/healthz` returns 200
- `README.md` skeleton with badge placeholders + `make up`/`make test` documented

**Showcase visible at end of phase:** GHA badge green on README, public Fly.io URL works.

**Dependencies:** none (greenfield start).

### Phase 2 — Core entities + public read

**Goal:** All read endpoints working with real data. **First two SQL showcases visible.**

**Deliverables:**
- Models: `Team`, `Player`, `Game`, `BoxScore`, `League`
- Alembic migration with composite index `(game_date DESC, league_id)` ← **SQL showcase #1**
- Repos + services + routers for: `GET /teams`, `GET /teams/{id}`, `GET /players/{id}`, `GET /games/{id}`, `GET /standings?league_id=`
- `standings_repo` uses `RANK() OVER (PARTITION BY league_id ORDER BY ...)` ← **SQL showcase #2 (window function)**
- `scripts/seed.py` with Roger's real league (1 league, 2-4 teams, 1-2 games)
- Integration tests via testcontainers Postgres — `tests/conftest.py` exposes `postgres_container` fixture ← **testcontainers showcase**
- OpenAPI `/docs` shows all 5+ endpoints with examples

**Showcase visible at end of phase:** Open `/docs` on prod URL → see standings endpoint → call it → get real data with `RANK()` computed in DB.

**Dependencies:** Phase 1 (skeleton + deploy).

### Phase 3 — Auth + coach writes

**Goal:** Coaches authenticate, upload box-scores. Background task recomputes aggregates.

**Deliverables:**
- `User` model with `role: Literal["coach", "admin"]`
- `core/security.py` — JWT encode/decode, bcrypt password hashing
- `POST /api/v1/auth/token` OAuth2 password flow (FastAPI Security)
- `api/deps.py` complete: `get_current_user`, `require_coach`
- `POST /api/v1/games` and `PATCH /api/v1/games/{id}` for coach uploads ← **auth showcase**
- `tasks/recompute_aggregates.py` triggered via `BackgroundTasks` ← **async background showcase**
- Integration tests: full auth flow (login → use token → write → verify recompute)

**Showcase visible at end of phase:** `/docs` shows lock icons on write endpoints. ADR-0002 explains why OAuth2 + JWT (not session cookies, not API keys).

**Dependencies:** Phase 2 (models + repos to write into).

### Phase 4 — Differentiators (rest of SQL showcases + cache)

**Goal:** Make the Postgres showcases that PROJECT.md mandates fully visible.

**Deliverables:**
- **JSONB**: `games.play_by_play JSONB` column. Endpoint `GET /games/{id}/play-by-play`. Visible in `models/game.py` with `Mapped[dict] = mapped_column(JSONB)` ← **SQL showcase #3**
- **Full-text search**: `tsvector` columns on `teams.name`, `players.full_name`. Endpoint `GET /search?q=...` ← **SQL showcase #4**
- **Materialized view (optional)** or simply a complex CTE for leaderboards filtered by stat (PPG, RPG, APG)
- **Redis cache** wired in: `standings_service` checks cache, invalidates on game write ← ADR-0005
- All migrations have `downgrade()` implementations ← **SQL showcase #5 (clean migration history)**

**Showcase visible at end of phase:** All 5 PROJECT.md SQL showcases are present in code, each with a comment pointing to ADR + STACK_WALKTHROUGH anchor.

**Dependencies:** Phase 3 (writes must exist before cache invalidation makes sense).

### Phase 5 — Polish + portfolio defense

**Goal:** Recruiter-ready. Roger can pass 30-min oral defense.

**Deliverables:**
- `README.md` full version: badges, 60s pitch, screenshots/curl examples, "Stack Walkthrough" section linking to `docs/STACK_WALKTHROUGH.md`
- `docs/STACK_WALKTHROUGH.md` — every tool, why chosen, where visible (anchored to files/lines)
- All 6 ADRs written (see tree in §1)
- `AI_basketball-portfolio-defense.md` — 7 Q&A typical interview questions (SST pattern)
- GitHub repo public, description set, topics tagged (`fastapi`, `postgres`, `docker`, `fly-io`)
- `.github/workflows/deploy.yml` triggers on `v*` tag — first prod release tagged `v0.1.0`

**Showcase visible at end of phase:** Recruiter lands on README, scrolls 30s, knows the entire stack + can click into `/docs` live.

**Dependencies:** Phase 4 (all features must be done to be documented honestly).

### Dependency graph

```
Phase 1 (foundation)
   │
   ▼
Phase 2 (entities + read)  ──┐
   │                         │
   ▼                         │
Phase 3 (auth + write)       │
   │                         │
   ▼                         │
Phase 4 (differentiators)    │
   │                         │
   ▼                         │
Phase 5 (polish)  ◄──────────┘
```

Strict linear order. No phase parallelism — solo developer, 1-2 week budget.

---

## Section 5 — Showcase Visibility Map

**Principle:** Every tool in the locked stack must be VISIBLE somewhere a recruiter can find in <30s of repo browsing. Doc mentions alone don't count.

| Tool / Concept | Where it's visible in code | Where it's documented |
|---|---|---|
| **FastAPI** | `src/basketball_stats/main.py` (app factory) + `api/v1/*.py` routers | README + STACK_WALKTHROUGH §FastAPI |
| **Pydantic v2** | `schemas/*.py` — every entity has `*Create`/`*Read`/`*Update` | STACK_WALKTHROUGH §Pydantic |
| **SQLAlchemy 2.0 async** | `models/*.py` use `Mapped[]` + `mapped_column()`; `core/db.py` uses `create_async_engine` | STACK_WALKTHROUGH §SQLAlchemy |
| **Postgres pur (no Supabase)** | `docker-compose.yml` (postgres:16-alpine service) + `fly.toml` (Fly Postgres attach) | ADR-0001 |
| **Alembic** | `migrations/versions/*.py` — visible filenames, each has docstring | ADR mentions, README "How to migrate" |
| **Window functions** | `repositories/standings_repo.py` — single SQL string with `RANK() OVER` + comment `# SQL showcase: window function` | STACK_WALKTHROUGH §SQL Showcases anchor |
| **JSONB** | `models/game.py` — `play_by_play: Mapped[dict] = mapped_column(JSONB)` | Same anchor |
| **Composite index** | `migrations/versions/0004_add_composite_index_standings.py` filename + docstring | Same anchor |
| **Full-text search (tsvector)** | `migrations/versions/0003_add_tsvector_search.py` + `repositories/search_repo.py` | Same anchor |
| **OAuth2 + JWT** | `core/security.py` (~40 lines) + `api/v1/auth.py` + `api/deps.py` `require_coach` | ADR-0002 |
| **Redis cache** | `core/cache.py` + service-layer `cache.get/set/delete` calls | ADR-0005 |
| **FastAPI BackgroundTasks** | `tasks/recompute_aggregates.py` + call site in `game_service.ingest_game()` | ADR-0004 |
| **pytest + httpx** | `tests/integration/*.py` use `AsyncClient` against the app | README "Testing" section |
| **testcontainers** | `tests/conftest.py` — `@pytest.fixture postgres_container` fixture (~20 lines, very readable) | STACK_WALKTHROUGH §Testing |
| **ruff** | `pyproject.toml` `[tool.ruff]` section | Badge in README |
| **mypy --strict** | `pyproject.toml` `[tool.mypy] strict = true` | Badge in README |
| **Docker** | `Dockerfile` (multi-stage, commented) at root | README §Local Dev |
| **Docker Compose** | `docker-compose.yml` at root, ≤40 lines, well-commented | README §Local Dev |
| **GitHub Actions** | `.github/workflows/ci.yml` (~30 lines) + `deploy.yml` (~25 lines) | Badge in README |
| **Fly.io** | `fly.toml` at root + `.github/workflows/deploy.yml` uses `superfly/flyctl-actions` | ADR-0006 |
| **OpenAPI** | `/docs` live in prod — link in README directly | README hero section |

**Single-source recruiter index:** `docs/STACK_WALKTHROUGH.md` has table-of-contents with anchors so a recruiter can ctrl-F any tool.

---

## Section 6 — Fly.io Deploy Architecture

### `fly.toml` sketch

```toml
app = "basketball-stats-api"
primary_region = "mad"   # Madrid — close to Roger + EU latency

[build]
  dockerfile = "Dockerfile"

[deploy]
  release_command = "alembic upgrade head"
  strategy = "rolling"

[env]
  PORT = "8080"
  LOG_LEVEL = "info"
  PYTHONUNBUFFERED = "1"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = "stop"     # free tier: scale to zero
  auto_start_machines = true
  min_machines_running = 0

  [[http_service.checks]]
    interval = "15s"
    timeout = "2s"
    grace_period = "10s"
    method = "GET"
    path = "/healthz"

[[vm]]
  size = "shared-cpu-1x"
  memory = "256mb"
```

### Postgres: Fly Postgres (recommended)

**Decision:** Fly Postgres (their managed offering on top of a Fly app), attached via `fly postgres attach`.

**Rationale:**
- **Free tier viable:** 1× shared-cpu-1x + 1GB volume = $0 within Fly's free allowances (as of 2025-2026 — verify at deploy time, terms shift).
- **Single-vendor simplicity:** one `flyctl` command attaches DB to app, sets `DATABASE_URL` secret automatically.
- **Alternative considered: Neon free tier** — viable, but adds a second vendor. Reject for portfolio simplicity. Migration path documented in ADR-0006 if Fly Postgres pricing changes.
- **Alternative considered: Supabase free Postgres** — BLOCKED by PROJECT.md "no overlap with Apostes" rule.

**Setup commands (documented in README §Deploy):**
```bash
flyctl launch --no-deploy
flyctl postgres create --name basketball-stats-db --region mad
flyctl postgres attach basketball-stats-db
# sets DATABASE_URL secret automatically
flyctl secrets set JWT_SECRET=$(openssl rand -hex 32)
flyctl secrets set REDIS_URL=...   # post-MVP
flyctl deploy
```

### Env vars management

All via `flyctl secrets set` (encrypted at rest, injected at runtime):

| Secret | Source | Used by |
|---|---|---|
| `DATABASE_URL` | auto-set by `flyctl postgres attach` | `core/db.py` async engine |
| `JWT_SECRET` | manual, generated with openssl | `core/security.py` |
| `REDIS_URL` | manual (post-MVP, Upstash free tier) | `core/cache.py` |
| `LOG_LEVEL` | `fly.toml [env]` (non-secret) | uvicorn/structlog |

`.env.example` at repo root documents all keys (no values). `core/config.py` Pydantic `Settings` reads from env with defaults for local dev.

### Health check

`GET /healthz` — implemented in `api/v1/health.py`:
- **MVP version:** returns `{"status": "ok"}` with 200. Used by Fly's HTTP check (see fly.toml).
- **Optional /readyz** — pings DB with `SELECT 1` and returns 200 only if DB reachable. Used for "ready to receive traffic" semantics. Fly uses `/healthz` for liveness only.

Why two endpoints? Kubernetes/Fly idiom; demonstrates awareness of liveness vs readiness. Single endpoint also fine for MVP — document the choice in ADR.

### Migration strategy on deploy

**Mechanism:** `[deploy] release_command = "alembic upgrade head"` in `fly.toml`.

**Behavior:**
1. `flyctl deploy` builds and pushes Docker image.
2. Fly spins up a one-off VM from the new image.
3. Runs `alembic upgrade head` — applies any pending migrations.
4. If exit code 0 → proceeds to rolling deploy of app VMs.
5. If exit code ≠ 0 → deploy aborts, old version stays running.

**Why this is the right pattern:**
- Migration happens BEFORE traffic shifts. App never starts with mismatched schema.
- Rollback safety: if migration fails, prod is unaffected.
- Visible: recruiter opens `fly.toml`, sees `release_command`, instantly understands deploy flow.
- ADR-0006 documents the choice + downside (long migrations block deploy — acceptable for amateur basketball scale).

### CI/CD wiring

`.github/workflows/deploy.yml` triggers on `v*` tag:

```yaml
name: Deploy
on:
  push:
    tags: ['v*']
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

`ci.yml` (push to main, PRs):

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: mypy src
      - run: pytest -v
```

Total ~30 lines per workflow. Recruiter-readable in 30s.

---

## Open questions for follow-up research (PITFALLS dimension)

- Confirm Fly.io free tier limits as of 2026-05 (machine-hours, Postgres storage).
- Confirm testcontainers-python compatibility with `pytest-asyncio` + SQLAlchemy 2.0 async (assumed compatible; verify with smoke test).
- Confirm Pydantic v2 + FastAPI version compatibility matrix at project start (FastAPI ≥0.100 required for Pydantic v2).
- Validate that single-process `BackgroundTasks` survives Fly's `auto_stop_machines = "stop"` — if machine stops between response and task completion, task is lost. Mitigation: keep `min_machines_running = 1` OR migrate to Arq with persistent queue in Phase 4.

---

*Confidence: HIGH on layout/boundaries/data-flow (community consensus). MEDIUM on Fly.io free-tier specifics (verify at deploy time — terms drift). Phase ordering reflects PROJECT.md success criteria 1:1.*
