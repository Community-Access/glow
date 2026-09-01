"""Concurrency gating for outbound AI API calls.

GLOW 2.0 routes all AI inference through OpenRouter (cloud) rather than
on-device models.  Gating here limits simultaneous outbound API calls to
prevent runaway spend and respect provider rate limits.

Caps are controlled by environment variables:

  GLOW_MAX_AI_SESSIONS    -- max simultaneous chat/fix API calls (default 10)
  GLOW_MAX_AUDIO_SESSIONS -- max simultaneous Whisper transcription calls (default 3)
  GLOW_MAX_VISION_SESSIONS -- max simultaneous vision API calls (default 5)

When a slot is not immediately available the route returns 503 with
Retry-After rather than queuing unbounded requests.

Distributed gating
-------------------

Under Gunicorn each worker process is a separate Python interpreter, so a
plain ``threading.BoundedSemaphore`` only caps *one* worker.  With N workers
the real ceiling is N times the configured cap, and ``get_capacity_metrics()``
(shown on /health) reports just one worker's view.  To make the caps count
across workers we back each gate with a Redis ZSET (one member per held slot,
score = acquisition unix time) and acquire slots with an atomic Lua script.

Redis is optional.  When no Redis URL is configured, or Redis is unreachable,
each gate falls back to the original in-process semaphore so dev and tests run
with zero infrastructure.  A Redis error at request time never surfaces to the
user: the affected call degrades to local gating and a warning is logged once.

Usage (in a route handler)::

    from .gating import ai_gate, audio_gate, GatingError

    try:
        with ai_gate():
            result = gateway.chat(...)
    except GatingError:
        return busy_response("AI assistant")
"""

from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Generator

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_MAX_AI: int = int(os.environ.get("GLOW_MAX_AI_SESSIONS", "10"))
_MAX_VISION: int = int(os.environ.get("GLOW_MAX_VISION_SESSIONS", "5"))
_MAX_AUDIO: int = int(os.environ.get("GLOW_MAX_AUDIO_SESSIONS", "3"))

# Optional bounded queue wait times (seconds). A value of 0 keeps fail-fast behavior.
_AI_QUEUE_WAIT_SECONDS: int = int(os.environ.get("GLOW_AI_QUEUE_WAIT_SECONDS", "25"))
_VISION_QUEUE_WAIT_SECONDS: int = int(os.environ.get("GLOW_VISION_QUEUE_WAIT_SECONDS", "20"))
_AUDIO_QUEUE_WAIT_SECONDS: int = int(os.environ.get("GLOW_AUDIO_QUEUE_WAIT_SECONDS", "0"))

# Retry-After hint sent to clients when a gate is full (seconds)
RETRY_AFTER_SECONDS: int = 90

# Slot TTLs (seconds).  A slot whose acquisition timestamp is older than the
# gate's TTL is treated as leaked (its worker crashed mid-operation) and is
# reclaimed on the next acquire/metrics read.  Audio transcription can run for
# minutes, so its TTL is derived from the max audio length plus a margin and is
# overridable; chat/vision calls are short-lived.
_WHISPER_MAX_AUDIO_MINUTES: int = int(os.environ.get("WHISPER_MAX_AUDIO_MINUTES", "120"))
_AUDIO_SLOT_TTL_SECONDS: int = int(
    os.environ.get("GLOW_GATE_SLOT_TTL_SECONDS", str(_WHISPER_MAX_AUDIO_MINUTES * 60 + 300))
)
_SHORT_SLOT_TTL_SECONDS: int = int(os.environ.get("GLOW_GATE_SHORT_TTL_SECONDS", "300"))

# How often to re-poll Redis while waiting for a slot (seconds).
_POLL_INTERVAL_SECONDS: float = 0.1


class GatingError(Exception):
    """Raised when no slot is available for a gated operation."""

    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(
            f"No capacity available for '{operation}'. "
            f"Please try again in {RETRY_AFTER_SECONDS} seconds."
        )


# ---------------------------------------------------------------------------
# Redis client (lazy, cached, shared by all threads in a worker)
# ---------------------------------------------------------------------------

_redis_conn_lock = threading.Lock()
_redis_client = None
_redis_client_resolved = False

# Test hook. When set to anything other than the sentinel, _get_redis_client()
# returns it verbatim (a fake client, or None to force the local fallback).
_TEST_CLIENT_UNSET = object()
_redis_test_client = _TEST_CLIENT_UNSET

_warned_keys: set[str] = set()
_warn_lock = threading.Lock()

# Compiled Lua acquire scripts, keyed by client identity.
_acquire_scripts: dict[int, object] = {}

