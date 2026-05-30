"""Convert route -- convert documents via MarkItDown, Pandoc, WeasyPrint, or DAISY Pipeline.

Seven conversion directions:
1. To Markdown (MarkItDown): .docx, .xlsx, .pptx, .pdf, .html, .csv, etc.
2. To ACB HTML (Pandoc, or MarkItDown→Pandoc): .md, .rst, .odt, .rtf, .docx, .epub,
   plus chained: .pptx, .xlsx, .xls, .pdf, .csv, .html, .htm, .json, .xml
3. To Word .docx (Pandoc, or MarkItDown→Pandoc): .md, .rst, .odt, .rtf, .epub,
   plus chained: .pptx, .xlsx, .xls, .pdf, .csv, .html, .htm, .json, .xml
4. To EPUB 3 (Pandoc, or MarkItDown→Pandoc): .md, .rst, .odt, .rtf, .docx,
   plus chained: .pptx, .xlsx, .xls, .pdf, .csv, .html, .htm, .json, .xml
5. To PDF (Pandoc + WeasyPrint, or MarkItDown→Pandoc+WeasyPrint): .md, .rst, .odt,
   .rtf, .docx, .epub, plus chained: .pptx, .xlsx, .xls, .pdf, .csv, .html, .htm
6. To EPUB / DAISY (Pipeline): .docx, .html, .epub (when Pipeline is installed)

Two-stage chaining: formats not natively supported by Pandoc are first extracted to
Markdown via MarkItDown, then that Markdown is fed to Pandoc. This transparently
extends Pandoc output to PowerPoint, Excel, PDF, and other MarkItDown-readable formats.

Audio transcription has its own dedicated route at /whisperer (BITS Whisperer).
Short `.mp3` and `.wav` files may also be converted to Markdown through
MarkItDown in the standard Convert flow.
"""

import os
import uuid

from flask import Blueprint, abort, current_app, redirect, render_template, request, send_file, url_for

from werkzeug.utils import secure_filename as _secure_filename

from acb_large_print.converter import CONVERTIBLE_EXTENSIONS, MARKITDOWN_AUDIO_EXTENSIONS

try:
    from quill_glow_core import convert_to_markdown
except Exception:
    from acb_large_print_core.services import convert_to_markdown
from acb_large_print.wcag_language import (
    analyze_text_for_wcag_language,
)
from acb_large_print.exporter import export_cms_fragment
from acb_large_print.pandoc_converter import (
    PANDOC_INPUT_EXTENSIONS,
    LIBREOFFICE_CONVERSIONS,
    convert_to_html,
    convert_to_docx,
    convert_to_odt,
    convert_to_epub,
    convert_to_pdf,
    pandoc_available,
    weasyprint_available,
    libreoffice_available,
    preconvert_via_libreoffice,
)
from acb_large_print.pipeline_converter import (
    PIPELINE_INPUT_EXTENSIONS,
)
import acb_large_print.pipeline_converter as _pipeline_converter

from ..upload import (
    CONVERT_EXTENSIONS,
    UploadError,
    cleanup_token,
    get_temp_dir,
    validate_upload,
)
from ..feature_flags import get_all_flags

from pathlib import Path

from mutagen import File as MutagenFile

convert_bp = Blueprint("convert", __name__)

_MARKITDOWN_AUDIO_MAX_MB = int(os.environ.get("GLOW_MARKITDOWN_AUDIO_MAX_MB", "25"))
_MARKITDOWN_AUDIO_MAX_MINUTES = float(os.environ.get("GLOW_MARKITDOWN_AUDIO_MAX_MINUTES", "8"))

# Sentinel path used to signal "skip ACB CSS" to pandoc_converter
_NO_ACB_CSS_SENTINEL = Path("__no_acb_css__")
_ASYNC_CONVERT_ENABLED = os.environ.get("GLOW_CONVERT_ASYNC", "1") == "1"
_WCAG_LANGUAGE_STAGE_VALUES = {"off", "input", "output", "both"}
_WCAG_LANGUAGE_ENFORCEMENT_VALUES = {"advisory", "strict"}
_WCAG_LANGUAGE_TEXT_EXTENSIONS = {".md", ".rst", ".txt", ".html", ".htm", ".csv", ".json", ".xml"}


def pipeline_available() -> bool:
    return _pipeline_converter.pipeline_available()


def get_available_conversions() -> dict:
    return _pipeline_converter.get_available_conversions()


def convert_with_pipeline(*args, **kwargs):
    return _pipeline_converter.convert_with_pipeline(*args, **kwargs)


# Allowed MIME types for the download/preview routes
_DOWNLOAD_MIMETYPES: dict[str, str] = {
    ".html": "text/html; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".epub": "application/epub+zip",
    ".pdf": "application/pdf",
    ".zip": "application/zip",
}


