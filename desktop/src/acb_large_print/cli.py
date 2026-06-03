"""Command-line interface for ACB Large Print Tool."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from . import __app_name__, __version__

log = logging.getLogger("acb_large_print")

# Respect NO_COLOR convention (https://no-color.org)
NO_COLOR = bool(os.environ.get("NO_COLOR"))


def _configure_logging(args: argparse.Namespace) -> None:
    """Set up logging based on --quiet / --verbose flags."""
    if getattr(args, "quiet", False):
        level = logging.WARNING
    elif getattr(args, "verbose", False):
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        stream=sys.stderr,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="acb-large-print",
        description=(
            "GLOW -- audit, fix, and create "
            "Office document templates that comply with the American "
            "Council of the Blind Large Print Guidelines."
        ),
        epilog=(
            "Examples:\n"
            "  acb-large-print audit report.docx\n"
            "  acb-large-print audit budget.xlsx\n"
            "  acb-large-print audit slides.pptx\n"
            "  acb-large-print audit book.epub\n"
            "  acb-large-print audit report.docx -f json -o report.json\n"
            "  acb-large-print fix  report.docx -o report-fixed.docx\n"
            "  acb-large-print fix  report.docx -o fixed.docx -b\n"
            "  acb-large-print fix  report.docx --dry-run\n"
            "  acb-large-print template -t 'Meeting Minutes'\n"
            "  acb-large-print batch audit docs/ -r -f json\n"
            "  acb-large-print batch fix docs/ -r -d fixed/\n"
            "  acb-large-print export report.docx --cms\n"
            "  acb-large-print convert slides.pptx\n"
            "  acb-large-print convert report.pdf -o report.md\n"
            "  acb-large-print convert-html notes.md\n"
            "  acb-large-print convert-html report.rst -o report.html\n"
            "\n"
            "Exit codes:\n"
            "  0  Success\n"
            "  1  Error (file not found, invalid arguments)\n"
            "  2  Audit completed with findings (document is non-compliant)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"{__app_name__} {__version__}",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress informational messages; only output results",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed processing information",
    )

    sub = parser.add_subparsers(dest="command", required=False)

    # ---- audit ----
    audit_p = sub.add_parser(
        "audit",
        help="Audit a document for ACB compliance",
        description="Scan a .docx, .xlsx, .pptx, or .epub file and report all ACB guideline violations.",
    )
    audit_p.add_argument(
        "file", type=Path, help="Path to .docx, .xlsx, .pptx, or .epub file to audit"
    )
    audit_p.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    audit_p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Save report to file instead of printing to console",
    )

    # ---- fix ----
    fix_p = sub.add_parser(
        "fix",
        help="Fix a document for ACB compliance",
        description="Automatically fix ACB compliance issues in a .docx file. Excel, PowerPoint, and ePub files are audited with manual fix guidance.",
    )
    fix_p.add_argument(
        "file", type=Path, help="Path to .docx, .xlsx, .pptx, or .epub file to fix"
    )
    fix_p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output file path (default: overwrites input)",
    )
    fix_p.add_argument(
        "--bound",
        "-b",
        action="store_true",
        help="Add binding margin (0.5 inch extra on left)",
    )
    fix_p.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would change without modifying any files",
    )
    fix_p.add_argument(
        "--flush-lists",
        action="store_true",
        default=True,
        help="Flush list items to the left margin (default)",
    )
    fix_p.add_argument(
        "--no-flush-lists",
        dest="flush_lists",
        action="store_false",
        help="Keep standard Word list indentation (0.50/0.25 inch)",
    )
    fix_p.add_argument(
        "--list-indent",
        type=float,
        default=None,
        help="Custom left indent for list items in inches (overrides --flush-lists)",
    )
    fix_p.add_argument(
        "--list-hanging",
        type=float,
        default=None,
        help="Custom hanging indent for list items in inches (overrides --flush-lists)",
    )
    fix_p.add_argument(
        "--flush-paragraphs",
        action="store_true",
        default=True,
        help="Remove paragraph indentation (default)",
    )
    fix_p.add_argument(
        "--no-flush-paragraphs",
        dest="flush_paragraphs",
        action="store_false",
        help="Keep existing paragraph indentation",
    )
    fix_p.add_argument(
        "--para-indent",
        type=float,
        default=None,
        help="Custom left indent for paragraphs in inches (overrides --flush-paragraphs)",
    )
    fix_p.add_argument(
        "--first-line-indent",
        type=float,
        default=None,
        help="Custom first-line indent for paragraphs in inches (overrides --flush-paragraphs)",
    )
    fix_p.add_argument(
        "--detect-headings",
        action="store_true",
        help="Detect faux headings and convert them to real heading styles",
    )
    fix_p.add_argument(
        "--ai",
        action="store_true",
        help="Use Ollama AI to refine heading detection (requires Ollama running)",
    )
    fix_p.add_argument(
        "--ai-provider",
        choices=["ollama", "openrouter"],
        default="ollama",
        help="AI provider to use for heading refinement (default: ollama)",
    )
    fix_p.add_argument(
        "--ai-model",
        type=str,
        default=None,
        help="AI model name (provider-specific default when omitted)",
    )
    fix_p.add_argument(
        "--ai-endpoint",
        type=str,
        default=None,
        help="AI endpoint URL override (provider-specific default when omitted)",
    )
    fix_p.add_argument(
        "--ai-api-key",
        type=str,
        default=None,
        help="API key for cloud providers (e.g., OpenRouter). Defaults to environment variable.",
    )
    fix_p.add_argument(
        "--ai-prompt",
        type=Path,
        default=None,
        help="Path to a text file containing a custom AI system prompt",
    )
    fix_p.add_argument(
        "--ai-keep-alive",
        type=str,
        default=None,
        help="How long Ollama keeps model in RAM after last request (default: 30m)",
    )
    fix_p.add_argument(
        "--heading-threshold",
        type=int,
        default=None,
        help="Minimum heuristic score for heading detection (0-100, default: 50)",
    )

    # ---- template ----
    tmpl_p = sub.add_parser(
        "template",
        help="Create an ACB-compliant Word template",
        description="Create a .dotx template with all ACB styles pre-configured.",
    )
    tmpl_p.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=Path("ACB-Large-Print.dotx"),
        help="Output template path (default: ACB-Large-Print.dotx)",
    )
    tmpl_p.add_argument(
        "--bound",
        "-b",
        action="store_true",
        help="Configure binding margins",
    )
    tmpl_p.add_argument(
        "--no-sample",
        "-n",
        action="store_true",
        help="Create empty template without sample content",
    )
    tmpl_p.add_argument(
        "--title",
        "-t",
        type=str,
        default="",
        help="Set the document title property",
    )
    tmpl_p.add_argument(
        "--install",
        "-i",
        action="store_true",
        help="Also install the template to Word's Templates folder",
    )
    tmpl_p.add_argument(
        "--flush-lists",
        action="store_true",
        default=True,
        help="Flush list items to the left margin (default)",
    )
    tmpl_p.add_argument(
        "--no-flush-lists",
        dest="flush_lists",
        action="store_false",
        help="Keep standard Word list indentation (0.50/0.25 inch)",
    )
    tmpl_p.add_argument(
        "--list-indent",
        type=float,
        default=None,
        help="Custom left indent for list items in inches",
    )
    tmpl_p.add_argument(
        "--list-hanging",
        type=float,
        default=None,
        help="Custom hanging indent for list items in inches",
    )

    # ---- batch ----
    batch_p = sub.add_parser(
        "batch",
        help="Process multiple documents at once",
        description="Run audit or fix on multiple .docx, .xlsx, or .pptx files.",
    )
    batch_p.add_argument(
        "action",
        choices=["audit", "fix"],
        help="Action to perform on each file",
    )
    batch_p.add_argument(
        "files",
        type=Path,
        nargs="+",
        help="Paths to .docx/.xlsx/.pptx files or directories (supports glob patterns)",
    )
    batch_p.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format for audit reports",
    )
    batch_p.add_argument(
        "--output-dir",
        "-d",
        type=Path,
        default=None,
        help="Directory for fixed files (batch fix)",
    )
    batch_p.add_argument(
        "--bound",
        "-b",
        action="store_true",
        help="Add binding margin (batch fix)",
    )
    batch_p.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Search subdirectories for .docx files",
    )
    batch_p.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would change without modifying any files (batch fix)",
    )
    batch_p.add_argument(
        "--flush-lists",
        action="store_true",
        default=True,
        help="Flush list items to the left margin (default, batch fix)",
    )
    batch_p.add_argument(
        "--no-flush-lists",
        dest="flush_lists",
        action="store_false",
        help="Keep standard Word list indentation (batch fix)",
    )
    batch_p.add_argument(
        "--list-indent",
        type=float,
        default=None,
        help="Custom left indent for list items in inches (batch fix)",
    )
    batch_p.add_argument(
        "--list-hanging",
        type=float,
        default=None,
        help="Custom hanging indent for list items in inches (batch fix)",
    )
    batch_p.add_argument(
        "--flush-paragraphs",
        action="store_true",
        default=True,
        help="Remove paragraph indentation (default, batch fix)",
    )
    batch_p.add_argument(
        "--no-flush-paragraphs",
        dest="flush_paragraphs",
        action="store_false",
        help="Keep existing paragraph indentation (batch fix)",
    )
    batch_p.add_argument(
        "--para-indent",
        type=float,
        default=None,
        help="Custom left indent for paragraphs in inches (batch fix)",
    )
    batch_p.add_argument(
        "--first-line-indent",
        type=float,
        default=None,
        help="Custom first-line indent for paragraphs in inches (batch fix)",
    )
    batch_p.add_argument(
        "--detect-headings",
        action="store_true",
        help="Detect faux headings and convert them to real heading styles (batch fix)",
    )
    batch_p.add_argument(
        "--ai",
        action="store_true",
        help="Use Ollama AI to refine heading detection (batch fix)",
    )
    batch_p.add_argument(
        "--ai-provider",
        choices=["ollama", "openrouter"],
        default="ollama",
        help="AI provider to use for heading refinement (default: ollama)",
    )
    batch_p.add_argument(
        "--ai-model",
        type=str,
        default=None,
        help="AI model name (provider-specific default when omitted)",
    )
    batch_p.add_argument(
        "--ai-endpoint",
        type=str,
        default=None,
        help="AI endpoint URL override (provider-specific default when omitted)",
    )
    batch_p.add_argument(
        "--ai-api-key",
        type=str,
        default=None,
        help="API key for cloud providers (e.g., OpenRouter). Defaults to environment variable.",
    )
    batch_p.add_argument(
        "--ai-prompt",
        type=Path,
        default=None,
        help="Path to a text file containing a custom AI system prompt",
    )
    batch_p.add_argument(
        "--ai-keep-alive",
        type=str,
        default=None,
        help="How long Ollama keeps model in RAM after last request (default: 30m)",
    )
    batch_p.add_argument(
        "--heading-threshold",
        type=int,
        default=None,
        help="Minimum heuristic score for heading detection (0-100, default: 50)",
    )
    batch_p.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=1,
        metavar="N",
        help="Number of files to process in parallel (default: 1). Use 0 for auto (one per CPU core).",
    )
    batch_p.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only the aggregate summary, not per-file reports (useful for CI dashboards).",
    )
    batch_p.add_argument(
        "--min-grade",
        type=str,
        default=None,
        choices=["A", "B", "C", "D", "F"],
        metavar="GRADE",
        help="Exit with code 2 if the average score falls below this grade (A/B/C/D/F).",
    )

    # ---- export ----
    export_p = sub.add_parser(
        "export",
        help="Export a Word document to ACB-compliant HTML",
        description=(
            "Convert a .docx file to ACB Large Print HTML. "
            "Two modes: standalone (full HTML + CSS file) or "
            "CMS fragment (embedded CSS, paste into WordPress/Drupal)."
        ),
    )
    export_p.add_argument("file", type=Path, help="Path to .docx file")
    export_p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output HTML file path (default: same name, .html extension)",
    )
    export_p.add_argument(
        "--cms",
        "-c",
        action="store_true",
        help="Generate a CMS fragment with embedded CSS instead of standalone",
    )
    export_p.add_argument(
        "--title",
        "-t",
        type=str,
        default="",
        help="Document title for the HTML output",
    )
    export_p.add_argument(
        "--css",
        type=Path,
        default=None,
        help="Custom CSS file path (standalone mode only)",
    )

    # ---- convert ----
    conv_p = sub.add_parser(
        "convert",
        help="Convert a document to Markdown",
        description=(
            "Convert a document to Markdown using MarkItDown. "
            "Supports .docx, .xlsx, .pptx, .pdf, .html, .csv, .json, "
            ".xml, .epub, and .zip files. Does NOT support audio files."
        ),
    )
    conv_p.add_argument("file", type=Path, help="Path to document file")
    conv_p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output .md file path (default: same name with .md extension)",
    )
    conv_p.add_argument(
        "--wcag-language",
        choices=["off", "input", "output", "both"],
        default="output",
        help="Run deterministic WCAG language checks (default: output).",
    )
    conv_p.add_argument(
        "--wcag-language-enforcement",
        choices=["advisory", "strict"],
        default="advisory",
        help="Advisory logs findings; strict exits with code 2 on WCAG language errors.",
    )

    # ---- convert-html ----
    convhtml_p = sub.add_parser(
        "convert-html",
        help="Convert a document to ACB-compliant HTML via Pandoc",
        description=(
            "Convert a document to standalone, accessible HTML with "
            "embedded ACB Large Print CSS using Pandoc. "
            "Supports .md, .rst, .odt, .rtf, and .docx files."
        ),
    )
    convhtml_p.add_argument("file", type=Path, help="Path to document file")
    convhtml_p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output .html file path (default: same name with .html extension)",
    )
    convhtml_p.add_argument(
        "--title",
        "-t",
        type=str,
        default=None,
        help="Document title for the HTML output (default: filename stem)",
    )
    convhtml_p.add_argument(
        "--css",
        type=Path,
        default=None,
        help="Custom CSS file to embed instead of the built-in ACB CSS",
    )
    convhtml_p.add_argument(
        "--lang",
        type=str,
        default="en",
        help="BCP-47 language tag for the HTML lang attribute (default: en)",
    )
    convhtml_p.add_argument(
        "--toc",
        action="store_true",
        help=(
            "Generate a clickable Table of Contents at the top of the "
            "HTML output (Pandoc --toc). For .docx sources, the "
            "original Word TOC field (which Pandoc otherwise flattens "
            "to unlinked text) is replaced with this linked version."
        ),
    )
    convhtml_p.add_argument(
        "--toc-depth",
        type=int,
        default=3,
        help="Maximum heading level to include in the TOC (default: 3).",
    )
    convhtml_p.add_argument(
        "--toc-title",
        type=str,
        default="Contents",
        help='Heading text shown above the generated TOC (default: "Contents").',
    )
    convhtml_p.add_argument(
        "--wcag-language",
        choices=["off", "input", "output", "both"],
        default="output",
        help="Run deterministic WCAG language checks (default: output).",
    )
    convhtml_p.add_argument(
        "--wcag-language-enforcement",
        choices=["advisory", "strict"],
        default="advisory",
        help="Advisory logs findings; strict exits with code 2 on WCAG language errors.",
    )

    # ---- gui ----
    sub.add_parser(
        "gui",
        help="Launch the graphical interface",
        description="Open the ACB Large Print Tool in GUI mode.",
    )

    # ---- completions ----
    comp_p = sub.add_parser(
        "completions",
        help="Generate shell completion scripts",
        description="Print a completion script for your shell.",
    )
    comp_p.add_argument(
        "shell",
        choices=["bash", "zsh", "powershell", "fish"],
        help="Target shell",
    )

    # ---- detect-headings ----
    dh_p = sub.add_parser(
        "detect-headings",
        help="Detect faux headings in a Word document",
        description=(
            "Scan a .docx file for paragraphs that look like headings "
            "but lack heading styles.  Optionally refine results with "
            "a local Ollama AI model."
        ),
    )
    dh_p.add_argument("file", type=Path, help="Path to .docx file")
    dh_p.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Save report to file instead of printing to console",
    )
    dh_p.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    dh_p.add_argument(
        "--ai",
        action="store_true",
        help="Use Ollama AI to refine heading detection (requires Ollama running)",
    )
    dh_p.add_argument(
        "--ai-provider",
        choices=["ollama", "openrouter"],
        default="ollama",
        help="AI provider to use for heading refinement (default: ollama)",
    )
    dh_p.add_argument(
        "--ai-model",
        type=str,
        default=None,
        help="AI model name (provider-specific default when omitted)",
    )
    dh_p.add_argument(
        "--ai-endpoint",
        type=str,
        default=None,
        help="AI endpoint URL override (provider-specific default when omitted)",
    )
    dh_p.add_argument(
        "--ai-api-key",
        type=str,
        default=None,
        help="API key for cloud providers (e.g., OpenRouter). Defaults to environment variable.",
    )
    dh_p.add_argument(
        "--ai-prompt",
        type=Path,
        default=None,
        help="Path to a text file containing a custom AI system prompt",
    )
    dh_p.add_argument(
        "--ai-keep-alive",
        type=str,
        default=None,
        help="How long Ollama keeps model in RAM after last request (default: 30m)",
    )
    dh_p.add_argument(
        "--threshold",
        type=int,
        default=None,
        help="Minimum heuristic score for heading detection (0-100, default: 50)",
    )
    dh_p.add_argument(
        "--apply",
        action="store_true",
        help="Apply detected heading styles to the document",
    )

    return parser


# ── Supported file extensions ─────────────────────────────────────────
SUPPORTED_EXTENSIONS = {".docx", ".xlsx", ".pptx", ".md", ".pdf", ".epub"}


def _audit_by_extension(file_path: Path):
    """Dispatch to the correct auditor based on file extension."""
    from quill_glow_core import audit_by_extension

    return audit_by_extension(file_path)


def _resolve_list_indent(args: argparse.Namespace) -> tuple[float, float]:
    """Resolve list indent values from CLI args.

    Priority: explicit --list-indent/--list-hanging > --flush-lists > defaults.
    """
    from . import constants as C

    if args.list_indent is not None or args.list_hanging is not None:
        return (
            args.list_indent if args.list_indent is not None else C.LIST_INDENT_IN,
            args.list_hanging if args.list_hanging is not None else C.LIST_HANGING_IN,
        )

    if args.flush_lists:
        return C.LIST_INDENT_FLUSH
    else:
        return C.LIST_INDENT_STANDARD


def _resolve_para_indent(args: argparse.Namespace) -> tuple[float, float]:
    """Resolve paragraph indent values from CLI args.

    Priority: explicit --para-indent/--first-line-indent > --flush-paragraphs > defaults.
    """
    from . import constants as C

    if args.para_indent is not None or args.first_line_indent is not None:
        return (
            args.para_indent if args.para_indent is not None else C.PARA_INDENT_IN,
            (
                args.first_line_indent
                if args.first_line_indent is not None
                else C.FIRST_LINE_INDENT_IN
            ),
        )

    if args.flush_paragraphs:
        return (C.PARA_INDENT_FLUSH, C.PARA_INDENT_FLUSH)
    else:
        return (C.PARA_INDENT_IN, C.FIRST_LINE_INDENT_IN)


def _resolve_ai_provider(args: argparse.Namespace):
    """Build an AI provider from CLI args, or return None if --ai not set."""
    if not getattr(args, "ai", False):
        return None

    from .ai_provider import get_provider

    system_prompt = None
    prompt_path = getattr(args, "ai_prompt", None)
    if prompt_path is not None:
        p = Path(prompt_path)
        if not p.exists():
            print(f"Error: AI prompt file not found: {p}", file=sys.stderr)
            sys.exit(1)
        system_prompt = p.read_text(encoding="utf-8")

    return get_provider(
        provider=getattr(args, "ai_provider", "ollama"),
        model=getattr(args, "ai_model", None),
        endpoint=getattr(args, "ai_endpoint", None),
        system_prompt=system_prompt,
        keep_alive=getattr(args, "ai_keep_alive", None),
        api_key=getattr(args, "ai_api_key", None),
    )


def _fix_by_extension(
    file_path: Path,
    output_path: Path | None = None,
    *,
    bound: bool = False,
    list_indent_in: float = 0.0,
    list_hanging_in: float = 0.0,
    para_indent_in: float = 0.0,
    first_line_indent_in: float = 0.0,
):
    """Dispatch to the correct fixer based on file extension.

    Returns (output_path, total_fixes, fix_records, post_audit, warnings).
    """
    from quill_glow_core import fix_by_extension

    return fix_by_extension(
        file_path,
        output_path=output_path,
        bound=bound,
        list_indent_in=list_indent_in,
        list_hanging_in=list_hanging_in,
        para_indent_in=para_indent_in,
        first_line_indent_in=first_line_indent_in,
    )


def _cmd_audit(args: argparse.Namespace) -> int:
    """Execute the audit command."""
    from .reporter import generate_json_report, generate_text_report

    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    ext = args.file.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(
            "Error: Unsupported file type "
            f"'{ext}'. Use .docx, .xlsx, .pptx, .md, .pdf, or .epub.",
            file=sys.stderr,
        )
        return 1

    log.debug("Auditing: %s", args.file)
    result = _audit_by_extension(args.file)
    log.debug(
        "Score: %d/100 (%s), %d findings",
        result.score,
        result.grade,
        len(result.findings),
    )

    if args.format == "json":
        report = generate_json_report(result)
    else:
        report = generate_text_report(result)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        log.info("Report saved to: %s", args.output)
    else:
        print(report)

    return 0 if result.passed else 2


def _cmd_fix(args: argparse.Namespace) -> int:
    """Execute the fix command."""
    from .reporter import generate_fix_summary

    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    ext = args.file.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(
            "Error: Unsupported file type "
            f"'{ext}'. Use .docx, .xlsx, .pptx, .md, .pdf, or .epub.",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        # Dry-run: audit only, report what would be fixed
        log.info("Dry run -- no files will be modified")
        result = _audit_by_extension(args.file)
        fixable = [f for f in result.findings if f.auto_fixable]
        manual = [f for f in result.findings if not f.auto_fixable]
        print(f"File: {args.file}")
        print(f"Score: {result.score}/100 (Grade {result.grade})")
        print(f"Auto-fixable issues: {len(fixable)}")
        print(f"Manual-review issues: {len(manual)}")
        if fixable:
            print("\nWould fix:")
            for i, f in enumerate(fixable, 1):
                print(f"  {i}. [{f.severity.value}] {f.rule_id}: {f.message}")
        if manual:
            print("\nRequires manual review:")
            for i, f in enumerate(manual, 1):
                print(f"  {i}. [{f.severity.value}] {f.rule_id}: {f.message}")
        return 0 if result.passed else 2

    list_indent_in, list_hanging_in = _resolve_list_indent(args)
    para_indent_in, first_line_indent_in = _resolve_para_indent(args)
    output_path, total_fixes, _records, post_audit, warnings = _fix_by_extension(
        args.file,
        output_path=args.output,
        bound=getattr(args, "bound", False),
        list_indent_in=list_indent_in,
        list_hanging_in=list_hanging_in,
        para_indent_in=para_indent_in,
        first_line_indent_in=first_line_indent_in,
    )

    report = generate_fix_summary(str(output_path), total_fixes, post_audit)
    print(report)
    for w in warnings:
        print(f"  WARNING: {w}")

    return 0 if post_audit.passed else 2


def _cmd_template(args: argparse.Namespace) -> int:
    """Execute the template command."""
    from .template import create_template, install_template

    list_indent_in, list_hanging_in = _resolve_list_indent(args)
    output = create_template(
        args.output,
        bound=args.bound,
        include_sample=not args.no_sample,
        title=args.title,
        list_indent_in=list_indent_in,
        list_hanging_in=list_hanging_in,
    )
    log.info("Template created: %s", output)

    if args.install:
        dest = install_template(output)
        log.info("Template installed to: %s", dest)
        log.info("It will appear in Word under File, New, Personal templates.")

    return 0


_GRADE_MIN_SCORE = {"A": 90, "B": 80, "C": 70, "D": 60, "F": 0}


def _expand_batch_files(args: argparse.Namespace) -> list[Path]:
    """Expand paths/globs/directories into a sorted, deduplicated file list."""
    files: list[Path] = []
    for pattern in args.files:
        p = Path(str(pattern))
        if p.is_dir():
            glob_method = p.rglob if args.recursive else p.glob
            for ext in SUPPORTED_EXTENSIONS:
                files.extend(glob_method(f"*{ext}"))
        elif "*" in str(pattern) or "?" in str(pattern):
            if args.recursive:
                files.extend(pattern.parent.rglob(pattern.name))
            else:
                files.extend(pattern.parent.glob(pattern.name))
        else:
            files.append(p)
    # Sort and deduplicate
    seen: set[Path] = set()
    result: list[Path] = []
    for f in sorted(files):
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result


def _cmd_batch(args: argparse.Namespace) -> int:
    """Execute the batch command with optional parallel execution."""
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from .reporter import (
        generate_fix_summary,
        generate_json_report,
        generate_text_report,
    )

    files = _expand_batch_files(args)
    if not files:
        print("Error: No matching document files found.", file=sys.stderr)
        return 1

    # Resolve indent values once
    list_indent_in, list_hanging_in = _resolve_list_indent(args)
    para_indent_in, first_line_indent_in = _resolve_para_indent(args)

    # Determine worker count
    jobs = getattr(args, "jobs", 1)
    if jobs == 0:
        jobs = os.cpu_count() or 1
    jobs = max(1, jobs)
    summary_only = getattr(args, "summary_only", False)

    total_files = len(files)
    # Ordered results -- initialise slots so parallel results land in file order
    ordered_reports: list[str | None] = [None] * total_files
    audit_results: list = [None] * total_files  # AuditResult or None
    exit_code = 0

    def _process_audit(idx: int, file_path: Path) -> tuple[int, str, object | None]:
        """Worker: audit one file. Returns (idx, report_text, result)."""
        log.info("[%d/%d] Auditing: %s", idx + 1, total_files, file_path.name)
        try:
            result = _audit_by_extension(file_path)
            if args.format == "json":
                report = generate_json_report(result)
            else:
                report = generate_text_report(result)
            return idx, report, result
        except Exception as exc:
            msg = f"ERROR auditing {file_path.name}: {exc}"
            log.warning(msg)
            return idx, msg, None

    def _process_fix(idx: int, file_path: Path) -> tuple[int, str, object | None]:
        """Worker: fix one file. Returns (idx, report_text, post_audit_result)."""
        log.info("[%d/%d] Fixing: %s", idx + 1, total_files, file_path.name)
        try:
            if args.dry_run:
                result = _audit_by_extension(file_path)
                fixable = [f for f in result.findings if f.auto_fixable]
                manual = [f for f in result.findings if not f.auto_fixable]
                txt = (
                    f"File: {file_path}\n"
                    f"  Auto-fixable: {len(fixable)}, Manual: {len(manual)}"
                )
                return idx, txt, result

            out = None
            if args.output_dir:
                args.output_dir.mkdir(parents=True, exist_ok=True)
                out = args.output_dir / file_path.name

            output_path, total_fixes, _records, post_audit, warnings = _fix_by_extension(
                file_path,
                output_path=out,
                bound=getattr(args, "bound", False),
                list_indent_in=list_indent_in,
                list_hanging_in=list_hanging_in,
                para_indent_in=para_indent_in,
                first_line_indent_in=first_line_indent_in,
            )
            lines = [generate_fix_summary(str(output_path), total_fixes, post_audit)]
            for w in warnings:
                lines.append(f"  WARNING: {w}")
            return idx, "\n".join(lines), post_audit
        except Exception as exc:
            msg = f"ERROR fixing {file_path.name}: {exc}"
            log.warning(msg)
            return idx, msg, None

    valid_files = [
        fp for fp in files
        if fp.exists() and fp.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    skipped = [fp for fp in files if fp not in valid_files]
    for fp in skipped:
        if not fp.exists():
            log.warning("Skipping (not found): %s", fp)
        else:
            log.warning("Skipping (unsupported format): %s", fp)

    if not valid_files:
        print("Error: No supported files to process.", file=sys.stderr)
        return 1

    worker = _process_audit if args.action == "audit" else _process_fix

    if jobs == 1:
        # Serial path -- simpler, preserves log ordering
        for idx, fp in enumerate(valid_files):
            ret_idx, report, result = worker(idx, fp)
            ordered_reports[ret_idx] = report
            audit_results[ret_idx] = result
    else:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {
                pool.submit(worker, idx, fp): idx
                for idx, fp in enumerate(valid_files)
            }
            for future in as_completed(futures):
                ret_idx, report, result = future.result()
                ordered_reports[ret_idx] = report
                audit_results[ret_idx] = result

    # Print per-file reports in original file order (unless summary-only)
    if not summary_only:
        for report in ordered_reports:
            if report is not None:
                print(report)
                print()

    # Aggregate summary
    all_results = [r for r in audit_results if r is not None]
    total_processed = len(all_results)
    total_issues = sum(len(getattr(r, "findings", [])) for r in all_results)
    passing = sum(1 for r in all_results if getattr(r, "passed", False))
    scores = [getattr(r, "score", None) for r in all_results if getattr(r, "score", None) is not None]
    avg_score = round(sum(scores) / len(scores)) if scores else None

    # Build severity counts
    sev_counts: dict[str, int] = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for r in all_results:
        for f in getattr(r, "findings", []):
            sev = getattr(getattr(f, "severity", None), "value", str(getattr(f, "severity", "")))
            if sev in sev_counts:
                sev_counts[sev] += 1

    sep = "-" * 60
    print(sep)
    print(f"Batch {args.action} complete")
    print(f"  Files processed : {total_processed}")
    if args.action == "audit":
        print(f"  Passing files   : {passing}/{total_processed}")
        if avg_score is not None:
            print(f"  Average score   : {avg_score}/100")
        if total_issues:
            print(f"  Total findings  : {total_issues}")
            for sev, count in sev_counts.items():
                if count:
                    print(f"    {sev:<10}: {count}")

    # JSON aggregate output when --format json
    if args.format == "json" and args.action == "audit":
        import json
        summary = {
            "action": args.action,
            "files_processed": total_processed,
            "passing": passing,
            "failing": total_processed - passing,
            "avg_score": avg_score,
            "total_findings": total_issues,
            "by_severity": sev_counts,
        }
        print(json.dumps({"batch_summary": summary}, indent=2))

    # Determine exit code
    for r in all_results:
        if not getattr(r, "passed", True):
            exit_code = 2

    # --min-grade check (audit only)
    min_grade = getattr(args, "min_grade", None)
    if min_grade and avg_score is not None and args.action == "audit":
        threshold = _GRADE_MIN_SCORE.get(min_grade, 0)
        if avg_score < threshold:
            log.warning(
                "Average score %d is below minimum grade %s (%d). Exiting with code 2.",
                avg_score, min_grade, threshold,
            )
            exit_code = 2

    return exit_code


def _cmd_export(args: argparse.Namespace) -> int:
    """Execute the export command."""
    from .exporter import export_cms_fragment, export_standalone_html

    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    # Default output path
    if args.output:
        out = args.output
    elif args.cms:
        out = args.file.with_suffix(".html").with_stem(args.file.stem + "-cms")
    else:
        out = args.file.with_suffix(".html")

    title = args.title or args.file.stem.replace("-", " ").replace("_", " ")

    if args.cms:
        path, warnings = export_cms_fragment(args.file, out, title=title)
        log.info("CMS fragment saved: %s", path)
    else:
        html_path, css_path, warnings = export_standalone_html(
            args.file,
            out,
            title=title,
            css_path=args.css,
        )
        log.info("HTML saved: %s", html_path)
        log.info("CSS saved:  %s", css_path)

    if warnings:
        log.warning("Conversion warnings (%d):", len(warnings))
        for w in warnings:
            log.warning("  - %s", w)

    return 0


def _wcag_stage_enabled(selected: str, target: str) -> bool:
    return selected in {target, "both"}


def _analyze_wcag_language_for_path(path: Path, *, stage: str):
    import tempfile
    from .converter import convert_to_markdown
    from .wcag_language import analyze_text_for_wcag_language

    ext = path.suffix.lower()
    if ext in {".md", ".rst", ".txt", ".html", ".htm", ".csv", ".json", ".xml"}:
        text = path.read_text(encoding="utf-8", errors="ignore")
    else:
        with tempfile.TemporaryDirectory(prefix="glow-wcag-lang-") as td:
            temp_md = Path(td) / f"{path.stem}.md"
            _md_path, text = convert_to_markdown(path, output_path=temp_md)
    return analyze_text_for_wcag_language(text, stage=stage)


def _print_wcag_language_report(report) -> None:
    log.info(
        "WCAG language (%s): %d finding(s), %d error(s), %d warning(s)",
        report.stage,
        report.total,
        report.error_count,
        report.warning_count,
    )
    for finding in report.findings[:8]:
        log.info(
            "  - %s (WCAG %s): %s",
            finding.rule_id,
            finding.wcag,
            finding.message,
        )
    if report.total > 8:
        log.info("  - ...and %d more finding(s).", report.total - 8)


def _cmd_convert(args: argparse.Namespace) -> int:
    """Execute the convert command."""
    from .converter import CONVERTIBLE_EXTENSIONS
    from quill_glow_core import convert_to_markdown
    from .wcag_language import analyze_text_for_wcag_language

    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    ext = args.file.suffix.lower()
    if ext not in CONVERTIBLE_EXTENSIONS:
        print(
            f"Error: Cannot convert '{ext}' files. "
            f"Supported: {', '.join(sorted(CONVERTIBLE_EXTENSIONS))}",
            file=sys.stderr,
        )
        return 1

    language_stage = getattr(args, "wcag_language", "output")
    language_enforcement = getattr(args, "wcag_language_enforcement", "advisory")
    reports = []
    if _wcag_stage_enabled(language_stage, "input"):
        input_report = _analyze_wcag_language_for_path(args.file, stage="input")
        reports.append(input_report)
        if language_enforcement == "strict" and input_report.error_count > 0:
            _print_wcag_language_report(input_report)
            return 2

    try:
        output_path, text = convert_to_markdown(args.file, output_path=args.output)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if _wcag_stage_enabled(language_stage, "output"):
        output_report = analyze_text_for_wcag_language(text, stage="output")
        reports.append(output_report)
        if language_enforcement == "strict" and output_report.error_count > 0:
            _print_wcag_language_report(output_report)
            return 2

    for report in reports:
        _print_wcag_language_report(report)

    log.info("Markdown saved to: %s (%d characters)", output_path, len(text))
    return 0


def _cmd_convert_html(args: argparse.Namespace) -> int:
    """Execute the convert-html command (Pandoc to ACB HTML)."""
    from .pandoc_converter import PANDOC_INPUT_EXTENSIONS, convert_to_html
    from .wcag_language import analyze_text_for_wcag_language

    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    ext = args.file.suffix.lower()
    if ext not in PANDOC_INPUT_EXTENSIONS:
        print(
            f"Error: Cannot convert '{ext}' files to HTML. "
            f"Supported: {', '.join(sorted(PANDOC_INPUT_EXTENSIONS))}",
            file=sys.stderr,
        )
        return 1

    language_stage = getattr(args, "wcag_language", "output")
    language_enforcement = getattr(args, "wcag_language_enforcement", "advisory")
    reports = []
    if _wcag_stage_enabled(language_stage, "input"):
        input_report = _analyze_wcag_language_for_path(args.file, stage="input")
        reports.append(input_report)
        if language_enforcement == "strict" and input_report.error_count > 0:
            _print_wcag_language_report(input_report)
            return 2

    try:
        output_path, html_text = convert_to_html(
            args.file,
            output_path=args.output,
            title=args.title,
            css_path=args.css,
            lang=args.lang,
            generate_toc=getattr(args, "toc", False),
            toc_depth=getattr(args, "toc_depth", 3),
            toc_title=getattr(args, "toc_title", "Contents"),
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if _wcag_stage_enabled(language_stage, "output"):
        output_report = analyze_text_for_wcag_language(html_text, stage="output")
        reports.append(output_report)
        if language_enforcement == "strict" and output_report.error_count > 0:
            _print_wcag_language_report(output_report)
            return 2

    for report in reports:
        _print_wcag_language_report(report)

    log.info("HTML saved to: %s (%d characters)", output_path, len(html_text))
    return 0


def _cmd_gui(_args: argparse.Namespace) -> int:
    """Launch the graphical interface."""
    try:
        from .gui import launch_gui
    except ImportError:
        print(
            "Error: wxPython is not installed. The GUI requires wxPython.\n"
            "Install it with: pip install wxPython>=4.2.0\n"
            "Use CLI commands instead: acb-large-print --help",
            file=sys.stderr,
        )
        return 1
    launch_gui()
    return 0


def _cmd_detect_headings(args: argparse.Namespace) -> int:
    """Execute the detect-headings command."""
    import json as _json

    from docx import Document

    from . import constants as C
    from .heading_detector import detect_headings

    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1

    ext = args.file.suffix.lower()
    if ext != ".docx":
        print(
            f"Error: Heading detection only supports .docx files, got '{ext}'.",
            file=sys.stderr,
        )
        return 1

    threshold = (
        args.threshold if args.threshold is not None else C.HEADING_CONFIDENCE_THRESHOLD
    )
    ai_provider = _resolve_ai_provider(args)
    doc = Document(str(args.file))

    system_prompt = None
    if args.ai_prompt and args.ai_prompt.exists():
        system_prompt = args.ai_prompt.read_text(encoding="utf-8")

    candidates = detect_headings(
        doc,
        ai_provider=ai_provider,
        threshold=threshold,
        system_prompt=system_prompt,
    )

    if args.json:
        data = [
            {
                "paragraph_index": c.paragraph_index,
                "text": c.text,
                "score": c.score,
                "confidence": c.confidence,
                "suggested_level": c.suggested_level,
                "signals": [{"name": n, "points": p} for n, p in c.signals],
                "ai_reasoning": c.ai_reasoning,
            }
            for c in candidates
        ]
        output = _json.dumps(data, indent=2, ensure_ascii=False)
    else:
        lines: list[str] = []
        lines.append(f"Detected {len(candidates)} faux heading(s) in {args.file.name}")
        lines.append("")
        for i, c in enumerate(candidates, 1):
            lines.append(
                f"  {i}. [H{c.suggested_level}] ({c.confidence}, score {c.score}) "
                f'"{c.text[:80]}"'
            )
            if c.signals:
                sigs = ", ".join(f"{n} (+{p})" for n, p in c.signals)
                lines.append(f"     Signals: {sigs}")
            if c.ai_reasoning:
                lines.append(f"     AI: {c.ai_reasoning}")
        output = "\n".join(lines)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        log.info("Report saved to: %s", args.output)
    else:
        print(output)

    if args.apply and candidates:
        for c in candidates:
            para = doc.paragraphs[c.paragraph_index]
            para.style = doc.styles[f"Heading {c.suggested_level}"]
        out_path = args.output or args.file
        doc.save(str(out_path))
        log.info("Applied %d heading style(s) to %s", len(candidates), out_path)

    return 0


def _cmd_completions(args: argparse.Namespace) -> int:
    """Generate shell completion script."""
    prog = "acb-large-print"
    commands = "audit fix template batch export convert convert-html detect-headings gui completions"
    prog_under = prog.replace("-", "_")

    if args.shell == "bash":
        script = (
            f"# bash completion for {prog}\n"
            f"_{prog_under}_completions() {{\n"
            '    local cur="${COMP_WORDS[COMP_CWORD]}"\n'
            '    local prev="${COMP_WORDS[COMP_CWORD-1]}"\n'
            '    case "$prev" in\n'
            f'        {prog}) COMPREPLY=($(compgen -W "{commands} --help --version --quiet --verbose" -- "$cur")) ;;\n'
            '        audit)  COMPREPLY=($(compgen -W "--format --output --help" -- "$cur") $(compgen -f -X \'!*.docx\' -- "$cur")) ;;\n'
            '        fix)    COMPREPLY=($(compgen -W "--output --bound --dry-run --help" -- "$cur") $(compgen -f -X \'!*.docx\' -- "$cur")) ;;\n'
            '        batch)  COMPREPLY=($(compgen -W "audit fix" -- "$cur")) ;;\n'
            '        export) COMPREPLY=($(compgen -W "--output --cms --title --css --help" -- "$cur") $(compgen -f -X \'!*.docx\' -- "$cur")) ;;\n'
            '        --format|-f) COMPREPLY=($(compgen -W "text json" -- "$cur")) ;;\n'
            '        *) COMPREPLY=($(compgen -f -- "$cur")) ;;\n'
            "    esac\n"
            "}}\n"
            f"complete -o default -F _{prog_under}_completions {prog}"
        )
        print(script)

    elif args.shell == "zsh":
        script = (
            f"#compdef {prog}\n"
            "_arguments \\\n"
            f"    '1:command:({commands})' \\\n"
            "    '--help[Show help]' \\\n"
            "    '--version[Show version]' \\\n"
            "    '--quiet[Suppress info messages]' \\\n"
            "    '--verbose[Show debug output]' \\\n"
            "    '*:file:_files -g \"*.docx\"'"
        )
        print(script)

    elif args.shell == "fish":
        lines = []
        for cmd in commands.split():
            lines.append(f"complete -c {prog} -n '__fish_use_subcommand' -a {cmd}")
        lines.append(f"complete -c {prog} -s h -l help -d 'Show help'")
        lines.append(f"complete -c {prog} -s V -l version -d 'Show version'")
        lines.append(f"complete -c {prog} -s q -l quiet -d 'Suppress info'")
        lines.append(f"complete -c {prog} -s v -l verbose -d 'Debug output'")
        print("\n".join(lines))

    elif args.shell == "powershell":
        cmds_quoted = ", ".join(f"'{c}'" for c in commands.split())
        script = (
            f"Register-ArgumentCompleter -CommandName {prog} -ScriptBlock {{\n"
            "    param($wordToComplete, $commandAst, $cursorPosition)\n"
            f"    $commands = @({cmds_quoted})\n"
            "    $flags = @('--help', '--version', '--quiet', '--verbose')\n"
            '    ($commands + $flags) | Where-Object { $_ -like "$wordToComplete*" } |\n'
            "        ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }\n"
            "}"
        )
        print(script)

    return 0


def main(argv: list[str] | None = None, *, force_cli: bool = False) -> int:
    """CLI entry point. Returns exit code.

    Args:
        argv: Command line arguments (None = sys.argv).
        force_cli: If True, never launch the GUI (print help instead).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args)

    if args.command is None:
        if force_cli:
            parser.print_help()
            return 0
        # No command given -- launch GUI by default if wxPython available
        try:
            from .gui import launch_gui
        except ImportError:
            parser.print_help()
            print(
                "\nNote: GUI unavailable (wxPython not installed). "
                "Use a subcommand above.",
                file=sys.stderr,
            )
            return 1
        launch_gui()
        return 0

    dispatch = {
        "audit": _cmd_audit,
        "fix": _cmd_fix,
        "template": _cmd_template,
        "batch": _cmd_batch,
        "export": _cmd_export,
        "convert": _cmd_convert,
        "convert-html": _cmd_convert_html,
        "detect-headings": _cmd_detect_headings,
        "gui": _cmd_gui,
        "completions": _cmd_completions,
    }

    handler = dispatch.get(args.command)
    if handler:
        return handler(args)

    parser.print_help()
    return 1
