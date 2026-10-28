This repository contains the GLOW -- a VS Code agent toolkit, desktop application, and web application for auditing and fixing Office documents (Word, Excel, PowerPoint) for accessibility. Enforces the American Council of the Blind Large Print Guidelines (revised May 6, 2025), Microsoft Accessibility Checker rules, and WCAG 2.2 AA digital accessibility standards.

## Deployment

- **Automated Deployment:** `bash ~/app/scripts/deploy-app.sh` (safe, automatic rollback on failure)
- **Maintenance Mode:** `bash ~/app/scripts/maintenance-mode.sh {on|off|status}` (toggle maintenance page without code deployment)
- **Strategy & Troubleshooting:** See `docs/deployment-strategy.md` for complete deployment workflow, failsafe features, and manual intervention procedures
- **Health Check:** `/health` endpoint responds with `200 OK` (even during maintenance mode) to support orchestration and monitoring

## Repository layout

- `.github/agents/large-print-formatter.agent.md` -- Main agent (9 operating modes for audit, generate, convert, template, CSS embed, Word setup, Markdown audit, Markdown fix, Markdown-to-HTML)
- `.github/agents/markdown-a11y-assistant.agent.md` -- Bundled WCAG markdown audit orchestrator (from accessibility agents ecosystem)
- `.github/agents/markdown-scanner.agent.md` -- Internal: single-file accessibility scanner
- `.github/agents/markdown-fixer.agent.md` -- Internal: auto-fix applicator
- `.github/agents/markdown-csv-reporter.agent.md` -- Internal: CSV finding export
- `.github/prompts/` -- Slash command prompt files (.prompt.md) for /acb-audit, /acb-convert, /acb-md-audit, /acb-md-convert, /acb-word-setup
- `.github/instructions/` -- Auto-attach instruction files (activates on html/css editing)
- `.github/skills/markdown-accessibility/` -- Pattern library, severity scoring, emoji maps, fix templates
- `styles/` -- Reference CSS stylesheet (acb-large-print.css)
- `templates/` -- HTML boilerplate skeleton (acb-large-print-boilerplate.html)
- `docs/` -- Detailed toolkit documentation, announcement, PRD, deployment guide, and source ACB specification (.docx)
- `samples/` -- Example source Markdown and converted HTML files
- `vendor/` -- Vendored third-party source (DAISY Ace, DAISY a11y-meta-viewer)
- `web/` -- Flask web application (browser-based audit, fix, template, export, convert, guidelines, about, feedback)
- `desktop/` -- Standalone Python CLI + wxPython GUI tool (auditor, fixer, converter, template builder, exporter)
- `office-addin/` -- Office.js Web Add-in for Microsoft Word ribbon integration (TypeScript port)

## Key conventions

- Accessibility expectations for every change are in `ACCESSIBILITY.md` ("Contributor expectations"); for web changes run `npm run test:axe`, `npm run test:keyboard` and `npm run test:reflow` in `web/`, and complete the accessibility checklist in `.github/PULL_REQUEST_TEMPLATE.md`
- All CSS uses rem units (never px for text) to support browser zoom and reflow
- Digital content uses WCAG 2.2 AA line-height (1.5) which overrides ACB print spec (1.15); print media query reverts to 1.15
- Emphasis is underline only -- no italic anywhere, no bold for body emphasis
- In Markdown, `<u>text</u>` inline HTML is the underline convention (styled in CSS to look distinct from hyperlinks)
- The agent uses `vscode_askQuestions` for interactive decisions (CSS delivery, print intent, conflict resolution)
- When markdownlint and Pandoc are available, the agent uses them automatically for higher-quality Markdown processing
- Reference CSS: `styles/acb-large-print.css` (workspace) or `{{VSCODE_USER_PROMPTS_FOLDER}}/acb-large-print.css` (User-level)
- Reference HTML: `templates/acb-large-print-boilerplate.html` (workspace) or `{{VSCODE_USER_PROMPTS_FOLDER}}/acb-large-print-boilerplate.html` (User-level)

## Agent relationships

- `large-print-formatter` is the primary agent. It handles ACB-specific rules across HTML, CSS, Markdown, and Word
- `markdown-a11y-assistant` is a complementary agent for general WCAG markdown auditing (9 domains: links, alt text, headings, tables, emoji, Mermaid/ASCII diagrams, em-dashes, anchors, plain language)
- The large-print-formatter has handoff links to markdown-a11y-assistant for combined ACB + WCAG workflows
- `markdown-scanner`, `markdown-fixer`, and `markdown-csv-reporter` are internal sub-agents invoked by markdown-a11y-assistant -- not user-facing

