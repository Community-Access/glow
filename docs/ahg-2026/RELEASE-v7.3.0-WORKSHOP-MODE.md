# GLOW 7.3.0 Workshop Mode (Draft)

## Purpose
GLOW 7.3.0 introduces a conference and training focused capability called Workshop Mode.

Workshop Mode is designed to help participants who are not developers, AI engineers, or accessibility specialists complete practical accessibility activities with guided, repeatable workflows.

## Theme
Accessibility Agents in Action: a hands-on GLOW workflow model for helping everyone become an accessibility champion.

GLOW framework:
- G: Ground the work in a real accessibility problem.
- L: Learn what people need to understand.
- O: Organize a repeatable workflow.
- W: Walk forward as accessibility champions.

## What is Included in This Build
- New feature flags for Workshop Mode rollout control.
- New workshop route at `/workshop/`.
- Initial accessible workshop experience with:
  - clear heading hierarchy,
  - keyboard-accessible skip link,
  - outcomes list,
  - agenda table with caption and scoped headers,
  - lab-hub capability indicators.
- Workshop Lab Hub persistence and flow:
  - session start/join by session code,
  - guided activity submissions,
  - shared gallery view,
  - peer feedback capture,
  - markdown artifact export.
- Documentation set for implementation, facilitation, and WCAG quality gates.

## Feature Flags
- `GLOW_ENABLE_WORKSHOP_MODE`
- `GLOW_ENABLE_WORKSHOP_LAB_HUB`
- `GLOW_ENABLE_WORKSHOP_GALLERY`
- `GLOW_ENABLE_WORKSHOP_PEER_REVIEW`

All flags are wired into template context for progressive rollout.

## WCAG 2.2 AA Expectations
Workshop Mode content and interactions must satisfy:
- semantic landmarks and one H1 per page,
- keyboard-only operability,
- visible focus indicators,
- descriptive link text,
- table semantics for schedule data,
- contrast compliance for text and controls,
- no color-only meaning,
- support for zoom and reflow,
- human-review guidance in AI-supported activities.

## Workshop Outcomes Target
Participants leave with at least one reusable artifact:
- GLOW-ready prompt,
- checklist,
- partner coaching message,
- remediation planning workflow,
- 30-day action plan.

## Non-Goals in This Phase
- LMS integration,
- enterprise role provisioning,
- advanced analytics dashboards,
- multilingual localization beyond baseline readiness.

## Rollout Guidance
- Keep feature-flagged in early internal pilots.
- Run facilitator dry-runs before conference deployment.
- Validate with keyboard and screen reader smoke tests before each event.

## Implemented Routes (Current)
- `GET/POST /workshop/` - workshop home plus session join/start.
- `GET/POST /workshop/session/<code>/activity/<activity_key>` - guided activity form flow.
- `GET /workshop/session/<code>/gallery` - workshop submissions and peer feedback.
- `POST /workshop/session/<code>/submission/<id>/feedback` - structured peer review save.
- `GET /workshop/session/<code>/export/markdown` - export workshop artifacts.

## Next Steps
- Implement guided form flow for all workshop worksheets.
- Add gallery and peer feedback persistence.
- Add facilitator dashboard with export to Markdown and Word.
- Add post-session action plan tracking.
