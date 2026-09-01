"""Tests for distributed (Redis-backed) concurrency gating with local fallback.

These use a small in-memory fake Redis that implements only the methods
gating.py calls: register_script (returning a callable that replicates the Lua
acquire), ping, zadd, zrem, zremrangebyscore, zcard. Two ``_Gate`` instances
sharing one fake stand in for two Gunicorn workers sharing one Redis.
"""

from __future__ import annotations

import threading
import time
from contextlib import ExitStack

import pytest

from acb_large_print_web import gating
from acb_large_print_web.gating import GatingError


class FakeRedis:
    """Minimal in-memory Redis stand-in for ZSET-based gating."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, float]] = {}
        self._lock = threading.Lock()

    def ping(self) -> bool:
        return True

    def register_script(self, script):
        # Replicate the Lua acquire semantics atomically in Python.
        def run(keys=None, args=None, client=None):
            key = keys[0]
            max_slots = int(args[0])
            now = float(args[1])
            ttl = float(args[2])
            token = args[3]
            with self._lock:
                members = self._store.setdefault(key, {})
                cutoff = now - ttl
                for stale in [t for t, s in members.items() if s < cutoff]:
                    del members[stale]
                if len(members) < max_slots:
                    members[token] = now
                    return token
                return None

        return run

    def zadd(self, key, mapping):
        with self._lock:
            members = self._store.setdefault(key, {})
            for member, score in mapping.items():
                members[member] = float(score)
            return len(mapping)

    def zrem(self, key, *tokens):
        with self._lock:
            members = self._store.get(key, {})
            removed = 0
            for token in tokens:
                if token in members:
                    del members[token]
                    removed += 1
            return removed

    def zremrangebyscore(self, key, min, max):
        lo = float(min)
        hi = float(max)
        with self._lock:
            members = self._store.get(key, {})
            drop = [t for t, s in members.items() if lo <= s <= hi]
            for token in drop:
                del members[token]
            return len(drop)

    def zcard(self, key):
        with self._lock:
            return len(self._store.get(key, {}))


class BrokenRedis(FakeRedis):
    """Pings fine but every acquire raises, to exercise runtime degradation."""

    def register_script(self, script):
        def run(keys=None, args=None, client=None):
            raise RuntimeError("redis exploded")

        return run


@pytest.fixture(autouse=True)
def _reset_gating():
    # Ensure each test starts and ends with env-based resolution so a fake
    # client never leaks into other test modules that import gating.
    gating.reset_redis_client_for_test()
    yield
    gating.reset_redis_client_for_test()


# ---------------------------------------------------------------------------
# Distributed path
# ---------------------------------------------------------------------------

def test_cap_is_shared_across_two_workers():
    fake = FakeRedis()
    gating.set_redis_client_for_test(fake)
    worker_a = gating._Gate("shared", "Test op", max_slots=2, queue_wait_seconds=0, ttl_seconds=60)
    worker_b = gating._Gate("shared", "Test op", max_slots=2, queue_wait_seconds=0, ttl_seconds=60)

    with ExitStack() as stack:
        stack.enter_context(worker_a.gate())
        stack.enter_context(worker_b.gate())
        assert fake.zcard("glow:gate:shared") == 2
        # N+1th acquire across the two workers is refused.
        with pytest.raises(GatingError):
            with worker_a.gate():
                pass


def test_release_frees_a_shared_slot():
    fake = FakeRedis()
    gating.set_redis_client_for_test(fake)
    worker_a = gating._Gate("free", "Test op", max_slots=1, queue_wait_seconds=0, ttl_seconds=60)
    worker_b = gating._Gate("free", "Test op", max_slots=1, queue_wait_seconds=0, ttl_seconds=60)

    with worker_a.gate():
        assert fake.zcard("glow:gate:free") == 1
    # Slot released; the other worker can now acquire.
    assert fake.zcard("glow:gate:free") == 0
    with worker_b.gate():
        assert fake.zcard("glow:gate:free") == 1


def test_expired_slot_is_reclaimed():
    fake = FakeRedis()
    gating.set_redis_client_for_test(fake)
    gate = gating._Gate("reclaim", "Test op", max_slots=1, queue_wait_seconds=0, ttl_seconds=10)
    # A crashed worker left a slot behind with an old timestamp.
    fake.zadd("glow:gate:reclaim", {"leaked": time.time() - 10_000})
    assert fake.zcard("glow:gate:reclaim") == 1

    # A fresh acquire reclaims the leaked slot rather than being blocked by it.
    with gate.gate():
        members = fake._store["glow:gate:reclaim"]
        assert "leaked" not in members
        assert len(members) == 1


def test_wait_seconds_times_out_when_full():
    fake = FakeRedis()
    gating.set_redis_client_for_test(fake)
    holder = gating._Gate("wait", "Test op", max_slots=1, queue_wait_seconds=0, ttl_seconds=60)
    waiter = gating._Gate("wait", "Test op", max_slots=1, queue_wait_seconds=0, ttl_seconds=60)

    with holder.gate():
        start = time.monotonic()
        with pytest.raises(GatingError):
            with waiter.gate(wait_seconds=1):
                pass
        elapsed = time.monotonic() - start
        assert elapsed >= 0.4  # it polled until the deadline instead of failing fast


def test_release_does_not_raise_for_unknown_token():
    fake = FakeRedis()
    gating.set_redis_client_for_test(fake)
    gate = gating._Gate("robust", "Test op", max_slots=1, queue_wait_seconds=0, ttl_seconds=60)
    # Releasing a token that was already reclaimed/expired must be a no-op.
    gate._release_redis(fake, "never-added")


def test_metrics_report_shared_active_counts():
    fake = FakeRedis()
    gating.set_redis_client_for_test(fake)
    with gating.ai_gate():
        metrics = gating.get_capacity_metrics()
        assert metrics["ai"]["active"] == 1
        assert metrics["ai"]["available"] == metrics["ai"]["limit"] - 1
    # Slot released -> shared count returns to zero.
    assert gating.get_capacity_metrics()["ai"]["active"] == 0


# ---------------------------------------------------------------------------
# Fallback path
# ---------------------------------------------------------------------------

def test_local_fallback_enforces_cap_without_redis():
    gating.set_redis_client_for_test(None)  # no Redis configured
    gate = gating._Gate("local", "Test op", max_slots=1, queue_wait_seconds=0, ttl_seconds=60)
    with gate.gate():
        with pytest.raises(GatingError):
            with gate.gate():
                pass


def test_local_fallback_metrics_use_in_process_counts():
    gating.set_redis_client_for_test(None)
    with gating.ai_gate():
        metrics = gating.get_capacity_metrics()
        assert metrics["ai"]["active"] == 1
        assert metrics["ai"]["limit"] == gating._MAX_AI


def test_redis_runtime_error_degrades_to_local():
    gating.set_redis_client_for_test(BrokenRedis())
    gate = gating._Gate("degrade", "Test op", max_slots=1, queue_wait_seconds=0, ttl_seconds=60)
    # Acquire raises inside Redis; the call must still succeed via the local
    # semaphore rather than surfacing an error.
    with gate.gate():
        pass
    # Local cap is still enforced under degradation.
    with gate.gate():
        with pytest.raises(GatingError):
            with gate.gate():
                pass
