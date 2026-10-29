#!/usr/bin/env python
"""Every AHG 2026 participant document in Markdown, HTML, Word and PowerPoint.

The owner's rule for the workshop is that every document a participant
receives is theirs in the format they work in. The Markdown file is the
source and stays the one place anyone edits. This module writes the other
three beside it, with the same name:

* ``<name>.html`` -- one standalone page: language and title declared, one
  h1, header cells scoped, wide tables in a focusable scroll region, light
  and dark both defined, nothing loaded from the network.
* ``<name>.docx`` -- ACB large print (GLOW's own template), real Heading
  styles, real list styles, real hyperlinks, table header rows marked to
  repeat, table alt text, title and language set on the file.
* ``<name>.pptx`` -- a reading deck: the document's title slide, then one
  slide per section. Every slide has a real title placeholder and a real
  body placeholder, filled in that order, and every title is unique: a
  section too long for one slide continues on the next as "(2 of 3)". Each
  table gets its own slide, with alt text and a marked header row.

``docs/ahg-2026/formats.json`` records, for each source, the SHA-256 of the
Markdown it was built from. ``web/tests/test_workshop_ahg_formats.py`` fails
when a source changes and its formats were not rebuilt, and checks the
structure of every output. Office files are written with fixed timestamps,
so a rebuild with the same libraries changes nothing.

    python scripts/build_ahg_kit.py --formats-only
    python scripts/ahg_formats.py            # the same, on its own

Pandoc reads the Markdown (it is what GLOW already uses to show the kit
online). python-docx and python-pptx write the Office files.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import html as _html
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AHG = REPO / "docs" / "ahg-2026"
MANIFEST = AHG / "formats.json"

# Every document a participant receives, relative to docs/ahg-2026. The
# inventory in docs/ahg-2026/formats.md says why each one is here and why
# everything else is not.
SOURCES: tuple[str, ...] = (
    "pre-event-message.md",
    "workshop-frontfacing-guide.md",
    "kit/README.md",
    "kit/agent-file-principles.md",
    "kit/accessibility-agents.md",
    "kit/accessibility-agents-in-the-kit.md",
    "kit/step-cards/0-before-the-day.md",
    "kit/step-cards/1-why-we-are-here.md",
    "kit/step-cards/2-design-your-agent.md",
    "kit/step-cards/3-your-agent-at-work.md",
    "kit/step-cards/4-ground-it.md",
    "kit/step-cards/5-build-the-office.md",
    "kit/step-cards/6-share-it.md",
    "kit/step-cards/7-take-it-home.md",
    "kit/examples/jordan-faculty-coach.md",
    "kit/examples/maria-alternate-format-planner.md",
    "kit/examples/sam-remediation-log-keeper.md",
    "repo/README.md",
)

FORMATS = (".html", ".docx", ".pptx")

# Office files carry this date, not the build time, so rebuilding changes
# nothing that the Markdown did not change.
FIXED = _dt.datetime(2026, 10, 1, 12, 0, 0)

FONT = "Arial"


# ---------------------------------------------------------------------------
# Reading the Markdown
# ---------------------------------------------------------------------------


@dataclass
class Run:
    text: str
    bold: bool = False
    code: bool = False
    url: str = ""


@dataclass
class Block:
    kind: str  # heading, para, list, code, quote, table, rule
    level: int = 0
    runs: list[Run] = field(default_factory=list)
    ordered: bool = False
    items: list[list[Block]] = field(default_factory=list)
    text: str = ""
    header: list[list[Run]] = field(default_factory=list)
    rows: list[list[list[Run]]] = field(default_factory=list)
    children: list[Block] = field(default_factory=list)


@dataclass
class Doc:
    source: Path
    title: str
    lang: str
    author: str
    description: str
    markdown: str
    blocks: list[Block]


def split_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines()
    end = lines.index("---", 1)
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta, "\n".join(lines[end + 1:]).lstrip("\n")


def pandoc() -> str:
    exe = shutil.which("pandoc")
    if not exe:
        sys.exit("Pandoc is needed to build the AHG formats: https://pandoc.org/installing.html")
    return exe


def _pandoc_json(markdown: str) -> list:
    done = subprocess.run(
        [pandoc(), "-f", "gfm-raw_html-task_lists", "-t", "json"],
        input=markdown.encode("utf-8"), capture_output=True, check=True,
    )
    return json.loads(done.stdout.decode("utf-8"))["blocks"]


def _inlines(items: list, *, bold: bool = False, url: str = "") -> list[Run]:
    out: list[Run] = []
    for node in items:
        t, c = node["t"], node.get("c")
        if t == "Str":
            out.append(Run(c, bold=bold, url=url))
        elif t in ("Space", "SoftBreak", "LineBreak"):
            out.append(Run(" ", bold=bold, url=url))
        elif t in ("Strong", "Emph", "Underline"):
            # ACB large print: emphasis is bold, never italic.
            out += _inlines(c, bold=True, url=url)
        elif t in ("Strikeout", "Superscript", "Subscript", "SmallCaps", "Span"):
            out += _inlines(c[-1] if t == "Span" else c, bold=bold, url=url)
        elif t == "Code":
            out.append(Run(c[1], bold=bold, code=True, url=url))
        elif t == "Link":
            out += _inlines(c[1], bold=bold, url=c[2][0])
        elif t == "Quoted":
            q = '"' if c[0]["t"] == "DoubleQuote" else "'"
            out.append(Run(q, bold=bold, url=url))
            out += _inlines(c[1], bold=bold, url=url)
            out.append(Run(q, bold=bold, url=url))
        elif t == "Image":
            raise ValueError("An image in a participant document needs a figure with alt text; add support first")
        elif t == "RawInline":
            out.append(Run(c[1], bold=bold, url=url))
    # Merge neighbours that look the same, so Word and PowerPoint get whole runs.
    merged: list[Run] = []
    for run in out:
        if merged and (merged[-1].bold, merged[-1].code, merged[-1].url) == (run.bold, run.code, run.url):
            merged[-1].text += run.text
        else:
            merged.append(run)
    return merged


def _cell(cell: list) -> list[Run]:
    runs: list[Run] = []
    for block in cell[4]:
        if block["t"] in ("Plain", "Para"):
            if runs:
                runs.append(Run(" "))
            runs += _inlines(block["c"])
    return runs


def _blocks(items: list) -> list[Block]:
    out: list[Block] = []
    for node in items:
        t, c = node["t"], node.get("c")
        if t == "Header":
            out.append(Block("heading", level=c[0], runs=_inlines(c[2])))
        elif t in ("Para", "Plain"):
            out.append(Block("para", runs=_inlines(c)))
        elif t == "BulletList":
            out.append(Block("list", items=[_blocks(i) for i in c]))
        elif t == "OrderedList":
            out.append(Block("list", ordered=True, items=[_blocks(i) for i in c[1]]))
        elif t == "CodeBlock":
            out.append(Block("code", text=c[1]))
        elif t == "BlockQuote":
            out.append(Block("quote", children=_blocks(c)))
        elif t == "HorizontalRule":
            out.append(Block("rule"))
        elif t == "Table":
            head = c[3][1]
            header = [_cell(cell) for cell in head[0][1]] if head else []
            rows = []
            for body in c[4]:
                for row in body[3]:
                    rows.append([_cell(cell) for cell in row[1]])
            out.append(Block("table", header=header, rows=rows))
        elif t == "Div":
            out += _blocks(c[1])
        elif t == "LineBlock":
            for line in c:
                out.append(Block("para", runs=_inlines(line)))
    return out


def plain(runs: list[Run]) -> str:
    return "".join(r.text for r in runs).strip()


def read(rel: str) -> Doc:
    source = AHG / rel
    markdown = source.read_text(encoding="utf-8").replace("\r\n", "\n")
    meta, body = split_front_matter(markdown)
    blocks = _blocks(_pandoc_json(body))
    h1 = [b for b in blocks if b.kind == "heading" and b.level == 1]
    if len(h1) != 1:
        sys.exit(f"{rel}: needs exactly one top-level heading, has {len(h1)}")
    title = meta.get("title") or plain(h1[0].runs)
    return Doc(
        source=source, title=title, lang=meta.get("lang", "en"),
        author=meta.get("author", "Community Access"),
        description=meta.get("description", ""), markdown=markdown, blocks=blocks,
    )


def office_lang(lang: str) -> str:
    return {"en": "en-US"}.get(lang, lang)


def source_hash(markdown: str) -> str:
    return hashlib.sha256(markdown.replace("\r\n", "\n").encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="$lang$" xml:lang="$lang$">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="author" content="$author-meta$">
<meta name="description" content="$description-meta$">
<title>$pagetitle$</title>
<style>
:root { color-scheme: light dark; --bg: #ffffff; --fg: #1a1a1a; --link: #0b57d0; --rule: #6b6b6b; --code-bg: #f2f2f2; --focus: #b3261e; }
@media (prefers-color-scheme: dark) { :root { --bg: #121212; --fg: #f1f1f1; --link: #a8c7fa; --rule: #9a9a9a; --code-bg: #262626; --focus: #ffb4ab; } }
html { font-size: 112.5%; }
body { background: var(--bg); color: var(--fg); font-family: Arial, Helvetica, sans-serif; line-height: 1.5; max-width: 46rem; margin: 0 auto; padding: 1rem; }
a { color: var(--link); text-decoration: underline; }
a:focus-visible, [tabindex]:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
h1, h2, h3, h4 { line-height: 1.25; }
code, pre { font-family: Consolas, "Courier New", monospace; background: var(--code-bg); }
pre { padding: 0.75rem; overflow-x: auto; white-space: pre-wrap; }
table { border-collapse: collapse; margin: 1rem 0; }
th, td { border: 1px solid var(--rule); padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }
.table-scroll { overflow-x: auto; }
blockquote { border-left: 4px solid var(--rule); margin-left: 0; padding-left: 1rem; }
@media print { body { max-width: none; } a { color: inherit; } }
</style>
</head>
<body>
<main>
$body$
</main>
</body>
</html>
"""


