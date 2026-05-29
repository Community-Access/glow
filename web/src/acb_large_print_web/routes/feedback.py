"""Feedback routes - human form plus generic support-hub API intake."""

from __future__ import annotations

import hmac
import json
import logging
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from flask import Blueprint, abort, current_app, jsonify, render_template, request

from ..app import csrf, limiter
from ..support_hub import create_support_issue, load_support_hub_config
from ..version import get_version

feedback_bp = Blueprint("feedback", __name__)

log = logging.getLogger(__name__)


def _get_db_path() -> Path:
    """Return the path to the feedback SQLite database."""
    instance_path = Path(current_app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    return instance_path / "feedback.db"


def _get_db() -> sqlite3.Connection:
    """Open (and auto-create) the feedback database."""
    db_path = _get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")  # safe for concurrent reads
    conn.execute(
        "CREATE TABLE IF NOT EXISTS feedback ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  timestamp TEXT NOT NULL,"
        "  name TEXT,"
        "  email TEXT,"
        "  source_app TEXT,"
        "  source_channel TEXT,"
        "  source_version TEXT,"
        "  platform TEXT,"
        "  category TEXT,"
        "  rating TEXT NOT NULL,"
        "  task TEXT,"
        "  summary TEXT,"
        "  message TEXT NOT NULL,"
        "  metadata_json TEXT,"
        "  github_issue_number INTEGER,"
        "  github_issue_url TEXT,"
        "  github_sync_status TEXT,"
        "  github_sync_error TEXT,"
        "  github_synced_at TEXT"
        ")"
    )
    _ensure_feedback_schema(conn)
    conn.commit()
    return conn


def _ensure_feedback_schema(conn: sqlite3.Connection) -> None:
    """Add missing columns for GitHub sync and contributor info when upgrading older databases."""
    existing = {
        row[1]
        for row in conn.execute("PRAGMA table_info(feedback)").fetchall()
    }
    required = {
        "name": "TEXT",
        "email": "TEXT",
        "source_app": "TEXT",
        "source_channel": "TEXT",
        "source_version": "TEXT",
        "platform": "TEXT",
        "category": "TEXT",
        "summary": "TEXT",
        "metadata_json": "TEXT",
        "github_issue_number": "INTEGER",
        "github_issue_url": "TEXT",
        "github_sync_status": "TEXT",
        "github_sync_error": "TEXT",
        "github_synced_at": "TEXT",
    }
    for col, col_type in required.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE feedback ADD COLUMN {col} {col_type}")


def _save_feedback_entry(entry: dict[str, str]) -> tuple[int, str | None, str | None, str | None]:
    conn = _get_db()
    cur = conn.execute(
        "INSERT INTO feedback ("
        "timestamp, name, email, source_app, source_channel, source_version, platform, "
        "category, rating, task, summary, message, metadata_json"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            entry["timestamp"],
            entry["name"],
            entry["email"],
            entry["source_app"],
            entry["source_channel"],
            entry["source_version"],
            entry["platform"],
            entry["category"],
            entry["rating"],
            entry["task"],
            entry["summary"],
            entry["message"],
            entry["metadata_json"],
        ),
    )
    feedback_id = int(cur.lastrowid)
    stored_entry = dict(entry)
    stored_entry["id"] = feedback_id
    issue_number, issue_url, sync_error = create_support_issue(stored_entry)
    if issue_number and issue_url:
        conn.execute(
            "UPDATE feedback SET github_issue_number=?, github_issue_url=?, github_sync_status=?, github_sync_error=?, github_synced_at=? WHERE id=?",
            (
                issue_number,
                issue_url,
                "synced",
                None,
                datetime.now(UTC).isoformat(),
                feedback_id,
            ),
        )
    else:
        conn.execute(
            "UPDATE feedback SET github_sync_status=?, github_sync_error=? WHERE id=?",
            ("failed", sync_error, feedback_id),
        )
        if sync_error:
            log.warning("Support-hub GitHub sync failed for id=%s: %s", feedback_id, sync_error)
    conn.commit()
    conn.close()
    return feedback_id, issue_url, sync_error, stored_entry["source_app"]


def _feedback_defaults() -> dict[str, str]:
    return {
        "name": "",
        "email": "",
        "summary": "",
        "rating": "",
        "task": "",
        "message": "",
        "source_app": "GLOW",
        "source_channel": "web",
        "source_version": get_version(),
        "platform": "browser",
        "category": "feedback",
        "metadata_json": "",
    }


def _render_feedback_form(error: str = "", **values: str):
    merged = _feedback_defaults()
    merged.update(values)
    merged["error"] = error
    merged["support_repo"] = load_support_hub_config().repo
    return render_template("feedback_form.html", **merged)


