"""Regression tests for the confirmed findings fixed in this pass.

Covers feature-flag persistence/seeding, atomic writes and corruption
fallback, rate-limiter storage selection, session-cookie hardening, admin
session fixation, request-log redaction, share-cache retention, the cleanup
lock wedge, and report_cache TTL/token guards.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from acb_large_print_web.app import create_app


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("FLASK_INSTANCE_PATH", str(tmp_path / "instance"))
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    return application


# ---------------------------------------------------------------------------
# Finding 1 + 3: seed only when the real store is empty (sqlite backend)
# ---------------------------------------------------------------------------
def test_sqlite_seed_gate_does_not_clobber_admin_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("FLASK_INSTANCE_PATH", str(tmp_path / "instance"))
    from acb_large_print_web import feature_flags as ff

    monkeypatch.setattr(ff, "_BACKEND", "sqlite")
    ff._SCHEMA_READY_PATHS.clear()

    app1 = create_app({"TESTING": True})
    with app1.app_context():
        # First boot seeds defaults into the sqlite store.
        assert ff.has_any_persisted() is True
        ff.set_flag("GLOW_ENABLE_AUDIT", False)

    # A worker respawn / restart must NOT re-seed over the admin's change.
    app2 = create_app({"TESTING": True})
    with app2.app_context():
        assert ff.get_flag("GLOW_ENABLE_AUDIT") is False
        # The sqlite backend never writes feature_flags.json; the old guard
        # keyed on that file and therefore re-seeded on every restart.
        assert not (tmp_path / "instance" / "feature_flags.json").exists()


def test_has_any_persisted_json(app):
    from acb_large_print_web import feature_flags as ff

    with app.app_context():
        # The app fixture seeds on startup, so the json store is populated.
        assert ff.has_any_persisted() is True
        ff._path().unlink()
        assert ff.has_any_persisted() is False
        ff._path().write_text("", encoding="utf-8")
        # Empty file must count as "not persisted".
        assert ff.has_any_persisted() is False


# ---------------------------------------------------------------------------
# Finding 2: atomic write + corruption fallback to last-known-good
# ---------------------------------------------------------------------------
def test_corrupt_json_falls_back_to_last_known_good(app):
    from acb_large_print_web import feature_flags as ff

    with app.app_context():
        ff.set_flag("GLOW_ENABLE_AUDIT", False)
        assert ff.get_flag("GLOW_ENABLE_AUDIT") is False

        p = ff._path()
        # No stray temp file should survive an atomic write.
        assert list(p.parent.glob("feature_flags.json.*.tmp")) == []

        # Truncate/corrupt the store on disk.
        p.write_text("{ this is not valid json", encoding="utf-8")

        # Must return the last-known-good value (False), not the compiled
        # default (True) which would silently re-enable the feature.
        assert ff.get_flag("GLOW_ENABLE_AUDIT") is False


# ---------------------------------------------------------------------------
# Finding 4: rate-limiter storage selection
# ---------------------------------------------------------------------------
def test_rate_limit_storage_uri_prefers_env(monkeypatch):
    from acb_large_print_web import app as app_mod

    for var in ("RATELIMIT_STORAGE_URI", "REDIS_URL", "CELERY_BROKER_URL"):
        monkeypatch.delenv(var, raising=False)
    assert app_mod._rate_limit_storage_uri() == "memory://"

    monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker:6379/0")
    assert app_mod._rate_limit_storage_uri() == "redis://broker:6379/0"

    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "redis://limits:6379/1")
    assert app_mod._rate_limit_storage_uri() == "redis://limits:6379/1"


# ---------------------------------------------------------------------------
# Finding 5: session cookie hardening
# ---------------------------------------------------------------------------
def test_session_cookie_flags_dev_vs_prod(tmp_path, monkeypatch):
    monkeypatch.setenv("FLASK_INSTANCE_PATH", str(tmp_path / "instance"))
    for var in ("FLASK_ENV", "FLASK_DEBUG", "GLOW_DEV"):
        monkeypatch.delenv(var, raising=False)

    testing_app = create_app({"TESTING": True})
    assert testing_app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert testing_app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    # Local/test runs over HTTP must not set Secure or the cookie is dropped.
    assert testing_app.config["SESSION_COOKIE_SECURE"] is False

    prod_app = create_app({})
    assert prod_app.config["SESSION_COOKIE_SECURE"] is True


# ---------------------------------------------------------------------------
# Finding 6: session fixation on password login
# ---------------------------------------------------------------------------
def test_password_login_clears_prior_session(tmp_path, monkeypatch):
    monkeypatch.setenv("FLASK_INSTANCE_PATH", str(tmp_path / "instance"))
    monkeypatch.setenv("ADMIN_LOCAL_EMAIL", "local-admin@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "sup3r-secret-pw")
    monkeypatch.setenv("ADMIN_BOOTSTRAP_EMAILS", "local-admin@example.com")

    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    client = application.test_client()

    with client.session_transaction() as sess:
        sess["stale_marker"] = "pre-login-value"

    resp = client.post(
        "/admin/login/password",
        data={"email": "local-admin@example.com", "password": "sup3r-secret-pw"},
    )
    assert resp.status_code == 302
    assert "/admin/queue" in resp.location

    with client.session_transaction() as sess:
        assert "stale_marker" not in sess
        assert sess.get("admin_email") == "local-admin@example.com"


# ---------------------------------------------------------------------------
# Finding 7: request-log query redaction
# ---------------------------------------------------------------------------
def test_redacted_request_target_masks_secrets(app):
    from acb_large_print_web.app import _redacted_request_target
    from flask import request

    qs = "access=AAA&p=BBB&token=CCC&key=DDD&password=EEE&foo=keepme"
    with app.test_request_context(f"/site-audit?{qs}"):
        out = _redacted_request_target(request)

    for secret in ("AAA", "BBB", "CCC", "DDD", "EEE"):
        assert secret not in out
    assert out.startswith("/site-audit?")
    assert "access=REDACTED" in out
    assert "foo=keepme" in out


# ---------------------------------------------------------------------------
# Finding 8: cleanup must not delete the long-lived shares/ dir
# ---------------------------------------------------------------------------
def test_cleanup_stale_uploads_preserves_shares(tmp_path, monkeypatch):
    from acb_large_print_web import upload

    monkeypatch.setattr(upload, "UPLOAD_TEMP_BASE", tmp_path)

    shares = tmp_path / "shares"
    shares.mkdir()
    (shares / "keep.txt").write_text("still valid share", encoding="utf-8")
    old_upload = tmp_path / "12345678-1234-1234-1234-123456789abc"
    old_upload.mkdir()

    past = time.time() - 3 * 3600
    os.utime(shares, (past, past))
    os.utime(old_upload, (past, past))

    cleaned = upload.cleanup_stale_uploads(max_age_hours=1)

    assert shares.exists() and (shares / "keep.txt").exists()
    assert not old_upload.exists()
    assert cleaned == 1


# ---------------------------------------------------------------------------
# Finding 9: cleanup lock recovers from a stale temp file
# ---------------------------------------------------------------------------
def test_cleanup_lock_recovers_from_stale_tmp(app):
    inst = Path(app.instance_path)
    inst.mkdir(parents=True, exist_ok=True)
    stale_tmp = inst / ".cleanup_lock.tmp"
    stale_tmp.write_text("999")
    past = time.time() - 600
    os.utime(stale_tmp, (past, past))

    client = app.test_client()
    client.get("/health")

    # The sweep must have run and produced the real lock file rather than
    # wedging forever on the abandoned temp file.
    assert (inst / ".cleanup_lock").exists()


# ---------------------------------------------------------------------------
# Finding 10: report_cache TTL guard + save_report token validation
# ---------------------------------------------------------------------------
def test_share_ttl_non_numeric_defaults(monkeypatch):
    from acb_large_print_web import report_cache

    monkeypatch.setenv("SHARE_TTL_HOURS", "not-a-number")
    assert report_cache._resolve_share_ttl_seconds() == 4 * 3600

    monkeypatch.setenv("SHARE_TTL_HOURS", "6")
    assert report_cache._resolve_share_ttl_seconds() == 6 * 3600


def test_save_report_rejects_bad_token(tmp_path, monkeypatch):
    from acb_large_print_web import report_cache

    base = tmp_path / "shares"
    monkeypatch.setattr(report_cache, "_SHARE_BASE", base)

    report_cache.save_report("../evil", "<html>evil</html>")
    # A traversal token must not create anything on disk.
    assert not base.exists() or list(base.iterdir()) == []

    good = "12345678-1234-1234-1234-123456789abc"
    report_cache.save_report(good, "<html>ok</html>")
    assert (base / good / "report.html").read_text(encoding="utf-8") == "<html>ok</html>"
