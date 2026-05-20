# Manual deploy walkthrough — Neon + Render (Phase 1)

Phase 1 deploys manually. The full pipeline (build → release on push to `master`)
is automated via `render.yaml` IaC + Render's GitHub integration. Tag-driven
release automation lands in Phase 4 (`INFRA-04`).

> **Why Render and not Koyeb?** See `docs/adr/0002-deploy-pivot-render.md`.
> TL;DR: Koyeb removed its free tier post-Mistral acquisition (forces $30/mo
> Pro). Fly.io requires credit card post-Oct-2024. Render free Docker web service
> remains the only zero-CC option that supports Docker deploy.

## 1. Neon project (free tier)

1. Sign up at <https://neon.tech> (GitHub OAuth).
2. **Create project** → name `basketball-stats-api`, region
   `aws-eu-central-1` (Frankfurt — co-located with Render `frankfurt`).
3. **Dashboard → Connection Details.** Copy **both** strings:
   - **Pooled** (default toggle ON) → `DATABASE_URL`
     `postgresql://<user>:<pwd>@ep-XXXX-pooler.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require`
   - **Direct** (toggle Pooled OFF) → `DATABASE_URL_DIRECT`
     `postgresql://<user>:<pwd>@ep-XXXX.c-3.eu-central-1.aws.neon.tech/neondb?sslmode=require`

> **⚠ Never point `DATABASE_URL_DIRECT` at the pooled URL.** PgBouncer in
> transaction mode silently corrupts Alembic migration state (cached statements,
> prepared transactions). The app uses pooled; Alembic uses direct. R3 in
> `.planning/phases/01-foundation/RESEARCH.md`.

## 2. Render web service — via dashboard (one-time)

Render's `render.yaml` IaC handles future updates, but the **first** wiring
between repo and Render must be done in the dashboard once.

1. Open <https://dashboard.render.com> → **New** → **Web Service**.
2. **Connect a repository** → authorize Render GitHub app on
   `rogerllinares/basketball-stats-api` → select repo.
3. Render auto-detects `render.yaml` at repo root and shows the IaC preview.
   Confirm:
   - **Name:** `basketball-stats-api`
   - **Region:** `frankfurt`
   - **Branch:** `master`
   - **Runtime:** `Docker`
   - **Plan:** `Free`
   - **Health check path:** `/healthz`
   - **Auto-deploy:** **OFF** (manual deploys only — same policy as SST, to avoid
     burning free-tier build minutes on every dependabot patch).
4. Click **Create Web Service**. First build starts; will fail because secrets
   are not set yet. Expected.

## 3. Secrets (dashboard → Environment)

In the new service → **Environment** tab → **Add Environment Variable**:

| Key | Value | Source |
|---|---|---|
| `DATABASE_URL` | `<pooled URL from step 1>` | Neon |
| `DATABASE_URL_DIRECT` | `<direct URL from step 1>` | Neon |
| `JWT_SECRET` | output of `openssl rand -hex 32` | Generate locally |
| `ENV` | `prod` | Static |
| `LOG_LEVEL` | `INFO` | Static |
| `PORT` | `8000` | Static (Render proxies `$PORT` → container) |

> Render mounts these as env vars inside the container at runtime — no rebuild
> needed when rotating secrets.

Generate `JWT_SECRET` locally (do **not** paste into chat):

```powershell
openssl rand -hex 32
```

Save Environment → service auto-redeploys.

## 4. Smoke test asyncpg + Neon SSL (local, before push)

```powershell
$NEON_POOLED = '<pooled URL from step 1>'

uv run python -c @"
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
"@
```

If this fails with an SSL error, fall back to Strategy A: `connect_args={'ssl':
'require'}` in `src/basketball_stats/core/db.py`.

## 5. Trigger first deploy

Auto-deploy is OFF (step 2). To deploy:

- **Dashboard:** service → **Manual Deploy** → **Deploy latest commit**. Or:
- **Render CLI** (`brew install render` / `winget install render`):
  ```powershell
  render login
  render deploys create <SERVICE_ID> --wait
  ```

Render pulls the repo, builds the Docker image, runs `alembic upgrade head`
inside the container CMD, then starts uvicorn. First boot ~2-3 min (cold image).

Live URL appears in the dashboard once health check passes:
`https://basketball-stats-api-<hash>.onrender.com`.

## 6. Verify

```powershell
$URL = 'https://basketball-stats-api-<hash>.onrender.com'
curl "$URL/healthz"      # → {"status":"ok","db":"reachable"}
curl "$URL/docs"         # → OpenAPI Swagger UI
```

## 7. Verify JSON logs + request_id

Dashboard → service → **Logs** tab. Filter by `request_id`. You should see JSON
lines with `"request_id":"..."` per `/healthz` hit (D-19 + D-20).

CLI alternative:

```powershell
render logs <SERVICE_ID> --tail 50 | Select-String request_id
```

## 8. Defeat 15-min idle cold-start (free tier limitation)

Render's free tier sleeps services after **15 min of no requests**. Cold-start
on wake is ~30 s — bad for a recruiter who clicks the live URL once.

Mitigation: GHA cron pings `/healthz` every 14 min. See
`.github/workflows/warm-ping.yml` (runs on `schedule: cron: '*/14 * * * *'`).

The 750 free instance-hours/month easily cover 24/7 warm.

## 9. Subsequent deploys (Phase 1+)

`master` is auto-deploy **OFF**. To ship a change:

1. Open PR → CI verda → merge to `master`.
2. Wait for the merge commit to appear in Render dashboard (Render polls the
   repo every ~1 min).
3. **Manual Deploy → Deploy latest commit**.

Rationale: matches SST policy. Prevents dependabot patches from burning
free-tier build minutes when nothing changed functionally.

## Troubleshooting

- **Build fails with `uv sync --locked`** → dependabot bumped `pyproject.toml`
  without `uv.lock`. Workaround documented in handoff (manual lock regen). The
  durable fix is `.github/workflows/uv-lock-bot.yml` (TODO P3).
- **Alembic `relation already exists`** → previous migration ran on pooled URL.
  Reset: connect with `DATABASE_URL_DIRECT`, `DROP TABLE alembic_version`,
  redeploy.
- **Health check 503 on first deploy** → expected for ~30 s while Alembic runs
  `upgrade head`. If 503 persists >2 min, check logs for asyncpg SSL handshake
  or env var typos.
- **Cold-start >60 s** → free tier is sleeping. Verify
  `.github/workflows/warm-ping.yml` schedule is enabled and recent runs are
  green.
