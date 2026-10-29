---
title: "What makes a good agent file"
lang: en
author: "Jeff Bishop, BITS"
description: "The principles of a good accessibility agent file, and the checklist /review-my-agent uses, from the Agent Skills specification and the Accessibility Agents project."
---

# What makes a good agent file

An agent is a set of plain-English instructions in one file, `SKILL.md`.
This card is what every agent in the kit follows, and what `/review-my-agent`
checks yours against. Read it once in block 2. Come back to it every time
you revise.

It follows the open Agent Skills format, the same one Accessibility Agents,
GitHub Copilot, VS Code, Claude Code, Codex and Gemini CLI read. Any other
assistant, ChatGPT in a browser included, takes the same file pasted in as
its instructions. The sources are at the end.

## The shape of the file

Every agent file has two parts: a short header between two lines of three
dashes, then the instructions.

The header holds these fields.

| Field | Needed | What it is |
|---|---|---|
| `name` | Yes | A short name: lowercase letters, numbers and hyphens, at most 64 characters, like `alternate-format-planner`. When the agent is installed, its folder has the same name |
| `description` | Yes | What the agent does and when to use it, in one or two sentences. At most 1,024 characters; aim for under 200 |
| `license` | No | How others may reuse it. Every workshop agent is `MIT` |
| `metadata` | No | Anything else, as short labels. The workshop uses `title`, `author`, `domain` and `output` |

The instructions are headings, in this order: Role, Task, Trusted guidance,
Output format, Example, Human review, Never. Every heading except Example
is required to share your agent.

## The twelve principles

### 1. One job

An agent that does one thing well beats one that does five things badly.
If your Task has the word "and" in it twice, you probably have two agents.

### 2. A name that says what it is

Lowercase, hyphens, no spaces: `faculty-coach`, not `My Agent v2`. When you
install the agent, its folder must have exactly this name, or tools will
not find it.

### 3. A description that says when to use it

The description is the first thing an assistant reads, and often the only
thing, when it decides whether to use your agent. VS Code reads only the
name and description of every skill up front; it reads the rest of the
file when the skill is used, and a file in `references` only when the
instructions point to it. Say what the agent does,
then start a second sentence with "Use when". For example: "Plans alternate
formats for a course document from a checker's report. Use when a student
needs a course document in large print, audio or braille."

### 4. A role with a person in it

Say who the agent is, and who it works for: "You are an alternate format
planner in a disability resource center. You work for the specialist who
handles accommodation requests." The person it works for is who it writes
for.

### 5. A task with an input and an output

Say what the agent is given and what it gives back: "Given a checker's report
and the formats a student needs, produce a plan." An agent that does not
know its input will guess at it.

### 6. Trusted guidance, named and linked

Name the sources it must use and cite, with links: WCAG 2.2 criteria, your
institution's policy, a style guide. Add the rule every workshop agent has:
work only from the evidence given, and say so when something is not in it.

### 7. An output format shaped for the reader

Describe the shape of the answer for the busy person who reads it: a
numbered list most urgent first, a short email, a table with a status
column. The best format is the one your reader already uses.

### 8. One example of a good answer

Show one short example of what good looks like. An example teaches the
shape, the tone and the length faster than any description. Keep it short,
and use the fictional course, never a real student.

### 9. Human review, with a name on it

Say who checks the agent's work before anything goes out, and what they
check. End every answer with a "Before you send this" checklist for that
person. If nobody is named, nobody reviewed it.

### 10. Never: the lines it does not cross

Every workshop agent keeps these three:

- Never ask for, or use, student names, records, accommodation details or
  health information.
- Never say a document is "compliant" or "accessible". Say what was checked,
  what was found, and what a person still needs to check.
- Never invent a finding that is not in the evidence.

Add your own, such as "Never promise a date".

### 11. Short enough to read

Keep the file short enough to read in five minutes. The Agent Skills format
asks for under 500 lines; Accessibility Agents keeps every agent under 6 KB,
about two pages. Long reference material goes in a separate file, in a
`references` folder beside `SKILL.md`, which the agent opens only when it
needs it.

### 12. Tested, and revised one change at a time

Nobody writes a good agent in one go. Try it on a real input, read where it
guessed or went wrong, change one thing, and try again. Each change is a new
version. Today you make at least three.