def write_html(doc: Doc, target: Path) -> None:
    _meta, body = split_front_matter(doc.markdown)
    with tempfile.TemporaryDirectory() as tmp:
        template = Path(tmp) / "ahg.html"
        template.write_text(HTML_TEMPLATE, encoding="utf-8")
        done = subprocess.run(
            [pandoc(), "-f", "gfm-raw_html", "-t", "html5", "--standalone", "--wrap=none",
             f"--template={template}",
             "--metadata", f"pagetitle={doc.title}", "--metadata", f"lang={doc.lang}",
             "--metadata", f"author-meta={doc.author}", "--metadata", f"description-meta={doc.description}"],
            input=body.encode("utf-8"), capture_output=True, check=True,
        )
    page = done.stdout.decode("utf-8").replace("\r\n", "\n")
    # Pandoc gives each line of a highlighted code block an empty, hidden
    # anchor; a link with no text is noise, so they go.
    page = re.sub(r'<a href="#cb\d+-\d+"[^>]*></a>', "", page)
    # Column headers say which way they apply, and a wide table scrolls in
    # its own named region instead of widening the page (WCAG 1.4.10).
    page = re.sub(r"<th(?=[ >])(?![^>]*\bscope=)", '<th scope="col"', page)
    count = 0

    def wrap(_m: re.Match) -> str:
        nonlocal count
        count += 1
        return f'<div class="table-scroll" role="region" aria-label="Table {count}" tabindex="0">\n<table>'

    page = re.sub(r"<table>", wrap, page).replace("</table>", "</table>\n</div>")
    target.write_text(page, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------


def _docx_hyperlink(paragraph, run: Run) -> None:
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    r_id = paragraph.part.relate_to(run.url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), r_id)
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    style = OxmlElement("w:rStyle")
    style.set(qn("w:val"), "Hyperlink")
    rpr.append(style)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rpr.append(underline)
    if run.bold:
        rpr.append(OxmlElement("w:b"))
    r.append(rpr)
    text = OxmlElement("w:t")
    text.text = run.text
    text.set(qn("xml:space"), "preserve")
    r.append(text)
    link.append(r)
    paragraph._p.append(link)


