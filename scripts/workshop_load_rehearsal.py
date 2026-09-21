#!/usr/bin/env python
"""Thirty people in one room, on one wifi, for seven hours.

The readiness plan calls this the largest remaining unknown, and it is: every
other risk in the workshop has been reasoned about, and this one has only been
reasoned about. Nothing here has ever been measured at room scale.

What this rehearses, specifically:

* **The rate limiter.** Limits used to be keyed on IP with a 120/minute
  default, which a conference NAT address shares between the whole room. That
  was fixed to key on the participant cookie, and static files were exempted.
  This is the check that the fix holds when thirty cookies arrive at once.
* **Write contention.** Every participant saves into one SQLite file. Saving
  is an upsert per participant per activity, and thirty of them land in the
  same few minutes at the start of each block.
* **The live room.** The gallery and the facilitator pulse poll while people
  are working, so the read load is not idle while the writes happen.

Pass criteria, from the readiness plan: **no 429s, and no request over two
seconds.**

Usage:

    python scripts/workshop_load_rehearsal.py --participants 30
    python scripts/workshop_load_rehearsal.py --base-url https://letitglow.app --code ahg-2026

With no ``--base-url`` it runs the app in-process against a temporary
instance directory, which measures the application without a network or a
production database in the way. Run it both ways: in-process tells you whether
the code is fast enough, and against the deployment tells you whether the
deployment is.

Nothing here writes to a real session unless you point it at one. Use a
throwaway code when running against production, and delete it afterwards.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "web" / "src"))

# The eleven activities, in the order a participant meets them.
ACTIVITY_SEQUENCE = [
    "journey_check_in",
    "problem_statement",
    "teach_vs_fix",
    "ai_boundary_map",
    "agent_formula",
    "lab_accessible_communication",
    "lab_alt_text_decision",
    "lab_remediation_plan",
    "champion_studio",
    "capstone_shareout",
    "action_plan_30_day",
]

SLOW_REQUEST_SECONDS = 2.0


@dataclass
class Sample:
    label: str
    seconds: float
    status: int


@dataclass
class Results:
    samples: list[Sample] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, label: str, seconds: float, status: int) -> None:
        with self.lock:
            self.samples.append(Sample(label, seconds, status))

    def fail(self, message: str) -> None:
        with self.lock:
            self.errors.append(message)

    @property
    def rate_limited(self) -> list[Sample]:
        return [s for s in self.samples if s.status == 429]

    @property
    def slow(self) -> list[Sample]:
        return [s for s in self.samples if s.seconds > SLOW_REQUEST_SECONDS]

    @property
    def failed(self) -> list[Sample]:
        return [s for s in self.samples if s.status >= 400 and s.status != 429]


def _field_values(app_module, activity_key: str) -> dict[str, str]:
    """Fill every required field, the way a participant would."""
    fields = app_module.ACTIVITY_FIELDS.get(activity_key, [])
    values: dict[str, str] = {}
    for spec in fields:
        values[spec["name"]] = (
            "Rehearsal answer. Long enough to be a realistic write, because a "
            "one-word answer does not exercise the same storage path that a "
            "real participant's paragraph does."
        )
    values["display_name"] = "Rehearsal participant"
    values["submit_action"] = "save"
    return values


def run_participant(index: int, client_factory, code: str, results: Results, app_module) -> None:
    client = client_factory()
    label = f"participant-{index:02d}"

    def timed(name: str, fn) -> object:
        started = time.perf_counter()
        try:
            response = fn()
        except Exception as exc:  # pragma: no cover - reported, not raised
            results.fail(f"{label} {name}: {exc}")
            return None
        elapsed = time.perf_counter() - started
        results.record(name, elapsed, response.status_code)
        return response

    timed("join", lambda: client.post(
        "/workshop/",
        data={"action": "join", "session_code": code, "display_name": f"Rehearsal {index}"},
    ))

    for activity_key in ACTIVITY_SEQUENCE:
        timed(f"GET {activity_key}", lambda k=activity_key: client.get(
            f"/workshop/session/{code}/activity/{k}"
        ))
        timed(f"POST {activity_key}", lambda k=activity_key: client.post(
            f"/workshop/session/{code}/activity/{k}",
            data=_field_values(app_module, k),
        ))
        # Between activities people look at the gallery and their own content.
        timed("gallery", lambda: client.get(f"/workshop/session/{code}/gallery"))

    timed("my content", lambda: client.get(f"/workshop/session/{code}/me"))
    timed("artifact", lambda: client.get(f"/workshop/session/{code}/artifact"))


def build_in_process(code: str):
    """Run against the app itself, with a throwaway instance directory."""
    from acb_large_print_web.app import create_app
    from acb_large_print_web.routes import workshop as workshop_routes
    from acb_large_print_web.workshop_store import ensure_session

    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    app.instance_path = tempfile.mkdtemp(prefix="glow-load-")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    with app.app_context():
        ensure_session(code, title="Load rehearsal", event_name="AHG rehearsal")

    def factory():
        client = app.test_client()
        client.set_cookie("glow_consent_v1", "1", domain="localhost")
        return client

    return factory, workshop_routes, app.instance_path


def build_http(base_url: str):
    """Run against a deployment. Needs `requests`."""
    import requests

    from acb_large_print_web.routes import workshop as workshop_routes

    class HttpClient:
        def __init__(self) -> None:
            self.session = requests.Session()
            self.session.cookies.set("glow_consent_v1", "1")

        def get(self, path: str):
            return self.session.get(base_url.rstrip("/") + path, timeout=30)

        def post(self, path: str, data=None):
            return self.session.post(base_url.rstrip("/") + path, data=data or {}, timeout=30)

    return HttpClient, workshop_routes, ""


def summarise(results: Results, participants: int, elapsed: float, in_process: bool) -> int:
    samples = results.samples
    if not samples:
        print("No samples recorded. Something is wrong with the harness.")
        return 1

    times = sorted(s.seconds for s in samples)
    p50 = statistics.median(times)
    p95 = times[int(len(times) * 0.95) - 1] if len(times) >= 20 else times[-1]

    print()
    print("=" * 62)
    print(f"Workshop load rehearsal: {participants} participants")
    print("=" * 62)
    print(f"  requests         {len(samples)}")
    print(f"  wall clock       {elapsed:.1f}s")
    print(f"  median           {p50 * 1000:.0f}ms")
    print(f"  p95              {p95 * 1000:.0f}ms")
    print(f"  slowest          {times[-1] * 1000:.0f}ms")
    print()

    pass_criteria = True

    if results.rate_limited:
        pass_criteria = False
        print(f"  FAIL  {len(results.rate_limited)} request(s) rate limited (429)")
        for sample in results.rate_limited[:5]:
            print(f"          {sample.label}")
    else:
        print("  OK    no request was rate limited")

    if results.slow:
        pass_criteria = False
        print(f"  FAIL  {len(results.slow)} request(s) over {SLOW_REQUEST_SECONDS:.0f}s")
        worst = sorted(results.slow, key=lambda s: -s.seconds)[:5]
        for sample in worst:
            print(f"          {sample.seconds * 1000:.0f}ms  {sample.label}")
    else:
        print(f"  OK    no request over {SLOW_REQUEST_SECONDS:.0f}s")

    if results.failed:
        pass_criteria = False
        print(f"  FAIL  {len(results.failed)} request(s) returned an error status")
        for sample in results.failed[:5]:
            print(f"          {sample.status}  {sample.label}")
    else:
        print("  OK    no error responses")

    if results.errors:
        pass_criteria = False
        print(f"  FAIL  {len(results.errors)} exception(s)")
        for message in results.errors[:5]:
            print(f"          {message}")

    print()
    print("  " + ("PASS - the room is survivable at this size."
                  if pass_criteria else
                  "FAIL - see above. This is the rehearsal doing its job."))

    if in_process and participants > 1:
        print()
        print("  Reading an in-process run:")
        print("    Thirty participants here are thirty threads sharing one GIL")
        print("    and one test client, so they queue in a way production does")
        print("    not - gunicorn runs several worker processes. Run with")
        print("    --participants 1 for the uncontended cost of each request;")
        print("    multiply by the participant count for the serialized floor.")
        print()
        print("    So treat latency from this mode as pessimistic about")
        print("    concurrency and optimistic about everything else. What it")
        print("    does prove is contention: lock errors, 429s and error")
        print("    statuses are real wherever they show up.")
        print()
        print("    The number that decides the room is a run against the")
        print("    deployment: --base-url https://letitglow.app --code <throwaway>")

    print("=" * 62)
    return 0 if pass_criteria else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--participants", type=int, default=30)
    parser.add_argument("--code", default="load-rehearsal")
    parser.add_argument("--base-url", default="", help="Run against a deployment instead of in-process.")
    parser.add_argument("--json", default="", help="Write the samples to this path.")
    args = parser.parse_args()

    if args.base_url:
        factory, workshop_routes, _ = build_http(args.base_url)
        print(f"Rehearsing against {args.base_url}, session {args.code!r}")
    else:
        factory, workshop_routes, instance = build_in_process(args.code)
        print(f"Rehearsing in-process, instance at {instance}")

    results = Results()
    threads = [
        threading.Thread(
            target=run_participant,
            args=(i, factory, args.code, results, workshop_routes),
            daemon=True,
        )
        for i in range(1, args.participants + 1)
    ]

    started = time.perf_counter()
    # Everyone arrives at once, which is what a facilitator saying "go" does.
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    elapsed = time.perf_counter() - started

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                [{"label": s.label, "ms": round(s.seconds * 1000), "status": s.status}
                 for s in results.samples],
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Samples written to {args.json}")

    return summarise(results, args.participants, elapsed, in_process=not args.base_url)


if __name__ == "__main__":
    raise SystemExit(main())
