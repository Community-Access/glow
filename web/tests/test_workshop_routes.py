from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web import workshop_store
from acb_large_print_web.app import create_app
from acb_large_print_web.routes import workshop as workshop_routes
from acb_large_print_web.workshop_store import (
    add_feedback,
    count_submissions,
    ensure_session,
    list_submissions,
    save_submission,
    upsert_conference_code,
)

FACILITATOR_KEY = "ahg-facilitator-key"


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setenv("GLOW_WORKSHOP_FACILITATOR_KEY", FACILITATOR_KEY)
    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "MAX_CONTENT_LENGTH": 50 * 1024 * 1024,
        }
    )
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _seed_workshop(app: Flask, session_code: str = "demo75") -> str:
    with app.app_context():
        ensure_session(session_code, title="GLOW Workshop Demo", event_name="CSUN")
        submission_id = save_submission(
            session_code,
            "teach_vs_fix",
            "Alex",
            "Coach by clarifying the partner's barrier first.",
            anonymity_mode=False,
        )
        add_feedback(
            session_code,
            submission_id,
            "Sam",
            "Clear plain-language framing",
            "May skip policy requirement checks",
            "Add explicit policy review checkpoint",
            "Reuse this as a team checklist template",
        )
    return session_code


def _unlock_facilitator(client, code: str) -> None:
    resp = client.post(
        f"/workshop/session/{code}/facilitator/unlock",
        data={"facilitator_key": FACILITATOR_KEY},
    )
    assert resp.status_code in (302, 303)


# ---------------------------------------------------------------------------
# Page shell -- these pages must render inside the GLOW app shell
# ---------------------------------------------------------------------------

PUBLIC_WORKSHOP_PATHS = [
    "/workshop/",
    "/workshop/guide",
    "/workshop/exercises",
    "/workshop/utilization",
]


@pytest.mark.parametrize("path", PUBLIC_WORKSHOP_PATHS)
def test_workshop_pages_use_the_shared_app_shell(client, path: str):
    """Workshop pages must extend base.html.

    They used to be standalone documents built with render_template_string,
    which meant no GLOW branding, no sidebar, no theme support -- and inline
    <style> blocks that the app's CSP dropped outright in production.
    """
    resp = client.get(path)
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    assert 'id="primary-nav"' in body, "workshop page is missing the shared sidebar"
    assert "acb-large-print.css" in body, "workshop page is missing the ACB stylesheet"
    assert "forms.css" in body, "workshop page is missing the shared form styles"
    assert "workshop.css" in body, "workshop page is missing the workshop stylesheet"
    assert "<footer" in body, "workshop page is missing the shared footer"


@pytest.mark.parametrize("path", PUBLIC_WORKSHOP_PATHS)
def test_workshop_pages_have_no_unnonced_inline_style(client, path: str):
    """Regression: every inline <style> must carry the per-request CSP nonce.

    The app sets ``style-src 'self' 'nonce-...'``. An un-nonced <style> element
    is dropped by the browser, which is what left these pages unstyled.
    """
    resp = client.get(path)
    body = resp.get_data(as_text=True)
    for match in re.finditer(r"<style([^>]*)>", body):
        assert "nonce=" in match.group(1), f"un-nonced <style> on {path}: {match.group(0)!r}"


# ---------------------------------------------------------------------------
# Facilitator gate
# ---------------------------------------------------------------------------

FACILITATOR_ONLY_PATHS = [
    "/workshop/session/{code}/facilitator",
    "/workshop/session/{code}/export/markdown",
    "/workshop/session/{code}/export/json",
    "/workshop/session/{code}/export/html",
    "/workshop/session/{code}/export/docx",
    "/workshop/session/{code}/follow-through/export/markdown",
]


@pytest.mark.parametrize("template", FACILITATOR_ONLY_PATHS)
def test_session_wide_surfaces_require_facilitator(client, app: Flask, template: str):
    """Everything that exposes the whole room's work is facilitator-only."""
    code = _seed_workshop(app, "gate75")
    resp = client.get(template.format(code=code))
    assert resp.status_code == 403
    assert "Facilitator access required" in resp.get_data(as_text=True)


def test_facilitator_unlock_rejects_a_wrong_key(client, app: Flask):
    code = _seed_workshop(app, "wrongkey75")
    resp = client.post(
        f"/workshop/session/{code}/facilitator/unlock",
        data={"facilitator_key": "not-the-key"},
    )
    assert resp.status_code == 403
    assert "was not recognized" in resp.get_data(as_text=True)
    assert client.get(f"/workshop/session/{code}/facilitator").status_code == 403


def test_workshop_facilitator_and_surfaces(client, app: Flask):
    code = _seed_workshop(app)
    _unlock_facilitator(client, code)

    dashboard = client.get(f"/workshop/session/{code}/facilitator")
    assert dashboard.status_code == 200
    html = dashboard.get_data(as_text=True)
    assert "Facilitator dashboard" in html
    assert "Feedback coverage" in html
    # Activity names are rendered, not raw storage keys.
    assert "Fix It for Me vs Teach Me to Improve It" in html
    assert "teach_vs_fix" not in html

    coach = client.get(f"/workshop/session/{code}/coach")
    assert coach.status_code == 200
    assert "Coach Mode" in coach.get_data(as_text=True)

    review = client.get(f"/workshop/session/{code}/review")
    assert review.status_code == 200
    assert "Review Mode" in review.get_data(as_text=True)

    share = client.get(f"/workshop/session/{code}/share")
    assert share.status_code == 200
    assert "Share Mode" in share.get_data(as_text=True)


