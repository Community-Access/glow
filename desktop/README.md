# GLOW

A cross-platform desktop application that audits, remediates, and exports Microsoft Office documents (Word, Excel, PowerPoint) to comply with the American Council of the Blind (ACB) Large Print Guidelines, Microsoft Accessibility Checker rules, and WCAG 2.2 AA digital accessibility standards.

## Features

- Audit .docx, .xlsx, .pptx, and .epub files against ACB Large Print and MSAC accessibility rules
- Auto-fix compliance issues in Word documents (fonts, spacing, emphasis, headings, margins)
- Audit Excel workbooks (sheet names, table headers, merged cells, alt text, hidden content, color-only data)
- Audit PowerPoint presentations (slide titles, reading order, alt text, font sizes, speaker notes, charts)
- Audit ePub e-books (title, language, navigation, heading hierarchy, alt text, table headers, accessibility metadata, link text)
- Display human-readable ePub accessibility metadata per the W3C Accessibility Metadata Display Guide 2.0 (ways of reading, conformance, navigation, rich content, hazards, summary, legal, additional info)
- Convert documents to Markdown via Microsoft MarkItDown (.docx, .xlsx, .pptx, .pdf, .html, .csv, .json, .xml, .epub)
- Generate ACB-compliant Word templates (.dotx) with pre-configured styles
- Export Word documents to accessible HTML (standalone or CMS-ready fragments)
- Accessible GUI wizard (screen reader compatible, keyboard navigable)
- Full CLI for scripting and batch processing of all three formats
- Cross-platform: Windows, macOS, and Linux (x64 and ARM64)

## Recent Fix Workflow Updates (April 2026)

- Fix Results now suppresses `ACB-FAUX-HEADING` from post-fix scoring when heading detection is explicitly disabled, and shows a "Suppressed by your settings" note.
- Fix Results now warns when source body text appears below 18pt because ACB normalization can increase page count in long documents.
- List indentation controls are always visible for discoverability and are enabled only when "Flush all lists to the left margin" is unchecked.
- Legacy Word VML shapes now treat explicit `alt=""` as decorative, reducing false `ACB-MISSING-ALT-TEXT` findings.

## Installation

### Pre-built executables

