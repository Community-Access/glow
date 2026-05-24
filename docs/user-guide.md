# GLOW -- User Guide

GLOW (Guided Layout and Output Workflow) helps you produce documents that people with low vision can read. It audits, fixes, converts, and templates Office documents, Markdown, PDFs, and ePubs against the ACB Large Print Guidelines and WCAG 2.2 Level AA.

New to GLOW? Start at [Quick Start](#1-quick-start). Already familiar? Jump straight to the section you need.

If AI is part of your setup, skip ahead to [What’s New in GLOW 6.0.0](#whats-new-in-glow-6.0.0) and [AI Features at a Glance](#ai-features-at-a-glance) for the short version of what GLOW can do when AI is on, and what stays hidden when it is not.

---

## What’s New in GLOW 6.0.0

GLOW 6.0.0 is the open source release that makes the project easier to join, easier to explain, and easier to run with your own AI account when you want AI help.

### Highlights in 6.0.0

1. **Open source contribution process** -- The web site, release notes, and announcement files now explain how to fork the repo, open a branch, submit a pull request, and work through review under branch protection. The project is ready for community contributions, not just downloads.
2. **Feedback-to-issue automation** -- Feedback submissions can now collect a name and email for follow-up and sync directly into GitHub Issues when a token is configured.
3. **Personal AI provider support with AI Playground (Beta)** -- Users can connect their own Ollama Cloud, OpenRouter, OpenAI, or Google Gemini API key and enable AI features. The playground is an experimental chat surface for testing compatible models without document context. You can explore model behavior, stream responses token-by-token, regenerate or stop responses, copy/export outputs, switch models mid-conversation, and navigate questions and answers directly using your keyboard or screen reader. Long-running replies now announce both in-progress and completed states to screen reader users. All conversation history is temporary and session-scoped.
4. **Per-feature provider/model selection** -- Choose different compatible provider/model pairs for heading detection, MarkItDown support, the playground, alt-text suggestions, and Whisperer from a unified AI Features settings page. The interface filters out incompatible choices so vision and audio workflows only expose models that can support them.
5. **Alt-Text Helper across visual formats** -- GLOW can now draft alternative text for standalone image files and visual content from Word, PowerPoint, Excel, PDF, and EPUB uploads from one shared helper surface.
6. **Visible AI usage meter and cost preview** -- The sidebar now shows a live AI usage summary, while Document Chat and AI Playground can preview rough token/cost estimates before you send a request.
7. **Clearer AI guidance** -- The About page and this user guide now explain what AI can do in short form even when AI is not yet enabled, so users can understand the capability before they turn it on.

### What stays simple

- If you do not enable AI, every non-AI workflow in GLOW still works exactly as before.
- If you do enable AI, the feature toggles keep the initial release limited to the most dependable text workflows.
- Document Chat remains available as a future step, not the default starting point.

## AI Features at a Glance

If you are deciding whether to turn AI on, here is the short version:

- **Heading detection** helps turn bold, large text into actual semantic headings. This runs automatically when Fix is available and runs in document workflows.

- **MarkItDown + AI support** makes text extraction smarter and document cleanup faster. When you audit, fix, or convert a document, the AI-enhanced extraction understands context and structure, not just layout. The result is cleaner documents with fewer artifacts and better heading relationships. This is enabled by default when you connect a compatible personal provider key.

- **Document Chat** remains a separate feature gate and is disabled by default in the personal-provider-first setup.

- **AI Playground (Beta)** is a standalone chat surface where you can explore compatible personal-provider models, ask questions, and test model behavior before using AI in real accessibility workflows. It includes streaming responses, regenerate/stop controls, prompt templates, a quota status banner, Markdown export, and delayed screen reader announcements for in-progress and completed long-running replies.
- **Alt-Text Helper** drafts editable alternative text for images, charts, slide visuals, rendered PDF pages, and other extracted visual items. It uses the alt-text model binding from AI Features and appends file-specific context automatically.
- **PII guardrails for AI requests** are enabled by default. Before AI calls, GLOW can detect and redact sensitive text (for example emails, phone numbers, and account-style identifiers) in chat prompts and alt-text prompt context.

- **Usage tracking** shows session-level request counts so you can see what you used while you were in GLOW.
- **Cost preview and rolling session limits** show rough request cost before send and can enforce an admin-configured per-session AI request window with a reset countdown.

- **Whisperer** is separate and only appears when an audio-transcription-capable provider path is active.

If AI is disabled, GLOW hides the AI-specific entry points and keeps the rest of the app focused on its document workflows.

---

## In This Guide

1. [Quick Start](#1-quick-start)
2. [How to Audit a Document](#2-how-to-audit-a-document)
3. [How to Fix a Document](#3-how-to-fix-a-document)
4. [How to Create a Template](#4-how-to-create-a-template)
5. [CMS Fragment (formerly Export)](#5-cms-fragment-formerly-export)
6. [How to Convert Between Formats](#6-how-to-convert-between-formats)
7. [Braille Studio: Text-to-Braille Translation](#7-braille-studio-text-to-braille-translation)
8. [Speech Studio: Document-to-Audio](#8-speech-studio-document-to-audio)
   - [PageFlow: Read Articles and Narrate Them](#pageflow-read-articles-and-narrate-them)
9. [BITS Whisperer: Transcribe Audio](#9-bits-whisperer-transcribe-audio)
10. [AI Playground (Beta): Explore Ollama Models](#10-ai-playground-beta-explore-ollama-models)
11. [MarkItDown + AI Integration: Smarter Text Extraction](#11-markitdown--ai-integration-smarter-text-extraction)
12. [Document Chat](#12-document-chat)
13. [Settings](#13-settings)
14. [Understanding Your Results](#14-understanding-your-results)
15. [Common Issues and How to Fix Them](#15-common-issues-and-how-to-fix-them)
16. [Tips by Document Format](#16-tips-by-document-format)
17. [Recommended Workflows](#17-recommended-workflows)
18. [DAISY Accessibility Tools](#18-daisy-accessibility-tools)
19. [Keyboard and Screen Reader Tips](#19-keyboard-and-screen-reader-tips)
20. [Frequently Asked Questions](#20-frequently-asked-questions)
20. [Website Accessibility Scans (Site Audit)](#20-website-accessibility-scans-site-audit)
21. [Getting Help](#21-getting-help)

---

## What's New in GLOW 5.0.0

GLOW 5.0.0 is a full UX redesign release. The horizontal tab bar that previously ran across every page has been replaced with a goal-oriented left sidebar navigation. All tools remain the same -- only the way you navigate to them has changed.

### Highlights in 5.0.0

1. **Goal-oriented sidebar navigation** -- The left sidebar organises every tool into five mission groups so you can navigate by what you want to accomplish, not by tool name.
2. **Five navigation groups:**
   - **Assess** -- Document Audit and Site Audit for finding accessibility barriers
   - **Fix and Build** -- Fix Document and Build Template for correcting and starting fresh
   - **Transform** -- Convert Format and Braille Studio for format and medium changes
   - **Listen and Speak** -- Speech Studio, PageFlow, and Whisperer for read-aloud and audio workflows
   - **Explore and Learn** -- Document Chat, Magic Lab, Guidelines, User Guide, FAQ, and Settings
3. **Responsive sidebar** -- On small screens the sidebar collapses to a hamburger menu. Clicking the hamburger slides the sidebar over the page with a focus trap and Escape-key dismissal.
4. **Correct ARIA pattern** -- All navigation links now use `aria-current="page"` (the correct ARIA 1.1 attribute for navigation). The prior `role="tab"` misuse has been removed.
5. **Mission Hub home page** -- The home page now shows five goal-oriented mission cards with feature-flag-aware tool links, replacing the previous Quick Start workflow steps and card grid.
6. **Version bumped to 5.0.0** -- Web app, desktop CLI, and Office add-in all reflect version 5.0.0.

---

## What's New in GLOW 4.0.0

GLOW 4.0.0 is a confidence release focused on stability, conversion fidelity,
and public-documentation accuracy. It keeps the full 3.1.0 feature surface and
adds targeted hardening in places that matter in real operations.

### Highlights in 4.0.0

1. **Safer Re-Audit from Fix Results** - The "Re-Audit Fixed Document" action
   now submits through a CSRF-protected POST flow, preserving token context,
   standards profile, and prior finding metadata safely.
2. **OpenDocument conversion resilience** - Convert now supports more
   OpenDocument inputs safely, including `.fodt` directly and optional
   LibreOffice pre-conversion for spreadsheet and presentation variants before
   the existing conversion pipeline.
3. **Better PDF table preservation in downstream exports** - Table structures
   detected in PDFs are now preserved more reliably when exporting to
   Pandoc-backed formats such as Word, HTML, and EPUB.
4. **Release-documentation synchronization** - Changelog, PRD, user guide,
   announcement pointers, and combined announcement artifacts are now aligned to
   the same release baseline so public messaging matches shipped behavior.
5. **Site Audit web scanner** - New `/site-audit` workflow to scan websites
   with URL/sitemap input, optional crawling, and downloadable scan artifacts.

### What remains true from 3.1.0

- Braille Studio, Speech Studio, Status page, roadmap-core feature flags, and
  WCAG self-audit CI coverage remain part of the active platform.
- The single-upload workflow (Quick Start to Audit/Fix/Convert and onward) is
  unchanged and remains central to day-to-day use.

---

## What's New in GLOW 3.1.0

GLOW 3.1.0 ships 11 new features: a full Braille Studio, Speech Studio document preparation via Pandoc, a Server Status diagnostic page, a comprehensive axe-core WCAG 2.2 AA CI audit of GLOW itself, and a set of operational hardening improvements for speech, braille, Docker, and CI.

### Roadmap core feature pack implemented in this release

This release also implements the 11 roadmap additions requested in one
feature-gated pack. If a feature is disabled by your administrator, its route
or UI surface may be hidden.

| Roadmap Item | Where You Use It | Flag |
|-------------|------------------|------|
| 1.5 Back-translation quality scoring | Braille Studio result panel | `GLOW_ENABLE_BRAILLE_BACK_TRANSLATION_SCORE` |
| 2.5 Pronunciation dictionary management | Speech pronunciation tools + Speech synthesis pre-processing | `GLOW_ENABLE_SPEECH_PRONUNCIATION_DICTIONARY` |
| 2.6 Real-time streaming preview | `POST /speech/stream` (API) | `GLOW_ENABLE_SPEECH_STREAM` |
| 3.3 Table accessibility advisor | `POST /magic/table-advisor` or core accessibility tools form | `GLOW_ENABLE_TABLE_ADVISOR` |
| 3.4 Reading order detection (PDF) | `POST /magic/reading-order` or core accessibility tools form | `GLOW_ENABLE_READING_ORDER_DETECTION` |
| 3.5 OCR for scanned PDFs | `POST /magic/ocr` or core accessibility tools form | `GLOW_ENABLE_PDF_OCR` |
| 3.6 Document compare and change tracking | `POST /magic/compare` or core accessibility tools form | `GLOW_ENABLE_DOCUMENT_COMPARE` |
| 4.3 OpenDocument Text export | Convert direction `to-odt` | `GLOW_ENABLE_CONVERT_TO_ODT` |
| 7.3 Cognitive profile mode | Settings toggle (Plain & Simple mode) | `GLOW_ENABLE_COGNITIVE_PROFILE` |
| 7.4 Forced-colors support | Automatic high-contrast CSS behavior | `GLOW_ENABLE_FORCED_COLORS_MODE` |
| 9.1 Public rule contribution portal | Rule proposal workflow | `GLOW_ENABLE_RULE_CONTRIBUTIONS` |

### Core accessibility intelligence tools

GLOW includes a dedicated accessibility intelligence surface in the core product.
It provides interactive forms for table analysis, PDF reading-order
inspection, scanned-PDF OCR extraction, document comparison, pronunciation
dictionary management, and rule proposal submission.

The same capabilities are also available as JSON endpoints for integration
workflows.

### Deployment and admin requirements for this pack

- `pandoc` is required for ODT conversion and Speech document rendering.
- Braille capabilities require `python3-louis` plus `liblouis-*` packages.
- OCR requires Tesseract + `pytesseract` + Pillow; when missing, OCR features
   return a clear unavailable message instead of failing silently.
- Feature flags can be toggled in the Admin flags page for controlled rollout.

### GitHub integration behavior

- Accessibility findings from CI are uploaded to GitHub Code Scanning as SARIF.
- Rule contribution submissions are currently stored locally in GLOW (SQLite)
   for review; automatic sync to GitHub Issues/PRs is planned but not active
   in v3.1.0.

### Braille Studio: translate to and from braille

A new dedicated tool at **/braille/** translates English text to braille and braille back to English, using the same liblouis engine trusted by screen readers worldwide.

**Supported table codes:**

| Code | Standard |
|------|---------|
| UEB Grade 1 | Unified English Braille, uncontracted (current BANA standard) |
| UEB Grade 2 | Unified English Braille, contracted (current BANA standard) |
| EBAE Grade 1 | English Braille American Edition, uncontracted (legacy) |
| EBAE Grade 2 | English Braille American Edition, contracted (legacy) |
| Computer Braille | BANA Computer Braille Code, 8-dot (code and terminal content) |

**Output formats:**

- **Unicode Braille** (U+2800--U+28FF) -- paste directly into documents, emails, or websites
- **BRF (ASCII)** -- Braille Ready Format, BANA-standard 40 cells per line, optional embosser pagination with form feeds; download as `.brf`

**Back-translation:** Paste or upload a `.brl` or `.brf` file and get back readable English text. Useful for verifying embosser output or proofreading contracted braille.

**How to reach it:** Select **Braille Studio** under the **Transform** group in the left sidebar. Braille Studio can be enabled or disabled via the `GLOW_ENABLE_BRAILLE` feature flag (default: enabled). When liblouis is not installed, the page explains the dependency clearly rather than showing a broken tool.

### Speech Studio: document narration via Pandoc

When you upload a document to Speech Studio, GLOW now extracts the text using Pandoc before synthesis. This applies to every non-plain-text format: `.md`, `.rst`, `.docx`, `.pptx`, `.xlsx`, `.pdf`, `.epub`, and others. The result is consistent, clean narration regardless of the original format. Plain `.txt` files bypass Pandoc and work on servers where Pandoc is unavailable.

**What you see in the UI:** The narration flow now uses an explicit two-stage design:

1. Upload your document or type your text.
2. Click **Next: Prepare text and estimate** -- GLOW extracts the text, measures it, and shows an estimated narration time.
3. **Preview first sentences** or **Download full document audio** -- these controls appear only after preparation succeeds.

If preparation fails (for example, Pandoc is not installed on this server), an error message scrolls into view explaining the issue.

### Server Status page

A new **/status** page gives operators and administrators a human-readable view of everything the `/health` endpoint reports:

- Service probes (speech engine, braille library)
- Service readiness (speech, braille)
- Feature flag summary
- Full feature flag list with current values
- Raw JSON output for automated monitoring

The Status page is accessible without completing the consent flow, so it works in automated health checks, uptime monitors, and Docker orchestration probes.

### GLOW now audits itself with axe-core on every CI run

Every CI build now runs an `@axe-core/playwright` audit of GLOW's own interface at WCAG 2.2 AA level. All 17 public routes are audited:

The original 5 (home, audit, fix, convert, template) plus Speech Studio, Braille Studio, Settings, Guidelines, User Guide, About, Changelog, FAQ, Rules Reference, Feedback, Privacy Policy, and Status.

Four interactive states are also tested: help accordions open, service-unavailable banners, dark mode (`prefers-color-scheme: dark`), and mobile viewport (375 x 812 px).

Critical and serious violations fail the CI build immediately with selector-level diagnostic output. Moderate and minor violations appear as advisory warnings. Results feed the existing SARIF upload to GitHub Code Scanning, so findings are visible in the repository Security tab.

### New feature flags for speech and braille export/conversion

Four granular feature flags let operators control which speech and braille endpoints are active:

| Flag | Controls | Default |
|------|---------|---------|
| `GLOW_ENABLE_CONVERT_TO_SPEECH` | Text extraction and narration preparation endpoints | Enabled |
| `GLOW_ENABLE_EXPORT_SPEECH` | Audio file download endpoints | Enabled |
| `GLOW_ENABLE_CONVERT_TO_BRAILLE` | Braille translation endpoint | Enabled |
| `GLOW_ENABLE_EXPORT_BRAILLE` | Braille result download endpoints | Enabled |

All four are visible and toggleable in the Admin feature flags panel.

---

## 1. Quick Start


If you have never used GLOW before -- or you are not sure which tool to reach for -- this section will get you from upload to result in under five minutes, and give you the vocabulary to use the rest of the guide.

### The scenario

You have a document. Maybe a board meeting agenda, a newsletter, a training handout, a policy memo, or a recording of a conference call. You need it to be readable by people with low vision and compatible with screen readers. You are not sure where to begin.

That is exactly what Quick Start is for.

### Step 1: Go to Quick Start

Click **Quick Start** in the top section of the left sidebar navigation on any GLOW page. You will land on a single upload form.

### Step 2: Upload anything

Quick Start accepts every format GLOW supports:

| Format | Extensions |
|--------|-----------|
| Word | .docx |
| Excel | .xlsx |
| PowerPoint | .pptx |
| PDF | .pdf |
| Markdown | .md |
| ePub | .epub |
| Image | .jpg .jpeg .png .gif .webp .bmp .tiff |
| Audio | .mp3 .wav .m4a .ogg .flac .aac .opus |

You do not need to know the format in advance. GLOW detects it and shows you what is possible.

### Step 3: Choose what you want to do

After upload, GLOW shows an action chooser. Every available action for your file type appears as a card. Actions that do not apply to your format are hidden -- you will not see broken or confusing options.

**What each action does:**

**Audit** -- Checks your document against ACB Large Print Guidelines and WCAG 2.2 rules. Returns a scored report with every finding, its severity, and what to do about it. Available for all document formats.

**Fix** -- Automatically corrects every formatting problem it can find in Word and Markdown documents: fonts, sizes, spacing, emphasis, alignment. Returns a corrected file. You keep your original. Available for Word and Markdown only.

**Convert** -- Transforms your document into a different format. Upload a PowerPoint, Excel, PDF, Word, or Markdown file and get back accessible HTML, a Word document, an EPUB, a PDF, or plain Markdown. PowerPoint, Excel, and PDF files use smart two-stage extraction: GLOW pulls the text into Markdown first, then Pandoc applies full ACB Large Print formatting. This is handled automatically -- you just choose your output format.

**Speech audio (from Convert)** -- Convert also includes a Speech direction that hands your uploaded file to Speech Studio without re-uploading. Use it when you want to preview voice output and download narration audio for the same source file.

**Export** -- Converts a Word document to a CMS Fragment (a scoped HTML snippet for WordPress, Drupal, or any CMS). The Export tab was merged into Convert in v2.7.0. Use **Convert &gt; CMS Fragment** to produce scoped HTML. Standalone HTML output is also available in Convert. See [Section 5](#5-cms-fragment-formerly-export) and [Section 6](#6-how-to-convert-between-formats).

**Template** -- Generates a Word template (.dotx) with all ACB styles pre-configured. Open it in Word and every document you create from it inherits compliant formatting from the first keystroke.

**BITS Whisperer** -- Transcribes an audio file to Markdown or Word. GLOW may normalize some audio formats locally, then send the file to the Whisper API for transcription. Temporary files are cleaned up after processing.

### Step 4: Follow the form

Each action has its own form with step-by-step fields. Every field has a label and a description. If you are not sure what an option means, expand the help section below it.

### What to do when you are done

After your first audit, you know what is wrong. After your first fix, most formatting problems are gone. A second audit on the fixed file shows what remains. Remaining items need manual attention -- the report tells you exactly what to do for each one.

Most users settle into a rhythm: **Audit, Fix, re-Audit, manual cleanup, publish.** The sections below explain each step in detail.

---

### Real-world scenarios

The following scenarios show which GLOW tools to reach for depending on what you are starting with.

#### "I have a Word document from a colleague and I need to check it for accessibility."

Go to **Audit**. Upload the .docx. Run Full Audit. Read the report. If the score is below 80 and you see Critical or High findings, go to Fix next.

#### "I have a Word document that I need to make accessible quickly."

Go to **Fix**. Upload the .docx. Run Full Fix. Download the corrected file. Re-audit to confirm.

#### "I have meeting minutes I need to post on our website."

If they are in Word: Fix first, then use **Convert &gt; Accessible web page (HTML)** or **Convert &gt; CMS Fragment** for WordPress/Drupal.

If they are in Markdown: Audit first, then Convert to accessible web page (HTML via Pandoc).

#### "Someone sent me a PowerPoint and I need an accessibility report."

Go to **Audit**. Upload the .pptx. The report shows every slide with issues, what is wrong on each slide, and step-by-step instructions for fixing it manually in PowerPoint.

Go to **Convert**. Upload the .xlsx and choose **Accessible web page (HTML)** or **Word document**. GLOW extracts the worksheet content to Markdown automatically and then formats it with ACB styles. Review the extracted content to ensure table structure and headers came through correctly.

#### "I have a PowerPoint and I need to publish it as an accessible web page."

Go to **Convert**. Upload the .pptx and choose **Accessible web page (HTML)**. GLOW automatically extracts the content to Markdown and then formats it with full ACB Large Print styles. For best results, review the extracted Markdown before the final HTML step.

#### "I have an Excel workbook and I need to share the data as an accessible document."

Write your content in Markdown or Word. Audit it. Fix it (if Word). Then Convert to accessible PDF. The output uses ACB print formatting: Arial 18pt, 1.15 line spacing, 1-inch margins.

#### "I have a conference call recording and I need to turn it into a document."

Go to **BITS Whisperer**. Upload the audio file. Choose Markdown or Word output. Download the transcript. Edit it in a text editor, then use Convert or Fix to finish the document.

#### "I need to start fresh with a correctly formatted Word document."

Go to **Template**. Generate a .dotx file. Open it in Word. Everything is pre-configured.

#### "I want to understand what is wrong with a specific section of my document without reading a full audit report."

Go to **Document Chat**. Upload your document and ask your question in plain language.

#### "I have a scanned PDF of a printed handout."

Go to **Audit**. Upload the PDF. The audit will flag if the document is untagged or if text is not extractable. For scanned PDFs, the recommended path is to re-create the source document in Word, format it with ACB styles, and export a new PDF. GLOW cannot auto-fix scanned PDFs.

#### "My organization produces ePub publications for library distribution."

Go to **Audit** and upload the .epub. GLOW runs DAISY Ace (100+ axe-core checks), schema.org metadata validation, heading structure analysis, and alt text checks. The report includes DAISY Knowledge Base links for every finding. After manual remediation, re-audit to confirm.

---

## 2. How to Audit a Document

### Supported formats

| Format | What is checked |
|--------|----------------|
| Word (.docx) | Fonts, sizes, spacing, emphasis, alignment, margins, heading structure, alt text, table headers, document properties, language, hyperlink text |
| Excel (.xlsx) | Sheet names, table headers, merged cells, alt text, color-only data, hyperlink text, workbook title, blank-row layout patterns, default table names |
| PowerPoint (.pptx) | Slide titles, reading order, alt text, font sizes, speaker notes, chart descriptions, duplicate titles, timing and animation safety (auto-advance speed, repeating animations, rapid sequences, fast transitions) |
| Markdown (.md) | YAML front matter (presence, closed fence, title, lang fields), heading hierarchy, empty/overlong/punctuated headings, italic and bold-abuse emphasis, bare URLs, ambiguous link text, alt text (presence + quality), emoji, em-dashes, table structure (headers, column counts), code block language identifiers, raw HTML tables and moving content, fake lists, ALL CAPS body text |
| PDF (.pdf) | Title, language, tagging, font sizes, font families, scanned pages, bookmarks, form fields |
| ePub (.epub) | Title, language, navigation, heading hierarchy, alt text, table headers, accessibility metadata, link text, MathML -- plus 100+ axe-core checks via DAISY Ace |

### Choosing an audit mode

**Full Audit** checks every applicable rule for your file type. Use this for a first audit or when you need a complete picture.

**Quick Audit** checks only Critical and High severity rules. Use this for a fast pass when you know your document's common issues and want to confirm progress.

**Custom Audit** lets you select individual rules. Use this for targeted re-checks -- for example, only font rules after a font-focused fix pass.

### Step-by-step

1. Go to **Audit**.
2. Choose rule categories: ACB Large Print, MS Accessibility Checker, or both.
3. Select an audit mode.
4. Upload your file (500 MB maximum).
5. Optionally check **Email me the report** and enter your address (visible only when email delivery is configured on this server).
6. Click **Run Audit**.
7. Review the report.

### Quick Wins filter

After an audit of a Word document, the report shows a **Quick Wins** bar above the findings table. This bar shows how many findings can be auto-fixed and lets you toggle the table to show only those fixable findings.

- Click **Show Quick Wins Only** to filter the table to auto-fixable findings.
- Click **Fix These Auto-Fixable Issues** to go directly to the Fix page. If your session is still active (within one hour of upload), GLOW pre-loads your document into Fix automatically -- no re-upload required.
- Click **Show Quick Wins Only** again to restore all findings.

### Shareable audit report links

Every audit report generates a **shareable link** that lets you send the report to a colleague without giving them access to the GLOW interface. The link is shown in the Share section of the report.

- The link contains only the rendered HTML report -- the original document is never accessible through it.
- The link is valid for one hour from the time the audit completed.
- Anyone with the link can view the report; no login is required.
- After one hour, the link expires and the cached report is permanently deleted.

Use shareable links for team reviews, stakeholder sign-off, or archiving a point-in-time compliance snapshot.

### Passphrase-protecting a shared report (new in 2.8.0)

If you are sharing a sensitive compliance report -- a board submission, an internal audit, a vendor review -- you can protect it with a passphrase so the link alone is not enough to open it.

On the Audit form, find the **Share Link Protection (Optional)** section near the bottom. Type a passphrase of 4-200 characters. Leave it blank if you do not need protection.

What happens when you set a passphrase:

- Anyone who opens your share link sees an unlock form asking for the passphrase before the report is shown.
- The same passphrase is required to download the CSV or PDF copy.
- The passphrase is stored only as a salted cryptographic hash -- GLOW never stores or logs the cleartext value and cannot recover it.
- The share link still expires after one hour regardless of the passphrase.
- Send the passphrase through a **separate channel** -- for example, a text message or phone call. Do not include it in the same email as the link.

### Download report as PDF or CSV

The Share section of the audit report also offers two download buttons:

- **Download PDF** -- a print-styled PDF of the full report, suitable for attaching to a board packet, audit submission, or compliance file. Generated server-side and cached for the session lifetime.
- **Download CSV** -- the findings as a UTF-8 BOM CSV with header preamble (filename, format, score, grade, profile, mode) followed by one row per finding (severity, rule ID, message, location, ACB reference, auto-fix flag, help links). Opens cleanly in Excel.

Both downloads use the same one-hour share token, so the buttons disappear when the report expires.

### Re-audit diff: see exactly what changed

When you re-audit a document after running Fix on it (the streamlined Fix → Re-Audit flow), the report shows a **diff banner** at the top:

- Score delta (e.g. "+12 points") and grade change
- Counts of fixed, persistent, and newly-introduced findings
- A list of the rule IDs that were resolved since the previous audit

If a fix introduced a new issue, it is called out in the "newly introduced" count so nothing slips through.

### Inline rule explanations

Every rule ID in the findings table is a click-to-expand disclosure. Open it to see the canonical rule description, ACB reference, and a plain-language "Why this matters" rationale -- without leaving the page or losing your place in a long findings list. Auto-fixable rules show an "Auto-fixable" badge inside the disclosure.

### Convert → Audit handoff

When you convert a document to HTML, Word, or EPUB on the Convert page, the result page now shows an **Audit This Document** card. One click runs the audit on the converted file -- no re-upload, no extra step.

---

- **Rule ID** -- a short code like `ACB-FONT-FAMILY` or `EPUB-MISSING-ALT-TEXT`
- **Severity** -- Critical, High, Medium, or Low
- **Location** -- where in the document the issue was found (paragraph number, slide number, sheet name, heading text, etc.)
- **Description** -- what is wrong and why it matters
- **Help links** -- links to the DAISY Knowledge Base, Microsoft support, or WCAG documentation for remediation guidance

Findings are grouped by severity. Tackle Critical first -- they make the document unreadable. Then High, Medium, Low.

### Batch auditing

The Audit form supports batch mode for up to three files at once.

1. Select **Batch Mode** on the Audit form.
2. Add up to three files. Each file shows its name and size with an accessible Remove button.
3. Choose **Combined Report** (one scorecard with per-file findings in collapsible sections) or **Individual Reports** (separate full report per file, stacked on one page).
4. Submit.

If you submit more than three files, the first three are audited and a note explains the rest were skipped.

### Email delivery

When email delivery is configured on the server, an **Email Report** section appears on the form. Check the box and enter your email address to receive the scorecard and a findings CSV file immediately after the audit completes. The CSV opens in Excel and includes every finding with rule ID, severity, WCAG criterion, location, and whether it can be auto-fixed. Your address is used only to deliver the report and is never stored.

### AI disclosure

Every audit result shows a data and privacy notice. When AI was not involved, the notice says rule-based analysis only. When AI was used, the notice explains which cloud-powered path was used and points you to the privacy policy.

---

## 3. How to Fix a Document

### What gets auto-fixed

| Format | What is corrected automatically |
|--------|--------------------------------|
| Word (.docx) | Fonts changed to Arial; body text raised to 18pt minimum; headings to 22pt and 20pt; italic removed; bold-as-emphasis changed to underline; alignment set to flush-left; line spacing normalized; margins set; widow and orphan control enabled; hyphenation disabled; document language set |
| Markdown (.md) | Heading hierarchy corrected; italic removed; em-dashes replaced |
| Excel, PowerPoint, PDF, ePub | Audit report with step-by-step manual guidance; no auto-fix available |

### Starting Fix from an audit (no re-upload)

The fastest way to start a fix pass is directly from your audit report. After the audit completes:

1. Click **Fix This Document** in the "What's Next" section, or click **Fix These Auto-Fixable Issues** in the Quick Wins bar.
2. GLOW takes you to the Fix page with your document already loaded -- no need to upload again.
3. Adjust options and click **Fix Document**.
4. After the fix, click **Re-Audit Fixed Document** on the fix result page to run an audit on the fixed file immediately -- again, no re-upload required.

You can also set an optional **Share passphrase** in the Re-Audit form on the Fix result page. When set, the shared report link (and its CSV/PDF downloads) will require that passphrase.

This entire Audit → Fix → Re-Audit cycle requires uploading the document only once. The document session stays active for up to one hour from your initial upload.

### Step-by-step

1. Go to **Fix**.
2. Upload your document.
3. Choose a fix mode (Full, Essentials, or Custom).
4. Configure any advanced options (see below).
5. Click **Fix Document**.
6. For Word and Markdown: download the corrected file. Your original is untouched.
7. For other formats: review the audit report with manual fix instructions.

### Fix modes

**Full** applies every available fix and reports all findings.

**Essentials** applies every available fix but reports only Critical and High findings. Use this when you want a clean file and a shorter report.

**Custom** lets you pick which fix rules to apply and which to report. Use for targeted passes.

### Quick Rule Exceptions

The **Quick Rule Exceptions** section on the Fix and Audit forms lets you suppress specific findings for one operation without changing your defaults. Suppressed rules are listed in the results so you always know what was excluded.

**Suppress ambiguous link text** (`ACB-LINK-TEXT`) -- skip vague links for this run. Use when your links are contextually clear or when you are triaging structural issues first.

**Suppress missing alt text** (`ACB-MISSING-ALT-TEXT`) -- skip images without alt text for this run. Use when doing a formatting pass first and will add alt text in a later pass.

**Suppress faux heading detection** (`ACB-FAUX-HEADING`) -- skip bold or large text that looks like a heading but is not styled as one. Use when you intentionally want to preserve visual pseudo-headings for design reasons.

### Heading detection: turning visual headings into real ones

Many documents -- meeting agendas, policy memos, handouts assembled from email -- use bold, large text to look like headings instead of Word's actual Heading styles. This breaks screen reader navigation entirely. Users who rely on heading-based navigation cannot move through the document. GLOW can find and convert those visual headings into real semantic heading styles.

**How detection works:**

1. The tool scores each paragraph on ten signals: font size, bold formatting, paragraph length, capitalization patterns, position in the document, and surrounding context. Paragraphs above the confidence threshold are flagged as candidates.

2. When AI-assisted heading refinement is enabled by the operator, borderline candidates may be sent through the configured AI path for a second opinion based on surrounding context.

3. Detected headings are assigned across Heading 1 through Heading 6 based on font size, document position, and the heading levels you allow for the run. Heading 1 uses the 22pt primary heading treatment; deeper levels are normalized to the 20pt subheading pattern.

**Accuracy modes:**

- **Conservative** -- heuristics only, stricter filtering. Minimizes false positives. Best for documents with short labels, names, times, or single-word lines like "Agenda".
- **Balanced** (default) -- heuristics plus optional AI refinement. Best for most office documents.
- **Thorough** -- broader candidate capture with AI refinement. Best when real headings are being missed.

**Using heading detection on the web:**

1. On the Fix page, check **Detect and convert faux headings to real heading styles**.
2. Optionally check **Refine with AI** if that feature is enabled on your deployment.
3. Adjust the confidence threshold if needed. Default is 50 out of 100. Higher means fewer, more certain conversions.
4. Choose an accuracy level.
5. Click **Fix Document**.
6. If candidates are found, the **Heading Review** page loads. It shows every candidate with:
   - Paragraph text plus font size and formatting signals
   - Confidence score and the individual signals that fired
   - AI reasoning, when AI was used
   - A heading level dropdown (H1 through H6) pre-set to the suggested level, plus a Skip option
7. Adjust any candidates that are wrong. Set false positives to Skip.
8. Click **Apply and Fix**. Confirmed headings are converted, then the normal fix pipeline runs.

If no candidates meet the threshold, the fix proceeds without the review step.

**Using heading detection on the CLI:**

```shell
# Heuristic only
acb-lp fix document.docx --detect-headings

# With AI refinement
acb-lp fix document.docx --detect-headings --ai

# Detection only (report without fixing)
acb-lp detect-headings document.docx

# Custom threshold and prompt file
acb-lp detect-headings document.docx --ai --ai-prompt prompt.txt --threshold 75
```

### Preserve centered headings

By default, Fix normalizes all paragraph alignment to flush-left per ACB requirements. Check **Preserve centered headings** on the Fix form to leave heading alignment as-is while still normalizing non-heading paragraphs.

Fix also enforces paragraph spacing through Word's **paragraph format** settings (`Space Before` / `Space After`) rather than by inserting blank paragraphs. That means normal body text is normalized to the configured post-paragraph spacing without adding extra empty lines to the document.

### Per-level list indentation

By default, Fix applies a uniform left indent to all list items. **Per-level list indentation** lets you specify different indent values for each nesting depth -- useful for documents with multi-level lists where each depth should use a specific measurement.

1. On the Fix form, find **List Indentation**.
2. Uncheck **Flush all lists to the left margin** if it is checked.
3. Check **Use per-level list indentation**.
4. Enter inch values for Level 1, Level 2, and Level 3. Leave a level blank if your document does not use it.

### Allowed heading levels

Restrict heading detection and review to a subset of levels. If your editorial style uses only H1 through H3, select those levels in the Heading Detection section of the Fix form. The review page will only show your selected levels in each dropdown. Configure defaults in **Settings** to have the form pre-filled on every visit.

### Custom font sizes (new in 2.8.0)

By default, GLOW applies the ACB Large Print standard sizes: 18pt body text, 22pt Heading 1, and 20pt for all other heading levels. If your organization uses different sizes -- for example, a 20pt body for a high-contrast handout, or 24pt headings for a large-format poster -- you can override any or all of these in the **Font Sizes** section of the Fix and Template forms.

**How to use:**

1. Open the Fix or Template form.
2. Find the **Font Sizes (Optional)** fieldset.
3. Enter a point size for Body (Normal text), or for any heading level (H1 through H6) you want to change.
4. Leave any field blank to keep the ACB default for that level.
5. Values are clamped to the range 8pt-96pt.

**What changes when you set a custom body size:**

- The auditor uses your body size as the minimum expected size for body paragraphs.
- The fixer raises body text to your specified size instead of the default 18pt.
- List Bullet and List Number styles are also updated to match your body size.
- The page-growth warning threshold adjusts to your specified body size.

**What changes when you set custom heading sizes:**

- The auditor expects your specified size for each heading level.
- The fixer applies your specified size to each heading level.

Custom sizes are a per-session setting. They are not stored by default -- configure defaults in **Settings > Font Size Defaults** to have the form pre-filled on every visit.

### Understanding page growth after fix

When body text is below 18pt, raising it to the ACB minimum increases line count. A 16pt newsletter will get notably longer after fix. Fix Results shows a page-growth warning when this condition is detected so the pagination change is expected rather than surprising.

### Fix result disclosures

Fix Results shows:

- Before and after compliance scores
- A list of every rule that was changed, with counts
- Which rules were suppressed (if any)
- A page-growth warning (when applicable)
- The exact time the fixed document will be deleted (one hour after upload)

---

## 4. How to Create a Template

A template (.dotx) is the most efficient path to compliance. Every document you create from it inherits correct formatting from the first keystroke -- no fixing required later.

### Step-by-step

1. Go to **Template**.
2. Enter a document title, or leave blank for a generic template.
3. Optionally check **Include sample content** to see examples of every heading level, list type, table, and emphasis style in the generated file.
4. Check **Add binding margin** if the document will be printed and bound (adds 0.5 inches to the left margin).
5. Click **Create Template** and save the downloaded .dotx file.
6. In Word, double-click the .dotx to create a new document from it.

### Installing the template in Word

Save the .dotx to your personal Templates folder:

- **Windows:** `%APPDATA%\Microsoft\Templates`
- **macOS:** `~/Library/Group Containers/UBF8T346G9.Office/User Content/Templates`

Then in Word, go to **File > New > Personal** (or Custom on Mac) and select the ACB Large Print template.

### Allowed heading levels for sample content

If your editorial policy uses only a subset of heading levels, choose those in the Template form. Sample content will use only your selected levels, so the generated file matches your actual workflow. Configure defaults in **Settings > Template Defaults** to have the form pre-filled on every visit.

### Standards profiles

- **ACB 2025 Baseline** -- current production defaults (Arial, ACB spacing). Use for day-to-day document production.
- **APH Submission** -- APH-oriented defaults (APHont preferred where available). Use when producing documents for APH submission or review.
- **Combined Strict** -- ACB template defaults with the strictest audit posture. Use for final pre-release quality gates.

---

## 5. CMS Fragment (formerly Export)

In v2.7.0, the dedicated Export page was merged into Convert. All Export functionality is now available in **Convert** at the same URL (`/convert`).

### What changed

- The **Export** tab functionality has been folded into Convert (CMS Fragment option) and is no longer a separate navigation entry.
- Bookmarks and links to `/export` are automatically redirected to `/convert`.
- CMS Fragment output is available in Convert: upload a Word file and select **CMS Fragment** as the direction.
- Standalone HTML output is also available in Convert: select **Accessible web page (HTML)** as the direction.

### How to produce a CMS Fragment (for WordPress, Drupal, or any CMS)

1. Go to **Convert**.
2. Upload a Word (.docx) file.
3. Select **CMS Fragment** as the output direction.
4. Click **Convert**.
5. On the result page, download the `-cms.html` file, or use the **Copy to Clipboard** button to copy the scoped HTML snippet directly.

The CMS Fragment contains HTML scoped to an `.acb-lp` wrapper class with matching CSS. Paste it into your CMS HTML editor without affecting your site theme.

### How to produce Standalone HTML

1. Go to **Convert**.
2. Upload a Word (.docx), Markdown (.md), or other supported file.
3. Select **Accessible web page (HTML)**.
4. Click **Convert** and download the result.

If your source is Markdown, Pandoc handles it directly and produces cleaner output than the Word-to-HTML path.

### Feature flag

The CMS Fragment direction in Convert is gated by the `GLOW_ENABLE_EXPORT_HTML` flag. Deployments that had this flag set to `false` will continue to hide CMS Fragment without any configuration change.

---

## 6. How to Convert Between Formats

The Convert page offers conversion directions powered by different engines. Starting in 2.7.0, PowerPoint (.pptx), Excel (.xlsx/.xls), PDF (.pdf), HTML, CSV, JSON, and XML files can be converted directly to accessible HTML, Word, EPUB, and PDF -- no manual intermediate step required. GLOW uses a smart two-stage process: MarkItDown extracts the content to Markdown, then Pandoc applies full ACB Large Print formatting. This happens transparently when you upload one of these file types and choose an output format.

Long-running Convert actions now use a unified job model with live progress plus explicit **Cancel** and **Retry** controls. Jobs also run with a server-side deadline and bounded retry attempts so status behavior is predictable for users and operators.

### To Markdown (plain text extraction)

**Engine:** Microsoft MarkItDown

Extracts readable text from any supported file. Good for feeding documents into AI tools, creating editable starting points, or getting content you can clean up and re-convert.

**Accepts:** Word (.docx), Excel (.xlsx, .xls), PowerPoint (.pptx), PDF (.pdf), HTML, CSV, JSON, XML, ePub (.epub), ZIP, and image files.

**You get back:** a `.md` file -- plain text with Markdown formatting marks for headings, lists, and links.

**AI image descriptions:** some deployments may enable AI-assisted image description generation for supported conversion paths. Check your local deployment policy before using AI-powered image workflows.

**When to use:** you need the raw content out of a file in any format. Also the right first step before a chain conversion -- extract to Markdown, edit, then convert to HTML, Word, EPUB, or PDF.

### To accessible web page (HTML)

**Engine:** Pandoc (with MarkItDown pre-processing for some formats)

Converts a document to a complete, accessible HTML page with ACB Large Print CSS built in. Produces clean, semantically correct HTML with proper headings, lists, tables, footnotes, and cross-references.

**Accepts natively:** Markdown (.md), Word (.docx), reStructuredText (.rst), OpenDocument (.odt), Rich Text (.rtf), ePub (.epub).

**Accepts via two-stage extraction:** PowerPoint (.pptx), Excel (.xlsx, .xls), PDF (.pdf), HTML (.html, .htm), CSV, JSON, XML. GLOW extracts content to Markdown first, then Pandoc formats the result.

**You get back:** a standalone `.html` file with all ACB formatting included.

**Options:**

- **ACB formatting** (on by default) -- embeds the full ACB Large Print stylesheet
- **Binding margin** -- shifts content right 0.5 inches for printed and bound output
- **Print stylesheet** -- adds `@media print` rules for ACB's print line-height (1.15 instead of 1.5)
- **Generate clickable Table of Contents** (on by default) -- Pandoc builds a fresh `<nav id="TOC">` with anchor links to every heading in the document. For Word (.docx) sources, the original auto-generated TOC field (which Pandoc otherwise flattens to unlinked paragraphs) is detected and removed so the output does not contain a duplicate unlinked TOC.
- **Format-faithful conversion** (off by default) -- skips ACB styling, binding-margin injection, and print-stylesheet post-processing so the HTML reflects the source document as closely as possible. When this is on, the three options above (ACB formatting, binding margin, print stylesheet) are ignored.

**When to use:** producing a web page for a browser, for printing from a browser, for email attachment, or for uploading to a website. Markdown input produces the cleanest output. Turn on **Format-faithful conversion** when you want GLOW to act as a pure converter and leave the look and feel of the source alone.

### To Word document

**Engine:** Pandoc (with MarkItDown pre-processing for some formats)

Converts a document to a Word file (.docx). Pandoc maps headings, lists, tables, and emphasis into Word's native styles.

**Accepts natively:** Markdown (.md), reStructuredText (.rst), OpenDocument (.odt), Rich Text (.rtf), HTML (.html), ePub (.epub).

**Accepts via two-stage extraction:** PowerPoint (.pptx), Excel (.xlsx, .xls), PDF (.pdf), CSV, JSON, XML. GLOW extracts content to Markdown first, then Pandoc formats the result.

**You get back:** a `.docx` file, immediately editable in Microsoft Word or LibreOffice Writer.

**When to use:** you have a Markdown or HTML document and need a Word version -- either for colleagues who work in Word, or to run GLOW Fix on content that started in another format. Common workflow: extract to Markdown, edit, convert to Word, then Fix.

### To EPUB 3 e-book (Pandoc)

**Engine:** Pandoc (with MarkItDown pre-processing for some formats)

Creates a lightweight EPUB 3 e-book with ACB Large Print CSS embedded in the stylesheet. Pandoc generates proper EPUB structure including a navigation document and EPUB metadata from the document title.

**Accepts natively:** Markdown (.md), Word (.docx), reStructuredText (.rst), OpenDocument (.odt), Rich Text (.rtf), HTML (.html).

**Accepts via two-stage extraction:** PowerPoint (.pptx), Excel (.xlsx, .xls), PDF (.pdf), CSV, JSON, XML.

**You get back:** an `.epub` file that opens in Apple Books, Calibre, Thorium, and other e-readers.

**When to use:** you need a simple, portable e-book. For production-quality EPUB with full accessibility metadata and DAISY reading-system compatibility, use the Pipeline option instead.

### To accessible PDF

**Engine:** Pandoc plus WeasyPrint (with MarkItDown pre-processing for some formats)

Creates a print-ready PDF formatted with ACB rules. Pandoc converts the source to HTML, then WeasyPrint renders it to PDF using ACB print rules: Liberation Sans (metrically identical to Arial), 18pt body text, 22pt headings, 1.15 line spacing, and 1-inch margins.

**Accepts natively:** Markdown (.md), Word (.docx), reStructuredText (.rst), OpenDocument (.odt), Rich Text (.rtf), ePub (.epub), HTML (.html).

**Accepts via two-stage extraction:** PowerPoint (.pptx), Excel (.xlsx, .xls), PDF (.pdf), CSV, JSON, XML.

**You get back:** a `.pdf` file.

**Options:**

- **Binding margin** -- adds 0.5 inches of extra left margin for printed and bound documents

**When to use:** producing a document that will be printed and distributed in large print. Note: WeasyPrint produces CSS-rendered PDFs that are visually formatted but may not carry full PDF/UA structural tags. For maximum tagged-PDF accessibility, fix the source document first and export from Word or LibreOffice.

### To EPUB or DAISY (DAISY Pipeline)

**Engine:** DAISY Pipeline 2

Creates accessible publications in formats designed for reading systems used by people with print disabilities. Produces packaged EPUB e-books and DAISY talking books with proper accessibility metadata, navigation documents, and reading order.

**Available conversions:**

- Word (.docx) to EPUB 3
- HTML to EPUB 3
- ePub to DAISY 2.02 talking book format
- ePub to DAISY 3 / DTBook

**You get back:** an `.epub` file or a `.zip` containing the DAISY output folder.

Pipeline conversions appear when DAISY Pipeline is installed on the server. If you do not see these options, Pipeline is not running on this instance.

### How to choose

| If you need... | Use... |
|----------------|--------|
| A web page to view in a browser or print | Accessible web page (HTML) |
| A print-ready PDF | Accessible PDF |
| A Word file to edit or run through Fix | Word document |
| A quick e-book | EPUB 3 e-book (Pandoc) |
| A DAISY talking book or production EPUB | EPUB or DAISY (Pipeline) |
| Raw content for editing or AI | Plain text (Markdown) |
| An HTML snippet for WordPress or Drupal | Convert page -- CMS Fragment direction |
| A PowerPoint or Excel file as a web page | Accessible web page (HTML) -- two-stage |
| A PDF reformatted with ACB print styles | Accessible PDF -- two-stage |

### Getting better results with chained conversion

For complex source formats (PowerPoint, Excel, PDF), GLOW automatically runs a two-stage process when you choose HTML, Word, EPUB, or PDF output: it extracts content to Markdown first (via MarkItDown), then Pandoc formats the result with ACB styles. You do not need to do anything extra -- just upload your file and choose your output format.

For even higher quality, you can run the chain manually and edit the intermediate Markdown:

1. **Extract to Markdown** -- pulls the text out of the source file.
2. **Edit the Markdown** -- fix headings, clean up tables, replace vague link text, add missing alt text.
3. **Convert the Markdown** -- to HTML, Word, EPUB, or PDF.

Manual chaining gives you a review step between extraction and formatting. Automatic chaining is faster when the source structure is clean.

---

## 7. Braille Studio: Text-to-Braille Translation

### Overview

Braille Studio translates English text to braille and back-translates braille to English text using [liblouis](https://liblouis.io/) with official BANA (Braille Authority of North America) translation tables.

### Supported braille codes and grades

- **UEB Grade 2** (Unified English Braille, contracted) — *Recommended for most literary text.* BANA current standard adopted January 4, 2016.
- **UEB Grade 1** (uncontracted) — For technical, scientific, and instructional materials where unambiguous cell-by-cell mapping is required.
- **BANA Computer Braille Code (8-dot)** — For source code, file paths, command-line output, and computer notation.
- **EBAE Grade 1 and Grade 2** (legacy) — English Braille American Edition, pre-2016 US standard. Provided for interoperability with older materials.

### How to use Braille Studio

1. **Open Braille Studio** -- Select **Braille Studio** under the **Transform** group in the left sidebar.
2. **Choose your direction:**
   - **Text → Braille** — Paste English text or upload a `.txt`, `.md` file
   - **Braille → Text** — Paste braille (Unicode or ASCII) or upload a `.brf`, `.brl` file
3. **Select a braille grade** — Default is UEB Grade 2 (BANA current standard). For technical content, choose UEB Grade 1 or Computer Braille Code.
4. **Choose output format** (text-to-braille only):
   - **Unicode Braille** — Display on screen, copy to documents, or send to braille displays
   - **BRF (Braille Ready Format)** — ASCII braille, embosser-ready, wrapped at 40 cells per line per BANA standards
5. **Paste or upload your input** — Paste directly in the text box (max 50,000 characters) or upload a file (max 512 KiB)
6. **Click Translate** — Results appear instantly.
7. **Download or copy** — Copy the result from the text box or click **Download** to save as `.brl` (Unicode) or `.brf` (ASCII)

### Key features

- **No account required** — Completely server-side. No cloud service, no API key.
- **Accessible UI** — Keyboard operable, screen reader friendly, WCAG 2.2 AA compliant.
- **BANA formatting** — BRF output automatically wrapped at the BANA-standard 40 cells per line.
- **Graceful degradation** — If liblouis is not installed, displays a friendly message explaining how to enable it.

### Important note about back-translation

- **Grade 1 and Computer Braille:** Lossless — you get exactly what you put in.
- **Grade 2:** Approximate by design. Because contractions are lossy, some context is lost. Back-translated results are best-effort interpretations.

For precise back-translation, use Grade 1 or Computer Braille.

### Standards and references

- [Braille Authority of North America (BANA)](https://www.brailleauthority.org/)
- [Unified English Braille (UEB) Rules](https://www.brailleauthority.org/ueb/ueb.html)
- [BANA Formats Guidelines](https://www.brailleauthority.org/formats/index.html)
- [liblouis Project](https://liblouis.io/)

---

## 8. Speech Studio: Document-to-Audio

Speech Studio synthesizes English documents to MP3 or WAV audio. Users can narrate board minutes, newsletters, training materials, or any document in the voice of their choice.

### How to use Speech Studio

1. **Open Speech Studio** -- Select **Speech Studio** under the **Listen and Speak** group in the left sidebar.
2. **Paste text or upload a document** — Paste English text directly or upload a file (Markdown, Word, PDF, Excel, PowerPoint, ePub, etc.)
3. **Choose your voice** — Select from curated Piper TTS voices (fast, local) or remote OpenRouter providers.
4. **Adjust speed and pitch** — Customize playback speed (0.5x to 2.0x) and pitch offset (−12 to +12 semitones).
5. **Preview or download** — Click **Preview** to hear the first few seconds or **Download** to get the full MP3 or WAV file

### Features

- **Fast processing** — Adaptive timing estimates based on real server telemetry
- **Multiple voices** — Curated selection of Piper TTS voices plus optional OpenRouter providers
- **Document support** — Upload Markdown, Word, PDF, Excel, PowerPoint, ePub, RTF, HTML, and more
- **High-quality output** — Downloads as MP3 or WAV
- **Session persistence** — Your voice and speed preferences are remembered across sessions

### Workflow tip: Convert → Speech

After converting a document to Markdown, HTML, or another format, the Convert tool offers a direct **Speech** button. Jump straight to Speech Studio with your newly converted document — no re-upload needed.

### PageFlow: read articles and narrate them

PageFlow is the browser-reading companion for articles, essays, and newsletters. It extracts the readable text from a URL, follows simple next-page pagination when a story spans multiple pages, shows you the cleaned text, and then lets you edit or narrate it before downloading audio.

### How to use PageFlow

1. **Open PageFlow** -- Select **PageFlow** under the **Listen and Speak** group in the left sidebar.
2. **Paste an article URL** -- Enter the page you want to read. PageFlow will try to detect pagination links and combine the story into one view.
3. **Review the extracted text** -- Check the cleaned text, which removes most navigation and boilerplate content.
4. **Edit if needed** -- Trim, correct, or rearrange the text before narration.
5. **Choose a narration voice** -- Pick the voice you want PageFlow to use for the audio version.
6. **Download audio** -- Generate an MP3 or WAV narration file from the article text.

### When to use PageFlow

- You want a reading-mode style view for a long article instead of the original page layout.
- The article spans multiple pages and you want the pages merged into one readable flow.
- You want to skim or revise the extracted text before generating speech.
- You want a single place to read first and listen later without changing tools.

---

## 9. BITS Whisperer: Transcribe Audio

BITS Whisperer transcribes audio files into accessible text documents using the Whisper API. GLOW may normalize OGG, FLAC, AAC, or Opus uploads into a more compatible temporary format before sending them for transcription.

### When to use BITS Whisperer

- You have a recorded meeting, presentation, or phone call and need a text transcript.
- You have a podcast episode or interview you want to make available as accessible text.
- You received a voice message and need a written version.
- You need to produce an accessible Word document from spoken content.

### Supported formats

MP3, WAV, M4A, OGG, FLAC, AAC, Opus.

### Step-by-step (standard mode)

1. Click the **BITS Whisperer** tab, or from Quick Start upload an audio file.
2. Upload your audio file (up to 500 MB by default).
3. Review the estimated conversion time shown after file selection.
4. Check the confirmation box to acknowledge you want to proceed.
5. Select a language, or leave it on **Auto-detect** (recommended for most recordings).
6. Choose output format: **Markdown** (.md) or **Word** (.docx).
7. Click **Transcribe Audio**.
8. Watch the progress bar. When it reaches 100%, your download starts automatically.

Keep the browser tab open while transcription runs. Navigating away does not cancel the job, but you will need the page open to trigger the download.

### Background mode for long recordings

For recordings estimated to take more than 30 minutes to transcribe (configurable by the server administrator), Whisperer offers a background processing option. Use this when you do not want to keep a browser tab open for an extended period.

1. Check **Process in background** on the Whisperer form.
2. Enter an email address for lifecycle notifications.
3. Create and confirm a retrieval password.
4. Submit.

GLOW sends email at three points: when the job is queued, when transcription starts, and when it completes. The completion email contains a single-use secure retrieval link. You must use both the link and the retrieval password to download the transcript.

If you do not retrieve the transcript within the configured window (default four hours after completion), GLOW removes it and sends a final email confirming the deletion.

### Audio limits

| Limit | Default | Environment variable |
|-------|---------|---------------------|
| File size | 500 MB | `WHISPER_MAX_AUDIO_MB` |
| Recording length | 120 minutes | `WHISPER_MAX_AUDIO_MINUTES` |
| Background queue depth | 5 jobs | `GLOW_MAX_AUDIO_QUEUE_DEPTH` |
| Background eligibility threshold | 30 minutes | `WHISPER_BACKGROUND_THRESHOLD_MINUTES` |
| Retrieval window | 4 hours after completion | `WHISPER_RETRIEVAL_HOURS` |

When a file exceeds a limit, GLOW returns a clear message and guidance to split or compress the recording.

### Tips for best results

**One speaker at a time.** Whisper handles overlapping voices poorly. Multiple people talking at once reduces accuracy significantly.

**Minimize background noise.** Close the microphone to the speaker. HVAC noise, crowd ambience, or background music all reduce accuracy.

**Specify the language for short clips.** For recordings under 30 seconds, picking the language explicitly is faster and more accurate than auto-detect.

**Review before using.** Whisper is highly accurate for clear English speech, but technical terms, proper nouns, and accents may need correction.

**Edit in Markdown first.** Download the .md file, correct it in any text editor, then convert it to your target format using the Convert page. This two-step approach gives you full control.

**Split very long meetings.** Recordings over two hours are better split into 20 to 30 minute segments. Each segment transcribes faster, errors are easier to find, and you can publish sections independently.

### Privacy

Your audio is uploaded to GLOW, optionally normalized for compatibility, sent to the Whisper transcription service, and held only as long as needed to complete conversion and deliver your download. After download or expiry, temporary files are removed. Nothing is stored as permanent account data.

---

## 10. AI Playground (Beta): Explore Personal AI Models

The AI Playground is your experimental testing ground for personal AI models. It is a standalone chat surface, separate from your documents, where you can explore how different compatible provider/model combinations respond to questions and get comfortable with AI before relying on it for real accessibility work.

Think of it as a safe space to build confidence. Ask any question. Switch models mid-conversation. Copy responses. Conversations stay in your session only and are never persisted to disk. It is magic because every part of it is designed to feel fluid and responsive.

### Why the Playground exists

- **Explore freely:** Try different compatible provider/model choices without risking document workflows.
- **Learn by doing:** See how models respond to accessibility questions, repair guidance, formatting advice.
- **Test before shipping:** Verify model behavior matches your expectations.
- **Private experimentation:** Session-scoped history. You delete it when you close the browser.
- **Accessible navigation:** Questions appear as H3 headings, answers as H4, so you can jump directly between them with a keyboard or screen reader.

### How to access the Playground

1. Go to the **Explore and Learn** section in the left sidebar.
2. Click **Experimental** and select **AI Playground**.
3. You will need at least one active personal AI provider key in AI Features.

### What the Playground feels like

**Starting a conversation:**
- Type a question or prompt in the text area.
- Press Enter (or Shift+Enter for a new line) or click Send.
- While GLOW fetches the response, a temporary assistant bubble appears showing "Thinking…"

**Receiving a response:**
- The thinking bubble smoothly transitions to the real response with no page reload.
- The response includes the model name and a **Copy** button so you can grab the text.
- A typing indicator animates to show progress during long responses.

**Continuing the conversation:**
- Ask follow-up questions. GLOW keeps the conversation history.
- Notice the conversation log shows clear visual distinction: your questions as H3 headings, AI responses as H4 headings.
- Screen reader users can jump directly between questions and answers using heading navigation.

**Switching models:**
- Click the model selector to try a different compatible model without clearing history.
- If a response runs longer than a few seconds, GLOW announces that it is still in progress for screen reader users and announces again when the delayed response arrives.
- Re-ask your last question with a different model to compare responses.
- Clear the entire conversation with the **Clear** button (you will be asked to confirm).

### Starter questions to try

- "Explain the ACB Large Print Guidelines in simple terms."
- "What is the difference between em-dash and hyphen in accessible documents?"
- "How would you fix italicized text in a low-vision document?"
- "What heading hierarchy means and why it matters for screen readers."
- "Describe the relationship between font size and line height in accessibility."

### What the Playground is not

- **Not Document Chat:** The Playground has no access to your documents. It is pure exploration.
- **Not persistent:** Refresh the page and the conversation disappears.
- **Not production-ready:** It is labeled Beta because we are still refining the experience.
- **Not a replacement for Audit/Fix:** Use Document Chat or Audit for serious accessibility analysis.

---

## 11. MarkItDown + AI Integration: Smarter Text Extraction

MarkItDown is a powerful text extraction tool from Microsoft. GLOW 6.0.0 combines it with an LLM to make document extraction smarter and faster.

### What is enabled

When you connect a compatible personal AI provider key in GLOW Settings, **MarkItDown + AI support is on by default** for:

- **Heading detection** — converts bold or large text into semantic headings automatically
- **Intelligent extraction** — understands context and structure, not just layout
- **Cleaner documents** — removes page numbers, repeated footers, noise, and artifacts

### How it works

When you run Audit or Fix on any document (Word, PDF, Markdown, Excel, PowerPoint, ePub), the AI-enhanced extraction:

1. Reads the document structure and content
2. Identifies what should be a heading vs. body text
3. Extracts text with AI awareness of importance and relationships
4. Returns cleaner input for accessibility workflows

### What you get

- **Better heading detection** — catches heading patterns that rule-based extraction misses
- **Less manual cleanup** — fewer artifacts and false structure to fix later
- **Consistent results** — works across all formats (Word, PDF, Markdown, Excel, PowerPoint, ePub)
- **Faster workflows** — more time for real accessibility work, less time on false positives

### Why it matters

Headings and document structure are objective problems:
- Either a text block is a heading, or it is not.
- Either a list item is a real list, or it is fake formatting.
- Either a paragraph break is intentional, or it is a layout artifact.

MarkItDown + AI solves these consistently. The combined approach produces documents that need less manual remediation before you can run Fix or convert to accessible output.

### Try it

1. **Audit mode:** Upload a document with missing or incorrect headings. The audit report will show what headings were detected and what remains. The score reflects both AI-found headings and manual structure issues.

2. **Playground first (optional):** Before trusting heading detection in production, try the AI Playground with a few sample headings from your document. Test different compatible provider/model options to see which one works best for your document types. Then configure that provider/model in AI Features and run Fix.

3. **Fix mode:** Run Fix on the document. Heading detection runs automatically if heading-fix AI is enabled. The corrected document shows the cleaned-up structure.

4. **Re-audit:** After Fix, run Audit again on the corrected document to confirm the structure improvements and identify remaining manual fixes.

### Performance and cost

- MarkItDown + AI uses your active personal provider/model binding, so cost depends on the provider and model you selected for that feature
- Extraction happens once per document, not per heading
- Results are deterministic but AI-influenced (different models may detect headings slightly differently; that is normal)

---

## 12. Document Chat

Document Chat lets you ask questions about an uploaded document in plain language. An OpenRouter-backed AI gateway answers using accessibility-focused tools across compliance, structure, content, and remediation. Core workflows remain available without AI if you prefer not to use it.

### When to use Document Chat

- You want to know what the most critical issues are without reading a full audit report.
- You want to ask a specific question: "Does Section 4 have any heading hierarchy problems?"
- You need a compliance summary for a team or board update.
- You want to understand a specific rule: "What does ACB-LINK-TEXT mean and how do I fix it?"
- You want to estimate how much work auto-fix will save before you commit to a workflow.

### Step-by-step

Document Chat requires an uploaded document. There are two ways to reach it:

**From Quick Start (recommended for new documents):**
1. Go to **Quick Start: Upload and Discover** on the homepage.
2. Upload your document and click **Next: Choose an Action**.
3. Select **Chat** from the action menu.

**From Audit or Fix results (no re-upload needed):**
1. Run an Audit or Fix on your document.
2. On the results page, click **Chat about this document**.
3. Type your question in the text field and press Enter or click Ask.
4. GLOW reads the document, calls the relevant tools, and returns a grounded answer.
5. Continue asking follow-up questions. Each turn is tracked in conversation history.
6. When done, export the session to Markdown, Word, or PDF.

### Agent categories and tools

Document Chat has 24 callable tools in five groups. GLOW selects and combines them based on your question -- you do not call them directly.

**Document tools** (7 tools) -- extract tables, find sections by heading name, search for keyword matches with line numbers, get word count and reading time statistics, summarize a section, list the full heading hierarchy, and list images.

**Compliance Agent** (4 tools) -- run a full GLOW audit summary with severity counts, get the compliance score with breakdown, list only Critical and High findings, list only findings that Fix can correct automatically.

**Structure Agent** (4 tools) -- detect skipped heading levels, find faux headings (bold paragraphs acting as headings), inspect list nesting, estimate reading-order risk from table and layout signals.

**Content Agent** (4 tools) -- detect italic and bold-abuse emphasis violations, flag bare URLs and vague link phrases, estimate reading level, detect center and right alignment overrides.

**Remediation Agent** (5 tools) -- explain any ACB rule ID in plain language, provide targeted fix instructions, rank all findings by severity and auto-fixability, estimate the score improvement Fix would produce, check images for missing or empty alt text.

### Starter prompts

- "Run an accessibility summary and tell me the top five issues."
- "List critical findings only and explain why each one matters."
- "Show me where heading hierarchy is broken."
- "Find faux headings and suggest the correct heading level for each."
- "Are there any ambiguous links like 'click here' or bare URLs?"
- "What is auto-fixable versus what needs manual work?"
- "Prioritize all findings by impact and effort."
- "Explain rule ACB-LINK-TEXT in plain language."
- "What would my score be after running Fix?"
- "Summarize Section 3 in two sentences."

### Conversation tips

- Ask one question at a time for the clearest answers.
- Reference section names when asking about specific content.
- Follow with "show evidence" to get concrete paragraph text or line numbers.
- Use "critical only" when you need a fast triage view.
- Export the session when finished. The export becomes an audit trail you can share with your team.

### Accessibility and privacy

Conversation history is organized by heading-based turns for screen reader navigation. All controls are keyboard accessible. No JavaScript is required for core chat usage. Sessions use GLOW's AI gateway and follow the same 1-hour retention policy for uploaded documents.

For AI-bound text, GLOW can apply Presidio-based preflight redaction before model calls. This is controlled by feature flags:

- `GLOW_ENABLE_PII_GUARDRAILS` (default: enabled)
- `GLOW_ENABLE_PII_GUARDRAILS_STRICT_MODE` (default: enabled)

When strict mode is enabled and the guardrail engine is unavailable, the AI request is blocked instead of sending unredacted text.

---

## 12. Settings

The **Settings** tab lets you configure default values once and apply them across every workflow.

### What Settings controls

- **Standards profile defaults** for Audit, Fix, and Template
- **Audit defaults:** mode, categories, and quick-rule suppressions
- **Fix defaults:** mode, categories, heading detection options, list and paragraph indentation settings, and suppressions
- **Template defaults:** profile, sample content, binding margin, and allowed heading levels
- **Export and Convert defaults**

### Privacy and persistence

Settings are saved in your browser's local storage. Nothing is sent to the server. Your preferences stay on the current browser and device only. Clearing browser data or site storage removes saved settings and returns GLOW to its built-in defaults.

### First-time setup

1. Open **Settings**.
2. Set your preferred audit mode and categories.
3. Set your preferred fix mode and heading options.
4. Click **Save My Settings**.
5. Open Audit or Fix and verify the defaults are pre-selected.

---

## 13. Understanding Your Results

### Severity levels

| Level | What it means | What to do |
|-------|--------------|------------|
| Critical | Makes the document unreadable for low-vision users or completely blocks assistive technology | Fix before publishing. These are deal-breakers. |
| High | Significant readability or structure problems | Fix as part of your remediation pass. |
| Medium | Compliance gaps that affect quality but do not block reading | Fix when time permits. |
| Low | Minor issues and best-practice recommendations | Address during polishing. |

### Compliance score

The score is the percentage of passing rules out of applicable rules for your document type. A score of 90 or above (Grade A) is the target for publishing. Below 70 (Grade C or lower) indicates substantial work is needed.

GLOW computes the score using a weighted-penalty model where each rule contributes a base severity deduction, and repeated occurrences of the same rule add a capped surcharge. This means grouped findings in the table do not change the score calculation; they only improve readability of the report.

### Standards profiles

**ACB 2025 Baseline** -- day-to-day production. No change from previous workflows.

**APH Submission** -- filters the report to APH-aligned checks. Use when producing evidence for APH submission or review cycles.

**Combined Strict** -- includes all implemented checks across ACB, WCAG, and MSAC. Use for final pre-release quality gates.

Profile selection changes report filtering and template defaults. It does not change the underlying auto-fix behavior for Word documents.

---

## 14. Common Issues and How to Fix Them

### "All text must use Arial font" (ACB-FONT-FAMILY)

**Why it matters:** Arial is required because it is a clean sans-serif font with excellent legibility at large sizes. Decorative, serif, and condensed fonts are harder to read for people with low vision.

**Auto-fix:** Yes. Fix changes all fonts to Arial.

**Manual fix:** In Word, select all text with Ctrl+A and change the font to Arial.

### "Body text must be 18pt minimum" (ACB-FONT-SIZE-BODY)

**Why it matters:** 18pt is the absolute floor for any text, including footnotes, captions, and table cells.

**Auto-fix:** Yes. Fix raises all body text to 18pt.

**Manual fix:** Select text smaller than 18pt and increase the font size.

### "Italic formatting is not permitted" (ACB-NO-ITALIC)

**Why it matters:** Slanted letter shapes are harder to distinguish at large sizes. Italic is prohibited everywhere, not just in body text.

**Auto-fix:** Yes. Fix removes all italic formatting.

**Manual fix:** Select italic text and press Ctrl+I to remove it. For emphasis, use underline (Ctrl+U) instead.

### "Images must have alternative text" (various alt text rules)

**Why it matters:** Screen readers cannot describe images. Users who cannot see the image rely entirely on the alt text description.

**Auto-fix:** No. Alt text requires human judgment about what the image actually shows.

**Manual fix in Word:** Right-click the image and choose **Edit Alt Text**. Describe what the image shows in one or two sentences. If the image is purely decorative, check **Mark as decorative**.

**Note:** Legacy Word VML shapes with `alt=""` are treated as decorative by GLOW and do not trigger a finding.

### "Heading levels must not skip" (ACB-HEADING-HIERARCHY / EPUB-HEADING-HIERARCHY)

**Why it matters:** Screen reader users navigate by heading level. Jumping from H1 to H3 breaks the document's logical structure and prevents efficient navigation.

**Auto-fix:** No. Heading intent requires human judgment.

**Manual fix:** Review your heading hierarchy. Each H3 must have an H2 parent; each H2 must have an H1 parent. Restructure or re-level headings as needed.

### "Links must have descriptive text" (various link text rules)

**Why it matters:** Vague links like "click here" or "read more" do not tell screen reader users where the link goes. Links should make sense when read in isolation.

**Auto-fix:** No. Link text requires human judgment.

**Manual fix:** Replace vague text with something descriptive. Change "click here to download the report" to "download the annual report (PDF)".

### "Why did my document get longer after fix?"

When body text is below 18pt, raising it to the ACB minimum increases line count. A 16pt newsletter will get notably longer after fix. Fix Results warns when this condition is detected so the pagination change is expected rather than surprising.

### "I turned heading detection off. Why did my score still change?"

When **Detect and convert faux headings** is unchecked, the post-fix report suppresses `ACB-FAUX-HEADING` from scoring. Fix Results lists suppressed rules so you know exactly what was excluded.

### "Where are the list indentation controls on the Fix page?"

The List Indentation fields are always visible. They are disabled while **Flush all lists to the left margin** is checked, and enabled when you uncheck it to use custom indents.

### "ePub should include accessibility metadata" (EPUB-ACCESSIBILITY-METADATA)

**Why it matters:** Accessibility metadata tells reading systems and library catalogs what features the publication offers, so users know whether it works with their assistive technology.

**Manual fix:** Add schema.org metadata to the OPF package document: `accessMode`, `accessibilityFeature`, `accessibilitySummary`, and `accessibilityHazard`. See the [DAISY Knowledge Base on schema.org metadata](https://kb.daisy.org/publishing/docs/metadata/schema.org/index.html).

---

## 15. Tips by Document Format

### Word (.docx)

- Use Word's built-in heading styles (Heading 1, Heading 2, etc.) instead of manually formatting text to look like a heading.
- Use real bulleted and numbered lists (Home, Bullets or Numbering), not manually typed dashes or numbers.
- Set the document title in File, Properties, Title.
- Set the document language in Review, Language.
- For emphasis, use underline -- never italic, and avoid bold in body text.
- After using Fix, always re-audit to catch any remaining manual-fix items.

### Excel (.xlsx)

- Give every sheet a meaningful name. "Sheet1" tells a screen reader user nothing.
- Use **Format as Table** so each column has a proper header row.
- Avoid merged cells. They confuse screen readers navigating the grid.
- Add alt text to any embedded images or charts.
- Do not rely on color alone to convey information.

### PowerPoint (.pptx)

- Every slide must have a unique title.
- Check reading order in the Selection Pane (View, Selection Pane). Objects are read bottom-to-top, so the title should appear at the bottom of the pane's list.
- Add alt text to every image, chart, and SmartArt graphic.
- Use slide layouts with built-in placeholders rather than manually placed text boxes.
- Add speaker notes for slides where the content is primarily visual.
- Avoid auto-advance timings under 5 seconds and repeating or rapidly triggered animation sequences. These prevent users from reading slide content in their own time and can cause discomfort for users with vestibular disorders.

### Markdown (.md)

- Use ATX-style headings (`# Heading 1`) not Setext-style (underlines).
- Never use italic (`*text*`). Use `<u>text</u>` for emphasis instead.
- Write descriptive link text: `[download the annual report](url)` not `[click here](url)`.
- Add alt text to all images: `![Description of the chart](chart.png)`.
- Do not leave blank lines between list items.
- Avoid bare URLs. Wrap them in link syntax.

### PDF (.pdf)

- PDFs must be tagged for accessibility. Scanned documents without OCR fail most checks.
- Set document title and language in the PDF properties.
- Use bookmarks for navigation in long documents.
- The best approach for PDFs: fix the source document (usually Word) and re-export. Remediating a PDF directly is slower and more error-prone.

### ePub (.epub)

- Include a navigation document (table of contents). This is required by EPUB Accessibility 1.1.
- Add schema.org accessibility metadata to the OPF file.
- Ensure all images have alt text in the content documents.
- Use proper heading levels (h1 through h6) without skipping.
- GLOW ePub audits include DAISY Ace, which runs 100+ axe-core checks beyond basic structural rules.
- When your ePub includes schema.org accessibility metadata, the audit report shows a human-readable Accessibility Metadata section describing how the publication can be read, conformance claims, navigation features, and hazards. This follows the W3C Accessibility Metadata Display Guide 2.0.
- If your ePub contains MathML, the audit detects it and provides specific guidance for mathematical content accessibility.

---

## 16. Recommended Workflows

### Workflow A: Fix an existing document (streamlined)

1. **Audit first** -- upload to Audit to understand the scope of issues.
2. **Fix directly** -- from the audit report, click **Fix This Document** or **Fix These Auto-Fixable Issues**. Your document loads into Fix automatically -- no re-upload required.
3. **Re-Audit directly** -- after the fix, click **Re-Audit Fixed Document** on the Fix result page. The fixed document is audited immediately -- no re-upload required.
4. **Manual fixes** -- open the fixed document and address remaining items from the re-audit report.
5. **Publish** -- use Convert to produce accessible HTML, distribute the corrected Word file, or convert to PDF.

The entire Audit → Fix → Re-Audit cycle requires uploading the document only once.

### Workflow B: Start a new document from scratch

1. **Create a template** -- use Template to generate a pre-configured .dotx file.
2. **Write in the template** -- use the built-in styles for all formatting. No fixing needed.
3. **Quick audit when done** -- upload to Audit with Quick Audit mode before publishing.

### Workflow C: Publish meeting minutes or agendas online

1. Write content in Markdown or Word.
2. Audit to check compliance.
3. Fix if the source is Word and has issues.
4. Convert to accessible HTML using the Accessible web page option (or CMS Fragment for WordPress/Drupal).
5. Upload the HTML file to your website.

### Workflow D: Transcribe a recorded meeting and publish

1. Go to **BITS Whisperer** and upload the audio file.
2. Download the Markdown transcript.
3. Edit the transcript -- fix proper nouns, add headings, clean up structure.
4. Audit the Markdown.
5. Convert to accessible HTML or Word.
6. Publish or distribute.

### Workflow E: Produce large print PDF for distribution

1. Write content in Markdown or Word.
2. Audit to check compliance.
3. Fix if needed (for Word documents).
4. Convert to PDF with Accessible PDF selected. Enable Binding margin if the document will be printed and bound.
5. Distribute for printing.

### Workflow F: Create accessible EPUB publications

1. Start with a properly formatted Word document or Markdown file.
2. Audit the source document.
3. Convert to EPUB -- use EPUB 3 via Pandoc for a quick e-book, or DAISY Pipeline for production-quality EPUB with full accessibility metadata.
4. Audit the EPUB -- DAISY Ace runs automatically.
5. Fix any EPUB-specific issues (metadata, alt text, navigation) and re-audit.

### Workflow G: Understand a complex document before remediating it

1. Go to **Document Chat** and upload the document.
2. Ask "Run an accessibility summary and tell me the top five issues."
3. Follow up with "What is auto-fixable versus what needs manual work?"
4. Ask "Estimate my score after running Fix."
5. Export the chat session as your audit planning document.
6. Proceed to Fix based on what you learned.

### Workflow H: Rapid compliance pass on a known document

Use this when you have a document you have worked on before and want a fast pass to confirm it still meets standards before publishing.

1. Go to **Audit** and upload the document.
2. Select **Quick Audit** (Critical and High findings only).
3. On the report, check the Quick Wins bar -- if there are auto-fixable issues, click **Fix These Auto-Fixable Issues** to proceed directly to Fix with your document pre-loaded.
4. On the Fix page, run Fix. Then click **Re-Audit Fixed Document** to confirm the score.
5. If the re-audit shows only Medium or Low findings, the document is ready to publish.

---

## 17. DAISY Accessibility Tools

GLOW integrates with open source tools from the [DAISY Consortium](https://daisy.org/), an international association serving people with print disabilities.

### DAISY Ace -- EPUB Accessibility Checker

[Ace by DAISY](https://daisy.github.io/ace/) is bundled with the web application and runs automatically during every ePub audit:

- All axe-core HTML accessibility rules (contrast, ARIA, landmarks, tables, forms)
- EPUB-specific metadata validation (accessibility metadata, package structure)
- Content document structure checks (headings, images, links)
- Findings linked to the DAISY Knowledge Base for remediation guidance

### DAISY Pipeline -- Document Conversion

[DAISY Pipeline](https://daisy.github.io/pipeline/) performs format conversions optimized for accessible publishing. When installed on the server, the Convert page gains:

- Word (.docx) to EPUB 3
- HTML to EPUB 3
- EPUB to DAISY 2.02 talking book format
- EPUB 2 to EPUB 3 upgrade

### DAISY Knowledge Base

The [Accessible Publishing Knowledge Base](https://kb.daisy.org/publishing/) provides the help links throughout audit reports. Every ePub-related finding links to a specific Knowledge Base article with detailed remediation guidance.

### MathML and Mathematical Content

When ePub files contain MathML, the audit detects it and provides guidance on making mathematical content accessible. The [MathCAT project](https://github.com/daisy/MathCAT) by DAISY generates speech, braille, and navigation from MathML for screen readers. If your ePub uses MathML, ensure it is properly structured so MathCAT and MathJax can process it.

---

## 18. Keyboard and Screen Reader Tips

GLOW is designed to work fully without a mouse.

- **Skip link:** Press Tab on any page to reveal a "Skip to main content" link that jumps past the sidebar navigation.
- **Sidebar navigation:** The left sidebar is a `<nav>` landmark with `aria-label="Primary navigation"`. Links are organised in five labelled groups. Use Tab and Enter to move between pages. The active page link carries `aria-current="page"`.
- **Mobile sidebar:** On small screens, the sidebar is hidden until the hamburger button is pressed. Press Escape or click the overlay to close. Focus is trapped inside the sidebar while it is open, and returns to the toggle button when closed.
- **Forms:** All form fields have visible labels and description text. Errors are announced with the alert role.
- **Help sections:** Help text uses `<details>/<summary>` elements. Press Enter or Space on a summary to expand or collapse. Screen readers announce the expanded and collapsed state.
- **File upload:** After selecting a file, Tab to the submit button and press Enter.
- **Submit feedback:** Every form disables its submit button and announces a status message via `aria-live` when submitted. This confirms your action and prevents accidental double-submission.
- **Severity badges:** Severity levels are shown as colored badges in audit reports. The text is always present (not color-only), so screen readers announce "Critical", "High", etc.
- **Help links:** External help links open in new tabs and are announced as such.
- **Back to top:** Each section on the Guidelines and Guide pages includes a "Back to table of contents" link.

---

## 19. Frequently Asked Questions

### Is my document stored on the server?

Uploaded files are stored in an isolated temporary workspace for the time needed to complete your workflow. Temporary files are automatically removed. Nothing is retained as permanent account data. Upload workspaces are removed after one hour of inactivity. Active sessions stay alive as long as the session is in use.

### What is the maximum file size?

500 MB. If your document is larger, try compressing images within the document first (Word: File, Compress Pictures).

### Can I audit multiple documents at once?

The web tool supports batch mode for up to three files at once. For larger batch processing, use the desktop application, which supports folder-level audits with the `--jobs N` flag for parallel processing.

### Why does Fix not change my headings?

Heading detection must be explicitly enabled. Check **Detect and convert faux headings** on the Fix form. If false positives are common (names, times, short labels), switch to Conservative accuracy mode. If real headings are being missed, switch to Thorough.

For heading level corrections (changing an H3 to an H2), Fix corrects heading formatting but does not reassign heading levels. Use the audit report to identify the hierarchy problem and restructure manually.

### Can I limit heading review to certain levels?

Yes. Use the **Allowed heading levels** checkboxes in the Fix form, or set defaults in Settings. The review page will only show your selected levels in each candidate dropdown.

### Why did a decorative image get flagged?

Use Word's **Mark as decorative** option for non-informational images. GLOW treats legacy Word VML shapes with `alt=""` as decorative. Images without decorative intent or meaningful alt text are still reported.

### What is the difference between ACB and MSAC rules?

**ACB Large Print** rules come from the American Council of the Blind Board of Publications. They cover visual formatting: font, size, spacing, emphasis, alignment, and margins.

**MS Accessibility Checker (MSAC)** rules align with the Microsoft Office Accessibility Checker and WCAG 2.1. They cover structural accessibility: alt text, table headers, reading order, hyperlink text, document properties.

Both categories work together for comprehensive compliance. Run with both enabled for best results.

### What about DAISY Pipeline conversions?

DAISY Ace is bundled and always runs during ePub audits. DAISY Pipeline (for format conversions like Word to EPUB, EPUB to DAISY 2.02) requires Java and is an optional server component installed by the administrator. Pipeline conversions appear automatically when available.

For the desktop application, install Node.js and Ace (`npm install -g @daisy/ace`) for full ePub audit support.

### Can I use GLOW for documents in languages other than English?

Yes. The ACB formatting rules (font, size, spacing, emphasis) apply regardless of language. Set the document language property (Rule: `ACB-DOC-LANGUAGE`) to the correct language code for proper screen reader pronunciation. BITS Whisperer supports automatic language detection or explicit language selection from 50+ languages.

### Is there a desktop version?

Yes. The GLOW includes a desktop application with a graphical wizard interface, command-line tools, and batch processing support. It runs on Windows without requiring an internet connection. Download from the [project releases page](https://github.com/Community-Access/glow/releases).

### Where can I read the ACB Large Print Guidelines?

The full guidelines are at [acb.org/large-print-guidelines](https://acb.org/large-print-guidelines) (revised May 6, 2025). A reference copy is in the repository at `docs/ACB Large Print Guidelines, revised 5-6-25.docx`. The web app includes a [Guidelines page](https://glow.bits-acb.org/guidelines) with the complete rule reference and audit rule mappings.

APH also publishes research-based large print guidance at [aph.org/resources/large-print-guidelines](https://www.aph.org/resources/large-print-guidelines/).

### Is there an admin area?

Yes. GLOW includes an admin-only sign-in and approval workflow for operational dashboards. Admin features include viewing and managing the audio conversion queue, canceling queued jobs, and re-queuing failed jobs. No general user accounts are supported in the current release. Email configuration is required for admin sign-in features.

---

## 20. Website Accessibility Scans (Site Audit)

Site Audit is designed for page-level accessibility checks when your source is a URL instead of an uploaded document.

Use Site Audit when you need to:

- review one or more live pages for common WCAG-aligned issues
- crawl a section of a site from a seed URL
- generate a portable evidence bundle for engineering handoff

### What each Site Audit option does

- **URLs to scan (one per line)**: seed pages to scan directly
- **Sitemap URL (optional)**: imports URLs from an XML sitemap and adds them to seeds
- **Maximum pages (1 to 50)**: hard cap on total pages scanned in a run
- **Follow in-site links**: discovers additional pages from links found on scanned pages
- **Crawl depth (0 to 5)**:
  - Depth 0: scan seed URLs only
  - Depth 1: include links found on each seed page
  - Depth 2+: continue link discovery across additional levels
- **Include subdomains**: allow discovery across `www`, `docs`, `blog`, and other subdomains
- **Limit crawl to same path branch**: keep discovery within the seed path hierarchy
  - Example: seed `https://example.org/docs` includes `/docs/getting-started` and `/docs/api`, but not `/blog`
- **Exclude URL patterns**: skip URLs containing listed text fragments (one per line)
  - Example patterns: `/tag/`, `?replytocom=`, `/print/`, `/calendar/`
- **Strict open-source learning links only**: for each finding, include only W3C/WAI and A11Y Project guidance links
- **Force re-scan existing pages in this run**: do not reuse existing page outputs for matching URLs
- **Run in background and show live status**: start crawl asynchronously, monitor progress, and cancel if needed
- **Protect run with tokenized link**: require a private token URL; optionally add a password

### Step-by-step walkthrough

1. Open the **Site Audit** tab.
2. Add scan sources.
   - Use one URL per line for focused checks.
   - Add a sitemap URL when you need broad coverage quickly.
3. Choose crawl behavior.
   - Start with **Follow in-site links** enabled.
   - Set **Crawl depth** based on intent:
     - 0 for spot checks
     - 1 for section scans
     - 2 for broad audits with controlled spread
4. Constrain scope to reduce noise.
   - Enable **Limit crawl to same path branch** for section-specific audits.
   - Add **Exclude URL patterns** for low-value or repetitive paths.
5. Set **Maximum pages** to match expected run size and time budget.
6. Click **Run Site Audit**.
7. Review results.
   - Run summary totals (scanned, failed, skipped, findings)
   - Per-page status table
   - WCAG tag rollup
   - Scan configuration block (for reproducibility)
8. Download artifacts for engineering handoff:
   - summary JSON
   - findings CSV
   - session log
   - full ZIP bundle

### Background runs, status, and cancel

When **Run in background** is enabled:

1. GLOW creates a job status page immediately.
2. The status page updates live with crawl progress and page currently being scanned.
3. You can click **Cancel crawl** at any time.
4. Failed or cancelled runs can show **Retry crawl** when retry budget remains.
5. Jobs stop automatically when their configured deadline is reached.
6. When complete, open the result page directly from the job status view.

### Protected private runs

When **Protect run with tokenized link** is enabled:

1. The run is stored with a token-hash (not plaintext token) and optional password hash.
2. Opening the run requires the tokenized URL.
3. If a password was set, users must also unlock with the password.
4. Downloads and summary endpoints honor the same access protection.

This allows teams to share targeted private scan links while keeping results out of reach without the token (and password if configured).

### Recommended run presets

1. **Quick smoke scan**
   - Maximum pages: 5 to 10
   - Follow links: on
   - Crawl depth: 0 or 1
   - Same path only: on
   - Exclusions: optional
2. **Section quality gate (release)**
   - Maximum pages: 25 to 50
   - Follow links: on
   - Crawl depth: 1 or 2
   - Same path only: on
   - Exclusions: recommended
3. **Cross-site discovery scan**
   - Maximum pages: 50
   - Follow links: on
   - Crawl depth: 2
   - Include subdomains: on
   - Same path only: off
   - Exclusions: strongly recommended

### Tips to get the most out of Site Audit

- Start narrow, then widen. Use depth 0 or 1 first, then increase depth if needed.
- Use path scoping plus exclusion patterns together. This removes common crawl traps and duplicate-value pages.
- Keep a reusable exclusion list in your team notes for known low-signal URL patterns.
- Use the findings CSV for triage and assignment, then use summary JSON and session log for traceability.
- Keep Force re-scan off for iterative runs unless content changed and you need fresh evidence.

### Site Audit defaults

You can set default Site Audit options in **Settings**:

- maximum pages per run
- crawl links on/off
- crawl depth default
- include subdomains on/off
- same path branch on/off
- default URL exclusion patterns
- force re-scan on/off

If **Remember my settings** is enabled, these defaults persist in local browser storage.

## 21. Getting Help

- **ACB Large Print Guidelines** -- [acb.org/large-print-guidelines](https://acb.org/large-print-guidelines)
- **APH Large Print Guidelines** -- [aph.org/resources/large-print-guidelines](https://www.aph.org/resources/large-print-guidelines/)
- **Guidelines reference page** -- available in the GLOW web app via the **Guidelines** tab. Includes a deep-dive link to the Rules Reference.
- **Rules Reference page** -- browse every audit rule with severity, WCAG mapping, and fix guidance. Accessible from the bottom of the Guidelines page. 
    *   **Include Shown** / **Exclude Shown**: bulk select or clear rules based on your current filters.
    *   **Toggle Shown**: invert the selection of visible rules.
    *   **Save Changes**: save your current rule selection as your global default for Audit and Fix.
    *   **Undo Changes**: discard unsaved changes and restore your previous rule set.
- **Submit feedback** -- use the Feedback page in the web app to report bugs, request features, or share your experience
- **About page** -- mission, organizations, standards, and open source dependencies
- **GitHub Issues** -- [report bugs or request features](https://github.com/Community-Access/glow/issues)
- **DAISY Knowledge Base** -- [remediation guidance for ePub issues](https://kb.daisy.org/publishing/)
- **Microsoft Accessibility Checker Guide** -- [Microsoft's guide to the Office accessibility checker](https://support.microsoft.com/en-us/office/improve-accessibility-with-the-accessibility-checker-a16f6de0-2f39-4a2b-8bd8-5ad801426c7f)
- **Project overview** -- [About GLOW](/about/)
- **Deployment and operations notes** -- [Deployment Guide](/deployment/)
# GLOW (Guided Layout & Output Workflow) -- User Guide

Everything you need to know to audit, fix, convert, and template your documents for ACB Large Print compliance using **GLOW (Guided Layout & Output Workflow)**. New to accessibility? Start with the **Quick Start** path below.

## In This Guide

1. [Quick Start (Beginner Path)](#1-quick-start-beginner-path)
2. [BITS Whisperer: Transcribe Audio](#2-bits-whisperer-transcribe-audio)
3. [Quick-Start Walkthrough (Expert Path)](#3-quick-start-walkthrough-expert-path)
4. [GLOW v2.5.0 Features](#4-glow-v250-features)
5. [How to Audit a Document](#5-how-to-audit-a-document)
6. [How to Fix a Document](#6-how-to-fix-a-document)
7. [How to Create a Template](#7-how-to-create-a-template)
8. [How to Use Settings](#8-how-to-use-settings)
9. [How to Export to HTML](#9-how-to-export-to-html)
10. [How to Convert Between Formats](#10-how-to-convert-between-formats)
11. [Understanding Your Results](#11-understanding-your-results)
12. [Common Issues and How to Fix Them](#12-common-issues-and-how-to-fix-them)
13. [Tips by Document Format](#13-tips-by-document-format)
14. [Recommended Workflows](#14-recommended-workflows)
15. [DAISY Accessibility Tools](#15-daisy-accessibility-tools)
16. [Keyboard and Screen Reader Tips](#16-keyboard-and-screen-reader-tips)
17. [Frequently Asked Questions](#17-frequently-asked-questions)
18. [Getting Help](#18-getting-help)
19. [Document Chat and Agentic Accessibility Tools](#19-document-chat-and-agentic-accessibility-tools)

**Quick links to v2.5.0 features:**
- [Quick Start Path](#1-quick-start-beginner-path) (for newcomers to accessibility)
- [BITS Whisperer](#2-bits-whisperer-transcribe-audio) (transcribe audio to text)
- [MarkItDown image descriptions](#image-descriptions-llm-generated-alt-text) (AI-powered alt text for images)
- [Document Chat](#19-document-chat-and-agentic-accessibility-tools) (ask accessibility questions in context)

**Quick links to v1.2.0 features:**
- [Quick Rule Exceptions](#quick-rule-exceptions)
- [Preserve centered headings](#preserve-centered-headings)
- [Per-level list indentation](#per-level-list-indentation)
- [Allowed heading levels](#allowed-heading-levels)
- [FAQ page](/faq/) (also accessible from the web app footer)

---

## 1. Quick Start (Beginner Path)

If you're new to GLOW (Guided Layout & Output Workflow) or unsure which tool to use, the **Quick Start** path is for you.

### How to use Quick Start

1. On the GLOW (Guided Layout & Output Workflow) homepage, click **"Quick Start: Upload & Discover"**
2. Upload any document (Word, Excel, PowerPoint, PDF, Markdown, image, audio, or ePub)
3. GLOW (Guided Layout & Output Workflow) will show you **all available actions** for your file type
4. Click the action you want (Audit, Fix, Convert, Template, Export, or BITS Whisperer)
5. Follow the step-by-step form for that action

### What each action does

- **Audit:** Check your document for accessibility issues and get a compliance report
- **Fix:** Auto-fix accessibility problems in Word documents
- **Convert:** Transform your document to Markdown, HTML, PDF, Word, or ePub
- **Export:** Convert Word to accessible HTML with built-in ACB styling
- **Template:** Generate a Word template pre-formatted with ACB styles
- **BITS Whisperer:** Transcribe audio files to Markdown or Word (see next section)

---

## 2. BITS Whisperer: Transcribe Audio

**BITS Whisperer** transcribes audio files into accessible text documents without sending your audio anywhere.

### Supported audio formats

- MP3 (.mp3)
- WAV (.wav)
- M4A (.m4a)
- OGG (.ogg)
- FLAC (.flac)
- AAC (.aac)
- Opus (.opus)

### How to use BITS Whisperer

1. Click the **"BITS Whisperer"** tab at the top, or from Quick Start upload an audio file
2. Upload your audio file (max 500 MB)
3. Review the estimated conversion time shown after file selection
4. Check the confirmation box to acknowledge you want to proceed
5. Optionally select a language (auto-detect is recommended for most recordings)
6. Choose output format: **Markdown** (plain text) or **Word** (editable .docx)
7. Click "Transcribe Audio"
8. Keep the page open while progress updates run. When progress reaches 100%, download starts automatically.

### Optional background mode for long recordings

For recordings estimated at 30 minutes or longer (server-configurable), Whisperer can run in background mode:

1. Enable **Process in background** on the Whisperer form.
2. Enter a notification email address.
3. Create and confirm a retrieval password.
4. Submit the job.

When enabled, GLOW sends lifecycle emails (queued, started, completed). The completed email contains a single-use secure retrieval link. You must use both the link and the retrieval password to download the transcript.

If the transcript is not retrieved within the configured window (default 4 hours after completion), GLOW clears it and sends a final email confirming removal.

### Long recordings and session behavior

- The web app session lifetime defaults to 4 hours (`SESSION_TIMEOUT_MINUTES=240`), which is typically enough for long jobs.
- Active transcription jobs keep their temporary workspace alive while running, so cleanup does not remove in-progress jobs.
- Files are retained for the time required to complete conversion successfully, then removed after download.
- If your browser is closed before download, stale files are still cleaned up by retention policy.

### Audio limits and graceful handling

- Audio file size limit is configurable with `WHISPER_MAX_AUDIO_MB` (default 500 MB).
- Maximum audio length is configurable with `WHISPER_MAX_AUDIO_MINUTES` (default 120 minutes).
- Background queue depth is configurable with `GLOW_MAX_AUDIO_QUEUE_DEPTH` (default 5).
- Background eligibility threshold is configurable with `WHISPER_BACKGROUND_THRESHOLD_MINUTES` (default 30).
- Secure retrieval retention window is configurable with `WHISPER_RETRIEVAL_HOURS` (default 4).
- If a file exceeds limits, GLOW returns a clear message and guidance to split or compress the recording.
- For very long meetings, split audio into smaller segments (for example 20-30 minutes each) for more reliable turnaround and easier review.

### Tips for best results

- **One speaker at a time:** Whisper works best when one person is speaking. Multiple speakers talking at once reduces accuracy.
- **Minimize background noise:** Close the microphone to the speaker. Loud background music, crowd noise, or HVAC hum will reduce accuracy.
- **Specify the language for short clips:** If your audio is under 30 seconds, picking the language explicitly is faster and more accurate than auto-detect.
- **Review the transcript:** Whisper is 95%+ accurate for clear English speech, but technical terms, proper nouns, and accents may need manual correction.
- **Edit in Markdown first:** Download the .md file, review and fix it in any text editor, then use Convert to turn it into an accessible web page, PDF, or Word document. This two-step approach gives you full control.

### Privacy

Your audio file is uploaded to GLOW, optionally normalized for compatibility, sent to the configured Whisper transcription service, and retained only as long as needed to complete conversion and deliver your download. After download or expiry, temporary files are deleted from GLOW. Nothing is stored as permanent account data.

---

## 19. Document Chat and Agentic Accessibility Tools

GLOW (Guided Layout & Output Workflow) 2.5.0 includes a chat experience that lets you interrogate uploaded documents in plain language.

### What Document Chat does

- Reads your uploaded document content
- Uses accessibility-focused tools to answer questions
- Returns grounded, actionable responses
- Tracks history by turn (`Turn 1`, `Turn 2`, and so on)
- Lets you export the session to Markdown, Word, or PDF

### Agent categories and tools available in chat

Document Chat has 24 callable tools across five categories.

1. **Document** (7 tools)
   - `extract_table` -- extract a table by name or index
   - `find_section` -- return a section by heading name
   - `search_text` -- find keyword matches with line numbers
   - `get_document_stats` -- word count, lines, headings, reading time
   - `summarize_section` -- return section text for summary
   - `list_headings` -- show heading hierarchy
   - `get_images` -- list images (vision/scanned path)

2. **Compliance Agent** (4 tools)
   - `run_accessibility_audit` -- full GLOW audit summary with severity counts
   - `get_compliance_score` -- score out of 100 with breakdown
   - `get_critical_findings` -- critical and high severity findings with fix type
   - `get_auto_fixable_findings` -- findings GLOW Fix can correct automatically

3. **Structure Agent** (4 tools)
   - `check_heading_hierarchy` -- detect skipped heading levels
   - `find_faux_headings` -- find bold body paragraphs acting as headings
   - `check_list_structure` -- inspect list nesting and consistency
   - `estimate_reading_order` -- reading-order risk from tables and layout signals

4. **Content Agent** (4 tools)
   - `check_emphasis_patterns` -- detect italic and bold-abuse violations
   - `check_link_text` -- flag bare URLs and generic link phrases
   - `check_reading_level` -- sentence and word complexity estimate
   - `check_alignment_hints` -- detect center/right alignment overrides

5. **Remediation Agent** (5 tools)
   - `explain_rule` -- plain-language explanation and fix steps for any ACB rule ID
   - `suggest_fix` -- targeted fix instructions for a rule
   - `prioritize_findings` -- rank all findings by severity and auto-fixability
   - `estimate_fix_impact` -- score improvement estimate after auto-fix
   - `check_image_alt_text` -- check images for missing or empty alt text

### Guided question cards (recommended starter prompts)

Use these prompts directly in chat:

- "Run an accessibility summary and tell me the top 5 issues."
- "List critical findings only and explain why each matters."
- "Show me where heading hierarchy is broken."
- "Find faux headings and suggest the correct heading level."
- "Are there any ambiguous links like 'click here' or bare URLs?"
- "Check emphasis patterns and flag italic usage."
- "What is auto-fixable versus manual-fix in this document?"
- "Prioritize fixes by impact and effort."
- "Explain rule ACB-LINK-TEXT in plain language."
- "Summarize Section 3 for a board-ready update."

### Best practices for high-quality answers

- Ask one question at a time.
- Reference section names when possible.
- Ask for "critical only" when triaging quickly.
- Follow with "show evidence" to get concrete lines/sections.
- Export the session when done for audit trail and team handoff.

### Accessibility behavior

- Conversation history is structured with heading-based turns for screen-reader navigation.
- All controls are keyboard accessible.
- Help content uses native `<details>/<summary>` patterns.
- No JavaScript is required for core chat usage.

### Privacy and retention

- Chat runs through GLOW's configured AI gateway in supported deployments.
- Conversation data stays in session storage.
- Session and uploaded content follow the 1-hour retention policy.

---

## 3. Quick-Start Walkthrough (Expert Path)

Tip: First-time users should use Full Audit mode to see everything. You can switch to Quick Audit later once you know what to look for.

### Step 2: Fix what you can automatically

Go to Fix and upload the same file. For Word documents, the tool automatically corrects fonts, sizes, spacing, alignment, and emphasis. You download a fixed copy -- your original stays untouched.

Tip: Not all issues can be auto-fixed. The fix report tells you exactly which issues need your manual attention and how to fix them step by step.

### Step 3: Re-audit to confirm

Upload the fixed document back to Audit to confirm all auto-fixable issues are resolved. Address any remaining manual items from the report.

Tip: A perfect score means zero Critical and High findings. Medium and Low findings are best practices -- good to fix but not blocking.

### Starting from scratch?

If you have not written your document yet, start with Create a Template. This gives you a Word document with all ACB styles pre-configured. Write your content in the template and it will be compliant from the start -- no fixing needed.

---

## 4. GLOW v2.5.0 Features and APH Submission Track

This section is the guided APH rollout workflow, written as an "instructor in your pocket" checklist. Follow each week in order and collect evidence at each gate.

### Week-by-week execution

1. **Week 1 -- Mapping and acceptance criteria**
   - Build the APH mapping matrix from current ACB + WCAG rules.
   - Define required submission artifacts and review criteria.
2. **Week 2 -- Core profile implementation**
   - Add standards profile metadata and profile applicability in canonical constants.
   - Sync the same rule semantics across Python core and Office add-in.
3. **Week 3 -- UI and reporting updates**
   - Add standards profile controls in web workflows.
   - Add standards source visibility in reports (ACB/WCAG/APH scope clarity).
4. **Week 4 -- Validation and package assembly**
   - Run full parity and regression validation.
   - Produce the APH submission package (summary, matrix, evidence, known limitations).

### Documentation strategy update

The APH workflow is now embedded directly across the site, this user guide, and the guidelines reference. This replaces reliance on a standalone distribution document and keeps guidance versioned with code.

### Week outputs

- **Week 1 output:** approved APH rule/evidence mapping table
- **Week 2 output:** merged profile-aware constants and synchronization checks
- **Week 3 output:** released profile UX/report updates with accessibility review
- **Week 4 output:** final submission bundle and release notes for 1.2.0

### Standards profiles explained (ACB, APH, Combined Strict)

Release 1.2.0 adds profile selection in Audit, Fix, and Template so teams can choose the right reporting lens and template defaults without changing the underlying remediation engine.

- **ACB 2025 Baseline (default):** no impact to existing users. Selecting ACB keeps current behavior, current scoring assumptions, and the same operational workflow chapters already use.
- **APH Submission:** uses the APH-aligned checks and defaults finalized in Release 1.2.0 for submission readiness and evidence packaging.
- **Combined Strict:** includes all currently implemented checks (ACB + MSAC/WCAG-aligned rules) for maximum strictness.

When to use each:

1. Use **ACB 2025 Baseline** for day-to-day production and continuity.
2. Use **APH Submission** when preparing APH rollout evidence and review packets.
3. Use **Combined Strict** for final pre-release quality gates.

Important: Profile selection changes report filtering in Audit/Fix and template defaults in Template. It does not alter the core fixed behavior for Word auto-fix.

### APH source review findings (DOCX + PDF + APHont package)

The APH source documents were reviewed directly (not only the landing page). Key findings used for integration planning:

- APH confirms the core large-print sizing pattern: 18 body, 20 subheading, 22 heading.
- APH recommends sans-serif fonts and provides APHont for low-vision document production.
- APH includes line-spacing/line-length and color palette guidance that goes beyond the currently enforced ACB/WCAG/MSAC rules.

Font package review result:

- APHont ZIP includes TTF variants for Regular, Bold, Italic, and BoldItalic.
- Integration should ignore packaging metadata artifacts (for example `__MACOSX` entries) and use only the actual font files.

Integration approach:

- Keep Arial as default for current ACB workflows.
- Add APHont as an optional profile-specific target as APH parity expands.
- Add fallback behavior and explicit status reporting when APHont is not available in runtime environments.

---

## 3. How to Audit a Document

### Supported formats

- **Word (.docx)** -- full ACB + WCAG rule set (fonts, sizes, spacing, emphasis, headings, margins, document properties)
- **Excel (.xlsx)** -- sheet names, table headers, merged cells, alt text, color-only data, hyperlink text
- **PowerPoint (.pptx)** -- slide titles, reading order, alt text, font sizes, speaker notes, chart descriptions
- **Markdown (.md)** -- heading hierarchy, emphasis violations, link text, alt text, emoji, em-dashes, tables
- **PDF (.pdf)** -- title, language, tagging, font sizes, font families, scanned pages, bookmarks
- **ePub (.epub)** -- title, language, navigation, heading hierarchy, alt text, table headers, accessibility metadata, link text, MathML detection. Includes comprehensive DAISY Ace checks (100+ axe-core rules).

### Choosing an audit mode

- **Full Audit** (recommended for first use) -- Checks every rule applicable to your file type. Gives you the complete picture. Use this until you know your document's common issues.
- **Quick Audit** -- Checks only Critical and High severity rules. Use this for a fast pass when you are already familiar with your document's formatting.
- **Custom Audit** -- Pick individual rules to check. Useful when you are working on specific issues (e.g., only font rules) or running a targeted re-check.

### Step-by-step

1. Go to Audit.
2. Choose your rule categories (ACB Large Print, MS Accessibility Checker, or both).
3. Select an audit mode.
4. Upload your file (500 MB maximum).
5. Optionally check **Email me the report and findings CSV** and enter your address (only shown when email delivery is configured for this instance).
6. Click Run Audit.
7. Review the report. Each finding shows the rule ID, severity, location in the document, and a description of what is wrong.

Tip: The audit report groups findings by severity. Tackle Critical issues first -- these make the document unreadable for low-vision users. Then work down through High, Medium, and Low.

### Email delivery

When email delivery is enabled on the server, an optional **Email Report** section appears on the audit form. Check the box and enter your email address to receive the scorecard and a findings CSV attachment immediately after the audit completes. The CSV opens in Excel or any spreadsheet application and includes every finding with its rule ID, severity, WCAG criterion, and whether it can be auto-fixed. Your email address is used only to send this report and is never stored.

---

## 4. How to Fix a Document

### What gets auto-fixed

| Format | Auto-Fix Level | What Is Corrected |
|--------|---------------|-------------------|
| Word (.docx) | Full auto-fix | Fonts to Arial, sizes to 18pt/22pt/20pt, italic removed, bold emphasis to underline, flush-left alignment, line spacing, margins, widow/orphan control, hyphenation off, language set |
| Markdown (.md) | Partial auto-fix | Heading hierarchy correction, italic removal, em-dash replacement |
| Excel, PowerPoint, PDF, ePub | Audit only | You receive a detailed report with manual fix guidance for each finding |

### Step-by-step

1. Go to Fix.
2. Upload your document.
3. Choose a fix mode (Full, Essentials, or Custom).
4. Click Fix Document.
5. For Word and Markdown: download the corrected file. Your original is untouched.
6. For other formats: review the audit report with step-by-step manual fix instructions.

Tip: The fix mode controls what appears in the report, not what gets corrected. Your Word document always receives all available auto-fixes regardless of mode.

### Recent Fix workflow updates

- If you uncheck **Detect and convert faux headings**, `ACB-FAUX-HEADING` is now suppressed from post-fix scoring so you are not penalized for a rule you intentionally disabled.
- Fix Results now shows a page-growth warning when your source appears to use body text below 18pt, since normalization to the ACB minimum can increase page count.
- List indentation controls are always visible under **List Indentation** and are disabled while **Flush all lists to the left margin** is checked.
- Legacy Word VML shapes with `alt=""` are treated as decorative and no longer trigger missing-alt findings.

### Quick Rule Exceptions

On the Fix and Audit forms, a new **Quick Rule Exceptions** section lets you suppress specific findings per operation without changing your default settings. This is useful when you want to ignore certain rules for one document without affecting your usual workflow.

**Available exceptions:**

- **Suppress ambiguous link text** (`ACB-LINK-TEXT`) -- ignore links that are not descriptive (e.g., "click here", "more info", "read more"). Use this when you know your links are contextually clear or when you are gathering feedback and do not want link-text errors to distract from other issues.
- **Suppress missing alt text** (`ACB-MISSING-ALT-TEXT`) -- ignore images without alt text. Use this when you are working on structural issues first and will add alt text in a later pass.
- **Suppress faux heading detection** (`ACB-FAUX-HEADING`) -- ignore bold, large text that looks like headings but are not styled as heading styles. Use this when you intentionally want to preserve visual "pseudo-headings" for design reasons and do not want them flagged.

**How to use:**

1. On the Fix or Audit form, expand the **Quick Rule Exceptions** section.
2. Check the rules you want to suppress for this operation only.
3. Submit the form normally.
4. The audit/fix results will not include findings for the suppressed rules, and a note will appear showing which rules were suppressed and why.

### Preserve centered headings

By default, the fixer normalizes all paragraph alignment to flush-left (ragged-right) per ACB requirements. However, you may want to preserve intentional heading center-alignment for design reasons.

The **Preserve centered headings** option on the Fix form skips alignment override for paragraphs identified as headings (those using Heading 1 through Heading 6 styles). Non-heading paragraphs are still normalized to flush-left.

**How to use:**

1. On the Fix form, find the **Heading Alignment Handling** option.
2. Check **Preserve centered headings** to leave heading alignment unchanged.
3. Uncheck it (default) to normalize all paragraphs including headings to flush-left.
4. Submit the form. Headings will retain their original alignment if the option is enabled.

### Per-level list indentation

By default, the fixer applies a uniform left indent to all list items regardless of their nesting depth. The new **Per-level list indentation** option lets you specify different indent values for Level 1, Level 2, and Level 3 list items.

This is useful when:
- Your document has multiple indentation levels and you want each level to use a specific indent value
- You want tighter spacing for nested lists (e.g., Level 1 at 0.25", Level 2 at 0.50", Level 3 at 0.75")
- You are working with bulleted or numbered lists that need consistent per-depth formatting

**How to use:**

1. On the Fix form, find the **List Indentation** section.
2. Check **Use per-level list indentation**.
3. Uncheck **Flush all lists to the left margin** if it is checked (the two options work together).
4. Enter indent values (in inches) for Level 1, Level 2, and Level 3.
5. Submit the form. The auditor and fixer apply per-level indents based on the paragraph's detected list style level.

Tip: Leave a level blank or set it to 0 if your document does not have that depth.

### Allowed heading levels

You can now restrict heading conversion and review to a selected subset of heading levels (for example, only Heading 1 through Heading 3, or include deeper levels when the document uses them).

This is useful when:
- Your publication style intentionally uses only part of the heading ladder.
- You want review options to match your editorial policy.
- You want heading detection, review, and template sample content to stay aligned.

**How to use in Fix:**

1. In the **Heading Detection** section, select only the heading levels your workflow allows.
2. Run Fix as normal.
3. On the heading review page, only those allowed heading levels appear in the dropdown.
4. Confirm and apply; out-of-range suggestions are mapped to the nearest allowed level.

**How to set defaults:**

1. Open **Settings**.
2. Under **Fix Defaults**, choose allowed heading levels for review and conversion.
3. Under **Template Defaults**, choose allowed heading levels for sample content.
4. Save with cookie opt-in enabled.

### Heading Detection (Word documents)

Many Word documents use bold, large text to simulate headings instead of using real heading styles (Heading 1, Heading 2, Heading 3). This causes accessibility problems because screen readers cannot navigate by headings, and the document has no logical structure.

The fixer can detect these "faux headings" and convert them to proper heading styles automatically.

**How it works:**

1. **Heuristic detection** -- The tool scores each paragraph on 10 signals: font size, bold formatting, short length, capitalization patterns, position in the document, and more. Paragraphs scoring above the confidence threshold (default 50 out of 100) are identified as likely headings.

2. **AI refinement (optional)** -- If AI-assisted heading refinement is enabled in your deployment, the tool can send borderline candidates for a second opinion. The AI considers surrounding context to improve accuracy.

3. **Heading level assignment** -- Detected headings can be assigned across Heading 1 through Heading 6 based on font size, document position, and the heading levels enabled for the run. Heading 1 is typically the first primary heading; deeper levels are normalized to the lower-level subheading pattern when selected.

### Heading detection accuracy modes

To balance speed and precision, the Fix workflow supports three accuracy modes:

- **Conservative** -- Heuristics-only with stricter filtering. Best when you want to minimize false positives such as names, times, or single-word labels (for example, "Agenda").
- **Balanced** (default) -- Heuristics plus optional AI refinement (when enabled). Best for most documents.
- **Thorough** -- More inclusive candidate capture with AI refinement when available. Best when you want to catch subtle headings and are willing to review more candidates.

Practical guidance:

- If names, times, or short labels are being flagged too often, switch to **Conservative**.
- If true headings are being missed, switch to **Thorough**.
- Keep **Balanced** for routine office documents.

**Using heading detection on the web:**

1. On the Fix page, check "Detect and convert faux headings to real heading styles."
2. Optionally check "Refine with AI" if that feature is enabled in your deployment.
3. Adjust the confidence threshold if needed (higher means fewer but more certain conversions).
4. Choose a heading detection accuracy level:
   - Conservative (fewer false positives)
   - Balanced (recommended default)
   - Thorough (captures more candidates)
5. Click Fix Document.
5. If candidates are found, you are taken to an **interactive heading review page**. This page shows a table listing every detected heading candidate with:
   - The paragraph text along with font size and bold/caps formatting info
   - The heuristic signals that fired and their point values
   - A confidence score and confidence level (High or Medium)
   - A heading level dropdown (H1 through H6) pre-set to the suggested level, plus a "Skip" option to exclude a candidate
   - If AI was used, the AI's reasoning is shown alongside the heuristic signals
6. Review each candidate. Change heading levels or set any false positives to "Skip."
7. Click "Apply Selections and Fix" to proceed. The confirmed headings are converted to real heading styles, then the normal fix pipeline runs.
8. The fix report details section shows every heading that was converted.

If no candidates are found above the confidence threshold, the fix proceeds directly without the review step.

**Using heading detection on the desktop GUI:**

1. Open the GLOW desktop application.
2. In the fix wizard (Step 3: Options), look for the Heading Detection section.
3. Check "Detect and convert faux headings to real heading styles."
4. Check "Refine with AI" if that feature is enabled in your deployment.
5. Adjust the confidence threshold using the slider or spin control.
6. Complete the wizard to run the fix. Detected headings are converted before other fixes are applied.

**Using heading detection on the CLI:**

```shell
# Heuristic only
acb-lp fix document.docx --detect-headings

# With AI refinement
acb-lp fix document.docx --detect-headings --ai

# Standalone detection (report only, no fix)
acb-lp detect-headings document.docx

# With custom prompt file and threshold
acb-lp detect-headings document.docx --ai --ai-prompt my-prompt.txt --threshold 75
```

### Stress Testing and Product Learning

### How We Tested This Feature And What We Learned

We did not rely on a few hand-made examples. We built a synthetic Word-document stress harness to imitate the kinds of files people actually upload.

What the test set included:

- Meeting agendas
- Policy manuals
- Newsletters
- Legal outlines
- Appendices and flyers
- Email-style content
- Plain-text paste with no heading styles
- Mixed-font and font-size drift
- Centered and justified text that had to be repaired
- Multilingual section labels and numbering patterns

What those 1,000 documents were meant to represent in everyday use:

- A meeting agenda someone pasted out of email
- A newsletter copied from a website with mixed fonts and centered headings
- A policy manual built from older templates with indentation drift
- A legal-outline document with numbering that has to stay structurally correct
- A training handout where short prompts may or may not be real headings
- An appendix or report supplement with short labels, notes, and reference items

In other words, the documents were designed to behave like realistic user uploads, not toy examples. Each one placed the potential heading inside a fuller document context so the platform had to make a realistic decision and then repair the result to match ACB rules.

What we measured:

1. Whether the detector found real headings
2. Whether it avoided common false positives
3. Whether the fixer converted those headings cleanly
4. Whether the repaired document passed ACB audit rules afterward

What we learned:

1. Short lines are not automatically headings. Signature lines, reminders, and similar short phrases must be treated carefully.
2. Real documents often combine several problems at once. A heading may be visually strong while the surrounding document still has bad alignment, bad indentation, or font drift.
3. Heading detection and ACB enforcement are connected. A heading can be detected correctly and still need further cleanup so the final document does not violate rules such as no ALL CAPS or no skipped heading levels.

How the platform changed because of those lessons:

- We strengthened false-positive handling for signature-like and callout-style text.
- We expanded the random corpus to include plain-text/no-style negatives, font-only heading cues, and multilingual variants.
- We added a heading-normalization pass in the fixer so converted headings are cleaned up after detection, including heading hierarchy repair and ALL CAPS cleanup.

What the latest validation showed:

- Full heading stress suite passed
- Larger randomized comparisons showed zero false positives and zero false negatives in the measured runs
- Full fix-then-audit validation showed zero remaining ACB findings across the 1,000-document corpus after the latest fixes

---

## 5. How to Create a Template

A template (.dotx) is the easiest way to start compliant. Every new document you create from this template inherits all ACB formatting automatically.

### Step-by-step

1. Go to Template.
2. Enter a document title (or leave blank for the default).
3. Optionally check "Include sample content" if you want to see examples of correct formatting.
4. Check "Add binding margin" if the document will be printed and bound.
5. Click Create Template and save the downloaded .dotx file.
6. In Word, double-click the .dotx file to create a new document based on it.

### Template profile defaults

Template now supports standards profiles:

- **ACB 2025 Baseline:** keeps the current production defaults (Arial + existing ACB spacing baseline).
- **APH Submission:** uses APH-oriented defaults (APHont preferred and 1.25 line spacing recommendation).
- **Combined Strict:** keeps ACB template defaults while teams use strict combined review posture in Audit/Fix.

If your team repeatedly uses the same template profile and options, configure them once in **Settings** so Template opens pre-filled each visit.

### Template heading-level defaults

Template sample content can now follow your selected heading-level subset.

1. In Template, choose **Allowed Heading Levels for Sample Content**.
2. If sample content is enabled, generated example headings will only use selected levels.
3. You can persist this in **Settings** under Template defaults.

### How to install the template in Word

1. Save the downloaded .dotx file to your Templates folder:
   - **Windows:** `%APPDATA%\Microsoft\Templates`
   - **macOS:** `~/Library/Group Containers/UBF8T346G9.Office/User Content/Templates`
2. In Word, go to File, New, Personal (or Custom on Mac).
3. Select the ACB Large Print template.
4. Start writing. All styles are already configured.

---

## 6. How to Use Settings

The **Settings** tab lets you set default values once and apply them across every workflow.

### What Settings controls

- Standards profile defaults for **Audit**, **Fix**, and **Template**.
- Audit defaults: mode, categories, and quick-rule suppressions.
- Fix defaults: mode, categories, heading options, list and paragraph indentation options, and suppressions.
- Template defaults: profile, sample content, binding margin, and allowed heading levels for sample content.
- Export and Convert defaults.

### Privacy and persistence

- Settings are saved only when you enable cookie opt-in.
- Settings stay on the current browser/device only.
- Turning opt-in off removes saved settings and returns GLOW to built-in defaults.

### Recommended setup flow

1. Open **Settings**.
2. Enable cookie opt-in.
3. Set your preferred defaults for each workflow.
4. Save.
5. Open Audit/Fix/Template/Export/Convert and verify defaults are pre-selected.

---

## 7. How to Export to HTML

Export converts a Word document to a web page with ACB-compliant CSS already applied. Choose between two output modes:

- **Standalone HTML** -- A complete web page with its own CSS file. Upload both files to your web server. Good for dedicated pages, intranet publishing, or email attachments.
- **CMS Fragment** -- An HTML snippet with embedded CSS scoped to a wrapper class. Paste it into WordPress, Drupal, or any CMS editor block. The scoped CSS will not conflict with your site theme.

### Step-by-step

1. Go to Export.
2. Upload a Word (.docx) file.
3. Optionally set a page title.
4. Choose Standalone or CMS Fragment.
5. Click Export and download your result.

Tip: If your source is Markdown instead of Word, use Convert with the "Accessible web page" option instead.

---

## 8. How to Convert Between Formats

The Convert page offers six conversion directions, each powered by a different engine. Choose the one that matches what you need to produce.

### To Markdown (plain text extraction)

**Powered by:** [Microsoft MarkItDown](https://github.com/microsoft/markitdown)

Extracts readable text from any supported file. Good for feeding documents into AI tools, creating starting points for documentation, or getting a simple version you can search and copy-paste. MarkItDown handles the widest range of input formats but produces plain text, not a finished web page.

**Accepts:** Word (.docx), Excel (.xlsx, .xls), PowerPoint (.pptx), PDF (.pdf), HTML, CSV, JSON, XML, ePub (.epub), and ZIP files.

**You get back:** a `.md` (Markdown) file -- plain text with formatting marks for headings, lists, and links. Opens in any text editor.

**Best when:** you need the raw content out of a document, regardless of its original format. Also the right first step if you plan to convert to HTML, Word, EPUB, or PDF later -- extract to Markdown, clean up the result, then convert from there.

### To accessible web page (HTML)

**Powered by:** [Pandoc](https://pandoc.org/) (John MacFarlane, UC Berkeley)

Turns a document into a complete, accessible HTML page with ACB Large Print CSS built in. Pandoc is the gold standard for document-to-HTML conversion -- it understands heading hierarchy, semantic lists, tables, footnotes, and cross-references, and produces clean, well-structured HTML. We embed our ACB Large Print CSS so the output meets accessibility standards out of the box.

**Accepts:** Markdown (.md), Word (.docx), reStructuredText (.rst), OpenDocument (.odt), Rich Text (.rtf), and ePub (.epub).

**You get back:** a standalone `.html` web page with all accessibility formatting included -- Arial font, large text, proper spacing, high contrast, and all other ACB requirements.

**Options:**

- **ACB formatting** (on by default) -- applies the full ACB Large Print stylesheet
- **Binding margin** -- shifts content right by 0.5 inches for printed/bound documents
- **Print stylesheet** -- adds `@media print` rules for ACB's tighter print line-height (1.15 instead of 1.5)

**Best when:** you need a web page that people will read in a browser, print on paper, email as an attachment, or upload to a website. Markdown (.md) files produce the cleanest output because Pandoc was specifically designed for Markdown-to-HTML conversion.

### To Word document (.docx)

**Powered by:** [Pandoc](https://pandoc.org/) (John MacFarlane, UC Berkeley)

Converts a document into a Word file. Pandoc maps headings, lists, tables, and emphasis into Word's native styles, so the output is immediately editable in Microsoft Word.

**Accepts:** Markdown (.md), reStructuredText (.rst), OpenDocument (.odt), Rich Text (.rtf), HTML (.html), and ePub (.epub).

**You get back:** a `.docx` file that opens directly in Microsoft Word or LibreOffice Writer.

**Best when:** you have a Markdown or HTML document and need a Word version for colleagues who work in Word, or when you want to run GLOW's audit and auto-fix on content that started in another format. A common workflow: extract to Markdown, clean up, convert to Word, then run Fix for full ACB compliance.

### To EPUB 3 e-book (via Pandoc)

**Powered by:** [Pandoc](https://pandoc.org/) (John MacFarlane, UC Berkeley)

Creates a lightweight EPUB 3 e-book with ACB Large Print CSS embedded in the stylesheet. Pandoc generates proper EPUB structure including a navigation document, content documents with semantic markup, and EPUB metadata from the document title.

**Accepts:** Markdown (.md), Word (.docx), reStructuredText (.rst), OpenDocument (.odt), Rich Text (.rtf), and HTML (.html).

**You get back:** an `.epub` file that opens in any e-reader application (Apple Books, Calibre, Thorium, etc.).

**Options:**

- **ACB formatting** (on by default) -- embeds the ACB Large Print stylesheet in the EPUB
- **Binding margin** -- not applicable to EPUB (ignored)
- **Print stylesheet** -- not applicable to EPUB (ignored)

**Best when:** you need a simple, portable e-book and do not require DAISY Pipeline's advanced metadata and accessibility features. For a quick Markdown-to-EPUB conversion, this is the fastest path. For production-quality accessible EPUB with full schema.org metadata, use the DAISY Pipeline option instead.

### To accessible PDF

**Powered by:** [Pandoc](https://pandoc.org/) + [WeasyPrint](https://weasyprint.org/) (CourtBouillon)

Creates an accessible PDF formatted with ACB BOP print-optimized rules. Pandoc converts the source document to HTML, then WeasyPrint renders that HTML to PDF using a dedicated print stylesheet with @page rules. The PDF uses Liberation Sans (metrically identical to Arial) for consistent typography, 18pt body text, 22pt headings, 1.15 line spacing (the ACB print specification), and 1-inch margins.

**Accepts:** Markdown (.md), Word (.docx), reStructuredText (.rst), OpenDocument (.odt), Rich Text (.rtf), ePub (.epub), and HTML (.html).

**You get back:** a `.pdf` file ready for printing or distribution.

**Options:**

- **Binding margin** -- adds 0.5 inches of extra left margin for printed/bound documents

**Best when:** you need a print-ready document with ACB-compliant formatting. Good for meeting agendas, newsletters, and reports that will be printed and distributed in large print. Note: WeasyPrint produces CSS-rendered PDFs that are visually formatted but may not be fully PDF/UA tagged. For maximum PDF accessibility, fix the source document first and use your word processor's PDF export.

### To EPUB or DAISY (via DAISY Pipeline)

**Powered by:** [DAISY Pipeline 2](https://daisy.github.io/pipeline/) (DAISY Consortium)

Creates accessible publications in structured formats designed for reading systems used by people with print disabilities. Unlike the other tools, Pipeline produces packaged publications -- EPUB e-books and DAISY talking books -- with proper accessibility metadata, navigation documents, and reading order.

Available conversions:

- **Word to EPUB 3** -- converts a Word document (.docx) to an accessible EPUB 3 e-book through a DTBook intermediate format that preserves document structure
- **HTML to EPUB 3** -- packages an HTML page (.html) into a portable, accessible e-book
- **EPUB to DAISY 2.02** -- converts an ePub (.epub) to DAISY 2.02 talking book format for playback on dedicated DAISY hardware
- **EPUB to DAISY 3** -- converts an ePub (.epub) to DAISY 3 / DTBook structured text format

**You get back:** an `.epub` file (for EPUB conversions) or a `.zip` file containing the DAISY output folder.

Note: Pipeline conversions appear automatically when the DAISY Pipeline is installed on the server. If you do not see these options, Pipeline is not available on this server instance.

### How do I decide between them?

Think about **who will read the result** and **how they will read it:**

- **Reading on screen or printing from a browser?** Use "Accessible web page" -- an HTML file with ACB formatting that works in any browser and prints cleanly.
- **Need a print-ready PDF?** Use "Accessible PDF" -- formatted with ACB print rules (1.15 line spacing, 1-inch margins, Arial 18pt).
- **Need a Word file to edit or run through Fix?** Use "Word document" -- gives you a .docx to open in Microsoft Word.
- **Need a simple e-book?** Use "EPUB 3 e-book (via Pandoc)" -- a quick path to a portable .epub file.
- **Reading on a DAISY player or need full EPUB accessibility metadata?** Use "EPUB or DAISY" via Pipeline -- these are the formats those devices expect.
- **Editing, searching, or feeding to an AI tool?** Use "Plain text" -- raw content in a simple format that works everywhere.
- **Pasting into WordPress or Drupal?** Use the Export page instead -- it has CMS Fragment mode.

### Chaining conversions for better results

You can get the best output by using two conversions in sequence:

1. **Extract to Markdown** to pull text from a PDF, PowerPoint, or other complex format.
2. **Edit the Markdown** in any text editor to clean up headings, fix links, and improve structure.
3. **Convert the Markdown** to an accessible web page, Word document, EPUB, or PDF.

This two-step approach almost always produces better results than a one-step direct conversion, because you can review and improve the content between steps.

---

## 9. Understanding Your Results

### Severity levels

| Level | What It Means | Action |
|-------|--------------|--------|
| Critical | Makes the document unreadable for low-vision users or completely blocks assistive technology | Must fix. These are deal-breakers. |
| High | Significant readability or structure problems | Should fix. Major quality issues. |
| Medium | Compliance gaps that affect quality but may not block reading | Fix when possible. Good for polishing. |
| Low | Minor issues or best-practice recommendations | Nice to fix. Not blocking compliance. |

### Reading the report

Each finding in the audit report includes:

- **Rule ID** -- a short code like `ACB-FONT-FAMILY` or `EPUB-MISSING-ALT-TEXT`. Click the help links (in the web app) to learn more about each rule.
- **Severity** -- Critical, High, Medium, or Low.
- **Location** -- where in the document the issue was found (paragraph number, slide number, sheet name, heading text, etc.).
- **Description** -- what is wrong and why it matters.
- **Help links** -- links to the DAISY Knowledge Base, Microsoft support, or WCAG documentation for detailed remediation guidance.

---

## 10. Common Issues and How to Fix Them

### "All text must use Arial font" (ACB-FONT-FAMILY)

**Why:** Arial is required because it is a clean sans-serif font with excellent legibility at large sizes.

**Auto-fix:** Yes -- the fixer changes all fonts to Arial automatically.

**Manual fix:** In Word, select all text (Ctrl+A), then change the font to Arial.

### "Body text must be 18pt minimum" (ACB-FONT-SIZE-BODY)

**Why:** 18pt is the absolute floor for any text, including footnotes and captions.

**Auto-fix:** Yes -- the fixer increases all body text to 18pt.

**Manual fix:** Select text smaller than 18pt and increase the font size.

### "Italic formatting is prohibited" (ACB-NO-ITALIC)

**Why:** Italic text is harder to read for people with low vision because slanted shapes reduce letter distinction.

**Auto-fix:** Yes -- the fixer removes all italic formatting.

**Manual fix:** Select italic text, press Ctrl+I to remove italic. If emphasis is needed, use underline (Ctrl+U) instead.

### "Images must have alt text" (Various rules)

**Why:** Screen readers cannot describe images without alternative text. Users who cannot see the image rely entirely on the alt text.

**Auto-fix:** No -- alt text requires human judgment about the image content.

**Manual fix in Word:** Right-click the image, Edit Alt Text. Describe what the image shows in 1-2 sentences. If the image is purely decorative, check "Mark as decorative."

Note: For legacy Word VML shapes, explicit `alt=""` is treated as decorative by the auditor.

### "I turned heading detection off. Why did my score still change?"

If **Detect and convert faux headings** is unchecked, fix results now suppress `ACB-FAUX-HEADING` in post-fix scoring. The results page also lists suppressed rules so you can verify exactly what was excluded.

### "Why did my document get longer after fix?"

Page growth is expected when source body text is below 18pt. For example, increasing 16pt body text to 18pt can significantly increase line count in long newsletters. Fix Results now warns when this condition is detected so the pagination change is expected rather than surprising.

### "Where are list indentation controls on the Fix page?"

The **List Indentation** fields are always visible. They are disabled while **Flush all lists to the left margin** is checked, and enabled when you uncheck it to use custom left/hanging indents.

**Manual fix in ePub:** Add an `alt` attribute to the `<img>` tag in the content document.

### "Heading levels must not skip" (ACB-HEADING-HIERARCHY / EPUB-HEADING-HIERARCHY)

**Why:** Screen reader users navigate by heading levels. Jumping from H1 to H3 breaks their mental model of the document structure.

**Auto-fix:** Not automatically -- heading intent requires human judgment.

**Manual fix:** Review your heading hierarchy. Each H3 must have an H2 parent, each H2 must have an H1 parent. Restructure or re-level headings as needed.

### "Links must have descriptive text" (Various rules)

**Why:** Vague links like "click here" or "read more" do not tell screen reader users where the link goes. Links should make sense read out of context.

**Auto-fix:** No -- link text requires human judgment.

**Manual fix:** Replace vague text with descriptive text. For example, change "click here to download the report" to "download the annual report (PDF)".

### "ePub should include accessibility metadata" (EPUB-ACCESSIBILITY-METADATA)

**Why:** Accessibility metadata tells reading systems and library catalogs what accessibility features the publication offers.

**Manual fix:** Add schema.org metadata to the OPF package document: accessMode, accessibilityFeature, accessibilitySummary, and accessibilityHazard. See the [DAISY Knowledge Base on schema.org metadata](https://kb.daisy.org/publishing/docs/metadata/schema.org/index.html).

---

## 11. Tips by Document Format

### Word (.docx)

- Use Word's built-in heading styles (Heading 1, Heading 2, etc.) instead of manually formatting text to look like a heading.
- Use real bulleted and numbered lists (Home, Bullets/Numbering), not manually typed dashes or numbers.
- Set the document title in File, Properties, Title.
- Set the document language in Review, Language.
- For emphasis, use underline -- never italic, and avoid bold in body text.
- After using the fix tool, always re-audit to catch any remaining manual-fix items.

### Excel (.xlsx)

- Give every sheet a meaningful name -- "Sheet1" is not helpful to screen reader users.
- Use Format as Table so each column has a proper header row.
- Avoid merged cells -- they confuse screen readers navigating the grid.
- Add alt text to any embedded images or charts.
- Do not rely on color alone to convey information (e.g., red cells for errors).

### PowerPoint (.pptx)

- Every slide must have a unique title.
- Check the reading order in the Selection Pane (View, Selection Pane). Objects are read bottom-to-top, so the title should be at the bottom of the list.
- Add alt text to every image, chart, and SmartArt graphic.
- Use slide layouts with built-in placeholders instead of manually placed text boxes.
- Add speaker notes for slide content that is primarily visual.

### Markdown (.md)

- Use ATX-style headings (`# Heading 1`) not Setext-style (underlines).
- Never use italic (`*text*`) -- use `<u>text</u>` for emphasis instead.
- Write descriptive link text: `[download the annual report](url)` not `[click here](url)`.
- Add alt text to all images: `![Description of the image](image.png)`.
- Do not leave blank lines between list items.
- Avoid bare URLs -- wrap them in link syntax.

### PDF (.pdf)

- PDFs should be tagged (structured) for accessibility. Scanned documents without OCR will fail many checks.
- Set the document title and language in the PDF properties.
- Use bookmarks for navigation in long documents.
- The best approach for PDFs is to fix the source (usually Word) and re-export.

### ePub (.epub)

- Include a navigation document (table of contents) -- this is required by EPUB Accessibility 1.1.
- Add schema.org accessibility metadata to the OPF file.
- Ensure all images have alt text in the content documents.
- Use proper heading levels (h1-h6) without skipping.
- ePub audits include DAISY Ace, which runs 100+ axe-core accessibility checks beyond the basic structural rules.
- When your ePub includes schema.org accessibility metadata, the audit report shows a human-readable "Accessibility Metadata" section describing how the publication can be read (visual adjustments, read aloud, braille), conformance claims, navigation features, hazards, and more. This follows the W3C Accessibility Metadata Display Guide 2.0.
- If your ePub contains MathML, the audit will detect it and provide specific accessibility guidance for mathematical content.

---

## 12. Recommended Workflows

### Workflow A: Fix an existing document

1. **Audit first** -- upload to Audit to understand the scope of issues.
2. **Auto-fix** -- upload to Fix to correct everything the tool can handle.
3. **Manual fixes** -- open the fixed document and address remaining items from the fix report.
4. **Re-audit** -- upload the manually-fixed document to Audit to confirm.
5. **Publish** -- optionally Export to accessible HTML for web publishing.

### Workflow B: Start a new document from scratch

1. **Create a template** -- use Template to generate a pre-configured .dotx file.
2. **Write in the template** -- use the built-in styles for all formatting.
3. **Quick audit** -- when done, upload to Audit with Quick Audit mode to verify compliance.

### Workflow C: Publish meeting minutes or agendas online

1. Write your content in Markdown or Word.
2. **Audit** to check compliance.
3. **Fix** if needed.
4. **Convert** to accessible HTML using the Convert page with "Accessible web page" selected.
5. Upload the HTML file to your website.

### Workflow D: Create accessible EPUB publications

1. Start with a properly formatted Word document or Markdown file.
2. **Audit** the source document for ACB compliance.
3. **Convert to EPUB** using the Convert page -- choose "EPUB 3 e-book (via Pandoc)" for a quick e-book, or a DAISY Pipeline conversion for production-quality EPUB with full accessibility metadata.
4. **Audit the EPUB** -- upload the .epub to Audit for EPUB-specific accessibility checks (DAISY Ace runs automatically).
5. Fix any EPUB-specific issues (metadata, alt text, navigation) and re-audit.

### Workflow E: Produce large print PDF for distribution

1. Write your content in Markdown or Word.
2. **Audit** to check compliance.
3. **Fix** if needed (for Word documents).
4. **Convert to PDF** using the Convert page with "Accessible PDF" selected. Enable "Binding margin" if the document will be printed and bound.
5. Distribute the PDF for printing. The output uses ACB BOP print formatting -- Arial 18pt, 1.15 line spacing, 1-inch margins.

---

## 13. DAISY Accessibility Tools

GLOW integrates with open source tools from the [DAISY Consortium](https://daisy.org/), an international association serving people with print disabilities. Here is how each integration works:

### DAISY Ace -- EPUB Accessibility Checker

[Ace by DAISY](https://daisy.github.io/ace/) is bundled with the web application and runs 100+ automated accessibility checks on EPUB publications using the axe-core engine. Every ePub audit automatically includes:

- All axe-core HTML accessibility rules (contrast, ARIA, landmarks, tables, forms)
- EPUB-specific metadata validation (accessibility metadata, package structure)
- Content document structure checks (headings, images, links)
- Findings linked to the [DAISY Knowledge Base](https://kb.daisy.org/publishing/) for remediation guidance

### DAISY Pipeline -- Document Conversion

[DAISY Pipeline](https://daisy.github.io/pipeline/) performs format conversions optimized for accessible publishing. When installed, the Convert page gains additional options:

- Word (.docx) to EPUB 3
- HTML to EPUB 3
- HTML to DAISY 2.02 (digital talking book format)
- EPUB 2 to EPUB 3 upgrade

### DAISY Knowledge Base

The [Accessible Publishing Knowledge Base](https://kb.daisy.org/publishing/) provides the help links you see throughout audit reports. Every ePub-related finding links to a specific Knowledge Base article with detailed remediation guidance.

### MathML and Mathematical Content

When ePub files contain MathML (mathematical markup), the audit detects it and provides guidance on making mathematical content accessible. The [MathCAT project](https://github.com/daisy/MathCAT) (Math Capable Assistive Technology) by DAISY generates speech, braille, and navigation from MathML for screen readers. If your ePub uses MathML, ensure it is properly structured so tools like MathCAT and MathJax can process it.

---

## 14. Keyboard and Screen Reader Tips

This tool is designed to work fully without a mouse. Here are tips for keyboard and screen reader users:

- **Skip link:** Press Tab on any page to reveal a "Skip to main content" link that jumps past the navigation.
- **Navigation:** The main navigation is a list of links. Use Tab and Enter to navigate between pages.
- **Forms:** All form fields have visible labels and description text. Errors are announced with the alert role.
- **Accordions:** Help sections use details/summary elements. Press Enter or Space on a summary to expand or collapse. Screen readers announce the expanded/collapsed state.
- **File upload:** After selecting a file, Tab to the submit button and press Enter. Upload progress is indicated by the page loading a new result.
- **Severity badges:** In the audit report, severity levels are shown as colored badges. The text content is always present (not color-only), so screen readers announce "Critical", "High", etc.
- **Help links:** External help links open in new tabs and are announced as such.
- **Back to top:** Each section on the Guidelines and Guide pages has a "Back to table of contents" link for quick navigation.

---

## 15. Frequently Asked Questions

### Is my document stored on the server?

Uploaded files are stored in an isolated temporary workspace long enough to complete audit/fix/download flows, including interactive heading review. Temporary files are automatically cleaned up and never retained as account data.

By default:

- Active sessions can continue for extended review workflows.
- Stale upload workspaces are automatically removed after 24 hours.

### What is the maximum file size?

500 MB. If your document is larger, try compressing images within the document first (Word: File, Compress Pictures).

### Can I audit multiple documents at once?

The web tool processes one document at a time. For batch processing, use the [desktop application](https://github.com/Community-Access/glow) which supports folder-level audits.

### Why does the fix not change my headings?

The fix tool can now detect "faux headings" -- paragraphs that look like headings (bold, large font, short text) but use a Normal style instead of a real Heading style. Enable "Detect and convert faux headings" on the Fix page to use this feature. On the web, you review detected candidates in an interactive table before they are applied. On the CLI, use `--detect-headings`.

If false positives are common (for example names, times, "Agenda" labels), use the heading detection accuracy control and switch to **Conservative**. If valid headings are being missed, use **Thorough**.

For heading hierarchy corrections (changing an H3 to an H2, for example), the fix tool corrects heading formatting (font, size, bold) but does not change heading levels. Review your heading structure manually using the report's guidance.

### Can I limit heading review to only certain levels?

Yes. Use the **Allowed heading levels** checkboxes in the Fix form, or set defaults in Settings.

When configured, the heading review page only shows those levels in each candidate dropdown, and confirm/apply honors the same subset.

Template sample content can also use the same subset so your authored examples and fix workflow stay consistent.

### Why did decorative images get flagged as missing alt text?

Use Word's **Mark as decorative** option for non-informational visuals. The auditor now correctly treats legacy VML shapes with `alt=""` as decorative. Images without decorative intent or meaningful alt text are still reported.

### What is the difference between ACB and MSAC rules?

**ACB Large Print** rules come from the American Council of the Blind's Board of Publications. They cover visual formatting: font, size, spacing, emphasis, alignment, and margins.

**MS Accessibility Checker (MSAC)** rules are aligned with the Microsoft Office Accessibility Checker and WCAG 2.1. They cover structural accessibility: alt text, table headers, reading order, hyperlink text, document properties.

Both categories work together for comprehensive compliance. Run with both enabled for best results.

### What about DAISY Pipeline conversions?

DAISY Ace is bundled with the web application and always runs during ePub audits. DAISY Pipeline (for advanced format conversions like Word to EPUB, HTML to DAISY 2.02) requires Java and is an optional server component. Pipeline conversions appear automatically when installed by the server administrator. For the desktop application, install Node.js and Ace (`npm install -g @daisy/ace`) for full ePub audit support.

### Can I use this tool for documents in languages other than English?

Yes. The ACB formatting rules (font, size, spacing) apply regardless of language. The tool audits document structure and formatting, not content. Set the document language property (Rule: ACB-DOC-LANGUAGE) to the correct language code for proper screen reader pronunciation.

### Is there a desktop version?

Yes. The [GLOW](https://github.com/Community-Access/glow) includes a desktop application with a graphical wizard interface, command-line tools, and batch processing support. It runs on Windows without requiring an internet connection.

### Where can I read the ACB Large Print Guidelines?

The full guidelines are available at [acb.org/large-print-guidelines](https://acb.org/large-print-guidelines) (revised May 6, 2025). A reference copy is included in this repository at `docs/ACB Large Print Guidelines, revised 5-6-25.docx`. The web application includes a [Guidelines page](https://glow.bits-acb.org/guidelines) with the complete rule reference and related audit rule mappings.

APH also publishes research-based large print guidance at [APH: Guidelines for the Development of Documents in Large Print](https://www.aph.org/resources/large-print-guidelines/), including APH-hosted DOCX and PDF versions.

---

## 16. Admin Access (Administrative Use Only)

GLOW includes an admin-only sign-in and approval workflow for operational dashboards.

- **No general user accounts in this release.** Admin authentication is restricted to approved administrative accounts only.
- **Email configuration required.** Admin sign-in features are enabled only when email delivery is configured.
- **Sign-in options:** Email magic link, Google, Apple, GitHub, Microsoft, Auth0, and WordPress (providers appear only when configured).
- **Approval required:** A user may request admin access, but an existing approved admin must approve before sign-in succeeds.
- **Admin dashboard:** Approved admins can view the audio conversion queue, cancel queued jobs, and re-queue failed jobs.
- **AI settings:** Configure and monitor cloud AI budget controls and API key status.
- **Feature flags:** Enable or disable specific tool features without redeploying.
- **Access request review:** Approve or deny pending admin access requests.
- **Tool usage analytics (`/admin/analytics`):** View cumulative visitor count, total tool uses, and per-tool breakdown with share percentages and last-used timestamps. Data persists across server restarts in SQLite.

---

## 17. Getting Help

- **Full ACB Large Print Guidelines Reference** -- available on the web app Guidelines page or at [acb.org/large-print-guidelines](https://acb.org/large-print-guidelines)
- **APH Large Print Guidelines (official source)** -- [aph.org/resources/large-print-guidelines](https://www.aph.org/resources/large-print-guidelines/)
- **Project overview and release highlights** -- [About GLOW](/about/)
- **Web app operations and deployment notes** -- [Deployment Guide](/deployment/)
- **Web app product requirements and implementation log** -- [Product Requirements Document](/prd/)
- **Submit Feedback** -- use the Feedback page in the web app to report bugs, request features, or share your experience
- **About This Project** -- mission, organizations, standards, and open source dependencies on the web app About page
- **GitHub Issues** -- [report bugs or request features](https://github.com/Community-Access/glow/issues) on the open source repository
- **DAISY Knowledge Base** -- [remediation guidance](https://kb.daisy.org/publishing/) for ePub accessibility issues
- **Microsoft Accessibility Checker Guide** -- [Microsoft's guide](https://support.microsoft.com/en-us/office/improve-accessibility-with-the-accessibility-checker-a16f6de0-2f39-4a2b-8bd8-5ad801426c7f) to the Office accessibility checker

**Implementation note:** APH alignment is fully integrated for the Release 1.2.0 submission workflow. Enforcement includes ACB + WCAG + Microsoft Accessibility Checker + format-specific rules with APH profile mapping finalized in this release.
