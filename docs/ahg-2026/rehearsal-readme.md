---
title: "AHG test folder: full instructions"
lang: en
author: "Community Access"
description:
  "Complete instructions for the numbered teacher and student rehearsal."
---

# AHG test folder: full instructions

This folder is your working rehearsal copy of the Accessibility Agents course
for Accessing Higher Ground 2026. Use it first as the teacher, then as a student
on each supported path. It includes the course materials, individual slide
reviews, positive and negative scenarios, fallback drills, accessibility checks
and a results sheet.

The initial sequence contains 356 numbered steps, covering 172 source test cases
and all 35 main-course slides. Some cases repeat on different paths. These are
instructions to carry out, not 356 tests already passed.

## 1. Start here

1. Open [the ordered rehearsal index](000-start-here.html) in your browser. It
   works from this folder without a local web server.
2. Read these instructions completely before starting. Keep the index open in
   one tab and the current numbered step in another.
3. Open [the results sheet](results.csv) in Excel or another CSV editor. Make a
   backup before editing it. Save it as CSV, preserving its columns.
4. Start with step 001 and work upward. Use the index links rather than trying
   to remember a long file name. Stop and resume between steps.
5. Before leaving a step, record what actually happened and save evidence. Do
   not mark something Pass just because the instructions look correct.

For the saved automated results, read `AUTOMATED-TEST-REPORT.md` if present. Use
[the Monday readiness checklist](monday-readiness-checklist.html) to collect the
final evidence and release decision. These reports do not replace the numbered
steps.

For plain text, use [the Markdown index](000-start-here.md) and the copies in
the `text` folder. These instructions are also supplied as `README.html`.

## 2. What is where

The entries below explain the folders and files you will use.

- `README.md`: these complete instructions. `README.html` is the browser reading
  copy.
- `000-start-here.html`: the clickable master sequence. This is the best
  starting point each time you return.
- `000-start-here.md`: the same sequence in Markdown.
- Numbered `.html` files at the top level: one rehearsal checkpoint per file.
  The number gives the order. The title identifies the role and task. The ending
  identifies the original source file.
- `text`: Markdown copies of the numbered instructions. These are alternative
  reading formats, not another set of tasks to complete.
- `materials`: a snapshot of the course source and generated materials. Original
  names and relative folders are preserved here.
- `materials/ahg.md`: the original full test plan and longer walkthrough. Its
  historical results are not your current rehearsal results.
- `materials/docs/ahg-2026`: the course folder, including the run of show,
  facilitator and helper cards, answer key, slides and participant kit.
- `materials/docs/ahg-2026/kit`: the participant kit, step cards, examples,
  agent instructions, browser prompts and deliberately flawed sample course.
- `materials/docs/ahg-2026/dist`: the built participant-kit ZIP.
- `results.csv`: one initially Pending row per numbered checkpoint.
- `slide-review-results.csv`: 140 initially Pending rows, one for each of 35
  slides in HTML, Word, PowerPoint and the large-print handout. Record notes,
  reading order, link activation, layout, the student's next action and evidence
  here. The handout intentionally has no speaker notes.
- `evidence`: save your own observed results here. Automated result summaries
  may also be saved here; they do not complete manual checkpoints.
- `manifest.json`: the machine-readable inventory of steps, source case IDs,
  slide count and hashes of the material snapshot. Do not edit it.
- `library`, if present: a separately built reading-format library. Use it only
  after its build and checks have completed. A folder appearing during a build
  is not evidence that all its PDF, EPUB or Daisy files are ready.

Files in `materials` retain their source names rather than being renumbered.
They are reference resources; the numbered files at the top level tell you when
to use them.

## 3. How to understand a file name

For example:

```text
031-teacher-and-student-review-slide-01-accessibility-agents--from-slides.md.html
```

Read this as:

- `031`: complete it as checkpoint 31 in this snapshot.
- `teacher-and-student`: rehearse it in both roles.
- `review-slide-01-accessibility-agents`: review slide 1.
- `from-slides.md`: the original source document is `slides.md`.
- `.html`: open this instruction file in a browser.

The two extensions in `slides.md.html` are intentional: the original name is
retained before the reading format. Every numbered file also gives an Original
source link inside it. Use that link to find the full context.

When a case says `from-ahg.md`, its specific test ID, such as Ground-03,
identifies the exact row in the original test plan.

## 4. Prepare the rehearsal

1. Set aside several sittings. This is a multi-day rehearsal, including separate
   browser, desktop and web runs, not a short document review.
