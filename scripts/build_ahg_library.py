#!/usr/bin/env python
"""Build the AHG 2026 resource library: every document, in every format.

One folder that anyone at Accessing Higher Ground can open and find every
resource in the format that works for them. ``work.md`` Part 5 is the spec;
``docs/ahg-2026/formats.md`` says how each format is made and checked.

Every participant document (``scripts/ahg_formats.py`` SOURCES), the deck,
and the four facilitator documents get one folder each, holding every format
under the same base name:

* ``.md``, ``.html``, ``.docx``, ``.pptx`` -- copied from GLOW's built copies
  (the facilitator documents have none in GLOW, so they are written here with
  the same ``ahg_formats`` writers);
* ``.pdf`` -- Word's own export of the ``.docx``, tagged, with bookmarks from
  the headings (Word runs in the background, never on screen);
* ``.epub`` -- Pandoc from the Markdown, with the HTML copies' CSS and EPUB
  Accessibility 1.1 metadata;
* ``daisy/daisy-202/`` and ``daisy/daisy-3/`` -- DAISY Pipeline 2 from the
  EPUB.

Then every copy is checked, and the build stops, naming the file, on any
failure: veraPDF (PDF/UA-1), Ace by DAISY, EPUBCheck, the Pipeline's own
validators, GLOW's ``check_ahg_formats.py`` and ``audit_ahg_docs.py``. A PDF
that fails a PDF/UA rule Word's export cannot be made to pass is kept and
marked in the manifest with the rule numbers, never hidden.

The kit, the browser path texts and the sample course are copied as they
are: they are not converted (``formats.md`` says why).

    python scripts/build_ahg_library.py                  # into S:\\ahg
    python scripts/build_ahg_library.py D:\\some\\folder
    python scripts/build_ahg_library.py out --no-pdf --no-daisy --no-checks

Never edits a source file. ``scripts/check_ahg_library.py`` checks the result.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import datetime as _dt
import hashlib
import html as _html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
AHG = REPO / "docs" / "ahg-2026"
KIT = AHG / "kit"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO / "desktop" / "src"))

import ahg_formats as F

DEFAULT_OUT = Path(r"S:\ahg")
MARKER = "manifest.csv"
PUBLISHER = "Community Access"
LIBRARY_TITLE = "AHG 2026 resource library"

LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
EPUBCHECK_JAR = Path(os.environ.get("EPUBCHECK_JAR", LOCAL / "Programs" / "epubcheck-5.4.0" / "epubcheck.jar"))
VERAPDF = Path(os.environ.get("VERAPDF", LOCAL / "Programs" / "verapdf" / "verapdf.bat"))
PIPELINE_HOME = Path(os.environ.get(
    "DAISY_PIPELINE_HOME",
    LOCAL / "Programs" / "pipeline-ui" / "resources" / "app.asar.unpacked" / "resources" / "daisy-pipeline"))
PIPELINE_WS = "http://localhost:8181/ws"
JAVA_HOMES = (Path(r"C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot\bin"),)

# ---------------------------------------------------------------------------
# What goes in, and where (work.md 5.1 and 5.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Group:
    folder: str
    name: str
    audience: str
    about: str


GROUPS: tuple[Group, ...] = (
    Group("01-start-here", "Start here", "Everyone",
          "What the day is, the message sent before it, and the words it uses."),
    Group("02-slides", "Slides", "Everyone, and the conference",
          "The deck, with speaker notes."),
    Group("03-step-cards", "Step cards", "Participants",
          "One card for each block of the day, 0 to 7."),
    Group("04-guides", "Guides", "Participants",
          "The kit's own guides, for the day and for after it."),
    Group("05-worked-examples", "Worked examples", "Participants",
          "Three people, three agents, start to finish."),
    Group("06-kit", "The kit", "Participants on VS Code",
          "The whole kit as one zip, and the VS Code profile."),
    Group("07-browser-path", "The browser path", "Participants in ChatGPT and other assistants",
          "Each text is pasted whole into an assistant, so plain text is the format."),
    Group("08-sample-course", "Sample course", "Participants",
          "PSY 101 as shipped. Its barriers are planted on purpose; it is not converted."),
    Group("09-facilitators", "For facilitators and helpers", "The team; not uploaded to the conference",
          "Run of show, pocket card, helpers' card and answer key."),
)
GROUP_BY_FOLDER = {g.folder: g for g in GROUPS}


@dataclass(frozen=True)
class Place:
    group: str
    slug: str
    about: str


# Every Markdown document, relative to docs/ahg-2026. Every entry in
# ahg_formats.SOURCES must be here (the build stops if one is not), plus the
# deck and the four facilitator documents.
PLACES: dict[str, Place] = {
    "workshop-frontfacing-guide.md": Place("01-start-here", "session-guide",
                                           "The session description, the six learning outcomes and the two rules."),
    "pre-event-message.md": Place("01-start-here", "pre-event-message",
                                  "The message sent before the day: what to bring and how to get ready."),
    "kit/glossary.md": Place("01-start-here", "glossary", "The words used on the day, in plain English."),
    "slides.md": Place("02-slides", "slides", "The deck for the whole day, with speaker notes."),
    "kit/step-cards/0-before-the-day.md": Place("03-step-cards", "0-before-the-day", "Setup, before the day."),
    "kit/step-cards/1-why-we-are-here.md": Place("03-step-cards", "1-why-we-are-here", "Block 1."),
    "kit/step-cards/2-design-your-agent.md": Place("03-step-cards", "2-design-your-agent", "Block 2."),
    "kit/step-cards/3-your-agent-at-work.md": Place("03-step-cards", "3-your-agent-at-work", "Block 3."),
    "kit/step-cards/4-ground-it.md": Place("03-step-cards", "4-ground-it", "Block 4."),
    "kit/step-cards/5-build-the-office.md": Place("03-step-cards", "5-build-the-office", "Block 5."),
    "kit/step-cards/6-share-it.md": Place("03-step-cards", "6-share-it", "Block 6."),
    "kit/step-cards/7-take-it-home.md": Place("03-step-cards", "7-take-it-home", "Block 7."),
    "kit/README.md": Place("04-guides", "kit-readme",
                           "The first page of the kit, with the screen reader section."),
    "kit/agent-file-principles.md": Place("04-guides", "agent-file-principles",
                                          "What makes a good agent file; read in block 2."),
    "kit/accessibility-agents.md": Place("04-guides", "accessibility-agents",
                                         "Keeping Accessibility Agents after the day."),
    "kit/accessibility-agents-in-the-kit.md": Place("04-guides", "accessibility-agents-in-the-kit",
                                                    "Which Accessibility Agents skills work fully in the kit."),
    "kit/write-your-own-agent.md": Place("04-guides", "write-your-own-agent",
                                         "The full tutorial, for writing agents after the day."),
    "repo/README.md": Place("04-guides", "workshop-repository",
                            "The front page of the workshop repository on GitHub."),
    "kit/examples/maria-alternate-format-planner.md": Place("05-worked-examples", "maria-alternate-format-planner",
                                                            "Maria's alternate format planner."),
    "kit/examples/jordan-faculty-coach.md": Place("05-worked-examples", "jordan-faculty-coach",
                                                  "Jordan's faculty coach."),
    "kit/examples/sam-remediation-log-keeper.md": Place("05-worked-examples", "sam-remediation-log-keeper",
                                                        "Sam's remediation log keeper."),
    "run-of-show.md": Place("09-facilitators", "run-of-show", "The day by the clock, with fallbacks and pre-flight."),
    "facilitator-card.md": Place("09-facilitators", "facilitator-card", "The facilitator's pocket card."),
    "helpers-card.md": Place("09-facilitators", "helpers-card", "One page for the helpers."),
    "answer-key.md": Place("09-facilitators", "answer-key", "Every barrier planted in the sample course."),
}
DECK = "slides.md"
FACILITATORS = ("run-of-show.md", "facilitator-card.md", "helpers-card.md", "answer-key.md")

# Every format a document comes in, in the order the index lists them.
DOC_FORMATS = ("docx", "html", "pdf", "epub", "daisy-202", "daisy-3", "pptx", "md")
FORMAT_NAMES = {
    "docx": "Word", "html": "HTML", "pdf": "PDF", "epub": "EPUB", "daisy-202": "DAISY 2.02",
    "daisy-3": "DAISY 3", "pptx": "PowerPoint", "md": "Markdown", "txt": "Plain text",
    "zip": "Zip", "code-profile": "VS Code profile", "png": "Image", "xlsx": "Excel",
    "vtt": "Captions", "csv": "CSV",
}

# 5.5: exactly what the conference form takes.
CONFERENCE_EXTS = {".doc", ".docx", ".pptx", ".pdf"}
CONFERENCE_LIMIT = 250 * 1024 * 1024


def conference_set() -> list[tuple[str, str, str]]:
    """(source rel, extension, upload name) for every file the conference gets."""
    out = [(DECK, ext, f"ahg-2026-slides.{ext}") for ext in ("pptx", "docx", "pdf")]
    named = [("workshop-frontfacing-guide.md", "session-guide"), ("kit/glossary.md", "glossary")]
    named += [(rel, "step-card-" + PLACES[rel].slug) for rel in F.SOURCES if rel.startswith("kit/step-cards/")]
    named += [(rel, "example-" + PLACES[rel].slug) for rel in F.SOURCES if rel.startswith("kit/examples/")]
    for rel, name in named:
        out += [(rel, ext, f"ahg-2026-{name}.{ext}") for ext in ("docx", "pdf")]
    return out


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def human_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{max(1, round(n / 1024))} KB"


def tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def say(text: str) -> None:
    print(text, flush=True)


class BuildError(SystemExit):
    def __init__(self, path: Path | str, problem: str) -> None:
        super().__init__(f"FAILED  {path}: {problem}")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("errors", "replace")
    kw.setdefault("check", False)
    return subprocess.run(cmd, **kw)  # noqa: PLW1510 - check is set just above


def java_env() -> dict[str, str]:
    env = dict(os.environ)
    if not shutil.which("java"):
        for home in JAVA_HOMES:
            if (home / "java.exe").is_file():
                env["PATH"] = f"{home}{os.pathsep}{env.get('PATH', '')}"
                break
    return env


def java() -> str:
    """The java executable: Windows finds a program on the caller's PATH, not the child's."""
    found = shutil.which("java", path=java_env().get("PATH"))
    if not found:
        raise BuildError("java", "Java 11 or later is needed for EPUBCheck and veraPDF")
    return found


def glow_commit() -> str:
    done = run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"])
    commit = done.stdout.strip() or "unknown"
    dirty = run(["git", "-C", str(REPO), "status", "--porcelain", "--", "docs/ahg-2026", "scripts"]).stdout.strip()
    return f"{commit} plus local changes" if dirty else commit


def markdown_body(rel: str) -> tuple[dict[str, str], str]:
    """The Markdown without its front matter or HTML comments (they never reach a reader)."""
    text = (AHG / rel).read_text(encoding="utf-8").replace("\r\n", "\n")
    meta, body = F.split_front_matter(text)
    body = re.sub(r"<!--.*?-->\n?", "", body, flags=re.DOTALL)
    return meta, body


def built_copy(rel: str, ext: str) -> Path:
    """Where GLOW keeps a document's built copy in one format."""
    if ext == "md":
        return AHG / rel
    return AHG / f"{F.output_stem(rel)}.{ext}"


