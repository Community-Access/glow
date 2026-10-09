# Simplification plan: Accessibility Agents in Action

**Status:** decided and being built. All decisions closed 21 September 2026.
**Written:** 21 September 2026. Revised the same day after a scoping pass.
**Decides:** what the day depends on, what participants are never asked to
know, what gets deleted, and how follow-through works when we are not the ones
doing it.

---

## 1. The goal, stated as a test

Reduce what the day depends on without reducing what it delivers.

A change is good if it removes a dependency, a configuration item, a rehearsal
or a failure mode **and** leaves all five of these true:

1. A participant with **one device and a browser** - a phone counts - completes
   the entire day and leaves with an artifact they would show a director.
2. No exercise requires an AI assistant, an account with any AI vendor, or any
   software installation.
3. No exercise requires a participant to know what MCP, a CLI, an IDE or a
   plugin is.
4. Every exercise ends in a human-review gate the participant wrote themselves.
5. Nobody is asked to be a developer.

The proposal's promise is the source of these: *"Participants do not need to be
AI scientists, AI developers, or programmers. They are met where they are."*

**Invariant 1 has changed, and the change is deliberate.** It previously read
"no laptop", carried by printed worksheet packs. We are not printing. See
section 3.

---

## 2. Decisions now locked

Recorded here so the plan is not re-litigated:

| # | Decision |
|---|---|
| L1 | **No house AI.** GLOW provides no free AI capability to the workshop. Participants who want AI use free ChatGPT, entirely at their option |
| L2 | **GLOW is the integral tool**, and it needs no account and no AI to do real work |
| L3 | **Third-party tools are optional**, never assumed, never required to complete anything |
| L4 | **No printed handouts from us.** Electronic copies only |
| L5 | **MCP, CLIs, IDEs and plugins are invisible to participants.** Not on a slide, not in the agenda, not in the artifact |
| L6 | **No vendor-specific tooling in the room** - not Gemini, Copilot, VS Code, or any other |
| L7 | **Follow-through is self-directed, and support is guaranteed on request.** We do not chase anyone, but anyone who writes to `support@community-access.org` gets help. Decided 21 September 2026 |
| L9 | **Designed for both a conference and a class** (was D2). The day is identical either way; see section 6 for why self-directed follow-through makes the distinction stop mattering |
| L10 | **Keep the 30-day nudge**, reworded as a reminder rather than an offer of support (was D3) |
| L11 | **Do the prompt-card derivation** from the twelve usable agent definitions (was D4). Not optional |
| L13 | **Room signage stays** (was D1a). A dozen sheets for the tables is room furniture, not a per-attendee handout, and it protects the join address - the one thing that must not fail at 8:35 |
| L14 | **Postmark is recommended, not required.** Decided 21 September 2026. The app degrades correctly without it. Two consequences, both accepted: losing your work becomes recoverable only by downloading before you leave, and L10's 30-day nudge cannot run |
| L12 | **Text only into ChatGPT. Never an upload.** Free-tier file and image uploads are capped at roughly two or three per day, unpublished and variable; text is unlimited. Every optional AI step in the day is copy-and-paste text (was D5) |
| L8 | **A participant needs a device.** Decided 21 September 2026 (was D1). A phone counts. "No laptop, no device" is no longer a supported case, and the pre-event message must say so |

---

## 3. The consequence of not printing, stated plainly

The proposal currently promises an offline paper path, and the runbook and
utilization guide both say to print worksheet packs and keep them as the
fallback. Dropping printing removes that fallback, and three things follow:

1. **Every participant needs a device.** A phone is enough - GLOW's pages are
   responsive and the workshop forms work on a small screen - but "no laptop,
   no device" is no longer a supported case.
2. **A dead network becomes a real failure**, not an inconvenience. Previously
   paper carried the day. Now the mitigation is that participants download the
   electronic pack *before* they arrive, and that the pack is usable offline
   once downloaded.
3. **The pre-event message becomes load-bearing.** It must say: bring a device,
   download the pack in advance, print it yourself if you prefer paper.

