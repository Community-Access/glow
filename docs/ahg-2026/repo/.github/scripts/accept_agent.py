#!/usr/bin/env python
"""Turn a "Share my agent" issue into a commit, credited to the person who sent it.

Runs from .github/workflows/accept-agent.yml when an issue with the
"agent-submission" label is opened or edited. Reads the issue from the
GitHub event file, never from the shell, because everything in an issue is
untrusted text.

If the agent is ready, this writes it to agents/<github-login>/<name>/SKILL.md
(or practice/<github-login>/SKILL.md for a practice agent), rebuilds the
gallery in agents/README.md, and tells the workflow to commit and reply. If
something needs fixing, it writes a friendly reply that says exactly what,
and nothing is committed.

Outputs, for the workflow, in $GITHUB_OUTPUT:
  status   accepted | needs-a-hand
  path     the file written, when accepted
  practice true | false
Writes the reply to post on the issue to reply.md.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SECTIONS = ("## Role", "## Task", "## Trusted guidance", "## Output format", "## Human review", "## Never")
MAX_BYTES = 20_000

# Things that look private. A workshop agent should never contain any of them.
PRIVATE = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "an email address"),
    (re.compile(r"\b\d{3}[-. ]\d{3}[-. ]\d{4}\b"), "a phone number"),
    (re.compile(r"\b\d{7,}\b"), "a long number, which could be a student ID"),
    (re.compile(r"\bstudent id\b", re.I), "the words student ID"),
]
ALLOWED_EMAILS = ("support@community-access.org",)


def parse_issue(body: str) -> dict[str, str]:
    """Split an issue form's body into {heading: value}."""
    fields: dict[str, str] = {}
    current = None
    lines: list[str] = []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        if line.startswith("### "):
            if current is not None:
                fields[current] = "\n".join(lines).strip()
            current = line[4:].strip()
            lines = []
        else:
            lines.append(line)
    if current is not None:
        fields[current] = "\n".join(lines).strip()
    return fields


def unfence(text: str) -> str:
    """The agent arrives inside a ```markdown fence; take it out."""
    text = (text or "").strip()
    match = re.match(r"^```[\w-]*\n(.*?)\n?```\s*$", text, re.S)
    return (match.group(1) if match else text).strip() + "\n"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")[:60]


def check(fields: dict[str, str], expected_code: str) -> tuple[list[str], dict]:
    """Return (problems, info). No problems means the agent can go in."""
    problems: list[str] = []
    code = fields.get("Workshop code", "").strip()
    if expected_code and code.lower() != expected_code.lower():
        problems.append(
            "The workshop code does not match. It is on your table card and in your setup email. "
            "Edit this issue, fix the code, and save; I will check again straight away."
        )

    practice = "practice" in fields.get("Is this your practice agent, or your real one?", "").lower()
    agent = unfence(fields.get("Your agent", ""))
    info = {"practice": practice, "agent": agent, "name": "", "title": "", "description": "", "author": ""}

    if len(agent.encode("utf-8")) > MAX_BYTES:
        problems.append("Your agent is longer than 20,000 characters. Shorten the guidance and try again.")

    header = None
    if not agent.startswith("---\n"):
        problems.append(
            "Your agent needs to start with its header: a line of three dashes, then name, description "
            "and the rest. Copy the whole of SKILL.md, from the very first line."
        )
    else:
        try:
            end = agent.index("\n---\n", 4)
            header = yaml.safe_load(agent[4:end]) or {}
        except (ValueError, yaml.YAMLError):
            problems.append(
                "The header at the top of your agent could not be read. The usual cause is a colon inside "
                "a description or author that is not in double quotes. Put those values in double quotes, "
                "as the template shows."
            )

    if isinstance(header, dict):
        info["name"] = slug(str(header.get("name", "")))
        info["description"] = str(header.get("description", "")).strip()
        meta = header.get("metadata") or {}
        if isinstance(meta, dict):
            info["title"] = str(meta.get("title", "")).strip()
            info["author"] = str(meta.get("author", "")).strip()
        if not practice and info["name"] in ("", "my-agent-name"):
            problems.append("Give your agent a name of its own on the name line, like faculty-coach.")
        if not practice and info["author"] in ("", "Your Name, Your Institution"):
            problems.append("Put your name on the author line, so your agent is credited to you.")

    if not practice:
        missing = [s[3:] for s in SECTIONS if s not in agent]
        if missing:
            problems.append("Your agent is missing these headings: " + ", ".join(missing) + ".")

    for pattern, what in PRIVATE:
        for match in pattern.finditer(agent):
            if match.group(0).lower() in ALLOWED_EMAILS:
                continue
            problems.append(
                f"Your agent seems to contain {what}. Workshop agents must contain nothing private. "
                "Take it out, edit this issue, and save."
            )
            break

    return problems, info


