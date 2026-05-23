"""basquethero.cat ingest module.

Offline batch scraper for Catalan basketball data hosted on basquethero.cat
(public Next.js + RSC aggregator of FCBQ data). Stdlib-only (urllib + re +
json) per D2.5-09. Produces JSON fixtures consumed by `data/seed/load_basquethero.py`.

See:
- `docs/adr/0005-offline-batch-basquethero-ingest.md` — architectural decision
- `.planning/phases/2.5-fcbq-ingest/2.5-PLAN-v2.md` — execution plan
- `.planning/phases/2.5-fcbq-ingest/2.5-RESEARCH-V2-basquethero.md` — source spike
"""
