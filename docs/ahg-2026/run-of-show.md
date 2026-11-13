---
title: "Run of show: Accessibility Agents at AHG 2026"
lang: en
author: "Jeff Bishop, University of Arizona, IT Accessibility Consultant"
description:
  "The AHG 2026 workshop day by the clock, with commands, pacing rules,
  fallbacks and pre-flight."
---

# Run of show: Accessibility Agents at AHG 2026

For the facilitator and helpers. The plan behind this is `plan.md`; the clock
comes from `workshop_agenda.AHG_DAY`, which the deck and every surface read, so
if this page and the deck ever disagree, the deck is right and this page gets
fixed.

- Session: Accessibility Agents: Building Human-Centered AI Workflows for
  Trusted Accessibility Automation at Scale
- When: Monday 16 November 2026, 10:30 AM to 4:30 PM Mountain Time
- Where: Matchless, Hilton Denver City Center
- Format: bring your own Windows or Mac laptop; beginner level
- Participants use one of three paths (`plan.md`, D18): the browser path with
  ChatGPT or another assistant and letitglow.app/ahg/assistant; VS Code on a
  computer with the AHG 2026 profile and the kit; or VS Code for the Web at
  vscode.dev with the kit. Approved public sharing uses a GitHub account;
  otherwise participants keep reviewed work locally. Everyone can use
  GLOW for the evidence and the commitment wall
- Facilitator: Jeff Bishop, University of Arizona, IT Accessibility Consultant,
  with at least one helper per ten participants

## 1. The one thing to hold on to

Everyone wins every block. Each block shows the finished result first, has a
step card and a Copilot command, and has a ready-made fallback in the kit, so
nobody falls behind and stays behind. A participant who starts from a ready-made
agent and adapts it has completed a meaningful exercise. Distinguish an
actual AI run, a written-example exercise and a confirmed public share.
Do not announce an action that the participant did not perform.

## 2. The day, by the clock

Each row is one block. The command is what VS Code participants type into
Copilot Chat; browser path participants paste the same block's text from
letitglow.app/ahg/assistant. The step card has every key and expected result for
both.

| Clock | Minutes | Block                              | Command                                 | Say                                                                                                |
| ----- | ------- | ---------------------------------- | --------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 10:00 | 30      | Setup table open, outside the room | /ready-check                            | "Let's get you ready before we start."                                                             |
| 10:30 | 35      | 1. Why we are here                 | /ready-check                            | "Forty thousand files and three people. Here is where we will be at four o'clock."                 |
| 11:05 | 40      | 2. Design your agent               | /design-my-agent                        | "Pick a card. Bring one real problem, nothing private. Copilot asks, you answer."                  |
| 11:45 | 30      | 3. Your agent at work              | /try-my-agent, then /review-my-agent    | "Catch guesses; asking for evidence is a success. Then version 2."                                 |
| 12:15 | 60      | Lunch                              | none                                    | "You have an agent, and you have already improved it."                                             |
| 1:15  | 50      | 4. Ground it                       | /ground-my-agent, then /review-my-agent | "Real evidence in, claims you can verify out. Version 3."                                          |
| 2:05  | 10      | Break                              | none                                    | "Next, your agent joins a team."                                                                   |
| 2:15  | 50      | 5. Build the office                | /run-the-office, then /review-my-agent  | "Your specialist joins the team. The team works the whole course. Version 4 is the one you share." |
| 3:05  | 35      | 6. Share it                        | letitglow.app/ahg/share, if approved    | "Check permission first. Share your reviewed version, or keep it locally with a follow-up." |
| 3:40  | 35      | 7. Take it home                    | /my-30-day-plan                         | "Small is the point. One workflow, one partner, one safeguard."                                    |
| 4:15  | 10      | Commitments                        | GLOW wall                               | Read three aloud. Do not name anyone.                                                              |
| 4:25  | 5       | Session evaluation                 | proctor                                 | "Before you go: the session evaluation. It shapes next year." Then stop talking.                   |

