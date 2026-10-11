"""The AHG 2026 agent kit, readable online at /ahg/kit.

Every file in docs/ahg-2026/kit gets its own address, so nobody has to unzip
anything to read a step card, an agent or a Copilot command, and anyone can
paste a file's plain-text address into Copilot or any other AI. Markdown is
shown as a page, converted with Pandoc when it is installed (it is on the
server), with raw HTML in the source switched off. Without Pandoc the text
is shown as it is.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from markupsafe import Markup, escape

# Folders in the order the kit README introduces them, with what each holds.
GROUPS: tuple[tuple[str, str, str], ...] = (
    ("", "Start here", "The kit's welcome page, and the VS Code profile."),
    ("step-cards", "Step cards", "One card per block, in the order things appear on screen. Read them here, or download the large print Word file."),
    ("my-agent", "Your agent", "The template you fill in during block 2. Copy it into your own folder, or ask Copilot to."),
    ("examples", "Worked examples", "Three people, three agents, from first draft to team report."),
    ("examples/agents", "Ready-made agents", "Six finished agents. Stuck at any point? Take one, put your name on it, and keep going. That counts."),
    ("office-team", "The office team", "The specialists your agent joins in block 6, one per kind of file."),
    (".github/prompts", "The Copilot commands", "What /ready-check, /design-my-agent and the rest of the commands tell Copilot to do."),
    (".github/agents", "The coordinator", "The agent that runs the office team."),
    (".github", "Copilot's instructions for the kit", "Read by Copilot whenever the kit is open."),
    (".vscode", "VS Code settings", "Large text, word wrap and the recommended extensions."),
)

TEXT_SUFFIXES = {".md", ".txt", ".json", ".vtt", ".code-profile", ".yml", ".yaml"}

# Kept out of the listing: they have better homes online.
ELSEWHERE = {
    "share-my-agent.html": "/ahg/share",
}


def kit_files(kit: Path) -> list[str]:
    """Every file in the kit, as kit-relative paths with forward slashes."""
    return sorted(p.relative_to(kit).as_posix() for p in kit.rglob("*") if p.is_file())


def group_of(rel: str) -> str:
    folder = rel.rsplit("/", 1)[0] if "/" in rel else ""
    # examples/agents/<name>/SKILL.md belongs to examples/agents, and
    # office-team/<name>/SKILL.md to office-team.
    known = [g[0] for g in GROUPS]
    while folder and folder not in known:
        folder = folder.rsplit("/", 1)[0] if "/" in folder else ""
    return folder


def label_for(rel: str) -> str:
    """A name a person can say: the agent's folder for SKILL.md files."""
    parts = rel.split("/")
    if parts[-1] == "SKILL.md" and len(parts) >= 2:
        return parts[-2].replace("-", " ").capitalize()
    name = parts[-1]
    for suffix in (".prompt.md", ".agent.md"):
        if name.endswith(suffix):
            return "/" + name[: -len(suffix)] if suffix == ".prompt.md" else name[: -len(suffix)].replace("-", " ").capitalize()
    return name


def split_front_matter(text: str) -> tuple[list[tuple[str, str]], str]:
    """YAML front matter as (key, value) pairs, and the Markdown after it."""
    if not text.startswith("---"):
        return [], text
    lines = text.splitlines()
    try:
        end = lines.index("---", 1)
    except ValueError:
        return [], text
    pairs = []
    for line in lines[1:end]:
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, value = line.split(":", 1)
            value = value.strip().strip('"').strip("'")
            if value:
                pairs.append((key.strip(), value))
    return pairs, "\n".join(lines[end + 1:])


_TABLE_OPEN = re.compile(r"<table>")


@lru_cache(maxsize=256)
def _pandoc_html(markdown: str) -> str | None:
    exe = shutil.which("pandoc")
    if not exe:
        return None
    try:
        done = subprocess.run(
            [exe, "-f", "gfm-raw_html", "-t", "html5", "--shift-heading-level-by=1", "--wrap=none"],
            input=markdown.encode("utf-8"), capture_output=True, timeout=20, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    html = done.stdout.decode("utf-8")
    # Wide tables scroll inside a named, focusable region instead of
    # widening the page (WCAG 1.4.10 reflow).
    count = 0

    def wrap(_m: re.Match) -> str:
        nonlocal count
        count += 1
        return f'<div class="table-scroll" role="region" aria-label="Table {count}" tabindex="0"><table>'

    html = _TABLE_OPEN.sub(wrap, html).replace("</table>", "</table></div>")
    return html


def markdown_page(text: str) -> tuple[list[tuple[str, str]], Markup]:
    """Front matter pairs, and the body as safe HTML."""
    pairs, body = split_front_matter(text)
    html = _pandoc_html(body)
    if html is None:
        return pairs, Markup(f'<pre class="plain">{escape(body)}</pre>')
    return pairs, Markup(html)
