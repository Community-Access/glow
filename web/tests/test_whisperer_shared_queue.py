"""Tests for the shared, cross-worker BITS Whisperer audio queue.

The audio concurrency gate is global (Redis-backed semaphore in gating.py) but
the waiting line used to be a per-process deque. These tests cover the shared
Redis ZSET queue that replaces it:

  - the queue-depth cap is global, not depth x worker-count;
  - the position shown to a waiting user is the global position;
  - claiming is atomic, so two workers never run the same job;
  - a job accepted by one worker can be claimed and started by another;
  - a job that is no longer "queued" is never started by a claim;
  - cancelling removes a job from the shared queue;
  - with no Redis, everything degrades to the original local deque.

A small in-memory fake Redis implements only the operations whisperer.py calls.
Two "workers" are simulated by sharing one fake while clearing the per-process
caches (``_jobs`` / ``_audio_queue``) between them.
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from acb_large_print_web.routes import whisperer as w


# ---------------------------------------------------------------------------
# Fake Redis (ZSET subset)
# ---------------------------------------------------------------------------

class FakeRedis:
    """In-memory stand-in implementing exactly the ops the shared queue uses."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, float]] = {}
        self._lock = threading.Lock()
        self.calls: list[str] = []

    # -- connection ---------------------------------------------------------

    def ping(self) -> bool:
        return True

    # -- scripts ------------------------------------------------------------

    def register_script(self, script: str):
        if "ZADD" in script:
            return self._enqueue_script
        if "ZRANGE" in script:
            return self._claim_script
        raise AssertionError(f"unexpected script: {script!r}")

    def _enqueue_script(self, keys=None, args=None, client=None):
        key = keys[0]
        job_id, score, max_depth = args[0], float(args[1]), int(args[2])
        with self._lock:
            self.calls.append("enqueue")
            members = self._store.setdefault(key, {})
            if job_id in members:
                return 1
            if len(members) >= max_depth:
                return 0
            members[job_id] = score
            return 1

    def _claim_script(self, keys=None, args=None, client=None):
        key = keys[0]
        with self._lock:
            self.calls.append("claim")
            members = self._store.setdefault(key, {})
            if not members:
                return False
            head = min(members.items(), key=lambda kv: (kv[1], kv[0]))[0]
            del members[head]
            return head.encode("utf-8")  # redis-py returns bytes

    # -- plain commands -----------------------------------------------------

    def zadd(self, key, mapping):
        with self._lock:
            members = self._store.setdefault(key, {})
            added = 0
            for member, score in mapping.items():
                if member not in members:
                    added += 1
                members[member] = float(score)
            return added

    def zrem(self, key, *members):
        with self._lock:
            current = self._store.setdefault(key, {})
            removed = 0
            for member in members:
                if member in current:
                    del current[member]
                    removed += 1
            return removed

    def zcard(self, key):
        with self._lock:
            return len(self._store.get(key, {}))

    def zscore(self, key, member):
        with self._lock:
            return self._store.get(key, {}).get(member)

    def _ordered(self, key):
        return [m for m, _ in sorted(self._store.get(key, {}).items(), key=lambda kv: (kv[1], kv[0]))]

    def zrank(self, key, member):
        with self._lock:
            order = self._ordered(key)
        try:
            return order.index(member)
        except ValueError:
            return None

    def zrange(self, key, start, end):
        with self._lock:
            order = self._ordered(key)
        if end == -1:
            end = len(order) - 1
        return [m.encode("utf-8") for m in order[start : end + 1]]


class BrokenRedis(FakeRedis):
    """Pings fine, but every queue operation raises."""

    def register_script(self, script: str):
        def run(keys=None, args=None, client=None):
            raise RuntimeError("redis exploded")

        return run

    def zrank(self, key, member):
        raise RuntimeError("redis exploded")

    def zcard(self, key):
        raise RuntimeError("redis exploded")

    def zrange(self, key, start, end):
        raise RuntimeError("redis exploded")

    def zscore(self, key, member):
        raise RuntimeError("redis exploded")


# ---------------------------------------------------------------------------
# Thread capture (no transcription ever runs)
# ---------------------------------------------------------------------------

class _NoopThread:
    def __init__(self) -> None:
        self.daemon = True

    def start(self) -> None:
        pass

    def is_alive(self) -> bool:
        return False


