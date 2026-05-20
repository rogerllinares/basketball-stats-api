# Phase 2: Core entities + public read — Plan

**Planned:** 2026-05-20
**Phase scope:** 23 REQ-IDs (DOM-01..07, READ-01..08, STAT-01/02/04/05, INFRA-06, OBS-01/08, TEST-02)
**Success criteria:** 7 (literal from ROADMAP — must all be TRUE at `/gsd-verify-work`)
**Estimated atomic commits:** ~38 (1 per task + ~5 merge-related)
**Estimated waves:** 9 (Setup → 8 build waves)

> **Locked inputs (do NOT re-debate):** PROJECT.md stack, 32 D-XX decisions de P1, 20 D2-XX decisions de `02-CONTEXT.md`, 7 SC del ROADMAP, 23 REQ-IDs.
> **3 pre-resolved flags** (from Q1/Q2/Q3 del research):
> - **Q1:** D2-20 composite index `(comp, season, avg_stat DESC)` substituït per 3 real indexes: `ix_games_competition_id`, `ix_box_scores_player_lookup`, `ix_box_scores_val_desc` (sobre GENERATED column literal — showcase).
> - **Q2:** `normalize_name()` transliterates `ç → c` explicitly. Test cases listed below.
> - **Q3:** ADR-0003 + ADR-0004 són **scope de P2**, scheduled inline.
>
> **Migrations directory:** `migrations/versions/` (verificat 2026-05-20; NO `alembic/versions/`).

---

## Hard rules (apply to every task)

1. **GitHub Issues OBLIGATORI.** Cada task = 1 issue creat ABANS de tocar codi. Labels: `phase/2-core-entities` + tipus + prioritat. Milestone `Phase 2: Core entities + public read`. Branch `<type>/<issue-N>-<slug>`. Commits acaben en `(#N)`. PR amb `Closes #N`.
2. **Verification-first.** Cap task marcada feta sense córrer la comanda `<verify>` i veure-la verda. Si falla → `/investigate`, NO continuar.
3. **Atomic commits.** 1 task = 1 commit (o 1 PR amb commits cohesionats). Reversible.
4. **Defense docstrings.** Cada repository file inclou docstring amb "Showcase:" line + paragraf "Defense for interview:" copiat literal del research §2.
5. **mypy --strict + ruff** verds a cada task. CI gate del P1 inherited.
6. **Round-trip migration gate** (P1 D-08): `alembic upgrade head && alembic downgrade base && alembic upgrade head` verd per la nova migration.
7. **`lazy="raise_on_sql"`** a totes les `relationship(...)` (P1.2 pitfall, research §1).
8. **Copy verbatim** dels snippets de `02-RESEARCH.md` quan toca. NO paraphrase. NO re-research.
9. **Out-of-scope dur:** NO FCBQ scrape (P2.5), NO writes/auth (P3), NO tsvector/ideal-five (P4), NO defense doc (P5). Exception: ADR-0003 + ADR-0004 son P2.

---

## Wave 0 — Setup (sequential, blocking)

### Task 0.1 — Phase 2 milestone + labels

- **Issue:** `gh issue create --title "chore(p2): setup milestone + labels" --label chore,P1,phase/2-core-entities --milestone "Phase 2: Core entities + public read"` (crear milestone abans amb `gh api repos/:owner/:repo/milestones -f title='Phase 2: Core entities + public read' -f description='23 REQ-IDs (DOM/READ/STAT/INFRA/OBS/TEST)'`).
- **Action:**
  - Verify master CI verda: `gh run list --branch master --limit 1 --json conclusion -q '.[0].conclusion'` ha de retornar `success`.
  - Create milestone "Phase 2: Core entities + public read" si no existeix.
  - Create labels missing: `phase/2-core-entities`, `domain`, `endpoint`, `migration`, `adr`, `seed`, `test`. Reuse `bug`, `enhancement`, `chore`, `documentation`, `infra`, `P0/P1/P2/P3` from P1.
- **Verify:**
  - `gh label list | grep phase/2-core-entities` → exists.
  - `gh api repos/:owner/:repo/milestones | jq '.[] | select(.title=="Phase 2: Core entities + public read") | .number'` → returns number.
- **Done:** Milestone + labels exist. CI on master verda confirmed.
- **Commit:** No code change. Close issue with comment "labels + milestone ready".

### Task 0.2 — Create P2 branch

- **Issue:** Create umbrella issue `#N`: `feat(p2): Phase 2 — core entities + public read endpoints` listing all 23 REQ-IDs as task checklist.
- **Action:** `git checkout master && git pull --ff-only && git checkout -b feat/<issue-N>-phase-2-core-entities`.
- **Verify:** `git branch --show-current` → `feat/<N>-phase-2-core-entities`.
- **Done:** Branch created off latest master.

---

## Wave 1 — Database Migration `0002_core_entities.py` (SINGLE TASK, blocking)

### Task 1.1 — Alembic migration 0002 (manual, NOT autogenerate)

- **Issue:** `gh issue create --title "feat(p2): migration 0002 — 9 tables + 2 GENERATED columns + indexes" --label migration,infra,P1,phase/2-core-entities`.
- **Files:** `migrations/versions/0002_core_entities.py` (NEW).
- **Action:**
  - Write migration BY HAND (research §1 — autogenerate NO detects `Computed()`).
  - `down_revision = "0001_baseline"`, `revision = "0002_core_entities"`.
  - Create tables in FK order: `clubs` → `seasons` → `competitions` → `teams` → `players` → `coaches` → `rosters` → `coaching_assignments` → `games` → `box_scores`.
  - Apply schema literal from `02-CONTEXT.md` D2-06. Box-score columns + 2 GENERATED columns via `sa.Computed("...", persisted=True)` — copy verbatim from research §1.
  - Indexes (Q1 resolution):
    - `ix_games_competition_id ON games(competition_id)` — accelerates leaderboards JOIN.
    - `ix_box_scores_player_lookup ON box_scores(player_id)` — accelerates PARTITION BY player_id.
    - `ix_games_date_competition ON games(game_date DESC, competition_id)` — STAT-05 calendar.
    - `ix_box_scores_val_desc ON box_scores(val DESC)` — showcase index sobre GENERATED stored column.
  - UNIQUE constraints per D2-06: clubs.normalized_name, seasons.label, competitions composite tuple, teams (club_id, normalized_name), players (license_id, dorsal_default, normalized_name), coaches (license_id, normalized_name).
  - ENUM `phase` (`fase_previa`, `segona_fase`, `playoff`) — use `sa.Enum(..., name="competition_phase")` and `create_type=True`.
  - `downgrade()` drops indexes + tables in reverse FK order + drops the enum type.
- **Verify:**
  ```bash
  # 1. mypy + ruff
  uv run ruff check migrations/versions/0002_core_entities.py
  uv run mypy --strict migrations/versions/0002_core_entities.py
  # 2. Round-trip (D-08 P1 gate):
  uv run alembic upgrade head
  uv run alembic downgrade base
  uv run alembic upgrade head
  # 3. STORED confirmed via psql against the test container (CI step) or:
  uv run pytest tests/integration/test_migration_generated_columns.py -v  # crea aquest test al Wave 7
  # 4. grep "Computed(" migrations/versions/0002_core_entities.py → 2 matches (reb + val).
  ```
- **Done:** Migration applies+reverts+reapplies clean. 2 `Computed(...)` present. 4 indexes created. CI verda per la branca.
- **Commit:** `feat(migration): add 0002 core entities migration with VAL+REB GENERATED columns (#N)`.

---

## Wave 2 — SQLAlchemy Models (parallelizable, depends on 1.1)

