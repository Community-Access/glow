"""Audit ePub files for ACB Large Print and WCAG accessibility compliance.

Uses DAISY Ace (https://github.com/daisy/ace) as the primary checker,
providing 100+ axe-core HTML rules plus EPUB-specific metadata, navigation,
and page-list checks.  Supplements Ace output with ACB-specific rules
(font size, emphasis, heading hierarchy) via Pandoc HTML extraction.

For the web application, Ace is a required dependency shipped in the
Docker image.  For the desktop application, Ace requires Node.js to be
installed by the user (``npm install -g @daisy/ace``).  When Ace is not
installed on the desktop, the auditor falls back to built-in checks and
logs a warning recommending installation.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from . import constants as C
from .auditor import AuditResult, Finding

log = logging.getLogger("acb_large_print")


# Namespaces used in OPF files
_OPF_NS = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
    "meta": "http://www.idpf.org/2007/opf",
}

# Ambiguous link text patterns (lowercase)
_AMBIGUOUS_LINK_RE = re.compile(
    r"^(click here|here|link|read more|learn more|more|more info|details|this|download)$",
    re.IGNORECASE,
)

# URL-like pattern
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)

# EPUBCheck output patterns, e.g.:
# ERROR(RSC-005): chapter1.xhtml(12,5): Message
_EPUBCHECK_RE = re.compile(
    r"^(ERROR|WARNING)\(([^)]+)\):\s+(.+)$",
    re.IGNORECASE,
)


class _HTMLStructureParser(HTMLParser):
    """Lightweight HTML parser to extract headings, images, tables, links, and MathML."""

    def __init__(self):
        super().__init__()
        self.headings: list[int] = []  # heading levels in order
        self.images_without_alt: int = 0
        self.images_total: int = 0
        self.tables_without_headers: int = 0
        self.tables_total: int = 0
        self.ambiguous_links: list[str] = []
        self.mathml_total: int = 0
        self.mathml_without_alt: int = 0
        self.indented_elements: list[str] = []  # tags with text-indent or margin-left
        self._in_table = False
        self._table_has_th = False
        self._in_link = False
        self._link_text = ""
        self._in_heading = False
        self._in_math = False
        self._math_has_alt = False
        self._math_has_annotation = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()

        # Headings
        if tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag_lower[1])
            self.headings.append(level)
            self._in_heading = True

        # Images
        elif tag_lower == "img":
            self.images_total += 1
            attr_dict = dict(attrs)
            alt = attr_dict.get("alt")
            if alt is None or alt.strip() == "":
                self.images_without_alt += 1

        # Tables
        elif tag_lower == "table":
            self._in_table = True
            self._table_has_th = False
            self.tables_total += 1
        elif tag_lower == "th" and self._in_table:
            self._table_has_th = True

        # Links
        elif tag_lower == "a":
            self._in_link = True
            self._link_text = ""

        # MathML
        elif tag_lower == "math":
            self.mathml_total += 1
            self._in_math = True
            self._math_has_alt = False
            self._math_has_annotation = False
            attr_dict = dict(attrs)
            if attr_dict.get("alttext", "").strip():
                self._math_has_alt = True

        elif tag_lower == "annotation" and self._in_math:
            self._math_has_annotation = True

        # Check inline style for text-indent or margin-left on body text elements
        if tag_lower in ("p", "div", "li", "blockquote", "section", "article"):
            attr_dict = dict(attrs)
            style = attr_dict.get("style", "")
            if style:
                if re.search(r"text-indent\s*:\s*[^0]", style) or re.search(
                    r"margin-left\s*:\s*[^0]", style
                ):
                    self.indented_elements.append(tag_lower)

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower == "table" and self._in_table:
            if not self._table_has_th:
                self.tables_without_headers += 1
            self._in_table = False
        elif tag_lower == "a" and self._in_link:
            self._in_link = False
            text = self._link_text.strip()
            if text and (_AMBIGUOUS_LINK_RE.match(text) or _URL_RE.match(text)):
                self.ambiguous_links.append(text[:80])
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._in_heading = False
        elif tag_lower == "math" and self._in_math:
            if not self._math_has_alt and not self._math_has_annotation:
                self.mathml_without_alt += 1
            self._in_math = False

    def handle_data(self, data: str) -> None:
        if self._in_link:
            self._link_text += data


def audit_epub(file_path: str | Path) -> AuditResult:
    """Audit an ePub file for accessibility issues.

    Returns an AuditResult compatible with the existing audit pipeline.

    Always runs DAISY Ace first for comprehensive axe-core + EPUB checks,
    then supplements with ACB-specific checks Ace does not cover.
    On the desktop, falls back to built-in checks if Ace is not installed
    (with a warning recommending installation).
    """
    file_path = Path(file_path)
    result = AuditResult(file_path=str(file_path))

    # Run Ace for comprehensive checking (required in web, recommended on desktop)
    ace_used = False
    try:
        from .ace_runner import ace_available, audit_epub_with_ace

        if ace_available():
            ace_result = audit_epub_with_ace(file_path)
            if ace_result is not None and ace_result.findings:
                result.findings.extend(ace_result.findings)
                ace_used = True
                # Propagate conformance level (#15)
                ace_conformance = getattr(ace_result, "ace_conformance", None)
                if ace_conformance:
                    result.ace_conformance = ace_conformance  # type: ignore[attr-defined]
                log.info(
                    "Ace found %d findings for %s",
                    len(ace_result.findings),
                    file_path.name,
                )
        else:
            log.warning(
                "DAISY Ace is not installed. ePub audit will use built-in checks only. "
                "Install Ace for comprehensive EPUB accessibility checking: "
                "npm install -g @daisy/ace"
            )
    except ImportError:
        log.warning(
            "DAISY Ace module not available. Install Node.js and Ace for "
            "comprehensive EPUB accessibility checking: npm install -g @daisy/ace"
        )

    # Always run our built-in checks (Ace may miss ACB-specific rules)
    _check_with_epubcheck(file_path, result)

    # Phase 1: OPF metadata checks (no external dependencies)
    _check_opf_metadata(file_path, result, ace_used)

    # Phase 2: Structural checks via Pandoc HTML extraction
    if not ace_used:
        # Ace already covers HTML checks via axe-core; skip Pandoc if Ace ran
        _check_html_structure(file_path, result)

    # Phase 3: Human-readable accessibility metadata display
    # (W3C Display Guide 2.0 algorithm -- based on DAISY a11y-meta-viewer)
    try:
        from .epub_meta_display import extract_metadata_display

        result.metadata_display = extract_metadata_display(file_path)
    except Exception:
        log.debug(
            "Metadata display extraction failed for %s", file_path.name, exc_info=True
        )

    return result


def _epubcheck_command() -> list[str] | None:
    """Resolve EPUBCheck invocation command.

    Priority:
    1) `epubcheck` executable on PATH
    2) `EPUBCHECK_JAR` + `java -jar`
    """
    exe = shutil.which("epubcheck")
    if exe:
        return [exe]

    jar = os.environ.get("EPUBCHECK_JAR", "").strip()
    if jar and Path(jar).exists():
        java = shutil.which("java")
        if java:
            return [java, "-jar", jar]

    return None


def _check_with_epubcheck(file_path: Path, result: AuditResult) -> None:
    """Run EPUBCheck when available and map findings into AuditResult.

    This is best-effort and does not block standard auditing when EPUBCheck is
    unavailable or fails unexpectedly.
    """
    enabled = os.environ.get("GLOW_ENABLE_EPUBCHECK", "true").strip().lower()
    if enabled not in ("1", "true", "yes", "on"):
        return

    cmd = _epubcheck_command()
    if not cmd:
        log.debug("EPUBCheck unavailable: skipping external EPUB validation")
        return

    try:
        proc = subprocess.run(
            [*cmd, str(file_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (subprocess.SubprocessError, OSError):
        log.debug("EPUBCheck execution failed", exc_info=True)
        return

    combined = f"{proc.stdout}\n{proc.stderr}".strip()
    if not combined:
        return

    added = 0
    for line in combined.splitlines():
        m = _EPUBCHECK_RE.match(line.strip())
        if not m:
            continue
        severity, code, message = m.groups()
        rule_id = "EPUBCHECK-ERROR" if severity.upper() == "ERROR" else "EPUBCHECK-WARNING"
        result.add(rule_id, f"{code}: {message}")
        added += 1
        if added >= 30:
            # Cap volume to keep reports readable on severely malformed EPUBs.
            break

    # If EPUBCheck ran and failed but did not produce parseable lines, add summary.
    if added == 0 and proc.returncode != 0:
        tail = combined.splitlines()[-1].strip() if combined.splitlines() else "Validation failed"
        result.add("EPUBCHECK-ERROR", f"EPUBCheck reported validation failure: {tail}")


def _check_opf_metadata(
    file_path: Path, result: AuditResult, ace_used: bool = False
) -> None:
    """Parse the ePub OPF file to check metadata."""
    seen_rules = {f.rule_id for f in result.findings}
    try:
        with zipfile.ZipFile(str(file_path), "r") as zf:
            # Find the OPF file via the container.xml
            opf_path = _find_opf_path(zf)
            if not opf_path:
                return

            opf_xml = zf.read(opf_path).decode("utf-8", errors="replace")
            root = ET.fromstring(opf_xml)

            # Core checks -- skip if Ace already reported them
            if "EPUB-TITLE" not in seen_rules:
                _check_title(root, result)
            if "EPUB-LANGUAGE" not in seen_rules:
                _check_language(root, result)
            if "EPUB-NAV-DOCUMENT" not in seen_rules:
                _check_nav_document(root, zf, opf_path, result)
            if "EPUB-ACCESSIBILITY-METADATA" not in seen_rules:
                _check_accessibility_metadata(root, result)

            # New Ace-inspired checks (always run -- Ace may not cover these)
            _check_accessibility_hazard(root, result)
            _check_access_mode_sufficient(root, result)
            _check_page_list(root, zf, opf_path, result)
            _check_page_source(root, zf, opf_path, result)

    except (zipfile.BadZipFile, ET.ParseError, KeyError, OSError):
        # If we can't parse the ePub at all, still continue with Pandoc checks
        pass


def _find_opf_path(zf: zipfile.ZipFile) -> str | None:
    """Locate the OPF file inside the ePub ZIP."""
    try:
        container = zf.read("META-INF/container.xml").decode("utf-8", errors="replace")
        root = ET.fromstring(container)
        # container namespace
        ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
        rootfile = root.find(".//c:rootfile", ns)
        if rootfile is not None:
            return rootfile.get("full-path")
    except (KeyError, ET.ParseError):
        pass

    # Fallback: look for any .opf file
    for name in zf.namelist():
        if name.lower().endswith(".opf"):
            return name
    return None


def _check_title(root: ET.Element, result: AuditResult) -> None:
    """Check for dc:title in OPF metadata."""
    title_el = root.find(".//{http://purl.org/dc/elements/1.1/}title")
    if title_el is None or not (title_el.text or "").strip():
        result.add(
            "EPUB-TITLE",
            "ePub has no title set in OPF metadata",
        )


def _check_language(root: ET.Element, result: AuditResult) -> None:
    """Check for dc:language in OPF metadata."""
    lang_el = root.find(".//{http://purl.org/dc/elements/1.1/}language")
    if lang_el is None or not (lang_el.text or "").strip():
        result.add(
            "EPUB-LANGUAGE",
            "ePub has no language set in OPF metadata",
        )


def _check_nav_document(
    root: ET.Element,
    zf: zipfile.ZipFile,
    opf_path: str,
    result: AuditResult,
) -> None:
    """Check for a navigation document (EPUB 3 nav or EPUB 2 NCX)."""
    ns_opf = "http://www.idpf.org/2007/opf"

    # EPUB 3: look for item with properties="nav"
    manifest = root.find(f"{{{ns_opf}}}manifest")
    if manifest is not None:
        for item in manifest.findall(f"{{{ns_opf}}}item"):
            props = item.get("properties", "")
            if "nav" in props.split():
                return  # Has EPUB 3 nav document

    # EPUB 2: look for NCX in spine toc attribute or manifest
    spine = root.find(f"{{{ns_opf}}}spine")
    if spine is not None:
        toc_id = spine.get("toc")
        if toc_id and manifest is not None:
            ncx_item = manifest.find(f"{{{ns_opf}}}item[@id='{toc_id}']")
            if ncx_item is not None:
                return  # Has NCX

    # Check manifest for any NCX media type
    if manifest is not None:
        for item in manifest.findall(f"{{{ns_opf}}}item"):
            media_type = item.get("media-type", "")
            if media_type == "application/x-dtbncx+xml":
                return  # Has NCX

    result.add(
        "EPUB-NAV-DOCUMENT",
        "ePub has no navigation document (table of contents)",
    )


def _check_accessibility_metadata(root: ET.Element, result: AuditResult) -> None:
    """Check for schema.org accessibility metadata (EPUB Accessibility 1.1)."""
    ns_opf = "http://www.idpf.org/2007/opf"
    metadata = root.find(f"{{{ns_opf}}}metadata")
    if metadata is None:
        result.add(
            "EPUB-ACCESSIBILITY-METADATA",
            "ePub has no accessibility metadata (accessMode, accessibilityFeature)",
        )
        return

    # Look for meta elements with schema.org accessibility properties
    has_access_mode = False
    has_accessibility_feature = False

    for meta in metadata.findall(f"{{{ns_opf}}}meta"):
        prop = meta.get("property", "")
        if prop == "schema:accessMode":
            has_access_mode = True
        elif prop == "schema:accessibilityFeature":
            has_accessibility_feature = True

    if not has_access_mode and not has_accessibility_feature:
        result.add(
            "EPUB-ACCESSIBILITY-METADATA",
            "ePub has no schema.org accessibility metadata (accessMode, accessibilityFeature)",
        )


def _check_html_structure(file_path: Path, result: AuditResult) -> None:
    """Use Pandoc to convert ePub to HTML, then parse for structural issues."""
    exe = shutil.which("pandoc")
    if not exe:
        # Without Pandoc, we can only do metadata checks
        return

    try:
        proc = subprocess.run(
            [exe, "-f", "epub", "-t", "html", "--no-highlight", str(file_path)],
            capture_output=True,
            # Pandoc writes UTF-8. Without this, Windows decodes as cp1252,
            # the reader thread fails on the first curly quote, and stdout is None.
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if proc.returncode != 0 or proc.stdout is None:
            return

        html = proc.stdout
    except (subprocess.SubprocessError, OSError):
        return

    parser = _HTMLStructureParser()
    parser.feed(html)

    # Heading hierarchy check
    _check_headings(parser.headings, result)

    # Alt text check
    if parser.images_without_alt > 0:
        result.add(
            "EPUB-MISSING-ALT-TEXT",
            f"{parser.images_without_alt} of {parser.images_total} images "
            f"missing alternative text",
        )

    # Table header check
    if parser.tables_without_headers > 0:
        result.add(
            "EPUB-TABLE-HEADERS",
            f"{parser.tables_without_headers} of {parser.tables_total} tables "
            f"missing <th> header cells",
        )

    # Ambiguous link text check
    if parser.ambiguous_links:
        examples = ", ".join(f"'{t}'" for t in parser.ambiguous_links[:5])
        if len(parser.ambiguous_links) > 5:
            examples += f" (and {len(parser.ambiguous_links) - 5} more)"
        result.add(
            "EPUB-LINK-TEXT",
            f"Non-descriptive link text found: {examples}",
        )

    # MathML accessibility check
    if parser.mathml_without_alt > 0:
        result.add(
            "EPUB-MATHML-ALT",
            f"{parser.mathml_without_alt} of {parser.mathml_total} MathML "
            f"elements missing alttext attribute or annotation",
        )

    # CSS text-indent / margin-left check
    if parser.indented_elements:
        count = len(parser.indented_elements)
        tags = ", ".join(f"<{t}>" for t in parser.indented_elements[:5])
        if count > 5:
            tags += f" (and {count - 5} more)"
        result.add(
            "EPUB-TEXT-INDENT",
            f"{count} element(s) use CSS text-indent or margin-left "
            f"for indentation: {tags}",
        )


def _check_headings(headings: list[int], result: AuditResult) -> None:
    """Check heading hierarchy for skipped levels."""
    if len(headings) < 2:
        return

    for i in range(1, len(headings)):
        prev = headings[i - 1]
        curr = headings[i]
        # Skipped level: e.g., H1 -> H3
        if curr > prev + 1:
            result.add(
                "EPUB-HEADING-HIERARCHY",
                f"Heading level skipped: H{prev} followed by H{curr}",
            )
            return  # Report once


# ---------------------------------------------------------------------------
# New metadata checks inspired by DAISY Ace EPUB rules
# See: https://daisy.github.io/ace/rules/epub/
# ---------------------------------------------------------------------------


def _check_accessibility_hazard(root: ET.Element, result: AuditResult) -> None:
    """Check for schema:accessibilityHazard metadata (flashing, motion, sound)."""
    ns_opf = "http://www.idpf.org/2007/opf"
    metadata = root.find(f"{{{ns_opf}}}metadata")
    if metadata is None:
        return

    for meta in metadata.findall(f"{{{ns_opf}}}meta"):
        prop = meta.get("property", "")
        if prop == "schema:accessibilityHazard":
            return  # Has hazard declaration

    result.add(
        "EPUB-ACCESSIBILITY-HAZARD",
        "ePub does not declare accessibility hazards "
        "(should state noFlashingHazard, noMotionSimulationHazard, noSoundHazard, or specific hazards)",
    )


def _check_access_mode_sufficient(root: ET.Element, result: AuditResult) -> None:
    """Check for schema:accessModeSufficient metadata."""
    ns_opf = "http://www.idpf.org/2007/opf"
    metadata = root.find(f"{{{ns_opf}}}metadata")
    if metadata is None:
        return

    for meta in metadata.findall(f"{{{ns_opf}}}meta"):
        prop = meta.get("property", "")
        if prop == "schema:accessModeSufficient":
            return  # Has access mode sufficient declaration

    result.add(
        "EPUB-ACCESS-MODE-SUFFICIENT",
        "ePub does not declare sufficient access modes "
        "(e.g., textual, visual, auditory) for discovery metadata",
    )


def _check_page_list(
    root: ET.Element,
    zf: zipfile.ZipFile,
    opf_path: str,
    result: AuditResult,
) -> None:
    """Check that ePub with pageNavigation feature has an authored page list."""
    ns_opf = "http://www.idpf.org/2007/opf"
    metadata = root.find(f"{{{ns_opf}}}metadata")
    if metadata is None:
        return

    has_page_nav = False
    for meta in metadata.findall(f"{{{ns_opf}}}meta"):
        prop = meta.get("property", "")
        text = (meta.text or "").strip()
        if prop == "schema:accessibilityFeature" and text in (
            "pageNavigation",
            "printPageNumbers",
            "pageBreakMarkers",
        ):
            has_page_nav = True
            break

    if not has_page_nav:
        return  # No page navigation feature declared -- nothing to check

    # Find nav document and check for page-list
    manifest = root.find(f"{{{ns_opf}}}manifest")
    if manifest is None:
        return

    for item in manifest.findall(f"{{{ns_opf}}}item"):
        props = item.get("properties", "")
        if "nav" in props.split():
            href = item.get("href", "")
            if href:
                # Resolve relative to OPF
                import posixpath

                nav_path = posixpath.join(posixpath.dirname(opf_path), href)
                try:
                    nav_content = zf.read(nav_path).decode("utf-8", errors="replace")
                    if (
                        'epub:type="page-list"' in nav_content
                        or "epub:type='page-list'" in nav_content
                    ):
                        return  # Has page list
                except (KeyError, OSError):
                    pass

    result.add(
        "EPUB-PAGE-LIST",
        "ePub declares page navigation feature but has no authored page list",
    )


def _check_page_source(
    root: ET.Element,
    zf: zipfile.ZipFile,
    opf_path: str,
    result: AuditResult,
) -> None:
    """Check dc:source or pageBreakSource when reflowable ePub has a page list."""
    ns_opf = "http://www.idpf.org/2007/opf"
    ns_dc = "http://purl.org/dc/elements/1.1/"
    metadata = root.find(f"{{{ns_opf}}}metadata")
    if metadata is None:
        return

    # Check if this is a reflowable ePub (not fixed layout)
    for meta in metadata.findall(f"{{{ns_opf}}}meta"):
        prop = meta.get("property", "")
        text = (meta.text or "").strip()
        if prop == "rendition:layout" and text == "pre-paginated":
            return  # Fixed layout -- page source not required

    # Check if it has page features
    has_page_feature = False
    for meta in metadata.findall(f"{{{ns_opf}}}meta"):
        prop = meta.get("property", "")
        text = (meta.text or "").strip()
        if prop == "schema:accessibilityFeature" and text in (
            "printPageNumbers",
            "pageBreakMarkers",
        ):
            has_page_feature = True
            break

    if not has_page_feature:
        return

    # Check for dc:source
    source_el = metadata.find(f"{{{ns_dc}}}source")
    if source_el is not None and (source_el.text or "").strip():
        return  # Has dc:source

    # Check for pageBreakSource meta
    for meta in metadata.findall(f"{{{ns_opf}}}meta"):
        prop = meta.get("property", "")
        if prop == "schema:pageBreakSource" or prop == "pageBreakSource":
            return

    result.add(
        "EPUB-PAGE-SOURCE",
        "Reflowable ePub with page breaks should declare dc:source or pageBreakSource "
        "to identify the print source edition",
    )