class _RecordingThreading:
    """Proxy for the threading module that records Thread(...) instead of running it."""

    def __init__(self, real, sink: list) -> None:
        self._real = real
        self._sink = sink

    def __getattr__(self, name):
        return getattr(self._real, name)

    def Thread(self, target=None, args=(), daemon=None, name=None, **kwargs):
        self._sink.append((target, tuple(args)))
        return _NoopThread()


@pytest.fixture
def started(monkeypatch):
    sink: list = []
    monkeypatch.setattr(w, "threading", _RecordingThreading(threading, sink))
    return sink


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Empty per-process state, an isolated shared job store, no sweeper thread."""
    monkeypatch.setenv(w._WHISPERER_JOBS_DIR_ENV, str(tmp_path / "jobs"))
    monkeypatch.setattr(w, "_AUDIO_SWEEP_SECONDS", 0.0)
    monkeypatch.setattr(w, "cleanup_token", lambda token: None)
    with w._jobs_lock:
        w._jobs.clear()
        w._audio_queue.clear()
    yield
    with w._jobs_lock:
        w._jobs.clear()
        w._audio_queue.clear()
    w.reset_queue_redis_client_for_test()
    w._sweeper_thread = None


@pytest.fixture
def fake_redis():
    fake = FakeRedis()
    w.set_queue_redis_client_for_test(fake)
    yield fake
    w.reset_queue_redis_client_for_test()


@pytest.fixture
def no_redis():
    w.set_queue_redis_client_for_test(None)
    yield
    w.reset_queue_redis_client_for_test()


def _capacity(monkeypatch, available: int) -> None:
    monkeypatch.setattr(
        "acb_large_print_web.gating.get_capacity_metrics",
        lambda: {"audio": {"available": available}},
    )


def _new_job(tmp_path, *, queued_at=None) -> w._WhisperJob:
    job_id = str(uuid.uuid4())
    audio = tmp_path / f"{job_id}.mp3"
    audio.write_bytes(b"\x00\x01\x02")
    return w._WhisperJob(
        job_id=job_id,
        token=f"tok-{job_id}",
        saved_path=audio,
        language=None,
        output_format="markdown",
        title=None,
        status="queued",
        queued_at=queued_at or datetime.now(UTC),
    )


def _accept(tmp_path, *, queued_at=None) -> w._WhisperJob:
    """Accept a job the way /whisperer/start does: persist, then enqueue."""
    job = _new_job(tmp_path, queued_at=queued_at)
    w._set_job(job)
    assert w._enqueue_job(job.job_id, job) is True
    return job


def _other_worker() -> None:
    """Drop this process's caches: what a job looks like on the OTHER worker."""
    with w._jobs_lock:
        w._jobs.clear()
        w._audio_queue.clear()


# ---------------------------------------------------------------------------
# Defect 2: the depth cap is global
# ---------------------------------------------------------------------------

def test_depth_cap_is_global_across_workers(fake_redis, monkeypatch, tmp_path):
    monkeypatch.setattr(w, "_MAX_AUDIO_QUEUE_DEPTH", 2)

    # Worker A accepts two jobs...
    _accept(tmp_path)
    _accept(tmp_path)
    # ...then the request lands on worker B, whose local deque is empty.
    _other_worker()

    third = _new_job(tmp_path)
    w._set_job(third)
    assert w._enqueue_job(third.job_id, third) is False, (
        "the N+1th job must be refused globally, not per worker"
    )
    assert fake_redis.zcard(w._AUDIO_QUEUE_KEY) == 2


def test_local_depth_would_have_allowed_double_the_queue(fake_redis, monkeypatch, tmp_path):
    """Guard against a regression back to the per-worker deque check."""
    monkeypatch.setattr(w, "_MAX_AUDIO_QUEUE_DEPTH", 1)
    _accept(tmp_path)
    _other_worker()
    assert list(w._audio_queue) == []  # worker B's local view says "empty"
    extra = _new_job(tmp_path)
    w._set_job(extra)
    assert w._enqueue_job(extra.job_id, extra) is False


# ---------------------------------------------------------------------------
# Defect 3: the position shown to the user is global
# ---------------------------------------------------------------------------

