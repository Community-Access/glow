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


def test_speech_document_preview_rejects_whitespace_only_text(client, monkeypatch: pytest.MonkeyPatch):
    """Verify that document-preview rejects whitespace-only preview text (issue #83)."""
    # Mock _load_extracted_text to return whitespace-only content
    monkeypatch.setattr(speech_route, "_load_extracted_text", lambda token: "   \n  \t  ")
    
    # Mock first_sentences to return whitespace (edge case where preview is all whitespace)
    monkeypatch.setattr(speech_route, "first_sentences", lambda text, **kwargs: "   \n  \t  ")
    
    # Try to preview with whitespace-only text
    res = client.post(
        "/speech/document-preview",
        data={
            "token": "some-token",
            "voice": "kokoro:af_bella",
            "speed": "1.0",
            "pitch": "0",
        },
    )
    
    # Should return "No preview text available." instead of trying to synthesize
    assert res.status_code == 400
    data = res.get_json()
    assert data.get("error") == "No preview text available."


def test_speech_preview_rejects_whitespace_after_pronunciation(client, monkeypatch: pytest.MonkeyPatch):
    """Verify that /preview rejects text that becomes whitespace-only after pronunciation dict (issue #83)."""
    # Mock pronunciation dictionary to return whitespace-only result
    monkeypatch.setattr(
        speech_route,
        "_apply_pronunciation_dictionary_if_enabled",
        lambda text: "   \n  \t  ",
    )
    
    res = client.post(
        "/speech/preview",
        data={
            "voice": "kokoro:af_bella",
            "text": "valid input text",
            "speed": "1.0",
            "pitch": "0",
        },
    )
    
    # Should reject whitespace-only result and not try to synthesize
    assert res.status_code == 400
    data = res.get_json()
    assert data.get("error") == "Text must not be empty."


def test_speech_download_rejects_whitespace_after_pronunciation(client, monkeypatch: pytest.MonkeyPatch):
    """Verify that /download rejects text that becomes whitespace-only after pronunciation dict (issue #83)."""
    # Mock pronunciation dictionary to return whitespace-only result
    monkeypatch.setattr(
        speech_route,
        "_apply_pronunciation_dictionary_if_enabled",
        lambda text: "   \n  \t  ",
    )
    
    res = client.post(
        "/speech/download",
        data={
            "voice": "kokoro:af_bella",
            "text": "valid input text",
            "speed": "1.0",
            "pitch": "0",
        },
    )
    
    # Should reject whitespace-only result and not try to synthesize
    assert res.status_code == 400
    data = res.get_json()
    assert data.get("error") == "Text must not be empty."


def test_speech_document_download_rejects_empty_content(client, monkeypatch: pytest.MonkeyPatch):
    """Verify that /document-download rejects extracted text that becomes empty (issue #83)."""
    # Mock _load_extracted_text and pronunciation to return whitespace
    monkeypatch.setattr(speech_route, "_load_extracted_text", lambda token: "   \n  \t  ")
    monkeypatch.setattr(
        speech_route,
        "_apply_pronunciation_dictionary_if_enabled",
        lambda text: "   \n  \t  ",
    )
    
    res = client.post(
        "/speech/document-download",
        data={
            "token": "some-token",
            "voice": "kokoro:af_bella",
            "speed": "1.0",
            "pitch": "0",
        },
    )
    
    # Should reject empty content with proper error message
    assert res.status_code == 400
    data = res.get_json()
    assert data.get("error") == "No content available for speech synthesis."


