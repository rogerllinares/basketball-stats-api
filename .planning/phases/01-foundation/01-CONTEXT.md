# Phase 1: Foundation - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Skeleton end-to-end deployable: container builds, GHA CI verde (ruff + mypy --strict + pytest), Koyeb sirve la imatge a una URL pública, Neon Postgres connectada, i `GET /healthz` retorna `{status:ok, db:ok}` amb un `SELECT 1` real. Zero business logic, zero domain entities. Tot el pipeline (build → test → migrate → deploy → healthcheck) provat sense escriure features.

**Out of scope per a Phase 1** (re-direccionat a phases posteriors):
- Cap entitat de domini (Team, Player, Game, BoxScore, etc.) — Phase 2.
- Cap endpoint públic més enllà de `/healthz` — Phase 2.
- Auth + JWT — Phase 3.
- Deploy-on-tag automation (`INFRA-04`) — Phase 4. P1 fa primer deploy manual via `koyeb deploy`.
- Stack walkthrough complet al README (`OBS-04`) — Phase 5. P1 stub.
- ADRs detallats — Phase 5. P1 crea només `docs/adr/.gitkeep` + ADR-0001 (stack election) com a baseline.

</domain>

<decisions>
## Implementation Decisions

### Skeleton Layout

- **D-01: src/ layout amb `src/basketball_stats/`** — `pip install -e .` obliga a treballar com en producció; intercepta packaging bugs aviat. Consensus `pypa/sampleproject` + `tiangolo/full-stack-fastapi-template`. Defense per recruiter: "evita imports accidentals del working dir durant tests".
- **D-02: Pre-creem l'arbre complet d'ARCHITECTURE.md des de P1** — `api/v1/`, `core/`, `models/`, `schemas/`, `services/`, `repositories/`, `tasks/` tots existeixen al primer commit amb `__init__.py` buits. Pro: P2 ja té els forats per omplir, el recruiter veu l'arquitectura completa el dia 1 (Repository+Service pattern visible abans que hi hagi codi). Con acceptat: arbre amb subdirs buits — mitigació: cada `__init__.py` té un docstring d'una línia explicant què viurà allà ("Phase 2: SQLAlchemy 2.0 models — Team, Player, Game, BoxScore, League, Coach").
- **D-03: Només `__init__.py` als subdirs sense codi P1** — NO creem `models/team.py`, `models/player.py` etc. amb stubs `# TODO`. Pro: cap fitxer fake al primer commit; quan P2 crei `team.py` és contingut real. Carriage del decision-tree: ARCHITECTURE.md llista els fitxers concrets de cada subdir però es materialitzen quan toca la phase corresponent.
- **D-04: Subdirs amb codi P1** — `core/` (config.py, db.py), `api/v1/` (health.py, deps.py minimal), `api/errors.py` (exception handlers globals des de P1 — mitiga P1.6 pitfall "recruiters veuen Python tracebacks").
- **D-05: tests/ split en `unit/` + `integration/` des de P1** — P1 hi té 1-2 tests cadascun (smoke `/healthz` integration, settings parsing unit). Pro: convenció establerta del primer commit; P2 expandeix sense refactor d'estructura.

### Alembic

- **D-06: Inicialitzar Alembic en P1 amb revision `0001_baseline.py` buida** — `upgrade() pass`, `downgrade() pass`. Pro: el pipeline `alembic upgrade head` es valida a CI + a Koyeb release_command **abans que la primera entity arribi**. Si `alembic.ini` / `env.py` async-aware tenen bugs, emergeixen aquí, no a P2 amb stress de modelar 7 entities alhora. Defense: "Phase 1 validates the migration pipeline as infrastructure; Phase 2 adds the first real schema migration on a proven pipeline."
- **D-07: `env.py` async-aware des del P1** — Compatible amb async engine (research/ARCHITECTURE.md). `target_metadata = Base.metadata` apuntant a `models.base.Base` (que existirà encara que sense subclasses).
- **D-08: CI valida round-trip de migracions** — Step extra a `ci.yml`: `alembic upgrade head && alembic downgrade base && alembic upgrade head` contra testcontainers Postgres. Mitiga P3.1 pitfall ("migrations without working downgrade()" = CV liability) des del primer commit. Defense: "every migration is reversible by CI gate, not by convention."

