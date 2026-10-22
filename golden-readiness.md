# AHG 2026: one runbook to reach golden

This is the single working checklist and evidence log for completing the AHG
workshop sign-off tracked by [GitHub issue #125](https://github.com/Community-Access/glow/issues/125).
Work down the steps in order. Keep test outcomes, evidence links, defect decisions,
timings, and signatures in this file. The case IDs below match the detailed
acceptance cases in [ahg.md](./ahg.md); use those IDs to identify the exact case
being run.

## Current state

- [x] Office development dependency issue #124 resolved by
  [PR #126](https://github.com/Community-Access/glow/pull/126), merged to main.
  Its Office build/server, repository test, and documentation checks passed.
  Word is not needed on the server or in CI.
- [x] Earlier release-readiness cleanup #123 is merged. Its production
  deployment and independent production-validation runs succeeded.
- [ ] #125 is still open. The hosted-browser download recheck passed; remaining
  items are the production latency rehearsal, human usability/accessibility
  checks, and the completed dated sign-off below.

The current hosted-browser run returned 40/40 HTTP 200 responses in 2.9 seconds.
The local workstation Python run returned 36/40; four requests timed out. The
hosted runner's network identity is not exposed, so record it as an independent
hosted-browser recheck and retain the unexplained local-network discrepancy.
An additional Windows workstation repeat returned 40/40 HTTP 200 responses
(average 1.84 s, slowest 3.17 s; each response was 583,659 bytes). A single
request also returned 200 with the `gunicorn` Server header. This shows the
intermittent timeout did not recur in this repeat, but the response times
suggest the endpoint is doing measurable work under concurrent load.
The historical local 30-person rehearsal had no errors or rate limits but
failed the latency gate (p95 5,274 ms, with requests over two seconds).

## Step 1: Prepare the test run

1. Start from the latest `main` and check that GitHub Actions is green. The
   latest code and dependency checks are already green after PR #126; rerun the
   checks after any subsequent fix.
2. Recruit: a beginner who has never used VS Code; an experienced Windows
   NVDA/JAWS tester; an experienced Mac VoiceOver tester; and a helper. The
   facilitator runs the facilitator cases. Each tester account must be a new
   GitHub account with Copilot Free, not Copilot Pro.
3. Reserve these required environments: Windows 11/Chrome with mouse and
   keyboard (Env-1); Windows 11/Chrome/NVDA (Env-2); Windows 11/Edge/JAWS
   (Env-3); current macOS/Safari/VoiceOver (Env-4); current macOS/Chrome,
   keyboard-only (Env-5); a Windows work laptop without admin rights (Env-6);
   and 200%/400% magnification (Env-7). Env-8 is optional.
4. Run the browser and load rehearsals below before inviting workshop testers.
   For load testing, coordinate a quiet window with the deployment maintainer
   and provision a disposable session using a unique `ahg-load-test-` code.
   The rehearsal writes participant and activity records. Do not use the live
   `ahg-2026` session.
5. For each check, write the date, tester, environment, case ID, outcome, and
   evidence (URL, run link, or artifact) in the log in Step 7. Mark a failure
   with a defect ID; never convert an unrun case to Pass.

## Step 2: Recheck the 40 kit downloads from a different network

**Current evidence (22 October 2026):** GitHub Actions
[Production Validation run 39838421311](https://github.com/Community-Access/glow/actions/runs/39838421311)
passed. A hosted Playwright browser fetched the production kit 40 times; all
40 returned HTTP 200 in 2.9 seconds. The runner does not expose its network
identity. The local workstation browser sweep was 49/50 overall; its only
failure was Load-01 with 36/40 successful downloads and four `WinError 10060`
timeouts. UI, axe, and reflow checks passed. Do not represent the local
network discrepancy as resolved; determine whether the hosted pass is accepted
as the required alternate-network evidence, or rerun from a known separate
network and investigate the workstation timeouts.

Run this from the repository root on a machine using a network different from
the one used for the failing run. The script also repeats the no-sign-in
browser checks and axe/reflow sweep. It needs Python Playwright, Chrome, and the
local axe file.

```powershell
python scripts/ahg_browser_checks.py --base https://letitglow.app --axe web/node_modules/axe-core/axe.min.js
```

**Pass:** `Load-01` reports 40/40 successful downloads within one minute, with
no rate-limit response. Record the network type/location without exposing a
personal address. Record all other script results too. If it fails, keep the
failure output, investigate the network path or service, fix or document a
tested workaround, and repeat from another network. Do not close #125 while
the failure is unexplained or unaccepted.

## Step 3: Measure latency against the deployed service

**Current status:** Production automation is now implemented in the manually
triggered [Workshop Production Rehearsal workflow](./.github/workflows/workshop-production-rehearsal.yml).
It provisions a run-specific disposable session, runs the 30-participant
latency gate, and attempts guarded cleanup even if the load command fails.
The workflow was not dispatched during this change. It needs the production
GitHub environment/secrets and reviewer approval, if configured, before use.
The prior local result failed the strict latency gate (p95 5,274 ms).

To run it after this change is deployed: in GitHub Actions, select **Workshop
Production Rehearsal** → **Run workflow**, select
`RUN-PRODUCTION-LOAD-TEST`, and run the 30-participant default. The `production`
environment must provide `DEPLOY_HOST`, `DEPLOY_USER`, and `DEPLOY_SSH_KEY`;
configure required reviewers there if the deployment policy requires approval.
Wait for **Remove the isolated rehearsal session** to pass as well as the load
step. Download the `workshop-production-rehearsal-<run>-<attempt>` artifact and
record p50, p95, slowest request, errors, 429s, and cleanup evidence below. If
cleanup fails, do not rerun under the same code; use the failed run's code and
the maintainer recovery procedure above.

1. Ask the deployment maintainer to provision a temporary, isolated workshop
   session with a unique session code. Confirm it exists before starting: the
   harness joins the session and creates sample participants and activities.
   The `--code` value below is the **session code**, not the access code.
2. During the agreed quiet window, run this from a network representative of
   the workshop venue. Replace the example code with the provisioned one.

```powershell
python scripts/workshop_load_rehearsal.py --participants 30 --base-url https://letitglow.app --code ahg-load-test-YYYYMMDD --json "$env:TEMP\ahg125-load.json"
```

3. **Pass:** the command exits successfully; there are no 429s, error
   responses, exceptions, or requests taking more than two seconds. Record
   total requests, p50, p95, slowest request, counts of 429/errors/exceptions,
   exit code, date/time, deployment URL, and network used.
4. Clean up using the procedure below. The harness has no cleanup command;
   do not manually edit the production database. If an isolated session and
   safe cleanup cannot be arranged, run this against a production-like staging
   deployment and record the limitation for explicit facilitator acceptance.
5. If latency fails, do not claim capacity sign-off. Investigate the slow
   routes/deployment, rerun the 30-participant test, and retain both results.
   A CI contention pass does not replace this deployment measurement.

### Disposable rehearsal session cleanup

The deployment maintainer owns this step. It must be completed before the
rehearsal starts: agree on a quiet window, generate a unique code beginning
`ahg-load-test-`, verify no conference/access-code mapping already uses it,
create the session, and record the exact code and database backup/snapshot ID
in the evidence log. Do not share the code with workshop participants. The
load harness posts 30 participants and their activity submissions; it does not
create peer feedback or follow-through entries, but cleanup also checks those
tables in case another rehearsal action added them.

After the run:

1. Stop any runner still using that code. Confirm the exact session code and
   session title are the disposable rehearsal values, not `ahg-2026` or another
   live session. If either check fails, stop and escalate; do not delete.
2. Take a fresh database snapshot. On the deployment-maintainer connection to
   the workshop SQLite database (`instance/workshop_mode.db`), query and record
   the row counts for the exact code in `workshop_conference_codes`,
   `workshop_nudges`, `workshop_return_links`, `workshop_feedback`,
   `workshop_follow_through`, `workshop_submissions`, `workshop_participants`,
   and `workshop_sessions`. Do not use broad cleanup, wildcard matches, or a
   command that deletes by date alone.
3. In one SQLite transaction, delete only matching rows, in this order:
   conference-code mappings, nudges, return links, feedback, follow-through,
   submissions, participants, and finally the session row. Bind the exact
   session code as a parameter in every statement. Never run this procedure
   with `ahg-2026` as the code.
4. Commit only after each statement reports its intended row count. Otherwise
   roll back. Re-query all eight tables for that exact code; every count must
   be zero. Record the operator, UTC time, pre-delete counts, post-delete
   counts, backup ID, and command/change reference in the evidence log.
5. Keep the rehearsal JSON artifact and logs as evidence; they do not belong
   in the workshop database. Do not delete the database file or restore the
   full snapshot over live data as a cleanup shortcut.

The workflow calls the guarded command in
`web/src/acb_large_print_web/workshop_rehearsal_admin.py`. It accepts only the
run-specific generated code, verifies the exact session title, refuses
unexpected related data, deletes only that session's submissions, participants,
and session row in one transaction, and verifies zero remaining rows. If
cleanup fails or detects unexpected records, the workflow fails and requires
the deployment maintainer to use the manual recovery steps above.

## Step 4: Run the workshop with real testers

For every required environment Env-1 through Env-7, complete the participant
flow from Setup-02 through Office-06, start to finish. Use the detailed actions
and expected results in [ahg.md](./ahg.md). At minimum, explicitly cover:

1. **Fresh-account setup:** Setup-02 to Setup-10. Create a new account with
   Copilot Free; install/import the profile by both URL and downloaded file;
   sign in; open the kit; run `/ready-check`; rename `office-team` and verify
   the warning, then restore the original name.
2. **Setup site and kit:** Setup-13 to Setup-18. Test private-window pages,
   all short links, practice-agent share, online kit/step cards/agents/commands,
   the sample course and skip links. Complete Setup-11 by ear during the
   screen-reader runs.
3. **Deck:** Deck-04 to Deck-11. Check the one-page reading view, print/PDF,
   slide timing against the agenda, speaker notes, and PowerPoint accessibility
   checker. Open the Word deck and run its Accessibility Checker too (Deck-09).
   Complete Deck-08 with NVDA or JAWS.
4. **Copilot blocks:** run every command case in Design-01 to Design-09,
   Try-01 to Try-04, Ground-01 to Ground-11, Office-01 to Office-08, and
   Plan-01 to Plan-02. Include the privacy refusal, ready-made-agent fallback,
   evidence checks, continuation behavior, room-agent attribution, and a full
   day Copilot Free usage count. Record timings where the case asks.
5. **Sharing and repository:** Share-02 to Share-04, Share-09 to Share-11,
   Repo-04, and Repo-07. Use real test accounts and practice agents; verify
   issue replies, collection, author attribution, screen-reader operation,
   ten simultaneous shares, and the promotion script against a scratch
   Accessibility Agents checkout. Clean up test issues/agents afterward.
6. **Materials and accessibility:** Mat-03 to Mat-07, A11y-01, A11y-03,
   A11y-04. Read the examples and pre-event message; check actual step-card
   files in Word; compare instructions with real screens; capture real Copilot
   output; check keyboard, reduced-motion, and large-text use. Word/PowerPoint
   are desktop tools for these document checks only; neither is a CI/server
   dependency.
7. **Fallbacks:** run Fall-01 to Fall-05: Wi-Fi off, Copilot limit, profile
   import refused, GitHub unavailable, and projector unavailable. Verify the
   specified fallback works in each case.
8. **Remaining automated case:** verify Auto-06, the axe sweep in `web/e2e`,
   against the current commit and record its passing Actions run. The other
   automated checks and material checks passed in the recent CI/readiness
   runs; after any fix, rerun the applicable checks in ahg.md section 2.4.

## Step 5: Perform and record the timed beginner dry run

Have the beginner tester complete the whole workshop while the facilitator
delivers it as planned. Record actual minutes per block below. If a block runs
more than five minutes over its slot, adjust the material or pacing and repeat
that block. Copy the final actual timings into section 2 of
`docs/ahg-2026/run-of-show.md`, as required by the test plan.

| Block | Planned minutes | Actual minutes | Tester/date | Pass or change needed |
|---|---:|---:|---|---|
| Setup | | | | |
| 1. Why we are here and the deck | | | | |
| 2. Design your agent | | | | |
| 3. Your agent at work | | | | |
| 4. Ground it | | | | |
| 5. Share it and the workshop repository | | | | |
| 6. Build the office | | | | |
| 7. Take it home and the commitment wall | | | | |

## Step 6: Close defects and finish event preparation

- Every defect is fixed and its test passes, or the defect log below records
  the written acceptance and the exact workaround facilitators will use.
- Clear test issues and agents from the workshop repository. Confirm the
  Accessibility Agents folder is ready for the end-of-day promotion step.
- Open the current setup message and click every participant-facing link.
  Confirm dates, Mountain Time, support address, privacy rule, and estimated
  setup time are correct.
- Confirm the facilitator has the current run of show, pocket card, working
  facilitator access, and is ready to run the day.

## Step 7: Evidence log and sign-off

### Evidence log

| Date | Case/run | Tester and environment | Result | Evidence link or artifact | Defect/workaround |
|---|---|---|---|---|---|
| 2026-10-22 | Load-01, hosted browser | Hosted Playwright; network identity unavailable | 40/40 HTTP 200 in 2.9 s | [Production Validation run 39838421311](https://github.com/Community-Access/glow/actions/runs/39838421311); hosted browser batch | Local workstation discrepancy remains: 36/40, four timeouts |
| 2026-10-22 | Browser/axe/reflow sweep | Local Windows workstation | 49/50; UI, axe, reflow passed; Load-01 36/40 | `scripts/ahg_browser_checks.py`; production `https://letitglow.app` | Four `WinError 10060` timeouts; investigate/accept explicitly |
| 2026-10-22 | Load-01, controlled workstation repeat | Windows workstation; 20 concurrent workers | 40/40 HTTP 200; average 1.84 s, max 3.17 s; 583,659 bytes each | PowerShell `HttpClient`/`Invoke-WebRequest` repeat against production | No timeout reproduced; endpoint responds `no-cache` and `Server: gunicorn`; dynamic ZIP generation is a plausible workload factor, not a confirmed cause |
| Pending | Production 30-participant latency | Not run | Blocked pending isolated session and safe cleanup/staging | None | Do not write test activity to live session |
| | Auto-06 axe sweep | | | | |
| | Setup and Copilot cases | | | | |
| | Screen-reader matrix Env-2/3/4 | | | | |
| | Sharing/repository cases | | | | |
| | Office Accessibility Checkers | | | | |
| | Fallbacks | | | | |
| | Dry-01 | | | | |

Add rows for each environment and each test case. Do not treat this summary row
as a replacement for a case-level result: all cases in ahg.md sections 2.4 to
2.13 must be marked Pass or Not applicable with a reason.

### Defect log

| Defect ID | Failing case | Fix or accepted workaround | Retest/evidence | Accepted by/date |
|---|---|---|---|---|
| | | | | |

### Required dated sign-offs

| Completion item | Signed by | Date | Evidence/notes |
|---|---|---|---|
| Automated checks, including Auto-06, pass | | | |
| Setup passes on every required environment | | | |
| Blocks 1–7 pass | | | |
| Required screen-reader matrix is complete | | | |
| Materials, accessibility, and fallbacks pass | | | |
| Defects closed or accepted with a usable workaround | | | |
| Timed dry run completed; run of show updated | | | |
| Workshop test data cleared; end-of-day agent folder ready | | | |
| Setup message sent with working links | | | |
| Facilitator ready to run the workshop | | | |

## Step 8: Close issue #125

Close [issue #125](https://github.com/Community-Access/glow/issues/125) only
after every required case is Pass or has a documented, accepted exception; the
download and latency evidence is attached; all sign-offs above are named and
dated; and any test data has been cleaned up. Then post a concise issue comment
linking this runbook, the final run-of-show timings, Actions runs, and any
accepted workaround. Green unit tests alone are not completion.
