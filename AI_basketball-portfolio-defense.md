---
title: Basketball Stats API — Portfolio Defense (chuleta de entrevista)
created: 2026-05-21
updated: 2026-05-21
tags: [basketball-stats-api, portfolio, interview, job-hunt-sep-2026, python, fastapi, postgres]
status: draft
project: basketball-stats-api
source: AFK overnight 2026-05-21 buffer extension
related: ["CLAUDE.md", ".planning/ROADMAP.md", ".planning/phases/02-core-entities/02-PLAN.md"]
---

# Basketball Stats API — Portfolio Defense

## Resumen

Chuleta per defensar Basketball Stats API en entrevistes (target: junior Backend Python + DevOps-curious, sep 2026). Pattern adaptat de `AI_apostes-portfolio-defense.md` + `AI_sst-portfolio-defense.md`. **Status: draft v1 escrit AFK overnight 2026-05-21**, sense walkthrough oral encara. Phase 1 SHIPPED + Phase 2 100% executat (PR #13 OPEN mergeable). Roger polir to + practicar 30 min abans d'usar-ho.

---

## 1. Problema (60 segons parlats)

> "El bàsquet amateur i semi-pro a Catalunya (lliga FCBQ — Federació Catalana de Basquetbol) genera milers de partits l'any sense un servei modern d'stats. Els referents existents (basquethero.cat, fcbq.cat) són HTML estàtic sense API i tracking limitat a 1a Catalana. Basketball Stats API resol això amb un REST FastAPI + Postgres que serveix box-scores, leaderboards, standings i ideal-fives per qualsevol competició de 2a Catalana fins a Supercopa, masc + fem, amb window functions Postgres per stats avançades (VAL/PIR FIBA), GENERATED COLUMNS al schema, i deploy IaC verificable."

**Per què importa en una entrevista Backend Python:** API-only, sense frontend, posa el focus en domain modelling + SQL avançat + testing infrastructure. Un recruiter veu Pydantic v2 examples + window functions + testcontainers + Alembic round-trip + Render IaC + GHA warm-ping cron — tota la stack backend "que es defensa en interview".

**Per què importa per al meu nínxol (EE+CS junior):** demostra que entenc PostgreSQL profundament (no només "soc capaç de fer `SELECT *`"). Window functions + GENERATED COLUMNS + indexos sobre columnes computades = senyal fort de "no és un junior que només copia Stack Overflow".

**El que NO dic:** "és un toy project". **Sí dic:** "live en producció, dades reals catalanes, deploy IaC reproduïble, ADR-driven decisions."

---

## 2. Stack + per què (l'important)

| Capa | Tech | Per què (en 1 frase) |
|---|---|---|
| Framework | FastAPI 0.115 + Python 3.12 (no 3.14) | Type hints + async + OpenAPI auto-generat + Pydantic v2 examples al `/docs`. Python 3.12 perquè és la versió més estable LTS-style (3.14 té breaking changes a typing). |
| ORM | SQLAlchemy 2.0 async + asyncpg | 2.0 async + Mapped[T] type-checked. asyncpg és l'únic driver Postgres async madur. `lazy="raise_on_sql"` a totes les relationships per detectar N+1 al test. |
| Migrations | Alembic async template + manual writes per Computed columns | `alembic revision --autogenerate` NO detecta `Computed()` (research §1) — migrations escrites manual. Round-trip gate (`upgrade → downgrade → upgrade`) en CI per a defenser cap migration sense reversibilitat. |
| DB | Postgres 16 (Neon free tier) + 9 entitats + 2 GENERATED columns + 4 indexes (incl. un sobre columna computed) | Neon = Postgres pur (no DynamoDB-style abstracció) + free tier + branching nativa. GENERATED `VAL` columna materialitza l'expressió FIBA PIR — no es calcula en Python, es calcula al SELECT. |
| Schemas | Pydantic v2 amb `ConfigDict(json_schema_extra={"examples":[...]})` | `/docs` mostra payload realistic en català (CB Granollers, Marc Soler, etc.). Recruiter prova `Try it out` i veu dades verificables, no `{"name":"string"}`. |
| Tests | pytest + testcontainers-python (PostgresContainer) | Integration tests corren sobre Postgres real (no SQLite, no mocks). Cobreix window functions + Computed columns + tie-breakers FCBQ. CI corre testcontainers en GHA. |
| Lint/Format | ruff + mypy --strict + pre-commit | Tot strict. `mypy --strict` per cada fitxer modified. Pre-commit blocks bad commits localment abans del push. |
| Container | Docker multi-stage + docker-compose local | `docker compose up` arrenca DB + API local. Multi-stage build amb `uv` per dependencies + slim runtime image. |
| Deploy | Render free Docker + render.yaml IaC + GHA warm-ping cron (`*/14min`) | render.yaml = Infrastructure-as-Code (recruiter veu reproductibilitat sense clicar UI). Render free tier cold-start 30s → warm-ping cron evita-ho. Pivot des de Koyeb 2026-05-20 (ADR-0002) quan Koyeb va treure free tier. |
| CI | GHA: ruff + mypy + pytest unit + testcontainers integration + alembic round-trip gate | 4 checks separats. Verde a master = ship-ready. PR #13 té statusCheckRollup.conclusion=SUCCESS. |
| Auth (P3+) | JWT via python-jose | No implementat encara — Phase 3+. Public read-only ara. |

**Si pregunten per què FastAPI i no Django REST:** "FastAPI = async-native + Pydantic-native + OpenAPI auto. Django REST és synchronous-default i requereix DRF serializers + django-rest-swagger per OpenAPI. Per un API-only servei, FastAPI estalvia ~30% boilerplate."

**Si pregunten per què Postgres pur i no MongoDB / Supabase:** "Postgres pur perquè vull demostrar SQL avançat (window functions, GENERATED columns, indexes sobre computed). Supabase també seria Postgres però amb RLS i auth bundled que afegirien dependència no necessària per un GET-only API. Mongo no encaixa — el domini és relacional (clubs ↔ teams ↔ players ↔ box_scores)."

**Si pregunten per què Render i no AWS/GCP:** "Render = render.yaml IaC + free tier Docker + zero-config deploys. AWS/GCP serien overkill per un side project + cost no trivial. Pivot des de Koyeb 2026-05-20 documentat a ADR-0002 perquè els free tiers viuen i moren — la lliçó és IaC + portabilitat (Docker), no vendor lock-in."

---

## 3. Arquitectura — capa per capa (1 minut)

```
Browser / curl
  ↓ HTTP GET
Render Docker (FastAPI uvicorn)
  ↓ asyncpg pool (sslmode=prefer, channel_binding strip)
Neon Postgres 16 (branching free tier)
  ↑
  GHA warm-ping cron (*/14min) ← evita cold-start
  GHA CI (ruff + mypy + pytest + alembic round-trip) ← gate ship
```

Repos separats per claretat:
- `basketball-stats-api` (backend FastAPI + Postgres)
- (P3+) `basketball-stats-web` (frontend opcional)
- (P2.5) FCBQ Ingest CLI (offline batch — preserva el lock "API en prod NO scrapeja FCBQ live")

---

## 4. Decisions defensables (ADRs)

| ADR | Decisió | Per què |
|---|---|---|
| 0001 | Stack election (FastAPI + Postgres + Alembic) | Single-version policy. Tot 3.12 + Postgres 16. Sense dual-track Python. |
| 0002 | Deploy pivot Koyeb → Render | Koyeb va treure free tier post-Mistral 2026-05-19. Pivot mid-execute amb full IaC migration (render.yaml + docs/setup/render-neon.md + banner SUPERSEDED a koyeb-neon.md). |
| 0003 | VAL formula PIR FIBA + Supercopa↔Territorial asymmetry | FIBA VAL = PTS + REB + AST + STL + BLK - FGmissed - FTmissed - TO. Supercopa permet inscriure jugadors d'altres equips federats; Territorial no. ADR documenta asimetria a queries de standings. |
| 0004 | Standings tie-breaker FEB-style | FEB usa head-to-head 1r, després point diff. Implementat a `repositories/standings.py` amb upgrade path documentat (si FCBQ canvia regles, només queda canviar el `ORDER BY`). |

---

## 5. Tres coses que mostraria primer al recruiter (3 minuts demo)

### 5.1 `/docs` Swagger UI en producció

Obre https://basketball-stats-api-banq.onrender.com/docs → mostra:
- 11 endpoints organitzats per tags (Competitions / Teams / Players / Games)
- `Try it out` → payload exemple realistic en català (CB Granollers, Marc Soler)
- Schema details → `VAL` és Computed (no editable from API — generated by Postgres)

**Punt clau:** "Mira els examples — són dades reals de catalan basketball, no `{name: string}`. Això surt de Pydantic `ConfigDict(json_schema_extra={examples})`. Defenseu un API perquè es prova en `Try it out` sense necessitat de Postman."

### 5.2 Migration 0002 — Computed VAL column

`migrations/versions/0002_core_entities.py` — ensenyar al recruiter:
- `sa.Computed("pts + reb + ast + stl + blk - fg_missed - ft_missed - turnovers", persisted=True)`
- `op.create_index("ix_box_scores_val_desc", "box_scores", [sa.text("val DESC")])`

**Punt clau:** "El recruiter veu que VAL no és Python-computed. És Postgres-computed. L'índex és sobre la columna generated. Quan algú demana `top-10 players per VAL`, el SELECT no calcula VAL — l'índex ja el té materialitzat ordenat DESC. Latència sub-ms."

### 5.3 Window function al leaderboards repository

`src/basketball_stats/repositories/leaderboards.py`:
```python
# RANK() OVER (PARTITION BY position ORDER BY avg_val DESC)
# Returns top-N players per position with their per-game averages.
```

**Punt clau:** "Window functions amb PARTITION BY són el showcase. La majoria de juniors mai han escrit `OVER (PARTITION BY ...)`. Es defensa explicant que això substitueix N+1 queries amb una sola query — el típic anti-pattern que els recruiters busquen detectar."

---

## 6. Trade-offs reconeguts (mostra honestedat)

| Trade-off | Decisió | Per què acceptat |
|---|---|---|
| Render free cold-start ~30s | Warm-ping cron `*/14min` | Beta phase. P5 podria moure a Render paid ($7/mes) si traffic justifica. |
| asyncpg `sslmode` handling bug | Helper `to_asyncpg_url()` strip libpq params | Neon URLs porten `sslmode=require&channel_binding=require` (libpq syntax), asyncpg parsea diferent. Detectat + fixat en deploy Phase 1. |
| `gsd-sdk` no al PATH (orquestració GSD manual) | Spawn `gsd-executor` manualment amb PLAN.md | Documented a `config.json _meta`. Patró usat amb èxit P1 + P2. |
| No frontend | Backend-only repo | Compleix scope "demostrar backend Python". Frontend potencial a P3+ (`basketball-stats-web`) o landing custom dins el repo. |
| GitHub Issues OBLIGATORI per portfolio signal | Tota task = 1 issue + labels + milestone + PR `Closes #N` | Recruiter mira el repo i veu disciplina vs ad-hoc commits. |
| Phase 2 plan amb 32 tasques 9 waves (over-spec per side project?) | Sí, però signal de "sé planificar" | GSD workflow oblig per fases. Plan complet + plan-checker PASS 9/9 dimensions abans d'executar. |

---

## 7. 7 Q&A típiques (preparades)

### Q1: Per què Catalan basketball?
A: "Visc el domini — sóc jugador amateur. La regla #1 per side project útil és "tens un avantatge injust" — el domain knowledge és el meu. FCBQ no té API. Trobada de necessitat + opportunity portfolio."

### Q2: Com gestiones noms amb accents catalans (ç, à, è)?
A: "`normalize_name()` utility — NFD decomposition + filter Mn category + `ç→c` transliteration via maketrans + UPPER + strip. Test cases parametritzats inclou `('Barça', 'BARCA')`. Decisió documentada a Q2 del plan Phase 2."

### Q3: Per què Alembic manual i no autogenerate?
A: "Autogenerate de SQLAlchemy NO detecta `Computed()`. Si automatitzo, perdo les Computed columns o em sucededeix migration drift. Escrivint a mà tinc 100% control — i la regla del repo és round-trip test (`upgrade → downgrade → upgrade`) que ha de passar verde en CI. Si la migration trenca, el test ho detecta abans del merge."

### Q4: Què passa quan Neon free tier es acaba?
A: "Render i Neon estan dissenyats per migrar — el render.yaml + Docker fan portabilitat. Si Neon canvia política (com Koyeb 2026-05-19), la migració seria self-host Postgres + Render apuntant a la nova URL. ADR-0002 documenta el pattern de pivot."

### Q5: Tests funcionen sense Docker Desktop local?
A: "No, els integration tests requereixen testcontainers que necessita Docker. Documentat com a `BLOCKED #8` al TODO — uso CI per validar fins que instal·li Docker Desktop. Decisió conscient — verification-first rule del repo diu "marcar BLOCKED no és assumir que funciona". La CI cobreix l'integration suite per a totes les PRs."

### Q6: Per què crear ADRs per a un side project?
A: "Recruiter signal + futur-jo signal. ADR-0002 (deploy pivot) m'ha estalviat ja 1h de re-recordar per què vam canviar a Render quan Roger reobre el repo en 3 mesos. Si entres a un equip que té ADRs, busques aquestes — vols demostrar que ja saps fer-les."

### Q7: Què queda per la P3+?
A: "Auth (JWT), writes (coach pot afegir box-scores), BackgroundTask per recalc averaged stats, /ideal-five flagship endpoint (window function RANK PARTITION BY position + scoring compost), full-text search amb tsvector per accents catalans, pipeline deploy on tag. Phase 4 és la "wow" feature — `/ideal-five` no existeix en cap referent català."

---

## 8. Què NO mostraria (estalvia temps)

- Migration round-trip CI logs (massa detall — només mencionar).
- 32 tasques del Phase 2 plan (massa detallat — només "GSD workflow disciplinat").
- Codigi tests detall — mencionar "245 tests verds" i passar.
- Dependabot PR history (ja resolt — manté repo polished).

## 9. Notes per Roger (oral practice)

- Practica un walkthrough de 5 minuts: problema → stack → 3 showcases (Swagger + Computed + window function) → 2 trade-offs honestos → "preguntes?".
- **Mai dir "side project" o "toy".** Sempre "production API live amb dades reals".
- Si recruiter no és tècnic profund, salta a `/docs` Swagger i deixa-li clicar — el visual venç el tècnic.
- Si recruiter és senior backend → focus a window function PARTITION BY + Computed column index. Diferenciació clara.

---

## 10. History

- 2026-05-21 v1 draft AFK overnight buffer extension — output del P2 "Aplicar 'entendre 100%' al portfolio (Apostes + TFG + Basketball)".
