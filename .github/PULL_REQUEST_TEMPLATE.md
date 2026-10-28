## What this changes and why

<!-- One or two sentences. Link the issue it closes, if any. -->

## Checks

- [ ] `pytest` passes in `web/` (and in `desktop/` if the desktop core changed)
- [ ] `CHANGELOG.md` has an entry under Unreleased
- [ ] A rule, threshold or severity change is made in every implementation (Python, TypeScript, the agents)

## Accessibility checklist

Accessibility is what GLOW is for. Read the contributor expectations in
[ACCESSIBILITY.md](https://github.com/Community-Access/glow/blob/main/ACCESSIBILITY.md#contributor-expectations)
and tick each item that applies to your change. Write N/A beside an item that
does not apply (for example, the interface items for a documentation-only
change).

### Documentation and content (any change to Markdown, help text or page copy)

- [ ] One H1 per file, and headings do not skip levels
- [ ] Link text is unique and descriptive (no "click here" or "read more")
- [ ] Images have meaningful alternative text or are marked decorative; diagrams have a text description nearby
- [ ] Tables have a header row and a sentence before them
- [ ] Real lists, not typed numbering; code in fenced blocks with a language
- [ ] Meaning is not carried by color, position or styling alone
- [ ] Plain language; abbreviations spelled out on first use
- [ ] Any video has captions and a transcript; audio has a transcript
- [ ] Rendered pages rebuilt with `python scripts/build-doc-pages.py` if a rendered document changed

### Interface (web templates, CSS, JavaScript, the desktop GUI or the Word add-in)

- [ ] `npm run test:axe`, `npm run test:keyboard` and `npm run test:reflow` pass in `web/`, or CI shows them passing
- [ ] Keyboard only: everything reachable and operable, visible focus, logical order, no keyboard trap
- [ ] Every control has a visible label that matches its accessible name; errors are tied to their fields
- [ ] Status changes (progress, errors, completion) are announced, not only shown
- [ ] Text contrast at least 4.5:1, interface components and focus indicators 3:1
- [ ] Targets at least 24 by 24 CSS pixels, or adequately spaced
- [ ] Reflows at 400 percent zoom without sideways scrolling, and respects reduced motion
- [ ] Native elements before ARIA
- [ ] Screen reader spot check done for a new component or a significant change (say which screen reader and browser below)

### Output documents (fixer, converter, template or export changes)

- [ ] The output keeps or improves real headings, lists, tables, alternative text, title and language
- [ ] Tested on a sample document, and the result checked with an accessibility checker (say which below)

### Dependencies

- [ ] A new dependency that shapes what users meet has had a short accessibility review, recorded in ACCESSIBILITY.md under "Dependencies and upstream blockers"

## Accessibility notes

<!-- Optional: what you tested and with what (for example NVDA 2026.3 with Chrome), known limitations, or follow-up issues. -->
