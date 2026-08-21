# GLOW Workshop Mode — Readiness Plan and Path to Golden

**For:** Accessibility Agents in Action — A Hands-On GLOW Workshop, Accessing Higher Ground
**First written:** 18 August 2026
**Last updated:** 21 August 2026
**GLOW version:** 8.0.0 (Workshop Mode introduced 7.3.0)
**Status:** Phases 1–4 built and verified. Phase 5 — hardening and rehearsal — is what remains.

---

## 1. Where this stands

Three days ago this document said the workshop's design was strong, its
curriculum complete, and its delivery layer newly repaired — and then listed
four phases of work that would take it from "a good conference session" to
"the session people remember".

Phases 1 through 4 are now built, tested, and committed on the branch
`workshop-ahg-readiness`.

### 1.1 What shipped

**Phase 1 — Foundations.**

- **Return links.** A participant can give an email address and receive a
  single-use link that restores their identity on any device. Tokens are
  stored hashed, expire after 45 days (outliving the 30-day plan), and the
  address never appears in the gallery, on the facilitator dashboard, or in
  any export.
- **Scenario bank.** Twelve scenarios, four per GLOW lab, each from a
  different institutional sector. Real briefs rather than one-line prompts:
  the situation, what is wrong with the artifact, what to notice, the tools
  that fit, a stretch task, and for three of them a starting document GLOW
  can actually audit. "Surprise me" is deterministic per participant, so it
  spreads briefs across a room and can be reproduced when a facilitator walks
  someone back through what they were given. Choosing is optional and the page
  says so — a participant with a real document of their own should use it.
- **Blank worksheet packs**, HTML and Word, generated from the live activity
  definitions so they cannot drift from the on-screen form. Word is Arial
  18pt with ruled lines; the HTML pack has aria-labelled writing spaces, so
  it is usable with a screen reader and not merely printable.
- **Short URLs, QR codes and printable room signage.** `/w/<code>` joins;
  `/w/<code>/7` opens the seventh activity, numbered the way a facilitator
  says it out loud. The signage page prints a card per activity with the
  address in large type and a QR code beside it.

**Phase 2 — The four-tier AI model.**

- **Tier 2 on every AI-assisted activity**: a prompt built from the
  participant's own answers, their chosen scenario and their own human-review
  step, ready to paste into whatever assistant they already have. A copy
  button that works under the site CSP, announcing through a status region and
  never moving focus, with the text still selectable if the clipboard fails.
- **Tier 1 gets a budget.** Per-participant and per-room caps on the house AI
  key. Hitting a cap routes to the Tier 2 path rather than an error, and the
  check fails open. The facilitator dashboard shows room usage.
- **Tier 3 gets a tool layer.** Generated skills name GLOW's six MCP
  endpoints and state what to do when they are unreachable — work from the
  guidance, name the gap, never present an unverified answer as a check.
- **Optional Lab: Run Your Agent**, deliberately outside the agenda so it
  never touches the progress passport. A door, not a corridor.

**Phase 3 — The living room.**

- **Live gallery and facilitator pulse** over SSE, counts only. The gallery
  announces new work politely and offers a "Show new submissions" control the
  reader activates; nothing is inserted underneath anyone and focus is never
  moved. The dashboard updates per-activity counts and bars in place and is
  safe to project.
- **"Start from this workflow"** on shared Champion Studio submissions. It
  fills the borrower's form only when they have nothing of their own saved;
  otherwise the borrowed workflow is shown beside their work rather than over
  it. Anonymous submitters stay anonymous.
- **Badge collection page.** The badges already existed and were announced
  once in a flash message; now they have somewhere to live.

**Phase 4 — The finish.**

- **Take-home artifact.** One designed page — workflow, who it helps, the
  human-review gate, the 30-day commitment — self-contained, large print, and
  printable, so it opens correctly from an email attachment years later.
- **End-of-day artifact email**, carrying the artifact, the generated agent
  package, and a single-use link back to everything else. The plain text of
  the artifact is in the body too, because institutional mail gateways strip
  attachments.
- **Commitment wall** for the close of the day: every 30-day commitment on one
  screen, anonymous by design.
- **30-day nudge**, as a command rather than a scheduled job: it quotes each
  participant's own words back and links to their follow-through log. Dry run
  is the default, nobody is emailed twice, and nobody who never gave an
  address is in the list.

### 1.2 Two problems found along the way

Both would have shown up in the room and nowhere else.

