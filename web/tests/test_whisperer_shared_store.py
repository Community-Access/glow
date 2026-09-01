"""Cross-worker job-store tests for BITS Whisperer.

The whisperer route keeps job state in a per-process in-memory dict. Under
gunicorn (2 workers) a follow-up request that lands on the OTHER worker used to
404: progress polls, downloads, and the emailed secure-retrieval link all
failed roughly half the time. These tests prove those lookups now resolve from
the shared filesystem store, by clearing the in-memory cache to simulate the
"other worker" and asserting the job is still found.

Offline: no threads, no network, no ffmpeg. The worker is never run; jobs are
seeded directly and the shared store is redirected to a tmp dir via the
GLOW_WHISPERER_JOBS_DIR override.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from flask import Flask
from werkzeug.security import generate_password_hash

from acb_large_print_web.app import create_app
from acb_large_print_web.routes import whisperer as w


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Empty in-memory state and a private, per-test shared store dir."""
    store = tmp_path / "whisperer_jobs"
    store.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GLOW_WHISPERER_JOBS_DIR", str(store))
    with w._jobs_lock:
        w._jobs.clear()
        w._audio_queue.clear()
    yield
    with w._jobs_lock:
        w._jobs.clear()
        w._audio_queue.clear()


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app(
        {"TESTING": True, "WTF_CSRF_ENABLED": False}
    )
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app, monkeypatch):
    # The feature gate depends on operator config; force it open so route tests
    # exercise the store logic deterministically.
    monkeypatch.setattr(w, "_require_whisperer_feature", lambda: None)
    return app.test_client()


def _seed_complete_job(tmp_path, *, is_background=False, output_name="out.md",
                       password=None, retrieval_token=None,
                       expires_in_hours=4, retrieved=False):
    """Create a completed job with a real output file, seed it into the store."""
    job_id = str(uuid.uuid4())
    out_dir = tmp_path / ("tok-" + job_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / output_name
    output_path.write_text("transcript body", encoding="utf-8")

    job = w._WhisperJob(
        job_id=job_id,
        token="tok-" + job_id,
        saved_path=out_dir / "sample.mp3",
        language=None,
        output_format="markdown",
        title=None,
        status="complete",
        progress=100,
        message="Complete. Your file is ready to download.",
        output_path=output_path,
        mimetype="text/markdown; charset=utf-8",
        download_name=output_name,
        completed_at=datetime.now(UTC),
        is_background=is_background,
        retrieval_token=retrieval_token,
        retrieval_password_hash=generate_password_hash(password) if password else None,
        retrieval_expires_at=(
            datetime.now(UTC) + timedelta(hours=expires_in_hours)
            if is_background else None
        ),
        retrieved=retrieved,
    )
    w._set_job(job)  # writes through to the shared store
    return job, output_path


def _forget_locally():
    """Simulate the request landing on the *other* gunicorn worker."""
    with w._jobs_lock:
        w._jobs.clear()


# ---------------------------------------------------------------------------
# _get_job falls back to the shared store (progress + download resolution)
# ---------------------------------------------------------------------------

def test_get_job_resolves_from_store_after_local_eviction(tmp_path):
    job, _ = _seed_complete_job(tmp_path)
    _forget_locally()
    assert w._get_job(job.job_id) is None or True  # sanity: no crash
    loaded = w._get_job(job.job_id)
    assert loaded is not None, "job must be discoverable from the shared store"
    assert loaded.status == "complete"
    assert loaded.progress == 100
    assert loaded.download_name == "out.md"
    assert Path(loaded.output_path).exists()


def test_progress_endpoint_cross_worker(client, tmp_path):
    job, _ = _seed_complete_job(tmp_path)
    _forget_locally()
    resp = client.get(f"/whisperer/progress/{job.job_id}")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "complete"
    assert data["progress"] == 100
    assert "download_url" in data


def test_download_endpoint_cross_worker(client, tmp_path):
    job, _ = _seed_complete_job(tmp_path)
    _forget_locally()
    resp = client.get(f"/whisperer/download/{job.job_id}")
    assert resp.status_code == 200
    assert b"transcript body" in resp.data


# ---------------------------------------------------------------------------
# Secure retrieval matches by token HASH and enforces password + expiry
# ---------------------------------------------------------------------------

def test_retrieve_matches_by_token_hash_cross_worker(client, tmp_path):
    token = "retrieval-" + uuid.uuid4().hex
    job, _ = _seed_complete_job(
        tmp_path, is_background=True, password="hunter2!", retrieval_token=token
    )
    _forget_locally()

    # GET renders the password form (job resolved purely from the store).
    resp = client.get(f"/whisperer/retrieve/{token}")
    assert resp.status_code == 200

    # POST with the correct password returns the transcript.
    resp = client.post(
        f"/whisperer/retrieve/{token}", data={"retrieval_password": "hunter2!"}
    )
    assert resp.status_code == 200
    assert b"transcript body" in resp.data


def test_retrieve_plaintext_token_never_persisted(tmp_path):
    token = "retrieval-" + uuid.uuid4().hex
    job, _ = _seed_complete_job(
        tmp_path, is_background=True, password="hunter2!", retrieval_token=token
    )
    status_file = Path(w._whisperer_jobs_root()) / job.job_id / "status.json"
    text = status_file.read_text(encoding="utf-8")
    assert token not in text, "plaintext retrieval token must never be written"
    assert w._hash_retrieval_token(token) in text, "token hash must be stored for lookup"
    # And the password itself is never stored -- only its hash.
    assert "hunter2!" not in text


def test_retrieve_wrong_password_rejected(client, tmp_path):
    token = "retrieval-" + uuid.uuid4().hex
    _seed_complete_job(
        tmp_path, is_background=True, password="hunter2!", retrieval_token=token
    )
    _forget_locally()
    resp = client.post(
        f"/whisperer/retrieve/{token}", data={"retrieval_password": "wrong-pass1"}
    )
    assert resp.status_code == 403


def test_retrieve_expired_link_rejected(client, tmp_path):
    token = "retrieval-" + uuid.uuid4().hex
    _seed_complete_job(
        tmp_path,
        is_background=True,
        password="hunter2!",
        retrieval_token=token,
        expires_in_hours=-1,  # already expired
    )
    _forget_locally()
    resp = client.post(
        f"/whisperer/retrieve/{token}", data={"retrieval_password": "hunter2!"}
    )
    assert resp.status_code == 410


def test_retrieve_unknown_token_404(client, tmp_path):
    _seed_complete_job(
        tmp_path, is_background=True, password="hunter2!",
        retrieval_token="retrieval-" + uuid.uuid4().hex,
    )
    _forget_locally()
    resp = client.get("/whisperer/retrieve/" + uuid.uuid4().hex)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Traversal guard: crafted job ids / tokens cannot escape the store root
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_id",
    ["../../etc/passwd", "..", "a/b", "j1", "", "not-a-uuid", "../" + "x" * 32],
)
def test_bad_job_id_rejected_before_path_join(bad_id):
    with pytest.raises(ValueError):
        w._safe_whisperer_job_id(bad_id)
    # Store helpers tolerate the bad id without traversing or raising outward.
    assert w._load_job_from_store(bad_id) is None
    w._patch_job_status(bad_id, status="running")  # no-op, must not raise
    w._delete_job_store(bad_id)  # no-op, must not raise


