"""The GLOW passport: one optional identity, no password, no sign-up wall.

A person who has carefully tuned a type scale, a contrast mode, reduced
motion and the cognitive-accessibility profile should not have to rebuild
that on a phone, or after a shared machine clears its cookies. Those are
exactly the people this tool exists for, and until now their configuration
lived in one browser's local storage and nowhere else.

A passport is: an opaque id in a cookie, an optional email address, a
settings blob, and two explicit opt-ins (notifications, history). It is
created only when someone asks for one, every surface keeps working without
it, and one control deletes it.

Design rules, carried over from the workshop return links this generalises:

* Tokens are single use, hashed at rest, and time-boxed. A copy of the
  database yields no working links.
* Retention is 90 days from last use, sliding. A returning visitor resets the
  clock; a passport nobody has used for three months is deleted, along with
  the address and anything else it held.
* History records what someone worked on, so it is off unless they turn it on,
  and turning settings on must never turn history on.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from flask import current_app

COOKIE_NAME = "glow_passport"

# Retention, decided 21 August: 90 days from last use, matching the workshop
# participant cookie's existing lifetime.
RETENTION_DAYS = 90
LINK_TTL_DAYS = 14

# Where a return link may land. An allow-list rather than a URL, so a link in
# an email can never be turned into an open redirect.
RETURN_DESTINATIONS = {
    "passport": "passport.passport_page",
    "settings": "settings.settings_page",
    "home": "main.index",
}


def _db_path() -> Path:
    p = Path(current_app.instance_path)
    p.mkdir(parents=True, exist_ok=True)
    return p / "passport.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS passports ("
        " passport_id TEXT PRIMARY KEY,"
        " email TEXT,"
        " display_name TEXT,"
        " settings_json TEXT NOT NULL DEFAULT '{}',"
        " notify_enabled INTEGER NOT NULL DEFAULT 0,"
        " history_enabled INTEGER NOT NULL DEFAULT 0,"
        " created_at_utc TEXT NOT NULL,"
        " updated_at_utc TEXT NOT NULL,"
        " last_seen_at_utc TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS passport_links ("
        " token_hash TEXT PRIMARY KEY,"
        " passport_id TEXT NOT NULL,"
        " created_at_utc TEXT NOT NULL,"
        " expires_at_utc TEXT NOT NULL,"
        " used_at_utc TEXT"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS passport_history ("
        " id INTEGER PRIMARY KEY AUTOINCREMENT,"
        " passport_id TEXT NOT NULL,"
        " kind TEXT NOT NULL,"
        " label TEXT NOT NULL,"
        " score INTEGER,"
        " grade TEXT,"
        " created_at_utc TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_passport_history_owner "
        "ON passport_history(passport_id, created_at_utc DESC)"
    )
    conn.commit()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def retention_days() -> int:
    raw = (os.environ.get("GLOW_PASSPORT_RETENTION_DAYS") or "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return RETENTION_DAYS


def link_ttl_days() -> int:
    raw = (os.environ.get("GLOW_PASSPORT_LINK_TTL_DAYS") or "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return LINK_TTL_DAYS


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Passports
# ---------------------------------------------------------------------------


def create_passport(
    *,
    settings: dict | None = None,
    email: str = "",
    display_name: str = "",
    notify_enabled: bool = False,
    history_enabled: bool = False,
) -> str:
    """Issue a passport and return its id. Called only when somebody asks."""
    passport_id = secrets.token_urlsafe(24)
    now = _utc_now()
    conn = _conn()
    conn.execute(
        "INSERT INTO passports (passport_id, email, display_name, settings_json, "
        "notify_enabled, history_enabled, created_at_utc, updated_at_utc, last_seen_at_utc) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            passport_id,
            (email or "").strip() or None,
            (display_name or "").strip() or None,
            json.dumps(settings or {}),
            1 if notify_enabled else 0,
            1 if history_enabled else 0,
            now,
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return passport_id


def get_passport(passport_id: str, *, touch: bool = True) -> dict | None:
    """Read a passport, refreshing its retention clock by default."""
    key = (passport_id or "").strip()
    if not key:
        return None
    conn = _conn()
    row = conn.execute(
        "SELECT passport_id, email, display_name, settings_json, notify_enabled, "
        "history_enabled, created_at_utc, updated_at_utc, last_seen_at_utc "
        "FROM passports WHERE passport_id=?",
        (key,),
    ).fetchone()
    if row is None:
        conn.close()
        return None
    if touch:
        conn.execute(
            "UPDATE passports SET last_seen_at_utc=? WHERE passport_id=?",
            (_utc_now(), key),
        )
        conn.commit()
    conn.close()

    record = dict(row)
    try:
        record["settings"] = json.loads(record.pop("settings_json") or "{}")
    except (TypeError, ValueError):
        record["settings"] = {}
    record["notify_enabled"] = bool(record.get("notify_enabled"))
    record["history_enabled"] = bool(record.get("history_enabled"))
    return record


def update_passport(
    passport_id: str,
    *,
    settings: dict | None = None,
    email: str | None = None,
    display_name: str | None = None,
    notify_enabled: bool | None = None,
    history_enabled: bool | None = None,
) -> None:
    """Update only what was passed. Unmentioned fields are left alone."""
    key = (passport_id or "").strip()
    if not key:
        return
    sets: list[str] = []
    values: list[object] = []
    if settings is not None:
        sets.append("settings_json=?")
        values.append(json.dumps(settings))
    if email is not None:
        sets.append("email=?")
        values.append(email.strip() or None)
    if display_name is not None:
        sets.append("display_name=?")
        values.append(display_name.strip() or None)
    if notify_enabled is not None:
        sets.append("notify_enabled=?")
        values.append(1 if notify_enabled else 0)
    if history_enabled is not None:
        sets.append("history_enabled=?")
        values.append(1 if history_enabled else 0)
    if not sets:
        return
    now = _utc_now()
    sets += ["updated_at_utc=?", "last_seen_at_utc=?"]
    values += [now, now, key]

    conn = _conn()
    conn.execute(f"UPDATE passports SET {', '.join(sets)} WHERE passport_id=?", values)
    conn.commit()
    conn.close()


def forget_passport(passport_id: str) -> dict:
    """Delete a passport and everything attached to it.

    Returns what was deleted, so the page can say so plainly rather than
    claiming success in the abstract.
    """
    key = (passport_id or "").strip()
    summary = {"passport": False, "email": False, "history_entries": 0, "links": 0}
    if not key:
        return summary

    conn = _conn()
    row = conn.execute(
        "SELECT email FROM passports WHERE passport_id=?", (key,)
    ).fetchone()
    if row is None:
        conn.close()
        return summary

    summary["passport"] = True
    summary["email"] = bool(row["email"])
    summary["history_entries"] = int(
        conn.execute(
            "SELECT COUNT(*) AS n FROM passport_history WHERE passport_id=?", (key,)
        ).fetchone()["n"]
    )
    summary["links"] = int(
        conn.execute(
            "SELECT COUNT(*) AS n FROM passport_links WHERE passport_id=?", (key,)
        ).fetchone()["n"]
    )

    conn.execute("DELETE FROM passport_history WHERE passport_id=?", (key,))
    conn.execute("DELETE FROM passport_links WHERE passport_id=?", (key,))
    conn.execute("DELETE FROM passports WHERE passport_id=?", (key,))
    conn.commit()
    conn.close()
    return summary


def purge_expired(*, days: int | None = None) -> int:
    """Delete passports nobody has used inside the retention window."""
    horizon = (datetime.now(UTC) - timedelta(days=days or retention_days())).isoformat()
    conn = _conn()
    stale = [
        str(row["passport_id"])
        for row in conn.execute(
            "SELECT passport_id FROM passports WHERE last_seen_at_utc < ?", (horizon,)
        ).fetchall()
    ]
    for passport_id in stale:
        conn.execute("DELETE FROM passport_history WHERE passport_id=?", (passport_id,))
        conn.execute("DELETE FROM passport_links WHERE passport_id=?", (passport_id,))
        conn.execute("DELETE FROM passports WHERE passport_id=?", (passport_id,))
    conn.execute(
        "DELETE FROM passport_links WHERE expires_at_utc < ?", (datetime.now(UTC).isoformat(),)
    )
    conn.commit()
    conn.close()
    return len(stale)


# ---------------------------------------------------------------------------
# Return links
# ---------------------------------------------------------------------------


def create_link(passport_id: str, *, ttl_days: int | None = None) -> str:
    """Issue a single-use return token; only its hash is stored."""
    key = (passport_id or "").strip()
    if not key:
        raise ValueError("A passport id is required.")
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    conn = _conn()
    conn.execute(
        "INSERT INTO passport_links (token_hash, passport_id, created_at_utc, expires_at_utc, used_at_utc) "
        "VALUES (?, ?, ?, ?, NULL)",
        (
            _hash_token(token),
            key,
            now.isoformat(),
            (now + timedelta(days=ttl_days or link_ttl_days())).isoformat(),
        ),
    )
    conn.commit()
    conn.close()
    return token


def consume_link(token: str) -> tuple[str, dict | None]:
    """Spend a return token.

    Returns ``(status, passport)`` where status is ``ok``, ``invalid``,
    ``used``, ``expired`` or ``gone``. The distinction matters: "already used"
    and "expired" are different instructions for the person holding the link,
    and neither means their settings are lost.
    """
    raw = (token or "").strip()
    if not raw:
        return "invalid", None

    conn = _conn()
    row = conn.execute(
        "SELECT token_hash, passport_id, expires_at_utc, used_at_utc "
        "FROM passport_links WHERE token_hash=?",
        (_hash_token(raw),),
    ).fetchone()
    if row is None:
        conn.close()
        return "invalid", None
    if row["used_at_utc"]:
        conn.close()
        return "used", None
    try:
        expires = datetime.fromisoformat(str(row["expires_at_utc"]))
    except ValueError:
        expires = datetime.now(UTC) - timedelta(seconds=1)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        conn.close()
        return "expired", None

    conn.execute(
        "UPDATE passport_links SET used_at_utc=? WHERE token_hash=?",
        (_utc_now(), str(row["token_hash"])),
    )
    conn.commit()
    conn.close()

    passport = get_passport(str(row["passport_id"]))
    if passport is None:
        return "gone", None
    return "ok", passport


# ---------------------------------------------------------------------------
# History -- opt-in, and only ever opt-in
# ---------------------------------------------------------------------------

HISTORY_LIMIT = 25


def record_history(
    passport_id: str, *, kind: str, label: str, score: int | None = None, grade: str = ""
) -> bool:
    """Record one piece of work, if and only if this passport asked for it.

    Returns True when something was stored. The check lives here rather than
    at each call site so a new caller cannot forget it.
    """
    passport = get_passport(passport_id, touch=False)
    if not passport or not passport.get("history_enabled"):
        return False

    conn = _conn()
    conn.execute(
        "INSERT INTO passport_history (passport_id, kind, label, score, grade, created_at_utc) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (passport_id, kind, label[:200], score, (grade or "")[:8], _utc_now()),
    )
    # Keep the tail short: this is "compare against your own past", not an
    # archive of everything somebody has ever opened.
    conn.execute(
        "DELETE FROM passport_history WHERE passport_id=? AND id NOT IN ("
        " SELECT id FROM passport_history WHERE passport_id=? "
        " ORDER BY id DESC LIMIT ?)",
        (passport_id, passport_id, HISTORY_LIMIT),
    )
    conn.commit()
    conn.close()
    return True


def list_history(passport_id: str, *, limit: int = HISTORY_LIMIT) -> list[dict]:
    key = (passport_id or "").strip()
    if not key:
        return []
    conn = _conn()
    rows = conn.execute(
        "SELECT id, kind, label, score, grade, created_at_utc FROM passport_history "
        "WHERE passport_id=? ORDER BY id DESC LIMIT ?",
        (key, int(limit)),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def clear_history(passport_id: str) -> int:
    key = (passport_id or "").strip()
    if not key:
        return 0
    conn = _conn()
    count = int(
        conn.execute(
            "SELECT COUNT(*) AS n FROM passport_history WHERE passport_id=?", (key,)
        ).fetchone()["n"]
    )
    conn.execute("DELETE FROM passport_history WHERE passport_id=?", (key,))
    conn.commit()
    conn.close()
    return count
