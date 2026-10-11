"""Filing a GLOW support ticket into FreeScout, without a second inbox.

`support@community-access.org` is answered by FreeScout on lp.csedesigns.com.
It expects mail over IMAP; Postmark, which receives that mail, has no IMAP, so
a small bridge (``feedback_hub.mailbridge``) takes Postmark's inbound webhook,
writes the raw RFC-822 message into a Maildir, and a localhost-only Dovecot
serves that Maildir to FreeScout::

    Postmark inbound --webhook--> mailbridge --> Maildir --> Dovecot --> FreeScout

This module posts to the same bridge, with the same payload shape, from inside
GLOW. That is the whole trick: a ticket raised in the product arrives at the
help desk as an ordinary email from the person who raised it, so FreeScout does
what it was written to do -- threads it, assigns it, replies to the customer,
reactivates the conversation when they answer -- and GLOW does not become a
second, worse help desk sitting alongside the real one.

**Why not FreeScout's API.** Creating a conversation through the API means
reimplementing the part of FreeScout worth having: `Message-ID` and
`In-Reply-To` matching, duplicate detection, customer-versus-agent replies,
auto-reply and bounce handling. The bridge's own documentation makes this
argument for inbound mail and it holds here too.

**Why not send it through Postmark.** Postmark will only send from a verified
domain, so the message would arrive `From: no-reply@notify.letitglow.app` and
FreeScout would file every ticket in the product against GLOW rather than
against the person who wrote it. Posting to the bridge directly puts the right
address in `From`, costs no Postmark send, and does not depend on the public
internet: on lp.csedesigns.com the bridge is attached to the same Docker
network GLOW runs on, reachable as ``helpdesk-mailbridge:8096``.

**The address in `From` is not verified, and the ticket says so.** Somebody can
type any address into a feedback form, and a help desk that replies to it would
be a way to send mail to a stranger over somebody else's signature. Every
message carries ``X-GLOW-Address-Verified: no`` and a line in the body saying
the same thing in words, so an agent about to reply can see what they are
replying to. Removing that line is not a tidy-up.

Configuration (environment variables):
  HELPDESK_BRIDGE_URL       -- The bridge's webhook, e.g.
                               http://helpdesk-mailbridge:8096/postmark/inbound
  HELPDESK_BRIDGE_USER      -- Its MAILBRIDGE_WEBHOOK_USER
  HELPDESK_BRIDGE_PASSWORD  -- Its MAILBRIDGE_WEBHOOK_PASSWORD
  HELPDESK_SUPPORT_EMAIL    -- Recipient. Must be in the bridge's
                               MAILBRIDGE_RECIPIENTS allow-list, or the bridge
                               returns 403. Default support@community-access.org
  HELPDESK_URL              -- Shown to people, not used to send. Default
                               https://helpdesk.community-access.org
  HELPDESK_MESSAGE_DOMAIN   -- Domain for generated Message-IDs.
                               Default letitglow.app
  HELPDESK_CATEGORIES       -- Which categories open a ticket, or "all".
                               Default bug,accessibility,regression,support

With no bridge URL or no credentials, nothing is filed and nothing fails: the
feedback entry is still stored and still reaches GitHub. A help desk that is
not configured yet must not be able to lose somebody's bug report.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import format_datetime, formataddr, make_msgid
from urllib import error as urlerror
from urllib import request as urlrequest

log = logging.getLogger(__name__)

# Which feedback deserves a conversation with a person. Praise and general
# comments are stored and still reach the admin list; they do not open a
# ticket somebody has to close. Same rule the GitHub side already applies,
# repeated rather than imported so the two can diverge if they should.
DEFAULT_TICKET_CATEGORIES = ("bug", "accessibility", "regression", "support")

# Returned as the "error" when a ticket was deliberately not filed. Callers
# distinguish this from a failure: nothing went wrong.
SKIP_PREFIX = "skipped: "

_DEFAULT_SUPPORT_EMAIL = "support@community-access.org"
_DEFAULT_HELPDESK_URL = "https://helpdesk.community-access.org"
_DEFAULT_MESSAGE_DOMAIN = "letitglow.app"
_REQUEST_TIMEOUT = 10  # seconds


@dataclass(frozen=True, slots=True)
class HelpdeskConfig:
    bridge_url: str
    user: str
    password: str
    support_email: str
    helpdesk_url: str
    message_domain: str
    categories: tuple[str, ...]

    @property
    def configured(self) -> bool:
        """Everything needed to actually deliver a ticket."""
        return bool(self.bridge_url and self.user and self.password and self.support_email)


def load_helpdesk_config() -> HelpdeskConfig:
    raw_categories = os.environ.get("HELPDESK_CATEGORIES", "").strip()
    if raw_categories.lower() == "all":
        categories: tuple[str, ...] = ()
    elif raw_categories:
        categories = tuple(
            item.strip().lower() for item in raw_categories.split(",") if item.strip()
        )
    else:
        categories = DEFAULT_TICKET_CATEGORIES

    return HelpdeskConfig(
        bridge_url=os.environ.get("HELPDESK_BRIDGE_URL", "").strip(),
        user=os.environ.get("HELPDESK_BRIDGE_USER", "").strip(),
        password=os.environ.get("HELPDESK_BRIDGE_PASSWORD", "").strip(),
        support_email=os.environ.get("HELPDESK_SUPPORT_EMAIL", "").strip()
        or _DEFAULT_SUPPORT_EMAIL,
        helpdesk_url=os.environ.get("HELPDESK_URL", "").strip() or _DEFAULT_HELPDESK_URL,
        message_domain=os.environ.get("HELPDESK_MESSAGE_DOMAIN", "").strip()
        or _DEFAULT_MESSAGE_DOMAIN,
        categories=categories,
    )


def helpdesk_configured() -> bool:
    return load_helpdesk_config().configured


def helpdesk_status() -> dict:
    """What an admin needs to know, with nothing secret in it."""
    config = load_helpdesk_config()
    return {
        "configured": config.configured,
        "bridge_url": config.bridge_url,
        "support_email": config.support_email,
        "helpdesk_url": config.helpdesk_url,
        "credentials_set": bool(config.user and config.password),
        "categories": list(config.categories) or ["all"],
    }


# ---------------------------------------------------------------------------
# Should this one become a ticket?
# ---------------------------------------------------------------------------

def should_open_ticket(entry: dict) -> tuple[bool, str]:
    """(open it, reason not to). The reason carries :data:`SKIP_PREFIX`.

    Two conditions, and the second is the one that matters. A ticket is a
    promise that somebody will answer; without an address there is nobody to
    answer, and an unanswerable ticket in a queue is worse than no ticket --
    it is an agent's time spent discovering they cannot help.
    """
    config = load_helpdesk_config()
    if not config.configured:
        return False, f"{SKIP_PREFIX}help desk is not configured"

    email = str(entry.get("email", "") or "").strip()
    if not email or "@" not in email:
        return False, f"{SKIP_PREFIX}no address to reply to"

    if config.categories:
        category = str(entry.get("category", "") or "").strip().lower()
        if category not in config.categories:
            return (
                False,
                f"{SKIP_PREFIX}category {category or 'none'!s} does not open a ticket",
            )

    return True, ""


# ---------------------------------------------------------------------------
# The message
# ---------------------------------------------------------------------------

def _context_lines(entry: dict) -> list[str]:
    """The facts an agent needs before they can start, in a fixed order."""
    fields = (
        ("Application", entry.get("source_app")),
        ("Version", entry.get("source_version")),
        ("Channel", entry.get("source_channel")),
        ("Platform", entry.get("platform")),
        ("Category", entry.get("category")),
        ("Rating", entry.get("rating")),
        ("Task in progress", entry.get("task")),
        ("GLOW feedback id", entry.get("id")),
        ("Tracker issue", entry.get("github_issue_url")),
    )
    return [f"{label}: {value}" for label, value in fields if value not in (None, "")]


def build_ticket_message(entry: dict, *, config: HelpdeskConfig | None = None) -> tuple[bytes, str]:
    """Render *entry* as an RFC-822 message. Returns (raw bytes, Message-ID).

    Plain text only, and no HTML alternative. A help desk conversation is read
    by agents and quoted back to customers; a text body survives both without
    a rendering engine's opinion in the middle of it.
    """
    config = config or load_helpdesk_config()

    name = str(entry.get("name", "") or "").strip()
    email = str(entry.get("email", "") or "").strip()
    summary = str(entry.get("summary", "") or "").strip()
    category = str(entry.get("category", "") or "").strip()
    subject = summary or f"GLOW {category or 'support'} request"

    message_id = make_msgid(domain=config.message_domain)

    body_parts = [str(entry.get("message", "") or "").strip(), ""]

    context = _context_lines(entry)
    if context:
        body_parts += ["--", "Submitted from GLOW:", *context, ""]

    metadata = str(entry.get("metadata_json", "") or "").strip()
    if metadata and metadata not in ("{}", "null"):
        try:
            parsed = json.loads(metadata)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict) and parsed:
            body_parts += [
                "Additional details:",
                *[f"{key}: {value}" for key, value in sorted(parsed.items())],
                "",
            ]

    body_parts += [
        "--",
        "This address was typed into a form in GLOW and has not been verified.",
        "Check that the person you are replying to is the person who wrote in.",
        "",
    ]

    message = EmailMessage()
    message["From"] = formataddr((name or "GLOW user", email))
    message["To"] = config.support_email
    message["Subject"] = subject
    message["Message-ID"] = message_id
    message["Date"] = format_datetime(datetime.now(UTC))
    message["X-GLOW-Source"] = str(entry.get("source_app", "") or "GLOW")
    message["X-GLOW-Feedback-Id"] = str(entry.get("id", "") or "")
    message["X-GLOW-Address-Verified"] = "no"
    # Not an auto-reply: a person pressed submit. Saying otherwise would make
    # FreeScout treat a real request as machine noise.
    message["Auto-Submitted"] = "no"
    message.set_content("\n".join(body_parts))

    return message.as_bytes(), message_id


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------

def file_ticket(entry: dict) -> tuple[str | None, str | None]:
    """File *entry* as a help desk ticket. Returns (Message-ID, error).

    Both halves are optional and exactly one is meaningful:

    * ``(message_id, None)``            -- filed.
    * ``(None, "skipped: ...")``        -- deliberately not filed.
    * ``(None, "some failure")``        -- tried and could not.

    Nothing raises. The feedback entry is already stored by the time this is
    called, so a help desk that is down costs a ticket, not a bug report.
    """
    open_it, skip_reason = should_open_ticket(entry)
    if not open_it:
        return None, skip_reason

    config = load_helpdesk_config()
    raw, message_id = build_ticket_message(entry, config=config)

    payload = {
        # The bridge writes this out byte for byte. It is the whole message.
        "RawEmail": raw.decode("utf-8", errors="replace"),
        # The envelope recipient the bridge checks against its allow-list.
        "OriginalRecipient": config.support_email,
        # The dedup key. Our own Message-ID is stable for this submission, so
        # a retry of the same ticket collapses rather than opening a second.
        "MessageID": message_id.strip("<>"),
        "From": str(entry.get("email", "") or ""),
        "Subject": str(entry.get("summary", "") or ""),
    }

    credential = base64.b64encode(
        f"{config.user}:{config.password}".encode()
    ).decode("ascii")
    request = urlrequest.Request(
        config.bridge_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {credential}",
            "User-Agent": "GLOW-helpdesk/1.0",
        },
        method="POST",
    )

    try:
        with urlrequest.urlopen(request, timeout=_REQUEST_TIMEOUT) as response:
            if 200 <= response.status < 300:
                log.info("Help desk ticket filed for feedback id=%s", entry.get("id"))
                return message_id, None
            return None, f"help desk returned HTTP {response.status}"
    except urlerror.HTTPError as exc:
        # The bridge's status codes say what to do about it, so translate them
        # into something an administrator reading the feedback list can act on.
        detail = {
            401: "help desk rejected the credentials (HELPDESK_BRIDGE_USER/PASSWORD)",
            403: (
                f"help desk does not accept mail for {config.support_email} "
                "(check the bridge's MAILBRIDGE_RECIPIENTS)"
            ),
            413: "ticket was larger than the help desk accepts",
        }.get(exc.code, f"help desk returned HTTP {exc.code}")
        log.warning("Help desk ticket not filed: %s", detail)
        return None, detail
    except urlerror.URLError as exc:
        log.warning("Help desk unreachable: %s", exc.reason)
        return None, f"help desk is unreachable: {exc.reason}"
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("Unexpected help desk failure")
        return None, f"help desk error: {exc}"
