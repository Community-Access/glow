---
title: "PSY 101 sample course: answer key"
lang: en
author: "Jeff Bishop, BITS"
description: "Every barrier planted in the PSY 101 sample course, for facilitators."
---

# PSY 101 sample course: answer key

For facilitators. Every barrier in the sample course was planted on purpose,
and this is the full list, so we can tell whether an agent found what it
should. Regenerate the files with `python scripts/build_ahg_sample_course.py`;
if you change a barrier there, change it here.

The course is fictional: "PSY 101: Introduction to Psychology", Fall 2026,
Dr. Dana Whitfield, Mesa Ridge State University. Every word is original. The
running joke is a course about memory and procrastination that keeps
forgetting things and running late.

## How to read this

Each table lists one file's barriers. The last column says what finds it.

- A GLOW rule ID means GLOW's audit reports it. Checked on 9 October 2026.
- "axe" means axe-core reports it, and so does Accessibility Insights
  FastPass, which runs axe-core. Checked with axe-core on 9 October 2026:
  color-contrast (3 elements), heading-order, html-has-lang, image-alt,
  landmark-one-main and region.
- "A person" means no automated checker reports it. An agent with good
  instructions may, and a person must check. These are the most useful
  barriers in the course, because they show why grounding needs judgment and
  human review on top.

## The course files

The files, and how GLOW scored each one before anyone fixed anything.

| File | What it is | GLOW score |
|---|---|---|
| `psy101-syllabus.docx` | The syllabus, Word | 0 |
| `psy101-week3-lecture.pptx` | Week 3 lecture on memory, PowerPoint | 58 |
| `psy101-gradebook.xlsx` | Gradebook template, Excel | 54 |
| `psy101-reading-forgetting-scanned.pdf` | Required reading, a scanned PDF | 50 |
| `psy101-lab1-stroop.pdf` | Lab handout with a form, PDF | 50 |
| `psy101-announcement.html` | Week 3 course announcement, web page | not a GLOW format |
| `psy101-week3-captions.vtt` | Auto-generated captions for the lecture recording | not a GLOW format |

## Syllabus (Word)

Each row is one planted barrier, who it affects, and what finds it.

| Barrier | Who it affects | WCAG | Found by |
|---|---|---|---|
| Brain logo with no alternative text | Screen reader users | 1.1.1 | GLOW `ACB-MISSING-ALT-TEXT` |
| Bold paragraphs pretending to be headings, so there is no heading structure | Screen reader users navigating by heading; anyone using the navigation pane | 1.3.1, 2.4.6 | GLOW `ACB-FAUX-HEADING` |
| No document title | Screen reader users; anyone with many files open | 2.4.2 | GLOW `ACB-DOC-TITLE` |
| A table used only for layout (instructor details) | Screen reader users, who hear a table that is not one | 1.3.1 | A person |
| Required and optional readings shown only by red and green | People who are color blind; screen reader users | 1.4.1 | A person |
| A typed "1)" list instead of a real numbered list | Screen reader users | 1.3.1 | GLOW `ACB-FAKE-LIST` |
| `NO MAKEUP EXAMS` in capitals, which also contradicts the accommodations statement | Readers with dyslexia; any student with an accommodation | Readability, and a policy problem | A person |
| A long passage set in italics | Readers with low vision or dyslexia | ACB large print | A person |
| Two links both called "click here" | Screen reader users listing links | 2.4.4 | GLOW `ACB-LINK-TEXT` |
| Schedule table with its header row not marked | Screen reader users | 1.3.1 | A person |
| Empty paragraphs used for spacing | Screen reader users, who hear "blank" | 1.3.1 | A person |
| The accommodations statement last, in 8pt light gray | Everyone, and especially the students it is for | 1.4.3, ACB large print | GLOW `ACB-FONT-SIZE-BODY` for size; a person for contrast |
| Body text below 18pt, Word's default styles | Readers with low vision | ACB large print | GLOW `ACB-FONT-SIZE-BODY` |

The teachable moment: the accommodations statement. Every checker can see it
is small. Only a person notices it is at the bottom, in gray, and contradicted
in capitals two sections earlier.

## Week 3 lecture (PowerPoint)

Each row is one planted barrier, who it affects, and what finds it.

| Barrier | Who it affects | WCAG | Found by |
|---|---|---|---|
| No presentation title | Screen reader users | 2.4.2 | GLOW `PPTX-TITLE` |
| Slide 2 has no title; slide 7's title is empty | Screen reader users moving slide to slide | 2.4.6, 1.3.1 | GLOW `PPTX-SLIDE-TITLE` |
| Slide 2 reads 3, 2, 1 to a screen reader | Screen reader users | 1.3.2 | GLOW `PPTX-READING-ORDER` |
| Two slides both titled "Memory" | Screen reader users | 2.4.6 | GLOW `PPTX-DUPLICATE-SLIDE-TITLE` |
| The memory model diagram's alternative text is "image.png" | Screen reader users | 1.1.1 | A person: GLOW counts it as present |
| The keys chart is only a picture, its alt text is "image.png", and its red and green bars carry meaning | Screen reader users; color blind viewers | 1.1.1, 1.4.1 | A person |
| Myth or fact answered only by red and green cells | Color blind viewers; screen reader users | 1.4.1 | A person |
| A wall of 11pt text | Everyone at the back of the room | ACB large print | GLOW `PPTX-SMALL-FONT` |

