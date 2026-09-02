"""Resource bounds on the anonymous Site Audit submit path.

A submitted scan runs on its own thread and makes up to ``max_pages`` outbound
fetches. Without bounds an anonymous caller can turn one HTTP request into a
crawler, and a burst into many. Two defenses are asserted here: a per-caller
rate limit on the submit endpoint, and a cap on how many scans actually run
concurrently.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
import acb_large_print_web.routes.site_audit as site_audit_route


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


def test_submit_is_rate_limited(client, monkeypatch: pytest.MonkeyPatch):
    """A burst of submissions is throttled rather than spawning a crawler each."""
    monkeypatch.setattr(site_audit_route, "_start_site_audit_job", lambda **kw: None)

    codes = []
    for _ in range(9):
        res = client.post(
            "/site-audit/",
            data={"sources": "https://example.com", "run_in_background": "on"},
        )
        codes.append(res.status_code)

    assert 429 in codes, f"expected the submit endpoint to throttle a burst, got {codes}"


def test_concurrent_scan_cap_reports_busy_instead_of_running(
    app: Flask, monkeypatch: pytest.MonkeyPatch
):
    """With every scan slot held, a new job reports a retryable busy state.

    It must not run the scan (which would mean unbounded outbound load) and it
    must not park the thread forever waiting for a slot.
    """
    ran: list[str] = []
    monkeypatch.setattr(
        site_audit_route,
        "_run_site_audit_job",
        lambda **kw: ran.append(kw["job"].job_id),
    )
    # No waiting around in a test; the point is the give-up path.
    monkeypatch.setattr(site_audit_route, "_SCAN_SLOT_WAIT_SECONDS", 0)

    # Hold every slot.
    held = 0
    while site_audit_route._scan_slots.acquire(blocking=False):
        held += 1
    assert held > 0, "expected a bounded number of scan slots"

    try:
        job = site_audit_route._SiteAuditJob(
            job_id="11111111-1111-1111-1111-111111111111",
            run_id="22222222-2222-2222-2222-222222222222",
        )
        with app.test_request_context():
            site_audit_route._start_site_audit_job(job=job, sources=["https://example.com"], options=None)
        if job.worker is not None:
            job.worker.join(timeout=10)

        assert ran == [], "the scan must not run when no slot is available"
        assert job.status == "failed"
        assert job.retryable is True
        assert "busy" in (job.error or "").lower()
    finally:
        for _ in range(held):
            site_audit_route._scan_slots.release()


def test_scan_slot_is_released_after_a_run(app: Flask, monkeypatch: pytest.MonkeyPatch):
    """A finished scan returns its slot, so the cap is not a one-way ratchet."""
    monkeypatch.setattr(site_audit_route, "_run_site_audit_job", lambda **kw: None)

    job = site_audit_route._SiteAuditJob(
        job_id="33333333-3333-3333-3333-333333333333",
        run_id="44444444-4444-4444-4444-444444444444",
    )
    with app.test_request_context():
        site_audit_route._start_site_audit_job(job=job, sources=["https://example.com"], options=None)
    if job.worker is not None:
        job.worker.join(timeout=10)

    # Every slot should be free again.
    acquired = 0
    while site_audit_route._scan_slots.acquire(blocking=False):
        acquired += 1
    for _ in range(acquired):
        site_audit_route._scan_slots.release()
    assert acquired == site_audit_route._MAX_CONCURRENT_SCANS
