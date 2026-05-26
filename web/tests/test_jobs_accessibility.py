from __future__ import annotations

import json
from pathlib import Path

import pytest

from acb_large_print_web.app import create_app
from acb_large_print_web.tasks import convert_tasks


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GLOW_JOBS_DIR", str(jobs_dir))

    application = create_app(
        {"TESTING": True, "WTF_CSRF_ENABLED": False, "MAX_CONTENT_LENGTH": 500 * 1024 * 1024}
    )
    application.config["TEST_TMPDIR"] = str(tmp_path)
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def _write_status(jobs_root: Path, job_id: str, payload: dict) -> None:
    job_dir = jobs_root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "status.json").write_text(json.dumps(payload), encoding="utf-8")


def test_job_progress_page_has_core_accessibility_semantics(tmp_path: Path, client):
    jobs_root = tmp_path / "jobs"
    job_id = "a11y-job-1"
    _write_status(
        jobs_root,
        job_id,
        {
            "state": "PROGRESS",
            "progress": 42,
            "message": "Converting",
            "result_file": None,
        },
    )

    res = client.get(f"/job/{job_id}")
    assert res.status_code == 200

    html = res.data.decode("utf-8")
    assert '<section class="card"' in html
    assert '<h1 id="job-title">Processing Job</h1>' in html
    assert 'id="job-message" aria-live="polite"' in html
    assert '<label id="job-progress-label" for="job-progress">Progress</label>' in html
    assert 'id="job-progress"' in html
    assert 'aria-labelledby="job-progress-label"' in html
    assert 'aria-describedby="job-progress-text"' in html
    assert 'id="job-error" class="error-text" role="alert" aria-live="assertive"' in html
    assert 'id="job-download-wrap" hidden' in html


def test_job_progress_missing_job_returns_404(client):
    res = client.get("/job/unknown-job")
    assert res.status_code == 404
    assert not (Path(client.application.config["TEST_TMPDIR"]) / "jobs" / "unknown-job").exists()


def test_job_poll_returns_status_payload(tmp_path: Path, client):
    jobs_root = tmp_path / "jobs"
    job_id = "poll-job-1"
    _write_status(
        jobs_root,
        job_id,
        {
            "state": "PROGRESS",
            "progress": 57,
            "message": "Still converting",
            "result_file": None,
        },
    )

    res = client.get(f"/job/{job_id}/poll")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["state"] == "PROGRESS"
    assert payload["progress"] == 57


def test_job_result_downloads_file_for_success(tmp_path: Path, client):
    jobs_root = tmp_path / "jobs"
    job_id = "result-job-1"
    job_dir = jobs_root / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    result_name = "result.md"
    (job_dir / result_name).write_text("# converted\n", encoding="utf-8")
    _write_status(
        jobs_root,
        job_id,
        {
            "state": "SUCCESS",
            "progress": 100,
            "message": "Done",
            "result_file": result_name,
            "filename": "source.docx",
        },
    )

    res = client.get(f"/job/{job_id}/result")
    assert res.status_code == 200
    assert res.data.decode("utf-8").replace("\r\n", "\n") == "# converted\n"
    assert "attachment; filename=\"source.md\"" in res.headers["Content-Disposition"]


def test_job_cancel_marks_job_cancelling(tmp_path: Path, client):
    jobs_root = tmp_path / "jobs"
    job_id = "cancel-job-1"
    _write_status(
        jobs_root,
        job_id,
        {
            "state": "PROGRESS",
            "progress": 25,
            "message": "Working",
            "result_file": None,
            "attempt": 1,
            "max_attempts": 2,
        },
    )

    res = client.post(f"/job/{job_id}/cancel")
    assert res.status_code == 302

    status = json.loads((jobs_root / job_id / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "CANCELLING"
    assert status["cancel_requested"] is True


def test_job_retry_requeues_failed_job(tmp_path: Path, client, monkeypatch: pytest.MonkeyPatch):
    jobs_root = tmp_path / "jobs"
    job_id = "retry-job-1"
    _write_status(
        jobs_root,
        job_id,
        {
            "state": "FAILURE",
            "progress": 0,
            "message": "Failed",
            "error": "boom",
            "result_file": None,
            "attempt": 1,
            "max_attempts": 2,
            "deadline_at": 9999999999.0,
            "retryable": True,
        },
    )
    (jobs_root / job_id).mkdir(parents=True, exist_ok=True)
    (jobs_root / job_id / "job-meta.json").write_text(
        json.dumps(
            {
                "op": "to_markdown",
                "upload_token": "token-1",
                "input_filename": "source.docx",
                "options": {},
            }
        ),
        encoding="utf-8",
    )

    calls: list[tuple] = []

    def _fake_delay(*args):
        calls.append(args)
        return None

    monkeypatch.setattr(convert_tasks.run_convert_job, "delay", _fake_delay)

    res = client.post(f"/job/{job_id}/retry")
    assert res.status_code == 302
    assert calls

    status = json.loads((jobs_root / job_id / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "PENDING"
    assert status["cancel_requested"] is False
