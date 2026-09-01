"""Document chat route -- ask questions about uploaded documents with tool calling."""

from __future__ import annotations

from pathlib import Path
import re

from flask import Blueprint, abort, make_response, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename

from ..app import limiter
from ..ai_gateway import (
    chat as gateway_chat,
    describe_image as gateway_describe_image,
    get_quota_status,
    make_session_hash,
)
from ..ai_features import require_ai_feature, AIFeatureDisabled
from ..chat_handler import ChatSession, DocumentContext, ToolRegistry
from ..gating import ai_gate, GatingError
from ..pii_guardrails import sanitize_text_for_ai
from ..upload import get_temp_dir, UploadError

chat_bp = Blueprint("chat", __name__)

_MAX_QUESTION_LENGTH = 2000
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
_IMAGE_QUESTION_KEYWORDS = (
    "image",
    "picture",
    "photo",
    "figure",
    "diagram",
    "chart",
    "graph",
    "screenshot",
    "ocr",
    "text in",
)


def _get_uploaded_document_path(token: str) -> Path:
    """Return the uploaded document path for a token."""
    temp_dir = get_temp_dir(token)
    saved_files = list(temp_dir.glob("*"))
    if not saved_files:
        raise UploadError("Upload not found.")
    return saved_files[0]


def _load_document_text(token: str) -> str:
    """Extract text from uploaded document."""
    try:
        saved_path = _get_uploaded_document_path(token)
        ext = saved_path.suffix.lower()

        if ext in {".md", ".txt", ".rst"}:
            return saved_path.read_text(encoding="utf-8")
        else:
            try:
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(str(saved_path))
                return result.text_content or ""
            except Exception as e:
                return f"[Error extracting text: {e}]"

    except UploadError:
        raise
    except Exception as e:
        raise UploadError(f"Error loading document: {e}") from e


def _build_document_context(question: str, document_text: str, max_chars: int = 8000) -> str:
    """Build a question-aware context window to improve answer grounding."""
    if not document_text:
        return ""

    text = document_text.strip()
    if len(text) <= max_chars:
        return text

    # Prefer keyword-near snippets when possible.
    tokens = [
        tok.lower()
        for tok in re.findall(r"[a-zA-Z0-9]{4,}", question)
        if tok.lower() not in {"what", "when", "where", "which", "about", "from", "that", "this"}
    ]

    lines = text.splitlines()
    snippets: list[str] = []
    for tok in tokens[:4]:
        for idx, line in enumerate(lines):
            if tok in line.lower():
                start = max(0, idx - 2)
                end = min(len(lines), idx + 3)
                snippet = "\n".join(lines[start:end]).strip()
                if snippet and snippet not in snippets:
                    snippets.append(snippet)
                if len("\n\n".join(snippets)) >= max_chars // 2:
                    break
        if len("\n\n".join(snippets)) >= max_chars // 2:
            break

    if snippets:
        merged = "\n\n".join(snippets)
        head = text[: max_chars // 4]
        return (head + "\n\n...\n\n" + merged)[:max_chars]

    # Fallback: beginning + ending context.
    half = max_chars // 2
    return text[:half] + "\n\n...\n\n" + text[-half:]


def _pdf_first_page_png(path: Path) -> bytes | None:
    """Render first PDF page to PNG bytes for vision analysis."""
    try:
        import fitz  # type: ignore[import-untyped]

        with fitz.open(str(path)) as doc:
            if doc.page_count < 1:
                return None
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=160)
            return pix.tobytes("png")
    except Exception:
        return None


