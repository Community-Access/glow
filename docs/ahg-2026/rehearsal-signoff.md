---
title: "Monday readiness: evidence and sign-off"
lang: en
author: "Community Access"
description: "Required observations, evidence and final release decision for the AHG rehearsal."
---

# Monday readiness: evidence and sign-off

This is the final decision sheet, not a certificate that the course is already
ready. Complete the [full ordered rehearsal](000-start-here.html) and record
observations in [the results sheet](results.csv). Read the full folder
instructions in `README.html` before starting.

Do not mark a gate complete because its instructions or files exist. Every
required gate needs an observed result and an evidence reference. If a gate is
blocked, name the owner, next action and accepted fallback.

## 1. Establish the exact version

1. Record the date, tester, operating system, browser, assistant product,
   account tier and assistive-technology version for each run.
2. Record the kit ZIP name, source revision and download date.
3. Distinguish the saved materials from the current public website. Record the
   website version separately; a local test is not a deployment.
4. Run the snapshot checker described in the folder instructions. Keep its
   output.
5. Preserve results and evidence before refreshing any materials.

Expected proof: a run header with these details and a successful integrity
check, or a clearly documented version mismatch.

- [ ] Version and environment evidence saved.

## 2. Run the automated gates

1. Read `AUTOMATED-TEST-REPORT.md` if present. Note its snapshot date.
2. Run the exact folder-instruction commands against the final source and
   exports.
3. Save each command, exit result, counts and relevant output.
4. For a failure, keep the first evidence, fix or document the defect, and save
   a separate retest. Never replace a failure with an unchecked Pass.
5. Treat missing tool reports, skipped required tests and incomplete builds as
   gaps, not successful validation.

Expected proof: dated passing results for the required gates, with every
exception named and explicitly accepted by the release owner.

- [ ] Automated evidence current; exceptions explicitly resolved or accepted.

## 3. Complete teacher preparation

1. Complete checkpoints 001 through 006.
2. Read the run of show, facilitator card, helper card, answer key and
   invitation in full. Keep the answer key out of the participant view.
3. Explain the goal and expected saved output of each block aloud.
4. Agree who handles captions, beginners, account failures and accessibility
   support. Confirm the room and network arrangements.

Expected proof: named helper roles, working materials and a teacher who can
demonstrate both the main route and the fallback.

- [ ] Teacher and helper preparation observed.

## 4. Review all slides individually

1. Complete checkpoints 031 through 065: one checkpoint for each of the 35
   main-course slides. Do not review only the first and last slides.
2. Open each numbered slide in HTML, Word, PowerPoint and the large-print
   handout.
3. Read visible content and speaker notes aloud. Confirm the title, reading
   order, block number, timing and Behind/Stuck instructions.
4. Activate each address using Tab and Enter in HTML, Control+click in Word, and
   Slide Show in PowerPoint. Confirm the destination, not just blue or
   underlined text.
5. Check every table, smallest text and overflow at the intended display size.
   Inspect the exported reading copy as well as the projected slide.
6. Switch to the student role and say what to do next without using the speaker
   notes.
7. Complete the deck-format and navigation cases at checkpoints 066 through 077.
8. Review the separate closing-demo PowerPoint in the demo phase too.

Expected proof: 35 individual slide results and deck-format results, with slide
numbers, format names and defect/retest evidence for any failures. Use
[the 140-row slide results sheet](slide-review-results.csv) to record all four
reading formats separately.

- [ ] All 35 main slides and the closing-demo slides reviewed.

## 5. Finish the ChatGPT student path

1. Start at checkpoint 078 and continue until the Desktop path begins.
2. Use a fresh approved conversation and fictional inputs.
3. Complete blocks 0 through 7 using the inline step-card instructions and the
   complete browser prompts. Do not use the teacher's completed agent.
4. Save agent versions 1 through 4, before/after answers, the team report, the
   shared or deferred contribution and the 30-day plan.
5. Complete each path-specific positive, negative and fallback case.
6. Record account tier and any usage limit. A paid-account run does not
   establish the free-account path.

Expected proof: recoverable saved outputs and an observed result for every
applicable ChatGPT case.

- [ ] Complete ChatGPT path and all its applicable cases observed.

## 6. Finish the desktop VS Code student path

1. Start at checkpoint 141 and continue until the Web path begins.
2. Use a fresh working kit, profile and approved account.
3. Follow every block's VS Code instructions, including exact slash commands,
   file review, approvals and saving.
4. Save the same versioned outputs as on the browser path.
5. Exercise the missing-file, missing-evidence, wrong-agent and fallback cases
   in scratch copies without overwriting the main agent.

