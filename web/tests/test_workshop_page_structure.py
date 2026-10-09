"""Structural accessibility of every workshop page, without a browser.

axe covers these routes in the Playwright sweep, but that sweep needs browser
binaries and a running server, so in practice it runs rarely and has not run
since the specimen panel, the prompt cards, the pre-flight screen and the
deck were added. This checks the structural things a parser can see, on every
render, in under a second:

* one ``h1`` per page, and no skipped heading levels
* every form control has an accessible name
* every data table marks its header cells with ``scope``
* no empty heading, label or button

None of that replaces a screen reader pass. It does mean a heading level
cannot be skipped in a template without a test going red, which is the class
of regression that is invisible until somebody is navigating by headings.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app
from acb_large_print_web.routes.workshop import ACTIVITY_ORDER
from acb_large_print_web.workshop_store import ensure_session

CODE = "structuredemo"
FACILITATOR_KEY = "unlock-me"

# Controls that carry their own semantics and need no visible label.
_SELF_LABELLING = {"hidden", "submit", "button", "reset", "image"}


class _Page(HTMLParser):
    """Just enough parsing to answer structural questions."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[int, str]] = []
        self.label_for: set[str] = set()
        self.controls: list[dict[str, str]] = []
        self.tables: list[dict[str, int]] = []
        self.empty_buttons = 0
        self._heading_level = 0
        self._heading_text = ""
        self._in_button = False
        self._button_text = ""
        self._table_stack: list[dict[str, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}

        if re.fullmatch(r"h[1-6]", tag):
            self._heading_level = int(tag[1])
            self._heading_text = ""

        elif tag == "label" and a.get("for"):
            self.label_for.add(a["for"])

        elif tag in {"input", "textarea", "select"}:
            kind = a.get("type", "text").lower()
            if kind not in _SELF_LABELLING:
                self.controls.append({
                    "tag": tag,
                    "id": a.get("id", ""),
                    "aria_label": a.get("aria-label", ""),
                    "aria_labelledby": a.get("aria-labelledby", ""),
                    "title": a.get("title", ""),
                })

        elif tag == "button":
            self._in_button = True
            self._button_text = a.get("aria-label", "")

        elif tag == "table":
            self._table_stack.append({"th": 0, "scoped": 0})

        elif tag == "th":
            if self._table_stack:
                self._table_stack[-1]["th"] += 1
                if a.get("scope"):
                    self._table_stack[-1]["scoped"] += 1

    def handle_endtag(self, tag: str) -> None:
        if re.fullmatch(r"h[1-6]", tag) and self._heading_level:
            self.headings.append((self._heading_level, self._heading_text.strip()))
            self._heading_level = 0
        elif tag == "button":
            if not self._button_text.strip():
                self.empty_buttons += 1
            self._in_button = False
        elif tag == "table" and self._table_stack:
            self.tables.append(self._table_stack.pop())

    def handle_data(self, data: str) -> None:
        if self._heading_level:
            self._heading_text += data
        if self._in_button:
            self._button_text += data


def parse(html: str) -> _Page:
    page = _Page()
    page.feed(html)
    return page


@pytest.fixture()
def app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Flask:
    monkeypatch.setenv("GLOW_WORKSHOP_FACILITATOR_KEY", FACILITATOR_KEY)
    application = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    application.instance_path = str(tmp_path / "instance")
    Path(application.instance_path).mkdir(parents=True, exist_ok=True)
    with application.app_context():
        ensure_session(CODE, title="Accessibility Agents in Action", event_name="AHG")
    return application


@pytest.fixture()
def client(app: Flask):
    client = app.test_client()
    client.post("/workshop/", data={"action": "join", "session_code": CODE, "display_name": "Rowan"})
    # Unlock the facilitator surfaces too. Without this the dashboard and
    # pre-flight answer 403 and are silently skipped -- which is exactly the
    # kind of coverage hole that makes a structural gate feel safer than it is.
    client.post(
        f"/workshop/session/{CODE}/facilitator/unlock",
        data={"facilitator_key": FACILITATOR_KEY},
    )
    return client


def _routes() -> list[str]:
    paths = [
        "/workshop/",
        "/workshop/guide",
        "/workshop/exercises",
        "/workshop/utilization",
        "/workshop/deck",
        f"/workshop/session/{CODE}/deck",
        f"/workshop/session/{CODE}/launchpad",
        f"/workshop/session/{CODE}/me",
        f"/workshop/session/{CODE}/gallery",
        f"/workshop/session/{CODE}/badges",
        f"/workshop/session/{CODE}/artifact",
        f"/workshop/session/{CODE}/wall",
        f"/workshop/session/{CODE}/coach",
        f"/workshop/session/{CODE}/review",
        f"/workshop/session/{CODE}/share",
        f"/workshop/session/{CODE}/follow-through",
        f"/workshop/session/{CODE}/signage",
        f"/workshop/session/{CODE}/facilitator",
        f"/workshop/session/{CODE}/preflight",
    ]
    paths += [f"/workshop/session/{CODE}/activity/{key}" for key in ACTIVITY_ORDER]
    return paths


def _pages(client):
    for path in _routes():
        resp = client.get(path)
        if resp.status_code != 200:
            continue
        yield path, parse(resp.get_data(as_text=True))


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------


def test_every_page_has_exactly_one_top_level_heading(client):
    for path, page in _pages(client):
        h1s = [text for level, text in page.headings if level == 1]
        assert len(h1s) == 1, f"{path}: {len(h1s)} h1 elements"


def test_no_page_skips_a_heading_level(client):
    """Skipping a level tells a screen reader user a section is missing."""
    for path, page in _pages(client):
        levels = [level for level, _ in page.headings]
        for previous, current in zip(levels, levels[1:], strict=False):
            assert current <= previous + 1, (
                f"{path}: heading jumps from h{previous} to h{current}"
            )


def test_no_heading_is_empty(client):
    for path, page in _pages(client):
        for level, text in page.headings:
            assert text, f"{path}: empty h{level}"


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------


def test_every_form_control_has_an_accessible_name(client):
    for path, page in _pages(client):
        for control in page.controls:
            named = (
                (control["id"] and control["id"] in page.label_for)
                or control["aria_label"]
                or control["aria_labelledby"]
                or control["title"]
            )
            assert named, (
                f"{path}: <{control['tag']} id={control['id']!r}> has no accessible name"
            )


def test_no_button_is_unlabelled(client):
    for path, page in _pages(client):
        assert page.empty_buttons == 0, f"{path}: {page.empty_buttons} button(s) with no text"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def test_every_table_header_cell_declares_its_scope(client):
    """Without scope, a header is announced as data and the table is noise."""
    for path, page in _pages(client):
        for index, table in enumerate(page.tables):
            if table["th"] == 0:
                continue
            assert table["scoped"] == table["th"], (
                f"{path}: table {index} has {table['th'] - table['scoped']} "
                "header cell(s) with no scope"
            )


# ---------------------------------------------------------------------------
# The surfaces added in September, which axe has not seen yet
# ---------------------------------------------------------------------------


def test_the_new_surfaces_actually_render(client):
    """A structural test that silently skipped every new page would pass."""
    rendered = {path for path, _ in _pages(client)}
    for path in (
        f"/workshop/session/{CODE}/facilitator",
        f"/workshop/session/{CODE}/preflight",
        f"/workshop/session/{CODE}/deck",
        f"/workshop/session/{CODE}/activity/lab_alt_text_decision",
        f"/workshop/session/{CODE}/activity/agent_formula",
        f"/workshop/session/{CODE}/activity/action_plan_30_day",
    ):
        assert path in rendered, f"{path} did not render, so it was not checked"