> All tasks share same pattern: file under `src/basketball_stats/models/`, Mapped types, `lazy="raise_on_sql"` on all relationships, docstring with "Showcase:" if applicable, import in `models/__init__.py` for autoload by Alembic env.

### Task 2.1 — `Club` + `Season` models + `normalize_name` utility

- **Issue:** `gh issue create --title "feat(p2): Club + Season models + normalize_name util" --label domain,P1,phase/2-core-entities`. Covers DOM-01.
- **Files:**
  - `src/basketball_stats/core/text.py` (NEW)
  - `src/basketball_stats/models/club.py` (NEW)
  - `src/basketball_stats/models/season.py` (NEW)
  - `src/basketball_stats/models/__init__.py` (modify — re-exports for Alembic autoload)
  - `tests/unit/test_normalize_name.py` (NEW)
- **Action:**
  - `core/text.py`: copy `normalize_name()` from research §5 + **add ç/Ç → c/C transliteration** (Q2 resolved):
    ```python
    _TRANS = str.maketrans({"ç": "c", "Ç": "C"})
    def normalize_name(s: str) -> str:
        decomposed = unicodedata.normalize("NFD", s)
        stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
        return stripped.translate(_TRANS).upper().strip()
    ```
  - `models/club.py`: `Club(Base)` with `id INT PK`, `display_name str`, `normalized_name str unique`, `created_at`.
  - `models/season.py`: `Season(Base)` with `id INT PK`, `start_year INT`, `label str unique`.
  - `tests/unit/test_normalize_name.py`: parametrize cases from research §5 + corrected for Q2:
    - `("Rafael Pintó", "RAFAEL PINTO")`, `("Núñez", "NUNEZ")`, `("Albà", "ALBA")`
    - `("Barça", "BARCA")` ← Q2 transliteration
    - `("L'Hospitalet", "L'HOSPITALET")`, `("S. Joan", "S. JOAN")`
    - `("  CB Granollers  ", "CB GRANOLLERS")`, `("CB ARTÉS", "CB ARTES")`
    - `("", "")`, `("a", "A")`, `("España", "ESPANA")`
- **Verify:**
  ```bash
  uv run ruff check src/basketball_stats/{core/text.py,models/club.py,models/season.py} tests/unit/test_normalize_name.py
  uv run mypy --strict src/basketball_stats/{core/text.py,models/club.py,models/season.py}
  uv run pytest tests/unit/test_normalize_name.py -v
  ```
- **Done:** All asserts pass including `Barça → BARCA`. mypy + ruff clean.
- **Commit:** `feat(domain): add Club+Season models and normalize_name utility (#N)`.

### Task 2.2 — `Competition` model + `Phase` enum

- **Issue:** `feat(p2): Competition model + Phase enum`. Covers DOM-04.
- **Files:** `src/basketball_stats/models/competition.py`, update `models/__init__.py`.
- **Action:**
  - `Phase = Literal["fase_previa", "segona_fase", "playoff"]` (Python type).
  - `Competition(Base)`: PK id; `category str`, `gender str (Literal["m","f"])`, `territory str`, `group_no int`, `season_id FK seasons.id`, `phase` (SQLAlchemy `Enum(..., name="competition_phase")` matching migration).
  - UNIQUE constraint on composite tuple `(category, gender, territory, group_no, season_id, phase)` via `__table_args__ = (UniqueConstraint(...),)`.
  - `relationship("Season", lazy="raise_on_sql")` + back_populates if Season holds collection.
- **Verify:** ruff + mypy --strict + `python -c "from basketball_stats.models.competition import Competition; print(Competition.__table__)"`.
- **Done:** Model importable, mypy clean, matches migration columns 1:1.
- **Commit:** `feat(domain): add Competition model with Phase enum (#N)`.

### Task 2.3 — `Team` model + `Roster` association

- **Issue:** `feat(p2): Team + Roster models`. Covers DOM-02 + D2-03.
- **Files:** `src/basketball_stats/models/team.py`, `src/basketball_stats/models/roster.py`.
- **Action:**
  - `Team(Base)`: PK id, `club_id FK clubs.id`, `display_name`, `normalized_name`. UNIQUE `(club_id, normalized_name)`.
  - `Roster(Base)`: composite PK `(player_id, team_id, season_id)`, `dorsal_at_season INT`, `joined_at`, `left_at NULL`.
  - All relationships `lazy="raise_on_sql"`.
- **Verify:** ruff + mypy --strict + import test.
- **Done:** Two models load, FK targets resolvable post-import.
- **Commit:** `feat(domain): add Team and Roster association models (#N)`.

### Task 2.4 — `Player` model

- **Issue:** `feat(p2): Player model with composite uniqueness`. Covers DOM-03 + D2-01.
- **Files:** `src/basketball_stats/models/player.py`.
- **Action:**
  - `Player(Base)`: PK id, `license_id INT`, `dorsal_default INT`, `display_name str`, `normalized_name str`. UNIQUE `(license_id, dorsal_default, normalized_name)`.
  - `relationship("BoxScore", lazy="raise_on_sql", back_populates="player")`.
  - Docstring includes D2-01 defense paragraph (URL slug pattern, surrogate vs composite).
- **Verify:** ruff + mypy --strict + import test.
- **Done:** Model loads, defense docstring present.
- **Commit:** `feat(domain): add Player model with hybrid surrogate+composite identity (#N)`.

### Task 2.5 — `Coach` + `CoachingAssignment` models

- **Issue:** `feat(p2): Coach + CoachingAssignment models`. Covers DOM-07.
- **Files:** `src/basketball_stats/models/coach.py`, `src/basketball_stats/models/coaching_assignment.py`.
- **Action:**
  - `Coach(Base)`: PK id, `license_id INT NULL`, `display_name`, `normalized_name`. UNIQUE `(license_id, normalized_name)`.
  - `CoachingAssignment(Base)`: composite PK `(coach_id, team_id, season_id)`, `role str`, `started_at`, `ended_at NULL`.
- **Verify:** ruff + mypy --strict.
- **Done:** Both models load.
- **Commit:** `feat(domain): add Coach + CoachingAssignment models (#N)`.

### Task 2.6 — `Game` model

- **Issue:** `feat(p2): Game model with Q1-Q4 markers`. Covers DOM-05.
- **Files:** `src/basketball_stats/models/game.py`.
- **Action:**
  - `Game(Base)`: PK id, `competition_id FK`, `matchday_no INT`, `game_date Date`, `home_team_id FK teams.id`, `away_team_id FK teams.id`, columns Q1-Q4 (`q1_home, q1_away, q2_home, q2_away, q3_home, q3_away, q4_home, q4_away` all INT), `total_home INT`, `total_away INT`.
  - Relationships to Competition + Team(s) `lazy="raise_on_sql"`. `box_scores` collection `lazy="raise_on_sql"`.
- **Verify:** ruff + mypy --strict + import test.
- **Done:** Model loads, FK targets resolve.
- **Commit:** `feat(domain): add Game model with quarter markers (#N)`.

### Task 2.7 — `BoxScore` model with 2 GENERATED columns

- **Issue:** `feat(p2): BoxScore model with VAL+REB GENERATED columns`. Covers DOM-06 + STAT-04.
- **Files:** `src/basketball_stats/models/box_score.py`.
- **Action:**
  - Copy verbatim from research §1 BoxScore class. **Critical:** `persisted=True` on both `Computed(...)`, val expression uses `(reb_of + reb_def)` NOT `reb` (Postgres forbids generated→generated reference).
  - Default `NOT NULL DEFAULT 0` on `fouls_drawn` + `blocks_received` (D2-07 PIR works without COALESCE).
  - All relationships `lazy="raise_on_sql"`.
  - Module docstring: "Showcase: 2 Postgres GENERATED COLUMNS STORED (REB total + VAL/PIR FIBA literal). See migration 0002 for SQL."
