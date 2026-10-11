"""Captured AI output, judged rather than generated.

The workshop provides no AI and a participant's own assistant is optional and
capped. So the "judge the machine" lesson is carried by specimens: output
written to be argued with, shown to everyone, and impossible to fail at 1:40
in the afternoon.

The test that matters most here is the provenance one. A specimen claiming to
have come from a named assistant on a named date must actually have done so -
teaching accessibility professionals to judge AI output while quietly
fabricating the output would be a poor way to spend their trust.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web import workshop_specimens as specimens
from acb_large_print_web.app import create_app
from acb_large_print_web.workshop_store import ensure_session

CODE = "specimendemo"


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


# ---------------------------------------------------------------------------
# Honesty
# ---------------------------------------------------------------------------


def test_illustrative_specimens_are_labelled_as_such():
    """Until someone captures real output, every specimen says it is written."""
    if specimens.has_real_captures():
        pytest.skip("real captures exist; provenance is per-specimen from here")

    for specimen_set in specimens.SPECIMEN_SETS:
        for specimen in specimen_set.specimens:
            assert specimen.provenance == specimens.ILLUSTRATIVE
            assert "not captured" in specimen.provenance_label


def test_the_page_tells_the_room_the_specimens_were_written(client):
    body = client.get(f"/workshop/session/{CODE}/activity/lab_alt_text_decision").get_data(as_text=True)
    assert "not captured from a live assistant" in body


# ---------------------------------------------------------------------------
# The exercise
# ---------------------------------------------------------------------------


def test_every_set_offers_a_real_disagreement():
    """A set where everything is wrong teaches nothing but cynicism."""
    for specimen_set in specimens.SPECIMEN_SETS:
        verdicts = {s.verdict for s in specimen_set.specimens}
        assert len(verdicts) > 1, f"{specimen_set.id} has only one verdict"
        assert len(specimen_set.specimens) >= 3


def test_every_specimen_explains_itself():
    for specimen_set in specimens.SPECIMEN_SETS:
        for specimen in specimen_set.specimens:
            assert specimen.why, f"{specimen.id} has no reasoning"
            assert specimen.verdict in specimens.VERDICT_LABELS


def test_alt_text_sets_carry_context_but_never_an_image():
    """Purpose lives in the words around the image, not in the pixels."""
    sets = specimens.specimen_sets_for("lab_alt_text_decision")
    assert sets
    for specimen_set in sets:
        context = specimen_set.context
        assert context is not None
        assert context.document and context.audience
        assert context.placement and context.surrounding_text
        assert context.visible


def test_the_decorative_case_is_taught():
    """An empty alt is a decision, and many people have never been told."""
    decorative = specimens.get_specimen_set("decorative-divider")
    assert decorative is not None
    good = [s for s in decorative.specimens if s.verdict == specimens.GOOD]
    assert good and 'alt=""' in good[0].text


def test_every_lab_2_scenario_has_specimens_about_that_scenario():
    """A participant who picked the archive brief should judge the archive.

    Selection used to key on the participant alone, so somebody could choose
    the campus-map scenario and then be asked about a board-report chart. The
    lab still worked - judging is the skill - but the join was arbitrary.
    """
    from acb_large_print_web.workshop_scenarios import scenarios_for

    for scenario in scenarios_for("lab_alt_text_decision"):
        matched = specimens.set_for_scenario("lab_alt_text_decision", scenario.id)
        assert matched is not None, f"no specimens for scenario {scenario.id}"
        assert matched.scenario_id == scenario.id


def test_a_chosen_scenario_beats_the_deterministic_pick():
    chosen = specimens.pick_specimen_set(
        "lab_alt_text_decision", "any-participant", scenario_id="archive-photograph"
    )
    assert chosen is not None and chosen.id == "archive-photograph"


def test_no_scenario_still_gives_a_set():
    """Choosing a scenario is optional, so the lab must work without one."""
    fallback = specimens.pick_specimen_set("lab_alt_text_decision", "someone")
    assert fallback is not None


def test_selection_is_deterministic_per_participant():
    """Reproducible, so a facilitator can walk someone back through theirs."""
    first = specimens.pick_specimen_set("lab_alt_text_decision", "participant-a")
    again = specimens.pick_specimen_set("lab_alt_text_decision", "participant-a")
    assert first is not None and first.id == again.id


def test_an_activity_with_no_specimens_gets_none():
    assert specimens.pick_specimen_set("journey_check_in", "anyone") is None


# ---------------------------------------------------------------------------
# On the page
# ---------------------------------------------------------------------------


def test_the_verdict_is_behind_a_disclosure(client):
    """Handing over the answer with the output turns judgment into reading."""
    body = client.get(f"/workshop/session/{CODE}/activity/lab_alt_text_decision").get_data(as_text=True)
    assert "<details>" in body
    assert "What we think, and why" in body


def test_the_page_never_asks_anyone_to_upload(client):
    body = client.get(f"/workshop/session/{CODE}/activity/lab_alt_text_decision").get_data(as_text=True)
    flat = " ".join(body.split())
    assert "Do not upload anything" in flat
    assert "free accounts limit uploads" in flat


def test_activities_without_specimens_show_no_panel(client):
    body = client.get(f"/workshop/session/{CODE}/activity/journey_check_in").get_data(as_text=True)
    assert "workshop-specimen" not in body
