# ADR-0006 — Nullable territory/group_no on competitions

**Date:** 2026-05-23
**Status:** Accepted
**Supersedes:** Schema decision in 0002_core_entities migration

## Context

Phase 2 (`0002_core_entities`) modeled `competitions.territory` and
`competitions.group_no` as `NOT NULL`, anchored on divisional examples like
`1a-territorial-m-bcn-grup-04`. Phase 2.5 ingest (`basquethero.cat`)
surfaced that FCBQ also has **nation-level competitions** with no territory
and/or no group number:

| Slug | category | gender | territory | group_no |
|---|---|---|---|---|
| `1a-territorial-m-bcn-grup-04` | 1a-territorial | M | bcn | 4 |
| `cc-2a-m-grup-01` | cc-2a | M | NULL | 1 |
| `super-copa-m` | super-copa | M | NULL | NULL |

The W3 loader (`data/seed/load_basquethero.py:_parse_competition_slug`)
correctly returns `None` for these — its docstring documents all three
shapes. The model was the missing piece.

## Decision

Make `competitions.territory` and `competitions.group_no` nullable
(migration `0004`).

Replace the plain `UniqueConstraint(category, gender, territory, group_no,
season_id, phase)` with a unique index that wraps the nullable columns in
`COALESCE`:

```sql
CREATE UNIQUE INDEX uq_competitions_natural_key ON competitions (
  category, gender,
  COALESCE(territory, ''), COALESCE(group_no, 0),
  season_id, phase
);
```

This preserves natural-key uniqueness for the NULL case, which a plain
`UniqueConstraint` would not (PostgreSQL treats `NULL != NULL`).

The loader switches from `on_conflict_do_update(index_elements=[...])` to
`on_conflict_do_update(constraint="uq_competitions_natural_key")` because
`index_elements` cannot describe an expression index.

## Consequences

**Positive.** Schema matches the FCBQ domain. The ingest pipeline no
longer needs sentinel placeholder values that would pollute leaderboards
and standings queries.

**Negative.** Queries that group or filter by `territory` must handle
`NULL` (e.g., `GROUP BY COALESCE(territory, 'national')`). API surface
must serialize `NULL` as `null` rather than skip the key — to be wired
when the relevant endpoints are touched.

**Migration safety.** `upgrade()` drops the old constraint, relaxes
`NOT NULL`, and creates the new index. Downgrade restores the old shape
and will fail if any NULLs were persisted in the meantime — acceptable
because the only way NULLs enter is via the new ingest, which would have
to be paused before downgrade in any environment with real data.
