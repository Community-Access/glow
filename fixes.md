# GLOW bug hunt and fixes

Date: 2026-09-01
Scope: `web/` (the GLOW Flask app). Triggered by David's Site Audit failure
report, then widened into a full read-only bug hunt across concurrency,
security, core logic, and the front end.

This document has three parts:

1. **David's report** and how it was resolved and verified in production.
2. **Fixes applied in this session** (shipped, with tests).
3. **Remaining findings** from the audit that are documented but not yet
   fixed, ranked so the next pass can pick them up in priority order.

---

## 1. David's report: "Working outside of application context"

David ran a single-page audit of the Carroll Center home page from two
machines and each time got:

> Scan failed, Error, , Working outside of application context. This typically
> means that you attempted to use functionality that needed the current
> application...

**Root cause.** The Site Audit form ships with "run in background" checked by
default. The background path ran the scan on a bare `threading.Thread` whose
worker called `_runs_root()` -> `current_app.instance_path` *after* the request
context that spawned it was gone. Flask raised `RuntimeError`; the worker
caught it and stored the raw message, which the job page then showed as "Scan
failed". The synchronous path never hit this because it runs inside the
request. No test exercised the real threaded worker body, so it went unseen.

**Fix.** Capture the app object while the request is still live and run the
worker inside `app.app_context()` -- the same idiom the workshop pulse route
already uses. `web/src/acb_large_print_web/routes/site_audit.py`.

**Verification (production).** After deploy, David's exact scenario was
reproduced over HTTP against `https://letitglow.app`: a background audit of
`https://carrollcenter.org/` reached `status: complete`, `error: null`,
`progress: 100`, and the result page rendered findings. The failure is gone.

Shipped in commit `7d84c4a` (deploy succeeded on the app; the deploy job's
post-check flagged two unrelated, transient probe failures -- see fix L).

---

## 2. Fixes applied in this session

All changes are covered by tests; the full web suite is green (843 passed,
31 skipped).

### A. Site Audit background scan runs without an app context (HIGH) — shipped `7d84c4a`
See part 1. `routes/site_audit.py`; test hardened in `tests/test_site_audit.py`
to wait for a terminal state and assert `status == "complete"` and
`error is None` (fails against the old code).

### B. Whisperer self-deadlock on a non-reentrant lock (HIGH)
`routes/whisperer.py` — the "audio queue full" branch called `_delete_job()`
(which takes `_jobs_lock`) *while already holding* `_jobs_lock`, a plain
non-reentrant `Lock`. The 9th+ concurrent start in one worker would block
forever holding the lock, wedging every route that touches it (progress
polling, dispatch, the admin queue page) until the process restarted. Fixed by
computing "queue full" under the lock and doing the cleanup after releasing it.

### C. Rate-limit key bypass defeated the brute-force caps (HIGH, security)
`app.py` `rate_limit_key()` keyed on the `glow_workshop_participant` cookie for
*every* route. An attacker rotating a random cookie per request minted a fresh
bucket each time — a total bypass of the admin-login 10/min cap, the
request-access caps, and the upload caps. Scoped the cookie-based key to
workshop routes only (`request.blueprint == "workshop"`); everywhere else keys
purely on the remote address. Workshop rooms behind one NAT still get
per-participant buckets.

### D. Open redirect in the consent gate (MEDIUM, security)
`routes/consent.py` — the `next` guard was `startswith(("http://","https://",
"//"))`, bypassable with `HTTPS://evil.com` (case) and `/\evil.com`
(backslash, which browsers normalize to `//`). The consent page is the first
page a new visitor sees, so it's a strong phishing lure. Replaced all three
call sites with a positive `_safe_next()` test: the target must parse with no
scheme and no host and begin with a single forward slash. Regression test
covers the case and backslash variants.

### E. Site Audit SSRF with response exfiltration (CRITICAL, security)
`site_audit.py` — the auditor fetched any http/https URL an anonymous visitor
submitted and saved the response body into `artifacts.zip`, which the submitter
can download. That is a full server-side request forgery primitive:
`http://169.254.169.254/...` (cloud metadata / credentials), `http://redis:6379/`,
internal admin pages — all readable. Added:

- `_is_public_url()` — resolves the host with `getaddrinfo` and rejects
  loopback, private, link-local, reserved, multicast, unspecified addresses and
  non-web ports.
