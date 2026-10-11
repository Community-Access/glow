"""The AHG 2026 agent kit, and the GLOW pages that hand it to participants.

The day promises that everyone builds an agent, joins an agent team and opens
a pull request. These tests hold the parts that make that promise safe for
non-developers: a kit that is complete, a fallback agent for every role card,
a share page that works under GLOW's content security policy, and handouts
that pass GLOW's own audit.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app

REPO = Path(__file__).resolve().parents[2]
KIT = REPO / "docs" / "ahg-2026" / "kit"
SECTIONS = ("## Role", "## Task", "## Trusted guidance", "## Output format", "## Human review", "## Never")
COMMANDS = ("ready-check", "design-my-agent", "try-my-agent", "ground-my-agent", "run-the-office", "my-30-day-plan")


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


# ---------------------------------------------------------------------------
# The kit itself
# ---------------------------------------------------------------------------


def _agent_files(folder: str) -> list[Path]:
    return sorted((KIT / folder).glob("*/SKILL.md"))


def test_every_agent_in_the_kit_has_all_six_sections():
    files = [KIT / "my-agent" / "SKILL.md", *_agent_files("office-team"), *_agent_files("examples/agents")]
    assert len(files) == 1 + 8 + 6
    for path in files:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\nname: "), path
        assert re.search(r"^  author: .+$", text, re.M), path
        for section in SECTIONS:
            assert section in text, (path, section)


def test_every_role_card_has_two_ready_made_fallback_agents():
    names = {p.parent.name for p in _agent_files("examples/agents")}
    assert {"alternate-format-planner", "document-triage"} <= names
    assert {"faculty-coach", "course-page-coach"} <= names
    assert {"remediation-log-keeper", "vendor-report-reader"} <= names


def test_no_agent_ever_claims_compliance_or_asks_for_student_data():
    for path in [*_agent_files("office-team"), *_agent_files("examples/agents"), KIT / "my-agent" / "SKILL.md"]:
        text = path.read_text(encoding="utf-8")
        assert "Never say a document is \"compliant\"" in text, path
        assert "student names, records, accommodation details" in text, path


def test_every_block_has_its_copilot_command_and_step_card():
    for command in COMMANDS:
        prompt = KIT / ".github" / "prompts" / f"{command}.prompt.md"
        assert prompt.is_file(), command
        assert prompt.read_text(encoding="utf-8").startswith("---\ndescription: ")
    cards = sorted(p.name for p in (KIT / "step-cards").glob("*.md"))
    assert len(cards) == 8, "setup plus seven blocks"
    for card in cards:
        assert (KIT / "step-cards" / card.replace(".md", ".docx")).is_file(), card


def test_every_step_card_has_a_way_back_in_and_a_win():
    for card in sorted((KIT / "step-cards").glob("[1-7]-*.md")):
        text = card.read_text(encoding="utf-8")
        for heading in ("## Where we are", "## What you will have at the end", "## Steps",
                        "## You are on track if", "## If you are stuck", "## Your win"):
            assert heading in text, (card.name, heading)


def test_every_course_file_has_its_evidence():
    course = KIT / "sample-course"
    for item in ("psy101-syllabus", "psy101-week3-lecture", "psy101-gradebook",
                 "psy101-reading-forgetting-scanned", "psy101-lab1-stroop",
                 "psy101-announcement", "psy101-week3-captions"):
        evidence = course / "evidence" / f"{item}.txt"
        assert evidence.is_file(), item
        assert evidence.read_text(encoding="utf-8").startswith("Evidence: "), item


def test_the_answer_key_is_not_in_the_kit():
    """Participants should find the barriers, not read them."""
    assert not list(KIT.rglob("answer-key*"))


def test_the_profile_installs_what_the_day_needs():
    profile = json.loads((KIT / "ahg-2026.code-profile").read_text(encoding="utf-8"))
    extensions = {e["identifier"]["id"] for e in json.loads(profile["extensions"])}
    assert {"github.copilot-chat", "github.vscode-pull-request-github", "github.remotehub",
            "deque-systems.vscode-axe-linter"} <= extensions
    settings = json.loads(json.loads(profile["settings"])["settings"])
    assert settings["editor.accessibilitySupport"] == "on"
    assert settings["editor.fontSize"] >= 18


def test_the_step_cards_pass_glow_s_own_audit(tmp_path):
    from acb_large_print.auditor import audit_document

    for card in sorted((KIT / "step-cards").glob("*.docx")):
        result = audit_document(card)
        serious = [f for f in result.findings
                   if str(f.severity).split(".")[-1] in {"CRITICAL", "HIGH", "MEDIUM"}]
        assert not serious, (card.name, [(f.rule_id, f.message) for f in serious])


# ---------------------------------------------------------------------------
# The GLOW pages
# ---------------------------------------------------------------------------


def test_the_setup_page_has_every_step_and_link(client):
    resp = client.get("/workshop/ahg-2026")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    for needle in ("/workshop/ahg-2026/kit.zip", "/workshop/ahg-2026/ahg-2026.code-profile",
                   "/workshop/ahg-2026/share", "Profiles: Import Profile", "Mountain Time",
                   "support@community-access.org", "Never paste anything private"):
        assert needle in body, needle


def test_the_kit_downloads_as_one_zip_without_the_answer_key(client):
    resp = client.get("/workshop/ahg-2026/kit.zip")
    assert resp.status_code == 200
    assert resp.mimetype == "application/zip"
    names = zipfile.ZipFile(io.BytesIO(resp.data)).namelist()
    for needle in ("ahg-2026-agent-kit/README.md", "ahg-2026-agent-kit/my-agent/SKILL.md",
                   "ahg-2026-agent-kit/.github/prompts/design-my-agent.prompt.md",
                   "ahg-2026-agent-kit/sample-course/psy101-syllabus.docx"):
        assert needle in names, needle
    assert not any("answer-key" in n for n in names)


def test_the_profile_is_served_for_import(client):
    resp = client.get("/workshop/ahg-2026/ahg-2026.code-profile")
    assert resp.status_code == 200
    assert json.loads(resp.data)["name"] == "AHG 2026 Accessibility Agents"


def test_the_share_page_works_under_the_content_security_policy(client):
    resp = client.get("/workshop/ahg-2026/share")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    nonce = re.search(r"'nonce-([^']+)'", resp.headers["Content-Security-Policy"]).group(1)
    assert f'<script nonce="{nonce}">' in body
    assert f'<style nonce="{nonce}">' in body
    assert "community/ahg-2026/" in body
    assert 'for="agent-file"' in body and 'for="agent-name"' in body


def test_step_cards_download_and_nothing_else_does(client):
    ok = client.get("/workshop/ahg-2026/step-cards/2-design-your-agent.docx")
    assert ok.status_code == 200
    assert client.get("/workshop/ahg-2026/step-cards/..%2F..%2Fanswer-key.md").status_code == 404
    assert client.get("/workshop/ahg-2026/step-cards/nope.docx").status_code == 404


def test_vs_code_can_import_the_profile_without_a_consent_cookie():
    """VS Code's Import Profile fetches the URL with no cookie at all."""
    from types import SimpleNamespace

    from acb_large_print_web.routes.consent import consent_required

    for path in ("/workshop/ahg-2026/ahg-2026.code-profile", "/workshop/ahg-2026/kit.zip"):
        req = SimpleNamespace(path=path, cookies={}, headers={})
        assert consent_required(req) is False, path
    page = SimpleNamespace(path="/workshop/ahg-2026/share", cookies={}, headers={})
    assert consent_required(page) is True


