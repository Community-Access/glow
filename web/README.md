# GLOW Accessibility Web Application

A Flask web application that provides browser-based access to the GLOW. Upload a Word, Excel, PowerPoint, Markdown, PDF, or ePub document, choose an operation (audit, fix, template, export, convert), and get results through either immediate responses or background jobs with progress tracking -- no installation required.

## Features

- **Audit** -- check a .docx, .xlsx, .pptx, .md, .pdf, or .epub file against accessibility rules with Full, Quick, or Custom mode. Rules adapt automatically to each file format.
- **Fix** -- auto-fix compliance issues in Word documents and download the corrected file. Other formats receive a detailed audit with manual fix guidance.
- **Template** -- generate a pre-configured ACB-compliant Word template (.dotx)
- **Export** -- convert a .docx to accessible HTML (standalone ZIP or CMS fragment)
- **Convert** -- transform documents between formats via six conversion directions: Markdown (MarkItDown), HTML (Pandoc), Word (Pandoc), EPUB 3 (Pandoc), PDF (Pandoc + WeasyPrint), and EPUB/DAISY (DAISY Pipeline)
- **Guidelines** -- browse the full ACB Large Print specification and WCAG 2.2 supplement
- **About** -- project mission, organizations, standards, open source dependencies, and acknowledgments
- **Feedback** -- collect user feedback with SQLite storage and password-protected review

### Queue-First Heavy Operations

When `GLOW_CONVERT_ASYNC=1` (default), heavy workflows run as background jobs and route to the shared progress page at `/job/<id>/`.

- **Convert** (long-running directions)
- **Speech** (typed/document downloads and document preparation)
- **PageFlow** (article extraction and narration download)
- **Audit** (single-file audit submit)
- **Fix** (non-interactive fix runs)
- **Template** generation
- **Export** generation

The job progress surface supports:

- Live updates via SSE with JSON polling fallback
- Cancel and retry controls
- Result download links (`/job/<id>/result`)
- Optional continue links for follow-up workflows (for example, queued Speech Prepare returning to Speech Studio)

### Recently Completed Fix UX/Behavior Updates

- **Heading suppression transparency** -- when users disable heading detection, `ACB-FAUX-HEADING` is suppressed from post-fix scoring and listed as suppressed in the results UI.
- **Page growth guidance** -- fix results now warn when detected pre-fix body text is below 18pt because normalization can increase pagination.
- **List indentation discoverability** -- list indent controls are always visible and toggle between disabled/enabled based on the "Flush all lists" setting.
- **VML decorative image handling** -- legacy VML shapes with explicit `alt=""` are treated as decorative (no missing-alt finding).
- **Quick Rule Exceptions** -- new collapsible section in Fix and Audit forms with toggles for `ACB-LINK-TEXT`, `ACB-MISSING-ALT-TEXT`, and `ACB-FAUX-HEADING` to suppress these rules per operation without editing workflow settings.
- **Preserve centered headings** -- Fix form option to skip alignment override on heading paragraphs, preserving intentional heading center-alignment.
- **Per-level list indentation** -- Fix form now accepts level-specific indent targets (Level 1, Level 2, Level 3) instead of a single uniform indent; auditor and fixer apply per-style-level expectations.
- **Allowed heading levels** -- Fix form and Settings now let teams restrict heading review/conversion to selected levels; heading review dropdown options and confirm-apply behavior honor that subset end-to-end.
- **Template heading-level alignment** -- Template form and Settings defaults now include allowed heading levels for sample content, and generated sample headings follow the selected level subset.
- **FAQ page** -- dedicated `/faq/` endpoint with answers to quick exception usage, heading preservation intent, per-level list indentation, and known limitations.

## Supported Formats

