---
project: basketball-stats-api
created: 2026-05-19
type: research-synthesis
sources:
  - .planning/research/STACK.md
  - .planning/research/FEATURES.md
  - .planning/research/ARCHITECTURE.md
  - .planning/research/PITFALLS.md
---

# Research Summary — Basketball Stats API

> Synthesis dels 4 researchers paral·lels. Llegir abans de REQUIREMENTS.md i ROADMAP.md.

## 1. Stack consolidat (versions 2026-05-19, verificades a PyPI + Context7)

| Categoria | Versió locked |
|---|---|
| Python | 3.11+ (recomanat 3.12 per typing improvements) |
| FastAPI | 0.136.1 |
| Pydantic | 2.13.4 |
| SQLAlchemy | 2.0.49 |
| Alembic | 1.18.4 |
| asyncpg | 0.31.0 (runtime) |
| psycopg | 3.3.4 (Alembic env.py sync) |
| Postgres | 16.14 (Neon serverless free tier) |
| Redis | (post-MVP, Upstash free o local) |
| pytest | 9.0.3 |
| httpx | 0.28.1 |
| testcontainers | 4.14.2 |
| ruff | 0.15.13 |
| mypy | 2.1.0 (--strict) |
| uv | 0.11.15 (package manager triat sobre poetry) |
| Auth | python-jose 3.5.0 (ADR-fallback PyJWT 2.12.1) + argon2-cffi (no bcrypt) |
| Extras | pydantic-settings, structlog, uvicorn[standard], gunicorn, python-multipart, greenlet, polyfactory |

**Ruled OUT (documentar als ADRs):** Flask, Django/DRF, psycopg2, SQLModel, pipenv, poetry, SQLite (prod/tests), Supabase, Vercel/Render/Fly, MongoDB, fastapi-users, `@on_event`, pyright, dataclasses per schemas.

## 2. Domini (insights de basquethero.cat scrape)

### Quirks del bàsquet català vs NBA (NO defaultear a NBA)

- **Stat headline = VAL (Valoración / FIBA PIR variant)**, NO PPG. Leaderboards ordenats per VAL per defecte.
- **Box-score model:** VAL, MIN, PTS, +/-, 2PM/2PA, 3PM/3PA, TL/TL%, REB (def/of separately), AST, REC (steals), TAP (blocks), PER (turnovers), FC (fouls). Plus per-quarter Q1-Q4.
- **No play-by-play, no shot chart** als referents — dades vénen del PDF acta FCBQ.
- **Competition hierarchy:** `(category, gender, territory, group, season, phase)`. Ex: `1a-territorial-m-bcn-grup-04`.
- **Categories:** Super Copa, Copa Catalunya, CC 1a/2a, 1a/3a Territorial. Territoris: bcn, gir, tar, lle.
- **Phase system:** "Fase Prèvia" → 2a fase → Playoff. Modelar com a entitat first-class.
- **Club ≠ Team:** un club pot tenir múltiples equips (sènior, sub-22, junior, etc.). Schema ha de reflectir-ho.
- **Player ID composite:** llicència + dorsal + nom (sistema federatiu). No assumir `int id`.
- **No API pública** dels referents (basquethero scrapes FCBQ); espai per la nostra API en un buit.

### Value proposition diferenciada

> *"Els números que no veus a l'acta"* — el PDF d'acta té el box-score; el value-add és **aggregation via SQL avançat**. Casa exactament amb Postgres pur showcase.

## 3. Arquitectura recomanada (estructura del codi)

```
basketball-stats-api/
├── src/basketball_stats/
│   ├── api/v1/                 # routers (HTTP only, thin <20 lines)
│   ├── schemas/                # Pydantic v2 (Create/Read/Update per entity)
│   ├── services/               # orquestració + transactions
│   ├── repositories/           # SQL/SQLAlchemy (showcases aquí)
│   ├── models/                 # SQLAlchemy 2.0 ORM
│   ├── core/                   # config, db engine, security, cache
│   └── tasks/                  # background jobs (BackgroundTasks built-in)
├── migrations/                 # Alembic
├── tests/
│   ├── unit/
│   ├── integration/            # testcontainers + Postgres real
│   └── conftest.py
├── docs/
│   ├── adr/                    # 6 ADRs mínim
│   └── STACK_WALKTHROUGH.md    # recruiter tour
├── data/seed/                  # seed amb dades reals de l'equip Roger
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml              # ruff + mypy + pytest config consolidated
├── koyeb.yaml                  # deploy config (substitueix fly.toml)
├── .github/workflows/ci.yml
├── .github/workflows/deploy.yml
├── README.md                   # secció Stack walkthrough amb anchors
└── AI_basketball-portfolio-defense.md   # chuleta tipus SST
```

