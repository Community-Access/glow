---
title: "AHG 2026 Accessibility Agents: instructions and test plan"
lang: en
author: "Jeff Bishop, BITS"
description: "How to run, rehearse and fully test the AHG 2026 Accessibility Agents workshop before 16 November 2026."
---

# AHG 2026 Accessibility Agents: instructions and test plan

This is the single document for getting the Accessing Higher Ground 2026
workshop from "built" to "tested and ready". Part 1 explains the course and
how to run it. Part 2 is the complete test plan. The workshop is ready when
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
| `kit/.github/prompts/` | The six Copilot commands, one per block |
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
English, puts it to work with GitHub Copilot in VS Code on a sample course,
grounds it in checker evidence so it cites WCAG 2.2, opens a pull request to
the open-source Accessibility Agents project, adds it to an agent team that
works through the whole course, and leaves with a 30-day plan.

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
| `.github/prompts/*.prompt.md` | One Copilot command per block |
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
Copilot Chat.

| Time | Block | Command | Participant has at the end |
|---|---|---|---|
| 10:00 | Setup table outside the room | `/ready-check` | A ready laptop |
| 10:30 | 1. Why we are here | `/ready-check` | The journey, and the finished result in view |
| 10:50 | 2. Design your agent | `/design-my-agent` | `my-agent/SKILL.md` with their name on it |
| 11:50 | 3. Your agent at work | `/try-my-agent` | A first answer on a course document |
| 12:15 | Lunch | none | |
| 1:15 | 4. Ground it | `/ground-my-agent` | Cited answers from evidence; a before and after |
| 2:10 | Break | none | |
| 2:20 | 5. Share it | `letitglow.app/ahg/share` | Their agent in the collection, committed in their name |
| 3:00 | 6. Build the office | `/run-the-office` | A team report with their agent's section |
| 3:45 | 7. Take it home | `/my-30-day-plan` | `my-30-day-plan.md` and a commitment on the wall |
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
   share page all work (tests Setup-01 to Setup-04, Setup-14).
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
python scripts/build_ahg_kit.py --axe-js web/node_modules/axe-core/axe.min.js
flask --app acb_large_print_web.app:create_app workshop-deck --code ahg-2026
python scripts/sync_ahg_repo.py ../ahg-2026
```

The kit build needs Python with python-docx, python-pptx, openpyxl, Pillow,
PyMuPDF and Playwright, and Chrome installed for the axe step. Never edit
`slides.*`, the step card Word files, the evidence files or
`share-my-agent.html` by hand; they are generated.

### 1.7 Running GLOW locally for testing before the merge

Testers can run every GLOW page from the branch on their own machine before
anything is deployed. In PowerShell, from `web/` in a checkout of the
`feat/ahg-2026-workshop` branch:

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

1. From 10:00, helpers run the setup table outside the room with
   `/ready-check`.
2. Every block: show the finished result, demo it on the projector, then
   participants run the block's command with its step card.
3. Anyone stuck uses a ready-made agent from `examples/agents/` and keeps
   going. Say often that this counts.
4. In block 5, project the collection and refresh it as agents arrive;
   read each name aloud. Helpers watch the issues labelled needs-a-hand.
5. In block 6, everyone runs their own team; the projector run with every
   shared agent comes last, from a `room/` folder in your kit.
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

Record results in the Result column: Pass, Fail (with a defect number), or
Not applicable (with a reason). Keep this file as the record; commit it with
results filled in.

### 2.2 People and accounts

The test plan needs the following people and accounts.

| Role | Who | Needs |
|---|---|---|
| Facilitator tester | Jeff | Admin on Community-Access/ahg-2026 and merge rights on Accessibility Agents; facilitator key |
| Beginner tester | Someone who has never opened VS Code | A brand-new GitHub account made for the test |
| Screen reader tester, Windows | An experienced NVDA and JAWS user | A Windows laptop, a new GitHub account |
| Screen reader tester, Mac | An experienced VoiceOver user | A Mac, a new GitHub account |
| Helper | Anyone | Reads the run of show and the fallback ladder |

Every tester account must have Copilot Free turned on. Use new accounts:
an account that already has Copilot Pro hides the free-tier limits this
plan has to measure.

Testers share into the real workshop repository with "My practice
agent", which lands in `practice/` and never reaches Accessibility Agents.
Clear test agents and issues afterwards (section 1.5, step 4).

### 2.3 Test environments

Each required row must be run at least once, start to finish, from Setup-02
to Office-06.

Jeff tests on Windows only. The Mac rows, Env-4 and Env-5, need a separate
tester with a Mac; until one is found they stay open, and sign-off lists
them as the one remaining gap rather than marking them Not applicable.

| ID | Operating system | Browser | Assistive technology | Required |
|---|---|---|---|---|
| Env-1 | Windows 11 | Chrome | None, mouse and keyboard | Yes |
| Env-2 | Windows 11 | Chrome | NVDA, current release | Yes |
| Env-3 | Windows 11 | Edge | JAWS 2026 | Yes |
| Env-4 | macOS, current release | Safari | VoiceOver | Yes |
| Env-5 | macOS, current release | Chrome | None, keyboard only | Yes |
| Env-6 | Windows 11, work laptop without administrator rights | Edge | None | Yes |
| Env-7 | Any | Any | Screen magnification at 200 percent and 400 percent zoom | Yes |
| Env-8 | Any | Any | Windows high contrast mode or a forced dark theme | No |

### 2.4 Automated checks

Run these first, from the repository root on the branch. All must pass
before manual testing starts, and again after any fix.

| ID | Command | Expected | Result |
|---|---|---|---|
| Auto-01 | `python -m pytest web/tests -q` with `PYTHONPATH=web/src;desktop/src` | All pass (1106 passed, 31 skipped at build time) | Pass, Claude, 10 Oct: 1112 passed, 31 skipped |
| Auto-02 | `python -m pytest web/tests/test_workshop_ahg_kit.py web/tests/test_workshop_deck.py web/tests/test_workshop_deck_formats.py web/tests/test_workshop_agenda.py -q` | All pass | Pass, Claude, 10 Oct |
| Auto-03 | `python -m pytest desktop/tests/test_md_auditor_false_positives.py desktop/tests/test_md_auditor_feature_parity.py -q` with `PYTHONPATH=desktop/src` | All pass | Pass, Claude, 10 Oct: 16 passed |
| Auto-04 | `python scripts/check_material_conformance.py` | "Every material conforms" | Pass, Claude, 10 Oct |
| Auto-08 | `python scripts/check_ahg_sample_course.py` | 42 of 42 pass | Pass, Claude, 10 Oct |
| Auto-05 | `python scripts/audit_ahg_docs.py` | "0 not passing" | Pass, Claude, 10 Oct: 34 documents |
| Auto-06 | The axe sweep in `web/e2e`, run as described in `web/e2e/README.md` | No violations on the workshop deck pages | |
| Auto-07 | GitHub Actions on PR #116 | All required checks green | Pass, Claude, 10 Oct, after fixing D-001 |

### 2.5 Setup and the setup page

These cover everything a participant does before the day.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Setup-01 | Open `/ahg` | Page loads; heading "Accessibility Agents at AHG 2026"; five numbered setup steps; the day's schedule; links to the kit, the profile, the share page, the slides and eight step cards; the two rules | Pass, Claude, 10 Oct |
| Setup-02 | Make a new GitHub account and turn on Copilot Free, following step card 0 | Account made; Copilot Free shows as active in GitHub settings | |
| Setup-03 | Install VS Code on Env-6 without administrator rights | Installs and opens | |
| Setup-04 | In VS Code, Command Palette, "Profiles: Import Profile", paste the profile address from the setup page | VS Code shows the "AHG 2026 Accessibility Agents" profile; importing installs GitHub Copilot Chat, GitHub Pull Requests, GitHub Repositories and the axe Accessibility Linter; editor text is 18pt | |
| Setup-05 | Repeat Setup-04 with the downloaded `.code-profile` file instead of the address | Same result | |
| Setup-06 | Sign in to GitHub in VS Code from the Accounts button | Signed in; Copilot Chat available | |
| Setup-07 | Download the kit from the setup page, unzip, and open the folder (File, Open Folder) | VS Code asks whether to trust the folder; after yes, `README.md` opens as the welcome page | |
| Setup-08 | Open the kit in a VS Code without the profile | VS Code offers the kit's recommended extensions; installing them gives the same set as Setup-04 | |
| Setup-09 | Open Copilot Chat with Control+Alt+I or Command+Control+I and type `/ready-check` | The command appears in the slash list with its description; Copilot reports five checks as Ready and ends with "You are ready for 16 November." | |
| Setup-10 | Rename `office-team` and run `/ready-check` again, then rename it back | Copilot reports that step as "Needs a hand", suggests one thing, and gives the support address | |
| Setup-11 | Read the setup page with a screen reader | One H1, H2s for each part, numbered list announced, every link name says where it goes | Pass, Claude, 10 Oct, axe clean; screen reader listen still to do |
| Setup-12 | Download `kit.zip` and the profile with no GLOW consent cookie (private window, direct links) | Both download without the consent page | Pass, Claude, 10 Oct |
| Setup-13 | Open the landing page and the share page in a private window | Both open straight away, with no consent page; the GLOW tools still ask | |
| Setup-14 | Open `letitglow.app/AHG`, `/ahg2026`, `/ahg-2026`, `/ahg/`, `www.letitglow.app/ahg` and `letitglow.app/workshop/ahg-2026` | Every one arrives at `letitglow.app/ahg` | |
| Setup-15 | Share the practice agent from step card 0, step 8 | Within about a minute the issue gets a reply beginning "Well done", and the agent is in `practice/<account>/SKILL.md` | |
| Setup-16 | Open `/ahg/kit`, then a step card, an agent and a Copilot command from it | Each reads as a page with its headings; each has a plain-text address that opens as text; the step cards offer their Word file | |
| Setup-17 | Open `/ahg/site`, then the course announcement; run Accessibility Insights FastPass on it | The index is accessible; the announcement shows its planted barriers, and FastPass finds what its checker report lists | |
| Setup-18 | Tab once on `/ahg`, `/ahg/kit`, `/ahg/site` and the share page, then press Enter | The first stop is Skip to main content, and Enter moves to the page content; no GLOW navigation on any of them | Pass, Claude, 10 Oct |

### 2.6 Block 1: Why we are here, and the deck

These cover the opening and every format of the deck.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Deck-01 | Open `/workshop/session/ahg-2026/deck` | 26 slides; first title "Accessibility Agents"; subtitle is the program title word for word | Pass, Claude, 10 Oct |
| Deck-02 | Move through the deck with arrow keys, Page Up and Page Down, Home and End | Each change moves focus to the slide heading and is announced politely | Pass, Claude, 10 Oct |
| Deck-03 | Turn speaker notes on and off with the `n` key and the button | Notes show and hide; state is announced | Pass, Claude, 10 Oct |
| Deck-04 | Use "Read as one page" | The deck becomes one document with one heading per slide | |
| Deck-05 | Print or print to PDF | One slide per page, notes included, body text 18pt | |
| Deck-06 | Download the deck as one file with `?download=1`, open it offline | Works with no network; no external scripts or styles | Pass, Claude, 10 Oct |
| Deck-07 | Open `slides.pptx` in PowerPoint; run Review, Check Accessibility | No errors; every slide has a title; reading order matches the screen | |
| Deck-08 | Read `slides.pptx` with NVDA or JAWS in PowerPoint | Titles, body and table on slides 3, 8, 10, 16 and 24 read in order; speaker notes in the notes pane | |
| Deck-09 | Open `slides.docx` in Word; run Check Accessibility | No errors; one heading per slide; speaker notes under "Speaker notes, slide N" | |
| Deck-10 | Compare the clock times on slides 5, 9, 12, 14, 15, 18, 19, 21, 24, 25 and 26 with section 1.4 | Every time matches | |
| Deck-11 | Read slides 1, 2 and 6 aloud with their speaker notes | Key point first, the Title II problem, the AI context and the privacy rule are all there | |

### 2.7 Block 2: Design your agent

These cover the most important hands-on block.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Design-01 | Type `/design-my-agent`; pick "documents and alternate formats"; give a real problem | Copilot names the two matching ready-made agents and offers to start from one | |
| Design-02 | Answer the five questions, borrowing from the example when unsure | Copilot asks one question at a time and waits | |
| Design-03 | Let Copilot write the file | `my-agent/SKILL.md` keeps the six headings and the Never section exactly; `name` is lowercase with hyphens; `author` is the tester's name; WCAG 2.2 links kept | |
| Design-04 | Read Copilot's summary | Five lines or fewer; one specific thing the agent does well; ends "Your agent exists." | |
| Design-05 | Repeat Design-01 to 04 for the other two role cards | Same, with the matching examples | |
| Design-06 | When asked for the problem, include a made-up student name and accommodation | Copilot declines to use it and reminds the tester to keep it private | |
| Design-07 | Fallback: copy `examples/agents/faculty-coach/SKILL.md` over `my-agent/SKILL.md` and change the author line, following step card 2 | Works by keyboard; the ready check still passes | |
| Design-08 | Do the whole block with a screen reader only | Every Copilot question and answer is readable in the chat view; the accessible view (Alt+F2) reads the full response | |
| Design-09 | Time the block for the beginner tester | Under 60 minutes including reading the example | |

### 2.8 Block 3: Your agent at work

These check the agent's first answer, before it has any evidence.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Try-01 | Type `/try-my-agent`; accept Copilot's suggested file | The suggestion fits the agent's task | |
| Try-02 | Read the answer | Answers as the agent; does not open `sample-course/evidence/` | |
| Try-03 | Read Copilot's note after the answer | One thing done well; one place it guessed; ends with the after-lunch line | |
| Try-04 | Run it with each of the six ready-made agents | Each produces an answer in its own output format | |

### 2.9 Block 4: Ground it

These prove that evidence changes the answers, for every kind of file.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Ground-01 | `/ground-my-agent` with the syllabus | Reads `evidence/psy101-syllabus.txt`; cites at least one WCAG 2.2 criterion with a link; lists what a person must still check | |
| Ground-02 | Same with the lecture | Mentions untitled slides and reading order; flags "image.png" alt text only as something a person must check | |
| Ground-03 | Same with the gradebook | Mentions merged cells and color-only status | |
| Ground-04 | Same with the scanned reading | Says the pages are pictures of text; cites 1.4.5 | |
| Ground-05 | Same with the lab handout | Mentions untagged PDF; says the color-dependent exercise needs an alternative, not an edit | |
| Ground-06 | Same with the announcement page | Uses the axe evidence: contrast, missing alt, language, heading order | |
| Ground-07 | Same with the captions | Uses the captions file and the known names; corrects "herman ebb in house" | |
| Ground-08 | Compare Ground-01 with Try-02 for the same file | The before and after shows fewer guesses and more citations | |
| Ground-09 | Open the syllabus in Word, Review, Check Accessibility; paste the results with the agent | The agent works from Word's results the same way | |
| Ground-10 | Check every answer from Ground-01 to 07 | None says "compliant" or "accessible" as a verdict; none invents a finding not in the evidence | |
| Ground-11 | Spot check every evidence file against `answer-key.md` | Every GLOW rule in the evidence appears in the key | |

### 2.10 Block 5: Share it, and the workshop repository

Run these with "My practice agent" unless the case says otherwise, so test
agents land in `practice/`; clear them afterwards.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Share-01 | Open `/ahg/share`; choose `my-agent/SKILL.md` | The text box fills; the name fills from the file; a status message is announced | Pass, Claude, 10 Oct |
| Share-02 | Press "Open the share form on GitHub" | A new tab opens the Share my agent form in Community-Access/ahg-2026, with the workshop code, the kind and the agent filled in | |
| Share-03 | Tick the privacy box and press Submit new issue | Within about a minute, a reply on the issue: "Your agent is in" with a link, or "Well done" for a practice agent; the issue closes | |
| Share-04 | Repeat Share-01 to 03 with a brand-new GitHub account | Same result; the commit shows on that account's profile as theirs | |
| Share-05 | Submit with the text box empty | Message "Your agent is empty"; focus moves to the text box | Pass, Claude, 10 Oct |
| Share-06 | Submit a real agent with the name still "my-agent-name" | Message asks for a name of its own; focus moves to the name field | Pass, Claude, 10 Oct |
| Share-07 | Paste an agent longer than about 7,000 characters | Message explains how to paste it into the form directly | Pass, Claude, 10 Oct |
| Share-08 | Use the offline `share-my-agent.html` from the kit | Same as Share-01 and 02 | Pass, Claude, 10 Oct |
| Share-09 | Open `/ahg/share?practice=1` | "My practice agent" is chosen | |
| Share-10 | Do Share-01 to 03 with NVDA and JAWS | Every control on the share page and on GitHub's form is reachable and named; the reply is found by heading or by refreshing | |
| Share-11 | Ten people share within two minutes | Every one gets a reply within five minutes; no commit is lost | |
| Repo-01 | A practice agent through the form | Committed to `practice/<account>/SKILL.md` with the sharer as author; reply "Well done"; issue closed, label agent-added | Pass, Claude, 10 Oct |
| Repo-02 | A real agent, with the code in lower case | Committed to `agents/<account>/<name>/SKILL.md` with the sharer as author; gallery updated; reply "Your agent is in", with its number | Pass, Claude, 10 Oct |
| Repo-03 | A wrong code, the template's name and author | Reply "Nearly there" listing all three problems; issue stays open, label needs-a-hand; nothing committed | Pass, Claude, 10 Oct |
| Repo-04 | Fix Repo-03 by editing the issue | Checked again on save; agent goes in; reply "Your agent is in" | |
| Repo-05 | An agent containing an email address or a nine-digit number | Reply names what looks private; nothing committed | Pass by tests, 10 Oct |
| Repo-06 | An author with an unquoted colon | Reply explains double quotes; nothing committed | Pass by tests, 10 Oct |
| Repo-07 | Run `scripts/promote_to_accessibility_agents.py` against a scratch checkout of Accessibility Agents | Every agent copied to `community/ahg-2026/`; `commit-message.txt` has a Co-authored-by line per author | |

### 2.11 Block 6: Build the office

These check the agent team, and the Copilot Free allowance for a whole day.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Office-01 | Type `/run-the-office` | Copilot explains in two lines what is about to happen | |
| Office-02 | Let it run | It works one file at a time and writes one line per file naming the specialists, so progress is announced | |
| Office-03 | Read the team report | Three lines for a director first; one section per course file; the tester's agent and name appear where its task fits; WCAG 2.2 criteria with links; "what no checker can see"; status "proposed" | |
| Office-04 | Read the end of the report | A "Before this goes anywhere" checklist, then one sentence saying what the tester's agent added | |
| Office-05 | Run with `my-agent/SKILL.md` still the template | The coordinator says so kindly and uses a ready-made agent or asks which one | |
| Office-06 | If the run stops before the last file, type "continue" | It continues from where it stopped | |
| Office-07 | Facilitator: copy every `agents/<login>/<name>/` folder from the ahg-2026 repository into a `room/` folder in the kit, then type `/run-the-office` | The coordinator puts every room agent on the team and names each one with its author | |
| Office-08 | Count the Copilot Free usage for one full participant day, Setup-09 to Plan-02 | Recorded; under the monthly allowance with room to spare | |

### 2.12 Block 7: Take it home, and the commitment wall

These check the 30-day plan and the anonymous commitment wall.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Plan-01 | Type `/my-30-day-plan`; answer six questions | One question at a time; `my-30-day-plan.md` saved as a short table with the agent's name at the top | |
| Plan-02 | Read Copilot's last line | One reason the plan is realistic; ends "Go make one more champion." | |
| Wall-01 | Open `letitglow.app/w/ahg-2026/11`, join with the access code, add a commitment | Saved | |
| Wall-02 | Open `/workshop/session/ahg-2026/wall`, entering the facilitator key if asked | The commitment appears with no name | |
| Wall-03 | Read the wall with a screen reader | Every commitment is reachable as list or text | |

### 2.13 Materials, accessibility and fallbacks

These cover the content, the sample course, and what happens when things go
wrong.

| ID | Steps | Expected | Result |
|---|---|---|---|
| Mat-01 | Open each of the seven sample course files | Each opens in its own application | Pass, Claude, 10 Oct: opened in Word, PowerPoint, Excel; PDFs and page parsed |
| Mat-02 | Check each planted barrier in `answer-key.md` against the files | Every barrier is present exactly as described | Pass, Claude, 10 Oct: 42 of 42 by scripts/check_ahg_sample_course.py |
| Mat-03 | Read the three worked examples aloud | Facts, times and names match the deck; examples are labelled as written examples | |
| Mat-04 | Open each step card Word file in Word; Check Accessibility | No errors; headings and numbered lists real | |
| Mat-05 | Compare each step card's steps with what testers actually did | Every key, label and expected result matches the real screens; fix any that do not | |
| Mat-06 | Read `pre-event-message.md` as a participant | Four steps, about 20 minutes, the support address, Mountain Time, the privacy rule | |
| Mat-07 | Replace the written before and after answers in the worked examples with real Copilot output captured in Ground-08 | Examples show real output, still labelled | |
| A11y-01 | Use every GLOW page in this plan by keyboard only | Every control reachable, visible focus, logical order | |
| A11y-02 | Zoom the setup page, share page and deck to 200 and 400 percent | No loss of content or function; no horizontal scrolling at 400 percent on the setup and share pages | Pass, Claude, 10 Oct, after fixing D-002 to D-004 |
| A11y-03 | Turn on reduced motion | Nothing animates | |
| A11y-04 | Use the kit in VS Code at the profile's 18pt with VS Code zoomed in twice | Chat and editor remain usable | |
| Fall-01 | Turn off wifi after setup | The kit, sample course, evidence, step cards and examples all still open; only Copilot and GitHub fail | |
| Fall-02 | Simulate a Copilot limit: sign in with an account that has used its allowance | The tester can pair, and the step card's catch-up path still completes the block | |
| Fall-03 | Profile import refused on Env-6 | Setup-08 route works | |
| Fall-04 | GitHub unreachable during block 5 | The agent file can be saved from the kit to a USB stick for a later pull request | |
| Fall-05 | Projector off | The facilitator can run the block from the pocket card and step cards alone | |
| Load-01 | 40 downloads of `kit.zip` from one network within a minute | All succeed; no rate limit refusal | Pass, Claude, 10 Oct: 40 of 40 |
| Dry-01 | Timed dry run of the whole day with the beginner tester, facilitator presenting | Real minutes per block written into `run-of-show.md` section 2; any block over by more than five minutes has a fix | |

### 2.14 Defect log

Number every defect. A defect is closed when its fix is merged and the test
that found it passes again.

| Defect | Test | What happened | Fix | Re-test result |
|---|---|---|---|---|
| D-001 | Auto-07 | Six ready-made agents had author lines like "Example: Maria Alvarez": invalid YAML. Vale stopped on it; VS Code would have misread the headers | Header text quoted by the kit build; template and /design-my-agent keep quotes; a test parses every front matter block (`1d4f1fd`) | Pass, 10 Oct |
| D-002 | A11y-02 | On every GLOW page, at 320px wide, page content was 0px wide: the AI meter sat outside the sidebar and became a column. Live on letitglow.app | Meter moved inside the sidebar; PR #117 for production, same commits on this branch | Pass, 10 Oct |
| D-003 | A11y-02 | Home, privacy, audit and convert pages overflowed sideways at 320px | Wrapping and width rules for main content and form controls (PR #117) | Pass, 10 Oct |
| D-004 | A11y-02, Deck axe | Setup page's profile address and the deck's slide picker overflowed at 320px; deck controls outside any landmark; count said "of 30" | Fixed in `41f1fd7` | Pass, 10 Oct |
| D-005 | Setup-04 | Prompt files used the older `mode:` header; VS Code 1.141 reads `agent:` | All six commands now use `agent: agent` | Pass by inspection; confirm in Setup-09 |

### 2.14a Results so far

Run by Claude on Windows, 10 October 2026, first against GLOW running
locally from the branch (section 1.7), then again against production after
PR #116 and PR #117 were merged and deployed the same day: 35 of 35 browser
checks pass on `https://letitglow.app`. Everything that needs no Copilot
sign-in, no screen reader by ear and no Mac is done, and passes. The full
record is `ahg-test-report.md`.

