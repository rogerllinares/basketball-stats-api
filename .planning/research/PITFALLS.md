---
project: basketball-stats-api
doc: PITFALLS
created: 2026-05-19
updated: 2026-05-19
researcher: Claude (gsd-new-project research phase)
overall_confidence: HIGH
---

# Domain Pitfalls — Basketball Stats API

**Scope:** FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + Postgres 16 + Alembic + Docker Compose + GitHub Actions + Fly.io. Stack LOCKED per `PROJECT.md`. Pitfalls below are specific to this stack and to the project's role as **portfolio piece for the Sep 2026 job hunt**.

**Sources verified:** Context7 (FastAPI `/websites/fastapi_tiangolo`, SQLAlchemy `/websites/sqlalchemy_en_20_orm`), Fly.io docs + community 2024-2026, WebSearch cross-check. Confidence HIGH unless noted.

---

## Bucket 1 — FastAPI / Pydantic v2

### P1.1 — Sync DB call inside async route blocks event loop
- **Warning signs**
  - Route declared `async def` but body calls `requests.get(...)`, `time.sleep(...)`, `session.execute()` on a sync SQLAlchemy `Session`, or any blocking I/O.
  - Throughput collapses under load > a handful of concurrent requests; uvicorn worker stuck.
- **Prevention**
  - Either: route is `async def` AND every I/O is `await` (AsyncSession, httpx.AsyncClient). Or: route is plain `def` and FastAPI offloads it to a threadpool automatically. Never mix.
  - Rule of thumb on PR review: `grep -nE "async def" routes/ | xargs -I{} ...` — if file has `async def` and `requests.` or `Session(` → flag.
- **Phase:** Phase 2 (API skeleton) — establish the convention from the first endpoint. Re-check in `/qa` of every later phase.

### P1.2 — `@app.on_event("startup"/"shutdown")` is deprecated (Context7 verified)
- **Warning signs**
  - Training-data code samples still use `@app.on_event("startup")`. Deprecation warning visible at boot.
- **Prevention**
  - Use `lifespan` async context manager from day 1:
    ```python
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # startup: open engine, warm caches
        yield
        # shutdown: dispose engine
    app = FastAPI(lifespan=lifespan)
    ```
  - DB engine creation and `engine.dispose()` belong here, not module top-level.
- **Phase:** Phase 2 (API skeleton).

### P1.3 — `Depends()` scope confusion: session reused across requests
- **Warning signs**
  - `DetachedInstanceError`, stale data, or "session is already in use" under concurrent load.
  - Dependency built as module-level singleton instead of per-request.
- **Prevention**
  - Standard pattern (memorize, copy-paste each project):
    ```python
    async def get_db() -> AsyncIterator[AsyncSession]:
        async with AsyncSessionLocal() as session:
            yield session
            # commit/rollback handled explicitly in route or via middleware
    ```
  - Never cache `AsyncSession` at app level. `Depends(get_db)` in every route.
- **Phase:** Phase 2.

### P1.4 — Pydantic v1 patterns leak from training data
- **Warning signs**
  - `class Config:` instead of `model_config = ConfigDict(...)`.
  - `orm_mode = True` instead of `from_attributes=True`.
  - `@validator` instead of `@field_validator` / `@model_validator`.
  - `.dict()` instead of `.model_dump()`; `parse_obj` instead of `model_validate`.
- **Prevention**
  - First file written should establish base schema with v2 idioms; all subsequent schemas inherit.
  - `ruff` rule `UP` (pyupgrade) catches some. Add `bugbear` for behaviour.
- **Phase:** Phase 2.

### P1.5 — Response model serialization leaks ORM fields
- **Warning signs**
  - `/docs` shows `password_hash`, internal IDs, or relationship lists with circular refs.
  - 500 errors on JSON serialization of `datetime`/`Decimal` without explicit config.
- **Prevention**
  - Every public endpoint has `response_model=SomeRead` schema. Never return the ORM model directly.
  - `Read` schemas pick only public fields; use `Field(exclude=True)` for safety.
- **Phase:** Phase 2 (set pattern), Phase 3 (auth — protect `User.hashed_password`).

### P1.6 — No structured error responses → recruiters see Python tracebacks
- **Warning signs**
  - `/docs` examples respond `{"detail": "Internal Server Error"}` or raw 500 with traceback.