2. Arrange approved test accounts, a helper and a beginner who can play a
   first-time participant. Do not assume a paid account proves the free-account
   path works.
3. Have Windows, Chrome and Edge, Word, Excel and PowerPoint ready. Arrange NVDA
   and JAWS testing and a separate Mac tester for VoiceOver. If a required
   environment is unavailable, record it as Blocked.
4. Confirm which AI tools and data your institution permits. Training settings
   alone do not authorize an upload.
5. Use fictional or explicitly approved non-sensitive inputs. Keep real student
   records, accommodations, health information, credentials, facilitator keys
   and confidential repository code out of AI prompts and saved evidence.
6. Use a scratch collection for sharing tests. A rehearsal must not publish test
   contributions to the real workshop collection, send messages, alter
   production settings or delete anyone else's work.
7. Download the materials before the offline drills. Copy a fresh working
   participant kit for each VS Code path. Do not edit the reference copy while
   using it as your baseline.
8. Read [the current run of show](materials/docs/ahg-2026/run-of-show.md) and
   [the helper card](materials/docs/ahg-2026/helpers-card.md). Confirm captions
   and how someone requests help.

## 5. Follow the phases in order

Use the numbered index for the exact checkpoint numbers. The phases are:

1. Teacher preparation: timing, pocket card, helpers, answer key and the
   participant invitation.
2. Automated gates and shared website setup checks.
3. Individual review of every main-deck slide, followed by deck-format and
   navigation checks.
4. A complete student run in ChatGPT using the browser prompts.
5. A complete student run in desktop VS Code.
6. A complete student run in VS Code for the Web.
7. Remaining shared cases: materials, repository intake, alternative assistants,
   accessibility, fallbacks and load testing.
8. Explicit end-to-end repeats in the required accessibility environments.
9. Separate rehearsals of ChatGPT Dots, Claude Duet and the no-account
   closing-demo fallback.
10. Timed teaching runs with a beginner and a final release decision.

Each block checkpoint includes the full step card, not only a link to it. Use
the browser section for ChatGPT and the VS Code section for Desktop or Web. Keep
the original-source link available to compare the exports.

A numbered case may tell you to exercise several files, role cards or agents.
Test every named item and keep a separate observation for each. Only mark the
checkpoint Pass when all required items pass.

## 6. Work as the teacher

For each block:

1. Show the finished result before demonstrating how to make it.
2. Open the corresponding slides and read the speaker notes aloud.
3. Explain the goal in plain language and describe anything on screen.
4. Demonstrate the action, the saved result and the fallback.
5. Say the Behind or Stuck instruction aloud.
6. Allow the student time to do the work without your account, your existing
   agent or your prior chat context.
7. Record the actual elapsed minutes, confusing labels and questions.
8. Verify that captions, keyboard operation and the screen reader still work
   during transitions, not only on a static page.

Keep the answer key in the teacher view. Do not coach the student toward a
finding before seeing what the agent and checker actually report.

Preserve the 30-day planning exercise, commitments and session evaluation. The
optional product demo is after the scheduled evaluation, not a reason to remove
student working time.

## 7. Work as the student on all three paths

Start a distinct run for each path. Use the common fictional inputs in Part 3,
section 3.6 of [the test plan](materials/ahg.md) so results are comparable.

### Browser path

