"""Tests for the Listen Later extraction helpers."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import acb_large_print_web.listen_later as listen_later


class _Response:
    def __init__(self, url: str, text: str, status_code: int = 200):
        self.url = url
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_extract_article_rejects_invalid_url():
    with pytest.raises(listen_later.ArticleExtractionError, match="valid article URL"):
        listen_later.extract_article("   ")


def test_extract_article_follows_next_page_and_merges_text(monkeypatch: pytest.MonkeyPatch):
    page_one = """
    <html>
      <head><title>Story Part 1</title></head>
      <body>
        <article>
          <p>Opening paragraph.</p>
          <p>Shared footer.</p>
        </article>
        <a rel="next" href="/story?page=2">Next</a>
      </body>
    </html>
    """
    page_two = """
    <html>
      <head><title>Story Part 2</title></head>
      <body>
        <article>
          <p>Second paragraph.</p>
          <p>Shared footer.</p>
        </article>
      </body>
    </html>
    """

    responses = {
        "https://example.com/story": _Response("https://example.com/story", page_one),
        "https://example.com/story?page=2": _Response("https://example.com/story?page=2", page_two),
    }

    def _fake_get(url, timeout, headers):
        return responses[url]

    monkeypatch.setattr(listen_later.requests, "get", _fake_get)
    monkeypatch.setattr(listen_later, "_extract_metadata", lambda html: SimpleNamespace(title="Story Title"))

    def _fake_extract(html, **kwargs):
        if "page=2" in html:
            return "Second paragraph.\n\nShared footer."
        return "Opening paragraph.\n\nShared footer."

    monkeypatch.setattr(listen_later, "_extract_main_text", _fake_extract)

    article = listen_later.extract_article("example.com/story")

    assert article.source_url == "https://example.com/story"
    assert article.final_url == "https://example.com/story?page=2"
    assert article.title == "Story Title"
    assert article.page_urls == ["https://example.com/story", "https://example.com/story?page=2"]
    assert "Opening paragraph." in article.text
    assert "Second paragraph." in article.text
    assert article.text.count("Shared footer.") == 1


def test_extract_article_falls_back_to_next_data_collection(monkeypatch: pytest.MonkeyPatch):
    payload = {
        "props": {
            "pageProps": {
                "title": "5 dollar Member Monday",
                "collection": {
                    "DisplayName": "5 dollar Member Monday",
                    "ProductCollectionName": "$5 Monday RBN",
                    "Description": "Weekly member offers.",
                    "ProductCollectionItems": [
                        {"ExtProductId": "101"},
                        {"ExtProductId": "102"},
                        {"ExtProductId": "103"},
                    ],
                },
            }
        }
    }
    page = f"""
    <html>
      <head><title>Collection</title></head>
      <body>
      <div id="__next"></div>
      <script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>
      </body>
    </html>
    """

    responses = {
        "https://example.com/collection": _Response("https://example.com/collection", page),
    }

    def _fake_get(url, timeout, headers):
        return responses[url]

    monkeypatch.setattr(listen_later.requests, "get", _fake_get)
    monkeypatch.setattr(listen_later, "_extract_metadata", lambda html: None)
    monkeypatch.setattr(listen_later, "_extract_main_text", lambda html, **kwargs: "")

    article = listen_later.extract_article("https://example.com/collection", follow_pagination=False)

    assert article.title == "Article"
    assert "# 5 dollar Member Monday" in article.text
    assert "Total listed items: 3" in article.text
    assert "- 101" in article.text


def test_extract_page_text_uses_next_data_when_primary_is_script_dump(monkeypatch: pytest.MonkeyPatch):
    payload = {
        "props": {
            "pageProps": {
                "title": "Sample Collection",
                "collection": {
                    "DisplayName": "Sample Collection",
                    "ProductCollectionItems": [{"ExtProductId": "abc-1"}],
                },
            }
        }
    }
    html = f"<script id=\"__NEXT_DATA__\" type=\"application/json\">{json.dumps(payload)}</script>"
    script_dump = '{"props":{"pageProps":{"_nextI18Next":"..."}}}' * 60

    monkeypatch.setattr(listen_later, "_extract_main_text", lambda html, **kwargs: script_dump)

    text = listen_later._extract_page_text(html, "https://example.com/collection")
    assert "Sample Collection" in text
    assert "abc-1" in text


def test_discover_next_page_url_from_next_data_payload():
    payload = {
        "props": {
            "pageProps": {
                "pagination": {
                    "nextUrl": "/stories/example/2/",
                }
            }
        }
    }
    html = f"<script id=\"__NEXT_DATA__\" type=\"application/json\">{json.dumps(payload)}</script>"

    next_url = listen_later._discover_next_page_url(html, "https://example.com/stories/example/")
    assert next_url == "https://example.com/stories/example/2/"


def test_extract_page_text_prefers_item_names_when_available(monkeypatch: pytest.MonkeyPatch):
    payload = {
        "props": {
            "pageProps": {
                "title": "Deals",
                "collection": {
                    "DisplayName": "Deals",
                    "ProductCollectionItems": [
                        {"ExtProductId": "sku-1", "DisplayName": "Family Pasta"},
                        {"ExtProductId": "sku-2", "Name": "Olive Oil"},
                    ],
                },
            }
        }
    }
    html = f"<script id=\"__NEXT_DATA__\" type=\"application/json\">{json.dumps(payload)}</script>"
    monkeypatch.setattr(listen_later, "_extract_main_text", lambda html, **kwargs: "")

    text = listen_later._extract_page_text(html, "https://example.com/deals")
    assert "Family Pasta (sku-1)" in text
    assert "Olive Oil (sku-2)" in text


def test_extract_page_text_can_fall_back_to_browser_adapter(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GLOW_PAGEFLOW_BROWSER_ADAPTER", "1")
    monkeypatch.setattr(listen_later, "_extract_main_text", lambda html, **kwargs: "")
    monkeypatch.setattr(listen_later, "_extract_nextjs_payload_text", lambda html, source_url: "")
    monkeypatch.setattr(
        listen_later,
        "_get_browser_adapter_payload",
        lambda url: {"text": "Rendered DOM content from browser adapter. " * 6, "next_candidates": []},
    )

    text = listen_later._extract_page_text("<html><div id='root'></div></html>", "https://example.com/js")
    assert "Rendered DOM content" in text


def test_discover_next_page_url_can_use_browser_adapter(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GLOW_PAGEFLOW_BROWSER_ADAPTER", "1")
    monkeypatch.setattr(
        listen_later,
        "_get_browser_adapter_payload",
        lambda url: {"text": "", "next_candidates": ["/story/2/", "https://evil.example.net/x"]},
    )

    next_url = listen_later._discover_next_page_url("<html></html>", "https://example.com/story/1/")
    assert next_url == "https://example.com/story/2/"


def test_browser_adapter_auto_mode_skips_non_js_pages(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GLOW_PAGEFLOW_BROWSER_ADAPTER", raising=False)
    calls = {"count": 0}

    def _fake_payload(url):
        calls["count"] += 1
        return {"text": "Rendered fallback", "next_candidates": ["/n"]}

    monkeypatch.setattr(listen_later, "_get_browser_adapter_payload", _fake_payload)
    monkeypatch.setattr(listen_later, "_extract_main_text", lambda html, **kwargs: "")
    monkeypatch.setattr(listen_later, "_extract_nextjs_payload_text", lambda html, source_url: "")

    _ = listen_later._extract_page_text("<html><body><article><p>Plain page text</p></article></body></html>", "https://example.com/plain")
    _ = listen_later._discover_next_page_url("<html><body><a href='/about'>About</a></body></html>", "https://example.com/p/1")
    assert calls["count"] == 0


def test_browser_adapter_auto_mode_runs_for_js_heavy_pages(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GLOW_PAGEFLOW_BROWSER_ADAPTER", raising=False)
    calls = {"count": 0}

    def _fake_payload(url):
        calls["count"] += 1
        return {"text": "Rendered DOM content from app root. " * 6, "next_candidates": ["/story/2/"]}

    monkeypatch.setattr(listen_later, "_get_browser_adapter_payload", _fake_payload)
    monkeypatch.setattr(listen_later, "_extract_main_text", lambda html, **kwargs: "")
    monkeypatch.setattr(listen_later, "_extract_nextjs_payload_text", lambda html, source_url: "")

    js_html = "<html><body><div id='root'></div>" + ("<script></script>" * 12) + "</body></html>"
    text = listen_later._extract_page_text(js_html, "https://example.com/app")
    assert "Rendered DOM content" in text

    next_url = listen_later._discover_next_page_url(js_html, "https://example.com/story/1/")
    assert next_url == "https://example.com/story/2/"
    assert calls["count"] >= 1
