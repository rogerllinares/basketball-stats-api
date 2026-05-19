# Basketball Stats API

> **Reglas globales:** ver `/CLAUDE.md` raíz del vault (Workflow Superpowers+gstack+GSD, paralelismo, hard rules, Coding Guidelines en `02 Skills/AI_coding-guidelines.md`). Este archivo cubre SOLO lo project-specific.

REST API FastAPI + Postgres pur (Neon) per al tracking de stats de bàsquet amateur/semi-pro de Roger (lliga FCBQ). Portfolio-ready per al job hunt setembre 2026 — categoria "Backend Python jr + DevOps-curious".

## Claude's Role

- Implementar tasques del PLAN.md de la fase activa amb commits atòmics.
- Defensar les 32 decisions D-XX de `01-CONTEXT.md` — si emergeix conflicte, llegir §Decision-Tree del PLAN abans de re-debatir.
- Mantenir CI verda a master. Cap merge si CI falla.
- Vigilar scope creep: si una task sembla necessitar una entitat de domini per "fer sentit" → parar i surfacejar (P2 territory).

**Prime directive:** Cada commit ha de ser defensable en una interview de 30 min.

## Project-specific rules

- **🛑 Verification-first — no avançar fins que tot estigui verificat i funcioni correctament.** Aquesta és la regla dura d'aquest projecte.
  - **Mai marcar una task com a feta sense executar la verificació explícita** (CI verda, smoke local quan aplica, badge renderitzant, endpoint responent 200, etc.).
  - **Si una verificació falla** → parar, investigar root cause (`/investigate`), arreglar, re-verificar. NO continuar amb la següent task amb el problema obert.
  - **Si la verificació no es pot executar localment** (ex: Docker Desktop missing, comptes externs no creats) → registrar com a BLOCKED explícit al handoff, NO assumir que funciona.
  - **Abans d'arrancar Path B (deploy)** o qualsevol fase nova → confirmar amb `gh run list --branch master` que l'últim run és `success`, i que no hi ha PRs oberts amb CI fallant que afectin master.
  - Raó: aquest repo és la cara que ensenyo en interviews. Un commit verd amb un bug latent és pitjor que un repo amb menys features.

- **Defensive coding amb rationale:** cada decisió no òbvia → ADR a `docs/adrs/` o D-XX al CONTEXT del fase. No deixar "magic numbers" sense comentari del WHY.

- **GSD workflow obligatori per fases:** `/gsd-discuss-phase N` → `/gsd-plan-phase N` → `/gsd-execute-phase N` → `/gsd-verify-work N`. Saltar només per fixes trivials d'≤2 archius.

## Tech Stack

- **Framework:** FastAPI (async, Python 3.12)
- **DB:** Postgres pur via Neon (free tier), asyncpg + SQLAlchemy 2.0 async
- **Migracions:** Alembic (async template)
- **Tests:** pytest + testcontainers (PostgresContainer)
- **Lint/format:** ruff + mypy --strict (pre-commit + CI)
- **Container:** Docker multi-stage + docker-compose
- **CI:** GitHub Actions (`.github/workflows/ci.yml`)
- **Deploy:** Koyeb free tier (region `fra`) + ghcr.io
- **Auth (P3+):** JWT via python-jose

## Folder Structure

```
Basketball Stats API/
├── CLAUDE.md
├── .planning/
│   ├── PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md, config.json
│   ├── phases/01-foundation/   ← CONTEXT, DISCUSSION-LOG, RESEARCH, PLAN
│   └── research/               ← SUMMARY, STACK, FEATURES, ARCHITECTURE, PITFALLS
├── src/basketball_stats/       ← api, core, models, schemas, services, repositories, tasks
├── tests/{unit,integration}/
├── alembic/
├── docs/
│   ├── adrs/                   ← ADR-0001 koyeb-neon
│   └── setup/koyeb-neon.md     ← Path B manual deploy walkthrough
├── Dockerfile, docker-compose.yml, .dockerignore
├── pyproject.toml, uv.lock, .python-version
├── .pre-commit-config.yaml, .gitleaks.toml
├── .github/workflows/ci.yml, dependabot.yml
└── README.md
```

## Skill triggers (project-specific overrides)

| Context | Skill |
|---|---|
| Abans de mergear PR (Roger o dependabot) | `/review` + verificar CI verda explícitament |
| Phase complete + tot verificat | `/gsd-verify-work` abans de `/ship` |
| CI vermella a master | `/investigate` immediat — bloqueja tot fins resolt |
| Dependabot PR amb major bump (3.12→3.14, lib major) | Avaluar manualment, no automerge |

## Estado actual

> **Last updated:** 2026-05-19
> **Status:** Phase 1 Path A **complete** + lint-clean + CI verda. 17/22 tasks fets. Repo públic https://github.com/rogerllinares/basketball-stats-api.
> **Next:** Path B (T19 Neon + T20 Koyeb + T22-finalpush live URL). Bloquejat només per creació de comptes Roger.

**Dependabot PRs oberts (status 2026-05-19 16:00):**
- PR#1 python 3.12→3.14-slim — ❌ FAIL (major Docker bump, no automerge)
- PR#2 actions/checkout v5→v6 — ✅ MERGED `60f4ad3`
- PR#3 pytest-env 1.2→1.6 — ❌ FAIL (investigar)
- PR#4 pydantic-settings 2.13→2.14.1 — ❌ FAIL (investigar)

Estat dinàmic a `TODO.md` raíz §Basketball Stats API i handoff `00 Notes/handoffs/basketball-stats-api.md`.
