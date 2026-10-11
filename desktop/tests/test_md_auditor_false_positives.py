"""Markdown rules must not fire on things that are not what they look for.

Found while auditing the AHG 2026 workshop materials: real ordered lists were
reported as "manually numbered", file names like ``acb_large_print_web`` as
italics, and ``SKILL.md`` in inline code as shouting. A checker that cries
wolf teaches people to ignore it, and these documents are about trusting
checkers.
"""

from __future__ import annotations

from pathlib import Path

from acb_large_print.md_auditor import audit_markdown


def _rules(tmp_path: Path, text: str) -> list[str]:
    path = tmp_path / "sample.md"
    path.write_text(text, encoding="utf-8")
    return [f.rule_id for f in audit_markdown(path).findings]


def test_a_real_ordered_list_is_not_a_fake_one(tmp_path: Path) -> None:
    rules = _rules(tmp_path, "# Steps\n\n1. Open it.\n2. Read it.\n3. Close it.\n4. Done.\n")
    assert "MD-FAKE-NUMBERED-LIST" not in rules


def test_a_manually_numbered_list_is_still_caught(tmp_path: Path) -> None:
    rules = _rules(tmp_path, "# Steps\n\n(1) Open it.\n(2) Read it.\n(3) Close it.\n")
    assert "MD-FAKE-NUMBERED-LIST" in rules


def test_underscores_inside_names_are_not_italics(tmp_path: Path) -> None:
    rules = _rules(tmp_path, "# Names\n\nSee acb_large_print_web and AHG_DAY for details.\n")
    assert "MD-NO-ITALIC" not in rules


def test_real_underscore_italics_are_still_caught(tmp_path: Path) -> None:
    rules = _rules(tmp_path, "# Emphasis\n\nThis is _really_ important.\n")
    assert "MD-NO-ITALIC" in rules


def test_inline_code_and_urls_are_literal(tmp_path: Path) -> None:
    text = "# Files\n\nOpen `my-agent/SKILL.md` and `_draft_` at https://example.com/_x_/README.\n"
    rules = _rules(tmp_path, text)
    assert "MD-NO-ITALIC" not in rules
    assert "MD-ALLCAPS" not in rules


def test_four_letter_acronyms_are_not_shouting(tmp_path: Path) -> None:
    rules = _rules(tmp_path, "# Kit\n\nBring an HDMI cable and the VPAT.\n")
    assert "MD-ALLCAPS" not in rules


def test_shouted_words_are_still_caught(tmp_path: Path) -> None:
    rules = _rules(tmp_path, "# Policy\n\nNO MAKEUP EXAMS will be given.\n")
    assert "MD-ALLCAPS" in rules


def test_a_described_table_may_have_a_blank_line_before_it(tmp_path: Path) -> None:
    rules = _rules(tmp_path, "# Data\n\nThe table below lists the files.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    assert "MD-TABLE-NO-DESCRIPTION" not in rules


def test_a_table_straight_after_a_heading_is_still_undescribed(tmp_path: Path) -> None:
    rules = _rules(tmp_path, "# Data\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
    assert "MD-TABLE-NO-DESCRIPTION" in rules


def test_an_address_in_inline_code_is_not_a_bare_url(tmp_path: Path) -> None:
    rules = _rules(tmp_path, "# Setup\n\nOpen `https://example.com/setup` in your browser.\n")
    assert "MD-BARE-URL" not in rules


def test_a_bare_url_in_prose_is_still_caught(tmp_path: Path) -> None:
    rules = _rules(tmp_path, "# Setup\n\nOpen https://example.com/setup in your browser.\n")
    assert "MD-BARE-URL" in rules
