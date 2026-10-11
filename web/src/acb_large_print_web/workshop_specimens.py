"""Captured AI output, for judging rather than generating.

The workshop provides no AI of its own, and a participant's own assistant is
optional and capped: free accounts allow roughly two image uploads a day and
do not publish the number. An exercise that depends on anybody generating
anything in the room will fail for some of the room, quietly, halfway through.

So where the day used to call a model, it shows what a model produced. That
turns out to be better teaching, not a consolation:

* The wrong answer is wrong **on purpose**, chosen to make a point, rather
  than whatever a model happened to emit at 1:40 PM in front of forty people.
* Everyone argues over the **same** artifact, so the discussion converges
  instead of scattering across forty different outputs.
* It cannot fail, cost money, hit a limit, or embarrass anyone on a projector.
* Someone who does have an assistant does the same exercise one level deeper:
  write your own, then compare it to these.

**Provenance is a field, and it is not decoration.** A specimen that says it
came from a named assistant on a named date must actually have done so. Until
someone captures real output and records where it came from, a specimen is
``ILLUSTRATIVE`` -- written to teach -- and every surface that shows it says
so. Teaching accessibility professionals to judge AI output while quietly
fabricating the output would be a poor way to spend their trust.
"""

from __future__ import annotations

from dataclasses import dataclass

# Provenance values.
ILLUSTRATIVE = "illustrative"

#: Shown wherever a specimen is displayed, so nobody mistakes a teaching
#: example for a capture.
PROVENANCE_LABELS = {
    ILLUSTRATIVE: "Written for this workshop, not captured from a live assistant.",
}


def provenance_label(provenance: str) -> str:
    """Human-readable provenance. Anything unrecognised is shown verbatim."""
    return PROVENANCE_LABELS.get(provenance, provenance)


# Verdicts. The participant assigns one before being shown ours.
GOOD = "good"
WRONG = "plausible-but-wrong"
EVASIVE = "evasive"

VERDICT_LABELS = {
    GOOD: "Usable",
    WRONG: "Fluent, confident, and wrong",
    EVASIVE: "Says nothing a reader can use",
}


@dataclass(frozen=True)
class Specimen:
    """One piece of machine output, for a participant to judge.

    ``why`` is the answer, and it is deliberately separate from ``text`` so a
    surface can show the output first and the reasoning second. Handing over
    both at once turns judgment into reading.
    """

    id: str
    label: str
    text: str
    verdict: str
    why: tuple[str, ...]
    provenance: str = ILLUSTRATIVE

    @property
    def verdict_label(self) -> str:
        return VERDICT_LABELS.get(self.verdict, self.verdict)

    @property
    def provenance_label(self) -> str:
        return provenance_label(self.provenance)


@dataclass(frozen=True)
class VisualContext:
    """Everything about an image except the image.

    Alt text is a judgment about purpose, and purpose lives in the context,
    not in the pixels: the surrounding text, the document's job, and what the
    reader is trying to do. Handing someone a picture and asking what is in it
    teaches the opposite -- that description is a vision problem.

    This is also what makes the lab work with no upload anywhere. GLOW can
    extract the placement and surrounding text from a real document
    deterministically; ``visual_items.py`` is parsing, with no AI in it.
    """

    document: str
    audience: str
    placement: str
    surrounding_text: str
    #: What is literally visible, stated plainly. Not the purpose - deriving
    #: that from the rest is the exercise.
    visible: tuple[str, ...]


@dataclass(frozen=True)
class SpecimenSet:
    """A context and the candidate outputs written about it."""

    id: str
    activity_key: str
    title: str
    context: VisualContext | None
    prompt_used: str
    specimens: tuple[Specimen, ...]
    #: The scenario this set belongs to, when it belongs to one. A participant
    #: who picked a brief should judge descriptions of *that* brief; anything
    #: else is an arbitrary join they will notice.
    scenario_id: str = ""


# ---------------------------------------------------------------------------
# Lab 2 -- alt text and human judgment
# ---------------------------------------------------------------------------

