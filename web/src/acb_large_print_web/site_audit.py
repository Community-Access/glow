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
    "2.4.10": "https://www.w3.org/WAI/WCAG22/Understanding/section-headings.html",
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
    "HEURISTIC-HEADING-NONE": [
        ("W3C Tutorial: Headings", "https://www.w3.org/WAI/tutorials/page-structure/headings/"),
        ("W3C: Section Headings (SC 2.4.10)", _WCAG_UNDERSTANDING_URLS["2.4.10"]),
    ],
    "HEURISTIC-HEADING-NO-H1": [
        ("W3C Tutorial: Headings", "https://www.w3.org/WAI/tutorials/page-structure/headings/"),
        ("W3C: Info and Relationships (SC 1.3.1)", _WCAG_UNDERSTANDING_URLS["1.3.1"]),
    ],
    "HEURISTIC-HEADING-MULTIPLE-H1": [
        ("W3C Tutorial: Headings", "https://www.w3.org/WAI/tutorials/page-structure/headings/"),
    ],
    "HEURISTIC-HEADING-SKIPPED-LEVEL": [
        ("W3C Tutorial: Headings", "https://www.w3.org/WAI/tutorials/page-structure/headings/"),
        ("W3C: Info and Relationships (SC 1.3.1)", _WCAG_UNDERSTANDING_URLS["1.3.1"]),
    ],
    "HEURISTIC-HEADING-SPARSE": [
        ("W3C: Section Headings (SC 2.4.10)", _WCAG_UNDERSTANDING_URLS["2.4.10"]),
        ("W3C Tutorial: Headings", "https://www.w3.org/WAI/tutorials/page-structure/headings/"),
    ],
    "HEURISTIC-HEADING-EMPTY": [
        ("W3C: Headings and Labels (SC 2.4.6)", _WCAG_UNDERSTANDING_URLS["2.4.6"]),
        ("W3C Tutorial: Headings", "https://www.w3.org/WAI/tutorials/page-structure/headings/"),
    ],
    "HEURISTIC-IMAGE-AS-HEADING": [
        ("W3C Tutorial: Headings", "https://www.w3.org/WAI/tutorials/page-structure/headings/"),
        ("W3C Tutorial: Images of text", "https://www.w3.org/WAI/tutorials/images/textual/"),
    ],
    "HEURISTIC-TITLE-GENERIC": [
        ("W3C: Page Titled (SC 2.4.2)", _WCAG_UNDERSTANDING_URLS["2.4.2"]),
        ("W3C Tutorial: Page titles", "https://www.w3.org/WAI/tutorials/page-structure/title/"),
    ],
    "HEURISTIC-TITLE-DUPLICATE": [
        ("W3C: Page Titled (SC 2.4.2)", _WCAG_UNDERSTANDING_URLS["2.4.2"]),
        ("W3C Tutorial: Page titles", "https://www.w3.org/WAI/tutorials/page-structure/title/"),
    ],
    "HEURISTIC-TITLE-NOT-DESCRIPTIVE": [
        ("W3C: Page Titled (SC 2.4.2)", _WCAG_UNDERSTANDING_URLS["2.4.2"]),
        ("W3C Tutorial: Page titles", "https://www.w3.org/WAI/tutorials/page-structure/title/"),
    ],
}

# Best-practice rules are real usability problems but are not, on their own, a
# WCAG 2.2 AA failure. They are tagged so reports can say so plainly instead of
# leaving a site owner to guess whether they have broken the law.
_BEST_PRACTICE_RULES = frozenset(
    {
        "HEURISTIC-HEADING-NONE",
        "HEURISTIC-HEADING-NO-H1",
        "HEURISTIC-HEADING-MULTIPLE-H1",
        "HEURISTIC-HEADING-SKIPPED-LEVEL",
        "HEURISTIC-HEADING-SPARSE",
        "HEURISTIC-HEADING-EMPTY",
        "HEURISTIC-IMAGE-AS-HEADING",
        "HEURISTIC-TITLE-GENERIC",
        "HEURISTIC-TITLE-DUPLICATE",
        "HEURISTIC-TITLE-NOT-DESCRIPTIVE",
    }
)

