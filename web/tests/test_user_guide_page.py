"""The user guide is one edition, numbered in order, and every link into it lands (#147).

``docs/user-guide.md`` once held two editions of itself, and the served page
(``templates/partials/guide_body.html``, built from it by
``scripts/build-doc-pages.py``) showed most sections twice under two numbering
schemes. These tests pin what was fixed:

* the served page has exactly one ``<h1>`` (the page template's) and no
  earlier edition;
* the numbered sections run 1, 2, 3 ... with no gap and no repeat;
* every ``#fragment`` link on the page, and every link into the guide from
  another template, names an id that exists;
* the committed partial is what the generator builds from the Markdown, so the
  two cannot drift apart again.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

from acb_large_print_web.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "web" / "src" / "acb_large_print_web" / "templates"
PARTIAL = TEMPLATES / "partials" / "guide_body.html"
SOURCE = REPO_ROOT / "docs" / "user-guide.md"


@pytest.fixture(scope="module")
def guide_html() -> str:
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    resp = app.test_client().get("/guide/")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def _ids(html: str) -> set[str]:
    return set(re.findall(r'\sid="([^"]+)"', html))


def test_guide_page_has_one_h1(guide_html):
    assert len(re.findall(r"<h1[\s>]", guide_html)) == 1


def test_guide_page_has_no_repeated_section_heading(guide_html):
    h2s = [re.sub(r"<[^>]+>", "", t).strip() for t in re.findall(r"<h2[^>]*>(.*?)</h2>", guide_html, re.S)]
    repeated = sorted({t for t in h2s if h2s.count(t) > 1})
    assert not repeated, f"level-two headings that appear more than once: {repeated}"


def _without_code(md: str) -> str:
    return re.sub(r"^```.*?^```", "", md, flags=re.M | re.S)


def test_guide_has_one_edition():
    md = SOURCE.read_text(encoding="utf-8")
    titles = re.findall(r"^# ", _without_code(md), flags=re.M)
    assert len(titles) == 1, "Markdown must have one level-one heading"
    for text in (md, PARTIAL.read_text(encoding="utf-8")):
        assert "Earlier edition of this guide" not in text
        assert "Quick Start (Beginner Path)" not in text


def test_numbered_sections_are_in_order():
    md = SOURCE.read_text(encoding="utf-8")
    numbers = [int(n) for n in re.findall(r"^## (\d+)\. ", md, flags=re.M)]
    assert numbers == list(range(1, len(numbers) + 1)), numbers


def test_contents_list_matches_the_numbered_sections():
    md = SOURCE.read_text(encoding="utf-8")
    headings = re.findall(r"^## (\d+\. .+)$", md, flags=re.M)
    contents = md.split("## In This Guide", 1)[1].split("\n---", 1)[0]
    entries = re.findall(r"^\d+\. \[(.+?)\]\(#", contents, flags=re.M)
    assert [h.split(". ", 1)[1] for h in headings] == entries


def test_every_fragment_link_on_the_guide_page_resolves(guide_html):
    ids = _ids(guide_html)
    missing = sorted({frag for frag in re.findall(r'href="#([^"]+)"', guide_html) if frag not in ids})
    assert not missing, f"links to ids that do not exist: {missing}"


def test_links_into_the_guide_from_other_templates_resolve():
    ids = _ids(PARTIAL.read_text(encoding="utf-8"))
    pattern = re.compile(r"url_for\('guide\.guide_page'\)\s*(?:\}\}|\+\s*')#([A-Za-z0-9_-]+)")
    found = {}
    for path in TEMPLATES.rglob("*.html"):
        for frag in pattern.findall(path.read_text(encoding="utf-8")):
            found.setdefault(frag, []).append(path.name)
    assert found, "expected templates that link into the guide"
    missing = {frag: files for frag, files in found.items() if frag not in ids}
    assert not missing, f"guide anchors that do not exist: {missing}"
    faq = (TEMPLATES / "partials" / "faq_body.html").read_text(encoding="utf-8")
    for frag in re.findall(r'href="/guide/#([^"]+)"', faq):
        assert frag in ids, frag


def test_committed_partial_matches_the_markdown():
    pytest.importorskip("markdown")
    spec = importlib.util.spec_from_file_location("build_doc_pages", REPO_ROOT / "scripts" / "build-doc-pages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.render("guide") == PARTIAL.read_text(encoding="utf-8"), (
        "guide_body.html is out of date: run `python scripts/build-doc-pages.py guide`"
    )
