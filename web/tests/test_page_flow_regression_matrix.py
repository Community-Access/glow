"""Regression matrix for PageFlow/listen_later extraction behavior.

These cases are intentionally offline and deterministic. They model common
publishing patterns seen across many domains, including JS-heavy Next.js pages.
"""

from __future__ import annotations

import json

import pytest

import acb_large_print_web.listen_later as listen_later
from tests.fixtures.page_flow_wild_patterns import WILD_PATTERN_CASES


def _next_data_page(*, title: str, display_name: str, item_ids: list[str]) -> str:
    payload = {
        "props": {
            "pageProps": {
                "title": title,
                "collection": {
                    "DisplayName": display_name,
                    "ProductCollectionName": display_name,
                    "Description": "Fixture collection for regression testing.",
                    "ProductCollectionItems": [{"ExtProductId": item_id} for item_id in item_ids],
                },
            }
        }
    }
    return (
        "<html><body><div id='__next'></div>"
        f"<script id='__NEXT_DATA__' type='application/json'>{json.dumps(payload)}</script>"
        "</body></html>"
    )


REGRESSION_CASES = [
    {
        "name": "classic_blog_article",
        "url": "https://example.com/blog/post",
        "html": "<html><body><article><h1>Story</h1><p>Body</p></article></body></html>",
        "extract_output": "# Story\n\nBody paragraph one.\n\nBody paragraph two.",
        "contains": ["Story", "Body paragraph one", "Body paragraph two"],
    },
    {
        "name": "classic_nav_noise_removed",
        "url": "https://example.com/nav/noise",
        "html": "<html><body><article><p>Body content.</p></article></body></html>",
        "extract_output": "TABLE OF CONTENTS\n\nBody content.\n\nNEXT PAGE",
        "contains": ["Body content."],
        "not_contains": ["TABLE OF CONTENTS", "NEXT PAGE"],
    },
    {
        "name": "nextjs_collection_raleys_style",
        "url": "https://example.com/collection/19307",
        "html": _next_data_page(
            title="5 dollar Member Monday",
            display_name="5 dollar Member Monday",
            item_ids=["101", "102", "103", "104"],
        ),
        "extract_output": "",
        "contains": ["5 dollar Member Monday", "Total listed items: 4", "- 101"],
    },
    {
        "name": "nextjs_payload_script_dump_override",
        "url": "https://example.com/next/dump",
        "html": _next_data_page(
            title="Grocery Deals",
            display_name="Grocery Deals",
            item_ids=["abc-1"],
        ),
        "extract_output": '{"props":{"pageProps":{"_nextI18Next":"..."}}}' * 70,
        "contains": ["Grocery Deals", "abc-1"],
        "not_contains": ["_nextI18Next"],
    },
    {
        "name": "nextjs_generic_page_props_strings",
        "url": "https://example.com/news/app-launch",
        "html": (
            "<html><body><script id='__NEXT_DATA__' type='application/json'>"
            + json.dumps(
                {
                    "props": {
                        "pageProps": {
                            "title": "Product Launch",
                            "headline": "A new release is available now.",
                            "summary": "This release improves performance and accessibility.",
                        }
                    }
                }
            )
            + "</script></body></html>"
        ),
        "extract_output": "",
        "contains": ["Product Launch", "A new release is available now.", "improves performance"],
    },
    {
        "name": "empty_extract_without_next_data",
        "url": "https://example.com/empty",
        "html": "<html><body><div id='root'></div></body></html>",
        "extract_output": "",
        "contains": [],
    },
    {
        "name": "sponsor_and_nav_noise_removed",
        "url": "https://example.com/story/sponsor",
        "html": "<html><body><article><p>Real content block.</p></article></body></html>",
        "extract_output": "SUPPORTED BY\n\nReal content block.\n\nEXCLUSIVE EXTRAS",
        "contains": ["Real content block."],
        "not_contains": ["SUPPORTED BY", "EXCLUSIVE EXTRAS"],
    },
    {
        "name": "markdown_heading_preserved",
        "url": "https://example.com/structured",
        "html": "<html><body><article>Structured</article></body></html>",
        "extract_output": "# Heading\n\n## Subheading\n\n- Item one\n- Item two",
        "contains": ["# Heading", "## Subheading", "- Item one"],
    },
    {
        "name": "generic_jsonish_string_filtered",
        "url": "https://example.com/jsonish",
        "html": (
            "<html><body><script id='__NEXT_DATA__' type='application/json'>"
            + json.dumps(
                {
                    "props": {
                        "pageProps": {
                            "title": "Announcements",
                            "body": "{\"props\":{\"pageProps\":\"internal\"}}",
                            "summary": "Public update summary text for readers.",
                        }
                    }
                }
            )
            + "</script></body></html>"
        ),
        "extract_output": "",
        "contains": ["Announcements", "Public update summary"],
        "not_contains": ["internal\"}}"],
    },
    {
        "name": "next_data_without_collection_uses_generic",
        "url": "https://example.com/app/post",
        "html": (
            "<html><body><script id='__NEXT_DATA__' type='application/json'>"
            + json.dumps(
                {
                    "props": {
                        "pageProps": {
                            "title": "Engineering Update",
                            "description": "We rebuilt the pagination service this quarter.",
                        }
                    }
                }
            )
            + "</script></body></html>"
        ),
        "extract_output": "",
        "contains": ["Engineering Update", "pagination service"],
    },
    {
        "name": "wordpress_story_with_ad_callouts",
        "url": "https://example.com/wp/story",
        "html": "<html><body><article><p>Story body.</p></article></body></html>",
        "extract_output": "ADVERTISEMENT\n\nStory body paragraph.\n\nSUPPORTED BY\n\nRelated posts",
        "contains": ["Story body paragraph."],
        "not_contains": ["SUPPORTED BY"],
    },
    {
        "name": "substack_like_markdown_sections",
        "url": "https://example.com/newsletter/post",
        "html": "<html><body><article>newsletter</article></body></html>",
        "extract_output": "# Weekly Note\n\n## What changed\n\n- Parser updates\n- Better pagination",
        "contains": ["# Weekly Note", "## What changed", "- Better pagination"],
    },
    {
        "name": "amp_style_content_preserved",
        "url": "https://example.com/amp/story",
        "html": "<html amp><body><article>amp</article></body></html>",
        "extract_output": "# AMP Story\n\nMain content paragraph.",
        "contains": ["AMP Story", "Main content paragraph"],
    },
    {
        "name": "paywall_shell_minimum_content",
        "url": "https://example.com/paywall/story",
        "html": "<html><body><div>shell</div></body></html>",
        "extract_output": "# Breaking News\n\nThis is a member-only story preview.",
        "contains": ["Breaking News", "member-only story preview"],
    },
    {
        "name": "ad_heavy_script_dump_prefers_next_data",
        "url": "https://example.com/ad-heavy/spa",
        "html": _next_data_page(
            title="Deals Hub",
            display_name="Deals Hub",
            item_ids=["sku-1", "sku-2"],
        ),
        "extract_output": '{"props":{"pageProps":{"_nextI18Next":"noise"}}}' * 80,
        "contains": ["Deals Hub", "sku-1"],
    },
    {
        "name": "generic_next_data_with_long_summary",
        "url": "https://example.com/platform/update",
        "html": (
            "<html><body><script id='__NEXT_DATA__' type='application/json'>"
            + json.dumps(
                {
                    "props": {
                        "pageProps": {
                            "title": "Platform Update",
                            "summary": "This month we shipped queue-based rendering, voice catalog improvements, and better pagination extraction across multiple content platforms.",
                        }
                    }
                }
            )
            + "</script></body></html>"
        ),
        "extract_output": "",
        "contains": ["Platform Update", "voice catalog improvements"],
    },
    {
        "name": "noisy_navigation_lines_removed",
        "url": "https://example.com/nav/page",
        "html": "<html><body><article>body</article></body></html>",
        "extract_output": "PAGE: 1 2 3\n\nMain section text.\n\nPREVIOUS PAGE\n\nNEXT PAGE",
        "contains": ["Main section text."],
        "not_contains": ["NEXT PAGE", "PREVIOUS PAGE"],
    },
    {
        "name": "jsonld_heavy_but_plain_text_kept",
        "url": "https://example.com/jsonld/story",
        "html": "<html><head><script type='application/ld+json'>{}</script></head><body></body></html>",
        "extract_output": "# Headline\n\nReadable article text with schema-heavy source.",
        "contains": ["Headline", "Readable article text"],
    },
    {
        "name": "long_catalog_extract_from_next_data",
        "url": "https://example.com/collection/huge",
        "html": _next_data_page(
            title="Weekly Savings",
            display_name="Weekly Savings",
            item_ids=[str(i) for i in range(1, 65)],
        ),
        "extract_output": "",
        "contains": ["Weekly Savings", "Total listed items: 64", "- 1", "- 40"],
    },
    {
        "name": "next_data_present_but_invalid_json_returns_primary",
        "url": "https://example.com/next/invalid",
        "html": "<script id='__NEXT_DATA__' type='application/json'>{invalid-json</script>",
        "extract_output": "# Primary Output\n\nFallback to primary extractor text.",
        "contains": ["Primary Output", "Fallback to primary"],
    },
    {
        "name": "unicode_and_typography_survive_cleanup",
        "url": "https://example.com/unicode/story",
        "html": "<html><body><article>unicode</article></body></html>",
        "extract_output": "# Café Review\n\nA ‘smart quotes’ paragraph with naïve unicode handling.",
        "contains": ["Café Review", "smart quotes", "naïve"],
    },
    {
        "name": "short_extract_kept_without_next_data",
        "url": "https://example.com/short",
        "html": "<html><body><p>short</p></body></html>",
        "extract_output": "Short text.",
        "contains": ["Short text."],
    },
    {
        "name": "merchant_collection_with_querystring_source",
        "url": "https://example.com/collection/19307?utm_source=home&utm_medium=hero",
        "html": _next_data_page(
            title="Member Monday",
            display_name="Member Monday",
            item_ids=["9001", "9002", "9003"],
        ),
        "extract_output": "",
        "contains": ["Member Monday", "Source: https://example.com/collection/19307?utm_source=home&utm_medium=hero"],
    },
    {
        "name": "script_dump_without_next_data_stays_non_crashing",
        "url": "https://example.com/spa/no-next",
        "html": "<html><body><div id='root'></div></body></html>",
        "extract_output": '{"props":{"pageProps":{"foo":"bar"}}}' * 80,
        "contains": [],
    },
]


