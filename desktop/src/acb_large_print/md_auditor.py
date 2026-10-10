"""Audit Markdown files for ACB Large Print and WCAG accessibility compliance.

Checks heading hierarchy, emphasis violations, bare URLs, ambiguous links,
missing alt text (including quality checks), emoji, em-dashes, table
descriptions, YAML front matter presence, code block language identifiers,
raw HTML patterns, fake list constructs, and ALL CAPS text.

Optionally runs markdownlint-cli as a subprocess for structural checks.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .auditor import AuditResult

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s*(.*)$")
_ATX_HEADING_STRICT_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_ITALIC_SINGLE_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
# CommonMark never treats an underscore inside a word as emphasis, so
# ``acb_large_print`` and ``AHG_DAY`` are names, not italics.
_ITALIC_UNDER_RE = re.compile(r"(?<![\w_])_(?![_\s])(.+?)(?<![_\s])_(?![\w_])")
# Inline code spans and bare URLs are literal text: emphasis and capitals
# inside them are names, not formatting.
_INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1")
_URL_RE = re.compile(r"https?://\S+")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ENTIRE_LINE_BOLD_RE = re.compile(r"^\s*\*\*.+\*\*\s*$")
_BARE_URL_RE = re.compile(r"(?<!\()\bhttps?://\S+(?!\))")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]+\)")
_MD_LINK_WITH_TARGET_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
_MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_TABLE_LINE_RE = re.compile(r"^\|.+\|$")
_TABLE_SEP_RE = re.compile(r"^\|[\s:|-]+\|$")
_EM_DASH_RE = re.compile(r"[\u2014\u2013]")
_URL_TEXT_RE = re.compile(r"^(https?://|www\.)", re.IGNORECASE)
_TRAILING_SPACES_RE = re.compile(r"( +)$")
_EMOJI_RE = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols and pictographs
    "\U0001f680-\U0001f6ff"  # transport and map
    "\U0001f900-\U0001f9ff"  # supplemental
    "\U0001fa00-\U0001fa6f"  # chess/extended-A
    "\U0001fa70-\U0001faff"  # extended-A cont.
    "\U00002702-\U000027b0"  # dingbats
    "\U000024c2-\U0001f251"  # enclosed
    "]+",
    re.UNICODE,
)

_AMBIGUOUS_LINK_TEXTS = frozenset(
    {
        "click here",
        "here",
        "link",
        "read more",
        "learn more",
        "more",
        "this",
        "this link",
        "this page",
        "more info",
        "info",
    }
)

# Alt text quality patterns
_ALT_FILENAME_RE = re.compile(
    r"^[\w\-]+\.(png|jpe?g|gif|svg|webp|bmp|tiff?|ico)$", re.IGNORECASE
)
_ALT_REDUNDANT_PREFIX_RE = re.compile(
    r"^(image of|photo of|picture of|screenshot of|graphic of|icon of|illustration of)\b",
    re.IGNORECASE,
)
# Decorative alt text is intentionally blank; single-char/symbol is suspicious
_ALT_TOO_SHORT_MIN = 3

# Raw HTML patterns
_RAW_TABLE_RE = re.compile(r"<table[\s>]", re.IGNORECASE)
_MOVING_CONTENT_RE = re.compile(r"<(marquee|blink)[\s>]", re.IGNORECASE)
_RAW_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_RAW_GENERIC_CONTAINER_RE = re.compile(r"<(div|span)[\s>]", re.IGNORECASE)
_RAW_PRESENTATIONAL_RE = re.compile(r"<(font|center)[\s>]", re.IGNORECASE)
_FENCED_CODE_LANG_RE = re.compile(r"^```(\S+)?")

# Fake list patterns
_FAKE_BULLET_CHARS = frozenset("\u2022\u25e6\u25aa\u2023\u25cf\u25cb")
# "1. item" is Markdown's own ordered list syntax, so it is never "fake".
# A manually numbered list is one Markdown does not recognise: "(1) item",
# "1 - item", "1: item".
_ORDERED_ITEM_RE = re.compile(r"^\d{1,9}[.)]\s+\S")
_FAKE_NUMBERED_RE = re.compile(r"^\s{0,2}(\(\d{1,2}\)|\d{1,2}\s*[-:\u2013])\s+\S")
_INLINE_BULLET_RE = re.compile(r"\S\s*[\u2022\u25e6\u25aa\u2023\u25cf\u25cb]\s+\S")

# ALL CAPS: three or more consecutive uppercase letters (skip code/URLs/acronyms)
# Five letters or more: four-letter acronyms (WCAG, HDMI, VPAT) are names,
# not shouting, and are far commoner in accessibility writing than shouted
# four-letter words.
_ALLCAPS_WORD_RE = re.compile(r"\b[A-Z]{5,}\b")
# Heading ends with terminal punctuation
_HEADING_TRAIL_PUNCT_RE = re.compile(r"[.;:]$")
# YAML front matter fence
_YAML_FENCE_RE = re.compile(r"^---\s*$")


def audit_markdown(file_path: str | Path) -> AuditResult:
    """Audit a Markdown file for accessibility issues.

    Returns an AuditResult compatible with the existing audit pipeline.
    """
    file_path = Path(file_path)
    text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    result = AuditResult(file_path=str(file_path))

    _check_yaml_front_matter(lines, result)
    _check_headings(lines, result)
    _check_emphasis(lines, result)
    _check_links(lines, result)
    _check_images(lines, result)
    _check_emoji(lines, result)
    _check_em_dashes(lines, result)
    _check_tables(lines, result)
    _check_code_blocks(lines, result)
    _check_raw_html(lines, result)
    _check_fake_lists(lines, result)
    _check_whitespace(lines, result)
    _check_allcaps(lines, result)

    return result


# ---------------------------------------------------------------------------
# Helpers — existing checks
# ---------------------------------------------------------------------------


def _check_yaml_front_matter(lines: list[str], result: AuditResult) -> None:
    """Check for YAML front matter block (--- ... ---) at top of file.

    Four checks (each conditional on the previous passing):
      1. MD-NO-YAML-FRONT-MATTER  -- block is absent entirely
      2. MD-YAML-UNCLOSED-FENCE   -- opening --- present but no closing ---
      3. MD-YAML-MISSING-TITLE    -- block present but no 'title:' key
      4. MD-YAML-MISSING-LANG     -- block present but no 'lang:' or 'language:' key
    """
    if not lines:
        return

    # Strip UTF-8 BOM from first line before matching
    first_line = lines[0].lstrip("\ufeff")
    if not _YAML_FENCE_RE.match(first_line):
        result.add(
            "MD-NO-YAML-FRONT-MATTER",
            "Document has no YAML front matter block (--- ... ---). "
            "Add a front matter block with at minimum 'title:' and 'lang:' fields.",
        )
        return

    # Find the closing --- fence (search up to 100 lines deep)
    MAX_FM_LINES = 100
    closing_idx: int | None = None
    for i in range(1, min(len(lines), MAX_FM_LINES)):
        if _YAML_FENCE_RE.match(lines[i]):
            closing_idx = i
            break

    if closing_idx is None:
        result.add(
            "MD-YAML-UNCLOSED-FENCE",
            "YAML front matter block opened with --- on line 1 but no closing --- "
            "fence was found. Add a closing --- to complete the block.",
        )
        return

    # Parse the front matter content between the two fences
    fm_lines = lines[1:closing_idx]
    fm_text = "\n".join(fm_lines).lower()

    # Check for title key (top-level only: "title:" at start of line)
    _YAML_TITLE_RE = re.compile(r"^title\s*:", re.MULTILINE)
    if not _YAML_TITLE_RE.search(fm_text):
        result.add(
            "MD-YAML-MISSING-TITLE",
            "YAML front matter is present but has no 'title:' field. "
            "Add 'title: Your Document Title' to the front matter block so the document title can be verified.",
        )

    # Check for lang / language key
    _YAML_LANG_RE = re.compile(r"^lang(?:uage)?\s*:", re.MULTILINE)
    if not _YAML_LANG_RE.search(fm_text):
        result.add(
            "MD-YAML-MISSING-LANG",
            "YAML front matter is present but has no 'lang:' or 'language:' field. "
            "Add 'lang: en' (or the appropriate BCP 47 language tag) to identify the document language.",
        )

    _YAML_AUTHOR_RE = re.compile(r"^author\s*:", re.MULTILINE)
    if not _YAML_AUTHOR_RE.search(fm_text):
        result.add(
            "MD-YAML-MISSING-AUTHOR",
            "YAML front matter is present but has no 'author:' field. "
            "Add 'author: Name' so assistive and publishing metadata include an author.",
        )

    _YAML_DESCRIPTION_RE = re.compile(r"^description\s*:", re.MULTILINE)
    if not _YAML_DESCRIPTION_RE.search(fm_text):
        result.add(
            "MD-YAML-MISSING-DESCRIPTION",
            "YAML front matter is present but has no 'description:' field. "
            "Add a short description to improve metadata quality and discoverability.",
        )


def _check_headings(lines: list[str], result: AuditResult) -> None:
    """Check heading hierarchy, multiple H1s, empty headings, length, and trailing punctuation."""
    levels: list[tuple[int, int]] = []  # (line_num, level)
    headings_by_level: dict[int, set[str]] = {}
    in_code_block = False
    total_nonempty_lines = 0
    para_since_heading = 0
    section_start_line = 1
    in_paragraph = False

    def _is_body_paragraph_line(text: str) -> bool:
        if not text:
            return False
        if text.startswith(("#", ">", "- ", "* ", "+ ")):
            return False
        if _FAKE_NUMBERED_RE.match(text) or _ORDERED_ITEM_RE.match(text):
            return False
        if _TABLE_LINE_RE.match(text) or _TABLE_SEP_RE.match(text):
            return False
        return True

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            in_paragraph = False
            continue
        if in_code_block:
            continue
        if stripped:
            total_nonempty_lines += 1

        # Empty heading: "## " with no following text
        m_empty = _ATX_HEADING_RE.match(line)
        if m_empty and not m_empty.group(2).strip():
            result.add(
                "MD-EMPTY-HEADING",
                f"H{len(m_empty.group(1))} heading marker with no text.",
                location=f"Line {i}",
            )
            in_paragraph = False
            continue

        m = _ATX_HEADING_STRICT_RE.match(line)
        if m:
            if para_since_heading >= 20:
                result.add(
                    "MD-LONG-SECTION-WITHOUT-HEADING",
                    f"Section contains {para_since_heading} paragraph(s) without an intermediate heading.",
                    location=f"Line {section_start_line}",
                )
            para_since_heading = 0
            in_paragraph = False

            level = len(m.group(1))
            heading_text = m.group(2).strip()
            levels.append((i, level))

            normalized_heading = re.sub(r"\s+", " ", heading_text.lower())
            seen = headings_by_level.setdefault(level, set())
            if normalized_heading in seen:
                result.add(
                    "MD-DUPLICATE-HEADING-TEXT",
                    f"Duplicate H{level} heading text: '{heading_text}'.",
                    location=f"Line {i}",
                )
            else:
                seen.add(normalized_heading)

            # Heading too long
            if len(heading_text) > 120:
                result.add(
                    "MD-HEADING-TOO-LONG",
                    f"H{level} heading is {len(heading_text)} characters (max 120): "
                    f"'{heading_text[:60]}...'",
                    location=f"Line {i}",
                )

            # Trailing terminal punctuation
            if _HEADING_TRAIL_PUNCT_RE.search(heading_text):
                result.add(
                    "MD-HEADING-ENDS-PUNCTUATION",
                    f"H{level} heading ends with terminal punctuation: '{heading_text[-1]}'",
                    location=f"Line {i}",
                )
            continue

        if _is_body_paragraph_line(stripped):
            if not in_paragraph:
                in_paragraph = True
                if para_since_heading == 0:
                    section_start_line = i
                para_since_heading += 1
        else:
            in_paragraph = False

    if para_since_heading >= 20:
        result.add(
            "MD-LONG-SECTION-WITHOUT-HEADING",
            f"Section contains {para_since_heading} paragraph(s) without an intermediate heading.",
            location=f"Line {section_start_line}",
        )

    if not levels and total_nonempty_lines >= 5:
        result.add(
            "MD-NO-HEADINGS",
            "Document contains no headings. Add structured headings to improve navigation.",
        )
        return

    # Multiple H1s
    h1_count = sum(1 for _, lvl in levels if lvl == 1)
    if h1_count > 1:
        result.add(
            "MD-MULTIPLE-H1",
            f"Found {h1_count} H1 headings; document should have only one.",
        )

    # Skipped levels
    for idx in range(1, len(levels)):
        prev_line, prev_lvl = levels[idx - 1]
        curr_line, curr_lvl = levels[idx]
        if curr_lvl > prev_lvl + 1:
            result.add(
                "MD-HEADING-HIERARCHY",
                f"Heading level skips from H{prev_lvl} to H{curr_lvl}.",
                location=f"Line {curr_line}",
            )


def _literal_free(line: str) -> str:
    """The line with inline code spans and URLs blanked out."""
    return _URL_RE.sub(" ", _INLINE_CODE_RE.sub(" ", line))


def _check_emphasis(lines: list[str], result: AuditResult) -> None:
    """Check for italic and bold-as-emphasis violations."""
    in_code_block = False
    for i, raw_line in enumerate(lines, 1):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if stripped.startswith("#"):
            continue
        line = _literal_free(raw_line)

        # Italic: *text* (not **bold**)
        for m in _ITALIC_SINGLE_RE.finditer(line):
            result.add(
                "MD-NO-ITALIC",
                f"Italic emphasis found: *{m.group(1)}*",
                location=f"Line {i}",
            )
        for m in _ITALIC_UNDER_RE.finditer(line):
            result.add(
                "MD-NO-ITALIC",
                f"Italic emphasis found: _{m.group(1)}_",
                location=f"Line {i}",
            )

        # Bold in body text (not headings)
        if _ENTIRE_LINE_BOLD_RE.match(line.strip()):
            result.add(
                "MD-ENTIRE-LINE-BOLDED",
                "Entire line is bolded. Use heading structure or normal body text instead.",
                location=f"Line {i}",
            )
        for m in _BOLD_RE.finditer(line):
            result.add(
                "MD-BOLD-EMPHASIS",
                f"Bold used for emphasis: **{m.group(1)}**",
                location=f"Line {i}",
            )


def _check_links(lines: list[str], result: AuditResult) -> None:
    """Check for bare URLs and ambiguous link text."""
    in_code_block = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Bare URLs (not inside markdown link syntax)
        cleaned = _MD_LINK_RE.sub("", line)
        cleaned = _MD_IMAGE_RE.sub("", cleaned)
        for m in _BARE_URL_RE.finditer(cleaned):
            result.add(
                "MD-BARE-URL",
                f"Bare URL should have descriptive link text: {m.group()[:60]}",
                location=f"Line {i}",
            )

        # Ambiguous link text
        for m in _MD_LINK_WITH_TARGET_RE.finditer(line):
            link_text = m.group(1).strip()
            text = link_text.lower()
            if not link_text:
                result.add(
                    "MD-EMPTY-LINK-TEXT",
                    "Link has empty visible text: [](...).",
                    location=f"Line {i}",
                )

            if _URL_TEXT_RE.match(link_text):
                result.add(
                    "MD-URL-AS-LINK-TEXT",
                    f"Link text is a URL instead of descriptive text: [{link_text}]",
                    location=f"Line {i}",
                )

            if text in _AMBIGUOUS_LINK_TEXTS:
                result.add(
                    "MD-AMBIGUOUS-LINK",
                    f"Ambiguous link text: [{m.group(1)}]",
                    location=f"Line {i}",
                )


def _check_images(lines: list[str], result: AuditResult) -> None:
    """Check images for missing alt text, filename alt text, redundant prefix, and too-short alt."""
    in_code_block = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        for m in _MD_IMAGE_RE.finditer(line):
            alt = m.group(1).strip()

            if not alt:
                result.add(
                    "MD-MISSING-ALT-TEXT",
                    "Image has no alternative text.",
                    location=f"Line {i}",
                )
                continue

            # Alt text is literally the filename
            if _ALT_FILENAME_RE.match(alt):
                result.add(
                    "MD-ALT-TEXT-FILENAME",
                    f"Alt text '{alt}' looks like a filename. "
                    "Replace with a meaningful description of the image content.",
                    location=f"Line {i}",
                )

            # Redundant prefix ("image of ...", "photo of ...")
            elif _ALT_REDUNDANT_PREFIX_RE.match(alt):
                prefix = alt.split()[0:3]
                result.add(
                    "MD-ALT-TEXT-REDUNDANT-PREFIX",
                    f"Alt text starts with redundant prefix '{' '.join(prefix)}'. "
                    "Screen readers already announce the image role; omit the prefix.",
                    location=f"Line {i}",
                )

            # Too short (but non-empty — empty is caught above)
            elif len(alt) < _ALT_TOO_SHORT_MIN:
                result.add(
                    "MD-ALT-TEXT-TOO-SHORT",
                    f"Alt text '{alt}' is only {len(alt)} character(s). "
                    "Provide a meaningful description of at least 3 characters, "
                    "or use empty alt text ![](url) only for decorative images.",
                    location=f"Line {i}",
                )


def _check_emoji(lines: list[str], result: AuditResult) -> None:
    """Check for emoji characters that should be removed."""
    in_code_block = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        for m in _EMOJI_RE.finditer(line):
            result.add(
                "MD-NO-EMOJI",
                f"Emoji found: {m.group()}",
                location=f"Line {i}",
            )


def _check_em_dashes(lines: list[str], result: AuditResult) -> None:
    """Check for em-dashes and en-dashes."""
    in_code_block = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if _EM_DASH_RE.search(line):
            result.add(
                "MD-EM-DASH",
                "Em-dash or en-dash found; use a plain dash instead.",
                location=f"Line {i}",
            )


def _check_tables(lines: list[str], result: AuditResult) -> None:
    """Check pipe tables for: preceding description, blank headers, column count mismatches."""
    in_table = False
    table_header_cols: int = 0
    in_code_block = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        is_table_line = bool(_TABLE_LINE_RE.match(stripped))
        is_sep_line = bool(_TABLE_SEP_RE.match(stripped))

        if is_table_line and not in_table:
            in_table = True
            # Check for descriptive text before the table. A blank line
            # between the description and the table is ordinary Markdown
            # style, so look back past blank lines; a heading or another
            # table directly above is what counts as "no description".
            if i >= 2:
                back = i - 2
                while back > 0 and not lines[back].strip():
                    back -= 1
                prev = lines[back].strip()
                if (not prev or prev.startswith("#") or _TABLE_LINE_RE.match(prev)
                        or _TABLE_SEP_RE.match(prev)):
                    result.add(
                        "MD-TABLE-NO-DESCRIPTION",
                        "Table has no preceding text description.",
                        location=f"Line {i}",
                    )
            else:
                result.add(
                    "MD-TABLE-NO-DESCRIPTION",
                    "Table at start of document has no preceding description.",
                    location=f"Line {i}",
                )

            # Parse header columns
            header_cells = [c.strip() for c in stripped.strip("|").split("|")]
            table_header_cols = len(header_cells)

            # Blank table headers
            blank_cols = [idx + 1 for idx, c in enumerate(header_cells) if not c]
            if blank_cols:
                result.add(
                    "MD-BLANK-TABLE-HEADER",
                    f"Pipe table has blank header cell(s) in column(s): {blank_cols}. "
                    "All column headers must have descriptive text.",
                    location=f"Line {i}",
                )

        elif is_table_line and in_table and not is_sep_line:
            # Data row — check column count
            row_cells = [c.strip() for c in stripped.strip("|").split("|")]
            if table_header_cols and len(row_cells) != table_header_cols:
                result.add(
                    "MD-TABLE-COLUMN-MISMATCH",
                    f"Table row has {len(row_cells)} cell(s) but header has "
                    f"{table_header_cols} column(s). Mismatched rows confuse screen readers.",
                    location=f"Line {i}",
                )

        elif not is_table_line and in_table:
            in_table = False
            table_header_cols = 0


# ---------------------------------------------------------------------------
# New checks (Phase 6)
# ---------------------------------------------------------------------------


def _check_code_blocks(lines: list[str], result: AuditResult) -> None:
    """Check fenced and indented code blocks for language identifiers."""
    in_fenced = False
    for i, line in enumerate(lines, 1):
        # Fenced code block open/close
        m = _FENCED_CODE_LANG_RE.match(line.strip())
        if m:
            if not in_fenced:
                in_fenced = True
                lang = m.group(1)
                if not lang:
                    result.add(
                        "MD-CODE-BLOCK-NO-LANGUAGE",
                        "Fenced code block has no language identifier (e.g. ```python). "
                        "Add a language tag so assistive technology can identify the content type.",
                        location=f"Line {i}",
                    )
            else:
                in_fenced = False
            continue

        if in_fenced:
            continue

        # Indented code block: 4+ spaces or a tab at start of non-blank line
        if (line.startswith("    ") or line.startswith("\t")) and line.strip():
            # Only flag if it looks like content, not a continuation list or blockquote
            result.add(
                "MD-INDENTED-CODE-BLOCK",
                "4-space indented code block cannot carry a language identifier. "
                "Convert to a fenced code block (``` lang) for better accessibility.",
                location=f"Line {i}",
            )


def _check_raw_html(lines: list[str], result: AuditResult) -> None:
    """Check for raw HTML table elements and moving content tags."""
    in_code_block = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        if _RAW_TABLE_RE.search(line):
            result.add(
                "MD-RAW-HTML-TABLE",
                "Raw HTML <table> in Markdown must include <th scope> header cells "
                "and a <caption> element. Consider using a pipe table instead.",
                location=f"Line {i}",
            )

        if _MOVING_CONTENT_RE.search(line):
            result.add(
                "MD-MOVING-CONTENT",
                "Raw <marquee> or <blink> HTML creates moving content that cannot "
                "be paused or stopped (WCAG 2.2.2). Remove this element entirely.",
                location=f"Line {i}",
            )

        if _RAW_BR_RE.search(line):
            result.add(
                "MD-RAW-BR-TAG",
                "Raw <br> tag found in Markdown. Prefer paragraph breaks or list structure.",
                location=f"Line {i}",
            )

        if _RAW_GENERIC_CONTAINER_RE.search(line):
            result.add(
                "MD-RAW-HTML-GENERIC-CONTAINER",
                "Raw <div> or <span> found in Markdown. Prefer semantic Markdown structure.",
                location=f"Line {i}",
            )

        if _RAW_PRESENTATIONAL_RE.search(line):
            result.add(
                "MD-RAW-HTML-PRESENTATIONAL",
                "Presentational HTML tag (<font> or <center>) found in Markdown.",
                location=f"Line {i}",
            )


def _check_fake_lists(lines: list[str], result: AuditResult) -> None:
    """Check for Unicode bullet characters and manually numbered lists used outside of Markdown list syntax."""
    in_code_block = False
    consecutive_numbered = 0

    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            consecutive_numbered = 0
            continue
        if in_code_block:
            continue

        stripped = line.strip()

        # Unicode bullet character at start of line (not inside a proper list item)
        if stripped and stripped[0] in _FAKE_BULLET_CHARS:
            result.add(
                "MD-FAKE-LIST-BULLET",
                f"Unicode bullet character '{stripped[0]}' used as inline list marker. "
                "Use a proper Markdown list item (- or *) so screen readers announce list structure.",
                location=f"Line {i}",
            )

        if _INLINE_BULLET_RE.search(line):
            result.add(
                "MD-FAKE-INLINE-BULLET",
                "Inline Unicode bullet found mid-sentence. Use a proper list structure.",
                location=f"Line {i}",
            )

        # Manually numbered list (1. 2. 3.) outside of Markdown ordered list syntax
        # A proper ordered list starts at 1. and uses consistent indentation —
        # we flag runs of 3+ consecutive lines that all match the pattern
        if _FAKE_NUMBERED_RE.match(stripped) and not stripped.startswith("-"):
            consecutive_numbered += 1
        else:
            if consecutive_numbered >= 3:
                result.add(
                    "MD-FAKE-NUMBERED-LIST",
                    f"{consecutive_numbered} consecutive lines appear to be a manually "
                    "numbered list. Convert to a proper Markdown ordered list (1. 2. 3.) "
                    "so screen readers can announce list structure.",
                    location=f"Line {i - consecutive_numbered}",
                )
            consecutive_numbered = 0

    # Flush at end of file
    if consecutive_numbered >= 3:
        result.add(
            "MD-FAKE-NUMBERED-LIST",
            f"{consecutive_numbered} consecutive lines appear to be a manually "
            "numbered list at end of file. Convert to a proper Markdown ordered list.",
            location=f"Line {len(lines) - consecutive_numbered + 1}",
        )


def _check_whitespace(lines: list[str], result: AuditResult) -> None:
    """Check for excessive blank lines and trailing spaces beyond Markdown hard-break usage."""
    blank_run = 0
    in_code_block = False

    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block

        if not line.strip():
            blank_run += 1
        else:
            if blank_run >= 3:
                start_line = i - blank_run
                result.add(
                    "MD-EXCESSIVE-BLANK-LINES",
                    f"Found {blank_run} consecutive blank lines.",
                    location=f"Line {start_line}",
                )
            blank_run = 0

        if in_code_block or not line.strip():
            continue

        m = _TRAILING_SPACES_RE.search(line)
        if m and len(m.group(1)) > 2:
            result.add(
                "MD-EXCESSIVE-TRAILING-SPACES",
                f"Line ends with {len(m.group(1))} trailing spaces. Use at most 2 for hard line breaks.",
                location=f"Line {i}",
            )

    if blank_run >= 3:
        start_line = len(lines) - blank_run + 1
        result.add(
            "MD-EXCESSIVE-BLANK-LINES",
            f"Found {blank_run} consecutive blank lines.",
            location=f"Line {start_line}",
        )


def _check_allcaps(lines: list[str], result: AuditResult) -> None:
    """Check for ALL CAPS words in body text (ACB guideline + WCAG 1.4.8).

    Allows acronyms of up to four letters, known longer acronyms, and
    anything inside inline code or a URL. Flags runs of 5+ uppercase letters
    that form a word.
    """
    in_code_block = False
    # Common known acronyms to skip (extend as needed)
    _SKIP_CAPS = frozenset({
        "WCAG", "HTML", "ARIA", "PDF", "EPUB", "DOCX", "XLSX", "PPTX",
        "URL", "ACB", "GLOW", "API", "JSON", "XML", "CSS", "HTTP",
        "HTTPS", "ID", "ISBN", "ISSN", "DOI", "FAQ", "NOTE", "TODO",
        "FIXME", "HACK", "WARN", "INFO", "DEBUG", "ERROR", "TRUE", "FALSE",
        "NULL", "NONE", "UTF", "ASCII", "YAML", "TOML",
    })

    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        # Skip headings (they have their own check)
        if line.strip().startswith("#"):
            continue

        for m in _ALLCAPS_WORD_RE.finditer(_literal_free(line)):
            word = m.group()
            if word not in _SKIP_CAPS:
                result.add(
                    "MD-ALLCAPS",
                    f"ALL CAPS word '{word}' found. Use mixed-case text; "
                    "some screen readers spell out all-caps words letter by letter.",
                    location=f"Line {i}",
                )
                break  # One finding per line to avoid noise


def run_markdownlint(file_path: str | Path) -> list[str]:
    """Run markdownlint-cli on a file and return raw output lines.

    Returns an empty list if markdownlint is not installed.
    """
    markdownlint = shutil.which("markdownlint")
    if not markdownlint:
        return []
    try:
        proc = subprocess.run(
            [markdownlint, str(file_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # markdownlint exits non-zero when issues are found
        output = proc.stdout.strip() or proc.stderr.strip()
        return output.splitlines() if output else []
    except (subprocess.TimeoutExpired, OSError):
        return []
