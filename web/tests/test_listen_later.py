"""Tests for the Listen Later extraction helpers."""

from __future__ import annotations

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