- **The site was not applying its own type scale.** `body { … }` in
  `acb-large-print.css` was left unclosed, so the ACB 18pt size, line height,
  letter spacing and centred max-width were stranded after an unrelated
  closing brace and discarded by every browser, on every page.
- **The room would have rate-limited itself.** Every limit was keyed on IP
  with a 120/minute default, and static assets counted. Thirty people behind
  one conference NAT address share that budget; one workshop page pulls a
  stylesheet and several scripts. Limits are now per participant, and static
  is exempt.

### 1.3 Three more found by the deploy, all production-breaking

The deploy pipeline is what surfaced these, and none of them could be seen in
a source checkout: they only appear when quill-glow-core is installed, which
is true in the image and false in a bare clone.

- **Every audit returned HTTP 500.** The audit routes filtered findings in
  place, and the post-split `AuditResult` is a frozen, slotted dataclass.
- **Every fix request returned HTTP 500.** The fix route expected a 5-tuple;
  the shared core returns a `FixResult` object, so `len(result)` raised.
- **`_fix_page_numbers` indexed `doc.sections[0]` unguarded**, so a document
  with no section properties took the request down.

Fixed in `c6f5d93`, with stand-in tests for both result shapes so the guard
holds whether or not the shared core is installed in the environment running
them. This is the same "works from source, breaks deployed" shape the MCP
server hit after the 8.0.0 split -- this time in the two workspaces the site
is named for.

### 1.4 The support tracker was full of our own test runs

Sixteen open GLOW issues in `Community-Access/support`, every one "Works
great!" or "Love it", filed in audit/fix pairs. `tests/test_app.py::TestFeedback`
posts feedback without stubbing the sender, so on any machine whose
environment carries `FEEDBACK_GITHUB_TOKEN` -- a developer shell, a deploy
shell -- running the web suite filed two live issues in a public tracker.

Fixed in `2080537`: tests can no longer reach the tracker, only categories
that need a person (bug, accessibility, regression, support) open an issue,
and identical submissions inside 24 hours open one. All sixteen closed with an
explanation.

### 1.5 Verification as of 21 August

| Check | Result |
|---|---|
| Full web test suite | **792 passed, 0 failed**, 31 skipped -- run with quill-glow-core installed, which is the deployed configuration |
| Workshop suites alone | 253 tests |
| Production after deploy | post-deploy verification passed, every URL check OK, all eight containers healthy |
| Live MCP | `/mcp/health` reports `backend: "glow"` |
| axe-core, WCAG 2.2 AA | **37 pages, 0 violations, 1009 passing rules** |
| Ruff on every file touched | clean |
| MCP endpoint tests against installed wheels | 8 passed |

---

## 2. What remains

### 2.1 Ship what exists

Done on 21 August: merged to main, deployed to production by hand, and the
MCP container rebuilt in the same deploy (`/mcp/health` now reports
`backend: "glow"` rather than `"unknown"`). What is left here is
configuration and one credential.

1. ~~Merge the branch.~~ Done.
2. ~~Deploy web.~~ Done, by hand over SSH.
3. ~~Rebuild the MCP image.~~ Done.
4. **Fix the CI deploy key.** GitHub Actions cannot deploy: the runner's key
   is not in the server's `authorized_keys`, so every push to main builds,
   tests, and then fails at the last step. Deploys are manual until this is
   fixed.
5. **Set the AI key in production.** `OPENROUTER_API_KEY` is unset --
   `/health` reports `key_set: false` for chat, vision and whisperer -- so
   Tier 1, the built-in AI a participant uses with no key of their own, does
   not work on the live site. Lab 2 is built around it.
6. **Set the rest of the event configuration** (section 5).

### 2.2 Phase 5 — hardening and rehearsal

This is the whole remaining risk. None of it is code.

| Item | Why it matters | Done when |
|---|---|---|
| Load rehearsal, 30 simulated participants | Nothing here has been tested at room scale. The rate-limit fix makes it survivable in theory; nobody has measured it | A 30-client run completes with no 429s and no request over 2s |
| Screen reader run-through: NVDA, JAWS, VoiceOver | axe passing is necessary, not sufficient. The live gallery, the copy buttons and the scenario picker are where automated and lived results diverge most | Each of the eleven activities completed end to end by ear |
| AI spend estimate, approved | The caps exist; the numbers behind them are guesses | A figure written down and agreed, and caps set to match |
| Full rehearsal with Tier 1 AI switched off | The day must run on Tiers 0 and 2 alone | A complete activity run with `OPENROUTER_API_KEY` unset |
| Offline / degraded-network rehearsal | Conference wifi is a real risk | Worksheet packs printed; the day demonstrably runs from paper |
| Facilitator dry run against the real agenda | Find the pacing problems before the room does | A timed run-through, with the room pulse open |
| Freeze | Ship nothing new in the final week | Branch tagged, no merges |

