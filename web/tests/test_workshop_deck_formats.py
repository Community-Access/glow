"""The deck in four formats, from one source, each one actually accessible.

"Send me the slides" has a different answer at every institution, and a deck
that only exists as a web page cannot be opened by the person who needs it in
Word with their own screen reader settings applied. So: HTML, Markdown, Word
and PowerPoint, all rendered from ``workshop_deck.build_slides`` so the
sentences cannot diverge.

These tests check the accessibility properties that are easy to lose and
invisible when lost: real heading styles, real list styles, a marked table
header row, a declared language, a real title placeholder on every slide, and
speaker notes in the notes slide rather than dumped on the slide itself.
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web import workshop_agenda as agenda
from acb_large_print_web import workshop_deck as deck
from acb_large_print_web.app import create_app
from acb_large_print_web.workshop_store import ensure_session

CODE = "formatdemo"


@pytest.fixture()
def ctx() -> deck.DeckContext:
    return deck.DeckContext(
        code_label=CODE,
        join_display=f"letitglow.app/w/{CODE}",
        activity_times=tuple(f"{b.minutes} minutes" for b in agenda.activity_blocks()),
    )


@pytest.fixture()
def app(tmp_path: Path) -> Flask:
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    with application.app_context():
        ensure_session(CODE, title="Accessibility Agents in Action", event_name="AHG")
    return application


@pytest.fixture()
def client(app: Flask):
    return app.test_client()


# ---------------------------------------------------------------------------
# One source
# ---------------------------------------------------------------------------


def test_every_format_renders_the_same_slides(ctx: deck.DeckContext):
    slides = deck.build_slides(ctx)
    assert len(slides) == 39
    assert len({s.id for s in slides}) == len(slides), "slide ids are anchors"

    markdown = deck.build_deck_markdown(ctx)
    for slide in slides:
        assert slide.title in markdown


def test_addresses_in_slide_text_and_tables_are_live_office_links(ctx, tmp_path, monkeypatch):
    from docx import Document
    from pptx import Presentation

    sample = deck.Slide("links", "", "Links", blocks=(
        deck.Para("Visit letitglow.app/ahg."),
        deck.Bullets(("Email help@example.edu.",)),
        deck.Table("Resources", ("Site", "Address"), (("Browser", "vscode.dev"),)),
    ), notes=("Read https://example.org/notes.",))
    monkeypatch.setattr(deck, "build_slides", lambda _ctx: [sample])
    word = Document(BytesIO(deck.build_deck_docx_bytes(ctx)))
    targets = {r.target_ref for r in word.part.rels.values() if r.reltype.endswith("/hyperlink")}
    assert {"https://letitglow.app/ahg", "mailto:help@example.edu",
            "https://vscode.dev", "https://example.org/notes"} <= targets
    powerpoint = Presentation(BytesIO(deck.build_deck_pptx_bytes(ctx)))
    table = next(shape.table for shape in powerpoint.slides[0].shapes if shape.has_table)
    assert table.cell(1, 1).text_frame.paragraphs[0].runs[0].hyperlink.address == "https://vscode.dev"
    note_targets = {
        run.hyperlink.address
        for paragraph in powerpoint.slides[0].notes_slide.notes_text_frame.paragraphs
        for run in paragraph.runs
    }
    assert "https://example.org/notes" in note_targets


def test_deck_address_links_escape_html_and_preserve_punctuation():
    from acb_large_print_web.routes.workshop import workshop_address_links

    html = str(workshop_address_links('<script>bad()</script> Visit letitglow.app/ahg.'))
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert '<a href="https://letitglow.app/ahg">letitglow.app/ahg</a>.' in html

def test_the_title_is_the_program_title():
    """AHG's top attendee complaint is a title that does not match the content."""
    assert f"{deck.DECK_TITLE}: {deck.DECK_SUBTITLE}" == (
        "Accessibility Agents: Building Human-Centered AI Workflows for "
        "Trusted Accessibility Automation at Scale"
    )


def test_every_block_opens_by_saying_where_we_are(ctx: deck.DeckContext):
    kickers = [s.kicker for s in deck.build_slides(ctx)]
    for number in range(2, 8):
        assert any(k.startswith(f"Block {number} of 7") for k in kickers)


