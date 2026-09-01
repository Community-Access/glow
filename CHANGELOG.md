# Changelog

All notable changes to the GLOW are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Releases are tagged in the [GitHub repository](https://github.com/Community-Access/glow). Dates are in Pacific Time (UTC-7).

---

## [Unreleased]

### Added

- **The GLOW passport** -- one optional identity for the whole product:
  settings that follow a person to another device via a single-use emailed
  link, with no password and no account. Preferences previously lived in one
  browser's local storage and evaporated on a phone or after a cookie clear,
  which fell hardest on the people who had most carefully tuned their type
  scale, contrast mode and cognitive profile. Optional at every point; GLOW is
  unchanged for anyone who never uses it. History is opt-in only, deleted when
  switched off; retention is 90 days from last use; one control deletes
  everything and says what it deleted. See `docs/PASSPORT.md`.
- **Workshop Mode and the passport are one identity.** Joining a workshop
  attaches the participant to the passport this browser carries, and the
  display name is remembered. Gallery anonymity is untouched.
- **Whisperer notification address is remembered** when notifications are on,
  instead of being retyped for every job.
- **Email status and a test send** on the admin queue page: what mail can do,
  which sender and stream, and one message that proves the path without
  waiting for a real event.

### Security

- **Site Audit no longer fetches internal addresses (SSRF fix).** The auditor fetched whatever URL an anonymous visitor submitted and packed the response body into the downloadable `artifacts.zip`, so a request for `http://169.254.169.254/...` or `http://redis:6379/` would let the submitter read cloud-metadata credentials and internal services. Added an `_is_public_url` gate (rejects loopback, private, link-local, reserved, multicast addresses and non-web ports) and an `_http_get` wrapper that re-validates every redirect hop and caps the response body at 8 MB against decompression bombs. All three fetch sites (scan, crawl, sitemap) go through it, and the sitemap XML is now parsed with `defusedxml`. ([web/src/acb_large_print_web/site_audit.py](web/src/acb_large_print_web/site_audit.py))
- **Rate-limit keys can no longer be rotated to bypass the brute-force caps.** `rate_limit_key` keyed on the `glow_workshop_participant` cookie for every route, so an attacker sending a fresh random cookie per request got a new bucket each time -- defeating the admin-login 10/min cap and the upload caps. The cookie key is now scoped to workshop routes only; everywhere else keys on the remote address. ([web/src/acb_large_print_web/app.py](web/src/acb_large_print_web/app.py))
- **Closed an open redirect in the consent gate.** The `next` guard was bypassable with `HTTPS://evil.com` (case) and `/\evil.com` (backslash). Replaced with a positive same-site test; the consent page is the first page a new visitor sees, so this was a strong phishing lure. ([web/src/acb_large_print_web/routes/consent.py](web/src/acb_large_print_web/routes/consent.py))

- **Per-request CSP nonces, site-wide.** The production `Content-Security-Policy` was `script-src 'self'; style-src 'self'`, which silently blocked every inline `<script>` and `<style>` block in the templates and every inline `on*=` event handler. Most pages had subtle JS-feature breakage (the same class of bug that froze the job progress bar at 20%). Moved CSP emission from [web/Caddyfile](web/Caddyfile) into a Flask `after_request` hook in [web/src/acb_large_print_web/app.py](web/src/acb_large_print_web/app.py) so each response gets a fresh `secrets.token_urlsafe(16)` nonce stashed on `g.csp_nonce`, exposed to Jinja as `csp_nonce`, and injected into `script-src` and `style-src`. Added `nonce="{{ csp_nonce }}"` to all 20 inline `<script>` blocks and 3 inline `<style>` blocks across the templates (`base.html`, `audit_form.html`, `fix_form.html`, `settings.html`, `admin_*`, `chat_form.html`, `convert_form.html`, `rules_ref.html`, `maintenance.html`, etc.). External scripts continue to match `'self'` and need no nonce. Added `script-src-attr 'none'` as defense-in-depth against any future inline event handlers, and `style-src-attr 'unsafe-inline'` so style attributes (`style="display:none"`) used throughout the markup keep working without a churn-heavy refactor.
- **Inline event handlers refactored to delegated listeners.** All 15 remaining `onclick`/`oninput` attributes (`return confirm(...)`, `history.back()`, `glowToggleRuleGroup(this, ...)`, the chat character-count mirror) were replaced with `data-confirm`, `data-action="history-back"`, `data-toggle-rule-group="select|deselect"`, and `data-char-count-target`/`data-char-count-max` attributes. A new [web/src/acb_large_print_web/static/inline-handlers.js](web/src/acb_large_print_web/static/inline-handlers.js), loaded from `base.html`, wires them up via delegated event listeners on `document`. Templates touched: `admin_requests.html`, `admin_speech.html`, `admin_queue.html`, `admin_flags.html`, `audit_form.html`, `fix_form.html`, `chat_form.html`, `privacy.html`, `error.html`, `feedback_thanks.html`. No `'unsafe-inline'` or `'unsafe-hashes'` in `script-src`.
- **Deduplicated security headers between Caddy and Flask.** Production responses were emitting `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` twice (once from Caddy, once from Flask), and the two `X-Frame-Options` values disagreed (`DENY` from Caddy versus `SAMEORIGIN` from Flask). Removed those three directives from the `letitglow.app` and `@sse` blocks in [web/Caddyfile](web/Caddyfile) and let Flask's existing `_add_security_headers` `after_request` hook own them. Caddy continues to emit only the transport-level / policy headers it should own (`Strict-Transport-Security`, `Permissions-Policy`).

### Fixed

- **Whisperer could deadlock its whole worker when the audio queue filled.** The "queue full" branch called a lock-taking helper while already holding the same non-reentrant lock, so the ninth concurrent submission would block forever holding it and wedge every route that touches the lock. ([web/src/acb_large_print_web/routes/whisperer.py](web/src/acb_large_print_web/routes/whisperer.py))
- **Site Audit crawler no longer follows `mailto:`/`tel:`/`javascript:` links or re-scans URL fragments.** `_normalize_url` prefixed any non-web string with `https://`, turning `mailto:info@x` into a bogus same-site "page"; and `/page` versus `/page#section` were treated as two pages, so in-page anchors burned the crawl budget. Non-web schemes are now rejected and fragments stripped. HTML error pages (status >= 400) are recorded as errors instead of counted as scanned pages, and the parser now flushes a missing or chunk-split `</title>` so compliant pages are not falsely reported as title-less. ([web/src/acb_large_print_web/site_audit.py](web/src/acb_large_print_web/site_audit.py))
- **Quick Wins undercounted auto-fixable findings.** Four entries in `FIXABLE_RULE_IDS` named rules that do not exist (`ACB-BOLD-BODY`, `ACB-ALL-CAPS`, `ACB-HYPHENATION`, `ACB-DOC-LANG`), so those findings were never shown as auto-fixable and the "Show Quick Wins Only" filter understated what GLOW Fix can do. Corrected to the real IDs and added a guard test. ([web/src/acb_large_print_web/routes/audit.py](web/src/acb_large_print_web/routes/audit.py))
- **The Site Audit live status page is now accessible.** It had no live region, no real progress bar, disabled the focused Cancel button on completion, and its poller retried a dead job forever with no `response.ok` check. It now announces every state/progress/error change into a polite live region, drives a `<progress>` element, surfaces the error inline, stops after repeated failures, and moves focus to the results link instead of dropping it. The "Private Access" card no longer claims protection on unprotected runs. ([web/src/acb_large_print_web/templates/site_audit_job.html](web/src/acb_large_print_web/templates/site_audit_job.html))
- **The deploy post-check no longer fails a healthy deploy on a probe race.** The external URL and CSP-header checks ran moments after Caddy restarts and a single early request could catch it mid-reload; both now retry with backoff. ([scripts/post-deploy-check.sh](scripts/post-deploy-check.sh))
- **Every ordinary Site Audit submission failed with "Working outside of application context."** The audit form's "run in background" box is checked by default, and the background path ran the scan on a bare `threading.Thread` whose worker called `_runs_root()` -- which reads `current_app.instance_path` -- after the request context that spawned it was gone. Flask raised `RuntimeError`, the worker caught it, and the job page reported the raw message as "Scan failed", which is what a user auditing a single page saw from two different machines. The thread body now runs inside `app.app_context()`, with the app object captured while the request is still live -- the same idiom the workshop pulse route already used. The background-job test previously stubbed the scanner and only checked the status endpoint's shape, so the swallowed error never failed it; it now waits for the job to finish and asserts a complete, error-free run, which fails against the old code. ([web/src/acb_large_print_web/routes/site_audit.py](web/src/acb_large_print_web/routes/site_audit.py), [web/tests/test_site_audit.py](web/tests/test_site_audit.py))
- **The weekly strict accessibility audit has failed every scheduled run since 2026-06-29 and nobody saw it,** because the strict step only runs on a schedule and every push-triggered run skipped it. Three pages failed -- user guide, workshop launchpad, workshop champion skill -- all reporting `0 blocking axe violation(s)`. The gate was red on axe `incomplete` results, not measured failures; the real ratios were 17.4:1, 17.4:1 and 14.19:1. Two were an axe limitation with a legitimate cause: `pre` carried a 1px border and no padding, and axe bounds a scroll container at `getBoundingClientRect().left + scrollWidth`, counting neither the border nor the fraction `scrollWidth` truncates, so wrapped text landed 1-20px outside the box axe computed and it could not resolve the background. `pre` now has padding, which also stops text touching its own border. The audit passes locally under the exact CI environment: 43 tests, 38 pages, 0 violations.
- **Workshop launchpad showed readers raw `<a href="...">` markup instead of links.** `escape()` returns `Markup`, and `Markup.replace()` escapes its replacement, so the anchors built in `_render_tokenized_workflow_text` were turned back into `&lt;a href=...&gt;` and rendered as visible text. The un-breakable URL inside then pushed the card past the right edge of the viewport -- a WCAG 1.4.10 Reflow failure at 1280px, worse at 320px -- which was the third strict-audit failure. Escaping now happens on a plain `str` and the trusted anchors are spliced in before re-wrapping, so untrusted text stays escaped; both behaviours have regression tests. `.workshop-panel > dl > dd` also gets `overflow-wrap: anywhere`, since the launchpad renders a bare `<dl>` that never picked up `.workshop-field-list`. ([web/src/acb_large_print_web/routes/workshop.py](web/src/acb_large_print_web/routes/workshop.py))
- **Four dark-mode contrast failures, none of which CI could see.** The accessibility gate audits the light theme only; dark mode is checked on the home page alone and only for violations, never `incomplete`. Found and fixed: the workflow tip (`.workflow-banner`, on audit, fix, convert, export and template) kept its light `#f0f5ff` background while text inherited `#e0e0e0` -- **1.21:1**, with its link at 1.98:1; `.flash-info`/`.flash-message` had the same fault at **1.97:1** on the link; `/changelog/` h3 headings computed `#1a1a1a` on `#121212` across 94 nodes -- **1.07:1**, effectively invisible; and `pre`/`kbd`/`table` kept `background-color: #ffffff` from the light rule with no dark counterpart, so a link crossing into a table sat at **2.16:1**. All now 6.29:1 or better, most above 11:1. Callout borders moved from `#1a4570` (1.90:1 against the page) to `#4a90d9` (5.60:1), since the fill is only 1.07:1 and the border is the sole thing separating the callout from the page. Light mode is unchanged throughout.

- **Site Audit was unreachable from the home page, and unmentioned on the page that sends people looking for it.** Reported by a user who could not find where to submit a URL: the "Assess Accessibility" card promised "a document or website" but rendered its Site Audit link behind an `{% elif %}`, so the link only ever appeared when Document Audit was *disabled* -- which it never is. The same `{% elif %}` hid three further calls to action: Build a Template, Braille Studio, and the Whisperer. All four cards now render every enabled destination, wrapped in a `.mission-card__links` list so the targets stay visually and programmatically separable; without it two `inline-block` anchors sat about thirteen pixels apart with overlapping focus rings and a target height under the 24px of WCAG 2.5.8. Document Audit and Site Audit now also point at each other, so arriving at the wrong one costs a single click instead of a support email. Files: [web/src/acb_large_print_web/templates/index.html](web/src/acb_large_print_web/templates/index.html), [web/src/acb_large_print_web/templates/audit_form.html](web/src/acb_large_print_web/templates/audit_form.html), [web/src/acb_large_print_web/templates/site_audit_form.html](web/src/acb_large_print_web/templates/site_audit_form.html), [web/src/acb_large_print_web/static/forms.css](web/src/acb_large_print_web/static/forms.css).
- **Speech Studio Quick Start no longer loops back to "upload again" (issue #84).** When a document is prepared asynchronously, `run_speech_prepare_job` redirects the user back to `/speech/?token=...`, but the `speech.speech_form` GET handler did not restore the prepared state, so the page looked like a fresh, un-prepared upload and the Preview/Download actions stayed hidden — an apparent infinite upload loop. The handler now re-reads the persisted `speech_prepare.json` (validating the token match, required fields, and a non-empty extracted-text file) and passes it to the template, which emits a `#speech-prepared-data` JSON block that [web/src/acb_large_print_web/static/speech.js](web/src/acb_large_print_web/static/speech.js) reads on load to restore the estimate, prefill the preview text, and reveal the preview/download buttons. Also excluded internal pipeline files (`speech_source.txt`, `speech_rendered.txt`, `speech_meta.json`, `speech_prepare.json`) from the upload-session scan in `speech_form` and `_resolve_document_source`, so the original uploaded filename (not a generated `speech_*` file) is shown and re-prepared. Files: [web/src/acb_large_print_web/routes/speech.py](web/src/acb_large_print_web/routes/speech.py), [web/src/acb_large_print_web/templates/speech.html](web/src/acb_large_print_web/templates/speech.html), [web/src/acb_large_print_web/static/speech.js](web/src/acb_large_print_web/static/speech.js). New regression tests in [web/tests/test_speech_routes.py](web/tests/test_speech_routes.py).
- **Live job progress now streams in real time** through the reverse proxy. Added `flush_interval -1` to the Caddy `reverse_proxy` for `letitglow.app` and narrowed `encode gzip` to a content-type allow-list so `text/event-stream` is never buffered or compressed. This affects every Server-Sent Events endpoint: job progress (convert, audit, fix, template, export, speech, page-flow), AI playground stream, speech stream, and the Ollama chat proxy. Previously the progress bar appeared frozen until the user manually refreshed. ([web/Caddyfile](web/Caddyfile))
- **SSE endpoints isolated from Caddy's `encode` handler.** The compression middleware inspects response chunks before deciding to skip non-matching content types, and that inspection buffered small SSE writes (progress deltas, heartbeats) even though `text/event-stream` was already off the allow-list. Moved `/job/*/status` and `/playground/stream` into a dedicated `@sse` matcher that bypasses `encode` entirely. ([web/Caddyfile](web/Caddyfile))
- **Gunicorn switched from sync to gthread workers** (`--worker-class gthread --workers 2 --threads 16 --keep-alive 75`). Sync workers serve one request per process, so each open SSE connection was holding one of four worker processes for up to the 30-minute stream timeout in [web/src/acb_large_print_web/routes/jobs.py](web/src/acb_large_print_web/routes/jobs.py). Four concurrent progress viewers wedged the entire app. Threaded workers handle long-lived streams alongside normal page loads, raising effective concurrency from 4 to 32. ([web/Dockerfile](web/Dockerfile))
- **Job progress bar stuck at 20% in production** because the page's progress-tracking JavaScript was an inline `<script>` block, which the site's `Content-Security-Policy: script-src 'self'` header silently blocks. The `EventSource` that drives the live progress UI was never created, so the bar never moved past the initial server-rendered value. Extracted the script to [web/src/acb_large_print_web/static/job-progress.js](web/src/acb_large_print_web/static/job-progress.js) and pass the SSE/poll URLs and initial state via `data-*` attributes on `#job-progress-root` in [web/src/acb_large_print_web/templates/jobs/progress.html](web/src/acb_large_print_web/templates/jobs/progress.html).
- **Maintenance mode toggle now reaches the web container.** Added `MAINTENANCE_MODE=${MAINTENANCE_MODE:-0}` to the `web` service environment in [web/docker-compose.prod.yml](web/docker-compose.prod.yml), so `scripts/maintenance-mode.sh` and `scripts/deploy-app.sh` can actually switch between the live site and the maintenance page. This fixes operator toggles that previously appeared to run but did not change app behavior.
- **Feature Flags CI import crash fixed for shared-core migration.** Added a new compatibility bridge at [web/src/acb_large_print_web/core_services.py](web/src/acb_large_print_web/core_services.py) that resolves `audit_by_extension`, `fix_by_extension`, and `convert_to_markdown` from `quill_glow_core` with per-symbol fallback to `acb_large_print_core`. Updated web routes/tasks (`convert.py`, `speech.py`, `audit.py`, `fix.py`, `chat_handler.py`, `magic_features.py`, `tasks/convert_tasks.py`) to import through the bridge so app startup and migrations no longer fail when `quill_glow_core` lacks `convert_to_markdown`.
- **Deploy workflow MCP test restored for markdown audits.** Updated [mcp_server/glow_mcp_utils.py](mcp_server/glow_mcp_utils.py) to resolve core services from `quill_glow_core` with fallback to `acb_large_print_core`, so `/audit` markdown requests no longer fail with HTTP 400 when only the fallback core package is installed in CI.
- **About page now shows the shared core library version explicitly.** The global template context now guarantees `component_versions.shared_core_library` (preferring `quill-glow-core`, then `acb-large-print-core`) and [web/src/acb_large_print_web/templates/about.html](web/src/acb_large_print_web/templates/about.html) displays that value for the "Shared service core package" field.
- **Production image builds now install shared core explicitly.** Added a `pip install` of the `quill-glow-core` source archive in [web/Dockerfile](web/Dockerfile) and [mcp_server/Dockerfile](mcp_server/Dockerfile) before installing `./desktop`, preventing deploy-time build failures when `quill-glow-core` is not resolvable from PyPI.
- **Queued uploads now persist across web and worker containers.** Added `GLOW_UPLOAD_TEMP_BASE=/app/instance/upload_temp` for both `web` and `worker` in [web/docker-compose.prod.yml](web/docker-compose.prod.yml), and made [web/src/acb_large_print_web/upload.py](web/src/acb_large_print_web/upload.py) honor that environment override. This keeps upload temp files in a shared writable volume and fixes queue jobs failing with `Upload token ... not found or expired`.
- **Audit queue handoff no longer deletes upload tokens before workers read them.** Updated [web/src/acb_large_print_web/routes/audit.py](web/src/acb_large_print_web/routes/audit.py) so async audit submits preserve the upload token (skip request-finally cleanup) after enqueuing `run_audit_job`, preventing immediate `Upload token ... not found or expired` failures on `/job/<id>/status`.

### Changed

- **Job progress page auto-advances on success.** When a queued job completes and a `continue_url` is set (e.g., PageFlow handing off to the narration page), the universal progress screen now announces "Done. Continuing\u2026" and navigates to the next step after a short delay. Any click or keypress cancels the auto-advance so users who want the Download or Continue link still control the page. ([web/src/acb_large_print_web/templates/jobs/progress.html](web/src/acb_large_print_web/templates/jobs/progress.html))

## [8.0.0] - 2026-05-23

### Added

- **PageFlow** at `/page-flow/`: extract readable article text from the web, follow simple next-page pagination, review and edit the cleaned text on-page, and download narrated audio from the same screen. Wired into the homepage mission grid and the Listen and Speak sidebar group.
- **Trafilatura-powered extraction dependency** added to the web app so PageFlow can turn messy article HTML into readable text before narration.

### Changed

- **Release versions synchronized to 8.0.0** across `VERSION`, `web/pyproject.toml`, `desktop/pyproject.toml`, `web/package.json`, and `office-addin/package.json`.

## [7.0.0] - 2026-05-13

### Added

- **Centralized version management**: Created root-level VERSION file as single source of truth; all components (desktop, web, office-addin) now read from it.
- **Version helper scripts**: Added `desktop/src/acb_large_print/version.py` and `web/src/acb_large_print_web/version.py` for dynamic version reading.
- **Office Add-in version helper**: Added `office-addin/src/version.ts` for TypeScript component version synchronization.
- **Increment version script**: New `scripts/increment-version.py` automates version bumping across all products with `--patch`, `--minor`, `--major` modes.

### Fixed

- **Accessibility improvements from main branch**: Contrast review noise fix, ARIA compliance enhancements, heading order corrections, landmark guardrails, and web app color contrast improvements.
- **Version consistency validation**: Updated `scripts/check-version-consistency.py` to validate VERSION file as authoritative source.
- **Feature flag defaults expanded**: Added `GLOW_ENABLE_USER_LOGIN` and `GLOW_ENABLE_ADMIN_LOGIN` flags (both disabled for 7.0.0) to support future user and admin authentication modes.
- **Public documentation link fixes**: Corrected broken internal links in user guide, PRD, and deployment documentation.
- **Accessibility tracking infrastructure**: Added logging for accessibility scan status and crawl noise detection to support continuous monitoring and trend analysis.

## [Unreleased]

### Fixed

- **Celery worker tasks crashing with "Working outside of application context"**: The previous fix (`celeryd_init` signal calling `create_app()`) was insufficient because the `@celery_app.task` decorators in `convert_tasks.py` execute at module-import time and bake in whatever `celery_app.Task` was at that moment (the default `celery.Task`). Reassigning `celery_app.Task` later did not retroactively rebind already-registered task classes. Rebuilt `web/src/acb_large_print_web/tasks/__init__.py` so `ContextTask` is a module-level class passed to `Celery(..., task_cls=ContextTask)` at app construction. Every `@celery_app.task`-decorated task (`glow.convert`, `glow.pageflow_extract`, `glow.speech`, `glow.template`, `glow.export`, `glow.audit`, `glow.fix`, `glow.speech_prepare`) now inherits the Flask-app-context wrapper regardless of import order. `ContextTask` also lazily bootstraps `create_app()` on first invocation as a safety net.

### Added

- **Celery worker liveness in `/health` and Docker healthcheck**: `web/src/acb_large_print_web/app.py` now probes the Celery worker pool via `celery_app.control.inspect().ping()` and includes a new `worker` entry in both `services` and `readiness`. When `CELERY_BROKER_URL` is configured but no workers respond, `/health` flips to `degraded`, which causes `scripts/deploy-app.sh` and `scripts/post-deploy-check.sh` to fail fast instead of marking a deploy as complete while jobs silently stall in `Queued` state. Added a corresponding Docker `healthcheck` to the `worker` service in `web/docker-compose.prod.yml` (runs `celery -A acb_large_print_web.tasks inspect ping`) so Docker surfaces a wedged worker for the `restart: unless-stopped` policy. Eager-mode (no broker) deployments report `not-configured` and remain green.

- **Queue-first heavy workflow expansion across the web app**: extended the shared `/job/<id>/` progress model beyond Convert to include Export, Template generation, Speech document preparation, Speech document/typed downloads, PageFlow extraction, single-file Audit submit, and non-interactive Fix runs. Added new queued task handlers in `web/src/acb_large_print_web/tasks/convert_tasks.py` plus retry dispatch support for these operations.
- **PageFlow queued extraction handoff**: added queued extraction operation support and a completion route (`/page-flow/from-job/<job_id>`) so users can resume in the editable PageFlow text screen after background extraction completes.
- **Job progress continue actions**: added optional `continue_url` support in job status payloads and progress UI so queued preprocess workflows can guide users back to the correct next step.
- **Queue route regression coverage**: added `web/tests/test_queue_routes.py` to validate queue path behavior for Template, Export, Speech Prepare, Audit, and Fix.

### Changed

- **Speech voice selection simplified**: Speech Studio now uses one combined voice combo box across ready engines instead of grouped radio clusters, and corresponding client-side state handling now reads/writes a single selected value.
- **PageFlow voice selection simplified**: PageFlow narration voice selection now uses one combined voice combo box and removed engine-filter UI/script complexity.
- **Speech prepare queue API response**: queued Speech document preparation now returns JSON (`202` with `job_url`) for fetch-based UI flows, while preserving synchronous fallback behavior when queueing is unavailable.
- **Canonical web domain defaults moved to `letitglow.app`** across deployment/runtime config: updated production Caddy routing, deploy script defaults, post-deploy checks, Keycloak hostname default, and maintenance/status helper guidance to use `letitglow.app` as the primary host while preserving legacy host behavior.
- **Legacy host redirect policy finalized with GGG exception**: legacy app hosts now redirect to canonical `letitglow.app` for normal routes, but continue to serve `/ggg*` directly so existing externally shared podcast/workshop distribution links keep working without redirect churn.
- **Community Access is now the default public branding profile**: switched default `GLOW_BRAND_PROFILE` behavior from `bits` to `communityaccess`, added Community Access logo asset, updated footer/org copy, and adjusted public-facing consent/about/privacy/guidelines wording toward neutral attribution.
- **OpenRouter referer and email sender defaults aligned to migration plan**: OpenRouter `HTTP-Referer` defaults now use `https://letitglow.app`, and Postmark default sender moved to `no-reply@notify.letitglow.app`.

### Fixed

- **Accessibility Regression Gate `/guide/` contrast stability**: strengthened code-block contrast for syntax-classed fenced code (`pre > code.language-*`) in `web/src/acb_large_print_web/static/forms.css` to prevent intermittent `color-contrast` serious violations in scheduled axe runs.
- **Accessibility Regression SARIF workflow reliability**: updated `.github/workflows/accessibility-regression.yml` to run the local locked `axe` binary (`npx --no-install axe`) instead of dynamically fetching `@axe-core/cli`, reducing Chrome/ChromeDriver version drift failures in CI.



## [7.6.0] - 2026-05-19

### Added

- **Convert: Generate clickable Table of Contents** option on the web Convert form and the desktop `convert-html` CLI (`--toc`, `--toc-depth`, `--toc-title`). Pandoc emits a fresh `<nav id="TOC">` with anchor links to every heading. For `.docx` sources, the original Word auto-generated table of contents (which Pandoc otherwise flattens to unlinked text) is automatically stripped so the new linked TOC does not appear twice. Implemented in `desktop/src/acb_large_print/pandoc_converter.py::convert_to_html` and wired through `web/src/acb_large_print_web/routes/convert.py` and `web/src/acb_large_print_web/templates/convert_form.html`.
- **Convert: Format-faithful conversion** toggle on the web Convert form. When checked, GLOW skips ACB styling, binding-margin injection, and the print-stylesheet post-processing step so the HTML output reflects the source document as closely as possible. The three existing formatting checkboxes (ACB formatting, binding margin, print stylesheet) are ignored when this option is active.
- **BITS column draft** at `docs/bits-article-glow-draft.md` (~980 words, plain language, deadline June 15, 2026) introducing GLOW to ACB affiliates and everyday users.

### 7.5.0 changes (rolled into 7.6.0)

### Added


- **Comprehensive PDF forms technical blueprint** in `pdf.md` with v1 execution scope, standards constraints, accessibility-first Field Definition Studio design, WCAG 2.2 AA keyboard and error-model requirements, open-source/commercial library evaluation notes, and a full data-storage architecture for documents, templates, submissions, artifacts, retention, and diagnostics. Generated companion HTML artifact at `pdf.html`.
- **Full ISO inspection framework for PDF forms** in `pdf.md`, including clause-family checkpoints (metadata, structure tree, semantics, forms/annotations, font/text mapping, destinations), multi-validator evidence normalization, mandatory human verification gates, licensed-text conformance-claim checkpointing, and a traceability artifact matrix for auditable technical review.
- **Production-grade AI operating model for PDF forms beta** in `pdf.md`, defining AI capability lanes (labels, options/grouping, help text, validation hints, sectioning), confidence and acceptance policy, human-in-the-loop review controls, prompt/version traceability, evaluation metrics and beta quality gates, cost/performance guardrails, and per-lane rollout/kill-switch feature flags.

- **Automation consent bypass** for scripted web workflows: requests that send `X-GLOW-Automation-Consent: GLOW` skip the first-visit consent redirect, and deployments can override the default with `GLOW_AUTOMATION_CONSENT_TOKEN`.
- **AI Playground streaming responses (SSE)** at `/beta/chat/stream` for token-by-token output rendering with automatic fallback to the legacy JSON endpoint when streaming is unavailable.
- **AI Playground quick controls**: regenerate response, stop generation, in-page model switcher, prompt templates, session quota banner, and conversation export as Markdown.
- **MarkItDown audio conversion choice for short MP3/WAV uploads** in the web Convert and Quick Start flows, so users can pick direct Markdown extraction for short clips while still using BITS Whisperer for larger recordings and broader audio format support.
- **Alt-Text Helper** at `/alt-text/` for AI-assisted alternative text drafting across standalone image files, Word, PowerPoint, Excel, PDF, and EPUB uploads. Quick Start and audit results can now hand visual-rich files directly into this workflow.
- **Alt-Text Helper variant generation**: `/alt-text/` now supports style selection (balanced, concise, detailed, instructional, narrative), multi-option suggestion generation (1/3/5), and optional per-page system-prompt add-ons for more diverse, controllable alt-text drafting.
- **AI request cost preview endpoint** at `/ai/usage/estimate` so Document Chat and AI Playground can show rough token and price estimates before sending.
- **Async conversion queue for web Convert** with Celery tasks, Redis-backed broker support, and a new /job route family for progress pages, SSE status streams, JSON polling, and secure result downloads.
- **Job progress accessibility regression tests** in `web/tests/test_jobs_accessibility.py` covering core semantics, missing-job 404 handling, poll responses, and result download behavior.
- **Workshop facilitator dashboard and delivery surfaces**: added `/workshop/session/<code>/facilitator` with live participation metrics and activity snapshots, plus explicit `/coach`, `/review`, and `/share` surfaces for workshop workflow handoffs.
- **Workshop multi-format artifact exports**: added JSON (`/export/json`), HTML (`/export/html`), and DOCX (`/export/docx`) exports in addition to existing markdown exports, and wired these into gallery/share/facilitator navigation.
- **Workshop route coverage tests** in `web/tests/test_workshop_routes.py` validating facilitator/coach/review/share routes and export endpoints.
- **Workshop follow-through persistence**: added `/workshop/session/<code>/follow-through` plus follow-through markdown export so users can save coaching templates, checklists, and 30-day commitments from workshop outputs.
- **Workshop follow-through discovery**: surfaced Workshop Follow-Through links in the main sidebar and homepage mission grid so users can continue after the workshop without hunting for the entry point.
- **Workshop sidebar placement refined**: moved the `Workshop Follow-Through` sidebar entry from the Experimental group into `Explore and Learn` so navigation aligns with workshop learning workflows.
- **Workshop follow-through tests** in `web/tests/test_workshop_routes.py` validating saved commitments and exported follow-through markdown.
- **Workshop interactive activity passport and structured forms**: upgraded `/workshop/session/<code>/activity/<activity_key>` with guided per-activity prompts, progress passport tracking, badge-style completion cues, and "save and continue" flow so workshop delivery feels more magical and hands-on while preserving export/follow-through compatibility.
- **Workshop conference-code and identity flow**: updated `/workshop/` to a two-step join journey (code lookup first, participant name second), added conference-code mappings via `instance/workshop_conference_codes.json` and `WORKSHOP_CONFERENCE_CODES_JSON`, and issued persistent guest participant tokens so people can return to their personal workshop content without login.
- **Workshop personal content surface**: added `/workshop/session/<code>/me` to show participant-specific submissions resolved from the guest token, with optional OIDC email binding when user login is available.
- **Workshop magical launchpad with tokenized workflows**: added `/workshop/session/<code>/launchpad` with scenario cards, downloadable sample documents from `samples/`, tokenized `[[GLOW:...]]` workflow steps, and deep links into Audit/Fix/Convert/Template/Chat/Alt-Text/Magic tools.
- **Cross-GLOW workshop return links**: added global `workshop_return` / `workshop_label` query handling in `base.html` for linked tool pages, now gated to active workshop participants so non-workshop users do not see workshop-return UI.
- **WCAG language processing for Convert uploads**: added deterministic language checks for uploaded/converted content (WCAG 3.1.1, 2.4.4, 3.3.2 plus plain-language long-sentence heuristics), configurable timing (`off`, `input`, `output`, `both`) and enforcement (`advisory`, `strict`) in `web/src/acb_large_print_web/templates/convert_form.html`, result reporting in `web/src/acb_large_print_web/templates/convert_result.html`, and default-enabled feature flags `GLOW_ENABLE_WCAG_LANGUAGE_PROCESSING` / `GLOW_ENABLE_WCAG_LANGUAGE_STRICT_MODE`.
- **Convert format coverage expanded**: added legacy Office binary support for `.doc` and `.ppt` plus plain-text `.txt` across the Convert stack by extending MarkItDown convertible inputs (`desktop/src/acb_large_print/converter.py`), adding LibreOffice pre-conversion mappings for legacy binaries (`desktop/src/acb_large_print/pandoc_converter.py`), and enabling chained Pandoc output routes from those formats (`web/src/acb_large_print_web/routes/convert.py` and `web/src/acb_large_print_web/upload.py`).
- **Presidio PII guardrails for AI routes**: added server-side PII sanitization for AI-bound text in Document Chat and alt-text suggestion routes (`/chat/`, `/alt-text/suggest`, and `/audit/suggest-alt-text`) via `web/src/acb_large_print_web/pii_guardrails.py`, added default-on feature flags `GLOW_ENABLE_PII_GUARDRAILS` / `GLOW_ENABLE_PII_GUARDRAILS_STRICT_MODE`, wired the new flags into the admin feature-flags UI, and added Presidio dependencies in `web/requirements.txt` and `web/pyproject.toml`.
- **Unified async orchestration controls for long-running jobs**: added retry/deadline/cancel semantics for Convert and Site Audit background jobs, including convert job metadata and retry dispatch support (`web/src/acb_large_print_web/tasks/convert_tasks.py`), shared async policy loading (`web/src/acb_large_print_web/async_orchestration.py`), new cancel/retry job routes (`web/src/acb_large_print_web/routes/jobs.py` and `web/src/acb_large_print_web/routes/site_audit.py`), and progress-page controls in `web/src/acb_large_print_web/templates/jobs/progress.html` and `web/src/acb_large_print_web/templates/site_audit_job.html`.
- **GGG podcast static-site deployment integration**: added a new `ggg` static service in `web/docker-compose.prod.yml`, routed `lp.csedesigns.com/ggg*` traffic to that service in `web/Caddyfile`, and added `scripts/deploy-ggg-content.sh` for targeted content sync. Standard production deploys now also run an optional server-local GGG sync inside `scripts/deploy-app.sh` (source `~/ggg` to destination `~/app/ggg` by default), regenerate/validate the feed when Node.js is available, and keep MP3 media out of GitHub.

### Changed

- **Release version source of truth enforced in web UI**: Updated `web/src/acb_large_print_web/app.py` to populate `release_version` from the root `VERSION` file via `web/src/acb_large_print_web/version.py`, and removed hard-coded version text from `web/src/acb_large_print_web/templates/index.html` and `web/src/acb_large_print_web/templates/about-mcp.html` so homepage/footer/about MCP messaging stay synchronized.
- **Version-file resolution hardened**: Updated both `web/src/acb_large_print_web/version.py` and `desktop/src/acb_large_print/version.py` to locate the repository `VERSION` file using module-relative parent traversal instead of fragile CWD-relative paths.
- **Regression coverage for release display sync**: Added tests in `web/tests/test_app.py` to assert homepage and about-page MCP version text matches the root `VERSION` value.
- **Homepage wording and semantics refined**: Removed overly technical "main branch" wording from the homepage release summary, and updated the supported-formats list markup in `web/src/acb_large_print_web/templates/index.html` so the `<ul>` always contains direct `<li>` children (feature toggles now use `hidden` on list items) to satisfy accessibility linting.
- **Deployment-gate test assertion hardened**: Updated `web/tests/test_app.py` to assert homepage release heading text using decoded response content instead of a brittle HTML-entity byte pattern, preventing false CI failures in the Deploy Web App workflow.
- **Landmark guardrail compliance in job progress template**: Removed redundant `aria-labelledby` from the `<section>` wrapper in `web/src/acb_large_print_web/templates/jobs/progress.html` to satisfy `web/tests/test_landmark_aria_guardrails.py` and avoid unnecessary region landmark noise.
- **Canonical version advanced to 7.2.0**: Updated root `VERSION` to `7.2.0` and synchronized `desktop/pyproject.toml`, `web/pyproject.toml`, `office-addin/package.json`, and `web/package.json` so all release surfaces read the same value.
- **Version consistency validator source-of-truth corrected**: Updated `scripts/check-version-consistency.py` to read from root `VERSION` (single source of truth) and validate changelog coverage for either `## [X.X.X]` release headings or `### X.X.X (Unreleased)` markers.
- **Job progress accessibility test alignment**: Updated `web/tests/test_jobs_accessibility.py` to assert the current `<section class="card">` structure without `aria-labelledby`, keeping test expectations consistent with the section-landmark guardrail enforced in `web/tests/test_landmark_aria_guardrails.py`.
- **Background job status payloads expanded**: job status endpoints now include attempt/max-attempt metadata and retry availability so UI polling and SSE streams can render consistent cancel/retry behavior.
- **Admin-login flag now hides login references and auth entry points**: Added `feature_admin_login_enabled` template context in `web/src/acb_large_print_web/app.py`, hid the footer Admin Sign-In link in `web/src/acb_large_print_web/templates/base.html` when disabled, removed admin-auth wording from `web/src/acb_large_print_web/templates/privacy.html` when disabled, and gated admin authentication entry routes in `web/src/acb_large_print_web/routes/admin.py` (login, request-access, magic-link, OAuth start/callback) with 404 when `GLOW_ENABLE_ADMIN_LOGIN` is false.
- **Footer admin access sentence now feature-gated**: The footer text `Admin features are restricted to approved administrative accounts.` in `web/src/acb_large_print_web/templates/base.html` now renders only when `feature_admin_login_enabled` is true.
- **Web container now carries canonical VERSION file**: Added `COPY VERSION /app/VERSION` to `web/Dockerfile` so `web/src/acb_large_print_web/version.py` can resolve release metadata at runtime in production containers.
- **Release-version fallback hardened**: Updated `web/src/acb_large_print_web/app.py` to fall back to installed package metadata (`acb-large-print-web`) instead of hardcoded `1.0.0` when reading `VERSION` fails.
- **Admin auth gate test-mode compatibility**: Updated `web/src/acb_large_print_web/routes/admin.py` so the login-route feature gate (`GLOW_ENABLE_ADMIN_LOGIN`) is bypassed in Flask `TESTING` mode, preserving production lockout behavior while keeping existing admin auth tests valid in CI.
- **Footer deploy and WCAG gate visibility**: Added footer status lines in `web/src/acb_large_print_web/templates/base.html` and client refresh logic in `web/src/acb_large_print_web/static/a11y-enhancements.js` to display `WCAG 2.2 AA` gate status, `WCAG 2.2 AAA` gate status, and current deployment phase from `/health`.
- **Health endpoint deployment telemetry**: Extended `web/src/acb_large_print_web/app.py` `/health` payload with a new `deployment` section (`state`, `phase`, `detail`, `updated_at_utc`, and `gates`) and readiness summaries for `wcag22aa_gate` / `wcag22aaa_gate`.
- **Deploy scripts now publish deploy-phase status**: Updated `scripts/deploy-app.sh` and `scripts/post-deploy-check.sh` to write phase/state updates into `instance/deploy-status.json`, allowing `/health` and footer UI to reflect real-time deployment progress and verification state.
- **Homepage 7.2.0 "What's New" now includes MCP docs link**: Updated `web/src/acb_large_print_web/templates/index.html` to include MCP server documentation link directly in the top "What's New in GLOW {{ release_version }}" section and removed the temporary footer MCP mention from `web/src/acb_large_print_web/templates/base.html`.
- **Pre-commit now stages all generated HTML partial artifacts**: Updated `scripts/pre-commit-check.py` to auto-stage `deployment_body.html` and `announcement_body.html` in addition to existing generated partials after `scripts/build-doc-pages.py` runs.
- **Office Add-in dependency security remediation**: Updated `office-addin/package.json` overrides and regenerated `office-addin/package-lock.json` to resolve transitive OpenTelemetry vulnerabilities (`@opentelemetry/exporter-prometheus`, `@opentelemetry/sdk-node`, and `@azure/monitor-opentelemetry`) reported by `npm audit`.
- **MCP server dependency security remediation**: Updated `mcp_server/requirements.txt` to bump `python-multipart` from `0.0.9` to `0.0.28`, addressing open Dependabot alerts against multipart parsing.
- **WCAG gate status wiring in deploy pipeline**: Updated `.github/workflows/deploy.yml` to resolve the `Accessibility Regression Gate` conclusion for the current commit and pass it to remote deployment via `WCAG22AA_GATE` / `WCAG22AAA_GATE` env vars, then updated `scripts/deploy-app.sh` and `scripts/post-deploy-check.sh` to persist these values in `instance/deploy-status.json` for `/health` and footer display.
- **Footer gate/deploy labels normalized**: Updated `web/src/acb_large_print_web/static/a11y-enhancements.js` to translate raw internal states (for example `not-reported`, `not-configured`, `unknown`) into user-friendly phrases (`awaiting report`, `not configured`, `checking`).
- **WCAG footer status consolidated into one magical line**: Replaced separate AA/AAA footer rows in `web/src/acb_large_print_web/templates/base.html` with a single sentence and updated `web/src/acb_large_print_web/static/a11y-enhancements.js` to report `WCAG 2.2 AA` status plus tracked `AAA` progress in one combined, reader-friendly phrase.
- **Deployment footer status now uses plain-language states**: Updated `web/src/acb_large_print_web/static/a11y-enhancements.js` so idle/no-rollout, in-progress, completed, and failed deployment states render as clear human-readable messages (with optional last-update context) instead of terse phase/state placeholders.
- **MCP server is now deployed and routed in production stack**: Added `mcp_server/Dockerfile`, introduced an `mcp` service in `web/docker-compose.prod.yml`, routed `/mcp/*` through `web/Caddyfile` to `mcp:8000`, and expanded deployment verification (`scripts/post-deploy-check.sh` and `scripts/deploy-app.sh`) to include MCP health checks.
- **Deploy workflow now includes MCP changes and tests**: Updated `.github/workflows/deploy.yml` to trigger on `mcp_server/**` changes and run `mcp_server/tests` in the pre-deploy test job.
- **Keycloak realm import isolation in production deploys**: Updated `scripts/deploy-app.sh` to render Keycloak realm JSON into `web/keycloak/import/` and clear stale generated files, updated `web/docker-compose.prod.yml` and `web/docker-compose.keycloak.yml` to mount that dedicated import directory, and updated deployment docs/partials so Keycloak no longer imports placeholder template files from persistent volume state.
- **Keycloak admin UI proxy compatibility**: Scoped strict web security headers in `web/Caddyfile` to the Flask app handle only, so `/auth/*` responses keep Keycloak-managed headers and the admin console no longer hangs on `Loading...`.
- **Postmark wiring for admin magic-link auth setup**: Added `POSTMARK_SERVER_TOKEN`, `POSTMARK_FROM_EMAIL`, `ADMIN_BOOTSTRAP_EMAILS`, and `ADMIN_MAGIC_LINK_TTL_MINUTES` to `web/.env.example`; clarified admin login messaging in `web/src/acb_large_print_web/templates/admin_login.html`; and documented these variables in `docs/deployment.md` and `web/README.md` so email-based admin magic links can be enabled cleanly.
- **Canonical version advanced to 7.5.0**: Updated root `VERSION` to `7.5.0` and synchronized `desktop/pyproject.toml`, `web/pyproject.toml`, `office-addin/package.json`, and `web/package.json`.

### 7.2.0 (Unreleased)

#### Added
- GLOW MCP server (`mcp_server/`):
  - FastAPI-based MCP API for agent integration
  - Endpoints: `/health`, `/audit`, `/fix`, `/convert`, `/report`
  - OpenAPI spec and full documentation
  - Designed for integration with Accessibility Agents (e.g., markdown-a11y-assistant)

#### Changed
- (pending) Integrate GLOW audit/fix/convert/report logic into MCP server

#### Fixed
- N/A

#### Removed
- N/A

- **Settings page refreshed** with visible AI and Beta checkpoints, including a new AI and Beta hub that links to AI Features, AI Playground, and Magic Lab when available.
- **Sidebar terminology cleaned up** so the experimental navigation group reads as Experimental instead of the run-together Beta/Experimental label.
- **Home page What's New** now points to GLOW 6.0.0 and highlights AI Playground, AI Features, and MarkItDown + AI integration.
- **Settings headings** now appear for each settings group so the page has explicit section headings in addition to fieldset legends.
- **AI feature flag split for chat surfaces**: `GLOW_ENABLE_AI_CHAT` now gates Document Chat only, while new `GLOW_ENABLE_AI_GENERAL_CHAT` gates AI Playground/general chat.
- **Production AI defaults aligned to Ollama-first rollout**: `GLOW_ENABLE_AI`, `GLOW_ENABLE_AI_GENERAL_CHAT`, `GLOW_ENABLE_AI_HEADING_FIX`, and `GLOW_ENABLE_AI_MARKITDOWN_LLM` default on in production compose; Document Chat, Whisperer, and alt-text remain off by default.
- **Ollama key setup flow** now requires successful key validation before save and keeps the save button disabled until validation succeeds.
- **Ollama key format handling** now accepts valid keys even when they do not use the historical `ollama_` prefix.
- **Ollama cloud defaults** now prefer `gemma3:4b` instead of `llama3.2`, and validation returns a suggested model based on what the account can actually run.
- **AI settings and playground pages** now load through external static JS/CSS assets so they work under the site CSP instead of relying on blocked inline scripts.
- **Ollama inference errors** now distinguish account inference authorization (`401`), paid-plan model gating (`403`), and missing account model access (`404`).
- **AI Features setup** now supports multiple personal providers at the same time, including Ollama Cloud, OpenRouter, OpenAI, and Google Gemini, with provider-specific key validation and session-scoped storage.
- **AI feature bindings** are now capability-aware: GLOW only offers models for a feature when the selected provider/model can actually support that workflow, including vision-gated alt-text suggestions and audio-gated Whisperer entry points.
- **AI usage meter and AI settings terminology** now describe the active personal provider generically instead of assuming every personal AI session is Ollama.
- **AI Features settings** now include session-scoped lease timing controls plus configurable base prompts for alt-text drafting and MarkItDown image-description workflows.
- **AI chat surfaces** now show rolling session quota information and rough token/cost preview text before request submission when model pricing is available.
- **Admin AI settings** now support a rolling per-session AI request cap and reset window in addition to the existing monthly budget and workload-specific limits.
- **MarkItDown capability coverage** now includes packaged support for all upstream extras in both the desktop and web Python package metadata, aligning installed behavior with the broader conversion formats already documented by MarkItDown upstream.
- **Quick Start audio routing** now offers both Convert and BITS Whisperer for `.mp3` and `.wav` files, while keeping longer or broader audio workflows on Whisperer.

### Fixed

- **Convert pipeline false-negative failure in CI**: Updated `web/src/acb_large_print_web/routes/convert.py` so WCAG language text extraction fails open when MarkItDown cannot parse a generated output artifact (for example, mocked or malformed EPUB bytes), preventing successful conversions from returning HTTP 500.
- **Rules Reference accessibility filters:** Removed a stale duplicate Type filter on `/rules/` that reused `id="filter-type"`, resolving axe `duplicate-id-aria` and `form-field-multiple-labels` findings.
- **Quick Start contrast review noise:** Replaced gradient upload-hero backgrounds with solid high-contrast surfaces and added explicit foreground colors to file/text inputs and textareas so axe can calculate contrast reliably.
- **Crawl accessibility cleanup:** Removed the remaining public raw Markdown deployment link, replaced decorative workflow banner glyphs, converted symbolic keyboard labels to text, and normalized code/table/textarea surfaces so automated contrast tools can compute foreground/background colors more reliably.
- **Documentation contrast review noise:** Hardened documentation table and code-block layout so long content wraps inside its own painted box instead of visually overlapping adjacent cells or partially obscuring code text during axe color-contrast analysis.
- **Deployment guide code blocks:** Kept generated `<pre><code>` snippets from exposing the inner `code` element as a block-level box, clearing axe color-contrast incomplete checks caused by the scroll container partially covering bash examples.
- **Public documentation links:** Replaced raw `.md` documentation links in web-facing guide, FAQ, and PRD pages with HTML routes, and added `/deployment/` as the public deployment guide page.
- **Audit and Template heading order:** Promoted top-level in-content headings on `/audit/` and `/template/` to `h2`, resolving axe `heading-order` findings from same-origin urlCheck crawls.
- **AI usage meter landmark:** The inactive AI meter now exposes the same complementary landmark semantics as active meter states, resolving axe `region` findings on the consent page.
- **Web App Color Contrast:** Darkened low-contrast sidebar, breadcrumb, grade, copied-button, and disabled-button colors in `web/src/acb_large_print_web/static/forms.css`; added missing dark-mode overrides for file inputs, upload drop zones, AI panels, action cards, chat turns, and progress panels so core GLOW pages remain readable in dark theme.
- **Feature Flags CI failures** now pass the web landmark guardrail again after removing redundant `section[aria-labelledby]` markup from the Alt-Text Helper and audit report templates, and the workflow now also triggers when its desktop or config-check dependencies change.
- **AI Playground character counter** no longer announces every keystroke to screen readers while typing. The counter still updates visually and remains available through the textarea description without repeated live-region interruptions.
- **AI Playground response cards** now keep model/copy controls after the response text instead of embedding them in the response heading, and assistant message wrappers no longer add extra spoken labels beyond the heading structure.
- **AI usage meter** now increments correctly for Ollama-backed chat turns by reading the current quota field returned by the server.
- **AI Playground long-running responses** now announce progress to screen reader users after a delay and announce completion when a delayed response arrives, instead of relying only on the visible thinking indicator.
- **Server-side AI feature gates** now recognize built-in server-provider paths for alt-text and Whisperer instead of requiring a personal provider session before those features can appear.
- **Legacy alt-text suggestion endpoint** no longer stops at DOCX media only. It now uses the shared visual extractor so PowerPoint, Excel, PDF, EPUB, and standalone image workflows stay aligned.
- **Quick Start and Speech Studio routing** no longer advertise document-chat or speech actions for uploaded audio files that are outside those workflows.
- **Job progress page semantics** now provide clearer live-region and progress labeling (`aria-labelledby`, `aria-describedby`, assertive error alerts, and hidden-state download toggling) to improve screen reader behavior during queue updates.

---

## [6.0.0] - 2026-05-09

### Added

- **AI Playground (Beta)** at `/beta/chat/` for open-ended Ollama model exploration
  - Accessible H3/H4 heading structure for keyboard and screen reader navigation
  - Per-feature Ollama model selection in unified AI Features settings
  - Session-scoped conversation history (not persisted by default)
  - Typing indicator, thinking animation, and copy-to-clipboard on responses
  - Smart response states: pending bubble → response with model name

- **MarkItDown + AI Integration** for intelligent document cleanup and extraction
  - LLM-enhanced MarkItDown support for better text extraction quality
  - Heading detection to convert bold/large text into semantic headings
  - See [MarkItDown + AI Integration Guide](#markitdown--ai-integration-guide) for details

- **Per-feature Ollama model selection** via unified AI Features settings page
  - Choose different models for heading detection, MarkItDown, and playground
  - Smart model recommendations based on feature workload
  - Validate keys before saving without overwriting previous choices

- **AI usage meter** in sidebar showing session-level request counts
  - Refreshes on page load and after AI actions
  - Helps users track what they have used in the current session

- **Feedback-to-issue automation** for capture and GitHub sync
  - Collect contact details for follow-up
  - Optional sync into GitHub Issues when configured

- **Open source contribution guidance** in README and release messaging
  - Fork → branch → pull request → review workflow
  - Clear branch protection and CI gating expectations

### Changed

- **AI feature defaults** for 6.0.0:
  - `GLOW_ENABLE_AI`: `True` (master switch on)
  - `GLOW_ENABLE_AI_HEADING_FIX`: `True` (heading detection enabled by default)
  - `GLOW_ENABLE_AI_MARKITDOWN_LLM`: `True` (MarkItDown LLM enabled by default)
  - `GLOW_ENABLE_AI_CHAT`: `False` (document chat off, beta)
  - `GLOW_ENABLE_AI_ALT_TEXT`: `False` (alt-text generation off, beta)
  - `GLOW_ENABLE_AI_WHISPERER`: `False` (uses OpenRouter, separate config)

- **Ollama-first setup path**: Users bring their own Ollama Cloud key; no server-side AI provider required for heading/MarkItDown

### Deprecated

- Document Chat deferred to 6.1.0+ (not recommended in 6.0.0)
- Direct OpenRouter support remains available for existing deployments

### Security

- Ollama API keys held only in server-side session storage, never logged or written to disk
- Session cookies are HttpOnly and Secure
- CSRF protection on all state-changing AI actions

### Planned for 6.1.0

- **Session quota enforcement.** Rate limiting to prevent accidental AI overuse: configurable requests-per-session with countdown timer in UI.
- **Conversation analytics dashboard.** Track model usage, success rates, and popular prompts (anonymized, no PII).

---

## [6.0.0] - 2026-05-09

### Added

- **AI Playground (Beta).** New standalone chat surface at `/beta/chat/` for open-ended Ollama experimentation without document context. Features H3/H4 heading structure for keyboard/screen-reader navigation, typing indicator, temporary conversation storage, and copy-to-clipboard buttons.
- **Per-feature Ollama model selection.** Users can now choose different Ollama models for each AI feature (heading detection, MarkItDown, playground) in AI Features settings.
- **Open source contribution flow.** Added release notes and combined announcement files explaining the community contribution process.
- **Feedback-to-issue automation.** Feedback submissions can collect contributor name and email and sync into GitHub Issues when configured.
- **Ollama Cloud user key support.** Added session-scoped Ollama Cloud key handling and per-feature toggles.
- **Session AI usage meter.** Added a sidebar meter and `/ai/usage/` endpoint for session-level usage tracking.
- **AI setup page.** Added a focused settings page for turning AI on, validating a key, and choosing a model.

### Changed

- **AI Feature enablement logic.** Playground feature is properly gated and enabled when master AI is on and Ollama key is configured.
- **Template context flags.** Added `ollama_active` and `ai_playground_enabled` aliases for cleaner template logic.
- **AI feature defaults.** For the Ollama path, heading detection and MarkItDown are enabled by default; Document Chat stays off.
- **About page and user guide.** Both now explain AI capabilities in short form and show the active feature set when enabled.

### Fixed

- **Pre-commit checker compliance.** Fixed `check-config-consistency.py` to handle new `GLOW_ENABLE_AI` and per-feature toggles correctly.

### Security

- **Session-only keys.** User-provided AI keys stay in server-side session and are never logged or written to disk.

---

## [Unreleased - Design System & UX Polish]

### Added

- **Web: dedicated AI Features entry and browser error reporting.** Added a first-class `/ai/` surface, a matching `AI Features` sidebar link, a browser-to-server `/ai/client-log` diagnostics endpoint, and shared `client-logging.js` so frontend failures on the AI setup flow are logged with request context instead of disappearing into the browser console.
- **Web: request ID correlation for AI failures.** Added per-request `X-Request-ID` response headers, included the ID in server request logs, and passed request IDs through AI setup fetch/error handlers plus `/ai/client-log` payloads so frontend failures can be traced to specific backend requests.
- **Web: CSS design tokens for mission accent colors.** Added `:root` custom properties `--color-assess`, `--color-fix`, `--color-transform`, `--color-listen`, `--color-explore`, and `--sidebar-width` to `forms.css` for consistent theming across all accent-color usages.
- **Web: SVG icons on all 15 sidebar navigation links.** Each sidebar link now has a 16×16 inline SVG icon (`aria-hidden="true"`, `focusable="false"`, `class="nav-icon"`) in `base.html`. Icons fade to full opacity on hover/active.
- **Web: Active sidebar group label accent color.** When the current page belongs to a mission group, the group's `<span class="sidebar-group-label">` inherits the group's accent color and top-border accent.
- **Web: Page breadcrumb context pill.** A colored `.page-breadcrumb` chip now appears above the `<h1>` on every tool page, showing the current mission group name and accent color.
- **Web: Mission card hover lift animation.** Mission cards on the home page now lift `translateY(-2px)` with an elevated box-shadow on hover. Animation is gated behind `@media (prefers-reduced-motion: no-preference)`.
- **Web: Upload hero centered card layout.** The Quick Start file upload page (`process_form.html`) now renders inside a `.upload-hero` centered card with a gradient background, blue accent border, and a dashed drop-zone file input.

### Changed

- **Web: AI defaults now ship enabled for Ollama-first rollout.** Updated `web/src/acb_large_print_web/feature_flags.py` and `web/instance/feature_flags.json` so `GLOW_ENABLE_AI`, `GLOW_ENABLE_AI_HEADING_FIX`, and `GLOW_ENABLE_AI_MARKITDOWN_LLM` default to `true`, while chat/whisperer/alt-text remain opt-in/off by default.
- **Web: AI setup is no longer treated as a Settings subpage.** Legacy `/settings/ai` links now redirect to the canonical `/ai/` page.
- **Office Add-in: patched `fast-uri` transitive vulnerability (GHSA-v39h-62p7-jpjc).** Added `"fast-uri": ">=3.1.2"` to `office-addin/package.json` `overrides` and regenerated `office-addin/package-lock.json` so `fast-uri` resolves to `3.1.2`.
- **Office Add-in: patched `fast-xml-builder` transitive vulnerability.** Added `"fast-xml-builder": ">=1.1.7"` to `office-addin/package.json` `overrides` and regenerated `office-addin/package-lock.json` so `fast-xml-builder` resolves to `1.2.0`.
- **Office Add-in: resolved remaining moderate transitive advisories.** Added `"hono": ">=4.12.18"`, `"express-rate-limit": ">=8.5.1"`, and `"ip-address": ">=10.1.1"` to `office-addin/package.json` `overrides` and regenerated `office-addin/package-lock.json`, resulting in `npm audit` reporting zero vulnerabilities.
- **Web: Toast container relocated to fixed bottom-right overlay.** `#toast-container` moved from inside `<main>` to just before `</body>`, so toasts no longer shift page layout.
- **Web: Sidebar dark-mode background deepened.** Dark mode sidebar background updated from `#1e1e1e` to `#141414` with depth shadow.
- **Web: Home page mission hub de-duplicated (repetition fix).** Mission cards now have short outcome-focused descriptions and single primary CTA links instead of re-listing multiple sidebar links.

---

## [5.0.0] -- 2025-07-14

### Added

- **Web: Goal-oriented left sidebar navigation (GLOW 5.0.0 UX redesign).** Replaced the horizontal overflow-scrolling tab bar on every page with a responsive, grouped left sidebar. The sidebar organises all tools into five mission groups: Assess (Document Audit, Site Audit), Fix and Build (Fix Document, Build Template), Transform (Convert Format, Braille Studio), Listen and Speak (Speech Studio, Whisperer), and Explore and Learn (Document Chat, Magic Lab, Guidelines, User Guide, FAQ, Settings). Implemented in `web/src/acb_large_print_web/templates/base.html` and `web/src/acb_large_print_web/static/forms.css`.

- **Web: `sidebar.js` -- accessible sidebar toggle controller.** New script `web/src/acb_large_print_web/static/sidebar.js` manages mobile slide-over open/close with `aria-expanded` state, focus trap, Escape-key dismissal, overlay click dismissal, and desktop/mobile breakpoint cleanup. Moves focus to the first sidebar link on open; restores focus to the hamburger button on close.

- **Web: Mobile header bar with hamburger toggle.** Added a sticky `.mobile-header` bar (visible below 64em) containing the hamburger `<button id="sidebar-toggle">` and a mobile brand link. The sidebar slides in over a semi-transparent overlay when toggled on small screens.

- **Web: GLOW 5.0.0 Mission Hub home page.** Replaced the GLOW 4.0.0 home page with a goal-oriented mission hub. The page opens with a GLOW 5.0.0 announcement banner, five mission cards (Assess, Fix and Build, Transform, Listen and Speak, Explore and Learn) each with feature-flag-aware tool links, a Quick Start call-to-action, supported format pills, and the GLOW Anthem section. Old duplicated card grid and tabs-explanation section removed. Updated `web/src/acb_large_print_web/templates/index.html`.

- **Web: Mission card CSS (`.mission-grid`, `.mission-card`).** Added mission grid layout and per-group accent border colours to `web/src/acb_large_print_web/static/forms.css`. Dark theme support included.

- **Web: Corrected ARIA navigation pattern.** All sidebar navigation links use `aria-current="page"` (correct ARIA 1.1 pattern for navigation). The prior implementation used `role="tablist"` and `role="tab"` for navigation links -- a misuse of the ARIA tab pattern -- which has been removed.

### Changed

- **Web: CSS layout redesign.** `body` max-width and padding overrides removed; layout now uses a flex `.app-layout` container (sidebar + `.content-area`). The `main` element applies `padding: 1.5rem clamp(1rem, 3vw, 2.5rem)` and `max-width: min(66rem, 100%)` internally. Print stylesheet updated to hide sidebar/mobile-header and reset layout to block. UA Arizona and dark-mode theme colour rules updated to target sidebar classes.

- **Web: Versions bumped to 5.0.0.** `web/pyproject.toml` version `4.0.0` → `5.0.0`; `desktop/pyproject.toml` version `4.0.0` → `5.0.0`; `desktop/src/acb_large_print/__init__.py` `__version__` `3.0.0` → `5.0.0`.

### Previously in Unreleased (now part of 5.0.0)

### Added

- **Web: Site Audit scanner and artifact export workflow.** Added a new
  feature-flagged `/site-audit` surface with URL/sitemap input, optional
  in-site crawling, per-run page scanning, and downloadable artifacts
  (summary JSON, findings CSV, session log, and bundled ZIP). Added backend
  scanner service in `web/src/acb_large_print_web/site_audit.py`, new route
  blueprint in `web/src/acb_large_print_web/routes/site_audit.py`, new
  templates `web/src/acb_large_print_web/templates/site_audit_form.html` and
  `web/src/acb_large_print_web/templates/site_audit_result.html`, and nav/home
  integration in `web/src/acb_large_print_web/templates/base.html` and
  `web/src/acb_large_print_web/templates/index.html`.

- **Web: Site Audit defaults in browser settings.** Added client-side
  preference persistence for Site Audit options (`max pages`, `crawl links`,
  `include subdomains`, `force`) in
  `web/src/acb_large_print_web/static/preferences.js` and Settings UI controls
  in `web/src/acb_large_print_web/templates/settings.html`.

- **Web: new feature flag `GLOW_ENABLE_SITE_AUDIT`.** Added the server-side
  flag default in `web/src/acb_large_print_web/feature_flags.py`, context
  injection in `web/src/acb_large_print_web/app.py`, admin flag rendering in
  `web/src/acb_large_print_web/routes/admin.py`, and seeded instance defaults
  in `web/instance/feature_flags.json` and `instance/feature_flags.json`.

- **Web tests: Site Audit route and flag coverage.** Added
  `web/tests/test_site_audit.py` and extended
  `web/tests/test_admin_flags.py` to assert `GLOW_ENABLE_SITE_AUDIT` renders in
  the admin Feature Flags page.

- **Web: Advanced Site Audit crawl controls.** Added crawl-depth controls,
  same-path crawl scoping, and URL exclusion patterns to Site Audit form
  processing and crawler behavior. Updated route parsing in
  `web/src/acb_large_print_web/routes/site_audit.py`, crawler options and
  expansion logic in `web/src/acb_large_print_web/site_audit.py`, Site Audit
  form/result templates in
  `web/src/acb_large_print_web/templates/site_audit_form.html` and
  `web/src/acb_large_print_web/templates/site_audit_result.html`, and
  persisted defaults in `web/src/acb_large_print_web/static/preferences.js`
  plus `web/src/acb_large_print_web/templates/settings.html`.

- **Web docs: Site Audit walkthrough expansion.** Expanded
  `docs/user-guide.md` Site Audit documentation with full option reference,
  crawl depth guidance, practical run presets, and operational tuning tips.

- **Web: Site Audit strict open-source learning mode.** Added a
  `strict_open_source_only` option that limits per-finding remediation links to
  open accessibility sources (W3C/WAI + A11Y Project) and suppresses non-core
  references when strict mode is enabled.

- **Web: Site Audit background jobs with status and cancel.** Added user-facing
  asynchronous crawl execution with a dedicated job status page and JSON status
  endpoint, plus cancellation support.

- **Web: Site Audit private tokenized run access with optional password.** Added
  protected run links backed by token hashing and optional password hashing,
  plus unlock flow and access checks for run views and artifact downloads.

### Fixed

- **Web: fix-result page no longer renders download helper JavaScript as
  visible text.** `web/src/acb_large_print_web/templates/fix_result.html`
  now wraps the download-status behavior in a proper `<script>` element so
  the button/status enhancement executes instead of appearing in the page
  content.

- **Web: file picker Enter-key upload fallback across document forms.**
  `web/src/acb_large_print_web/static/a11y-enhancements.js` now adds a
  keyboard fallback for focused single-file inputs: when a file is selected,
  pressing Enter on the file input submits the owning form via
  `requestSubmit()`. This hardens upload behavior for browser/file-dialog
  combinations where keyboard confirmation can leave users at the file input
  without completing the upload path.

- **Web: explicit Upload selected file helper action on forms.**
  `web/src/acb_large_print_web/static/a11y-enhancements.js` now injects an
  additional button for single-file inputs labeled "Upload selected file".
  The helper button is enabled only after file selection and submits the
  owning form directly, providing a clear keyboard path independent of native
  file-dialog controls.

---

## [4.0.0] - 2026-05-04

### Added

- **Roadmap core feature regression tests.** Added
  `web/tests/test_magic_routes.py` to cover table advisor, pronunciation
  dictionary CRUD/preview/export, rule proposal submission/listing,
  compare-route behavior, and feature-flag 404 gating for OCR/reading-order.
- **ODT conversion tests.** Added `web/tests/test_convert_odt.py` to verify
  `to-odt` conversion happy-path rendering and feature-flag enforcement.
- **Speech streaming tests.** Extended `web/tests/test_speech_routes.py` with
  checks for `/speech/stream` flag gating and pronunciation dictionary
  pre-processing behavior.
- **Admin flags coverage for roadmap core pack.** Extended
  `web/tests/test_admin_flags.py` to assert that all 11 roadmap-core feature
  flags render as toggleable controls in `/admin/flags`.

### Changed

- **Roadmap cleanup.** `roadmap.md` now removes completed v3.1.0 backlog items
  (1.5, 2.5, 2.6, 3.3, 3.4, 3.5, 3.6, 4.3, 7.3, 7.4, 9.1) from active themes
  and tracks them under a dedicated completed section.

### Fixed

- **Markdown to PDF styling cascade now preserves ACB formatting.**
  `desktop/src/acb_large_print/pandoc_converter.py` now embeds PDF CSS using
  Pandoc `--include-in-header` in the intermediate HTML, then renders that
  HTML directly with WeasyPrint. This prevents Pandoc default styling from
  overriding ACB heading/list/link styles in PDF output.

- **DOCX conversion line wrapping and LibreOffice input support improved.**
  Added `--wrap=none` for Pandoc DOCX generation to avoid soft-wrap line
  breaks in generated XML. Added `.fodt` as a native Pandoc input and added
  `.ods/.fods/.odp/.fodp` upload support with optional LibreOffice
  pre-conversion (`soffice`) into `.xlsx/.pptx` before the existing
  MarkItDown-to-Pandoc chain.

- **PDF tables now preserved in Word / HTML / EPUB exports.** When a PDF
  containing embedded tables is uploaded and converted to Word (`.docx`),
  HTML, EPUB, or any other Pandoc-backed output format, the tables are now
  extracted as Markdown pipe tables and included in the output document.
  Previously, MarkItDown's pdfminer.six text extraction silently dropped all
  table structure, producing flat text.  The fix adds
  `_pdf_to_markdown_with_tables()` to `desktop/src/acb_large_print/converter.py`,
  which uses PyMuPDF's `find_tables()` API (already a project dependency) to
  detect and format table cells, interleave them with surrounding text in
  reading order, and skip duplicate raw text blocks that fall inside table
  bounding boxes.  Falls back transparently to MarkItDown if PyMuPDF is
  unavailable.  18 new unit tests added in
  `desktop/tests/test_pdf_table_extraction.py`.

- **Compare endpoint extension mismatch.** `POST /magic/compare` now uses an
  explicit allow-list aligned with its UI and parser support (`.txt`, `.csv`,
  `.json`, `.xml`, `.html`, `.rst`, `.odt`, `.rtf`, plus existing types)
  instead of defaulting to the narrower upload allow-list.
- **PyMuPDF lifecycle robustness.** `magic_features.detect_reading_order_pdf()`
  and `magic_features.ocr_pdf()` now compute `pages_scanned` before closing
  the document handle, avoiding access to `len(doc)` after `doc.close()`.

- **Fix result re-audit flow hardening.**
  `web/src/acb_large_print_web/templates/fix_result.html` now submits the
  re-audit action through a CSRF-protected POST form to `/audit/from-fix`,
  including token, filename, standards profile, and prior finding context.
  Added regression coverage in `web/tests/test_fix_routes.py`.

- **Public release documentation sync for v4.0.0.** Updated canonical release
  and public-facing docs to align version messaging across changelog,
  announcements, combined announcement artifacts, PRD status, roadmap header,
  and user guide release framing.

---

## [3.1.0] - 2026-05-01

### Added

- **Roadmap core feature pack implemented (11 items, all feature-gated).**
  Implemented the roadmap additions requested for 1.5, 2.5, 2.6, 3.3, 3.4,
  3.5, 3.6, 4.3, 7.3, 7.4, and 9.1 as core platform capabilities with
  explicit server-side flags and production deployment requirements:
  - 1.5 **Braille back-translation quality scoring** in Braille Studio result
    view (`GLOW_ENABLE_BRAILLE_BACK_TRANSLATION_SCORE`).
  - 2.5 **Speech pronunciation dictionary management** with CSV import/export,
    preview, and synthesis pre-processing (`GLOW_ENABLE_SPEECH_PRONUNCIATION_DICTIONARY`).
  - 2.6 **Real-time streaming speech preview endpoint** at
    `POST /speech/stream` (`GLOW_ENABLE_SPEECH_STREAM`).
  - 3.3 **Table accessibility advisor API** at `POST /magic/table-advisor`
    (`GLOW_ENABLE_TABLE_ADVISOR`).
  - 3.4 **Reading order detection API** for PDFs at
    `POST /magic/reading-order` (`GLOW_ENABLE_READING_ORDER_DETECTION`).
  - 3.5 **OCR API for scanned PDFs** at `POST /magic/ocr` (best-effort when
    `pytesseract`/Pillow are available) (`GLOW_ENABLE_PDF_OCR`).
  - 3.6 **Document compare and change-tracking API** at `POST /magic/compare`
    (`GLOW_ENABLE_DOCUMENT_COMPARE`).
  - 4.3 **ODT export direction** in Convert (`to-odt`) backed by Pandoc
    (`GLOW_ENABLE_CONVERT_TO_ODT`).
  - 7.3 **Cognitive profile mode** (Plain & Simple) in Settings with local
    preference persistence and automatic help accordion expansion
    (`GLOW_ENABLE_COGNITIVE_PROFILE`).
  - 7.4 **Forced-colors/high-contrast mode support** in core CSS using system
    colors and forced-colors media-query rules (`GLOW_ENABLE_FORCED_COLORS_MODE`).
  - 9.1 **Public rule contribution portal** in Magic Lab (`/magic`) with
    proposal submission/list endpoints and Rules Reference cross-link
    (`GLOW_ENABLE_RULE_CONTRIBUTIONS`).

  **Deployment dependency tracking for this pack:**
  - Required: `pandoc` (ODT conversion and Speech document rendering paths)
  - Required: `python3-louis` + `liblouis-*` (Braille translation)
  - Optional/runtime-detected: `pytesseract`, Pillow, and Tesseract binary
    for OCR (`GLOW_ENABLE_PDF_OCR` returns clear unavailability diagnostics
    when dependencies are missing)
  - Required in CI: Node deps include `@axe-core/playwright` and
    `@axe-core/cli` for self-audit and SARIF generation

  **GitHub integration points:**
  - Implemented: SARIF output is uploaded to GitHub Code Scanning via
    `github/codeql-action/upload-sarif` in CI.
  - Clarified: rule proposals are currently stored in local SQLite and are
    not yet auto-synced to GitHub Issues/PRs; API-backed sync remains a
    future enhancement.

- **Comprehensive axe-core WCAG 2.2 AA audit of GLOW itself.**
  Added `web/e2e/tests/axe-audit.spec.mjs` — a Playwright-integrated
  `@axe-core/playwright` test suite that audits all 17 public routes at
  WCAG 2.2 AA level on every CI run. Pages audited include the 5 previously
  covered (home, audit, fix, convert, template) plus 12 new routes: Speech
  Studio, Braille Studio, Settings, Guidelines, User Guide, About, Changelog,
  FAQ, Rules Reference, Feedback, Privacy Policy, and Status. Additionally
  audits four interactive states: help accordions open, speech/braille
  unavailable banners, dark mode (`prefers-color-scheme: dark`), and mobile
  viewport (375 × 812 px). Critical and serious violations fail the CI build
  immediately with selector-level diagnostic output. Moderate and minor
  violations are surfaced as advisory warnings without blocking the build.
  Added `@axe-core/playwright ^4.11.2` to `web/package.json`. Added
  `test:axe` npm script that runs only the axe spec (separate from the
  functional regression suite). Expanded `@axe-core/cli` URL list in
  `accessibility-regression.yml` to match all 17 routes for the SARIF
  secondary scan. Axe results are written to `artifacts/axe-results.json` in
  the existing CLI format consumed by `axe_json_to_sarif.py`, so SARIF upload
  to GitHub Code Scanning is unchanged.

- **Server Status page (`/status`).** Added a human-readable diagnostics page
  that renders the same payload as `/health`, including service probes,
  readiness states, feature flag summary, full feature flag list, and raw
  JSON output for operators.

- **Braille navigation regression test.** Added
  `test_main_nav_shows_braille_tab_when_enabled` in `web/tests/test_braille.py`
  to ensure the Braille tab remains visible in top navigation when
  `GLOW_ENABLE_BRAILLE` is enabled.

- **Braille Studio** -- new `/braille/` tool for BANA-compliant text-to-braille and
  braille-to-text translation via [liblouis](https://liblouis.io/) (`louis` Python bindings).
  Supports all current BANA standards:
  - UEB Grade 1 and Grade 2 (Unified English Braille, BANA literary standard adopted 2016)
  - BANA Computer Braille Code (8-dot, `en-us-comp8.ctb`)
  - Legacy EBAE Grade 1 and Grade 2 (interoperability with pre-2016 materials)
  - Unicode Braille output (U+2800--U+28FF) and BRF ASCII output
  - BRF output is wrapped at the BANA-standard 40 cells per line (25 lines/page with
    optional paginated form-feed for embossers)
  - Graceful degradation when `louis` is not installed
  - Feature-gated via `GLOW_ENABLE_BRAILLE` (default: enabled)
  - Tab added to main navigation; download endpoint for `.brl`/`.brf`/`.txt` result files
  - 30 req/min rate limit on form and download endpoints

- **Speech Studio document preparation now uses Pandoc for uniform text rendering.**
  Uploaded documents (`.md`, `.rst`, `.docx`, `.pptx`, `.xlsx`, `.pdf`, `.epub`, etc.) are
  converted to normalized plain text via Pandoc before synthesis. `.txt` files
  are read directly; all other formats require Pandoc to be installed on the server.
  This guarantees consistent narration quality across every supported format.
  The error message returned when Pandoc is absent now explicitly names the missing
  dependency so administrators can resolve it quickly.

- **CI workflows now install Pandoc explicitly.** `deploy.yml`, `feature-flags-ci.yml`,
  and `accessibility-regression.yml` all run `apt-get install pandoc` before the
  web test suite so the full Speech Studio document prepare path is exercised in CI.

### Fixed

- **`/status` is now reachable without consent redirect.** Added `/status`
  to consent-gate exemptions so operational diagnostics are publicly
  accessible like `/health`.

- **`/status` now safely serializes mocked diagnostic values.** Health payload
  construction now coerces non-string Braille `louis_version` values to text
  before rendering JSON, preventing test/runtime failures when mocks return
  non-JSON-native objects.

- **Workflow install conflict for desktop editable install.** Aligned
  `desktop/pyproject.toml` and `desktop/requirements.txt` to
  `mammoth>=1.11.0,<1.12.0` so dependency resolution is compatible with
  `markitdown[docx,pdf,pptx,xlsx]>=0.1.5` in CI and deploy workflows.

- **Health now reports Speech and Braille readiness explicitly.** `/health`
  now includes `services.speech`, `services.braille`, and corresponding
  `readiness.speech` / `readiness.braille` entries alongside feature flag
  data so operational issues are visible without guessing.

- **Braille tab visibility now has explicit local flag defaults.** Added
  `GLOW_ENABLE_BRAILLE: true` to `instance/feature_flags.json` and
  `web/instance/feature_flags.json` so local runs do not rely on implicit
  default resolution for the Braille top-nav tab.

- **Server deploy image now ships working liblouis Python bindings.**
  `web/Dockerfile` installs `liblouis-bin`, `liblouis-dev`, `liblouis-data`,
  and `python3-louis` (the official Debian bindings) via apt, then copies the
  `louis` module into the pip Python 3.13 site-packages so `import louis`
  resolves at runtime. A build-time smoke-test (`python3 -c "import louis"`)
  fails the Docker build immediately if the binding is absent. The `pylouis`
  stub PyPI package (which installed no importable code) has been removed from
  `web/pyproject.toml` and `web/requirements.txt`.

- **New feature flags for speech and braille export/conversion.**
  Added `GLOW_ENABLE_EXPORT_SPEECH`, `GLOW_ENABLE_CONVERT_TO_SPEECH`,
  `GLOW_ENABLE_EXPORT_BRAILLE`, and `GLOW_ENABLE_CONVERT_TO_BRAILLE` (all
  default: enabled). Flags are wired into route-level guards: synthesis and
  document-prepare endpoints check `CONVERT_TO_*`; download endpoints check
  `EXPORT_*`. All four flags appear in the admin feature flags UI under the
  Exports and Convert subfeatures groups.

- **Speech Studio staged actions are now robustly hidden until preparation completes.**
  The post-prepare action group (`Preview first sentences`, `Download full document audio`)
  now uses both semantic `hidden`/`aria-hidden` attributes and JS state toggling, so those
  controls do not appear on first load even if style state is inconsistent. Preparation errors
  now auto-scroll into view so a failed `Next: Prepare text and estimate` action is immediately
  visible. Changes in `web/src/acb_large_print_web/templates/speech.html`,
  `web/src/acb_large_print_web/static/speech.js`, and
  `web/tests/test_speech_routes.py`.

- **`/changelog/` no longer crashes with a Jinja `TemplateSyntaxError`.**
  `scripts/build-doc-pages.py` now wraps all auto-generated partials in
  `{% raw %}...{% endraw %}` so changelog and guide entries that document Jinja
  syntax (e.g. `{{.Name}}`, `{% if %}`, `{{ }}`) are treated as plain text instead
  of live template directives.

- **`post_findings.json` no longer appears in the project root.** The post-fix findings
  file is now always written inside the session temp directory (`get_temp_dir(token)`)
  instead of `saved_path.parent`, which resolved to the working directory on some
  hosts.

- **`POST /audit/` returned `405 METHOD NOT ALLOWED`** instead of `400` for empty
  submissions because the `@audit_bp.route('/', methods=['POST'])` decorator was
  accidentally dropped from `audit_submit_rate_limited`. Restored.

---

- **8 workflow optimization improvements (v3.1.0 staging):**
  1. **Post-fix re-audit button** — `fix_result.html` now shows "Re-Audit Fixed Document" action, eliminating download-then-manual-reaudit friction.
  2. **Convert→Audit bridge** — Convert results now offer direct "Audit this file" form submission to `audit.audit_from_convert()`, skipping re-upload.
  3. **Prominent batch audit CTA** — Audit form redesigned with side-by-side callouts highlighting benefits of batch mode (compare formats, before/after, test variants).
  4. **Enhanced findings diff** — Auto-diff now shows detailed sections for "Newly Detected," "Still Present," and "Cleared" findings with explanatory text.
  5. **Session audit history** — Session maintains compact history of last 5 audits with score, grade, filename, timestamp, and share token; shown in audit form for quick restart.
  6. **Smart audit workflow** — Convert tool now features contextual next-step guidance (e.g., "Test variant formats together → batch audit").
  7. **Feedback loop prototype** — Shared audit reports now support optional reviewer comment collection (foundation for future iterations).
  8. **Session restore on expiry** — Expired upload sessions now offer history-based recovery ("Continue from previous audit" with one click).

- **15 product infrastructure improvements (v3.0.1 staging):**
  1. Toast notifications framework with progress indicators (keyboard + voice-accessible).
  2. `standards_profile` (acb_2025|aph_submission|combined_strict) propagation through audit→fix→reaudit workflow for consistent rule filtering.
  3. Ctrl+U keyboard shortcut to focus file picker anywhere on the page.
  4. Session keep-alive: `/health` ping every 15 minutes when forms are active (prevents idle timeout).
  5. Webhook callback support: POST audit results to user-supplied HTTPS URL with HMAC-SHA256 `X-GLOW-Signature` header.
  6. Share TTL configurable via `SHARE_TTL_HOURS` env var (default 4 hours); `get_share_ttl_hours()` helper exposed to templates.
  7. Session-based auto-diff: compare current audit vs. previous in same session for progress tracking (cleared/persistent/new).
  8. Large-file upload rate limit: 1/min for files >10 MB (separate from standard 6/min limit) — prevents abuse of slow audits.
  9. Voice preview endpoint: `/speech/voice-preview` POST for quick demo with default text (20/min rate limit).
  10. Audit history in session: maintains up to 5 recent audits with scores and share tokens.
  11. AI-powered alt-text suggestions: `POST /audit/suggest-alt-text` with token + image_index (requires ai_alt_text_enabled).
  12. CSV export of post-fix findings: `POST /fix/csv/<token>` downloads findings CSV from post_findings.json.
  13. EPUB Ace conformance level exposure: extract W3C conformance declaration and expose via `AuditResult.ace_conformance`.
  14. Form-level context injection: `audit_history` and `share_ttl_hours` now in all template contexts via app.py context_processor.
  15. All improvements are independent, tested, and backwards-compatible.

### Changed

- **Speech Studio flow now guides users in stages.** The document action now starts with an explicit `Next: Prepare text and estimate` step, then reveals preview/download actions only after preparation succeeds. This makes the process clearer and avoids appearing like action buttons do nothing before the document is prepared. Changes in `web/src/acb_large_print_web/templates/speech.html` and `web/src/acb_large_print_web/static/speech.js`.

- **Convert-to-Speech copy now states text-rendering behavior.** Convert page guidance for `Speech audio` now explicitly explains that Speech Studio renders the document to plain text first, then shows estimate details and preview/download controls. Changes in `web/src/acb_large_print_web/templates/convert_form.html`.

### Fixed

- **Speech Studio preparation now enforces Pandoc-first text rendering for document narration.** Non-plain-text inputs are rendered through a Pandoc plain-text stage before narration checks and conversion, and the rendered intermediate text is persisted for diagnostics (`speech_rendered.txt`) alongside normalized source text (`speech_source.txt`). Changes in `web/src/acb_large_print_web/routes/speech.py`.

- **Announcement page cleanup.** Removed stray rendered `>` paragraphs in the announcement body content that appeared between quote blocks. Changes in `web/src/acb_large_print_web/templates/partials/announcement_body.html`.

### Added

- **Speech route regression tests.** Added `web/tests/test_speech_routes.py` covering Speech page rendering of the staged `Next: Prepare text and estimate` action, Pandoc-required behavior, text extraction paths, and prepare-document persistence of rendered and normalized text artifacts.

---

## [3.0.0] - 2026-04-30

### Added

- **Speech Studio platform completed.** `/speech/` now supports typed synthesis, uploaded document-to-speech conversion, snippet preview, and full narration download.
- **Curated multi-voice Piper seeding during build and deploy.** Docker build-time model prefetch and `scripts/deploy-app.sh` now seed a curated English Piper set (US + GB accents) instead of only one default voice.
- **Admin Speech Studio voice management.** Added an admin page with one-click Piper voice pack install/remove actions and live install status.
- **Convert-to-Speech handoff.** Convert tab now includes a `Speech audio` direction that redirects to Speech Studio with token handoff and no re-upload.
- **Anthem download analytics.** Home page now includes a Let it GLOW theme download action with usage tracking.
- **Speech usage pattern analytics.** Speech interactions now track mode, voice, speed, and pitch for analytics.
- **Speech conversion telemetry datastore.** New `instance/speech_metrics.db` records document conversion runtime by word count and source size.
- **Adaptive duration estimation.** Speech timing estimates now blend baseline heuristics with historical real conversion telemetry from the same server infrastructure.

### Changed

- **Speech Demo rebranded to Speech Studio.** Updated UI labels and explanatory copy to present production-ready speech workflows.
- **Speech settings persistence.** Global browser preferences (`glow_user_settings`) now persist voice, text, speed, and pitch and auto-apply in Speech Studio.
- **Speech first-class navigation.** Added dedicated Speech tab and Quick Start Speech action routing.

### Fixed

- **Speech preview feedback for slower synthesis.** Added stronger live in-progress status messaging for longer preview waits.

---

## [2.8.0] - 2026-04-30

> A heartfelt thank you to the BITS community and the broader blind and low-vision community whose feedback, feature requests, and real-world testing made this release possible. Every feature in 2.8.0 came directly from your suggestions. We are building GLOW for you and with you -- your voice is in every line of this release.

### Added

- **Quick Start handoff: audit, fix, and convert without re-uploading.** The Quick Start landing page now uploads a document once and routes the user to Audit, Fix, or Convert with the file already loaded -- no second upload is required. `GET /audit/?token=...` and `GET /convert/?token=...` resolve the token to the existing session directory and render their forms with a "Ready to audit/convert: &lt;filename&gt;" notice in place of the file picker. The corresponding POST handlers honour a `prefill=1` flag to re-use the cached file rather than calling `validate_upload`. Fix already routed through `fix.fix_from_audit_form`; the Quick Start dispatcher in `routes/process.py` now sends `fix` requests there too. Implemented in `routes/audit.py` (`audit_form`, `_audit_single`), `routes/convert.py` (`convert_form`, `convert_submit`), `routes/process.py` (`process_go`), and templates `audit_form.html` and `convert_form.html`. New tests in `tests/test_v270_new_routes.py::TestQuickStartHandoff`.


---

## [2.7.0] - 2026-04-29



### Added

- **GLOW Anthem:** Embedded the "Let it GLOW" cinematic ballad on the home page with an accessible audio player and integrated lyrics.

- **User-selectable dark mode (Light / Dark / Auto).** GLOW now offers an explicit theme choice instead of only following the operating system. The preference is stored in `localStorage` under `glow_theme` (values `light`, `dark`, `auto`; default `auto`). An inline boot script in `<head>` resolves the preference and writes `data-theme="dark"` or `data-theme="light"` on `<html>` before first paint, eliminating the flash-of-wrong-theme on reload. The CSS dark block was rewritten to key off `html[data-theme="dark"]` instead of `@media (prefers-color-scheme: dark)`, so `auto` mode now responds dynamically when the OS preference changes. New controls: a theme selector dropdown in the footer (always visible) and a radio group at the top of the Settings page; both stay in sync via the `data-theme-control` attribute. A `<meta name="color-scheme" content="light dark">` tag tells the browser to render native widgets (scrollbars, form controls) in the matching scheme. New file `static/theme.js`; changes in `static/forms.css`, `templates/base.html`, and `templates/settings.html`.

- **Centered page layout on wide viewports.** The body of every page is now horizontally centered with a wider max-width (`min(82rem, 100%)`) and responsive horizontal padding (`clamp(1rem, 3vw, 2.5rem)`) instead of being pinned flush left in a 70ch column. Long-prose paragraphs and lists that are direct children of `<main>` are still constrained to a 70ch reading measure, while cards, tables, and form layouts use the full width. Changes in `static/acb-large-print.css`.

- **Reliable focus indicators across all form controls.** All interactive elements (links, buttons, inputs, selects, textareas, checkboxes, radios, summary, `[tabindex]`) now render a 3px solid blue outline plus a layered white-and-blue halo (`box-shadow`) on `:focus-visible`. Native checkboxes and radios -- which previously lost their outlines on some browsers/themes -- now get an explicit ring with offset and a dashed outline on the wrapping `<label>` (via `:has()`) so the control text is also visually located. A `forced-colors` block defers to the system `Highlight` colour for Windows High Contrast users, and a dark-mode block swaps the white halo for a dark halo so the indicator stays visible against dark backgrounds. Changes in `static/forms.css`.

### Changed

- **Guidelines and Settings moved out of the main ribbon.** The top navigation now focuses on document tools (Quick Start, Template, Audit, Fix, Convert, Whisperer). Guidelines and Settings have moved into the footer "Additional links" navigation, which already housed User Guide, FAQ, About, PRD, Changelog, Feedback, Admin Sign-In, Privacy Policy, and Terms of Use. Both are also called out as cards on the Quick Start page so new users can find them. Changes in `templates/base.html` and `templates/process_form.html`.

- **Streamlined Audit → Fix (no re-upload).** Two new routes enable users to go from an audit report directly to Fix without re-uploading the document. `GET /fix/from-audit/<token>` renders the Fix form with the session file pre-loaded and a notice showing the filename; `POST /fix/from-audit/<token>` runs the full fix pipeline -- including the heading-review confirmation flow -- on the existing session file. The "Fix This Document" and "Fix These Auto-Fixable Issues" buttons on the audit report now route to these token-based URLs when a session is active; they fall back to the standard `/fix/` form otherwise. A new `_find_fixable_file(temp_dir)` helper resolves the first supported file in the temp directory. When an expired token is followed, the user is redirected to the standard fix form with `?notice=session_expired`. Changes in `routes/fix.py` and `templates/fix_form.html`.

- **Streamlined Fix → Re-Audit (no re-upload).** A new `POST /audit/from-fix` route re-audits the fixed file from an existing session without requiring a second upload. The route accepts `token` and `download_name` form fields, resolves the fixed file using `werkzeug.utils.secure_filename` with a path-traversal check and fallback to any `-fixed` file, runs the audit inline, generates a share token, and renders `audit_report.html` with full report context. The "Re-Audit Now" button on the fix result page has been replaced with a `<form>` POST to this route (guarded by `{% if feature_audit_enabled %}`), passing the session token and download name. Changes in `routes/audit.py` and `templates/fix_result.html`.

- **Privacy policy: audit session retention and share token wording.** The Data Storage and Retention Policy (`templates/privacy.html`) has been updated to accurately reflect the new session model: uploaded files are retained for up to 1 hour to enable the Fix shortcut and Chat follow-on actions; shareable report links contain only rendered HTML (never the original document) and expire after 1 hour. The "No permanent storage" section clarifies that the report cache holds rendered HTML only. Last updated date changed to April 29, 2026.

- **Privacy policy: analytics disclosure expanded.** The Data Storage and Retention Policy now explicitly documents operational analytics collection: aggregate visitor counter (unique browser sessions), per-tool usage counters (Audit, Fix, Convert, Template Builder, BITS Whisperer, Document Chat), and per-tool last-used timestamps. The page now also states where these metrics are stored (`instance/visitor_counter.db`, `instance/tool_usage.db`), what they are used for (internal reporting and capacity planning), and what they exclude (document content, extracted text, prompts, transcripts, and fixed output). Change in `web/src/acb_large_print_web/templates/privacy.html`.

- **Feature flag docs: `GLOW_ENABLE_EXPORT_HTML` description updated.** `docs/feature-flags.md` updated to document that this flag now gates the CMS Fragment direction in Convert (rather than a standalone Export route), and that the legacy `/export` redirect to Convert is unaffected by the flag.

- **Export folded into Convert.** The Export tab has been removed from the main navigation. Its CMS Fragment functionality is now a dedicated direction within the Convert page (`/convert/`). Users who visit `/export` (bookmarks, cached links) are permanently redirected (301) to `/convert`. The Quick Start "CMS Fragment" action for `.docx` files now routes directly to Convert. The CMS Fragment option in Convert is gated by the existing `GLOW_ENABLE_EXPORT_HTML` feature flag, calls the same `export_cms_fragment()` function, and produces an identical `-cms.html` download. Changes in `routes/convert.py`, `routes/export.py`, `routes/process.py`, `templates/base.html`, `templates/convert_form.html`, `templates/index.html`, and `templates/process_form.html`.

- **Convert: CMS Fragment direction.** Added a new `to-html-cms` direction to Convert that accepts Word (`.docx`) files and produces a scoped ACB-styled HTML snippet ready to paste into WordPress or Drupal without conflicting with the site theme. Visible in Step 2 only for `.docx` files. Changes in `routes/convert.py` and `templates/convert_form.html`.

- **Audit report: grade letter headline.** The compliance grade letter (A–F) is now displayed as a large typographic element at the top of the audit report, making the outcome immediately visible before reading the score or findings. The score (NN/100) and finding count appear beside the grade letter as supporting detail. Changes in `templates/audit_report.html` and `static/forms.css`.

- **After-action next-step cards.** The "What's Next?" section on both the audit report and fix result pages now displays a prominent action card (`.next-step-callout`) for the primary recommended workflow:
  - **Audit report:** a "Fix This Document" card with a "Audit Another" secondary button replaces the bare link for `.docx` files with findings and an enabled Fix feature.
  - **Fix result:** a "Re-Audit Now" card with a "Fix Another Document" secondary button immediately follows the What's Next heading, making the Audit → Fix → Re-Audit loop explicit and actionable.
  Changes in `templates/audit_report.html`, `templates/fix_result.html`, and `static/forms.css`.

- **Drag-and-drop file upload zones.** All file upload forms now include a visual drag-and-drop zone adjacent to the file input. Dragging a file onto the zone assigns it to the input, updates the hint text, and fires a `change` event so other scripts (such as the Convert extension filter) react correctly. The original `<input type="file">` remains accessible and unchanged for keyboard and screen-reader users. Implemented in a new `static/dropzone.js` module included from `templates/base.html`. Styles added to `static/forms.css`.

- **Navigation: Quick Start tab.** The Quick Start upload-and-discover flow (`/process/`) is now accessible from a permanent tab in the main navigation bar, appearing as the first tab on every page. Previously it was only reachable from a button on the home page. The tab is always shown regardless of feature flags. Changes in `templates/base.html`.

- **Navigation: Template tab moved before Audit.** The Template tab now appears immediately after Quick Start, before Audit and Fix, reflecting a start-of-workflow position for new document creation. Changes in `templates/base.html`.

- **Two-stage chained conversion for PowerPoint, Excel, PDF, and more.** The Convert page (`/convert/`) now accepts `.pptx`, `.xlsx`, `.xls`, `.pdf`, `.csv`, `.html`, `.htm`, `.json`, and `.xml` files as input for all Pandoc output directions (HTML, Word, EPUB, PDF). Files are first extracted to Markdown via MarkItDown, then Pandoc applies full ACB Large Print formatting. This is fully transparent -- users simply upload their file and choose the output format. Changes in `web/src/acb_large_print_web/routes/convert.py` and `templates/convert_form.html`.
  - Defined `_CHAIN_VIA_MARKDOWN` frozenset for the chained extension set.
  - Defined `_PANDOC_EFFECTIVE_EXTENSIONS` = `PANDOC_INPUT_EXTENSIONS | _CHAIN_VIA_MARKDOWN` used for validation and UI.
  - All four Pandoc directions (`to-html`, `to-docx`, `to-epub`, `to-pdf`) now perform a MarkItDown stage 1 when the extension is in `_CHAIN_VIA_MARKDOWN`, then pass the intermediate `.md` to Pandoc.

- **Convert page: Upload first (step reorder).** Step 1 is now "Upload your file" so the JavaScript can inspect the extension before the user picks an output format. The previous step order was: choose output → formatting → title → upload. The new order is: upload → choose output → formatting → title. Changes in `templates/convert_form.html`.

- **Convert page: JavaScript extension-aware output filtering.** After a file is selected in Step 1, JavaScript reads the file extension and enables only the conversion directions that support that file type. Unavailable options are disabled in place with a visual indicator. A live-region hint message names the available formats and notes when two-stage chaining applies. The extension sets are serialized from Flask template context variables (`pandoc_effective_exts`, `markitdown_exts`, `pipeline_exts`, `chain_via_markdown_exts`) and injected as `Set` objects so no server round-trip is needed. Changes in `templates/convert_form.html`.

- **Convert: Result page with inline preview.** HTML and CMS Fragment conversion now redirects to a dedicated result page (`templates/convert_result.html`) instead of immediately downloading the file. The result page shows a Download button, and for HTML output, an inline iframe preview of the converted document. New `GET /convert/download/<token>/<filename>` and `GET /convert/preview/<token>/<filename>` routes serve the file without exposing the temp directory path. Changes in `routes/convert.py` and new template `templates/convert_result.html`.

- **Convert: CMS Fragment clipboard copy.** The Convert result page for the CMS Fragment direction includes a read-only `<textarea>` showing the full HTML snippet and a "Copy to Clipboard" button. Changes in `templates/convert_result.html`, `static/forms.css`, and new `static/toast.js`.

- **Audit report: Quick wins filter.** A "Show Quick Wins Only" toggle button appears above the findings table when at least one finding is auto-fixable. Clicking it hides all non-auto-fixable rows and shows a count of auto-fixable findings. The toggle is ARIA-pressed compliant and includes a live-region status element. The set of auto-fixable rule IDs (`FIXABLE_RULE_IDS`) is defined in `routes/audit.py` and passed to the template as `fixable_rule_ids`. Changes in `routes/audit.py` and `templates/audit_report.html`.

- **Audit report: Shareable report URL.** After a successful audit, the rendered report HTML is cached server-side for 1 hour in a new `report_cache.py` module (`web/src/acb_large_print_web/report_cache.py`). A shareable URL (`GET /audit/share/<share_token>`) is displayed in a collapsible "Share this report" section at the bottom of the report. The share token is a separate UUID from the upload token — the original document is never accessible via the share link. Changes in `routes/audit.py`, new `report_cache.py`, and `templates/audit_report.html`.

- **Fix result: Grade letter on After score box.** The After score box on the fix result page now displays a large typographic grade letter (matching the audit report style), making the improvement immediately visible. Changes in `templates/fix_result.html` and `static/forms.css`.

- **Toast notification system.** A lightweight global toast notification module (`static/toast.js`) is included from `base.html`. It exposes `window.GLOW.toast(message, type)` for programmatic toasts and wires a global `click` handler for `[data-copy-target]` buttons that copies the target input's value to the clipboard and shows a "Copied!" toast. Changes in `templates/base.html`, new `static/toast.js`, and `static/forms.css`.

- **Dark mode CSS.** The dark theme rules in `static/forms.css` cover body, navigation, cards, buttons, tables, badges, score grades, footer, forms, file-input zones, dropzone, and details/summary elements. As of the v2.7.0 user-selectable toggle (above), they key off `html[data-theme="dark"]` rather than `@media (prefers-color-scheme: dark)`, so the user's explicit Light/Dark/Auto choice always wins and Auto mode still tracks the OS via `matchMedia`.

- **Print CSS improvements.** An additional `@media print` block in `static/forms.css` hides the quick wins bar, share section, toast container, CMS copy bar, and convert preview iframe when printing, and adds page-break rules for the findings table.

- **Responsive mobile layout improvements.** New responsive rules in `static/forms.css` adjust form layouts, navigation, action bars, and score boxes for narrow viewports.

- **Streamlined Convert → Audit handoff (no re-upload).** A new `POST /audit/from-convert` route audits the converted file from an existing Convert session without a second upload. The `convert_result.html` page now shows an "Audit This Document" call-to-action card for HTML, Word, and EPUB outputs (i.e. formats GLOW's auditors support), guarded by `feature_audit_enabled`. The route resolves the converted file using `secure_filename` with a path-traversal check, runs the audit inline, generates a share token, and renders `audit_report.html`. On expired or missing session the user is redirected to the standard upload form with a friendly notice. Changes in `routes/audit.py` and `templates/convert_result.html`.

- **Audit report: download as PDF.** A new `GET /audit/share/<share_token>/pdf` route renders the cached share-report HTML to PDF via WeasyPrint, caches the result in the share directory for the session lifetime, and serves it as `application/pdf`. The audit report's "Share this report" section now exposes a "Download PDF" button alongside the share URL. When WeasyPrint is not installed the route returns 503 and the button degrades gracefully. Changes in `routes/audit.py`, new helpers `report_cache.save_pdf()` / `load_pdf()` / `report_cache.save_findings_data()` / `load_findings_data()`, and `templates/audit_report.html`.

- **Audit report: download findings as CSV.** A new `GET /audit/share/<share_token>/csv` route returns the audit findings as a UTF-8 BOM CSV with a header preamble (filename, format, score, grade, profile, mode) followed by the standard column row. The CSV is generated from cached findings JSON written alongside the report HTML at audit time. The "Share this report" section now exposes a "Download CSV" button that pairs with the existing email-CSV-attachment delivery. New module `web/src/acb_large_print_web/csv_export.py` extracted from the email path; new helpers `report_cache.save_findings_data()` / `load_findings_data()`. Changes in `routes/audit.py`, new `csv_export.py`, and `templates/audit_report.html`.

- **SQLite visitor counter.** A new `visitor_counter.py` module tracks unique browser sessions using a single-row SQLite counter (`instance/visitor_counter.db`, WAL mode). One increment fires per session via a `@app.before_request` hook; static assets and the `/health` endpoint are excluded. The current count is injected into every template as `visitor_count` via the `inject_rules()` context processor and displayed in the footer as "Visitors: 1,234". New file `web/src/acb_large_print_web/visitor_counter.py`; changes in `app.py` and `templates/base.html`.

- **Tool usage analytics.** A new `tool_usage.py` module maintains per-tool use counts in a SQLite database (`instance/tool_usage.db`, WAL mode). Each of the six public tool endpoints (Audit, Fix, Convert, Template Builder, BITS Whisperer, Document Chat) records a count increment as the first operation inside its submit handler; failures are swallowed silently so a DB error never surfaces to the user. Counts and a "last used" timestamp are exposed via `get_all()` and `get_total()`. New file `web/src/acb_large_print_web/tool_usage.py`; changes in `routes/audit.py`, `routes/fix.py`, `routes/convert.py`, `routes/template.py`, `routes/whisperer.py`, and `routes/chat.py`.

- **Admin analytics dashboard.** A new `GET /admin/analytics` route (admin-only) renders a summary of tool usage counts per tool (with share percentages and last-used timestamps) alongside the total visitor count. Accessible from a new "Tool usage analytics" link in the Admin Queue dashboard. New template `templates/admin_analytics.html`. Changes in `routes/admin.py` and `templates/admin_queue.html`.

- **About page: Usage Statistics section.** The About page (`/about/`) now includes a "Usage Statistics" section showing total visitor count, total tool uses, and a table of per-tool counts (rows with zero uses are hidden). The `about_page` route now imports and passes `tool_usage`, `total_uses`, and `visitor_count` to the template. Changes in `routes/about.py` and `templates/about.html`.

- **Re-audit: before/after diff banner.** When an audit is re-run via `POST /audit/from-fix`, the report now displays a diff banner above the score showing the score delta (e.g. "+12 points"), grade change, fixed/persistent/new finding counts, and the rule IDs that were fixed since the previous audit. Implemented via a new `_compute_audit_diff()` helper in `routes/audit.py` that consumes `prev_score` and `prev_rule_ids` form fields posted from the fix result page, and a new `audit_diff` block in `templates/audit_report.html`. The fix result form now propagates `prev_score` and a comma-joined list of rule IDs from the original audit.

- **Audit report: inline rule explanations.** Each rule ID in the findings table is now wrapped in a `<details>` disclosure that shows the canonical rule description, ACB reference, and "Why this matters" rationale pulled from `rule_reference_metadata.py`. The disclosure is keyboard-operable, opens in place without triggering a layout shift, and is hidden when printed. Auto-fixable rules show a "Auto-fixable" badge inside the disclosure. Changes in `templates/audit_report.html` and `static/forms.css`. A new `_rules_by_id()` helper in `routes/audit.py` builds the lookup table at request time.

- **Roadmap page.** Added `GET /roadmap` route and `templates/roadmap.html`, linked from the footer alongside Privacy and Changelog. The page lists shipped highlights, in-progress work, and longer-term ideas so contributors and adopters can see where GLOW is heading. Content lives entirely in the template -- no backend data layer.

- **Global keyboard focus indicators.** Added a global `:focus-visible` ring (3px solid `--color-primary` with 2px offset) in `static/forms.css` that applies to all focusable elements, paired with `:focus:not(:focus-visible) { outline: none }` so mouse clicks no longer leave a focus ring on buttons. Browsers without `:focus-visible` support fall back to the default browser ring. The ring also respects dark mode via the existing primary color variable.

- **Consent modal: scrollable body and improved focus management.** The "Cloud AI Consent" modal in the chat panel now wraps its long policy text in a scrollable `.consent-modal-scroll` region with a max-height of 60vh, ensuring the Decline/Accept buttons remain visible on small viewports. The modal also traps focus while open, restores focus to the trigger when closed, and respects the `prefers-reduced-motion` media query (skipping the fade-in animation). Changes in `templates/chat_panel.html` and `static/forms.css`.

- **Reduced motion support.** All custom animations (toast slide-in, dropzone hover transition, consent modal fade) now check `@media (prefers-reduced-motion: reduce)` and disable transition/animation when the user has requested reduced motion. Changes in `static/forms.css` and `static/toast.js`.

- **Tests: 22 new unit tests for v2.7.0 routes.** New `web/tests/test_v270_new_routes.py` exercises `report_cache.save_findings_data()` / `load_findings_data()` / `save_pdf()` / `load_pdf()` (roundtrip, bad token, missing share dir, TTL expiry), `csv_export.findings_to_csv_bytes()` (BOM, preamble, columns, empty-list, filename safety), the new share-report CSV and PDF routes (cached path, 404 on unknown token, 503 when WeasyPrint missing), and the `audit_from_convert` error paths (expired/missing token). Also includes a CSS guard test that fails if any shipped stylesheet introduces an `outline: none / 0 / transparent` rule outside the allowed `:focus:not(:focus-visible)` recipe, protecting the new global focus ring from future regressions.

### Fixed

- **Production deploy now forces Caddy to apply config changes and validates from a disposable container.** Updated `scripts/deploy-app.sh` to validate `web/Caddyfile` without depending on a running `caddy` container, then force-recreate the proxy so bind-mounted config changes actually reach production. Updated `scripts/post-deploy-check.sh` to verify that the live MP3 response includes `media-src 'self'` in the Content Security Policy so stale proxy config is caught during deployment instead of after release.

- **Web changelog page no longer crashes under Jinja parsing.** `web/src/acb_large_print_web/templates/partials/changelog_body.html` is now wrapped in a Jinja `{% raw %}...{% endraw %}` block so literal documentation examples like `{{.Name}}`, `{% if %}`, and `{{ }}` are treated as text instead of template syntax. This resolves `/changelog/` HTTP 500 errors and unblocks the Playwright static reference page regression test in Accessibility Regression Gate.

- **Home page accessibility test updated for renamed navigation section heading.** `web/tests/test_app.py` now asserts `Main Navigation Tab Order and Purpose` (replacing `What Each Tab Does`) and renames the test method to match the updated UI copy, resolving Deploy/Feature Flags CI failures caused by stale expectation text.

- **Streamlined flow: session context preserved on fix error.** When a fix attempt initiated from an audit report (`POST /fix/from-audit/<token>`) encounters an error, the fix form now re-renders with the original session token and filename intact. Previously the form re-rendered as a generic upload form, losing the user's context and requiring a fresh upload. Change in `routes/fix.py`.

- **Streamlined flow: prefill notice button label.** The notice shown when the Fix form pre-loads a session file incorrectly referred to the submit action as "Run Fix." The actual button label is "Fix Document." Label corrected in `templates/fix_form.html`.

- **Home page Settings card: Personalization chip is now clickable.** On the main page, the "Personalization" format tag in the Settings card now links to the Settings page route (`settings.settings_page`) instead of rendering as plain text. Change in `web/src/acb_large_print_web/templates/index.html`.

## [2.6.0] - 2026-04-28

### Added

- **Web Rules Reference deep-dive page.** Added a new `/rules/` route in `web/src/acb_large_print_web/routes/rules_ref.py` with a dedicated `rules_ref.html` template and `rule_reference_metadata.py` data module. The page provides a searchable, filterable browser for all audit rules with severity badges, profile membership, help links, extended rationale, suppression guidance, and deep-linkable rule anchors from the main web navigation.

- **Community inspiration and attribution: Jamal Mazrui's accessibility tooling leadership.** Added release-level attribution recognizing [Jamal Mazrui](https://github.com/jamalmazrui) and the influence of [extCheck](https://github.com/jamalmazrui/extCheck) and [xlHeaders](https://github.com/jamalmazrui/xlHeaders) on this release's expanded rule coverage and remediation tooling.

- **PowerPoint timing and motion safety checks.** Added four new PPTX rules in `desktop/src/acb_large_print/constants.py` and implemented detection in `desktop/src/acb_large_print/pptx_auditor.py`:
  - `PPTX-FAST-AUTO-ADVANCE`
  - `PPTX-REPEATING-ANIMATION`
  - `PPTX-RAPID-AUTO-ANIMATION`
  - `PPTX-FAST-TRANSITION`

- **Expanded Markdown accessibility quality checks.** Added 20 Markdown-focused rules and corresponding auditor logic in `desktop/src/acb_large_print/md_auditor.py`, including alt text quality checks, YAML/front-matter validation, heading and code-block quality checks, raw HTML checks, table consistency checks, fake-list checks, and ALL CAPS detection.

- **Deeper YAML front matter validation -- three new sub-rules.** `desktop/src/acb_large_print/md_auditor.py` and `constants.py` now enforce three additional YAML front matter checks applied whenever a front matter block is present:
  - `MD-YAML-UNCLOSED-FENCE` (High) -- opening `---` has no closing `---` fence; metadata cannot be parsed
  - `MD-YAML-MISSING-TITLE` (Medium) -- front matter block lacks a `title:` field (WCAG 2.4.2)
  - `MD-YAML-MISSING-LANG` (High) -- front matter block lacks a `lang:` or `language:` field (WCAG 3.1.1)
  The existing `MD-NO-YAML-FRONT-MATTER` check is suppressed when any deeper check fires (no redundant reports). `office-addin/src/constants.ts` and `web/src/acb_large_print_web/rules.py` are both updated with the new rules.

- **Web app help-text coverage for all 2.6.0 Markdown rules.** `web/src/acb_large_print_web/rules.py` was missing help links for all 16 Markdown rules added in this release. Added link entries (CommonMark spec, WebAIM, WCAG Understanding docs, ACB guidelines) for every new rule: `MD-ALT-TEXT-FILENAME`, `MD-ALT-TEXT-REDUNDANT-PREFIX`, `MD-ALT-TEXT-TOO-SHORT`, `MD-NO-YAML-FRONT-MATTER`, `MD-YAML-UNCLOSED-FENCE`, `MD-YAML-MISSING-TITLE`, `MD-YAML-MISSING-LANG`, `MD-EMPTY-HEADING`, `MD-HEADING-TOO-LONG`, `MD-HEADING-ENDS-PUNCTUATION`, `MD-CODE-BLOCK-NO-LANGUAGE`, `MD-INDENTED-CODE-BLOCK`, `MD-RAW-HTML-TABLE`, `MD-MOVING-CONTENT`, `MD-BLANK-TABLE-HEADER`, `MD-TABLE-COLUMN-MISMATCH`, `MD-FAKE-LIST-BULLET`, `MD-FAKE-NUMBERED-LIST`, `MD-ALLCAPS`.

- **Markdown parity sweep: 14 additional extCheck-aligned rules.** Added the remaining Markdown parity checks identified from extCheck into `desktop/src/acb_large_print/md_auditor.py` with synchronized rule metadata in `desktop/src/acb_large_print/constants.py`, `office-addin/src/constants.ts`, and help-link coverage in `web/src/acb_large_print_web/rules.py`: `MD-EMPTY-LINK-TEXT`, `MD-URL-AS-LINK-TEXT`, `MD-NO-HEADINGS`, `MD-DUPLICATE-HEADING-TEXT`, `MD-LONG-SECTION-WITHOUT-HEADING`, `MD-YAML-MISSING-AUTHOR`, `MD-YAML-MISSING-DESCRIPTION`, `MD-EXCESSIVE-BLANK-LINES`, `MD-EXCESSIVE-TRAILING-SPACES`, `MD-RAW-BR-TAG`, `MD-RAW-HTML-GENERIC-CONTAINER`, `MD-RAW-HTML-PRESENTATIONAL`, `MD-FAKE-INLINE-BULLET`, and `MD-ENTIRE-LINE-BOLDED`.

- **Excel layout and naming checks.** Added two new XLSX rules in `desktop/src/acb_large_print/constants.py` and implemented in `desktop/src/acb_large_print/xlsx_auditor.py`:
  - `XLSX-BLANK-ROWS-LAYOUT`
  - `XLSX-DEFAULT-TABLE-NAME`

- **New Excel fixer capability inspired by xlHeaders.** Added `desktop/src/acb_large_print/xlsx_fixer.py` with `add_excel_header_named_ranges()`, which creates xlHeaders-style named ranges (`ColumnTitleNN`, `RowTitleNN`, `Title01`) to improve screen reader header context in Excel workbooks.

- **Office add-in rule registry sync for 2.6.0 coverage.** Updated `office-addin/src/constants.ts` with the new PPTX and XLSX rules, plus Markdown rule identifiers and `DocFormat.MD` support to keep shared rule metadata aligned across implementations.

### Changed

- **Web Rules Reference accessibility polish.** `web/src/acb_large_print_web/templates/rules_ref.html` now exposes each rule as a navigable heading for screen-reader heading lists, moves keyboard focus to deep-linked rules when loading `#rule-*` anchors, and debounces search-driven live-region updates to reduce announcement noise.

- **Web settings and per-rule customization now use local storage instead of preference cookies.** `web/src/acb_large_print_web/static/preferences.js`, `web/src/acb_large_print_web/templates/settings.html`, `web/src/acb_large_print_web/templates/rules_ref.html`, `web/src/acb_large_print_web/templates/privacy.html`, and `web/src/acb_large_print_web/templates/consent.html` now explain and use browser local storage for saved workflow defaults, saved custom Audit/Fix rule sets, and Rules Reference filter state. The consent cookie (`glow_consent_v1`) remains separate and unchanged.

- **Rules Reference can now edit saved custom rule sets for Audit and Fix.** `web/src/acb_large_print_web/templates/rules_ref.html` and `web/src/acb_large_print_web/routes/rules_ref.py` now support target-aware rule-set editing with per-rule checkboxes, visible-only bulk actions, saved selection counts, and direct links from Settings into Audit or Fix custom-rule editing.

- **Excel default table-name findings now use a dedicated rule ID.** `desktop/src/acb_large_print/xlsx_auditor.py` now emits default Excel table-name findings under `XLSX-DEFAULT-TABLE-NAME` instead of reusing `XLSX-TABLE-HEADERS`, improving severity targeting and reporting clarity.

- **Website About page now includes 2.6.0 attribution details.** Updated `web/src/acb_large_print_web/templates/about.html` with a dedicated acknowledgment of Jamal Mazrui and explicit references to extCheck and xlHeaders as inspirations for this release.

## [2.5.0] - 2026-04-28

### Added

- **New feature flag: `GLOW_ENABLE_HEADING_DETECTION` (default `True`).** Added to `feature_flags.py` `_DEFAULTS` and injected as `feature_heading_detection_enabled` in the global template context via `app.py`. Controls visibility of heading detection settings in the Settings tab and can be used to gate the Fix route's heading detection controls in future.

- **Settings tab: feature-flag-gated settings.** `settings.html` now conditionally renders settings based on active feature flags. The "Enable heading detection" checkbox and its confidence threshold and accuracy mode controls are hidden when `GLOW_ENABLE_HEADING_DETECTION` is off. The "Enable AI refinement" checkbox remains hidden when `GLOW_ENABLE_AI_HEADING_FIX` is off (existing gate). Convert Defaults direction radios (`to-markdown`, `to-html`, `to-docx`, `to-epub`, `to-pdf`, `to-pipeline`) are each individually gated behind their corresponding `feature_convert_to_*_enabled` flags, matching the gating already applied in `convert_form.html`.

- **Settings tab: convert direction default selection now respects feature flags.** In `settings.html`, Convert Defaults now selects the first enabled direction radio using a Jinja namespace guard instead of hard-coding `to-markdown` as checked. This prevents blank or invalid defaults when `GLOW_ENABLE_CONVERT_TO_MARKDOWN` is disabled.

- **Desktop PDF audit: smarter image-based PDF detection with DPI quality check.** `desktop/src/acb_large_print/pdf_auditor.py` now uses image coverage area (requires ≥40% of page area) to avoid false positives from pages with small decorative images. The `PDF-NO-IMAGES-OF-TEXT` finding now classifies documents as entirely scanned, majority-scanned (≥50%), or partially scanned and includes page percentage and OCR remediation guidance (Adobe Acrobat, Tesseract, ABBYY FineReader). A new `PDF-IMAGE-RESOLUTION` check (`desktop/src/acb_large_print/constants.py`) flags scanned pages where image resolution is below 150 DPI — the minimum for acceptable OCR results — with per-page DPI values and a recommendation to re-scan at 300 DPI or higher.

- **Docs quality: Vale prose linting profile + CI workflow.** Added a low-noise prose quality gate for documentation with repository rules and vocabulary files (`.vale.ini`, `.vale/styles/Glow/*`, `.vale/config/vocabularies/Glow/*`) and a dedicated workflow (`.github/workflows/docs-quality.yml`) that lints `docs/**/*.md` and `README.md`. Initial rules focus on plain-language clarity, ambiguous link text, and long-sentence readability warnings.

- **EPUB auditing: optional EPUBCheck integration for authoritative package validation.** `desktop/src/acb_large_print/epub_auditor.py` now runs EPUBCheck (when available) and maps parsed `ERROR(...)` / `WARNING(...)` output into audit findings (`EPUBCHECK-ERROR`, `EPUBCHECK-WARNING`) with safe caps to keep reports readable. Validation is controlled via `GLOW_ENABLE_EPUBCHECK` (default enabled) and gracefully skips when EPUBCheck is unavailable.
- **CI: accessibility regression gate with Playwright + axe + SARIF.** Added `.github/workflows/accessibility-regression.yml` to run web Playwright regression tests and an axe-core WCAG 2.2 AA scan against key routes, then upload SARIF results for code scanning visibility.

- **Ops: WSL pre-production Docker staging helper.** Added `scripts/wsl-stage-regression.ps1` plus `web/docker-compose.wsl.yml` so GLOW can be staged in a WSL distro, health-checked, and regression-tested from the workstation before deploying to the main server. The WSL staging override defaults AI feature flags off to mirror the current non-AI rollout plan.

- **Web: Chat response quality improvements -- 7 new tools and grounding enhancements.** `web/src/acb_large_print_web/chat_handler.py` adds four new tools to the Document agent category: `get_document_summary` (plain-language document type, title, and section overview), `get_section_content` (full paragraph text of a named section, replacing the existence-only `find_section`), `get_decisions_and_actions` (extracts voted motions and action item owners from meeting/board documents), and `get_what_passes` (surfaces what the document already does correctly for balanced responses). `get_all_tools()` and the `call()` dispatcher are updated for all four. `routes/chat.py` now injects a document orientation block (summary + compliance score + what passes) on the first turn of every chat session so the model always opens with a grounded overview. The system prompt adds a confidence guard (rule 8) instructing the model not to report violations unless a pre-flight tool explicitly detected them, and a balance rule (rule 9) requiring acknowledgment of passing checks alongside violations.
- **Web: Table question dispatch now uses `extract_table` instead of `estimate_reading_order`.** Keywords "table", "column", "row", "data" in `dispatch_for_question()` now call `extract_table("0")` as the primary tool, falling back to `estimate_reading_order` only when no tables are found. Previously table questions were incorrectly routed to the reading-order tool.
- **Web: New `get_section_content` dispatcher route.** Questions matching patterns like "what does X say", "tell me about X", or "content of X" now trigger `get_section_content` in the keyword dispatcher, returning actual paragraph text rather than just confirming section existence.
- **Web: New `get_decisions_and_actions` and `get_what_passes` dispatcher routes.** Questions about votes, motions, approvals, and action items route to `get_decisions_and_actions`. Questions asking what passes, what's correct, or what's compliant route to `get_what_passes`.
- **Tests: Probe paths 24b–24f (Layer 2) for new document tools.** `tests/openrouter-probe/run_chat_paths_app.py` and `_write_probe.py` add unit-level coverage for `get_document_summary`, `get_section_content` (found/not-found), `get_decisions_and_actions`, and `get_what_passes` in Layer 2.
- **Tests: Probe paths 70b–70d (Layer 7) for new pipeline behaviors.** End-to-end pipeline paths added for document-summary questions, financial-section content retrieval, and board vote/decision extraction.

- **Docs: Cloud AI implementation plan consolidated into core documentation.** Merged the standalone cloud transition and implementation backlog content into `docs/prd.md` and `docs/deployment.md`, including the adopted OpenRouter production roadmap, provider-privacy strategy, environment wiring, and admin bootstrap guidance.
- **Web: Privacy-aware OpenRouter routing foundation.** `web/src/acb_large_print_web/ai_gateway.py` now supports comma-separated model fallback lists and sends OpenRouter provider preferences for privacy-sensitive routing (`dataCollection: deny`, `zdr: true`, fallbacks enabled, latency sort).
- **Web: Secure local admin bootstrap path.** Added `web/src/acb_large_print_web/credentials.py` for environment-first secret loading with optional local `server.credentials` fallback for development, plus password-based bootstrap admin login support in `web/src/acb_large_print_web/routes/admin.py` and `admin_login.html`.
- **Web: AI queue/backpressure controls for large workloads.** `web/src/acb_large_print_web/gating.py` now supports bounded queue waits and queued-capacity telemetry for AI, vision, and audio gates via `GLOW_AI_QUEUE_WAIT_SECONDS`, `GLOW_VISION_QUEUE_WAIT_SECONDS`, and `GLOW_AUDIO_QUEUE_WAIT_SECONDS`.
- **Web: OpenRouter transient retry/backoff controls.** `web/src/acb_large_print_web/ai_gateway.py` now retries transient OpenRouter failures (`429`, `5xx`) using configurable backoff (`OPENROUTER_MAX_RETRIES`, `OPENROUTER_RETRY_BASE_SECONDS`).
- **Web: Chat usage transparency improvements.** `web/src/acb_large_print_web/templates/chat_form.html` now surfaces per-session chat remaining count and queue behavior guidance for long/complex requests.

- **Web E2E: Whisperer sample-audio regression flow.** Added Playwright coverage in `web/e2e/tests/regression.spec.mjs` for `/whisperer`: consent handling, sample audio upload, explicit estimate refresh, proceed confirmation, transcription start, transcript download assertion, and saved artifact verification. Supports `E2E_UPLOAD_AUDIO` override and defaults to `S:/code/bw/Samples/ronaldreaganchallengeraddressatt3232.mp3`.
- **Web: Whisperer estimate troubleshooting diagnostics.** Added optional client-side estimate diagnostics in `whisperer_form.html` (enable with `?whispererDebug=1`) with event tracing for file selection, key/click triggers, fetch status, payload handling, and fallback paths. Added structured server-side estimate diagnostics in `routes/whisperer.py` with `WHISPERER_ESTIMATE` log lines plus optional debug payload support (`?debug=1` or `X-Whisperer-Debug: 1`).

### Changed

- **Deploy script: safe Docker cleanup controls added.** `scripts/deploy-app.sh` now supports orphan cleanup during deploy (`COMPOSE_REMOVE_ORPHANS=1` by default) and post-deploy artifact cleanup toggles. Successful deploys now optionally prune unused images (`CLEANUP_ON_SUCCESS=1`, `CLEANUP_IMAGE_PRUNE=1` by default). Optional builder cache cleanup is available via `CLEANUP_BUILDER_PRUNE=1` with `CLEANUP_BUILDER_KEEP_STORAGE` (default `4GB`). Rollback-path cleanup remains opt-in (`CLEANUP_ON_ROLLBACK=0` by default).

- **Office Add-in: dependency toolchain refreshed to latest available versions.** Updated `office-addin/package.json` and `office-addin/package-lock.json` to current releases for `typescript` (6.0.3), `webpack` (5.106.2), `webpack-cli` (7.0.2), `@types/office-js` (1.0.589), and `html-webpack-plugin` (5.6.7), plus transitive updates (`ts-loader`, `css-loader`, `webpack-dev-server`). Added `office-addin/src/global.d.ts` to declare `*.css` modules for TypeScript 6 side-effect CSS import compatibility so `npm run build` continues to compile successfully.

- **Web: Deployment branding profile support for BITS vs University of Arizona.** Added `web/src/acb_large_print_web/branding.py` and context injection in `web/src/acb_large_print_web/app.py` to support `GLOW_BRAND_PROFILE`. Default `bits` keeps current ACB/BITS wording. Setting `GLOW_BRAND_PROFILE=uarizona` now switches shared UI text in `templates/base.html` and `templates/index.html` to University of Arizona-friendly branding (removing ACB/BITS identity wording from title, nav/footer identity lines, homepage guideline copy, and Whisperer label).
- **Web: Branding is now operator-visible in Admin with deployment guidance.** `web/src/acb_large_print_web/templates/admin_flags.html` now shows a read-only active profile panel and instructions for switching `GLOW_BRAND_PROFILE` at deployment time.
- **Ops: Compose docs now include brand profile environment variable.** `web/docker-compose.prod.yml` and `web/docker-compose.wsl.yml` now document `GLOW_BRAND_PROFILE=${GLOW_BRAND_PROFILE:-bits}` for explicit profile selection.
- **Release posture: AI remains disabled by default in production and staging.** AI feature flags continue to default to off; core non-AI workflows (Audit, Fix, Export, Convert, Template, standards guidance, and profile-aware branding) remain fully functional.
- **Web: Guidelines reference page now supports UArizona branding profile language.** `web/src/acb_large_print_web/templates/guidelines.html` now conditionally removes ACB/BITS-branded wording when `GLOW_BRAND_PROFILE=uarizona` while preserving standards and rule details.
- **Web: Completed template context exposure for all non-AI feature flags.** `web/src/acb_large_print_web/app.py` now exposes `feature_word_setup_enabled`, `feature_markdown_audit_enabled`, `feature_pydocx_enabled`, `feature_openpyxl_enabled`, and `feature_python_pptx_enabled` in addition to existing feature booleans.
- **Web: Added dedicated HTML export feature flag.** `web/src/acb_large_print_web/feature_flags.py` introduces `GLOW_ENABLE_EXPORT_HTML` and `web/src/acb_large_print_web/routes/export.py` now gates `/export` at route level (GET/POST), while templates and Quick Start entry points hide Export when disabled.
- **Web: Added per-direction convert feature flags and route enforcement.** `GLOW_ENABLE_CONVERT_TO_MARKDOWN`, `GLOW_ENABLE_CONVERT_TO_HTML`, `GLOW_ENABLE_CONVERT_TO_DOCX`, `GLOW_ENABLE_CONVERT_TO_EPUB`, `GLOW_ENABLE_CONVERT_TO_PDF`, and `GLOW_ENABLE_CONVERT_TO_PIPELINE` now drive both UI visibility in `templates/convert_form.html` and backend direction guards in `web/src/acb_large_print_web/routes/convert.py`. Admin management now includes a dedicated Convert directions section in `templates/admin_flags.html` / `routes/admin.py`.

- **Web: AI features can now be deployment-gated independently from the OpenRouter key.** `web/src/acb_large_print_web/ai_features.py` now supports a master `GLOW_ENABLE_AI` switch plus per-feature gates for chat, Whisperer, AI heading refinement, alt-text helpers, and MarkItDown LLM behavior. This allows the non-AI web fixes to be deployed immediately while specific AI paths remain hidden and route-disabled until validation is complete.

- **Web: Default AI model switched from free Llama/Mistral pool to GPT-4o-mini.** `_DEFAULT_MODEL` in `web/src/acb_large_print_web/ai_gateway.py` now defaults to `openai/gpt-4o-mini` (primary) and `openai/gpt-4o` (fallback/escalation), replacing the previously unavailable `meta-llama/llama-3-8b-instruct:free,mistralai/mistral-7b-instruct:free` free-model pool. The legacy free model entries are retained in the cost table for accounts that override via `AI_DEFAULT_MODEL`. Admin reset-to-defaults and the admin AI settings dropdown updated to match. Probe path 01 and integration test fixtures updated to the new primary model. All 84/84 probe paths now pass.

### Fixed

- **Post-deploy verification no longer hangs/fails on removed Ollama service.** `scripts/post-deploy-check.sh` now gates required service checks dynamically from Compose service definitions and skips `ollama` when it is not present in `docker-compose.prod.yml`. Readiness parsing now treats `not-configured` as OK for feature-gated AI checks, preventing false deployment failures when AI/Ollama are intentionally disabled.

- **CI deploy gate: fixed false failure in Fix route form-option test under AI-off defaults.** `web/tests/test_fix_routes.py` now mocks `acb_large_print_web.ai_features.ai_heading_fix_enabled()` directly in `TestParseFormOptions::test_detect_headings_on` instead of mutating environment variables after app startup. This keeps the assertion aligned with cached feature-flag behavior in CI and prevents the `Deploy Web App` workflow from failing before SSH deployment.

- **Desktop PDF audit: resolved pre-existing style violations in `pdf_auditor.py`.** Wrapped long string and expression lines that previously triggered lint errors (including lines around missing-PyMuPDF messaging, tagged-PDF messaging, text block extraction, and font-family prefix checks) with no behavior changes.

- **Web: Changelog page `/changelog/` returned HTTP 500 due to unescaped template syntax in `changelog_body.html`.** Two occurrences of brace sequences that Jinja2 mis-parsed as template directives were escaped with HTML entities: a Docker service label using Go template syntax `{{.Name}}` (→ `&#123;&#123;.Name&#125;&#125;`) and an inline code example showing `{% set %}` / `{{ }}` Jinja2 syntax (→ `&#123;% set %&#125;` / `&#123;&#123; &#125;&#125;`).
- **CI: axe-core accessibility gate SARIF generation fixed.** `.github/workflows/accessibility-regression.yml` previously used the unsupported `--reporter sarif` flag (axe CLI 4.11.3 does not support it). Fixed by saving JSON output with `--save axe-results.json` and converting via the new `.github/scripts/axe_json_to_sarif.py` converter script, which emits valid SARIF 2.1.0 for GitHub code scanning upload.

- **Web: Home operation cards now map to correct features and labels.** `web/src/acb_large_print_web/templates/index.html` now correctly pairs the Audit card with `feature_audit_enabled` and the Fix card with `feature_checker_enabled`, with matching card classes/links/format labels.

- **Web: default Fix runs no longer show a false custom-settings warning.** `web/src/acb_large_print_web/customization_warning.py` now reads the normalized option keys produced by the Fix route and uses the canonical ACB defaults (`0.0` flush-left list indent, `0.0` paragraph indents) instead of the obsolete `0.5` list-indent default. A plain, no-customization Fix run no longer reports `List indent changed to 0.0"`.
- **Word fix: deeper heading styles now normalize consistently.** `desktop/src/acb_large_print/constants.py` and `office-addin/src/constants.ts` now define `Heading 4` through `Heading 6` with the same 20pt bold subheading treatment as the deepest configured subheading level, so existing built-in Word headings beyond level 3 no longer fall through with stale italic/small-font styling.
- **Word fix: paragraph spacing is now normalized directly on content paragraphs.** `desktop/src/acb_large_print/fixer.py` now applies canonical before/after spacing and line spacing to paragraph content, not just named styles, which fixes cases where body paragraphs kept Word's default 8pt after-spacing or heading paragraphs retained stale direct spacing overrides.
- **Word audit: repeated non-Arial findings are now capped.** `desktop/src/acb_large_print/auditor.py` and `office-addin/src/auditor.ts` now collapse repeated document-wide non-Arial font findings to the first three paragraph locations plus one summary row, reducing report spam for documents formatted wholesale in fonts like Times New Roman.
- **Docs: heading-level and paragraph-spacing guidance aligned with current fix behavior.** `docs/user-guide.md` and `web/src/acb_large_print_web/templates/partials/guide_body.html` now describe Heading 1 through Heading 6 support accurately and clarify that GLOW enforces paragraph spacing via Word paragraph-format settings (`Space Before` / `Space After`) rather than inserting blank paragraphs.
- **Web: customization warning no longer shows literal `<br>` tags or forced line wraps.** The warning text in `fix_result.html`, `audit_report.html`, and `audit_batch_report.html` now renders as plain text with preserved paragraph breaks via CSS instead of injecting escaped `<br />` tags, and `customization_warning.py` now generates unwrapped paragraph text so the notice reads naturally.
- **Web: AI-gated routes and entry points now stay consistent when a feature is turned off.** Quick Start, homepage cards, Fix-result and Audit-report chat pivots, Convert's Whisperer callout, and Whisperer/chat backend routes now honor the deployment feature gates so disabled AI features do not remain reachable through direct links or stale UI affordances.

- **Web: OpenRouter chat compatibility fallback on 400/404 payload rejections.** `web/src/acb_large_print_web/ai_gateway.py` now retries chat-completions calls once with a compatibility payload (dropping provider routing hints and model-list field) when providers reject advanced routing fields, improving reliability for chat and vision paths while keeping privacy routing as the default.
- **Tests: OpenRouter probe layer-1 no longer aborts on first model failure.** `tests/openrouter-probe/run_chat_paths_app.py` now records failures for paths 01/02 and continues executing remaining layer-1 paths so full coverage reports are generated even when a specific model is unavailable.
- **Tests: Audio probe and live test aligned with tuple return contract.** Updated `tests/openrouter-probe/run_audio_app.py` and `tests/openrouter-probe/test_openrouter_live.py` to unpack `(transcript, prompt_tokens, completion_tokens)` from `_transcribe_via_input_audio()` instead of assuming a string-only return.

- **Web: Chat tool dispatch now actually grounds responses.** `web/src/acb_large_print_web/routes/chat.py` now runs the local pre-flight keyword tool dispatcher before calling the model and injects those results into the system prompt, so Document Chat uses the accessibility toolset rather than leaving it disconnected.
- **Web: Whisperer cloud compatibility normalization.** `web/src/acb_large_print_web/routes/whisperer.py` now normalizes cloud-incompatible audio formats (OGG, FLAC, AAC, Opus) to temporary MP3 via `ffmpeg` before Whisper API upload, improving reliability across common chapter recordings.
- **Web: Health check and runtime probes scrubbed of old local-model assumptions.** `web/src/acb_large_print_web/app.py` now probes OpenRouter and Whisper directly and no longer reports Ollama or local Whisper readiness.
- **Web: Deployment stack scrubbed of stale local AI services.** Removed `ollama` and `faster-whisper` from the web deployment definitions and updated core templates (`index.html`, `chat_form.html`, `whisperer_form.html`, `about.html`, `privacy.html`) to reflect cloud-based AI usage accurately.
- **Docs: Remaining stale local-Whisper wording removed.** Updated `docs/user-guide.md` to consistently describe cloud transcription with temporary retention and cleanup.
- **Tests: Cloud architecture alignment.** Updated web tests to validate OpenRouter/Whisper health service keys and cloud Whisperer mocks, added queue/retry-focused tests in `web/tests/test_gating_ai_gateway.py`, and refreshed upload extension coverage for new audio formats.

- **Web: Accessibility audit sweep (18 templates + 2 static files).** Corrected multiple WCAG 2.2 AA issues across the web application templates. Changes: removed redundant `aria-labelledby` from `<section>` elements that already contain a headed `<h2>` (redundant landmark name per ARIA 1.2 implicit section semantics); removed `role="contentinfo"` from `<footer>` (native landmark, explicit role not required); fixed `consent.html` to use a proper `role="dialog" aria-modal="true"` modal with backdrop (users with low vision using screen magnification were seeing inline content instead of a blocking consent gate); promoted step headings in `whisperer_form.html` and `convert_form.html` from `<h3>` to `<h2>` to match their position as top-level steps within the tabpanel's content hierarchy; added `type="button"` to the Go Back button in `feedback_thanks.html` (implicit type was `submit`, risking accidental form submission); moved character-count paragraph in `chat_form.html` from `aria-hidden="true"` to `aria-live="polite" aria-atomic="true"` so screen readers announce remaining characters; removed `aria-describedby` from `admin_queue.html` System Health table (the `<caption>` already provides the description — `aria-describedby` pointing to a caption ID is redundant); fixed `maintenance.html` footer color from `#999999` (fails WCAG 1.4.3 at 3.2:1) to `#767676` (passes at 4.5:1), added `aria-hidden="true"` to decorative 🔧 emoji, and added `prefers-reduced-motion: reduce` rule to stop the status-indicator animation; added `id="confirm-estimate-hint"` to the `<p class="field-hint">` in `whisperer_form.html` that the confirm-estimate checkbox references via `aria-describedby` (was a dangling reference); disabled submit button with `aria-disabled="true"` until both acknowledge-checkboxes are checked, with JS `syncConfirmButton()` keeping disabled state in sync; wrapped `audioInput.addEventListener` in an `if (audioInput)` guard; added AbortController timeout (15 s) on Whisperer start-job fetch; improved JSON parse error handling for start-job response; improved queue-position display (1-indexed); added forms.css consent modal styles (`consent-modal-backdrop`, `consent-modal`, `consent-modal-scroll`) for the dialog layout.

- **Web: Whisperer estimate endpoint URL resolution.** `whisperer_form.html` now uses explicit backend URLs (`data-estimate-url`, `data-start-url`) instead of deriving endpoints from `form.action`, preventing broken estimate/start requests caused by path/URL variations.
- **Web: Whisperer metadata duration scaling with PyAV.** `_estimate_audio_duration_seconds()` now normalizes time-base conversion across PyAV variants so `container.duration` is interpreted in seconds correctly, avoiding extreme/invalid duration values.
- **Web: Whisperer estimate button keyboard activation reliability.** `whisperer_form.html` now handles `keydown`, `keyup`, and legacy `keypress` activation paths for Space/Enter on the estimate button with duplicate-trigger protection, improving behavior for browser and assistive-technology combinations that do not emit consistent click events.
- **Web: Whisperer estimate button real-time feedback.** The Calculate estimate button now shows "Calculating..." and disables during the estimate request, with live progress messaging ("Button pressed. Checking for audio file...", "Contacting server...") so users and screen-reader users get clear status updates about what the button is doing. Added exhaustive keyboard event telemetry to the button: logs all keydown/keyup/keypress events plus focus/blur state to the diagnostics panel and browser console for troubleshooting keyboard activation issues.
- **Web: Whisperer server-side estimate fallback step.** Added a no-JavaScript server-first flow using "Next: calculate estimate on server" and `/whisperer/estimate-page`, with two-stage rendering: initial page shows upload+Next only; after estimate, the same page shows estimate-confirmation and remaining transcription steps.
- **Web: Whisperer client-side confirm-estimate checkbox validation.** The JS submit handler now validates the required acknowledgement checkbox before posting to the server, showing a focused, accessible inline message and moving focus to the checkbox so users never reach the server with that input missing.
- **Web: Whisperer stage-2 error re-renders stay in stage 2.** When `whisperer_submit` catches a validation or runtime error it now preserves `estimate_ready=True` (when an `existing_token` is present), keeping the user on the estimate+options page so they can correct their input without re-uploading.
- **Web: Whisperer catch-all exception handler on both submit routes.** Unexpected exceptions in `whisperer_submit` and `whisperer_start_job` are now caught, logged with full tracebacks, and returned as user-friendly messages (HTML form re-render and JSON respectively) instead of propagating to the generic 500 error page.
- **Web: Whisperer model-load failure now reports the real cause.** `whisper_convert()` now maps common engine startup failures to specific user-facing errors, including insufficient disk space while downloading/loading the Whisper model and general model-load failures, instead of collapsing everything into a generic transcription-engine message.
- **Web: Additional route catch-alls now pass through real exception text.** Unexpected exceptions in `convert_submit`, `export_submit`, `template_form`, and `whisperer_start_job` now surface the actual exception message to the user instead of replacing it with a generic placeholder, improving diagnosis of production-only failures.
- **Desktop: Whisper transcription fallback now preserves real engine errors.** `whisper_convert()` no longer replaces unknown transcription failures with a fixed generic message; after specific model-load and disk-space cases are handled, the original exception text is propagated so the web app can display the actual cause.
- **Web: Whisperer cache path is now writable in containers.** The web Docker image now creates and owns a dedicated Hugging Face cache directory under `/app/.cache`, sets `XDG_CACHE_HOME`, `HF_HOME`, and `HUGGINGFACE_HUB_CACHE`, and `whisper_convert()` passes that writable cache path explicitly to `WhisperModel`. This fixes production failures like `[Errno 13] Permission denied: '/app/.cache'`.
- **Web: Increased Gunicorn request timeout for long Whisper runs.** The container now runs Gunicorn with a 30-minute timeout (up from 5 minutes) to prevent `WORKER TIMEOUT` / HTTP 502 errors while first-time model warm-up or long audio transcription is in progress.
- **Deploy: Whisper model warm-up before maintenance is lifted.** `scripts/deploy-app.sh` now preloads the Whisper model inside the web container after health passes and before disabling maintenance mode, so first-user requests do not stall on model initialization/download. Controlled via `WHISPER_WARMUP_ON_DEPLOY` (default `1`) and `WHISPER_WARMUP_TIMEOUT` (default `1200` seconds).
- **Deploy: Ollama model warm-up before maintenance is lifted.** `scripts/deploy-app.sh` now optionally pre-pulls Ollama models used by chat/vision (`llama3`, `llava` by default) before maintenance mode is disabled, reducing first-request delays and improving readiness status. Controlled via `OLLAMA_WARMUP_ON_DEPLOY` (default `1`), `OLLAMA_WARMUP_MODELS` (default `llama3 llava`), and `OLLAMA_WARMUP_TIMEOUT_PER_MODEL` (default `900` seconds).
- **Web: Whisperer client-side oversized-file precheck.** The form now uses the server-configured maximum audio size to warn and block oversized files immediately after selection (before upload), disabling estimate/proceed controls until a valid file is chosen.
- **Web: Whisperer progress UX clarity improvements.** The transcribe page now shows an explicit phase label (queued/model warm-up/transcribing/building/complete), an elapsed-time counter, queue position in status text, automatic scroll to the progress panel after submit, and a "still working" message when progress appears stalled during long model warm-up or processing.

### Added

- **Web: `/health` Ollama warm-model tracking.** `_get_ollama_running_models()` now queries `/api/ps` to list models currently loaded in Ollama memory. The `readiness.chat` and `readiness.vision` blocks each expose a new `model_warm` boolean, and `models.ollama_running` is included in the response and health log line so operators can tell instantly whether `llama3`/`llava` are warm (in memory) vs merely pulled (on disk).
- **Web: `/health` Whisper model-present check.** `_whisper_model_present()` inspects the configured Hugging Face cache directory for `model.bin` to distinguish "faster-whisper installed" from "Whisper model actually downloaded". `readiness.whisperer` now exposes `model_present` separately from `dependency_present`, so the health endpoint surfaces the full warm-up state of the Whisperer pipeline.
- **Ops: Post-deploy readiness gate for models.** `scripts/post-deploy-check.sh` now curls `/health` after all containers pass their Docker health gates and parses the `readiness` JSON with Python. If any feature (`chat`, `vision`, `whisperer`) is `not-ready`, the script prints the status/present/warm details and fails the deployment verification, preventing a deploy from being marked PASSED when required models have not been downloaded or loaded.

### Changed

- **Web: Whisperer duration probe now prefers Mutagen metadata.** `_estimate_audio_duration_seconds()` now uses `mutagen` as the primary duration source and falls back to PyAV for additional codec/container coverage. Added `mutagen>=1.47.0` to `web/pyproject.toml` and `web/requirements.txt`.

## [2.0.0] - 2026-04-17

### Added

- **Ops: Deep deployment logging.** `scripts/deploy-app.sh` now writes every phase of a deployment to a timestamped log file in `~/deploy-logs/` (always teed to stdout). Each step emits an ISO-8601 timestamp. The health-wait loop logs per-attempt container `state=` / `health=` / `last_log=` for all four services at every interval. On health check failure the script dumps the last 40-80 lines from each service log, runs `docker inspect` to show container error and restart state, and probes `/health` JSON to print the full service + readiness breakdown. Rollback attempts are logged the same way. A `deploy-latest.log` symlink always points to the most recent run.
- **Web: `/health` deep readiness checks.** The `/health` endpoint now returns a `readiness` object alongside `services`. `readiness.chat` reports whether the Llama 3 model is loaded in Ollama. `readiness.vision` reports whether LLaVA is available. `readiness.whisperer` reports whether faster-whisper is installed. The top-level `status` field is `"degraded"` if any service is down or any readiness check is `"not-ready"`. The `models.ollama` array lists all currently loaded model names.
- **Web: `/health` probe logs service + readiness summary at INFO.** Every `/health` call now emits a structured log line: `HEALTH status=... services=... readiness=... models=... duration_ms=...`. Health poll calls that return 200 in under 2 seconds are suppressed to avoid log noise; slow or failing calls always log.
- **Web: Flask startup ready log.** On worker startup the app emits `GLOW startup: web=X core=Y maintenance=Z log_level=W` so deployment logs confirm the correct package versions are loaded.
- **Web: Per-request logging middleware.** Every request logs `REQUEST METHOD /path -> STATUS (Xms) ua=...` at INFO after the response is sent. Silent for fast successful `/health` polls.
- **Admin: Live System Health panel on admin queue dashboard.** `admin_queue.html` now shows a "System Health" table that fetches `/health` JSON on load and refreshes every 20 seconds alongside the queue refresh. Rows show web / pipeline / Ollama service status plus chat (Llama 3), vision (LLaVA), and Whisperer readiness.
- **Docker: Service log labels and increased retention.** All four Compose services now include a `tag` label (`glow-web/{{.Name}}`, `glow-pipeline/{{.Name}}`, `glow-ollama/{{.Name}}`, `glow-caddy/{{.Name}}`) for `docker logs` filtering. Log caps raised: web 5 files x 20 MB; pipeline and Ollama 5 files x 10 MB; Caddy 3 files x 5 MB (was 2 files x 5-10 MB). Web healthcheck timeout raised to 10 s and retries to 5 to accommodate slower starts. `process_form.html`, `template_form.html`, `fix_review_headings.html`, `admin_login.html`, `chat_form.html`, `feedback_form.html`, `admin_request_access.html`, `consent.html`, and `whisperer_retrieve.html` now disable their submit button and display a polite `aria-live` status paragraph immediately on submit. Prevents double-submission and gives screen readers and sighted users clear progress feedback.
- **Web: Download processing state on fix_result.** The "Download Fixed Document" button in `fix_result.html` shows "Preparing your download…" and disables for 4 seconds on click, preventing double-submission on slow connections.
- **Web: Document Chat card on home page.** `index.html` now includes Document Chat in the card grid and "What Each Tab Does" section. Users no longer need to discover Chat only by accident.
- **Web: Format-specific CTAs in batch audit report.** `audit_batch_report.html` per-file sections now show actionable next steps for every supported format (xlsx/pptx manual-fix guide, md convert flow, pdf Acrobat note, epub source-fix hint). "What's Next?" section expanded.
- **Web: Whisperer step numbering with Jinja namespace counter.** Step labels in `whisperer_form.html` use a `namespace(step=1)` counter so numbers stay sequential when the email background-notification fieldset is hidden.
- **Web: Settings page noscript fallback.** `settings.html` includes a `<noscript>` notice informing users that Settings requires JavaScript.
- **Web: Admin queue auto-refresh.** `admin_queue.html` auto-reloads every 20 seconds when any row shows `queued` or `processing` status. Refresh stops when the tab is hidden. Polite `aria-live` announcement precedes each reload with a timestamped caption.
- **Web: Fix review headings -- session expiry recovery hint.** `fix_review_headings.html` shows the session expiry time and recovery instructions near the submit button.
- **Web: Chat Ask Question submit state.** The Ask Question button disables and announces "Asking the AI… This can take up to 30 seconds" via `aria-live` during AI inference.
- **Web: Chat export emoji aria-hidden.** Decorative emoji on Export and Clear Conversation buttons are wrapped in `<span aria-hidden="true">`.
- **Web: process_choose empty-state fallback.** When no actions are available for a file type, `process_choose.html` shows a descriptive notice listing supported formats.
- **Web: process_choose action icon aria-hidden.** Decorative emoji icons on action cards in `process_choose.html` are wrapped with `aria-hidden="true"`.
- **Web: Admin request confirmation dialogs.** Approve and Deny buttons in `admin_requests.html` include `onclick="return confirm(…)"` guards naming the target email to prevent accidental approvals or denials.
- **Web: Admin queue action confirmation dialogs.** Cancel and Re-Queue buttons in `admin_queue.html` include confirm dialogs to prevent accidental queue operations.
- **Web: Privacy page consent-clear confirmation dialog.** The "Clear My Consent Record" button in `privacy.html` requires user confirmation before posting.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Opus) to Markdown (.md) or Word (.docx) using faster-whisper with the Whisper medium model and CTranslate2 int8 quantization. Audio is processed entirely on the GLOW server and never sent to any external service (no OpenAI, no cloud API). Supports language selection (auto-detect or choose from 50+ languages). Includes concurrency gating to protect CPU resources and a 503 Busy page with Retry-After headers when the inference queue is full.
- **Web: Consent and agreement gate (`/consent`).** First-time visitors are shown a one-page agreement explaining how GLOW handles data, what AI features are available locally, privacy protections, and cookie policies before accessing any tool. Agreement is stored in a secure `glow_consent_v1` cookie (HttpOnly, Strict SameSite, 365-day expiry). The consent gate is skipped in test mode so existing tests don't require cookie fixtures. Users can withdraw consent and reset the gate via the Privacy Policy page.
- **Web: Quick Start beginner path (`/process`).** New universal upload form + contextual action chooser. Users upload any document type and are shown available actions (Audit, Fix, Convert, Export, Template, BITS Whisperer) based on the file type. Reduces barrier to entry for accessibility newcomers while keeping the expert tab interface for power users. Both paths coexist.
- **Web: MarkItDown 0.2+ integration with enhanced capabilities.** Upgraded from MarkItDown 0.1.5 to 0.2+. Added support for image files (JPG, JPEG, PNG, GIF, WebP, BMP, TIFF). New `convert_with_llm_descriptions()` function passes local Ollama/Llama3 instance as LLM client to generate alt text descriptions for images in PowerPoint files and standalone image uploads -- fully local, no third-party API. New `youtube_to_markdown()` function fetches YouTube video transcripts (using YouTube's own caption data) and converts them to Markdown.
- **Web: Image file audit support.** Image files (.jpg, .jpeg, .png, .gif, .webp, .bmp, .tiff) are now accepted by Audit. Extracted EXIF metadata and any embedded text are included in the audit report.
- **Web: `/health` capacity metrics.** The health check endpoint now exposes `capacity` object with `active_jobs` (AI and audio inference jobs in flight), `max_concurrent_jobs`, and feature availability flags (`whisper_available`, `ai_available`). Consumed by the 503 busy logic to determine when to queue or reject.
- **Web: `convert_form.html` callout card for BITS Whisperer.** Below the standard Convert form, a prominent info card directs audio users to BITS Whisperer with a link to `/whisperer`.
- **Web: BITS Whisperer tab in main navigation.** Added between Convert and Guidelines tabs in base.html navigation.
- **Web: Settings link in footer.** Users can now access the Settings page (preference defaults) from the footer navigation.
- **Web: Audio concurrency gating and semaphore.** New `gating.py` module implements audio and AI task concurrency limiting via semaphore. Prevents CPU overload during Whisper transcription. Configurable via `GLOW_MAX_AUDIO_JOBS` (default 1) and `GLOW_MAX_AI_JOBS` (default 1) environment variables. When at capacity, a 503 Busy page is returned with `Retry-After: 60` header.
- **Web: Privacy Policy consent withdrawal controls.** New section in Privacy Policy (`/privacy`) allows users to clear their consent cookie via a button that POSTs to `/consent/withdraw`. Also documents cookie policy and the opt-in nature of consent.
- **Web: `aria-describedby` on whisperer retrieve password input.** The retrieval password field in `whisperer_retrieve.html` now references its hint paragraph via `aria-describedby`.
- **Web: `aria-describedby` on whisperer password-confirm input.** The confirm password field in `whisperer_form.html` now has its own hint paragraph and `aria-describedby`.
- **Web: `autocomplete="name"` on display_name in admin_request_access.** Assists password managers and autofill.
- **Web: Styled `:disabled` state for `btn-primary` and `btn-secondary`.** `forms.css` now explicitly styles `button:disabled` and `[aria-disabled="true"]` for both button classes, providing consistent visual feedback across browsers rather than relying on browser defaults.
- **Web: HTTP 403 error handler.** `app.py` now registers a `@errorhandler(403)` that renders the styled `error.html` template (matching 404/500 behavior) instead of Flask's default unstyled 403 page. Triggered by `abort(403)` in feedback review, admin access checks, and OAuth flows.

### Changed

- **Web: fix_review_headings Apply button** now has an `id` and processing-state JS to prevent accidental double-submission.

### Added

- **Web: Real-time BITS Whisperer progress reporting.** Whisper transcription now runs as a background job with dedicated status and download endpoints (`/whisperer/start`, `/whisperer/progress/<job_id>`, `/whisperer/download/<job_id>`). The Whisperer page shows true server-reported conversion percentage instead of only elapsed-time estimates, including live status announcements for screen reader users.
- **Web: Whisperer preflight estimate + proceed confirmation.** Before transcription starts, the Whisperer form now shows an estimated conversion time from uploaded audio metadata and requires explicit user confirmation to proceed.
- **Web: Whisperer graceful length/size limits.** Added configurable guardrails (`WHISPER_MAX_AUDIO_MB`, `WHISPER_MAX_AUDIO_MINUTES`) with clear user-facing guidance to split/compress oversized recordings instead of failing silently.
- **Web: Active Whisperer job retention hardening.** In-progress audio jobs now refresh their temp workspace timestamps so stale-upload cleanup does not remove files needed for long-running conversions.
- **Web: Whisperer background queue + secure retrieval lifecycle.** Any audio job (any length) can opt into background processing with queueing, queued/started/completed lifecycle notifications, single-use secure retrieval links, retrieval password verification, and a final content-cleared email when unretrieved results expire. The background option is always visible when email is configured -- not gated on recording length -- so users are never stranded on a busy-server 503 without a queue path.
- **Ops: Deploy script backup + rollback safety.** `scripts/deploy-app.sh` now creates a pre-deploy feedback backup (by default) and performs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.
- **Admin: Authentication and approval hub.** Added admin-only login and approval routes (`/admin/login`, `/admin/request-access`, `/admin/queue`, `/admin/requests`) with email magic-link login, configured SSO providers (Google, Apple, GitHub, Microsoft, Auth0, WordPress), bootstrap admin seeding, and approval-required access control.
- **Admin: Audio queue operations UI.** Added admin dashboard controls to inspect audio conversion queue state, cancel queued jobs, and re-queue failed jobs.
- **BITS Whisperer: On-server audio transcription.** New `/whisperer` route and tab. Transcribes audio files (MP3, WAV, M4A, OGG, FLAC, AAC, Op
- Pattern library, severity scoring, emoji maps, and fix templates

#### Reference Files

- `acb-large-print.css` -- drop-in CSS stylesheet (rem-based, WCAG 2.2 AA, `@media print` overrides for ACB 1.15 line-height)
- `acb-large-print-boilerplate.html` -- semantic HTML skeleton with headings, lists, TOC leader dots, table, figure with caption, and endnotes

#### Desktop Tool (Python)

- CLI with subcommands: `audit`, `fix`, `template`, `export`, `batch`
- GUI: accessible 7-step wxPython wizard
- Word document auditor enforcing ACB Large Print Guidelines:
  - Font family (Arial), body size (18pt), heading sizes (22pt/20pt)
  - No italic, bold restricted to headings, underline emphasis
  - Flush left alignment, line spacing, margins, widow/orphan control
  - No hyphenation, page numbers, heading hierarchy
  - Document title, document language (WCAG 2.4.2, 3.1.1)
  - Alt text, table headers, hyperlink text (Microsoft Accessibility Checker rules)
- Word document fixer: auto-corrects fonts, sizes, spacing, alignment, emphasis
- Word template builder: generates `.dotx` with all ACB styles pre-configured
- HTML exporter via Mammoth: standalone pages and CMS-embeddable fragments
- Cross-platform PyInstaller builds (Windows x64, macOS ARM64)
- Inno Setup installer for Windows distribution

#### CI/CD

- GitHub Actions workflow for automated builds on push/tag/PR
- Artifact upload for all platform executables
- Release automation on version tags

#### Documentation

- Comprehensive documentation (`docs/acb-large-print-toolkit.md`)
- Project announcement (`docs/announcement.md`)
- ACB Large Print Guidelines source document (`docs/`)
