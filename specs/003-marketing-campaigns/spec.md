# SPEC-003 — Marketing campaigns and the UTM key that ties a lead to them

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Gap: EOS Gap Map v0.1, domain 5 Marketing & Growth — "No campaign or channel record; no lead-source attribution".

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-003 / 1.0 |
| Status | draft (2026-11-11) |
| Repository / path | bookchaowalit/life-content-api / `specs/003-marketing-campaigns/spec.md` |
| Owner (maker) | Claude Code (marketing attribution session, 2026-11-11) |
| Reviewer (checker) | Codex review Stop hook + a fresh reviewer before merge |
| Approver | Owner (asked to start the work 2026-11-11; merge and deploy wait for the owner) |
| Paired change | bookchaowalit/sales-crm SPEC "lead attribution" (CRM stores the UTM of each inquiry) |
| Branch | `feat/marketing-campaigns` (PR, not main-only) |

## 1. Problem and intent

- **Problem:** nothing records which campaign ran on which channel, with what budget and dates, so no
  lead or baht can be traced back to the work that brought it in.
- **Outcome:** a `campaign` resource in the content cell. Each campaign owns one `utm_campaign` key
  (unique per workspace). The CRM stores the same key on every inquiry, so the two can be joined.
  Content pieces and calendar entries can point at the campaign they serve.
- **Why now:** Finance suite is the first product to sell (2026-11-11); its launch needs measured channels.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| `campaign` resource (CRUD, filters, date range rule, unique UTM key), `campaign_id` on `content` and `content-calendar`, migration `0002` | Ad-platform spend import, a reporting mart, email marketing lists, social scheduling, any personal data |

## 3. Behaviour — scenarios

### AC-01 — A campaign has a name, a channel and a UTM key
- **When** the owner creates a campaign without `name`, `channel` or `utm_campaign` → 422.
- **When** `channel` is not one of `seo, pseo, social_organic, social_paid, email, community, marketplace, outreach, referral, partner, ads_search, event, other` → 422.

### AC-02 — The UTM key is a safe slug and unique per workspace
- `utm_campaign` (and `utm_source`, `utm_medium` when set) must match `^[a-z0-9][a-z0-9._-]{0,63}$` → otherwise 422.
- A second campaign with the same `utm_campaign` in the same workspace → 409; another workspace may reuse it.

### AC-03 — Dates and money are sane
- `start_date` after `end_date` → 422; the same day is accepted.
- `budget_thb` and `spend_thb` are whole baht, `0 … 100000000`; a negative value → 422.

### AC-04 — Status follows a small lifecycle vocabulary
- `status` ∈ `planned, active, paused, ended, killed`, default `planned`.

### AC-05 — Content and calendar entries can serve a campaign
- `campaign_id` on `content` and `content-calendar` must name an existing campaign of the same workspace → otherwise 422.
- Deleting a campaign that content still points at → 409.

## 4. Data and contract

- New table `content.campaigns`, RLS `workspace_isolation`, grants to `content_api` (migration `0002_campaigns.sql`, append-only).
- New permissions `content.campaign:read|write|delete`. **Rollout:** the owner grants them on the hosted
  platform (`empire-cells grant --cell content`) after deploy; until then campaign routes answer 403.

## 5. Verification

- Red first: `tests/test_campaigns.py` fails before `cell.yaml` and the migration change.
- Green: `.venv/bin/pytest -q`, `.venv/bin/mypy .`, `uvx ruff@0.17.1 check . && uvx ruff@0.17.1 format --check .`.
- After deploy (owner go-ahead): `/health`, one authorized `GET /v1/campaigns`.
