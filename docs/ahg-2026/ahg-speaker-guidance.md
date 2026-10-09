# AHG 2026 speaker guidance, checked against this workshop

The conference sent four documents to speakers on 9 October 2026: the speaker
orientation outline, the guided notes, the "Speaker Best Practices" slides,
and the CVENT Speaker Resource Center instructions. This is every
recommendation in them, where this workshop meets it, and what only a person
can still do.

Checked 9 October 2026. The materials checked are the deck in all four
formats, the worksheet pack, the run of show, the pocket card, the pre-event
message and the three front-facing guides.

## Accessible, in the digital sense

| Recommendation | Where it is met |
|---|---|
| Materials meet WCAG 2 | The Word deck and the worksheet pack are styled by GLOW's own ACB template code and pass GLOW's own audit with no critical, high or medium findings. The PowerPoint passes GLOW's PowerPoint audit with no findings. Tests hold all three to that bar. The HTML deck is in the axe sweep. |
| Use a checker | GLOW is the checker. `test_workshop_deck_formats.py` and `test_workshop_worksheets.py` run its auditor on every build. |
| Complete manual checks | Not automatable. The screen reader passes in `run-of-show.md` section 5 (NVDA, JAWS, VoiceOver) are the manual check, and they are still outstanding. |
| Fix any issues | Fixed on 9 October: Word headings were 14pt and blue with an italic Heading 4, body text used bold and larger sizes that read as fake headings, margins were 1.25 inches and there were no page numbers. PowerPoint had 32 runs of text under 18pt. The projected HTML had 17px all-caps kickers, a 17px agenda table with italic rows, and printed at 12pt. |

## Accessible, in the design sense

| Recommendation | Where it is met |
|---|---|
| Avoid walls of text | The agenda slide was an 18-row table. It is now three chunks (morning, afternoon, close); the full timetable is on every participant's device. The housekeeping slide was cut to four short bullets, with the rest moved to speaker notes. |
| Chunking | The agenda slide is the three chunks of the day. Each activity is one slide with one question. |
| Practice demos; dry run live activities | Rehearsal items 6 to 10 in `run-of-show.md`: load rehearsal, screen reader passes, a no-AI run, a degraded-network run and a timed dry run. All still outstanding. |
| Have a backup plan | The fallback ladder in `run-of-show.md` section 4. The deck downloads as one self-contained file, and the worksheet pack works offline. |

## Accessible, in the delivery sense

| Recommendation | Where it is met |
|---|---|
| Wear the mic | Slide 1 speaker notes, the pocket card's "say these" list and the run of show: mic on before a word, and repeat every question and volunteer into it. |
| Slow down, the two-thirds rule | Of 420 working minutes, 345 are participant activities. The run of show adds a "talk for a third" rule for each block. |
| Describe visuals | Speaker notes on the join slide (say what is on the screen), the agenda slide (read the three parts aloud), the re-entry slide (read the counts) and the wall (read three aloud). |
| Key point and why care, up front | Slide 1 notes: say the key point before any logistics. |

## Practical and engaging

| Recommendation | Where it is met |
|---|---|
| More hands-on | Eleven activities and three labs; the participant writes for most of the day. |
| Leave with a skill, a tool or a framework | The take-home artifact, the 30-day plan, the agent formula and GLOW itself. |
| Fix pacing | One agenda module drives every surface, with pacing rules for what to compress first. |
| Title and content match | Check this by hand. The deck is titled "Accessibility Agents in Action". The day deliberately provides no AI and no software agents; the "agents" are written instructions for an assistant the participant may or may not use. If the accepted program title or abstract promises running agents, slides 2 and 8 have to say plainly what the day is, early, and the abstract cannot be changed in CVENT. |

## A word on AI

| Recommendation | Where it is met |
|---|---|
| Say what you will and will not cover | Slide 8 speaker notes: covers where AI can help and the review that must follow; does not cover vendor comparisons, building software, or requiring AI. |
| Address ethical and responsible use | Slide 8 (named human review), activity 4 (helpful, risky or human required), and a privacy rule that was missing until 9 October: never paste anything private into an assistant. That rule is now on slide 2, in the worksheet pack, the pre-event message, the front-facing guide and the run of show. |
| Do not alienate the hesitant, or the advocates | Slide 8 notes: name the concerns once, without dwelling on them. AI is optional all day, and nothing is missing without it. |
| Say how this differs from the other 15+ AI sessions | Slide 8 notes: it is about people making more people who can, with AI optional throughout. |
| Keep the emphasis on accessibility | Slides 6, 8 and 30. |

## Logistics

| Recommendation | Where it is met |
|---|---|
| Save time for the session evaluation | New last block, 4:25 to 4:30, in the agenda module, so every surface shows it. Slide 30 asks for it, and the proctor runs it. It took five minutes from the peer review round. |
| Bring your own laptop, charger and adaptors | Pocket card checklist. |
| Visit the room ahead of time | Pocket card checklist. |
| BYOD: attendees may not have admin rights | Nothing to install. Slide 3, the pre-event message and the run of show say so. |
| Times are Mountain Time | The pre-event message, the pocket card, the run of show and the front-facing guide. |
| Upload materials to CVENT (DOC, DOCX, PPTX, PDF; under 250 MB) | Pre-flight item 4 in the run of show, and the pocket card checklist. `slides.pptx` and `slides.docx` qualify; the worksheet pack is a DOCX. |

## Only a person can do these

1. Compare the deck title and the first two slides with the accepted title and
   abstract in CVENT, and decide whether slide 2 needs to say more.
2. Upload `slides.pptx`, `slides.docx` and the worksheet pack in CVENT under
   My Tasks, and check the session details there for typesetting errors.
3. Update the CVENT profile: photo, bio, email.
4. Get the date, room, proctor's name and session type, and fill in the
   pocket card.
5. Run the screen reader passes and the timed dry run. They are the manual
   checks the guidance asks for, and nothing here replaces them.