### Health Endpoints

- **D-09: Single `/healthz` endpoint amb DB probe real** — Compleix OBS-02 literal (`{status:"ok", db:"ok"}` amb `SELECT 1`). NO afegim `/readyz` separat al P1 (scope creep — la separació liveness/readiness és K8s idiom valuós però el spec ja diu `/healthz` amb DB check; documentar a ADR-0007 si emergeix necessitat). Defense per recruiter: "el spec va decidir un endpoint únic perquè Koyeb HTTP check espera una sola URL; la separació K8s pure ve quan migrem a multi-replica."
- **D-10: Comportament en fallida DB** — `/healthz` retorna **HTTP 503** amb body `{"status":"degraded", "db":"fail", "error":"<sanitized>"}` si `SELECT 1` raises. Koyeb HTTP check auto-restart configurat per a 5 fallades consecutives → la instància es reinicia (no es queda penjada amb DB caiguda). Pro: comportament cloud-native correcte; recruiter veu "production thinking". Defense: "503 vs 200 amb status:degraded — el codi HTTP és el contracte que Koyeb llegeix, el body és per a humans."
- **D-11: BackgroundTask NO usat al P1** — `/healthz` és síncron-async normal (ruta async amb `await session.execute(select(1))`). BackgroundTasks és pattern Phase 3 (AUTH-05 recompute).

### Python + Tooling