## The review checklist

`/review-my-agent`, and the same step on the browser path, asks these
questions of your agent. Every "no" is a revision you could make.

1. Does it do one job?
2. Is the name lowercase, with hyphens, and under 64 characters?
3. Does the description say what it does, and start a sentence with "Use when"?
4. Does the Role say who it works for?
5. Does the Task name its input and its output?
6. Does Trusted guidance name and link its sources, and say to work only from evidence?
7. Is the Output format shaped for the person who reads it?
8. Is there one short example of a good answer?
9. Does Human review name who checks, and end with a checklist?
10. Are the three Never rules still there, word for word?
11. Is it short enough to read in five minutes?
12. After the last try, is there one change that would have made the answer better?

## Where an agent file lives

The same file works everywhere; only the place changes.

| Where | Put it here | Then |
|---|---|---|
| VS Code, on a computer or at vscode.dev | `.github/skills/<name>/SKILL.md` in the open folder | Type `/<name>` in Copilot Chat. `/install-my-agent` does this for you |
| GitHub Copilot CLI, Codex, Gemini CLI | `.agents/skills/<name>/SKILL.md`, or `~/.agents/skills/<name>/SKILL.md` for every project | It appears by name |
| Claude Code | `.claude/skills/<name>/SKILL.md`, or `~/.claude/skills/<name>/SKILL.md` for every project | It appears by name |
| ChatGPT, Claude, Gemini, or a campus assistant in a browser | Paste the whole file as your first message, or into a project's or custom assistant's instructions | Ask your question in the same conversation |
| The open-source collection | Share it at letitglow.app/ahg/share | It goes into Accessibility Agents with your name on it |

Commands you start yourself, rather than ones the assistant should choose on
its own, add `disable-model-invocation: true` to the header. The kit's
commands, such as `/ready-check`, do. VS Code and Claude Code read that
field; it is not part of the open format, so other tools may ignore it.
Never combine it with `user-invocable: false`: VS Code then neither offers
the skill as a command nor loads it on its own, so it never runs.
The Accessibility Agents reference skills in this kit do combine them, on
purpose: nobody runs a reference on its own, and its entry points open the
file by path.

## Sources

Checked on 29 October 2026.

- [Agent Skills specification](https://agentskills.io/specification): the
  file format, the header fields and their limits (`name` at most 64
  characters and matching its folder, `description` at most 1,024), and the
  advice to keep `SKILL.md` under 500 lines and put the rest in
  `references`.
- [VS Code: use Agent Skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills):
  the folders VS Code searches (`.github/skills`, `.claude/skills`,
  `.agents/skills`, and `~/.copilot/skills` for every project), how a skill
  becomes a `/` command, `user-invocable` and `disable-model-invocation`,
  and the three steps in which a skill is loaded.
- [GitHub Docs: about agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills):
  where GitHub Copilot and the Copilot CLI find skills.
- [Claude Code: skills](https://code.claude.com/docs/en/skills),
  [Codex: build skills](https://learn.chatgpt.com/docs/build-skills) and
  [Gemini CLI: skills](https://geminicli.com/docs/cli/skills/): where each
  of those tools finds skills.
- [Accessibility Agents: Agent Skills standard](https://github.com/Community-Access/accessibility-agents/blob/main/docs/standards/agent-skills.md):
  how the project applies the format, its size limits, and where each tool
  finds skills.
- [Accessibility Agents: citation policy](https://github.com/Community-Access/accessibility-agents/blob/main/docs/standards/citation-policy.md):
  why every finding cites a source.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/), a W3C Recommendation (first
  published 5 October 2023, current edition 12 December 2024), and
  [Understanding WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/):
  the standard every workshop agent cites. [WCAG 3.0](https://www.w3.org/TR/wcag-3.0/)
  is a Working Draft, not a standard; no agent should cite it as one.
- [ADA Title II web rule](https://www.ada.gov/resources/2024-03-08-web-rule/):
  public colleges and universities must meet WCAG 2.1 AA. An interim final
  rule of 20 April 2026 moved the dates to 26 April 2027 for entities of
  50,000 people or more and 26 April 2028 for smaller ones.
