# Accessibility

GLOW (Guided Layout & Output Workflow) exists so that documents work for people
who are blind or have low vision. It audits, fixes and converts Word, Excel,
PowerPoint, PDF, Markdown and ePub files against the ACB and APH large print
guidelines, Microsoft Accessibility Checker rules and WCAG 2.2 AA. A tool that
checks other people's accessibility has to hold itself to the same standard.
Everyone, including people who use a screen reader, screen magnification, high
contrast, voice control, a switch or the keyboard alone, should be able to use
GLOW, read what it reports, read its documentation and contribute to it.

This document covers GLOW's accessibility priorities, what we ask of
contributors, how to report a barrier and how we respond, who owns this work,
the dependencies we rely on, what we test on, and what we know is not yet good
enough. It applies to every part of GLOW: the web app at
[letitglow.app](https://letitglow.app), the desktop app, the Word add-in, the
MCP server and the documents GLOW produces.

We follow the
[Open Source Accessibility Framework](https://open-source-accessibility.github.io/Open-Source-Accessibility-Framework/),
an improvement framework from GitHub and Microsoft. It is not a certification,
and following it is not a claim that GLOW is fully accessible. Our progress is
in [Open Source Accessibility Framework](#open-source-accessibility-framework)
below.

## Priorities

- **Target:** we work toward [WCAG 2.2](https://www.w3.org/TR/WCAG22/) Level AA
  for every interface GLOW has and every document it writes. This target guides
  our work; it is not a claim of verified conformance.
- **Keyboard first.** Every page, dialog and task pane can be used with a
  keyboard alone, with a visible focus indicator, a logical order and no
  traps. The web app has a skip link and labelled landmarks.
- **Screen reader support.** Native HTML and native desktop controls before
  ARIA; every control has a name that matches its visible label; results,
  progress and errors are announced, not only shown.
- **Low vision.** GLOW applies the ACB Large Print styles to itself: Arial,
  large type, flush-left text, underline for emphasis, `rem` units so text
  scales with browser zoom, reflow at 400 percent, WCAG AA contrast, and a
  forced-colors mode.
- **Reports a person can use.** Every finding is in words: a severity shown as
  text, the rule, where it is, and what to do about it. Nothing depends on
  color or position.
- **Accessible output.** The documents GLOW fixes or converts must be more
  accessible than what went in: real headings, lists and tables, alternative
  text, document language and title. Where an output format falls short, we say
  so (see [Known limitations](#known-limitations)).
- **Documentation that works with assistive technology:** one H1 per page, no
  skipped heading levels, descriptive link text, alternative text, and code in
  fenced blocks with a language.

## Contributor expectations

These apply to every pull request. The pull request template has the same list
as a checklist, and [CONTRIBUTING.md](CONTRIBUTING.md#accessibility) says where
to start.

- **Testing**
  - Run `pytest` in `web/` (it includes the template guardrails in
    `web/tests/test_landmark_aria_guardrails.py`).
  - For any change to a page, template, stylesheet or script in `web/`, run the
    browser suites in `web/`: `npm run test:axe` (axe-core, WCAG 2.2 AA tags),
    `npm run test:keyboard` (the keyboard-only smoke test) and
    `npm run test:reflow` (200 and 400 percent zoom). CI runs all three.
  - Do one keyboard-only pass of what you changed: everything reachable with
    Tab and Shift+Tab, everything operable with Enter, Space and the arrow
    keys, focus always visible, the order logical, and no keyboard trap. You
    can move into and out of every dialog, menu, details panel and editor.
  - For a new component or a significant change to what a page says or
    announces, spot-check it with a screen reader: headings and landmarks,
    names that match their purpose, states (expanded, selected, checked),
    lists announced as lists, and status messages announced (upload progress,
    errors, completed jobs). Say what you tested with in the pull request.
- **Interfaces** (web templates, the desktop GUI, the Word add-in task pane)
  - Every control has a visible label that matches its accessible name.
  - The focus indicator is visible and has at least 3:1 contrast against what
    is around it.
  - Form errors are tied to their fields (`aria-describedby`,
    `aria-invalid`) and announced; status changes use a live region.
  - Dialogs and the mobile navigation move focus in, keep it there while open,
    close with Escape and return focus to what opened them.
  - Color is never the only way to show meaning; severity badges and states
    carry text.
  - Text contrast is at least 4.5:1, large text and interface components
    3:1, and targets at least 24 by 24 CSS pixels or adequately spaced.
  - Animations respect `prefers-reduced-motion`.
  - In `desktop/`, every wxPython control has a label or `SetName()`, and tab
    order follows the visual order.
  - In `office-addin/`, the task pane works from the keyboard once Office has
    moved focus to it (F6).
- **Documentation and content**
  - One H1 per file, a logical heading hierarchy, and real lists.
  - Unique, descriptive link text; never "click here" or "read more". Vale
    checks this in CI.
  - Meaningful alternative text for every image, or mark it decorative; a text
    description near every diagram, including ASCII diagrams.
  - Tables with a header row and a sentence before them saying what the rows
    are.
  - Code in fenced blocks with a language (`text` for plain output and
    directory trees).
  - Plain language; spell out an abbreviation on first use.
  - Captions and a transcript for any video, a transcript for audio.
- **Dependencies:** a new dependency that shapes what users meet (a UI
  library, a document or PDF engine, a converter) needs a short accessibility
  review before it is adopted; see
  [Dependencies and upstream blockers](#dependencies-and-upstream-blockers).
- **CI/CD:** the Accessibility Regression Gate blocks a pull request that adds
  a critical or serious axe-core violation, a keyboard failure or a reflow
  failure, and the Docs Quality workflow checks Markdown structure. Fix what
  they flag, or explain in the pull request why it cannot be fixed and open an
  issue with the `accessibility` label.
- **Rules stay in sync.** A change to an audit rule, threshold or severity goes
  into every implementation together, as
  [the Copilot instructions](.github/copilot-instructions.md) require.

## Reporting accessibility issues

If anything in GLOW is hard or impossible for you to use, please tell us. We
treat accessibility reports as expertise, not complaints.

- **On GitHub:** open an issue with the
  [accessibility issue form](https://github.com/Community-Access/glow/issues/new?template=accessibility.yml).
  Partial reports are welcome.
- **In GLOW:** use the [feedback form](https://letitglow.app/feedback/) in the
  web app. You do not need a GitHub account.
- **By email,** if GitHub or the form is a barrier for you, or you would rather
  not post publicly: write to
  [support@community-access.org](mailto:support@community-access.org), or to
  the maintainer, [jeff@jeffbishop.com](mailto:jeff@jeffbishop.com). We will
  file the issue for you if you want one, and keep your details private if you
  ask.

Helpful details, all optional:

- What you were trying to do, and what happened instead.
- Where: the page URL, the desktop app screen, the add-in, the MCP tool, or the
  document GLOW produced (attach it only if it holds nothing private).
- Steps to reproduce.
- Your operating system, browser or Word version, and assistive technology,
  with versions.
- A screenshot or recording, if you are comfortable sharing one.
- How much it gets in your way (see [Severity](#severity)).

You never need to tell us about a disability or diagnosis.

### Severity

We use four levels, the same names the CI gate uses for axe-core results.
Reporters do not need to choose one; we assign or confirm it during triage.

- **Critical:** you cannot complete a core task, such as uploading a document,
  reading an audit report, downloading a fixed file or reading GLOW's output.
- **Serious:** you can complete the task only with real difficulty or a
  workaround.
- **Moderate:** the task works, but is confusing, slow or inconsistent.
- **Minor:** a small problem with little effect on getting things done.

These describe barriers in GLOW itself. They are separate from the severities
GLOW gives findings in your documents (Critical, High, Medium and Low).

### How we respond

- We acknowledge every accessibility report promptly, respectfully and
  constructively, and say what happens next.
- We do not ask you to justify your experience or disclose personal
  information. If we need more detail, we ask specific questions about the
  environment and the steps.
- We label the issue `accessibility`, confirm its severity, name its owner and
  say where the work is tracked.
- Where we can, we offer a workaround while a fix is in progress, and explain
  any limitation or dependency outside our control.
- We post an update on the issue whenever its status or expected timing
  changes, and link the pull request that fixes it.
- When a fix lands, we may ask you, or another person affected, to confirm it
  works before we close the issue. We write down the outcome before closing:
  what changed, in which release, or why it cannot change and what to do
  instead.
- We thank you, and credit you in the release notes only in the way you choose,
  or not at all.

Critical and serious barriers come before other work. We do not yet publish
target resolution times; when we do, they will be here.

## Ownership and maintenance

Accessibility is owned by **Jeff Bishop**, project maintainer
([@accesswatch](https://github.com/accesswatch) on GitHub,
[jeff@jeffbishop.com](mailto:jeff@jeffbishop.com)).

The accessibility owner:

- triages accessibility reports, assigns severity and keeps the `accessibility`
  label applied;
- marks suitable issues `good first issue` or `help wanted`, with scope,
  context and acceptance criteria;
- reviews pull requests against the contributor expectations above;
- reviews the accessibility of new dependencies before they are adopted;
- keeps this document, the test records in
  [docs/accessibility-testing.md](docs/accessibility-testing.md) and the
  framework progress current, and publishes a progress update with each
  release;
- escalates unresolved accessibility risks to the project's maintainers.

If ownership changes, this section changes in the same pull request.

## Dependencies and upstream blockers

The third-party components that most affect what people meet in GLOW, what
each one affects, and what we know about it. "No known barrier" means none is
recorded yet, not that none exists.

| Dependency | Affects | Known barriers and mitigation |
|---|---|---|
| Flask and Jinja templates | All web pages | GLOW writes its own HTML and CSS; no UI framework. Tested with axe-core and the keyboard suite |
| [WeasyPrint](https://doc.courtbouillon.org/weasyprint/) | PDF output from Convert, the audit report as PDF, Document Chat export | GLOW asks WeasyPrint for tagged PDF that identifies itself as PDF/UA-1. The tags follow the HTML, so they are only as good as the source document. Checking the output with PAC or veraPDF is tracked in [#145](https://github.com/Community-Access/glow/issues/145) |
| [Pandoc](https://pandoc.org/) | HTML, Word and ePub conversion | No known barrier. Headings, lists and tables come from the source structure |
| [MarkItDown](https://github.com/microsoft/markitdown) | Conversion to Markdown | Text extraction quality depends on the source; image-only PDFs produce little text |
| python-docx, python-pptx, openpyxl | Reading and fixing Office files | No known barrier |
| [DAISY Ace](https://github.com/daisy/ace) (vendored) | ePub accessibility checking | No known barrier |
| [liblouis](https://liblouis.io/) | Braille Studio output | Braille output depends on the chosen table; check it before distribution |
| [wxPython](https://wxpython.org/) | The desktop app's interface | Native controls expose the platform accessibility API; not yet tested with a screen reader ([#146](https://github.com/Community-Access/glow/issues/146)) |
| Office.js and the Word task pane host | The Word add-in | Reaching the task pane is Word's own keyboard behavior (F6); not yet tested with a screen reader ([#146](https://github.com/Community-Access/glow/issues/146)) |
| Kokoro and Piper text to speech | Speech Studio audio | Audio is an alternative format; the source text stays available |

No upstream blocker is currently known: none of these components has an open
upstream accessibility issue that stops GLOW fixing a barrier. When one is
found, it is linked here and tracked in an issue of our own with the
`accessibility` label, with the workaround we offer in the meantime. This list
is reviewed when a dependency is added or upgraded.

## Supported environments

What GLOW supports, and what has been tested. Only environments listed as
tested have been tested.

- **Web app:** a standard HTML application with no browser support policy of
  its own. We aim to support current versions of Chrome, Edge, Firefox and
  Safari on desktop and mobile.
  - **Tested automatically, on every pull request that changes `web/`:**
    Chromium (Chrome for Testing, through Playwright) on Ubuntu Linux; at
    1280 by 720 CSS pixels, at 640 pixels (200 percent zoom), at 320 pixels
    (400 percent zoom) and at a mobile viewport; in light and dark mode.
  - **Input methods tested:** keyboard alone (automatically, see
    [docs/accessibility-testing.md](docs/accessibility-testing.md)) and
    pointer (the regression suite). Touch, voice control and switch access
    have not been tested.
  - The web app works without JavaScript; drag and drop is an extra, never the
    only way to choose a file.
- **Desktop app:** Windows x64, macOS on Apple silicon, and Linux x64 and
  ARM64, as built in [desktop/README.md](desktop/README.md). Not yet tested
  with assistive technology.
- **Word add-in:** Word on Windows and macOS (Word API 1.3 or later), as
  described in [the README](README.md#office-add-in). Not yet tested with
  assistive technology.
- **MCP server:** plain text and JSON output, read in whatever client calls
  it; the client's own interface is outside GLOW.
- **Assistive technology:** GLOW is designed for NVDA, JAWS and Narrator on
  Windows, VoiceOver on macOS and iOS, TalkBack on Android, screen
  magnification and browser zoom. **No screen reader test has been recorded
  yet** for any part of GLOW; see [Known limitations](#known-limitations).

## Known limitations

These are the barriers we know about. Please
[report any we have missed](#reporting-accessibility-issues).

- **No recorded screen reader testing.** Automated tests check structure,
  names, focus and contrast, but nobody has yet recorded a test of the core
  flows with a screen reader, so we cannot say how well uploads, progress
  messages, reports and downloads work when heard. Tracked in
  [#144](https://github.com/Community-Access/glow/issues/144) (web) and
  [#146](https://github.com/Community-Access/glow/issues/146) (desktop app and
  Word add-in). If something does not work for you, the feedback form and
  email above reach a person.
- **The desktop app and the Word add-in have no automated accessibility
  tests.** Only the web app does. Tracked in
  [#146](https://github.com/Community-Access/glow/issues/146). The web app
  offers the same audit, fix and convert functions.
- **PDF output has not been checked with PAC or veraPDF.** PDFs made with
  WeasyPrint are tagged and identify themselves as PDF/UA-1, with headings,
  lists, tables, reading order, a title and a language, and a test checks that
  every PDF path writes them. No one has yet run the output through a PDF/UA
  checker or read it with a screen reader. Tracked in
  [#145](https://github.com/Community-Access/glow/issues/145). If you must
  deliver certified PDF/UA, check the file yourself, or export PDF from the
  fixed Word document in Word or LibreOffice.
- **Feature-gated AI pages are tested only when enabled.** Document Chat, BITS
  Whisperer, the Alt-Text Helper and the AI Playground are off in CI, so the
  automated suites do not reach them. Treat them as untested.
- **Human checks are not yet recorded.** Plain language, how descriptive the
  wording is, real browser zoom and text-only resizing still need a person;
  [#143](https://github.com/Community-Access/glow/issues/143) and the manual
  records in [docs/accessibility-testing.md](docs/accessibility-testing.md)
  track them.
- **The last production crawl was in May 2026,** before the move to
  letitglow.app. It reported no confirmed axe-core violations, and seven
  color contrast results that axe could not decide, on code blocks in the
  deployment guide. They have not been re-checked since; the record is in
  [docs/accessibility-testing.md](docs/accessibility-testing.md#production-crawl-record).

## Open Source Accessibility Framework

We are adopting the
[Open Source Accessibility Framework](https://open-source-accessibility.github.io/Open-Source-Accessibility-Framework/)
in its four phases. Each action counts as done only when its definition of done
is met by what is in this repository; recurring actions are set up and then
repeated. The full record, action by action with evidence, is in
[docs/accessibility-framework.md](docs/accessibility-framework.md), and the
public tracking issue is [GLOW, issue 54](https://github.com/open-source-accessibility/Open-Source-Accessibility-Framework/issues/54). As of
October 2026, 19 of 24 actions:

- **Foundational:** this document; the `accessibility` label.
- **Workflow:** all ten actions: priorities and contributor expectations,
  the issue form and other reporting routes, severity and response, the pull
  request checklist, labelled starter and expert-help issues, an owner,
  accessible documentation checked in CI, interface requirements, and the
  dependency record above.
- **Testing:** automated axe-core, keyboard and reflow checks in CI,
  documentation checks, and supported environments with known limitations.
  The screen reader spot check and the manual checks need people, and are
  next.
- **Community:** an open invitation to help, a published progress update, and
  shared resources. Responding to reports is documented but has no reports to
  show yet; accessible ways to collaborate, and public recognition with
  consent, are next.

## Feedback

To suggest an improvement to this document or to how we work, open an issue or
a pull request, or write to the address above. Thank you for helping make GLOW
usable by everyone.
