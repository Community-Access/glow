---
title: "AHG 2026 participant documents, in every format"
lang: en
author: "Jeff Bishop, BITS"
description: "Every document a participant receives, the formats each comes in, how they are built and checked, and why some files have no copies."
---

# AHG 2026 participant documents, in every format

The rule for the day: everything a participant receives is theirs in the
format they work in. Every document below comes as Markdown, HTML, Word and
PowerPoint. The Markdown file is the source and the only one anyone edits.

## How the copies are made

One command rebuilds every copy:

```text
python scripts/build_ahg_kit.py --formats-only
```

`python scripts/build_ahg_kit.py` does the same as part of the whole kit.
Pandoc reads the Markdown, the same converter GLOW uses to show the kit
online, and `scripts/ahg_formats.py` writes the three copies beside each
source, with the same name. A README's copies are called `read-me`, because
GitHub and VS Code each show one README and an HTML one can win.

- HTML: one standalone page with nothing loaded from the network. Its
  language and title are declared, it has one h1, every header cell is
  scoped, wide tables scroll in their own named region, and both light and
  dark are defined.
- Word: GLOW's ACB large print styles (Arial 18 point, nothing set in from
  the margin, no italics), real Heading and list styles, real hyperlinks,
  table header rows marked to repeat, alt text on every table, and the
  title and language set on the file.
- PowerPoint: a title slide, then one slide per section, every slide built
  from a real title placeholder and a real body placeholder. A section too
  long for one slide continues as "(2 of 3)", so no two slides share a
  title. Each table gets its own slide, with alt text and a marked header
  row. The language is set on the file and on every run of text.

Office files carry a fixed date rather than the build time, so a rebuild
with the same libraries changes nothing.

## How they are checked

- `python scripts/check_ahg_formats.py` checks all four formats of every
  document: that each copy exists and was built from the Markdown as it is
  now (`formats.json` records the SHA-256 of each source), and the
  structure listed above. It exits non-zero on any failure.
- `web/tests/test_workshop_ahg_formats.py` runs those checks in CI, and runs
  GLOW's own Word and PowerPoint audits over every copy. Nothing at medium
  severity or above is allowed.
- A person still has to open the Word and PowerPoint files in Office, run
  the built-in Accessibility Checker and read a few with a screen reader.
  `golden-readiness.md` at the repository root lists those checks.

## The inventory

Each row is one document a participant receives, where they meet it, and
its four formats. Slide counts include the title slide.

| Document | Where a participant meets it | Formats |
|---|---|---|
| `pre-event-message.md` | Sent three times before the day | md, html, docx, pptx (10 slides) |
| `workshop-frontfacing-guide.md` | The session description, at /workshop/guide | md, html, docx, pptx (11 slides) |
| `kit/README.md` | The first page of the kit | md, html, docx, pptx, as `read-me` |
| `kit/agent-file-principles.md` | Read in block 2, used by /review-my-agent | md, html, docx, pptx |
| `kit/accessibility-agents.md` | Keeping Accessibility Agents after the day | md, html, docx, pptx |
| `kit/accessibility-agents-in-the-kit.md` | Which skills work fully in the kit | md, html, docx, pptx |
| `kit/glossary.md` | The words used today, read before the day | md, html, docx, pptx |
| `kit/step-cards/0-before-the-day.md` | Setup, before the day | md, html, docx, pptx |
| `kit/step-cards/1-why-we-are-here.md` | Block 1 | md, html, docx, pptx |
| `kit/step-cards/2-design-your-agent.md` | Block 2 | md, html, docx, pptx |
| `kit/step-cards/3-your-agent-at-work.md` | Block 3 | md, html, docx, pptx |
| `kit/step-cards/4-ground-it.md` | Block 4 | md, html, docx, pptx |
| `kit/step-cards/5-build-the-office.md` | Block 5 | md, html, docx, pptx |
| `kit/step-cards/6-share-it.md` | Block 6 | md, html, docx, pptx |
| `kit/step-cards/7-take-it-home.md` | Block 7 | md, html, docx, pptx |
| `kit/examples/jordan-faculty-coach.md` | Worked example | md, html, docx, pptx |
| `kit/examples/maria-alternate-format-planner.md` | Worked example | md, html, docx, pptx |
| `kit/examples/sam-remediation-log-keeper.md` | Worked example | md, html, docx, pptx |
| `repo/README.md` | The workshop repository's front page | md, html, docx, pptx, as `read-me` |

`formats.json` has the exact file names and slide count of each.

The slide deck already comes in all four formats from its own generator,
`web/src/acb_large_print_web/workshop_deck.py`: `slides.md`, `slides.html`,
`slides.docx` and `slides.pptx`. See `README.md` in this folder.

## What has no copies, and why

Each row is one kind of file a participant may see, and why it stays in
the one format it has.

| Files | Why one format |
|---|---|
| The agent files: `kit/.github/skills/*/SKILL.md`, `kit/my-agent/SKILL.md`, `kit/examples/agents/*/SKILL.md`, `kit/office-team/*/SKILL.md`, `kit/.github/agents/*.agent.md`, `kit/.github/copilot-instructions.md` | They are instructions an assistant reads, and the format is the point: VS Code finds a skill only as a `SKILL.md` in its own folder. A Word copy could be edited and pasted back with the formatting that breaks it. Participants read them online at letitglow.app/ahg/kit, which shows each as a page |
| The browser path texts, `kit/any-assistant/*.txt` | Each is pasted whole into an assistant. Plain text is the only format that pastes cleanly everywhere, and the page at letitglow.app/ahg/assistant gives each one a Copy button |
| The sample course, `kit/sample-course/*` | It is deliberately inaccessible: every barrier is planted for the agents to find. Converting it would remove or change the barriers. Its checker reports, `sample-course/evidence/*.txt`, are plain text for the same reason as the browser path texts |
| `kit/share-my-agent.html` | The offline copy of a form, not a document |
| `kit/.vscode/*.json`, `kit/ahg-2026.code-profile`, `kit/accessibility-agents-skills.json`, `kit/accessibility-agents-LICENSE.txt` | Settings and data that VS Code or a script reads, and a licence that must travel unchanged |
| `answer-key.md`, `run-of-show.md`, `facilitator-card.md`, `helpers-card.md`, `plan.md` and the rest of this folder | For facilitators, not participants |
| `workshop-frontfacing-exercises.md`, `workshop-frontfacing-utilization.md` | September's Workshop Mode day, which GLOW still offers for other trainings; not part of the AHG day |
| `repo/agents/README.md`, `repo/practice/README.md` | One line each, pointing at the gallery; GitHub shows them in place |
| `for-accessibility-agents/community/ahg-2026/README.md` | Goes into the Accessibility Agents repository, which takes Markdown only |
