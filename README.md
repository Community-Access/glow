# GLOW

GLOW stands for **Guided Layout & Output Workflow**.

A VS Code agent toolkit, desktop application, and web application for auditing and fixing Office documents for accessibility. Enforces the American Council of the Blind (ACB) Large Print Guidelines (revised May 6, 2025), Microsoft Accessibility Checker rules, and WCAG 2.2 AA digital accessibility standards.

External APH source reference: [APH Guidelines for the Development of Documents in Large Print](https://www.aph.org/resources/large-print-guidelines/).

Status note: APH alignment in GLOW is fully integrated in Release 1.2.0 for the submission workflow, alongside existing ACB + WCAG + Microsoft Accessibility Checker + format-specific rule sets.

## Release 4.0.0 at a Glance

- Curated conversion hardening is now in the mainline release path, including LibreOffice-assisted pre-conversion for OpenDocument spreadsheets and presentations before the MarkItDown plus Pandoc chain.
- PDF table preservation is improved for downstream exports (Word, HTML, EPUB, and other Pandoc-backed outputs) using PyMuPDF table extraction and Markdown table reconstruction.
- Fix-to-re-audit flow now uses an explicit CSRF-protected POST re-audit form from the Fix result page for stronger request integrity and clearer standards-profile propagation.
- Public release documents are now synchronized around v4.0.0 artifacts, with updated changelog, release notes, announcement pointers, PRD status, and user guidance.

### How GLOW knows which branding profile is active

GLOW reads the `GLOW_BRAND_PROFILE` environment variable at runtime and injects profile context into all templates.

- `GLOW_BRAND_PROFILE=bits` (default)
- `GLOW_BRAND_PROFILE=uarizona`

Where this is resolved:

- `web/src/acb_large_print_web/branding.py` (`get_branding_context()`)
- `web/src/acb_large_print_web/app.py` (global context injection)

Operational note: profile switching is deployment-level (restart/redeploy required), not a live admin toggle.

## Standards Profiles (Release 1.2.0)

The web Audit, Fix, and Template flows now include three standards profiles:

- **ACB 2025 Baseline** -- default profile. This preserves current behavior. If you select ACB, there is no workflow change and no scoring model change from the existing production experience.
- **APH Submission** -- uses the APH-aligned checks and defaults finalized in Release 1.2.0 for submission preparation and evidence packaging.
- **Combined Strict** -- shows all currently implemented checks together (ACB + MSAC/WCAG-aligned rules) for maximum rigor in one run. Template generation keeps ACB defaults in this mode for predictable production output.

Profile intent:

- Use **ACB 2025 Baseline** for existing chapter operations and continuity.
- Use **APH Submission** when assembling APH evidence and rollout documentation.
- Use **Combined Strict** for final quality gates before publication.

Template behavior by profile:

- **ACB 2025 Baseline** -- unchanged template defaults (Arial + current ACB spacing baseline).
- **APH Submission** -- APH-oriented template defaults (APHont preferred and 1.25 line spacing recommendation).
- **Combined Strict** -- keeps ACB template defaults while using strict combined review posture in Audit/Fix.

Profile reporting:

- Audit and Fix results now display the selected profile label so exported evidence is traceable.

## Guideline Scope (ACB, APH, AFB)

- GLOW supports two large-print production standards: ACB (default) and APH (fully integrated submission profile in Release 1.2.0).
- AFB JVIB style guidance is not a large-print production mode in GLOW. It is an academic manuscript submission style for the Journal of Visual Impairment & Blindness.
- Use ACB for consumer/member publications and APH for educational/student large-print workflows.
- If you are preparing a JVIB manuscript, follow AFB JVIB rules directly outside the fix/audit profile selector.

References:

- ACB/BITS: https://www.bits-acb.org
- APH large-print guidance: https://www.aph.org/resources/large-print-guidelines/
- AFB JVIB style guidelines: https://afb.org/news-publications/publications/jvib/authors/afb-style-guidelines

## Writing Conventions Used in GLOW

- Use `large print` as a noun and `large-print` as a modifier.
- Use em-dashes with no surrounding spaces.
- Use person-first and neutral language in documentation and UI.

### Prose quality checks (Vale)

This repository uses a lightweight Vale profile for documentation clarity and accessibility writing quality.

- Config: `.vale.ini`
- Rules: `.vale/styles/Glow/`
- Vocabulary: `.vale/config/vocabularies/Glow/`
- CI workflow: `.github/workflows/docs-quality.yml`

Current rules are intentionally low-noise and focus on:

- discouraging ambiguous link text (for example "click here")
- reducing jargon-heavy phrasing
- flagging very long sentences for readability review

## Supported Document Formats

| Format | Audit | Auto-Fix | Template | Export | Convert |
|--------|-------|----------|----------|--------|---------|
| Word (.docx) | 30+ ACB + MSAC rules | Yes -- fonts, spacing, emphasis, headings, margins | Yes (.dotx) | HTML (standalone or CMS) | To Markdown, To HTML, To EPUB 3 |
| Excel (.xlsx) | MSAC rules -- sheet names, table headers, merged cells, alt text, hidden content, color-only | Planned | -- | -- | To Markdown |
| PowerPoint (.pptx) | MSAC rules -- slide titles, reading order, alt text, font sizes, speaker notes, charts | Planned | -- | -- | To Markdown |
| Markdown (.md) | ACB emphasis, headings, images, lists | Planned | -- | -- | To HTML, To Word, To EPUB 3, To PDF |
| PDF (.pdf) | Page-level structure and text extraction | Planned | -- | -- | To Markdown |
| ePub (.epub) | EPUB Accessibility 1.1 (title, language, nav, headings, alt text, tables, links, metadata) | Planned | -- | -- | To Markdown, To HTML, To PDF |
| HTML/CSS | ACB + WCAG 2.2 AA (via VS Code agent) | Yes (via agent) | Yes | -- | To Word, To EPUB 3, To PDF |

## Five ways to use it

| Interface | Who it is for | Install required? |
|-----------|---------------|-------------------|
| **Web app** | Anyone with a browser -- chapter officers, newsletter editors, conference attendees | No -- just open the URL |
| **Desktop GUI** | Users who prefer a native desktop wizard with file dialogs | Yes -- download a single executable |
| **CLI** | Developers and scripters who want batch processing | Yes -- `pip install` or download executable |
| **VS Code agent** | Developers using VS Code with Copilot Chat | Yes -- copy agent files to VS Code config |
| **Word Add-in** | Users who want ACB tools in the Word ribbon | Yes -- sideload the Office Add-in |

## What GLOW does

- Audits Word (.docx), Excel (.xlsx), PowerPoint (.pptx), Markdown (.md), PDF (.pdf), ePub (.epub), HTML, and CSS files for accessibility
- Auto-fixes Word document compliance issues (fonts, spacing, emphasis, headings, margins)
- Provides detailed audit reports for Excel, PowerPoint, Markdown, PDF, and ePub with manual fix guidance
- Generates ACB-compliant Word templates (.dotx) with pre-configured styles
- Exports Word documents to accessible HTML (standalone or CMS-ready fragments)
- Converts documents to Markdown via Microsoft MarkItDown (.docx, .doc, .xlsx, .pptx, .ppt, .txt, .pdf, .html, .csv, .json, .xml, .epub)
- Converts documents to accessible HTML, Word (.docx), EPUB 3, and PDF via Pandoc (and WeasyPrint for PDF)
- Runs optional deterministic WCAG language processing during Convert uploads (before conversion, after conversion, or both) with advisory or strict enforcement modes; controlled by feature flags `GLOW_ENABLE_WCAG_LANGUAGE_PROCESSING` and `GLOW_ENABLE_WCAG_LANGUAGE_STRICT_MODE`
- Runs optional Presidio-based PII redaction before AI requests for uploaded content in Document Chat and alt-text workflows; controlled by feature flags `GLOW_ENABLE_PII_GUARDRAILS` and `GLOW_ENABLE_PII_GUARDRAILS_STRICT_MODE`
- Converts Markdown to ACB-compliant HTML with proper document structure
- Produces PowerShell scripts for configuring Word document styles
- Detects and uses external tools (markdownlint, Pandoc) when available

## Shared core architecture (retrofit baseline)

GLOW now includes a shared service package at:

- `desktop/src/acb_large_print_core/`

This package is the canonical dispatch layer for **audit**, **fix**, and **MarkItDown conversion** across CLI, desktop, and web surfaces.

Current shared entry points:

- `acb_large_print_core.services.audit_by_extension(...)`
- `acb_large_print_core.services.fix_by_extension(...)`
- `acb_large_print_core.services.convert_to_markdown(...)`
- `acb_large_print_core.versions.get_component_versions()`

Design intent:

- Keep UX-specific behavior in each interface (web routes, GUI dialogs, CLI output formatting).
- Keep business logic dispatch and component-version provenance in shared core APIs.
- Enable future extraction to an external reusable package without changing app-layer behavior.

## Recent Fix Workflow Updates (April 2026)

- Fix Results now suppresses `ACB-FAUX-HEADING` from post-fix scoring when heading detection is explicitly disabled, and shows a "Suppressed by your settings" note for transparency.
- Fix Results now warns when pre-fix body text appears below 18pt, because normalizing to the ACB minimum can increase page count in long documents.
- Fix form list indentation fields are always visible for discoverability and are enabled only when "Flush all lists to the left margin" is unchecked.
- Legacy Word VML shapes now treat explicit `alt=""` as decorative, reducing false `ACB-MISSING-ALT-TEXT` findings.
- **Quick Rule Exceptions** section added to Fix and Audit forms: suppress `ACB-LINK-TEXT`, `ACB-MISSING-ALT-TEXT`, and `ACB-FAUX-HEADING` rules per submission without workflow disruption.
- **Preserve centered headings** option added to Fix form: when enabled, skips alignment override on heading paragraphs, preserving intentional heading centering.
- **Per-level list indentation** added to Fix form: configure level-specific expected indents (Level 1, 2, 3) instead of a single uniform indent; auditor and fixer recognize paragraph list styles and apply per-level settings.
- **Allowed heading levels** added to Fix and Settings: teams can restrict heading detection/review/conversion to selected levels only (for example, H1-H3), and heading review options now honor that subset.
- **Template heading-level alignment** added: template sample content now honors the same selected heading-level subset so authoring and fixing workflows stay consistent.
- **Dedicated FAQ page** available at web app `/faq/` with answers to common workflow questions including quick exceptions, heading preservation, per-level indents, and known limitations.

## Workspace structure

```
lp/
  .github/
    copilot-instructions.md              Repo-level Copilot context
    agents/
      large-print-formatter.agent.md     Main agent (9 operating modes)
      markdown-a11y-assistant.agent.md   WCAG markdown audit orchestrator
      markdown-scanner.agent.md          Internal: single-file scanner
      markdown-fixer.agent.md            Internal: auto-fix applicator
      markdown-csv-reporter.agent.md     Internal: CSV export
    prompts/
      acb-audit.prompt.md               /acb-audit slash command
      acb-convert.prompt.md             /acb-convert slash command
      acb-md-audit.prompt.md            /acb-md-audit slash command
      acb-md-convert.prompt.md          /acb-md-convert slash command
      acb-word-setup.prompt.md          /acb-word-setup slash command
    instructions/
      acb-large-print.instructions.md   Auto-attach on html/css files
    skills/
      markdown-accessibility/
        SKILL.md                         Pattern library, severity scoring, fix templates
  styles/
    acb-large-print.css                  Reference CSS (rem-based, print overrides)
  templates/
    acb-large-print-boilerplate.html     Semantic HTML skeleton
  docs/
    user-guide.md                        Complete user guide for all interfaces
    announcement.md                      Press release / announcement
    prd.md                               Canonical web app product requirements document
    deployment.md                        Step-by-step server deployment guide
    shared-core-retrofit.md              Shared service-core architecture and migration status
  samples/
    *.md                                 Example Markdown source files
    *.html                               Converted HTML output files
    *-cms-embed.html                     CMS embed snippets (class-scoped)
  reference/
    ACB Large Print Guidelines, revised 5-6-25.docx   Source specification
  web/                                   Flask web application
    src/acb_large_print_web/             Application package
    tests/                               Test suite
    Dockerfile                           Production container image
    docker-compose.yml                   Compose file for deployment
  desktop/                               Desktop CLI + GUI (Python)
    src/acb_large_print_core/            Shared service core (canonical dispatch layer)
    src/acb_large_print/                 App-layer CLI/GUI + format engines
  office-addin/                          Office.js Word Add-in (TypeScript)
    src/                                 TypeScript port of audit/fix/template
  vendor/                                Vendored third-party source
    daisy-ace/                           DAISY Ace source (MIT)
    daisy-a11y-meta-viewer/              DAISY a11y-meta-viewer source (CC BY-NC-SA 4.0)
```

## Quick start

### Use the web app (no install)

Open the web app in any browser. Upload a Word, Excel, PowerPoint, Markdown, or PDF file and choose an operation:

| Page | What it does |
|------|-------------|
| **Audit** | Check any supported document against accessibility rules (Full, Quick, or Custom mode) |
| **Fix** | Auto-fix Word documents; get audit-based fix guidance for other formats |
| **Template** | Generate a profile-aware Word template (.dotx): ACB baseline defaults, APH-oriented defaults, or combined strict review posture |
| **Export** | Convert a .docx to accessible HTML (standalone or CMS fragment) |
| **Convert** | Transform documents between formats (Markdown, HTML, Word, EPUB 3, PDF, DAISY) |
| **Guidelines** | Browse the full ACB specification and WCAG 2.2 supplement |
| **Settings** | Set and save default profiles/modes/options across Audit, Fix, Template, Export, and Convert |
| **About** | Project mission, organizations, standards, open source dependencies, and acknowledgments |

### Run the web app locally

```bash
cd web
pip install -e ".[dev]"
pip install -e "../desktop"
flask --app acb_large_print_web.app:create_app run --debug
```

### Deploy with Docker

```bash
cd web
docker compose up --build
```

See [docs/deployment.md](docs/deployment.md) for full production deployment (Ubuntu VPS, Caddy, TLS).

### Install to VS Code (User-level)

Copy the agent, prompts, styles, templates, and instructions to your VS Code User config:

```powershell
$prompts = "$env:APPDATA\Code\User\prompts"
$agents  = "$env:APPDATA\Code\User\agents"

# Main agent and bundled markdown agents
Copy-Item .github\agents\*.agent.md $agents\ -Force

# Slash commands
Copy-Item .github\prompts\*.prompt.md $prompts\ -Force

# Auto-attach instructions
Copy-Item .github\instructions\acb-large-print.instructions.md $prompts\ -Force

# Reference CSS and HTML boilerplate
Copy-Item styles\acb-large-print.css $prompts\ -Force
Copy-Item templates\acb-large-print-boilerplate.html $prompts\ -Force
```

### Use the slash commands

Open the VS Code Chat panel (Ctrl+Shift+I) and type the command. The prompt files route to the correct agent automatically.

| Command | What it does |
|---|---|
| `/acb-audit` | Audit the open file for ACB compliance |
| `/acb-convert` | Fix the open file to ACB compliance |
| `/acb-md-audit` | Audit a Markdown file for ACB compliance |
| `/acb-md-convert` | Convert Markdown to ACB-compliant HTML |
| `/acb-word-setup` | Generate a Word styles configuration script |

## Using the agents

### Large Print Formatter (main agent)

Address `@large-print-formatter` in VS Code Chat. It supports 9 operating modes that activate based on your request.

#### Mode 1: Review / Audit -- check an HTML or CSS file

Reads the file, checks every ACB rule, and reports a PASS/FAIL checklist with a compliance score.

Sample prompts:

- `@large-print-formatter audit this HTML file for ACB compliance`
- `@large-print-formatter review the open file against ACB Large Print rules`
- `@large-print-formatter check if this CSS meets the ACB typography requirements`

#### Mode 2: Generate -- create new ACB-compliant content

Creates new HTML/CSS with all ACB rules applied from the start. Asks whether you want external CSS, embedded, or both.

Sample prompts:

- `@large-print-formatter generate a new ACB-compliant HTML page for a meeting agenda`
- `@large-print-formatter create an ACB-compliant newsletter template`

#### Mode 3: Convert / Reformat -- fix an existing file

Reads an existing HTML file, detects every deviation, and fixes it. Handles fragments (no DOCTYPE) by wrapping them in a complete document shell. Fixes bold abuse, fake headings, `<br>` separators, and italic misuse.

Sample prompts:

- `@large-print-formatter convert this HTML file to ACB compliance`
- `@large-print-formatter reformat the open file for large print`
- `@large-print-formatter fix this Pandoc output to meet ACB guidelines`

#### Mode 4: CSS / HTML Template -- get starter files

Generates a reference CSS file and semantic HTML boilerplate with all ACB + WCAG rules, including print media overrides.

Sample prompts:

- `@large-print-formatter generate an ACB-compliant CSS stylesheet`
- `@large-print-formatter create an HTML boilerplate with ACB large print styles`

#### Mode 5: CSS Embed -- inline the stylesheet

Takes the reference CSS and embeds it as a `<style>` block in an HTML file, removing any external `<link>` to avoid duplication.

Sample prompts:

- `@large-print-formatter embed the CSS directly into this HTML file`
- `@large-print-formatter inline the ACB stylesheet into the open file`

#### Mode 5a: CMS Embed Snippet -- scoped output for WordPress / Drupal / CMS

Produces a class-scoped version of the content: all CSS selectors are prefixed with `.acb-lp` and the HTML content is wrapped in `<div class="acb-lp">`. This prevents the ACB styles from clashing with the CMS theme. The output is a single file (no DOCTYPE/head/body) ready to paste into any CMS HTML editor.

Sample prompts:

- `@large-print-formatter create a WordPress embed snippet for this HTML`
- `@large-print-formatter generate a CMS-ready version of the meeting agenda`
- `@large-print-formatter convert this markdown to a CMS embed snippet`

When using `/acb-convert` or Mode 3/Mode 9, you can also select "CMS embed snippet" from the CSS delivery question to get this output alongside the standalone HTML.

#### Mode 6: Word Setup Script -- configure Microsoft Word

Generates a PowerShell COM automation script that configures Word styles (Normal, Heading 1, Heading 2, List Bullet) and page layout to ACB spec.

Sample prompts:

- `@large-print-formatter generate a Word setup script for ACB large print`
- `@large-print-formatter create a PowerShell script to configure Word for ACB compliance`

#### Mode 7: Markdown Audit -- check a .md file

Reads a Markdown file and checks ACB-specific rules: italic prohibition, heading hierarchy, emphasis conventions, ALL CAPS, lists, images, bare URLs.

Sample prompts:

- `@large-print-formatter audit this markdown file for ACB compliance`
- `@large-print-formatter check the open .md file against ACB rules`

#### Mode 8: Markdown Fix -- auto-repair a .md file

Runs the audit first, then auto-fixes what it can (italic removal, heading hierarchy, ALL CAPS) and asks about ambiguous cases.

Sample prompts:

- `@large-print-formatter fix this markdown file for ACB compliance`
- `@large-print-formatter auto-fix the ACB issues in the open .md file`

#### Mode 9: Markdown to HTML Conversion -- full pipeline

Converts Markdown to a complete ACB-compliant HTML document. Asks about CSS delivery, print intent, and output location. Uses Pandoc when available.

Sample prompts:

- `@large-print-formatter convert this markdown to ACB-compliant HTML`
- `@large-print-formatter convert meeting-agenda.md to large print HTML with embedded CSS`
- `@large-print-formatter convert the open .md file to HTML for print`

### Markdown Accessibility Assistant (bundled)

Address `@markdown-a11y-assistant` in VS Code Chat for general WCAG markdown auditing. This is a separate, interactive wizard that covers 9 accessibility domains beyond ACB formatting.

Sample prompts:

- `@markdown-a11y-assistant audit this markdown file`
- `@markdown-a11y-assistant check all .md files in the docs folder`
- `@markdown-a11y-assistant review the README for accessibility`

The assistant will ask you configuration questions before scanning (scope, emoji preference, Mermaid preference) and then orchestrate its sub-agents (`markdown-scanner`, `markdown-fixer`, `markdown-csv-reporter`) automatically.

#### Domains covered by the markdown accessibility agents

| Domain | What it checks | WCAG criteria |
|---|---|---|
| Descriptive links | Ambiguous text ("click here", "read more"), bare URLs, repeated identical text | 2.4.4, 2.4.9 |
| Image alt text | Missing, empty, filename-as-alt, generic placeholders | 1.1.1 |
| Heading hierarchy | Skipped levels, multiple H1s, bold-as-heading | 1.3.1, 2.4.6 |
| Table descriptions | Missing descriptions, empty headers, layout tables | 1.3.1 |
| Emoji | Decorative emoji, emoji bullets, consecutive emoji, emoji in headings | 1.3.3, Cognitive |
| Mermaid/ASCII diagrams | Diagrams without text alternatives | 1.1.1, 1.3.1 |
| Em-dash normalization | Unicode em/en-dashes, doubled hyphens | Cognitive |
| Anchor link validation | Broken `#anchor` links, GitHub anchor generation rules | 2.4.4 |
| Plain language | Sentence length, passive voice, emoji bullets | Cognitive |

### Combined ACB + WCAG workflow

For the most thorough audit of a Markdown file, run both agents in sequence:

1. `@large-print-formatter audit this markdown file for ACB compliance` -- catches ACB-specific formatting rules (italic prohibition, font requirements, print layout)
2. `@markdown-a11y-assistant audit the same file` -- catches general WCAG issues (emoji, Mermaid diagrams, ambiguous links, anchor validation)

The large-print-formatter has built-in handoff links. After an ACB audit, it can offer to hand off to `@markdown-a11y-assistant` for the broader WCAG sweep.

## If you already have the accessibility agents installed

The markdown accessibility agents are bundled here for completeness so GLOW works standalone. **If you already have the [accessibility agents](https://github.com/accessibility-agents) repo cloned as a workspace or installed to your VS Code User config, use those copies as the source of truth.** Do not copy the bundled versions over newer ones. The accessibility agents repo receives updates to all agents, skills, and shared instructions that this standalone copy will not automatically pick up.

To check if you already have them:

```powershell
# Check User-level agents
Get-ChildItem "$env:APPDATA\Code\User\agents\markdown-*" -ErrorAction SilentlyContinue

# Check for the accessibility agents workspace
Get-ChildItem S:\code\agents\.github\agents\markdown-* -ErrorAction SilentlyContinue
```

If either location returns results, those are your source of truth and will receive updates from the accessibility agents project. The bundled copies in this repo are a frozen snapshot for standalone use only.

## CMS embedding (WordPress, Drupal, etc.)

When pasting ACB Large Print content into a CMS page, the standalone HTML file's bare selectors (`body`, `h1`, `p`) will conflict with the theme's CSS. The agent produces a **CMS embed snippet** that avoids this:

- All CSS selectors are scoped under a `.acb-lp` class prefix
- Content is wrapped in `<div class="acb-lp">...</div>`
- No document shell (`<!DOCTYPE>`, `<html>`, `<head>`, `<body>`) -- the CMS already provides these
- Output file uses a `-cms-embed.html` suffix

To get a CMS embed snippet:

1. Select "CMS embed snippet" when the agent asks about CSS delivery, **or**
2. Ask directly: `@large-print-formatter create a CMS embed snippet for this file`

The agent always produces the CMS embed as a separate file alongside the standalone HTML.

## External tool support

The agent detects and uses these tools when available:

| Tool | Purpose | Install |
|---|---|---|
| markdownlint | Structural Markdown linting before ACB audit | `npm install -g markdownlint-cli` |
| Pandoc | Reliable GFM to HTML5 conversion | [pandoc.org/installing](https://pandoc.org/installing.html) |

When tools are not installed, the agent performs equivalent checks manually.

## ACB Large Print rules (summary)

- Font: Arial only, 18pt body, 22pt headings, 20pt subheadings
- Alignment: flush left, ragged right (never justified)
- Emphasis: underline only (no bold for emphasis, no italic ever)
- Headings: proper hierarchy, no ALL CAPS, no skipped levels
- Lists: large solid bullets, no extra spacing between items
- Links: descriptive text (no bare URLs, no "click here")
- Spacing: 1 blank line between paragraphs, no blank lines between list items
- Digital supplement: WCAG 2.2 AA contrast (4.5:1), 400% zoom reflow, 1.5x line-height

## Validation And Lessons Learned

We did not treat heading detection and ACB repair as a one-time feature drop. We stress-tested the platform with synthetic Word documents designed to behave like real documents that users actually upload: copied email threads, plain-text paste, newsletter blurbs, agendas, policy manuals, legal outlines, appendices, and flyers.

What the stress work covered:

- 1,000 generated Word documents in the primary full-corpus run
- 1,000 total heading scenarios in the current release-scale corpus
- 10 document families covering different writing styles and layout problems
- 12 randomized scenario patterns including real headings, false positives, no-style body lines, font-only drift, multilingual section labels, centered titles, justified paragraphs, hanging indents, and mixed-font paste artifacts
- 7 language variants in the current random set: English, Spanish, French, German, Italian, Portuguese, and Dutch

What the 1,000 generated documents represented:

- Board agendas pasted from email threads
- Newsletters and flyers with decorative layout drift
- Policy manuals with section labels and long explanatory body text
- Legal outlines with numbering and nested structure pressure
- Training handouts with prompts and labels that can look like headings
- Appendix-style documents with short labels that can be confused with captions or notes
- Plain-text paste where no proper heading styles exist at all

Each generated document included real document structure around the test case, not just a single isolated line. That means the platform had to judge a candidate heading in context, then repair the surrounding formatting back to ACB rules.

What we proved:

- Full heading stress suite: 5 tests passed
- Heuristic detector against 1,000 ground-truth scenarios: 0 false positives, 0 false negatives
- Denser randomized sweep over 4,800 scenarios: 0 false positives, 0 false negatives
- Fix-then-audit enforcement sweep over 1,000 generated documents: 0 remaining ACB findings after the latest fixes
- Core fixer and detector test set: 150 tests passed

What we learned while testing:

1. Real-world documents do not fail in one neat way. They mix plain text, manual bold, centered titles, font overrides, copied web formatting, and fake structure in the same file.
2. A heading detector that only looks for bold text is not good enough. It must also learn from length, punctuation, numbering, body context, and known false-positive shapes like signature lines and callouts.
3. Passing heading detection alone is not enough. The fixer must also repair the document back to ACB rules, which means alignment, indentation, font normalization, heading hierarchy, and heading text cleanup all have to work together.
4. The most useful failures were not dramatic crashes. They were policy mismatches, such as faux headings converted to ALL CAPS Heading 3 lines that then created heading-level skips.

How we adapted the platform:

- Added stronger false-positive penalties for signature-like lines and callout/salutation patterns
- Expanded the synthetic corpus to include multilingual numbering, plain-text/no-style negatives, and font-size-only heading cases
- Tightened the fixer so converted headings are normalized after conversion, including ALL CAPS cleanup and heading-hierarchy repair
- Re-ran the full corpus after every meaningful change so we only kept changes that improved measured outcomes

Confidence statement:

- We are confident in the current lessons learned for heading detection and ACB repair behavior on the scenarios we generated and measured.
- We are also confident that the fixer path is written in a cross-platform way because it uses platform-neutral Python and document-processing libraries rather than OS-specific APIs.
- We have runtime proof for Windows in this session. Final cross-platform runtime proof still requires executing the same validation commands on macOS and Linux CI runners.

## License

GLOW implements the ACB Large Print Guidelines, a public specification from the American Council of the Blind. GLOW code and configuration files are provided for organizational use.

## Web Application

The `web/` directory contains a Flask web application that provides browser-based access to all core operations. No installation or account required. Runs in Docker for production deployment. See [web/README.md](web/README.md) for full documentation.

## Desktop Tool

The `desktop/` directory contains a standalone desktop application (CLI and GUI) that audits, fixes, and exports Microsoft Word documents for ACB compliance. It builds as one-file executables for 6 platforms via PyInstaller and GitHub Actions. See [desktop/README.md](desktop/README.md) for full documentation.

## Office Add-in

The `office-addin/` directory contains an Office.js Web Add-in that integrates ACB Large Print audit, fix, and template tools directly into the Microsoft Word ribbon. TypeScript port of the Python core. Deployed to GitHub Pages automatically on push.
