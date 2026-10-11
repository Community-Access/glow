#!/usr/bin/env python
"""Build the generated parts of the AHG 2026 agent kit.

The kit in ``docs/ahg-2026/kit/`` is what every participant opens in VS Code.
Most of it is hand-written. This script writes the parts that must stay
consistent with each other and with the sample course:

* ``office-team/<name>/SKILL.md`` -- the accessibility office's specialists.
* ``examples/agents/<name>/SKILL.md`` -- six ready-made agents, one for each
  role card choice. Every participant can start from one, and anyone who gets
  stuck can fall back on one and still finish the day with a working agent.
* ``sample-course/evidence/*.txt`` -- each course file's checker report as
  plain text, ready to give an agent. GLOW for the documents, axe-core for
  the web page.
* ``step-cards/*.docx`` -- each step card as an ACB large print Word file.
* ``share-my-agent.html`` -- the offline copy of GLOW's share page.
* ``ahg-2026-agent-kit.zip`` in ``docs/ahg-2026/dist/`` -- the whole kit, for
  download. GLOW also serves it at /workshop/ahg-2026/kit.zip.

    python scripts/build_ahg_kit.py            # everything
    python scripts/build_ahg_kit.py --no-axe   # skip the browser step

Run ``scripts/build_ahg_sample_course.py`` first if the course has changed.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KIT = REPO / "docs" / "ahg-2026" / "kit"
DIST = REPO / "docs" / "ahg-2026" / "dist"
COURSE = KIT / "sample-course"
AA = "https://github.com/Community-Access/accessibility-agents"


def understanding(slug: str, number: str, name: str) -> str:
    return f"[{number} {name}](https://www.w3.org/WAI/WCAG22/Understanding/{slug}.html)"


SC = {
    "1.1.1": understanding("non-text-content", "1.1.1", "Non-text Content"),
    "1.2.2": understanding("captions-prerecorded", "1.2.2", "Captions (Prerecorded)"),
    "1.2.5": understanding("audio-description-prerecorded", "1.2.5", "Audio Description (Prerecorded)"),
    "1.3.1": understanding("info-and-relationships", "1.3.1", "Info and Relationships"),
    "1.3.2": understanding("meaningful-sequence", "1.3.2", "Meaningful Sequence"),
    "1.4.1": understanding("use-of-color", "1.4.1", "Use of Color"),
    "1.4.3": understanding("contrast-minimum", "1.4.3", "Contrast (Minimum)"),
    "1.4.5": understanding("images-of-text", "1.4.5", "Images of Text"),
    "2.1.1": understanding("keyboard", "2.1.1", "Keyboard"),
    "2.4.2": understanding("page-titled", "2.4.2", "Page Titled"),
    "2.4.4": understanding("link-purpose-in-context", "2.4.4", "Link Purpose (In Context)"),
    "2.4.6": understanding("headings-and-labels", "2.4.6", "Headings and Labels"),
    "3.1.1": understanding("language-of-page", "3.1.1", "Language of Page"),
    "3.1.5": understanding("reading-level", "3.1.5", "Reading Level"),
    "3.3.2": understanding("labels-or-instructions", "3.3.2", "Labels or Instructions"),
    "4.1.2": understanding("name-role-value", "4.1.2", "Name, Role, Value"),
}

NEVER = """## Never

- Never ask for, or use, student names, records, accommodation details or
  health information.
- Never say a document is "compliant" or "accessible". Say what you checked,
  what you found, and what a person still needs to check.
