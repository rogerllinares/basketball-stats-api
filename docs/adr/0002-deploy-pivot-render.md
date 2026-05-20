# ADR-0002 — Deploy Pivot: Koyeb → Render

**Status:** Accepted
**Date:** 2026-05-20
**Decider:** Roger Llinares (sole maintainer)
**Supersedes:** ADR-0001 row "Deploy" only. All other ADR-0001 decisions remain in force.

## Context

ADR-0001 (2026-05-19) selected **Koyeb free tier** as the Phase 1 deploy target,
with two explicit constraints:

1. **Zero monthly cost** during job hunt prep (no portfolio is worth burning
   monthly cash on a side project — `PROJECT.md` constraint).
2. **Anti-overlap rule** (PROJECT.md constraint #1): no Vercel / Render /
   Supabase / Next.js / React / Spring. Rationale: three portfolio projects
   (Apostes, SST, Basketball) must show three distinct stacks to recruiters.

Phase 1 Path A (codebase + CI + Dockerfile + image to GHCR) completed
2026-05-19. Path B (account creation + first deploy) was attempted
2026-05-20 and surfaced two new facts that invalidate the ADR-0001 deploy
choice:

- **Koyeb removed its free tier.** Acquisition by Mistral AI (flagged as risk
  R2 in `.planning/phases/01-foundation/RESEARCH.md`) materialized. New signups
  see a hard paywall: $30/month Pro plan minimum to deploy any service.
  Verified via signup flow screenshot 2026-05-20 10:38 CET.
- **Fly.io requires a credit card** at signup (post-Oct-2024 anti-abuse policy).
  Hobby tier still exists ($5/mo free allowance), but CC entry is mandatory.
  Verified via signup flow screenshot 2026-05-20 10:41 CET.

The zero-monthly-cost constraint is a **hard** constraint for this project (it
is a portfolio piece, not revenue-generating). The anti-overlap rule was a
**soft** constraint (a nice-to-have portfolio-variety signal).

When two constraints conflict and one is hard while the other is soft, the
hard one wins. Hence the anti-overlap rule must yield for the Deploy row.

## Decision

**Pivot Phase 1 deploy from Koyeb to Render** (free Docker web service,
`frankfurt` region). All other stack choices unchanged.

Alternatives evaluated and rejected:

| Option | Anti-overlap | Zero CC | Docker | Rejected because |
|---|---|---|---|---|
| Render free Docker web service | ❌ overlaps SST | ✅ | ✅ | **CHOSEN.** Mitigated by: different DB (Neon vs SST's Postgres), different framework (FastAPI vs SST's), different deploy mode (Docker vs SST's buildpack). |
| Railway | ✅ | ❌ (CC required) | ✅ | Same CC blocker as Fly. |
| Cloud Run (GCP) | ✅ | ❌ (CC for activation) | ✅ | Same CC blocker. |
| PythonAnywhere free | ✅ | ✅ | ❌ (PaaS Python-native, no Docker) | Loses Docker signal; rewriting Dockerfile→requirements.txt loses prior work. |
| VPS Hetzner (~€4.5/mo) | ✅ | CC + bank transfer | ✅ | Violates zero-monthly-cost hard constraint. |
| Self-host (Cloudflare Tunnel from home) | ✅ | ✅ | ✅ | Dynamic IP, downtime risk, no SLA-quality URL for recruiters. Not portfolio-defensible. |

## Consequences

- **Anti-overlap signal weakens** at the portfolio level: two of three projects
  (SST + Basketball) live on Render. Mitigation captured in the table above —
  the rest of the stack divergence (DB, framework, deploy mode) is the
  recruiter-visible variety story.
- **Cold-start mitigation needed.** Render free sleeps services after 15 min
  idle (Koyeb free did not). Mitigation: GHA cron `*/14 * * * *` hits
  `/healthz` to keep the service warm. 750 free instance-hours/month covers
  24/7 uptime. See `.github/workflows/warm-ping.yml`.
- **No CLI-first `koyeb app init` flow.** Render's bootstrap requires one
  dashboard click (connect GitHub repo). Subsequent updates are IaC via
  `render.yaml` at repo root. Net loss: ~1 manual click. Net win: IaC visible
  in repo (recruiter signal: Infrastructure-as-Code).
- **`docs/setup/koyeb-neon.md` is superseded** but retained as historical
  context. A `SUPERSEDED` banner at the top points to `render-neon.md` and to
  this ADR. Audit trail preserved.
- **Phase 1 plan tasks T19 and T20** (Neon project create + Koyeb app init)
  collapse into a single Render dashboard step + `render.yaml` IaC commit. PLAN
  remains accurate at the conceptual level (provision DB → provision deploy
  target → wire secrets → push image → verify health). Task IDs unchanged in
  PLAN.md for audit consistency; their execution path swaps Koyeb→Render.
- **R2 risk realized.** RESEARCH.md flagged "Koyeb being acquired by Mistral
  AI" as a flag, not an action. This ADR closes that risk loop: the pivot
  this ADR documents *is* the action.

## References

- `docs/adr/0001-stack-election.md` — original Deploy row (now superseded by
  this ADR; the rest stands).
- `docs/setup/render-neon.md` — new operational walkthrough.
- `docs/setup/koyeb-neon.md` — superseded; banner points here.
- `render.yaml` — IaC for the Render service.
- `.github/workflows/warm-ping.yml` — cold-start mitigation.
- `.planning/phases/01-foundation/RESEARCH.md` §R2 — Koyeb acquisition risk
  that materialized.
- `.planning/PROJECT.md` constraint #1 — anti-overlap rule (now relaxed for
  Deploy only).