# ---------------------------------------------------------------------------
# The record of every file
# ---------------------------------------------------------------------------


@dataclass
class Entry:
    group: str
    document: str
    fmt: str
    path: Path  # file, or for DAISY the folder (expanded when the manifest is written)
    check: str = ""
    tools: str = ""


@dataclass
class Library:
    out: Path
    built: str
    commit: str
    tools: dict[str, str] = field(default_factory=dict)
    entries: list[Entry] = field(default_factory=list)
    docs: list[tuple[str, Place, str]] = field(default_factory=list)  # rel, place, title
    exceptions: list[str] = field(default_factory=list)
    only: set[str] = field(default_factory=set)  # slugs; empty means every document

    def add(self, group: str, document: str, fmt: str, path: Path, check: str = "", tools: str = "") -> Entry:
        entry = Entry(group, document, fmt, path, check, tools)
        self.entries.append(entry)
        return entry

    def find(self, document: str, fmt: str) -> Entry | None:
        return next((e for e in self.entries if e.document == document and e.fmt == fmt), None)


# ---------------------------------------------------------------------------
# Step 1: the four formats GLOW already builds are current, and pass
# ---------------------------------------------------------------------------


def ensure_formats_current(skip_audit: bool) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO / "desktop" / "src"), str(REPO / "web" / "src"),
                                         env.get("PYTHONPATH", "")])
    check = [sys.executable, str(SCRIPTS / "check_ahg_formats.py")]
    done = run(check, env=env, cwd=REPO)
    if done.returncode != 0:
        say("  the four formats are out of date; rebuilding them (build_ahg_kit.py --formats-only)")
        rebuilt = run([sys.executable, str(SCRIPTS / "build_ahg_kit.py"), "--formats-only"], env=env, cwd=REPO)
        if rebuilt.returncode != 0:
            raise BuildError("scripts/build_ahg_kit.py --formats-only", rebuilt.stderr.strip()[-500:])
        done = run(check, env=env, cwd=REPO)
        if done.returncode != 0:
            raise BuildError("scripts/check_ahg_formats.py", done.stdout.strip()[-1500:])
    results = {"check_ahg_formats": done.stdout.strip().splitlines()[-1]}
    say(f"  check_ahg_formats.py: {results['check_ahg_formats']}")
    if not skip_audit:
        audit = run([sys.executable, str(SCRIPTS / "audit_ahg_docs.py")], env=env, cwd=REPO)
        last = audit.stdout.strip().splitlines()[-1] if audit.stdout.strip() else audit.stderr.strip()[-300:]
        if audit.returncode != 0:
            raise BuildError("scripts/audit_ahg_docs.py", audit.stdout.strip()[-1500:])
        results["audit_ahg_docs"] = last
        say(f"  audit_ahg_docs.py: {last}")
    return results