def test_workshop_export_formats(client, app: Flask):
    code = _seed_workshop(app, "exports75")
    _unlock_facilitator(client, code)

    md = client.get(f"/workshop/session/{code}/export/markdown")
    assert md.status_code == 200
    assert md.mimetype == "text/markdown"
    assert "GLOW Workshop Demo" in md.get_data(as_text=True)

    js = client.get(f"/workshop/session/{code}/export/json")
    assert js.status_code == 200
    assert js.mimetype == "application/json"
    assert '"session_code": "exports75"' in js.get_data(as_text=True)

    html = client.get(f"/workshop/session/{code}/export/html")
    assert html.status_code == 200
    assert html.mimetype == "text/html"
    assert "GLOW Workshop Demo" in html.get_data(as_text=True)

    docx = client.get(f"/workshop/session/{code}/export/docx")
    assert docx.status_code == 200
    assert docx.mimetype == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert docx.data.startswith(b"PK")


# ---------------------------------------------------------------------------
# Export redaction
# ---------------------------------------------------------------------------

def test_json_export_never_leaks_participant_tokens_or_anonymous_names(client, app: Flask):
    """The JSON export used to hand out the participant session cookie.

    ``participant_key`` is the value of ``glow_workshop_participant`` and is
    accepted as a bearer credential, so exporting it allowed anyone with the
    session code to assume another participant's identity. The same payload
    also carried the real name of participants who chose anonymity, while the
    Markdown, HTML and DOCX exports correctly masked it.
    """
    code = "redact75"
    with app.app_context():
        ensure_session(code, title="Redaction Demo")
        save_submission(
            code,
            "journey_check_in",
            "Jordan Rivera",
            "A sensitive example I do not want attributed.",
            participant_key="super-secret-participant-token",
            anonymity_mode=True,
        )
    _unlock_facilitator(client, code)

    payload = json.loads(client.get(f"/workshop/session/{code}/export/json").get_data(as_text=True))
    submission = payload["submissions"][0]

    assert submission["anonymity_mode"] == 1
    assert "participant_key" not in submission
    assert submission["display_name"] == "Anonymous participant"

    raw = client.get(f"/workshop/session/{code}/export/json").get_data(as_text=True)
    assert "super-secret-participant-token" not in raw
    assert "Jordan Rivera" not in raw

    markdown = client.get(f"/workshop/session/{code}/export/markdown").get_data(as_text=True)
    assert "Jordan Rivera" not in markdown


# ---------------------------------------------------------------------------
# Participant flows
# ---------------------------------------------------------------------------

def test_workshop_follow_through_flow(client, app: Flask):
    code = _seed_workshop(app, "follow75")

    page = client.get(f"/workshop/session/{code}/follow-through")
    assert page.status_code == 200
    assert "Workshop follow-through" in page.get_data(as_text=True)

    # Post/Redirect/Get: a refresh must not silently duplicate the item.
    save_resp = client.post(
        f"/workshop/session/{code}/follow-through",
        data={
            "item_kind": "action_commitment",
            "item_title": "Run team follow-up",
            "owner_name": "Alex",
            "due_date": "2026-06-15",
            "item_details": "Check adoption and confidence with the partner team.",
        },
    )
    assert save_resp.status_code in (302, 303)

    body = client.get(save_resp.headers["Location"]).get_data(as_text=True)
    assert "Saved follow-through item." in body
    assert "Run team follow-up" in body
    # Status is stated in text, not implied by the button verb alone.
    assert "Status" in body

    status_resp = client.post(
        f"/workshop/session/{code}/follow-through/1/status",
        data={"status": "done"},
    )
    assert status_resp.status_code in (302, 303)

    _unlock_facilitator(client, code)
    export_resp = client.get(f"/workshop/session/{code}/follow-through/export/markdown")
    assert export_resp.status_code == 200
    export_body = export_resp.get_data(as_text=True)
    assert "Run team follow-up" in export_body
    assert "2026-06-15" in export_body
    assert "Status: done" in export_body


def test_follow_through_preserves_entered_values_on_validation_failure(client, app: Flask):
    code = _seed_workshop(app, "ftkeep75")

    resp = client.post(
        f"/workshop/session/{code}/follow-through",
        data={
            "item_kind": "checklist",
            "item_title": "",  # missing -> validation failure
            "owner_name": "Robin",
            "due_date": "2026-07-01",
            "item_details": "Details the participant typed and must not lose.",
        },
    )
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Please add both a title and details" in body
    assert "Details the participant typed and must not lose." in body
    assert 'value="Robin"' in body
    assert 'value="2026-07-01"' in body
    assert 'value="checklist" selected' in body


def test_homepage_surfaces_workshop_follow_through(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Workshop Follow-Through" in body
    explore_idx = body.find('id="nav-group-explore"')
    assert explore_idx != -1


def test_workshop_activity_structured_form_and_save_next(client, app: Flask):
    code = "activity75"
    with app.app_context():
        ensure_session(code, title="Activity Demo")

    page = client.get(f"/workshop/session/{code}/activity/journey_check_in")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "Your response" in body
    assert "Accessibility Journey Check-In" in body

    save_next = client.post(
        f"/workshop/session/{code}/activity/journey_check_in",
        data={
            "display_name": "Pat",
            "work_type": "Document remediation",
            "partner_blockers": "Unclear heading structure",
            "champion_shift": "Partners would fix their own drafts",
            "submit_action": "save_next",
        },
    )
    assert save_next.status_code in (302, 303)
    assert "problem_statement" in save_next.headers["Location"]


def test_activity_keeps_anonymity_choice_when_validation_fails(client, app: Flask):
    """Regression: the anonymity tick used to be dropped on a failed submit.

    A participant who ticked "share anonymously", tripped validation and
    resubmitted would have their real name published to the gallery.
    """
    code = "anon75"
    with app.app_context():
        ensure_session(code, title="Anonymity Demo")

    resp = client.post(
        f"/workshop/session/{code}/activity/journey_check_in",
        data={
            "display_name": "Casey",
            "anonymity_mode": "on",
            "work_type": "Course content review",
            "partner_blockers": "",  # missing -> validation failure
            "champion_shift": "",
            "submit_action": "save",
        },
    )
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)

    assert 'name="anonymity_mode" type="checkbox"\n                 checked' in body or "checked" in body
    # Entered values survive.
    assert "Course content review" in body
    assert 'value="Casey"' in body
    # Every missing field is named -- the old code truncated the list to three.
    assert "Where do partners most often get stuck?" in body
    assert "What would change if more people became accessibility champions?" in body
    assert "..." not in body.split("Please complete these answers")[1].split("</p>")[0]