# Plain-language "what do I actually do about this?" text. The rule id and the
# WCAG number tell an expert what happened; these tell everyone else.
_RULE_GUIDANCE: dict[str, str] = {
    "HEURISTIC-HTML-LANG": (
        "Screen readers use this to pick the right voice and pronunciation. "
        "Add lang=\"en\" (or the page's language) to the <html> tag."
    ),
    "HEURISTIC-HTML-TITLE": (
        "The title is the first thing a screen reader announces and what shows in "
        "browser tabs and bookmarks. Add a <title> describing this page."
    ),
    "HEURISTIC-IMG-ALT": (
        "Add alt text describing what each image shows. If an image is purely "
        "decorative, give it an empty alt=\"\" so screen readers skip it."
    ),
    "HEURISTIC-LINK-TEXT": (
        "Screen reader users often browse a list of a page's links out of context, "
        "where \"click here\" means nothing. Say where the link goes instead."
    ),
    "HEURISTIC-HEADING-NONE": (
        "Headings are how screen reader and keyboard users jump around a page. "
        "With none, the only way through is to read every line in order. "
        "Mark each section's title as a heading (<h2>, <h3>, and so on)."
    ),
    "HEURISTIC-HEADING-NO-H1": (
        "Every page should start with one <h1> naming what the page is about, "
        "so people know where they have landed."
    ),
    "HEURISTIC-HEADING-MULTIPLE-H1": (
        "Use a single <h1> for the page's main title and <h2> for the sections "
        "under it, so the page has one clear top level."
    ),
    "HEURISTIC-HEADING-SKIPPED-LEVEL": (
        "Heading levels should step down one at a time (h1, then h2, then h3). "
        "A skipped level makes the page outline sound like content is missing."
    ),
    "HEURISTIC-HEADING-SPARSE": (
        "This page has a lot of content but almost no headings, so there is no "
        "way to skim or skip ahead. Add an <h2> at the start of each section."
    ),
    "HEURISTIC-HEADING-EMPTY": (
        "This heading announces nothing. If it is an image, give the image alt "
        "text; otherwise put the section's name inside the heading tag."
    ),
    "HEURISTIC-IMAGE-AS-HEADING": (
        "Graphics appear to be doing the visual job of section headings. A sighted "
        "visitor sees the structure, but a screen reader user gets no headings to "
        "navigate by. Put a real heading tag beside or behind each of these images."
    ),
    "HEURISTIC-TITLE-GENERIC": (
        "The title does not say which page this is. Lead with the page's own "
        "subject, then the site name, for example \"Projects | Stow Lions Club\"."
    ),
    "HEURISTIC-TITLE-DUPLICATE": (
        "Several pages share this exact title, so tabs, bookmarks, history, and "
        "search results cannot be told apart. Give each page its own title."
    ),
    "HEURISTIC-TITLE-NOT-DESCRIPTIVE": (
        "The title does not match what the page is actually about. Make it "
        "describe this page's content, not just the site."
    ),
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
    # Best-practice checks. These are not WCAG failures on their own, so they
    # are reported separately from conformance findings and can be switched
    # off by anyone who only wants pass/fail conformance results.
    check_heading_structure: bool = True
    check_title_quality: bool = True


@dataclass(slots=True)
class _Heading:
    """One heading found on the page, with the text a screen reader announces."""

    level: int
    text: str
    # True when the heading's only content was an image, so its announced text
    # comes entirely from that image's alt attribute (empty alt = silent heading).
    image_only: bool


# Content-bearing tags whose text counts toward the page's word total. Used to
# tell a real content page (which needs section headings) apart from a stub.
_BLOCK_TEXT_TAGS = frozenset({"p", "li", "td", "th", "dd", "dt", "figcaption", "blockquote"})

_HEADING_TAGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})


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
        # Heading structure and content-volume signals for the best-practice checks.
        self.headings: list[_Heading] = []
        self.img_with_alt_text: list[str] = []
        self.word_count = 0
        self._heading_level = 0
        self._heading_parts: list[str] = []
        self._heading_had_img_alt: list[str] = []
        # The tag that opened the current heading, plus how deep the same tag
        # name is nested inside it, so the heading closes on its own end tag
        # rather than on the first nested one.
        self._heading_tag = ""
        self._heading_nest = 0
        self._block_depth = 0
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._heading_level and tag == self._heading_tag:
            self._heading_nest += 1
        if tag == "html":
            self.doc_lang = (attrs_map.get("lang") or "").strip()
        elif tag == "title":
            self._in_title = True
            self._title_parts = []
        elif tag == "img":
            if "alt" not in attrs_map:
                self.img_missing_alt += 1
            else:
                alt = (attrs_map.get("alt") or "").strip()
                if alt:
                    self.img_with_alt_text.append(alt)
                if self._heading_level:
                    self._heading_had_img_alt.append(alt)
        elif tag == "a":
            self._current_anchor_href = (attrs_map.get("href") or "").strip()
            self._current_anchor_text = []
        elif tag in _HEADING_TAGS:
            self._start_heading(int(tag[1]), tag)
        elif attrs_map.get("role", "").strip().lower() == "heading":
            # ARIA headings announce exactly like native ones, so an outline
            # built only from h1-h6 would misreport a page that uses them.
            try:
                level = int((attrs_map.get("aria-level") or "2").strip())
            except ValueError:
                level = 2
            self._start_heading(max(1, min(6, level)), tag)
        elif tag in _BLOCK_TEXT_TAGS:
            self._block_depth += 1

    def _start_heading(self, level: int, tag: str) -> None:
        self._heading_level = level
        self._heading_tag = tag
        self._heading_nest = 0
        self._heading_parts = []
        self._heading_had_img_alt = []

    def _end_heading(self) -> None:
        if not self._heading_level:
            return
        own_text = " ".join(p.strip() for p in self._heading_parts if p.strip()).strip()
        image_only = not own_text and bool(self._heading_had_img_alt)
        text = own_text or " ".join(a for a in self._heading_had_img_alt if a).strip()
        self.headings.append(_Heading(level=self._heading_level, text=text, image_only=image_only))
        self._heading_level = 0
        self._heading_tag = ""
        self._heading_nest = 0
        self._heading_parts = []
        self._heading_had_img_alt = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
            return
        if self._heading_level:
            self._heading_parts.append(data)
            if data.strip():
                self._heading_had_own_text = True
        elif self._block_depth:
            self.word_count += len(data.split())
        if self._current_anchor_href:
            self._current_anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        # A heading ends only on its own tag, never on a nested one. Closing on
        # any end tag truncated headings like <h2><span class="icon"></span>Projects</h2>
        # and reported them as announcing no text.
        if self._heading_level and tag == self._heading_tag:
            if self._heading_nest:
                self._heading_nest -= 1
            else:
                self._end_heading()
            return
        if tag == "title":
            self._in_title = False
            self.title = "".join(self._title_parts).strip()
        elif tag == "a" and self._current_anchor_href:
            anchor_text = " ".join(p.strip() for p in self._current_anchor_text if p.strip()).strip()
            self.links.append((self._current_anchor_href, anchor_text))
            self._current_anchor_href = ""
            self._current_anchor_text = []
        elif tag in _BLOCK_TEXT_TAGS:
            self._block_depth = max(0, self._block_depth - 1)

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
        self._end_heading()


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
            check_heading_structure=options.check_heading_structure,
            check_title_quality=options.check_title_quality,
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

    # Duplicate titles can only be seen across the run, so this runs once all
    # pages are in. It appends to each affected page's findings.
    if options.check_title_quality:
        duplicate_findings = _duplicate_title_findings(
            pages, strict_open_source_only=options.strict_open_source_only
        )
        all_findings.extend(duplicate_findings)
        for page in pages:
            page_json = run_dir / "pages" / _slug_for_url(str(page.get("url") or "")) / "page.json"
            if page_json.parent.exists():
                _write_json(page_json, page)

    notices = _build_run_notices(pages)
    for notice in notices:
        log_lines.append(f"notice: {notice['title']} - {notice['message']}")

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
            "check_heading_structure": options.check_heading_structure,
            "check_title_quality": options.check_title_quality,
        },
        "totals": {
            **totals,
            "findings": len(all_findings),
            "pages_total": len(scan_urls),
        },
        "cancelled": cancelled,
        "notices": notices,
        "wcag_rollup": dict(sorted(wcag_rollup.items())),
        "pages": pages,
    }

    _write_json(run_dir / "summary.json", summary)
    _write_findings_csv(run_dir / "findings.csv", all_findings)
    _write_log(run_dir / "session.log", log_lines)
    _write_zip(run_dir)
    return summary