def test_no_text_file_in_the_workshop_carries_control_characters():
    """Shell escaping has turned backslashes into control bytes here before."""
    ahg = REPO / "docs" / "ahg-2026"
    bad = []
    for path in [*ahg.rglob("*.md"), *ahg.rglob("*.html"), *ahg.rglob("*.txt"), *ahg.rglob("*.json")]:
        text = path.read_text(encoding="utf-8")
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", text):
            bad.append(str(path.relative_to(REPO)))
    assert not bad, bad


def test_the_share_page_can_be_rehearsed_against_a_test_fork(client):
    body = client.get("/workshop/ahg-2026/share").get_data(as_text=True)
    assert 'params.get("repo")' in body
    assert "Community-Access/accessibility-agents/new/main" in body, "the real target stays the default"


def test_the_coordinator_can_run_the_whole_room_s_agents():
    text = (KIT / ".github" / "agents" / "office-coordinator.agent.md").read_text(encoding="utf-8")
    assert "room/<name>/SKILL.md" in text


def test_every_front_matter_block_is_valid_yaml():
    """An unquoted colon once broke six agent headers; VS Code and Vale both read them."""
    import yaml

    broken = []
    for path in [*REPO.joinpath("docs", "ahg-2026").rglob("*.md"), REPO / "ahg.md"]:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        if not text.startswith("---\n"):
            continue
        end = text.index("\n---\n", 4)
        try:
            yaml.safe_load(text[4:end])
        except yaml.YAMLError as exc:
            broken.append((str(path.relative_to(REPO)), str(exc).splitlines()[0]))
    assert not broken, broken