| Format | Audit | Auto-Fix | Template | Export | Convert |
|--------|-------|----------|----------|--------|---------|
| Word (.docx) | Full (30+ ACB + MSAC rules) | Yes | Yes (.dotx) | Yes (HTML) | To Markdown, To HTML, To EPUB 3 |
| Excel (.xlsx) | Full (MSAC rules: sheet names, table headers, merged cells, alt text, hidden content, color-only) | Planned | -- | -- | To Markdown |
| PowerPoint (.pptx) | Full (MSAC rules: slide titles, reading order, alt text, font sizes, speaker notes, charts) | Planned | -- | -- | To Markdown |
| Markdown (.md) | Basic (ACB emphasis, headings, images, lists) | Planned | -- | -- | To HTML, To Word, To EPUB 3, To PDF |
| PDF (.pdf) | Basic (page-level structure and text extraction) | Planned | -- | -- | To Markdown |
| HTML (.html) | -- | -- | -- | -- | To Word, To EPUB 3, To PDF |
| ePub (.epub) | Full (EPUB Accessibility 1.1: title, language, nav, headings, alt text, tables, links, metadata) | Planned | -- | -- | To Markdown, To HTML, To PDF, To DAISY 2.02, To DAISY 3 |

## Architecture

The web app is a thin Flask layer over the existing `acb_large_print` Python library. It calls the same public API that the CLI and GUI use -- zero modifications to the core library.

```
web/
  src/
    acb_large_print_web/
      app.py              Application factory (CSRF, rate limiting, logging)
      upload.py           File validation, temp directory management
      rules.py            Rule metadata helpers for templates
      wsgi.py             Gunicorn entry point
      routes/
        main.py           GET / landing page
        audit.py          GET/POST /audit
        fix.py            GET/POST /fix
        template.py       GET/POST /template
        export.py         GET/POST /export
        convert.py        GET/POST /convert
        guidelines.py     GET /guidelines
        about.py          GET /about
        feedback.py       GET/POST /feedback, GET /feedback/review
      templates/          Jinja2 HTML templates
      static/             CSS and favicon
  tests/
    test_app.py           28 tests (smoke, error, feedback, accessibility, integration)
  Dockerfile
  docker-compose.yml
  pyproject.toml
  requirements.txt
```

## Quick Start (Development)

```bash
cd web
pip install -e ".[dev]"
pip install -e "../desktop"

flask --app acb_large_print_web.app:create_app run --debug
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Running Tests

```bash
cd web
python -m pytest tests/ -v
```

### Heading Stress Validation (1,000-Document Scale)

The web app's Guide and About pages expose stress-testing transparency for heading detection and repair. The validation itself runs through the shared stress harness in the desktop test suite.

Current stress scale:

- 1,000 generated Word documents
- 1 scenario block per document
- 1,000 total heading scenarios

What the web-facing platform is proving through that harness:

- Heading detection can separate real headings from common false positives
- Repair can normalize the same documents back to strict ACB rules
- Product changes are accepted only after the measured corpus improves or stays clean

Validation commands:

```bash
python -m pytest desktop/tests/test_heading_stress_corpus.py::test_full_stress_corpus_generates_one_thousand_documents desktop/tests/test_heading_stress_corpus.py::test_full_fixer_stress_corpus_repairs_all_documents -q
python -m pytest desktop/tests/test_heading_stress_corpus.py -q
```

Pass/fail interpretation:

- Pass: generation and repair checks complete with zero failures.
- Fail: treat as regression and investigate failing scenario families before release.

Lessons learned from the completed runs:

1. Users do not upload "cleanly wrong" documents. They upload mixed documents with plain-text paste, bold-only headings, centered titles, font drift, and indentation drift in the same file.
2. False-positive control is critical. Signature lines and short callouts are easy to misread as headings unless the detector includes negative-pattern penalties.
3. Good heading detection is not the end of the job. The fixer also has to repair heading hierarchy and heading text so the final document passes ACB audit rules.
4. The platform improved because stress failures were turned into product changes, not just test notes. We expanded scenario randomness and added heading normalization in the fixer after the corpus exposed those gaps.

Current measured outcomes:

- Full heading stress suite: 5 passed
- Core fixer and detector suite: 150 passed
- 1,000-scenario comparison: 0 false positives, 0 false negatives
- 4,800-scenario denser randomized comparison: 0 false positives, 0 false negatives
- 1,000-document ACB fix-then-audit sweep: 0 remaining ACB findings

### PageFlow Wild-Pattern Regression Testing

PageFlow extraction is validated with a deterministic offline regression matrix
that mimics real-world web patterns (editorial CMS, ad-heavy pages,
JS-heavy Next.js/SPA shells, ecommerce collections, and noisy pagination).

Primary regression tests:

```bash
cd web
PYTHONPATH=src pytest tests/test_page_flow_regression_matrix.py tests/test_listen_later.py tests/test_page_flow.py -q
```

Wild-pattern fixture corpus:

- `tests/fixtures/page_flow_wild_patterns.py`

Capture a live page into a fixture skeleton for review:

```bash
cd web
python tools/capture_page_flow_fixture.py \
  --url "https://example.com/article" \
  --name example_article \
  --out tests/fixtures/captured/example_article.json
