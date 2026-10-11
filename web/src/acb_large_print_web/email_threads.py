"""Two-way email for GLOW: threads, replies, bounces and suppressions.

GLOW has always been able to send. It could not listen. A participant who
replied to a workshop artifact email, a person who answered an audit report
with a question, an admin who hit Reply on a sign-in link -- every one of
them was writing to a no-reply address that dropped the message on the
floor. For a tool whose users are disproportionately people for whom email
*is* the accessible channel, that is not a missing nicety.

This module is the other half of :mod:`acb_large_print_web.email`. It keeps:

* Threads -- one conversation between GLOW and one person, anchored to
  whatever produced it (a workshop participant, a passport, an admin, a
  feedback entry) so the reply lands back in the right part of the product.
* Messages -- every outbound and inbound message in that thread, in order,
  with the Postmark message id so a delivery argument can be settled.
* Suppressions -- addresses Postmark told us to stop mailing. A hard bounce
  or a spam complaint is honoured everywhere at once, rather than re-sent by
  the next feature that happens to hold the address.
* Events -- the raw webhook record for anything that arrives.

Routing an inbound message back to its thread uses, in order:

1. The mailbox hash Postmark parses out of ``reply+<key>@inbound...``. This
   is the reliable path, and the one every GLOW message sets up.
2. ``In-Reply-To`` / ``References`` matched against the Postmark message id
   of an outbound message we stored.
3. The most recently active open thread for the sender's address.

If all three miss, the message still becomes a thread -- unassigned, visible
to an admin -- because silently discarding somebody's reply is the exact
failure this module exists to end.

Privacy follows the passport's rules: addresses are stored because a
conversation cannot work without them, message bodies are kept for a bounded
window, and one call deletes a thread and everything in it.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

try:  # Flask is present in the app, absent in a bare script or a cron job.
    from flask import current_app, has_app_context
except Exception:  # pragma: no cover - defensive
    current_app = None  # type: ignore[assignment]

    def has_app_context() -> bool:  # type: ignore[misc]
        return False


# How long a conversation is kept after its last message. Long enough that a
# reply three months after a workshop still lands in context, short enough
# that GLOW is not an email archive.
RETENTION_DAYS = 180

# Where an inbound message can be anchored. An allow-list rather than free
# text, so a webhook payload can never invent a context.
CONTEXT_KINDS = (
    "workshop",   # a training-platform participant
    "passport",   # someone with a GLOW passport
    "admin",      # staff-to-staff, or an admin access request
    "feedback",   # a reply to a feedback acknowledgement
    "audit",      # a question about a delivered report
    "inbound",    # arrived unsolicited; not yet anchored to anything
)

_VALID_KEY = re.compile(r"^[0-9a-f]{20}$")

# Where a quoted reply starts. Mail clients are not consistent, so this is a
# best effort that errs towards keeping text: showing a little quoted history
# is harmless, cutting somebody's actual sentence is not.
_QUOTE_MARKERS = (
    re.compile(r"^\s*On .{5,120}\bwrote:\s*$", re.MULTILINE),
    re.compile(r"^\s*-{2,}\s*Original Message\s*-{2,}\s*$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*From:\s.+$", re.MULTILINE),
    re.compile(r"^\s*_{10,}\s*$", re.MULTILINE),
    re.compile(r"^\s*Sent from my \w+", re.MULTILINE),
)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _instance_dir() -> Path:
    """The instance directory, with or without an application context.

    Webhook handling runs inside a request, but suppression checks are also
    made from a worker thread and from the send helpers, which may not have
    one. Falling back to the environment keeps a missing context from turning
    into a failed send.
    """
    if has_app_context() and current_app is not None:
        path = Path(current_app.instance_path)
    else:
        path = Path(os.environ.get("GLOW_INSTANCE_PATH", "instance"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _db_path() -> Path:
    return _instance_dir() / "email_threads.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS mail_threads ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " thread_key TEXT NOT NULL UNIQUE,"
        " context_kind TEXT NOT NULL,"
        " context_id TEXT NOT NULL DEFAULT '',"
        " owner_kind TEXT NOT NULL DEFAULT '',"
        " owner_key TEXT NOT NULL DEFAULT '',"
        " session_code TEXT NOT NULL DEFAULT '',"
        " subject TEXT NOT NULL DEFAULT '',"
        " participant_email TEXT NOT NULL DEFAULT '',"
        " participant_name TEXT NOT NULL DEFAULT '',"
        " status TEXT NOT NULL DEFAULT 'open',"
        " unread_for_staff INTEGER NOT NULL DEFAULT 0,"
        " unread_for_participant INTEGER NOT NULL DEFAULT 0,"
        " created_at_utc TEXT NOT NULL,"
        " updated_at_utc TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS mail_messages ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " thread_id INTEGER NOT NULL,"
        " direction TEXT NOT NULL,"
        " author_label TEXT NOT NULL DEFAULT '',"
        " from_email TEXT NOT NULL DEFAULT '',"
        " to_email TEXT NOT NULL DEFAULT '',"
        " subject TEXT NOT NULL DEFAULT '',"
        " body_text TEXT NOT NULL DEFAULT '',"
        " body_html TEXT NOT NULL DEFAULT '',"
        " postmark_message_id TEXT NOT NULL DEFAULT '',"
        " in_reply_to TEXT NOT NULL DEFAULT '',"
        " attachments_json TEXT NOT NULL DEFAULT '[]',"
        " delivery_state TEXT NOT NULL DEFAULT '',"
        " delivery_detail TEXT NOT NULL DEFAULT '',"
        " created_at_utc TEXT NOT NULL,"
        " FOREIGN KEY(thread_id) REFERENCES mail_threads(id)"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS mail_suppressions ("
        " email TEXT PRIMARY KEY,"
        " reason TEXT NOT NULL DEFAULT '',"
        " detail TEXT NOT NULL DEFAULT '',"
        " source TEXT NOT NULL DEFAULT '',"
        " created_at_utc TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS mail_events ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " record_type TEXT NOT NULL,"
        " email TEXT NOT NULL DEFAULT '',"
        " message_id TEXT NOT NULL DEFAULT '',"
        " summary TEXT NOT NULL DEFAULT '',"
        " payload_json TEXT NOT NULL DEFAULT '{}',"
        " created_at_utc TEXT NOT NULL"
        ")"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mail_messages_thread ON mail_messages(thread_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mail_messages_pmid ON mail_messages(postmark_message_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mail_threads_owner ON mail_threads(owner_kind, owner_key)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mail_threads_email ON mail_threads(participant_email)"
    )
    conn.commit()


def ensure_schema() -> None:
    """Create the tables now, so the first webhook is not the first write."""
    conn = _conn()
    conn.close()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _norm_email(value: str | None) -> str:
    return (value or "").strip().lower()


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------

def inbound_address() -> str:
    """The address GLOW asks people to reply to, or "" if none is set.

    This is the Postmark inbound address: either the server's own
    ``<hash>@inbound.postmarkapp.com`` or, once an inbound domain has its MX
    record, something readable like ``reply@inbound.letitglow.app``.
    """
    return os.environ.get("POSTMARK_INBOUND_ADDRESS", "").strip()


def inbound_configured() -> bool:
    return "@" in inbound_address()


def reply_address(thread_key: str) -> str:
    """``reply+<key>@inbound...`` -- the per-thread return address.

    Postmark parses everything after the ``+`` into ``MailboxHash`` on the
    inbound payload, which is how a reply finds its conversation without
    depending on the sender's mail client preserving headers.
    """
    base = inbound_address()
    if "@" not in base or not thread_key:
        return base
    local, _, domain = base.partition("@")
    local = local.split("+", 1)[0]
    return f"{local}+{thread_key}@{domain}"


def thread_key_from_address(address: str) -> str:
    """Pull the thread key back out of a ``reply+<key>@...`` address."""
    local = (address or "").strip().split("@", 1)[0]
    if "+" not in local:
        return ""
    candidate = local.split("+", 1)[1].strip().lower()
    return candidate if _VALID_KEY.match(candidate) else ""


# ---------------------------------------------------------------------------
# Threads
# ---------------------------------------------------------------------------

def _row_to_thread(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    thread = dict(row)
    thread["reply_address"] = reply_address(str(thread.get("thread_key", "")))
    return thread


def create_thread(
    *,
    context_kind: str,
    subject: str,
    participant_email: str,
    participant_name: str = "",
    context_id: str = "",
    owner_kind: str = "",
    owner_key: str = "",
    session_code: str = "",
) -> dict:
    """Open a conversation and return it, reply address included."""
    if context_kind not in CONTEXT_KINDS:
        context_kind = "inbound"
    now = _utc_now()
    conn = _conn()
    try:
        for _ in range(5):
            key = secrets.token_hex(10)
            try:
                cursor = conn.execute(
                    "INSERT INTO mail_threads ("
                    " thread_key, context_kind, context_id, owner_kind, owner_key,"
                    " session_code, subject, participant_email, participant_name,"
                    " status, created_at_utc, updated_at_utc"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)",
                    (
                        key,
                        context_kind,
                        context_id,
                        owner_kind,
                        owner_key,
                        session_code,
                        subject.strip(),
                        _norm_email(participant_email),
                        participant_name.strip(),
                        now,
                        now,
                    ),
                )
                conn.commit()
                row = conn.execute(
                    "SELECT * FROM mail_threads WHERE id=?", (cursor.lastrowid,)
                ).fetchone()
                return _row_to_thread(row) or {}
            except sqlite3.IntegrityError:
                continue  # astronomically unlikely key collision; try again
        raise RuntimeError("could not allocate a thread key")
    finally:
        conn.close()


def get_thread(thread_id: int) -> dict | None:
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM mail_threads WHERE id=?", (int(thread_id),)).fetchone()
        return _row_to_thread(row)
    finally:
        conn.close()


def get_thread_by_key(thread_key: str) -> dict | None:
    key = (thread_key or "").strip().lower()
    if not _VALID_KEY.match(key):
        return None
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM mail_threads WHERE thread_key=?", (key,)).fetchone()
        return _row_to_thread(row)
    finally:
        conn.close()


def find_or_create_thread(
    *,
    context_kind: str,
    context_id: str,
    subject: str,
    participant_email: str,
    participant_name: str = "",
    owner_kind: str = "",
    owner_key: str = "",
    session_code: str = "",
) -> dict:
    """Reuse the open conversation for this person and context, or start one.

    A participant who gets their artifact emailed twice should not end up
    with two conversations; a participant who writes about something new a
    month later should not have it buried under an old subject line. The
    compromise is: same context, same address, still open -- same thread.
    """
    email = _norm_email(participant_email)
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM mail_threads WHERE context_kind=? AND context_id=? AND"
            " participant_email=? AND status='open' ORDER BY updated_at_utc DESC LIMIT 1",
            (context_kind, context_id, email),
        ).fetchone()
    finally:
        conn.close()
    existing = _row_to_thread(row)
    if existing:
        return existing
    return create_thread(
        context_kind=context_kind,
        context_id=context_id,
        subject=subject,
        participant_email=email,
        participant_name=participant_name,
        owner_kind=owner_kind,
        owner_key=owner_key,
        session_code=session_code,
    )


def list_threads(
    *,
    owner_kind: str = "",
    owner_key: str = "",
    context_kind: str = "",
    session_code: str = "",
    status: str = "",
    limit: int = 100,
) -> list[dict]:
    clauses: list[str] = []
    params: list[object] = []
    if owner_kind:
        clauses.append("t.owner_kind=?")
        params.append(owner_kind)
    if owner_key:
        clauses.append("t.owner_key=?")
        params.append(owner_key)
    if context_kind:
        clauses.append("t.context_kind=?")
        params.append(context_kind)
    if session_code:
        clauses.append("t.session_code=?")
        params.append(session_code)
    if status:
        clauses.append("t.status=?")
        params.append(status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT t.*,"
            " (SELECT COUNT(*) FROM mail_messages m WHERE m.thread_id = t.id) AS message_count,"
            " (SELECT m.body_text FROM mail_messages m WHERE m.thread_id = t.id"
            "  ORDER BY m.id DESC LIMIT 1) AS last_body"
            " FROM mail_threads t"
            + where
            + " ORDER BY t.updated_at_utc DESC LIMIT ?",
            (*params, int(limit)),
        ).fetchall()
    finally:
        conn.close()
    threads = []
    for row in rows:
        thread = _row_to_thread(row) or {}
        thread["preview"] = summarize(str(thread.get("last_body") or ""))
        threads.append(thread)
    return threads


def set_thread_status(thread_id: int, status: str) -> None:
    if status not in ("open", "closed"):
        return
    conn = _conn()
    try:
        conn.execute(
            "UPDATE mail_threads SET status=?, updated_at_utc=? WHERE id=?",
            (status, _utc_now(), int(thread_id)),
        )
        conn.commit()
    finally:
        conn.close()


def assign_thread(
    thread_id: int,
    *,
    context_kind: str = "",
    context_id: str = "",
    owner_kind: str = "",
    owner_key: str = "",
    session_code: str = "",
) -> None:
    """Anchor a thread that arrived without one, from the admin view."""
    sets: list[str] = []
    params: list[object] = []
    if context_kind in CONTEXT_KINDS:
        sets.append("context_kind=?")
        params.append(context_kind)
    for column, value in (
        ("context_id", context_id),
        ("owner_kind", owner_kind),
        ("owner_key", owner_key),
        ("session_code", session_code),
    ):
        if value:
            sets.append(f"{column}=?")
            params.append(value)
    if not sets:
        return
    conn = _conn()
    try:
        conn.execute(
            f"UPDATE mail_threads SET {', '.join(sets)}, updated_at_utc=? WHERE id=?",
            (*params, _utc_now(), int(thread_id)),
        )
        conn.commit()
    finally:
        conn.close()


def mark_read(thread_id: int, *, by: str) -> None:
    """Clear the unread marker for ``staff`` or ``participant``."""
    column = "unread_for_staff" if by == "staff" else "unread_for_participant"
    conn = _conn()
    try:
        conn.execute(f"UPDATE mail_threads SET {column}=0 WHERE id=?", (int(thread_id),))
        conn.commit()
    finally:
        conn.close()


def count_unread(*, for_staff: bool = True, owner_kind: str = "", owner_key: str = "") -> int:
    column = "unread_for_staff" if for_staff else "unread_for_participant"
    clauses = [f"{column}=1"]
    params: list[object] = []
    if owner_kind:
        clauses.append("owner_kind=?")
        params.append(owner_kind)
    if owner_key:
        clauses.append("owner_key=?")
        params.append(owner_key)
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM mail_threads WHERE " + " AND ".join(clauses), tuple(params)
        ).fetchone()
        return int(row[0])
    finally:
        conn.close()


def delete_thread(thread_id: int) -> int:
    """Delete a conversation and its messages. Returns messages removed."""
    conn = _conn()
    try:
        removed = conn.execute(
            "SELECT COUNT(*) FROM mail_messages WHERE thread_id=?", (int(thread_id),)
        ).fetchone()[0]
        conn.execute("DELETE FROM mail_messages WHERE thread_id=?", (int(thread_id),))
        conn.execute("DELETE FROM mail_threads WHERE id=?", (int(thread_id),))
        conn.commit()
        return int(removed)
    finally:
        conn.close()


def purge_expired(*, days: int | None = None) -> int:
    """Delete conversations untouched for the retention window."""
    window = days if days is not None else RETENTION_DAYS
    cutoff = (datetime.now(UTC) - timedelta(days=window)).isoformat()
    conn = _conn()
    try:
        ids = [
            int(row[0])
            for row in conn.execute(
                "SELECT id FROM mail_threads WHERE updated_at_utc < ?", (cutoff,)
            ).fetchall()
        ]
        for thread_id in ids:
            conn.execute("DELETE FROM mail_messages WHERE thread_id=?", (thread_id,))
        conn.execute("DELETE FROM mail_threads WHERE updated_at_utc < ?", (cutoff,))
        conn.commit()
        return len(ids)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def add_message(
    thread_id: int,
    *,
    direction: str,
    body_text: str,
    body_html: str = "",
    subject: str = "",
    from_email: str = "",
    to_email: str = "",
    author_label: str = "",
    postmark_message_id: str = "",
    in_reply_to: str = "",
    attachments: tuple[str, ...] = (),
    delivery_state: str = "",
    delivery_detail: str = "",
) -> int:
    """Append a message, and mark the thread unread for the other side."""
    if direction not in ("in", "out"):
        raise ValueError("direction must be 'in' or 'out'")
    now = _utc_now()
    conn = _conn()
    try:
        cursor = conn.execute(
            "INSERT INTO mail_messages ("
            " thread_id, direction, author_label, from_email, to_email, subject,"
            " body_text, body_html, postmark_message_id, in_reply_to,"
            " attachments_json, delivery_state, delivery_detail, created_at_utc"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                int(thread_id),
                direction,
                author_label,
                _norm_email(from_email),
                _norm_email(to_email),
                subject,
                body_text,
                body_html,
                (postmark_message_id or "").strip(),
                in_reply_to,
                json.dumps(list(attachments)),
                delivery_state,
                delivery_detail,
                now,
            ),
        )
        unread = "unread_for_staff" if direction == "in" else "unread_for_participant"
        conn.execute(
            f"UPDATE mail_threads SET updated_at_utc=?, {unread}=1 WHERE id=?",
            (now, int(thread_id)),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)
    finally:
        conn.close()


def list_messages(thread_id: int, *, limit: int = 200) -> list[dict]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM mail_messages WHERE thread_id=? ORDER BY id ASC LIMIT ?",
            (int(thread_id), int(limit)),
        ).fetchall()
    finally:
        conn.close()
    messages = []
    for row in rows:
        message = dict(row)
        try:
            message["attachments"] = json.loads(message.get("attachments_json") or "[]")
        except (TypeError, ValueError):
            message["attachments"] = []
        messages.append(message)
    return messages


def record_delivery_state(postmark_message_id: str, state: str, detail: str = "") -> int:
    """Mark what Postmark said happened to an outbound message."""
    message_id = (postmark_message_id or "").strip()
    if not message_id:
        return 0
    conn = _conn()
    try:
        cursor = conn.execute(
            "UPDATE mail_messages SET delivery_state=?, delivery_detail=?"
            " WHERE postmark_message_id=?",
            (state, detail[:500], message_id),
        )
        conn.commit()
        return int(cursor.rowcount or 0)
    finally:
        conn.close()


def thread_for_postmark_message_id(message_id: str) -> dict | None:
    ident = (message_id or "").strip().strip("<>")
    if not ident:
        return None
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT t.* FROM mail_threads t JOIN mail_messages m ON m.thread_id = t.id"
            " WHERE m.postmark_message_id = ? ORDER BY m.id DESC LIMIT 1",
            (ident,),
        ).fetchone()
        return _row_to_thread(row)
    finally:
        conn.close()


def latest_open_thread_for(email: str) -> dict | None:
    address = _norm_email(email)
    if not address:
        return None
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT * FROM mail_threads WHERE participant_email=? AND status='open'"
            " ORDER BY updated_at_utc DESC LIMIT 1",
            (address,),
        ).fetchone()
        return _row_to_thread(row)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Suppressions
# ---------------------------------------------------------------------------

def suppress(email: str, *, reason: str, detail: str = "", source: str = "") -> None:
    address = _norm_email(email)
    if not address:
        return
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO mail_suppressions (email, reason, detail, source, created_at_utc)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(email) DO UPDATE SET reason=excluded.reason,"
            " detail=excluded.detail, source=excluded.source,"
            " created_at_utc=excluded.created_at_utc",
            (address, reason, detail[:500], source, _utc_now()),
        )
        conn.commit()
    finally:
        conn.close()


def unsuppress(email: str) -> bool:
    address = _norm_email(email)
    if not address:
        return False
    conn = _conn()
    try:
        cursor = conn.execute("DELETE FROM mail_suppressions WHERE email=?", (address,))
        conn.commit()
        return bool(cursor.rowcount)
    finally:
        conn.close()


def is_suppressed(email: str) -> bool:
    """True if Postmark told us to stop mailing this address."""
    address = _norm_email(email)
    if not address:
        return False
    conn = _conn()
    try:
        row = conn.execute("SELECT 1 FROM mail_suppressions WHERE email=?", (address,)).fetchone()
        return row is not None
    finally:
        conn.close()


def suppression_for(email: str) -> dict | None:
    address = _norm_email(email)
    if not address:
        return None
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM mail_suppressions WHERE email=?", (address,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_suppressions(*, limit: int = 200) -> list[dict]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM mail_suppressions ORDER BY created_at_utc DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def count_suppressions() -> int:
    conn = _conn()
    try:
        return int(conn.execute("SELECT COUNT(*) FROM mail_suppressions").fetchone()[0])
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def record_event(
    *,
    record_type: str,
    email: str = "",
    message_id: str = "",
    summary: str = "",
    payload: dict | None = None,
) -> int:
    conn = _conn()
    try:
        cursor = conn.execute(
            "INSERT INTO mail_events"
            " (record_type, email, message_id, summary, payload_json, created_at_utc)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                record_type,
                _norm_email(email),
                (message_id or "").strip(),
                summary[:300],
                json.dumps(payload or {})[:20000],
                _utc_now(),
            ),
        )
        conn.commit()
        return int(cursor.lastrowid or 0)
    finally:
        conn.close()


def list_events(*, limit: int = 100, record_type: str = "") -> list[dict]:
    conn = _conn()
    try:
        if record_type:
            rows = conn.execute(
                "SELECT * FROM mail_events WHERE record_type=? ORDER BY id DESC LIMIT ?",
                (record_type, int(limit)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM mail_events ORDER BY id DESC LIMIT ?", (int(limit),)
            ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Reply text
# ---------------------------------------------------------------------------

def strip_quoted_reply(text: str) -> str:
    """Trim the quoted history off an inbound reply.

    Postmark's ``StrippedTextReply`` does this well and is preferred where it
    is present; this is the fallback for the cases where it is empty, and for
    text that came from ``TextBody``.
    """
    body = (text or "").replace("\r\n", "\n")
    cut = len(body)
    for marker in _QUOTE_MARKERS:
        match = marker.search(body)
        if match and match.start() < cut:
            cut = match.start()
    trimmed = body[:cut].strip()
    # A reply that is nothing but quoted history should not become an empty
    # message; keeping the original is better than losing it.
    return trimmed or body.strip()


def summarize(text: str, *, length: int = 140) -> str:
    """A one-line preview for a thread list."""
    collapsed = " ".join((text or "").split())
    if len(collapsed) <= length:
        return collapsed
    return collapsed[: length - 1].rstrip() + "..."
