"""Helper to expose rule metadata to Jinja2 templates."""

from __future__ import annotations

import copy
import dataclasses
import re

from acb_large_print.constants import (
    AUDIT_RULES,
    DocFormat,
)

# Standards profiles used by Audit/Fix workflows.
PROFILE_ACB_2025 = "acb_2025"
PROFILE_APH_SUBMISSION = "aph_submission"
PROFILE_COMBINED_STRICT = "combined_strict"

PROFILE_LABELS: dict[str, str] = {
    PROFILE_ACB_2025: "ACB 2025 Baseline",
    PROFILE_APH_SUBMISSION: "APH Submission",
    PROFILE_COMBINED_STRICT: "Combined Strict (ACB + MSAC)",
}

# APH profile maps to the APH-aligned submission checks and defaults finalized
# in Release 1.2.0.
_APH_PROFILE_RULE_IDS: set[str] = {
    "ACB-FONT-FAMILY",
    "ACB-FONT-SIZE-BODY",
    "ACB-FONT-SIZE-H1",
    "ACB-FONT-SIZE-H2",
    "ACB-NO-ITALIC",
    "ACB-ALIGNMENT",
    "ACB-PARA-INDENT",
    "ACB-FIRST-LINE-INDENT",
    "ACB-MARGINS",
    "ACB-NO-ALLCAPS",
    "ACB-HEADING-HIERARCHY",
    "ACB-DOC-TITLE",
    "ACB-DOC-LANGUAGE",
    "ACB-MISSING-ALT-TEXT",
    "ACB-TABLE-HEADER-ROW",
    "ACB-LINK-TEXT",
}

# ---------------------------------------------------------------------------
# Help URL generation -- maps every rule to authoritative learning resources
# ---------------------------------------------------------------------------

# WCAG criterion slug lookup: "WCAG 1.1.1 ..." -> Understanding doc URL
_WCAG_SLUGS: dict[str, str] = {
    "1.1.1": "non-text-content",
    "1.3.1": "info-and-relationships",
    "1.3.2": "meaningful-sequence",
    "1.3.5": "identify-input-purpose",
    "1.4.1": "use-of-color",
    "1.4.3": "contrast-minimum",
    "1.4.4": "resize-text",
    "1.4.5": "images-of-text",
    "1.4.11": "non-text-contrast",
    "1.4.12": "text-spacing",
    "2.1.1": "keyboard",
    "2.4.1": "bypass-blocks",
    "2.4.2": "page-titled",
    "2.4.3": "focus-order",
    "2.4.4": "link-purpose-in-context",
    "2.4.5": "multiple-ways",
    "2.4.6": "headings-and-labels",
    "2.4.7": "focus-visible",
    "3.1.1": "language-of-page",
    "3.1.2": "language-of-parts",
    "3.3.1": "error-identification",
    "3.3.2": "labels-or-instructions",
    "4.1.2": "name-role-value",
}

_WCAG_RE = re.compile(r"WCAG\s+(\d+\.\d+\.\d+)")

