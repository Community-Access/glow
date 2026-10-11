# Workshop Mode Data Model and API Notes

## Overview
Workshop Mode uses a lightweight SQLite database in instance storage for training reliability and simple deployment.

Database file:
- `instance/workshop_mode.db`

## Tables

### workshop_sessions
- `session_code` TEXT PRIMARY KEY
- `title` TEXT NOT NULL
- `event_name` TEXT
- `created_at_utc` TEXT NOT NULL

### workshop_submissions
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `session_code` TEXT NOT NULL
- `activity_key` TEXT NOT NULL
- `display_name` TEXT NOT NULL
- `anonymity_mode` INTEGER NOT NULL DEFAULT 0
- `content_text` TEXT NOT NULL
- `created_at_utc` TEXT NOT NULL
- `updated_at_utc` TEXT NOT NULL

### workshop_feedback
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `session_code` TEXT NOT NULL
- `submission_id` INTEGER NOT NULL
- `reviewer_display_name` TEXT NOT NULL
- `strength` TEXT NOT NULL
- `risk_or_gap` TEXT NOT NULL
- `recommended_safeguard` TEXT NOT NULL
- `reuse_suggestion` TEXT NOT NULL
- `created_at_utc` TEXT NOT NULL

## Session Code Rules
Accepted pattern:
- 3 to 64 characters
- letters, numbers, dash, underscore

## Activity Keys
- `journey_check_in`
- `problem_statement`
- `teach_vs_fix`
- `ai_boundary_map`
- `agent_formula`
- `lab_accessible_communication`
- `lab_alt_text_decision`
- `lab_remediation_plan`
- `champion_studio`
- `capstone_shareout`
- `action_plan_30_day`

## Current Route Contracts

### Join/Start Session
- `POST /workshop/`
- Inputs:
  - `session_code`
  - `session_title`
- Behavior:
  - creates session if missing
  - redirects to first guided activity

### Save Activity Submission
- `POST /workshop/session/<code>/activity/<activity_key>`
- Inputs:
  - `display_name`
  - `anonymity_mode` (optional)
  - `content_text`
- Behavior:
  - inserts submission row
  - shows status and allows navigation to next activity

### Save Peer Feedback
- `POST /workshop/session/<code>/submission/<id>/feedback`
- Inputs:
  - `reviewer_display_name`
  - `strength`
  - `risk_or_gap`
  - `recommended_safeguard`
  - `reuse_suggestion`

### Export Artifacts
- `GET /workshop/session/<code>/export/markdown`
- Output:
  - Markdown attachment with submissions and peer feedback

## Accessibility Notes
- Anonymous sharing is supported for participant privacy in gallery contexts.
- Peer feedback structure enforces strengths, risks, safeguards, and reuse guidance.
- Export retains human-review fields to preserve accountability.
