"""Regression checks for the self-contained presenter guide."""

import html
import re

import build_ahg_presenter as presenter


def test_standalone_html_contains_current_complete_prompts_and_valid_targets():
    page = (presenter.ahg_formats.AHG / "presenter-slide-script.html").read_text(encoding="utf-8")
    assert presenter.browser_prompts() in page
    assert "PRESENTER_BROWSER_PROMPTS" not in page
    for key, _title, filename in presenter.PROMPTS:
        match = re.search(
            rf'<details id="browser-prompt-{key}">.*?<pre tabindex="0"><code>(.*?)</code></pre>',
            page,
            re.DOTALL,
        )
        assert match, key
        expected = (presenter.ahg_formats.AHG / "kit" / "any-assistant" / filename).read_text(encoding="utf-8")
        assert html.unescape(match.group(1)) == expected
    for target in re.findall(r'href="#([^"]+)"', page):
        assert f'id="{target}"' in page, target


def test_capstone_source_is_complete_and_slide_cues_are_present():
    page = (presenter.ahg_formats.AHG / "presenter-slide-script.html").read_text(encoding="utf-8")
    match = re.search(
        r'<details id="browser-prompt-capstone-source">.*?<pre tabindex="0"><code>(.*?)</code></pre>',
        page,
        re.DOTALL,
    )
    assert match
    source = (presenter.ahg_formats.AHG / "kit" / "sample-course" / "psy101-announcement.html").read_text(encoding="utf-8")
    assert html.unescape(match.group(1)).endswith(source)
    slides = re.split(r'<h3 id="[^"]+">Slide (\d+)\.[^<]+</h3>', page)
    assert [int(slides[i]) for i in range(1, len(slides), 2)] == list(range(1, 40))
    for i in range(1, len(slides), 2):
        number, section = int(slides[i]), slides[i + 1]
        assert "Words to say" in section, number
        if number < 39:
            assert "Cue" in section, number
