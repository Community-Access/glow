"""The workshop deck, as content rather than as a file.

A deck that exists as one HTML file cannot also be a Word document, a
PowerPoint, or Markdown without somebody maintaining four copies of the same
sentences -- and four copies is how the day's timings ended up disagreeing in
four places before ``workshop_agenda`` existed.

So the slides live here as data. Every format is a renderer over the same
list, and every clock time comes from ``workshop_agenda.AHG_DAY`` at render
time, so a change to the day reaches all four formats at once.

This is the Accessing Higher Ground 2026 deck: seven blocks, 10:30 to 4:30,
built to keep every promise in the published session description. The plan
behind it is ``docs/ahg-2026/plan.md``.

Accessibility is not a pass applied afterwards to any of them:

* **HTML** -- one heading per slide, a linear reading mode, focus moved to
  the heading on slide change, polite announcements, no colour-only meaning.
* **Word** -- real heading styles, real list styles, Arial 18pt (ACB large
  print), a marked table header row, and a declared document language.
* **PowerPoint** -- every slide has a real title placeholder and a real body
  placeholder, in that order, because that order *is* the reading order a
  screen reader announces. Nothing is a floating text box. Speaker notes go
  in the notes slide where a reader expects them, and tables carry alt text.
* **Markdown** -- headings, lists and pipe tables; no layout tricks, so it
  converts cleanly into whatever an institution actually uses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from io import BytesIO
from typing import ClassVar

from . import workshop_agenda as agenda

DECK_TITLE = "Accessibility Agents"
DECK_SUBTITLE = "Building Human-Centered AI Workflows for Trusted Accessibility Automation at Scale"
DECK_EVENT = "Accessing Higher Ground 2026"
DECK_BYLINE = "Jeff Bishop, University of Arizona, IT Accessibility Consultant"
DECK_CREDIT = (
    "In collaboration with Blind Information Technology Solutions (BITS) and Techopolis, "
    "with special thanks to Taylor Arndt, who helped dream up and build Accessibility Agents."
)


#: Where the kit and the workshop pages live. Slide links are absolute, so
#: they work from the downloaded HTML, Word, PowerPoint and Markdown too.
SITE = "https://letitglow.app"

#: The line before a slide's links, in every format.
LINKS_LABEL = "In the kit and on the site:"

#: Step card file per block, counting "before the day" as 0.
STEP_CARDS = (
    "0-before-the-day.md",
    "1-why-we-are-here.md",
    "2-design-your-agent.md",
    "3-your-agent-at-work.md",
    "4-ground-it.md",
    "5-build-the-office.md",
    "6-share-it.md",
    "7-take-it-home.md",
)

#: What each of the seven blocks leaves a participant with, for the map.
LEAVES_WITH = (
    "A ready laptop",
    "Version 1",
    "Version 2",
    "Version 3, cited",
    "Version 4, in a team",
    "Shared, in your name",
    "A 30-day plan",
)

# ---------------------------------------------------------------------------
# Content kinds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Para:
    """A paragraph. ``lead`` is set larger; ``big`` is the line of the slide."""

    kind: ClassVar[str] = "para"
    text: str
    lead: bool = False
    big: bool = False
    small: bool = False


@dataclass(frozen=True)
class Bullets:
    kind: ClassVar[str] = "bullets"
    items: tuple[str, ...]
    ordered: bool = False


@dataclass(frozen=True)
class Definitions:
    """Term and meaning. A description list in HTML, a two-level list elsewhere."""

    kind: ClassVar[str] = "definitions"
    items: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Panel:
    """A called-out aside. Rendered as a blockquote where one exists."""

    kind: ClassVar[str] = "panel"
    lines: tuple[str, ...]


@dataclass(frozen=True)
class Url:
    """An address said out loud and read off a wall. Set very large."""

    kind: ClassVar[str] = "url"
    text: str


@dataclass(frozen=True)
class Table:
    kind: ClassVar[str] = "table"
    caption: str
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    compact: bool = False


Content = Para | Bullets | Definitions | Panel | Url | Table


@dataclass(frozen=True)
class Slide:
    id: str
    kicker: str
    title: str
    blocks: tuple[Content, ...] = ()
    notes: tuple[str, ...] = ()
    section: str = ""
    #: (label, address) pairs: where this slide's subject lives in the kit or
    #: on the site, so anyone reading the deck can go straight to it.
    links: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class DeckContext:
    """What the deck needs to know about the room it is being shown in."""

    code_label: str = "your-code"
    join_display: str = "letitglow.app/w/your-code"
    activity_times: tuple[str, ...] = field(default_factory=tuple)

    def activity(self, number: int) -> str:
        """The kicker fragment for activity *number*, counting from one."""
        try:
            length = self.activity_times[number - 1]
        except IndexError:  # pragma: no cover - defensive
            length = ""
        return f"{length} - /w/{self.code_label}/{number}"


def _block(number: int) -> agenda.Block:
    """Block *number* of the AHG day, counting the opening as 1."""
    return agenda.ahg_blocks()[number - 1]


def _you_are_here(number: int) -> str:
    block = _block(number)
    return f"Block {number} of 7 - {block.clock} - {block.minutes} minutes"


JOURNEY = (
    "The problem: a course full of barriers, and a team too small.",
    "Your agent: six plain-English answers.",
    "Your agent at work: your AI uses it on one course document, and you revise it.",
    "Your agent, grounded: real evidence in, cited answers out.",
    "Your agent in the team: the whole course, at once.",
    "Your agent, shared: your best version, in an open-source collection, with your name on it.",
    "Your campus: a 30-day plan.",
)

#: The six learning outcomes in the session guide, one line each. They are
#: read at the start of the day (the outcomes slide) and read back at the end of it
#: (/my-30-day-plan and step card 7).
OUTCOMES = (
    "Describe an accessibility task as an agent.",
    "Ground an agent's answers in checker evidence, citing WCAG 2.2.",
    "Name what no checker finds, and write the review step that catches it.",
    "Explain how a team of specialists and a coordinator scales the work.",
    "Contribute to an open-source project, credited in your name.",
    "Plan one workflow to try on your own campus in 30 days.",
)


def _journey_note(number: int) -> str:
    return f"Say where we are on the journey: step {number} of 7, \"{JOURNEY[number - 1]}\" Then show what they will have at the end of this block before anyone starts."


# ---------------------------------------------------------------------------
# The deck
# ---------------------------------------------------------------------------


def _kit(rel: str) -> str:
    """The online copy of a kit file, readable without unzipping anything."""
    return f"{SITE}/ahg/kit/{rel}"


def _card(number: int) -> tuple[str, str]:
    return (f"Step card {number}", _kit(f"step-cards/{STEP_CARDS[number]}"))


def _leaves_with(number: int) -> str:
    return LEAVES_WITH[number - 1]


def build_slides(ctx: DeckContext) -> list[Slide]:
    """Every slide of the AHG 2026 day, in order, with this room's addresses."""
    day = agenda.AHG_DAY
    lunch = next(b for b in day if b.kind == agenda.LUNCH)
    rest = next(b for b in day if b.kind == agenda.BREAK)
    commitments = next(b for b in day if b.title == "Commitments")
    evaluation = day[-1]
    blocks = agenda.ahg_blocks()

    return _where_you_are([
        # -- Block 1: why we are here ---------------------------------------
        Slide(
            id="s1", section="Opening", kicker=DECK_EVENT, title=DECK_TITLE,
            blocks=(
                Para(DECK_SUBTITLE, lead=True),
                Para("Today you build an accessibility agent. By 4:00 it works in a team, in an open-source project, with your name on it."),
                Para(DECK_BYLINE, small=True),
                Para(DECK_CREDIT, small=True),
            ),
            notes=(
                "The proctor introduces the session. Put the microphone on before you say a word, and keep it on all day: when someone speaks from the floor, pass them a mic or repeat what they said into yours before you answer.",
                "Say the key point before any logistics, in one sentence: accessibility in higher education does not scale by fixing, it scales by making more people who can, and agents are how one person's know-how reaches a whole course.",
                "Describe the slide: the title, the subtitle from the program, and one sentence promising what they leave with.",
                "Name the collaborators out loud: BITS and Techopolis, and Taylor Arndt, who helped dream up and build Accessibility Agents.",
            ),
            links=(("Everything for today", f"{SITE}/ahg"),),
        ),
        Slide(
            id="s2", section="Opening", kicker="The problem", title="Forty thousand files and three people",
            blocks=(
                Para("Title II requires WCAG 2.1 AA of public colleges and universities, from April 2027 for most."),
                Para("Most of what is in scope is documents: syllabi, slide decks, scanned readings."),
                Para("Nobody fixes that by working harder.", big=True),
            ),
            notes=(
                "Ask, warmly: who here has a backlog? Who has a spreadsheet with the word final in its name more than once? Let the laugh happen; it is recognition, not mockery.",
                "Then the question for the day: how do we scale without losing quality, accountability or trust?",
                "Title II's rule points to WCAG 2.1 AA; 2.2 is the current standard and includes everything 2.1 does. The Department of Justice's interim final rule of 20 April 2026 moved the dates to 26 April 2027 for entities of 50,000 people or more and 26 April 2028 for smaller ones (ada.gov, the web rule page). Check that page the week before in case the dates move again. Say it once and move on.",
            ),
        ),
        Slide(
            id="s3", section="Opening", kicker="Where we will be at 4:00", title="The finished result, first",
            blocks=(
                Para("A team of agents reviews a whole course and writes one report. One section, from Maria's agent:"),
                Table(
                    caption="One finding in the team report",
                    headers=("Part", "What it says"),
                    rows=(
                        ("File", "The scanned required reading"),
                        ("Evidence", "GLOW audit: pictures of text, untagged"),
                        ("Plan", "A clean source, then large print and audio"),
                        ("Reviewer", "Alternate format specialist"),
                    ),
                ),
            ),
            notes=(
                "Read the table out loud, row by row. It is the destination; people relax when they can see it.",
                "Every finding in the real report has its evidence, its WCAG criterion with a link, and a named person who checks it. You will build one of the agents that writes a section like this.",
                "Maria is a colleague in a disability resource center. She is fictional, and she is one step ahead of the room all day.",
            ),
            links=(("Maria's finished agent", _kit("examples/maria-alternate-format-planner.md")),),
        ),
        Slide(
            id="s4", section="Opening", kicker="The map for today", title="The day, in seven steps",
            blocks=(
                Table(
                    caption="The seven blocks, and what each one leaves you with",
                    headers=("When", "Block", "You leave with"),
                    rows=tuple(
                        (block.starts_at, block.title, _leaves_with(number))
                        for number, block in enumerate(blocks, start=1)
                    ),
                    compact=True,
                ),
            ),
            notes=(
                "Read the seven, slowly. This map comes back at the start of every block, so nobody ever wonders where we are.",
                "Point out the pattern: every block makes the same agent better. Version 1 before lunch, version 4 by three o'clock.",
                "Promise them out loud: every step has a finished example to fall back on. Nobody gets stuck and stays stuck.",
            ),
            links=(("The kit's own map of the day", _kit("README.md")),),
        ),
        Slide(
            id="outcomes", section="Opening", kicker="By 4:30", title="What you will be able to do",
            blocks=(Bullets(items=OUTCOMES),),
            notes=(
                "Read the six outcomes once. They come back at 4:15, when everyone's 30-day plan reads them back with what they made today.",
            ),
        ),
        Slide(
            id="s5", section="Opening", kicker="Housekeeping", title="How today runs",
            blocks=(
                Bullets(items=(
                    f"10:30 to 4:30 Mountain Time. Lunch {lunch.starts_at}, break {rest.starts_at}, evaluation {evaluation.starts_at}.",
                    "Three paths: VS Code on your laptop, VS Code at vscode.dev, or any AI assistant in a browser.",
                    "Every block starts by showing you the finished result.",
                    "Ask for anything: large print, a seat, a pause, a repeat.",
                )),
            ),
            notes=(
                "Name the exits and the restrooms, physically pointing.",
                "Say the last line slowly, then add: that is not an interruption of this workshop - it is this workshop.",
                "Say the three paths once: VS Code on a laptop, VS Code for the Web at vscode.dev, or the browser path with ChatGPT or another assistant at letitglow.app/ahg/assistant. Same blocks, same agent, same share. Anyone whose VS Code will not cooperate moves to the browser path and loses nothing.",
                f"The last five minutes, at {evaluation.starts_at}, belong to the session evaluation.",
            ),
            links=(("Choose your path", f"{SITE}/ahg/paths"),),
        ),
        Slide(
            id="ready", section="Opening", kicker="Before we build", title="Ready check",
            blocks=(
                Bullets(ordered=True, items=(
                    "VS Code: open your kit folder, open Copilot Chat, type /ready-check.",
                    "Browser: copy the ready check text from letitglow.app/ahg/assistant into your assistant.",
                    "Wait for: You are ready.",
                )),
                Para("Needs a hand? Raise it. A helper comes to you, and the room carries on.", big=True),
            ),
            notes=(
                "Give this five full minutes. Run /ready-check on the projector first, so everyone hears what ready sounds like.",
                "Copilot Chat opens with Control+Alt+I, or Control+Command+I on a Mac. Say the keys out loud.",
                "Helpers move now, to every raised hand and to anyone who has not typed anything. A laptop that will not cooperate goes to the browser path, which loses nothing.",
            ),
            links=(_card(0), ("The browser path", f"{SITE}/ahg/assistant")),
        ),
        Slide(
            id="kit", section="Opening", kicker="Your kit", title="What is in your kit",
            blocks=(
                Definitions(items=(
                    ("Step cards", "One per block: every key, and what you should hear."),
                    ("Examples", "Six finished agents. Start from one whenever you like."),
                    ("Sample course", "PSY 101, with barriers planted on purpose."),
                    ("Glossary and tutorial", "Every word we use, and how to write an agent."),
                )),
            ),
            notes=(
                "Open the kit folder on the projector and walk it top to bottom, out loud: step-cards, examples, sample-course, glossary.md, write-your-own-agent.md, and .github/skills, which holds the commands and the Accessibility Agents team.",
                "Everything is also online at letitglow.app/ahg/kit, readable without unzipping anything, and every slide in the HTML deck links to the part of the kit it is about.",
            ),
            links=(
                ("The kit, online", f"{SITE}/ahg/kit"),
                ("Glossary", _kit("glossary.md")),
                ("Write your own agent", _kit("write-your-own-agent.md")),
            ),
        ),
        Slide(
            id="site", section="Opening", kicker="letitglow.app/ahg", title="The website, page by page",
            blocks=(
                Definitions(items=(
                    ("Paths", "Choose VS Code, vscode.dev or a browser."),
                    ("Assistant", "One text per block, for the browser path."),
                    ("Share", "Where your agent goes public, in block 6."),
                    ("Slides", "This deck, with links into the kit."),
                )),
            ),
            notes=(
                "Show the home page on the projector and press each link once. People who know where things are ask fewer questions and get stuck for less time.",
                "Say that the slides, the kit and the website say the same things in the same words, so whichever one someone prefers, they are not missing anything.",
            ),
            links=(
                ("Paths", f"{SITE}/ahg/paths"),
                ("Assistant", f"{SITE}/ahg/assistant"),
                ("Share", f"{SITE}/ahg/share"),
                ("Slides", f"{SITE}/ahg/slides"),
            ),
        ),
        Slide(
            id="s6", section="Opening", kicker="Two rules, all day", title="Private stays private, and people decide",
            blocks=(
                Bullets(ordered=True, items=(
                    "Never paste anything private into any AI: student records, health or disability information, private identifying details.",
                    "Every agent ends with a person checking its work.",
                )),
                Para("If nobody is named, nobody reviewed it.", big=True),
            ),
            notes=(
                "We use a sample course all day, so there is never a reason to paste anything real.",
                "Set the AI context here, in under a minute. What today covers: agents that analyze course content, find barriers and draft fixes, grounded in checkers and cited standards. What it does not: replacing anyone, or trusting any answer without evidence.",
                "Say what makes it different from the other AI sessions this week: it is about higher education accessibility work at scale, built by the people who do that work, and every agent is open source.",
                "Name the reasons people hesitate - privacy, accuracy, other people's jobs - once, without dwelling. Rule one answers the first. Grounding answers the second. Rule two answers the third.",
            ),
        ),
        Slide(
            id="parts", section="Opening", kicker="How agents work", title="What makes up an agent",
            blocks=(
                Definitions(items=(
                    ("Instructions", "A file you write, in plain English."),
                    ("A model", "The AI that reads the instructions and does the work."),
                    ("Evidence", "Checker reports and standards it must use and cite."),
                    ("A person", "Who reviews its work before anything goes out."),
                )),
            ),
            notes=(
                "Walk it once with Maria's agent: her instructions say plan alternate formats; Copilot is the model; the GLOW audit of the scanned reading is the evidence; the alternate format specialist is the person.",
                "Say the point plainly: the model is the same for everyone in the room. What makes an agent good is the instructions and the evidence you give it, and the person who checks it. That is the part you build today.",
                "A team is several agents and a coordinator that routes work between them. That is block 5.",
            ),
            links=(("What makes a good agent file", _kit("agent-file-principles.md")),),
        ),
        Slide(
            id="s7", section="Opening", kicker="No code, really", title="The instructions are six answers",
            blocks=(
                Definitions(items=(
                    ("Role", "Who it is, and who it works for."),
                    ("Task", "The one job it does."),
                    ("Trusted guidance", "What it must cite: WCAG 2.2, your procedures."),
                    ("Output format", "What comes back, in a usable shape."),
                    ("Example", "One short, good answer."),
                    ("Human review", "Who checks it."),
                )),
            ),
            notes=(
                "This is the slide that lowers the shoulders. Say it twice: if you can write instructions for a new colleague, you can write an agent.",
                "The file format is the same one the open-source Accessibility Agents project uses, which is why their agents and yours can work in the same team this afternoon.",
            ),
            links=(("Write your own agent", _kit("write-your-own-agent.md")),),
        ),
        Slide(
            id="automation", section="Opening", kicker="Before you trust it", title="Automation helps. You decide.",
            blocks=(
                Table(
                    caption="What an agent does well, and what stays with you",
                    headers=("An agent is good at", "You must still"),
                    rows=(
                        ("Reading a whole course quickly", "Know what accessible looks like"),
                        ("Explaining a checker's findings", "Check its claims against the evidence"),
                        ("Drafting fixes and plans", "Decide what goes out, and sign it"),
                        ("Citing the standard", "Spot what no checker sees"),
                    ),
                ),
                Para("An agent can be confidently wrong. Your judgment is the safeguard.", big=True),
            ),
            notes=(
                "This is the most important slide of the morning. Automation multiplies whatever you give it: good instructions and good evidence scale good work, and a careless agent scales mistakes just as fast.",
                "Name the critical things out loud: never paste private data; never call anything compliant on an agent's word; read every finding before it reaches a student or a faculty member; and know enough WCAG to tell when an answer is wrong.",
                "Block 3 tests missing evidence. Catch any guesses, but celebrate an agent that asks for the evidence instead.",
            ),
            links=(("Glossary: human review and grounding", _kit("glossary.md")),),
        ),
        Slide(
            id="s8", section="Opening", kicker="Agents in action", title="Your accessibility office",
            blocks=(
                Table(
                    caption="The agent team you join this afternoon",
                    headers=("Specialist", "Takes"),
                    rows=(
                        ("Word, PowerPoint, Excel", "Syllabi, decks, gradebooks"),
                        ("PDF", "Readings, forms, scans"),
                        ("Web pages", "Course pages"),
                        ("Captions and media", "Lecture captions"),
                        ("Plain language", "Anything a student acts on"),
                        ("Standards reviewer", "Everyone's findings, last"),
                        ("Your agent", "Whatever you build it to do"),
                    ),
                ),
            ),
            notes=(
                "A coordinator routes each file to the specialist it needs. Read the specialists down the list. Pause on the last row: the team has an empty chair, and it is theirs.",
                "These specialists are adapted from the open-source Accessibility Agents project. That is where their agents go this afternoon too.",
            ),
            links=(("The office team", f"{SITE}/ahg/kit#office-team"),),
        ),
        # -- Block 2: design your agent -------------------------------------
        Slide(
            id="s9", section="Design", kicker=_you_are_here(2), title="Design your agent",
            blocks=(
                Para("You leave with: version 1 of your agent."),
                Definitions(items=(
                    ("Documents and alternate formats", "A format planner, or a triage agent."),
                    ("Course content and faculty", "A faculty coach, or a course page coach."),
                    ("Compliance and procurement", "A remediation log, or a vendor report reader."),
                )),
                Para("Pick one card, and one task your office does every week, with nothing private in it."),
            ),
            notes=(
                _journey_note(2),
                "Every card has two ready-made agents in examples/agents. Nobody starts from a blank page; everybody starts from something that already works and makes it theirs.",
            ),
            links=(_card(2), ("Ready-made agents", f"{SITE}/ahg/kit#examples-agents")),
        ),
        Slide(
            id="s10", section="Design", kicker="Watch me first", title="Maria's six answers",
            blocks=(
                Table(
                    caption="Maria's alternate format planner",
                    headers=("Question", "Maria's answer"),
                    rows=(
                        ("Role", "Alternate format planner"),
                        ("Task", "Plan formats from checker reports"),
                        ("Trusted guidance", "WCAG 2.2, ACB large print"),
                        ("Output format", "Numbered steps, who does each"),
                        ("Example", "Scanned reading to large print"),
                        ("Human review", "A specialist checks it"),
                    ),
                ),
            ),
            notes=(
                "Read Maria's answers aloud. Then type /design-my-agent in Copilot Chat on the projector and answer as Maria, so they hear the whole conversation once before they have theirs.",
                "Fill in what the table shortens: she works in a disability resource center; her guidance cites WCAG 2.2 1.4.5 and 1.1.1 by number and her office's own procedure; her example gets the text out of the scan first, then 18 point large print; and the student confirms the format works for them.",
                "Say that the browser path is the same conversation: the block 2 text from letitglow.app/ahg/assistant pasted into ChatGPT asks the same questions in the same order.",
                "Joke if the room is warm: Maria's coffee machine has been out of order since August. Her agent does not drink coffee, which is its main advantage.",
            ),
            links=(("Maria's agent, in full", _kit("examples/maria-alternate-format-planner.md")),),
        ),
        Slide(
            id="s11", section="Design", kicker="Your turn", title="Your AI asks, you answer",
            blocks=(
                Bullets(ordered=True, items=(
                    "VS Code: in Copilot Chat, type /design-my-agent.",
                    "Browser: paste the block 2 text into your assistant.",
                    "Answer one question at a time. Borrow from the examples.",
                )),
                Para("Stuck? Start from a ready-made agent. That counts.", big=True),
            ),
            notes=(
                "VS Code writes the agent into my-agent/SKILL.md. In a browser it comes back in a box with a Copy button; download it from the share page.",
                "You are on track when your AI tells you one thing your agent does well.",
                "Helpers move now. Look for the person who has not typed anything yet, and sit with them quietly.",
                "Step card 2 has every key and every expected screen in words, for screen reader users and anyone who prefers paper.",
            ),
            links=(_card(2), ("Block 2 text for a browser", f"{SITE}/ahg/assistant")),
        ),
        # -- Block 3: your agent at work ------------------------------------
        Slide(
            id="s12", section="Design", kicker=_you_are_here(3), title="Your agent at work",
            blocks=(
                Bullets(ordered=True, items=(
                    "Type /try-my-agent, or paste the block 3 text.",
                    "Pick a file from the PSY 101 sample course.",
                    "Read the answer. Then /review-my-agent: version 2.",
                )),
                Para("No evidence? A good agent asks instead of guessing.", big=True),
                Para("Behind? Try a ready-made agent from examples/agents instead."),
            ),
            notes=(
                _journey_note(3),
                "PSY 101 is fictional: a course about memory and procrastination that keeps forgetting things and running late. The barriers in it are planted on purpose; the answer key is in the facilitator folder.",
            ),
            links=(_card(3), ("The sample course", f"{SITE}/ahg/kit#sample-course")),
        ),
        Slide(
            id="s13", section="Design", kicker="Watch me", title="Maria's first answer",
            blocks=(
                Panel(lines=(
                    "\"Run Acrobat's Make Accessible, add alt text to all images, and increase the font size. This will make it compliant.\"",
                )),
                Bullets(items=(
                    "It never saw the file, so it missed that it is a scan.",
                    "Alt text cannot turn pictures of text into text.",
                    "It said \"compliant\", which it is told never to say.",
                )),
            ),
            notes=(
                "Read the quote in a confident voice, then the three problems in a normal one. The contrast is the joke, and the lesson. It is the automation slide, happening.",
                "This is a written example, labelled as one in the kit. On the day, show a real first answer from the room if someone offers one.",
            ),
        ),
        Slide(
            id="s14", section="Lunch", kicker=f"Lunch - {lunch.clock}", title=f"Back at {lunch.resume}",
            blocks=(
                Para("You have an agent. That was the hard part."),
                Para("After lunch: evidence you can verify."),
                Para("Before you go: two questions, no name, at letitglow.app/ahg/check-in."),
            ),
            notes=(
                "Say well done, and mean it. Most people in this room had never written an agent at 10:30.",
                "Ask everyone to do the check-in before they leave the room. Helpers read the results over lunch at letitglow.app/ahg/check-in/results with the survey key, and go first to anyone who said they are stuck.",
                "Anyone still setting up: lunch is when a helper finishes it with them.",
            ),
            links=(("Check in", f"{SITE}/ahg/check-in"),),
        ),
        # -- Block 4: ground it ---------------------------------------------
        Slide(
            id="s15", section="Afternoon", kicker=_you_are_here(4), title="Ground it",
            blocks=(
                Bullets(ordered=True, items=(
                    "Type /ground-my-agent, or paste the block 4 text.",
                    "Same file as this morning, with its checker report.",
                    "Compare the two answers.",
                    "Then /review-my-agent: version 3.",
                )),
                Para("Behind? Ground Maria's agent instead. Same lesson."),
            ),
            notes=(
                _journey_note(4),
                "The checker report is GLOW's audit for documents and axe for the web page.",
                "Grounding supports the trusted in the session title. It reduces guessing but does not guarantee correctness. Check the source, the citation and what the checker did not test; a person decides.",
            ),
            links=(_card(4), ("Checker reports for PSY 101", f"{SITE}/ahg/kit#sample-course")),
        ),
        Slide(
            id="s16", section="Afternoon", kicker="Watch me", title="Before and after",
            blocks=(
                Table(
                    caption="Maria's agent, on the scanned reading",
                    headers=("Before evidence", "After evidence"),
                    rows=(
                        ("Guessed an ordinary PDF", "Knew it was pictures of text"),
                        ("WCAG 2.1, no links", "WCAG 2.2, 1.4.5, linked"),
                        ("\"Compliant\"", "What was checked, and what a person must check"),
                        ("Fix the PDF", "A clean source, then large print and audio"),
                    ),
                ),
            ),
            notes=(
                "Read both columns, row by row.",
                "Then ask one volunteer to read their own before and after. One is enough, and applaud it.",
            ),
        ),
        Slide(
            id="s17", section="Afternoon", kicker="The skill, not the tool", title="Any checker, and a person",
            blocks=(
                Para("Word's, PowerPoint's or Acrobat's checker, or Accessibility Insights, work the same way."),
                Para("Some barriers no checker sees:"),
                Bullets(items=(
                    "An accommodations policy contradicted elsewhere.",
                    "Alt text that says \"image.png\".",
                    "A lab that only works if you can see color.",
                    "Captions that turn Ebbinghaus into \"ebb in house\".",
                )),
            ),
            notes=(
                "The skill is giving your agent evidence, whatever the tool.",
                "If Word is handy, show Review, then Check Accessibility on the syllabus, and paste its results into Copilot with the agent. Same skill, different tool.",
                "The accommodations statement is last in the syllabus, and contradicted two sections earlier by a no-makeup-exams rule in capitals.",
                "Those four barriers are why every agent has a human review step. Read each one; the room will recognise every one of them from their own campus.",
            ),
        ),
        Slide(
            id="s18", section="Afternoon", kicker=f"Break - {rest.minutes} minutes", title=f"Back at {rest.resume}",
            blocks=(Para("Next, your agent joins a team. Then it goes public."),),
            notes=("Short break on purpose. The next two blocks are where the day comes together.",),
        ),
        # -- Block 5: build the office --------------------------------------
        Slide(
            id="s19", section="Afternoon", kicker=_you_are_here(5), title="Build the office",
            blocks=(
                Bullets(ordered=True, items=(
                    "Type /run-the-office, or paste the block 5 text.",
                    "The coordinator sends each file to its specialists, and to yours.",
                    "The standards-reviewer role checks the draft; staff still review it.",
                    "Then /review-my-agent: version 4, your best.",
                )),
                Para("Behind? The office runs with any version of your agent."),
            ),
            notes=(
                _journey_note(5),
                "You get one team report, with your agent's section in it.",
                "This is building an agent team: they added a specialist, and their coordinator is running it. Copilot announces each file as it finishes, so screen reader users hear progress, not silence.",
                "On the browser path the same coordinator and specialists travel inside the block 5 text, so ChatGPT or any assistant runs the same team. If an assistant stops part way, type continue.",
            ),
            links=(_card(5), ("The office team", f"{SITE}/ahg/kit#office-team")),
        ),
        Slide(
            id="s20", section="Afternoon", kicker="What scale looks like", title="One course, one report",
            blocks=(
                Bullets(items=(
                    "Seven files, eight specialists, plus yours.",
                    "Every finding: evidence, a WCAG 2.2 link, a named reviewer.",
                    "A list of what the supplied evidence cannot establish.",
                )),
                Para("Quality, accountability and transparency, at scale.", big=True),
            ),
            notes=(
                "The report opens with three lines a director will actually read. It is also a Tuesday.",
                "One assistant follows specialist roles in sequence here; this is not independent validation. Seven sample files demonstrate the method, not production throughput. Review effort, errors and deadlines decide whether a campus pilot can grow.",
                "Ask: what would it take to run this across ten courses? Let them answer. The honest answer is a person's review time, which is exactly where it should go.",
            ),
        ),
        Slide(
            id="s21", section="Afternoon", kicker="The real thing", title="The full Accessibility Agents team",
            blocks=(
                Para("The office you just ran is a small version of a real open-source project."),
                Bullets(items=(
                    "Six entry points, and 107 skills behind them.",
                    "Already in your kit, in .github/skills.",
                    "Ask for document-accessibility-wizard by name.",
                )),
            ),
            notes=(
                "Fifteen minutes, on the projector, in VS Code with the kit open. Start a new chat and ask: use document-accessibility-wizard to review the PSY 101 course, using the files in sample-course/evidence. Web, Word, PowerPoint, Excel and PDF, on the screen.",
                "Point out that the skills that need scanners say so and ask for checker results, as accessibility-agents-in-the-kit.md explains. Never let it claim a scan it did not run.",
                "Close with: your agent goes into this project tonight, credited to you. That is the next block.",
            ),
            links=(
                ("Accessibility Agents", _kit("accessibility-agents.md")),
                ("What is in the kit's copy", _kit("accessibility-agents-in-the-kit.md")),
            ),
        ),
        # -- Block 6: share it ----------------------------------------------
        Slide(
            id="s22", section="Afternoon", kicker=_you_are_here(6), title="Share it",
            blocks=(
                Bullets(ordered=True, items=(
                    "Open letitglow.app/ahg/share, and choose your newest SKILL.md.",
                    "Press Open the share form on GitHub.",
                    "Check the privacy box, and press Submit new issue.",
                    "Within a minute: Your agent is in.",
                )),
                Para("Behind? Share any version. Version 1 counts."),
            ),
            notes=(
                _journey_note(6),
                "You can also paste the agent in instead of choosing the file. The form opens already filled in.",
                "Everyone shared a practice agent before the day, so this is the second time, not the first. Say so; it changes the room.",
                "Helpers watch the issues labelled needs-a-hand and go to those people first. A Nearly there reply always says exactly what to fix.",
                "If sharing is not approved or GitHub is unavailable, save a reviewed draft and a next step. Do not call it published, and do not collect it without permission.",
            ),
            links=(_card(6), ("Share your agent", f"{SITE}/ahg/share")),
        ),
        Slide(
            id="s23", section="Afternoon", kicker="Open source, live", title="In the collection, with your name on it",
            blocks=(
                Para("As your agents arrive, the collection grows, here, on the screen."),
                Para("Tonight they all go into Accessibility Agents, every author credited.", big=True),
            ),
            notes=(
                "Project agents/README.md in github.com/Community-Access/ahg-2026 and refresh it as agents arrive. Read each name and agent title out loud. Applause is allowed and encouraged.",
                "The collection is for anyone in higher education to use and improve.",
                "Each agent is committed in its author's name, so it shows on their own GitHub profile. Started from a ready-made agent? It still counts. Say so: what matters is that it is yours now.",
            ),
            links=(("The AHG 2026 collection", "https://github.com/Community-Access/ahg-2026"),),
        ),
        Slide(
            id="s24", section="Afternoon", kicker="Agents in action", title="Everyone's agents, together",
            blocks=(
                Para("One more run, on the screen: the office team with every agent this room shared."),
                Para("Listen for yours."),
            ),
            notes=(
                "Last thing in this block. Copy every agents/<login>/<name>/ folder from the ahg-2026 repository into a room/ folder in your kit, then run /run-the-office on the projector. Read out each agent's name as the coordinator calls it.",
                "If the run is slow, narrate it. If it stumbles, say what happened and why; a real failure explained well teaches more than a perfect demo.",
            ),
        ),
        # -- Block 7: take it home ------------------------------------------
        Slide(
            id="s25", section="Close", kicker=_you_are_here(7), title="Take it home",
            blocks=(
                Bullets(ordered=True, items=(
                    "Type /my-30-day-plan, or paste the block 7 text.",
                    f"Add your one-sentence commitment at {ctx.join_display}/11.",
                )),
                Para("Small is the point.", big=True),
                Para("Behind? Adapt a worked example with a helper."),
            ),
            notes=(
                _journey_note(7),
                "Try up to five fictional or approved non-sensitive examples beside the existing process. Include review time, errors and delivery time in the comparison. Never delay an accommodation for a pilot.",
                "Reserve five minutes for a partner to check the plan: input, output destination, reviewer role, deadline, approval, day-30 measure and stop rule. If AI is not approved, a paper workflow and approval request count.",
                "The commitment goes on the wall, with no names on it.",
            ),
            links=(_card(7),),
        ),
        Slide(
            id="fit", section="Close", kicker="Your office", title="Plug it into the work you already do",
            blocks=(
                Table(
                    caption="Where an agent fits in work you already do",
                    headers=("In your office", "The agent drafts", "A person"),
                    rows=(
                        ("Alternate format request", "The production plan", "Approves it"),
                        ("Course review before term", "Findings by course", "Assigns the fixes"),
                        ("A faculty question", "A coaching reply", "Edits and sends"),
                        ("A vendor's accessibility report", "The gaps", "Decides to buy"),
                    ),
                ),
            ),
            notes=(
                "This is the slide that turns today into Tuesday. An agent helps most at one step of a workflow the office already runs, not as a new process beside it.",
                "Read the four questions slowly: what starts it, what it reads, where its draft goes, who signs off. Their 30-day plan asks exactly these.",
                "Say plainly: use the AI assistant your campus approves, and follow its rules on what information may go in. Nothing private, today or on Monday.",
                "Keep drafts beside the existing process for a month. Record evidence source/date, agent version, reviewer decision and unresolved barriers in the approved log. Stop for private data, unverifiable evidence or missing review.",
            ),
            links=(_card(7), ("Putting it to work in your office", _kit("write-your-own-agent.md"))),
        ),
        Slide(
            id="monday", section="Close", kicker="With tools you already have", title="On Monday",
            blocks=(
                Table(
                    caption="What you learned, and what you can use it with on Monday",
                    headers=("You learned", "Monday, with"),
                    rows=(
                        ("Writing an agent", "Your campus-approved AI assistant"),
                        ("Grounding it", "Office and Acrobat checkers, Accessibility Insights, axe"),
                        ("Human review", "Your own office's process"),
                        ("Agent teams", "One specialist at a time, or Accessibility Agents"),
                    ),
                ),
            ),
            notes=(
                "Start with tools your campus already approves. Availability, subscriptions and data rules differ; no new purchase is required to map a workflow on paper.",
                "Point at Accessibility Agents for anyone who wants the whole team on their own laptop.",
            ),
            links=(("Accessibility Agents", _kit("accessibility-agents.md")),),
        ),
        Slide(
            id="s26", section="Close", kicker=commitments.starts_at, title="The commitment wall",
            blocks=(
                Para("Every commitment in this room, on one screen, with no names on it."),
            ),
            notes=(
                "Project the wall from GLOW. Read three aloud. Do not comment on them, do not rank them.",
                "Then go straight to the evaluation. The last five minutes belong to it.",
            ),
        ),
        Slide(
            id="s27", section="Close", kicker=f"{evaluation.starts_at} - Thank you", title="Go make one more champion",
            blocks=(
                Para("You came in with a problem. You leave with an agent, a team and a plan.", lead=True),
                Para("Now: the session evaluation. It shapes next year's conference."),
                Para("Help any time: jeffbis@arizona.edu"),
                Para(DECK_CREDIT, small=True),
            ),
            notes=(
                "Say it, thank them, and hand over to the proctor for the evaluation. Then stop talking while people fill it in.",
                "No question block here. Answer at the tables while people pack up.",
                "GLOW is a community project of BITS, an affiliate of the American Council of the Blind.",
            ),
            links=(
                ("University of Arizona accessibility", "https://accessibility.arizona.edu"),
                ("BITS", "https://www.bits-acb.org"),
                ("Techopolis", "https://www.techopolis.app"),
            ),
        ),
    ])


