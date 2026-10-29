---
title: "AHG 2026 pocket card"
lang: en
author: "Jeff Bishop, BITS"
description: "The facilitator's pocket card for the AHG 2026 workshop."
---

# AHG 2026 pocket card

Print this, fold it once, and keep it in a pocket. Fill in every blank
marked with a dash before you leave for Denver.

## The event

- Monday 16 November 2026, 10:30 AM to 4:30 PM Mountain Time
- Matchless, Hilton Denver City Center
- Setup table from: 10:00
- Proctor: -
- Peak AV contact: -
- Wifi network and password: -
- Projector input, HDMI or USB-C: -

## The addresses

Everything participants need starts from the setup page.

| What | Address |
|---|---|
| Everything, for everyone | letitglow.app/ahg |
| Share page | letitglow.app/ahg/share |
| The pre-workshop survey | letitglow.app/ahg/survey |
| Survey answers, for the team | letitglow.app/ahg/survey/results, with the survey key (in your password manager, never on a slide or card) |
| The kit, online, no unzipping | letitglow.app/ahg/kit |
| The browser path: one text per block | letitglow.app/ahg/assistant |
| Choosing a path, and assistant setup | letitglow.app/ahg/paths |
| The sample course, online | letitglow.app/ahg/site |
| The collection | github.com/Community-Access/ahg-2026, agents folder |
| Anyone who needs a hand | github.com/Community-Access/ahg-2026/issues, label needs-a-hand |
| Commitment for the wall | letitglow.app/w/ahg-2026/11 |
| The wall, to project | letitglow.app/workshop/session/ahg-2026/wall |
| The deck | letitglow.app/workshop/session/ahg-2026/deck |
| End of day, into Accessibility Agents | scripts/promote_to_accessibility_agents.py in the ahg-2026 repository |

Facilitator key: write it here, and never put it on a slide. -

## The clock

The command in each row is what VS Code participants type into Copilot
Chat. Browser path participants paste that block's text from
letitglow.app/ahg/assistant.

| Time | Block | Command |
|---|---|---|
| 10:30 | 1. Why we are here (20) | /ready-check |
| 10:50 | 2. Design your agent (50): version 1 | /design-my-agent |
| 11:40 | 3. Your agent at work (35), then version 2 | /try-my-agent, /review-my-agent |
| 12:15 | Lunch | none |
| 1:15 | 4. Ground it (50), then version 3 | /ground-my-agent, /review-my-agent |
| 2:05 | Break (10) | none |
| 2:15 | 5. Build the office (50), then version 4; Accessibility Agents on the projector last | /run-the-office, /review-my-agent |
| 3:05 | 6. Share it (35), read names as agents arrive; everyone's agents on the projector last | share page |
| 3:40 | 7. Take it home (35) | /my-30-day-plan |
| 4:15 | Commitments (10) | the wall |
| 4:25 | Session evaluation (5) | proctor |

## Say these out loud

- Before a word: mic on. Keep it on. Repeat every question into it.
- First minutes: "Forty thousand files and three people. Here is where we will be at four o'clock."
- Every block: "Here is what you will have at the end." Then show it.
- Often: "Stuck? Start from a ready-made agent and put your name on it. That counts."
- When VS Code fights back: "Take the browser path. Same block, nothing to install."
- Whenever an assistant comes up: "Never paste anything private."
- Whatever you project: say what is on it.
- At 4:25: "Before you go: the session evaluation." Then stop talking.

## If something breaks

1. One person stuck: a helper sits with them; a ready-made agent keeps them moving.
2. Copilot limit reached, or VS Code will not cooperate: the browser path, same block.
3. Wifi slow: one block at a time, demo each step on the projector.
4. GitHub down: collect agent files on a USB stick; share them for people after, credited to them.

## Before the room fills

- [ ] Your laptop, charger and adaptors; the deck open; Copilot signed in
- [ ] ChatGPT signed in on a second browser, block 1 text pasted once this morning
- [ ] A test agent shared through letitglow.app/ahg/share this morning, and the reply arrived
- [ ] The setup page, kit and share page open from a phone on cellular
- [ ] Helpers briefed: who covers which tables, and the fallback ladder
- [ ] Setup table outside the room, with two spare laptops if you can borrow them
- [ ] slides.pptx on a USB stick in case the venue projects from its own machine

## Thirty days later

```text
flask --app acb_large_print_web.app:create_app workshop-nudge ahg-2026 --dry-run
flask --app acb_large_print_web.app:create_app workshop-nudge ahg-2026 --send
```

Dry run first, always. Read what is about to go out.
