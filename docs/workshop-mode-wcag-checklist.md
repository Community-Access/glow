# Workshop Mode WCAG 2.2 AA Checklist

## Purpose
This checklist defines implementation and QA requirements for GLOW Workshop Mode pages, forms, galleries, and facilitator tools.

## Semantic Structure
- One H1 per page.
- Ordered heading hierarchy (H2 after H1, H3 under H2).
- Landmark usage: header, nav, main, footer.
- Skip link to main content appears first and is keyboard focusable.

## Keyboard Access
- All controls operable via keyboard.
- No positive tabindex values.
- Visible focus indicator present and high contrast.
- No keyboard trap in overlays or dialogs.
- Focus returns to trigger after dialog close.

## Forms and Errors
- Every input has a persistent label.
- Required fields are programmatically exposed.
- Error messaging is linked to fields.
- Submit errors provide clear remediation guidance.
- Entered values are preserved after validation failures.

## Tables
- Tables are only used for tabular data.
- Every table has a caption.
- Header cells use proper scope values.
- Reading order remains logical for screen readers.

## Links and Controls
- Link text is descriptive out of context.
- Icon-only controls include accessible names.
- New-tab behavior is announced in link text where applicable.
- Status is never conveyed by color only.

## Visual and Contrast
- Text contrast minimum 4.5:1.
- Large text and UI boundaries minimum 3:1.
- Focus ring contrast minimum 3:1.
- Reflow support at 320px-equivalent width.
- Zoom support to 200 percent without loss of function.

## Dynamic Updates
- Live region used only when content updates asynchronously.
- Polite announcements for non-critical changes.
- No repeated or noisy announcements.
- Focus is not stolen during background updates.

### The live room, specifically

The gallery and facilitator dashboard stream updates from
`/workshop/session/<code>/pulse.stream`. The rules that keep that usable:

- The server sends counts only, never content. There is nothing in the stream
  that would need redacting, and nothing for an announcement to read out.
- New work is announced as a count in a polite status region, once per change.
- The list is never re-rendered, reordered, or extended underneath the reader.
  New work appears only when they activate "Show new submissions", which is an
  ordinary link and an ordinary page load.
- Focus is never moved.
- Where EventSource is unavailable the page polls the JSON endpoint instead;
  the page is correct either way, just not live.

Note for test authors: a page holding an SSE connection never reaches
Playwright's `networkidle`, so the axe helper waits for `load` instead.

### Copy-to-clipboard controls

- The copied text stays on the page in a labelled, read-only field, so the
  button is an accelerator rather than the only route to it.
- The outcome is reported in a status region, not by moving focus.
- Clipboard failure is reported and tells the reader what to do instead.

### QR codes

- Every QR code is accompanied by its address as text, in large type. The
  address is the artifact; the code is the companion. A QR code is no use to
  someone reading the page on the phone they would scan it with, or to anyone
  using a screen reader.
- Each code carries alt text naming the address it encodes.
- Codes render with their own white quiet zone so they stay scannable in dark
  mode.

## Cognitive and Readability
- Plain language instructions.
- Task steps are short and explicit.
- Avoid ambiguous jargon where possible.
- Keep action labels consistent across workflow steps.

## Forms and Errors, Full-Page-Reload Flows
Workshop Mode submits with ordinary form posts, not async updates, so the
"Dynamic Updates" rules below do not cover its status messaging. These do:
- Focus moves to the status region after a submit. Moving focus in response to
  the user pressing Submit is user-initiated, not focus stealing.
- Error lists are never truncated. Every failing field is named.
- Success and error use distinct elements and distinct roles; errors use
  role="alert", never role="status".
- Checkbox and select state round-trips on validation failure, not only text
  inputs. A dropped checkbox can publish something the participant chose to
  keep private.
- Successful posts redirect (Post/Redirect/Get) so refresh cannot duplicate.

## Verification Gates
Automated gate:
- axe-core scan with WCAG 2.2 AA tags must have zero critical and serious issues.
- Workshop routes are covered by `web/e2e/tests/axe-audit.spec.mjs`, which
  seeds a session so the gallery and personal pages are scanned populated.
  Adding a workshop page means adding it to `WORKSHOP_PAGES` in that spec.
- Workshop pages must render inside `base.html`. Standalone documents with
  inline `<style>` are dropped by the app's Content-Security-Policy and lose
  the design system; `tests/test_workshop_routes.py` guards both.

Downloadable artifacts are audited too, in their own way:
- The blank worksheet pack ships as a standalone HTML document with `lang`,
  a heading per activity, and an aria-labelled writing space per field, plus a
  Word version whose Normal style is Arial 18pt.
- The generated agent skill package is plain Markdown.

Manual gate:
- Keyboard-only walkthrough
- Screen reader smoke test
- Contrast spot checks
- Form error and recovery path validation

## Workshop-Specific Human Review Safeguard
Every AI-assisted workflow output must include:
- what AI drafted,
- what human must verify,
- final reviewer owner,
- final acceptance note.