_CHAT_SYSTEM_PROMPT = (
    "You are GLOW (Guided Layout & Output Workflow), an accessibility-focused "
    "document assistant. You help users understand and fix accessibility issues "
    "according to the ACB Large Print Guidelines, Microsoft Accessibility Checker "
    "rules, and WCAG 2.2 AA.\n\n"
    "When answering:\n"
    "1. Be specific and actionable -- cite the ACB rule ID (e.g. ACB-NO-ITALIC) when relevant.\n"
    "2. Prioritize critical violations first.\n"
    "3. Provide step-by-step fix instructions.\n"
    "4. If the document excerpt does not contain enough information, say so clearly.\n"
    "5. Lead with the most important finding; keep answers concise.\n"
    "6. Ground conclusions in the supplied pre-flight analysis and document context; do not invent findings.\n"
    "7. When a question references converted output, explain both source-content and output-format implications.\n"
    "8. CRITICAL -- Only report rule violations that were explicitly detected by a pre-flight tool result above. "
    "Do NOT add violations from your training knowledge if they are not present in the tool output. "
    "If a rule was not checked, say so rather than assuming it passes or fails.\n"
    "9. When reporting violations, also briefly acknowledge what the document already does correctly "
    "(e.g. valid heading hierarchy, clean link text). A balanced response builds trust.\n"
    "10. If a get_document_summary or get_compliance_score result is present in the pre-flight data, "
    "open your answer by briefly orienting the user to what the document is and its overall compliance picture."
)


@chat_bp.route("/", methods=["GET"])
def chat_form():
    """Show the chat form. Returns 404 if AI is not configured."""
    try:
        require_ai_feature("chat")
    except AIFeatureDisabled:
        abort(404)

    token = request.args.get("token")
    if not token:
        return redirect(url_for("process.process_form"))

    # Session hash for quota tracking
    sess_id = session.get("_id", "")
    sess_hash = make_session_hash(sess_id) if sess_id else "anonymous"
    quota = get_quota_status(sess_hash)

    try:
        session_key = f"chat_{token}"
        chat_data = session.get(session_key)

        if chat_data:
            chat_session = ChatSession.from_dict(chat_data)
        else:
            try:
                _load_document_text(token)  # validate file is readable
                temp_dir = get_temp_dir(token)
                saved_files = list(temp_dir.glob("*"))
                filename = saved_files[0].name if saved_files else "document"
                chat_session = ChatSession(token, filename)
                session[session_key] = chat_session.to_dict()
            except UploadError as e:
                return render_template("chat_form.html", error=str(e), token=token, quota=quota)

        return render_template(
            "chat_form.html",
            token=token,
            filename=chat_session.filename,
            conversation=chat_session.turns,
            quota=quota,
        )

    except Exception as e:
        return render_template("chat_form.html", error=str(e), token=token, quota=quota), 500


