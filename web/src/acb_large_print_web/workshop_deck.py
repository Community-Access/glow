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
from dataclasses import dataclass, field
from io import BytesIO
from typing import ClassVar

from . import workshop_agenda as agenda

DECK_TITLE = "Accessibility Agents"
DECK_SUBTITLE = "Building Human-Centered AI Workflows for Trusted Accessibility Automation at Scale"
DECK_EVENT = "Accessing Higher Ground 2026"
DECK_BYLINE = "Jeff Bishop - BITS, an affiliate of the American Council of the Blind"


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
    "Your agent: five plain-English answers.",
    "Your agent at work: Copilot uses it on one course document.",
    "Your agent, grounded: real evidence in, cited answers out.",
    "Your agent, shared: a pull request to an open-source project, with your name on it.",
    "Your agent in the team: the whole course, at once.",
    "Your campus: a 30-day plan.",
)


def _journey_note(number: int) -> str:
    return f"Say where we are on the journey: step {number} of 7, \"{JOURNEY[number - 1]}\" Then show what they will have at the end of this block before anyone starts."


# ---------------------------------------------------------------------------
# The deck
# ---------------------------------------------------------------------------


def build_slides(ctx: DeckContext) -> list[Slide]:
    """Every slide of the AHG 2026 day, in order, with this room's addresses."""
    day = agenda.AHG_DAY
    lunch = next(b for b in day if b.kind == agenda.LUNCH)
    rest = next(b for b in day if b.kind == agenda.BREAK)
    commitments = next(b for b in day if b.title == "Commitments")
    evaluation = day[-1]

    return [
        # -- Block 1: why we are here ---------------------------------------
        Slide(
            id="s1", section="Opening", kicker=DECK_EVENT, title=DECK_TITLE,
            blocks=(
                Para(DECK_SUBTITLE, lead=True),
                Para("Today you build an accessibility agent. By four o'clock it is part of a team, and part of an open-source project, with your name on it."),
                Para(f"{DECK_BYLINE}", small=True),
            ),
            notes=(
                "The proctor introduces the session. Put the microphone on before you say a word, and keep it on all day: when someone speaks from the floor, pass them a mic or repeat what they said into yours before you answer.",
                "Say the key point before any logistics, in one sentence: accessibility in higher education does not scale by fixing, it scales by making more people who can, and agents are how one person's know-how reaches a whole course.",
                "Describe the slide: the title, the subtitle from the program, and one sentence promising what they leave with.",
            ),
        ),
        Slide(
            id="s2", section="Opening", kicker="The problem", title="Forty thousand files and three people",
            blocks=(
                Para("WCAG 2.2 is the standard. Title II made it a deadline for public colleges and universities."),
                Para("Every syllabus, slide deck, scanned reading and course page is in scope, and most of them are documents, not web pages."),
                Para("Nobody fixes that by working harder. The question is how to scale without losing quality, accountability or trust.", big=True),
            ),
            notes=(
                "Ask, warmly: who here has a backlog? Who has a spreadsheet with the word final in its name more than once? Let the laugh happen; it is recognition, not mockery.",
                "Title II's rule points to WCAG 2.1 AA; 2.2 is the current standard and includes everything 2.1 does. Say it once and move on.",
            ),
        ),
        Slide(
            id="s3", section="Opening", kicker="Where we will be at 4:00", title="The finished result, first",
            blocks=(
                Para("This afternoon a team of agents works through a whole course and writes one report. Every finding has its evidence, its WCAG criterion, and a named person who checks it."),
                Table(
                    caption="One section of that report, from Maria's agent:",
                    headers=("Part", "What it says"),
                    rows=(
                        ("File", "The scanned required reading"),
                        ("Routed to", "Alternate format planner, by Maria Alvarez"),
                        ("Evidence", "GLOW audit: pictures of text, no text layer, untagged"),
                        ("Plan", "Get a clean source, then large print and audio, and post it for every student"),
                        ("Reviewer", "Alternate format specialist. Status: proposed"),
                    ),
                ),
                Para("You will build one of the agents that writes a section like this."),
            ),
            notes=(
                "Read the table out loud, row by row. It is the destination; people relax when they can see it.",
                "Maria is a colleague in a disability resource center. She is fictional, and she is one step ahead of the room all day.",
            ),
        ),
        Slide(
            id="s4", section="Opening", kicker="The map for today", title="The journey",
            blocks=(Bullets(ordered=True, items=JOURNEY),),
            notes=(
                "Read all seven, slowly. This list comes back at the start of every block with one step marked, so nobody ever wonders where we are.",
                "Promise them out loud: every step has a finished example to fall back on. Nobody gets stuck and stays stuck.",
            ),
        ),
        Slide(
            id="s5", section="Opening", kicker="Housekeeping", title="How today runs",
            blocks=(
                Bullets(items=(
                    f"10:30 to 4:30 Mountain Time. Lunch at {lunch.starts_at}. A break at {rest.starts_at}.",
                    "Your laptop, with VS Code, the AHG 2026 profile and your GitHub account. Not set up yet? A helper is coming to you.",
                    "Seven blocks. Every one starts by showing you the finished result.",
                    f"The last five minutes, at {evaluation.starts_at}, are the session evaluation.",
                    "Ask for anything, any time: large print, a seat, a pause, a repeat.",
                )),
            ),
            notes=(
                "Name the exits and the restrooms, physically pointing.",
                "Say the last bullet slowly, then add: that is not an interruption of this workshop - it is this workshop.",
                "If anyone is not set up, do not wait for them. Helpers sit with them while the room carries on; the morning is designed so they catch up by lunch.",
            ),
        ),
        Slide(
            id="s6", section="Opening", kicker="Two rules, all day", title="Private stays private, and people decide",
            blocks=(
                Bullets(ordered=True, items=(
                    "Never paste anything private into any AI: student records, health or disability information, anyone's name. We use a sample course all day.",
                    "Every agent ends with a person checking its work. Agents draft. People decide.",
                )),
                Para("If nobody is named, nobody reviewed it.", big=True),
            ),
            notes=(
                "Set the AI context here, in under a minute. What today covers: agents that analyze course content, find barriers and draft fixes, grounded in checkers and cited standards. What it does not: replacing anyone, or trusting any answer without evidence.",
                "Say what makes it different from the other AI sessions this week: it is about higher education accessibility work at scale, built by the people who do that work, and every agent is open source.",
                "Name the reasons people hesitate - privacy, accuracy, other people's jobs - once, without dwelling. Rule one answers the first. Grounding answers the second. Rule two answers the third.",
            ),
        ),
        Slide(
            id="s7", section="Opening", kicker="No code, really", title="What an agent is",
            blocks=(
                Definitions(items=(
                    ("Role", "Who it is, and who it works for."),
                    ("Task", "The one job it does."),
                    ("Trusted guidance", "The standards and policies it must cite: WCAG 2.2, your own procedures."),
                    ("Output format", "What comes back, in a shape a busy person can use."),
                    ("Human review", "Who checks it before anything goes out."),
                )),
                Para("An agent is those five answers, written in plain English. Writing one is writing, not coding.", big=True),
            ),
            notes=(
                "This is the slide that lowers the shoulders. Say it twice: if you can write instructions for a new colleague, you can write an agent.",
                "The file format is the same one the open-source Accessibility Agents project uses, which is why their agents and yours can work in the same team this afternoon.",
            ),
        ),
        Slide(
            id="s8", section="Opening", kicker="Agents in action", title="Your accessibility office",
            blocks=(
                Table(
                    caption="The agent team you will join this afternoon. A coordinator routes each file to these specialists.",
                    headers=("Specialist", "Takes"),
                    rows=(
                        ("Word documents", "Syllabi, handouts"),
                        ("PowerPoint slides", "Lecture decks"),
                        ("Excel workbooks", "Gradebooks, templates"),
                        ("PDF documents", "Readings, forms, scans"),
                        ("Web pages", "Course pages, with axe and Accessibility Insights"),
                        ("Captions and media", "Lecture captions"),
                        ("Plain language", "Anything a student must read and act on"),
                        ("Standards reviewer", "Everyone's findings, last"),
                        ("Your agent", "Whatever you build it to do"),
                    ),
                ),
            ),
            notes=(
                "Read the specialists down the list. Pause on the last row: the team has an empty chair, and it is theirs.",
                "These specialists are adapted from the open-source Accessibility Agents project. That is where their agents go this afternoon too.",
            ),
        ),
        # -- Block 2: design your agent -------------------------------------
        Slide(
            id="s9", section="Design", kicker=_you_are_here(2), title="Design your agent",
            blocks=(
                Para("By the end of this block: your own agent, in a file, with your name on it."),
                Definitions(items=(
                    ("Documents and alternate formats", "An alternate format planner, or a document triage agent."),
                    ("Course content and faculty coaching", "A faculty coach, or a course page coach."),
                    ("Compliance and procurement", "A remediation log keeper, or a vendor report reader."),
                )),
                Para("Pick one card. Bring one real problem from your job, with nothing private in it."),
            ),
            notes=(
                _journey_note(2),
                "Every card has two ready-made agents in examples/agents. Nobody starts from a blank page; everybody starts from something that already works and makes it theirs.",
            ),
        ),
        Slide(
            id="s10", section="Design", kicker="Watch me first", title="Maria's five answers",
            blocks=(
                Table(
                    caption="Maria, from the Disability Resource Center, designing her alternate format planner:",
                    headers=("Question", "Maria's answer"),
                    rows=(
                        ("Role", "An alternate format planner in a disability resource center"),
                        ("Task", "Plan the formats a student needs from a checker's report"),
                        ("Trusted guidance", "WCAG 2.2 1.4.5 and 1.1.1, ACB large print, our procedure"),
                        ("Output format", "Numbered steps with who does each, then a checklist"),
                        ("Human review", "The specialist checks page by page; the student confirms"),
                    ),
                ),
            ),
            notes=(
                "Read Maria's answers aloud. Then type /design-my-agent in Copilot Chat on the projector and answer as Maria, so they hear the whole conversation once before they have theirs.",
                "Joke if the room is warm: Maria's coffee machine has been out of order since August. Her agent does not drink coffee, which is its main advantage.",
            ),
        ),
        Slide(
            id="s11", section="Design", kicker="Your turn", title="Copilot asks, you answer",
            blocks=(
                Bullets(ordered=True, items=(
                    "Open Copilot Chat: Control+Alt+I on Windows, Command+Control+I on a Mac.",
                    "Type /design-my-agent and press Enter.",
                    "Answer the questions, one at a time. Borrow from the example whenever you like.",
                    "Copilot writes your answers into my-agent/SKILL.md and reads it back.",
                )),
                Para("You are on track if Copilot tells you one thing your agent does well."),
                Para("Stuck? Copy a ready-made agent from examples/agents into my-agent. That counts. You are still in."),
            ),
            notes=(
                "Helpers move now. Look for the person who has not typed anything yet, and sit with them quietly.",
                "Step card 2 has every key and every expected screen in words, for screen reader users and anyone who prefers paper.",
            ),
        ),
        # -- Block 3: your agent at work ------------------------------------
        Slide(
            id="s12", section="Design", kicker=_you_are_here(3), title="Your agent at work",
            blocks=(
                Para("By the end of this block: your agent's first answer on a real course document."),
                Bullets(ordered=True, items=(
                    "In Copilot Chat, type /try-my-agent.",
                    "Pick a file from the PSY 101 sample course.",
                    "Read what your agent says.",
                )),
                Para("It will guess a little. That is not a mistake. It is the setup for this afternoon.", big=True),
            ),
            notes=(
                _journey_note(3),
                "PSY 101 is fictional: a course about memory and procrastination that keeps forgetting things and running late. The barriers in it are planted on purpose; the answer key is in the facilitator folder.",
            ),
        ),
        Slide(
            id="s13", section="Design", kicker="Watch me", title="Maria's first answer",
            blocks=(
                Panel(lines=(
                    "\"Run Acrobat's Make Accessible action, add alternative text to all images, and increase the font size. This will make the document compliant with WCAG 2.1.\"",
                )),
                Bullets(items=(
                    "It never saw the file, so it did not know the reading is a scan.",
                    "Alt text on pictures of text would describe the pictures, not turn them into text.",
                    "It said \"compliant\", which her agent is told never to say.",
                )),
            ),
            notes=(
                "Read the quote in a confident voice, then the three problems in a normal one. The contrast is the joke, and the lesson.",
                "This is a written example, labelled as one in the kit. On the day, show a real first answer from the room if someone offers one.",
            ),
        ),
        Slide(
            id="s14", section="Lunch", kicker=f"Lunch - {lunch.clock}", title=f"Back at {lunch.resume}",
            blocks=(
                Para("You have an agent. That was the hard part."),
                Para("After lunch it stops guessing."),
            ),
            notes=(
                "Say well done, and mean it. Most people in this room had never written an agent at 10:30.",
                "Anyone still setting up: lunch is when a helper finishes it with them.",
            ),
        ),
        # -- Block 4: ground it ---------------------------------------------
        Slide(
            id="s15", section="Afternoon", kicker=_you_are_here(4), title="Ground it",
            blocks=(
                Para("By the end of this block: the same agent, giving cited answers from real evidence. A before and an after."),
                Bullets(ordered=True, items=(
                    "In Copilot Chat, type /ground-my-agent.",
                    "Use the same file as this morning.",
                    "Your agent reads that file's checker report from sample-course/evidence: GLOW for documents, axe for the web page.",
                    "Compare the two answers.",
                )),
            ),
            notes=(
                _journey_note(4),
                "Grounding is the trusted in the session title. The checkers find; the agent explains and plans; a person decides.",
            ),
        ),
        Slide(
            id="s16", section="Afternoon", kicker="Watch me", title="Before and after",
            blocks=(
                Table(
                    caption="Maria's agent, on the scanned reading:",
                    headers=("Before evidence", "After evidence"),
                    rows=(
                        ("Guessed the file was an ordinary PDF", "Knew it was two pages of pictures of text"),
                        ("WCAG 2.1, no links", "WCAG 2.2, 1.4.5 Images of Text, linked"),
                        ("\"Compliant\"", "What was checked, and what a person must check"),
                        ("Fix the PDF", "Get a clean source, then large print and audio for everyone"),
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
                Para("The same works with Word's and PowerPoint's own Accessibility Checker, Acrobat's checker, or Accessibility Insights. The skill is giving your agent evidence."),
                Para("And some barriers no checker sees:"),
                Bullets(items=(
                    "The accommodations statement, last, in 8-point gray, contradicted two sections earlier by a no-makeup-exams rule in capitals.",
                    "Alt text that says \"image.png\".",
                    "A lab that only works if you can see color.",
                    "Captions that turn Ebbinghaus into \"ebb in house\".",
                )),
            ),
            notes=(
                "If Word is handy, show Review, then Check Accessibility on the syllabus, and paste its results into Copilot with the agent. Same skill, different tool.",
                "Those four barriers are why every agent has a human review step. Read each one; the room will recognise every one of them from their own campus.",
            ),
        ),
        Slide(
            id="s18", section="Afternoon", kicker=f"Break - {rest.minutes} minutes", title=f"Back at {rest.resume}",
            blocks=(Para("Next, your agent goes public. Nicely."),),
            notes=("Short break on purpose. The next two blocks are where the day comes together.",),
        ),
        # -- Block 5: share it ----------------------------------------------
        Slide(
            id="s19", section="Afternoon", kicker=_you_are_here(5), title="Share it",
            blocks=(
                Para("By the end of this block: your own pull request in the open-source Accessibility Agents project."),
                Bullets(ordered=True, items=(
                    "Open letitglow.app/workshop/ahg-2026/share in your browser, and choose your my-agent/SKILL.md.",
                    "Press Open GitHub with my agent. GitHub opens with your agent filled in.",
                    "Press Propose changes. GitHub makes your own copy, called a fork.",
                    "Press Create pull request, then Create pull request again.",
                )),
                Para("That is your contribution. Buttons only. No code."),
            ),
            notes=(
                _journey_note(5),
                "Step card 5 walks the GitHub pages one control at a time, with what a screen reader announces at each step.",
            ),
        ),
        Slide(
            id="s20", section="Afternoon", kicker="Open source, live", title="Merged, with your name on it",
            blocks=(
                Para("As your pull requests arrive, I review and merge them, here, on the screen."),
                Para("Every agent merged today lives in community/ahg-2026 in the Accessibility Agents project, for anyone in higher education to use and improve.", big=True),
            ),
            notes=(
                "Merge on the projector as they arrive, and read each name and agent title out loud. Applause is allowed and encouraged.",
                "Started from a ready-made agent? It still counts. Say so: what matters is that it is yours now.",
            ),
        ),
        # -- Block 6: build the office --------------------------------------
        Slide(
            id="s21", section="Afternoon", kicker=_you_are_here(6), title="Build the office",
            blocks=(
                Para("By the end of this block: your agent working inside a team, across the whole course, and one team report."),
                Bullets(ordered=True, items=(
                    "In Copilot Chat, type /run-the-office.",
                    "The coordinator sends each course file to its specialists, and yours where it fits.",
                    "The standards reviewer checks everyone's work.",
                    "You get the team report, with your agent's section in it.",
                )),
            ),
            notes=(
                _journey_note(6),
                "This is building an agent team: they added a specialist, and their coordinator is running it. Copilot announces each file as it finishes, so screen reader users hear progress, not silence.",
            ),
        ),
        Slide(
            id="s22", section="Afternoon", kicker="What scale looks like", title="One course, one report",
            blocks=(
                Bullets(items=(
                    "Seven files, eight specialists, plus yours.",
                    "Every finding: evidence, a WCAG 2.2 criterion with its link, and a named reviewer.",
                    "A list of what no checker could see, for a person.",
                    "Three lines at the top that a director will actually read.",
                )),
                Para("That is quality, accountability and transparency, at scale. It is also a Tuesday.", big=True),
            ),
            notes=(
                "Ask: what would it take to run this across ten courses? Let them answer. The honest answer is a person's review time, which is exactly where it should go.",
            ),
        ),
        Slide(
            id="s23", section="Afternoon", kicker="Agents in action", title="Everyone's agents, together",
            blocks=(
                Para("One more run, on the screen: the office team with every agent this room merged."),
                Para("Listen for yours."),
            ),
            notes=(
                "Run the merged team on the projector against the sample course. Read out each agent's name as the coordinator calls it.",
                "If the run is slow, narrate it. If it stumbles, say what happened and why; a real failure explained well teaches more than a perfect demo.",
            ),
        ),
        # -- Block 7: take it home ------------------------------------------
        Slide(
            id="s24", section="Close", kicker=_you_are_here(7), title="Take it home",
            blocks=(
                Para("By the end of this block: a 30-day plan for your own campus."),
                Bullets(ordered=True, items=(
                    "In Copilot Chat, type /my-30-day-plan.",
                    f"Then add your one-sentence commitment at {ctx.join_display}/11 for the wall.",
                )),
                Table(
                    caption="What you can do on Monday, with tools you already have:",
                    headers=("You learned", "Monday, with"),
                    rows=(
                        ("Writing an agent", "Any AI assistant, including your campus Copilot"),
                        ("Grounding it", "Word's, PowerPoint's and Acrobat's checkers, Accessibility Insights, axe"),
                        ("Human review, in writing", "Your own office's process"),
                        ("Agent teams", "One specialist at a time, or the Accessibility Agents project"),
                    ),
                ),
            ),
            notes=(
                _journey_note(7),
                "Small is the point. \"Run the planner on the next five requests\" beats \"transform our office\".",
            ),
        ),
        Slide(
            id="s25", section="Close", kicker=commitments.starts_at, title="The commitment wall",
            blocks=(
                Para("Every commitment in this room, on one screen, with no names on it."),
            ),
            notes=(
                "Project the wall from GLOW. Read three aloud. Do not comment on them, do not rank them.",
                "Then go straight to the evaluation. The last five minutes belong to it.",
            ),
        ),
        Slide(
            id="s26", section="Close", kicker=f"{evaluation.starts_at} - Thank you", title="Go make one more champion",
            blocks=(
                Para("You came in with a problem. You are leaving with an agent, a team and a plan.", lead=True),
                Para("Before you go: the session evaluation. It shapes next year's conference."),
                Para("Help any time, before or after today: support@community-access.org."),
                Para("GLOW is a community project of BITS, an affiliate of the American Council of the Blind.", small=True),
            ),
            notes=(
                "Say it, thank them, and hand over to the proctor for the evaluation. Then stop talking while people fill it in.",
                "No question block here. Answer at the tables while people pack up.",
            ),
        ),
    ]


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
        if slide.notes:
            # Numbered, so a heading list reads "Speaker notes, slide 4"
            # rather than thirty identical entries.
            doc.add_heading(f"Speaker notes, slide {index}", level=3)
            for note in slide.notes:
                doc.add_paragraph(note)

    out = BytesIO()
    doc.save(out)
    return out.getvalue()


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
            placeholder.height = Inches(1.2) if is_title else Inches(5.4)
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

    def _para(text: str, *, level: int = 0, size: int = 20, bold: bool = False, marker: bool | None = None):
        nonlocal first
        paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
        first = False
        paragraph.text = text
        paragraph.level = level
        if marker is None:
            marker = level > 0
        if not marker:
            # Without this the body layout puts a bullet on every line: a
            # dash before "1." on a numbered item, and on a plain paragraph a
            # list that a screen reader announces as one.
            p_pr = paragraph._p.get_or_add_pPr()
            if level == 0:
                p_pr.set("marL", "0")
                p_pr.set("indent", "0")
            p_pr.insert(0, p_pr.makeelement(qn("a:buNone"), {}))
        for run in paragraph.runs:
            run.font.size = Pt(size)
            run.font.name = "Arial"
            run.font.bold = bold
        return paragraph

    # 18pt is the floor for anything on a slide, kicker included.
    if slide_data.kicker:
        _para(slide_data.kicker, size=18)

    for block in slide_data.blocks:
        if isinstance(block, Para):
            size = 28 if block.big else (24 if block.lead else 20)
            _para(block.text, size=size, bold=block.big)
        elif isinstance(block, Url):
            _para(block.text, size=32, bold=True)
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


def _pptx_table_slide(slide, slide_data: Slide, Inches, Pt) -> None:
    """A title-only slide carrying one table, captioned and alt-texted."""
    caption = ""
    table_block = None
    intro: list[str] = []
    for block in slide_data.blocks:
        if isinstance(block, Table):
            table_block = block
            caption = block.caption
        elif isinstance(block, Para):
            intro.append(block.text)
        elif isinstance(block, Bullets):
            # Steps on a table slide must not be dropped: on the take-home
            # slide they are the instructions.
            intro.extend(
                f"{n}. {item}" if block.ordered else item
                for n, item in enumerate(block.items, start=1)
            )
        elif isinstance(block, Definitions):
            intro.extend(f"{term}: {meaning}" for term, meaning in block.items)

    top = Inches(1.6)
    if slide_data.kicker or intro or caption:
        box = slide.shapes.add_textbox(Inches(0.6), top, Inches(12.1), Inches(0.45 * max(1, len(intro) + 2)))
        frame = box.text_frame
        frame.word_wrap = True
        lines = ([slide_data.kicker] if slide_data.kicker else []) + intro + ([caption] if caption else [])
        frame.text = lines[0]
        for line in lines[1:]:
            frame.add_paragraph().text = line
        for paragraph in frame.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(18)
                run.font.name = "Arial"
        top = Inches(1.6 + 0.45 * len(lines) + 0.3)

    if table_block is None:  # pragma: no cover - only table slides come here
        return

    rows = len(table_block.rows) + 1
    cols = len(table_block.headers)
    height = Inches(min(4.6, 0.45 * rows + 0.3))
    graphic_frame = slide.shapes.add_table(rows, cols, Inches(0.6), top, Inches(12.1), height)
    table = graphic_frame.table
    table.first_row = True  # header row, announced as one

    for position, heading in enumerate(table_block.headers):
        cell = table.cell(0, position)
        cell.text = heading
        for paragraph in cell.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(18)
                run.font.bold = True
                run.font.name = "Arial"

    for row_index, row in enumerate(table_block.rows, start=1):
        for position, value in enumerate(row):
            cell = table.cell(row_index, position)
            cell.text = value
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(18)
                    run.font.name = "Arial"

    _set_alt_text(graphic_frame, caption or f"Table: {slide_data.title}")


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
