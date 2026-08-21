# Workshop Mode Facilitator Runbook

## Workshop Promise
Participants do not need to be developers or AI specialists.

Facilitators should center practical accessibility work, confidence building, and partner ownership.

## Session Structure
Total day: 8:30 AM to 4:30 PM
- seven workshop hours plus one-hour lunch
- two short breaks included in workshop block

## Preparation Checklist (Before Event)
1. Validate feature flags
- workshop mode enabled
- lab hub enabled
- gallery enabled
- peer review enabled

2. Validate environment
- workshop routes reachable
- forms submit path available
- export paths operational (markdown/json/html/docx)
- fallback worksheets ready
- facilitator access configured (see below) and tested before the room fills

### Facilitator access

The facilitator dashboard and the session-wide exports show every
participant's submissions, so they are not open to everyone holding the
session code. Access is granted two ways:

- Sign in as an approved GLOW administrator, or
- Unlock the session with its facilitator key at
  `/workshop/session/<session-code>/facilitator`.

Set the key either per session, in the conference code configuration
(`instance/workshop_conference_codes.json` or the
`WORKSHOP_CONFERENCE_CODES_JSON` environment variable):

```json
[
  {
    "access_code": "AHG2026",
    "session_code": "ahg-2026",
    "session_title": "Accessibility Agents in Action",
    "event_name": "Accessing Higher Ground",
    "facilitator_key": "choose-a-strong-value"
  }
]
```

...or deployment-wide with the `GLOW_WORKSHOP_FACILITATOR_KEY` environment
variable, which covers ad-hoc sessions created on the day.

If no key is configured anywhere, these surfaces are restricted to signed-in
administrators. That is deliberate -- it fails closed rather than exposing the
room's work.

Participants never need this key. Their own artifacts are always available to
them from **My workshop content**, including a Markdown download.

### Participant privacy

Submissions marked "share anonymously" are shown and exported as
"Anonymous participant" in every format, including JSON. Exports never contain
participant session tokens.

Email addresses given for return links are held only to send that person their
own work. They never appear in the gallery, on the facilitator dashboard, or in
any export, and there is a regression test asserting exactly that.

### Return links

A participant's identity is a cookie on one device. Anyone who switches from
laptop to phone, or whose browser clears cookies, loses access to their work
unless they have emailed themselves a return link.

Point people at this early -- ideally right after the first activity is saved,
while there is still something worth keeping. The control is on the "My
workshop content" page, under "Work on another device".

- Giving an address is optional; the day works fully without it.
- The link is single use and expires after 45 days, which outlives the 30-day
  action plan. Override with `GLOW_WORKSHOP_RETURN_LINK_TTL_DAYS`.
- Requesting another link is always available, so a used or expired link is a
  recoverable inconvenience, not lost work.
- Links are stored hashed. A copy of the workshop database yields no usable
  links.

Requires `POSTMARK_SERVER_TOKEN` on the server. Without it the form is replaced
by a prompt to download work before leaving -- check this before the session,
because it is invisible until someone looks for it.

3. Accessibility validation
- keyboard-only walkthrough complete
- screen reader smoke test complete
- contrast checks complete
- heading and landmark checks complete

4. Facilitation assets
- opening slides or HTML brief
- scenario packets for labs
- peer feedback rubric
- capstone prompt and action plan template

## Facilitation Rhythm
1. Start with problem framing
- ask participants what accessibility problem they need to solve
- avoid tool-first framing

2. Reframe role
- move from "fix everything" to "teach repeatable patterns"

3. Maintain responsible AI boundary
- classify tasks as:
  - helpful for AI
  - risky without review
  - human required

4. Require human-review checkpoints
- every team identifies final human validation before completion

## Lab Guidance
Lab 1: Accessible communications
- target clarity, structure, meaningful links, and inclusive language

Lab 2: Alt text and image purpose
- emphasize context and purpose are human decisions

Lab 3: Remediation planning
- prioritize impact, sequence actions, and coach content owners

## Peer Review Guidance
Participants should provide:
- one strength
- one risk or missing safeguard
- one recommendation for reuse at scale

Keep tone supportive and improvement-oriented.

## Facilitator Dashboard and Delivery Surfaces
- Facilitator dashboard: `/workshop/session/<code>/facilitator`
  - monitor total submissions, anonymous participation, feedback coverage, and activity-level completion.
- Coach mode: `/workshop/session/<code>/coach`
  - keep teams focused on partner-centered teaching language.
- Review mode: `/workshop/session/<code>/review`
  - reinforce human-required decisions and final safeguards.
- Share mode: `/workshop/session/<code>/share`
  - publish reusable artifacts and trigger export downloads.
- Follow-Through page: `/workshop/session/<code>/follow-through`
  - save reusable coaching templates, checklists, and 30-day commitments.

## Capstone and Exit
Each participant or team leaves with:
- one reusable workflow artifact
- one explicit human-review safeguard
- one 30-day action commitment

## Conference Delivery Notes
- provide short URLs in addition to QR codes
- keep backup offline worksheets available
- avoid time-box pressure that blocks accessible participation
- allow participants to anonymize sensitive examples

## Incident Handling
If workshop app features degrade:
1. switch to backup worksheet mode
2. continue facilitation sequence without technical interruption
3. capture artifacts manually for post-session import

## Post-Session Follow-Up
Within 48 hours:
- export artifacts
- send participants a resource packet
- include 30-day reminder template

Within 30 days:
- request brief implementation update
- collect examples of workflow reuse
- identify candidates for future GLOW skills/prompts
