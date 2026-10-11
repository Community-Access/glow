"""The page layout must reflow at narrow widths (WCAG 2.2, 1.4.10 Reflow).

The AI usage meter was once included after the sidebar's closing tag, which
made it a third column in the app's flex row. On a phone, or at 400 percent
zoom, it took the full width and left the page content zero pixels wide.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from flask import Flask

from acb_large_print_web.app import create_app


@pytest.fixture()
def client(tmp_path: Path):
    app: Flask = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False})
    app.instance_path = str(tmp_path / "instance")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    return app.test_client()


def test_the_ai_meter_sits_inside_the_sidebar(client):
    html = client.get("/privacy").get_data(as_text=True)
    meter = re.search(r'<div\s[^>]*class="ai-meter', html)
    if meter is None:
        pytest.skip("AI meter not rendered in this configuration")
    nav_open = html.find('<nav class="sidebar"')
    if nav_open == -1:
        nav_open = html.find("sidebar")
    nav_close = html.find("</nav>", nav_open)
    assert nav_open < meter.start() < nav_close, "the meter must be inside the sidebar nav"


def test_the_app_layout_has_only_the_sidebar_and_the_content_area(client):
    html = client.get("/privacy").get_data(as_text=True)
    start = html.find('class="app-layout"')
    content = html.find('class="content-area"', start)
    between = html[start:content]
    # Between the layout's opening tag and the content area, the only
    # top-level element is the sidebar; anything else becomes a column.
    assert between.count("</nav>") >= 1
    assert "ai-meter" not in between[between.rfind("</nav>"):]


def test_the_stylesheet_keeps_content_and_controls_inside_320px():
    css = (Path(__file__).resolve().parents[1] / "src" / "acb_large_print_web" / "static" / "forms.css").read_text(encoding="utf-8")
    assert "overflow-wrap: anywhere" in css
    assert "minmax(min(20rem, 100%), 1fr)" in css
    assert re.search(r"main fieldset \{\s*min-width: 0;", css)
