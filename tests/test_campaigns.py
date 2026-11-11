"""SPEC-003: marketing campaigns and the UTM key that ties a CRM lead to them."""

import pytest
from content_helpers import (
    CALENDAR,
    CAMPAIGNS,
    CONTENTS,
    another_workspace,
    create_campaign,
    create_content,
    create_entry,
)


# AC-01
@pytest.mark.parametrize("missing", ["name", "channel", "utm_campaign"])
def test_a_campaign_needs_a_name_a_channel_and_a_utm_key(client, owner, missing):
    body = {"name": "Finance launch", "channel": "pseo", "utm_campaign": "fin-launch"}
    del body[missing]
    assert client.post(CAMPAIGNS, headers=owner, json=body).status_code == 422


def test_the_channel_must_be_a_known_one(client, owner):
    assert create_campaign(client, owner, channel="billboard").status_code == 422
    assert create_campaign(client, owner, channel="social_paid").status_code == 201


# AC-02
@pytest.mark.parametrize(
    "key", ["Fin Launch", "-fin", "fin/launch", "fin?x=1", "a" * 65, "สินค้า"]
)
def test_the_utm_key_is_a_lowercase_slug(client, owner, key):
    assert create_campaign(client, owner, utm_campaign=key).status_code == 422


@pytest.mark.parametrize("name", ["utm_source", "utm_medium"])
def test_utm_source_and_medium_are_slugs_too(client, owner, name):
    assert create_campaign(client, owner, **{name: "Face Book"}).status_code == 422
    ok = create_campaign(client, owner, utm_campaign=f"ok-{name}", **{name: "facebook"})
    assert ok.status_code == 201


def test_the_utm_key_is_unique_per_workspace(client, owner, harness, platform):
    assert create_campaign(client, owner, utm_campaign="dup-key").status_code == 201
    assert create_campaign(client, owner, utm_campaign="dup-key").status_code == 409
    other = another_workspace(harness, platform)
    assert create_campaign(client, other, utm_campaign="dup-key").status_code == 201


# AC-03
def test_a_campaign_cannot_end_before_it_starts(client, owner):
    late = create_campaign(
        client,
        owner,
        utm_campaign="late",
        start_date="2026-12-02",
        end_date="2026-12-01",
    )
    assert late.status_code == 422
    same = create_campaign(
        client,
        owner,
        utm_campaign="same",
        start_date="2026-12-01",
        end_date="2026-12-01",
    )
    assert same.status_code == 201


@pytest.mark.parametrize("name", ["budget_thb", "spend_thb"])
def test_money_is_whole_non_negative_baht(client, owner, name):
    assert create_campaign(client, owner, **{name: -1}).status_code == 422
    assert create_campaign(client, owner, **{name: 100_000_001}).status_code == 422
    assert create_campaign(client, owner, **{name: 12.5}).status_code == 422
    ok = create_campaign(client, owner, utm_campaign=f"money-{name}", **{name: 5000})
    assert ok.status_code == 201
    assert ok.json()[name] == 5000


# AC-04
def test_status_defaults_to_planned_and_is_a_known_stage(client, owner):
    created = create_campaign(client, owner, utm_campaign="status-default")
    assert created.json()["status"] == "planned"
    assert create_campaign(client, owner, status="live").status_code == 422
    assert (
        create_campaign(client, owner, utm_campaign="k", status="killed").status_code
        == 201
    )


def test_campaigns_can_be_listed_by_channel_and_status(client, owner):
    create_campaign(
        client, owner, utm_campaign="by-email", channel="email", status="active"
    )
    found = client.get(
        CAMPAIGNS, headers=owner, params={"channel": "email", "status": "active"}
    )
    assert found.status_code == 200
    keys = {row["utm_campaign"] for row in found.json()["items"]}
    assert "by-email" in keys


# AC-05
def test_content_and_calendar_entries_can_serve_a_campaign(client, owner):
    campaign = create_campaign(client, owner, utm_campaign="served").json()["id"]
    piece = create_content(client, owner, campaign_id=campaign)
    entry = create_entry(client, owner, campaign_id=campaign)
    assert piece.status_code == 201
    assert piece.json()["campaign_id"] == campaign
    assert entry.status_code == 201
    assert entry.json()["campaign_id"] == campaign
    listed = client.get(
        CONTENTS, headers=owner, params={"campaign_id": campaign}
    ).json()
    assert [row["id"] for row in listed["items"]] == [piece.json()["id"]]
    listed = client.get(
        CALENDAR, headers=owner, params={"campaign_id": campaign}
    ).json()
    assert [row["id"] for row in listed["items"]] == [entry.json()["id"]]


def test_a_dangling_or_foreign_campaign_is_refused(client, owner, harness, platform):
    assert create_content(client, owner, campaign_id=999_999_999).status_code == 422
    other = another_workspace(harness, platform)
    foreign = create_campaign(client, other, utm_campaign="foreign").json()["id"]
    assert create_entry(client, owner, campaign_id=foreign).status_code == 422


def test_a_campaign_still_served_by_content_cannot_be_deleted(client, owner):
    campaign = create_campaign(client, owner, utm_campaign="kept").json()["id"]
    create_content(client, owner, campaign_id=campaign)
    assert client.delete(f"{CAMPAIGNS}/{campaign}", headers=owner).status_code == 409