def _where_you_are(slides: list[Slide]) -> list[Slide]:
    """Put "Block 2 of 7, slide 2 of 3" on every slide inside a block.

    Someone who drifted, stepped out or lost the thread finds their place
    from the slide alone, without asking. Lunch, the break and the close
    belong to no block and are left as they are.
    """
    owners: list[int] = []
    block = 1
    for slide in slides:
        if slide.kicker.startswith("Block ") and " of 7" in slide.kicker:
            block = int(slide.kicker.split()[1])
        owners.append(0 if slide.id in _OUTSIDE_BLOCKS else block)
    placed = []
    for slide, owner in zip(slides, owners, strict=True):
        if owner and not slide.kicker.startswith("Block "):
            members = [i for i, o in enumerate(owners) if o == owner]
            position = members.index(len(placed)) + 1
            slide = replace(slide, kicker=f"Block {owner} of 7, slide {position} of {len(members)} - {slide.kicker}")
        elif owner:
            members = [i for i, o in enumerate(owners) if o == owner]
            prefix = f"Block {owner} of 7 - "
            slide = replace(slide, kicker=slide.kicker.replace(prefix, f"Block {owner} of 7, slide 1 of {len(members)} - ", 1))
        placed.append(slide)
    return placed


#: The title slide, lunch, the break and the close: slides that belong to no
#: block, or (the title) that are shown before anyone is looking for their place.
_OUTSIDE_BLOCKS = frozenset({"s1", "s14", "s18", "s26", "s27"})


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------


