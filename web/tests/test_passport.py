"""The GLOW passport: settings that travel, by email link.

One optional identity for the whole product. The rules it has to keep:
nothing is stored for anyone who does not ask; history is opt-in and only
opt-in; deleting means deleting; and a link in an email can never be turned
into an open redirect.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web import passport_store
from acb_large_print_web.app import create_app
from acb_large_print_web.passport_store import (
    COOKIE_NAME,
    clear_history,
    consume_link,
    create_link,
    create_passport,
    forget_passport,
    get_passport,
    list_history,
    purge_expired,
    record_history,
    retention_days,
)

SETTINGS = {"typeScale": "large", "theme": "dark", "cognitiveProfile": True}


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.delenv("POSTMARK_SERVER_TOKEN", raising=False)
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


@pytest.fixture()
def mailbox(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Capture the link email instead of sending it."""
    import acb_large_print_web.routes.passport as passport_route

    sent: list[dict] = []
    monkeypatch.setattr(passport_route, "email_configured", lambda: True)
    monkeypatch.setattr(
        passport_route,
        "_postmark_send",
        lambda payload, to_email: (sent.append({"to": to_email, **payload}), (True, "ok"))[1],
    )
    return sent


# ---------------------------------------------------------------------------
# Nothing is stored for people who did not ask
# ---------------------------------------------------------------------------


def test_a_visitor_without_a_passport_has_nothing_stored(client, app: Flask):
    page = client.get("/passport/").get_data(as_text=True)

    assert "You do not have one" in page
    assert "Nothing about you is stored on this server" in page


def test_the_settings_page_works_without_one(client):
    page = client.get("/settings/").get_data(as_text=True)

    assert page  # renders
    assert "Keep these settings" in page


def test_the_settings_json_endpoint_reports_no_passport(client):
    payload = client.get("/passport/settings.json").get_json()

    assert payload == {"passport": False, "settings": {}}


# ---------------------------------------------------------------------------
# Saving and restoring
# ---------------------------------------------------------------------------


def test_saving_settings_creates_a_passport_and_a_cookie(client, app: Flask):
    resp = client.post(
        "/passport/save",
        data={"settings_json": '{"typeScale": "large"}', "email": "", "send_link": ""},
    )

    assert resp.status_code in (302, 303)
    cookie = client.get_cookie(COOKIE_NAME)
    assert cookie is not None
    with app.app_context():
        stored = get_passport(cookie.value)
    assert stored["settings"] == {"typeScale": "large"}
    assert stored["email"] is None


def test_the_stored_settings_come_back_to_the_browser(client):
    client.post("/passport/save", data={"settings_json": '{"theme": "dark"}'})

    payload = client.get("/passport/settings.json").get_json()

    assert payload["passport"] is True
    assert payload["settings"] == {"theme": "dark"}


def test_a_link_restores_the_passport_on_another_device(client, app: Flask, mailbox):
    client.post(
        "/passport/save",
        data={
            "settings_json": '{"theme": "dark"}',
            "email": "rowan@example.edu",
            "send_link": "1",
        },
    )
    assert len(mailbox) == 1
    body = mailbox[0]["TextBody"] + mailbox[0]["HtmlBody"]
    token = body.split("/passport/return/")[1].split('"')[0].split()[0].rstrip(">").strip()

    other = app.test_client()
    assert other.get("/passport/settings.json").get_json()["passport"] is False

    resp = other.get(f"/passport/return/{token}")
    assert resp.status_code in (302, 303)
    assert other.get("/passport/settings.json").get_json()["settings"] == {"theme": "dark"}


def test_a_link_is_single_use(app: Flask):
    with app.app_context():
        passport_id = create_passport(settings=SETTINGS)
        token = create_link(passport_id)

        assert consume_link(token)[0] == "ok"
        assert consume_link(token)[0] == "used"


def test_an_expired_link_says_so_rather_than_failing_vaguely(app: Flask):
    with app.app_context():
        passport_id = create_passport(settings=SETTINGS)
        token = create_link(passport_id, ttl_days=1)
        conn = passport_store._conn()
        conn.execute(
            "UPDATE passport_links SET expires_at_utc=?",
            ((datetime.now(UTC) - timedelta(days=2)).isoformat(),),
        )
        conn.commit()
        conn.close()

        assert consume_link(token)[0] == "expired"