def test_download_bad_job_id_does_not_traverse(client):
    # A crafted id must not resolve to any file; it 404s cleanly.
    resp = client.get("/whisperer/download/..%2F..%2Fsecret")
    assert resp.status_code in (400, 404)


def test_valid_uuid_accepted(tmp_path):
    jid = str(uuid.uuid4())
    assert w._safe_whisperer_job_id(jid) == jid


# ---------------------------------------------------------------------------
# Store-only state changes write through (marking retrieved cross-worker)
# ---------------------------------------------------------------------------

def test_update_job_writes_through_when_only_in_store(tmp_path):
    job, _ = _seed_complete_job(
        tmp_path, is_background=True, password="pw123456!",
        retrieval_token="retrieval-" + uuid.uuid4().hex,
    )
    _forget_locally()  # job now lives only in the shared store
    # This is exactly what the retrieve route does after a successful download.
    w._update_job(job.job_id, retrieved=True)
    reloaded = w._load_job_from_store(job.job_id)
    assert reloaded is not None
    assert reloaded.retrieved is True, "state change must persist to the store"


def test_retrieve_is_single_use_cross_worker(client, tmp_path):
    token = "retrieval-" + uuid.uuid4().hex
    job, output_path = _seed_complete_job(
        tmp_path, is_background=True, password="hunter2!", retrieval_token=token
    )
    _forget_locally()

    first = client.post(
        f"/whisperer/retrieve/{token}", data={"retrieval_password": "hunter2!"}
    )
    assert first.status_code == 200

    # after_this_request cleanup marked it retrieved in the store; a second
    # attempt on any worker is refused as already used.
    _forget_locally()
    second = client.post(
        f"/whisperer/retrieve/{token}", data={"retrieval_password": "hunter2!"}
    )
    assert second.status_code in (410, 404)
