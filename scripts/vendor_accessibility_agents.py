#!/usr/bin/env python
"""Ship Accessibility Agents inside the AHG 2026 agent kit.

VS Code, on a computer and at vscode.dev, uses every skill in the
``.github/skills`` folder of the folder that is open. The kit is that
folder, so copying Accessibility Agents' skills there gives every VS Code
participant the whole project with nothing to install: no terminal, no
plugin, no extension.

What the kit cannot carry is the project's scanner tools (its MCP server),
its scripts and its hooks. This script records, for every skill, what it
relies on, in ``accessibility-agents-skills.json`` in the kit, so the kit's
card can say plainly what works and what needs the full install. When the
Accessibility Agents checkout has its own capability matrix,
``docs/reference/no-install-capability.json``, that is used instead of the
heuristic here.

    python scripts/vendor_accessibility_agents.py ../agents
    python scripts/vendor_accessibility_agents.py            # downloads main from GitHub,
                                                             # pinned to its current commit

The project's MIT licence travels with the copy, as
``accessibility-agents-LICENSE.txt`` in the kit, because the licence requires
its copyright and permission notice in every copy.

Run ``scripts/build_ahg_kit.py`` afterwards to rebuild the zip.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KIT = REPO / "docs" / "ahg-2026" / "kit"
TARGET = KIT / ".github" / "skills"
MANIFEST = KIT / "accessibility-agents-skills.json"
ZIP_URL = "https://github.com/Community-Access/accessibility-agents/archive/{ref}.zip"
COMMIT_API = "https://api.github.com/repos/Community-Access/accessibility-agents/commits/main"
LICENSE_COPY = KIT / "accessibility-agents-LICENSE.txt"
SOURCE_URL = "https://github.com/Community-Access/accessibility-agents"

# The kit's own commands. Never overwritten, and never listed as
# Accessibility Agents skills.
KIT_COMMANDS = {
    "ready-check", "design-my-agent", "try-my-agent", "ground-my-agent",
    "run-the-office", "my-30-day-plan", "review-my-agent", "install-my-agent",
}

SCANNERS = re.compile(r"\bmcp\b|\brun_[a-z_]+|\bscan_[a-z_]+\(|playwright|verapdf", re.I)
SCRIPTS = re.compile(r"scripts/[a-z0-9_-]+\.(?:mjs|py|js)|\bnode scripts\b|\bpython scripts\b")
GITHUB_CLI = re.compile(r"\bgh (?:issue|pr|api|run|release|repo|project)\b|GitHub CLI|gh CLI")

NEEDS = {
    "scanners": "Its scanner tools are not in the kit. Give it your checker's results instead, or use the full version in Codespaces.",
    "github": "Needs the GitHub command-line tool. Use the full version in Codespaces.",
    "scripts": "Its report scripts are not in the kit. It writes its findings directly instead.",
}


def fetch_source(arg: str | None) -> tuple[Path, str]:
    if arg:
        src = Path(arg).resolve()
        if not (src / "skills").is_dir():
            sys.exit(f"No skills folder in {src}")
        try:
            sha = subprocess.run(["git", "-C", str(src), "rev-parse", "HEAD"],
                                 capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            sha = "unknown"
        return src, sha
    # Pin to the commit main points at now, so the kit can always say exactly
    # which version it carries (ahg.md, D-016).
    req = urllib.request.Request(COMMIT_API, headers={"Accept": "application/vnd.github.sha"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        sha = resp.read().decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        sys.exit(f"Could not read the commit main points at; pass a checkout instead. Got: {sha[:80]!r}")
    tmp = Path(tempfile.mkdtemp(prefix="aa-"))
    with urllib.request.urlopen(ZIP_URL.format(ref=sha), timeout=60) as resp:
        data = resp.read()
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(tmp)
    root = next(tmp.iterdir())
    return root, sha


def classify(skill_dir: Path) -> list[str]:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    needs = []
    if SCANNERS.search(text):
        needs.append("scanners")
    if GITHUB_CLI.search(text):
        needs.append("github")
    if SCRIPTS.search(text):
        needs.append("scripts")
    return needs


def front(skill_dir: Path) -> dict[str, str]:
    lines = (skill_dir / "SKILL.md").read_text(encoding="utf-8").splitlines()
    out: dict[str, str] = {}
    if not lines or lines[0] != "---":
        return out
    for line in lines[1:]:
        if line == "---":
            break
        if ":" in line and not line.startswith((" ", "-")):
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip().strip('"').strip("'")
    return out


LIMITS_PAGE = KIT / "accessibility-agents-in-the-kit.md"


def write_limits_page(skills: list[dict], sha: str) -> None:
    """A page a participant can read: what works in the kit, and what does not."""
    full = [s for s in skills if not s["needs"]]
    lines = [
        "---",
        'title: "Accessibility Agents in this kit"',
        "lang: en",
        'author: "Generated by scripts/vendor_accessibility_agents.py"',
        'description: "Which Accessibility Agents skills work fully in the AHG 2026 kit, and which need the full version."',
        "---",
        "",
        "# Accessibility Agents in this kit",
        "",
        f"This kit carries all {len(skills)} Accessibility Agents skills, from",
        f"commit `{sha[:7]}` of [Accessibility Agents]({SOURCE_URL}), in `.github/skills`. Open the",
        "kit in VS Code, on a computer or at vscode.dev, and they are there:",
        "start a new chat and ask for one by name. Nothing to install.",
        "",
        "They are under the project's MIT licence, which is in",
        "`accessibility-agents-LICENSE.txt` in this kit.",
        "",
        "The kit cannot carry the project's scanner tools, its scripts or its",
        "hooks. So every skill below works, but some work differently here. The",
        "full version, with everything, is one click away in Codespaces:",
        "`accessibility-agents.md` in this kit says how.",
        "",
        "## Works fully in the kit",
        "",
        f"{len(full)} skills need nothing the kit lacks. These are the ones you can ask for by name; the rest are specialists they call for you:",
        "",
    ]
    lines += [f"- `{s['name']}`" for s in full if s["you_can_ask_for_it"]]
    lines += [
        "",
        "## Works differently in the kit",
        "",
        "Each row is one skill that relies on something the kit cannot carry,",
        "and what it does instead.",
        "",
        "| Skill | In the kit |",
        "|---|---|",
    ]
    for s in skills:
        if s["needs"]:
            lines.append(f"| `{s['name']}` | {' '.join(s['in_the_kit'])} |")
    lines += [
        "",
        "Never trust a skill that says it scanned something when the scanners",
        "are not there. Give it your checker's results: Word's, PowerPoint's or",
        "Acrobat's Accessibility Checker, Accessibility Insights, or axe.",
        "",
    ]
    LIMITS_PAGE.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    src, sha = fetch_source(sys.argv[1] if len(sys.argv) > 1 else None)
    matrix_path = src / "docs" / "reference" / "no-install-capability.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8")) if matrix_path.is_file() else None

    TARGET.mkdir(parents=True, exist_ok=True)
    # Remove the previous copy, keeping the kit's own commands.
    for old in TARGET.iterdir():
        if old.is_dir() and old.name not in KIT_COMMANDS:
            shutil.rmtree(old)

    skills = []
    for skill_dir in sorted(p for p in (src / "skills").iterdir() if (p / "SKILL.md").is_file()):
        name = skill_dir.name
        if name in KIT_COMMANDS:
            sys.exit(f"Accessibility Agents has a skill named {name}, the same as a kit command")
        shutil.copytree(skill_dir, TARGET / name, ignore=shutil.ignore_patterns("node_modules", "__pycache__"))
        meta = front(skill_dir)
        if matrix and name in matrix.get("skills", {}):
            entry = matrix["skills"][name]
            needs = entry.get("needs", [])
        else:
            needs = classify(skill_dir)
        skills.append({
            "name": name,
            "description": meta.get("description", ""),
            "you_can_ask_for_it": meta.get("user-invocable", "true") != "false",
            "needs": needs,
            "in_the_kit": [NEEDS[n] for n in needs if n in NEEDS],
        })

    MANIFEST.write_text(json.dumps({
        "source": SOURCE_URL,
        "commit": sha,
        "classified_by": "the project's capability matrix" if matrix else "this script's reading of each SKILL.md",
        "skills": skills,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    licence = src / "LICENSE"
    if not licence.is_file():
        sys.exit(f"No LICENSE in {src}: the MIT licence must travel with the copy")
    LICENSE_COPY.write_text(
        "Accessibility Agents, " + SOURCE_URL + ", commit " + sha + "\n"
        "The skills in .github/skills that are not the kit's own commands are\n"
        "copied unchanged from that project, under this licence.\n\n"
        + licence.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    write_limits_page(skills, sha)
    full = sum(1 for s in skills if not s["needs"])
    print(f"{len(skills)} Accessibility Agents skills copied into {TARGET.relative_to(REPO)} from {sha[:7]}")
    print(f"  {full} work fully in the kit; {len(skills) - full} rely on something the kit cannot carry")
    for key in NEEDS:
        names = [s["name"] for s in skills if key in s["needs"]]
        print(f"  {key}: {len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