### 2.3 Loose ends worth clearing before November

- ~~Five failing tests on `main`.~~ Fixed. The three
  `TestSettingsIntegration` failures read repo files relative to the working
  directory and now resolve from the repository root; the two feedback
  failures were reading the developer's real support-hub configuration and are
  now isolated. The suite is 792 passed, 0 failed.
- **Dependency alerts.** 77 open on the default branch (2 critical, 31 high),
  nearly all npm packages under `office-addin`, with eight Dependabot pull
  requests waiting. `office-addin` has not been touched since 23 May --
  decide whether it still ships, because retiring it clears most of the list
  at once.
- **The AI feature flags are off in production.** `GLOW_ENABLE_AI_CHAT`,
  `GLOW_ENABLE_AI_ALT_TEXT` and `GLOW_ENABLE_AI_WHISPERER` are all `0`, and
  `OPENROUTER_API_KEY` is absent from the container -- `docker-compose.prod.yml`
  never references it, so it has to reach the container through
  `~/app/web/.env`. Setting the key alone is not enough; the three flags have
  to be turned on with it. Meanwhile `GLOW_ENABLE_AI_HEADING_FIX` and
  `GLOW_ENABLE_AI_MARKITDOWN_LLM` default to `1`, so those paths are enabled
  and keyless -- trying and failing rather than cleanly off.
- **Tracked Keycloak fixtures.** `keycloak-users.json` and
  `glow-oidc-client.json` hold placeholders today; realm exports drift and
  include secrets by default. Generate them at setup instead.
- **The dead checkout at `C:\Users\jeffb\glow`**, which still has uncommitted
  edits to `pii_guardrails.py` and `routes/convert.py`. Its editable install
  has been removed, so it can no longer shadow this repo, but it should be
  diffed and deleted.
- ~~The accessibility gate was switched off.~~ Restored in `e148e96`.
  Commit `c788b27`, titled "Make CodeQL workflow manual-only", had left
  `accessibility-regression.yml` as `workflow_dispatch:` only, so axe had not
  run on a pull request or a push since 2 August.
- ~~The deploy checker cried wolf on every deploy.~~ Fixed in `e148e96` and
  `dcd1c4e`: the readiness parser read from stdin, which the heredoc had
  already consumed, so it never saw the payload; three URL checks failed
  documents that redirect by design; and model readiness now reports rather
  than gates (`REQUIRE_MODEL_READINESS=1` restores gating).
- **`review.md` is untracked at the repository root.** Commit it, move it into
  `docs/`, or delete it -- but decide, because root clutter is what it warns
  about itself.
- **The merged `workshop-ahg-readiness` branch** can be deleted from the
  remote once it has been reviewed. Everything on it is in `main`.
- **Whatever is deleting things on this machine.** The Playwright browser
  binaries vanished mid-session on 21 August, and `review.md` records two
  broken virtualenvs earlier. Worth identifying before it eats something on
  the day.

### 2.4 Deliberately not doing

- **Full Keycloak accounts before November.** Magic links give ninety percent
  of the benefit at five percent of the cost and none of the friction.
- **A scheduled nudge job.** A command a person runs, having looked at the
  list, is the right shape for mail sent a month after an event.
- **Anything new in the final week.** See "freeze".

---

## 3. The path to golden

Working back from a November conference. Weeks are counts from 21 August.

**Weeks 1–2 (now): ship and configure.**
Merge, deploy web, rebuild the MCP image, set the event configuration, and
walk the whole day yourself once on the deployed site rather than locally.
Fix what that turns up. Nothing else on this list is meaningful until the
thing people will use is the thing that is running.

**Weeks 3–4: content and rehearsal one.**
Read all twelve scenarios aloud and cut or rewrite anything that sounds like
software wrote it. Do the first screen reader pass — NVDA first, because it
is the one most attendees will be running. Print the worksheet packs and the
signage; look at them on paper rather than on screen.

