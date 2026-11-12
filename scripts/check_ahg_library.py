#!/usr/bin/env python
"""Check an AHG 2026 resource library built by ``scripts/build_ahg_library.py``.

What it checks, for the library in the folder given (default ``S:\\ahg``):

* every document has every format -- Markdown, HTML, Word, PowerPoint, PDF,
  EPUB, DAISY 2.02 and DAISY 3, all under the document's own base name --
  or the build recorded why not (``build-notes.json``);
* every file is in ``manifest.csv`` with its size and SHA-256, and every row
  of the manifest is a file that is there;
* every link in ``index.html`` and ``README.md`` is relative and resolves;
* ``index.html`` has a skip link, one h1, "Which format should I choose?"
  first, and one h2 per group;
* the conference set holds exactly the files work.md 5.5 names, each a DOC,
  DOCX, PPTX or PDF under 250 MB, named ``ahg-2026-...`` in lowercase;
* axe-core finds no violations in ``index.html`` (and, unless
  ``--index-only``, in every document's HTML copy) in Microsoft Edge at
  1280 and 320 CSS pixels wide, and nothing scrolls sideways.

    python scripts/check_ahg_library.py              # S:\\ahg
    python scripts/check_ahg_library.py D:\\other --no-axe

Exit 1 on any failure, naming each file.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import build_ahg_library as B
import check_ahg_formats as C

AXE_CANDIDATES = (
    REPO / "web" / "node_modules" / "axe-core" / "axe.min.js",
    REPO.parent / "glow" / "web" / "node_modules" / "axe-core" / "axe.min.js",
)
WIDTHS = (1280, 320)
CONFERENCE_NAME = re.compile(r"ahg-2026-[a-z0-9]+(-[a-z0-9]+)*\.(doc|docx|pptx|pdf)")


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.headings: list[tuple[int, str]] = []
        self.skip = False
        self._heading: tuple[int, list[str]] | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if "skip-link" in (a.get("class") or "") and a["href"].startswith("#"):
                self.skip = True
        if re.fullmatch(r"h[1-6]", tag):
            self._heading = (int(tag[1]), [])

    def handle_endtag(self, tag):
        if self._heading and tag == f"h{self._heading[0]}":
            self.headings.append((self._heading[0], "".join(self._heading[1]).strip()))
            self._heading = None

    def handle_data(self, data):
        if self._heading:
            self._heading[1].append(data)


def _resolve(root: Path, base: Path, href: str) -> tuple[bool, str]:
    parts = urlsplit(href)
    if parts.scheme or parts.netloc or href.startswith("/"):
        return False, "not a relative link"
    if not parts.path:
        return True, ""  # a link to a place on the same page
    target = (base.parent / unquote(parts.path)).resolve()
    if root.resolve() not in (target, *target.parents):
        return False, "leaves the library"
    if not target.exists():
        return False, "resolves to nothing"
    return True, ""


def check_layout(root: Path, notes: dict) -> list[str]:
    problems: list[str] = []
    only = set(notes.get("only") or [])
    options = notes.get("options", {})
    for place in B.PLACES.values():
        if only and place.slug not in only:
            continue
        folder = root / place.group / place.slug
        if not folder.is_dir():
            problems.append(f"{folder.relative_to(root).as_posix()}: missing")
            continue
        wanted = ["md", "html", "docx", "pptx", "epub"]
        if options.get("pdf", True):
            wanted.append("pdf")
        for ext in wanted:
            path = folder / f"{place.slug}.{ext}"
            if not path.is_file() or path.stat().st_size == 0:
                problems.append(f"{path.relative_to(root).as_posix()}: missing or empty")
        if options.get("daisy", True):
            if not (folder / "daisy" / "daisy-202" / "ncc.html").is_file():
                problems.append(f"{folder.relative_to(root).as_posix()}/daisy/daisy-202/ncc.html: missing")
            if not list((folder / "daisy" / "daisy-3").glob("*.opf")):
                problems.append(f"{folder.relative_to(root).as_posix()}/daisy/daisy-3: no package file")
        for path in folder.iterdir():
            if path.is_file() and path.stem != place.slug:
                problems.append(f"{path.relative_to(root).as_posix()}: not named {place.slug}.*")
    for name in ("index.html", "README.md", "README.docx", "build-notes.json"):
        if not (root / name).is_file():
            problems.append(f"{name}: missing")
    if not (root / "06-kit" / "ahg-2026-agent-kit.zip").is_file():
        problems.append("06-kit/ahg-2026-agent-kit.zip: missing")
    readme = root / "08-sample-course" / "README.md"
    if not readme.is_file():
        problems.append("08-sample-course/README.md: missing")
    else:
        first = next((line for line in readme.read_text(encoding="utf-8").splitlines()
                      if line.strip() and not line.startswith("#")), "")
        if "planted on purpose" not in first:
            problems.append("08-sample-course/README.md: the first sentence must say the barriers are planted on purpose")
    return problems


def _normalized_target(target: str) -> str:
    parts = urlsplit(unquote(target))
    if parts.scheme in ("http", "https") and parts.netloc and not parts.path:
        parts = parts._replace(path="/")
    return parts.geturl()


def check_document_links(root: Path, notes: dict) -> tuple[list[str], int]:
    """Prove that source destinations survived conversion in each reading format."""
    problems: list[str] = []
    checked = 0
    only = set(notes.get("only") or [])
    for place in B.PLACES.values():
        if only and place.slug not in only:
            continue
        folder = root / place.group / place.slug
        source = folder / f"{place.slug}.md"
        if not source.is_file():
            continue  # check_layout reports the missing document
        expected = C.expected_targets(source.read_text(encoding="utf-8"))
        for extension in ("html", "docx", "pptx", "epub", "pdf", "daisy-202", "daisy-3"):
            path = folder / f"{place.slug}.{extension}"
            if extension.startswith("daisy-"):
                path = folder / "daisy" / extension
            if not path.exists():
                continue  # recorded format exceptions and layout are checked separately
            if extension in ("html", "docx", "pptx"):
                targets = C.hyperlink_targets(path)
            elif extension == "pdf":
                import pymupdf

                with pymupdf.open(path) as document:
                    targets = {link["uri"] for page in document for link in page.get_links() if link.get("uri")}
            else:
                parser = _Links()
                if extension == "epub":
                    with zipfile.ZipFile(path) as archive:
                        for name in archive.namelist():
                            if name.endswith((".xhtml", ".html")):
                                parser.feed(archive.read(name).decode("utf-8"))
                else:
                    for content in path.rglob("*"):
                        if content.suffix.lower() in (".html", ".xhtml", ".xml"):
                            parser.feed(content.read_text(encoding="utf-8"))
                targets = set(parser.links)
            missing = {_normalized_target(target) for target in expected} - {
                _normalized_target(target) for target in targets
            }
            if missing:
                problems.append(f"{path.relative_to(root)}: missing clickable targets: {sorted(missing)}")
            checked += 1
    return problems, checked


def check_manifest(root: Path) -> tuple[list[str], int]:
    problems: list[str] = []
    manifest = root / B.MARKER
    if not manifest.is_file():
        return [f"{B.MARKER}: missing"], 0
    with manifest.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if rows and list(rows[0].keys()) != B.MANIFEST_FIELDS:
        problems.append(f"{B.MARKER}: columns are {list(rows[0].keys())}, not {B.MANIFEST_FIELDS}")
    listed = {}
    for row in rows:
        path = root / row["path"]
        listed[row["path"]] = row
        if not path.is_file():
            problems.append(f"{row['path']}: in the manifest but not in the library")
            continue
        if int(row["bytes"]) != path.stat().st_size:
            problems.append(f"{row['path']}: {path.stat().st_size} bytes, the manifest says {row['bytes']}")
        if B.sha256(path) != row["sha256"]:
            problems.append(f"{row['path']}: SHA-256 differs from the manifest")
        for field in ("group", "format", "glow_commit", "built"):
            if not row.get(field):
                problems.append(f"{row['path']}: no {field} in the manifest")
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and rel != B.MARKER and rel not in listed:
            problems.append(f"{rel}: not in the manifest")
    return problems, len(rows)


def check_links(root: Path) -> tuple[list[str], int]:
    problems: list[str] = []
    count = 0
    index = root / "index.html"
    if index.is_file():
        parser = _Links()
        parser.feed(index.read_text(encoding="utf-8"))
        for href in parser.links:
            count += 1
            ok, why = _resolve(root, index, href)
            if not ok:
                problems.append(f"index.html: {href}: {why}")
        levels = [level for level, _ in parser.headings]
        if levels.count(1) != 1:
            problems.append(f"index.html: {levels.count(1)} h1 elements, not one")
        h2 = [text for level, text in parser.headings if level == 2]
        if not h2 or h2[0] != "Which format should I choose?":
            problems.append("index.html: the first h2 is not 'Which format should I choose?'")
        for group in B.GROUPS:
            if (root / group.folder).is_dir() and group.name not in h2:
                problems.append(f"index.html: no h2 for {group.name}")
        if not parser.skip:
            problems.append("index.html: no skip link")
        if not re.search(r'<html lang="en"', index.read_text(encoding="utf-8")):
            problems.append("index.html: no lang on <html>")
    readme = root / "README.md"
    if readme.is_file():
        for href in re.findall(r"\]\(([^)]+)\)", readme.read_text(encoding="utf-8")):
            count += 1
            ok, why = _resolve(root, readme, href)
            if not ok:
                problems.append(f"README.md: {href}: {why}")
    return problems, count


def check_conference(root: Path, notes: dict) -> tuple[list[str], int]:
    problems: list[str] = []
    folder = root / "conference-upload"
    if not folder.is_dir():
        return ["conference-upload: missing"], 0
    files = sorted(p for p in folder.rglob("*"))
    for path in files:
        if path.is_dir():
            problems.append(f"conference-upload/{path.name}: a folder; the form takes files only")
            continue
        if path.suffix.lower() not in B.CONFERENCE_EXTS:
            problems.append(f"conference-upload/{path.name}: {path.suffix} is not DOC, DOCX, PPTX or PDF")
        if path.stat().st_size >= B.CONFERENCE_LIMIT:
            problems.append(f"conference-upload/{path.name}: 250 MB or more")
        if not CONFERENCE_NAME.fullmatch(path.name):
            problems.append(f"conference-upload/{path.name}: not a plain lowercase ahg-2026- name")
    only = set(notes.get("only") or [])
    expected = {name for rel, ext, name in B.conference_set()
                if (not only or B.PLACES[rel].slug in only)
                and (ext != "pdf" or notes.get("options", {}).get("pdf", True))}
    present = {p.name for p in files if p.is_file()}
    for name in sorted(expected - present):
        problems.append(f"conference-upload/{name}: missing")
    for name in sorted(present - expected):
        problems.append(f"conference-upload/{name}: not in the conference set (work.md 5.5)")
    return problems, len(present)


def _axe_js() -> Path | None:
    return next((p for p in AXE_CANDIDATES if p.is_file()), None)


def check_axe(root: Path, pages: list[Path], axe_js: Path) -> tuple[list[str], str]:
    from playwright.sync_api import sync_playwright

    problems: list[str] = []
    script = axe_js.read_text(encoding="utf-8")
    version = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        try:
            for width in WIDTHS:
                page = browser.new_page(viewport={"width": width, "height": 900})
                for path in pages:
                    rel = path.relative_to(root).as_posix()
                    page.goto(path.resolve().as_uri())
                    page.add_script_tag(content=script)
                    result = page.evaluate("async () => await axe.run(document, {resultTypes: ['violations']})")
                    version = result["testEngine"]["version"]
                    for v in result["violations"]:
                        problems.append(f"{rel} at {width}px: axe {v['id']} ({v['impact']}), {len(v['nodes'])} element(s)")
                    wide = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
                    if wide > 0:
                        problems.append(f"{rel} at {width}px: scrolls sideways by {wide}px")
                page.close()
        finally:
            browser.close()
    return problems, version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", type=Path, default=B.DEFAULT_OUT)
    parser.add_argument("--no-axe", action="store_true", help="skip the browser checks")
    parser.add_argument("--index-only", action="store_true", help="run axe on index.html only")
    parser.add_argument("--axe-js", type=Path, help="path to axe.min.js")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not (root / B.MARKER).is_file():
        print(f"{root}: no {B.MARKER}; not a library")
        return 1

    notes_path = root / "build-notes.json"
    notes = json.loads(notes_path.read_text(encoding="utf-8")) if notes_path.is_file() else {}
    report: list[tuple[str, list[str], str]] = []

    problems = check_layout(root, notes)
    report.append(("Every document in every format", problems, f"{len(problems)} problems"))
    problems, rows = check_manifest(root)
    report.append(("Manifest", problems, f"{rows} files listed"))
    problems, links = check_links(root)
    report.append(("Links in index.html and README.md", problems, f"{links} links"))
    problems, files = check_conference(root, notes)
    report.append(("Conference set", problems, f"{files} files"))
    problems, files = check_document_links(root, notes)
    report.append(("Source hyperlinks in reading formats", problems, f"{files} formats checked"))
    if not args.no_axe:
        axe_js = args.axe_js or _axe_js()
        if axe_js is None:
            report.append(("axe-core", ["axe.min.js not found; pass --axe-js"], ""))
        else:
            pages = [root / "index.html"]
            if not args.index_only:
                pages += sorted(root.glob("0*/*/*.html"))
            problems, version = check_axe(root, pages, axe_js)
            report.append((f"axe-core {version} in Edge at 1280 and 320 px", problems, f"{len(pages)} pages"))

    failed = 0
    for name, problems, detail in report:
        print(f"{'PASS' if not problems else 'FAIL'}  {name}: {detail}")
        for problem in problems:
            print(f"      {problem}")
        failed += bool(problems)
    for note in notes.get("exceptions", []):
        print(f"NOTE  {note}")
    print(f"{len(report) - failed} of {len(report)} checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