def test_workshop_code_lookup_then_name_join_and_my_content(client, app: Flask):
    code = "join75"
    with app.app_context():
        upsert_conference_code(
            "AHG2026",
            session_code=code,
            session_title="Accessibility Agents in Action",
            event_name="Accessing Higher Ground",
        )

    lookup = client.post("/workshop/", data={"action": "lookup", "access_code": "AHG2026"})
    assert lookup.status_code in (302, 303)

    join = client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Pat"})
    assert join.status_code in (302, 303)

    mine = client.get(f"/workshop/session/{code}/me")
    assert mine.status_code == 200
    assert "Participant: Pat" in mine.get_data(as_text=True)


def test_participant_can_export_their_own_artifacts_without_facilitator_access(client, app: Flask):
    """Session-wide exports are gated, so participants need their own route."""
    code = "selfexport75"
    with app.app_context():
        ensure_session(code, title="Self Export Demo")

    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Rowan"})
    client.post(
        f"/workshop/session/{code}/activity/journey_check_in",
        data={
            "display_name": "Rowan",
            "work_type": "Alt text coaching",
            "partner_blockers": "Purpose versus description",
            "champion_shift": "Content owners would decide purpose themselves",
            "submit_action": "save",
        },
    )

    resp = client.get(f"/workshop/session/{code}/me/export/markdown")
    assert resp.status_code == 200
    assert resp.mimetype == "text/markdown"
    body = resp.get_data(as_text=True)
    assert "Alt text coaching" in body
    assert "Accessibility Journey Check-In" in body

    # Session-wide export remains gated for this same participant.
    assert client.get(f"/workshop/session/{code}/export/markdown").status_code == 403


def test_workshop_launchpad_tokens_and_samples(client, app: Flask):
    code = "launch75"
    with app.app_context():
        ensure_session(code, title="Launchpad Demo")

    page = client.get(f"/workshop/session/{code}/launchpad")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert "Exercise launchpad" in body
    # Tool links read as tool names, not as raw GLOW:AUDIT style tokens.
    assert "Audit Workspace" in body
    assert "GLOW:AUDIT" not in body


def test_workshop_sample_and_resource_downloads_resolve(client, app: Flask):
    """These read off disk; the container layout differs from a checkout."""
    code = "assets75"
    with app.app_context():
        ensure_session(code, title="Asset Demo")

    sample = client.get(f"/workshop/session/{code}/samples/glow-test-docx")
    assert sample.status_code == 200
    assert sample.data.startswith(b"PK")

    resource = client.get("/workshop/resources/guide")
    assert resource.status_code == 200
    assert resource.mimetype == "text/markdown"


def test_workshop_return_banner_only_for_workshop_participants(client, app: Flask):
    code = "banner75"
    with app.app_context():
        ensure_session(code, title="Banner Demo")

    target = f"/workshop/session/{code}/launchpad"
    without_cookie = client.get(f"/audit/?workshop_return={target}&workshop_label=Return+to+Workshop")
    assert "Workshop flow:" not in without_cookie.get_data(as_text=True)

    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Pat"})
    with_cookie = client.get(f"/audit/?workshop_return={target}&workshop_label=Return+to+Workshop")
    assert "Workshop flow:" in with_cookie.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Revision, prefill and drafts
# ---------------------------------------------------------------------------

def _save_activity(client, code, activity="journey_check_in", **overrides):
    data = {
        "display_name": "Rowan",
        "work_type": "Alt text coaching",
        "partner_blockers": "Purpose versus description",
        "champion_shift": "Content owners would decide purpose themselves",
        "submit_action": "save",
    }
    data.update(overrides)
    return client.post(f"/workshop/session/{code}/activity/{activity}", data=data)


def test_resaving_an_activity_revises_instead_of_duplicating(client, app: Flask):
    """save_submission is an upsert.

    It used to be a bare INSERT, so every revision left another copy behind.
    By mid-morning the gallery, the room-wide counts and the facilitator's
    completion numbers were all inflated by repeat saves.
    """
    code = "revise75"
    with app.app_context():
        ensure_session(code, title="Revision Demo")
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Rowan"})

    _save_activity(client, code, work_type="First answer")
    _save_activity(client, code, work_type="Second answer")
    _save_activity(client, code, work_type="Third answer")

    with app.app_context():
        rows = list_submissions(code, activity_key="journey_check_in")
    assert len(rows) == 1, "re-saving an activity must revise the same row"
    assert "Third answer" in rows[0]["content_text"]
    assert "First answer" not in rows[0]["content_text"]


