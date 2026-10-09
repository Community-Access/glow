# AHG 2026 pocket card

Print this. Fold it once. Put it in a pocket. Fill in every ALL-CAPS blank
before you leave for the conference.

---

## The event

- Date: DATE
- Room: ROOM
- Doors / setup from: TIME
- Wifi network and password: NETWORK / PASSWORD
- Projector input: HDMI or USB-C - CONFIRM
- Venue AV contact: NAME, PHONE

## The addresses

| What | Address |
|---|---|
| Join | `letitglow.app/w/CODE` |
| Any activity | `letitglow.app/w/CODE/1` through `/11` |
| Signage to print | `letitglow.app/workshop/session/SESSION/signage` |
| Facilitator dashboard | `letitglow.app/workshop/session/SESSION/facilitator` |
| Gallery | `letitglow.app/workshop/session/SESSION/gallery` |
| Take-home artifact | `letitglow.app/workshop/session/SESSION/artifact` |
| Commitment wall, 4:25 | `letitglow.app/workshop/session/SESSION/wall` |
| Blank worksheets | `letitglow.app/workshop/worksheets.docx` |
| The deck | `letitglow.app/workshop/session/SESSION/deck` |
| Deck as PowerPoint | same address plus `.pptx` (also `.docx`, `.md`) |
| Pre-flight | `letitglow.app/workshop/session/SESSION/preflight` |

**Facilitator key: write it here, and never put it on a slide.** KEY

## The clock

| Time | Block |
|---|---|
| 8:30 | Welcome, deck slides 1-9 |
| 8:50 | 1. Journey check-in (20) |
| 9:10 | 2. Problem statement (30) |
| 9:40 | 3. Teach vs fix (30) |
| 10:10 | Break (15) - say "return links" again |
| 10:25 | 4. Boundary map (30) |
| 10:55 | 5. Agent formula (35) |
| 11:30 | Lab 1 (45) |
| 12:15 | Lunch - check the AI usage panel |
| 1:15 | Re-entry, room pulse (10) |
| 1:25 | Lab 2, alt text (45) |
| 2:10 | Lab 3, remediation (45) |
| 2:55 | Break (10) |
| 3:05 | Champion Studio (40) |
| 3:45 | Peer review (15) |
| 4:00 | Capstone + artifact (15) |
| 4:15 | Engagement plan (10) |
| 4:25 | Commitment wall (5) |

## Say these out loud

- First ten minutes: "Two ways today. GLOW in a browser does the whole day, no account, no AI. Your own assistant is an upgrade, never a requirement."
- After activity 1 saves, and again at the break: "Send yourself a return link."
- Whenever an assistant comes up: "Paste the text. Do not upload files - free accounts cap uploads and do not cap text."
- At 4:00: "Two minutes on the artifact page. This is what you forward on Monday."

## If something breaks

1. Someone with no device: pair them at the table, or lend them yours.
2. Wifi degraded: keep the sequence; the activities are questions and work said aloud. Point at the pack they downloaded.
3. Site unreachable: run from the downloaded packs and the deck. Collect on paper, type up later.
4. Projector dead: read the join address aloud; the table signage carries it too.

## Before the room fills

- [ ] Pre-flight page opened; every row OK, or you know why not
- [ ] Worksheet pack links sent out in advance (we do not print them)
- [ ] Signage printed and on the tables
- [ ] Deck printed as a handout, and all four formats on the laptop: HTML, PowerPoint, Word, Markdown
- [ ] `slides.pptx` on a USB stick, in case the venue projects from its own machine
- [ ] Facilitator dashboard open and unlocked on your laptop
- [ ] Test email sent from `/admin/queue`
- [ ] You have joined the session yourself from a phone on cellular

## Thirty days later

    flask --app acb_large_print_web.app:create_app workshop-nudge CODE --dry-run
    flask --app acb_large_print_web.app:create_app workshop-nudge CODE --send

Dry run first, always. Read what is about to go out.