def build_deck_markdown(ctx: DeckContext) -> str:
    """The deck as Markdown: headings, lists, pipe tables, nothing clever.

    No bold and no italic. Structure carries the emphasis -- a heading for
    each slide and for its notes -- which is what GLOW's own Markdown audit
    asks of everybody else's documents.
    """
    lines: list[str] = [
        "---",
        f'title: "{DECK_TITLE}: {DECK_SUBTITLE}"',
        "lang: en",
        f'author: "{DECK_BYLINE}"',
        f'description: "The {DECK_EVENT} deck, with speaker notes."',
        "---",
        "",
        f"# {DECK_TITLE}",
        "",
        f"{DECK_SUBTITLE}",
        "",
        f"- Event: {DECK_EVENT}",
        f"- Presenter: {DECK_BYLINE}",
        f"- {DECK_CREDIT}",
        f"- Join: {ctx.join_display}",
        "",
        f"Speaker notes are included under each slide. {len(build_slides(ctx))} slides.",
        "",
        "---",
        "",
    ]

    for index, slide in enumerate(build_slides(ctx), start=1):
        lines.append(f"## {index}. {slide.title}")
        lines.append("")
        if slide.kicker:
            lines.append(slide.kicker)
            lines.append("")
        for block in slide.blocks:
            lines.extend(_markdown_block(block))
        if slide.links:
            lines.append(LINKS_LABEL)
            lines.append("")
            lines.extend(f"- [{label}]({url})" for label, url in slide.links)
            lines.append("")
        if slide.notes:
            lines.append(f"### Speaker notes, slide {index}")
            lines.append("")
            for note in slide.notes:
                lines.append(f"> {note}")
                lines.append(">")
            if lines[-1] == ">":
                lines.pop()
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


