"""Two-way mail: the reply path, the webhooks, and the do-not-send list.

GLOW could send but not listen. These tests cover the half that was missing:
a message that carries a per-conversation Reply-To, a Postmark inbound
webhook that files the answer against the right thread, delivery events that
suppress addresses which will never work again, and the in-app views that let
a participant or an admin carry on the conversation without email at all.

The webhook tests matter twice over. An unauthenticated inbound endpoint is a
way for anyone on the internet to write into somebody's conversation, so the
first thing checked is that it refuses.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web import email as email_module
from acb_large_print_web import email_threads
from acb_large_print_web.app import create_app

WEBHOOK_SECRET = "test-webhook-secret"
INBOUND = "reply@inbound.example.test"


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "test-token")
    monkeypatch.setenv("POSTMARK_INBOUND_ADDRESS", INBOUND)
    monkeypatch.setenv("POSTMARK_WEBHOOK_TOKEN", WEBHOOK_SECRET)
    monkeypatch.delenv("POSTMARK_WEBHOOK_ALLOWED_IPS", raising=False)
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


@pytest.fixture()
def ctx(app: Flask):
    with app.app_context():
        yield app


class _FakeResponse:
    def __init__(self, status: int = 200, body: dict | None = None):
        self.status_code = status
        self._body = body if body is not None else {"MessageID": "abcd-1234-efgh-5678"}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------

def test_reply_address_carries_the_thread_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("POSTMARK_INBOUND_ADDRESS", INBOUND)

    address = email_threads.reply_address("0123456789abcdef0123")

    assert address == "reply+0123456789abcdef0123@inbound.example.test"
    assert email_threads.thread_key_from_address(address) == "0123456789abcdef0123"


def test_a_plain_address_yields_no_thread_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("POSTMARK_INBOUND_ADDRESS", INBOUND)

    assert email_threads.thread_key_from_address(INBOUND) == ""
    assert email_threads.thread_key_from_address("reply+not-a-key@inbound.example.test") == ""


def test_without_an_inbound_address_conversations_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("POSTMARK_SERVER_TOKEN", "test-token")
    monkeypatch.delenv("POSTMARK_INBOUND_ADDRESS", raising=False)

    assert email_module.conversations_available() is False


# ---------------------------------------------------------------------------
# Sending into a conversation
# ---------------------------------------------------------------------------

def test_a_thread_message_sets_reply_to_and_is_recorded(
    ctx: Flask, monkeypatch: pytest.MonkeyPatch
):
    captured: dict = {}

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        captured.update(json or {})
        return _FakeResponse()

    monkeypatch.setattr(email_module.requests, "post", fake_post)

    thread = email_threads.create_thread(
        context_kind="workshop",
        subject="Your GLOW workshop artifacts",
        participant_email="participant@example.test",
        participant_name="Sam",
    )
    ok, detail = email_module.send_thread_message(thread, body_text="Here is your plan.")

    assert ok is True, detail
    assert captured["ReplyTo"] == f"reply+{thread['thread_key']}@inbound.example.test"
    messages = email_threads.list_messages(int(thread["id"]))
    assert len(messages) == 1
    assert messages[0]["direction"] == "out"
    assert messages[0]["postmark_message_id"] == "abcd-1234-efgh-5678"


def test_the_reply_footer_tells_people_they_can_just_reply(
    ctx: Flask, monkeypatch: pytest.MonkeyPatch
):
    captured: dict = {}
    monkeypatch.setattr(
        email_module.requests,
        "post",
        lambda url, json=None, headers=None, timeout=None: (
            captured.update(json or {}) or _FakeResponse()
        ),
    )

    thread = email_threads.create_thread(
        context_kind="passport", subject="A question", participant_email="a@example.test"
    )
    email_module.send_thread_message(thread, body_text="An answer.")

    assert "reply to this email" in captured["TextBody"].lower()
    assert "reply to this email" in captured["HtmlBody"].lower()


def test_a_message_cannot_be_sent_when_replies_are_not_configured(
    ctx: Flask, monkeypatch: pytest.MonkeyPatch
):
    thread = email_threads.create_thread(
        context_kind="passport", subject="A question", participant_email="a@example.test"
    )
    monkeypatch.delenv("POSTMARK_INBOUND_ADDRESS", raising=False)

    ok, detail = email_module.send_thread_message(thread, body_text="Hello")

    assert ok is False
    assert "POSTMARK_INBOUND_ADDRESS" in detail


# ---------------------------------------------------------------------------
# The inbound webhook
# ---------------------------------------------------------------------------

def _inbound_payload(*, mailbox_hash: str = "", from_email: str = "participant@example.test"):
    return {
        "FromFull": {"Email": from_email, "Name": "Sam Participant"},
        "To": f"reply+{mailbox_hash}@inbound.example.test" if mailbox_hash else INBOUND,
        "MailboxHash": mailbox_hash,
        "Subject": "Re: Your GLOW workshop artifacts",
        "MessageID": "inbound-message-1",
        "TextBody": "Thank you. One question about step 3.\n\nOn Tuesday, GLOW wrote:\n> the original",
        "StrippedTextReply": "",
        "HtmlBody": "<p>Thank you.</p>",
        "Headers": [{"Name": "In-Reply-To", "Value": "<abcd-1234-efgh-5678>"}],
        "Attachments": [],
    }


def test_the_inbound_webhook_refuses_without_the_secret(client, ctx: Flask):
    response = client.post("/mail/webhook/inbound", json=_inbound_payload())

    assert response.status_code == 403


def test_the_inbound_webhook_refuses_a_wrong_secret(client, ctx: Flask):
    response = client.post(
        "/mail/webhook/inbound?token=not-the-secret", json=_inbound_payload()
    )

    assert response.status_code == 403


def test_the_inbound_webhook_fails_closed_when_no_secret_is_set(
    client, ctx: Flask, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("POSTMARK_WEBHOOK_TOKEN", raising=False)

    response = client.post("/mail/webhook/inbound?token=anything", json=_inbound_payload())

    assert response.status_code == 503


def test_a_reply_is_filed_against_its_thread_by_mailbox_hash(client, ctx: Flask):
    thread = email_threads.create_thread(
        context_kind="workshop",
        subject="Your GLOW workshop artifacts",
        participant_email="participant@example.test",
    )

    response = client.post(
        f"/mail/webhook/inbound?token={WEBHOOK_SECRET}",
        json=_inbound_payload(mailbox_hash=str(thread["thread_key"])),
    )

    assert response.status_code == 200
    messages = email_threads.list_messages(int(thread["id"]))
    assert len(messages) == 1
    assert messages[0]["direction"] == "in"
    # The quoted history is trimmed, the person's own sentence is not.
    assert "One question about step 3." in messages[0]["body_text"]
    assert "the original" not in messages[0]["body_text"]


def test_a_reply_falls_back_to_the_in_reply_to_header(client, ctx: Flask):
    thread = email_threads.create_thread(
        context_kind="workshop",
        subject="Your GLOW workshop artifacts",
        participant_email="participant@example.test",
    )
    email_threads.add_message(
        int(thread["id"]),
        direction="out",
        body_text="The original message.",
        postmark_message_id="abcd-1234-efgh-5678",
    )

    client.post(
        f"/mail/webhook/inbound?token={WEBHOOK_SECRET}", json=_inbound_payload()
    )

    messages = email_threads.list_messages(int(thread["id"]))
    assert [item["direction"] for item in messages] == ["out", "in"]


def test_an_unroutable_message_still_becomes_a_conversation(client, ctx: Flask):
    payload = _inbound_payload(from_email="stranger@example.test")
    payload["Headers"] = []

    response = client.post(f"/mail/webhook/inbound?token={WEBHOOK_SECRET}", json=payload)

    assert response.status_code == 200
    threads = email_threads.list_threads(context_kind="inbound")
    assert len(threads) == 1
    assert threads[0]["participant_email"] == "stranger@example.test"


def test_an_out_of_office_reply_does_not_land_in_the_conversation(client, ctx: Flask):
    thread = email_threads.create_thread(
        context_kind="workshop",
        subject="Your GLOW workshop artifacts",
        participant_email="participant@example.test",
    )
    payload = _inbound_payload(mailbox_hash=str(thread["thread_key"]))
    payload["Headers"] = [{"Name": "Auto-Submitted", "Value": "auto-replied"}]

    client.post(f"/mail/webhook/inbound?token={WEBHOOK_SECRET}", json=payload)

    assert email_threads.list_messages(int(thread["id"])) == []
    assert email_threads.list_events(record_type="InboundAutoReply")


def test_a_reply_reopens_a_closed_conversation(client, ctx: Flask):
    thread = email_threads.create_thread(
        context_kind="workshop",
        subject="Your GLOW workshop artifacts",
        participant_email="participant@example.test",
    )
    email_threads.set_thread_status(int(thread["id"]), "closed")

    client.post(
        f"/mail/webhook/inbound?token={WEBHOOK_SECRET}",
        json=_inbound_payload(mailbox_hash=str(thread["thread_key"])),
    )

    assert email_threads.get_thread(int(thread["id"]))["status"] == "open"


# ---------------------------------------------------------------------------
# Delivery events
# ---------------------------------------------------------------------------

def test_a_hard_bounce_suppresses_the_address(client, ctx: Flask):
    response = client.post(
        f"/mail/webhook/events?token={WEBHOOK_SECRET}",
        json={
            "RecordType": "Bounce",
            "Type": "HardBounce",
            "Email": "gone@example.test",
            "MessageID": "abcd-1234-efgh-5678",
            "Description": "The server was unable to deliver your message.",
            "Inactive": True,
        },
    )

    assert response.status_code == 200
    assert email_threads.is_suppressed("gone@example.test") is True


def test_a_soft_bounce_does_not_suppress_the_address(client, ctx: Flask):
    client.post(
        f"/mail/webhook/events?token={WEBHOOK_SECRET}",
        json={
            "RecordType": "Bounce",
            "Type": "SoftBounce",
            "Email": "full@example.test",
            "MessageID": "m1",
            "Description": "Mailbox full",
            "Inactive": False,
        },
    )

    assert email_threads.is_suppressed("full@example.test") is False


def test_a_spam_complaint_suppresses_the_address(client, ctx: Flask):
    client.post(
        f"/mail/webhook/events?token={WEBHOOK_SECRET}",
        json={
            "RecordType": "SpamComplaint",
            "Email": "annoyed@example.test",
            "MessageID": "m2",
        },
    )

    assert email_threads.is_suppressed("annoyed@example.test") is True


def test_a_delivery_event_is_recorded_against_the_message(client, ctx: Flask):
    thread = email_threads.create_thread(
        context_kind="passport", subject="Hello", participant_email="a@example.test"
    )
    email_threads.add_message(
        int(thread["id"]), direction="out", body_text="Hi", postmark_message_id="m3"
    )

    client.post(
        f"/mail/webhook/events?token={WEBHOOK_SECRET}",
        json={"RecordType": "Delivery", "Email": "a@example.test", "MessageID": "m3"},
    )

    assert email_threads.list_messages(int(thread["id"]))[0]["delivery_state"] == "delivered"


def test_a_subscription_change_can_both_suppress_and_release(client, ctx: Flask):
    client.post(
        f"/mail/webhook/events?token={WEBHOOK_SECRET}",
        json={
            "RecordType": "SubscriptionChange",
            "Recipient": "opted-out@example.test",
            "SuppressSending": True,
            "SuppressionReason": "ManualSuppression",
        },
    )
    assert email_threads.is_suppressed("opted-out@example.test") is True

    client.post(
        f"/mail/webhook/events?token={WEBHOOK_SECRET}",
        json={
            "RecordType": "SubscriptionChange",
            "Recipient": "opted-out@example.test",
            "SuppressSending": False,
        },
    )
    assert email_threads.is_suppressed("opted-out@example.test") is False


# ---------------------------------------------------------------------------
# Suppression is honoured by every sender
# ---------------------------------------------------------------------------

def test_a_suppressed_address_is_not_mailed(ctx: Flask, monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    def fake_post(url, json=None, headers=None, timeout=None):  # noqa: A002
        calls.append(url)
        return _FakeResponse()

    monkeypatch.setattr(email_module.requests, "post", fake_post)
    email_threads.suppress("gone@example.test", reason="HardBounce", source="bounce")

    ok, detail = email_module.send_test_email("gone@example.test")

    assert ok is False
    assert calls == []
    assert "do-not-send" in detail


def test_clearing_a_suppression_lets_mail_flow_again(
    ctx: Flask, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(
        email_module.requests,
        "post",
        lambda url, json=None, headers=None, timeout=None: _FakeResponse(),
    )
    email_threads.suppress("back@example.test", reason="HardBounce", source="bounce")
    email_threads.unsuppress("back@example.test")

    ok, _detail = email_module.send_test_email("back@example.test")

    assert ok is True


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

def test_status_reports_the_inbound_half(ctx: Flask):
    status = email_module.email_status()

    assert status["inbound_configured"] is True
    assert status["inbound_address"] == INBOUND
    assert status["webhook_secret_set"] is True
    assert status["stream"] == "outbound"
    names = {feature["name"] for feature in status["features"]}
    assert "Conversations" in names


def test_conversations_report_unavailable_without_an_inbound_address(
    ctx: Flask, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("POSTMARK_INBOUND_ADDRESS", raising=False)

    status = email_module.email_status()
    conversations = [f for f in status["features"] if f["name"] == "Conversations"][0]

    assert conversations["available"] is False


# ---------------------------------------------------------------------------
# The in-app views
# ---------------------------------------------------------------------------

def test_the_conversations_page_is_honest_with_an_unknown_visitor(client, ctx: Flask):
    response = client.get("/mail/conversations")

    assert response.status_code == 200
    assert b"Nothing to show yet" in response.data


def test_a_participant_sees_only_their_own_conversations(client, ctx: Flask):
    from acb_large_print_web.workshop_store import create_or_update_participant, ensure_session

    ensure_session("TESTCODE")
    participant_key = str(
        create_or_update_participant("TESTCODE", "Sam")["participant_key"]
    )
    mine = email_threads.create_thread(
        context_kind="workshop",
        subject="Mine",
        participant_email="sam@example.test",
        owner_kind="workshop_participant",
        owner_key=participant_key,
    )
    email_threads.create_thread(
        context_kind="workshop",
        subject="Somebody else's",
        participant_email="other@example.test",
        owner_kind="workshop_participant",
        owner_key="a-different-key",
    )

    client.set_cookie("glow_workshop_participant", participant_key)
    response = client.get("/mail/conversations")

    assert b"Mine" in response.data
    assert b"Somebody else" not in response.data

    # And the detail view is scoped the same way.
    assert client.get(f"/mail/conversations/{mine['id']}").status_code == 200


def test_another_persons_conversation_is_not_readable(client, ctx: Flask):
    thread = email_threads.create_thread(
        context_kind="workshop",
        subject="Not yours",
        participant_email="other@example.test",
        owner_kind="workshop_participant",
        owner_key="somebody-else",
    )

    client.set_cookie("glow_workshop_participant", "not-the-owner")
    response = client.get(f"/mail/conversations/{thread['id']}")

    assert response.status_code == 404


def test_the_staff_console_requires_an_admin(client, ctx: Flask):
    assert client.get("/mail/admin").status_code == 403


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------

def test_purging_removes_a_stale_conversation_and_its_messages(ctx: Flask):
    thread = email_threads.create_thread(
        context_kind="passport", subject="Old", participant_email="old@example.test"
    )
    email_threads.add_message(int(thread["id"]), direction="out", body_text="Hello")

    assert email_threads.purge_expired(days=0) == 1
    assert email_threads.get_thread(int(thread["id"])) is None
    assert email_threads.list_messages(int(thread["id"])) == []
