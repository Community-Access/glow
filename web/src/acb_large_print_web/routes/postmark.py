"""Postmark webhooks, and the conversations they feed.

Two halves:

*Webhooks.* ``/mail/webhook/inbound`` receives replies; ``/mail/webhook/events``
receives bounces, spam complaints, deliveries and subscription changes. Both
require a shared secret and both fail closed: if ``POSTMARK_WEBHOOK_TOKEN`` is
not set, they return 503 rather than accepting anonymous posts, because an
open inbound endpoint is a way to write arbitrary rows into somebody's inbox.

*Conversations.* A participant reads and answers inside GLOW at
``/mail/conversations``, identified by the passport cookie or the workshop
participant cookie they already have -- no new account, no password. Staff
read and answer everything at ``/mail/admin``.

The design rule is the one the rest of GLOW follows: the email path and the
in-app path are the same conversation, not two systems that happen to share
an address. Somebody who replies from their phone and then opens GLOW on a
laptop sees one thread in order, and either way of answering works.
"""

from __future__ import annotations

import hmac
import ipaddress
import logging
import os
import re
from typing import Any

from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from .. import email_threads
from ..app import csrf, limiter
from ..email import conversations_available, email_configured, send_thread_message
from ..helpdesk import helpdesk_configured, helpdesk_status, load_helpdesk_config

postmark_bp = Blueprint("postmark", __name__)

log = logging.getLogger(__name__)

# The workshop's participant cookie, repeated rather than imported: importing
# routes.workshop here would make two blueprints depend on each other's import
# order for the sake of one string.
PARTICIPANT_COOKIE = "glow_workshop_participant"
PASSPORT_COOKIE = "glow_passport"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MESSAGES = {
    "sent": ("Your message has been sent.", False),
    "empty": ("Write something before sending.", True),
    "unavailable": ("Replies are not available on this server yet.", True),
    "send-failed": ("We could not send that message. Please try again later.", True),
    "closed": ("That conversation is closed.", True),
    "started": ("Your message has been sent. Replies will appear here.", False),
    "no-address": ("Add an email address first, so we have somewhere to reply.", True),
    "cleared": ("That address can receive mail from GLOW again.", False),
    "thread-closed": ("Conversation closed.", False),
    "thread-reopened": ("Conversation reopened.", False),
    "deleted": ("Conversation deleted.", False),
}


def _message() -> tuple[str, bool]:
    key = (request.args.get("m") or "").strip()
    text, is_error = MESSAGES.get(key, ("", False))
    return text, is_error


# ---------------------------------------------------------------------------
# Webhook authentication
# ---------------------------------------------------------------------------

def _webhook_secret() -> str:
    return os.environ.get("POSTMARK_WEBHOOK_TOKEN", "").strip()


def _presented_secret() -> str:
    """The secret this request carries, from any of the three usual places.

    Postmark's webhook configuration accepts a URL, so all three are things
    it can actually send: basic auth credentials embedded in the URL, a
    query string, or a custom header.
    """
    auth = request.authorization
    if auth is not None and auth.password:
        return str(auth.password)
    header = request.headers.get("X-Postmark-Webhook-Token", "")
    if header:
        return header.strip()
    return (request.args.get("token") or "").strip()


def _source_ip_allowed() -> bool:
    """Optional second lock: Postmark publishes the addresses it posts from.

    Unset means "do not check", because the shared secret is the primary
    control and an allow-list that goes stale silently rejects real mail.
    """
    raw = os.environ.get("POSTMARK_WEBHOOK_ALLOWED_IPS", "").strip()
    if not raw:
        return True
    remote = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    if not remote:
        return False
    try:
        address = ipaddress.ip_address(remote)
    except ValueError:
        return False
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            if address in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def _authorize_webhook() -> None:
    """Abort unless this really is Postmark. Fails closed by design."""
    secret = _webhook_secret()
    if not secret:
        log.error("Postmark webhook rejected: POSTMARK_WEBHOOK_TOKEN is not set")
        abort(503)
    if not hmac.compare_digest(_presented_secret(), secret):
        log.warning("Postmark webhook rejected: bad or missing secret")
        abort(403)
    if not _source_ip_allowed():
        log.warning("Postmark webhook rejected: source address not in allow-list")
        abort(403)


