"""Workshop mode routes for training and conference delivery (7.3.0)."""

from __future__ import annotations

import hmac
import os
from datetime import UTC, datetime
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    g,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from markupsafe import Markup, escape

from ..app import limiter
from ..email import email_configured, send_workshop_return_link_email
from ..feature_flags import get_flag
from ..workshop_scenarios import get_scenario, pick_scenario, scenarios_for
from ..workshop_worksheets import (
    Worksheet,
    WorksheetField,
    build_worksheet_docx_bytes,
    build_worksheet_html,
)
from ..workshop_skills import (
    build_copy_prompt,
    build_skill_markdown,
    build_skill_zip_bytes,
)
from ..workshop_store import (
    add_feedback,
    bind_participant_login,
    consume_return_link,
    count_submissions,
    create_or_update_participant,
    create_return_link,
    decode_field_values,
    ensure_session,
    export_follow_through_markdown,
    export_session_docx_bytes,
    export_session_html,
    export_session_json,
    export_session_markdown,
    get_conference_code,
    get_facilitator_key,
    get_participant,
    get_participant_submission,
    get_session,
    list_feedback_for_session,
    list_follow_through_items,
    list_submissions,
    list_submissions_for_participant,
    load_conference_codes_from_env,
    load_conference_codes_from_file,
    normalize_session_code,
    return_link_ttl_days,
    save_follow_through_item,
    save_submission,
    update_follow_through_status,
)
from .admin import is_authenticated_admin

workshop_bp = Blueprint("workshop", __name__)
PARTICIPANT_COOKIE = "glow_workshop_participant"

ACTIVITY_ORDER = [
    "journey_check_in",
    "problem_statement",
    "teach_vs_fix",
    "ai_boundary_map",
    "agent_formula",
    "lab_accessible_communication",
    "lab_alt_text_decision",
    "lab_remediation_plan",
    "champion_studio",
    "capstone_shareout",
    "action_plan_30_day",
]

ACTIVITY_PROMPTS = {
    "journey_check_in": "What accessibility work do you do? Where do partners get stuck? What would change if more of them became accessibility champions?",
    "problem_statement": "Start with the problem you can see today. Then name the deeper problem behind it. Who needs to learn this work or own part of it? What would success look like if it happened again and again, without you?",
    "teach_vs_fix": "Take a request that says 'just fix it for me.' Write a reply that coaches instead. Your reply should solve the problem today. It should also teach the person to do it next time.",
    "ai_boundary_map": "Sort your tasks into three groups. Which ones can AI help with? Which ones are risky unless a person checks the work? Which ones need a human to decide? Then list the safeguards you would add.",
    "agent_formula": "Design an accessibility helper for the partners you support. Use the five-part formula. Give it a role, a task, guidance it can trust, and a format for what it gives back. Then add the human review step.",
    "lab_accessible_communication": "Rewrite a real message so more people can read it. Use plain words and short sentences. Add clear headings. Make each link say where it goes. Add welcoming words about how to ask for access help.",
    "lab_alt_text_decision": "Write down why the image is there. Say what a reader must know about it. Say what you can leave out. Then list what a person must check before the alt text goes live.",
    "lab_remediation_plan": "Make a remediation plan for a real document, slide, or course page. List the barriers you find. Put the fixes in order, most important first. Then write how you would coach the owner, so the next version is better.",
    "champion_studio": "Design a workflow you can use again and again. It should teach your partners to own the work. Say who does each step. Name the point where a person must review the result before it goes out.",
    "capstone_shareout": "Sum up your workflow in a few sentences. Say who it helps and what they learn. Then explain how it keeps accessibility work going after today.",
    "action_plan_30_day": "Choose one workflow to try in the next 30 days. Choose one partner or team to help. Choose one safeguard you will use every time. Then name the first step you will take.",
}

ACTIVITY_META = {
    "journey_check_in": {"title": "Accessibility Journey Check-In", "time": "20 minutes", "badge": "Journey Mapper"},
    "problem_statement": {"title": "What Problem Are We Solving?", "time": "35 minutes", "badge": "Problem Framer"},
    "teach_vs_fix": {"title": "Fix It for Me vs Teach Me to Improve It", "time": "35 minutes", "badge": "Coaching Catalyst"},
    "ai_boundary_map": {"title": "Helpful, Risky, or Human Required?", "time": "35 minutes", "badge": "Boundary Builder"},
    "agent_formula": {"title": "Accessibility Agent Formula", "time": "35 minutes", "badge": "Agent Architect"},
    "lab_accessible_communication": {"title": "GLOW Lab 1: Accessible Communications", "time": "55 minutes", "badge": "Communication Coach"},
    "lab_alt_text_decision": {"title": "GLOW Lab 2: Alt Text and Human Judgment", "time": "50 minutes", "badge": "Meaning Mapper"},
    "lab_remediation_plan": {"title": "GLOW Lab 3: Remediation Planning", "time": "50 minutes", "badge": "Remediation Planner"},
    "champion_studio": {"title": "Accessibility Champion Studio", "time": "45 minutes", "badge": "Champion Designer"},
    "capstone_shareout": {"title": "Capstone Share-Out", "time": "25 minutes", "badge": "Story Sharer"},
    "action_plan_30_day": {"title": "30-Day Action Plan", "time": "15 minutes", "badge": "Momentum Builder"},
}

ACTIVITY_FIELDS = {
    "journey_check_in": [
        {"name": "work_type", "label": "What kind of accessibility work do you do?", "rows": 3, "required": True},
        {"name": "partner_blockers", "label": "Where do partners most often get stuck?", "rows": 3, "required": True},
        {"name": "champion_shift", "label": "What would change if more people became accessibility champions?", "rows": 3, "required": True},
    ],
    "problem_statement": [
        {"name": "surface_problem", "label": "The problem you can see today", "rows": 2, "required": True},
        {"name": "capacity_problem", "label": "The deeper problem behind it (capacity)", "rows": 2, "required": True},
        {"name": "who_learns", "label": "Who needs to learn or own part of this?", "rows": 2, "required": True},
        {"name": "repeatable_success", "label": "What would success look like if it happened every time?", "rows": 2, "required": True},
    ],
    "teach_vs_fix": [
        {"name": "partner_request", "label": "What the partner asked you to do", "rows": 2, "required": True},
        {"name": "immediate_need", "label": "What has to be fixed today", "rows": 2, "required": True},
        {"name": "partner_learning", "label": "What the partner needs to learn", "rows": 2, "required": True},
        {"name": "coaching_response", "label": "Your coaching reply", "rows": 4, "required": True},
    ],
    "ai_boundary_map": [
        {"name": "tasks", "label": "Tasks you want to sort", "rows": 3, "required": True},
        {"name": "boundaries", "label": "Sort each task: AI can help, risky without review, or human only", "rows": 3, "required": True},
        {"name": "safeguards", "label": "Safeguards and review steps", "rows": 3, "required": True},
    ],
    "agent_formula": [
        {"name": "role", "label": "Role: who the helper acts as", "rows": 2, "required": True},
        {"name": "task", "label": "Task: what you want it to do", "rows": 2, "required": True},
        {"name": "trusted_guidance", "label": "Trusted guidance: the rules or standards it should follow", "rows": 3, "required": True},
        {"name": "output_format", "label": "Output format: what you want it to give back", "rows": 2, "required": True},
        {"name": "human_review", "label": "Human review: what a person must check", "rows": 2, "required": True},
    ],
    "lab_accessible_communication": [
        {"name": "communication_type", "label": "What is the message, and who reads it?", "rows": 2, "required": True},
        {"name": "top_issues", "label": "The biggest problems you found", "rows": 3, "required": True},
        {"name": "revised_content", "label": "Your rewritten version", "rows": 5, "required": True},
        {"name": "teaching_note", "label": "Teaching note for the person who owns this content", "rows": 3, "required": True},
        {"name": "review_checklist", "label": "Human-review checklist", "rows": 3, "required": True},
    ],
    "lab_alt_text_decision": [
        {"name": "image_context", "label": "Where the image appears", "rows": 2, "required": True},
        {"name": "image_purpose", "label": "Why the image is there", "rows": 2, "required": True},
        {"name": "relevant_info", "label": "What the alt text must say", "rows": 2, "required": True},
        {"name": "omit_info", "label": "What you can leave out", "rows": 2, "required": True},
        {"name": "draft_alt", "label": "Your draft alt text, or notes for a longer description", "rows": 3, "required": True},
        {"name": "verification_questions", "label": "What a person must check before this goes live", "rows": 2, "required": True},
    ],
    "lab_remediation_plan": [
        {"name": "content_track", "label": "What is this content, and who uses it?", "rows": 2, "required": True},
        {"name": "likely_barriers", "label": "Barriers people may hit", "rows": 3, "required": True},
        {"name": "priority_fixes", "label": "Fixes to do first", "rows": 3, "required": True},
        {"name": "owner_questions", "label": "Questions for the person who owns this content", "rows": 3, "required": True},
        {"name": "human_inspection", "label": "What a person must check by hand", "rows": 2, "required": True},
        {"name": "coaching_message", "label": "Coaching message", "rows": 3, "required": True},
    ],
    "champion_studio": [
        {"name": "workflow_name", "label": "Workflow name", "rows": 2, "required": True},
        {"name": "partner_group", "label": "Who this workflow helps", "rows": 2, "required": True},
        {"name": "responsibility", "label": "What you want your partners to learn to do themselves", "rows": 3, "required": True},
        {"name": "ai_support", "label": "Where GLOW or AI can help", "rows": 3, "required": True},
        {"name": "final_output", "label": "What the workflow produces", "rows": 2, "required": True},
        {"name": "human_safeguard", "label": "Human-review safeguard", "rows": 2, "required": True},
    ],
    "capstone_shareout": [
        {"name": "workflow_summary", "label": "Workflow summary", "rows": 3, "required": True},
        {"name": "who_it_helps", "label": "Who it helps and what they learn", "rows": 3, "required": True},
        {"name": "reusability", "label": "How you will use it again", "rows": 2, "required": True},
        {"name": "safeguard", "label": "Final human-review safeguard", "rows": 2, "required": True},
    ],
    "action_plan_30_day": [
        {"name": "workflow_30", "label": "One workflow to try in the next 30 days", "rows": 2, "required": True},
        {"name": "partner_team_30", "label": "One partner or team to support", "rows": 2, "required": True},
        {"name": "safeguard_30", "label": "One safeguard to include every time", "rows": 2, "required": True},
        {"name": "first_step_30", "label": "The first step you will take", "rows": 2, "required": True},
    ],
}

