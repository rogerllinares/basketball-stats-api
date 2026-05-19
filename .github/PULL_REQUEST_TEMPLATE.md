<!-- Title: <type>(<scope>): <short summary> (#<issue>)
     Types: feat | fix | chore | docs | ci | refactor | test | infra | security -->

## What

<!-- 1-3 bullets describing the change. The "why" goes in the linked issue. -->

-
-

## Closes

<!-- REQUIRED. Every PR closes at least one issue. If you didn't open one, open it now. -->
Closes #

## How verified

<!-- Concrete proof: command + outcome. CI green is necessary but not sufficient. -->

- [ ] `uv run pytest` green locally
- [ ] `uv run ruff check . && uv run mypy --strict src/`
- [ ] CI green on this branch
- [ ] Manual smoke (if applicable): <command + expected output>

## Notes / trade-offs

<!-- Optional. Anything reviewer should know but isn't obvious from the diff. -->
