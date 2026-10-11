---
title: "Worked example: Jordan's faculty coach"
lang: en
author: "Jeff Bishop, BITS"
description: "Worked example: a faculty coach agent, from problem to 30-day plan."
---

# Worked example: Jordan's faculty coach

Role card: Course content and faculty coaching.

Jordan Lee is an instructional designer at Mesa Ridge State University's
Center for Teaching. There are three designers and roughly 1,900 courses.
Jordan has done the math, and it does not end well for anybody's weekends.

The answers in step 4 are examples written for the workshop. On the day,
everyone's own AI writes its own.

## 1. The problem

Dr. Whitfield's PSY 101 syllabus has thirteen kinds of barrier in it. Jordan
could fix them all in an hour. Next semester there would be a new syllabus
with the same thirteen, and 1,899 other courses waiting.

The fix that scales is not Jordan fixing the syllabus. It is Dr. Whitfield
learning the one habit behind most of it, in a note short enough to be read
between classes and kind enough to be read at all.

## 2. Jordan's five answers

Each row is one question, and the answer.

| Question | Jordan's answer |
|---|---|
| Role: who is this agent? | A faculty coach at a university teaching center. Warm, brief, never scolding. Works for the instructional designer |
| Task: the one job | Given a checker's report on a faculty member's document, write a short note that teaches the one habit that would prevent most of the barriers, and lists the rest briefly |
| Trusted guidance | WCAG 2.2; Microsoft's guidance on making Word documents accessible; our center's accessible syllabus template |
| Output format | An email under 200 words: a thank-you, the one habit with how to do it in Word, the two or three other fixes, and an offer of help. Then a note for Jordan of anything left out on purpose |
| Human review | Jordan reads every note before it goes, and checks the tone would land well with this particular person |

## 3. Jordan's agent

```markdown
---
name: faculty-coach
description: Turns a checker's report on a faculty document into a short, kind note that teaches the habit behind the barriers.
license: MIT
metadata:
  tier: specialist
  domain: documents
  output: message
  title: Faculty Coach
  workshop: AHG 2026
  author: Jordan Lee, Mesa Ridge State University
---
## Role

You are a faculty coach at a university teaching center. You are warm,
brief, and never scolding. You work for the instructional designer.

## Task

Given a checker's report on a faculty member's document, write a short note
that teaches the one habit that would prevent most of the barriers, and lists
the rest briefly.

## Trusted guidance

Cite by name and link: WCAG 2.2; Microsoft's guidance on accessible Word
documents; our center's accessible syllabus template. Work only from the
evidence. If something is not in it, say so.

## Output format

An email under 200 words: thank them; the one habit, with how to do it in
Word; two or three other fixes; an offer of help. Then, for the designer
only: anything left out on purpose, and why.

## Human review

The designer reads every note before it is sent and checks the tone suits
this particular person.

## Never

- Never name or describe any student, or any student's accommodation.
- Never say the document is "compliant". Never list every finding; pick.
```

## 4. Before and after grounding

### Before: "Write to Dr. Whitfield about her syllabus"

> Example answer: Dear Dr. Whitfield, I reviewed your syllabus and found
> several accessibility issues that must be corrected to comply with ADA
> Title II and WCAG 2.1 AA. Please address the following: add alt text to all
> images; ensure color contrast meets 4.5:1; use proper heading structure;
> avoid "click here" links; ensure tables have headers; use a minimum font
> size; provide captions for all videos; ensure forms are labeled...

It reads like a parking ticket. It lists problems the syllabus does not have
(there are no videos and no forms), teaches no habit, and will be read by
nobody.

### After: given GLOW's report on the syllabus

The evidence, from GLOW (summarized; the full report has 38 findings):

```text
psy101-syllabus.docx  score 0
7  HIGH      ACB-FAUX-HEADING        Looks like Heading 1 but has no heading style
7  HIGH      ACB-BOLD-HEADINGS-ONLY  Bold used in body text
4  MEDIUM    ACB-FAKE-LIST           Manually typed list numbering detected
2  HIGH      ACB-LINK-TEXT           Non-descriptive hyperlink text: 'click here'
1  CRITICAL  ACB-MISSING-ALT-TEXT    'Picture 1' has no alternative text
1  MEDIUM    ACB-DOC-TITLE           Document has no title set in properties
```

> Example answer:
>
> Subject: One small Word habit for the PSY 101 syllabus
>
> Hi Dana,
>
> Thank you for the syllabus. "We study procrastination in Week 9, and
> frankly I need the data" made our whole office laugh.
>
> One habit would fix most of what our checker found: use Word's Heading
> styles instead of bold text for section titles. Select "Course
> Description", then choose Heading 1 on the Home tab. Screen reader users
> can then jump between sections, and Word builds the navigation pane for
> you ([WCAG 2.2, 1.3.1](https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html)).
>
> Three quick ones while you are in there:
>
> 1. Rename the two "click here" links to say where they go, like "course
>    calendar" ([2.4.4](https://www.w3.org/WAI/WCAG22/Understanding/link-purpose-in-context.html)).
> 2. Give the brain logo a short description: right-click, then "Edit Alt Text".
> 3. Use Word's numbered list button for the grading list.
>
> Happy to do the first one with you in ten minutes, any time this week.
>
> Jordan
>
> For Jordan only: I left out the accommodations statement on purpose. It is
> at the end, in 8pt light gray, and the all-caps "no makeup exams" line
> contradicts it. That is a conversation, not a bullet. I could not check
> color contrast from this report, and the "red means required" reading list
> needs a person to see.

What changed: one habit instead of thirteen orders, real Word steps, a joke
the instructor wrote herself, and the hard conversation handed to a person.

## 5. In the repository

`community/ahg-2026/faculty-coach/SKILL.md`, with Jordan's name in it.

## 6. In the team

The coordinator sends the syllabus findings to the Word specialist for the
fix list, and the same findings to Jordan's coach for the note to the
instructor. Two agents, one document, two different jobs. That is a team.

## 7. Jordan's 30-day plan

Each row is one part of the plan, and the answer.

| Question | Jordan's answer |
|---|---|
| One workflow | Every syllabus review ends with a coach note, not a fixed file |
| One partner | The psychology department, because Dana said yes first |
| One safeguard | I read every note before it goes; nothing auto-sends |
| First step this week | Send three coach notes and count the replies |
| Who needs to know | The center director; this changes what we report as "done" |
| What it looks like if it worked | Next semester's syllabi arrive with real headings, without us touching them |
