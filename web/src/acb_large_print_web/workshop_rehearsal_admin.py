"""Safely provision and remove disposable workshop load rehearsal sessions.

This command is intended to run inside the deployed web container. It refuses
session codes outside the generated ``ahg-load-test-<run>-<attempt>`` format,
and removes only records belonging to a session with the matching run title.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys

from .app import create_app
from . import workshop_store


_CODE_RE = re.compile(r"^ahg-load-test-(\d+)-(\d+)$")
_ANCILLARY_TABLES = (
    "workshop_conference_codes",
    "workshop_nudges",
    "workshop_return_links",
    "workshop_feedback",
    "workshop_follow_through",
)


def _validate_identity(code: str, run_id: str, attempt: str) -> str:
    if not run_id.isdigit() or not attempt.isdigit():
        raise ValueError("run-id and attempt must contain digits only")
    expected = f"ahg-load-test-{run_id}-{attempt}"
    if code != expected or not _CODE_RE.fullmatch(code):
        raise ValueError("code must exactly match ahg-load-test-<run-id>-<attempt>")
    return f"Automated load rehearsal run {run_id}-{attempt}"


def _counts(conn: sqlite3.Connection, code: str) -> dict[str, int]:
    tables = (*_ANCILLARY_TABLES, "workshop_submissions", "workshop_participants", "workshop_sessions")
    return {
        table: int(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE session_code=?", (code,)).fetchone()[0])
        for table in tables
    }


def provision(code: str, run_id: str, attempt: str) -> dict[str, object]:
    title = _validate_identity(code, run_id, attempt)
    conn = workshop_store._conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM workshop_sessions WHERE session_code=?", (code,)).fetchone():
            raise ValueError("refusing to reuse an existing session code")
        if conn.execute("SELECT 1 FROM workshop_conference_codes WHERE session_code=?", (code,)).fetchone():
            raise ValueError("refusing to use a code mapped to a conference access code")
        conn.execute(
            "INSERT INTO workshop_sessions (session_code, title, event_name, created_at_utc) VALUES (?, ?, ?, ?)",
            (code, title, "Automated disposable load rehearsal", workshop_store._utc_now()),
        )
        conn.commit()
        return {"action": "provisioned", "code": code, "title": title}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cleanup(code: str, run_id: str, attempt: str) -> dict[str, object]:
    title = _validate_identity(code, run_id, attempt)
    conn = workshop_store._conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        session = conn.execute(
            "SELECT title FROM workshop_sessions WHERE session_code=?", (code,)
        ).fetchone()
        if session is None:
            conn.commit()
            return {"action": "already-absent", "code": code}
        if str(session["title"]) != title:
            raise ValueError("session title does not match this workflow run; refusing deletion")

        before = _counts(conn, code)
        unexpected = {table: count for table, count in before.items() if table in _ANCILLARY_TABLES and count}
        if unexpected:
            raise ValueError(f"unexpected related records; operator review required: {unexpected}")

        deleted = {
            "workshop_submissions": conn.execute(
                "DELETE FROM workshop_submissions WHERE session_code=?", (code,)
            ).rowcount,
            "workshop_participants": conn.execute(
                "DELETE FROM workshop_participants WHERE session_code=?", (code,)
            ).rowcount,
            "workshop_sessions": conn.execute(
                "DELETE FROM workshop_sessions WHERE session_code=?", (code,)
            ).rowcount,
        }
        after = _counts(conn, code)
        if any(after.values()):
            raise RuntimeError(f"cleanup verification failed; remaining row counts: {after}")
        conn.commit()
        return {"action": "cleaned", "code": code, "deleted": deleted, "remaining": after}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("provision", "cleanup"))
    parser.add_argument("--code", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args(argv)

    try:
        app = create_app()
        with app.app_context():
            result = provision(args.code, args.run_id, args.attempt) if args.action == "provision" else cleanup(
                args.code, args.run_id, args.attempt
            )
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:  # CLI boundary: show a concise operator-facing error.
        print(f"workshop rehearsal {args.action} failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