def _build_run_notices(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run-level status messages about the scan itself, not about the pages.

    The deep scanner failing is one event, however many pages it affected. It is
    reported once, in plain language, with the raw error tucked away for whoever
    maintains the server.
    """
    # Only pages that actually carry a deep-scan record can be counted. A run
    # that reuses cached pages has results without one, and including those in
    # the denominator produced counts like "2 of 0 pages".
    attempted = [p for p in pages if isinstance(p.get("deep_scan"), dict)]
    failed = [p for p in attempted if not p["deep_scan"].get("ok")]
    if not failed:
        return []

    first = failed[0]["deep_scan"]
    if len(failed) == 1:
        scope = "1 page in this scan"
    elif len(failed) == len(attempted):
        scope = f"all {len(failed)} pages in this scan"
    else:
        scope = f"{len(failed)} of {len(attempted)} pages in this scan"

    return [
        {
            "id": "deep-scan-unavailable",
            "level": "warning",
            "title": "Some automated checks could not run",
            "message": f"{first.get('message', _SCANNER_FALLBACK_MESSAGE)} This affected {scope}.",
            "consequence": _SCANNER_CONSEQUENCE,
            "detail": first.get("detail", ""),
            "affected_pages": len(failed),
        }
    ]


def _scan_single_page(
    url: str,
    page_dir: Path,
    *,
    strict_open_source_only: bool = False,
    check_heading_structure: bool = True,
    check_title_quality: bool = True,
) -> dict[str, Any]:
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

    if check_heading_structure:
        findings.extend(
            _heading_findings(url, parser, strict_open_source_only=strict_open_source_only)
        )
    if check_title_quality:
        findings.extend(
            _title_findings(url, parser, strict_open_source_only=strict_open_source_only)
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
    else:
        axe_error = "The deep scanner is not installed on this server."

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
    # A scanner outage is a problem with GLOW, not with the page being scanned.
    # Reporting it as a per-page "finding" put an unreadable npm stack trace in
    # every site owner's results and made it look like their own defect, so it
    # is carried as run-level status and summarised once instead.
    if axe_data:
        axe_status = {"ok": True}
    else:
        axe_status = {
            "ok": False,
            "message": _friendly_scanner_message(axe_error or ""),
            "detail": _shorten_detail(axe_error or ""),
        }

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
        "deep_scan": axe_status,
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
        # Plain-language remediation advice, and whether this is a hard WCAG
        # failure or a best practice, so reports never leave a non-specialist
        # guessing what a rule id means or how much it matters.
        "guidance": _RULE_GUIDANCE.get(rule_id, ""),
        "best_practice": rule_id in _BEST_PRACTICE_RULES,
    }


# A page with at least this much prose is treated as a real content page, so
# "almost no headings" is a navigation problem rather than a short stub page.
_SPARSE_HEADING_WORD_FLOOR = 250
# Roughly how much content one heading can reasonably cover. A flat count is the
# wrong test: the reported page had two headings across ~960 words and was still
# impossible to navigate, so the expectation scales with content instead.
_WORDS_PER_HEADING = 300
# Never demand more than this many, so a long single-topic article is not buried
# in requests to chop it up.
_MAX_EXPECTED_HEADINGS = 6
# Enough alt-bearing graphics to suggest they are carrying the page's structure.
_IMAGE_AS_HEADING_FLOOR = 3


def _expected_heading_count(word_count: int) -> int:
    """How many headings a page this size needs to stay navigable."""
    if word_count < _SPARSE_HEADING_WORD_FLOOR:
        return 0
    scaled = -(-word_count // _WORDS_PER_HEADING)  # ceiling division
    return max(2, min(_MAX_EXPECTED_HEADINGS, scaled))

_GENERIC_TITLES = frozenset(
    {
        "",
        "home",
        "home page",
        "homepage",
        "index",
        "untitled",
        "untitled document",
        "untitled page",
        "new page",
        "welcome",
        "page",
        "default",
        "document",
        "main",
        "main page",
        "web page",
        "website",
    }
)

# Words too common to prove a title actually describes the page.
_TITLE_STOPWORDS = frozenset(
    {
        "a", "an", "and", "at", "by", "for", "from", "in", "of", "on", "or",
        "our", "the", "to", "with", "page", "home", "site", "website", "welcome",
        "official", "www", "com", "org", "net", "html", "htm", "php", "index",
    }
)


def _title_keywords(text: str) -> set[str]:
    """Significant lowercase words in a title, heading, or URL slug."""
    words = re.split(r"[^a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in _TITLE_STOPWORDS}


def _heading_findings(
    url: str,
    parser: _PageParser,
    *,
    strict_open_source_only: bool = False,
) -> list[dict[str, Any]]:
    """Best-practice checks on the page's heading outline.

    Headings are how screen reader users navigate; a page can pass every
    automated WCAG check and still be unusable because it has none. These are
    reported as best practice, not as conformance failures.
    """
    findings: list[dict[str, Any]] = []
    headings = parser.headings
    levels = [h.level for h in headings]
    h1_count = levels.count(1)
    expected = _expected_heading_count(parser.word_count)

    def add(rule_id: str, severity: str, message: str, location: str, wcag_tags: list[str]) -> None:
        findings.append(
            _finding(
                url,
                rule_id,
                severity,
                message,
                location,
                wcag_tags=wcag_tags,
                strict_open_source_only=strict_open_source_only,
            )
        )

    if not headings:
        add(
            "HEURISTIC-HEADING-NONE",
            "serious",
            "This page has no headings at all, so there is no way to skim it or jump between sections.",
            "body",
            ["wcag131"],
        )
    else:
        if h1_count == 0:
            add(
                "HEURISTIC-HEADING-NO-H1",
                "moderate",
                "This page has headings but no top-level heading (h1) naming what the page is about.",
                "body",
                ["wcag131"],
            )
        elif h1_count > 1:
            add(
                "HEURISTIC-HEADING-MULTIPLE-H1",
                "minor",
                f"This page has {h1_count} top-level headings (h1). A page normally has one.",
                "h1",
                ["wcag131"],
            )

        # Level jumps: h1 -> h3 sounds to a screen reader user like a section
        # was skipped. Only downward jumps matter; coming back up is normal.
        previous = levels[0]
        for level in levels[1:]:
            if level > previous + 1:
                add(
                    "HEURISTIC-HEADING-SKIPPED-LEVEL",
                    "moderate",
                    f"Heading levels jump from h{previous} to h{level}, skipping a level in the page outline.",
                    f"h{level}",
                    ["wcag131"],
                )
                break
            previous = level

        empty_headings = sum(1 for h in headings if not h.text.strip())
        if empty_headings:
            add(
                "HEURISTIC-HEADING-EMPTY",
                "serious",
                f"Detected {empty_headings} heading(s) that announce no text, so they are silent to a screen reader.",
                "h1, h2, h3, h4, h5, h6",
                ["wcag246"],
            )

        # A page with substantial content but hardly any headings: the reported
        # case was one h1 plus a stray subheading across ~960 words.
        if expected and len(headings) < expected:
            add(
                "HEURISTIC-HEADING-SPARSE",
                "moderate",
                (
                    f"This page has roughly {parser.word_count} words of content but only "
                    f"{len(headings)} heading(s). A page this size normally needs at least "
                    f"{expected} to be skimmed or navigated by section."
                ),
                "body",
                ["wcag2410"],
            )

    # Graphics standing in for section headings: several meaningful images, a
    # substantial page, and too little heading structure to go with them.
    if (
        len(parser.img_with_alt_text) >= _IMAGE_AS_HEADING_FLOOR
        and expected
        and len(headings) < expected
    ):
        add(
            "HEURISTIC-IMAGE-AS-HEADING",
            "moderate",
            (
                f"Detected {len(parser.img_with_alt_text)} content images but only {len(headings)} heading(s). "
                "Graphics may be doing the visual job of section headings, which gives screen "
                "reader users nothing to navigate by."
            ),
            "img",
            ["wcag131"],
        )

    return findings


def _title_findings(
    url: str,
    parser: _PageParser,
    *,
    strict_open_source_only: bool = False,
) -> list[dict[str, Any]]:
    """Best-practice checks on whether the title actually describes the page.

    A present-but-useless title passes the WCAG 2.4.2 automated check while
    still leaving tabs, bookmarks, and history entries indistinguishable.
    """
    title = (parser.title or "").strip()
    if not title:
        # Already reported as a conformance failure by HEURISTIC-HTML-TITLE.
        return []

    findings: list[dict[str, Any]] = []
    normalized = re.sub(r"\s+", " ", title).strip().lower()

    if normalized in _GENERIC_TITLES:
        findings.append(
            _finding(
                url,
                "HEURISTIC-TITLE-GENERIC",
                "moderate",
                f'The page title "{title}" does not say which page this is.',
                "head > title",
                wcag_tags=["wcag242"],
                strict_open_source_only=strict_open_source_only,
            )
        )
        return findings

    # Does the title share any significant word with the page's own h1 or with
    # the URL slug? If not, it is almost certainly the site name on every page.
    title_words = _title_keywords(title)
    if not title_words:
        return findings

    h1_text = next((h.text for h in parser.headings if h.level == 1 and h.text.strip()), "")
    slug = urlparse(url).path.rsplit("/", 1)[-1]
    slug_words = _title_keywords(slug.rsplit(".", 1)[0])
    heading_words = _title_keywords(h1_text) | slug_words

    # With nothing to compare against we cannot judge the title; stay quiet
    # rather than guess.
    if heading_words and not (title_words & heading_words):
        subject = f'the page heading "{h1_text}"' if h1_text.strip() else "this page's address"
        findings.append(
            _finding(
                url,
                "HEURISTIC-TITLE-NOT-DESCRIPTIVE",
                "minor",
                f'The page title "{title}" shares no wording with {subject}, so it may not describe this page.',
                "head > title",
                wcag_tags=["wcag242"],
                strict_open_source_only=strict_open_source_only,
            )
        )

    return findings


def _duplicate_title_findings(
    pages: list[dict[str, Any]],
    *,
    strict_open_source_only: bool = False,
) -> list[dict[str, Any]]:
    """Flag pages in this run that share one title. Cross-page by nature."""
    by_title: dict[str, list[dict[str, Any]]] = {}
    for page in pages:
        if page.get("result") not in {"ok", "skipped"}:
            continue
        title = re.sub(r"\s+", " ", str(page.get("title") or "")).strip()
        if not title:
            continue
        by_title.setdefault(title.lower(), []).append(page)

    findings: list[dict[str, Any]] = []
    for group in by_title.values():
        if len(group) < 2:
            continue
        title = str(group[0].get("title") or "").strip()
        for page in group:
            finding = _finding(
                str(page.get("url") or ""),
                "HEURISTIC-TITLE-DUPLICATE",
                "moderate",
                f'{len(group)} pages in this scan share the title "{title}", so they cannot be told apart.',
                "head > title",
                wcag_tags=["wcag242"],
                strict_open_source_only=strict_open_source_only,
            )
            page.setdefault("findings", []).append(finding)
            page["finding_count"] = len(page["findings"])
            findings.append(finding)
    return findings


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


# Raw scanner failures are npm/Selenium stack traces. Site owners are not the
# audience for those, so each known failure shape gets a sentence that says what
# happened, whose problem it is, and what it means for their results.
_SCANNER_MESSAGE_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "eacces",
        "The deep scanner could not start because of a file-permission problem on the "
        "GLOW server. Nothing is wrong with your page.",
    ),
    (
        "enoent",
        "The deep scanner is not installed on the GLOW server. Nothing is wrong with your page.",
    ),
    (
        "chromedriver",
        "The deep scanner's browser could not start on the GLOW server. Nothing is wrong "
        "with your page.",
    ),
    (
        "session not created",
        "The deep scanner's browser could not start on the GLOW server. Nothing is wrong "
        "with your page.",
    ),
    (
        "timed out",
        "The deep scan took too long on this page and was stopped. Very large or slow "
        "pages can hit this limit.",
    ),
    (
        "timeout",
        "The deep scan took too long on this page and was stopped. Very large or slow "
        "pages can hit this limit.",
    ),
    (
        "network",
        "The deep scanner could not reach the page from the GLOW server.",
    ),
    (
        "not installed",
        "The deep scanner is not installed on the GLOW server. Nothing is wrong with your page.",
    ),
)

_SCANNER_FALLBACK_MESSAGE = (
    "The deep scanner could not run on the GLOW server. Nothing is wrong with your page."
)

_SCANNER_CONSEQUENCE = (
    "The checks listed below still ran, but this scan did not include the deeper "
    "automated tests (colour contrast, form labels, ARIA, and similar). Re-run the "
    "scan later, or report this to the GLOW administrator if it keeps happening."
)


def _friendly_scanner_message(raw_error: str) -> str:
    """Turn a raw scanner failure into a sentence a site owner can act on."""
    lowered = (raw_error or "").lower()
    for needle, message in _SCANNER_MESSAGE_PATTERNS:
        if needle in lowered:
            return message
    return _SCANNER_FALLBACK_MESSAGE


def _shorten_detail(raw_error: str, limit: int = 400) -> str:
    """Collapse a multi-line stack trace into one line for the details pane."""
    collapsed = re.sub(r"\s+", " ", (raw_error or "").strip())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def _npx_path() -> str | None:
    # Resolve once. A bare "npx" passed to subprocess.run raises
    # FileNotFoundError on Windows, where the launcher is "npx.cmd"; shutil.which
    # finds the real executable (honouring PATHEXT) and we reuse that full path.
    return shutil.which("npx")


def _axe_path() -> str | None:
    """Path to a directly installed axe CLI, if the image has one.

    Preferred over `npx axe`: npx downloads the package on first use, which
    needs both a writable npm cache and outbound registry access at scan time.
    In the container neither is guaranteed, and the download failure surfaced as
    an npm EACCES trace on every scanned page.
    """
    return shutil.which("axe")


def _axe_available() -> bool:
    return _axe_path() is not None or _npx_path() is not None


def _run_axe(url: str, output_path: Path) -> None:
    axe_bin = _axe_path()
    if axe_bin:
        command = [axe_bin]
    else:
        npx = _npx_path()
        if not npx:
            raise RuntimeError("axe executable not found on PATH")
        command = [npx, "axe"]

    # --save takes a bare filename resolved against --dir, NOT a path. Passing
    # an absolute path made axe resolve it against its working directory
    # (/app/instance/... became /app/app/instance/...), fail to write, and still
    # exit 0 -- so no results were ever saved and every page looked unscanned.
    command += [
        url,
        "--tags",
        ",".join(WCAG_TAGS),
        "--dir",
        str(output_path.parent),
        "--save",
        output_path.name,
    ]
    # Chrome cannot use its sandbox inside an unprivileged container, and the
    # default /dev/shm is too small there; without these it exits before axe
    # ever runs.
    chrome_options = "no-sandbox,disable-dev-shm-usage,disable-gpu"
    command += [f"--chrome-options={chrome_options}"]
    chromedriver = shutil.which("chromedriver")
    if chromedriver:
        command += ["--chromedriver-path", chromedriver]

    proc = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
        raise RuntimeError(err)
    # axe reports a failed write on stdout and still exits 0. Without this check
    # the missing file is indistinguishable from "the scanner never ran", which
    # is how a silent save failure would be misreported to a site owner.
    if not output_path.exists():
        combined = f"{proc.stdout}\n{proc.stderr}".strip()
        marker = "Unable to save file!"
        detail = combined[combined.find(marker):].strip() if marker in combined else combined[-300:]
        raise RuntimeError(f"axe ran but saved no results to {output_path}. {detail}".strip())


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
        writer.writerow(
            [
                "page_url",
                "severity",
                "category",
                "rule_id",
                "message",
                "what_to_do",
                "location",
                "help_url",
                "wcag_criteria",
                "resource_urls",
            ]
        )
        for item in findings:
            resources = item.get("resources") or []
            resource_urls = "; ".join(str(r.get("url", "")) for r in resources if isinstance(r, dict) and r.get("url"))
            writer.writerow(
                [
                    item.get("page_url", ""),
                    item.get("severity", ""),
                    # Spelled out rather than a bare True/False, so a spreadsheet
                    # reader can tell a legal requirement from a recommendation.
                    "Best practice" if item.get("best_practice") else "WCAG conformance",
                    item.get("rule_id", ""),
                    item.get("message", ""),
                    item.get("guidance", ""),
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
