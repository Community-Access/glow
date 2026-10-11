# Workshop Mode Implementation Plan

## Objective
Build a training-first GLOW experience for conference and institutional workshops that is approachable, accessible, and repeatable.

## Primary User Types
- Accessibility specialists
- Instructional designers
- Faculty and staff partners
- Disability services teams
- Communications and content owners
- Workshop facilitators

## Core Product Capabilities
1. Guided workshop flow
- Structured activity sequence from orientation to capstone.
- Step-by-step prompts for each lab.
- Autosave and resume support.

2. Artifact generation
- Capture participant outputs in a normalized data model.
- Support reusable exports:
  - Markdown
  - Word
  - JSON

3. Shared learning loop
- Accessible gallery cards for participant work.
- Structured peer feedback workflow.
- Facilitator curation and highlight queue.

4. Trust and governance
- Human-review checkpoints in every AI-assisted activity.
- Transparent status indicators for scan and deployment quality.
- Auditability for workflow changes and featured outputs.

## Data Model (Initial)
- workshop_session
  - id
  - title
  - event_name
  - session_code
  - facilitator_id
  - start_at_utc
  - end_at_utc
  - status
- participant_submission
  - id
  - workshop_session_id
  - activity_key
  - display_name
  - anonymity_mode
  - content_json
  - created_at_utc
  - updated_at_utc
- peer_feedback
  - id
  - workshop_session_id
  - submission_id
  - reviewer_display_name
  - strengths
  - risk_or_gap
  - recommended_safeguard
  - reuse_suggestion
  - created_at_utc

## Activity Keys
- journey_check_in
- problem_statement
- teach_vs_fix
- ai_boundary_map
- agent_formula
- lab_accessible_communication
- lab_alt_text_decision
- lab_remediation_plan
- champion_studio
- peer_review
- capstone_shareout
- action_plan_30_day

## API and Route Phasing
Phase A (Foundation)
- `GET /workshop/`
- workshop metadata and static agenda view

Status:
- Complete on branch `feature/glow-7-3-workshop-mode`.

Phase B (Guided Forms)
- `GET /workshop/session/<code>/activity/<activity_key>`
- `POST /workshop/session/<code>/activity/<activity_key>`

Status:
- Initial implementation complete (session start/join + activity submission flow).

Phase C (Gallery + Peer Review)
- `GET /workshop/session/<code>/gallery`
- `POST /workshop/session/<code>/peer-feedback`

Status:
- Initial implementation complete (gallery + peer feedback persistence).

Phase D (Facilitator Console)
- `GET /workshop/session/<code>/facilitator`
- `POST /workshop/session/<code>/export`

Status:
- Export path partially complete (markdown export endpoint implemented).
- Facilitator dashboard remains planned.

## WCAG 2.2 AA Engineering Checklist
- Use semantic landmarks and heading order.
- Maintain keyboard-first interaction for all controls.
- Ensure visible focus indicators and no focus traps.
- Provide labeled forms with inline instructions.
- Use clear, descriptive links and button labels.
- Ensure schedule views use proper table semantics.
- Avoid color-only status communication.
- Ensure 200% zoom and reflow behavior.
- Keep dynamic updates screen-reader compatible.

## QA Gates
Automated:
- axe-core scan with WCAG 2.2 AA tags on workshop routes.
- no critical/serious violations.

Manual:
- keyboard-only completion of all activities.
- screen reader smoke test on:
  - navigation
  - form submission and errors
  - gallery cards
  - peer feedback flow

## Security and Privacy Baseline
- CSRF protection on all writes.
- Input size limits and sanitization for rich text fields.
- Optional anonymous submission mode.
- No PII in default export unless user opts in.

## Operational Readiness
- Pre-event environment checklist
- Backup worksheet path when network instability occurs
- Facilitator support playbook for common issues

## Success Metrics
- completion rate per activity
- artifact reuse rate after event
- participant confidence delta (pre/post)
- 30-day follow-through rate
- facilitator effort score