- `_http_get()` — an SSRF-guarded GET that validates the initial URL **and
  every redirect hop** (redirects are followed manually with
  `allow_redirects=False`), and **caps the body at 8 MB** so a gzip bomb can't
  exhaust memory/disk.

All three fetch sites (single-page scan, crawl, sitemap) go through it. Tests
cover blocking of internal literals, allowing a stubbed public host, and that
`_scan_single_page` never reaches `requests.get` for a blocked URL.
Residual risk noted below (DNS rebinding — finding R1).

### F. Crawler treated `mailto:`/`tel:`/`javascript:` as pages; duplicate fragments (HIGH, correctness)
`site_audit.py` `_normalize_url()` prefixed any non-http string with
`https://`, so `mailto:info@x` became `https://mailto:info@x` — parsed as host
`mailto` with userinfo, then queued and fetched as a "same-site page" that
produced bogus findings and a credential-shaped request to the real site. Now
non-web schemes are rejected. Also strips URL fragments so `/page` and
`/page#section` are one page, not two (in-page anchors and skip links no longer
burn the `max_pages` budget re-scanning identical HTML).

### G. HTML parser never flushed a missing/split closing tag (MEDIUM, correctness)
`site_audit.py` `_PageParser` committed the title and trailing link only on the
closing tag, so a page whose `</title>` was absent or split across read chunks
was falsely reported as "missing a non-empty title element" (a **high**
severity false positive on a compliant page), and a trailing `<a>` was dropped
from the crawl frontier. Added a `close()` override that flushes pending title
and anchor state, and call `parser.close()` on both parse paths.

### H. HTTP error pages recorded as successfully scanned (MEDIUM, correctness)
`site_audit.py` `_scan_single_page` returned `result: "ok"` regardless of
status code, so a 404/500 body (with no title or lang) was counted toward
coverage and produced two "high" findings against a URL that never really
renders. Now any status >= 400 is returned as a per-page error.

### I. Quick Wins undercounted: four `FIXABLE_RULE_IDS` didn't exist (MEDIUM, user-facing)
`routes/audit.py` — `ACB-BOLD-BODY`, `ACB-ALL-CAPS`, `ACB-HYPHENATION`,
`ACB-DOC-LANG` are not real rule IDs (verified against
`desktop/src/acb_large_print/constants.py`). The correct rules
(`ACB-BOLD-HEADINGS-ONLY`, `ACB-NO-ALLCAPS`, `ACB-NO-HYPHENATION`,
`ACB-DOC-LANGUAGE`) were therefore never shown as auto-fixable, so "Show Quick
Wins Only" understated what GLOW Fix can do and users did manual work the tool
would have done. Corrected the IDs and added a guard test asserting
`FIXABLE_RULE_IDS <= get_all_rule_ids()` so they can't drift again.

### J. Site Audit live status page was inaccessible and its poller hung (HIGH, a11y) — AHG-relevant
`templates/site_audit_job.html` — the one page whose whole job is live status
had no `aria-live`, no `role="status"`, no real progress bar, so a screen-reader
or magnifier user got zero feedback for the entire crawl. On completion it
disabled the (likely focused) Cancel button, dropping focus to `<body>`. The
poller called `r.json()` with no `r.ok` check, so a 403/404/500 (e.g. the job
expired from the in-memory store after a restart) threw and it retried forever,
leaving the page stuck at "queued / 0%". Rewrote it to:

- announce every state/progress/message/error change into a polite live region;
- drive a real `<progress>` element;
- surface `data.error` in a live error row (previously only shown on reload);
- check `r.ok`, stop after 5 consecutive failures with "Lost contact with the
  scan. Reload this page.";
- on completion hide the Cancel form (not disable it) and move focus to the
  results link.

Also guarded the misleading "Private Access" card behind `{% if access %}` so
unprotected runs no longer claim to be private.

### K. Declared `defusedxml` as a dependency
`site_audit.py` now parses the sitemap XML with `defusedxml` (billion-laughs /
entity-expansion protection on attacker-controlled sitemaps). Added
`defusedxml>=0.7.1` to `web/requirements.txt` and `web/pyproject.toml` — it was
only present transitively, which would have broken the prod build's import.

