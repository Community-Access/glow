"""Filing a GLOW support ticket into FreeScout through the mail bridge.

The help desk answers `support@community-access.org` and ingests mail over
IMAP; the bridge turns an HTTPS post into a Maildir message it can fetch. GLOW
posts to that same bridge, which is what makes a ticket raised in the product
arrive as an ordinary email *from the person who raised it* rather than from
GLOW.

Two properties are worth more than the rest and are tested first:

* The `From` header is the submitter, because FreeScout keys the customer off
  it and a ticket filed against `no-reply@` is a ticket nobody can answer.
* Nothing here can lose a bug report. A help desk that is unconfigured,
  unreachable or refusing is a ticket not filed -- never a submission dropped.
"""

from __future__ import annotations

import email as email_lib
import email.policy
import json
from pathlib import Path
from urllib import error as urlerror

import pytest
from flask import Flask

from acb_large_print_web import helpdesk
from acb_large_print_web.app import create_app

BRIDGE = "http://helpdesk-mailbridge:8096/postmark/inbound"
SUPPORT = "support@community-access.org"


@pytest.fixture()
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HELPDESK_BRIDGE_URL", BRIDGE)
    monkeypatch.setenv("HELPDESK_BRIDGE_USER", "bridge-user")
    monkeypatch.setenv("HELPDESK_BRIDGE_PASSWORD", "bridge-password")
    monkeypatch.setenv("HELPDESK_SUPPORT_EMAIL", SUPPORT)
    monkeypatch.delenv("HELPDESK_CATEGORIES", raising=False)


def _entry(**overrides) -> dict:
    entry = {
        "id": 42,
        "timestamp": "2026-09-11T12:00:00+00:00",
        "name": "Sam Participant",
        "email": "sam@example.test",
        "source_app": "GLOW",
        "source_channel": "web",
        "source_version": "7.0.0",
        "platform": "Windows",
        "category": "bug",
        "rating": "poor",
        "task": "Auditing a document",
        "summary": "Headings are not announced",
        "message": "The heading level is wrong on the audit report page.",
        "metadata_json": "{}",
    }
    entry.update(overrides)
    return entry


class _Captured:
    """Stands in for the bridge, and remembers what it was sent."""

    def __init__(self, status: int = 200):
        self.status = status
        self.request = None

    def __call__(self, request, timeout=None):
        self.request = request
        captured = self

        class _Response:
            status = captured.status

            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *exc):
                return False

        return _Response()

    @property
    def payload(self) -> dict:
        return json.loads(self.request.data.decode("utf-8"))

    @property
    def message(self):
        return email_lib.message_from_string(self.payload["RawEmail"], policy=email.policy.default)


# ---------------------------------------------------------------------------
# The two properties that matter most
# ---------------------------------------------------------------------------

def test_the_ticket_comes_from_the_person_who_raised_it(
    configured, monkeypatch: pytest.MonkeyPatch
):
    """FreeScout keys the customer off From. Get this wrong and every ticket
    in the product is filed against GLOW rather than against a person."""
    bridge = _Captured()
    monkeypatch.setattr(helpdesk.urlrequest, "urlopen", bridge)

    message_id, error = helpdesk.file_ticket(_entry())

    assert error is None
    assert message_id
    assert bridge.message["From"] == "Sam Participant <sam@example.test>"
    assert bridge.message["To"] == SUPPORT
    assert bridge.payload["OriginalRecipient"] == SUPPORT


def test_an_unreachable_help_desk_is_reported_not_raised(
    configured, monkeypatch: pytest.MonkeyPatch
):
    """The feedback is already stored by the time this runs. A help desk that
    is down must cost a ticket, never a bug report."""

    def _refuse(request, timeout=None):
        raise urlerror.URLError("connection refused")

    monkeypatch.setattr(helpdesk.urlrequest, "urlopen", _refuse)

    message_id, error = helpdesk.file_ticket(_entry())

    assert message_id is None
    assert "unreachable" in error


# ---------------------------------------------------------------------------
# What becomes a ticket
# ---------------------------------------------------------------------------

def test_no_ticket_without_an_address_to_reply_to(configured):
    open_it, reason = helpdesk.should_open_ticket(_entry(email=""))

    assert open_it is False
    assert reason.startswith(helpdesk.SKIP_PREFIX)
    assert "no address" in reason


def test_praise_does_not_open_a_ticket(configured):
    open_it, reason = helpdesk.should_open_ticket(_entry(category="praise"))

    assert open_it is False
    assert "does not open a ticket" in reason


def test_a_bug_report_opens_a_ticket(configured):
    open_it, reason = helpdesk.should_open_ticket(_entry())

    assert open_it is True
    assert reason == ""


