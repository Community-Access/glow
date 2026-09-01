"""Regression tests for fix-download MIME types and the webhook SSRF guard."""

from __future__ import annotations

import sys
import types

import pytest

from acb_large_print_web.routes.fix import _FIX_DOWNLOAD_MIMETYPES


def test_fix_download_mimetypes_cover_all_output_formats():
    # Each format a fix can emit must map to its own MIME type, not DOCX.
    assert _FIX_DOWNLOAD_MIMETYPES[".xlsx"].endswith("spreadsheetml.sheet")
    assert _FIX_DOWNLOAD_MIMETYPES[".pptx"].endswith("presentationml.presentation")
    assert _FIX_DOWNLOAD_MIMETYPES[".pdf"] == "application/pdf"
    assert _FIX_DOWNLOAD_MIMETYPES[".epub"] == "application/epub+zip"
    assert _FIX_DOWNLOAD_MIMETYPES[".md"].startswith("text/markdown")
    docx = _FIX_DOWNLOAD_MIMETYPES[".docx"]
    # Every mapping is distinct from DOCX except .docx itself.
    non_docx = {k: v for k, v in _FIX_DOWNLOAD_MIMETYPES.items() if k != ".docx"}
    assert docx not in non_docx.values()


@pytest.fixture
def _stub_requests(monkeypatch):
    """Replace the ``requests`` module with a call-recording stub."""
    calls = []
    stub = types.ModuleType("requests")

    def _post(url, *a, **k):
        calls.append(url)
        return types.SimpleNamespace(status_code=200)

    stub.post = _post
    monkeypatch.setitem(sys.modules, "requests", stub)
    return calls


def test_fire_webhook_rejects_non_https_scheme(_stub_requests):
    from acb_large_print_web.routes.audit import _fire_webhook

    # Case-varying scheme must not bypass the https requirement.
    _fire_webhook("HTTP://example.com/hook", {"event": "audit.complete"})
    assert _stub_requests == []


def test_fire_webhook_rejects_private_and_internal_hosts(_stub_requests):
    from acb_large_print_web.routes.audit import _fire_webhook

    for url in (
        "https://127.0.0.1/hook",
        "https://localhost/hook",
        "https://169.254.169.254/latest/meta-data",
        "https://10.0.0.5/hook",
    ):
        _fire_webhook(url, {"event": "audit.complete"})
    assert _stub_requests == []
