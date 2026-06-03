"""Canonical shared dispatch services for GLOW desktop/web/CLI."""

from __future__ import annotations

from pathlib import Path

SUPPORTED_AUDIT_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".md", ".pdf", ".epub"}
SUPPORTED_FIX_EXTENSIONS = set(SUPPORTED_AUDIT_EXTENSIONS)


def audit_by_extension(
    file_path: str | Path,
    *,
    list_indent_in: float | None = None,
    list_level_indents: dict[int, float] | None = None,
    para_indent_in: float | None = None,
    first_line_indent_in: float | None = None,
    style_size_overrides: dict[str, float] | None = None,
):
    """Run the appropriate auditor for the file extension."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".xlsx":
        from acb_large_print.xlsx_auditor import audit_workbook

        return audit_workbook(path)
    if ext == ".pptx":
        from acb_large_print.pptx_auditor import audit_presentation

        return audit_presentation(path)
    if ext == ".md":
        from acb_large_print.md_auditor import audit_markdown

        return audit_markdown(path)
    if ext == ".pdf":
        from acb_large_print.pdf_auditor import audit_pdf

        return audit_pdf(path)
    if ext == ".epub":
        from acb_large_print.epub_auditor import audit_epub

        return audit_epub(path)

    from acb_large_print.auditor import audit_document

    return audit_document(
        path,
        list_indent_in=list_indent_in,
        list_level_indents=list_level_indents,
        para_indent_in=para_indent_in,
        first_line_indent_in=first_line_indent_in,
        style_size_overrides=style_size_overrides,
    )


def fix_by_extension(
    file_path: str | Path,
    output_path: str | Path | None = None,
    *,
    bound: bool = False,
    list_indent_in: float = 0.0,
    list_hanging_in: float = 0.0,
    list_level_indents: dict[int, float] | None = None,
    para_indent_in: float = 0.0,
    first_line_indent_in: float = 0.0,
    preserve_heading_alignment: bool = False,
    detect_headings: bool = False,
    ai_provider: object | None = None,
    heading_threshold: int | None = None,
    confirmed_headings: list | None = None,
    heading_accuracy_level: str = "balanced",
    style_size_overrides: dict[str, float] | None = None,
):
    """Run fixer workflow for the extension.

    Returns (output_path, total_fixes, fix_records, post_audit, warnings).
    """
    path = Path(file_path)
    out = Path(output_path) if output_path is not None else None
    ext = path.suffix.lower()

    if ext == ".xlsx":
        post_audit = audit_by_extension(path)
        return (
            path,
            0,
            [],
            post_audit,
            [
                "Excel workbooks cannot be auto-fixed yet. "
                "Review the audit findings and fix them manually in Excel."
            ],
        )
    if ext == ".pptx":
        post_audit = audit_by_extension(path)
        return (
            path,
            0,
            [],
            post_audit,
            [
                "PowerPoint presentations cannot be auto-fixed yet. "
                "Review the audit findings and fix them manually in PowerPoint."
            ],
        )
    if ext == ".md":
        post_audit = audit_by_extension(path)
        return (
            path,
            0,
            [],
            post_audit,
            [
                "Markdown auto-fix is coming soon. "
                "Review the audit findings and fix them in your text editor."
            ],
        )
    if ext == ".pdf":
        post_audit = audit_by_extension(path)
        return (
            path,
            0,
            [],
            post_audit,
            [
                "PDF files cannot be auto-fixed. "
                "Use Adobe Acrobat Pro or re-export from the source application."
            ],
        )
    if ext == ".epub":
        post_audit = audit_by_extension(path)
        return (
            path,
            0,
            [],
            post_audit,
            [
                "ePub files cannot be auto-fixed yet. "
                "Review the audit findings and fix them in your ePub editor."
            ],
        )

    from acb_large_print.fixer import fix_document

    return fix_document(
        path,
        output_path=out,
        bound=bound,
        list_indent_in=list_indent_in,
        list_hanging_in=list_hanging_in,
        list_level_indents=list_level_indents,
        para_indent_in=para_indent_in,
        first_line_indent_in=first_line_indent_in,
        preserve_heading_alignment=preserve_heading_alignment,
        detect_headings=detect_headings,
        ai_provider=ai_provider,
        heading_threshold=heading_threshold,
        confirmed_headings=confirmed_headings,
        heading_accuracy_level=heading_accuracy_level,
        style_size_overrides=style_size_overrides,
    )


from acb_large_print import converter as _converter  # noqa: E402

CONVERTIBLE_EXTENSIONS = _converter.CONVERTIBLE_EXTENSIONS
MARKITDOWN_AUDIO_EXTENSIONS = _converter.MARKITDOWN_AUDIO_EXTENSIONS


def convert_to_markdown(src_path: str | Path, output_path: str | Path | None = None):
    """Convert source document to Markdown via shared MarkItDown pipeline."""
    return _converter.convert_to_markdown(src_path, output_path=output_path)