def test_position_is_global_not_local(fake_redis, tmp_path):
    first = _accept(tmp_path, queued_at=datetime.now(UTC) - timedelta(seconds=10))
    _other_worker()  # second job is accepted by another worker
    second = _accept(tmp_path)

    assert w._queue_position(first.job_id) == 1
    assert w._queue_position(second.job_id) == 2, (
        "a job queued behind another worker's job must not report '#1 in line'"
    )
    assert w._queue_position(str(uuid.uuid4())) is None


def test_admin_snapshot_uses_global_order(fake_redis, tmp_path):
    first = _accept(tmp_path, queued_at=datetime.now(UTC) - timedelta(seconds=10))
    _other_worker()
    second = _accept(tmp_path)

    rows = {row["job_id"]: row for row in w.get_admin_queue_snapshot()}
    # Only the locally cached job is listed, but its position is the global one.
    assert rows[second.job_id]["queue_position"] == 2
    assert first.job_id not in rows  # it lives on the other worker's cache


def test_progress_payload_reports_global_position(fake_redis, tmp_path):
    _accept(tmp_path, queued_at=datetime.now(UTC) - timedelta(seconds=10))
    _other_worker()
    mine = _accept(tmp_path)
    assert w._queue_position(mine.job_id) == 2


# ---------------------------------------------------------------------------
# Atomic claim
# ---------------------------------------------------------------------------

def test_claim_returns_jobs_in_fifo_order(fake_redis, tmp_path):
    now = datetime.now(UTC)
    ids = [
        _accept(tmp_path, queued_at=now - timedelta(seconds=n)).job_id
        for n in (30, 20, 10)
    ]
    claimed = [w._shared_claim() for _ in range(3)]
    assert claimed == list(ids)
    assert w._shared_claim() is None


def test_concurrent_claims_never_hand_out_the_same_job(fake_redis, monkeypatch, tmp_path):
    monkeypatch.setattr(w, "_MAX_AUDIO_QUEUE_DEPTH", 20)
    expected ={_accept(tmp_path, queued_at=datetime.now(UTC) - timedelta(seconds=n)).job_id
                for n in range(12)}

    results: list[str] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(4)

    def worker() -> None:
        barrier.wait()
        while True:
            job_id = w._shared_claim()
            if job_id is None:
                return
            with results_lock:
                results.append(job_id)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert len(results) == len(expected), "every job must be claimed exactly once"
    assert set(results) == expected
    assert len(set(results)) == len(results), "two workers claimed the same job"


# ---------------------------------------------------------------------------
# Defect 1: cross-worker dispatch (the stall)
# ---------------------------------------------------------------------------

def test_job_accepted_by_worker_a_is_started_by_worker_b(fake_redis, monkeypatch, tmp_path, started):
    job = _accept(tmp_path)
    _other_worker()  # worker B has never seen this job in memory
    assert job.job_id not in w._jobs

    _capacity(monkeypatch, 1)
    w._dispatch_queued_jobs()

    assert started == [(w._run_whisper_job, (job.job_id,))], (
        "worker B must claim and start the globally-oldest queued job"
    )
    # It was rebuilt from the shared store into this worker's cache...
    assert job.job_id in w._jobs
    assert w._jobs[job.job_id].token == job.token
    # ...and marked running in the shared store so no one else re-runs it.
    assert w._load_job_from_store(job.job_id).status == "running"
    assert fake_redis.zcard(w._AUDIO_QUEUE_KEY) == 0


def test_dispatch_starts_only_up_to_available_capacity(fake_redis, monkeypatch, tmp_path, started):
    now = datetime.now(UTC)
    ids = [_accept(tmp_path, queued_at=now - timedelta(seconds=n)).job_id for n in (30, 20, 10)]
    _other_worker()

    _capacity(monkeypatch, 2)
    w._dispatch_queued_jobs()

    assert [args[0] for _, args in started] == ids[:2]
    assert fake_redis.zcard(w._AUDIO_QUEUE_KEY) == 1


def test_dispatch_is_a_noop_without_capacity(fake_redis, monkeypatch, tmp_path, started):
    _accept(tmp_path)
    _capacity(monkeypatch, 0)
    w._dispatch_queued_jobs()
    assert started == []
    assert fake_redis.zcard(w._AUDIO_QUEUE_KEY) == 1


