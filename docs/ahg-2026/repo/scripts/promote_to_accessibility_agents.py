#!/usr/bin/env python
"""Send every AHG 2026 agent to the Accessibility Agents project, authors credited.

Run at the end of the workshop by the facilitator, from a checkout of this
repository, with a checkout of Community-Access/accessibility-agents beside
it on a new branch:

    python scripts/promote_to_accessibility_agents.py ../accessibility-agents

It copies agents/<login>/<name>/SKILL.md to
community/ahg-2026/<name>/SKILL.md in that checkout (adding the login to the
folder name when two people chose the same name), and writes
commit-message.txt here, with a Co-authored-by line for every author taken
from this repository's own history, so GitHub credits each of them. Then:

    cd ../accessibility-agents
    git add community/ahg-2026
    git commit -F ../ahg-2026/commit-message.txt
    git push, and open the pull request
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def authors_of(path: Path) -> list[str]:
    out = subprocess.run(
        ["git", "log", "--format=%an <%ae>", "--", str(path.relative_to(ROOT))],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    seen = []
    for line in out.splitlines():
        if line and "github-actions" not in line and line not in seen:
            seen.append(line)
    return seen


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    target_repo = Path(sys.argv[1]).resolve()
    dest_root = target_repo / "community" / "ahg-2026"
    if not (target_repo / ".git").exists():
        print(f"Not a git checkout: {target_repo}")
        return 2

    agents = sorted((ROOT / "agents").glob("*/*/SKILL.md"))
    names = [p.parent.name for p in agents]
    coauthors: list[str] = []
    for path in agents:
        login, name = path.parent.parent.name, path.parent.name
        folder = name if names.count(name) == 1 else f"{name}-{login}"
        out = dest_root / folder / "SKILL.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        for author in authors_of(path):
            if author not in coauthors:
                coauthors.append(author)
        print(f"  {path.relative_to(ROOT).as_posix()} -> community/ahg-2026/{folder}/SKILL.md")

    message = [
        f"Add {len(agents)} agents from the AHG 2026 workshop",
        "",
        "Written by participants at Accessibility Agents: Building Human-Centered",
        "AI Workflows for Trusted Accessibility Automation at Scale, Accessing",
        "Higher Ground, Denver, 16 November 2026. Collected in",
        "https://github.com/Community-Access/ahg-2026.",
        "",
        *[f"Co-authored-by: {a}" for a in coauthors],
    ]
    (ROOT / "commit-message.txt").write_text("\n".join(message) + "\n", encoding="utf-8")
    print(f"{len(agents)} agents, {len(coauthors)} authors. Commit message in commit-message.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
