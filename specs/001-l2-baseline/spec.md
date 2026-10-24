# SPEC-001 — L2 baseline: locked dependencies, strict types, domain rules under test

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Big Loop Plan Wave 2 (solo-empire `repository-catalog/roadmaps/BIG-LOOP-PLAN-2026-10-21.md`).

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-001 / 1.0 |
| Status | approved (2026-10-24, see Approval) |
| Repository / path | bookchaowalit/life-content-api / `specs/001-l2-baseline/spec.md` |
| Owner (maker) | Claude Code (Wave 2 cells session) |
| Reviewer (checker) | Fresh Claude reviewer session (no maker context) |
| Approver | AI approval 2026-10-24 under the owner's process (see Approval) |
| Requirement links | Big Loop DoD L2: `PRODUCT.md`, ≥ 3 test files, Sentry, type check; L1 lockfile |
| Main-only | yes: committed straight to `main`, so the red run is local (ADR-0004 rule 2, v1.1) |
| Created / approved | 2026-10-22 / 2026-10-24 |

## 1. Problem and intent

- **Problem:** Dependencies were installed unpinned, there was no type check, the only tests were the generic contract suite, the API stored a series episode published before it was recorded, and an integer counter above 2147483647 ends in a server error instead of a 422.
- **Outcome:** the image installs exactly `uv.lock` (`uv sync --frozen`), CI runs Ruff, mypy
  (strict on `src/`) and a coverage gate on shared CI v1.1.1, and the cell's own rules have
  tests of their own beyond the generic contract suite.
- **Why now:** Wave 2 of the Big Loop Plan; milestone M1 is 2026-11-15.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| `uv.lock`, Dockerfile, CI caller bump, Ruff/mypy config and fixes, domain tests, `PRODUCT.md` | New endpoints or fields; database migrations; a shared cellkit package (owner decision 2026-10-21: each service owns its code) |

## 3. Behaviour — scenarios

### AC-01 — An episode cannot be published before it was recorded

- **Given** an owner with write permission
- **When** they create an episode with `recorded_at` 2026-10-12T09:00 and `published_at` 2026-10-11T09:00
- **Then** the API answers 422 `invalid_value` naming both fields; the same moment for both is accepted
- **Test:** `tests/test_content_validation.py::test_an_episode_cannot_be_published_before_it_was_recorded` · level: integration (API + throwaway PostgreSQL)

### AC-02 — Publishing before the recording is refused on update

- **Given** an episode recorded on 2026-10-12
- **When** a patch sets `published_at` to 2026-10-01
- **Then** the API answers 422 and the stored `published_at` stays empty; a patch that touches neither moment still succeeds
- **Test:** `tests/test_content_validation.py::test_publishing_before_the_recording_is_refused_on_update` · level: integration (API + throwaway PostgreSQL)

### AC-03 — Calendar entries and content use their own kinds

- **Given** the content and content-calendar resources
- **When** the owner creates entries of type `thread`, `carousel` and `playbook`
- **Then** the calendar accepts thread and carousel but refuses playbook; content accepts playbook
- **Test:** `tests/test_content_validation.py::test_the_calendar_knows_thread_and_carousel_but_not_playbook` · level: integration (API + throwaway PostgreSQL)

### AC-04 — References must resolve inside the workspace

- **Given** a calendar entry or metric that points at another record
- **When** the id does not exist or belongs to another workspace
- **Then** the API answers 422 `reference_not_found`; deleting a record that is still referenced answers 409 `has_dependents`
- **Test:** `tests/test_content_validation.py::test_a_reference_to_another_workspace_is_refused` · level: integration (API + throwaway PostgreSQL)

### AC-05 — New records start with the documented defaults

- **Given** create requests with only the required fields
- **When** a content piece, calendar entry, episode and metric are created
- **Then** content is an idea with zero counters, the entry is a blog idea with priority 3, the episode is a tiktok idea and the metric source is manual
- **Test:** `tests/test_content_defaults.py` · level: integration (API + throwaway PostgreSQL)

### AC-06 — Listing and stats follow the declared filters

- **Given** content and calendar entries of several types and statuses
- **When** the owner lists by a filter (including `has_cta` and repeated values) or groups stats by a filter or a non-filter field
- **Then** only matching records are listed oldest first, stats count per value, and a non-filter field is refused with 422
- **Test:** `tests/test_content_queries.py` · level: integration (API + throwaway PostgreSQL)

### AC-07 — A patch bumps the version only when something changed

- **Given** a content piece at version 1
- **When** the owner patches a new status, then resends the same status
- **Then** the first patch gives version 2, the second keeps the version; a stale `expected_version` answers 409
- **Test:** `tests/test_content_queries.py::test_a_patch_that_changes_nothing_keeps_the_version` · level: integration (API + throwaway PostgreSQL)

