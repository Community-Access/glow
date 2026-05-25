from __future__ import annotations

import io
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
from acb_large_print_web.routes.consent import CONSENT_COOKIE_NAME
import acb_large_print_web.routes.audit as audit_route
import acb_large_print_web.routes.export as export_route
import acb_large_print_web.routes.fix as fix_route
import acb_large_print_web.routes.speech as speech_route
import acb_large_print_web.routes.template as template_route


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app(
        {
            "TESTING": False,
            "WTF_CSRF_ENABLED": False,
            "MAX_CONTENT_LENGTH": 50 * 1024 * 1024,
        }
    )
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    return application


@pytest.fixture()
def client(app: Flask):
    c = app.test_client()
    c.set_cookie(CONSENT_COOKIE_NAME, "1")
    return c


def test_template_submit_queues_job(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(template_route, "_ASYNC_HEAVY_ENABLED", True)
    monkeypatch.setattr(template_route, "create_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(template_route, "run_template_job", type("X", (), {"delay": staticmethod(lambda *args, **kwargs: None)})())

    resp = client.post(
        "/template/",
        data={
            "title": "Queued Template",
            "bound": "on",
            "include_sample": "on",
        },
    )

    assert resp.status_code == 302
    assert "/job/" in resp.headers.get("Location", "")


def test_export_submit_queues_job(client, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(export_route, "_ASYNC_HEAVY_ENABLED", True)
    monkeypatch.setattr(export_route, "create_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(export_route, "run_export_job", type("X", (), {"delay": staticmethod(lambda *args, **kwargs: None)})())
    fake_doc = tmp_path / "sample.docx"
    fake_doc.write_bytes(b"PK\x03\x04fake-docx")
    monkeypatch.setattr(export_route, "validate_upload", lambda _upload: ("tok", fake_doc))

    resp = client.post(
        "/export/",
        data={
            "document": (io.BytesIO(b"fake docx"), "sample.docx"),
            "mode": "standalone",
            "title": "Queued Export",
        },
        content_type="multipart/form-data",
    )

    assert resp.status_code == 302
    assert "/job/" in resp.headers.get("Location", "")


def test_speech_prepare_queues_job(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(speech_route, "_ASYNC_SPEECH_ENABLED", True)
    monkeypatch.setattr(speech_route, "create_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(speech_route, "run_speech_prepare_job", type("X", (), {"delay": staticmethod(lambda *args, **kwargs: None)})())
    monkeypatch.setattr(speech_route, "_resolve_document_source", lambda: ("tok", Path("sample.docx"), "sample.docx"))

    resp = client.post(
        "/speech/prepare",
        data={
            "speed": "1.0",
        },
    )

    assert resp.status_code == 202
    payload = resp.get_json()
    assert payload is not None
    assert payload.get("queued") is True
    assert "/job/" in (payload.get("job_url") or "")


def test_audit_submit_queues_single_job(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(audit_route, "_ASYNC_HEAVY_ENABLED", True)
    monkeypatch.setattr(audit_route, "create_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(audit_route, "run_audit_job", type("X", (), {"delay": staticmethod(lambda *args, **kwargs: None)})())

    resp = client.post(
        "/audit/",
        data={
            "document": (io.BytesIO(b"# heading\n\nbody"), "sample.md"),
            "upload_mode": "single",
            "mode": "full",
            "standards_profile": "acb_2025",
            "category": ["acb", "msac"],
        },
        content_type="multipart/form-data",
    )

    assert resp.status_code == 302
    assert "/job/" in resp.headers.get("Location", "")


def test_fix_submit_queues_non_review_job(client, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setattr(fix_route, "_ASYNC_HEAVY_ENABLED", True)
    monkeypatch.setattr(fix_route, "create_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(fix_route, "run_fix_job", type("X", (), {"delay": staticmethod(lambda *args, **kwargs: None)})())
    fake_doc = tmp_path / "sample.docx"
    fake_doc.write_bytes(b"PK\x03\x04fake-docx")
    monkeypatch.setattr(fix_route, "validate_upload", lambda _upload: ("tok", fake_doc))
    monkeypatch.setattr(fix_route, "_parse_form_options", lambda form: {
        "bound": False,
        "mode": "full",
        "list_indent_in": 0.5,
        "list_hanging_in": 0.25,
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
        "allowed_heading_levels": [1, 2, 3],
        "style_size_overrides": None,
        "rule_policy": None,
    })

    resp = client.post(
        "/fix/",
        data={
            "document": (io.BytesIO(b"fake docx"), "sample.docx"),
            "mode": "full",
        },
        content_type="multipart/form-data",
    )

    assert resp.status_code == 302
    assert "/job/" in resp.headers.get("Location", "")
