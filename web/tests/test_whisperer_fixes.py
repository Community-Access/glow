"""Regression tests for BITS Whisperer worker/queue fixes.

These call the worker helpers directly with stubs (no real threads, no network,
no ffmpeg) so they stay deterministic.
"""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest

from acb_large_print_web.routes import whisperer as w
from acb_large_print_web.gating import GatingError


@pytest.fixture(autouse=True)
def _isolate_job_state():
    """Each test starts from empty module-global job/queue state."""
    with w._jobs_lock:
        w._jobs.clear()
        w._audio_queue.clear()
    yield
    with w._jobs_lock:
        w._jobs.clear()
        w._audio_queue.clear()


def _make_job(tmp_path, *, job_id="j1", output_format="markdown", is_background=False):
    audio = tmp_path / "sample.mp3"
    audio.write_bytes(b"\x00\x01\x02")
    return w._WhisperJob(
        job_id=job_id,
        token="tok-" + job_id,
        saved_path=audio,
        language=None,
        output_format=output_format,
        title=None,
        status="running",
        is_background=is_background,
    )


@contextmanager
def _gate_ok(*a, **k):
    yield


# ---------------------------------------------------------------------------
# Fix 1: any exception -> job failed + queue advances (never stuck "running")
# ---------------------------------------------------------------------------

def test_unexpected_exception_marks_failed_and_advances_queue(monkeypatch, tmp_path):
    monkeypatch.setattr(w, "get_temp_dir", lambda token: tmp_path)
    monkeypatch.setattr(w, "cleanup_token", lambda token: None)
    monkeypatch.setattr(w, "audio_gate", _gate_ok)

    def boom(*a, **k):
        raise OSError("disk vanished")  # not in the old narrow except set

    monkeypatch.setattr(w, "gateway_transcribe", boom)

    dispatched = []
    monkeypatch.setattr(w, "_dispatch_queued_jobs", lambda: dispatched.append(True))

    job = _make_job(tmp_path)
    w._set_job(job)
    w._run_whisper_job(job.job_id)

    stored = w._get_job(job.job_id)
    assert stored.status == "failed"
    assert stored.error
    assert dispatched, "queue must advance via finally on unexpected failure"


def test_base_exception_not_swallowed(monkeypatch, tmp_path):
    monkeypatch.setattr(w, "get_temp_dir", lambda token: tmp_path)
    monkeypatch.setattr(w, "cleanup_token", lambda token: None)
    monkeypatch.setattr(w, "audio_gate", _gate_ok)
    monkeypatch.setattr(w, "_dispatch_queued_jobs", lambda: None)

    def kb(*a, **k):
        raise KeyboardInterrupt()

    monkeypatch.setattr(w, "gateway_transcribe", kb)

    job = _make_job(tmp_path)
    w._set_job(job)
    with pytest.raises(KeyboardInterrupt):
        w._run_whisper_job(job.job_id)


# ---------------------------------------------------------------------------
# Fix 2: GatingError re-queues AND re-dispatches when a slot is free
# ---------------------------------------------------------------------------

def _gate_full(*a, **k):
    @contextmanager
    def _cm():
        raise GatingError("BITS Whisperer transcription")
        yield  # pragma: no cover

    return _cm()


def test_gating_error_requeues_and_redispatches_when_capacity_free(monkeypatch, tmp_path):
    monkeypatch.setattr(w, "get_temp_dir", lambda token: tmp_path)
    monkeypatch.setattr(w, "audio_gate", _gate_full)
    monkeypatch.setattr(
        "acb_large_print_web.gating.get_capacity_metrics",
        lambda: {"audio": {"available": 1}},
    )
    dispatched = []
    monkeypatch.setattr(w, "_dispatch_queued_jobs", lambda: dispatched.append(True))

    job = _make_job(tmp_path)
    w._set_job(job)
    w._run_whisper_job(job.job_id)

    assert w._get_job(job.job_id).status == "queued"
    assert job.job_id in list(w._audio_queue)
    assert dispatched, "re-queued job must trigger a re-dispatch when a slot is free"


def test_gating_error_does_not_redispatch_when_full(monkeypatch, tmp_path):
    monkeypatch.setattr(w, "get_temp_dir", lambda token: tmp_path)
    monkeypatch.setattr(w, "audio_gate", _gate_full)
    monkeypatch.setattr(
        "acb_large_print_web.gating.get_capacity_metrics",
        lambda: {"audio": {"available": 0}},
    )
    dispatched = []
    monkeypatch.setattr(w, "_dispatch_queued_jobs", lambda: dispatched.append(True))

    job = _make_job(tmp_path)
    w._set_job(job)
    w._run_whisper_job(job.job_id)

    assert w._get_job(job.job_id).status == "queued"
    assert not dispatched, "must not busy re-dispatch while the gate is full"


