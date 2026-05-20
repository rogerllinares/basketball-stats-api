# Basketball Stats API

> REST API per a estadístiques de bàsquet amateur — FCBQ. FastAPI + Postgres pur (Neon) + Docker + Render.

![CI](https://github.com/rogerllinares/basketball-stats-api/actions/workflows/ci.yml/badge.svg)
![Ruff](https://img.shields.io/badge/lint-ruff-blue)
![Mypy](https://img.shields.io/badge/types-mypy--strict-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![Postgres](https://img.shields.io/badge/postgres-16-336791)
![License](https://img.shields.io/badge/license-MIT-green)

**Live:** <https://basketball-stats-api-banq.onrender.com> · [`/healthz`](https://basketball-stats-api-banq.onrender.com/healthz) · [`/docs`](https://basketball-stats-api-banq.onrender.com/docs)

## What this is

API REST per a una lliga amateur de bàsquet (FCBQ, Catalunya). Tracks competitions,
teams, players, games, box-scores. Read endpoints públics; les escriptures requereixen
JWT de coach (Phase 3+). Flagship endpoint `/matchday/{date}/ideal-five` arriba a
Phase 4 (window-function `RANK PARTITION BY` posició).

Portfolio piece — diseñat per ser defensable en una entrevista de 30 min.

## Local dev

```bash
# 1. Clone + install
git clone https://github.com/rogerllinares/basketball-stats-api.git
cd basketball-stats-api
uv sync --locked

# 2. Spin up Postgres + the API
docker compose up -d
# Wait ~10s for postgres healthcheck + alembic upgrade
curl http://localhost:8000/healthz
# {"status":"ok","db":"ok"}

# 3. OpenAPI playground
open http://localhost:8000/docs
```

## Deploy

Manual deploy walkthrough (Phase 1): see [`docs/setup/render-neon.md`](docs/setup/render-neon.md). IaC at [`render.yaml`](render.yaml). Tag-driven automation lands in Phase 4 (`INFRA-04`).

The original target was Koyeb; the pivot to Render is documented in [`docs/adr/0002-deploy-pivot-render.md`](docs/adr/0002-deploy-pivot-render.md).

## Phase 2 walkthrough — domain + public reads

**Shipped 2026-05-20.** 10 SQLAlchemy entities + 8 GET endpoints + window functions + GENERATED columns + Catalan seed.

### Endpoints (live)

| Method | Path | What it shows |
|---|---|---|
| `GET` | `/api/v1/competitions` | List competitions (paginated 50/page) |
| `GET` | `/api/v1/competitions/{id}` | Competition + season label |
| `GET` | `/api/v1/competitions/{id}/standings` | Window-function `RANK() OVER (ORDER BY wins DESC, point_diff DESC)` — FEB-style tie-break |
| `GET` | `/api/v1/competitions/{id}/leaderboards/{stat}` | Top-N by `pts`/`reb`/`ast`/`stl`/`blk`/`val` — nested window (`RANK + AVG`) |
| `GET` | `/api/v1/teams/{id}` | Roster + recent games + upcoming games embedded (single round-trip via `selectinload`) |
| `GET` | `/api/v1/players/{slug}` | Player by `normalize_name` slug (NFD + `ç→c`) |
| `GET` | `/api/v1/players/by-id/{id}` | Player by id — split route avoids regex collision |
| `GET` | `/api/v1/games/{id}` | Game + both box-scores |

Try it live: <https://basketball-stats-api-banq.onrender.com/docs>

### Postgres showcase

- **GENERATED COLUMNS** (`migrations/versions/0002_core_entities.py`):
  - `box_scores.reb = oreb + dreb` (simple addition).
  - `box_scores.val = pts + reb + ast + stl + blk + fgm + ftm − fga − fta − to` — PIR FIBA literal (see [`docs/adr/0003-val-pir-fiba-formula.md`](docs/adr/0003-val-pir-fiba-formula.md)).
- **Window functions** (`src/basketball_stats/repositories/standings.py`, `leaderboards.py`):
  - `RANK() OVER (ORDER BY wins DESC, point_diff DESC)` for standings (Phase 2 tie-break; head-to-head v2 path documented in [`docs/adr/0004-standings-tie-breaker.md`](docs/adr/0004-standings-tie-breaker.md)).
  - Nested `RANK + AVG OVER (PARTITION BY player_id)` for leaderboards top-N by averaged stat.
- **Catalan-aware slugs** (`src/basketball_stats/utils/normalize.py`):
  - `normalize_name("Barça") == "BARCA"` — NFD + filter combining marks + explicit `ç→c` maketrans + uppercase.

### Defense for interview

- 6 repositories in `src/basketball_stats/repositories/` carry `"""Showcase:"""` + `"""Defense for interview:"""` docstrings.
- 2 ADRs document the non-obvious choices: PIR FIBA + Supercopa↔Territorial asymmetry (`0003`), FEB-simple tie-break and v2 upgrade path (`0004`).
- All ORM relationships use `lazy="raise_on_sql"` — accidental N+1 queries hard-fail in tests.
- All seed `license_id`s live in `99001-99012` to stay outside the real FCBQ federation range — the demo cannot be confused with production data.

### Plan trail

- [`docs/adr/0001-stack-election.md`](docs/adr/0001-stack-election.md) — rationale per cada eina del stack.
- [`docs/adr/0002-deploy-pivot-render.md`](docs/adr/0002-deploy-pivot-render.md) — deploy pivot Koyeb → Render.
- [`docs/adr/0003-val-pir-fiba-formula.md`](docs/adr/0003-val-pir-fiba-formula.md) — VAL = PIR FIBA + Supercopa↔Territorial NOT NULL DEFAULT 0.
- [`docs/adr/0004-standings-tie-breaker.md`](docs/adr/0004-standings-tie-breaker.md) — FEB-simple now, head-to-head v2.
- [`docs/setup/render-neon.md`](docs/setup/render-neon.md) — operational deploy doc.
- [`.planning/`](.planning/) — full project planning trail (PROJECT, REQUIREMENTS, ROADMAP, per-phase CONTEXT + RESEARCH + PLAN).

## License

MIT — see [LICENSE](LICENSE).