def test_speech_prefill_flow_quick_start_to_speech(client, tmp_path: Path, monkeypatch):
    """Test the Quick Start → Speech prefill workflow."""
    from acb_large_print_web.upload import validate_upload
    from werkzeug.datastructures import FileStorage
    
    # Mock speech synthesis to avoid needing actual Kokoro models
    monkeypatch.setattr(
        "acb_large_print_web.speech.synthesize_document_text",
        lambda voice_id, text, **kw: (b"\x00\x01\x02\x03", "test.wav")
    )
    
    # Step 1: Simulate Quick Start upload
    txt_content = b"This is a test document for speech conversion.\n\nIt has multiple paragraphs."
    txt_file = FileStorage(
        stream=io.BytesIO(txt_content),
        filename="test.txt",
        content_type="text/plain",
    )
    
    # Upload the file (simulating Quick Start upload)
    with client.session_transaction() as sess:
        app = client.application
        token, saved_path = validate_upload(txt_file, allowed_extensions={".txt"})
        assert saved_path.exists()
        assert token  # Should generate a UUID token
    
    # Step 2: Simulate arriving at Speech Studio with token from Quick Start
    speech_form_resp = client.get(f"/speech/?token={token}")
    assert speech_form_resp.status_code == 200
    body = speech_form_resp.get_data(as_text=True)
    # Should show the prefilled filename
    assert "Ready from Quick Start" in body
    assert "test.txt" in body
    assert f'value="{token}"' in body  # token should be in hidden input
    assert 'value="1"' in body  # prefill flag should be 1
    
    # Step 3: Prepare the document (without uploading a new file, using prefill)
    prepare_resp = client.post(
        "/speech/prepare",
        data={
            "token": token,
            "prefill": "1",
            "voice": "kokoro:af_bella",
            "speed": "1.0",
        },
    )
    # Should succeed
    assert prepare_resp.status_code == 200
    prep_data = prepare_resp.get_json()
    assert prep_data.get("ok")
    assert "preview_text" in prep_data
    assert "char_count" in prep_data
    assert prep_data["char_count"] > 0
    assert "This is a test" in prep_data.get("preview_text", "")
    
    # Step 4: Download should work with the prepared token
    download_resp = client.post(
        "/speech/document-download",
        data={
            "token": token,
            "voice": "kokoro:af_bella",
            "speed": "1.0",
            "pitch": "0",
        },
    )
    # This might be 202 (queued) or 200 with audio, but NOT 400 (empty text error) or 503 (service error)
    assert download_resp.status_code in (200, 202)
    if download_resp.status_code == 200:
        # Should have audio content-type
        assert "audio" in download_resp.content_type or download_resp.data


def test_speech_restores_prepared_state_after_async_prepare(client):
    """Returning to /speech/?token=... after an async prepare restores state.

    Regression for issue #84: the async preparation job redirects back to
    /speech/?token=..., so the GET handler must re-read speech_prepare.json and
    surface the estimate + preview/download actions instead of looking like an
    un-prepared upload (which created an apparent upload loop).
    """
    import json as _json

    from acb_large_print_web.upload import validate_upload
    from werkzeug.datastructures import FileStorage

    txt_file = FileStorage(
        stream=io.BytesIO(b"Sentence one. Sentence two. Sentence three."),
        filename="report.txt",
        content_type="text/plain",
    )
    token, saved_path = validate_upload(txt_file, allowed_extensions={".txt"})
    temp_dir = saved_path.parent

    # Simulate what run_speech_prepare_job persists on success.
    (temp_dir / speech_route._DOC_EXTRACT_NAME).write_text(
        "Sentence one. Sentence two. Sentence three.", encoding="utf-8"
    )
    summary = {
        "token": token,
        "filename": "report.txt",
        "preview_text": "Sentence one. Sentence two.",
        "char_count": 43,
        "word_count": 6,
        "estimate_audio_seconds": 3.2,
        "estimate_processing_seconds": 4.5,
        "continue_url": f"/speech/?token={token}",
    }
    (temp_dir / speech_route._DOC_PREPARE_NAME).write_text(
        _json.dumps(summary), encoding="utf-8"
    )

    resp = client.get(f"/speech/?token={token}")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    # Prepared summary is embedded for the JS to restore.
    assert 'id="speech-prepared-data"' in body
    assert "Sentence one. Sentence two." in body
    # The original upload, not an internal generated file, is shown as ready.
    assert "report.txt" in body
    assert speech_route._DOC_EXTRACT_NAME not in body
    assert speech_route._DOC_PREPARE_NAME not in body


def test_speech_ignores_mismatched_prepared_summary(client):
    """A speech_prepare.json from a different token must not be restored."""
    import json as _json

    from acb_large_print_web.upload import validate_upload
    from werkzeug.datastructures import FileStorage

    txt_file = FileStorage(
        stream=io.BytesIO(b"Hello world."),
        filename="doc.txt",
        content_type="text/plain",
    )
    token, saved_path = validate_upload(txt_file, allowed_extensions={".txt"})
    temp_dir = saved_path.parent
    (temp_dir / speech_route._DOC_EXTRACT_NAME).write_text("Hello world.", encoding="utf-8")
    (temp_dir / speech_route._DOC_PREPARE_NAME).write_text(
        _json.dumps({"token": "some-other-token", "filename": "doc.txt"}),
        encoding="utf-8",
    )

    resp = client.get(f"/speech/?token={token}")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'id="speech-prepared-data"' not in body
