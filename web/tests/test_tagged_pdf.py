"""Every PDF GLOW renders with WeasyPrint is tagged and claims PDF/UA-1 (#145).

WeasyPrint writes untagged PDF unless asked, and an untagged PDF gives a screen
reader no headings, no lists, no tables and no reading order. GLOW renders PDF
with WeasyPrint in three places -- Convert to PDF, the shared audit report's
PDF download, and the Document Chat PDF export -- and each one is checked here
by rendering a real PDF and reading its catalog back:

* ``/MarkInfo << /Marked true >>`` and a ``/StructTreeRoot`` (it is tagged);
* structure elements for the headings, lists and tables in the source;
* ``/Lang`` and ``/ViewerPreferences << /DisplayDocTitle true >>`` with a title;
* ``pdfuaid:part="1"`` in the XMP metadata (it identifies as PDF/UA-1).

The last test is a guard: nothing in the shipped source calls ``write_pdf()``
except ``write_tagged_pdf``, so a fourth call site cannot quietly go untagged.
"""

from __future__ import annotations

import os
import re
import shutil
import uuid
from pathlib import Path

import pytest

pymupdf = pytest.importorskip("pymupdf")

REPO_ROOT = Path(__file__).resolve().parents[2]


def _weasyprint_usable() -> bool:
    try:
        import weasyprint  # noqa: F401
    except (ImportError, OSError):  # OSError: Pango/Cairo system libs missing
        return False
    return True


# On a developer machine without Pango or Pandoc these tests skip. In CI they
# must run: a skip there would let an untagged PDF through unnoticed.
_IN_CI = bool(os.environ.get("CI"))

needs_weasyprint = pytest.mark.skipif(
    not _IN_CI and not _weasyprint_usable(),
    reason="WeasyPrint (or its system libraries) not installed",
)
needs_pandoc = pytest.mark.skipif(
    not _IN_CI and shutil.which("pandoc") is None, reason="Pandoc not installed"
)


def _pdf_facts(pdf_bytes: bytes) -> dict:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    catalog = doc.pdf_catalog()
    struct_types = set()
    for xref in range(1, doc.xref_length()):
        if doc.xref_get_key(xref, "Type") == ("name", "/StructElem"):
            kind, value = doc.xref_get_key(xref, "S")
            if kind == "name":
                struct_types.add(value.lstrip("/"))
    return {
        "mark_info": doc.xref_get_key(catalog, "MarkInfo"),
        "struct_tree_root": doc.xref_get_key(catalog, "StructTreeRoot")[0],
        "lang": doc.xref_get_key(catalog, "Lang"),
        "viewer_prefs": doc.xref_get_key(catalog, "ViewerPreferences"),
        "xmp": doc.get_xml_metadata() or "",
        "title": (doc.metadata or {}).get("title", ""),
        "struct_types": struct_types,
    }


def _assert_tagged_pdf_ua(facts: dict) -> None:
    assert facts["mark_info"][0] == "dict"
    assert re.search(r"/Marked\s+true", facts["mark_info"][1]), facts["mark_info"]
    assert facts["struct_tree_root"] == "xref", "no /StructTreeRoot: the PDF is untagged"
    assert re.search(r'pdfuaid:part(="1"|>1<)', facts["xmp"]), "no PDF/UA-1 identifier in XMP"
    assert facts["lang"][0] == "string" and facts["lang"][1], "no document language"
    assert "DisplayDocTitle true" in facts["viewer_prefs"][1]
    assert facts["title"], "no document title"


# ---------------------------------------------------------------------------
# The shared option set
# ---------------------------------------------------------------------------


def test_tagged_pdf_options_request_pdf_ua_1():
    from acb_large_print.pandoc_converter import TAGGED_PDF_OPTIONS

    assert TAGGED_PDF_OPTIONS == {"pdf_variant": "pdf/ua-1", "pdf_tags": True}


# ---------------------------------------------------------------------------
# 1. Convert to PDF (Pandoc + WeasyPrint)
# ---------------------------------------------------------------------------