_PATH_RE = re.compile(r"(?<![`\w])((?:[\w.-]+/)+[\w.-]+\.(?:md|html|txt)|[\w.-]+/(?=\s|$|[.,]))")


def _md(text: str) -> str:
    """File and folder names as inline code, so they read as names."""
    return _PATH_RE.sub(lambda m: "`" + m.group(1) + "`", text)


def _markdown_block(block: Content) -> list[str]:
    if isinstance(block, Para):
        return [_md(block.text), ""]
    if isinstance(block, Url):
        return [f"### {block.text}", ""]
    if isinstance(block, Bullets):
        out = []
        for position, item in enumerate(block.items, start=1):
            out.append(f"{position}. {_md(item)}" if block.ordered else f"- {_md(item)}")
        out.append("")
        return out
    if isinstance(block, Definitions):
        out = [f"- {term}: {_md(meaning)}" for term, meaning in block.items]
        out.append("")
        return out
    if isinstance(block, Panel):
        out = [f"> {line}" for line in block.lines]
        out.append("")
        return out
    if isinstance(block, Table):
        out = [block.caption, ""]
        out.append("| " + " | ".join(block.headers) + " |")
        out.append("|" + "|".join(["---"] * len(block.headers)) + "|")
        for row in block.rows:
            out.append("| " + " | ".join(row) + " |")
        out.append("")
        return out
    return []  # pragma: no cover - every kind is handled above


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------