- **Prevention**
  - Register `app.exception_handler(IntegrityError)`, `RequestValidationError` overrides, and a generic `Exception` handler in prod (only logs traceback, returns sanitized envelope `{error: code, message, request_id}`).
- **Phase:** Phase 2.

---

## Bucket 2 — SQLAlchemy 2.0 async

### P2.1 — Implicit lazy-load on async session raises `MissingGreenlet`
- **Warning signs** (Context7 verified)
  - Accessing `team.players` after the `await session.execute(...)` returns → `sqlalchemy.exc.MissingGreenlet`.
  - Tests pass when one row loaded; explode when relationship traversed in a loop.
- **Prevention**
  - Forbid lazy by configuration at the relationship level:
    ```python
    players: Mapped[list["Player"]] = relationship(lazy="raise_on_sql")
    ```
  - Each query that touches a relationship uses `selectinload(...)` (collections) or `joinedload(...)` (one-to-one):
    ```python
    stmt = select(Team).options(selectinload(Team.players))
    ```
  - `selectinload` is the right default for the leaderboard/box-score domain (one-to-many).
- **Phase:** Phase 2 (models), Phase 3 (queries hit the wall first).

### P2.2 — N+1 in standings / leaderboards
- **Warning signs**
  - `/standings` route fires hundreds of SELECTs for a 12-team league (visible in `echo=True` logs).
  - Latency > 1s on tiny dataset.
- **Prevention**
  - Aggregate at SQL layer: a single query returning `team, wins, losses, points_for, points_against, RANK() OVER (...)`.
  - Never compute aggregates in Python by walking relationships.
- **Phase:** Phase 3 (leaderboards/standings are the Postgres showcase).

### P2.3 — SQLAlchemy 1.x syntax in training-data examples
- **Warning signs**
  - `session.query(Team).filter_by(...).all()` (1.x legacy style).
  - `relationship("Player", backref="team")` (2.0 prefers `back_populates` + `Mapped[]`).
- **Prevention**
  - Use 2.0 idioms exclusively: `select()` + `session.execute()` / `session.scalars()`. `Mapped[]` annotations on every column.
  - Quick grep gate: `grep -rn "session.query\|filter_by\|backref=" src/` — must return zero.
- **Phase:** Phase 2.

### P2.4 — Commit/rollback semantics wrong → silent data loss or zombie transactions
- **Warning signs**
  - Tests show writes "succeeded" but row not present after restart.
  - `session.commit()` called twice; `session.close()` missing in error paths.
- **Prevention**
  - Centralize in dependency:
    ```python
    async def get_db():
        async with AsyncSessionLocal() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise
    ```
  - Or do commit at route level explicitly. **Pick one and document in ADR.**
- **Phase:** Phase 2.

---

## Bucket 3 — Postgres 16 + Alembic

### P3.1 — Migrations without working `downgrade()` → CV liability
- **Warning signs**
  - `def downgrade(): pass` in generated migrations.
  - PR review: nobody has ever run `alembic downgrade -1` locally.
- **Prevention**
  - CI step: `alembic upgrade head && alembic downgrade base && alembic upgrade head` against testcontainers Postgres. Forces every migration to round-trip.
  - REQ-INFRA gate of the success criteria already calls for this — wire it.
- **Phase:** Phase 4 (CI), but the discipline starts Phase 2.

### P3.2 — `CREATE INDEX` without `CONCURRENTLY` locks the table
- **Warning signs**
  - Migration creates a GIN/composite index inside the auto-generated transaction → `ACCESS EXCLUSIVE` lock.
  - On Fly.io free-ish Postgres with 1 connection, deploy hangs.
- **Prevention**
  - For index creation migrations, disable the transaction wrapper and use `CONCURRENTLY`:
    ```python
    # in migration
    def upgrade():
        op.execute("COMMIT")  # exit transaction
        op.execute("CREATE INDEX CONCURRENTLY ix_games_date_league ON games (game_date DESC, league_id)")
    # plus: revision-level: transactional_ddl = False / mark as non-transactional
    ```
  - For demo dataset sizes (< 10k rows) it doesn't matter functionally, but **documenting this in an ADR is a recruiter signal**.
