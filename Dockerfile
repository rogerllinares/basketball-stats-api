# syntax=docker/dockerfile:1.7
# Multi-stage image — RESEARCH §7.1.
# Image target: < 200 MB (INFRA-02). Non-root user. BuildKit cache for uv.
# CMD runs alembic upgrade head then uvicorn (Q4 default — failure mode visible in Koyeb logs).

FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.11.15 /uv /uvx /bin/
WORKDIR /app

# Install deps first (cache-friendly), then the project itself.
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy source + install the project.
COPY pyproject.toml uv.lock README.md /app/
COPY src /app/src
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


FROM python:3.12-slim AS runtime
WORKDIR /app

# Non-root user.
RUN groupadd --system app && useradd --system --gid app --home /app app

# Copy resolved venv + source from the builder stage.
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

USER app
EXPOSE 8000

# Migrations run on every boot (idempotent — alembic exits 0 when already at head).
# Failure surfaces in Koyeb runtime logs (Q4 default).
CMD ["sh", "-c", "alembic upgrade head && uvicorn basketball_stats.main:app --host 0.0.0.0 --port ${PORT}"]