**Recommendation.** Publish the pack in advance and say so twice - in the
conference description and in any pre-event mail. Keep the Word and HTML packs
(they already exist and cost nothing to serve). If AHG offers a handout service
or a print desk, use it; that is the venue printing, not us.

**This is the one place where simplification genuinely costs something**, and
it was taken as an explicit decision rather than a side effect: **yes, decided
21 September 2026.** What it now forces is in section 8, item 9 - the
propagation list. Nine documents and the deck currently promise a paper path
that will not exist.

One thing it does **not** change: ACB large print typography, the take-home
artifact being printable *by the participant*, and the facilitator printing
their own pocket card and deck handout. Those are not attendee handouts from
us.

---

## 4. What participants see, and what they never see

### They see

- **GLOW**, in a browser, with no account and no sign-in.
- **A workflow they design**, in plain language, with a review step in their
  own words.
- **A prompt they can paste** into free ChatGPT if they want to - and a day
  that is complete if they never do.
- **Real accessibility findings** on real documents, produced by GLOW's audit,
  which is deterministic and involves no AI at all.

### They never see

- The letters M, C and P in that order.
- A command line, an IDE, an extension, a plugin, a config file, or `npm`.
- A vendor name attached to a requirement.
- A request for an API key, an account, or a card.

This is not condescension. It is scope. A disability services coordinator
adopting a repeatable workflow does not need the plumbing, and every piece of
plumbing on a slide is a piece of the audience deciding this is not for them.

**One exception, and it is a door rather than a corridor.** A single optional
appendix in the take-home artifact, for the minority who are technical: *"If
you work with developers, there is a deeper integration - here is where to
read about it."* One link. Never a slide, never in the agenda, never a
prerequisite.

---

## 5. The design

### 5.1 GLOW is the common denominator

The reason GLOW can carry the day is that its core is **deterministic, not
AI**. Verified in the source rather than assumed:

| Tool | AI involved? | Evidence |
|---|---|---|
| **Audit** | No | The only AI in the audit blueprint is a separate endpoint, `/audit/suggest-alt-text`, gated behind `ai_alt_text_enabled()`. Running an audit never touches it |
| **Fix** | Only if ticked | `use_ai = form.get("use_ai") == "on" and ai_heading_fix_enabled()` (`routes/fix.py:349`). Unticked, or unconfigured, and no model runs |
| **Convert** | No | No AI in the route. MarkItDown LLM enhancement is a separately gated flag |
| **Report, reading order** | No | Deterministic throughout |

So AI in GLOW is **strictly additive and opt-in**, not woven through. Same
document in, same findings out, no key, no account, no cost. That is a rare
thing to be able to put in front of a room whose access you cannot predict, and
it is the single fact this whole plan rests on.

GLOW is therefore not "the platform the workshop happens to run on". It is the
tool the workshop teaches, and the exercises produce real output from real
documents the participants bring.

### 5.2 Two paths, not four tiers

1. **GLOW in a browser.** Everything. The whole day. No account, no AI.
2. **Plus free ChatGPT, if you want it.** Paste the prompt the day builds for
   you. An upgrade that deepens the same exercise; never a different exercise,
   never a required one.

Simple enough to say in ten seconds and true enough to hold all day.

### 5.3 The specimen bank carries the AI lesson

With no house AI and third-party AI optional, the "judge the machine" lesson
cannot depend on anybody generating anything. So we show what a machine
produced instead.

Each scenario gains two or three captured AI outputs: one good, one fluent and
confidently wrong, one that hedges and says nothing useful. Participants judge
them.

This is better teaching than live generation, not a consolation prize:

- The wrong answer is wrong **on purpose**, chosen to make the point, rather
  than whatever a model happened to emit at 1:40 PM in front of forty people.
- Everyone argues over the **same** artifact, so the discussion converges.
- It cannot fail, cost money, hit a limit, or embarrass anyone on a projector.
- Someone using free ChatGPT does the same exercise one level deeper: generate
  your own, then compare it to ours. Same worksheet, same review gate.

