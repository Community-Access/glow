"""Scenario bank for the GLOW workshop labs.

Eleven activities with one brief each is thin for a seven-hour day, and it
hands a table of instructional designers the same faculty handout as a table
of PDF remediation specialists. Each lab therefore offers several scenarios
drawn from genuinely different institutional contexts, and a participant can
pick one, be given one, or ignore the bank entirely and bring their own work.

Scenarios are data, not prose in a document, so the app can put the starting
material and the tool links in front of the participant rather than describing
them. Where a scenario names an artifact, it is one of the sample files the
workshop already ships, so "audit this" is a real audit of a real document.

Nothing here is required: a participant who arrives with their own real
problem should use it. The bank exists for the majority who do not have one
to hand at 11:20 on a conference Tuesday.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    """One lab starting point.

    ``sector`` is what makes the bank work: two people at the same table
    should be able to pick briefs that look nothing like each other.
    """

    id: str
    title: str
    sector: str
    summary: str
    brief: tuple[str, ...]
    what_to_notice: tuple[str, ...]
    tools: tuple[str, ...] = ()
    sample_slug: str = ""
    stretch: str = ""


# ---------------------------------------------------------------------------
# GLOW Lab 1 -- Accessible Communications
# ---------------------------------------------------------------------------

_LAB_1 = (
    Scenario(
        id="emergency-notice",
        title="The campus notice nobody could read in time",
        sector="Public university, communications office",
        summary="A building closure notice written in a hurry, sent to 20,000 people.",
        brief=(
            "A water main has failed under the main library. Facilities sent "
            "the communications office three sentences at 6:40 AM and the "
            "notice went out at 7:05 AM to every student and staff address.",
            "The notice is one unbroken paragraph of 180 words. It opens with "
            "two sentences of apology, puts the closure dates in the middle, "
            "and ends with 'please see the link below for further details'. "
            "The link text is 'click here'. The building name appears only in "
            "the subject line. There is no plain statement of what a reader "
            "should do instead.",
            "Three people have already emailed to ask whether the library is "
            "open. A screen reader user replied to say they could not tell "
            "from the message which building was affected.",
        ),
        what_to_notice=(
            "The reader's question is 'is my thing still happening?' and the "
            "answer is buried in the fourth sentence.",
            "'Click here' tells a person tabbing through links nothing at all.",
            "Urgency is not a reason to drop structure. It is the reason to "
            "keep it.",
        ),
        tools=("GLOW:FIX", "GLOW:TEMPLATE"),
        stretch=(
            "Write the version that goes out next time before the emergency, "
            "as a template with the blanks marked."
        ),
    ),
    Scenario(
        id="family-newsletter",
        title="The district newsletter families skim on a phone",
        sector="K-12 school district, family engagement",
        summary="A monthly newsletter that assumes a desktop screen and a lot of patience.",
        brief=(
            "The district sends a monthly newsletter to families. It is built "
            "in a word processor, exported to PDF, and attached to an email.",
            "This month's edition is four pages. Headings are bold 14pt text "
            "rather than real heading styles. Dates sit inside a table used "
            "for layout. Two announcements are images of text made in a "
            "design tool. A quarter of the families in the district read it "
            "on a phone, and a growing number read it in a language other "
            "than the one it was written in.",
            "A parent has asked why the translation tool in their browser "
            "produces nothing for the two most important announcements.",
        ),
        what_to_notice=(
            "Text inside an image cannot be translated, enlarged, searched, "
            "or read aloud. That is four failures from one design decision.",
            "A layout table reads aloud as a sequence of unrelated cells.",
            "Real headings are what make a four-page document skimmable in a "
            "school pickup line.",
        ),
        tools=("GLOW:AUDIT", "GLOW:FIX"),
        sample_slug="board-agenda-docx",
        stretch=(
            "Draft the reply to the parent. It has to explain the fix without "
            "blaming the person who made the graphics."
        ),
    ),
    Scenario(
        id="conference-cfp",
        title="The call for proposals that filtered out the wrong people",
        sector="Professional association, events team",
        summary="A submission call whose form and instructions exclude some of the experts.",
        brief=(
            "An association opens its annual call for proposals. The call is "
            "a web page with a linked PDF and an online form.",
            "The page uses colour alone to mark required fields. The PDF "
            "carries the submission criteria and is a scan of a printed "
            "sheet. The deadline is written as '5pm' with no time zone. The "
            "form's date field expects one format and rejects the other "
            "without saying which it wants.",
            "Two people who requested accommodations last year did not "
            "submit this year.",
        ),
        what_to_notice=(
            "An error message that does not say what would be accepted is a "
            "dead end, not feedback.",
            "A scanned PDF of the criteria means the criteria are unreadable "
            "to some of the people best qualified to meet them.",
            "Who is missing from the submissions is itself accessibility "
            "evidence.",
        ),
        tools=("GLOW:AUDIT", "GLOW:CONVERT"),
        stretch=(
            "Rewrite the accommodations sentence so it invites a request "
            "rather than daring someone to make one."
        ),
    ),
    Scenario(
        id="library-workshop-blurb",
        title="The workshop announcement that hid the important part",
        sector="Community college library",
        summary="A short announcement where the access information is the fine print.",
        brief=(
            "The library runs a weekly drop-in session on research skills. "
            "The announcement goes out on a poster, an email, and a slide in "
            "the lobby loop.",
            "It leads with a slogan, sets the body text at 9pt over a "
            "photographic background, and puts the room number, the captioning "
            "note, and the contact for access requests in a grey footer.",
            "Attendance is good among students who already use the library "
            "and near zero among everyone else.",
        ),
        what_to_notice=(
            "Access information in the footer says the access is an "
            "afterthought, whatever the words claim.",
            "Text over a photograph fails contrast in ways that change with "
            "every image swap.",
            "The same content has to work in print, in email, and on a screen "
            "across the room.",
        ),
        tools=("GLOW:FIX", "GLOW:TEMPLATE"),
        stretch="Produce the one-line version for the lobby slide.",
    ),
)


# ---------------------------------------------------------------------------
# GLOW Lab 2 -- Alt Text and Human Judgment
# ---------------------------------------------------------------------------

_LAB_2 = (
    Scenario(
        id="tactile-graphic",
        title="A photograph of a tactile graphic",
        sector="University disability services, STEM support",
        summary="An image of an accessibility accommodation, used in a handout about it.",
        brief=(
            "A chemistry department handout explains how students can request "
            "tactile versions of diagrams. It includes a photograph of a "
            "raised-line molecular diagram on a desk, with a student's hands "
            "resting on it.",
            "The automated tool suggests: 'A person touching a piece of "
            "paper.' The instructor's own attempt is: 'Tactile graphic of "
            "benzene ring.'",
            "The handout will be read by students, by faculty deciding "
            "whether to request the service, and by the procurement office.",
        ),
        what_to_notice=(
            "Purpose first: is this image showing what the service produces, "
            "or teaching the molecule? The alt text differs completely.",
            "The automated description is not wrong, it is irrelevant -- the "
            "most common failure mode of generated alt text.",
            "A blind student reading a handout about tactile graphics is the "
            "sharpest possible audience for getting this right.",
        ),
        tools=("GLOW:ALT_TEXT", "GLOW:CHAT"),
        stretch=(
            "Write the version for the procurement office, who need to know "
            "what was produced and at what quality."
        ),
    ),
    Scenario(
        id="dashboard-screenshot",
        title="A screenshot of a data dashboard in a board report",
        sector="Nonprofit, annual reporting",
        summary="A complex image carrying the argument of the whole page.",
        brief=(
            "The quarterly board report includes a screenshot of an analytics "
            "dashboard: four charts, a filter bar, and a large number tile "
            "reading '38% increase'.",
            "The surrounding paragraph says 'as the dashboard shows, "
            "engagement is up'. The dashboard itself is a live tool the board "
            "does not have access to.",
            "The report is circulated as a PDF and read aloud by at least one "
            "board member on a commute.",
        ),
        what_to_notice=(
            "If the argument lives in the image, the image is not "
            "decorative and alt text alone will not carry it.",
            "A long description, a data table, or a rewritten sentence may "
            "each be the right answer. Choosing between them is the skill.",
            "'As the dashboard shows' is a sentence that assumes sight.",
        ),
        tools=("GLOW:ALT_TEXT", "GLOW:CHAT", "GLOW:TEMPLATE"),
        sample_slug="board-agenda-html",
        stretch=(
            "Rewrite the paragraph so the image becomes supporting evidence "
            "rather than the argument."
        ),
    ),
    Scenario(
        id="archive-photograph",
        title="A historical photograph with a caption that contradicts it",
        sector="Museum or archive, digital collections",
        summary="An image where accuracy, interpretation, and provenance collide.",
        brief=(
            "A digital collection publishes a 1930s photograph of a factory "
            "floor. The catalogue caption names the building and the year. "
            "The photograph shows roughly forty workers, most of them women, "
            "at long benches.",
            "The existing alt text is the catalogue caption repeated verbatim. "
            "The automated suggestion is 'Black and white photo of a group of "
            "people in a room.'",
            "Curators disagree about how much interpretation belongs in alt "
            "text, and the collection has 60,000 images.",
        ),
        what_to_notice=(
            "Repeating a nearby caption as alt text makes a screen reader say "
            "everything twice and adds nothing.",
            "Describing what is visible is not the same as interpreting it, "
            "and both have a place -- in different fields.",
            "At 60,000 images, the policy matters more than any single "
            "description. That policy is what the participant is designing.",
        ),
        tools=("GLOW:ALT_TEXT", "GLOW:CHAT"),
        stretch=(
            "Draft the two-sentence rule the cataloguing team could actually "
            "follow at scale."
        ),
    ),
    Scenario(
        id="decorative-or-not",
        title="Four images in a newsletter, one of which matters",
        sector="Health system, patient communications",
        summary="A triage exercise: decorative, informative, functional, or complex.",
        brief=(
            "A patient newsletter contains a divider flourish, a stock photo "
            "of a clinician and patient talking, a photograph of the new "
            "clinic entrance including its accessible ramp and door button, "
            "and an infographic of flu-shot clinic times.",
            "Every one of them currently has the alt text 'image'.",
            "The newsletter goes to patients, including people deciding "
            "whether they can physically get into the new building.",
        ),
        what_to_notice=(
            "The entrance photograph is functional information for someone "
            "planning a journey. The stock photo is not.",
            "The infographic's content has to exist somewhere as text, not "
            "just in alt.",
            "'Image' is worse than empty alt: it interrupts and tells nobody "
            "anything.",
        ),
        tools=("GLOW:ALT_TEXT",),
        stretch=(
            "Sort all four before writing any text, and record the reason for "
            "each decision. The reasons are the reusable part."
        ),
    ),
)


# ---------------------------------------------------------------------------
# GLOW Lab 3 -- Remediation Planning
# ---------------------------------------------------------------------------

_LAB_3 = (
    Scenario(
        id="faculty-handout",
        title="Thirty-five pages, three weeks before term",
        sector="University, centre for teaching and learning",
        summary="The classic: one large document, one deadline, one unwilling author.",
        brief=(
            "A faculty member's course handout is 35 pages exported from a "
            "word processor to PDF. It has no tags, no real headings, twelve "
            "images without alt text, four data tables built with tabs, and "
            "a scanned appendix.",
            "A student with a screen reader is enrolled and term starts in "
            "three weeks. The faculty member is willing but has no time and "
            "has never heard of tagging.",
            "You have one afternoon of your own time this week and can ask "
            "for a student worker for two more.",
        ),
        what_to_notice=(
            "What must be fixed before day one is a much shorter list than "
            "what should be fixed eventually.",
            "The scanned appendix may be a rekeying job, not a tagging job. "
            "Knowing which is the plan.",
            "The faculty member has to end this able to do the next one "
            "better, or you will be here again in twelve weeks.",
        ),
        tools=("GLOW:AUDIT", "GLOW:FIX", "GLOW:CONVERT"),
        sample_slug="glow-test-docx",
        stretch=(
            "Write the three-sentence version you would send the department "
            "chair to get the student worker approved."
        ),
    ),
    Scenario(
        id="uncaptioned-course",
        title="Forty videos, no captions, one course shell",
        sector="Community college, online learning",
        summary="A backlog where the cheapest fix is not the right one everywhere.",
        brief=(
            "An online course contains forty recorded lectures, none "
            "captioned. Automatic captions are available and are roughly 85% "
            "accurate, which collapses on the technical vocabulary that the "
            "assessments are built around.",
            "The budget covers professional captioning for about eight hours "
            "of video. The lectures total twenty-two hours.",
            "The course runs again in six weeks and every term after that.",
        ),
        what_to_notice=(
            "85% accuracy sounds close and is not: the wrong 15% is the "
            "graded vocabulary.",
            "Triage by what is assessed, not by what is longest.",
            "A backlog that regenerates every term is a workflow problem "
            "wearing a remediation problem's clothes.",
        ),
        tools=("GLOW:AUDIT", "GLOW:MAGIC"),
        stretch=(
            "Say what changes about how next term's lectures are recorded, "
            "so this list is shorter next time."
        ),
    ),
    Scenario(
        id="vendor-vpat",
        title="A procurement decision with a VPAT full of 'partially supports'",
        sector="State agency or university procurement",
        summary="Remediation you cannot do yourself, and a contract you can still shape.",
        brief=(
            "A department wants to buy a scheduling tool. The vendor's "
            "accessibility conformance report marks most criteria 'partially "
            "supports' with no detail, and the keyboard-navigation row is "
            "blank.",
            "Your own five-minute test finds that the date picker cannot be "
            "operated without a mouse and the error messages are colour only.",
            "The department has already told staff the tool arrives next "
            "month.",
        ),
        what_to_notice=(
            "'Partially supports' with no explanation is not a claim, it is "
            "an absence of one.",
            "The leverage is in the contract, the remediation timeline, and "
            "the interim workaround -- not in fixing someone else's code.",
            "A five-minute keyboard test is evidence a procurement officer "
            "can act on.",
        ),
        tools=("GLOW:AUDIT", "GLOW:TEMPLATE"),
        stretch=(
            "Draft the two questions to send the vendor that cannot be "
            "answered with 'partially supports'."
        ),
    ),
    Scenario(
        id="pdf-archive",
        title="Nine hundred legacy PDFs and no way to fix them all",
        sector="Government or research library, public records",
        summary="A scale problem where the honest plan includes what will not be fixed.",
        brief=(
            "A public-facing archive holds roughly 900 PDFs published over "
            "fifteen years. Perhaps 60 are downloaded more than twice a year. "
            "Most are scans. A handful are legally required to be available.",
            "There is no realistic budget to remediate the archive.",
            "A request has arrived for one specific document from 2011, and "
            "the requester needs it this week.",
        ),
        what_to_notice=(
            "On-demand remediation with a stated turnaround is a legitimate "
            "plan, and often the only honest one.",
            "The 60 documents people actually use are a different project "
            "from the 840 they do not.",
            "Saying out loud what will not be fixed, and how to ask for it, "
            "beats implying everything is fine.",
        ),
        tools=("GLOW:AUDIT", "GLOW:CONVERT", "GLOW:TEMPLATE"),
        stretch=(
            "Write the sentence that goes on the archive page describing how "
            "to request an accessible copy."
        ),
    ),
)


SCENARIOS: dict[str, tuple[Scenario, ...]] = {
    "lab_accessible_communication": _LAB_1,
    "lab_alt_text_decision": _LAB_2,
    "lab_remediation_plan": _LAB_3,
}


def scenarios_for(activity_key: str) -> tuple[Scenario, ...]:
    """Every scenario offered for one activity, or an empty tuple."""
    return SCENARIOS.get((activity_key or "").strip(), ())


def get_scenario(activity_key: str, scenario_id: str) -> Scenario | None:
    """One scenario by id, scoped to its activity."""
    wanted = (scenario_id or "").strip()
    if not wanted:
        return None
    for scenario in scenarios_for(activity_key):
        if scenario.id == wanted:
            return scenario
    return None


def pick_scenario(activity_key: str, seed: str) -> Scenario | None:
    """Choose a scenario for someone who would rather be given one.

    Deterministic in *seed* -- normally the participant key -- so "surprise
    me" does not reshuffle on every page load, and so two people at the same
    table are unlikely to be handed the same brief. A hash rather than a
    random draw also keeps this reproducible when a facilitator is walking a
    participant back through what they were given.
    """
    options = scenarios_for(activity_key)
    if not options:
        return None
    digest = hashlib.sha256(f"{activity_key}:{seed}".encode()).digest()
    return options[digest[0] % len(options)]


def scenario_titles(activity_key: str) -> dict[str, str]:
    """id -> title, for rendering a saved choice without the full record."""
    return {scenario.id: scenario.title for scenario in scenarios_for(activity_key)}