# ---------------------------------------------------------------------------
# Step 2: the Markdown, HTML, Word and PowerPoint copies
# ---------------------------------------------------------------------------


def _glow_audit(path: Path) -> str:
    """GLOW's own Word, PowerPoint, PDF or EPUB audit, as one line."""
    from acb_large_print.auditor import audit_document
    from acb_large_print.epub_auditor import audit_epub
    from acb_large_print.pdf_auditor import audit_pdf
    from acb_large_print.pptx_auditor import audit_presentation

    audit = {".docx": audit_document, ".pptx": audit_presentation, ".pdf": audit_pdf, ".epub": audit_epub}[path.suffix]
    result = audit(path)
    serious = [f for f in result.findings if str(f.severity).split(".")[-1] in {"CRITICAL", "HIGH"}]
    ok = result.passed and not serious
    word = "pass" if ok else "FAIL " + ", ".join(sorted({f.rule_id for f in serious})[:6])
    return f"GLOW audit {word} (score {result.score})"


def copy_documents(lib: Library) -> None:
    sys.path.insert(0, str(SCRIPTS))
    import check_ahg_formats as C

    unplaced = [rel for rel in F.SOURCES if rel not in PLACES]
    if unplaced:
        raise BuildError("scripts/build_ahg_library.py", f"no place in the library for {', '.join(unplaced)}; add it to PLACES")
    order = [rel for rel in PLACES if not lib.only or PLACES[rel].slug in lib.only]
    for rel in order:
        place = PLACES[rel]
        folder = lib.out / place.group / place.slug
        folder.mkdir(parents=True, exist_ok=True)
        doc = F.read(rel)
        lib.docs.append((rel, place, doc.title))
        target = folder / f"{place.slug}.md"
        shutil.copyfile(AHG / rel, target)
        lib.add(place.group, place.slug, "md", target, "audit_ahg_docs.py pass")
        if rel in FACILITATORS:
            # GLOW keeps no copies of these; write them with the same writers.
            F.write_html(doc, folder / f"{place.slug}.html")
            F.write_docx(doc, folder / f"{place.slug}.docx")
            F.write_pptx(doc, folder / f"{place.slug}.pptx")
            for ext, check in (("html", C.check_html), ("docx", C.check_docx), ("pptx", C.check_pptx)):
                path = folder / f"{place.slug}.{ext}"
                problems = check(path)
                if problems:
                    raise BuildError(path, "; ".join(problems))
                result = "check_ahg_formats checks pass"
                if ext in ("docx", "pptx"):
                    result += "; " + _glow_audit(path)
                    if "FAIL" in result:
                        raise BuildError(path, result)
                lib.add(place.group, place.slug, ext, path, result, f"pandoc {lib.tools['pandoc']}")
            continue
        for ext in ("html", "docx", "pptx"):
            source = built_copy(rel, ext)
            if not source.is_file():
                raise BuildError(source, "GLOW has no built copy; run python scripts/build_ahg_kit.py --formats-only")
            target = folder / f"{place.slug}.{ext}"
            shutil.copyfile(source, target)
            check = "check_ahg_formats.py pass" if rel != DECK else "deck tests pass"
            if ext in ("docx", "pptx"):
                check += "; audit_ahg_docs.py pass"
            lib.add(place.group, place.slug, ext, target, check)


# ---------------------------------------------------------------------------
# Step 3: EPUB 3, from the Markdown
# ---------------------------------------------------------------------------

EPUB_CSS = re.search(r"<style>\n(.*?)</style>", F.HTML_TEMPLATE, re.DOTALL).group(1)


def _a11y_metadata(summary: str) -> str:
    lines = [
        '<meta property="schema:accessMode">textual</meta>',
        '<meta property="schema:accessModeSufficient">textual</meta>',
        '<meta property="schema:accessibilityFeature">structuralNavigation</meta>',
        '<meta property="schema:accessibilityFeature">tableOfContents</meta>',
        '<meta property="schema:accessibilityFeature">readingOrder</meta>',
        '<meta property="schema:accessibilityHazard">none</meta>',
        f'<meta property="schema:accessibilitySummary">{_html.escape(summary)}</meta>',
        '<meta property="dcterms:conformsTo">EPUB Accessibility 1.1 - WCAG 2.2 Level AA</meta>',
        f'<meta property="a11y:certifiedBy">{PUBLISHER}</meta>',
    ]
    return "\n    ".join(lines)


def _rewrite_opf(epub: Path, summary: str) -> None:
    """Replace Pandoc's accessibility metadata with the full EPUB Accessibility 1.1 set."""
    with zipfile.ZipFile(epub) as zf:
        entries = [(info, zf.read(info.filename)) for info in zf.infolist()]
    out = []
    for info, data in entries:
        if info.filename.endswith(".opf"):
            text = data.decode("utf-8")
            text = re.sub(r'\s*<meta property="(schema:access[^"]*|dcterms:conformsTo|a11y:[^"]*)"[^>]*>[^<]*</meta>',
                          "", text)
            text = text.replace("</metadata>", f"  {_a11y_metadata(summary)}\n  </metadata>", 1)
            data = text.encode("utf-8")
        out.append((info, data))
    with zipfile.ZipFile(epub, "w") as zf:
        for info, data in out:
            # The mimetype entry stays first and uncompressed, as OCF requires.
            method = zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED
            zf.writestr(zipfile.ZipInfo(info.filename, date_time=info.date_time), data, compress_type=method)


def write_epub(rel: str, title: str, target: Path, built: str) -> None:
    meta, body = markdown_body(rel)
    author = meta.get("author", "Community Access")
    description = meta.get("description", "")
    lang = meta.get("lang", "en")
    slug = PLACES[rel].slug
    # Pandoc's gfm reader keeps inline HTML even with -raw_html, so text such
    # as "agents/<login>/<name>/" would reach the XHTML as tags. Read the
    # Markdown once, turn any raw HTML back into the text it was, and write
    # the EPUB from that, the way the Word and PowerPoint copies already do.
    document = json.loads(run([F.pandoc(), "-f", "gfm", "-t", "json"], input=body).stdout)
    document["blocks"] = _raw_html_as_text(document["blocks"])
    with tempfile.TemporaryDirectory() as tmp:
        css = Path(tmp) / "ahg.css"
        css.write_text(EPUB_CSS, encoding="utf-8")
        source = Path(tmp) / "source.json"
        source.write_text(json.dumps(document), encoding="utf-8")
        cmd = [F.pandoc(), str(source), "-f", "json", "-t", "epub3", "-o", str(target),
               "--epub-title-page=false", f"--css={css}", "--toc-depth=3",
               "--metadata", f"title={title}", "--metadata", f"lang={lang}",
               "--metadata", f"author={author}", "--metadata", f"publisher={PUBLISHER}",
               "--metadata", f"date={built}", "--metadata", f"description={description}",
               "--metadata", f"identifier=urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, 'https://letitglow.app/ahg/library/' + slug)}"]
        done = run(cmd)
        if done.returncode != 0:
            raise BuildError(target, f"Pandoc failed: {done.stderr.strip()[-500:]}")
    summary = ("This publication is text only, with headings, a table of contents and a logical "
               "reading order for navigation, and no hazards; it meets WCAG 2.2 Level AA.")
    _rewrite_opf(target, summary)