- **Phase:** Phase 3 (indexes for leaderboards) + ADR.

### P3.3 — JSONB play-by-play unindexed → O(N) scans
- **Warning signs**
  - Query like `WHERE pbp @> '[{"player_id": 7}]'::jsonb` does seq scan (visible in `EXPLAIN`).
- **Prevention**
  - GIN index on the JSONB column with `jsonb_path_ops` operator class for `@>` queries:
    ```sql
    CREATE INDEX ix_games_pbp_gin ON games USING GIN (pbp jsonb_path_ops);
    ```
  - Document operator usage in ADR: `->` returns JSON, `->>` returns text, `@>` containment.
- **Phase:** Phase 3.

### P3.4 — tsvector via app code instead of `GENERATED ... STORED`
- **Warning signs**
  - Application writes both `name` and `name_tsv` columns, easy to forget.
  - Trigger-based approach pollutes migration history.
- **Prevention** (modern Postgres ≥ 12, verified for PG 16)
  - Generated column kept in sync by Postgres itself:
    ```sql
    name_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', coalesce(name, ''))) STORED
    ```
  - GIN index on `name_tsv`. App writes only `name`.
- **Phase:** Phase 3 (full-text search showcase).

### P3.5 — Window function over un-indexed sort key
- **Warning signs**
  - `RANK() OVER (PARTITION BY league_id ORDER BY ppg DESC)` on a 5k-row table goes 600ms.
- **Prevention**
  - Composite index aligned with the `PARTITION BY ... ORDER BY ...`:
    ```sql
    CREATE INDEX ix_pstats_league_ppg ON player_season_stats (league_id, ppg DESC);
    ```
  - Run `EXPLAIN (ANALYZE, BUFFERS)` once and paste output in the leaderboard ADR. Big recruiter signal.
- **Phase:** Phase 3.

### P3.6 — Connection pool sized larger than DB max_connections
- **Warning signs**
  - `FATAL: sorry, too many clients already` under modest load.
  - `pool_size=20, max_overflow=10` against a Postgres with `max_connections=22`.
- **Prevention**
  - Free-ish managed Postgres typically caps low (Fly Postgres: depends on plan; assume 20-30 if unmanaged).
  - Set explicitly: `create_async_engine(url, pool_size=5, max_overflow=5, pool_pre_ping=True, pool_recycle=1800)`.
  - For a 1-instance Fly deploy, 5+5 is plenty.
- **Phase:** Phase 4 (deploy).

---

## Bucket 4 — Docker / Docker Compose

### P4.1 — Image bloated by using `python:3.11` instead of slim
- **Warning signs**
  - `docker images` shows api image > 800 MB.
  - Fly deploy push is slow; cold start adds seconds.
- **Prevention**
  - Multi-stage Dockerfile:
    ```dockerfile
    FROM python:3.11-slim AS builder
    RUN pip install --user -r requirements.txt
    FROM python:3.11-slim
    COPY --from=builder /root/.local /root/.local
    ENV PATH=/root/.local/bin:$PATH
    ```
  - Target < 200 MB. Mention size in README.
- **Phase:** Phase 1 (Docker baseline).

### P4.2 — `pip install` busted on every code change (no layer caching)
- **Warning signs**
  - `docker build` reruns `pip install` whenever any `.py` changes → 1-2 min rebuild loop.
- **Prevention**
  - Copy `pyproject.toml` / `requirements.txt` first, install, then copy source:
    ```dockerfile
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    COPY ./src ./src
    ```
  - Use BuildKit cache mount: `RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt`.
- **Phase:** Phase 1.

### P4.3 — Missing `.dockerignore` → ships `.venv/`, `.git/`, `__pycache__/`, `.env`
- **Warning signs**
  - Image > 1 GB out of nowhere.
  - Worse: `.env` leaks into image → secrets in registry.
- **Prevention**
  - `.dockerignore` from day 1:
    ```
    .venv
    .git
    __pycache__
    *.pyc
    .env
    .env.*
    .pytest_cache
    .mypy_cache
    .ruff_cache
    htmlcov
    ```
- **Phase:** Phase 1.

### P4.4 — Postgres data lost on `docker compose down`
- **Warning signs**
  - Bind-mount missing or anonymous volume; `down` wipes seed data.