```

Notes:

- Captured fixtures should be reviewed and trimmed before being added to CI.
- Keep CI tests offline and deterministic; use optional live probes only as a
  non-blocking monitoring lane.

Nightly live probe lane:

- Workflow: `.github/workflows/pageflow-live-probe.yml`
- Script: `web/tools/page_flow_live_probe.py`
- Corpus: `web/tests/fixtures/page_flow_live_corpus.txt`

Run manually:

```bash
cd web
PYTHONPATH=src python tools/page_flow_live_probe.py \
  --corpus tests/fixtures/page_flow_live_corpus.txt \
  --out test-results/page_flow_live_probe.json \
  --max-pages 5
```

Optional browser-rendered adapter (PageFlow parity mode):

- `GLOW_PAGEFLOW_BROWSER_ADAPTER=auto` (default): use Node/Playwright adapter only for JS-heavy pages
- `GLOW_PAGEFLOW_BROWSER_ADAPTER=1`: force adapter for all pages
- `GLOW_PAGEFLOW_BROWSER_ADAPTER=0`: disable adapter
- `GLOW_PAGEFLOW_BROWSER_TIMEOUT_SEC=20`: adapter timeout (seconds)

The adapter script is `web/tools/page_flow_render.mjs` and is fail-safe: when Node/Playwright is unavailable, extraction falls back to the standard parser path.

## Docker

Build and run locally:

```bash
cd web
docker compose up --build
```

The app is served on port 8000. For production deployment with Caddy (auto-TLS), see [docs/deployment.md](../docs/deployment.md).

### Background Workers

For full async queue processing in development or production, run a Celery worker alongside the web app:

```bash
cd web
celery -A acb_large_print_web.tasks worker --loglevel=INFO
```

If no broker is configured, Celery runs in eager mode and tasks execute inline.

### WSL Staging Before Production Deploy

On a Windows workstation with WSL 2, you can stage the Docker stack in your Ubuntu distro and run the current regression gate before touching the main server.

Prerequisites:

- Docker Desktop WSL integration must be enabled for the target distro.
- The repo `.venv` must exist for the focused pytest lane.
- `web/node_modules` and Playwright browsers must already be installed for the browser lane.

Run:

```powershell
pwsh -File .\scripts\wsl-stage-regression.ps1
```

What it does:

- Starts `web/docker-compose.yml` with the WSL override `web/docker-compose.wsl.yml`
- Waits for `/health` on `http://127.0.0.1:8000`
- Runs the focused web pytest regression set used for the current rollout
- Runs the Playwright regression suite against the running WSL-hosted container stack
- Defaults all AI feature flags to `0` so non-AI release validation matches the planned production rollout

Useful switches:

