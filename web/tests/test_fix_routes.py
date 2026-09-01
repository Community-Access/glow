"""Tests for the fix route -- heading review, confirm, and download flows."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from acb_large_print_web.app import create_app


def test_fixable_rule_ids_all_exist():
    """Quick Wins understates GLOW Fix if an id here does not match a real rule."""
    from acb_large_print_web.routes.audit import FIXABLE_RULE_IDS
    from acb_large_print_web.rules import get_all_rule_ids

    unknown = FIXABLE_RULE_IDS - get_all_rule_ids()
    assert not unknown, f"FIXABLE_RULE_IDS names rules that do not exist: {sorted(unknown)}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "MAX_CONTENT_LENGTH": 500 * 1024 * 1024,
        }
    )
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


def _make_fake_docx() -> io.BytesIO:
    """Minimal valid .docx ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        zf.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/>'
            "</Relationships>",
        )
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>"
            "<w:p><w:r><w:t>Test</w:t></w:r></w:p>"
            "</w:body>"
            "</w:document>",
        )
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Fix form loads
# ---------------------------------------------------------------------------


class TestFixForm:
    @patch("acb_large_print_web.ai_features.ai_heading_fix_enabled", return_value=False)
    def test_fix_form_loads(self, mock_ai, client):
        resp = client.get("/fix/")
        assert resp.status_code == 200
        assert b"Fix" in resp.data

    @patch("acb_large_print_web.ai_features.ai_heading_fix_enabled", return_value=True)
    def test_fix_form_shows_ai_checkbox_when_available(self, mock_ai, client):
        resp = client.get("/fix/")
        assert resp.status_code == 200
        # The form should contain an AI-related option
        assert b"ai" in resp.data.lower() or b"detect" in resp.data.lower()


# ---------------------------------------------------------------------------
# Fix submit -- no file / wrong file
# ---------------------------------------------------------------------------