- **Prevention**
  - Named volume:
    ```yaml
    volumes:
      pg_data:
    services:
      postgres:
        volumes:
          - pg_data:/var/lib/postgresql/data
    ```
  - `down` (no `-v`) preserves. `down -v` is the only wipe.
- **Phase:** Phase 1.

### P4.5 — API container starts before Postgres ready → flaky boot
- **Warning signs**
  - First `docker compose up` fails 50% of the time with `connection refused`.
  - `depends_on: postgres` without `condition: service_healthy` doesn't wait.
- **Prevention**
  - Postgres healthcheck + condition:
    ```yaml
    postgres:
      healthcheck:
        test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER}"]
        interval: 2s
        timeout: 3s
        retries: 10
    api:
      depends_on:
        postgres:
          condition: service_healthy
    ```
- **Phase:** Phase 1.

---

## Bucket 5 — GitHub Actions + Fly.io

### P5.1 — **CRITICAL: Fly.io has no free tier for new accounts (since Oct 2024)**
- **Warning signs**
  - `PROJECT.md` says "Fly.io free tier" — verified via Fly docs + community 2024-2026: free allowances **removed for new signups**. New accounts get 2 VM-hours or 7 days trial, then card required, then pay-as-you-go (~$3-5/month realistic minimum for tiny app + Postgres).
  - Cost-budget constraint "$0 prod" + "cap línia que requereixi targeta" in PROJECT.md is **currently incompatible** with the locked deploy target.
- **Prevention** — Roger decides one of:
  1. **Accept ~$3-5/month** as portfolio investment, keep Fly.io (still cheap, still differentiator).
  2. **Switch deploy target** to one of: Railway (free tier exists 2026 but small), Koyeb (free web service tier), self-host on Oracle Cloud Free Tier (always-free VM), or Hetzner (€4 VPS — still differentiator vs Vercel/Render).
  3. **Keep Fly.io spec'd but mark deploy as paid before launch** in ADR; ship Docker Compose + GHA build, defer prod URL.
- This must be resolved at roadmap time. **Stack is locked but pricing reality isn't, and PROJECT.md success criterion 2 requires a public URL.**
- **Phase:** Decided in roadmap (before Phase 4). Confidence HIGH (verified web + Fly docs 2024-2026).

### P5.2 — testcontainers in CI needs Docker daemon available
- **Warning signs**
  - testcontainers works locally, fails in CI with `Could not connect to Docker host`.
- **Prevention**
  - GitHub-hosted runners (`ubuntu-latest`) ship Docker — testcontainers works out of the box, no `services:` block needed.
  - Avoid `services: postgres` because then you're testing against the GHA-managed service, not real testcontainers (loses the differential).
  - Set `TESTCONTAINERS_RYUK_DISABLED=true` in CI to avoid the reaper container hanging the job.
- **Phase:** Phase 4 (CI).

### P5.3 — Tests pass locally, fail in CI
- **Warning signs**
  - Timezone-dependent assertions (`datetime.now()` on TZ-naive comparisons).
  - Locale-dependent string sort.
  - Different Postgres version local (16) vs CI image (15).
- **Prevention**
  - Pin Postgres image tag in testcontainers: `PostgresContainer("postgres:16-alpine")`.
  - All datetimes UTC + `timezone.utc`-aware. Add `TZ=UTC` to CI env.
  - Run CI image locally periodically: `act` or matching `python:3.11-slim` tag.
- **Phase:** Phase 4.

### P5.4 — `FLY_API_TOKEN` secret handling
- **Warning signs**
  - Token in plaintext anywhere in the repo or workflow YAML.
  - Token never rotated; same one across personal accounts.
- **Prevention**
  - `gh secret set FLY_API_TOKEN` (account-scoped or org-scoped token from `fly tokens create deploy`).
  - Workflow uses `env: FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}` only in deploy job, not on every step.
  - Use `flyctl deploy --remote-only` so build runs on Fly's builders (no Docker layer leakage in GHA logs).
- **Phase:** Phase 4.

### P5.5 — Deploy-on-every-merge → noisy, expensive, and breaks free trials fast
- **Warning signs**
  - Every PR merge triggers a prod deploy; rollbacks frequent.
