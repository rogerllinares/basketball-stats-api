> # ⚠ SUPERSEDED — 2026-05-20
> #
> # This walkthrough is **no longer active**. Koyeb removed its free tier
> # post-Mistral acquisition (the R2 risk in RESEARCH.md materialized).
> # See **`docs/setup/render-neon.md`** for the active deploy path and
> # **`docs/adr/0002-deploy-pivot-render.md`** for the full rationale.
> #
> # Kept here as historical context — the deploy path was rebuilt from
> # scratch, not patched on top of this doc.

# Manual deploy walkthrough — Neon + Koyeb (Phase 1)

Phase 1 deploys manually. The full pipeline (build → push → migrate → release) is
automated on tag in Phase 4 (`INFRA-04`).

## 1. Neon project (free tier)

1. Sign up at <https://neon.tech> (Google or GitHub OAuth).
2. **Create project** → name `basketball-stats-api`, region `aws-eu-central-1`
   (Frankfurt — co-located with Koyeb `fra`).
3. **Dashboard → Connection Details.** Copy **both** strings:
   - **Pooled** (default toggle ON) → `DATABASE_URL`
     `postgresql://<user>:<pwd>@ep-XXXX-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`
   - **Direct** (toggle Pooled OFF) → `DATABASE_URL_DIRECT`
     `postgresql://<user>:<pwd>@ep-XXXX.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require`

> **⚠ Never point `DATABASE_URL_DIRECT` at the pooled URL.** PgBouncer in transaction
> mode silently corrupts Alembic migration state (cached statements, prepared
> transactions). The app uses the pooled URL; Alembic uses direct. R3 in
> `.planning/phases/01-foundation/RESEARCH.md`.

## 2. Koyeb account + CLI

```powershell
# install the CLI
powershell -c "irm https://www.koyeb.com/install.ps1 | iex"

# OAuth login (browser flow)
koyeb login
koyeb whoami   # confirms cached token at ~/.koyeb/config.yaml
```

## 3. Secrets

```powershell
$NEON_POOLED  = '<pooled URL from step 1>'
$NEON_DIRECT  = '<direct URL from step 1>'
$JWT_SECRET   = (openssl rand -hex 32)   # stub for Phase 3

koyeb secrets create DATABASE_URL          --value $NEON_POOLED
koyeb secrets create DATABASE_URL_DIRECT   --value $NEON_DIRECT
koyeb secrets create JWT_SECRET            --value $JWT_SECRET

koyeb secrets list
```

## 4. Smoke test asyncpg + Neon SSL

```powershell
uv run python -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

url = '$NEON_POOLED'.replace('postgresql://', 'postgresql+asyncpg://', 1)
async def m():
    e = create_async_engine(url)
    async with e.connect() as c:
        r = await c.execute(text('SELECT 1'))
        print('ok', r.scalar())
asyncio.run(m())
"
```

If this fails with an SSL error, fall back to Strategy A:
`connect_args={'ssl': 'require'}` in `core/db.py`.

## 5. First deploy

```powershell
# Build + push image to GHCR (Koyeb pulls from there).
docker build -t ghcr.io/rogerllinares/basketball-stats-api:0.1.0-rc1 .
gh auth token | docker login ghcr.io -u rogerllinares --password-stdin
docker push ghcr.io/rogerllinares/basketball-stats-api:0.1.0-rc1

# Create the Koyeb app.
koyeb app init basketball-stats-api `
    --docker ghcr.io/rogerllinares/basketball-stats-api:0.1.0-rc1 `
    --instance-type free `
    --regions fra `
    --ports 8000:http `
    --routes /:8000 `
    --env PORT=8000 `
    --env "DATABASE_URL={{ secret.DATABASE_URL }}" `
    --env "DATABASE_URL_DIRECT={{ secret.DATABASE_URL_DIRECT }}" `
    --env ENV=prod `
    --env LOG_LEVEL=INFO
```

Wait for service `healthy`, then `curl https://basketball-stats-api-<slug>.koyeb.app/healthz`.

## 6. Health check config — via dashboard UI

> **⚠ Koyeb's CLI flag syntax for HTTP health checks is not publicly documented.**
> Configure via the dashboard for Phase 1; automation lands in Phase 4 (INFRA-04).
> R1 in `.planning/phases/01-foundation/RESEARCH.md`.

1. Open <https://app.koyeb.com> → `basketball-stats-api` app → `basketball-stats-api`
   service → **Settings → Health Checks**.
2. Click **Add health check** → choose **HTTP**.
3. Fill in:
   - **Path:** `/healthz`
   - **Port:** `8000`
   - **Grace period:** `30s`
   - **Interval:** `10s`
   - **Timeout:** `5s`
   - **Failure threshold (auto-restart):** `5`
4. Save. Koyeb will restart the instance after 5 consecutive failed probes
   (matches D-10 contract: `/healthz` returns 503 when DB unreachable so Koyeb
   knows to recycle, not just log).

## 7. Verify JSON logs + request_id

```powershell
koyeb logs basketball-stats-api/basketball-stats-api --type runtime |
    Select-String request_id | Select-Object -First 5
```

You should see JSON lines with `"request_id":"..."` per request (D-19 + D-20).
