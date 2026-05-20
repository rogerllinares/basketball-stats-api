---
gsd_state_version: 1.0
milestone: v0.1.0
milestone_name: milestone
status: Roadmap draft generated, awaiting Roger approval
last_updated: "2026-05-19T12:24:44.378Z"
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# STATE — Basketball Stats API

## Current Status

**Stage:** ROADMAP_DRAFT (awaiting Roger approval before `/gsd-discuss-phase 1`)

| Step | Status | Notes |
|---|---|---|
| 1. Setup (dir + git + .gitignore + planning dirs) | Done | git init in project, gitignored from vault |
| 2. PROJECT.md | Done | Stack locked per Roger 2026-05-19 |
| 3. config.json | Done | Coarse granularity, parallel, balanced models, research+check+verify ON |
| 4. Research (4 parallel agents) | Done | Synthesis a `.planning/research/SUMMARY.md` |
| 5. REQUIREMENTS.md | Done | 40 v1 REQ-IDs agrupats DOM/READ/AUTH/STAT/INFRA/OBS/TEST |
| 6. ROADMAP.md | Done | 5 phases coarse, 100% coverage (40/40), awaiting Roger approval |
| 7. Approval gate | Pending | Final step before `/gsd-discuss-phase 1` |

## Current Position

**Phase:** 2 (core-entities — context gathered, ready for planning)
**Plan:** none
**Status:** Phase 2 CONTEXT.md written; next is `/gsd-plan-phase 2`
**Progress:** `[########################................] 1/5 phases` (P1 SHIPPED 2026-05-20)

## Roadmap Snapshot

| # | Phase | REQs | Status |
|---|---|---|---|
| 1 | Foundation | 8 | ✅ SHIPPED 2026-05-20 (live https://basketball-stats-api-banq.onrender.com) |
| 2 | Core entities + public read | 23 | Context gathered 2026-05-20 — ready for plan |
| 3 | Auth + coach writes | 6 | Not started |
| 4 | Differentiators + deploy automation | 3 | Not started |
| 5 | Polish (docs-only) | 3 | Not started |

Insertable phase (post-P2-ship): **2.5 FCBQ Ingest CLI** — decidit 2026-05-20 durant `/gsd-discuss-phase 2`. Create via `/gsd-insert-phase`.

## Recent Activity

- 2026-05-19 — Project initialized after SST closure. Stack + domain locked. Research spawned (4 parallel agents).
- 2026-05-19 — Research synthesis written to `.planning/research/SUMMARY.md`.
- 2026-05-19 — REQUIREMENTS.md drafted with 40 v1 REQ-IDs across 7 categories.
- 2026-05-19 — ROADMAP.md drafted with 5 phases coarse, 100% requirement coverage validated, traceability matrix written back to REQUIREMENTS.md.
- 2026-05-19 — Roadmap revised post-review (Claude critique + Roger approval): Redis dropped from MVP, `/matchday/ideal-five` promoted from v2 to Phase 4 flagship, seed-minimal + OpenAPI examples moved P5→P2. Total v1 REQs: 40→43. Coverage 43/43 mantingut.
- 2026-05-20 — Phase 1 SHIPPED. Pivot Koyeb→Render (ADR-0002). Live URL https://basketball-stats-api-banq.onrender.com.
- 2026-05-20 — Phase 2 CONTEXT.md gathered. 20 D2-decisions captures. Phase 2.5 FCBQ Ingest CLI deferred (insertable post-P2). Async sub-decisions: Player PK híbrid, normalització UPPER+sense-accents, Team permanent+Roster M:N, VAL=PIR FIBA literal STORED, default 0 per fouls_drawn/blocks_received + ADR-0003 asimetria, REB=2n GENERATED column, standings simple FEB-style + ADR-0004 gap normatiu, leaderboards window functions on-the-fly, pagination offset/limit, seed fictius català, schemas Create/Update drafts a P2 (writes a P3).

## Next Action

`/gsd-plan-phase 2` per crear PLAN.md de Phase 2 amb tasks atòmiques.

## Accumulated Context

### Key decisions (mirror PROJECT.md §Key Decisions)

- Stack FastAPI + Postgres pur + Docker + GHA + Koyeb + Neon LOCKED 2026-05-19.
- Domini bàsquet català FCBQ (no NBA defaults).
- 43 v1 REQ-IDs post-review (original 40 + READ-09 + OBS-08 + INFRA-06).
- **Redis OUT del MVP 2026-05-19** (dead-weight pattern evitat; re-introduir només a v2 amb cas d'ús real).
- **`/matchday/ideal-five` PROMOTED de v2 a Phase 4 flagship 2026-05-19** (window function RANK PARTITION BY posició + composite scoring — diferenciador real que cap referent català ofereix).
- **Seed minimal + OpenAPI examples movits de P5 a P2 2026-05-19** (sense ells P2 retorna `[]` i `/docs` es veu amateur).

### Open todos

- (none pre-approval)

### Blockers

- (none — awaiting approval gate)

## Decision Log

Veure `PROJECT.md §Key Decisions` + `ROADMAP.md §Notes` per justificació d'ordre de phases.

## Session Continuity

Last session: 2026-05-19T12:24:44.366Z
