"""AHG 2026 pre-workshop survey: letitglow.app/ahg/survey.

Sent to registered participants the week before the day, so the room is set
up for the people in it: which path each person takes, what their laptop and
campus allow, what access needs to be ready at 10:00, and what problem each
person brings. Answers stay in GLOW's instance folder (``ahg_survey.db``);
nothing goes to an AI or to GitHub. The facilitator reads them at
``/ahg/survey/results?key=...`` when ``AHG_SURVEY_KEY`` is set, and nowhere
otherwise.

The questions live in ``QUESTIONS`` so the form, the validation, the results
page and the CSV all read one list.
"""

from __future__ import annotations

import csv
import hmac
import io
import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from flask import Blueprint, abort, current_app, make_response, redirect, render_template, request, url_for

from ..app import limiter

ahg_survey_bp = Blueprint("ahg_survey", __name__)

log = logging.getLogger(__name__)

#: When the answers are deleted. Said on the form and on the privacy page.
DELETE_BY = "31 January 2027"


@dataclass(frozen=True)
class Question:
    key: str
    label: str
    kind: str  # "radio", "check", "text", "line", "email", "github"
    options: tuple[str, ...] = ()
    hint: str = ""
    required: bool = False
    group: str = ""


QUESTIONS: tuple[Question, ...] = (
    # About you
    Question(
        "role",
        "Which best describes your work?",
        "radio",
        (
            "Disability resources or accessibility office",
            "Alternate formats",
            "Instructional design or teaching center",
            "Faculty",
            "IT accessibility",
            "Leadership",
            "Other",
        ),
        required=True,
        group="About you",
    ),
    Question(
        "institution",
        "What kind of institution?",
        "radio",
        (
            "Public university",
            "Private college or university",
            "Community college",
            "System office or state agency",
            "Other",
        ),
        group="About you",
    ),
    Question(
        "card",
        "Which role card are you most interested in?",
        "radio",
        (
            "Documents and alternate formats",
            "Course content and faculty coaching",
            "Compliance and procurement",
            "Not sure yet",
        ),
        hint="You choose one on the day. This helps us seat helpers.",
        group="About you",
    ),
    # Your setup
    Question(
        "path",
        "Which path do you plan to take?",
        "radio",
        (
            "The browser path, with an AI assistant",
            "VS Code on my computer",
            "VS Code for the Web, at vscode.dev",
            "Not sure",
        ),
        hint="letitglow.app/ahg/paths compares them.",
        required=True,
        group="Your setup",
    ),
    Question(
        "assistants",
        "Which AI assistants can you use at work?",
        "check",
        (
            "ChatGPT",
            "Microsoft Copilot",
            "GitHub Copilot",
            "Claude",
            "Gemini",
            "An assistant built by my campus",
            "None are allowed",
            "Not sure",
        ),
        group="Your setup",
    ),
    Question(
        "laptop",
        "Can you install software on the laptop you will bring?",
        "radio",
        (
            "Yes",
            "No, it is locked down",
            "Not sure",
        ),
        group="Your setup",
    ),
    Question(
        "experience",
        "Which of these have you used before?",
        "check",
        (
            "VS Code",
            "GitHub",
            "An AI assistant, for work",
            "An AI assistant's custom instructions, projects or GPTs",
            "None of these",
        ),
        group="Your setup",
    ),
    Question(
        "ready",
        "Have you done the setup and the ready check?",
        "radio",
        (
            "Yes, it said I am ready",
            "I started, and got stuck",
            "Not yet",
        ),
        group="Your setup",
    ),
    # Access
    Question(
        "tools",
        "Which of these will you use during the day?",
        "check",
        (
            "A screen reader",
            "Screen magnification",
            "Voice control",
            "A braille display",
            "Keyboard only",
            "Large print materials",
            "None of these",
        ),
        hint="So the right helpers and materials are ready at 10:00. Optional.",
        group="Access",
    ),
    Question(
        "access_notes",
        "Anything we should have ready for you?",
        "text",
        hint="A seat, a format, a pause, which screen reader. No medical details needed.",
        group="Access",
    ),
    # Your goals
    Question(
        "content",
        "What makes up most of your backlog?",
        "check",
        (
            "Word documents",
            "PDFs",
            "Scanned readings",
            "PowerPoint slides",
            "Excel workbooks",
            "Web and LMS pages",
            "Video and captions",
        ),
        group="Your goals",
    ),
    Question(
        "problem",
        "One real problem you would like your agent to help with",
        "text",
        hint="Nothing private: no student names, records or accommodation details.",
        group="Your goals",
    ),
    Question("success", "What would make the day worth it for you?", "text", group="Your goals"),
    Question(
        "contact",
        "Would you like a helper to contact you before the day?",
        "radio",
        (
            "Yes, please",
            "No, thank you",
        ),
        hint="We will use the email address you gave above.",
        group="Your goals",
    ),
)

#: Who is answering. Asked first, so the setup help and the share on the day
#: can be matched to the person. The GitHub account is optional here because
#: some people make it after reading the survey; the links say how.
DETAILS: tuple[Question, ...] = (
    Question("name", "Your name", "line", required=True, group="Your details"),
    Question(
        "email",
        "Your email address",
        "email",
        hint="The one you registered for AHG with. Used only to help you get ready for the day.",
        required=True,
        group="Your details",
    ),
    Question(
        "github",
        "Your GitHub username",
        "github",
        hint="You share your agent on GitHub in block 6. No account yet? It is free and takes a few minutes; leave this empty and come back.",
        group="Your details",
    ),
)

