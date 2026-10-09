"""The workshop day, in one place.

Before this module the day existed in four places that disagreed: the
participant-facing agenda table on the workshop home page, the "suggested
length" on every activity page, the exercise pack, and the run-of-show a
facilitator was working from. The three code copies totalled 400, 455 and
420 minutes respectively, for a day that has 420 minutes in it.

That is not a cosmetic problem. A participant reading "45 minutes" on the
page while the facilitator gives them 35 concludes they are behind, and a
participant who believes they are behind stops asking for what they need.

So: one ordered list of blocks, wall clock derived from durations, and
everything else -- the agenda table, the activity times, the exercise pack,
the printed run of show -- read from it. ``validate()`` proves the blocks are
contiguous and add up to the day, and a test calls it.

The canonical prose version is ``docs/ahg-2026/run-of-show.md``. If the two
ever disagree, this module is what participants actually see, so this module
is what has to be fixed.
"""

from __future__ import annotations

from dataclasses import dataclass

DAY_START_MINUTES = 8 * 60 + 30   # 8:30 AM
DAY_END_MINUTES = 16 * 60 + 30    # 4:30 PM
LUNCH_MINUTES = 60

# Block kinds. "activity" blocks map to a key in ACTIVITY_ORDER; everything
# else is facilitator scaffolding that must still occupy real minutes.
WELCOME = "welcome"
ACTIVITY = "activity"
PEER_REVIEW = "peer_review"
BREAK = "break"
LUNCH = "lunch"
CLOSE = "close"


@dataclass(frozen=True)
class Block:
    """One block of the day. ``start`` is minutes after midnight."""

    start: int
    minutes: int
    title: str
    mode: str
    kind: str
    activity_key: str = ""
    note: str = ""

    @property
    def end(self) -> int:
        return self.start + self.minutes

    @property
    def clock(self) -> str:
        return f"{_clock(self.start)}-{_clock(self.end)}"

    @property
    def resume(self) -> str:
        """When the room comes back. What a break slide actually needs."""
        return _clock(self.end)

    @property
    def starts_at(self) -> str:
        return _clock(self.start)

    @property
    def length_label(self) -> str:
        return f"{self.minutes} minutes"


def _clock(minutes: int) -> str:
    """12-hour clock with no meridiem, the way a facilitator says it."""
    hour, minute = divmod(minutes, 60)
    hour12 = hour if hour <= 12 else hour - 12
    return f"{hour12}:{minute:02d}"


AGENDA: tuple[Block, ...] = (
    Block(
        start=8 * 60 + 30, minutes=20,
        title="Welcome and how the day works",
        mode="Orientation", kind=WELCOME,
        note="Two ways today, and the first one is enough.",
    ),
    Block(
        start=8 * 60 + 50, minutes=20,
        title="Accessibility Journey Check-In",
        mode="Reflection and group share",
        kind=ACTIVITY, activity_key="journey_check_in",
    ),
    Block(
        start=9 * 60 + 10, minutes=30,
        title="What Problem Are We Solving?",
        mode="Problem framing",
        kind=ACTIVITY, activity_key="problem_statement",
    ),
    Block(
        start=9 * 60 + 40, minutes=30,
        title="Fix It for Me vs Teach Me to Improve It",
        mode="Coaching practice",
        kind=ACTIVITY, activity_key="teach_vs_fix",
    ),
    Block(
        start=10 * 60 + 10, minutes=15,
        title="Break",
        mode="Break", kind=BREAK,
        note="Say it again: send yourself a return link.",
    ),
    Block(
        start=10 * 60 + 25, minutes=30,
        title="Helpful, Risky, or Human Required?",
        mode="Responsible AI boundary map",
        kind=ACTIVITY, activity_key="ai_boundary_map",
    ),
    Block(
        start=10 * 60 + 55, minutes=35,
        title="Accessibility Agent Formula",
        mode="Role, task, guidance, output, human review",
        kind=ACTIVITY, activity_key="agent_formula",
    ),
    Block(
        start=11 * 60 + 30, minutes=45,
        title="GLOW Lab 1: Accessible Communications",
        mode="Hands-on lab",
        kind=ACTIVITY, activity_key="lab_accessible_communication",
    ),
    Block(
        start=12 * 60 + 15, minutes=LUNCH_MINUTES,
        title="Lunch",
        mode="Break", kind=LUNCH,
        note="Nothing in the afternoon depends on a model answering.",
    ),
    Block(
        start=13 * 60 + 15, minutes=10,
        title="Re-entry and room pulse",
        mode="Orientation", kind=WELCOME,
        note="Nobody is behind. There is no behind.",
    ),
    Block(
        start=13 * 60 + 25, minutes=45,
        title="GLOW Lab 2: Alt Text and Human Judgment",
        mode="Hands-on lab",
        kind=ACTIVITY, activity_key="lab_alt_text_decision",
    ),
    Block(
        start=14 * 60 + 10, minutes=45,
        title="GLOW Lab 3: Remediation Planning",
        mode="Hands-on lab",
        kind=ACTIVITY, activity_key="lab_remediation_plan",
    ),
    Block(
        start=14 * 60 + 55, minutes=10,
        title="Break",
        mode="Break", kind=BREAK,
    ),
    Block(
        start=15 * 60 + 5, minutes=40,
        title="Accessibility Champion Studio",
        mode="Workflow design",
        kind=ACTIVITY, activity_key="champion_studio",
    ),
    Block(
        start=15 * 60 + 45, minutes=10,
        title="Peer review round",
        mode="Feedback and refinement", kind=PEER_REVIEW,
        note="Peer feedback is a form on gallery submissions, not a numbered activity.",
    ),
    Block(
        start=15 * 60 + 55, minutes=15,
        title="Capstone Share-Out",
        mode="Share-out and take-home artifact",
        kind=ACTIVITY, activity_key="capstone_shareout",
    ),
    Block(
        start=16 * 60 + 10, minutes=10,
        title="30-Day Action Plan",
        mode="Commitment",
        kind=ACTIVITY, activity_key="action_plan_30_day",
    ),
    Block(
        start=16 * 60 + 20, minutes=5,
        title="The commitment wall",
        mode="Close", kind=CLOSE,
        note="Read three aloud. Do not name anyone.",
    ),
    # AHG asks every speaker to save time for its session evaluation, and the
    # proctor runs it. Five minutes at the end, taken from the peer review
    # round -- the one block the pacing rules already allow to shrink.
    Block(
        start=16 * 60 + 25, minutes=5,
        title="Session evaluation",
        mode="Close", kind=CLOSE,
        note="Hand over to the proctor. Stop talking while people fill it in.",
    ),
)

