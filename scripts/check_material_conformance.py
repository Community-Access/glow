#!/usr/bin/env python
"""Do the workshop materials still say what the plan decided?

Thirteen decisions were locked in ``docs/ahg-2026/plan.md`` (L1-L13). Several
of them are about what participants are told: no house AI, no printed
handouts, no plumbing, paste text rather than upload, two paths rather than
four tiers. Materials drift back toward the old story one helpful sentence at
a time, and the drift is invisible until somebody reads a handout aloud in a
room.

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
]

# Records of how we got here. Free to describe the past.
HISTORY = {
    "plan.md",
    "status-2026-09-21.md",
    "readiness-plan.md",
    "RELEASE-v7.3.0-WORKSHOP-MODE.md",
    "workshop-mode-implementation-plan.md",
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
        "L1: no house AI",
        r"\b(built-in AI|house AI|GLOW's own AI|our AI|AI allowance|AI budget|AI cap)\b",
        "The workshop provides no AI of its own.",
    ),
    Rule(
        "L1: no AI tiers",
        r"\bTier [0-3]\b|\bfour tiers\b|\bthree ways\b",
        "Two paths: GLOW in a browser, and your own assistant if you have one.",
    ),
    Rule(
        "L4/L8: electronic handouts only",
        r"\bprint (a dozen|the worksheet|worksheets)\b|\bprinted packs\b|\bpacks at the back\b",
        "We do not print handouts. Participants download, and print their own if they want paper.",
        allow=("we do not print", "not printing", "print it yourself", "print their own"),
    ),
    Rule(
        "L5: no plumbing",
        r"\b(MCP|model context protocol|/mcp\b|npm\b|command line|stdio)\b",
        "Participants never meet plumbing.",
    ),
    Rule(
        "L6: no vendor tooling requirement",
        r"\b(VS Code|Claude Code|Gemini CLI|Codex CLI|Copilot)\b",
        "No vendor-specific tooling in the room.",
        # L6 forbids *requiring* a vendor tool. Naming assistants a
        # participant may already have, in a sentence that says "whatever you
        # already use", is the case it explicitly permits -- and refusing to
        # name any would leave people guessing what we mean.
        allow=("already use", "already have", "you already"),
    ),
    Rule(
        "L12: text only, never upload",
        r"\bupload (the |an |your )?(image|images|file|files|document)\b",
        "Free accounts cap uploads and do not cap text. Paste text instead.",
        allow=("do not upload", "never upload", "without uploading", "rather than uploading"),
    ),
]

# Things that must be present somewhere in the material set.
REQUIRED_SOMEWHERE = [
    ("support@community-access.org", "L7: the support address participants are given"),
    ("letitglow.app", "L2: GLOW is the tool the day uses"),
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

    print("Checking workshop materials against the decisions in plan.md")
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
