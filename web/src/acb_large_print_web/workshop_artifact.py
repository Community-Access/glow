"""The thing a participant takes home.

Until now the personal export was a serialized transcript: every answer, in
order, under its field label. Useful as a record, and nobody forwards it to
their director on Monday.

This builds the same content as one designed page -- their workflow, who it
helps, the human-review gate they wrote themselves, and their 30-day
commitment -- in a form that can be printed, emailed as an attachment, or
opened offline years later.

It is a standalone document rather than an app page on purpose. It gets
emailed, saved to a desktop, and printed; it cannot depend on the site being
up, on a stylesheet resolving, or on a Content-Security-Policy nonce. So it
carries its own styles, and those styles follow the ACB large-print guidance
the rest of GLOW enforces: Arial, 18pt body, generous leading, flush left,
black on white. An artifact from an accessibility workshop should not need
remediation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape


@dataclass(frozen=True)
class ArtifactSection:
    """One block of the participant's own words."""

    heading: str
    intro: str = ""
    items: tuple[tuple[str, str], ...] = ()
    body: str = ""


@dataclass(frozen=True)
class Artifact:
    participant_name: str
    session_code: str
    event_name: str = ""
    workflow_name: str = ""
    human_review: str = ""
    badges_earned: int = 0
    badges_total: int = 0
    sections: tuple[ArtifactSection, ...] = field(default=())
    generated_on: str = ""


_STYLES = """
    :root { color-scheme: light; }
    body {
      font-family: Arial, Helvetica, sans-serif;
      font-size: 18pt;
      line-height: 1.5;
      letter-spacing: 0.12em;
      word-spacing: 0.16em;
      color: #1a1a1a;
      background: #ffffff;
      text-align: left;
      hyphens: none;
      max-width: 44em;
      margin: 0 auto;
      padding: 1in 0.75in;
    }
    h1 { font-size: 28pt; margin-bottom: 0.25rem; }
    h2 { font-size: 22pt; margin-top: 2.5rem; }
    h3 { font-size: 19pt; margin-bottom: 0.25rem; }
    p, dd, li { margin-top: 0.35rem; }
    .subtitle { font-size: 16pt; }
    dl { margin: 0; }
    dt { font-weight: bold; margin-top: 1.25rem; }
    dd { margin-left: 0; }
    /* The safeguard is the point of the whole workflow, so it is the one
       thing on the page that is visually set apart -- and it says so in
       words as well, never by the border alone. */
    .safeguard {
      border: 4px solid #1a1a1a;
      padding: 1rem;
      margin: 1.5rem 0;
    }
    .footer {
      margin-top: 3rem;
      border-top: 2px solid #1a1a1a;
      padding-top: 1rem;
      font-size: 15pt;
    }
    @media print {
      body { padding: 0.5in; font-size: 14pt; }
      h2 { page-break-after: avoid; }
      .safeguard, section { page-break-inside: avoid; }
      .footer { page-break-before: avoid; }
    }
"""


def artifact_title(artifact: Artifact) -> str:
    name = artifact.workflow_name.strip() or "My accessibility workflow"
    who = artifact.participant_name.strip()
    return f"{name} — {who}" if who else name


def build_artifact_html(artifact: Artifact) -> str:
    """Render the take-home page as a self-contained HTML document."""
    title = artifact_title(artifact)
    where = artifact.event_name.strip()

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(title)}</title>",
        f"<style>{_STYLES}</style>",
        "</head>",
        "<body>",
        f"<h1>{escape(artifact.workflow_name.strip() or 'My accessibility workflow')}</h1>",
        '<p class="subtitle">',
        escape(
            "Designed by "
            + (artifact.participant_name.strip() or "a workshop participant")
            + (f" at {where}" if where else " at a GLOW workshop")
            + (f", {artifact.generated_on}" if artifact.generated_on.strip() else "")
            + "."
        ),
        "</p>",
    ]

    if artifact.human_review.strip():
        parts += [
            '<div class="safeguard">',
            "<h2>Human review, required</h2>",
            "<p>This workflow is not finished until a person has done this:</p>",
            f"<p>{escape(artifact.human_review.strip())}</p>",
            "<p>",
            escape(
                "An automated pass is evidence, not proof. Nothing here should "
                "be described as accessible on the strength of a tool's output "
                "alone."
            ),
            "</p>",
            "</div>",
        ]

    for section in artifact.sections:
        parts.append("<section>")
        parts.append(f"<h2>{escape(section.heading)}</h2>")
        if section.intro.strip():
            parts.append(f"<p>{escape(section.intro.strip())}</p>")
        if section.body.strip():
            for paragraph in section.body.strip().splitlines():
                if paragraph.strip():
                    parts.append(f"<p>{escape(paragraph.strip())}</p>")
        if section.items:
            parts.append("<dl>")
            for label, value in section.items:
                parts.append(f"<dt>{escape(label)}</dt>")
                parts.append(f"<dd>{escape(value) if value.strip() else 'Not answered.'}</dd>")
            parts.append("</dl>")
        parts.append("</section>")

    if artifact.badges_total:
        parts += [
            "<section>",
            "<h2>Progress</h2>",
            f"<p>{artifact.badges_earned} of {artifact.badges_total} workshop "
            "activities completed.</p>",
            "</section>",
        ]

    parts += [
        '<div class="footer">',
        "<p>",
        escape(
            "Written in plain language by the person named above, at a GLOW "
            "workshop. Every word of the workflow is theirs; GLOW only "
            "arranged it."
        ),
        "</p>",
        f"<p>Workshop session: {escape(artifact.session_code)}.</p>",
        "</div>",
        "</body>",
        "</html>",
    ]
    return "\n".join(parts)


def build_artifact_text(artifact: Artifact) -> str:
    """A plain-text rendering, for an email body that does not assume HTML."""
    lines = [artifact_title(artifact), ""]
    if artifact.human_review.strip():
        lines += [
            "HUMAN REVIEW, REQUIRED",
            artifact.human_review.strip(),
            "",
        ]
    for section in artifact.sections:
        lines.append(section.heading.upper())
        if section.intro.strip():
            lines.append(section.intro.strip())
        if section.body.strip():
            lines.append(section.body.strip())
        for label, value in section.items:
            lines.append(f"- {label}: {value.strip() or 'Not answered.'}")
        lines.append("")
    lines.append(f"Workshop session: {artifact.session_code}")
    return "\n".join(lines).rstrip() + "\n"