_ENROLMENT_CHART = SpecimenSet(
    id="enrolment-chart",
    activity_key="lab_alt_text_decision",
    scenario_id="dashboard-screenshot",
    title="A chart in a report to the board",
    prompt_used="Write alt text for this image.",
    context=VisualContext(
        document="The annual accessibility services report, going to the board of trustees.",
        audience="Trustees. Not specialists. Most will read the summary and nothing else.",
        placement="Immediately under the heading 'Demand is outpacing staffing'.",
        surrounding_text=(
            "Requests for alternative-format materials rose again this year, "
            "for the fourth year running, while the team stayed at three "
            "full-time staff. The chart below shows the gap."
        ),
        visible=(
            "A line chart with two lines over five years, 2022 to 2026.",
            "The upper line rises steeply from about 400 to about 1,900.",
            "The lower line is almost flat at 3.",
            "The legend reads 'Format requests' and 'Staff (FTE)'.",
        ),
    ),
    specimens=(
        Specimen(
            id="enrolment-good",
            label="Candidate A",
            text=(
                "Line chart: format requests rose from about 400 in 2022 to "
                "about 1,900 in 2026, while staffing stayed flat at 3 "
                "full-time equivalents."
            ),
            verdict=GOOD,
            why=(
                "It gives the comparison the heading promised, in the units the "
                "reader needs.",
                "It is short enough to be heard without losing the thread.",
                "A trustee who reads only this knows what the chart was for.",
            ),
        ),
        Specimen(
            id="enrolment-wrong",
            label="Candidate B",
            text=(
                "A professional line graph with two trend lines on a white "
                "background, showing steady year-on-year growth in both "
                "categories across a five-year period, with a legend in the "
                "upper right and clearly labelled axes."
            ),
            verdict=WRONG,
            why=(
                "\"Growth in both categories\" is false. Staffing did not grow; "
                "that is the entire point of the chart.",
                "It is fluent and confident, which is exactly why it is "
                "dangerous - nothing in the sentence signals doubt.",
                "It describes the chart's appearance rather than its meaning: "
                "background, legend position, axis labels. None of that is why "
                "the chart is in the report.",
                "Anyone who cannot see the image cannot catch the error. Only "
                "someone who read the surrounding text can.",
            ),
        ),
        Specimen(
            id="enrolment-evasive",
            label="Candidate C",
            text="Chart showing data about accessibility services over time.",
            verdict=EVASIVE,
            why=(
                "Technically true and completely useless.",
                "A reader who hears this knows a chart exists and nothing else.",
                "It is the safest-sounding answer and the one that fails the "
                "reader hardest.",
            ),
        ),
    ),
)

_CAMPUS_MAP = SpecimenSet(
    id="accessible-entrance-map",
    activity_key="lab_alt_text_decision",
    title="A map on a student-facing web page",
    prompt_used="Write alt text for this image.",
    context=VisualContext(
        document="The 'Getting to your exam' page, published a week before exams.",
        audience="Students, including disabled students, often reading on a phone on the day.",
        placement="After the paragraph naming the accessible entrance.",
        surrounding_text=(
            "The accessible entrance to the Hale Building is on the north "
            "side, off Turner Street. The step-free route from the car park "
            "is marked on the map below."
        ),
        visible=(
            "A simplified campus map with a dashed line from a car park to a building.",
            "A wheelchair symbol beside one door on the north side.",
            "Street names: Turner Street, Bellweather Road.",
            "A 'you are here' pin at the car park.",
        ),
    ),
    specimens=(
        Specimen(
            id="map-evasive",
            label="Candidate A",
            text="Map of the campus showing building locations and walking routes.",
            verdict=EVASIVE,
            why=(
                "A student standing in the car park in the rain learns nothing "
                "they can act on.",
                "The information they need - which door, which street - is in "
                "the image and not in this sentence.",
            ),
        ),
        Specimen(
            id="map-good",
            label="Candidate B",
            text=(
                "Step-free route from the Turner Street car park to the "
                "accessible entrance on the north side of the Hale Building: "
                "leave the car park at the Turner Street exit, turn right, and "
                "the marked door is roughly 100 metres along on the left."
            ),
            verdict=GOOD,
            why=(
                "It converts the map into the instruction the map exists to give.",
                "It is long for alt text, and that is correct here: this is "
                "wayfinding, and brevity would cost the reader the journey.",
                "It only works because someone who could see the map wrote it "
                "down. No machine reading pixels reliably produces this.",
            ),
        ),
        Specimen(
            id="map-wrong",
            label="Candidate C",
            text=(
                "A campus map showing the accessible entrance clearly marked "
                "with a wheelchair symbol, with an easy step-free path from "
                "the nearby parking area."
            ),
            verdict=WRONG,
            why=(
                "\"Clearly marked\" and \"easy\" are judgments the writer cannot "
                "make on the reader's behalf.",
                "It says a route exists without saying what the route is. The "
                "reader is told to be reassured rather than told where to walk.",
                "It reads as helpful, which is why it would survive a review "
                "that was only skimming.",
            ),
        ),
    ),
)