def _docx_runs(paragraph, runs: list[Run]) -> None:
    for run in runs:
        if run.url.startswith(("http://", "https://", "mailto:")):
            _docx_hyperlink(paragraph, run)
            continue
        r = paragraph.add_run(run.text)
        r.bold = run.bold or None


class _Numbering:
    """Each numbered list starts again at 1; Word's List Number style would not."""

    def __init__(self, doc):
        self.doc = doc

    def restart(self) -> int:
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        style_num = self.doc.styles["List Number"].element.pPr.numPr.numId.val
        numbering = self.doc.part.numbering_part.element
        nums = numbering.findall(qn("w:num"))
        abstract = next(n for n in nums if n.get(qn("w:numId")) == str(style_num))
        abstract_id = abstract.find(qn("w:abstractNumId")).get(qn("w:val"))
        new_id = max(int(n.get(qn("w:numId"))) for n in nums) + 1
        num = OxmlElement("w:num")
        num.set(qn("w:numId"), str(new_id))
        ref = OxmlElement("w:abstractNumId")
        ref.set(qn("w:val"), abstract_id)
        num.append(ref)
        override = OxmlElement("w:lvlOverride")
        override.set(qn("w:ilvl"), "0")
        start = OxmlElement("w:startOverride")
        start.set(qn("w:val"), "1")
        override.append(start)
        num.append(override)
        numbering.append(num)
        return new_id