def build_deck_docx_bytes(ctx: DeckContext) -> bytes:
    """The deck as a Word document in ACB large print.

    Real heading styles so the navigation pane and a screen reader's heading
    list both work; real list styles rather than typed hyphens; a marked
    header row on each table; and a declared language so a screen reader
    does not guess at pronunciation.
    """
    from acb_large_print.template import apply_acb_large_print  # type: ignore
    from docx import Document  # type: ignore
    from docx.oxml.ns import qn  # type: ignore

    # GLOW's own ACB styles, so the deck passes GLOW's own audit: 22pt and
    # 20pt headings, no italic, one-inch margins, page numbers, a title and
    # a language. Emphasis comes from structure, not from bold body text.
    doc = apply_acb_large_print(Document(), title=DECK_TITLE)

    # Also on the Normal style itself, for readers that ignore docDefaults.
    rpr = doc.styles["Normal"].element.get_or_add_rPr()
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = rpr.makeelement(qn("w:lang"), {})
        rpr.append(lang)
    lang.set(qn("w:val"), "en-US")

    doc.core_properties.subject = DECK_SUBTITLE
    doc.core_properties.author = DECK_BYLINE

    doc.add_heading(DECK_TITLE, level=1)
    doc.add_paragraph(DECK_SUBTITLE)
    doc.add_paragraph(f"Event: {DECK_EVENT}")
    doc.add_paragraph(f"Presenter: {DECK_BYLINE}")
    doc.add_paragraph(DECK_CREDIT)
    doc.add_paragraph(f"Join: {ctx.join_display}")
    doc.add_paragraph(
        "Speaker notes follow each slide, under a heading of their own, so "
        "they can be skipped by heading navigation or read deliberately."
    )

    for index, slide in enumerate(build_slides(ctx), start=1):
        doc.add_page_break()
        doc.add_heading(f"{index}. {slide.title}", level=2)
        if slide.kicker:
            doc.add_paragraph(slide.kicker)
        for block in slide.blocks:
            _docx_block(doc, block)
        if slide.links:
            doc.add_paragraph(LINKS_LABEL)
            for label, url in slide.links:
                _docx_link(doc.add_paragraph(style="List Bullet"), label, url)
        if slide.notes:
            # Numbered, so a heading list reads "Speaker notes, slide 4"
            # rather than thirty identical entries.
            doc.add_heading(f"Speaker notes, slide {index}", level=3)
            for note in slide.notes:
                doc.add_paragraph(note)

    out = BytesIO()
    doc.save(out)
    return out.getvalue()