def test_the_day_is_the_ahg_day(ctx: deck.DeckContext):
    assert agenda.validate_ahg_day() == []
    markdown = deck.build_deck_markdown(ctx)
    for block in agenda.AHG_DAY:
        if block.kind in (agenda.BREAK, agenda.LUNCH):
            assert block.starts_at in markdown


def test_no_slide_is_a_wall_of_text(ctx: deck.DeckContext):
    """AHG speaker guidance: avoid walls of text."""
    for slide in deck.build_slides(ctx):
        for block in slide.blocks:
            if isinstance(block, deck.Bullets):
                assert len(block.items) <= 6, slide.id
            if isinstance(block, deck.Table):
                assert len(block.rows) <= 7, slide.id


def _visible_words(slide: deck.Slide) -> int:
    words = 0
    for block in slide.blocks:
        if isinstance(block, deck.Para) and not block.small:
            words += len(block.text.split())
        elif isinstance(block, deck.Bullets):
            words += sum(len(item.split()) for item in block.items)
        elif isinstance(block, deck.Definitions):
            words += sum(len(f"{t} {m}".split()) for t, m in block.items)
        elif isinstance(block, deck.Panel):
            words += sum(len(line.split()) for line in block.lines)
        elif isinstance(block, deck.Table):
            words += sum(len(cell.split()) for row in block.rows for cell in row)
    return words


def test_every_slide_can_be_read_from_the_back_of_the_room(ctx: deck.DeckContext):
    """A projected slide is a headline, not a handout: the detail is in the notes."""
    for slide in deck.build_slides(ctx):
        if slide.id == "outcomes":
            continue  # the published learning outcomes, word for word
        assert _visible_words(slide) <= 60, (slide.id, _visible_words(slide))


def test_every_link_on_a_slide_goes_somewhere_real(ctx: deck.DeckContext):
    kit = Path(__file__).resolve().parents[2] / "docs" / "ahg-2026" / "kit"
    prefix = f"{deck.SITE}/ahg/kit/"
    for slide in deck.build_slides(ctx):
        for label, url in slide.links:
            assert label and url.startswith(("https://", "http://")), (slide.id, url)
            if url.startswith(prefix):
                assert (kit / url[len(prefix):]).is_file(), (slide.id, url)


def test_block_slides_link_to_their_step_card(ctx: deck.DeckContext):
    starts = re.compile(r"^Block (\d) of 7, slide 1 of \d+ - \d")
    found = 0
    for slide in deck.build_slides(ctx):
        match = starts.match(slide.kicker)
        if match:
            found += 1
            assert any(label == f"Step card {match.group(1)}" for label, _ in slide.links), slide.id
    assert found == 6, "blocks 2 to 7 each open with their own slide"


def test_every_slide_in_a_block_says_where_you_are(ctx: deck.DeckContext):
    """Someone who stepped out finds their place from the slide alone."""
    where = re.compile(r"^Block \d of 7, slide (\d+) of (\d+) - ")
    for slide in deck.build_slides(ctx):
        if slide.id in ("s1", "s14", "s18", "s26", "s27"):
            continue
        match = where.match(slide.kicker)
        assert match, (slide.id, slide.kicker)
        assert int(match.group(1)) <= int(match.group(2))


def test_hands_on_slides_say_what_to_do_if_you_are_behind(ctx: deck.DeckContext):
    for slide_id in ("s11", "s12", "s15", "s19", "s22", "s25"):
        slide = next(s for s in deck.build_slides(ctx) if s.id == slide_id)
        text = " ".join(b.text for b in slide.blocks if isinstance(b, deck.Para))
        assert "Behind?" in text or "Stuck?" in text, slide_id


def test_the_day_ends_with_the_session_evaluation():
    """AHG asks speakers to save time for the session evaluation."""
    assert agenda.AGENDA[-1].title == "Session evaluation"
    assert agenda.AGENDA[-1].minutes >= 5


