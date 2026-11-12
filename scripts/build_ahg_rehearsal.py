#!/usr/bin/env python
"""Build a source-attributed, numbered teacher/student rehearsal in S:\\ahgtest.

Run with the active environment and PYTHONPATH=web\\src;desktop\\src.
Existing output is never overwritten. Use a new destination for a fresh run.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

import ahg_formats as F
import check_ahg_formats as C
from acb_large_print_web import workshop_deck as deck

REPO = F.REPO
DEFAULT_OUT = Path(r"S:\ahgtest")
PATHS = ("ChatGPT", "Desktop", "Web")
CARDS = deck.STEP_CARDS


@dataclass(frozen=True)
class Case:
    id: str
    steps: str
    expected: str
    paths: tuple[str, ...]
    section: str


def cases_from_plan(text: str) -> list[Case]:
    """Keep every test row, without importing historical Pass results."""
    plan = text.split("## Part 2: Test plan", 1)[1].split("### 2.14 Defect log", 1)[0]
    cases = []
    headers: list[str] = []
    section = ""
    for line in plan.splitlines():
        if line.startswith("#"):
            section = line.lstrip("# ").strip()
        if not line.startswith("|"):
            headers = []
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if cells[0] == "ID":
            headers = cells
        elif headers and re.fullmatch(r"[A-Za-z]+-\d+", cells[0]):
            row = dict(zip(headers, cells))
            paths = tuple(p for p in PATHS if p in row and not row[p].lower().startswith("n/a"))
            for prefix, path in (("SetupB-", "ChatGPT"), ("SetupD-", "Desktop"), ("SetupW-", "Web")):
                if cells[0].startswith(prefix):
                    paths = (path,)
            steps = row.get("Steps") or row.get("Command") or "; ".join(
                f"{key}: {value}" for key, value in row.items()
                if key not in {"ID", "Result", *PATHS, "Block 1", "Block 2", "Block 5"}
            )
            expected = row.get("Expected", "Run the required scope below and record observed evidence, not an earlier result.")
            cases.append(Case(cells[0], steps, expected, paths, section))
    ids = [case.id for case in cases]
    if not cases or len(ids) != len(set(ids)):
        raise ValueError("The test-plan case inventory is empty or contains duplicate IDs")
    return cases


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _source_link(source: str) -> str:
    return f"[{source}](materials/{source})"


def _html(markdown: str, target: Path) -> None:
    title = next(line[2:] for line in markdown.splitlines() if line.startswith("# "))
    F.write_html(F.Doc(target, title, "en", "Community Access", "", markdown, []), target)


def block_instructions(card_text: str) -> str:
    _, body = F.split_front_matter(card_text)
    body = re.sub(r"^(#{1,4}) ", r"##\1 ", body, flags=re.MULTILINE)
    return (
        "First explain this block as the teacher: show the expected finished result, "
        "read the matching main-deck slides and demonstrate the fallback. "
        "Then complete the full step card below as a student. For ChatGPT use "
        "the browser instructions; for Desktop or Web use the VS Code instructions. "
        "Also complete any instructions for everyone. Do not skip saving. "
        "Read all eight planning questions in block 7; unknown approvals or "
        "measurements remain pending with an owner and next action. "
        "After blocks 3, 4 and 5, run /review-my-agent (or the browser review text), "
        "inspect the twelve answers, approve one justified change and save the next version."
        "\n\n## Full step card\n\n" + body.strip()
    )


def build(out: Path) -> dict:
    out = out.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"{out}: not empty; choose a fresh destination to preserve rehearsal evidence")
    if out == REPO or REPO in out.parents:
        raise ValueError("Rehearsal output must be outside the repository")
    cases = cases_from_plan((REPO / "ahg.md").read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    material = out / "materials"
    shutil.copytree(F.AHG, material / "docs" / "ahg-2026")
    shutil.copyfile(REPO / "ahg.md", material / "ahg.md")
    (out / "text").mkdir()
    (out / "evidence").mkdir()
    slides = deck.build_slides(deck.DeckContext(code_label="ahg-2026", join_display="letitglow.app/w/ahg-2026"))
    steps: list[dict] = []
    results: list[dict] = []

    def add(title: str, source: str, role: str, body: str, case_id: str = "", path: str = "") -> None:
        number = len(steps) + 1
        name = f"{number:03d}-{_slug(role)}-{_slug(title)[:55]}--from-{Path(source).name}"
        heading = f"{number:03d}. {title}"
        markdown = (
            f"# {heading}\n\nRole: {role}. Path: {path or 'shared'}.\n\n"
            f"Original source: {_source_link(source)}.\n\n{body}\n\n"
            "## Record before continuing\n\n"
            f"Record {case_id or name} in [the results sheet](results.csv): "
            "Pass, Fail, Blocked or Not applicable with a reason. Save observed "
            "output, elapsed minutes and a defect reference in the evidence folder. "
            "Do not store account credentials, student data or facilitator keys.\n\n"
            "[Return to the sequence](000-start-here.html).\n"
        )
        _html(markdown, out / f"{name}.html")
        # The HTML and Markdown live at different depths.
        (out / "text" / f"{name}.md").write_text(
            markdown.replace("](materials/", "](../materials/").replace("](results.csv)", "](../results.csv)")
            .replace("](000-start-here.html)", "](../000-start-here.html)"),
            encoding="utf-8",
        )
        steps.append({"number": number, "file": f"{name}.html", "title": title, "source": source,
                      "role": role, "case": case_id, "path": path})
        results.append({"step": number, "case": case_id or name, "role": role, "path": path,
                        "environment": "", "source": source, "status": "Pending", "minutes": "",
                        "evidence": "", "defect_or_reason": ""})

    def add_case(case: Case, path: str = "") -> None:
        role = "Student" if path else "Teacher and tester"
        safety = (
            "Use a scratch collection and practice submissions for all rehearsal writes. "
            "Do not publish test agents, change production configuration or delete "
            "contributions in the real collection. Live sharing, load tests and cleanup "
            "require the facilitator's explicit approval. A local test is not a live-service pass."
        )
        add(f"{case.id}: {case.section}", "ahg.md", role,
            f"## Action\n\n{case.steps}\n\n## Expected result\n\n{case.expected}\n\n"
            f"## Safe scope\n\n{safety}\n\n"
            "For a multi-file, multi-agent or multi-role case, record a separate observation "
            "for every named item. Pass only after all of them pass. Use the current "
            "step card, agent template and supplied checker evidence; do not infer missing findings.",
            case.id, path)

    for source, title in (
        ("docs/ahg-2026/run-of-show.md", "Teacher pre-flight and timing"),
        ("docs/ahg-2026/facilitator-card.md", "Teacher pocket card"),
        ("docs/ahg-2026/helpers-card.md", "Helper preparation and fallback ladder"),
        ("docs/ahg-2026/answer-key.md", "Teacher-only sample course answer key"),
        ("docs/ahg-2026/pre-event-message.md", "Student invitation and setup message"),
        ("docs/ahg-2026/kit/session-in-plain-language.md", "Student course purpose and glossary"),
    ):
        add(title, source, "Teacher" if "Teacher" in title or "Helper" in title else "Student",
            "Read the entire linked source. Open its available Word, HTML and PowerPoint "
            "copies in the same materials folder. Check every participant link. As teacher, "
            "explain the goal aloud; as student, explain what you will produce. "
            "Confirm support arrangements, captions, approved accounts and a Mac tester. "
            "Keep the answer key out of the participant view.")

    for case in cases:
        if case.id.startswith("Auto-"):
            add_case(case)
    for case in cases:
        if case.id.startswith(("Setup-", "Assist-")):
            add_case(case)

    # Read every projected slide before presenting the student runs.
    for number, slide in enumerate(slides, 1):
        body = (
            f"## Slide {number} of {len(slides)}: {slide.title}\n\n"
            f"{slide.kicker}\n\n"
            "Open the HTML, Word, PowerPoint and large-print handout copies of slides "
            "in materials/docs/ahg-2026. Go to this numbered slide in each. "
            "Read its visible content and speaker notes aloud. Check title, reading "
            "order, timing, links, smallest text and the Behind/Stuck fallback. "
            "Then switch roles: as student, state the next action without relying "
            "on the speaker notes. Test links using Tab and Enter in HTML, "
            "Control+click in Word, and Slide Show in PowerPoint.\n\n"
            "## Teacher notes from the source\n\n" + "\n\n".join(slide.notes)
            + "\n\n## Related resources\n\n"
            + "\n".join(f"- [{label}]({url})" for label, url in slide.links)
        )
        add(f"Review slide {number:02d}: {slide.title}", "docs/ahg-2026/slides.md", "Teacher and student", body)
    for case in cases:
        if case.id.startswith("Deck-"):
            add_case(case)

    block_families = {0: (), 1: (), 2: ("Design-",), 3: ("Try-",), 4: ("Ground-",),
                      5: ("Office-",), 6: ("Share-",), 7: ("Plan-",)}
    for path in PATHS:
        add(f"{path}: rehearsal inputs and version checkpoints", "ahg.md", "Student",
            "Read Part 3, section 3.6 for the common design inputs. Use only fictional "
            "course data. Keep one main conversation or kit copy for the full run and "
            "separate scratch conversations/copies for negative tests. Save agent versions "
            "1, 2, 3 and 4, the before/after answers, the team report and the 30-day plan. "
            "Measure the free-tier path separately from the optional paid demo. "
            "Do not overwrite a completed agent while testing fallback agents.", path=path)
        for block, card in enumerate(CARDS):
            source = f"docs/ahg-2026/kit/step-cards/{card}"
            add(f"{path}: block {block} - {card[2:-3]}", source, "Teacher then student",
                block_instructions((REPO / source).read_text(encoding="utf-8")),
                path=path)
            if block == 0:
                prefix = {"ChatGPT": "SetupB-", "Desktop": "SetupD-", "Web": "SetupW-"}[path]
                for case in cases:
                    if case.id.startswith(prefix):
                        add_case(case, path)
            for case in cases:
                if case.id.startswith(block_families[block]) and path in case.paths:
                    add_case(case, path)
        for case in cases:
            if case.id.startswith("AA-") and path in case.paths:
                add_case(case, path)

    covered = {step["case"] for step in steps if step["case"]}
    for case in cases:
        if case.id not in covered:
            add_case(case)

    # Explicit repeat runs prevent a screen-reader spot check becoming a
    # claimed end-to-end pass. Each matrix row has its own pending result.
    matrix = {
        "Env-1": PATHS, "Env-2": PATHS, "Env-3": ("ChatGPT", "Desktop"),
        "Env-4": ("ChatGPT", "Web"), "Env-5": PATHS,
        "Env-6": ("Desktop",), "Env-7": PATHS, "Env-8": PATHS,
    }
    for environment, paths in matrix.items():
        for path in paths:
            add(f"{environment}: end-to-end {path}", "ahg.md", "Student and accessibility tester",
                "Use the operating system, browser and assistive technology in Part 2, "
                "section 2.3. Repeat this path's complete numbered block 0 through block 7 "
                "sequence above, including the team report, sharing and plan. Keep an "
                "environment-specific copy of its case observations in evidence. "
                "For screen-reader rows, use the screen reader and keyboard throughout, "
                "not only for a spot check. For Env-7, repeat at both 200 and 400 percent. "
                "Env-8 is optional; the required Mac rows stay Blocked until a Mac tester "
                "actually runs them. Never mark them Not applicable merely because this "
                "computer is Windows.", environment, path)
            results[-1]["environment"] = environment

    for product in ("ChatGPT Dots", "Claude Duet", "No-account tabletop fallback"):
        add(f"Closing demo: {product}", "docs/ahg-2026/kit/closing-demo.md", "Teacher",
            "Follow the entire demo source for this product or fallback, including its "
            "access check, exact prompt, follow-up, acceptance checklist and task-stop check. "
            "Review closing-demo.pptx as well as the main slides. Mark unavailable "
            "access Blocked, not Pass. Label illustrative or previously captured output. "
            "Never use a connected campus account or spend money to complete the demo.")
    add("Final timed teaching run and release decision", "docs/ahg-2026/run-of-show.md", "Teacher and beginner",
        "Run the entire day with another person acting as a first-time student, once "
        "in a browser and once in desktop VS Code. Keep the deck visible and rehearse "
        "captions, transitions, lunch, break, commitments and evaluation. Record actual "
        "minutes per block. Preserve plan-writing and the evaluation; the closing demo "
        "is optional after 4:30. Review all failures, missing manual checks and blockers. "
        "Sign off only against the source test plan's definition of done. After a fix, "
        "rerun its case and the automated gates. Do not deploy or delete live test "
        "content without approval.")

    fields = list(results[0])
    with (out / "results.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    with (out / "slide-review-results.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=(
            "slide", "title", "format", "status", "notes", "reading_order",
            "link_activation", "layout", "student_next_action", "evidence", "defect_or_reason",
        ))
        writer.writeheader()
        writer.writerows(
            {"slide": number, "title": slide.title, "format": format_name, "status": "Pending"}
            for number, slide in enumerate(slides, 1)
            for format_name in ("HTML", "Word", "PowerPoint", "Large-print handout")
        )
    manifest = {"steps": steps, "cases": [case.id for case in cases],
                "slides": len(slides), "materials": {
                    str(path.relative_to(material)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sorted(material.rglob("*")) if path.is_file()
                }}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    overview = (
        "# AHG rehearsal: start here\n\n"
        "Follow the numbered HTML files below in order. Each names its original source. "
        "The text folder holds the same instructions as Markdown; materials holds an "
        "unchanged snapshot of the source course and all its built formats. The slides "
        "are reviewed individually before all three full student runs. No earlier "
        "test results are carried forward: every result starts Pending.\n\n"
        "## Full instructions and sign-off\n\n"
        "- [Read the full folder instructions](README.html).\n"
        "- [Use the Monday readiness checklist](monday-readiness-checklist.html).\n"
        "- [Record each slide in each format](slide-review-results.csv).\n\n"
        "## Working safely\n\n"
        "Use approved demo accounts and scratch repositories. No real student records, "
        "public test submissions, mass production downloads, configuration changes "
        "or destructive cleanup without explicit approval. Do not upload repository "
        "code or confidential material to an AI service. The closing demo uses only "
        "the fictional evidence printed in its source.\n\n"
        "## Schedule and priorities\n\n"
        "This is a multi-day rehearsal, not a one-hour checklist. First run the automated "
        "gates, teacher slide review and one complete browser path. Next run desktop "
        "and web VS Code, all scenarios, the accessibility matrix and timed beginner runs. "
        "Recruit a Mac tester in parallel; do not wait until the last day. The paid "
        "Dots/Duet demo is optional and cannot replace a required course test.\n\n"
        "## Record evidence\n\n"
        "Open [results.csv](results.csv) in Excel. Record actual results and minutes; "
        "keep supporting outputs in evidence. Pending or Blocked is not a pass. "
        "For a failed check, record the exact input, output, source, product version "
        "and retest. Use a fresh destination to rebuild; this builder will not overwrite "
        "your observations.\n\n"
        "## Ordered steps\n\n"
        + "\n".join(f"{step['number']}. [{step['title']}]({step['file']})" for step in steps)
        + "\n"
    )
    (out / "000-start-here.md").write_text(overview, encoding="utf-8")
    _html(overview, out / "000-start-here.html")
    _, readme = F.split_front_matter((F.AHG / "rehearsal-readme.md").read_text(encoding="utf-8"))
    (out / "README.md").write_text(readme, encoding="utf-8")
    _html(readme, out / "README.html")
    _, signoff = F.split_front_matter((F.AHG / "rehearsal-signoff.md").read_text(encoding="utf-8"))
    (out / "monday-readiness-checklist.md").write_text(signoff, encoding="utf-8")
    _html(signoff, out / "monday-readiness-checklist.html")
    verify(out)
    return manifest


def verify(out: Path) -> None:
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    steps = manifest["steps"]
    if [step["number"] for step in steps] != list(range(1, len(steps) + 1)):
        raise ValueError("Rehearsal sequence has a gap or duplicate number")
    cases = cases_from_plan((out / "materials" / "ahg.md").read_text(encoding="utf-8"))
    observed = {(step["case"], step["path"]) for step in steps if step["case"]}
    required = {(case.id, path) for case in cases for path in (case.paths or ("",))}
    if required - observed:
        raise ValueError(f"Uncovered source scenarios: {sorted(required - observed)}")
    slide_steps = [step for step in steps if step["title"].startswith("Review slide ")]
    if len(slide_steps) != manifest["slides"]:
        raise ValueError("Not every main-deck slide has a review step")
    for relative, expected in manifest["materials"].items():
        path = out / "materials" / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Missing or changed course snapshot: {path}")
    pages = [out / "000-start-here.html", *(out / step["file"] for step in steps)]
    if (out / "README.html").is_file():
        pages.append(out / "README.html")
    if (out / "monday-readiness-checklist.html").is_file():
        pages.append(out / "monday-readiness-checklist.html")
    for page in pages:
        if not page.is_file():
            raise ValueError(f"Missing rehearsal step: {page}")
        parser = C._Html()
        parser.feed(page.read_text(encoding="utf-8"))
        for href in parser.targets:
            link = urlsplit(href)
            if not link.scheme and link.path and not (page.parent / unquote(link.path)).is_file():
                raise ValueError(f"{page.name}: broken local link: {href}")
        problems = C.check_html(page)
        if problems:
            raise ValueError(f"{page.name}: {problems}")
    with (out / "results.csv").open(encoding="utf-8-sig", newline="") as stream:
        recorded_steps = [int(row["step"]) for row in csv.DictReader(stream)]
    if recorded_steps != [step["number"] for step in steps]:
        raise ValueError("Results sheet does not match the ordered steps")
    with (out / "slide-review-results.csv").open(encoding="utf-8-sig", newline="") as stream:
        slide_rows = [(int(row["slide"]), row["format"]) for row in csv.DictReader(stream)]
    expected_slides = [
        (number, format_name) for number in range(1, manifest["slides"] + 1)
        for format_name in ("HTML", "Word", "PowerPoint", "Large-print handout")
    ]
    if slide_rows != expected_slides:
        raise ValueError("Slide results sheet does not cover every slide in every reading format")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", nargs="?", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--check", action="store_true", help="verify an existing rehearsal without changing results")
    args = parser.parse_args()
    if args.check:
        verify(args.out.resolve())
        print(f"PASS: sequence, case/path coverage, slide coverage, snapshot hashes and local links: {args.out}")
        return 0
    manifest = build(args.out)
    print(f"{len(manifest['steps'])} ordered steps, {len(manifest['cases'])} source cases, "
          f"{manifest['slides']} slides: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
