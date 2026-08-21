"""The shared email layer: status, message rendering, and the test send.

Six GLOW features depend on one Postmark token -- audit delivery, batch
delivery, Whisperer notifications, admin sign-in links, and three workshop
features. Until now the only way to find out whether mail worked was to
trigger one of them and wait, which is a poor thing to discover on a
conference morning.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web import email as email_module
from acb_large_print_web.app import create_app
from acb_large_print_web.email import (
    EMAIL_FEATURES,
    email_status,
    render_email,
    send_test_email,
)


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.delenv("POSTMARK_SERVER_TOKEN", raising=False)
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def test_status_reports_unconfigured_without_a_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("POSTMARK_SERVER_TOKEN", raising=False)

    status = email_status()

    assert status["configured"] is False
    assert all(feature["available"] is False for feature in status["features"])


def test_status_lists_every_feature_that_depends_on_mail(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "token-value")

    status = email_status()

    assert status["configured"] is True
    assert len(status["features"]) == len(EMAIL_FEATURES)
    names = " ".join(f["name"] for f in status["features"])
    for expected in ("Audit report", "Whisperer", "Admin sign-in", "return links", "nudge"):
        assert expected in names


def test_status_never_carries_the_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "super-secret-token")

    status = email_status()

    assert "super-secret-token" not in repr(status)
    # A length is useful when diagnosing a truncated paste; the value is not.
    assert status["token_length"] == len("super-secret-token")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_every_message_has_a_real_plain_text_alternative():
    html, text = render_email(
        title="A title",
        intro="An introduction.",
        paragraphs=("A paragraph.",),
        bullets=("First", "Second"),
        closing="A closing line.",
    )

    for fragment in ("A title", "An introduction.", "A paragraph.", "First", "Second"):
        assert fragment in html
        assert fragment in text
    # The text version is text, not markup with the tags stripped later.
    assert "<" not in text


def test_the_html_is_structured_rather_than_styled():
    html, _text = render_email(title="T", intro="I", bullets=("a",))

    assert html.startswith("<h1>T</h1>")
    assert "<ul><li>a</li></ul>" in html
    # Nothing here depends on colour or on an image loading.
    assert "color" not in html
    assert "<img" not in html


def test_the_text_version_keeps_the_reading_order():
    _html, text = render_email(
        title="Title", intro="Intro", paragraphs=("Middle",), closing="End"
    )

    assert text.index("Title") < text.index("Intro") < text.index("Middle") < text.index("End")


# ---------------------------------------------------------------------------
# The test send
# ---------------------------------------------------------------------------


def test_a_test_send_without_a_token_explains_itself(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("POSTMARK_SERVER_TOKEN", raising=False)

    ok, detail = send_test_email("someone@example.edu")

    assert ok is False
    assert "POSTMARK_SERVER_TOKEN" in detail


def test_a_test_send_names_the_sender_and_the_stream(monkeypatch: pytest.MonkeyPatch):
    """The usual failure is mail from an address the domain does not
    authorise, which is invisible until someone checks a spam folder."""
    monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "token-value")
    sent: dict = {}

    def _capture(payload, to_email):
        sent.update(payload)
        return True, "ok"

    monkeypatch.setattr(email_module, "_send", _capture)

    ok, _detail = send_test_email("someone@example.edu", requested_by="admin@example.edu")

    assert ok is True
    assert sent["To"] == "someone@example.edu"
    assert sent["Subject"] == "GLOW test email"
    assert "no-reply@notify.letitglow.app" in sent["TextBody"]
    assert "transactional" in sent["TextBody"]
    assert "admin@example.edu" in sent["TextBody"]
    assert sent["TextBody"].strip()
    assert sent["HtmlBody"].startswith("<h1>")


# ---------------------------------------------------------------------------
# The admin surface
# ---------------------------------------------------------------------------


def test_the_admin_page_says_what_breaks_without_mail(app: Flask, monkeypatch: pytest.MonkeyPatch):
    """Admin sign-in links are themselves one of the things that break, so
    the page has to be reachable by an admin who arrived another way."""
    import acb_large_print_web.routes.admin as admin_route

    monkeypatch.setattr(admin_route, "_require_admin", lambda: "admin@example.edu")
    client = app.test_client()

    page = client.get("/admin/queue").get_data(as_text=True)

    assert "Postmark is not configured" in page
    assert "Whisperer job notifications" in page
    assert "Send test email" in page


def test_the_test_button_is_disabled_when_nothing_can_send(app: Flask, monkeypatch):
    import acb_large_print_web.routes.admin as admin_route

    monkeypatch.setattr(admin_route, "_require_admin", lambda: "admin@example.edu")
    client = app.test_client()

    page = client.get("/admin/queue").get_data(as_text=True)

    assert "disabled" in page


def test_posting_a_test_without_a_token_reports_rather_than_pretends(app: Flask, monkeypatch):
    import acb_large_print_web.routes.admin as admin_route

    monkeypatch.setattr(admin_route, "_require_admin", lambda: "admin@example.edu")
    client = app.test_client()

    resp = client.post("/admin/email/test", data={"test_email": "someone@example.edu"})

    assert resp.status_code in (302, 303)
    assert "email_error" in resp.headers["Location"]


def test_a_blank_address_sends_to_the_admin_themselves(app: Flask, monkeypatch):
    import acb_large_print_web.routes.admin as admin_route

    monkeypatch.setattr(admin_route, "_require_admin", lambda: "admin@example.edu")
    monkeypatch.setattr(admin_route, "email_configured", lambda: True)
    captured: dict = {}

    def _fake(to_email, *, requested_by=""):
        captured["to"] = to_email
        captured["by"] = requested_by
        return True, "ok"

    monkeypatch.setattr(admin_route, "send_test_email", _fake)
    client = app.test_client()

    client.post("/admin/email/test", data={"test_email": ""})

    assert captured == {"to": "admin@example.edu", "by": "admin@example.edu"}
