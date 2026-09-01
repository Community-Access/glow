"""Site accessibility scanning helpers for the web-facing site-audit workflow."""

from __future__ import annotations

import csv
import hashlib
import ipaddress
import json
import re
import shutil
import socket
import subprocess
import time
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urljoin, urlparse

import requests
from defusedxml import ElementTree


WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
_RUN_ID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

_WCAG_UNDERSTANDING_URLS: dict[str, str] = {
    "1.1.1": "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html",
    "1.3.1": "https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html",
    "1.3.2": "https://www.w3.org/WAI/WCAG22/Understanding/meaningful-sequence.html",
    "1.4.3": "https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html",
    "2.1.1": "https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html",
    "2.4.1": "https://www.w3.org/WAI/WCAG22/Understanding/bypass-blocks.html",
    "2.4.2": "https://www.w3.org/WAI/WCAG22/Understanding/page-titled.html",
    "2.4.3": "https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html",
    "2.4.4": "https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html",
    "2.4.6": "https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html",
    "2.4.7": "https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html",
    "3.1.1": "https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html",
    "3.3.1": "https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html",
    "3.3.2": "https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html",
    "4.1.2": "https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html",
    "4.1.3": "https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html",
}

_RULE_LEARNING_URLS: dict[str, list[tuple[str, str]]] = {
    "HEURISTIC-HTML-LANG": [
        ("W3C: Language of Page (SC 3.1.1)", _WCAG_UNDERSTANDING_URLS["3.1.1"]),
        ("MDN: The html lang attribute", "https://developer.mozilla.org/docs/Web/HTML/Global_attributes/lang"),
    ],
    "HEURISTIC-HTML-TITLE": [
        ("W3C: Page Titled (SC 2.4.2)", _WCAG_UNDERSTANDING_URLS["2.4.2"]),
        ("W3C Tutorial: Page structure", "https://www.w3.org/WAI/tutorials/page-structure/"),
    ],
    "HEURISTIC-IMG-ALT": [
        ("W3C: Non-text Content (SC 1.1.1)", _WCAG_UNDERSTANDING_URLS["1.1.1"]),
        ("W3C Tutorial: Images concepts", "https://www.w3.org/WAI/tutorials/images/"),
    ],
    "HEURISTIC-LINK-TEXT": [
        ("W3C: Link Purpose (SC 2.4.4)", _WCAG_UNDERSTANDING_URLS["2.4.4"]),
        ("W3C Tutorial: Link text", "https://www.w3.org/WAI/tutorials/links/link-text/"),
    ],
    "AXE-COLOR-CONTRAST": [
        ("W3C: Contrast Minimum (SC 1.4.3)", _WCAG_UNDERSTANDING_URLS["1.4.3"]),
        ("A11Y Project: Color contrast", "https://www.a11yproject.com/posts/what-is-color-contrast/"),
    ],
    "AXE-IMAGE-ALT": [
        ("W3C: Non-text Content (SC 1.1.1)", _WCAG_UNDERSTANDING_URLS["1.1.1"]),
        ("W3C Tutorial: Images concepts", "https://www.w3.org/WAI/tutorials/images/"),
    ],
    "AXE-LINK-NAME": [
        ("W3C: Link Purpose (SC 2.4.4)", _WCAG_UNDERSTANDING_URLS["2.4.4"]),
        ("W3C Tutorial: Link text", "https://www.w3.org/WAI/tutorials/links/link-text/"),
    ],
}