def test_saved_answers_are_prefilled_when_returning_to_an_activity(client, app: Flask):
    """WCAG 3.3.7 Redundant Entry: do not make people retype stored answers."""
    code = "prefill75"
    with app.app_context():
        ensure_session(code, title="Prefill Demo")
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Rowan"})

    _save_activity(
        client,
        code,
        work_type="Course content review",
        partner_blockers="Heading structure",
        champion_shift="Owners fix their own drafts",
        bonus_note="A reflection worth keeping",
        anonymity_mode="on",
    )

    body = client.get(f"/workshop/session/{code}/activity/journey_check_in").get_data(as_text=True)
    assert "Course content review" in body
    assert "Heading structure" in body
    assert "Owners fix their own drafts" in body
    assert "A reflection worth keeping" in body
    # The anonymity choice round-trips too.
    assert "checked" in body


def test_draft_saves_partial_work_and_stays_out_of_the_gallery(client, app: Flask):
    """Drafts let people park unfinished work against 46 required textareas."""
    code = "draft75"
    with app.app_context():
        ensure_session(code, title="Draft Demo")
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Rowan"})

    resp = client.post(
        f"/workshop/session/{code}/activity/journey_check_in",
        data={
            "display_name": "Rowan",
            "work_type": "Partial work so far",
            "partner_blockers": "",  # deliberately incomplete
            "champion_shift": "",
            "submit_action": "draft",
        },
    )
    assert resp.status_code in (302, 303)

    page = client.get(resp.headers["Location"]).get_data(as_text=True)
    assert "Draft saved" in page
    assert "Partial work so far" in page
    assert "saved as a draft" in page

    # A draft is unfinished work: not in the shared gallery, not in the counts.
    gallery = client.get(f"/workshop/session/{code}/gallery").get_data(as_text=True)
    assert "Partial work so far" not in gallery
    with app.app_context():
        assert count_submissions(code) == 0
        assert count_submissions(code, include_drafts=True) == 1

    # ...but the participant still sees their own draft.
    mine = client.get(f"/workshop/session/{code}/me").get_data(as_text=True)
    assert "Partial work so far" in mine


def test_completing_a_draft_promotes_it_without_duplicating(client, app: Flask):
    code = "draftdone75"
    with app.app_context():
        ensure_session(code, title="Draft Promote Demo")
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Rowan"})

    client.post(
        f"/workshop/session/{code}/activity/journey_check_in",
        data={"display_name": "Rowan", "work_type": "Draft text", "submit_action": "draft"},
    )
    _save_activity(client, code, work_type="Finished text")

    with app.app_context():
        assert count_submissions(code, include_drafts=True) == 1
        rows = list_submissions(code)
    assert len(rows) == 1
    assert int(rows[0]["is_draft"]) == 0
    assert "Finished text" in rows[0]["content_text"]


# ---------------------------------------------------------------------------
# Gallery pagination and filtering
# ---------------------------------------------------------------------------

def test_gallery_paginates_instead_of_rendering_every_submission(client, app: Flask):
    """A full-day session produces hundreds of submissions.

    Rendering them all put several thousand tab stops on one page.
    """
    code = "page75"
    with app.app_context():
        ensure_session(code, title="Pagination Demo")
        for i in range(25):
            save_submission(
                code,
                "teach_vs_fix",
                f"Person {i}",
                f"Submission body number {i}",
                participant_key=f"key-{i}",
            )

    first = client.get(f"/workshop/session/{code}/gallery").get_data(as_text=True)
    assert "Showing 1 to 10 of 25" in first
    assert "Page 1 of 3" in first
    assert "Submission body number 24" in first
    assert "Submission body number 4" not in first
    assert "Next page (page 2 of 3)" in first

    last = client.get(f"/workshop/session/{code}/gallery?page=3").get_data(as_text=True)
    assert "Showing 21 to 25 of 25" in last
    assert "Previous page (page 2 of 3)" in last

    # Out-of-range pages clamp rather than erroring or showing an empty page.
    clamped = client.get(f"/workshop/session/{code}/gallery?page=999")
    assert clamped.status_code == 200
    assert "Page 3 of 3" in clamped.get_data(as_text=True)


def test_gallery_filters_by_activity(client, app: Flask):
    code = "filter75"
    with app.app_context():
        ensure_session(code, title="Filter Demo")
        save_submission(code, "teach_vs_fix", "A", "Coaching answer", participant_key="k1")
        save_submission(code, "agent_formula", "B", "Agent answer", participant_key="k2")

    body = client.get(f"/workshop/session/{code}/gallery?activity=agent_formula").get_data(as_text=True)
    assert "Agent answer" in body
    assert "Coaching answer" not in body
    assert "Accessibility Agent Formula" in body

    ignored = client.get(f"/workshop/session/{code}/gallery?activity=not-a-real-activity").get_data(as_text=True)
    assert "Agent answer" in ignored
    assert "Coaching answer" in ignored


def test_peer_feedback_keeps_typed_text_when_validation_fails(client, app: Flask):
    """Regression: four textareas used to be discarded with no message."""
    code = _seed_workshop(app, "peerkeep75")
    with app.app_context():
        submission_id = list_submissions(code)[0]["id"]

    resp = client.post(
        f"/workshop/session/{code}/submission/{submission_id}/feedback",
        data={
            "reviewer_display_name": "Sam",
            "strength": "Really clear coaching tone",
            "risk_or_gap": "   ",  # whitespace only -> server rejects
            "recommended_safeguard": "Add a policy review step",
            "reuse_suggestion": "Turn this into a team checklist",
        },
    )
    assert resp.status_code in (302, 303)

    body = client.get(resp.headers["Location"]).get_data(as_text=True)
    assert "All four answers are needed" in body
    assert "Really clear coaching tone" in body
    assert "Add a policy review step" in body
    assert "Turn this into a team checklist" in body


