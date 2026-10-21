"""What the content cell refuses: unknown kinds, missing fields, bad dates, dangling references."""

from content_helpers import (
    CALENDAR,
    CONTENTS,
    EPISODES,
    METRICS,
    another_workspace,
    create_content,
    create_entry,
    create_episode,
    create_metric,
)


def test_a_content_piece_needs_a_title(client, owner):
    response = client.post(CONTENTS, headers=owner, json={"status": "draft"})
    assert response.status_code == 422


def test_a_content_title_cannot_be_empty(client, owner):
    assert create_content(client, owner, title="").status_code == 422


def test_content_type_must_be_a_known_kind(client, owner):
    assert create_content(client, owner, content_type="hologram").status_code == 422
    assert create_content(client, owner, content_type="playbook").status_code == 201


def test_content_status_must_be_a_known_stage(client, owner):
    assert create_content(client, owner, status="scheduled").status_code == 422
    assert create_content(client, owner, status="published").status_code == 201


def test_published_at_must_be_a_timestamp(client, owner):
    assert create_content(client, owner, published_at="next week").status_code == 422


def test_a_counter_must_be_a_whole_number(client, owner):
    assert create_content(client, owner, views="many").status_code == 422
    assert create_content(client, owner, shares=1.5).status_code == 422


def test_a_content_piece_refuses_fields_it_does_not_have(client, owner):
    assert create_content(client, owner, colour="red").status_code == 422


def test_a_title_cannot_be_cleared_on_update(client, owner):
    piece = create_content(client, owner).json()
    cleared = client.patch(
        f"{CONTENTS}/{piece['id']}", headers=owner, json={"title": None}
    )
    assert cleared.status_code == 422, cleared.text
    assert cleared.json()["detail"] == {"error": "invalid_value", "fields": ["title"]}


def test_the_calendar_knows_thread_and_carousel_but_not_playbook(client, owner):
    assert create_entry(client, owner, content_type="thread").status_code == 201
    assert create_entry(client, owner, content_type="carousel").status_code == 201
    assert create_entry(client, owner, content_type="playbook").status_code == 422


def test_a_calendar_status_must_be_a_known_step(client, owner):
    assert create_entry(client, owner, status="approved").status_code == 422
    assert create_entry(client, owner, status="killed").status_code == 201


def test_a_calendar_entry_needs_a_title(client, owner):
    response = client.post(CALENDAR, headers=owner, json={"topic": "Pricing"})
    assert response.status_code == 422


def test_scheduled_date_must_be_a_calendar_date(client, owner):
    assert create_entry(client, owner, scheduled_date="31/10/2026").status_code == 422
    assert create_entry(client, owner, scheduled_date="2026-10-31").status_code == 201


def test_has_cta_must_be_true_or_false(client, owner):
    assert create_entry(client, owner, has_cta="maybe").status_code == 422


def test_an_entry_can_only_repurpose_an_existing_entry(client, owner):
    refused = create_entry(client, owner, repurpose_from=987654321)
    assert refused.status_code == 422, refused.text
    assert refused.json()["detail"] == {"error": "reference_not_found"}


def test_a_reference_must_be_a_positive_id(client, owner):
    assert create_entry(client, owner, related_content_id=0).status_code == 422
    assert create_entry(client, owner, repurpose_from=-3).status_code == 422


def test_an_entry_can_only_point_at_an_existing_content_piece(client, owner):
    refused = create_entry(client, owner, related_content_id=987654321)
    assert refused.status_code == 422, refused.text
    assert refused.json()["detail"] == {"error": "reference_not_found"}


def test_a_reference_to_another_workspace_is_refused(client, owner, harness, platform):
    stranger = another_workspace(harness, platform)
    foreign_piece = create_content(client, stranger).json()
    foreign_entry = create_entry(client, stranger).json()
    pointing_at_content = create_entry(
        client, owner, related_content_id=foreign_piece["id"]
    )
    assert pointing_at_content.status_code == 422, pointing_at_content.text
    pointing_at_entry = create_entry(client, owner, repurpose_from=foreign_entry["id"])
    assert pointing_at_entry.status_code == 422, pointing_at_entry.text


def test_an_episode_needs_series_day_and_account(client, owner):
    base = {"series_slug": "daily-tips", "day_number": 1, "account_handle": "@book"}
    for missing in base:
        body = {k: v for k, v in base.items() if k != missing}
        response = client.post(EPISODES, headers=owner, json=body)
        assert response.status_code == 422, missing


def test_an_episode_day_must_be_a_whole_number(client, owner):
    assert create_episode(client, owner, day_number="first").status_code == 422


def test_an_episode_status_must_be_a_known_step(client, owner):
    assert create_episode(client, owner, status="published").status_code == 422
    for status in ("published_user_confirmed", "published_verified"):
        assert create_episode(client, owner, status=status).status_code == 201


def test_planned_date_must_be_a_calendar_date(client, owner):
    assert create_episode(client, owner, planned_date="soon").status_code == 422


def test_a_metric_needs_an_episode_and_a_capture_time(client, owner):
    episode = create_episode(client, owner).json()
    valid = create_metric(client, owner, episode_id=episode["id"])
    assert valid.status_code == 201, valid.text
    missing_time = client.post(
        METRICS, headers=owner, json={"episode_id": episode["id"]}
    )
    assert missing_time.status_code == 422
    missing_episode = create_metric(client, owner)
    assert missing_episode.status_code == 422


def test_a_metric_can_only_belong_to_an_existing_episode(client, owner):
    refused = create_metric(client, owner, episode_id=987654321)
    assert refused.status_code == 422, refused.text
    assert refused.json()["detail"] == {"error": "reference_not_found"}


def test_a_metric_cannot_belong_to_an_episode_of_another_workspace(
    client, owner, harness, platform
):
    stranger = another_workspace(harness, platform)
    foreign_episode = create_episode(client, stranger).json()
    refused = create_metric(client, owner, episode_id=foreign_episode["id"])
    assert refused.status_code == 422, refused.text


def test_a_metric_count_must_be_a_whole_number(client, owner):
    episode = create_episode(client, owner).json()
    refused = create_metric(client, owner, episode_id=episode["id"], likes="lots")
    assert refused.status_code == 422


def test_an_episode_cannot_be_published_before_it_was_recorded(client, owner):
    backwards = create_episode(
        client,
        owner,
        recorded_at="2026-10-12T09:00:00+00:00",
        published_at="2026-10-11T09:00:00+00:00",
    )
    assert backwards.status_code == 422, backwards.text
    assert backwards.json()["detail"] == {
        "error": "invalid_value",
        "fields": ["published_at", "recorded_at"],
    }
    same_moment = create_episode(
        client,
        owner,
        recorded_at="2026-10-12T09:00:00+00:00",
        published_at="2026-10-12T09:00:00+00:00",
    )
    assert same_moment.status_code == 201, same_moment.text


def test_publishing_before_the_recording_is_refused_on_update(client, owner):
    episode = create_episode(
        client, owner, recorded_at="2026-10-12T09:00:00+00:00"
    ).json()
    path = f"{EPISODES}/{episode['id']}"
    refused = client.patch(
        path, headers=owner, json={"published_at": "2026-10-01T09:00:00+00:00"}
    )
    assert refused.status_code == 422, refused.text
    assert client.get(path, headers=owner).json()["published_at"] is None
    # A patch that touches neither moment still works.
    renamed = client.patch(path, headers=owner, json={"title": "Day one"})
    assert renamed.status_code == 200, renamed.text