### 5.4 What an "agent" is in this room

Not a plugin. Not an install. **A prompt, a workflow, and a named human-review
gate** - a repeatable way of working that the participant can hand to a
colleague. It is useful three ways, and each one needs less than the last:

| Form | What it needs |
|---|---|
| A workflow card: who does what, where the review happens | Nothing |
| A GLOW recipe: exact steps and addresses, no login | A browser |
| A pasteable prompt | Free ChatGPT, if they want it |

### 5.4a How much of Accessibility Agents this audience can actually use

An earlier draft of this plan implied more than exists. Corrected, with the
repository checked rather than assumed.

**The integration runs one way only.** `s:\code\agents` has
`mcp-server/tools/glow-tools.js`, which calls GLOW. **GLOW consumes nothing
from the agents project** - a search of `web/src`, `mcp_server` and `docs`
returns zero references. There is no "GLOW learns from the agents" today, and
building one is not a November-sized piece of work.

**Most of the catalogue is for a different audience.** Of 80 agents, about
twelve are usable with a documents-and-communications room:

`document-accessibility-wizard`, `word-accessibility`,
`powerpoint-accessibility`, `excel-accessibility`, `pdf-accessibility`,
`office-remediator`, `epub-accessibility`, `markdown-a11y-assistant`,
`wcag-guide`, `accessibility-statement`, `media-accessibility`,
`cognitive-accessibility`.

The remaining ~68 are for developers and repositories: `aria-specialist`,
`web-component-specialist`, `python-specialist`, `wxpython-specialist`,
`nvda-addon-specialist`, `playwright-scanner`, `lighthouse-bridge`, twenty
GitHub workflow managers, and so on. Correct, valuable, and wrong for this
room.

**Three of the ones we would most want are scoped to web code**, and would need
rewriting before a documents audience could use them:

- `alt-text-headings` - "for web applications". Lab 2 is the alt-text lab, so
  this is the single most wanted agent in the catalogue and it is aimed
  elsewhere.
- `text-quality-reviewer` - also "for web applications".
- `screen-reader-lab` - parses HTML and JSX.

Two more read well but are not what their names suggest here:
`email-accessibility` audits HTML email *templates* under client rendering
constraints, not "write a clearer email"; `pdf-remediator` generates scripts.
`document-inventory` is explicitly an internal helper invoked by other agents.

### 5.4b What this means for the title

"Accessibility Agents in Action" has to cash, and on the facts above it does
not cash by itself: participants install nothing, and GLOW does not use the
agents. Two things make it honest, and both are cheap:

**Say what an agent is, out loud, in the first ten minutes.** The definition
above - role, task, trusted guidance, output format, human review - is the
curriculum already. The Accessibility Agents project is then the worked example
of the same idea built at industrial scale, shown once, not a dependency.

**Derive the prompt cards from those twelve agent definitions, by hand.** This
is the only thing that makes "learning from those components" true rather than
aspirational. It is authoring work, not integration: take the WCAG guidance
inside `word-accessibility.md`, `powerpoint-accessibility.md`,
`document-accessibility-wizard.md` and the rest, and turn it into
participant-facing cards that work in a browser or in free ChatGPT. Roughly two
days. It also gives those twelve a second life outside a developer tool, which
is worth something to the agents project independently of this workshop.

If we do not do the derivation, we should stop claiming the day draws on the
agents project and let the title stand on the concept alone. Either is
defensible. Claiming it without doing it is not.

### 5.5 Exercise by exercise

