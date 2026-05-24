"""PageFlow route for reading-mode extraction and narration downloads."""

from __future__ import annotations

from flask import Blueprint, current_app, make_response, render_template, request

from ..app import limiter
from ..listen_later import ArticleExtractionError, extract_article
from ..speech import (
    KOKORO_VOICES,
    PIPER_VOICES,
    SpeechError,
    estimate_audio_seconds_from_text,
    get_engine_status,
    normalize_document_text,
    synthesize_document_text,
    wav_bytes_to_mp3,
)
from ..tool_usage import record_details as _record_usage_details

page_flow_bp = Blueprint("page_flow", __name__)


def _voice_groups(engine_status: dict) -> tuple[list[dict], list[dict]]:
    kokoro = KOKORO_VOICES if engine_status.get("kokoro", {}).get("ready") else []
    piper_ready = set(engine_status.get("piper", {}).get("voices_available", []))
    piper = [voice for voice in PIPER_VOICES if voice["id"] in piper_ready]
    return kokoro, piper


def _default_voice_id(engine_status: dict) -> str:
    if engine_status.get("kokoro", {}).get("ready") and KOKORO_VOICES:
        return f"kokoro:{KOKORO_VOICES[0]['id']}"
    piper_ready = engine_status.get("piper", {}).get("voices_available", [])
    if piper_ready:
        return f"piper:{piper_ready[0]}"
    return ""


def _page_flow_context(**extra):
    engine_status = get_engine_status()
    any_engine_ready = bool(engine_status.get("kokoro", {}).get("ready") or engine_status.get("piper", {}).get("ready"))
    kokoro_voices, piper_voices = _voice_groups(engine_status)
    context = {
        "engine_status": engine_status,
        "any_engine_ready": any_engine_ready,
        "kokoro_voices": kokoro_voices,
        "piper_voices": piper_voices,
        "default_voice_id": _default_voice_id(engine_status),
        "article": None,
        "article_text": "",
        "error": "",
        "source_url": "",
        "title": "",
        "estimated_audio_seconds": 0.0,
    }
    context.update(extra)
    if context.get("article_text"):
        context["estimated_audio_seconds"] = estimate_audio_seconds_from_text(context["article_text"])
    return context


@page_flow_bp.route("/", methods=["GET", "POST"])
def page_flow_form():
    source_url = ""
    error = ""
    article = None
    article_text = ""
    title = ""

    if request.method == "POST":
        source_url = (request.form.get("source_url") or request.form.get("url") or "").strip()
        if not source_url:
            error = "Please enter an article URL."
        else:
            try:
                article = extract_article(source_url)
                article_text = article.text
                title = article.title
                source_url = article.source_url
            except ArticleExtractionError as exc:
                error = str(exc)

    return render_template(
        "page_flow.html",
        **_page_flow_context(
            article=article,
            article_text=article_text,
            error=error,
            source_url=source_url,
            title=title,
        ),
    )


@page_flow_bp.route("/download", methods=["POST"])
@limiter.limit("6 per minute")
def page_flow_download():
    engine_status = get_engine_status()
    any_engine_ready = bool(engine_status.get("kokoro", {}).get("ready") or engine_status.get("piper", {}).get("ready"))
    if not any_engine_ready:
        return (
            render_template(
                "page_flow.html",
                **_page_flow_context(
                    error="Speech synthesis is not available on this server right now.",
                    source_url=(request.form.get("source_url") or "").strip(),
                    title=(request.form.get("title") or "").strip(),
                    article_text=(request.form.get("text") or "").strip(),
                ),
            ),
            503,
        )

    text = normalize_document_text(request.form.get("text") or "")
    title = (request.form.get("title") or "PageFlow").strip() or "PageFlow"
    voice_id = (request.form.get("voice") or _default_voice_id(engine_status)).strip()
    speed = 1.0
    pitch = 0

    if not text:
        return (
            render_template(
                "page_flow.html",
                **_page_flow_context(
                    error="The article text is empty.",
                    source_url=(request.form.get("source_url") or "").strip(),
                    title=title,
                    article_text="",
                ),
            ),
            400,
        )

    try:
        wav_bytes, wav_filename = synthesize_document_text(voice_id, text, speed=speed, pitch=pitch)
    except SpeechError as exc:
        return (
            render_template(
                "page_flow.html",
                **_page_flow_context(
                    error=str(exc),
                    source_url=(request.form.get("source_url") or "").strip(),
                    title=title,
                    article_text=text,
                ),
            ),
            503,
        )

    from ..tool_usage import record_details as _record_usage_details

    _record_usage_details(
        "page_flow",
        {
            "mode": "article_download",
            "voice": voice_id,
            "title": title[:120],
            "length": str(len(text)),
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