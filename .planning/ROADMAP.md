---
project: basketball-stats-api
created: 2026-05-19
updated: 2026-05-19
status: draft (post-review revisions applied, pending Roger sign-off)
phases: 5
requirements_mapped: 43
granularity: coarse
---

# ROADMAP — Basketball Stats API

## Overview

End state: una API REST FastAPI + Postgres pur desplegada a Koyeb amb Neon, amb dades reals de la lliga de Roger, CI/CD verd, OpenAPI a `/docs` públic, README amb stack walkthrough i `AI_basketball-portfolio-defense.md` defensable en una entrevista de 30 min. Delivery shape: 5 phases coarse, cadascuna cabable en 2-3 dies de feina enfocada per dev jr, total MVP en 10-15 dies de calendari. P1 deixa el skeleton desplegat; P2 ja entrega valor (read endpoints amb window functions que justifiquen el stack); P3 tanca el cicle d'escriptura; P4 afegeix el diferenciador tsvector + automatització deploy on tag; P5 és narrativa-only (README + ADRs + defense doc) per fer la peça presentable a recruiters.

## Phase Summary

| # | Name | Goal | REQ count | Success criteria count |
|---|------|------|-----------|------------------------|
| 1 | Foundation | Skeleton desplegat amb CI verd i `/healthz` accessible públicament | 8 | 5 |
| 2 | Core entities + public read | API pública amb window functions visible al codi, totes les entitats del domini català, seed mínim i OpenAPI examples | 23 | 7 |
| 2.5 | FCBQ Ingest CLI (INSERTED) | Offline batch CLI scrapejant FCBQ (2a Catalana → Supercopa M+F) → JSON fixtures commitejats + loader, substituint el seed mínim amb dades reals catalanes | TBD | TBD |
| 3 | Auth + coach writes | Coaches autenticats pugen i corregeixen box-scores amb recompute automàtic | 6 | 4 |
| 4 | Differentiators + deploy automation | Flagship endpoint `/ideal-five` + full-text search jugadors + pipeline deploy on tag funcional | 3 | 4 |
| 5 | Polish (docs-only) | README walkthrough + 6 ADRs + portfolio defense doc → tag `v0.1.0` | 3 | 4 |

## Phase 1: Foundation

**Goal:** Skeleton del projecte funcional end-to-end: container builda, CI passa, `/healthz` respon des d'una URL pública Koyeb amb Neon connectat. **NO Redis al MVP** (carried out 2026-05-19 post-review).

**Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-05, OBS-02, OBS-03, OBS-07, TEST-01

**Success criteria** (what must be TRUE):
1. `docker compose up` aixeca `api + postgres` localment i `curl localhost:8000/healthz` retorna `{"status":"ok","db":"ok"}` amb check real Postgres (`SELECT 1`). Sense camp `cache` al MVP.
2. `git push` a `main` dispara GHA workflow que executa `ruff check` + `mypy --strict` + `pytest`, tot verd, en menys de 5 min.
3. Koyeb serveix la imatge a una URL pública i `curl <url>/healthz` confirma DB Neon connectada.
4. README mostra badges de CI status (verd), ruff, mypy, Python version, license.
5. Logs estructurats en JSON apareixen a Koyeb logs amb `request_id` per cada request.

**Dependencies:** none (first phase)

**Plans:** TBD

## Phase 2: Core entities + public read

**Goal:** API pública complerta amb totes les entitats del domini català FCBQ modelades, tots els GET endpoints servint dades reals, i window functions Postgres visibles al codi com a diferenciador del stack.

**Requirements:** DOM-01, DOM-02, DOM-03, DOM-04, DOM-05, DOM-06, DOM-07, READ-01, READ-02, READ-03, READ-04, READ-05, READ-06, READ-07, READ-08, STAT-01, STAT-02, STAT-04, STAT-05, TEST-02, OBS-01, OBS-08, INFRA-06

**Success criteria** (what must be TRUE):
1. `GET /competitions/{id}/standings` retorna standings amb `RANK()` window function i tie-breakers FCBQ correctes; el SQL és visible a `repositories/standings.py` amb comentari explicatiu.
2. `GET /competitions/{id}/leaderboards?stat=val` retorna top-N jugadors per VAL usant window function + composite index `(competition_id, season, avg_stat DESC)`.
3. Migration d'Alembic mostra `VAL` com a GENERATED COLUMN amb expressió SQL FIBA PIR, no calculat a Python.
4. `GET /games/{id}` retorna box-score complet de tots els jugadors d'ambdós equips amb marcador per quart Q1-Q4.
5. Test suite d'integration corre sobre Postgres real via testcontainers (no mocks, no SQLite) i cobreix les queries amb window functions; `/docs` mostra tots els endpoints amb tags i exemples.
6. `data/seed/minimal.py` executable poblea DB amb 1 competition + 2 teams + 1 game + 12 box-scores; tots els READ endpoints retornen dades no buides en local i en testcontainers (smoke-test `curl localhost:8000/competitions` torna array amb almenys 1 item).
7. Tots els Pydantic schemas (Create/Read/Update) tenen `model_config = ConfigDict(json_schema_extra={"examples": [...]})` amb dades realistes en català (noms equip tipus "CB Granollers"); `/docs` renderitza payload exemple a cada endpoint POST/PUT i resposta exemple a cada GET (verificat manualment a `localhost:8000/docs`).