## ACB rules (quick reference)

- Font: Arial only, 18pt body, 22pt headings, 20pt subheadings
- Alignment: flush left, ragged right (never justified)
- Emphasis: underline only (no bold for emphasis, no italic ever)
- Headings: proper hierarchy, no ALL CAPS, no skipped levels
- Lists: large solid bullets, no extra spacing between items
- Links: descriptive text (no bare URLs, no "click here")
- Spacing: 1 blank line between paragraphs, no blank lines between list items
- Digital supplement: WCAG 2.2 AA contrast (4.5:1), 400% zoom reflow, 1.5x line-height

## Cross-implementation sync (CRITICAL)

The ACB audit rules, fix logic, constants, and severity definitions exist in multiple implementations that MUST stay in sync:

| Concern                                  | Python (desktop)                                           | TypeScript (office-addin)                       | Flask Web (web)                | CSS/HTML (styles, agents)                                      |
| ---------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------- | ------------------------------ | -------------------------------------------------------------- |
| Constants (font sizes, margins, spacing) | `desktop/src/acb_large_print/constants.py`                 | `office-addin/src/constants.ts`                 | Imports from Python core       | `styles/acb-large-print.css`                                   |
| Audit rules + severity                   | `desktop/src/acb_large_print/constants.py` (`AUDIT_RULES`) | `office-addin/src/constants.ts` (`AUDIT_RULES`) | Imports from Python core       | Agent rules in `.github/agents/large-print-formatter.agent.md` |
| Audit logic (Word)                       | `desktop/src/acb_large_print/auditor.py`                   | `office-addin/src/auditor.ts`                   | Imports from Python core       | N/A                                                            |
| Audit logic (Excel)                      | `desktop/src/acb_large_print/xlsx_auditor.py`              | N/A                                             | Imports from Python core       | N/A                                                            |
| Audit logic (PowerPoint)                 | `desktop/src/acb_large_print/pptx_auditor.py`              | N/A                                             | Imports from Python core       | N/A                                                            |
| Audit logic (ePub)                       | `desktop/src/acb_large_print/epub_auditor.py`              | N/A                                             | Imports from Python core       | N/A                                                            |
| ePub metadata display (W3C Guide 2.0)    | `desktop/src/acb_large_print/epub_meta_display.py`         | N/A                                             | Imports from Python core       | Vendored JS in `vendor/daisy-a11y-meta-viewer/`                |
| Fix logic                                | `desktop/src/acb_large_print/fixer.py`                     | `office-addin/src/fixer.ts`                     | Imports from Python core       | N/A                                                            |
| Converter (MarkItDown)                   | `desktop/src/acb_large_print/converter.py`                 | N/A                                             | Imports from Python core       | N/A                                                            |
| Converter (Pandoc + WeasyPrint)          | `desktop/src/acb_large_print/pandoc_converter.py`          | N/A                                             | Imports from Python core       | N/A                                                            |
| Template builder                         | `desktop/src/acb_large_print/template.py`                  | `office-addin/src/template.ts`                  | Imports from Python core       | N/A                                                            |
| Web routes and templates                 | N/A                                                        | N/A                                             | `web/src/acb_large_print_web/` | N/A                                                            |

**When modifying ANY rule, constant, or check:**

1. Update ALL implementations -- never change one without the others
2. If adding a new audit rule ID in Python, add the same rule in TypeScript and update the agent
3. If changing a threshold (e.g., font size, margin tolerance), grep all three locations
4. The Python `constants.py` is the canonical source of truth -- TypeScript and CSS must match it
5. The Flask web app imports the Python core directly -- no sync needed for rule logic, but template rendering (help text, rule descriptions) auto-generates from `constants.py`

## Changelog (CRITICAL)

The file `CHANGELOG.md` at the repository root is the single source of truth for project history. It is rendered as HTML by the Flask web app at `/changelog`.

**When making ANY commit that adds features, fixes bugs, changes behavior, or modifies dependencies:**

1. Update `CHANGELOG.md` under the current `[Unreleased]` or version heading
2. Use Keep a Changelog format: `### Added`, `### Changed`, `### Fixed`, `### Removed`
3. Be specific -- name files, rule IDs, routes, and CLI flags that changed
4. Group related changes under descriptive `### Section` headings
5. The changelog is deployed inside the Docker image (`COPY CHANGELOG.md ./`) and served at `/changelog` -- never remove it from the build

## Execution preference (CRITICAL)

- Do NOT use Python environment setup/configuration tools (for example `configure_python_environment`) in this repository workflow.
- Use the already active shell environment/venv in the terminal session for tests and commands.
- If a command requires a different interpreter, ask the user first before changing environments.