def _validate_feedback_entry(entry: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if not entry["message"]:
        errors.append("Please enter your feedback.")
    if len(entry["message"]) > 5000:
        errors.append("Feedback is limited to 5,000 characters.")
    if entry["rating"] and entry["rating"] not in ("excellent", "good", "fair", "poor"):
        errors.append("Invalid rating value.")
    if entry["email"] and "@" not in entry["email"]:
        errors.append("Please provide a valid email address.")
    if len(entry["summary"]) > 240:
        errors.append("Short summary is limited to 240 characters.")
    if not entry["source_app"]:
        errors.append("Source application is required.")
    return errors


def _entry_from_form() -> dict[str, str]:
    entry = _feedback_defaults()
    entry.update(
        {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "summary": request.form.get("summary", "").strip(),
            "rating": request.form.get("rating", "").strip(),
            "task": request.form.get("task", "").strip(),
            "message": request.form.get("message", "").strip(),
            "source_app": request.form.get("source_app", "GLOW").strip() or "GLOW",
            "source_channel": request.form.get("source_channel", "web").strip() or "web",
            "source_version": request.form.get("source_version", get_version()).strip() or get_version(),
            "platform": request.form.get("platform", "browser").strip() or "browser",
            "category": request.form.get("category", "feedback").strip() or "feedback",
            "metadata_json": request.form.get("metadata_json", "").strip(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    )
    return entry


def _entry_from_json(payload: dict[str, object]) -> dict[str, str]:
    metadata = payload.get("metadata")
    metadata_json = ""
    if isinstance(metadata, dict):
        metadata_json = json.dumps(metadata, indent=2, sort_keys=True)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "name": str(payload.get("name", "") or "").strip(),
        "email": str(payload.get("email", "") or "").strip(),
        "summary": str(payload.get("summary", "") or "").strip(),
        "rating": str(payload.get("rating", "") or "").strip(),
        "task": str(payload.get("task", "") or "").strip(),
        "message": str(payload.get("message", "") or "").strip(),
        "source_app": str(payload.get("source_app", "") or "").strip(),
        "source_channel": str(payload.get("source_channel", "api") or "api").strip(),
        "source_version": str(payload.get("source_version", "") or "").strip(),
        "platform": str(payload.get("platform", "") or "").strip(),
        "category": str(payload.get("category", "feedback") or "feedback").strip(),
        "metadata_json": metadata_json,
    }
    return entry


@feedback_bp.route("/", methods=["GET"])
def feedback_form():
    return _render_feedback_form()


@feedback_bp.route("/", methods=["POST"])
@limiter.limit("10 per hour", error_message="Too many feedback submissions. Please try again later.")
def feedback_submit():
    entry = _entry_from_form()
    if not entry["rating"]:
        return _render_feedback_form("Please select a rating.", **entry), 400
    errors = _validate_feedback_entry(entry)
    if errors:
        return _render_feedback_form(" ".join(errors), **entry), 400

    issue_url = None
    try:
        _feedback_id, issue_url, _sync_error, source_app = _save_feedback_entry(entry)
    except (sqlite3.Error, OSError):
        log.exception("Failed to save feedback")
        source_app = entry["source_app"]

    return render_template(
        "feedback_thanks.html",
        issue_url=issue_url,
        source_app=source_app,
        support_repo=load_support_hub_config().repo,
    )


@feedback_bp.route("/api", methods=["POST"])
@csrf.exempt
@limiter.limit("30 per hour", error_message="Too many API feedback submissions. Please try again later.")
def feedback_submit_api():
    cfg = load_support_hub_config()
    if not cfg.api_token:
        abort(404)
    authorization = request.headers.get("Authorization", "")
    expected = f"Bearer {cfg.api_token}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        return jsonify({"error": "Unauthorized"}), 403
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object required"}), 400
    entry = _entry_from_json(payload)
    errors = _validate_feedback_entry(entry)
    if errors:
        return jsonify({"error": " ".join(errors)}), 400
    try:
        feedback_id, issue_url, sync_error, source_app = _save_feedback_entry(entry)
    except (sqlite3.Error, OSError):
        log.exception("Failed to save API feedback")
        return jsonify({"error": "Feedback could not be stored"}), 500
    return jsonify(
        {
            "status": "accepted",
            "id": feedback_id,
            "source_app": source_app,
            "support_repo": cfg.repo,
            "issue_url": issue_url,
            "github_sync_status": "synced" if issue_url else "failed",
            "github_sync_error": sync_error,
        }
    ), 202


@feedback_bp.route("/review")
def feedback_review():
    """Display all feedback entries. Protected by FEEDBACK_PASSWORD env var."""
    expected = os.environ.get("FEEDBACK_PASSWORD", "")
    if not expected:
        abort(404)  # review disabled when no password is configured

    provided = request.args.get("key", "")
    if not provided or not hmac.compare_digest(provided, expected):
        abort(403)

    try:
        conn = _get_db()
        cursor = conn.execute(
            "SELECT id, timestamp, name, email, source_app, source_channel, source_version, platform, category, rating, task, summary, message, metadata_json, github_issue_number, github_issue_url, github_sync_status, github_sync_error "
            "FROM feedback ORDER BY id DESC"
        )
        rows = [
            {
                "id": r[0],
                "timestamp": r[1],
                "name": r[2],
                "email": r[3],
                "source_app": r[4],
                "source_channel": r[5],
                "source_version": r[6],
                "platform": r[7],
                "category": r[8],
                "rating": r[9],
                "task": r[10],
                "summary": r[11],
                "message": r[12],
                "metadata_json": r[13],
                "github_issue_number": r[14],
                "github_issue_url": r[15],
                "github_sync_status": r[16],
                "github_sync_error": r[17],
            }
            for r in cursor.fetchall()
        ]
        conn.close()
    except (sqlite3.Error, OSError):
        log.exception("Failed to load feedback")
        rows = []

    response = render_template("feedback_review.html", entries=rows)
    resp = current_app.make_response(response)
    resp.headers["Cache-Control"] = "no-store"
    return resp