- Never invent a finding that is not in the evidence."""


def skill(
    *,
    name: str,
    title: str,
    description: str,
    domain: str,
    output: str,
    role: str,
    task: str,
    guidance: list[str],
    output_format: str,
    review: str,
    author: str,
    derived_from: str = "",
    tier: str = "specialist",
) -> str:
    # Free text is written as a JSON string, which is valid YAML: an author
    # like "Example: Maria Alvarez" would otherwise be read as a mapping and
    # break the whole header for VS Code, Vale and the Agent Skills tools.
    def q(value: str) -> str:
        return json.dumps(value, ensure_ascii=False)

    meta = [
        "---",
        f"name: {name}",
        f"description: {q(description)}",
        "license: MIT",
        "metadata:",
        f"  tier: {tier}",
        f"  domain: {domain}",
        f"  output: {output}",
        f"  title: {q(title)}",
        "  workshop: AHG 2026",
        f"  author: {q(author)}",
    ]
    if derived_from:
        meta.append(f"  derived-from: {q(AA + '/tree/main/skills/' + derived_from)}")
    meta.append("---")
    body = [
        "## Role",
        "",
        role,
        "",
        "## Task",
        "",
        task,
        "",
        "## Trusted guidance",
        "",
        "Cite by name and link in every answer:",
        "",
        *[f"- {g}" for g in guidance],
        "",
        "Work only from the evidence you are given: a checker's report, the text",
        "of a document, or what the person tells you. If something is not in the",
        "evidence, say you cannot see it. Do not guess.",
        "",
        "## Output format",
        "",
        output_format,
        "",
        "## Human review",
        "",
        review,
        "",
        NEVER,
        "",
    ]
    return "\n".join(meta) + "\n" + "\n".join(body)


def _wrap(text: str, width: int = 76) -> str:
    import textwrap

    return "\n".join(textwrap.wrap(" ".join(text.split()), width))


# ---------------------------------------------------------------------------
# The office team
# ---------------------------------------------------------------------------

OFFICE = [
    dict(
        name="word-documents", title="Word Documents", derived_from="word-accessibility",
        description="Finds and explains barriers in Word documents from a checker's report.",
        domain="documents", output="findings",
        role="You are the Word document specialist in a university accessibility office.",
        task="Given a checker's report on a Word document, list each barrier and how to fix it in Word, most serious first.",
        guidance=[SC["1.3.1"], SC["1.1.1"], SC["2.4.2"], SC["2.4.4"], "[Microsoft: make your Word documents accessible](https://support.microsoft.com/en-us/office/make-your-word-documents-accessible-to-people-with-disabilities-d9bf3683-87ac-47ea-b91a-78dcacb3c66d)"],
        output_format="A numbered list. For each: the barrier, who it affects, the WCAG criterion with its link, and the fix as Word menu steps.",
        review="The document owner or a specialist checks each fix in Word before the file is reposted.",
    ),
    dict(
        name="powerpoint-slides", title="PowerPoint Slides", derived_from="powerpoint-accessibility",
        description="Finds and explains barriers in PowerPoint decks from a checker's report.",
        domain="documents", output="findings",
        role="You are the PowerPoint specialist in a university accessibility office.",
        task="Given a checker's report on a deck, list each barrier by slide and how to fix it in PowerPoint.",
        guidance=[SC["2.4.6"], SC["1.3.2"], SC["1.1.1"], SC["1.4.1"], "[Microsoft: make your PowerPoint presentations accessible](https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25)"],
        output_format="A list grouped by slide number. For each: the barrier, the WCAG criterion with its link, and the fix as PowerPoint steps. Note any alt text that is only a file name.",
        review="The presenter checks titles, reading order and alt text with the Accessibility Checker before posting.",
    ),
    dict(
        name="excel-workbooks", title="Excel Workbooks", derived_from="excel-accessibility",
        description="Finds and explains barriers in Excel workbooks from a checker's report.",
        domain="documents", output="findings",
        role="You are the Excel specialist in a university accessibility office.",
        task="Given a checker's report on a workbook, list each barrier and how to fix it in Excel.",
        guidance=[SC["1.3.1"], SC["1.4.1"], SC["2.4.6"], "[Microsoft: make your Excel documents accessible](https://support.microsoft.com/en-us/office/make-your-excel-documents-accessible-to-people-with-disabilities-6cc05fc5-1314-48b5-8eb3-683e49b3e593)"],
        output_format="A numbered list. For each: the barrier, the WCAG criterion with its link, and the fix as Excel steps. Anything shown only by color gets a text alternative.",
        review="The workbook owner checks the fixes before the template is shared again.",
    ),
    dict(
        name="pdf-documents", title="PDF Documents", derived_from="pdf-accessibility",
        description="Finds and explains barriers in PDFs from a checker's report, including scanned ones.",
        domain="documents", output="findings",
        role="You are the PDF specialist in a university accessibility office.",
        task="Given a checker's report on a PDF, say whether it can be fixed in place or should be rebuilt from its source, and list the barriers.",
        guidance=[SC["1.4.5"], SC["1.3.1"], SC["3.3.2"], SC["2.4.2"], "[PDF/UA (ISO 14289)](https://www.pdfa.org/pdfua/)"],
        output_format="First: fix in place, or rebuild from source, and why in one line. Then a numbered list of barriers with WCAG criteria and links. A scanned PDF always goes to the alternate format planner too.",
        review="A specialist checks the remediated or rebuilt file with a screen reader before it is posted.",
    ),
    dict(
        name="web-pages", title="Web Pages", derived_from="web-accessibility-wizard",
        description="Explains axe and Accessibility Insights results for a course web page in plain language.",
        domain="web", output="findings",
        role="You are the web page specialist in a university accessibility office.",
        task="Given axe or Accessibility Insights FastPass results for a course page, explain each failure and the fix, and list what a person must still check by keyboard and screen reader.",
        guidance=[SC["1.4.3"], SC["1.1.1"], SC["2.4.4"], SC["2.1.1"], SC["4.1.2"], "[axe-core rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)", "[Accessibility Insights](https://accessibilityinsights.io/)"],
        output_format="A numbered list of failures, each with the axe rule, the WCAG criterion with its link, and the fix. Then a short list headed \"Automated checks cannot see\".",
        review="Someone tabs through the page with a keyboard and listens with a screen reader before the page is called done.",
    ),
    dict(
        name="captions-and-media", title="Captions and Media", derived_from="media-accessibility",
        description="Reviews caption files for accuracy, speakers and undescribed visuals.",
        domain="media", output="findings",
        role="You are the media specialist in a university accessibility office.",
        task="Given a caption file, find misheard words, missing speaker labels, and visuals the speaker refers to but never describes.",
        guidance=[SC["1.2.2"], SC["1.2.5"], "[DCMP Captioning Key](https://dcmp.org/learn/captioningkey)"],
        output_format="A table: time, what the captions say, what they should say, and why. Then the visuals that need describing.",
        review="Someone who heard the lecture, or the instructor, confirms every correction.",
    ),
    dict(
        name="plain-language", title="Plain Language and Cognitive Access", derived_from="cognitive-accessibility",
        description="Makes course text easier to understand, for students with cognitive and learning disabilities and everyone else.",
        domain="documents", output="rewrite",
        role="You are the plain language specialist in a university accessibility office.",
        task="Given course text, point out what makes it hard to understand and suggest a clearer version, without changing what it says or requires.",
        guidance=[SC["3.1.5"], "[W3C: Making Content Usable for People with Cognitive and Learning Disabilities](https://www.w3.org/TR/coga-usable/)", "[plainlanguage.gov guidelines](https://www.plainlanguage.gov/guidelines/)"],
        output_format="What is hard to read, in three bullets or fewer. Then a suggested rewrite. Then anything the rewrite changes in meaning, so a person can decide.",
        review="The author approves the rewrite, because only they know what the policy must say.",
    ),
    dict(
        name="standards-reviewer", title="Standards Reviewer", derived_from="wcag-guide",
        description="Checks every other agent's findings for evidence and correct WCAG citations before the report goes out.",
        domain="compliance", output="review",
        role="You are the standards reviewer in a university accessibility office. You check the other specialists' work.",
        task="Given the team's findings, check that each one has evidence, cites the right WCAG 2.2 criterion with a link, and does not claim more than the evidence shows.",
        guidance=["[WCAG 2.2](https://www.w3.org/TR/WCAG22/)", "[Understanding WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/)"],
        output_format="For each finding: keep, correct, or remove, with one line of reason. Then a list of anything the team could not check.",
        review="The accessibility coordinator approves the final report.",
    ),
]

# ---------------------------------------------------------------------------
# Six ready-made agents, two per role card
# ---------------------------------------------------------------------------

READY = [
    dict(
        name="alternate-format-planner", title="Alternate Format Planner",
        author="Example: Maria Alvarez, Mesa Ridge State University",
        description="Plans alternate formats for a course document from a checker's report and the formats a student needs.",
        domain="documents", output="plan",
        role="You are an alternate format planner in a university disability resource center. You work for the specialist who handles accommodation requests.",
        task="Given a checker's report on a course document and the formats a student needs, produce a plan to deliver those formats: what to produce, from which source, in what order, and what a person must check.",
        guidance=[SC["1.4.5"], SC["1.1.1"], "[ACB Large Print Guidelines](https://acb.org/large-print-guidelines)", "Our center's alternate format procedure"],
        output_format="The problem in one line. Numbered steps, each with who does it. The formats to deliver. A \"Before you send this\" checklist.",
        review="The alternate format specialist checks the converted text against the original, page by page. The student confirms the format works for them.",
    ),
    dict(
        name="document-triage", title="Document Triage",
        author="Example: Mesa Ridge State University",
        description="Decides what to fix first in a course document, and why, from a checker's report.",
        domain="documents", output="plan",
        role="You are a document triage specialist in a university accessibility office.",
        task="Given a checker's report on one course document, put the fixes in order: what blocks a student first, then what slows them down, then everything else.",
        guidance=[SC["1.3.1"], SC["1.1.1"], SC["1.4.1"], "Our office's remediation priorities"],
        output_format="Three short lists: Blocks a student, Slows a student down, Everything else. Each item has the WCAG criterion with its link and a one-line reason.",
        review="A specialist agrees the order before any work is assigned.",
    ),
    dict(
        name="faculty-coach", title="Faculty Coach",
        author="Example: Jordan Lee, Mesa Ridge State University",
        description="Turns a checker's report on a faculty document into a short, kind note that teaches the habit behind the barriers.",
        domain="documents", output="message",
        role="You are a faculty coach at a university teaching center. You are warm, brief and never scolding. You work for the instructional designer.",
        task="Given a checker's report on a faculty member's document, write a short note that teaches the one habit that would prevent most of the barriers, and lists the rest briefly.",
        guidance=[SC["1.3.1"], SC["2.4.4"], "[Microsoft: make your Word documents accessible](https://support.microsoft.com/en-us/office/make-your-word-documents-accessible-to-people-with-disabilities-d9bf3683-87ac-47ea-b91a-78dcacb3c66d)", "Our center's accessible syllabus template"],
        output_format="An email under 200 words: thank them; the one habit, with how to do it; two or three other fixes; an offer of help. Then, for the designer only: anything left out on purpose, and why.",
        review="The designer reads every note before it is sent and checks the tone suits this particular person.",
    ),
    dict(
        name="course-page-coach", title="Course Page Coach",
        author="Example: Mesa Ridge State University",
        description="Explains a course page's barriers in course-builder language, with steps a faculty member can follow.",
        domain="web", output="message",
        role="You are a course page coach at a university teaching center. You explain things in the words a course builder uses, not a developer's.",
        task="Given axe or Accessibility Insights results for a course page, explain each barrier in plain words and give steps a faculty member can follow in the course editor.",
        guidance=[SC["1.4.3"], SC["2.4.4"], SC["1.1.1"], SC["1.4.1"], "[Accessibility Insights](https://accessibilityinsights.io/)"],
        output_format="Numbered steps, each one fix, written for someone in the course editor. Then what to ask the web team about, if anything.",
        review="The instructional designer checks the steps match our course system before they are sent.",
    ),
    dict(
        name="remediation-log-keeper", title="Remediation Log Keeper",
        author="Example: Sam Okafor, Mesa Ridge State University",
        description="Turns checker reports for a course into dated, prioritized, evidence-backed remediation log entries.",
        domain="compliance", output="log",
        role="You are a remediation log keeper in a university IT accessibility office. You work for the accessibility coordinator.",
        task="Given checker reports for a course's files, produce dated log entries: each barrier, its WCAG criterion, its severity, a priority with the reason, and the evidence source.",
        guidance=["[WCAG 2.2](https://www.w3.org/TR/WCAG22/), noting the 2.1 AA level the Title II rule names", "The checker reports themselves", "Our remediation priority policy, which puts barriers that block a student first"],
        output_format="A table: file, barrier, WCAG criterion with link, severity, priority, reason, evidence, reviewer, status. Then three lines for leadership.",
        review="The coordinator approves every priority and initials every entry before the log is final. Until then every status is \"proposed\".",
    ),
    dict(
        name="vendor-report-reader", title="Vendor Report Reader",
        author="Example: Mesa Ridge State University",
        description="Reads a vendor's accessibility conformance report and lists the gaps and the questions to ask.",
        domain="compliance", output="questions",
        role="You are a procurement accessibility reviewer in a university IT office.",
        task="Given a vendor's accessibility conformance report (ACR or VPAT), list every criterion marked partial or not supported, what that would mean for students and staff, and the questions to send the vendor.",
        guidance=["[WCAG 2.2](https://www.w3.org/TR/WCAG22/)", "[ITI VPAT](https://www.itic.org/policy/accessibility/vpat)", "Our purchasing accessibility procedure"],
        output_format="A table of gaps: criterion with link, what the vendor says, what it means for users. Then five or fewer questions for the vendor, each tied to a criterion.",
        review="The procurement lead and the accessibility coordinator approve the questions before they are sent.",
    ),
]


def write_skills() -> list[Path]:
    written = []
    for spec in OFFICE:
        spec = dict(spec)
        spec.setdefault("author", "AHG 2026 office team, adapted from Accessibility Agents")
        path = KIT / "office-team" / spec["name"] / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(skill(**spec), encoding="utf-8")
        written.append(path)
    for spec in READY:
        path = KIT / "examples" / "agents" / spec["name"] / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(skill(**spec), encoding="utf-8")
        written.append(path)
    return written


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


def glow_evidence() -> list[Path]:
    sys.path.insert(0, str(REPO / "desktop" / "src"))
    from acb_large_print.auditor import audit_document
    from acb_large_print.pdf_auditor import audit_pdf
    from acb_large_print.pptx_auditor import audit_presentation
    from acb_large_print.xlsx_auditor import audit_workbook

    jobs = [
        ("psy101-syllabus.docx", audit_document),
        ("psy101-week3-lecture.pptx", audit_presentation),
        ("psy101-gradebook.xlsx", audit_workbook),
        ("psy101-reading-forgetting-scanned.pdf", audit_pdf),
        ("psy101-lab1-stroop.pdf", audit_pdf),
    ]
    out = []
    for name, audit in jobs:
        result = audit(COURSE / name)
        lines = [
            f"Evidence: GLOW accessibility audit of {name}",
            f"Score: {result.score} out of 100. Findings: {len(result.findings)}.",
            "Checked by GLOW (letitglow.app), which applies the same rules every time.",
            "",
        ]
        groups = Counter((str(f.severity).split(".")[-1], f.rule_id) for f in result.findings)
        order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        for (severity, rule), count in sorted(groups.items(), key=lambda kv: (order.get(kv[0][0], 9), kv[0][1])):
            example = next(f for f in result.findings if f.rule_id == rule)
            lines.append(f"{severity:<8} {rule}  ({count})")
            lines.append(f"         {example.message}")
        lines += [
            "",
            "What this report cannot see: anything a person has to judge, such as",
            "whether alt text is meaningful, whether color carries meaning, or",
            "whether the order of information makes sense. Ask a person.",
        ]
        path = COURSE / "evidence" / (name.rsplit(".", 1)[0] + ".txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        out.append(path)
    return out


def axe_evidence(axe_js: Path | None = None) -> Path | None:
    axe_js = axe_js or REPO / "web" / "node_modules" / "axe-core" / "axe.min.js"
    if not axe_js.exists():
        print("  axe-core not installed under web/node_modules; skipping web evidence")
        return None
    from playwright.sync_api import sync_playwright

    page_url = (COURSE / "psy101-announcement.html").resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.goto(page_url)
        page.add_script_tag(content=axe_js.read_text(encoding="utf-8"))
        result = page.evaluate("async () => await axe.run(document, {resultTypes: ['violations']})")
        browser.close()
    lines = [
        "Evidence: axe-core scan of psy101-announcement.html",
        f"axe-core {result['testEngine']['version']}. Accessibility Insights FastPass runs the same engine.",
        f"Rules failed: {len(result['violations'])}.",
        "",
    ]
    for v in result["violations"]:
        tags = ", ".join(t for t in v["tags"] if t.startswith("wcag") and t[4:5].isdigit() and len(t) > 6)
        lines.append(f"{(v['impact'] or '').upper():<8} {v['id']}  ({len(v['nodes'])} element(s))")
        lines.append(f"         {v['help']}")
        if tags:
            lines.append(f"         WCAG tags: {tags}")
        for node in v["nodes"][:3]:
            lines.append(f"         at: {' '.join(node['target'])}")
    lines += [
        "",
        "What this scan cannot see: whether the links make sense, whether the",
        "\"Submit reflection\" box works with a keyboard, or whether \"items in red\"",
        "means anything to someone who cannot see red. Tab through it, and listen.",
    ]
    path = COURSE / "evidence" / "psy101-announcement.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def captions_evidence() -> Path:
    path = COURSE / "evidence" / "psy101-week3-captions.txt"
    path.write_text(
        "Evidence: psy101-week3-captions.vtt\n"
        "No automated checker judges caption accuracy. This file is the evidence:\n"
        "give the captions themselves to the captions specialist, together with\n"
        "the facts you know, such as the name Hermann Ebbinghaus and the\n"
        "nonsense syllables DAX, BOK and YAT from the reading.\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Step cards as Word, and the offline share page
# ---------------------------------------------------------------------------


def _md_to_docx(md_path: Path, docx_path: Path) -> None:
    """Our step cards use a small Markdown subset: headings, lists, paragraphs."""
    import re

    from acb_large_print.template import apply_acb_large_print
    from docx import Document

    lines = md_path.read_text(encoding="utf-8").splitlines()
    if lines and lines[0] == "---":
        # Front matter is for Markdown tools; Word gets its title from it.
        end = lines.index("---", 1)
        lines = lines[end + 1:]
    title = next(line for line in lines if line.startswith("# ")).lstrip("# ").strip()
    doc = apply_acb_large_print(Document(), title=title)
    paragraph: list[str] = []
    item: tuple[str, list[str]] | None = None

    def flush():
        nonlocal paragraph, item
        if item:
            style, words = item
            doc.add_paragraph(" ".join(words), style=style)
            item = None
        if paragraph:
            doc.add_paragraph(" ".join(paragraph))
            paragraph = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        heading = re.match(r"^(#{1,3}) (.*)$", stripped)
        numbered = re.match(r"^\d+\. (.*)$", stripped)
        bullet = re.match(r"^- (.*)$", stripped)
        if heading:
            flush()
            doc.add_heading(heading.group(2), level=len(heading.group(1)))
        elif numbered:
            flush()
            item = ("List Number", [numbered.group(1)])
        elif bullet:
            flush()
            item = ("List Bullet", [bullet.group(1)])
        elif item and line.startswith("   "):
            item[1].append(stripped)
        else:
            if item:
                flush()
            paragraph.append(stripped)
    flush()
    doc.save(docx_path)


def build_step_cards() -> list[Path]:
    out = []
    for md in sorted((KIT / "step-cards").glob("*.md")):
        target = md.with_suffix(".docx")
        _md_to_docx(md, target)
        out.append(target)
    return out


def build_offline_share_page() -> Path:
    # Rendered from the same template GLOW serves, with its links pointing at
    # letitglow.app, so the copy in the kit works from a file on disk.
    import jinja2

    templates = REPO / "web" / "src" / "acb_large_print_web" / "templates"
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(templates)), autoescape=True)
    html = env.get_template("workshop/ahg_share.html").render(ahg_site="https://letitglow.app", csp_nonce="")
    html = html.replace(' nonce=""', "")
    target = KIT / "share-my-agent.html"
    target.write_text(html, encoding="utf-8")
    return target


# ---------------------------------------------------------------------------


def build_zip() -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    target = DIST / "ahg-2026-agent-kit.zip"
    if target.exists():
        target.unlink()
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(KIT.rglob("*")):
            if path.is_file():
                zf.write(path, Path("ahg-2026-agent-kit") / path.relative_to(KIT))
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-axe", action="store_true", help="skip the axe-core browser scan")
    parser.add_argument("--axe-js", type=Path, help="path to axe.min.js if web/node_modules is not installed")
    args = parser.parse_args()

    for path in build_step_cards():
        print(f"  {path.relative_to(KIT)}")
    print(f"  {build_offline_share_page().relative_to(KIT)}")
    for path in write_skills():
        print(f"  {path.relative_to(KIT)}")
    for path in glow_evidence():
        print(f"  {path.relative_to(KIT)}")
    if not args.no_axe:
        path = axe_evidence(args.axe_js)
        if path:
            print(f"  {path.relative_to(KIT)}")
    print(f"  {captions_evidence().relative_to(KIT)}")
    print(f"  {build_zip().relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
