---
title: "AHG 2026 participant documents, in every format"
lang: en
author: "Jeff Bishop, University of Arizona, IT Accessibility Consultant"
description:
  "Every document a participant receives, the formats each comes in, how they
  are built and checked, and why some files have no copies."
---

# AHG 2026 participant documents, in every format

The rule for the day: everything a participant receives is theirs in the format
they work in. Every document below comes as Markdown, HTML, Word and PowerPoint.
The Markdown file is the source and the only one anyone edits.

## How the copies are made

One command rebuilds every copy:

```text
python scripts/build_ahg_kit.py --formats-only
```

`python scripts/build_ahg_kit.py` does the same as part of the whole kit. Pandoc
reads the Markdown, the same converter GLOW uses to show the kit online, and
`scripts/ahg_formats.py` writes the three copies beside each source, with the
same name. A README's copies are called `read-me`, because GitHub and VS Code
each show one README and an HTML one can win.

- HTML: one standalone page with nothing loaded from the network. Its language
  and title are declared, it has one h1, every header cell is scoped, wide
  tables scroll in their own named region, and both light and dark are defined.
- Word: GLOW's ACB large print styles (Arial 18 point, nothing set in from the
  margin, no italics), real Heading and list styles, real hyperlinks, table
  header rows marked to repeat, alt text on every table, and the title and
  language set on the file.
- PowerPoint: a title slide, then one slide per section, every slide built from
  a real title placeholder and a real body placeholder. A section too long for
  one slide continues as "(2 of 3)", so no two slides share a title. Each table
  gets its own slide, with alt text and a marked header row. The language is set
  on the file and on every run of text. Wrapped cells receive individual row
  heights. Wide or overlong tables become labelled records over multiple reading
  slides, preserving every column's label and value instead of shrinking text.

Office files carry a fixed date rather than the build time, so a rebuild with
the same libraries changes nothing.

Plain web addresses, email addresses and inline-code URLs become real hyperlinks
in HTML, Word, PowerPoint and the library EPUBs. Recognized bare domains receive
an HTTPS target. Sentence punctuation stays outside the link, explicit Markdown
link labels stay unchanged, and fenced commands stay literal. PDF inherits links
from Word; DAISY inherits the EPUB content. Actual PDF and DAISY reader behavior
still needs a manual check.

## How they are checked

- `python scripts/check_ahg_formats.py` checks all four formats of every
  document: that each copy exists and was built from the Markdown as it is now
  (`formats.json` records the SHA-256 of each source), and the structure listed
  above. It exits non-zero on any failure.
- The same checker compares expected source destinations with live HTML anchors
  and Office hyperlink elements, not just visible URL text or unused
  relationship records.
- `web/tests/test_workshop_ahg_formats.py` runs those checks in CI, and runs
  GLOW's own Word and PowerPoint audits over every copy. Nothing at medium
  severity or above is allowed.
- A person still has to open the Word and PowerPoint files in Office, run the
  built-in Accessibility Checker and read a few with a screen reader.
  `golden-readiness.md` at the repository root lists those checks.

## The inventory

Each row is one document a participant receives, where they meet it, and its
four formats. Slide counts include the title slide.

| Document                                         | Where a participant meets it                                      | Formats                            |
| ------------------------------------------------ | ----------------------------------------------------------------- | ---------------------------------- |
| `pre-event-message.md`                           | Sent three times before the day                                   | md, html, docx, pptx (10 slides)   |
| `workshop-frontfacing-guide.md`                  | The session description, at /workshop/guide                       | md, html, docx, pptx (11 slides)   |
| `kit/README.md`                                  | The first page of the kit                                         | md, html, docx, pptx, as `read-me` |
| `kit/agent-file-principles.md`                   | Read in block 2, used by /review-my-agent                         | md, html, docx, pptx               |
| `kit/accessibility-agents.md`                    | Keeping Accessibility Agents after the day                        | md, html, docx, pptx               |
| `kit/accessibility-agents-in-the-kit.md`         | Which skills work fully in the kit                                | md, html, docx, pptx               |
| `kit/glossary.md`                                | The words used today, read before the day                         | md, html, docx, pptx               |
| `kit/session-in-plain-language.md`               | The workshop in about 150 words, to decide or pass on             | md, html, docx, pptx               |
| `kit/your-day-at-a-glance.md`                    | The seven stops, paths, transitions and what to keep              | md, html, docx, pptx               |
| `kit/write-your-own-agent.md`                    | The full tutorial, for writing agents after the day               | md, html, docx, pptx               |
| `kit/closing-demo.md`                            | Optional Dots and Claude Duet demonstration, after the evaluation | md, html, docx, pptx               |
| `kit/step-cards/0-before-the-day.md`             | Setup, before the day                                             | md, html, docx, pptx               |
| `kit/step-cards/1-why-we-are-here.md`            | Block 1                                                           | md, html, docx, pptx               |
| `kit/step-cards/2-design-your-agent.md`          | Block 2                                                           | md, html, docx, pptx               |
| `kit/step-cards/3-your-agent-at-work.md`         | Block 3                                                           | md, html, docx, pptx               |
| `kit/step-cards/4-ground-it.md`                  | Block 4                                                           | md, html, docx, pptx               |
| `kit/step-cards/5-build-the-office.md`           | Block 5                                                           | md, html, docx, pptx               |
| `kit/step-cards/6-share-it.md`                   | Block 6                                                           | md, html, docx, pptx               |
| `kit/step-cards/7-take-it-home.md`               | Block 7                                                           | md, html, docx, pptx               |
| `kit/examples/jordan-faculty-coach.md`           | Worked example                                                    | md, html, docx, pptx               |
| `kit/examples/maria-alternate-format-planner.md` | Worked example                                                    | md, html, docx, pptx               |
| `kit/examples/sam-remediation-log-keeper.md`     | Worked example                                                    | md, html, docx, pptx               |
| `repo/README.md`                                 | The workshop repository's front page                              | md, html, docx, pptx, as `read-me` |

