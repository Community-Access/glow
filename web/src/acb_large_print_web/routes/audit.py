"""Audit route -- upload a document and view a compliance report."""

from collections import Counter
from datetime import datetime, timezone
import os
from pathlib import Path
import uuid

from flask import Blueprint, Response, abort, current_app, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename as _sf

import re
import threading

from ..email import send_audit_report_email, send_batch_audit_report_email
from ..app import limiter
from ..csv_export import findings_to_csv_bytes, safe_filename_stem
from ..rules import (
    apply_rule_policy,
    build_rule_policy,
    filter_findings,
    get_all_rule_ids,
    get_help_urls,
    get_profile_label,
    get_rule_ids_by_category,
    get_rule_ids_by_severity,
    get_rule_ids_by_format,
    get_rule_ids_by_profile,
    get_rules_by_format,
)
from ..upload import UploadError, cleanup_token, validate_upload
from ..customization_warning import detect_audit_customizations, generate_customization_warning
from ..tasks.convert_tasks import create_job, run_audit_job

audit_bp = Blueprint("audit", __name__)
_ASYNC_HEAVY_ENABLED = os.environ.get("GLOW_CONVERT_ASYNC", "1") == "1"

# Rule IDs where AI-powered alt-text suggestions apply.
_ALT_TEXT_RULE_IDS: frozenset[str] = frozenset({
    "MSAC-ALT-TEXT",
    "EPUB-MISSING-ALT-TEXT",
    "ACB-MISSING-ALT",
})


def _is_small_upload() -> bool:
    """Return True when the upload Content-Length is below the large-file threshold.

    Used as ``exempt_when`` on the secondary 1/min rate limiter so only uploads
    over 10 MB are subject to the tighter cap.
    """
    return (request.content_length or 0) < 10 * 1024 * 1024


def _fire_webhook(callback_url: str, payload: dict) -> None:
    """POST audit results JSON to a user-supplied HTTPS callback URL.

    Runs in a daemon thread so it never blocks the response.  The request is
    signed with an HMAC-SHA256 ``X-GLOW-Signature`` header derived from
    ``WEBHOOK_SECRET`` (falls back to a random per-process secret).
    """
    import hashlib as _hashlib
    import hmac as _hmac
    import json as _json
    import os as _os
    import time as _time

    import requests as _requests

    try:
        secret = (_os.environ.get("WEBHOOK_SECRET") or "").encode() or _WEBHOOK_FALLBACK_SECRET
        body = _json.dumps(payload, default=str).encode()
        sig = _hmac.new(secret, body, _hashlib.sha256).hexdigest()
        _requests.post(
            callback_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-GLOW-Signature": f"sha256={sig}",
                "X-GLOW-Timestamp": str(int(_time.time())),
            },
            timeout=10,
            allow_redirects=False,
        )
    except Exception:
        pass  # webhook delivery is best-effort


# Stable per-process fallback signing secret (not cryptographically strong,
# but prevents trivially forged signatures when WEBHOOK_SECRET is not set).
import os as _os_mod, secrets as _secrets_mod
_WEBHOOK_FALLBACK_SECRET: bytes = _os_mod.urandom(32)


# Used by the audit report Quick Wins filter.
FIXABLE_RULE_IDS: frozenset[str] = frozenset({
    "ACB-FONT-FAMILY",
    "ACB-FONT-SIZE-BODY",
    "ACB-FONT-SIZE-H1",
    "ACB-FONT-SIZE-H2",
    "ACB-MARGINS",
    "ACB-LINE-SPACING",
    "ACB-ALIGNMENT",
    "ACB-LIST-INDENT",
    "ACB-PARA-INDENT",
    "ACB-FIRST-LINE-INDENT",
    "ACB-NO-ITALIC",
    "ACB-BOLD-BODY",
    "ACB-ALL-CAPS",
    "ACB-NO-ALLCAPS",
    "ACB-HYPHENATION",
    "ACB-PAGE-NUMBERS",
    "ACB-DOC-TITLE",
    "ACB-DOC-LANG",
    "ACB-FAUX-HEADING",
    "ACB-HEADING-HIERARCHY",
})

_BATCH_LIMIT = 3
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _validate_email(addr: str) -> bool:
    """Basic server-side email format check. Rejects obviously invalid addresses."""
    return bool(addr) and bool(_EMAIL_RE.match(addr)) and len(addr) <= 254


def _is_ace_installed() -> bool:
    """Ace is a required dependency -- always True in the web app."""
    try:
        from acb_large_print.ace_runner import ace_available

        return ace_available()
    except ImportError:
        return False