### AC-08 — Numbers fit their columns

- **Given** an int field (PostgreSQL integer) or a real field
- **When** a client sends 2**31, or NaN / Infinity / 1e400 as raw JSON
- **Then** the API answers 422 naming the field (before: a 500 from PostgreSQL, or the value silently stored as null)
- **Test:** `tests/test_contract.py::test_numbers_fit_their_columns` · level: integration (API + throwaway PostgreSQL)

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| `POST /v1/content-series-episodes`, `PATCH /v1/content-series-episodes/{id}` | changed | `published_at` before `recorded_at` → `422 {"error": "invalid_value", "fields": ["published_at", "recorded_at"]}` |
| `cell.yaml` | changed | new resource key `ranges: [[recorded_at, published_at]]` on `content-series-episode` |

- **Data model / migration:** N/A — no schema change. Range rules are checked by the API on
  create and update; rows already stored are not rewritten.
- **Backward compatibility:** clients keep the same routes. A write that would store a range
  ending before it starts now gets `422 invalid_value` instead of `201/200`.

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Performance | N/A — no hot-path change beyond one comparison per declared range | — |
| Security / privacy | Same authorization, RLS and Sentry scrubbing as before | contract suite (`tests/test_contract.py`), `tests/test_sentry.py` |
| Reliability / observability | Reproducible image from `uv.lock`; failed inline publishes reach Sentry | image rehearsal before push; `test_inline_publish_failure_is_reported` |
| Accessibility / UX | N/A — API only | — |

## 6. Test plan (TDD)

- **Test levels:** integration tests against the FastAPI app with a throwaway local PostgreSQL
  (pgserver) and a fake platform; no hosted database or platform.
- **Test data:** generated in each test; no production data.
- **Coverage:** CI gate `coverage-threshold: "57"` (measured 59.84% on 2026-10-22, minus 2 points).
- **Not test-first (exceptions):** tests that pin behaviour the service already had
  (characterization tests, marked below) were written after the code by nature; tooling and
  config changes are covered by CI itself.

### Red / green log

| Scenario | Test | Red: commit / run + failure message | Green: commit / run | Refactor note |
|---|---|---|---|---|
| AC-01 | `tests/test_content_validation.py::test_an_episode_cannot_be_published_before_it_was_recorded` | 7cac7e7 · `.venv/bin/pytest -q tests/test_content_validation.py::test_an_episode_cannot_be_published_before_it_was_recorded` · `assert 201 == 422` | CI run of the pushed tip | none |
| AC-02 | `tests/test_content_validation.py::test_publishing_before_the_recording_is_refused_on_update` | 7cac7e7 · `.venv/bin/pytest -q tests/test_content_validation.py::test_publishing_before_the_recording_is_refused_on_update` · `assert 200 == 422` | CI run of the pushed tip | none |
| AC-03 | `tests/test_content_validation.py::test_the_calendar_knows_thread_and_carousel_but_not_playbook` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-04 | `tests/test_content_validation.py::test_a_reference_to_another_workspace_is_refused` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-05 | `tests/test_content_defaults.py` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-06 | `tests/test_content_queries.py` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-07 | `tests/test_content_queries.py::test_a_patch_that_changes_nothing_keeps_the_version` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-08 | `tests/test_contract.py::test_numbers_fit_their_columns` | c64bfba · `.venv/bin/pytest -q -k numbers_fit` · `psycopg.errors.NumericValueOutOfRange: integer out of range` | CI run of the pushed tip | none |

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Stored rows written before a range rule existed may already be inverted | a patch touching one of those dates is refused until both are fixed | owner | patches that do not touch the range still work |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-10-22 | Implemented with the Wave 2 baseline | all | pending owner |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Implemented (DoD) | Reviewer (checker) | Fresh Claude reviewer / 2026-10-22 | see Wave 2 report | CI run of the pushed tip |
| Implemented (DoD) | Approver | Owner | pending | Wave 2 report |

## Approval (2026-10-24)

| Field | Value |
|---|---|
| Checker | independent Claude reviewer subagent (`solo:solo-reviewer`, Sonnet, read-only, no maker context) |
| Approver | AI approval under the owner's process (approvals by the owner or AI with evidence; maker and checker are different agents). Recorded by Claude session oa-remainder on the owner's instruction "ทำที่เหลือให้หน่อย" (2026-10-24) |
| Verdict | **approved** |
| Tests run by the checker | .venv/bin/pytest -q --cov: 106 passed, 15 skipped |
| Evidence | test_content_validation.py, test_content_defaults.py, test_content_queries.py (has_cta, version bump, stale 409); numbers_fit 4 resources; gate 57. |