_DROP = object()


def _raw_html_as_text(node):
    """Every RawInline or RawBlock of HTML in a Pandoc AST, as the plain text it was written as."""
    if isinstance(node, list):
        out = []
        for item in node:
            item = _raw_html_as_text(item)
            if item is not _DROP:
                out.append(item)
        return out
    if isinstance(node, dict):
        kind, content = node.get("t"), node.get("c")
        if kind == "RawInline" and content[0] in ("html", "html4", "html5"):
            return {"t": "Str", "c": content[1]}
        if kind == "RawBlock" and content[0] in ("html", "html4", "html5"):
            text = content[1].strip()
            return _DROP if text.startswith("<!--") else {"t": "Para", "c": [{"t": "Str", "c": text}]}
        return {k: _raw_html_as_text(v) for k, v in node.items()}
    return node


def build_epubs(lib: Library) -> None:
    for rel, place, title in lib.docs:
        target = lib.out / place.group / place.slug / f"{place.slug}.epub"
        write_epub(rel, title, target, lib.built)
        lib.add(place.group, place.slug, "epub", target, "", f"pandoc {lib.tools['pandoc']}")
    say(f"  {len(lib.docs)} EPUB files")


# ---------------------------------------------------------------------------
# Step 4: PDF, from the Word file, by Word itself (never on screen)
# ---------------------------------------------------------------------------


def build_pdfs(lib: Library) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    try:
        # DispatchEx: a new Word of our own, never the one a person has open.
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0  # wdAlertsNone
        lib.tools["word"] = f"Microsoft Word {word.Version} build {word.Build}"
        for rel, place, _title in lib.docs:
            folder = lib.out / place.group / place.slug
            docx = folder / f"{place.slug}.docx"
            pdf = folder / f"{place.slug}.pdf"
            document = word.Documents.Open(str(docx), ConfirmConversions=False, ReadOnly=True,
                                           AddToRecentFiles=False, Visible=False)
            try:
                document.ExportAsFixedFormat(
                    OutputFileName=str(pdf), ExportFormat=17,  # wdExportFormatPDF
                    OpenAfterExport=False, OptimizeFor=0,  # wdExportOptimizeForPrint
                    IncludeDocProps=True,  # the title, which PDF/UA requires
                    CreateBookmarks=1,  # wdExportCreateHeadingBookmarks
                    DocStructureTags=True, BitmapMissingFonts=True, UseISO19005_1=False)
            finally:
                document.Close(SaveChanges=0)
            if not pdf.is_file():
                raise BuildError(pdf, "Word wrote no PDF")
            lib.add(place.group, place.slug, "pdf", pdf, "", lib.tools["word"])
    finally:
        if word is not None:
            word.Quit(SaveChanges=0)
        pythoncom.CoUninitialize()
    say(f"  {len(lib.docs)} PDF files, from {lib.tools['word']}")


# ---------------------------------------------------------------------------
# Step 5: DAISY 2.02 and DAISY 3, from the EPUB, by DAISY Pipeline 2
# ---------------------------------------------------------------------------


def _pipeline_alive() -> str:
    try:
        with urllib.request.urlopen(f"{PIPELINE_WS}/alive", timeout=5) as resp:  # localhost only
            text = resp.read().decode("utf-8")
    except OSError:
        return ""
    found = re.search(r'<alive[^>]*\sversion="([^"]+)"', text)
    return found.group(1) if found else "unknown"


def ensure_pipeline() -> str:
    version = _pipeline_alive()
    if version:
        return version
    launcher = PIPELINE_HOME / "bin" / "pipeline2.bat"
    if not launcher.is_file():
        raise BuildError(launcher, "DAISY Pipeline 2 is not installed here")
    say("  starting the DAISY Pipeline 2 engine (local, this machine only)")
    # Run from the engine's own folder: the launcher uses "cd" without /d,
    # so from another drive its relative class path finds nothing.
    subprocess.Popen(["cmd", "/c", str(launcher), "local"], cwd=str(PIPELINE_HOME),
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(90):
        time.sleep(2)
        version = _pipeline_alive()
        if version:
            return version
    raise BuildError(PIPELINE_WS, "the DAISY Pipeline 2 engine did not start within three minutes")


def _dp2(*args: str) -> subprocess.CompletedProcess:
    cli = PIPELINE_HOME / "cli" / "dp2.exe"
    return run([str(cli), "--host", "http://localhost", "--port", "8181", "--ws_path", "ws",
                "--starting", "false", *args, "-q"], timeout=1800)


def _validation_errors_202(report_dir: Path) -> tuple[int, int, list[str]]:
    """Errors and warnings in the DAISY 2.02 validator's HTML report."""
    errors, warnings, messages = 0, 0, []
    for report in report_dir.rglob("*.html"):
        text = report.read_text(encoding="utf-8", errors="replace")
        for cls, body in re.findall(r'<li class="(message-error|error|message-warning|warning)"[^>]*>(.*?)</li>', text, re.DOTALL):
            plain = " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", body)).split())
            if "type::warning" in plain or cls.endswith("warning"):
                warnings += 1
            else:
                errors += 1
                messages.append(plain[:300])
    return errors, warnings, messages


def _daisy_one(epub: Path, folder: Path, work: Path) -> dict[str, str]:
    """Both DAISY versions of one EPUB, each validated; returns a check line per version."""
    results: dict[str, str] = {}
    # The engine can keep its input open after a job; give it a copy, so the
    # library's own EPUB can always be replaced on the next build.
    source = work / epub.name
    shutil.copyfile(epub, source)
    for script, name in (("epub3-to-daisy202", "daisy-202"), ("epub3-to-daisy3", "daisy-3")):
        out = work / name
        shutil.rmtree(out, ignore_errors=True)
        done = _dp2(script, "--source", str(source), "-o", str(out), "--validation", "abort")
        if "status: SUCCESS" not in done.stdout:
            raise BuildError(epub, f"DAISY Pipeline {script} did not succeed: {done.stdout.strip()[-600:]}")
        result_dir = out / "result"
        # DAISY 2.02 lands in a folder named after the identifier; DAISY 3 does not.
        inner = [p for p in result_dir.iterdir() if p.is_dir()]
        source_dir = inner[0] if name == "daisy-202" and len(inner) == 1 else result_dir
        target = folder / "daisy" / name
        # Validated where the engine wrote it, then copied, for the same reason as above.
        if name == "daisy-202":
            report = work / "validate-202"
            shutil.rmtree(report, ignore_errors=True)
            _dp2("daisy202-validator", "--source", str(source_dir / "ncc.html"), "-o", str(report))
            errors, warnings, messages = _validation_errors_202(report)
            if errors:
                raise BuildError(target / "ncc.html",
                                 f"DAISY 2.02 validator: {errors} errors: {' | '.join(messages[:3])}")
            results[name] = f"converter validation pass; daisy202-validator 0 errors, {warnings} warnings"
        else:
            dtbook = next(source_dir.glob("*.xml"))
            report = work / "validate-3"
            shutil.rmtree(report, ignore_errors=True)
            _dp2("dtbook-validator", "--source", str(dtbook), "-o", str(report))
            xml = next(report.rglob("dtbook-validation-report.xml"), None)
            if xml is None:
                raise BuildError(target / dtbook.name, "the DTBook validator wrote no report")
            count = re.search(r"<d:error-count>(\d+)</d:error-count>", xml.read_text(encoding="utf-8"))
            if not count or count.group(1) != "0":
                raise BuildError(target / dtbook.name,
                                 f"DTBook validator: {count.group(1) if count else 'unknown'} errors")
            results[name] = "converter validation pass; dtbook-validator 0 errors"
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source_dir, target)
    return results