@needs_weasyprint
@needs_pandoc
def test_convert_to_pdf_from_markdown_is_tagged(tmp_path):
    from acb_large_print.pandoc_converter import convert_to_pdf

    src = tmp_path / "sample.md"
    src.write_text(
        "# Main heading\n\nIntro paragraph.\n\n## Section\n\n"
        "- first item\n- second item\n\n"
        "| Name | Value |\n|------|-------|\n| a | 1 |\n| b | 2 |\n",
        encoding="utf-8",
    )
    out, size = convert_to_pdf(src, tmp_path / "sample.pdf", title="Sample document")
    assert size > 0
    facts = _pdf_facts(out.read_bytes())
    _assert_tagged_pdf_ua(facts)
    assert facts["title"] == "Sample document"
    assert facts["lang"][1] == "en"
    assert {"H1", "H2", "L", "LI", "Table", "TR"} <= facts["struct_types"], facts["struct_types"]


@needs_weasyprint
@needs_pandoc
def test_convert_to_pdf_from_glow_test_docx_is_tagged(tmp_path):
    """The sample named in #145: its headings and lists reach the tag tree."""
    from acb_large_print.pandoc_converter import convert_to_pdf

    sample = REPO_ROOT / "samples" / "GLOW_Test_2-fixed.docx"
    if not sample.exists():
        pytest.skip("samples/GLOW_Test_2-fixed.docx not present")
    out, _ = convert_to_pdf(sample, tmp_path / "glow-test-2.pdf")
    facts = _pdf_facts(out.read_bytes())
    _assert_tagged_pdf_ua(facts)
    assert any(t in facts["struct_types"] for t in ("H1", "H2")), facts["struct_types"]


# ---------------------------------------------------------------------------
# 2. Shared audit report as PDF
# ---------------------------------------------------------------------------


@needs_weasyprint
def test_shared_audit_report_pdf_is_tagged(tmp_path):
    from acb_large_print_web import report_cache
    from acb_large_print_web.app import create_app

    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    app.instance_path = str(tmp_path / "instance")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    token = str(uuid.uuid4())
    report_cache.save_report(
        token,
        '<!DOCTYPE html><html lang="en"><head><title>Audit report</title></head>'
        "<body><main><h1>Audit report</h1><h2>Findings</h2>"
        "<table><tr><th>Rule</th><th>Severity</th></tr>"
        "<tr><td>Alt text</td><td>High</td></tr></table>"
        "<ul><li>Fix one</li><li>Fix two</li></ul></main></body></html>",
    )
    try:
        resp = app.test_client().get(f"/audit/share/{token}/pdf")
        assert resp.status_code == 200
        assert resp.mimetype == "application/pdf"
        facts = _pdf_facts(resp.data)
    finally:
        shutil.rmtree(report_cache._share_dir(token), ignore_errors=True)
    _assert_tagged_pdf_ua(facts)
    assert {"H1", "H2", "Table", "L"} <= facts["struct_types"], facts["struct_types"]


# ---------------------------------------------------------------------------
# 3. Document Chat PDF export
# ---------------------------------------------------------------------------


@needs_weasyprint
@needs_pandoc
def test_chat_export_pdf_is_tagged_with_title_and_language(tmp_path):
    from acb_large_print_web.chat_handler import ChatSession

    session = ChatSession("tok", "report.docx")
    turn = session.add_turn("What are the headings?")
    turn.answer = "There are two:\n\n- Introduction\n- Results\n"
    out = tmp_path / "chat.pdf"
    session.export_pdf(out)

    facts = _pdf_facts(out.read_bytes())
    _assert_tagged_pdf_ua(facts)
    assert facts["title"] == "Chat Session: report.docx"
    assert facts["lang"][1] == "en"
    assert {"H1", "H2", "L"} <= facts["struct_types"], facts["struct_types"]


# ---------------------------------------------------------------------------
# Guard: no untagged write_pdf() call in shipped code
# ---------------------------------------------------------------------------


def test_no_direct_write_pdf_calls_in_shipped_source():
    offenders = []
    for root in (REPO_ROOT / "web" / "src", REPO_ROOT / "desktop" / "src", REPO_ROOT / "mcp_server"):
        for path in root.rglob("*.py"):
            if "tests" in path.parts:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("#", 1)[0]
                if ".write_pdf(" in code and "return html_doc.write_pdf(target, **TAGGED_PDF_OPTIONS)" not in code:
                    offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
    assert not offenders, (
        "Render PDF through acb_large_print.pandoc_converter.write_tagged_pdf, "
        "not write_pdf() directly, so the output is tagged PDF/UA-1: " + ", ".join(offenders)
    )
