# GLOW and AHG release readiness, 22 October 2026

This is the record of the dependency and release-readiness cleanup. Automated
checks do not replace the participant, screen reader, and facilitator sign-offs
in the [AHG test plan](ahg.md#215-sign-off).

## Completed triage

- Reviewed all 71 open issues. Seventy contain only positive feedback, in two
  repeated messages. One explicitly validates the feedback system. Closed each
  with an explanation, preserving the original submission.
- Confirmed that the feedback tests already isolate live support credentials.
- Reimplemented the heading-warning fix from
  [pull request 70](https://github.com/Community-Access/glow/pull/70) on current
  main, with regression coverage for defaults, disabled detection, non-default
  accuracy, and browser form values.
- Kept existing generated e2e job data intact and excluded it from Git status.

## Verified checks

These results were collected on Windows with Python 3.14.8. The repository's
Python 3.13 Linux CI remains the merge gate.

- Heading-customization regression tests: 11 passed.
- MCP tests with the updated multipart parser: 8 passed.
- Version consistency: passed at 8.0.0.
- Configuration consistency: passed.
- AHG materials: 31 documents and 32 templates conform to the program.
- Sample course: all 42 intended barriers verified.
- AHG document audits: all 38 documents pass.
- Read-only production validation: all required checks pass. One health request
  took 2.5 seconds and produced a response-time warning.
- Web npm audit, including development dependencies: zero vulnerabilities.
- Office runtime npm audit: zero vulnerabilities. The full development tree
  still reports 12 high-severity package findings rooted in unpatched
  `node-forge` and `braces` advisories. None have been dismissed.
- Python 3.13 Linux CI: 1,153 web tests passed, 31 skipped; 8 MCP tests passed.
- Corrected Windows document browser regressions: 8 passed; the optional
  audio upload case is skipped because its external fixture is unavailable.
  Document tests now use a tracked fixture and cannot silently skip in CI.
- The CI accessibility gate and 30-participant contention rehearsal passed.

## Outstanding automated findings

- Production AHG browser checks: 49 of 50 passed. The only failure was the
  40-download test using Python's HTTP client: 27 returned 200 and 13 hit
  connection timeouts. The setup, deck, share, keyboard, reflow, and axe checks
  passed. A separate Node fetch check, in two batches of 20, returned 200
  for all 40 requests. This suggests a client or network-path issue but does
  not establish its cause. Recheck from another network before signing off.
- Office development dependencies still need upstream patches for
  [the node-forge signature-verification advisory](https://github.com/advisories/GHSA-86w9-cpqp-85rv)
  and [the braces recursion advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).
  Keep local development tools on trusted inputs and local interfaces; do not
  expose the development server publicly. Do not downgrade packages merely
  to make an audit command report fewer findings.

These findings remain open in
[the development dependency tracker](https://github.com/Community-Access/glow/issues/124)
and [the AHG final sign-off tracker](https://github.com/Community-Access/glow/issues/125).

## Load-test interpretation

The local 30-participant rehearsal completed 1,080 requests with no error
responses or rate limits. Its full latency gate failed: median 2,227 ms,
95th percentile 5,274 ms, and maximum 5,914 ms. Other local validation was
running concurrently. This is not a production capacity sign-off.
An uncontended 36-request run had one request above the two-second threshold
(2,352 ms); its 95th percentile was 1,322 ms. It also fails the strict gate.

The in-process rehearsal shares a Python interpreter across participants; the
deployed application uses multiple worker processes. Use the contention CI
gate to detect lock errors and failed requests, and arrange a deliberate
deployment rehearsal before signing off room-scale response times. Do not
mark the failed local latency result as a pass.

## Remaining human sign-offs

Use the [current AHG test plan](ahg.md), not the superseded sharing instructions
in the first [AHG test report](ahg-test-report.md).

- Fresh-account Copilot setup and a complete run through the workshop commands,
  including the Free-plan allowance and fallback paths.
- NVDA and JAWS listening checks; VoiceOver checks with a Mac tester where
  required by the environment matrix.
- Word and PowerPoint Accessibility Checker results for the actual distributed
  files, plus step-card comparisons with the current screens.
- Sharing a practice agent through the current workshop repository and form,
  verifying the collection and the end-of-day author-credit workflow.
- Offline, quota, network, profile-import, and projector fallback drills.
- A timed beginner dry run, with actual timings recorded in the run of show.
- Dated facilitator sign-off and the setup message with working links.

## Change record

The replacement changes and CI results are tracked in
[pull request 123](https://github.com/Community-Access/glow/pull/123).
The Office add-in now has a dedicated CI gate for its locked installation,
runtime dependency audit, production build, sideload CLI, and development
server startup. Final CI results are attached to that pull request.
This cleanup does not certify the workshop as golden: the two open trackers
and human sign-offs above must be resolved or explicitly accepted.
