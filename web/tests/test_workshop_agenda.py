"""The day described in one place, and the surfaces that read from it.

Before ``workshop_agenda`` the day existed in four places that disagreed:
the participant-facing agenda table, the suggested length on every activity
page, the exercise pack, and the facilitator's run of show. A participant
reading "45 minutes" while the facilitator gives them 35 concludes they are
behind, and a participant who believes they are behind stops asking for what
they need. These tests are what stops that happening again.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web import workshop_agenda as agenda
from acb_large_print_web.app import create_app
from acb_large_print_web.routes.workshop import (
    ACTIVITY_META,
    ACTIVITY_ORDER,
    EXERCISE_PACK,
    OPTIONAL_ACTIVITY_ORDER,
)
from acb_large_print_web.workshop_store import ensure_session

CODE = "agendademo"
FACILITATOR_KEY = "unlock-me"


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setenv("GLOW_WORKSHOP_FACILITATOR_KEY", FACILITATOR_KEY)
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    with application.app_context():
        ensure_session(CODE, title="Accessibility Agents in Action", event_name="AHG")
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _unlock(client) -> None:
    client.post(
        f"/workshop/session/{CODE}/facilitator/unlock",
        data={"facilitator_key": FACILITATOR_KEY},
    )


# ---------------------------------------------------------------------------
# The agenda itself
# ---------------------------------------------------------------------------


def test_the_agenda_is_contiguous_and_fills_the_day():
    assert agenda.validate() == []


def test_the_working_day_is_seven_hours_plus_lunch():
    assert agenda.working_minutes() == 420
    assert agenda.total_minutes() == 480


def test_every_passport_activity_has_exactly_one_block():
    keys = [b.activity_key for b in agenda.activity_blocks()]
    assert keys == [k for k in ACTIVITY_ORDER]


def test_the_optional_lab_is_not_in_the_agenda():
    """A door, not a corridor: it must not occupy the room's minutes."""
    keys = {b.activity_key for b in agenda.activity_blocks()}
    for optional in OPTIONAL_ACTIVITY_ORDER:
        assert optional not in keys


def test_breaks_and_lunch_are_real_minutes():
    rests = [b for b in agenda.AGENDA if b.kind in (agenda.BREAK, agenda.LUNCH)]
    assert len(rests) == 3
    assert sum(b.minutes for b in rests if b.kind == agenda.BREAK) == 25


def test_current_and_next_block_track_the_clock():
    ten_thirty = 10 * 60 + 30
    assert agenda.current_block(ten_thirty).activity_key == "ai_boundary_map"
    assert agenda.next_block(ten_thirty).activity_key == "agent_formula"
    assert agenda.current_block(6 * 60) is None


# ---------------------------------------------------------------------------
# Everything that reads from it
# ---------------------------------------------------------------------------


def test_activity_pages_show_the_agenda_length():
    for key in ACTIVITY_ORDER:
        block = agenda.block_for_activity(key)
        assert ACTIVITY_META[key]["time"] == f"{block.minutes} minutes"


def test_the_optional_lab_says_it_is_optional():
    assert ACTIVITY_META["lab_run_your_agent"]["time"] == agenda.OPTIONAL_LENGTH_LABEL


def test_the_exercise_pack_cannot_drift_from_the_activity_pages():
    for exercise in EXERCISE_PACK:
        meta = ACTIVITY_META[exercise["activity"]]
        assert exercise["name"] == meta["title"]
        assert exercise["time"] == meta["time"]


def test_the_home_page_agenda_names_lunch_and_the_breaks(client):
    body = client.get("/workshop/").get_data(as_text=True)
    assert "12:15-1:15" in body
    assert "Lunch" in body
    assert "8:30-8:50" in body


def test_the_facilitator_run_of_show_carries_clock_minutes(client, app: Flask):
    _unlock(client)
    body = client.get(f"/workshop/session/{CODE}/facilitator").get_data(as_text=True)
    assert "Run of show" in body
    # The marker the browser clock uses to find "now".
    assert 'data-start="510"' in body  # 8:30
    assert 'data-end="990"' in body    # 4:30