def _docx_table(doc, block: Block, caption: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    cols = max(len(block.header), *(len(r) for r in block.rows)) if block.rows else len(block.header)
    table = doc.add_table(rows=1 + len(block.rows), cols=cols)
    table.style = "Table Grid"
    for i, runs in enumerate(block.header):
        cell = table.rows[0].cells[i]
        paragraph = cell.paragraphs[0]
        _docx_runs(paragraph, [Run(r.text, bold=True, code=r.code, url=r.url) for r in runs])
    # The header row is announced as one and repeats on every page.
    tr_pr = table.rows[0]._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)
    for r_index, row in enumerate(block.rows, start=1):
        for c_index, runs in enumerate(row):
            _docx_runs(table.rows[r_index].cells[c_index].paragraphs[0], runs)
    # Alt text for the table: Word's Table Properties, Alt Text.
    tbl_pr = table._tbl.tblPr
    for tag, value in (("w:tblCaption", caption), ("w:tblDescription", f"Table: {caption}, {len(block.rows)} rows")):
        el = OxmlElement(tag)
        el.set(qn("w:val"), value)
        tbl_pr.append(el)


def write_docx(doc: Doc, target: Path) -> None:
    from acb_large_print.template import apply_acb_large_print
    from docx import Document
    from docx.shared import Inches

    from docx.oxml.ns import qn

    word = apply_acb_large_print(Document(), title=doc.title, lang=office_lang(doc.lang))
    props = word.core_properties
    props.author = doc.author
    props.subject = doc.description
    props.last_modified_by = doc.author
    props.created = FIXED
    props.modified = FIXED
    props.revision = 1
    numbering = _Numbering(word)
    styles = {s.name for s in word.styles}
    last_heading = doc.title

    def list_style(ordered: bool, depth: int) -> str:
        base = "List Number" if ordered else "List Bullet"
        name = base if depth == 0 else f"{base} {min(depth + 1, 3)}"
        return name if name in styles else base

    def emit(blocks: list[Block], depth: int = 0, quote: bool = False) -> None:
        nonlocal last_heading
        for block in blocks:
            if block.kind == "heading":
                word.add_heading(plain(block.runs), level=min(block.level, 9))
                last_heading = plain(block.runs)
            elif block.kind == "para":
                # ACB large print sets nothing in from the margin, quotes
                # included: an indent is where a magnified view loses text.
                _docx_runs(word.add_paragraph(), block.runs)
            elif block.kind == "list":
                num_id = numbering.restart() if block.ordered else None
                for item in block.items:
                    first, rest = (item[0], item[1:]) if item and item[0].kind == "para" else (Block("para"), item)
                    p = word.add_paragraph(style=list_style(block.ordered, depth))
                    if num_id is not None:
                        num_pr = p._p.get_or_add_pPr().get_or_add_numPr()
                        num_pr.get_or_add_ilvl().val = 0
                        num_pr.get_or_add_numId().val = num_id
                    _docx_runs(p, first.runs)
                    for child in rest:
                        if child.kind == "list":
                            emit([child], depth + 1)
                        else:
                            emit([child], depth, quote=True)
            elif block.kind == "code":
                # One paragraph, its lines kept by line breaks: an agent
                # file's "# Role" or "- Never" lines are text to copy, not
                # this document's headings or lists.
                p = word.add_paragraph()
                for n, line in enumerate(block.text.splitlines() or [""]):
                    r = p.add_run(line)
                    if n:
                        r._r.addprevious(r._r.makeelement(qn("w:br"), {}))
            elif block.kind == "quote":
                emit(block.children, depth, quote=True)
            elif block.kind == "table":
                _docx_table(word, block, last_heading)
                word.add_paragraph()
            # A horizontal rule carries no meaning a heading does not already give.

    emit(doc.blocks)
    word.save(target)
    _fix_zip_dates(target)