def test_categories_can_be_opened_up_to_everything(
    configured, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("HELPDESK_CATEGORIES", "all")

    open_it, _reason = helpdesk.should_open_ticket(_entry(category="praise"))

    assert open_it is True


def test_nothing_is_filed_when_the_help_desk_is_not_configured(
    monkeypatch: pytest.MonkeyPatch
):
    for name in (
        "HELPDESK_BRIDGE_URL",
        "HELPDESK_BRIDGE_USER",
        "HELPDESK_BRIDGE_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)

    message_id, error = helpdesk.file_ticket(_entry())

    assert message_id is None
    assert error.startswith(helpdesk.SKIP_PREFIX)
    assert helpdesk.helpdesk_configured() is False


# ---------------------------------------------------------------------------
# The message itself
# ---------------------------------------------------------------------------

def test_the_ticket_says_the_address_is_unverified(configured):
    """Anyone can type anyone's address into a form. An agent about to reply
    should be able to see that before they do."""
    raw, _message_id = helpdesk.build_ticket_message(_entry())
    message = email_lib.message_from_bytes(raw, policy=email.policy.default)

    assert message["X-GLOW-Address-Verified"] == "no"
    assert "has not been verified" in message.get_content()


def test_the_ticket_carries_the_context_an_agent_needs(configured):
    raw, _message_id = helpdesk.build_ticket_message(
        _entry(github_issue_url="https://github.com/org/repo/issues/7")
    )
    body = email_lib.message_from_bytes(raw, policy=email.policy.default).get_content()

    assert "The heading level is wrong" in body
    assert "Version: 7.0.0" in body
    assert "Platform: Windows" in body
    assert "GLOW feedback id: 42" in body
    assert "https://github.com/org/repo/issues/7" in body


def test_the_subject_falls_back_when_no_summary_was_given(configured):
    raw, _message_id = helpdesk.build_ticket_message(_entry(summary=""))

    assert email_lib.message_from_bytes(raw, policy=email.policy.default)["Subject"] == "GLOW bug request"


def test_the_message_id_is_the_dedup_key(configured, monkeypatch: pytest.MonkeyPatch):
    """The bridge dedups on Postmark's MessageID. Ours is stable for one
    submission, so a retry collapses instead of opening a second ticket."""
    bridge = _Captured()
    monkeypatch.setattr(helpdesk.urlrequest, "urlopen", bridge)

    message_id, _error = helpdesk.file_ticket(_entry())

    assert bridge.payload["MessageID"] == message_id.strip("<>")
    assert "<" not in bridge.payload["MessageID"]


def test_extra_metadata_is_included_when_present(configured):
    raw, _message_id = helpdesk.build_ticket_message(
        _entry(metadata_json=json.dumps({"browser": "Firefox 142", "page": "/audit"}))
    )
    body = email_lib.message_from_bytes(raw, policy=email.policy.default).get_content()

    assert "browser: Firefox 142" in body
    assert "page: /audit" in body


# ---------------------------------------------------------------------------
# Talking to the bridge
# ---------------------------------------------------------------------------

def test_the_request_carries_basic_credentials(
    configured, monkeypatch: pytest.MonkeyPatch
):
    import base64

    bridge = _Captured()
    monkeypatch.setattr(helpdesk.urlrequest, "urlopen", bridge)

    helpdesk.file_ticket(_entry())

    expected = base64.b64encode(b"bridge-user:bridge-password").decode("ascii")
    assert bridge.request.headers["Authorization"] == f"Basic {expected}"


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "credentials"),
        (403, "does not accept mail"),
        (413, "larger than"),
    ],
)
def test_the_bridge_status_codes_become_something_an_admin_can_act_on(
    configured, monkeypatch: pytest.MonkeyPatch, status: int, expected: str
):
    def _fail(request, timeout=None):
        raise urlerror.HTTPError(BRIDGE, status, "no", {}, None)

    monkeypatch.setattr(helpdesk.urlrequest, "urlopen", _fail)

    message_id, error = helpdesk.file_ticket(_entry())

    assert message_id is None
    assert expected in error


# ---------------------------------------------------------------------------
# End to end through the feedback form
# ---------------------------------------------------------------------------

@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.delenv("FEEDBACK_GITHUB_TOKEN", raising=False)
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


def test_the_feedback_form_files_a_ticket_and_says_so(
    app: Flask, configured, monkeypatch: pytest.MonkeyPatch
):
    bridge = _Captured()
    monkeypatch.setattr(helpdesk.urlrequest, "urlopen", bridge)

    response = app.test_client().post(
        "/feedback/",
        data={
            "name": "Sam Participant",
            "email": "sam@example.test",
            "category": "bug",
            "rating": "poor",
            "summary": "Headings are not announced",
            "message": "The heading level is wrong on the audit report page.",
        },
    )

    assert response.status_code == 200
    assert b"Somebody will reply" in response.data
    assert b"support@community-access.org" in response.data
    assert bridge.message["From"] == "Sam Participant <sam@example.test>"


def test_feedback_still_works_when_the_help_desk_is_down(
    app: Flask, configured, monkeypatch: pytest.MonkeyPatch
):
    def _refuse(request, timeout=None):
        raise urlerror.URLError("connection refused")

    monkeypatch.setattr(helpdesk.urlrequest, "urlopen", _refuse)

    response = app.test_client().post(
        "/feedback/",
        data={
            "name": "Sam",
            "email": "sam@example.test",
            "category": "bug",
            "rating": "poor",
            "summary": "Something broke",
            "message": "A description of what broke.",
        },
    )

    assert response.status_code == 200
    assert b"Thank You" in response.data
    # No promise of a reply that is not going to come.
    assert b"Somebody will reply" not in response.data