- **D-12: Python 3.12 (pin via `.python-version` + `pyproject.toml`)** — INFRA-02 ja especifica `python:3.12-slim`. PROJECT.md diu "3.11+" però la versió concreta no estava locked. Decideixo **3.12** (estable a 2026-05, supportada fins 2028-10, més recent vs `tiangolo/full-stack-fastapi-template` que ja l'usa). `.python-version` + `requires-python = ">=3.12"` a `pyproject.toml`. Defense: "3.12 té noves syntax errors clearer + performance gains; pin explícit evita drift entre dev/CI/prod."
- **D-13: `uv` com a package manager + `uv.lock` committed** — uv 0.11.15 verificat al research. `uv.lock` versionat al repo (deterministic builds entre dev/CI/Koyeb). Dev deps separades via `[dependency-groups] dev = [...]` (PEP 735 — uv idiom 2026). Defense: "uv = 10-100× pip; lockfile committed elimina 'works on my machine' entre Roger + GHA + Koyeb builder."
- **D-14: `pyproject.toml` PEP 621 = single source of config** — `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`, deps, version, all in one file. Defense: "recruiter obre 1 fitxer i veu tot — sense `.cfg`/`.ini` scattered. `alembic.ini` és l'única excepció (requerit per Alembic)."

### CI/CD (P1 scope)

- **D-15: Single Python version a CI, NO matrix** — ubuntu-latest + Python 3.12. Matrix multi-version és over-engineering per a solo dev portfolio (deploy target és un sol Python; matrix afegeix CI time sense valor demostratiu).
- **D-16: testcontainers a CI des de P1** — El test smoke `/healthz` necessita DB session real per validar `SELECT 1`. `tests/conftest.py` exposa `postgres_container` fixture (`PostgresContainer("postgres:16-alpine")`). `TESTCONTAINERS_RYUK_DISABLED=true` a CI env (mitiga P5.2 — ryuk reaper container penja jobs). Defense: "testcontainers funcional des del primer commit elimina sorpreses a P2 quan el coverage de window functions explota; P1 = wiring, P2 = volum."
- **D-17: uv cache a GHA** — `astral-sh/setup-uv@v3` action amb `enable-cache: true`. Build < 2 min, total CI ruff+mypy+pytest+migration-roundtrip < 5 min (success criterion #2).
- **D-18: CI corre sobre push + PR a `main`** — Pre-merge gate. Tag-based deploy ve a P4 (INFRA-04); P1 no té `deploy.yml`. Pro: visible que la CI **gate** existeix abans que automation deploy; recruiter veu workflow split entre `ci.yml` (gate) i `deploy.yml` (action, P4).

### Observability (P1 scope)

- **D-19: structlog JSON output en prod, console renderer en dev** — Detect via env var `ENV=prod|dev` a `core/config.py`. `LOG_LEVEL` configurable. Defense: "JSON logs són parseables per qualsevol log aggregator (Koyeb el té built-in); console mode en dev és per a humans."
- **D-20: Custom ASGI middleware per `request_id`** — Accepta inbound header `X-Request-Id` si està present (distributed tracing across services); genera UUID4 si no. Binda a `structlog.contextvars` perquè cada log line dins la request inclou `request_id` automàticament. Retorna `X-Request-Id` al response header. Defense: "demostra awareness de distributed tracing patterns sense importar OpenTelemetry full stack (que seria scope creep per a un MVP solo)."
- **D-21: Badges al README des de P1** — CI status (GHA), ruff, mypy, Python 3.12, license MIT. Cinc badges al header del README. Pro: visible des del primer commit; CI verda = badge verda dia 1. Mitiga P6.6 pitfall.

### Docker

- **D-22: Multi-stage Dockerfile basat en `python:3.12-slim`** — Builder stage: uv sync. Runtime stage: copy `.venv` + src. Image < 200 MB (INFRA-02). Non-root user al runtime. BuildKit cache mount per uv (`--mount=type=cache,target=/root/.cache/uv`). Defense per mida: "una stage runtime sense uv ni cache d'apt ens deixa sota 200 MB; Koyeb cold start sub-segon."
- **D-23: `.dockerignore` complet des del primer commit** — Inclou `.venv`, `.git`, `__pycache__`, `*.pyc`, `.env*`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `tests/`, `htmlcov`, `.planning/`. Mitiga P4.3 (secrets leak) + P4.1 (image bloat).
- **D-24: docker-compose.yml: api + postgres (sense Redis)** — Postgres 16-alpine, named volume `pg_data` (mitiga P4.4 data loss), healthcheck `pg_isready` + `depends_on: condition: service_healthy` (mitiga P4.5 race condition).
- **D-25: API container amb bind-mount de `src/` en dev + `uvicorn --reload`** — Dev experience instant; en prod (Koyeb) corre sense reload + sense bind-mount, només la imatge built.

### Repository hygiene + GitHub setup (P1)

- **D-26: GitHub remote creat en P1, repo PUBLIC des del primer push** — Necessari per als badges (GHA badges només funcionen amb repo accessible). Pro: contribution graph signal accumula des de 2026-05 fins al hiring window 2026-09 (mitiga P6.10 "dead repo"). Roger ja té el repo gitignored al vault, ja és git inicialitzat; només falta `gh repo create roger-llinares/basketball-stats-api --public --source=. --remote=origin --push`.
- **D-27: `.gitignore` exhaustiu abans del primer push** — `.env*`, `.venv`, `__pycache__`, `*.pyc`, `htmlcov`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `dist/`, `.coverage`. Mitiga P6.5 (secrets committed) abans que pugui passar.
- **D-28: Pre-commit hooks instal·lats en P1** — `pre-commit-config.yaml` amb: ruff (lint + format), gitleaks (secret scan), mypy --strict, conventional commits enforcement. `pre-commit install` a setup local. CI re-corre les mateixes hooks com a safety net. Defense per recruiter: "conventional commits + gitleaks pre-commit = senyal de production discipline; el repo no acumula `wip` / `fix` commits ni secrets accidentals (P6.3 + P6.5 mitigats by design)."
- **D-29: Dependabot config (`.github/dependabot.yml`)** — Weekly checks per pip + GHA actions. Pro: contribution activity visible al graph encara que Roger no toqui codi; recruiter veu PRs merged regularment (P6.9 + P6.10 mitigats).

### README scope en P1

- **D-30: README mínim-viable per a P1** — Estructura:
  1. **1-line pitch** + screenshot placeholder de `/docs` (omplir-lo en P2 quan hi hagi endpoints).
  2. **Badges row** (CI, ruff, mypy, Python 3.12, license).
  3. **Live URL** stub (`https://basketball-stats-api-<slug>.koyeb.app/healthz`).
  4. **Local dev**: `docker compose up` + esperar healthcheck + `curl localhost:8000/healthz`.
  5. **Deploy**: pointer a `docs/setup/koyeb-neon.md`.
  6. **Stack walkthrough**: placeholder "Phase 5 polish — see [TODO]". Stub honest, no claims false.
- **D-31: `docs/setup/koyeb-neon.md` step-by-step en P1** — Roger executa manualment durant P1 execute però queda documentat al repo per al next person. Inclou: create Neon project, create Koyeb account, set `DATABASE_URL` + `JWT_SECRET` (per P3) com a Koyeb secrets, primer `koyeb app create` + deploy. Defense: "el deploy de P1 és manual i documentat; P4 afegeix l'automation (deploy-on-tag) sobre setup ja provat."
- **D-32: `docs/adr/0001-stack-election.md` baseline en P1** — Documenta les decisions LOCKED de PROJECT.md (FastAPI, Postgres pur via Neon, Koyeb, uv, testcontainers). Pro: ADRs comencen a P1 amb una base, no apareixen de cop a P5 (mitigació P6.8 "I know X without showing it"). Les altres 5+ ADRs creixen per phase: 0002-auth-method (P3), 0003-background-tasks (P3), 0004-window-functions (P2 o P4), 0005-redis-dropped (P5 polish), 0006-koyeb-switch (referenciat aquí, completat P5), 0007-health-vs-readyz (P5 polish opcional).

### Claude's Discretion (Roger delegated portfolio-best judgment)

Roger va dir "haz lo que sea mejor para el portfolio y documenta que haces y porque para que yo luego pueda explicarlo". Totes les decisions D-09 a D-32 són Claude's discretion documentades amb rationale defensable a interview. Cap decisió oculta — totes amb "Defense:" o "Pro:/Con:" explícits.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level (LOCKED, no re-debate)
- `.planning/PROJECT.md` — Stack lockat 2026-05-19 + Out of Scope explícit + Success Criteria del projecte.
- `.planning/REQUIREMENTS.md` §INFRA + §OBS + §TEST — 8 REQ-IDs de P1 (INFRA-01/02/03/05, OBS-02/03/07, TEST-01).
- `.planning/ROADMAP.md` §"Phase 1: Foundation" — Goal + 5 Success Criteria literals + dependency graph.
- `.planning/STATE.md` §"Accumulated Context" — Decisions cumulades post-review 2026-05-19.

### Research (HIGH confidence, frozen 2026-05-19)
- `.planning/research/SUMMARY.md` — Síntesi consolidada per phase.
- `.planning/research/STACK.md` — Versions verificades PyPI (FastAPI 0.136.1, Pydantic 2.13.4, SQLAlchemy 2.0.49, uv 0.11.15, argon2-cffi).
- `.planning/research/ARCHITECTURE.md` §1 (Project Layout `src/`), §2 (Repository+thin Service), §5 (Showcase Visibility Map per a P1 tools), §6 (Fly.io deploy architecture — adaptar a Koyeb mantenint el patró `release_command` + secrets via CLI).
- `.planning/research/PITFALLS.md` — Top 10 perills. Per a P1 específicament: P4.1 (image bloat), P4.2 (pip cache layer), P4.3 (.dockerignore secrets), P4.4 (Postgres volume loss), P4.5 (depends_on race), P5.2 (testcontainers ryuk), P5.3 (CI vs local divergence), P6.5 (.env committed), P6.6 (CI badge red/missing), P6.9 (outdated deps), P6.10 (dead repo).
- `.planning/research/FEATURES.md` — Scrape basquethero.cat. NO consumit per P1 (zero domain entities) — referenciat per coherència, P2 l'utilitzarà.

### External docs to verify durant planning/execute
- Koyeb docs: https://www.koyeb.com/docs (free tier limits, `koyeb` CLI, secrets management, HTTP healthcheck config) — el research va canviar Fly.io→Koyeb però els passos exactes del CLI cal verificar-los a P1 execute.
- Neon docs: https://neon.tech/docs (free tier limits actuals 2026, connection pooling string format, branch model si aplica).
- uv docs: https://docs.astral.sh/uv/ (PEP 735 `[dependency-groups]`, lockfile semantics, GHA action `astral-sh/setup-uv`).
- structlog docs: https://www.structlog.org/en/stable/ (contextvars binding, JSON renderer config, FastAPI/Starlette middleware integration).
- testcontainers-python: https://testcontainers-python.readthedocs.io/ (PostgresContainer 16-alpine, ryuk disable env var).
- Alembic async docs: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic (env.py template async-aware).

No external specs/ADRs propis encara — aquest projecte és greenfield. Els ADRs creixen per phase (vegeu D-32).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
**Cap codi previ** — el repo està al commit root `2c7310d` amb només `.planning/` populat. P1 és el first feature commit.

### Established Patterns
**Cap pattern previ al projecte.** Patterns que aquesta phase ESTABLEIX per a tot el codebase:
- `src/` layout amb `pip install -e .` workflow.
- Pydantic Settings a `core/config.py` amb env_file + defaults.
- Async engine + `AsyncSessionLocal` factory + `get_db()` dependency a `core/db.py` (template directament de PITFALLS P1.3, mateix patró que `tiangolo/full-stack-fastapi-template`).
- FastAPI lifespan context manager (NO `@app.on_event` — deprecated, P1.2 pitfall mitigated).
- Exception handlers globals a `api/errors.py` (P1.6 mitigated).
- structlog JSON + request_id via custom middleware.
- ruff + mypy --strict configurats a `pyproject.toml`.
- testcontainers per a integration tests.

Tots aquests patterns es validen al P1 amb 1 endpoint (`/healthz`) i s'expandeixen a la resta de phases sense modificar-los.

### Integration Points
**Inbound:** Cap (P1 és el first push).
**Outbound:** Koyeb HTTP healthcheck → `/healthz`. Neon Postgres → `DATABASE_URL` secret a Koyeb.

</code_context>

<specifics>
## Specific Ideas

- **Defense-first rationale** — Roger va delegar les decisions amb la consigna "documenta que haces y porque para que yo luego pueda explicarlo". Cada decision D-01..D-32 té un bloc "Defense:" o "Pro:/Con:" que serveix com a guió d'entrevista. El downstream planner ha de **preservar aquests rationales** als comentaris del codi (docstring d'una línia al fitxer de cada decision) perquè recruiter pugui obrir el fitxer i veure el "perquè" sense buscar als ADRs encara incompletes.
- **Mirror del SST gate** — El projecte té success criteria explícitament alineats amb el patró SST (deploy verificat + README walkthrough + ADRs + portfolio-defense doc). Aquest paral·lelisme és intencional; mantenir-lo a totes les phases.
- **Anti-overlap rule** — Hard constraint del project: cap line que toqui Vercel / Render / Supabase / Next.js / React / Spring. Si emergeix temptació de "podríem afegir un mini frontend per veure-ho" → bloqueig automàtic, repo separat `basketball-stats-web` algun dia. P1 NO té aquest risc però documentat per coherència.

</specifics>

<deferred>
## Deferred Ideas

- **`/readyz` separat de `/healthz`** — La separació K8s-style (liveness vs readiness) és un pattern valuós però scope creep per a P1 (el spec OBS-02 vol un sol endpoint amb DB check). Si emergeix necessitat (e.g., scale a multi-replica on volem readiness probes diferents del liveness) → ADR-0007 al P5 polish.
- **OpenTelemetry full stack** — Tracing distribuït complet (traces + metrics + structured logs amb trace_id correlat) és scope creep. P1 fa request_id custom middleware com a "pre-OpenTelemetry" pattern. Si Roger vol portfolio observability avançat → milestone v2.
- **Materialized views per a leaderboards** — Mencionat al research/ARCHITECTURE.md §3 com a optional. Defer a P4 si emergeix necessitat real (window function probably suficient per al volum amateur).
- **Matrix CI multi-Python** — Out of scope per a solo dev project. Si algun moment el projecte té contributors externs → matrix.
- **Conventional commits enforcement via commitlint server-side** — P1 enforça via pre-commit local. Server-side (Husky equivalent + GHA check del commit message) afegit només si emergeix necessitat (i.e., Roger no se l'autoaplica).

### Out-of-MVP ideas surfaced during analysis (registered, not acted upon)
- **JWT_SECRET rotation strategy** — P3 introdueix JWT; rotation policy és v2.
- **Multi-region Koyeb deploy** — Single region (fra/par/mad sigui el més proper a Catalunya) per a MVP. Multi-region és overkill.
- **Custom domain (basketball-stats.cat?)** — Out of scope MVP; `*.koyeb.app` subdomain és suficient. Si Roger vol → P5 polish opcional.

</deferred>

---

*Phase: 1-foundation*
*Context gathered: 2026-05-19*