@dataclass(slots=True)
class SiteAuditOptions:
    max_pages: int = 10
    crawl_links: bool = True
    crawl_depth: int = 1
    include_subdomains: bool = False
    same_path_only: bool = False
    exclude_url_patterns: tuple[str, ...] = ()
    strict_open_source_only: bool = False
    force: bool = False


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.doc_lang = ""
        self.title = ""
        self._in_title = False
        self._title_parts: list[str] = []
        self.img_missing_alt = 0
        self.links: list[tuple[str, str]] = []
        self._current_anchor_href = ""
        self._current_anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag == "html":
            self.doc_lang = (attrs_map.get("lang") or "").strip()
        elif tag == "title":
            self._in_title = True
            self._title_parts = []
        elif tag == "img":
            if "alt" not in attrs_map:
                self.img_missing_alt += 1
        elif tag == "a":
            self._current_anchor_href = (attrs_map.get("href") or "").strip()
            self._current_anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        elif self._current_anchor_href:
            self._current_anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            self.title = "".join(self._title_parts).strip()
        elif tag == "a" and self._current_anchor_href:
            anchor_text = " ".join(p.strip() for p in self._current_anchor_text if p.strip()).strip()
            self.links.append((self._current_anchor_href, anchor_text))
            self._current_anchor_href = ""
            self._current_anchor_text = []

    def close(self) -> None:
        # Flush title/anchor state that a missing or chunk-split closing tag
        # never committed, so a compliant page is not reported as title-less
        # and a trailing link is not dropped from the crawl frontier.
        super().close()
        if self._in_title and not self.title:
            self.title = "".join(self._title_parts).strip()
            self._in_title = False
        if self._current_anchor_href:
            anchor_text = " ".join(p.strip() for p in self._current_anchor_text if p.strip()).strip()
            self.links.append((self._current_anchor_href, anchor_text))
            self._current_anchor_href = ""
            self._current_anchor_text = []


def is_valid_run_id(run_id: str) -> bool:
    return bool(_RUN_ID_RE.match((run_id or "").strip()))


def get_run_dir(base_dir: Path, run_id: str) -> Path | None:
    if not is_valid_run_id(run_id):
        return None
    run_dir = (base_dir / run_id).resolve()
    try:
        run_dir.relative_to(base_dir.resolve())
    except ValueError:
        return None
    if not run_dir.exists() or not run_dir.is_dir():
        return None
    return run_dir


def parse_input_urls(sources: str, sitemap_url: str) -> list[str]:
    values: list[str] = []
    for line in (sources or "").splitlines():
        candidate = _normalize_url(line.strip())
        if candidate:
            values.append(candidate)
    if sitemap_url.strip():
        values.extend(_read_sitemap_urls(_normalize_url(sitemap_url.strip())))
    deduped: list[str] = []
    seen: set[str] = set()
    for url in values:
        if url not in seen:
            seen.add(url)
            deduped.append(url)
    return deduped


