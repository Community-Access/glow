# Accessing Higher Ground 2026 - the whole workshop, in one folder

Everything for the all-day workshop lives here. Nothing workshop-related is
left elsewhere in `docs/`.

## Read in this order

On 9 October 2026 the workshop was redesigned to keep every promise in the
published AHG program. `plan.md` is the current plan. Documents marked
"September" describe the earlier design and are being rewritten;
`scripts/check_material_conformance.py` lists what still disagrees with the
program.

| # | File or folder | What it is |
|---|---|---|
| 1 | `plan.md` | The current plan: every promise in the program and where it is kept, the decisions D1 to D15, the day, and the order of work |
| 2 | `sample-course/` | PSY 101, the course everyone works on, with barriers planted on purpose. `answer-key.md` lists every one |
| 3 | `worked-examples/` | Three finished agents, one per role card, each with all seven steps and a before and after |
| 4 | `kit/` | What participants open in VS Code: the AHG 2026 profile, the welcome page and the agent template |
| 5 | `pre-event-message.md` | The setup checklist participants are sent |
| 6 | `ahg-speaker-guidance.md` | Every recommendation from the AHG speaker orientation, and where it is met |
| 7 | `run-of-show.md`, `facilitator-card.md`, `slides.*` | September; being rewritten for the new day |
| 8 | `plan-2026-09-glow-only.md`, `status-2026-09-21.md`, `readiness-plan.md` | Records of the September design |

## The deck, in four formats

| File | Use it for |
|---|---|
| `slides.html` | Projecting, and reading. Keyboard driven, one linear reading mode, speaker notes, prints one slide per page |
| `slides.pptx` | When someone asks for "the PowerPoint", or the venue projects from their own machine |
| `slides.docx` | When someone wants it in Word with their own screen reader and font settings |
| `slides.md` | Reviewing, diffing, and converting into whatever an institution actually uses |

**All four are generated.** Edit `web/src/acb_large_print_web/workshop_deck.py`,
then regenerate:

    flask --app acb_large_print_web.app:create_app workshop-deck --code <session>

Do not edit the files in place; the next run overwrites them.

The live deck is served by the app and is what you should actually project,
because it carries the room's real join address:

- `/workshop/session/<code>/deck` - with this room's code in it
- `/workshop/deck` - before a session exists
- add `.md`, `.docx` or `.pptx` to any of those for the other formats

### What makes each format accessible

- **HTML** - one heading per slide under one document heading; a "Read as one
  page" mode that turns the deck into a linear document; focus moves to the
  new slide's heading and the change is announced politely; arrow keys, Page
  Up/Down, Home/End; `n` toggles speaker notes; dark and light both defined;
  nothing carried by colour alone; prints with notes.
- **Word** - real Heading 1/2/3 styles, real bullet and number list styles,
  Arial 18pt (ACB large print), table header rows marked as headers so they
  are announced as headers and repeat across pages, and a declared document
  language.
- **PowerPoint** - every slide has a real title placeholder and a real body
  placeholder, filled in that order, because placeholder order is the reading
  order a screen reader announces. Nothing is a floating text box. Tables
  carry alt text and a marked header row. Speaker notes are in the notes
  slide, not dumped onto the slide. Title and language are set on the file.
- **Markdown** - headings, lists and pipe tables only. No layout tricks, so it
  converts cleanly.

Tests hold each of those: `web/tests/test_workshop_deck_formats.py`.

## Reference, for the room and the build

| File | What it is |
|---|---|
| `workshop-frontfacing-guide.md` | The session description, promise, audience and outcomes. Served to participants at `/workshop/guide` |
| `workshop-frontfacing-exercises.md` | The exercise pack. Served at `/workshop/exercises` |
| `workshop-frontfacing-utilization.md` | Deployment and follow-through guide. Served at `/workshop/utilization` |
| `workshop-mode-facilitator-runbook.md` | The product-level runbook: every surface, and what to do when something breaks |
| `workshop-mode-wcag-checklist.md` | Accessibility conformance for the workshop surfaces |
| `workshop-mode-data-model.md` | What is stored, and what is never stored |
| `workshop-mode-implementation-plan.md` | How Workshop Mode was built |
| `RELEASE-v7.3.0-WORKSHOP-MODE.md` | The release notes Workshop Mode shipped with |

The three `workshop-frontfacing-*.md` files are read off disk at runtime and
copied into the container by `web/Dockerfile`. Renaming or moving one breaks
`/workshop/resources/<slug>`; the paths are in `RESOURCE_FILES` in
`web/src/acb_large_print_web/routes/workshop.py`.

## Related, in another repository

`s:/code/agents/docs/CONFORMANCE-AUDIT-2026-09.md` audits the Accessibility
Agents project this session is named after. Four of its items (A1-A4 in
`plan.md`) are on the pre-conference list because they are attendee-visible:
they decide whether someone who installs the extension after the session finds
it working. The rest of that audit waits until December.

## Not in this folder, on purpose

`docs/GLOW-Presentation-Outline.md` is a **different session**: a 45-minute
conference talk that predates Workshop Mode and points at an old address. It
is deliberately not filed here so nobody picks it up in November by mistake.

## One source for the day

The day is defined once, in `web/src/acb_large_print_web/workshop_agenda.py`.
The participant agenda table, the suggested length on every activity page, the
exercise pack, all four deck formats and the facilitator's run-of-show strip
read from it. `web/tests/test_workshop_agenda.py` fails if they drift apart,
and `workshop_agenda.validate()` fails if the blocks stop adding up to the
day. Change a length there, not in eight places.

## Still to verify

- Read `slides.html` end to end with NVDA, in both views.
- Open `slides.pptx` in PowerPoint and run the built-in Accessibility Checker.
- Open `slides.docx` in Word and run the same check.
- Print one copy of each and look at it on paper.
- axe covers the served deck; it has not been run since the deck became
  data-driven, because the Playwright browser binaries are missing on this
  machine.
- In the meantime, `web/tests/test_workshop_page_structure.py` checks what a
  parser can see across 30 workshop pages on every test run: one h1 per page,
  no skipped heading levels, an accessible name on all 115 form controls,
  `scope` on every table header cell, and no empty heading or button. That is
  not a substitute for axe or for a screen reader; it does mean a heading
  level cannot be skipped in a template without a test going red.