- **Verify:**
  - ruff + mypy --strict.
  - `python -c "from basketball_stats.models.box_score import BoxScore; assert 'val' in BoxScore.__table__.c"`.
  - **Round-trip Alembic** (re-verify migration matches model post-additions): `alembic upgrade head && alembic downgrade base && alembic upgrade head`.
- **Done:** Model loads, val + reb are Mapped[int], DDL emitted by SQLAlchemy matches migration.
- **Commit:** `feat(domain): add BoxScore model with VAL+REB GENERATED columns (#N)`.

---

## Wave 2.5 — ADR-0003 (right after BoxScore + migration ship)

### Task 2.5.1 — Write ADR-0003 VAL formula

- **Issue:** `docs(adr): ADR-0003 VAL formula PIR FIBA + Supercopa/Territorial asymmetry`. Label `documentation, adr`.
- **Files:** `docs/adr/0003-val-pir-fiba-formula.md`.
- **Action:** Follow P1 D-32 ADR numbering. Document:
  - **D2-07:** VAL = PIR FIBA literal STORED via GENERATED COLUMN.
  - **D2-08:** Asimetria Supercopa (registra fouls_drawn + blocks_received) vs Territorial (no els registra → defaults 0 → PIR aproximat baix-defensiu).
  - **Decision:** schema uniform amb defaults 0; pots subestimar jugadors defensius en Territorial. Honest limitation documentat aquí.
  - **Q2 ç-normalization footnote:** brief reference that name normalization transliterates `ç → c` for FCBQ matching robustness.
  - References: `models/box_score.py`, `migrations/versions/0002_core_entities.py`, postgres docs link.
- **Verify:**
  - File exists at exact path.
  - `head -5 docs/adr/0003-val-pir-fiba-formula.md` shows ADR-pattern frontmatter.
  - Linked from README "ADR index" if section exists; else create a small index in `docs/adr/README.md`.
- **Done:** ADR file committed, indexed.
- **Commit:** `docs(adr): add ADR-0003 VAL formula PIR FIBA + asymmetry note (#N)`.

---

## Wave 3 — Pydantic Schemas (parallelizable, depends on Wave 2)

> All schemas under `src/basketball_stats/schemas/`. Each Read schema declares `model_config = ConfigDict(from_attributes=True, json_schema_extra={"examples": [<2 Catalan realistic examples>]})` per D2-17 + OBS-08. Create/Update drafts only (POST/PUT comes in P3). `PaginationParams` added to `api/v1/deps.py` (D2-13).

### Task 3.1 — `PaginationParams` + `schemas/__init__.py` + Competition schema

- **Issue:** `feat(p2): pagination helper + Competition schemas`. Covers part of READ-01, OBS-08.
- **Files:**
  - `src/basketball_stats/api/v1/deps.py` (modify — add PaginationParams + PaginationDep)
  - `src/basketball_stats/schemas/__init__.py` (NEW)
  - `src/basketball_stats/schemas/competition.py` (NEW)
- **Action:**
  - **deps.py:** copy verbatim `PaginationParams` + `PaginationDep` from research §3 (Annotated[..., Field(ge=0/ge=1/le=100)], extra="forbid").
  - **schemas/competition.py:** copy verbatim CompetitionRead + CompetitionCreate from research §3. 2 examples in Catalan (1a-territorial-m-bcn-grup-4 + super-copa-m-cat-playoff).
- **Verify:** ruff + mypy --strict + `python -c "from basketball_stats.api.v1.deps import PaginationParams; PaginationParams(offset=0, limit=20)"`.
- **Done:** Helpers + Competition schemas importable.
- **Commit:** `feat(api): pagination helper and Competition schemas with Catalan examples (#N)`.

### Task 3.2 — `Team` + `Player` + `Coach` schemas

- **Issue:** `feat(p2): Team + Player + Coach schemas`. Covers OBS-08.
- **Files:**
  - `src/basketball_stats/schemas/team.py` (NEW)
  - `src/basketball_stats/schemas/player.py` (NEW)
  - `src/basketball_stats/schemas/coach.py` (NEW)
- **Action:**
  - `TeamRead`: id, club_id, display_name, normalized_name; `from_attributes=True`; examples `[{display_name: "CB Granollers", ...}, {display_name: "CB Artés", ...}]`.
  - `TeamDetailRead`: extends Team — embeds `roster_current: list[PlayerRead]` + `recent_games: list[GameSummaryRead]` + `upcoming_games: list[GameSummaryRead]`. Example: full payload with 12-player roster + 2 recent + 2 upcoming games. (Used by READ-04 router Task 5.2; defined here in Wave 3 to preserve wave boundary.)
  - `PlayerRead`: id, license_id, dorsal_default, display_name, normalized_name; examples `[{display_name: "Rafael Pintó", dorsal: 5}, ...]`.
  - `PlayerStatsRead`: aggregated season stats (totals + per-game avg) for READ-06 — fields: games_played, pts_total, pts_avg, reb_total, reb_avg, ast_avg, val_avg.
  - `CoachRead`: id, license_id, display_name, normalized_name; example with Catalan coach name.
  - `TeamCreate` / `PlayerCreate` / `CoachCreate` drafts (NOT exposed via POST in P2 — schema exists for /docs).
- **Verify:** ruff + mypy --strict; `pytest tests/unit/test_pydantic_examples_render.py` (skel: import each schema, assert `model_json_schema()["examples"]` non-empty).
- **Done:** All schemas importable, examples present.
- **Commit:** `feat(api): Team+Player+Coach Pydantic schemas with Catalan examples (#N)`.

### Task 3.3 — `Game` + `BoxScore` + `Standings` + `Leaderboards` schemas

- **Issue:** `feat(p2): Game/BoxScore + window-function read schemas`. Covers OBS-08 + STAT-01/02.
- **Files:**
  - `src/basketball_stats/schemas/game.py` (NEW)
  - `src/basketball_stats/schemas/standings.py` (NEW)
  - `src/basketball_stats/schemas/leaderboards.py` (NEW)
- **Action:**
  - `BoxScoreRead`: game_id, player_id, team_id, min, pts, plus_minus, fg2m/fg2a/fg3m/fg3a/ftm/fta, reb_of/reb_def/reb (computed), ast, rec, tap, per, fc, fouls_drawn, blocks_received, val (computed). Example: `{player_id: 1, pts: 10, reb: 5, val: 17, ...}` (matching research §4 expected val).
  - `GameRead`: id, competition_id, matchday_no, game_date, home_team_id, away_team_id, q1_home/q1_away..q4_home/q4_away, total_home, total_away, `box_scores: list[BoxScoreRead]`. Example with 2025-10-15 + CB Granollers vs CB Artés.
  - `StandingsRow`: team_id, display_name, played, wins, losses, points_for, points_against, point_diff, position.
  - `LeaderboardRow`: player_id, display_name, games_played, avg_stat, position. + `LeaderboardStat = Literal["val", "pts", "reb", "ast", "rec", "tap", "plus_minus"]` (matching ALLOWED_STATS).
- **Verify:** ruff + mypy --strict + import each + examples non-empty.
- **Done:** All schemas present with realistic Catalan examples.
- **Commit:** `feat(api): Game/BoxScore/Standings/Leaderboards schemas (#N)`.

---

## Wave 4 — Repositories (parallelizable, depends on Waves 2+3)

> Per D2-15: routers call repos directly (no service layer). Per D2-16: 1 file per query concept. **Every file has module docstring with "Showcase:" line + "Defense for interview:" paragraph** (copy from research §2 verbatim).