def _resolve_convert_file(token: str, filename: str):
    """Resolve a convert download/preview request to a safe file path.

    Returns (file_path, mimetype) or aborts 404 on any failure.
    """
    safe_name = _secure_filename(filename)
    if not safe_name:
        abort(404)
    temp_dir = get_temp_dir(token)
    if not temp_dir:
        abort(404)
    file_path = temp_dir / safe_name
    # Verify the resolved path is still inside the temp dir (traversal guard)
    try:
        file_path.resolve().relative_to(temp_dir.resolve())
    except ValueError:
        abort(404)
    if not file_path.exists() or not file_path.is_file():
        abort(404)
    ext = file_path.suffix.lower()
    mimetype = _DOWNLOAD_MIMETYPES.get(ext, "application/octet-stream")
    return file_path, mimetype


@convert_bp.route("/download/<token>/<filename>", methods=["GET"])
def convert_download(token: str, filename: str):
    """Serve a previously converted file as a download."""
    file_path, mimetype = _resolve_convert_file(token, filename)
    return send_file(
        str(file_path),
        mimetype=mimetype,
        as_attachment=True,
        download_name=file_path.name,
    )


@convert_bp.route("/preview/<token>/<filename>", methods=["GET"])
def convert_preview(token: str, filename: str):
    """Serve a previously converted HTML file inline (for iframe preview)."""
    file_path, mimetype = _resolve_convert_file(token, filename)
    if file_path.suffix.lower() != ".html":
        abort(404)
    return send_file(str(file_path), mimetype=mimetype, as_attachment=False)

# Document-type formats in CONVERTIBLE_EXTENSIONS that Pandoc cannot read directly
# but are worth chaining via Markdown (excludes .zip and image formats).
# These get a two-stage conversion: MarkItDown → .md → Pandoc.
_CHAIN_VIA_MARKDOWN: frozenset[str] = frozenset({
    ".doc",   # Word (legacy binary)
    ".ppt",   # PowerPoint (legacy binary)
    ".pptx",  # PowerPoint
    ".xlsx",  # Excel
    ".xls",   # Excel (legacy)
    ".pdf",   # PDF (text-based)
    ".csv",   # CSV data
    ".html",  # HTML (re-encode with ACB styling via Pandoc)
    ".htm",   # HTML (alternate extension)
    ".json",  # JSON data
    ".xml",   # XML data
    ".ods",   # LibreOffice Calc
    ".fods",  # Flat ODF Spreadsheet
    ".odp",   # LibreOffice Impress
    ".fodp",  # Flat ODF Presentation
})

# All formats accepted by Pandoc outputs after chaining is accounted for
_PANDOC_EFFECTIVE_EXTENSIONS: frozenset[str] = (
    PANDOC_INPUT_EXTENSIONS | _CHAIN_VIA_MARKDOWN
)

# Build the accept strings for the file inputs
_MD_ACCEPT = ",".join(sorted(CONVERTIBLE_EXTENSIONS))
_HTML_ACCEPT = ",".join(sorted(_PANDOC_EFFECTIVE_EXTENSIONS))
# Union of all for a single file input (no audio -- that's /whisperer)
_ALL_ACCEPT = ",".join(
    sorted(CONVERTIBLE_EXTENSIONS | PANDOC_INPUT_EXTENSIONS | PIPELINE_INPUT_EXTENSIONS)
)


def _is_auditable_output(filename: str) -> bool:
    """Return True if the converted output's extension is supported by Audit."""
    from ..upload import ALLOWED_EXTENSIONS

    suffix = Path(filename).suffix.lower()
    return suffix in ALLOWED_EXTENSIONS


def _convert_result_response(
    token_value: str,
    *,
    download_name: str,
    preview_type: str,
    original_stem: str,
    cms_content: str | None = None,
    language_reports: list[dict[str, object]] | None = None,
):
    """Render the shared convert_result.html for a finished conversion.

    Used by every direction that produces a downloadable artefact, so the
    user lands on a page with explicit Download and (optionally) Audit
    actions instead of being thrown into a browser save dialog.
    """
    return render_template(
        "convert_result.html",
        token=token_value,
        download_name=download_name,
        preview_type=preview_type,
        original_stem=original_stem,
        cms_content=cms_content,
        auditable_output=_is_auditable_output(download_name),
        language_reports=language_reports or [],
    )


def _coerce_language_stage(raw_value: str | None, *, enabled: bool) -> str:
    if not enabled:
        return "off"
    value = (raw_value or "output").strip().lower()
    if value not in _WCAG_LANGUAGE_STAGE_VALUES:
        return "output"
    return value


def _coerce_language_enforcement(raw_value: str | None, *, strict_enabled: bool) -> str:
    value = (raw_value or "advisory").strip().lower()
    if value not in _WCAG_LANGUAGE_ENFORCEMENT_VALUES:
        return "advisory"
    if value == "strict" and not strict_enabled:
        return "advisory"
    return value


