#!/usr/bin/env python3
"""Build the standalone AHG presenter HTML from its slide-by-slide script."""

from __future__ import annotations

import html
import re

import ahg_formats


def main() -> int:
    doc = ahg_formats.read("presenter-slide-script.md")
    target = ahg_formats.AHG / "presenter-slide-script.html"
    ahg_formats.write_html(doc, target)
    page = target.read_text(encoding="utf-8")
    headings = re.findall(r'<h3 id="([^"]+)">(Slide (\d+)\.[^<]+)</h3>', page)
    if [int(number) for _, _, number in headings] != list(range(1, 40)):
        raise ValueError("Presenter script must contain slides 1 through 39 in order")
    links = "\n".join(
        f'<li><a href="#{html.escape(anchor, quote=True)}">{label}</a></li>'
        for anchor, label, _ in headings
    )
    nav = (
        '<!-- a11y: needs manual verification — keyboard and screen reader behavior of the slide index -->\n'
        '<details>\n<summary>Jump to a slide</summary>\n'
        '<nav aria-label="Slide index">\n<ol>\n' + links
        + '\n</ol>\n</nav>\n</details>'
    )
    page, count = re.subn(r"(</h1>)", lambda match: match.group(1) + "\n" + nav, page, count=1)
    if count != 1:
        raise ValueError("Presenter script needs one document heading")
    target.write_text(page, encoding="utf-8", newline="\n")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
