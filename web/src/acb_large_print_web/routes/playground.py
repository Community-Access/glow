"""AI Playground -- open-ended Ollama chat sandbox (Beta).

This route provides a standalone conversational interface for testing
Ollama AI capabilities without a document context.  It is intentionally
simple: no tool-calling, no agentic flow, no document upload.  The goal
is a clean surface for evaluating model behaviour before wiring it into
more complex GLOW workflows.

Routes
------
GET  /beta/chat/        -- Playground page
POST /beta/chat/send    -- Streaming-ready JSON chat endpoint
POST /beta/chat/clear   -- Clear server-side conversation history
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, UTC

from flask import Blueprint, Response, jsonify, render_template, request, session, stream_with_context

from ..ai_features import AIFeatureDisabled, require_ai_feature
from ..app import limiter
from ..credentials import (
    OLLAMA_FEATURE_LABELS,
    OLLAMA_MODEL_RECOMMENDATIONS,
    get_user_ollama_model_for,
    is_ollama_configured,
)

log = logging.getLogger(__name__)

playground_bp = Blueprint("playground", __name__)

_PLAYGROUND_HISTORY_KEY = "playground_history"
_MAX_HISTORY_TURNS = 20       # keep last N user/assistant pairs in session
_MAX_QUESTION_LEN  = 3000
_PLAYGROUND_TEMPLATES = [
    {"id": "summarize", "label": "Summarize this text", "prompt": "Summarize the following text into plain language bullet points for a low-vision audience:\n\n"},
    {"id": "actions", "label": "Extract action items", "prompt": "Extract action items from this content and return an owner/action/deadline table:\n\n"},
    {"id": "plain-language", "label": "Rewrite in plain language", "prompt": "Rewrite this content in plain language at approximately grade 8 reading level:\n\n"},
    {"id": "acb-check", "label": "ACB quick check", "prompt": "Review this content for likely ACB large print issues and list concise fixes:\n\n"},
    {"id": "headings", "label": "Propose heading structure", "prompt": "Suggest a semantic heading structure (H1-H3) for this content:\n\n"},
]
_SYSTEM_PROMPT = (
    "You are a helpful, friendly AI assistant embedded in GLOW -- an "
    "accessibility-focused document workflow tool for the blind and low-vision "
    "community.  Answer clearly and concisely.  When uncertain, say so.  "
    "You are running as an Ollama model supplied by the user for testing purposes."
)


def _session_hash() -> str:
    key = session.get("ollama_api_key", "anon")
    return hashlib.sha256(key.encode()).hexdigest()


# Server-side conversation history, keyed by session hash.
#
# History previously lived only in the signed-cookie session. That worked for
# the plain-request paths (/send, /regenerate) because the Set-Cookie is written
# when the view returns. It silently failed for the SSE stream: Flask builds and
# commits the response cookie *before* the @stream_with_context body iterates, so
# any session write from inside the generator was discarded and every streamed
# turn's history was lost -- the assistant never saw prior context. Persisting
# server-side lets the streaming generator record turns durably.
_server_history: dict[str, list[dict]] = {}
_server_history_lock = threading.Lock()


def _get_history() -> list[dict]:
    key = _session_hash()
    with _server_history_lock:
        if key in _server_history:
            return list(_server_history[key])
    # First touch this process/session: seed the server-side store from whatever
    # the signed cookie carried (preserves history across a restart and keeps the
    # cookie-seeded rendering path working).
    seeded = list(session.get(_PLAYGROUND_HISTORY_KEY, []))
    if seeded:
        with _server_history_lock:
            _server_history[key] = list(seeded)
    return seeded


def _set_history(history: list[dict]) -> None:
    # Trim to last N pairs (each pair = 2 messages)
    turns = _MAX_HISTORY_TURNS * 2
    trimmed = list(history[-turns:])
    key = _session_hash()
    with _server_history_lock:
        _server_history[key] = trimmed
    # Best-effort mirror into the cookie session so history survives a restart.
    # This is a no-op when the response is already committed (the SSE generator),
    # where the server-side store above is the authoritative copy.
    try:
        session[_PLAYGROUND_HISTORY_KEY] = trimmed
        session.modified = True
    except Exception:
        pass


@playground_bp.route("/", methods=["GET"])
def playground_page():
    """Render the AI Playground page."""
    return render_template(
        "beta_chat.html",
        ollama_active=is_ollama_configured(),
        playground_model=get_user_ollama_model_for("playground"),
        model_recommendations=OLLAMA_MODEL_RECOMMENDATIONS,
        prompt_templates=_PLAYGROUND_TEMPLATES,
        feature_label=OLLAMA_FEATURE_LABELS.get("playground", "AI Playground"),
        history=_get_history(),
    )


@playground_bp.route("/send", methods=["POST"])
@limiter.limit("30 per minute")
def playground_send():
    """Process a single chat turn and return the assistant reply as JSON.

    Request (JSON or form):
        message  str   The user's message

    Response (JSON):
        {ok: true,  reply: str, model: str}
        {ok: false, error: str}
    """
    # Gate: Ollama key must be active; playground feature must be enabled
    try:
        require_ai_feature("playground")
    except AIFeatureDisabled as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403

    if not is_ollama_configured():
        return jsonify({"ok": False, "error": "The AI Playground requires your personal Ollama key."}), 403

    raw = request.get_json(silent=True) or {}
    message = (raw.get("message") or request.form.get("message") or "").strip()

    if not message:
        return jsonify({"ok": False, "error": "Message cannot be empty."}), 400
    if len(message) > _MAX_QUESTION_LEN:
        return jsonify({"ok": False, "error": f"Message too long (max {_MAX_QUESTION_LEN} characters)."}), 400

    from ..ai_gateway import chat as gateway_chat
    from ..ai_gateway import get_quota_status, make_session_hash

    history = _get_history()
    sess_hash = _session_hash()
    quota = get_quota_status(sess_hash)
    if quota.get("session_quota_enabled") and not quota.get("session_available", True):
        return jsonify({"ok": False, "error": "This session has reached the current AI request limit. Please wait for the reset window before sending more requests."}), 429

    try:
        reply, _ = gateway_chat(
            question=message,
            system_prompt=_SYSTEM_PROMPT,
            session_hash=sess_hash,
            conversation_history=history,
            feature="playground",
        )
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503

    # Append this turn to history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    _set_history(history)

    model_used = get_user_ollama_model_for("playground")
    return jsonify({"ok": True, "reply": reply, "model": model_used})


@playground_bp.route("/stream", methods=["POST"])
@limiter.limit("30 per minute")
def playground_stream():
    """Process a single chat turn and stream assistant output via SSE.

    Event payloads:
      {"type": "token", "token": "...", "model": "..."}
      {"type": "done", "reply": "...", "model": "..."}
      {"type": "error", "error": "..."}
    """
    try:
        require_ai_feature("playground")
    except AIFeatureDisabled as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403

    if not is_ollama_configured():
        return jsonify({"ok": False, "error": "The AI Playground requires your personal Ollama key."}), 403

    raw = request.get_json(silent=True) or {}
    message = (raw.get("message") or request.form.get("message") or "").strip()

    if not message:
        return jsonify({"ok": False, "error": "Message cannot be empty."}), 400
    if len(message) > _MAX_QUESTION_LEN:
        return jsonify({"ok": False, "error": f"Message too long (max {_MAX_QUESTION_LEN} characters)."}), 400

    from ..ai_gateway import get_quota_status, stream_ollama_chat

    history = _get_history()
    sess_hash = _session_hash()
    quota = get_quota_status(sess_hash)
    if quota.get("session_quota_enabled") and not quota.get("session_available", True):
        return jsonify({"ok": False, "error": "This session has reached the current AI request limit. Please wait for the reset window before sending more requests."}), 429

    @stream_with_context
    def _event_stream():
        chunks: list[str] = []
        model_used = get_user_ollama_model_for("playground")
        try:
            for evt in stream_ollama_chat(
                question=message,
                system_prompt=_SYSTEM_PROMPT,
                session_hash=sess_hash,
                conversation_history=history,
                feature="playground",
            ):
                if evt.get("model"):
                    model_used = str(evt.get("model"))
                if evt.get("token"):
                    token = str(evt.get("token"))
                    chunks.append(token)
                    payload = {"type": "token", "token": token, "model": model_used}
                    yield f"data: {json.dumps(payload)}\n\n"

            reply = "".join(chunks)
            updated = list(history)
            updated.append({"role": "user", "content": message})
            updated.append({"role": "assistant", "content": reply})
            _set_history(updated)

            done_payload = {"type": "done", "reply": reply, "model": model_used}
            yield f"data: {json.dumps(done_payload)}\n\n"
        except RuntimeError as exc:
            err_payload = {"type": "error", "error": str(exc)}
            yield f"data: {json.dumps(err_payload)}\n\n"

    response = Response(_event_stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@playground_bp.route("/model", methods=["POST"])
def playground_set_model():
    """Set the active playground model in session without leaving the page."""
    try:
        require_ai_feature("playground")
    except AIFeatureDisabled as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403

    payload = request.get_json(silent=True) or {}
    model = (payload.get("model") or "").strip()
    valid = {m.get("id") for m in OLLAMA_MODEL_RECOMMENDATIONS if m.get("id")}
    if model not in valid:
        return jsonify({"ok": False, "error": "Invalid model selection."}), 400

    feature_models = dict(session.get("ollama_feature_models") or {})
    feature_models["playground"] = model
    session["ollama_feature_models"] = feature_models
    session.modified = True
    return jsonify({"ok": True, "model": model})


@playground_bp.route("/quota", methods=["GET"])
def playground_quota():
    """Return session quota status for UI meter/warnings."""
    from ..ai_gateway import get_quota_status

    sess_hash = _session_hash()
    quota = get_quota_status(sess_hash)
    return jsonify({"ok": True, "quota": quota})


@playground_bp.route("/regenerate", methods=["POST"])
@limiter.limit("20 per minute")
def playground_regenerate():
    """Regenerate the most recent assistant response for the last user message."""
    try:
        require_ai_feature("playground")
    except AIFeatureDisabled as exc:
        return jsonify({"ok": False, "error": str(exc)}), 403

    history = _get_history()
    if len(history) < 2:
        return jsonify({"ok": False, "error": "No conversation available to regenerate."}), 400
    if history[-1].get("role") != "assistant" or history[-2].get("role") != "user":
        return jsonify({"ok": False, "error": "Could not locate the last user/assistant turn."}), 400

    last_user = str(history[-2].get("content") or "").strip()
    base_history = history[:-2]

    from ..ai_gateway import chat as gateway_chat
    from ..ai_gateway import get_quota_status

    sess_hash = _session_hash()
    quota = get_quota_status(sess_hash)
    if quota.get("session_quota_enabled") and not quota.get("session_available", True):
        return jsonify({"ok": False, "error": "This session has reached the current AI request limit. Please wait for the reset window before sending more requests."}), 429
    try:
        reply, _ = gateway_chat(
            question=last_user,
            system_prompt=_SYSTEM_PROMPT,
            session_hash=sess_hash,
            conversation_history=base_history,
            feature="playground",
        )
    except RuntimeError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 503

    updated = list(base_history)
    updated.append({"role": "user", "content": last_user})
    updated.append({"role": "assistant", "content": reply})
    _set_history(updated)

    model_used = get_user_ollama_model_for("playground")
    return jsonify({"ok": True, "reply": reply, "model": model_used})


@playground_bp.route("/export", methods=["GET"])
def playground_export():
    """Export current conversation history as markdown."""
    history = _get_history()
    lines = ["# AI Playground Conversation", "", f"Exported: {datetime.now(UTC).isoformat()}", ""]
    if not history:
        lines.append("No messages in this session yet.")
    else:
        for item in history:
            role = "User" if item.get("role") == "user" else "Assistant"
            lines.append(f"## {role}")
            lines.append("")
            lines.append(str(item.get("content") or ""))
            lines.append("")

    body = "\n".join(lines)
    resp = Response(body, mimetype="text/markdown")
    resp.headers["Content-Disposition"] = "attachment; filename=playground-conversation.md"
    return resp


@playground_bp.route("/clear", methods=["POST"])
def playground_clear():
    """Wipe the server-side conversation history for this session."""
    with _server_history_lock:
        _server_history.pop(_session_hash(), None)
    session.pop(_PLAYGROUND_HISTORY_KEY, None)
    session.modified = True
    return jsonify({"ok": True})
