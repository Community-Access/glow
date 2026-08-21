"""Phase 3: the live room, peer borrowing, and the badge collection.

The gallery and the facilitator dashboard were filing cabinets. These tests
cover turning them into a room -- and the constraint that makes it safe, which
is that a live-updating page must never move a screen reader user's focus or
change content underneath them.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
from acb_large_print_web.routes.workshop import ACTIVITY_ORDER
from acb_large_print_web.workshop_store import ensure_session

CODE = "livedemo"

CHAMPION = {
    "workflow_name": "Faculty email accessibility coach",
    "partner_group": "Faculty who send course announcements",
    "responsibility": "Write their own accessible announcements",
    "ai_support": "Check the draft for structure and plain language",
    "final_output": "A revised draft and a short explanation",
    "human_safeguard": "A person reads it aloud before it is sent",
}


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setenv("GLOW_WORKSHOP_FACILITATOR_KEY", "key")
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    with application.app_context():
        ensure_session(CODE, title="GLOW Workshop Demo", event_name="AHG")
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _participant(app: Flask, name: str):
    client = app.test_client()
    client.set_cookie("glow_consent_v1", "1", domain="localhost")
    client.post("/workshop/", data={"action": "join", "session_code": CODE, "display_name": name})
    return client


def _save_champion(client, *, anonymous: bool = False) -> None:
    data = dict(CHAMPION)
    if anonymous:
        data["anonymity_mode"] = "on"
    client.post(f"/workshop/session/{CODE}/activity/champion_studio", data=data)


# ---------------------------------------------------------------------------
# The pulse
# ---------------------------------------------------------------------------


def test_the_pulse_reports_counts_and_nothing_else(app: Flask, client):
    rowan = _participant(app, "Rowan")
    _save_champion(rowan)

    payload = client.get(f"/workshop/session/{CODE}/pulse.json").get_json()

    assert payload["total"] == 1
    assert payload["participants"] == 1
    assert payload["by_activity"]["champion_studio"] == 1
    # Nothing that would need redacting can appear in a stream anyone can read.
    body = client.get(f"/workshop/session/{CODE}/pulse.json").get_data(as_text=True)
    assert "Rowan" not in body
    assert "Faculty" not in body


def test_the_pulse_covers_every_activity_in_the_agenda(client):
    payload = client.get(f"/workshop/session/{CODE}/pulse.json").get_json()

    assert sorted(payload["by_activity"]) == sorted(ACTIVITY_ORDER)


def test_the_pulse_is_scoped_to_one_session(app: Flask, client):
    with app.app_context():
        ensure_session("othersession", title="Elsewhere")
    rowan = _participant(app, "Rowan")
    _save_champion(rowan)

    other = client.get("/workshop/session/othersession/pulse.json").get_json()

    assert other["total"] == 0


def test_an_unknown_session_has_no_pulse(client):
    assert client.get("/workshop/session/nosuchthing/pulse.json").status_code == 404


# ---------------------------------------------------------------------------
# The gallery announces politely
# ---------------------------------------------------------------------------


def test_the_gallery_announces_through_a_status_region_with_an_opt_in_control(app: Flask):
    rowan = _participant(app, "Rowan")
    _save_champion(rowan)

    page = rowan.get(f"/workshop/session/{CODE}/gallery").get_data(as_text=True)

    assert 'id="workshop-live-status"' in page
    assert 'role="status"' in page
    # The reader chooses when new work appears; it is never inserted for them.
    assert 'id="workshop-live-reveal"' in page
    assert "Show new submissions" in page
    assert "workshop-live.js" in page


def test_the_gallery_tells_the_client_where_to_listen(app: Flask):
    rowan = _participant(app, "Rowan")

    page = rowan.get(f"/workshop/session/{CODE}/gallery").get_data(as_text=True)

    assert f"/workshop/session/{CODE}/pulse.stream" in page
    assert f"/workshop/session/{CODE}/pulse.json" in page


def test_the_facilitator_room_pulse_is_projectable(app: Flask, client):
    rowan = _participant(app, "Rowan")
    _save_champion(rowan)
    client.post(f"/workshop/session/{CODE}/facilitator/unlock", data={"facilitator_key": "key"})

    page = client.get(f"/workshop/session/{CODE}/facilitator").get_data(as_text=True)

    assert "Room pulse" in page
    assert 'data-activity-count="champion_studio"' in page
    assert "<progress" in page
    # Counts, never anyone's work.
    assert "Faculty who send course announcements" not in page


# ---------------------------------------------------------------------------
# "Steal this"
# ---------------------------------------------------------------------------


def test_a_shared_workflow_can_be_used_as_a_starting_point(app: Flask):
    rowan = _participant(app, "Rowan")
    _save_champion(rowan)
    sam = _participant(app, "Sam")

    gallery = sam.get(f"/workshop/session/{CODE}/gallery").get_data(as_text=True)
    assert "Start from this workflow" in gallery

    page = sam.get(
        f"/workshop/session/{CODE}/activity/champion_studio?adopt=1"
    ).get_data(as_text=True)

    assert "Faculty who send course announcements" in page
    assert "Started from the workflow shared by Rowan" in page
    assert "Adapted from the workflow shared by Rowan" in page


def test_borrowing_never_overwrites_your_own_saved_work(app: Flask):
    rowan = _participant(app, "Rowan")
    _save_champion(rowan)

    sam = _participant(app, "Sam")
    sam.post(
        f"/workshop/session/{CODE}/activity/champion_studio",
        data={
            "workflow_name": "My own coaching loop",
            "partner_group": "Department admins",
            "responsibility": "Own their own documents",
            "ai_support": "Draft a checklist",
            "final_output": "A checklist",
            "human_safeguard": "I test with a keyboard",
        },
    )

    page = sam.get(
        f"/workshop/session/{CODE}/activity/champion_studio?adopt=1"
    ).get_data(as_text=True)

    # Their own answers are still in the form...
    assert "My own coaching loop" in page
    assert "Department admins" in page
    # ...and the borrowed workflow is shown beside it instead.
    assert "Workflow shared by Rowan" in page
    assert "Your own saved answers are untouched" in page


def test_borrowing_respects_a_submitters_anonymity(app: Flask):
    rowan = _participant(app, "Rowan")
    _save_champion(rowan, anonymous=True)
    sam = _participant(app, "Sam")

    page = sam.get(
        f"/workshop/session/{CODE}/activity/champion_studio?adopt=1"
    ).get_data(as_text=True)

    assert "an anonymous participant" in page
    assert "Rowan" not in page


def test_only_finished_shared_workflows_can_be_borrowed(app: Flask):
    rowan = _participant(app, "Rowan")
    rowan.post(
        f"/workshop/session/{CODE}/activity/champion_studio",
        data={"workflow_name": "Half an idea", "submit_action": "draft"},
    )
    sam = _participant(app, "Sam")

    page = sam.get(
        f"/workshop/session/{CODE}/activity/champion_studio?adopt=1"
    ).get_data(as_text=True)

    assert "Half an idea" not in page


def test_a_nonsense_adopt_id_is_ignored(app: Flask):
    sam = _participant(app, "Sam")

    resp = sam.get(f"/workshop/session/{CODE}/activity/champion_studio?adopt=notanumber")

    assert resp.status_code == 200
    assert "Started from the workflow" not in resp.get_data(as_text=True)


def test_work_from_another_activity_cannot_be_adopted(app: Flask):
    rowan = _participant(app, "Rowan")
    rowan.post(
        f"/workshop/session/{CODE}/activity/journey_check_in",
        data={
            "work_type": "Library remediation",
            "partner_blockers": "Scanned PDFs",
            "champion_shift": "Departments fix their own headings",
        },
    )
    sam = _participant(app, "Sam")

    page = sam.get(
        f"/workshop/session/{CODE}/activity/champion_studio?adopt=1"
    ).get_data(as_text=True)

    assert "Library remediation" not in page


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------


def test_badges_have_somewhere_to_live(app: Flask):
    rowan = _participant(app, "Rowan")
    _save_champion(rowan)

    page = rowan.get(f"/workshop/session/{CODE}/badges").get_data(as_text=True)

    assert "Champion Designer" in page
    assert f"1 of {len(ACTIVITY_ORDER)} badges earned" in page
    assert "Not yet earned" in page


def test_a_draft_does_not_earn_a_badge(app: Flask):
    rowan = _participant(app, "Rowan")
    rowan.post(
        f"/workshop/session/{CODE}/activity/champion_studio",
        data={"workflow_name": "Half an idea", "submit_action": "draft"},
    )

    page = rowan.get(f"/workshop/session/{CODE}/badges").get_data(as_text=True)

    assert f"0 of {len(ACTIVITY_ORDER)} badges earned" in page


def test_the_optional_lab_badge_is_marked_as_not_counted(app: Flask):
    rowan = _participant(app, "Rowan")

    page = rowan.get(f"/workshop/session/{CODE}/badges").get_data(as_text=True)

    assert "Agent Runner" in page
    assert "optional, not counted" in page


def test_badges_need_a_participant(client):
    assert client.get(f"/workshop/session/{CODE}/badges").status_code == 404


def test_every_workshop_page_can_reach_the_badges(app: Flask):
    rowan = _participant(app, "Rowan")

    page = rowan.get(f"/workshop/session/{CODE}/me").get_data(as_text=True)

    assert f"/workshop/session/{CODE}/badges" in page
