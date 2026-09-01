"""BITS Whisperer route -- cloud audio transcription to Markdown or Word.

BITS Whisperer routes audio transcription through OpenRouter using the operator's
OPENROUTER_API_KEY (same key used for all other AI features -- no separate key needed).
When that key is not configured, the /whisperer route and tab are hidden entirely.

Audio files are sent to the OpenRouter audio transcription endpoint, then immediately
deleted from the GLOW server.  Transcripts are processed locally and never
stored beyond the session temp directory (deleted within 1 hour).

Outputs:
  - Markdown (.md) -- plain ACB-compliant transcript ready to edit or convert
  - Word (.docx) -- Markdown transcript passed through Pandoc for an editable
    Word document (requires Pandoc to be installed)

Route:
  GET  /whisperer           -- upload form
  POST /whisperer           -- process audio, return file download
"""

from __future__ import annotations

import hmac
import os
import re
import secrets
import subprocess
import threading
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from acb_large_print.pandoc_converter import convert_to_docx, pandoc_available
from flask import (
    Blueprint,
    after_this_request,
    current_app,
    jsonify,
    make_response,
    render_template,
    request,
    send_file,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from ..ai_features import AIFeatureDisabled, require_ai_feature
from ..ai_gateway import is_whisper_configured
from ..ai_gateway import transcribe as gateway_transcribe
from ..email import email_configured, send_whisperer_status_email
from ..gating import RETRY_AFTER_SECONDS, GatingError, audio_gate
from ..passport_store import COOKIE_NAME as PASSPORT_COOKIE
from ..passport_store import get_passport as _get_passport
from ..upload import AUDIO_EXTENSIONS, UploadError, cleanup_token, get_temp_dir, validate_upload

whisperer_bp = Blueprint("whisperer", __name__)


def _require_whisperer_feature() -> None:
    """Abort with 404 when BITS Whisperer is disabled for this deployment."""
    try:
        require_ai_feature("whisperer")
    except AIFeatureDisabled:
        from flask import abort

        abort(404)


@dataclass
class _WhisperJob:
    job_id: str
    token: str
    saved_path: Path
    language: str | None
    output_format: str
    title: str | None
    status: str = "queued"  # queued | running | complete | failed
    progress: int = 0
    message: str = "Queued..."
    error: str | None = None
    output_path: Path | None = None
    mimetype: str | None = None
    download_name: str | None = None
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    is_background: bool = False
    notify_email: str | None = None
    retrieval_token: str | None = None
    retrieval_url: str | None = None
    retrieval_password_hash: str | None = None
    retrieval_expires_at: datetime | None = None
    retrieved: bool = False
    cleanup_timer_set: bool = False


_jobs: dict[str, _WhisperJob] = {}
_jobs_lock = threading.Lock()
_audio_queue: deque[str] = deque()

_MAX_AUDIO_MB = int(os.environ.get("WHISPER_MAX_AUDIO_MB", "500"))
_MAX_AUDIO_MINUTES = int(os.environ.get("WHISPER_MAX_AUDIO_MINUTES", "120"))
_MAX_AUDIO_QUEUE_DEPTH = int(os.environ.get("GLOW_MAX_AUDIO_QUEUE_DEPTH", "5"))
_BACKGROUND_THRESHOLD_MINUTES = int(os.environ.get("WHISPER_BACKGROUND_THRESHOLD_MINUTES", "30"))
_RETRIEVAL_HOURS = int(os.environ.get("WHISPER_RETRIEVAL_HOURS", "4"))
# Terminal (complete/failed) jobs are pruned from _jobs once older than this,
# so foreground/failed jobs no longer live for the whole process lifetime.
# Background completed jobs that are still inside their retrieval window are
# exempt from pruning (see _prune_terminal_jobs_locked).
_TERMINAL_JOB_RETENTION_HOURS = int(
    os.environ.get("WHISPER_TERMINAL_JOB_RETENTION_HOURS", str(max(_RETRIEVAL_HOURS, 4)))
)
# Hard cap on the local ffmpeg normalization step so a hung child cannot pin a
# worker thread forever.
_FFMPEG_TIMEOUT_SECONDS = int(os.environ.get("WHISPER_FFMPEG_TIMEOUT_SECONDS", "300"))
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ESTIMATE_BYTES_PER_SECOND = 16000  # ~128 kbps compressed audio
_MIN_PLAUSIBLE_BYTES_PER_SECOND = 500  # guardrail for bogus long metadata durations
_CLOUD_DIRECT_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".webm", ".mp4", ".mpeg", ".mpga"}
_CLOUD_TRANSCODE_AUDIO_EXTENSIONS = {".ogg", ".flac", ".aac", ".opus"}

# Accept string for the file input
_AUDIO_ACCEPT = ",".join(sorted(AUDIO_EXTENSIONS))

