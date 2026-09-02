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

import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
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
from ..upload import (
    AUDIO_EXTENSIONS,
    UPLOAD_TEMP_BASE,
    UploadError,
    cleanup_token,
    get_temp_dir,
    validate_upload,
)

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


# ---------------------------------------------------------------------------
# Shared, cross-worker job store
# ---------------------------------------------------------------------------
#
# The in-memory ``_jobs`` dict is per-process. Under gunicorn (2 workers x 16
# threads in production) a follow-up request -- a progress poll, a download, or
# an emailed secure-retrieval link opened hours later -- routinely lands on the
# OTHER worker, where ``_jobs`` has no entry, and 404s.
#
# To make status/results/retrieval discoverable from any worker we persist each
# job's serializable state to ``<instance>/whisperer_jobs/<job_id>/status.json``
# atomically (temp file + os.replace). Readers on any process load from there
# when the id is absent locally. Follows the idioms in
# ``tasks/convert_tasks.py`` (write_status/read_status/_safe_job_id/_jobs_root).
#
# Precondition for cross-worker DOWNLOAD/RETRIEVE (not just status): the output
# file itself must live on a volume shared by every worker. Outputs are written
# into the upload token dir (``UPLOAD_TEMP_BASE/<token>/...``). In production
# ``GLOW_UPLOAD_TEMP_BASE=/app/instance/upload_temp`` lives on the ``feedback-data``
# volume mounted read-write into every container (see docker-compose.prod.yml),
# so this holds. If an operator points GLOW_UPLOAD_TEMP_BASE at a per-container
# path, status/progress still work cross-worker but the file transfer only works
# on the worker that produced it.
#
# NOTE ON CONTEXT: the transcription worker runs in a bare ``threading.Thread``
# with no Flask application context, so ``current_app.instance_path`` (the
# convert_tasks idiom, valid inside a Celery task context) would raise there and
# progress would never persist. We instead site the store beside
# ``UPLOAD_TEMP_BASE`` -- a module constant resolved from GLOW_UPLOAD_TEMP_BASE
# with no app context required -- which is the same shared instance volume.

_WHISPERER_JOBS_DIR_ENV = "GLOW_WHISPERER_JOBS_DIR"
# Job ids are ``str(uuid.uuid4())``. Validate strictly before any path join so a
# crafted id/token can never traverse out of the store root.
_JOB_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def _whisperer_jobs_root() -> Path:
    """Return the shared job-store root, creating it if needed.

    Resolved without a Flask app context so the bare worker thread can persist
    progress. ``GLOW_WHISPERER_JOBS_DIR`` overrides for tests/ops.
    """
    override = os.environ.get(_WHISPERER_JOBS_DIR_ENV, "").strip()
    if override:
        root = Path(override)
    else:
        root = UPLOAD_TEMP_BASE.parent / "whisperer_jobs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_whisperer_job_id(job_id: str) -> str:
    """Reject any id that is not a plain UUID before joining it to a path."""
    if not job_id or not _JOB_ID_RE.match(job_id):
        raise ValueError(f"Invalid job_id: {job_id!r}")
    return job_id


def _job_store_dir(job_id: str, *, create: bool) -> Path:
    safe = _safe_whisperer_job_id(job_id)
    d = _whisperer_jobs_root() / safe
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _hash_retrieval_token(token: str) -> str:
    """Hash a retrieval token for storage/lookup. We never persist the plaintext."""
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _job_to_status_dict(job: _WhisperJob) -> dict:
    """Serialize a job to the cross-worker status payload.

    NEVER writes the retrieval password (only its existing hash) and NEVER writes
    the plaintext retrieval token (only its SHA-256 hash, matched by hashing the
    presented token at retrieval time).
    """
    return {
        "job_id": job.job_id,
        "token": job.token,
        "saved_path": str(job.saved_path) if job.saved_path else None,
        "language": job.language,
        "output_format": job.output_format,
        "title": job.title,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "error": job.error,
        "output_path": str(job.output_path) if job.output_path else None,
        "mimetype": job.mimetype,
        "download_name": job.download_name,
        "queued_at": _iso(job.queued_at),
        "started_at": _iso(job.started_at),
        "completed_at": _iso(job.completed_at),
        "is_background": job.is_background,
        "notify_email": job.notify_email,
        "retrieval_token_hash": (
            _hash_retrieval_token(job.retrieval_token) if job.retrieval_token else None
        ),
        "retrieval_url": job.retrieval_url,
        "retrieval_password_hash": job.retrieval_password_hash,
        "retrieval_expires_at": _iso(job.retrieval_expires_at),
        "retrieved": job.retrieved,
    }