**Weeks 5–6: scale and money.**
Load rehearsal at 30 participants. Cost the AI, set the caps to the agreed
number, and rehearse hitting a cap so you have seen the message a participant
will see. JAWS and VoiceOver passes.

**Weeks 7–8: the degraded days.**
Run a full session with the house AI switched off. Run one with the network
throttled and one from paper alone. These are the rehearsals that decide
whether a bad conference wifi day is an inconvenience or a disaster.

**Weeks 9–10: the facilitator run.**
A timed dry run against the real agenda, with the room pulse open and a
second person playing an awkward participant: someone who joins late, someone
who clears their cookies, someone whose institution blocks the tool, someone
using only a screen reader.

**Week 11: freeze.**
Tag the release. Print everything. Write the one-page card for yourself with
the session code, the facilitator key, the signage URL, and the wall URL on
it.

**Golden means:** a participant with no laptop, no account, no AI access and a
screen reader can complete the entire day and leave with a printed artifact
they are willing to show their director — and a participant with all of those
things leaves with a working agent they designed themselves. Both of those
have to be true on a bad wifi day.

---

## 4. Risks that remain

| Risk | Mitigation | State |
|---|---|---|
| Conference wifi fails | Worksheet packs, offline artifact, no lab depends on cloud AI | Built; rehearsal outstanding |
| Untested at room scale | 30-participant load rehearsal | Outstanding — the largest remaining unknown |
| AI budget exhausted mid-session | Per-participant and per-room caps, exhaustion routes to Tier 2 | Built; the numbers are still guesses |
| Live updates hurt screen reader users | Counts only, polite announcement, explicit "show new" control, focus never moved | Built and tested; needs a human ear |
| AI output embarrasses the facilitator on a projector | Human-review framing throughout; the room pulse shows counts only | Built |
| A lab accidentally requires an install or a key | Tier 3 is a download and a five-minute mention; a test asserts the Tier 2 prompt never mentions installing anything | Built |
| Deployed MCP does not match the generated skills | Rebuild the image before the event | Outstanding |
| Scope creep in the final weeks | Phases 1–4 are done; everything left is rehearsal | Manageable — hold the freeze |

---

## 5. Event configuration reference

| Variable | What it does | For AHG |
|---|---|---|
| `GLOW_ENABLE_WORKSHOP_MODE` | Master switch | on |
| `GLOW_ENABLE_WORKSHOP_LAB_HUB` | Activities, gallery, exports | on |
| `GLOW_ENABLE_WORKSHOP_GALLERY` | Shared gallery | on |
| `GLOW_ENABLE_WORKSHOP_PEER_REVIEW` | Peer feedback forms | on |
| `GLOW_WORKSHOP_FACILITATOR_KEY` | Unlocks the dashboard and session exports | set, and keep off the slides |
| `WORKSHOP_CONFERENCE_CODES_JSON` | Access code → session mapping | set for the AHG code |
| `POSTMARK_SERVER_TOKEN` | Return links, artifact email, nudge | required — without it those features hide themselves |
| `OPENROUTER_API_KEY` | Tier 1: alt-text generation, document chat, transcription | **not set in production as of 21 August**; Lab 2 depends on it |
| `GLOW_ENABLE_AI_ALT_TEXT` | Lab 2's one-click alt text | `0` in production; set to `1` with the key |
| `GLOW_ENABLE_AI_CHAT` | Document chat | `0` in production |
| `GLOW_ENABLE_AI_WHISPERER` | Transcription | `0` in production |
| `GLOW_WORKSHOP_RETURN_LINK_TTL_DAYS` | Return link lifetime | default 45 |
| `GLOW_WORKSHOP_AI_PARTICIPANT_CAP` | Per-person AI calls | default 40; set from the spend estimate |
| `GLOW_WORKSHOP_AI_SESSION_CAP` | Whole-room AI calls | default 600; likewise |
| `GLOW_MCP_BASE_URL` | Tool layer named in generated skills | default `https://letitglow.app/mcp` |
| `GLOW_WORKSHOP_ASSET_ROOT` | Where samples and front-facing docs live | only if the container layout changes |

**On the day, one card in your pocket:**

- Join: `letitglow.app/w/<code>`
- Signage to print: `/workshop/session/<code>/signage`
- Dashboard: `/workshop/session/<code>/facilitator`
- Wall, for 4:25: `/workshop/session/<code>/wall`
- Worksheets: `/workshop/worksheets.docx`