def test_sweeper_starts_only_when_redis_is_active(monkeypatch, tmp_path, started):
    monkeypatch.setattr(w, "_AUDIO_SWEEP_SECONDS", 5.0)
    monkeypatch.setattr(w, "_sweeper_thread", None)

    w.set_queue_redis_client_for_test(None)
    w._ensure_queue_sweeper()
    assert started == [], "no sweeper thread without Redis (dev/test behavior unchanged)"

    w.set_queue_redis_client_for_test(FakeRedis())
    w._ensure_queue_sweeper()
    assert [target for target, _ in started] == [w._queue_sweeper_loop]


# ---------------------------------------------------------------------------
# Status guard: never double-start
# ---------------------------------------------------------------------------

def test_claimed_job_is_not_started_when_no_longer_queued(fake_redis, monkeypatch, tmp_path, started):
    job = _accept(tmp_path)
    # Another worker already started it (or an admin cancelled it).
    w._patch_job_status(job.job_id, status="running")
    _other_worker()

    _capacity(monkeypatch, 2)
    w._dispatch_queued_jobs()

    assert started == [], "a job whose stored status is not 'queued' must not run"
    assert fake_redis.zcard(w._AUDIO_QUEUE_KEY) == 0, "the stale entry is dropped"


def test_claimed_job_missing_from_the_store_is_dropped(fake_redis, monkeypatch, tmp_path, started):
    job = _accept(tmp_path)
    w._delete_job_store(job.job_id)
    _other_worker()

    _capacity(monkeypatch, 1)
    w._dispatch_queued_jobs()

    assert started == []
    assert fake_redis.zcard(w._AUDIO_QUEUE_KEY) == 0


# ---------------------------------------------------------------------------
# Removal
# ---------------------------------------------------------------------------

def test_cancelling_removes_the_job_from_the_shared_queue(fake_redis, monkeypatch, tmp_path, started):
    job = _accept(tmp_path)
    ok, message = w.admin_cancel_queued_job(job.job_id)

    assert ok, message
    assert fake_redis.zcard(w._AUDIO_QUEUE_KEY) == 0
    assert w._shared_claim() is None, "a cancelled job must never be claimable"

    _capacity(monkeypatch, 1)
    w._dispatch_queued_jobs()
    assert started == []
    assert w._load_job_from_store(job.job_id).status == "failed"


def test_cancel_rejects_a_job_that_is_not_queued(fake_redis, tmp_path):
    job = _accept(tmp_path)
    assert w._shared_claim() == job.job_id  # already running somewhere
    ok, message = w.admin_cancel_queued_job(job.job_id)
    assert not ok
    assert "queued" in message.lower()


def test_deleting_a_job_removes_it_from_the_shared_queue(fake_redis, tmp_path):
    job = _accept(tmp_path)
    w._delete_job(job.job_id)
    assert fake_redis.zcard(w._AUDIO_QUEUE_KEY) == 0


def test_queue_full_rollback_leaves_no_shared_entry(fake_redis, monkeypatch, tmp_path):
    monkeypatch.setattr(w, "_MAX_AUDIO_QUEUE_DEPTH", 1)
    _accept(tmp_path)
    rejected = _new_job(tmp_path)
    w._set_job(rejected)
    assert w._enqueue_job(rejected.job_id, rejected) is False
    w._delete_job(rejected.job_id)  # what the 503 path does
    assert fake_redis.zrank(w._AUDIO_QUEUE_KEY, rejected.job_id) is None
    assert fake_redis.zcard(w._AUDIO_QUEUE_KEY) == 1


def test_requeue_keeps_the_original_place_in_line(fake_redis, tmp_path):
    """The GatingError path gives the slot back without losing priority."""
    now = datetime.now(UTC)
    first = _accept(tmp_path, queued_at=now - timedelta(seconds=60))
    second = _accept(tmp_path, queued_at=now)

    assert w._shared_claim() == first.job_id
    w._requeue_job_at_head(first.job_id, first)

    assert w._queue_position(first.job_id) == 1, "re-queued job keeps the head, not the back"
    assert w._queue_position(second.job_id) == 2