### L. Deploy post-check failed the deploy on transient probe races (CI)
`scripts/post-deploy-check.sh` — `check_url` / `check_header_contains` probed
`letitglow.app` moments after Caddy and the app containers restart; a single
early request could catch Caddy mid-reload and fail an otherwise healthy
deploy (this is what failed the `7d84c4a` deploy job even though the app was
up). Both checks now retry up to four times with a 5s backoff before reporting
a problem.

**Files changed:** `routes/site_audit.py`, `routes/whisperer.py`,
`routes/consent.py`, `routes/audit.py`, `site_audit.py`, `app.py`,
`templates/site_audit_job.html`, `requirements.txt`, `pyproject.toml`,
`scripts/post-deploy-check.sh`, plus `CHANGELOG.md` and the test files
`tests/test_site_audit.py`, `tests/test_static_routes.py`,
`tests/test_fix_routes.py`.

---

## 3. Second pass — the remaining findings, now fixed

Everything below was fixed in a second pass by seven file-partitioned
implementation agents, each with regression tests. The full web suite is green
(916 passing). The per-agent summary:

- **Site Audit engine/UI** — run-dir + `_jobs` TTL sweep and eviction;
  cancel+retry no longer spawns a second worker over one run dir; retry forces a
  fresh crawl and the skip branch aggregates cached findings; UTF-8 charset
  recovery; non-HTML content-type is skipped instead of parsed; axe resolves
  `npx` via `shutil.which`; one severity vocabulary (axe critical → critical);
  the protected-run gate coerces naive timestamps (403 not 500); corrupt
  `page.json` is re-scanned; O(1) crawl-frontier membership; new-tab link labels.
- **Whisperer + Playground** — the transcription failure handler catches broad
  exceptions and always advances the queue in a `finally`; `GatingError`
  re-queues then re-dispatches when capacity frees; terminal jobs are pruned
  (background jobs inside their retrieval window exempted); the token dir is
  touched on completion; the completion email uses an absolute URL resolved in
  the request; ffmpeg has a timeout; the Playground SSE stream persists history
  server-side (plus two latent `get_quota_status` NameErrors fixed).
- **Core infra** — feature-flag seeding is gated on the store actually being
  empty (no more reset-to-defaults on every sqlite restart); flag writes are
  atomic + locked with a last-known-good fallback; sqlite connections are closed
  and the schema built once; the rate limiter uses Redis when available; session
  cookies are HttpOnly/SameSite/Secure; admin password and OAuth logins clear the
  session first; request logs redact secret query params; the share cache
  survives the upload sweep; the cleanup lock recovers from a stale tmp;
  `report_cache` guards its token and TTL parse.
- **Content processing** — the chat Compliance Agent reads `.message` and
  lowercases severity (it produces real audits again, not a silent heuristic
  fallback); PDF export raises on failure and the route returns the error page;
  pandoc/ffmpeg have timeouts; PyMuPDF docs are always closed; the pronunciation
  regex escapes its replacement and handles punctuated terms; table heuristics
  fixed; an extensionless upload is never deleted; zip/XML bombs are capped and
  parsed with `defusedxml`.
- **Rules + audit/fix routes** — WCAG reference mismatches corrected and missing
  slugs added; `build_rule_policy` no longer iterates a string into an empty
  rule set; an empty custom selection audits nothing (not everything);
  `suggest_alt_text` returns 400 not 500; the webhook callback runs through the
  SSRF gate with a case-insensitive scheme check; fix downloads use the right
  mimetype.
- **PageFlow SSRF** — `source_url` and every redirect hop run through
  `_is_public_url`; the POST handler is rate-limited; argv option-injection into
  the node subprocess is blocked.
- **Frontend** — the rules_ref data-loss null deref, tabs.js hijacking the admin
  flags tablist (and re-injecting un-nonced script), the app-wide once-a-second
  ai-meter re-announcement, the job-progress SSE with no error fallback, the
  file-input Enter and Ctrl+U key hijacks, the Escape-in-`<details>` trap,
  duplicate copy handlers, the 20s admin_queue hard reload, the incomplete
  admin_flags tab pattern, the alt-text-helper JSON/clipboard crashes, and the
  smaller pluralization / aria-label / queued-guard / Quick-Wins-label items.