### Task 4.1 — `repositories/competitions.py`

- **Issue:** `feat(p2): competitions repository`. Covers READ-01 backend.
- **Files:** `src/basketball_stats/repositories/__init__.py` (NEW empty marker), `src/basketball_stats/repositories/competitions.py` (NEW).
- **Action:**
  - Module docstring: showcase line + defense paragraph (filterable list pattern).
  - Async functions: `list_competitions(session, filters, offset, limit) -> tuple[list[Competition], int]` (returns rows + total count). Filters: category, gender, territory, season_id. `get_competition(session, id) -> Competition | None`.
  - Use SQLAlchemy 2.0 `select(Competition).where(...)` + `func.count()` for total (research §6 pattern).
- **Verify:** ruff + mypy --strict + `pytest tests/integration/test_competitions_repo.py -v` (test skeleton in Wave 7).
- **Done:** Repo importable, returns proper types.
- **Commit:** `feat(repo): add competitions repository (#N)`.

### Task 4.2 — `repositories/teams.py`

- **Issue:** `feat(p2): teams repository`. Covers READ-04 backend.
- **Files:** `src/basketball_stats/repositories/teams.py` (NEW).
- **Action:**
  - `get_team(session, id) -> Team | None`.
  - `get_team_roster(session, team_id, season_id) -> list[tuple[Player, int]]` (player + dorsal_at_season, via Roster JOIN). Use `selectinload(...)` to avoid N+1 (P1.2).
  - `get_team_recent_games(session, team_id, limit=5) -> list[Game]` ordered by game_date DESC.
  - `get_team_upcoming_games(...)` — empty list at P2 (no future-dated games in seed); function exists for API contract.
  - Module docstring + defense.
- **Verify:** ruff + mypy --strict + integration test stub.
- **Done:** Repo importable.
- **Commit:** `feat(repo): add teams repository with roster + recent games (#N)`.

### Task 4.3 — `repositories/players.py`

- **Issue:** `feat(p2): players repository + slug URL pattern`. Covers READ-05 + READ-06.
- **Files:** `src/basketball_stats/repositories/players.py` (NEW).
- **Action:**
  - `get_player_by_slug(session, license_id, dorsal, slug) -> Player | None` — matches `(license_id, dorsal_default, normalize_name(slug))` per D2-01 URL pattern.
  - `get_player(session, id) -> Player | None`.
  - `get_player_season_stats(session, player_id, season_id) -> PlayerStatsRead` — aggregated via SQL: `SELECT AVG(val), AVG(pts), AVG(reb), AVG(ast), COUNT(*) FROM box_scores JOIN games WHERE player_id=:p AND season_id=:s`.
  - `get_player_game_log(session, player_id, limit=10) -> list[BoxScore]` ordered by game_date DESC via JOIN games.
  - Module docstring + defense.
- **Verify:** ruff + mypy --strict.
- **Done:** Repo importable, slug pattern matches.
- **Commit:** `feat(repo): add players repository with slug lookup + season stats (#N)`.

### Task 4.4 — `repositories/games.py`

- **Issue:** `feat(p2): games repository with box-score detail`. Covers READ-07 + READ-08.
- **Files:** `src/basketball_stats/repositories/games.py` (NEW).
- **Action:**
  - `get_game_with_box_scores(session, game_id) -> Game | None` — uses `selectinload(Game.box_scores).selectinload(BoxScore.player)` to materialize full payload, no lazy-load.
  - `list_competition_games(session, competition_id, matchday_no=None, offset, limit) -> tuple[list[Game], int]` filtered by competition + optional matchday.
  - Module docstring: "Showcase: composite index `ix_games_date_competition` accelerates calendar queries (STAT-05)."
- **Verify:** ruff + mypy --strict.
- **Done:** Repo importable, eager-loads box_scores without N+1.
- **Commit:** `feat(repo): add games repository with eager box-score loading (#N)`.

### Task 4.5 — `repositories/standings.py` (STAT-01 + SC1)

- **Issue:** `feat(p2): standings repository with RANK() window function`. Covers STAT-01 + READ-02.
- **Files:** `src/basketball_stats/repositories/standings.py` (NEW).
- **Action:** **Copy verbatim from research §2** the entire `STANDINGS_SQL` text() block + `fetch_standings()` async function + module docstring (showcase + defense paragraph). RANK() with tie-breakers `(wins DESC, point_diff DESC, points_for DESC)` per D2-10.
- **Verify:**
  - ruff + mypy --strict.
  - `grep -c "RANK() OVER" src/basketball_stats/repositories/standings.py` ≥ 1.
  - Skeleton integration test (Wave 7) returns 2 rows for seed.
- **Done:** Standings repo with literal RANK() SQL visible.
- **Commit:** `feat(repo): add standings repository with RANK window function (#N)`.

### Task 4.6 — `repositories/leaderboards.py` (STAT-02 + SC2)

- **Issue:** `feat(p2): leaderboards repository with nested window functions`. Covers STAT-02 + READ-03.
- **Files:** `src/basketball_stats/repositories/leaderboards.py` (NEW).
- **Action:** **Copy verbatim from research §2** `LEADERBOARDS_SQL_TEMPLATE` + `ALLOWED_STATS` + `fetch_leaderboard()`. Module docstring with showcase paragraph (AVG + RANK nested, composite index `(competition_id)` rationale).
- **Verify:**
  - ruff + mypy --strict.
  - `grep -c "RANK() OVER" src/basketball_stats/repositories/leaderboards.py` ≥ 1.
  - `grep -c "ALLOWED_STATS" src/basketball_stats/repositories/leaderboards.py` ≥ 1 (allowlist for SQL injection safety).
- **Done:** Leaderboards repo with literal nested window function SQL visible.
- **Commit:** `feat(repo): add leaderboards repository with AVG+RANK window functions (#N)`.

---

## Wave 5 — Routers (parallelizable, depends on Waves 3+4)

> All under `src/basketball_stats/api/v1/`. Each router uses `response_model=...` (D2-18, no `dict[str, Any]`). Paginated routes inject `X-Total-Count` via `response: Response` parameter (research §6 — NOT via constructor headers). 404 via `HTTPException(status.HTTP_404_NOT_FOUND, detail=...)`.

### Task 5.1 — `api/v1/competitions.py` (READ-01 + READ-02 + READ-03 + READ-08)

- **Issue:** `feat(p2): competitions endpoints (list + detail + standings + leaderboards + games)`.
- **Files:** `src/basketball_stats/api/v1/competitions.py` (NEW).
- **Action:**
  - `GET /competitions` — list with filters (category, gender, territory, season_id) + PaginationDep + X-Total-Count. Copy verbatim router template from research §6 + extend filters.
  - `GET /competitions/{id}` — get_competition, 404 if None.
  - `GET /competitions/{id}/standings` — calls `fetch_standings()`, `response_model=list[StandingsRow]`.
  - `GET /competitions/{id}/leaderboards?stat=val&limit=10&offset=0` — calls `fetch_leaderboard()` with stat validated by `LeaderboardStat` Literal, `response_model=list[LeaderboardRow]`. If stat not in `ALLOWED_STATS`, raise 422 (Pydantic Literal enforces).
  - `GET /competitions/{id}/games?matchday=5` — calls `list_competition_games()`, paginated, X-Total-Count.
- **Verify:**
  - ruff + mypy --strict.
  - `python -c "from basketball_stats.api.v1.competitions import router; print(router.routes)"` → 5 routes.
- **Done:** Router file with 5 endpoints, all response_model declared.
- **Commit:** `feat(api): competitions router with standings + leaderboards endpoints (#N)`.