Working time is 300 minutes, plus the hour for lunch.

### Optional closing demonstration, after the evaluation

If the room can remain open, offer 4:30 to 4:40 for
[ChatGPT Dots and Claude Duet](kit/closing-demo.md). Use its separate reading
slides, `kit/closing-demo.pptx`, and the same fictional evidence in both
products. Demonstrate draft preparation, evidence limits and human approval, not
access to a campus inbox. Rehearse access first; both products have eligibility
limits. A labelled written walkthrough is the fallback.

Do not take time from the 30-day plan, commitments or the 4:25 evaluation. If
the room closes at 4:30, share the demo for later. The standard course does not
require a paid subscription or preview access.

## 3. Pacing rules

- Move on the room, not on the fastest person. When most of the room has their
  "on track" sign, move on; helpers carry the rest.
- Block 2 is the one that runs long. If it does, use the ready-made agent to
  catch up. If five minutes must come from block 7, shorten its demo, never the
  plan-writing, partner review or saving time.
- Never cut the session evaluation or block 6's privacy and permission review.
  Confirmed sharing and a reviewed local copy with a permission follow-up are
  distinct valid outcomes.
- In block 6, with the authors' permission, project the collection, `agents/README.md` in
  Community-Access/ahg-2026, and refresh it as agents arrive; read each name and
  agent title aloud. Helpers watch the issues labelled needs-a-hand and go to
  those people first.
- At the end of block 6, use the eight-minute presenter-led
  [ChatGPT and GLOW MCP capstone](chatgpt-mcp-capstone.md) to show how coworkers
  can use reviewed instructions with shared tools on the fictional PSY 101
  announcement. Replace the optional shared-agent rerun if needed; do not
  extend the block or cut permission review. Preconfigure the account off
  screen. Participants watch, with no new account or paid requirement.
  If time or connectivity fails, show the explicitly labelled saved example.
- In block 5, everyone runs their own team first, then /review-my-agent. The
  last 15 minutes are the full Accessibility Agents project on the projector, on
  the same course, from the skills in the kit. The projector run with every
  shared agent comes at the end of block 6, as a bonus, never as a substitute.
  For it, copy each `agents/<login>/<name>/` folder from the ahg-2026 repository
  into a `room/` folder in your kit; the coordinator adds every agent there to
  the team.

## 4. Delivery, from the AHG speaker orientation

The conference's own guidance, applied to this room. The full mapping is
`ahg-speaker-guidance.md`.

- Wear the mic all day. Repeat every question and every volunteer into it.
- Slow down, and talk for a third. Every block is mostly participants doing.
- Describe what you project. Read tables and reports aloud.
- Key point first: accessibility in higher education scales by making more
  people who can, and agents carry one person's know-how across a whole course.
- Set the AI context on slide 10: what the day covers, what it does not, and the
  privacy rule.
- Give the ready check (slide 7) five full minutes, and walk the kit and the
  website (slides 8 and 9) on the projector, so nobody spends the day looking
  for things.
- Slow down on slides 11 to 13: what makes up an agent, the six answers, and
  what automation cannot decide. Everything after builds on them.
- Every slide in the HTML, Word, PowerPoint and Markdown decks links to its part
  of the kit or the site, so anyone reading along can go straight there. The
  large print handout (`slides-large-print-handout.docx`) is the same slides
  without the notes, every link written out; print a few.
- Every slide inside a block says where it is ("Block 4 of 7, slide 2 of 3"),
  and every hands-on slide says what to do if you are behind. Read the "Behind?"
  line out loud; it is permission, not a footnote.
- Captions, all day. Ask the conference whether CART is booked for the room. If
  not, present from PowerPoint with Slide Show, Always Use Subtitles on, or turn
  on Windows Live Captions (Windows key + Control + L) with microphone audio
  included. Say at 10:30 where the captions are.