### Patrons clau

- **`src/` layout** sobre flat (catches packaging bugs primer).
- **Repository + thin Service** — SQL showcases en fitxers únics, no escampats.
- **DI via `Depends()` només per:** `get_db`, `get_current_user`, `require_coach`, `get_settings`, `get_cache`. Repos/services instanciats per callers.
- **`Annotated[X, Depends(...)]`** (PEP 593), no estil antic.
- **`@asynccontextmanager` lifespan**, no `@app.on_event` (deprecated).
- **`BackgroundTasks` built-in** sobre Celery/RQ/Arq per MVP. Migrar a Arq si Phase 4 ho necessita.
- **RFC 7807 problem-details exception handlers.**

## 4. Phase sequence proposat (5 fases coarse)

1. **Foundation** — skeleton + Docker Compose (api+postgres+redis) + Alembic buit + CI (ruff+mypy+pytest minimal) + Koyeb hello-world `/healthz` + Neon Postgres link.
2. **Core entities + public read** — Team/Player/Game/BoxScore/League/Competition models, GET endpoints, **window function showcase** (standings + leaderboard ordenat per VAL), **composite index showcase** `(league_id, game_date DESC)`, testcontainers integration tests.
3. **Auth + coach writes** — OAuth2/JWT + argon2id passwords, `require_coach` Depends, POST /games + box-score upload, BackgroundTasks recompute aggregates.
4. **Differentiators** — **JSONB showcase** (play-by-play column, no obligatori MVP), **tsvector + GIN showcase** (full-text search noms jugadors/equips), Redis cache invalidation pattern, downgrade() migrations reversibles.
5. **Polish** — README amb Stack Walkthrough section + anchors, `docs/STACK_WALKTHROUGH.md`, 6 ADRs, `AI_basketball-portfolio-defense.md` tipus SST, badges CI verds, tag `v0.1.0` → deploy prod, seed amb dades reals equip Roger.

## 5. Pitfalls top 5 (a vigilar des de Phase 1)

| # | Pitfall | Mitigació | Phase |
|---|---|---|---|
| 1 | **Fly.io ja no és free** | RESOLT 2026-05-19: switch a Koyeb + Neon | — |
| 2 | **Async lazy-load `MissingGreenlet`** | `lazy="raise_on_sql"` a totes les relations + `selectinload`/`joinedload` obligatori | Phase 2 setup |
| 3 | **Postgres showcases invisibles** | Secció "SQL highlights" al README amb file:line links + 1-line "why non-trivial" per cada un | Phase 5 + revisar a cada phase |
| 4 | **Sync DB call dins async route** | Convention bake-in primer endpoint: `async def` → `await` tot I/O. Ruff lint regla `ASYNC` activada. | Phase 1 + permanent |
| 5 | **Mocked-everything tests** | testcontainers obligatori per integration tests. CI workflow té step "verify integration tests use real Postgres". | Phase 2 + permanent |

## 6. Riscos remanents post-research

- **Koyeb free tier validar limits 2026** abans de Phase 1 deploy (memory, cold-start, hores). Si massa restrictiu → Hetzner CX11 ~3€/mes com Plan B.
- **Neon free tier:** 0.5GB storage + auto-suspend tras 5min idle. Cold-start ~500ms al primer request. Acceptable per portfolio; documentar al README.
- **Catalan basketball federation data:** Roger ha de seedejar manualment des de PDFs d'acta. No hi ha source automàtic. Acceptable per portfolio (Roger ho admet), out-of-scope ingest automàtic.
