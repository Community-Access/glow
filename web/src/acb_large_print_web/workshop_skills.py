"""Compile a participant's Champion Studio workflow into a portable agent skill.

The workshop teaches a five-part formula:

    Accessibility Agent = Role + Task + Trusted Guidance + Output Format + Human Review

An Agent Plugins 1.0 skill is a directory containing a ``SKILL.md`` file with
YAML frontmatter and a plain-Markdown body. The two are the same object, so a
participant who fills in the Champion Studio in plain language has already
authored a skill without writing any code.

This module does that translation. It produces three renderings of the same
content, matching the workshop's tiered approach to AI:

* :func:`build_copy_prompt` -- Tier 2. Plain text to paste into whatever
  assistant the participant already uses. Needs no install and no API key.
* :func:`build_skill_markdown` -- Tier 3. The ``SKILL.md`` file itself.
* :func:`build_skill_zip_bytes` -- Tier 3. The complete downloadable package.

Nothing here calls an AI model. It is string assembly over answers the
participant has already written, which is what makes it work offline and at
zero cost.
"""

from __future__ import annotations

import re
import zipfile
from io import BytesIO

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")
_MAX_SLUG = 60

# Champion Studio field -> its role in the generated skill.
CHAMPION_FIELDS = (
    "workflow_name",
    "partner_group",
    "responsibility",
    "ai_support",
    "final_output",
    "human_safeguard",
)


def slugify(value: str, *, fallback: str = "accessibility-workflow") -> str:
    """A filename- and identifier-safe form of the participant's workflow name."""
    slug = _SLUG_STRIP.sub("-", (value or "").strip().lower()).strip("-")
    slug = slug[:_MAX_SLUG].strip("-")
    return slug or fallback


def _clean(value: str) -> str:
    """Collapse a textarea answer to a single tidy block."""
    text = (value or "").strip()
    if not text:
        return ""
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(line for line in lines).strip()


def _one_line(value: str) -> str:
    """Flatten an answer for use in YAML frontmatter."""
    return " ".join(_clean(value).split())


def _numbered(value: str) -> list[str]:
    """Split an answer into steps, respecting the participant's own line breaks."""
    text = _clean(value)
    if not text:
        return []
    parts = [p.strip(" -*\t") for p in text.splitlines() if p.strip(" -*\t")]
    return parts or [text]


def _yaml_block_scalar(value: str, indent: str = "  ") -> str:
    """Render text as a YAML block scalar so quoting can never break the file."""
    body = _clean(value) or "(not provided)"
    lines = body.splitlines() or ["(not provided)"]
    return "|-\n" + "\n".join(f"{indent}{line}" for line in lines)


