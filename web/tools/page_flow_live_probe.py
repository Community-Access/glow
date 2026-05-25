#!/usr/bin/env python3
"""Run non-blocking live probes for PageFlow extraction quality.

This script is intended for nightly observability, not deterministic CI gating.
It reads a URL corpus, attempts extraction, and writes a summary JSON report.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from acb_large_print_web.listen_later import ArticleExtractionError, extract_article


@dataclass
class ProbeResult:
    url: str
    ok: bool
    title: str
    page_count: int
    char_count: int
    duration_ms: int
    error: str


def _load_urls(path: Path) -> list[str]:
    if not path.exists():
        return []
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def _probe(url: str, max_pages: int) -> ProbeResult:
    start = time.perf_counter()
    try:
        article = extract_article(url, max_pages=max_pages, follow_pagination=True)
        duration_ms = int((time.perf_counter() - start) * 1000)
        title = (article.title or "").strip()
        text = article.text or ""
        # Minimal quality guardrails for observability.
        looks_valid = bool(title) and len(text.strip()) >= 80
        return ProbeResult(
            url=url,
            ok=looks_valid,
            title=title,
            page_count=len(article.page_urls),
            char_count=len(text),
            duration_ms=duration_ms,
            error="" if looks_valid else "Extracted output too short or missing title",
        )
    except ArticleExtractionError as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return ProbeResult(url=url, ok=False, title="", page_count=0, char_count=0, duration_ms=duration_ms, error=str(exc))
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        return ProbeResult(url=url, ok=False, title="", page_count=0, char_count=0, duration_ms=duration_ms, error=f"Unhandled error: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="PageFlow live probe runner")
    parser.add_argument("--corpus", default="tests/fixtures/page_flow_live_corpus.txt", help="Path to URL corpus file")
    parser.add_argument("--out", default="test-results/page_flow_live_probe.json", help="Path to output JSON report")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximum pages to follow per URL")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any probe fails")
    args = parser.parse_args()

    corpus_path = Path(args.corpus)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    urls = _load_urls(corpus_path)
    results = [_probe(url, max_pages=max(1, args.max_pages)) for url in urls]

    ok_count = sum(1 for r in results if r.ok)
    fail_count = len(results) - ok_count
    summary = {
        "generated_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "total": len(results),
        "ok": ok_count,
        "failed": fail_count,
        "success_rate": round((ok_count / len(results) * 100.0), 1) if results else 0.0,
        "results": [asdict(r) for r in results],
    }

    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    print(f"PageFlow live probe report written: {out_path}")
    print(f"Total: {summary['total']}  OK: {summary['ok']}  Failed: {summary['failed']}  Success rate: {summary['success_rate']}%")

    if args.strict and fail_count > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