- Before lunch, the check-in: letitglow.app/ahg/check-in, two questions, no
  name. Helpers read `/ahg/check-in/results?key=...` (the survey's key) over
  lunch and go first to anyone stuck.
- The last five minutes are the session evaluation. The proctor runs it.

### Block 7: check that the plan can leave the room

Use the 35 minutes as follows: five to show a finished plan, twenty to answer
the eight questions, five for partner review and five to save the plan. Take
commitments at 4:15. A pending baseline or approval gets an owner and next
action, not a made-up answer. If time is short, adapt one worked example rather
than adding tool demonstrations. Each participant explains the trigger, safe
input, draft destination, reviewer role, deadline and campus approval. The
partner checks that a small pilot has a baseline, a day-30 measure and a stop
rule. Use step card 7 and the three worked examples. One approved workflow is
enough; the center does not have to own every campus remediation task.

No approved AI tool, no account or a blocked network: use Word or paper and the
written examples. Do not ask someone to bypass campus policy. Keep drafts local
if sharing approval is pending; arrange later sharing with their permission. Do
not collect student data with the plan or commitment.

## 5. Fallback ladder

Run down this ladder. Do not jump to the bottom.

| What broke                                                        | What you do                                                                                                                                          | What the room hears                              |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| One person's setup                                                | A helper fixes it with them; they use a ready-made agent until it works                                                                              | Nothing. Handle it at the table                  |
| Copilot Free limit reached                                        | Save the latest agent; use another campus-approved assistant, or the written example with a helper                                                   | Nothing                                          |
| VS Code will not install, sign in or open the kit                 | Move to the browser path; nothing to install                                                                                                         | Nothing                                          |
| An assistant asks the participant to log in, or refuses the paste | Use an approved account; if blocked, save the agent and use the written example with a helper                                                        | Nothing                                          |
| A browser path participant's assistant forgets their agent        | Paste the agent as its own message, then the block's text again                                                                                      | Nothing                                          |
| The profile did not import                                        | Open the kit; VS Code offers the recommended extensions; a helper installs them                                                                      | Nothing                                          |
| Conference wifi degrades                                          | Everything except Copilot and GitHub is in the kit already; slow the room to one block at a time and demo each step on the projector                 | "We will do this one together on the screen."    |
| GitHub is unreachable in block 6                                  | With permission, collect only reviewed public agent instructions using an approved transfer method; otherwise participants keep them locally | "Keep the reviewed copy and record the next approval or retry step." |
| Projector fails                                                   | Read the slide aloud; everyone has the step cards in the kit                                                                                         | Nothing                                          |

Use the complete written-example route in `kit/your-day-at-a-glance.md`
when no approved AI works. For a tool switch, preserve the current block,
course filename, actual first answer and subsequent report as well as the
latest agent. Reopen the saved copies before resuming. Do not invent a
before-and-after result if the first answer was lost.

## 6. Pre-flight

Everything here is configuration or rehearsal.

The first table is what must be true before the day works at all.

| #   | Item                                                                                                                                                                         | Done when                                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 1   | Community-Access/ahg-2026 is synced from GLOW (`scripts/sync_ahg_repo.py`), its `WORKSHOP_CODE` variable matches the table cards, and its test issues and agents are cleared | A practice and a real test agent shared through letitglow.app/ahg/share both get their reply within a minute; then deleted |
| 2   | The [workshop landing page](https://letitglow.app/ahg), kit, profile, share page and step cards all work; the [www address](https://www.letitglow.app/ahg) arrives there too | Each opens from a phone and a laptop                                                                                       |
| 3   | The conference session code is set for the commitment wall                                                                                                                   | letitglow.app/w/ahg-2026/11 accepts a commitment                                                                           |
| 4   | The setup message has gone out three times (by 20 October, on 6 November, two days before), with the real links                                                              | Sent, and both links tested on Windows and on a Mac                                                                        |
| 5   | Materials uploaded to the Cvent Speaker Resource Center, under My Tasks: `slides.pptx`, `slides.docx`, and the step cards. DOC, DOCX, PPTX or PDF only, under 250 MB         | The uploads show in My Tasks                                                                                               |

The second table is the rehearsal; the day works badly without it.

| #   | Item                                                                                                                                                        | Done when                                                                                                    |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 6   | The walkthrough in `plan.md` section 16: profile import, Copilot reading the kit, the commands, the share page, all with NVDA, JAWS and VoiceOver           | Every step done by ear, with notes                                                                           |
| 7   | Copilot Free's allowance measured against one participant's full day; Copilot now bills in GitHub AI Credits and publishes no chat count for Free           | The share of the allowance one day uses, written down, with headroom                                         |
| 7a  | Every block run on the browser path in ChatGPT, signed in, and on both VS Code paths                                                                        | `ahg.md` sections 2.7 to 2.12, each path column                                                              |
| 8   | Timed dry run with a second person playing a participant who has never opened VS Code, once on the browser path and once in VS Code                         | Real minutes written beside section 2                                                                        |
| 10  | The pre-workshop survey: `AHG_SURVEY_KEY` is set on the server, the survey went out with the second setup message, and the answers were read on 13 November | `/ahg/survey/results?key=...` opens; paths, access needs and helper requests are in the pocket card's blanks |
| 11  | Captions: CART confirmed with the conference, or PowerPoint subtitles or Windows Live Captions tested on the presenting laptop with the room microphone     | Captions read back a test sentence correctly from the back row                                               |
| 12  | The check-in: `/ahg/check-in` accepts an answer and `/ahg/check-in/results?key=...` shows it                                                                | One test check-in, then the results page read by ear                                                         |
| 9   | Freeze: tag the release, rebuild the kit, print the pocket card                                                                                             | No merges in the final week                                                                                  |

## 6a. After the session: into Accessibility Agents

Before promoting the collection, a facilitator reviews each contribution for
private information, licensing permission and instructions that could change the
intended team behavior. Keep unreviewed contributions out of the live team run;
publication is not an endorsement of an agent's findings.

The program promises every participant commits their agent to the open-source
Accessibility Agents repository. On the day they commit it to the workshop
collection; this step carries every one of them into Accessibility Agents with
its author credited.

1. In a checkout of Community-Access/accessibility-agents, make a branch.
2. From a checkout of Community-Access/ahg-2026, run
   `python scripts/promote_to_accessibility_agents.py ../accessibility-agents`.
3. In the Accessibility Agents checkout: `git add community/ahg-2026`, then
   `git commit -F ../ahg-2026/commit-message.txt`. The message credits every
   author as a co-author, so each name appears in that project's history.
4. Push, open the pull request, and merge it. Then post the link in the ahg-2026
   repository so everyone can find their name.

## 7. Success measures

Check the six outcomes from work participants already made; no extra test:

| Outcome                   | Evidence to check                                                     |
| ------------------------- | --------------------------------------------------------------------- |
| Describe an agent task    | Saved agent names its input, output and reviewer                      |
| Ground and cite           | One finding traced to supplied evidence and a relevant criterion      |
| Recognize checking limits | One manual check with a responsible reviewer                          |
| Explain the team          | Participant can name the handoff to their specialist                  |
| Contribute                | A verified collection link, or a saved draft with a sharing next step |
| Plan campus use           | A saved plan with review, measure, owner and stop rule                |

Record completed, needs help or deferred with permission. Do not count a saved
sharing draft as a completed public contribution.

Collect these. They are the next proposal's evidence.

- Ready checks passed by 11:05.
- Practice agents shared before the day, and real agents shared on it, and how
  many started from a ready-made agent: count the folders in `practice/` and
  `agents/` in the ahg-2026 repository.
- Team reports that name the participant's agent.
- 30-day plans saved, and commitments on the wall.
- Replies to the 30-day follow-up.

Thirty days after:

```text
flask --app acb_large_print_web.app:create_app workshop-nudge ahg-2026 --dry-run
flask --app acb_large_print_web.app:create_app workshop-nudge ahg-2026 --send
```
