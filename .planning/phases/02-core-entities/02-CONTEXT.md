# Phase 2: Core entities + public read - Context

**Gathered:** 2026-05-20
**Status:** Ready for planning

<domain>
## Phase Boundary

API pública complerta amb totes les entitats del domini català FCBQ modelades (Club, Team, Player, Competition, Game, BoxScore, Coach + Roster + Season), tots els 8 GET endpoints (READ-01..08) servint dades reals d'un seed minimal, i window functions Postgres visibles al codi com a diferenciador del stack. Inclou: VAL com a GENERATED COLUMN STORED, REB total com a 2n GENERATED COLUMN, composite index `(competition_id, season, avg_stat DESC)` per leaderboards, composite index `(game_date DESC, competition_id)` per llistes de games, integration tests testcontainers cobrint queries amb window functions, exemples Pydantic v2 en català renderitzant a `/docs`, seed minimal `data/seed/minimal.py` (1 competition + 2 teams + 1 game + 12 box-scores), pagination offset/limit a totes les list endpoints. Zero writes (escriure ve a P3 AUTH). Zero auth (P3). Zero tsvector/full-text search (P4 STAT-03). Zero `/ideal-five` (P4 READ-09). Zero deploy automation (P4 INFRA-04). README screenshot `/docs` placeholder de P1 omplert aquí.

**Out of scope per a Phase 2** (re-direccionat a phases posteriors):
- Auth + JWT — P3.
- Writes (POST/PUT) + BackgroundTask recompute — P3.
- `/ideal-five` flagship endpoint — P4.
- tsvector + GIN + accents search — P4 (NOTA: la normalització UPPER+sense-accents a P2 facilita P4).
- Deploy on tag automation — P4.
- ADRs detallats al README walkthrough — P5.
- Defense doc + 6 ADRs complets — P5.
- Materialized table per a season averages — diferit; window functions on-the-fly són suficients a escala amateur.
- **FCBQ Ingest CLI** — Phase 2.5 separada (post-P2-ship, `/gsd-insert-phase`). Phase 2 segueix amb seed minimal manual fictiu en català.

</domain>

<decisions>
## Implementation Decisions

### Entity Shape & Identity