_DECORATIVE_FLOURISH = SpecimenSet(
    id="decorative-divider",
    activity_key="lab_alt_text_decision",
    scenario_id="decorative-or-not",
    title="The image that should say nothing",
    prompt_used="Write alt text for this image.",
    context=VisualContext(
        document="A staff newsletter, sent monthly.",
        audience="All staff.",
        placement="Between two unrelated stories, as a visual break.",
        surrounding_text=(
            "...and the library will reopen on the 14th.\n\n[image]\n\n"
            "Nominations for the teaching awards close at the end of the month."
        ),
        visible=(
            "A thin horizontal band of overlapping coloured shapes.",
            "No text, no logo, no people.",
        ),
    ),
    specimens=(
        Specimen(
            id="divider-wrong",
            label="Candidate A",
            text=(
                "A decorative banner with abstract geometric shapes in teal, "
                "coral and cream, creating a modern visual separator between "
                "sections."
            ),
            verdict=WRONG,
            why=(
                "Every word is accurate and the whole thing is wrong.",
                "A screen reader user hears twenty words that carry no "
                "information and interrupt two stories.",
                "This is the most common alt-text failure in real documents: "
                "describing something that should have been silent.",
            ),
        ),
        Specimen(
            id="divider-good",
            label="Candidate B",
            text='alt="" (empty, so the image is skipped)',
            verdict=GOOD,
            why=(
                "An empty alt is a decision, and here it is the correct one.",
                "The image does no work for the reader, so the right amount to "
                "say about it is nothing.",
                "Many people have never been told this is allowed, let alone "
                "that it is often right.",
            ),
        ),
        Specimen(
            id="divider-evasive",
            label="Candidate C",
            text="Image.",
            verdict=EVASIVE,
            why=(
                "Worse than silence: it announces something and then withholds it.",
                "The reader now has to decide whether they missed something. "
                "They did not, but they cannot know that.",
            ),
        ),
    ),
)

# ---------------------------------------------------------------------------
# Activity 4 -- helpful, risky, or human required
# ---------------------------------------------------------------------------

_BOUNDARY_SET = SpecimenSet(
    id="boundary-outputs",
    activity_key="ai_boundary_map",
    title="Four things a machine was asked to do",
    prompt_used="Various. Each output below answers a different request.",
    context=None,
    specimens=(
        Specimen(
            id="boundary-headings",
            label="Request A: turn the bold lines in this document into headings",
            text=(
                "I have converted 14 bold paragraphs to Heading 2. Two were "
                "left alone because they appeared mid-sentence."
            ),
            verdict=GOOD,
            why=(
                "Mechanical, checkable, and reversible.",
                "It reported what it did not do, which is the behaviour you "
                "want and rarely get.",
                "A person can verify this in under a minute.",
            ),
        ),
        Specimen(
            id="boundary-summary",
            label="Request B: summarise this accommodation policy for staff",
            text=(
                "Staff should direct students with disabilities to Disability "
                "Services, who will assess eligibility and arrange approved "
                "accommodations within 10 working days."
            ),
            verdict=WRONG,
            why=(
                "Plausible, readable, and it has quietly invented a deadline.",
                "Summarising policy compresses away the exceptions, which is "
                "where the people who need the policy actually live.",
                "This is the middle pile: useful with review, harmful without. "
                "The safeguard is obvious once named - someone who owns the "
                "policy reads it before it is circulated.",
            ),
        ),
        Specimen(
            id="boundary-purpose",
            label="Request C: decide whether this photo needs alt text",
            text=(
                "This image appears decorative and can be given an empty alt "
                "attribute."
            ),
            verdict=WRONG,
            why=(
                "Whether an image is decorative depends on what the page is "
                "for, and the machine cannot see the page's purpose.",
                "The same photograph is decorative in a newsletter and load-"
                "bearing in a building-access guide.",
                "This belongs in the third pile: a person decides, always.",
            ),
        ),
        Specimen(
            id="boundary-refusal",
            label="Request D: tell me if this document meets WCAG 2.2 AA",
            text=(
                "Based on my review, this document appears to meet WCAG 2.2 "
                "Level AA requirements."
            ),
            verdict=WRONG,
            why=(
                "A conformance claim is a legal statement, and nothing here "
                "was tested.",
                "It cannot run a screen reader, check focus order, or ask a "
                "user. It read some text and produced a reassuring sentence.",
                "The honest version states what was checked, what was not, and "
                "leaves the claim to a person. Compare this with what your own "
                "agent should say when a tool is unavailable.",
            ),
        ),
    ),
)