# Atomically reclaim expired slots, then claim one if there is room.
#   KEYS[1] = gate key (ZSET)
#   ARGV[1] = max slots
#   ARGV[2] = now (unix seconds)
#   ARGV[3] = slot TTL seconds
#   ARGV[4] = unique token
# Returns the token on success, or false (nil to the client) when the gate is full.
_LUA_ACQUIRE = """
local key = KEYS[1]
local max = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local ttl = tonumber(ARGV[3])
local token = ARGV[4]
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - ttl)
local count = redis.call('ZCARD', key)
if count < max then
  redis.call('ZADD', key, now, token)
  redis.call('EXPIRE', key, math.ceil(ttl * 2))
  return token
end
return false
"""


def set_redis_client_for_test(client) -> None:
    """Inject a Redis client (or None) for tests, bypassing env resolution.

    Pass a fake client to exercise the distributed path, or ``None`` to force
    the in-process semaphore fallback. Call with no explicit reset needed; it
    clears cached script/connection state so tests stay isolated.
    """
    global _redis_test_client, _redis_client, _redis_client_resolved
    with _redis_conn_lock:
        _redis_test_client = client
        _redis_client = None
        _redis_client_resolved = False
        _acquire_scripts.clear()
    with _warn_lock:
        _warned_keys.clear()


def reset_redis_client_for_test() -> None:
    """Undo :func:`set_redis_client_for_test`, restoring env-based resolution."""
    global _redis_test_client, _redis_client, _redis_client_resolved
    with _redis_conn_lock:
        _redis_test_client = _TEST_CLIENT_UNSET
        _redis_client = None
        _redis_client_resolved = False
        _acquire_scripts.clear()


def _warn_once(key: str, message: str) -> None:
    with _warn_lock:
        if key in _warned_keys:
            return
        _warned_keys.add(key)
    _log.warning(message)


def _resolve_redis_url() -> str | None:
    """Return the first configured Redis URL, matching app.py's precedence."""
    for var in ("RATELIMIT_STORAGE_URI", "REDIS_URL", "CELERY_BROKER_URL"):
        value = (os.environ.get(var) or "").strip()
        if value and value.startswith(("redis://", "rediss://", "unix://")):
            return value
    return None


def _create_redis_client():
    url = _resolve_redis_url()
    if not url:
        return None
    try:
        import redis  # imported lazily so the package works without redis installed

        client = redis.from_url(url)
        client.ping()
        return client
    except Exception as exc:  # noqa: BLE001 - any failure means "use local gating"
        _warn_once(
            "redis-connect",
            f"gating: Redis unavailable ({exc!r}); falling back to in-process "
            "semaphores. Concurrency caps will not be shared across workers.",
        )
        return None


def _get_redis_client():
    if _redis_test_client is not _TEST_CLIENT_UNSET:
        return _redis_test_client
    global _redis_client, _redis_client_resolved
    if _redis_client_resolved:
        return _redis_client
    with _redis_conn_lock:
        if not _redis_client_resolved:
            _redis_client = _create_redis_client()
            _redis_client_resolved = True
        return _redis_client


def _get_acquire_script(client):
    script = _acquire_scripts.get(id(client))
    if script is None:
        script = client.register_script(_LUA_ACQUIRE)
        _acquire_scripts[id(client)] = script
    return script


# ---------------------------------------------------------------------------
# Gate: local semaphore + optional Redis-backed distributed semaphore
# ---------------------------------------------------------------------------

