"""Smoke tests for static / low-logic routes.

Covers:
- consent gate (GET show, POST accept, open-redirect guard)
- privacy page
- docs pages (guide, changelog, prd, faq, announcement)
- deployment guide page
- security response headers present on every response
- 429 error handler renders GLOW error page (not raw Flask text)
- 404 error handler
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask
from types import SimpleNamespace

from acb_large_print_web.routes.consent import (
    AUTOMATION_CONSENT_DEFAULT_TOKEN,
    AUTOMATION_CONSENT_HEADER,
    AUTOMATION_CONSENT_TOKEN_ENV,
    consent_required,
)

from acb_large_print_web.app import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


# ---------------------------------------------------------------------------
# Consent gate
# ---------------------------------------------------------------------------


def test_consent_get_renders_form(client):
    resp = client.get("/consent/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "consent" in body.lower() or "agree" in body.lower()


def test_consent_get_passes_next_param(client):
    resp = client.get("/consent/?next=%2Faudit%2F")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # next URL should be embedded in the form
    assert "/audit/" in body


def test_consent_post_sets_cookie_and_redirects(client):
    resp = client.post("/consent/", data={"agreed": "yes", "next_url": "/audit/"})
    assert resp.status_code in (302, 303)
    assert "glow_consent_v1" in resp.headers.get("Set-Cookie", "")
    assert "/audit/" in resp.headers.get("Location", "")


def test_consent_post_open_redirect_blocked(client):
    """Absolute URLs in next_url must not be honoured."""
    resp = client.post("/consent/", data={"agreed": "yes", "next_url": "https://evil.example.com/"})
    assert resp.status_code in (302, 303)
    location = resp.headers.get("Location", "")
    assert "evil.example.com" not in location


def test_consent_post_relative_next_honoured(client):
    resp = client.post("/consent/", data={"agreed": "yes", "next_url": "/fix/"})
    assert resp.status_code in (302, 303)
    assert "/fix/" in resp.headers.get("Location", "")


def test_consent_post_open_redirect_bypass_variants_blocked(client):
    """Case-mangled schemes and backslash tricks must not escape the site."""
    for evil in (
        "HTTPS://evil.example.com/",
        "https:/evil.example.com/",
        "/\\evil.example.com",
        "//evil.example.com",
        "\\/evil.example.com",
    ):
        resp = client.post("/consent/", data={"agreed": "yes", "next_url": evil})
        assert resp.status_code in (302, 303)
        location = resp.headers.get("Location", "")
        assert "evil.example.com" not in location, evil


def test_status_path_is_exempt_from_consent_gate():
    req = SimpleNamespace(path="/status", cookies={})
    assert consent_required(req) is False


def test_automation_consent_bypass_accepts_default_token(monkeypatch):
    monkeypatch.delenv(AUTOMATION_CONSENT_TOKEN_ENV, raising=False)
    req = SimpleNamespace(
        path="/audit/",
        cookies={},
        headers={AUTOMATION_CONSENT_HEADER: AUTOMATION_CONSENT_DEFAULT_TOKEN},
    )
    assert consent_required(req) is False


def test_automation_consent_bypass_accepts_matching_token(monkeypatch):
    monkeypatch.setenv(AUTOMATION_CONSENT_TOKEN_ENV, "automation-secret")
    req = SimpleNamespace(
        path="/audit/",
        cookies={},
        headers={AUTOMATION_CONSENT_HEADER: "automation-secret"},
    )
    assert consent_required(req) is False


def test_automation_consent_bypass_rejects_wrong_token(monkeypatch):
    monkeypatch.delenv(AUTOMATION_CONSENT_TOKEN_ENV, raising=False)
    req = SimpleNamespace(
        path="/audit/",
        cookies={},
        headers={AUTOMATION_CONSENT_HEADER: "wrong-secret"},
    )
    assert consent_required(req) is True


# ---------------------------------------------------------------------------
# Privacy page
# ---------------------------------------------------------------------------


def test_privacy_page_renders(client):
    resp = client.get("/privacy/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "privacy" in body.lower() or "data" in body.lower()


def test_privacy_page_has_heading(client):
    resp = client.get("/privacy/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "<h1" in body or "<h2" in body


# ---------------------------------------------------------------------------
# Documentation pages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url,keyword", [
    ("/guide/",        "guide"),
    ("/changelog/",    "changelog"),
    ("/prd/",          "product"),
    ("/deployment/",   "deployment"),
    ("/faq/",          "faq"),
    ("/announcement/", "glow"),
])
def test_docs_page_renders_200(client, url, keyword):
    resp = client.get(url)
    assert resp.status_code == 200, f"{url} returned {resp.status_code}"
    body = resp.get_data(as_text=True).lower()
    assert keyword in body, f"'{keyword}' not found in {url}"


def test_changelog_page_no_jinja_syntax_error(client):
    """The /changelog/ page must not raise a TemplateSyntaxError.

    This regression test guards against changelog entries that document
    Jinja syntax ({{.Name}}, {%if%}) leaking through into the rendered
    partial and being mis-parsed by Jinja2.  The page must return 200;
    the body must not contain a Jinja exception traceback.
    """
    resp = client.get("/changelog/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # A live Jinja exception produces "jinja2.exceptions.TemplateSyntaxError"
    # in the traceback.  The word "TemplateSyntaxError" alone can appear in
    # the changelog text that *documents* the fix -- that is fine.
    assert "jinja2.exceptions.TemplateSyntaxError" not in body
    assert "Internal Server Error" not in body


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url", [
    "/",
    "/audit/",
    "/fix/",
    "/privacy/",
    "/changelog/",
    "/status",
    "/health",
])
def test_security_headers_present(client, url):
    resp = client.get(url)
    assert resp.headers.get("X-Content-Type-Options") == "nosniff", \
        f"X-Content-Type-Options missing on {url}"
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN", \
        f"X-Frame-Options missing on {url}"
    assert "Referrer-Policy" in resp.headers, \
        f"Referrer-Policy missing on {url}"


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


def test_404_renders_glow_error_page(client):
    resp = client.get("/this-route-definitely-does-not-exist-xyzzy/")
    assert resp.status_code == 404
    body = resp.get_data(as_text=True)
    # Must be our error template, not a raw Flask/Werkzeug HTML page
    assert "Page Not Found" in body or "not found" in body.lower()
    assert "<html" in body.lower()


def test_429_handler_renders_glow_error_page(app):
    """Manually trigger the 429 handler and verify it renders the GLOW template."""
    from werkzeug.exceptions import TooManyRequests

    with app.test_request_context("/"):
        with app.app_context():
            # Find the registered 429 handler by walking the spec the same way
            # Flask's dispatch_exception does: HTTPException code -> handler.
            exc = TooManyRequests()
            handler = app._find_error_handler(exc, "")
            assert handler is not None, "No 429 error handler registered"
            result = handler(exc)
            # Handler returns (response_body, status_code) or a Response object
            if isinstance(result, tuple):
                body = result[0]
                code = result[1]
            else:
                body = result.get_data(as_text=True)
                code = result.status_code
            assert code == 429
            assert "Too Many Requests" in body or "many requests" in str(body).lower()