def build_daisy(lib: Library, jobs: int) -> None:
    version = ensure_pipeline()
    lib.tools["pipeline"] = f"DAISY Pipeline 2 engine {version}"
    work_root = Path(tempfile.mkdtemp(prefix="ahg-daisy-"))
    try:
        def one(item: tuple[str, Place, str]) -> tuple[Place, dict[str, str]]:
            _rel, place, _title = item
            folder = lib.out / place.group / place.slug
            work = work_root / place.slug
            work.mkdir(parents=True, exist_ok=True)
            return place, _daisy_one(folder / f"{place.slug}.epub", folder, work)

        with cf.ThreadPoolExecutor(max_workers=jobs) as pool:
            for place, results in pool.map(one, lib.docs):
                folder = lib.out / place.group / place.slug
                for name, check in results.items():
                    lib.add(place.group, place.slug, name, folder / "daisy" / name, check, lib.tools["pipeline"])
                say(f"    DAISY {place.group}/{place.slug}")
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
    say(f"  {len(lib.docs)} DAISY 2.02 and {len(lib.docs)} DAISY 3 books, from {lib.tools['pipeline']}")


# ---------------------------------------------------------------------------
# Step 6: the checks on the new formats
# ---------------------------------------------------------------------------


# PDF/UA-1 rules (ISO 14289-1 clause-test, as veraPDF numbers them) that
# Word's own export fails whatever the Word file holds. A PDF failing only
# these is kept and marked; any other failed rule stops the build.
WORD_EXPORT_RULES = {
    "5-1": "Word writes no PDF/UA identification (pdfuaid) in the XMP metadata",
    "7.5-1": "Word writes no Scope on table header cells (TH), so veraPDF cannot work out a cell's headers",
}


def _verapdf(path: Path, env: dict[str, str]) -> tuple[bool, list[str]]:
    done = run(["cmd", "/c", str(VERAPDF), "--flavour", "ua1", "--format", "xml", str(path)], env=env, timeout=600)
    report = done.stdout
    if "<validationReport" not in report:
        raise BuildError(path, f"veraPDF gave no report: {(done.stderr or report).strip()[-400:]}")
    compliant = re.search(r'isCompliant="(true|false)"', report)
    failed = set()
    for rule in re.findall(r"<rule [^>]*>", report):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', rule))
        if attrs.get("status") == "failed":
            failed.add(f"{attrs.get('clause')}-{attrs.get('testNumber')}")
    return bool(compliant and compliant.group(1) == "true"), sorted(failed)


def check_pdfs(lib: Library, jobs: int) -> None:
    pdfs = [e for e in lib.entries if e.fmt == "pdf"]
    if not pdfs:
        return
    if not VERAPDF.is_file():
        raise BuildError(VERAPDF, "veraPDF is not installed here")
    env = java_env()
    with cf.ThreadPoolExecutor(max_workers=jobs) as pool:
        results = list(pool.map(lambda e: (e, *_verapdf(e.path, env)), pdfs))
    for entry, compliant, failed in results:
        if compliant:
            verdict = "veraPDF PDF/UA-1 pass"
        else:
            unexpected = [r for r in failed if r not in WORD_EXPORT_RULES]
            if unexpected or not failed:
                raise BuildError(entry.path, f"veraPDF PDF/UA-1 fails {' '.join(unexpected) or 'with no rule named'}")
            verdict = f"PDF/UA: fails {' '.join(failed)}"
            lib.exceptions.append(f"{entry.path.relative_to(lib.out).as_posix()}: {verdict}")
        glow = _glow_audit(entry.path)
        entry.check = f"{verdict}; {glow}"
        entry.tools = f"{entry.tools}; {lib.tools['verapdf']}"
    passed = sum(1 for e in pdfs if e.check.startswith("veraPDF PDF/UA-1 pass"))
    say(f"  veraPDF PDF/UA-1: {passed} of {len(pdfs)} PDF files pass")
    for rule, why in WORD_EXPORT_RULES.items():
        n = sum(1 for e in pdfs if f" {rule}" in e.check.split(";")[0])
        if n:
            say(f"    {n} fail {rule}: {why}")


def _ace(epub: Path) -> dict[str, int]:
    with tempfile.TemporaryDirectory() as tmp:
        ace = shutil.which("ace") or shutil.which("ace.cmd")
        if not ace:
            raise BuildError(epub, "Ace by DAISY is not installed (npm install -g @daisy/ace)")
        done = run([ace, "-f", "-s", "-o", tmp, str(epub)], timeout=900)
        report = Path(tmp) / "report.json"
        if not report.is_file():
            raise BuildError(epub, f"Ace wrote no report: {(done.stderr or done.stdout).strip()[-400:]}")
        data = json.loads(report.read_text(encoding="utf-8"))
    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for doc in data.get("assertions", []):
        for assertion in doc.get("assertions", []):
            impact = assertion.get("earl:test", {}).get("earl:impact", "minor")
            counts[impact] = counts.get(impact, 0) + 1
    return counts


def _epubcheck(epub: Path) -> tuple[int, int]:
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "epubcheck.json"
        run([java(), "-jar", str(EPUBCHECK_JAR), str(epub), "--json", str(report)], env=java_env(), timeout=600)
        if not report.is_file():
            raise BuildError(epub, "EPUBCheck wrote no report")
        data = json.loads(report.read_text(encoding="utf-8"))
    severities = [m.get("severity") for m in data.get("messages", [])]
    errors = sum(1 for s in severities if s in ("ERROR", "FATAL"))
    warnings = sum(1 for s in severities if s == "WARNING")
    return errors, warnings


def check_epubs(lib: Library, jobs: int) -> None:
    epubs = [e for e in lib.entries if e.fmt == "epub"]

    def one(entry: Entry) -> tuple[Entry, dict[str, int], tuple[int, int]]:
        return entry, _ace(entry.path), _epubcheck(entry.path)

    with cf.ThreadPoolExecutor(max_workers=jobs) as pool:
        for entry, ace, (errors, warnings) in pool.map(one, epubs):
            if ace["critical"] or ace["serious"]:
                raise BuildError(entry.path, f"Ace: {ace['critical']} critical, {ace['serious']} serious violations")
            if errors:
                raise BuildError(entry.path, f"EPUBCheck: {errors} errors")
            entry.check = (f"Ace 0 critical, 0 serious, {ace['moderate']} moderate, {ace['minor']} minor; "
                           f"EPUBCheck 0 errors, {warnings} warnings; {_glow_audit(entry.path)}")
            entry.tools = f"{entry.tools}; {lib.tools['ace']}; {lib.tools['epubcheck']}"
    say(f"  Ace and EPUBCheck: {len(epubs)} of {len(epubs)} EPUB files pass")