_TACTILE_GRAPHIC = SpecimenSet(
    id="tactile-graphic",
    activity_key="lab_alt_text_decision",
    scenario_id="tactile-graphic",
    title="A photograph of an accommodation, in a handout about that accommodation",
    prompt_used="Write alt text for this image.",
    context=VisualContext(
        document="A handout for STEM faculty explaining how tactile graphics are made and requested.",
        audience="Faculty who have never requested one and do not know what to ask for.",
        placement="Under the heading 'What you will receive'.",
        surrounding_text=(
            "A tactile graphic turns a printed diagram into raised lines and "
            "textures a student reads by touch. Allow three weeks. The photo "
            "below shows a finished one."
        ),
        visible=(
            "A hand resting on a raised-line diagram on thick paper.",
            "The diagram is a circuit, with raised lines and three textured areas.",
            "A braille label sits beside each textured area.",
            "A printed original lies next to it for comparison.",
        ),
    ),
    specimens=(
        Specimen(
            id="tactile-wrong",
            label="Candidate A",
            text=(
                "A close-up photograph of a person's hand touching a white "
                "embossed document on a wooden desk, with natural lighting "
                "from the left."
            ),
            verdict=WRONG,
            why=(
                "Accurate about the photograph and useless about the subject.",
                "The reader is a faculty member learning what a tactile "
                "graphic *is*. Lighting and desk material answer a question "
                "nobody asked.",
                "This is the most common trap in the whole lab: describing the "
                "photograph instead of the thing the photograph is there to "
                "explain.",
            ),
        ),
        Specimen(
            id="tactile-good",
            label="Candidate B",
            text=(
                "A finished tactile graphic of a circuit diagram: raised lines "
                "for the wires, three textured areas for the components, and a "
                "braille label beside each one. A hand is reading it, with the "
                "printed original alongside for comparison."
            ),
            verdict=GOOD,
            why=(
                "It answers the question the heading asked: what will I receive?",
                "It names the parts that make it a tactile graphic rather than "
                "an embossed picture - raised lines, textures, braille labels.",
                "Longer than usual, and right to be: this image is carrying an "
                "explanation, not decorating one.",
            ),
        ),
        Specimen(
            id="tactile-evasive",
            label="Candidate C",
            text="Tactile graphic example.",
            verdict=EVASIVE,
            why=(
                "A reader who cannot see it now knows an example exists.",
                "The handout's whole purpose is to show faculty what they are "
                "asking for. This sentence withholds exactly that.",
            ),
        ),
    ),
)

