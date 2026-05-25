"""Job status routes: SSE stream, JSON poll, result download, and progress page.

Endpoints
─────────
  GET /job/<id>/status      Server-Sent Events stream (EventSource)
  GET /job/<id>/poll        JSON status snapshot (for browsers without SSE)
  GET /job/<id>/result      Stream / download the completed result file
  GET /job/<id>/            Progress page (HTML with live progress bar)
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    abort,
    redirect,
    render_template,
    request,
    stream_with_context,
    url_for,
)

from ..tasks.convert_tasks import _job_dir, read_status, request_cancel, retry_convert_job

log = logging.getLogger(__name__)
jobs_bp = Blueprint("jobs", __name__)

# How often the SSE generator polls the status file (seconds)
_SSE_POLL_INTERVAL = 0.5
# Maximum SSE stream duration before forcing a close (prevents zombie connections)
_SSE_MAX_SECONDS = 30 * 60  # 30 minutes


# ---------------------------------------------------------------------------
# Progress page (entry point for async convert redirects)
# ---------------------------------------------------------------------------

@jobs_bp.route("/<job_id>/")
@jobs_bp.route("/<job_id>")
def job_progress(job_id: str):
    """Render the live progress page for a queued job."""
    status = read_status(job_id)
    if status.get("state") == "MISSING":
        abort(404)
    return render_template(
        "jobs/progress.html",
        job_id=job_id,
        job_status=status,
    )


# ---------------------------------------------------------------------------
# SSE status stream
# ---------------------------------------------------------------------------

@jobs_bp.route("/<job_id>/status")
def job_status_stream(job_id: str):
    """Server-Sent Events endpoint.  Streams progress events until done/error."""
    # Validate job exists before opening stream
    if read_status(job_id).get("state") == "MISSING":
        abort(404)

    @stream_with_context
    def _generate():
        deadline = time.monotonic() + _SSE_MAX_SECONDS
        last_progress = -1
        last_state = ""

        while time.monotonic() < deadline:
            status = read_status(job_id)
            state = status.get("state", "PENDING")
            progress = int(status.get("progress", 0))

            # Only emit when something changed
            if progress != last_progress or state != last_state:
                last_progress = progress
                last_state = state
                payload = json.dumps({
                    "state": state,
                    "progress": progress,
                    "message": status.get("message", ""),
                    "error": status.get("error", ""),
                    "result_file": status.get("result_file", ""),
                    "continue_url": status.get("continue_url", ""),
                    "attempt": int(status.get("attempt", 0)),
                    "max_attempts": int(status.get("max_attempts", 1)),
                    "retryable": bool(status.get("retryable", False)),
                    "deadline_at": status.get("deadline_at"),
                })
                if state in ("SUCCESS", "FAILURE", "CANCELLED"):
                    yield f"event: {state.lower()}\ndata: {payload}\n\n"
                    return  # Close stream after terminal event
                else:
                    yield f"data: {payload}\n\n"

            # Keep-alive comment every poll cycle
            yield ": heartbeat\n\n"
            time.sleep(_SSE_POLL_INTERVAL)

        # Timeout: send a special timeout event
        yield 'event: timeout\ndata: {"state":"TIMEOUT","message":"Job timed out"}\n\n'

    return Response(
        _generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# JSON poll (fallback for environments where EventSource is unavailable)
# ---------------------------------------------------------------------------

@jobs_bp.route("/<job_id>/poll")
def job_status_poll(job_id: str):
    """Return a one-shot JSON status snapshot."""
    status = read_status(job_id)
    if status.get("state") == "MISSING":
        abort(404)
    return status


# ---------------------------------------------------------------------------
# Result file download
# ---------------------------------------------------------------------------

# Allowed result extensions to prevent path traversal
_ALLOWED_RESULT_EXTS = {
    ".md", ".html", ".htm", ".json", ".docx", ".odt", ".epub", ".pdf", ".zip",
    ".mp3", ".wav",
}
_RESULT_MIMETYPES = {
    ".md": "text/markdown; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".epub": "application/epub+zip",
    ".pdf": "application/pdf",
    ".zip": "application/zip",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}


@jobs_bp.route("/<job_id>/result")
def job_result(job_id: str):
    """Serve the completed result file for download."""
    status = read_status(job_id)
    if status.get("state") != "SUCCESS":
        abort(404)

    result_file = status.get("result_file", "")
    if not result_file:
        abort(404)

    # Reject filenames with path traversal sequences
    result_file = os.path.basename(result_file)
    ext = Path(result_file).suffix.lower()
    if ext not in _ALLOWED_RESULT_EXTS:
        abort(404)

    try:
        out_dir = _job_dir(job_id, create=False)
    except ValueError:
        abort(404)

    file_path = out_dir / result_file
    if not file_path.exists():
        abort(404)

    # Verify the file is actually inside the expected directory (defence in depth)
    try:
        file_path.resolve().relative_to(out_dir.resolve())
    except ValueError:
        abort(403)

    mimetype = _RESULT_MIMETYPES.get(ext, "application/octet-stream")
    original_filename = status.get("filename", result_file)
    stem = Path(original_filename).stem if original_filename else Path(result_file).stem
    download_name = f"{stem}{ext}"

    return Response(
        _stream_file(file_path),
        mimetype=mimetype,
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"',
            "Content-Length": str(file_path.stat().st_size),
        },
    )


@jobs_bp.route("/<job_id>/cancel", methods=["POST"])
def job_cancel(job_id: str):
    status = read_status(job_id)
    if status.get("state") == "MISSING":
        abort(404)
    request_cancel(job_id)
    return redirect(url_for("jobs.job_progress", job_id=job_id))


@jobs_bp.route("/<job_id>/retry", methods=["POST"])
def job_retry(job_id: str):
    status = read_status(job_id)
    if status.get("state") == "MISSING":
        abort(404)
    retry_convert_job(job_id)
    return redirect(url_for("jobs.job_progress", job_id=job_id))


def _stream_file(path: Path, chunk_size: int = 65536):
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            yield chunk