EXERCISE_PACK = [
  {
    "name": "Accessibility Journey Check-In",
    "time": "20 minutes",
    "purpose": "Help participants locate themselves in the accessibility journey and identify partner support needs.",
    "output": "Accessibility journey notes and shared barriers list.",
  },
  {
    "name": "What Problem Are We Solving?",
    "time": "35 minutes",
    "purpose": "Train teams to start with the accessibility problem before selecting tools.",
    "output": "Problem statement with capacity-building focus.",
  },
  {
    "name": "Fix It for Me vs Teach Me to Improve It",
    "time": "40 minutes",
    "purpose": "Practice converting urgent fix requests into teachable coaching responses.",
    "output": "Coaching response patterns for partner ownership.",
  },
  {
    "name": "Helpful, Risky, or Human Required",
    "time": "40 minutes",
    "purpose": "Establish practical responsible-AI boundaries for accessibility tasks.",
    "output": "AI boundary map with review safeguards.",
  },
  {
    "name": "Accessibility Agent Formula",
    "time": "45 minutes",
    "purpose": "Build non-technical agent concepts using a repeatable formula.",
    "output": "Role + Task + Guidance + Output + Human Review draft.",
  },
  {
    "name": "GLOW Lab 1: Accessible Communications",
    "time": "60 minutes",
    "purpose": "Improve real communication artifacts while teaching reusable accessibility patterns.",
    "output": "Revised communication and human-review checklist.",
  },
  {
    "name": "GLOW Lab 2: Alt Text and Human Judgment",
    "time": "55 minutes",
    "purpose": "Use AI support without losing human control of image purpose and meaning.",
    "output": "Image purpose decision checklist with verification questions.",
  },
  {
    "name": "GLOW Lab 3: Remediation Planning",
    "time": "55 minutes",
    "purpose": "Turn large remediation requests into practical coaching workflows.",
    "output": "Prioritized remediation coaching template.",
  },
  {
    "name": "Accessibility Champion Studio",
    "time": "50 minutes",
    "purpose": "Design reusable partner-facing workflows for local institutional needs.",
    "output": "Draft champion workflow artifact.",
  },
]

RESOURCE_FILES = {
  "guide": "workshop-frontfacing-guide.md",
  "exercises": "workshop-frontfacing-exercises.md",
  "utilization": "workshop-frontfacing-utilization.md",
}

WORKSHOP_ACTION_TOKENS = {
    "GLOW:AUDIT": ("Audit Workspace", "audit.audit_form"),
    "GLOW:FIX": ("Fix Workspace", "fix.fix_form"),
    "GLOW:CONVERT": ("Convert Workspace", "convert.convert_form"),
    "GLOW:TEMPLATE": ("Template Builder", "template.template_form"),
    "GLOW:CHAT": ("Document Chat", "chat.chat_form"),
    "GLOW:ALT_TEXT": ("Alt-Text Helper", "alt_text.alt_text_form"),
    "GLOW:MAGIC": ("Magic Lab", "magic.magic_home"),
}

WORKSHOP_SAMPLE_FILES = {
    "board-agenda-docx": "04 - April 8 2026 BITS Board Meeting Agenda.docx",
    "board-agenda-md": "04 - April 8 2026 BITS Board Meeting Agenda.md",
    "board-agenda-html": "04 - April 8 2026 BITS Board Meeting Agenda.html",
    "glow-test-docx": "GLOW Test 2.docx",
}

MAGIC_SCENARIOS = [
    {
        "id": "communication-refresh",
        "title": "Accessible Communication Refresh",
        "goal": "Turn a dense announcement into a plain-language, well-structured communication.",
        "tokens": ["GLOW:AUDIT", "GLOW:FIX", "GLOW:TEMPLATE"],
        "sample_slug": "board-agenda-docx",
        "activity_key": "lab_accessible_communication",
        "workflow_text": "Run [[GLOW:AUDIT]] to identify barriers, draft improvements in [[GLOW:FIX]], then save a reusable coaching script in [[GLOW:TEMPLATE]].",
    },
    {
        "id": "alt-text-judgment",
        "title": "Alt Text and Human Judgment",
        "goal": "Practice purpose-first image decisions with explicit human verification.",
        "tokens": ["GLOW:ALT_TEXT", "GLOW:CHAT", "GLOW:TEMPLATE"],
        "sample_slug": "board-agenda-html",
        "activity_key": "lab_alt_text_decision",
        "workflow_text": "Use [[GLOW:ALT_TEXT]] for first-draft guidance, pressure-test language in [[GLOW:CHAT]], and package a checklist in [[GLOW:TEMPLATE]].",
    },
    {
        "id": "remediation-prioritization",
        "title": "Remediation Prioritization Sprint",
        "goal": "Convert a large remediation problem into a realistic, teachable plan.",
        "tokens": ["GLOW:AUDIT", "GLOW:CONVERT", "GLOW:MAGIC"],
        "sample_slug": "glow-test-docx",
        "activity_key": "lab_remediation_plan",
        "workflow_text": "Start with [[GLOW:AUDIT]] for evidence, summarize action tracks in [[GLOW:CONVERT]], and use [[GLOW:MAGIC]] for advanced advisory checks.",
    },
]


FACILITATOR_SESSION_PREFIX = "workshop_facilitator:"
GALLERY_PAGE_SIZE = 10
FEEDBACK_DRAFT_SESSION_KEY = "workshop_feedback_draft"


def _gallery_return_args() -> dict:
    """The page and filter the caller was looking at.

    Both gallery forms post from a specific page of a possibly-filtered list.
    Redirecting back to an unfiltered page 1 would strand the reviewer away
    from the card they were working on -- and because the stashed feedback
    draft is only rendered on the card it belongs to, it would be popped from
    the session and silently thrown away.
    """
    args: dict = {}
    page_raw = (request.form.get("return_page") or "").strip()
    if page_raw.isdigit() and int(page_raw) > 1:
        args["page"] = int(page_raw)
    activity = (request.form.get("return_activity") or "").strip()
    if activity in ACTIVITY_PROMPTS:
        args["activity"] = activity
    return args
STATUS_LABELS = {"open": "Open", "done": "Complete", "paused": "Paused"}
FOLLOW_THROUGH_GROUPS = [
    ("action_commitment", "30-day commitments", "No commitments saved yet."),
    ("template", "Reusable coaching templates", "No templates saved yet."),
    ("checklist", "Checklists", "No checklists saved yet."),
]


# ---------------------------------------------------------------------------
# Runtime asset resolution
# ---------------------------------------------------------------------------

