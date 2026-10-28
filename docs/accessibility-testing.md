# Accessibility Testing

How GLOW's accessibility is tested: the automated checks that run in CI, the
keyboard, screen reader and manual checks for the core flows, the
documentation checks, and the record of each run. The expectations behind them
are in [ACCESSIBILITY.md](../ACCESSIBILITY.md#contributor-expectations).

Automated checks find likely barriers. They do not replace testing by people,
and above all by people who use assistive technology every day. A check that
has not been run says "Not yet run"; nothing here is a claim of conformance.

## Core flows

The key tasks a new user must be able to complete. They are the flows the
regression suite already treats as core (`web/e2e/tests/regression.spec.mjs`),
and every record below uses them.

1. **Find your way around:** reach the main content and any page from the
   navigation.
2. **Audit a document:** choose a Word document, run the audit, and read the
   report.
3. **Fix a document:** choose a document, run the fix, read the results and
   download the fixed file.
4. **Convert a document:** choose a document, convert it, and download the
   result.
5. **Create a template:** create a Word template and download it.

## Automated checks

Each check, where it runs, and what it covers. All three browser suites run in
the Accessibility Regression Gate workflow
(`.github/workflows/accessibility-regression.yml`) on every pull request and
push to `main` that changes `web/`, and every Monday.

| Check | Command (in `web/`) | What it checks | Blocks a merge when |
|---|---|---|---|
| axe-core in Playwright | `npm run test:axe` | Every public page and the workshop pages, plus interactive states, dark mode and a mobile viewport, against the WCAG 2.0, 2.1 and 2.2 A and AA tags | Any critical or serious violation, or an incomplete result |
| axe-core CLI with SARIF | in the workflow | Seventeen public pages; results uploaded to code scanning as `accessibility-regression` | Any critical or serious violation |
| Keyboard-only smoke test | `npm run test:keyboard` | The five core flows, keyboard only (below) | Any check fails |
| Zoom and reflow | `npm run test:reflow` | Six core pages at 640 and 320 CSS pixels wide (200 and 400 percent zoom) | The page scrolls sideways, or the heading, navigation or submit button is lost |
| Template guardrails | `pytest` | No redundant landmark roles or names in `web/` templates; job progress page semantics | Any test fails |
| Markdown accessibility lint | in the Docs Quality workflow | Heading levels, one H1, image alternative text, link text, table shape, code block languages | Any error |
| Vale | in the Docs Quality workflow | Descriptive link text and plain language in `docs/` and the README | Warnings only |

axe-core's WCAG 2.2 tag covers only target size; the other WCAG 2.2 criteria
need people. The keyboard test compares focus styles; it does not judge whether
an indicator is easy to see. The reflow test sets the viewport width; it does
not test real browser zoom or text-only resizing.

What the automated checks found is fixed or tracked: the gate fails the pull
request, SARIF results appear in code scanning, and anything not fixed in the
same change becomes an issue with the `accessibility` label.

## Keyboard-only checks

Five records, one per core flow. Each is run two ways: automatically on every
pull request by `web/e2e/tests/keyboard.spec.mjs`, and by a person, which is
tracked in [#143](https://github.com/Community-Access/glow/issues/143).

Every record checks that all links and controls in the task:

- can be reached with Tab and Shift+Tab;
- can be operated from the keyboard (Enter, Space, arrow keys where expected);
- show a visible focus indicator with sufficient contrast;
- follow a logical focus order, the same as the reading order;
- have no keyboard trap: focus moves into and out of dialogs, menus, details
  panels and the mobile navigation;

and that the task can be completed end to end. Do not use a mouse or other
pointing device.

### How the automated test checks each point

- **Reached:** it walks the whole tab sequence of each page and requires every
  visible link and control to be in it (one radio per group, as browsers do).
- **Operated:** it completes each flow with keys only: Space or Enter on the
  file input opens the file chooser, Enter submits, Enter on the download
  link or button downloads.
- **Visible focus:** each element reached must look different when focused
  (outline, box shadow, border, background or underline).
- **Order:** no positive `tabindex`, and the tab sequence follows document
  order.
- **No trap:** the sequence comes back round to its start, and Tab always moves
  focus on.
- It also checks that the first Tab reaches "Skip to main content" and that
  Enter on it moves focus to the main content.

### Keyboard: find your way around

Start at <https://letitglow.app/>. Pages: home, then any page from the
navigation.

- [ ] Every link and control can be reached with Tab and Shift+Tab.
- [ ] Every control works from the keyboard.
- [ ] A visible focus indicator is always present and has sufficient contrast.
- [ ] Focus order is logical: no jumps, follows the reading order.
- [ ] No keyboard trap, including the mobile navigation at a narrow width
      (Escape closes it and returns focus to the menu button).
- [ ] The first Tab reaches "Skip to main content", and Enter on it moves to
      the main content.

### Keyboard: audit a document

Start at <https://letitglow.app/audit/>.

- [ ] Every link and control can be reached with Tab and Shift+Tab.
- [ ] Space or Enter on "Upload a document" opens the file chooser.
- [ ] Help panels open and close with Enter or Space.
- [ ] A visible focus indicator is always present and has sufficient contrast.
- [ ] Focus order is logical.
- [ ] No keyboard trap.
- [ ] Enter on "Run Audit" runs the audit, and every link and control in the
      report can be reached and used.

### Keyboard: fix a document

Start at <https://letitglow.app/fix/>.

- [ ] Every link and control, including every fix option, can be reached and
      set from the keyboard.
- [ ] A visible focus indicator is always present and has sufficient contrast.
- [ ] Focus order is logical.
- [ ] No keyboard trap.
- [ ] Enter on "Fix Document" runs the fix, and Enter on "Download" downloads
      the fixed file.

### Keyboard: convert a document

Start at <https://letitglow.app/convert/>.

- [ ] Every link and control, including the output format choices (arrow keys
      within the group), can be reached and set from the keyboard.
- [ ] A visible focus indicator is always present and has sufficient contrast.
- [ ] Focus order is logical.
- [ ] No keyboard trap.
- [ ] Enter on "Convert My Document" converts it, and Enter on the download
      link downloads the result.

### Keyboard: create a template

Start at <https://letitglow.app/template/>.

- [ ] Every link and control can be reached and set from the keyboard.
- [ ] A visible focus indicator is always present and has sufficient contrast.
- [ ] Focus order is logical.
- [ ] No keyboard trap.
- [ ] Enter on "Create Template" downloads the template, or opens the job page
      where "Download result" can be reached and used.

### Keyboard run record

Each run, newest first.

| Date | Run by | Environment | Result |
|---|---|---|---|
| 2026-10-28 | Automated: `npm run test:keyboard`, run while adopting the framework | Chromium 153 (Chrome for Testing) headless, Playwright 1.64, Linux, local Flask server, 1280 by 720 | Pass, 10 of 10 tests, on five runs in a row. Tab stops per page: home 45, audit form 39, audit report 40, fix form 57, fix results 34, convert form 41, conversion complete 31, template form 49; every stop had a visible focus style and every sequence returned to its start |
| Every pull request that changes `web/` | Automated, in the Accessibility Regression Gate | Chromium, Playwright, Ubuntu (GitHub Actions) | See the workflow run on the pull request |
| Not yet run | A person ([#143](https://github.com/Community-Access/glow/issues/143)) | | |

## Screen reader spot checks

An agent or a script cannot do these: they need a person running a real screen
reader. They are tracked in
[#144](https://github.com/Community-Access/glow/issues/144). Use at least one
combination, and record it:

- Windows: NVDA or JAWS, with Chrome, Edge or Firefox.
- macOS: VoiceOver with Safari.
- iOS: VoiceOver with Safari; Android: TalkBack with Chrome.

For each core flow, check:

- [ ] I can navigate the page by headings and landmarks.
- [ ] Controls have clear names that match their purpose ("Upload a
      document", "Run Audit").
- [ ] Custom controls announce their role, name, value and state (expanded,
      selected, checked), including help panels and the mobile menu button.
- [ ] Lists and list items are announced as lists.
- [ ] Dynamic updates are announced: upload and job progress, errors,
      validation, and completion.
- [ ] Reading order is logical, and the report or results page starts in a
      sensible place.
- [ ] The task can be completed end to end, including the download.

### Screen reader run record

| Date | Tested by | Screen reader, browser and operating system, with versions | Flows | Result |
|---|---|---|---|---|
| Not yet run | | | | |

## Manual checks

The visual and language checks, for each core flow. Some can be measured by a
tool; the rest need a person.

- [ ] Keyboard: the task can be completed by keyboard alone (see the keyboard
      records).
- [ ] Alternative text describes each informative image's purpose; decorative
      images are hidden from assistive technology.
- [ ] Page title, headings, input labels and error messages are descriptive.
- [ ] Plain language is used; abbreviations such as ACB, APH and WCAG are
      spelled out on first reference.
- [ ] At 200 percent browser zoom, no information or function is lost.
- [ ] At 400 percent (a 320 CSS pixel wide window), content reflows without
      sideways scrolling or loss of information or function.
- [ ] Text and controls have sufficient contrast, and color is never the only
      way meaning is conveyed, in light mode, dark mode and forced colors.

### Manual checks run record

| Check | Evidence so far | Status |
|---|---|---|
| Keyboard | The keyboard records above | Automated pass; a person has not yet run it |
| Alternative text | axe-core `image-alt` and related rules pass on every page | Automated only; quality in context not yet judged by a person |
| Descriptive titles, headings, labels and errors | axe-core `document-title`, `label` and `heading-order` rules pass | Automated only; wording not yet judged by a person |
| Plain language | Vale's plain-language rule on the documentation | Not yet run on the interface |
| Zoom 200 percent and reflow 400 percent | `npm run test:reflow`, 2026-10-28: 12 of 12 pass (six pages at 640 and 320 CSS pixels, Chromium) | Automated only; real browser zoom and text resizing not yet run |
| Contrast and color use | axe-core `color-contrast`, light and dark mode, gate fails on incomplete results | Automated only; images of text, focus indicator contrast and forced colors not yet checked by a person |

## Desktop app and Word add-in

Neither has automated accessibility tests. Both are tracked in
[#146](https://github.com/Community-Access/glow/issues/146).

### Desktop app

Keyboard only, then with a screen reader (NVDA, JAWS or Narrator on Windows;
VoiceOver on macOS):

- [ ] Every control in the wizard can be reached with Tab and operated with the
      keyboard, in visual order, with visible focus.
- [ ] Every control announces a name that matches its label.
- [ ] Opening a document, running an audit, reading the results, running a fix
      and saving can be done end to end.
- [ ] Progress and completion are announced.

### Word add-in

With the GLOW task pane open in Word (F6 moves focus to the pane):

- [ ] Every button and result in the pane can be reached and operated from the
      keyboard, with visible focus.
- [ ] Results and status messages are announced by the screen reader.
- [ ] An audit and a fix can be completed end to end.

### Desktop and add-in run record

| Date | Tested by | Surface | Environment | Result |
|---|---|---|---|---|
| Not yet run | | | | |

## Documentation checks

The checks for GLOW's documentation, run on every pull request where they can
be automated and by a person before a release.

| Area | How it is checked |
|---|---|
| Structure | Markdown lint: heading levels (MD001), one H1 (MD025). By hand: real lists, not typed numbering |
| Alternatives | Markdown lint: image alternative text (MD045). By hand: a text description near every diagram, including ASCII diagrams |
| Links | Markdown lint (MD059) and Vale: descriptive link text |
| Captions | By hand: captions and a transcript for any video, a transcript for audio. The Markdown linter does not check this |
| Tables | Markdown lint: consistent table shape (MD055, MD056). By hand: a header row and a sentence before the table |
| Code blocks | Markdown lint: every fenced block has a language (MD040). By hand: code as text, not images; long commands explained nearby |

The lint configuration is `.github/a11y.markdownlint-cli2.jsonc`; the Docs Quality
workflow runs it on every Markdown file outside `vendor/`, the sample inputs
and the AHG workshop materials.

### Documentation review record

Reviewed on 2026-10-28, while adopting the framework, by automated lint and a
read-through:

- **Files:** every tracked Markdown file outside `vendor/`, `samples/`, `tmp/`,
  `plan/` and the AHG workshop materials (70 files), including the README,
  CONTRIBUTING.md, ACCESSIBILITY.md, the user guide, the FAQ, the deployment
  guide, `web/README.md`, `desktop/README.md`, the latest release notes and
  the pull request template. The issue form is YAML and was read by hand.
- **Found:** 38 code blocks without a language in nine files; one false
  heading block in `web/README.md` (shell comments outside a code block,
  rendered as eight H1 headings); a second H1 in the user guide, where an
  earlier edition of the guide follows the current one; two ASCII diagrams
  with no description in words. No missing image alternative text, no
  ambiguous link text, no skipped heading levels, no malformed tables.
- **Fixed in the same change:** every code block has a language; the
  `web/README.md` block is a real section; both diagrams have a description
  before them; the user guide's second title is a level-two heading, in the
  Markdown and in the page the web app renders at `/guide/`. The other pages
  the web app renders from Markdown (deployment guide, PRD) were not
  regenerated, because their committed HTML has drifted from the Markdown
  sources and regenerating would drop content; their fixes show on GitHub.
- **Tracked:** the duplicated user guide,
  [#147](https://github.com/Community-Access/glow/issues/147).
- **Captions:** the documentation has no video. The home page's audio (the
  GLOW anthem) has its lyrics on the page.

## Production crawl record

Before this testing document existed, GLOW tracked crawls of the production
site in the root `accessibility.md`. That record is kept here, unchanged in
substance. It dates from May 2026, when the site was at `glow.bits-acb.org`;
it has not been repeated at letitglow.app.

### Crawl scope

A raw Flask route list is not the right accessibility scope by itself. It
includes health checks, downloads, admin-only routes, dynamic token routes, and
feature-gated AI pages that may not be visible or enabled in production. The
scan scope is:

- User-visible navigation and footer links rendered with the current feature
  flags and provider configuration.
- Same-origin HTML pages discovered from those visible links.
- Source-derived route checks only as a completeness backstop, with
  feature-gated, dynamic, download, and internal routes classified separately.

### Latest evidence, May 2026

Sources used:

- urlCheck same-origin crawl of `https://glow.bits-acb.org` with the GLOW automation consent header.
- urlCheck source-derived route probe built from the Flask route map.
- Direct HTTP checks for feature-gated routes.
- Current local feature flags in `instance/feature_flags.json`.

Current feature-gate interpretation:

- `GLOW_ENABLE_AI_WHISPERER` is `false`; BITS Whisperer should not appear in public navigation and `/whisperer/` should not be treated as a public crawl gap while disabled.
- `GLOW_ENABLE_AI_CHAT` is `false`; Document Chat should not appear in public navigation and `/chat/` should not be treated as a public crawl gap while disabled.
- `GLOW_ENABLE_AI_ALT_TEXT` is `true` locally, but the route is also provider-gated by `ai_alt_text_enabled()`. It should be scanned only when it appears in rendered navigation or when production provider configuration enables it.
- `/health` is an orchestration endpoint, not a user-facing HTML page. Do not count it as an accessibility page failure.

### Confirmed issues

Current source status: all known deterministic axe violations from the latest completed crawl have source fixes. Local crawl testing was stopped because it was hanging in this environment; use production or a deployed staging target for ongoing counts.

Latest live production re-scan on May 13, 2026 used urlCheck against `https://glow.bits-acb.org/` with same-origin crawl and the GLOW automation consent header. It discovered 27 URLs, scanned 27 URLs, and reported `0` confirmed axe violations and `0` scanner errors. The previous table/code cleanup reduced `color-contrast` incomplete/manual-review nodes from `39` to `7`; the remaining `7` were all generated deployment guide bash code blocks. A follow-up source fix now renders the inner `pre code` element inline inside the painted `pre` container; verify on production after deployment.

#### 1. Production still showed heading-order issues on `/audit/` and `/template/`

Status: Fixed in source, needs production verification after deploy.

Evidence from latest production crawl:

| URL | Rule | Impact | Nodes |
| --- | --- | --- | --- |
| `https://glow.bits-acb.org/audit/` | `heading-order` | moderate | 1 |
| `https://glow.bits-acb.org/template/` | `heading-order` | moderate | 1 |

Notes:

- These were already fixed in GLOW commits `e3900c2` on `main` and `656d435` on `feature/7.0.0` by promoting top-level in-content headings to `h2`.
- Re-scan production after deployment before reopening code work.

#### 2. Production crawl found old public `.md` links returning 404

Status: Fixed in source, needs production verification after deploy.

Evidence from production crawl before/around deployment:

- `https://glow.bits-acb.org/README.md`
- `https://glow.bits-acb.org/guide/deployment.md`
- `https://glow.bits-acb.org/web/README.md`
- `https://glow.bits-acb.org/guide/prd.md`
- `https://glow.bits-acb.org/prd/deployment.md`

Notes:

- Public docs should link to HTML routes, not raw Markdown files.
- GLOW now has a public `/deployment/` page.
- The source and generated partials were fixed in commits `e3900c2` and `656d435`.
- Direct check later returned `200` for `/deployment/`.

#### 3. Feature-gated routes must not leak into public navigation when disabled

Status: Watch item.

Routes observed as `404` in direct/source-derived checks:

- `/chat/`
- `/whisperer/`
- `/alt-text/`

Current interpretation:

- `/chat/` and `/whisperer/` are not current public gaps because their feature gates are disabled and they were not discovered in the visible homepage crawl.
- `/alt-text/` needs conditional review: scan it only when production renders the Alt-Text Helper link or provider configuration enables `ai_alt_text_enabled()`.

Action:

- Build future scan seed lists from rendered navigation/footer links, not just Flask routes.
- Keep source-route probes, but classify feature-gated routes as disabled/internal unless visible in rendered HTML.

### Manual review items

The latest homepage crawl reported no additional confirmed axe violations beyond the heading-order findings above. It did report incomplete/manual-review checks. The Rules Reference duplicate-ID items have now been fixed in source, and the Quick Start upload panel now uses solid high-contrast backgrounds so axe can calculate text contrast reliably. The latest live production crawl still reports color-contrast incomplete/manual-review nodes on long documentation tables and code blocks.

| Rule | Count | Notes |
| --- | ---: | --- |
| `color-contrast` | 7 | Live production still reports incomplete/manual-review nodes only on `/deployment/` bash code blocks; source now adjusts `pre code` rendering and needs production re-scan after deployment. |
| `duplicate-id-aria` | 1 | Fixed in source by removing the stale duplicate `filter-type` control from Rules Reference. |
| `form-field-multiple-labels` | 1 | Fixed in source by removing the stale duplicate `filter-type` control from Rules Reference. |

Last completed pre-deploy crawl evidence after the first fixes showed `0` confirmed axe violations, `0` crawl 404s after the Markdown link cleanup, and remaining color-contrast incomplete checks only. A final local count was intentionally not used because local crawling was stopped. The live production re-scan also showed `0` confirmed axe violations and `0` scanner errors, but the color-contrast incomplete/manual-review count remains open.

Action:

- Re-run the crawl after deployment and move any remaining items back to confirmed issues only if they reproduce against the updated source.
- Use a production or deployed staging target for the next count, not the local Flask development server.

### Routes excluded from the page crawl

These routes may exist in Flask but should not be counted as public page gaps without additional context:

- Health/status machine endpoints: `/health`.
- Download/export endpoints: `/anthem/download`, `/magic/pronunciation/export.csv`, `/braille/download`, dynamic `/convert/download/...`, dynamic `/audit/share/.../csv`, and similar file-producing routes.
- Dynamic token/job routes that require prior workflow state: `/audit/share/<share_token>`, `/convert/preview/<token>/<filename>`, `/site-audit/jobs/<job_id>`, `/whisperer/retrieve/<token>`, and related routes.
- Disabled feature-gated AI routes: `/chat/`, `/whisperer/`, and any provider-gated AI route that is not rendered in visible navigation.
- Admin-only pages beyond the public sign-in or request-access flows.

### urlCheck status

urlCheck fork: `accesswatch/urlCheck`.

Relevant pushed commits:

- `7af9396` - Adds crawl automation support, generic custom headers, HTTP error capture, non-HTML crawl skipping, and upstream contribution notes.
- `adb4c2d` - Forces modern Edge `--headless=new` when invisible mode is active.

Useful behavior now available:

- `--crawl` recursively discovers same-origin HTML pages until `--crawl-limit`.
- `--crawl` defaults to invisible/headless browsing unless `--authenticate` is set.
- `--header "Name: Value"` sends reusable custom headers.
- `--header-env Name=ENV_VAR` sends environment-backed custom headers for secret values.
- `--glow-consent-token` remains as a GLOW convenience, but the generic header options are the upstream-friendly path for Jamal.
- HTTP errors such as `404` are reported explicitly under failed scans.

### Next scan plan

1. Deploy the latest GLOW commits.
2. Generate a scan seed from rendered production navigation and footer links.
3. Add source-derived public routes only when they are enabled and user-visible.
4. Exclude health, download, dynamic, disabled, and admin-only routes from the normal page accessibility score.
5. Re-run urlCheck crawl and update this file with confirmed violations, 404s, and manual-review items.