| # | Activity | Change | Needs AI? | Needs an account? |
|---|---|---|---|---|
| 1 | Journey Check-In | Unchanged | No | No |
| 2 | What Problem Are We Solving? | Unchanged | No | No |
| 3 | Fix It for Me vs Teach Me | Unchanged | No | No |
| 4 | Helpful, Risky, Human Required | Sort **real captured outputs** into the three piles, then your own tasks | No | No |
| 5 | Agent Formula | Build the five-part workflow; adapt a ready-made prompt card rather than starting blank | No | No |
| 6 | Lab 1: Communications | Rewrite a real message, then **run GLOW's audit on it** and read real findings | No | No |
| 7 | Lab 2: Alt Text | **Context in text, not an upload** (section 5.6): judge the specimen, then write your own. Optional ChatGPT step is text-only critique | No | No |
| 8 | Lab 3: Remediation | Plan from **real GLOW audit findings**, ordered by who is blocked | No | No |
| 9 | Champion Studio | Design the workflow; the output is a card, a GLOW recipe and a prompt | No | No |
| 10 | Capstone Share-Out | Unchanged | No | No |
| 11 | Engagement Plan (was 30-Day Action Plan) | Rewritten - see section 6 | No | No |

Every row is No twice. That is the test from section 1, met line by line.

### 5.6 Lab 2 without an image upload

The free-tier check (D5) rules out asking anyone to upload an image. It also
rules out uploading a *document*, since the same three-file cap applies. So the
rule for the whole day is simple and worth saying to the room once: **paste
text, never upload.**

That sounds like a constraint on Lab 2. It is actually a better lab.

**Alt text is a judgment about purpose, and purpose lives in the context, not
in the pixels.** An image on a page does not tell you why it is there; the
surrounding text, the document's job and the reader's task do. A lab built on
"upload the picture and see what the machine says" quietly teaches the opposite
lesson - that description is a vision problem.

So Lab 2 gives every participant, on screen and in the pack:

1. **The context, in text.** Where the image sits, what the paragraph around it
   says, what the document is for, who reads it. GLOW extracts this
   deterministically today - `visual_items.py` is pure parsing with zero AI in
   it - so the platform can produce it from a real document the participant
   brings.
2. **The specimens.** Two or three captured descriptions: one good, one fluent
   and confidently wrong, one that hedges.
3. **The four questions**, applied to the specimens and then to their own.

The optional ChatGPT step becomes **text-only critique**: paste the context and
your candidate alt text, and ask for a critique against the four questions.
Unlimited on the free tier, works on a phone, and needs no upload from anyone.

Someone who *does* have an image and a spare upload can still try one. It is a
bonus at the end of the lab, never the spine of it.

---

### 5.7 Showing what investment buys, without selling

Open question, raised 21 September 2026: should the day include a rich
demonstration of what becomes possible with tools a department would have to
buy - Copilot and its equivalents - as something to take to a budget holder?

**Yes, and it does not breach L5 or L6.** Those decisions say nobody is
*required* to have a vendor tool and nobody has to meet plumbing to finish the
day. Showing the ceiling to people who will have to argue for a budget is a
different act from making them depend on it. The audience for "should we
invest in this" is not in the room; it is the director they report to on
Monday. Which means the demonstration has to travel.

Four constraints on doing it well:

1. **Record it. Do not run it live.** A live demo needs the network, the
   vendor's service, and luck, in front of forty people, at the end of a long
   day. A recording is captioned, audio-described, pausable, repeatable, and
   it goes home in the artifact where the budget holder can watch it. At an
   accessibility conference an uncaptioned live demo would also be its own
   embarrassment.
2. **Not at the close.** 4:25 is the commitment wall, and that is the emotional
   end of the day. A product demonstration after it turns a workshop into a
   pitch on the way out. Put it before the capstone, or offer it at lunch and
   after 4:30 as a door rather than a corridor.
3. **Name the category, show one example.** "Assistants that work inside your
   editor, such as..." rather than a single vendor's name on a slide at a
   community conference. The example can be concrete; the framing should not
   read as an endorsement.
4. **Show the ceiling *and* the floor.** The honest demonstration includes what
   it still gets wrong and where a person still decides - the same judgment the
   whole day teaches. A demo that only shows the magic contradicts every other
   hour of the workshop.

**Recommendation:** produce it as a recorded segment, ship it with the
take-home artifact alongside a one-page "what this would cost and what it would
change" note, and give it an optional ten-minute slot before the capstone. That
serves the person who has to make the case without spending the close on it,
and without anyone in the room needing a licence to have had a complete day.

