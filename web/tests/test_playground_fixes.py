"""Regression tests for AI Playground streaming history persistence (Fix 7)."""

from __future__ import annotations

import pytest

from acb_large_print_web.app import create_app
from acb_large_print_web.routes import playground as pg


@pytest.fixture()
def app():
    application = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "WTF_CSRF_ENABLED": False})
    return application


@pytest.fixture(autouse=True)
def _clear_server_history():
    with pg._server_history_lock:
        pg._server_history.clear()
    yield
    with pg._server_history_lock:
        pg._server_history.clear()


def test_set_history_persists_server_side_across_requests(app):
    """A turn recorded in one request (as the SSE generator does) is visible in
    the next request without relying on the response cookie."""
    turns = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    with app.test_request_context("/beta/chat/stream", method="POST"):
        pg._set_history(turns)

    # A fresh request context (same anon session hash) must still see the turns,
    # proving they were persisted server-side, not only in the cookie.
    with app.test_request_context("/beta/chat/send", method="POST"):
        assert pg._get_history() == turns


def test_streamed_turn_would_be_lost_via_cookie_only(app):
    """Sanity: writing to the cookie session inside a committed response is
    exactly what failed before; the server-side store is what rescues it."""
    with app.test_request_context("/beta/chat/stream", method="POST"):
        pg._set_history([
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
        ])
        # Server-side store holds it immediately, independent of any cookie.
        key = pg._session_hash()
    with pg._server_history_lock:
        assert key in pg._server_history
        assert len(pg._server_history[key]) == 2


def test_clear_wipes_server_side_history(app):
    with app.test_request_context("/beta/chat/stream", method="POST"):
        pg._set_history([
            {"role": "user", "content": "x"},
            {"role": "assistant", "content": "y"},
        ])
    with app.test_client() as client:
        # Seed the same session then clear via the route.
        resp = client.post("/beta/chat/clear")
        assert resp.status_code == 200
    with app.test_request_context("/beta/chat/send", method="POST"):
        # anon hash history cleared
        assert pg._get_history() == []


def test_get_history_seeds_from_cookie_when_server_store_empty(app):
    """Backward-compat: a cookie-seeded session still renders history."""
    seed = [{"role": "user", "content": "seeded"}, {"role": "assistant", "content": "ok"}]
    with app.test_request_context("/beta/chat/"):
        from flask import session

        session[pg._PLAYGROUND_HISTORY_KEY] = seed
        assert pg._get_history() == seed