def gallery(root: Path) -> str:
    rows = []
    for path in sorted((root / "agents").glob("*/*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        try:
            header = yaml.safe_load(text[4:text.index("\n---\n", 4)]) or {}
        except (ValueError, yaml.YAMLError):
            header = {}
        meta = header.get("metadata") or {}
        title = str(meta.get("title") or header.get("name") or path.parent.name).replace("|", "-")
        author = str(meta.get("author") or "").replace("|", "-")
        what = str(header.get("description") or "").replace("|", "-")
        login = path.parent.parent.name
        rel = path.relative_to(root / "agents").as_posix()
        rows.append(f"| [{title}]({rel}) | {author} | [@{login}](https://github.com/{login}) | {what} |")
    lines = [
        "# Agents built at AHG 2026",
        "",
        "Every accessibility agent shared at Accessing Higher Ground 2026, written by",
        "the people who do this work in higher education. Each one is plain English,",
        "free to use and improve, and cites the standards it relies on.",
        "",
        f"{len(rows)} agents so far.",
        "",
    ]
    if rows:
        lines += [
            "Each row is one agent, who wrote it, and what it does.",
            "",
            "| Agent | Author | On GitHub | What it does |",
            "|---|---|---|---|",
            *rows,
            "",
        ]
    return "\n".join(lines)


def accept(info: dict, login: str, root: Path = ROOT) -> Path:
    if info["practice"]:
        target = root / "practice" / slug(login) / "SKILL.md"
    else:
        target = root / "agents" / slug(login) / info["name"] / "SKILL.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(info["agent"], encoding="utf-8")
    (root / "agents" / "README.md").write_text(gallery(root), encoding="utf-8")
    return target


def reply_accepted(info: dict, login: str, url: str, number_in_gallery: int) -> str:
    if info["practice"]:
        return (
            f"Well done, @{login}. Your practice agent is in: {url}\n\n"
            "That was the whole of sharing. On the day you will do exactly this once more, "
            "with your real agent. Nothing else to set up.\n"
        )
    name = info["title"] or info["name"]
    return (
        f"Your agent is in, @{login}. \"{name}\" is now part of the AHG 2026 collection, "
        f"agent number {number_in_gallery}, with your name on it.\n\n"
        f"- Your agent: {url}\n"
        "- The whole collection: https://github.com/Community-Access/ahg-2026/blob/main/agents/README.md\n\n"
        "At the end of the day every agent here goes into the open-source Accessibility Agents "
        "project, with each author credited. Thank you for building it.\n\n"
        "Want to change it? Edit this issue and save. Your agent updates.\n"
    )


def reply_problems(problems: list[str], login: str) -> str:
    lines = [
        f"Nearly there, @{login}. One or two things to fix, and then your agent goes straight in:",
        "",
        *[f"{n}. {p}" for n, p in enumerate(problems, start=1)],
        "",
        "To fix it: open the menu at the top of this issue, choose Edit, change the text, and save. "
        "I check again as soon as you save. A helper can do this with you; raise a hand.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    issue = event["issue"]
    login = issue["user"]["login"]
    expected = os.environ.get("WORKSHOP_CODE", "AHG2026").strip()

    problems, info = check(parse_issue(issue.get("body") or ""), expected)
    out = Path(os.environ.get("GITHUB_OUTPUT", "github_output.txt"))
    reply = Path("reply.md")

    if problems:
        reply.write_text(reply_problems(problems, login), encoding="utf-8")
        with out.open("a", encoding="utf-8") as fh:
            fh.write("status=needs-a-hand\npractice=false\n")
        return 0

    path = accept(info, login)
    rel = path.relative_to(ROOT).as_posix()
    url = f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', 'Community-Access/ahg-2026')}/blob/main/{rel}"
    count = len(list((ROOT / "agents").glob("*/*/SKILL.md")))
    reply.write_text(reply_accepted(info, login, url, count), encoding="utf-8")
    with out.open("a", encoding="utf-8") as fh:
        fh.write(f"status=accepted\npath={rel}\npractice={'true' if info['practice'] else 'false'}\n")
        # Untrusted text going into a workflow output: one safe line only.
        label = f"practice agent from {login}" if info["practice"] else (info["title"] or info["name"])
        title = re.sub(r"[^\w ,.'()-]", "", label)[:80]
        fh.write(f"title={title}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