def _status_dict_to_job(data: dict) -> _WhisperJob:
    """Reconstruct a (detached) job from a stored status payload."""
    return _WhisperJob(
        job_id=str(data.get("job_id", "")),
        token=str(data.get("token", "")),
        saved_path=Path(data["saved_path"]) if data.get("saved_path") else Path(),
        language=data.get("language"),
        output_format=str(data.get("output_format", "markdown")),
        title=data.get("title"),
        status=str(data.get("status", "queued")),
        progress=int(data.get("progress", 0) or 0),
        message=str(data.get("message", "")),
        error=data.get("error"),
        output_path=Path(data["output_path"]) if data.get("output_path") else None,
        mimetype=data.get("mimetype"),
        download_name=data.get("download_name"),
        queued_at=_parse_dt(data.get("queued_at")),
        started_at=_parse_dt(data.get("started_at")),
        completed_at=_parse_dt(data.get("completed_at")),
        is_background=bool(data.get("is_background", False)),
        notify_email=data.get("notify_email"),
        # Plaintext retrieval token is never stored; leave it None. Retrieval
        # lookup matches on the stored hash instead.
        retrieval_token=None,
        retrieval_url=data.get("retrieval_url"),
        retrieval_password_hash=data.get("retrieval_password_hash"),
        retrieval_expires_at=_parse_dt(data.get("retrieval_expires_at")),
        retrieved=bool(data.get("retrieved", False)),
    )


