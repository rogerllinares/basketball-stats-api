---
status: complete-with-deferred-gap
phase: 02-core-entities
source:
  - .planning/ROADMAP.md §Phase 2 (7 SC)
  - .planning/phases/02-core-entities/02-PLAN.md (32 tasques, 9 waves)
started: 2026-05-21
updated: 2026-05-21
verifier: Claude (manual orchestration — gsd-sdk not in PATH)
mode: retroactive (post-merge, master 4c107bc)
---

## Current Test

[testing complete — 1 gap DEFERRED to Phase 2.5 per Roger decision 2026-05-21]

## Tests

### 1. SC1 — RANK() window function in standings repository
expected: `GET /competitions/{id}/standings` retorna standings amb `RANK() OVER (PARTITION BY ... ORDER BY ...)` visible al SQL del repository + tie-breakers FCBQ correctes + comentari explicatiu.
result: pass
evidence: `src/basketball_stats/repositories/standings.py:61` (`RANK() OVER`), L3 docstring `"Showcase: PostgreSQL window function RANK() OVER (PARTITION BY ... ORDER BY ...)"`, ADR-0004 documenta tie-breaker FEB-simple. CI master verda confirma SQL parse.

### 2. SC2 — Leaderboards window function + composite index
expected: `GET /competitions/{id}/leaderboards?stat=val` retorna top-N usant window function + composite index `(competition_id, season, avg_stat DESC)`.
result: pass
evidence: `src/basketball_stats/repositories/leaderboards.py:45` (`RANK() OVER`) + `migrations/0002_core_entities.py:300,315` (`ix_games_competition_id`, `ix_box_scores_val_desc`). Index original D2-20 substituït per 3 indexes reals (avg_stat output de window function = no indexable), decisió Q1 documentada al handoff.

### 3. SC3 — VAL com a GENERATED COLUMN amb expressió SQL FIBA PIR
expected: Migration mostra `VAL` com a GENERATED COLUMN amb expressió PIR FIBA, no calculat a Python.
result: pass
evidence: `migrations/0002_core_entities.py:281-292` — `sa.Column("val", sa.Integer(), sa.Computed("pts + (reb_of + reb_def) + ast + rec + tap + fouls_drawn - (fg2a - fg2m) - (fg3a - fg3m) - (fta - ftm) - per - fc - blocks_received", persisted=True))`. Formula FIBA PIR completa. ADR-0003 documenta decisió + asymmetry Supercopa↔Territorial.

### 4. SC4 — GET /games/{id} box-score complet Q1-Q4
expected: `GET /games/{id}` retorna box-score complet de tots els jugadors d'ambdós equips amb marcador per quart Q1-Q4.
result: pass
evidence: `src/basketball_stats/api/v1/games.py:23-35` (`@router.get("/{game_id}")` retorna `GameRead` amb `box_scores` embedded). Schema `GameRead` inclou `q1_home/q1_away..q4_home/q4_away`. `selectinload(Game.box_scores)` evita N+1 (D-pitfall P1.2). Smoke live no possible per DB buida (cf SC6 gap).
note: parcialment cobert per integration test `tests/integration/test_games_endpoint.py` (CI verda).

### 5. SC5 — Integration tests sobre Postgres real via testcontainers + /docs
expected: Test suite d'integration corre sobre Postgres real via testcontainers (no mocks, no SQLite) i cobreix queries amb window functions; `/docs` mostra tots els endpoints amb tags i exemples.
result: pass
evidence: 10 fitxers a `tests/integration/`: test_standings_rank, test_leaderboards_val, test_val_generated_column, test_games_endpoint, test_competitions_endpoint, test_players_endpoint, test_seed_minimal_loads, test_pydantic_examples_render, test_healthz. `tests/conftest.py` usa `PostgresContainer`. CI master `4c107bc` verda (alembic round-trip + ruff/mypy/pytest unit+integration). `/docs` live OpenAPI render ✅ (Phase 1 preservat).

