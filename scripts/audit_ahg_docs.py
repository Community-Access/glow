#!/usr/bin/env python
"""Run GLOW's own audits over every AHG 2026 document a person reads.

Markdown documents go through GLOW's Markdown auditor; the Word and
PowerPoint deck and the Word step cards go through GLOW's Office auditors.
A document passes when GLOW says it passes and has no critical or high
finding.

The Copilot instruction files in ``kit/.github/`` and the agent files
(``SKILL.md``) are left out on purpose: their headers are fixed by VS Code
and the Agent Skills format, not written for a reader, and
``web/tests/test_workshop_ahg_kit.py`` checks their content instead.

    python scripts/audit_ahg_docs.py            # summary
    python scripts/audit_ahg_docs.py --verbose  # every finding

Exit code 0 when every document passes.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AHG = REPO / "docs" / "ahg-2026"
sys.path.insert(0, str(REPO / "desktop" / "src"))

from acb_large_print import md_auditor  # noqa: E402
from acb_large_print.auditor import audit_document  # noqa: E402
from acb_large_print.pptx_auditor import audit_presentation  # noqa: E402

SEPTEMBER = {
    "plan-2026-09-glow-only.md", "status-2026-09-21.md", "readiness-plan.md",
    "RELEASE-v7.3.0-WORKSHOP-MODE.md", "workshop-mode-data-model.md",
    "workshop-mode-facilitator-runbook.md", "workshop-mode-implementation-plan.md",
    "workshop-mode-wcag-checklist.md", "workshop-frontfacing-exercises.md",
    "workshop-frontfacing-utilization.md",
}


def markdown_files() -> list[Path]:
    files = [REPO / "ahg.md"] if (REPO / "ahg.md").exists() else []
    for path in sorted(AHG.rglob("*.md")):
        rel = path.relative_to(AHG)
        if path.name in SEPTEMBER or path.name == "SKILL.md" or ".github" in rel.parts:
            continue
        files.append(path)
    return files


def office_files() -> list[tuple[Path, object]]:
    files: list[tuple[Path, object]] = [
        (AHG / "slides.docx", audit_document),
        (AHG / "slides.pptx", audit_presentation),
    ]
    files += [(p, audit_document) for p in sorted((AHG / "kit" / "step-cards").glob("*.docx"))]
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    failures = 0
    checked = 0
    jobs = [(p, md_auditor.audit_markdown) for p in markdown_files()] + office_files()
    for path, audit in jobs:
        result = audit(path)
        checked += 1
        serious = [f for f in result.findings
                   if str(f.severity).split(".")[-1] in {"CRITICAL", "HIGH"}]
        ok = result.passed and not serious
        failures += 0 if ok else 1
        if not ok or args.verbose:
            print(f"{'PASS' if ok else 'FAIL'}  {result.score:3}  {path.relative_to(REPO).as_posix()}")
            counts = Counter((f.rule_id, str(f.severity).split(".")[-1]) for f in result.findings)
            for (rule, severity), n in counts.most_common():
                print(f"        {n:3} {severity:<8} {rule}")
    print(f"{checked} documents checked, {failures} not passing.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
