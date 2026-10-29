# Open Source Accessibility Framework in GLOW

GLOW is adopting GitHub's
[Open Source Accessibility Framework](https://open-source-accessibility.github.io/Open-Source-Accessibility-Framework/)
(source:
[open-source-accessibility/Open-Source-Accessibility-Framework](https://github.com/open-source-accessibility/Open-Source-Accessibility-Framework),
MIT). This page records each of its 24 actions: whether its definition of done
is met by what is in this repository, the evidence, and for recurring actions
the practice that keeps it going.

The framework is for steady, visible improvement. It is not a certification,
and completing an action is not a claim that GLOW is accessible or conforms to
any standard. Progress is self-reported. The project-facing summary is in
[ACCESSIBILITY.md](../ACCESSIBILITY.md#open-source-accessibility-framework).

Definitions of done follow the framework at commit
`b2ea31a2e38cbab3e774e4142575b78876b9b53f` (19 October 2026). An action is
marked done only when every item of its definition of done is met. "Recurring"
means the mechanism is in place and must be repeated; it does not mean it has
already been repeated.

## Summary

Status as of 28 October 2026, by phase.

| Phase | Done | Not done |
|---|---:|---:|
| Foundational | 2 | 0 |
| Workflow | 10 | 0 |
| Testing | 4 | 2 |
| Community | 4 | 2 |
| Total | 20 | 4 |

## Foundational phase

The two actions that make the commitment visible and give accessibility work a
label.

| No. | Action and ID | Status | Evidence |
|---:|---|---|---|
| 1 | Create an ACCESSIBILITY.md (`create-an-accessibilitymd`) | Done | [ACCESSIBILITY.md](../ACCESSIBILITY.md) at the root; its opening says why accessibility matters to GLOW. It replaces the earlier `accessibility.md` crawl log, which moved to [the testing document](accessibility-testing.md#production-crawl-record) |
| 2 | Use an accessibility label to track relevant work (`use-an-accessibility-label-to-track-relevant-work`) | Done; recurring | The `accessibility` label exists and is on every open accessibility issue: #125, #143 to #147. The issue form applies it to every new report |

## Workflow phase

The ten actions that put accessibility into how GLOW is written, reviewed and
maintained.

| No. | Action and ID | Status | Evidence |
|---:|---|---|---|
| 1 | Surface accessibility expectations for contributors (`surface-accessibility-expectations-for-contributors`) | Done; recurring | "Priorities" and "Contributor expectations" in ACCESSIBILITY.md; the "Accessibility" section of [CONTRIBUTING.md](../CONTRIBUTING.md#accessibility) links to them and lists the checks to run |
| 2 | Create an accessible path for reporting accessibility bugs (`create-an-accessible-path-for-reporting-accessibility-bugs`) | Done; recurring | [The accessibility issue form](../.github/ISSUE_TEMPLATE/accessibility.yml) (applies the `accessibility` label, four required fields, severity optional); the in-app feedback form and email as alternatives, in the form, `config.yml`, ACCESSIBILITY.md and CONTRIBUTING.md; triage and response in ACCESSIBILITY.md |
| 3 | Establish a simple accessibility triage approach (`establish-a-simple-accessibility-triage-approach`) | Done; recurring | "Reporting accessibility issues", "Severity" and "How we respond" in ACCESSIBILITY.md. The four severity names match the issue form and the CI gate. No numeric resolution targets are published yet; the section says so |
| 4 | Add an accessibility section to the pull request template (`add-an-accessibility-section-to-the-pull-request-template`) | Done; recurring | [The pull request template](../.github/PULL_REQUEST_TEMPLATE.md): an accessibility checklist for content, interface, output documents and dependencies, drawn from the contributor expectations, asking contributors to tick each item or mark it N/A |
| 5 | Tag beginner-friendly accessibility issues (`tag-beginner-friendly-accessibility-issues`) | Done; recurring | [#143](https://github.com/Community-Access/glow/issues/143), labelled `accessibility` and `good first issue`, with steps, acceptance criteria and where to get help |
| 6 | Tag accessibility issues where you need expert help (`tag-accessibility-issues-where-you-need-expert-help`) | Done; recurring | [#144](https://github.com/Community-Access/glow/issues/144) (screen reader user), [#145](https://github.com/Community-Access/glow/issues/145) (tagged PDF and PDF/UA), [#146](https://github.com/Community-Access/glow/issues/146) (desktop and Office assistive technology testing), labelled `accessibility` and `help wanted`, each naming the expertise and acceptance criteria. #125 also carries both labels |
| 7 | Assign accessibility ownership (`assign-accessibility-ownership`) | Done; recurring | "Ownership and maintenance" in ACCESSIBILITY.md: Jeff Bishop (@accesswatch), with the owner's responsibilities |
| 8 | Make docs accessible by default (`make-docs-accessible-by-default`) | Done; recurring | Every Markdown file in scope passes the accessibility lint (one H1, heading levels, alternative text, link text, table shape, code block languages); two ASCII diagrams now have a description in words. Enforced by the Docs Quality workflow. The user guide, which held two editions of itself, is one edition again (#147). Details in [the documentation review record](accessibility-testing.md#documentation-review-record) |
| 9 | Design accessible interfaces (`design-accessible-interfaces`) | Done; recurring | Interface requirements for the web app, the desktop GUI and the Word add-in under "Contributor expectations" in ACCESSIBILITY.md; reviewed through the pull request checklist and the owner's review; keyboard access, focus and labels checked by axe-core and the keyboard test on the web app, and tracked for the desktop app and add-in in #146 |
| 10 | Evaluate key dependencies and upstream blockers (`evaluate-key-dependencies-and-upstream-blockers`) | Done; recurring | "Dependencies and upstream blockers" in ACCESSIBILITY.md lists the accessibility-relevant dependencies, what each affects, known barriers and workarounds. New dependencies are reviewed (contributor expectations, pull request checklist, owner responsibilities). No upstream blocker is currently known, so item 3 has nothing to link yet. The WeasyPrint limitation was GLOW's own configuration: GLOW now asks for tagged PDF/UA-1 output, and checking it with PAC or veraPDF is tracked in #145 |

## Testing phase

The six actions that make checking repeatable.

| No. | Action and ID | Status | Evidence |
|---:|---|---|---|
| 1 | Add at least one automated accessibility check (`add-at-least-one-automated-accessibility-check`) | Done; recurring | The Accessibility Regression Gate (`.github/workflows/accessibility-regression.yml`) runs axe-core through Playwright and the axe CLI with SARIF upload on every pull request and push that changes `web/`, and weekly; it fails on critical or serious violations. Issues are fixed in the pull request or tracked with the `accessibility` label |
| 2 | Perform a keyboard-only smoke test for core flows (`perform-a-keyboard-only-smoke-test-for-core-flows`) | Done; recurring | The five core flows have keyboard-only records in [the testing document](accessibility-testing.md#keyboard-only-checks), covering focus, operation, visible focus, order and traps. `web/e2e/tests/keyboard.spec.mjs` performs them with keys only and runs in CI; the run record is in the testing document. A person's pass is tracked in #143 |
| 3 | Perform a screen reader spot check for core flows (`perform-a-screen-reader-spot-check-for-core-flows`) | Not done | The checks are documented per core flow, but no person has run them and no test environment is recorded yet. Tracked in #144 (web) and #146 (desktop app and Word add-in) |
| 4 | Perform manual accessibility checks (`perform-manual-accessibility-checks`) | Not done | The checks for keyboard, descriptive and plain language, zoom and reflow, and contrast are documented, with automated evidence for reflow at 200 and 400 percent (`npm run test:reflow`) and contrast (axe-core). Plain and descriptive language, real browser zoom and contrast of images and focus indicators still need a person |
| 5 | Perform accessibility checks for documentation (`perform-accessibility-checks-for-documentation`) | Done; recurring | "Documentation checks" in the testing document covers structure, alternatives, links, captions, tables and code blocks; 70 Markdown files were reviewed on 2026-10-28; what was found was fixed, the duplicated user guide later (#147); the lint runs on every pull request |
| 6 | Document supported environments and known limitations (`document-supported-environments-and-known-limitations`) | Done; recurring | "Supported environments" in ACCESSIBILITY.md lists platforms, browsers, viewports, input methods and assistive technology, separating supported from tested and saying plainly that no screen reader test is recorded. "Known limitations" describes each barrier by its effect, with a workaround and an issue link |

## Community phase

The six actions that involve the people who use and build GLOW.

| No. | Action and ID | Status | Evidence |
|---:|---|---|---|
| 1 | Invite community help on accessibility work (`invite-community-help-on-accessibility-work`) | Done; recurring | Public label searches and non-code ways to help in [CONTRIBUTING.md](../CONTRIBUTING.md#accessibility-work-you-can-pick-up); #143 to #147 have scope, context and acceptance criteria; questions go to the issue or support@community-access.org; the in-app feedback form is the standing feedback channel: submissions reach the maintainers' feedback review page and, when support-hub sync is configured, become tracked issues |
| 2 | Respond constructively to accessibility reports (`respond-constructively-to-accessibility-reports`) | Done; recurring | Item 1: how to respond is documented in "How we respond" in ACCESSIBILITY.md. Items 2 and 3: since 29 October 2026 `.github/workflows/accessibility-reports.yml` acknowledges every report, reminds the owner after 5 business days without a reply, reopens a report closed without a documented outcome (a merged fix or an `Outcome:` line), and invites the reporter to confirm a fix. No accessibility reports from users were on record yet, so the rule covers the first one. The owner, Jeff Bishop, decided that past reports are not reopened |
| 3 | Provide accessible and respectful ways to contribute and collaborate (`provide-accessible-and-respectful-ways-to-contribute-and-collaborate`) | Not done | Asynchronous ways to take part, meeting practice and a private accommodation route are in [CONTRIBUTING.md](../CONTRIBUTING.md#ways-to-take-part); the tool review is below; [the Code of Conduct](../CODE_OF_CONDUCT.md) names dismissiveness toward accessibility concerns and publishing private information, with an enforcement ladder. Still needed: the maintainers' statement that the code of conduct is enforced and that its reporting addresses are current, and a review of the collaboration tools by someone who uses assistive technology |
| 4 | Recognize accessibility contributions publicly (`recognize-accessibility-contributions-publicly`) | Not done | The practice is below. No contribution has yet been credited with recorded consent |
| 5 | Publish accessibility progress updates (`publish-accessibility-progress-updates`) | Done; recurring | The first update is [docs/accessibility-progress.md](accessibility-progress.md), summarised in `CHANGELOG.md`, which the site publishes at `/changelog/`. It lists completed work, remaining work, known barriers and links. The practice, one update per release, is in ACCESSIBILITY.md and below |
| 6 | Share accessibility resources (`share-accessibility-resources`) | Done; recurring | [docs/accessibility-resources.md](accessibility-resources.md): the keyboard and reflow test suites, the issue form, the pull request checklist and the test records, each with the problem it solves, prerequisites, limitations and where it does not apply; maintained by the accessibility owner |

### Collaboration tools review

The tools people use to take part in GLOW, what was checked and the
alternative offered. Reviewed on 28 October 2026 by the maintainer's agent
while adopting the framework; none of these has yet been reviewed by a person
using assistive technology.

| Tool | What was checked | Alternative |
|---|---|---|
| GitHub issues, pull requests and the issue form | GitHub documents its own accessibility at [accessibility.github.com](https://accessibility.github.com/documentation); the GLOW issue form uses plain labels, four required fields and no required disclosure | The feedback form or email |
| GLOW's feedback form (`/feedback/`) | Covered by the axe-core suite on every pull request that changes `web/` | Email |
| Email (support@community-access.org) | Plain text, any client | None needed |
| Meetings | None are required; when held, agenda in advance and notes afterwards, no camera or speaking required | Issues and email |

### Recognition practice

- Before crediting anyone, the maintainer asks how they want to be credited
  (name, handle, or not at all) and records the answer on the issue or pull
  request.
- Credit describes the work, never the person's disability or assistive
  technology.
- Accessibility contributions, including testing, reports and documentation,
  are credited in `CHANGELOG.md` and the release notes for the release that
  ships them, and may be shared in the
  [Open Source Accessibility community shoutouts](https://github.com/orgs/open-source-accessibility/discussions/new?category=shoutout).
- `.github/workflows/accessibility-credits.yml` asks the question on each
  accessibility contribution from outside the maintainers and records the
  answer as a `credit: yes`, `credit: anonymous` or `credit: no` label.
- Release step: before tagging a release, run
  `node .github/scripts/a11y-credits.mjs --since <previous tag>` and paste the
  block it prints into the release's `CHANGELOG.md` section and release notes.
  It lists items labelled `credit: yes` or `credit: anonymous` closed since
  that tag, as code and other contributions, and warns about `credit: asked`
  items with no answer after 14 days: leave those contributors out, or ask
  them again.

### Progress update practice

- One update per release, in [docs/accessibility-progress.md](accessibility-progress.md)
  (newest first) and a short summary in the release's `CHANGELOG.md` section.
- Each update covers what was completed, what is open with its workaround,
  known limitations, and links to issues and pull requests. Counts are counts,
  not scores.
- The framework tracking issue is updated at the same time, checking only the
  actions whose definition of done is met.

## Registration

Registering GLOW in the framework is a public tracking issue in the
framework's repository, opened by the maintainer from the
[Track your project's progress form](https://github.com/open-source-accessibility/Open-Source-Accessibility-Framework/issues/new?template=project-registration.yml).
GLOW's tracking issue is [GLOW, issue 54](https://github.com/open-source-accessibility/Open-Source-Accessibility-Framework/issues/54), opened on 28 October 2026.
This page, ACCESSIBILITY.md and the README link to it, and the README shows the
framework badge it provides.
