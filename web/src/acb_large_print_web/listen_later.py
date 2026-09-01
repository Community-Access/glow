"""Listen Later article extraction helpers.

This module fetches article pages, extracts the readable story text, and
follows simple next-page pagination links when present.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from lxml import html as lxml_html

from .site_audit import _is_public_url

try:
    from trafilatura import extract as _extract_main_text
    from trafilatura import extract_metadata as _extract_metadata
except Exception:  # pragma: no cover - handled at runtime if dependency is absent
    _extract_main_text = None
    _extract_metadata = None


class ArticleExtractionError(Exception):
    """Raised when article extraction fails."""


class BlockedURLError(ArticleExtractionError):
    """Raised when a target URL is not public (SSRF guard).

    Subclasses ArticleExtractionError so the page-flow route already renders it
    as a clean user-facing message instead of a 500.
    """


_FETCH_HEADERS = {"User-Agent": "GLOW-Listen-Later/1.0"}
_MAX_FETCH_REDIRECTS = 5


@dataclass(slots=True)
class ExtractedArticle:
    """Normalized article content ready for display or narration."""

    source_url: str
    final_url: str
    title: str
    text: str
    page_urls: list[str]


def normalize_url(value: str) -> str:
    """Return a canonical http(s) URL or an empty string if invalid."""
    value = (value or "").strip()
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return parsed.geturl()


def extract_article(url: str, *, max_pages: int = 5, follow_pagination: bool = True) -> ExtractedArticle:
    """Fetch and extract the readable text from an article URL.

    When pagination links are present, this follows a small chain of related
    pages and merges the extracted text into a single article body.
    """
    start_url = normalize_url(url)
    if not start_url:
        raise ArticleExtractionError("Please enter a valid article URL.")

    # SSRF gate: only fetch public http(s) hosts. Blocks loopback, private,
    # link-local, reserved, multicast and unspecified addresses and non-web
    # ports so a submitter can't read internal services (e.g. cloud metadata
    # at http://169.254.169.254/ or http://localhost/).
    if not _is_public_url(start_url):
        raise BlockedURLError("That URL can't be fetched. Enter a public web (http/https) article address.")

    if _extract_main_text is None or _extract_metadata is None:
        raise ArticleExtractionError("Article extraction requires the trafilatura package.")

    page_urls: list[str] = []
    page_texts: list[str] = []
    title = ""
    seen: set[str] = set()
    current_url = start_url

    for _ in range(max(1, int(max_pages))):
        if current_url in seen:
            break
        seen.add(current_url)

        html, fetched_url = _fetch_html(current_url)
        page_urls.append(fetched_url)

        if not title:
            title = _extract_title(html)

        text = _extract_page_text(html, fetched_url)
        if text:
            page_texts.append(text)
        elif not page_texts:
            raise ArticleExtractionError("Could not extract readable article text from this page.")

        if not follow_pagination:
            break

        next_url = _discover_next_page_url(html, fetched_url)
        if not next_url or next_url in seen:
            break
        current_url = next_url

    merged = _merge_page_texts(page_texts)
    if not merged.strip():
        raise ArticleExtractionError("Could not extract readable article text from this page.")

    if not title:
        title = "Article"

    return ExtractedArticle(
        source_url=start_url,
        final_url=page_urls[-1] if page_urls else start_url,
        title=title,
        text=merged,
        page_urls=page_urls,
    )


def _fetch_html(url: str) -> tuple[str, str]:
    """SSRF-guarded fetch.

    Redirects are followed manually so the public-address gate is re-checked on
    every hop; otherwise an allowed host could 302 to an internal one and escape
    the gate (mirrors site_audit._http_get).
    """
    current = url
    for _ in range(_MAX_FETCH_REDIRECTS + 1):
        if not _is_public_url(current):
            raise BlockedURLError(f"Refusing to fetch non-public URL: {current}")
        response = requests.get(
            current,
            timeout=20,
            headers=_FETCH_HEADERS,
            allow_redirects=False,
        )
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            if not location:
                response.raise_for_status()
                return response.text or "", response.url or current
            current = urljoin(current, location)
            continue
        response.raise_for_status()
        return response.text or "", response.url or current
    raise BlockedURLError(f"Too many redirects while fetching {url}")


def _extract_title(html: str) -> str:
    if _extract_metadata is None:
        return ""
    try:
        metadata = _extract_metadata(html)
    except Exception:
        return ""
    if metadata is None:
        return ""
    title = getattr(metadata, "title", "") or ""
    return str(title).strip()


def _extract_page_text(html: str, url: str) -> str:
    if _extract_main_text is None:
        return ""

    # Prefer markdown output so heading/list structure survives extraction.
    # If the installed trafilatura version doesn't support these options,
    # fall back to the legacy plain-text call.
    try:
        text = _extract_main_text(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            include_formatting=True,
            output_format="markdown",
            favor_precision=False,
        )
    except TypeError:
        text = _extract_main_text(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
    except Exception as exc:
        raise ArticleExtractionError(f"Could not extract readable article text: {exc}") from exc

    cleaned = _remove_extraction_noise(_normalize_text(text or ""))

    # JS-heavy sites (Next.js) often render useful content in __NEXT_DATA__.
    # Prefer structured payload extraction when text is empty or appears to be
    # mostly script/config dump noise.
    if cleaned and not _looks_like_script_dump(cleaned):
        return cleaned

    payload_text = _extract_nextjs_payload_text(html, url)
    if payload_text:
        return payload_text

    browser_text = _extract_browser_rendered_text(url, html=html)
    if browser_text:
        return browser_text

    return cleaned


def _discover_next_page_url(html: str, base_url: str) -> str:
    try:
        tree = lxml_html.fromstring(html)
    except Exception:
        return ""

    candidates: list[str] = []
    candidates.extend(tree.xpath('//link[@rel="next"]/@href'))
    candidates.extend(tree.xpath('//a[@rel="next"]/@href'))

    for anchor in tree.xpath("//a[@href]"):
        href = anchor.get("href") or ""
        label = " ".join(anchor.itertext())
        label = " ".join(
            part for part in [label, anchor.get("aria-label") or "", anchor.get("title") or ""] if part
        ).strip().lower()
        if not label:
            continue
        if re.search(r"\bnext\b|\bcontinue\b|\bmore\b|\bolder\b|\bpage\s*2\b|[»›>]+", label):
            candidates.append(href)

    base_host = (urlparse(base_url).hostname or "").lower()
    for href in candidates:
        next_url = normalize_url(urljoin(base_url, href))
        if not next_url:
            continue
        next_host = (urlparse(next_url).hostname or "").lower()
        if next_host and base_host and next_host == base_host:
            return next_url

    payload_next = _discover_next_page_url_from_payload(html, base_url)
    if payload_next:
        return payload_next

    browser_next = _discover_next_page_url_from_browser(base_url, html=html)
    if browser_next:
        return browser_next

    return ""


def _merge_page_texts(page_texts: list[str]) -> str:
    blocks: list[str] = []
    seen_blocks: set[str] = set()

    for page_text in page_texts:
        for block in re.split(r"\n{2,}", page_text.strip()):
            normalized = _normalize_text(block)
            if not normalized:
                continue
            key = " ".join(normalized.split()).lower()
            if key in seen_blocks:
                continue
            seen_blocks.add(key)
            blocks.append(normalized)

    return "\n\n".join(blocks).strip()


def _normalize_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    cleaned: list[str] = []
    blank = False

    for line in lines:
        if not line:
            if cleaned and not blank:
                cleaned.append("")
            blank = True
            continue
        cleaned.append(line)
        blank = False

    return "\n".join(cleaned).strip()


def _remove_extraction_noise(text: str) -> str:
    """Drop common pagination/navigation artifacts from extracted text."""
    if not text:
        return ""

    drop_patterns = [
        r"^page:\s*",
        r"^next\s*(page|→|>|»)?\s*$",
        r"^previous\s*(page|←|<|«)?\s*$",
        r"^table of contents\s*$",
        r"^additional links\s*$",
        r"^supported by\s*$",
        r"^exclusive extras\s*$",
    ]
    compiled = [re.compile(p, re.IGNORECASE) for p in drop_patterns]

    kept: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and any(rx.match(stripped) for rx in compiled):
            continue
        kept.append(line)

    return _normalize_text("\n".join(kept))


def _looks_like_script_dump(text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if "__next_data__" in lowered or '"props"' in lowered and '"pageprops"' in lowered:
        return True
    brace_count = text.count("{") + text.count("}")
    return brace_count > 80 and len(text) > 1200


def _extract_nextjs_payload_text(html: str, source_url: str) -> str:
    """Extract readable text from a Next.js __NEXT_DATA__ payload."""
    match = re.search(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""

    raw_json = (match.group(1) or "").strip()
    if not raw_json:
        return ""

    try:
        data = json.loads(raw_json)
    except Exception:
        return ""

    page_props = ((data.get("props") or {}).get("pageProps") or {})
    title = str(page_props.get("title") or "").strip()
    collection = page_props.get("collection")
    if isinstance(collection, dict):
        return _render_nextjs_collection_text(source_url, title, collection)

    generic = _render_nextjs_generic_text(source_url, title, page_props)
    return generic


def _render_nextjs_collection_text(source_url: str, title: str, collection: dict) -> str:
    heading = title or str(collection.get("DisplayName") or collection.get("ProductCollectionName") or "Collection").strip() or "Collection"
    lines: list[str] = [f"# {heading}", f"Source: {source_url}"]

    display_name = str(collection.get("DisplayName") or "").strip()
    collection_name = str(collection.get("ProductCollectionName") or "").strip()
    description = str(collection.get("Description") or "").strip()
    if display_name:
        lines.append(f"Display name: {display_name}")
    if collection_name and collection_name != display_name:
        lines.append(f"Collection name: {collection_name}")
    if description:
        lines.append("")
        lines.append(description)

    items = collection.get("ProductCollectionItems") or []
    if isinstance(items, list):
        lines.append("")
        lines.append(f"Total listed items: {len(items)}")
        lines.append("Sample items:")
        sample_count = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            product_id = item.get("ExtProductId")
            item_name = str(
                item.get("DisplayName")
                or item.get("ProductCollectionName")
                or item.get("Name")
                or ""
            ).strip()
            if not product_id and not item_name:
                continue
            if product_id and item_name:
                lines.append(f"- {item_name} ({product_id})")
            elif item_name:
                lines.append(f"- {item_name}")
            else:
                lines.append(f"- {product_id}")
            sample_count += 1
            if sample_count >= 40:
                break

    return _normalize_text("\n".join(lines))


def _render_nextjs_generic_text(source_url: str, title: str, page_props: dict) -> str:
    lines: list[str] = []
    if title:
        lines.append(f"# {title}")
    lines.append(f"Source: {source_url}")

    snippets: list[str] = []
    _collect_nextjs_strings(page_props, snippets, depth=0)
    for snippet in snippets[:80]:
        lines.append("")
        lines.append(snippet)

    return _normalize_text("\n".join(lines))


def _collect_nextjs_strings(node: Any, out: list[str], *, depth: int) -> None:
    if depth > 6 or len(out) >= 200:
        return

    if isinstance(node, str):
        text = _normalize_text(node)
        if len(text) >= 30 and not _looks_like_jsonish_text(text):
            out.append(text)
        return

    if isinstance(node, list):
        for item in node:
            _collect_nextjs_strings(item, out, depth=depth + 1)
        return

    if not isinstance(node, dict):
        return

    skip_keys = {
        "_nextI18Next",
        "appConfig",
        "cookies",
        "nonce",
        "scriptLoader",
        "buildId",
        "query",
    }
    for key, value in node.items():
        if key in skip_keys:
            continue
        if isinstance(value, str) and key.lower() in {"title", "description", "headline", "summary", "text", "body"}:
            text = _normalize_text(value)
            if text and not _looks_like_jsonish_text(text):
                out.append(text)
            continue
        _collect_nextjs_strings(value, out, depth=depth + 1)


def _looks_like_jsonish_text(text: str) -> bool:
    lowered = text.lower()
    if "{\"" in text or "\"props\"" in text or "\"pageprops\"" in text:
        return True
    if lowered.startswith("http") and len(text) > 140:
        return True
    return False


def _discover_next_page_url_from_payload(html: str, base_url: str) -> str:
    """Try to infer next-page URLs from embedded app-state JSON payloads."""
    raw_json = _extract_next_data_json(html)
    if not raw_json:
        return ""

    try:
        payload = json.loads(raw_json)
    except Exception:
        return ""

    base_host = (urlparse(base_url).hostname or "").lower()
    candidates: list[str] = []
    _collect_payload_next_url_candidates(payload, candidates)

    for candidate in candidates:
        next_url = normalize_url(urljoin(base_url, candidate))
        if not next_url:
            continue
        next_host = (urlparse(next_url).hostname or "").lower()
        if next_host and base_host and next_host == base_host and next_url != base_url:
            return next_url

    return ""


def _extract_next_data_json(html: str) -> str:
    match = re.search(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""
    return (match.group(1) or "").strip()


def _collect_payload_next_url_candidates(node: Any, out: list[str], *, depth: int = 0) -> None:
    if depth > 8 or len(out) >= 200:
        return

    if isinstance(node, str):
        value = node.strip()
        lowered = value.lower()
        if value and (
            "/" in value
            and (
                "page=" in lowered
                or "/page/" in lowered
                or lowered.endswith("/2")
                or lowered.endswith("/2/")
                or "next" in lowered
            )
        ):
            out.append(value)
        return

    if isinstance(node, list):
        for item in node:
            _collect_payload_next_url_candidates(item, out, depth=depth + 1)
        return

    if not isinstance(node, dict):
        return

    for key, value in node.items():
        key_lower = str(key).lower()
        if isinstance(value, str):
            if key_lower in {"next", "nexturl", "next_url", "href", "url", "pathname", "path"}:
                out.append(value)
            elif "next" in key_lower and ("url" in key_lower or "path" in key_lower or "href" in key_lower):
                out.append(value)
        _collect_payload_next_url_candidates(value, out, depth=depth + 1)


def _browser_adapter_mode() -> str:
    """Return adapter mode: '0' (off), '1' (force), or 'auto' (default)."""
    return (os.environ.get("GLOW_PAGEFLOW_BROWSER_ADAPTER", "auto") or "auto").strip().lower()


def _browser_adapter_enabled_for_html(html: str) -> bool:
    mode = _browser_adapter_mode()
    if mode in {"0", "false", "off", "disabled"}:
        return False
    if mode in {"1", "true", "on", "enabled", "force"}:
        return True
    # Default 'auto' mode: only for JS-heavy pages.
    return _looks_js_heavy_page_html(html)


@lru_cache(maxsize=64)
def _get_browser_adapter_payload(url: str) -> dict:
    """Return rendered-page extraction payload from optional Node adapter."""
    web_root = Path(__file__).resolve().parents[2]
    script_path = web_root / "tools" / "page_flow_render.mjs"
    if not script_path.exists():
        return {}

    # Defense in depth against argv option injection into the Node renderer.
    # The SSRF gate already forces a normalized http(s):// URL on a public host,
    # so a leading '-' can't survive normalization; guard explicitly anyway so a
    # value like "--foo" can never be parsed as a flag by page_flow_render.mjs.
    if not url.startswith(("http://", "https://")) or url.startswith("-"):
        return {}

    timeout_sec = 20
    try:
        timeout_sec = max(5, int(os.environ.get("GLOW_PAGEFLOW_BROWSER_TIMEOUT_SEC", "20")))
    except ValueError:
        timeout_sec = 20

    try:
        proc = subprocess.run(
            ["node", str(script_path), "--url", url, "--timeout-ms", str(timeout_sec * 1000)],
            cwd=str(web_root),
            capture_output=True,
            text=True,
            timeout=timeout_sec + 5,
            check=False,
        )
    except Exception:
        return {}

    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return {}
    try:
        payload = json.loads(proc.stdout)
        if isinstance(payload, dict):
            return payload
    except Exception:
        return {}
    return {}


def _extract_browser_rendered_text(url: str, *, html: str) -> str:
    if not _browser_adapter_enabled_for_html(html):
        return ""
    payload = _get_browser_adapter_payload(url)
    text = _normalize_text(payload.get("text") or "")
    if len(text) < 80:
        return ""
    return _remove_extraction_noise(text)


def _discover_next_page_url_from_browser(base_url: str, *, html: str) -> str:
    if not _browser_adapter_enabled_for_html(html):
        return ""
    payload = _get_browser_adapter_payload(base_url)
    candidates = payload.get("next_candidates") or []
    if not isinstance(candidates, list):
        return ""

    base_host = (urlparse(base_url).hostname or "").lower()
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        next_url = normalize_url(urljoin(base_url, candidate))
        if not next_url:
            continue
        next_host = (urlparse(next_url).hostname or "").lower()
        if next_host and base_host and next_host == base_host and next_url != base_url:
            return next_url
    return ""


def _looks_js_heavy_page_html(html: str) -> bool:
    if not html:
        return False
    lowered = html.lower()
    js_markers = [
        "__next_data__",
        "_next/static",
        "id=\"__next\"",
        "id='__next'",
        "id=\"root\"",
        "id='root'",
        "data-reactroot",
    ]
    marker_hit = any(marker in lowered for marker in js_markers)

    # Heuristic: many scripts and relatively little body text suggest client render.
    script_count = lowered.count("<script")
    rough_text = re.sub(r"<[^>]+>", " ", html)
    rough_text = re.sub(r"\s+", " ", rough_text).strip()
    text_len = len(rough_text)

    return marker_hit or (script_count >= 8 and text_len < 1400)