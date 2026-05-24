"""Listen Later article extraction helpers.

This module fetches article pages, extracts the readable story text, and
follows simple next-page pagination links when present.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from lxml import html as lxml_html

try:
    from trafilatura import extract as _extract_main_text
    from trafilatura import extract_metadata as _extract_metadata
except Exception:  # pragma: no cover - handled at runtime if dependency is absent
    _extract_main_text = None
    _extract_metadata = None


class ArticleExtractionError(Exception):
    """Raised when article extraction fails."""


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
    response = requests.get(url, timeout=20, headers={"User-Agent": "GLOW-Listen-Later/1.0"})
    response.raise_for_status()
    return response.text or "", response.url or url


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
    try:
        text = _extract_main_text(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
    except Exception as exc:
        raise ArticleExtractionError(f"Could not extract readable article text: {exc}") from exc
    return _normalize_text(text or "")


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