- **Prevention**
  - Tag-based deploy: deploy job triggers only on `tags: ['v*']`. Manual `git tag vX.Y.Z && git push --tags`.
  - Tagging discipline = perceived as production-minded. **Document in ADR.**
- **Phase:** Phase 4.

### P5.6 — `release_command` migration failure locks deploy
- **Warning signs**
  - `release_command = "alembic upgrade head"` in `fly.toml`; if it fails (bad SQL, network), the new release never goes live but the old one keeps running. Easy to miss in logs.
- **Prevention**
  - Always run `alembic upgrade head` in CI before tagging — never as the only safety net.
  - Monitor `fly releases` after every deploy. If `release_command` exits non-zero, fix in a new commit, don't `--force`.
- **Phase:** Phase 4.

---

## Bucket 6 — Portfolio (recruiter red flags)

### P6.1 — "Just CRUD" — no Postgres showcase visible from the README
- **Warning signs**
  - README walkthrough talks features, never shows the window function, GIN index, or `EXPLAIN` plan.
  - Recruiter clicks → sees three vanilla `select(...).filter()` queries → moves on.
- **Prevention**
  - README has a **"SQL highlights"** section with code snippet of the leaderboard query (RANK + composite index), the JSONB containment query (with EXPLAIN), and the tsvector search. 3 snippets, each 10 lines, with a 1-line "why this is non-trivial".
  - `AI_basketball-portfolio-defense.md` (already in REQ-DOCS) is the 30-min walkthrough — write the SQL section first.
- **Phase:** Phase 3 (build them) + Phase 5 (docs).

### P6.2 — Tests are 100% mocked → integration story collapses on first interview question
- **Warning signs**
  - `tests/` has `Mock(spec=Session)` everywhere; no testcontainers run.
  - "What happens if your migration has a typo?" → no answer.
- **Prevention**
  - Pyramid: unit (schemas, business logic), integration (testcontainers + real Postgres + migrations applied), e2e (httpx `AsyncClient` against the lifespan-started app).
  - Coverage of the **leaderboard SQL** must be integration, not unit. That's where the differentiator lives.
- **Phase:** Phase 2 onwards. Enforce in CI.

### P6.3 — Garbage commit history: "wip", "fix", "stuff"
- **Warning signs**
  - `git log --oneline` looks like a chat log.
- **Prevention**
  - Conventional commits enforced locally: `feat:`, `fix:`, `chore:`, `docs:`. Add `commitlint` or just a pre-commit hook.
  - On dirty branches, squash into atomic commits before PR. One commit = one logical change.
  - Roger already follows this in vault commits; carry over.
- **Phase:** Ongoing.

### P6.4 — No README walkthrough → recruiter doesn't find the gold
- **Warning signs**
  - README is auto-generated `pip install` instructions only.
  - No "What to look at first" section.
- **Prevention**
  - README structure (in this order):
    1. One-line pitch + screenshot of `/docs`.
    2. Live demo link.
    3. **"Recruiter quickstart" — 5 files to look at, 1 line each.**
    4. Stack walkthrough table (already in REQ-DOCS).
    5. Local setup.
    6. ADRs link.
- **Phase:** Phase 5 (docs) — but stub Phase 1.

### P6.5 — `.env` / API keys committed
- **Warning signs**
  - `git log -p -- .env` returns content. `gh-secret-scan` flags.
- **Prevention**
  - `.gitignore` includes `.env*` before first commit. `.env.example` only.
  - `pre-commit` with `detect-secrets` or `gitleaks`.
  - If leaked: rotate token immediately, then BFG. Recruiter who sees a secret in history won't ask.
- **Phase:** Phase 1 + ongoing.

### P6.6 — CI badge red or missing on README
- **Warning signs**
  - `main` branch with failing builds visible publicly.
  - No badges at all = recruiter assumes no CI.
- **Prevention**
  - Add badges from day 1, even if they go red — they go green when you fix it, which is the point.
  - Required: build/lint/test status, coverage (codecov free tier OK), Python version.
- **Phase:** Phase 4.

### P6.7 — `/docs` not accessible in production
- **Warning signs**
  - Deploy hides `/docs` behind auth or sets `docs_url=None`.
- **Prevention**
  - Leave `/docs` open in prod for portfolio. This is **the** showcase route — recruiters open it before code.
  - If genuine concern: gate `/redoc` and `/openapi.json` but keep `/docs` visible.