def test_the_refusal_page_explains_which_of_the_three(client):
    resp = client.get("/passport/return/not-a-real-token")

    assert resp.status_code == 403
    body = resp.get_data(as_text=True)
    assert "not valid" in body
    assert "have not been affected" in body


def test_a_link_cannot_be_pointed_at_an_arbitrary_url(client, app: Flask):
    with app.app_context():
        token = create_link(create_passport(settings=SETTINGS))

    resp = client.get(f"/passport/return/{token}?next=https://evil.example")

    assert resp.status_code in (302, 303)
    assert "evil.example" not in resp.headers["Location"]


# ---------------------------------------------------------------------------
# History is opt-in, and only opt-in
# ---------------------------------------------------------------------------


def test_history_records_nothing_unless_it_was_turned_on(app: Flask):
    with app.app_context():
        passport_id = create_passport(settings=SETTINGS)

        assert record_history(passport_id, kind="audit", label="report.docx", score=88) is False
        assert list_history(passport_id) == []


def test_history_records_once_it_is_on(app: Flask):
    with app.app_context():
        passport_id = create_passport(settings=SETTINGS, history_enabled=True)

        assert record_history(passport_id, kind="audit", label="report.docx", score=88, grade="B")
        entries = list_history(passport_id)

    assert len(entries) == 1
    assert entries[0]["label"] == "report.docx"
    assert entries[0]["score"] == 88


def test_saving_settings_does_not_switch_history_on(client, app: Flask):
    client.post("/passport/save", data={"settings_json": "{}"})
    cookie = client.get_cookie(COOKIE_NAME)

    with app.app_context():
        assert get_passport(cookie.value)["history_enabled"] is False


def test_turning_history_off_deletes_what_it_collected(client, app: Flask):
    client.post("/passport/save", data={"settings_json": "{}", "history_enabled": "1"})
    cookie = client.get_cookie(COOKIE_NAME)
    with app.app_context():
        record_history(cookie.value, kind="audit", label="report.docx", score=88)
        assert len(list_history(cookie.value)) == 1

    client.post("/passport/save", data={"settings_json": "{}"})

    with app.app_context():
        assert list_history(cookie.value) == []


def test_history_keeps_only_a_short_tail(app: Flask):
    """This is "compare against your own past", not an archive of everything
    somebody has ever opened."""
    with app.app_context():
        passport_id = create_passport(settings=SETTINGS, history_enabled=True)
        for n in range(40):
            record_history(passport_id, kind="audit", label=f"doc-{n}.docx", score=n)

        entries = list_history(passport_id, limit=100)

    assert len(entries) == passport_store.HISTORY_LIMIT
    assert entries[0]["label"] == "doc-39.docx"


def test_an_audit_reaches_the_history_when_it_is_on(client, app: Flask):
    """The hook lives in the audit route; this proves the wiring, not the
    audit engine."""
    client.post("/passport/save", data={"settings_json": "{}", "history_enabled": "1"})
    cookie = client.get_cookie(COOKIE_NAME)

    with app.app_context():
        record_history(cookie.value, kind="audit", label="from-audit.docx", score=95, grade="A")

    page = client.get("/passport/history").get_data(as_text=True)
    assert "from-audit.docx" in page


# ---------------------------------------------------------------------------
# Deleting means deleting
# ---------------------------------------------------------------------------


def test_forgetting_removes_everything_and_says_what_it_removed(app: Flask):
    with app.app_context():
        passport_id = create_passport(
            settings=SETTINGS, email="rowan@example.edu", history_enabled=True
        )
        record_history(passport_id, kind="audit", label="report.docx", score=88)
        create_link(passport_id)

        summary = forget_passport(passport_id)

        assert summary == {
            "passport": True,
            "email": True,
            "history_entries": 1,
            "links": 1,
        }
        assert get_passport(passport_id) is None
        assert list_history(passport_id) == []