### Task 5.2 — `api/v1/teams.py` (READ-04)

- **Issue:** `feat(p2): teams endpoint`.
- **Files:** `src/basketball_stats/api/v1/teams.py` (NEW).
- **Action:** `GET /teams` (list + pagination + X-Total-Count, `response_model=list[TeamRead]`) + `GET /teams/{id}` (detail = team + roster current season + recent games + upcoming games, `response_model=TeamDetailRead` — schema defined in Wave 3 Task 3.2). 404 on missing.
- **Verify:** ruff + mypy --strict.
- **Done:** 2 routes, response_model declared.
- **Commit:** `feat(api): teams router with detail + roster (#N)`.

### Task 5.3 — `api/v1/players.py` (READ-05 + READ-06)

- **Issue:** `feat(p2): players endpoint + slug URL pattern`.
- **Files:** `src/basketball_stats/api/v1/players.py` (NEW).
- **Action:**
  - `GET /players/{license_dorsal_slug}` (path like `/players/80121-5-rafael-pinto`) — parse with regex `r"^(\d+)-(\d+)-([a-z0-9-]+)$"`, call `get_player_by_slug()`. 404 on miss or pattern mismatch.
  - `GET /players/{id}` — int fallback for internal/admin use; `response_model=PlayerRead`.
  - `GET /players/{id}/stats?season_id=1` — calls `get_player_season_stats()`, `response_model=PlayerStatsRead`. 404 if no rows.
  - `GET /players/{id}/games?limit=10` — game log via `get_player_game_log()`.
- **Verify:** ruff + mypy --strict + route enumeration.
- **Done:** All 4 routes, slug parser works.
- **Commit:** `feat(api): players router with slug URL pattern + season stats (#N)`.

### Task 5.4 — `api/v1/games.py` (READ-07)

- **Issue:** `feat(p2): game detail endpoint with box-score`.
- **Files:** `src/basketball_stats/api/v1/games.py` (NEW).
- **Action:** `GET /games/{id}` returns `GameRead` with embedded `box_scores: list[BoxScoreRead]` for BOTH teams (12+12). Calls `get_game_with_box_scores()` (selectinload pattern — no lazy-load). 404 on miss.
- **Verify:** ruff + mypy --strict.
- **Done:** 1 route, eager-loads BoxScore.player without lazy-load explosion.
- **Commit:** `feat(api): game detail endpoint with full box-score (#N)`.

### Task 5.5 — Register all routers in `main.py` + `api/v1/__init__.py`

- **Issue:** `feat(p2): wire v1 routers into FastAPI app`.
- **Files:**
  - `src/basketball_stats/api/v1/__init__.py` (NEW or modify — `api_router` aggregator with prefix `/api/v1`).
  - `src/basketball_stats/main.py` (modify — `app.include_router(api_router)`).
- **Action:** Copy verbatim router-aggregator pattern from research §6. Tags: `competitions`, `teams`, `players`, `games`. Health stays separate (no `/api/v1` prefix per P1).
- **Verify:**
  - ruff + mypy --strict.
  - `uv run python -m basketball_stats.main --check` or import `app` + count routes (expect ≥9: 1 health + 8 P2 GETs).
  - Run app: `uv run uvicorn basketball_stats.main:app --port 8001 &` + `curl localhost:8001/openapi.json | jq '.paths | keys | length'` ≥ 9.
- **Done:** All routers visible at /openapi.json.
- **Commit:** `feat(api): wire v1 router aggregator into main (#N)`.

---

## Wave 5.5 — ADR-0004 (after standings router lands)

### Task 5.5.1 — Write ADR-0004 standings tie-breaker

- **Issue:** `docs(adr): ADR-0004 standings tie-breaker (FEB-simple + v2 upgrade path)`.
- **Files:** `docs/adr/0004-standings-tie-breaker.md`.
- **Action:** Document D2-10:
  - **Decision:** RANK() OVER (PARTITION BY competition_id ORDER BY wins DESC, point_diff DESC, points_for DESC) — FEB-standard.
  - **Gap:** FCBQ normativa requires head-to-head in 2-3-way ties. NOT implemented at MVP.
  - **Upgrade path v2:** CTE that computes head-to-head record per tied pair, then composite ORDER BY (wins, h2h_wins, h2h_diff, point_diff, points_for). Pseudo-SQL sketch included.
  - References: `repositories/standings.py`, FEB rules link.
- **Verify:** File exists, indexed in `docs/adr/README.md`.
- **Done:** ADR file committed.
- **Commit:** `docs(adr): add ADR-0004 standings tie-breaker (#N)`.

---

## Wave 6 — Seed Minimal (INFRA-06 + SC6)

### Task 6.1 — `seed/minimal.py` — 1 competition + 2 teams + 1 game + 12 box-scores

- **Issue:** `feat(p2): minimal seed script — fictitious Catalan data`.
- **Files:**
  - `src/basketball_stats/seed/__init__.py` (NEW empty marker).
  - `src/basketball_stats/seed/minimal.py` (NEW).
  - `data/seed/minimal.py` is the **canonical executable path** per ROADMAP §SC6 / INFRA-06. Decision: implement under `src/basketball_stats/seed/minimal.py` and expose `data/seed/minimal.py` as a thin pointer (1-line `from basketball_stats.seed.minimal import main; main()` if-name-main wrapper) OR alias via `python -m basketball_stats.seed.minimal`. **Use the `python -m` form** (research §8 SC6 verification confirms).
