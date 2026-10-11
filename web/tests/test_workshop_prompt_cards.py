"""Ready-made agents, in a form a non-developer can use.

The workshop is named after the Accessibility Agents project, and until these
cards existed that name did not cash: participants installed nothing and GLOW
used nothing from it. The cards are the honest version - guidance derived by
hand from those agent definitions, rewritten for people who write documents
rather than code.

The load-bearing test here is the plumbing one. These cards are the surface
most likely to leak developer language back into a room of disability
services staff, because they came from developer-facing source material.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web import workshop_prompt_cards as cards
from acb_large_print_web.app import create_app
from acb_large_print_web.routes.workshop import ACTIVITY_ORDER
from acb_large_print_web.workshop_store import ensure_session

CODE = "carddemo"

# Locked as L5 and L12 in docs/ahg-2026/plan.md.
PLUMBING = (
    "mcp",
    "model context protocol",
    "npm",
    "cli",
    "command line",
    "terminal",
    "api key",
    "vs code",
    "copilot",
    "gemini",
    "plugin",
    "repository",
    "openxml",
    "python-docx",
)


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    with application.app_context():
        ensure_session(CODE, title="Accessibility Agents in Action", event_name="AHG")
    return application


@pytest.fixture()
def client(app: Flask):
    client = app.test_client()
    client.post("/workshop/", data={"action": "join", "session_code": CODE, "display_name": "Rowan"})
    return client


def _mentions(text: str, word: str) -> bool:
    """Whole-word match. Without the boundaries, "cli" matches "click"."""
    return re.search(r"\b" + re.escape(word) + r"\b", text) is not None

def _card_text(card: cards.PromptCard) -> str:
    parts = [card.title, card.for_whom, card.role, card.task, card.output_format,
             card.human_review, card.prompt, *card.guidance, *card.glow_steps]
    return " ".join(parts).lower()


# ---------------------------------------------------------------------------
# No plumbing, anywhere
# ---------------------------------------------------------------------------


def test_no_card_mentions_plumbing():
    for card in cards.CARDS:
        text = _card_text(card)
        for word in PLUMBING:
            assert not _mentions(text, word), f"card {card.id!r} mentions {word!r}"


def test_no_card_asks_anyone_to_upload_to_an_assistant():
    """Free accounts cap uploads and do not cap text. See plan.md L12."""
    for card in cards.CARDS:
        prompt = card.prompt.lower()
        assert "upload" not in prompt, f"card {card.id!r} asks for an upload"


def test_no_card_needs_an_account_or_an_install():
    for card in cards.CARDS:
        text = _card_text(card)
        assert "sign in" not in text
        assert "install" not in text


# ---------------------------------------------------------------------------
# The five-part formula
# ---------------------------------------------------------------------------


def test_every_card_is_a_complete_formula():
    """The formula is the curriculum. A card missing a part teaches the gap."""
    for card in cards.CARDS:
        labels = [label for label, _ in card.formula]
        assert labels == ["Role", "Task", "Trusted guidance", "Output format", "Human review"]
        for label, value in card.formula:
            assert value.strip(), f"card {card.id!r} has an empty {label}"


def test_every_card_names_a_human_who_checks_something():
    """A review step that says 'someone should check' is not a review step."""
    for card in cards.CARDS:
        assert len(card.human_review) > 40, f"card {card.id!r} review gate is too thin"


def test_every_card_points_at_its_source():
    for card in cards.CARDS:
        assert card.source_agent, f"card {card.id!r} has no attribution"


def test_cards_attach_to_real_activities():
    for card in cards.CARDS:
        assert card.activity_key in ACTIVITY_ORDER


def test_the_labs_and_the_studio_all_have_at_least_one():
    for key in (
        "teach_vs_fix",
        "lab_accessible_communication",
        "lab_alt_text_decision",
        "lab_remediation_plan",
        "champion_studio",
    ):
        assert cards.cards_for(key), f"no card for {key}"


def test_glow_steps_never_require_an_account():
    for card in cards.CARDS:
        for step in card.glow_steps:
            lowered = step.lower()
            assert "log in" not in lowered and "sign up" not in lowered


# ---------------------------------------------------------------------------
# On the page
# ---------------------------------------------------------------------------


def test_the_formula_activity_shows_every_card_to_dissect(client):
    body = client.get(f"/workshop/session/{CODE}/activity/agent_formula").get_data(as_text=True)
    assert body.count('class="workshop-card"') == len(cards.CARDS)
    assert "Ready-made agents, to take apart" in body


def test_a_lab_shows_only_its_own_cards(client):
    body = client.get(f"/workshop/session/{CODE}/activity/lab_alt_text_decision").get_data(as_text=True)
    expected = len(cards.cards_for("lab_alt_text_decision"))
    assert body.count('class="workshop-card"') == expected
    assert expected >= 1


def test_the_prompt_is_selectable_and_labelled(client):
    """A read-only textarea, so it can be copied by keyboard and announced once."""
    body = client.get(f"/workshop/session/{CODE}/activity/agent_formula").get_data(as_text=True)
    assert "<textarea readonly" in body
    assert "ready to copy" in body


def test_the_page_says_a_card_works_without_an_assistant(client):
    body = client.get(f"/workshop/session/{CODE}/activity/agent_formula").get_data(as_text=True)
    flat = " ".join(body.split())
    assert "You do not need an assistant to use this card" in flat


def test_an_activity_with_no_cards_shows_no_panel(client):
    body = client.get(f"/workshop/session/{CODE}/activity/journey_check_in").get_data(as_text=True)
    assert "workshop-card" not in body