Still to decide: who records it, against what document, and whether the
one-page cost note is ours to write or theirs.

## 6. Follow-through, when we are not doing it

Follow-through is self-directed. That makes **planning** it the last real
exercise of the day rather than an afterthought, because nobody is going to
chase anyone.

Activity 11 becomes an **engagement plan**: how this gets used in their
organisation, with or without GLOW. Four questions currently; six, and sharper:

1. **One workflow** you will use in the next thirty days.
2. **One partner or team** you will use it with.
3. **One safeguard** you will apply every time.
4. **The first step**, small enough to do this week.
5. **Who needs to know or approve** - the manager, the comms lead, the IT
   policy that may or may not permit an AI tool.
6. **What "it worked" looks like**, in one sentence you could say to that
   person.

Five and six are the additions, and they are the difference between a good
intention and something that survives contact with an institution. A workflow
nobody approved and nobody measured does not get adopted; it gets forgotten.

The take-home artifact then carries everything needed to act alone:

- the workflow card,
- the GLOW recipe, with exact addresses and no login,
- the prompt, for anyone who wants to use free ChatGPT,
- the human-review gate in their own words,
- the engagement plan,
- and one line: questions go to `support@community-access.org`.

**The support line is a commitment, not a footnote.** "Write to
`support@community-access.org` and you will get help" is going to be said from
the front of the room, printed in the artifact, and carried home by everyone
who attends. It is the right offer and it is worth making. It also needs an
owner and a rough response expectation before it is said out loud, because the
audience most likely to take it up is the one least well served by being
ignored. One named person and "we answer within a week" is enough; silence
after a promise is worse than never promising.

**On the automated 30-day nudge.** It still works and it costs one command.
With support now guaranteed on request, the nudge is no longer carrying any
support weight - it is simply a reminder that quotes someone's own commitment
back to them and points at the support address. My recommendation is to keep
it: opt-in, fires once, and the replies are the only evidence any of this
stuck.

**Email stays, and it is self-service, not support.** Return links let someone
move from laptop to phone without losing their work, and the artifact email is
how the day leaves the building. With no printed fallback, both matter more
than they did, not less.

---

## 7. What gets deleted

| Deleted | Why it can go |
|---|---|
| `workshop_ai_budget.py` and its request hook | Nothing to ration |
| `GLOW_WORKSHOP_AI_PARTICIPANT_CAP`, `GLOW_WORKSHOP_AI_SESSION_CAP` | Same |
| The cap-reached page and the dashboard AI usage panel | Same |
| The room-wide "pause the built-in AI" switch | Built this session; meaningless without a house AI |
| `OPENROUTER_API_KEY` and three AI flags, from workshop pre-flight | No longer blocking |
| The AI spend estimate and its approval | No spend |
| Rehearsal: hitting a cap | No caps |
| Rehearsal: a full run with the key unset | That run becomes the only run |
| The MCP tool section in generated agent packages | Plumbing, and L5 says participants never see it |
| Four-tier language, everywhere | Two paths |

Blocking pre-flight drops from five rows to one: the session configuration.
Postmark is recommended, not blocking (L14).

**Scope note:** this is the workshop only. GLOW's own alt-text helper, document
chat and transcription elsewhere on the site are untouched and unaffected.

---

## 8. What gets built

Ordered by value per unit of work.

