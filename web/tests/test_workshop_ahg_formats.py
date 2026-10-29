"""Every AHG 2026 participant document, in Markdown, HTML, Word and PowerPoint.

The owner's rule: everything a participant receives is theirs in the format
they work in. scripts/ahg_formats.py writes the copies; these tests fail when
a Markdown source changes and its copies were not rebuilt, when a copy loses
a structure a screen reader depends on, or when one fails GLOW's own audit.
The inventory, and why some files have no copies, is docs/ahg-2026/formats.md.
"""

from __future__ import annotations

import sys
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


def test_the_kit_online_offers_the_copies_beside_the_document_not_as_files_of_their_own():
    kit = F.AHG / "kit"
    assert [label for label, _ in kit_online.other_formats(kit, "README.md")] == ["Word", "PowerPoint", "HTML"]
    assert kit_online.is_other_format(kit, "read-me.pptx")
    assert kit_online.is_other_format(kit, "step-cards/3-your-agent-at-work.docx")
    assert not kit_online.is_other_format(kit, "share-my-agent.html")