def _extract_text_for_wcag_language(path: Path, temp_dir: Path) -> str:
    ext = path.suffix.lower()
    if ext in _WCAG_LANGUAGE_TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="ignore")
    extracted_path = temp_dir / f"{path.stem}-wcag-language.md"
    try:
        _md_path, text = convert_to_markdown(path, output_path=extracted_path)
        return text
    except Exception as exc:
        current_app.logger.warning(
            "WCAG_LANGUAGE text extraction skipped for %s: %s",
            path,
            exc,
        )
        return ""


def _run_wcag_language_stage(stage: str, path: Path, temp_dir: Path) -> dict[str, object]:
    text = _extract_text_for_wcag_language(path, temp_dir)
    report = analyze_text_for_wcag_language(text, stage=stage)
    return report.to_dict()


def _format_wcag_language_error(report_dict: dict[str, object]) -> str:
    findings = report_dict.get("findings")
    stage = str(report_dict.get("stage") or "output")
    if not isinstance(findings, list):
        return f"WCAG language processing ({stage}) found blocking issues."
    report_text_lines = [f"WCAG language processing ({stage}) found blocking issue(s):"]
    for item in findings[:4]:
        if not isinstance(item, dict):
            continue
        wcag = str(item.get("wcag") or "").strip()
        wcag_label = f"WCAG {wcag}" if wcag else "WCAG"
        report_text_lines.append(
            f"- {item.get('rule_id', 'WCAG-LANGUAGE')} ({wcag_label}): {item.get('message', 'Issue detected.')}"
        )
    remaining = max(0, int(report_dict.get("total", 0)) - 4)
    if remaining:
        report_text_lines.append(f"- ...and {remaining} more.")
    return "\n".join(report_text_lines)


def _template_context(**extra):
    """Common template variables for the convert form."""
    all_flags = get_all_flags()
    convert_enabled = bool(all_flags.get("GLOW_ENABLE_CONVERTER", True))
    convert_to_markdown_enabled = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_MARKDOWN", True))
    convert_to_html_enabled = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_HTML", True))
    convert_to_docx_enabled = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_DOCX", True))
    convert_to_odt_enabled = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_ODT", True))
    convert_to_epub_enabled = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_EPUB", True))
    convert_to_pdf_enabled = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_PDF", True))
    convert_to_pipeline_enabled = bool(all_flags.get("GLOW_ENABLE_CONVERT_TO_PIPELINE", True))
    wcag_language_processing_enabled = bool(all_flags.get("GLOW_ENABLE_WCAG_LANGUAGE_PROCESSING", True))
    wcag_language_strict_enabled = bool(all_flags.get("GLOW_ENABLE_WCAG_LANGUAGE_STRICT_MODE", True))

    pipeline_conversions = (
        get_available_conversions() if convert_to_pipeline_enabled else {}
    )
    return dict(
        md_accept=_MD_ACCEPT,
        html_accept=_HTML_ACCEPT,
        all_accept=_ALL_ACCEPT,
        pandoc_installed=pandoc_available(),
        weasyprint_installed=weasyprint_available(),
        libreoffice_installed=libreoffice_available(),
        pipeline_installed=pipeline_available(),
        pipeline_conversions=pipeline_conversions,
        convert_enabled=convert_enabled,
        convert_to_markdown_enabled=convert_to_markdown_enabled,
        convert_to_html_enabled=convert_to_html_enabled,
        convert_to_docx_enabled=convert_to_docx_enabled,
        convert_to_odt_enabled=convert_to_odt_enabled,
        convert_to_epub_enabled=convert_to_epub_enabled,
        convert_to_pdf_enabled=convert_to_pdf_enabled,
        convert_to_pipeline_enabled=convert_to_pipeline_enabled,
        wcag_language_processing_enabled=wcag_language_processing_enabled,
        wcag_language_strict_enabled=wcag_language_strict_enabled,
        wcag_language_stage_default="output" if wcag_language_processing_enabled else "off",
        wcag_language_enforcement_default="advisory",
        speech_enabled=bool(all_flags.get("GLOW_ENABLE_SPEECH", True)),
        export_html_enabled=bool(all_flags.get("GLOW_ENABLE_EXPORT_HTML", True)),
        # Extension sets for JS-driven UI filtering
        chain_via_markdown_exts=sorted(_CHAIN_VIA_MARKDOWN),
        pandoc_native_exts=sorted(PANDOC_INPUT_EXTENSIONS),
        pandoc_effective_exts=sorted(_PANDOC_EFFECTIVE_EXTENSIONS),
        markitdown_exts=sorted(CONVERTIBLE_EXTENSIONS),
        speech_source_exts=sorted(CONVERTIBLE_EXTENSIONS - MARKITDOWN_AUDIO_EXTENSIONS - {".zip"}),
        pipeline_exts=sorted(PIPELINE_INPUT_EXTENSIONS),
        libreoffice_exts=sorted(LIBREOFFICE_CONVERSIONS),
        markitdown_audio_exts=sorted(MARKITDOWN_AUDIO_EXTENSIONS),
        markitdown_audio_max_mb=_MARKITDOWN_AUDIO_MAX_MB,
        markitdown_audio_max_minutes=_MARKITDOWN_AUDIO_MAX_MINUTES,
        **extra,
    )