def test_the_privacy_rule_is_on_a_slide(ctx: deck.DeckContext):
    slide = next(s for s in deck.build_slides(ctx) if s.id == "s6")
    text = " ".join(getattr(b, "text", "") or " ".join(getattr(b, "items", ())) for b in slide.blocks)
    assert "Never paste anything private" in text


def test_sharing_slides_preserve_approval_and_deferred_paths(ctx: deck.DeckContext):
    slides = {slide.id: slide for slide in deck.build_slides(ctx)}
    steps = next(block.items for block in slides["s22"].blocks if isinstance(block, deck.Bullets))
    assert "permission" in steps[0].lower()
    assert "private" in steps[0].lower()
    assert "GitHub" in " ".join(steps[1:])
    assert "keep a reviewed copy" in " ".join(
        block.text for block in slides["s22"].blocks if isinstance(block, deck.Para)
    )
    assert "permission" in " ".join(slides["s23"].notes).lower()
    assert "permission" in " ".join(slides["s24"].notes).lower()
    assert "ready-made" in " ".join(slides["s24"].notes).lower()


def test_every_promise_is_named_on_a_slide(ctx: deck.DeckContext):
    markdown = deck.build_deck_markdown(ctx)
    for promise in ("VS Code", "Copilot", "GitHub", "collection", "Accessibility Agents",
                    "axe", "Accessibility Insights", "WCAG 2.2", "Title II", "team",
                    "session evaluation"):
        assert promise in markdown, promise


def test_this_room_s_addresses_reach_every_format(ctx: deck.DeckContext):
    markdown = deck.build_deck_markdown(ctx)
    assert f"letitglow.app/w/{CODE}/11" in markdown
    assert f"letitglow.app/w/{CODE}" in markdown


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def test_markdown_uses_headings_and_lists_not_layout(ctx: deck.DeckContext):
    markdown = deck.build_deck_markdown(ctx)
    lines = markdown.splitlines()
    assert lines[0] == "---" and lines[1].startswith("title: ")
    assert "# Accessibility Agents" in lines
    assert "## 1. Accessibility Agents" in markdown
    assert "\n- " in markdown
    assert "\n1. " in markdown
    # Pipe table with a header separator, not spaces pretending to be columns.
    assert "| Specialist | Takes |" in markdown
    assert "|---|---|" in markdown


def test_markdown_keeps_the_speaker_notes(ctx: deck.DeckContext):
    markdown = deck.build_deck_markdown(ctx)
    assert "### Speaker notes, slide 2" in markdown
    assert "Let the laugh happen" in markdown


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------


def test_word_uses_real_heading_and_list_styles(ctx: deck.DeckContext):
    from docx import Document

    doc = Document(BytesIO(deck.build_deck_docx_bytes(ctx)))
    styles = [p.style.name for p in doc.paragraphs]

    assert styles.count("Heading 1") == 1, "one document title"
    assert styles.count("Heading 2") == len(deck.build_slides(ctx)), "one heading per slide"
    assert "List Bullet" in styles
    assert "List Number" in styles
    assert "Heading 3" in styles, "speaker notes get their own heading level"


def test_word_is_acb_large_print_and_declares_its_language(ctx: deck.DeckContext):
    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(BytesIO(deck.build_deck_docx_bytes(ctx)))
    normal = doc.styles["Normal"]
    assert normal.font.name == "Arial"
    assert normal.font.size.pt == 18

    lang = normal.element.get_or_add_rPr().find(qn("w:lang"))
    assert lang is not None
    assert lang.get(qn("w:val")) == "en-US"
    assert doc.core_properties.title == deck.DECK_TITLE


def test_word_tables_mark_their_header_row(ctx: deck.DeckContext):
    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(BytesIO(deck.build_deck_docx_bytes(ctx)))
    assert doc.tables, "the deck carries tables"
    for table in doc.tables:
        header = table.rows[0]
        tr_pr = header._tr.find(qn("w:trPr"))
        assert tr_pr is not None and tr_pr.find(qn("w:tblHeader")) is not None, (
            "a table header row that is not marked is announced as data"
        )


# ---------------------------------------------------------------------------
# PowerPoint
# ---------------------------------------------------------------------------


