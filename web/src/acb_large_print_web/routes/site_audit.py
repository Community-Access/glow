"""Site-audit route -- scan web pages for accessibility issues and export artifacts."""

from __future__ import annotations

import dataclasses
import hashlib
import hmac
import json
import secrets
import shutil
import threading
import time
from pathlib import Path
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from flask import Blueprint, Response, abort, current_app, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..async_orchestration import deadline_exceeded, load_policy
from ..feature_flags import get_flag
from ..site_audit import SiteAuditOptions, get_run_dir, parse_input_urls, run_site_audit


site_audit_bp = Blueprint("site_audit", __name__)


@dataclass
class _SiteAuditJob:
    job_id: str
    run_id: str
    status: str = "queued"
    progress: int = 0
    message: str = "Queued"
    error: str | None = None
    cancelled: bool = False
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: dict[str, Any] | None = None
    access_token_hash: str | None = None
    access_token_value: str | None = None
    access_password_hash: str | None = None
    access_expires_at: datetime | None = None
    cancel_event: threading.Event | None = None
    worker: threading.Thread | None = None
    attempt: int = 0
    max_attempts: int = 1
    deadline_at: float | None = None
    retryable: bool = False
    sources: tuple[str, ...] = ()
    options: SiteAuditOptions | None = None


_jobs: dict[str, _SiteAuditJob] = {}
_jobs_lock = threading.Lock()
_access_ttl_hours = 24


def _enabled() -> bool:
    return bool(get_flag("GLOW_ENABLE_SITE_AUDIT", True))


def sweep_site_audit_runs(max_age_hours: int = _access_ttl_hours) -> int:
    """Delete run directories under instance/site_audit_runs older than the TTL.

    Each run holds full page HTML, a summary, and artifacts that are never
    otherwise removed, so without this sweep the instance directory grows without
    bound. Mirrors upload.cleanup_stale_uploads / report_cache.sweep_expired_shares.
    Returns the number of run directories removed.
    """
    root = _runs_root()
    if not root.exists():
        return 0
    removed = 0
    cutoff = time.time() - (max_age_hours * 3600)
    try:
        for item in root.iterdir():
            if not item.is_dir():
                continue
            try:
                if item.stat().st_mtime < cutoff:
                    shutil.rmtree(item, ignore_errors=True)
                    removed += 1
            except OSError:
                pass
    except OSError:
        pass
    return removed