### Third pass — the last remaining items, now fixed

- **Cross-worker job state (Site Audit + Whisperer).** Both job stores now
  persist each job's state to a per-job `status.json` on the shared instance
  volume (`instance/site_audit_jobs/<id>/` and `instance/whisperer_jobs/<id>/`),
  written atomically (temp + `os.replace`), following the `tasks/convert_tasks.py`
  idioms. Status polls, cancel, retry, download, and the emailed Whisperer
  retrieval link now resolve from any gunicorn worker instead of 404-ing ~half
  the time. Job ids are validated against a strict UUID pattern before any path
  join (traversal guard); the plaintext access/retrieval tokens are never written
  to disk (only their hashes), and the retrieval password keeps its existing
  hash-only storage. Cross-worker cancellation works via a flag in the shared
  status file, which the running worker consults. Residual, unchanged by design:
  which worker *runs* a job, and the per-process queue/gating, stay per-process —
  only lookup/status/cancel/retry/download/retrieve became cross-worker. (For
  Whisperer download/retrieve the output *file* must also be on the shared volume;
  in production `GLOW_UPLOAD_TEMP_BASE` is on the `feedback-data` volume mounted
  into every container, so it is.)
- **office-addin vulnerabilities and build.** `npm audit` now reports **0
  vulnerabilities**: `nanoid`, `browserslist`, and `adm-zip` are pinned to patched
  versions in `overrides` (the adm-zip override to `>=0.6.0` avoided a breaking
  downgrade of the dev-only `office-addin-debugging` tool), and a semver-safe
  `npm audit fix` cleared the rest. The pre-existing `npm run build` failure is
  fixed: `version.ts` read the filesystem at runtime (`fs`/`path`/`__dirname`),
  which is wrong for a browser task-pane bundle and broke the TypeScript build.
  The version is now injected at build time by webpack's `DefinePlugin` from the
  repo-root `VERSION` file, so the add-in compiles cleanly and stays in sync.

### Still open (minor hardening, tracked)

- **SSRF DNS-rebinding residual (R1)** — `_is_public_url` resolves and validates
  the host, but a subsequent connect could re-resolve to a different address.
  Pinning the resolved IP for the actual connection is a hardening follow-up; the
  single-fetch window makes this low-risk.
- **Per-process queue/gating** — Whisperer's audio queue depth and concurrency
  gate are still per-worker, so the advertised caps are effectively multiplied by
  the worker count. Making these exact needs a shared counter (Redis); the job
  *state* is now shared, which was the user-visible bug.

---

## Appendix: original finding detail (for reference)

The findings above were originally documented here as "not yet fixed"; the
detail is retained below. Most HIGH items shared one root cause: **in-memory
per-process state under a 2-worker gunicorn deployment.**

### Multi-worker state (the biggest theme) — HIGH
Caddy round-robins across two gunicorn worker processes, but several stores
live in one process's memory, so a follow-up request that lands on the other
worker sees nothing:

- **Whisperer `_jobs` / `_audio_queue`** — ~half of progress polls, downloads,
  and emailed secure-retrieval links hit the worker that doesn't own the job and
  404. `routes/whisperer.py`.
- **Site Audit `_jobs`** — the background progress page, cancel, retry, and
  status endpoint `abort(404)` about half the time. `routes/site_audit.py`.
- **Admin queue snapshot / cancel / requeue** — the admin sees ~half the queue.
- **flask-limiter `storage_uri="memory://"`** — every rate limit is effectively
  doubled and non-deterministic. Point it at the existing Redis.
- **Audit webhook fallback secret `os.urandom(32)`** — the two workers sign with
  different secrets, so `X-GLOW-Signature` can't be verified when
  `WEBHOOK_SECRET` is unset.

Recommended direction: move these job stores to the filesystem/SQLite pattern
already used by `tasks/convert_tasks.py` (status JSON on the shared volume), or
run them on Celery like the other long jobs; move rate-limit storage to Redis.

### Feature flags reset to defaults on every restart (sqlite backend) — CRITICAL
`app.py` seeds defaults when `feature_flags.json` doesn't exist, but the sqlite
backend never creates that file, so the guard is always true and
`reset_defaults()` upserts all defaults over the admin's changes on every
restart/worker respawn — silently re-enabling disabled features (AI, billing
exposure). `docker-compose.dev.yml` uses the sqlite backend. Gate the seed on
the actual store being empty. (The tests labelled "sqlite backend" actually
exercise the JSON backend, because `_BACKEND` is bound at import — so this path
is untested.)

