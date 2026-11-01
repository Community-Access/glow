"""The AHG 2026 room check-in at /ahg/check-in.

Asked once on the day, so it must take two taps, ask for no name, tell a
screen reader user exactly what is missing, put help requests at the top of
the helpers' page, and show nothing to anyone without the key.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask
from markupsafe import escape

from acb_large_print_web.app import create_app
from acb_large_print_web.routes.ahg_checkin import NEEDS_HELP

KEY = "test-key-for-the-room"


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def test_the_form_asks_two_questions_and_no_name(client):
    body = client.get("/ahg/check-in").get_data(as_text=True)
    assert body.count("<fieldset") == 2
    assert "<legend>How is it going? (needed)</legend>" in body
    assert 'name="name"' not in body and 'name="email"' not in body
    assert '<label for="q-seat">' in body


def test_a_missing_answer_is_named_and_focused(client):
    resp = client.post("/ahg/check-in", data={"path": "VS Code on my computer"})
    assert resp.status_code == 400
    body = resp.get_data(as_text=True)
    assert 'role="alert"' in body
    message = escape('Answer "How is it going?"')
    assert f'<a href="#q-how">{message}</a>' in body
    assert 'value="VS Code on my computer" checked' in body


def test_a_help_request_says_a_helper_is_coming(client):
    resp = client.post("/ahg/check-in", data={"how": NEEDS_HELP, "path": "VS Code at vscode.dev", "seat": "Table 4"})
    assert resp.status_code == 303
    body = client.get(resp.headers["Location"]).get_data(as_text=True)
    assert "A helper is on the way" in body


def test_results_need_the_key(client, monkeypatch):
    monkeypatch.delenv("AHG_SURVEY_KEY", raising=False)
    assert client.get("/ahg/check-in/results").status_code == 404
    monkeypatch.setenv("AHG_SURVEY_KEY", KEY)
    assert client.get("/ahg/check-in/results?key=wrong").status_code == 403


def test_help_requests_lead_the_results(client, monkeypatch):
    monkeypatch.setenv("AHG_SURVEY_KEY", KEY)
    client.post("/ahg/check-in", data={"how": "On track", "path": "VS Code on my computer"})
    client.post(
        "/ahg/check-in",
        data={"how": NEEDS_HELP, "path": "A browser, with an AI assistant", "seat": "Table 7, by the door"},
    )
    resp = client.get(f"/ahg/check-in/results?key={KEY}")
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "no-store"
    body = resp.get_data(as_text=True)
    assert "2 check-ins" in body
    assert body.index("Table 7, by the door") < body.index('<caption id="t-how">')
    assert '<tr><th scope="row">On track</th><td>1</td></tr>' in body
