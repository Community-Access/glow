"""Pre-flight: is this deployment ready to run a workshop day?

The answer used to live in four places -- the admin queue for mail, the
container environment for the feature flags, and a JSON file for the
conference code -- so nobody could see it at once. One screen, one answer,
and nothing secret on it.

The house AI and its budget subsystem were removed on 21 September 2026
(plan.md, L1). These tests also hold that line: pre-flight must not grow an
AI row back, because the workshop no longer has an AI resource to manage.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
from acb_large_print_web.workshop_store import ensure_session

CODE = "preflightdemo"
FACILITATOR_KEY = "unlock-me"
NOW = "2026-11-05T14:00:00+00:00"


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setenv("GLOW_WORKSHOP_FACILITATOR_KEY", FACILITATOR_KEY)
    monkeypatch.delenv("WORKSHOP_CONFERENCE_CODES_JSON", raising=False)
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    with application.app_context():
        ensure_session(CODE, title="Accessibility Agents in Action", event_name="AHG")
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _unlock(client) -> None:
    client.post(
        f"/workshop/session/{CODE}/facilitator/unlock",
        data={"facilitator_key": FACILITATOR_KEY},
    )


def _join(client, name: str = "Rowan") -> str:
    client.post("/workshop/", data={"action": "join", "session_code": CODE, "display_name": name})
    return client.get_cookie("glow_workshop_participant").value


# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------


def test_preflight_is_closed_to_anyone_without_the_key(client):
    resp = client.get(f"/workshop/session/{CODE}/preflight")
    assert resp.status_code == 403
    assert "Facilitator access required" in resp.get_data(as_text=True)


def test_the_deployment_wide_page_is_admin_only(client):
    assert client.get("/workshop/preflight").status_code == 404


def test_preflight_names_every_setting_the_day_depends_on(client):
    _unlock(client)
    body = client.get(f"/workshop/session/{CODE}/preflight").get_data(as_text=True)
    for label in (
        "Workshop Mode",
        "Shared gallery",
        "Peer feedback",
        "Facilitator key",
        "Conference access code",
        "Outbound mail (Postmark)",
    ):
        assert label in body


def test_preflight_never_prints_a_secret(client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-super-secret-value")
    _unlock(client)
    body = client.get(f"/workshop/session/{CODE}/preflight").get_data(as_text=True)
    assert "sk-super-secret-value" not in body
    assert FACILITATOR_KEY not in body


def test_preflight_has_no_ai_row_to_grow_back(client, monkeypatch):
    """The workshop has no AI resource to manage. Keep it that way."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-not-a-real-key")
    _unlock(client)
    body = client.get(f"/workshop/session/{CODE}/preflight").get_data(as_text=True).lower()

    for word in ("openrouter", "built-in ai", "ai cap", "participant cap", "spend"):
        assert word not in body, f"pre-flight mentions {word!r}"