def _rules_by_id() -> dict:
    """Lazy lookup of rule metadata keyed by rule_id for inline explanations."""
    from acb_large_print.constants import AUDIT_RULES

    out: dict[str, dict] = {}
    for rid, rule in AUDIT_RULES.items():
        out[rid] = {
            "rule_id": rid,
            "description": rule.description,
            "auto_fixable": rule.auto_fixable,
            "acb_reference": rule.acb_reference,
        }
    return out


def _findings_to_dicts(findings) -> list[dict]:
    """Convert Finding dataclass instances to JSON-serialisable dicts."""
    out: list[dict] = []
    for f in findings:
        sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
        out.append({
            "rule_id": f.rule_id,
            "severity": sev,
            "message": f.message,
            "location": getattr(f, "location", "") or "",
            "acb_reference": getattr(f, "acb_reference", "") or "",
            "auto_fixable": getattr(f, "auto_fixable", False),
            "help_urls": get_help_urls(f.rule_id, getattr(f, "acb_reference", "") or ""),
        })
    return out


def _save_share_artifacts(
    share_token: str | None,
    html: str,
    *,
    findings,
    filename: str,
    doc_format: str,
    score: int,
    grade: str,
    profile_label: str,
    mode_label: str,
    passphrase: str | None = None,
) -> None:
    """Persist HTML and findings JSON for the share token (best-effort).

    When ``passphrase`` is provided (truthy, non-empty after stripping) the
    share is also passphrase-protected via ``set_share_passphrase``.
    """
    if not share_token:
        return
    try:
        from ..report_cache import (
            save_findings_data,
            save_report,
            set_share_passphrase,
        )

        save_report(share_token, html)
        save_findings_data(share_token, {
            "filename": filename,
            "doc_format": doc_format,
            "score": int(score),
            "grade": grade,
            "profile_label": profile_label,
            "mode_label": mode_label,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "findings": _findings_to_dicts(findings),
        })
        cleaned = (passphrase or "").strip()
        if cleaned:
            set_share_passphrase(share_token, cleaned)
    except Exception:
        pass


def _share_passphrase_from_form() -> str | None:
    """Read and validate an optional share passphrase from the current request.

    Returns the cleaned passphrase, or None when none was supplied. A minimum
    length of 4 characters is enforced so accidental whitespace cannot lock a
    share. Maximum 200 characters to avoid pathological inputs.
    """
    raw = (request.form.get("share_passphrase") or "").strip()
    if not raw:
        return None
    if len(raw) < 4 or len(raw) > 200:
        return None
    return raw


def _compute_audit_diff(
    findings,
    *,
    prev_score: int | None,
    prev_rule_ids: list[str],
    current_score: int,
):
    """Return a diff summary dict comparing this audit to a previous one.

    ``prev_rule_ids`` may include duplicates (one entry per finding); both
    sides are reduced to multisets so we can compute "cleared" vs "remaining"
    counts, plus a set of newly-introduced rule IDs.
    Returns None when prev_score is missing.
    """
    if prev_score is None:
        return None
    current_ids = [f.rule_id for f in findings]
    cur_counter = Counter(current_ids)
    prev_counter = Counter(prev_rule_ids)
    cleared_total = sum((prev_counter - cur_counter).values())
    new_ids = sorted(set(cur_counter) - set(prev_counter))
    persistent_total = sum((cur_counter & prev_counter).values())
    new_total = sum(cur_counter[r] for r in new_ids)
    return {
        "prev_score": int(prev_score),
        "current_score": int(current_score),
        "delta": int(current_score) - int(prev_score),
        "prev_count": sum(prev_counter.values()),
        "current_count": sum(cur_counter.values()),
        "cleared_count": cleared_total,
        "persistent_count": persistent_total,
        "new_count": new_total,
        "new_rule_ids": new_ids,
    }


def _audit_by_extension(saved_path: Path):
    """Dispatch to the correct auditor based on file extension."""
    from ..core_services import audit_by_extension

    return audit_by_extension(saved_path)


def _format_from_path(saved_path: Path) -> str:
    """Return the format key for a file path."""
    return saved_path.suffix.lower().lstrip(".")


def _get_epub_ace_conformance(result) -> str | None:
    """Return the Ace conformance level string for an EPUB audit result.

    Reads the ``ace_conformance`` attribute set by ``audit_epub_with_ace``.
    Returns a human-readable string like "EPUB Accessibility 1.0 - WCAG 2.0 Level AA",
    or None when conformance data is unavailable.
    """
    return getattr(result, "ace_conformance", None)


# ---------------------------------------------------------------------------
# AI alt-text suggestion endpoint (#14)
# ---------------------------------------------------------------------------

