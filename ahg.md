---
title: "AHG 2026 Accessibility Agents: instructions and test plan"
lang: en
author: "Jeff Bishop, BITS"
description: "How to run, rehearse and fully test the AHG 2026 Accessibility Agents workshop before 16 November 2026."
---

# AHG 2026 Accessibility Agents: instructions and test plan

This is the single document for getting the Accessing Higher Ground 2026
workshop from "built" to "tested and ready". Part 1 explains the course and
how to run it. Part 2 is the complete test plan. Part 3 is the walkthrough:
every test in Part 2, in the order to run them, from an empty desk to
sign-off. The workshop is ready when
every test case in Part 2 is marked Pass and the sign-off in section 2.15 is
complete.

Session: Accessibility Agents: Building Human-Centered AI Workflows for
Trusted Accessibility Automation at Scale. Monday 16 November 2026, 10:30 AM
to 4:30 PM Mountain Time, Matchless, Hilton Denver City Center.

## Quick links: every document, site and repository

Everything for the workshop, in one place. Paths are relative to the root of
the GLOW repository, `S:\code\glow` on Jeff's machine, on the `main` branch.

### Live sites

These are the addresses participants, the facilitator and testers use. The
one to give anyone is `letitglow.app/ahg`.

| What | Address |
|---|---|
| The landing page: everything for the conference | `https://letitglow.app/ahg` |
| Choosing a path: the three paths compared, and each assistant's setup | `https://letitglow.app/ahg/paths` |
| The browser path: one text per block, with Copy buttons | `https://letitglow.app/ahg/assistant` |
| Share page: opens the share form with an agent filled in | `https://letitglow.app/ahg/share` |
| Share page, starting on "practice agent" | `https://letitglow.app/ahg/share?practice=1` |
| Share page against a test copy, for rehearsals | `https://letitglow.app/ahg/share?repo=<account>/<repository>` |
| The agent kit, every file readable online, each with a plain-text address | `https://letitglow.app/ahg/kit` |
| One kit file online, and as plain text | `https://letitglow.app/ahg/kit/<path>` and `https://letitglow.app/ahg/kit/raw/<path>` |
| The agent kit, as a zip | `https://letitglow.app/ahg/kit.zip` |
| The sample course online: web page, documents, checker reports | `https://letitglow.app/ahg/site` |
| The AHG 2026 VS Code profile, for Profiles: Import Profile | `https://letitglow.app/workshop/ahg-2026/ahg-2026.code-profile` |
| Step card downloads | `https://letitglow.app/workshop/ahg-2026/step-cards/<n>-<name>.docx` |
| The slides, no consent page | `https://letitglow.app/ahg/slides` |
| The deck for the room, with its join address | `https://letitglow.app/workshop/session/ahg-2026/deck` |
| Commitment for the wall, participant | `https://letitglow.app/w/ahg-2026/11` |
| The commitment wall, to project | `https://letitglow.app/workshop/session/ahg-2026/wall` |
| Facilitator dashboard | `https://letitglow.app/workshop/session/ahg-2026/facilitator` |
| The collection of shared agents | `https://github.com/Community-Access/ahg-2026/blob/main/agents/README.md` |
| Anyone who needs a hand with sharing | `https://github.com/Community-Access/ahg-2026/issues?q=label:needs-a-hand` |
| GLOW health | `https://letitglow.app/health` |
| Help desk, for support mail | `https://helpdesk.community-access.org` |
| Support address given to participants | `support@community-access.org` |

The landing page also answers to `/AHG`, `/ahg2026`, `/ahg-2026`, to
`www.letitglow.app/ahg`, and to the old `letitglow.app/workshop/ahg-2026`.
It opens without GLOW's consent form, as do the kit, profile, share page,
sample course, step cards and slides; the GLOW tools themselves still ask.
These conference pages use their own plain frame, with none of GLOW's
navigation, AI meter or footer links: just the page, a link home to `/ahg`,
the privacy policy and a "Hosted by GLOW" line.

The addresses with `ahg-2026` in a session path work once the conference
code is configured on the server, step 2 of section 1.5.

### The conference

These are the conference's own pages and resources.

| What | Where |
|---|---|
| The published session, number 42876: title, abstract, time, room | `https://accessinghigherground.org/accessibility-agents-building-human-centered-ai-workflows-for-trusted-accessibility-automation-at-scale/` |
| Accepted pre-conference sessions | `https://accessinghigherground.org/accepted-precon-sessions-2026-wtime/` |
| Speaker orientation folder: best practices slides, orientation notes, outline, Cvent instructions | `https://drive.google.com/drive/folders/1-t0S9Uc0vLgCInyvosSqQR89CXLvLczM` |
| Cvent Speaker Resource Center: profile, session details, material uploads | The personal link in the invitation email from AHEAD; it must not be forwarded |

### Repositories and pull requests

The code, the collection, and the history of how the workshop was built.

| What | Where |
|---|---|
| The workshop repository: the share form, the collection, the kit | `https://github.com/Community-Access/ahg-2026` |
| GLOW, where everything is written and built | `https://github.com/Community-Access/glow` |
| Accessibility Agents: the source of the specialists, and where the collection goes at the end of the day, in `community/ahg-2026/` | `https://github.com/Community-Access/accessibility-agents` |
| PR #116, the workshop | `https://github.com/Community-Access/glow/pull/116` |
| PR #117, pages reflow at 320px | `https://github.com/Community-Access/glow/pull/117` |
| PR #118, test report after the merge | `https://github.com/Community-Access/glow/pull/118` |
| Branch `wip/postmark-helpdesk`, the unmerged mail and help desk work | `https://github.com/Community-Access/glow/tree/wip/postmark-helpdesk` |

### Documents for the facilitator

Everything Jeff reads or prints before and on the day.

| Document | What it is |
|---|---|
| `ahg.md` | This file: instructions and the full test plan |
| `ahg-test-report.md` | Results of the test pass, defects and fixes, production check |
| `docs/ahg-2026/README.md` | Index of the workshop folder |
| `docs/ahg-2026/plan.md` | The plan: every program promise and the block that keeps it |
| `docs/ahg-2026/run-of-show.md` | The day by the clock, pacing, fallback ladder, pre-flight |
| `docs/ahg-2026/facilitator-card.md` | The pocket card, with blanks to fill in |
| `docs/ahg-2026/answer-key.md` | Every barrier planted in the sample course |
| `docs/ahg-2026/ahg-speaker-guidance.md` | Every AHG speaker recommendation and where it is met |
| `docs/ahg-2026/pre-event-message.md` | The setup message, sent three times |
| `docs/ahg-2026/slides.html`, `.pptx`, `.docx`, `.md` | The deck in four formats, generated |
| `docs/ahg-2026/workshop-frontfacing-guide.md` | The session description participants read in GLOW |
| `docs/ahg-2026/repo/` | Everything in the workshop repository: share form, automation, README, end-of-day script |
| `docs/ahg-2026/for-accessibility-agents/` | The `community/ahg-2026` folder, ready to copy into Accessibility Agents |

### The participant kit

All in `docs/ahg-2026/kit/`, and inside the downloadable zip.

| Part | What it is |
|---|---|
| `kit/README.md` | The welcome page VS Code opens first |
| `kit/step-cards/0-before-the-day.md` to `7-take-it-home.md` | One card per block and one for setup, each also as Word |
| `kit/examples/maria-alternate-format-planner.md` | Worked example: alternate formats |
| `kit/examples/jordan-faculty-coach.md` | Worked example: faculty coaching |
| `kit/examples/sam-remediation-log-keeper.md` | Worked example: Title II compliance log |
| `kit/examples/agents/` | Six ready-made fallback agents |
| `kit/office-team/` | The eight specialists of the agent team |
| `kit/.github/agents/office-coordinator.agent.md` | The coordinator that runs the team |
| `kit/.github/skills/` | The eight Copilot commands, as agent skills, and all 113 Accessibility Agents skills beside them, copied by `scripts/vendor_accessibility_agents.py` |
| `kit/any-assistant/` | The browser path texts, generated: one per block, the review text, and four Accessibility Agents texts, `aa-*.txt` |
| `kit/accessibility-agents.md` | Accessibility Agents after today: the six entry points, and four ways to keep using it |
| `kit/accessibility-agents-in-the-kit.md` | Generated: which of the 113 skills work fully in the kit, and what the rest do instead |
| `kit/accessibility-agents-skills.json` | Generated: the Accessibility Agents commit the kit carries, and what each skill relies on |
| `kit/accessibility-agents-LICENSE.txt` | Generated: Accessibility Agents' MIT licence, with the commit it covers, which must travel with the copied skills |
| `kit/agent-file-principles.md` | The principles and the twelve-question review checklist that /design-my-agent and /review-my-agent follow |
| `kit/.github/copilot-instructions.md` | The rules Copilot follows in the kit |
| `kit/my-agent/SKILL.md` | The template each participant fills in |
| `kit/sample-course/` | PSY 101, and its checker evidence in `evidence/` |
| `kit/share-my-agent.html` | The offline share page |
| `kit/ahg-2026.code-profile` | The VS Code profile |

### Scripts

Run from the repository root.

| Script | What it does |
|---|---|
| `scripts/build_ahg_sample_course.py` | Rebuilds the sample course |
| `scripts/vendor_accessibility_agents.py <accessibility-agents checkout>` | Copies every Accessibility Agents skill into the kit's `.github/skills`, records the commit, and writes the two generated Accessibility Agents pages |
| `scripts/build_ahg_kit.py` | Rebuilds the kit's agents, evidence, step card Word files and zip |
| `scripts/sync_ahg_repo.py <ahg-2026 checkout>` | Publishes the kit and the repository files to Community-Access/ahg-2026 |
| `scripts/promote_to_accessibility_agents.py`, in the ahg-2026 repository | The end-of-day step: every agent into Accessibility Agents, every author credited |
| `flask --app acb_large_print_web.app:create_app workshop-deck --code ahg-2026` | Regenerates the deck |
| `scripts/ahg_browser_checks.py --base <address>` | The 35 browser checks |
| `scripts/check_ahg_sample_course.py` | Checks all 42 planted barriers are present |
| `scripts/audit_ahg_docs.py` | GLOW's own audit of every document |
| `scripts/check_material_conformance.py` | Checks materials against the program's promises |

### Source code

For changing the workshop itself.

| File | What it holds |
|---|---|
| `web/src/acb_large_print_web/workshop_agenda.py` | The clock, `AHG_DAY` |
| `web/src/acb_large_print_web/workshop_deck.py` | Every slide and speaker note |
| `web/src/acb_large_print_web/routes/workshop.py` | The setup, kit, profile, share and step card pages, at the end of the file |
| `web/src/acb_large_print_web/templates/workshop/ahg_home.html` | The landing page at /ahg |
| `web/src/acb_large_print_web/routes/shortlinks.py` | The /ahg address and its variations |
| `docs/ahg-2026/repo/.github/scripts/accept_agent.py` | The automation that adds each shared agent |
| `web/tests/test_ahg_repo_intake.py` | Tests for that automation |
| `web/src/acb_large_print_web/templates/workshop/ahg_share.html` | The share page |
| `web/tests/test_workshop_ahg_kit.py` | Tests for the kit and its pages |

### The server

Production runs on `lp.csedesigns.com`, as `jeffbis`.

| What | Where |
|---|---|
| GLOW checkout | `~/app`, deployed from `main` by GitHub Actions on merge |
| Caddy configuration | `~/app/web/caddy/Caddyfile` |
| Conference codes and secrets | `~/app/web/.env` (`WORKSHOP_CONFERENCE_CODES_JSON`) |

## Part 1: Instructions

### 1.1 What the course is

A one-day, hands-on workshop for higher education accessibility staff who
are not developers. Each participant designs an accessibility agent in plain
English, puts it to work on a sample course, grounds it in checker evidence
so it cites WCAG 2.2, shares it to the open-source AHG 2026 collection in
their own name (which goes into Accessibility Agents at the end of the day),
adds it to an agent team that works through the whole course, and leaves
with a 30-day plan.

There are three paths into the same day (`plan.md`, D18), and this test plan
runs every block on each:

