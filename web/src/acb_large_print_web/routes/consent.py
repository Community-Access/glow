"""Consent gate -- first-visit privacy agreement.

Every first-time visitor is redirected here before accessing any tool.
Agreement is stored in a long-lived cookie (glow_consent_v1).

Routes:
  GET  /consent          -- show the agreement page
  POST /consent          -- record agreement, set cookie, redirect to ?next=
"""

from __future__ import annotations

import hmac
import os
from datetime import timedelta

from urllib.parse import urlparse

from flask import (
    Blueprint,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

consent_bp = Blueprint("consent", __name__)


def _safe_next(next_url: str | None) -> str:
    """Return a same-site relative path, or the index if unsafe.

    A plain ``startswith(("http://", "https://", "//"))`` reject is bypassable:
    ``HTTPS://evil.com`` slips through the case-sensitive check, and ``/\\evil``
    is normalized to ``//evil`` by browsers. Test positively instead -- the
    target must parse with no scheme and no host, and begin with a single
    forward slash. The consent page is the first page a new visitor sees, which
    makes an open redirect here an unusually effective phishing lure.
    """
    fallback = url_for("main.index")
    candidate = (next_url or "").strip()
    if not candidate.startswith("/"):
        return fallback
    if candidate[1:2] in ("/", "\\"):
        return fallback
    parsed = urlparse(candidate)
    if parsed.scheme or parsed.netloc:
        return fallback
    return candidate

#: Cookie name.  Increment the suffix if the agreement text changes materially
#: so that returning users are asked to re-agree.
CONSENT_COOKIE_NAME = "glow_consent_v1"
CONSENT_COOKIE_MAX_AGE = int(timedelta(days=365).total_seconds())
AUTOMATION_CONSENT_HEADER = "X-GLOW-Automation-Consent"
AUTOMATION_CONSENT_DEFAULT_TOKEN = "GLOW"
AUTOMATION_CONSENT_TOKEN_ENV = "GLOW_AUTOMATION_CONSENT_TOKEN"
BYPASS_CONSENT_ENV = "GLOW_BYPASS_CONSENT_FOR_AUTOMATION"
ENABLE_AUTOMATION_BYPASS_ENDPOINT_ENV = "GLOW_ENABLE_AUTOMATION_CONSENT_ENDPOINT"

#: Routes the consent gate never intercepts.  Keep this list minimal.
CONSENT_EXEMPT_PREFIXES = (
    "/consent",
    "/static",
    "/health",
    "/status",
    "/privacy",
    "/favicon",
)


def has_consent(req) -> bool:
    """Return True if the visitor has already agreed."""
    return req.cookies.get(CONSENT_COOKIE_NAME) == "1"


def has_automation_consent_bypass(req) -> bool:
    """Return True when automation presents the configured bypass token."""
    expected_token = os.environ.get(
        AUTOMATION_CONSENT_TOKEN_ENV,
        AUTOMATION_CONSENT_DEFAULT_TOKEN,
    ).strip()
    if not expected_token:
        return False
    supplied_token = req.headers.get(AUTOMATION_CONSENT_HEADER, "").strip()
    if not supplied_token:
        return False
    return hmac.compare_digest(supplied_token, expected_token)


def _expected_automation_token() -> str:
    return os.environ.get(
        AUTOMATION_CONSENT_TOKEN_ENV,
        AUTOMATION_CONSENT_DEFAULT_TOKEN,
    ).strip()


def _is_automation_endpoint_enabled() -> bool:
    value = os.environ.get(ENABLE_AUTOMATION_BYPASS_ENDPOINT_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _is_valid_automation_token(token: str) -> bool:
    expected_token = _expected_automation_token()
    supplied_token = (token or "").strip()
    if not expected_token or not supplied_token:
        return False
    return hmac.compare_digest(supplied_token, expected_token)


def has_env_consent_bypass() -> bool:
    """Return True when consent is globally bypassed for automation contexts."""
    value = os.environ.get(BYPASS_CONSENT_ENV, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def consent_required(req) -> bool:
    """Return True if this request should trigger the consent redirect."""
    path = req.path.rstrip("/") or "/"
    if any(path.startswith(prefix) for prefix in CONSENT_EXEMPT_PREFIXES):
        return False
    if has_env_consent_bypass():
        return False
    if has_automation_consent_bypass(req):
        return False
    return not has_consent(req)


@consent_bp.route("/", methods=["GET"])
def consent_form():
    next_url = _safe_next(request.args.get("next"))
    return render_template("consent.html", next_url=next_url)


@consent_bp.route("/", methods=["POST"])
def consent_submit():
    agreed = request.form.get("agreed") == "yes"
    next_url = _safe_next(request.form.get("next_url"))

    if not agreed:
        return render_template(
            "consent.html",
            next_url=next_url,
            error="You must agree to the terms before continuing.",
        ), 400

    resp = make_response(redirect(next_url))
    resp.set_cookie(
        CONSENT_COOKIE_NAME,
        "1",
        max_age=CONSENT_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Strict",
        secure=request.is_secure,
    )
    return resp


@consent_bp.route("/bypass", methods=["GET"])
def consent_automation_bypass():
    """Set consent cookie for automation-driven browser inspection flows.

    Guardrails:
    - Disabled by default (requires GLOW_ENABLE_AUTOMATION_CONSENT_ENDPOINT=1)
    - Requires valid token (query param ``token`` or header)
    """
    if not _is_automation_endpoint_enabled():
        return "Not found", 404

    supplied_token = request.args.get("token") or request.headers.get(AUTOMATION_CONSENT_HEADER, "")
    if not _is_valid_automation_token(supplied_token):
        return "Forbidden", 403

    next_url = _safe_next(request.args.get("next"))

    resp = make_response(redirect(next_url))
    resp.set_cookie(
        CONSENT_COOKIE_NAME,
        "1",
        max_age=CONSENT_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Strict",
        secure=request.is_secure,
    )
    return resp


@consent_bp.route("/withdraw", methods=["POST"])
def consent_withdraw():
    """Clear the consent cookie so the user is asked to agree again next visit."""
    resp = make_response(redirect(url_for("consent.consent_form")))
    resp.delete_cookie(CONSENT_COOKIE_NAME, samesite="Strict")
    return resp
