"""The workshop deck, as content rather than as a file.

A deck that exists as one HTML file cannot also be a Word document, a
PowerPoint, or Markdown without somebody maintaining four copies of the same
sentences -- and four copies is how the day's timings ended up disagreeing in
four places before ``workshop_agenda`` existed.

So the slides live here as data. Every format is a renderer over the same
list, and the agenda slide is built from ``workshop_agenda`` at render time,
so a change to the day reaches all four formats at once.

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

from dataclasses import dataclass, field
from io import BytesIO
from typing import ClassVar

from . import workshop_agenda as agenda

DECK_TITLE = "Accessibility Agents in Action"
DECK_SUBTITLE = "A hands-on GLOW workshop for human-centered accessibility workflows"
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


def _day_in_three_parts() -> Definitions:
    """The day as three chunks, with every break and lunch named.

    Not the full timetable. Eighteen rows projected is a wall of text, and
    a wall of text is exactly what the AHG speaker guidance asks presenters
    not to put on a screen; three chunks is what a listener can hold. The
    full table is on the workshop home page, on every participant's device.
    The times are still read from the agenda, so the slide cannot drift.
    """
    blocks = agenda.deck_blocks()
    break_1, break_2, lunch = blocks["break_1"], blocks["break_2"], blocks["lunch"]
    first, last = agenda.AGENDA[0], agenda.AGENDA[-1]
    return Definitions(items=(
        (
            f"Morning, {first.starts_at}-{lunch.starts_at}",
            f"Why this work matters, five short activities, and Lab 1. Break at {break_1.starts_at}.",
        ),
        (
            f"Afternoon, {lunch.resume}-{break_2.resume}",
            f"Two labs: alt text, then remediation planning. Break at {break_2.starts_at}.",
        ),
        (
            f"Close, {break_2.resume}-{last.resume}",
            "Your workflow, your take-home artifact, your 30-day plan, and the session evaluation.",
        ),
    ))


# ---------------------------------------------------------------------------
# The deck
# ---------------------------------------------------------------------------


def build_slides(ctx: DeckContext) -> list[Slide]:
    """Every slide, in order, with this room's own addresses in them."""
    blocks = agenda.deck_blocks()
    break_1 = blocks["break_1"]
    break_2 = blocks["break_2"]
    lunch = blocks["lunch"]
    peer_review = blocks["peer_review"]
    close_at = blocks["close_at"]

    return [
        Slide(
            id="s1", section="Opening", kicker=DECK_EVENT, title=DECK_TITLE,
            blocks=(
                Para(DECK_SUBTITLE, lead=True),
                Para("Helping everyone become an accessibility champion.", lead=True),
                Para(f"{DECK_BYLINE} - letitglow.app", small=True),
            ),
            notes=(
                "Do not start with the tool. Start with the room. Ask nothing yet - let people sit down, find power, and settle.",
                "The proctor introduces the session. Put the microphone on before you say a word, and keep it on all day: when a volunteer speaks, pass them a mic or say what they said back into yours before you answer. Some people in this room hear you only through it.",
                "Say the key point once, before any logistics, in one sentence: the work is not fixing documents, it is making more people who can. Then the promise on the next slide.",
            ),
        ),
        Slide(
            id="s2", section="Opening", kicker="The promise",
            title="Two ways, and the first one is enough",
            blocks=(
                Bullets(ordered=True, items=(
                    "GLOW, in a browser. The whole day. No account, no sign-in, no AI.",
                    "Plus your own assistant, if you already have one. An upgrade on the same exercise, never a different one.",
                )),
                Para("Nothing today needs an account with anyone.", big=True),
                Para(
                    "One rule if you use an assistant: paste text, never upload files - "
                    "and never paste anything private.",
                ),
            ),
            notes=(
                "Say this in the first ten minutes, exactly once, and mean it. Everything later in the day depends on the room believing it.",
                "The upload rule matters: free accounts allow roughly two image uploads a day and do not publish the number. An instruction that fails at 1:40 is worse than one nobody followed.",
                "The privacy half matters more. Say what private means here: student records, health or disability information, anyone's name. A free assistant may keep what is pasted into it. Use the scenarios, or strip the details out first.",
            ),
        ),
        Slide(
            id="s3", section="Opening", kicker="Housekeeping", title="How today runs",
            blocks=(
                Bullets(items=(
                    f"8:30 to 4:30. Lunch at {lunch.starts_at}. Breaks at {break_1.starts_at} and {break_2.starts_at}.",
                    "Eleven activities. Nothing is graded, and nothing is collected without you choosing to share it.",
                    "Any device, a phone included. Nothing to install, so a locked-down work laptop is fine.",
                    "Everything you write is yours, and you leave with all of it.",
                    "Ask for anything, any time - large print, a seat, a pause, a repeat.",
                )),
            ),
            notes=(
                "Name the exits and the bathrooms, physically pointing. Some people will not ask.",
                "If anyone arrived without the worksheet pack, the links are on the workshop home page and work on a phone. We do not hand out paper.",
                "Say the last bullet slowly, then add: that is not an interruption of this workshop - it is this workshop. It sets the tone for whether anyone asks for anything all day.",
                "The worksheet pack was published before today for anyone who wanted to print their own. Say so for the person who did.",
            ),
        ),
        Slide(
            id="s4", section="Opening", kicker="Join the room", title="One address, all day",
            blocks=(
                Url(ctx.join_display),
                Para("The same address is on the card at every table, in large type, with a QR code beside it."),
                Para(
                    "Each activity has its own short address: slash 1, slash 2, and so on, "
                    "numbered the way I will say them out loud."
                ),
            ),
            notes=(
                "Read the address out twice, letter by letter, then wait. Do not move on until people are in. The code on this slide is the live one for this session - there is nothing to replace.",
                "Say what is on the screen: the address and nothing else. The QR code is on the table cards, not here, so nobody hunts the slide for it.",
                "Signage is printed from the facilitator dashboard: session, then signage.",
            ),
        ),
        Slide(
            id="s5", section="Opening", kicker="Do this early",
            title="So you never lose your work",
            blocks=(
                Para("Your work is held against this browser on this device. Switch to a phone, or clear your cookies, and it is gone."),
                Para("On My workshop content, under Work on another device, give an email address and you will be sent a link that restores everything, anywhere."),
                Bullets(items=(
                    "Entirely optional. The day works without it.",
                    "The address is used for that one message and never appears anywhere else.",
                    "The link lasts 45 days, which outlives your 30-day plan.",
                )),
            ),
            notes=(
                f"Give this twice: once now, once at the {break_1.starts_at} break, when there is something worth keeping.",
                "If Postmark is not configured, the form is replaced by a download prompt. Check before the room fills - it is invisible until you look for it.",
            ),
        ),
        Slide(
            id="s6", section="Opening", kicker="Why we are here",
            title="Accessibility does not scale by fixing",
            blocks=(
                Para("If you are the person who fixes everything, then accessibility in your institution is exactly as large as your calendar."),
                Para("The work is not fixing documents. The work is making more people who can.", big=True),
            ),
            notes=(
                "This is the pivot of the whole day. Let it sit. Some people in this room are exhausted by being the only one.",
                "Optional: ask for a show of hands on \"who is the only accessibility person in your unit\" - but only if the room is warm enough. It can land as exposure rather than solidarity.",
            ),
        ),
        Slide(
            id="s7", section="Opening", kicker="Four words for the day", title="The GLOW framework",
            blocks=(
                Definitions(items=(
                    ("G - Ground", "Ground the work in a real accessibility problem, not a tool."),
                    ("L - Learn", "Learn what the people around you actually need to understand."),
                    ("O - Organize", "Organize it into a workflow that repeats without you."),
                    ("W - Walk", "Walk forward as champions, plural."),
                )),
            ),
            notes=(
                "Map the day onto this once, here, and then stop talking about the acronym. It is scaffolding, not content.",
            ),
        ),
        Slide(
            id="s8", section="Opening", kicker="The boundary", title="AI drafts. People decide.",
            blocks=(
                Para("Every activity today has a human-review step that you write yourself, in your own words, for your own context."),
                Para("Not because AI is dangerous in the abstract - because purpose, meaning, context and harm are judgments, and judgments have owners."),
                Para("If nobody is named, nobody reviewed it.", big=True),
            ),
            notes=(
                "This is the slide institutional leadership cares about. It is also the honest one.",
                "Set the AI context here, in under a minute. What this session covers: where AI can help in accessibility work, and the human review that has to follow it. What it does not: comparing vendors, building software, or requiring anyone to use AI at all.",
                "Say what makes it different from the other AI sessions this week: it is about people making more people who can, and AI stays optional throughout. Name the reasons people hesitate - privacy, accuracy, other people's jobs - without dwelling on them. The boundary on this slide is the answer to each.",
                "The generated prompts put the participant's own review step inside the prompt as an instruction, not as a closing remark. Mention that at activity 5, not here.",
            ),
        ),
        Slide(
            id="s9", section="Opening", kicker="The shape of the day", title="Where we are going",
            blocks=(_day_in_three_parts(),),
            notes=(
                "Thirty seconds. Read the three parts out loud - not everyone can read the screen. Then say \"the last part is what you take home\".",
                "The full timetable, every break included, is on the workshop home page on every device. These times come from the workshop agenda, so they cannot drift from what each activity page shows.",
            ),
        ),
        Slide(
            id="s10", section="Morning", kicker=f"Activity 1 - {ctx.activity(1)}",
            title="Accessibility Journey Check-In",
            blocks=(
                Para("What accessibility work do you actually do? Where do your partners get stuck - the same place, over and over?"),
                Para("What would change if more of them became champions?"),
            ),
            notes=(
                "No sharing pressure. Writing, then a table conversation if the table wants one.",
                "When the first submissions land, point people at the return link. This is the moment they have something to lose.",
            ),
        ),
        Slide(
            id="s11", section="Morning", kicker=f"Activity 2 - {ctx.activity(2)}",
            title="What problem are we solving?",
            blocks=(
                Para("Start with the problem you can see today."),
                Para("Then name the deeper one behind it. Who needs to learn this work, or own part of it?"),
                Para("What does success look like if it happens again and again, without you?", big=True),
            ),
            notes=(
                "Watch for tool-first answers - \"we need a checker\". Push back gently: a checker is an answer, not a problem.",
            ),
        ),
        Slide(
            id="s12", section="Morning", kicker=f"Activity 3 - {ctx.activity(3)}",
            title="Fix it for me, or teach me?",
            blocks=(
                Para("Take a real request that said \"just fix it for me.\""),
                Para("Write the reply that does both: solves it today, and teaches it for next time."),
                Panel(lines=(
                    "The pattern: I have done X for you. Here is the one thing that caused it. "
                    "Next time, do Y - it takes about a minute, and here is where it lives.",
                )),
            ),
            notes=(
                "The hard part is tone, not content. Nobody learns from a reply that makes them feel caught.",
                "Ask for one volunteer to read theirs aloud. One is enough.",
            ),
        ),
        Slide(
            id="s13", section="Morning", kicker=f"Break - {break_1.minutes} minutes",
            title=f"Back at {break_1.resume}",
            blocks=(
                Para("If you have not sent yourself a return link yet, now is the moment. My workshop content, then Work on another device."),
            ),
            notes=(
                "Project the room pulse during the break. Counts only - it is safe on a screen.",
                "Walk the room. The person who has not typed anything is the one to sit with, quietly.",
            ),
        ),
        Slide(
            id="s14", section="Morning", kicker=f"Activity 4 - {ctx.activity(4)}",
            title="Helpful, risky, or human required?",
            blocks=(
                Para("Sort your own tasks into three piles. Then write the safeguard that makes the middle pile safe."),
                Table(
                    caption="The three piles",
                    headers=("Pile", "Example"),
                    rows=(
                        ("Helpful for AI", "Drafting alt text for a chart you wrote"),
                        ("Risky without review", "Summarising a policy document"),
                        ("Human required", "Deciding what an image is for"),
                    ),
                ),
            ),
            notes=(
                "The examples are deliberately arguable. If a table disagrees about which pile something is in, that argument is the exercise.",
            ),
        ),
        Slide(
            id="s15", section="Morning", kicker=f"Activity 5 - {ctx.activity(5)}",
            title="The Accessibility Agent Formula",
            blocks=(
                Definitions(items=(
                    ("Role", "Who is it being, and for whom?"),
                    ("Task", "One job, said plainly."),
                    ("Trusted guidance", "Whose rules - WCAG, ACB large print, your own style guide?"),
                    ("Output format", "What comes back, in what shape, so a person can use it?"),
                    ("Human review", "Who checks what, before it goes out?"),
                )),
                Para("You are not writing code. You are writing instructions for a colleague who is fast, literal, and has never met your institution."),
            ),
            notes=(
                "This is the technical peak of the day and it is still five sentences on a page. Say so.",
                "Mention the optional \"Run your agent\" lab here, once. Lunch or after 4:30. A door, not a corridor.",
            ),
        ),
        Slide(
            id="s16", section="Morning", kicker=f"Lab 1 - {ctx.activity(6)}",
            title="GLOW Lab 1: Accessible Communications",
            blocks=(
                Para("Rewrite a real message so more people can read it."),
                Bullets(items=(
                    "Plain words, short sentences.",
                    "Real headings, not bold text pretending to be headings.",
                    "Links that say where they go.",
                    "Words that welcome an access request instead of burying it.",
                )),
                Para("Bring your own message if you have one. The scenarios are a net, not a rail."),
            ),
            notes=(
                "Four scenarios from four sectors, plus \"Surprise me\", which is deterministic per person - two people at a table will rarely get the same brief, and you can walk anyone back through what they were given.",
                "A real document of their own always beats a scenario. Say it out loud.",
            ),
        ),
        Slide(
            id="s17", section="Morning", kicker=f"Lunch - {lunch.clock}",
            title=f"Back at {lunch.resume}",
            blocks=(
                Para("Nothing is due. Nothing is graded."),
                Para("If you want more: the optional Run Your Agent lab is open, and it is genuinely optional."),
            ),
            notes=(
                "Eat. Nothing in the afternoon depends on a model answering, so there is nothing to watch over lunch.",
            ),
        ),
        Slide(
            id="s18", section="Afternoon", kicker=f"{lunch.resume} - Re-entry",
            title="Where the room is",
            blocks=(
                Para("Here is what the room has finished so far. No names, just counts."),
                Para("Nobody is behind. There is no behind.", big=True),
            ),
            notes=(
                "Project the facilitator dashboard. Counts only - it never carries anyone's work. Read the counts aloud; the screen is not the only way into the room.",
                "Nothing in the afternoon depends on a model answering, so there is no bad news to deliver here. Say that once if the room looks anxious about it.",
            ),
        ),
        Slide(
            id="s19", section="Afternoon", kicker=f"Lab 2 - {ctx.activity(7)}",
            title="GLOW Lab 2: Alt Text and Human Judgment",
            blocks=(
                Para("A machine can tell you what is in the picture."),
                Para("Only you can say what the picture is for.", big=True),
                Para(
                    "So this lab gives you the context in words, and descriptions "
                    "somebody already wrote. Your job is to judge them.",
                ),
            ),
            notes=(
                "Nobody uploads anything. Purpose lives in the words around an image, not in the pixels - a lab built on 'upload it and see' teaches the opposite.",
                "The descriptions are written to be argued with. One is fluent and confidently wrong; that is the one to spend time on.",
            ),
        ),
        Slide(
            id="s20", section="Afternoon", kicker="Lab 2 - the method",
            title="Four questions, in this order",
            blocks=(
                Bullets(ordered=True, items=(
                    "Why is this image here? If you cannot answer, it may not need to be.",
                    "What must a reader know about it to follow the page?",
                    "What can you leave out? Alt text is not an inventory.",
                    "What must a person verify before this goes live?",
                )),
                Para("Generated descriptions are confident and sometimes wrong. Question four is the whole job."),
            ),
            notes=(
                "If you have one, show a generated description that is fluent and factually wrong. It teaches more than any slide.",
                "Decorative images: an empty alt is a decision, and a correct one. Say it explicitly - many people have never been told.",
            ),
        ),
        Slide(
            id="s21", section="Afternoon", kicker=f"Lab 3 - {ctx.activity(8)}",
            title="GLOW Lab 3: Remediation Planning",
            blocks=(
                Para("Take a real document, slide deck, or course page. List what is broken. Then put the fixes in order."),
                Para("Order by who is blocked, not by what is easy.", big=True),
                Para("Then write how you would coach the owner, so the next version starts better."),
            ),
            notes=(
                "Everyone sorts by effort first. The reorder, once someone says \"but this one blocks a student on Monday\", is the lesson.",
            ),
        ),
        Slide(
            id="s22", section="Afternoon", kicker=f"Break - {break_2.minutes} minutes",
            title=f"Back at {break_2.resume}",
            blocks=(Para("The last stretch is the one you take home."),),
            notes=(
                "Short break on purpose. Protect the last 85 minutes; that is where the artifact comes from.",
            ),
        ),
        Slide(
            id="s23", section="Afternoon", kicker=f"Studio - {ctx.activity(9)}",
            title="Accessibility Champion Studio",
            blocks=(
                Para("Design one workflow you can hand to someone else."),
                Bullets(items=(
                    "Who does each step?",
                    "Where is the point a person must review before anything goes out?",
                    "What does the partner learn by doing it, that they did not know before?",
                )),
                Para("Build the workflow that still works when you are on holiday.", big=True),
            ),
            notes=(
                "Workflows shared to the gallery carry a \"Start from this workflow\" link. It fills an empty form only; it never writes over someone's own answers. Anonymous submitters stay anonymous in the attribution.",
            ),
        ),
        Slide(
            id="s24", section="Afternoon",
            kicker=f"Peer review - {peer_review.minutes} minutes - gallery",
            title="Three sentences for someone else",
            blocks=(
                Bullets(ordered=True, items=(
                    "One thing that is strong.",
                    "One risk or missing safeguard.",
                    "One way it could be reused somewhere else.",
                )),
                Para("Supportive, specific, and short. You are reviewing a workflow, not a person."),
            ),
            notes=(
                "The gallery announces new work as a count and waits for the reader to press \"Show new submissions\". Nothing appears underneath anyone mid-read. Say that out loud - it will be noticed in this room, and it should be.",
            ),
        ),
        Slide(
            id="s25", section="Afternoon", kicker=f"Capstone - {ctx.activity(10)}",
            title="Say it in four sentences",
            blocks=(
                Para("What is your workflow? Who does it help? What do they learn?"),
                Para("And how does it keep going after today?"),
            ),
            notes=(
                "Take three or four out loud, from volunteers. Then send everyone to the artifact page - that is the next slide and it needs two full minutes.",
            ),
        ),
        Slide(
            id="s26", section="Afternoon", kicker="Take it with you",
            title="My take-home artifact",
            blocks=(
                Para("One page, assembled from what you wrote today: your workflow, who it helps, the human-review gate in your own words, and your 30-day commitment."),
                Bullets(items=(
                    "Print it, or download it as a single file that still opens years from now.",
                    "Email it to yourself with your agent package and a link back to everything else.",
                )),
                Para("This is the thing you forward to a director on Monday.", big=True),
            ),
            notes=(
                "Do not rush this. Two minutes each, and it is the highest-value two minutes of the day.",
                "The plain text of the artifact is in the email body too, because institutional mail gateways strip attachments.",
            ),
        ),
        Slide(
            id="s27", section="Afternoon", kicker=f"Activity 11 - {ctx.activity(11)}",
            title="How this gets used where you work",
            blocks=(
                Definitions(items=(
                    ("One workflow", "that you will actually try."),
                    ("One partner", "or team you will try it with."),
                    ("One safeguard", "you will use every single time."),
                    ("One first step", "small enough to do this week."),
                    ("Who needs to know", "or approve it - a manager, a comms lead, an IT policy."),
                    ("What it looks like if it worked", "in one sentence you could say to them."),
                )),
            ),
            notes=(
                "Small is the point. \"Rewrite one email template\" beats \"audit the LMS\".",
                "The last two are the additions, and they are the difference between a good intention and something that survives an institution. A workflow nobody approved and nobody measured gets forgotten.",
                "Nobody is going to chase them about this. Say so, and say where help is: support@community-access.org.",
            ),
        ),
        Slide(
            id="s28", section="Close", kicker=close_at, title="The commitment wall",
            blocks=(
                Para("Every commitment in this room, on one screen, with no names on it."),
                Para("A promise made in front of strangers should not carry a name unless the person who made it decides to say it out loud."),
            ),
            notes=(
                "Project it. Read three aloud. Do not comment on them, do not rank them, do not add a moral.",
                "Then go straight to what happens next. The last five minutes belong to the session evaluation.",
            ),
        ),
        Slide(
            id="s29", section="Close", kicker="After today", title="What happens next",
            blocks=(
                Bullets(items=(
                    "Within 48 hours: a resource packet, and your exports in Markdown, JSON, HTML and Word.",
                    "In 30 days: one message quoting your own commitment back to you, with a link to your follow-through log.",
                    "Whenever you need it: support@community-access.org. Nobody will chase you, and anybody who writes gets help.",
                    "Always: GLOW is free, open source, and built by the community it serves.",
                )),
                Url("letitglow.app"),
            ),
            notes=(
                "Nobody is emailed twice, nobody who did not give an address is on the list, and the nudge is a command a person runs after looking at what is about to go out.",
            ),
        ),
        Slide(
            id="s30", section="Close", kicker="Thank you", title="Go make one more champion",
            blocks=(
                Para("You came in as the person who fixes things.", lead=True),
                Para("You are leaving as the person who makes more people who can.", big=True),
                Para("Before you go: the session evaluation. It shapes next year's conference."),
                Para("GLOW is a community project of BITS, an affiliate of the American Council of the Blind.", small=True),
            ),
            notes=(
                "Last slide. Say it, thank them, and hand over to the proctor for the session evaluation. Then stop talking while people fill it in - the five minutes are theirs.",
                "Do not add a Q and A block here - answer at the tables while people pack up.",
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
        f"# {DECK_TITLE}",
        "",
        f"{DECK_SUBTITLE}",
        "",
        f"- Event: {DECK_EVENT}",
        f"- Presenter: {DECK_BYLINE}",
        f"- Join: {ctx.join_display}",
        "",
        "Speaker notes are included under each slide. Thirty slides.",
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


def _markdown_block(block: Content) -> list[str]:
    if isinstance(block, Para):
        return [block.text, ""]
    if isinstance(block, Url):
        return [f"### {block.text}", ""]
    if isinstance(block, Bullets):
        out = []
        for position, item in enumerate(block.items, start=1):
            out.append(f"{position}. {item}" if block.ordered else f"- {item}")
        out.append("")
        return out
    if isinstance(block, Definitions):
        out = [f"- {term}: {meaning}" for term, meaning in block.items]
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

    top = Inches(1.6)
    if slide_data.kicker or intro or caption:
        box = slide.shapes.add_textbox(Inches(0.6), top, Inches(12.1), Inches(0.45 * 3))
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
