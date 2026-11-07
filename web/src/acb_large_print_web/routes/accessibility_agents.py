"""Accessibility Agents on letitglow.app.

One page: the ways to use Accessibility Agents (in an AI assistant through
the hosted MCP server, by pasting the AHG texts, through GLOW for documents,
or installed in full), a check tool that calls the hosted server, and a place
to ask questions with the visitor's own AI key.

The hosted server is a separate service (Community-Access/
accessibility-agents, mcp-server/Dockerfile) that Caddy serves at /a11y/mcp
on this same origin, so the check tool's script calls it directly.

Asking uses the visitor's own key, sent with each request and never stored:
see aa_ask.py.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

from .. import aa_ask
from ..app import limiter
from ..upload import ALLOWED_EXTENSIONS, UploadError, cleanup_token, validate_upload

accessibility_agents_bp = Blueprint("accessibility_agents", __name__)

#: The public address of the hosted Accessibility Agents MCP server.
HOSTED_MCP_URL = "https://letitglow.app/a11y/mcp"

#: Components the server has guidelines for (get_accessibility_guidelines).
GUIDELINE_COMPONENTS = (
    ("modal", "Modal dialog"),
    ("tabs", "Tabs"),
    ("accordion", "Accordion"),
    ("combobox", "Combobox"),
    ("carousel", "Carousel"),
    ("form", "Form"),
    ("live-region", "Live region"),
    ("navigation", "Navigation"),
    ("general", "General"),
)


def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@accessibility_agents_bp.route("/", methods=["GET"])
def accessibility_agents_page():
    return render_template(
        "accessibility_agents.html",
        hosted_mcp_url=HOSTED_MCP_URL,
        guideline_components=GUIDELINE_COMPONENTS,
        ask_providers=[(pid, p["label"], p["default_model"], p["key_url"])
                       for pid, p in aa_ask.PROVIDERS.items()],
    )


@accessibility_agents_bp.route("/ask", methods=["POST"])
@limiter.limit("10 per minute")
def ask():
    data = request.get_json(silent=True) or {}
    try:
        result = aa_ask.ask(
            provider_id=str(data.get("provider") or ""),
            key=str(data.get("key") or ""),
            model=str(data.get("model") or ""),
            question=str(data.get("question") or ""),
            material=str(data.get("material") or ""),
            source=str(data.get("source") or ""),
        )
    except aa_ask.AskError as exc:
        return _no_store(jsonify({"error": str(exc)})), 400
    except Exception:  # noqa: BLE001 - never let a key reach a traceback page
        return _no_store(jsonify({"error": "Something went wrong. Try again."})), 502
    return _no_store(jsonify(result))


@accessibility_agents_bp.route("/models", methods=["POST"])
@limiter.limit("10 per minute")
def models():
    data = request.get_json(silent=True) or {}
    try:
        found = aa_ask.list_models(str(data.get("provider") or ""), str(data.get("key") or ""))
    except aa_ask.AskError as exc:
        return _no_store(jsonify({"error": str(exc)})), 400
    except Exception:  # noqa: BLE001 - never let a key reach a traceback page
        return _no_store(jsonify({"error": "Something went wrong. Try again."})), 502
    return _no_store(jsonify({"models": found}))


#: Files Ask can read: GLOW's document formats plus plain web and text files.
EXTRACT_EXTENSIONS = ALLOWED_EXTENSIONS | {".html", ".htm", ".txt", ".css", ".csv"}
#: Text and web files are read as they are; documents go through MarkItDown.
PLAIN_EXTENSIONS = {".html", ".htm", ".txt", ".css", ".csv", ".md"}
MAX_EXTRACT_BYTES = 20 * 1024 * 1024


@accessibility_agents_bp.route("/extract", methods=["POST"])
@limiter.limit("10 per minute")
def extract():
    """Turn one uploaded file into text for the Ask form. The file is not kept."""
    if (request.content_length or 0) > MAX_EXTRACT_BYTES + 64 * 1024:
        return _no_store(jsonify({"error": "Choose a file under 20 MB."})), 400
    token = None
    try:
        token, path = validate_upload(request.files.get("file"), EXTRACT_EXTENSIONS)
        ext = path.suffix.lower()
        if ext in PLAIN_EXTENSIONS:
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            from ..magic_features import extract_text_for_compare

            text = extract_text_for_compare(path)
        text = text.strip()
        if not text:
            return _no_store(jsonify({"error": "No text was found in that file. "
                                      "A scanned PDF needs GLOW's OCR first."})), 400
        limit = aa_ask.MAX_MATERIAL_CHARS
        return _no_store(jsonify({
            "filename": path.name,
            "kind": "HTML" if ext in {".html", ".htm"} else ext.lstrip(".").upper(),
            "text": text[:limit],
            "truncated": len(text) > limit,
            "characters": len(text),
        }))
    except UploadError as exc:
        return _no_store(jsonify({"error": str(exc)})), 400
    except Exception:  # noqa: BLE001
        return _no_store(jsonify({"error": "That file could not be read. Try another."})), 502
    finally:
        if token:
            cleanup_token(token)


@accessibility_agents_bp.route("/openrouter/exchange", methods=["POST"])
@limiter.limit("5 per minute")
def openrouter_exchange():
    data = request.get_json(silent=True) or {}
    try:
        key = aa_ask.exchange_openrouter_code(
            str(data.get("code") or ""), str(data.get("code_verifier") or "")
        )
    except aa_ask.AskError as exc:
        return _no_store(jsonify({"error": str(exc)})), 400
    except Exception:  # noqa: BLE001
        return _no_store(jsonify({"error": "Something went wrong. Try again."})), 502
    return _no_store(jsonify({"key": key}))
