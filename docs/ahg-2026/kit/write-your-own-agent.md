---
title: "Write your own accessibility agent: a tutorial"
lang: en
author: "Jeff Bishop, BITS"
description: "A start-to-finish tutorial for writing, testing, grounding and sharing an accessibility agent, in any AI assistant, after the AHG 2026 workshop."
---

# Write your own accessibility agent: a tutorial

This tutorial takes you from a blank file to an agent you trust, on your
own, in any AI assistant. It does not need the workshop's commands, and it
does not need code. If you were at the workshop, it is the same method, slowed
down and written out, so you can do it again on Monday for a different job.

It takes about an hour the first time. Have this open in one window and your
AI assistant in another.

## How this tutorial works

There are eight steps. Each one has what to do, what good looks like, and a
check before you move on. One example runs all the way through: Dev, a media
services coordinator, writes an agent for lecture captions. The example uses
the sample course in this kit, so you can follow along with real files.
Dev is fictional, and the answers quoted are examples written for this
tutorial; your assistant's own answers will differ.

Each row is one step, what you do in it, and what you have at the end.

| Step | You do | You end with |
|---|---|---|
| 1 | Choose one job | One sentence: given what, produce what, for whom |
| 2 | Write the header | A name and a description that says when to use it |
| 3 | Write the six sections | Role, Task, Trusted guidance, Output format, Example, Human review |
| 4 | Keep the Never rules | The three lines every agent keeps |
| 5 | Try it, with no evidence | A first answer, and a list of where it guessed |
| 6 | Ground it | A second answer that cites evidence and WCAG 2.2 |
| 7 | Revise, one change at a time | Versions 2, 3 and 4 |
| 8 | Install it and share it | Your agent where you work, and in the open-source collection |

## Before you start

- Open `my-agent/SKILL.md` in this kit, or copy the template at the end of
  this tutorial into a new file named `SKILL.md`.
- Open `agent-file-principles.md` beside it. This tutorial refers to its
  twelve principles by number.
- Read the two rules again. Never paste anything private into any AI:
  student records, health or disability information, or anyone's name.
  Every agent ends with a named person checking its work.

## Step 1: choose one job

An agent is a set of plain-English instructions that tells an AI assistant
how to do one job, the way you would brief a new colleague. The single
biggest mistake is giving it two jobs.

Write one sentence in this shape:

> Given [what it is handed], produce [what it hands back], for [who reads
> it].

Then test the sentence:

- Does it have the word "and" in it twice? Then you have two agents
  (principle 1). Pick the one you would use most this month.
- Could you hand the input to a new colleague today? If the input is "the
  course", it is too big. If it is "a caption file and the course's list of
  names and terms", it is right.
- Do you know who reads the output? If you cannot name them, you cannot
  choose its format in step 3.

Dev's first try was: "Check captions and fix accessibility for all our
videos." That is three jobs and no reader. Dev's second try:

> Given a lecture's caption file and the course's list of names and terms,
> produce a correction request for our captioning vendor, for me to check
> and send.

### Step 1 check

You have one sentence with one input, one output and one reader.

## Step 2: write the header

The header is the few lines at the top of `SKILL.md`, between two lines of
three dashes. Two fields are needed: `name` and `description`. The rest is
optional.

```markdown
---
name: caption-correction-request
description: "Turns a lecture caption file and a course's names and terms into a correction request for the captioning vendor. Use when lecture captions have misheard names, terms or speakers."
license: MIT
metadata:
  title: "Caption Correction Request"
  author: "Dev Patel, Mesa Ridge State University"
  version: "1"
---
```

The name:

- Lowercase letters, numbers and hyphens, at most 64 characters, no spaces
  (principle 2). When you install the agent, its folder must have exactly
  this name, or the assistant skips it without telling you.

The description matters more than anything else in the header:

- An assistant reads only the name and description of every agent up front,
  and decides from those whether to use yours (principle 3). The rest of the
  file is read only when the agent is used.
- Say what it does in one sentence. Then start a second sentence with "Use
  when", naming the situation that calls for it.
- At most 1,024 characters. Aim for under 200.
- Keep the description and title inside double quotes, so a colon in your
  wording cannot break the header.

### Step 2 check

The name matches the folder you will put it in. The description has a "Use
when" sentence that a stranger could act on.

## Step 3: write the six sections

Under the header, write these headings, in this order. Each one answers one
question.

### Role: who is this agent, and who does it work for?

Name a role and a person (principle 4). The person it works for is who it
writes for.

