# Worked example: Maria's alternate format planner

Role card: Documents and alternate formats.

Maria Alvarez coordinates alternate formats at the Mesa Ridge State
University Disability Resource Center. It is Week 3. Her inbox has 41 new
requests, the semester is eleven days old, and the coffee machine on her
floor has been "temporarily out of order" since August.

The answers in steps 3 and 4 are examples written for the workshop, to show
the shape of a weak answer and a good one. On the day, everyone's own AI
writes its own, and no two will be identical.

## 1. The problem

A student in PSY 101 has an approved accommodation for large print, and uses
text-to-speech for longer readings. The Week 3 required reading, "A Short
History of Forgetting", was posted as a scanned PDF. It cannot be enlarged
cleanly, searched, or read aloud.

Maria does not need a lecture on WCAG. She needs a plan she can act on before
Friday, and a way to stop rebuilding the same plan by hand for every request.

## 2. Her five answers

| Question | Maria's answer |
|---|---|
| Role: who is this agent? | An alternate format planner in a university disability resource center, working for the specialist who handles accommodation requests |
| Task: the one job | Given a checker's report on a course document and the formats a student needs, produce a plan to deliver those formats: what to produce, from which source, in what order, and what a person must check |
| Trusted guidance | WCAG 2.2, especially 1.4.5 Images of Text and 1.1.1 Non-text Content; the ACB large print guidelines; our center's alternate format procedure |
| Output format | A short plan: the problem in one line, then numbered steps with who does each, then the formats to deliver, then a "before you send this" checklist |
| Human review | The alternate format specialist checks the converted text against the original page by page, and the student confirms the format works for them |

## 3. Her agent

GLOW turns the five answers into this file. Maria never typed the headings,
the frontmatter or the never-do list; they come from the template.

```markdown
---
name: alternate-format-planner
description: Plans alternate formats for a course document from a checker's report and the formats a student needs.
license: MIT
metadata:
  tier: specialist
  domain: documents
  output: plan
  title: Alternate Format Planner
  workshop: AHG 2026
  author: Maria Alvarez, Mesa Ridge State University
---
## Role

You are an alternate format planner in a university disability resource
center. You work for the specialist who handles accommodation requests.

## Task

Given a checker's report on a course document and the formats a student
needs, produce a plan to deliver those formats: what to produce, from which
source, in what order, and what a person must check.

## Trusted guidance

Cite by name and link in every answer:

- WCAG 2.2, 1.4.5 Images of Text and 1.1.1 Non-text Content
- ACB Large Print Guidelines
- Our center's alternate format procedure

Work only from the evidence you are given. If something is not in the
evidence, say you cannot see it. Do not guess.

## Output format

The problem in one line. Numbered steps, each with who does it. The formats
to deliver. A "Before you send this" checklist.

## Human review

The alternate format specialist checks the converted text against the
original, page by page. The student confirms the format works for them.

## Never

- Never ask for, or use, student names, records, accommodation details or
  health information.
- Never say a document is "compliant" or "accessible". Say what you checked,
  what you found, and what a person still needs to check.
```

## 4. Before and after grounding

The same agent, asked the same question twice.

### Before: the agent is given only the file name

> Question: Plan large print and audio for psy101-reading-forgetting-scanned.pdf.

> Example answer: To make this PDF accessible, run Adobe Acrobat's "Make
> Accessible" action, add alternative text to all images, ensure a logical
> reading order, and increase the font size to at least 18pt. Then export to
> Word for large print and use a text-to-speech tool for audio. This will make
> the document compliant with WCAG 2.1.

Sounds confident. It is mostly wrong for this file:

- It guessed. It never saw the document and does not know it is scanned.
- "Add alternative text to all images" would describe the pictures of text,
  not turn them into text.
- "Compliant" is a word the agent was told never to use.
- WCAG 2.1, not the 2.2 its instructions name, and no links.

### After: the agent is given GLOW's audit report

The evidence, copied from GLOW's audit of the reading:

```text
psy101-reading-forgetting-scanned.pdf  score 50
CRITICAL  PDF-NO-IMAGES-OF-TEXT  This PDF appears to be entirely scanned
          (all 2 pages are image-only with no extractable text).
CRITICAL  PDF-TAGGED     PDF is not tagged; screen readers cannot determine
          document structure
HIGH      PDF-TITLE      PDF has no title set in document metadata
HIGH      PDF-LANGUAGE   PDF has no language set in document metadata
```

> Example answer:
>
> Problem: the reading is two pages of pictures of text, with no text layer,
> so it cannot be enlarged cleanly, searched or read aloud
> ([WCAG 2.2, 1.4.5 Images of Text](https://www.w3.org/WAI/WCAG22/Understanding/images-of-text.html)).
>
> 1. Specialist: get a clean source. Ask the instructor for the original
>    file; it is often a Word document on someone's laptop. This is faster
>    and more accurate than recognition from a scan.
> 2. If there is no original: run text recognition on the scan, then fix it
>    against the page. Watch the nonsense syllables (DAX, BOK, YAT); text
>    recognition will "correct" them into real words.
> 3. Large print: from the clean text, 18pt Arial, left aligned, real
>    headings for the title and "Discussion questions", a numbered list for
>    the three questions ([ACB Large Print Guidelines](https://acb.org/large-print-guidelines)).
> 4. Audio: from the same clean text, with the syllables spelled out so the
>    voice does not say "dax" as a word.
> 5. Post the clean version to the course for everyone, not only this student.
>
> Deliver: large print Word file, and audio.
>
> Before you send this:
> - [ ] Converted text checked against the scan, page by page
> - [ ] Nonsense syllables match the original exactly
> - [ ] The student has confirmed large print and audio work for them
> - [ ] What I could not check: whether the original has figures not visible
>       in this scan. Ask the instructor.
>
> Sources: [WCAG 2.2](https://www.w3.org/TR/WCAG22/),
> [Understanding 1.4.5](https://www.w3.org/WAI/WCAG22/Understanding/images-of-text.html),
> [ACB Large Print Guidelines](https://acb.org/large-print-guidelines).

What changed: the agent stopped guessing, because it had evidence. It cited
the right criterion, knew what it could not see, and handed the decisions to
a person.

## 5. Her agent in the repository

At 2:20 Maria presses Share. Her agent goes to the Accessibility Agents
repository as `community/ahg-2026/alternate-format-planner/SKILL.md`, with
her name in it. At about 2:50 it is merged on the projector, with the room
watching.

## 6. Her agent in the team

At 3:00 the office team works the whole PSY 101 course. The coordinator sends
the scanned reading to Maria's agent, because that is the job it describes.
Her section of the team report:

> Required reading, psy101-reading-forgetting-scanned.pdf.
> Routed to: alternate-format-planner (Maria Alvarez).
> Evidence: GLOW, 4 findings, 2 critical.
> Plan: clean source from instructor, else text recognition and page-by-page
> check; large print and audio from the clean text; post for all students.
> Reviewer: alternate format specialist. Status: waiting for review.

## 7. Her 30-day plan

| Question | Maria's answer |
|---|---|
| One workflow | Every scanned-reading request goes through the planner before I touch it |
| One partner | Our two student workers, who do the text recognition |
| One safeguard | Nothing goes to a student until the page-by-page check is ticked |
| First step this week | Run the planner on the next five requests and compare with what I would have done |
| Who needs to know | My director, because this changes our intake form |
| What it looks like if it worked | Requests out in three days instead of eight, and no "the syllables were wrong" emails |
