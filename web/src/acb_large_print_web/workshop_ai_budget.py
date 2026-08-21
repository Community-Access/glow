"""Per-participant AI budgets for a room running on one house key.

Thirty people running AI-assisted labs against a single provider key, in one
seven-hour window, is a load and spend profile GLOW has never seen. The
failure this prevents is specific: one enthusiastic participant in a retry
loop at 2 PM taking the room's AI down for everyone else.

Two caps, both deliberately generous:

* per participant, so no single person can spend the room's budget
* per session, so the room as a whole has a known ceiling

What happens at the cap matters as much as the cap itself. Exhaustion routes
to the Tier 2 path -- the prompt the participant can paste into whatever
assistant they already have -- so it reads as a doorway rather than a wall.
Nothing about the day depends on the house key being available.

Only actions are counted, never page views: a participant reading a page they
already loaded has not spent anything.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import current_app

# Blueprints whose POSTs actually call a model.
AI_BLUEPRINTS = frozenset({"ai", "chat", "alt_text", "magic", "playground", "speech"})

DEFAULT_PARTICIPANT_CAP = 40
DEFAULT_SESSION_CAP = 600


def _db_path() -> Path:
    p = Path(current_app.instance_path)
    p.mkdir(parents=True, exist_ok=True)
    return p / "workshop_mode.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS workshop_ai_usage ("
        " session_code TEXT NOT NULL,"
        " participant_key TEXT NOT NULL,"
        " calls INTEGER NOT NULL DEFAULT 0,"
        " updated_at_utc TEXT NOT NULL,"
        " PRIMARY KEY (session_code, participant_key)"
        ")"
    )
    return conn


def _cap(name: str, default: int) -> int:
    """A cap of zero disables that limit; a negative or unparsable value is
    treated as unset, because a typo in an environment variable must not
    silently switch the room's AI off."""
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def participant_cap() -> int:
    return _cap("GLOW_WORKSHOP_AI_PARTICIPANT_CAP", DEFAULT_PARTICIPANT_CAP)


def session_cap() -> int:
    return _cap("GLOW_WORKSHOP_AI_SESSION_CAP", DEFAULT_SESSION_CAP)


def record_call(session_code: str, participant_key: str, *, now: str) -> int:
    """Count one AI action and return the participant's new total."""
    conn = _conn()
    conn.execute(
        "INSERT INTO workshop_ai_usage (session_code, participant_key, calls, updated_at_utc) "
        "VALUES (?, ?, 1, ?) "
        "ON CONFLICT(session_code, participant_key) DO UPDATE SET "
        "calls = calls + 1, updated_at_utc = excluded.updated_at_utc",
        (session_code, participant_key, now),
    )
    conn.commit()
    row = conn.execute(
        "SELECT calls FROM workshop_ai_usage WHERE session_code=? AND participant_key=?",
        (session_code, participant_key),
    ).fetchone()
    conn.close()
    return int(row["calls"]) if row else 1


def participant_calls(session_code: str, participant_key: str) -> int:
    conn = _conn()
    row = conn.execute(
        "SELECT calls FROM workshop_ai_usage WHERE session_code=? AND participant_key=?",
        (session_code, participant_key),
    ).fetchone()
    conn.close()
    return int(row["calls"]) if row else 0


def session_calls(session_code: str) -> int:
    conn = _conn()
    row = conn.execute(
        "SELECT COALESCE(SUM(calls), 0) AS total FROM workshop_ai_usage WHERE session_code=?",
        (session_code,),
    ).fetchone()
    conn.close()
    return int(row["total"]) if row else 0


def session_usage(session_code: str) -> dict:
    """What a facilitator needs to see before 2 PM rather than after it."""
    conn = _conn()
    rows = conn.execute(
        "SELECT participant_key, calls FROM workshop_ai_usage WHERE session_code=? "
        "ORDER BY calls DESC",
        (session_code,),
    ).fetchall()
    conn.close()

    totals = [int(row["calls"]) for row in rows]
    per_cap = participant_cap()
    return {
        "participants": len(totals),
        "total_calls": sum(totals),
        "busiest": totals[0] if totals else 0,
        "at_cap": sum(1 for value in totals if per_cap and value >= per_cap),
        "participant_cap": per_cap,
        "session_cap": session_cap(),
    }


def over_budget(session_code: str, participant_key: str) -> str:
    """Return ``""``, ``"participant"`` or ``"session"``.

    Checked before the call is made, so the last permitted call still
    completes rather than being cut off half way.
    """
    per_cap = participant_cap()
    if per_cap and participant_calls(session_code, participant_key) >= per_cap:
        return "participant"
    room_cap = session_cap()
    if room_cap and session_calls(session_code) >= room_cap:
        return "session"
    return ""
