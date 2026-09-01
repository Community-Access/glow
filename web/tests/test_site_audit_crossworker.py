"""Cross-worker job-store tests for the Site Audit background jobs.

Under gunicorn's 2 worker processes the in-memory ``_jobs`` dict only exists in
the process that accepted the submit; a follow-up request that lands on the
OTHER worker used to see an empty dict and 404. These tests simulate the "other
worker" by persisting a job to the shared status file and then clearing the
in-memory ``_jobs`` cache, proving the endpoints still serve the job, that a
cancel issued cross-worker is observed, and that a crafted job_id cannot
traverse out of the job-store root.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
import acb_large_print_web.routes.site_audit as site_audit_route
import acb_large_print_web.site_audit as site_audit


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
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


def _make_job(job_id: str, run_id: str, **overrides) -> site_audit_route._SiteAuditJob:
    kwargs = dict(
        job_id=job_id,
        run_id=run_id,
        status="running",
        progress=42,
        message="Scanning 3/10: https://example.com/x",
        attempt=1,
        max_attempts=2,
        deadline_at=9999999999.0,
        created_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        sources=("https://example.com",),
        options=site_audit.SiteAuditOptions(max_pages=10, crawl_depth=2),
    )
    kwargs.update(overrides)
    return site_audit_route._SiteAuditJob(**kwargs)


def test_status_endpoint_served_from_shared_store(client, app):
    # A job written by "one worker" is still found after the local cache is empty.
    job_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    with app.app_context():
        site_audit_route._persist_job(_make_job(job_id, run_id))
    site_audit_route._jobs.clear()  # simulate the request landing on the other worker

    res = client.get(f"/site-audit/jobs/{job_id}/status")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["job_id"] == job_id
    assert payload["run_id"] == run_id
    assert payload["status"] == "running"
    assert payload["progress"] == 42
    assert payload["attempt"] == 1
    assert payload["max_attempts"] == 2


def test_job_page_served_from_shared_store(client, app):
    job_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    with app.app_context():
        site_audit_route._persist_job(_make_job(job_id, run_id))
    site_audit_route._jobs.clear()

    res = client.get(f"/site-audit/jobs/{job_id}")
    assert res.status_code == 200


def test_unknown_uuid_still_404s(client):
    site_audit_route._jobs.clear()
    res = client.get(f"/site-audit/jobs/{uuid.uuid4()}/status")
    assert res.status_code == 404


def test_cancel_via_shared_flag_is_observed(client, app):
    # A cancel issued where the job is NOT in local memory must land in the shared
    # store so a worker in another process observes it via _shared_cancel_requested.
    job_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    with app.app_context():
        site_audit_route._persist_job(_make_job(job_id, run_id))
    site_audit_route._jobs.clear()

    res = client.post(f"/site-audit/jobs/{job_id}/cancel")
    assert res.status_code == 302

    with app.app_context():
        assert site_audit_route._shared_cancel_requested(job_id) is True
        data = site_audit_route._read_job_status(job_id)
        assert data is not None
        assert data["status"] == "cancelled"
        assert data["cancelled"] is True


def test_protected_job_uses_hash_not_plaintext_token(client, app):
    # The plaintext token is never written to disk; access is still enforced when
    # the job is served from the shared store.
    job_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    token = "plaintext-secret-token"
    with app.app_context():
        job = _make_job(job_id, run_id, access_token_hash=site_audit_route._hash_token(token))
        site_audit_route._persist_job(job)
        status_path = site_audit_route._job_status_path(job_id, create=False)
    site_audit_route._jobs.clear()

    # The status file holds the hash, never the plaintext token.
    raw = status_path.read_text(encoding="utf-8")
    assert token not in raw
    assert site_audit_route._hash_token(token) in raw

    denied = client.get(f"/site-audit/jobs/{job_id}/status")
    assert denied.status_code == 403

    allowed = client.get(f"/site-audit/jobs/{job_id}/status?access={token}")
    assert allowed.status_code == 200
    assert allowed.get_json()["job_id"] == job_id


def test_retry_loads_job_from_shared_store(client, app, monkeypatch):
    # Retry must work even when the job only exists in the shared store (the
    # retry then runs in whichever worker received the request).
    job_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    with app.app_context():
        site_audit_route._persist_job(
            _make_job(job_id, run_id, status="failed", error="boom", attempt=1, max_attempts=2)
        )
    site_audit_route._jobs.clear()

    started: list[str] = []
    monkeypatch.setattr(
        site_audit_route, "_start_site_audit_job", lambda **kw: started.append(kw["job"].job_id)
    )

    res = client.post(f"/site-audit/jobs/{job_id}/retry", data={})
    assert res.status_code == 302
    assert started == [job_id]
    # Promoted into the local cache and re-queued.
    assert site_audit_route._jobs[job_id].status == "queued"
    with app.app_context():
        assert site_audit_route._read_job_status(job_id)["status"] == "queued"
    site_audit_route._jobs.clear()


def test_bad_job_id_cannot_traverse(app):
    bad_ids = [
        "../../etc/passwd",
        "..\\..\\windows\\system32",
        "abc/../../secret",
        "not-a-uuid",
        "",
        "..",
    ]
    with app.app_context():
        for bad in bad_ids:
            with pytest.raises(ValueError):
                site_audit_route._safe_job_id(bad)
            with pytest.raises(ValueError):
                site_audit_route._job_status_path(bad, create=False)
            # Reads return None and writes are a tolerant no-op -- nothing is
            # created outside the job-store root.
            assert site_audit_route._read_job_status(bad) is None
            site_audit_route._write_job_status(bad, status="x")

        store_root = Path(app.instance_path) / "site_audit_jobs"
        # No traversal artifact escaped into the instance dir.
        leaked = [p.name for p in Path(app.instance_path).iterdir()] if Path(app.instance_path).exists() else []
        assert "etc" not in leaked and "secret" not in leaked
        # And the store root holds no bogus entries from the no-op writes.
        if store_root.exists():
            assert list(store_root.iterdir()) == []


def test_sweep_site_audit_job_store_removes_stale_dirs(app, monkeypatch):
    import os
    import time

    with app.app_context():
        root = site_audit_route._jobs_store_root()
        stale = root / str(uuid.uuid4())
        stale.mkdir()
        (stale / "status.json").write_text("{}", encoding="utf-8")
        fresh = root / str(uuid.uuid4())
        fresh.mkdir()
        old = time.time() - (site_audit_route._access_ttl_hours + 1) * 3600
        os.utime(stale, (old, old))

        removed = site_audit_route.sweep_site_audit_job_store()
        assert removed == 1
        assert not stale.exists()
        assert fresh.exists()
