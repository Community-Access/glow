"""Regression tests for WCAG help-link generation and rule-policy building.

Covers:
- Every rule whose ``acb_reference`` names a WCAG success criterion resolves
  to a slug (no silent misses), and the specific corrected/suppressed rules
  behave as intended.
- ``build_rule_policy`` normalizes plain-dict form values instead of iterating
  a category string character-by-character.
- Custom mode with an explicit empty selection audits nothing, not everything.
"""

from __future__ import annotations

from acb_large_print.constants import AUDIT_RULES

from acb_large_print_web.rules import (
    _WCAG_RE,
    _WCAG_REFERENCE_OVERRIDES,
    _WCAG_SLUGS,
    _wcag_url_from_reference,
    build_rule_policy,
    get_all_rule_ids,
)


def test_every_wcag_reference_resolves_or_is_intentionally_overridden():
    """No rule that cites a WCAG SC should silently miss a slug."""
    misses = []
    for rid, rule in AUDIT_RULES.items():
        m = _WCAG_RE.search(rule.acb_reference or "")
        if not m:
            continue
        if rid in _WCAG_REFERENCE_OVERRIDES:
            # Intentional correction or suppression -- verify it resolves the
            # way the override declares (a string criterion must have a slug).
            override = _WCAG_REFERENCE_OVERRIDES[rid]
            if override is not None:
                assert override in _WCAG_SLUGS, f"{rid} override {override} lacks a slug"
            continue
        criterion = m.group(1)
        if criterion not in _WCAG_SLUGS:
            misses.append((rid, criterion))
    assert not misses, f"Rules cite WCAG criteria with no slug: {misses}"


def test_pptx_small_font_links_to_resize_text_not_contrast():
    ref = AUDIT_RULES["PPTX-SMALL-FONT"].acb_reference
    label, url = _wcag_url_from_reference(ref, "PPTX-SMALL-FONT")
    assert "resize-text" in url
    assert "1.4.4" in label
    assert "contrast-minimum" not in url


def test_suppressed_rules_produce_no_auto_wcag_link():
    for rid in (
        "ACB-DOC-AUTHOR",
        "MD-YAML-MISSING-AUTHOR",
        "MD-YAML-MISSING-DESCRIPTION",
        "MD-NO-EMOJI",
        "MD-CODE-BLOCK-NO-LANGUAGE",
        "MD-INDENTED-CODE-BLOCK",
    ):
        ref = AUDIT_RULES[rid].acb_reference
        assert _wcag_url_from_reference(ref, rid) is None, rid


def test_newly_added_slugs_generate_links():
    # 2.2.1, 2.2.2, 2.3.3, 1.4.8 rules now get a link.
    for rid in (
        "PPTX-FAST-AUTO-ADVANCE",
        "PPTX-REPEATING-ANIMATION",
        "PPTX-RAPID-AUTO-ANIMATION",
        "PPTX-FAST-TRANSITION",
        "MD-ALLCAPS",
    ):
        ref = AUDIT_RULES[rid].acb_reference
        result = _wcag_url_from_reference(ref, rid)
        assert result is not None, rid
        assert result[1].startswith("https://www.w3.org/WAI/WCAG22/Understanding/")


def test_build_rule_policy_plain_dict_category_not_iterated_char_by_char():
    """A plain dict with a scalar category must not degenerate to zero rules."""
    policy = build_rule_policy({"mode": "full", "category": "acb"})
    # "acb" iterated char-by-char ('a','c','b') would select no real category
    # and yield an empty rule set. It must instead resolve real ACB rules.
    assert len(policy.selected) > 0
    assert all(rid in AUDIT_RULES for rid in policy.selected)


def test_custom_mode_empty_selection_audits_nothing():
    """Unchecking every rule in custom mode selects nothing, not everything."""
    policy = build_rule_policy({"mode": "custom"})
    assert policy.selected == frozenset()
    # Sanity: full mode still selects the whole set.
    full = build_rule_policy({"mode": "full"})
    assert full.selected == frozenset(get_all_rule_ids())