def _asset_roots() -> list[Path]:
    """Candidate roots that may contain the runtime ``samples/`` and ``docs/``.

    These files are read off disk rather than served from the package, so the
    layout differs by deployment. In a source checkout the package sits at
    ``<repo>/web/src/acb_large_print_web`` and walking up three parents finds
    the repo root. In the container the package is pip-installed into
    site-packages, so that same walk lands in the Python prefix instead --
    which is why the sample and resource downloads used to 404 in production.
    Probe the plausible roots and use whichever actually holds the file.
    """
    roots: list[Path] = []

    configured = (os.environ.get("GLOW_WORKSHOP_ASSET_ROOT") or "").strip()
    if configured:
        roots.append(Path(configured))

    root_path = Path(current_app.root_path)
    if len(root_path.parents) >= 3:
        roots.append(root_path.parents[2])  # source checkout
    roots.append(Path(current_app.instance_path).parent)  # /app in the image
    roots.append(Path.cwd())

    seen: set[str] = set()
    unique: list[Path] = []
    for root in roots:
        key = str(root)
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def _resolve_asset(*relative_parts: str) -> Path | None:
    """Return the first existing asset path across the candidate roots."""
    for root in _asset_roots():
        candidate = root.joinpath(*relative_parts)
        if candidate.is_file():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

def _workshop_enabled() -> bool:
    return bool(get_flag("GLOW_ENABLE_WORKSHOP_MODE", True))


def _lab_hub_enabled() -> bool:
    return bool(get_flag("GLOW_ENABLE_WORKSHOP_LAB_HUB", True))


def _gallery_enabled() -> bool:
    return bool(get_flag("GLOW_ENABLE_WORKSHOP_GALLERY", True))


def _peer_review_enabled() -> bool:
    return bool(get_flag("GLOW_ENABLE_WORKSHOP_PEER_REVIEW", True))


# ---------------------------------------------------------------------------
# Facilitator access
# ---------------------------------------------------------------------------

def _expected_facilitator_key(code: str) -> str | None:
    """The key that unlocks facilitator tools for *code*, if one is configured.

    Per-session keys come from the conference-code config (JSON file or the
    WORKSHOP_CONFERENCE_CODES_JSON variable). GLOW_WORKSHOP_FACILITATOR_KEY is
    the fallback for ad-hoc sessions created on the day.
    """
    try:
        configured = get_facilitator_key(code)
    except ValueError:
        configured = None
    if configured:
        return configured
    env_key = (os.environ.get("GLOW_WORKSHOP_FACILITATOR_KEY") or "").strip()
    return env_key or None


def _is_facilitator(code: str) -> bool:
    """True when the caller may see session-wide participant work.

    An approved GLOW admin always qualifies. Otherwise the caller must have
    unlocked this specific session with its facilitator key. When no key is
    configured anywhere only admins qualify -- failing closed, because these
    surfaces expose every participant's submissions.
    """
    if is_authenticated_admin():
        return True
    expected = _expected_facilitator_key(code)
    if not expected:
        return False
    granted = session.get(FACILITATOR_SESSION_PREFIX + code)
    return bool(granted) and hmac.compare_digest(str(granted), expected)


def _facilitator_unlock_response(code: str, *, error: str = "", status: int = 403):
    """Render the unlock prompt for a caller who is not a facilitator."""
    return (
        render_template(
            "workshop/facilitator_unlock.html",
            session_code=code,
            error=error,
            key_configured=bool(_expected_facilitator_key(code)),
        ),
        status,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _activity_title(activity_key: str) -> str:
    return ACTIVITY_META.get(activity_key, {}).get("title", activity_key)


def _activity_titles() -> dict[str, str]:
    return {key: _activity_title(key) for key in ACTIVITY_ORDER}


def _format_timestamp(value: str) -> str:
    """Render a stored ISO-8601 UTC timestamp in a readable form."""
    raw = (value or "").strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return raw
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).strftime("%d %B %Y at %H:%M UTC")


def _decorate_submissions(rows: list[dict]) -> list[dict]:
    """Attach display-ready fields without mutating the stored rows."""
    decorated = []
    for row in rows:
        item = dict(row)
        item["updated_display"] = _format_timestamp(str(item.get("updated_at_utc", "")))
        decorated.append(item)
    return decorated


def _workshop_return_target(session_code: str, *, activity_key: str | None = None) -> str:
    key = (activity_key or "").strip()
    if key and key in ACTIVITY_PROMPTS:
        return url_for("workshop.workshop_activity", session_code=session_code, activity_key=key)
    return url_for("workshop.workshop_launchpad", session_code=session_code)


def _action_link_for_token(token: str, session_code: str, *, return_to: str) -> tuple[str, str]:
    label, endpoint = WORKSHOP_ACTION_TOKENS[token]
    href = url_for(
        endpoint,
        workshop_return=return_to,
        workshop_label=f"Return to Workshop ({session_code})",
    )
    return label, href


def _render_tokenized_workflow_text(text: str, session_code: str, *, return_to: str) -> Markup:
    rendered = escape(text or "")
    for token, (label, endpoint) in WORKSHOP_ACTION_TOKENS.items():
        pattern = f"[[{token}]]"
        if pattern in rendered:
            href = url_for(
                endpoint,
                workshop_return=return_to,
                workshop_label=f"Return to Workshop ({session_code})",
            )
            link = f'<a href="{escape(href)}">{escape(label)}</a>'
            rendered = rendered.replace(pattern, link)
    return Markup(rendered)


def _serialize_activity_submission(
    activity_key: str,
    fields: list[dict],
    values: dict[str, str],
    bonus_note: str,
    scenario_title: str = "",
) -> str:
    lines: list[str] = []
    lines.append(f"Activity: {_activity_title(activity_key)}")
    lines.append(f"Activity key: {activity_key}")
    if scenario_title.strip():
        # Which brief the answer responds to. Without this an exported
        # remediation plan reads as advice about nothing in particular.
        lines.append(f"Scenario: {scenario_title.strip()}")
    lines.append("")
    for field in fields:
        label = field.get("label", field.get("name", "Field"))
        value = (values.get(field.get("name", "")) or "").strip()
        lines.append(f"{label}:")
        lines.append(value or "(not provided)")
        lines.append("")
    if bonus_note.strip():
        lines.append("Bonus reflection:")
        lines.append(bonus_note.strip())
        lines.append("")
    return "\n".join(lines).strip()


def _resolve_session_from_access_code(raw_code: str) -> tuple[str, str, str]:
    """Resolve a user-entered access code to (session_code, title, event_name).

    Supports configured conference codes, direct existing session codes, and
    ad-hoc session creation.
    """
    value = (raw_code or "").strip()
    if not value:
        raise ValueError("Please enter a workshop or conference code.")

    mapped = get_conference_code(value)
    if mapped:
        return (
            str(mapped.get("session_code", "")).strip(),
            str(mapped.get("session_title", "GLOW Workshop Session")).strip() or "GLOW Workshop Session",
            str(mapped.get("event_name", "")).strip(),
        )

    code = normalize_session_code(value)
    existing = get_session(code)
    if existing:
        return (
            code,
            str(existing.get("title", "GLOW Workshop Session")).strip() or "GLOW Workshop Session",
            str(existing.get("event_name", "")).strip(),
        )

    return (code, "GLOW Workshop Session", "")


def _active_login_email() -> str | None:
    user = getattr(g, "oidc_user_info", {}) if g is not None else {}
    if isinstance(user, dict):
        email = (user.get("email") or "").strip()
        if email:
            return email
    return None


def _set_participant_cookie(resp, participant_key: str):
    resp.set_cookie(
        PARTICIPANT_COOKIE,
        participant_key,
        max_age=60 * 60 * 24 * 90,
        httponly=True,
        samesite="Lax",
    )
    return resp


def _current_participant(code: str) -> dict | None:
    """The participant identified by this device's cookie, if it matches *code*."""
    participant_key = (request.cookies.get(PARTICIPANT_COOKIE) or "").strip()
    if not participant_key:
        return None
    participant = get_participant(participant_key)
    if not participant or str(participant.get("session_code", "")).strip() != code:
        return None
    if _active_login_email():
        bind_participant_login(str(participant.get("participant_key", "")), _active_login_email() or "")
    return participant


def _require_session(session_code: str) -> str:
    try:
        code = normalize_session_code(session_code)
    except ValueError:
        abort(404)
    if get_session(code) is None:
        abort(404)
    return code


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