### Chat "Compliance Agent" live audit is dead code — HIGH
`chat_handler.py` reads `finding.description`, but `Finding` has `.message`, so
every live-audit call throws `AttributeError`, is swallowed, and the user gets
the regex heuristic presented as a real GLOW audit. Separately, severity
comparisons use `"critical"` while the enum values are `"Critical"` etc., so
even after fixing the attribute the counts are all zero and
`get_critical_findings` answers "Document is in good shape" for a document with
critical violations. Fix `.message` + case-normalize severity; add a test that
`_audit_cache` is populated.

### Whisperer worker: narrow `except` freezes jobs and stalls the queue — HIGH
`routes/whisperer.py` catches only `(UploadError, RuntimeError, FileNotFoundError,
ValueError)`. An `OSError`/`MemoryError`/`requests` error escapes the thread, the
job is stuck "running" forever, and `_dispatch_queued_jobs()` never runs so
every queued job behind it stalls until restart. Use `except Exception` (keep
`BaseException` uncaught) and put `_dispatch_queued_jobs()` in a `finally`.

### Background transcripts deleted an hour into a four-hour window — HIGH
`_RETRIEVAL_HOURS = 4` but `UPLOAD_MAX_AGE_HOURS = 1`, and nothing touches the
token dir after the job completes, so the per-request sweeper `rmtree`s the
finished transcript ~70 minutes in. The user opens the "valid 4 hours" email and
gets "no longer available". Touch the dir on completion, or align the TTLs, or
store retrieval artifacts outside the sweep base.

### Share cache deleted ~3 hours before shares expire — HIGH
`upload.cleanup_stale_uploads` rmtrees `shares/` (which lives under
`UPLOAD_TEMP_BASE`) once its mtime passes the 1h upload cutoff, while
`SHARE_TTL_HOURS = 4`. Outstanding share links 404 three hours early. Skip the
`shares` directory in the sweep (or move it out of the upload base).

### Site Audit disk + memory leak — HIGH
`instance/site_audit_runs/` is never swept and `_jobs` is never evicted. Each
run stores full page HTML twice (raw + zipped) plus the summary and plaintext
token in memory forever. A few hundred runs fill the volume (ENOSPC) and RSS
grows monotonically. Add a TTL sweep to the existing per-request cleanup hook
and evict terminal `_jobs` entries.

### Cancel + Retry can run two workers over one run dir — HIGH
`routes/site_audit.py` — cancel is only observed between pages, so an immediate
Retry clears the cancel event and spawns a second thread that writes the same
`summary.json` / `findings.csv` / `artifacts.zip` concurrently (on Windows, a
`PermissionError` on the open zip). Track the worker thread and refuse retry
while it's alive, or give retry a fresh `run_id`. Related: retry re-uses cached
`page.json` output (unless `force`), so a retried run can report "0 findings"
from the skip branch — force a fresh crawl on retry.

### Chat PDF export returns a 0-byte "PDF" with HTTP 200 — HIGH
`chat_handler.py` / `routes/chat.py` — on failure `export_pdf` returns silently
after the temp file already exists, so `temp_path.exists()` is always true and
the user downloads an empty `.pdf` with a 200. Raise on failure, check
`st_size > 0`, clean temp siblings in `finally`, and add `timeout=` to the
pandoc/ffmpeg subprocess calls.

### Playground SSE writes to `session` inside the generator — MEDIUM
`routes/playground.py` — the `Set-Cookie` is already built before the streaming
body iterates, so every streamed turn's history is silently dropped and the
assistant "forgets" mid-conversation. Persist streamed turns server-side.

### Secrets in query strings are written to the request log — MEDIUM-HIGH
`app.py` logs `full_path` including the query string, capturing share
passphrases (`?p=`), site-audit access tokens (`?access=`), admin magic-link
tokens (`?token=`), and the feedback review key. Two `speech.py` lines log
upload tokens outright. Redact known-sensitive params in the log line; prefer
POST/short-lived cookies over `?access=`/`?p=`.

