"""Tests for the PageFlow article extraction and narration routes."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask

import acb_large_print_web.routes.page_flow as page_flow_route
from acb_large_print_web.app import create_app


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


def test_homepage_shows_pageflow_entry(client):
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "PageFlow" in body
    assert "/page-flow/" in body


def test_pageflow_form_renders_extract_button(client):
    resp = client.get("/page-flow/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Extract readable text" in body
    assert "PageFlow" in body


def test_pageflow_extract_renders_text(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        page_flow_route,
        "extract_article",
        lambda source_url: SimpleNamespace(
            source_url=source_url,
            final_url="https://example.com/story?page=2",
            title="Story Title",
            text="First paragraph.\n\nSecond paragraph.",
            page_urls=["https://example.com/story", "https://example.com/story?page=2"],
        ),
    )

    resp = client.post("/page-flow/", data={"source_url": "example.com/story"})
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Readable text" in body
    assert "First paragraph." in body
    assert "Second paragraph." in body
    assert "Combined from 2 pages." in body


def test_pageflow_download_returns_audio_attachment(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        page_flow_route,
        "get_engine_status",
        lambda: {
            "kokoro": {"ready": True, "voices_available": ["af_bella"]},
            "piper": {"ready": False, "voices_available": []},
        },
    )
    monkeypatch.setattr(page_flow_route, "wav_bytes_to_mp3", lambda wav_bytes: b"MP3DATA")
    captured: dict[str, str] = {}

    def _fake_synthesize(voice_id: str, text: str, *, speed: float, pitch: int):
        captured["voice_id"] = voice_id
        captured["text"] = text
        return b"RIFF....WAVE", "glow-speech-document-af_bella.wav"

    monkeypatch.setattr(page_flow_route, "synthesize_document_text", _fake_synthesize)

    resp = client.post(
        "/page-flow/download",
        data={
            "voice": "kokoro:af_bella",
            "title": "Story Title",
            "text": "First paragraph.\n\nSecond paragraph.",
        },
    )

    assert resp.status_code == 200
    assert resp.headers.get("Content-Type", "").startswith("audio/mpeg")
    assert "attachment;" in (resp.headers.get("Content-Disposition") or "")
    assert captured["voice_id"] == "kokoro:af_bella"
    assert "First paragraph." in captured["text"]
