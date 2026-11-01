"""AHG 2026 room check-in: letitglow.app/ahg/check-in.

Asked once on the day, after block 3, so helpers go where they are needed
instead of waiting for hands. Two questions and an optional seat, no name:
someone who is behind says so more readily when nobody can tell who said it.
Answers stay in GLOW's instance folder (``ahg_survey.db``, beside the
survey); nothing goes to an AI or to GitHub. The facilitator and helpers read
them at ``/ahg/check-in/results?key=...`` with the survey's key, and the
answers are deleted with the survey's.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime

from flask import Blueprint, abort, make_response, redirect, render_template, request, url_for

from ..app import limiter
from .ahg_survey import DELETE_BY, Question, _check_key, _db

ahg_checkin_bp = Blueprint("ahg_checkin", __name__)

log = logging.getLogger(__name__)

#: The answer a helper acts on. Listed first on the results page.
NEEDS_HELP = "Stuck: please send a helper"

CHECKIN: tuple[Question, ...] = (
    Question(
        "how",
        "How is it going?",
        "radio",
        ("On track", "A bit behind, but fine", NEEDS_HELP),
        required=True,
    ),
    Question(
        "path",
        "Which path are you on?",
        "radio",
        ("A browser, with an AI assistant", "VS Code on my computer", "VS Code at vscode.dev"),
        required=True,
    ),
    Question(
        "seat",
        "Where are you sitting?",
        "line",
        hint="Optional. A table number or a landmark, so a helper can find you. No name needed.",
    ),
)

MAX_SEAT = 80


def _table(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS checkins ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  submitted TEXT NOT NULL,"
        "  how TEXT NOT NULL,"
        "  path TEXT NOT NULL,"
        "  seat TEXT NOT NULL"
        ")"
    )
    return conn


def _render_form(answers: dict[str, str], errors: list[tuple[str, str]]):
    return render_template(
        "workshop/ahg_checkin.html",
        questions=CHECKIN,
        answers=answers,
        errors=errors,
        delete_by=DELETE_BY,
    )


@ahg_checkin_bp.route("/ahg/check-in", methods=["GET"], strict_slashes=False)
def checkin_form():
    return _render_form({}, [])


@ahg_checkin_bp.route("/ahg/check-in", methods=["POST"], strict_slashes=False)
@limiter.limit("20 per hour", error_message="Too many check-ins from one place. Raise a hand instead.")
def checkin_submit():
    answers: dict[str, str] = {}
    errors: list[tuple[str, str]] = []
    for q in CHECKIN:
        value = request.form.get(q.key, "").strip()
        if q.kind == "radio":
            value = value if value in q.options else ""
        else:
            value = value[:MAX_SEAT]
        answers[q.key] = value
        if q.required and not value:
            errors.append((q.key, f'Answer "{q.label}"'))
    if errors:
        return _render_form(answers, errors), 400
    try:
        conn = _table(_db())
        conn.execute(
            "INSERT INTO checkins (submitted, how, path, seat) VALUES (?, ?, ?, ?)",
            (datetime.now(UTC).isoformat(timespec="seconds"), answers["how"], answers["path"], answers["seat"]),
        )
        conn.commit()
        conn.close()
    except (sqlite3.Error, OSError):
        log.exception("AHG check-in: could not save an answer")
        abort(500)
    return redirect(url_for("ahg_checkin.checkin_thanks", help="1" if answers["how"] == NEEDS_HELP else None), code=303)


@ahg_checkin_bp.route("/ahg/check-in/thanks", methods=["GET"])
def checkin_thanks():
    return render_template("workshop/ahg_checkin_thanks.html", asked_for_help=request.args.get("help") == "1")


@ahg_checkin_bp.route("/ahg/check-in/results", methods=["GET"])
def checkin_results():
    _check_key()
    conn = _table(_db())
    rows = [
        {"id": r[0], "submitted": r[1], "how": r[2], "path": r[3], "seat": r[4]}
        for r in conn.execute("SELECT id, submitted, how, path, seat FROM checkins ORDER BY id DESC")
    ]
    conn.close()
    tallies = {
        q.key: {option: sum(1 for row in rows if row[q.key] == option) for option in q.options}
        for q in CHECKIN
        if q.kind == "radio"
    }
    resp = make_response(
        render_template(
            "workshop/ahg_checkin_results.html",
            questions=CHECKIN,
            help_rows=[row for row in rows if row["how"] == NEEDS_HELP],
            total=len(rows),
            tallies=tallies,
            key=request.args.get("key", ""),
        )
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp
