"""Speech Studio route and synthesis endpoints -- v3.0.0.

Provides:
    GET  /speech/                 -- Speech Studio page
    POST /speech/preview          -- synthesize typed text preview, return WAV
    POST /speech/download         -- synthesize typed text, return MP3/WAV attachment
    POST /speech/prepare          -- extract uploaded document text and return estimates
    POST /speech/document-preview -- preview first sentences from extracted document
    POST /speech/document-download -- synthesize full extracted document to MP3/WAV
"""

from __future__ import annotations

import json
import io
import os
import subprocess
import time
import uuid
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    make_response,
    render_template,
    request,
    url_for,
)

from ..core_services import convert_to_markdown
from acb_large_print.pandoc_converter import pandoc_available

from ..app import limiter
from ..speech import (
    KOKORO_VOICES,
    PIPER_VOICES,
    SpeechError,
    estimate_audio_seconds_from_text,
    estimate_processing_seconds_from_text,
    first_sentences,
    get_engine_status,
    normalize_document_text,
    synthesize_document_text,
    synthesize,
    wav_duration_seconds,
    wav_bytes_to_mp3,
)
from ..magic_features import apply_pronunciation_dictionary
from .. import speech_metrics
from ..upload import AUDIO_EXTENSIONS, CONVERT_EXTENSIONS, UploadError, get_temp_dir, validate_upload
from ..upload import UPLOAD_TEMP_BASE
from ..tasks.convert_tasks import create_job, run_speech_prepare_job

speech_bp = Blueprint("speech", __name__)

_ASYNC_SPEECH_ENABLED = os.environ.get("GLOW_CONVERT_ASYNC", "1") == "1"

_TEXT_MAX_LEN = 500
_DOC_EXTRACT_NAME = "speech_source.txt"
_DOC_RENDERED_NAME = "speech_rendered.txt"
_DOC_META_NAME = "speech_meta.json"
_DOC_ALLOWED_EXTENSIONS = (set(CONVERT_EXTENSIONS) - AUDIO_EXTENSIONS - {".zip"}) | {".txt", ".rst"}
_DOC_ACCEPT = ",".join(sorted(_DOC_ALLOWED_EXTENSIONS))
_DEFAULT_DEMO_TEXT = (
    "Welcome to Speech Studio. "
    "Choose a voice, tune speed and pitch, and create clear narration for your audience."
)


def _voice_options(engine_status: dict) -> list[dict]:
    """Return a single combined voice list for all ready engines."""
    options: list[dict] = []

    if engine_status.get("kokoro", {}).get("ready"):
        for voice in KOKORO_VOICES:
            options.append(
                {
                    "value": f"kokoro:{voice['id']}",
                    "label": f"{voice['label']} (Kokoro - {voice['accent']}, {voice['gender']})",
                }
            )

    piper_ready = list(engine_status.get("piper", {}).get("voices_available", []))
    curated_by_id = {voice["id"]: voice for voice in PIPER_VOICES}
    for voice_id in piper_ready:
        curated = curated_by_id.get(voice_id)
        if curated:
            options.append(
                {
                    "value": f"piper:{curated['id']}",
                    "label": f"{curated['label']} (Piper - {curated['accent']}, {curated['gender']})",
                }
            )
            continue
        options.append(
            {
                "value": f"piper:{voice_id}",
                "label": f"{voice_id} (Piper)",
            }
        )

    return options


def _speech_flag(name: str, default: bool = True) -> bool:
    """Return the value of a GLOW feature flag, defaulting to *default* on error."""
    try:
        from .. import feature_flags as _ff
        return bool(_ff.get_all_flags().get(name, default))
    except Exception:
        return default


def _convert_disabled_response():
    return jsonify({"error": "Speech synthesis is currently disabled by the site administrator."}), 403


def _export_disabled_response():
    return jsonify({"error": "Speech export is currently disabled by the site administrator."}), 403