# ---------------------------------------------------------------------------
# Reading level
# ---------------------------------------------------------------------------

def test_activity_prompts_stay_within_plain_language_target():
    """Prompts are read under time pressure by a deliberately broad audience.

    The workshop promises participants do not need to be developers or AI
    specialists, so the briefs are held to roughly a grade 8 reading level.
    """
    import re as _re

    from acb_large_print_web.routes.workshop import ACTIVITY_PROMPTS

    def syllables(word: str) -> int:
        word = word.lower().strip(".,!?;:'\"")
        if not word:
            return 0
        groups = _re.findall(r"[aeiouy]+", word)
        count = len(groups)
        if word.endswith("e") and count > 1 and not word.endswith(("le", "ee")):
            count -= 1
        return max(1, count)

    def grade(text: str) -> float:
        sentences = [s for s in _re.split(r"[.!?]+", text) if s.strip()]
        words = _re.findall(r"[A-Za-z']+", text)
        if not sentences or not words:
            return 0.0
        syl = sum(syllables(w) for w in words)
        return 0.39 * (len(words) / len(sentences)) + 11.8 * (syl / len(words)) - 15.59

    too_hard = {key: round(grade(text), 1) for key, text in ACTIVITY_PROMPTS.items() if grade(text) > 8.0}
    assert not too_hard, f"prompts above the grade 8 target: {too_hard}"


# ---------------------------------------------------------------------------
# Defects found by accessibility review of the first implementation round
# ---------------------------------------------------------------------------

def test_peer_feedback_failure_keeps_text_when_reviewing_from_a_later_page(client, app: Flask):
    """Regression: gallery pagination used to destroy the reviewer's answers.

    The redirect carried no page or filter, so a reviewer working on page 2 was
    returned to page 1. Their card was not rendered there, the stashed draft
    was popped anyway, and all five fields vanished with no error shown --
    indistinguishable from the button doing nothing.
    """
    code = "pagekeep75"
    with app.app_context():
        ensure_session(code, title="Paged Feedback Demo")
        for i in range(15):
            save_submission(code, "teach_vs_fix", f"P{i}", f"Body {i}", participant_key=f"k{i}")
        # Oldest row sorts last, so it lands on page 2.
        target = list_submissions(code)[-1]["id"]

    page_two = client.get(f"/workshop/session/{code}/gallery?page=2").get_data(as_text=True)
    assert f'id="submission-{target}"' in page_two, "fixture assumption: target is on page 2"

    resp = client.post(
        f"/workshop/session/{code}/submission/{target}/feedback",
        data={
            "reviewer_display_name": "Sam",
            "strength": "Clear coaching tone",
            "risk_or_gap": "   ",  # whitespace only -> rejected server-side
            "recommended_safeguard": "Add a policy review step",
            "reuse_suggestion": "Make it a team checklist",
            "return_page": "2",
            "return_activity": "",
        },
    )
    assert resp.status_code in (302, 303)
    location = resp.headers["Location"]
    assert "page=2" in location, "the reviewer must land back on the page they were on"

    body = client.get(location).get_data(as_text=True)
    assert "All four answers are needed" in body
    assert "Clear coaching tone" in body
    assert "Add a policy review step" in body
    assert "Make it a team checklist" in body


def test_peer_feedback_error_does_not_persist_after_refresh(client, app: Flask):
    """The error state follows the stashed draft, not the query string.

    Otherwise a refresh re-renders "your text is still below" above four empty
    boxes -- an error message that is actively lying.
    """
    code = _seed_workshop(app, "refresh75")
    with app.app_context():
        target = list_submissions(code)[0]["id"]

    resp = client.post(
        f"/workshop/session/{code}/submission/{target}/feedback",
        data={"reviewer_display_name": "Sam", "strength": "Good", "risk_or_gap": " ",
              "recommended_safeguard": "x", "reuse_suggestion": "y"},
    )
    location = resp.headers["Location"]

    first = client.get(location).get_data(as_text=True)
    assert "All four answers are needed" in first

    # Same URL again: the draft has been consumed, so the claim must be gone.
    second = client.get(location).get_data(as_text=True)
    assert "still in the form below" not in second
    assert "All four answers are needed" not in second


def test_saving_a_draft_cannot_demote_finished_work(client, app: Flask):
    """Regression: the upsert overwrote is_draft unconditionally.

    Returning to a completed activity and pressing "Save draft" pulled the
    finished response out of the gallery, the room count and the participant's
    own passport -- while showing a success message.
    """
    code = "demote75"
    with app.app_context():
        ensure_session(code, title="Demotion Demo")
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Rowan"})

    _save_activity(client, code, work_type="Finished work")
    with app.app_context():
        assert count_submissions(code) == 1

    client.post(
        f"/workshop/session/{code}/activity/journey_check_in",
        data={"display_name": "Rowan", "work_type": "Reworded", "submit_action": "draft"},
    )

    with app.app_context():
        rows = list_submissions(code)
    assert len(rows) == 1, "a finished response must stay published"
    assert int(rows[0]["is_draft"]) == 0
    assert "Reworded" in rows[0]["content_text"]


def test_anonymity_choice_carries_to_the_next_activity(client, app: Flask):
    """A participant should not have to re-tick anonymity eleven times.

    Forgetting once publishes their real name to the shared gallery.
    """
    code = "carry75"
    with app.app_context():
        ensure_session(code, title="Anonymity Carry Demo")
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Casey"})

    _save_activity(client, code, anonymity_mode="on")

    nxt = client.get(f"/workshop/session/{code}/activity/problem_statement").get_data(as_text=True)
    assert "checked" in nxt, "anonymity must default on for the next activity"
    # ...and the control must not be hidden behind a closed disclosure.
    assert "anonymous sharing" in nxt.lower()
    assert "<details open" in nxt.replace("<details ", "<details ")