# ---------------------------------------------------------------------------
# PowerPoint
# ---------------------------------------------------------------------------

# A body placeholder at 20pt Arial on a 16:9 slide holds about this much.
CHARS_PER_LINE = 80
LINES_PER_SLIDE = 12
TABLE_LINES_PER_SLIDE = 11
CODE_LINES = 8


@dataclass
class Line:
    runs: list[Run]
    level: int = 0
    number: int = 0  # 0 = bullet or plain
    bullet: bool = False
    code: bool = False


@dataclass
class SlideSpec:
    title: str
    lines: list[Line] = field(default_factory=list)
    table: Block | None = None
    table_caption: str = ""


def _lines_needed(line: Line) -> int:
    if line.code:
        return sum(max(1, math.ceil(len(r.text) / CHARS_PER_LINE)) for r in line.runs)
    return max(1, math.ceil(len(plain(line.runs)) / (CHARS_PER_LINE - 6 * line.level)))


def _flatten(blocks: list[Block], level: int = 0) -> list[Line | Block]:
    out: list[Line | Block] = []
    for block in blocks:
        if block.kind == "para":
            out.append(Line(block.runs, level=level))
        elif block.kind == "list":
            for n, item in enumerate(block.items, start=1):
                first, rest = (item[0], item[1:]) if item and item[0].kind == "para" else (Block("para"), item)
                out.append(Line(first.runs, level=level + 1, number=n if block.ordered else 0, bullet=not block.ordered))
                out += _flatten(rest, level + 1)
        elif block.kind == "code":
            # Lines of an agent file are kept together, a few to a paragraph
            # joined by line breaks, so "- Never" is not taken for a list.
            # A chunk never starts on a "- " line, which would read as a
            # typed bullet: it carries on to the end of that list instead.
            lines = block.text.splitlines()
            chunk: list[str] = []
            for text in lines:
                if len(chunk) >= CODE_LINES and not text.lstrip().startswith(("- ", "* ")):
                    out.append(Line([Run(t, code=True) for t in chunk], level=level, code=True))
                    chunk = []
                chunk.append(text)
            if chunk:
                out.append(Line([Run(t, code=True) for t in chunk], level=level, code=True))
        elif block.kind == "quote":
            out += _flatten(block.children, level + 1)
        elif block.kind == "table":
            out.append(block)
    return out


def plan_slides(doc: Doc) -> list[SlideSpec]:
    """Sections become slides; long ones continue; every title is unique."""
    sections: list[tuple[str, list[Block]]] = []
    h2 = ""
    current: tuple[str, list[Block]] | None = None
    intro: list[Block] = []
    for block in doc.blocks:
        if block.kind == "heading" and block.level == 1:
            continue
        if block.kind == "heading" and block.level == 2:
            h2 = plain(block.runs)
            current = (h2, [])
            sections.append(current)
        elif block.kind == "heading":
            name = plain(block.runs)
            current = (f"{h2}: {name}" if h2 else name, [])
            sections.append(current)
        elif current is None:
            intro.append(block)
        else:
            current[1].append(block)
    if intro:
        sections.insert(0, ("About this document", intro))

    specs: list[SlideSpec] = []
    for title, blocks in sections:
        group: list[SlideSpec] = []
        page = SlideSpec(title)
        used = 0
        for item in _flatten(blocks):
            if isinstance(item, Block):  # a table: its own slides
                if page.lines:
                    group.append(page)
                page = SlideSpec(title)
                used = 0
                chunk: list[list[list[Run]]] = []
                chunk_lines = 1 + _row_lines(item.header, len(item.header))
                for row in item.rows:
                    need = _row_lines(row, len(item.header))
                    if chunk and chunk_lines + need > TABLE_LINES_PER_SLIDE:
                        group.append(SlideSpec(title, table=Block("table", header=item.header, rows=chunk), table_caption=title))
                        chunk, chunk_lines = [], 1 + _row_lines(item.header, len(item.header))
                    chunk.append(row)
                    chunk_lines += need
                group.append(SlideSpec(title, table=Block("table", header=item.header, rows=chunk), table_caption=title))
                continue
            need = _lines_needed(item)
            if page.lines and used + need > LINES_PER_SLIDE:
                group.append(page)
                page = SlideSpec(title)
                used = 0
            page.lines.append(item)
            used += need
        if page.lines or not group:
            group.append(page)
        if len(group) > 1:
            for n, spec in enumerate(group, start=1):
                spec.title = f"{title} ({n} of {len(group)})"
        specs += group

    seen: dict[str, int] = {}
    for spec in specs:
        if spec.title in seen:
            seen[spec.title] += 1
            spec.title = f"{spec.title}, part {seen[spec.title]}"
        else:
            seen[spec.title] = 1
    return specs


