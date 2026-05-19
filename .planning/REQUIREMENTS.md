---
project: basketball-stats-api
created: 2026-05-19
updated: 2026-05-19
source: .planning/research/FEATURES.md (basquethero.cat scrape + tech showcase mapping)
status: v1-draft (pending Roger approval)
---

# Requirements v1 — Basketball Stats API

> **REQ-ID format:** `[CATEGORY]-[NUMBER]`. Categories: DOM (domain entities), READ (public read endpoints), AUTH (authenticated writes), STAT (advanced stats / showcase), INFRA (Docker, CI/CD, deploy), OBS (observability, docs, OpenAPI), TEST (testing infrastructure).
>
> Cada requirement ha de poder traduir-se a 1+ endpoint(s) o capacitat verificable. Out-of-scope explícit al final.

## v1 Requirements (MVP — must ship)

### Domain entities (DOM)

- [ ] **DOM-01:** Club entity (un club pot tenir múltiples equips, p.ex. CB Sabadell amb sènior + sub-22 + junior).
- [ ] **DOM-02:** Team entity (un team pertany a un club + una competition; un club pot tenir N teams).
- [ ] **DOM-03:** Player entity amb composite key `(license_id, dorsal, name)` — modelat com a entity normal amb índex únic; reflecteix sistema federatiu FCBQ.
- [ ] **DOM-04:** League / Competition entity amb tuple `(category, gender, territory, group, season, phase)`. Categories: Super Copa, Copa Catalunya, CC 1a, CC 2a, 1a Territorial, 3a Territorial. Phases: fase-previa, 2a-fase, playoff.
- [ ] **DOM-05:** Game / Match entity (data, equip local, equip visitant, marcador per quart Q1-Q4, marcador final, competition_id, phase_id, matchday).
- [ ] **DOM-06:** BoxScore entity per (game, player) amb camps: VAL, MIN, PTS, plus_minus, FG2M, FG2A, FG3M, FG3A, FTM, FTA, REB_OF, REB_DEF, AST, STL (REC), BLK (TAP), TOV (PER), FOULS (FC). VAL és **GENERATED COLUMN** (mostrar SQL showcase).
- [ ] **DOM-07:** Coach entity vinculada a un o més Teams (rol que pot pujar box-scores d'aquests teams).

### Public read endpoints (READ)

- [ ] **READ-01:** `GET /competitions` — llista competitions disponibles (filtres: category, gender, territory, season).
- [ ] **READ-02:** `GET /competitions/{id}/standings` — standings d'una competition (window function `RANK()` per posicions + tie-breakers FCBQ).
- [ ] **READ-03:** `GET /competitions/{id}/leaderboards?stat=val&limit=10` — leaderboard ordenat per stat (default `val`), window function `RANK() OVER (PARTITION BY competition_id ORDER BY avg_stat DESC)`.
- [ ] **READ-04:** `GET /teams/{id}` — fitxa equip (info + roster + properes partides + últimes partides).
- [ ] **READ-05:** `GET /players/{id}` — fitxa jugador (info + season averages + game log últims 10 partits).
- [ ] **READ-06:** `GET /players/{id}/stats?season=2025-26` — stats agregats d'un jugador per temporada (totals + per-game averages).
- [ ] **READ-07:** `GET /games/{id}` — detall partit (marcador per quart + box-score complet de tots els jugadors d'ambdós equips).
- [ ] **READ-08:** `GET /competitions/{id}/games?matchday=5` — llista games d'una jornada / matchday.
- [ ] **READ-09:** `GET /matchday/{date}/ideal-five` — millor cinc d'una jornada (1 PG, 1 SG, 1 SF, 1 PF, 1 C). Implementació: `RANK() OVER (PARTITION BY position ORDER BY composite_score DESC)` amb scoring `PTS + REB*1.2 + AST*1.5 + REC*2 - PER*1.5`. **Flagship endpoint del MVP — diferenciador real, query no trivial, no existeix als referents catalans (basquethero.cat inclòs), demo memorable a recruiter.** Promogut de v2 a MVP 2026-05-19 post-review.

### Auth + coach writes (AUTH)

- [ ] **AUTH-01:** Coach pot autenticar-se amb email + password (OAuth2 password flow + JWT bearer token, argon2id hash).
- [ ] **AUTH-02:** `POST /games` — coach autenticat pot crear un game amb el seu box-score complet en una sola request (transaction).
- [ ] **AUTH-03:** `PUT /games/{id}/boxscore` — coach autenticat (i propietari del team afectat) pot corregir un box-score.
- [ ] **AUTH-04:** `require_coach` dependency que valida JWT + role + ownership del team afectat.
- [ ] **AUTH-05:** Després d'un `POST /games` o `PUT /games/{id}/boxscore` → BackgroundTask recompute de season averages + standings cache invalidation.

### Stats avançats / showcases SQL (STAT)

- [ ] **STAT-01:** Standings query usa **window function** `RANK() OVER (PARTITION BY competition_id ORDER BY wins DESC, points_for - points_against DESC)`. Visible al fitxer `repositories/standings.py` amb comentari explicatiu.
- [ ] **STAT-02:** Leaderboard query usa **window function** + **composite index** `(competition_id, season, avg_stat DESC)`. Visible al fitxer `repositories/leaderboards.py`.
- [ ] **STAT-03:** Cerca de jugador per nom usa **tsvector + GIN index** (full-text search amb suport accents catalans). Endpoint `GET /search/players?q=...`.
- [ ] **STAT-04:** VAL del box-score com a **GENERATED COLUMN** Postgres (no calculat a Python). Migration visible amb expressió SQL FIBA PIR.
- [ ] **STAT-05:** Composite index `(game_date DESC, competition_id)` per queries de games per jornada. Visible al fitxer de migrations.

### Infra (INFRA)

- [ ] **INFRA-01:** `docker-compose.yml` engega `api` + `postgres:16` amb `docker compose up`. Healthchecks dependencies correctes (api espera postgres ready). **NO Redis al MVP** (carried out 2026-05-19 post-review — re-introduir només a v2).
- [ ] **INFRA-02:** `Dockerfile` multi-stage (builder + runtime) basat en `python:3.12-slim`. Image final < 200MB. `.dockerignore` exclou `.git`, `.venv`, `__pycache__`, `tests/`, `docs/`.
- [ ] **INFRA-03:** GitHub Actions CI workflow: `ruff check` + `mypy --strict` + `pytest` (unit + integration testcontainers) a cada push. Cache de uv per build ràpid.
- [ ] **INFRA-04:** GitHub Actions deploy workflow: on tag `v*.*.*` → build image + push a Koyeb registry + deploy + `alembic upgrade head` com a release_command.
- [ ] **INFRA-05:** Koyeb deploy del servei API + Neon Postgres free tier configurat amb `DATABASE_URL` via Koyeb secret. Health check a `/healthz`.
- [ ] **INFRA-06:** Seed script `data/seed/minimal.py` poblea DB amb 1 competition + 2 teams + 1 game + 12 box-scores. Executable amb `docker compose exec api python -m basketball_stats.seed.minimal`. **Necessari a Phase 2** (sense seed els READ endpoints retornen `[]` i no es pot smoke-test). Phase 5 afegirà `data/seed/real.py` amb dades reals del Sènior A de Roger (mateix script pattern, fitxer diferent). Promogut de P5 a P2 2026-05-19 post-review.

### Observability + docs (OBS)

- [ ] **OBS-01:** OpenAPI `/docs` (Swagger UI) i `/redoc` accessibles en prod amb totes les rutes documentades, tags per categoria, exemples per cada endpoint.
- [ ] **OBS-02:** Endpoint `/healthz` retorna `{ "status": "ok", "db": "ok" }` amb check real a Postgres (`SELECT 1`). Sense camp `cache` al MVP (Redis fora del MVP).
- [ ] **OBS-03:** Structured logging amb `structlog` (JSON output en prod, pretty en dev). Cada request té `request_id`.
- [ ] **OBS-04:** README amb secció "Stack walkthrough": cada eina del stack té (a) per què s'usa, (b) on s'usa al codi (file:line link), (c) què demostra al recruiter.
- [ ] **OBS-05:** `docs/adr/` amb mínim 6 ADRs (numerats 0001-000N): stack election, auth method, sync vs background ingest, cache strategy, deploy target switch a Koyeb, repository pattern decision.
- [ ] **OBS-06:** `AI_basketball-portfolio-defense.md` al root del projecte (tipus SST): stack + arquitectura + trade-offs + 7 Q&A típiques d'entrevista (window functions, async patterns, deploy choice, JWT vs sessions, etc.).
- [ ] **OBS-07:** README badges: CI status (GHA), code style (ruff), type checked (mypy), license, Python version.
- [ ] **OBS-08:** Cada Pydantic schema (Create/Read/Update) té `model_config = ConfigDict(json_schema_extra={"examples": [...]})` amb dades realistes en català (noms equip tipus "CB Granollers", jugadors amb dorsals reals, dates 2025-26 season). `/docs` mostra payload exemple a cada endpoint POST/PUT i resposta exemple a cada GET. Verificat manualment a `localhost:8000/docs`. Promogut de P5 a P2 2026-05-19 post-review (sense examples `/docs` es veu amateur).

### Testing (TEST)

- [ ] **TEST-01:** Unit tests sobre services + schemas + utils. Coverage mínim 70%.
- [ ] **TEST-02:** Integration tests amb `testcontainers` corre Postgres real (no SQLite, no mocks de DB). Coverage real de queries amb window functions + JSONB + tsvector. Visible al `tests/conftest.py` la fixture `postgres_container`.
- [ ] **TEST-03:** Tots els tests passen verds a CI abans de cada deploy. Sense skip / xfail sense issue tracker associat.

## v2 Requirements (post-MVP, deferred)

> Llistat com a hipòtesi de continuïtat; no es construeixen al MVP.

- **Redis cache amb invalidation explícita** a cada `POST /games`. Carried OUT of MVP 2026-05-19 post-review — afegir només quan hi hagi cas d'ús real (BackgroundTask del MVP funciona sense cache layer).
- JSONB play-by-play (mostrar JSONB showcase encara que MVP no en tingui dades reals).
- Endpoint `GET /matchday/{date}/mvp` — MVP individual de la jornada (window function `RANK()` + filtre per data + composite scoring).
- Streak detection (jugador / equip amb millor ratxa de victòries / VAL).
- Player development trend endpoint (window function `LAG` + temporal series).
- Free agents / fichajes endpoint (basquethero.cat differentiator).
- Multi-tenant SaaS (cada lliga té el seu workspace).
- WebSockets per live score updates durant un partit.

## Out of Scope (NO build — documenta perquè)

- **Frontend web/mobile dins aquest repo.** → Si Roger vol UI, repo separat `basketball-stats-web` amb Vite/React o Next.js.
- **Live ingest des de scoreboard físic / API externa de partits.** → Ingest només via POST manual de coaches.
- **Multi-tenant SaaS (workspaces per lliga).** → Single dataset, single seed. Multi-suport a v2 si surt natural.
- **Advanced NBA metrics (PER, BPM, TS%, eFG% computacionalment complexes).** → Per a portfolio, VAL/PIR + bàsics són suficients i alineats amb context català.
- **Shot charts.** → Cap referent català ho té; requereix coordenades de tir, no surten del PDF d'acta.
- **Push notifications mobile.** → No mobile target. Out of scope total.
- **Social features (likes, comments, follow).** → No xarxa social; portfolio API technical.
- **Betting / odds integration.** → Out of scope hard (conflict d'identitat amb projecte Apostes).
- **ML predictions (predict winners, MVP, etc.).** → Out of scope per MVP; serveixin a v3 si Roger vol portfolio ML.
- **GraphQL.** → REST clean és més legible per recruiter jr.
- **Deploy a Vercel / Render / Supabase / Fly.io.** → Vercel+Render bloquejats per regla anti-overlap SST/Apostes. Fly.io ja no té free tier (Oct 2024). Koyeb + Neon és el deploy escollit.
- **Cap servei que requereixi targeta de crèdit.** → Hard constraint Roger ($0 prod).
- **Test mocks de DB.** → testcontainers obligatori per als integration tests. Mocks només per unit puros (services sense DB).

## Traceability (filled by ROADMAP.md)

> Mapping REQ-ID → phase. Filled by gsd-roadmapper 2026-05-19.

| REQ-ID | Phase | Status |
|---|---|---|
| DOM-01 | Phase 2 | Pending |
| DOM-02 | Phase 2 | Pending |
| DOM-03 | Phase 2 | Pending |
| DOM-04 | Phase 2 | Pending |
| DOM-05 | Phase 2 | Pending |
| DOM-06 | Phase 2 | Pending |
| DOM-07 | Phase 2 | Pending |
| READ-01 | Phase 2 | Pending |
| READ-02 | Phase 2 | Pending |
| READ-03 | Phase 2 | Pending |
| READ-04 | Phase 2 | Pending |
| READ-05 | Phase 2 | Pending |
| READ-06 | Phase 2 | Pending |
| READ-07 | Phase 2 | Pending |
| READ-08 | Phase 2 | Pending |
| READ-09 | Phase 4 | Pending |
| AUTH-01 | Phase 3 | Pending |
| AUTH-02 | Phase 3 | Pending |
| AUTH-03 | Phase 3 | Pending |
| AUTH-04 | Phase 3 | Pending |
| AUTH-05 | Phase 3 | Pending |
| STAT-01 | Phase 2 | Pending |
| STAT-02 | Phase 2 | Pending |
| STAT-03 | Phase 4 | Pending |
| STAT-04 | Phase 2 | Pending |
| STAT-05 | Phase 2 | Pending |
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| INFRA-04 | Phase 4 | Pending |
| INFRA-05 | Phase 1 | Pending |
| INFRA-06 | Phase 2 | Pending |
| OBS-01 | Phase 2 | Pending |
| OBS-02 | Phase 1 | Pending |
| OBS-03 | Phase 1 | Pending |
| OBS-04 | Phase 5 | Pending |
| OBS-05 | Phase 5 | Pending |
| OBS-06 | Phase 5 | Pending |
| OBS-07 | Phase 1 | Pending |
| OBS-08 | Phase 2 | Pending |
| TEST-01 | Phase 1 | Pending |
| TEST-02 | Phase 2 | Pending |
| TEST-03 | Phase 3 | Pending |

**Coverage:** 43 / 43 v1 requirements mapped (100%). No orphans, no duplicates.

> Nota counting: original draft 40 REQs. Post-review 2026-05-19 afegits 3 nous (READ-09 ideal-five, OBS-08 schema examples, INFRA-06 seed minimal) → total 43 (DOM 7 + READ 9 + AUTH 5 + STAT 5 + INFRA 6 + OBS 8 + TEST 3 = 43).
