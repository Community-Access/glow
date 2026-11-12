"""Every AHG 2026 participant document, in Markdown, HTML, Word and PowerPoint.

The owner's rule: everything a participant receives is theirs in the format
they work in. scripts/ahg_formats.py writes the copies; these tests fail when
a Markdown source changes and its copies were not rebuilt, when a copy loses
a structure a screen reader depends on, or when one fails GLOW's own audit.
The inventory, and why some files have no copies, is docs/ahg-2026/formats.md.
"""

from __future__ import annotations

import sys
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import ahg_formats as F  # noqa: E402
import check_ahg_formats as C  # noqa: E402

from acb_large_print_web import ahg_kit_online as kit_online  # noqa: E402

SERIOUS = {"CRITICAL", "HIGH", "MEDIUM"}


@pytest.fixture(scope="module")
def results() -> dict[str, list[str]]:
    return C.check_all()


@pytest.mark.parametrize("rel", F.SOURCES)
def test_every_participant_document_is_current_and_well_formed_in_four_formats(rel, results):
    assert not results[rel], results[rel]


def test_the_inventory_names_every_document_with_copies():
    inventory = (F.AHG / "formats.md").read_text(encoding="utf-8")
    for rel in F.SOURCES:
        assert f"`{rel}`" in inventory, rel


@pytest.mark.parametrize("rel", F.SOURCES)
def test_the_word_and_powerpoint_copies_pass_glow_s_own_audit(rel):
    from acb_large_print.auditor import audit_document
    from acb_large_print.pptx_auditor import audit_presentation

    stem = F.AHG / F.output_stem(rel)
    for path, audit in ((stem.with_suffix(".docx"), audit_document), (stem.with_suffix(".pptx"), audit_presentation)):
        result = audit(path)
        serious = [f for f in result.findings if str(f.severity).split(".")[-1] in SERIOUS]
        assert not serious, (path.name, [(f.rule_id, f.message) for f in serious])


def test_a_readme_s_copies_never_compete_with_it():
    assert F.output_stem("kit/README.md") == "kit/read-me"
    assert F.output_stem("kit/step-cards/6-share-it.md") == "kit/step-cards/6-share-it"


def test_plain_and_code_addresses_are_clickable_in_every_export(tmp_path):
    markdown = """# Link rehearsal

## Resources

Visit letitglow.app/ahg/paths, then `https://example.org/a_(b)`.
Use [the named resource](https://example.com/named) or help@example.edu.

| Site | Address |
|---|---|
| Browser | vscode.dev |

```text
curl https://example.com/command
```
"""
    doc = F.Doc(tmp_path / "source.md", "Link rehearsal", "en", "AHG", "", markdown,
                F._blocks(F._pandoc_json(markdown)))
    expected = {"https://letitglow.app/ahg/paths", "https://example.org/a_(b)",
                "https://example.com/named", "mailto:help@example.edu", "https://vscode.dev"}
    assert C.expected_targets(markdown) == expected
    for extension, writer in ((".html", F.write_html), (".docx", F.write_docx), (".pptx", F.write_pptx)):
        target = tmp_path / ("links" + extension)
        writer(doc, target)
        assert C.hyperlink_targets(target) == expected, extension


def test_address_detection_keeps_punctuation_and_does_not_link_file_names():
    from acb_large_print.document_links import address_parts

    text = "(https://example.org/a_(b)). Read slides.pptx, SKILL.md and report.html."
    parts = list(address_parts(text))
    assert "".join(label for label, _target in parts) == text
    assert [(label, target) for label, target in parts if target] == [
        ("https://example.org/a_(b)", "https://example.org/a_(b)"),
    ]
    assert list(address_parts("vscode.dev.")) == [("vscode.dev", "https://vscode.dev"), (".", "")]


def test_reading_tables_allocate_space_for_wrapped_text(tmp_path):
    from pptx import Presentation
    from pptx.util import Inches

    doc = F.read("kit/step-cards/7-take-it-home.md")
    doc.blocks = [F.Block("table", header=[[F.Run("Part")], [F.Run("Plan")]],
                          rows=[[[F.Run("Input")], [F.Run("Approved evidence " * 12)]],
                                [[F.Run("Owner")], [F.Run("Reviewer")]]])]
    target = tmp_path / "wrapped.pptx"
    F.write_pptx(doc, target)
    prs = Presentation(target)
    table = prs.slides[1].shapes[-1].table
    assert table.rows[1].height > table.rows[2].height
    assert prs.slides[1].shapes[-1].top + sum(r.height for r in table.rows) <= Inches(7.1)


def test_wide_reading_tables_keep_every_value_as_labelled_records():
    doc = F.read("kit/step-cards/7-take-it-home.md")
    headers = [[F.Run(f"Column {n}")] for n in range(9)]
    values = [[F.Run(f"Value {n}")] for n in range(9)]
    doc.blocks = [F.Block("table", header=headers, rows=[values])]
    slides = F.plan_slides(doc)
    assert all(s.table is None for s in slides)
    text = "\n".join(F.plain(line.runs) for s in slides for line in s.lines)
    for n in range(9):
        assert f"Column {n}: Value {n}" in text


def test_campus_plan_questions_match_on_both_paths():
    import build_ahg_kit as kit_builder

    skill = (F.AHG / "kit" / ".github" / "skills" / "my-30-day-plan" / "SKILL.md").read_text(encoding="utf-8")
    browser = kit_builder.ASSISTANT_TEXTS["7-my-30-day-plan"]["task"]
    questions = re.compile(r"1\. One workflow.*?(?=\n\n)", re.S)
    assert questions.search(skill).group() == questions.search(browser).group()
    assert len(re.findall(r"^\d\. ", questions.search(skill).group(), re.M)) == 8
    for text in (skill, browser):
        for required in ("approval", "pending", "baseline", "reviewer", "manual process",
                         "day-30", "Never delay an accommodation"):
            assert required.lower() in text.lower()


def test_the_kit_online_offers_the_copies_beside_the_document_not_as_files_of_their_own():
    kit = F.AHG / "kit"
    assert [label for label, _ in kit_online.other_formats(kit, "README.md")] == ["Word", "PowerPoint", "HTML"]
    assert kit_online.is_other_format(kit, "read-me.pptx")
    assert kit_online.is_other_format(kit, "step-cards/3-your-agent-at-work.docx")
    assert not kit_online.is_other_format(kit, "share-my-agent.html")