def _estimate_audio_minutes(path: Path) -> float | None:
    """Return the best-effort duration of an audio file in minutes."""
    try:
        audio = MutagenFile(path)
    except Exception:
        return None
    info = getattr(audio, "info", None)
    length_seconds = float(getattr(info, "length", 0) or 0)
    if length_seconds <= 0:
        return None
    return length_seconds / 60.0


def _markitdown_audio_guardrail_message(path: Path) -> str | None:
    """Return a user-facing guardrail message for long MarkItDown audio jobs."""
    ext = path.suffix.lower()
    if ext not in MARKITDOWN_AUDIO_EXTENSIONS:
        return None

    size_mb = path.stat().st_size / (1024 * 1024)
    duration_minutes = _estimate_audio_minutes(path)

    too_large = size_mb > _MARKITDOWN_AUDIO_MAX_MB
    too_long = (
        duration_minutes is not None
        and duration_minutes > _MARKITDOWN_AUDIO_MAX_MINUTES
    )
    if not too_large and not too_long:
        return None

    details: list[str] = []
    if too_large:
        details.append(
            f"size {size_mb:.1f} MB exceeds the {int(_MARKITDOWN_AUDIO_MAX_MB)} MB web limit"
        )
    if too_long and duration_minutes is not None:
        details.append(
            f"duration {duration_minutes:.1f} minutes exceeds the {_MARKITDOWN_AUDIO_MAX_MINUTES:g}-minute web limit"
        )

    detail_text = "; ".join(details) if details else "the file is too large for synchronous conversion"
    return (
        "MarkItDown audio conversion in Convert is limited to short MP3/WAV files so the request does not time out. "
        f"This file cannot be processed here because {detail_text}. "
        "Use BITS Whisperer for larger recordings, background processing, or non-MP3/WAV audio formats."
    )


