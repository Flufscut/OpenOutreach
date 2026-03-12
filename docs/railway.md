# Railway Deployment

OpenOutreach can be deployed to [Railway](https://railway.app) for a managed, always-on instance that auto-updates when you sync your fork with upstream.

## Prerequisites

- A GitHub fork of [eracle/OpenOutreach](https://github.com/eracle/OpenOutreach)
- A Railway account with GitHub connected
- The [upstream sync workflow](.github/workflows/sync-upstream.yml) in your fork (runs daily + manual trigger)

## Quick Setup

1. **Create a new Railway project** and add a service from your GitHub fork (`owner/OpenOutreach`).

2. **Set build configuration** via service variables:
   - `RAILWAY_DOCKERFILE_PATH` = `compose/linkedin/Dockerfile`

3. **Add a volume** for persistent storage:
   - Mount path: `/app/assets`
   - This persists SQLite DB, cookies, and ML models across deployments.
   - Set `RAILWAY_RUN_UID=0` so the container can write to the volume.

4. **Set required environment variables** (Railway Variables tab):

   | Variable | Required | Description |
   |----------|----------|-------------|
   | `NON_INTERACTIVE` | Yes | `1` |
   | `LEGAL_ACCEPTANCE` | Yes | `1` (after reading LEGAL_NOTICE.md) |
   | `LLM_API_KEY` | Yes | Your LLM API key |
   | `AI_MODEL` | Yes | Model name (e.g. `gpt-4o`) |
   | `LINKEDIN_EMAIL` | Yes | LinkedIn login email |
   | `LINKEDIN_PASSWORD` | Yes | LinkedIn password |
   | `PRODUCT_DOCS` | Yes | Product description (multi-line OK) |
   | `CAMPAIGN_OBJECTIVE` | Yes | Campaign objective |
   | `LLM_API_BASE` | No | API base URL (optional) |
   | `CAMPAIGN_NAME` | No | Default: "LinkedIn Outreach" |
   | `BOOKING_LINK` | No | Calendar/booking URL |
   | `CONNECT_DAILY_LIMIT` | No | Default: 20 |
   | `CONNECT_WEEKLY_LIMIT` | No | Default: 100 |
   | `FOLLOW_UP_DAILY_LIMIT` | No | Default: 30 |
   | `SUBSCRIBE_NEWSLETTER` | No | Default: true |
   | `DJANGO_SUPERUSER_USERNAME` | No | Admin username (creates superuser on deploy) |
   | `DJANGO_SUPERUSER_EMAIL` | No | Admin email (required if creating superuser) |
   | `DJANGO_SUPERUSER_PASSWORD` | No | Admin password (required if creating superuser) |
   | `LINKEDIN_STORAGE_STATE_B64` | No | Base64-encoded Playwright storage state (skip login) |
   | `LINKEDIN_STORAGE_STATE` | No | Minified JSON Playwright storage state (alternative to B64) |
   | `LINKEDIN_COOKIES_JSON` | No | JSON array of cookies (browser extension format) |
   | `LINKEDIN_COOKIES_B64` | No | Base64-encoded JSON array of cookies |

5. **Deploy** — Railway auto-deploys on push. Add a domain for Django Admin access.

## Upstream Sync

The `.github/workflows/sync-upstream.yml` workflow syncs your fork with `eracle/OpenOutreach`:

- **Schedule**: Daily at 00:00 UTC
- **Manual**: Actions → Sync Upstream → Run workflow

When the workflow pushes to your fork, Railway redeploys automatically.

## Django Admin

When `PORT` is set (Railway does this automatically), the start script runs Django's development server in the background. Access:

- **Landing page**: `https://your-app.railway.app/` (choose CRM or Django Admin)
- **Django Admin**: `https://your-app.railway.app/admin/`
- **CRM UI**: `https://your-app.railway.app/crm/`

**Create a superuser** — Set `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` in Railway Variables. The `ensure_superuser` command runs on every deploy and creates/updates the admin user. Alternatively, use Railway's shell: `python manage.py createsuperuser`

## VNC (Optional)

To view the browser automation live, add a TCP proxy for port 5900 in the Railway dashboard. Connect any VNC client to the provided host:port.

## LinkedIn Checkpoint

LinkedIn may show a verification (checkpoint) page when it detects automated login from cloud IPs. When this happens:

1. **Add a TCP proxy for port 5900** in Railway (Settings → Networking → Add TCP Proxy).
2. **Connect via VNC** to the proxy host:port.
3. **Complete the verification** in the browser (CAPTCHA, email code, etc.).
4. The daemon waits up to 5 minutes for you to finish; once done, it continues and saves the session.

**Alternative — provide cookie data:** Export cookies from your browser (e.g. EditThisCookie, Cookie-Editor) as a JSON array. Set `LINKEDIN_COOKIES_JSON` in Railway with the minified JSON, or `LINKEDIN_COOKIES_B64` with the base64-encoded array. The format supports: domain, name, value, path, expirationDate, httpOnly, secure, sameSite, session. The daemon will convert to Playwright format and skip login.