#: Help links shown under a question, as (text, address) pairs.
LINKS: dict[str, tuple[tuple[str, str], ...]] = {
    "github": (
        ("Make a free GitHub account", "https://github.com/signup"),
        (
            "GitHub's guide to creating an account",
            "https://docs.github.com/en/get-started/start-your-journey/creating-an-account-on-github",
        ),
        ("Choosing a path, with every setup step", "/ahg/paths"),
    ),
}

QUESTIONS = DETAILS + QUESTIONS

#: A GitHub username: letters, digits and single hyphens, 39 characters at
#: most, never starting or ending with a hyphen.
GITHUB_NAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")

GROUPS: tuple[str, ...] = tuple(dict.fromkeys(q.group for q in QUESTIONS))
MAX_TEXT = 2000


def _db() -> sqlite3.Connection:
    folder = Path(current_app.instance_path)
    folder.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(folder / "ahg_survey.db"))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS responses ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  submitted TEXT NOT NULL,"
        "  answers_json TEXT NOT NULL"
        ")"
    )
    return conn


def _answers_from_form() -> dict[str, object]:
    answers: dict[str, object] = {}
    for q in QUESTIONS:
        if q.kind == "check":
            picked = [v for v in request.form.getlist(q.key) if v in q.options]
            answers[q.key] = picked
        elif q.kind == "radio":
            value = request.form.get(q.key, "")
            answers[q.key] = value if value in q.options else ""
        elif q.kind == "github":
            answers[q.key] = request.form.get(q.key, "").strip().removeprefix("@")[:100]
        else:
            answers[q.key] = request.form.get(q.key, "").strip()[:MAX_TEXT]
    return answers


def _errors(answers: dict[str, object]) -> list[tuple[str, str]]:
    errors = []
    for q in QUESTIONS:
        if q.required and not answers.get(q.key):
            errors.append((q.key, f'Answer "{q.label}"'))
    email = str(answers.get("email", ""))
    if email and ("@" not in email or " " in email or len(email) > 254):
        errors.append(("email", "Check your email address: it needs an @ and no spaces"))
    github = str(answers.get("github", "")).removeprefix("@")
    if github and not GITHUB_NAME.match(github):
        errors.append(
            ("github", "Check your GitHub username: letters, numbers and single hyphens only, or leave it empty")
        )
    return errors


@ahg_survey_bp.route("/ahg/survey", methods=["GET"], strict_slashes=False)
def survey_form():
    return render_template(
        "workshop/ahg_survey.html",
        questions=QUESTIONS,
        groups=GROUPS,
        links=LINKS,
        answers={},
        errors=[],
        delete_by=DELETE_BY,
    )


@ahg_survey_bp.route("/ahg/survey", methods=["POST"], strict_slashes=False)
@limiter.limit("10 per hour", error_message="Too many answers from one place. Please try again later.")
def survey_submit():
    answers = _answers_from_form()
    errors = _errors(answers)
    if errors:
        return render_template(
            "workshop/ahg_survey.html",
            questions=QUESTIONS,
            groups=GROUPS,
            links=LINKS,
            answers=answers,
            errors=errors,
            delete_by=DELETE_BY,
        ), 400
    try:
        conn = _db()
        conn.execute(
            "INSERT INTO responses (submitted, answers_json) VALUES (?, ?)",
            (datetime.now(UTC).isoformat(timespec="seconds"), json.dumps(answers)),
        )
        conn.commit()
        conn.close()
    except (sqlite3.Error, OSError):
        log.exception("AHG survey: could not save an answer")
        abort(500)
    return redirect(url_for("ahg_survey.survey_thanks"), code=303)


@ahg_survey_bp.route("/ahg/survey/thanks", methods=["GET"])
def survey_thanks():
    return render_template("workshop/ahg_survey_thanks.html")


def _check_key() -> None:
    expected = os.environ.get("AHG_SURVEY_KEY", "")
    if not expected:
        abort(404)
    provided = request.args.get("key", "")
    if not provided or not hmac.compare_digest(provided, expected):
        abort(403)


def _load() -> list[dict[str, object]]:
    conn = _db()
    rows = conn.execute("SELECT id, submitted, answers_json FROM responses ORDER BY id").fetchall()
    conn.close()
    return [{"id": r[0], "submitted": r[1], **json.loads(r[2])} for r in rows]


@ahg_survey_bp.route("/ahg/survey/results", methods=["GET"])
def survey_results():
    _check_key()
    rows = _load()
    tallies = {}
    for q in QUESTIONS:
        if q.kind in ("radio", "check"):
            counts = {o: 0 for o in q.options}
            for row in rows:
                value = row.get(q.key)
                for v in value if isinstance(value, list) else [value]:
                    if v in counts:
                        counts[v] += 1
            tallies[q.key] = counts
    resp = make_response(
        render_template(
            "workshop/ahg_survey_results.html",
            questions=QUESTIONS,
            rows=rows,
            tallies=tallies,
            key=request.args.get("key", ""),
        )
    )
    resp.headers["Cache-Control"] = "no-store"
    return resp


@ahg_survey_bp.route("/ahg/survey/results.csv", methods=["GET"])
def survey_results_csv():
    _check_key()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "submitted", *[q.key for q in QUESTIONS]])
    for row in _load():
        writer.writerow(
            [
                row["id"],
                row["submitted"],
                *["; ".join(v) if isinstance(v, list) else v for v in (row.get(q.key, "") for q in QUESTIONS)],
            ]
        )
    resp = make_response(out.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = "attachment; filename=ahg-2026-survey.csv"
    resp.headers["Cache-Control"] = "no-store"
    return resp