def _write_job_status(job: _WhisperJob) -> None:
    """Atomically persist a full job snapshot. Never raises into the job flow."""
    try:
        d = _job_store_dir(job.job_id, create=True)
    except (ValueError, OSError):
        return
    try:
        path = d / "status.json"
        tmp = d / "status.json.tmp"
        tmp.write_text(json.dumps(_job_to_status_dict(job)), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def _patch_job_status(job_id: str, **fields) -> None:
    """Atomically merge *fields* into an existing status file (create if needed).

    Used for incremental transitions so a job that only exists in the shared
    store (i.e. was created on another worker) still records the change.
    """
    try:
        d = _job_store_dir(job_id, create=True)
    except (ValueError, OSError):
        return
    try:
        path = d / "status.json"
        existing: dict = {}
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                existing = {}
        existing.update(fields)
        tmp = d / "status.json.tmp"
        tmp.write_text(json.dumps(existing), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass


def _load_job_from_store(job_id: str) -> _WhisperJob | None:
    """Load a job from the shared store, or None if absent/unreadable/invalid."""
    try:
        d = _job_store_dir(job_id, create=False)
    except (ValueError, OSError):
        return None
    path = d / "status.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return _status_dict_to_job(data)


def _delete_job_store(job_id: str) -> None:
    """Remove a job's status directory from the shared store."""
    try:
        d = _job_store_dir(job_id, create=False)
    except (ValueError, OSError):
        return
    shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# Shared, cross-worker audio queue (Redis ZSET, local deque fallback)
# ---------------------------------------------------------------------------
#
# The audio concurrency gate is now GLOBAL (see gating.py: a Redis-backed
# distributed semaphore). The waiting line in front of it was not: ``_audio_queue``
# is a per-process deque, which produced three defects under gunicorn:
#
#   1. STALL -- worker B finishing a job releases a *global* slot and dispatches
#      from its own (possibly empty) deque, while worker A's queued jobs sleep
#      forever at "Queued..." with capacity sitting idle.
#   2. GLOBAL DEPTH -- ``_MAX_AUDIO_QUEUE_DEPTH`` measured one worker's deque, so
#      the real cap was depth x worker-count and "queue is full" was decided on
#      half the picture.
#   3. MISLEADING POSITION -- the position shown to a waiting user (and to the
#      admin queue page) was the index in the local deque. Someone told "#2 in
#      line" could really be #5. Screen reader users wait on these estimates.
#
# The fix is one shared FIFO in Redis: ZSET ``glow:queue:audio``, member = job id,
# score = enqueue unix time. Enqueue (with an exact global depth cap) and claim
# (pop-lowest-score) are single Lua scripts so they are atomic -- two workers can
# never claim the same job. Any worker can run any job because the input audio
# lives on the shared upload volume and the job's state lives in the shared job
# store above.
#
# Redis is optional. With no Redis configured (dev, tests) every helper degrades
# to the original local deque with the original semantics, and a Redis error at
# runtime degrades the same way after logging one warning.

_AUDIO_QUEUE_KEY = "glow:queue:audio"
# Housekeeping TTL so an abandoned deployment cannot leak the key forever. It is
# refreshed on every enqueue; a day is far longer than any transcription.
_AUDIO_QUEUE_TTL_SECONDS = 86_400
# How often each worker re-checks the shared queue so a slot released on ANOTHER
# worker is noticed (defect 1). 0 disables the sweeper.
_AUDIO_SWEEP_SECONDS = float(os.environ.get("GLOW_AUDIO_SWEEP_SECONDS", "5"))

_queue_redis_lock = threading.Lock()
_queue_redis_client = None
_queue_redis_resolved = False

# Test hook: anything other than the sentinel is returned verbatim by
# _queue_client() (a fake client, or None to force the local deque path).
_QUEUE_TEST_CLIENT_UNSET = object()
_queue_test_client = _QUEUE_TEST_CLIENT_UNSET

_queue_scripts: dict[int, dict[str, object]] = {}

_queue_warned: set[str] = set()
_queue_warn_lock = threading.Lock()

# Enqueue one job iff the shared queue has room. Atomic, so the depth cap is
# exact and global rather than per-worker.
#   KEYS[1] = queue key (ZSET)   ARGV[1] = job id
#   ARGV[2] = score (unix time)  ARGV[3] = max depth   ARGV[4] = key TTL
# Returns 1 when queued (or already queued), 0 when the queue is full.
_LUA_ENQUEUE = """
local key = KEYS[1]
local job = ARGV[1]
local score = tonumber(ARGV[2])
local max = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])
if redis.call('ZSCORE', key, job) then
  return 1
end
if redis.call('ZCARD', key) >= max then
  return 0
end
redis.call('ZADD', key, score, job)
redis.call('EXPIRE', key, ttl)
return 1
"""

# Claim the head of the queue (lowest score = earliest enqueue). ZPOPMIN
# semantics; atomic, so two workers never claim the same job id.
#   KEYS[1] = queue key
# Returns the job id, or false (-> None in the client) when the queue is empty.
_LUA_CLAIM = """
local key = KEYS[1]
local head = redis.call('ZRANGE', key, 0, 0)
if not head or #head == 0 then
  return false
end
redis.call('ZREM', key, head[1])
return head[1]
"""


def set_queue_redis_client_for_test(client) -> None:
    """Inject a Redis client (or None) for the shared queue in tests."""
    global _queue_test_client, _queue_redis_client, _queue_redis_resolved
    with _queue_redis_lock:
        _queue_test_client = client
        _queue_redis_client = None
        _queue_redis_resolved = False
        _queue_scripts.clear()
    with _queue_warn_lock:
        _queue_warned.clear()


def reset_queue_redis_client_for_test() -> None:
    """Undo :func:`set_queue_redis_client_for_test`, restoring env resolution."""
    global _queue_test_client, _queue_redis_client, _queue_redis_resolved
    with _queue_redis_lock:
        _queue_test_client = _QUEUE_TEST_CLIENT_UNSET
        _queue_redis_client = None
        _queue_redis_resolved = False
        _queue_scripts.clear()


def _queue_warn_once(key: str, message: str) -> None:
    with _queue_warn_lock:
        if key in _queue_warned:
            return
        _queue_warned.add(key)
    try:
        current_app.logger.warning(message)
    except RuntimeError:  # no app context (worker thread / sweeper)
        import logging

        logging.getLogger(__name__).warning(message)


def _create_queue_redis_client():
    # Same URL precedence as gating.py / app.py -- resolved there so there is one
    # definition of "where is Redis".
    from ..gating import _resolve_redis_url

    url = _resolve_redis_url()
    if not url:
        return None
    try:
        import redis  # imported lazily so the package works without redis installed

        client = redis.from_url(url)
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001 - any failure means "use the local deque"
        _queue_warn_once(
            "queue-redis-connect",
            f"whisperer: Redis unavailable ({exc!r}); the audio queue is "
            "per-worker. Queue depth and position are this worker's view only.",
        )
        return None


def _queue_client():
    """Return the shared-queue Redis client, or None to use the local deque."""
    if _queue_test_client is not _QUEUE_TEST_CLIENT_UNSET:
        return _queue_test_client
    global _queue_redis_client, _queue_redis_resolved
    if _queue_redis_resolved:
        return _queue_redis_client
    with _queue_redis_lock:
        if not _queue_redis_resolved:
            _queue_redis_client = _create_queue_redis_client()
            _queue_redis_resolved = True
        return _queue_redis_client


def _queue_script(client, name: str):
    scripts = _queue_scripts.get(id(client))
    if scripts is None:
        scripts = {
            "enqueue": client.register_script(_LUA_ENQUEUE),
            "claim": client.register_script(_LUA_CLAIM),
        }
        _queue_scripts[id(client)] = scripts
    return scripts[name]


def _queue_score(job: _WhisperJob | None) -> float:
    """FIFO score for a job: its original enqueue time when we know it.

    Re-enqueueing with the ORIGINAL score is what keeps a job that had to give
    its slot back (GatingError) at the head of the line instead of sending it to
    the back -- the shared-queue equivalent of ``deque.appendleft``.
    """
    if job is not None and job.queued_at is not None:
        try:
            return job.queued_at.timestamp()
        except (OverflowError, OSError, ValueError):
            pass
    return time.time()


def _shared_enqueue(job_id: str, score: float, *, force: bool = False) -> bool | None:
    """Add *job_id* to the shared queue.

    Returns True when queued, False when the queue is globally full, and None
    when there is no usable Redis (caller falls back to the local deque).
    ``force=True`` bypasses the depth cap; used only to give back a slot a job
    already held, which never grows the queue beyond its previous size.
    """
    client = _queue_client()
    if client is None:
        return None
    try:
        if force:
            client.zadd(_AUDIO_QUEUE_KEY, {job_id: score})
            return True
        result = _queue_script(client, "enqueue")(
            keys=[_AUDIO_QUEUE_KEY],
            args=[job_id, score, _MAX_AUDIO_QUEUE_DEPTH, _AUDIO_QUEUE_TTL_SECONDS],
        )
        return bool(result and int(result) == 1)
    except Exception as exc:  # noqa: BLE001 - degrade to the local deque
        _queue_warn_once(
            "queue-redis-enqueue",
            f"whisperer: Redis error queuing audio job ({exc!r}); using this "
            "worker's local queue for it.",
        )
        return None


def _shared_claim() -> str | None:
    """Atomically pop the head job id from the shared queue, or None."""
    client = _queue_client()
    if client is None:
        return None
    try:
        result = _queue_script(client, "claim")(keys=[_AUDIO_QUEUE_KEY])
    except Exception as exc:  # noqa: BLE001 - degrade to the local deque
        _queue_warn_once(
            "queue-redis-claim",
            f"whisperer: Redis error claiming an audio job ({exc!r}); this "
            "worker will dispatch from its local queue only.",
        )
        return None
    if not result:
        return None
    if isinstance(result, bytes):
        return result.decode("utf-8", "replace")
    return str(result)


def _shared_remove(job_id: str) -> bool:
    """Drop *job_id* from the shared queue. True when it was actually queued."""
    client = _queue_client()
    if client is None:
        return False
    try:
        return int(client.zrem(_AUDIO_QUEUE_KEY, job_id) or 0) > 0
    except Exception as exc:  # noqa: BLE001 - removal must never break a request
        _queue_warn_once(
            "queue-redis-remove",
            f"whisperer: Redis error removing an audio job ({exc!r}).",
        )
        return False


def _shared_depth() -> int | None:
    client = _queue_client()
    if client is None:
        return None
    try:
        return int(client.zcard(_AUDIO_QUEUE_KEY) or 0)
    except Exception:  # noqa: BLE001 - callers fall back to the local view
        return None


def _shared_order() -> list[str] | None:
    """Return the shared queue in FIFO order, or None when Redis is unusable."""
    client = _queue_client()
    if client is None:
        return None
    try:
        members = client.zrange(_AUDIO_QUEUE_KEY, 0, -1) or []
    except Exception:  # noqa: BLE001
        return None
    return [m.decode("utf-8", "replace") if isinstance(m, bytes) else str(m) for m in members]


# -- cross-worker wake-up ----------------------------------------------------
#
# A slot freed on worker B has to wake worker A's queued jobs. Event-driven
# dispatch (still done, for low latency) cannot do that on its own, so each
# worker runs ONE daemon sweeper that re-dispatches every few seconds. It is
# started lazily and only when Redis is actually in use, so single-process dev
# and the test suite behave exactly as before.

_sweeper_thread: threading.Thread | None = None
_sweeper_lock = threading.Lock()


def _queue_sweeper_loop() -> None:  # pragma: no cover - timing loop
    while True:
        time.sleep(_AUDIO_SWEEP_SECONDS)
        try:
            _dispatch_queued_jobs()
        except Exception:  # noqa: BLE001 - the sweeper must never die
            try:
                _queue_warn_once(
                    "queue-sweeper-error",
                    "whisperer: audio queue sweeper hit an error; continuing.",
                )
            except Exception:  # noqa: BLE001
                pass


def _ensure_queue_sweeper() -> None:
    """Start this worker's sweeper thread once, only when Redis is active."""
    global _sweeper_thread
    if _AUDIO_SWEEP_SECONDS <= 0:
        return
    thread = _sweeper_thread
    if thread is not None and thread.is_alive():
        return
    with _sweeper_lock:
        thread = _sweeper_thread
        if thread is not None and thread.is_alive():
            return
        if _queue_client() is None:
            return
        thread = threading.Thread(
            target=_queue_sweeper_loop, name="whisperer-queue-sweeper", daemon=True
        )
        _sweeper_thread = thread
        thread.start()


def _find_job_by_retrieval_token(token: str) -> _WhisperJob | None:
    """Resolve a retrieval token to its job, cross-worker, by matching its HASH.

    Checks the local cache first (constant-time hash compare), then scans the
    shared store's ``*/status.json`` for a matching ``retrieval_token_hash``. The
    scan is bounded because terminal jobs are pruned (see prune helpers).
    """
    if not token:
        return None
    presented = _hash_retrieval_token(token)

    with _jobs_lock:
        for job in _jobs.values():
            if job.retrieval_token and hmac.compare_digest(
                _hash_retrieval_token(job.retrieval_token), presented
            ):
                return job

    try:
        root = _whisperer_jobs_root()
    except OSError:
        return None
    for status_file in root.glob("*/status.json"):
        try:
            data = json.loads(status_file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        stored = data.get("retrieval_token_hash")
        if stored and hmac.compare_digest(str(stored), presented):
            job = _status_dict_to_job(data)
            # The presented token matched this job's stored hash; expose it so
            # downstream code that references job.retrieval_token still works.
            job.retrieval_token = token
            return job
    return None

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
    _prune_store_dirs(now, cutoff)


def _prune_store_dirs(now: datetime, cutoff: timedelta) -> None:
    """Delete stale terminal ``whisperer_jobs/<id>`` dirs from the shared store.

    Mirrors the in-memory retention: a background transcript that is still
    retrievable (complete, not retrieved, inside its window) is never removed.
    Best-effort and never raises into the caller.
    """
    try:
        root = _whisperer_jobs_root()
    except OSError:
        return
    try:
        entries = list(root.iterdir())
    except OSError:
        return
    for d in entries:
        try:
            if not d.is_dir():
                continue
            status_file = d / "status.json"
            try:
                marker_ts = (status_file if status_file.exists() else d).stat().st_mtime
            except OSError:
                continue
            if now.timestamp() - marker_ts <= cutoff.total_seconds():
                continue
            data: dict = {}
            if status_file.exists():
                try:
                    data = json.loads(status_file.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    data = {}
            status = data.get("status")
            if status not in ("complete", "failed"):
                # Non-terminal (or unknown): leave it. A live job keeps its
                # status file fresh via write-through, so a stale non-terminal
                # dir is an orphan we still avoid deleting out from under a poll.
                continue
            if (
                data.get("is_background")
                and status == "complete"
                and not data.get("retrieved")
            ):
                exp = _parse_dt(data.get("retrieval_expires_at"))
                if exp is None or now <= exp:
                    continue
            shutil.rmtree(d, ignore_errors=True)
        except OSError:
            continue


def _set_job(job: _WhisperJob) -> None:
    with _jobs_lock:
        _prune_terminal_jobs_locked()
        _jobs[job.job_id] = job
    _write_job_status(job)


def _get_job(job_id: str) -> _WhisperJob | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is not None:
        return job
    # Not in this worker's cache -- the accepting worker may have created it.
    # Fall back to the shared store so progress/download resolve cross-worker.
    return _load_job_from_store(job_id)


def _delete_job(job_id: str) -> None:
    # Also drop it from the shared queue so a job that was downloaded, expired,
    # or rolled back can never be claimed and started by another worker.
    _shared_remove(job_id)
    with _jobs_lock:
        _jobs.pop(job_id, None)


def _enqueue_job(job_id: str, job: _WhisperJob | None = None) -> bool:
    """Put a job in line for the audio gate. False means the queue is full.

    With Redis the depth cap is enforced atomically across every worker (defect
    2); without it, this is the original local deque check-and-append.
    """
    shared = _shared_enqueue(job_id, _queue_score(job))
    if shared is not None:
        if shared:
            _ensure_queue_sweeper()
        return shared
    with _jobs_lock:
        if job_id in _audio_queue:
            return True
        if len(_audio_queue) >= _MAX_AUDIO_QUEUE_DEPTH:
            return False
        _audio_queue.append(job_id)
    return True


def _requeue_job_at_head(job_id: str, job: _WhisperJob | None = None) -> None:
    """Give a job back its place at the head after it had to release its slot."""
    shared = _shared_enqueue(job_id, _queue_score(job), force=True)
    if shared:
        _ensure_queue_sweeper()
        return
    with _jobs_lock:
        if job_id not in _audio_queue:
            _audio_queue.appendleft(job_id)


def _queue_depth() -> int:
    """Current queue depth -- global when Redis is active, local otherwise."""
    depth = _shared_depth()
    if depth is not None:
        return depth
    with _jobs_lock:
        return len(_audio_queue)


def _is_queued(job_id: str) -> bool:
    client = _queue_client()
    if client is not None:
        try:
            return client.zscore(_AUDIO_QUEUE_KEY, job_id) is not None
        except Exception:  # noqa: BLE001 - fall through to the local view
            pass
    with _jobs_lock:
        return job_id in _audio_queue


def _queue_position(job_id: str) -> int | None:
    """Position in line, 1-based. Global (ZRANK) when Redis is active.

    Defect 3: this number is read out to the waiting user, so it has to reflect
    the whole deployment's queue, not just the worker that answered the poll.
    """
    client = _queue_client()
    if client is not None:
        try:
            rank = client.zrank(_AUDIO_QUEUE_KEY, job_id)
            return None if rank is None else int(rank) + 1
        except Exception as exc:  # noqa: BLE001 - degrade to the local view
            _queue_warn_once(
                "queue-redis-rank",
                f"whisperer: Redis error reading queue position ({exc!r}); "
                "reporting this worker's position.",
            )
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
    # Build a serialized patch alongside the in-memory mutation so the change is
    # recorded even when this worker has no local cache entry (the job was
    # created on another worker). The patch merges into the shared status file.
    patch: dict = {}
    with _jobs_lock:
        job = _jobs.get(job_id)
        if status is not None:
            if job is not None:
                job.status = status
            patch["status"] = status
        if progress is not None:
            clamped = max(0, min(100, int(progress)))
            if job is not None:
                job.progress = clamped
            patch["progress"] = clamped
        if message is not None:
            if job is not None:
                job.message = message
            patch["message"] = message
        if error is not None:
            if job is not None:
                job.error = error
            patch["error"] = error
        if output_path is not None:
            if job is not None:
                job.output_path = output_path
            patch["output_path"] = str(output_path)
        if mimetype is not None:
            if job is not None:
                job.mimetype = mimetype
            patch["mimetype"] = mimetype
        if download_name is not None:
            if job is not None:
                job.download_name = download_name
            patch["download_name"] = download_name
        if started_at is not None:
            if job is not None:
                job.started_at = started_at
            patch["started_at"] = _iso(started_at)
        if completed_at is not None:
            if job is not None:
                job.completed_at = completed_at
            patch["completed_at"] = _iso(completed_at)
        if retrieval_expires_at is not None:
            if job is not None:
                job.retrieval_expires_at = retrieval_expires_at
            patch["retrieval_expires_at"] = _iso(retrieval_expires_at)
        if retrieved is not None:
            if job is not None:
                job.retrieved = retrieved
            patch["retrieved"] = retrieved
    if patch:
        _patch_job_status(job_id, **patch)


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
    _delete_job_store(job.job_id)


def _claim_job_for_start(job_id: str) -> _WhisperJob | None:
    """Prepare a claimed job to run here, or None when it must not be started.

    The job may have been accepted by a DIFFERENT worker, in which case it is
    absent from this process's ``_jobs`` and is rebuilt from the shared store
    (its audio lives on the shared upload volume, so any worker can run it).

    The stored status is the guard: a job that was cancelled, already started,
    or has vanished from the store is dropped instead of being run twice.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)

    stored = _load_job_from_store(job_id)
    if job is None:
        if stored is None:
            return None
        job = stored
        with _jobs_lock:
            existing = _jobs.get(job_id)
            if existing is not None:
                job = existing
            else:
                _jobs[job_id] = job

    status = stored.status if stored is not None else job.status
    if status != "queued":
        return None

    with _jobs_lock:
        job.status = "running"
        job.progress = 1
        job.message = "Initializing transcription..."
        job.started_at = datetime.now(UTC)
    return job


def _dispatch_shared_queue(capacity: int) -> int:
    """Claim and start up to *capacity* jobs from the shared queue."""
    started = 0
    for _ in range(capacity):
        job_id = _shared_claim()
        if job_id is None:
            break
        job = _claim_job_for_start(job_id)
        if job is None:
            # Cancelled, already running, or gone: the atomic claim already
            # removed it, so it simply leaves the queue.
            continue

        _write_job_status(job)

        if job.notify_email:
            _send_job_email(job, "started")

        thread = threading.Thread(target=_run_whisper_job, args=(job_id,), daemon=True)
        thread.start()
        started += 1
    return started


def _dispatch_queued_jobs() -> None:
    """Start queued jobs while audio gate capacity is available.

    With Redis this drains the SHARED queue, so a slot released on any worker
    starts the globally-oldest waiting job (defect 1). Any job that landed in
    this worker's local deque (a Redis blip during enqueue) is drained after.
    """
    from ..gating import get_capacity_metrics

    capacity = get_capacity_metrics().get("audio", {}).get("available", 0)
    if capacity <= 0:
        return

    capacity = int(capacity)
    if _queue_client() is not None:
        _ensure_queue_sweeper()
        capacity -= _dispatch_shared_queue(capacity)
        if capacity <= 0:
            return

    for _ in range(capacity):
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

        _write_job_status(job)

        if job.notify_email:
            _send_job_email(job, "started")

        thread = threading.Thread(target=_run_whisper_job, args=(job_id,), daemon=True)
        thread.start()


def get_admin_queue_snapshot(limit_recent: int = 100) -> list[dict]:
    """Return queue/running/completed/failed snapshot for admin dashboard."""
    # Global order when Redis is active, so the admin sees the real line rather
    # than this worker's slice of it (defect 3).
    shared_order = _shared_order()
    with _jobs_lock:
        queue_order = shared_order if shared_order is not None else list(_audio_queue)
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
        was_local = job_id in _audio_queue
        if was_local:
            _audio_queue.remove(job_id)
    # Remove from the shared queue too, so no worker can claim it later.
    was_shared = _shared_remove(job_id)
    if not (was_local or was_shared):
        return False, "Only queued jobs can be canceled."

    with _jobs_lock:
        job.status = "failed"
        job.progress = 0
        job.message = "Canceled by admin before processing."
        job.error = "Canceled by admin."

    _write_job_status(job)
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
    # Membership and depth are read against the shared queue when Redis is
    # active; the enqueue below is what actually enforces the cap, atomically.
    if _is_queued(job_id):
        return False, "Job is already queued."
    if _queue_depth() >= _MAX_AUDIO_QUEUE_DEPTH:
        return False, "Queue is full."

    temp_dir = get_temp_dir(job.token)
    if temp_dir is None or not job.saved_path.exists():
        return False, "Cannot re-queue because source audio is no longer available."

    with _jobs_lock:
        previous = (job.status, job.progress, job.message, job.error)
        job.status = "queued"
        job.progress = 0
        job.message = "Queued..."
        job.error = None
        job.started_at = None
        job.completed_at = None

    # Publish "queued" BEFORE enqueuing: another worker may claim it the instant
    # it appears, and the claim guard reads the stored status.
    _write_job_status(job)
    if not _enqueue_job(job_id, job):
        with _jobs_lock:
            job.status, job.progress, job.message, job.error = previous
        _write_job_status(job)
        return False, "Queue is full."

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
                local_job = _jobs.get(job_id)
                if local_job is not None:
                    local_job.status = "queued"
                    local_job.progress = 0
                    local_job.message = "Queued... waiting for audio capacity."
            if local_job is not None:
                # Persist "queued" first: with a shared queue another worker can
                # claim this job as soon as it is re-listed, and the claim guard
                # reads the stored status.
                _write_job_status(local_job)
            else:
                _patch_job_status(
                    job_id,
                    status="queued",
                    progress=0,
                    message="Queued... waiting for audio capacity.",
                )
            # Re-enter the line at the job's ORIGINAL enqueue time so giving the
            # slot back does not send it to the back of the queue.
            _requeue_job_at_head(job_id, local_job or job)
            job = local_job if local_job is not None else job
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

        # Atomic global enqueue when Redis is active: the depth cap counts every
        # worker's waiting jobs, not just this one's (defect 2).
        queue_full = not _enqueue_job(job_id, job)
        if queue_full:
            # Roll back outside any lock: _jobs_lock is a plain (non-reentrant)
            # Lock, so calling these lock-taking helpers while holding it would
            # deadlock the worker and, through it, every route that touches the
            # lock (progress polling, dispatch, the admin queue page).
            # _delete_job also drops the id from the shared queue.
            _delete_job(job_id)
            _delete_job_store(job_id)
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
    # Resolve cross-worker: match the presented token's HASH against the shared
    # store (the emailed link is very likely opened on a different worker).
    job = _find_job_by_retrieval_token(token)

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