def _row_lines(row: list[list[Run]], cols: int) -> int:
    width = max(10, (CHARS_PER_LINE + 10) // max(1, cols))
    return max((max(1, math.ceil(len(plain(cell)) / width)) for cell in row), default=1)


def _set_lang(run, lang: str) -> None:
    run.font._rPr.set("lang", lang)


def _pptx_runs(paragraph, runs: list[Run], *, size: int, lang: str, bold: bool = False) -> None:
    from pptx.util import Pt

    if not runs:
        runs = [Run("")]
    for item in runs:
        r = paragraph.add_run()
        r.text = item.text
        r.font.size = Pt(size)
        r.font.name = "Consolas" if item.code else FONT
        r.font.bold = bold or item.bold
        if item.url.startswith(("http://", "https://", "mailto:")):
            r.hyperlink.address = item.url
        _set_lang(r, lang)


def _no_bullet(paragraph, level: int) -> None:
    from pptx.oxml.ns import qn

    p_pr = paragraph._p.get_or_add_pPr()
    if level == 0:
        p_pr.set("marL", "0")
        p_pr.set("indent", "0")
    p_pr.insert(0, p_pr.makeelement(qn("a:buNone"), {}))


def _alt_text(shape, text: str) -> None:
    element = shape._element
    for holder_name in ("nvGraphicFramePr", "nvSpPr", "nvPicPr"):
        holder = getattr(element, holder_name, None)
        if holder is not None and getattr(holder, "cNvPr", None) is not None:
            holder.cNvPr.set("descr", text)
            return


def _place(slide, Inches) -> None:
    for placeholder in slide.placeholders:
        is_title = placeholder.placeholder_format.idx == 0
        placeholder.left = Inches(0.6)
        placeholder.width = Inches(12.1)
        placeholder.top = Inches(0.4) if is_title else Inches(1.7)
        placeholder.height = Inches(1.2) if is_title else Inches(5.4)


def _title(slide, text: str, lang: str, size: int = 36) -> None:
    frame = slide.shapes.title.text_frame
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    _pptx_runs(paragraph, [Run(text)], size=size, lang=lang, bold=True)


def write_pptx(doc: Doc, target: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches, Pt

    lang = office_lang(doc.lang)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    props = prs.core_properties
    props.title = doc.title
    props.subject = doc.description
    props.author = doc.author
    props.last_modified_by = doc.author
    props.language = lang
    props.created = FIXED
    props.modified = FIXED
    props.revision = 1

    # The title slide: the document's name, and what it is.
    first = prs.slides.add_slide(prs.slide_layouts[0])
    for placeholder in first.placeholders:
        is_title = placeholder.placeholder_format.idx == 0
        placeholder.left = Inches(0.8)
        placeholder.width = Inches(11.7)
        placeholder.top = Inches(1.6) if is_title else Inches(4.0)
        placeholder.height = Inches(2.2) if is_title else Inches(2.4)
    _title(first, doc.title, lang, size=40)
    subtitle = first.placeholders[1].text_frame
    subtitle.word_wrap = True
    _pptx_runs(subtitle.paragraphs[0], [Run(doc.description or doc.author)], size=24, lang=lang)

    for spec in plan_slides(doc):
        if spec.table is not None:
            slide = prs.slides.add_slide(prs.slide_layouts[5])  # title only
            _place(slide, Inches)
            _title(slide, spec.title, lang)
            block = spec.table
            cols = len(block.header)
            rows = 1 + len(block.rows)
            frame = slide.shapes.add_table(rows, cols, Inches(0.6), Inches(1.7), Inches(12.1), Inches(min(5.4, 0.5 * rows)))
            table = frame.table
            table.first_row = True
            for c, runs in enumerate(block.header):
                cell = table.cell(0, c)
                _pptx_runs(cell.text_frame.paragraphs[0], runs, size=18, lang=lang, bold=True)
            for r, row in enumerate(block.rows, start=1):
                for c in range(cols):
                    runs = row[c] if c < len(row) else [Run("")]
                    cell = table.cell(r, c)
                    cell.text_frame.word_wrap = True
                    _pptx_runs(cell.text_frame.paragraphs[0], runs, size=18, lang=lang)
            _alt_text(frame, f"Table: {spec.table_caption}. Columns: {', '.join(plain(h) for h in block.header)}.")
            continue

        slide = prs.slides.add_slide(prs.slide_layouts[1])  # title and content
        _place(slide, Inches)
        _title(slide, spec.title, lang)
        body = next(p for p in slide.placeholders if p.placeholder_format.idx != 0)
        frame = body.text_frame
        frame.word_wrap = True
        for i, line in enumerate(spec.lines):
            paragraph = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
            level = min(line.level, 4)
            paragraph.level = level
            runs = list(line.runs)
            if line.number:
                runs.insert(0, Run(f"{line.number}. "))
            if not line.bullet:
                _no_bullet(paragraph, level)
            if line.code:
                for n, run in enumerate(runs):
                    if n:
                        paragraph.add_line_break()
                    _pptx_runs(paragraph, [run], size=18, lang=lang)
                continue
            _pptx_runs(paragraph, runs, size=20, lang=lang)
        frame.auto_size = None
        for paragraph in frame.paragraphs:
            paragraph.space_after = Pt(6)

    prs.save(target)
    _fix_zip_dates(target)


# ---------------------------------------------------------------------------


def _fix_zip_dates(path: Path) -> None:
    """Rewrite an Office file with fixed entry dates, so rebuilds are byte-stable."""
    with zipfile.ZipFile(path) as zf:
        entries = [(info, zf.read(info.filename)) for info in zf.infolist()]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for info, data in entries:
            fixed = zipfile.ZipInfo(info.filename, date_time=FIXED.timetuple()[:6])
            fixed.compress_type = zipfile.ZIP_DEFLATED
            fixed.external_attr = info.external_attr
            zf.writestr(fixed, data)


def output_stem(rel: str) -> str:
    """Where a source's other formats go: beside it, with the same name.

    Except a README: GitHub and VS Code each pick one README to show, and an
    HTML README can win. Its copies are read-me.* instead.
    """
    folder, _, name = rel.rpartition("/")
    stem = "read-me" if name == "README.md" else name[:-3]
    return f"{folder}/{stem}" if folder else stem


def outputs_for(rel: str) -> list[str]:
    return [output_stem(rel) + ext for ext in FORMATS]


def build(only: list[str] | None = None) -> list[Path]:
    written: list[Path] = []
    manifest: dict[str, dict] = {}
    if MANIFEST.is_file():
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8")).get("documents", {})
    for rel in SOURCES:
        if only and rel not in only:
            continue
        doc = read(rel)
        stem = AHG / output_stem(rel)
        write_html(doc, stem.with_suffix(".html"))
        write_docx(doc, stem.with_suffix(".docx"))
        write_pptx(doc, stem.with_suffix(".pptx"))
        manifest[rel] = {
            "title": doc.title,
            "sha256": source_hash(doc.markdown),
            "formats": [Path(p).name for p in [rel] + outputs_for(rel)],
            "slides": 1 + len(plan_slides(doc)),
        }
        written += [stem.with_suffix(ext) for ext in FORMATS]
    manifest = {rel: manifest[rel] for rel in SOURCES if rel in manifest}
    MANIFEST.write_text(json.dumps({
        "about": "Written by scripts/ahg_formats.py. The SHA-256 of each Markdown source its HTML, Word and PowerPoint files were built from. Do not edit; rebuild.",
        "documents": manifest,
    }, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    return written


def main() -> int:
    for path in build(sys.argv[1:] or None):
        print(f"  {path.relative_to(REPO)}")
    print(f"  {MANIFEST.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