def build_deck_handout_docx_bytes(ctx: DeckContext) -> bytes:
    """The slides as a large print handout: no speaker notes, links written out.

    For anyone who would rather follow on paper, or in Word at their own
    size, than read a projector. Every link shows its address, because a
    printed page cannot be clicked.
    """
    from acb_large_print.template import apply_acb_large_print  # type: ignore
    from docx import Document  # type: ignore

    doc = apply_acb_large_print(Document(), title=f"{DECK_TITLE}: large print handout")
    doc.core_properties.subject = DECK_SUBTITLE
    doc.core_properties.author = DECK_BYLINE
    doc.core_properties.language = "en-US"

    doc.add_heading(f"{DECK_TITLE}: large print handout", level=1)
    doc.add_paragraph(DECK_SUBTITLE)
    doc.add_paragraph(f"{DECK_EVENT}. {DECK_BYLINE}.")
    doc.add_paragraph(
        "Every slide, in order, without the speaker notes. Each slide's links are "
        "written out in full, so they work on paper too."
    )

    for index, slide in enumerate(build_slides(ctx), start=1):
        doc.add_heading(f"{index}. {slide.title}", level=2)
        if slide.kicker:
            doc.add_paragraph(slide.kicker)
        for block in slide.blocks:
            _docx_block(doc, block)
        if slide.links:
            doc.add_paragraph(LINKS_LABEL)
            for label, url in slide.links:
                shown = url.split("://", 1)[-1]
                _docx_link(doc.add_paragraph(style="List Bullet"), f"{label}: {shown}", url)

    out = BytesIO()
    doc.save(out)
    return out.getvalue()