- `-KeepRunning` leaves the WSL containers up after tests finish
- `-SkipPytest` or `-SkipE2E` narrows the lane when debugging
- `-EnableAI` stages the stack with all AI feature flags enabled
- `-AudioPath` supplies a Whisperer sample when AI staging is enabled

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | Random per-start | Flask session secret. Set a fixed value in production. |
| `FEEDBACK_PASSWORD` | (unset) | Set to enable `/feedback/review?key=<password>`. Disabled when unset. |
| `POSTMARK_SERVER_TOKEN` | (unset) | Postmark server token used for audit-report emails, Whisperer notifications, and admin magic-link sign-in emails. |
| `POSTMARK_FROM_EMAIL` | `reports@glow.bits-acb.org` | Sender address used by Postmark-delivered app emails. |
| `LOG_LEVEL` | `INFO` | Python logging level (DEBUG, INFO, WARNING, ERROR). |
| `MAX_CONTENT_LENGTH` | 500 MB | Maximum upload file size. |
| `GLOW_CONVERT_ASYNC` | `1` | Enable queue-first processing for heavy workflows. Set to `0` to force synchronous route execution. |
| `CELERY_BROKER_URL` | (unset) | Celery broker URL (for example Redis). When unset, Celery uses eager inline mode. |
| `CELERY_RESULT_BACKEND` | (unset) | Optional Celery result backend. Defaults to broker when provided. |
| `ADMIN_BOOTSTRAP_EMAILS` | (unset) | Comma-separated admin emails automatically approved for admin sign-in flows. |
| `ADMIN_MAGIC_LINK_TTL_MINUTES` | `20` | Expiration window for admin email magic links. |
| `GLOW_ENABLE_AI` | `1` | Master switch for all web AI features. Set to `0` to deploy the site with AI paths hidden and disabled while still shipping non-AI fixes. |
| `GLOW_ENABLE_AI_CHAT` | `1` | Gate Document Chat independently. |
| `GLOW_ENABLE_AI_WHISPERER` | `1` | Gate BITS Whisperer independently. |
| `GLOW_ENABLE_AI_HEADING_FIX` | `1` | Gate AI refinement in the Fix workflow while keeping heuristic heading detection available. |
| `GLOW_ENABLE_AI_ALT_TEXT` | `1` | Gate AI-assisted alt-text helpers independently. |
| `GLOW_ENABLE_AI_MARKITDOWN_LLM` | `1` | Gate MarkItDown LLM enhancements independently. |
| `GLOW_AUTOMATION_CONSENT_TOKEN` | `GLOW` | Shared secret for automation. Requests that send the exact token in the `X-GLOW-Automation-Consent` header bypass the first-visit consent redirect. Override the default in production with a deployment-specific secret. |

## Security

- CSRF protection on all POST forms (Flask-WTF)
- Rate limiting: 120 requests/minute per IP (Flask-Limiter)
- Upload validation: .docx, .xlsx, .pptx, .md, .pdf extension whitelist, `secure_filename()`, path traversal prevention
- 500 MB upload size limit enforced by Flask before handlers run
- Temp files deleted in `finally` blocks -- guaranteed cleanup on success or exception
- Docker: non-root user, health check, tmpfs for temp files

## Accessibility (WCAG 2.2 AA)

- `lang="en"` on all pages
- Skip navigation link
- Landmark regions: header, nav, main, footer
- All form controls have associated labels
- Error messages linked via `aria-describedby` and `aria-invalid`
- Flash messages include text prefixes (Error/Success/Warning/Note) -- not color alone
- Severity badges, format pills, and format tags all have visible text labels -- color is supplementary
- All text and interactive-component contrast meets WCAG 2.2 AA thresholds
- Visible focus indicators (3px solid outline) on all interactive elements including nav links
- Native `<details>/<summary>` for contextual help (no JavaScript)
- `aria-current="page"` on active nav item
- ACB Large Print CSS applied to the tool itself
- Works without JavaScript enabled

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Flask 3.x |
| WSGI server | Gunicorn 23.x |
| Python | 3.13 |
| Core library | acb_large_print (local) |
| Document conversion | MarkItDown (Microsoft) |
| CSRF | Flask-WTF |
| Rate limiting | Flask-Limiter |
| Feedback storage | SQLite (WAL mode) |
| Container | Docker + Compose |
| Reverse proxy | Caddy 2.x (production) |

# --- OIDC/Keycloak Integration ---
# Flask-OIDC is included in requirements.txt for Google/Keycloak login.
# The Dockerfile and docker-compose.keycloak.yml support local Keycloak for dev/testing.
#
# For production, use a managed Keycloak or secure your own instance with a persistent DB and HTTPS.
#
# See docs/AUTH-KEYCLOAK-GUIDED-SETUP.md for full setup and onboarding instructions.
# ---
