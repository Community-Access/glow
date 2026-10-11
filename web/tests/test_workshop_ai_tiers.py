"""The two paths: GLOW in a browser, and your own assistant if you want one.

The house AI is gone and so is every mention of plumbing. What remains is the
prompt a participant pastes into whatever assistant they already have, and the
agent package they take home. Both must be usable by someone who has never
heard of MCP, a CLI, or a plugin -- and the tests below are what hold that
line, because plumbing creeps back one helpful sentence at a time.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
from acb_large_print_web.routes.workshop import (
    ACTIVITY_ORDER,
    AI_ASSISTED_ACTIVITIES,
    OPTIONAL_ACTIVITY_ORDER,
)
from acb_large_print_web.workshop_skills import (
    build_activity_prompt,
    build_skill_markdown,
    build_skill_zip_bytes,
)
from acb_large_print_web.workshop_store import ensure_session

CODE = "tierdemo"

VALUES = {
    "workflow_name": "Faculty email accessibility coach",
    "partner_group": "Faculty who send course announcements",
    "responsibility": "Write their own accessible announcements",
    "ai_support": "Check the draft for structure and plain language",
    "final_output": "A revised draft and a short explanation",
    "human_safeguard": "A person reads it aloud before it is sent",
}


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    with application.app_context():
        ensure_session(CODE, title="GLOW Workshop Demo", event_name="AHG")
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _join(client) -> None:
    client.post("/workshop/", data={"action": "join", "session_code": CODE, "display_name": "Rowan"})


# ---------------------------------------------------------------------------
# Tier 2: the prompt itself
# ---------------------------------------------------------------------------


def test_the_prompt_builds_on_the_participants_own_words():
    prompt = build_activity_prompt(
        activity_title="GLOW Lab 1",
        task="Rewrite a message so more people can read it.",
        answers=[("The message", "A closure notice for the library")],
        human_review="Read it aloud before sending.",
    )

    assert "A closure notice for the library" in prompt
    assert "Build on it; do not replace it" in prompt
    assert "Read it aloud before sending." in prompt


def test_the_prompt_always_carries_a_human_review_instruction():
    prompt = build_activity_prompt(activity_title="Lab", task="Do the thing.")

    assert "what you checked and what you did not check" in prompt
    assert "verify myself" in prompt


def test_an_empty_form_asks_questions_rather_than_inventing_answers():
    prompt = build_activity_prompt(activity_title="Lab", task="Do the thing.")

    assert "Ask me up to three questions" in prompt


def test_the_prompt_includes_the_chosen_scenario():
    prompt = build_activity_prompt(
        activity_title="Lab",
        task="Do the thing.",
        scenario_title="Nine hundred legacy PDFs",
        scenario_brief=["Most are scans.", "There is no budget."],
    )

    assert "Nine hundred legacy PDFs" in prompt
    assert "Most are scans." in prompt


def test_the_prompt_never_mentions_installing_anything():
    prompt = build_activity_prompt(
        activity_title="Lab", task="Do the thing.", answers=[("A", "B")]
    )

    lowered = prompt.lower()
    for word in ("install", "api key", "terminal", "vs code", "mcp"):
        assert word not in lowered


# ---------------------------------------------------------------------------
# Tier 2: on the page
# ---------------------------------------------------------------------------


def test_every_ai_assisted_activity_carries_a_copy_button(client, app: Flask):
    _join(client)

    for activity_key in AI_ASSISTED_ACTIVITIES:
        page = client.get(f"/workshop/session/{CODE}/activity/{activity_key}").get_data(as_text=True)
        assert 'data-copy-target="activity-copy-prompt"' in page, activity_key
        assert "Use the assistant you already have" in page, activity_key


def test_activities_where_ai_does_not_belong_have_no_prompt(client, app: Flask):
    _join(client)

    page = client.get(f"/workshop/session/{CODE}/activity/journey_check_in").get_data(as_text=True)

    assert "activity-copy-prompt" not in page


def test_saved_answers_reach_the_prompt(client, app: Flask):
    _join(client)
    client.post(
        f"/workshop/session/{CODE}/activity/agent_formula",
        data={
            "role": "A patient accessibility coach for faculty",
            "task": "Check announcements before they go out",
            "trusted_guidance": "Our campus style guide and WCAG 2.2 AA",
            "output_format": "A revised draft plus two teaching notes",
            "human_review": "A person reads it aloud before sending",
        },
    )

    page = client.get(f"/workshop/session/{CODE}/activity/agent_formula").get_data(as_text=True)

    assert "A patient accessibility coach for faculty" in page
    assert "A person reads it aloud before sending" in page


def test_the_copy_button_is_an_accelerator_not_the_only_route(client, app: Flask):
    """The text stays on the page and stays selectable, so a clipboard
    failure or a locked-down browser is an inconvenience, not a dead end."""
    _join(client)

    page = client.get(f"/workshop/session/{CODE}/activity/champion_studio").get_data(as_text=True)

    assert "<textarea" in page
    assert "select the text and copy it yourself" in page
    assert 'role="status"' in page


# ---------------------------------------------------------------------------
# The agent package: no plumbing, anywhere
# ---------------------------------------------------------------------------

# Words a participant should never have to meet. Locked as L5 and L12 in
# docs/ahg-2026/plan.md: the audience is disability services staff and faculty,
# not developers, and every piece of plumbing on a page is a slice of the room
# deciding this is not for them.
PLUMBING = (
    "mcp",
    "model context protocol",
    "endpoint",
    "localhost",
    "npm",
    "cli",
    "command line",
    "terminal",
    "api key",
    "install",
    "vs code",
    "copilot",
    "gemini",
    "plugin",
    "extension",
)


def _mentions(text: str, word: str) -> bool:
    """Whole-word match. Without the boundaries, "cli" matches "click"."""
    return re.search(r"\b" + re.escape(word) + r"\b", text) is not None


def test_the_generated_package_names_no_plumbing():
    skill = build_skill_markdown(VALUES).lower()

    for word in PLUMBING:
        assert not _mentions(skill, word), f"generated agent package mentions {word!r}"


def test_the_package_is_complete_without_a_tool_layer():
    skill = build_skill_markdown(VALUES)

    assert "## Verification truth" in skill
    assert "## Workflow" in skill
    assert "## Do not activate for" in skill


def test_the_zip_carries_no_plumbing_either(app: Flask):
    _filename, payload = build_skill_zip_bytes(VALUES)

    import zipfile
    from io import BytesIO

    with zipfile.ZipFile(BytesIO(payload)) as zf:
        body = " ".join(
            zf.read(name).decode("utf-8", "ignore") for name in zf.namelist()
        ).lower()

    for word in PLUMBING:
        assert not _mentions(body, word), f"agent package zip mentions {word!r}"


# ---------------------------------------------------------------------------
# Tier 3: the optional lab
# ---------------------------------------------------------------------------


def test_the_optional_lab_is_outside_the_agenda():
    for key in OPTIONAL_ACTIVITY_ORDER:
        assert key not in ACTIVITY_ORDER


def test_the_optional_lab_says_it_does_not_count(client, app: Flask):
    _join(client)

    page = client.get(f"/workshop/session/{CODE}/activity/lab_run_your_agent").get_data(as_text=True)

    assert "optional" in page.lower()
    assert "does not count" in page
    assert "missing nothing the workshop" in page


def test_the_optional_lab_does_not_move_the_progress_bar(client, app: Flask):
    _join(client)
    before = client.get(f"/workshop/session/{CODE}/activity/journey_check_in").get_data(as_text=True)

    client.post(
        f"/workshop/session/{CODE}/activity/lab_run_your_agent",
        data={
            "where_you_ran_it": "Copilot in my institution's tenant",
            "what_you_gave_it": "A real announcement from last week",
            "what_it_got_right": "It found the vague link text",
            "what_it_got_wrong": "It claimed the contrast was fine without checking",
            "design_change": "Say explicitly that it cannot judge contrast",
            "review_step": "I check contrast myself with the checker",
        },
    )
    after = client.get(f"/workshop/session/{CODE}/activity/journey_check_in").get_data(as_text=True)

    marker = f"of {len(ACTIVITY_ORDER)} activities saved"
    assert marker in before
    assert marker in after
    assert f"0 of {len(ACTIVITY_ORDER)}" in after


def test_the_champion_skill_page_offers_the_optional_lab(client, app: Flask):
    _join(client)
    client.post(
        f"/workshop/session/{CODE}/activity/champion_studio",
        data={
            "workflow_name": "Faculty email accessibility coach",
            "partner_group": "Faculty",
            "responsibility": "Write their own",
            "ai_support": "Check structure",
            "final_output": "A revised draft",
            "human_safeguard": "Read it aloud",
        },
    )

    page = client.get(f"/workshop/session/{CODE}/champion-skill").get_data(as_text=True)

    assert "lab_run_your_agent" in page
    assert "take it or leave it" in page