# Language choices shown in the form (BCP-47 code -> display label)
# Sorted by global speaker population for quick scanning
_LANGUAGE_CHOICES: list[tuple[str, str]] = [
    ("", "Auto-detect (recommended)"),
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("it", "Italian"),
    ("pt", "Portuguese"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("ru", "Russian"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("zh", "Chinese (Mandarin)"),
    ("ar", "Arabic"),
    ("hi", "Hindi"),
    ("tr", "Turkish"),
    ("sv", "Swedish"),
    ("da", "Danish"),
    ("no", "Norwegian"),
    ("fi", "Finnish"),
]


def _remembered_notify_email() -> str:
    """The address this browser's passport asked us to remember, if any.

    Typing the same address into every long job is a small, repeated
    annoyance, and the passport already holds it. Absent a passport, or with
    notifications switched off, this returns "" and the field is empty --
    exactly as before.
    """
    try:
        passport = _get_passport((request.cookies.get(PASSPORT_COOKIE) or "").strip())
        if passport and passport.get("notify_enabled"):
            return str(passport.get("email") or "")
    except Exception:
        pass
    return ""


def _template_context(**extra):
    return dict(
        audio_accept=_AUDIO_ACCEPT,
        whisper_installed=is_whisper_configured(),
        pandoc_installed=pandoc_available(),
        email_enabled=email_configured(),
        remembered_notify_email=_remembered_notify_email(),
        max_audio_mb=_MAX_AUDIO_MB,
        background_threshold_minutes=_BACKGROUND_THRESHOLD_MINUTES,
        language_choices=_LANGUAGE_CHOICES,
        **extra,
    )


def _busy_response():
    resp = make_response(
        render_template(
            "busy.html",
            operation="BITS Whisperer transcription",
            retry_seconds=RETRY_AFTER_SECONDS,
            back_url=url_for("whisperer.whisperer_form"),
        ),
        503,
    )
    resp.headers["Retry-After"] = str(RETRY_AFTER_SECONDS)
    return resp


def _touch_token_dir(token: str) -> None:
    """Refresh token dir mtime so active jobs are not removed by stale cleanup."""
    temp_dir = get_temp_dir(token)
    if temp_dir is None:
        return
    try:
        os.utime(temp_dir, None)
    except OSError:
        pass


def _estimate_audio_duration_seconds(audio_path: Path) -> float | None:
    """Estimate audio length from metadata; returns None if unavailable.

    Uses Mutagen first for a simple, format-agnostic metadata duration value,
    then falls back to PyAV for broader codec/container coverage.
    """

    try:
        from mutagen import File as MutagenFile  # type: ignore[import-untyped]

        audio = MutagenFile(str(audio_path))
        length = getattr(getattr(audio, "info", None), "length", None)
        if length is not None:
            seconds = float(length)
            if seconds > 0:
                return seconds
    except Exception:
        pass

    def _to_seconds(duration: int | float, time_base: object) -> float | None:
        """Normalize duration and time base to seconds across PyAV variants."""
        try:
            tb = float(time_base)
        except (TypeError, ValueError, OverflowError):
            return None

        if tb <= 0:
            return None

        # Some PyAV builds expose av.time_base as 1_000_000 instead of 1/1_000_000.
        # Detect that case and divide so container.duration is interpreted as seconds.
        if tb > 1:
            return float(duration) / tb
        return float(duration) * tb

    try:
        import av  # type: ignore[import-untyped]

        with av.open(str(audio_path)) as container:
            if container.duration is not None:
                seconds = _to_seconds(container.duration, av.time_base)
                if seconds is not None:
                    return seconds

            audio_streams = [s for s in container.streams if getattr(s, "type", "") == "audio"]
            if audio_streams:
                stream = audio_streams[0]
                if stream.duration is not None and stream.time_base is not None:
                    seconds = _to_seconds(stream.duration, stream.time_base)
                    if seconds is not None:
                        return seconds
    except Exception:
        return None

    return None


def _enforce_audio_limits(saved_path: Path, duration_seconds: float | None) -> None:
    """Enforce file-size and duration caps with user-friendly errors."""
    try:
        size_bytes = saved_path.stat().st_size
    except OSError:
        size_bytes = 0

    max_bytes = _MAX_AUDIO_MB * 1024 * 1024
    if max_bytes > 0 and size_bytes > max_bytes:
        raise UploadError(
            f"This audio file is too large for transcription on this server ({_MAX_AUDIO_MB} MB limit). "
            "Please compress or split the recording and try again."
        )

    if duration_seconds is not None and _MAX_AUDIO_MINUTES > 0:
        if duration_seconds > (_MAX_AUDIO_MINUTES * 60):
            raise UploadError(
                "This recording exceeds the maximum supported length "
                f"({_MAX_AUDIO_MINUTES} minutes). "
                "Please split it into shorter sections and transcribe each section."
            )


def _sanitize_duration_estimate(saved_path: Path, duration_seconds: float | None) -> float | None:
    """Return a trustworthy duration estimate, or None when metadata looks implausible.

    Some files contain broken duration metadata (for example wildly large values).
    If the implied bytes/second is unrealistically low, treat the duration as unknown
    so we can fall back to size-based estimation instead of false >120 minute errors.
    """
    if duration_seconds is None:
        return None

    if duration_seconds <= 0:
        return None

    try:
        size_bytes = saved_path.stat().st_size
    except OSError:
        size_bytes = 0

    if size_bytes > 0:
        implied_bytes_per_second = size_bytes / duration_seconds
        if implied_bytes_per_second < _MIN_PLAUSIBLE_BYTES_PER_SECOND:
            return None

    return duration_seconds


def _require_estimate_acknowledgement() -> None:
    """Require explicit user acknowledgment before starting transcription."""
    if request.form.get("confirm_estimate") != "yes":
        raise UploadError(
            "Please review the estimated processing time and check the confirmation box "
            "before starting transcription."
        )


def _require_uncertain_estimate_acknowledgement() -> None:
    """Require explicit acknowledgment when only a rough size-based estimate is available."""
    source = (request.form.get("estimate_source") or "").strip().lower()
    if source == "size-fallback" and request.form.get("confirm_uncertain_estimate") != "yes":
        raise UploadError(
            "This file's exact duration could not be determined. Please acknowledge the "
            "rough estimate warning before starting transcription."
        )


def _resolve_audio_upload(
    uploaded_file,
    existing_token: str | None = None,
) -> tuple[str, Path, bool, str]:
    """Resolve audio source from fresh upload or previously uploaded token.

    Returns:
        token, saved_path, created_new_token, filename
    """
    if uploaded_file is not None and getattr(uploaded_file, "filename", ""):
        token, saved_path = validate_upload(
            uploaded_file,
            allowed_extensions=AUDIO_EXTENSIONS,
        )
        return token, saved_path, True, saved_path.name

    token = (existing_token or "").strip()
    if not token:
        raise UploadError("No file selected. Please choose an audio file to upload.")

    temp_dir = get_temp_dir(token)
    if temp_dir is None:
        raise UploadError("Your uploaded audio is no longer available. Please select the file again.")

    for candidate in temp_dir.iterdir():
        if candidate.is_file() and candidate.suffix.lower() in AUDIO_EXTENSIONS:
            return token, candidate, False, candidate.name

    raise UploadError("Your uploaded audio could not be found. Please select the file again.")


def _prepare_audio_for_cloud(saved_path: Path) -> Path:
    """Normalize cloud-incompatible audio containers/codecs to MP3 with ffmpeg.

    OpenAI-compatible transcription endpoints are most reliable with mp3/m4a/wav/webm.
    We keep the broader upload list for UX, then transcode unsupported-but-common
    formats into MP3 locally before upload.
    """
    ext = saved_path.suffix.lower()
    if ext in _CLOUD_DIRECT_AUDIO_EXTENSIONS:
        return saved_path

    if ext not in _CLOUD_TRANSCODE_AUDIO_EXTENSIONS:
        return saved_path

    normalized_path = saved_path.with_name(f"{saved_path.stem}.normalized.mp3")
    if normalized_path.exists():
        return normalized_path

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(saved_path),
                "-vn",
                "-acodec",
                "libmp3lame",
                "-ar",
                "44100",
                "-ac",
                "1",
                "-b:a",
                "128k",
                str(normalized_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=_FFMPEG_TIMEOUT_SECONDS,
        )
        return normalized_path
    except subprocess.TimeoutExpired as exc:
        # A hung ffmpeg child would otherwise pin this worker thread forever.
        try:
            normalized_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise UploadError(
            "Audio normalization timed out on this server. "
            "Please convert the file to MP3, M4A, or WAV and try again."
        ) from exc
    except Exception as exc:
        raise UploadError(
            "This audio format needs conversion before cloud transcription, but normalization failed. "
            "Please convert the file to MP3, M4A, or WAV and try again."
        ) from exc


def _prune_terminal_jobs_locked(now: datetime | None = None) -> None:
    """Drop old terminal (complete/failed) jobs. Caller must hold _jobs_lock.

    Without this, foreground and failed jobs accumulated in _jobs for the whole
    process lifetime (only background jobs were ever removed, via their 4-hour
    cleanup Timer). Background completed jobs that are still retrievable are
    exempt so we never delete a transcript out from under a pending retrieval.
    """
    now = now or datetime.now(UTC)
    cutoff = timedelta(hours=_TERMINAL_JOB_RETENTION_HOURS)
    for job_id in list(_jobs.keys()):
        job = _jobs.get(job_id)
        if job is None or job.status not in ("complete", "failed"):
            continue
        # Keep background transcripts alive until their retrieval window closes.
        if job.is_background and job.status == "complete" and not job.retrieved:
            if job.retrieval_expires_at is None or now <= job.retrieval_expires_at:
                continue
        marker = job.completed_at or job.started_at or job.queued_at
        if marker is None:
            continue
        if now - marker > cutoff:
            del _jobs[job_id]


def _set_job(job: _WhisperJob) -> None:
    with _jobs_lock:
        _prune_terminal_jobs_locked()
        _jobs[job.job_id] = job


def _get_job(job_id: str) -> _WhisperJob | None:
    with _jobs_lock:
        return _jobs.get(job_id)


def _delete_job(job_id: str) -> None:
    with _jobs_lock:
        _jobs.pop(job_id, None)


def _queue_position(job_id: str) -> int | None:
    with _jobs_lock:
        try:
            return list(_audio_queue).index(job_id) + 1
        except ValueError:
            return None


def _update_job(
    job_id: str,
    *,
    status: str | None = None,
    progress: int | None = None,
    message: str | None = None,
    error: str | None = None,
    output_path: Path | None = None,
    mimetype: str | None = None,
    download_name: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    retrieval_expires_at: datetime | None = None,
    retrieved: bool | None = None,
) -> None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = max(0, min(100, int(progress)))
        if message is not None:
            job.message = message
        if error is not None:
            job.error = error
        if output_path is not None:
            job.output_path = output_path
        if mimetype is not None:
            job.mimetype = mimetype
        if download_name is not None:
            job.download_name = download_name
        if started_at is not None:
            job.started_at = started_at
        if completed_at is not None:
            job.completed_at = completed_at
        if retrieval_expires_at is not None:
            job.retrieval_expires_at = retrieval_expires_at
        if retrieved is not None:
            job.retrieved = retrieved


def _validate_email_address(address: str) -> None:
    value = (address or "").strip()
    if not value:
        raise UploadError("Please provide an email address for background processing.")
    if len(value) > 254 or not _EMAIL_RE.match(value):
        raise UploadError("Please provide a valid email address.")


def _validate_retrieval_password(password: str, confirm: str) -> None:
    if not password:
        raise UploadError("Please create a retrieval password for secure access.")
    if password != confirm:
        raise UploadError("Retrieval password and confirmation do not match.")
    if len(password) < 8:
        raise UploadError("Retrieval password must be at least 8 characters.")
    has_digit = any(ch.isdigit() for ch in password)
    has_symbol = any(not ch.isalnum() for ch in password)
    if not (has_digit or has_symbol):
        raise UploadError("Retrieval password must include at least one number or symbol.")


def _send_job_email(job: _WhisperJob, phase: str) -> None:
    if not job.notify_email:
        return

    if phase == "queued":
        position = _queue_position(job.job_id)
        subject = "GLOW BITS Whisperer job queued"
        text = (
            "Your audio transcription request is queued.\n\n"
            f"Queue position: {position if position is not None else 'processing soon'}\n"
            "You will receive another email when transcription starts."
        )
        html = (
            "<p>Your audio transcription request is queued.</p>"
            f"<p><strong>Queue position:</strong> {position if position is not None else 'processing soon'}</p>"
            "<p>You will receive another email when transcription starts.</p>"
        )
    elif phase == "started":
        subject = "GLOW BITS Whisperer job started"
        text = "Your queued audio transcription has started on the server."
        html = "<p>Your queued audio transcription has started on the server.</p>"
    elif phase == "completed":
        subject = "GLOW BITS Whisperer job complete"
        path = f"/whisperer/retrieve/{job.retrieval_token}"
        # Prefer the absolute URL resolved in the request context at submission
        # time. The worker thread has no request/app context, so url_for(...,
        # _external=True) here would raise RuntimeError and fall back to a
        # relative (dead-in-email) path.
        if job.retrieval_url:
            link = job.retrieval_url
        else:
            base_url = os.environ.get("GLOW_PUBLIC_BASE_URL", "").rstrip("/")
            if base_url:
                link = f"{base_url}{path}"
            else:
                try:
                    link = url_for("whisperer.whisperer_retrieve", token=job.retrieval_token, _external=True)
                except RuntimeError:
                    link = path
        expiry = job.retrieval_expires_at.isoformat() if job.retrieval_expires_at else "4 hours"
        text = (
            "Your audio transcription is ready.\n\n"
            f"Retrieve link: {link}\n"
            "Use the retrieval password you created at submission.\n"
            f"This link is single-use and expires at: {expiry}."
        )
        html = (
            "<p>Your audio transcription is ready.</p>"
            f"<p><a href=\"{link}\">Open secure retrieval link</a></p>"
            "<p>Use the retrieval password you created at submission.</p>"
            f"<p>This link is single-use and expires at: <strong>{expiry}</strong>.</p>"
        )
    elif phase == "cleared":
        subject = "GLOW BITS Whisperer content cleared"
        text = (
            "Your completed audio transcription was not retrieved within the retention window.\n"
            "The content has been cleared from the server.\n"
            "Please upload and process the file again if needed."
        )
        html = (
            "<p>Your completed audio transcription was not retrieved within the retention window.</p>"
            "<p>The content has been cleared from the server.</p>"
            "<p>Please upload and process the file again if needed.</p>"
        )
    else:
        return

    send_whisperer_status_email(job.notify_email, subject, html, text)


def _cleanup_unretrieved_job(job_id: str) -> None:
    job = _get_job(job_id)
    if job is None:
        return
    if job.status != "complete" or job.retrieved:
        return
    _send_job_email(job, "cleared")
    cleanup_token(job.token)
    _delete_job(job.job_id)


def _dispatch_queued_jobs() -> None:
    """Start queued jobs while audio gate capacity is available."""
    from ..gating import get_capacity_metrics

    capacity = get_capacity_metrics().get("audio", {}).get("available", 0)
    if capacity <= 0:
        return

    for _ in range(int(capacity)):
        with _jobs_lock:
            if not _audio_queue:
                return
            job_id = _audio_queue.popleft()
            job = _jobs.get(job_id)
            if job is None:
                continue
            job.status = "running"
            job.progress = 1
            job.message = "Initializing transcription..."
            job.started_at = datetime.now(UTC)

        if job.notify_email:
            _send_job_email(job, "started")

        thread = threading.Thread(target=_run_whisper_job, args=(job_id,), daemon=True)
        thread.start()


def get_admin_queue_snapshot(limit_recent: int = 100) -> list[dict]:
    """Return queue/running/completed/failed snapshot for admin dashboard."""
    with _jobs_lock:
        queue_order = list(_audio_queue)
        rows: list[dict] = []
        for job in _jobs.values():
            queue_position = None
            if job.job_id in queue_order:
                queue_position = queue_order.index(job.job_id) + 1

            rows.append(
                {
                    "job_id": job.job_id,
                    "status": job.status,
                    "progress": job.progress,
                    "message": job.message,
                    "queued_at": job.queued_at,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "is_background": job.is_background,
                    "notify_email": job.notify_email,
                    "queue_position": queue_position,
                }
            )

    def _sort_key(row: dict):
        return row.get("queued_at") or datetime.min.replace(tzinfo=UTC)

    rows.sort(key=_sort_key, reverse=True)
    return rows[:limit_recent]


def admin_cancel_queued_job(job_id: str) -> tuple[bool, str]:
    """Cancel a queued job (admin operation)."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return False, "Job not found."
        if job_id not in _audio_queue:
            return False, "Only queued jobs can be canceled."
        _audio_queue.remove(job_id)
        job.status = "failed"
        job.progress = 0
        job.message = "Canceled by admin before processing."
        job.error = "Canceled by admin."

    cleanup_token(job.token)
    return True, "Queued job canceled."


def admin_requeue_failed_job(job_id: str) -> tuple[bool, str]:
    """Requeue a failed job when source upload still exists."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            return False, "Job not found."
        if job.status != "failed":
            return False, "Only failed jobs can be re-queued."
        if job_id in _audio_queue:
            return False, "Job is already queued."
        if len(_audio_queue) >= _MAX_AUDIO_QUEUE_DEPTH:
            return False, "Queue is full."

        temp_dir = get_temp_dir(job.token)
        if temp_dir is None or not job.saved_path.exists():
            return False, "Cannot re-queue because source audio is no longer available."

        job.status = "queued"
        job.progress = 0
        job.message = "Queued..."
        job.error = None
        job.started_at = None
        job.completed_at = None
        _audio_queue.append(job_id)

    _dispatch_queued_jobs()
    return True, "Failed job re-queued."


def _run_whisper_job(job_id: str) -> None:
    job = _get_job(job_id)
    if job is None:
        return

    requeued = False
    try:
        ext = job.saved_path.suffix.lower()
        if ext not in AUDIO_EXTENSIONS:
            raise UploadError(
                f"'{ext}' is not a supported audio format. "
                f"Supported: {', '.join(sorted(AUDIO_EXTENSIONS))}."
            )

        temp_dir = get_temp_dir(job.token)
        if temp_dir is None:
            raise UploadError("Upload session expired. Please upload the audio again.")

        _touch_token_dir(job.token)

        md_output = temp_dir / f"{job.saved_path.stem}.md"

        try:
            _update_job(
                job_id,
                status="running",
                progress=1,
                message=(
                    "Connecting to transcription service..."
                ),
            )
            with audio_gate():
                transcript_text = gateway_transcribe(
                    job.saved_path,
                    language=job.language,
                    session_hash="background",
                )
                md_output.write_text(transcript_text, encoding="utf-8")
                transcript_path = md_output
                _update_job(job_id, status="running", progress=80, message="Transcription complete. Formatting output...")
                _touch_token_dir(job.token)
        except GatingError:
            with _jobs_lock:
                _audio_queue.appendleft(job_id)
                job = _jobs.get(job_id)
                if job is not None:
                    job.status = "queued"
                    job.progress = 0
                    job.message = "Queued... waiting for audio capacity."
            requeued = True
            return

        if job.output_format == "word":
            if not pandoc_available():
                raise UploadError(
                    "Pandoc is not installed on this server. "
                    "Audio-to-Word conversion requires Pandoc for the final step. "
                    "Choose Markdown output instead."
                )

            _update_job(
                job_id,
                status="running",
                progress=97,
                message="Transcription complete. Building Word document...",
            )
            _touch_token_dir(job.token)
            user_title = (job.title or "").strip()
            title = user_title or job.saved_path.stem.replace("-", " ").replace("_", " ")
            docx_output = temp_dir / f"{job.saved_path.stem}.docx"
            output_path, _ = convert_to_docx(
                transcript_path,
                output_path=docx_output,
                title=title,
            )
            _touch_token_dir(job.token)
            _update_job(
                job_id,
                status="complete",
                progress=100,
                message="Complete. Your file is ready to download.",
                output_path=output_path,
                mimetype=(
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                ),
                download_name=f"{job.saved_path.stem}.docx",
            )
            # Refresh the token dir mtime at completion so the finished
            # transcript survives the retrieval window rather than being swept
            # UPLOAD_MAX_AGE_HOURS after the last processing touch.
            _touch_token_dir(job.token)
            job = _get_job(job_id)
            if job and job.is_background and job.notify_email:
                expiry = datetime.now(UTC) + timedelta(hours=_RETRIEVAL_HOURS)
                _update_job(job_id, retrieval_expires_at=expiry, completed_at=datetime.now(UTC))
                job = _get_job(job_id)
                _send_job_email(job, "completed")
                if not job.cleanup_timer_set:
                    timer = threading.Timer(_RETRIEVAL_HOURS * 3600, _cleanup_unretrieved_job, args=(job_id,))
                    timer.daemon = True
                    timer.start()
                    with _jobs_lock:
                        if _jobs.get(job_id):
                            _jobs[job_id].cleanup_timer_set = True
            return

        _update_job(
            job_id,
            status="complete",
            progress=100,
            message="Complete. Your file is ready to download.",
            output_path=transcript_path,
            mimetype="text/markdown; charset=utf-8",
            download_name=f"{job.saved_path.stem}.md",
            completed_at=datetime.now(UTC),
        )
        # Refresh the token dir mtime at completion so the finished transcript
        # survives the retrieval window rather than being swept
        # UPLOAD_MAX_AGE_HOURS after the last processing touch.
        _touch_token_dir(job.token)
        job = _get_job(job_id)
        if job and job.is_background and job.notify_email:
            expiry = datetime.now(UTC) + timedelta(hours=_RETRIEVAL_HOURS)
            _update_job(job_id, retrieval_expires_at=expiry)
            job = _get_job(job_id)
            _send_job_email(job, "completed")
            if not job.cleanup_timer_set:
                timer = threading.Timer(_RETRIEVAL_HOURS * 3600, _cleanup_unretrieved_job, args=(job_id,))
                timer.daemon = True
                timer.start()
                with _jobs_lock:
                    if _jobs.get(job_id):
                        _jobs[job_id].cleanup_timer_set = True
    except Exception as exc:
        # Catch *any* failure (OSError, MemoryError, requests errors,
        # CalledProcessError, ...), not just the previously-narrow set -- an
        # uncaught exception here left the job stuck "running" forever and, worse,
        # skipped queue advancement so every job behind it stalled. We do not
        # catch BaseException (KeyboardInterrupt/SystemExit must propagate).
        _update_job(
            job_id,
            status="failed",
            progress=0,
            message=str(exc) or "Transcription failed due to an unexpected error.",
            error=str(exc) or exc.__class__.__name__,
        )
        cleanup_token(job.token)
    finally:
        # Always advance the queue so a finished, failed, or re-queued job never
        # strands the jobs behind it. On re-queue, only dispatch when a slot is
        # actually free -- _dispatch_queued_jobs() itself returns early when audio
        # capacity is 0, so this cannot spin into unbounded re-dispatch.
        if requeued:
            from ..gating import get_capacity_metrics

            if get_capacity_metrics().get("audio", {}).get("available", 0) > 0:
                _dispatch_queued_jobs()
        else:
            _dispatch_queued_jobs()


@whisperer_bp.route("/", methods=["GET"])
def whisperer_form():
    _require_whisperer_feature()
    return render_template("whisperer_form.html", **_template_context(estimate_ready=False))


@whisperer_bp.route("/estimate", methods=["POST"])
def whisperer_estimate():
    """Return a best-effort transcription time estimate for an uploaded audio file.

    Uses PyAV metadata when available; falls back to file-size-based estimate.
    This endpoint is intentionally lightweight and always cleans up the temp token.
    """
    _require_whisperer_feature()
    token = None
    try:
        debug_requested = request.args.get("debug") == "1" or request.headers.get("X-Whisperer-Debug") == "1"
        uploaded_file = request.files.get("audio")
        uploaded_name = getattr(uploaded_file, "filename", None) or "(missing)"

        token, saved_path = validate_upload(
            uploaded_file,
            allowed_extensions=AUDIO_EXTENSIONS,
        )

        ext = saved_path.suffix.lower()
        if ext not in AUDIO_EXTENSIONS:
            raise UploadError(
                f"'{ext}' is not a supported audio format. "
                f"Supported: {', '.join(sorted(AUDIO_EXTENSIONS))}."
            )

        duration_seconds = _sanitize_duration_estimate(
            saved_path,
            _estimate_audio_duration_seconds(saved_path),
        )
        _enforce_audio_limits(saved_path, duration_seconds)

        try:
            size_bytes = saved_path.stat().st_size
        except OSError:
            size_bytes = 0

        source = "metadata"
        audio_seconds = duration_seconds
        if audio_seconds is None or audio_seconds <= 0:
            source = "size-fallback"
            audio_seconds = max(1.0, size_bytes / _ESTIMATE_BYTES_PER_SECOND)

        expected_seconds = max(15.0, float(audio_seconds) * 1.1)

        current_app.logger.info(
            "WHISPERER_ESTIMATE ok file=%s ext=%s size=%s source=%s audio_seconds=%.6f expected_seconds=%.6f",
            uploaded_name,
            ext,
            int(size_bytes),
            source,
            float(audio_seconds),
            float(expected_seconds),
        )

        payload = {
            "audio_seconds": float(audio_seconds),
            "expected_seconds": float(expected_seconds),
            "source": source,
            "size_bytes": int(size_bytes),
        }
        if debug_requested:
            payload["debug"] = {
                "filename": uploaded_name,
                "extension": ext,
                "duration_probe": "metadata" if duration_seconds is not None else "fallback",
            }

        return jsonify(payload)
    except UploadError as exc:
        current_app.logger.warning(
            "WHISPERER_ESTIMATE upload_error file=%s error=%s",
            getattr(request.files.get("audio"), "filename", "(missing)"),
            str(exc),
        )
        return jsonify({"error": str(exc)}), 400
    except Exception:
        current_app.logger.exception(
            "WHISPERER_ESTIMATE unexpected_error file=%s",
            getattr(request.files.get("audio"), "filename", "(missing)"),
        )
        return jsonify({"error": "Unable to estimate processing time due to an unexpected server error."}), 500
    finally:
        if token:
            cleanup_token(token)


@whisperer_bp.route("/estimate-page", methods=["POST"])
def whisperer_estimate_page():
    """Server-side estimate flow that re-renders the form with estimate values."""
    _require_whisperer_feature()
    token = None
    created_new_token = False
    try:
        token, saved_path, created_new_token, uploaded_name = _resolve_audio_upload(
            request.files.get("audio"),
            existing_token=request.form.get("existing_token"),
        )

        ext = saved_path.suffix.lower()
        if ext not in AUDIO_EXTENSIONS:
            raise UploadError(
                f"'{ext}' is not a supported audio format. "
                f"Supported: {', '.join(sorted(AUDIO_EXTENSIONS))}."
            )

        duration_seconds = _sanitize_duration_estimate(
            saved_path,
            _estimate_audio_duration_seconds(saved_path),
        )
        _enforce_audio_limits(saved_path, duration_seconds)

        try:
            size_bytes = saved_path.stat().st_size
        except OSError:
            size_bytes = 0

        source = "metadata"
        audio_seconds = duration_seconds
        if audio_seconds is None or audio_seconds <= 0:
            source = "size-fallback"
            audio_seconds = max(1.0, size_bytes / _ESTIMATE_BYTES_PER_SECOND)

        expected_seconds = max(15.0, float(audio_seconds) * 1.1)

        return render_template(
            "whisperer_form.html",
            **_template_context(
                estimate_audio_seconds=float(audio_seconds),
                estimate_expected_seconds=float(expected_seconds),
                estimate_source=source,
                existing_token=token,
                uploaded_filename=uploaded_name,
                estimate_ready=True,
            ),
        )
    except UploadError as exc:
        if token and created_new_token:
            cleanup_token(token)
        return render_template(
            "whisperer_form.html",
            **_template_context(
                estimate_error=str(exc),
                existing_token=request.form.get("existing_token"),
                uploaded_filename=request.form.get("uploaded_filename"),
                estimate_ready=False,
            ),
        ), 400


@whisperer_bp.route("/", methods=["POST"])
def whisperer_submit():
    _require_whisperer_feature()
    token = None
    created_new_token = False
    try:
        from ..tool_usage import record as _record_usage
        _record_usage("whisperer")
        token, saved_path, created_new_token, uploaded_name = _resolve_audio_upload(
            request.files.get("audio"),
            existing_token=request.form.get("existing_token"),
        )
        _require_estimate_acknowledgement()
        ext = saved_path.suffix.lower()

        if not is_whisper_configured():
            raise UploadError(
                "BITS Whisperer is not configured on this server. "
                "Please contact the administrator."
            )

        if ext not in AUDIO_EXTENSIONS:
            raise UploadError(
                f"'{ext}' is not a supported audio format. "
                f"Supported: {', '.join(sorted(AUDIO_EXTENSIONS))}."
            )

        duration_seconds = _sanitize_duration_estimate(
            saved_path,
            _estimate_audio_duration_seconds(saved_path),
        )
        _enforce_audio_limits(saved_path, duration_seconds)
        _require_uncertain_estimate_acknowledgement()

        temp_dir = get_temp_dir(token)
        if temp_dir is None:
            raise UploadError("Upload session expired. Please upload the audio again.")
        language = request.form.get("language") or None
        output_format = request.form.get("output_format", "markdown")

        cloud_audio_path = _prepare_audio_for_cloud(saved_path)
        md_output = temp_dir / f"{saved_path.stem}.md"

        try:
            with audio_gate():
                transcript_text = gateway_transcribe(
                    cloud_audio_path,
                    language=language,
                    session_hash=request.cookies.get("session", "anonymous")[:24],
                )
                md_output.write_text(transcript_text, encoding="utf-8")
                transcript_path = md_output
        except GatingError:
            return _busy_response()

        if output_format == "word":
            if not pandoc_available():
                raise UploadError(
                    "Pandoc is not installed on this server. "
                    "Audio-to-Word conversion requires Pandoc for the final step. "
                    "Choose Markdown output instead."
                )
            user_title = request.form.get("title", "").strip()
            title = user_title or saved_path.stem.replace("-", " ").replace("_", " ")
            docx_output = temp_dir / f"{saved_path.stem}.docx"
            output_path, _ = convert_to_docx(
                transcript_path,
                output_path=docx_output,
                title=title,
            )
            return send_file(
                str(output_path),
                mimetype=(
                    "application/vnd.openxmlformats-officedocument"
                    ".wordprocessingml.document"
                ),
                as_attachment=True,
                download_name=f"{saved_path.stem}.docx",
            )
        else:
            # Markdown (default)
            return send_file(
                str(transcript_path),
                mimetype="text/markdown; charset=utf-8",
                as_attachment=True,
                download_name=f"{saved_path.stem}.md",
            )

    except UploadError as exc:
        return (
            render_template(
                "whisperer_form.html",
                error=str(exc),
                **_template_context(
                    existing_token=request.form.get("existing_token"),
                    uploaded_filename=request.form.get("uploaded_filename") or uploaded_name if 'uploaded_name' in locals() else request.form.get("uploaded_filename"),
                    estimate_ready=bool(request.form.get("existing_token")),
                ),
            ),
            400,
        )
    except RuntimeError as exc:
        return (
            render_template(
                "whisperer_form.html",
                error=str(exc),
                **_template_context(
                    existing_token=request.form.get("existing_token"),
                    uploaded_filename=request.form.get("uploaded_filename") or uploaded_name if 'uploaded_name' in locals() else request.form.get("uploaded_filename"),
                    estimate_ready=bool(request.form.get("existing_token")),
                ),
            ),
            500,
        )
    except Exception as exc:
        current_app.logger.exception("WHISPERER_SUBMIT unexpected_error")
        error_message = str(exc) if str(exc) else "Something went wrong while processing this transcription request. Please try again."
        return (
            render_template(
                "whisperer_form.html",
                error=error_message,
                **_template_context(
                    existing_token=request.form.get("existing_token"),
                    uploaded_filename=request.form.get("uploaded_filename") or uploaded_name if 'uploaded_name' in locals() else request.form.get("uploaded_filename"),
                    estimate_ready=bool(request.form.get("existing_token")),
                ),
            ),
            500,
        )
    finally:
        if token and created_new_token:
            cleanup_token(token)


@whisperer_bp.route("/start", methods=["POST"])
def whisperer_start_job():
    """Start a background Whisper transcription job and return a job id."""
    _require_whisperer_feature()
    token = None
    created_new_token = False
    try:
        if not is_whisper_configured():
            raise UploadError(
                "BITS Whisperer is not configured on this server. "
                "Please contact the administrator."
            )

        token, saved_path, created_new_token, uploaded_name = _resolve_audio_upload(
            request.files.get("audio"),
            existing_token=request.form.get("existing_token"),
        )
        _require_estimate_acknowledgement()

        ext = saved_path.suffix.lower()
        if ext not in AUDIO_EXTENSIONS:
            raise UploadError(
                f"'{ext}' is not a supported audio format. "
                f"Supported: {', '.join(sorted(AUDIO_EXTENSIONS))}."
            )

        cloud_audio_path = _prepare_audio_for_cloud(saved_path)

        duration_seconds = _sanitize_duration_estimate(
            saved_path,
            _estimate_audio_duration_seconds(saved_path),
        )
        _enforce_audio_limits(saved_path, duration_seconds)
        _require_uncertain_estimate_acknowledgement()

        background_opt_in = request.form.get("background_opt_in") == "yes"
        notify_email = (request.form.get("notify_email") or "").strip()
        retrieval_password = request.form.get("retrieval_password") or ""
        retrieval_password_confirm = request.form.get("retrieval_password_confirm") or ""

        if background_opt_in:
            if not email_configured():
                raise UploadError(
                    "Background transcription with secure retrieval requires email service to be configured by the administrator."
                )
            _validate_email_address(notify_email)
            _validate_retrieval_password(retrieval_password, retrieval_password_confirm)

        output_format = request.form.get("output_format", "markdown")
        if output_format not in {"markdown", "word"}:
            raise UploadError("Invalid output format selected.")

        if output_format == "word" and not pandoc_available():
            raise UploadError(
                "Pandoc is not installed on this server. "
                "Audio-to-Word conversion requires Pandoc for the final step. "
                "Choose Markdown output instead."
            )

        job_id = str(uuid.uuid4())
        retrieval_token = secrets.token_urlsafe(32) if background_opt_in else None
        # Resolve the absolute retrieval URL now, while a request context exists.
        # The worker thread that sends the completion email has no request/app
        # context, so url_for(_external=True) there would raise and fall back to
        # a relative, dead-in-email link. Prefer the operator-configured public
        # base URL; otherwise resolve from the current request.
        retrieval_url = None
        if retrieval_token:
            base_url = os.environ.get("GLOW_PUBLIC_BASE_URL", "").rstrip("/")
            if base_url:
                retrieval_url = f"{base_url}/whisperer/retrieve/{retrieval_token}"
            else:
                try:
                    retrieval_url = url_for(
                        "whisperer.whisperer_retrieve", token=retrieval_token, _external=True
                    )
                except Exception:
                    retrieval_url = None
        job = _WhisperJob(
            job_id=job_id,
            token=token,
            saved_path=cloud_audio_path,
            language=request.form.get("language") or None,
            output_format=output_format,
            title=request.form.get("title") or None,
            status="queued",
            progress=0,
            message=(
                "Queued..."
                if duration_seconds is None
                else f"Queued... estimated audio length: {round(duration_seconds / 60, 1)} minutes."
            ),
            queued_at=datetime.now(UTC),
            is_background=background_opt_in,
            notify_email=notify_email if background_opt_in else None,
            retrieval_token=retrieval_token,
            retrieval_url=retrieval_url,
            retrieval_password_hash=generate_password_hash(retrieval_password) if background_opt_in else None,
        )
        _set_job(job)

        with _jobs_lock:
            queue_full = len(_audio_queue) >= _MAX_AUDIO_QUEUE_DEPTH
            if not queue_full:
                _audio_queue.append(job_id)
        if queue_full:
            # Do not call the lock-taking helpers while holding _jobs_lock:
            # _jobs_lock is a plain (non-reentrant) Lock, so _delete_job would
            # deadlock the worker and, through it, every route that touches
            # the lock (progress polling, dispatch, the admin queue page).
            _delete_job(job_id)
            cleanup_token(token)
            return jsonify({
                "error": (
                    "The audio queue is currently full. Please try again in a few minutes."
                )
            }), 503

        if job.notify_email:
            _send_job_email(job, "queued")

        _dispatch_queued_jobs()

        return (
            jsonify(
                {
                    "job_id": job_id,
                    "status": "queued",
                    "progress": 0,
                    "message": "Queued...",
                    "progress_url": url_for("whisperer.whisperer_job_progress", job_id=job_id),
                    "download_url": url_for("whisperer.whisperer_job_download", job_id=job_id),
                    "background_opt_in": background_opt_in,
                }
            ),
            202,
        )
    except UploadError as exc:
        if token and created_new_token:
            cleanup_token(token)
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        if token and created_new_token:
            cleanup_token(token)
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        current_app.logger.exception("WHISPERER_START unexpected_error")
        if token and created_new_token:
            cleanup_token(token)
        return jsonify({"error": str(exc) or "Something went wrong starting this transcription job. Please try again."}), 500


@whisperer_bp.route("/progress/<job_id>", methods=["GET"])
def whisperer_job_progress(job_id: str):
    """Return JSON progress for a running or completed Whisper job."""
    _require_whisperer_feature()
    job = _get_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found or expired."}), 404

    payload = {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "background_opt_in": job.is_background,
    }
    if job.status == "queued":
        payload["queue_position"] = _queue_position(job.job_id)
    if job.error:
        payload["error"] = job.error
    if job.status == "complete":
        payload["download_url"] = url_for("whisperer.whisperer_job_download", job_id=job.job_id)

    return jsonify(payload)


@whisperer_bp.route("/download/<job_id>", methods=["GET"])
def whisperer_job_download(job_id: str):
    """Download the completed Whisper output and clean up job resources."""
    _require_whisperer_feature()
    job = _get_job(job_id)
    if job is None:
        return render_template("whisperer_form.html", error="Job not found or expired.", **_template_context()), 404

    if job.status != "complete" or job.output_path is None:
        return (
            render_template(
                "whisperer_form.html",
                error="Transcription is not complete yet. Please wait for 100% progress.",
                **_template_context(),
            ),
            409,
        )

    path = Path(job.output_path)
    if not path.exists():
        cleanup_token(job.token)
        _delete_job(job.job_id)
        return (
            render_template(
                "whisperer_form.html",
                error="The output file is no longer available. Please run transcription again.",
                **_template_context(),
            ),
            404,
        )

    @after_this_request
    def _cleanup_after_download(response):
        cleanup_token(job.token)
        _delete_job(job.job_id)
        return response

    return send_file(
        str(path),
        mimetype=job.mimetype or "application/octet-stream",
        as_attachment=True,
        download_name=job.download_name or path.name,
    )


@whisperer_bp.route("/retrieve/<token>", methods=["GET", "POST"])
def whisperer_retrieve(token: str):
    """Secure retrieval endpoint for background jobs (link + password)."""
    _require_whisperer_feature()
    job = None
    with _jobs_lock:
        for _job in _jobs.values():
            if _job.retrieval_token and hmac.compare_digest(_job.retrieval_token, token):
                job = _job
                break

    if job is None or not job.is_background:
        return render_template("whisperer_form.html", error="Secure retrieval link is invalid or expired.", **_template_context()), 404

    if request.method == "GET":
        return render_template(
            "whisperer_retrieve.html",
            token=token,
            retrieval_hours=_RETRIEVAL_HOURS,
            expired=bool(job.retrieval_expires_at and datetime.now(UTC) > job.retrieval_expires_at),
        )

    if job.retrieval_expires_at and datetime.now(UTC) > job.retrieval_expires_at:
        cleanup_token(job.token)
        _delete_job(job.job_id)
        return render_template("whisperer_retrieve.html", token=token, expired=True, error="This retrieval link has expired."), 410

    password = request.form.get("retrieval_password", "")
    if not job.retrieval_password_hash or not check_password_hash(job.retrieval_password_hash, password):
        return render_template("whisperer_retrieve.html", token=token, error="Invalid retrieval password."), 403

    if job.retrieved:
        return render_template("whisperer_retrieve.html", token=token, expired=True, error="This retrieval link has already been used."), 410

    if job.status != "complete" or job.output_path is None:
        return render_template("whisperer_retrieve.html", token=token, error="Your transcription is not ready yet. Please check email updates and try again."), 409

    path = Path(job.output_path)
    if not path.exists():
        cleanup_token(job.token)
        _delete_job(job.job_id)
        return render_template("whisperer_retrieve.html", token=token, expired=True, error="The transcript is no longer available."), 404

    _update_job(job.job_id, retrieved=True)

    @after_this_request
    def _cleanup_after_secure_download(response):
        cleanup_token(job.token)
        _delete_job(job.job_id)
        return response

    return send_file(
        str(path),
        mimetype=job.mimetype or "application/octet-stream",
        as_attachment=True,
        download_name=job.download_name or path.name,
    )
