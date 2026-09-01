from __future__ import annotations

import io
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
import acb_large_print_web.routes.magic as magic_route


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "MAX_CONTENT_LENGTH": 50 * 1024 * 1024,
        }
    )
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def test_magic_home_renders(client):
    res = client.get("/magic/")
    assert res.status_code == 200
    assert "Magic Lab" in res.get_data(as_text=True)


def test_table_advisor_requires_text(client):
    res = client.post("/magic/table-advisor", data={})
    assert res.status_code == 400
    payload = res.get_json()
    assert payload is not None
    assert "Provide HTML or Markdown table text" in payload.get("error", "")


def test_table_advisor_returns_findings(client):
    sample = "<table><tr><td>A</td><td>B</td></tr></table>"
    res = client.post("/magic/table-advisor", data={"text": sample})
    assert res.status_code == 200
    payload = res.get_json()
    assert payload is not None
    assert payload.get("status") == "ok"
    assert payload.get("finding_count", 0) >= 1


def test_table_advisor_respects_feature_flag(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        magic_route,
        "get_all_flags",
        lambda: {"GLOW_ENABLE_TABLE_ADVISOR": False},
    )
    res = client.post("/magic/table-advisor", data={"text": "|A|B|\n|---|---|\n|1|2|"})
    assert res.status_code == 404


def test_pronunciation_crud_preview_export(client):
    upsert = client.post(
        "/magic/pronunciation",
        data={"term": "GLOW", "replacement": "glow", "notes": "brand"},
    )
    assert upsert.status_code == 200

    preview = client.post(
        "/magic/pronunciation/preview",
        data={"text": "GLOW toolkit"},
    )
    assert preview.status_code == 200
    payload = preview.get_json()
    assert payload is not None
    assert payload.get("text") == "glow toolkit"

    export = client.get("/magic/pronunciation/export.csv")
    assert export.status_code == 200
    csv_text = export.get_data(as_text=True)
    assert "term,replacement,notes,updated_at" in csv_text
    assert "GLOW,glow,brand" in csv_text

    delete = client.post("/magic/pronunciation/delete", data={"term": "GLOW"})
    assert delete.status_code == 200


def test_rule_proposal_submit_and_list(client):
    submit = client.post(
        "/magic/rules/propose",
        data={
            "title": "Add contrast warning",
            "rationale": "Need stronger color checks",
            "severity": "high",
            "suggested_rule_id": "ACB-COLOR-CONTRAST",
            "submitted_by": "qa@example.org",
        },
    )
    assert submit.status_code == 200
    payload = submit.get_json()
    assert payload is not None
    assert payload.get("ok") is True
    assert isinstance(payload.get("proposal_id"), int)

    listing = client.get("/magic/rules/proposals")
    assert listing.status_code == 200
    payload = listing.get_json()
    assert payload is not None
    assert payload.get("ok") is True
    assert any(p.get("title") == "Add contrast warning" for p in payload.get("proposals", []))


def test_compare_accepts_txt_and_returns_diff(client):
    res = client.post(
        "/magic/compare",
        data={
            "document_a": (io.BytesIO(b"alpha\nbravo\n"), "a.txt"),
            "document_b": (io.BytesIO(b"alpha\ncharlie\n"), "b.txt"),
        },
        content_type="multipart/form-data",
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload is not None
    assert payload.get("status") == "ok"
    assert "diff_preview" in payload


def test_ocr_and_reading_order_flags_respected(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        magic_route,
        "get_all_flags",
        lambda: {
            "GLOW_ENABLE_PDF_OCR": False,
            "GLOW_ENABLE_READING_ORDER_DETECTION": False,
        },
    )

    ocr_res = client.post("/magic/ocr", data={})
    ro_res = client.post("/magic/reading-order", data={})
    assert ocr_res.status_code == 404
    assert ro_res.status_code == 404


# ---------------------------------------------------------------------------
# magic_features unit-level regression tests (findings 6-9)
# ---------------------------------------------------------------------------

from acb_large_print_web import magic_features


def test_pronunciation_backslash_replacement_is_literal(app):
    """Finding 6: a replacement containing regex escapes (\\g, \\1) must be
    treated literally and must not raise re.error."""
    with app.app_context():
        magic_features.upsert_pronunciation("foo", r"\g<0>\1 bar")
        out = magic_features.apply_pronunciation_dictionary("a foo b")
        assert out == r"a \g<0>\1 bar b"


def test_pronunciation_non_word_edge_term(app):
    """Finding 6: a term with non-word edges ('C++') must still match, since
    \\b never fires between two non-word characters."""
    with app.app_context():
        magic_features.upsert_pronunciation("C++", "C plus plus")
        out = magic_features.apply_pronunciation_dictionary("I love C++ code")
        assert out == "I love C plus plus code"


def test_pronunciation_normal_term_boundaries_preserved(app):
    """Finding 6: normal terms still respect word boundaries (no partial hits)."""
    with app.app_context():
        magic_features.upsert_pronunciation("cat", "feline")
        out = magic_features.apply_pronunciation_dictionary("the cat concatenates")
        assert out == "the feline concatenates"


def test_nested_table_single_is_reported():
    """Finding 7: a single nested table (descendant-only .//table gives len 1)
    must be reported."""
    html = "<table><tr><td><table><tr><td>x</td></tr></table></td></tr></table>"
    result = magic_features.analyze_tables(html)
    codes = [f["code"] for f in result["findings"]]
    assert "TABLE-NESTED" in codes


def test_markdown_blank_header_cell_detected():
    """Finding 8: a blank interior header cell is detected from the raw split."""
    md = "| Name | | Date |\n| --- | --- | --- |\n| a | b | c |\n"
    result = magic_features.analyze_tables(md)
    codes = [f["code"] for f in result["findings"]]
    assert "TABLE-MISSING-HEADERS" in codes


def test_markdown_table_inside_code_fence_skipped():
    """Finding 8: pipe lines inside a fenced code block are not parsed as tables."""
    md = "```\n| only |\n| --- |\n```\n"
    result = magic_features.analyze_tables(md)
    codes = [f["code"] for f in result["findings"]]
    assert "TABLE-TOO-FEW-COLS" not in codes
    assert "TABLE-MISSING-HEADERS" not in codes


def test_extract_text_for_compare_never_deletes_extensionless_input(tmp_path, monkeypatch):
    """Finding 9: for an extensionless upload, the comparison output path must
    differ from the input so the later unlink cannot delete the user's file."""
    src = tmp_path / "uploadnoext"
    src.write_bytes(b"original content")

    def fake_convert(path, output_path):
        output_path.write_text("converted markdown", encoding="utf-8")
        return output_path, None

    monkeypatch.setattr(
        "acb_large_print_web.core_services.convert_to_markdown", fake_convert
    )

    text = magic_features.extract_text_for_compare(src)
    assert text == "converted markdown"
    # The user's original upload survives.
    assert src.exists()
    assert src.read_bytes() == b"original content"
    # The temporary conversion artifact was cleaned up.
    assert not (tmp_path / "uploadnoext.cmp.md").exists()
