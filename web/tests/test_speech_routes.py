"""Speech Studio route and extraction behavior tests."""

from __future__ import annotations

import io
import uuid
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
from acb_large_print_web.upload import UploadError
import acb_large_print_web.routes.speech as speech_route


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


def test_speech_page_renders_next_prepare_button(client):
    resp = client.get("/speech/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Next: Prepare text and estimate" in body


def test_speech_page_hides_post_prepare_actions_initially(client):
    resp = client.get("/speech/")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'id="document-after-prepare-actions" class="next-step-actions" hidden' in body
    assert "Preview first sentences" in body
    assert "Download full document audio" in body


def test_extract_document_text_txt_bypasses_pandoc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source = tmp_path / "sample.txt"
    source.write_text("Alpha\nBeta", encoding="utf-8")

    monkeypatch.setattr(speech_route, "pandoc_available", lambda: False)

    text = speech_route._extract_document_text(source)
    assert text == "Alpha\nBeta"


def test_extract_document_text_requires_pandoc_for_markdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = tmp_path / "sample.md"
    source.write_text("# Title\n\nParagraph.", encoding="utf-8")

    monkeypatch.setattr(speech_route, "pandoc_available", lambda: False)

    with pytest.raises(UploadError, match="Pandoc is required"):
        speech_route._extract_document_text(source)


def test_extract_document_text_markdown_uses_pandoc_render(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source = tmp_path / "sample.md"
    source.write_text("# Heading\n\nBody.", encoding="utf-8")

    monkeypatch.setattr(speech_route, "pandoc_available", lambda: True)

    def _fake_render(md_input: Path, txt_output: Path) -> None:
        assert md_input == source
        txt_output.write_text("Rendered plain text", encoding="utf-8")

    monkeypatch.setattr(speech_route, "_render_markdown_to_text_with_pandoc", _fake_render)

    text = speech_route._extract_document_text(source)
    assert text == "Rendered plain text"


def test_speech_prepare_returns_pandoc_error_when_unavailable_for_md(
    client, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(speech_route, "pandoc_available", lambda: False)

    resp = client.post(
        "/speech/prepare",
        data={
            "document": (io.BytesIO(b"# Title\n\nTest body"), "sample.md"),
            "speed": "1.0",
        },
        content_type="multipart/form-data",
    )

    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload is not None
    assert "Pandoc is required" in payload.get("error", "")


def test_speech_prepare_persists_rendered_and_normalized_text(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    token = str(uuid.uuid4())
    temp_dir = tmp_path / token
    temp_dir.mkdir(parents=True, exist_ok=True)

    source_path = temp_dir / "source.docx"
    source_path.write_bytes(b"fake-docx-content")

    monkeypatch.setattr(
        speech_route,
        "_resolve_document_source",
        lambda: (token, source_path, "source.docx"),
    )
    monkeypatch.setattr(speech_route, "get_temp_dir", lambda _t: temp_dir)
    monkeypatch.setattr(
        speech_route,
        "_extract_document_text",
        lambda _path: "Title\n\nLine one.\n\nLine two.",
    )

    resp = client.post("/speech/prepare", data={"speed": "1.0"})
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload is not None
    assert payload.get("ok") is True

    rendered = temp_dir / "speech_rendered.txt"
    normalized = temp_dir / "speech_source.txt"
    assert rendered.exists()
    assert normalized.exists()
    assert "Line one." in rendered.read_text(encoding="utf-8")
    assert normalized.read_text(encoding="utf-8").strip() != ""


def test_speech_prepare_propagates_extract_upload_error(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    token = str(uuid.uuid4())
    temp_dir = tmp_path / token
    temp_dir.mkdir(parents=True, exist_ok=True)

    source_path = temp_dir / "source.docx"
    source_path.write_bytes(b"fake")

    monkeypatch.setattr(
        speech_route,
        "_resolve_document_source",
        lambda: (token, source_path, "source.docx"),
    )
    monkeypatch.setattr(speech_route, "get_temp_dir", lambda _t: temp_dir)

    def _raise_extract(_path: Path) -> str:
        raise UploadError("Pandoc is required for Speech Studio document preparation")

    monkeypatch.setattr(speech_route, "_extract_document_text", _raise_extract)

    resp = client.post("/speech/prepare", data={"speed": "1.0"})
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload is not None
    assert "Pandoc is required" in payload.get("error", "")


def test_speech_stream_respects_feature_flag(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        speech_route,
        "_speech_flag",
        lambda name, default=True: False if name == "GLOW_ENABLE_SPEECH_STREAM" else True,
    )

    res = client.post(
        "/speech/stream",
        data={"voice": "kokoro:af_bella", "text": "hello"},
    )
    assert res.status_code == 403
    payload = res.get_json()
    assert payload is not None
    assert "disabled" in payload.get("error", "").lower()


def test_speech_stream_uses_pronunciation_dictionary(client, monkeypatch: pytest.MonkeyPatch):
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        speech_route,
        "_speech_flag",
        lambda name, default=True: True,
    )
    monkeypatch.setattr(
        speech_route,
        "_apply_pronunciation_dictionary_if_enabled",
        lambda text: text.replace("GLOW", "glow"),
    )

    def _fake_synthesize(voice_id: str, text: str, *, speed: float, pitch: int):
        captured["text"] = text
        return b"RIFF....WAVE", "sample.wav"

    monkeypatch.setattr(speech_route, "synthesize", _fake_synthesize)

    res = client.post(
        "/speech/stream",
        data={"voice": "kokoro:af_bella", "text": "GLOW toolkit", "speed": "1.0", "pitch": "0"},
    )
    assert res.status_code == 200
    assert res.headers.get("Content-Type", "").startswith("audio/wav")
    assert captured.get("text") == "glow toolkit"


def test_speech_download_queues_job(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(speech_route, "_ASYNC_SPEECH_ENABLED", True)
    monkeypatch.setattr(speech_route, "_queue_speech_text_job", lambda **kwargs: "/job/queued-typed/")

    res = client.post(
        "/speech/download",
        data={
            "voice": "kokoro:af_bella",
            "text": "Queue this typed speech.",
            "speed": "1.0",
            "pitch": "0",
        },
    )
    assert res.status_code == 202
    payload = res.get_json()
    assert payload is not None
    assert payload.get("queued") is True
    assert payload.get("job_url") == "/job/queued-typed/"


def test_speech_document_download_queues_job(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(speech_route, "_ASYNC_SPEECH_ENABLED", True)
    monkeypatch.setattr(speech_route, "_load_extracted_text", lambda token: "Prepared document text")
    monkeypatch.setattr(speech_route, "_queue_speech_text_job", lambda **kwargs: "/job/queued-doc/")

    res = client.post(
        "/speech/document-download",
        data={
            "token": "11111111-1111-1111-1111-111111111111",
            "voice": "kokoro:af_bella",
            "speed": "1.0",
            "pitch": "0",
        },
    )
    assert res.status_code == 202
    payload = res.get_json()
    assert payload is not None
    assert payload.get("queued") is True
    assert payload.get("job_url") == "/job/queued-doc/"


def test_speech_download_falls_back_to_sync_when_queue_fails(client, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(speech_route, "_ASYNC_SPEECH_ENABLED", True)

    def _raise_queue(**kwargs):
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(speech_route, "_queue_speech_text_job", _raise_queue)
    monkeypatch.setattr(
        speech_route,
        "synthesize",
        lambda voice_id, text, speed, pitch: (b"RIFF....WAVE", "glow-speech-af_bella.wav"),
    )
    monkeypatch.setattr(speech_route, "wav_bytes_to_mp3", lambda wav_bytes: b"MP3DATA")

    res = client.post(
        "/speech/download",
        data={
            "voice": "kokoro:af_bella",
            "text": "fallback to sync",
            "speed": "1.0",
            "pitch": "0",
        },
    )
    assert res.status_code == 200
    assert res.headers.get("Content-Type", "").startswith("audio/mpeg")