The workshop is live, so everything below can be run against
`https://letitglow.app/workshop/ahg-2026`; the local copy in section 1.7 is
no longer needed. What remains for Jeff, on Windows:

1. Setup-02 to Setup-10: make a fresh GitHub account, import the profile,
   open the kit, and run `/ready-check`. The four extensions in the profile
   were confirmed to install in VS Code 1.141; GitHub Copilot Chat is built
   into that version.
2. Every case in sections 2.7 to 2.12 that runs a Copilot command.
3. Deck-07 and Deck-09: the Office Accessibility Checker on the deck. GLOW's
   own audits already score both files 100.
4. The screen reader rows Env-2 and Env-3 with NVDA and JAWS, including
   Setup-11 and Share-10 by ear.
5. Share-02 to Share-04, Share-09 to Share-11, Repo-04 and Repo-07, with
   real GitHub accounts, sharing practice agents.
6. Fall-01 to Fall-05 and Dry-01.

### 2.15 Sign-off

The workshop is ready when every line below is signed and dated.

| Item | Signed by | Date |
|---|---|---|
| Automated checks, section 2.4, all pass | | |
| Setup, section 2.5, all pass on every required environment | | |
| Blocks 1 to 7, sections 2.6 to 2.12, all pass | | |
| Screen reader matrix, section 2.3, complete | | |
| Materials, accessibility and fallbacks, section 2.13, all pass | | |
| Defect log closed or every open defect accepted with a workaround | | |
| Dry run done and run of show updated | | |
| Workshop repository cleared of test agents, and the Accessibility Agents folder in place for the end-of-day step | | |
| Setup message sent with working links | | |
| Facilitator ready to run the day | | |