@workshop_bp.route("/", methods=["GET", "POST"])
def workshop_home():
    if not _workshop_enabled():
        abort(404)

    # Best-effort code loading for conference events.
    try:
        load_conference_codes_from_env()
        load_conference_codes_from_file()
    except Exception:
        pass

    error = ""
    info = ""
    session_code = ""
    session_title = "GLOW Workshop Session"
    session_event = ""
    join_mode = False
    participant_display_name = "Participant"

    query_code = (request.args.get("code") or "").strip()
    if query_code:
        try:
            session_code, session_title, session_event = _resolve_session_from_access_code(query_code)
            ensure_session(session_code, title=session_title, event_name=session_event)
            join_mode = True
        except ValueError as exc:
            error = str(exc)

    if join_mode:
        participant = _current_participant(session_code)
        if participant:
            participant_display_name = str(participant.get("display_name", "Participant")).strip() or "Participant"
            info = "Welcome back. Your personal workshop content is ready."

    if request.method == "POST":
        action = (request.form.get("action") or "lookup").strip().lower()
        if action == "lookup":
            raw_code = (request.form.get("access_code") or "").strip()
            try:
                code, title, event_name = _resolve_session_from_access_code(raw_code)
                ensure_session(code, title=title, event_name=event_name)
                return redirect(url_for("workshop.workshop_home", code=code))
            except ValueError as exc:
                error = str(exc)
                session_code = raw_code
        elif action == "join":
            code = (request.form.get("session_code") or "").strip()
            display_name = (request.form.get("display_name") or "Participant").strip() or "Participant"
            try:
                normalized_code = normalize_session_code(code)
                session_meta = get_session(normalized_code)
                if session_meta is None:
                    abort(404)
                existing_key = (request.cookies.get(PARTICIPANT_COOKIE) or "").strip()
                participant_row = create_or_update_participant(
                    normalized_code,
                    display_name,
                    participant_key=existing_key or None,
                    login_email=_active_login_email(),
                )
                resp = make_response(
                    redirect(
                        url_for(
                            "workshop.workshop_activity",
                            session_code=normalized_code,
                            activity_key=ACTIVITY_ORDER[0],
                        )
                    )
                )
                return _set_participant_cookie(resp, str(participant_row.get("participant_key", "")))
            except ValueError as exc:
                error = str(exc)
                session_code = code
                join_mode = True

    schedule = [
        {"time": "8:30-8:50", "title": "Welcome and Accessibility Journey Check-In", "mode": "Reflection and group share"},
        {"time": "8:50-9:25", "title": "What Problem Are We Solving?", "mode": "Problem framing"},
        {"time": "9:25-10:00", "title": "From Fixing Everything to Teaching Partners to Fish", "mode": "Coaching practice"},
        {"time": "10:10-10:45", "title": "Human-Centered AI Boundaries", "mode": "Helpful, risky, human-required map"},
        {"time": "10:45-11:20", "title": "Accessibility Agents in Plain Language", "mode": "Role, task, guidance, output, human review"},
        {"time": "11:20-12:15", "title": "GLOW Lab 1: Accessible Communications", "mode": "Hands-on lab"},
        {"time": "1:15-2:05", "title": "GLOW Lab 2: Alt Text and Human Judgment", "mode": "Hands-on lab"},
        {"time": "2:05-2:55", "title": "GLOW Lab 3: Remediation Planning", "mode": "Hands-on lab"},
        {"time": "3:05-3:50", "title": "Accessibility Champion Studio", "mode": "Workflow design"},
        {"time": "3:50-4:15", "title": "Peer Review and Scaling Path", "mode": "Feedback and refinement"},
        {"time": "4:15-4:30", "title": "Capstone and 30-Day Action Plan", "mode": "Commitment and share-out"},
    ]

    outcomes = [
        "Frame accessibility work around a real human problem before selecting tools.",
        "Use AI support responsibly with explicit human-review safeguards.",
        "Build repeatable partner-facing workflows that teach, not only fix.",
        "Leave with reusable artifacts such as prompts, checklists, and action plans.",
    ]

    return render_template(
        "workshop/home.html",
        schedule=schedule,
        outcomes=outcomes,
        error=error,
        info=info,
        join_mode=join_mode,
        session_code=session_code,
        session_title=session_title,
        session_event=session_event,
        participant_display_name=participant_display_name,
    )


def _scenario_cards(activity_key: str, session_code: str, *, selected_id: str) -> list[dict]:
    """The scenario menu for one activity, ready to render."""
    cards = []
    for scenario in scenarios_for(activity_key):
        cards.append(
            {
                "id": scenario.id,
                "title": scenario.title,
                "sector": scenario.sector,
                "summary": scenario.summary,
                "selected": scenario.id == selected_id,
                "href": url_for(
                    "workshop.workshop_activity",
                    session_code=session_code,
                    activity_key=activity_key,
                    scenario=scenario.id,
                    _anchor="scenario",
                ),
            }
        )
    return cards


def _scenario_detail(scenario, session_code: str, *, activity_key: str) -> dict:
    """Expand one scenario into brief, tool links and starting material."""
    return_to = _workshop_return_target(session_code, activity_key=activity_key)
    action_links = []
    for token in scenario.tools:
        if token in WORKSHOP_ACTION_TOKENS:
            label, href = _action_link_for_token(token, session_code, return_to=return_to)
            action_links.append({"token": token, "label": label, "href": href})
    return {
        "id": scenario.id,
        "title": scenario.title,
        "sector": scenario.sector,
        "summary": scenario.summary,
        "brief": list(scenario.brief),
        "what_to_notice": list(scenario.what_to_notice),
        "stretch": scenario.stretch,
        "action_links": action_links,
        "sample_slug": scenario.sample_slug,
        "sample_name": WORKSHOP_SAMPLE_FILES.get(scenario.sample_slug, ""),
    }