def run_site_audit(
    *,
    run_id: str,
    base_dir: Path,
    sources: list[str],
    options: SiteAuditOptions,
    is_cancelled: Callable[[], bool] | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()

    log_lines: list[str] = []
    log_lines.append(f"run_id={run_id}")
    log_lines.append(f"started_utc={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(started))}")
    log_lines.append(f"sources={len(sources)}")
    log_lines.append(f"max_pages={options.max_pages}")
    log_lines.append(f"crawl_links={str(options.crawl_links).lower()}")
    log_lines.append(f"crawl_depth={options.crawl_depth}")
    log_lines.append(f"include_subdomains={str(options.include_subdomains).lower()}")
    log_lines.append(f"same_path_only={str(options.same_path_only).lower()}")
    log_lines.append(f"exclude_url_patterns={len(options.exclude_url_patterns)}")
    log_lines.append(f"strict_open_source_only={str(options.strict_open_source_only).lower()}")
    log_lines.append(f"force={str(options.force).lower()}")

    if options.crawl_links:
        scan_urls = _expand_with_crawl(
            sources,
            max_pages=options.max_pages,
            crawl_depth=options.crawl_depth,
            include_subdomains=options.include_subdomains,
            same_path_only=options.same_path_only,
            exclude_url_patterns=options.exclude_url_patterns,
            is_cancelled=is_cancelled,
        )
    else:
        scan_urls = [
            url
            for url in sources
            if not _is_excluded_url(url, options.exclude_url_patterns)
        ][: options.max_pages]

    all_findings: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    wcag_rollup: dict[str, int] = {}
    totals = {"scanned": 0, "failed": 0, "skipped": 0}
    cancelled = False

    for index, url in enumerate(scan_urls, start=1):
        if is_cancelled and is_cancelled():
            cancelled = True
            log_lines.append(f"[{index}/{len(scan_urls)}] cancelled before {url}")
            break

        if progress_callback:
            progress_callback(index, len(scan_urls), url)

        slug = _slug_for_url(url)
        page_dir = run_dir / "pages" / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        page_json = page_dir / "page.json"

        if page_json.exists() and not options.force:
            previous = _load_json(page_json, None)
            if not isinstance(previous, dict) or "url" not in previous or "result" not in previous:
                # A corrupt or truncated cached page.json would otherwise be
                # pushed straight into the summary, rendering a row with no url
                # or result. Re-scan instead of trusting the bad cache.
                log_lines.append(
                    f"[{index}/{len(scan_urls)}] cached page.json invalid, re-scanning {url}"
                )
            else:
                previous["result"] = "skipped"
                previous["reason"] = "existing output"
                previous["index"] = index
                pages.append(previous)
                totals["skipped"] += 1
                # Aggregate the findings the cached page already recorded, so a
                # run that reuses cached output still reports its findings
                # instead of "0 findings".
                for finding in previous.get("findings", []):
                    all_findings.append(finding)
                for tag, count in (previous.get("wcag_tags") or {}).items():
                    wcag_rollup[tag] = wcag_rollup.get(tag, 0) + int(count)
                log_lines.append(f"[{index}/{len(scan_urls)}] skipped {url} (existing output)")
                continue

        log_lines.append(f"[{index}/{len(scan_urls)}] scanning {url}")
        page_result = _scan_single_page(
            url,
            page_dir,
            strict_open_source_only=options.strict_open_source_only,
        )
        page_result["index"] = index
        pages.append(page_result)

        if page_result["result"] == "ok":
            totals["scanned"] += 1
        else:
            totals["failed"] += 1

        for finding in page_result.get("findings", []):
            all_findings.append(finding)
        for tag, count in page_result.get("wcag_tags", {}).items():
            wcag_rollup[tag] = wcag_rollup.get(tag, 0) + int(count)

        _write_json(page_json, page_result)

    elapsed_ms = int((time.time() - started) * 1000)
    summary = {
        "run_id": run_id,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "elapsed_ms": elapsed_ms,
        "options": {
            "max_pages": options.max_pages,
            "crawl_links": options.crawl_links,
            "crawl_depth": options.crawl_depth,
            "include_subdomains": options.include_subdomains,
            "same_path_only": options.same_path_only,
            "exclude_url_patterns": list(options.exclude_url_patterns),
            "strict_open_source_only": options.strict_open_source_only,
            "force": options.force,
        },
        "totals": {
            **totals,
            "findings": len(all_findings),
            "pages_total": len(scan_urls),
        },
        "cancelled": cancelled,
        "wcag_rollup": dict(sorted(wcag_rollup.items())),
        "pages": pages,
    }

    _write_json(run_dir / "summary.json", summary)
    _write_findings_csv(run_dir / "findings.csv", all_findings)
    _write_log(run_dir / "session.log", log_lines)
    _write_zip(run_dir)
    return summary


def _scan_single_page(url: str, page_dir: Path, *, strict_open_source_only: bool = False) -> dict[str, Any]:
    try:
        resp = _http_get(url, timeout=20)
    except Exception as exc:
        # Includes BlockedURLError (SSRF gate) and ordinary network failures;
        # one page erroring must not abort the whole run.
        return {
            "url": url,
            "result": "error",
            "status_code": None,
            "reason": str(exc),
            "title": "",
            "findings": [],
            "wcag_tags": {},
        }

    status_code = getattr(resp, "status_code", None)
    if isinstance(status_code, int) and status_code >= 400:
        # An error page is not an audited page. Recording it as "ok" counted a
        # 404/500 body toward coverage and, since it has no title or lang,
        # produced two "high" findings against a URL that never really renders.
        return {
            "url": url,
            "result": "error",
            "status_code": status_code,
            "reason": f"HTTP {status_code}",
            "title": "",
            "findings": [],
            "wcag_tags": {},
        }

    # Only HTML bodies are parseable; a linked PDF or image served at a URL we
    # crawled would otherwise be pulled fully into the parser. Skip anything
    # that is not (X)HTML, or that declares no content type at all.
    headers = getattr(resp, "headers", None)
    content_type = str(headers.get("Content-Type", "") or "") if headers else ""
    main_type = content_type.split(";", 1)[0].strip().lower()
    if main_type not in {"text/html", "application/xhtml+xml"}:
        return {
            "url": url,
            "final_url": getattr(resp, "url", url),
            "result": "skipped",
            "status_code": status_code,
            "reason": f"Unsupported content type: {content_type or 'none'}",
            "title": "",
            "findings": [],
            "wcag_tags": {},
        }

    # requests defaults an un-declared text/* charset to ISO-8859-1, which
    # mojibakes UTF-8 pages (garbled titles). When the server sent no charset,
    # fall back to the byte-sniffed encoding before decoding.
    if "charset=" not in content_type.lower():
        apparent = getattr(resp, "apparent_encoding", None)
        if apparent:
            try:
                resp.encoding = apparent
            except Exception:
                pass

    html = resp.text or ""
    (page_dir / "page.html").write_text(html, encoding="utf-8", errors="ignore")

    parser = _PageParser()
    parser.feed(html)
    # HTMLParser only commits title/link state on the closing tag; without
    # close() a page whose </title> is missing or split across chunks is
    # wrongly reported as having no title.
    parser.close()

    findings: list[dict[str, Any]] = []
    if not parser.doc_lang:
        findings.append(
            _finding(
                url,
                "HEURISTIC-HTML-LANG",
                "serious",
                "Document root is missing a lang attribute.",
                "html",
                wcag_tags=["wcag311"],
                strict_open_source_only=strict_open_source_only,
            )
        )
    if not parser.title:
        findings.append(
            _finding(
                url,
                "HEURISTIC-HTML-TITLE",
                "serious",
                "Document is missing a non-empty title element.",
                "head > title",
                wcag_tags=["wcag242"],
                strict_open_source_only=strict_open_source_only,
            )
        )
    if parser.img_missing_alt:
        findings.append(
            _finding(
                url,
                "HEURISTIC-IMG-ALT",
                "serious",
                f"Detected {parser.img_missing_alt} image element(s) missing alt text.",
                "img",
                wcag_tags=["wcag111"],
                strict_open_source_only=strict_open_source_only,
            )
        )

    generic_count = 0
    for _, text in parser.links:
        normalized = text.strip().lower()
        if normalized in {"click here", "here", "read more", "learn more", "more"}:
            generic_count += 1
    if generic_count:
        findings.append(
            _finding(
                url,
                "HEURISTIC-LINK-TEXT",
                "moderate",
                f"Detected {generic_count} link(s) with non-descriptive text.",
                "a",
                wcag_tags=["wcag244"],
                strict_open_source_only=strict_open_source_only,
            )
        )

    wcag_tags: dict[str, int] = {}
    axe_json_path = page_dir / "axe.json"
    axe_data: dict[str, Any] | list[dict[str, Any]] | None = None
    axe_error = None
    if _axe_available():
        try:
            _run_axe(url, axe_json_path)
            axe_data = _load_json(axe_json_path, None)
        except Exception as exc:
            axe_error = str(exc)

    if axe_data:
        violations = axe_data if isinstance(axe_data, list) else [axe_data]
        for raw_page in violations:
            page = raw_page if isinstance(raw_page, dict) else {}
            for raw_violation in page.get("violations", []):
                if not isinstance(raw_violation, dict):
                    continue
                violation = raw_violation
                rule_id = (violation.get("id") or "axe-unknown").upper()
                impact = str(violation.get("impact") or "moderate").lower()
                severity = _severity_for_impact(impact)
                help_text = violation.get("help") or "Accessibility violation detected."
                help_url = violation.get("helpUrl") or ""
                violation_tags = [str(tag) for tag in (violation.get("tags") or [])]
                nodes = violation.get("nodes") or []
                count = max(1, len(nodes))
                selector = ""
                if nodes:
                    target = nodes[0].get("target") or []
                    selector = " > ".join(str(x) for x in target if x)
                findings.append(
                    _finding(
                        url,
                        f"AXE-{rule_id}",
                        severity,
                        f"{help_text} ({count} node(s)).",
                        selector,
                        help_url,
                        wcag_tags=violation_tags,
                        strict_open_source_only=strict_open_source_only,
                    )
                )
                for tag in violation_tags:
                    if str(tag).lower().startswith("wcag"):
                        wcag_tags[tag] = wcag_tags.get(tag, 0) + count
    elif axe_error:
        findings.append(
            _finding(
                url,
                "AXE-UNAVAILABLE",
                "minor",
                f"axe-cli scan unavailable: {axe_error}",
                "",
                strict_open_source_only=strict_open_source_only,
            )
        )

    return {
        "url": url,
        "final_url": resp.url,
        "result": "ok",
        "status_code": resp.status_code,
        "title": parser.title,
        "doc_lang": parser.doc_lang,
        "findings": findings,
        "finding_count": len(findings),
        "wcag_tags": dict(sorted(wcag_tags.items())),
    }


def _expand_with_crawl(
    sources: list[str],
    *,
    max_pages: int,
    crawl_depth: int,
    include_subdomains: bool,
    same_path_only: bool,
    exclude_url_patterns: tuple[str, ...],
    is_cancelled: Callable[[], bool] | None = None,
) -> list[str]:
    queue: list[tuple[str, int, str]] = [(url, 0, url) for url in sources]
    # Mirror the frontier in a set so the membership test on every discovered
    # link is O(1) instead of rebuilding a set from the whole queue per link.
    queued: set[str] = {url for url in sources}
    visited: list[str] = []
    seen: set[str] = set()

    while queue and len(visited) < max_pages:
        if is_cancelled and is_cancelled():
            break
        url, depth, seed_url = queue.pop(0)
        if url in seen:
            continue
        if _is_excluded_url(url, exclude_url_patterns):
            continue
        seen.add(url)
        visited.append(url)

        if depth >= crawl_depth:
            continue

        try:
            resp = _http_get(url, timeout=15)
        except Exception:
            continue
        parser = _PageParser()
        parser.feed(resp.text or "")
        parser.close()
        for href, _ in parser.links:
            candidate = _normalize_url(urljoin(resp.url, href))
            if not candidate:
                continue
            if not _same_site(seed_url, candidate, include_subdomains):
                continue
            if same_path_only and not _same_or_descendant_path(seed_url, candidate):
                continue
            if _is_excluded_url(candidate, exclude_url_patterns):
                continue
            if candidate not in seen and candidate not in queued:
                queue.append((candidate, depth + 1, seed_url))
                queued.add(candidate)

    return visited


def _same_or_descendant_path(base: str, candidate: str) -> bool:
    base_path = (urlparse(base).path or "/").rstrip("/")
    candidate_path = (urlparse(candidate).path or "/").rstrip("/")
    if not base_path:
        base_path = "/"
    if not candidate_path:
        candidate_path = "/"
    if base_path == "/":
        return True
    return candidate_path == base_path or candidate_path.startswith(base_path + "/")


def _is_excluded_url(url: str, patterns: tuple[str, ...]) -> bool:
    if not patterns:
        return False
    lowered = url.lower()
    return any(pattern.lower() in lowered for pattern in patterns if pattern)


def _same_site(base: str, candidate: str, include_subdomains: bool) -> bool:
    base_host = (urlparse(base).hostname or "").lower()
    cand_host = (urlparse(candidate).hostname or "").lower()
    if not base_host or not cand_host:
        return False
    if cand_host == base_host:
        return True
    if include_subdomains and cand_host.endswith("." + base_host):
        return True
    return False


_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


def _normalize_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        # A bare host ("example.com/path") gets https://, but a non-web scheme
        # ("mailto:", "tel:", "javascript:") must be rejected -- prefixing it
        # produced "https://mailto:info@x", which urlparse read as host
        # "mailto" with userinfo, so the crawler queued and fetched it as a
        # same-site page and reported bogus findings against it.
        if _SCHEME_RE.match(value):
            return ""
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    # Drop the fragment so "/page" and "/page#section" are one page, not two
    # (in-page anchors and skip links otherwise exhaust the max_pages budget
    # re-scanning identical HTML).
    parsed = parsed._replace(fragment="")
    return parsed.geturl()


_ALLOWED_FETCH_PORTS = {80, 443}
_MAX_FETCH_BYTES = 8 * 1024 * 1024
_MAX_FETCH_REDIRECTS = 5
_FETCH_HEADERS = {"User-Agent": "GLOW-SiteAudit/1.0"}


class BlockedURLError(Exception):
    """Raised when a target URL resolves to a non-public address (SSRF guard)."""


def _ip_is_public(ip_str: str) -> bool:
    """Return True only for a genuinely routable public address."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _is_public_url(url: str) -> bool:
    """Return True only if every address the host resolves to is public.

    The auditor fetches whatever URL an anonymous visitor submits, so without
    this gate the tool is a server-side request forgery primitive: a request
    for ``http://169.254.169.254/...`` or ``http://redis:6379/`` would let the
    submitter read cloud-metadata credentials and internal services through the
    saved page body. Reject loopback, private, link-local, reserved, multicast
    and unspecified addresses, and anything not on an ordinary web port.

    This is a fast pre-check for a clean error message. It is not the only
    defense: DNS can rebind between this lookup and the socket connect, so the
    guarded fetch session below also validates the *actual* peer address at
    connect time (see ``_GuardedHTTPSConnection``), which is TOCTOU-free.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname
    if not host:
        return False
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return False
    if port not in _ALLOWED_FETCH_PORTS:
        return False
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        if not _ip_is_public(info[4][0]):
            return False
    return True


def _assert_public_peer(sock) -> None:
    """Abort a connection whose actual peer is not a public address.

    Called at connect time, after the socket has connected, so the address
    validated is exactly the one bytes would be sent to -- closing the DNS
    rebinding window that a name-based pre-check alone leaves open.
    """
    try:
        peer = sock.getpeername()[0]
    except OSError:
        raise BlockedURLError("Could not determine peer address")
    if not _ip_is_public(peer):
        raise BlockedURLError(f"Refusing to connect to non-public address {peer}")


def _build_guarded_session() -> "requests.Session":
    """A requests Session whose connections validate the peer IP at connect time.

    Implemented by subclassing urllib3's connection classes so the check runs
    inside ``connect()`` -- no DNS/SNI/cert behavior is changed, we merely refuse
    to proceed once the real peer turns out to be internal. If urllib3 internals
    differ from what we expect, fall back to a plain session (still protected by
    the ``_is_public_url`` pre-check on every hop, just not TOCTOU-free).
    """
    session = requests.Session()
    try:
        from urllib3.connection import HTTPConnection, HTTPSConnection
        from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
        from urllib3.poolmanager import PoolManager
        from requests.adapters import HTTPAdapter

        class _GuardedHTTPConnection(HTTPConnection):
            def connect(self):
                super().connect()
                _assert_public_peer(self.sock)

        class _GuardedHTTPSConnection(HTTPSConnection):
            def connect(self):
                super().connect()
                _assert_public_peer(self.sock)

        class _GuardedHTTPPool(HTTPConnectionPool):
            ConnectionCls = _GuardedHTTPConnection

        class _GuardedHTTPSPool(HTTPSConnectionPool):
            ConnectionCls = _GuardedHTTPSConnection

        class _GuardedPoolManager(PoolManager):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.pool_classes_by_scheme = {
                    "http": _GuardedHTTPPool,
                    "https": _GuardedHTTPSPool,
                }

        class _GuardedAdapter(HTTPAdapter):
            def init_poolmanager(self, connections, maxsize, block=False, **kw):
                self.poolmanager = _GuardedPoolManager(
                    num_pools=connections, maxsize=maxsize, block=block, **kw
                )

        adapter = _GuardedAdapter()
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    except Exception:  # pragma: no cover - urllib3 shape changed; degrade safely
        pass
    return session


_guarded_session = _build_guarded_session()


def _http_get(url: str, *, timeout: int) -> requests.Response:
    """SSRF-guarded GET.

    Validates the public-address gate on the initial URL and on every redirect
    hop (so an attacker cannot 302 an allowed host to an internal one), and caps
    the body read so a decompression bomb cannot exhaust memory or disk. The
    fetch runs on a session that also re-validates the real peer IP at connect
    time, so a DNS rebind between the name check and the socket cannot slip an
    internal address through. Raises BlockedURLError for a non-public target or
    too many redirects; other network failures propagate as requests exceptions.
    """
    current = url
    for _ in range(_MAX_FETCH_REDIRECTS + 1):
        if not _is_public_url(current):
            raise BlockedURLError(f"Refusing to fetch non-public URL: {current}")
        resp = _guarded_session.get(
            current,
            timeout=timeout,
            headers=_FETCH_HEADERS,
            allow_redirects=False,
            stream=True,
        )
        if resp.is_redirect or resp.is_permanent_redirect:
            location = resp.headers.get("Location")
            resp.close()
            if not location:
                return resp
            current = urljoin(current, location)
            continue
        content = b""
        for chunk in resp.iter_content(65536):
            content += chunk
            if len(content) > _MAX_FETCH_BYTES:
                content = content[:_MAX_FETCH_BYTES]
                break
        resp._content = content
        # Present the final URL to callers that build relative links from it.
        resp.url = current
        return resp
    raise BlockedURLError(f"Too many redirects while fetching {url}")


def _read_sitemap_urls(sitemap_url: str) -> list[str]:
    if not sitemap_url:
        return []
    try:
        resp = _http_get(sitemap_url, timeout=20)
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.text)
    except Exception:
        return []

    urls: list[str] = []
    for node in root.findall(".//{*}loc"):
        if node.text:
            normalized = _normalize_url(node.text.strip())
            if normalized:
                urls.append(normalized)
    return urls


