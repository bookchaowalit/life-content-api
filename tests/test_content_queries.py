"""Listing, grouping and the lifecycle of the content resources."""

from content_helpers import (
    CALENDAR,
    CONTENTS,
    EPISODES,
    METRICS,
    create_content,
    create_entry,
    create_episode,
    create_metric,
)


def ids(response):
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def test_content_list_filters_by_type_status_and_niche(client, owner):
    blog = create_content(
        client, owner, content_type="blog", related_niche_id=11
    ).json()
    video = create_content(
        client, owner, content_type="video", status="draft", related_niche_id=12
    ).json()
    assert ids(
        client.get(CONTENTS, headers=owner, params={"content_type": "video"})
    ) == [video["id"]]
    assert ids(client.get(CONTENTS, headers=owner, params={"status": "idea"})) == [
        blog["id"]
    ]
    assert ids(
        client.get(CONTENTS, headers=owner, params={"related_niche_id": 12})
    ) == [video["id"]]


def test_a_filter_can_be_repeated_to_match_any_value(client, owner):
    blog = create_content(client, owner, content_type="blog").json()
    video = create_content(client, owner, content_type="video").json()
    create_content(client, owner, content_type="podcast")
    listed = client.get(
        CONTENTS,
        headers=owner,
        params=[("content_type", "blog"), ("content_type", "video")],
    )
    assert ids(listed) == [blog["id"], video["id"]]


def test_content_cannot_be_listed_by_a_field_that_is_not_a_filter(client, owner):
    refused = client.get(CONTENTS, headers=owner, params={"title": "x"})
    assert refused.status_code == 422
    assert refused.json()["detail"]["error"] == "unknown_filter"


def test_content_is_listed_oldest_first_and_newest_first_on_request(client, owner):
    first = create_content(client, owner, title="One").json()
    second = create_content(client, owner, title="Two").json()
    assert ids(client.get(CONTENTS, headers=owner)) == [first["id"], second["id"]]
    newest = client.get(CONTENTS, headers=owner, params={"order": "desc"})
    assert ids(newest) == [second["id"], first["id"]]


def test_stats_count_content_per_status(client, owner):
    create_content(client, owner)
    create_content(client, owner, status="draft")
    create_content(client, owner, status="draft")
    stats = client.get(
        f"{CONTENTS}/stats", headers=owner, params={"group_by": "status"}
    )
    assert stats.status_code == 200, stats.text
    assert stats.json()["groups"] == {"idea": 1, "draft": 2}


def test_stats_refuse_a_field_that_is_not_a_filter(client, owner):
    for path in (CONTENTS, CALENDAR, EPISODES, METRICS):
        stats = client.get(f"{path}/stats", headers=owner, params={"group_by": "id"})
        assert stats.status_code == 422, path


def test_calendar_filters_by_cta_status_and_type(client, owner):
    with_cta = create_entry(client, owner, has_cta=True, status="scheduled").json()
    plain = create_entry(client, owner, content_type="thread").json()
    assert ids(client.get(CALENDAR, headers=owner, params={"has_cta": "true"})) == [
        with_cta["id"]
    ]
    assert ids(client.get(CALENDAR, headers=owner, params={"has_cta": "false"})) == [
        plain["id"]
    ]
    assert ids(client.get(CALENDAR, headers=owner, params={"status": "scheduled"})) == [
        with_cta["id"]
    ]
    assert ids(
        client.get(CALENDAR, headers=owner, params={"content_type": "thread"})
    ) == [plain["id"]]


def test_calendar_filters_by_what_it_repurposes_and_which_content_it_serves(
    client, owner
):
    piece = create_content(client, owner).json()
    original = create_entry(
        client, owner, title="Original", related_content_id=piece["id"]
    ).json()
    clip = create_entry(
        client, owner, title="Clip", repurpose_from=original["id"]
    ).json()
    by_source = client.get(
        CALENDAR, headers=owner, params={"repurpose_from": original["id"]}
    )
    assert ids(by_source) == [clip["id"]]
    by_content = client.get(
        CALENDAR, headers=owner, params={"related_content_id": piece["id"]}
    )
    assert ids(by_content) == [original["id"]]


def test_stats_count_calendar_entries_per_content_type(client, owner):
    create_entry(client, owner)
    create_entry(client, owner, content_type="thread")
    create_entry(client, owner, content_type="thread")
    stats = client.get(
        f"{CALENDAR}/stats", headers=owner, params={"group_by": "content_type"}
    )
    assert stats.json()["groups"] == {"blog": 1, "thread": 2}