def build_skill_markdown(
    values: dict[str, str],
    *,
    author: str = "Workshop participant",
    event_name: str = "",
    trusted_guidance: str = "",
) -> str:
    """Render the participant's workflow as an Agent Plugins 1.0 ``SKILL.md``.

    ``trusted_guidance`` comes from the participant's Accessibility Agent
    Formula activity when they completed it, so the two exercises compose:
    the formula supplies the standards the agent must follow, and the studio
    supplies the workflow around them.
    """
    name = _one_line(values.get("workflow_name", "")) or "Accessibility workflow"
    slug = slugify(name)
    helps = _one_line(values.get("partner_group", ""))
    responsibility = _clean(values.get("responsibility", ""))
    ai_support = _clean(values.get("ai_support", ""))
    output = _clean(values.get("final_output", ""))
    safeguard = _clean(values.get("human_safeguard", ""))
    guidance = _clean(trusted_guidance)

    # The description is a single sentence-or-two summary. Multi-line answers
    # must not be flattened into a run-on, so only the first stated
    # responsibility is used here; the full list appears in the body below.
    description = helps or f"Supports accessibility work for {name}."
    if description and description[-1] not in ".!?":
        description += "."
    first_responsibility = (_numbered(responsibility) or [""])[0].rstrip(". ")
    if first_responsibility:
        lowered = first_responsibility[0].lower() + first_responsibility[1:]
        description = f"{description} Teaches them to {lowered}."

    origin = "GLOW workshop"
    if event_name:
        origin = f"GLOW workshop at {event_name}"

    lines: list[str] = []
    lines.append("---")
    lines.append(f"name: {slug}")
    lines.append(f"description: {_yaml_block_scalar(description)}")
    lines.append("metadata:")
    lines.append(f"  author: {_one_line(author) or 'Workshop participant'}")
    lines.append(f"  source: {origin}")
    lines.append('  version: "1.0.0"')
    lines.append("---")
    lines.append("")
    lines.append(f"# {name}")
    lines.append("")

    if helps:
        lines.append("## Who this helps")
        lines.append("")
        lines.append(helps)
        lines.append("")

    if responsibility:
        lines.append("## What this teaches")
        lines.append("")
        lines.append(
            "This workflow exists to build the partner's own capability, not to "
            "do the work for them. By the end they should be able to:"
        )
        lines.append("")
        for step in _numbered(responsibility):
            lines.append(f"- {step}")
        lines.append("")

    lines.append("## Workflow")
    lines.append("")
    if ai_support:
        for index, step in enumerate(_numbered(ai_support), start=1):
            lines.append(f"{index}. {step}")
    else:
        lines.append("1. (Describe what the assistant should help with.)")
    lines.append("")

    if guidance:
        lines.append("## Trusted guidance")
        lines.append("")
        lines.append("Follow these sources. Do not substitute general knowledge for them:")
        lines.append("")
        for item in _numbered(guidance):
            lines.append(f"- {item}")
        lines.append("")

    if output:
        lines.append("## Output")
        lines.append("")
        lines.append(output)
        lines.append("")

    # The workshop's human-review field and the Accessibility Agents skill
    # format's "Verification truth" section are the same requirement, so the
    # participant's safeguard lands where the production skills put theirs.
    lines.append("## Verification truth")
    lines.append("")
    lines.append(
        "State plainly what was checked and how. Never describe content as "
        "accessible on the basis of an automated result alone."
    )
    lines.append("")
    lines.append("A human must verify the following before this work is considered done:")
    lines.append("")
    if safeguard:
        for item in _numbered(safeguard):
            lines.append(f"- {item}")
    else:
        lines.append("- (Name the human review step this workflow requires.)")
    lines.append("")
    lines.append(
        "If any of the above has not happened, say so in the response rather "
        "than implying the work is complete."
    )
    lines.append("")

    lines.append("## Do not activate for")
    lines.append("")
    lines.append(
        "Requests outside this workflow's purpose, or any request to decide on "
        "a person's behalf what their accessibility needs are."
    )
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_readme(
    values: dict[str, str],
    *,
    author: str = "Workshop participant",
    event_name: str = "",
) -> str:
    """A plain-language explanation for the participant's colleagues."""
    name = _one_line(values.get("workflow_name", "")) or "Accessibility workflow"
    helps = _one_line(values.get("partner_group", ""))
    safeguard = _clean(values.get("human_safeguard", ""))
    origin = f"the GLOW workshop at {event_name}" if event_name else "a GLOW workshop"

    lines = [
        f"# {name}",
        "",
        f"Designed by {_one_line(author) or 'a workshop participant'} at {origin}.",
        "",
        "## What this is",
        "",
        "This folder holds an *agent skill*: a plain-language description of an",
        "accessibility workflow, written so that an AI assistant can follow it",
        "consistently. There is no code in it. You can read every word of it.",
        "",
    ]
    if helps:
        lines += ["## Who it is for", "", helps, ""]

    lines += [
        "## How to use it",
        "",
        "**If you use an AI assistant in a browser** (ChatGPT, Copilot, Claude,",
        "Gemini): open `SKILL.md`, copy everything below the `---` block, and",
        "paste it in before your request. No installation needed.",
        "",
        "**If you use an agent tool that supports Agent Plugins** (Claude Code,",
        "and similar): drop this folder into your `skills/` directory. The",
        "assistant will pick it up automatically.",
        "",
        "**If you do not use AI at all**: `SKILL.md` still works as a written",
        "procedure. That was the point of designing it in plain language.",
        "",
        "## What must stay true",
        "",
        "This workflow has a human review step built into it, in the",
        "`Verification truth` section of `SKILL.md`. It is not optional and it",
        "should not be edited out:",
        "",
    ]
    if safeguard:
        for item in _numbered(safeguard):
            lines.append(f"- {item}")
    else:
        lines.append("- (No human review step was recorded. Add one before using this.)")

    lines += [
        "",
        "An automated pass is evidence, not proof. Real verification still means",
        "testing with a keyboard and with a screen reader, and asking the people",
        "who rely on the content.",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def build_copy_prompt(
    values: dict[str, str],
    *,
    trusted_guidance: str = "",
) -> str:
    """Tier 2: plain text to paste into whatever assistant the participant has.

    Deliberately free of frontmatter, file paths and tooling references, so it
    works in a chat box on a phone with nothing installed.
    """
    name = _one_line(values.get("workflow_name", "")) or "Accessibility workflow"
    helps = _one_line(values.get("partner_group", ""))
    responsibility = _clean(values.get("responsibility", ""))
    ai_support = _clean(values.get("ai_support", ""))
    output = _clean(values.get("final_output", ""))
    safeguard = _clean(values.get("human_safeguard", ""))
    guidance = _clean(trusted_guidance)

    lines = [f"You are an accessibility assistant supporting this workflow: {name}."]
    if helps:
        lines.append(f"The people you are helping are: {helps}")
    lines.append("")

    lines.append("Your task:")
    for step in _numbered(ai_support) or ["(Describe the task.)"]:
        lines.append(f"- {step}")
    lines.append("")

    if guidance:
        lines.append("Follow this guidance. Do not substitute general knowledge for it:")
        for item in _numbered(guidance):
            lines.append(f"- {item}")
        lines.append("")

    if responsibility:
        lines.append("Teach as you go. The person you are helping should learn to:")
        for item in _numbered(responsibility):
            lines.append(f"- {item}")
        lines.append("")

    if output:
        lines.append("Give me back:")
        lines.append(output)
        lines.append("")

    lines.append("Before you finish, do these things:")
    lines.append("- Say exactly what you checked and what you did not check.")
    lines.append("- Do not call anything accessible based only on an automated result.")
    lines.append("- List what a human still has to verify, specifically:")
    for item in _numbered(safeguard) or ["(Name the human review step.)"]:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append(
        "If you are unsure about something, say so plainly instead of guessing."
    )

    return "\n".join(lines).rstrip() + "\n"


def build_skill_zip_bytes(
    values: dict[str, str],
    *,
    author: str = "Workshop participant",
    event_name: str = "",
    trusted_guidance: str = "",
) -> tuple[str, bytes]:
    """Build the downloadable package. Returns ``(filename, zip_bytes)``."""
    slug = slugify(_one_line(values.get("workflow_name", "")))
    skill = build_skill_markdown(
        values, author=author, event_name=event_name, trusted_guidance=trusted_guidance
    )
    readme = build_readme(values, author=author, event_name=event_name)
    prompt = build_copy_prompt(values, trusted_guidance=trusted_guidance)

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}/SKILL.md", skill)
        zf.writestr(f"{slug}/README.md", readme)
        # The same content as a paste-ready prompt, so the package is useful
        # even to someone with no agent tooling at all.
        zf.writestr(f"{slug}/copy-into-any-assistant.txt", prompt)
    return f"{slug}.zip", buf.getvalue()