@audit_bp.route("/suggest-alt-text", methods=["POST"])
@limiter.limit("5 per minute")
def suggest_alt_text():
    """Return AI-generated alt-text suggestions for images in a preserved document.

    Requires a live chat_token (the document must still be on the server),
    an item index (0-based), and the AI alt-text feature to be enabled.
    Supports standalone images plus Word, PowerPoint, Excel, PDF, and EPUB files.

    Request (JSON or form):
        token        str   Chat/audit session token
        image_index  int   0-based index of the visual item in the document

    Response (JSON):
        {suggestion: str} on success
        {error: str}      on failure
    """
    from ..ai_features import ai_alt_text_enabled
    from ..ai_gateway import chat as gateway_chat, describe_image, make_session_hash
    from ..gating import GatingError, ai_gate, vision_gate
    from ..pii_guardrails import sanitize_text_for_ai
    from ..upload import ALT_TEXT_SOURCE_EXTENSIONS, get_temp_dir
    from ..user_ai import build_alt_text_prompt
    from ..visual_items import extract_visual_items

    if not ai_alt_text_enabled():
        return {"error": "AI alt-text suggestions are not enabled on this server."}, 503

    token = (request.form.get("token") or request.json.get("token") if request.is_json else request.form.get("token") or "").strip()
    try:
        image_index = int((request.form.get("image_index") or (request.json.get("image_index", 0) if request.is_json else 0)))
    except (TypeError, ValueError):
        image_index = 0

    if not token:
        return {"error": "Session token required."}, 400

    temp_dir = get_temp_dir(token)
    if temp_dir is None:
        return {"error": "Session expired. Please re-audit the document."}, 410

    doc_path = None
    for f in sorted(temp_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in ALT_TEXT_SOURCE_EXTENSIONS:
            doc_path = f
            break

    if doc_path is None:
        return {"error": "No supported visual source was found in this session."}, 400

    items = extract_visual_items(doc_path)
    if not items:
        return {"error": "No visual items found in this file."}, 404
    if image_index >= len(items):
        image_index = 0

    item = items[image_index]
    session_hash = make_session_hash(session.get("_id", "") or token)
    prompt = build_alt_text_prompt(
        document_name=doc_path.name,
        image_index=image_index,
        total_images=len(items),
        current_alt_text=str(item.get("current_alt_text") or ""),
        surrounding_text=list(item.get("context_lines") or []),
    )
    system_prompt = "You draft WCAG 2.2 AA-compliant alternative text. Return only the alt text."

    try:
        safe_prompt, _prompt_meta = sanitize_text_for_ai(
            prompt, surface="audit_alt_text_prompt"
        )
        safe_system_prompt, _system_meta = sanitize_text_for_ai(
            system_prompt, surface="audit_alt_text_system_prompt"
        )
        if item.get("text_only"):
            with ai_gate(wait_seconds=30):
                suggestion, _ = gateway_chat(
                    question=safe_prompt,
                    system_prompt=safe_system_prompt,
                    session_hash=session_hash,
                    feature="alt_text",
                )
        else:
            with vision_gate(wait_seconds=20):
                suggestion = describe_image(
                    bytes(item.get("image_bytes") or b""),
                    str(item.get("mime_type") or "image/png"),
                    safe_prompt,
                    session_hash,
                )
    except GatingError:
        return {"error": "Vision processing is busy right now. Please try again shortly."}, 503
    except Exception as exc:
        return {"error": str(exc)}, 503

    return {"suggestion": str(suggestion).strip(), "image_index": image_index, "total_images": len(items)}

@audit_bp.route("/", methods=["POST"])
@limiter.limit(
    "6 per minute",
    error_message="Too many audit requests. Please wait a moment and try again.",
)
@limiter.limit(
    "1 per minute",
    exempt_when=_is_small_upload,
    error_message="Large-file audit requests are limited to 1 per minute. Please wait before retrying.",
)
def audit_submit_rate_limited():
    """Rate-limited POST handler -- delegates to audit_submit."""
    return audit_submit()


@audit_bp.route("/", methods=["GET"])
def audit_form():
    from flask import session
    from ..email import email_configured
    from ..upload import get_temp_dir, ALLOWED_EXTENSIONS

    # Quick Start handoff: ?token=... pre-fills the form with the file
    # already uploaded via /process. The user does not need to upload again.
    prefill_token = (request.args.get("token") or "").strip()
    prefill_filename = None
    if prefill_token:
        temp_dir = get_temp_dir(prefill_token)
        if temp_dir is not None:
            for f in sorted(temp_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
                    prefill_filename = f.name
                    break
        if prefill_filename is None:
            prefill_token = None  # session expired or no file -- ignore

    return render_template(
        "audit_form.html",
        ace_installed=_is_ace_installed(),
        email_configured=email_configured(),
        rules_by_format=get_rules_by_format(),
        prefill_token=prefill_token or None,
        prefill_filename=prefill_filename,
        audit_history=session.get("glow_audit_history") or [],
    )


@audit_bp.route("/from-fix", methods=["POST"])
def audit_from_fix():
    """Re-audit a fixed document without re-uploading (uses existing session token)."""
    from ..upload import get_temp_dir, ALLOWED_EXTENSIONS
    from ..email import email_configured as _ec

    token = request.form.get("token", "").strip()
    download_name = request.form.get("download_name", "").strip()

    temp_dir = get_temp_dir(token)
    if temp_dir is None:
        return (
            render_template(
                "audit_form.html",
                error="Your session has expired. Please upload the fixed document to audit it.",
                ace_installed=_is_ace_installed(),
                email_configured=_ec(),
                rules_by_format=get_rules_by_format(),
            ),
            400,
        )

    # Resolve the fixed file -- prefer the named download, then any -fixed file, then any allowed file
    saved_path = None
    if download_name:
        candidate = temp_dir / _sf(download_name)
        try:
            candidate.resolve().relative_to(temp_dir.resolve())
            if candidate.exists() and candidate.suffix.lower() in ALLOWED_EXTENSIONS:
                saved_path = candidate
        except ValueError:
            pass
    if saved_path is None:
        for f in sorted(temp_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS and f.stem.endswith("-fixed"):
                saved_path = f
                break
    if saved_path is None:
        for f in sorted(temp_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
                saved_path = f
                break

    if saved_path is None:
        return (
            render_template(
                "audit_form.html",
                error="Fixed document not found. Session may have expired. Please upload again.",
                ace_installed=_is_ace_installed(),
                email_configured=_ec(),
                rules_by_format=get_rules_by_format(),
            ),
            400,
        )

    try:
        standards_profile = request.form.get("standards_profile", "acb_2025")
        profile_label = get_profile_label(standards_profile)
        doc_format = _format_from_path(saved_path)
        policy = build_rule_policy(request.form)
        mode_label = policy.mode_label
        suppressed_rules = sorted(policy.suppressed)

        result = _audit_by_extension(saved_path)
        result = apply_rule_policy(result, policy)

        # Compute a diff vs the audit that ran before the fix, when present.
        prev_score_raw = request.form.get("prev_score", "").strip()
        try:
            prev_score_int: int | None = int(prev_score_raw) if prev_score_raw else None
        except ValueError:
            prev_score_int = None
        prev_rule_ids_raw = request.form.get("prev_rule_ids", "")
        prev_rule_ids = [r.strip() for r in prev_rule_ids_raw.split(",") if r.strip()]
        audit_diff = _compute_audit_diff(
            result.findings,
            prev_score=prev_score_int,
            prev_rule_ids=prev_rule_ids,
            current_score=result.score,
        )

        chat_token = token  # keep token alive for further downstream use

        share_token = str(uuid.uuid4())
        try:
            share_url = url_for("audit.shared_report", share_token=share_token, _external=True)
        except Exception:
            share_url = None
            share_token = None

        html = render_template(
            "audit_report.html",
            result=result,
            mode_label=mode_label,
            profile_label=profile_label,
            doc_format=doc_format,
            ace_installed=_is_ace_installed(),
            suppressed_rules=suppressed_rules,
            email_status=None,
            ai_used=False,
            customization_warning="",
            chat_token=chat_token,
            fixable_rule_ids=FIXABLE_RULE_IDS,
            share_token=share_token,
            share_url=share_url,
            share_passphrase_set=bool(_share_passphrase_from_form()),
            rules_by_id=_rules_by_id(),
            standards_profile=standards_profile,
            audit_diff=audit_diff,
            audit_source="from-fix",
        )

        _save_share_artifacts(
            share_token,
            html,
            findings=result.findings,
            filename=saved_path.name,
            doc_format=doc_format,
            score=result.score,
            grade=result.grade,
            profile_label=profile_label,
            mode_label=mode_label,
            passphrase=_share_passphrase_from_form(),
        )

        return html

    except Exception:
        return (
            render_template(
                "audit_form.html",
                error="An error occurred during re-audit. Please try again.",
                ace_installed=_is_ace_installed(),
                email_configured=_ec(),
                rules_by_format=get_rules_by_format(),
            ),
            500,
        )


@audit_bp.route("/from-convert", methods=["POST"])
def audit_from_convert():
    """Audit a converted document without re-uploading (uses existing token).

    Mirrors :func:`audit_from_fix` but locates any auditable file in the
    session temp directory rather than expecting a ``-fixed`` suffix.
    """
    from ..upload import get_temp_dir, ALLOWED_EXTENSIONS
    from ..email import email_configured as _ec

    token = request.form.get("token", "").strip()
    download_name = request.form.get("download_name", "").strip()

    temp_dir = get_temp_dir(token)
    if temp_dir is None:
        return (
            render_template(
                "audit_form.html",
                error="Your session has expired. Please upload the converted document to audit it.",
                ace_installed=_is_ace_installed(),
                email_configured=_ec(),
                rules_by_format=get_rules_by_format(),
            ),
            400,
        )

    saved_path = None
    if download_name:
        candidate = temp_dir / _sf(download_name)
        try:
            candidate.resolve().relative_to(temp_dir.resolve())
            if candidate.exists() and candidate.suffix.lower() in ALLOWED_EXTENSIONS:
                saved_path = candidate
        except ValueError:
            pass
    if saved_path is None:
        # Prefer the most recently modified auditable file in the temp dir.
        candidates = [
            f for f in temp_dir.iterdir()
            if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
        ]
        if candidates:
            saved_path = max(candidates, key=lambda p: p.stat().st_mtime)

    if saved_path is None:
        return (
            render_template(
                "audit_form.html",
                error="The converted file could not be audited (its format is not supported by the auditor).",
                ace_installed=_is_ace_installed(),
                email_configured=_ec(),
                rules_by_format=get_rules_by_format(),
            ),
            400,
        )

    try:
        standards_profile = request.form.get("standards_profile", "acb_2025")
        profile_label = get_profile_label(standards_profile)
        doc_format = _format_from_path(saved_path)
        policy = build_rule_policy(request.form)
        mode_label = policy.mode_label
        suppressed_rules = sorted(policy.suppressed)

        result = _audit_by_extension(saved_path)
        result = apply_rule_policy(result, policy)

        chat_token = token

        share_token = str(uuid.uuid4())
        try:
            share_url = url_for("audit.shared_report", share_token=share_token, _external=True)
        except Exception:
            share_url = None
            share_token = None

        html = render_template(
            "audit_report.html",
            result=result,
            mode_label=mode_label,
            profile_label=profile_label,
            doc_format=doc_format,
            ace_installed=_is_ace_installed(),
            suppressed_rules=suppressed_rules,
            email_status=None,
            ai_used=False,
            customization_warning="",
            chat_token=chat_token,
            fixable_rule_ids=FIXABLE_RULE_IDS,
            share_token=share_token,
            share_url=share_url,
            share_passphrase_set=bool(_share_passphrase_from_form()),
            rules_by_id=_rules_by_id(),
            standards_profile=standards_profile,
            audit_diff=None,
            audit_source="from-convert",
        )

        _save_share_artifacts(
            share_token,
            html,
            findings=result.findings,
            filename=saved_path.name,
            doc_format=doc_format,
            score=result.score,
            grade=result.grade,
            profile_label=profile_label,
            mode_label=mode_label,
            passphrase=_share_passphrase_from_form(),
        )

        return html

    except Exception:
        return (
            render_template(
                "audit_form.html",
                error="An error occurred while auditing the converted document. Please try again.",
                ace_installed=_is_ace_installed(),
                email_configured=_ec(),
                rules_by_format=get_rules_by_format(),
            ),
            500,
        )


@audit_bp.route("/share/<share_token>/csv", methods=["GET"])
def shared_report_csv(share_token: str):
    """Download the cached audit findings as a UTF-8 CSV file."""
    from ..report_cache import load_findings_data

    gate = _share_unlock_required(share_token)
    if gate is not None:
        return gate

    data = load_findings_data(share_token)
    if not data:
        abort(404)

    csv_bytes = findings_to_csv_bytes(
        data.get("findings", []),
        filename=data.get("filename", ""),
        doc_format=data.get("doc_format", ""),
        score=data.get("score"),
        grade=data.get("grade", ""),
        profile_label=data.get("profile_label", ""),
        mode_label=data.get("mode_label", ""),
    )

    stem = safe_filename_stem(Path(data.get("filename", "audit") or "audit").stem)
    download_name = f"{stem}-findings.csv"
    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


@audit_bp.route("/share/<share_token>/pdf", methods=["GET"])
def shared_report_pdf(share_token: str):
    """Render the cached HTML report as a PDF (lazy, cached for repeat downloads)."""
    from ..report_cache import (
        load_findings_data,
        load_pdf,
        load_report,
        save_pdf,
    )

    gate = _share_unlock_required(share_token)
    if gate is not None:
        return gate

    pdf_bytes = load_pdf(share_token)
    if pdf_bytes is None:
        html = load_report(share_token)
        if not html:
            abort(404)
        try:
            from weasyprint import HTML  # type: ignore[import-not-found]
        except ImportError:
            abort(503)
        try:
            pdf_bytes = HTML(string=html, base_url=request.url_root).write_pdf()
        except Exception:
            abort(500)
        if pdf_bytes:
            save_pdf(share_token, pdf_bytes)

    data = load_findings_data(share_token) or {}
    stem_source = data.get("filename") or "audit"
    stem = safe_filename_stem(Path(stem_source).stem or "audit")
    download_name = f"{stem}-audit-report.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )


@audit_bp.route("/share/<share_token>", methods=["GET", "POST"])
def shared_report(share_token: str):
    """Serve a cached, shareable audit report by token (valid for 1 hour).

    When the share is passphrase-protected, render a small unlock form on
    GET and validate the supplied passphrase on POST. The passphrase is also
    accepted via the ``?p=...`` query string for convenience (e.g. when the
    sharer pastes a combined link into chat) -- but the prompt is the
    canonical path.
    """
    from ..report_cache import (
        load_report,
        share_requires_passphrase,
        verify_share_passphrase,
    )

    html = load_report(share_token)
    if not html:
        abort(404)

    if share_requires_passphrase(share_token):
        candidate = (request.form.get("share_passphrase")
                     or request.args.get("p")
                     or "").strip()
        if not candidate or not verify_share_passphrase(share_token, candidate):
            return render_template(
                "share_unlock.html",
                share_token=share_token,
                error=bool(candidate),
                target="report",
            ), (401 if candidate else 200)

    return Response(html, mimetype="text/html")


def _share_unlock_required(share_token: str) -> Response | None:
    """Return an unlock-form Response when a passphrase is required and missing.

    Used by the CSV and PDF download endpoints, which accept the passphrase
    only via ``?p=...`` (no POST body) so a single click from the unlock form
    can deep-link to either download.
    """
    from ..report_cache import (
        share_requires_passphrase,
        verify_share_passphrase,
    )
    if not share_requires_passphrase(share_token):
        return None
    candidate = (request.args.get("p") or "").strip()
    if candidate and verify_share_passphrase(share_token, candidate):
        return None
    return render_template(
        "share_unlock.html",
        share_token=share_token,
        error=bool(candidate),
        target="download",
    ), 401  # type: ignore[return-value]


def audit_submit():
    upload_mode = request.form.get("upload_mode", "single")

    if upload_mode == "batch":
        return _audit_batch()
    return _audit_single()


def _audit_single():
    """Handle single-file audit -- original behaviour."""
    token = None
    try:
        from flask import session
        from ..tool_usage import record as _record_usage
        from ..upload import get_temp_dir, ALLOWED_EXTENSIONS
        _record_usage("audit")

        # Quick Start handoff: when a session token is posted with prefill=1
        # we re-use the previously uploaded file rather than requiring a new
        # upload. validate_upload() is skipped entirely in that path.
        saved_path = None
        prefill_token = (request.form.get("token") or "").strip()
        if prefill_token and request.form.get("prefill") == "1":
            temp_dir = get_temp_dir(prefill_token)
            if temp_dir is not None:
                for f in sorted(temp_dir.iterdir()):
                    if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
                        saved_path = f
                        break
            if saved_path is None:
                # Session expired or file missing -- fall through to normal upload
                prefill_token = ""
            else:
                token = prefill_token

        if saved_path is None:
            token, saved_path = validate_upload(request.files.get("document"))

        if _ASYNC_HEAVY_ENABLED and not current_app.config.get("TESTING", False):
            upload_token = token
            job_id = str(uuid.uuid4())
            create_job(
                job_id,
                "audit",
                saved_path.name,
                meta={
                    "op": "audit",
                    "upload_token": upload_token,
                    "input_filename": saved_path.name,
                    "options": {
                        "standards_profile": request.form.get("standards_profile", "acb_2025"),
                        "category": request.form.getlist("category"),
                        "mode": request.form.get("mode", "full"),
                        "suppress_rule": request.form.getlist("suppress_rule"),
                    },
                },
            )
            run_audit_job.delay(
                job_id,
                upload_token,
                saved_path.name,
                {
                    "standards_profile": request.form.get("standards_profile", "acb_2025"),
                    "category": request.form.getlist("category"),
                    "mode": request.form.get("mode", "full"),
                    "suppress_rule": request.form.getlist("suppress_rule"),
                },
            )
            # Queue workers consume the uploaded file from the token path.
            # Do not clean it up in this request-finally path.
            token = None
            return redirect(url_for("jobs.job_progress", job_id=job_id))

        standards_profile = request.form.get("standards_profile", "acb_2025")
        profile_label = get_profile_label(standards_profile)
        doc_format = _format_from_path(saved_path)

        policy = build_rule_policy(request.form)
        mode_label = policy.mode_label
        suppressed_rules = sorted(policy.suppressed)

        # --- #7: Pull last-audit baseline from session for auto-diff -------
        _last = session.get("glow_last_audit") or {}
        _session_prev_score: int | None = _last.get("score")
        _session_prev_rule_ids: list[str] = _last.get("rule_ids") or []

        result = _audit_by_extension(saved_path)
        result = apply_rule_policy(result, policy)

        # Optional email delivery
        email_status = None
        if request.form.get("email_report") == "on":
            to_email = request.form.get("report_email", "").strip()
            if not _validate_email(to_email):
                email_status = {"success": False, "message": "Report could not be sent: the email address provided is invalid."}
            elif to_email:
                severity_breakdown = Counter(
                    str(f.severity.value) if hasattr(f.severity, "value") else str(f.severity)
                    for f in result.findings
                )
                ok, msg = send_audit_report_email(
                    to_email=to_email,
                    filename=saved_path.name,
                    doc_format=doc_format,
                    score=result.score,
                    grade=result.grade,
                    findings_count=len(result.findings),
                    severity_breakdown=dict(severity_breakdown),
                    findings=result.findings,
                )
                email_status = {"success": ok, "message": msg}

        # Detect and warn about customizations from ACB defaults
        has_customizations, customization_reasons = detect_audit_customizations(request.form)
        customization_warning = ""
        if has_customizations:
            customization_warning = generate_customization_warning(customization_reasons)

        # Preserve the uploaded file for a potential Chat pivot.
        # Nulling token prevents the finally block from deleting it;
        # the temp dir is reclaimed by OS TTL or the next audit/chat cleanup.
        chat_token = token
        token = None

        # --- #7: Auto-diff vs previous audit (session baseline) -----------
        audit_diff = _compute_audit_diff(
            result.findings,
            prev_score=_session_prev_score,
            prev_rule_ids=_session_prev_rule_ids,
            current_score=result.score,
        )

        # --- #7/#13: Persist current audit in session ---------------------
        try:
            session.permanent = True
            session["glow_last_audit"] = {
                "score": result.score,
                "rule_ids": [f.rule_id for f in result.findings],
                "filename": saved_path.name,
            }
            # --- #13: Audit history (compact, max 5 entries) --------------
            _history = list(session.get("glow_audit_history") or [])
            _share_token_for_history = None  # will be filled below
            _history_entry = {
                "score": result.score,
                "grade": result.grade,
                "filename": saved_path.name[:60],
                "ts": int(datetime.now(timezone.utc).timestamp()),
            }
            _history.insert(0, _history_entry)
            session["glow_audit_history"] = _history[:5]

            # The same entry, kept past the session, but only for a passport
            # whose owner ticked the history box. record_history() re-checks
            # that itself, so a future caller cannot forget to.
            try:
                from ..passport_store import COOKIE_NAME, record_history

                _passport_id = (request.cookies.get(COOKIE_NAME) or "").strip()
                if _passport_id:
                    record_history(
                        _passport_id,
                        kind="audit",
                        label=saved_path.name[:60],
                        score=result.score,
                        grade=str(result.grade or ""),
                    )
            except Exception:
                pass
        except Exception:
            audit_diff = None  # session not available; degrade gracefully

        # Generate share token before rendering so it can be embedded in the HTML.
        share_token = str(uuid.uuid4())
        try:
            share_url = url_for(
                "audit.shared_report", share_token=share_token, _external=True
            )
        except Exception:
            share_url = None
            share_token = None

        # Patch the history entry with the share_token now that we have it
        try:
            _history = list(session.get("glow_audit_history") or [])
            if _history:
                _history[0]["share_token"] = share_token
                session["glow_audit_history"] = _history
        except Exception:
            pass

        html = render_template(
            "audit_report.html",
            result=result,
            mode_label=mode_label,
            profile_label=profile_label,
            standards_profile=standards_profile,
            doc_format=doc_format,
            ace_installed=_is_ace_installed(),
            suppressed_rules=suppressed_rules,
            email_status=email_status,
            ai_used=False,
            customization_warning=customization_warning,
            chat_token=chat_token,
            fixable_rule_ids=FIXABLE_RULE_IDS,
            share_token=share_token,
            share_url=share_url,
            share_passphrase_set=bool(_share_passphrase_from_form()),
            rules_by_id=_rules_by_id(),
            audit_diff=audit_diff,
            audit_source="upload",
        )

        _save_share_artifacts(
            share_token,
            html,
            findings=result.findings,
            filename=saved_path.name,
            doc_format=doc_format,
            score=result.score,
            grade=result.grade,
            profile_label=profile_label,
            mode_label=mode_label,
            passphrase=_share_passphrase_from_form(),
        )

        # --- #11: Optional webhook callback (HTTPS URLs only) ------------
        raw_callback = (request.form.get("callback_url") or "").strip()
        if raw_callback and raw_callback.startswith("https://"):
            _payload = {
                "event": "audit.complete",
                "score": result.score,
                "grade": result.grade,
                "filename": saved_path.name,
                "doc_format": doc_format,
                "findings_count": len(result.findings),
                "share_url": share_url,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            threading.Thread(
                target=_fire_webhook,
                args=(raw_callback, _payload),
                daemon=True,
            ).start()

        return html
    except UploadError as e:
        from ..email import email_configured as _ec
        return (
            render_template(
                "audit_form.html",
                error=str(e),
                ace_installed=_is_ace_installed(),
                email_configured=_ec(),
                rules_by_format=get_rules_by_format(),
            ),
            400,
        )
    except Exception:
        from ..email import email_configured as _ec
        return (
            render_template(
                "audit_form.html",
                error="An error occurred while processing the document. "
                "Please ensure it is a valid Office file and try again.",
                ace_installed=_is_ace_installed(),
                email_configured=_ec(),
                rules_by_format=get_rules_by_format(),
            ),
            500,
        )
    finally:
        if token:
            cleanup_token(token)


def _audit_batch():
    """Handle multi-file audit (up to _BATCH_LIMIT files).

    Gracefully trims to the limit rather than returning an error.
    Files that fail validation are skipped with a warning note instead
    of aborting the whole run.
    """
    standards_profile = request.form.get("standards_profile", "acb_2025")
    profile_label = get_profile_label(standards_profile)
    report_style = request.form.get("report_style", "combined")

    policy = build_rule_policy(request.form)
    mode_label = policy.mode_label
    suppressed_rules = sorted(policy.suppressed)

    uploaded_files = request.files.getlist("document")

    # Graceful over-limit: silently trim, note it in the results
    trimmed = len(uploaded_files) > _BATCH_LIMIT
    files_to_process = uploaded_files[:_BATCH_LIMIT]
    skipped_count = len(uploaded_files) - _BATCH_LIMIT if trimmed else 0

    if not files_to_process:
        from ..email import email_configured as _ec
        return (
            render_template(
                "audit_form.html",
                error="No files were received. Please add at least one document.",
                ace_installed=_is_ace_installed(),
                email_configured=_ec(),
                rules_by_format=get_rules_by_format(),
            ),
            400,
        )

    file_results = []  # list of dicts: filename, doc_format, result, error
    tokens_to_clean = []

    for file_storage in files_to_process:
        token = None
        try:
            token, saved_path = validate_upload(file_storage)
            tokens_to_clean.append(token)
            doc_format = _format_from_path(saved_path)
            result = _audit_by_extension(saved_path)
            result = apply_rule_policy(result, policy)
            file_results.append(
                {
                    "filename": saved_path.name,
                    "doc_format": doc_format,
                    "result": result,
                    "error": None,
                }
            )
        except UploadError as e:
            if token:
                cleanup_token(token)
            file_results.append(
                {
                    "filename": getattr(file_storage, "filename", "unknown") or "unknown",
                    "doc_format": None,
                    "result": None,
                    "error": str(e),
                }
            )
        except Exception:
            if token:
                cleanup_token(token)
            fname = getattr(file_storage, "filename", "unknown") or "unknown"
            file_results.append(
                {
                    "filename": fname,
                    "doc_format": None,
                    "result": None,
                    "error": "An unexpected error occurred while processing this file.",
                }
            )

    # Clean up all temp dirs
    for t in tokens_to_clean:
        cleanup_token(t)

    # Build aggregate stats for combined report header
    successful = [r for r in file_results if r["result"] is not None]
    failed = [r for r in file_results if r["result"] is None]

    total_findings = sum(len(r["result"].findings) for r in successful)
    avg_score = (
        round(sum(r["result"].score for r in successful) / len(successful))
        if successful
        else None
    )

    severity_totals: Counter = Counter()
    for r in successful:
        for f in r["result"].findings:
            severity_totals[f.severity.value] += 1

    # Optional email delivery (single combined email for the whole batch)
    email_status = None
    if request.form.get("email_report") == "on":
        to_email = request.form.get("report_email", "").strip()
        if not _validate_email(to_email):
            email_status = {"success": False, "message": "Report could not be sent: the email address provided is invalid."}
        elif to_email and successful:
            ok, msg = send_batch_audit_report_email(
                to_email=to_email,
                file_results=file_results,
                avg_score=avg_score,
                total_findings=total_findings,
            )
            email_status = {"success": ok, "message": msg}

    # Detect and warn about customizations from ACB defaults
    has_customizations, customization_reasons = detect_audit_customizations(request.form)
    customization_warning = ""
    if has_customizations:
        customization_warning = generate_customization_warning(customization_reasons)

    return render_template(
        "audit_batch_report.html",
        file_results=file_results,
        successful=successful,
        failed=failed,
        report_style=report_style,
        mode_label=mode_label,
        profile_label=profile_label,
        suppressed_rules=suppressed_rules,
        total_findings=total_findings,
        avg_score=avg_score,
        severity_totals=severity_totals,
        trimmed=trimmed,
        skipped_count=skipped_count,
        batch_limit=_BATCH_LIMIT,
        ace_installed=_is_ace_installed(),
        email_status=email_status,
        customization_warning=customization_warning,
    )
