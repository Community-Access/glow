# Playwright Regression Suite

This folder contains browser-based regression tests for the GLOW web app.

## Coverage

The suite in [e2e/tests/regression.spec.mjs](e2e/tests/regression.spec.mjs) covers:

- Home page smoke check (including WCAG 2.2 copy)
- Audit upload flow (`/audit`)
- Fix upload flow (`/fix`)
- Export upload flow with file download (`/export`)
- Convert upload flow with file download (`/convert`)
- Template generation download (`/template`)
- Site Audit page scan + artifact links (`/site-audit`)
- BITS Whisperer sample-audio transcription flow (`/whisperer`)
- Static pages smoke checks (`/guidelines`, `/guide`, `/about`, `/changelog`, `/feedback`)

Three accessibility suites run beside it in the Accessibility Regression Gate
workflow:

- [e2e/tests/axe-audit.spec.mjs](tests/axe-audit.spec.mjs) (`npm run test:axe`):
  axe-core against every public page and the workshop pages, failing on any
  critical or serious violation.
- [e2e/tests/keyboard.spec.mjs](tests/keyboard.spec.mjs) (`npm run test:keyboard`):
  the keyboard-only smoke test for the core flows. It walks each page's tab
  sequence and completes the audit, fix and convert flows using only Tab,
  Enter and Space.
- [e2e/tests/reflow.spec.mjs](tests/reflow.spec.mjs) (`npm run test:reflow`):
  the core pages at 320 and 640 CSS pixels wide (400 and 200 percent zoom),
  with no sideways scrolling.

What each one checks, and what still needs a person, is in
[docs/accessibility-testing.md](../../docs/accessibility-testing.md).

## Prerequisites

From [web/package.json](web/package.json) scripts:

- `npm install`
- `npx playwright install`

The upload tests require a DOCX file path. By default the suite uses:

- `d:/code/test.docx`

Override with:

```powershell
$env:E2E_UPLOAD_DOCX="D:/path/to/your/file.docx"
```

The Whisperer regression test requires an audio file path. By default it uses:

- `S:/code/bw/Samples/ronaldreaganchallengeraddressatt3232.mp3`

Override with:

```powershell
$env:E2E_UPLOAD_AUDIO="S:/path/to/your/audio.mp3"
```

When the target environment intentionally gates AI off, the Whisperer regression
test skips cleanly if `/whisperer/` returns `404` or shows the standard
unavailable banner.

## Run

```powershell
npm run test:e2e
```

To run the browser suite against a Dockerized WSL staging stack instead of the
local Flask dev server, point Playwright at the reused server:

```powershell
$env:E2E_BASE_URL="http://127.0.0.1:8000"
$env:E2E_PORT="8000"
npm run test:e2e:report
```

## Generate Issue Report

```powershell
npm run test:e2e:report
```

This writes:

- [e2e/artifacts/ISSUES.md](e2e/artifacts/ISSUES.md)
- [e2e/artifacts/results.json](e2e/artifacts/results.json)
- [e2e/artifacts/junit.xml](e2e/artifacts/junit.xml)
- [e2e/artifacts/html-report/index.html](e2e/artifacts/html-report/index.html)

## Notes

- The Playwright web server is started by [e2e/playwright.config.mjs](e2e/playwright.config.mjs).
- Base URL defaults to `http://127.0.0.1:5100`.
- Override with `E2E_BASE_URL` and `E2E_PORT` when needed.
