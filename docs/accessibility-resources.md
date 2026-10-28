# Accessibility Resources

Materials from GLOW's accessibility work that other projects can reuse. Each
entry says what problem it solves, what you need to use it, its limits, and
when it does not apply. Everything here is in this repository. The web
package that holds the test suites is declared MIT in `web/pyproject.toml`,
and the text adapted from the Open Source Accessibility Framework and its
toolkit is MIT. The repository has no top-level license file yet, so check
with the maintainers before reusing anything else.

These resources are maintained by GLOW's accessibility owner (see
[Ownership and maintenance](../ACCESSIBILITY.md#ownership-and-maintenance)),
and are reviewed with each release. Report a problem in one of them with the
[accessibility issue form](https://github.com/Community-Access/glow/issues/new?template=accessibility.yml).

## Keyboard-only smoke test for Playwright

[`web/e2e/tests/keyboard.spec.mjs`](../web/e2e/tests/keyboard.spec.mjs)

- **Problem it solves:** axe-core checks a page's structure, but not whether a
  keyboard user can actually get through a task. This test walks each page's
  whole tab sequence and completes the flows with Tab, Enter and Space only.
- **What it checks:** every visible link and control is reached (one radio
  per group); each one looks different when focused; no positive `tabindex`
  and tab order follows document order; the sequence returns to its start and
  Tab never sticks (no trap); the skip link is first and works; and each flow,
  including choosing a file and downloading the result, completes by keyboard.
- **To reuse it:** Playwright with `@playwright/test`. The functions
  `inventory`, `focusState`, `walkTabSequence` and `assertKeyboardContract`
  are independent of GLOW; replace the routes, the selectors and the flows at
  the bottom of the file with your own.
- **Limits:** it compares computed styles, so it proves a focus style exists,
  not that it is easy to see or has 3:1 contrast. It checks tab order against
  document order, not against visual order. It allows a few repeated stops on
  one element for media controls. A page that moves focus on load starts the
  walk from there; the full cycle still covers every element.
- **When it does not apply:** native desktop or mobile apps; custom widgets
  that use arrow keys inside a single tab stop (it checks that they are
  reached, not that their arrow keys work); and anything that needs a person's
  judgement.

## Zoom and reflow check for Playwright

[`web/e2e/tests/reflow.spec.mjs`](../web/e2e/tests/reflow.spec.mjs)

- **Problem it solves:** people who zoom to 200 or 400 percent lose content
  or controls when a page does not reflow. This test loads pages at 640 and
  320 CSS pixels wide, the layouts a 1280 pixel window produces at those zoom
  levels, and fails on sideways scrolling or a lost heading, navigation or
  submit button.
- **To reuse it:** Playwright; change `PAGES`, the navigation name and the
  menu button selector.
- **Limits:** it sets the viewport, which is not the same as browser zoom or
  text-only resizing; it does not detect clipped or overlapping text. Data
  tables and code blocks that scroll inside their own box are allowed, as WCAG
  2.2 success criterion 1.4.10 allows.
- **When it does not apply:** content that genuinely needs two-dimensional
  layout, such as maps and large data tables.

## Accessibility issue form

[`.github/ISSUE_TEMPLATE/accessibility.yml`](../.github/ISSUE_TEMPLATE/accessibility.yml)

- **Problem it solves:** reports that arrive without steps or environment, and
  forms that ask disabled people to disclose more than they need to.
- **What it does:** four required questions in plain words; severity,
  assistive technology, environment and WCAG optional; the `accessibility`
  label applied automatically; and other routes for people who cannot or
  would rather not use GitHub.
- **To reuse it:** replace the "Where" options, the example steps, the
  feedback form and the email address with your project's own.
- **Limits:** GitHub issue forms work with a keyboard and screen readers, but
  some people cannot use GitHub at all; keep an alternative route.

## Pull request accessibility checklist

[`.github/PULL_REQUEST_TEMPLATE.md`](../.github/PULL_REQUEST_TEMPLATE.md)

- **Problem it solves:** accessibility left to the end of review, or to one
  reviewer's memory.
- **What it does:** groups the checks by what changed (content, interface,
  output documents, dependencies), so a contributor ticks only what applies
  and marks the rest N/A.
- **To reuse it:** keep the groups that match what your project ships, and
  replace the commands with your own checks. The "output documents" group fits
  projects that generate files.
- **Limits:** a checklist records intent; the automated checks and a reviewer
  are what confirm it.

## Test records

[`docs/accessibility-testing.md`](accessibility-testing.md)

- **Problem it solves:** not knowing what has been tested, by whom, on what,
  and when, which makes "supported" claims impossible to check.
- **What it holds:** core flows; keyboard, screen reader and manual checks per
  flow; run records that separate automated runs from runs by people and say
  "Not yet run" until someone runs them; and the documentation checks.
- **To reuse it:** replace the core flows with your own three to five key
  tasks, and keep the run record tables.

## Triage and response wording

The "Reporting accessibility issues", "Severity" and "How we respond" sections
of [ACCESSIBILITY.md](../ACCESSIBILITY.md#reporting-accessibility-issues).

- **Problem it solves:** inconsistent triage, and responses that question the
  reporter's experience.
- **What it holds:** four severity levels defined by their effect on a task,
  the same names a CI gate uses for axe-core results; and response
  commitments that never ask for a diagnosis.
- **Limits:** no numeric resolution targets yet; add your own only if your
  project can keep them.
