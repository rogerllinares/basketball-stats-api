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

**Phase:** 2.5 (fcbq-ingest — PLAN ready 2026-05-21)
**Plan:** `.planning/phases/2.5-fcbq-ingest/2.5-PLAN.md` — 6 waves, 19 tasks, 7-8h estimated
**Status:** Phase 2.5 PLAN.md committed. Wave 0 = FCBQ source discovery spike (BLOCKING GATE — STOP rule if Playwright needed). Waves 1-3 build foundation + loader against sample-mini fixture BEFORE scraping. Waves 4-5 scrape real cc-2a-m 2025-26 + load Neon prod (closes P2 SC6). Wave 6 verify + ship. Each task = 1 GitHub Issue per project rule. Next: `/gsd-execute-phase 2.5` (or manual Wave 0 spike first if executor wants live evidence).
**Progress:** `[################################........] 2/6 phases` (P1+P2 SHIPPED, P2.5 inserted)

## Roadmap Snapshot

| # | Phase | REQs | Status |
|---|---|---|---|
| 1 | Foundation | 8 | ✅ SHIPPED 2026-05-20 (live https://basketball-stats-api-banq.onrender.com) |
| 2 | Core entities + public read | 23 | ✅ SHIPPED 2026-05-21 (master `4c107bc`, PR #13). UAT: 6/7 SC PASS, SC6 DEFERRED a P2.5. |
| 2.5 | FCBQ Ingest CLI | TBD | PLAN ready 2026-05-21 (6 waves, 19 tasks) — awaiting `/gsd-execute-phase 2.5` |
| 3 | Auth + coach writes | 6 | Not started |
| 4 | Differentiators + deploy automation | 3 | Not started |
| 5 | Polish (docs-only) | 3 | Not started |

## Recent Activity

- 2026-05-19 — Project initialized after SST closure. Stack + domain locked. Research spawned (4 parallel agents).
- 2026-05-19 — Research synthesis written to `.planning/research/SUMMARY.md`.
- 2026-05-19 — REQUIREMENTS.md drafted with 40 v1 REQ-IDs across 7 categories.
- 2026-05-19 — ROADMAP.md drafted with 5 phases coarse, 100% requirement coverage validated, traceability matrix written back to REQUIREMENTS.md.
- 2026-05-19 — Roadmap revised post-review (Claude critique + Roger approval): Redis dropped from MVP, `/matchday/ideal-five` promoted from v2 to Phase 4 flagship, seed-minimal + OpenAPI examples moved P5→P2. Total v1 REQs: 40→43. Coverage 43/43 mantingut.
- 2026-05-20 — Phase 1 SHIPPED. Pivot Koyeb→Render (ADR-0002). Live URL https://basketball-stats-api-banq.onrender.com.
- 2026-05-20 — Phase 2 CONTEXT.md gathered. 20 D2-decisions captures. Phase 2.5 FCBQ Ingest CLI deferred (insertable post-P2). Async sub-decisions: Player PK híbrid, normalització UPPER+sense-accents, Team permanent+Roster M:N, VAL=PIR FIBA literal STORED, default 0 per fouls_drawn/blocks_received + ADR-0003 asimetria, REB=2n GENERATED column, standings simple FEB-style + ADR-0004 gap normatiu, leaderboards window functions on-the-fly, pagination offset/limit, seed fictius català, schemas Create/Update drafts a P2 (writes a P3).
- 2026-05-21 — Phase 2 SHIPPED (master `4c107bc`, PR #13 squash+delete, 49 fitxers +3423 -9). Live URL preservat.
- 2026-05-21 — `/gsd-verify-work 2` complete. UAT escrit a `.planning/phases/02-core-entities/02-UAT.md`. 6/7 SC PASS. SC6 `GET /competitions=[]` en prod (Neon sense seed). Roger decideix DEFER a Phase 2.5.
- 2026-05-21 — Phase 2.5 INSERTED post Phase 2. Goal: CLI Python offline batch FCBQ scrape → JSON fixtures versionats + loader. Substitueix seed minimal fictici per dades reals catalanes (2a Catalana → Supercopa M+F). Preserva LOCKED no-live-ingest constraint.
- 2026-05-21 — Phase 2.5 CONTEXT.md gathered + DISCUSSION-LOG.md written. 11 D2.5-decisions LOCKED. Roger interrupted mid-discussion to delegate technical detail ("decideix tu però raonant-ho per interview prep") → Claude decidit amb justificació densa + ADR-0005 a generar a planning. Decisions: D2.5-01 researcher spike pre-planning (FCBQ source unknown), D2.5-02 httpx async, D2.5-03 two-phase fetch/parse + raw cache gitignored, D2.5-04 1 fixture per (comp,season) nested, D2.5-05 Player PK = license_id, D2.5-06 UPSERT ON CONFLICT, D2.5-07 first ship cc-2a-m 2025-26 only, D2.5-08 1 req/s + tenacity + UA rotation + resumable state, D2.5-09 module ingest/fcbq + argparse stdlib + 0 new deps, D2.5-10 CI import-ban grep + sample fixture test + idempotency, D2.5-11 ADR-0005 obligatori amb alternatives A/B/C/D.
- 2026-05-21 — Phase 2.5 PLAN.md written. 6 waves, 19 tasks, 7-8h estimated. W0 spike BLOCKING GATE (STOP if Playwright needed). W1 foundation (skeleton + ADR-0005 + CI import-ban + .gitignore). W2 Pydantic fixture models + sample-mini.json. W3 loader UPSERT + idempotency double-load test (loader proven against sample BEFORE scraping). W4 client + state + parser + CLI. W5 real cc-2a-m 2025-26 scrape + Neon prod load → CLOSES P2 SC6. W6 verify + ship + handoff. Decision tree + risk register inline. Each task = 1 GitHub Issue per project rule. Next: `/gsd-execute-phase 2.5`.

### Roadmap Evolution

- Phase 2.5 (INSERTED 2026-05-21, URGENT post-P2-UAT) — FCBQ Ingest CLI per resoldre SC6 gap (DB Neon prod buida). Substitueix seed minimal fictici per dades reals catalanes via offline batch scrape FCBQ. Preserva LOCKED no-live-ingest. Inserted after Phase 2.

## Next Action

`/gsd-discuss-phase 2.5` per gather context i decisions de Phase 2.5 (FCBQ Ingest CLI).

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