- **Action:**
  - Async `seed(session, *, force=False) -> dict[str, int]` returns counts.
  - Data per D2-14: 100% Catalan fictitious. Examples:
    - 1 Season: id=1, start_year=2025, label="2025-26".
    - 1 Competition: id=1, category="1a-territorial", gender="m", territory="bcn", group_no=4, season_id=1, phase="fase_previa".
    - 1 Club CB Granollers + 1 Club CB Artés.
    - 2 Teams (1 per club).
    - 12 Players with license_ids 99001-99012 (D2-14 fora del range federatiu), dorsals 4-15, Catalan-fictitious names. **Fixed mapping (anchor for slug tests like Task 7.6):**

      | license_id | dorsal_default | display_name    | normalized_name | slug              |
      |-----------:|---------------:|-----------------|-----------------|-------------------|
      | 99001      | 5              | Marc Soler      | MARC SOLER      | `marc-soler`      |
      | 99002      | 6              | Jordi Vila      | JORDI VILA      | `jordi-vila`      |
      | 99003      | 7              | Pol Camps       | POL CAMPS       | `pol-camps`       |
      | 99004      | 8              | Aleix Mas       | ALEIX MAS       | `aleix-mas`       |
      | 99005      | 9              | Nil Roca        | NIL ROCA        | `nil-roca`        |
      | 99006      | 10             | Roger Pujol     | ROGER PUJOL     | `roger-pujol`     |
      | 99007      | 11             | Bernat Llop     | BERNAT LLOP     | `bernat-llop`     |
      | 99008      | 12             | Arnau Vidal     | ARNAU VIDAL     | `arnau-vidal`     |
      | 99009      | 13             | Iu Roig         | IU ROIG         | `iu-roig`         |
      | 99010      | 14             | Gerard Pou      | GERARD POU      | `gerard-pou`      |
      | 99011      | 15             | Adrià Solà      | ADRIA SOLA      | `adria-sola`      |
      | 99012      | 4              | Quim Bosch      | QUIM BOSCH      | `quim-bosch`      |

      Test 7.6 asserts URL `/api/v1/players/99001-5-marc-soler` resolves to the row license_id=99001. Tests may assert this row's structure but should NOT depend on other names.
    - 1 Game (matchday=1, date=2025-10-15, home=Granollers, away=Artés, totals 80-84 home win/loss for standings sanity).
    - 12 BoxScores (12 home players for the home team; visitors' 12 box-scores via second iteration → total 24). Use varied PTS/REB to make leaderboard ordering nontrivial.
    - 1 Coach + 2 CoachingAssignment.
  - Idempotent: detect via `select(func.count()).select_from(Season).where(Season.id == 1)`; skip if seed exists, unless `--force` (truncates all P2 tables in reverse FK order first).
  - CLI entrypoint: `if __name__ == "__main__"`: parse `--force` arg, run `asyncio.run(seed(...))`.
- **Verify:**
  ```bash
  # Local against testcontainer or docker-compose:
  uv run alembic upgrade head
  uv run python -m basketball_stats.seed.minimal
  # Expected stdout: "seeded: 1 competition, 2 teams, 12 players, 1 game, 24 box_scores, 1 coach, 2 coaching_assignments"
  # Re-run idempotent:
  uv run python -m basketball_stats.seed.minimal
  # Expected: "already seeded; pass --force to re-seed".
  # Force re-seed:
  uv run python -m basketball_stats.seed.minimal --force
  ```
- **Done:** Seed runs, idempotent, --force works.
- **Commit:** `feat(seed): minimal seed with Catalan fictitious data + idempotency (#N)`.

---

## Wave 7 — Integration Tests (depends on Waves 1-6)

> Tests interleave per layer. Coverage target ≥80% on `repositories/`. Use existing `db_session` + new `seed_minimal` fixture (research §4). All tests use real Postgres via testcontainers (P1 D-16 inherited).

### Task 7.1 — `seed_minimal` fixture + `tests/conftest.py` patch + smoke test

- **Issue:** `test(p2): add seed_minimal fixture to integration conftest`.
- **Files:** `tests/integration/conftest.py` (modify — append fixture from research §4).
- **Action:** Append `seed_minimal` session-scoped fixture from research §4 verbatim. Smoke test `tests/integration/test_seed_minimal_loads.py`: requests `seed_minimal` + asserts counts via SQL.
- **Verify:** `uv run pytest tests/integration/test_seed_minimal_loads.py -v` green.
- **Done:** Fixture importable, smoke test green.
- **Commit:** `test(infra): add seed_minimal fixture for window-function tests (#N)`.

### Task 7.2 — `test_val_generated_column.py` (SC3)

- **Issue:** `test(p2): VAL+REB GENERATED column assertion`. Covers STAT-04 + SC3.
- **Files:** `tests/integration/test_val_generated_column.py` (NEW).
- **Action:** Copy verbatim from research §4. INSERT raw stats → SELECT reb,val → assert reb=5, val=17. Test does NOT use seed_minimal (clean state — uses inline INSERTs).
- **Verify:** `uv run pytest tests/integration/test_val_generated_column.py -v` green.
- **Done:** Test passes; val=17, reb=5 confirmed.
- **Commit:** `test(domain): VAL GENERATED column matches PIR FIBA literal (#N)`.

### Task 7.3 — `test_standings_rank.py` (SC1)

- **Issue:** `test(p2): standings RANK window function`. Covers STAT-01 + SC1.
- **Files:** `tests/integration/test_standings_rank.py` (NEW).
- **Action:** Copy from research §4 skeleton. With `seed_minimal` (2 teams, 1 game, home loses 80-84 → away rank=1, home rank=2). Assert `len(standings)==2`, `standings[0]["position"]==1`, `standings[1]["position"]==2`, `standings[0]["wins"] >= standings[1]["wins"]`.
- **Verify:** `uv run pytest tests/integration/test_standings_rank.py -v` green.
- **Done:** Test passes.
- **Commit:** `test(repo): standings RANK with tie-breakers (#N)`.

### Task 7.4 — `test_leaderboards_val.py` (SC2)

- **Issue:** `test(p2): leaderboards window function ordering`. Covers STAT-02 + SC2.
- **Files:** `tests/integration/test_leaderboards_val.py` (NEW).
- **Action:** With `seed_minimal` (24 box-scores), call `fetch_leaderboard(competition_id=1, stat="val", limit=10)`. Assert `len(rows) <= 10`, `rows[0]["position"]==1`, `rows[0]["avg_stat"] >= rows[1]["avg_stat"]`. Run also with stat="pts" — verify ordering different (or stable). Run with stat="invalid" → assert raises ValueError.
- **Verify:** `uv run pytest tests/integration/test_leaderboards_val.py -v` green.
- **Done:** Window function ordering proven.
- **Commit:** `test(repo): leaderboards AVG+RANK ordering (#N)`.

### Task 7.5 — `test_pagination_offset_limit.py` + `test_competition_endpoint_filters.py`

- **Issue:** `test(p2): pagination + competition filter endpoints (HTTP layer)`.
- **Files:**
  - `tests/integration/test_pagination_offset_limit.py` (NEW).
  - `tests/integration/test_competition_endpoint_filters.py` (NEW).
- **Action:**
  - Use `httpx.AsyncClient` + `lifespan="on"` to drive FastAPI app against testcontainer.
  - Pagination: seed 30 dummy competitions (or via factory), call `GET /api/v1/competitions?offset=10&limit=5`, assert response has 5 items + header `X-Total-Count: 30`.
  - Filters: call `?category=1a-territorial`, `?gender=m`, etc., assert filtered set.
- **Verify:** `uv run pytest tests/integration/test_pagination_offset_limit.py tests/integration/test_competition_endpoint_filters.py -v` green.
- **Done:** Both tests pass.
- **Commit:** `test(api): pagination + competition filter integration tests (#N)`.

### Task 7.6 — `test_games_endpoint.py` (SC4) + `test_players_endpoint.py`

- **Issue:** `test(p2): games + players endpoint integration`.
- **Files:**
  - `tests/integration/test_games_endpoint.py` (NEW).
  - `tests/integration/test_players_endpoint.py` (NEW).
- **Action:**
  - `test_games_endpoint`: with `seed_minimal`, `GET /api/v1/games/1` → assert payload has q1/q2/q3/q4 home+away keys + `box_scores` array length == 24.
  - `test_players_endpoint`: `GET /api/v1/players/99001-5-marc-soler` returns player; `GET /api/v1/players/1/stats?season_id=1` returns PlayerStatsRead with games_played≥1.
- **Verify:** `uv run pytest tests/integration/test_games_endpoint.py tests/integration/test_players_endpoint.py -v` green.
- **Done:** Both pass.
- **Commit:** `test(api): games detail + player slug+stats endpoints (#N)`.

### Task 7.7 — `test_pydantic_examples_render.py` (SC7)

- **Issue:** `test(p2): OpenAPI examples render in /openapi.json`.
- **Files:** `tests/integration/test_pydantic_examples_render.py` (NEW).
- **Action:** Start app via httpx AsyncClient. Fetch `/openapi.json`. Assert `data["components"]["schemas"]["CompetitionRead"]["examples"]` is a non-empty list. Repeat for Team/Player/Game/BoxScore/Standings/Leaderboard schemas. Assert each has at least 1 Catalan-flavored example (presence of `"display_name"` containing typical Catalan token like `CB` OR specific check).
- **Verify:** `uv run pytest tests/integration/test_pydantic_examples_render.py -v` green.
- **Done:** All schemas verified.
- **Commit:** `test(api): OpenAPI examples render at /openapi.json (#N)`.

### Task 7.8 — Coverage report + 80%+ gate

- **Issue:** `test(p2): enforce ≥80% coverage on repositories/`.
- **Files:** `.github/workflows/ci.yml` (modify — add coverage step + threshold), `pyproject.toml` (modify — `[tool.coverage]` config if not present).
- **Action:**
  - Add `--cov=src/basketball_stats/repositories --cov-fail-under=80` to pytest invocation in CI.
  - Local verification: `uv run pytest tests/ --cov=src/basketball_stats/repositories --cov-report=term-missing`.
- **Verify:**
  ```bash
  uv run pytest tests/ --cov=src/basketball_stats/repositories --cov-fail-under=80
  ```
  Exit 0 ⇔ ≥80%. Below 80% → add tests in this task.
- **Done:** Coverage ≥80% on `repositories/`, CI gate enforces.
- **Commit:** `test(ci): enforce 80% coverage on repositories (#N)`.

---

## Wave 8 — README screenshot + smoke test + verify-prep

### Task 8.1 — `/docs` Swagger UI screenshot → README

- **Issue:** `docs(p2): replace /docs placeholder with real screenshot`.
- **Files:** `assets/docs-screenshot.png` (NEW binary asset), `README.md` (modify — replace P1 D-30 §1 placeholder).
- **Action:**
  - **Default: Playwright headless capture** (autonomous, no Roger-at-keyboard requirement):
    1. `uv add --dev playwright && uv run playwright install chromium` (one-time).
    2. Start app: `uv run uvicorn basketball_stats.main:app &` (background).
    3. Seed: `uv run python -m basketball_stats.seed.minimal`.
    4. Capture script `scripts/capture-docs-screenshot.py`:
       ```python
       from playwright.sync_api import sync_playwright
       with sync_playwright() as p:
           browser = p.chromium.launch()
           page = browser.new_page(viewport={"width": 1280, "height": 1600})
           page.goto("http://localhost:8000/docs", wait_until="networkidle")
           page.wait_for_selector(".swagger-ui .opblock-tag", timeout=10000)
           page.screenshot(path="assets/docs-screenshot.png", full_page=True)
           browser.close()
       ```
    5. Run: `uv run python scripts/capture-docs-screenshot.py`.
  - **Fallback (manual):** open `http://localhost:8000/docs` + Win+Shift+S → save as `assets/docs-screenshot.png`. Use only if Playwright install fails on Render runner.
  - Edit README to replace placeholder text with `![/docs Swagger UI](assets/docs-screenshot.png)` + 1-line caption "API públic amb 8 GET endpoints + exemples catalans renderitzant a /docs".
- **Verify:**
  - `ls -la assets/docs-screenshot.png` shows file.
  - `grep -c "docs-screenshot.png" README.md` ≥ 1.
  - Render the README locally (or in GitHub web preview) shows image OK.
- **Done:** README screenshot present.
- **Commit:** `docs(readme): real /docs screenshot replaces P1 placeholder (#N)`.

### Task 8.2 — Smoke test script `scripts/smoke-test-p2.sh`

- **Issue:** `chore(p2): smoke-test all 8 GET endpoints`.
- **Files:** `scripts/smoke-test-p2.sh` (NEW, executable).
- **Action:**
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  BASE=${BASE:-http://localhost:8000}
  echo "Smoke testing P2 endpoints against $BASE"
  # READ-01
  curl -fsS "$BASE/api/v1/competitions" | jq 'length' | grep -E '^[1-9]'
  # READ-02
  curl -fsS "$BASE/api/v1/competitions/1/standings" | jq '.[0].position' | grep -E '^1$'
  # READ-03
  curl -fsS "$BASE/api/v1/competitions/1/leaderboards?stat=val&limit=3" | jq 'length'
  # READ-04
  curl -fsS "$BASE/api/v1/teams/1" | jq '.id'
  # READ-05
  curl -fsS "$BASE/api/v1/players/1" | jq '.id'
  # READ-06
  curl -fsS "$BASE/api/v1/players/1/stats?season_id=1" | jq '.games_played'
  # READ-07
  curl -fsS "$BASE/api/v1/games/1" | jq '.box_scores | length' | grep -E '^[12][0-9]$|^24$'
  # READ-08
  curl -fsS "$BASE/api/v1/competitions/1/games?matchday=1" | jq 'length'
  echo "All 8 endpoints OK"
  ```
- **Verify:**
  - Local: `BASE=http://localhost:8000 bash scripts/smoke-test-p2.sh` exits 0.
  - Render prod (after Render auto-deploy from PR merge — or skip if not yet auto-deployed): `BASE=https://basketball-stats-api-banq.onrender.com bash scripts/smoke-test-p2.sh`. **Note:** Render prod seed needs to be loaded — separate step, may surface as a P2.5 task.
- **Done:** Local smoke green. Document in PR body that prod smoke runs post-deploy.
- **Commit:** `chore(scripts): add P2 smoke-test script (#N)`.

### Task 8.3 — Final round-trip + `gsd-verify-work` prep

- **Issue:** `chore(p2): pre-verify-work checklist`.
- **Files:** None (verification only).
- **Action:**
  - Run full local matrix:
    ```bash
    uv run ruff check .
    uv run mypy --strict src/
    uv run pytest tests/ --cov=src/basketball_stats/repositories --cov-fail-under=80
    uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head
    uv run python -m basketball_stats.seed.minimal --force
    uv run uvicorn basketball_stats.main:app --port 8000 &
    sleep 3
    bash scripts/smoke-test-p2.sh
    kill %1
    ```
  - Verify all 7 SC TRUE (see mapping section below).
  - Open PR → wait CI verda → close all sub-issues → ready for `/gsd-verify-work 2`.
- **Verify:** All commands exit 0. PR CI verda. All P2 sub-issues closed (or scheduled to close-on-merge).
- **Done:** PR ready for review/merge.
- **Commit:** Final integration commit on the feature branch (likely merge commit) referencing umbrella issue.

---

## Goal-Backward Verification — 7 SC ↔ Plan Tasks Mapping

| SC | Truncated | Tasks proving it | Verification command |
|----|-----------|------------------|----------------------|
| 1 | `/standings` returns RANK + SQL visible | 1.1, 4.5, 5.1, 7.3 | `curl /api/v1/competitions/1/standings \| jq '.[0].position'` == 1 AND `grep -c "RANK() OVER" src/basketball_stats/repositories/standings.py` ≥ 1 |
| 2 | `/leaderboards?stat=val` window + composite index | 1.1, 4.6, 5.1, 7.4 | `grep -c "RANK() OVER" src/basketball_stats/repositories/leaderboards.py` ≥ 1 AND `grep -c "ix_games_competition_id" migrations/versions/0002_core_entities.py` ≥ 1 AND `curl /api/v1/competitions/1/leaderboards?stat=val&limit=3 \| jq '.[].position'` returns `[1,2,3]` |
| 3 | VAL as GENERATED COLUMN (FIBA PIR) | 1.1, 2.7, 7.2 | `grep -c "Computed(" migrations/versions/0002_core_entities.py` == 2 (reb+val) AND `pytest tests/integration/test_val_generated_column.py` green AND `psql -c "\d+ box_scores" \| grep -c "generated always as"` == 2 |
| 4 | `/games/{id}` box-score Q1-Q4 + full payload | 1.1, 4.4, 5.4, 7.6 | `curl /api/v1/games/1 \| jq '{q1_home, q4_away, total_home, box_scores: (.box_scores \| length)}'` returns full quarters + box_scores length == 24 |
| 5 | Integration tests on real PG cover window functions + /docs has examples | 7.1-7.8 | `pytest tests/integration -v` all green AND `curl /openapi.json \| jq '.paths \| keys \| length'` ≥ 9 |
| 6 | seed minimal populates DB | 6.1, 7.1 | `python -m basketball_stats.seed.minimal --force` exits 0 + `curl /api/v1/competitions \| jq 'length'` ≥ 1 AND `curl /api/v1/teams \| jq 'length'` == 2 |
| 7 | Pydantic schemas examples render at /docs | 3.1, 3.2, 3.3, 7.7 | `curl /openapi.json \| jq '.components.schemas.CompetitionRead.examples \| length'` ≥ 1 AND manual `/docs` visit shows Catalan examples dropdown AND `grep -rc "json_schema_extra" src/basketball_stats/schemas/` ≥ 6 |

---

## REQ-IDs Coverage Map (all 23, 1:1+)

| REQ-ID | Description | Tasks | Status |
|--------|-------------|-------|--------|
| DOM-01 | Club entity | 2.1 | Pending |
| DOM-02 | Team entity | 2.3 | Pending |
| DOM-03 | Player entity composite | 2.4 | Pending |
| DOM-04 | Competition tuple | 2.2 | Pending |
| DOM-05 | Game with Q1-Q4 | 2.6 | Pending |
| DOM-06 | BoxScore + GENERATED VAL | 2.7 | Pending |
| DOM-07 | Coach + CoachingAssignment | 2.5 | Pending |
| READ-01 | GET /competitions list+filters | 4.1, 5.1, 7.5 | Pending |
| READ-02 | GET /standings | 4.5, 5.1, 7.3 | Pending |
| READ-03 | GET /leaderboards | 4.6, 5.1, 7.4 | Pending |
| READ-04 | GET /teams/{id} | 4.2, 5.2 | Pending |
| READ-05 | GET /players/{id} | 4.3, 5.3, 7.6 | Pending |
| READ-06 | GET /players/{id}/stats | 4.3, 5.3, 7.6 | Pending |
| READ-07 | GET /games/{id} | 4.4, 5.4, 7.6 | Pending |
| READ-08 | GET /competitions/{id}/games | 4.4, 5.1 | Pending |
| STAT-01 | RANK window standings | 1.1, 4.5, 7.3 | Pending |
| STAT-02 | Window + composite index leaderboards | 1.1, 4.6, 7.4 | Pending |
| STAT-04 | VAL GENERATED COLUMN | 1.1, 2.7, 7.2 | Pending |
| STAT-05 | Composite index games_date | 1.1, 4.4 | Pending |
| INFRA-06 | Seed minimal | 6.1, 7.1 | Pending |
| OBS-01 | /docs with tags + examples | 5.5, 8.1, 7.7 | Pending |
| OBS-08 | Pydantic examples Catalan | 3.1, 3.2, 3.3, 7.7 | Pending |
| TEST-02 | testcontainers + window functions | 7.1-7.8 | Pending |

**Coverage:** 23/23 (100%). No orphans.

---

## Risks + Mitigations

1. **SQLAlchemy Computed() DDL mismatch vs migration.**
   - Risk: ORM emits slightly different SQL than the manual migration → CI round-trip drift or `MetaData.create_all()` shape diverges from `alembic upgrade`.
   - Mitigation: integration test that boots app against migration-applied DB; if SQLAlchemy schema reflection raises, fix mapping to match migration verbatim. Manual migration is canonical; models follow.

2. **testcontainers boot time slows CI to >5 min.**
   - Risk: session-scoped fixture + 8 routers + 24 box-score seed may push past P1 CI gate.
   - Mitigation: keep `seed_minimal` session-scoped (already planned). Skip seed for unit tests. Use `pytest -x` locally during iteration. If CI exceeds 5 min, add a separate `integration` job that runs in parallel to `unit + lint`.

3. **mypy --strict on SQLAlchemy 2.0 + `Computed(...)` may surface stub gaps.**
   - Risk: mypy errors on `Mapped[int] = mapped_column(Computed(...))` if stubs incomplete.
   - Mitigation: research §1 confirmed type-compat works in 2.0.49. If errors appear, use `# type: ignore[misc]` with comment referencing this risk + open issue to remove once stubs fixed.

4. **Render free Docker cold-start kills first smoke after deploy.**
   - Risk: post-merge `BASE=prod bash smoke-test-p2.sh` may 503 first time.
   - Mitigation: warm-ping workflow inherited from P1 keeps the dyno warm. Smoke is gated to local at task 8.2; prod smoke is a `--gaps` follow-up if needed.

5. **`docker compose exec api python -m basketball_stats.seed.minimal` requires Docker Desktop, which Roger may not have running locally (P1 ship known issue).**
   - Risk: SC6 strict-reading requires this exact command.
   - Mitigation: provide both forms — `python -m basketball_stats.seed.minimal` (uv-direct, works without Docker) + `docker compose exec api python -m basketball_stats.seed.minimal` (full INFRA-06 literal). Document both in README. Verify P1 smoke-bug ressurfaces here: if Docker missing, escalate to BLOCKED at handoff per CLAUDE.md verification-first rule.

6. **Coverage threshold may force test-shaped code in repositories.**
   - Risk: 80% on `repositories/` is tight if some branches (404 paths, filter combinations) aren't covered.
   - Mitigation: tasks 7.5+7.6 explicitly target filter+404 paths. If still <80%, add parametrized tests under `tests/unit/test_repositories_*.py` mocking session.

---

## Dependencies on Phase 1 (inherited, NOT re-implemented)

1. **Async engine + `AsyncSessionLocal` + `get_db()`** at `src/basketball_stats/core/db.py` — reused as-is.
2. **Pydantic Settings + dual-DSN** (`to_asyncpg_url()`) at `src/basketball_stats/core/config.py` — reused.
3. **structlog JSON + request_id middleware** — every new repo/router logs via `structlog.get_logger(__name__)`.
4. **Global exception handlers** at `src/basketball_stats/api/errors.py` — P1 D-04 catches 500s; we add `HTTPException(404)` raises directly per research §6.
5. **Alembic async env.py** — supports new migration 0002 without changes.
6. **testcontainers PostgresContainer + ryuk-off** at `tests/conftest.py` + `tests/integration/conftest.py` (P1 D-16) — append `seed_minimal` fixture only.
7. **ruff + mypy --strict CI gate** at `.github/workflows/ci.yml` — every new file must pass.
8. **Migration round-trip CI gate** (P1 D-08) — auto-validates 0002 reversibility.
9. **GitHub Issues + labels + milestones workflow** — project CLAUDE.md hard rule, applied per-task.

---

## Out of Scope (do NOT implement in P2)

- **FCBQ Ingest CLI** → Phase 2.5 separate post-ship.
- **Auth + JWT + writes (POST/PUT) + BackgroundTask recompute** → Phase 3.
- **`/ideal-five` flagship endpoint** → Phase 4.
- **tsvector + GIN + accent-search** → Phase 4 (the `normalize_name` here primes it).
- **Deploy-on-tag automation (INFRA-04)** → Phase 4.
- **ADRs beyond 0003 + 0004 (README walkthrough, defense doc)** → Phase 5.
- **Materialized view `player_season_averages`** → v2 if performance demands.
- **Cross-phase aggregate endpoint** (`?across=phase`) → Phase 4 or v2.
- **Head-to-head tie-breaker CTE complex** → v2 (ADR-0004 documents upgrade path).
- **Service layer for reads** → P3 with AUTH writes (transactions/permission).
- **Materialized view for standings** → v2 if performance demands.
- **JSONB play-by-play column** → P4 or v2.
- **Streak detection (LAG window)** → P4 / v2.
- **`/matchday/{date}/mvp`** → P4 / v2.

---

*Plan: 2-core-entities · planned 2026-05-20 · 8 build waves + setup · 23 REQ-IDs + 7 SC traceable.*
