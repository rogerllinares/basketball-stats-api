---
project: basketball-stats-api
created: 2026-05-19
updated: 2026-05-19
status: initializing
owner: Roger Llinares
---

# Basketball Stats API

## What This Is

REST API per al tracking de stats de bàsquet amateur/semi-pro: equips, jugadors, partits, box scores, standings i leaderboards. **API-only** (no UI dins aquest repo). Dades reals de l'equip i lliga de Roger (jugador semi-pro). Pensat com a **peça de portfolio per al job hunt setembre 2026**, diferenciador clar respecte els altres projectes:

| Projecte previ | Stack | Què cobreix |
|---|---|---|
| Apostes Automatitzades | Next.js 16 + Supabase + Tailwind + Vercel | Full-stack jr TS/React + auth multi-tenant |
| Sustainable Spending Tracker | React/Vite + Spring Boot + Render + Vercel | Full-stack jr Java/Spring + frontend React |
| TFG QBot Platform | C + QNX RTOS + POSIX threads + LIDAR | Embedded jr (defense/automotive/robotics) |
| **Basketball Stats API (aquest)** | **FastAPI + Postgres pur + Docker + GHA + Koyeb + Neon** | **Backend Python jr + DevOps bàsic** |

## Core Value

> **Un únic API REST production-grade que demostra al recruiter: SQL avançat en Postgres pur, FastAPI async + Pydantic v2 + SQLAlchemy 2.0, CI/CD complet i Docker, en un domini personal i defensable a l'entrevista (la lliga real de Roger).**

Si aquest punt cau, la peça no serveix per al job hunt.

## Context

