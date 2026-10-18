# life-content-api
The Content cell: its own API (Railway, serverless) and its own Neon
database, described by `cell.yaml` and served by the code in `src/cellkit/`, which
this repository owns. It
reuses empire-platform for identity, authorization, executions and audit over
HTTP with the caller's token.

| | |
|---|---|
| API | Railway project `life-content-api`, service `content-api` (Serverless) |
| Data | Neon project `life-content-api`, database `content` |
| Registry | solo-empire `repository-catalog/registries/online-systems.yaml` (`content`) |

## API

Every resource has list, stats, get, get-by-legacy-id, create, patch and delete
(see `cellkit/app.py`). Permissions are `content.<resource>:read|write|delete`.

| Path | Resource | Filters |
|---|---|---|
| `/v1/contents` | content | `content_type`, `status`, `related_niche_id` |
| `/v1/content-calendars` | content-calendar | `content_type`, `status`, `has_cta`, `repurpose_from`, `related_project_id`, `related_content_id` |
| `/v1/content-series-episodes` | content-series-episode | `status` |
| `/v1/content-series-episode-metrics` | content-series-episode-metric | `episode_id` |

## Develop and operate

```bash
uv venv .venv && uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/pytest -q
NEON_API_KEY=... .venv/bin/content-db provision
npm install && railway config apply && railway up --ci --service content-api
railway scale --service content-api asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0   # next to Neon and the platform
```

Railway variables: `SENTRY_DSN` (error reporting; unset = off, see
`src/cellkit/_sentry.py`), `CONTENT_DB_MODE=hosted`, `CONTENT_DB_URL_API`,
`CONTENT_JWT_PUBLIC_KEY_PEM`, `CONTENT_JWT_ISSUER`, `EMPIRE_PLATFORM_URL`.
