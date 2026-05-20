# ADR-0003 — VAL Formula: FIBA PIR Literal + Supercopa↔Territorial Asymmetry

**Status:** Accepted
**Date:** 2026-05-20
**Decider:** Roger Llinares (sole maintainer)
**Scope:** Phase 2 — documents `D2-07`, `D2-08`, `D2-09` of `02-CONTEXT.md`.

## Context

`STAT-04` (Phase 2 requirement) and `SC3` (ROADMAP exit criterion) require the
box-score `val` column to be a **Postgres `GENERATED ALWAYS AS ... STORED`
column**, not a Python-side calculation. The query path `GET /competitions/{id}
/leaderboards?stat=val` reads `val` directly from disk and the index
`ix_box_scores_val_desc` covers it.

Two questions arise once you commit to STORED:

1. **Which VAL formula?** FIBA PIR is the standard for European basketball,
   but several Catalan stat sites publish slight variants (basquethero.cat
   uses a weighted version that emphasizes assists; FCBQ's own match acta has
   no published formula).
2. **How do we handle stats that the FCBQ Territorial acta does not record
   but the FCBQ Supercopa acta does?** Specifically `fouls_drawn` (faltes
   rebudes) and `blocks_received` (taps rebuts). PIR uses both as positive
   and negative components respectively.

The answers shape the migration (column DDL, defaults), the model
(`box_score.py` Computed expression), the seed (which fields populate), and
the interview defense (recruiter will ask "why these fields and not the
basquethero variant?").

## Decision

### Use FIBA PIR literal — no weighting variant

The formula committed to `migrations/versions/0002_core_entities.py` and
`src/basketball_stats/models/box_score.py` is:

```
val = pts + reb_of + reb_def + ast + rec + tap + fouls_drawn
      - (fg2a - fg2m) - (fg3a - fg3m) - (fta - ftm)
      - per - fc - blocks_received
```

This is the FIBA Performance Index Rating verbatim — every term has
coefficient 1 (positive or negative). No variant weighting. Reasoning:

- **Interview defense:** "Why FIBA PIR?" → "Because it is the published
  international standard. A variant would need either a formal source or a
  rationale a recruiter can verify; basquethero's variant is undocumented."
- **Portability:** Any reader who knows European basketball recognises PIR
  on sight. A variant introduces a "you have to learn our formula" step that
  has zero portfolio value.
- **Reproducibility:** PIR formula is in `02-CONTEXT.md`, this ADR, the
  migration, and the model. Four places to find the same expression.

### Handle the Supercopa↔Territorial asymmetry with `NOT NULL DEFAULT 0`

The fields `fouls_drawn` (`F.R.` on the acta) and `blocks_received` (`T.R.`)
exist in the FCBQ Supercopa acta and NOT in the Territorial acta (clarified
by Roger 2026-05-20). Two options were on the table:

| Option | Schema | Migration impact | Defense |
|--------|--------|------------------|---------|
| A — `NULL` allowed | `INT NULL` | Trivial | val expression must `COALESCE(..., 0)` for every term, formula becomes noisy |
| B — `NOT NULL DEFAULT 0` | `INT NOT NULL DEFAULT '0'` | Trivial | val expression stays clean; rows from Territorial coaches see "0" which is **truthful** (the acta literally records "did not happen / not tracked") |

Option B chosen. The seed and Territorial ingest write `0` for these fields;
the Supercopa ingest writes the real values. The VAL formula stays readable
in the migration — readers see the PIR identity without a `COALESCE`
distraction.

This means: for Territorial games, the `val` column is the **PIR lower
bound** (negative terms `blocks_received` are zeroed). For Supercopa games,
the `val` column is the exact PIR. The asymmetry is documented in this ADR
and in `box_score.py` docstring, surfaced in the README walkthrough, and
testable via a fixture pair (one Territorial row + one Supercopa row, same
player, validate that the Supercopa row's val differs by the
`fouls_drawn - blocks_received` term).

### REB as a second GENERATED COLUMN

`reb = reb_of + reb_def` is the simplest possible derivation, but recording
it explicitly as a STORED generated column was chosen for two reasons:

1. **Double showcase.** A recruiter sees that GENERATED COLUMN is used not
   only for the complex (val) case but also for the trivial (reb) case —
   the message is "derive in the database whenever the derivation is
   deterministic," not "only when it is complex."
2. **Read queries are cleaner.** `SELECT reb FROM box_scores` reads better
   than `SELECT reb_of + reb_def FROM box_scores` and survives column
   reshuffles. Every `READ-04/05/06` query path uses `reb` directly.

## Consequences

- **VAL formula is locked.** Future PRs that touch the formula must update
  this ADR, the migration, the model, and `02-CONTEXT.md` D2-07 together.
- **Territorial val rows are PIR lower bounds.** Reports and leaderboards
  derived from val show Territorial vs Supercopa as commensurate by
  default. If a future feature wants strict apples-to-apples (e.g. for an
  awards page), it must filter by competition phase or annotate.
- **No Python-side VAL helpers.** Every code path that needs val reads the
  column. The seed builds rows with raw fields; Postgres computes val
  during INSERT. Tests assert val by reading the column back, never by
  recomputing in Python (research §4 has the verbatim test).
- **The migration is the source of truth for the formula expression.** The
  `box_score.py` model mirrors it for type checking, but the database is
  authoritative — there is no risk of "model says X, DB says Y" because the
  model just declares the same Computed() expression.

## Alternatives considered

- **Python-side VAL calculation in a service layer.** Rejected: violates
  STAT-04 (which mandates SQL-side). Also adds risk of formula drift between
  writer (POST /games — P3) and reader (READ leaderboards — P2).
- **Materialized view of `player_season_averages`.** Deferred to v2 — at
  current data volume (one league, a few hundred box-scores per season) the
  window function on a STORED `val` index is fast enough. Adding a
  materialized view too early would force a refresh strategy.
- **Polymorphic schema (separate `box_scores_supercopa` table with extra
  fields).** Rejected: complicates joins, breaks the single VAL formula
  invariant, and forces every read query to branch on competition phase.
  The NULL-vs-default question is small enough to solve at the column
  level.

## References

- 02-CONTEXT.md D2-06 (schema), D2-07 (formula), D2-08 (asymmetry rule),
  D2-09 (REB second showcase).
- 02-RESEARCH.md §1 (Computed declaration, pitfalls).
- 02-PLAN.md Task 2.5.1.
- Postgres 16 docs — Generated Columns:
  <https://www.postgresql.org/docs/16/ddl-generated-columns.html>
- FIBA Eurobasket stat manual (PIR definition, public).