_ARCHIVE_PHOTOGRAPH = SpecimenSet(
    id="archive-photograph",
    activity_key="lab_alt_text_decision",
    scenario_id="archive-photograph",
    title="An archive photograph, where the machine knows things it cannot know",
    prompt_used="Write alt text for this image.",
    context=VisualContext(
        document="A digital collections page in a museum's online archive.",
        audience="Researchers, students, and the descendants of people in the collection.",
        placement="Beside the catalogue record, which lists what is actually known.",
        surrounding_text=(
            "Catalogue record: photographer unidentified. Date estimated "
            "1918-1924. Location recorded as 'mill district, unconfirmed'. "
            "Subjects unnamed."
        ),
        visible=(
            "A black and white photograph of eleven people outside a brick building.",
            "Most wear work clothes; two wear aprons.",
            "A painted sign on the building is partly obscured.",
            "The image is creased across one corner.",
        ),
    ),
    specimens=(
        Specimen(
            id="archive-wrong",
            label="Candidate A",
            text=(
                "A group of factory workers, likely textile mill employees, "
                "photographed outside their workplace in the early 1920s, "
                "showing the working conditions of the period."
            ),
            verdict=WRONG,
            why=(
                "The catalogue says photographer unidentified, date estimated, "
                "location unconfirmed, subjects unnamed. This sentence asserts "
                "occupation, industry, relationship to the building, and date.",
                "Every one of those may be true. None is *known*, and an "
                "archive that states them has quietly manufactured provenance.",
                "This is the failure that is hardest to catch, because it reads "
                "like competent cataloguing.",
            ),
        ),
        Specimen(
            id="archive-good",
            label="Candidate B",
            text=(
                "Eleven people stand outside a brick building, most in work "
                "clothes and two in aprons. A painted sign on the building is "
                "partly obscured. The print is creased across one corner. "
                "See the catalogue record for what is known about date and "
                "location."
            ),
            verdict=GOOD,
            why=(
                "It describes what is visible and stops there.",
                "It points at the catalogue rather than competing with it, so "
                "the uncertainty stays where the archive put it.",
                "Noting the crease matters: the condition of a print is part of "
                "what a researcher is looking at.",
            ),
        ),
        Specimen(
            id="archive-evasive",
            label="Candidate C",
            text="Historical photograph from the collection.",
            verdict=EVASIVE,
            why=(
                "Avoids the trap by avoiding the job.",
                "A researcher browsing by ear gets nothing to decide whether "
                "this record is worth opening.",
                "Caution is not the same as care. The good answer describes "
                "carefully; it does not decline to describe.",
            ),
        ),
    ),
)


SPECIMEN_SETS: tuple[SpecimenSet, ...] = (
    _ENROLMENT_CHART,
    _CAMPUS_MAP,
    _DECORATIVE_FLOURISH,
    _TACTILE_GRAPHIC,
    _ARCHIVE_PHOTOGRAPH,
    _BOUNDARY_SET,
)


def specimen_sets_for(activity_key: str) -> tuple[SpecimenSet, ...]:
    return tuple(s for s in SPECIMEN_SETS if s.activity_key == activity_key)


def get_specimen_set(set_id: str) -> SpecimenSet | None:
    for candidate in SPECIMEN_SETS:
        if candidate.id == set_id:
            return candidate
    return None


def set_for_scenario(activity_key: str, scenario_id: str) -> SpecimenSet | None:
    """The set written about *this* scenario, if there is one."""
    if not scenario_id:
        return None
    for candidate in specimen_sets_for(activity_key):
        if candidate.scenario_id == scenario_id:
            return candidate
    return None


def pick_specimen_set(
    activity_key: str, seed: str, scenario_id: str = ""
) -> SpecimenSet | None:
    """The specimens a participant should judge.

    A chosen scenario wins: somebody who picked the archive brief should be
    judging descriptions of the archive photograph, not of a chart from a
    different sector. Only when no scenario is chosen, or none has a set of
    its own, does this fall back to a deterministic pick -- same rule as the
    scenario bank, so a facilitator can walk someone back through what they
    were given.
    """
    import hashlib

    matched = set_for_scenario(activity_key, scenario_id)
    if matched is not None:
        return matched

    sets = specimen_sets_for(activity_key)
    if not sets:
        return None
    digest = hashlib.sha256(f"{activity_key}:{seed}".encode()).hexdigest()
    return sets[int(digest[:8], 16) % len(sets)]


def has_real_captures() -> bool:
    """True once any specimen carries provenance other than illustrative.

    Used by a test: while this is False, every surface must say the specimens
    were written for teaching rather than captured.
    """
    return any(
        specimen.provenance != ILLUSTRATIVE
        for specimen_set in SPECIMEN_SETS
        for specimen in specimen_set.specimens
    )