Expected proof: saved files, before/after observations and a result for every
applicable Desktop case.

- [ ] Complete Desktop path and all its applicable cases observed.

## 7. Finish the VS Code for the Web student path

1. Start at checkpoint 209 and complete its block 0 through block 7 run.
2. Verify repository opening, authentication, browser storage and saving.
3. Save outputs outside the browser session and prove they can be reopened.
4. Complete all applicable Web cases; explain genuine unsupported features
   rather than silently omitting them.

Expected proof: saved outputs and an observed result for every applicable Web
case, including account or browser restrictions.

- [ ] Complete Web path and all its applicable cases observed.

## 8. Complete every scenario, not just the happy path

1. Continue through all remaining shared checkpoints.
2. For a case naming several role cards, files or agents, record a separate
   observation for every named item.
3. Exercise missing evidence, unsupported input, lost context, refusal, privacy
   boundaries, ready-made agents, alternate assistants, sharing failure, offline
   work and deferred contribution.
4. Run sharing writes and cleanup only in an explicitly approved scratch
   collection. Do not publish rehearsal contributions to the real room.
5. Keep original failed outputs and retests separately.

Expected proof: every required case has an observation; a multi-item case is not
Pass until every required item passes.

- [ ] Scenario coverage complete with no unexplained Pending rows.

## 9. Complete the accessibility environment repeats

1. Complete checkpoints 333 through 352, following the source environment matrix
   for each row.
2. Use the specified keyboard, browser and screen reader for the whole
   applicable path, not a single-page spot check.
3. Include required Windows NVDA/JAWS and Mac VoiceOver runs.
4. Exercise 200 and 400 percent zoom, narrow reflow, captions and focus during
   transitions and result updates.
5. Record an unavailable required environment as Blocked and assign an actual
   tester; do not mark it Not applicable because this machine cannot run it.

Expected proof: environment-specific end-to-end results with tester and product
versions, and retests for discovered barriers.

- [ ] All required accessibility environments observed.

## 10. Verify the documents and reading formats

1. Open the final Word and PowerPoint copies in Office, not only a parser.
2. Run the Office Accessibility Checker and inspect reading order.
3. Activate the exported links and verify the actual destinations.
4. If distributing PDF, EPUB or Daisy, finish its build and relevant checks.
   Open the output in the intended reader and navigate it.
5. Do not distribute a partially built library or represent `--no-checks` output
   as a validated accessibility pass.

Expected proof: final export names, checker results, reader observations and
link-activation evidence. Record any formats excluded from delivery.

- [ ] Every distributed format checked and usable in its intended reader.

## 11. Rehearse the optional demo and fallback

1. Complete checkpoint 353 for ChatGPT Dots, 354 for Claude Duet and 355 for the
   no-account tabletop fallback.
2. Confirm actual preview access. Mark unavailable products Blocked, not Pass;
   they are optional and cannot prevent the core course.
3. Use the fictional script, keep connectors off, check cited evidence, require
   human approval and verify task-stop status.
4. Run the tabletop fallback even if both products work.
5. Label illustrative or prerecorded output and its date.

Expected proof: a working safe demo or a rehearsed, honestly labelled fallback,
placed after the evaluation without consuming core work time.

- [ ] Safe optional demo decision and no-account fallback rehearsed.

## 12. Prove the pacing with beginners

1. Complete checkpoint 356 with someone who has not built the course.
2. Run the whole teaching sequence once with a browser student and once with a
   desktop VS Code student.
3. Keep the slides visible and rehearse transitions, captions, lunch, break,
   commitments and evaluation.
4. Record actual minutes per block, questions, stalls and helper actions.
5. Repeat any block whose fixes changed its instructions or timing.

Expected proof: two observed beginner runs with timings that preserve the
student work, 30-day plan, commitments and evaluation.

- [ ] Browser and Desktop beginner runs completed within the schedule.

## 13. Make and record the release decision

Fill in these fields. Keep this sheet with the results and evidence.

- Decision: Not ready / Ready with accepted exceptions / Ready.
- Decision date and exact materials revision:
- Release owner:
- Required checks still Pending or Blocked:
- Open defects and their evidence references:
- Accepted exceptions, rationale, owner and working fallback:
- Cases retested after fixes, with evidence references:
- Delivered formats and validation status:
- Public website version and verification date:
- Optional demo plan and fallback:
- Final approval:

Do not choose Ready while required observations are missing. An accepted
exception needs an explicit owner decision; the existence of a workaround alone
is not approval.
