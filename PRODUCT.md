# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through the cell's own MCP server (`content-mcp`, tools
  `content.<resource>.list|get|create|update|delete`) and the hosted tool hub
  (`platform-mcp-remote-worker`, which lists this cell's origin).
- Local owner tooling that reads cells through the registry client: `ops-toolkit`
  (`infra/scripts/utils/cell_store.py`) and `mcp-aggregator` (`src/cell-store.ts`, `EMPIRE_CONTENT_API`).
- Automations with an `empire-platform` token (for example `owner-mcp`), within the permissions
  `content.content|content-calendar|content-series-episode|content-series-episode-metric:read|write|delete`.
- No web page reads this cell yet: `life-dashboard-web` has no content module.

## Product Purpose

The owner's register of content work in four resources: finished or planned content pieces, a
publishing calendar, the episodes of a short-video series, and dated metric snapshots per episode.
It lets content be planned, moved through its stages and measured in one place.

Success: every piece, calendar entry and series episode exists once with its current stage, and the
reach of an episode (views, likes, shares, followers) can be read as a series of dated snapshots.

## Positioning

One capability, one service: its own API (Railway), its own database (Neon) with row-level
security per workspace, and authorization, executions and audit through `empire-platform`. It is
workspace-scoped, so the same service can serve other tenants without code changes.

## Operating Context

- Production: `https://content-api-production-bca7.up.railway.app` (`/health`), deployed by
  merging to `main` after CI.
- The cell was created empty on 2026-10-11: the old SQLite tables held no rows, so nothing was
  imported. Imports through the API keep the old id in `legacy_id`.
- Monitored by `platform-uptime-worker` (`content-api`); errors go to Sentry when `SENTRY_DSN` is set.
- This cell publishes no graph events (`cell.yaml` has no `graph:`).

## Capabilities and Constraints

- `/v1/contents`: list (filters `content_type`, `status`, `related_niche_id`), stats, get,
  get-by-legacy-id, create (with `Idempotency-Key`), patch (with `expected_version`), delete.
- `/v1/content-calendars`: the same routes; filters `content_type`, `status`, `has_cta`,
  `repurpose_from`, `related_project_id`, `related_content_id`.
- `/v1/content-series-episodes`: the same routes; filter `status`.
- `/v1/content-series-episode-metrics`: the same routes; filter `episode_id`.
- Rules tested:
  - `title` is required and not empty on content and calendar entries; an episode needs
    `series_slug`, `day_number` and `account_handle`; a metric needs `episode_id` and `captured_at`.
  - `content_type` and `status` are fixed enums and differ per resource (the calendar knows
    `thread` and `carousel`, content knows `playbook`; episodes have their own recording and
    publishing steps).
  - A content piece starts as an `idea` with `views`, `shares`, `leads_generated` at 0; a calendar
    entry starts as a `blog` idea with priority 3, `has_cta` false and zero counters; an episode
    starts as a `tiktok` idea; a metric defaults to source `manual`.
  - `repurpose_from`, `related_content_id` and a metric's `episode_id` must point at a record of
    the same workspace (422 `reference_not_found`); deleting a record that others still point at is
    refused (409 `has_dependents`).
  - `published_at` cannot be before `recorded_at` on an episode (422 `invalid_value`).
  - No uniqueness is enforced: titles and series days may repeat; an episode may have many
    snapshots.
  - `stats` groups only by a filter; any other `group_by` is a 422. List order is oldest first
    (`order=desc` reverses it).
- Counters (`views`, `shares`, `likes`, ...) are 32-bit integers with no lower bound: a negative
  count is accepted, and a value above 2147483647 currently ends in a server error instead of a 422
  (known gap in the shared service code, covered by an expected-failure test).
- `related_niche_id`, `related_project_id` and `related_skill_ids` are plain ids, not foreign keys;
  which cell they point at is [ต้องยืนยัน].
- Out of scope: publishing to platforms, scraping metrics, and the content text itself beyond the
  `body`/`body_html`/`content_body` fields.

## Measures

Proposed (nothing collects them yet):

- Calendar entries moved to `published` or `repurposed` per month.
- Episodes with at least one metric snapshot after reaching `published_verified`.
- 5xx rate and p95 latency on `/v1/contents` (Sentry and uptime worker).