def test_admin_requeue_uses_the_shared_queue(fake_redis, monkeypatch, tmp_path, started):
    job = _new_job(tmp_path)
    job.status = "failed"
    w._set_job(job)
    monkeypatch.setattr(w, "get_temp_dir", lambda token: tmp_path)
    _capacity(monkeypatch, 0)  # queued, not started

    ok, message = w.admin_requeue_failed_job(job.job_id)

    assert ok, message
    assert fake_redis.zrank(w._AUDIO_QUEUE_KEY, job.job_id) == 0
    assert w._load_job_from_store(job.job_id).status == "queued"

    # A second attempt sees the job already sitting in the shared queue.
    with w._jobs_lock:
        w._jobs[job.job_id].status = "failed"
    ok, message = w.admin_requeue_failed_job(job.job_id)
    assert not ok and "already queued" in message.lower()


def test_admin_requeue_refuses_when_the_global_queue_is_full(fake_redis, monkeypatch, tmp_path):
    monkeypatch.setattr(w, "_MAX_AUDIO_QUEUE_DEPTH", 1)
    _accept(tmp_path)  # queued on another worker
    _other_worker()

    failed = _new_job(tmp_path)
    failed.status = "failed"
    w._set_job(failed)
    monkeypatch.setattr(w, "get_temp_dir", lambda token: tmp_path)

    ok, message = w.admin_requeue_failed_job(failed.job_id)
    assert not ok and message == "Queue is full."
    assert w._jobs[failed.job_id].status == "failed", "state must be rolled back"


# ---------------------------------------------------------------------------
# Fallback: no Redis behaves exactly as before
# ---------------------------------------------------------------------------

def test_without_redis_enqueue_uses_the_local_deque(no_redis, monkeypatch, tmp_path):
    monkeypatch.setattr(w, "_MAX_AUDIO_QUEUE_DEPTH", 2)
    a = _accept(tmp_path)
    b = _accept(tmp_path)
    assert list(w._audio_queue) == [a.job_id, b.job_id]

    third = _new_job(tmp_path)
    w._set_job(third)
    assert w._enqueue_job(third.job_id, third) is False
    assert list(w._audio_queue) == [a.job_id, b.job_id]


def test_without_redis_position_comes_from_the_local_deque(no_redis, tmp_path):
    a = _accept(tmp_path)
    b = _accept(tmp_path)
    assert w._queue_position(a.job_id) == 1
    assert w._queue_position(b.job_id) == 2
    assert w._queue_position("nope") is None


def test_without_redis_dispatch_pops_the_local_deque(no_redis, monkeypatch, tmp_path, started):
    a = _accept(tmp_path)
    b = _accept(tmp_path)
    _capacity(monkeypatch, 1)

    w._dispatch_queued_jobs()

    assert started == [(w._run_whisper_job, (a.job_id,))]
    assert list(w._audio_queue) == [b.job_id]
    assert w._jobs[a.job_id].status == "running"


def test_without_redis_requeue_goes_to_the_front(no_redis, tmp_path):
    a = _accept(tmp_path)
    b = _accept(tmp_path)
    with w._jobs_lock:
        w._audio_queue.remove(a.job_id)
    w._requeue_job_at_head(a.job_id, a)
    assert list(w._audio_queue) == [a.job_id, b.job_id]


def test_without_redis_cancel_still_works(no_redis, tmp_path):
    job = _accept(tmp_path)
    ok, _ = w.admin_cancel_queued_job(job.job_id)
    assert ok
    assert list(w._audio_queue) == []


# ---------------------------------------------------------------------------
# Redis outage must never break a request
# ---------------------------------------------------------------------------

def test_redis_errors_degrade_to_the_local_queue(monkeypatch, tmp_path, started):
    w.set_queue_redis_client_for_test(BrokenRedis())
    try:
        job = _new_job(tmp_path)
        w._set_job(job)
        # Enqueue, position and dispatch all keep working locally.
        assert w._enqueue_job(job.job_id, job) is True
        assert list(w._audio_queue) == [job.job_id]
        assert w._queue_position(job.job_id) == 1

        _capacity(monkeypatch, 1)
        w._dispatch_queued_jobs()
        assert started == [(w._run_whisper_job, (job.job_id,))]
    finally:
        w.reset_queue_redis_client_for_test()


def test_shared_helpers_never_raise_on_a_broken_client(monkeypatch, tmp_path):
    w.set_queue_redis_client_for_test(BrokenRedis())
    try:
        assert w._shared_claim() is None
        assert w._shared_depth() is None
        assert w._shared_order() is None
        assert w._shared_enqueue(str(uuid.uuid4()), 1.0) is None
    finally:
        w.reset_queue_redis_client_for_test()