> You are a caption quality assistant in a university media services
> office. You work for the media services coordinator, who sends correction
> requests to the captioning vendor.

### Task: what is it given, and what does it give back?

Copy your step 1 sentence, then add what "done" means (principle 5).

> Given a lecture's caption file (WebVTT or SRT) and the course's list of
> names and terms, produce a correction request: every caption that
> misspells or mishears a listed name or term, every caption that is missing
> a speaker change, and the time stamp of each.

### Trusted guidance: what must it use and cite?

Name your sources, with links, and add the rule every workshop agent has:
work only from the evidence given (principle 6).

> Cite by name and link:
>
> - [WCAG 2.2, 1.2.2 Captions (Prerecorded)](https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded.html)
> - [W3C WAI: captions and subtitles](https://www.w3.org/WAI/media/av/captions/)
> - Our captioning contract's accuracy clause
>
> Work only from the caption file and the list of names and terms. If
> something is not in them, say you cannot see it. Do not guess.

### Output format: what comes back, and in what shape?

Shape it for the person who reads it (principle 7). The best format is the
one your reader already uses. Dev's vendor takes a table.

> A short note to the vendor naming the course and lecture. Then a table:
> time stamp, what the caption says, what it should say, and why (name,
> term or speaker). Most serious first. Then a "Before you send this"
> checklist for the coordinator.

### Example: what does one good answer look like?

One short example teaches the shape, the tone and the length faster than
any description (principle 8). Use the fictional course, never a real
student.

> | Time | Caption says | Should say | Why |
> |---|---|---|---|
> | 00:00:04.500 | herman ebb in house | Hermann Ebbinghaus | Name on the course list |

### Human review: who checks it, and what do they check?

Name the person and what they check, and end every answer with a checklist
for them (principle 9). If nobody is named, nobody reviewed it.

> The media services coordinator checks every correction against the
> recording before sending, and checks anything the agent marked as not
> sure. End every answer with "Before you send this":
>
> - [ ] Each correction checked against the recording
> - [ ] Any caption marked "not sure" listened to again
> - [ ] Nothing in the request names a student

### Step 3 check

Every heading has at least one sentence of your own. The Example is under
ten lines. Human review names a role, not "someone".

## Step 4: keep the Never rules

End the file with a Never section. Every workshop agent keeps these three,
word for word, and you may add your own (principle 10).

```markdown
## Never

- Never ask for, or use, student names, records, accommodation details or
  health information.
- Never say a document is "compliant" or "accessible". Say what you checked,
  what you found, and what a person still needs to check.
- Never invent a finding that is not in the evidence.
```

Dev added one more: "Never change a caption's time stamps."

### Step 4 check

The three rules are there, unchanged. Your own rule is one line.

## Step 5: try it, with no evidence

Now see what the agent does when it has to guess. This first answer is
supposed to be weak; it shows you what to fix.

1. Start a new conversation in your assistant.
2. Paste the whole agent file as your first message. In VS Code with the
   agent installed (step 8), type `/` and its name instead.
3. Ask it to do its job, giving it only a file name. Dev asked: "Write the
   correction request for psy101-week3-captions.vtt."
4. Read the answer, and write down every place it guessed.

Dev's first answer apologised for not seeing the file, then listed "common
caption errors" from nowhere and called the captions "not ADA compliant".
Three problems, each a lesson: it had no evidence, it filled the gap with
generic advice, and it used a word its Never rules forbid.

Read the answer for these, every time:

- Did it guess at anything it was not given?
- Did it cite a source, with a link?
- Is the output in the shape you asked for?
- Does it end with the reviewer's checklist?
- Did it break a Never rule?

### Step 5 check

You have the first answer, and a written list of what was wrong with it.

## Step 6: ground it in evidence

Grounding means giving the agent the evidence it needs, so it stops
guessing. Evidence is a checker's report, the text of a document, or what
you tell it.

1. In the same conversation, give it the evidence. Dev pasted the caption
   file from `sample-course/psy101-week3-captions.vtt`, then the course's
   names and terms: Hermann Ebbinghaus, the nonsense syllables DAX, BOK and
   YAT, the spacing effect.
2. Ask the same question again.
3. Compare the two answers side by side.

Dev's grounded answer found "herman ebb in house" at 00:00:04.500 and
"docks and bach" at 00:00:09.000, cited 1.2.2 with its link, flagged the
question from the room at 00:00:21.500 as a speaker change with no label,
and ended with the checklist.

Some barriers no checker sees. Captions are the clearest case: no automated
tool judges whether "ebb in house" is right. That is why the evidence here
is the caption file and your list of terms, and why the reviewer listens to
the recording. For a Word file, a PDF or a web page, the evidence is a
checker's report: Word's, PowerPoint's or Acrobat's own Accessibility
Checker, Accessibility Insights, axe or GLOW. Paste its results.

### Step 6 check

The second answer cites at least one WCAG 2.2 criterion with a link, names
what it could not check, and guesses at nothing.

## Step 7: revise, one change at a time

Now improve the agent file, not the answer. Change one thing, try again,
and see what that one change did (principle 12).

1. Ask the twelve review questions in `agent-file-principles.md` of your
   agent. Every "not yet" is a revision you could make.
2. Choose the one change that would most improve the next answer. Prefer a
   change the last answer showed was needed.
3. Make that change in the file, raise `version` by one, and save it.
4. Try again, in a new conversation, with the same evidence.

Dev's three revisions:

Each row is one version, the one thing that changed, and why.

| Version | What changed | Why |
|---|---|---|
| 2 | Task now says "the course's list of names and terms is part of the input; ask for it if it is missing" | Version 1 never asked for the list |
| 3 | Output format adds a "not sure" column | Version 2 presented every guess as certain |
| 4 | Human review adds "listen again to every caption marked not sure" | Version 3's not-sure items needed a person, and nobody was told |

Ways agents commonly go wrong, and the one change that fixes each:

Each row is one thing an agent does wrong, and the one change that fixes it.

| It does this | Change this |
|---|---|
| Guesses when evidence is missing | Trusted guidance: "If the evidence is missing, ask for it. Do not guess" |
| Gives a lecture instead of a result | Output format: describe the exact shape, and shorten the Example |
| Cites WCAG with no links, or the wrong version | Trusted guidance: list the criteria by number, name and link |
| Says "compliant" | Check the Never rules are there, word for word |
| Does two jobs | Task: cut to one; make the second job its own agent |
| The review step is vague | Human review: name the role and what they check |
| Gets too long to read | Move reference material into a `references` folder (below) |

### When the file gets long

Keep `SKILL.md` short enough to read in five minutes (principle 11). The
Agent Skills format asks for under 500 lines. Long material, such as a
vendor's style guide or your office's procedure, goes in a `references`
folder beside `SKILL.md`. Point to it from the instructions, for example
"For the vendor's spelling rules, read references/vendor-style.md". The
assistant opens that file only when the instructions send it there.

### When to split one agent into two

Split it when the Task has grown a second job, when two readers need two
different formats, or when the Example no longer fits in ten lines. Dev
later wrote a second agent that drafts the note to the instructor about the
same captions: same evidence, different reader, different job.

### Step 7 check

You have at least three versions, each with one change you can name.

## Step 8: install it and share it

The same file works everywhere; only the place changes. Each row is one
tool, where the file goes, and how you use it.

| Tool | Put the file here | Then |
|---|---|---|
| VS Code with GitHub Copilot, on a computer or at vscode.dev | `.github/skills/<name>/SKILL.md` in the folder you open | Type `/` and the agent's name in Copilot Chat |
| GitHub Copilot CLI | `.github/skills/<name>/SKILL.md` in the project, or `~/.agents/skills/<name>/SKILL.md` for every project | It appears by name |
| Claude Code | `.claude/skills/<name>/SKILL.md`, or `~/.claude/skills/<name>/SKILL.md` for every project | It appears by name |
| Codex | `.agents/skills/<name>/SKILL.md`, or `~/.agents/skills/<name>/SKILL.md` | It appears by name |
| Gemini CLI | `.gemini/skills/<name>/SKILL.md`, or `.agents/skills/<name>/SKILL.md` | It appears by name |
| ChatGPT, Claude, Gemini, Copilot on github.com, or a campus assistant, in a browser | Paste the whole file as your first message, or into a project's or custom assistant's instructions | Ask in the same conversation |

In ChatGPT on the web and on a phone, a skill works only when it comes in a
plugin from ChatGPT's directory, so pasting is the way in for your own
agent. In the ChatGPT desktop app, standalone skills work too.

If the agent does not appear, check three things: the folder name matches
`name` exactly; the header starts and ends with three dashes; you started a
new chat after installing it.

To share it, open letitglow.app/ahg/share, choose your newest version, and
press the button. It goes into the AHG 2026 collection on GitHub, committed
in your name, and into the Accessibility Agents project with you credited.

### Step 8 check

The agent answers by name where you work, and you know where its newest
version is.

## Keeping it good

- Re-run it whenever a standard, a policy or your vendor's contract changes,
  and update Trusted guidance first.
- Keep a short changelog at the end of the file: version, date, the one
  change.
- When someone else's agent does part of your job better, use theirs and
  give credit. Accessibility Agents has 113 skills you can read and borrow
  from; `accessibility-agents.md` in this kit says how to get them.

## Practice

Three exercises, each with a model answer. Try each one before you read the
answer.

### Exercise 1: a description that says when

Rewrite this description so an assistant knows when to use it: "Helps with
PDFs."

Model answer: "Plans fixes for an untagged or scanned course PDF from
Acrobat's Accessibility Checker report. Use when a course PDF fails
Acrobat's check or cannot be read aloud."

### Exercise 2: one job, not two

This Task has two jobs. Split it: "Review the syllabus for accessibility and
write an email to the instructor."

Model answer: agent 1, "Given a checker's report on a syllabus, list each
barrier with its WCAG 2.2 criterion and fix." Agent 2, "Given that list,
write a short, kind note to the instructor teaching the one habit behind
most of it." The second is Jordan's faculty coach in `examples/`.

### Exercise 3: a review step with a name on it

This Human review is too vague. Fix it: "Someone should check this."

Model answer: "The alternate format specialist checks the converted text
against the original, page by page, before it goes to the student. End
every answer with a 'Before you send this' checklist."

## One-page checklist

Go down this list before you share an agent.

- [ ] One job: given what, produce what, for whom.
- [ ] `name`: lowercase, hyphens, at most 64 characters, matches the folder.
- [ ] `description`: what it does, then "Use when".
- [ ] Role names a role and who it works for.
- [ ] Task names the input and the output.
- [ ] Trusted guidance links its sources and says to work only from evidence.
- [ ] Output format is shaped for the reader.
- [ ] One short example of a good answer.
- [ ] Human review names who checks what, and ends with a checklist.
- [ ] The three Never rules, word for word.
- [ ] Short enough to read in five minutes; long material in `references`.
- [ ] Tried with no evidence, grounded, then revised one change at a time.

## The template

Copy this into a new file named `SKILL.md`, in a folder with the same name
as `name`.

```markdown
---
name: my-agent-name
description: "What this agent does, for whom, in one sentence. Use when: the situation that calls for it."
license: MIT
metadata:
  title: "My Agent Title"
  author: "Your Name, Your Institution"
  version: "1"
---
## Role

Who this agent is, and who it works for.

## Task

What it is given, and what it gives back. One job.

## Trusted guidance

The sources it must use and cite, by name and link:

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [Understanding WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/)
- Your own policy, style guide or procedure.

Work only from the evidence you are given. If something is not in the
evidence, say you cannot see it. Do not guess.

## Output format

What comes back, in what shape, for the person who reads it.

## Example

One short example of a good answer, using a fictional case.

## Human review

Who checks what before anything goes out. End every answer with a "Before
you send this" checklist for that person.

## Never

- Never ask for, or use, student names, records, accommodation details or
  health information.
- Never say a document is "compliant" or "accessible". Say what you checked,
  what you found, and what a person still needs to check.
- Never invent a finding that is not in the evidence.
```

## Sources

Checked on 29 October 2026.

- [Agent Skills specification](https://agentskills.io/specification): the
  file format, `name` (at most 64 characters, matching its folder),
  `description` (at most 1,024 characters), the advice to keep `SKILL.md`
  under 500 lines, and the `references` folder.
- [VS Code: use Agent Skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills):
  where VS Code finds skills, typing `/` to use one, and how a skill is
  loaded in three steps, name and description first.
- [GitHub Docs: about agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills),
  [Claude Code: skills](https://code.claude.com/docs/en/skills),
  [Codex: build skills](https://learn.chatgpt.com/docs/build-skills) and
  [Gemini CLI: skills](https://geminicli.com/docs/cli/skills/): where each
  tool finds skills, and where ChatGPT reads them.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and
  [Understanding 1.2.2 Captions (Prerecorded)](https://www.w3.org/WAI/WCAG22/Understanding/captions-prerecorded.html).
- [W3C WAI: captions and subtitles](https://www.w3.org/WAI/media/av/captions/).
- `agent-file-principles.md` in this kit: the twelve principles and the
  review questions this tutorial follows.
