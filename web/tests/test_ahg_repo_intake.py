"""The automation that adds a shared agent to Community-Access/ahg-2026.

The script lives in docs/ahg-2026/repo/.github/scripts/accept_agent.py and is
synced into the workshop repository. These tests run it against the issue
bodies GitHub's form produces, so the moment someone presses the button is
tested before the day, not on it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "docs" / "ahg-2026" / "repo" / ".github" / "scripts" / "accept_agent.py"
KIT = REPO / "docs" / "ahg-2026" / "kit"


@pytest.fixture(scope="module")
def intake():
    spec = importlib.util.spec_from_file_location("accept_agent", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def body(agent: str, code: str = "AHG2026", kind: str = "My real agent") -> str:
    return (
        f"### Workshop code\n\n{code}\n\n"
        f"### Is this your practice agent, or your real one?\n\n{kind}\n\n"
        f"### Your agent\n\n```markdown\n{agent}\n```\n\n"
        "### Privacy\n\n- [X] My agent contains nothing private.\n"
    )


def ready_made(name: str = "faculty-coach") -> str:
    return (KIT / "examples" / "agents" / name / "SKILL.md").read_text(encoding="utf-8")


def test_a_ready_made_agent_goes_straight_in(intake, tmp_path):
    problems, info = intake.check(intake.parse_issue(body(ready_made())), "AHG2026")
    assert problems == []
    assert info["name"] == "faculty-coach" and not info["practice"]
    (tmp_path / "agents").mkdir()
    path = intake.accept(info, "Jane-Doe", tmp_path)
    assert path == tmp_path / "agents" / "jane-doe" / "faculty-coach" / "SKILL.md"
    gallery = (tmp_path / "agents" / "README.md").read_text(encoding="utf-8")
    assert "1 agents so far" in gallery and "Faculty Coach" in gallery


def test_the_practice_agent_goes_to_practice(intake, tmp_path):
    template = (KIT / "my-agent" / "SKILL.md").read_text(encoding="utf-8")
    problems, info = intake.check(intake.parse_issue(body(template, kind="My practice agent")), "AHG2026")
    assert problems == [], "the untouched template is a fine practice agent"
    (tmp_path / "agents").mkdir()
    path = intake.accept(info, "someone", tmp_path)
    assert path == tmp_path / "practice" / "someone" / "SKILL.md"


def test_the_untouched_template_is_not_a_real_agent(intake):
    template = (KIT / "my-agent" / "SKILL.md").read_text(encoding="utf-8")
    problems, _ = intake.check(intake.parse_issue(body(template)), "AHG2026")
    assert any("name of its own" in p for p in problems)
    assert any("author line" in p for p in problems)


def test_a_wrong_workshop_code_is_explained(intake):
    problems, _ = intake.check(intake.parse_issue(body(ready_made(), code="ahg2025")), "AHG2026")
    assert any("workshop code" in p for p in problems)


def test_the_code_is_not_case_sensitive(intake):
    problems, _ = intake.check(intake.parse_issue(body(ready_made(), code="ahg2026")), "AHG2026")
    assert problems == []


def test_private_details_are_refused(intake):
    leaky = ready_made().replace("## Role", "Contact jane.student@university.edu, ID 900123456.\n\n## Role")
    problems, _ = intake.check(intake.parse_issue(body(leaky)), "AHG2026")
    assert any("email address" in p for p in problems)
    assert any("student ID" in p for p in problems)


def test_an_unquoted_colon_gets_a_plain_explanation(intake):
    broken = ready_made().replace('author: "Example: Jordan Lee, Mesa Ridge State University"',
                                  "author: Example: Jordan Lee")
    problems, _ = intake.check(intake.parse_issue(body(broken)), "AHG2026")
    assert any("double quotes" in p for p in problems)


def test_a_missing_heading_is_named(intake):
    partial = ready_made().replace("## Human review", "## Reviewing")
    problems, _ = intake.check(intake.parse_issue(body(partial)), "AHG2026")
    assert any("Human review" in p for p in problems)


def test_a_hostile_name_cannot_escape_the_folder(intake, tmp_path):
    hostile = ready_made().replace("name: faculty-coach", "name: ../../.github/workflows/x")
    problems, info = intake.check(intake.parse_issue(body(hostile)), "AHG2026")
    assert problems == []
    (tmp_path / "agents").mkdir()
    path = intake.accept(info, "../evil", tmp_path)
    assert tmp_path / "agents" in path.parents
    assert ".." not in path.relative_to(tmp_path).as_posix()


def test_replies_are_warm_and_specific(intake):
    _, info = intake.check(intake.parse_issue(body(ready_made())), "AHG2026")
    yes = intake.reply_accepted(info, "jane", "https://example.test/x", 7)
    assert "Your agent is in, @jane" in yes and "agent number 7" in yes and "Accessibility Agents" in yes
    no = intake.reply_problems(["Fix the code."], "jane")
    assert "Nearly there" in no and "1. Fix the code." in no and "Edit" in no
