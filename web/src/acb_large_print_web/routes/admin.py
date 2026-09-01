"""Admin authentication and queue management routes.

Admin access is intentionally separate from end-user workflows.
Current scope: admin-only sign-in and approval workflow.
Future scope may introduce non-admin user accounts.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import html as html_mod
import os
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from werkzeug.security import check_password_hash, generate_password_hash
from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ..app import limiter
from ..credentials import get_bootstrap_admin_email, get_bootstrap_admin_password
from ..ai_gateway import (
    get_admin_stats,
    get_model_catalog,
    get_runtime_config,
    project_monthly_cost,
    update_runtime_config,
)
from ..feature_flags import (
    get_all_flags as _get_all_flags,
    get_flag as _get_flag,
    set_flag as _set_flag,
    reset_defaults as _reset_flag_defaults,
    get_flag_meta as _get_flag_meta,
    get_backend as _get_flags_backend,
    migrate_json_to_sqlite as _migrate_flags,
    get_audit_entries as _get_audit_entries,
)
from ..email import (
    email_configured,
    email_status,
    send_test_email,
    send_whisperer_status_email,
)
from ..speech import (
    get_engine_status,
    get_piper_voice_inventory,
    install_piper_voice,
    remove_piper_voice,
)
from .whisperer import (
    admin_cancel_queued_job,
    admin_requeue_failed_job,
    get_admin_queue_snapshot,
)

admin_bp = Blueprint("admin", __name__)

_MAGIC_LINK_TTL_MINUTES = int(os.environ.get("ADMIN_MAGIC_LINK_TTL_MINUTES", "20"))


def _abort_if_admin_login_disabled() -> None:
    """Hide only admin authentication entry points when feature-gated off."""
    if current_app.testing:
        return
    if not _get_flag("GLOW_ENABLE_ADMIN_LOGIN", False):
        abort(404)


@dataclass
class _ProviderConfig:
    key: str
    label: str
    client_id: str
    client_secret: str
    auth_url: str
    token_url: str
    userinfo_url: str
    scope: str
    email_field: str


def _db_path() -> Path:
    instance_path = Path(current_app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    return instance_path / "admin_auth.db"


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS admin_accounts ("
        "  email TEXT PRIMARY KEY,"
        "  display_name TEXT,"
        "  approved INTEGER NOT NULL DEFAULT 0,"
        "  password_hash TEXT,"
        "  created_at TEXT NOT NULL,"
        "  approved_at TEXT,"
        "  approved_by TEXT"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS admin_requests ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  email TEXT NOT NULL,"
        "  display_name TEXT,"
        "  reason TEXT,"
        "  status TEXT NOT NULL DEFAULT 'pending',"
        "  requested_at TEXT NOT NULL,"
        "  reviewed_at TEXT,"
        "  reviewed_by TEXT"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS admin_magic_links ("
        "  token_hash TEXT PRIMARY KEY,"
        "  email TEXT NOT NULL,"
        "  expires_at TEXT NOT NULL,"
        "  created_at TEXT NOT NULL,"
        "  used_at TEXT"
        ")"
    )
    cols = [r[1] for r in conn.execute("PRAGMA table_info(admin_accounts)").fetchall()]
    if "password_hash" not in cols:
        conn.execute("ALTER TABLE admin_accounts ADD COLUMN password_hash TEXT")
    conn.commit()
    return conn


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _bootstrap_admins() -> None:
    raw = os.environ.get("ADMIN_BOOTSTRAP_EMAILS", "").strip()
    if not raw:
        return

    emails = [_normalize_email(item) for item in raw.split(",") if item.strip()]
    if not emails:
        return

    conn = _db()
    now = _utc_now()
    for email in emails:
        conn.execute(
            "INSERT INTO admin_accounts (email, display_name, approved, created_at, approved_at, approved_by) "
            "VALUES (?, ?, 1, ?, ?, 'bootstrap') "
            "ON CONFLICT(email) DO UPDATE SET approved=1",
            (email, email, now, now),
        )
    conn.commit()
    conn.close()

    _bootstrap_local_admin_password()


def _bootstrap_local_admin_password() -> None:
    """Bootstrap a local password admin account for emergency/admin access."""
    email = _normalize_email(get_bootstrap_admin_email())
    password = get_bootstrap_admin_password().strip()
    if not email or not password:
        return

    conn = _db()
    now = _utc_now()
    row = conn.execute(
        "SELECT email, password_hash FROM admin_accounts WHERE email=?",
        (email,),
    ).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO admin_accounts (email, display_name, approved, password_hash, created_at, approved_at, approved_by) "
            "VALUES (?, ?, 1, ?, ?, ?, 'bootstrap-local')",
            (email, email, generate_password_hash(password), now, now),
        )
    elif not row["password_hash"]:
        conn.execute(
            "UPDATE admin_accounts SET approved=1, password_hash=?, approved_at=?, approved_by='bootstrap-local' WHERE email=?",
            (generate_password_hash(password), now, email),
        )

    conn.commit()
    conn.close()


def _account(email: str) -> sqlite3.Row | None:
    conn = _db()
    row = conn.execute(
        "SELECT email, display_name, approved, password_hash FROM admin_accounts WHERE email=?",
        (email,),
    ).fetchone()
    conn.close()
    return row


def _is_approved_admin(email: str) -> bool:
    row = _account(email)
    return bool(row and int(row["approved"]) == 1)


def _current_admin_email() -> str | None:
    value = session.get("admin_email")
    return _normalize_email(value) if value else None


def _require_admin() -> str:
    _bootstrap_admins()
    email = _current_admin_email()
    if not email or not _is_approved_admin(email):
        abort(403)
    return email


def is_authenticated_admin() -> bool:
    """Public, non-aborting variant of :func:`_require_admin`.

    Other blueprints need to ask "is this an approved admin?" without the
    403 side effect so they can fall back to their own access path.
    """
    try:
        _bootstrap_admins()
        email = _current_admin_email()
        return bool(email and _is_approved_admin(email))
    except Exception:
        return False


def _provider_env(prefix: str, name: str) -> str:
    return os.environ.get(f"ADMIN_OAUTH_{prefix}_{name}", "").strip()


def _provider_configs() -> list[_ProviderConfig]:
    providers: list[_ProviderConfig] = []

    def add_provider(
        key: str,
        label: str,
        default_auth: str,
        default_token: str,
        default_userinfo: str,
        default_scope: str,
        default_email_field: str,
    ) -> None:
        prefix = key.upper()
        client_id = _provider_env(prefix, "CLIENT_ID")
        client_secret = _provider_env(prefix, "CLIENT_SECRET")
        auth_url = _provider_env(prefix, "AUTH_URL") or default_auth
        token_url = _provider_env(prefix, "TOKEN_URL") or default_token
        userinfo_url = _provider_env(prefix, "USERINFO_URL") or default_userinfo
        scope = _provider_env(prefix, "SCOPE") or default_scope
        email_field = _provider_env(prefix, "EMAIL_FIELD") or default_email_field

        if not client_id or not client_secret or not auth_url or not token_url or not userinfo_url:
            return

        providers.append(
            _ProviderConfig(
                key=key,
                label=label,
                client_id=client_id,
                client_secret=client_secret,
                auth_url=auth_url,
                token_url=token_url,
                userinfo_url=userinfo_url,
                scope=scope,
                email_field=email_field,
            )
        )

    add_provider(
        "google",
        "Google",
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
        "https://openidconnect.googleapis.com/v1/userinfo",
        "openid email profile",
        "email",
    )

    add_provider(
        "github",
        "GitHub",
        "https://github.com/login/oauth/authorize",
        "https://github.com/login/oauth/access_token",
        "https://api.github.com/user",
        "read:user user:email",
        "email",
    )

    add_provider(
        "microsoft",
        "Microsoft",
        "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "https://graph.microsoft.com/v1.0/me",
        "openid email profile",
        "mail",
    )

    auth0_domain = os.environ.get("ADMIN_AUTH0_DOMAIN", "").strip()
    if auth0_domain:
        auth0_domain = auth0_domain.rstrip("/")
        add_provider(
            "auth0",
            "Auth0",
            f"{auth0_domain}/authorize",
            f"{auth0_domain}/oauth/token",
            f"{auth0_domain}/userinfo",
            "openid email profile",
            "email",
        )

    add_provider(
        "apple",
        "Apple",
        "https://appleid.apple.com/auth/authorize",
        "https://appleid.apple.com/auth/token",
        _provider_env("APPLE", "USERINFO_URL"),
        "name email",
        "email",
    )

    add_provider(
        "wordpress",
        "WordPress",
        _provider_env("WORDPRESS", "AUTH_URL"),
        _provider_env("WORDPRESS", "TOKEN_URL"),
        _provider_env("WORDPRESS", "USERINFO_URL"),
        "openid email profile",
        "email",
    )

    return providers


def _send_admin_email(to_email: str, subject: str, html: str, text: str) -> None:
    if not email_configured():
        return
    send_whisperer_status_email(to_email, subject, html, text)


def _pending_requests() -> list[sqlite3.Row]:
    conn = _db()
    rows = conn.execute(
        "SELECT id, email, display_name, reason, status, requested_at, reviewed_at, reviewed_by "
        "FROM admin_requests ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return rows


def _make_magic_link(email: str) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = (datetime.now(UTC) + timedelta(minutes=_MAGIC_LINK_TTL_MINUTES)).isoformat()

    conn = _db()
    conn.execute(
        "INSERT INTO admin_magic_links (token_hash, email, expires_at, created_at, used_at) "
        "VALUES (?, ?, ?, ?, NULL)",
        (token_hash, email, expires_at, _utc_now()),
    )
    conn.commit()
    conn.close()
    return token


def _decode_jwt_email(id_token: str) -> str:
    try:
        parts = id_token.split(".")
        if len(parts) < 2:
            return ""
        payload = parts[1]
        padded = payload + "=" * (-len(payload) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
        import json

        obj = json.loads(raw.decode("utf-8"))
        return _normalize_email(obj.get("email", ""))
    except Exception:
        return ""


@admin_bp.route("/login", methods=["GET"])
def admin_login() -> Any:
    _abort_if_admin_login_disabled()
    _bootstrap_admins()
    providers = _provider_configs() if email_configured() else []
    local_password_email = _normalize_email(get_bootstrap_admin_email())
    return render_template(
        "admin_login.html",
        providers=providers,
        email_enabled=email_configured(),
        local_password_enabled=bool(get_bootstrap_admin_password().strip()),
        local_password_email=local_password_email,
        ttl_minutes=_MAGIC_LINK_TTL_MINUTES,
    )


@admin_bp.route("/login/password", methods=["POST"])
@limiter.limit("10 per minute")
def admin_login_password() -> Any:
    _abort_if_admin_login_disabled()
    _bootstrap_admins()
    email = _normalize_email(request.form.get("email", ""))
    password = request.form.get("password", "")
    email_enabled = email_configured()
    local_password_email = _normalize_email(get_bootstrap_admin_email())

    if not email and not email_enabled and local_password_email:
        email = local_password_email

    if not password:
        return render_template(
            "admin_login.html",
            providers=_provider_configs() if email_enabled else [],
            email_enabled=email_enabled,
            local_password_enabled=bool(get_bootstrap_admin_password().strip()),
            local_password_email=local_password_email,
            ttl_minutes=_MAGIC_LINK_TTL_MINUTES,
            error="Password is required.",
        ), 400

    if not email:
        return render_template(
            "admin_login.html",
            providers=_provider_configs() if email_enabled else [],
            email_enabled=email_enabled,
            local_password_enabled=bool(get_bootstrap_admin_password().strip()),
            local_password_email=local_password_email,
            ttl_minutes=_MAGIC_LINK_TTL_MINUTES,
            error="Email is required for password sign-in.",
        ), 400

    row = _account(email)
    if row is None or not row["password_hash"] or not check_password_hash(row["password_hash"], password):
        return render_template(
            "admin_login.html",
            providers=_provider_configs() if email_enabled else [],
            email_enabled=email_enabled,
            local_password_enabled=bool(get_bootstrap_admin_password().strip()),
            local_password_email=local_password_email,
            ttl_minutes=_MAGIC_LINK_TTL_MINUTES,
            error="Invalid admin credentials.",
        ), 403

    if int(row["approved"]) != 1:
        return render_template(
            "admin_login.html",
            providers=_provider_configs() if email_enabled else [],
            email_enabled=email_enabled,
            local_password_enabled=bool(get_bootstrap_admin_password().strip()),
            local_password_email=local_password_email,
            ttl_minutes=_MAGIC_LINK_TTL_MINUTES,
            error="This account is not approved for admin access.",
        ), 403

    # Prevent session fixation: drop any pre-login session before elevating.
    session.clear()
    session["admin_email"] = email
    return redirect(url_for("admin.admin_queue"))


@admin_bp.route("/logout", methods=["POST"])
def admin_logout() -> Any:
    session.pop("admin_email", None)
    return redirect(url_for("admin.admin_login"))


@admin_bp.route("/request-access", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def admin_request_access() -> Any:
    _abort_if_admin_login_disabled()
    _bootstrap_admins()
    if not email_configured():
        return (
            render_template(
                "admin_request_access.html",
                submitted=False,
                form_disabled=True,
                error="Admin access requests are unavailable until email delivery is configured.",
            ),
            503,
        )

    if request.method == "GET":
        return render_template("admin_request_access.html", submitted=False)

    email = _normalize_email(request.form.get("email", ""))
    name = (request.form.get("display_name", "") or "").strip()
    reason = (request.form.get("reason", "") or "").strip()

    if not email:
        return render_template("admin_request_access.html", submitted=False, error="Email is required."), 400

    conn = _db()
    pending = conn.execute(
        "SELECT id FROM admin_requests WHERE email=? AND status='pending'",
        (email,),
    ).fetchone()
    if pending:
        conn.close()
        return render_template("admin_request_access.html", submitted=True)

    conn.execute(
        "INSERT INTO admin_requests (email, display_name, reason, status, requested_at, reviewed_at, reviewed_by) "
        "VALUES (?, ?, ?, 'pending', ?, NULL, NULL)",
        (email, name, reason, _utc_now()),
    )
    conn.commit()
    conn.close()

    if email_configured():
        bootstrap = os.environ.get("ADMIN_BOOTSTRAP_EMAILS", "")
        admins = [_normalize_email(item) for item in bootstrap.split(",") if item.strip()]
        safe_email = html_mod.escape(email)
        safe_name = html_mod.escape(name or "N/A")
        safe_reason = html_mod.escape(reason or "N/A")
        for admin_email in admins:
            _send_admin_email(
                admin_email,
                "GLOW admin access request",
                (
                    f"<p>New admin access request from <strong>{safe_email}</strong>.</p>"
                    f"<p>Name: {safe_name}</p><p>Reason: {safe_reason}</p>"
                    f"<p>Review requests: <a href=\"{url_for('admin.admin_login', _external=True)}\">Admin login</a></p>"
                ),
                (
                    f"New admin access request from {email}.\n"
                    f"Name: {name or 'N/A'}\nReason: {reason or 'N/A'}\n"
                    f"Review at: {url_for('admin.admin_login', _external=True)}"
                ),
            )

    return render_template("admin_request_access.html", submitted=True)


@admin_bp.route("/login/email", methods=["POST"])
@limiter.limit("5 per minute")
def admin_login_email() -> Any:
    _abort_if_admin_login_disabled()
    _bootstrap_admins()
    if not email_configured():
        return render_template("admin_login.html", providers=[], email_enabled=False, error="Email authentication is not available."), 400

    email = _normalize_email(request.form.get("email", ""))
    if not email:
        return render_template("admin_login.html", providers=_provider_configs(), email_enabled=True, error="Email is required."), 400

    if not _is_approved_admin(email):
        return render_template(
            "admin_login.html",
            providers=_provider_configs(),
            email_enabled=True,
            error="This account is not approved for admin access. Please request access.",
            ttl_minutes=_MAGIC_LINK_TTL_MINUTES,
        ), 403

    token = _make_magic_link(email)
    link = url_for("admin.admin_magic_link_consume", token=token, _external=True)
    _send_admin_email(
        email,
        "GLOW admin sign-in link",
        (
            "<p>Your admin sign-in link is ready.</p>"
            f"<p><a href=\"{link}\">Sign in to admin</a></p>"
            f"<p>This link expires in {_MAGIC_LINK_TTL_MINUTES} minutes.</p>"
        ),
        (
            f"Your admin sign-in link: {link}\n"
            f"This link expires in {_MAGIC_LINK_TTL_MINUTES} minutes."
        ),
    )
    return render_template(
        "admin_login.html",
        providers=_provider_configs(),
        email_enabled=True,
        notice="A secure admin sign-in link was sent to your email.",
        ttl_minutes=_MAGIC_LINK_TTL_MINUTES,
    )


@admin_bp.route("/magic-link/consume", methods=["GET"])
def admin_magic_link_consume() -> Any:
    _abort_if_admin_login_disabled()
    _bootstrap_admins()
    token = request.args.get("token", "")
    if not token:
        abort(400)

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn = _db()
    row = conn.execute(
        "SELECT token_hash, email, expires_at, used_at FROM admin_magic_links WHERE token_hash=?",
        (token_hash,),
    ).fetchone()

    if row is None:
        conn.close()
        return render_template("admin_login.html", providers=_provider_configs(), email_enabled=email_configured(), error="Magic link is invalid."), 403

    if row["used_at"]:
        conn.close()
        return render_template("admin_login.html", providers=_provider_configs(), email_enabled=email_configured(), error="Magic link was already used."), 403

    if datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC):
        conn.close()
        return render_template("admin_login.html", providers=_provider_configs(), email_enabled=email_configured(), error="Magic link has expired."), 403

    email = _normalize_email(row["email"])
    if not _is_approved_admin(email):
        conn.close()
        return render_template("admin_login.html", providers=_provider_configs(), email_enabled=email_configured(), error="Admin approval is required."), 403

    conn.execute(
        "UPDATE admin_magic_links SET used_at=? WHERE token_hash=?",
        (_utc_now(), token_hash),
    )
    conn.commit()
    conn.close()

    session.clear()
    session["admin_email"] = email
    return redirect(url_for("admin.admin_queue"))


def _oauth_provider_by_key(key: str) -> _ProviderConfig | None:
    for provider in _provider_configs():
        if provider.key == key:
            return provider
    return None


@admin_bp.route("/oauth/start/<provider_key>", methods=["GET"])
def admin_oauth_start(provider_key: str) -> Any:
    _abort_if_admin_login_disabled()
    _bootstrap_admins()
    if not email_configured():
        return redirect(url_for("admin.admin_login"))

    provider = _oauth_provider_by_key(provider_key)
    if provider is None:
        abort(404)

    state = secrets.token_urlsafe(24)
    session["admin_oauth_state"] = {"state": state, "provider": provider.key}

    params = {
        "client_id": provider.client_id,
        "redirect_uri": url_for("admin.admin_oauth_callback", provider_key=provider.key, _external=True),
        "response_type": "code",
        "scope": provider.scope,
        "state": state,
    }

    return redirect(f"{provider.auth_url}?{urlencode(params)}")


@admin_bp.route("/oauth/callback/<provider_key>", methods=["GET"])
def admin_oauth_callback(provider_key: str) -> Any:
    _abort_if_admin_login_disabled()
    _bootstrap_admins()
    provider = _oauth_provider_by_key(provider_key)
    if provider is None:
        abort(404)

    state_payload = session.get("admin_oauth_state") or {}
    expected_state = state_payload.get("state", "")
    expected_provider = state_payload.get("provider", "")
    given_state = request.args.get("state", "")
    if not expected_state or not hmac.compare_digest(given_state, expected_state) or expected_provider != provider.key:
        return render_template("admin_login.html", providers=_provider_configs(), email_enabled=email_configured(), error="OAuth state mismatch. Please try again."), 403

    code = request.args.get("code", "")
    if not code:
        return render_template("admin_login.html", providers=_provider_configs(), email_enabled=email_configured(), error="OAuth callback did not include a code."), 400

    token_resp = requests.post(
        provider.token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "redirect_uri": url_for("admin.admin_oauth_callback", provider_key=provider.key, _external=True),
        },
        headers={"Accept": "application/json"},
        timeout=10,
    )
    if token_resp.status_code >= 400:
        return render_template("admin_login.html", providers=_provider_configs(), email_enabled=email_configured(), error="OAuth token exchange failed."), 403

    try:
        token_payload = token_resp.json()
    except Exception:
        return render_template("admin_login.html", providers=_provider_configs(), email_enabled=email_configured(), error="OAuth provider returned an unexpected response."), 502

    access_token = token_payload.get("access_token", "")
    id_token = token_payload.get("id_token", "")

    email = ""
    if access_token and provider.userinfo_url:
        user_resp = requests.get(
            provider.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            timeout=10,
        )
        if user_resp.status_code < 400:
            try:
                user_data = user_resp.json()
            except Exception:
                user_data = {}
            email = _normalize_email(user_data.get(provider.email_field, ""))

            if provider.key == "github" and not email:
                email_resp = requests.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                    timeout=10,
                )
                if email_resp.status_code < 400:
                    try:
                        email_list = email_resp.json()
                    except Exception:
                        email_list = []
                    for item in email_list:
                        if item.get("primary") and item.get("verified"):
                            email = _normalize_email(item.get("email", ""))
                            break

    if not email and id_token:
        email = _decode_jwt_email(id_token)

    if not email:
        return render_template("admin_login.html", providers=_provider_configs(), email_enabled=email_configured(), error="Could not determine account email from OAuth provider."), 403

    if not _is_approved_admin(email):
        return render_template(
            "admin_login.html",
            providers=_provider_configs(),
            email_enabled=email_configured(),
            error="This account is not approved for admin access. Please request access.",
            ttl_minutes=_MAGIC_LINK_TTL_MINUTES,
        ), 403

    # Prevent session fixation: drop any pre-login session before elevating.
    session.clear()
    session["admin_email"] = email
    return redirect(url_for("admin.admin_queue"))


@admin_bp.route("/queue", methods=["GET"])
def admin_queue() -> Any:
    email = _require_admin()
    rows = get_admin_queue_snapshot()
    return render_template(
        "admin_queue.html",
        admin_email=email,
        rows=rows,
        email_status=email_status(),
        email_notice=request.args.get("email_notice", "").strip(),
        email_error=request.args.get("email_error", "").strip(),
    )


@admin_bp.route("/email/test", methods=["POST"])
@limiter.limit("6 per hour")
def admin_email_test() -> Any:
    """Send one test message, to prove the mail path in production.

    Seven features depend on a single Postmark token -- audit delivery,
    Whisperer notifications, admin sign-in links, and three workshop
    features. Until now the only way to know whether it worked was to
    trigger one of them and wait. The usual failure is not "no mail" but
    "mail the recipient's domain silently rejects", which nobody notices
    until the day it matters.
    """
    admin_email = _require_admin()
    target = (request.form.get("test_email") or "").strip() or admin_email

    if not email_configured():
        return redirect(
            url_for(
                "admin.admin_queue",
                email_error="POSTMARK_SERVER_TOKEN is not set, so nothing can be sent.",
            )
        )

    ok, detail = send_test_email(target, requested_by=admin_email)
    if ok:
        return redirect(
            url_for("admin.admin_queue", email_notice=f"Test email sent to {target}.")
        )
    return redirect(url_for("admin.admin_queue", email_error=detail))


@admin_bp.route("/speech", methods=["GET"])
def admin_speech() -> Any:
    email = _require_admin()
    status = get_engine_status()
    voices = get_piper_voice_inventory()
    return render_template(
        "admin_speech.html",
        admin_email=email,
        engine_status=status,
        voices=voices,
        notice=request.args.get("notice"),
        error=request.args.get("error"),
    )


@admin_bp.route("/speech/install/<voice_id>", methods=["POST"])
def admin_speech_install(voice_id: str) -> Any:
    _require_admin()
    ok, msg = install_piper_voice(voice_id)
    return redirect(
        url_for("admin.admin_speech", notice=msg if ok else None, error=None if ok else msg)
    )


@admin_bp.route("/speech/remove/<voice_id>", methods=["POST"])
def admin_speech_remove(voice_id: str) -> Any:
    _require_admin()
    ok, msg = remove_piper_voice(voice_id)
    return redirect(
        url_for("admin.admin_speech", notice=msg if ok else None, error=None if ok else msg)
    )


@admin_bp.route("/ai", methods=["GET", "POST"])
def admin_ai_settings() -> Any:
    """Admin AI configuration panel (model routing, budget, quotas)."""
    email = _require_admin()
    notice = None
    error = None

    if request.method == "POST":
        try:
            updates = {
                "default_model": (request.form.get("default_model") or "").strip(),
                "fallback_model": (request.form.get("fallback_model") or "").strip(),
                "vision_model": (request.form.get("vision_model") or "").strip(),
                "escalation_thresh": float(request.form.get("escalation_thresh") or "0.7"),
                "monthly_budget_usd": float(request.form.get("monthly_budget_usd") or "20"),
                "chat_daily_limit": int(request.form.get("chat_daily_limit") or "50"),
                "audio_monthly_min": int(request.form.get("audio_monthly_min") or "100"),
                "session_quota_per_session": int(request.form.get("session_quota_per_session") or "0"),
                "quota_reset_hours": int(request.form.get("quota_reset_hours") or "24"),
                "whisper_model": (request.form.get("whisper_model") or "openai/whisper-large-v3").strip(),
            }

            if request.form.get("use_free_defaults") == "on":
                updates["default_model"] = "openai/gpt-4o-mini"
                updates["fallback_model"] = "openai/gpt-4o"
            if updates["escalation_thresh"] < 0 or updates["escalation_thresh"] > 1:
                raise ValueError("Escalation threshold must be between 0.0 and 1.0")
            if updates["monthly_budget_usd"] <= 0:
                raise ValueError("Monthly budget must be greater than 0")
            if updates["chat_daily_limit"] < 0:
                raise ValueError("Chat daily limit cannot be negative")
            if updates["audio_monthly_min"] < 0:
                raise ValueError("Audio monthly limit cannot be negative")
            if updates["session_quota_per_session"] < 0:
                raise ValueError("Session AI request limit cannot be negative")
            if updates["quota_reset_hours"] <= 0:
                raise ValueError("Session quota reset hours must be greater than 0")
            if not updates["default_model"]:
                raise ValueError("Default model is required")
            if not updates["fallback_model"]:
                raise ValueError("Fallback model is required")
            if not updates["vision_model"]:
                updates["vision_model"] = updates["fallback_model"]

            update_runtime_config(updates)
            notice = "AI settings saved. Changes apply immediately."
        except Exception as exc:
            error = f"Could not save settings: {exc}"

    cfg = get_runtime_config()
    stats = get_admin_stats()
    models = get_model_catalog()
    projection = project_monthly_cost(
        model_id=str(cfg.get("default_model", "openai/gpt-4o-mini")),
        monthly_requests=10000,
        avg_input_tokens=1200,
        avg_output_tokens=400,
    )
    return render_template(
        "admin_ai.html",
        admin_email=email,
        cfg=cfg,
        stats=stats,
        models=models,
        projection=projection,
        notice=notice,
        error=error,
    )


@admin_bp.route("/ai/pricing", methods=["GET"])
def admin_ai_pricing() -> Any:
    """Live pricing and projection API for the admin AI settings page."""
    _require_admin()
    model_id = (request.args.get("model") or "").strip()
    try:
        monthly_requests = int(request.args.get("monthly_requests") or "10000")
        avg_input_tokens = int(request.args.get("avg_input_tokens") or "1200")
        avg_output_tokens = int(request.args.get("avg_output_tokens") or "400")
    except ValueError:
        return jsonify({"error": "Invalid numeric query params"}), 400

    models = get_model_catalog()
    selected = next((m for m in models if m.get("id") == model_id), None)
    if selected is None and models:
        selected = models[0]
        model_id = str(selected.get("id", ""))

    projected = project_monthly_cost(model_id, monthly_requests, avg_input_tokens, avg_output_tokens)
    return jsonify(
        {
            "model": selected,
            "projection": {
                "monthly_requests": monthly_requests,
                "avg_input_tokens": avg_input_tokens,
                "avg_output_tokens": avg_output_tokens,
                "projected_monthly_usd": projected,
            },
            "models": models,
        }
    )



@admin_bp.route("/flags", methods=["GET", "POST"])
def admin_flags() -> Any:
    """Admin panel to view and manipulate server-side feature flags."""
    email = _require_admin()
    notice = None
    error = None

    feature_keys = [
        # Master and AI subfeatures
        "GLOW_ENABLE_AI",
        "GLOW_ENABLE_AI_GENERAL_CHAT",
        "GLOW_ENABLE_AI_CHAT",
        "GLOW_ENABLE_AI_WHISPERER",
        "GLOW_ENABLE_AI_HEADING_FIX",
        "GLOW_ENABLE_AI_ALT_TEXT",
        "GLOW_ENABLE_AI_MARKITDOWN_LLM",
        # Core GLOW features (non-AI)
        "GLOW_ENABLE_AUDIT",
        "GLOW_ENABLE_CHECKER",
        "GLOW_ENABLE_HEADING_DETECTION",
        "GLOW_ENABLE_CONVERTER",
        "GLOW_ENABLE_TEMPLATE_BUILDER",
        "GLOW_ENABLE_WORD_SETUP",
        "GLOW_ENABLE_MARKDOWN_AUDIT",
        # Document type flags
        "GLOW_ENABLE_WORD",
        "GLOW_ENABLE_EXCEL",
        "GLOW_ENABLE_POWERPOINT",
        "GLOW_ENABLE_PDF",
        "GLOW_ENABLE_MARKDOWN",
        "GLOW_ENABLE_EPUB",
        # Export / conversion capabilities
        "GLOW_ENABLE_EXPORT_HTML",
        "GLOW_ENABLE_EXPORT_PDF",
        "GLOW_ENABLE_EXPORT_WORD",
        "GLOW_ENABLE_EXPORT_MARKDOWN",
        # Convert direction subfeatures
        "GLOW_ENABLE_CONVERT_TO_MARKDOWN",
        "GLOW_ENABLE_CONVERT_TO_HTML",
        "GLOW_ENABLE_CONVERT_TO_DOCX",
        "GLOW_ENABLE_CONVERT_TO_EPUB",
        "GLOW_ENABLE_CONVERT_TO_PDF",
        "GLOW_ENABLE_CONVERT_TO_PIPELINE",
        # Speech export / convert subfeatures
        "GLOW_ENABLE_EXPORT_SPEECH",
        "GLOW_ENABLE_CONVERT_TO_SPEECH",
        # Braille export / convert subfeatures
        "GLOW_ENABLE_EXPORT_BRAILLE",
        "GLOW_ENABLE_CONVERT_TO_BRAILLE",
        # Roadmap feature switches
        "GLOW_ENABLE_BRAILLE_BACK_TRANSLATION_SCORE",
        "GLOW_ENABLE_SPEECH_PRONUNCIATION_DICTIONARY",
        "GLOW_ENABLE_SPEECH_STREAM",
        "GLOW_ENABLE_TABLE_ADVISOR",
        "GLOW_ENABLE_READING_ORDER_DETECTION",
        "GLOW_ENABLE_PDF_OCR",
        "GLOW_ENABLE_DOCUMENT_COMPARE",
        "GLOW_ENABLE_CONVERT_TO_ODT",
        "GLOW_ENABLE_COGNITIVE_PROFILE",
        "GLOW_ENABLE_FORCED_COLORS_MODE",
        "GLOW_ENABLE_RULE_CONTRIBUTIONS",
        "GLOW_ENABLE_SITE_AUDIT",
        "GLOW_ENABLE_WCAG_LANGUAGE_PROCESSING",
        "GLOW_ENABLE_WCAG_LANGUAGE_STRICT_MODE",
        "GLOW_ENABLE_PII_GUARDRAILS",
        "GLOW_ENABLE_PII_GUARDRAILS_STRICT_MODE",
        # Optional tool integrations
        "GLOW_ENABLE_PANDOC",
        "GLOW_ENABLE_WEASYPRINT",
        "GLOW_ENABLE_PYMUPDF",
        "GLOW_ENABLE_MARKITDOWN",
        "GLOW_ENABLE_DAISY_ACE",
        "GLOW_ENABLE_DAISY_META_VIEWER",
        "GLOW_ENABLE_DAISY_PIPELINE",
        "GLOW_ENABLE_EPUBCHECK",
        "GLOW_ENABLE_PYDOCX",
        "GLOW_ENABLE_OPENPYXL",
        "GLOW_ENABLE_PYTHON_PPTX",
    ]

    # Group keys for template rendering
    categories = {
        "ai": [
            "GLOW_ENABLE_AI",
            "GLOW_ENABLE_AI_GENERAL_CHAT",
            "GLOW_ENABLE_AI_CHAT",
            "GLOW_ENABLE_AI_WHISPERER",
            "GLOW_ENABLE_AI_HEADING_FIX",
            "GLOW_ENABLE_AI_ALT_TEXT",
            "GLOW_ENABLE_AI_MARKITDOWN_LLM",
            "GLOW_ENABLE_PII_GUARDRAILS",
            "GLOW_ENABLE_PII_GUARDRAILS_STRICT_MODE",
        ],
        "core": [
            "GLOW_ENABLE_AUDIT",
            "GLOW_ENABLE_CHECKER",
            "GLOW_ENABLE_HEADING_DETECTION",
            "GLOW_ENABLE_SITE_AUDIT",
            "GLOW_ENABLE_COGNITIVE_PROFILE",
            "GLOW_ENABLE_FORCED_COLORS_MODE",
            "GLOW_ENABLE_RULE_CONTRIBUTIONS",
            "GLOW_ENABLE_WCAG_LANGUAGE_PROCESSING",
            "GLOW_ENABLE_WCAG_LANGUAGE_STRICT_MODE",
        ],
        "conversion": [
            "GLOW_ENABLE_CONVERTER",
            "GLOW_ENABLE_TEMPLATE_BUILDER",
            "GLOW_ENABLE_WORD_SETUP",
            "GLOW_ENABLE_MARKDOWN_AUDIT",
            "GLOW_ENABLE_TABLE_ADVISOR",
            "GLOW_ENABLE_READING_ORDER_DETECTION",
            "GLOW_ENABLE_PDF_OCR",
            "GLOW_ENABLE_DOCUMENT_COMPARE",
        ],
        "documents": [
            "GLOW_ENABLE_WORD",
            "GLOW_ENABLE_EXCEL",
            "GLOW_ENABLE_POWERPOINT",
            "GLOW_ENABLE_PDF",
            "GLOW_ENABLE_MARKDOWN",
            "GLOW_ENABLE_EPUB",
        ],
        "exports": [
            "GLOW_ENABLE_EXPORT_HTML",
            "GLOW_ENABLE_EXPORT_PDF",
            "GLOW_ENABLE_EXPORT_WORD",
            "GLOW_ENABLE_EXPORT_MARKDOWN",
            "GLOW_ENABLE_EXPORT_SPEECH",
            "GLOW_ENABLE_EXPORT_BRAILLE",
            "GLOW_ENABLE_SPEECH_STREAM",
        ],
        "convert_subfeatures": [
            "GLOW_ENABLE_CONVERT_TO_MARKDOWN",
            "GLOW_ENABLE_CONVERT_TO_HTML",
            "GLOW_ENABLE_CONVERT_TO_DOCX",
            "GLOW_ENABLE_CONVERT_TO_ODT",
            "GLOW_ENABLE_CONVERT_TO_EPUB",
            "GLOW_ENABLE_CONVERT_TO_PDF",
            "GLOW_ENABLE_CONVERT_TO_PIPELINE",
            "GLOW_ENABLE_CONVERT_TO_SPEECH",
            "GLOW_ENABLE_CONVERT_TO_BRAILLE",
        ],
        "integrations": [
            "GLOW_ENABLE_BRAILLE_BACK_TRANSLATION_SCORE",
            "GLOW_ENABLE_SPEECH_PRONUNCIATION_DICTIONARY",
            "GLOW_ENABLE_PANDOC",
            "GLOW_ENABLE_WEASYPRINT",
            "GLOW_ENABLE_PYMUPDF",
            "GLOW_ENABLE_MARKITDOWN",
            "GLOW_ENABLE_DAISY_ACE",
            "GLOW_ENABLE_DAISY_META_VIEWER",
            "GLOW_ENABLE_DAISY_PIPELINE",
            "GLOW_ENABLE_EPUBCHECK",
            "GLOW_ENABLE_PYDOCX",
            "GLOW_ENABLE_OPENPYXL",
            "GLOW_ENABLE_PYTHON_PPTX",
        ],
    }

    if request.method == "POST":
        try:
            if request.form.get("reset_defaults") == "on":
                _reset_flag_defaults()
                notice = "Feature flags reset to defaults."
            else:
                posted = {k: request.form.get(k) == "on" for k in feature_keys}

                # Cascade: if master AI is off, ensure all AI subfeatures are off.
                if not posted.get("GLOW_ENABLE_AI", False):
                    for child in [
                        "GLOW_ENABLE_AI_GENERAL_CHAT",
                        "GLOW_ENABLE_AI_CHAT",
                        "GLOW_ENABLE_AI_WHISPERER",
                        "GLOW_ENABLE_AI_HEADING_FIX",
                        "GLOW_ENABLE_AI_ALT_TEXT",
                        "GLOW_ENABLE_AI_MARKITDOWN_LLM",
                    ]:
                        posted[child] = False

                for k, v in posted.items():
                    # Record who changed the flag for auditing
                    _set_flag(k, v, changed_by=email)
                notice = "Feature flags updated."
        except Exception as exc:
            error = f"Could not update flags: {exc}"

    flags = _get_all_flags()
    # Collect metadata per-flag for display
    metas = {k: _get_flag_meta(k) for k in feature_keys}
    backend = _get_flags_backend()
    # Collect recent audit rows for display (best-effort)
    audit_rows: list[dict[str, Any]] = []
    try:
        for k in feature_keys:
            audit_rows.extend(_get_audit_entries(k, limit=10))
        # sort by changed_at desc and keep recent 200
        audit_rows = sorted(audit_rows, key=lambda r: r.get("changed_at") or "", reverse=True)[:200]
    except Exception:
        audit_rows = []
    return render_template(
        "admin_flags.html",
        admin_email=email,
        flags=flags,
        flag_meta=metas,
        flags_backend=backend,
        audit_rows=audit_rows,
        feature_keys=feature_keys,
        categories=categories,
        notice=notice,
        error=error,
    )



@admin_bp.route("/flags/migrate", methods=["POST"])
def admin_flags_migrate() -> Any:
    """Trigger a JSON->SQLite migration helper (idempotent) from the UI."""
    _require_admin()
    notice = None
    error = None
    try:
        _migrate_flags()
        notice = "Feature flags migrated (if JSON data present)."
    except Exception as exc:
        error = f"Migration failed: {exc}"

    return redirect(url_for("admin.admin_flags", notice=notice, error=error))


@admin_bp.route("/queue/cancel/<job_id>", methods=["POST"])
def admin_queue_cancel(job_id: str) -> Any:
    _require_admin()
    ok, msg = admin_cancel_queued_job(job_id)
    return redirect(url_for("admin.admin_queue", notice=msg if ok else None, error=None if ok else msg))


@admin_bp.route("/queue/requeue/<job_id>", methods=["POST"])
def admin_queue_requeue(job_id: str) -> Any:
    _require_admin()
    ok, msg = admin_requeue_failed_job(job_id)
    return redirect(url_for("admin.admin_queue", notice=msg if ok else None, error=None if ok else msg))


@admin_bp.route("/requests", methods=["GET"])
def admin_requests() -> Any:
    email = _require_admin()
    rows = _pending_requests()
    return render_template("admin_requests.html", admin_email=email, rows=rows)


def _ensure_account(email: str, display_name: str | None = None) -> None:
    conn = _db()
    conn.execute(
        "INSERT INTO admin_accounts (email, display_name, approved, created_at, approved_at, approved_by) "
        "VALUES (?, ?, 0, ?, NULL, NULL) "
        "ON CONFLICT(email) DO NOTHING",
        (email, display_name or email, _utc_now()),
    )
    conn.commit()
    conn.close()


@admin_bp.route("/requests/approve/<int:req_id>", methods=["POST"])
def admin_approve_request(req_id: int) -> Any:
    reviewer = _require_admin()
    conn = _db()
    row = conn.execute(
        "SELECT id, email, display_name, status FROM admin_requests WHERE id=?",
        (req_id,),
    ).fetchone()
    if row is None:
        conn.close()
        abort(404)

    if row["status"] != "pending":
        conn.close()
        return redirect(url_for("admin.admin_requests"))

    _ensure_account(_normalize_email(row["email"]), row["display_name"])
    now = _utc_now()
    conn.execute(
        "UPDATE admin_accounts SET approved=1, approved_at=?, approved_by=? WHERE email=?",
        (now, reviewer, _normalize_email(row["email"])),
    )
    conn.execute(
        "UPDATE admin_requests SET status='approved', reviewed_at=?, reviewed_by=? WHERE id=?",
        (now, reviewer, req_id),
    )
    conn.commit()
    conn.close()

    if email_configured():
        _send_admin_email(
            _normalize_email(row["email"]),
            "GLOW admin access approved",
            (
                "<p>Your admin access request has been approved.</p>"
                f"<p>Sign in here: <a href=\"{url_for('admin.admin_login', _external=True)}\">Admin login</a></p>"
            ),
            f"Your admin access request has been approved. Sign in at {url_for('admin.admin_login', _external=True)}",
        )

    return redirect(url_for("admin.admin_requests"))


@admin_bp.route("/analytics", methods=["GET"])
def admin_analytics() -> Any:
    """Tool usage analytics dashboard."""
    email = _require_admin()
    from ..tool_usage import (
        get_all as _get_tool_usage,
        get_detail_counts as _get_detail_counts,
        get_total as _get_tool_total,
    )
    from ..visitor_counter import get_count as _get_visitor_count
    from ..speech_metrics import get_summary as _get_speech_metrics_summary
    usage = _get_tool_usage()
    total_uses = _get_tool_total()
    visitor_count = _get_visitor_count()
    return render_template(
        "admin_analytics.html",
        admin_email=email,
        usage=usage,
        total_uses=total_uses,
        visitor_count=visitor_count,
        speech_metrics_summary=_get_speech_metrics_summary(),
        anthem_downloads=_get_detail_counts("anthem_download", "detail", limit=1),
        speech_modes=_get_detail_counts("speech", "mode", limit=20),
        speech_voices=_get_detail_counts("speech", "voice", limit=20),
        speech_speeds=_get_detail_counts("speech", "speed", limit=20),
        speech_pitches=_get_detail_counts("speech", "pitch", limit=20),
    )


@admin_bp.route("/requests/deny/<int:req_id>", methods=["POST"])
def admin_deny_request(req_id: int) -> Any:
    reviewer = _require_admin()
    conn = _db()
    row = conn.execute(
        "SELECT id, email, status FROM admin_requests WHERE id=?",
        (req_id,),
    ).fetchone()
    if row is None:
        conn.close()
        abort(404)

    if row["status"] == "pending":
        conn.execute(
            "UPDATE admin_requests SET status='denied', reviewed_at=?, reviewed_by=? WHERE id=?",
            (_utc_now(), reviewer, req_id),
        )
        conn.commit()
    conn.close()

    if row["status"] == "pending" and email_configured():
        _send_admin_email(
            _normalize_email(row["email"]),
            "GLOW admin access request update",
            "<p>Your admin access request was reviewed and is not approved at this time.</p>",
            "Your admin access request was reviewed and is not approved at this time.",
        )

    return redirect(url_for("admin.admin_requests"))
