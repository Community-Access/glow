# Accessibility Progress

Public updates on GLOW's accessibility work, newest first. One update is
published with each release; the practice is described in
[ACCESSIBILITY.md](../ACCESSIBILITY.md#ownership-and-maintenance) and
[the framework record](accessibility-framework.md#progress-update-practice).
Counts are counts, not scores or ratings.

## Accessibility progress, October 2026

GLOW adopted the
[Open Source Accessibility Framework](https://open-source-accessibility.github.io/Open-Source-Accessibility-Framework/)
this month: 19 of its 24 actions are done, as recorded in
[the framework record](accessibility-framework.md).

### Completed

- An [ACCESSIBILITY.md](../ACCESSIBILITY.md) with GLOW's priorities, what we
  ask of contributors, how to report a barrier, how we respond, who owns this
  work, the dependencies that affect accessibility, supported environments and
  known limitations.
- An [accessibility issue form](https://github.com/Community-Access/glow/issues/new?template=accessibility.yml),
  with the in-app feedback form and email as alternatives for anyone who cannot
  or would rather not use GitHub.
- An accessibility checklist in the pull request template.
- A keyboard-only smoke test of the five core flows (finding your way around,
  audit, fix, convert, template) that runs on every pull request that changes
  the web app, alongside the existing axe-core gate. Its first runs passed: every
  link and control on every page in the flows was reachable by Tab, showed a
  focus style, came in reading order, and no page trapped focus.
- A zoom and reflow check at 200 and 400 percent for six core pages, which
  also passed.
- The documentation now passes an accessibility lint on every pull request:
  38 code blocks gained a language, a block of comments that rendered as eight
  top-level headings in the web app README became a real section, and two
  diagrams gained a description in words.
- A record of how GLOW is tested, in
  [docs/accessibility-testing.md](accessibility-testing.md).

### In progress and open

Five issues are open with the `accessibility` label, plus one carried over:

- [#144](https://github.com/Community-Access/glow/issues/144): no screen
  reader test of the web app has been recorded. Help wanted from someone who
  uses a screen reader every day.
- [#146](https://github.com/Community-Access/glow/issues/146): the desktop
  app and the Word add-in have not been tested with assistive technology. Help
  wanted. The web app offers the same functions meanwhile.
- [#145](https://github.com/Community-Access/glow/issues/145): PDFs made
  with WeasyPrint are untagged. Workaround: export PDF from the fixed Word
  document in Word or LibreOffice. Help wanted from someone who knows tagged
  PDF.
- [#147](https://github.com/Community-Access/glow/issues/147): the user guide
  holds two editions of itself. Workaround: use the contents at the top.
- [#143](https://github.com/Community-Access/glow/issues/143): a person's
  keyboard pass of the core flows. A good first issue; no code needed.
- [#125](https://github.com/Community-Access/glow/issues/125): human sign-off
  for the AHG workshop, including screen reader checks.

### Known limitations

See [Known limitations](../ACCESSIBILITY.md#known-limitations) in
ACCESSIBILITY.md.

### Lessons learned

Automated checks were already strong for the web app's pages, but nothing
checked the flows as a keyboard user lives them, and nothing at all covered
the desktop app, the Word add-in or the PDFs GLOW writes. Writing down what
has been tested, separately from what is supported, made those gaps visible.

### How to help

Pick up an issue labelled
[accessibility](https://github.com/Community-Access/glow/issues?q=is%3Aissue+is%3Aopen+label%3Aaccessibility),
or report a barrier with the
[accessibility issue form](https://github.com/Community-Access/glow/issues/new?template=accessibility.yml).
