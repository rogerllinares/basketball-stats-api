# ADR-0005 — Offline Batch basquethero.cat Ingest (Replaces FCBQ STOP)

**Status:** Accepted
**Date:** 2026-05-22
**Decider:** Roger Llinares (sole maintainer)
**Scope:** Phase 2.5 — documents `D2.5-01..11` of `.planning/phases/2.5-fcbq-ingest/2.5-CONTEXT.md`. Supersedes the v1 PLAN (`2.5-PLAN-v1-archived.md`) which assumed FCBQ as the data source.

## Context

Phase 2 (Core entities + public read) shipped 2026-05-21 with `seed/minimal.py` populating fictional Catalan-named entities (license IDs 99001-99012). UAT identified **SC6 deferred**: `GET /api/v1/competitions` returns `[]` against Neon prod because the minimal seed is local-test-only and never runs as part of the deploy.

The original Phase 2.5 plan (`2.5-PLAN-v1-archived.md`) called for an offline batch CLI scraping `basquetcatala.cat` (FCBQ's official site) under 11 LOCKED architectural decisions (D2.5-01..11): two-phase fetch/parse, license_id natural key, UPSERT loader, zero new top-level deps, stdlib argparse, CI import-ban grep, ADR mandatory.

A Wave 0 discovery spike against FCBQ (commit `3b56f3f`) returned **STOP**:

- Every URL gated behind a **reCAPTCHA v3 wall** (`/security-check` redirect + HMAC-signed `fcbq_rc` cookie + POST `/recaptcha/verifica` validator).
- Box scores delivered as **JPG presigned S3 URLs** (~1h TTL), not HTML tables.
- Player-level stats behind a **third-party microservice** (`msstats.optimalwayconsulting.com`) requiring JWT RS256 short-lived tokens.
- User-Agent spoofing did not bypass any of the above.
- A captcha-solver dependency would have violated `D2.5-02` (httpx-only) and `D2.5-09` (zero new top-level deps), and a JWT-issuing flow would have required reverse-engineering a third-party producer of the token.

A second spike (AFK overnight cluster C8, commit `ee40024`) probed `basquethero.cat` — a public Next.js + RSC aggregator that mirrors FCBQ data. Findings:

- `robots.txt`: `User-Agent: * Allow: /` (107 bytes, fully permissive).
- `sitemap.xml`: 17,017 URLs, `cc-2a-m-grup-{01..06}` slugs directly addressable.
- Stack: Next.js App Router + React Server Components on Vercel.
- Data streamed via `self.__next_f.push([N, "<payload>"])` chunks (165 per calendar page, 134 decodable as JSON).
- A 130-line stdlib-only spike (`spike-basquethero/spike.py`) decoded the RSC chunks with `urllib + re + json` and reported the top dict-key frequency for parser tuning.

This ADR records the swap of data source from FCBQ to basquethero.cat and the implications for D2.5-01..D2.5-11.

## Decision

**Build the Phase 2.5 ingest CLI against `basquethero.cat` as the data source. Use stdlib only (`urllib + re + json`) for the ingest path. Keep `httpx` for the API runtime path.**

The CLI lives in `src/basketball_stats/ingest/basquethero/` with a `__main__.py` entry exposing three subcommands (per D2.5-03 two-phase fetch/parse):

- `python -m basketball_stats.ingest.basquethero fetch <slug> <season>` — writes raw HTML to `data/raw/basquethero/<slug>-<season>/` (gitignored cache, per D2.5-04).
- `python -m basketball_stats.ingest.basquethero parse <slug> <season>` — reads raw, walks RSC chunks, writes normalised `data/seed/basquethero/<slug>-<season>.json` (committed fixture, per D2.5-04).
- `python -m basketball_stats.ingest.basquethero scrape <slug> <season>` — fetch + parse end-to-end.

The loader (`data/seed/load_basquethero.py`) is a separate operational script that consumes a fixture and UPSERTs against Neon (`ON CONFLICT DO UPDATE`, per D2.5-06). The loader is invoked manually by the operator with `DATABASE_URL` pointing at Neon prod; **no FastAPI runtime path touches the loader**, enforced by a CI grep step (D2.5-10).

A CI step in `.github/workflows/ci.yml` runs **before deps install**:

```yaml
- name: Enforce offline-only ingest separation (no-live-ingest)
  run: |
    if grep -rn "from basketball_stats.ingest" src/basketball_stats/ --exclude-dir=ingest; then
      echo "::error::Production code imports from offline-only ingest package — violates LOCKED no-live-ingest (ADR-0005)"
      exit 1
    fi
```

### Delta against D2.5-01..D2.5-11

| Decision | Status | Change |
|---|---|---|
| **D2.5-01** source structure | UPDATED | `basquetcatala.cat` → `www.basquethero.cat`. URL pattern `/liga/{slug}/{calendario,equipos,jugadores}`. |
| **D2.5-02** httpx async | RELAXED | "httpx-only" → "urllib in ingest (zero deps), httpx in API runtime (existing dep)". Sync requests are sufficient — one HTTP per league suffices, RSC parsing is CPU-bound. |
| **D2.5-03** two-phase fetch/parse | HOLD | unchanged. |
| **D2.5-04** fixture per (comp,season) | HOLD | unchanged. |
| **D2.5-05** license_id PK | HOLD | unchanged. `FixturePlayer.license_id` is `int \| None`: basquethero may omit it for some players; loader SKIPs those with a structured warning rather than inventing IDs. |
| **D2.5-06** UPSERT ON CONFLICT | HOLD | unchanged. |
| **D2.5-07** first ship `cc-2a-m 2025-26` only | UPDATED | basquethero splits this competition into 6 groups (`cc-2a-m-grup-01..06`). First ship is `cc-2a-m-grup-01 2025-26`; other groups are trivial follow-up runs (UPSERT idempotent). |
| **D2.5-08** rate-limit + retry + resumable | HOLD | retry implemented as stdlib loop (`time.sleep(2**attempt + random.uniform(0,1))`) instead of `tenacity` (avoids one dep). |
| **D2.5-09** zero new top-level deps | HOLDS | parser is `urllib + re + json + recursive walker` — all stdlib. Pydantic models reused (existing dep). |
| **D2.5-10** CI import-ban + sample fixture test + idempotency double-load | HOLD | unchanged. |
| **D2.5-11** ADR mandatory with alternatives A/B/C/D | HOLD | this document. |

## Alternatives considered

### A — Pay for the FCBQ Open Data feed

Some federations expose a paid API for normalised data. Cost: unknown but likely €€€/year, and the FCBQ portal does not publicly advertise such a product. **Rejected** — the cost would dwarf a portfolio project's budget and the portfolio signal of "I bought my way out of the problem" is the opposite of what recruiters look for in a junior backend candidate. The point of the project is to show I solve the problem, not that I procure data.

### B — Playwright headed Chrome to bypass reCAPTCHA

A headed Chromium instance can execute the JS that reCAPTCHA v3 expects, capture the token, and forward it on subsequent fetches. Two killers: (1) Chromium adds **~500 MB of dependency surface** including the browser binary itself — a violation of `D2.5-09` (zero new top-level deps) of the same shape as bringing in bs4 + selectolax; (2) running a headed browser in CI requires a Display or xvfb, which the GHA runner does not provide out of the box. **Rejected** — the constraint exists for portfolio defensibility ("can this run cheaply, repeatably, on commodity infra?"), not just code hygiene.

### C — Manual CSV uploads of season stats

The operator (Roger) downloads season stats from FCBQ in CSV form (where exposed), commits the CSVs to the repo, and a one-shot loader consumes them. **Rejected** — there is no published CSV export from FCBQ at the amateur tier; the alternative is manual data entry into a spreadsheet, which is not reproducible (any error gets baked into git history) and not scalable to multiple competitions. The recruiter-visible artifact would be a directory of mystery-source CSVs, not a piece of software.

### D — Live ingest from a runtime FastAPI endpoint

Add a FastAPI route `/admin/ingest` that triggers an in-process scrape on demand. **Rejected** — violates the LOCKED `no-live-ingest` constraint (CONTEXT.md, original Phase 2 decision row). The runtime path must remain network-free against external sites to keep Neon's cold-start budget, Render's request timeout, and the OpenAPI surface clean. The async path also collides with the existing httpx client used for internal API tests.

## Consequences

- **Module naming.** The ingest module is `src/basketball_stats/ingest/basquethero/`, **not** `ingest/fcbq/`, because the data source is basquethero.cat. The planning folder remains `2.5-fcbq-ingest/` to preserve git history (the milestone was originally scoped as "FCBQ Ingest CLI"). The naming asymmetry is a fact of the rescope; the README and the CLI invocation both surface the correct name.
- **Stack defensibility.** The parser walks JSX trees inside RSC payloads — pattern matching, not key lookup. A future basquethero stack change (e.g., migration off Vercel RSC) would break the parser. Mitigation: a sample raw fixture is committed under `tests/fixtures/basquethero/raw/`, so the parser test catches structural drift in CI before it breaks production scrapes. The recovery path is "inspect raw, update the walker, re-run scrape" — a 1-2h fix for a future maintainer, not a re-architecture.
- **License-ID gaps.** basquethero does not guarantee a `license_id` for every player. The loader SKIPs players without one, with a structured stderr warning. The API will report a partial roster for those teams. Acceptable for an MVP — license-completeness is a data-source problem, not a loader problem.
- **Single-source dependency.** basquethero.cat is a third-party aggregator of FCBQ data. If basquethero shuts down or changes terms, the ingest path goes with it. Fallback: a manual CSV upload (alternative C above) can be added as a one-off escape hatch. Documented here so the future maintainer has the trail.
- **Portfolio narrative.** The README and the interview walkthrough name this ADR explicitly. The story is: "I tested the official data source, found a hard captcha wall I could not legitimately bypass, and pivoted to a public aggregator with permissive terms. The parser is stdlib-only because the dependency budget for ingest is zero." That story is the differentiator between a candidate who quits at the first wall and one who finds the second path.

## Future

- **Multi-group ingestion.** Add `--all-groups` flag to the CLI that iterates `cc-2a-m-grup-{01..06}` (or any league family). Trivial extension once W4 lands.
- **Player-level stats endpoint.** RESEARCH-V2 §9 hypothesises player stats live under `/liga/<slug>/jugadores`. Not in Phase 2.5 scope; add as Phase 4 or 5 extension if leaderboards demand richer per-player aggregations than box scores provide.
- **Standings ingestion.** Spike found no separate standings URL; standings may be embedded in the calendar RSC payload or auto-derived from games. Phase 4 task to confirm.
- **Differential update mode.** Current CLI re-scrapes the whole league each run. A future flag `--since <date>` could short-circuit fetches for completed-and-loaded games. Probably premature — at amateur scale the full re-scrape is fast.

## References

- `.planning/phases/2.5-fcbq-ingest/2.5-CONTEXT.md` — D2.5-01..D2.5-11 LOCKED decisions.
- `.planning/phases/2.5-fcbq-ingest/2.5-RESEARCH.md` — v1 FCBQ STOP report (historical).
- `.planning/phases/2.5-fcbq-ingest/2.5-RESEARCH-V2-basquethero.md` — v2 PROCEED report.
- `.planning/phases/2.5-fcbq-ingest/2.5-PLAN-v2.md` — execution plan (this ADR's tasks).
- `spike-basquethero/spike.py` — 130-line stdlib spike, kernel of the future parser.
- `ADR-0003` — VAL formula PIR FIBA (parallel "implement standard, document gap" pattern).
- `ADR-0004` — Standings tie-breaker FEB-simple (same pattern).
