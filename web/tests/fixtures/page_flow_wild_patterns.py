"""Wild-pattern fixtures for PageFlow extraction regressions.

These mimic common real-world publishing and commerce layouts while staying
fully deterministic and offline for CI.
"""

from __future__ import annotations

import json


def _next_payload(title: str, strings: list[str]) -> str:
    payload = {
        "props": {
            "pageProps": {
                "title": title,
                "summary": strings[0] if strings else "",
                "highlights": strings,
            }
        }
    }
    return (
        "<html><body><div id='__next'></div>"
        f"<script id='__NEXT_DATA__' type='application/json'>{json.dumps(payload)}</script>"
        "</body></html>"
    )


WILD_PATTERN_CASES = [
    {
        "name": "newsroom_with_liveblog_labels",
        "url": "https://example.com/news/live",
        "html": "<html><body><article>live blog</article></body></html>",
        "extract_output": "LIVE UPDATES\n\n# Main update\n\nA meaningful paragraph from the story.",
        "contains": ["Main update", "meaningful paragraph"],
    },
    {
        "name": "cdn_cached_wordpress_with_related_links",
        "url": "https://example.com/wp/cached",
        "html": "<html><body><article>cached story</article></body></html>",
        "extract_output": "# Cached Story\n\nBody text here.\n\nAdditional Links",
        "contains": ["Cached Story", "Body text here"],
        "not_contains": ["Additional Links"],
    },
    {
        "name": "medium_like_heading_stack",
        "url": "https://example.com/medium/post",
        "html": "<html><body><article>medium</article></body></html>",
        "extract_output": "# Why We Rebuilt This\n\n## Context\n\n## Design choices\n\nFinal notes.",
        "contains": ["Why We Rebuilt This", "Design choices", "Final notes"],
    },
    {
        "name": "ghost_cms_with_membership_banner",
        "url": "https://example.com/ghost/member-story",
        "html": "<html><body><article>ghost</article></body></html>",
        "extract_output": "EXCLUSIVE EXTRAS\n\n# Member Story\n\nPublic preview paragraph.",
        "contains": ["Member Story", "Public preview paragraph"],
        "not_contains": ["EXCLUSIVE EXTRAS"],
    },
    {
        "name": "drupal_article_with_pager_tokens",
        "url": "https://example.com/drupal/story",
        "html": "<html><body><article>drupal</article></body></html>",
        "extract_output": "Page: 1 2 3\n\nReadable drupal body content.",
        "contains": ["Readable drupal body content"],
        "not_contains": ["Page:"],
    },
    {
        "name": "nextjs_marketing_page",
        "url": "https://example.com/next/marketing",
        "html": _next_payload(
            "Platform Launch",
            [
                "We launched a resilient extraction system.",
                "It handles pagination and script-heavy pages.",
            ],
        ),
        "extract_output": "",
        "contains": ["Platform Launch", "resilient extraction system", "script-heavy pages"],
    },
    {
        "name": "vite_spa_dump_with_next_payload_absent",
        "url": "https://example.com/spa/vite",
        "html": "<html><body><div id='app'></div></body></html>",
        "extract_output": '{"state":{"route":"/article","content":"hydrated"}}' * 40,
        "contains": [],
    },
    {
        "name": "commerce_collection_json_fallback",
        "url": "https://example.com/shop/collection",
        "html": (
            "<html><body><script id='__NEXT_DATA__' type='application/json'>"
            + json.dumps(
                {
                    "props": {
                        "pageProps": {
                            "title": "Weekly Cart Deals",
                            "collection": {
                                "DisplayName": "Weekly Cart Deals",
                                "ProductCollectionName": "Weekly Cart Deals",
                                "Description": "Low-friction member pricing.",
                                "ProductCollectionItems": [
                                    {"ExtProductId": "sku-100"},
                                    {"ExtProductId": "sku-101"},
                                ],
                            },
                        }
                    }
                }
            )
            + "</script></body></html>"
        ),
        "extract_output": "",
        "contains": ["Weekly Cart Deals", "Total listed items: 2", "sku-100"],
    },
    {
        "name": "european_locale_story",
        "url": "https://example.com/eu/story",
        "html": "<html><body><article>eu</article></body></html>",
        "extract_output": "# Cote d'Ivoire Update\n\nAuteurs presentent la feuille de route.",
        "contains": ["Cote d'Ivoire Update", "feuille de route"],
    },
    {
        "name": "academic_blog_with_toc_and_footers",
        "url": "https://example.com/research/post",
        "html": "<html><body><article>research</article></body></html>",
        "extract_output": "Table of Contents\n\n# Findings\n\nEmpirical section.\n\nSupported by",
        "contains": ["Findings", "Empirical section"],
        "not_contains": ["Table of Contents", "Supported by"],
    },
    {
        "name": "static_site_generator_post",
        "url": "https://example.com/ssg/post",
        "html": "<html><body><article>ssg</article></body></html>",
        "extract_output": "# SSG Post\n\n## Intro\n\n## Implementation\n\nDone.",
        "contains": ["SSG Post", "Implementation", "Done."],
    },
    {
        "name": "forum_thread_first_post_only",
        "url": "https://example.com/forum/thread",
        "html": "<html><body><div>thread</div></body></html>",
        "extract_output": "# Thread title\n\nOriginal poster summary paragraph.",
        "contains": ["Thread title", "Original poster summary"],
    },
    {
        "name": "documentation_portal_mixed_lists",
        "url": "https://example.com/docs/guide",
        "html": "<html><body><article>docs</article></body></html>",
        "extract_output": "# Guide\n\n## Steps\n\n1. Install\n2. Configure\n\n- Verify output",
        "contains": ["Guide", "1. Install", "- Verify output"],
    },
    {
        "name": "headline_only_shell",
        "url": "https://example.com/shell/headline",
        "html": "<html><body><div>headline shell</div></body></html>",
        "extract_output": "# Headline only",
        "contains": ["Headline only"],
    },
    {
        "name": "regional_deals_with_query",
        "url": "https://example.com/deals?region=west&campaign=weekly",
        "html": _next_payload(
            "Regional Deals",
            [
                "Top regional discounts are refreshed weekly.",
                "Member pricing requires loyalty authentication.",
            ],
        ),
        "extract_output": "",
        "contains": ["Regional Deals", "Source: https://example.com/deals?region=west&campaign=weekly"],
    },
]
