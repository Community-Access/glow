from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acb_large_print_web.app import create_app


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def test_feedback_form_submission_syncs_to_support_hub(client, monkeypatch, app: Flask) -> None:
    import acb_large_print_web.routes.feedback as feedback_route

    monkeypatch.setattr(
        feedback_route,
        "create_support_issue",
        lambda entry: (321, "https://github.com/Community-Access/support/issues/321", None),
    )

    response = client.post(
        "/feedback/",
        data={
            # A tracker issue is opened for the categories that need a person
            # to act; general praise is stored without one.
            "category": "bug",
            "rating": "good",
            "task": "convert",
            "summary": "HTML conversion looked great but the footer was duplicated",
            "message": "The result was strong overall, but I saw the footer twice in the HTML output.",
        },
    )

    assert response.status_code == 200
    assert b"Community Access support hub" in response.data

    conn = sqlite3.connect(str(Path(app.instance_path) / "feedback.db"))
    row = conn.execute(
        "SELECT source_app, source_channel, summary, github_issue_number FROM feedback"
    ).fetchone()
    conn.close()

    assert row == ("GLOW", "web", "HTML conversion looked great but the footer was duplicated", 321)


def test_feedback_api_submission_accepts_external_source(client, monkeypatch, app: Flask) -> None:
    import acb_large_print_web.routes.feedback as feedback_route

    monkeypatch.setenv("SUPPORT_HUB_API_TOKEN", "shared-secret")
    monkeypatch.setattr(
        feedback_route,
        "create_support_issue",
        lambda entry: (654, "https://github.com/Community-Access/support/issues/654", None),
    )

    response = client.post(
        "/feedback/api",
        headers={"Authorization": "Bearer shared-secret"},
        json={
            "source_app": "Quill",
            "source_channel": "desktop-beta",
            "source_version": "0.9.0-beta1",
            "platform": "Windows 11",
            "category": "bug",
            "rating": "poor",
            "task": "glow_fix_document",
            "summary": "GLOW fix preview opened, but compare started on the wrong tab",
            "message": "After choosing GLOW Fix Current Document, the preview opened correctly but focus stayed on the source tab.",
            "metadata": {"assistive_tech": "NVDA", "keyboard_pack": "Quill Review"},
        },
    )

    assert response.status_code == 202
    payload = response.get_json()
    assert payload is not None
    assert payload["support_repo"] == "Community-Access/support"
    assert payload["issue_url"].endswith("/654")

    conn = sqlite3.connect(str(Path(app.instance_path) / "feedback.db"))
    row = conn.execute(
        "SELECT source_app, source_channel, category, summary, github_issue_number FROM feedback"
    ).fetchone()
    conn.close()

    assert row == (
        "Quill",
        "desktop-beta",
        "bug",
        "GLOW fix preview opened, but compare started on the wrong tab",
        654,
    )


def test_feedback_api_requires_shared_token(client, monkeypatch) -> None:
    monkeypatch.setenv("SUPPORT_HUB_API_TOKEN", "shared-secret")

    response = client.post(
        "/feedback/api",
        headers={"Authorization": "Bearer wrong-secret"},
        json={
            "source_app": "Quill",
            "message": "Hello",
        },
    )

    assert response.status_code == 403


def test_support_hub_config_defaults_to_support_repo(monkeypatch) -> None:
    from acb_large_print_web.support_hub import load_support_hub_config

    monkeypatch.delenv("SUPPORT_HUB_GITHUB_REPO", raising=False)
    monkeypatch.delenv("FEEDBACK_GITHUB_REPO", raising=False)

    config = load_support_hub_config()

    assert config.repo == "Community-Access/support"
    assert config.labels == ["needs-triage"]
