from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import error as urlerror
from urllib import request as urlrequest


@dataclass(frozen=True, slots=True)
class SupportHubConfig:
    token: str
    repo: str
    assignee: str
    labels: list[str]
    api_token: str


def load_support_hub_config() -> SupportHubConfig:
    token = (
        os.environ.get("SUPPORT_HUB_GITHUB_TOKEN", "").strip()
        or os.environ.get("FEEDBACK_GITHUB_TOKEN", "").strip()
    )
    repo = (
        os.environ.get("SUPPORT_HUB_GITHUB_REPO", "").strip()
        or os.environ.get("FEEDBACK_GITHUB_REPO", "").strip()
        or "Community-Access/support"
    )
    assignee = (
        os.environ.get("SUPPORT_HUB_GITHUB_ASSIGNEE", "").strip()
        or os.environ.get("FEEDBACK_GITHUB_ASSIGNEE", "").strip()
    )
    labels_raw = (
        os.environ.get("SUPPORT_HUB_GITHUB_LABELS", "").strip()
        or os.environ.get("FEEDBACK_GITHUB_LABELS", "").strip()
        or "needs-triage"
    )
    labels = [item.strip() for item in labels_raw.split(",") if item.strip()]
    api_token = (
        os.environ.get("SUPPORT_HUB_API_TOKEN", "").strip()
        or os.environ.get("FEEDBACK_API_TOKEN", "").strip()
    )
    return SupportHubConfig(
        token=token,
        repo=repo,
        assignee=assignee,
        labels=labels,
        api_token=api_token,
    )


def create_support_issue(entry: dict[str, object]) -> tuple[int | None, str | None, str | None]:
    cfg = load_support_hub_config()
    if not cfg.token:
        return None, None, "SUPPORT_HUB_GITHUB_TOKEN not configured"

    payload = _build_issue_payload(entry, cfg)
    req = urlrequest.Request(
        f"https://api.github.com/repos/{cfg.repo}/issues",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {cfg.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "community-access-support-hub-sync",
        },
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("number"), data.get("html_url"), None
    except urlerror.HTTPError as exc:
        details = ""
        try:
            details = exc.read().decode("utf-8")
        except Exception:
            details = str(exc)
        return None, None, f"GitHub API error: {exc.code} {details}"
    except Exception as exc:  # noqa: BLE001
        return None, None, f"GitHub sync failed: {exc}"


def _build_issue_payload(entry: dict[str, object], cfg: SupportHubConfig) -> dict[str, object]:
    source_app = str(entry.get("source_app", "Unknown App") or "Unknown App").strip()
    category = str(entry.get("category", "feedback") or "feedback").strip().lower()
    summary = _issue_summary(entry)
    title = f"[{source_app}] {category}: {summary}"

    body_lines = [
        "## Support Intake",
        "",
        f"- Source application: `{source_app}`",
        f"- Submission channel: `{entry.get('source_channel', 'unknown') or 'unknown'}`",
        f"- Source version: `{entry.get('source_version', 'unknown') or 'unknown'}`",
        f"- Platform: `{entry.get('platform', 'unknown') or 'unknown'}`",
        f"- Feedback ID: `{entry.get('id', 'pending')}`",
        f"- Submitted at (UTC): `{entry.get('timestamp', 'unknown')}`",
        f"- Category: `{category}`",
    ]
    rating = str(entry.get("rating", "") or "").strip()
    task = str(entry.get("task", "") or "").strip()
    if rating:
        body_lines.append(f"- Rating: `{rating}`")
    if task:
        body_lines.append(f"- Task: `{task}`")
    if summary:
        body_lines.append(f"- Summary: {summary}")

    name = str(entry.get("name", "") or "").strip()
    email = str(entry.get("email", "") or "").strip()
    if name or email:
        body_lines.extend(["", "### Contact"])
        if name:
            body_lines.append(f"- Name: {name}")
        if email:
            body_lines.append(f"- Email: {email}")

    body_lines.extend(["", "### Message", "", str(entry.get("message", "") or "")])

    metadata_json = str(entry.get("metadata_json", "") or "").strip()
    if metadata_json:
        body_lines.extend(["", "### Additional Metadata", "", "```json", metadata_json, "```"])

    body_lines.extend(["", "---", "Source: Community Access support-hub automation."])

    payload: dict[str, object] = {
        "title": title[:240],
        "body": "\n".join(body_lines),
        "labels": cfg.labels,
    }
    if cfg.assignee:
        payload["assignees"] = [cfg.assignee]
    return payload


def _issue_summary(entry: dict[str, object]) -> str:
    summary = str(entry.get("summary", "") or "").strip()
    if summary:
        return summary[:90]
    task = str(entry.get("task", "") or "").strip()
    if task:
        return task[:90]
    message = str(entry.get("message", "") or "").strip().splitlines()[0] if entry.get("message") else ""
    if not message:
        return "new feedback"
    compact = " ".join(message.split())
    return compact[:90]