def test_promote_to_follow_through_survives_peer_review_being_disabled(client, app: Flask):
    """Regression: one misplaced endif gated promote behind the peer-review flag.

    Follow-through has no flag of its own, so disabling peer review removed a
    feature it does not own -- and left cards with zero controls.
    """
    from acb_large_print_web.feature_flags import set_flag

    code = _seed_workshop(app, "flagscope75")

    with app.app_context():
        set_flag("GLOW_ENABLE_WORKSHOP_PEER_REVIEW", False)
    try:
        body = client.get(f"/workshop/session/{code}/gallery").get_data(as_text=True)
    finally:
        with app.app_context():
            set_flag("GLOW_ENABLE_WORKSHOP_PEER_REVIEW", True)

    # Guard against a vacuous pass: the flag must really have taken effect.
    assert "Add peer feedback" not in body
    assert "Promote to follow-through" in body


def test_error_states_reach_the_document_title(client, app: Flask):
    """The title is the only channel guaranteed to be announced on a page load.

    Programmatic focus applied during load is best-effort and is discarded
    outright by some screen reader and browser combinations.
    """
    code = "titlestate75"
    with app.app_context():
        ensure_session(code, title="Title Demo")
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Rowan"})

    failed = client.post(
        f"/workshop/session/{code}/activity/journey_check_in",
        data={"display_name": "Rowan", "work_type": "only one field", "submit_action": "save"},
    ).get_data(as_text=True)
    assert "<title>Not saved" in failed

    bad_code = client.post("/workshop/", data={"action": "lookup", "access_code": "!!"}).get_data(as_text=True)
    assert "<title>Code not recognised" in bad_code


def test_scrollable_tables_are_keyboard_reachable(client, app: Flask):
    """overflow-x containers need to be focusable or keyboard users cannot scroll them."""
    body = client.get("/workshop/").get_data(as_text=True)
    assert 'class="workshop-table-wrap" tabindex="0" role="region"' in body


# ---------------------------------------------------------------------------
# Champion Studio -> portable agent skill
# ---------------------------------------------------------------------------

CHAMPION_ANSWERS = {
    "workflow_name": "Faculty Email Accessibility Coach",
    "partner_group": "Faculty who send course announcements to large classes",
    "responsibility": "Write meaningful link text\nUse headings instead of bold text",
    "ai_support": "Find unclear links and missing structure\nSuggest a clearer rewrite",
    "final_output": "A revised email and a checklist for next time",
    "human_safeguard": "A person checks the accommodation contact details are current",
}

FORMULA_ANSWERS = {
    "role": "An accessibility communication coach",
    "task": "Review announcements before they go out",
    "trusted_guidance": "WCAG 2.2 AA\nUniversity accessibility policy",
    "output_format": "A revised draft plus a checklist",
    "human_review": "A person confirms the contact details",
}


def _join_and_design(client, app: Flask, code: str, *, with_formula: bool = True):
    with app.app_context():
        ensure_session(code, title="Skill Demo", event_name="Accessing Higher Ground")
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Jeff Bishop"})
    if with_formula:
        client.post(
            f"/workshop/session/{code}/activity/agent_formula",
            data={"display_name": "Jeff Bishop", "submit_action": "save", **FORMULA_ANSWERS},
        )
    client.post(
        f"/workshop/session/{code}/activity/champion_studio",
        data={"display_name": "Jeff Bishop", "submit_action": "save", **CHAMPION_ANSWERS},
    )


def test_champion_studio_compiles_a_valid_skill_package(client, app: Flask):
    """The workshop's five-part formula and an Agent Plugins skill are the same object.

    A participant who fills in the Champion Studio in plain language has
    authored a skill without writing any code, so GLOW compiles it for them.
    """
    import io
    import zipfile

    code = "skill75"
    _join_and_design(client, app, code)

    resp = client.get(f"/workshop/session/{code}/champion-skill.zip")
    assert resp.status_code == 200
    assert resp.mimetype == "application/zip"
    assert "faculty-email-accessibility-coach.zip" in resp.headers["Content-Disposition"]

    archive = zipfile.ZipFile(io.BytesIO(resp.data))
    names = archive.namelist()
    assert "faculty-email-accessibility-coach/SKILL.md" in names
    assert "faculty-email-accessibility-coach/README.md" in names
    # The package stays useful to someone with no agent tooling at all.
    assert "faculty-email-accessibility-coach/copy-into-any-assistant.txt" in names

    skill = archive.read("faculty-email-accessibility-coach/SKILL.md").decode("utf-8")

    # Frontmatter is well formed and slugged.
    assert skill.startswith("---\n")
    assert "name: faculty-email-accessibility-coach" in skill
    assert "author: Jeff Bishop" in skill
    assert "Accessing Higher Ground" in skill

    # The participant's own words survive, unaltered.
    assert "Write meaningful link text" in skill
    assert "Suggest a clearer rewrite" in skill

    # The human-review answer lands in the section the production skills use
    # for exactly this purpose.
    assert "## Verification truth" in skill
    assert "accommodation contact details are current" in skill
    assert "Never describe content as accessible on the basis of an automated result alone." in skill


