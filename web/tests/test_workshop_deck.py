"""The projected deck, served with the room's own code in it.

The deck used to be an HTML file on a laptop with ``CODE`` typed into it by
hand before the session. That is one more thing to get wrong at 8:25 in a
room that is filling up, and it guaranteed the deck's agenda would drift from
the times the activity pages show.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web import workshop_agenda as agenda
from acb_large_print_web.app import create_app
from acb_large_print_web.workshop_store import ensure_session

CODE = "deckdemo"


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
    return app.test_client()


def test_the_deck_carries_this_session_code(client):
    body = client.get(f"/workshop/session/{CODE}/deck").get_data(as_text=True)
    assert f"/w/{CODE}/7" in body
    assert f"/w/{CODE}" in body
    assert "CODE" not in body.replace("code_label", "")


def test_the_deck_agenda_comes_from_the_agenda_module(client):
    body = client.get(f"/workshop/session/{CODE}/deck").get_data(as_text=True)
    for block in agenda.AGENDA:
        assert block.clock in body


def test_activity_lengths_on_the_deck_match_the_activity_pages(client):
    body = client.get(f"/workshop/session/{CODE}/deck").get_data(as_text=True)
    lab2 = agenda.block_for_activity("lab_alt_text_decision")
    assert f"{lab2.minutes} minutes - /w/{CODE}/7" in body


def test_break_slides_say_when_the_room_comes_back(client):
    body = client.get(f"/workshop/session/{CODE}/deck").get_data(as_text=True)
    breaks = agenda.blocks_of_kind(agenda.BREAK)
    for block in breaks:
        assert f"Back at {block.resume}" in body


def test_the_deck_downloads_as_one_self_contained_file(client):
    """The projector fallback, and the copy that opens without the network."""
    resp = client.get(f"/workshop/session/{CODE}/deck?download=1")
    assert resp.status_code == 200
    assert "attachment" in resp.headers["Content-Disposition"]
    body = resp.get_data(as_text=True)
    # Self-contained: no external scripts, styles or images.
    assert "<script src=" not in body
    assert "<link rel=\"stylesheet\"" not in body
    assert "http://" not in body


def test_the_deck_is_readable_as_one_linear_document(client):
    """The mode a screen reader user will actually use."""
    body = client.get(f"/workshop/session/{CODE}/deck").get_data(as_text=True)
    assert "Read as one page" in body
    assert 'role="status"' in body
    assert 'aria-live="polite"' in body
    # Every slide is a landmark-labelled section with a real heading.
    assert body.count('class="slide"') == body.count("<h2 id=")


def test_inline_blocks_carry_the_csp_nonce(client):
    """Served from the app, an inline style or script without a nonce is dead."""
    resp = client.get(f"/workshop/session/{CODE}/deck")
    body = resp.get_data(as_text=True)
    assert "<style nonce=" in body
    assert "<script nonce=" in body
    assert "<style>" not in body
    assert "<script>" not in body


def test_the_deck_reads_before_a_session_exists(client):
    body = client.get("/workshop/deck").get_data(as_text=True)
    assert "your-code" in body


def test_an_unknown_session_has_no_deck(client):
    assert client.get("/workshop/session/no-such-room/deck").status_code == 404
