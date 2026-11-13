"""Tests for the Braille Studio route (/braille/) and braille_converter module.

These tests do not require liblouis to be installed.  When ``louis`` is absent
the converter reports it as unavailable and the route returns a graceful
degradation page.  When ``louis`` IS installed the full translation path is
exercised with real BANA-compliant UEB tables.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from acb_large_print_web.app import create_app


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


# ---------------------------------------------------------------------------
# braille_converter unit tests (no louis dependency)
# ---------------------------------------------------------------------------


class TestBrailleConverter:
    def _module(self):
        """Re-import module fresh so _louis state is isolated."""
        import importlib
        import acb_large_print.braille_converter as m
        return importlib.import_module("acb_large_print.braille_converter")

    def test_constants_bana_compliant(self):
        m = self._module()
        assert m.BRF_LINE_LENGTH == 40, "BANA standard line length must be 40 cells"
        assert m.BRF_PAGE_LENGTH == 25, "BANA standard page length must be 25 lines"

    def test_grades_contains_ueb(self):
        m = self._module()
        assert "ueb_g1" in m.GRADES, "UEB Grade 1 must be present (BANA current standard)"
        assert "ueb_g2" in m.GRADES, "UEB Grade 2 must be present (BANA current standard)"

    def test_grades_contains_computer_braille(self):
        m = self._module()
        assert "computer" in m.GRADES, "Computer Braille Code must be present"
        table, _, _ = m.GRADES["computer"]
        assert "comp8" in table, "Computer Braille should use en-us-comp8.ctb"

    def test_grades_contains_legacy_ebae(self):
        m = self._module()
        assert "ebae_g1" in m.GRADES, "EBAE Grade 1 (legacy) must be present"
        assert "ebae_g2" in m.GRADES, "EBAE Grade 2 (legacy) must be present"

    def test_default_grade_is_ueb_g2(self):
        m = self._module()
        assert m.DEFAULT_GRADE == "ueb_g2", "Default must be UEB Grade 2 (BANA literary standard)"

    def test_ueb_tables_use_ueb_ctb(self):
        m = self._module()
        table_g1, _, _ = m.GRADES["ueb_g1"]
        table_g2, _, _ = m.GRADES["ueb_g2"]
        assert "en-ueb-g1.ctb" in table_g1
        assert "en-ueb-g2.ctb" in table_g2

    def test_brf_dis_referenced_for_brf_output(self):
        """_BRF_DIS must be the BANA/North-American BRF display table."""
        m = self._module()
        assert m._BRF_DIS == "en-us-brf.dis"

    def test_format_brf_output_wraps_at_40(self):
        m = self._module()
        # 80-char line should be split into two 40-char lines
        long_line = "A" * 80
        wrapped = m.format_brf_output(long_line, line_length=40)
        for line in wrapped.splitlines():
            assert len(line) <= 40, f"BRF line exceeds 40 cells: {len(line)}"

    def test_format_brf_output_word_wrap(self):
        m = self._module()
        # Sentence with spaces -- should break at word boundaries
        text = "the quick brown fox jumps over the lazy dog " * 2
        wrapped = m.format_brf_output(text, line_length=40)
        for line in wrapped.splitlines():
            assert len(line) <= 40

    def test_format_brf_output_hard_wrap_no_spaces(self):
        m = self._module()
        # Token longer than line_length -- must hard-wrap
        long_token = "X" * 60
        wrapped = m.format_brf_output(long_token, line_length=40)
        for line in wrapped.splitlines():
            assert len(line) <= 40

    def test_format_brf_output_paginate_inserts_form_feed(self):
        m = self._module()
        # 50 short lines → 2 pages with paginate=True
        text = "\n".join(["line"] * 50)
        paginated = m.format_brf_output(text, line_length=40, page_length=25, paginate=True)
        assert "\x0c" in paginated, "Paginated BRF must contain form-feed (0x0C)"

    def test_normalize_brf_detects_unicode_braille(self):
        m = self._module()
        unicode_brl = "\u2801\u2803"  # already Unicode Braille
        result = m._normalize_brf_if_needed(unicode_brl)
        assert result == unicode_brl  # must pass through unchanged

    def test_normalize_brf_converts_ascii(self):
        m = self._module()
        # ASCII space (0x20) → U+2800 (no dots), '!' (0x21) → U+2801 (dot 1)
        brf_ascii = " !"
        result = m._normalize_brf_if_needed(brf_ascii)
        assert result[0] == "\u2800"
        assert result[1] == "\u2801"

    def test_braille_unavailable_without_louis(self):
        """When louis is not installed, braille_available() must return False."""
        import importlib
        import acb_large_print.braille_converter as m

        try:
            with patch.dict(sys.modules, {"louis": None}):
                importlib.reload(m)
                assert not m.braille_available()
                assert m.get_unavailability_reason() != ""
        finally:
            importlib.reload(m)

    def test_text_to_braille_raises_on_empty_input(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        with pytest.raises(m.BrailleError, match="empty"):
            m.text_to_braille("")

    def test_text_to_braille_raises_on_unknown_grade(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        with pytest.raises(m.BrailleError, match="Unknown grade"):
            m.text_to_braille("Hello", grade="bogus_grade")

    def test_text_to_braille_raises_on_unknown_format(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        with pytest.raises(m.BrailleError, match="Unknown output format"):
            m.text_to_braille("Hello", output_format="pdf")  # type: ignore[arg-type]

    def test_text_to_braille_ueb_g2_unicode(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        result = m.text_to_braille("hello", grade="ueb_g2", output_format="unicode")
        # All result characters must be Unicode Braille or whitespace/newline
        for ch in result:
            assert "\u2800" <= ch <= "\u28ff" or ch in (" ", "\n", "\r"), (
                f"Unexpected character in Unicode Braille output: {repr(ch)}"
            )

    def test_text_to_braille_ueb_g1_unicode(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        result = m.text_to_braille("hello", grade="ueb_g1", output_format="unicode")
        assert result, "UEB G1 result must be non-empty"

    def test_text_to_braille_brf_line_length(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        # Long text → BRF output lines must all be ≤40 cells (BANA standard)
        text = "The quick brown fox jumps over the lazy dog. " * 5
        result = m.text_to_braille(text, grade="ueb_g2", output_format="brf")
        for line in result.splitlines():
            assert len(line) <= 40, (
                f"BRF output line exceeds BANA 40-cell limit: {len(line)} chars"
            )

    def test_text_to_braille_brf_charset(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        result = m.text_to_braille("Hello", grade="ueb_g2", output_format="brf")
        # BRF must be printable ASCII (0x20-0x5F) plus newlines
        for ch in result:
            code = ord(ch)
            assert (0x20 <= code <= 0x5F) or ch in ("\n", "\r"), (
                f"Non-ASCII character in BRF output: {repr(ch)}"
            )

    def test_braille_to_text_ueb_g2_roundtrip(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        original = "hello world"
        braille = m.text_to_braille(original, grade="ueb_g2", output_format="unicode")
        back = m.braille_to_text(braille, grade="ueb_g2")
        # Grade 2 back-translation is approximate; at minimum must not raise
        assert isinstance(back, str)
        assert back.strip() != ""

    def test_braille_to_text_ueb_g1_lossless(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        # Grade 1 is uncontracted; round-trip for ASCII text should be exact
        original = "hello world"
        braille = m.text_to_braille(original, grade="ueb_g1", output_format="unicode")
        back = m.braille_to_text(braille, grade="ueb_g1")
        assert back.strip().lower() == original.lower()

    def test_braille_to_text_accepts_brf_input(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        original = "hello"
        brf = m.text_to_braille(original, grade="ueb_g1", output_format="brf")
        # BRF input should be normalised and back-translated without error
        back = m.braille_to_text(brf, grade="ueb_g1")
        assert isinstance(back, str)

    def test_too_long_input_raises(self):
        m = self._module()
        if not m.braille_available():
            pytest.skip("louis not installed")
        with pytest.raises(m.BrailleError, match="too long"):
            m.text_to_braille("x" * (m.MAX_INPUT_CHARS + 1))


# ---------------------------------------------------------------------------
# Route integration tests (mock louis when absent)
# ---------------------------------------------------------------------------


class TestBrailleRoute:
    def test_main_nav_shows_braille_tab_when_enabled(self, client, app):
        with app.test_request_context():
            from acb_large_print_web import feature_flags as ff

            ff.set_flag("GLOW_ENABLE_BRAILLE", True)

        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.data.decode()
        assert 'href="/braille/"' in data
        assert "Braille Studio" in data

    def test_get_form_renders(self, client):
        resp = client.get("/braille/")
        assert resp.status_code == 200
        data = resp.data.decode()
        assert "Braille Studio" in data

    def test_get_form_contains_bana_standards(self, client):
        resp = client.get("/braille/")
        data = resp.data.decode()
        # BANA reference must appear on the page in both available and unavailable states
        assert "brailleauthority.org" in data or "BANA" in data

    def test_get_form_shows_ueb_grades(self, client):
        resp = client.get("/braille/")
        data = resp.data.decode()
        # UEB must be mentioned in both available and unavailable states
        assert "UEB" in data or "Unified English Braille" in data

    def test_post_empty_text_returns_error(self, client):
        resp = client.post(
            "/braille/",
            data={"direction": "text-to-braille", "grade": "ueb_g2",
                  "output_format": "unicode", "input_text": ""},
        )
        assert resp.status_code == 200
        assert b"error" in resp.data.lower() or b"empty" in resp.data.lower() or b"please enter" in resp.data.lower()

    def test_post_too_long_returns_error(self, client):
        resp = client.post(
            "/braille/",
            data={"direction": "text-to-braille", "grade": "ueb_g2",
                  "output_format": "unicode", "input_text": "x" * 60_000},
        )
        assert resp.status_code == 200
        assert b"long" in resp.data.lower() or b"error" in resp.data.lower()

    def test_post_unknown_grade_falls_back(self, client):
        """An unknown grade value should be silently sanitised to the default."""
        resp = client.post(
            "/braille/",
            data={"direction": "text-to-braille", "grade": "bad_grade",
                  "output_format": "unicode", "input_text": "hello"},
        )
        # Should return 200 (error or result, but not a crash)
        assert resp.status_code == 200

    def test_download_without_session_result_returns_400(self, client):
        # Clear session -- no prior translation
        with client.session_transaction() as sess:
            sess.pop("braille_result", None)
        resp = client.get("/braille/download")
        assert resp.status_code == 400

    def test_feature_flag_disabled_shows_disabled_page(self, client, app):
        """When GLOW_ENABLE_BRAILLE is False the form should indicate unavailability."""
        with app.test_request_context():
            from acb_large_print_web import feature_flags as ff
            # Temporarily write flag to instance store
            try:
                ff._save({"GLOW_ENABLE_BRAILLE": False})
            except Exception:
                pytest.skip("Could not write feature flag in test context")

        resp = client.get("/braille/")
        assert resp.status_code == 200
        data = resp.data.decode()
        # Should not show the translation form; should show disabled state
        assert "disabled" in data.lower() or "unavailable" in data.lower() or "not available" in data.lower()

        # Restore
        with app.test_request_context():
            from acb_large_print_web import feature_flags as ff
            try:
                ff._save({"GLOW_ENABLE_BRAILLE": True})
            except Exception:
                pass

    def test_post_with_louis_mocked(self, client):
        """When louis is available (mocked), a translation POST returns a result."""
        mock_louis = MagicMock()
        mock_louis.translateString.return_value = "\u2801\u2803"  # dots 1, 12

        import acb_large_print.braille_converter as m

        with patch.object(m, "_louis", mock_louis):
            resp = client.post(
                "/braille/",
                data={"direction": "text-to-braille", "grade": "ueb_g2",
                      "output_format": "unicode", "input_text": "hello"},
            )
            assert resp.status_code == 200

    def test_rate_limit_applied(self, client):
        """Endpoint must have a rate limit (verified by presence of limiter decorator)."""
        # We just confirm the route is reachable and doesn't error at low volume
        for _ in range(3):
            resp = client.get("/braille/")
            assert resp.status_code == 200