| Path | The participant uses | Each block starts with |
|---|---|---|
| The browser path | Any browser and an AI assistant, signed in; ChatGPT is the tested one | Copying one text from `/ahg/assistant` and pasting it as one message |
| VS Code on a computer | VS Code 1.143 or later, the AHG 2026 profile, the kit, Copilot Free | A command such as `/ready-check` in Copilot Chat |
| VS Code for the Web | vscode.dev in Chrome or Edge, the kit opened from the laptop, Copilot Free | The same commands |

The full design, with every promise in the program mapped to the block that
keeps it, is `docs/ahg-2026/plan.md`.

### 1.2 Where everything is

Everything for the course is in `docs/ahg-2026/`. The table lists what each
part is and who uses it.

| Path | What it is | Used by |
|---|---|---|
| `docs/ahg-2026/README.md` | Index of the folder | Everyone |
| `docs/ahg-2026/plan.md` | The plan and the promise map | Facilitator |
| `docs/ahg-2026/run-of-show.md` | The day by the clock, pacing, fallbacks, pre-flight | Facilitator, helpers |
| `docs/ahg-2026/facilitator-card.md` | The pocket card | Facilitator |
| `docs/ahg-2026/answer-key.md` | Every barrier planted in the sample course | Facilitator, testers |
| `docs/ahg-2026/pre-event-message.md` | The setup message for participants | Facilitator |
| `docs/ahg-2026/ahg-speaker-guidance.md` | The AHG speaker recommendations and where they are met | Facilitator |
| `docs/ahg-2026/slides.*` | The deck: HTML, PowerPoint, Word, Markdown | Facilitator |
| `docs/ahg-2026/kit/` | The agent kit every participant opens in VS Code | Participants |
| `docs/ahg-2026/for-accessibility-agents/` | The landing folder for capstone pull requests, to copy into that repository | Facilitator |
| `web/src/acb_large_print_web/workshop_deck.py` | The source of the deck | Maintainer |
| `web/src/acb_large_print_web/workshop_agenda.py` | The clock (`AHG_DAY`) | Maintainer |
| `scripts/build_ahg_sample_course.py` | Rebuilds the sample course | Maintainer |
| `scripts/build_ahg_kit.py` | Rebuilds the kit's generated parts and the zip | Maintainer |
| `scripts/audit_ahg_docs.py` | Runs GLOW's audits over every document | Maintainer, testers |
| `scripts/check_material_conformance.py` | Checks materials against the program's promises | Maintainer, testers |
| `scripts/sync_ahg_repo.py` | Publishes the kit and repository files to Community-Access/ahg-2026 | Maintainer |
| `docs/ahg-2026/repo/` | The workshop repository's own files | Maintainer |

### 1.3 The agent kit

Participants download the kit as a zip from the setup page and open the
folder in VS Code. The table lists its parts.

| Part | What it does |
|---|---|
| `README.md` | Welcome page; opens first in VS Code |
| `.github/copilot-instructions.md` | Workshop rules for Copilot: plain language, encouragement, evidence only, cite WCAG 2.2, never "compliant", nothing private |
| `.github/skills/<command>/SKILL.md` | The kit's eight commands, as agent skills: one per block, plus /review-my-agent, which makes the next version of the participant's agent, and /install-my-agent, which makes it a command of its own. Prompt files run only in Local chat sessions since VS Code 1.143; skills run in the default ones too |
| `.github/skills/<skill>/` | All 113 Accessibility Agents skills, copied unchanged from the commit named in `accessibility-agents-skills.json`. Six of them are entry points a participant asks for by name; they call the rest |
| `any-assistant/*.txt` | The browser path: one text per block, carrying the block's instructions and every kit file it needs, the review text, and four `aa-*.txt` texts that carry an Accessibility Agents entry point and the specialists it calls. Generated by `scripts/build_ahg_kit.py` |
| `accessibility-agents.md` | What Accessibility Agents is and how to keep using it after today: in the kit, in Codespaces, in their own projects, with their IT team, or in a browser assistant |
| `accessibility-agents-in-the-kit.md`, `accessibility-agents-skills.json` | Generated by the vendor script: which skills work fully in the kit, and what the others do without the project's scanners, scripts and hooks |
| `agent-file-principles.md` | The principles of a good agent file, and the review checklist |
| `.github/agents/office-coordinator.agent.md` | The coordinator that runs the agent team |
| `office-team/` | Eight specialists: Word, PowerPoint, Excel, PDF, web pages, captions and media, plain language, standards reviewer |
| `my-agent/SKILL.md` | The participant's own agent |
| `examples/` | Maria, Jordan and Sam's worked examples, and six ready-made agents in `examples/agents/` |
| `sample-course/` | PSY 101, seven files with planted barriers, and `evidence/` with each file's checker report |
| `step-cards/` | Setup plus one card per block, Markdown and large print Word |
| `share-my-agent.html` | Offline copy of the share page |
| `ahg-2026.code-profile` | The VS Code profile |

### 1.4 The day

The day runs 10:30 to 4:30 in seven blocks. The command is typed into
Copilot Chat on the two VS Code paths; on the browser path the same block is
one text on `/ahg/assistant`. The clock is `AHG_DAY` in
`workshop_agenda.py`; this table follows it.

On 27 October `AHG_DAY` changed: building the office moved before sharing,
so participants share their best version, and blocks 3, 4 and 5 now each end
with /review-my-agent, which makes the next version of their agent. The kit's
commands, browser path texts, GLOW pages, tests, step cards, the kit's
README, the deck, the run of show and this plan all follow the new order
(D-012, closed 28 October). The build the office text is
`5-run-the-office.txt`.

| Time | Block | Command | Participant has at the end |
|---|---|---|---|
| 10:00 | Setup table outside the room | `/ready-check` | A ready laptop |
| 10:30 | 1. Why we are here | `/ready-check` | The journey, and the finished result in view |
| 10:50 | 2. Design your agent | `/design-my-agent` | Version 1 of `my-agent/SKILL.md`, with their name on it |
| 11:40 | 3. Your agent at work | `/try-my-agent`, then `/review-my-agent` | A first answer on a course document, then version 2 |
| 12:15 | Lunch | none | |
| 1:15 | 4. Ground it | `/ground-my-agent`, then `/review-my-agent` | Cited answers from evidence; a before and after; version 3 |
| 2:05 | Break | none | |
| 2:15 | 5. Build the office | `/run-the-office`, then `/review-my-agent` | A team report with their agent's section, then the full Accessibility Agents team (D-017) |
| 3:05 | 6. Share it | `letitglow.app/ahg/share` | Their best version in the collection, committed in their name |
| 3:40 | 7. Take it home | `/my-30-day-plan` | `my-30-day-plan.md`, a commitment on the wall, and `accessibility-agents.md` for after today |
| 4:15 | Commitments | GLOW wall | |
| 4:25 | Session evaluation | proctor | |

### 1.5 Before the day: configuration

PR #116 was merged and deployed on 10 October 2026, and the workshop
repository Community-Access/ahg-2026 exists, owned by Community Access with
Jeff as admin. Do these before the first setup message goes out.

1. Accept the admin invitation to Community-Access/ahg-2026 on the
   jeffreybishop account (GitHub emails it).
2. Add the AHG session to GLOW's conference codes, in
   `WORKSHOP_CONFERENCE_CODES_JSON` in `~/app/web/.env` or in
   `instance/workshop_conference_codes.json`:

   ```json
   [{"access_code": "AHG2026", "session_code": "ahg-2026",
     "session_title": "Accessibility Agents: Building Human-Centered AI Workflows for Trusted Accessibility Automation at Scale",
     "event_name": "Accessing Higher Ground 2026", "active": true,
     "facilitator_key": "choose-a-long-random-key"}]
   ```

   Choose your own facilitator key, and keep it off every slide.
3. The share form's workshop code is the `WORKSHOP_CODE` variable in the
   ahg-2026 repository's settings, under Secrets and variables, then Actions.
   It is `AHG2026` now; if you change it, change the table cards and the
   setup message to match.
4. Clear the test issues and the test agents from the ahg-2026 repository
   before the setup message goes out (test cases Repo-01 to Repo-07 leave
   some behind).
5. Open `https://letitglow.app/ahg` and confirm the page, kit, profile and
   share page all work (tests Setup-01, Setup-14, Assist-01 and SetupD-03).
6. Send the setup message in `pre-event-message.md` by 20 October, again on
   6 November, and two days before. It asks everyone to share a practice
   agent; watch `practice/` in the ahg-2026 repository fill up, and write to
   anyone missing by 9 November.
7. Upload `slides.pptx`, `slides.docx` and the step cards to the Cvent
   Speaker Resource Center under My Tasks.
8. Before the end-of-day step, copy
   `docs/ahg-2026/for-accessibility-agents/community/ahg-2026/README.md` into
   the Accessibility Agents repository at the same path, after confirming its
   `scripts/validate-skills.mjs`, context budget check and
   `scripts/install.mjs` skip `community/`.

### 1.6 Rebuilding after a change

Run these from the repository root after changing the course, the kit or
the deck, then re-run the automated checks in section 2.4. Finish with the
sync to the workshop repository, so participants who download it get the
same kit.

```text
python scripts/build_ahg_sample_course.py
python scripts/vendor_accessibility_agents.py ../accessibility-agents
python scripts/build_ahg_kit.py --axe-js web/node_modules/axe-core/axe.min.js
flask --app acb_large_print_web.app:create_app workshop-deck --code ahg-2026
python scripts/sync_ahg_repo.py ../ahg-2026
```

Run the vendor step only to move the kit to a newer Accessibility Agents
commit. Give it a checkout, as above, so it records the commit; with no
argument it downloads main and records only the word "main" (D-016). Then
run section 2.13a again. The kit build writes the `aa-*.txt` texts only
when the vendored skills are present, so vendor first.

The kit build needs Python with python-docx, python-pptx, openpyxl, Pillow,
PyMuPDF and Playwright, and Chrome installed for the axe step. Never edit
`slides.*`, the step card Word files, the evidence files or
`share-my-agent.html` by hand; they are generated.

### 1.7 Running GLOW locally for testing before the merge

Testers can run every GLOW page from the branch on their own machine before
anything is deployed. In PowerShell, from `web/` in a checkout of the
`feat/ahg-three-paths` branch:

```text
$env:PYTHONPATH = "src;..\desktop\src"
$env:WORKSHOP_CONFERENCE_CODES_JSON = '[{"access_code":"AHGTEST","session_code":"ahg-2026","session_title":"Accessibility Agents","event_name":"AHG 2026 rehearsal","active":true,"facilitator_key":"rehearsal-key"}]'
python -m flask --app acb_large_print_web.app:create_app run --port 5000
```

Then use `http://127.0.0.1:5000` wherever this plan says
`https://letitglow.app`. The first visit shows GLOW's consent page; accept
it.

### 1.8 Running the day

Follow `run-of-show.md`. In short:

1. From 10:00, helpers run the setup table outside the room: `/ready-check`
   in VS Code, or the block 1 text on the browser path. Anyone whose VS Code
   will not cooperate moves to the browser path there and then.
2. Every block: show the finished result, demo it on the projector in VS
   Code, then participants run the block on their own path with its step
   card.
3. Anyone stuck uses a ready-made agent from `examples/agents/` and keeps
   going. Say often that this counts.
4. In block 5, everyone runs their own team, then /review-my-agent. The
   last 15 minutes are the full Accessibility Agents project on the
   projector, from the skills in the kit (D-017).
5. In block 6, project the collection and refresh it as agents arrive;
   read each name aloud. Helpers watch the issues labelled needs-a-hand.
   The projector run with every shared agent comes last, from a `room/`
   folder in your kit.
6. 4:25 is the session evaluation. Stop talking.
7. After the session, send the collection into Accessibility Agents with
   `scripts/promote_to_accessibility_agents.py`, as `run-of-show.md`
   section 6a describes.

## Part 2: Test plan

### 2.1 Goal and definition of done

The goal is to prove, before 16 November, that a beginner with a laptop can
complete every block by keyboard and screen reader as well as by mouse, that
every fallback works, and that every material is accessible.

Testing is complete when all of these are true:

1. Every test case in sections 2.4 to 2.13 is marked Pass, or marked Not
   applicable with a reason.
2. Every defect found is fixed and its test re-run to Pass, or accepted in
   writing in the defect log with a workaround on the day.
3. The screen reader matrix in section 2.3 is complete for every row marked
   required.
4. The timed dry run in section 2.13 is done and its real minutes are written
   into `run-of-show.md`.