def _docx_link(paragraph, label: str, url: str) -> None:
    """A real hyperlink, which python-docx has no call for.

    The label is the link text, so a screen reader's links list reads
    "Step card 2" rather than an address spelled out a character at a time.
    """
    from docx.opc.constants import RELATIONSHIP_TYPE as RT  # type: ignore
    from docx.oxml.ns import qn  # type: ignore

    rel_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = paragraph._p.makeelement(qn("w:hyperlink"), {qn("r:id"): rel_id})
    # The ScreenTip. Word's PDF export writes it as the link's Contents,
    # which PDF/UA requires of every link (veraPDF 7.18.1-2 and 7.18.5-2).
    link.set(qn("w:tooltip"), label)
    run = link.makeelement(qn("w:r"), {})
    r_pr = run.makeelement(qn("w:rPr"), {})
    style = r_pr.makeelement(qn("w:rStyle"), {qn("w:val"): "Hyperlink"})
    r_pr.append(style)
    underline = r_pr.makeelement(qn("w:u"), {qn("w:val"): "single"})
    r_pr.append(underline)
    run.append(r_pr)
    text = run.makeelement(qn("w:t"), {})
    text.text = label
    run.append(text)
    link.append(run)
    paragraph._p.append(link)


def _docx_block(doc, block: Content) -> None:
    from docx.oxml.ns import qn  # type: ignore

    # Every paragraph is body text at the style's 18pt. Larger or bold body
    # text is what GLOW's auditor reports as a faux heading, and on paper it
    # is one: a reader cannot tell a big line from a section break.
    if isinstance(block, Para):
        doc.add_paragraph(block.text)
        return

    if isinstance(block, Url):
        doc.add_paragraph(f"Address: {block.text}")
        return

    if isinstance(block, Bullets):
        style = "List Number" if block.ordered else "List Bullet"
        for item in block.items:
            doc.add_paragraph(item, style=style)
        return

    if isinstance(block, Definitions):
        for term, meaning in block.items:
            doc.add_paragraph(f"{term}: {meaning}", style="List Bullet")
        return

    if isinstance(block, Panel):
        for line in block.lines:
            # Not "Intense Quote": Word's version is italic, blue and centred.
            doc.add_paragraph(line)
        return

    if isinstance(block, Table):
        doc.add_paragraph(block.caption)
        table = doc.add_table(rows=1, cols=len(block.headers))
        table.style = "Table Grid"
        header_cells = table.rows[0].cells
        for position, heading in enumerate(block.headers):
            header_cells[position].text = heading
        # Mark the header row so it repeats across pages and is announced as
        # a header row rather than data.
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        tbl_header = tr_pr.makeelement(qn("w:tblHeader"), {})
        tr_pr.append(tbl_header)

        for row in block.rows:
            cells = table.add_row().cells
            for position, value in enumerate(row):
                cells[position].text = value
        doc.add_paragraph("")
        return


# ---------------------------------------------------------------------------
# PowerPoint
# ---------------------------------------------------------------------------


def build_deck_pptx_bytes(ctx: DeckContext) -> bytes:
    """The deck as PowerPoint, built the way a screen reader needs it.

    Every slide uses a layout with a real title placeholder and a real body
    placeholder, filled in that order. That is not cosmetic: placeholder
    order is the reading order PowerPoint reports, and a deck assembled from
    free-floating text boxes reads in creation order, which is rarely the
    order anyone means.

    Tables carry alt text, the deck declares its language and title, and
    speaker notes go in the notes slide rather than into a shape on the
    slide itself.
    """
    from pptx import Presentation  # type: ignore
    from pptx.util import Inches, Pt  # type: ignore

    prs = Presentation()
    prs.slide_width = Inches(13.333)   # 16:9
    prs.slide_height = Inches(7.5)

    prs.core_properties.title = DECK_TITLE
    prs.core_properties.subject = DECK_SUBTITLE
    prs.core_properties.author = DECK_BYLINE
    prs.core_properties.language = "en-US"

    title_and_content = prs.slide_layouts[1]
    title_only = prs.slide_layouts[5]

    for slide_data in build_slides(ctx):
        has_table = any(isinstance(b, Table) for b in slide_data.blocks)
        layout = title_only if has_table else title_and_content
        slide = prs.slides.add_slide(layout)

        # The default layouts are drawn for 4:3. Stretch the title and body
        # placeholders across the 16:9 slide, or text wraps at two thirds of
        # the width and the title sits off centre.
        # Setting one coordinate on an inherited placeholder zeroes the rest,
        # so all four are set.
        for placeholder in slide.placeholders:
            is_title = placeholder.placeholder_format.idx == 0
            placeholder.left = Inches(0.6)
            placeholder.width = Inches(12.1)
            placeholder.top = Inches(0.4) if is_title else Inches(1.7)
            placeholder.height = Inches(1.0) if is_title else Inches(5.4)
        slide.shapes.title.text = slide_data.title
        for paragraph in slide.shapes.title.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(36)
                run.font.name = "Arial"
                run.font.bold = True

        if has_table:
            _pptx_table_slide(slide, slide_data, Inches, Pt)
        else:
            _pptx_body_slide(slide, slide_data, Pt)

        notes = list(slide_data.notes)
        if slide_data.kicker:
            notes.insert(0, f"[{slide_data.kicker}]")
        slide.notes_slide.notes_text_frame.text = "\n\n".join(notes)

    out = BytesIO()
    prs.save(out)
    return out.getvalue()


#: The smallest text on any projected slide, kicker and table cells included.
#: 24pt is the usual floor for a projected room; the ACB's 18pt is for print
#: held in the hand, not for the back row.
PPTX_FLOOR_PT = 24


def _pptx_links(frame, links: tuple[tuple[str, str], ...], Pt, *, first: bool) -> None:
    """One line, "In the kit and on the site:" then each label as a real link."""
    paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
    lead = paragraph.add_run()
    lead.text = LINKS_LABEL + " "
    for position, (label, url) in enumerate(links):
        if position:
            sep = paragraph.add_run()
            sep.text = ", "
        run = paragraph.add_run()
        run.text = label
        run.hyperlink.address = url
    for run in paragraph.runs:
        run.font.size = Pt(PPTX_FLOOR_PT)
        run.font.name = "Arial"
    return paragraph