The teachable moment: "image.png". A file name as alt text passes a checker
that only asks whether alt text exists. Ask the room how many of their own
decks would pass the same way.

## Gradebook (Excel)

Each row is one planted barrier, who it affects, and what finds it.

| Barrier | Who it affects | WCAG | Found by |
|---|---|---|---|
| Merged title and header cells | Screen reader users | 1.3.1 | GLOW `XLSX-MERGED-CELLS` |
| Columns with no usable header | Screen reader users | 1.3.1 | GLOW `XLSX-BLANK-COLUMN-HEADER` |
| Status shown only by a cell's fill color, the cell itself empty | Color blind users; screen reader users, who hear nothing | 1.4.1 | GLOW `XLSX-COLOR-ONLY` |
| Sheets named "Sheet" and "Sheet2" | Screen reader users | 2.4.6 | GLOW `XLSX-SHEET-NAME` |
| No workbook title | Screen reader users | 2.4.2 | GLOW `XLSX-TITLE` |
| A blank spacer row | Screen reader users | 1.3.1 | A person |
| The color legend in 8pt light gray: "Green good, red bad, yellow meh" | Everyone | 1.4.3 | A person |

## Required reading (scanned PDF)

Each row is one planted barrier, who it affects, and what finds it.

| Barrier | Who it affects | WCAG | Found by |
|---|---|---|---|
| Every page is a picture of text, with no text layer | Screen reader users; anyone who needs to enlarge, search or listen | 1.4.5, 1.1.1 | GLOW `PDF-NO-IMAGES-OF-TEXT` |
| Not tagged | Screen reader users | 1.3.1 | GLOW `PDF-TAGGED` |
| No title, no language | Screen reader users | 2.4.2, 3.1.1 | GLOW `PDF-TITLE`, `PDF-LANGUAGE` |

The teachable moment: this is the alternate format request. Fixing the PDF is
one answer; producing large print, plain language and audio from a clean
source is the answer the student asked for. Its last paragraph makes the
argument for you: a reading nobody can review is a reading everybody forgets.

## Lab handout (PDF with a form)

Each row is one planted barrier, who it affects, and what finds it.

| Barrier | Who it affects | WCAG | Found by |
|---|---|---|---|
| Not tagged, and the table is only drawn lines | Screen reader users | 1.3.1 | GLOW `PDF-TAGGED`; a person for the table |
| Three form fields with no labels | Screen reader users, who hear "edit text" three times | 1.3.1, 3.3.2, 4.1.2 | A person |
| The exercise itself depends on seeing color | Blind students; some color blind students | 1.4.1 | A person |
| The deadline in 7pt light gray | Everyone | 1.4.3 | GLOW `PDF-FONT-SIZE` for size; a person for contrast |
| No title, no language | Screen reader users | 2.4.2, 3.1.1 | GLOW `PDF-TITLE`, `PDF-LANGUAGE` |

The teachable moment: the Stroop test cannot be fixed by editing the PDF. A
blind student needs an alternative activity that teaches the same idea. That
is the "human required" pile, and a good agent says so instead of inventing a
fix.

## Course announcement (web page)

Each row is one planted barrier, who it affects, and what finds it.

| Barrier | Who it affects | WCAG | Found by |
|---|---|---|---|
| No page language | Screen reader users | 3.1.1 | axe |
| Page title is only "Announcement" | Screen reader users; anyone with many tabs | 2.4.2 | A person |
| The page heading is a bold div, not a heading | Screen reader users | 1.3.1 | A person |
| Heading levels jump from 1 to 4 | Screen reader users | 1.3.1 | axe, as a best practice |
| Image with no alt attribute | Screen reader users | 1.1.1 | axe |
| Light gray instructions | Low vision readers | 1.4.3 | axe |
| "Items in red are due Friday" | Color blind readers; screen reader users | 1.4.1 | A person |
| Links called "Click here" and "Read more" | Screen reader users listing links | 2.4.4 | A person |
| A "Submit" button that is a clickable div, and white on light green | Keyboard and screen reader users; low vision readers | 2.1.1, 4.1.2, 1.4.3 | axe for contrast; a person with a keyboard for the rest |
| The accommodations note in 11px light gray | Everyone, and the students it is for | 1.4.3 | axe |
| No main landmark; content sits outside any region | Screen reader users jumping by landmark | 1.3.1, as a best practice | axe |

## Lecture captions (WebVTT)

Each row is one planted barrier, who it affects, and what finds it.

| Barrier | Who it affects | WCAG | Found by |
|---|---|---|---|
| "herman ebb in house" for Hermann Ebbinghaus, "docks and bach" for DAX and BOK | Deaf and hard of hearing students | 1.2.2 | A person |
| No speaker identification when a student asks a question | Deaf and hard of hearing students | 1.2.2 | A person |
| "As you can see on this graph" with nothing describing the graph | Blind students | 1.2.5, or describe it aloud | A person |
| No capitals or punctuation | Everyone reading captions | Readability | A person |

## What this course teaches, in one line

GLOW and axe find a lot, quickly and the same way every time. The barriers
that matter most to a student, the buried accommodations statement, the
"image.png" alt text, the color-only Stroop test, the misheard name in the
captions, need judgment. That is the case for agents that cite their
evidence, and for a person who reviews everything they say.