- **Phase:** Phase 4.

### P6.8 — "I know Postgres" without showing it
- **Warning signs**
  - README claims "Advanced SQL with Postgres" → grep repo → only `INSERT/SELECT *`.
- **Prevention**
  - The 5 obligatory Postgres showcases from PROJECT.md (window functions, JSONB, composite indexes, FTS, reversible migrations) **each must be linkable in README** by filename + line range.
- **Phase:** Phase 3 + Phase 5.

### P6.9 — Outdated deps (FastAPI 0.95, Pydantic v1, SQLAlchemy 1.4)
- **Warning signs**
  - `requirements.txt` pinned to old versions; `pip-audit` flags CVEs.
- **Prevention**
  - Pin to current major (`fastapi>=0.115,<0.130`, `pydantic>=2.8`, `sqlalchemy>=2.0.30`).
  - Dependabot enabled on the repo. Even just merging Dependabot PRs is recruiter-visible activity.
- **Phase:** Phase 1 + ongoing.

### P6.10 — Dead repo (no commits in 30+ days at hiring time)
- **Warning signs**
  - GitHub contribution graph cold around Sep 2026 (the hiring window).
- **Prevention**
  - Even after MVP, ship one small visible improvement per week through the job hunt: an ADR, a query optimization, a new endpoint. The contribution graph **is** the signal.
- **Phase:** Post-MVP, ongoing through Sep 2026.

---

## Phase-Specific Warnings (cross-bucket lookup)

| Phase (TBD by roadmap, expected) | Pitfalls to address |
|---|---|
| **Phase 1 — Bootstrap (Docker, repo, CI scaffolding)** | P4.1, P4.2, P4.3, P4.4, P4.5, P6.5, P6.9 |
| **Phase 2 — API skeleton + models + auth scaffold** | P1.1, P1.2, P1.3, P1.4, P1.5, P1.6, P2.1, P2.3, P2.4, P3.1 (start) |
| **Phase 3 — Postgres showcases (queries, indexes, FTS, JSONB)** | P2.1, P2.2, P3.2, P3.3, P3.4, P3.5, P6.1, P6.8 |
| **Phase 4 — CI/CD + Deploy** | P3.1 (CI round-trip), P3.6, P5.1 (must be resolved!), P5.2, P5.3, P5.4, P5.5, P5.6, P6.6, P6.7 |
| **Phase 5 — Docs, ADRs, defense doc, polish** | P6.1, P6.4, P6.8 |
| **Ongoing (every PR)** | P1.1, P6.3, P6.5, P6.10 |

---

## Top 10 Pitfalls Overall (prioritized — these will sink the project)

1. **P5.1 — Fly.io has no free tier for new accounts (2024+).** PROJECT.md cost-budget conflict. Must resolve at roadmap time. *Confidence HIGH.*
2. **P2.1 — Async lazy-load = `MissingGreenlet` in prod.** Whole codebase pattern, not a one-off. Get it right Phase 2 or rewrite. *Context7 verified.*
3. **P6.1 / P6.8 — Postgres showcases not visible from README.** If the recruiter can't find the window function in 60 seconds, the whole differentiation premise dies. *Recruiter-facing, project-critical.*
4. **P1.1 — Sync DB call inside async route.** Single-bug class that silently kills throughput. Junior interview red flag if discovered.
5. **P3.1 — Migrations without working `downgrade()`.** Easy to ignore, called out by ADR-reading senior engineers.
6. **P6.2 — Mocked-everything tests.** testcontainers is the differentiator; if not actually used, the README claim is a lie under interview probing.
7. **P5.5 — Deploy-on-every-merge.** Either burns Fly trial fast or just looks unprofessional. Tag-based deploy = signal.
8. **P3.3 / P3.5 — Unindexed JSONB / window function showcases.** If the showcase queries are slow on demo data, it backfires harder than not having them.
9. **P1.2 — `@app.on_event` deprecated.** Trivial to fix, but having it triggers "outdated training data" in recruiter's head. *Context7 verified.*
10. **P6.5 — `.env` / secrets committed.** Instant-fail. Set `.gitignore` + `gitleaks` pre-commit before first push.

---

*Last updated: 2026-05-19 (initial research, pre-roadmap).*