@chat_bp.route("/", methods=["POST"])
@limiter.limit("10 per minute")
def chat_submit():
    """Process a user question via OpenRouter and return an answer."""
    try:
        require_ai_feature("chat")
    except AIFeatureDisabled:
        abort(404)

    token = request.form.get("token")
    question = request.form.get("question", "").strip()

    if not token or not question:
        pass
    else:
        from ..tool_usage import record as _record_usage
        _record_usage("chat")

    if not token or not question:
        return redirect(url_for("chat.chat_form", token=token))

    if len(question) > _MAX_QUESTION_LENGTH:
        return render_template(
            "chat_form.html",
            error=f"Question is too long. Please keep it under {_MAX_QUESTION_LENGTH} characters.",
            token=token,
        ), 400

    # Session hash for quota tracking
    sess_id = session.get("_id", "")
    sess_hash = make_session_hash(sess_id) if sess_id else "anonymous"
    quota = get_quota_status(sess_hash)

    if not quota["chat_available"]:
        reason = (
            "The daily AI chat limit has been reached. Please try again tomorrow."
            if quota["chat_remaining_today"] == 0
            else "AI features are temporarily unavailable. Please try again later."
        )
        return render_template("chat_form.html", error=reason, token=token, quota=quota), 429
    if quota.get("session_quota_enabled") and not quota.get("session_available", True):
        reason = "This browser session has reached the current AI request limit. Please wait for the reset window before sending another request."
        return render_template("chat_form.html", error=reason, token=token, quota=quota), 429

    try:
        session_key = f"chat_{token}"
        chat_data = session.get(session_key)

        if not chat_data:
            return redirect(url_for("chat.chat_form", token=token))

        chat_session = ChatSession.from_dict(chat_data)
        doc_text = _load_document_text(token)
        saved_path = _get_uploaded_document_path(token)
        context = DocumentContext(doc_text, chat_session.filename, doc_path=saved_path)
        tools = ToolRegistry(context)
        turn = chat_session.add_turn(question)
        preflight_analysis = tools.dispatch_for_question(question)

        # On the first turn, prepend a document orientation block so the model
        # always knows what document it is looking at and its compliance state.
        if len(chat_session.turns) == 1:
            orientation = (
                "\n\n=== Document orientation (first-turn context) ===\n"
                + tools.get_document_summary()
                + "\n\n"
                + tools.get_compliance_score()
                + "\n\n"
                + tools.get_what_passes()
                + "\n=== End orientation ==="
            )
            preflight_analysis = preflight_analysis + orientation

        doc_context = _build_document_context(question, doc_text)

        vision_context = ""
        ext = saved_path.suffix.lower()
        is_image_question = any(kw in question.lower() for kw in _IMAGE_QUESTION_KEYWORDS)
        if ext in _IMAGE_EXTENSIONS:
            try:
                image_bytes = saved_path.read_bytes()
                vision_answer = gateway_describe_image(
                    image_bytes=image_bytes,
                    mime_type=f"image/{'jpeg' if ext in {'.jpg', '.jpeg'} else ext.lstrip('.')}",
                    prompt=(
                        "Describe this image for accessibility review. Include visible text, "
                        "chart/table meaning, and any missing-context risks for screen reader users."
                    ),
                    session_hash=sess_hash,
                )
                if vision_answer:
                    vision_context = f"\n\n=== Vision analysis (uploaded image) ===\n{vision_answer}"
            except Exception as exc:
                vision_context = f"\n\n=== Vision analysis ===\nVision analysis unavailable: {exc}"

        if (is_image_question or "ocr" in question.lower() or "scan" in question.lower()) and ext == ".pdf" and len(doc_text.strip()) < 300:
            png_bytes = _pdf_first_page_png(saved_path)
            if png_bytes:
                try:
                    vision_answer = gateway_describe_image(
                        image_bytes=png_bytes,
                        mime_type="image/png",
                        prompt=(
                            "This appears to be an image-first PDF page. Extract readable text when possible "
                            "and summarize key visual structure for accessibility remediation."
                        ),
                        session_hash=sess_hash,
                    )
                    if vision_answer:
                        vision_context = (
                            vision_context
                            + "\n\n=== Vision analysis (PDF first page render) ===\n"
                            + vision_answer
                        )
                except Exception as exc:
                    vision_context = vision_context + f"\n\nVision OCR fallback unavailable: {exc}"

        conv_pairs = [
            item
            for t in chat_session.turns[:-1]
            for item in (
                {"role": "user", "content": t.question},
                {"role": "assistant", "content": t.answer or ""},
            )
        ]

        try:
            safe_question, _question_meta = sanitize_text_for_ai(
                question, surface="chat_question"
            )
            safe_preflight, _preflight_meta = sanitize_text_for_ai(
                preflight_analysis, surface="chat_preflight_analysis"
            )
            safe_doc_context, _doc_meta = sanitize_text_for_ai(
                doc_context, surface="chat_document_context"
            )
            safe_vision_context, _vision_meta = sanitize_text_for_ai(
                vision_context, surface="chat_vision_context"
            )
            safe_conv_pairs: list[dict[str, str]] = []
            for pair in conv_pairs:
                safe_content, _pair_meta = sanitize_text_for_ai(
                    str(pair.get("content") or ""),
                    surface=f"chat_history_{pair.get('role', 'unknown')}",
                )
                safe_conv_pairs.append(
                    {"role": str(pair.get("role") or "user"), "content": safe_content}
                )
        except RuntimeError as exc:
            return (
                render_template("chat_form.html", error=str(exc), token=token, quota=quota),
                503,
            )

        try:
            wait_seconds = 90 if len(doc_context) > 6000 else None
            with ai_gate(wait_seconds=wait_seconds):
                answer, was_escalated = gateway_chat(
                    question=safe_question,
                    system_prompt=f"{_CHAT_SYSTEM_PROMPT}\n\n{safe_preflight}{safe_vision_context}",
                    session_hash=sess_hash,
                    document_text=safe_doc_context,
                    conversation_history=safe_conv_pairs,
                )
        except GatingError:
            resp = make_response(
                render_template(
                    "busy.html",
                    operation="AI document assistant",
                    retry_seconds=30,
                    back_url=url_for("chat.chat_form", token=token),
                ),
                503,
            )
            resp.headers["Retry-After"] = "30"
            return resp
        except RuntimeError as exc:
            # Budget exhausted or not configured
            return render_template("chat_form.html", error=str(exc), token=token, quota=quota), 503

        turn.answer = answer
        turn.tool_calls = []
        for line in preflight_analysis.splitlines():
            if line.startswith("[") and line.endswith("]") and line != "[=== GLOW Document Analysis (pre-flight tool results) ===]":
                turn.tool_calls.append({"name": line.strip("[]")})
        if was_escalated:
            turn.tool_calls.append({"escalated": True})
        turn.tool_results = {"preflight": preflight_analysis}

        session[session_key] = chat_session.to_dict()
        session.modified = True

        return redirect(url_for("chat.chat_form", token=token))

    except UploadError as e:
        return render_template("chat_form.html", error=str(e), token=token, quota=quota), 400
    except Exception:
        return render_template("chat_form.html", error="An unexpected error occurred. Please try again.", token=token, quota=quota), 500


