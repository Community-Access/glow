"""The lab scenario bank, and how it reaches a participant.

Eleven activities with one brief each was thin for a seven-hour day. These
tests cover both halves of the fix: the data being coherent, and a
participant being able to choose, be given, or ignore a scenario without
losing work.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask
from markupsafe import escape

from acb_large_print_web.app import create_app
from acb_large_print_web.routes.workshop import (
    WORKSHOP_ACTION_TOKENS,
    WORKSHOP_SAMPLE_FILES,
)
from acb_large_print_web.workshop_scenarios import (
    SCENARIOS,
    get_scenario,
    pick_scenario,
    scenarios_for,
)
from acb_large_print_web.workshop_store import ensure_session

LAB = "lab_remediation_plan"


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _join(client, app: Flask, code: str = "scenariodemo") -> str:
    with app.app_context():
        ensure_session(code, title="GLOW Workshop Demo", event_name="AHG")
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Rowan"})
    return code


# ---------------------------------------------------------------------------
# The bank itself
# ---------------------------------------------------------------------------


def test_every_lab_offers_several_distinct_sectors():
    """A table of instructional designers and a table of PDF specialists
    should not be handed the same brief."""
    for activity_key, bank in SCENARIOS.items():
        assert len(bank) >= 3, activity_key
        sectors = {scenario.sector for scenario in bank}
        assert len(sectors) == len(bank), f"{activity_key} repeats a sector"


def test_scenario_ids_are_unique_within_an_activity():
    for activity_key, bank in SCENARIOS.items():
        ids = [scenario.id for scenario in bank]
        assert len(set(ids)) == len(ids), activity_key


def test_scenarios_only_reference_real_tools_and_real_samples():
    for bank in SCENARIOS.values():
        for scenario in bank:
            for token in scenario.tools:
                assert token in WORKSHOP_ACTION_TOKENS, token
            if scenario.sample_slug:
                assert scenario.sample_slug in WORKSHOP_SAMPLE_FILES, scenario.sample_slug


def test_every_scenario_carries_a_brief_and_something_to_notice():
    for bank in SCENARIOS.values():
        for scenario in bank:
            assert len(scenario.brief) >= 2, scenario.id
            assert scenario.what_to_notice, scenario.id


def test_surprise_me_is_stable_for_one_person_and_spreads_across_a_room():
    first = pick_scenario(LAB, "participant-key-a")
    assert first is not None
    assert pick_scenario(LAB, "participant-key-a").id == first.id

    picks = {pick_scenario(LAB, f"participant-{n}").id for n in range(40)}
    assert len(picks) > 1


def test_unknown_ids_and_activities_return_nothing():
    assert get_scenario(LAB, "no-such-scenario") is None
    assert get_scenario("journey_check_in", "faculty-handout") is None
    assert scenarios_for("journey_check_in") == ()
    assert pick_scenario("journey_check_in", "seed") is None


# ---------------------------------------------------------------------------
# Reaching a participant
# ---------------------------------------------------------------------------


def test_a_lab_lists_its_scenarios_and_says_they_are_optional(client, app: Flask):
    code = _join(client, app)

    page = client.get(f"/workshop/session/{code}/activity/{LAB}").get_data(as_text=True)

    for scenario in scenarios_for(LAB):
        # Titles carry apostrophes, which Jinja escapes on the way out.
        assert str(escape(scenario.title)) in page
    assert "use a real document of" in page
    assert "Surprise me" in page


def test_choosing_a_scenario_shows_its_brief_and_starting_document(client, app: Flask):
    code = _join(client, app)

    page = client.get(
        f"/workshop/session/{code}/activity/{LAB}?scenario=faculty-handout"
    ).get_data(as_text=True)

    assert "Thirty-five pages, three weeks before term" in page
    assert "scanned appendix" in page
    assert f"/workshop/session/{code}/samples/glow-test-docx" in page
    # The tools named by the scenario are one click away.
    assert "/audit/" in page


def test_an_unknown_scenario_id_falls_back_to_the_menu(client, app: Flask):
    code = _join(client, app)

    resp = client.get(f"/workshop/session/{code}/activity/{LAB}?scenario=not-real")

    assert resp.status_code == 200
    assert "Surprise me" in resp.get_data(as_text=True)


def test_activities_without_a_bank_show_no_scenario_section(client, app: Flask):
    code = _join(client, app)

    page = client.get(f"/workshop/session/{code}/activity/journey_check_in").get_data(as_text=True)

    assert 'id="scenario"' not in page


def test_the_chosen_scenario_is_recorded_and_comes_back(client, app: Flask):
    code = _join(client, app)

    client.post(
        f"/workshop/session/{code}/activity/{LAB}",
        data={
            "scenario_id": "uncaptioned-course",
            "content_track": "Forty recorded lectures for an online course.",
            "likely_barriers": "No captions, and automatic ones miss the graded vocabulary.",
            "priority_fixes": "Caption the assessed lectures first.",
            "owner_questions": "Which lectures do the assessments draw on?",
            "human_inspection": "A person checks the technical terms in every caption file.",
            "coaching_message": "Show the recording checklist before next term.",
        },
    )

    mine = client.get(f"/workshop/session/{code}/me").get_data(as_text=True)
    assert "Forty videos, no captions" in mine

    # Reopening the activity restores the brief, not just the answers.
    again = client.get(f"/workshop/session/{code}/activity/{LAB}").get_data(as_text=True)
    assert "Forty videos, no captions, one course shell" in again


def test_a_forged_scenario_id_is_dropped_rather_than_stored(client, app: Flask):
    code = _join(client, app)

    client.post(
        f"/workshop/session/{code}/activity/{LAB}",
        data={
            "scenario_id": "<script>alert(1)</script>",
            "content_track": "Forty recorded lectures for an online course.",
            "likely_barriers": "No captions, and automatic ones miss the graded vocabulary.",
            "priority_fixes": "Caption the assessed lectures first.",
            "owner_questions": "Which lectures do the assessments draw on?",
            "human_inspection": "A person checks the technical terms in every caption file.",
            "coaching_message": "Show the recording checklist before next term.",
        },
    )

    mine = client.get(f"/workshop/session/{code}/me").get_data(as_text=True)
    assert "Scenario:" not in mine
    assert "alert(1)" not in mine


def test_surprise_me_hands_over_a_real_brief(client, app: Flask):
    code = _join(client, app)

    page = client.get(
        f"/workshop/session/{code}/activity/{LAB}?scenario=surprise"
    ).get_data(as_text=True)

    assert "What to notice" in page
    assert any(str(escape(scenario.title)) in page for scenario in scenarios_for(LAB))