def _payloads() -> list[dict[str, Any]]:
    """The webhook body, as a list. Postmark posts one object; be tolerant."""
    body = request.get_json(silent=True)
    if isinstance(body, dict):
        return [body]
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]
    return []


# ---------------------------------------------------------------------------
# Inbound mail
# ---------------------------------------------------------------------------

def _headers_map(payload: dict) -> dict[str, str]:
    headers = {}
    for item in payload.get("Headers") or []:
        if isinstance(item, dict):
            headers[str(item.get("Name", "")).lower()] = str(item.get("Value", ""))
    return headers


def _sender(payload: dict) -> tuple[str, str]:
    full = payload.get("FromFull")
    if isinstance(full, dict):
        return (
            str(full.get("Email", "") or "").strip().lower(),
            str(full.get("Name", "") or "").strip(),
        )
    return str(payload.get("From", "") or "").strip().lower(), ""


def _recipients(payload: dict) -> list[str]:
    """Every address this message was addressed to, for hash recovery."""
    found: list[str] = []
    for key in ("ToFull", "CcFull", "BccFull"):
        for item in payload.get(key) or []:
            if isinstance(item, dict) and item.get("Email"):
                found.append(str(item["Email"]))
    for key in ("To", "Cc", "OriginalRecipient"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            found.extend(part.strip() for part in value.split(","))
    return [item for item in found if item]


def _is_auto_reply(payload: dict, headers: dict[str, str]) -> bool:
    """Out-of-office and bounce-loop detection.

    A vacation responder answering GLOW's message, which GLOW then files and
    (if anything ever auto-answered) replies to, is how a mail loop starts.
    Nothing here auto-answers, but the message is still noise in somebody's
    conversation, so it is recorded as an event and not as a reply.
    """
    if headers.get("auto-submitted", "").lower() not in ("", "no"):
        return True
    if headers.get("x-autoreply") or headers.get("x-autorespond"):
        return True
    if headers.get("precedence", "").lower() in ("bulk", "auto_reply", "junk"):
        return True
    subject = str(payload.get("Subject", "") or "").lower()
    return subject.startswith(("auto:", "automatic reply", "out of office"))


def _route_inbound(payload: dict, headers: dict[str, str]) -> tuple[dict | None, str]:
    """Find the conversation a reply belongs to. Returns (thread, how)."""
    key = str(payload.get("MailboxHash", "") or "").strip().lower()
    if key:
        thread = email_threads.get_thread_by_key(key)
        if thread:
            return thread, "mailbox-hash"

    for address in _recipients(payload):
        candidate = email_threads.thread_key_from_address(address)
        if candidate:
            thread = email_threads.get_thread_by_key(candidate)
            if thread:
                return thread, "recipient-address"

    references = f"{headers.get('in-reply-to', '')} {headers.get('references', '')}"
    for ident in re.findall(r"[0-9a-fA-F-]{20,}", references):
        thread = email_threads.thread_for_postmark_message_id(ident)
        if thread:
            return thread, "in-reply-to"

    from_email, _name = _sender(payload)
    thread = email_threads.latest_open_thread_for(from_email)
    if thread:
        return thread, "sender-history"

    return None, "unrouted"


@postmark_bp.route("/webhook/inbound", methods=["POST"])
@csrf.exempt
@limiter.limit("120 per minute")
def inbound_webhook():
    """Receive one inbound message and file it against a conversation."""
    _authorize_webhook()

    stored = 0
    for payload in _payloads():
        headers = _headers_map(payload)
        from_email, from_name = _sender(payload)
        subject = str(payload.get("Subject", "") or "").strip() or "(no subject)"
        body = (
            str(payload.get("StrippedTextReply", "") or "").strip()
            or email_threads.strip_quoted_reply(str(payload.get("TextBody", "") or ""))
        )
        attachments = tuple(
            str(item.get("Name", ""))
            for item in (payload.get("Attachments") or [])
            if isinstance(item, dict) and item.get("Name")
        )

        if _is_auto_reply(payload, headers):
            email_threads.record_event(
                record_type="InboundAutoReply",
                email=from_email,
                message_id=str(payload.get("MessageID", "") or ""),
                summary=subject,
                payload={"Subject": subject, "From": from_email},
            )
            continue

        thread, how = _route_inbound(payload, headers)
        if thread is None:
            # Somebody wrote to us out of the blue, or the routing hints were
            # all stripped in transit. Still a person waiting for an answer.
            thread = email_threads.create_thread(
                context_kind="inbound",
                subject=subject,
                participant_email=from_email,
                participant_name=from_name,
            )

        email_threads.add_message(
            int(thread["id"]),
            direction="in",
            author_label=from_name or from_email,
            from_email=from_email,
            to_email=", ".join(_recipients(payload))[:300],
            subject=subject,
            body_text=body,
            body_html=str(payload.get("HtmlBody", "") or ""),
            postmark_message_id=str(payload.get("MessageID", "") or ""),
            in_reply_to=headers.get("in-reply-to", ""),
            attachments=attachments,
        )
        # A reply to a closed conversation reopens it: the alternative is
        # answering somebody into a folder nobody looks at.
        if str(thread.get("status")) != "open":
            email_threads.set_thread_status(int(thread["id"]), "open")

        log.info("Inbound mail from %s filed on thread %s (%s)", from_email, thread["id"], how)
        stored += 1

    return jsonify({"ok": True, "stored": stored}), 200


# ---------------------------------------------------------------------------
# Delivery events
# ---------------------------------------------------------------------------

# Bounce types that mean "this address will never work". Transient and soft
# bounces are recorded but not suppressed: a full mailbox on Tuesday is not a
# reason to stop mailing somebody on Friday.
_PERMANENT_BOUNCES = {
    "HardBounce",
    "BadEmailAddress",
    "SpamNotification",
    "SpamComplaint",
    "ManuallyDeactivated",
    "Unsubscribe",
    "Blocked",
}


@postmark_bp.route("/webhook/events", methods=["POST"])
@csrf.exempt
@limiter.limit("240 per minute")
def events_webhook():
    """Bounces, spam complaints, deliveries and subscription changes."""
    _authorize_webhook()

    handled = 0
    for payload in _payloads():
        record_type = str(payload.get("RecordType", "") or "").strip()
        email = str(
            payload.get("Email") or payload.get("Recipient") or payload.get("From") or ""
        ).strip()
        message_id = str(payload.get("MessageID", "") or "").strip()

        email_threads.record_event(
            record_type=record_type or "Unknown",
            email=email,
            message_id=message_id,
            summary=str(payload.get("Description") or payload.get("Details") or "")[:300],
            payload=payload,
        )

        if record_type == "Bounce":
            bounce_type = str(payload.get("Type", "") or "")
            detail = str(payload.get("Description", "") or payload.get("Details", "") or "")
            email_threads.record_delivery_state(message_id, "bounced", f"{bounce_type}: {detail}")
            if bounce_type in _PERMANENT_BOUNCES or bool(payload.get("Inactive")):
                email_threads.suppress(
                    email, reason=bounce_type or "Bounce", detail=detail, source="bounce"
                )
                log.warning("Suppressed %s after %s bounce", email, bounce_type)

        elif record_type == "SpamComplaint":
            email_threads.record_delivery_state(message_id, "spam-complaint")
            email_threads.suppress(
                email,
                reason="SpamComplaint",
                detail=str(payload.get("Details", "") or ""),
                source="spamcomplaint",
            )
            log.warning("Suppressed %s after a spam complaint", email)

        elif record_type == "Delivery":
            email_threads.record_delivery_state(
                message_id, "delivered", str(payload.get("Details", "") or "")
            )

        elif record_type == "SubscriptionChange":
            if payload.get("SuppressSending"):
                email_threads.suppress(
                    email,
                    reason=str(payload.get("SuppressionReason", "") or "Unsubscribed"),
                    detail=str(payload.get("Origin", "") or ""),
                    source="subscriptionchange",
                )
            else:
                email_threads.unsuppress(email)

        handled += 1

    return jsonify({"ok": True, "handled": handled}), 200


# ---------------------------------------------------------------------------
# Who is reading: the identity a participant already has
# ---------------------------------------------------------------------------

def _viewer() -> tuple[str, str, str]:
    """(owner_kind, owner_key, display name) for whoever is asking.

    GLOW has no user accounts, by choice. A conversation is owned by the same
    cookie identity that owns the work it came from -- a passport, or a
    workshop participant -- so reading your own messages needs nothing you do
    not already have.
    """
    participant_key = (request.cookies.get(PARTICIPANT_COOKIE) or "").strip()
    if participant_key:
        try:
            from ..workshop_store import get_participant

            participant = get_participant(participant_key)
        except Exception:  # pragma: no cover - defensive
            participant = None
        if participant:
            return (
                "workshop_participant",
                participant_key,
                str(participant.get("display_name", "") or "You"),
            )

    passport_id = (request.cookies.get(PASSPORT_COOKIE) or "").strip()
    if passport_id:
        try:
            from ..passport_store import get_passport

            passport = get_passport(passport_id, touch=False)
        except Exception:  # pragma: no cover - defensive
            passport = None
        if passport:
            return "passport", passport_id, "You"

    return "", "", ""


def _viewer_thread(thread_id: int) -> dict | None:
    """A thread, but only if it belongs to the person asking for it."""
    owner_kind, owner_key, _name = _viewer()
    if not owner_key:
        return None
    thread = email_threads.get_thread(thread_id)
    if not thread:
        return None
    if str(thread.get("owner_kind")) != owner_kind or str(thread.get("owner_key")) != owner_key:
        return None
    return thread


# ---------------------------------------------------------------------------
# Conversations, as a participant sees them
# ---------------------------------------------------------------------------

@postmark_bp.route("/conversations", methods=["GET"])
def conversations():
    """Every conversation this person has with GLOW, newest first."""
    owner_kind, owner_key, display_name = _viewer()
    message, message_is_error = _message()
    threads = (
        email_threads.list_threads(owner_kind=owner_kind, owner_key=owner_key)
        if owner_key
        else []
    )
    return render_template(
        "conversations.html",
        threads=threads,
        identified=bool(owner_key),
        display_name=display_name,
        available=conversations_available(),
        # When GLOW cannot hold a conversation itself, the help desk still
        # can. Pointing at a real, monitored address beats an apology.
        support_email=(
            load_helpdesk_config().support_email
            if helpdesk_configured()
            else os.environ.get("GLOW_SUPPORT_EMAIL", "").strip()
        ),
        message=message,
        message_is_error=message_is_error,
        status_prefix=("Not sent" if message_is_error else ("Sent" if message else "")),
    )


@postmark_bp.route("/conversations/<int:thread_id>", methods=["GET"])
def conversation(thread_id: int):
    """One conversation, in order, with a box to answer in."""
    thread = _viewer_thread(thread_id)
    if thread is None:
        abort(404)
    email_threads.mark_read(thread_id, by="participant")
    message, message_is_error = _message()
    return render_template(
        "conversation.html",
        thread=thread,
        messages=email_threads.list_messages(thread_id),
        available=conversations_available(),
        message=message,
        message_is_error=message_is_error,
        status_prefix=("Not sent" if message_is_error else ("Sent" if message else "")),
    )


@postmark_bp.route("/conversations/<int:thread_id>/reply", methods=["POST"])
@limiter.limit("20 per hour")
def conversation_reply(thread_id: int):
    """Answer from inside GLOW. The other side receives ordinary email."""
    thread = _viewer_thread(thread_id)
    if thread is None:
        abort(404)

    def _back(outcome: str):
        return redirect(url_for("postmark.conversation", thread_id=thread_id, m=outcome))

    body = (request.form.get("body") or "").strip()
    if not body:
        return _back("empty")
    if str(thread.get("status")) != "open":
        return _back("closed")
    if not conversations_available():
        return _back("unavailable")

    ok, _detail = send_thread_message(
        thread,
        body_text=body,
        author_label=str(thread.get("participant_name") or "You"),
    )
    return _back("sent" if ok else "send-failed")


@postmark_bp.route("/conversations/start", methods=["POST"])
@limiter.limit("10 per hour")
def conversation_start():
    """Open a new conversation with GLOW from inside the product."""
    owner_kind, owner_key, display_name = _viewer()
    if not owner_key:
        abort(404)

    def _back(outcome: str):
        return redirect(url_for("postmark.conversations", m=outcome))

    body = (request.form.get("body") or "").strip()
    subject = (request.form.get("subject") or "").strip() or "A question about GLOW"
    email = (request.form.get("email") or "").strip().lower()
    session_code = (request.form.get("session_code") or "").strip()

    if not body:
        return _back("empty")
    if not _EMAIL_RE.match(email):
        return _back("no-address")
    if not conversations_available():
        return _back("unavailable")

    thread = email_threads.create_thread(
        context_kind="workshop" if owner_kind == "workshop_participant" else "passport",
        context_id=owner_key,
        subject=subject,
        participant_email=email,
        participant_name=display_name,
        owner_kind=owner_kind,
        owner_key=owner_key,
        session_code=session_code,
    )
    ok, _detail = send_thread_message(
        thread, subject=subject, body_text=body, author_label=display_name or "Participant"
    )
    return _back("started" if ok else "send-failed")


# ---------------------------------------------------------------------------
# The staff side
# ---------------------------------------------------------------------------

def _require_staff() -> str:
    from .admin import is_authenticated_admin

    if not is_authenticated_admin():
        abort(403)
    from flask import session

    return str(session.get("admin_email", "") or "admin")


@postmark_bp.route("/admin", methods=["GET"])
def admin_threads():
    """Every conversation, and everything Postmark has told us lately."""
    _require_staff()
    message, message_is_error = _message()
    return render_template(
        "mail_admin.html",
        threads=email_threads.list_threads(limit=200),
        unread=email_threads.count_unread(for_staff=True),
        suppressions=email_threads.list_suppressions(limit=100),
        events=email_threads.list_events(limit=50),
        inbound_address=email_threads.inbound_address(),
        available=conversations_available(),
        email_ready=email_configured(),
        webhook_secret_set=bool(_webhook_secret()),
        inbound_url=url_for("postmark.inbound_webhook", _external=True),
        events_url=url_for("postmark.events_webhook", _external=True),
        helpdesk=helpdesk_status(),
        message=message,
        message_is_error=message_is_error,
        status_prefix=("Not done" if message_is_error else ("Done" if message else "")),
    )


@postmark_bp.route("/admin/<int:thread_id>", methods=["GET"])
def admin_thread(thread_id: int):
    """One conversation, from the staff side."""
    _require_staff()
    thread = email_threads.get_thread(thread_id)
    if thread is None:
        abort(404)
    email_threads.mark_read(thread_id, by="staff")
    message, message_is_error = _message()
    return render_template(
        "mail_admin_thread.html",
        thread=thread,
        messages=email_threads.list_messages(thread_id),
        available=conversations_available(),
        context_kinds=email_threads.CONTEXT_KINDS,
        message=message,
        message_is_error=message_is_error,
        status_prefix=("Not sent" if message_is_error else ("Sent" if message else "")),
    )


@postmark_bp.route("/admin/<int:thread_id>/reply", methods=["POST"])
def admin_reply(thread_id: int):
    """Answer a participant. They receive ordinary email and can reply again."""
    staff_email = _require_staff()
    thread = email_threads.get_thread(thread_id)
    if thread is None:
        abort(404)

    def _back(outcome: str):
        return redirect(url_for("postmark.admin_thread", thread_id=thread_id, m=outcome))

    body = (request.form.get("body") or "").strip()
    if not body:
        return _back("empty")
    if not conversations_available():
        return _back("unavailable")

    ok, _detail = send_thread_message(
        thread,
        subject=(request.form.get("subject") or "").strip(),
        body_text=body,
        author_label=f"GLOW ({staff_email})",
    )
    return _back("sent" if ok else "send-failed")


@postmark_bp.route("/admin/<int:thread_id>/status", methods=["POST"])
def admin_thread_status(thread_id: int):
    """Close a finished conversation, or reopen one."""
    _require_staff()
    wanted = (request.form.get("status") or "").strip()
    email_threads.set_thread_status(thread_id, wanted)
    return redirect(
        url_for(
            "postmark.admin_thread",
            thread_id=thread_id,
            m="thread-closed" if wanted == "closed" else "thread-reopened",
        )
    )


@postmark_bp.route("/admin/<int:thread_id>/assign", methods=["POST"])
def admin_thread_assign(thread_id: int):
    """Anchor a conversation that arrived without a context."""
    _require_staff()
    email_threads.assign_thread(
        thread_id,
        context_kind=(request.form.get("context_kind") or "").strip(),
        session_code=(request.form.get("session_code") or "").strip(),
    )
    return redirect(url_for("postmark.admin_thread", thread_id=thread_id, m="sent"))


@postmark_bp.route("/admin/<int:thread_id>/delete", methods=["POST"])
def admin_thread_delete(thread_id: int):
    """Delete a conversation and everything in it."""
    _require_staff()
    email_threads.delete_thread(thread_id)
    return redirect(url_for("postmark.admin_threads", m="deleted"))


@postmark_bp.route("/admin/suppressions/clear", methods=["POST"])
def admin_clear_suppression():
    """Let an address receive mail again after the underlying problem is fixed."""
    _require_staff()
    email_threads.unsuppress((request.form.get("email") or "").strip())
    return redirect(url_for("postmark.admin_threads", m="cleared"))


@postmark_bp.route("/admin/health", methods=["GET"])
def admin_health():
    """A machine-readable answer to "is two-way mail working?"."""
    _require_staff()
    response = make_response(
        jsonify(
            {
                "sending_configured": email_configured(),
                "inbound_address": email_threads.inbound_address(),
                "webhook_secret_set": bool(_webhook_secret()),
                "conversations_available": conversations_available(),
                "open_threads": len(email_threads.list_threads(status="open", limit=500)),
                "unread_for_staff": email_threads.count_unread(for_staff=True),
                "suppressed": email_threads.count_suppressions(),
                "inbound_webhook_url": url_for("postmark.inbound_webhook", _external=True),
                "events_webhook_url": url_for("postmark.events_webhook", _external=True),
                "helpdesk": helpdesk_status(),
            }
        )
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@postmark_bp.route("/admin/purge", methods=["POST"])
def admin_purge():
    """Apply the retention promise now rather than opportunistically."""
    _require_staff()
    removed = email_threads.purge_expired()
    current_app.logger.info("Purged %d expired conversations", removed)
    return redirect(url_for("postmark.admin_threads", m="deleted"))