# Per-rule authoritative help links: list of (label, url) tuples.
# Rules not listed here still get auto-generated WCAG links from acb_reference.
_RULE_HELP_URLS: dict[str, list[tuple[str, str]]] = {
    # --- ACB print rules ---
    "ACB-FONT-FAMILY": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
        ("WebAIM: Typefaces and Fonts", "https://webaim.org/techniques/fonts/"),
    ],
    "ACB-FONT-SIZE-BODY": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
        ("WebAIM: Typefaces and Fonts", "https://webaim.org/techniques/fonts/"),
    ],
    "ACB-FONT-SIZE-H1": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "ACB-FONT-SIZE-H2": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "ACB-NO-ITALIC": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    "ACB-BOLD-HEADINGS-ONLY": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    "ACB-ALIGNMENT": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
        (
            "WebAIM: Reading Order and Alignment",
            "https://webaim.org/techniques/semanticstructure/",
        ),
    ],
    "ACB-LINE-SPACING": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
        (
            "WCAG: Text Spacing",
            "https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html",
        ),
    ],
    "ACB-MARGINS": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    "ACB-WIDOW-ORPHAN": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    "ACB-NO-HYPHENATION": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    "ACB-PAGE-NUMBERS": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    "ACB-HEADING-HIERARCHY": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
        (
            "Microsoft: Accessible Word Headings",
            "https://support.microsoft.com/en-us/office/create-accessible-word-documents-d9bf3683-87ac-47ea-b91a-78dcacb3c66d#bkmk_headings",
        ),
    ],
    "ACB-NO-ALLCAPS": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
        ("WebAIM: Typefaces and Fonts", "https://webaim.org/techniques/fonts/"),
    ],
    "ACB-DOC-TITLE": [
        (
            "Microsoft: Set a Document Title",
            "https://support.microsoft.com/en-us/office/create-accessible-word-documents-d9bf3683-87ac-47ea-b91a-78dcacb3c66d#bkmk_doctitle",
        ),
        ("WebAIM: Page Title", "https://webaim.org/techniques/pagetitle/"),
    ],
    "ACB-DOC-LANGUAGE": [
        (
            "Microsoft: Set Document Language",
            "https://support.microsoft.com/en-us/office/create-accessible-word-documents-d9bf3683-87ac-47ea-b91a-78dcacb3c66d#bkmk_language",
        ),
        ("WebAIM: Document Language", "https://webaim.org/techniques/language/"),
    ],
    # --- MSAC rules ---
    "ACB-MISSING-ALT-TEXT": [
        (
            "Microsoft: Add Alt Text",
            "https://support.microsoft.com/en-us/office/add-alternative-text-to-a-shape-picture-chart-smartart-graphic-or-other-object-44989b2a-903c-4d9a-b742-6a75b451c669",
        ),
        ("WebAIM: Alternative Text", "https://webaim.org/techniques/alttext/"),
    ],
    "ACB-TABLE-HEADER-ROW": [
        (
            "Microsoft: Accessible Tables in Word",
            "https://support.microsoft.com/en-us/office/create-accessible-tables-in-word-cb464015-59dc-46a0-ac01-6217c62210e5",
        ),
        (
            "WebAIM: Creating Accessible Tables",
            "https://webaim.org/techniques/tables/data",
        ),
    ],
    "ACB-LINK-TEXT": [
        (
            "Microsoft: Accessible Hyperlinks",
            "https://support.microsoft.com/en-us/office/create-accessible-word-documents-d9bf3683-87ac-47ea-b91a-78dcacb3c66d#bkmk_links",
        ),
        ("WebAIM: Links and Hypertext", "https://webaim.org/techniques/hypertext/"),
    ],
    "ACB-FORM-FIELD-LABEL": [
        ("WebAIM: Creating Accessible Forms", "https://webaim.org/techniques/forms/"),
    ],
    "ACB-COMPLEX-TABLE": [
        (
            "Microsoft: Accessible Tables in Word",
            "https://support.microsoft.com/en-us/office/create-accessible-tables-in-word-cb464015-59dc-46a0-ac01-6217c62210e5",
        ),
        (
            "WebAIM: Creating Accessible Tables",
            "https://webaim.org/techniques/tables/data",
        ),
    ],
    "ACB-EMPTY-TABLE-CELL": [
        (
            "WebAIM: Creating Accessible Tables",
            "https://webaim.org/techniques/tables/data",
        ),
    ],
    "ACB-FLOATING-CONTENT": [
        (
            "Microsoft: Accessible Word Documents",
            "https://support.microsoft.com/en-us/office/create-accessible-word-documents-d9bf3683-87ac-47ea-b91a-78dcacb3c66d",
        ),
    ],
    "ACB-FAKE-LIST": [
        (
            "Microsoft: Accessible Word Documents",
            "https://support.microsoft.com/en-us/office/create-accessible-word-documents-d9bf3683-87ac-47ea-b91a-78dcacb3c66d",
        ),
    ],
    "ACB-REPEATED-SPACES": [
        (
            "Microsoft: Accessible Word Documents",
            "https://support.microsoft.com/en-us/office/create-accessible-word-documents-d9bf3683-87ac-47ea-b91a-78dcacb3c66d#bkmk_whitespace",
        ),
    ],
    "ACB-LONG-SECTION": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "ACB-DUPLICATE-HEADING": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "ACB-LINK-UNDERLINE": [
        ("WebAIM: Links and Hypertext", "https://webaim.org/techniques/hypertext/"),
    ],
    "ACB-DOC-AUTHOR": [
        (
            "Microsoft: Accessible Word Documents",
            "https://support.microsoft.com/en-us/office/create-accessible-word-documents-d9bf3683-87ac-47ea-b91a-78dcacb3c66d",
        ),
    ],
    # --- Excel rules ---
    "XLSX-TITLE": [
        (
            "Microsoft: Accessible Excel Workbooks",
            "https://support.microsoft.com/en-us/office/create-accessible-excel-workbooks-6cc05fc5-1314-48b5-8eb3-683e49b3e593#bkmk_doctitle",
        ),
    ],
    "XLSX-SHEET-NAME": [
        (
            "Microsoft: Accessible Excel Workbooks",
            "https://support.microsoft.com/en-us/office/create-accessible-excel-workbooks-6cc05fc5-1314-48b5-8eb3-683e49b3e593#bkmk_sheettabs",
        ),
    ],
    "XLSX-TABLE-HEADERS": [
        (
            "Microsoft: Accessible Excel Workbooks",
            "https://support.microsoft.com/en-us/office/create-accessible-excel-workbooks-6cc05fc5-1314-48b5-8eb3-683e49b3e593#bkmk_tableheaders",
        ),
        (
            "WebAIM: Creating Accessible Tables",
            "https://webaim.org/techniques/tables/data",
        ),
    ],
    "XLSX-MERGED-CELLS": [
        (
            "Microsoft: Accessible Excel Workbooks",
            "https://support.microsoft.com/en-us/office/create-accessible-excel-workbooks-6cc05fc5-1314-48b5-8eb3-683e49b3e593#bkmk_mergedcells",
        ),
    ],
    "XLSX-BLANK-COLUMN-HEADER": [
        (
            "Microsoft: Accessible Excel Workbooks",
            "https://support.microsoft.com/en-us/office/create-accessible-excel-workbooks-6cc05fc5-1314-48b5-8eb3-683e49b3e593",
        ),
    ],
    "XLSX-COLOR-ONLY": [
        (
            "Microsoft: Accessible Excel Workbooks",
            "https://support.microsoft.com/en-us/office/create-accessible-excel-workbooks-6cc05fc5-1314-48b5-8eb3-683e49b3e593#bkmk_color",
        ),
        ("WebAIM: Color and Contrast", "https://webaim.org/articles/contrast/"),
    ],
    "XLSX-HIDDEN-CONTENT": [
        (
            "Microsoft: Accessible Excel Workbooks",
            "https://support.microsoft.com/en-us/office/create-accessible-excel-workbooks-6cc05fc5-1314-48b5-8eb3-683e49b3e593",
        ),
    ],
    "XLSX-HEADER-FROZEN": [
        (
            "Microsoft: Accessible Excel Workbooks",
            "https://support.microsoft.com/en-us/office/create-accessible-excel-workbooks-6cc05fc5-1314-48b5-8eb3-683e49b3e593",
        ),
    ],
    "XLSX-SHEET-NAME-LENGTH": [
        (
            "Microsoft: Accessible Excel Workbooks",
            "https://support.microsoft.com/en-us/office/create-accessible-excel-workbooks-6cc05fc5-1314-48b5-8eb3-683e49b3e593#bkmk_sheettabs",
        ),
    ],
    # --- PowerPoint rules ---
    "PPTX-TITLE": [
        (
            "Microsoft: Accessible PowerPoint",
            "https://support.microsoft.com/en-us/office/create-accessible-powerpoint-presentations-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25",
        ),
    ],
    "PPTX-SLIDE-TITLE": [
        (
            "Microsoft: Accessible PowerPoint",
            "https://support.microsoft.com/en-us/office/create-accessible-powerpoint-presentations-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25#bkmk_slidetitles",
        ),
        (
            "WebAIM: PowerPoint Accessibility",
            "https://webaim.org/techniques/powerpoint/",
        ),
    ],
    "PPTX-READING-ORDER": [
        (
            "Microsoft: Slide Reading Order",
            "https://support.microsoft.com/en-us/office/create-accessible-powerpoint-presentations-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25#bkmk_readingorder",
        ),
    ],
    "PPTX-TITLE-READING-ORDER": [
        (
            "Microsoft: Slide Reading Order",
            "https://support.microsoft.com/en-us/office/create-accessible-powerpoint-presentations-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25#bkmk_readingorder",
        ),
    ],
    "PPTX-SMALL-FONT": [
        (
            "WebAIM: PowerPoint Accessibility",
            "https://webaim.org/techniques/powerpoint/",
        ),
    ],
    "PPTX-SPEAKER-NOTES": [
        (
            "Microsoft: Accessible PowerPoint",
            "https://support.microsoft.com/en-us/office/create-accessible-powerpoint-presentations-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25",
        ),
    ],
    "PPTX-CHART-ALT-TEXT": [
        (
            "Microsoft: Add Alt Text",
            "https://support.microsoft.com/en-us/office/add-alternative-text-to-a-shape-picture-chart-smartart-graphic-or-other-object-44989b2a-903c-4d9a-b742-6a75b451c669",
        ),
        ("WebAIM: Alternative Text", "https://webaim.org/techniques/alttext/"),
    ],
    "PPTX-DUPLICATE-SLIDE-TITLE": [
        (
            "Microsoft: Accessible PowerPoint",
            "https://support.microsoft.com/en-us/office/create-accessible-powerpoint-presentations-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25#bkmk_slidetitles",
        ),
    ],
    "PPTX-HEADING-SKIP": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    # --- Markdown rules ---
    "MD-HEADING-HIERARCHY": [
        (
            "CommonMark: ATX Headings",
            "https://spec.commonmark.org/0.31.2/#atx-headings",
        ),
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "MD-MULTIPLE-H1": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "MD-NO-ITALIC": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    "MD-BOLD-EMPHASIS": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    "MD-BARE-URL": [
        ("CommonMark: Links", "https://spec.commonmark.org/0.31.2/#links"),
        ("WebAIM: Links and Hypertext", "https://webaim.org/techniques/hypertext/"),
    ],
    "MD-AMBIGUOUS-LINK": [
        ("WebAIM: Links and Hypertext", "https://webaim.org/techniques/hypertext/"),
    ],
    "MD-EMPTY-LINK-TEXT": [
        ("WebAIM: Links and Hypertext", "https://webaim.org/techniques/hypertext/"),
    ],
    "MD-URL-AS-LINK-TEXT": [
        ("WebAIM: Links and Hypertext", "https://webaim.org/techniques/hypertext/"),
    ],
    "MD-MISSING-ALT-TEXT": [
        ("CommonMark: Images", "https://spec.commonmark.org/0.31.2/#images"),
        ("WebAIM: Alternative Text", "https://webaim.org/techniques/alttext/"),
    ],
    "MD-NO-EMOJI": [
        ("Unicode Emoji Standard", "https://unicode.org/emoji/"),
    ],
    "MD-TABLE-NO-DESCRIPTION": [
        (
            "WebAIM: Creating Accessible Tables",
            "https://webaim.org/techniques/tables/data",
        ),
    ],
    "MD-EM-DASH": [],
    "MD-ALT-TEXT-FILENAME": [
        ("WebAIM: Alternative Text", "https://webaim.org/techniques/alttext/"),
        ("CommonMark: Images", "https://spec.commonmark.org/0.31.2/#images"),
    ],
    "MD-ALT-TEXT-REDUNDANT-PREFIX": [
        ("WebAIM: Alternative Text", "https://webaim.org/techniques/alttext/"),
    ],
    "MD-ALT-TEXT-TOO-SHORT": [
        ("WebAIM: Alternative Text", "https://webaim.org/techniques/alttext/"),
    ],
    "MD-NO-YAML-FRONT-MATTER": [
        (
            "YAML Front Matter (Jekyll docs)",
            "https://jekyllrb.com/docs/front-matter/",
        ),
        ("WCAG 2.4.2 Page Titled", "https://www.w3.org/WAI/WCAG22/Understanding/page-titled"),
    ],
    "MD-YAML-UNCLOSED-FENCE": [
        (
            "YAML Front Matter (Jekyll docs)",
            "https://jekyllrb.com/docs/front-matter/",
        ),
        ("WCAG 2.4.2 Page Titled", "https://www.w3.org/WAI/WCAG22/Understanding/page-titled"),
    ],
    "MD-YAML-MISSING-TITLE": [
        (
            "WCAG 2.4.2 Page Titled",
            "https://www.w3.org/WAI/WCAG22/Understanding/page-titled",
        ),
    ],
    "MD-YAML-MISSING-LANG": [
        (
            "WCAG 3.1.1 Language of Page",
            "https://www.w3.org/WAI/WCAG22/Understanding/language-of-page",
        ),
        (
            "BCP 47 Language Tags",
            "https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry",
        ),
    ],
    "MD-YAML-MISSING-AUTHOR": [
        (
            "YAML Front Matter (Jekyll docs)",
            "https://jekyllrb.com/docs/front-matter/",
        ),
    ],
    "MD-YAML-MISSING-DESCRIPTION": [
        (
            "YAML Front Matter (Jekyll docs)",
            "https://jekyllrb.com/docs/front-matter/",
        ),
    ],
    "MD-NO-HEADINGS": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "MD-DUPLICATE-HEADING-TEXT": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "MD-LONG-SECTION-WITHOUT-HEADING": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "MD-EMPTY-HEADING": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "MD-HEADING-TOO-LONG": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "MD-HEADING-ENDS-PUNCTUATION": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "MD-CODE-BLOCK-NO-LANGUAGE": [
        (
            "CommonMark: Fenced Code Blocks",
            "https://spec.commonmark.org/0.31.2/#fenced-code-blocks",
        ),
    ],
    "MD-INDENTED-CODE-BLOCK": [
        (
            "CommonMark: Fenced Code Blocks",
            "https://spec.commonmark.org/0.31.2/#fenced-code-blocks",
        ),
    ],
    "MD-RAW-HTML-TABLE": [
        (
            "WebAIM: Creating Accessible Tables",
            "https://webaim.org/techniques/tables/data",
        ),
    ],
    "MD-MOVING-CONTENT": [
        (
            "WCAG 2.2.2 Pause, Stop, Hide",
            "https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide",
        ),
    ],
    "MD-RAW-BR-TAG": [
        (
            "CommonMark: Hard Line Breaks",
            "https://spec.commonmark.org/0.31.2/#hard-line-breaks",
        ),
    ],
    "MD-RAW-HTML-GENERIC-CONTAINER": [
        (
            "CommonMark: Raw HTML",
            "https://spec.commonmark.org/0.31.2/#raw-html",
        ),
    ],
    "MD-RAW-HTML-PRESENTATIONAL": [
        (
            "CommonMark: Raw HTML",
            "https://spec.commonmark.org/0.31.2/#raw-html",
        ),
    ],
    "MD-BLANK-TABLE-HEADER": [
        (
            "WebAIM: Creating Accessible Tables",
            "https://webaim.org/techniques/tables/data",
        ),
    ],
    "MD-TABLE-COLUMN-MISMATCH": [
        (
            "WebAIM: Creating Accessible Tables",
            "https://webaim.org/techniques/tables/data",
        ),
    ],
    "MD-FAKE-LIST-BULLET": [
        (
            "CommonMark: Lists",
            "https://spec.commonmark.org/0.31.2/#lists",
        ),
    ],
    "MD-FAKE-NUMBERED-LIST": [
        (
            "CommonMark: Lists",
            "https://spec.commonmark.org/0.31.2/#lists",
        ),
    ],
    "MD-FAKE-INLINE-BULLET": [
        (
            "CommonMark: Lists",
            "https://spec.commonmark.org/0.31.2/#lists",
        ),
    ],
    "MD-EXCESSIVE-BLANK-LINES": [
        (
            "CommonMark: Blank Lines",
            "https://spec.commonmark.org/0.31.2/#blank-lines",
        ),
    ],
    "MD-EXCESSIVE-TRAILING-SPACES": [
        (
            "CommonMark: Hard Line Breaks",
            "https://spec.commonmark.org/0.31.2/#hard-line-breaks",
        ),
    ],
    "MD-ENTIRE-LINE-BOLDED": [
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "MD-ALLCAPS": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    # --- PDF rules ---
    "PDF-TITLE": [
        (
            "Adobe: Document Title",
            "https://helpx.adobe.com/acrobat/using/creating-accessible-pdfs.html",
        ),
        ("WebAIM: PDF Accessibility", "https://webaim.org/techniques/acrobat/"),
    ],
    "PDF-LANGUAGE": [
        (
            "Adobe: Document Language",
            "https://helpx.adobe.com/acrobat/using/creating-accessible-pdfs.html",
        ),
        ("WebAIM: PDF Accessibility", "https://webaim.org/techniques/acrobat/"),
    ],
    "PDF-TAGGED": [
        (
            "Adobe: Creating Accessible PDFs",
            "https://helpx.adobe.com/acrobat/using/creating-accessible-pdfs.html",
        ),
        ("WebAIM: PDF Accessibility", "https://webaim.org/techniques/acrobat/"),
    ],
    "PDF-FONT-SIZE": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    "PDF-FONT-FAMILY": [
        (
            "ACB Large Print Guidelines (PDF)",
            "https://www.acb.org/large-print-guidelines",
        ),
    ],
    "PDF-NO-IMAGES-OF-TEXT": [
        (
            "Adobe: Scan and OCR",
            "https://helpx.adobe.com/acrobat/using/scan-documents-pdf.html",
        ),
        ("WebAIM: PDF Accessibility", "https://webaim.org/techniques/acrobat/"),
    ],
    "PDF-BOOKMARKS": [
        (
            "Adobe: Creating Accessible PDFs",
            "https://helpx.adobe.com/acrobat/using/creating-accessible-pdfs.html",
        ),
    ],
    # --- ePub rules ---
    "EPUB-TITLE": [
        ("EPUB Accessibility 1.1", "https://www.w3.org/TR/epub-a11y-11/"),
        (
            "Accessible Publishing Knowledge Base: Title",
            "https://kb.daisy.org/publishing/docs/epub/title.html",
        ),
    ],
    "EPUB-LANGUAGE": [
        ("EPUB Accessibility 1.1", "https://www.w3.org/TR/epub-a11y-11/"),
        (
            "Accessible Publishing Knowledge Base: Language",
            "https://kb.daisy.org/publishing/docs/epub/language.html",
        ),
    ],
    "EPUB-NAV-DOCUMENT": [
        ("EPUB Accessibility 1.1", "https://www.w3.org/TR/epub-a11y-11/"),
        (
            "Accessible Publishing Knowledge Base: Navigation",
            "https://kb.daisy.org/publishing/docs/navigation/toc.html",
        ),
    ],
    "EPUB-HEADING-HIERARCHY": [
        (
            "Accessible Publishing Knowledge Base: Headings",
            "https://kb.daisy.org/publishing/docs/html/headings.html",
        ),
        ("WebAIM: Headings", "https://webaim.org/techniques/semanticstructure/"),
    ],
    "EPUB-MISSING-ALT-TEXT": [
        (
            "Accessible Publishing Knowledge Base: Images",
            "https://kb.daisy.org/publishing/docs/html/images.html",
        ),
        ("WebAIM: Alternative Text", "https://webaim.org/techniques/alttext/"),
    ],
    "EPUB-TABLE-HEADERS": [
        (
            "Accessible Publishing Knowledge Base: Tables",
            "https://kb.daisy.org/publishing/docs/html/tables.html",
        ),
        (
            "WebAIM: Creating Accessible Tables",
            "https://webaim.org/techniques/tables/data",
        ),
    ],
    "EPUB-ACCESSIBILITY-METADATA": [
        (
            "EPUB Accessibility 1.1: Discovery Metadata",
            "https://www.w3.org/TR/epub-a11y-11/#sec-disc-package",
        ),
        (
            "Schema.org: Accessibility Properties",
            "https://www.w3.org/wiki/WebSchemas/Accessibility",
        ),
    ],
    "EPUB-LINK-TEXT": [
        ("WebAIM: Links and Hypertext", "https://webaim.org/techniques/hypertext/"),
        (
            "Accessible Publishing Knowledge Base: Links",
            "https://kb.daisy.org/publishing/docs/html/links.html",
        ),
    ],
    "EPUB-ACCESSIBILITY-HAZARD": [
        (
            "EPUB Accessibility 1.1: Discovery Metadata",
            "https://www.w3.org/TR/epub-a11y-11/#sec-disc-package",
        ),
        (
            "Accessible Publishing Knowledge Base: Hazards",
            "https://kb.daisy.org/publishing/docs/metadata/schema.org/accessibilityHazard.html",
        ),
        ("DAISY Ace: EPUB Rules", "https://daisy.github.io/ace/rules/epub/"),
    ],
    "EPUB-ACCESS-MODE-SUFFICIENT": [
        (
            "EPUB Accessibility 1.1: Discovery Metadata",
            "https://www.w3.org/TR/epub-a11y-11/#sec-disc-package",
        ),
        (
            "Accessible Publishing Knowledge Base: Access Mode",
            "https://kb.daisy.org/publishing/docs/metadata/schema.org/accessModeSufficient.html",
        ),
        ("DAISY Ace: EPUB Rules", "https://daisy.github.io/ace/rules/epub/"),
    ],
    "EPUB-PAGE-LIST": [
        (
            "Accessible Publishing Knowledge Base: Page List",
            "https://kb.daisy.org/publishing/docs/navigation/pagelist.html",
        ),
        ("DAISY Ace: EPUB Rules", "https://daisy.github.io/ace/rules/epub/"),
    ],
    "EPUB-PAGE-SOURCE": [
        (
            "Accessible Publishing Knowledge Base: Page List",
            "https://kb.daisy.org/publishing/docs/navigation/pagelist.html",
        ),
        ("EPUB Accessibility 1.1", "https://www.w3.org/TR/epub-a11y-11/"),
    ],
    "EPUB-MATHML-ALT": [
        (
            "Accessible Publishing Knowledge Base: MathML",
            "https://kb.daisy.org/publishing/docs/html/mathml.html",
        ),
        ("DAISY MathCAT (Math Speech)", "https://github.com/daisy/MathCAT"),
        ("WebAIM: Alternative Text", "https://webaim.org/techniques/alttext/"),
    ],
    "ACE-EPUB-CHECK": [
        ("DAISY Ace: EPUB Rules", "https://daisy.github.io/ace/rules/epub/"),
        ("EPUB Accessibility 1.1", "https://www.w3.org/TR/epub-a11y-11/"),
        ("Accessible Publishing Knowledge Base", "https://kb.daisy.org/publishing/"),
    ],
    "ACE-AXE-CHECK": [
        ("DAISY Ace: HTML Rules", "https://daisy.github.io/ace/rules/html/"),
        (
            "Deque axe-core Rules",
            "https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md",
        ),
        ("Accessible Publishing Knowledge Base", "https://kb.daisy.org/publishing/"),
    ],
}


def _wcag_url_from_reference(acb_reference: str) -> tuple[str, str] | None:
    """Extract a WCAG Understanding doc URL from an acb_reference string."""
    m = _WCAG_RE.search(acb_reference)
    if not m:
        return None
    criterion = m.group(1)
    slug = _WCAG_SLUGS.get(criterion)
    if not slug:
        return None
    return (
        f"WCAG {criterion} Understanding",
        f"https://www.w3.org/WAI/WCAG22/Understanding/{slug}.html",
    )


def get_help_urls(rule_id: str, acb_reference: str) -> list[dict[str, str]]:
    """Return list of help link dicts for a rule.

    Each dict has 'label' and 'url' keys. Combines manually curated
    links with auto-generated WCAG Understanding doc links.
    """
    urls: list[dict[str, str]] = []
    # Add curated links first
    for label, url in _RULE_HELP_URLS.get(rule_id, []):
        urls.append({"label": label, "url": url})
    # Auto-generate WCAG link from acb_reference if not already present
    wcag = _wcag_url_from_reference(acb_reference)
    if wcag:
        # Avoid duplicate: check if we already have a link to the same page
        wcag_base = wcag[1].split("?")[0]
        if not any(wcag_base in u["url"] for u in urls):
            urls.append({"label": wcag[0], "url": wcag[1]})
    return urls


def _rule_to_dict(rule) -> dict:
    """Convert a RuleDef to a template-friendly dict with help_urls."""
    rule_type = "other"
    if rule.rule_id.startswith("ACB-"):
        rule_type = "acb"
    elif rule.rule_id.startswith("MSAC-"):
        rule_type = "msac"
    elif rule.rule_id.startswith("APH-"):
        rule_type = "aph"
    elif rule.rule_id.startswith("EPUB-"):
        rule_type = "epub"
    elif rule.rule_id.startswith("MD-"):
        rule_type = "markdown"

    return {
        "rule_id": rule.rule_id,
        "description": rule.description,
        "severity": rule.severity.value,
        "acb_reference": rule.acb_reference,
        "category": rule.category.value,
        "auto_fixable": rule.auto_fixable,
        "formats": sorted(f.value for f in rule.formats),
        "help_urls": get_help_urls(rule.rule_id, rule.acb_reference),
        "rule_type": rule_type,
    }


def get_rules_by_severity() -> dict[str, list[dict]]:
    """Return AUDIT_RULES grouped by severity for template rendering."""
    groups: dict[str, list[dict]] = {
        "Critical": [],
        "High": [],
        "Medium": [],
        "Low": [],
    }
    for rule in AUDIT_RULES.values():
        groups[rule.severity.value].append(_rule_to_dict(rule))
    return groups


def get_rules_by_category() -> dict[str, list[dict]]:
    """Return AUDIT_RULES grouped by category for template rendering."""
    groups: dict[str, list[dict]] = {"acb": [], "msac": []}
    for rule in AUDIT_RULES.values():
        groups[rule.category.value].append(_rule_to_dict(rule))
    return groups


def get_all_rule_ids() -> set[str]:
    """Return set of all rule IDs."""
    return set(AUDIT_RULES.keys())


def get_rule_ids_by_severity(*severities: str) -> set[str]:
    """Return rule IDs matching the given severity labels."""
    sev_set = set(severities)
    return {r.rule_id for r in AUDIT_RULES.values() if r.severity.value in sev_set}


def get_rule_ids_by_category(*categories: str) -> set[str]:
    """Return rule IDs matching the given category values ('acb', 'msac')."""
    cat_set = set(categories)
    return {r.rule_id for r in AUDIT_RULES.values() if r.category.value in cat_set}


def get_rule_ids_by_format(fmt_str: str) -> set[str]:
    """Return rule IDs applicable to a document format ('docx', 'xlsx', 'pptx')."""
    try:
        fmt = DocFormat(fmt_str)
    except ValueError:
        return set(AUDIT_RULES.keys())  # unknown format: return all
    return {r.rule_id for r in AUDIT_RULES.values() if fmt in r.formats}


def get_rule_ids_by_profile(profile: str) -> set[str]:
    """Return rule IDs enabled by standards profile."""
    normalized = (profile or PROFILE_ACB_2025).strip().lower()
    if normalized == PROFILE_APH_SUBMISSION:
        return set(_APH_PROFILE_RULE_IDS)
    # ACB baseline and combined strict currently use all implemented rules.
    return get_all_rule_ids()


def get_profile_label(profile: str) -> str:
    """Return user-facing standards profile label."""
    normalized = (profile or PROFILE_ACB_2025).strip().lower()
    return PROFILE_LABELS.get(normalized, PROFILE_LABELS[PROFILE_ACB_2025])


def filter_findings(findings: list, rule_ids: set[str]) -> list:
    """Filter a findings list to include only the given rule IDs."""
    return [f for f in findings if f.rule_id in rule_ids]


def with_findings(result, findings: list):
    """Return *result* carrying *findings*, without mutating anything.

    The legacy audit result allowed ``result.findings = ...``; the
    post-split shared-core ``AuditResult`` is a frozen, slotted dataclass and
    raises on that assignment. Because the shared core is installed in
    deployment and absent from a bare source checkout, the in-place version
    passed every local test and returned HTTP 500 from every audit on the
    deployed site -- the same "works from source, breaks deployed" shape the
    MCP server hit after the 8.0.0 split.
    """
    try:
        result.findings = findings
        return result
    except Exception:
        pass
    try:
        return dataclasses.replace(result, findings=findings)
    except Exception:
        pass
    copied = copy.copy(result)
    try:
        object.__setattr__(copied, "findings", findings)
    except Exception:
        # Nothing worked: return the unfiltered result rather than failing
        # the request. The report shows more than the user asked for, which
        # is wrong but recoverable; a 500 is not.
        return result
    return copied


def apply_rule_policy(result, policy):
    """Return *result* with the user's rule policy applied to its findings.

    Never mutates. The legacy audit result allowed ``result.findings = ...``;
    the post-split shared-core ``AuditResult`` is a frozen, slotted dataclass
    and raises ``FrozenInstanceError`` on that assignment. Because the shared
    core is installed in deployment and not in a bare source checkout, the
    in-place version passed every local test and returned HTTP 500 from every
    audit on the deployed site -- the same "works from source, breaks
    deployed" shape the MCP server hit after the 8.0.0 split.

    Only the findings change. Score and grade are whatever the auditor
    reported for the whole document, which is the behaviour the in-place
    version had too.
    """
    return with_findings(
        result, filter_findings(result.findings, policy.selected - policy.suppressed)
    )


def get_help_urls_map() -> dict[str, list[dict[str, str]]]:
    """Return a dict mapping every rule_id to its help URL list.

    This is injected as a template context variable so findings tables
    can look up help links by rule_id.
    """
    return {
        rule.rule_id: get_help_urls(rule.rule_id, rule.acb_reference)
        for rule in AUDIT_RULES.values()
    }


# Format display ordering and labels for the suppression panel template.
_FORMAT_ORDER = ["docx", "xlsx", "pptx", "md", "pdf", "epub"]
_FORMAT_LABELS: dict[str, str] = {
    "docx": "Word (.docx)",
    "xlsx": "Excel (.xlsx)",
    "pptx": "PowerPoint (.pptx)",
    "md": "Markdown (.md)",
    "pdf": "PDF",
    "epub": "ePub",
}


def get_rules_by_format() -> dict[str, dict]:
    """Return all audit rules grouped by document format.

    Returns an ordered dict keyed by format string ("docx", etc.) where
    each value is ``{"label": str, "rules": list[dict]}``.  Rules that
    apply to multiple formats appear in every relevant group.  Empty
    groups are included so the template can iterate a stable key order.
    """
    groups: dict[str, dict] = {
        fmt: {"label": _FORMAT_LABELS[fmt], "rules": []}
        for fmt in _FORMAT_ORDER
    }
    for rule in AUDIT_RULES.values():
        rule_dict = _rule_to_dict(rule)
        for fmt_val in rule_dict["formats"]:
            if fmt_val in groups:
                groups[fmt_val]["rules"].append(rule_dict)
    return groups


def build_rule_policy(form) -> "RulePolicy":
    """Build a :class:`RulePolicy` from Flask form data.

    This is the single entry point for both the audit and fix routes.
    It consolidates all rule-selection and suppression logic that was
    previously scattered across audit.py, fix.py, and the old
    ``_build_rule_filter`` helper.

    Backward-compatible: the legacy boolean fields
    ``suppress_link_text``, ``suppress_missing_alt_text``, and
    ``suppress_faux_heading`` are still recognised alongside the new
    ``suppress_rule`` multi-value field.

    Parameters
    ----------
    form:
        A Flask ``ImmutableMultiDict`` (``request.form``) or any mapping
        that supports ``.get()`` and ``.getlist()``.
    """
    from acb_large_print.rule_policy import RulePolicy

    mode = form.get("mode", "full")
    standards_profile = form.get("standards_profile", PROFILE_ACB_2025)

    # ---- Category + profile intersection --------------------------------
    categories = (
        form.getlist("category") if hasattr(form, "getlist") else form.get("category", [])
    )
    if not categories:
        categories = ["acb", "msac"]

    category_rule_ids = get_rule_ids_by_category(*categories)
    profile_rule_ids = get_rule_ids_by_profile(standards_profile)

    # ---- Base rule set from mode ----------------------------------------
    if mode == "quick":
        base = get_rule_ids_by_severity("Critical", "High")
        mode_label = "Quick Audit -- Critical and High only"
    elif mode == "custom":
        custom_ids = (
            set(form.getlist("rule")) if hasattr(form, "getlist") else set(form.get("rule", []))
        )
        base = custom_ids or get_all_rule_ids()
        mode_label = f"Custom Audit -- {len(base)} rules selected"
    else:
        base = get_all_rule_ids()
        mode_label = "Full Audit -- all rules"

    selected = frozenset(base & category_rule_ids & profile_rule_ids)

    # ---- Suppressed rules -----------------------------------------------
    suppressed: set[str] = set()

    # New generic multi-value field
    if hasattr(form, "getlist"):
        suppressed.update(form.getlist("suppress_rule"))

    # Backward-compat: legacy boolean checkboxes
    if form.get("suppress_link_text") == "on":
        suppressed.add("ACB-LINK-TEXT")
    if form.get("suppress_missing_alt_text") == "on":
        suppressed.add("ACB-MISSING-ALT-TEXT")
    if form.get("suppress_faux_heading") == "on":
        suppressed.add("ACB-FAUX-HEADING")

    # Safety: only allow real rule IDs to prevent form injection
    suppressed = {rid for rid in suppressed if rid in AUDIT_RULES}

    return RulePolicy(
        selected=selected,
        suppressed=frozenset(suppressed),
        mode_label=mode_label,
    )


# Type alias so callers can import RulePolicy via this module if desired.
from acb_large_print.rule_policy import RulePolicy  # noqa: E402  (import at bottom OK)
