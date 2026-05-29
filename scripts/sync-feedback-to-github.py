#!/usr/bin/env python3
"""Backfill/sync feedback entries into the Community Access support hub.

This script reads rows from instance/feedback.db and creates issues in a target
GitHub repository for entries that are not already synced.

Usage examples:
  python scripts/sync-feedback-to-github.py
  python scripts/sync-feedback-to-github.py --db s:/code/glow/instance/feedback.db --repo Community-Access/support

Environment variables:
  SUPPORT_HUB_GITHUB_TOKEN    Required unless --token is supplied
  SUPPORT_HUB_GITHUB_REPO     Default repository (default: Community-Access/support)
  SUPPORT_HUB_GITHUB_ASSIGNEE Default assignee (default: none)
  SUPPORT_HUB_GITHUB_LABELS   Comma-separated labels (default: needs-triage)

Legacy FEEDBACK_GITHUB_* variables are still honored for compatibility.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from acb_large_print_web.support_hub import create_support_issue, load_support_hub_config


def ensure_schema(conn: sqlite3.Connection) -> None:
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
    cols = {row[1] for row in conn.execute("PRAGMA table_info(feedback)").fetchall()}
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
    for column, column_type in required.items():
        if column not in cols:
            conn.execute(f"ALTER TABLE feedback ADD COLUMN {column} {column_type}")
    conn.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync feedback.db rows into Community Access support issues"
    )
    parser.add_argument("--db", default="s:/code/glow/instance/feedback.db", help="Path to feedback.db")
    parser.add_argument("--repo", default="", help="Target owner/repo")
    parser.add_argument("--assignee", default="", help="GitHub assignee username")
    parser.add_argument("--labels", default="", help="Comma-separated labels")
    parser.add_argument("--token", default="", help="GitHub token override")
    parser.add_argument("--limit", type=int, default=0, help="Max rows to sync (0 = all)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_support_hub_config()
    token = args.token.strip() or cfg.token
    if not token:
        print("ERROR: GitHub token missing. Set SUPPORT_HUB_GITHUB_TOKEN or use --token")
        return 2

    repo = args.repo.strip() or cfg.repo
    assignee = args.assignee.strip() or cfg.assignee
    labels_raw = args.labels.strip() or ",".join(cfg.labels)
    labels = [item.strip() for item in labels_raw.split(",") if item.strip()]

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)

    limit_clause = ""
    params: tuple[object, ...] = ()
    if args.limit and args.limit > 0:
        limit_clause = " LIMIT ?"
        params = (args.limit,)

    rows = conn.execute(
        "SELECT id, timestamp, name, email, source_app, source_channel, source_version, platform, "
        "category, rating, task, summary, message, metadata_json, github_issue_number "
        "FROM feedback WHERE github_issue_number IS NULL ORDER BY id ASC" + limit_clause,
        params,
    ).fetchall()

    if not rows:
        print("No unsynced feedback rows found.")
        conn.close()
        return 0

    print(f"Found {len(rows)} unsynced feedback rows.")
    ok = 0
    failed = 0
    previous = {
        key: os.environ.get(key)
        for key in (
            "SUPPORT_HUB_GITHUB_TOKEN",
            "SUPPORT_HUB_GITHUB_REPO",
            "SUPPORT_HUB_GITHUB_ASSIGNEE",
            "SUPPORT_HUB_GITHUB_LABELS",
        )
    }
    os.environ["SUPPORT_HUB_GITHUB_TOKEN"] = token
    os.environ["SUPPORT_HUB_GITHUB_REPO"] = repo
    os.environ["SUPPORT_HUB_GITHUB_ASSIGNEE"] = assignee
    os.environ["SUPPORT_HUB_GITHUB_LABELS"] = ",".join(labels)
    try:
        for row in rows:
            entry = {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "name": row["name"] or "",
                "email": row["email"] or "",
                "source_app": row["source_app"] or "GLOW",
                "source_channel": row["source_channel"] or "web",
                "source_version": row["source_version"] or "",
                "platform": row["platform"] or "",
                "category": row["category"] or "feedback",
                "rating": row["rating"] or "",
                "task": row["task"] or "",
                "summary": row["summary"] or "",
                "message": row["message"] or "",
                "metadata_json": row["metadata_json"] or "",
            }
            issue_number, issue_url, error = create_support_issue(entry)
            if issue_number and issue_url:
                ok += 1
                conn.execute(
                    "UPDATE feedback SET github_issue_number=?, github_issue_url=?, github_sync_status=?, github_sync_error=?, github_synced_at=? WHERE id=?",
                    (
                        issue_number,
                        issue_url,
                        "synced",
                        None,
                        datetime.now(UTC).isoformat(),
                        row["id"],
                    ),
                )
                print(f"synced id={row['id']} -> issue #{issue_number} in {repo}")
            else:
                failed += 1
                conn.execute(
                    "UPDATE feedback SET github_sync_status=?, github_sync_error=? WHERE id=?",
                    ("failed", error, row["id"]),
                )
                print(f"failed id={row['id']}: {error}")
            conn.commit()
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    conn.close()
    print(f"Done. synced={ok}, failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