### 6. SC6 — Seed minimal executat + smoke curl /competitions retorna ≥1 item
expected: `data/seed/minimal.py` executable poblea DB amb 1 competition + 2 teams + 1 game + 12 box-scores; tots els READ endpoints retornen dades no buides en local i en testcontainers; smoke-test `curl localhost:8000/competitions` torna array amb almenys 1 item.
result: issue
reported: "`GET https://basketball-stats-api-banq.onrender.com/api/v1/competitions` retorna `[]` en producció. El seed mai s'ha corregut contra Neon prod. Render boota Docker amb DB connectada però sense dades. Integration tests sí passen (testcontainers + seed_minimal fixture cada test), però producció continua amb DB buida des de la migration."
severity: major
artifacts:
  - src/basketball_stats/seed/minimal.py (existeix, no s'invoca en deploy)
  - render.yaml (no executa seed step)
  - Dockerfile (CMD = uvicorn, no seed)
  - migrations/versions/0002_core_entities.py (només DDL, no DML)
missing:
  - Mecanisme de seed-on-deploy (post-deploy hook a Render, o startup task FastAPI, o GHA job que truca seed contra Neon)
  - O alternativa: skipar seed minimal i esperar Phase 2.5 (FCBQ Ingest CLI amb dades reals)

### 7. SC7 — Pydantic schemas amb examples en català
expected: Tots els Pydantic schemas (Create/Read/Update) tenen `model_config = ConfigDict(json_schema_extra={"examples": [...]})` amb dades realistes en català (ex: "CB Granollers"); `/docs` renderitza payload exemple a cada endpoint.
result: pass
evidence: `src/basketball_stats/schemas/team.py:24,30,53` examples `{"display_name": "CB Granollers"}` + `"CB Artés"`. `schemas/standings.py:17,28` mateixos. `schemas/competition.py:1` docstring `"OBS-08 examples in Catalan"`. `schemas/coach.py:11,33` json_schema_extra. Integration test `test_pydantic_examples_render.py` verifica que OpenAPI genera els examples (CI verda).

## Summary

total: 7
passed: 6
issues: 1
pending: 0
skipped: 0

## Gaps

```yaml
- truth: "GET /competitions retorna array amb almenys 1 item (SC6)"
  status: failed
  reason: "User reported: GET https://basketball-stats-api-banq.onrender.com/api/v1/competitions retorna [] en producció. Seed minimal mai executat contra Neon prod. Render Docker boota amb DB connectada però sense dades."
  severity: major
  test: 6
  artifacts:
    - src/basketball_stats/seed/minimal.py
    - render.yaml
    - Dockerfile
    - migrations/versions/0002_core_entities.py
  missing:
    - Seed-on-deploy mechanism (post-deploy hook, startup task, o GHA cron)
    - O alternativa: skip seed minimal, anar directe a Phase 2.5 FCBQ Ingest amb dades reals
  decision: DEFERRED to Phase 2.5 (Roger 2026-05-21). Quick fix runtime seed descartat — Phase 2.5 substituirà el seed minimal per dades reals FCBQ (2a Catalana → Supercopa M+F). `/api/v1/competitions` continuarà retornant `[]` en producció fins que P2.5 ship (~6-8h estimat). Risc acceptat: recruiter que entri en aquesta finestra veurà API buida; mitigació parcial via README links a `tests/integration/` + `AI_basketball-portfolio-defense.md`.
```

## Acknowledged Gaps

- **Playwright screenshot deferred** (Wave 8 AFK 2026-05-20) — Docker Desktop OFF durant AFK. No bloqueja CI ni functionality. Manual quan Docker Desktop ON. Issue tracking al TODO §Basketball Stats API [P3] Docker Desktop local #8.

## Notes

- Audit retroactiu post-merge (master `4c107bc`), no live UAT amb Roger durant build.
- 6/7 SC verificats via source + CI; SC6 verificat via live HTTP fetch.
- Decisió Roger 2026-05-21: **SC6 DEFERRED a Phase 2.5**. Phase 2 considerada SHIPPED amb 1 gap conegut + mitigació planificada. Próximo paso al handoff: `/gsd-insert-phase` → `/gsd-discuss-phase 2.5`.