5. The sign-off in section 2.15 is complete.

To run the plan, follow Part 3 from start to finish: it puts every case
below in order, with the exact answers to type. Record results in the Result
column, or the path column: Pass, Fail (with a defect number), or
Not applicable (with a reason). Keep this file as the record; commit it with
results filled in.

### 2.2 People and accounts

The test plan needs the following people and accounts.

| Role | Who | Needs |
|---|---|---|
| Facilitator tester | Jeff | Admin on Community-Access/ahg-2026 and merge rights on Accessibility Agents; facilitator key; a free ChatGPT account made for the test |
| Beginner tester | Someone who has never opened VS Code | A brand-new GitHub account made for the test |
| Screen reader tester, Windows | An experienced NVDA and JAWS user | A Windows laptop, a new GitHub account |
| Screen reader tester, Mac | An experienced VoiceOver user | A Mac, a new GitHub account |
| Helper | Anyone | Reads the run of show and the fallback ladder |

Every tester account must have Copilot Free. Use new accounts: an account
that already has Copilot Pro hides the free-tier limits this plan has to
measure. For the same reason, the ChatGPT column uses a free ChatGPT account
made for the test, never a Plus account. Copilot moved to GitHub AI Credits
on 1 June 2026 and publishes no chat count for Free, so Office-08 measures
the share of the allowance a day uses.

Testers share into the real workshop repository with "My practice
agent", which lands in `practice/` and never reaches Accessibility Agents.
Clear test agents and issues afterwards (section 1.5, step 4).

### 2.3 Test environments and paths

Each required environment row must be run at least once, start to finish,
from setup to the team report.

Jeff tests on Windows only. The Mac rows, Env-4 and Env-5, need a separate
tester with a Mac; until one is found they stay open, and sign-off lists
them as the one remaining gap rather than marking them Not applicable.

| ID | Operating system | Browser | Assistive technology | Required |
|---|---|---|---|---|
| Env-1 | Windows 11 | Chrome | None, mouse and keyboard | Yes |
| Env-2 | Windows 11 | Chrome | NVDA, current release | Yes |
| Env-3 | Windows 11 | Edge | JAWS 2026 | Yes |
| Env-4 | macOS, current release | Safari for the browser path, Chrome for VS Code for the Web | VoiceOver | Yes |
| Env-5 | macOS, current release | Chrome | None, keyboard only | Yes |
| Env-6 | Windows 11, work laptop without administrator rights | Edge | None | Yes |
| Env-7 | Any | Any | Screen magnification at 200 percent and 400 percent zoom | Yes |
| Env-8 | Any | Any | Windows high contrast mode or a forced dark theme | No |

#### 2.3a The three paths

Every participant takes one of three paths (`docs/ahg-2026/plan.md`, D18).
Every block case in sections 2.7 to 2.12 has a result column for each path,
and every one must be run. A case that cannot apply to a path says so in
that column, with the reason.

| Path | Column | What the tester uses | Required |
|---|---|---|---|
| The browser path | ChatGPT | chatgpt.com, signed in to a free account made for the test, with the texts from `/ahg/assistant` | Yes |
| VS Code on a computer | Desktop | VS Code 1.143 or later, the AHG 2026 profile, the kit folder, Copilot Free | Yes |
| VS Code for the Web | Web | vscode.dev in Chrome or Edge, the kit folder opened from the laptop, Copilot Free | Yes |

Each required path must be run start to finish at least once with no
assistive technology (Env-1) and once with NVDA (Env-2). JAWS (Env-3) and
VoiceOver (Env-4) run at least the browser path and one VS Code path.

#### 2.3b Other assistants on the browser path

The browser path names other assistants. They are not required for sign-off,
but run block 1, block 2 and block 5 in each before the setup message calls
it tested with that assistant.

| ID | Assistant | Block 1 | Block 2 | Block 5 | Result |
|---|---|---|---|---|---|
| Alt-01 | GitHub Copilot on github.com, Copilot Free | | | | |
| Alt-02 | Claude, free plan | | | | |
| Alt-03 | Gemini, free | | | | |
| Alt-04 | Microsoft 365 Copilot Chat, work account | | | | |
| Alt-05 | ChatGPT, signed out | Pass, Claude, 27 Oct | Stops: after the first answer a "Log in or sign up" wall blocks the next message | Not reached | Signed out is not supported; every surface says to sign in (D-007) |

### 2.4 Automated checks

Run these first, from the repository root on the branch. All must pass
before manual testing starts, and again after any fix.

| ID | Command | Expected | Result |
|---|---|---|---|
| Auto-01 | `python -m pytest web/tests -q` with `PYTHONPATH=web/src;desktop/src` | All pass | |
| Auto-02 | `python -m pytest web/tests/test_workshop_ahg_kit.py web/tests/test_workshop_deck.py web/tests/test_workshop_deck_formats.py web/tests/test_workshop_agenda.py -q` | All pass | |
| Auto-03 | `python -m pytest desktop/tests/test_md_auditor_false_positives.py desktop/tests/test_md_auditor_feature_parity.py -q` with `PYTHONPATH=desktop/src` | All pass | |
| Auto-04 | `python scripts/check_material_conformance.py` | "Every material conforms" | |
| Auto-08 | `python scripts/check_ahg_sample_course.py` | 42 of 42 pass | |
| Auto-05 | `python scripts/audit_ahg_docs.py` | "0 not passing" | |
| Auto-06 | The axe sweep in `web/e2e`, run as described in `web/e2e/README.md`, plus `/ahg/assistant` and `/ahg/paths` | No violations | |
| Auto-07 | GitHub Actions on the pull request | All required checks green | |
| Auto-09 | `python scripts/build_ahg_kit.py --no-axe`, then `git status` | The six `any-assistant/*.txt` texts and the step card Word files rebuild with no other change | |

### 2.5 Setup, on each path

These cover everything a participant does before the day. The GLOW pages
come first, then each path's own setup.

#### 2.5a The GLOW pages

These check the conference pages every path uses: the landing page, the paths page, the browser path page, the kit and the share page.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Setup-01 | Open `/ahg` | Heading "Accessibility Agents at AHG 2026"; "Get ready: choose a path" with the three paths and a link to each; the day's schedule; links to the kit, the profile, the share page, the slides and eight step cards; the two rules | |
| Setup-11 | Read `/ahg`, `/ahg/paths` and `/ahg/assistant` with a screen reader | One H1 each, H2s for each part, numbered lists announced, every link name says where it goes, the paths table read with its caption and row and column headers | |
| Setup-12 | Download `kit.zip` and the profile with no GLOW consent cookie (private window, direct links) | Both download without the consent page | |
| Setup-13 | Open `/ahg`, `/ahg/paths`, `/ahg/assistant` and the share page in a private window | Every one opens straight away, with no consent page | |
| Setup-14 | Open `letitglow.app/AHG`, `/ahg2026`, `/ahg-2026`, `/ahg/`, `www.letitglow.app/ahg` and `letitglow.app/workshop/ahg-2026` | Every one arrives at `letitglow.app/ahg` | |
| Setup-16 | Open `/ahg/kit`, then a step card, an agent and a command from it | Each reads as a page with its headings; each has "Copy this file's text" and a plain-text link; the step cards offer their Word file | |
| Setup-17 | Open `/ahg/site`, then the course announcement; run Accessibility Insights FastPass on it | The announcement shows its planted barriers, and FastPass finds what its checker report lists | |
| Setup-18 | Tab once on `/ahg`, `/ahg/paths`, `/ahg/assistant`, `/ahg/kit`, `/ahg/site` and the share page, then press Enter | The first stop is Skip to main content, and Enter moves to the page content | |
| Assist-01 | Open `/ahg/assistant` | Sections for blocks 1 to 7, with block 6 pointing to the share page, then "Review your agent" and "Accessibility Agents in any assistant" with its four texts; each other block has a "Copy the text for Block N: ..." button, a "Read the text first" disclosure and a plain-text link | |
| Assist-02 | Press each Copy button, then paste into Notepad | The whole text arrives, starting "AHG 2026 Accessibility Agents workshop. Block"; the message under the button says it is copied and how to paste | |
| Assist-03 | Press the same Copy button twice with NVDA running | Both presses are announced; the second begins "Done again" | |
| Assist-04 | Block the clipboard (Chrome site settings, Clipboard, Block) and press a Copy button | The disclosure opens, the text is selected, focus is in it, and the message says to press Control+C, read on focus | |
| Assist-05 | Turn off JavaScript and open `/ahg/assistant` | No Copy buttons show; each text is still readable in its disclosure and at its plain-text address | |
| Assist-06 | Open `/ahg/paths` | The comparison table, then sections for the browser path (with ChatGPT, Copilot on github.com, Claude, Gemini and Microsoft 365 Copilot Chat), VS Code on a computer and VS Code for the Web, then switching paths and the two rules | |
| Assist-07 | Check every instruction on `/ahg/paths` against the real screens, on the day of testing: the ChatGPT Data controls toggle, the VS Code Profiles menu, the Restricted Mode banner, vscode.dev Open Folder and its permission prompts | Every label matches what is on screen; fix the page for any that does not | |
| Share-12 | On the share page, choose "My practice agent" and press "Fill in the practice template" | The template fills "Your agent, as text"; "My practice agent" is chosen; the message says both | |
| Share-13 | Type something into the text box, then press "Fill in the practice template" | A confirmation asks before replacing it; Cancel keeps the text | |
| Share-14 | Paste an agent and press "Download as `SKILL.md`" | A file named `SKILL.md` is saved with the pasted text; the message says the browser is saving it | |
| Share-15 | Press "Download as `SKILL.md`" with the box empty | The error is read when focus moves to the box; it clears when you type | |

#### 2.5b The browser path setup, with ChatGPT

These follow step card 0, "Everyone" and "In a browser", with a new ChatGPT account.

| ID | Steps | Expected | Result |
|---|---|---|---|
| SetupB-01 | Make a new GitHub account (step card 0, Everyone) | Account made | |
| SetupB-02 | At chatgpt.com choose Sign up for free and make a test account | Signed in; the composer is labelled "Chat with ChatGPT" | |
| SetupB-03 | Turn off training: profile menu, Settings, Data controls, "Improve the model for everyone" | The toggle exists with that name, and turns off | |
| SetupB-04 | From `/ahg/assistant`, copy block 1, switch tabs with Control+Tab, paste, press Enter | All three checks Ready; the template comes back in a code block with a Copy button; ends "You are ready for 16 November." and the practice agent line | Signed out: Pass, Claude, 27 Oct, all three checks Ready and both closing lines exact. Signed in: |
| SetupB-05 | Share the practice agent from step card 0, using "Fill in the practice template" | Within about a minute the issue gets a reply beginning "Well done" | |
| SetupB-06 | Do SetupB-02 to SetupB-05 with NVDA | The ChatGPT composer, Send button and each reply are reachable; the code block's Copy button is named | |

#### 2.5c VS Code on a computer

These follow step card 0, "In VS Code on your computer", with a new GitHub account.

| ID | Steps | Expected | Result |
|---|---|---|---|
| SetupD-01 | Install VS Code on Env-6 without administrator rights | Installs and opens; Help, About shows 1.143 or later | |
| SetupD-02 | Accounts menu, sign in with GitHub, with a brand-new account | Signed in; Copilot Free active with no other step | |
| SetupD-03 | File, Preferences, Profiles; New Profile menu, Import Profile; paste the profile address; Create | The "AHG 2026 Accessibility Agents" profile is made and active; the axe Accessibility Linter installed; editor text 18pt | |
| SetupD-04 | Repeat SetupD-03 with the downloaded `.code-profile` file | Same result | |
| SetupD-05 | Unzip the kit and open the folder (File, Open Folder) | If Restricted Mode shows, Manage, then Trust works; `README.md` opens as the welcome page | |
| SetupD-06 | Open the kit in a VS Code without the profile | VS Code offers the kit's recommended extensions | |
| SetupD-07 | Open Copilot Chat with Control+Alt+I and type `/` | The eight commands appear in the list with their descriptions, as skills, in the default (Copilot) session, alongside the Accessibility Agents entry points (AA-10) | |
| SetupD-08 | Type `/ready-check` | Five checks Ready; ends "You are ready for 16 November." | |
| SetupD-09 | Rename `office-team` and run `/ready-check` again, then rename it back | That step is "Needs a hand", with one suggestion and the support address | |
| SetupD-10 | Start a new chat, set Session Target to Local, and type `/ready-check` | Also runs; record it, as the fallback if skills misbehave | |
| SetupD-11 | Share the practice agent, choosing `my-agent/SKILL.md` | Reply "Well done" within about a minute | |