def _apply_pronunciation_dictionary_if_enabled(text: str) -> str:
    if not _speech_flag("GLOW_ENABLE_SPEECH_PRONUNCIATION_DICTIONARY"):
        return text
    try:
        return apply_pronunciation_dictionary(text)
    except Exception:
        return text


# ---------------------------------------------------------------------------
# Speech Studio page
# ---------------------------------------------------------------------------


@speech_bp.route("/", methods=["GET"])
def speech_form():
    status = get_engine_status()
    any_ready = status["kokoro"]["ready"] or status["piper"]["ready"]
    voice_options = _voice_options(status)
    prefill_token = (request.args.get("token") or "").strip()
    prefill_filename = None
    if prefill_token:
        temp_dir = get_temp_dir(prefill_token)
        if temp_dir is not None:
            for f in sorted(temp_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in _DOC_ALLOWED_EXTENSIONS:
                    prefill_filename = f.name
                    break
        if prefill_filename is None:
            prefill_token = ""

    return render_template(
        "speech.html",
        kokoro_voices=KOKORO_VOICES,
        piper_voices=PIPER_VOICES,
        engine_status=status,
        any_engine_ready=any_ready,
        default_text=_DEFAULT_DEMO_TEXT,
        text_max_len=_TEXT_MAX_LEN,
        all_accept=_DOC_ACCEPT,
        prefill_token=prefill_token or None,
        prefill_filename=prefill_filename,
        voice_options=voice_options,
        default_voice_id=(voice_options[0]["value"] if voice_options else ""),
    )


# ---------------------------------------------------------------------------
# Preview -- returns WAV bytes for inline <audio> player via JS fetch
# ---------------------------------------------------------------------------


@speech_bp.route("/preview", methods=["POST"])
@limiter.limit("15 per minute")
def speech_preview():
    if not _speech_flag("GLOW_ENABLE_CONVERT_TO_SPEECH"):
        return _convert_disabled_response()
    voice_id = (request.form.get("voice") or "").strip()
    text = (request.form.get("text") or "").strip()[:_TEXT_MAX_LEN]
    speed = _parse_float(request.form.get("speed"), default=1.0, lo=0.5, hi=2.0)
    pitch = _parse_int(request.form.get("pitch"), default=0, lo=-20, hi=20)

    if not voice_id:
        return jsonify({"error": "No voice selected."}), 400
    if not text:
        return jsonify({"error": "Text must not be empty."}), 400

    text = _apply_pronunciation_dictionary_if_enabled(text)
    if not text or not text.strip():
        return jsonify({"error": "Text must not be empty."}), 400

    try:
        wav_bytes, _ = synthesize(voice_id, text, speed=speed, pitch=pitch)
    except SpeechError as exc:
        return jsonify({"error": str(exc)}), 503

    from ..tool_usage import record_details as _record_usage_details

    _record_usage_details(
        "speech",
        {
            "mode": "typed_preview",
            "voice": voice_id,
            "speed": f"{speed:.1f}",
            "pitch": str(pitch),
        },
    )

    resp = make_response(wav_bytes)
    resp.headers["Content-Type"] = "audio/wav"
    resp.headers["Content-Length"] = len(wav_bytes)
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------------------------------------------------------------------------
# Voice Preview -- quick demo of a voice with default demo text (#10)
# ---------------------------------------------------------------------------


@speech_bp.route("/voice-preview", methods=["POST"])
@limiter.limit("20 per minute")
def voice_preview():
    """Play a quick demo of the selected voice using the default demo text.

    Called when user clicks a voice in the selector to preview that voice.
    Faster rate limit (20/min vs 15/min) because each click is a small request.
    """
    if not _speech_flag("GLOW_ENABLE_CONVERT_TO_SPEECH"):
        return _convert_disabled_response()
    voice_id = (request.form.get("voice") or "").strip()
    if not voice_id:
        return jsonify({"error": "No voice selected."}), 400

    demo_text = _apply_pronunciation_dictionary_if_enabled(_DEFAULT_DEMO_TEXT)
    try:
        wav_bytes, _ = synthesize(voice_id, demo_text, speed=1.0, pitch=0)
    except SpeechError as exc:
        return jsonify({"error": str(exc)}), 503

    from ..tool_usage import record_details as _record_usage_details

    _record_usage_details(
        "speech",
        {
            "mode": "voice_preview",
            "voice": voice_id,
        },
    )

    resp = make_response(wav_bytes)
    resp.headers["Content-Type"] = "audio/wav"
    resp.headers["Content-Length"] = len(wav_bytes)
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------------------------------------------------------------------------
# Download -- returns MP3 (or WAV fallback) as a file attachment
# ---------------------------------------------------------------------------


@speech_bp.route("/download", methods=["POST"])
@limiter.limit("10 per minute")
def speech_download():
    if not _speech_flag("GLOW_ENABLE_EXPORT_SPEECH"):
        return _export_disabled_response()
    voice_id = (request.form.get("voice") or "").strip()
    text = (request.form.get("text") or "").strip()[:_TEXT_MAX_LEN]
    speed = _parse_float(request.form.get("speed"), default=1.0, lo=0.5, hi=2.0)
    pitch = _parse_int(request.form.get("pitch"), default=0, lo=-20, hi=20)

    if not voice_id:
        return jsonify({"error": "No voice selected."}), 400
    if not text:
        return jsonify({"error": "Text must not be empty."}), 400

    text = _apply_pronunciation_dictionary_if_enabled(text)
    if not text or not text.strip():
        return jsonify({"error": "Text must not be empty."}), 400

    if _ASYNC_SPEECH_ENABLED:
        try:
            job_url = _queue_speech_text_job(
                text=text,
                input_filename="speech-typed-input.txt",
                voice_id=voice_id,
                speed=speed,
                pitch=pitch,
                output_format="mp3",
            )
            return (
                jsonify(
                    {
                        "queued": True,
                        "job_url": job_url,
                        "message": "Speech conversion queued.",
                    }
                ),
                202,
            )
        except Exception:
            current_app.logger.exception("Speech typed download queueing failed; falling back to synchronous rendering")

    try:
        wav_bytes, wav_filename = synthesize(voice_id, text, speed=speed, pitch=pitch)
    except SpeechError as exc:
        # Return JSON so the JS fetch() handler can surface the error message
        return jsonify({"error": str(exc)}), 503

    from ..tool_usage import record_details as _record_usage_details

    _record_usage_details(
        "speech",
        {
            "mode": "typed_download",
            "voice": voice_id,
            "speed": f"{speed:.1f}",
            "pitch": str(pitch),
        },
    )

    # Attempt MP3 encoding; fall back to WAV if pydub/ffmpeg unavailable
    mp3_bytes = wav_bytes_to_mp3(wav_bytes)
    if mp3_bytes is not None:
        content = mp3_bytes
        content_type = "audio/mpeg"
        filename = wav_filename.replace(".wav", ".mp3")
    else:
        content = wav_bytes
        content_type = "audio/wav"
        filename = wav_filename

    resp = make_response(content)
    resp.headers["Content-Type"] = content_type
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.headers["Content-Length"] = len(content)
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------------------------------------------------------------------------
# Uploaded document speech workflow
# ---------------------------------------------------------------------------


@speech_bp.route("/prepare", methods=["POST"])
@limiter.limit("20 per minute")
def speech_prepare_document():
    """Extract text from an uploaded document and return synthesis estimates."""
    if not _speech_flag("GLOW_ENABLE_CONVERT_TO_SPEECH"):
        return _convert_disabled_response()
    if _ASYNC_SPEECH_ENABLED and not current_app.config.get("TESTING", False):
        try:
            token, saved_path, filename = _resolve_document_source()
            speed = _parse_float(request.form.get("speed"), default=1.0, lo=0.5, hi=2.0)
            job_id = str(uuid.uuid4())
            create_job(
                job_id,
                "speech_prepare",
                saved_path.name,
                meta={
                    "op": "speech_prepare",
                    "upload_token": token,
                    "input_filename": filename,
                    "speed": speed,
                },
            )
            run_speech_prepare_job.delay(job_id, token, saved_path.name, speed)
            return (
                jsonify(
                    {
                        "queued": True,
                        "job_url": str(url_for("jobs.job_progress", job_id=job_id)),
                        "message": "Speech preparation queued.",
                    }
                ),
                202,
            )
        except Exception:
            current_app.logger.exception("Speech prepare queueing failed; falling back to synchronous processing")
    try:
        token, saved_path, filename = _resolve_document_source()
        text = _extract_document_text(saved_path)
        cleaned = normalize_document_text(text)
        if not cleaned:
            raise UploadError("Could not extract readable text from this file.")

        temp_dir = get_temp_dir(token)
        if temp_dir is None:
            raise UploadError("Upload session not found.")

        extracted_path = temp_dir / _DOC_EXTRACT_NAME
        extracted_path.write_text(cleaned, encoding="utf-8")
        rendered_path = temp_dir / _DOC_RENDERED_NAME
        rendered_path.write_text(text, encoding="utf-8")

        preview_text = first_sentences(cleaned, count=2, max_chars=500)
        words = len(cleaned.split())
        chars = len(cleaned)
        try:
            source_size_bytes = int(saved_path.stat().st_size)
        except OSError:
            source_size_bytes = 0
        speed = _parse_float(request.form.get("speed"), default=1.0, lo=0.5, hi=2.0)
        selected_voice = (request.form.get("voice") or "").strip()
        engine = (selected_voice.split(":", 1)[0] if ":" in selected_voice else "unknown")
        estimate_audio_seconds = estimate_audio_seconds_from_text(cleaned, speed=speed)
        baseline_processing_seconds = estimate_processing_seconds_from_text(cleaned, speed=speed)
        estimate_processing_seconds, estimate_source, estimate_samples = speech_metrics.estimate_processing_seconds(
            engine=engine,
            speed=speed,
            word_count=words,
            char_count=chars,
            source_size_bytes=source_size_bytes,
            baseline_seconds=baseline_processing_seconds,
        )

        meta = {
            "token": token,
            "filename": filename,
            "source_name": saved_path.name,
            "chars": chars,
            "words": words,
            "source_size_bytes": source_size_bytes,
            "estimate_audio_seconds": estimate_audio_seconds,
            "estimate_processing_seconds": estimate_processing_seconds,
            "estimate_source": estimate_source,
            "estimate_samples": estimate_samples,
        }
        (temp_dir / _DOC_META_NAME).write_text(json.dumps(meta, indent=2), encoding="utf-8")

        from ..tool_usage import record_details as _record_usage_details

        _record_usage_details(
            "speech",
            {
                "mode": "document_prepare",
                "source_ext": saved_path.suffix.lower(),
                "speed": f"{speed:.1f}",
            },
        )

        return jsonify(
            {
                "ok": True,
                "token": token,
                "filename": filename,
                "preview_text": preview_text,
                "char_count": chars,
                "word_count": words,
                "estimate_audio_seconds": round(estimate_audio_seconds, 1),
                "estimate_processing_seconds": round(estimate_processing_seconds, 1),
                "estimate_source": estimate_source,
                "estimate_samples": estimate_samples,
                "announcement_interval_seconds": _announcement_interval_seconds(
                    estimate_processing_seconds
                ),
            }
        )
    except UploadError as exc:
        return jsonify({"error": str(exc)}), 400
    except SpeechError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:
        current_app.logger.exception("Speech prepare failed")
        return jsonify({"error": f"Speech preparation failed: {exc}"}), 500


@speech_bp.route("/document-preview", methods=["POST"])
@limiter.limit("12 per minute")
def speech_document_preview():
    """Preview first sentences from extracted document text."""
    if not _speech_flag("GLOW_ENABLE_CONVERT_TO_SPEECH"):
        return _convert_disabled_response()
    token = (request.form.get("token") or "").strip()
    voice_id = (request.form.get("voice") or "").strip()
    speed = _parse_float(request.form.get("speed"), default=1.0, lo=0.5, hi=2.0)
    pitch = _parse_int(request.form.get("pitch"), default=0, lo=-20, hi=20)

    if not token:
        return jsonify({"error": "Missing upload token."}), 400
    if not voice_id:
        return jsonify({"error": "No voice selected."}), 400

    try:
        text = _load_extracted_text(token)
        preview_text = first_sentences(text, count=2, max_chars=500)
        preview_text = _apply_pronunciation_dictionary_if_enabled(preview_text)
        if not preview_text or not preview_text.strip():
            return jsonify({"error": "No preview text available."}), 400
        wav_bytes, _ = synthesize(voice_id, preview_text, speed=speed, pitch=pitch)
    except UploadError as exc:
        return jsonify({"error": str(exc)}), 400
    except SpeechError as exc:
        return jsonify({"error": str(exc)}), 503

    from ..tool_usage import record_details as _record_usage_details

    _record_usage_details(
        "speech",
        {
            "mode": "document_preview",
            "voice": voice_id,
            "speed": f"{speed:.1f}",
            "pitch": str(pitch),
        },
    )

    resp = make_response(wav_bytes)
    resp.headers["Content-Type"] = "audio/wav"
    resp.headers["Content-Length"] = len(wav_bytes)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@speech_bp.route("/document-download", methods=["POST"])
@limiter.limit("6 per minute")
def speech_document_download():
    """Render full extracted document text to speech and return download."""
    if not _speech_flag("GLOW_ENABLE_EXPORT_SPEECH"):
        return _export_disabled_response()
    token = (request.form.get("token") or "").strip()
    voice_id = (request.form.get("voice") or "").strip()
    speed = _parse_float(request.form.get("speed"), default=1.0, lo=0.5, hi=2.0)
    pitch = _parse_int(request.form.get("pitch"), default=0, lo=-20, hi=20)

    if not token:
        return jsonify({"error": "Missing upload token."}), 400
    if not voice_id:
        return jsonify({"error": "No voice selected."}), 400

    try:
        text = _apply_pronunciation_dictionary_if_enabled(_load_extracted_text(token))
    except UploadError as exc:
        return jsonify({"error": str(exc)}), 400

    if not text or not text.strip():
        return jsonify({"error": "No content available for speech synthesis."}), 400

    if _ASYNC_SPEECH_ENABLED:
        try:
            job_url = _queue_speech_text_job(
                text=text,
                input_filename="speech-document-input.txt",
                voice_id=voice_id,
                speed=speed,
                pitch=pitch,
                output_format="mp3",
            )
            return (
                jsonify(
                    {
                        "queued": True,
                        "job_url": job_url,
                        "message": "Document speech conversion queued.",
                    }
                ),
                202,
            )
        except Exception:
            current_app.logger.exception("Speech document download queueing failed; falling back to synchronous rendering")

    try:
        started = time.monotonic()
        wav_bytes, wav_filename = synthesize_document_text(
            voice_id,
            text,
            speed=speed,
            pitch=pitch,
        )
        processing_seconds = max(0.01, time.monotonic() - started)
    except UploadError as exc:
        return jsonify({"error": str(exc)}), 400
    except SpeechError as exc:
        return jsonify({"error": str(exc)}), 503

    word_count = len(normalize_document_text(text).split())
    char_count = len(normalize_document_text(text))
    source_size_bytes = _source_size_for_token(token)
    engine = (voice_id.split(":", 1)[0] if ":" in voice_id else "unknown")
    speech_metrics.record_document_conversion(
        engine=engine,
        voice=voice_id,
        speed=speed,
        pitch=pitch,
        word_count=word_count,
        char_count=char_count,
        source_size_bytes=source_size_bytes,
        processing_seconds=processing_seconds,
        audio_seconds=wav_duration_seconds(wav_bytes),
    )

    from ..tool_usage import record_details as _record_usage_details

    _record_usage_details(
        "speech",
        {
            "mode": "document_download",
            "voice": voice_id,
            "speed": f"{speed:.1f}",
            "pitch": str(pitch),
        },
    )

    mp3_bytes = wav_bytes_to_mp3(wav_bytes)
    if mp3_bytes is not None:
        content = mp3_bytes
        content_type = "audio/mpeg"
        filename = wav_filename.replace(".wav", ".mp3")
    else:
        content = wav_bytes
        content_type = "audio/wav"
        filename = wav_filename

    resp = make_response(content)
    resp.headers["Content-Type"] = content_type
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    resp.headers["Content-Length"] = len(content)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@speech_bp.route("/stream", methods=["POST"])
@limiter.limit("12 per minute")
def speech_stream():
    """2.6 Real-time streaming preview endpoint.

    Returns chunked WAV bytes so playback can start before the full payload
    is buffered by the client.
    """
    if not _speech_flag("GLOW_ENABLE_SPEECH_STREAM"):
        return jsonify({"error": "Streaming preview is disabled by the site administrator."}), 403
    if not _speech_flag("GLOW_ENABLE_CONVERT_TO_SPEECH"):
        return _convert_disabled_response()

    voice_id = (request.form.get("voice") or "").strip()
    text = (request.form.get("text") or "").strip()[:_TEXT_MAX_LEN]
    speed = _parse_float(request.form.get("speed"), default=1.0, lo=0.5, hi=2.0)
    pitch = _parse_int(request.form.get("pitch"), default=0, lo=-20, hi=20)

    if not voice_id:
        return jsonify({"error": "No voice selected."}), 400
    if not text:
        return jsonify({"error": "Text must not be empty."}), 400

    text = _apply_pronunciation_dictionary_if_enabled(text)
    try:
        wav_bytes, _ = synthesize(voice_id, text, speed=speed, pitch=pitch)
    except SpeechError as exc:
        return jsonify({"error": str(exc)}), 503

    def _iter_chunks(data: bytes, chunk_size: int = 32 * 1024):
        for i in range(0, len(data), chunk_size):
            yield data[i : i + chunk_size]

    return Response(
        _iter_chunks(wav_bytes),
        mimetype="audio/wav",
        headers={
            "Cache-Control": "no-store",
            "Transfer-Encoding": "chunked",
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_float(value, *, default: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return default


def _parse_int(value, *, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def _resolve_document_source() -> tuple[str, Path, str]:
    """Resolve document source from either token handoff or fresh upload."""
    token = (request.form.get("token") or "").strip()
    prefill = request.form.get("prefill") == "1"
    if token and prefill:
        temp_dir = get_temp_dir(token)
        if temp_dir is None:
            raise UploadError("Upload session expired. Please upload the file again.")
        for f in sorted(temp_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in _DOC_ALLOWED_EXTENSIONS:
                return token, f, f.name
        raise UploadError("No supported document found for this session.")

    upload = request.files.get("document")
    token, saved_path = validate_upload(upload, allowed_extensions=_DOC_ALLOWED_EXTENSIONS)
    return token, saved_path, saved_path.name


def _extract_document_text(path: Path) -> str:
    """Extract normalized plain text from supported document formats.

    Rendering pipeline by extension:
      .txt          -- direct UTF-8 read (no Pandoc needed)
      .md / .rst    -- Pandoc plain-render (Pandoc required)
      everything else -- MarkItDown → Markdown, then Pandoc plain-render
    """
    ext = path.suffix.lower()
    if ext == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")

    if not pandoc_available():
        raise UploadError(
            "Pandoc is required for Speech Studio document preparation so the source "
            "can be rendered to plain text before narration."
        )

    if ext in {".md", ".rst"}:
        md_input = path
    else:
        md_output = path.with_name(f"{path.stem}-speech-extracted.md")
        _, text = convert_to_markdown(path, output_path=md_output)
        if not text:
            # Fallback to any extracted markdown file text if direct return was empty.
            try:
                text = md_output.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = ""
        md_input = md_output

    txt_output = path.with_name(f"{path.stem}-speech-rendered.txt")
    _render_markdown_to_text_with_pandoc(md_input, txt_output)
    return txt_output.read_text(encoding="utf-8", errors="ignore")


def _render_markdown_to_text_with_pandoc(src_path: Path, output_path: Path) -> None:
    """Render source content to plain text using Pandoc for speech processing."""
    ext = src_path.suffix.lower()
    if ext == ".rst":
        input_format = "rst"
    elif ext == ".md":
        input_format = "gfm"
    else:
        input_format = "markdown"

    cmd = [
        "pandoc",
        "--from",
        input_format,
        "--to",
        "plain",
        "--output",
        str(output_path),
        str(src_path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip() or "Unknown Pandoc error"
        raise UploadError(f"Pandoc text rendering failed: {stderr}")


def _load_extracted_text(token: str) -> str:
    temp_dir = get_temp_dir(token)
    if temp_dir is None:
        raise UploadError("Upload session expired. Please upload the file again.")
    extracted_path = temp_dir / _DOC_EXTRACT_NAME
    if not extracted_path.exists():
        raise UploadError("Document not prepared for speech yet. Click Prepare first.")
    return extracted_path.read_text(encoding="utf-8", errors="ignore")


def _announcement_interval_seconds(estimate_processing_seconds: float) -> int:
    """Return user-friendly status announcement cadence based on estimated runtime."""
    if estimate_processing_seconds <= 30:
        return 10
    if estimate_processing_seconds <= 120:
        return 20
    if estimate_processing_seconds <= 600:
        return 45
    if estimate_processing_seconds <= 1200:
        return 90
    return 150


def _source_size_for_token(token: str) -> int:
    temp_dir = get_temp_dir(token)
    if temp_dir is None:
        return 0
    total = 0
    for f in temp_dir.iterdir():
        if not f.is_file():
            continue
        if f.name in {_DOC_EXTRACT_NAME, _DOC_RENDERED_NAME, _DOC_META_NAME}:
            continue
        try:
            total += int(f.stat().st_size)
        except OSError:
            continue
    return total


def _queue_speech_text_job(
    *,
    text: str,
    input_filename: str,
    voice_id: str,
    speed: float,
    pitch: int,
    output_format: str,
) -> str:
    """Queue a speech conversion job from already-normalized text."""
    from ..tasks.convert_tasks import create_job, run_speech_job

    upload_token = str(uuid.uuid4())
    temp_dir = UPLOAD_TEMP_BASE / upload_token
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / _DOC_EXTRACT_NAME).write_text(text, encoding="utf-8")
    (temp_dir / _DOC_RENDERED_NAME).write_text(text, encoding="utf-8")

    job_id = str(uuid.uuid4())
    create_job(
        job_id,
        "speech",
        input_filename,
        meta={
            "op": "speech",
            "upload_token": upload_token,
            "input_filename": input_filename,
            "voice_id": voice_id,
            "speed": speed,
            "pitch": pitch,
            "output_format": output_format,
        },
    )
    run_speech_job.delay(
        job_id,
        upload_token,
        input_filename,
        voice_id,
        speed,
        pitch,
        output_format,
    )
    return str(url_for("jobs.job_progress", job_id=job_id))
