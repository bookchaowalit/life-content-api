"""Shared helpers for the content domain tests."""

import uuid
from typing import Any

CONTENTS = "/v1/contents"
CALENDAR = "/v1/content-calendars"
EPISODES = "/v1/content-series-episodes"
METRICS = "/v1/content-series-episode-metrics"


def create_content(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    return client.post(
        CONTENTS, headers=owner, json={"title": "A content piece", **fields}
    )


def create_entry(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    return client.post(
        CALENDAR, headers=owner, json={"title": "A calendar entry", **fields}
    )


def create_episode(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {"series_slug": "daily-tips", "day_number": 1, "account_handle": "@book"}
    return client.post(EPISODES, headers=owner, json={**body, **fields})


def create_metric(client: Any, owner: dict[str, str], **fields: Any) -> Any:
    body = {"captured_at": "2026-10-10T08:00:00+00:00"}
    return client.post(METRICS, headers=owner, json={**body, **fields})


def another_workspace(harness: Any, platform: Any) -> dict[str, str]:
    """Headers of a second owner in a different workspace, with every permission."""
    actor, workspace = uuid.uuid4(), uuid.uuid4()
    platform.grants[actor] = set(harness.cell.permissions())
    headers: dict[str, str] = harness.token(actor, workspace)
    return headers