| # | Work | Size |
|---|---|---|
| 1 | Specimen bank: captured AI outputs per scenario, in the worksheet packs and on screen | Medium - the real work |
| 2 | Engagement plan: rewrite activity 11 and the artifact section that carries it | Small |
| 3 | Delete the AI budget subsystem and its surfaces | Small, mostly removal |
| 4 | Strip MCP and tooling language from generated packages and the deck | Small |
| 5 | Labs 1 and 3 anchored on real GLOW audit runs | Small - the tools exist |
| 6 | **Prompt cards derived by hand from the twelve usable agent definitions** (section 5.4a). The only thing that makes "draws on Accessibility Agents" true | Medium - about two days of authoring |
| 7 | Deck, runbook, exercises: two paths, electronic handouts, support address | Small |
| 8 | Pre-event message: bring a device, download the pack, print it yourself if you want paper | Small, and it must not be forgotten |
| 9 | Lab 2 rebuilt on text context from `visual_items.py` plus specimens; no upload anywhere in the day | Small - the extraction exists |
| A1 | **Accessibility Agents: fix the stale GLOW base URL** (`glow-tools.js`, `mcp-server/README.md` point at `glow.bits-acb.org`) | 2 lines |
| A2 | **Accessibility Agents: strip 70 byte-order marks** (`check-skill-conformance.mjs --fix-bom`) | Minutes |
| A3 | **Accessibility Agents: 79 frontmatter names to their folder slug**, plus 3 files with no frontmatter | An afternoon |
| A4 | **Accessibility Agents: add the two unscanned trees to `validate-agents.js`** so it cannot regress | Small, and it must come after A2 and A3 or CI goes red |
| 10 | **Propagate L8** through everything that still promises paper: the guide's "offline fallback worksheets", the utilization guide's "keep backup offline worksheets available", the runbook's "print a dozen" and its backup-worksheet incident step, the run of show's fallback ladder and pre-flight, the pocket card's print checklist, the readiness plan's paper-only rehearsal, and deck slides 2 and 3 which say "on paper, printed packs at the back" | Small each, nine places, easy to miss one |

---

## 9. Open decisions

**D1. Do we accept that a participant now needs a device? DECIDED: yes,
21 September 2026.** Recorded as L8. The propagation work it forces is section
8 item 9.

**D1a. Does "no printing" include the room signage? DECIDED: signage stays,
21 September 2026.** Recorded as L13. Original reasoning below.

Narrow, and it changes
the room setup. The worksheet packs are clearly attendee handouts and they are
now electronic only. Room signage is less clear: `/workshop/session/<code>/signage`
prints one card per activity with the join address in large type and a QR code,
for the tables. It is room furniture rather than a handout, and it is the only
thing that helps someone who arrives late, looks away, or is sitting too far
back to read the projector. If signage also goes, the join address exists only
on the deck and in whatever people typed correctly the first time.

**D2. Conference, class, or both? DECIDED: both, one design,
21 September 2026.** Recorded as L9.

The decision on follow-through is what collapses this question. Once
follow-through is self-directed with support guaranteed on request, the answer
is the same for a conference and for a class: you plan it yourself, and help is
there if you ask. Seeing a class again next week becomes a bonus the facilitator
can use, not a different design. Activity 11 needs no branch.

**D3. Keep or retire the 30-day nudge?**
Recommendation: keep, reworded as a reminder rather than an offer of support.

**D4. Do we do the prompt-card derivation, or drop the claim?**
Section 5.4b. About two days of authoring turns twelve developer-facing agent
definitions into participant-facing cards, and is the only thing that makes the
day genuinely draw on the Accessibility Agents project. The alternative is to
let the title stand on the concept of an agent alone and stop saying the day
uses that work. Both are defensible; claiming it without doing it is not.
Recommendation: do it, because `alt-text-headings` being web-scoped means Lab 2
needs a documents-oriented card written anyway.

**D5. Free ChatGPT specifics. CHECKED 21 September 2026. Recorded as L12.**

What the check found:

- **Text messages are unlimited** on the free tier as of September 2026.
- **Image and file uploads are not.** Third-party trackers report roughly two
  image uploads per rolling 24 hours, and about three file uploads total
  (images, PDFs and documents combined).
- **OpenAI does not publish the numbers.** Engadget, reporting in August 2026,
  states plainly that OpenAI does not share exact limits; users can see their
  remaining usage in Settings, and the thresholds move with load.

**Consequence: Lab 2 cannot be built on image uploads.** Two per day,
unpublished, variable, and quite possibly already spent before the session -
an optional path that silently fails for half the people who try it is worse
than not offering one. See section 5.6 for how Lab 2 works instead.

