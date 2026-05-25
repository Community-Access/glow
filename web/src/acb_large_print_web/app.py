"""Flask application factory."""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

from flask import Flask, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFError, CSRFProtect

from .rules import get_help_urls_map, get_rules_by_category, get_rules_by_severity

csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120 per minute"],
    storage_uri="memory://",
)


def create_app(config: dict | None = None) -> Flask:
    """Create and configure the Flask application."""
    # Resolve instance path: honour FLASK_INSTANCE_PATH env var so the
    # feedback SQLite database lands in the Docker volume (/app/instance)
    # instead of Flask's default which resolves to site-packages/instance/
    # (not writable by the container's non-root user).
    # Default: CWD-relative "instance/" -- in Docker (WORKDIR /app) this
    # resolves to /app/instance, which matches the compose volume mount.
    _instance_path = os.environ.get(
        "FLASK_INSTANCE_PATH",
        os.path.join(os.getcwd(), "instance"),
    )
    app = Flask(__name__, instance_path=_instance_path)
    app.url_map.strict_slashes = False

    # Defaults
    app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500 MB
    secret = os.environ.get("SECRET_KEY", "")
    if not secret:
        secret = os.urandom(32).hex()
        app.logger.warning(
            "SECRET_KEY not set -- using random key. "
            "Sessions and CSRF tokens will not survive restarts."
        )
    app.config["SECRET_KEY"] = secret

    # Session timeout: default 4 hours for long document processing workflows
    # Users can adjust via SESSION_TIMEOUT_MINUTES env var
    timeout_minutes = int(os.environ.get("SESSION_TIMEOUT_MINUTES", "240"))
    app.config["PERMANENT_SESSION_LIFETIME"] = timeout_minutes * 60
    app.config["SESSION_REFRESH_EACH_REQUEST"] = True

    if config:
        app.config.update(config)

    # Extensions
    csrf.init_app(app)
    limiter.init_app(app)

    # Logging
    _configure_logging(app)

    # Optional queue wiring (Celery runs in eager mode when broker is unset).
    try:
        from .tasks import make_celery as _make_celery
        _make_celery(app)
    except Exception:
        app.logger.exception("Failed to initialize Celery queue wiring")

    # Request timing (set before each request so after_request can compute duration)
    import time as _time

    @app.before_request
    def _record_request_start():
        from flask import g as _g, request as _req
        _g._request_start = _time.monotonic()
        incoming_id = (_req.headers.get("X-Request-ID") or "").strip()
        _g.request_id = incoming_id or uuid.uuid4().hex[:12]

    @app.before_request
    def _count_visitor():
        """Increment visitor counter once per browser session."""
        from flask import session as _sess, request as _req
        # Skip static files, health checks, and API calls
        if _req.path.startswith('/static') or _req.path == '/health':
            return
        if not _sess.get('_v_counted'):
            try:
                from .visitor_counter import increment_and_get
                _sess['_v_counted'] = True
                _sess.permanent = True
                increment_and_get()
            except Exception:
                pass

    @app.after_request
    def _log_request(response):
        from flask import g as _g, request as _req
        request_id = getattr(_g, "request_id", "") or uuid.uuid4().hex[:12]
        response.headers["X-Request-ID"] = request_id
        duration_ms = round((_time.monotonic() - getattr(_g, '_request_start', _time.monotonic())) * 1000)
        # Skip noisy health poll logs unless they fail or are slow
        if _req.path == '/health' and response.status_code == 200 and duration_ms < 2000:
            return response
        app.logger.info(
            'REQUEST id=%s %s %s -> %s (%dms) ua=%s',
            request_id,
            _req.method,
            _req.full_path.rstrip('?'),
            response.status_code,
            duration_ms,
            (_req.user_agent.string or '')[:80],
        )
        return response

    # Make rule metadata available in all templates
    @app.context_processor
    def inject_rules():
        from .ai_features import get_all_flags as _get_ai_flags
        from .branding import get_branding_context as _get_branding_context
        from .version import get_version as _get_release_version

        try:
            release_ver = _get_release_version()
        except Exception:
            try:
                from importlib.metadata import version as _pkg_version
                release_ver = _pkg_version("acb-large-print-web")
            except Exception:
                release_ver = "unknown"

        web_ver = release_ver
        desktop_ver = release_ver
        ctx = {
            "rules_by_severity": get_rules_by_severity(),
            "rules_by_category": get_rules_by_category(),
            "help_urls_map": get_help_urls_map(),
            "web_version": web_ver,
            "desktop_version": desktop_ver,
            "release_version": release_ver,
        }
        # Inject AI flags (from ai_features)
        ctx.update(_get_ai_flags())
        # Inject deployment branding profile (Community Access default, optional overrides)
        ctx.update(_get_branding_context())

        # Inject visitor count for footer display
        try:
            from .visitor_counter import get_count as _get_visitor_count
            ctx["visitor_count"] = _get_visitor_count()
        except Exception:
            ctx["visitor_count"] = 0

        # Share TTL (hours) for template display
        try:
            from .report_cache import get_share_ttl_hours as _get_share_ttl_hours
            ctx["share_ttl_hours"] = _get_share_ttl_hours()
        except Exception:
            ctx["share_ttl_hours"] = 4

        # Inject server-side feature flags (broad feature visibility)
        try:
            from . import feature_flags as _ff

            all_flags = _ff.get_all_flags()
            # Expose raw map and common convenience booleans used in templates
            ctx["feature_flags"] = all_flags
            ctx["feature_word_enabled"] = bool(all_flags.get("GLOW_ENABLE_WORD", True))
            ctx["feature_excel_enabled"] = bool(all_flags.get("GLOW_ENABLE_EXCEL", True))
            ctx["feature_powerpoint_enabled"] = bool(all_flags.get("GLOW_ENABLE_POWERPOINT", True))
            ctx["feature_pdf_enabled"] = bool(all_flags.get("GLOW_ENABLE_PDF", True))
            ctx["feature_markdown_enabled"] = bool(all_flags.get("GLOW_ENABLE_MARKDOWN", True))
            ctx["feature_epub_enabled"] = bool(all_flags.get("GLOW_ENABLE_EPUB", True))
            ctx["feature_pandoc_enabled"] = bool(all_flags.get("GLOW_ENABLE_PANDOC", True))
            ctx["feature_weasyprint_enabled"] = bool(all_flags.get("GLOW_ENABLE_WEASYPRINT", True))
            ctx["feature_daisy_ace_enabled"] = bool(all_flags.get("GLOW_ENABLE_DAISY_ACE", True))
            ctx["feature_daisy_meta_viewer_enabled"] = bool(all_flags.get("GLOW_ENABLE_DAISY_META_VIEWER", True))
            ctx["feature_daisy_pipeline_enabled"] = bool(all_flags.get("GLOW_ENABLE_DAISY_PIPELINE", True))
            ctx["feature_pymupdf_enabled"] = bool(all_flags.get("GLOW_ENABLE_PYMUPDF", True))
            ctx["feature_markitdown_enabled"] = bool(all_flags.get("GLOW_ENABLE_MARKITDOWN", True))
            # Operation-level feature flags (controls tab/card/guide visibility)
            ctx["feature_audit_enabled"] = bool(all_flags.get("GLOW_ENABLE_AUDIT", True))
            ctx["feature_checker_enabled"] = bool(all_flags.get("GLOW_ENABLE_CHECKER", True))
            ctx["feature_converter_enabled"] = bool(all_flags.get("GLOW_ENABLE_CONVERTER", True))
            ctx["feature_template_builder_enabled"] = bool(all_flags.get("GLOW_ENABLE_TEMPLATE_BUILDER", True))
            ctx["feature_export_html_enabled"] = bool(all_flags.get("GLOW_ENABLE_EXPORT_HTML", True))
            ctx["feature_export_pdf_enabled"] = bool(all_flags.get("GLOW_ENABLE_EXPORT_PDF", True))
            ctx["feature_export_word_enabled"] = bool(all_flags.get("GLOW_ENABLE_EXPORT_WORD", True))
            ctx["feature_export_markdown_enabled"] = bool(all_flags.get("GLOW_ENABLE_EXPORT_MARKDOWN", True))
            ctx["feature_convert_to_markdown_enabled"] = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_MARKDOWN", True))
            ctx["feature_convert_to_html_enabled"] = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_HTML", True))
            ctx["feature_convert_to_docx_enabled"] = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_DOCX", True))
            ctx["feature_convert_to_epub_enabled"] = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_EPUB", True))
            ctx["feature_convert_to_pdf_enabled"] = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_PDF", True))
            ctx["feature_convert_to_pipeline_enabled"] = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_PIPELINE", True))
            ctx["feature_heading_detection_enabled"] = bool(all_flags.get("GLOW_ENABLE_HEADING_DETECTION", True))
            # Additional capability flags exposed for future UI/route gating
            ctx["feature_word_setup_enabled"] = bool(all_flags.get("GLOW_ENABLE_WORD_SETUP", True))
            ctx["feature_markdown_audit_enabled"] = bool(all_flags.get("GLOW_ENABLE_MARKDOWN_AUDIT", True))
            ctx["feature_pydocx_enabled"] = bool(all_flags.get("GLOW_ENABLE_PYDOCX", True))
            ctx["feature_openpyxl_enabled"] = bool(all_flags.get("GLOW_ENABLE_OPENPYXL", True))
            ctx["feature_python_pptx_enabled"] = bool(all_flags.get("GLOW_ENABLE_PYTHON_PPTX", True))
            ctx["feature_speech_enabled"] = bool(all_flags.get("GLOW_ENABLE_SPEECH", True))
            ctx["feature_export_speech_enabled"] = bool(all_flags.get("GLOW_ENABLE_EXPORT_SPEECH", True))
            ctx["feature_convert_to_speech_enabled"] = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_SPEECH", True))
            ctx["feature_braille_enabled"] = bool(all_flags.get("GLOW_ENABLE_BRAILLE", True))
            ctx["feature_export_braille_enabled"] = bool(all_flags.get("GLOW_ENABLE_EXPORT_BRAILLE", True))
            ctx["feature_convert_to_braille_enabled"] = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_BRAILLE", True))
            ctx["feature_braille_back_translation_score_enabled"] = bool(all_flags.get("GLOW_ENABLE_BRAILLE_BACK_TRANSLATION_SCORE", True))
            ctx["feature_speech_pronunciation_dictionary_enabled"] = bool(all_flags.get("GLOW_ENABLE_SPEECH_PRONUNCIATION_DICTIONARY", True))
            ctx["feature_speech_stream_enabled"] = bool(all_flags.get("GLOW_ENABLE_SPEECH_STREAM", True))
            ctx["feature_table_advisor_enabled"] = bool(all_flags.get("GLOW_ENABLE_TABLE_ADVISOR", True))
            ctx["feature_reading_order_detection_enabled"] = bool(all_flags.get("GLOW_ENABLE_READING_ORDER_DETECTION", True))
            ctx["feature_pdf_ocr_enabled"] = bool(all_flags.get("GLOW_ENABLE_PDF_OCR", True))
            ctx["feature_document_compare_enabled"] = bool(all_flags.get("GLOW_ENABLE_DOCUMENT_COMPARE", True))
            ctx["feature_convert_to_odt_enabled"] = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_ODT", True))
            ctx["feature_cognitive_profile_enabled"] = bool(all_flags.get("GLOW_ENABLE_COGNITIVE_PROFILE", True))
            ctx["feature_forced_colors_mode_enabled"] = bool(all_flags.get("GLOW_ENABLE_FORCED_COLORS_MODE", True))
            ctx["feature_rule_contributions_enabled"] = bool(all_flags.get("GLOW_ENABLE_RULE_CONTRIBUTIONS", True))
            ctx["feature_site_audit_enabled"] = bool(all_flags.get("GLOW_ENABLE_SITE_AUDIT", True))
            ctx["feature_user_login_enabled"] = bool(all_flags.get("GLOW_ENABLE_USER_LOGIN", False))
            ctx["feature_admin_login_enabled"] = bool(all_flags.get("GLOW_ENABLE_ADMIN_LOGIN", False))
            ctx["feature_workshop_mode_enabled"] = bool(all_flags.get("GLOW_ENABLE_WORKSHOP_MODE", True))
            ctx["feature_workshop_lab_hub_enabled"] = bool(all_flags.get("GLOW_ENABLE_WORKSHOP_LAB_HUB", True))
            ctx["feature_workshop_gallery_enabled"] = bool(all_flags.get("GLOW_ENABLE_WORKSHOP_GALLERY", True))
            ctx["feature_workshop_peer_review_enabled"] = bool(all_flags.get("GLOW_ENABLE_WORKSHOP_PEER_REVIEW", True))
        except Exception:
            # Best-effort injection; templates should handle missing keys gracefully
            pass
        return ctx

    # Jinja2 filter: render lightweight Markdown to safe HTML for AI answers.
    # Covers the subset typically produced: headings, bold,
    # inline code, unordered/ordered lists, horizontal rules, and paragraphs.
    # Uses markupsafe (already a Flask dependency) for escaping.
    import re as _re
    from markupsafe import Markup, escape as _esc

    def _markdown_to_html(text: str) -> Markup:
        if not text:
            return Markup("")
        lines = text.splitlines()
        out: list[str] = []
        in_ul = in_ol = False
        ol_counter = 0

        def close_lists():
            nonlocal in_ul, in_ol, ol_counter
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False
                ol_counter = 0

        def inline(s: str) -> str:
            # Escape the whole string first, then apply inline markup.
            # All captured groups from patterns applied after _esc() are
            # already-escaped Markup strings so no further escaping is needed.
            escaped = str(_esc(s))
            # Bold (**text** or __text__)
            escaped = _re.sub(r"\*\*(.+?)\*\*", lambda m: f"<strong>{m.group(1)}</strong>", escaped)
            escaped = _re.sub(r"__(.+?)__", lambda m: f"<strong>{m.group(1)}</strong>", escaped)
            # Inline code (content already HTML-escaped above)
            escaped = _re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", escaped)
            return escaped

        for line in lines:
            raw = line.rstrip()
            # ATX headings
            m = _re.match(r"^(#{1,6})\s+(.*)", raw)
            if m:
                close_lists()
                level = len(m.group(1))
                out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
                continue
            # Horizontal rule
            if _re.match(r"^[-*_]{3,}\s*$", raw):
                close_lists()
                out.append("<hr>")
                continue
            # Unordered list item
            m = _re.match(r"^[-*+]\s+(.*)", raw)
            if m:
                if in_ol:
                    out.append("</ol>")
                    in_ol = False
                    ol_counter = 0
                if not in_ul:
                    out.append("<ul>")
                    in_ul = True
                out.append(f"<li>{inline(m.group(1))}</li>")
                continue
            # Ordered list item
            m = _re.match(r"^\d+\.\s+(.*)", raw)
            if m:
                if in_ul:
                    out.append("</ul>")
                    in_ul = False
                if not in_ol:
                    out.append("<ol>")
                    in_ol = True
                out.append(f"<li>{inline(m.group(1))}</li>")
                continue
            # Blank line
            if not raw:
                close_lists()
                out.append("")
                continue
            # Normal paragraph line
            close_lists()
            out.append(f"<p>{inline(raw)}</p>")

        close_lists()
        return Markup("\n".join(out))

    app.jinja_env.filters["markdown"] = _markdown_to_html

    def _group_findings_by_rule(findings):
        """Group an iterable of Finding-like objects by ``rule_id``.

        Returns a list of dicts (one per rule) ordered by descending severity
        weight, then by descending occurrence count, then by first appearance
        in the original list. Each dict has:

        * ``rule_id`` -- canonical rule id
        * ``first`` -- the first Finding in the group (used for the summary row)
        * ``count`` -- number of occurrences
        * ``occurrences`` -- the full list of Finding objects (preserves order)

        Templates use this to render a single summary row per rule with a
        nested accordion that lists every individual occurrence (location and
        message). This matches how the score is calculated and avoids the
        "wall of duplicates" the audit/fix tables used to show.
        """
        severity_weight = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        groups: dict[str, dict] = {}
        for idx, f in enumerate(findings or []):
            rid = getattr(f, "rule_id", None) or (f.get("rule_id") if isinstance(f, dict) else None) or ""
            if rid not in groups:
                groups[rid] = {
                    "rule_id": rid,
                    "first": f,
                    "first_index": idx,
                    "occurrences": [f],
                }
            else:
                groups[rid]["occurrences"].append(f)

        def _sort_key(g):
            sev = getattr(g["first"], "severity", None)
            sev_value = getattr(sev, "value", sev)
            sev_str = str(sev_value or "").strip().lower()
            return (
                -severity_weight.get(sev_str, 0),
                -len(g["occurrences"]),
                g["first_index"],
            )

        ordered = sorted(groups.values(), key=_sort_key)
        for g in ordered:
            g["count"] = len(g["occurrences"])
            g.pop("first_index", None)
        return ordered

    app.jinja_env.globals["group_findings_by_rule"] = _group_findings_by_rule

    # Register blueprints
    from .routes.main import main_bp
    from .routes.audit import audit_bp
    from .routes.fix import fix_bp
    from .routes.template import template_bp
    from .routes.export import export_bp
    from .routes.guidelines import guidelines_bp
    from .routes.feedback import feedback_bp
    from .routes.about import about_bp
    from .routes.convert import convert_bp
    from .routes.docs_pages import guide_bp, changelog_bp, prd_bp, deployment_bp, faq_bp, announcement_bp
    from .routes.settings import ai_bp, settings_bp
    from .routes.privacy import privacy_bp
    from .routes.whisperer import whisperer_bp
    from .routes.consent import consent_bp, consent_required
    from .routes.process import process_bp
    from .routes.chat import chat_bp
    from .routes.playground import playground_bp
    from .routes.admin import admin_bp
    from .routes.rules_ref import rules_ref_bp
    from .routes.speech import speech_bp
    from .routes.page_flow import page_flow_bp
    from .routes.braille import braille_bp
    from .routes.magic import magic_bp
    from .routes.site_audit import site_audit_bp
    from .routes.ai_usage import ai_usage_bp
    from .routes.alt_text import alt_text_bp
    from .routes.jobs import jobs_bp
    from .routes.workshop import workshop_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(consent_bp, url_prefix="/consent")
    app.register_blueprint(process_bp, url_prefix="/process")
    app.register_blueprint(audit_bp, url_prefix="/audit")
    app.register_blueprint(fix_bp, url_prefix="/fix")
    app.register_blueprint(template_bp, url_prefix="/template")
    app.register_blueprint(export_bp, url_prefix="/export")
    app.register_blueprint(convert_bp, url_prefix="/convert")
    app.register_blueprint(whisperer_bp, url_prefix="/whisperer")
    app.register_blueprint(guidelines_bp, url_prefix="/guidelines")
    app.register_blueprint(guide_bp, url_prefix="/guide")
    app.register_blueprint(changelog_bp, url_prefix="/changelog")
    app.register_blueprint(prd_bp, url_prefix="/prd")
    app.register_blueprint(deployment_bp, url_prefix="/deployment")
    app.register_blueprint(faq_bp, url_prefix="/faq")
    app.register_blueprint(announcement_bp, url_prefix="/announcement")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    app.register_blueprint(ai_bp, url_prefix="/ai")
    app.register_blueprint(feedback_bp, url_prefix="/feedback")
    app.register_blueprint(about_bp, url_prefix="/about")
    app.register_blueprint(privacy_bp, url_prefix="/privacy")
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(playground_bp, url_prefix="/beta/chat")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(rules_ref_bp, url_prefix="/rules")
    app.register_blueprint(speech_bp, url_prefix="/speech")
    app.register_blueprint(page_flow_bp, url_prefix="/page-flow")
    app.register_blueprint(braille_bp, url_prefix="/braille")
    app.register_blueprint(magic_bp, url_prefix="/magic")
    app.register_blueprint(site_audit_bp, url_prefix="/site-audit")
    app.register_blueprint(ai_usage_bp, url_prefix="/ai/usage")
    app.register_blueprint(alt_text_bp, url_prefix="/alt-text")
    app.register_blueprint(jobs_bp, url_prefix="/job")
    app.register_blueprint(workshop_bp, url_prefix="/workshop")

    # Configure speech engine model directory from instance path
    try:
        from . import speech as _speech_mod
        _speech_mod.configure(os.path.join(app.instance_path, "speech_models"))
    except Exception:
        pass

    # Startup ready log -- emitted once per worker process launch
    try:
        from importlib.metadata import version as _pkg_version
        _web_ver = _pkg_version("acb-large-print-web")
        _core_ver = _pkg_version("acb-large-print")
    except Exception:
        _web_ver = _core_ver = "unknown"
    app.logger.info(
        "GLOW startup: web=%s core=%s maintenance=%s log_level=%s",
        _web_ver,
        _core_ver,
        os.environ.get("MAINTENANCE_MODE", "0"),
        os.environ.get("LOG_LEVEL", "INFO"),
    )

    # Seed defaults for feature flags on first startup (if no persisted flags exist).
    try:
        from . import feature_flags as _feature_flags
        from pathlib import Path as _Path

        ff_path = _Path(app.instance_path) / "feature_flags.json"
        if not ff_path.exists():
            with app.app_context():
                app.logger.info("Seeding default feature flags into instance/feature_flags.json")
                _feature_flags.reset_defaults()
    except Exception:
        app.logger.debug("Failed to seed default feature flags (continuing)")

    # Maintenance mode: gate all requests except /health and /status when
    # MAINTENANCE_MODE=1. This allows safe deployment-time downtime while
    # keeping service diagnostics available.
    @app.before_request
    def check_maintenance_mode():
        from flask import request as req
        maintenance_mode = os.environ.get("MAINTENANCE_MODE", "0") == "1"
        if maintenance_mode and req.path not in {"/health", "/status"}:
            return render_template("maintenance.html"), 503

    # Consent gate: redirect first-time visitors to the agreement page.
    # Skipped in test mode so existing tests don't need consent cookies.
    @app.before_request
    def require_consent():
        if app.testing:
            return None
        from flask import redirect, request as req, url_for as _url_for
        if consent_required(req):
            return redirect(
                _url_for("consent.consent_form", next=req.full_path.rstrip("?"))
            )

    def _build_health_payload() -> tuple[dict, bool]:
        from .gating import get_capacity_metrics
        from .ai_gateway import (
            get_admin_stats,
            is_ai_configured,
            is_budget_exhausted,
        )
        from . import feature_flags as _ff
        from acb_large_print.braille_converter import (
            braille_available,
            get_unavailability_reason,
            louis_version,
        )
        from .speech import get_engine_status
        import time as _htime

        _hstart = _htime.monotonic()

        capacity = get_capacity_metrics()
        admin_stats = get_admin_stats()
        ai_configured = is_ai_configured()
        budget_ok = not is_budget_exhausted()
        all_flags = _ff.get_all_flags()

        deployment = {
            "state": "idle",
            "phase": "none",
            "detail": "No deployment is currently in progress.",
            "updated_at_utc": None,
            "gates": {
                "wcag22aa": "not-reported",
                "wcag22aaa": "not-reported",
            },
        }
        try:
            deploy_status_path = Path(app.instance_path) / "deploy-status.json"
            if deploy_status_path.exists():
                parsed = json.loads(deploy_status_path.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    deployment.update({
                        "state": str(parsed.get("state", deployment["state"])),
                        "phase": str(parsed.get("phase", deployment["phase"])),
                        "detail": str(parsed.get("detail", deployment["detail"])),
                        "updated_at_utc": parsed.get("updated_at_utc", deployment["updated_at_utc"]),
                    })
                    gates = parsed.get("gates")
                    if isinstance(gates, dict):
                        deployment["gates"]["wcag22aa"] = str(gates.get("wcag22aa", deployment["gates"]["wcag22aa"]))
                        deployment["gates"]["wcag22aaa"] = str(gates.get("wcag22aaa", deployment["gates"]["wcag22aaa"]))
        except Exception:
            pass

        speech_enabled = bool(all_flags.get("GLOW_ENABLE_SPEECH", True))
        braille_enabled = bool(all_flags.get("GLOW_ENABLE_BRAILLE", True))

        # Live reachability probes (non-blocking, short timeout)
        openrouter_probe = _probe_openrouter() if ai_configured else {
            "status": "not-configured",
            "detail": "OPENROUTER_API_KEY not set -- AI features disabled",
        }
        whisper_probe = _probe_whisper() if ai_configured else {
            "status": "not-configured",
            "detail": "OPENROUTER_API_KEY not set -- Whisperer disabled",
        }
        from .keycloak import get_keycloak_health_url
        keycloak_url = get_keycloak_health_url()
        if keycloak_url:
            try:
                import requests as _requests

                resp = _requests.get(keycloak_url, timeout=3)
                keycloak_probe = {
                    "status": "ok" if resp.status_code == 200 else "unhealthy",
                    "detail": (
                        f"Keycloak reachable (HTTP {resp.status_code})"
                        if resp.status_code == 200
                        else f"Keycloak returned HTTP {resp.status_code}"
                    ),
                }
            except Exception as exc:
                keycloak_probe = {
                    "status": "unreachable",
                    "detail": f"Keycloak probe failed: {exc}",
                }
        else:
            keycloak_probe = {
                "status": "not-configured",
                "detail": "Keycloak OIDC is not configured",
            }

        if speech_enabled:
            try:
                speech_engine_status = get_engine_status()
                kokoro_ready = bool(speech_engine_status.get("kokoro", {}).get("ready"))
                piper_ready = bool(speech_engine_status.get("piper", {}).get("ready"))
                speech_ready = kokoro_ready or piper_ready
                speech_probe = {
                    "status": "ok" if speech_ready else "not-ready",
                    "detail": (
                        "Speech Studio ready"
                        if speech_ready
                        else "Speech enabled but no speech engine is ready"
                    ),
                    "kokoro_ready": kokoro_ready,
                    "piper_ready": piper_ready,
                }
            except Exception as exc:
                speech_probe = {
                    "status": "error",
                    "detail": f"Speech status probe failed: {exc}",
                }
        else:
            speech_probe = {
                "status": "not-configured",
                "detail": "GLOW_ENABLE_SPEECH is disabled",
            }

        if braille_enabled:
            try:
                braille_ready = braille_available()
                braille_version = louis_version()
                if not isinstance(braille_version, str):
                    braille_version = str(braille_version)
                braille_probe = {
                    "status": "ok" if braille_ready else "not-ready",
                    "detail": (
                        f"Braille Studio ready (liblouis {braille_version})"
                        if braille_ready
                        else get_unavailability_reason()
                    ),
                    "louis_version": braille_version,
                }
            except Exception as exc:
                braille_probe = {
                    "status": "error",
                    "detail": f"Braille status probe failed: {exc}",
                }
        else:
            braille_probe = {
                "status": "not-configured",
                "detail": "GLOW_ENABLE_BRAILLE is disabled",
            }

        services = {
            "web": {"status": "ok", "detail": "service responding"},
            "keycloak": keycloak_probe,
            "openrouter": openrouter_probe,
            "whisper": whisper_probe,
            "speech": speech_probe,
            "braille": braille_probe,
        }

        readiness = {
            "chat": {
                "status": "ready" if ai_configured and budget_ok and openrouter_probe["status"] == "ok" else "not-ready",
                "provider": "openrouter",
                "key_set": ai_configured,
                "reachable": openrouter_probe["status"] == "ok",
                "budget_ok": budget_ok,
            },
            "vision": {
                "status": "ready" if ai_configured and budget_ok and openrouter_probe["status"] == "ok" else "not-ready",
                "provider": "openrouter",
                "key_set": ai_configured,
                "reachable": openrouter_probe["status"] == "ok",
                "budget_ok": budget_ok,
            },
            "whisperer": {
                "status": "ready" if ai_configured and whisper_probe["status"] == "ok" else "not-ready",
                "provider": "openrouter",
                "key_set": ai_configured,
                "reachable": whisper_probe["status"] == "ok",
            },
            "keycloak": {
                "status": "ready" if keycloak_probe["status"] == "ok" else keycloak_probe["status"],
                "enabled": keycloak_probe["status"] != "not-configured",
                "reachable": keycloak_probe["status"] == "ok",
            },
            "speech": {
                "status": (
                    "ready"
                    if speech_enabled and speech_probe["status"] == "ok"
                    else ("not-configured" if not speech_enabled else "not-ready")
                ),
                "enabled": speech_enabled,
                "reachable": speech_probe["status"] == "ok",
            },
            "braille": {
                "status": (
                    "ready"
                    if braille_enabled and braille_probe["status"] == "ok"
                    else ("not-configured" if not braille_enabled else "not-ready")
                ),
                "enabled": braille_enabled,
                "reachable": braille_probe["status"] == "ok",
                "louis_version": braille_probe.get("louis_version", "unavailable"),
            },
            "budget": {
                "status": "ok" if budget_ok else "exhausted",
                "monthly_budget_usd": admin_stats.get("budget_usd", 20.0),
                "monthly_spend_usd": admin_stats.get("monthly_spend", 0.0),
                "pct_used": round(
                    min(100.0, admin_stats.get("monthly_spend", 0.0)
                        / max(admin_stats.get("budget_usd", 20.0), 0.01) * 100),
                    1,
                ),
            },
            "wcag22aa_gate": {
                "status": deployment["gates"]["wcag22aa"],
            },
            "wcag22aaa_gate": {
                "status": deployment["gates"]["wcag22aaa"],
            },
        }

        # Overall status: web always ok; degrade when configured dependencies
        # are unavailable.
        provider_ok = (not ai_configured or openrouter_probe["status"] == "ok")
        keycloak_ok = keycloak_probe["status"] in ("ok", "not-configured")
        speech_ok = (not speech_enabled) or (speech_probe["status"] == "ok")
        braille_ok = (not braille_enabled) or (braille_probe["status"] == "ok")
        all_ok = provider_ok and budget_ok and keycloak_ok and speech_ok and braille_ok

        _hduration_ms = round((_htime.monotonic() - _hstart) * 1000)
        app.logger.info(
            "HEALTH status=%s openrouter=%s keycloak=%s whisper=%s speech=%s braille=%s budget_pct=%.1f%% duration_ms=%d",
            "ok" if all_ok else "degraded",
            openrouter_probe["status"],
            keycloak_probe["status"],
            whisper_probe["status"],
            speech_probe["status"],
            braille_probe["status"],
            readiness["budget"]["pct_used"],
            _hduration_ms,
        )

        payload = {
            "status": "ok" if all_ok else "degraded",
            "services": services,
            "readiness": readiness,
            "models": {
                "chat_default": admin_stats.get("default_model", "n/a"),
                "chat_fallback": admin_stats.get("fallback_model", "n/a"),
                "vision": admin_stats.get("vision_model", "n/a"),
                # audio_path_active reflects which path GLOW tries first:
                # input_audio (gpt-audio-mini) is the primary; direct
                # (whisper-large-v3) is only used if primary fails.
                "whisper_fallback": admin_stats.get("whisper_model", "openai/whisper-large-v3"),
                "audio_primary": "openai/gpt-audio-mini",
                "audio_path_active": "input_audio",
            },
            "feature_flags": all_flags,
            "feature_flag_summary": {
                "enabled": sum(1 for _k, _v in all_flags.items() if _v),
                "disabled": sum(1 for _k, _v in all_flags.items() if not _v),
                "total": len(all_flags),
            },
            "capacity": capacity,
            "deployment": deployment,
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "duration_ms": _hduration_ms,
        }
        return payload, all_ok

    # Health check
    @app.route("/health")
    def health():
        payload, _all_ok = _build_health_payload()
        return jsonify(payload), 200

    @app.route("/status")
    def status_page():
        import json as _json

        payload, _all_ok = _build_health_payload()
        return render_template(
            "status.html",
            health=payload,
            pretty_json=_json.dumps(payload, indent=2, sort_keys=True),
        )

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        return _render_error(
            "Session Expired",
            "Your form session has expired. Please go back, refresh the page, "
            "and try again.",
            400,
        )

    # Error handlers
    @app.errorhandler(413)
    def too_large(e):
        return _render_error(
            "File Too Large",
            "The uploaded file exceeds the 500 MB size limit. "
            "Please upload a smaller file.",
            413,
        )

    @app.errorhandler(404)
    def not_found(e):
        return _render_error(
            "Page Not Found",
            "The page you requested does not exist.",
            404,
        )

    @app.errorhandler(403)
    def forbidden(e):
        return _render_error(
            "Access Denied",
            "You do not have permission to access this page.",
            403,
        )

    @app.errorhandler(500)
    def server_error(e):
        return _render_error(
            "Server Error",
            "Something went wrong while processing your request. " "Please try again.",
            500,
        )

    @app.errorhandler(429)
    def rate_limited(e):
        return _render_error(
            "Too Many Requests",
            "You have made too many requests in a short period. "
            "Please wait a moment and try again.",
            429,
        )

    # Security response headers applied to every response.
    # X-Content-Type-Options prevents MIME-sniffing attacks.
    # X-Frame-Options prevents clickjacking.
    # Referrer-Policy limits information leakage in Referer headers.
    @app.after_request
    def _add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    # Cleanup stale uploads on startup
    @app.before_request
    def cleanup_stale_uploads():
        """Clean up old temporary uploads once per minute, worker-safe.

        Uses a lock file in the instance directory so that only one of the
        N Gunicorn workers runs the sweep at a time.  The lock file stores the
        epoch timestamp of the last successful sweep; any worker that reads a
        timestamp younger than 60 s skips the sweep entirely.
        """
        import time
        from pathlib import Path as _Path
        from . import upload

        now = time.time()
        lock_path = _Path(app.instance_path) / ".cleanup_lock"
        try:
            # Fast path: read existing timestamp without acquiring a lock.
            if lock_path.exists():
                try:
                    last = float(lock_path.read_text(encoding="ascii").strip())
                    if now - last < 60:
                        return
                except Exception:
                    pass
            # Slow path: try to atomically claim the sweep slot.
            # O_CREAT | O_EXCL fails if another worker already created the
            # temp file; that worker owns this sweep cycle.
            tmp = lock_path.with_suffix(".tmp")
            try:
                fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.write(fd, str(now).encode())
                os.close(fd)
                os.replace(str(tmp), str(lock_path))
            except FileExistsError:
                return  # Another worker won the race; skip.
            # This worker owns the sweep.
            max_age = int(os.environ.get("UPLOAD_MAX_AGE_HOURS", "1"))
            upload.cleanup_stale_uploads(max_age_hours=max_age)
            try:
                from .report_cache import sweep_expired_shares as _sweep_shares
                _sweep_shares()
            except Exception:
                pass
        except Exception:
            pass  # Never crash a user request due to cleanup failure

    from .routes.status import status_bp

    app.register_blueprint(status_bp)

    # --- OIDC Authentication Integration ---
    try:
        from flask_oidc import OpenIDConnect
        from .oidc_auth import oidc_auth_bp
        from .keycloak import build_oidc_settings

        oidc_settings = build_oidc_settings()
        if oidc_settings is None:
            app.logger.warning(
                "OIDC authentication is disabled until KEYCLOAK_BASE_URL, KEYCLOAK_REALM, "
                "KEYCLOAK_CLIENT_ID, KEYCLOAK_CLIENT_SECRET, and KEYCLOAK_REDIRECT_URI are set."
            )
        else:
            app.config.update(oidc_settings)
            OpenIDConnect(app)
            app.register_blueprint(oidc_auth_bp)
            app.logger.info("OIDC authentication enabled (Keycloak)")
    except ImportError:
        app.logger.warning("Flask-OIDC not installed; OIDC authentication is disabled.")
    except Exception as exc:
        app.logger.error(f"OIDC authentication setup failed: {exc}")
    # --- End OIDC Integration ---

    return app


def _configure_logging(app: Flask) -> None:
    """Set up structured logging."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Also configure the package-level logger
    pkg_logger = logging.getLogger("acb_large_print_web")
    pkg_logger.handlers.clear()
    pkg_logger.addHandler(handler)
    pkg_logger.setLevel(getattr(logging, log_level, logging.INFO))


def _render_error(title: str, message: str, code: int):
    """Render an error page."""
    from flask import render_template

    return render_template("error.html", title=title, message=message), code


def _probe_openrouter(timeout: float = 4.0) -> dict[str, str]:
    """Probe OpenRouter /models to verify the key is valid and the service is reachable.

    Returns a status dict with keys 'status' ("ok" | "unreachable" | "auth-error")
    and 'detail' for display in the health response.
    We hit /models (a cheap, read-only endpoint) with a short timeout.
    No content is sent -- this is purely a connectivity + auth check.
    """
    from .credentials import get_openrouter_api_key
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError, URLError

    key = get_openrouter_api_key()
    if not key:
        return {"status": "not-configured", "detail": "OPENROUTER_API_KEY not set"}

    req = Request(
        "https://openrouter.ai/api/v1/models",
        headers={
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://letitglow.app",
            "X-Title": "GLOW Health Check",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310
            code = getattr(resp, "status", 200)
            if 200 <= code < 300:
                return {"status": "ok", "detail": f"reachable (HTTP {code})"}
            return {"status": "degraded", "detail": f"unexpected HTTP {code}"}
    except HTTPError as exc:
        if exc.code in (401, 403):
            return {"status": "auth-error", "detail": f"API key rejected (HTTP {exc.code})"}
        return {"status": "degraded", "detail": f"HTTP {exc.code} from OpenRouter"}
    except URLError as exc:
        return {"status": "unreachable", "detail": f"Network error: {exc.reason}"}
    except Exception as exc:  # pragma: no cover
        return {"status": "unreachable", "detail": str(exc)}


def _probe_whisper(timeout: float = 4.0) -> dict[str, str]:
    """Whisperer uses the same OpenRouter key -- delegate to the OpenRouter probe."""
    return _probe_openrouter(timeout=timeout)