def _slug_for_url(url: str) -> str:
    parsed = urlparse(url)
    stem = (parsed.netloc + parsed.path).strip("/").replace("/", "-")
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "-", stem) or "page"
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"{stem[:80]}-{digest}"


def _finding(
    page_url: str,
    rule_id: str,
    severity: str,
    message: str,
    location: str,
    help_url: str = "",
    wcag_tags: Iterable[str] | None = None,
    strict_open_source_only: bool = False,
) -> dict[str, Any]:
    wcag_criteria = _extract_wcag_criteria(wcag_tags or [])
    resources = _build_learning_resources(rule_id, help_url, wcag_criteria, strict_open_source_only=strict_open_source_only)
    return {
        "page_url": page_url,
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
        "location": location,
        "help_url": help_url,
        "wcag_criteria": wcag_criteria,
        "resources": resources,
    }


def _extract_wcag_criteria(tags: Iterable[str]) -> list[str]:
    criteria: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        tag = str(raw).strip().lower()
        if not tag.startswith("wcag"):
            continue
        payload = tag[4:]
        if not payload.isdigit() or len(payload) < 3:
            continue
        criterion = f"{payload[0]}.{payload[1]}.{payload[2:]}"
        criterion = criterion.replace(".0", ".") if criterion.endswith(".0") else criterion
        if criterion not in seen:
            seen.add(criterion)
            criteria.append(criterion)
    return criteria


