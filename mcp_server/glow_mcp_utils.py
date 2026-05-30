"""
GLOW MCP Server - Core integration utilities

This module dispatches to the correct GLOW audit, fix, convert, and report logic
based on file format. It is used by the FastAPI endpoints in main.py.
"""
from pathlib import Path
import tempfile
import sys

from acb_large_print.pandoc_converter import convert_to_html, convert_to_docx
from acb_large_print.reporter import generate_json_report, generate_text_report, generate_html_report

SUPPORTED_FORMATS = {"markdown", "md", "docx", "html"}


def _resolve_core_services():
    """Return (audit_by_extension, convert_to_markdown, fix_by_extension).

    Import lazily so module import does not fail in environments where shared
    core packages are not installed but endpoints that need them are not used.
    """
    try:
        from quill_glow_core import audit_by_extension, convert_to_markdown, fix_by_extension

        return audit_by_extension, convert_to_markdown, fix_by_extension
    except Exception as exc:
        raise RuntimeError(
            "Shared core services unavailable. Install quill-glow-core for MCP operations."
        ) from exc


def run_page_flow_extract(source_url: str, *, max_pages: int = 5, follow_pagination: bool = True):
    """Extract readable article text from a web URL using PageFlow logic.

    Returns a JSON-serializable dictionary with normalized article details.
    """
    if not source_url or not str(source_url).strip():
        raise ValueError("source_url is required")

    # Prefer direct import when package path is already configured.
    try:
        from acb_large_print_web.listen_later import extract_article, ArticleExtractionError
    except ImportError:
        # Fallback for standalone mcp_server execution: add web/src to path.
        project_root = Path(__file__).resolve().parents[1]
        web_src = project_root / "web" / "src"
        if str(web_src) not in sys.path:
            sys.path.insert(0, str(web_src))
        try:
            from acb_large_print_web.listen_later import extract_article, ArticleExtractionError
        except Exception as exc:
            raise RuntimeError(
                "PageFlow extraction requires web/src/acb_large_print_web to be importable"
            ) from exc

    try:
        article = extract_article(
            str(source_url).strip(),
            max_pages=max(1, int(max_pages)),
            follow_pagination=bool(follow_pagination),
        )
    except ArticleExtractionError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "source_url": article.source_url,
        "final_url": article.final_url,
        "title": article.title,
        "text": article.text,
        "page_urls": list(article.page_urls),
        "page_count": len(article.page_urls),
        "char_count": len(article.text or ""),
    }


def run_audit(file_path: Path, fmt: str):
    """Dispatch to the correct audit function based on format."""
    audit_by_extension, _convert_to_markdown, _fix_by_extension = _resolve_core_services()
    fmt = fmt.lower()
    if fmt in ("markdown", "md", "docx"):
        return audit_by_extension(file_path)
    raise ValueError(f"Unsupported format for audit: {fmt}")


def run_fix(file_path: Path, fmt: str, output_path: Path = None):
    """Dispatch to the correct fix function based on format."""
    _audit_by_extension, _convert_to_markdown, fix_by_extension = _resolve_core_services()
    fmt = fmt.lower()
    if fmt == "docx":
        return fix_by_extension(file_path, output_path=output_path)
    raise ValueError(f"Unsupported format for fix: {fmt}")


def run_convert(file_path: Path, from_fmt: str, to_fmt: str, output_path: Path = None):
    """Dispatch to the correct convert function based on formats."""
    _audit_by_extension, convert_to_markdown, _fix_by_extension = _resolve_core_services()
    from_fmt = from_fmt.lower()
    to_fmt = to_fmt.lower()
    if from_fmt == "docx" and to_fmt in ("markdown", "md"):
        return convert_to_markdown(file_path, output_path)
    if from_fmt == "docx" and to_fmt == "html":
        return convert_to_html(file_path, output_path)
    if from_fmt in ("markdown", "md") and to_fmt == "docx":
        return convert_to_docx(file_path, output_path)
    if from_fmt in ("markdown", "md") and to_fmt == "html":
        # Convert markdown to docx, then docx to html
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path, _ = convert_to_docx(file_path, Path(tmpdir) / "temp.docx")
            return convert_to_html(docx_path, output_path)
    raise ValueError(f"Unsupported conversion: {from_fmt} -> {to_fmt}")


def run_report(audit_result, report_type: str = "json"):
    """Generate a report from an AuditResult."""
    if report_type == "json":
        return generate_json_report(audit_result)
    if report_type == "text":
        return generate_text_report(audit_result)
    if report_type == "html":
        return generate_html_report(audit_result)
    raise ValueError(f"Unsupported report type: {report_type}")
