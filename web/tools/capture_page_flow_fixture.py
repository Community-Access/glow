#!/usr/bin/env python3
"""Capture a live page into a deterministic PageFlow fixture skeleton.

Usage:
  python tools/capture_page_flow_fixture.py \
    --url "https://example.com/article" \
    --name example_article \
    --out web/tests/fixtures/captured/example_article.json

This tool is intentionally non-destructive: it writes a fixture skeleton for
human review before inclusion in regression tests.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

import requests


def _slugify(value: str) -> str:
    safe = []
    for ch in value.lower().strip():
        if ch.isalnum():
            safe.append(ch)
        elif ch in {"-", "_"}:
            safe.append(ch)
        else:
            safe.append("-")
    out = "".join(safe)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "captured_case"


def _extract_next_data(content: str) -> str:
    marker = 'id="__NEXT_DATA__"'
    idx = content.find(marker)
    if idx < 0:
        marker = "id='__NEXT_DATA__'"
        idx = content.find(marker)
    if idx < 0:
        return ""

    script_start = content.rfind("<script", 0, idx)
    if script_start < 0:
        return ""
    gt = content.find(">", idx)
    if gt < 0:
        return ""
    script_end = content.find("</script>", gt)
    if script_end < 0:
        return ""
    return content[gt + 1 : script_end].strip()


def build_fixture(url: str, name: str, timeout: int = 20) -> dict:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "GLOW-PageFlow-Fixture-Capture/1.0"})
    resp.raise_for_status()

    html = resp.text or ""
    final_url = resp.url or url
    next_data = _extract_next_data(html)

    parsed = urlparse(final_url)
    host = parsed.hostname or "unknown-host"

    contains = []
    if next_data:
        try:
            payload = json.loads(next_data)
            title = ((payload.get("props") or {}).get("pageProps") or {}).get("title")
            if isinstance(title, str) and title.strip():
                contains.append(title.strip())
        except Exception:
            pass

    case = {
        "name": _slugify(name),
        "url": final_url,
        "host": host,
        "captured_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "html": html,
        "extract_output": "",
        "contains": contains,
        "not_contains": [],
        "notes": "Review and trim html/extract expectations before adding to CI regression suite.",
    }
    return case


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture a live URL into a PageFlow regression fixture skeleton.")
    parser.add_argument("--url", required=True, help="Source URL to capture")
    parser.add_argument("--name", required=False, help="Fixture case name")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    name = args.name or _slugify(args.url)
    fixture = build_fixture(args.url, name, timeout=args.timeout)

    out_path.write_text(json.dumps(fixture, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"Wrote fixture: {out_path}")
    print(f"Name: {fixture['name']}")
    print(f"Host: {fixture['host']}")
    print(f"URL: {fixture['url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
