# Basketball Stats API

> REST API per a estadístiques de bàsquet amateur — FCBQ. FastAPI + Postgres pur (Neon) + Docker + Koyeb.

![CI](https://github.com/rogerllinares/basketball-stats-api/actions/workflows/ci.yml/badge.svg)
![Ruff](https://img.shields.io/badge/lint-ruff-blue)
![Mypy](https://img.shields.io/badge/types-mypy--strict-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Live URL:** `(coming soon — first deploy pending in execute follow-up)`

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

Manual deploy walkthrough (Phase 1): see [`docs/setup/koyeb-neon.md`](docs/setup/koyeb-neon.md).
Tag-driven automation lands in Phase 4 (`INFRA-04`).

## Stack walkthrough

Phase 5 polish — full per-file walkthrough lands then. For now:

- [`docs/adr/0001-stack-election.md`](docs/adr/0001-stack-election.md) — rationale per cada eina del stack.
- [`docs/setup/koyeb-neon.md`](docs/setup/koyeb-neon.md) — operational deploy doc.
- [`.planning/`](. planning/) — full project planning trail (PROJECT, REQUIREMENTS, ROADMAP, per-phase CONTEXT + RESEARCH + PLAN).

## License

MIT — see [LICENSE](LICENSE).