def _build_learning_resources(
    rule_id: str,
    help_url: str,
    wcag_criteria: list[str],
    *,
    strict_open_source_only: bool = False,
) -> list[dict[str, str]]:
    links: list[tuple[str, str, str]] = []

    if help_url and not strict_open_source_only:
        links.append(("axe-core rule help", help_url, "axe-core"))

    for criterion in wcag_criteria:
        wcag_url = _WCAG_UNDERSTANDING_URLS.get(criterion)
        if wcag_url:
            links.append((f"W3C Understanding SC {criterion}", wcag_url, "W3C"))

    for title, url in _RULE_LEARNING_URLS.get(rule_id, []):
        if strict_open_source_only and "developer.mozilla.org" in url:
            continue
        links.append((title, url, "Open guidance"))

    # Add baseline open references even when a rule has no explicit mapping.
    links.append(("W3C WCAG 2.2 Quick Reference", "https://www.w3.org/WAI/WCAG22/quickref/", "W3C"))
    links.append(("WAI Authoring Practices Guide", "https://www.w3.org/WAI/ARIA/apg/", "W3C"))
    links.append(("A11Y Project Checklist", "https://www.a11yproject.com/checklist/", "A11Y Project"))

    deduped: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for title, url, source in links:
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append({"title": title, "url": url, "source": source})
    return deduped