def test_powerpoint_gives_every_slide_a_real_title(ctx: deck.DeckContext):
    from pptx import Presentation

    prs = Presentation(BytesIO(deck.build_deck_pptx_bytes(ctx)))
    slides = deck.build_slides(ctx)
    assert len(prs.slides) == len(slides)

    for shipped, source in zip(prs.slides, slides, strict=True):
        assert shipped.shapes.title is not None, "a slide with no title placeholder"
        assert shipped.shapes.title.text == source.title


def test_powerpoint_content_sits_in_placeholders_not_floating_boxes(ctx: deck.DeckContext):
    """Placeholder order is the reading order a screen reader announces."""
    from pptx import Presentation

    prs = Presentation(BytesIO(deck.build_deck_pptx_bytes(ctx)))
    for slide in prs.slides:
        has_table = any(shape.has_table for shape in slide.shapes)
        if has_table:
            continue  # table slides are title-only by design
        placeholders = [p.placeholder_format.idx for p in slide.placeholders]
        assert 0 in placeholders, "the title placeholder"
        assert len(placeholders) >= 2, "body text belongs in the body placeholder"


def test_powerpoint_notes_go_in_the_notes_slide(ctx: deck.DeckContext):
    from pptx import Presentation

    prs = Presentation(BytesIO(deck.build_deck_pptx_bytes(ctx)))
    notes = [s.notes_slide.notes_text_frame.text for s in prs.slides]
    assert any("Let the laugh happen" in n for n in notes)
    # Notes must not have been dumped onto the slide surface instead.
    for slide in prs.slides:
        body = " ".join(sh.text_frame.text for sh in slide.shapes if sh.has_text_frame)
        assert "Let the laugh happen" not in body


def test_powerpoint_tables_carry_alt_text_and_a_header_row(ctx: deck.DeckContext):
    from pptx import Presentation

    prs = Presentation(BytesIO(deck.build_deck_pptx_bytes(ctx)))
    found = 0
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_table:
                continue
            found += 1
            assert shape.table.first_row is True
            descr = shape._element.nvGraphicFramePr.cNvPr.get("descr")
            assert descr, "a table with no alt text"
    assert found >= 1, "the three piles table"


def test_powerpoint_has_no_text_under_24pt(ctx: deck.DeckContext):
    """24pt is the floor for a projected room, kicker and table cells included."""
    from pptx import Presentation

    prs = Presentation(BytesIO(deck.build_deck_pptx_bytes(ctx)))
    small = []
    for number, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            frames = []
            if shape.has_text_frame:
                frames.append(shape.text_frame)
            if getattr(shape, "has_table", False) and shape.has_table:
                frames.extend(cell.text_frame for row in shape.table.rows for cell in row.cells)
            for frame in frames:
                for paragraph in frame.paragraphs:
                    for run in paragraph.runs:
                        if run.text.strip() and (run.font.size is None or run.font.size.pt < 24):
                            small.append((number, run.text[:30], run.font.size and run.font.size.pt))
    assert not small, small


def test_powerpoint_wrapped_rows_have_individual_heights_and_clear_footers(ctx):
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation(BytesIO(deck.build_deck_pptx_bytes(ctx)))
    for data, slide in zip(deck.build_slides(ctx), prs.slides):
        for index, shape in enumerate(slide.shapes):
            if not shape.has_table:
                continue
            block = next(b for b in data.blocks if isinstance(b, deck.Table))
            width = 70 // len(block.headers) - 2
            for row, texts in zip(shape.table.rows, [block.headers, *block.rows]):
                expected = Inches(0.1 + 0.42 * max(deck._pptx_lines(t, width) for t in texts))
                assert row.height == expected, (data.id, texts)
            for following in list(slide.shapes)[index + 1:]:
                assert following.top >= shape.top + shape.height + Inches(0.14), data.id
                assert following.top + following.height <= prs.slide_height, data.id


