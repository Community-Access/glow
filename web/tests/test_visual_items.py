"""Regression tests for visual_items ZIP/XML bomb hardening (finding 10)."""

from __future__ import annotations

import io
import zipfile

import pytest

from acb_large_print_web import visual_items


def test_xml_parsing_is_defused():
    """XML entity-expansion (billion-laughs) must be rejected, not expanded.

    The stdlib xml.etree would happily parse the DOCTYPE/entity; defusedxml
    raises instead. This guards the parser swap in _extract_docx_media.
    """
    bomb = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE lolz [<!ENTITY lol "lol">]>'
        "<root>&lol;</root>"
    )
    with pytest.raises(Exception):
        visual_items._safe_xml_fromstring(bomb)


def test_zip_budget_rejects_oversized_entry(monkeypatch):
    """A single entry whose declared size exceeds the per-entry cap is refused
    before archive.read() inflates it into memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("big.bin", b"x" * 1000)
    buf.seek(0)

    monkeypatch.setattr(visual_items, "_MAX_ZIP_ENTRY_BYTES", 100)
    with zipfile.ZipFile(buf) as z:
        budget = visual_items._ZipBudget()
        with pytest.raises(ValueError):
            budget.read(z, "big.bin")


def test_zip_budget_rejects_cumulative_overflow(monkeypatch):
    """The running total cap stops many moderate entries from summing into a bomb."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.bin", b"x" * 600)
        z.writestr("b.bin", b"y" * 600)
    buf.seek(0)

    monkeypatch.setattr(visual_items, "_MAX_ZIP_ENTRY_BYTES", 10_000)
    monkeypatch.setattr(visual_items, "_MAX_ZIP_TOTAL_BYTES", 1000)
    with zipfile.ZipFile(buf) as z:
        budget = visual_items._ZipBudget()
        assert budget.read(z, "a.bin") == b"x" * 600  # first fits
        with pytest.raises(ValueError):
            budget.read(z, "b.bin")  # cumulative total now exceeds cap


def _tiny_png() -> bytes:
    # Not a valid PNG; dimension detection fails gracefully (returns None, None).
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def test_extract_epub_stops_at_max_items(tmp_path):
    """Finding 10: extraction stops once max_items is reached instead of reading
    every image entry in the archive."""
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as z:
        for i in range(5):
            z.writestr(f"OEBPS/img{i}.png", _tiny_png())

    items = visual_items.extract_visual_items(epub, max_items=2)
    assert len(items) == 2
    assert all(item["total_items"] == 2 for item in items)
