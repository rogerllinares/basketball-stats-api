# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-19
**Phase:** 1-foundation
**Areas discussed:** Skeleton, Alembic, Health endpoints, Python+Koyeb/Neon, + Claude's discretion bucket (CI, Observability, Docker, Repo hygiene, README, ADRs)

---

## Esqueleto de directorios

### Q1 — Alcance del árbol src/

| Option | Description | Selected |
|--------|-------------|----------|
| Árbol completo vacío | Pre-creem api/v1, core, models, schemas, services, repositories, tasks amb `__init__.py` + placeholder docstring. P2 ja té els forats. Recruiter veu l'arquitectura sencera dia 1. | ✓ |
| Mínim absolut | Només main + core + api/v1/health. P2 crea la resta. Repo més honest en P1. | |
| Intermedi | core/, api/v1/, tests/ ara; resta a P2. | |

**User's choice:** Árbol completo vacío
**Notes:** Confirms ARCHITECTURE.md research; P2 velocity prioritized over "no empty files" honesty.

### Q2 — Marcar archivos vacíos

| Option | Description | Selected |
|--------|-------------|----------|
| Solo `__init__.py` | Subdirs amb `__init__.py` buit + docstring. No team.py/player.py stubs. | ✓ |
| Placeholder per entitat | models/team.py amb `# TODO Phase 2`. | |
| Tú decides | Claude tria el patró més net. | |

**User's choice:** Solo `__init__.py`
**Notes:** No fake files; first commit by entity is real content.

### Q3 — Estructura tests/

| Option | Description | Selected |
|--------|-------------|----------|
| tests/unit + tests/integration | Split des de P1. 1-2 tests cada subdir. | ✓ |
| tests/ flat | Només tests/test_health.py + conftest. Split quan P2. | |

**User's choice:** tests/unit + tests/integration
**Notes:** Convention from first commit; no refactor later.

---

## Alembic init en P1

### Q1 — Alembic en P1?

| Option | Description | Selected |
|--------|-------------|----------|
| Inicialitzar amb migration buida | `alembic init` + `0001_baseline.py` amb `pass`/`pass`. Pipeline validat des de P1. | ✓ |
| Diferir a P2 | P1 no toca Alembic. P2 ho fa quan arriben DOM. | |

**User's choice:** Inicialitzar amb migration buida
**Notes:** Pipeline-as-infrastructure. P2 stress = només modelar, no debugar alembic.

---

## Health endpoints + DB outage (Claude's discretion — Roger delegat)

| Decision | Alternatives considered | Chosen |
|----------|------------------------|--------|
| Single `/healthz` vs split `/healthz` + `/readyz` | (a) Single (compleix OBS-02 literal). (b) Split (K8s-pure idiom). | (a) Single — OBS-02 spec ja decidit; split es ADR-0007 P5 opcional. |
| Response on DB fail | (a) Always 200 amb status:degraded. (b) 503 amb sanitized error. | (b) 503 — Koyeb HTTP check restart, cloud-native correct. |

**Notes:** Defense framed for recruiter: HTTP code = contract per Koyeb, body = humans.

---

## Python version + Koyeb/Neon setup (Claude's discretion)

| Decision | Alternatives considered | Chosen |
|----------|------------------------|--------|
| Python version | 3.11 (PROJECT.md), 3.12 (INFRA-02), 3.13 (newest). | 3.12 — pin via `.python-version` + `requires-python>=3.12`. Estable + suportat fins 2028-10. |
| Setup Koyeb/Neon | (a) Manual fora del repo. (b) docs/setup/koyeb-neon.md committed. | (b) Documentat step-by-step al repo; Roger executa manualment durant P1 execute. |

---

## Claude's Discretion buckets (Roger said "haz lo que sea mejor para el portfolio")

### CI/CD scope P1

- Single Python version (NO matrix).
- testcontainers wiring des de P1 (1 smoke integration test).
- uv cache via `astral-sh/setup-uv@v3`.
- CI gate on push + PR a `main`.
- Round-trip migration validation step (mitiga P3.1 pitfall).

### Observability scope P1

- structlog JSON prod / console dev.
- Custom ASGI middleware per `request_id` (accept inbound or generate UUID4).
- 5 badges al README (CI, ruff, mypy, Python, license).

### Docker

- Multi-stage Dockerfile basat en python:3.12-slim.
- Image <200 MB. Non-root user.
- BuildKit cache mount per uv.
- `.dockerignore` exhaustiu (mitigated P4.3 + P4.1).
- docker-compose: api + postgres-16-alpine + named volume + pg_isready healthcheck (mitigated P4.4 + P4.5).
- Bind-mount + `--reload` en dev.

### Repository hygiene + GitHub

- GitHub remote creat en P1, repo PUBLIC dia 1.
- Pre-commit hooks: ruff + gitleaks + mypy + conventional commits.
- Dependabot weekly.
- `.gitignore` exhaustiu abans del first push.

### README + ADRs

- README mínim-viable amb badges + quickstart + deploy pointer + Stack walkthrough stub.
- `docs/setup/koyeb-neon.md` step-by-step.
- `docs/adr/0001-stack-election.md` baseline. Altres ADRs creixen per phase.

---

## Claude's Discretion

Roger delegat totes les decisions restants amb la consigna: *"haz lo que sea mejor para el portfolio y documenta que haces y porque para que yo luego pueda explicarlo"*. Documentació per a defense interview integrada a CONTEXT.md (cada D-XX té "Defense:" o "Pro/Con" explícit).

## Deferred Ideas

- `/readyz` separat (ADR-0007, P5 polish opcional).
- OpenTelemetry full stack (milestone v2).
- Materialized views leaderboards (P4 si emergeix necessitat).
- Matrix CI multi-Python (out of scope solo dev).
- Server-side conventional commits enforcement (only if local hooks fail).
- JWT_SECRET rotation policy (v2).
- Multi-region Koyeb (overkill MVP).
- Custom domain `basketball-stats.cat` (P5 polish opcional).
