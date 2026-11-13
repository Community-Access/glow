# VS Code desktop walkthrough: commands, exact answers and saved results


## Start here

This file contains the exact commands, interview answers, expected results and source instructions for the complete fictional alternate-format exercise. No chat attachment is required: Copilot reads the local kit as a workspace. Do not use private documents. Braille production is not required.

1. Download [the current workshop kit ZIP](https://letitglow.app/ahg/kit.zip). Extract all files to a new writable folder so you do not overwrite an earlier run.
2. Install and open [VS Code](https://code.visualstudio.com) if your institution permits it. Sign in with your approved GitHub account through Accounts. Use File, Open Folder to open the extracted `ahg-2026-agent-kit` folder, not the ZIP or its parent. Trust only this reviewed workshop folder if Restricted Mode prevents access. If Copilot access or writes are unavailable, record Blocked.
3. In Explorer, confirm you can see `my-agent`, `sample-course` and `.github`. Open Copilot Chat with Control+Alt+I on Windows or Control+Command+I on a Mac. Choose Agent mode if available; the mode must permit the expected workspace reads and approved writes.
4. Type each command below in the chat message box and send it. Do not type it in a terminal. Keep one conversation. Approve only the workshop file operations you expect. Read back files in Explorer after each save; a success message alone is not proof.
5. If a slash command is missing, do not pretend it ran. The complete command instructions are included at the end of this file for inspection with a helper. Record Blocked and switch to an approved route if the command or file access cannot be restored.

## Block 1: save and reopen the practice template

Type and send:

````````text
/ready-check
````````


What should happen: Expect the assistant to name the template's seven headings, explain both privacy and human-review rules, and return the whole template. It must wait for you to confirm a successful save and reopen before declaring you ready.

Next: approve saving the practice copy in `my-agent/history/practice-SKILL.md`. Open it in Explorer, check all seven headings and confirm the reopen to Copilot. Only then continue to block 2.

## Block 2: design version 1

Type and send:

````````text
/design-my-agent
````````


What should happen: Expect a role-card question, a starting-agent suggestion, six design questions one at a time, and optional author credit. Use the exact answers below as each question arrives. Expect one complete agent with YAML front matter, all seven template headings, unchanged Never rules, trusted-guidance links and version 1.

When asked about role card and problem, send only:

````````text
Documents and alternate formats. When a student needs a scanned course reading in large print, we lose days working out what to produce and who checks it.
````````


When asked about starting agent, send only:

````````text
Start from the alternate format planner.
````````


When asked about role, send only:

````````text
You are an alternate format planner in a university disability resource center. You work for the specialist who handles accommodation requests.
````````


When asked about task, send only:

````````text
Given a checker's report on a course document and the formats a student needs, plan how to deliver those formats, in order, with who does each step.
````````


When asked about trusted guidance, send only:

````````text
WCAG 2.2, especially 1.4.5 Images of Text and 1.1.1 Non-text Content, the ACB Large Print Guidelines, and our center's alternate format procedure.
````````


When asked about output format, send only:

````````text
The problem in one line, numbered steps with who does each, the formats to deliver, then a checklist.
````````


When asked about example, send only:

````````text
For a scanned reading, state that pages are images of text; assign text conversion and page-by-page checking to a specialist; list the requested large-print output and a review checklist.
````````


When asked about human review, send only:

````````text
The alternate format specialist checks the converted text against the original page by page, and the student confirms the format works.
````````


When asked about optional author credit, send only:

````````text
Use the fictional public credit Workshop Test Author, AHG test run.
````````


Next: open `my-agent/SKILL.md` and `my-agent/history/agent-v1.md`. Confirm both complete texts match and metadata says version 1. Continue to block 3.

## Block 3: try it without checker evidence

Type and send:

````````text
/try-my-agent
````````


What should happen: When asked for the course file, paste psy101-reading-forgetting-scanned.pdf. This is a filename, not an attachment. Expect the assistant to name your agent and either give a cautious plan or ask for missing evidence. Asking for evidence is a successful first try; invented checker findings are not.

Next: approve appending the actual answer to `my-agent/workshop-notes.md`. Reopen the notes; keep the first answer for the grounded comparison.

### Review: make version 2

Send:

````````text
/review-my-agent
````````


Expect twelve Yes/Not yet checks and one proposed change. Read it; it must wait for your permission. If the change is appropriate, send:

````````text
Yes. Make only that proposed change and keep the Never rules unchanged.
````````


Next: approve the expected saves. Open `my-agent/SKILL.md`, `my-agent/history/agent-v2.md` and the installed skill path Copilot names. All must contain the same complete agent with version 2. Keep earlier history copies. Stop for help on a mismatch or failed save; otherwise continue to the next block.

## Block 4: add evidence and compare

Type and send:

````````text
/ground-my-agent
````````


What should happen: Use the same scanned-reading filename and the actual first answer. The complete checker evidence is included in the workspace. Expect a new evidence-based answer, linked WCAG criteria, a before-and-after comparison and remaining human checks. It must not pretend to have opened the original PDF or invent the first answer.

Next: approve appending the actual answer to `my-agent/workshop-notes.md`. Reopen the notes; keep the first answer for the grounded comparison.

### Review: make version 3

Send:

````````text
/review-my-agent
````````


Expect twelve Yes/Not yet checks and one proposed change. Read it; it must wait for your permission. If the change is appropriate, send:

````````text
Yes. Make only that proposed change and keep the Never rules unchanged.
````````


Next: approve the expected saves. Open `my-agent/SKILL.md`, `my-agent/history/agent-v3.md` and the installed skill path Copilot names. All must contain the same complete agent with version 3. Keep earlier history copies. Stop for help on a mismatch or failed save; otherwise continue to the next block.

## Block 5: run the team

Type and send:

````````text
/run-the-office
````````


What should happen: Copilot should read the team instructions and fictional evidence from the workspace. Expect progress by filename and a team report covering all seven course files, your agent's contribution, priorities, evidence limits and human review. If the answer stops partway through, paste: Continue from the last completed file; do not repeat or invent results.

Next: approve appending the actual answer to `my-agent/workshop-notes.md`. Reopen the notes; keep the first answer for the grounded comparison.

### Review: make version 4

Send:

````````text
/review-my-agent
````````


Expect twelve Yes/Not yet checks and one proposed change. Read it; it must wait for your permission. If the change is appropriate, send:

````````text
Yes. Make only that proposed change and keep the Never rules unchanged.
````````


Next: approve the expected saves. Open `my-agent/SKILL.md`, `my-agent/history/agent-v4.md` and the installed skill path Copilot names. All must contain the same complete agent with version 4. Keep earlier history copies. Stop for help on a mismatch or failed save; otherwise continue to the next block.

## Block 6: keep it local or share with permission

No chat command or attachment is needed. If sharing is not approved, keep version 4 locally and record the role that must authorize sharing. Then go to block 7; sharing is not a completion requirement.

If sharing is approved:

1. Open [the workshop share page](https://letitglow.app/ahg/share).
2. Choose your newest saved agent, or paste its complete text. Inspect the preview and remove private or non-public information.
3. Read the destination and permission notice before pressing "Open the share form on GitHub": opening that form sends the text to GitHub before submission.
4. Sign in if asked, inspect the issue content, select the privacy confirmation and press "Submit new issue".
5. Inspect the resulting issue and actual automated reply. If it does not appear, record the issue address and status; do not claim publication succeeded.

Next: return to the same assistant conversation for block 7.

## Block 7: make and review a 30-day plan

Type and send:

````````text
/my-30-day-plan
````````


What should happen: Expect eight questions, one at a time. Use the exact answers below. Expect a short Markdown table in one code block, with unknown approvals and measurements marked pending. It must ask you to review the draft before calling the plan final.

When asked about one workflow, send only:

````````text
Plan alternate formats for the next five scanned readings that come in.
````````


When asked about where it plugs in, send only:

````````text
An approved request starts the task. The agent reads fictional or approved non-sensitive checker evidence. Its draft goes into the existing approved ticket for staff review.
````````


When asked about one partner, send only:

````````text
Our alternate format specialist.
````````


When asked about one safeguard, send only:

````````text
The alternate format specialist checks every converted page against the original. Stop and use the existing manual process if evidence is missing, private data appears or a deadline would be missed.
````````


When asked about approved tools and data, send only:

````````text
Campus approval is pending. The process owner will confirm the approved assistant and allowed data; until then use fictional examples or the written plan without AI.
````````


When asked about first step this week, send only:

````````text
Run the planner alongside the manual process on up to five fictional or approved non-sensitive examples; keep student records out of AI.
````````


When asked about who needs to know, send only:

````````text
My director and the campus process owner must approve the pilot.
````````


When asked about day-30 review, send only:

````````text
Review on 16 December 2026. Baseline and target are pending; the process owner will measure total staff time including review, errors, rework and on-time delivery, then decide whether to continue, revise or stop.
````````


Next: approve the draft save to `my-30-day-plan.md` and reopen it. Explain the trigger, evidence, handoff, reviewer and stop rule to a partner; when alone, compare against the included example. Tell Copilot the correction, approve the final save, reopen it and confirm it contains the reviewed plan. Preserve any previous plan before replacing it.

## Finish: verify what you actually kept

You should now have a readable practice template, complete agent versions 1 to 4, the actual first answer, the grounded comparison, a seven-file team report and a reviewed final 30-day plan. Inspect each saved file, not just the assistant's success message.

Record each block as Pass, Fail, Blocked or Not run, with the actual response and saved filename. Missing quota, a missing command, a denied write or an unavailable service is Blocked, not Pass. Different wording is acceptable; missing evidence, missing files or invented results are not.

## If something stops working

- Do not buy a subscription or upload documents to get through this exercise. All required text is in this walkthrough. These are instructions for a person to run, not a claim that ChatGPT, Copilot or a screen reader has already passed.
- If an account rejects a message or reaches its context or usage limit, save the work completed and record the exact message. Smaller paste parts help with individual-message size, not exhausted quota or total conversation context.
- For an interrupted chat, paste the latest complete agent, the chosen filename and the actual saved first answer into a new approved conversation before resuming the relevant block. Do not let the assistant invent lost work. If it cannot hold the required context, stop that AI test and use the written fallback below.
- A written fallback is a different completion route, not a successful live-AI test. Read the included finished example, copy it into a local document, mark its stages against your own problem, keep a manual review checklist and write the eight plan answers above as your draft. Ask a partner to check the trigger, input, handoff, reviewer and stop rule. Save their correction and the final plan.
- For setup help, contact the workshop organizer or attend the setup table from 10:00. Do not expose private information in screenshots or support requests.

## Finished example for the written fallback

The following is the complete current Maria worked example. Its sample output is not evidence that your own AI run succeeded.



````````text
---
title: "Worked example: Maria's alternate format planner"
lang: en
author: "Jeff Bishop, University of Arizona, IT Accessibility Consultant"
description: "Worked example: an alternate format planner agent, from problem to 30-day plan."
---

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

## 2. Her six answers

Each row is one question, and the answer.

| Question | Maria's answer |
|---|---|
| Role: who is this agent? | An alternate format planner in a university disability resource center, working for the specialist who handles accommodation requests |
| Task: the one job | Given a checker's report on a course document and the formats a student needs, produce a plan to deliver those formats: what to produce, from which source, in what order, and what a person must check |
| Trusted guidance | WCAG 2.2, especially 1.4.5 Images of Text and 1.1.1 Non-text Content; the ACB large print guidelines; our center's alternate format procedure |
| Output format | A short plan: the problem in one line, then numbered steps with who does each, then the formats to deliver, then a "before you send this" checklist |
| Example: one short, good answer | For the scanned week 2 reading in large print: the problem in one line (pictures of text, 1.4.5), then get the publisher's text, or recognize and correct it page by page, then 18 point large print, then the checklist |
| Human review | The alternate format specialist checks the converted text against the original page by page, and the student confirms the format works for them |

## 3. Her agent

GLOW turns the six answers into this file. Maria never typed the headings,
the frontmatter or the never-do list; they come from the template.

```markdown
---
name: alternate-format-planner
description: Plans alternate formats for a course document from a checker's report and the formats a student needs. Use when a student needs a course document in large print, audio or another approved format.
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

This is an intentionally flawed example for discussion, not an answer
participants must reproduce. A good first response asks for evidence.

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

Maria also supplies fictional staff context: the requested formats are
large print and audio, and the reading contains the terms DAX, BOK and YAT
and three discussion questions. These details are not established by the
checker excerpt. Without source text or staff confirmation, ask for them.

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

What changed: the answer now uses the supplied evidence, cites a relevant
criterion and names what still needs checking. A person must verify those
claims; giving an agent evidence does not guarantee it used it correctly.

## 5. Her agent in the team

At 2:15 the office team works the whole PSY 101 course. The coordinator sends
the scanned reading to Maria's agent, because that is the job it describes.
Her section of the team report:

> Required reading, psy101-reading-forgetting-scanned.pdf.
> Routed to: alternate-format-planner (Maria Alvarez).
> Evidence: GLOW, 4 findings, 2 critical.
> Plan: clean source from instructor, else text recognition and page-by-page
> check; large print and audio from the clean text; post for all students.
> Reviewer: alternate format specialist. Status: waiting for review.

## 6. Her agent in the collection

In this example, Maria has permission to publish the instructions under the
MIT licence and has removed private and non-public information. At 3:05
she opens the share page and chooses version 4. Opening the GitHub form
sends the text before submission. Without approval she would instead keep
the reviewed file locally with a permission owner and follow-up date.
GitHub's share form opens already filled in; she checks the privacy check box and
presses Submit new issue. A minute later the reply says "Your agent is in",
and her agent is in the AHG 2026 collection as
`agents/<her GitHub account>/alternate-format-planner/SKILL.md`, committed in
her name. At the end of the day it goes into the Accessibility Agents
project, with her credited.
## 7. Her 30-day plan

Each row is one part of the plan, and the answer.

| Question | Maria's answer |
|---|---|
| One workflow | Pilot production-plan drafts for up to five approved non-sensitive scanned readings, beside our existing process |
| Handoff | Staff keep student details in the case system; the agent reads approved document evidence and a generic format requirement; its draft returns to the specialist's ticket |
| One partner | Our two student workers, who do the text recognition |
| One safeguard | Nothing goes to a student until the page-by-page check box is checked |
| Approved tools and data | Director and campus privacy team confirm the assistant and permitted inputs before use; approval pending in this example |
| First step this week | Rehearse on the fictional reading, then record baseline staff and review time before an approved pilot |
| Who needs to know | My director, because this changes our intake form |
| Day-30 decision | Specialist and director compare total staff time, corrections and on-time delivery; continue only if quality is no worse and the workflow helps |
| Stop and fallback | Uncertain source, private data or a deadline at risk: stop the agent and use the existing production process; never delay an accommodation |

## Sources

Checked on 29 October 2026.

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/), the current W3C Recommendation.
- [Understanding 1.4.5 Images of Text](https://www.w3.org/WAI/WCAG22/Understanding/images-of-text.html)
  and [Understanding 1.1.1 Non-text Content](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html).
- [ACB Large Print Guidelines](https://acb.org/large-print-guidelines), from the
  American Council of the Blind.
````````


## Complete command instructions for a helper

These are reference text, not additional commands to run. The workspace kit supplies the templates and course evidence the commands read.

### Instructions for /ready-check

````````text
---
name: ready-check
description: "Check you are ready for the AHG 2026 workshop. Takes two minutes. Use when setting up, before the day or at 10:30."
disable-model-invocation: true
---
You are running the ready check for a participant at the AHG 2026 workshop.
Be warm and brief. They may be new to VS Code and Copilot.

Check these, in order, and report each as "Ready" or "Needs a hand", with one
plain sentence:

1. You can read `README.md` in this folder. Quote its first heading.
2. You can see the sample course: list the files in `sample-course/`.
3. You can see the evidence: count the files in `sample-course/evidence/`.
4. You can read the agent template: name the headings in `my-agent/SKILL.md`.
5. You can see the office team: count the folders in `office-team/`.
6. You can read the principles card: name the first of the twelve principles
   in `agent-file-principles.md`.

After these read checks, ask permission to create
`my-agent/history/practice-SKILL.md` as a copy of the template. Never replace
an existing file: use an unused numbered suffix for a repeated practice.
Read the saved file back and verify it matches. If saving is denied or fails,
report "Needs a hand", not Ready. Ask the participant to reopen the saved
file with Control+P (Command+P on Mac), confirm that they can read its seven
headings, and wait for their reply.

Only when the six read checks and the save/reopen check succeed, say:

You are ready for 16 November. Getting set up was the hardest part of the day, and it is done.

Then say: Optional practice sharing is only for approved public content.
Opening the GitHub form sends the text before submission. If approved, use
letitglow.app/ahg/share and choose "My practice agent". Otherwise keep your
practice local and record who can confirm permission. At 11:05, use
/design-my-agent for block 2.

If anything needs a hand, say which step, suggest one simple thing to try,
and say: write to jeffbis@arizona.edu, or come to the setup table
from 10:00 on the day. Nobody gets left behind.
````````


### Instructions for /design-my-agent

````````text
---
name: design-my-agent
description: "Block 2. Design your agent by answering six questions. Copilot writes version 1. Use when starting your own agent."
disable-model-invocation: true
---
You are helping a participant design their own accessibility agent. They are
probably not a developer. Make this feel easy and make them feel good about
what they are building. Follow `agent-file-principles.md`.

1. Ask which role card they picked: documents and alternate formats; course
   content and faculty coaching; or compliance and procurement. Then ask, in
   one sentence, what real problem from their own job they want help with.
   Remind them: nothing private, no student names or records. If they give private
   identifying details, a record or an accommodation, do not repeat or use it; ask them to
   describe the problem without it.
2. Open the matching ready-made agents in `examples/agents/` and tell them,
   in one line each, which one is closest. Offer to start from it.
3. Ask these six questions one at a time, and wait for each answer:
   - Role: who is this agent, and who does it work for?
   - Task: what is the one job it does: what is it given, and what does it
     give back?
   - Trusted guidance: which standards and local policies must it use?
   - Output format: what should come back, in what shape, for whom?
   - Example: what would one short, good answer look like? Offer to draft
     one from the example agent if they are unsure.
   - Human review: who checks it before anything goes out?
   If they are unsure, offer the example's answer and let them change it.
4. Ask what public author credit they choose, such as their professional
   name and institution. They may leave the placeholder and add credit
   locally with a helper before sharing; do not insist on personal details.
5. Before replacing a non-template `my-agent/SKILL.md`, preserve its complete
   contents in an unused file in `my-agent/history/` and confirm the copy.
   Write their answers into `my-agent/SKILL.md`, keeping the template's
   headings and its "Never" section exactly. Set `name` to a short lowercase
   name with hyphens, at most 64 characters. Write the `description` as what
   it does in one sentence, then a second sentence starting "Use when". Set
   `author` to the name and institution they gave you, and add
   `version: "1"` under `metadata`. Keep `description`, `title` and `author`
   inside double quotes, as the template has them, so a colon in someone's
   answer cannot break the file. Keep the WCAG 2.2 links in Trusted guidance.
6. Save a complete copy as `my-agent/history/agent-v1.md`. Never replace an
   existing history file; use an unused numbered suffix if needed. Read both
   files back and verify that they match. If saving fails, say which file
   failed and stop for help; do not claim version 1 was saved.
7. Read the finished file back in five lines or fewer, and tell them one
   specific thing their agent does well.

End with: Your agent exists. This is version 1. Next, we put it to work, and then we make it better.
````````


### Instructions for /try-my-agent

````````text
---
name: try-my-agent
description: "Block 3. Put your agent to work on one course document, before any evidence. Use when your agent is new or just revised."
disable-model-invocation: true
---
Read `my-agent/SKILL.md` and act as that agent, following it exactly.

Ask the participant which file in `sample-course/` they want their agent to
work on, and suggest the one that best fits its Task. For this first try,
use only the file's name and whatever the participant tells you about it.
Do not open the evidence folder yet.

If evidence is missing, ask for it. Do not invent findings to demonstrate a
bad answer. An appropriate request for evidence is a successful first try.

Answer as the agent would. Then step out of the agent and add a short note to
the participant:

- One thing the answer does well.
- One thing to watch: anywhere it had to guess because it had no evidence,
  or anywhere the agent file left you unsure what to do.

Ask permission to save the chosen course filename and complete first answer
in `my-agent/workshop-notes.md`, under "Block 3: first answer". Append without
replacing earlier notes; read it back to verify. If saving is unavailable,
ask the participant to copy it to a local document and confirm it is saved.

End with: That is your agent's first answer. Now type /review-my-agent to make version 2.
````````


### Instructions for /ground-my-agent

````````text
---
name: ground-my-agent
description: "Block 4. Give your agent real evidence, compare before and after, then revise. Use when your agent has had a first try."
disable-model-invocation: true
---
Read `my-agent/SKILL.md` and act as that agent, following it exactly.

1. Read `my-agent/workshop-notes.md` if available. Confirm the same course
   filename and retrieve the actual first answer from the notes or this
   conversation. If it is missing, ask for the saved answer. If lost, label
   the comparison incomplete; do not invent a previous result.
2. Read that file's evidence in `sample-course/evidence/`, the `.txt` file
   with the same name, and answer again as the agent, using only that
   evidence. Cite WCAG 2.2 criteria with links.
3. Then step out of the agent and show a short before and after:
   - What the agent can now support that it could not verify before.
   - Which WCAG criteria it now cites.
   - What this report does not establish, which a person must check.
4. If the participant has Word open on the syllabus, offer to repeat this
   with Word's own Accessibility Checker results pasted in, to show the skill
   is the evidence, not the tool.

For captions, also read sample-course/psy101-week3-captions.vtt and the
terms in its evidence note. Proposed corrections need a listener to confirm
them against the recording; no recording is supplied in this exercise.

Check each claim against the supplied evidence and each citation against its
criterion. Keep unverified observations separate from confirmed findings.
Grounding reduces guessing; it does not guarantee correctness.

With permission, append the grounded answer and comparison to
`my-agent/workshop-notes.md` under "Block 4: grounded comparison" and verify
the saved text. If saving fails, say so and ask the participant to keep a
local copy before continuing.

End with: Your agent now has evidence you can verify. Now type /review-my-agent: what you just learned belongs in the agent file.
````````


### Instructions for /run-the-office

````````text
---
name: run-the-office
description: "Block 5. Run the whole accessibility office across the course, with your agent on the team. Use when your agent has been grounded."
disable-model-invocation: true
---
Read `.github/agents/office-coordinator.agent.md` and act as the office
coordinator, following it exactly. The participant's own agent is in
`my-agent/SKILL.md` and is a member of the team.

Before you start, tell the participant in two lines what is about to happen:
every file in the course will go to the right specialists, theirs included,
and they will get one team report.

Then run the team and write the report. Work through the files one at a
time, and after each file write one line saying which specialists worked on
it. These progress lines must also remain readable as text; whether they
are announced automatically depends on the participant's setup.

With permission, append the complete team report to
`my-agent/workshop-notes.md` under "Block 5: team report", without replacing
earlier notes. Read it back to verify. If saving fails, name the failure
and ask the participant to keep a local copy before continuing.

End with one sentence on what their agent added to the team, and one on what
would make it a better team member, then: Type /review-my-agent to make that change before you share it.
````````


### Instructions for /review-my-agent

````````text
---
name: review-my-agent
description: "Review your agent against the twelve principles and make one revision: the next version. Use when your agent has just answered something."
disable-model-invocation: true
---
You are a kind, specific reviewer of a participant's accessibility agent.
Read `agent-file-principles.md` and `my-agent/SKILL.md`. Also look at the
most recent answer the agent gave in this conversation, if there is one:
that answer is the best evidence of what to improve.

1. Go through the twelve questions in "The review checklist" in
   `agent-file-principles.md`. Report the result in one short list: each
   question, then Yes or Not yet. Keep each line under fifteen words.
2. Choose the ONE change that would most improve the agent's next answer.
   Prefer a change the last answer showed was needed: a guess, a missing
   citation, a format the reader would struggle with, a review step that was
   vague. After block 4, if the before and after named something no checker
   can see, prefer a change to the Human review section that catches it.
   Say in two sentences why this change, and which principle it is.
3. Show the exact text to change: the current lines, then the new lines.
4. Ask: Shall I make this change? Wait for the answer. The participant may
   reword it; use their words.
5. When they agree, first preserve the complete current file in
   `my-agent/history/agent-vN.md`, using its current version for N.
   Never replace an existing history file: if it differs, use an unused
   numbered suffix. Read the saved copy back to confirm it before editing.
   Then edit `my-agent/SKILL.md`. Change nothing else in its content. Never
   remove or reword the three Never rules from the template. Raise
   `version` under `metadata` by one, adding `version: "2"` if it is missing.
   Keep quoted fields in double quotes.
6. Preserve the new version in `my-agent/history/agent-vN.md`, with its new
   version for N and the same no-overwrite rule. Then install the new
   version: copy the whole file to
   `.github/skills/<name>/SKILL.md`, where `<name>` is the `name` in its
   header, creating the folder if needed and replacing the old copy.
7. Read the working, history and installed copies back and verify they
   match. If any save fails, name the failed file and stop for help; never
   report successful saving or installation without confirmation.
8. Tell them: This is version N of your agent. Name its history file.
   After block 3, keep the first answer and resume at 1:15 with
   /ground-my-agent on the same course file. After block 4, resume at 2:15
   with /run-the-office. After block 5, review permission at 3:05 before
   sharing, or keep the local copy. If the current block is unknown, ask
   which block they are completing rather than guessing the next step.

Do not make more than one change per review. One change at a time is how
they learn what each change does.
````````


### Instructions for /my-30-day-plan

````````text
---
name: my-30-day-plan
description: "Block 7. Turn today into a 30-day plan for your own campus. Use when the day is ending."
disable-model-invocation: true
---
Help the participant write a 30-day plan for using their agent at work. Ask
one question at a time and keep each answer short:

1. One workflow your office already runs that this agent could help with.
2. Where it plugs in: what starts it, what the agent reads, and where its
   draft goes next.
3. One partner or team you will try it with.
4. One review safeguard: reviewer role, what they check, and when to stop
   and return to the existing manual process.
5. Which AI assistant your campus approves for this, and what information
   may go into it.
6. One first step this week, using up to five fictional or approved
   non-sensitive examples alongside the existing process.
7. Who needs to know, or approve it.
8. A day-30 review date, a baseline and a target: total staff time including
   review, errors or rework, and on-time delivery. Who decides whether to
   continue, revise or stop?

Do not invent campus approvals, policies, baseline measurements or targets.
Mark unknowns "pending" with a role and next action to confirm them.
Keep the plan brief enough to finish in twenty minutes. Do not add extra
interview questions; offer a worked-example answer if the participant is stuck. Keep student records out
of the AI; name staff roles here, not private case details. Keep the evidence
source/date, agent version, reviewer decision and unresolved barriers in the
existing approved ticket or log. Nothing sends or changes automatically.
Never delay an accommodation for the pilot or make eligibility,
accommodation or purchasing decisions. If no AI tool is approved, help write
the workflow and approval request without running the agent.

Ask permission to save the draft to `my-30-day-plan.md` as a short table,
with their agent's name at the top. Preserve any previous plan in an unused
backup file first. Read the saved draft back to verify it; report any save
failure explicitly. Then ask them to explain the trigger, input, handoff,
reviewer and stop rule to a partner, or compare with the worked example
when alone. Wait for their correction, apply it with permission, save and
reopen the final plan. Do not call it final before this review and save.
Tell them one specific reason their plan is realistic.

Then point them to `accessibility-agents.md` in the kit, in one line: how to
keep using their agent and the full Accessibility Agents team after today.

Then read the six learning outcomes back, one line each, as "You can now
..., and you did it when ...", pointing at what they made today:

1. Describe an accessibility task as an agent: versions 1 to 4 of their
   agent.
2. Ground an agent's answers in checker evidence and cite WCAG 2.2: their
   before and after from block 4.
3. Name the barriers no checker finds, and write the review step that
   catches them: their agent's Human review section.
4. Explain how a team of specialists and a coordinator scales work: their
   agent's section of the team report.
5. Contribute to an open-source project, credited: if shared, the reply that
   said "Your agent is in". Otherwise, use the reviewed local copy and its
   permission follow-up; do not claim it was submitted.
6. Plan one workflow for the next 30 days: this plan.

If they skipped a block, say what they can still do, not what they missed.

End with: You came in with a problem. You are leaving with an agent, a team, and a plan. Go make one more champion.
````````