@workshop_bp.route("/session/<session_code>/activity/<activity_key>", methods=["GET", "POST"])
def workshop_activity(session_code: str, activity_key: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    if activity_key not in ACTIVITY_PROMPTS:
        abort(404)

    try:
        code = normalize_session_code(session_code)
    except ValueError:
        abort(404)

    if get_session(code) is None:
        ensure_session(code)

    participant = _current_participant(code)
    participant_name = "Participant"
    if participant:
        participant_name = str(participant.get("display_name", "Participant")).strip() or "Participant"

    activity_fields = ACTIVITY_FIELDS.get(
        activity_key,
        [{"name": "response", "label": "Response", "rows": 6, "required": True}],
    )
    field_values = {field.get("name", ""): "" for field in activity_fields}
    bonus_note = ""
    anonymity_mode = False
    missing_fields: list[str] = []
    message = ""
    message_is_error = False

    scenario_id = ""

    if request.method == "POST":
        display_name = (request.form.get("display_name") or participant_name).strip() or participant_name
        anonymity_mode = bool(request.form.get("anonymity_mode"))
        scenario_id = (request.form.get("scenario_id") or "").strip()
        if not get_scenario(activity_key, scenario_id):
            scenario_id = ""
        submit_action = (request.form.get("submit_action") or "save").strip().lower()
        for field in activity_fields:
            key = field.get("name", "")
            field_values[key] = (request.form.get(key) or "").strip()
        bonus_note = (request.form.get("bonus_note") or "").strip()

        # A draft deliberately skips the required-field check so a participant
        # can park partial work and come back. The button carries
        # formnovalidate so the browser does not block it either.
        is_draft = submit_action == "draft"

        missing_fields = [] if is_draft else [
            str(field.get("name", ""))
            for field in activity_fields
            if field.get("required", True) and not field_values.get(field.get("name", ""), "").strip()
        ]

        if missing_fields:
            # Keep every entered value, the chosen display name and the
            # anonymity choice on the re-render. Losing the anonymity tick in
            # particular would republish a name the participant chose to hide.
            participant_name = display_name
            labels = [
                str(field.get("label", field.get("name", "field")))
                for field in activity_fields
                if str(field.get("name", "")) in missing_fields
            ]
            message = "Please complete these answers before saving: " + "; ".join(labels) + "."
            message_is_error = True
        else:
            chosen = get_scenario(activity_key, scenario_id)
            content_text = _serialize_activity_submission(
                activity_key,
                activity_fields,
                field_values,
                bonus_note,
                scenario_title=chosen.title if chosen else "",
            )
            participant_row = create_or_update_participant(
                code,
                display_name,
                participant_key=(participant.get("participant_key") if participant else None),
                login_email=_active_login_email(),
            )
            participant = participant_row
            participant_name = str(participant_row.get("display_name", display_name)).strip() or display_name
            stored_values = dict(field_values)
            stored_values["bonus_note"] = bonus_note
            if scenario_id:
                stored_values["scenario_id"] = scenario_id
            save_submission(
                code,
                activity_key,
                participant_name,
                content_text,
                participant_key=str(participant_row.get("participant_key", "")),
                anonymity_mode=anonymity_mode,
                field_values=stored_values,
                is_draft=is_draft,
            )
            idx_now = ACTIVITY_ORDER.index(activity_key)
            next_now = ACTIVITY_ORDER[idx_now + 1] if idx_now < len(ACTIVITY_ORDER) - 1 else None
            if submit_action == "save_next" and next_now:
                target = url_for(
                    "workshop.workshop_activity",
                    session_code=code,
                    activity_key=next_now,
                    saved=activity_key,
                )
            else:
                target = url_for(
                    "workshop.workshop_activity",
                    session_code=code,
                    activity_key=activity_key,
                    **{"drafted" if is_draft else "saved": activity_key},
                    _anchor="activity-status",
                )
            # Post/Redirect/Get: a refresh must not resubmit the activity.
            resp = make_response(redirect(target))
            return _set_participant_cookie(resp, str(participant_row.get("participant_key", "")))

    saved_key = (request.args.get("saved") or "").strip()
    drafted_key = (request.args.get("drafted") or "").strip()
    if saved_key in ACTIVITY_META and not message:
        badge = ACTIVITY_META[saved_key].get("badge", "Workshop Champion")
        message = f"Saved {_activity_title(saved_key)}. Badge unlocked: {badge}."
    elif drafted_key in ACTIVITY_META and not message:
        message = (
            f"Draft saved for {_activity_title(drafted_key)}. "
            "It stays private to you until you save the finished response."
        )

    existing = (
        get_participant_submission(code, str(participant.get("participant_key", "")), activity_key)
        if participant
        else None
    )
    is_draft_state = bool(int((existing or {}).get("is_draft", 0) or 0))

    if request.method == "GET" and existing:
        # Redundant entry (WCAG 3.3.7): give participants their own saved
        # answers back in the right boxes instead of an empty form.
        stored = decode_field_values(existing)
        for field in activity_fields:
            name = str(field.get("name", ""))
            if stored.get(name):
                field_values[name] = stored[name]
        bonus_note = stored.get("bonus_note", "")
        anonymity_mode = bool(int(existing.get("anonymity_mode", 0) or 0))
    elif request.method == "GET" and participant:
        # No saved answer for this activity yet. Carry the participant's most
        # recent anonymity choice forward as the default: someone who opted to
        # share anonymously should not have to re-tick the box on all eleven
        # activities, and forgetting once publishes their name.
        prior = list_submissions_for_participant(code, str(participant.get("participant_key", "")))
        if prior:
            anonymity_mode = bool(int(prior[0].get("anonymity_mode", 0) or 0))

    # Scenario selection. A query parameter wins over the stored choice so a
    # participant can switch briefs; "surprise" picks one deterministically
    # from their own key, which spreads briefs across the room without
    # reshuffling on every page load.
    scenario_bank = scenarios_for(activity_key)
    scenario = None
    if scenario_bank:
        requested = (
            scenario_id if request.method == "POST" else (request.args.get("scenario") or "").strip()
        )
        if requested == "surprise":
            seed = str(participant.get("participant_key", "")) if participant else code
            scenario = pick_scenario(activity_key, seed)
        else:
            stored_choice = decode_field_values(existing).get("scenario_id", "") if existing else ""
            scenario = get_scenario(activity_key, requested) or get_scenario(activity_key, stored_choice)
        scenario_id = scenario.id if scenario else ""

    return_to = _workshop_return_target(code, activity_key=activity_key)

    idx = ACTIVITY_ORDER.index(activity_key)
    prev_key = ACTIVITY_ORDER[idx - 1] if idx > 0 else None
    next_key = ACTIVITY_ORDER[idx + 1] if idx < len(ACTIVITY_ORDER) - 1 else None
    count = count_submissions(code, activity_key=activity_key)

    # The passport reports the individual participant's own progress. Using the
    # session-wide list here made every activity look complete for everyone as
    # soon as any one person in the room submitted.
    own_submissions = (
        list_submissions_for_participant(
            code, str(participant.get("participant_key", "")), include_drafts=False
        )
        if participant
        else []
    )
    by_activity = {key: 0 for key in ACTIVITY_ORDER}
    for submission in own_submissions:
        key = submission.get("activity_key", "")
        if key in by_activity:
            by_activity[key] += 1
    completed_activities = sum(1 for key in ACTIVITY_ORDER if by_activity.get(key, 0) > 0)
    progress_pct = round((completed_activities / len(ACTIVITY_ORDER)) * 100)
    activity_meta = ACTIVITY_META.get(
        activity_key,
        {"title": activity_key, "time": "Varies", "badge": "Workshop Champion"},
    )

    return render_template(
        "workshop/activity.html",
        session_code=code,
        status_prefix=("Not saved" if message_is_error else ("Saved" if message else "")),
        skill_ready=(activity_key == "champion_studio" and _champion_skill_context(code) is not None),
        activity_key=activity_key,
        activity_title=activity_meta.get("title", activity_key),
        activity_time=activity_meta.get("time", "Varies"),
        activity_badge=activity_meta.get("badge", "Workshop Champion"),
        activity_fields=activity_fields,
        field_values=field_values,
        bonus_note=bonus_note,
        scenario_cards=_scenario_cards(activity_key, code, selected_id=scenario_id),
        scenario=_scenario_detail(scenario, code, activity_key=activity_key) if scenario else None,
        scenario_id=scenario_id,
        scenario_surprise_href=(
            url_for(
                "workshop.workshop_activity",
                session_code=code,
                activity_key=activity_key,
                scenario="surprise",
                _anchor="scenario",
            )
            if scenario_bank
            else ""
        ),
        anonymity_mode=anonymity_mode,
        is_draft_state=is_draft_state,
        missing_fields=missing_fields,
        prompt_text=ACTIVITY_PROMPTS[activity_key],
        message=message,
        message_is_error=message_is_error,
        idx=idx,
        total_activities=len(ACTIVITY_ORDER),
        completed_activities=completed_activities,
        progress_pct=progress_pct,
        by_activity=by_activity,
        activity_order=ACTIVITY_ORDER,
        activity_titles=_activity_titles(),
        prev_key=prev_key,
        next_key=next_key,
        count=count,
        gallery_enabled=_gallery_enabled(),
        participant_name=participant_name,
        return_to=return_to,
    )


@workshop_bp.route("/session/<session_code>/launchpad", methods=["GET"])
def workshop_launchpad(session_code: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code = _require_session(session_code)
    session_meta = get_session(code) or {}

    activity_key = (request.args.get("activity") or "").strip()
    if activity_key and activity_key not in ACTIVITY_PROMPTS:
        activity_key = ""
    return_to = _workshop_return_target(code, activity_key=activity_key or ACTIVITY_ORDER[0])

    scenario_cards = []
    for scenario in MAGIC_SCENARIOS:
        action_links = []
        for token in scenario.get("tokens", []):
            if token in WORKSHOP_ACTION_TOKENS:
                label, href = _action_link_for_token(token, code, return_to=return_to)
                action_links.append({"token": token, "label": label, "href": href})
        scenario_cards.append(
            {
                "id": scenario["id"],
                "title": scenario["title"],
                "goal": scenario["goal"],
                "sample_slug": scenario["sample_slug"],
                "sample_name": WORKSHOP_SAMPLE_FILES.get(scenario["sample_slug"], ""),
                "activity_key": scenario["activity_key"],
                "activity_title": _activity_title(str(scenario["activity_key"])),
                "action_links": action_links,
                "workflow_html": _render_tokenized_workflow_text(
                    str(scenario.get("workflow_text", "")), code, return_to=return_to
                ),
            }
        )

    participant = _current_participant(code)
    participant_name = str(participant.get("display_name", "")).strip() if participant else ""

    return render_template(
        "workshop/launchpad.html",
        session_code=code,
        session_title=session_meta.get("title", "GLOW Workshop Session"),
        participant_name=participant_name,
        scenario_cards=scenario_cards,
        activity_key=activity_key,
    )


@workshop_bp.route("/session/<session_code>/samples/<slug>", methods=["GET"])
def workshop_sample_download(session_code: str, slug: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    _require_session(session_code)

    filename = WORKSHOP_SAMPLE_FILES.get((slug or "").strip().lower())
    if not filename:
        abort(404)
    path = _resolve_asset("samples", filename)
    if path is None:
        current_app.logger.error(
            "Workshop sample %r missing; searched roots: %s",
            filename,
            ", ".join(str(r) for r in _asset_roots()),
        )
        abort(404)
    return send_file(str(path), as_attachment=True, download_name=filename)


@workshop_bp.route("/session/<session_code>/me", methods=["GET"])
def workshop_my_content(session_code: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code = _require_session(session_code)

    participant = _current_participant(code)
    if not participant:
        return render_template("workshop/my_content_missing.html", session_code=code), 404

    submissions = _decorate_submissions(
        list_submissions_for_participant(code, str(participant.get("participant_key", "")))
    )
    message, message_is_error = _return_link_message()
    return render_template(
        "workshop/my_content.html",
        session_code=code,
        participant=participant,
        submissions=submissions,
        activity_titles=_activity_titles(),
        status_prefix=("Not sent" if message_is_error else ("Sent" if message else "")),
        return_link_available=email_configured(),
        return_link_ttl_days=return_link_ttl_days(),
        message=message,
        message_is_error=message_is_error,
    )


@workshop_bp.route("/session/<session_code>/me/export/markdown", methods=["GET"])
def workshop_my_export(session_code: str):
    """A participant's own artifacts.

    Session-wide exports are facilitator-only, so this is the route that keeps
    the workshop promise that every participant leaves with their own work.
    """
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code = _require_session(session_code)

    participant = _current_participant(code)
    if not participant:
        return render_template("workshop/my_content_missing.html", session_code=code), 404

    rows = list_submissions_for_participant(code, str(participant.get("participant_key", "")))
    name = str(participant.get("display_name", "Participant")).strip() or "Participant"

    lines = ["# My GLOW workshop artifacts", "", f"Participant: {name}", f"Session code: `{code}`", ""]
    if not rows:
        lines.append("No activity responses saved yet.")
    for row in rows:
        lines.append(f"## {_activity_title(str(row.get('activity_key', '')))}")
        lines.append("")
        lines.append(f"Last updated: {_format_timestamp(str(row.get('updated_at_utc', '')))}")
        lines.append("")
        lines.append("```text")
        lines.append((row.get("content_text") or "").strip())
        lines.append("```")
        lines.append("")

    return Response(
        "\n".join(lines),
        mimetype="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{code}-my-workshop-artifacts.md"'},
    )


def _champion_skill_context(code: str):
    """The participant's Champion Studio answers, enriched by their formula.

    Returns ``(values, trusted_guidance, author)`` or ``None`` when they have
    not saved a finished Champion Studio response yet.
    """
    participant = _current_participant(code)
    if not participant:
        return None
    key = str(participant.get("participant_key", ""))

    studio = get_participant_submission(code, key, "champion_studio")
    if not studio or int(studio.get("is_draft", 0) or 0):
        return None
    values = decode_field_values(studio)
    if not values:
        return None

    # The Accessibility Agent Formula activity supplies the standards the
    # agent must follow, so the two exercises compose into one artifact.
    formula = get_participant_submission(code, key, "agent_formula")
    trusted_guidance = decode_field_values(formula).get("trusted_guidance", "") if formula else ""

    author = str(participant.get("display_name", "Workshop participant")).strip() or "Workshop participant"
    return values, trusted_guidance, author


# ---------------------------------------------------------------------------
# Return links
# ---------------------------------------------------------------------------

_RETURN_LINK_MESSAGES = {
    "sent": ("Check your email. Your return link is on its way.", False),
    "invalid-email": ("Enter an email address in the form name@example.com.", True),
    "unavailable": ("Return links are not available on this server right now.", True),
    "send-failed": ("We could not send that email. Please try again, or ask your facilitator.", True),
}


def _return_link_message() -> tuple[str, bool]:
    """Render the outcome of a return-link request carried in the redirect.

    The request POSTs and redirects rather than rendering in place, so a
    refresh cannot re-send the email. The outcome travels as a short key
    instead of the address itself: an email address must not end up in a
    URL, a bookmark, or a server access log.
    """
    key = (request.args.get("link") or "").strip()
    return _RETURN_LINK_MESSAGES.get(key, ("", False))


def _looks_like_email(value: str) -> bool:
    """A deliberately loose check -- Postmark is the real validator.

    The point is to catch an empty box or an obvious typo before promising
    someone an email that will never arrive, not to police RFC 5322.
    """
    candidate = (value or "").strip()
    if not candidate or len(candidate) > 254 or " " in candidate:
        return False
    local, at, domain = candidate.partition("@")
    return bool(local and at and "." in domain and not domain.startswith(".") and not domain.endswith("."))


@workshop_bp.route("/session/<session_code>/return-link", methods=["POST"])
@limiter.limit("5 per hour")
def workshop_return_link_request(session_code: str):
    """Email this participant a link that restores their identity elsewhere."""
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code = _require_session(session_code)

    participant = _current_participant(code)
    if not participant:
        return render_template("workshop/my_content_missing.html", session_code=code), 404

    def _back(outcome: str):
        return redirect(url_for("workshop.workshop_my_content", session_code=code, link=outcome))

    email = (request.form.get("return_email") or "").strip()
    if not _looks_like_email(email):
        return _back("invalid-email")
    if not email_configured():
        return _back("unavailable")

    key = str(participant.get("participant_key", ""))
    # Remember the address so the end-of-day artifact and the 30-day nudge
    # have somewhere to go. It is never rendered in the gallery, the
    # facilitator dashboard, or any export.
    bind_participant_login(key, email)

    token = create_return_link(code, key)
    link = url_for("workshop.workshop_return", token=token, _external=True)
    session_meta = get_session(code) or {}
    sent, _detail = send_workshop_return_link_email(
        email,
        link=link,
        ttl_days=return_link_ttl_days(),
        session_title=str(session_meta.get("title", "")).strip(),
        participant_name=str(participant.get("display_name", "")).strip(),
    )
    return _back("sent" if sent else "send-failed")


@workshop_bp.route("/return/<token>", methods=["GET"])
def workshop_return(token: str):
    """Spend a return token and re-attach this device to its participant."""
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)

    status, participant = consume_return_link(token)
    if status != "ok" or not participant:
        return (
            render_template("workshop/return_link_invalid.html", status=status),
            403,
        )

    code = str(participant.get("session_code", ""))
    resp = make_response(redirect(url_for("workshop.workshop_my_content", session_code=code)))
    return _set_participant_cookie(resp, str(participant.get("participant_key", "")))


@workshop_bp.route("/session/<session_code>/champion-skill", methods=["GET"])
def workshop_champion_skill(session_code: str):
    """Preview the agent skill compiled from the participant's own workflow."""
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code = _require_session(session_code)
    session_meta = get_session(code) or {}

    context = _champion_skill_context(code)
    if context is None:
        return (
            render_template(
                "workshop/champion_skill_missing.html",
                session_code=code,
            ),
            404,
        )

    values, trusted_guidance, author = context
    event_name = str(session_meta.get("event_name", "")).strip()
    return render_template(
        "workshop/champion_skill.html",
        session_code=code,
        workflow_name=values.get("workflow_name", "").strip() or "Your accessibility workflow",
        skill_markdown=build_skill_markdown(
            values, author=author, event_name=event_name, trusted_guidance=trusted_guidance
        ),
        copy_prompt=build_copy_prompt(values, trusted_guidance=trusted_guidance),
        has_guidance=bool(trusted_guidance.strip()),
    )


@workshop_bp.route("/session/<session_code>/champion-skill.zip", methods=["GET"])
def workshop_champion_skill_download(session_code: str):
    """Download the participant's workflow as an Agent Plugins 1.0 package."""
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code = _require_session(session_code)
    session_meta = get_session(code) or {}

    context = _champion_skill_context(code)
    if context is None:
        abort(404)

    values, trusted_guidance, author = context
    filename, payload = build_skill_zip_bytes(
        values,
        author=author,
        event_name=str(session_meta.get("event_name", "")).strip(),
        trusted_guidance=trusted_guidance,
    )
    return Response(
        payload,
        mimetype="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@workshop_bp.route("/session/<session_code>/gallery", methods=["GET"])
def workshop_gallery(session_code: str):
    if not _workshop_enabled() or not _gallery_enabled():
        abort(404)
    code = _require_session(session_code)

    # Filter and paginate. A full-day session with 25 participants produces
    # hundreds of submissions; rendering them all put several thousand tab
    # stops on a single page.
    activity_filter = (request.args.get("activity") or "").strip()
    if activity_filter and activity_filter not in ACTIVITY_PROMPTS:
        activity_filter = ""

    total = count_submissions(code, activity_key=activity_filter or None)
    total_pages = max(1, (total + GALLERY_PAGE_SIZE - 1) // GALLERY_PAGE_SIZE)
    try:
        page = int((request.args.get("page") or "1").strip())
    except ValueError:
        page = 1
    page = min(max(1, page), total_pages)

    submissions = _decorate_submissions(
        list_submissions(
            code,
            activity_key=activity_filter or None,
            limit=GALLERY_PAGE_SIZE,
            offset=(page - 1) * GALLERY_PAGE_SIZE,
        )
    )
    feedback = list_feedback_for_session(code)
    participant = _current_participant(code)
    reviewer_default = str(participant.get("display_name", "")).strip() if participant else ""

    activity_choices = [
        {"key": key, "title": _activity_title(key), "count": count_submissions(code, activity_key=key)}
        for key in ACTIVITY_ORDER
    ]

    saved_id = (request.args.get("feedback_saved") or "").strip()
    error_id = (request.args.get("feedback_error") or "").strip()
    # Only consume the stashed draft when this render will actually show it.
    # Popping it on any gallery GET meant a redirect that landed on a page
    # without that card destroyed the reviewer's typed answers.
    stashed = session.get(FEEDBACK_DRAFT_SESSION_KEY) or {}
    feedback_draft = {}
    draft_target = int(stashed.get("submission_id", 0)) if stashed else 0
    if draft_target and any(int(row.get("id", 0)) == draft_target for row in submissions):
        feedback_draft = session.pop(FEEDBACK_DRAFT_SESSION_KEY)
    message = ""
    message_is_error = False
    if error_id and feedback_draft:
        message = (
            "That peer feedback was not saved. All four feedback answers are "
            "needed, and a space on its own does not count as an answer. "
            "Your answers are still in the form below."
        )
        message_is_error = True
    elif saved_id:
        message = "Peer feedback saved."
    elif (request.args.get("saved") or "").strip():
        message = "Saved follow-through item."

    return render_template(
        "workshop/gallery.html",
        session_code=code,
        submissions=submissions,
        feedback=feedback,
        peer_review_enabled=_peer_review_enabled(),
        activity_titles=_activity_titles(),
        reviewer_default=reviewer_default,
        feedback_draft=feedback_draft,
        feedback_error_id=draft_target if feedback_draft else None,
        activity_filter=activity_filter,
        activity_choices=activity_choices,
        page=page,
        total_pages=total_pages,
        total=total,
        page_size=GALLERY_PAGE_SIZE,
        first_index=((page - 1) * GALLERY_PAGE_SIZE) + 1 if total else 0,
        last_index=min(page * GALLERY_PAGE_SIZE, total),
        message=message,
        message_is_error=message_is_error,
    )


@workshop_bp.route("/session/<session_code>/follow-through", methods=["GET", "POST"])
def workshop_follow_through(session_code: str):
    if not _workshop_enabled():
        abort(404)
    code = _require_session(session_code)
    session_meta = get_session(code) or {}

    form_values = {
        "item_kind": "action_commitment",
        "item_title": "",
        "owner_name": "Participant",
        "due_date": "",
        "item_details": "",
    }
    participant = _current_participant(code)
    if participant:
        form_values["owner_name"] = str(participant.get("display_name", "Participant")).strip() or "Participant"

    message = ""
    message_is_error = False

    if request.method == "POST":
        form_values["item_kind"] = (request.form.get("item_kind") or "action_commitment").strip() or "action_commitment"
        form_values["item_title"] = (request.form.get("item_title") or "").strip()
        form_values["owner_name"] = (request.form.get("owner_name") or "Participant").strip() or "Participant"
        form_values["due_date"] = (request.form.get("due_date") or "").strip()
        form_values["item_details"] = (request.form.get("item_details") or "").strip()
        return_to = (request.form.get("return_to") or "").strip().lower()
        source_raw = (request.form.get("source_submission_id") or "").strip()
        source_submission_id = int(source_raw) if source_raw.isdigit() else None

        if not form_values["item_title"] or not form_values["item_details"]:
            message = "Please add both a title and details before saving."
            message_is_error = True
        else:
            new_id = save_follow_through_item(
                code,
                form_values["item_kind"],
                form_values["item_title"],
                form_values["item_details"],
                form_values["owner_name"],
                due_date=form_values["due_date"] or None,
                source_submission_id=source_submission_id,
            )
            # Post/Redirect/Get so a refresh cannot silently duplicate the item.
            if return_to == "gallery" and source_submission_id is not None:
                return redirect(
                    url_for(
                        "workshop.workshop_gallery",
                        session_code=code,
                        saved=1,
                        **_gallery_return_args(),
                        _anchor=f"submission-{source_submission_id}",
                    )
                )
            return redirect(
                url_for(
                    "workshop.workshop_follow_through",
                    session_code=code,
                    saved=new_id,
                    _anchor="ft-status",
                )
            )

    if (request.args.get("saved") or "").strip() and not message:
        message = "Saved follow-through item."

    items = list_follow_through_items(code)
    groups = []
    for key, title, empty_text in FOLLOW_THROUGH_GROUPS:
        group_items = []
        for item in items:
            if item.get("kind") != key:
                continue
            row = dict(item)
            row["status_label"] = STATUS_LABELS.get(str(row.get("status", "open")), str(row.get("status", "open")))
            group_items.append(row)
        # Keyed "entries", not "items": Jinja resolves ``group.items`` to the
        # dict's built-in items() method, not this list.
        groups.append({"key": key, "title": title, "entries": group_items, "empty_text": empty_text})

    return render_template(
        "workshop/follow_through.html",
        session_code=code,
        session_title=session_meta.get("title", "GLOW Workshop Session"),
        message=message,
        message_is_error=message_is_error,
        form_values=form_values,
        groups=groups,
    )


@workshop_bp.route("/session/<session_code>/follow-through/export/markdown", methods=["GET"])
def workshop_follow_through_export(session_code: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code = _require_session(session_code)
    if not _is_facilitator(code):
        return _facilitator_unlock_response(code)
    session_meta = get_session(code) or {}

    markdown = export_follow_through_markdown(
        code, session_title=session_meta.get("title", "GLOW Workshop Session")
    )
    return Response(
        markdown,
        mimetype="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{code}-workshop-follow-through.md"'},
    )


@workshop_bp.route("/session/<session_code>/follow-through/<int:item_id>/status", methods=["POST"])
def workshop_follow_through_status(session_code: str, item_id: int):
    if not _workshop_enabled():
        abort(404)
    code = _require_session(session_code)

    status = (request.form.get("status") or "").strip().lower()
    try:
        update_follow_through_status(code, item_id, status)
    except ValueError:
        abort(400)
    return redirect(
        url_for(
            "workshop.workshop_follow_through",
            session_code=code,
            _anchor=f"ft-item-{item_id}",
        )
    )


@workshop_bp.route("/session/<session_code>/submission/<int:submission_id>/feedback", methods=["POST"])
def workshop_peer_feedback(session_code: str, submission_id: int):
    if not _workshop_enabled() or not _peer_review_enabled():
        abort(404)
    code = _require_session(session_code)

    reviewer = (request.form.get("reviewer_display_name") or "Peer Reviewer").strip() or "Peer Reviewer"
    strength = (request.form.get("strength") or "").strip()
    risk_or_gap = (request.form.get("risk_or_gap") or "").strip()
    safeguard = (request.form.get("recommended_safeguard") or "").strip()
    reuse = (request.form.get("reuse_suggestion") or "").strip()

    if not (strength and risk_or_gap and safeguard and reuse):
        # Previously the failure path and the success path were byte-identical
        # bare redirects, so four textareas were silently discarded with no
        # message at all. Carry the typed answers across the redirect and put
        # them back in the same card, rather than making the reviewer retype.
        session[FEEDBACK_DRAFT_SESSION_KEY] = {
            "submission_id": int(submission_id),
            "reviewer_display_name": reviewer,
            "strength": strength,
            "risk_or_gap": risk_or_gap,
            "recommended_safeguard": safeguard,
            "reuse_suggestion": reuse,
        }
        return redirect(
            url_for(
                "workshop.workshop_gallery",
                session_code=code,
                feedback_error=submission_id,
                **_gallery_return_args(),
                _anchor=f"feedback-err-{submission_id}",
            )
        )

    add_feedback(code, submission_id, reviewer, strength, risk_or_gap, safeguard, reuse)
    return redirect(
        url_for(
            "workshop.workshop_gallery",
            session_code=code,
            feedback_saved=submission_id,
            **_gallery_return_args(),
            _anchor=f"submission-{submission_id}",
        )
    )


# ---------------------------------------------------------------------------
# Session-wide exports (facilitator only)
# ---------------------------------------------------------------------------

def _facilitator_export(session_code: str):
    """Shared guard for the session-wide exports."""
    code = _require_session(session_code)
    if not _is_facilitator(code):
        return code, _facilitator_unlock_response(code)
    return code, None


@workshop_bp.route("/session/<session_code>/export/markdown", methods=["GET"])
def workshop_export_markdown(session_code: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code, denied = _facilitator_export(session_code)
    if denied is not None:
        return denied
    session_meta = get_session(code) or {}
    markdown = export_session_markdown(code, session_title=session_meta.get("title", "GLOW Workshop Session"))
    return Response(
        markdown,
        mimetype="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{code}-workshop-artifacts.md"'},
    )


@workshop_bp.route("/session/<session_code>/export/json", methods=["GET"])
def workshop_export_json(session_code: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code, denied = _facilitator_export(session_code)
    if denied is not None:
        return denied
    session_meta = get_session(code) or {}
    payload = export_session_json(code, session_title=session_meta.get("title", "GLOW Workshop Session"))
    return Response(
        payload,
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{code}-workshop-artifacts.json"'},
    )


@workshop_bp.route("/session/<session_code>/export/html", methods=["GET"])
def workshop_export_html(session_code: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code, denied = _facilitator_export(session_code)
    if denied is not None:
        return denied
    session_meta = get_session(code) or {}
    html = export_session_html(code, session_title=session_meta.get("title", "GLOW Workshop Session"))
    return Response(
        html,
        mimetype="text/html",
        headers={"Content-Disposition": f'attachment; filename="{code}-workshop-artifacts.html"'},
    )


@workshop_bp.route("/session/<session_code>/export/docx", methods=["GET"])
def workshop_export_docx(session_code: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code, denied = _facilitator_export(session_code)
    if denied is not None:
        return denied
    session_meta = get_session(code) or {}
    try:
        content = export_session_docx_bytes(code, session_title=session_meta.get("title", "GLOW Workshop Session"))
    except ImportError:
        return Response("DOCX export unavailable: python-docx is not installed.", status=503, mimetype="text/plain")
    return Response(
        content,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{code}-workshop-artifacts.docx"'},
    )


# ---------------------------------------------------------------------------
# Facilitator surfaces
# ---------------------------------------------------------------------------

@workshop_bp.route("/session/<session_code>/facilitator", methods=["GET"])
def workshop_facilitator(session_code: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code = _require_session(session_code)
    if not _is_facilitator(code):
        return _facilitator_unlock_response(code)
    session_meta = get_session(code) or {}

    submissions = _decorate_submissions(list_submissions(code))
    feedback = list_feedback_for_session(code)
    by_activity = {key: 0 for key in ACTIVITY_ORDER}
    anonymous_count = 0
    covered_feedback = 0
    for s in submissions:
        activity = s.get("activity_key", "")
        if activity in by_activity:
            by_activity[activity] += 1
        if int(s.get("anonymity_mode", 0)):
            anonymous_count += 1
        if feedback.get(int(s.get("id", 0))):
            covered_feedback += 1

    activity_rows = [{"title": _activity_title(key), "count": by_activity[key]} for key in ACTIVITY_ORDER]

    return render_template(
        "workshop/facilitator.html",
        session_code=code,
        session_title=session_meta.get("title", "GLOW Workshop Session"),
        activity_rows=activity_rows,
        activity_titles=_activity_titles(),
        total_submissions=len(submissions),
        anonymous_count=anonymous_count,
        covered_feedback=covered_feedback,
        feedback_coverage_pct=(round((covered_feedback / len(submissions)) * 100) if submissions else 0),
        recent_submissions=submissions[:12],
        feedback=feedback,
    )


@workshop_bp.route("/session/<session_code>/facilitator/unlock", methods=["POST"])
def workshop_facilitator_unlock(session_code: str):
    if not _workshop_enabled() or not _lab_hub_enabled():
        abort(404)
    code = _require_session(session_code)

    supplied = (request.form.get("facilitator_key") or "").strip()
    expected = _expected_facilitator_key(code)
    if expected and supplied and hmac.compare_digest(supplied, expected):
        session[FACILITATOR_SESSION_PREFIX + code] = expected
        return redirect(url_for("workshop.workshop_facilitator", session_code=code))
    return _facilitator_unlock_response(code, error="That facilitator key was not recognized for this session.")


# ---------------------------------------------------------------------------
# Guidance surfaces
# ---------------------------------------------------------------------------

@workshop_bp.route("/session/<session_code>/coach", methods=["GET"])
def workshop_coach(session_code: str):
    if not _workshop_enabled():
        abort(404)
    code = _require_session(session_code)
    return render_template("workshop/coach.html", session_code=code)


@workshop_bp.route("/session/<session_code>/review", methods=["GET"])
def workshop_review(session_code: str):
    if not _workshop_enabled():
        abort(404)
    code = _require_session(session_code)
    return render_template("workshop/review.html", session_code=code)


@workshop_bp.route("/session/<session_code>/share", methods=["GET"])
def workshop_share(session_code: str):
    if not _workshop_enabled():
        abort(404)
    code = _require_session(session_code)
    return render_template("workshop/share.html", session_code=code)


# ---------------------------------------------------------------------------
# Blank worksheet pack
# ---------------------------------------------------------------------------

def _worksheet_pack() -> list[Worksheet]:
    """Every activity as a blank worksheet, built from the live definitions.

    Generated rather than written out, so a worksheet cannot drift away from
    the form a participant sees on screen.
    """
    sheets: list[Worksheet] = []
    for key in ACTIVITY_ORDER:
        meta = ACTIVITY_META.get(key, {})
        fields = ACTIVITY_FIELDS.get(
            key, [{"name": "response", "label": "Response", "rows": 6}]
        )
        sheets.append(
            Worksheet(
                key=key,
                title=str(meta.get("title", key)),
                time=str(meta.get("time", "Varies")),
                badge=str(meta.get("badge", "Workshop Champion")),
                prompt=ACTIVITY_PROMPTS.get(key, ""),
                fields=tuple(
                    WorksheetField(
                        label=str(field.get("label", field.get("name", "Response"))),
                        rows=int(field.get("rows", 3) or 3),
                    )
                    for field in fields
                ),
                scenarios=tuple(
                    (scenario.title, scenario.sector) for scenario in scenarios_for(key)
                ),
            )
        )
    return sheets


@workshop_bp.route("/worksheets.html", methods=["GET"])
def workshop_worksheets_html():
    """The printable pack, for a table with no laptops on it.

    Sent as a download rather than rendered in the app so it carries its own
    large-print styles -- the site CSP drops inline styles, and this document
    has to work when opened from a USB stick with no network at all.
    """
    if not _workshop_enabled():
        abort(404)
    html = build_worksheet_html(_worksheet_pack())
    return Response(
        html,
        mimetype="text/html",
        headers={
            "Content-Disposition": 'attachment; filename="glow-workshop-worksheets.html"'
        },
    )


@workshop_bp.route("/worksheets.docx", methods=["GET"])
def workshop_worksheets_docx():
    """The same pack as Word, in ACB large print."""
    if not _workshop_enabled():
        abort(404)
    try:
        payload = build_worksheet_docx_bytes(_worksheet_pack())
    except Exception:
        current_app.logger.exception("Worksheet DOCX generation failed")
        abort(503)
    return Response(
        payload,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": 'attachment; filename="glow-workshop-worksheets.docx"'
        },
    )


@workshop_bp.route("/guide", methods=["GET"])
def workshop_guide():
    if not _workshop_enabled():
        abort(404)
    return render_template("workshop/guide.html")


@workshop_bp.route("/exercises", methods=["GET"])
def workshop_exercises():
    if not _workshop_enabled():
        abort(404)
    return render_template("workshop/exercises.html", exercises=EXERCISE_PACK)


@workshop_bp.route("/utilization", methods=["GET"])
def workshop_utilization():
    if not _workshop_enabled():
        abort(404)
    return render_template("workshop/utilization.html")


@workshop_bp.route("/resources/<slug>", methods=["GET"])
def workshop_resource_download(slug: str):
    if not _workshop_enabled():
        abort(404)
    filename = RESOURCE_FILES.get((slug or "").strip().lower())
    if not filename:
        abort(404)

    path = _resolve_asset("docs", filename)
    if path is None:
        current_app.logger.error(
            "Workshop resource %r missing; searched roots: %s",
            filename,
            ", ".join(str(r) for r in _asset_roots()),
        )
        abort(404)

    return send_file(
        str(path),
        mimetype="text/markdown",
        as_attachment=True,
        download_name=filename,
    )