REGRESSION_CASES = REGRESSION_CASES + WILD_PATTERN_CASES


@pytest.mark.parametrize("case", REGRESSION_CASES, ids=[c["name"] for c in REGRESSION_CASES])
def test_page_flow_extraction_regression_matrix(monkeypatch: pytest.MonkeyPatch, case: dict):
    monkeypatch.setattr(listen_later, "_extract_main_text", lambda html, **kwargs: case["extract_output"])

    text = listen_later._extract_page_text(case["html"], case["url"])

    for expected in case.get("contains", []):
        assert expected in text
    for forbidden in case.get("not_contains", []):
        assert forbidden not in text


NEXT_LINK_CASES = [
    {
        "name": "rel_next_anchor",
        "html": "<html><body><a rel='next' href='/story/2'>Next</a></body></html>",
        "base_url": "https://example.com/story/1",
        "expected": "https://example.com/story/2",
    },
    {
        "name": "link_rel_next",
        "html": "<html><head><link rel='next' href='https://example.com/story/2' /></head></html>",
        "base_url": "https://example.com/story/1",
        "expected": "https://example.com/story/2",
    },
    {
        "name": "aria_label_next",
        "html": "<html><body><a href='/page/2' aria-label='Next Page'>go</a></body></html>",
        "base_url": "https://example.com/page/1",
        "expected": "https://example.com/page/2",
    },
    {
        "name": "title_continue",
        "html": "<html><body><a href='/chapter-2' title='Continue reading'>Continue</a></body></html>",
        "base_url": "https://example.com/chapter-1",
        "expected": "https://example.com/chapter-2",
    },
    {
        "name": "symbol_arrow",
        "html": "<html><body><a href='/n'>»</a></body></html>",
        "base_url": "https://example.com/p/1",
        "expected": "https://example.com/n",
    },
    {
        "name": "cross_host_rejected",
        "html": "<html><body><a rel='next' href='https://evil.example.net/x'>Next</a></body></html>",
        "base_url": "https://example.com/p/1",
        "expected": "",
    },
    {
        "name": "no_next_found",
        "html": "<html><body><a href='/about'>About</a></body></html>",
        "base_url": "https://example.com/p/1",
        "expected": "",
    },
    {
        "name": "next_data_pagination_next_url",
        "html": (
            "<html><body><script id='__NEXT_DATA__' type='application/json'>"
            + json.dumps(
                {
                    "props": {
                        "pageProps": {
                            "pagination": {
                                "nextUrl": "/series/story/2/"
                            }
                        }
                    }
                }
            )
            + "</script></body></html>"
        ),
        "base_url": "https://example.com/series/story/1/",
        "expected": "https://example.com/series/story/2/",
    },
    {
        "name": "next_data_cross_host_next_rejected",
        "html": (
            "<html><body><script id='__NEXT_DATA__' type='application/json'>"
            + json.dumps(
                {
                    "props": {
                        "pageProps": {
                            "pagination": {
                                "nextUrl": "https://other.example.net/series/story/2/"
                            }
                        }
                    }
                }
            )
            + "</script></body></html>"
        ),
        "base_url": "https://example.com/series/story/1/",
        "expected": "",
    },
]


