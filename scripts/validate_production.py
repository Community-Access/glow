#!/usr/bin/env python
"""Is the deployed site actually ready to run a workshop day?

The pre-flight page answers this from inside the app. This answers it from
outside, against whatever is really deployed, so it can be run before a
conference from any machine and again after a deploy to confirm the deploy
did what it claimed.

**Read-only by default.** Every check is a GET against a public surface.
Nothing here creates a session, joins as a participant, or writes a row --
which matters, because merely visiting ``/workshop/?code=X`` calls
``ensure_session()`` and would leave a real session behind in production.

    python scripts/validate_production.py
    python scripts/validate_production.py --base-url https://staging.example.org

Exit code 0 when every required check passes, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "https://letitglow.app"
CONSENT_COOKIE = "glow_consent_v1=1"
SLOW_SECONDS = 2.0

# Surfaces a participant or facilitator reaches on the day. Anything marked
# required must answer 200; the rest are reported but do not fail the run,
# because they depend on work that may not be deployed yet.
SURFACES = [
    ("/workshop/", "Workshop home", True),
    ("/workshop/guide", "Front-facing guide", True),
    ("/workshop/exercises", "Exercise pack", True),
    ("/workshop/utilization", "Utilization guide", True),
    ("/workshop/worksheets.html", "Worksheet pack (HTML)", True),
    ("/workshop/worksheets.docx", "Worksheet pack (Word)", True),
    ("/workshop/resources/guide", "Guide download", True),
    ("/workshop/resources/exercises", "Exercises download", True),
    ("/workshop/resources/utilization", "Utilization download", True),
    ("/audit/", "Audit tool", True),
    ("/fix/", "Fix tool", True),
    ("/convert/", "Convert tool", True),
    ("/mcp/health", "MCP health", True),
    ("/workshop/deck", "Workshop deck", False),
    ("/workshop/deck.pptx", "Deck as PowerPoint", False),
    ("/workshop/deck.docx", "Deck as Word", False),
    ("/workshop/deck.md", "Deck as Markdown", False),
]

WORKSHOP_FLAGS = (
    "GLOW_ENABLE_WORKSHOP_MODE",
    "GLOW_ENABLE_WORKSHOP_LAB_HUB",
    "GLOW_ENABLE_WORKSHOP_GALLERY",
    "GLOW_ENABLE_WORKSHOP_PEER_REVIEW",
)


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []
        self.failed = 0

    def add(self, state: str, label: str, detail: str = "") -> None:
        self.rows.append((state, label, detail))
        if state == "FAIL":
            self.failed += 1

    def render(self) -> None:
        width = max(len(label) for _, label, _ in self.rows) + 2
        for state, label, detail in self.rows:
            print(f"  {state:<5} {label:<{width}} {detail}")


#: Surfaces that needed a second attempt. Reported, so that a surface which
#: always needs one is visible rather than silently smoothed over.
RETRIED: list[str] = []


def fetch(url: str, timeout: int = 30, attempts: int = 2) -> tuple[int, bytes, float]:
    """Fetch a URL, retrying once on a transport error.

    A dropped connection is a network blip, not a broken deployment. Without
    this, one lost packet turns a daily check red and teaches everybody to
    ignore it. HTTP errors are *not* retried: a 404 is an answer.
    """
    request = urllib.request.Request(
        url,
        headers={"Cookie": CONSENT_COOKIE, "User-Agent": "glow-production-validator"},
    )

    last_error = ""
    for attempt in range(1, attempts + 1):
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if attempt > 1:
                    RETRIED.append(url)
                return response.status, body, time.perf_counter() - started
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), time.perf_counter() - started
        except Exception as exc:  # noqa: BLE001 - a probe reports every failure, it does not crash
            last_error = str(exc)
            if attempt < attempts:
                time.sleep(2)

    print(f"    ({last_error})")
    return 0, b"", 0.0


def check_health(base: str, report: Report) -> dict:
    status, body, seconds = fetch(f"{base}/health")
    if status != 200:
        report.add("FAIL", "Health endpoint", f"HTTP {status}")
        return {}

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        report.add("FAIL", "Health endpoint", "response was not JSON")
        return {}

    report.add(
        "OK" if payload.get("status") == "ok" else "FAIL",
        "Health endpoint",
        f"{payload.get('status')}, {seconds * 1000:.0f}ms",
    )
    if seconds > SLOW_SECONDS:
        report.add(
            "WARN",
            "Health response time",
            f"{seconds:.1f}s on one uncontended request; it runs live probes",
        )

    if "deployment" in payload:
        deployment = payload["deployment"]
        report.add(
            "OK" if deployment.get("state") == "completed" else "WARN",
            "Last deploy",
            f"{deployment.get('state')} at {deployment.get('updated_at_utc', 'unknown')}",
        )
        gates = deployment.get("gates", {})
        report.add(
            "OK" if gates.get("wcag22aa") == "passed" else "WARN",
            "WCAG 2.2 AA gate",
            str(gates.get("wcag22aa")),
        )
    else:
        report.add("WARN", "Last deploy", "not in this response; re-run")

    # /health intermittently answers with a reduced payload that omits
    # feature_flags entirely. A missing key is not a disabled flag, and
    # reporting it as one would raise a false alarm about the workshop being
    # switched off. Say "not reported" and mean it.
    if "feature_flags" not in payload:
        report.add(
            "WARN",
            "Workshop feature flags",
            "/health returned a reduced payload with no feature_flags; re-run",
        )
        report.add("WARN", "House AI", "not reported in this response")
        return payload

    flags = payload["feature_flags"]
    off = [name for name in WORKSHOP_FLAGS if flags.get(name) is False]
    absent = [name for name in WORKSHOP_FLAGS if name not in flags]
    if off:
        report.add("FAIL", "Workshop feature flags", ", ".join(off) + " off")
    elif absent:
        report.add("WARN", "Workshop feature flags", ", ".join(absent) + " not reported")
    else:
        report.add("OK", "Workshop feature flags", "all four on")

    ai_on = [k for k, v in flags.items() if k.startswith("GLOW_ENABLE_AI") and v]
    report.add(
        "OK",
        "House AI",
        "off, as the plan intends" if not ai_on else f"on: {', '.join(ai_on)}",
    )
    return payload


def check_surfaces(base: str, report: Report) -> None:
    for path, label, required in SURFACES:
        status, body, seconds = fetch(base + path)
        if status == 200:
            detail = f"{len(body):,} bytes, {seconds * 1000:.0f}ms"
            report.add("WARN" if seconds > SLOW_SECONDS else "OK", label, detail)
        elif required:
            report.add("FAIL", label, f"HTTP {status}")
        else:
            report.add("-", label, f"HTTP {status} (not deployed yet)")


def check_worksheet_is_real(base: str, report: Report) -> None:
    """A 200 that returns an error page is still a 200."""
    status, body, _ = fetch(f"{base}/workshop/worksheets.docx")
    if status != 200:
        report.add("FAIL", "Worksheet pack is a real .docx", f"HTTP {status}")
        return
    # Every .docx is a zip, so it starts with the local file header magic.
    report.add(
        "OK" if body[:2] == b"PK" else "FAIL",
        "Worksheet pack is a real .docx",
        f"{len(body):,} bytes" if body[:2] == b"PK" else "not a zip archive",
    )


def check_mcp_backend(base: str, report: Report) -> None:
    status, body, _ = fetch(f"{base}/mcp/health")
    if status != 200:
        report.add("FAIL", "MCP backend", f"HTTP {status}")
        return
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        report.add("FAIL", "MCP backend", "response was not JSON")
        return
    backend = payload.get("shared_core", {}).get("backend")
    report.add(
        "OK" if backend == "glow" else "FAIL",
        "MCP backend",
        f"backend={backend}",
    )


def check_short_urls(base: str, report: Report) -> None:
    """`/w` must redirect rather than 404. No session code: that would write."""
    request = urllib.request.Request(
        f"{base}/w",
        headers={"Cookie": CONSENT_COOKIE, "User-Agent": "glow-production-validator"},
    )

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=30) as response:
            code = response.status
    except urllib.error.HTTPError as exc:
        code = exc.code
    except Exception as exc:  # noqa: BLE001 - a probe reports every failure, it does not crash
        report.add("FAIL", "Short URL /w", str(exc))
        return
    report.add(
        "OK" if code in (301, 302, 303, 307, 308) else "FAIL",
        "Short URL /w",
        f"HTTP {code}",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"Validating {base}  (read-only: no session is created, no row is written)")
    print("=" * 74)

    report = Report()
    check_health(base, report)
    check_mcp_backend(base, report)
    check_short_urls(base, report)
    check_surfaces(base, report)
    check_worksheet_is_real(base, report)

    report.render()
    if RETRIED:
        print()
        print(f"  {len(RETRIED)} request(s) needed a second attempt:")
        for url in dict.fromkeys(RETRIED):
            print(f"    {url}")
        print("  One blip is noise. The same surface retrying every run is not.")
    print("=" * 74)

    if report.failed:
        print(f"  {report.failed} required check(s) failed.")
        return 1
    print("  All required checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