# ---------------------------------------------------------------------------
# Fix 3: terminal jobs are pruned on _set_job
# ---------------------------------------------------------------------------

def test_old_terminal_jobs_are_pruned(tmp_path):
    now = datetime.now(UTC)
    old_failed = _make_job(tmp_path, job_id="old")
    old_failed.status = "failed"
    old_failed.completed_at = now - timedelta(hours=w._TERMINAL_JOB_RETENTION_HOURS + 1)
    with w._jobs_lock:
        w._jobs["old"] = old_failed  # insert directly (no prune)

    w._set_job(_make_job(tmp_path, job_id="new"))

    assert "old" not in w._jobs
    assert "new" in w._jobs


def test_background_complete_within_window_is_not_pruned(tmp_path):
    now = datetime.now(UTC)
    bg = _make_job(tmp_path, job_id="bg", is_background=True)
    bg.status = "complete"
    bg.retrieved = False
    bg.completed_at = now - timedelta(hours=w._TERMINAL_JOB_RETENTION_HOURS + 1)
    bg.retrieval_expires_at = now + timedelta(hours=1)  # still retrievable
    with w._jobs_lock:
        w._jobs["bg"] = bg

    w._set_job(_make_job(tmp_path, job_id="new"))

    assert "bg" in w._jobs, "retrievable background transcript must survive pruning"


# ---------------------------------------------------------------------------
# Fix 4: token dir mtime refreshed on completion + helper works
# ---------------------------------------------------------------------------

def test_touch_token_dir_refreshes_mtime(monkeypatch, tmp_path):
    import os as _os

    monkeypatch.setattr(w, "get_temp_dir", lambda token: tmp_path)
    _os.utime(tmp_path, (1000, 1000))
    assert tmp_path.stat().st_mtime < 2000
    w._touch_token_dir("whatever")
    assert tmp_path.stat().st_mtime > 1_000_000  # bumped to ~now


def test_successful_run_touches_token_dir_on_completion(monkeypatch, tmp_path):
    monkeypatch.setattr(w, "get_temp_dir", lambda token: tmp_path)
    monkeypatch.setattr(w, "cleanup_token", lambda token: None)
    monkeypatch.setattr(w, "audio_gate", _gate_ok)
    monkeypatch.setattr(w, "gateway_transcribe", lambda *a, **k: "hello transcript")
    monkeypatch.setattr(w, "_dispatch_queued_jobs", lambda: None)

    touched = []
    real_touch = w._touch_token_dir
    monkeypatch.setattr(w, "_touch_token_dir", lambda token: touched.append(token))

    job = _make_job(tmp_path)
    w._set_job(job)
    w._run_whisper_job(job.job_id)

    assert w._get_job(job.job_id).status == "complete"
    assert touched, "completion path must refresh the token dir mtime"


# ---------------------------------------------------------------------------
# Fix 5: completion email uses the absolute URL captured in the request
# ---------------------------------------------------------------------------

def test_completion_email_uses_stored_absolute_url(monkeypatch, tmp_path):
    captured = {}

    def fake_send(to, subject, html, text):
        captured.update(to=to, subject=subject, html=html, text=text)

    monkeypatch.setattr(w, "send_whisperer_status_email", fake_send)

    job = _make_job(tmp_path, is_background=True)
    job.notify_email = "user@example.com"
    job.retrieval_token = "abc123"
    job.retrieval_url = "https://glow.example.org/whisperer/retrieve/abc123"
    job.status = "complete"

    w._send_job_email(job, "completed")

    assert "https://glow.example.org/whisperer/retrieve/abc123" in captured["text"]
    assert "https://glow.example.org/whisperer/retrieve/abc123" in captured["html"]


# ---------------------------------------------------------------------------
# Fix 6: ffmpeg normalization has a timeout and handles TimeoutExpired
# ---------------------------------------------------------------------------

def test_prepare_audio_passes_timeout_and_handles_expiry(monkeypatch, tmp_path):
    audio = tmp_path / "clip.ogg"  # .ogg -> transcode path
    audio.write_bytes(b"OggS")

    captured = {}

    def fake_run(cmd, **kwargs):
        captured.update(kwargs)
        raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout"))

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(w.UploadError) as exc:
        w._prepare_audio_for_cloud(audio)

    assert "timed out" in str(exc.value).lower()
    assert captured.get("timeout", 0) > 0