class _Gate:
    """One concurrency gate with a Redis-backed cap and a local fallback."""

    def __init__(
        self,
        name: str,
        operation: str,
        max_slots: int,
        queue_wait_seconds: int,
        ttl_seconds: int,
    ) -> None:
        self.name = name
        self.operation = operation
        self.max = max_slots
        self.queue_wait_seconds = queue_wait_seconds
        self.ttl = ttl_seconds
        self.key = f"glow:gate:{name}"
        self._sem = threading.BoundedSemaphore(max_slots)
        self._lock = threading.Lock()
        self._local_active = 0
        self._waiting = 0

    # -- distributed (Redis) ------------------------------------------------

    def _acquire_redis(self, client, wait: int) -> str | None:
        """Poll-acquire a distributed slot. Returns a token, or None on timeout.

        Raises on Redis errors so the caller can fall back to local gating.
        """
        script = _get_acquire_script(client)
        deadline = time.monotonic() + wait
        while True:
            token = uuid.uuid4().hex
            now = time.time()
            result = script(keys=[self.key], args=[self.max, now, self.ttl, token])
            if result:
                return token
            if wait <= 0 or time.monotonic() >= deadline:
                return None
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            time.sleep(min(_POLL_INTERVAL_SECONDS, remaining))

    def _release_redis(self, client, token: str) -> None:
        if client is None or token is None:
            return
        try:
            client.zrem(self.key, token)
        except Exception:  # noqa: BLE001 - release must never raise
            pass

    # -- local (in-process) -------------------------------------------------

    def _acquire_local(self, wait: int) -> bool:
        if wait > 0:
            return self._sem.acquire(timeout=wait)
        return self._sem.acquire(blocking=False)

    # -- context manager ----------------------------------------------------

    @contextmanager
    def gate(self, wait_seconds: int | None = None) -> Generator[None, None, None]:
        wait = (
            self.queue_wait_seconds
            if wait_seconds is None
            else max(0, int(wait_seconds))
        )
        client = _get_redis_client()
        mode = "local"
        token: str | None = None
        acquire_client = None

        with self._lock:
            self._waiting += 1
        try:
            if client is not None:
                try:
                    token = self._acquire_redis(client, wait)
                    if token is None:
                        raise GatingError(self.operation)
                    mode = "redis"
                    acquire_client = client
                except GatingError:
                    raise
                except Exception as exc:  # noqa: BLE001 - degrade to local gating
                    _warn_once(
                        "redis-runtime",
                        f"gating: Redis error during acquire ({exc!r}); using "
                        "in-process semaphore for this call.",
                    )
                    client = None
            if client is None:
                if not self._acquire_local(wait):
                    raise GatingError(self.operation)
                mode = "local"
        finally:
            with self._lock:
                self._waiting -= 1

        with self._lock:
            self._local_active += 1
        try:
            yield
        finally:
            with self._lock:
                self._local_active -= 1
            if mode == "redis":
                self._release_redis(acquire_client, token)
            else:
                self._sem.release()

    # -- metrics ------------------------------------------------------------

    def metrics(self) -> dict:
        client = _get_redis_client()
        if client is not None:
            try:
                now = time.time()
                client.zremrangebyscore(self.key, "-inf", now - self.ttl)
                active = int(client.zcard(self.key))
                with self._lock:
                    waiting = self._waiting
                return {
                    "active": active,
                    "limit": self.max,
                    "available": max(0, self.max - active),
                    "queued": waiting,
                    "queue_wait_seconds": self.queue_wait_seconds,
                }
            except Exception as exc:  # noqa: BLE001 - fall back to local counts
                _warn_once(
                    "redis-metrics",
                    f"gating: Redis error reading capacity ({exc!r}); reporting "
                    "in-process counts.",
                )
        with self._lock:
            active = self._local_active
            waiting = self._waiting
        return {
            "active": active,
            "limit": self.max,
            "available": max(0, self.max - active),
            "queued": waiting,
            "queue_wait_seconds": self.queue_wait_seconds,
        }


# ---------------------------------------------------------------------------
# Gate singletons (module-level; each worker holds its own local fallback)
# ---------------------------------------------------------------------------

_ai_gate = _Gate(
    "ai", "AI assistant", _MAX_AI, _AI_QUEUE_WAIT_SECONDS, _SHORT_SLOT_TTL_SECONDS
)
_vision_gate = _Gate(
    "vision", "Vision processing", _MAX_VISION, _VISION_QUEUE_WAIT_SECONDS,
    _SHORT_SLOT_TTL_SECONDS,
)
_audio_gate = _Gate(
    "audio", "BITS Whisperer transcription", _MAX_AUDIO, _AUDIO_QUEUE_WAIT_SECONDS,
    _AUDIO_SLOT_TTL_SECONDS,
)


# ---------------------------------------------------------------------------
# Public context managers (signatures unchanged)
# ---------------------------------------------------------------------------

@contextmanager
def ai_gate(wait_seconds: int | None = None) -> Generator[None, None, None]:
    """Acquire one AI API call slot. Raises GatingError if unavailable."""
    with _ai_gate.gate(wait_seconds):
        yield


@contextmanager
def audio_gate(wait_seconds: int | None = None) -> Generator[None, None, None]:
    """Acquire one BITS Whisperer API call slot. Raises GatingError if unavailable."""
    with _audio_gate.gate(wait_seconds):
        yield


@contextmanager
def vision_gate(wait_seconds: int | None = None) -> Generator[None, None, None]:
    """Acquire one vision API call slot. Raises GatingError if unavailable."""
    with _vision_gate.gate(wait_seconds):
        yield


# ---------------------------------------------------------------------------
# Metrics (consumed by /health)
# ---------------------------------------------------------------------------

def get_capacity_metrics() -> dict:
    """Return a snapshot of current gating counters for the health endpoint.

    When Redis is active the counts are shared across all workers (ZCARD per
    gate, after reclaiming expired slots); otherwise they reflect this worker's
    in-process semaphores.
    """
    return {
        "ai": _ai_gate.metrics(),
        "vision": _vision_gate.metrics(),
        "audio": _audio_gate.metrics(),
    }
