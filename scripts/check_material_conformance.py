#!/usr/bin/env python
"""Do the workshop materials keep the promises the program made?

The AHG program promises a full-day, laptop, hands-on workshop in which
participants build accessibility agents and agent teams with VS Code, GitHub
and Copilot, grounded in axe-core and Accessibility Insights, and commit an
agent to the open-source Accessibility Agents repository. ``plan.md`` records
how each promise is kept (D1 to D15).

The September plan said the opposite in several places: no AI, no
development tools, a phone is enough, no account. Materials written then
drift back one helpful sentence at a time, and the drift is invisible until
somebody reads a handout aloud in a room.

So this checks the documents and templates a participant or facilitator
actually meets, against the decisions, and says where they disagree.

**Two kinds of file, deliberately separated.** Materials used *on the day*
must conform. Records of how we got here -- the plan, the status assessment,
the readiness history, past release notes -- must be free to describe what was
true before, or they cannot do their job.

    python scripts/check_material_conformance.py
    python scripts/check_material_conformance.py --verbose

Exit code 0 when the materials conform, 1 otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AHG = REPO / "docs" / "ahg-2026"
TEMPLATES = REPO / "web" / "src" / "acb_large_print_web" / "templates" / "workshop"

# Used on the day. These must conform.
MATERIALS = [
    AHG / "workshop-frontfacing-guide.md",
    AHG / "workshop-frontfacing-exercises.md",
    AHG / "workshop-frontfacing-utilization.md",
    AHG / "workshop-mode-facilitator-runbook.md",
    AHG / "run-of-show.md",
    AHG / "facilitator-card.md",
    AHG / "pre-event-message.md",
    AHG / "slides.md",
    AHG / "README.md",
    AHG / "kit" / "README.md",
    AHG / "kit" / "my-agent" / "SKILL.md",
    AHG / "worked-examples" / "maria-alternate-format-planner.md",
    AHG / "worked-examples" / "jordan-faculty-coach.md",
    AHG / "worked-examples" / "sam-remediation-log-keeper.md",
]

# Records of how we got here. Free to describe the past.
HISTORY = {
    "plan.md",
    "status-2026-09-21.md",
    "readiness-plan.md",
    "RELEASE-v7.3.0-WORKSHOP-MODE.md",
    "workshop-mode-implementation-plan.md",
    "plan-2026-09-glow-only.md",
    "answer-key.md",
}


class Rule:
    """One decision, expressed as a pattern that must not appear."""

    def __init__(self, decision: str, pattern: str, why: str, allow: tuple[str, ...] = ()):
        self.decision = decision
        self.regex = re.compile(pattern, re.IGNORECASE)
        self.why = why
        self.allow = tuple(a.lower() for a in allow)

    def violations(self, text: str) -> list[tuple[int, str]]:
        found = []
        for number, line in enumerate(text.splitlines(), start=1):
            match = self.regex.search(line)
            if not match:
                continue
            lowered = line.lower()
            if any(phrase in lowered for phrase in self.allow):
                continue
            found.append((number, line.strip()))
        return found


RULES = [
    Rule(
        "D3: no house AI",
        r"\b(built-in AI|house AI|GLOW's own AI|our AI|AI allowance|AI budget|AI cap)\b",
        "The workshop provides no AI of its own; each participant's Copilot is theirs.",
    ),
    Rule(
        "D3: the September tiers are gone",
        r"\bTier [0-3]\b|\bfour tiers\b|\bthree ways\b|\btwo ways\b",
        "One path: Copilot all day, VS Code and GitHub in the afternoon.",
    ),
    Rule(
        "D2: a laptop is required",
        r"\bphone (is fine|is enough|counts|included)\b|\ba phone counts\b|\bany device\b",
        "The program says bring a Windows or Mac laptop.",
    ),
    Rule(
        "D3/D9: participants use their own GitHub account",
        r"\bno account\b|\bwithout an account\b|\bno sign-in\b|\bno AI\b",
        "Every participant has a free GitHub account with Copilot Free.",
    ),
    Rule(
        "D2/D15: no command line, no installs beyond VS Code",
        r"\b(MCP|model context protocol|/mcp\b|npm\b|command line|stdio|git clone|terminal)\b",
        "Participants never meet a terminal; the profile installs everything.",
        allow=("no terminal", "never meet a terminal", "no command line"),
    ),
    Rule(
        "D4: text only, never upload",
        r"\bupload (the |an |your )?(image|images|file|files|document)\b",
        "Free accounts cap uploads and do not cap text. Paste text instead.",
        allow=("do not upload", "never upload", "without uploading", "rather than uploading"),
    ),
]

# Things that must be present somewhere in the material set.
REQUIRED_SOMEWHERE = [
    ("support@community-access.org", "D13: the support address participants are given"),
    ("VS Code", "Promise: agents and teams built with Visual Studio Code"),
    ("Copilot", "Promise: agents and teams built with GitHub Copilot"),
    ("GitHub", "Promise: open-source collaboration on GitHub"),
    ("pull request", "Promise: participants commit an agent to the repository"),
    ("Accessibility Agents", "Promise: the open-source Accessibility Agents repository"),
    ("axe", "Promise: axe-core grounding"),
    ("Accessibility Insights", "Promise: Accessibility Insights grounding"),
    ("agent team", "Promise: agent teams of coordinated specialists"),
    ("Title II", "Promise: the higher education Title II context"),
    ("WCAG 2.2", "Promise: grounded in WCAG 2.2"),
    ("session evaluation", "D14: time saved for the AHG session evaluation"),
]


def check(path: Path, verbose: bool) -> list[str]:
    problems: list[str] = []
    if not path.exists():
        return [f"{path.name}: MISSING"]

    text = path.read_text(encoding="utf-8")
    for rule in RULES:
        for number, line in rule.violations(text):
            problems.append(
                f"{path.name}:{number}  [{rule.decision}]\n"
                f"      {line[:110]}\n"
                f"      -> {rule.why}"
            )
    if verbose and not problems:
        print(f"  OK    {path.name}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("Checking workshop materials against the program's promises (plan.md, D1 to D15)")
    print("=" * 74)

    problems: list[str] = []
    for path in MATERIALS:
        problems.extend(check(path, args.verbose))

    # Served templates count as material: a participant reads them on the day.
    for path in sorted(TEMPLATES.glob("*.html")):
        problems.extend(check(path, args.verbose))

    corpus = "\n".join(
        p.read_text(encoding="utf-8") for p in MATERIALS if p.exists()
    )
    for needle, why in REQUIRED_SOMEWHERE:
        if needle.lower() not in corpus.lower():
            problems.append(f"MISSING from every material: {needle}  [{why}]")

    if problems:
        print(f"\n{len(problems)} non-conformance(s):\n")
        for problem in problems:
            print(f"  {problem}\n")
        print("=" * 74)
        print(f"  {len(problems)} to fix.")
        return 1

    print("\n  Every material conforms to the locked decisions.")
    print(f"  Checked {len(MATERIALS)} documents and "
          f"{len(list(TEMPLATES.glob('*.html')))} templates.")
    print("  (Records of how we got here are excluded by design: "
          + ", ".join(sorted(HISTORY)) + ")")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
