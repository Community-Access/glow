# Frequently Asked Questions

## Fix and Audit Workflow FAQ

<details class="help-accordion" open markdown="1">
<summary>I turned heading detection off. Why did my score still change?</summary>

Fix Results suppresses **ACB-FAUX-HEADING** when heading detection is disabled, so you are not penalized for a rule you intentionally bypassed.

The results page lists every suppressed rule in a "Suppressed by your settings" note.

</details>

<details class="help-accordion" markdown="1">
<summary>Can I preserve centered titles and headings?</summary>

Yes. On the Fix page, enable **Preserve centered headings** under Heading Alignment Handling.

This keeps centered heading paragraphs unchanged and suppresses heading-specific alignment findings in the fix results.

</details>

<details class="help-accordion" markdown="1">
<summary>Can I suppress raw URL link warnings for print workflows?</summary>

Yes. Use **Quick Rule Exceptions** on the Audit or Fix page and check "I use raw URLs for hard-copy readers."

This suppresses **ACB-LINK-TEXT** in the current run and documents the suppression in results.

</details>

<details class="help-accordion" markdown="1">
<summary>How do decorative image exceptions work?</summary>

Use Word's "Mark as decorative" for non-informational images. The auditor now handles legacy VML `alt=""` as decorative.

If you still need a workflow override, use Quick Rule Exceptions to suppress **ACB-MISSING-ALT-TEXT** for the run.

</details>

<details class="help-accordion" markdown="1">
<summary>Why did my document grow in page count after fix?</summary>

When source body text is below 18pt, normalizing to ACB minimum increases line count. This is expected, especially in long newsletters.

Fix Results now warns when pre-fix body text appears below 18pt so pagination growth is expected.

</details>

<details class="help-accordion" markdown="1">
<summary>What is per-level list indentation (Issue 8B)?</summary>

On the Fix page, under List Indentation, enable **Use per-level list indentation** to set level 1, 2, and 3 indents separately.

This supports multi-level list formatting without flattening all nesting levels to one indent value.

</details>

<details class="help-accordion" markdown="1">
<summary>Can I limit heading review to only certain levels (for example H1-H3)?</summary>

Yes. In Fix, use **Allowed heading levels** to select the subset your workflow permits.

The heading review page only offers those levels in each candidate dropdown, and confirm/apply honors the same subset. Template sample content can use the same preference through Template and Settings defaults.

</details>

<details class="help-accordion" markdown="1">
<summary>Known limitation: soft-return title + author in one heading paragraph</summary>

If a single heading paragraph combines title and byline using Shift+Enter, fixer normalization may unify formatting across runs in that heading.

Recommended workaround: separate title and author into distinct styled paragraphs or review these headings manually after fix.

</details>

<details class="help-accordion" markdown="1">
<summary>Is the AFB style guide the same as a large-print standard?</summary>

No. AFB guidance for JVIB is an academic manuscript submission style (for example, 12pt Calibri and journal-focused formatting), not a large-print production standard.

For large-print production in GLOW, use ACB (default) or APH profiles.

</details>

<details class="help-accordion" markdown="1">
<summary>Which guideline standards does this tool follow?</summary>

GLOW follows ACB by default and includes APH submission profile support for APH-aligned workflows.

AFB JVIB style guidance is referenced for terminology and writing conventions, but it is not a selectable fix/audit mode.

</details>

<details class="help-accordion" markdown="1">
<summary>What is the correct spelling: large print or large-print?</summary>

Use **large print** as a noun ("This document is in large print") and **large-print** as a modifier ("a large-print edition").

</details>

<details class="help-accordion" markdown="1">
<summary>How should I format em-dashes and numbers in running text?</summary>

Use em-dashes with no spaces before or after. In Word, insert an em-dash symbol or use two hyphens with no spaces.

For numbers in prose, spell out one through nine, use numerals for 10 and above, write "percent" instead of "%", and use decades without apostrophes (for example, 1990s).

</details>

See also: [User Guide FAQ section](/guide/#20-frequently-asked-questions).

## Convert FAQ

<details class="help-accordion" markdown="1">
<summary>Can I convert a PowerPoint or Excel file directly to HTML, Word, EPUB, or PDF?</summary>

Yes. As of GLOW 2.7.0, you can upload a PowerPoint (.pptx), Excel (.xlsx, .xls), PDF (.pdf), HTML, CSV, JSON, or XML file and choose any of the Pandoc output directions (accessible web page, Word document, EPUB, accessible PDF). GLOW automatically runs a two-stage process: it extracts the content to Markdown first using MarkItDown, then Pandoc formats the result with full ACB Large Print styles. You do not need to do anything extra -- just upload and choose your output format.

For the cleanest results, well-structured source files work best. Complex layouts, merged table cells, and heavily visual slides may require manual cleanup of the extracted Markdown.

</details>

<details class="help-accordion" markdown="1">
<summary>What is the difference between automatic two-stage conversion and doing it manually?</summary>

Automatic two-stage conversion is the same two-step process (MarkItDown extract → Pandoc format) run back-to-back without you doing anything in between. It is fast and convenient for well-structured source files.

Manual chaining gives you a review step between extraction and formatting:

1. Convert your file **To Markdown** to get the extracted text.
2. Open the Markdown file, review and fix headings, clean up tables, add missing alt text.
3. Convert the improved Markdown to your target format (HTML, Word, EPUB, or PDF).

Manual chaining produces better results when the source file has complex layouts, inconsistent heading structure, or heavy use of visual formatting that does not map cleanly to text.

</details>

<details class="help-accordion" markdown="1">
<summary>Where is the Quick Start option?</summary>

Quick Start is the first tab in the navigation bar at the top of every GLOW page. Click it, upload any supported file, and GLOW shows you every available action for that file type -- no need to know in advance which tool to use.

</details>
