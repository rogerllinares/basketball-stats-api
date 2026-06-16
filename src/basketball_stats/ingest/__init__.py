"""Offline-only ingest package.

NEVER imported from API runtime (`src/basketball_stats/api`, `services`,
`repositories`, `tasks`). The constraint is enforced by a CI grep step
(see `.github/workflows/ci.yml` — "Enforce offline-only ingest separation").

See `docs/adr/0005-offline-batch-basquethero-ingest.md` for the architectural
rationale (LOCKED no-live-ingest, Phase 2.5 v2 — basquethero.cat).
"""
