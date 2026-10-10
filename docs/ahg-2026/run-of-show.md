---
title: "Run of show: Accessibility Agents at AHG 2026"
lang: en
author: "Jeff Bishop, BITS"
description: "The AHG 2026 workshop day by the clock, with commands, pacing rules, fallbacks and pre-flight."
---

# Run of show: Accessibility Agents at AHG 2026

For the facilitator and helpers. The plan behind this is `plan.md`; the
clock comes from `workshop_agenda.AHG_DAY`, which the deck and every surface
read, so if this page and the deck ever disagree, the deck is right and this
page gets fixed.

- Session: Accessibility Agents: Building Human-Centered AI Workflows for
  Trusted Accessibility Automation at Scale
- When: Monday 16 November 2026, 10:30 AM to 4:30 PM Mountain Time
- Where: Matchless, Hilton Denver City Center
- Format: bring your own Windows or Mac laptop; beginner level
- Participants use: VS Code with the AHG 2026 profile, GitHub Copilot Free,
  their own GitHub account, the agent kit, and GLOW for the evidence and the
  commitment wall
- Facilitator: Jeff Bishop, with at least one helper per ten participants

## 1. The one thing to hold on to

Everyone wins every block. Each block shows the finished result first, has
a step card and a Copilot command, and has a ready-made fallback in the kit,
so nobody falls behind and stays behind. A participant who starts from a
ready-made agent and puts their name on it has still built an agent, run a
team and opened a pull request. Say so out loud, more than once.

## 2. The day, by the clock

Each row is one block. The command is what participants type into Copilot
Chat; the step card has every key and expected result.

| Clock | Minutes | Block | Command | Say |
|---|---|---|---|---|
| 10:00 | 30 | Setup table open, outside the room | /ready-check | "Let's get you ready before we start." |
| 10:30 | 20 | 1. Why we are here | /ready-check | "Forty thousand files and three people. Here is where we will be at four o'clock." |
| 10:50 | 60 | 2. Design your agent | /design-my-agent | "Pick a card. Bring one real problem, nothing private. Copilot asks, you answer." |
| 11:50 | 25 | 3. Your agent at work | /try-my-agent | "It will guess a little. That is the setup for this afternoon." |
| 12:15 | 60 | Lunch | none | "You have an agent. That was the hard part." |
| 1:15 | 55 | 4. Ground it | /ground-my-agent | "Real evidence in, cited answers out. Watch it stop guessing." |
| 2:10 | 10 | Break | none | "Next, your agent goes public. Nicely." |
| 2:20 | 40 | 5. Share it | the share page | "Buttons only. Your pull request, your name." |
| 3:00 | 45 | 6. Build the office | /run-the-office | "Your specialist joins the team. The team works the whole course." |
| 3:45 | 30 | 7. Take it home | /my-30-day-plan | "Small is the point. One workflow, one partner, one safeguard." |
| 4:15 | 10 | Commitments | GLOW wall | Read three aloud. Do not name anyone. |
| 4:25 | 5 | Session evaluation | proctor | "Before you go: the session evaluation. It shapes next year." Then stop talking. |

Working time is 300 minutes, plus the hour for lunch.

## 3. Pacing rules

- Move on the room, not on the fastest person. When most of the room has
  their "on track" sign, move on; helpers carry the rest.
- Block 2 is the one that runs long. If it does, take five minutes from
  block 7, never from blocks 5 or 6.
- Never cut the session evaluation, and never cut block 5: the pull request
  is the capstone the program promised.
- In block 5, merge pull requests on the projector as they arrive, and read
  each name and agent title aloud.
- In block 6, everyone runs their own team first. The projector run with
  every merged agent comes at the end of the block, as a bonus, never as a
  substitute.

## 4. Delivery, from the AHG speaker orientation

The conference's own guidance, applied to this room. The full mapping is
`ahg-speaker-guidance.md`.

- Wear the mic all day. Repeat every question and every volunteer into it.
- Slow down, and talk for a third. Every block is mostly participants doing.
- Describe what you project. Read tables and reports aloud.
- Key point first: accessibility in higher education scales by making more
  people who can, and agents carry one person's know-how across a whole
  course.
- Set the AI context on slide 6: what the day covers, what it does not, and
  the privacy rule.
- The last five minutes are the session evaluation. The proctor runs it.

## 5. Fallback ladder

Run down this ladder. Do not jump to the bottom.

| What broke | What you do | What the room hears |
|---|---|---|
| One person's setup | A helper fixes it with them; they use a ready-made agent until it works | Nothing. Handle it at the table |
| Copilot Free limit reached | Pair with a neighbor for the rest of the block | Nothing |
| The profile did not import | Open the kit; VS Code offers the recommended extensions; a helper installs them | Nothing |
| Conference wifi degrades | Everything except Copilot and GitHub is in the kit already; slow the room to one block at a time and demo each step on the projector | "We will do this one together on the screen." |
| GitHub is unreachable in block 5 | Collect agent files from the kit on a USB stick; open the pull requests together after the session | "Your agent still goes in with your name on it." |
| Projector fails | Read the slide aloud; everyone has the step cards in the kit | Nothing |

## 6. Pre-flight

Everything here is configuration or rehearsal.

The first table is what must be true before the day works at all.

| # | Item | Done when |
|---|---|---|
| 1 | The `community/ahg-2026` folder exists in the Accessibility Agents repository, and you can merge pull requests into it | A test pull request from the share page merges |
| 2 | letitglow.app/workshop/ahg-2026 serves the setup page, the kit, the profile and the share page | Each opens from a phone and a laptop |
| 3 | The conference session code is set for the commitment wall | letitglow.app/w/ahg-2026/11 accepts a commitment |
| 4 | The setup message has gone out three times (by 20 October, on 6 November, two days before), with the real links | Sent, and both links tested on Windows and on a Mac |
| 5 | Materials uploaded to the Cvent Speaker Resource Center, under My Tasks: `slides.pptx`, `slides.docx`, and the step cards. DOC, DOCX, PPTX or PDF only, under 250 MB | The uploads show in My Tasks |

The second table is the rehearsal; the day works badly without it.

| # | Item | Done when |
|---|---|---|
| 6 | The walkthrough in `plan.md` section 16: profile import, Copilot reading the kit, the commands, the share page, all with NVDA, JAWS and VoiceOver | Every step done by ear, with notes |
| 7 | Copilot Free's allowance measured against one participant's full day | A number written down, with headroom |
| 8 | Timed dry run with a second person playing a participant who has never opened VS Code | Real minutes written beside section 2 |
| 9 | Freeze: tag the release, rebuild the kit, print the pocket card | No merges in the final week |

## 7. Success measures

Collect these. They are the next proposal's evidence.

- Ready checks passed by 10:50.
- Pull requests opened and merged, and how many started from a ready-made
  agent.
- Team reports that name the participant's agent.
- 30-day plans saved, and commitments on the wall.
- Replies to the 30-day follow-up.

Thirty days after:

```text
flask --app acb_large_print_web.app:create_app workshop-nudge ahg-2026 --dry-run
flask --app acb_large_print_web.app:create_app workshop-nudge ahg-2026 --send
```
