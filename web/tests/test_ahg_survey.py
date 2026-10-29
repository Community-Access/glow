"""The AHG 2026 pre-workshop survey at /ahg/survey.

It is sent to every registered participant, so it must open without a
consent wall, keep every answer it is given, refuse nothing a person may
leave blank, tell a screen reader user exactly what to fix, and show the
answers only to someone holding the key.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

import pytest
from flask import Flask
from markupsafe import escape

from acb_large_print_web.app import create_app
from acb_large_print_web.routes.ahg_survey import QUESTIONS


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _minimal() -> dict[str, str]:
    return {
        "name": "Maria Alvarez",
        "email": "maria@example.edu",
        "role": "Alternate formats",
        "path": "The browser path, with an AI assistant",
    }


def test_the_survey_opens_without_a_consent_wall(client):
    page = client.get("/ahg/survey")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "<h1>Before the day: a short survey</h1>" in html
    assert 'name="csrf_token"' in html


def test_every_question_is_on_the_form_with_a_name(client):
    html = client.get("/ahg/survey").get_data(as_text=True)
    for q in QUESTIONS:
        assert f'id="q-{q.key}"' in html, q.key
        for option in q.options:
            assert f'value="{escape(option)}"' in html, (q.key, option)


def test_every_choice_group_is_a_fieldset_and_every_field_has_a_label(client):
    html = client.get("/ahg/survey").get_data(as_text=True)
    assert html.count("<fieldset") == sum(q.kind in ("radio", "check") for q in QUESTIONS)
    assert html.count("<legend>") == html.count("<fieldset")
    for q in QUESTIONS:
        if q.kind not in ("radio", "check"):
            assert f'<label for="q-{q.key}">' in html, q.key
    # Every input in a group sits inside its own label.
    for match in re.finditer(r'<input type="(radio|checkbox)"', html):
        assert html.rfind("<label>", 0, match.start()) > html.rfind("</label>", 0, match.start())


def test_the_four_needed_questions_are_marked(client):
    html = client.get("/ahg/survey").get_data(as_text=True)
    assert html.count("(needed)") == sum(q.required for q in QUESTIONS) == 4
    assert [q.key for q in QUESTIONS if q.required] == ["name", "email", "role", "path"]
    assert html.count('aria-required="true"') == 2  # the two text fields; groups say it in the legend


def test_your_details_come_first_with_github_help_links(client):
    html = client.get("/ahg/survey").get_data(as_text=True)
    assert [q.key for q in QUESTIONS[:3]] == ["name", "email", "github"]
    assert html.index('id="q-name"') < html.index('id="q-role"')
    assert 'href="https://github.com/signup"' in html
    assert "creating-an-account-on-github" in html
    assert "(opens in a new tab)" in html
    assert 'autocomplete="username"' in html and 'autocomplete="email"' in html


def test_a_minimal_answer_is_saved_and_thanked(client):
    response = client.post("/ahg/survey", data=_minimal())
    assert response.status_code == 303
    assert response.headers["Location"].endswith("/ahg/survey/thanks")
    assert client.get("/ahg/survey/thanks").status_code == 200


def test_missing_answers_come_back_with_a_focusable_error_summary(client):
    response = client.post("/ahg/survey", data={"role": "Faculty"})
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert 'role="alert"' in html and 'id="error-summary"' in html
    assert '<a href="#q-path">' in html
    assert 'id="e-path"' in html and 'aria-describedby="h-path e-path"' in html
    assert "<title>Check your answers:" in html
    # What was already answered is kept.
    assert 'value="Faculty" checked' in html


def test_name_and_email_are_needed_and_checked(client):
    data = {**_minimal(), "email": "not an address"}
    del data["name"]
    html = client.post("/ahg/survey", data=data).get_data(as_text=True)
    assert '<a href="#q-name">' in html and '<a href="#q-email">' in html
    assert "Check your email address" in html
    assert 'aria-invalid="true"' in html


@pytest.mark.parametrize("name", ["accesswatch", "@accesswatch", "a-b-c", "A1"])
def test_good_github_usernames_are_kept(client, monkeypatch, name):
    monkeypatch.setenv("AHG_SURVEY_KEY", "k")
    assert client.post("/ahg/survey", data={**_minimal(), "github": name}).status_code == 303
    rows = list(csv.DictReader(io.StringIO(client.get("/ahg/survey/results.csv?key=k").get_data(as_text=True))))
    assert rows[-1]["github"] == name.removeprefix("@")


@pytest.mark.parametrize("name", ["-lead", "trail-", "two--hyphens", "has space", "under_score", "x" * 40])
def test_bad_github_usernames_are_refused(client, name):
    response = client.post("/ahg/survey", data={**_minimal(), "github": name})
    assert response.status_code == 400
    assert "Check your GitHub username" in response.get_data(as_text=True)


def test_unknown_options_are_dropped_not_stored(app, client):
    data = {**_minimal(), "tools": ["A screen reader", "<script>"], "card": "Made up"}
    client.post("/ahg/survey", data=data)
    import os

    os.environ["AHG_SURVEY_KEY"] = "k"
    try:
        rows = list(csv.DictReader(io.StringIO(client.get("/ahg/survey/results.csv?key=k").get_data(as_text=True))))
    finally:
        del os.environ["AHG_SURVEY_KEY"]
    assert rows[0]["tools"] == "A screen reader"
    assert rows[0]["card"] == ""


def test_results_are_hidden_without_the_key(client, monkeypatch):
    monkeypatch.delenv("AHG_SURVEY_KEY", raising=False)
    assert client.get("/ahg/survey/results").status_code == 404
    monkeypatch.setenv("AHG_SURVEY_KEY", "secret")
    assert client.get("/ahg/survey/results").status_code == 403
    assert client.get("/ahg/survey/results?key=wrong").status_code == 403
    assert client.get("/ahg/survey/results.csv?key=wrong").status_code == 403


def test_results_tally_and_export(client, monkeypatch):
    monkeypatch.setenv("AHG_SURVEY_KEY", "secret")
    client.post("/ahg/survey", data={**_minimal(), "assistants": ["ChatGPT", "Claude"], "problem": "Scanned readings"})
    client.post(
        "/ahg/survey",
        data={**_minimal(), "assistants": ["ChatGPT"], "contact": "Yes, please", "email": "a@example.edu"},
    )
    page = client.get("/ahg/survey/results?key=secret")
    assert page.status_code == 200
    assert page.headers["Cache-Control"] == "no-store"
    html = page.get_data(as_text=True)
    assert "2 responses" in html
    assert '<tr><th scope="row">ChatGPT</th><td>2</td></tr>' in html
    assert "Scanned readings" in html and "a@example.edu" in html
    export = client.get("/ahg/survey/results.csv?key=secret")
    assert export.headers["Content-Type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(export.get_data(as_text=True))))
    assert [r["assistants"] for r in rows] == ["ChatGPT; Claude", "ChatGPT"]
