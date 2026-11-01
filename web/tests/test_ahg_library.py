"""The AHG 2026 resource library: scripts/build_ahg_library.py and its checker.

The library is one folder holding every AHG document in every format, built
from GLOW by a script (work.md Part 5). These tests build a small library of
three documents in a temporary folder with Pandoc alone, then check its
layout, manifest, links and conference set with scripts/check_ahg_library.py,
and that the checker notices when any of them is broken.

The parts that need Microsoft Word (PDF), Java (veraPDF, EPUBCheck), Ace by
DAISY or a running DAISY Pipeline 2 engine each skip when that tool is not
on the machine, so CI without them still passes.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import ahg_formats as F  # noqa: E402
import build_ahg_library as B  # noqa: E402
import check_ahg_library as C  # noqa: E402

SMALL = "glossary,7-take-it-home,slides"


def _pandoc_ok() -> bool:
    exe = shutil.which("pandoc")
    if not exe:
        return False
    first = subprocess.run([exe, "--version"], capture_output=True, text=True, check=False).stdout.split("\n", 1)[0]
    found = re.search(r"(\d+)\.(\d+)", first)
    return bool(found) and (int(found.group(1)), int(found.group(2))) >= (3, 1)


needs_pandoc = pytest.mark.skipif(not _pandoc_ok(), reason="needs Pandoc 3.1 or later")


@pytest.fixture(scope="module")
def library(tmp_path_factory) -> Path:
    if not _pandoc_ok():
        pytest.skip("needs Pandoc 3.1 or later")
    out = tmp_path_factory.mktemp("ahg-library")
    code = B.main([str(out), "--only", SMALL, "--no-pdf", "--no-daisy", "--no-checks"])
    assert code == 0
    return out


def _notes(root: Path) -> dict:
    return json.loads((root / "build-notes.json").read_text(encoding="utf-8"))


def _copy(library: Path, tmp_path: Path) -> Path:
    target = tmp_path / "copy"
    shutil.copytree(library, target)
    return target


# ---------------------------------------------------------------------------
# The plan, without building anything
# ---------------------------------------------------------------------------


def test_every_participant_document_has_a_place_in_the_library():
    missing = [rel for rel in F.SOURCES if rel not in B.PLACES]
    assert not missing, f"add these to build_ahg_library.PLACES: {missing}"
    for rel in (B.DECK, *B.FACILITATORS):
        assert rel in B.PLACES


def test_places_are_in_known_groups_with_unique_plain_names():
    folders = {g.folder for g in B.GROUPS}
    slugs = [p.slug for p in B.PLACES.values()]
    assert len(slugs) == len(set(slugs))
    for rel, place in B.PLACES.items():
        assert place.group in folders, rel
        assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", place.slug), place.slug
        assert (F.AHG / rel).is_file(), rel
    assert [g.folder for g in B.GROUPS] == sorted(g.folder for g in B.GROUPS)


def test_facilitator_documents_stay_out_of_the_conference_set():
    for rel in B.FACILITATORS:
        assert B.PLACES[rel].group == "09-facilitators"
    names = {name for _rel, _ext, name in B.conference_set()}
    for rel in B.FACILITATORS:
        assert not any(B.PLACES[rel].slug in name for name in names)


def test_the_conference_set_is_exactly_what_work_md_5_5_names():
    files = B.conference_set()
    names = [name for _rel, _ext, name in files]
    assert len(names) == len(set(names))
    # The deck in three formats and its large print handout in two; the
    # session guide, glossary, plain-language summary, eight step cards and
    # three examples in two.
    assert len(files) == 3 + 2 + 2 * (3 + 8 + 3)
    assert {ext for _rel, ext, _name in files} <= {"docx", "pptx", "pdf"}
    for name in names:
        assert C.CONFERENCE_NAME.fullmatch(name), name
    assert "ahg-2026-slides.pptx" in names
    assert "ahg-2026-slides-large-print-handout.pdf" in names
    assert "ahg-2026-in-plain-language.docx" in names
    assert "ahg-2026-session-guide.pdf" in names


def test_raw_html_in_markdown_reaches_the_epub_as_text():
    ast = [{"t": "Para", "c": [{"t": "Str", "c": "agents/"}, {"t": "RawInline", "c": ["html", "<login>"]}]},
           {"t": "RawBlock", "c": ["html", "<!-- generated -->"]},
           {"t": "Table", "c": [["", [], []], [None, []]]}]
    out = B._raw_html_as_text(ast)
    assert out[0]["c"][1] == {"t": "Str", "c": "<login>"}
    assert len(out) == 2, "an HTML comment is dropped"
    assert out[1]["c"][1] == [None, []], "a null in the AST is kept"


def test_the_library_is_never_built_inside_the_repository():
    with pytest.raises(SystemExit):
        B.main([str(REPO / "docs" / "ahg-library-test"), "--no-pdf", "--no-daisy", "--no-checks"])


def test_ace_report_with_a_list_of_assertions_is_read():
    # Ace 1.4 writes "assertions" as a list; GLOW's EPUB audit used to crash on it.
    from acb_large_print.ace_runner import ace_report_to_findings

    report = {"assertions": [{"assertions": [{
        "earl:test": {"dct:title": "metadata-accessmode", "earl:impact": "serious"},
        "earl:result": {"earl:outcome": "fail", "dct:description": "missing"},
    }]}]}
    assert isinstance(ace_report_to_findings(report), list)


# ---------------------------------------------------------------------------
# A small library, built with Pandoc alone
# ---------------------------------------------------------------------------


@needs_pandoc
def test_small_library_has_the_layout_manifest_links_and_conference_set(library):
    notes = _notes(library)
    assert C.check_layout(library, notes) == []
    problems, rows = C.check_manifest(library)
    assert problems == [] and rows > 20
    problems, links = C.check_links(library)
    assert problems == [] and links > 20
    problems, files = C.check_conference(library, notes)
    assert problems == []
    # The glossary and card 7 as DOCX, the deck as PPTX and DOCX, and the deck's
    # large print handout as DOCX; no PDF in this build.
    assert files == 5


@needs_pandoc
def test_each_document_folder_holds_one_base_name(library):
    folder = library / "01-start-here" / "glossary"
    names = sorted(p.name for p in folder.iterdir())
    assert names == ["glossary.docx", "glossary.epub", "glossary.html", "glossary.md", "glossary.pptx"]
    assert (library / "02-slides" / "slides" / "slides.pptx").is_file()
    assert (library / "06-kit" / "ahg-2026-agent-kit.zip").is_file()
    assert sorted(p.name for p in (library / "07-browser-path").iterdir()) == sorted(
        p.name for p in (F.AHG / "kit" / "any-assistant").glob("*.txt"))


@needs_pandoc
def test_the_sample_course_says_first_that_its_barriers_are_planted(library):
    text = (library / "08-sample-course" / "README.md").read_text(encoding="utf-8")
    first = next(line for line in text.splitlines() if line.strip() and not line.startswith("#"))
    assert "planted on purpose" in first
    assert (library / "08-sample-course" / "psy101-syllabus.docx").read_bytes() == (
        F.AHG / "kit" / "sample-course" / "psy101-syllabus.docx").read_bytes()


@needs_pandoc
def test_the_epub_has_accessibility_metadata_and_no_front_matter(library):
    epub = library / "01-start-here" / "glossary" / "glossary.epub"
    with zipfile.ZipFile(epub) as zf:
        assert zf.infolist()[0].filename == "mimetype"
        assert zf.infolist()[0].compress_type == zipfile.ZIP_STORED
        opf = next(zf.read(n).decode("utf-8") for n in zf.namelist() if n.endswith(".opf"))
        text = "".join(zf.read(n).decode("utf-8") for n in zf.namelist() if n.endswith(".xhtml"))
    for needed in ('property="schema:accessMode">textual<', 'property="schema:accessModeSufficient">textual<',
                   ">structuralNavigation<", ">tableOfContents<", ">readingOrder<",
                   'property="schema:accessibilityHazard">none<', 'property="schema:accessibilitySummary"',
                   ">EPUB Accessibility 1.1 - WCAG 2.2 Level AA<", "<dc:language>en</dc:language>",
                   "<dc:creator", "<dc:title"):
        assert needed in opf, needed
    assert "lang: en" not in text and "description:" not in text, "front matter leaked into the EPUB"
    assert 'href="../styles/' in text or "stylesheet" in text


@needs_pandoc
def test_the_front_door_names_format_and_size_in_every_link(library):
    page = (library / "index.html").read_text(encoding="utf-8")
    assert page.index("Which format should I choose?") < page.index("Start here")
    assert re.search(r">Word, \d+ KB</a>", page)
    assert "http://" not in page and "https://" not in page
    readme = (library / "README.md").read_text(encoding="utf-8")
    assert "## Which format should I choose?" in readme
    assert (library / "README.docx").is_file()


@needs_pandoc
def test_the_checker_catches_a_changed_a_missing_and_an_unlisted_file(library, tmp_path):
    root = _copy(library, tmp_path)
    (root / "01-start-here" / "glossary" / "glossary.html").write_text("changed", encoding="utf-8")
    (root / "01-start-here" / "glossary" / "glossary.epub").unlink()
    (root / "stray.txt").write_text("x", encoding="utf-8")
    problems, _ = C.check_manifest(root)
    joined = "\n".join(problems)
    assert "glossary.html: " in joined and "SHA-256" in joined
    assert "glossary.epub: in the manifest but not in the library" in joined
    assert "stray.txt: not in the manifest" in joined
    assert any("glossary.epub" in p for p in C.check_layout(root, _notes(root)))


@needs_pandoc
def test_the_checker_catches_broken_links_and_a_wrong_conference_file(library, tmp_path):
    root = _copy(library, tmp_path)
    index = root / "index.html"
    index.write_text(index.read_text(encoding="utf-8").replace(
        "01-start-here/glossary/glossary.docx", "01-start-here/glossary/nothing.docx", 1).replace(
        "</main>", '<a href="https://example.org/">away</a></main>', 1), encoding="utf-8")
    problems, _ = C.check_links(root)
    assert any("nothing.docx: resolves to nothing" in p for p in problems)
    assert any("example.org" in p and "not a relative link" in p for p in problems)
    (root / "conference-upload" / "ahg-2026-glossary.epub").write_bytes(b"x")
    problems, _ = C.check_conference(root, _notes(root))
    assert any("not DOC, DOCX, PPTX or PDF" in p for p in problems)


@needs_pandoc
def test_a_rebuild_refuses_to_clear_a_folder_that_is_not_a_library(tmp_path):
    (tmp_path / "keep.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(SystemExit):
        B.prepare_out(tmp_path, force=False)
    assert (tmp_path / "keep.txt").is_file()


@needs_pandoc
def test_the_manifest_columns(library):
    with (library / "manifest.csv").open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames == B.MANIFEST_FIELDS
        rows = list(reader)
    assert {r["group"] for r in rows} >= {"01-start-here", "02-slides", "03-step-cards", "06-kit",
                                         "07-browser-path", "08-sample-course", "conference-upload", "library"}
    assert all(len(r["sha256"]) == 64 for r in rows)


# ---------------------------------------------------------------------------
# The tools CI does not have: each skips when absent
# ---------------------------------------------------------------------------


def _java() -> str | None:
    try:
        return B.java()
    except SystemExit:
        return None


@needs_pandoc
@pytest.mark.skipif(not (B.EPUBCHECK_JAR.is_file() and _java()), reason="needs Java and EPUBCheck")
def test_epubcheck_passes_the_library_epub(library):
    errors, _warnings = B._epubcheck(library / "01-start-here" / "glossary" / "glossary.epub")
    assert errors == 0


@needs_pandoc
@pytest.mark.skipif(not (shutil.which("ace") or shutil.which("ace.cmd")), reason="needs Ace by DAISY")
def test_ace_finds_nothing_serious_in_the_library_epub(library):
    counts = B._ace(library / "01-start-here" / "glossary" / "glossary.epub")
    assert counts["critical"] == 0 and counts["serious"] == 0


def _word() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        return False
    import winreg

    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application")
    except OSError:
        return False
    return True


@needs_pandoc
@pytest.mark.skipif(not (_word() and B.VERAPDF.is_file() and _java()), reason="needs Microsoft Word, Java and veraPDF")
def test_word_pdf_passes_pdf_ua_once_finished(library, tmp_path):
    """Word's export plus finish_pdf_ua is PDF/UA-1 compliant, with no exceptions."""
    root = _copy(library, tmp_path)
    lib = B.Library(out=root, built="2026-10-29", commit="test", only={"glossary"})
    lib.docs = [("kit/glossary.md", B.PLACES["kit/glossary.md"], "Words used today")]
    B.build_pdfs(lib)
    compliant, failed = B._verapdf(root / "01-start-here" / "glossary" / "glossary.pdf", B.java_env())
    assert compliant, failed


def _pipeline_running() -> bool:
    try:
        with urllib.request.urlopen(f"{B.PIPELINE_WS}/alive", timeout=2):
            return True
    except OSError:
        return False


@needs_pandoc
@pytest.mark.skipif(not _pipeline_running(), reason="needs a running DAISY Pipeline 2 engine")
def test_daisy_pipeline_makes_valid_daisy_202_and_3(library, tmp_path):
    root = _copy(library, tmp_path)
    folder = root / "01-start-here" / "glossary"
    work = tmp_path / "work"
    work.mkdir()
    results = B._daisy_one(folder / "glossary.epub", folder, work)
    assert results["daisy-202"].startswith("converter validation pass; daisy202-validator 0 errors")
    assert results["daisy-3"] == "converter validation pass; dtbook-validator 0 errors"
    assert (folder / "daisy" / "daisy-202" / "ncc.html").is_file()