- **D2-01: Player PK híbrid — surrogate `id INT` PK + `UNIQUE(license_id, dorsal, normalized_name)`.** Internament identitat = `id` simple (FKs d'1 columna a totes les taules relacionades — BoxScore, Roster). Externament, l'API exposa el composite via URL slug pattern de basquethero: `GET /players/<license_id>-<dorsal>-<slug>` (e.g. `/players/80121-5-rafael-pinto`). Payloads inclouen els 3 camps federatius com identitat pública. Defense per recruiter: "modeling federatiu visible a l'API, normalitzat internament — best of both worlds. URL pattern fidel a basquethero. Risc de cascada UPDATE per typo accent aïllat: només `players` row es modifica, FKs intactes."

- **D2-02: Normalització obligatòria a totes les entitats amb nom — `UPPER + sense accents + TRIM`.** Aplicat a `players.normalized_name`, `teams.normalized_name`, `clubs.normalized_name`. Storage convention: e.g. "Rafael Pintó" → `"RAFAEL PINTO"`. Original name stored a camp paral·lel `players.display_name`/`teams.display_name`/`clubs.display_name` (case-sensitive UTF-8 amb accents) per a output API/UI. Justificació: la FCBQ utilitza majúscules sense accents a les actes oficials; normalitzar facilita matching de CLI scraper de Phase 2.5 + tsvector preprocessing de P4. Funció utility Python pura: `normalize_name(s: str) -> str` (unicodedata NFD + filter category != Mn + upper + strip).

- **D2-03: Team permanent + Roster M:N taula separada.** `teams (id, club_id, display_name, normalized_name)` viu eternament (no és season-scoped). Relació Player↔Team via taula intermèdia `rosters (player_id, team_id, season_id, dorsal_at_season, joined_at, left_at NULL)` — un jugador pot tenir N Rosters al llarg de N temporades al mateix Team. Dorsal pot canviar per season → stored a Roster, no a Player. Tracking històric complet (e.g. "5 temporades al CB Granollers"). Defense: "pattern federatiu real, capture how players cycle through teams". Cost acceptat: 1 taula extra (rosters) + 1 JOIN al consultar plantilla actual.

- **D2-04: Coach ↔ Team relation = M:N join table `coaching_assignments`.** Schema `(coach_id, team_id, season_id, role, started_at, ended_at NULL)`. Un coach pot dirigir múltiples teams (sènior + sub-22). Un team pot canviar de coach mid-season (started_at + ended_at gestiona historial). Coach entity en sí (DOM-07) té només info bàsica (id, license_id, normalized_name, display_name). Authentication camps (email, password_hash) afegits a P3 AUTH-01.

- **D2-05: Phase = enum column `competitions.phase` (valors: `fase_previa`, `segona_fase`, `playoff`).** Cada combinació `(category, gender, territory, group_no, season_id, phase)` genera un `competition_id` distint. Implicació: standings i leaderboards per `competition_id` són naturalment per-phase (no requereixen filtre WHERE phase=X). Cross-phase agregat ("millor anotador sumant les 3 phases d'una season") és endpoint addicional fora MVP (defer si emergeix). Si emergeix necessitat de dates/format diferents per phase → promoure a entitat pròpia futur (ADR).

- **D2-06: Schema entitats final per P2 (9 taules — més 2 GENERATED COLUMNS a `box_scores`):**
  ```
  clubs            (id PK, display_name, normalized_name UNIQUE, created_at)
  seasons          (id PK, start_year, label UNIQUE)  -- e.g. (1, 2025, "2025-26")
  competitions     (id PK, category, gender, territory, group_no, season_id FK, phase ENUM,
                    UNIQUE(category, gender, territory, group_no, season_id, phase))
  teams            (id PK, club_id FK, display_name, normalized_name, UNIQUE(club_id, normalized_name))
  players          (id PK, license_id INT, dorsal_default INT, display_name, normalized_name,
                    UNIQUE(license_id, dorsal_default, normalized_name))
  coaches          (id PK, license_id INT NULL, display_name, normalized_name,
                    UNIQUE(license_id, normalized_name))
  rosters          (PK (player_id, team_id, season_id), dorsal_at_season INT, joined_at, left_at NULL)
  coaching_assignments  (PK (coach_id, team_id, season_id), role, started_at, ended_at NULL)
  games            (id PK, competition_id FK, matchday_no INT, game_date DATE,
                    home_team_id FK, away_team_id FK,
                    q1_home INT, q1_away INT, q2_home, q2_away, q3_home, q3_away, q4_home, q4_away,
                    total_home INT, total_away INT)
  box_scores       (PK (game_id, player_id), team_id FK, min INT,
                    pts, plus_minus, fg2m, fg2a, fg3m, fg3a, ftm, fta,
                    reb_of, reb_def, ast, rec, tap, per, fc,
                    fouls_drawn INT NOT NULL DEFAULT 0,
                    blocks_received INT NOT NULL DEFAULT 0,
                    reb GENERATED ALWAYS AS (reb_of + reb_def) STORED,
                    val GENERATED ALWAYS AS (
                      pts + (reb_of + reb_def) + ast + rec + tap + fouls_drawn
                      - (fg2a - fg2m) - (fg3a - fg3m) - (fta - ftm)
                      - per - fc - blocks_received
                    ) STORED)
  ```

### VAL / PIR formula

- **D2-07: VAL formula = PIR FIBA literal (no variant ponderada de basquethero).** GENERATED ALWAYS AS STORED. Expressió SQL completa visible a la migration (STAT-04 + SC3 LOCKED del ROADMAP). Schema inclou `fouls_drawn` i `blocks_received` (camps que l'acta FCBQ Territorial NO registra però la Supercopa SÍ — clarificat per Roger 2026-05-20). Default `NOT NULL DEFAULT 0` per ambdós → formula PIR FIBA funciona sense COALESCE.

- **D2-08: ADR-0003 documenta asimetria `val` per nivell de competició.** Per a Supercopa (i altres categories on FCBQ registra detalles), el VAL és PIR FIBA literal exacte. Per a Territorial (on `fouls_drawn` i `blocks_received` no es registren), el VAL és PIR FIBA aproximat amb defaults 0 → pot subestimar lleugerament jugadors defensius. Defense honest: "schema uniform, dades varien per nivell. Implemento l'estàndard internacional PIR. ADR detalla els límits." Aquest ADR és **scope de P2** (no defer a P5).

- **D2-09: REB total = 2n GENERATED COLUMN `reb` (= reb_of + reb_def) STORED.** Mostra doble showcase de GENERATED COLUMN a migration. Queries READ-04/05/06 escriuen `reb` directe, no `reb_of + reb_def`. Defense: "GENERATED COLUMN no és només per a mètriques complexes (VAL) — també per a derivacions trivials que es repeteixen a queries."

### Standings + Leaderboards

- **D2-10: Standings tie-breaker simple FEB-style + ADR documentant gap normatiu FCBQ.** Query principal:
  ```sql
  RANK() OVER (
    PARTITION BY competition_id
    ORDER BY wins DESC, (points_for - points_against) DESC, points_for DESC
  )
  ```
  Defense: "pattern FEB estàndard, suficient per escala amateur. La normativa FCBQ exacta requereix head-to-head en empats de 2-3 equips; ADR-0004 documenta aquest gap i com upgrade-ho a v2 amb CTE." `wins`, `points_for`, `points_against` són **computats on-the-fly** a partir de `games` via subquery/CTE — no taula stored. Cap recompute hook (P3 territori). Implementació visible a `repositories/standings.py` amb comentari explicatiu (STAT-01 + SC1).

- **D2-11: Leaderboards window function on-the-fly, zero materialized table.** Query `/competitions/{id}/leaderboards?stat=val&limit=10`:
  ```sql
  RANK() OVER (
    PARTITION BY competition_id, season_id
    ORDER BY avg_stat DESC
  )
  ```
  on `avg_stat` es deriva de `AVG(<stat>) OVER (PARTITION BY player_id, season_id) FROM box_scores JOIN games WHERE competition_id = :id`. **NO** taula `player_season_averages` materialitzada a P2. Defense: "window functions on-the-fly són suficients a escala amateur (~500 jugadors per lliga, ~30 games per season → sub-100ms). Materialization a v2 quan emergeixi necessitat real." Composite index `(competition_id, season_id)` a `box_scores` accelera el PARTITION. Visible a `repositories/leaderboards.py` (STAT-02 + SC2).

- **D2-12: Leaderboards naturalment per-phase via competition_id.** Decisió D2-05 (Phase enum a Competition) implica que cada (category, gender, territory, group, season, phase) té el seu competition_id distint. `/competitions/{id}/leaderboards` retorna leaderboard per aquesta phase. Cap query cross-phase al MVP. Si recruiter pregunta "i sumar les 3 phases?" → endpoint addicional `/competitions/{id}/aggregate?across=phase` és easy follow-up; defer fins necessitat real.

### Pagination

- **D2-13: Pagination offset/limit simple a totes les list endpoints (READ-01, READ-03, READ-08).** Query params: `?offset=0&limit=20`. Defaults: `offset=0`, `limit=20`. Max: `limit=100` (validator Pydantic). Response: items array al body + header `X-Total-Count` amb total integer. Defense: "pattern estàndard, suficient a escala amateur. Cursor-based seria over-engineering — ~500 jugadors per lliga no necessita protecció contra inserts mid-pagination." Helper Pydantic `PaginationParams` reusable via Depends.

### Seed minimal

- **D2-14: Seed `data/seed/minimal.py` — 100% fictius realistes en català.** Equips fictius (e.g. `CB GRANOLLERS`, `CB ARTES`), 12 jugadors amb noms catalans fictius, dorsals 4-15, llicències inventades range 99001-99012 (fora del range federatiu real). 1 competition (e.g. `1a-territorial-m-bcn-grup-04`, season `2025-26`, phase `fase_previa`). 1 game amb box-score complet (24 box_scores totals: 12 home + 12 away). 1 Coach + 2 CoachingAssignment (1 per team). Privacy-safe (repo públic). Defense: "seed minimal demostratiu per a smoke-test endpoints; demo final amb dades reals via CLI FCBQ Phase 2.5 (basquethero pattern d'ús públic FCBQ)." Executable: `docker compose exec api python -m basketball_stats.seed.minimal` (INFRA-06 LOCKED). Idempotent: detecta seed existent + skip o re-seed sota flag `--force`.

### Repository + Service pattern

- **D2-15: Pure-read phase → repositories tenen tota la lògica SQL, services són thin pass-through.** Routers cridarien Services? **NO al P2** — routers criden Repositories directament via Depends, perquè zero validation logic més enllà del Pydantic input. Services emergiran a P3 amb AUTH writes (transactions + recompute + permission checks). Defense: "Repository pattern visible a P2; Service layer creix orgànicament a P3 quan apareix lògica transaccional. No over-engineer prematuely."

- **D2-16: Fitxers de codi per entitat — un repository per concepte de query, no per entitat ORM.** Convention:
  ```
  src/basketball_stats/repositories/
    standings.py        — Query window function RANK + tie-breakers (STAT-01)
    leaderboards.py     — Query window function AVG + RANK (STAT-02)
    games.py            — Query games per matchday + box-score full
    players.py          — Player profile + season stats + game log
    teams.py            — Team detail + roster + upcoming + last games
    competitions.py     — Competition list + filters
  ```
  Cada fitxer té docstring de mòdul amb "Showcases:" line referenciant SQL pattern. Defense per recruiter: "1 fitxer = 1 query pattern; window functions concentrades a `standings.py` i `leaderboards.py` per fer-les easy de trobar."

### Pydantic v2 + OpenAPI examples

- **D2-17: Schemas separats Create/Read/Update per entitat (OBS-08 + SC7).** Create/Update solament definits a P2 com a "drafts" — endpoints POST/PUT són P3 territory. Read schemas implementen `model_config = ConfigDict(json_schema_extra={"examples": [...]})` amb exemples realistes catalans (CB GRANOLLERS, dorsals 4-15, dates `2025-10-15` de season 2025-26). `/docs` Swagger UI ha de mostrar payload exemple a cada GET response. Verificació manual: `curl localhost:8000/openapi.json | jq '.paths."/competitions".get.responses."200".content."application/json".examples'` → no buit (TEST-02 cobrirà part d'això).

- **D2-18: ResponseModel a totes les rutes (no `dict`).** Cada endpoint declara `response_model=schemas.X` perquè OpenAPI generi schema. Cap `Any` ni `dict[str, Any]`. mypy --strict ajudarà a enforce-ho.

### Testing

- **D2-19: TEST-02 testcontainers integration tests cobreixen 100% les queries amb window functions.** Pyttests específics:
  - `test_standings_rank.py`: 2 teams, 2 games (1 victòria casa-fora), verificar RANK = 1 i 2.
  - `test_leaderboards_val.py`: 12 box_scores, verificar leaderboard top-3 ordenat per AVG(val) DESC.
  - `test_pagination_offset_limit.py`: 30 fixtures, verificar `offset=10&limit=5` retorna ítems 10-14 + `X-Total-Count: 30`.
  - `test_val_generated_column.py`: insert box_score amb pts=10, reb=5, etc., verificar VAL = PIR FIBA literal.
  - `test_competition_endpoint_filters.py`: filtres `?category=&gender=&territory=&season=`.
  Coverage target P2: 80%+ sobre repositories. Unit tests cobreixen Pydantic schemas + normalize_name() utility.

### Migration shape

- **D2-20: Una sola migration per a tot el schema P2 (`0002_core_entities.py`).** Una migration per phase, no per entitat. Defense: "phase boundary = migration boundary; cada release fa una migration cohesiva." Reversible via `downgrade()` que dropa totes les taules en ordre invers de FK. P1 D-08 (CI valida round-trip) cobrirà aquesta migration també. Composite indexes inclosos: `(competition_id, season_id, avg_stat DESC)` per leaderboards (un per stat?), `(game_date DESC, competition_id)` per games per jornada (STAT-05).

### Claude's Discretion

Roger ha delegat (igual que P1) el detail-level per "documenta que haces y porque para que yo luego pueda explicarlo". Decisions D2-15..D2-20 són Claude's discretion amb rationale defensable. Cap decisió oculta.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project-level (LOCKED, no re-debate)
- `.planning/PROJECT.md` — Stack lockat 2026-05-19 + Out of Scope explícit + Success Criteria del projecte.
- `.planning/REQUIREMENTS.md` §DOM (DOM-01..07) + §READ (READ-01..08) + §STAT (STAT-01, 02, 04, 05) + §INFRA (INFRA-06) + §OBS (OBS-01, OBS-08) + §TEST (TEST-02) — 23 REQ-IDs de P2.
- `.planning/ROADMAP.md` §"Phase 2: Core entities + public read" — Goal + 7 Success Criteria literals + dependency Phase 1.
- `.planning/STATE.md` §"Accumulated Context" — Decisions cumulades.
- `.planning/phases/01-foundation/01-CONTEXT.md` — 32 LOCKED decisions D-01..D-32 (especially D-01 src/ layout, D-02..D-05 architecture tree, D-13 uv + lockfile, D-14 pyproject.toml single source, D-19/D-20 structlog + request_id middleware).

### Research (HIGH confidence, frozen 2026-05-19)
- `.planning/research/SUMMARY.md` §2 (Domini insights basquethero), §3 (Arquitectura recomanada — Repository+Service, src/ layout).
- `.planning/research/STACK.md` — SQLAlchemy 2.0.49 async, Pydantic 2.13.4, asyncpg 0.31.0, testcontainers 4.14.2.
- `.planning/research/ARCHITECTURE.md` §1 (Project Layout), §2 (Repository+thin Service), §5 (Showcase Visibility Map — window functions, GENERATED COLUMN, composite indexes), §6 (Fly.io → adapt to Render del P1).
- `.planning/research/FEATURES.md` — **CRÍTIC per a P2**:
  - §1.2 (URL taxonomia basquethero, slug patterns).
  - §1.3 (lligues observades — 44 grups, categories, territoris, gèneres).
  - §1.4 (stats tracked Super Copa Masculina J28 — camps exactes box-score + VAL formula revelada).
  - §1.7 (Catalan quirks — competition jeràrquica, season entity, club ≠ team, phase system, jornada=matchday, PIR/Valoración mètrica, MVP, quintet ideal, acta oficial FCBQ).
- `.planning/research/PITFALLS.md` — P1.2 (lazy-load MissingGreenlet — `lazy="raise_on_sql"`), P2 (composite key vs surrogate — decidit per D2-01), P5.2 (testcontainers ryuk disabled — heretat de P1 D-16).

### External docs to verify durant planning/execute
- SQLAlchemy 2.0 async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html (async session patterns, `selectinload` + `joinedload` per evitar N+1, `lazy="raise_on_sql"`).
- SQLAlchemy `GENERATED ALWAYS AS`: https://docs.sqlalchemy.org/en/20/core/defaults.html#computed-columns — sintaxi exacta per Postgres STORED.
- Postgres GENERATED COLUMNS: https://www.postgresql.org/docs/16/ddl-generated-columns.html (STORED only, expressió ha de ser immutable, indexable).
- Postgres window functions: https://www.postgresql.org/docs/16/tutorial-window.html (RANK vs DENSE_RANK, PARTITION BY syntax).
- Alembic data migrations: https://alembic.sqlalchemy.org/en/latest/cookbook.html#conditional-migration-elements (per al seed inline si necessari, encara que seed serà script Python separat no Alembic).
- Pydantic v2 `model_config` examples: https://docs.pydantic.dev/2.13/concepts/json_schema/#field-level-customization (json_schema_extra examples).
- FastAPI Depends + `Annotated[X, Depends(...)]`: https://fastapi.tiangolo.com/tutorial/dependencies/ (PEP 593 pattern locked al P1 D-04).
- testcontainers PostgresContainer: https://testcontainers-python.readthedocs.io/en/latest/modules/postgres/ (fixture scope, env vars).

### ADRs a crear durant P2 (no esperar a P5)
- **ADR-0003: VAL formula PIR FIBA literal + asimetria Supercopa↔Territorial.** Documenta D2-07, D2-08 — per què defaults 0 i quan és exacte vs aproximat.
- **ADR-0004: Standings tie-breaker simple FEB-style.** Documenta D2-10 — per què no head-to-head al MVP + path d'upgrade a v2 amb CTE.

(Aquests 2 ADRs són **scope de P2**, no defer a P5. La resta de 4 ADRs creixen a P3+P5 segons P1 D-32.)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
Codi existent de P1 (commit master HEAD ~`540d9e9`):
- `src/basketball_stats/models/base.py` — Declarative Base buit (D-07 P1). **Aquí land les 9 entitats P2.**
- `src/basketball_stats/core/db.py` — Async engine + `AsyncSessionLocal` + `get_db()` dependency. **Reusat tal qual per P2.**
- `src/basketball_stats/core/config.py` — Pydantic Settings amb env_file + `to_asyncpg_url()` helper (fix sslmode bug P1). **Reusat tal qual.**
- `src/basketball_stats/api/errors.py` — Global exception handlers (D-04 P1). **Reusat; potser afegir handlers específics 404 NotFound, 422 ValidationError refinats si emergeix necessitat.**
- `src/basketball_stats/api/v1/deps.py` — Re-exporta `get_db`. **P2 afegirà `PaginationParams` Depends helper aquí.**
- `src/basketball_stats/api/v1/health.py` — `/healthz` endpoint (P1 D-09/D-10). **No tocar.**
- `tests/conftest.py` — testcontainers `postgres_container` fixture + `db_session` (P1 D-16). **Reusat per P2 integration tests; possible afegir `seed_minimal` fixture que carregui dades fictícies per a tests d'standings/leaderboards.**
- `migrations/versions/0001_baseline.py` — Buida `upgrade() pass / downgrade() pass` (P1 D-06). **P2 crea `0002_core_entities.py` damunt aquesta.** (Path verificat 2026-05-20; `alembic.ini` declara `script_location = %(here)s/migrations`.)

### Established Patterns (de P1, mandatory mantenir)
- `src/` layout — **Tots els nous models a `src/basketball_stats/models/` (1 fitxer per concepte de domini, no per entitat sola).**
- Pydantic v2 schemas amb `model_config` — Cada Create/Read/Update amb `json_schema_extra={"examples": [...]}`.
- Async engine + `await session.execute(...)` — Cap sync DB call dins async route (Pitfall P4 LOCKED).
- structlog JSON + request_id middleware — Cada nou repository/service log mitjançant `structlog.get_logger(__name__)`.
- ruff + mypy --strict — Cada nou fitxer ha de passar (CI gate).
- testcontainers per integration — Cap mock de DB (D-16 P1, TEST-02 reinforces).
- Exception handlers globals — Cap stack trace exposat al response (P1 D-04 + P1.6 pitfall).
- Migrations reversible — `downgrade()` implementat per a `0002_core_entities.py` (P1 D-08 round-trip CI).

### Integration Points
**Inbound:** Endpoints exposats a `https://basketball-stats-api-banq.onrender.com` via Render (live). README screenshot `/docs` placeholder de P1 omplert ara que hi ha endpoints reals.

**Outbound:**
- Neon Postgres `DATABASE_URL` (asyncpg) per al runtime — heretat de P1.
- Alembic `DATABASE_URL_DIRECT` (psycopg) per a migrations — heretat de P1.

</code_context>

<specifics>
## Specific Ideas

- **basquethero alignment as North Star, NOT 1:1 copy.** El scrape FEATURES.md és la font de domini-language oficial: VAL com a mètrica primària, URL slug patterns per a player IDs (`/players/<license>-<dorsal>-<slug>`), competition tuple hierarchy. La nostra API ha de ser **defensable per recruiter familiaritzat amb basquethero** ("aquest projecte modela el bàsquet català com els referents que existeixen, no inventa el seu món"). PERÒ amb diferenciadors clars: GENERATED COLUMNS visibles (basquethero amaga el càlcul), API pura amb OpenAPI (basquethero és frontend opaque), Postgres pur (basquethero usa MongoDB).

- **Defense-first comentaris als fitxers de repository.** Cada `repositories/<query>.py` ha de tenir docstring de mòdul amb pattern:
  ```python
  """Leaderboards repository.

  Showcase: PostgreSQL window function ``RANK() OVER (PARTITION BY ... ORDER BY ...)``
  visible al SQL d'aquesta query. Implementa STAT-02.

  Defense for interview: "window functions són la diferència vs un ORM-only solution
  que tornaria N+1 i un ranking calculat a Python. La query corre en sub-100ms a escala
  amateur perquè el composite index (competition_id, season_id) cobreix el PARTITION BY."
  """
  ```

- **Phase 2.5 boundary signal.** Si durant l'execució de P2 emergeix temptació de "podríem afegir un scrape script ràpid per omplir més dades" → BLOQUEAR i deferir explícitament a Phase 2.5. Phase 2 ship en temps amb seed minimal manual.

- **README screenshot del `/docs`.** Capturar pantalla del Swagger UI omplit amb endpoints + exemples realistes en català. Substituir el placeholder de P1 D-30 §1. Mostra abundància visual ("look how many endpoints I have") al recruiter al primer cop d'ull.

</specifics>

<deferred>
## Deferred Ideas

- **FCBQ Ingest CLI (Phase 2.5)** — scrape HTML FCBQ de 2a Catalana → Supercopa, M+F. Pattern utility offline batch (no live ingest, preservant LOCKED constraint PROJECT.md): Roger executa, genera JSON fixtures commitejats a `data/seed/fcbq/`. **Crear via `/gsd-insert-phase` post-P2-ship.** Apuntat a TODO.md raíz §Basketball Stats API [P2].

- **Web frontend UI** (basketball-stats-web repo separat o `/` landing custom) — millorar pàgina web del projecte amb Claude Design + Pretext HTML + Vercel free. Decidir abast (custom Swagger UI vs repo separat amb frontend real). Defense portfolio: API + frontend. Apuntat a TODO.md raíz §Basketball Stats API [P3].

- **Materialized table `player_season_averages`** — defer a v2 quan emergeixi necessitat real. Window functions on-the-fly suficients a escala amateur.

- **Cross-phase aggregate endpoint** — `/competitions/{id}/aggregate?across=phase` per sumar leaderboards de fase-previa + 2a-fase + playoff. Defer fins que emergeixi necessitat (potser Phase 5 polish demo).

- **Head-to-head tie-breaker amb CTE complex** — defer a v2. ADR-0004 documentarà el gap amb path d'upgrade.

- **Service layer per a reads** — defer a P3 quan emergeixin transactions + permission checks (AUTH writes). P2 routers criden Repositories directament.

- **Materialized view per a standings** — defer si emergeix problema de performance (no esperat).

- **JSONB play-by-play column** — defer a P4 o v2 (FEATURES.md DIFF-04, no obligatori MVP).

- **Streak detection (Racha ▲3/▼3)** — basquethero ho mostra. Pattern LAG window function + gaps-and-islands. Defer a P4 (DIFF-09) o v2.

- **/matchday/{date}/mvp** — MVP individual de la jornada. Defer a P4 (DIFF-02) o v2.

- **Player development trend (LAG)** — defer a v2 (DIFF-05).

</deferred>

---

*Phase: 2-core-entities*
*Context gathered: 2026-05-20*
