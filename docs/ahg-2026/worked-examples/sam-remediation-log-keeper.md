# Worked example: Sam's remediation log keeper

Role card: Compliance and procurement.

Sam Okafor is the IT accessibility coordinator at Mesa Ridge State
University. Sam reports to the CIO, who asked one question after the Title II
deadline passed: "Where are we, and can we prove it?" Sam has a spreadsheet
named `FINAL_final_v3.xlsx`, and would like a better answer.

The answers in step 4 are examples written for the workshop. On the day,
everyone's own AI writes its own.

## 1. The problem

Title II asks public institutions to make web content and course materials
meet WCAG 2.1 AA. Nobody fixes 40,000 files in a semester. What an
institution can show is a defensible record: what was checked, what was
found, what is fixed first and why, who decided, and when.

PSY 101 is one course. Sam wants a log entry for it that would survive a
complaint, an audit, and the CIO reading it on a phone.

## 2. Sam's five answers

| Question | Sam's answer |
|---|---|
| Role: who is this agent? | A remediation log keeper in a university IT accessibility office, working for the accessibility coordinator |
| Task: the one job | Given checker reports for a course's files, produce dated log entries: each barrier, its WCAG criterion, its severity, a priority with the reason, and the evidence source |
| Trusted guidance | WCAG 2.2 (and note the 2.1 AA level the rule names); the checker reports; our remediation priority policy, which puts barriers that block a student first |
| Output format | A table: file, barrier, WCAG criterion with link, severity, priority, reason, evidence, reviewer, status. Then a three-line summary for leadership |
| Human review | The coordinator approves every priority before the log is final, and initials each entry |

## 3. Sam's agent

```markdown
---
name: remediation-log-keeper
description: Turns checker reports for a course into dated, prioritized, evidence-backed remediation log entries.
license: MIT
metadata:
  tier: specialist
  domain: compliance
  output: log
  title: Remediation Log Keeper
  workshop: AHG 2026
  author: Sam Okafor, Mesa Ridge State University
---
## Role

You are a remediation log keeper in a university IT accessibility office.
You work for the accessibility coordinator.

## Task

Given checker reports for a course's files, produce dated log entries: each
barrier, its WCAG criterion, its severity, a priority with the reason, and
the evidence source.

## Trusted guidance

Cite by name and link: WCAG 2.2, noting the 2.1 AA level the Title II rule
names; the checker reports themselves; our remediation priority policy,
which puts barriers that block a student first. Use only the evidence given.

## Output format

A table: file, barrier, WCAG criterion with link, severity, priority,
reason, evidence, reviewer, status. Then three lines for leadership.

## Human review

The coordinator approves every priority and initials every entry before the
log is final. Until then every status is "proposed".

## Never

- Never include student names or accommodation details.
- Never mark anything "compliant". Mark what was checked, by what, and when.
- Never invent a finding that is not in the evidence.
```

## 4. Before and after grounding

### Before: "Make a compliance log for PSY 101"

> Example answer: PSY 101 Accessibility Compliance Log. Overall status:
> Partially compliant (estimated 72%). Issues: missing alt text (high),
> contrast (medium), captions (high), keyboard navigation (medium). Estimated
> remediation time: 6 hours. Recommendation: course is substantially
> compliant pending minor fixes.

A number with no source, a percentage nobody can defend, a "compliant" that
would not survive the first question, and no dates, names or evidence. It is
exactly the kind of log that causes problems later.

### After: given GLOW's reports for the lecture, the gradebook and the lab handout

The evidence, from GLOW:

```text
psy101-week3-lecture.pptx  score 58
2  CRITICAL  PPTX-SLIDE-TITLE    Slide has no title or the title placeholder is empty
1  MEDIUM    PPTX-READING-ORDER  Reading order differs from visual layout
psy101-gradebook.xlsx  score 54
1  MEDIUM    XLSX-COLOR-ONLY     4 empty cells with background color may convey meaning through color alone
3  MEDIUM    XLSX-MERGED-CELLS   Merged range A1:F1 disrupts screen reader navigation
psy101-lab1-stroop.pdf  score 50
1  CRITICAL  PDF-TAGGED          PDF is not tagged
```

> Example answer (first rows; dated 16 November 2026):
>
> | File | Barrier | WCAG | Severity | Priority | Reason | Evidence | Reviewer | Status |
> |---|---|---|---|---|---|---|---|---|
> | Lab 1 handout | Not tagged; structure unavailable to screen readers | [1.3.1](https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html) | Critical | 1 | Due Friday; blocks completing graded work | GLOW PDF-TAGGED | S.O. | Proposed |
> | Week 3 lecture | Two slides without titles | [2.4.6](https://www.w3.org/WAI/WCAG22/Understanding/headings-and-labels.html) | Critical | 2 | Posted now; slows but does not block | GLOW PPTX-SLIDE-TITLE | S.O. | Proposed |
> | Week 3 lecture | Reading order out of sequence on one slide | [1.3.2](https://www.w3.org/WAI/WCAG22/Understanding/meaningful-sequence.html) | Medium | 2 | Same file, same fix session | GLOW PPTX-READING-ORDER | S.O. | Proposed |
> | Gradebook | Status shown by color only | [1.4.1](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html) | Medium | 3 | Instructor-facing template; fix before grades post | GLOW XLSX-COLOR-ONLY | S.O. | Proposed |
>
> For leadership: PSY 101 checked 16 November, 3 files, 5 finding types.
> The one barrier that blocks graded work is first, with a fix due before
> Friday. Nothing here is marked compliant; all priorities await approval.
>
> Not in this evidence: the lab's form fields and its color-dependent
> exercise need a person to check; the slides' "image.png" alt text passes
> the checker and should not.

What changed: every row has a source, a date and a reviewer, priorities have
reasons a person can disagree with, and the gaps in the evidence are written
down instead of hidden.

## 5. In the repository

`community/ahg-2026/remediation-log-keeper/SKILL.md`, with Sam's name in it.

## 6. In the team

The coordinator runs the specialists across the whole course, then hands
every finding to Sam's log keeper last. The office's work becomes one log,
which is the part leadership actually reads.

## 7. Sam's 30-day plan

| Question | Sam's answer |
|---|---|
| One workflow | Every course review ends as log entries, not an email |
| One partner | The registrar's office, who can tell us which courses have the most students |
| One safeguard | Nothing leaves "proposed" without my initials |
| First step this week | Log the ten highest-enrollment courses |
| Who needs to know | The CIO and general counsel |
| What it looks like if it worked | When asked "where are we", I send a link, not a spreadsheet named FINAL_final_v4 |