def test_skill_frontmatter_is_parseable_yaml(client, app: Flask):
    """A malformed description would break every client that reads the file."""
    code = "yaml75"
    _join_and_design(client, app, code)

    from acb_large_print_web.workshop_skills import build_skill_markdown

    tricky = dict(CHAMPION_ANSWERS)
    tricky["workflow_name"] = 'A "quoted": name, with punctuation'
    tricky["partner_group"] = "Staff: those who write\nmulti-line answers"
    skill = build_skill_markdown(tricky, author="Jeff Bishop")

    _, frontmatter, _ = skill.split("---\n", 2)
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(frontmatter)
    except ImportError:
        pytest.skip("PyYAML not installed")

    assert isinstance(parsed, dict)
    assert parsed["name"] == "a-quoted-name-with-punctuation"
    assert isinstance(parsed["description"], str)
    assert parsed["metadata"]["author"] == "Jeff Bishop"


def test_agent_formula_supplies_the_trusted_guidance_section(client, app: Flask):
    """The two activities compose: the formula names the standards to follow."""
    code = "compose75"
    _join_and_design(client, app, code, with_formula=True)

    page = client.get(f"/workshop/session/{code}/champion-skill").get_data(as_text=True)
    assert "## Trusted guidance" in page
    assert "WCAG 2.2 AA" in page
    assert "University accessibility policy" in page

    # Without the formula the section is omitted and the participant is told why.
    other = "nocompose75"
    _join_and_design(client, app, other, with_formula=False)
    page2 = client.get(f"/workshop/session/{other}/champion-skill").get_data(as_text=True)
    assert "no trusted guidance section yet" in page2


def test_copy_prompt_needs_no_tooling_and_keeps_the_review_step(client, app: Flask):
    """Tier 2 is the path for people who already have ChatGPT or Copilot.

    It must carry the same substance as the skill file, without frontmatter,
    file paths or any reference to installing anything.
    """
    code = "prompt75"
    _join_and_design(client, app, code)

    page = client.get(f"/workshop/session/{code}/champion-skill").get_data(as_text=True)
    assert 'id="copy-prompt"' in page

    from acb_large_print_web.workshop_skills import build_copy_prompt

    prompt = build_copy_prompt(CHAMPION_ANSWERS, trusted_guidance="WCAG 2.2 AA")
    assert "---" not in prompt, "frontmatter must not leak into the paste-ready prompt"
    assert "SKILL.md" not in prompt
    assert "install" not in prompt.lower()
    assert "Suggest a clearer rewrite" in prompt
    assert "accommodation contact details are current" in prompt
    assert "what you checked and what you did not check" in prompt


def test_agent_is_not_offered_until_a_finished_workflow_exists(client, app: Flask):
    """A draft is not enough -- the agent needs every part of the formula."""
    code = "notready75"
    with app.app_context():
        ensure_session(code, title="Not Ready Demo")
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": "Rowan"})

    missing = client.get(f"/workshop/session/{code}/champion-skill")
    assert missing.status_code == 404
    assert "no finished response saved" in missing.get_data(as_text=True)
    assert client.get(f"/workshop/session/{code}/champion-skill.zip").status_code == 404

    client.post(
        f"/workshop/session/{code}/activity/champion_studio",
        data={"display_name": "Rowan", "workflow_name": "Half done", "submit_action": "draft"},
    )
    assert client.get(f"/workshop/session/{code}/champion-skill.zip").status_code == 404


def test_another_participant_cannot_download_your_agent(client, app: Flask):
    """The package is scoped to the participant who designed it."""
    code = "scoped75"
    _join_and_design(client, app, code)
    assert client.get(f"/workshop/session/{code}/champion-skill.zip").status_code == 200

    other = app.test_client()
    other.set_cookie("glow_consent_v1", "1", domain="localhost")
    assert other.get(f"/workshop/session/{code}/champion-skill.zip").status_code == 404


# ---------------------------------------------------------------------------
# Return links -- identity that survives a closed laptop
# ---------------------------------------------------------------------------


class _MailBox:
    """Captures return-link emails instead of calling Postmark."""

    def __init__(self, *, succeed: bool = True) -> None:
        self.succeed = succeed
        self.sent: list[dict] = []

    def __call__(self, to_email, *, link, ttl_days, session_title="", participant_name=""):
        self.sent.append(
            {
                "to": to_email,
                "link": link,
                "ttl_days": ttl_days,
                "session_title": session_title,
                "participant_name": participant_name,
            }
        )
        return (self.succeed, "queued" if self.succeed else "failed")


@pytest.fixture()
def mailbox(monkeypatch: pytest.MonkeyPatch) -> _MailBox:
    box = _MailBox()
    monkeypatch.setattr(workshop_routes, "email_configured", lambda: True)
    monkeypatch.setattr(workshop_routes, "send_workshop_return_link_email", box)
    return box


def _join_and_save(client, code: str, *, name: str = "Rowan") -> None:
    client.post("/workshop/", data={"action": "join", "session_code": code, "display_name": name})
    client.post(
        f"/workshop/session/{code}/activity/journey_check_in",
        data={
            "work_type": "Document remediation for a campus library.",
            "partner_blockers": "Faculty send scanned PDFs with no structure.",
            "champion_shift": "Departments would fix their own headings.",
        },
    )


def test_return_link_form_appears_on_my_content(client, app: Flask, mailbox: _MailBox):
    code = _seed_workshop(app, "returnform")
    _join_and_save(client, code)

    page = client.get(f"/workshop/session/{code}/me").get_data(as_text=True)

    assert 'name="return_email"' in page
    assert f"/workshop/session/{code}/return-link" in page