1. Follow step card 0 and sign in to an approved assistant.
2. Keep [the browser prompt page](https://letitglow.app/ahg/assistant) and the
   assistant in separate tabs.
3. Copy the entire text for the current block, not just its title.
4. Paste it as one message. Wait for the response to finish.
5. Keep the main conversation for the whole-day run. Use separate chats for
   missing-agent, privacy and fallback scenarios.
6. Save each agent version and other outputs outside the conversation. Confirm
   you can recover them if the conversation is lost.

### Desktop VS Code

1. Follow the desktop section of step card 0, including the profile and
   recommended extensions.
2. Open your working copy of the unzipped participant kit.
3. Open Copilot Chat and use the exact command on the current step card.
4. Check what files changed before accepting edits.
5. Save your main agent before trying a fallback agent. Restore the main working
   agent afterward without changing the reference materials.
6. Record actual free-tier allowance use and any limit messages.

### VS Code for the Web

1. Use Chrome or Edge and follow the web section of step card 0.
2. Open a separate working kit copy at
   [VS Code for the Web](https://vscode.dev).
3. Record the browser's real permission prompts and any differences from the
   instructions.
4. Run the same block commands and save the same checkpoints as desktop.
5. Close and reopen the tab when the case requires it; verify the files and
   saved work can be recovered.

### Save these checkpoints on each path

- Block 0 and 1: setup result and practice-sharing observation.
- Block 2: agent version 1 and its six design answers.
- Block 3: first answer, review checklist and agent version 2.
- Block 4: checker evidence, grounded answer, before/after comparison and agent
  version 3.
- Block 5: whole-course team report, human-review items and agent version 4.
- Block 6: reviewed sharing draft, or verified scratch-collection result.
- Block 7: eight-question 30-day plan and its partner-review observation.

Unknown campus approvals, baseline measurements and targets stay Pending with a
responsible role and next action. Do not invent them to finish.

## 8. Review slides and other formats

Open the following copies from the snapshot:

- [HTML slides](materials/docs/ahg-2026/slides.html).
- [PowerPoint slides](materials/docs/ahg-2026/slides.pptx).
- [Word slides and speaker notes](materials/docs/ahg-2026/slides.docx).
- [Large-print handout](materials/docs/ahg-2026/slides-large-print-handout.docx).
- [Markdown slides](materials/docs/ahg-2026/slides.md).

For every one of the 35 numbered slide reviews:

Open [the slide-by-format results sheet](slide-review-results.csv). Record all
four formats separately, then summarize the slide's result in the main results
sheet. For the handout's notes field, record Not applicable: participant handout
has no speaker notes.

1. Find the same slide in all formats.
2. Check title, content, timing, notes and reading order.
3. Explain the next action as a student without consulting speaker notes.
4. Follow the slide's links. Visible URL text is not proof of a link.
5. In HTML, use Tab and Enter. In Word, use Control+click or the hyperlink
   context menu. In PowerPoint, test links in Slide Show.
6. Run Word's and PowerPoint's Accessibility Checkers. Record unresolved issues
   and manually check meaningful reading order and usability.
7. Review at high zoom and with the required screen reader.

Do the same link checks on the step cards and guides. In PDF, test actual link
activation in a PDF reader; in EPUB and Daisy, use the intended reading
application. A parser finding a hyperlink is not a full reader usability test.

The PSY 101 sample files intentionally contain barriers. Their findings must
remain present for the exercises. Do not fix or convert the baseline sample
course as a way to make its audit pass.

## 9. Record results and evidence

The results sheet has these columns:

- `step`: the numbered checkpoint.
- `case`: the source test ID, or a generated checkpoint identifier.
- `role`: teacher, student or tester.
- `path`: ChatGPT, Desktop, Web or shared.
- `environment`: the actual operating system, browser and assistive technology
  used. Add versions where relevant.
- `source`: the originating document.
- `status`: begin with Pending; change only after observing the result.
- `minutes`: actual elapsed time.
- `evidence`: the relative name of your supporting file in `evidence`.
- `defect_or_reason`: the failure, blocker, exception or retest reference.

Use these status meanings:

- Pending: not run yet.
- Pass: performed in the stated scope; expected behavior observed.
- Fail: performed; expected behavior not observed.
- Blocked: cannot run because access, a device, approval or a dependency is
  missing. This is not a pass.
- Not applicable: truly outside this case's scope; give a reason. Missing Mac
  hardware does not make a required Mac test Not applicable.

For example, save a grounded-answer observation under a name such as:

```text
evidence/Ground-03-Desktop-Env-2-attempt-01.txt
```

Include the fictional input, exact output, source evidence, observed problem and
the reviewer's conclusion. Remove private account details. Keep the first failed
attempt and save the retest separately.

## 10. Run and understand the automated checks

Run commands from `S:\code\glow` using the already active Python environment. Do
not change interpreters or create a new environment just for this rehearsal.

In PowerShell:

```powershell
Set-Location S:\code\glow
$env:PYTHONPATH = "web\src;desktop\src"
python scripts\build_ahg_rehearsal.py S:\ahgtest --check
python scripts\check_ahg_formats.py
python scripts\check_material_conformance.py
python scripts\check_ahg_sample_course.py
python scripts\audit_ahg_docs.py
python -m pytest web\tests\test_workshop_ahg_formats.py web\tests\test_workshop_deck_formats.py web\tests\test_ahg_rehearsal.py -q
```

The rehearsal check verifies consecutive step numbers, source case/path
coverage, individual slide coverage, material snapshot hashes, local links and
HTML structure. It preserves your results sheet.

The format check verifies current generated copies and live HTML and Office
hyperlink destinations. It does not merely search for printed URL text. The
sample-course check expects all 42 planted barriers.

For web accessibility regression checks:

```powershell
Set-Location S:\code\glow\web
$env:PYTHONPATH = "S:\code\glow\web\src;S:\code\glow\desktop\src"
$env:E2E_PYTHON = (Get-Command python).Source
npm run test:axe
npm run test:keyboard
npm run test:reflow
```

These suites start or use a local test server. Confirm you are not accidentally
targeting a live service. Follow `S:\code\glow\web\e2e\README.md` for
prerequisites, test fixtures and configuration. If a command fails, save its
exact command, exit result and relevant output; do not silently skip it.

If a completed reading library is present, its separate check is:

```powershell
Set-Location S:\code\glow
$env:PYTHONPATH = "web\src;desktop\src"
python scripts\check_ahg_library.py S:\ahgtest\library
```

PDF/UA, EPUBCheck, Ace and Daisy checks depend on their installed tools. A
failed tool or missing report remains a validation gap. Do not call a library
fully verified because a build ran with checks disabled.

Automated checks do not prove signed-in AI behavior, free-tier capacity, Office
reader usability, screen-reader announcements or classroom pacing. Those are
explicit manual steps in this folder.

## 11. Rehearse the optional closing demo

Read [the complete demo script](materials/docs/ahg-2026/kit/closing-demo.md). It
also has HTML, Word and PowerPoint copies in the same folder.

1. Rehearse ChatGPT Dots and Claude Duet separately.
2. Verify actual account eligibility before presenting. A subscription does not
   guarantee preview access.
3. Use only the small fictional evidence printed in the script.
4. Keep connectors and access to your computer off.
5. Use the exact prompt, then the missing-evidence follow-up.
6. Trace the output to the supplied evidence and check every citation.
7. Keep sending, publication and other actions behind human review.
8. Stop background tasks and verify their status before leaving.
9. Rehearse the no-account tabletop fallback as its own checkpoint.

A written example is illustrative unless it is labelled with an actual captured
run and date. Do not imply you ran an unavailable product.

Keep the demo optional, after the 4:25 evaluation and scheduled 4:30 end, only
if the room can remain open. Otherwise share the walkthrough for later.

## 12. Deal with failures and fallbacks

1. Record the failure before changing anything.
2. Identify whether it is the course instructions, a generated file, an account
   limitation, a missing dependency or a product interface change.
3. Use the documented fallback: ready-made agent, another approved path, written
   exercise, saved draft or deferred sharing.
4. Check that the fallback preserves the participant's work and learning
   outcome. Merely bypassing a failed step does not make it pass.
5. Report source changes in the repository, rebuild the affected outputs and
   rerun the failing case plus related automated gates.
6. Retain the original evidence and record the successful retest, or the
   accepted workaround and responsible person.

No live mass-download tests, public sharing tests, production deployments or
destructive cleanup happen automatically from this folder. Arrange approval and
a safe target for those cases.

## 13. Pause, resume and refresh safely

Before stopping, save the results CSV, the current agent version, outputs and
the next step number. Resume from that number in the index.

Do not rebuild over this folder. The generator refuses a non-empty destination
to protect your observations. For a new rehearsal snapshot:

```powershell
Set-Location S:\code\glow
$env:PYTHONPATH = "web\src;desktop\src"
python scripts\build_ahg_rehearsal.py S:\ahgtest-next
python scripts\build_ahg_rehearsal.py S:\ahgtest-next --check
```

Keep the old results and evidence. Compare changed source materials before
deciding which cases need to be rerun. A snapshot hash check proves the snapshot
has not changed; it does not prove that it is the newest repository revision or
the version currently deployed on the public website.

## 14. Decide whether the course is ready

Use the definition of done and sign-off in
[the source test plan](materials/ahg.md). At minimum:

- All required path and environment cases are observed and recorded.
- Every required screen-reader run and Office check is complete.
- All slides, step cards, sample files, evidence and links have been reviewed.
- Both beginner timed runs are complete with realistic block timings.
- Every failure is fixed and retested, or has an explicitly accepted workaround
  with an owner.
- The kit, reading library and deployed website version are distinguished and
  their actual validation status is recorded.
- The optional demo has a working fallback and does not displace core work.
- No required check is silently left Pending or described as a pass.

Suggested priority: complete one realistic browser teaching run early, recruit
the Mac tester immediately, then finish the desktop/web and accessibility
matrices. Practice the optional paid-product demo last.