#### 2.5d VS Code for the Web

These follow step card 0, "In VS Code for the Web", in Chrome and then Edge.

| ID | Steps | Expected | Result |
|---|---|---|---|
| SetupW-01 | Open vscode.dev in Chrome | The Welcome page; the Chat view opens with Control+Alt+I and its input is announced as "Chat Input (Agent)" | Pass, Claude, 27 Oct: Chat view present, "Build with Agent", input "Chat Input (Agent), edit files in your workspace", Copilot status in the status bar |
| SetupW-02 | Repeat SetupW-01 in Edge, and in Safari and Firefox | Edge works; Safari and Firefox cannot open a folder, as `/ahg/paths` says | |
| SetupW-03 | Open Folder, pick the unzipped kit; allow the browser's prompts | Record the exact wording of each prompt in `/ahg/paths` and step card 0; the Explorer shows the kit | |
| SetupW-04 | Accounts menu, sign in with GitHub | Signed in; Copilot Free active | |
| SetupW-05 | Type `/` in the Chat view | The eight commands appear, alongside the Accessibility Agents entry points (AA-10) | |
| SetupW-06 | Type `/ready-check` | Five checks Ready; ends "You are ready for 16 November." | |
| SetupW-07 | Close the tab, reopen vscode.dev, open the kit from Open Recent | The kit opens again, possibly after one more permission prompt | |
| SetupW-08 | Press Control+N in the Chat view | The browser opens a new window, as `/ahg/paths` warns; the New Chat button starts a new chat | |

### 2.6 Block 1: Why we are here, and the deck

These cover the opening and every format of the deck.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Deck-01 | Open `/workshop/session/ahg-2026/deck` | 26 slides; first title "Accessibility Agents"; subtitle is the program title word for word | |
| Deck-02 | Move through the deck with arrow keys, Page Up and Page Down, Home and End | Each change moves focus to the slide heading and is announced politely | |
| Deck-03 | Turn speaker notes on and off with the `n` key and the button | Notes show and hide; state is announced | |
| Deck-04 | Use "Read as one page" | The deck becomes one document with one heading per slide | |
| Deck-05 | Print or print to PDF | One slide per page, notes included, body text 18pt | |
| Deck-06 | Download the deck as one file with `?download=1`, open it offline | Works with no network | |
| Deck-07 | Open `slides.pptx` in PowerPoint; run Review, Check Accessibility | No errors; every slide has a title; reading order matches the screen | |
| Deck-08 | Read `slides.pptx` with NVDA or JAWS in PowerPoint | Titles, body and tables read in order; speaker notes in the notes pane | |
| Deck-09 | Open `slides.docx` in Word; run Check Accessibility | No errors; one heading per slide | |
| Deck-10 | Compare the clock times in the deck with section 1.4 | Every time matches | |
| Deck-11 | Read slides 1, 2, 5 and 6 aloud with their speaker notes | Key point first, the Title II problem, the three paths, the AI context and the privacy rule are all there | |
| Deck-12 | Read slides 11, 12, 15, 19, 21 and 24 | Each gives the VS Code command and the browser path step | |

### 2.7 Block 2: Design your agent

The ChatGPT column pastes the block 2 text from `/ahg/assistant` into the
conversation from SetupB-04. The two VS Code columns type `/design-my-agent`.

| ID | Steps | Expected | ChatGPT | Desktop | Web |
|---|---|---|---|---|---|
| Design-01 | Start the block; pick "documents and alternate formats"; give a real problem | It asks for the card and the problem, reminds you nothing private, names the two matching ready-made agents and offers to start from one | First turn, signed out: Pass, Claude, 27 Oct. It asked for the card and problem with the privacy reminder, and named both agents per card | | |
| Design-02 | Answer the six questions (D-015), borrowing from the example when unsure | One question at a time; it waits for each answer | | | |
| Design-03 | Give a name and institution; let it write the agent | ChatGPT: the whole agent in one code block with a Copy button. VS Code: `my-agent/SKILL.md` written. Either way: six headings and the Never section exactly; `name` lowercase with hyphens; `author` quoted; WCAG 2.2 links kept | | | |
| Design-04 | Read the summary | Five lines or fewer; one specific thing the agent does well; ends "Your agent exists." ChatGPT also says how to keep it with "Download as `SKILL.md`" | | | |
| Design-05 | ChatGPT: copy the code block, paste into the share page, "Download as `SKILL.md`" | The downloaded file starts with three dashes and `name:` and passes the share page's name check | | n/a: the file is in the kit | n/a: the file is in the kit |
| Design-06 | Repeat Design-01 to 04 for the other two role cards | Same, with the matching examples | | | |
| Design-07 | When asked for the problem, include a made-up student name and accommodation | It declines to use it and reminds the tester to keep it private | | | |
| Design-08 | Fallback: from `/ahg/kit`, copy the faculty coach and use it as the agent, changing the author | ChatGPT: accepted as the agent. VS Code: pasted over `my-agent/SKILL.md`; the ready check still passes | | | |
| Design-09 | Do the whole block with NVDA only | Every question and answer is readable; in VS Code, Alt+F2 reads the full response; in ChatGPT, the code block's Copy button is reachable and named | | | |
| Design-10 | Time the block for the beginner tester | Under 60 minutes including reading the example | | | |

### 2.8 Block 3: Your agent at work

These check the agent's first answer, before it has any evidence, on each path.

| ID | Steps | Expected | ChatGPT | Desktop | Web |
|---|---|---|---|---|---|
| Try-01 | Start the block (block 3 text, or `/try-my-agent`); accept the suggested file | It uses the agent from block 2, naming it; the suggestion fits the agent's task | | | |
| Try-02 | Read the answer | Answers as the agent, with no checker evidence | | | |
| Try-03 | Read the note after the answer | One thing done well; one place it guessed; ends with the after-lunch line | | | |
| Try-04 | Run it with each of the six ready-made agents | Each produces an answer in its own output format | | | |
| Try-05 | ChatGPT only: start a new conversation, then paste the block 3 text | It asks you to paste your agent and waits; pasting the downloaded `SKILL.md` carries on | | n/a | n/a |

### 2.9 Block 4: Ground it

These prove that evidence changes the answers, for every kind of file, on each path.

| ID | Steps | Expected | ChatGPT | Desktop | Web |
|---|---|---|---|---|---|
| Ground-01 | Start the block with the syllabus | Uses `psy101-syllabus` evidence; cites at least one WCAG 2.2 criterion with a link; lists what a person must still check | | | |
| Ground-02 | Same with the lecture | Mentions untitled slides and reading order; flags "image.png" alt text only as something a person must check | | | |
| Ground-03 | Same with the gradebook | Mentions merged cells and color-only status | | | |
| Ground-04 | Same with the scanned reading | Says the pages are pictures of text; cites 1.4.5 | | | |
| Ground-05 | Same with the lab handout | Mentions untagged PDF; says the color-dependent exercise needs an alternative, not an edit | | | |
| Ground-06 | Same with the announcement page | Uses the axe evidence: contrast, missing alt, language, heading order | | | |
| Ground-07 | Same with the captions | Uses the captions evidence and the known names; corrects "herman ebb in house" | | | |
| Ground-08 | Compare Ground-01 with Try-02 for the same file | Fewer guesses and more citations | | | |
| Ground-09 | Paste Word's Check Accessibility results for the syllabus | The agent works from Word's results the same way | | | |
| Ground-10 | Check every answer from Ground-01 to 07 | None says "compliant" or "accessible" as a verdict; none invents a finding not in the evidence | | | |
| Ground-11 | Spot check every evidence file against `answer-key.md` | Every GLOW rule in the evidence appears in the key | | | |

### 2.10 Block 6: Share it, and the workshop repository

Run these with "My practice agent" unless the case says otherwise, so test
agents land in `practice/`; clear them afterwards. Sharing is the same page
on every path; the columns record where the agent came from.

| ID | Steps | Expected | ChatGPT | Desktop | Web |
|---|---|---|---|---|---|
| Share-01 | Open `/ahg/share`; give it the agent (ChatGPT: the downloaded `SKILL.md` or a paste; VS Code: `my-agent/SKILL.md`) | The text box fills; the name fills; a status message is announced | | | |
| Share-02 | Press "Open the share form on GitHub" | A new tab opens the Share my agent form in Community-Access/ahg-2026, filled in | | | |
| Share-03 | Tick the privacy box and press Submit new issue | Within about a minute, a reply: "Your agent is in" with a link, or "Well done" for a practice agent | | | |
| Share-04 | Repeat Share-01 to 03 with a brand-new GitHub account | Same; the commit shows on that account's profile | | | |
| Share-10 | Do Share-01 to 03 with NVDA and JAWS | Every control on the share page and GitHub's form is reachable and named; the reply is found by heading or by refreshing | | | |

These do not depend on the path.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Share-05 | Submit with the text box empty | "Your agent is empty" is read on focus; focus moves to the text box | |
| Share-06 | Submit a real agent with the name still "my-agent-name" | Message asks for a name of its own; focus moves to the name field | |
| Share-07 | Paste an agent longer than about 7,000 characters | Message explains how to paste it into the form directly | |
| Share-08 | Use the offline `share-my-agent.html` from the kit | Same as Share-01, 02, 12 and 14 | |
| Share-09 | Open `/ahg/share?practice=1` | "My practice agent" is chosen | |
| Share-11 | Ten people share within two minutes | Every one gets a reply within five minutes; no commit is lost | |
| Repo-01 | A practice agent through the form | Committed to `practice/<account>/SKILL.md` with the sharer as author; reply "Well done"; issue closed | |
| Repo-02 | A real agent, with the code in lower case | Committed to `agents/<account>/<name>/SKILL.md`; gallery updated; reply "Your agent is in" | |
| Repo-03 | A wrong code, the template's name and author | Reply "Nearly there" listing all three; issue stays open, label needs-a-hand | |
| Repo-04 | Fix Repo-03 by editing the issue | Checked again on save; agent goes in | |
| Repo-05 | An agent containing an email address or a nine-digit number | Reply names what looks private; nothing committed | |
| Repo-06 | An author with an unquoted colon | Reply explains double quotes; nothing committed | |
| Repo-07 | Run `scripts/promote_to_accessibility_agents.py` against a scratch checkout of Accessibility Agents | Every agent copied to `community/ahg-2026/`; a Co-authored-by line per author | |

### 2.11 Block 5: Build the office

The ChatGPT column pastes the block 5 text, about 31 KB, in the same
conversation. This is the case most likely to hit a free plan's limits;
record exactly what happens.

| ID | Steps | Expected | ChatGPT | Desktop | Web |
|---|---|---|---|---|---|
| Office-01 | Start the block (block 5 text, or `/run-the-office`) | ChatGPT accepts the whole text as one message; it explains in two lines what is about to happen | | | |
| Office-02 | Let it run | One file at a time, one line per file naming the specialists | | | |
| Office-03 | Read the team report | Three lines for a director first; one section per course file; the tester's agent and name where its task fits; WCAG 2.2 criteria with links; "what no checker can see"; status "proposed" | | | |
| Office-04 | Read the end of the report | A "Before this goes anywhere" checklist, then one sentence saying what the tester's agent added | | | |
| Office-05 | Run with no agent (ChatGPT: a new conversation; VS Code: the template left in `my-agent/SKILL.md`) | It says so kindly and offers the ready-made agents | | | |
| Office-06 | If the run stops before the last file, type "continue" | It continues from where it stopped | | | |
| Office-07 | Facilitator, Desktop only: copy every shared agent into `room/` in the kit, then `/run-the-office` | Every room agent is on the team, named with its author | n/a | | n/a |
| Office-08 | Record the AI usage for one full participant day | ChatGPT: any limit messages, and when. Copilot: the share of the monthly allowance used, from github.com Copilot settings | | | |

### 2.12 Block 7: Take it home, and the commitment wall

These check the 30-day plan on each path.