@convert_bp.route("/", methods=["GET"])
def convert_form():
    ctx = _template_context()
    if not ctx["convert_enabled"]:
        abort(404)

    # Quick Start handoff: ?token=... pre-fills with already-uploaded file.
    from ..upload import get_temp_dir
    prefill_token = (request.args.get("token") or "").strip()
    prefill_filename = None
    if prefill_token:
        temp_dir = get_temp_dir(prefill_token)
        if temp_dir is not None:
            for f in sorted(temp_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in CONVERT_EXTENSIONS:
                    prefill_filename = f.name
                    break
        if prefill_filename is None:
            prefill_token = None

    return render_template(
        "convert_form.html",
        prefill_token=prefill_token or None,
        prefill_filename=prefill_filename,
        **ctx,
    )


@convert_bp.route("/", methods=["POST"])
def convert_submit():
    token = None
    ctx = _template_context()
    try:
        if not ctx["convert_enabled"]:
            abort(404)

        # Quick Start handoff: re-use a previously uploaded file when the
        # form posts a session token rather than a new upload.
        from ..upload import get_temp_dir
        saved_path = None
        prefill_token = (request.form.get("token") or "").strip()
        if prefill_token and request.form.get("prefill") == "1":
            temp_dir = get_temp_dir(prefill_token)
            if temp_dir is not None:
                for f in sorted(temp_dir.iterdir()):
                    if f.is_file() and f.suffix.lower() in CONVERT_EXTENSIONS:
                        saved_path = f
                        break
            if saved_path is not None:
                token = prefill_token

        if saved_path is None:
            token, saved_path = validate_upload(
                request.files.get("document"),
                allowed_extensions=CONVERT_EXTENSIONS,
            )
        ext = saved_path.suffix.lower()
        direction = request.form.get("direction", "to-markdown")
        language_stage = _coerce_language_stage(
            request.form.get("wcag_language_stage"),
            enabled=ctx["wcag_language_processing_enabled"],
        )
        language_enforcement = _coerce_language_enforcement(
            request.form.get("wcag_language_enforcement"),
            strict_enabled=ctx["wcag_language_strict_enabled"],
        )
        ctx["wcag_language_stage_default"] = language_stage
        ctx["wcag_language_enforcement_default"] = language_enforcement

        direction_flags = {
            "to-markdown": ctx["convert_to_markdown_enabled"],
            "to-html": ctx["convert_to_html_enabled"],
            "to-html-cms": ctx["export_html_enabled"],
            "to-docx": ctx["convert_to_docx_enabled"],
            "to-odt": ctx["convert_to_odt_enabled"],
            "to-epub": ctx["convert_to_epub_enabled"],
            "to-pdf": ctx["convert_to_pdf_enabled"],
            "to-pipeline": ctx["convert_to_pipeline_enabled"],
            "to-speech": ctx["speech_enabled"],
        }
        if direction.startswith("pipeline-") and not ctx["convert_to_pipeline_enabled"]:
            raise UploadError("DAISY Pipeline conversion is disabled on this server.")
        if direction in direction_flags and not direction_flags[direction]:
            raise UploadError("That conversion direction is disabled on this server.")

        from ..tool_usage import record as _record_usage
        _record_usage("convert", detail=direction)

        temp_dir = get_temp_dir(token)
        if temp_dir is None:
            raise UploadError("Upload session expired or not found.")
        language_reports: list[dict[str, object]] = []

        def _apply_wcag_language_stage(stage_name: str, target_path: Path) -> None:
            report_dict = _run_wcag_language_stage(stage_name, target_path, temp_dir)
            language_reports.append(report_dict)
            if language_enforcement == "strict" and int(report_dict.get("error_count", 0)) > 0:
                raise UploadError(_format_wcag_language_error(report_dict))

        if language_stage in {"input", "both"} and direction != "to-speech":
            _apply_wcag_language_stage("input", saved_path)

        # Pre-convert LibreOffice-native formats before entering the normal
        # MarkItDown->Pandoc chain. If LibreOffice is missing or conversion
        # fails, continue with the original file path.
        if temp_dir is not None and ext in LIBREOFFICE_CONVERSIONS:
            lo_path = preconvert_via_libreoffice(
                saved_path,
                LIBREOFFICE_CONVERSIONS[ext],
                temp_dir,
            )
            if lo_path is not None:
                current_app.logger.info(
                    "CONVERT libreoffice_preconvert ext=%s -> %s",
                    ext,
                    lo_path.suffix.lower(),
                )
                saved_path = lo_path
                ext = saved_path.suffix.lower()

        if direction == "to-speech":
            # Seamless handoff: keep upload session and move directly to Speech Studio.
            result_token = token
            token = None
            return redirect(url_for("speech.speech_form", token=result_token))

        # Async queue path for potentially long-running conversions.
        # Keep the upload token alive for the worker by nulling token before return.
        async_op_map = {
            "to-markdown": "to_markdown",
            "to-html": "to_html",
            "to-docx": "to_docx",
            "to-odt": "to_odt",
            "to-epub": "to_epub",
            "to-pdf": "to_pdf",
            "to-pipeline": "pipeline",
        }
        if (
            _ASYNC_CONVERT_ENABLED
            and not current_app.config.get("TESTING", False)
            and language_stage == "off"
            and (direction in async_op_map or direction.startswith("pipeline-"))
        ):
            from ..tasks.convert_tasks import create_job, run_convert_job

            op = "pipeline" if direction.startswith("pipeline-") else async_op_map[direction]
            conversion_key = ""
            if direction == "to-pipeline":
                conversion_key = request.form.get("pipeline_conversion", "")
            elif direction.startswith("pipeline-"):
                conversion_key = direction.replace("pipeline-", "")

            if op == "pipeline":
                if not pipeline_available():
                    raise UploadError(
                        "DAISY Pipeline is not installed on the server. "
                        "Pipeline conversions are unavailable."
                    )
                if conversion_key not in get_available_conversions():
                    raise UploadError(
                        f"Pipeline conversion '{conversion_key}' is not available."
                    )

            options = {
                "title": (request.form.get("title", "").strip() or saved_path.stem.replace("-", " ").replace("_", " ")),
                "acb_format": request.form.get("acb_format") == "on",
                "binding_margin": request.form.get("binding_margin") == "on",
                "print_ready": request.form.get("print_ready") == "on",
                "pipeline_conversion": conversion_key,
                "llm_description": request.form.get("llm_description") == "on",
                "wcag_language_stage": language_stage,
                "wcag_language_enforcement": language_enforcement,
            }

            job_id = str(uuid.uuid4())
            create_job(
                job_id,
                op,
                saved_path.name,
                meta={
                    "op": op,
                    "upload_token": token,
                    "input_filename": saved_path.name,
                    "options": options,
                },
            )
            run_convert_job.delay(
                job_id,
                op,
                token,
                saved_path.name,
                options,
            )
            token = None
            return redirect(url_for("jobs.job_progress", job_id=job_id))

        if direction == "to-html":
            # Pandoc (or MarkItDown→Pandoc): document -> ACB HTML
            if not pandoc_available():
                raise UploadError(
                    "Pandoc is not installed on the server. "
                    "HTML conversion is unavailable."
                )
            if ext not in _PANDOC_EFFECTIVE_EXTENSIONS:
                raise UploadError(
                    f"File type '{ext}' cannot be converted to HTML. "
                    f"Supported: {', '.join(sorted(_PANDOC_EFFECTIVE_EXTENSIONS))}."
                )
            # Two-stage chain: MarkItDown -> Markdown -> Pandoc HTML
            pandoc_input = saved_path
            if ext in _CHAIN_VIA_MARKDOWN:
                md_intermediate = temp_dir / f"{saved_path.stem}-extracted.md"
                current_app.logger.info(
                    "CONVERT two_stage ext=%s stage1=markitdown->md", ext
                )
                pandoc_input, _ = convert_to_markdown(
                    saved_path, output_path=md_intermediate
                )
            html_output = temp_dir / f"{saved_path.stem}.html"

            # Read form options
            user_title = request.form.get("title", "").strip()
            title = user_title or saved_path.stem.replace("-", " ").replace("_", " ")
            acb_format = request.form.get("acb_format") == "on"
            binding_margin = request.form.get("binding_margin") == "on"
            print_ready = request.form.get("print_ready") == "on"
            generate_toc = request.form.get("generate_toc") == "on"
            format_faithful = request.form.get("format_faithful") == "on"

            # Format-faithful mode: turn off all ACB styling and post-processing.
            # User wants the closest representation of the source document with
            # no automatic adjustments.
            if format_faithful:
                acb_format = False
                binding_margin = False
                print_ready = False

            # Build CSS path: None means use built-in ACB CSS,
            # pass a blank sentinel to skip ACB CSS when unchecked
            css_path = None  # default: built-in ACB CSS
            if not acb_format:
                css_path = _NO_ACB_CSS_SENTINEL

            output_path, text = convert_to_html(
                pandoc_input,
                output_path=html_output,
                title=title,
                css_path=css_path,
                generate_toc=generate_toc,
            )

            # Post-process: inject binding margin and/or strip print stylesheet
            # (skipped automatically in format-faithful mode because acb_format
            # is forced off above).
            if acb_format and (binding_margin or not print_ready):
                html_text = output_path.read_text(encoding="utf-8")
                if binding_margin:
                    html_text = html_text.replace(
                        "padding: 1rem 1rem;",
                        "padding: 1rem 1rem 1rem 1.5rem;",
                        1,
                    )
                if not print_ready:
                    # Remove the @media print block from embedded CSS
                    import re

                    html_text = re.sub(
                        r"@media\s+print\s*\{[^}]*(?:\{[^}]*\}[^}]*)*\}",
                        "",
                        html_text,
                    )
                output_path.write_text(html_text, encoding="utf-8")

            # Preserve the temp dir for the result page download/preview routes.
            if language_stage in {"output", "both"}:
                _apply_wcag_language_stage("output", output_path)
            result_token = token
            token = None
            return _convert_result_response(
                result_token,
                download_name=f"{saved_path.stem}.html",
                preview_type="html",
                original_stem=saved_path.stem,
                language_reports=language_reports,
            )
        elif direction == "to-docx":
            if not pandoc_available():
                raise UploadError(
                    "Pandoc is not installed on the server. "
                    "Word conversion is unavailable."
                )
            if ext not in _PANDOC_EFFECTIVE_EXTENSIONS:
                raise UploadError(
                    f"File type '{ext}' cannot be converted to Word. "
                    f"Supported: {', '.join(sorted(_PANDOC_EFFECTIVE_EXTENSIONS))}."
                )
            if ext == ".docx":
                raise UploadError(
                    "The input file is already a Word document (.docx). "
                    "Choose a different input format."
                )
            # Two-stage chain: MarkItDown -> Markdown -> Pandoc .docx
            pandoc_input = saved_path
            if ext in _CHAIN_VIA_MARKDOWN:
                md_intermediate = temp_dir / f"{saved_path.stem}-extracted.md"
                current_app.logger.info(
                    "CONVERT two_stage ext=%s stage1=markitdown->md", ext
                )
                pandoc_input, _ = convert_to_markdown(
                    saved_path, output_path=md_intermediate
                )
            docx_output = temp_dir / f"{saved_path.stem}.docx"
            user_title = request.form.get("title", "").strip()
            title = user_title or saved_path.stem.replace("-", " ").replace("_", " ")
            output_path, _ = convert_to_docx(
                pandoc_input,
                output_path=docx_output,
                title=title,
            )
            if language_stage in {"output", "both"}:
                _apply_wcag_language_stage("output", output_path)
            result_token = token
            token = None
            return _convert_result_response(
                result_token,
                download_name=output_path.name,
                preview_type="binary",
                original_stem=saved_path.stem,
                language_reports=language_reports,
            )
        elif direction == "to-odt":
            if not pandoc_available():
                raise UploadError(
                    "Pandoc is not installed on the server. "
                    "ODT conversion is unavailable."
                )
            if ext not in _PANDOC_EFFECTIVE_EXTENSIONS:
                raise UploadError(
                    f"File type '{ext}' cannot be converted to ODT. "
                    f"Supported: {', '.join(sorted(_PANDOC_EFFECTIVE_EXTENSIONS))}."
                )
            if ext == ".odt":
                raise UploadError(
                    "The input file is already an OpenDocument Text (.odt). "
                    "Choose a different input format."
                )
            pandoc_input = saved_path
            if ext in _CHAIN_VIA_MARKDOWN:
                md_intermediate = temp_dir / f"{saved_path.stem}-extracted.md"
                current_app.logger.info(
                    "CONVERT two_stage ext=%s stage1=markitdown->md", ext
                )
                pandoc_input, _ = convert_to_markdown(
                    saved_path, output_path=md_intermediate
                )
            odt_output = temp_dir / f"{saved_path.stem}.odt"
            user_title = request.form.get("title", "").strip()
            title = user_title or saved_path.stem.replace("-", " ").replace("_", " ")
            output_path, _ = convert_to_odt(
                pandoc_input,
                output_path=odt_output,
                title=title,
            )
            if language_stage in {"output", "both"}:
                _apply_wcag_language_stage("output", output_path)
            result_token = token
            token = None
            return _convert_result_response(
                result_token,
                download_name=output_path.name,
                preview_type="binary",
                original_stem=saved_path.stem,
                language_reports=language_reports,
            )
        elif direction == "to-epub":
            # Pandoc (or MarkItDown->Pandoc): document -> EPUB 3
            if not pandoc_available():
                raise UploadError(
                    "Pandoc is not installed on the server. "
                    "EPUB conversion is unavailable."
                )
            if ext not in _PANDOC_EFFECTIVE_EXTENSIONS:
                raise UploadError(
                    f"File type '{ext}' cannot be converted to EPUB. "
                    f"Supported: {', '.join(sorted(_PANDOC_EFFECTIVE_EXTENSIONS))}."
                )
            if ext == ".epub":
                raise UploadError(
                    "The input file is already an EPUB. "
                    "Choose a different input format."
                )
            # Two-stage chain: MarkItDown -> Markdown -> Pandoc EPUB
            pandoc_input = saved_path
            if ext in _CHAIN_VIA_MARKDOWN:
                md_intermediate = temp_dir / f"{saved_path.stem}-extracted.md"
                current_app.logger.info(
                    "CONVERT two_stage ext=%s stage1=markitdown->md", ext
                )
                pandoc_input, _ = convert_to_markdown(
                    saved_path, output_path=md_intermediate
                )
            epub_output = temp_dir / f"{saved_path.stem}.epub"
            user_title = request.form.get("title", "").strip()
            title = user_title or saved_path.stem.replace("-", " ").replace("_", " ")
            acb_format = request.form.get("acb_format") == "on"
            css_path = None
            if not acb_format:
                css_path = _NO_ACB_CSS_SENTINEL
            output_path, _ = convert_to_epub(
                pandoc_input,
                output_path=epub_output,
                title=title,
                css_path=css_path,
            )
            if language_stage in {"output", "both"}:
                _apply_wcag_language_stage("output", output_path)
            result_token = token
            token = None
            return _convert_result_response(
                result_token,
                download_name=output_path.name,
                preview_type="binary",
                original_stem=saved_path.stem,
                language_reports=language_reports,
            )
        elif direction == "to-pdf":
            # Pandoc + WeasyPrint (or MarkItDown->Pandoc+WeasyPrint): document -> PDF
            if not pandoc_available():
                raise UploadError(
                    "Pandoc is not installed on the server. "
                    "PDF conversion is unavailable."
                )
            if not weasyprint_available():
                raise UploadError(
                    "WeasyPrint is not installed on the server. "
                    "PDF conversion is unavailable."
                )
            if ext not in _PANDOC_EFFECTIVE_EXTENSIONS:
                raise UploadError(
                    f"File type '{ext}' cannot be converted to PDF. "
                    f"Supported: {', '.join(sorted(_PANDOC_EFFECTIVE_EXTENSIONS))}."
                )
            # Two-stage chain: MarkItDown -> Markdown -> Pandoc PDF
            pandoc_input = saved_path
            if ext in _CHAIN_VIA_MARKDOWN:
                md_intermediate = temp_dir / f"{saved_path.stem}-extracted.md"
                current_app.logger.info(
                    "CONVERT two_stage ext=%s stage1=markitdown->md", ext
                )
                pandoc_input, _ = convert_to_markdown(
                    saved_path, output_path=md_intermediate
                )
            pdf_output = temp_dir / f"{saved_path.stem}.pdf"
            user_title = request.form.get("title", "").strip()
            title = user_title or saved_path.stem.replace("-", " ").replace("_", " ")
            acb_format = request.form.get("acb_format") == "on"
            binding_margin = request.form.get("binding_margin") == "on"
            css_path = None
            if not acb_format:
                css_path = _NO_ACB_CSS_SENTINEL
            output_path, _ = convert_to_pdf(
                pandoc_input,
                output_path=pdf_output,
                title=title,
                css_path=css_path,
                binding_margin=binding_margin,
            )
            if language_stage in {"output", "both"}:
                _apply_wcag_language_stage("output", output_path)
            result_token = token
            token = None
            return _convert_result_response(
                result_token,
                download_name=output_path.name,
                preview_type="binary",
                original_stem=saved_path.stem,
                language_reports=language_reports,
            )
        elif direction == "to-html-cms":
            # Exporter: .docx -> ACB-styled HTML CMS fragment for WordPress/Drupal
            if not ctx["export_html_enabled"]:
                raise UploadError("CMS Fragment export is disabled on this server.")
            if ext != ".docx":
                raise UploadError(
                    "CMS Fragment export only accepts Word (.docx) files. "
                    f"Received '{ext}'."
                )
            user_title = request.form.get("title", "").strip()
            title = user_title or None
            cms_output = temp_dir / f"{saved_path.stem}-cms.html"
            export_cms_fragment(saved_path, cms_output, title=title)
            cms_content = cms_output.read_text(encoding="utf-8")
            if language_stage in {"output", "both"}:
                _apply_wcag_language_stage("output", cms_output)
            # Preserve the temp dir for the result page download route.
            result_token = token
            token = None
            return _convert_result_response(
                result_token,
                download_name=f"{saved_path.stem}-cms.html",
                preview_type="cms",
                original_stem=saved_path.stem,
                cms_content=cms_content,
                language_reports=language_reports,
            )
        elif direction == "to-pipeline" or direction.startswith("pipeline-"):
            # DAISY Pipeline conversion
            if direction == "to-pipeline":
                conversion_key = request.form.get("pipeline_conversion", "")
            else:
                conversion_key = direction.replace("pipeline-", "")
            if not pipeline_available():
                raise UploadError(
                    "DAISY Pipeline is not installed on the server. "
                    "Pipeline conversions are unavailable."
                )
            available = get_available_conversions()
            if conversion_key not in available:
                raise UploadError(
                    f"Pipeline conversion '{conversion_key}' is not available."
                )
            output_path, summary = convert_with_pipeline(
                saved_path,
                conversion_key,
                output_dir=temp_dir,
            )
            if language_stage in {"output", "both"} and output_path.is_file():
                _apply_wcag_language_stage("output", output_path)
            if output_path.is_file():
                mimetype = (
                    "application/epub+zip"
                    if output_path.suffix == ".epub"
                    else "application/octet-stream"
                )
                return send_file(
                    str(output_path),
                    mimetype=mimetype,
                    as_attachment=True,
                    download_name=output_path.name,
                )
            else:
                # Directory output -- package as zip
                import shutil as _shutil

                zip_path = temp_dir / f"{saved_path.stem}-{conversion_key}.zip"
                _shutil.make_archive(
                    str(zip_path.with_suffix("")), "zip", str(output_path)
                )
                return send_file(
                    str(zip_path),
                    mimetype="application/zip",
                    as_attachment=True,
                    download_name=zip_path.name,
                )
        else:
            # MarkItDown: document -> Markdown (default / to-markdown direction)
            if ext not in CONVERTIBLE_EXTENSIONS:
                raise UploadError(
                    f"File type '{ext}' cannot be converted to Markdown. "
                    f"Supported: {', '.join(sorted(CONVERTIBLE_EXTENSIONS))}. "
                    "To transcribe audio, use BITS Whisperer."
                )
            audio_guardrail = _markitdown_audio_guardrail_message(saved_path)
            if audio_guardrail:
                raise UploadError(audio_guardrail)
            md_output = temp_dir / f"{saved_path.stem}.md"
            output_path, _ = convert_to_markdown(
                saved_path,
                output_path=md_output,
            )
            if language_stage in {"output", "both"}:
                _apply_wcag_language_stage("output", output_path)
            result_token = token
            token = None
            return _convert_result_response(
                result_token,
                download_name=output_path.name,
                preview_type="binary",
                original_stem=saved_path.stem,
                language_reports=language_reports,
            )

    except UploadError as exc:
        return (
            render_template(
                "convert_form.html",
                error=str(exc),
                **ctx,
            ),
            400,
        )
    except RuntimeError as exc:
        return (
            render_template(
                "convert_form.html",
                error=str(exc),
                **ctx,
            ),
            500,
        )
    except Exception as exc:
        current_app.logger.exception("CONVERT_SUBMIT unexpected_error")
        return (
            render_template(
                "convert_form.html",
                error=str(exc) or "An error occurred while converting the document. Please try again.",
                **ctx,
            ),
            500,
        )
    finally:
        if token:
            cleanup_token(token)