@pytest.mark.parametrize("case", NEXT_LINK_CASES, ids=[c["name"] for c in NEXT_LINK_CASES])
def test_next_page_discovery_patterns(case: dict):
    result = listen_later._discover_next_page_url(case["html"], case["base_url"])
    assert result == case["expected"]


NOISE_CASES = [
    {
        "name": "drops_supported_by",
        "text": "SUPPORTED BY\n\nBody paragraph.",
        "contains": ["Body paragraph."],
        "not_contains": ["SUPPORTED BY"],
    },
    {
        "name": "drops_table_of_contents",
        "text": "Table of Contents\n\nSection text",
        "contains": ["Section text"],
        "not_contains": ["Table of Contents"],
    },
    {
        "name": "drops_next_previous_lines",
        "text": "Previous Page\n\nMain text\n\nNext Page",
        "contains": ["Main text"],
        "not_contains": ["Previous Page", "Next Page"],
    },
]


@pytest.mark.parametrize("case", NOISE_CASES, ids=[c["name"] for c in NOISE_CASES])
def test_noise_cleanup_patterns(case: dict):
    cleaned = listen_later._remove_extraction_noise(case["text"])
    for expected in case.get("contains", []):
        assert expected in cleaned
    for forbidden in case.get("not_contains", []):
        assert forbidden not in cleaned