| ID | Steps | Expected | ChatGPT | Desktop | Web |
|---|---|---|---|---|---|
| Plan-01 | Start the block; answer six questions | One question at a time. ChatGPT: the plan in one code block as a table. VS Code: `my-30-day-plan.md` saved | | | |
| Plan-02 | Read the last line | One reason the plan is realistic; ends "Go make one more champion." | | | |

The commitment wall is the same on every path.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Wall-01 | Open `letitglow.app/w/ahg-2026/11`, join with the access code, add a commitment | Saved | |
| Wall-02 | Open `/workshop/session/ahg-2026/wall`, entering the facilitator key if asked | The commitment appears with no name | |
| Wall-03 | Read the wall with a screen reader | Every commitment is reachable as list or text | |

### 2.13 Materials, accessibility and fallbacks

These cover the content, the sample course, and what happens when things go wrong, on every path.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Mat-01 | Open each of the seven sample course files | Each opens in its own application | |
| Mat-02 | Check each planted barrier in `answer-key.md` against the files | Every barrier present exactly as described | |
| Mat-03 | Read the three worked examples aloud | Facts, times and names match the deck | |
| Mat-04 | Open each step card Word file in Word; Check Accessibility | No errors; headings real; each path's numbered list starts at 1 | |
| Mat-05 | Compare each step card's steps with what testers actually did, on each path | Every key, label and expected result matches the real screens | |
| Mat-06 | Read `pre-event-message.md` as a participant | The three paths, the support address, Mountain Time, the privacy rule | |
| Mat-07 | Replace the written before and after answers in the worked examples with real output captured in Ground-08 | Examples show real output, still labelled | |
| A11y-01 | Use every GLOW page in this plan by keyboard only | Every control reachable, visible focus, logical order | |
| A11y-02 | Zoom `/ahg`, `/ahg/paths`, `/ahg/assistant`, the share page and the deck to 200 and 400 percent | No loss of content or function; no horizontal page scrolling at 400 percent; the paths table scrolls inside its own region | |
| A11y-03 | Turn on reduced motion | Nothing animates | |
| A11y-04 | Use the kit at 18pt with VS Code zoomed in twice, on a computer and at vscode.dev | Chat and editor remain usable | |
| Fall-01 | Turn off wifi after setup | The kit, sample course, evidence, step cards and examples still open; only the AI and GitHub fail | |
| Fall-02 | Use up the Copilot allowance, or sign in with an account that has | The step card's switch to the browser path completes the block from the same point | |
| Fall-03 | Profile import refused on Env-6 | SetupD-06 route works, or the browser path | |
| Fall-04 | GitHub unreachable during block 5 | The agent file can be saved for a later share: from the kit, or by "Download as `SKILL.md`" | |
| Fall-05 | Projector off | The facilitator can run the block from the pocket card and step cards alone | |
| Fall-06 | Mid-block, move a participant from VS Code to the browser path, as `/ahg/paths` "Switching paths" says | They carry on from the same block with the same agent | |
| Load-01 | 40 downloads of `kit.zip` from one network within a minute | All succeed | |
| Dry-01 | Timed dry run of the whole day with the beginner tester, once on the browser path and once in VS Code | Real minutes per block written into `run-of-show.md` section 2 | |

### 2.13a Accessibility Agents in the kit

The kit carries the real Accessibility Agents project: all 113 of its skills,
copied unchanged into `.github/skills` by
`scripts/vendor_accessibility_agents.py`, beside the kit's own commands. These
cases prove the copy is faithful, that it works on every path without the
project's scanners, and that every way `accessibility-agents.md` offers for
after today really works. Find the pinned commit in
`accessibility-agents-skills.json`.

The copy itself, from the repository:

| ID | Steps | Expected | Result |
|---|---|---|---|
| AA-01 | Check out Accessibility Agents at the pinned commit beside GLOW. Run `python scripts/vendor_accessibility_agents.py ../accessibility-agents`, then `git status` | Nothing changes: the copy is reproducible | Pass, Claude, 28 Oct: a second run leaves every kit file byte-identical |
| AA-02 | Compare every folder in the kit's `.github/skills`, except the eight kit commands, with `skills/` in Accessibility Agents at the pinned commit | The same files with the same contents; nothing missing, nothing extra | Pass by content, Claude, 28 Oct: 113 skills and 412 files at `aaf1cfb`, Accessibility Agents 7.1 plus two fixes, the tip of main. (27 Oct: 108 skills and 365 files at `decf6ba`) |
| AA-03 | Compare each copied skill's folder name with the `name` in its header | All match; VS Code finds a skill only when they do | Pass, Claude, 28 Oct |
| AA-04 | Compare the copied skill names with the kit's eight commands | No clash; the vendor script stops if there ever is one | Pass, Claude, 28 Oct |
| AA-05 | Read `accessibility-agents-in-the-kit.md` against `accessibility-agents-skills.json` | The same commit; the counts add up, 72 working fully and 41 working differently, 113 in all; every "works differently" row says what to do instead | Pass, Claude, 28 Oct |
| AA-06 | Read `accessibility-agents.md` against the Accessibility Agents README at the pinned commit | The six entry points, the install lines and the note that the VS Code extension is retired all match the project | Pass, Claude, 28 Oct, against Accessibility Agents 7.1: the install table was brought up to the current commands, and the Codespaces steps match its dev container (D-010) |
| AA-07 | Look for Accessibility Agents' licence in the kit | The project's MIT licence and copyright line travel with the copied skills | Pass, Claude, 28 Oct: `accessibility-agents-LICENSE.txt`, written by the vendor script (D-014) |
| AA-08 | Unzip `dist/ahg-2026-agent-kit.zip`, and the kit downloaded from letitglow.app/ahg | Both have 121 folders in `.github/skills`, 113 plus the eight commands, the four `aa-*.txt` texts, the three Accessibility Agents pages and the licence | Pass, Claude, 28 Oct: `dist/ahg-2026-agent-kit.zip`, and the letitglow.app download after deploy `b7529e7` (121 skill folders, the licence, step cards in the new order) |
| AA-09 | One week before the day, compare the pinned commit with Accessibility Agents main | The same; or the kit is vendored again at the new commit, AA-01 to AA-06 re-run, and the kit rebuilt and synced | |

On each path. The ChatGPT column uses the `aa-*.txt` texts and the review
text from `/ahg/assistant`; the VS Code columns ask for the skill by name in
a new chat in the kit.

| ID | Steps | Expected | ChatGPT | Desktop | Web |
|---|---|---|---|---|---|
| AA-10 | New Chat; type `/` | The six entry points are listed: accessibility-lead, web-accessibility-wizard, document-accessibility-wizard, markdown-a11y-assistant, developer-hub and github-hub. The kit's eight commands are still easy to find by typing their names | n/a: no list | | |
| AA-11 | Ask: `use document-accessibility-wizard to review psy101-syllabus.docx, using sample-course/evidence/psy101-syllabus.txt`. ChatGPT: paste `aa-office-documents`, then the evidence file's text | It works from the evidence; cites WCAG 2.2 criteria with links; never says it scanned, ran or opened anything it could not; never asks for anything private | | | |
| AA-12 | The same with web-accessibility-wizard and the announcement page's axe evidence. ChatGPT: `aa-web-pages` | As AA-11; it finds the contrast, alt text, language and heading order failures in the evidence | | | |
| AA-13 | Ask pdf-accessibility, a skill that works differently in the kit, to scan the lab handout. ChatGPT: `aa-pdf-and-epub` | It says it has no scanner here and asks for Acrobat's Accessibility Checker results or the evidence file; it never invents a scan | | | |
| AA-14 | Ask markdown-a11y-assistant to review the kit's `README.md`. ChatGPT: `aa-markdown`, then the README's text | Findings on headings, links and tables, each tied to a criterion | | | |
| AA-15 | In a new chat for each, paste each of the four `aa-*.txt` texts, signed in to the free account | Each is accepted as one message (they are 23 to 36 KB) and begins by asking for the document and its checker results | Ready: the texts are on `/ahg/assistant` (D-011) | n/a | n/a |
| AA-16 | After block 2, type `/install-my-agent`; then New Chat and type `/` and the agent's name | It checks the name, copies the agent to `.github/skills/<name>/SKILL.md` and explains in three lines; the agent is then its own command and answers as itself | n/a: nothing to install | | |
| AA-17 | After block 3, type `/review-my-agent`. ChatGPT: paste the review text | Twelve lines of Yes or Not yet; one change, shown as the current and new lines, with the reason; it asks before changing anything; on yes it changes only that, keeps the three Never rules, raises `version` by one, and (VS Code) installs the new version | Ready: the review text is on `/ahg/assistant` (D-011) | | |
| AA-18 | Run AA-17 again after block 4 and after block 5 | Version 3, then version 4; each time a different change, tied to the agent's last answer | | | |
| AA-19 | Do AA-11 and AA-17 with NVDA only | Every answer readable, with Alt+F2 in VS Code; the change it proposes can be read before agreeing | | | |

After today: the routes in `accessibility-agents.md`.

| ID | Steps | Expected | Result |
|---|---|---|---|
| AA-20 | Follow "The full version, in your browser, with one click" with a test account | A codespace opens; the six entry points answer; the scanners run, as the page promises | Ready for a person: Accessibility Agents 7.1 has the dev container (D-010) |
| AA-21 | Follow "In your own projects in VS Code": Download ZIP, copy every `skills` folder into `.github/skills` of a fresh folder, New Chat | The six entry points appear, and AA-11 passes there with the evidence file copied in | |
| AA-22 | Optional, on a scratch laptop: each line of "With your IT team" | Each installs, and the entry points appear in that tool | |

### 2.14 Defect log

Number every defect. A defect is closed when its fix is merged and the test
that found it passes again.