# The optional lab is deliberately outside the agenda and outside the
# passport: a participant who never opens it has missed nothing the workshop
# promised. A door, not a corridor.
OPTIONAL_LENGTH_LABEL = "20 minutes, optional"


def activity_blocks() -> tuple[Block, ...]:
    return tuple(b for b in AGENDA if b.kind == ACTIVITY)


def activity_minutes() -> dict[str, int]:
    return {b.activity_key: b.minutes for b in activity_blocks()}


def activity_length_label(activity_key: str, default: str = "Varies") -> str:
    minutes = activity_minutes().get(activity_key)
    return f"{minutes} minutes" if minutes else default


def block_for_activity(activity_key: str) -> Block | None:
    for block in activity_blocks():
        if block.activity_key == activity_key:
            return block
    return None


def schedule_rows() -> list[dict[str, str]]:
    """Rows for the participant-facing agenda table.

    Breaks and lunch are included on purpose. A participant who cannot see
    when lunch is has to ask, and some of them will not ask.
    """
    return [
        {"time": b.clock, "title": b.title, "mode": b.mode, "kind": b.kind}
        for b in AGENDA
    ]


def facilitator_rows() -> list[dict[str, str]]:
    """Rows for the facilitator run-of-show strip: same blocks, plus the cue."""
    return [
        {
            "time": b.clock,
            "start": b.starts_at,
            "start_minutes": b.start,
            "end_minutes": b.end,
            "minutes": b.minutes,
            "title": b.title,
            "mode": b.mode,
            "kind": b.kind,
            "activity_key": b.activity_key,
            "note": b.note,
        }
        for b in AGENDA
    ]


def current_block(now_minutes: int) -> Block | None:
    """The block containing ``now_minutes``, or None outside the day."""
    for block in AGENDA:
        if block.start <= now_minutes < block.end:
            return block
    return None


def next_block(now_minutes: int) -> Block | None:
    for block in AGENDA:
        if block.start > now_minutes:
            return block
    return None


def total_minutes() -> int:
    return sum(b.minutes for b in AGENDA)


def working_minutes() -> int:
    """The day minus lunch: the minutes actually spent working."""
    return sum(b.minutes for b in AGENDA if b.kind != LUNCH)


def blocks_of_kind(kind: str) -> tuple[Block, ...]:
    return tuple(b for b in AGENDA if b.kind == kind)


def deck_blocks() -> dict[str, object]:
    """The handful of blocks the projected deck names by name.

    The deck says "back at 10:25" on a break slide and "lunch, 12:15 to 1:15"
    on another. Those are clock times, and a clock time written into a slide
    is a fifth copy of the day waiting to go stale.
    """
    breaks = blocks_of_kind(BREAK)
    lunches = blocks_of_kind(LUNCH)
    peer = blocks_of_kind(PEER_REVIEW)
    closes = blocks_of_kind(CLOSE)
    return {
        "break_1": breaks[0] if breaks else None,
        "break_2": breaks[1] if len(breaks) > 1 else None,
        "lunch": lunches[0] if lunches else None,
        "peer_review": peer[0] if peer else None,
        "close_at": closes[0].starts_at if closes else "",
    }


def validate() -> list[str]:
    """Return a list of problems with the agenda. Empty means it holds.

    Called by a test rather than at import, so a mistake fails a suite
    instead of taking the site down.
    """
    problems: list[str] = []

    if AGENDA[0].start != DAY_START_MINUTES:
        problems.append(f"day starts at {_clock(AGENDA[0].start)}, expected {_clock(DAY_START_MINUTES)}")
    if AGENDA[-1].end != DAY_END_MINUTES:
        problems.append(f"day ends at {_clock(AGENDA[-1].end)}, expected {_clock(DAY_END_MINUTES)}")

    for earlier, later in zip(AGENDA, AGENDA[1:], strict=False):
        if earlier.end != later.start:
            problems.append(
                f"gap or overlap between {earlier.title!r} ending {_clock(earlier.end)} "
                f"and {later.title!r} starting {_clock(later.start)}"
            )

    if total_minutes() != DAY_END_MINUTES - DAY_START_MINUTES:
        problems.append(f"blocks total {total_minutes()} minutes, day is {DAY_END_MINUTES - DAY_START_MINUTES}")

    lunch = [b for b in AGENDA if b.kind == LUNCH]
    if len(lunch) != 1 or lunch[0].minutes != LUNCH_MINUTES:
        problems.append("expected exactly one lunch block of 60 minutes")

    keys = [b.activity_key for b in activity_blocks()]
    if len(keys) != len(set(keys)):
        problems.append("an activity appears in the agenda more than once")
    if any(not key for key in keys):
        problems.append("an activity block has no activity_key")

    return problems