`formats.json` has the exact file names and slide count of each.

The slide deck already comes in all four formats from its own generator,
`web/src/acb_large_print_web/workshop_deck.py`: `slides.md`, `slides.html`,
`slides.docx` and `slides.pptx`. See `README.md` in this folder.

## The library: PDF, EPUB and DAISY as well

`scripts/build_ahg_library.py` builds the AHG 2026 resource library, one folder
(`S:\ahg` by default) holding every document above, the deck and the four
facilitator documents in seven formats, each in its own folder under one base
name. It copies the four formats from here and makes three more:

- PDF: Word's own export of the Word file, run in the background, with "Document
  structure tags for accessibility" and "Create bookmarks using headings" both
  on. Never print to PDF. The build adds the PDF/UA identifier and table header
  scope omitted by Word, then veraPDF checks each one against PDF/UA-1 and
  GLOW's PDF audit runs too. Failures stop the build; passing machine checks
  does not replace manual reading review. Each link's text is its ScreenTip in
  the Word copies, which Word writes as the link's description in the PDF.
- EPUB 3: Pandoc from the Markdown, without its front matter, with the HTML
  copies' styles and EPUB Accessibility 1.1 metadata (text only, structural
  navigation, table of contents, reading order, no hazards, a summary, and
  conformance to WCAG 2.2 Level AA). Ace by DAISY must find nothing serious or
  critical, and EPUBCheck no errors.
- DAISY 2.02 and DAISY 3: DAISY Pipeline 2 from the EPUB, text only. Each
  conversion runs with the Pipeline's own validation set to stop on a problem;
  then its DAISY 2.02 validator checks the NCC book and its DTBook validator the
  DAISY 3 text.

The sample course and the browser path texts are copied as they are, for the
reasons in the next section. `scripts/check_ahg_library.py` then checks that
every document has every format, that every file is in the manifest with its
SHA-256, that every link in the front door resolves, that the conference folder
holds only DOCX, PPTX and PDF under 250 MB, and runs axe-core in Edge over every
page at 1280 and 320 pixels.

## What has no copies, and why

Each row is one kind of file a participant may see, and why it stays in the one
format it has.

The optional tester walkthroughs in `kit/manual-walkthroughs/` are rehearsal
scripts, not additional participant lessons. Each comes as Markdown and
self-contained HTML with complete inputs, expected outputs and blank result
fields. The short verification sequence is `manual-verification.txt` beside
this document; matching observed rehearsal copies live in `S:\ahgtest`.

| Files                                                                                                                                                                                                             | Why one format                                                                                                                                                                                                                                                                                          |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The agent files: `kit/.github/skills/*/SKILL.md`, `kit/my-agent/SKILL.md`, `kit/examples/agents/*/SKILL.md`, `kit/office-team/*/SKILL.md`, `kit/.github/agents/*.agent.md`, `kit/.github/copilot-instructions.md` | They are instructions an assistant reads, and the format is the point: VS Code finds a skill only as a `SKILL.md` in its own folder. A Word copy could be edited and pasted back with the formatting that breaks it. Participants read them online at letitglow.app/ahg/kit, which shows each as a page |
| The browser path texts, `kit/any-assistant/*.txt`                                                                                                                                                                 | Each is pasted whole into an assistant. Plain text is the only format that pastes cleanly everywhere, and the page at letitglow.app/ahg/assistant gives each one a Copy button                                                                                                                          |
| The sample course, `kit/sample-course/*`                                                                                                                                                                          | It is deliberately inaccessible: every barrier is planted for the agents to find. Converting it would remove or change the barriers. Its checker reports, `sample-course/evidence/*.txt`, are plain text for the same reason as the browser path texts                                                  |
| `kit/share-my-agent.html`                                                                                                                                                                                         | The offline copy of a form, not a document                                                                                                                                                                                                                                                              |
| `kit/.vscode/*.json`, `kit/ahg-2026.code-profile`, `kit/accessibility-agents-skills.json`, `kit/accessibility-agents-LICENSE.txt`                                                                                 | Settings and data that VS Code or a script reads, and a licence that must travel unchanged                                                                                                                                                                                                              |
| `answer-key.md`, `run-of-show.md`, `facilitator-card.md`, `helpers-card.md`, `plan.md` and the rest of this folder                                                                                                | For facilitators, not participants                                                                                                                                                                                                                                                                      |
| `workshop-frontfacing-exercises.md`, `workshop-frontfacing-utilization.md`                                                                                                                                        | September's Workshop Mode day, which GLOW still offers for other trainings; not part of the AHG day                                                                                                                                                                                                     |
| `repo/agents/README.md`, `repo/practice/README.md`                                                                                                                                                                | One line each, pointing at the gallery; GitHub shows them in place                                                                                                                                                                                                                                      |
| `for-accessibility-agents/community/ahg-2026/README.md`                                                                                                                                                           | Goes into the Accessibility Agents repository, which takes Markdown only                                                                                                                                                                                                                                |