def _npx_path() -> str | None:
    # Resolve once. A bare "npx" passed to subprocess.run raises
    # FileNotFoundError on Windows, where the launcher is "npx.cmd"; shutil.which
    # finds the real executable (honouring PATHEXT) and we reuse that full path.
    return shutil.which("npx")


def _axe_available() -> bool:
    return _npx_path() is not None


def _run_axe(url: str, output_path: Path) -> None:
    npx = _npx_path()
    if not npx:
        raise RuntimeError("npx executable not found on PATH")
    command = [
        npx,
        "axe",
        url,
        "--tags",
        ",".join(WCAG_TAGS),
        "--save",
        str(output_path),
    ]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
        raise RuntimeError(err)


# Single severity vocabulary shared by axe and heuristic findings, most to
# least severe. Heuristic findings emit these values directly; axe impacts map
# onto them below (critical -> critical, not the old critical -> serious that
# meant no finding was ever "critical").
SEVERITY_LEVELS = ("critical", "serious", "moderate", "minor")


def _severity_for_impact(impact: str) -> str:
    impact = (impact or "").strip().lower()
    if impact in SEVERITY_LEVELS:
        return impact
    return "minor"


def _write_findings_csv(path: Path, findings: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["page_url", "severity", "rule_id", "message", "location", "help_url", "wcag_criteria", "resource_urls"])
        for item in findings:
            resources = item.get("resources") or []
            resource_urls = "; ".join(str(r.get("url", "")) for r in resources if isinstance(r, dict) and r.get("url"))
            writer.writerow(
                [
                    item.get("page_url", ""),
                    item.get("severity", ""),
                    item.get("rule_id", ""),
                    item.get("message", ""),
                    item.get("location", ""),
                    item.get("help_url", ""),
                    ", ".join(item.get("wcag_criteria") or []),
                    resource_urls,
                ]
            )


def _write_log(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_zip(run_dir: Path) -> None:
    zip_path = run_dir / "artifacts.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for child in run_dir.rglob("*"):
            if child == zip_path or not child.is_file():
                continue
            zf.write(child, child.relative_to(run_dir))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback
