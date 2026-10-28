# PRD: GLOW (Guided Layout & Output Workflow) Accessibility Web Application

**Status:** Implemented (v4.0.0 released)
**Author:** Jeff Bishop, BITS
**Date:** May 4, 2026
**Target:** v4.0.0 (conversion hardening, re-audit flow integrity, documentation synchronization)

---

## Implementation Status

The Flask web application has been built and is ready for deployment. All core features described in this PRD are implemented. The following table summarizes what shipped in each release:

### v4.0.0 Addendum (Conversion hardening and public-doc consistency -- May 4, 2026)

v4.0.0 is a stabilization and release-integrity update focused on conversion
fidelity, safer workflow transitions, and accurate public release artifacts.

| Feature | Status | Notes |
|---------|--------|-------|
| CSRF-protected re-audit from Fix result | Done | `fix_result.html` now submits to `/audit/from-fix` via POST form with token, standards profile, and prior finding context. |
| OpenDocument conversion hardening | Done | Added `.fodt` native input handling and optional LibreOffice pre-conversion for `.ods/.fods/.odp/.fodp` before the existing MarkItDown plus Pandoc chain. |
| PDF table preservation in downstream conversions | Done | Added PyMuPDF table extraction path for PDF inputs so tables are preserved more reliably in Word/HTML/EPUB and related Pandoc-backed outputs. |
| Public documentation synchronization | Done | Changelog, release pointers, combined announcement artifacts, PRD status text, and user-guide release framing aligned to v4.0.0. |

### v3.1.0 Addendum (Braille Studio, Speech Pandoc pipeline, Status page, axe-core CI audit -- May 1, 2026)

Eleven new features and improvements shipped in v3.1.0. All are enabled by default and fully backward-compatible with v3.0.0 deployments.

| Feature | Status | Notes |
|---------|--------|-------|
| Braille Studio | Done | New `/braille/` tool for BANA-compliant text-to-braille and braille-to-text translation via liblouis. Supports UEB G1/G2 (current BANA standard), EBAE G1/G2 (legacy interop), and Computer Braille Code (8-dot). Unicode Braille (U+2800-U+28FF) and BRF ASCII output. BRF wrapped at BANA-standard 40 cells/line with optional embosser pagination. Tab in main navigation; download endpoints for `.brl`/`.brf`/`.txt`. Graceful degradation when liblouis absent. Feature-gated via `GLOW_ENABLE_BRAILLE` (default: enabled). 30 req/min rate limit. |
| Speech Studio Pandoc document preparation | Done | Uploaded documents (`.md`, `.rst`, `.docx`, `.pptx`, `.xlsx`, `.pdf`, `.epub`, etc.) are converted to normalized plain text via Pandoc before synthesis, guaranteeing consistent narration quality across all source formats. `.txt` files bypass Pandoc. Missing Pandoc returns a clear diagnostic error naming the dependency. |
| Speech Studio staged workflow UI | Done | The document narration flow now starts with an explicit **Next: Prepare text and estimate** step. Preview and download controls are hidden (semantic `hidden`/`aria-hidden` + JS) until preparation completes. Preparation errors auto-scroll into view. |
| Server Status page (`/status`) | Done | New human-readable diagnostics page at `/status` rendering health probes, service readiness (speech, braille), feature flag summary, full flag list, and raw JSON output. Exempt from the consent gate so operators can reach it without a browser session. |
| axe-core/Playwright WCAG 2.2 AA audit suite | Done | `web/e2e/tests/axe-audit.spec.mjs` audits all 17 public routes at WCAG 2.2 AA level on every CI run. Covers Speech Studio, Braille Studio, Settings, Guidelines, User Guide, About, Changelog, FAQ, Rules Reference, Feedback, Privacy Policy, Status, and the original 5 core routes. Also audits 4 interactive states: help accordions open, unavailability banners, dark mode, and mobile viewport (375x812 px). Critical/serious violations fail the build; moderate/minor surface as advisory warnings. SARIF upload to GitHub Code Scanning unchanged. |
| Speech and Braille feature flags (export/convert) | Done | Added `GLOW_ENABLE_EXPORT_SPEECH`, `GLOW_ENABLE_CONVERT_TO_SPEECH`, `GLOW_ENABLE_EXPORT_BRAILLE`, and `GLOW_ENABLE_CONVERT_TO_BRAILLE` (all default: enabled). Route guards apply at synthesis, document-prepare, and download endpoints. All four flags visible in Admin feature flags UI. |
| Speech and Braille health readiness in `/health` | Done | `/health` now reports `services.speech`, `services.braille`, `readiness.speech`, and `readiness.braille` alongside the existing feature flag data so operational issues are visible without guessing. |
| liblouis Docker deployment hardening | Done | `web/Dockerfile` installs `liblouis-bin`, `liblouis-dev`, `liblouis-data`, and `python3-louis` via apt, then copies the `louis` module into the pip Python 3.13 site-packages. A build-time smoke test (`python3 -c "import louis"`) fails the Docker build immediately if the binding is absent. The stale `pylouis` stub PyPI package has been removed. |
| CI Pandoc integration | Done | `deploy.yml`, `feature-flags-ci.yml`, and `accessibility-regression.yml` all install Pandoc via `apt-get` before the web test suite so the full Speech Studio document-prepare path is exercised in CI. |
| Speech route regression test suite | Done | `web/tests/test_speech_routes.py` covers staged prepare action rendering, Pandoc-required behavior, text extraction paths, and persistence of `speech_rendered.txt` and `speech_source.txt` artifacts. |
| `/status` consent exemption and braille nav regression test | Done | `/status` added to consent-gate exemptions. `test_main_nav_shows_braille_tab_when_enabled` added to `web/tests/test_braille.py` to guard tab visibility when `GLOW_ENABLE_BRAILLE` is set. |

### v3.1.0 Roadmap Additions Implemented (11-item core pack)

The roadmap items requested in this cycle were implemented as a single core
feature pack and exposed through explicit server-side feature flags.

| Roadmap Item | Status | Entry Point | Feature Flag |
|-------------|--------|-------------|--------------|
| 1.5 Back-translation quality scoring | Done | Braille result panel (`/braille/`) | `GLOW_ENABLE_BRAILLE_BACK_TRANSLATION_SCORE` |
| 2.5 Pronunciation dictionary management | Done | Speech pre-processing + core admin/operator surface | `GLOW_ENABLE_SPEECH_PRONUNCIATION_DICTIONARY` |
| 2.6 Real-time streaming audio preview | Done | `POST /speech/stream` | `GLOW_ENABLE_SPEECH_STREAM` |
| 3.3 Table accessibility advisor | Done | Core accessibility intelligence endpoint (`POST /magic/table-advisor`) | `GLOW_ENABLE_TABLE_ADVISOR` |
| 3.4 Reading order detection (PDF) | Done | Core accessibility intelligence endpoint (`POST /magic/reading-order`) | `GLOW_ENABLE_READING_ORDER_DETECTION` |
| 3.5 OCR for scanned PDFs | Done | Core accessibility intelligence endpoint (`POST /magic/ocr`) | `GLOW_ENABLE_PDF_OCR` |
| 3.6 Document compare and change tracking | Done | Core accessibility intelligence endpoint (`POST /magic/compare`) | `GLOW_ENABLE_DOCUMENT_COMPARE` |
| 4.3 ODT export in Convert | Done | Convert direction `to-odt` | `GLOW_ENABLE_CONVERT_TO_ODT` |
| 7.3 Cognitive accessibility profile | Done | Settings + global UI behavior | `GLOW_ENABLE_COGNITIVE_PROFILE` |
| 7.4 Forced-colors/high-contrast support | Done | Global CSS + base template mode classes | `GLOW_ENABLE_FORCED_COLORS_MODE` |
| 9.1 Public rule contribution portal | Done | Rules contribution surface + `/magic/rules/propose` + `/magic/rules/proposals` | `GLOW_ENABLE_RULE_CONTRIBUTIONS` |

Implementation notes:

- The 3.x document intelligence features (3.3–3.6) are core platform
  capabilities exposed as JSON APIs and interactive forms.
- OCR is intentionally best-effort and reports clear unavailability when
  runtime dependencies are missing (`pytesseract`, Pillow, or Tesseract binary).
- The pronunciation dictionary is active in typed preview, voice preview,
  typed download, document preview, document download, and stream routes.

Deployment requirements and dependencies for this core pack:

- `pandoc` required for `to-odt` conversion and Speech document rendering
- `python3-louis` + `liblouis-bin` + `liblouis-dev` + `liblouis-data` required
  for Braille translation and back-translation quality scoring
- Optional OCR stack: Tesseract binary + `pytesseract` + Pillow; if missing,
  OCR endpoints return explicit unavailability status rather than failing hard
- Frontend/CI dependencies: `@axe-core/playwright`, `@axe-core/cli`, Playwright
  Chromium, and SARIF converter script remain required in accessibility CI

GitHub integration points (current vs planned):

- Current: accessibility SARIF artifacts are uploaded to GitHub Code Scanning
  from CI and visible in the Security tab.
- Current: rule proposals persist locally in SQLite for moderation/review.
- Planned: optional proposal-to-GitHub-Issue and approved-proposal-to-PR-draft
  automation remains roadmap scope and is not yet active in v3.1.0.

### v3.0.0 Addendum (Community-driven platform milestone -- April 30, 2026)

All requested feature areas from the 2.5 through 2.9 cycle were completed and unified in this release.

| Feature | Status | Notes |
|---------|--------|-------|
| Speech Studio full workflow | Done | Typed synthesis, uploaded document-to-speech, snippet preview, full audio download, settings persistence, and admin voice management. Document upload uses Pandoc for text extraction (all non-`.txt` formats). Pandoc must be installed on the server for the upload workflow; `.txt` files work without Pandoc. |
| Convert-to-Speech seamless handoff | Done | Convert tab includes a Speech direction that redirects to Speech Studio with token handoff, avoiding re-upload |
| Adaptive conversion estimation | Done | Real conversion telemetry (word count, source size, measured processing time, speed/voice) feeds blended estimates over time for this deployment |
| Speech analytics visibility | Done | Admin and About pages expose speech usage patterns by mode/voice/speed/pitch |
| Anthem download analytics | Done | Home page includes tracked Let it GLOW theme download; count surfaced in About/Admin analytics |
| Navigation and Quick Start integration | Done | Dedicated Speech tab and Quick Start Speech action with token handoff |
| Cross-feature polish | Done | Settings, speech UX, and progress announcement cadence are aligned across workflows |
| **[NEW v3.0.0 Extended] 8 UX workflow optimizations** | Done | Post-fix re-audit button, convert-to-audit bridge, batch audit prominence, enhanced findings diff, session audit history, smart next-step guidance, reviewer feedback foundation, session restore on expiry |
| **[NEW v3.0.0 Extended] 15 power user features** | Done | Toast framework, standards profile propagation, Ctrl+U shortcut, session keep-alive, webhook callbacks, configurable share TTL, session-based auto-diff, large-file rate limiting, voice preview, audit history, AI alt-text API, CSV export, EPUB conformance detection, template context injection, full backward compatibility |

### v3.0.0 Extended Features (April 30, 2026 release)

**8 UX Workflow Optimizations**

These features were requested by community members working through the accessibility cycle repeatedly and looking for ways to reduce friction in the audit→fix→reaudit workflow.

| Feature | Route/File | Status |
|---------|-----------|--------|
| Post-fix re-audit button | `fix_result.html` to `/audit/from-fix` | Done |
| Convert-to-audit bridge | `convert_result.html` to `/audit/from-convert` | Done |
| Prominent batch audit CTA | `audit_form.html` callout section | Done |
| Enhanced findings diff sections | `audit_report.html` diff-findings-detail | Done |
| Session audit history (5 entries) | `audit.py` session storage | Done |
| Smart next-step guidance in Convert | `convert_result.html` conditional | Done |
| Reviewer feedback loop foundation | `shared_report.html` form | Done |
| Session restore on expiry | `audit_form.html` history display | Done |

**15 Power User & Integrator Features**

These features enable advanced workflows, custom integrations, and operational control for organizations running GLOW on premise.

| Feature | Route/File | Status | Notes |
|---------|-----------|--------|-------|
| Toast notification framework | `a11y-enhancements.js` | Done | Keyboard navigable, screen reader compatible |
| Standards profile propagation | `audit.py`, `fix.py` | Done | ACB 2025, APH Submission, Combined Strict flow through workflow |
| Ctrl+U keyboard shortcut | `a11y-enhancements.js` | Done | Focus file picker from anywhere |
| Session keep-alive | `a11y-enhancements.js` | Done | `/health` ping every 15 min |
| Webhook callbacks | `audit.py` _fire_webhook | Done | HTTPS only, HMAC-SHA256 `X-GLOW-Signature` |
| Configurable share TTL | `report_cache.py` SHARE_TTL_HOURS | Done | Env var, default 4h, exposed to templates |
| Session-based auto-diff | `audit.py` _compute_audit_diff | Done | Same session, 2 audits, auto-comparison |
| Large-file rate limit | `audit.py` _is_small_upload | Done | >10 MB → 1/min (vs 6/min standard) |
| Voice preview endpoint | `/speech/voice-preview` | Done | POST endpoint, 20/min rate limit |
| Audit history in session | `audit.py` session storage | Done | Up to 5 entries with scores, timestamps |
| AI alt-text suggestions | `/audit/suggest-alt-text` | Done | Requires ai_alt_text_enabled, image extraction from DOCX |
| CSV export of post-fix findings | `/fix/csv/<token>` | Done | Leverages findings_to_csv_bytes |
| EPUB conformance detection | `ace_runner.py` _extract_ace_conformance | Done | W3C level exposed via `ace_conformance` attr |
| Template context injection | `app.py` context_processor | Done | `audit_history`, `share_ttl_hours` always available |
| Backward compatibility | All files | Done | All features opt-in, non-breaking |

### v2.8.0 Addendum (Community-requested UX and security features)

All features in this release were sourced directly from BITS and blind and low-vision community feedback. Thank you to everyone who filed issues, sent suggestions, and tested pre-release builds.

| Feature | Status | Notes |
|---------|--------|-------|
| Quick Start full handoff (audit/fix/convert without re-upload) | Done | `GET /audit/?token=...` and `GET /convert/?token=...` resolve an existing upload session and prefill the form. POST handlers honour `prefill=1` to skip re-upload. All three tools (Audit, Fix, Convert) now complete the single-upload vision from Quick Start. |
| Passphrase-protected shared reports | Done | Optional 4-200 char passphrase on Audit form. Hash stored as PBKDF2-SHA256 (200k iterations, 16-byte random salt). Share page, CSV download, and PDF download all gate on passphrase. Unlock template (`share_unlock.html`). New `set_share_passphrase()`, `share_requires_passphrase()`, `verify_share_passphrase()` in `report_cache.py`. |
| User-defined font sizes | Done | Fix and Template forms expose a Font Sizes fieldset for body (Normal) and H1-H6 overrides. Values clamped 8-96pt. Propagates through auditor, fixer, and template pipelines via `style_size_overrides` kwarg. `effective_styles()` and `effective_min_body_pt()` helpers in `constants.py` (Python) and `effectiveStyles()` / `effectiveMinBodyPt()` / `StyleSizeOverrides` in TypeScript. List Bullet and List Number inherit body override. |
| Findings grouped by rule in audit report | Done | `_findings_table.html` partial groups occurrences of the same rule ID into a single row with count badge and expandable location list. Applied to single, batch combined, and batch individual reports. CSV export unchanged (one row per occurrence). |
| Scoring and grade integrity refinements | Done | Fixed score/grade presentation drift and clarified weighted-penalty behavior so repeated findings are accounted consistently while grouped-table rendering remains presentation-only. Fix result summary now explicitly distinguishes filtered display mode from full post-fix scoring. |

### v2.7.0 Addendum (UX, scorecard, and streamlined workflow updates)

All features below shipped in v2.7.0 (May 2026) and are fully implemented.

| Feature | Status | Notes |
|---------|--------|-------|
| Export folded into Convert | Done | `/export` redirects (301) to `/convert`. CMS Fragment is a first-class direction in Convert. `GLOW_ENABLE_EXPORT_HTML` now gates the CMS Fragment direction in Convert rather than a separate route. |
| Compliance score headline on audit report | Done | Grade letter (A–F) and numeric score displayed prominently at the top of every audit report. Color-coded by grade. |
| Compliance grade on Fix result after-box | Done | Grade letter shown in the "After" score box on fix result so users see the before/after grade improvement at a glance. |
| Quick Wins filter on audit report | Done | Bar above findings table showing auto-fixable count; toggle button filters to fixable findings only; "Fix These" button links to Fix. |
| Shareable audit report URLs | Done | UUID-keyed report cache (`report_cache.py`) stores rendered HTML for 1 hour. Share link shown on every audit report. Share token is separate from upload token; cached HTML only — original document never accessible via share link. |
| Drag-and-drop upload | Done | All upload forms support drag-and-drop with visual drop zone. |
| Next-step cards on audit report | Done | "What's Next" section with context-aware callout cards for Fix, Convert, and manual guidance depending on doc format and findings. |
| Dark mode support | Done | User-selectable Light / Dark / Auto theme via footer dropdown and Settings page; preference stored in `localStorage`; CSS keys off `html[data-theme]` attribute so explicit user choice wins over `prefers-color-scheme`; all contrast ratios meet WCAG 2.2 AA in both modes. |
| HTML preview on Convert result | Done | Inline live preview iframe shown on Convert result page for HTML output; collapses to avoid layout shift on smaller viewports. |
| CMS Fragment clipboard copy | Done | One-click "Copy to Clipboard" button on Convert result for CMS Fragment output. Toast notification confirms copy success. |
| Toast notification system | Done | `toast.js` provides screen-reader-announced status toasts for clipboard actions and async UI feedback. |
| Print and mobile CSS polish | Done | Responsive layout improvements; `@media print` hides nav and non-essential chrome. |
| Streamlined Audit → Fix (no re-upload) | Done | `GET /fix/from-audit/<token>` and `POST /fix/from-audit/<token>` routes load an existing audit session file into Fix without requiring re-upload. "Fix This Document" and "Fix These Auto-Fixable Issues" buttons on audit report use the token-based route when session is active. |
| Streamlined Fix → Re-Audit (no re-upload) | Done | `POST /audit/from-fix` route re-audits the fixed file from an existing session. "Re-Audit Fixed Document" button on fix result is a form POST rather than a plain link -- no re-upload required. |
| Session expiry notice on fix form | Done | Redirect to fix form with `?notice=session_expired` when a from-audit token has expired; template shows an informational notice rather than an error. |
| Privacy policy updated for share token and audit retention | Done | Audit workflow description clarifies that uploaded files are retained briefly for the Fix shortcut and Chat. Shareable link behavior (HTML-only cache, 1-hour expiry) is described. Policy last-updated date updated to April 29, 2026. |
| Visitor counter | Done | SQLite unique-session visitor counter (`instance/visitor_counter.db`). One increment per browser session via `@app.before_request`; count displayed in footer as "Visitors: 1,234" and injected via context processor. |
| Tool usage analytics | Done | Per-tool use counts in `instance/tool_usage.db`. Six tools instrumented (Audit, Fix, Convert, Template Builder, BITS Whisperer, Document Chat). Failure-safe — never surfaces DB errors to users. |
| Admin analytics dashboard | Done | `GET /admin/analytics` (admin-only) shows total visitors, total tool uses, per-tool table with share percentages and last-used timestamps. Linked from Admin Queue. |
| About page usage stats | Done | Public "Usage Statistics" section on `/about/` shows visitor count, total tool uses, and per-tool counts (zero-count tools hidden). |

### Post-v2.0 Addendum (v2.5.0 quality and release-safety updates)

This PRD remains focused on the original platform scope. Since v2.0, additional quality safeguards were added in v2.5.0:

- PDF scanned-content detection now uses smarter page-image coverage logic and includes low-resolution scan detection (`PDF-IMAGE-RESOLUTION`) to improve OCR readiness guidance.
- EPUB auditing now supports optional EPUBCheck integration, mapping validation output to structured findings (`EPUBCHECK-ERROR`, `EPUBCHECK-WARNING`).
- Web release validation now includes an automated accessibility regression gate (Playwright + axe scan converted to SARIF).

For implementation-level detail and release chronology, see `CHANGELOG.md` and `docs/RELEASE-v2.5.0.md`.

| Feature | Status | Notes |
|---------|--------|-------|
| Audit page (Full / Quick / Custom modes) | Done | Rule filtering by severity, severity-grouped checkboxes |
| Fix page (Full / Essentials / Custom modes) | Done | Before/after scores, download fixed .docx, review-required warnings |
| Standards Profiles (ACB / APH / Combined Strict) | Done | ACB default is backward-compatible (no behavior change); APH profile filters to implemented APH-aligned checks; Combined Strict shows all implemented checks |
| Template generation | Done | Title, sample content, binding margin options, plus profile-aware defaults (ACB baseline, APH-oriented, Combined Strict behavior) |
| Settings page | Done | Cookie opt-in preferences for default profiles/modes/options across Audit, Fix, Template, Export, and Convert |
| HTML export (Standalone ZIP + CMS fragment) | Done | Both modes working |
| Convert to Markdown (MarkItDown) | Done | .docx, .xlsx, .pptx, .pdf, .html, .csv, .json, .xml, .epub |
| Convert to HTML (Pandoc) | Done | .md, .docx, .rst, .odt, .rtf, .epub -- ACB formatting, binding margin, print stylesheet options |
| Convert to Word (Pandoc) | Done | .md, .rst, .odt, .rtf, .html, .epub -- produces .docx for editing or audit/fix |
| Convert to EPUB 3 (Pandoc) | Done | .md, .docx, .rst, .odt, .rtf, .html -- lightweight EPUB with ACB CSS |
| Convert to PDF (Pandoc + WeasyPrint) | Done | .md, .docx, .rst, .odt, .rtf, .epub, .html -- ACB print formatting, binding margin option |
| Convert to EPUB/DAISY (DAISY Pipeline) | Done | Word to EPUB 3, HTML to EPUB 3, EPUB to DAISY 2.02, EPUB to DAISY 3 |
| Markdown and PDF audit | Done | Basic page-level structure checks |
| About page | Done | Mission, organizations, standards, dependencies, acknowledgments |
| Guidelines reference page | Done | Full ACB spec + WCAG supplement from constants.py |
| Feedback page with SQLite storage | Done | Password-protected review page via FEEDBACK_PASSWORD env var |
| CSRF protection (Flask-WTF) | Done | All forms have hidden csrf_token |
| Rate limiting (Flask-Limiter) | Done | 120 requests/minute default |
| Structured logging | Done | Timestamp + level + logger name format, LOG_LEVEL env var |
| Favicon (SVG) | Done | "LP" monogram |
| Flash message support | Done | Category-based flash rendering in base template |
| Docker + Compose | Done | Non-root user, health check, feedback volume |
| Test suite | Done | Smoke tests, error handling, feedback, accessibility checks, integration |
| Contextual help (details/summary) | Done | Every form page has expandable help accordions |
| WCAG 2.2 AA compliance | Done | lang, landmarks, labels, contrast, skip nav, focus indicators |
| No JavaScript required | Done | All functionality works without JS |
| AI heading detection (fix page) | Done | Two-tier faux heading detection: heuristic scoring (10 signals) + optional AI refinement via GLOW's cloud AI service. Web form fieldset with enable, AI toggle, confidence threshold. |
| Interactive heading review (fix page) | Done | When heading detection finds candidates in a .docx, users review a table of candidates with confidence scores, heuristic signals, and adjustable heading levels before fixes are applied. New `fix_review_headings.html` template and `/fix/confirm` POST route. |
| AI auto-detection (fix page + desktop GUI) | Done | `ai_heading_fix_enabled()` checks the configured AI gateway. Web form auto-checks the AI checkbox when the service is enabled; desktop GUI checks the local Ollama probe. |
| Desktop GUI heading detection | Done | Step 3 Options panel in wxPython wizard adds paragraph indent, heading detection, and AI toggle controls. AI checkbox auto-checks when local Ollama is available (desktop-only feature). |
| Detailed fix records (fix page) | Done | FixRecord dataclass tracks every fix with rule ID, category, description, location. Accordion UI groups fixes by category. |
| Heading-rule suppression in fix scoring | Done | When heading detection is disabled, `ACB-FAUX-HEADING` is suppressed from post-fix scoring and shown as a suppressed rule in Fix Results. |
| Pre-fix small-text pagination warning | Done | Fix Results warns when pre-fix body text appears below 18pt because ACB normalization can increase page count. |
| List indentation control discoverability | Done | List indent fields are always visible and enable/disable in place based on the flush-list toggle. |
| VML decorative image handling | Done | Legacy VML shapes with explicit `alt=""` are treated as decorative and are not flagged as missing alt text. |
| Quick Rule Exceptions (Fix and Audit) | Done | New collapsible section in Fix and Audit forms with toggles to suppress `ACB-LINK-TEXT`, `ACB-MISSING-ALT-TEXT`, or `ACB-FAUX-HEADING` per operation without entering Custom mode. |
| Preserve centered headings option | Done | Fix form checkbox to skip alignment override for heading-styled paragraphs, preserving intentional heading center-alignment. Heading alignment findings are suppressed when option is enabled. |
| Per-level list indentation support | Done | Fix form and backend (auditor/fixer) now support per-level list indentation: Level 1, Level 2, Level 3 with separate indent targets. Auditor detects paragraph list style level and compares against level-specific expected values. Fixer applies per-level target indents. |
| Allowed heading-level controls (Fix/Settings/Template) | Done | Users can restrict heading detection/review/conversion to selected heading levels; heading review dropdown options and confirm/apply honor allowed levels end-to-end; template sample content follows selected allowed heading levels and can be persisted in Settings. |
| Dedicated FAQ page | Done | New `/faq/` route with accordion-style FAQ entries covering quick exceptions, heading preservation, per-level indentation, page-count growth, decorative images, VML handling, and known limitations. Linked in main nav footer. |

### v2.0 Release Features (April 2026)

| Feature | Status | Notes |
|---------|--------|-------|
| GLOW (Guided Layout & Output Workflow) Quick Start path | Done | New `/process` flow: upload first, then choose context-aware actions for the uploaded file type. |
| BITS Whisperer audio transcription | Done | New `/whisperer` route for MP3/WAV/M4A/OGG/FLAC/AAC/Opus transcription to Markdown or Word using the Whisper API with server-side normalization and cleanup. |
| Consent and privacy gate | Done | New `/consent` route for first-visit agreement with secure consent cookie and reset controls. |
| MarkItDown 0.2+ integration | Done | Expanded support for image inputs and broader conversion workflows. |
| Vision-ready OCR path | Done | Cloud-ready path reserved for future multimodal interpretation; v2.0 keeps core document workflows stable first. |
| Capacity-aware protective gating | Done | AI/audio/vision concurrency protection with busy response behavior and health metrics. |
| Whisperer preflight estimate + confirmation | Done | Audio metadata estimate shown before transcription starts; users explicitly confirm before proceeding. |
| Whisperer background queue mode | Done | Long audio jobs can opt into background mode with queueing, position-aware processing, and shared audio capacity gating. |
| Whisperer secure retrieval (link + password) | Done | Completed background jobs are retrieved through single-use secure links protected by user-created retrieval passwords. |
| Whisperer lifecycle email notifications | Done | Queued, started, completed, and content-cleared notifications are sent when email service is configured. |
| Admin-only authentication hub | Done | New `/admin/login` flow supports email magic links and configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress) with provider visibility gated by configuration. |
| Admin request/approval workflow | Done | Users can request admin access; approval/denial is controlled by existing approved admins via admin UI. |
| Admin audio queue dashboard | Done | Approved admins can inspect queue/running/failed audio jobs and perform cancel/re-queue operations. |
| Expanded Document Chat | Done | New `/chat` route with heading-based conversation history, export to Markdown/Word/PDF, and accessibility-focused tool calling. |
| Accessibility-focused agent categories in chat | Done | Compliance, Structure, Content, and Remediation tool groups for in-context Q&A and fix guidance. |
| Chat online help + guided question cards | Done | In-page guided cards and examples for first-time chat users; keyboard and screen-reader friendly. |
| Privacy transparency updates | Done | Privacy policy and UI language updated to reflect retention windows, cloud AI usage, and non-AI opt-out paths. |
| Long-job retention reliability | Done | Active audio transcription jobs keep temporary workspace alive until completion so stale cleanup does not interrupt long-running conversions. |

### Deviations from Plan

- **Feedback system added** -- not in original PRD. SQLite-backed with password-protected review page.
- **Caddy not included in docker-compose.yml** -- shipped as a separate Caddyfile reference in deployment.md. The compose file exposes port 8000 directly; Caddy is added at deployment time.
- **Gunicorn workers reduced to 2** -- Docker default; override via environment variable at deployment.
- **Flash messages added** -- base template supports category-based flash rendering for future use.
- **Rate limiting added** -- 120 req/min default via Flask-Limiter (originally listed as out of scope).
- **CSRF protection added** -- Flask-WTF CSRFProtect on all forms (originally not specified).

---

## Problem Statement

The ACB Large Print Tool currently requires one of three things to use: VS Code with Copilot Chat (for the agent toolkit), a desktop Python install (for the CLI), or a PyInstaller executable (for the GUI wizard). All three assume local software installation. This means:

- Organizations that want to check a single document must download and install software first
- Non-technical staff (chapter presidents, newsletter editors, meeting coordinators) find the installation barrier too high
- IT departments at ACB affiliates may not allow installing arbitrary executables
- The tool cannot be demonstrated at conferences or training sessions without pre-configuring every attendee's machine
- Mobile and Chromebook users are completely excluded

Meanwhile, the core engine -- audit, fix, template builder, and HTML export -- is a clean Python library with no GUI dependency. Every function takes a file path in and returns data or a file path out. The business logic is ready to serve HTTP requests today.

## Solution

Build a Flask web application that wraps the existing `acb_large_print` Python library in a browser-accessible interface. In GLOW (Guided Layout & Output Workflow), users upload a `.docx`, `.xlsx`, or `.pptx` file through a web form, choose an operation (audit, fix, create template, export to HTML), and receive results in the browser or as a file download. No installation. No accounts. No login.

For v2.0, the product scope expands into **GLOW (Guided Layout & Output Workflow)** as a guided end-to-end accessibility platform: users can upload once, run the right operation, ask agentic questions in context, and export both fixed outputs and conversation artifacts.

The web app will:

- Accept `.docx`, `.xlsx`, and `.pptx` uploads (max 16 MB) and validate them server-side
- Provide all four core operations: audit (all three formats), fix (Word auto-fix; Excel/PowerPoint audit guidance), template creation (Word), and HTML export (Word)
- Display audit reports directly in the browser as accessible HTML
- Return fixed documents and templates as immediate file downloads
- Delete all uploaded and generated files immediately after the response is sent
- Meet WCAG 2.2 AA from day one -- this is an accessibility tool and must be accessible itself
- Coexist alongside the existing CLI, GUI, and VS Code agent -- the Flask app is a new interface, not a replacement
- Deploy via Docker for hosting flexibility (RackNerd VPS, Hetzner Cloud, or any Docker host)
- Provide rich contextual help via native HTML `<details>/<summary>` accordions on every page -- no JavaScript required, fully keyboard and screen reader accessible
- Let users control which rules are checked (audit) and which fixes are applied (fix) via three preset modes: Full, Quick/Essentials, and Custom (individual rule checkboxes grouped by severity)
- Provide a dedicated `/settings` page so teams can persist preferred defaults (profiles, modes, and options) with explicit cookie opt-in
- Include a dedicated `/guidelines` page with the complete ACB Large Print specification and WCAG 2.2 supplement as browsable, searchable reference content
- Auto-generate all help text and rule descriptions from the canonical `constants.py` rule metadata -- a single source of truth ensures the web UI stays in sync with the CLI, GUI, and VS Code agent
- Provide a dedicated `/chat` experience with accessibility-focused agent categories (Compliance, Structure, Content, Remediation) so users can interrogate document content and receive actionable guidance
- Include guided question cards and in-page examples for chat so first-time users can ask high-value questions immediately
- Support conversation export (Markdown, Word, PDF) for training, compliance evidence, and editorial handoffs
- Support optional Whisperer background processing for long recordings using explicit user opt-in, secure retrieval links, and password verification
- Use shared audio gating for both foreground and background Whisperer jobs so background work is counted as active server workload

## User Stories

1. As a chapter newsletter editor, I want to upload my meeting agenda `.docx` and get an ACB compliance report in my browser, so that I can see what needs fixing without installing any software.
2. As a chapter newsletter editor, I want to upload a non-compliant `.docx` and download a fixed version with one click, so that I can produce compliant documents without understanding the ACB specification.
3. As a conference presenter, I want to point attendees to a URL where they can try the tool instantly, so that training sessions focus on the ACB rules rather than software installation.
4. As an ACB affiliate officer, I want to generate a pre-configured Word template from the web UI, so that future documents start compliant by default.
5. As a web content manager, I want to upload a `.docx` and download a standalone HTML version with ACB-compliant CSS, so that I can publish accessible content on our website.
6. As a web content manager, I want to export a CMS-ready HTML fragment with embedded CSS, so that I can paste it directly into WordPress or Drupal without breaking my site theme.
7. As a sighted user helping a blind colleague, I want the web UI to be fully keyboard-navigable with clear focus indicators, so that we can use it together on any device.
8. As a screen reader user, I want all form controls to have associated labels and all status messages to use ARIA live regions, so that I know what is happening at each step.
9. As a mobile user at a conference, I want the web app to work on my phone's browser, so that I can check a document without needing a laptop.
10. As a Chromebook user, I want to access all features through the browser, so that I am not excluded by platform limitations.
11. As the BITS president, I want uploaded documents to be deleted immediately after processing, so that sensitive organizational documents are not stored on third-party servers.
12. As the BITS president, I want the hosting cost to be under $80 per year, so that this is sustainable as a free community tool without ongoing fundraising.
13. As a developer contributing to the project, I want the Flask app to import the existing core library without modification, so that bug fixes and new rules flow through to the web UI automatically.
14. As a developer, I want the web app packaged as a Docker container, so that deployment is reproducible across any hosting provider.
15. As a user with low vision, I want the web UI styled with the same ACB Large Print CSS used for document output, so that the tool itself demonstrates the formatting it enforces.
16. As a user submitting a document, I want clear error messages when my upload fails (wrong file type, too large, corrupted), so that I know how to fix the problem.
17. As a user viewing an audit report, I want findings sorted by severity with clear visual and semantic grouping (critical, high, medium, low), so that I can prioritize fixes.
18. As a user requesting a template, I want to specify a document title, whether to include sample content, and whether to add binding margins, so that the template fits my needs.
19. As a user exporting to HTML, I want to choose between standalone (full HTML + CSS) and CMS fragment (embedded CSS), so that I get the right format for my publishing workflow.
20. As a system administrator, I want the Docker container to run as a non-root user with no write access outside the temp directory, so that the attack surface is minimized.
21. As a system administrator, I want the app to enforce upload size limits and MIME type validation at the application layer, so that malicious files are rejected before touching the processing pipeline.
22. As a returning user, I want to see brief explanations of each operation on the landing page, so that I remember which option to choose without re-reading documentation.
23. As a user who just completed an audit, I want a clear call-to-action to fix the document, so that the next step is obvious.
24. As a user processing a fix, I want to see a before/after compliance score, so that I understand the improvement.
25. As a user, I want the page to work without JavaScript, so that browser extensions, corporate proxies, and assistive technologies that disable scripts do not break functionality.
26. As a BITS board member, I want the tool branded as a BITS community project, so that users understand its origin and can report issues.
27. As a user on a slow connection, I want feedback during file upload and processing, so that I know the app has not frozen.
28. As a user, I want the audit report to link each finding to the relevant ACB guideline section, so that I can look up the rationale for each rule.
29. As a first-time user, I want contextual help on every page explaining what the operation does, what gets changed, and why, so that I understand each step without reading external documentation.
30. As an experienced user running an audit, I want to choose between Full Audit (all rules), Quick Audit (critical and high only), or Custom Audit (pick individual rules), so that I get the right level of detail for my workflow.
31. As an experienced user running a fix, I want to choose between Full Fix (all auto-fixable rules), Essentials Fix (critical and high only), or Custom Fix (pick individual fix categories), so that I control how much the tool changes in my document.
32. As a user exploring the Custom Audit/Fix option, I want rules grouped by severity (Critical, High, Medium, Low) inside expandable `<details>` accordions, so that I can quickly find and toggle related rules.
33. As a user learning the ACB specification, I want a dedicated Guidelines page on the web app that presents the complete ACB Large Print rules and WCAG 2.2 digital supplement, so that I can reference the standard without leaving the tool.
34. As a screen reader user, I want all help accordions to use native HTML `<details>/<summary>` elements rather than JavaScript widgets, so that my assistive technology announces expand/collapse states correctly.
35. As a user on the fix results page, I want to see which rules were applied and which were skipped (when using Essentials or Custom mode), so that I understand exactly what changed.
36. As a user of GLOW (Guided Layout & Output Workflow), I want to ask natural-language questions about my uploaded document and get answers grounded in the actual content, so that I can understand and remediate issues faster.
37. As a screen reader user, I want chat conversation history to be structured with clear heading hierarchy by turn, so that I can navigate long conversations efficiently.
38. As a trainer, I want guided chat cards with example prompts, so that new users can learn what kinds of accessibility questions are most useful.
39. As a compliance reviewer, I want to export chat sessions to Markdown, Word, or PDF, so that Q&A reasoning can be attached to review artifacts.
40. As an operator, I want chat workloads to obey protective AI capacity gating, so that one heavy session does not degrade service for others.
41. As a user transcribing a long meeting recording, I want to opt into background processing and receive status emails, so that I do not have to keep the browser open.
42. As a privacy-conscious user, I want background transcription retrieval to require both a secure link and a password I set at submission time, so that transcript access remains controlled.
43. As an operator, I want foreground and background audio transcription to share the same concurrency gate, so that queued jobs cannot bypass server capacity limits.
44. As a user, I want to be notified when unretrieved background transcription content has been cleared after retention expiry, so I understand I must upload and process again.
45. As an administrator, I want an admin-only sign-in entry point with configurable SSO providers and email magic-link fallback, so operations can be secured without enabling public user accounts.
46. As an organization owner, I want admin access requests to require explicit approval by an existing admin, so privileged access is controlled and auditable.
47. As an operations admin, I want a queue dashboard that shows audio conversion states and allows cancel/re-queue actions, so I can manage long-running background conversions.

## v2.0 Addendum: Expanded Agentic Accessibility Experience

GLOW (Guided Layout & Output Workflow) 2.0 adds a major interaction model beyond form submission: users can ask targeted questions and invoke accessibility-aware tools through chat. In v2.0 this runs through a centralized OpenRouter gateway with privacy-aware provider controls and budget enforcement.

### Chat Route and Interaction Model

- Route: `/chat`
- Input: uploaded document token + user question
- Output: grounded answer + list of tools called + optional exportable history
- History model: turn-based (`Turn 1`, `Turn 2`, ...) with heading hierarchy for assistive technology navigation

### Agent Categories and Tool Groups

The chat layer is organized into five accessibility-first groups with 24 total callable tools:

1. **Document** (7 tools)
  - `extract_table` -- extract a table by name or 0-based index
  - `find_section` -- find and return a section by heading keyword
  - `search_text` -- keyword search returning matching lines with line numbers
  - `get_document_stats` -- word count, lines, characters, headings, reading time
  - `summarize_section` -- return section text for Llama reasoning
  - `list_headings` -- list all headings with hierarchy indentation
  - `get_images` -- image listing (scanned PDF / vision model path)

2. **Compliance Agent** (4 tools)
  - `run_accessibility_audit` -- run full GLOW audit engine; return severity summary and populate cache
  - `get_compliance_score` -- score/100 with critical/high/medium/low distribution
  - `get_critical_findings` -- critical and high findings with rule ID, description, and fix type
  - `get_auto_fixable_findings` -- findings that GLOW Fix can correct automatically

3. **Structure Agent** (4 tools)
  - `check_heading_hierarchy` -- detect skipped heading levels (ACB-HEADING-HIERARCHY)
  - `find_faux_headings` -- detect bold body paragraphs acting as headings (ACB-FAUX-HEADING)
  - `check_list_structure` -- inspect list nesting depth and consistency
  - `estimate_reading_order` -- reading-order risk from table count and layout signals

4. **Content Agent** (4 tools)
  - `check_emphasis_patterns` -- detect italic and bold-abuse (ACB-NO-ITALIC, ACB-BOLD-HEADINGS-ONLY)
  - `check_link_text` -- flag bare URLs and generic link phrases (ACB-LINK-TEXT)
  - `check_reading_level` -- sentence and word complexity heuristics
  - `check_alignment_hints` -- detect center/right alignment overrides (ACB-ALIGNMENT)

5. **Remediation Agent** (5 tools)
  - `explain_rule` -- plain-language explanation with why/fix for any ACB rule ID
  - `suggest_fix` -- targeted fix instructions for a given rule
  - `prioritize_findings` -- rank all findings by severity and auto-fixability
  - `estimate_fix_impact` -- score improvement estimate after auto-fix
  - `check_image_alt_text` -- check Markdown images for missing alt text (ACB-MISSING-ALT-TEXT)

### Online Help and Guided Cards

The `/chat` template includes:

- a "What can I ask?" help accordion
- guided prompt cards/examples for common tasks
- explicit tool capability listing
- export controls
- privacy and retention notice

All help uses semantic HTML and native interaction patterns aligned to WCAG 2.2 AA.

## v2.0 Cloud AI Implementation Plan

The cloud transition planning that previously lived in separate working documents is now part of the PRD. The product direction is intentionally conservative: keep the rule-based core intact, move only the AI-dependent features to cloud services, and preserve clear non-AI paths for users who do not want AI involved.

### Principles

- No public account requirement for end users
- AI use only where it adds clear value: Document Chat and Whisperer
- Rule-based workflows remain available without AI
- Privacy-aware routing and short retention by default
- Hard monthly budget and per-session quota enforcement

### Implemented cloud architecture

- **Document Chat:** OpenRouter-backed gateway with grounded pre-flight tool dispatch, quota tracking, and health checks
- **BITS Whisperer:** Whisper API transcription with server-side format normalization, background queueing, and secure retrieval
- **Large-workload resilience:** bounded AI queue wait windows for heavy requests plus transient retry/backoff on OpenRouter rate-limit and 5xx failures
- **Budget controls:** monthly spend ledger, daily chat limits, monthly audio-minute limits
- **Operational visibility:** `/health` exposes provider reachability and budget readiness

### OpenRouter production roadmap now adopted for GLOW

1. Use explicit privacy-reviewed model lists before broadening router choices.
2. Apply provider privacy controls per request where supported.
3. Prefer deterministic fallback lists over random free-model routing for document-sensitive workloads.
4. Add dynamic model discovery from the OpenRouter models API for future admin tooling.
5. Preserve non-AI alternatives for users and organizations that opt out of AI processing.

### Roadmap

#### Near-term roadmap (within v2.0 maintenance releases)

- Add explicit OpenRouter provider routing preferences for privacy, latency, and parameter support.
- Add admin-facing visibility into resolved OpenRouter model/provider usage.
- Add stronger cloud-side retry and fallback telemetry for chat and vision.
- Expand Whisperer compatibility normalization and operator diagnostics.

#### Medium-term roadmap

- Introduce privacy-reviewed multimodal document assistance through the same AI gateway.
- Add dynamic model catalog filtering for ZDR/privacy-safe providers.
- Offer opt-in economy mode for low-risk workloads while preserving the privacy-first default.
- Add richer structured-output/tool-calling flows for remediation suggestions.

## Implementation Decisions

### Architecture

- The Flask web app lives in a new top-level `web/` directory alongside `desktop/` and `office-addin/`. It is a separate Python package (`acb_large_print_web`) that imports `acb_large_print` as a dependency.
- **Zero modifications** to the existing `acb_large_print` core library. The web app calls the same public API that the CLI and GUI use: `audit_document()`, `fix_document()`, `create_template()`, `export_standalone_html()`, `export_cms_fragment()`, and the reporter functions. Rule filtering happens in the web layer by post-filtering `AuditResult.findings` -- the core audit always runs all checks.
- The app uses the Flask application factory pattern (`create_app()`) for testability and configuration flexibility.

### Help Text and Documentation Strategy

Every page includes contextual help using native HTML `<details>/<summary>` accordion elements:

- **No JavaScript dependency** -- `<details>` is natively supported in all modern browsers, is keyboard-operable (Enter/Space to toggle), and is correctly announced by screen readers as "collapsed/expanded".
- **Help text is auto-generated from `constants.py`** -- the Jinja2 templates iterate over `AUDIT_RULES` to render rule descriptions, severity, ACB references, and auto-fixable status. This means a new rule added to the core library automatically appears in the web UI with zero template changes.
- **Accordions are grouped by severity** -- Critical, High, Medium, Low. Each severity group is a `<details>` accordion containing the rules in that group.
- **Every form page** (audit, fix, template, export) includes operation-specific help accordions explaining what the operation does, what options are available, and what the output will be.
- **A dedicated `/guidelines` page** presents the full ACB Large Print specification and WCAG 2.2 AA digital supplement as structured, browsable HTML with one `<details>` accordion per guideline section.

### Rule Selection (Audit and Fix)

Both the audit and fix pages offer three preset modes via radio buttons:

**Audit page:**
- **Full Audit** (default) -- runs all 16 rules. Recommended for first-time users.
- **Quick Audit** -- runs only Critical and High severity rules. Fast overview of major issues.
- **Custom Audit** -- expands a panel of checkboxes grouped by severity (`<details>` accordions: Critical, High, Medium, Low). Each checkbox corresponds to one rule from `AUDIT_RULES`. All are checked by default; the user unchecks any rules they want to skip.

**Fix page:**
- **Full Fix** (default) -- applies all auto-fixable rules. Brings the document to maximum compliance.
- **Essentials Fix** -- applies only Critical and High severity auto-fixes. Leaves Medium/Low issues untouched.
- **Custom Fix** -- same severity-grouped checkbox panel. User picks which fix categories to apply.

**Implementation:** The core library always runs all checks/fixes. The web layer:
- **Audit:** post-filters `AuditResult.findings` to include only the selected rule IDs before rendering the report.
- **Fix:** cannot partially fix (the core `fix_document()` applies everything). For Essentials/Custom modes, the web layer runs `fix_document()` with all fixes, then runs a post-fix audit and filters the report to show only the user's selected rules. The fix result page clearly states "All auto-fixable issues were corrected" regardless of mode, and the filtered report shows the user's focus area. This keeps KISS while giving the appearance of control -- the document is always fully fixed, which is the safest outcome.

### Standards Profiles (Release 1.2.0)

Audit and Fix now include an explicit standards profile selector to support APH submission packaging while preserving current ACB production behavior.

- **ACB 2025 Baseline (default):** no behavioral change from existing production. Selecting this profile keeps current rule scope and current operator workflow unchanged.
- **APH Submission:** surfaces the APH-aligned checks and defaults finalized in Release 1.2.0 for submission readiness and evidence packaging.
- **Combined Strict:** includes all currently implemented checks (ACB + MSAC/WCAG-aligned) in a single strict profile for final review and evidence generation.

Design guarantees:

- Backward compatibility is anchored on **ACB 2025 Baseline** as the default profile.
- Profile selection is visible in Audit and Fix results for evidence traceability.
- Profile filtering is applied in the web layer; canonical audit/fix logic remains unchanged.

---

## New Features (April 2026) -- Based on Live User Feedback

### Quick Rule Exceptions (Issue 2)

**Problem:** Users have legitimate reasons to suppress specific rules in certain workflows. For example, a newsletter that intentionally uses raw URLs for hard-copy readers, or documents with intentionally decorative images. The only way to suppress rules was to enter Custom Audit/Fix mode and uncheck them from a long list, which is not discoverable.

**Solution:** A new **Quick Rule Exceptions** section added to both Fix and Audit forms. Three pre-labeled checkboxes:
- "Suppress ambiguous link text (`ACB-LINK-TEXT`)" -- for documents using raw URLs intentionally
- "Suppress missing alt text (`ACB-MISSING-ALT-TEXT`)" -- for documents with intentionally decorative images
- "Suppress faux heading detection (`ACB-FAUX-HEADING`)" -- for documents with pre-correct headings

When checked, the corresponding rule IDs are added to a suppression set. The audit/fix result shows a "Suppressed by your settings" note listing which rules were excluded.

**Implementation:**
- `_parse_form_options()` extracts new form fields `suppress_link_text`, `suppress_missing_alt_text`, `suppress_faux_heading`
- `_run_fix_and_render()` filters `post_audit.findings` to exclude suppressed rule IDs before scoring
- Template shows suppressed rules in a dismissible note
- Same suppression mechanism as existing mode filtering

### Preserve Centered Headings (Issue 5)

**Problem:** The fixer normalizes all paragraph alignment to flush-left per ACB rules. However, some documents (stories, poems, newsletters with design intent) intentionally center headings for visual hierarchy. The fixer silently overwrites this.

**Solution:** A new "Heading Alignment Handling" section in the Fix form with a checkbox: "Preserve centered headings (do not enforce left-alignment for heading paragraphs)."

When enabled:
- `_fix_paragraph_formatting()` skips heading paragraphs (those using Heading 1, 2, 3 styles) when resetting alignment
- `ACB-ALIGNMENT` findings on heading paragraphs are suppressed from post-fix scoring
- The result page notes which headings were preserved

**Implementation:**
- `preserve_heading_alignment=True` parameter threaded through `_parse_form_options()` → `_fix_by_extension()` → `fix_document()`
- `_fix_paragraph_formatting()` checks paragraph style name and skips if `preserve_heading_alignment` is True
- `_run_fix_and_render()` suppresses alignment findings for heading paragraphs when preserve option is active
- Fixer and auditor both updated in `desktop/src/acb_large_print/`

### Per-Level List Indentation Support (Issue 8B)

**Problem:** The fixer applies a single uniform left indent to all list items regardless of nesting depth. Word documents with multi-level lists need different indents per level (Level 1 at 0.25", Level 2 at 0.50", Level 3 at 0.75").

**Solution:** A new "Per-level list indentation" toggle in the Fix form that reveals three input fields for Level 1, Level 2, and Level 3 indent values (in inches).

**Implementation:**
- New UI toggle and input fields in `fix_form.html`
- `_parse_form_options()` extracts `use_list_levels` flag and builds `list_level_indents: dict[int, float]` from form values
- `auditor.py` gains `_list_level_from_style()` helper to extract nesting level from paragraph style names
- `_check_paragraph_content()` now accepts optional `list_level_indents` and applies per-level expected indentation
- `fixer.py` similarly gains per-level support: `_fix_paragraph_formatting()` accepts `list_level_indents` and applies level-specific target indents to list paragraphs
- Audit findings for lists reference the level: "Expected Level 2 indent 0.50 in, found 0.25 in"
- Both auditor and fixer thread `list_level_indents` through their pipelines
- Form JavaScript manages enable/disable state between base indents and per-level indents (mutually exclusive)

### Dedicated FAQ Page (Issue 7)

**Problem:** Live user feedback revealed recurrent questions that don't fit into inline help or the guidelines page. Examples: "Why is my score still low after 170 fixes?" "Why did my document get 61% longer?" "Can I use centered titles?" These questions need a discoverable home.

**Solution:** A new `/faq/` route and template (`faq.py`, `faq.html`) with accordion-style entries using native HTML `<details>/<summary>`.

**FAQ topics:**
- Quick Rule Exceptions: when and why to use each toggle
- Preserve centered headings: when to use, creative publication examples
- Per-level list indentation: configuration and use cases
- Page expansion after fixing: explanation and mitigation strategies
- Decorative images and VML handling: `alt=""` semantics
- Raw URLs for hard-copy readers: use case explanation
- Soft-return heading technique workaround: known limitation with fix
- Binding margin setup: binding options and use
- Known limitations and future directions

**Implementation:**
- New blueprint `routes/faq.py` with single GET route returning `render_template('faq.html')`
- New template `templates/faq.html` with accordion-style `<details>/<summary>` entries
- Registered in `app.py`
- Link added to main nav footer in `base.html`
- Link added to Fix result page help section

---

### Modules

**Module 1: `app.py` -- Application Factory**

- `create_app(config=None) -> Flask`
- Registers blueprints, sets `MAX_CONTENT_LENGTH` (16 MB), configures temp directory, registers error handlers (413, 415, 500), registers `after_request` cleanup.
- Single function, no global state.

**Module 2: `upload.py` -- File Upload and Validation**

- `validate_upload(file) -> Path` -- accepts Flask `FileStorage`, validates extension (`.docx` only) and file size, saves to a `tempfile.TemporaryDirectory()`, returns the temp file path.
- `cleanup_tempdir(path) -> None` -- deletes the temporary directory and all contents.
- This is the **security boundary**. All uploaded file validation (extension, MIME type, magic bytes, path traversal prevention) happens here and nowhere else.

**Module 3: `routes/` -- Flask Blueprints**

Six thin blueprints. Each handles GET (show form) and POST (process upload), calling core functions directly:

| Blueprint | URL | Core API called | Response |
|-----------|-----|-----------------|----------|
| `main_bp` | `GET /` | None | Landing page with format pills, operation cards, and descriptions |
| `audit_bp` | `GET /audit`, `POST /audit` | `audit_document()` / `audit_workbook()` / `audit_presentation()` | Rendered audit report in browser (filtered by selected mode/rules) |
| `fix_bp` | `GET /fix`, `POST /fix` | `fix_document()` (Word) or audit-only (Excel/PowerPoint) | Fixed `.docx` download or audit guidance + before/after score |
| `template_bp` | `GET /template`, `POST /template` | `create_template()` | `.dotx` file download |
| `export_bp` | `GET /export`, `POST /export` | `export_standalone_html()` or `export_cms_fragment()` | HTML file download (standalone) or ZIP (standalone + CSS) |
| `guidelines_bp` | `GET /guidelines` | None (reads from `constants.py`) | Full ACB specification reference page |

Each POST route: validate upload -> save to temp dir -> call core function -> filter results by mode -> return response -> cleanup temp dir in `finally` block.

**Module 4: `templates/` -- Jinja2 HTML Templates**

- `base.html` -- layout: skip nav link, `<header>` landmark with BITS branding, `<nav>` with links to all pages, `<main>` landmark, `<footer>` landmark, heading hierarchy starting at `<h1>`.
- `index.html` -- landing page with cards for each operation, brief descriptions, and link to guidelines.
- `guidelines.html` -- full ACB Large Print specification and WCAG 2.2 digital supplement. One `<details>/<summary>` accordion per guideline section (Font, Headings, Emphasis, Alignment, Spacing, Margins, Pagination, Hyphenation, Page Numbers, Document Properties). Each section lists the relevant audit rules with severity and description.
- `audit_form.html` -- upload form with three radio buttons (Full / Quick / Custom), a `<details>` panel for Custom mode containing severity-grouped rule checkboxes, and contextual help accordions explaining the audit process.
- `audit_report.html` -- audit results rendered as accessible HTML table with severity badges. Includes a "What's Next" section with a link to the fix page.
- `fix_form.html` -- upload form with three radio buttons (Full Fix / Essentials Fix / Custom Fix), severity-grouped checkbox panel for Custom mode, contextual help accordions.
- `fix_result.html` -- before/after score comparison, list of applied/skipped rules, download link.
- `template_form.html` -- options form (title, sample content toggle, binding margin toggle) with help accordions for each option.
- `export_form.html` -- upload form with standalone/CMS radio toggle, title field, help accordions explaining each format.
- `error.html` -- error page with clear message and link back to the operation.
- `_help_rules.html` -- partial template (Jinja2 include) rendering severity-grouped rule checkboxes from `AUDIT_RULES`. Used by both audit and fix forms.

All templates use the ACB Large Print CSS for body text, headings, and spacing. Minimal supplemental CSS for form layout and `<details>` styling only.

**Module 5: `static/` -- CSS and Assets**

- Copies (not symlinks) `acb-large-print.css` from `styles/` into `web/static/`.
- A small `forms.css` for form-specific layout (input widths, button styles, file upload area).
- No JavaScript required. All forms use standard HTML `<form>` POST submissions. Optional progressive enhancement (upload progress indicator) if JS is available, but full functionality without it.

**Module 6: `wsgi.py` -- Production Entry Point**

- `app = create_app()` -- the WSGI callable for Gunicorn/uWSGI.

**Module 7: `Dockerfile` + `docker-compose.yml`**

- Base image: `python:3.13-slim`
- Non-root user (`appuser`)
- Install `acb_large_print` + `acb_large_print_web` + `gunicorn`
- Expose port 8000
- Gunicorn with 8 workers, 120s timeout (for large document processing)
- `docker-compose.yml`: two services -- Caddy reverse proxy (auto-HTTPS) + Flask app container
- Health check endpoint: `GET /health` returns 200
- Caddy persists TLS certificates in a Docker named volume
- See the [Deployment Guide](/deployment/) for step-by-step server setup and deployment commands

### File Handling and Security

- Uploaded files are saved to a new `tempfile.TemporaryDirectory()` per request.
- Temp directories are deleted in a `finally` block after the response is sent -- guaranteed cleanup even on exceptions.
- No files are ever written outside the temp directory.
- File extension whitelist: `.docx`, `.xlsx`, `.pptx` only.
- `MAX_CONTENT_LENGTH = 16 * 1024 * 1024` (16 MB) enforced by Flask before the upload handler runs.
- `werkzeug.utils.secure_filename()` applied to all uploaded filenames.
- The Docker container runs as non-root with a read-only filesystem except for `/tmp`.

### Accessibility (WCAG 2.2 AA)

- All pages have `lang="en"` on `<html>`.
- Skip navigation link as first focusable element.
- Landmark regions: `<header>`, `<nav>`, `<main>`, `<footer>`.
- Heading hierarchy: `<h1>` for page title, `<h2>` for sections, no skipped levels.
- All form controls have associated `<label>` elements.
- File input has help text via `aria-describedby` explaining accepted formats and size limit.
- Error messages linked to controls via `aria-describedby` and `aria-invalid`.
- Status messages (upload processing, success, failure) in `aria-live="polite"` region.
- Minimum 4.5:1 contrast ratio for all text.
- Focus indicators visible on all interactive elements.
- No reliance on color alone to convey information (severity uses text labels alongside color).
- All interactive elements have minimum 44x44px touch targets.
- Works without JavaScript enabled.

### Hosting Options (Docker-first, decide later)

The app ships as a Docker container. Any of these hosting options work:

| Option | Spec | Price | Notes |
|--------|------|-------|-------|
| **RackNerd 8 GB VPS (recommended)** | 6 vCPU, 8 GB RAM, 150 GB SSD, 20 TB transfer | **$62.49/year** (~$5.21/mo) | Black Friday promo -- locks in at renewal. Massive headroom for concurrent processing, room to host additional BITS services on the same VPS. Equivalent DigitalOcean Droplet would cost ~$576/year. |
| RackNerd 4 GB VPS | 3 vCPU, 4 GB RAM, 65 GB SSD, 6.5 TB transfer | $29.98/year | Good mid-tier if budget is tighter. |
| RackNerd 2.5 GB VPS | 2 vCPU, 2.5 GB RAM, 45 GB SSD, 3 TB transfer | $18.66/year | Minimum comfortable for this app alone. |
| DigitalOcean App Platform | 1 vCPU, 1 GB RAM, 100 GB transfer | $10/mo ($120/year) | Zero-ops managed platform (auto-deploy on git push, no SSH). Higher cost, less RAM, tight transfer limits. Best for teams wanting fully managed hosting. |
| Hetzner Cloud CX22 | 2 vCPU, 4 GB RAM, 40 GB SSD, 20 TB transfer | ~$54/year (~$4.49/mo) | EU GDPR, great API, hourly billing, US datacenter available (Ashburn VA). |
| Any Docker host | Varies | Varies | `docker compose up` works anywhere. |

**Recommended production stack (RackNerd 8 GB):**
- Ubuntu 24.04 LTS on the VPS
- Docker + Docker Compose for the app
- Caddy as reverse proxy (automatic Let's Encrypt TLS certificates)
- Gunicorn (8 workers -- 8 GB RAM supports it) as the WSGI server
- systemd service for auto-restart
- UptimeRobot free tier for uptime monitoring (pings `GET /health` every 5 minutes)
- Subdomain pointed via DNS A record to VPS IP
- Capacity for additional BITS services on the same VPS (150 GB SSD, 20 TB transfer)

**Deployment workflow:**
1. SSH into VPS
2. `git pull` (or `docker pull` from registry)
3. `docker compose up -d --build`
4. Caddy handles TLS automatically

For complete step-by-step commands starting from a bare server, see the [Deployment Guide](/deployment/).

### Concrete Technology Stack

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| OS | Ubuntu | 24.04 LTS | 5-year support, Docker-native, widely documented |
| Container runtime | Docker Engine + Compose | Latest stable | Reproducible builds, single `docker compose up` deploy |
| Reverse proxy / TLS | Caddy | 2.x | Automatic Let's Encrypt, zero-config HTTPS, single binary |
| WSGI server | Gunicorn | 23.x | Battle-tested, simple config, works with Flask out of the box |
| Web framework | Flask | 3.x | Minimal, no ORM/auth baggage, Jinja2 server-rendered HTML |
| Python | CPython | 3.13 | Latest stable, matches `python:3.13-slim` Docker image |
| Core library | acb_large_print | (local) | Existing audit/fix/template/export engine -- zero changes |
| Document converter | Pandoc | 3.1+ | Universal document converter: Markdown/Word/RST/ODT/RTF/ePub to HTML, Word, EPUB 3, and PDF (via WeasyPrint) |
| PDF renderer | WeasyPrint | 62.0+ | CSS-based PDF rendering with ACB print formatting (CourtBouillon). Requires Pango, Cairo, GDK-Pixbuf system libraries and Liberation Sans font. |
| AI inference | OpenRouter | API | Cloud LLM inference for chat, heading detection, and AI-assisted workflows. Privacy-aware provider routing (`dataCollection: deny`). Desktop tool uses local Ollama (optional). |
| Process manager | systemd | (OS built-in) | Auto-restart Docker on reboot, journald logging |
| Firewall | ufw | (OS built-in) | Simple allow/deny rules for SSH, HTTP, HTTPS |
| Monitoring | UptimeRobot | Free tier | 5-minute HTTP pings to `/health`, email/SMS alerts on downtime |

### Proposed Directory Structure

```text
web/
  src/
    acb_large_print_web/
      __init__.py           # create_app() factory
      upload.py             # File validation and temp directory management
      wsgi.py               # Gunicorn entry point
      routes/
        __init__.py
        main.py             # GET / landing page
        audit.py            # GET/POST /audit (with rule filtering)
        fix.py              # GET/POST /fix (with mode filtering)
        template.py         # GET/POST /template
        export.py           # GET/POST /export
        guidelines.py       # GET /guidelines -- full ACB spec reference
      templates/
        base.html           # Layout with skip nav, landmarks, nav bar
        index.html          # Landing page with operation cards
        guidelines.html     # Full ACB spec + WCAG supplement reference
        audit_form.html     # Upload + Full/Quick/Custom radio + help
        audit_report.html   # Findings table + What's Next link
        fix_form.html       # Upload + Full/Essentials/Custom radio + help
        fix_result.html     # Before/after scores + applied rules + download
        template_form.html  # Options form + help accordions
        export_form.html    # Upload + standalone/CMS toggle + help
        error.html          # Error page
        _help_rules.html    # Partial: severity-grouped rule checkboxes
      static/
        acb-large-print.css # Copy of reference CSS
        forms.css           # Form layout, details styling, cards
  tests/
    __init__.py
    test_app.py             # Smoke tests: home, about, routes exist
    test_audit.py           # Rule filtering, Full/Quick/Custom modes
    test_fix.py             # Before/after scores, download
    test_template.py        # Template generation options
    test_export.py          # Standalone and CMS exports
    test_errors.py          # 413 (large file), 415 (wrong type), 500
    test_accessibility.py   # WCAG checks: lang, landmarks, labels, contrast
  Dockerfile
  docker-compose.yml
  requirements.txt
  pyproject.toml
```

---

## GLOW 3.0.0 -- Speech Platform (Planned)

**Status:** Planned -- not yet implemented
**Target release:** 3.0.0
**Specification source:** `docs/speech.md` (Kokoro TTS Platform PRD, Unix-Based, CPU-Optimized)
**Predecessor:** BITS Whisperer (audio-to-text) shipped in v2.0.0. The speech platform extends GLOW in the complementary direction: text-to-accessible-audio.

### Vision

GLOW 3.0.0 will add a self-hosted text-to-speech (TTS) capability powered by Kokoro ONNX, enabling blind and low-vision users and the organizations that serve them to generate accessible audio versions of large-print documents without requiring a GPU, without sending document content to third-party cloud services, and without per-request API costs.

This closes the full accessibility loop: GLOW can already audit, fix, convert, and format documents for visual large-print reading. The 3.0.0 speech platform adds audio output as a first-class delivery format for the same content.

### What the BITS community said

The speech platform was the most frequently requested feature across the BITS community feedback collected through 2.7.0 and 2.8.0. Members consistently asked for a way to produce MP3 audio versions of board minutes, newsletters, and policy memos -- in particular for members who use refreshable braille displays or screen readers in combination with audio, and for families who distribute recorded versions of meeting summaries. GLOW 3.0.0 is the answer to those requests.

### Design Principles

- **CPU-first, no GPU required.** Kokoro runs at approximately 0.8-1.5x realtime on a modern CPU. The BITS server (or any Docker host) can generate a 2-minute audio clip from 300 words in under 3 minutes without specialist hardware.
- **No third-party cloud TTS.** Document content stays on-premise. This is essential for organizations that handle member health, legal, or financial documents.
- **Preview-first UX.** Generate the first 3-8 seconds of audio before committing to a full-length job. Confirms voice, speed, and tone before waiting for a long generation job.
- **Async for long documents.** Documents over 300 words are processed as background jobs with a queue position indicator, a status polling endpoint, and email notification when the job completes (when email is configured). Short documents are processed inline.
- **User-controlled voice and parameters.** Multiple pre-configured voices (af_bella, am_adam, and others as available). Adjustable speed (native Kokoro parameter), pitch (FFmpeg post-processing), and energy level (audio filter).

### Technical Architecture (from `docs/speech.md`)

```text
User Input (text or GLOW document)
  ↓
Text Analyzer (length estimate → async vs inline decision)
  ↓
Preview Generator (first ~200 chars, < 1 second target)
  ↓
TTS Engine (Kokoro ONNX, CPU)
  ↓
Audio Processor (WAV → MP3 via FFmpeg at 192kbps)
  ↓
Storage + Download API
```

**Components:**

| Component | Technology |
|-----------|-----------|
| TTS engine | Kokoro ONNX (CPU, loaded into memory at startup) |
| Audio conversion | FFmpeg (`libmp3lame`, 192kbps) |
| Job queue | Redis + worker pool (2-4 workers) |
| API layer | FastAPI (integrated with Flask via proxy or sidecar) |
| Storage | `/audio/{session_id}/{job_id}.mp3` (temp, TTL-bound) |
| Caching | Hash of `(text + voice + parameters)` -- identical jobs reuse output |

**Text chunking:** long documents are split at ~500-word boundaries, each chunk processed in parallel, then merged before MP3 encoding. This keeps individual generation units fast and enables progress reporting.

### Performance Expectations (CPU)

| Input Size | Audio Duration | CPU Generation Time |
|-----------|---------------|---------------------|
| 50 words (~20 sec audio) | 20 sec | 15-25 sec |
| 300 words (~2 min audio) | 2 min | 1.5-3 min |
| 2,000 words (~12-15 min audio) | 12-15 min | 10-20 min |

Short documents (under ~50 words) are generated inline. All others use async queue mode.

### Time Estimation API

```http
POST /speech/estimate
{
  "text": "...",
  "speed": 1.0
}
→
{
  "estimated_audio_length_sec": 100,
  "estimated_generation_time_sec": 95,
  "processing_mode": "cpu",
  "word_count": 270
}
```

### API Surface (planned routes)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/speech/preview` | POST | Generate first ~8 seconds from first ~200 chars of input |
| `/speech/estimate` | POST | Estimate audio duration and generation time |
| `/speech/generate` | POST | Start a full generation job; returns `job_id` for async mode |
| `/speech/status/<job_id>` | GET | Poll job progress (percentage, estimated completion time) |
| `/speech/download/<job_id>` | GET | Download completed MP3 |

### GLOW Integration Points

- **Audit report:** "Listen to this report" button generates an MP3 of the plain-text summary.
- **Convert result:** "Download as audio" option alongside HTML/Word/PDF/EPUB for supported output formats.
- **Quick Start:** "Transcribe" action (Whisperer, text → audio) and "Read aloud" action (TTS, document → audio) will appear as complementary Quick Start cards.
- **BITS Whisperer → TTS pipeline:** transcribe audio → edit transcript → re-synthesize corrected audio. Full round-trip in one session.

### Voice Customization

| Parameter | Mechanism |
|-----------|----------|
| Voice | Pre-configured Kokoro voice IDs (af_bella, am_adam, others) |
| Speed | Native Kokoro `speed` parameter |
| Pitch shift | FFmpeg `rubberband` or `asetrate` filter post-processing |
| Energy / loudness | FFmpeg `loudnorm` filter |

### Non-Goals for 3.0.0

- Multilingual synthesis (English only in 3.0.0)
- Voice cloning or custom voice training
- Studio-grade prosody control
- Emotion-level synthesis
- GPU requirement (CPU-only is a hard constraint)

### Out-of-Scope (Deferred Post-3.0.0)

- Real-time streaming TTS for Document Chat
- Braille-to-audio pipeline
- Multilingual voice support

### Dependencies

- Kokoro ONNX model files (downloaded at container build time or mounted as a volume)
- FFmpeg (system package in Docker image)
- Redis (new sidecar service in `docker-compose.yml`)
- 2-4 additional GB RAM per active worker (Kokoro model in memory)

### Deployment Impact

The 3.0.0 release will add a Redis sidecar and one or more Kokoro worker containers to the existing Docker Compose stack. The Flask/Gunicorn web container will proxy speech requests to the FastAPI sidecar. The BITS server (RackNerd 8 GB, 6 vCPU) has the headroom to run 2 workers with comfortable margin. Audio output files are temp-bound with the same TTL lifecycle as document uploads (1-hour maximum).

For full technical detail, see `docs/speech.md`.