**Thirty days later:**

    flask --app acb_large_print_web.app:create_app workshop-nudge <code> --dry-run
    flask --app acb_large_print_web.app:create_app workshop-nudge <code> --send

---

## 6. Email: Postmark, end to end

Email is not configured in production. Seven features depend on it, so this
section is the whole path from a Postmark account to a verified test message
landing in an inbox.

Everything here is optional. GLOW runs with mail switched off; each feature
below hides itself or degrades in a stated way rather than failing.

### 6.1 What GLOW sends, and what happens without it

| Feature | Without email |
|---|---|
| Audit report delivery | The report is on screen and downloadable; the email link is simply absent |
| Batch audit reports | Same, for a folder of documents |
| Whisperer job notifications | Transcription still runs; nobody is told when it finishes |
| Admin sign-in links | `/admin` is reachable only through the OAuth providers |
| Workshop return links | Identity stays a cookie on one device. The form is replaced by a prompt to download work before leaving |
| Workshop artifact email | The artifact is still viewable, printable and downloadable |
| Workshop 30-day nudge | The follow-through loop never closes, and there is no outcome data |

The two that matter for Accessing Higher Ground are the return link and the
artifact email: they are the difference between the day ending in a browser
tab and the day ending in someone's inbox.

### 6.2 Setup, in order