def test_return_link_restores_the_participant_on_another_device(client, app: Flask, mailbox: _MailBox):
    code = _seed_workshop(app, "returnhop")
    _join_and_save(client, code, name="Rowan")

    resp = client.post(
        f"/workshop/session/{code}/return-link",
        data={"return_email": "rowan@example.edu"},
    )
    assert resp.status_code in (302, 303)
    assert resp.headers["Location"].endswith("link=sent")
    assert len(mailbox.sent) == 1
    assert mailbox.sent[0]["to"] == "rowan@example.edu"

    # A second browser, with no participant cookie of its own.
    other = app.test_client()
    other.set_cookie("glow_consent_v1", "1", domain="localhost")
    assert other.get(f"/workshop/session/{code}/me").status_code == 404

    follow = other.get(mailbox.sent[0]["link"], follow_redirects=True)
    body = follow.get_data(as_text=True)
    assert follow.status_code == 200
    assert "Rowan" in body
    assert "Document remediation for a campus library." in body


def test_return_link_is_single_use(client, app: Flask, mailbox: _MailBox):
    code = _seed_workshop(app, "returnonce")
    _join_and_save(client, code)
    client.post(f"/workshop/session/{code}/return-link", data={"return_email": "rowan@example.edu"})
    link = mailbox.sent[0]["link"]

    first = app.test_client()
    first.set_cookie("glow_consent_v1", "1", domain="localhost")
    assert first.get(link).status_code in (302, 303)

    second = app.test_client()
    second.set_cookie("glow_consent_v1", "1", domain="localhost")
    replay = second.get(link)
    assert replay.status_code == 403
    assert "already been used" in replay.get_data(as_text=True)
    # The replay must not hand out an identity.
    assert second.get(f"/workshop/session/{code}/me").status_code == 404


def test_expired_return_link_is_refused_and_says_so(client, app: Flask, mailbox: _MailBox):
    code = _seed_workshop(app, "returnstale")
    _join_and_save(client, code)
    client.post(f"/workshop/session/{code}/return-link", data={"return_email": "rowan@example.edu"})
    link = mailbox.sent[0]["link"]

    with app.app_context():
        conn = workshop_store._conn()
        conn.execute(
            "UPDATE workshop_return_links SET expires_at_utc=?",
            ((datetime.now(UTC) - timedelta(days=1)).isoformat(),),
        )
        conn.commit()
        conn.close()

    stale = app.test_client()
    stale.set_cookie("glow_consent_v1", "1", domain="localhost")
    resp = stale.get(link)
    assert resp.status_code == 403
    assert "expired" in resp.get_data(as_text=True)


def test_unknown_return_token_is_refused(client, app: Flask, mailbox: _MailBox):
    _seed_workshop(app, "returnbogus")
    resp = client.get("/workshop/return/not-a-real-token")
    assert resp.status_code == 403
    assert "not valid" in resp.get_data(as_text=True)


def test_return_link_rejects_a_malformed_address_without_sending(client, app: Flask, mailbox: _MailBox):
    code = _seed_workshop(app, "returnbadmail")
    _join_and_save(client, code)

    resp = client.post(f"/workshop/session/{code}/return-link", data={"return_email": "rowan.example.edu"})

    assert resp.headers["Location"].endswith("link=invalid-email")
    assert mailbox.sent == []
    page = client.get(f"/workshop/session/{code}/me?link=invalid-email").get_data(as_text=True)
    assert "name@example.com" in page


def test_return_link_requires_a_participant(client, app: Flask, mailbox: _MailBox):
    code = _seed_workshop(app, "returnnoone")

    resp = client.post(f"/workshop/session/{code}/return-link", data={"return_email": "rowan@example.edu"})

    assert resp.status_code == 404
    assert mailbox.sent == []


def test_return_link_reports_a_failed_send(client, app: Flask, mailbox: _MailBox):
    code = _seed_workshop(app, "returnfail")
    _join_and_save(client, code)
    mailbox.succeed = False

    resp = client.post(f"/workshop/session/{code}/return-link", data={"return_email": "rowan@example.edu"})

    assert resp.headers["Location"].endswith("link=send-failed")
    page = client.get(f"/workshop/session/{code}/me?link=send-failed").get_data(as_text=True)
    assert "could not send" in page


def test_participant_email_never_reaches_facilitator_surfaces(client, app: Flask, mailbox: _MailBox):
    code = _seed_workshop(app, "returnprivate")
    _join_and_save(client, code)
    client.post(f"/workshop/session/{code}/return-link", data={"return_email": "rowan@example.edu"})

    facilitator = app.test_client()
    facilitator.set_cookie("glow_consent_v1", "1", domain="localhost")
    _unlock_facilitator(facilitator, code)

    surfaces = [
        f"/workshop/session/{code}/facilitator",
        f"/workshop/session/{code}/gallery",
        f"/workshop/session/{code}/export/json",
        f"/workshop/session/{code}/export/markdown",
        f"/workshop/session/{code}/export/html",
    ]
    for path in surfaces:
        body = facilitator.get(path).get_data(as_text=True)
        assert "rowan@example.edu" not in body, path


def test_return_token_is_not_stored_in_the_clear(client, app: Flask, mailbox: _MailBox):
    code = _seed_workshop(app, "returnhashed")
    _join_and_save(client, code)
    client.post(f"/workshop/session/{code}/return-link", data={"return_email": "rowan@example.edu"})
    token = mailbox.sent[0]["link"].rsplit("/", 1)[-1]

    with app.app_context():
        conn = workshop_store._conn()
        rows = conn.execute("SELECT token_hash FROM workshop_return_links").fetchall()
        conn.close()

    assert len(rows) == 1
    assert rows[0]["token_hash"] != token
    assert rows[0]["token_hash"] == hashlib.sha256(token.encode("utf-8")).hexdigest()