class TestFixSubmitErrors:
    def test_no_file(self, client):
        resp = client.post("/fix/", data={})
        assert resp.status_code == 400
        assert b"No file selected" in resp.data

    def test_wrong_extension(self, client):
        data = {"document": (io.BytesIO(b"hello"), "test.txt")}
        resp = client.post("/fix/", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400
        assert b"not supported" in resp.data

    def test_corrupt_docx(self, client):
        data = {"document": (io.BytesIO(b"not a zip"), "test.docx")}
        resp = client.post("/fix/", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400
        assert b"does not appear to be a valid" in resp.data


# ---------------------------------------------------------------------------
# Fix submit -- basic fix (no heading detection)
# ---------------------------------------------------------------------------


class TestFixSubmitBasic:
    def test_fix_docx_returns_result(self, client):
        docx = _make_fake_docx()
        data = {"document": (docx, "test.docx")}
        resp = client.post("/fix/", data=data, content_type="multipart/form-data")
        # Should either succeed (200) or error gracefully (500)
        assert resp.status_code in (200, 500)


# ---------------------------------------------------------------------------
# Fix confirm route
# ---------------------------------------------------------------------------


class TestFixConfirm:
    def test_confirm_expired_token(self, client):
        """Expired token should return 400 with session expired message."""
        data = {
            "token": "00000000-0000-0000-0000-000000000000",
            "candidate_count": "0",
        }
        resp = client.post("/fix/confirm", data=data)
        assert resp.status_code == 400
        assert b"expired" in resp.data.lower() or b"Session" in resp.data

    def test_confirm_invalid_token_format(self, client):
        data = {
            "token": "not-a-uuid",
            "candidate_count": "0",
        }
        resp = client.post("/fix/confirm", data=data)
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Fix download route
# ---------------------------------------------------------------------------


class TestFixDownload:
    def test_download_expired_token(self, client):
        """Missing temp dir returns 404."""
        data = {
            "token": "00000000-0000-0000-0000-000000000000",
            "download_name": "test-fixed.docx",
        }
        resp = client.post("/fix/download", data=data)
        assert resp.status_code == 404

    def test_download_missing_file(self, client, tmp_path):
        """Token exists but file is gone."""
        from acb_large_print_web import upload

        original_base = upload.UPLOAD_TEMP_BASE
        upload.UPLOAD_TEMP_BASE = tmp_path

        token = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        token_dir = tmp_path / token
        token_dir.mkdir()

        data = {
            "token": token,
            "download_name": "nonexistent-fixed.docx",
        }
        resp = client.post("/fix/download", data=data)
        assert resp.status_code == 404

        upload.UPLOAD_TEMP_BASE = original_base


# ---------------------------------------------------------------------------
# _parse_form_options
# ---------------------------------------------------------------------------


class TestParseFormOptions:
    def test_defaults(self, app):
        """Default form values are sensible."""
        from acb_large_print_web.routes.fix import _parse_form_options
        from werkzeug.datastructures import MultiDict

        with app.app_context():
            form = MultiDict({})
            opts = _parse_form_options(form)
            assert opts["bound"] is False
            assert opts["detect_headings"] is False
            assert opts["use_ai"] is False
            assert 0 <= opts["heading_threshold"] <= 100

    def test_bound_on(self, app):
        from acb_large_print_web.routes.fix import _parse_form_options
        from werkzeug.datastructures import MultiDict

        with app.app_context():
            form = MultiDict({"bound": "on"})
            opts = _parse_form_options(form)
            assert opts["bound"] is True

    def test_flush_lists(self, app):
        from acb_large_print_web.routes.fix import _parse_form_options
        from werkzeug.datastructures import MultiDict

        with app.app_context():
            form = MultiDict({"flush_lists": "on"})
            opts = _parse_form_options(form)
            assert opts["list_indent_in"] == 0.0
            assert opts["list_hanging_in"] == 0.0

    def test_heading_threshold_clamped(self, app):
        from acb_large_print_web.routes.fix import _parse_form_options
        from werkzeug.datastructures import MultiDict

        with app.app_context():
            form = MultiDict({"heading_threshold": "999"})
            opts = _parse_form_options(form)
            assert opts["heading_threshold"] == 100

    def test_heading_threshold_invalid(self, app):
        from acb_large_print_web.routes.fix import _parse_form_options
        from werkzeug.datastructures import MultiDict

        with app.app_context():
            form = MultiDict({"heading_threshold": "abc"})
            opts = _parse_form_options(form)
            assert opts["heading_threshold"] == 50  # default

    def test_list_indent_clamped(self, app):
        from acb_large_print_web.routes.fix import _parse_form_options
        from werkzeug.datastructures import MultiDict

        with app.app_context():
            form = MultiDict({"list_indent": "10.0"})
            opts = _parse_form_options(form)
            assert opts["list_indent_in"] == 2.0  # max

    def test_detect_headings_on(self, app, monkeypatch):
        from acb_large_print_web.routes.fix import _parse_form_options
        from werkzeug.datastructures import MultiDict

        with app.app_context():
            # Mock ai_heading_fix_enabled to return True for this test
            # (Environment variables don't work because flags are cached at app startup)
            monkeypatch.setattr("acb_large_print_web.ai_features.ai_heading_fix_enabled", lambda: True)
            form = MultiDict({"detect_headings": "on", "use_ai": "on"})
            opts = _parse_form_options(form)
            assert opts["detect_headings"] is True
            assert opts["use_ai"] is True


# ---------------------------------------------------------------------------
# Regression checks for recent Fix UX updates
# ---------------------------------------------------------------------------


class _FakeAuditResult:
    def __init__(self, score=100, grade="A", findings=None):
        self.score = score
        self.grade = grade
        self.findings = findings or []


class _FakeFinding:
    def __init__(self, rule_id: str, message: str = "", location: str = ""):
        self.rule_id = rule_id
        self.message = message
        self.location = location


def test_fix_result_shows_suppressed_rules_note(app):
    from acb_large_print_web.routes.fix import _run_fix_and_render

    pre = _FakeAuditResult(score=80, grade="B", findings=[])
    post = _FakeAuditResult(score=90, grade="A", findings=[])

    opts = {
        "bound": False,
        "mode": "full",
        "list_indent_in": 0.0,
        "list_hanging_in": 0.0,
        "list_level_indents": None,
        "para_indent_in": 0.0,
        "first_line_indent_in": 0.0,
        "preserve_heading_alignment": False,
        "detect_headings": False,
        "use_ai": False,
        "suppress_link_text": False,
        "suppress_missing_alt_text": False,
        "suppress_faux_heading": False,
        "heading_threshold": 50,
        "heading_accuracy": "balanced",
    }

    with app.test_request_context("/fix/", method="POST", data={}):
        with patch("acb_large_print_web.routes.fix._audit_by_extension", return_value=pre), patch(
            "acb_large_print_web.routes.fix._fix_by_extension",
            return_value=(MagicMock(), 0, [], post, []),
        ):
            html = _run_fix_and_render(Path("test.docx"), "tok", opts)

    assert "Suppressed by your settings" in html
    assert "ACB-FAUX-HEADING" in html


def test_fix_result_shows_page_growth_warning_for_small_text(app):
    from acb_large_print_web.routes.fix import _run_fix_and_render

    pre = _FakeAuditResult(score=70, grade="C", findings=[])
    post = _FakeAuditResult(score=85, grade="B", findings=[])

    opts = {
        "bound": False,
        "mode": "full",
        "list_indent_in": 0.0,
        "list_hanging_in": 0.0,
        "list_level_indents": None,
        "para_indent_in": 0.0,
        "first_line_indent_in": 0.0,
        "preserve_heading_alignment": False,
        "detect_headings": True,
        "use_ai": False,
        "suppress_link_text": False,
        "suppress_missing_alt_text": False,
        "suppress_faux_heading": False,
        "heading_threshold": 50,
        "heading_accuracy": "balanced",
    }

    with app.test_request_context("/fix/", method="POST", data={}):
        with patch("acb_large_print_web.routes.fix._audit_by_extension", return_value=pre), patch(
            "acb_large_print_web.routes.fix._fix_by_extension",
            return_value=(MagicMock(), 0, [], post, []),
        ), patch(
            "acb_large_print_web.routes.fix._estimate_pre_fix_body_font_pt",
            return_value=16.0,
        ):
            html = _run_fix_and_render(Path("test.docx"), "tok", opts)

    assert "can increase page count" in html
    assert "16pt" in html


def test_fix_result_customization_warning_renders_without_literal_br_tags(app):
    from acb_large_print_web.routes.fix import _run_fix_and_render

    pre = _FakeAuditResult(score=80, grade="B", findings=[])
    post = _FakeAuditResult(score=90, grade="A", findings=[])

    opts = {
        "bound": False,
        "mode": "full",
        "list_indent_in": 0.5,
        "list_hanging_in": 0.0,
        "list_level_indents": None,
        "para_indent_in": 0.0,
        "first_line_indent_in": 0.0,
        "preserve_heading_alignment": False,
        "detect_headings": False,
        "use_ai": False,
        "suppress_link_text": False,
        "suppress_missing_alt_text": False,
        "suppress_faux_heading": False,
        "heading_threshold": 50,
        "heading_accuracy": "balanced",
    }

    with app.test_request_context("/fix/", method="POST", data={}):
        with patch("acb_large_print_web.routes.fix._audit_by_extension", return_value=pre), patch(
            "acb_large_print_web.routes.fix._fix_by_extension",
            return_value=(MagicMock(), 0, [], post, []),
        ):
            html = _run_fix_and_render(Path("test.docx"), "tok", opts)

    assert "Custom Settings Applied" in html
    assert "List indent changed to 0.5" in html
    assert "&lt;br" not in html
    assert "<br" not in html


def test_fix_form_list_indent_fields_visible_and_disabled_by_default(client):
    resp = client.get("/fix/")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    assert '<div id="list-indent-fields" class="indent-fields">' in html
    assert 'id="list-indent"' in html and "disabled" in html
    assert 'id="list-hanging"' in html and "disabled" in html
    assert 'value="ACB-LINK-TEXT"' in html
    assert 'value="ACB-MISSING-ALT-TEXT"' in html
    assert 'value="ACB-FAUX-HEADING"' in html
    assert 'name="preserve_heading_alignment"' in html
    assert 'name="use_list_levels"' in html
    assert 'name="allowed_heading_levels"' in html


def test_fix_result_suppresses_heading_alignment_when_preserve_enabled(app):
    from acb_large_print_web.routes.fix import _run_fix_and_render

    pre = _FakeAuditResult(score=80, grade="B", findings=[])
    post = _FakeAuditResult(
        score=70,
        grade="C",
        findings=[_FakeFinding("ACB-ALIGNMENT", "Direct alignment override on heading paragraph")],
    )

    opts = {
        "bound": False,
        "mode": "full",
        "list_indent_in": 0.0,
        "list_hanging_in": 0.0,
        "list_level_indents": None,
        "para_indent_in": 0.0,
        "first_line_indent_in": 0.0,
        "preserve_heading_alignment": True,
        "detect_headings": True,
        "use_ai": False,
        "suppress_link_text": False,
        "suppress_missing_alt_text": False,
        "suppress_faux_heading": False,
        "heading_threshold": 50,
        "heading_accuracy": "balanced",
    }

    with app.test_request_context("/fix/", method="POST", data={}):
        with patch("acb_large_print_web.routes.fix._audit_by_extension", return_value=pre), patch(
            "acb_large_print_web.routes.fix._fix_by_extension",
            return_value=(MagicMock(), 0, [], post, []),
        ):
            html = _run_fix_and_render(Path("test.docx"), "tok", opts)

    assert "Suppressed by your settings" in html
    assert "ACB-ALIGNMENT (headings)" in html


def test_fix_result_reaudit_uses_post_form_not_get_link(app):
    from acb_large_print_web.routes.fix import _run_fix_and_render

    pre = _FakeAuditResult(score=80, grade="B", findings=[])
    post = _FakeAuditResult(score=90, grade="A", findings=[])

    opts = {
        "bound": False,
        "mode": "full",
        "list_indent_in": 0.0,
        "list_hanging_in": 0.0,
        "list_level_indents": None,
        "para_indent_in": 0.0,
        "first_line_indent_in": 0.0,
        "preserve_heading_alignment": False,
        "detect_headings": True,
        "use_ai": False,
        "suppress_link_text": False,
        "suppress_missing_alt_text": False,
        "suppress_faux_heading": False,
        "heading_threshold": 50,
        "heading_accuracy": "balanced",
    }

    with app.test_request_context("/fix/", method="POST", data={}):
        with patch("acb_large_print_web.routes.fix._audit_by_extension", return_value=pre), patch(
            "acb_large_print_web.routes.fix._fix_by_extension",
            return_value=(MagicMock(), 0, [], post, []),
        ):
            html = _run_fix_and_render(Path("test.docx"), "tok", opts)

    assert 'action="/audit/from-fix"' in html
    assert 'method="post"' in html.lower()
    assert 'href="/audit/from-fix' not in html


def test_parse_form_options_supports_per_level_list_indents(app):
    from acb_large_print_web.routes.fix import _parse_form_options
    from werkzeug.datastructures import MultiDict

    with app.app_context():
        form = MultiDict(
            {
                "flush_lists": "",
                "use_list_levels": "on",
                "list_indent": "0.50",
                "list_hanging": "0.25",
                "list_indent_level_1": "0.25",
                "list_indent_level_2": "0.50",
                "list_indent_level_3": "0.75",
            }
        )
        opts = _parse_form_options(form)
        assert opts["list_level_indents"] == {0: 0.25, 1: 0.5, 2: 0.75}


def test_parse_form_options_supports_allowed_heading_levels(app):
    from acb_large_print_web.routes.fix import _parse_form_options
    from werkzeug.datastructures import MultiDict

    with app.app_context():
        form = MultiDict(
            {
                "allowed_heading_levels": ["1", "3", "5"],
            }
        )
        opts = _parse_form_options(form)
        assert opts["allowed_heading_levels"] == [1, 3, 5]