def _evict_stale_jobs(max_age_hours: int = _access_ttl_hours) -> int:
    """Drop terminal in-memory jobs older than the access TTL.

    A completed job pins its full summary, plaintext access token, and messages
    in the ``_jobs`` dict forever. Evict finished jobs (complete/failed/cancelled)
    whose worker thread is no longer alive and whose terminal timestamp is past
    the TTL. Thread-safe on its own; returns the number evicted.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    removed = 0
    with _jobs_lock:
        for job_id in list(_jobs.keys()):
            job = _jobs[job_id]
            if job.status not in {"complete", "failed", "cancelled"}:
                continue
            if job.worker is not None and job.worker.is_alive():
                continue
            ts = job.completed_at or job.created_at
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts < cutoff:
                del _jobs[job_id]
                removed += 1
    return removed


def _runs_root() -> Path:
    root = Path(current_app.instance_path) / "site_audit_runs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _write_access_metadata(run_id: str, token_hash: str, password_hash: str | None, expires_at: datetime) -> None:
    run_dir = _runs_root() / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "token_hash": token_hash,
        "password_hash": password_hash,
        "expires_at": expires_at.astimezone(UTC).isoformat(),
    }
    (run_dir / "access.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _read_access_metadata(run_id: str) -> dict | None:
    run_dir = get_run_dir(_runs_root(), run_id)
    if run_dir is None:
        return None
    path = run_dir / "access.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _session_unlock_key(run_id: str) -> str:
    return f"site_audit_unlock:{run_id}"


def _access_token_from_request() -> str:
    return (request.args.get("access") or request.form.get("access") or "").strip()


def _enforce_run_access(run_id: str, *, allow_unlock_form: bool = True):
    metadata = _read_access_metadata(run_id)
    if not metadata:
        return None

    expires_raw = str(metadata.get("expires_at") or "")
    try:
        expires_at = datetime.fromisoformat(expires_raw)
    except Exception:
        expires_at = datetime.now(UTC) - timedelta(seconds=1)
    # A hand-edited or older access.json may carry a tz-naive timestamp;
    # comparing that against an aware now() raises TypeError -> 500. Treat a
    # naive expiry as UTC so the gate returns 403, not a server error.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        abort(403)

    token = _access_token_from_request()
    expected_hash = str(metadata.get("token_hash") or "")
    if not token or not expected_hash or not hmac.compare_digest(_hash_token(token), expected_hash):
        abort(403)

    password_hash = str(metadata.get("password_hash") or "")
    if not password_hash:
        return None

    if session.get(_session_unlock_key(run_id)):
        return None

    if allow_unlock_form:
        return render_template(
            "site_audit_unlock.html",
            run_id=run_id,
            access=token,
            error=None,
        )
    abort(403)


def _start_site_audit_job(*, job: _SiteAuditJob, sources: list[str], options: SiteAuditOptions) -> None:
    app = current_app._get_current_object()

    def _worker() -> None:
        with app.app_context():
            _run_site_audit_job(job=job, sources=sources, options=options)

    thread = threading.Thread(target=_worker, daemon=True)
    with _jobs_lock:
        job.worker = thread
    thread.start()


def _run_site_audit_job(*, job: _SiteAuditJob, sources: list[str], options: SiteAuditOptions) -> None:
    for attempt in range(job.attempt + 1, job.max_attempts + 1):
        with _jobs_lock:
            job.attempt = attempt
            job.status = "running"
            job.retryable = attempt < job.max_attempts
            job.message = "Crawl and scan in progress"
            job.started_at = datetime.now(UTC)
            job.error = None

        def _is_cancelled() -> bool:
            if deadline_exceeded(job.deadline_at):
                return True
            return bool(job.cancel_event and job.cancel_event.is_set())

        def _progress(current: int, total: int, url: str) -> None:
            if _is_cancelled():
                return
            pct = int((current / max(total, 1)) * 100)
            with _jobs_lock:
                job.progress = max(0, min(100, pct))
                job.message = f"Scanning {current}/{total}: {url}"

        if deadline_exceeded(job.deadline_at):
            with _jobs_lock:
                job.status = "failed"
                job.retryable = False
                job.error = "Job exceeded deadline."
                job.message = "Scan timed out"
                job.completed_at = datetime.now(UTC)
            return

        try:
            summary = run_site_audit(
                run_id=job.run_id,
                base_dir=_runs_root(),
                sources=sources,
                options=options,
                is_cancelled=_is_cancelled,
                progress_callback=_progress,
            )
            with _jobs_lock:
                job.summary = summary
                job.cancelled = bool(summary.get("cancelled"))
                job.status = "cancelled" if job.cancelled else "complete"
                job.progress = 100
                job.retryable = bool(job.cancelled and attempt < job.max_attempts and not deadline_exceeded(job.deadline_at))
                job.message = "Scan cancelled" if job.cancelled else "Scan complete"
                job.completed_at = datetime.now(UTC)
            return
        except Exception as exc:
            if attempt < job.max_attempts and not deadline_exceeded(job.deadline_at):
                with _jobs_lock:
                    job.status = "retrying"
                    job.message = f"Retrying scan ({attempt}/{job.max_attempts})"
                    job.error = str(exc)
                continue
            with _jobs_lock:
                job.status = "failed"
                job.retryable = False
                job.error = str(exc)
                job.message = "Scan failed"
                job.completed_at = datetime.now(UTC)
            return



def _can_retry(job: _SiteAuditJob) -> bool:
    if job.status not in {"failed", "cancelled"}:
        return False
    if job.attempt >= job.max_attempts:
        return False
    if deadline_exceeded(job.deadline_at):
        return False
    return True


@site_audit_bp.route("/", methods=["GET"])
def site_audit_form():
    if not _enabled():
        abort(404)
    sweep_site_audit_runs()
    _evict_stale_jobs()
    return render_template("site_audit_form.html")


@site_audit_bp.route("/", methods=["POST"])
def site_audit_submit():
    if not _enabled():
        abort(404)

    sweep_site_audit_runs()
    _evict_stale_jobs()

    sources_raw = (request.form.get("sources") or "").strip()
    sitemap_raw = (request.form.get("sitemap_url") or "").strip()

    max_pages_raw = (request.form.get("max_pages") or "10").strip()
    try:
        max_pages = int(max_pages_raw)
    except ValueError:
        max_pages = 10
    max_pages = max(1, min(50, max_pages))

    crawl_depth_raw = (request.form.get("crawl_depth") or "1").strip()
    try:
        crawl_depth = int(crawl_depth_raw)
    except ValueError:
        crawl_depth = 1
    crawl_depth = max(0, min(5, crawl_depth))

    crawl_links = bool(request.form.get("crawl_links"))
    include_subdomains = bool(request.form.get("include_subdomains"))
    same_path_only = bool(request.form.get("same_path_only"))
    strict_open_source_only = bool(request.form.get("strict_open_source_only"))
    run_in_background = bool(request.form.get("run_in_background"))
    exclude_patterns_raw = (request.form.get("exclude_patterns") or "").strip()
    exclude_url_patterns = tuple(
        p.strip()
        for p in exclude_patterns_raw.replace(",", "\n").splitlines()
        if p.strip()
    )
    force = bool(request.form.get("force"))
    protect_results = bool(request.form.get("protect_results"))
    access_password = (request.form.get("access_password") or "").strip()

    access_token_value: str | None = None
    access_token_hash: str | None = None
    access_password_hash: str | None = None
    access_expires_at = datetime.now(UTC) + timedelta(hours=_access_ttl_hours)
    if protect_results:
        access_token_value = secrets.token_urlsafe(32)
        access_token_hash = _hash_token(access_token_value)
        access_password_hash = generate_password_hash(access_password) if access_password else None

    urls = parse_input_urls(sources_raw, sitemap_raw)
    if not urls:
        return render_template(
            "site_audit_form.html",
            error="Provide at least one valid URL or sitemap URL.",
            sources=sources_raw,
            sitemap_url=sitemap_raw,
            max_pages=max_pages,
            crawl_depth=crawl_depth,
            crawl_links=crawl_links,
            include_subdomains=include_subdomains,
            same_path_only=same_path_only,
            strict_open_source_only=strict_open_source_only,
            exclude_patterns=exclude_patterns_raw,
            run_in_background=run_in_background,
            protect_results=protect_results,
            force=force,
        ), 400

    run_id = str(uuid.uuid4())
    options = SiteAuditOptions(
        max_pages=max_pages,
        crawl_links=crawl_links,
        crawl_depth=crawl_depth,
        include_subdomains=include_subdomains,
        same_path_only=same_path_only,
        exclude_url_patterns=exclude_url_patterns,
        strict_open_source_only=strict_open_source_only,
        force=force,
    )

    if access_token_hash:
        _write_access_metadata(run_id, access_token_hash, access_password_hash, access_expires_at)

    if run_in_background:
        policy = load_policy("SITE_AUDIT")
        job_id = str(uuid.uuid4())
        job = _SiteAuditJob(
            job_id=job_id,
            run_id=run_id,
            created_at=datetime.now(UTC),
            access_token_hash=access_token_hash,
            access_token_value=access_token_value,
            access_password_hash=access_password_hash,
            access_expires_at=access_expires_at,
            cancel_event=threading.Event(),
            max_attempts=policy.max_attempts,
            deadline_at=policy.deadline_at,
            sources=tuple(urls),
            options=options,
        )
        with _jobs_lock:
            _jobs[job_id] = job
        _start_site_audit_job(job=job, sources=urls, options=options)

        return render_template(
            "site_audit_job.html",
            job=job,
            run_id=run_id,
            job_id=job_id,
            access=access_token_value,
        )

    summary = run_site_audit(
        run_id=run_id,
        base_dir=_runs_root(),
        sources=urls,
        options=options,
    )

    return render_template(
        "site_audit_result.html",
        summary=summary,
        run_id=run_id,
        access=access_token_value,
    )


@site_audit_bp.route("/jobs/<job_id>", methods=["GET"])
def site_audit_job(job_id: str):
    if not _enabled():
        abort(404)
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        abort(404)

    token = _access_token_from_request()
    if job.access_token_hash and (not token or not hmac.compare_digest(_hash_token(token), job.access_token_hash)):
        abort(403)

    return render_template(
        "site_audit_job.html",
        job=job,
        run_id=job.run_id,
        job_id=job_id,
        access=token,
    )


@site_audit_bp.route("/jobs/<job_id>/status", methods=["GET"])
def site_audit_job_status(job_id: str):
    if not _enabled():
        abort(404)
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        abort(404)
    token = _access_token_from_request()
    if job.access_token_hash and (not token or not hmac.compare_digest(_hash_token(token), job.access_token_hash)):
        abort(403)

    return jsonify(
        {
            "job_id": job.job_id,
            "run_id": job.run_id,
            "status": job.status,
            "progress": job.progress,
            "message": job.message,
            "error": job.error,
            "cancelled": job.cancelled,
            "attempt": job.attempt,
            "max_attempts": job.max_attempts,
            "retryable": _can_retry(job),
            "result_url": url_for("site_audit.site_audit_run", run_id=job.run_id, access=token),
        }
    )


@site_audit_bp.route("/jobs/<job_id>/cancel", methods=["POST"])
def site_audit_job_cancel(job_id: str):
    if not _enabled():
        abort(404)
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        abort(404)

    token = _access_token_from_request()
    if job.access_token_hash and (not token or not hmac.compare_digest(_hash_token(token), job.access_token_hash)):
        abort(403)

    if job.cancel_event:
        job.cancel_event.set()
    with _jobs_lock:
        if job.status in {"queued", "running", "retrying"}:
            job.status = "cancelled"
            job.message = "Cancellation requested"
            job.cancelled = True

    return redirect(url_for("site_audit.site_audit_job", job_id=job_id, access=token))


@site_audit_bp.route("/jobs/<job_id>/retry", methods=["POST"])
def site_audit_job_retry(job_id: str):
    if not _enabled():
        abort(404)
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        abort(404)

    token = _access_token_from_request()
    if job.access_token_hash and (not token or not hmac.compare_digest(_hash_token(token), job.access_token_hash)):
        abort(403)

    # A cancel is only observed between pages, so the previous worker may still
    # be alive when Retry arrives. Spawning a second thread over the same run dir
    # corrupts artifacts.zip (PermissionError on Windows). Refuse until the old
    # worker has actually exited.
    if job.worker is not None and job.worker.is_alive():
        return redirect(url_for("site_audit.site_audit_job", job_id=job_id, access=token))

    if _can_retry(job):
        # Force a fresh crawl on retry: otherwise run_site_audit sees the cached
        # page.json files and the retried run reuses stale output.
        retry_options = dataclasses.replace(job.options, force=True) if job.options else None
        with _jobs_lock:
            job.cancelled = False
            job.status = "queued"
            job.progress = 0
            job.message = "Queued for retry"
            job.error = None
            job.options = retry_options
            if job.cancel_event:
                job.cancel_event.clear()
        summary_path = (_runs_root() / job.run_id) / "summary.json"
        if summary_path.exists():
            summary_path.unlink()
        try:
            if not retry_options or not job.sources:
                raise RuntimeError("Retry metadata missing")
            _start_site_audit_job(job=job, sources=list(job.sources), options=retry_options)
        except Exception:
            with _jobs_lock:
                job.status = "failed"
                job.error = "Unable to retry this job."
                job.message = "Scan failed"

    return redirect(url_for("site_audit.site_audit_job", job_id=job_id, access=token))


@site_audit_bp.route("/runs/<run_id>/unlock", methods=["POST"])
def site_audit_unlock(run_id: str):
    if not _enabled():
        abort(404)
    metadata = _read_access_metadata(run_id)
    if not metadata:
        return redirect(url_for("site_audit.site_audit_run", run_id=run_id))

    token = _access_token_from_request()
    expected_hash = str(metadata.get("token_hash") or "")
    if not token or not expected_hash or not hmac.compare_digest(_hash_token(token), expected_hash):
        abort(403)

    password_hash = str(metadata.get("password_hash") or "")
    if password_hash:
        provided = (request.form.get("access_password") or "").strip()
        if not provided or not check_password_hash(password_hash, provided):
            return render_template("site_audit_unlock.html", run_id=run_id, access=token, error="Incorrect password.")
        session[_session_unlock_key(run_id)] = True

    return redirect(url_for("site_audit.site_audit_run", run_id=run_id, access=token))


@site_audit_bp.route("/runs/<run_id>", methods=["GET"])
def site_audit_run(run_id: str):
    if not _enabled():
        abort(404)
    run_dir = get_run_dir(_runs_root(), run_id)
    if run_dir is None:
        abort(404)
    access_gate = _enforce_run_access(run_id)
    if access_gate is not None:
        return access_gate
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        abort(404)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return render_template("site_audit_result.html", summary=summary, run_id=run_id, access=_access_token_from_request())


@site_audit_bp.route("/runs/<run_id>/download/<artifact>", methods=["GET"])
def site_audit_download(run_id: str, artifact: str):
    if not _enabled():
        abort(404)
    run_dir = get_run_dir(_runs_root(), run_id)
    if run_dir is None:
        abort(404)
    access_gate = _enforce_run_access(run_id, allow_unlock_form=False)
    if access_gate is not None:
        return access_gate

    mapping = {
        "summary": (run_dir / "summary.json", "application/json", f"site-audit-{run_id}-summary.json"),
        "csv": (run_dir / "findings.csv", "text/csv", f"site-audit-{run_id}-findings.csv"),
        "log": (run_dir / "session.log", "text/plain", f"site-audit-{run_id}-session.log"),
        "zip": (run_dir / "artifacts.zip", "application/zip", f"site-audit-{run_id}-artifacts.zip"),
    }
    item = mapping.get(artifact)
    if item is None:
        abort(404)

    file_path, mime, filename = item
    if not file_path.exists():
        abort(404)
    return send_file(file_path, mimetype=mime, as_attachment=True, download_name=filename)


@site_audit_bp.route("/runs/<run_id>/summary", methods=["GET"])
def site_audit_summary_json(run_id: str):
    if not _enabled():
        abort(404)
    run_dir = get_run_dir(_runs_root(), run_id)
    if run_dir is None:
        abort(404)
    access_gate = _enforce_run_access(run_id, allow_unlock_form=False)
    if access_gate is not None:
        return access_gate
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        abort(404)
    return Response(summary_path.read_text(encoding="utf-8"), mimetype="application/json")
