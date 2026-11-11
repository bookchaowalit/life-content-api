"""SPEC-003: a text field may carry an anchored pattern, enforced by the API and by PostgreSQL."""

from __future__ import annotations

import pytest

from cellkit import sqlgen
from cellkit.app import models
from cellkit.spec import SpecError, parse

SLUG = "^[a-z0-9][a-z0-9-]{0,9}$"


def cell_with(field: dict) -> object:
    return parse(
        {"cell": "kit", "resources": {"tag": {"fields": {"key": field}}}},
    )


def test_a_pattern_becomes_a_check_constraint():
    cell = cell_with({"type": "text", "required": True, "pattern": SLUG})
    key = cell.resource("tag").fields[0]  # type: ignore[attr-defined]
    assert key.pattern == SLUG
    assert f"key ~ '{SLUG}'" in sqlgen.column(cell, key)  # type: ignore[arg-type]


def test_the_api_model_refuses_a_value_that_does_not_match():
    cell = cell_with({"type": "text", "pattern": SLUG})
    create, _ = models(cell.resource("tag"))  # type: ignore[attr-defined]
    assert create(key="ok-1").key == "ok-1"  # type: ignore[call-arg, attr-defined]
    for bad in ("Not Ok", "-lead", "a" * 11, "ok-1\n"):
        with pytest.raises(ValueError):
            create(key=bad)  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ({"type": "int", "pattern": SLUG}, "text field"),
        ({"type": "text", "pattern": 5}, "text field"),
        ({"type": "text", "pattern": "[a-z]+"}, "anchored"),
        ({"type": "text", "pattern": "^a'b$"}, "quote"),
        ({"type": "text", "pattern": "^(a$"}, "invalid pattern"),
    ],
)
def test_a_bad_pattern_is_refused_when_the_spec_loads(field, message):
    with pytest.raises(SpecError, match=message):
        cell_with(field)
