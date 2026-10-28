"""Convert documents using Pandoc (and optionally WeasyPrint for PDF).

Wraps the Pandoc CLI to convert text-oriented document formats into:
- Standalone, accessible HTML with embedded ACB Large Print CSS
- Word (.docx) documents with optional ACB reference styling
- EPUB 3 e-books with embedded ACB accessibility CSS
- Tagged PDF/UA-1 documents rendered from ACB HTML via WeasyPrint

Supported input: .md, .rst, .txt, .odt, .rtf, .docx, .epub.

Pandoc is an external dependency -- not a Python package.  The module
falls back gracefully when it is not installed.  WeasyPrint is an
optional Python dependency for PDF output; the module falls back
gracefully when it is not installed.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("acb_large_print")

# Input formats Pandoc handles well for ACB HTML output.
# Deliberately scoped to document types relevant to accessibility conversion
# (not the full 40+ formats Pandoc supports).
PANDOC_INPUT_EXTENSIONS: set[str] = {
    ".md",  # Markdown (GFM)
    ".rst",  # reStructuredText
    ".txt",  # Plain text
    ".odt",  # OpenDocument Text
    ".fodt",  # Flat OpenDocument Text
    ".rtf",  # Rich Text Format
    ".docx",  # Word (Pandoc's own reader)
    ".epub",  # ePub e-books
}

# Pandoc input format flag for each extension
_INPUT_FORMAT: dict[str, str] = {
    ".md": "gfm",
    ".rst": "rst",
    ".txt": "markdown",
    ".odt": "odt",
    ".fodt": "odt",
    ".rtf": "rtf",
    ".docx": "docx",
    ".epub": "epub",
}

# ---------------------------------------------------------------------------
# Minimal ACB CSS for embedding in Pandoc output
# (mirrors styles/acb-large-print.css -- keep in sync)
# ---------------------------------------------------------------------------
_ACB_CSS = """\
html { font-size: 100%; }
body {
  font-family: Arial, sans-serif;
  font-size: 1.5rem;
  font-weight: 400;
  color: #1a1a1a;
  background-color: #ffffff;
  text-align: left;
  line-height: 1.5;
  letter-spacing: 0.12em;
  word-spacing: 0.16em;
  margin: 0 auto;
  padding: 1rem 1rem;
  max-width: 70ch;
  hyphens: none;
  -webkit-hyphens: none;
  columns: 1;
}
h1, h2 {
  font-family: Arial, sans-serif;
  font-size: 1.833rem;
  font-weight: 700;
  line-height: 1.5;
  text-align: left;
  text-transform: none;
  margin-top: 1.5em;
  margin-bottom: 1em;
}
h3, h4, h5, h6 {
  font-family: Arial, sans-serif;
  font-size: 1.667rem;
  font-weight: 700;
  line-height: 1.5;
  text-align: left;
  text-transform: none;
  margin-top: 1.5em;
  margin-bottom: 1em;
}
p {
  margin-top: 0;
  margin-bottom: 2em;
}
em, .acb-emphasis {
  font-style: normal;
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
}
u {
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
}
a {
  color: #0055cc;
  text-decoration: underline;
  text-decoration-thickness: 1px;
}
a:hover, a:focus {
  text-decoration-thickness: 2px;
  outline: 2px solid currentColor;
  outline-offset: 2px;
}
ul { list-style-type: disc; padding-left: 1.5em; margin-top: 0; margin-bottom: 2em; }
ul li { margin-bottom: 0; padding-left: 0.5em; }
ul li::marker { color: #1a1a1a; font-size: 1.2em; }
ol { list-style-type: decimal; padding-left: 1.5em; margin-top: 0; margin-bottom: 2em; }
ol li { margin-bottom: 0; padding-left: 0.5em; }
table { border-collapse: collapse; width: 100%; font-size: inherit; }
th, td { text-align: left; padding: 0.5em 0.75em; border: 1px solid #666; }
th { font-weight: 700; }
caption { font-size: 1.5rem; font-weight: 700; text-align: left; margin-bottom: 0.5em; }
figure { margin: 1.5em 0; }
figcaption { font-size: 1.5rem; margin-top: 0.5em; }
img { max-width: 100%; height: auto; }
@media print {
  body { line-height: 1.15; color: #000; background-color: #faf8f0; max-width: none; padding: 0; }
  @page { margin: 1in; }
  @page :left { margin-left: 1.5in; }
  a { color: #000; text-decoration: underline; }
}
"""


def pandoc_available() -> bool:
    """Return True if the Pandoc CLI is installed and reachable."""
    return shutil.which("pandoc") is not None


def pandoc_version() -> str | None:
    """Return the Pandoc version string, or None if not installed."""
    exe = shutil.which("pandoc")
    if not exe:
        return None
    try:
        result = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        first_line = result.stdout.strip().splitlines()[0]
        return first_line  # e.g. "pandoc 3.1.13"
    except (subprocess.SubprocessError, IndexError):
        return None


# Class names Pandoc assigns to paragraphs that came from the docx
# table-of-contents field. Pandoc flattens the field result, so each TOC
# entry becomes a paragraph styled "TOC 1".."TOC 9" with class "TOC1"..
# "TOC9". We also strip the "TOCHeading" paragraph ("Contents" / "Table
# of Contents"). When we emit a fresh Pandoc-generated TOC, these stale
# unlinked paragraphs would otherwise appear as a second, broken TOC.
_DOCX_TOC_PARAGRAPH_RE = re.compile(
    r'<p\s+class="(?:TOCHeading|TOC\d+)"[^>]*>.*?</p>\s*',
    flags=re.IGNORECASE | re.DOTALL,
)


def _strip_docx_source_toc(html_text: str) -> str:
    """Remove paragraphs Pandoc emits for the original docx TOC field.

    Pandoc's docx reader does not preserve the field's hyperlinks; it
    emits the visible TOC text as paragraphs with classes ``TOC1``..
    ``TOC9`` (and an optional ``TOCHeading`` line). When we generate a
    fresh linked TOC via ``--toc``, those stale paragraphs become a
    duplicate, unlinked TOC. Strip them.
    """
    return _DOCX_TOC_PARAGRAPH_RE.sub("", html_text)


def convert_to_html(
    src_path: Path,
    output_path: Path | None = None,
    *,
    title: str | None = None,
    css_path: Path | None = None,
    lang: str = "en",
    generate_toc: bool = False,
    toc_depth: int = 3,
    toc_title: str = "Contents",
) -> tuple[Path, str]:
    """Convert a document to ACB-compliant standalone HTML via Pandoc.

    Args:
        src_path: Path to input file (.md, .rst, .odt, .rtf, .docx).
        output_path: Optional path for the .html file.  Defaults to same
            directory / stem as *src_path* with ``.html`` extension.
        title: Document title for the HTML ``<title>`` element.
            Defaults to the input filename stem.
        css_path: Optional path to an external CSS file.  If provided,
            its contents are embedded in the HTML ``<head>``.  If omitted,
            the built-in ACB Large Print CSS is used.
        lang: BCP-47 language tag for the ``<html lang>`` attribute.
        generate_toc: When True, Pandoc emits a fresh ``<nav id="TOC">``
            with clickable anchor links to every heading in the document.
            For ``.docx`` sources, the original Word table-of-contents
            field (which Pandoc otherwise flattens to plain text) is
            stripped so the new linked TOC does not appear twice.
        toc_depth: Maximum heading level to include in the generated TOC.
        toc_title: Heading text shown above the generated TOC.

    Returns:
        (output_path, html_text)

    Raises:
        FileNotFoundError: If *src_path* does not exist.
        ValueError: If the extension is not in PANDOC_INPUT_EXTENSIONS.
        RuntimeError: If Pandoc is not installed or conversion fails.
    """
    src_path = Path(src_path)
    if not src_path.exists():
        raise FileNotFoundError(f"File not found: {src_path}")

    ext = src_path.suffix.lower()
    if ext not in PANDOC_INPUT_EXTENSIONS:
        raise ValueError(
            f"Cannot convert '{ext}' files to HTML. "
            f"Supported: {', '.join(sorted(PANDOC_INPUT_EXTENSIONS))}"
        )

    exe = shutil.which("pandoc")
    if not exe:
        raise RuntimeError(
            "Pandoc is not installed. "
            "Install it from https://pandoc.org/installing.html"
        )

    if output_path is None:
        output_path = src_path.with_suffix(".html")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if title is None:
        title = src_path.stem.replace("-", " ").replace("_", " ")

    # Resolve CSS: use provided file, skip CSS, or use built-in ACB CSS
    if css_path is not None and css_path.name == "__no_acb_css__":
        css_text = ""  # User opted out of ACB formatting
    elif css_path and css_path.exists():
        css_text = css_path.read_text(encoding="utf-8")
    else:
        css_text = _ACB_CSS

    # Write a temporary header-include file with the CSS
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        header_file = tmp_dir / "acb-header.html"
        header_file.write_text(
            f"<style>\n{css_text}\n</style>\n",
            encoding="utf-8",
        )

        input_fmt = _INPUT_FORMAT.get(ext, "markdown")

        cmd = [
            exe,
            "--standalone",
            "--from",
            input_fmt,
            "--to",
            "html5",
            "--include-in-header",
            str(header_file),
            "--metadata",
            f"title={title}",
            "--metadata",
            f"lang={lang}",
        ]

        if generate_toc:
            # Pandoc generates a fresh <nav id="TOC"> with anchor links
            # to every heading. Pandoc auto-assigns slug IDs to headings
            # in --standalone mode, so the anchors resolve correctly.
            cmd.extend(
                [
                    "--toc",
                    f"--toc-depth={int(toc_depth)}",
                    "--metadata",
                    f"toc-title={toc_title}",
                ]
            )

        cmd.extend(
            [
                "--output",
                str(output_path),
                str(src_path),
            ]
        )

        log.info("Running: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"Pandoc conversion failed (exit code {result.returncode}): "
                f"{stderr}"
            )

        html_text = output_path.read_text(encoding="utf-8")

        if generate_toc and ext == ".docx":
            html_text = _strip_docx_source_toc(html_text)
            output_path.write_text(html_text, encoding="utf-8")

        log.info(
            "Pandoc conversion complete: %s -> %s (%d characters)",
            src_path.name,
            output_path.name,
            len(html_text),
        )
        return output_path, html_text

    finally:
        # Clean up temp header file
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# ACB CSS for PDF rendering (print-optimized variant)
# Uses print line-height (1.15) and @page rules for margins. Font stack
# puts Arial first, with Liberation Sans as Linux fallback.
# ---------------------------------------------------------------------------
_ACB_PDF_CSS = """\
html { font-size: 100%; }
body {
  font-family: Arial, "Liberation Sans", sans-serif;
  font-size: 18pt;
  font-weight: 400;
  color: #000;
  background-color: #fff;
  text-align: left;
  line-height: 1.15;
  letter-spacing: 0.12em;
  word-spacing: 0.16em;
  margin: 0;
  padding: 0;
  hyphens: none;
  columns: 1;
}
@page {
  size: letter;
  margin: 1in;
}
h1, h2 {
  font-family: Arial, "Liberation Sans", sans-serif;
  font-size: 22pt;
  font-weight: 700;
  line-height: 1.15;
  text-align: left;
  text-transform: none;
  margin-top: 1.5em;
  margin-bottom: 1em;
}
h3, h4, h5, h6 {
  font-family: Arial, "Liberation Sans", sans-serif;
  font-size: 20pt;
  font-weight: 700;
  line-height: 1.15;
  text-align: left;
  text-transform: none;
  margin-top: 1.5em;
  margin-bottom: 1em;
}
p {
  margin-top: 0;
  margin-bottom: 1em;
}
em, .acb-emphasis {
  font-style: normal;
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
}
u {
  text-decoration: underline;
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
}
a {
  color: #000;
  text-decoration: underline;
}
ul { list-style-type: disc; padding-left: 1.5em; margin-top: 0; margin-bottom: 1em; }
ul li { margin-bottom: 0; padding-left: 0.5em; }
ol { list-style-type: decimal; padding-left: 1.5em; margin-top: 0; margin-bottom: 1em; }
ol li { margin-bottom: 0; padding-left: 0.5em; }
table { border-collapse: collapse; width: 100%; font-size: inherit; }
th, td { text-align: left; padding: 0.5em 0.75em; border: 1px solid #666; }
th { font-weight: 700; }
caption { font-size: 18pt; font-weight: 700; text-align: left; margin-bottom: 0.5em; }
figure { margin: 1.5em 0; }
figcaption { font-size: 18pt; margin-top: 0.5em; }
img { max-width: 100%; height: auto; }
"""

# Binding-margin variant adds 0.5in extra on the left for bound documents
_ACB_PDF_CSS_BINDING = _ACB_PDF_CSS.replace(
    "margin: 1in;",
    "margin: 1in 1in 1in 1.5in;",
)


# Options every GLOW call to WeasyPrint's ``write_pdf()`` passes, so the PDF
# it writes is tagged (a structure tree with headings, lists, tables and
# reading order, ``/MarkInfo /Marked true``) and identifies itself as PDF/UA-1
# (ISO 14289-1) in its XMP metadata, with the document title shown in the
# title bar. WeasyPrint has supported both since version 68, the minimum GLOW
# pins. Without them WeasyPrint writes an untagged PDF that a screen reader
# meets as one undifferentiated run of text (issue #145).
#
# The PDF/UA identifier is a claim, not a certificate: the HTML still has to
# carry a <title>, a lang attribute, real headings and alt text, and the
# result should be checked with PAC or veraPDF.
TAGGED_PDF_OPTIONS: dict[str, object] = {
    "pdf_variant": "pdf/ua-1",
    "pdf_tags": True,
}


def write_tagged_pdf(html_doc, target=None):
    """Render a ``weasyprint.HTML`` document as tagged PDF/UA-1.

    Use this instead of calling WeasyPrint's ``write_pdf`` directly, so that no
    PDF GLOW produces is untagged. *target* is passed through to WeasyPrint:
    a path or file object to write to, or ``None`` to get the PDF as bytes.
    """
    return html_doc.write_pdf(target, **TAGGED_PDF_OPTIONS)


def weasyprint_available() -> bool:
    """Return True if WeasyPrint is installed and importable."""
    try:
        import weasyprint  # noqa: F401

        return True
    except (ImportError, OSError):
        return False


def convert_to_docx(
    src_path: Path,
    output_path: Path | None = None,
    *,
    title: str | None = None,
    lang: str = "en",
) -> tuple[Path, int]:
    """Convert a document to Word (.docx) via Pandoc.

    Args:
        src_path: Path to input file (.md, .rst, .odt, .rtf, .epub).
        output_path: Optional path for the .docx file.
        title: Document title metadata.
        lang: BCP-47 language tag for the document.

    Returns:
        (output_path, file_size_bytes)

    Raises:
        FileNotFoundError: If *src_path* does not exist.
        ValueError: If the extension is not in PANDOC_INPUT_EXTENSIONS.
        RuntimeError: If Pandoc is not installed or conversion fails.
    """
    src_path = Path(src_path)
    if not src_path.exists():
        raise FileNotFoundError(f"File not found: {src_path}")

    ext = src_path.suffix.lower()
    if ext not in PANDOC_INPUT_EXTENSIONS:
        raise ValueError(
            f"Cannot convert '{ext}' files to Word. "
            f"Supported: {', '.join(sorted(PANDOC_INPUT_EXTENSIONS))}"
        )
    # Don't convert .docx -> .docx
    if ext == ".docx":
        raise ValueError(
            "The input file is already a Word document (.docx). "
            "Choose a different input format."
        )

    exe = shutil.which("pandoc")
    if not exe:
        raise RuntimeError(
            "Pandoc is not installed. "
            "Install it from https://pandoc.org/installing.html"
        )

    if output_path is None:
        output_path = src_path.with_suffix(".docx")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if title is None:
        title = src_path.stem.replace("-", " ").replace("_", " ")

    input_fmt = _INPUT_FORMAT.get(ext, "markdown")

    cmd = [
        exe,
        "--standalone",
        "--wrap=none",
        "--from",
        input_fmt,
        "--to",
        "docx",
        "--metadata",
        f"title={title}",
        "--metadata",
        f"lang={lang}",
        "--output",
        str(output_path),
        str(src_path),
    ]

    log.info("Running: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            f"Pandoc conversion failed (exit code {result.returncode}): " f"{stderr}"
        )

    size = output_path.stat().st_size
    log.info(
        "Pandoc conversion complete: %s -> %s (%d bytes)",
        src_path.name,
        output_path.name,
        size,
    )
    return output_path, size


def convert_to_odt(
    src_path: Path,
    output_path: Path | None = None,
    *,
    title: str | None = None,
    lang: str = "en",
) -> tuple[Path, int]:
    """Convert a document to OpenDocument Text (.odt) via Pandoc."""
    src_path = Path(src_path)
    if not src_path.exists():
        raise FileNotFoundError(f"File not found: {src_path}")

    ext = src_path.suffix.lower()
    if ext not in PANDOC_INPUT_EXTENSIONS:
        raise ValueError(
            f"Cannot convert '{ext}' files to ODT. "
            f"Supported: {', '.join(sorted(PANDOC_INPUT_EXTENSIONS))}"
        )
    if ext == ".odt":
        raise ValueError(
            "The input file is already an OpenDocument Text (.odt). "
            "Choose a different input format."
        )

    exe = shutil.which("pandoc")
    if not exe:
        raise RuntimeError(
            "Pandoc is not installed. "
            "Install it from https://pandoc.org/installing.html"
        )

    if output_path is None:
        output_path = src_path.with_suffix(".odt")
    else:
        output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if title is None:
        title = src_path.stem.replace("-", " ").replace("_", " ")

    input_fmt = _INPUT_FORMAT.get(ext, "markdown")
    cmd = [
        exe,
        "--standalone",
        "--from",
        input_fmt,
        "--to",
        "odt",
        "--metadata",
        f"title={title}",
        "--metadata",
        f"lang={lang}",
        "--output",
        str(output_path),
        str(src_path),
    ]

    log.info("Running: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            f"Pandoc conversion failed (exit code {result.returncode}): {stderr}"
        )

    size = output_path.stat().st_size
    log.info(
        "Pandoc conversion complete: %s -> %s (%d bytes)",
        src_path.name,
        output_path.name,
        size,
    )
    return output_path, size


def convert_to_epub(
    src_path: Path,
    output_path: Path | None = None,
    *,
    title: str | None = None,
    css_path: Path | None = None,
    lang: str = "en",
) -> tuple[Path, int]:
    """Convert a document to EPUB 3 via Pandoc with ACB CSS.

    Args:
        src_path: Path to input file (.md, .rst, .odt, .rtf, .docx).
        output_path: Optional path for the .epub file.
        title: Document title metadata.
        css_path: Optional CSS file to embed. Uses ACB CSS if omitted.
            Pass the sentinel ``Path("__no_acb_css__")`` to skip ACB CSS.
        lang: BCP-47 language tag.

    Returns:
        (output_path, file_size_bytes)

    Raises:
        FileNotFoundError: If *src_path* does not exist.
        ValueError: If the extension is not in PANDOC_INPUT_EXTENSIONS.
        RuntimeError: If Pandoc is not installed or conversion fails.
    """
    src_path = Path(src_path)
    if not src_path.exists():
        raise FileNotFoundError(f"File not found: {src_path}")

    ext = src_path.suffix.lower()
    if ext not in PANDOC_INPUT_EXTENSIONS:
        raise ValueError(
            f"Cannot convert '{ext}' files to EPUB. "
            f"Supported: {', '.join(sorted(PANDOC_INPUT_EXTENSIONS))}"
        )
    # Don't convert .epub -> .epub
    if ext == ".epub":
        raise ValueError(
            "The input file is already an EPUB. " "Choose a different input format."
        )

    exe = shutil.which("pandoc")
    if not exe:
        raise RuntimeError(
            "Pandoc is not installed. "
            "Install it from https://pandoc.org/installing.html"
        )

    if output_path is None:
        output_path = src_path.with_suffix(".epub")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if title is None:
        title = src_path.stem.replace("-", " ").replace("_", " ")

    # Resolve CSS for EPUB embedding
    if css_path is not None and css_path.name == "__no_acb_css__":
        css_text = ""
    elif css_path and css_path.exists():
        css_text = css_path.read_text(encoding="utf-8")
    else:
        css_text = _ACB_CSS

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        input_fmt = _INPUT_FORMAT.get(ext, "markdown")

        cmd = [
            exe,
            "--from",
            input_fmt,
            "--to",
            "epub3",
            "--metadata",
            f"title={title}",
            "--metadata",
            f"lang={lang}",
            "--output",
            str(output_path),
        ]

        # Embed ACB CSS into the EPUB
        if css_text:
            css_file = tmp_dir / "acb-epub.css"
            css_file.write_text(css_text, encoding="utf-8")
            cmd.extend(["--css", str(css_file)])

        cmd.append(str(src_path))

        log.info("Running: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"Pandoc EPUB conversion failed (exit code {result.returncode}): "
                f"{stderr}"
            )

        size = output_path.stat().st_size
        log.info(
            "Pandoc EPUB conversion complete: %s -> %s (%d bytes)",
            src_path.name,
            output_path.name,
            size,
        )
        return output_path, size

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def convert_to_pdf(
    src_path: Path,
    output_path: Path | None = None,
    *,
    title: str | None = None,
    css_path: Path | None = None,
    lang: str = "en",
    binding_margin: bool = False,
) -> tuple[Path, int]:
    """Convert a document to PDF via Pandoc (HTML intermediate) + WeasyPrint.

    The two-step process:
    1. Pandoc converts the source to standalone HTML with ACB CSS.
    2. WeasyPrint renders the HTML+CSS to PDF, honoring @page rules,
       print line-height (1.15), and ACB BOP font standards (Arial 18pt).

    Args:
        src_path: Path to input file (.md, .rst, .odt, .rtf, .docx, .epub).
        output_path: Optional path for the .pdf file.
        title: Document title for PDF metadata.
        css_path: Optional CSS file. Uses ACB print CSS if omitted.
            Pass the sentinel ``Path("__no_acb_css__")`` to skip ACB CSS.
        lang: BCP-47 language tag.
        binding_margin: If True, adds 0.5-inch extra left margin for binding.

    Returns:
        (output_path, file_size_bytes)

    Raises:
        FileNotFoundError: If *src_path* does not exist.
        ValueError: If the extension is not supported.
        RuntimeError: If Pandoc or WeasyPrint is not installed.
    """
    src_path = Path(src_path)
    if not src_path.exists():
        raise FileNotFoundError(f"File not found: {src_path}")

    ext = src_path.suffix.lower()
    if ext not in PANDOC_INPUT_EXTENSIONS:
        raise ValueError(
            f"Cannot convert '{ext}' files to PDF. "
            f"Supported: {', '.join(sorted(PANDOC_INPUT_EXTENSIONS))}"
        )

    exe = shutil.which("pandoc")
    if not exe:
        raise RuntimeError(
            "Pandoc is not installed. "
            "Install it from https://pandoc.org/installing.html"
        )

    try:
        import weasyprint
    except (ImportError, OSError) as exc:
        raise RuntimeError(
            "WeasyPrint is not installed. PDF conversion is unavailable. "
            "Install it with: pip install weasyprint"
        ) from exc

    if output_path is None:
        output_path = src_path.with_suffix(".pdf")
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if title is None:
        title = src_path.stem.replace("-", " ").replace("_", " ")

    # Resolve CSS: use ACB print-optimized variant by default
    if css_path is not None and css_path.name == "__no_acb_css__":
        pdf_css = ""
    elif css_path and css_path.exists():
        pdf_css = css_path.read_text(encoding="utf-8")
    else:
        pdf_css = _ACB_PDF_CSS_BINDING if binding_margin else _ACB_PDF_CSS

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        # Step 1: Pandoc -> standalone HTML with ACB CSS embedded in <head>.
        # This ensures our stylesheet wins by cascade order in the rendered HTML.
        html_intermediate = tmp_dir / f"{src_path.stem}.html"
        input_fmt = _INPUT_FORMAT.get(ext, "markdown")

        cmd = [
            exe,
            "--standalone",
            "--from",
            input_fmt,
            "--to",
            "html5",
        ]

        if pdf_css:
            header_file = tmp_dir / "acb-pdf-header.html"
            header_file.write_text(
                f"<style>\n{pdf_css}\n</style>\n",
                encoding="utf-8",
            )
            cmd += ["--include-in-header", str(header_file)]

        cmd += [
            "--metadata",
            f"title={title}",
            "--metadata",
            f"lang={lang}",
            "--output",
            str(html_intermediate),
            str(src_path),
        ]

        log.info("Pandoc (HTML intermediate): %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"Pandoc conversion failed (exit code {result.returncode}): "
                f"{stderr}"
            )

        # Step 2: WeasyPrint renders HTML -> PDF. CSS is already embedded.
        log.info(
            "WeasyPrint: rendering %s -> %s", html_intermediate.name, output_path.name
        )
        html_doc = weasyprint.HTML(filename=str(html_intermediate))
        write_tagged_pdf(html_doc, str(output_path))

        size = output_path.stat().st_size
        log.info(
            "PDF conversion complete: %s -> %s (%d bytes)",
            src_path.name,
            output_path.name,
            size,
        )
        return output_path, size

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# LibreOffice-native formats that should be pre-converted before MarkItDown.
LIBREOFFICE_CONVERSIONS: dict[str, str] = {
    ".doc": ".docx",
    ".ppt": ".pptx",
    ".ods": ".xlsx",
    ".fods": ".xlsx",
    ".odp": ".pptx",
    ".fodp": ".pptx",
}


def libreoffice_available() -> bool:
    """Return True if the LibreOffice CLI is installed and reachable."""
    return shutil.which("soffice") is not None


def preconvert_via_libreoffice(
    src_path: Path,
    target_ext: str,
    out_dir: Path,
) -> Path | None:
    """Pre-convert a LibreOffice format to Office XML via ``soffice``.

    Returns the converted path on success, else ``None`` so callers can
    continue with their normal conversion path.
    """
    exe = shutil.which("soffice")
    if not exe:
        return None

    src_path = Path(src_path)
    out_dir = Path(out_dir)
    target_ext = target_ext.lower()

    if not src_path.exists() or not out_dir.exists() or not target_ext.startswith("."):
        return None

    try:
        # Re-discover source by directory listing to keep path provenance local.
        src_path = next(
            (
                f
                for f in src_path.parent.iterdir()
                if f.is_file() and f.name == src_path.name
            ),
            src_path,
        )
    except OSError:
        return None

    fmt = target_ext.lstrip(".")
    cmd = [
        exe,
        "--headless",
        "--convert-to",
        fmt,
        "--outdir",
        str(out_dir),
        str(src_path),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.SubprocessError, OSError):
        return None

    if result.returncode != 0:
        log.warning(
            "LibreOffice pre-conversion failed (%s -> %s): %s",
            src_path.name,
            target_ext,
            (result.stderr or "").strip(),
        )
        return None

    out_name = f"{src_path.stem}{target_ext}"
    converted = next(
        (
            f
            for f in out_dir.iterdir()
            if f.is_file() and f.name.lower() == out_name.lower()
        ),
        None,
    )
    if converted and converted.exists():
        return converted
    return None