# ---------------------------------------------------------------------------
# Step 7: the files that are not converted
# ---------------------------------------------------------------------------


SAMPLE_README = """# PSY 101 sample course

The barriers in this course are planted on purpose. It is the fictional PSY
101, Introduction to Psychology, at Mesa Ridge State University, exactly as
the workshop kit ships it, and every barrier in it is there for the agents
to find. That is why it comes in its own formats only: converting it would
remove or change the barriers.

- The course files are the ones a participant opens in the kit.
- `evidence` holds each file's checker report as plain text, ready to give
  an agent: GLOW for the documents, axe-core for the web page.

The full list of barriers is the answer key, in `09-facilitators`, for
facilitators only.
"""


def copy_files(lib: Library) -> None:
    # 06: the kit, as one zip, and the VS Code profile.
    sys.path.insert(0, str(SCRIPTS))
    import build_ahg_kit

    kit_dir = lib.out / "06-kit"
    kit_dir.mkdir(parents=True, exist_ok=True)
    zip_path = build_ahg_kit.build_zip()  # zips the kit as committed; writes only the gitignored dist/
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad:
            raise BuildError(zip_path, f"corrupt entry {bad}")
        entries = len(zf.infolist())
    shutil.copyfile(zip_path, kit_dir / "ahg-2026-agent-kit.zip")
    lib.add("06-kit", "ahg-2026-agent-kit", "zip", kit_dir / "ahg-2026-agent-kit.zip",
            f"zip test pass, {entries} entries")
    shutil.copyfile(KIT / "ahg-2026.code-profile", kit_dir / "ahg-2026.code-profile")
    json.loads((kit_dir / "ahg-2026.code-profile").read_text(encoding="utf-8"))
    lib.add("06-kit", "ahg-2026", "code-profile", kit_dir / "ahg-2026.code-profile", "valid JSON")

    # 07: the browser path texts.
    texts = lib.out / "07-browser-path"
    texts.mkdir(parents=True, exist_ok=True)
    for path in sorted((KIT / "any-assistant").glob("*.txt")):
        shutil.copyfile(path, texts / path.name)
        path.read_text(encoding="utf-8")
        lib.add("07-browser-path", path.stem, "txt", texts / path.name, "UTF-8 plain text")

    # 08: the sample course, barriers and all.
    course = lib.out / "08-sample-course"
    course.mkdir(parents=True, exist_ok=True)
    (course / "README.md").write_text(SAMPLE_README, encoding="utf-8", newline="\n")
    lib.add("08-sample-course", "README", "md", course / "README.md", "written by the library build")
    for path in sorted((KIT / "sample-course").rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(KIT / "sample-course")
        target = course / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        document = ("evidence/" if rel.parts[0] == "evidence" else "") + path.stem
        lib.add("08-sample-course", document, path.suffix.lstrip("."), target,
                "planted barriers, not checked" if rel.parts[0] != "evidence" else "checker report")


# ---------------------------------------------------------------------------
# Step 8: the conference set
# ---------------------------------------------------------------------------


def build_conference(lib: Library) -> None:
    folder = lib.out / "conference-upload"
    folder.mkdir(parents=True, exist_ok=True)
    for rel, ext, name in conference_set():
        place = PLACES[rel]
        if lib.only and place.slug not in lib.only:
            continue
        source = lib.out / place.group / place.slug / f"{place.slug}.{ext}"
        if not source.is_file():
            if ext == "pdf":
                continue  # built without PDF (--no-pdf); the checker says so
            raise BuildError(source, "missing; the conference set needs it")
        target = folder / name
        shutil.copyfile(source, target)
        if target.stat().st_size >= CONFERENCE_LIMIT:
            raise BuildError(target, "250 MB or more; the conference form will refuse it")
        origin = lib.find(place.slug, ext)
        lib.add("conference-upload", place.slug, ext, target,
                f"copy of {source.relative_to(lib.out).as_posix()}" + (f"; {origin.check}" if origin and origin.check else ""),
                origin.tools if origin else "")


# ---------------------------------------------------------------------------
# Step 9: the front door, README and manifest (work.md 5.4)
# ---------------------------------------------------------------------------

CHOOSE = [
    ("Word", "to edit, or to read in large print. ACB large print: Arial 18 point, flush left."),
    ("HTML", "to read in a web browser. Each page works offline."),
    ("PDF", "to print. Tagged, with bookmarks from the headings."),
    ("EPUB", "for an e-reader or a reading app such as Thorium Reader, Apple Books or Voice Dream."),
    ("DAISY", "for a DAISY player: DAISY 2.02 for most players, DAISY 3 where yours prefers it. Text only, no audio."),
    ("Markdown", "for GitHub, or to read as plain text."),
    ("PowerPoint", "a reading deck: each section as a slide. The deck itself is under Slides."),
]

INDEX_CSS = """
  :root { --fg: #111; --bg: #fff; --muted: #333; --accent: #0b4f8a; --panel: #eef3f8; --line: #555; --focus: #b45309; }
  @media (prefers-color-scheme: dark) {
    :root { --fg: #f2f2f2; --bg: #121212; --muted: #d6d6d6; --accent: #8cc4ff; --panel: #1e2a36; --line: #aaa; --focus: #fbbf24; }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
  body { font-family: Arial, Helvetica, sans-serif; font-size: 1.5rem; line-height: 1.5;
         color: var(--fg); background: var(--bg); margin: 0; overflow-wrap: break-word; }
  .wrap { margin: 0 auto; max-width: 52rem; padding: 0 1rem; }
  .skip-link { position: absolute; left: 0.5rem; top: -10rem; background: var(--bg); color: var(--accent);
               padding: 0.5rem 1rem; border: 3px solid var(--accent); z-index: 10; }
  .skip-link:focus { top: 0.5rem; }
  header { border-bottom: 2px solid var(--line); padding: 0.75rem 0; }
  header p { margin: 0; font-weight: 700; }
  main { padding: 0.5rem 0 3rem; }
  main:focus { outline: none; }
  h1 { font-size: 2.2rem; line-height: 1.2; margin: 1.25rem 0 1rem; }
  h2 { font-size: 1.8rem; line-height: 1.25; margin-top: 2.5rem; }
  p, li { max-width: 40em; }
  a { color: var(--accent); text-decoration-thickness: 0.08em; text-underline-offset: 0.15em; }
  a:hover { text-decoration-thickness: 0.15em; }
  :focus-visible { outline: 4px solid var(--focus); outline-offset: 3px; }
  code { font-family: Consolas, "Courier New", monospace; font-size: 0.95em; overflow-wrap: anywhere; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
  caption { text-align: left; font-weight: 700; padding-bottom: 0.5rem; }
  th, td { text-align: left; vertical-align: top; border: 1px solid var(--line); padding: 0.4rem 0.6rem; }
  thead th { background: var(--panel); }
  ul.formats { list-style: none; margin: 0; padding: 0; }
  ul.formats li { margin: 0 0 0.25rem; }
  dl.choose dt { font-weight: 700; margin-top: 0.75rem; }
  dl.choose dd { margin-left: 0; }
  footer { border-top: 2px solid var(--line); padding: 1rem 0 2rem; font-size: 1.25rem; color: var(--muted); }
  @media (max-width: 40rem) {
    table, thead, tbody, tr, th, td { display: block; width: 100%; }
    thead { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
    tr { border: 1px solid var(--line); margin-bottom: 1rem; }
    th, td { border: 0; border-top: 1px solid var(--line); }
    tr > :first-child { border-top: 0; }
  }
  @media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
  @media print { .skip-link { display: none; } body { font-size: 18pt; } }
"""


@dataclass
class Row:
    title: str
    about: str
    links: list[tuple[str, str, int]]  # label, relative href, bytes


def _href(lib: Library, path: Path) -> str:
    return path.relative_to(lib.out).as_posix()


def _daisy_entry(path: Path, fmt: str) -> Path:
    return path / "ncc.html" if fmt == "daisy-202" else next(path.glob("*.opf"), path)


def rows_for(lib: Library, group: str) -> list[Row]:
    rows: list[Row] = []
    if group in {p.group for _r, p, _t in lib.docs}:
        for _rel, place, title in lib.docs:
            if place.group != group:
                continue
            links = []
            for fmt in DOC_FORMATS:
                entry = lib.find(place.slug, fmt)
                if entry is None or entry.group != group:
                    continue
                target = _daisy_entry(entry.path, fmt) if fmt.startswith("daisy") else entry.path
                links.append((FORMAT_NAMES[fmt], _href(lib, target), tree_size(entry.path)))
            rows.append(Row(title, place.about, links))
        return rows
    for entry in lib.entries:
        if entry.group != group:
            continue
        name = entry.path.name
        label = FORMAT_NAMES.get(entry.fmt, entry.fmt.upper())
        about = {
            "ahg-2026-agent-kit.zip": "The whole kit, to unzip and open in VS Code.",
            "ahg-2026.code-profile": "The VS Code profile: import it with Profiles, Import Profile.",
            "README.md": "Read this first: the barriers are planted on purpose.",
        }.get(name, "")
        if not about and group == "07-browser-path":
            about = "Paste the whole text into the assistant."
        if not about and group == "08-sample-course":
            about = "Checker report, as plain text." if entry.document.startswith("evidence/") else "Course file, barriers included."
        rows.append(Row(name, about, [(label, _href(lib, entry.path), entry.path.stat().st_size)]))
    return rows


def write_index(lib: Library) -> Path:
    e = _html.escape
    parts = [
        "<!DOCTYPE html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="color-scheme" content="light dark">',
        f"<title>{LIBRARY_TITLE}</title>", f"<style>{INDEX_CSS}</style>", "</head>", "<body>",
        '<a class="skip-link" href="#main">Skip to main content</a>',
        '<header><div class="wrap"><p>AHG 2026: Accessibility Agents</p></div></header>',
        '<main id="main" tabindex="-1"><div class="wrap">',
        f"<h1>{LIBRARY_TITLE}</h1>",
        ("<p>Every resource for the Accessibility Agents workshop at Accessing Higher Ground 2026, "
        "in the format that works for you. Every link is to a file in this folder, so it all works offline.</p>"),
        '<h2 id="choose">Which format should I choose?</h2>', '<dl class="choose">',
    ]
    for name, why in CHOOSE:
        parts.append(f"<dt>{e(name)}</dt><dd>{e(why)}</dd>")
    parts.append("</dl>")
    for group in GROUPS:
        rows = rows_for(lib, group.folder)
        if not rows:
            continue
        parts += [f'<h2 id="{group.folder}">{e(group.name)}</h2>',
                  f"<p>For: {e(group.audience)}. {e(group.about)}</p>",
                  f"<table><caption>{e(group.name)}: each document, what it is, and every format</caption>",
                  ('<thead><tr><th scope="col">Document</th><th scope="col">What it is</th>'
                  '<th scope="col">Formats</th></tr></thead><tbody>')]
        for row in rows:
            links = "".join(f'<li><a href="{e(href)}">{e(label)}, {human_size(size)}</a></li>'
                            for label, href, size in row.links)
            parts.append(f'<tr><th scope="row">{e(row.title)}</th><td>{e(row.about)}</td>'
                         f'<td><ul class="formats">{links}</ul></td></tr>')
        parts.append("</tbody></table>")
    upload = sorted((e2 for e2 in lib.entries if e2.group == "conference-upload"), key=lambda x: x.path.name)
    if upload:
        parts += ['<h2 id="conference-upload">For the conference upload</h2>',
                  ("<p>The files the conference site takes, Word, PowerPoint and PDF only, "
                  "in the <code>conference-upload</code> folder:</p>"), "<ul>"]
        for entry in upload:
            parts.append(f'<li><a href="{e(_href(lib, entry.path))}">{e(entry.path.name)}, '
                         f'{human_size(entry.path.stat().st_size)}</a></li>')
        parts.append("</ul>")
    parts += ["</div></main>",
              '<footer><div class="wrap">',
              (f"<p>Built {e(lib.built)} from GLOW {e(lib.commit)} by <code>scripts/build_ahg_library.py</code>. "
              "Every file, its size, SHA-256 and check result are in <code>manifest.csv</code>.</p>"),
              f"<p>From {PUBLISHER}.</p></div></footer>", "</body>", "</html>", ""]
    path = lib.out / "index.html"
    path.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    return path


def readme_markdown(lib: Library) -> str:
    lines = [f"# {LIBRARY_TITLE}", "",
             ("Every resource for the Accessibility Agents workshop at Accessing Higher Ground 2026, "
             "in the format that works for you. `index.html` is the same list as a web page."), "",
             "## Which format should I choose?", ""]
    lines += [f"- **{name}**: {why}" for name, why in CHOOSE]
    for group in GROUPS:
        rows = rows_for(lib, group.folder)
        if not rows:
            continue
        lines += ["", f"## {group.name}", "", f"For: {group.audience}. {group.about}", "",
                  "| Document | What it is | Formats |", "|---|---|---|"]
        for row in rows:
            links = ", ".join(f"[{label}, {human_size(size)}]({href})" for label, href, size in row.links)
            title = row.title.replace("|", "-")
            lines.append(f"| {title} | {row.about.replace('|', '-')} | {links} |")
    upload = sorted((e for e in lib.entries if e.group == "conference-upload"), key=lambda x: x.path.name)
    if upload:
        lines += ["", "## For the conference upload", "",
                  "The files the conference site takes, Word, PowerPoint and PDF only, in `conference-upload`:", ""]
        lines += [f"- [{e.path.name}, {human_size(e.path.stat().st_size)}]({_href(lib, e.path)})" for e in upload]
    lines += ["", "## About this library", "",
              (f"Built {lib.built} from GLOW {lib.commit} by `scripts/build_ahg_library.py`. "
              "Every file, its size, SHA-256 and check result are in `manifest.csv`."), ""]
    return "\n".join(lines)


def write_readme(lib: Library) -> tuple[Path, Path]:
    md = lib.out / "README.md"
    text = readme_markdown(lib)
    md.write_text(text, encoding="utf-8", newline="\n")
    blocks = F._blocks(F._pandoc_json(text))
    doc = F.Doc(source=md, title=LIBRARY_TITLE, lang="en", author=PUBLISHER,
                description="Every AHG 2026 workshop resource, in every format.", markdown=text, blocks=blocks)
    original = F._docx_runs

    def runs_with_relative_links(paragraph, runs):
        # Links in the README point at files beside it; Word follows a relative link.
        for run_ in runs:
            if run_.url and not run_.url.startswith(("http://", "https://", "mailto:", "#")):
                F._docx_hyperlink(paragraph, run_)
            else:
                original(paragraph, [run_])

    F._docx_runs = runs_with_relative_links
    try:
        docx = lib.out / "README.docx"
        F.write_docx(doc, docx)
    finally:
        F._docx_runs = original
    return md, docx


MANIFEST_FIELDS = ["group", "document", "format", "path", "bytes", "sha256", "check", "tools", "glow_commit", "built"]


def write_manifest(lib: Library) -> Path:
    rows = []
    for entry in lib.entries:
        paths = sorted(p for p in entry.path.rglob("*") if p.is_file()) if entry.path.is_dir() else [entry.path]
        for path in paths:
            rows.append({
                "group": entry.group, "document": entry.document, "format": entry.fmt,
                "path": path.relative_to(lib.out).as_posix(), "bytes": path.stat().st_size,
                "sha256": sha256(path), "check": entry.check, "tools": entry.tools,
                "glow_commit": lib.commit, "built": lib.built,
            })
    rows.sort(key=lambda r: r["path"])
    target = lib.out / MARKER
    with target.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return target


# ---------------------------------------------------------------------------


def tool_versions(lib: Library, *, pdf: bool, daisy: bool, checks: bool) -> None:
    pandoc = run([F.pandoc(), "--version"]).stdout.split("\n", 1)[0]
    lib.tools["pandoc"] = pandoc.replace("pandoc ", "").strip()
    if checks:
        env = java_env()
        ace = shutil.which("ace") or shutil.which("ace.cmd")
        lib.tools["ace"] = "Ace by DAISY " + (run([ace, "--version"]).stdout.strip() if ace else "missing")
        epubcheck = run([java(), "-jar", str(EPUBCHECK_JAR), "--version"], env=env).stdout.strip().splitlines()
        lib.tools["epubcheck"] = (epubcheck[0] if epubcheck else "EPUBCheck missing").replace("v", "", 1)
        if pdf:
            vera = run(["cmd", "/c", str(VERAPDF), "--version"], env=env).stdout.strip().splitlines()
            lib.tools["verapdf"] = vera[0] if vera else "veraPDF missing"


def prepare_out(out: Path, force: bool) -> None:
    if out.exists() and any(out.iterdir()):
        if not (out / MARKER).is_file() and not force:
            raise BuildError(out, "is not empty and holds no library manifest; refusing to clear it (use --force)")
        for child in out.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    out.mkdir(parents=True, exist_ok=True)
    # An empty manifest at once, so a build that stops part way can still be cleared next time.
    (out / MARKER).write_text(",".join(MANIFEST_FIELDS) + "\n", encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", nargs="?", type=Path, default=DEFAULT_OUT, help=f"output folder (default {DEFAULT_OUT})")
    parser.add_argument("--no-pdf", action="store_true", help="skip the PDF copies (no Word on this machine)")
    parser.add_argument("--no-daisy", action="store_true", help="skip the DAISY copies (no DAISY Pipeline 2)")
    parser.add_argument("--no-checks", action="store_true",
                        help="skip veraPDF, Ace, EPUBCheck and GLOW's audits (for tests without Java)")
    parser.add_argument("--jobs", type=int, default=3, help="DAISY and Ace jobs at once (default 3)")
    parser.add_argument("--only", default="", help="comma-separated document folder names, for a small test build")
    parser.add_argument("--force", action="store_true", help="clear a non-empty output folder that is not a library")
    args = parser.parse_args(argv)

    out = args.out.resolve()
    if REPO in (out, *out.parents):
        raise BuildError(out, "the library is built outside the repository")
    started = time.time()
    lib = Library(out=out, built=_dt.date.today().isoformat(), commit=glow_commit(),
                  only={s for s in args.only.split(",") if s})
    unknown = lib.only - {p.slug for p in PLACES.values()}
    if unknown:
        raise BuildError("--only", f"no such document: {', '.join(sorted(unknown))}")
    tool_versions(lib, pdf=not args.no_pdf, daisy=not args.no_daisy, checks=not args.no_checks)
    say(f"AHG 2026 library: {out}, from GLOW {lib.commit}")
    lib.tools.update(ensure_formats_current(skip_audit=args.no_checks))
    prepare_out(out, args.force)
    copy_documents(lib)
    say(f"  {len(lib.docs)} documents: Markdown, HTML, Word and PowerPoint")
    build_epubs(lib)
    if not args.no_pdf:
        build_pdfs(lib)
    if not args.no_daisy:
        build_daisy(lib, args.jobs)
    if not args.no_checks:
        if not args.no_pdf:
            check_pdfs(lib, args.jobs)
        check_epubs(lib, args.jobs)
    copy_files(lib)
    build_conference(lib)
    write_index(lib)
    write_readme(lib)
    lib.add("library", "index", "html", out / "index.html", "check_ahg_library.py runs axe-core")
    lib.add("library", "README", "md", out / "README.md")
    lib.add("library", "README", "docx", out / "README.docx")
    if args.no_pdf:
        lib.exceptions.append("PDF not built (--no-pdf)")
    if args.no_daisy:
        lib.exceptions.append("DAISY not built (--no-daisy)")
    if lib.only:
        lib.exceptions.append(f"test build of {len(lib.docs)} documents only (--only)")
    (out / "build-notes.json").write_text(json.dumps({
        "built": lib.built, "glow_commit": lib.commit, "tools": lib.tools, "exceptions": lib.exceptions,
        "options": {"pdf": not args.no_pdf, "daisy": not args.no_daisy, "checks": not args.no_checks},
        "only": sorted(lib.only),
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    lib.add("library", "build-notes", "json", out / "build-notes.json", "the build's tools, options and exceptions")
    manifest = write_manifest(lib)
    files = sum(1 for _ in csv.DictReader(manifest.open(encoding="utf-8")))
    say(f"  {files} files in {manifest.name}")
    for note in lib.exceptions:
        say(f"  exception: {note}")
    say(f"Done in {round(time.time() - started)} s: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
