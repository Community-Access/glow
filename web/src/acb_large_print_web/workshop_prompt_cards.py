"""Ready-made accessibility agents, in a form a non-developer can use.

An "agent" in this room is not a plugin and not an install. It is a **role, a
task, trusted guidance, an output format, and a named human-review gate** -
the five-part formula the workshop teaches. A card is one of those, written
out, so a participant has something real to read, argue with and adapt rather
than a blank page to fill.

Each card works three ways, needing less each time:

* **On its own.** The steps are a written procedure. Follow them, or hand them
  to a colleague. Nothing to set up.
* **With GLOW.** ``glow_steps`` names what letitglow.app does for this task,
  in a browser, with no account and no AI.
* **With an assistant, if you already have one.** ``prompt`` is pasteable into
  free ChatGPT or anything else. Text only - never an upload, because free
  accounts cap uploads and do not cap text.

**On provenance.** These are derived by hand from the Accessibility Agents
project (``Community-Access/accessibility-agents``), whose agent definitions
carry unusually careful WCAG guidance but are written for developers working
in a repository. ``source_agent`` names the one each card came from, and
``sources`` carries the same authoritative references that agent cites, so a
participant who wants the original can find it. Nobody has to install
anything to use a card, and no card mentions plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromptCard:
    """One ready-made agent, in the five-part shape the workshop teaches."""

    id: str
    title: str
    #: Which workshop activity this card belongs beside.
    activity_key: str
    #: The person this helps, in their own words rather than a job title.
    for_whom: str

    # The five parts of the formula, spelled out so activity 5 can dissect them.
    role: str
    task: str
    guidance: tuple[str, ...]
    output_format: str
    human_review: str

    #: The pasteable version, for anyone with an assistant.
    prompt: str
    #: What GLOW does for this task, in a browser, free, no account.
    glow_steps: tuple[str, ...] = ()
    #: Which Accessibility Agents definition this was derived from.
    source_agent: str = ""
    #: The authoritative references that agent cites.
    sources: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    @property
    def formula(self) -> tuple[tuple[str, str], ...]:
        """The card as the five-part formula, for reading and dissecting."""
        return (
            ("Role", self.role),
            ("Task", self.task),
            ("Trusted guidance", "; ".join(self.guidance)),
            ("Output format", self.output_format),
            ("Human review", self.human_review),
        )


WCAG_NON_TEXT = (
    "WCAG 1.1.1 Non-text Content",
    "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html",
)
WCAG_HEADINGS = (
    "WCAG 2.4.6 Headings and Labels",
    "https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html",
)
WCAG_LINK_PURPOSE = (
    "WCAG 2.4.4 Link Purpose (In Context)",
    "https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html",
)
WAI_IMAGES = (
    "W3C WAI Images Tutorial",
    "https://www.w3.org/WAI/tutorials/images/",
)
PLAIN_LANGUAGE = (
    "Plain Language Guidelines",
    "https://www.plainlanguage.gov/guidelines/",
)
COGA = (
    "W3C Making Content Usable for People with Cognitive Disabilities",
    "https://www.w3.org/WAI/WCAG2/supplemental/",
)
MS_CHECKER = (
    "Microsoft Accessibility Checker rules",
    "https://support.microsoft.com/en-us/office/rules-for-the-accessibility-checker-651e08f2-0fc3-4e10-aaca-74b4a67101c1",
)
MS_WORD = (
    "Make your Word documents accessible",
    "https://support.microsoft.com/en-us/office/make-your-word-documents-accessible-to-people-with-disabilities-d9bf3683-87ac-47ea-b91a-78dcacb3c66d",
)
MS_POWERPOINT = (
    "Make your PowerPoint presentations accessible",
    "https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25",
)


CARDS: tuple[PromptCard, ...] = (
    PromptCard(
        id="plain-language-rewrite",
        title="Rewrite this so more people can read it",
        activity_key="lab_accessible_communication",
        for_whom="Anyone who sends notices, announcements or instructions to a lot of people.",
        role=(
            "A plain-language editor who works alongside disability services, "
            "and who knows that the people most affected by an unclear notice "
            "are the least likely to ask about it."
        ),
        task=(
            "Rewrite a real message so it can be understood on one reading, "
            "keeping every fact intact."
        ),
        guidance=(
            "Plain Language Guidelines",
            "W3C COGA guidance on making content usable",
            "WCAG 2.4.6 Headings and Labels",
        ),
        output_format=(
            "The rewritten message, then a short list of what changed and why. "
            "Do not change any date, name, room number, deadline or phone number."
        ),
        human_review=(
            "A person who knows the facts checks every number, date and name "
            "against the original before it is sent. Plain language edits are "
            "where facts quietly drift."
        ),
        prompt=(
            "You are a plain-language editor working with a disability "
            "services team. Rewrite the message below so it can be understood "
            "on one reading.\n\n"
            "Rules:\n"
            "- Keep every fact exactly as written: dates, times, names, room "
            "numbers, deadlines, phone numbers and email addresses must not "
            "change.\n"
            "- Short sentences. One idea each.\n"
            "- Put the thing the reader must do first.\n"
            "- Use real headings if the message is longer than a screen.\n"
            "- Make every link say where it goes. Never 'click here' or "
            "'read more'.\n"
            "- Include a welcoming sentence about how to ask for an "
            "adjustment or an alternative format.\n\n"
            "Give me two things: the rewritten message, then a short list of "
            "what you changed and why.\n\n"
            "Then tell me what you were unsure about, and what I should "
            "check before sending.\n\n"
            "Here is the message:\n\n[paste your message here]"
        ),
        glow_steps=(
            "Save the message as a document and run Audit at letitglow.app. "
            "No account needed.",
            "Read the findings for headings, link text and language. Those are "
            "the ones that decide whether a screen reader user can move around "
            "the message.",
            "Run Fix to apply the mechanical corrections, then Audit again to "
            "see what only a person can do.",
        ),
        source_agent="cognitive-accessibility",
        sources=(PLAIN_LANGUAGE, COGA, WCAG_HEADINGS),
    ),
    PromptCard(
        id="meaningful-links",
        title="Make every link say where it goes",
        activity_key="lab_accessible_communication",
        for_whom="Anyone whose pages or emails are full of 'click here' and 'read more'.",
        role="A reviewer who reads a page the way a screen reader user does: by pulling out the links and reading them as a list.",
        task="Find every link whose text does not say where it goes, and write a replacement.",
        guidance=("WCAG 2.4.4 Link Purpose (In Context)", "W3C WAI link text guidance"),
        output_format=(
            "A table: the current link text, why it fails out of context, and "
            "a replacement of five words or fewer where possible."
        ),
        human_review=(
            "Someone who knows where each link actually goes confirms the new "
            "text is true. A confident replacement for the wrong destination is "
            "worse than 'click here'."
        ),
        prompt=(
            "Read the content below and list every link.\n\n"
            "For each one, tell me:\n"
            "1. The current link text.\n"
            "2. Whether it would still make sense read aloud on its own, with "
            "no surrounding sentence. Screen reader users often navigate by "
            "pulling up a list of every link on the page.\n"
            "3. A replacement, as short as you can make it while still being "
            "specific.\n\n"
            "Do not invent destinations. If you cannot tell where a link goes "
            "from what I gave you, say so and ask.\n\n"
            "Here is the content:\n\n[paste your content here]"
        ),
        glow_steps=(
            "Run Audit at letitglow.app and look for link-text findings.",
            "The audit is deterministic: the same document gives the same "
            "findings every time, with no AI involved.",
        ),
        source_agent="alt-text-headings",
        sources=(WCAG_LINK_PURPOSE,),
    ),
    PromptCard(
        id="alt-text-decision",
        title="Decide what an image is for, then describe it",
        activity_key="lab_alt_text_decision",
        for_whom="Anyone who puts images into documents, slides or pages.",
        role=(
            "A colleague who asks what an image is doing before asking what it "
            "shows, and who knows an empty alt is a decision rather than a gap."
        ),
        task="Work out the purpose of an image from its context, then write alt text that serves that purpose.",
        guidance=(
            "WCAG 1.1.1 Non-text Content",
            "W3C WAI Images Tutorial, especially the decision tree",
        ),
        output_format=(
            "The purpose in one sentence, then the alt text, then what a "
            "person must verify before it goes live."
        ),
        human_review=(
            "A person confirms the description is true of the actual image. A "
            "fluent description of something that is not there is the most "
            "common and least visible failure here."
        ),
        prompt=(
            "I am writing alt text. I am going to give you the context in "
            "words rather than the image, because what an image is *for* lives "
            "in the words around it.\n\n"
            "Context:\n"
            "- The document: [what it is, and who reads it]\n"
            "- Where the image sits: [which heading or paragraph it follows]\n"
            "- The text around it: [paste the surrounding sentences]\n"
            "- What is visible in the image: [describe it plainly yourself]\n\n"
            "My draft alt text: [paste your draft, or write 'none yet']\n\n"
            "Please:\n"
            "1. Say in one sentence what this image is doing for the reader.\n"
            "2. Say whether it is decorative. If it is, say so plainly - an "
            "empty alt is the correct answer sometimes.\n"
            "3. Critique my draft against that purpose: what is missing, what "
            "is surplus, what is asserted that the context does not support.\n"
            "4. Offer an alternative.\n"
            "5. List what I must check myself before this goes live.\n\n"
            "Do not describe the image's appearance - colours, layout, "
            "background - unless that appearance is the point."
        ),
        glow_steps=(
            "Upload the document to letitglow.app and run Audit. It lists "
            "every image and flags the ones with no alt text.",
            "The audit tells you which images need a decision. It cannot make "
            "the decision, and it does not pretend to.",
        ),
        source_agent="alt-text-headings",
        sources=(WCAG_NON_TEXT, WAI_IMAGES),
    ),
    PromptCard(
        id="word-document-coach",
        title="Fix a Word document, and teach its author",
        activity_key="lab_remediation_plan",
        for_whom="Anyone who receives Word documents from colleagues and has to make them usable.",
        role=(
            "A coach who leads with what to click in Word itself, because most "
            "authors are not developers and never will be."
        ),
        task="Turn a list of accessibility problems in a .docx into steps its author can follow, in Word, without you.",
        guidance=(
            "Microsoft Accessibility Checker rules",
            "Make your Word documents accessible",
            "WCAG 2.4.6 Headings and Labels",
        ),
        output_format=(
            "Two sections. 'Start here' has the Word UI steps, in order. 'Why "
            "it matters' has one sentence per fix, naming who is blocked."
        ),
        human_review=(
            "The author applies the fixes and re-runs the check themselves. If "
            "you apply them, you have fixed one document; if they do, you have "
            "fixed the next twenty."
        ),
        prompt=(
            "I have a Word document with accessibility problems. I want to "
            "coach its author rather than fix it for them.\n\n"
            "Here is what is wrong:\n\n[paste your audit findings]\n\n"
            "Write me a reply to the author that:\n"
            "- Leads with what to click in Word itself, step by step, in the "
            "order they should do it. Assume they are a capable adult who has "
            "never heard of a heading style.\n"
            "- Gives one sentence per fix on why it matters, naming who is "
            "blocked without it.\n"
            "- Is warm. Nobody learns from a message that makes them feel "
            "caught.\n"
            "- Ends with the one habit that would prevent most of this next "
            "time.\n\n"
            "Do not mention file formats, XML, or scripts."
        ),
        glow_steps=(
            "Run Audit at letitglow.app on the .docx for the findings list.",
            "Run Fix for the mechanical corrections, then Audit again: what "
            "remains is the part that needs a person, and that is what you "
            "coach.",
        ),
        source_agent="word-accessibility",
        sources=(MS_CHECKER, MS_WORD, WCAG_HEADINGS),
    ),
    PromptCard(
        id="slide-deck-coach",
        title="Make a slide deck navigable",
        activity_key="lab_remediation_plan",
        for_whom="Anyone who collects slide decks from presenters and has to publish them.",
        role=(
            "A reviewer who knows a deck is a canvas, not a document, and that "
            "without titles and a set reading order a screen reader user has "
            "nothing to navigate by."
        ),
        task="Turn slide-deck problems into steps the presenter can follow in PowerPoint before they next present.",
        guidance=(
            "Microsoft Accessibility Checker rules",
            "Make your PowerPoint presentations accessible",
        ),
        output_format="A per-slide list: what to change, where the control is, and why.",
        human_review=(
            "Someone reads the deck in outline view and checks the reading "
            "order matches the order it will be spoken in."
        ),
        prompt=(
            "I have a slide deck with accessibility problems. Here is what is "
            "wrong:\n\n[paste your audit findings]\n\n"
            "Write me a short note to the presenter that covers, per slide:\n"
            "- What to change.\n"
            "- Where that control is in PowerPoint.\n"
            "- Why it matters, in one sentence.\n\n"
            "Cover slide titles, reading order, alt text on images and charts, "
            "and text that is only distinguished by colour.\n\n"
            "Keep it to what they can do before they next present."
        ),
        glow_steps=(
            "Audit the .pptx at letitglow.app for the findings.",
            "Convert the deck to a document if you need a readable handout; "
            "the structure comes with it.",
        ),
        source_agent="powerpoint-accessibility",
        sources=(MS_CHECKER, MS_POWERPOINT),
    ),
    PromptCard(
        id="remediation-order",
        title="Put the fixes in the right order",
        activity_key="lab_remediation_plan",
        for_whom="Anyone handed more accessibility problems than they have time for.",
        role="A planner who orders work by who is blocked, not by what is quick.",
        task="Take a list of findings and produce a sequence somebody can actually work through.",
        guidance=(
            "WCAG 2.2 conformance levels, used as a floor rather than a target",
            "Microsoft Accessibility Checker severities",
        ),
        output_format=(
            "An ordered list. For each item: who is blocked today, roughly how "
            "long it takes, and who owns it."
        ),
        human_review=(
            "A person who knows the audience confirms the order. A severity "
            "score does not know that one of these documents is a student's "
            "exam instructions for Monday."
        ),
        prompt=(
            "Here are accessibility findings for a real document:\n\n"
            "[paste your audit findings]\n\n"
            "Context: [what the document is, who reads it, when they need it]\n\n"
            "Put the fixes in the order I should do them. Order by who is "
            "blocked today, not by what is fastest.\n\n"
            "For each item give me: who cannot use this today, roughly how "
            "long the fix takes, and who should own it - me, the author, or a "
            "specialist.\n\n"
            "Then tell me which ones I could skip this week without anybody "
            "being locked out, and say plainly what the cost of skipping is.\n\n"
            "Do not tell me the document is compliant or non-compliant. That "
            "is a judgment for a person who has tested it."
        ),
        glow_steps=(
            "Audit the document at letitglow.app for findings with real "
            "severities.",
            "Export the report if you need something to send to an owner.",
        ),
        source_agent="office-remediator",
        sources=(MS_CHECKER,),
    ),
    PromptCard(
        id="teach-dont-fix",
        title="Answer 'just fix it for me'",
        activity_key="teach_vs_fix",
        for_whom="Anyone who is the only accessibility person in their unit.",
        role=(
            "A colleague who solves the problem today and leaves the person "
            "able to solve it themselves tomorrow."
        ),
        task="Turn a 'fix it for me' request into a reply that does both.",
        guidance=("Plain Language Guidelines", "Your own institution's style and tone"),
        output_format=(
            "A reply of three parts: what you did, the one thing that caused "
            "it, and what to do next time - with where that control lives."
        ),
        human_review="You read it back and ask whether you would want to receive it.",
        prompt=(
            "Somebody sent me this request:\n\n[paste the request]\n\n"
            "What I actually did to fix it:\n\n[describe it]\n\n"
            "Write me a reply that does three things, in this order:\n"
            "1. Tells them it is done.\n"
            "2. Names the single thing that caused it, without jargon.\n"
            "3. Shows what to do next time, with where the control is, in "
            "about a minute of their effort.\n\n"
            "Be warm and brief. Do not lecture, do not list more than one "
            "thing to learn, and do not make them feel caught. Nobody learns "
            "from a message that embarrasses them."
        ),
        source_agent="cognitive-accessibility",
        sources=(PLAIN_LANGUAGE,),
    ),
    PromptCard(
        id="champion-workflow",
        title="Turn what you did into something repeatable",
        activity_key="champion_studio",
        for_whom="Anyone who wants this to keep happening when they are on holiday.",
        role="A colleague who writes down how the work is done so that somebody else can do it.",
        task="Turn a one-off fix into a workflow with named owners and a review gate.",
        guidance=(
            "Your own institution's approval and publishing process",
            "WCAG 2.2 AA as the floor the workflow has to clear",
        ),
        output_format=(
            "Numbered steps, each with an owner. One step marked as the human "
            "review gate, with what that person checks."
        ),
        human_review=(
            "The gate is inside the workflow, named, with a person attached. A "
            "workflow whose review step says 'someone should check' has no "
            "review step."
        ),
        prompt=(
            "I want to turn something I do by hand into a workflow a colleague "
            "could run.\n\n"
            "What I do now: [describe it]\n"
            "Who I do it for: [the partner or team]\n"
            "What goes wrong when it is skipped: [describe it]\n\n"
            "Write it as numbered steps. For each step, say who does it - me, "
            "the content owner, or somebody else.\n\n"
            "Mark exactly one step as the human review gate, and say what that "
            "person checks and what they are allowed to send it back for.\n\n"
            "Then tell me: which step is most likely to be skipped when "
            "somebody is busy, and what would make skipping it obvious."
        ),
        glow_steps=(
            "Any step that says 'check the document' can be letitglow.app's "
            "Audit: free, no account, same answer every time.",
            "Any step that says 'fix the obvious things' can be Fix, followed "
            "by a second Audit to show what is left for a person.",
        ),
        source_agent="document-accessibility-wizard",
        sources=(MS_CHECKER,),
    ),
)


def cards_for(activity_key: str) -> tuple[PromptCard, ...]:
    return tuple(c for c in CARDS if c.activity_key == activity_key)


def get_card(card_id: str) -> PromptCard | None:
    for card in CARDS:
        if card.id == card_id:
            return card
    return None


def all_sources() -> tuple[tuple[str, str], ...]:
    """Every authoritative reference the cards cite, deduplicated."""
    seen: dict[str, str] = {}
    for card in CARDS:
        for title, url in card.sources:
            seen.setdefault(title, url)
    return tuple(sorted(seen.items()))