def _pptx_body_slide(slide, slide_data: Slide, Pt) -> None:
    """Fill the layout's body placeholder. Never a floating text box."""
    from pptx.oxml.ns import qn  # type: ignore

    body = None
    for placeholder in slide.placeholders:
        if placeholder.placeholder_format.idx != 0:
            body = placeholder
            break
    if body is None:  # pragma: no cover - layout 1 always has a body
        return

    frame = body.text_frame
    frame.word_wrap = True
    first = True

    def _no_marker(paragraph, level: int) -> None:
        # Without this the body layout puts a bullet on every line: a dash
        # before "1." on a numbered item, and on a plain paragraph a list
        # that a screen reader announces as one.
        p_pr = paragraph._p.get_or_add_pPr()
        if level == 0:
            p_pr.set("marL", "0")
            p_pr.set("indent", "0")
        p_pr.insert(0, p_pr.makeelement(qn("a:buNone"), {}))

    def _para(text: str, *, level: int = 0, size: int = PPTX_FLOOR_PT, bold: bool = False, marker: bool | None = None):
        nonlocal first
        paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
        first = False
        paragraph.text = text
        paragraph.level = level
        if marker is None:
            marker = level > 0
        if not marker:
            _no_marker(paragraph, level)
        for run in paragraph.runs:
            run.font.size = Pt(size)
            run.font.name = "Arial"
            run.font.bold = bold
        return paragraph

    if slide_data.kicker:
        _para(slide_data.kicker)

    for block in slide_data.blocks:
        if isinstance(block, Para):
            size = 32 if block.big else (28 if block.lead else PPTX_FLOOR_PT)
            _para(block.text, size=size, bold=block.big)
        elif isinstance(block, Url):
            _para(block.text, size=36, bold=True)
        elif isinstance(block, Bullets):
            for position, item in enumerate(block.items, start=1):
                text = f"{position}. {item}" if block.ordered else item
                _para(text, level=1, marker=not block.ordered)
        elif isinstance(block, Definitions):
            for term, meaning in block.items:
                _para(f"{term}: {meaning}", level=1)
        elif isinstance(block, Panel):
            for line in block.lines:
                _para(line, level=1)

    if slide_data.links:
        paragraph = _pptx_links(frame, slide_data.links, Pt, first=first)
        _no_marker(paragraph, 0)


def _pptx_lines(text: str, chars_per_line: int = 70) -> int:
    """Roughly how many lines *text* wraps to at 24pt across the slide."""
    return max(1, -(-len(text) // chars_per_line))


def _pptx_table_slide(slide, slide_data: Slide, Inches, Pt) -> None:
    """A title-only slide carrying one table, captioned and alt-texted."""
    caption = ""
    table_block = None
    intro: list[str] = []
    after: list[str] = []
    for block in slide_data.blocks:
        target = after if table_block is not None else intro
        if isinstance(block, Table):
            table_block = block
            caption = block.caption
        elif isinstance(block, Para):
            target.append(block.text)
        elif isinstance(block, Bullets):
            # Steps on a table slide must not be dropped: on the take-home
            # slide they are the instructions.
            target.extend(
                f"{n}. {item}" if block.ordered else item
                for n, item in enumerate(block.items, start=1)
            )
        elif isinstance(block, Definitions):
            target.extend(f"{term}: {meaning}" for term, meaning in block.items)

    line_height = 0.42   # inches: 24pt text at 1.2 leading
    top = 1.5
    # The kicker stays: inside a block it is the "where you are" line.
    lines = ([slide_data.kicker] if slide_data.kicker else []) + intro + ([caption] if caption else [])
    if lines:
        height = line_height * sum(_pptx_lines(line) for line in lines)
        box = slide.shapes.add_textbox(Inches(0.6), Inches(top), Inches(12.1), Inches(height))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_top = frame.margin_bottom = 0
        frame.text = lines[0]
        for line in lines[1:]:
            frame.add_paragraph().text = line
        for paragraph in frame.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(PPTX_FLOOR_PT)
                run.font.name = "Arial"
        top += height + 0.1

    if table_block is None:  # pragma: no cover - only table slides come here
        return

    rows = len(table_block.rows) + 1
    cols = len(table_block.headers)
    # Long cells wrap; give each row the height its longest cell needs.
    per_col = 70 // cols - 2   # less the cell margins
    row_lines = [max(_pptx_lines(cell, per_col) for cell in table_block.headers)] + [
        max(_pptx_lines(cell, per_col) for cell in row) for row in table_block.rows
    ]
    row_heights = [Inches(0.1 + line_height * n) for n in row_lines]
    height = sum(row_heights)
    graphic_frame = slide.shapes.add_table(rows, cols, Inches(0.6), Inches(top), Inches(12.1), height)
    table = graphic_frame.table
    table.first_row = True  # header row, announced as one
    # Equal rows make PowerPoint expand wrapped cells on open, over the footer.
    for row, row_height in zip(table.rows, row_heights):
        row.height = row_height
        for cell in row.cells:
            cell.margin_top = cell.margin_bottom = Inches(0.05)
            cell.text_frame.word_wrap = True

    for position, heading in enumerate(table_block.headers):
        cell = table.cell(0, position)
        cell.text = heading
        for paragraph in cell.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(PPTX_FLOOR_PT)
                run.font.bold = True
                run.font.name = "Arial"

    for row_index, row in enumerate(table_block.rows, start=1):
        for position, value in enumerate(row):
            cell = table.cell(row_index, position)
            cell.text = value
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(PPTX_FLOOR_PT)
                    run.font.name = "Arial"

    _set_alt_text(graphic_frame, caption or f"Table: {slide_data.title}")
    top += graphic_frame.height / Inches(1) + 0.15

    # Anything after the table, and the links, go below it, in reading order.
    if after or slide_data.links:
        link_text = LINKS_LABEL + " " + ", ".join(label for label, _ in slide_data.links)
        tail_height = sum(0.56 * _pptx_lines(line, 45) for line in after)
        if slide_data.links:
            tail_height += line_height * _pptx_lines(link_text)
        box = slide.shapes.add_textbox(Inches(0.6), Inches(top), Inches(12.1), Inches(tail_height))
        frame = box.text_frame
        frame.word_wrap = True
        frame.margin_top = frame.margin_bottom = 0
        first = True
        for line in after:
            paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
            first = False
            paragraph.text = line
            for run in paragraph.runs:
                run.font.size = Pt(32)
                run.font.bold = True
                run.font.name = "Arial"
        if slide_data.links:
            _pptx_links(frame, slide_data.links, Pt, first=first)


def _set_alt_text(shape, text: str) -> None:
    """Alt text on a shape, which python-pptx does not expose directly.

    PowerPoint reads a shape's ``descr`` as its alternative text. Without it
    a table is announced as an unlabelled object, which is worse than no
    table at all: the reader knows something is there and cannot tell what.
    """
    element = getattr(shape, "_element", None)
    if element is None:  # pragma: no cover - defensive
        return

    c_nv_pr = None
    for holder_name in ("nvGraphicFramePr", "nvSpPr", "nvPicPr", "nvCxnSpPr"):
        holder = getattr(element, holder_name, None)
        if holder is not None:
            c_nv_pr = getattr(holder, "cNvPr", None)
            if c_nv_pr is not None:
                break

    if c_nv_pr is None:  # pragma: no cover - unusual shape types
        return

    c_nv_pr.set("descr", text)
