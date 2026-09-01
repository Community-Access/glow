"""PageFlow route for reading-mode extraction and narration downloads."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from flask import Blueprint, current_app, make_response, redirect, render_template, request, url_for

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
from ..upload import UPLOAD_TEMP_BASE
from ..tasks.convert_tasks import _job_dir, read_status, create_job, run_pageflow_extract_job

_ASYNC_SPEECH_ENABLED = os.environ.get("GLOW_CONVERT_ASYNC", "1") == "1"

page_flow_bp = Blueprint("page_flow", __name__)


def _voice_options(engine_status: dict) -> list[dict]:
    options: list[dict] = []

    kokoro = KOKORO_VOICES if engine_status.get("kokoro", {}).get("ready") else []
    for voice in kokoro:
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


def _default_voice_id(engine_status: dict) -> str:
    options = _voice_options(engine_status)
    if options:
        return str(options[0]["value"])
    return ""


def _page_flow_context(**extra):
    engine_status = get_engine_status()
    any_engine_ready = bool(engine_status.get("kokoro", {}).get("ready") or engine_status.get("piper", {}).get("ready"))
    voice_options = _voice_options(engine_status)
    context = {
        "engine_status": engine_status,
        "any_engine_ready": any_engine_ready,
        "voice_options": voice_options,
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
@limiter.limit("6 per minute", methods=["POST"])
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
            if _ASYNC_SPEECH_ENABLED and not current_app.config.get("TESTING", False):
                job_id = str(uuid.uuid4())
                create_job(
                    job_id,
                    "pageflow_extract",
                    source_url,
                    meta={
                        "op": "pageflow_extract",
                        "upload_token": "pageflow",
                        "input_filename": source_url,
                        "source_url": source_url,
                        "max_pages": 5,
                        "follow_pagination": True,
                    },
                )
                run_pageflow_extract_job.delay(job_id, source_url, 5, True)
                return redirect(url_for("jobs.job_progress", job_id=job_id))
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


@page_flow_bp.route("/from-job/<job_id>", methods=["GET"])
def page_flow_from_job(job_id: str):
    status = read_status(job_id)
    if status.get("state") != "SUCCESS":
        return redirect(url_for("jobs.job_progress", job_id=job_id))

    result_file = (status.get("result_file") or "").strip()
    if not result_file:
        return redirect(url_for("jobs.job_progress", job_id=job_id))

    try:
        payload_path = _job_dir(job_id, create=False) / result_file
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except Exception:
        return redirect(url_for("jobs.job_progress", job_id=job_id))

    article = {
        "source_url": payload.get("source_url", ""),
        "final_url": payload.get("final_url", ""),
        "page_urls": payload.get("page_urls", []),
        "text": payload.get("text", ""),
        "title": payload.get("title", "") or "Article",
    }
    return render_template(
        "page_flow.html",
        **_page_flow_context(
            article=article,
            article_text=str(payload.get("text", "")),
            error="",
            source_url=str(payload.get("source_url", "")),
            title=str(payload.get("title", "") or "Article"),
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

    if _ASYNC_SPEECH_ENABLED and not current_app.config.get("TESTING", False):
        try:
            from ..tasks.convert_tasks import create_job, run_speech_job

            upload_token = str(uuid.uuid4())
            temp_dir = UPLOAD_TEMP_BASE / upload_token
            temp_dir.mkdir(parents=True, exist_ok=True)
            (temp_dir / "speech_source.txt").write_text(text, encoding="utf-8")
            (temp_dir / "speech_rendered.txt").write_text(text, encoding="utf-8")

            input_filename = f"{title.replace(' ', '_') or 'pageflow'}.txt"
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
                    "output_format": "mp3",
                },
            )
            run_speech_job.delay(
                job_id,
                upload_token,
                input_filename,
                voice_id,
                speed,
                pitch,
                "mp3",
            )
            return redirect(url_for("jobs.job_progress", job_id=job_id))
        except Exception:
            current_app.logger.exception("PageFlow async speech handoff failed; falling back to sync synthesis")

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