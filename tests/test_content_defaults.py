"""Defaults of each content resource and the rules that are NOT constraints."""

import pytest
from content_helpers import (
    CONTENTS,
    create_content,
    create_entry,
    create_episode,
    create_metric,
)


def test_new_content_starts_as_an_idea_with_zero_counters(client, owner):
    response = create_content(client, owner, title="Pricing post")
    assert response.status_code == 201, response.text
    piece = response.json()
    assert piece["status"] == "idea"
    assert piece["views"] == 0
    assert piece["shares"] == 0
    assert piece["leads_generated"] == 0
    assert piece["content_type"] is None
    assert piece["version"] == 1


def test_new_calendar_entry_is_a_blog_idea_with_priority_3(client, owner):
    response = create_entry(client, owner, title="Launch week")
    assert response.status_code == 201, response.text
    entry = response.json()
    assert entry["content_type"] == "blog"
    assert entry["status"] == "idea"
    assert entry["priority"] == 3
    assert entry["word_count"] == 0
    assert entry["has_cta"] is False
    assert entry["views"] == 0
    assert entry["engagement"] == 0
    assert entry["leads_generated"] == 0
    assert entry["repurpose_from"] is None
    assert entry["version"] == 1


def test_new_episode_is_an_idea_for_tiktok(client, owner):
    response = create_episode(client, owner, series_slug="empire-diary", day_number=7)
    assert response.status_code == 201, response.text
    episode = response.json()
    assert episode["platform"] == "tiktok"
    assert episode["status"] == "idea"
    assert episode["day_number"] == 7
    assert episode["version"] == 1


def test_a_metric_is_manual_unless_its_source_is_given(client, owner):
    episode = create_episode(client, owner).json()
    manual = create_metric(client, owner, episode_id=episode["id"])
    assert manual.status_code == 201, manual.text
    assert manual.json()["source"] == "manual"
    assert manual.json()["views"] is None
    scraped = create_metric(client, owner, episode_id=episode["id"], source="api")
    assert scraped.json()["source"] == "api"


def test_the_same_title_can_be_used_by_several_pieces(client, owner):
    first = create_content(client, owner, title="Weekly notes")
    second = create_content(client, owner, title="Weekly notes")
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_an_episode_can_get_a_metric_snapshot_every_day(client, owner):
    episode = create_episode(client, owner).json()
    for day in ("2026-10-10", "2026-10-11"):
        snapshot = create_metric(
            client,
            owner,
            episode_id=episode["id"],
            captured_at=f"{day}T08:00:00+00:00",
            views=100,
        )
        assert snapshot.status_code == 201, snapshot.text


def test_content_keeps_the_old_id_when_it_is_imported(client, owner):
    imported = client.post(
        CONTENTS, headers=owner, json={"title": "Old post", "legacy_id": 4242}
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["id"] == 4242
    assert imported.json()["legacy_id"] == 4242
    again = client.post(
        CONTENTS, headers=owner, json={"title": "Old post", "legacy_id": 4242}
    )
    assert again.status_code == 409


@pytest.mark.xfail(
    strict=True,
    reason="cellkit app.write does not catch NumericValueOutOfRange: a counter above "
    "2147483647 ends in a 500 instead of a 422",
)
def test_a_counter_above_the_integer_range_is_refused_not_a_server_error(client, owner):
    response = create_content(client, owner, views=2**31)
    assert response.status_code == 422
