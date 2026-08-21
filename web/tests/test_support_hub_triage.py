"""Which feedback becomes a tracker issue, and which quietly does not.

A monitoring script exercising the live site opened ten identical "Love it"
issues in the support repository in one afternoon. Praise is worth having and
worth storing; it is not worth a ticket somebody has to triage, and a queue
full of it is where a real user's bug report goes to be overlooked.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
from acb_large_print_web.support_hub import (
    DEFAULT_ISSUE_CATEGORIES,
    load_support_hub_config,
    should_open_issue,
)


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    # Never reach the real tracker from a test, whatever the machine's
    # environment happens to carry.
    for name in (
        "SUPPORT_HUB_GITHUB_TOKEN",
        "FEEDBACK_GITHUB_TOKEN",
        "SUPPORT_HUB_ISSUE_CATEGORIES",
    ):
        monkeypatch.delenv(name, raising=False)
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


@pytest.fixture()
def filed(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Capture what would have been sent to GitHub."""
    import acb_large_print_web.routes.feedback as feedback_route

    calls: list[dict] = []

    def _fake(entry):
        calls.append(dict(entry))
        return (321, "https://github.com/Community-Access/support/issues/321", None)

    monkeypatch.setattr(feedback_route, "create_support_issue", _fake)
    return calls


def _rows(app: Flask) -> list[tuple]:
    conn = sqlite3.connect(str(Path(app.instance_path) / "feedback.db"))
    rows = conn.execute(
        "SELECT category, summary, github_sync_status, github_sync_error FROM feedback ORDER BY id"
    ).fetchall()
    conn.close()
    return rows


PRAISE = {
    "source_app": "GLOW",
    "category": "feedback",
    "rating": "excellent",
    "task": "fix",
    "summary": "fix",
    "message": "Love it",
}

BUG = {
    "source_app": "GLOW",
    "category": "bug",
    "rating": "poor",
    "task": "audit",
    "summary": "Audit crashed on a scanned PDF",
    "message": "Uploading a scanned PDF returns a 500 page.",
}


# ---------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------


def test_bug_reports_are_filed():
    assert should_open_issue({"category": "bug"})[0] is True


def test_praise_and_general_comments_are_not_filed():
    wanted, reason = should_open_issue({"category": "feedback"})

    assert wanted is False
    assert "not triaged" in reason


def test_the_triaged_categories_are_the_ones_that_need_a_person():
    assert set(DEFAULT_ISSUE_CATEGORIES) == {"bug", "accessibility", "regression", "support"}


def test_the_old_behaviour_is_one_environment_variable_away(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPPORT_HUB_ISSUE_CATEGORIES", "all")

    assert should_open_issue({"category": "feedback"})[0] is True


def test_the_list_can_be_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUPPORT_HUB_ISSUE_CATEGORIES", "bug")
    cfg = load_support_hub_config()

    assert cfg.issue_categories == ("bug",)
    assert should_open_issue({"category": "accessibility"}, cfg)[0] is False


# ---------------------------------------------------------------------------
# End to end through the form
# ---------------------------------------------------------------------------


def test_praise_is_kept_but_opens_no_issue(client, app: Flask, filed: list[dict]):
    resp = client.post("/feedback/", data=PRAISE)

    assert resp.status_code in (200, 302, 303)
    # The page says what happened rather than implying a broken configuration.
    body = resp.get_data(as_text=True)
    assert "only open a tracker ticket" in body
    assert "GitHub sync is not enabled" not in body
    rows = _rows(app)
    assert len(rows) == 1, "the feedback itself must still be stored"
    assert rows[0][0] == "feedback"
    assert rows[0][2] == "skipped"
    assert "not triaged" in (rows[0][3] or "")
    assert filed == []


def test_a_bug_report_still_reaches_the_tracker(client, app: Flask, filed: list[dict]):
    client.post("/feedback/", data=BUG)

    rows = _rows(app)
    assert rows[0][2] == "synced"
    assert len(filed) == 1
    assert filed[0]["summary"] == "Audit crashed on a scanned PDF"


def test_the_same_report_twice_only_opens_one_issue(client, app: Flask, filed: list[dict]):
    client.post("/feedback/", data=BUG)
    client.post("/feedback/", data=BUG)

    rows = _rows(app)
    assert len(rows) == 2, "both submissions are still recorded"
    assert rows[0][2] == "synced"
    assert rows[1][2] == "skipped"
    assert "already filed" in (rows[1][3] or "")
    assert len(filed) == 1


def test_a_different_report_is_not_treated_as_a_duplicate(client, app: Flask, filed: list[dict]):
    client.post("/feedback/", data=BUG)
    other = dict(BUG, summary="Fix dropped the footer", message="The footer vanished after fixing.")
    client.post("/feedback/", data=other)

    assert len(filed) == 2


def test_a_monitor_hammering_the_form_cannot_flood_the_queue(client, app: Flask, filed: list[dict]):
    """Ten identical submissions, which is what actually happened."""
    for _ in range(10):
        client.post("/feedback/", data=PRAISE)

    assert filed == []
    assert len(_rows(app)) == 10