---

## 10. Build status, 21 September 2026

**Production hotfix awaiting review: [PR #112](https://github.com/Community-Access/glow/pull/112).**
The schema-per-connection fix, isolated in a clean worktree from `origin/main`
so none of the in-progress Postmark work rides along. All four checks pass,
including the Playwright and axe gate. Branch protection requires one
approving review; merging it deploys to production automatically, which is
what puts the fix on the server.


| # | Item | Status |
|---|---|---|
| 1 | Specimen bank | **Done** - `workshop_specimens.py`, four sets, shown on Lab 2 and activity 4, provenance labelled |
| 2 | Engagement plan | **Done** - two new fields, help text wired through `aria-describedby`, carried into the artifact |
| 3 | Delete the AI budget subsystem | **Done** - module, hook, caps, cap page, usage panel and pause switch all removed |
| 4 | Strip plumbing from generated packages | **Done** - and a test now fails if any of sixteen plumbing words reappears |
| 5 | Labs 1 and 3 on real audit runs | **Done** - both already linked to Audit; Lab 2 and the launchpad repointed off the disabled AI tools |
| 6 | Prompt cards from the agent definitions | **Done** - eight cards in `workshop_prompt_cards.py`, shown on five activities, every one a complete five-part formula |
| 7 | Deck, runbook, exercises: two paths | **Done** |
| 8 | Pre-event message | **Done** - `pre-event-message.md` |
| 9 | Lab 2 without an upload | **Done** |
| 10 | Propagate L8 | **Done** - guide, utilization, runbook, run of show, pocket card, deck |
| A1-A4 | Accessibility Agents pre-conference fixes | **Done 21 September** - 152 violations to 0; conformance now gated on every PR. One editorial decision left, recorded in the audit |
| - | **Lab 2 and launchpad pointed at disabled AI tools** | **Fixed** - found while building item 5; every Lab 2 scenario offered a link to a feature L1 switched off |

### Why the Accessibility Agents items are on this list

They are here rather than on a separate track because they are visible to
attendees. The session is named after that project, the take-home artifact
points people at it, and the follow-through design assumes somebody curious
will look. Today, an attendee who installs the Gemini extension on Monday gets
70 skills whose frontmatter no strict parser can see. That is a workshop
quality problem wearing another repository's clothes.

A1 to A4 are the attendee-visible subset of
`agents/docs/CONFORMANCE-AUDIT-2026-09.md`. Everything else in that audit -
tool annotations, structured output, the SDK v2 migration - waits until
December, because none of it is reachable by anyone in the room.

**Deadline: mid-October, or defer all four to December.** Two days of
mechanical work eight weeks out is free. The same two days in the final
fortnight competes with the timed dry run, and the freeze rule says ship
nothing new in the final week. If mid-October passes without them, say so and
move them; nothing is lost.

**And the thing that actually decides November is neither list.** Phase 5 of
the readiness plan - load rehearsal at 30 participants, NVDA then JAWS then
VoiceOver, the degraded-network run, the timed facilitator dry run against
this agenda, freeze week - has had no progress since 21 August and is
entirely outstanding. It cannot be compressed, because it needs a room, a
calendar and other people. Every scheduling decision above should be read
against that.

## 11. Sequence

1. Answer D1 to D5.
2. Write the specimen bank. Longest lead time, so start it first.
3. Delete the AI budget subsystem; strip MCP and tooling language.
4. Rewrite activity 11 as the engagement plan, and the artifact that carries it.
5. Anchor Labs 1 and 3 on real audit runs.
6. If D4 is yes, derive the twelve prompt cards. Independent of the code
   work, so it can run in parallel.
7. Rewrite the deck, runbook and exercises to two paths and electronic packs.
8. Draft the pre-event message.
8a. Accessibility Agents A1 to A4, if mid-October has not passed. Independent
    of everything else, so it can run in parallel.
9. Regenerate the deck in all four formats; re-run the accessibility sweep.
10. Dry run against the real agenda, on a phone, with the specimens on screen.
