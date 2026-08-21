"""Per-participant AI budgets, and what happens when one runs out.

Thirty people on one house key for seven hours is a spend profile the app has
never seen. The failure this prevents is one participant in a retry loop at
2 PM taking the room's AI down for everybody. Equally important is the
behaviour at the cap: a doorway to the copy-a-prompt path, never a wall.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
from acb_large_print_web.workshop_ai_budget import (
    over_budget,
    participant_calls,
    record_call,
    session_calls,
    session_usage,
)
from acb_large_print_web.workshop_store import ensure_session

CODE = "budgetdemo"
NOW = "2026-11-05T14:00:00+00:00"


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setenv("GLOW_WORKSHOP_AI_PARTICIPANT_CAP", "3")
    monkeypatch.setenv("GLOW_WORKSHOP_AI_SESSION_CAP", "5")
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    with application.app_context():
        ensure_session(CODE, title="GLOW Workshop Demo", event_name="AHG")
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _join(client, name: str = "Rowan") -> str:
    """Join, and hand back the participant key the cookie now carries."""
    client.post("/workshop/", data={"action": "join", "session_code": CODE, "display_name": name})
    return client.get_cookie("glow_workshop_participant").value


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------


def test_calls_accumulate_per_participant_and_per_room(app: Flask):
    with app.app_context():
        record_call(CODE, "alex", now=NOW)
        record_call(CODE, "alex", now=NOW)
        record_call(CODE, "sam", now=NOW)

        assert participant_calls(CODE, "alex") == 2
        assert participant_calls(CODE, "sam") == 1
        assert session_calls(CODE) == 3


def test_one_participant_cannot_spend_the_rooms_allowance(app: Flask):
    with app.app_context():
        for _ in range(3):
            record_call(CODE, "alex", now=NOW)

        assert over_budget(CODE, "alex") == "participant"
        # Their neighbour is unaffected.
        assert over_budget(CODE, "sam") == ""


def test_the_room_itself_has_a_ceiling(app: Flask):
    with app.app_context():
        record_call(CODE, "alex", now=NOW)
        record_call(CODE, "alex", now=NOW)
        record_call(CODE, "sam", now=NOW)
        record_call(CODE, "sam", now=NOW)
        record_call(CODE, "kim", now=NOW)

        # Nobody is individually over three, but the room is at five.
        assert over_budget(CODE, "kim") == "session"


def test_a_cap_of_zero_means_no_cap(app: Flask, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GLOW_WORKSHOP_AI_PARTICIPANT_CAP", "0")
    monkeypatch.setenv("GLOW_WORKSHOP_AI_SESSION_CAP", "0")
    with app.app_context():
        for _ in range(50):
            record_call(CODE, "alex", now=NOW)

        assert over_budget(CODE, "alex") == ""


def test_a_mistyped_cap_falls_back_to_the_default_rather_than_zero(
    app: Flask, monkeypatch: pytest.MonkeyPatch
):
    """A typo in an environment variable must not switch the room's AI off."""
    monkeypatch.setenv("GLOW_WORKSHOP_AI_PARTICIPANT_CAP", "lots")
    with app.app_context():
        from acb_large_print_web.workshop_ai_budget import (
            DEFAULT_PARTICIPANT_CAP,
            participant_cap,
        )

        assert participant_cap() == DEFAULT_PARTICIPANT_CAP


# ---------------------------------------------------------------------------
# What the facilitator sees
# ---------------------------------------------------------------------------


def test_the_facilitator_sees_usage_before_the_afternoon(app: Flask, client, monkeypatch):
    monkeypatch.setenv("GLOW_WORKSHOP_FACILITATOR_KEY", "key")
    with app.app_context():
        record_call(CODE, "alex", now=NOW)
        record_call(CODE, "alex", now=NOW)
        record_call(CODE, "sam", now=NOW)

        usage = session_usage(CODE)
        assert usage["participants"] == 2
        assert usage["total_calls"] == 3
        assert usage["busiest"] == 2
        assert usage["participant_cap"] == 3

    client.post(f"/workshop/session/{CODE}/facilitator/unlock", data={"facilitator_key": "key"})
    page = client.get(f"/workshop/session/{CODE}/facilitator").get_data(as_text=True)

    assert "Built-in AI usage" in page
    assert "Calls used by this room: 3" in page


# ---------------------------------------------------------------------------
# The request path
# ---------------------------------------------------------------------------


def test_reading_pages_costs_nothing(client, app: Flask):
    key = _join(client)
    client.get("/alt-text/")
    client.get(f"/workshop/session/{CODE}/activity/lab_alt_text_decision")

    with app.app_context():
        assert participant_calls(CODE, key) == 0


def test_someone_outside_a_workshop_is_never_budgeted(client, app: Flask):
    """The cap belongs to the room, not to the whole site."""
    for _ in range(10):
        client.post("/alt-text/", data={})

    with app.app_context():
        assert session_calls(CODE) == 0


def test_reaching_the_cap_offers_the_copy_a_prompt_path(client, app: Flask):
    key = _join(client)
    with app.app_context():
        for _ in range(3):
            record_call(CODE, key, now=NOW)

    resp = client.post("/alt-text/", data={})
    body = resp.get_data(as_text=True)

    assert resp.status_code == 429
    assert "AI limit reached" in body
    assert "ChatGPT" in body
    assert "no key, no install" in body or "needs no key" in body
    assert f"/workshop/session/{CODE}/me" in body
    # Nothing is broken and the page says so.
    assert "Nothing is lost" in body