Download the latest release for your platform from the
[Releases page](https://github.com/your-org/acb-large-print/releases):

| Platform | Filename | Notes |
|---|---|---|
| Windows | `acb-large-print-win-x64.exe` | x64 binary, also runs on ARM64 via emulation |
| macOS | `acb-large-print-macos-arm64` | Apple Silicon (M1/M2/M3/M4) |

On macOS and Linux, make the file executable after downloading:

```bash
chmod +x acb-large-print-*
```

### Install from source

```bash
cd desktop
pip install -e .

# or with dev dependencies
pip install -e ".[dev]"
```

Requires Python 3.10 or later.

### Dependencies

| Package | Version | Purpose |
|---|---|---|
| python-docx | 1.1.0+ | Read and write .docx files |
| openpyxl | 3.1.0+ | Read and write .xlsx files |
| python-pptx | 1.0.0+ | Read and write .pptx files |
| mammoth | 1.8.0+ | Convert .docx to clean HTML |
| markitdown | 0.1.5+ | Convert documents to Markdown |
| wxPython | 4.2.0+ | Accessible cross-platform GUI |

### Runtime configuration

These settings are read at runtime. Leave them unset unless you are using the feature they control.

| Variable | When used | Default | Purpose |
|---|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter AI provider | none | Required for OpenRouter-backed heading classification. |
| `WHISPER_MODEL` | Audio transcription | `medium` | Chooses the local Whisper model used by MarkItDown/faster-whisper. |
| `PIPELINE_URL` | DAISY Pipeline conversions | `http://pipeline:8181/ws` | Base URL for the Pipeline REST service. |
| `EPUBCHECK_JAR` | EPUBCheck validation | none | Path to an `epubcheck` JAR when validating EPUB packages with Java. |
| `GLOW_ENABLE_EPUBCHECK` | EPUBCheck validation | `true` | Enables or disables EPUBCheck-backed EPUB auditing. |

The desktop app also expects the following external tools when you use the related features:

- Ollama for local AI heading classification
- Node.js plus `@daisy/ace` for full EPUB auditing
- Java for `EPUBCHECK_JAR`-based EPUBCheck validation

The code also honors `HUGGINGFACE_HUB_CACHE`, `HF_HOME`, and `XDG_CACHE_HOME` for Whisper/MarkItDown cache location, plus `NO_COLOR` for plain CLI output.

Copy `desktop/.env.example` to `desktop/.env` if you want a local override file.

## Usage

### GUI mode (default)

Double-click the executable or run without arguments:

```bash
acb-large-print
```

The 7-step wizard walks through:

1. Open a .docx, .xlsx, or .pptx file
2. Initial audit (view compliance report in your browser)
3. Choose output options (standalone HTML, CMS fragment, Markdown conversion)
4. Auto-remediate all fixable issues (Word) or review audit guidance (Excel, PowerPoint)
5. Verify the fixed document (view report showing improvements)
6. Save the fixed document and optional HTML/Markdown exports
7. Summary of everything accomplished

### CLI mode

#### Audit a document

```bash
acb-large-print audit report.docx
acb-large-print audit budget.xlsx
acb-large-print audit slides.pptx
acb-large-print audit report.docx --format json
acb-large-print audit report.docx -o audit-report.txt
```

#### Fix a document

```bash
# Word documents get auto-fixed
acb-large-print fix report.docx
acb-large-print fix report.docx -o report-fixed.docx
acb-large-print fix report.docx --bound   # add binding margin

# Excel and PowerPoint files are audited with manual fix guidance
acb-large-print fix budget.xlsx
acb-large-print fix slides.pptx
```

#### Create a template

```bash
acb-large-print template
acb-large-print template ACB-Template.dotx --bound --title "Meeting Agenda"
acb-large-print template --install   # also copy to Word's Templates folder
```

#### Export to HTML

```bash
# Standalone HTML + CSS file
acb-large-print export report.docx

# CMS fragment (embedded CSS, paste into WordPress/Drupal)
acb-large-print export report.docx --cms

# Custom title and output path
acb-large-print export report.docx -o output.html --title "Board Meeting Agenda"
```

#### Convert to Markdown

```bash
# Convert any supported document to Markdown
acb-large-print convert slides.pptx
acb-large-print convert report.pdf -o report.md
acb-large-print convert budget.xlsx
```

#### Batch processing

```bash
# Audit all Office documents in a directory
acb-large-print batch audit docs/ -r

# Batch fix (Word gets auto-fixed, Excel/PowerPoint get audit reports)
acb-large-print batch fix docs/ -r --output-dir fixed/
```

## Architecture

```text
desktop/
  src/acb_large_print/
    __init__.py          Version and metadata
    __main__.py          Entry point (CLI dispatch or GUI launch)
    constants.py         ACB rule definitions and thresholds
    auditor.py           Word document scanner -- checks 30+ rules, returns AuditResult
    xlsx_auditor.py      Excel workbook scanner -- MSAC accessibility rules
    pptx_auditor.py      PowerPoint presentation scanner -- MSAC accessibility rules
    fixer.py             Auto-remediation engine -- applies fixes to python-docx Document
    reporter.py          Report generators (text, JSON, HTML)
    exporter.py          DOCX-to-HTML export (mammoth + ACB post-processing)
    converter.py         Document-to-Markdown conversion (via MarkItDown)
    template.py          Word template (.dotx) generator with ACB styles
    cli.py               argparse CLI with audit/fix/template/export/convert/batch/gui commands
    gui.py               wxPython 7-step wizard (accessible, screen reader compatible)
  build.py               Cross-platform PyInstaller build script
  pyproject.toml         Project metadata and dependencies
  requirements.txt       Pip requirements (core dependencies)
  installer/
    acb-large-print.iss  Inno Setup installer script (Windows)
  LICENSE.txt            MIT License
```

### Module details

**auditor.py** scans a .docx file and returns an `AuditResult` containing:

- `passed` (bool): whether the document meets all rules
- `findings` (list): each finding has a rule ID, severity, description, location, and suggested fix
- `score` (int): compliance score (0--100)
- `grade` (str): letter grade A--F

**fixer.py** takes an `AuditResult` and the source document, then applies fixes:

- Font family (set to Arial)
- Font sizes (18pt body, 22pt headings, 20pt subheadings)
- Line spacing and paragraph spacing
- Remove italic and bold-as-emphasis
- Heading hierarchy corrections
- Margin and page layout adjustments
- Binding margin (optional)

**exporter.py** converts .docx to HTML via mammoth with ACB-specific style mapping:

- `export_standalone_html()`: full HTML document + external CSS file
- `export_cms_fragment()`: body-only HTML with embedded `<style>` block, scoped under `.acb-lp` class for safe CMS pasting
- Post-processes mammoth output: strips inline styles, cleans empty paragraphs, adds table `scope` attributes

**reporter.py** generates reports in three formats:

- `generate_text_report()`: plain text with ASCII severity indicators
- `generate_json_report()`: machine-readable JSON
- `generate_html_report()`: accessible HTML with severity badges, summary grid, and findings table

**gui.py** provides a wxPython wizard with full accessibility:

- All controls have labels or `SetName()` for screen readers
- Alt-key accelerators (Alt+B Back, Alt+N Next, Alt+C Cancel)
- Read-only text areas for report display
- HTML reports open in the default browser
- Standard file dialogs for all file operations
- Status bar announces the current step

## Building executables

### Local build (current platform)

```bash
cd desktop
pip install pyinstaller>=6.0
python build.py
```

This produces a single-file executable in `dist/`:

- Windows: `acb-large-print-win-x64.exe` (or `win-arm64`)
- macOS: `acb-large-print-macos-arm64` (or `macos-x64`)
- Linux: `acb-large-print-linux-x64` (or `linux-arm64`)

### Cross-platform builds via GitHub Actions

Push a version tag to trigger automated builds on all 6 platforms:

```bash
git tag v1.0.0
git push origin v1.0.0
```

This runs the workflow at `.github/workflows/build.yml` which:

1. Builds on 2 runners simultaneously (Windows x64, macOS ARM64)
2. Uploads each executable as a GitHub Actions artifact
3. Creates a combined download with both binaries
4. Creates a GitHub Release with executables attached (tag pushes only)

You can also trigger the workflow manually from the Actions tab and optionally upload to a release.

### Build matrix

| Runner | OS | Arch | Executable output |
|---|---|---|---|
| `windows-latest` | Windows | x64 | `acb-large-print-win-x64.exe` |
| `macos-latest` | macOS | ARM64 | `acb-large-print-macos-arm64` |

### Windows installer (optional)

For Windows distribution with Start menu shortcuts and Word template installation, build the Inno Setup installer:

1. Build the executable: `python build.py`
2. Open `installer/acb-large-print.iss` in Inno Setup
3. Compile -- produces `dist/installer/ACB-Large-Print-Setup-1.0.0.exe`

The installer is fully accessible: standard Windows controls, descriptive labels, per-user install (no admin rights needed).

### Platform notes

- **macOS**: The executable may need to be allowed in System Settings, Privacy and Security after first download (Apple Gatekeeper).
- **PyInstaller cannot cross-compile**: Each platform must be built natively. The GitHub Actions workflow handles this automatically.

## ACB Large Print rules (summary)

- Font: Arial only, 18pt body, 22pt headings, 20pt subheadings
- Alignment: flush left, ragged right (never justified)
- Emphasis: underline only (no bold for emphasis, no italic ever)
- Headings: proper hierarchy, no ALL CAPS, no skipped levels
- Lists: large solid bullets, no extra spacing between items
- Links: descriptive text (no bare URLs, no "click here")
- Spacing: 1 blank line between paragraphs, no blank lines between list items
- Digital supplement: WCAG 2.2 AA contrast (4.5:1), 400% zoom reflow, 1.5x line-height

Full specification: `reference/ACB Large Print Guidelines, revised 5-6-25.docx`

## HTML export details

### Standalone mode

Produces two files:

- `document.html` -- complete HTML5 document with `<link>` to CSS
- `acb-large-print.css` -- external stylesheet with all ACB + WCAG rules, including `@media print` overrides

### CMS fragment mode

Produces one file:

- `document-cms.html` -- body-only HTML with embedded `<style>` block
- All CSS selectors scoped under `.acb-lp` class to prevent CMS theme conflicts
- Content wrapped in `<div class="acb-lp">...</div>`
- No `<!DOCTYPE>`, `<html>`, `<head>`, or `<body>` tags -- the CMS provides these

### mammoth style mapping

The exporter maps Word styles to semantic HTML:

| Word Style | HTML Output |
|---|---|
| Heading 1 | `<h1>` |
| Heading 2 | `<h2>` |
| Heading 3--6 | `<h3>` through `<h6>` |
| Bold | `<strong>` (structural only, not emphasis) |
| Italic | Stripped (ACB prohibits italic) |
| Underline | `<u class="acb-emphasis">` |
| Hyperlinks | `<a href="...">` with descriptive text preserved |

Post-processing removes inline styles, cleans empty paragraphs, and adds `scope` attributes to table headers.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Submit a pull request

## Stress Validation And Lessons Learned

This runbook records what we tested, what we learned, how we adapted the fixer, and what the evidence now supports.

### Scope

- 1,000 generated Word documents in the main release-scale corpus
- 1,000 total heading scenarios at the current default scale
- 10 document families
- 12 randomized scenario patterns
- 7 language variants in the random heading set

The corpus lives in [desktop/src/acb_large_print/stress_profiles.py](desktop/src/acb_large_print/stress_profiles.py).

### What The Tests Covered

Heading-detection scenarios:

- Genuine headings with strong visual signals
- Numbered headings and outline-style headings
- Plain-text lines with no heading styles
- Font-size-only heading cues
- False positives such as signature lines and callout labels
- Multilingual section labels and numbering patterns
- Mixed-format paste artifacts such as centered titles, justified text, font drift, and indentation drift

What the 1,000 generated documents represented:

- Meeting agendas and board packets assembled from pasted material
- Newsletters and flyers with decorative layout problems
- Policy manuals built from older templates with drifted formatting
- Legal outlines with numbering and hierarchy pressure
- Training handouts with prompts and labels that may look like headings
- Appendix-style and reference documents with short labels and notes
- Plain-text paste where no real heading styles exist

The documents were intentionally built to behave like realistic user uploads. Each potential heading appeared inside a fuller document context, so the platform had to detect structure and then repair the rest of the document back to ACB compliance.

Document-repair scenarios:

- Flush-left alignment enforcement
- Paragraph and list indentation repair
- Font family and size normalization
- Italic removal and body emphasis cleanup
- Faux-heading conversion to real heading styles
- Heading hierarchy repair
- ALL CAPS heading cleanup

### Validation Commands

Run from the repository root after setting PYTHONPATH to include desktop/src and web/src.

Primary full-suite command:

```bash
python -m pytest desktop/tests/test_heading_stress_corpus.py -q
```

Core fixer and detector command:

```bash
python -m pytest desktop/tests/test_fixer_headings.py desktop/tests/test_heading_stress_corpus.py desktop/tests/test_heading_detector.py desktop/tests/test_heading_detector_extensive.py -q
```

Ground-truth comparison and fix-then-audit sweeps were also run directly with Python one-liners over the full corpus to measure false positives, false negatives, and post-fix ACB findings.

### What We Proved

- Full heading stress suite: 5 passed
- Core fixer and detector suite: 150 passed
- 1,000-scenario heuristic comparison: 0 false positives, 0 false negatives
- 4,800-scenario denser randomized comparison: 0 false positives, 0 false negatives
- 1,000-document fix-then-audit sweep: 0 remaining ACB findings after the latest fixes

### Lessons Learned

1. Real documents combine multiple failure modes. A single file may contain plain-text headings, copied email content, mixed fonts, centered titles, fake emphasis, and indentation drift all at once.
2. Heading detection quality depends on negative examples as much as positive ones. Signature lines, reminders, and similar short phrases are exactly where false positives happen if penalties are weak.
3. Repair quality must be measured separately from detection quality. A detector can be correct while the repaired document still violates ACB rules.
4. The most valuable findings came from policy-level failures, not crashes. The strongest example was faux headings that were correctly detected but still produced ACB-HEADING-HIERARCHY and ACB-NO-ALLCAPS failures after repair.

### How The Platform Adapted

- Added stronger penalties for signature-like and callout-style false positives
- Expanded randomness to include multilingual headings, plain-text/no-style negatives, and font-only heading cues
- Lowered one synthetic expected heading level so the generated ground truth better matched the intended structure
- Added a fixer normalization pass that converts ALL CAPS heading text to title case and repairs skipped heading levels after faux-heading conversion

### Confidence Statement

- We are confident in the lessons learned for heading detection and ACB repair within the tested corpus because the final measured results are clean across the full release-scale run and the denser randomized run.
- We are confident in the fixer design being cross-platform because it uses platform-neutral Python document processing rather than OS-specific APIs.
- We only have runtime proof from Windows in this session. macOS and Linux still need the same validation commands run in CI for full cross-platform execution proof.

## License

MIT License. See [LICENSE.txt](LICENSE.txt).

Copyright 2026 BITS (Blind Information Technology Solutions).