### Session hardening — MEDIUM-LOW
`app.py` never sets `SESSION_COOKIE_SECURE`/`SAMESITE`; the password and OAuth
admin sign-in paths don't `session.clear()` before elevating (session fixation).
The consent cookie two files over does all of this correctly and is a good
template.

### Front-end correctness/a11y (beyond fix J) — MEDIUM
Confirmed by the front-end sweep; each is a small, local fix:

- `rules_ref.html` — `getElementById('btn-toggle-all')` is null (no such
  element), throwing in `DOMContentLoaded` so the user's saved rule set is never
  applied and can be overwritten with "all rules" on Save. **Silent data loss.**
- `static/tabs.js` — grabs the first `[role="tablist"]` globally and breaks the
  admin Feature Flags page (wipes unsaved toggles; re-injects inline script
  without the CSP nonce, so it's then blocked). Bail out when the tabs aren't
  links.
- `partials/ai_meter.html` + `ai-meter.js` — the whole meter is
  `aria-live`/`aria-atomic`, re-announced once per second app-wide; the countdown
  timer is never cleared. Move live-ness to a dedicated span and guard the writes.
- `job-progress.js` — SSE has no `onerror`/fallback and unguarded `JSON.parse`;
  the poll fallback shares fix J's missing-`r.ok` flaw.
- Several smaller ones: file-input Enter submits the form; Escape inside
  `<details>` collapses it while typing; duplicate copy-to-clipboard handlers;
  `admin_queue.html` hard-reloads every 20s with a fake live region; singular/
  plural "1 submissions"; download-button-stuck-disabled on `send_file`
  responses.

### Core-logic smaller items — MEDIUM/LOW
- `resp.text` mis-decodes UTF-8 pages that declare charset only in `<meta>`
  (requests defaults to ISO-8859-1 for `text/html`) → mojibake titles.
- Every URL is fetched twice (crawl then scan); no content-type check before
  feeding to the HTML parser (a linked large PDF is pulled fully into memory).
- `magic_features.py` regex replacement string isn't escaped (`\g`/`\1` in a
  user pronunciation entry → 500 or injected backreference); `\b` boundaries
  never match punctuated terms like `C++`.
- PyMuPDF documents leaked on exception (`fitz.open` without `with`/`finally`) —
  on Windows this locks the file and later cleanup fails.
- Chat/audit history stored in the client cookie session grows past the 4 KB
  limit and the whole session silently vanishes.
- `_run_axe` uses bare `"npx"` in `subprocess.run`, which fails on Windows dev
  (`npx.cmd`), producing an `AXE-UNAVAILABLE` finding on every page locally.
- Nested-table / markdown-table heuristics have off-by-one and unreachable
  branches (`.//table` descendant-only; blank-header check can't fire).
- Several WCAG reference mismatches in `rules.py` produce misleading
  "Understanding SC" links (e.g. a font-size rule linking to the contrast page).

### R1. Residual SSRF: DNS rebinding — LOW (follow-up to fix E)
`_is_public_url` resolves and validates, but a subsequent connect could resolve
again to a different (internal) address. Full protection pins the resolved IP
and connects to it with the original Host header. The fetch happens once so the
window is narrow, but note it for a hardening pass.

### R2. Blind SSRF via the audit webhook callback — MEDIUM
`routes/audit.py` `_fire_webhook` POSTs to any `https://` URL with only a
scheme prefix check (case-sensitive, so `HTTPS://` bypasses it) and no
private-range filter. `allow_redirects=False` limits it, but internal HTTPS
services are reachable, and `share_url` (carrying the report token) is sent to
whatever host the form named. Run it through the same `_is_public_url` gate.

### R3. PageFlow SSRF — MEDIUM
`routes/page_flow.py` fetches `source_url` and returns the extracted text
directly (no zip needed), and hands the URL to a headless-browser subprocess.
Same `_is_public_url` gate belongs here; also reject URLs starting with `-`
before the node argv.

### R4. Upload zip/XML bombs — MEDIUM
`visual_items.py` reads each zip entry fully into memory before the `max_items`
trim and parses `word/document.xml` with `xml.etree` (entity-expansion
vulnerable). Check `ZipInfo.file_size` against per-entry and total caps; use
`defusedxml` here too.
