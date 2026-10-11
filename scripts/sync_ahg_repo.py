#!/usr/bin/env python
"""Copy the AHG 2026 kit and repository files into a checkout of Community-Access/ahg-2026.

GLOW is the source of truth: the kit lives in docs/ahg-2026/kit and the
workshop repository's own files (share form, automation, README, scripts)
live in docs/ahg-2026/repo. This copies both into a local checkout of the
workshop repository, without touching agents/ or practice/ beyond their
README files, so participants' agents are never overwritten.

    python scripts/sync_ahg_repo.py ../ahg-2026
    cd ../ahg-2026 && git add -A && git commit && git push
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SOURCE_REPO = REPO / "docs" / "ahg-2026" / "repo"
SOURCE_KIT = REPO / "docs" / "ahg-2026" / "kit"
KEEP = ("agents", "practice")


def copy_tree(src: Path, dst: Path) -> int:
    count = 0
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        if rel.parts[0] in KEEP and rel.name != "README.md":
            continue
        if rel.parts[0] == "agents" and rel.name == "README.md" and (dst / rel).exists():
            continue  # the gallery is rebuilt by the automation; never reset it
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        count += 1
    return count


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    dest = Path(sys.argv[1]).resolve()
    if not (dest / ".git").exists():
        print(f"Not a git checkout: {dest}")
        return 2
    kit = dest / "kit"
    if kit.exists():
        shutil.rmtree(kit)
    n = copy_tree(SOURCE_REPO, dest)
    m = copy_tree(SOURCE_KIT, kit)
    print(f"{n} repository files and {m} kit files copied into {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
