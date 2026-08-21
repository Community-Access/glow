"""Phase 4: what people leave with, and what brings them back.

The take-home artifact, the email that delivers it, the commitment wall, and
the 30-day nudge. The workshop's theory of change is that people leave and
act; until now the only delivery vehicle was a Markdown transcript nobody
forwards to their director.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web import email as email_module
from acb_large_print_web.app import create_app
from acb_large_print_web.routes import workshop as workshop_routes
from acb_large_print_web.workshop_artifact import (
    Artifact,
    ArtifactSection,
    build_artifact_html,
    build_artifact_text,
)
from acb_large_print_web.workshop_store import (
    ensure_session,
    participants_due_for_nudge,
    record_nudge,
)

CODE = "artifactdemo"

CHAMPION = {
    "workflow_name": "Faculty email accessibility coach",
    "partner_group": "Faculty who send course announcements",
    "responsibility": "Write their own accessible announcements",
    "ai_support": "Check the draft for structure and plain language",
    "final_output": "A revised draft and a short explanation",
    "human_safeguard": "A person reads it aloud before it is sent",
}

PLAN = {
    "workflow_30": "Coach the chemistry department through one announcement",
    "partner_team_30": "Chemistry teaching staff",
    "safeguard_30": "Keyboard test every page before it goes out",
    "first_step_30": "Email the chair on Monday",
}


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    with application.app_context():
        ensure_session(CODE, title="GLOW Workshop Demo", event_name="Accessing Higher Ground")
    return application


@pytest.fixture()
def client(app: Flask):
    client = app.test_client()
    client.post("/workshop/", data={"action": "join", "session_code": CODE, "display_name": "Rowan"})
    return client


class _MailBox:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.succeed = True

    def __call__(self, to_email, **kwargs):
        self.sent.append({"to": to_email, **kwargs})
        return (self.succeed, "queued" if self.succeed else "failed")


@pytest.fixture()
def mailbox(monkeypatch: pytest.MonkeyPatch) -> _MailBox:
    box = _MailBox()
    monkeypatch.setattr(workshop_routes, "email_configured", lambda: True)
    monkeypatch.setattr(workshop_routes, "send_workshop_artifact_email", box)
    return box


def _do_the_workshop(client) -> None:
    client.post(f"/workshop/session/{CODE}/activity/champion_studio", data=CHAMPION)
    client.post(f"/workshop/session/{CODE}/activity/action_plan_30_day", data=PLAN)


# ---------------------------------------------------------------------------
# The document itself
# ---------------------------------------------------------------------------


def _sample_artifact() -> Artifact:
    return Artifact(
        participant_name="Rowan",
        session_code=CODE,
        event_name="Accessing Higher Ground",
        workflow_name="Faculty email accessibility coach",
        human_review="A person reads it aloud before it is sent",
        badges_earned=2,
        badges_total=11,
        sections=(
            ArtifactSection(heading="The workflow", items=(("Who this helps", "Faculty"),)),
        ),
        generated_on="05 November 2026",
    )


def test_the_artifact_is_a_complete_standalone_document():
    html = build_artifact_html(_sample_artifact())

    assert html.startswith("<!DOCTYPE html>")
    assert '<html lang="en">' in html
    assert html.count("<h1>") == 1
    # Self-contained: it is emailed, saved and printed, so it cannot depend on
    # the site being up.
    assert "<style>" in html
    assert "http://" not in html


def test_the_artifact_is_large_print_and_printable():
    html = build_artifact_html(_sample_artifact())

    assert "font-size: 18pt" in html
    assert "font-family: Arial" in html
    assert "@media print" in html


def test_the_human_review_gate_is_the_prominent_thing():
    html = build_artifact_html(_sample_artifact())

    assert "Human review, required" in html
    assert "A person reads it aloud before it is sent" in html
    # Set apart in words, not by the border alone.
    assert "not finished until a person has done this" in html


def test_the_artifact_escapes_what_people_typed():
    artifact = Artifact(
        participant_name="<script>alert(1)</script>",
        session_code=CODE,
        workflow_name="<b>bold</b>",
    )

    html = build_artifact_html(artifact)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_a_plain_text_rendering_exists_for_mail_that_strips_html():
    text = build_artifact_text(_sample_artifact())

    assert "HUMAN REVIEW, REQUIRED" in text
    assert "Faculty" in text
    assert "<" not in text


# ---------------------------------------------------------------------------
# The artifact in the app
# ---------------------------------------------------------------------------


def test_the_artifact_is_built_from_the_participants_own_answers(client):
    _do_the_workshop(client)

    page = client.get(f"/workshop/session/{CODE}/artifact").get_data(as_text=True)

    assert "Faculty email accessibility coach" in page
    assert "Coach the chemistry department through one announcement" in page
    assert "A person reads it aloud before it is sent" in page


def test_an_empty_artifact_says_so_instead_of_pretending(client):
    page = client.get(f"/workshop/session/{CODE}/artifact").get_data(as_text=True)

    assert "There is nothing on it yet" in page


def test_drafts_are_left_off_the_artifact(client):
    client.post(
        f"/workshop/session/{CODE}/activity/champion_studio",
        data={"workflow_name": "Half an idea", "submit_action": "draft"},
    )

    page = client.get(f"/workshop/session/{CODE}/artifact").get_data(as_text=True)

    assert "Half an idea" not in page


def test_the_artifact_downloads_as_one_file(client):
    _do_the_workshop(client)

    resp = client.get(f"/workshop/session/{CODE}/artifact.html")

    assert resp.status_code == 200
    assert f'filename="{CODE}-my-glow-workflow.html"' in resp.headers["Content-Disposition"]
    assert b"Faculty email accessibility coach" in resp.data


def test_the_artifact_needs_a_participant(app: Flask):
    stranger = app.test_client()

    assert stranger.get(f"/workshop/session/{CODE}/artifact").status_code == 404


# ---------------------------------------------------------------------------
# Emailing it home
# ---------------------------------------------------------------------------


def test_the_email_carries_the_artifact_and_the_agent(client, mailbox: _MailBox):
    _do_the_workshop(client)

    resp = client.post(
        f"/workshop/session/{CODE}/artifact/email",
        data={"artifact_email": "rowan@example.edu"},
    )

    assert resp.status_code in (302, 303)
    assert resp.headers["Location"].endswith("sent=sent")
    assert len(mailbox.sent) == 1
    names = [name for name, _payload, _type in mailbox.sent[0]["attachments"]]
    assert any(name.endswith("my-glow-workflow.html") for name in names)
    assert any(name.endswith(".zip") for name in names)


def test_the_email_includes_a_way_back_in(client, mailbox: _MailBox):
    _do_the_workshop(client)
    client.post(
        f"/workshop/session/{CODE}/artifact/email", data={"artifact_email": "rowan@example.edu"}
    )

    assert "/workshop/return/" in mailbox.sent[0]["return_link"]


def test_the_address_given_earlier_is_reused_without_retyping(client, mailbox: _MailBox):
    _do_the_workshop(client)
    client.post(
        f"/workshop/session/{CODE}/artifact/email", data={"artifact_email": "rowan@example.edu"}
    )

    client.post(f"/workshop/session/{CODE}/artifact/email", data={"artifact_email": ""})

    assert len(mailbox.sent) == 2
    assert mailbox.sent[1]["to"] == "rowan@example.edu"


def test_an_empty_artifact_is_not_emailed(client, mailbox: _MailBox):
    resp = client.post(
        f"/workshop/session/{CODE}/artifact/email", data={"artifact_email": "rowan@example.edu"}
    )

    assert resp.headers["Location"].endswith("sent=empty")
    assert mailbox.sent == []


def test_a_malformed_address_is_refused_before_anything_is_sent(client, mailbox: _MailBox):
    _do_the_workshop(client)

    resp = client.post(
        f"/workshop/session/{CODE}/artifact/email", data={"artifact_email": "rowan.example.edu"}
    )

    assert resp.headers["Location"].endswith("sent=invalid-email")
    assert mailbox.sent == []


def test_the_artifact_address_never_reaches_a_shared_surface(client, mailbox: _MailBox, app: Flask):
    _do_the_workshop(client)
    client.post(
        f"/workshop/session/{CODE}/artifact/email", data={"artifact_email": "rowan@example.edu"}
    )

    for path in (
        f"/workshop/session/{CODE}/gallery",
        f"/workshop/session/{CODE}/wall",
        f"/workshop/session/{CODE}/export/json",
    ):
        assert "rowan@example.edu" not in client.get(path).get_data(as_text=True), path


# ---------------------------------------------------------------------------
# The commitment wall
# ---------------------------------------------------------------------------


def test_the_wall_shows_commitments_without_names(client, app: Flask):
    _do_the_workshop(client)

    page = client.get(f"/workshop/session/{CODE}/wall").get_data(as_text=True)

    assert "Coach the chemistry department through one announcement" in page
    assert "Email the chair on Monday" in page
    # Anonymous by design, whatever they chose for the gallery.
    assert "Rowan" not in page


def test_an_empty_wall_explains_itself(client):
    page = client.get(f"/workshop/session/{CODE}/wall").get_data(as_text=True)

    assert "No commitments yet" in page


def test_draft_commitments_stay_off_the_wall(client):
    client.post(
        f"/workshop/session/{CODE}/activity/action_plan_30_day",
        data={"workflow_30": "Still deciding", "submit_action": "draft"},
    )

    page = client.get(f"/workshop/session/{CODE}/wall").get_data(as_text=True)

    assert "Still deciding" not in page


# ---------------------------------------------------------------------------
# The 30-day nudge
# ---------------------------------------------------------------------------


def test_nobody_is_due_a_nudge_on_the_day(client, app: Flask):
    _do_the_workshop(client)

    with app.app_context():
        assert participants_due_for_nudge(CODE, days=30) == []


def test_a_commitment_comes_due_after_the_waiting_period(client, app: Flask, mailbox: _MailBox):
    _do_the_workshop(client)
    client.post(
        f"/workshop/session/{CODE}/artifact/email", data={"artifact_email": "rowan@example.edu"}
    )

    with app.app_context():
        # days=0 stands in for time passing.
        due = participants_due_for_nudge(CODE, days=0)

    assert len(due) == 1
    assert due[0]["login_email"] == "rowan@example.edu"


def test_someone_who_never_gave_an_address_is_never_emailed(client, app: Flask):
    _do_the_workshop(client)

    with app.app_context():
        assert participants_due_for_nudge(CODE, days=0) == []


def test_nobody_is_nudged_twice(client, app: Flask, mailbox: _MailBox):
    _do_the_workshop(client)
    client.post(
        f"/workshop/session/{CODE}/artifact/email", data={"artifact_email": "rowan@example.edu"}
    )

    with app.app_context():
        due = participants_due_for_nudge(CODE, days=0)
        record_nudge(CODE, due[0]["participant_key"])

        assert participants_due_for_nudge(CODE, days=0) == []


def test_the_nudge_command_defaults_to_a_dry_run(client, app: Flask, mailbox: _MailBox, monkeypatch):
    _do_the_workshop(client)
    client.post(
        f"/workshop/session/{CODE}/artifact/email", data={"artifact_email": "rowan@example.edu"}
    )
    sent: list = []
    monkeypatch.setattr(
        email_module, "send_workshop_nudge_email", lambda *a, **k: sent.append(a) or (True, "ok")
    )

    result = app.test_cli_runner().invoke(args=["workshop-nudge", CODE, "--days", "0"])

    assert "Dry run" in result.output
    assert "Rowan" in result.output
    assert sent == []


def test_the_nudge_quotes_their_own_words_back(app: Flask):
    from acb_large_print_web.workshop_nudge import _commitment_of

    row = {
        "content_json": '{"workflow_30": "Coach chemistry", "first_step_30": "Email the chair"}'
    }

    with app.app_context():
        commitment = _commitment_of(row)

    assert "Coach chemistry" in commitment
    assert "Email the chair" in commitment


def test_a_return_link_can_land_on_the_follow_through_log(client, app: Flask, mailbox: _MailBox):
    """The nudge asks how it went, so it has to arrive where the answer goes."""
    _do_the_workshop(client)
    from acb_large_print_web.workshop_store import create_return_link

    with app.app_context():
        key = client.get_cookie("glow_workshop_participant").value
        token = create_return_link(CODE, key)

    other = app.test_client()
    resp = other.get(f"/workshop/return/{token}?next=follow-through")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/follow-through")


def test_an_unknown_destination_falls_back_to_my_content(client, app: Flask):
    _do_the_workshop(client)
    from acb_large_print_web.workshop_store import create_return_link

    with app.app_context():
        key = client.get_cookie("glow_workshop_participant").value
        token = create_return_link(CODE, key)

    other = app.test_client()
    resp = other.get(f"/workshop/return/{token}?next=https://evil.example")

    assert resp.headers["Location"].endswith("/me")