- **Owner:** Roger Llinares (estudiant EE UPC, intern E.G.O. Appliances fins 2026-06-28, jugador semi-pro de bàsquet).
- **Motivació:** Cobrir la categoria d'ofertes "Backend Python jr" + "Full-stack Python jr" + "DevOps-curious jr" que actualment NO té representada al portfolio. Maximitzar ofertes aplicables a BCN/remote sense superposar-se amb cap altre projecte.
- **Hook d'entrevista:** "Vaig construir-ho per al meu equip — l'usem cada setmana, tinc dades reals, aquí tens el playground." Domini personal → defensa creïble.
- **Inspiració de domini:** `www.basquethero.cat` — referent de tracking de bàsquet català amateur. El researcher fa scrape per extreure entitats/stats/UX característica del bàsquet local (NO copiar 1:1).
- **Ubicació codi:** `C:\Users\llina\Desktop\SecondBrain\03 Projects\Otros Proyectos\Basketball Stats API\` (gitignored al vault, git propi dins el dir, mateix patró que LinkedIn Job Hunt).
- **Deadline soft:** MVP cabable en 1-2 setmanes amb disciplina GSD. Bloqueja el pitch del job hunt 2026-09 si no es tanca.

## Stack (LOCKED — decidit per Roger 2026-05-19, no re-debatir sense aprovació explícita)

| Capa | Tecnologia | Per què aquesta |
|---|---|---|
| Lang | **Python 3.11+** | Roger ja l'usa intermig (LinkedIn CLI). Categoria d'ofertes més gran. |
| Web framework | **FastAPI** | Framework Python jr més modern + demandat 2026. OpenAPI auto-doc → recruiters obren `/docs` i veuen tot. |
| Validation | **Pydantic v2** | Idiomàtic FastAPI. Demostra type-safety i schema-first. |
| ORM | **SQLAlchemy 2.0 async** | Estàndard de facto Python. La sintaxi 2.0 + async = punt fort. |
| DB | **Postgres 16 PUR via Neon free tier** (no Supabase) | Diferenciador clar vs Apostes. SQL directe + migracions. Neon = Postgres serverless gratis. |
| Migracions | **Alembic** | Estàndard SQLAlchemy. |
| Auth | **OAuth2 + JWT** (FastAPI Security) | Coaches escriuen, públic llegeix. Showcase patró. |
| Cache | **Redis** *(post-MVP, v2 — NO inclòs al MVP)* | Carried out 2026-05-19 post-review: cap endpoint MVP l'usava, dead-weight pattern evitat. Re-introduir només quan hi hagi cas d'ús real de cache invalidation. |
| Tests | **pytest + httpx + testcontainers (Postgres real)** | testcontainers = tests d'integració amb DB real, no mocks. Punt diferencial. |
| Linting | **ruff** + **mypy --strict** | Estricte = senyal de qualitat. |
| Infra local | **Docker Compose** (api + postgres) | Hands-on Docker visible al README. Redis fora del MVP (v2). |
| CI/CD | **GitHub Actions** | Estàndard. Pipeline complet: ruff + mypy + pytest + build image + deploy on tag. |
| Deploy (web) | **Koyeb nano free tier** | NO repetir Vercel (SST/Apostes) ni Render (SST). Fly.io ja no té free tier (Oct 2024), Koyeb és l'alternativa free 2026. |
| Deploy (DB) | **Neon Postgres free tier** | Postgres serverless gratis. Connection pooling inclòs. Separat del web host = arquitectura realista. |
| OpenAPI | Built-in FastAPI | `/docs` accessible públicament en prod. |

**Showcases obligats de Postgres** (han d'aparèixer al codi/migracions, no només dir-ho):
1. **Window functions** — `RANK() OVER (PARTITION BY league_id ORDER BY ppg DESC)` per leaderboards.
2. **JSONB** — play-by-play d'un partit.
3. **Indexes compostos** — `(game_date DESC, league_id)` per queries de standings.
4. **Full-text search** — `tsvector` sobre noms de jugadors/equips.
5. **Migration history clean** — totes les migracions reversibles (`downgrade()` implementades).

## Requirements

### Validated

(None yet — ship to validate)

### Active (hypothesis until shipped)

> Refinarem amb el researcher i el scrape de basquethero.cat. Següent gate: REQUIREMENTS.md.

- [ ] [REQ-PUBLIC] Endpoint públic per consultar standings d'una lliga.
- [ ] [REQ-PUBLIC] Endpoint públic per consultar leaderboards filtrats per stat (PPG, RPG, APG, etc.).
- [ ] [REQ-PUBLIC] Endpoint públic per consultar el detall d'un partit (box-score + play-by-play).
- [ ] [REQ-PUBLIC] Endpoint públic per consultar el perfil d'un jugador (stats totals + per partit).
- [ ] [REQ-AUTH] Coaches autenticats poden pujar el box-score d'un partit.
- [ ] [REQ-AUTH] Coaches autenticats poden corregir un box-score ja pujat.
- [ ] [REQ-INFRA] Docker Compose engega api + postgres amb `docker compose up`. (Redis fora del MVP — v2.)
- [ ] [REQ-INFRA] GitHub Actions executa lint + types + tests a cada push i deploy on tag.
- [ ] [REQ-DOCS] README té secció "Stack walkthrough" amb per què s'ha triat cada eina i què demostra.
- [ ] [REQ-DOCS] `docs/adr/` conté ADRs per cada decisió no-òbvia (auth method, sync vs async ingest, cache invalidation strategy).
- [ ] [REQ-DOCS] `AI_basketball-portfolio-defense.md` (al root del projecte) tipus SST: stack + arquitectura + trade-offs + 7 Q&A típiques d'entrevista.
- [ ] [REQ-OBS] OpenAPI accessible a `/docs` en prod amb totes les rutes documentades + exemples.

### Out of Scope (explicit — no fer)

- **UI web/mobile dins aquest repo.** Si Roger vol un dashboard després → repo separat (`basketball-stats-web`), aquest projecte resta API-only.
- **Live ingest des de scoreboard físic / API externa de partits.** Ingest només via POST manual de coaches.
- **Multi-tenant SaaS.** Single-league/team focus. Multi-lliga només si surt natural de l'schema, no com a feature dedicada.
- **Cap servei sobre Vercel/Render/Supabase.** Bloquejat per regla anti-overlap amb SST/Apostes.
- **Redis al MVP.** Defer a v2 quan emergeixi cas d'ús real de cache invalidation. `docker-compose` del MVP només té `api + postgres`.
- **Realtime WebSockets per al MVP.** Deferred a post-MVP si Redis ja hi és (v2).
- **Mobile push notifications.** Out of scope total per a aquest projecte.
- **Funcionalitat d'estadístiques avançades tipus "advanced metrics NBA"** (PER, TS%, BPM). MVP = stats bàsiques (PTS/REB/AST/STL/BLK/TOV/MIN). Avançades en milestone v2.

## Key Decisions

| Decisió | Rationale | Outcome |
|---|---|---|
| FastAPI + Postgres pur + Docker + GHA + Fly.io stack | Cobrir backend Python jr + DevOps; zero overlap amb portfolio existent | LOCKED 2026-05-19 |
| Domini basketball stats (no finances personals, no SST-clone) | Domini personal de Roger (semi-pro) → defensa única d'entrevista | LOCKED 2026-05-19 |
| API-only en aquest repo | Mantenir scope cabable 1-2 setmanes; UI seria un repo separat | LOCKED 2026-05-19 |
| Documentació visible de cada eina (README + ADRs + defense doc) | Requisit explícit Roger: "que es vegi tot l'ús d'eines" | LOCKED 2026-05-19 |
| Inspiració basquethero.cat (no còpia) | Referent català amateur; ajusta l'scope al bàsquet local realista | Pendent — researcher fa scrape |
| Postgres pur vs Supabase | Diferenciador vs Apostes; permet showcase SQL directe | LOCKED 2026-05-19 |
| Koyeb + Neon vs Fly.io vs Vercel/Render | Fly.io perdé free tier Oct 2024 (descobert pel researcher PITFALLS). Koyeb manté free + Neon Postgres free = $0 prod respectant el constraint. Render exclós per regla anti-overlap SST. | LOCKED 2026-05-19 (after research) |
| Redis OUT del MVP | Cap endpoint MVP l'usava (`POST /games` recompute via BackgroundTask sense cache layer). Evitar dead-weight pattern — recruiter preguntaria "per què està això?" sense resposta. Re-introduir només a v2 amb cas d'ús real. | LOCKED 2026-05-19 post-review |
| testcontainers (Postgres real) vs mocks | Tests d'integració realistes; diferencial de qualitat | Pendent — confirmar al researcher PITFALLS |

## Success Criteria (project-level, no de phase)

El projecte queda "Portfolio-ready" (estat tipus SST) quan totes aquestes són ✅:

1. **Tests verds** — `ruff` + `mypy --strict` + `pytest` tots passen en CI a la branca `main`.
2. **Production deploy verificat** — `GET /docs` accessible des de una URL pública (Koyeb), retorna OpenAPI complet amb totes les rutes documentades.
3. **Hi ha dades reals seedejades** — almenys una lliga + dos equips + un partit amb box-score real de l'equip de Roger.
4. **README té secció "Stack walkthrough"** — cada eina amb per què, on s'usa, què demostra al recruiter.
5. **`docs/adr/` té mínim 6 ADRs** cobrint: stack election, auth method, sync vs background ingest, cache strategy (Redis-drop), deploy target switch a Koyeb, repository pattern.
6. **`AI_basketball-portfolio-defense.md` escrit** — stack + arquitectura + 7 Q&A típiques tipus SST.
7. **GitHub repo públic** — README pro, badges CI verds, link al deploy.
8. **Roger pot defensar-ho 30 min en una entrevista** — passa el walkthrough oral amb Claude (gate pre-entrevista, tipus SST).

## Constraints

- **Time-budget:** MVP en 1-2 setmanes amb GSD disciplinat. Si superem 3 setmanes → reescopejar.
- **Cost-budget:** $0 prod (Koyeb free tier + Neon Postgres free tier). Cap línia que requereixi targeta.
- **No overlap amb SST/Apostes:** Si una decisió emergent toca Vercel/Render/Supabase/React/Tailwind/Next.js/Spring → bloquejar i triar alternativa.
- **Hard rules del vault** (CLAUDE.md raïz): tests sempre, plantilla universal de docs, AI_ prefix només a docs que crea Claude.

## Evolution

Aquest document evoluciona a cada phase-transition i milestone:

**Després de cada phase transition** (via `/gsd-transition`):
1. Requirements invalidats? → Out of Scope amb raó.
2. Requirements validats? → Validated amb referència de fase.
3. Nous requirements? → Active.
4. Decisions noves? → Key Decisions.

**Després de cada milestone** (via `/gsd-complete-milestone`):
1. Review complet de totes les seccions.
2. Core Value check — segueix sent la prioritat?
3. Audit Out of Scope — raons encara vàlides?

---

*Last updated: 2026-05-19 after initialization (pre-research, pre-roadmap).*