def test_episodes_filter_by_status_and_count_per_status(client, owner):
    create_episode(client, owner, day_number=1)
    recorded = create_episode(client, owner, day_number=2, status="recorded").json()
    listed = client.get(EPISODES, headers=owner, params={"status": "recorded"})
    assert ids(listed) == [recorded["id"]]
    stats = client.get(
        f"{EPISODES}/stats", headers=owner, params={"group_by": "status"}
    )
    assert stats.json()["groups"] == {"idea": 1, "recorded": 1}


def test_metrics_filter_by_episode(client, owner):
    one = create_episode(client, owner, day_number=1).json()
    two = create_episode(client, owner, day_number=2).json()
    metric = create_metric(client, owner, episode_id=one["id"], views=10).json()
    create_metric(client, owner, episode_id=two["id"], views=20)
    listed = client.get(METRICS, headers=owner, params={"episode_id": one["id"]})
    assert ids(listed) == [metric["id"]]
    stats = client.get(
        f"{METRICS}/stats", headers=owner, params={"group_by": "episode_id"}
    )
    assert stats.json()["groups"] == {str(one["id"]): 1, str(two["id"]): 1}


def test_a_changed_patch_bumps_the_version(client, owner):
    piece = create_content(client, owner).json()
    path = f"{CONTENTS}/{piece['id']}"
    published = client.patch(
        path, headers=owner, json={"status": "published", "views": 120}
    )
    assert published.status_code == 200, published.text
    assert published.json()["version"] == 2
    assert published.json()["views"] == 120
    assert published.json()["title"] == piece["title"]


def test_a_patch_that_changes_nothing_keeps_the_version(client, owner):
    piece = create_content(client, owner, status="draft").json()
    path = f"{CONTENTS}/{piece['id']}"
    same = client.patch(path, headers=owner, json={"status": "draft"})
    assert same.status_code == 200, same.text
    assert same.json()["version"] == 1
    assert same.json()["updated_at"] == piece["updated_at"]


def test_a_stale_expected_version_is_refused(client, owner):
    piece = create_content(client, owner).json()
    path = f"{CONTENTS}/{piece['id']}"
    assert (
        client.patch(path, headers=owner, json={"status": "draft"}).status_code == 200
    )
    stale = client.patch(
        path, headers=owner, json={"status": "review", "expected_version": 1}
    )
    assert stale.status_code == 409
    assert stale.json()["detail"] == {"error": "version_conflict", "version": 2}


def test_a_calendar_entry_moves_through_its_steps(client, owner):
    entry = create_entry(client, owner, title="Newsletter 12").json()
    path = f"{CALENDAR}/{entry['id']}"
    for version, status in enumerate(("researching", "drafting", "scheduled"), start=2):
        moved = client.patch(path, headers=owner, json={"status": status})
        assert moved.status_code == 200, moved.text
        assert moved.json()["version"] == version
    assert client.get(path, headers=owner).json()["status"] == "scheduled"


def test_a_deleted_content_piece_is_gone(client, owner):
    piece = create_content(client, owner).json()
    path = f"{CONTENTS}/{piece['id']}"
    assert client.delete(path, headers=owner).status_code == 204
    assert client.get(path, headers=owner).status_code == 404
    assert client.delete(path, headers=owner).status_code == 404


def test_content_with_calendar_entries_cannot_be_deleted(client, owner):
    piece = create_content(client, owner).json()
    entry = create_entry(client, owner, related_content_id=piece["id"]).json()
    refused = client.delete(f"{CONTENTS}/{piece['id']}", headers=owner)
    assert refused.status_code == 409, refused.text
    assert refused.json()["detail"] == {"error": "has_dependents"}
    assert client.delete(f"{CALENDAR}/{entry['id']}", headers=owner).status_code == 204
    assert client.delete(f"{CONTENTS}/{piece['id']}", headers=owner).status_code == 204


def test_an_entry_that_was_repurposed_cannot_be_deleted(client, owner):
    original = create_entry(client, owner, title="Original").json()
    clip = create_entry(
        client, owner, title="Clip", repurpose_from=original["id"]
    ).json()
    refused = client.delete(f"{CALENDAR}/{original['id']}", headers=owner)
    assert refused.status_code == 409, refused.text
    assert client.delete(f"{CALENDAR}/{clip['id']}", headers=owner).status_code == 204
    assert (
        client.delete(f"{CALENDAR}/{original['id']}", headers=owner).status_code == 204
    )


def test_an_episode_with_metrics_cannot_be_deleted(client, owner):
    episode = create_episode(client, owner).json()
    metric = create_metric(client, owner, episode_id=episode["id"]).json()
    refused = client.delete(f"{EPISODES}/{episode['id']}", headers=owner)
    assert refused.status_code == 409, refused.text
    assert client.delete(f"{METRICS}/{metric['id']}", headers=owner).status_code == 204
    assert (
        client.delete(f"{EPISODES}/{episode['id']}", headers=owner).status_code == 204
    )