**1. Postmark account and server.** Create a Server (call it "GLOW
production"). Copy its **Server API token** -- the per-server token, not the
account token. The account token cannot send.

**2. Verify the sender.** Postmark will not send from an address it has not
verified. Two ways:

- *Sender Signature*: verify one address by clicking a link sent to it.
  Quickest, and it only authorises that one address.
- *Domain verification (recommended)*: add the DKIM `TXT` record and the
  Return-Path `CNAME` that Postmark shows you, at the DNS host for
  `notify.letitglow.app`. This authorises every address on the domain,
  survives address changes, and is what keeps mail out of spam folders.

GLOW's default sender is `no-reply@notify.letitglow.app`. Whatever you
verify, `POSTMARK_FROM_EMAIL` must match it exactly.

**3. Leave the account's sandbox.** New Postmark accounts are restricted to
verified recipient addresses until approved. Request approval well before
November, or thirty participants will receive nothing and Postmark will
report success.

**4. Message stream.** The code sends on the `transactional` stream, which is
the default ID Postmark creates. If you make a custom stream, either name it
`transactional` or change `_POSTMARK_STREAM` in
`web/src/acb_large_print_web/email.py`. Broadcast streams are for marketing
and must not be used here.

**5. Configure the server.** In `~/app/web/.env` on bishoplink -- the `web`
service loads it through `env_file`, and `docker-compose.prod.yml` does not
reference these names individually:

    POSTMARK_SERVER_TOKEN=<the server API token>
    POSTMARK_FROM_EMAIL=no-reply@notify.letitglow.app

Then restart:

    cd ~/app/web && docker compose -f docker-compose.prod.yml up -d web worker

The worker needs it too: Whisperer notifications are sent from Celery.

**6. Verify without guessing.** Sign in to `/admin`, open the queue page, and
use the **Email** panel: it states whether Postmark is configured, which
sender and stream are in use, what each feature would do, and offers a test
send. Send one to yourself, then confirm it in Postmark's Activity view.

    # or from a shell on the server
    docker compose -f docker-compose.prod.yml exec -T web python -c \
      "from acb_large_print_web.email import email_status; print(email_status())"

### 6.3 When it does not work

| Symptom | Cause | Fix |
|---|---|---|
| `401` from Postmark | Account token used instead of the server token | Copy the token from the Server, not the account |
| `422` validation error | `POSTMARK_FROM_EMAIL` is not a verified sender | Verify the address, or the domain it belongs to |
| Sends succeed, nothing arrives | Account still in sandbox, or recipient not verified | Request account approval |
| Mail lands in spam | DKIM and Return-Path records missing | Complete domain verification rather than a single signature |
| `429` | Rate limited | Back off; the workshop's volume is nowhere near this |
| Timeout | Postmark unreachable from the container | Check egress; GLOW surfaces the failure and never blocks the request |

### 6.4 Volume and cost for the event

Thirty participants generate roughly: 30 return links, plus a handful of
re-requests, plus 30 artifact emails, plus 30 nudges a month later. Call it
120 messages for the event and its follow-up, well inside Postmark's smallest
paid tier and around the free developer allowance. Audit-report delivery adds
one message per person who asks for one.

### 6.5 Privacy stance

Addresses are used only to send someone their own work. They never appear in
the shared gallery, on the facilitator dashboard, or in any export, and a test
asserts that across all five surfaces. Giving an address is optional at every
step, and the retention period is stated on the form that asks for it.

### 6.6 What was built for this, and what is still optional

Added on 21 August, all of it inert until a token exists:

- `email_status()` -- one structured answer to "will mail work?", carrying the
  sender, the stream and a feature-by-feature availability list, and never the
  token itself.
- `render_email()` -- the house layout. Semantic HTML, a real plain-text
  alternative in the same reading order, no colour-carried meaning and no
  images, because an email client is a browser with opinions and some readers
  will only ever see the text part.
- `send_test_email()` and the admin **Email** panel -- prove the path in
  production without waiting for a real audit or a real workshop.

Still optional, in rough order of usefulness:

1. **Bounce and spam-complaint webhooks.** Postmark can POST delivery events
   back. Today a hard bounce is invisible; with a webhook, a participant whose
   address was mistyped could be told on the day rather than never.
2. **A delivery log.** Store feature, outcome and a hash of the recipient (not
   the address) so "did their artifact go?" has an answer that does not depend
   on someone's Postmark login.
3. **Per-feature switches.** One token turns on all seven features. A
   `GLOW_EMAIL_FEATURES` allow-list would let a deployment enable audit
   delivery without enabling workshop mail, or the reverse.
4. **A digest instead of individual sends.** The 30-day nudge is a natural fit
   for a scheduled digest to the facilitator as well as the participant.
5. **Moving the older senders onto `render_email()`.** The audit-report builder
   still writes its own HTML with inline colour for severity pills. It works
   and is well covered by tests, so it was left alone -- but two message
   styles is one more than a product needs, and the severity pills are the one
   place GLOW's own mail carries meaning in colour alone.

---

## Appendix A — Feature inventory

**Participant surfaces:** workshop home and join, eleven activities plus one
optional lab, scenario picker on each GLOW lab, exercise launchpad with
tokenized deep links, my workshop content, personal Markdown export, take-home
artifact (view, download, email), champion skill preview and package download,
copy-a-prompt on every AI-assisted activity, badge collection, shared gallery
with peer feedback and workflow borrowing, follow-through log, return links.

**Facilitator surfaces:** gated dashboard with metrics, live room pulse, AI
usage panel, recent submissions, session-wide export in four formats,
follow-through export, printable room signage, commitment wall.

**Offline surfaces:** blank worksheet packs in HTML and Word, downloadable
sample documents, self-contained take-home artifact.

**Platform:** four feature flags, SQLite session store, conference access
codes, facilitator key access control, 90-day participant cookie, single-use
return links, optional OIDC binding, per-participant AI budgets,
per-participant rate limiting, short URLs, QR codes, SSE live counts,
Postmark mail, a nudge command.

## Appendix B — Key source locations

| Concern | Path |
|---|---|
| Routes | `web/src/acb_large_print_web/routes/workshop.py` |
| Short URLs | `web/src/acb_large_print_web/routes/shortlinks.py` |
| Persistence | `web/src/acb_large_print_web/workshop_store.py` |
| Scenario bank | `web/src/acb_large_print_web/workshop_scenarios.py` |
| Agent skill compiler | `web/src/acb_large_print_web/workshop_skills.py` |
| Worksheet packs | `web/src/acb_large_print_web/workshop_worksheets.py` |
| Take-home artifact | `web/src/acb_large_print_web/workshop_artifact.py` |
| AI budgets | `web/src/acb_large_print_web/workshop_ai_budget.py` |
| Nudge command | `web/src/acb_large_print_web/workshop_nudge.py` |
| Templates | `web/src/acb_large_print_web/templates/workshop/` |
| Styles | `web/src/acb_large_print_web/static/workshop.css` |
| Live updates | `web/src/acb_large_print_web/static/workshop-live.js` |
| Tests | `web/tests/test_workshop_*.py` |
| Accessibility CI | `web/e2e/tests/axe-audit.spec.mjs` |
| Facilitator runbook | `docs/workshop-mode-facilitator-runbook.md` |
| WCAG checklist | `docs/workshop-mode-wcag-checklist.md` |
| Email | `web/src/acb_large_print_web/email.py` |
| MCP server | `mcp_server/main.py` |
