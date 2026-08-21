"""Short URLs, QR codes, and the printable room signage.

The packet requires both, and requires the short URL rather than accepting a
QR code alone -- a QR code is no use to someone reading the page on the phone
they would have to scan it with, or to anyone using a screen reader.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
from acb_large_print_web.routes.workshop import ACTIVITY_ORDER
from acb_large_print_web.workshop_store import ensure_session

CODE = "ahgdemo"


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
    return app.test_client()


# ---------------------------------------------------------------------------
# Short URLs
# ---------------------------------------------------------------------------


def test_a_session_code_alone_is_enough_to_join(client):
    resp = client.get(f"/w/{CODE}")

    assert resp.status_code == 302
    assert resp.headers["Location"] == f"/workshop/?code={CODE}"


def test_activities_are_numbered_the_way_a_facilitator_says_them(client):
    """"Everyone go to slash w slash A H G slash seven." """
    for number, key in enumerate(ACTIVITY_ORDER, start=1):
        resp = client.get(f"/w/{CODE}/{number}")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith(f"/activity/{key}")


def test_numbers_outside_the_agenda_are_not_found(client):
    assert client.get(f"/w/{CODE}/0").status_code == 404
    assert client.get(f"/w/{CODE}/{len(ACTIVITY_ORDER) + 1}").status_code == 404


def test_a_malformed_session_code_is_not_found(client):
    assert client.get("/w/not a code/1").status_code == 404


def test_the_short_form_can_hand_out_a_random_scenario(client):
    resp = client.get(f"/w/{CODE}/6?surprise=1")

    assert resp.status_code == 302
    assert "scenario=surprise" in resp.headers["Location"]


def test_bare_short_prefix_reaches_the_workshop(client):
    resp = client.get("/w")

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/workshop/")


# ---------------------------------------------------------------------------
# QR codes
# ---------------------------------------------------------------------------


def test_qr_codes_are_svg_and_encode_this_sessions_short_url(client):
    resp = client.get(f"/workshop/session/{CODE}/qr/join.svg")
    body = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("image/svg+xml")
    assert "<svg" in body
    # Scannable in dark mode: the code brings its own quiet zone.
    assert "#ffffff" in body or "fill=\"#fff" in body


def test_every_activity_has_its_own_code(client):
    for number in range(1, len(ACTIVITY_ORDER) + 1):
        assert client.get(f"/workshop/session/{CODE}/qr/{number}.svg").status_code == 200


def test_the_endpoint_will_not_encode_arbitrary_targets(client):
    """Not a general 'encode any text' service: that would let anyone host a
    QR code pointing anywhere under this domain's name."""
    assert client.get(f"/workshop/session/{CODE}/qr/nope.svg").status_code == 404
    assert client.get(f"/workshop/session/{CODE}/qr/https%3A%2F%2Fevil.example.svg").status_code == 404


def test_qr_for_an_unknown_session_is_not_found(client):
    assert client.get("/workshop/session/nosuchsession/qr/join.svg").status_code == 404


# ---------------------------------------------------------------------------
# Signage
# ---------------------------------------------------------------------------


def test_signage_shows_the_address_as_text_beside_every_code(client):
    page = client.get(f"/workshop/session/{CODE}/signage").get_data(as_text=True)

    assert f"/w/{CODE}" in page
    # One card per activity plus the join card.
    assert page.count("workshop-signage-card") == len(ACTIVITY_ORDER) + 1
    assert 'alt="QR code for ' in page


def test_signage_explains_why_the_url_comes_first(client):
    page = client.get(f"/workshop/session/{CODE}/signage").get_data(as_text=True)

    assert "screen reader" in page


def test_the_facilitator_dashboard_links_to_the_signage(client, app: Flask, monkeypatch):
    monkeypatch.setenv("GLOW_WORKSHOP_FACILITATOR_KEY", "key")
    client.post(f"/workshop/session/{CODE}/facilitator/unlock", data={"facilitator_key": "key"})

    page = client.get(f"/workshop/session/{CODE}/facilitator").get_data(as_text=True)

    assert f"/workshop/session/{CODE}/signage" in page