def test_word_passes_glow_s_own_audit(ctx: deck.DeckContext, tmp_path):
    """Use a checker, fix what it finds - the deck is held to GLOW's own bar."""
    from acb_large_print.auditor import audit_document

    path = tmp_path / "deck.docx"
    path.write_bytes(deck.build_deck_docx_bytes(ctx))
    result = audit_document(path)
    serious = [
        f for f in result.findings
        if str(f.severity).split(".")[-1] in {"CRITICAL", "HIGH", "MEDIUM"}
    ]
    assert not serious, [(f.rule_id, f.message) for f in serious]


def test_powerpoint_passes_glow_s_own_audit(ctx: deck.DeckContext, tmp_path):
    from acb_large_print.pptx_auditor import audit_presentation

    path = tmp_path / "deck.pptx"
    path.write_bytes(deck.build_deck_pptx_bytes(ctx))
    result = audit_presentation(path)
    assert not result.findings, [(f.rule_id, f.message) for f in result.findings]


def test_powerpoint_declares_its_title_and_language(ctx: deck.DeckContext):
    from pptx import Presentation

    prs = Presentation(BytesIO(deck.build_deck_pptx_bytes(ctx)))
    assert prs.core_properties.title == deck.DECK_TITLE
    assert prs.core_properties.language == "en-US"


# ---------------------------------------------------------------------------
# The routes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("suffix", "mimetype"),
    [
        ("md", "text/markdown"),
        ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    ],
)
def test_each_format_downloads_with_the_right_type(client, suffix: str, mimetype: str):
    resp = client.get(f"/workshop/session/{CODE}/deck.{suffix}")
    assert resp.status_code == 200
    assert resp.mimetype == mimetype
    assert f"glow-workshop-deck.{suffix}" in resp.headers["Content-Disposition"]
    assert len(resp.data) > 1000


def test_the_formats_are_offered_on_the_deck_itself(client):
    body = client.get(f"/workshop/session/{CODE}/deck").get_data(as_text=True)
    for label in ("HTML, one file", "Word", "PowerPoint", "Markdown"):
        assert label in body


def test_the_formats_read_without_a_session(client):
    for suffix in ("md", "docx", "pptx"):
        assert client.get(f"/workshop/deck.{suffix}").status_code == 200


def test_powerpoint_links_are_real_links(ctx: deck.DeckContext):
    from pptx import Presentation

    prs = Presentation(BytesIO(deck.build_deck_pptx_bytes(ctx)))
    addresses = set()
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        if run.hyperlink.address:
                            addresses.add(run.hyperlink.address)
    expected = {url for s in deck.build_slides(ctx) for _, url in s.links}
    assert expected <= addresses, expected - addresses


def test_html_slide_list_is_links_not_a_dropdown(client):
    """A dropdown that jumps on change moves the slide on every arrow press."""
    body = client.get(f"/workshop/session/{CODE}/deck").get_data(as_text=True)
    assert "<select" not in body
    assert 'id="slide-list"' in body
    assert body.count('data-index="') == 39
    assert 'href="https://letitglow.app/ahg/kit/step-cards/2-design-your-agent.md"' in body
    assert deck.LINKS_LABEL in body


def test_the_large_print_handout_has_slides_and_links_but_no_notes(ctx: deck.DeckContext, tmp_path):
    from acb_large_print.auditor import audit_document
    from docx import Document

    data = deck.build_deck_handout_docx_bytes(ctx)
    text = "\n".join(p.text for p in Document(BytesIO(data)).paragraphs)
    assert "Let the laugh happen" not in text, "speaker notes stay out of the handout"
    assert "Automation helps. You decide." in text
    assert "Step card 2: letitglow.app/ahg/kit/step-cards/2-design-your-agent.md" in text

    path = tmp_path / "handout.docx"
    path.write_bytes(data)
    serious = [
        f for f in audit_document(path).findings
        if str(f.severity).split(".")[-1] in {"CRITICAL", "HIGH", "MEDIUM"}
    ]
    assert not serious, [(f.rule_id, f.message) for f in serious]


def test_the_handout_downloads(client):
    resp = client.get(f"/workshop/session/{CODE}/deck-handout.docx")
    assert resp.status_code == 200
    assert "large-print-handout.docx" in resp.headers["Content-Disposition"]
    body = client.get(f"/workshop/session/{CODE}/deck").get_data(as_text=True)
    assert "Large print handout, Word" in body
