#!/usr/bin/env python3
"""Build the standalone AHG presenter HTML from its slide-by-slide script."""

from __future__ import annotations

import html
import re

import ahg_formats

PROMPTS = (
    ("1", "Ready check", "1-ready-check.txt"),
    ("2", "Design your agent", "2-design-my-agent.txt"),
    ("3", "Try your agent", "3-try-my-agent.txt"),
    ("4", "Ground your agent", "4-ground-my-agent.txt"),
    ("5", "Run the office", "5-run-the-office.txt"),
    ("review", "Review and improve your agent after blocks 3, 4 and 5", "review-my-agent.txt"),
    ("7", "Make your 30-day plan", "7-my-30-day-plan.txt"),
)


def browser_prompts() -> str:
    """Embed the exact kit prompts so the standalone guide works offline."""
    sections = []
    prompts = [
        (key, title, (ahg_formats.AHG / "kit" / "any-assistant" / filename).read_text(encoding="utf-8"))
        for key, title, filename in PROMPTS
    ]
    capstone = (ahg_formats.AHG / "chatgpt-mcp-capstone.md").read_text(encoding="utf-8")
    setup = capstone.split("## 4. Connect ChatGPT", 1)[1].split("## 5. Prepare", 1)[0]
    preparation = capstone.split("## 5. Prepare", 1)[1].split("## 6. Run", 1)[0]
    smoke = re.findall(r"```text\n(.*?)\n```", setup, flags=re.DOTALL)
    messages = re.findall(r"```text\n(.*?)\n```", preparation, flags=re.DOTALL)
    if len(smoke) != 1 or len(messages) != 2:
        raise ValueError("Capstone setup prompts could not be identified")
    announcement = (ahg_formats.AHG / "kit" / "sample-course" / "psy101-announcement.html").read_text(encoding="utf-8")
    prompts.extend((
        ("capstone-smoke", "Capstone connection smoke test", smoke[0]),
        ("capstone-agent", "Capstone reviewed agent instructions", messages[0]),
        ("capstone-source", "Capstone source message and complete fictional HTML", messages[1] + "\n" + announcement),
    ))
    for key, title, prompt in prompts:
        sections.append(
            f'<details id="browser-prompt-{key}">\n'
            f'<summary>{html.escape(title)} — complete browser prompt</summary>\n'
            '<p>Copy the entire text below into your approved assistant conversation. '
            'If no Copy button appears, select the text and copy it manually.</p>\n'
            '<button type="button" class="copy-prompt" hidden>Copy this complete prompt</button>\n'
            '<span role="status"></span>\n'
            f'<pre tabindex="0"><code>{html.escape(prompt)}</code></pre>\n'
            '</details>'
        )
    return "\n".join(sections) + '''
<style>
button:focus-visible, summary:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
.copy-prompt { font: inherit; margin: .5rem .5rem .5rem 0; padding: .4rem .7rem; }
details[id^="browser-prompt-"] { margin: 1rem 0; }
</style>
<script>
if (navigator.clipboard && navigator.clipboard.writeText) {
  document.querySelectorAll('.copy-prompt').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', async () => {
      const section = button.closest('details');
      const status = section.querySelector('[role="status"]');
      try {
        await navigator.clipboard.writeText(section.querySelector('code').textContent);
        status.textContent = 'Prompt copied. Paste it into your assistant.';
      } catch (error) {
        status.textContent = 'Copy was unavailable. Select the prompt text and copy it manually.';
      }
    });
  });
}
</script>'''


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
    marker = "<p>PRESENTER_BROWSER_PROMPTS</p>"
    if page.count(marker) != 1:
        raise ValueError("Presenter script needs one browser prompt marker")
    page = page.replace(marker, browser_prompts())
    target.write_text(page, encoding="utf-8", newline="\n")
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