@chat_bp.route("/export/<format>", methods=["GET"])
def chat_export(format: str):
    """Export conversation."""
    try:
        require_ai_feature("chat")
    except AIFeatureDisabled:
        abort(404)

    token = request.args.get("token")
    
    if not token:
        return redirect(url_for("process.process_form"))

    try:
        session_key = f"chat_{token}"
        chat_data = session.get(session_key)
        
        if not chat_data:
            return redirect(url_for("chat.chat_form", token=token))

        chat_session = ChatSession.from_dict(chat_data)

        # Sanitize filename for use in Content-Disposition header
        safe_stem = secure_filename(chat_session.filename) or "document"

        if format == "markdown":
            md_content = chat_session.export_markdown()
            return (
                md_content,
                200,
                {
                    "Content-Type": "text/markdown; charset=utf-8",
                    "Content-Disposition": f'attachment; filename="{safe_stem}_chat.md"',
                },
            )

        elif format == "word":
            from tempfile import NamedTemporaryFile
            temp = NamedTemporaryFile(suffix=".docx", delete=False)
            temp_path = Path(temp.name)
            temp.close()

            chat_session.export_word(temp_path)

            with open(temp_path, "rb") as f:
                docx_data = f.read()

            temp_path.unlink()

            return (
                docx_data,
                200,
                {
                    "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "Content-Disposition": f'attachment; filename="{safe_stem}_chat.docx"',
                },
            )

        elif format == "pdf":
            from tempfile import NamedTemporaryFile
            temp = NamedTemporaryFile(suffix=".pdf", delete=False)
            temp_path = Path(temp.name)
            temp.close()

            try:
                chat_session.export_pdf(temp_path)
                pdf_ok = temp_path.exists() and temp_path.stat().st_size > 0
            except Exception:
                pdf_ok = False

            if pdf_ok:
                with open(temp_path, "rb") as f:
                    pdf_data = f.read()
                temp_path.unlink(missing_ok=True)

                return (
                    pdf_data,
                    200,
                    {
                        "Content-Type": "application/pdf",
                        "Content-Disposition": f'attachment; filename="{safe_stem}_chat.pdf"',
                    },
                )
            else:
                temp_path.unlink(missing_ok=True)
                return render_template(
                    "error.html",
                    title="Export Failed",
                    message="PDF generation failed. Please try Markdown or Word export instead.",
                ), 500

        else:
            return render_template(
                "error.html",
                title="Unknown Export Format",
                message="The requested export format is not supported.",
            ), 400

    except Exception:
        return render_template(
            "error.html",
            title="Export Error",
            message="An error occurred while exporting the conversation. Please try again.",
        ), 500


@chat_bp.route("/clear", methods=["POST"])
def chat_clear():
    """Clear the conversation."""
    try:
        require_ai_feature("chat")
    except AIFeatureDisabled:
        abort(404)

    token = request.form.get("token")
    
    if token:
        session_key = f"chat_{token}"
        session.pop(session_key, None)
        session.modified = True

    return redirect(url_for("chat.chat_form", token=token))