**Dependencies:** Phase 1

**Plans:** TBD

## Phase 2.5: FCBQ Ingest CLI (INSERTED 2026-05-21)

**Context:** Inserted post Phase 2 ship per resoldre SC6 gap (`GET /api/v1/competitions` retornava `[]` en producció — seed minimal mai s'executava contra Neon). En lloc de fer un quick fix runtime del seed fictici, substituir-lo per ingest **offline batch de dades reals catalanes FCBQ** — major valor portfolio (recruiter veu equips, partits, jugadors reals al `/docs`) sense violar la constraint LOCKED `no-live-ingest` (cap consulta HTTP a FCBQ des de la API en producció).

**Goal:** CLI Python executable (`python -m basketball_stats.ingest.fcbq <comp> <season>`) que scrapeja les pàgines HTML FCBQ d'una competició + temporada, normalitza a JSON fixtures versionats a `data/seed/fcbq/<comp-slug>-<season>.json`, i `data/seed/load_fcbq.py` carrega aquests fixtures al DB. La API en prod NO truca FCBQ — només llegeix les JSON fixtures committejades. Cobertura mínima: 2a Catalana M+F → Supercopa M+F (mateix nivell que basquethero.cat). Categories aproximades: super-copa, copa-catalunya, cc-1a, cc-2a, 1a-territorial, 2a-territorial × M+F × grups territorials (bcn/gir/tar/lle).

**Requirements:** TBD (a definir a `/gsd-discuss-phase 2.5`)

**Success criteria** (what must be TRUE):
1. TBD — definits durant discuss-phase. Punts ancora previsibles:
   - CLI scrapeja almenys 1 competició FCBQ (default: cc-2a M) i escriu JSON fixture vàlid a `data/seed/fcbq/`.
   - `load_fcbq.py` executat contra Neon prod fa que `GET /api/v1/competitions` retorni ≥1 item (tanca SC6 P2).
   - Cap codi del package `src/basketball_stats/` (production runtime) importa res de `ingest/` (separació strict offline ↔ runtime).
   - ADR-0005 documenta la decisió "offline batch utility per preservar LOCKED no-live-ingest constraint" + alternatives considerades.
   - CI verda amb test que verifica una fixture sample carrega sense errors via testcontainers.

**Dependencies:** Phase 2 (models, migrations, repositories, schemas) + decision Roger 2026-05-21 DEFER SC6 a aquesta fase.

**Plans:** TBD

## Phase 3: Auth + coach writes

**Goal:** Coaches poden autenticar-se i pujar/corregir box-scores complets, amb recompute automàtic d'agregats en background.

**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, TEST-03

**Success criteria** (what must be TRUE):
1. Coach pot fer `POST /auth/login` amb email + password i rebre un JWT bearer token (argon2id hash a la DB).
2. `POST /games` amb JWT vàlid d'un coach owner del team crea game + box-score complet en una sola transaction; sense JWT o sense ownership retorna 401/403.
3. `PUT /games/{id}/boxscore` permet corregir només si el coach és owner del team afectat; `require_coach` Depends valida JWT + role + ownership.
4. Després d'un POST/PUT exitós, una BackgroundTask recomputa season averages i les pròximes queries de `/leaderboards` reflecteixen els valors nous sense intervenció manual.

**Dependencies:** Phase 2

**Plans:** TBD

## Phase 4: Differentiators + deploy automation

**Goal:** Flagship endpoint `/matchday/{date}/ideal-five` (window function RANK PARTITION BY posició + scoring compost) + full-text search jugadors amb accents catalans + pipeline deploy on tag funcional. Aquesta phase és la que un recruiter recorda — `/ideal-five` no existeix a cap referent català.

**Requirements:** READ-09, STAT-03, INFRA-04

**Success criteria** (what must be TRUE):
1. `GET /search/players?q=jordi` retorna matches amb fuzzy matching sobre tsvector + GIN index, i `q=jordí` o `q=jordi` retornen els mateixos resultats (suport accents).
2. Crear tag `v0.0.x-rc` al repo dispara GHA workflow que builda imatge, la pushea al Koyeb registry, fa deploy i executa `alembic upgrade head` com a release_command sense intervenció manual.
3. Migration amb tsvector + GIN index és visible al directori `migrations/` amb `downgrade()` reversible.
4. `GET /matchday/2026-03-15/ideal-five` retorna exactament 5 jugadors (1 PG + 1 SG + 1 SF + 1 PF + 1 C) ordenats per `composite_score` (`PTS + REB*1.2 + AST*1.5 + REC*2 - PER*1.5`); SQL visible a `repositories/ideal_five.py` amb comentari explicant scoring formula + `RANK() OVER (PARTITION BY position ORDER BY composite_score DESC)`; query funciona sobre testcontainers Postgres real amb seed minimal expandit a ≥5 jugadors per posició.

**Dependencies:** Phase 3

**Plans:** TBD

## Phase 5: Polish (docs-only)

**Goal:** Peça presentable a recruiters: README walkthrough complet, ADRs cobrint decisions no-òbvies, defense doc tipus SST i tag `v0.1.0` desplegat a prod amb dades reals seedejades.

**Requirements:** OBS-04, OBS-05, OBS-06

**Success criteria** (what must be TRUE):
1. README té secció "Stack walkthrough" amb cada eina del stack llistada com `(per què, file:line on s'usa, què demostra al recruiter)`; els file:line són links GitHub clicables.
2. `docs/adr/` conté mínim 6 ADRs numerats (0001-000N) cobrint: stack election, auth method, sync vs background ingest, cache strategy, Koyeb switch, repository pattern.
3. `AI_basketball-portfolio-defense.md` al root té estructura tipus SST: stack + arquitectura + trade-offs + 7 Q&A típiques d'entrevista (window functions, async patterns, deploy choice, JWT vs sessions, testcontainers, generated columns, error handling).
4. Tag `v0.1.0` creat → CI verd → deploy automàtic → `<koyeb-url>/docs` accessible amb `data/seed/real.py` executat (Sènior A de Roger; mínim 1 competition + 2 teams + 1 partit real amb box-score complet extret de l'acta FCBQ). Substitueix el seed minimal de P2.

**Dependencies:** Phase 4

**Plans:** TBD

## Coverage Matrix

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

**Total mapped:** 43 / 43 v1 requirements (100% coverage)

> Nota: original draft 40 REQs. Post-review 2026-05-19 afegits 3 nous (READ-09 ideal-five flagship, OBS-08 schema examples, INFRA-06 seed minimal) → 43 totals (DOM 7 + READ 9 + AUTH 5 + STAT 5 + INFRA 6 + OBS 8 + TEST 3 = 43). Coverage 100%.

## Out-of-roadmap (v2 — deferred per config.json scope)

Llistats a REQUIREMENTS.md §v2 com a hipòtesi de continuïtat post-MVP:

- **Redis cache amb invalidation explícita** per `POST /games` — carried OUT of MVP 2026-05-19 post-review. MVP usa només BackgroundTask sense Redis layer. Re-introduir només quan hi hagi cas d'ús real.
- JSONB play-by-play column (showcase JSONB requeria dades de play-by-play que els referents catalans no tenen; deferred a v2 si Roger vol).
- `GET /matchday/{date}/mvp` — MVP individual de la jornada amb window function RANK + filtre data + composite scoring.
- Streak detection (jugador / equip amb millor ratxa).
- Player development trend (`LAG` window function + temporal series).
- Free agents / fichajes endpoint (basquethero.cat differentiator).
- Multi-tenant SaaS (workspaces per lliga).
- WebSockets per live score updates.

## Notes

- **Phase 1 critical path:** sense INFRA-01/02/03/05 + OBS-02 no hi ha skeleton desplegable. P1 ha de tancar amb Koyeb verd o tot el roadmap s'enfonsa. **NO Redis al MVP** — `docker-compose` només `api + postgres`.
- **Phase 2 value lock:** STAT-01/02 (window functions) + INFRA-06 (seed minimal) + OBS-08 (Pydantic examples) viuen aquí, no a P4/P5. Sense aquests 3, els READ endpoints retornen `[]` i `/docs` es veu amateur — la phase no és demoable.
- **Phase 3 simpler than P4:** auth + writes és més senzill que tsvector + accents + deploy automation + flagship endpoint; ordre correcte.
- **Phase 4 sharper:** 3 reqs (STAT-03 tsvector + INFRA-04 deploy on tag + **READ-09 `/ideal-five`**). `/ideal-five` és el flagship endpoint del projecte — query no trivial amb `RANK() PARTITION BY position`, no existeix a cap referent català (basquethero.cat inclòs). És el que un recruiter recorda.
- **Phase 5 docs-only:** zero nous endpoints. Substitueix `data/seed/minimal.py` per `data/seed/real.py` amb dades reals del Sènior A de Roger. Si emergeix la necessitat de codi nou aquí, crear Phase 4.x via `/gsd-insert-phase`.
- **Redis decision (2026-05-19 post-review):** dropped del MVP. El `docker-compose redis` original era dead-weight — cap endpoint l'usava. Re-introduir només a v2 quan hi hagi cas d'ús real de cache invalidation. Documentat com ADR a P5.
