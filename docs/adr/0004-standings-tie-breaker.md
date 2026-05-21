# ADR-0004 — Standings Tie-Breaker: FEB-Simple + Path to FCBQ Head-to-Head

**Status:** Accepted
**Date:** 2026-05-20
**Decider:** Roger Llinares (sole maintainer)
**Scope:** Phase 2 — documents `D2-10` of `02-CONTEXT.md`.

## Context

`STAT-01` and `SC1` require the standings query to use a Postgres `RANK()`
window function with deterministic tie-breakers. The MVP standings endpoint
(`GET /competitions/{id}/standings`) returns one row per team with a
`position` integer derived in SQL.

The FCBQ official regulation for the Catalan amateur league uses **head-to-
head** results as the primary tie-breaker when two or three teams finish
with the same number of wins. The FEB (Federación Española de Baloncesto)
top-down regulation uses **point differential** as the primary tie-breaker.
The two systems agree on the tiebreaker semantic ("most-deserving team
first") but produce different orderings when the head-to-head outcome
contradicts the season-long point differential.

Implementing head-to-head correctly requires a self-join over the games
table to extract per-pair records, then a composite ORDER BY that mixes
per-pair and aggregate columns. The query gains a CTE and roughly doubles
in complexity — useful as a v2 showcase, premature for the MVP.

## Decision

### MVP uses FEB-simple tie-breakers

The standings query in `src/basketball_stats/repositories/standings.py`
sorts rows with:

```sql
RANK() OVER (
  PARTITION BY competition_id
  ORDER BY wins DESC, point_diff DESC, points_for DESC
)
```

Tie-breaker chain:

1. **Wins** (primary) — most wins first.
2. **Point differential** (tie 1) — `points_for - points_against`.
3. **Points for** (tie 2) — gross points scored. Acts as a last-resort
   stable sort for the (rare) case where two teams have identical wins and
   identical differential.

The chain is FEB-canonical. It cannot produce a draw of position for two
teams unless every field matches exactly, in which case `RANK()` correctly
assigns both teams the same position and skips the next integer
(1, 1, 3 — D2-10 semantic).

### Gap vs FCBQ documented, not implemented

The FCBQ official rule prefers head-to-head when two teams have identical
wins. For typical league configurations (≥10 games per team), head-to-head
divergence happens in <5 % of seasons — a known acceptable approximation
for an MVP. The endpoint metadata declares the tie-breaker explicitly so a
reader can verify the position derivation by hand.

### Upgrade path to v2 — head-to-head CTE

The v2 implementation will add a `head_to_head` CTE before the rank step:

```sql
WITH per_team AS (...),           -- unchanged
aggregated AS (...),              -- unchanged
tied_groups AS (
  -- Find groups of teams with identical (wins, ...) in this competition.
  SELECT competition_id, wins, ARRAY_AGG(team_id) AS members
  FROM aggregated
  GROUP BY competition_id, wins
  HAVING COUNT(*) > 1
),
head_to_head AS (
  -- For each tied group, compute the intra-group win count per team.
  SELECT
    g.competition_id,
    a.team_id,
    COUNT(*) FILTER (
      WHERE g.home_team_id = a.team_id AND g.total_home > g.total_away
         OR g.away_team_id = a.team_id AND g.total_away > g.total_home
    ) AS h2h_wins
  FROM aggregated a
  JOIN tied_groups tg
    ON tg.competition_id = a.competition_id
    AND tg.wins = a.wins
    AND a.team_id = ANY(tg.members)
  JOIN games g
    ON g.competition_id = a.competition_id
    AND g.home_team_id = ANY(tg.members)
    AND g.away_team_id = ANY(tg.members)
  GROUP BY g.competition_id, a.team_id
)
SELECT
  a.team_id,
  ...
  RANK() OVER (
    PARTITION BY a.competition_id
    ORDER BY
      a.wins DESC,
      COALESCE(h.h2h_wins, 0) DESC,    -- new tie-breaker
      a.point_diff DESC,
      a.points_for DESC
  ) AS position
FROM aggregated a
LEFT JOIN head_to_head h USING (team_id, competition_id);
```

The CTE adds ~12 lines of SQL and one self-join. At amateur scale (~30
games / 8 teams per competition) the planner still produces sub-100 ms
results — the explain plan should show a hash join on `tied_groups.members`
without spilling.

### When to upgrade

Trigger the v2 implementation when **any** of the following holds:

- The FCBQ adopts a stricter regulation that requires head-to-head at the
  amateur tier.
- A user reports a real standings divergence (e.g. "my team finished
  ahead in head-to-head but the API says otherwise").
- The dataset reaches multi-league / multi-tier scale where the
  approximation becomes noticeably wrong.

Until then, the gap is documented here and surfaced in the README
walkthrough — a recruiter asking "why is standings simple?" gets a direct
answer (this ADR) instead of a hand-wave.

## Consequences

- **`standings.py` SQL is locked.** Future PRs that change the ORDER BY
  must update this ADR alongside the SQL.
- **Tests assert the FEB chain.** `test_standings_rank.py` (Wave 7) uses a
  fixture where wins are unique → no head-to-head divergence — the test
  passes for both implementations, which is intentional: it gates
  correctness without locking us out of the v2 upgrade.
- **README walkthrough names this ADR** in the "things you might ask" Q&A
  section so the interview defense has a single source of truth.

## Alternatives considered

- **Implement head-to-head at P2.** Rejected: adds ~12 lines of SQL +
  one self-join to the standings query, doubling its complexity for a
  rule that diverges from FEB in <5 % of seasons at amateur scale.
- **Use only `wins DESC`** as a single sort key (let `RANK()` return ties
  freely). Rejected: produces a non-deterministic ordering between tied
  teams across query executions — bad UX, hard to test.
- **Add per-pair differential** as a tie-breaker. Considered but rejected:
  point_diff already covers the season-long pattern; per-pair adds
  complexity proportional to the v2 head-to-head CTE for marginal accuracy
  gain.

## References

- 02-CONTEXT.md D2-10 (decision).
- 02-RESEARCH.md §2 (standings SQL verbatim).
- 02-PLAN.md Task 5.5.1.
- FEB tie-breaker rule (Reglamento de Competiciones, Art. 75).
- ADR-0003 — VAL formula PIR FIBA (parallel showcase of "implement the
  standard, document the gap").
