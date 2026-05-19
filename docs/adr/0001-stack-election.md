# ADR-0001 — Stack Election

**Status:** Accepted
**Date:** 2026-05-19
**Decider:** Roger Llinares (sole maintainer)

## Context

Greenfield REST API for FCBQ amateur basketball statistics, deployed solo, time-boxed
to ~15 days of focused work. Two hard constraints from `PROJECT.md`:

1. **Anti-overlap rule.** No Vercel / Render / Supabase / Next.js / React / Spring
   (overlaps with active projects: Apostes Automatitzades and SST).
2. **Recruiter-defensible day 1.** Every tool choice must survive a 30-min interview;
   the project is a portfolio piece for the September 2026 job hunt.

## Decision

| Concern | Choice | Alternatives rejected |
|---|---|---|
| Language | Python 3.12 | 3.13 (too new for some libs); 3.11 (out-of-the-box LTS but missing 3.12 type improvements). |
| Web framework | **FastAPI 0.136** | Flask (no async-first); Django (orthogonal to API-only need); Litestar (smaller ecosystem signal). |
| ORM | **SQLAlchemy 2.0 async + asyncpg** | SQLModel (couples ORM + schema; less recruiter signal); Tortoise (smaller community); raw asyncpg (loses migrations + repository patterns). |
| Validation | **Pydantic v2.13** | Marshmallow (legacy); attrs (no schema gen). |
| Migrations | **Alembic 1.18** (async cookbook template) | Custom migration tool; Django-style auto-migrations (not FastAPI-native). |
| DB | **Postgres 16 (Neon free tier, EU)** | SQLite (no window functions in prod-grade demos); MySQL (worse JSON + window-function ergonomics); Supabase (anti-overlap with Apostes); Render Postgres (anti-overlap with SST). |
| Deploy | **Koyeb (free tier, `fra`)** | Fly.io (free tier ended 2025); Render (anti-overlap); Heroku (paid only); plain VPS (anti-recruiter-signal: too much sysadmin, too little app focus). |
| Package mgmt | **uv 0.11.15** + lockfile committed | pip-tools (slower, no editable installs); poetry (slower resolver, weaker reproducibility story in 2026); pipx (tooling only, not app). |
| Test infra | **testcontainers-python** + Postgres 16-alpine | Mocking with SQLAlchemy mock_engine (covers nothing real); SQLite-in-memory (no window functions, no GENERATED COLUMNS); shared dev DB (race-y in CI). |
| Logging | **structlog 25 + tty-detected JSON/console** | stdlib logging (no contextvars binding); loguru (less recruiter signal); OpenTelemetry full stack (scope creep for MVP — `request_id` middleware is the pre-otel bridge per D-20). |
| Container | **Multi-stage `python:3.12-slim` + uv** | Distroless (debugging cost); alpine (musl libc + asyncpg drama); plain Debian (bloat). |
| CI | **GitHub Actions, single job, no matrix** | CircleCI / GitLab CI (less embedded in recruiter eyeballs); matrix Python versions (single-prod-version = overkill for solo). |

## Consequences

- The codebase is **explicitly demonstrative** of the chosen stack: every tool has a
  visible "why" in code comments and ADRs (per the recruiter-defense rule). Future
  phases (Phase 5) compile this into a stack walkthrough document.
- **No frontend.** The deliverable is API + `/docs` (OpenAPI). A separate
  `basketball-stats-web` repo could live some day; out of scope for v0.1.
- **No Redis at MVP.** Removed during post-review on 2026-05-19 (dead-weight pattern —
  no endpoint used it). Will be re-added in v2 only when a real caching use case
  emerges. Background recompute uses FastAPI `BackgroundTasks` (Phase 3, AUTH-05).
- **Single deploy region.** Koyeb `fra` for proximity to Catalonia. Multi-region is v2.
- **Manual deploy in Phase 1, automation in Phase 4.** This sequence proves the
  pipeline manually (visible in `docs/setup/koyeb-neon.md`) before tag-driven
  automation (`INFRA-04`) layers on top — debuggable failure modes by design.

## References

- `.planning/PROJECT.md` — LOCKED stack decisions and project-level success criteria.
- `.planning/research/STACK.md` — PyPI version pin verification, alternatives ruled out.
- `.planning/research/ARCHITECTURE.md` — `src/basketball_stats/` layout + Repository/Service patterns.
- `.planning/research/PITFALLS.md` — Top 10 pitfalls; the choices above explicitly avoid the docker, async, and CI traps surfaced there.
- `docs/setup/koyeb-neon.md` — operationalizes the deploy decision.