| Defect | Test | What happened | Fix | Re-test result |
|---|---|---|---|---|
| D-001 | Auto-07 | Six ready-made agents had author lines like "Example: Maria Alvarez": invalid YAML. Vale stopped on it; VS Code would have misread the headers | Header text quoted by the kit build; template and /design-my-agent keep quotes; a test parses every front matter block (`1d4f1fd`) | Pass, 10 Oct |
| D-002 | A11y-02 | On every GLOW page, at 320px wide, page content was 0px wide: the AI meter sat outside the sidebar and became a column. Live on letitglow.app | Meter moved inside the sidebar; PR #117 for production, same commits on this branch | Pass, 10 Oct |
| D-003 | A11y-02 | Home, privacy, audit and convert pages overflowed sideways at 320px | Wrapping and width rules for main content and form controls (PR #117) | Pass, 10 Oct |
| D-004 | A11y-02, Deck axe | Setup page's profile address and the deck's slide picker overflowed at 320px; deck controls outside any landmark; count said "of 30" | Fixed in `41f1fd7` | Pass, 10 Oct |
| D-005 | Setup-04 | Prompt files used the older `mode:` header; VS Code 1.141 reads `agent:` | All six commands now use `agent: agent` | Superseded by D-006 |
| D-006 | Research, 27 Oct | VS Code 1.143 runs prompt files only in Local chat sessions; new chats default to the Copilot session, where `/ready-check` would not exist | The six commands moved to agent skills in `.github/skills/` (D19); tests hold the layout | Confirm in SetupD-07, SetupD-10 and SetupW-05 |
| D-007 | Alt-05, 27 Oct | ChatGPT signed out answered block 1 and the first turn of block 2, then a "Log in or sign up" wall stopped every further message | Every browser path surface says to sign in: `/ahg/assistant`, `/ahg/paths`, step cards 0 and 1, the setup message | Confirm in SetupB-04 signed in |
| D-008 | Build, 27 Oct | Step card Word files continued numbering across lists, so a card's second list started at 6 | Each numbered list gets its own numbering that starts at 1 | Pass by inspection of `0-before-the-day.docx`; confirm in Mat-04 |
| D-009 | Build, 27 Oct | Wrapped bullet lines in step cards became separate paragraphs in Word | Continuation lines indented two spaces join their bullet | Pass by inspection; confirm in Mat-04 |
| D-010 | AA-06, AA-20, 27 Oct | `accessibility-agents.md` says a codespace gives "the whole project, scanners included" and that "the scanners run for you". At `decf6ba` Accessibility Agents has no dev container; its skills are in `skills/`, which VS Code does not read; its scanner server is declared in a root `mcp.json`, which VS Code does not read; and nothing installs the server's dependencies | Either Accessibility Agents gains a `.devcontainer` that installs it and a VS Code skills and MCP setup, or the page drops the Codespaces route or gives the terminal steps. Then run AA-20. 28 Oct: Accessibility Agents 7.1 added the dev container (`.devcontainer/devcontainer.json`, which installs the project and its scanners and runs `npm run setup`) and `.vscode/mcp.json`; `accessibility-agents.md` now gives those steps | Fixed upstream; AA-20 needs a person with a codespace |
| D-011 | AA-15, AA-17, 27 Oct | `/ahg/assistant` has no "Accessibility Agents in any assistant" section and no review text, though `accessibility-agents.md`, the block 4 text and the block 7 text send people there. The page lists only the six block texts | Add the four `aa-*.txt` texts and `review-my-agent.txt` to the page, with Copy buttons and plain-text links. 28 Oct: `/ahg/assistant` has "Review your agent" and "Accessibility Agents in any assistant", each with Copy buttons, a "Read the text first" disclosure and a plain-text link | Pass, 28 Oct: `test_the_browser_path_page_offers_every_block_with_a_copy_button` |
| D-012 | Inspection, 27 Oct | `AHG_DAY` moved Build the office to block 5 and Share it to block 6. The kit build now writes `5-run-the-office.txt`, but `/ahg/assistant` still looks for `6-run-the-office.txt`, so the page silently drops that block, and `test_workshop_ahg_kit.py` still expects the old name, so Auto-01 and Auto-02 will fail. The step cards, kit README, deck, run of show and this plan's block sections still use the old order | Bring `AHG_ASSISTANT_BLOCKS`, the tests, the step cards, the kit README, the deck, `run-of-show.md` and sections 2.10 to 2.12 and Part 3 into the new order. 28 Oct: done everywhere the old order appeared: `AHG_ASSISTANT_BLOCKS`, the page, the tests, step cards 5 and 6 (renamed), the kit README, the deck, `run-of-show.md`, the facilitator card, `plan.md`, the Maria example and this plan | Pass, 28 Oct: web tests |
| D-013 | AA-08, 27 Oct | `dist/ahg-2026-agent-kit.zip` was built at 3:33 PM, before the skills were copied in at 4:30, so the download has none of the 108 skills, the two new commands or the new pages | Rebuild with `build_ahg_kit.py`, then sync the workshop repository. 28 Oct: rebuilt after vendoring 7.1 | Pass, 28 Oct: AA-08 on the zip and on letitglow.app; workshop repository synced (ahg-2026#4) |
| D-014 | AA-07, 27 Oct | The kit carries Accessibility Agents' skills but not its MIT licence, which requires the copyright and permission notice in every copy | Have the vendor script copy the project's `LICENSE` into the kit beside the skills, and name it in `accessibility-agents.md`. 28 Oct: the vendor script writes `accessibility-agents-LICENSE.txt`, and both Accessibility Agents pages name it | Pass, 28 Oct (AA-07) |
| D-015 | Inspection, 27 Oct | /design-my-agent now asks six questions, adding Example; Design-02 and the agenda's block 2 line say five | Choose one and align the command, the browser text, the step card, the agenda and Design-02. 28 Oct: six, as /design-my-agent and the template already had them: the step card, agenda, deck, assistant page, examples and plan now say six | Closed, 28 Oct |
| D-016 | Inspection, 27 Oct | Run with no checkout, the vendor script records the word "main" instead of a commit, so the kit could not say which version it carries | Look up the commit, or require a checkout. 28 Oct: without a checkout the script now asks GitHub which commit main is at, downloads that commit, and records it | Closed, 28 Oct |
| D-017 | Inspection, 27 Oct | The agenda says block 5 ends with "the full Accessibility Agents team", but /run-the-office and its text have no such step | Decide the step, then write it into /run-the-office, its browser text and the step card, with a test case. 28 Oct: as the agenda says, the last 15 minutes of block 5 are the full Accessibility Agents project on the projector, from the kit, run by the facilitator; a new slide, the step card and the run of show say so. There is no participant step | Closed, 28 Oct; confirm in the dry run |

### 2.14a Results so far

The pages, kit, step cards and deck changed on 27 October to add the three
paths, so every result was cleared for a fresh run. The 10 October record of
the earlier single-path design is kept in `ahg-test-report.md`.

Run so far on 27 October, by Claude on Windows:

- SetupW-01: VS Code for the Web has the Chat view, opened with
  Control+Alt+I, with "Build with Agent", agent mode, and the input
  announced as "Chat Input (Agent), edit files in your workspace". So the
  third path is real; its sign-in and kit steps still need a person.
- SetupB-04 and Design-01, signed out: ChatGPT ran block 1 exactly and began
  block 2 correctly, then stopped behind a sign-in wall (D-007).

Later on 27 October, Claude checked the Accessibility Agents copy, section
2.13a, against the project at the pinned commit, `decf6ba`, and logged D-010
to D-017.

On 28 October, Claude vendored Accessibility Agents 7.1 (`aaf1cfb`, 113
skills), fixed D-010 to D-017, rebuilt the kit and re-ran section 2.13a's
repository checks:

- AA-01 to AA-05, AA-07 and AA-08 pass: the copy is reproducible; all 113
  skills and 412 files match by content; every name matches its folder;
  nothing clashes with a kit command; 72 skills work fully in the kit and
  41 work differently; the licence travels with them; the zip has 121
  skill folders.
- AA-06 passes against 7.1.
- The web tests pass (section 2.4).
- After deploy, `/ahg/assistant` on letitglow.app has blocks 1 to 7, the
  review text and the four Accessibility Agents texts.

What remains, in order:

1. Done 28 October: deployed to letitglow.app (`b7529e7`), the workshop
   repository synced, and AA-08 checked on the live download.
2. The automated checks, section 2.4.
3. SetupB-02 to SetupB-06, then sections 2.7 to 2.12 and 2.13a in the ChatGPT column,
   signed in to a free test account.
4. SetupD-01 to SetupD-11, then sections 2.7 to 2.12 and 2.13a in the Desktop column.
5. SetupW-02 to SetupW-08, then sections 2.7 to 2.12 and 2.13a in the Web column.
6. The screen reader runs in section 2.3a: each path with NVDA, and JAWS on
   the browser path and one VS Code path.
7. Section 2.3b for each other assistant, before calling it tested.
8. Share, Repo, Wall, Mat, A11y and Fall cases, and Dry-01 on two paths.
9. AA-09 a week before the day.

### 2.15 Sign-off

The workshop is ready when every line below is signed and dated.

| Item | Signed by | Date |
|---|---|---|
| Automated checks, section 2.4, all pass | | |
| Setup, section 2.5, all pass on every required environment | | |
| Blocks 1 to 7, sections 2.6 to 2.12, all pass in the ChatGPT column | | |
| Blocks 1 to 7, sections 2.6 to 2.12, all pass in the Desktop column | | |
| Blocks 1 to 7, sections 2.6 to 2.12, all pass in the Web column | | |
| Screen reader matrix, section 2.3, complete | | |
| Materials, accessibility and fallbacks, section 2.13, all pass | | |
| Accessibility Agents in the kit, section 2.13a, all pass at the commit the kit carries | | |
| Defect log closed or every open defect accepted with a workaround | | |
| Dry run done and run of show updated | | |
| Workshop repository cleared of test agents, and the Accessibility Agents folder in place for the end-of-day step | | |
| Setup message sent with working links | | |
| Facilitator ready to run the day | | |

## Part 3: The walkthrough, start to finish

Part 2 lists every test case. This part is the order to run them in: one
script, from an empty desk to the signed-off workshop, in sittings you can
stop between. Every step says what to do, what you should see, and which
test case IDs to mark in Part 2. When a step says "Mark", write Pass, or
Fail with a defect number from section 2.14, in that case's Result column
or path column.

Where a step gives text in a box, type or paste exactly that. Every answer
you need to give an assistant is written here, so you never have to make
one up, and two runs on different paths can be compared.

### 3.1 The sittings, and how long they take

Each row is one sitting. Do them in this order; each one needs the ones
before it.

| Sitting | What it covers | Where | About |
|---|---|---|---|
| A | Accounts, notebook, and where to test | Anywhere | 45 minutes |
| B | Automated checks | The repository, on the branch | 20 minutes |
| C | The GLOW pages, by keyboard and mouse | GLOW running locally from the branch | 60 minutes |
| D | Merge, deploy, and the production check | GitHub and letitglow.app | 30 minutes |
| E | The browser path, the whole day, in ChatGPT | letitglow.app and chatgpt.com | 3 hours |
| F | VS Code on a computer, the whole day | VS Code on Windows | 3 hours |
| G | VS Code for the Web, the whole day | vscode.dev in Chrome, then Edge | 2.5 hours |
| H | Screen readers: NVDA and JAWS | The browser path and one VS Code path | 4 hours |
| I | The deck and the materials | PowerPoint, Word, the deck page | 90 minutes |
| J | The workshop repository and the fallbacks | GitHub and a laptop with wifi you can switch off | 90 minutes |
| K | Other assistants, optional | Copilot on github.com, Claude, Gemini, Microsoft 365 | 90 minutes |
| L | The Mac, by a Mac tester | macOS with VoiceOver | 3 hours |
| M | The timed dry runs | With the beginner tester | Two days |
| N | Clean up, results and sign-off | The repository and GitHub | 60 minutes |

### 3.2 Sitting A: accounts, notebook, and where to test

1. Make three new GitHub accounts, one per path, so each path's Copilot Free allowance and each share can be told apart. Suggested names: `ahg-test-browser`, `ahg-test-desktop`, `ahg-test-web`. Use addresses you can receive mail at; GitHub sends a code. Do not add Copilot Pro to any of them.
2. Make one new ChatGPT account at chatgpt.com with "Sign up for free". Do not use a Plus account; it hides the free plan's limits.
3. Open a plain text notebook, `ahg-test-notes.txt`, outside the repository. For every assistant answer you will be asked to "keep", paste the whole answer into it under the test case ID. These are the evidence for Mat-07 and for any defect you log.
4. Have ready: a Windows 11 laptop with Chrome and Edge, NVDA and JAWS installed, Word and PowerPoint, and a second screen if you have one.
5. Know which GLOW to test against. Until the branch is merged and deployed, the new pages (`/ahg/paths`, `/ahg/assistant`, the share page's new buttons) exist only on the branch, so sittings B and C run against GLOW on your own machine, section 1.7. From sitting D onwards everything runs against `https://letitglow.app`, because the browser path texts and the step cards point there.

### 3.3 Sitting B: automated checks

From the repository root, on the `feat/ahg-three-paths` branch, in
PowerShell. Run each command and compare with section 2.4.

1. `$env:PYTHONPATH = "web/src;desktop/src"`, then `python -m pytest web/tests -q`. Mark Auto-01.
2. `python -m pytest web/tests/test_workshop_ahg_kit.py web/tests/test_workshop_deck.py web/tests/test_workshop_deck_formats.py web/tests/test_workshop_agenda.py -q`. Mark Auto-02.
3. `$env:PYTHONPATH = "desktop/src"`, then `python -m pytest desktop/tests/test_md_auditor_false_positives.py desktop/tests/test_md_auditor_feature_parity.py -q`. Mark Auto-03.
4. `python scripts/check_material_conformance.py`. Mark Auto-04.
5. `python scripts/audit_ahg_docs.py`. Mark Auto-05.
6. `python scripts/check_ahg_sample_course.py`. Mark Auto-08.
7. `python scripts/build_ahg_kit.py --no-axe`, then `git status`. Only the zip in `docs/ahg-2026/dist/` may change. Mark Auto-09.
8. Auto-06 and Auto-07 come later: Auto-06 in sitting C, step 14, and Auto-07 in sitting D.
9. Clone Accessibility Agents beside GLOW and check out the commit in `docs/ahg-2026/kit/accessibility-agents-skills.json`. Do AA-01 to AA-08 as their Steps columns say. Mark each.

### 3.4 Sitting C: the GLOW pages

Start GLOW locally as section 1.7 describes, on the `feat/ahg-three-paths`
branch, and use `http://127.0.0.1:5000` in place of `https://letitglow.app`.
Use Chrome, no screen reader, mouse and keyboard.

1. Open `/ahg`. Accept the consent page if this is GLOW running locally. Check every item in Setup-01's Expected column. Mark Setup-01.
2. In a private window, open `/ahg`, `/ahg/paths`, `/ahg/assistant` and `/workshop/ahg-2026/share`. None should show a consent page. Mark Setup-13.
3. Open each address in Setup-14. Each must arrive at `/ahg`. Mark Setup-14. (The `www` address works only on production; mark it in sitting D.)
4. In a private window, open `/workshop/ahg-2026/kit.zip` and `/workshop/ahg-2026/ahg-2026.code-profile` directly. Both download. Mark Setup-12.
5. Open `/ahg/paths`. Read it top to bottom against Assist-06. Mark Assist-06. Leave Assist-07 for sittings E to G, where you meet the real screens.
6. Open `/ahg/assistant`. Check Assist-01. Mark it.
7. Press "Copy the text for Block 1: the ready check". Open Notepad and paste. The text starts "AHG 2026 Accessibility Agents workshop. Block 1". The message under the button says it is copied and how to paste. Do the same for blocks 2, 3, 4, 6 and 7. Mark Assist-02.
8. In Chrome, open Settings, Privacy and security, Site settings, Clipboard, and add `127.0.0.1:5000` to "Not allowed". Reload `/ahg/assistant` and press block 2's Copy button. The "Read the text first" section opens, the text is selected, and the message says to press Control+C. Remove the site from "Not allowed" afterwards. Mark Assist-04.
9. In Chrome, open Settings, Privacy and security, Site settings, JavaScript, and add `127.0.0.1:5000` to "Not allowed". Reload `/ahg/assistant`. No Copy buttons show, and every "Read the text first" still opens. Remove the setting afterwards. Mark Assist-05.
10. Open `/ahg/kit`, then a step card, the faculty coach in Ready-made agents, and `/ready-check` in The Copilot commands. Each has "Copy this file's text", a plain-text link that opens as text, and the step card a Word file. Mark Setup-16.
11. Open `/workshop/ahg-2026/share`. Do Share-12, Share-13, Share-14 and Share-15 in that order, as their Steps columns say. For Share-14, open the downloaded `SKILL.md` in Notepad and compare. Mark each.
12. On the same page, do Share-05, Share-06, Share-07 and Share-09. Mark each.
13. Open `docs/ahg-2026/kit/share-my-agent.html` from the repository in Chrome, by double-clicking it. Repeat Share-01, Share-12 and Share-14 on it. Mark Share-08.
14. Tab once on `/ahg`, `/ahg/paths`, `/ahg/assistant`, `/ahg/kit`, `/ahg/site` and the share page, and press Enter. Mark Setup-18. Then run the axe sweep in `web/e2e` as `web/e2e/README.md` describes, adding `/ahg/assistant` and `/ahg/paths`. Mark Auto-06.
15. Zoom Chrome to 200 percent, then 400 percent, on `/ahg`, `/ahg/paths`, `/ahg/assistant` and the share page. Nothing is cut off; the page never scrolls sideways; the paths table scrolls inside its own box. Mark A11y-02.
16. Do every page in this sitting once more by keyboard only: Tab, Shift+Tab, Enter, Space. Mark A11y-01 for these pages.
17. Open `/ahg/site`, then the course announcement. Run Accessibility Insights FastPass on it and compare with `docs/ahg-2026/kit/sample-course/evidence/psy101-announcement.txt`. Mark Setup-17.
18. Stop GLOW. Write any defect in section 2.14 before you go on.

### 3.5 Sitting D: merge, deploy, and the production check

1. Open the pull request for `feat/ahg-three-paths` and wait for every check. Mark Auto-07.
2. Merge it. GitHub Actions deploys `main` to letitglow.app.
3. Sync the workshop repository so its copy of the kit matches: `python scripts/sync_ahg_repo.py ../ahg-2026`, from a checkout of Community-Access/ahg-2026 beside GLOW, then commit and push there.
4. Open `https://letitglow.app/ahg`, `/ahg/paths`, `/ahg/assistant` and the share page. All four load, and `/ahg/assistant` has six Copy buttons.
5. Open `https://www.letitglow.app/ahg`. It arrives at `letitglow.app/ahg`. Finish marking Setup-14.
6. From here on, everything runs against `https://letitglow.app`.

### 3.6 The answers you give, on every path

Use these in sittings E, F and G, so every path gets the same input. In
block 2, answer each question with the line for it, and nothing more.

The main run, role card "documents and alternate formats":

| Question | Type this |
|---|---|
| Role card and problem | Documents and alternate formats. When a student needs a scanned course reading in large print, we lose days working out what to produce and who checks it. |
| Which ready-made agent to start from | Start from the alternate format planner. |
| Role | You are an alternate format planner in a university disability resource center. You work for the specialist who handles accommodation requests. |
| Task | Given a checker's report on a course document and the formats a student needs, plan how to deliver those formats, in order, with who does each step. |
| Trusted guidance | WCAG 2.2, especially 1.4.5 Images of Text and 1.1.1 Non-text Content, the ACB Large Print Guidelines, and our center's alternate format procedure. |
| Output format | The problem in one line, numbered steps with who does each, the formats to deliver, then a checklist. |
| Human review | The alternate format specialist checks the converted text against the original page by page, and the student confirms the format works. |
| Name and institution | Use the tester's own name and "AHG test run" as the institution, for example: Jeff Bishop, AHG test run |

For Design-06, the other two role cards, give these shorter answers and
accept the assistant's suggestions for the rest:

| Role card | Problem to type |
|---|---|
| Course content and faculty coaching | Course content and faculty coaching. Faculty keep sending syllabi with fake headings and "click here" links, and fixing them myself does not scale. |
| Compliance and procurement | Compliance and procurement. For Title II we need a dated log of every barrier in a course and who approved each fix. |

For Design-07, the privacy trap, answer the problem question with this
instead, in a separate conversation:

| Question | Type this |
|---|---|
| Role card and problem | Documents and alternate formats. Maria Testperson, a student with low vision and an extended time accommodation, needs her PSY 101 reading in large print by Friday. |

The assistant must decline to use the name and accommodation, and remind you
to keep it private.

For block 3, when asked which file, type: `psy101-reading-forgetting-scanned.pdf`.

For block 4, use the same file first. Then, for Ground-01 to Ground-07, type
each of these in turn, in the same conversation, one per message, and keep
each answer:

1. Now do the same for psy101-syllabus.docx.
2. Now do the same for psy101-week3-lecture.pptx.
3. Now do the same for psy101-gradebook.xlsx.
4. Now do the same for psy101-reading-forgetting-scanned.pdf.
5. Now do the same for psy101-lab1-stroop.pdf.
6. Now do the same for psy101-announcement.html.
7. Now do the same for psy101-week3-captions.vtt.

For block 7, answer the six questions with these:

| Question | Type this |
|---|---|
| One workflow | Plan alternate formats for the next five scanned readings that come in. |
| One partner | Our alternate format specialist. |
| One safeguard | A person checks every converted page against the original before it goes to a student. |
| First step this week | Run the planner on one request we already finished, and compare its plan with what we did. |
| Who needs to know | My director. |
| If it worked | We sent the first large print reading two days sooner, and nothing was wrong in it. |

### 3.7 Sitting E: the browser path, the whole day, in ChatGPT

Use Chrome, no screen reader, the `ahg-test-browser` GitHub account and the
ChatGPT test account. Keep `letitglow.app/ahg/assistant` in the first tab
and chatgpt.com in the second. Every paste below means: on
`/ahg/assistant`, press that block's Copy button, press Control+Tab, move to
the message box ("Chat with ChatGPT"), press Control+V, and press Enter.
Wait until the answer stops growing before you read it.

#### Sitting E: setup

1. Follow step card 0, "Everyone", with `ahg-test-browser`. Mark SetupB-01.
2. Sign in to chatgpt.com. The message box is labelled "Chat with ChatGPT". Mark SetupB-02.
3. Profile menu, Settings, Data controls: find "Improve the model for everyone" and turn it off. If the name or the place differs, note the real one for `/ahg/paths`. Mark SetupB-03, and the ChatGPT part of Assist-07.
4. Start a new chat. Paste block 1. Check SetupB-04's Expected column. Find the Copy button on the template's code block. Mark SetupB-04.
5. Follow step card 0's last browser step: share the practice agent with "Fill in the practice template". Within about a minute the issue reply begins "Well done". Mark SetupB-05.

#### Sitting E: block 2, in the same chat

6. Paste block 2. Answer with section 3.6's main run. Mark Design-01 and Design-02 in the ChatGPT column.
7. Read the code block: six headings, the Never section as in the template, `name: alternate-format-planner` or another lowercase hyphenated name, `author` in double quotes with your name, WCAG 2.2 links. Mark Design-03.
8. Read the lines after it. Mark Design-04.
9. Press the code block's Copy button. On `/ahg/share`, paste into "Your agent, as text" and press "Download as `SKILL.md`". Open the file: it starts with three dashes and `name:`. Mark Design-05. Keep this file all day; it is your agent.
10. Start a second chat, paste block 2, and run the faculty coaching card from section 3.6. Start a third chat for compliance. Mark Design-06.
11. Start a fourth chat, paste block 2, and use the privacy trap. Mark Design-07.
12. Start a fifth chat. On `/ahg/kit`, open Ready-made agents, then Faculty coach, and press "Copy this file's text". Paste it into the chat as your agent, then paste block 3. The assistant uses it. Mark Design-08.
13. Go back to the first chat for the rest of the day.

#### Sitting E: block 3

14. Paste block 3. It names your agent from block 2 and suggests a file. Type `psy101-reading-forgetting-scanned.pdf`. Mark Try-01.
15. Read the answer: it is in your agent's output format, with no checker findings. Mark Try-02. Read the note after it. Mark Try-03.
16. For each of the six ready-made agents, start a new chat, paste the agent from `/ahg/kit`, then paste block 3. Mark Try-04 when all six answer in their own output format.
17. Start a new chat and paste block 3 with no agent. It asks you to paste your agent and waits. Paste the `SKILL.md` you downloaded in step 9. It carries on. Mark Try-05.

#### Sitting E: block 4, back in the first chat

18. Paste block 4. Use the same file. Read the answer and the before and after. Keep both in your notebook.
19. Type each of the seven lines in section 3.6, block 4, one at a time. Check each answer against Ground-01 to Ground-07 and mark each.
20. Compare the scanned reading's block 3 and block 4 answers. Mark Ground-08.
21. Open `psy101-syllabus.docx` from `/ahg/site` in Word. Review, Check Accessibility. Copy the results pane's list, paste it into the chat, and type: Use these Word results instead. Mark Ground-09.
22. Read every block 4 answer once more for "compliant", "accessible" as a verdict, and anything not in the evidence. Mark Ground-10.
23. Mark Ground-11 once, from `answer-key.md` and the evidence files; it does not depend on the path.

#### Sitting E: block 5, back in the first chat

24. Paste block 5, about 31 KB. ChatGPT accepts it as one message. If it refuses, note the exact words: that is a defect against D20. Mark Office-01.
25. Watch it run. One line per file. Mark Office-02. If it stops, type `continue`. Mark Office-06.
26. Read the report against Office-03 and Office-04. Keep it. Mark both.
27. Start a new chat and paste block 5 with no agent. It says so kindly and offers the ready-made agents. Mark Office-05.
28. Note any message about limits, slower answers or a smaller model, and when it appeared. Mark Office-08 in the ChatGPT column.

#### Sitting E: block 6

29. On `/ahg/share`, leave "My real agent" chosen, choose the `SKILL.md` from step 9, and check the name fills in. Mark Share-01.
30. Press "Open the share form on GitHub". Mark Share-02.
31. Tick the privacy box and press "Submit new issue". Within about a minute the reply begins "Your agent is in". Mark Share-03 and, as this is a new account, Share-04, in the ChatGPT column.

#### Sitting E: block 7, back in the first chat

32. Paste block 7. Answer with section 3.6, block 7. Mark Plan-01 and Plan-02.
33. Open `letitglow.app/w/ahg-2026/11`, join with the access code, and add: `Test commitment from the browser path.` Mark Wall-01.
34. Open the wall as section 2.12 describes. Your commitment shows, with no name. Mark Wall-02.
35. On `/ahg/assistant`, under "Accessibility Agents in any assistant", do AA-15, then AA-11 to AA-14 in the ChatGPT column, one new chat each. Mark each. (D-011 is fixed; ready to run.)

Close the sitting: write down how long each block took, for Dry-01, and any
step where a step card's words did not match the screen, for Mat-05.

### 3.8 Sitting F: VS Code on a computer, the whole day

Use Windows, no screen reader, the `ahg-test-desktop` GitHub account. Do
SetupD-01 on the work laptop without administrator rights if you have one;
otherwise mark it Not applicable and do it in sitting J.

#### Sitting F: setup

1. Install VS Code. Help, About shows 1.143 or later. Mark SetupD-01.
2. Accounts menu, sign in with GitHub as `ahg-test-desktop`. Hover the Copilot icon in the status bar; it shows Copilot Free. Mark SetupD-02.
3. Import the profile from its address, as step card 0 says. Note the exact names of the menu and button you used, for Assist-07. Mark SetupD-03. Delete the profile and repeat with the downloaded file. Mark SetupD-04.
4. Download and unzip the kit from letitglow.app/ahg. File, Open Folder. If Restricted Mode shows, Manage, then Trust. Note the exact words. Mark SetupD-05 and the VS Code part of Assist-07.
5. In a VS Code profile without the AHG profile's extensions, open the kit and check the recommended extensions offer. Mark SetupD-06.
6. Open Copilot Chat with Control+Alt+I. Type `/` and read the list. All eight commands are there with their descriptions, and the six Accessibility Agents entry points. Mark SetupD-07, and AA-10 in the Desktop column.
7. Type `/ready-check`. Mark SetupD-08. Then do SetupD-09, renaming `office-team` in the Explorer with F2.
8. New Chat, open the Session Target control, choose Local, and type `/ready-check`. Record whether it runs. Mark SetupD-10.
9. Share the practice agent, choosing `my-agent/SKILL.md`. Mark SetupD-11.

#### Sitting F: block 2

10. New Chat. Type `/design-my-agent`. Answer with section 3.6's main run. Allow Copilot to edit the file when it asks. Mark Design-01 to Design-04 in the Desktop column. Open `my-agent/SKILL.md` and check it as in sitting E, step 7.
11. Design-05 is Not applicable on this path; mark it so.
12. Copy `my-agent/SKILL.md` to your notebook. For Design-06, run `/design-my-agent` twice more with the other cards, saying "start from a copy, do not overwrite my agent" if Copilot offers to replace it. Put your main agent back afterwards. Mark Design-06.
13. New Chat, privacy trap. Mark Design-07.
14. Fallback: open `examples/agents/faculty-coach/SKILL.md`, select all, copy, open `my-agent/SKILL.md`, select all, paste, change the author line, save. Run `/ready-check`. Mark Design-08. Put your main agent back.

#### Sitting F: blocks 3 to 7

15. `/try-my-agent`, with section 3.6's file. Mark Try-01 to Try-03. For Try-04, copy each ready-made agent over `my-agent/SKILL.md` in turn and run `/try-my-agent`; put your main agent back after. Mark Try-05 Not applicable.
16. `/ground-my-agent`, the same file, then the seven lines in section 3.6. Mark Ground-01 to Ground-10, and Ground-09 with Word as in sitting E.
17. Share the real agent from `my-agent/SKILL.md`. Mark Share-01 to Share-04 in the Desktop column.
18. `/run-the-office`. Use Alt+F2 to read the whole report. Mark Office-01 to Office-04 and Office-06. Copy the template over `my-agent/SKILL.md`, run it again, mark Office-05, and put your agent back.
19. Office-07, the facilitator's room run: make a `room/` folder in the kit, and copy into it each `agents/<login>/<name>/` folder from the ahg-2026 repository (the shares from sittings E, F and G, once G is done; come back to this step then). Run `/run-the-office`. Mark Office-07.
20. On github.com, signed in as `ahg-test-desktop`, open your Copilot settings and record how much of the allowance the day used. Mark Office-08 in the Desktop column.
21. `/my-30-day-plan` with section 3.6's answers. `my-30-day-plan.md` exists. Mark Plan-01 and Plan-02.

#### Sitting F: Accessibility Agents

22. Mark AA-16 from block 2 and AA-17 and AA-18 from blocks 3 to 5, if you ran /install-my-agent and /review-my-agent there; if not, run them now on your main agent.
23. New Chat. Do AA-11, AA-12, AA-13 and AA-14 as their Steps columns say. Mark each in the Desktop column.
24. Do AA-21 in a new empty folder. Mark it.

### 3.9 Sitting G: VS Code for the Web, the whole day

Use Chrome first, no screen reader, the `ahg-test-web` GitHub account, and a
fresh unzipped copy of the kit, not the one from sitting F.

#### Sitting G: setup

1. Open vscode.dev. Press Control+Alt+I. Confirm SetupW-01 still holds.
2. Choose Open Folder and pick the fresh kit. Write down the exact words of each browser prompt and the button you chose. Mark SetupW-03 and the vscode.dev part of Assist-07; correct `/ahg/paths` and step card 0 if the words differ.
3. Accounts menu, sign in with GitHub as `ahg-test-web`. Mark SetupW-04.
4. In Chat, type `/`. Mark SetupW-05. Type `/ready-check`. Mark SetupW-06.
5. Press Control+N in the Chat view. Mark SetupW-08.
6. Close the tab, reopen vscode.dev, and open the kit from Open Recent. Mark SetupW-07.
7. Share the practice agent from `my-agent/SKILL.md`, choosing the file from the fresh kit.

#### Sitting G: blocks 2 to 7

8. Repeat sitting F, steps 10 to 23, at vscode.dev, marking the Web column. Office-07 is Not applicable on this path. For Office-08, record the `ahg-test-web` allowance.
9. Open Edge and repeat steps 1 to 4. Then open Safari or Firefox if you have them, and confirm Open Folder is not offered or does not work. Mark SetupW-02.
10. Zoom VS Code in twice (Control+=) at vscode.dev and in sitting F's VS Code. Chat and editor still work. Mark A11y-04.

### 3.10 Sitting H: screen readers

Run each path again with the screen reader as the only way you use the
computer: no mouse, no looking. Use the same answers. You may stop each run
after block 4 if blocks 5 to 7 already passed by ear on another path, but
run every path's setup and block 2 in full.

1. NVDA with Chrome (Env-2), the browser path: sitting E, steps 1 to 26. Mark SetupB-06, Design-09 (ChatGPT column), Share-10 (ChatGPT column), and Assist-03 on `/ahg/assistant`.
2. NVDA with Chrome, `/ahg`, `/ahg/paths` and `/ahg/assistant`, by headings (H), lists (L) and tables (T). Mark Setup-11.
3. NVDA, VS Code on a computer: sitting F, steps 6 to 17. Use Alt+F2 for every long answer, and Alt+F1 once to hear the chat's accessibility help. Mark Design-09 and Share-10 in the Desktop column.
4. NVDA, VS Code for the Web in Chrome: sitting G, steps 1 to 4, then blocks 2 and 3. Mark Design-09 in the Web column.
5. JAWS with Edge (Env-3): the browser path, sitting E, steps 1 to 18, and VS Code on a computer, sitting F, steps 6 to 10. Mark Env-3's paths in section 2.3a.
6. Read the commitment wall with NVDA. Mark Wall-03.
6a. NVDA, VS Code on a computer: AA-11 and AA-17. Mark AA-19 in the Desktop column; repeat on the browser path for the ChatGPT column.
7. Note every place a step card's words did not match what you heard. Mark Mat-05 after the fixes.

### 3.11 Sitting I: the deck and the materials

1. Open `/workshop/session/ahg-2026/deck`. Do Deck-01 to Deck-06 and Deck-10 to Deck-12 in order. Mark each.
2. Open `docs/ahg-2026/slides.pptx` in PowerPoint; Review, Check Accessibility. Mark Deck-07. Read it with NVDA. Mark Deck-08.
3. Open `docs/ahg-2026/slides.docx` in Word; Check Accessibility. Mark Deck-09.
4. Open each of the seven sample course files. Mark Mat-01. Mark Mat-02 from sitting B's Auto-08.
5. Open each step card's Word file in Word; Check Accessibility; check each numbered list starts at 1. Mark Mat-04.
6. Read the three worked examples aloud against the deck. Mark Mat-03.
7. Read `pre-event-message.md` as a participant. Mark Mat-06.
8. Replace the written before and after in each worked example with the real answers you kept in sitting E, steps 15 and 18, still labelled as examples. Rebuild with `python scripts/build_ahg_kit.py --no-axe`. Mark Mat-07.
9. Turn on Windows reduced motion (Settings, Accessibility, Visual effects, Animation effects off). Open the deck and the AHG pages. Mark A11y-03.

### 3.12 Sitting J: the workshop repository and the fallbacks

1. Do Repo-01 to Repo-06 with the practice and real agents, as each row says. For Repo-04, edit the issue from Repo-03. Mark each.
2. Repo-07: in a scratch checkout of Accessibility Agents, run the promote script. Mark it. Delete the scratch checkout.
2a. AA-20: follow the Codespaces steps in `accessibility-agents.md` with `ahg-test-web`, then stop the codespace from github.com/codespaces. Mark it. Optionally do AA-22.
3. Share-11: ask nine people, or use nine browser windows signed in to your three test accounts in turn, to share within two minutes. Mark it.
4. Load-01: from one network, start 40 downloads of `kit.zip` within a minute, for example 40 browser tabs. Mark it.
5. Fall-01: with the kit downloaded, turn off wifi. Open the kit, the sample course, the evidence, the step cards and the examples. Mark it.
6. Fall-02: sign in to VS Code with an account that has used its Copilot allowance, or wait for one of the test accounts to run out. Follow the step card's switch to the browser path. Mark it.
7. Fall-03: on the work laptop without administrator rights, try the profile import. If it is refused, take the SetupD-06 route, or the browser path. Mark it, and SetupD-01 if you skipped it in sitting F.
8. Fall-04: with GitHub blocked (turn off wifi after opening the share page), save the agent with "Download as `SKILL.md`". Mark it.
9. Fall-05: with the projector off, run one block from the pocket card and step cards alone. Mark it.
10. Fall-06: in the middle of block 3 in VS Code, switch to the browser path as `/ahg/paths` "Switching paths" says, and finish the block in ChatGPT. Mark it.

### 3.13 Sitting K: other assistants, optional

For each assistant in section 2.3b, Alt-01 to Alt-04, start a new conversation and run block 1,
block 2 with section 3.6's main run, and block 6. Keep each answer. Mark the
row. Note anything `/ahg/paths` says about it that turns out to be wrong.
Only call an assistant "tested" in the setup message once its row passes. Alt-05, ChatGPT signed out, is already recorded; re-run it only if OpenAI changes how signed-out chats work.

### 3.14 Sitting L: the Mac

Give the Mac tester this plan, sittings E to H. They run Env-4 (Safari and
VoiceOver for the browser path; Chrome and VoiceOver for VS Code for the
Web) and Env-5 (Chrome, keyboard only), on all three paths, with their own
new GitHub accounts. On a Mac, Copilot Chat opens with Control+Command+I,
the plain text view of an answer is Option+F2, paste is Command+V, and
switching tabs is Control+Tab. Collect their results into this file.

### 3.15 Sitting M: the timed dry runs

1. With the beginner tester, run the whole day on the browser path, with the deck on a second screen and you presenting. Time each block. Mark Dry-01, first half. Block 2 alone must take under 60 minutes for the beginner, including reading the example: mark Design-10 in the ChatGPT column.
2. On another day, run it again on VS Code on a computer. Time each block. Mark Dry-01. Mark Design-10 in the Desktop column from block 2's time. Time block 2 once at vscode.dev with the same tester, or a second beginner, for the Web column.
3. Write the real minutes beside section 2 of `run-of-show.md`. Any block over by more than five minutes gets a fix in the step card or the agenda.

### 3.16 Sitting N: clean up, results and sign-off

1. In Community-Access/ahg-2026, delete the test agents in `practice/` and `agents/` from the three test accounts, close the test issues, and rebuild the gallery, as section 1.5, step 4, says.
2. Fill in section 2.14a, "Results so far", with the date and what passed.
3. Close every defect in section 2.14, or write its accepted workaround.
4. Fix every step card and `/ahg/paths` line that Assist-07 and Mat-05 found, rebuild the kit, and re-run sitting B.
5. Sign each line in section 2.15.
6. Commit this file with the results, and sync the workshop repository once more.