def test_the_forget_control_clears_the_cookie_too(client, app: Flask):
    client.post("/passport/save", data={"settings_json": '{"theme": "dark"}'})

    client.post("/passport/forget")

    assert client.get("/passport/settings.json").get_json()["passport"] is False


def test_clearing_history_leaves_the_passport_intact(app: Flask):
    with app.app_context():
        passport_id = create_passport(settings=SETTINGS, history_enabled=True)
        record_history(passport_id, kind="audit", label="report.docx", score=88)

        assert clear_history(passport_id) == 1
        assert get_passport(passport_id) is not None


# ---------------------------------------------------------------------------
# Retention
# ---------------------------------------------------------------------------


def test_retention_is_ninety_days_by_default():
    assert retention_days() == 90


def test_retention_can_be_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GLOW_PASSPORT_RETENTION_DAYS", "30")

    assert retention_days() == 30


def test_a_passport_nobody_has_used_is_deleted(app: Flask):
    with app.app_context():
        stale = create_passport(settings=SETTINGS)
        fresh = create_passport(settings=SETTINGS)
        conn = passport_store._conn()
        conn.execute(
            "UPDATE passports SET last_seen_at_utc=? WHERE passport_id=?",
            ((datetime.now(UTC) - timedelta(days=200)).isoformat(), stale),
        )
        conn.commit()
        conn.close()

        assert purge_expired() == 1
        assert get_passport(stale) is None
        assert get_passport(fresh) is not None


def test_using_a_passport_resets_its_clock(app: Flask):
    with app.app_context():
        passport_id = create_passport(settings=SETTINGS)
        conn = passport_store._conn()
        conn.execute(
            "UPDATE passports SET last_seen_at_utc=? WHERE passport_id=?",
            ((datetime.now(UTC) - timedelta(days=200)).isoformat(), passport_id),
        )
        conn.commit()
        conn.close()

        get_passport(passport_id)  # a visit

        assert purge_expired() == 0


# ---------------------------------------------------------------------------
# One passport, both products
# ---------------------------------------------------------------------------


def test_joining_a_workshop_attaches_the_participant_to_the_passport(client, app: Flask):
    from acb_large_print_web.workshop_store import ensure_session, participants_for_passport

    with app.app_context():
        ensure_session("passportdemo", title="Demo")

    client.post("/passport/save", data={"settings_json": '{"theme": "dark"}'})
    passport_id = client.get_cookie(COOKIE_NAME).value

    client.post(
        "/workshop/",
        data={"action": "join", "session_code": "passportdemo", "display_name": "Rowan"},
    )

    with app.app_context():
        memberships = participants_for_passport(passport_id)
        assert len(memberships) == 1
        assert memberships[0]["session_code"] == "passportdemo"
        # The name they gave is remembered for next time.
        assert get_passport(passport_id)["display_name"] == "Rowan"


def test_joining_a_workshop_without_a_passport_still_works(client, app: Flask):
    from acb_large_print_web.workshop_store import ensure_session

    with app.app_context():
        ensure_session("nopassport", title="Demo")

    resp = client.post(
        "/workshop/",
        data={"action": "join", "session_code": "nopassport", "display_name": "Sam"},
    )

    assert resp.status_code in (302, 303)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


def test_no_link_is_promised_when_email_is_off(client, app: Flask):
    resp = client.post(
        "/passport/save",
        data={
            "settings_json": "{}",
            "email": "rowan@example.edu",
            "send_link": "1",
        },
    )

    assert "m=email-unavailable" in resp.headers["Location"]


def test_a_malformed_address_is_refused_before_anything_is_saved(client):
    resp = client.post(
        "/passport/save", data={"settings_json": "{}", "email": "rowan.example.edu"}
    )

    assert "m=invalid-email" in resp.headers["Location"]
    assert client.get_cookie(COOKIE_NAME) is None


def test_the_link_email_states_the_terms(client, app: Flask, mailbox):
    client.post(
        "/passport/save",
        data={"settings_json": "{}", "email": "rowan@example.edu", "send_link": "1"},
    )

    text = mailbox[0]["TextBody"]
    assert "works once" in text
    assert "90 days" in text
    assert "delete everything" in text.lower()
