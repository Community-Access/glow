---
title: "Welcome to the AHG 2026 agent kit"
lang: en
author: "Jeff Bishop, BITS"
description: "Welcome page for the AHG 2026 agent kit."
---

# Welcome to the AHG 2026 agent kit

You are in the right place. This page opens by itself when you open the kit
in VS Code. Nothing here needs code, and nothing here can break.

## Three paths into the same day

Every path gives you the same agent, the same team report and the same
share on GitHub. letitglow.app/ahg/paths compares them.

- In a browser: no kit needed. Open letitglow.app/ahg/assistant, copy each
  block's text, and paste it into ChatGPT, Copilot on github.com, Claude,
  Gemini or your campus assistant. The same texts are in this kit, in
  `any-assistant/`.
- In VS Code on your computer: you are probably reading this there. Each
  block is one command in Copilot Chat.
- In VS Code for the Web: the same, at vscode.dev in Chrome or Edge, with
  this folder opened from your laptop.

## Start here, in VS Code

1. Open Copilot Chat: Control+Alt+I on Windows, or Control+Command+I on a
   Mac.
2. Type /ready-check and press Enter. Copilot checks five things and tells
   you that you are ready.

If a banner says Restricted Mode, choose Manage, then Trust first. It is the
workshop kit, and Copilot cannot work on its files until you trust it.

Every block of the day has its own command, listed below, and its own step
card in the step-cards folder.

## The day, one command per block

Each command is typed into Copilot Chat. On the browser path, the same
block is one text on letitglow.app/ahg/assistant. The step card for each
block has every key and every expected result in words.

| Block | Time | Command | What you get |
|---|---|---|---|
| 1. Why we are here | 10:30 | /ready-check | A ready laptop |
| 2. Design your agent | 10:50 | /design-my-agent | Your own agent, in `my-agent/SKILL.md`: version 1 |
| 3. Your agent at work | 11:40 | /try-my-agent, then /review-my-agent | Its first answer on a course document, and version 2 |
| 4. Ground it | 1:15 | /ground-my-agent, then /review-my-agent | Cited answers from real evidence, and version 3 |
| 5. Build the office | 2:15 | /run-the-office, then /review-my-agent | Your agent in a team, across the whole course, and version 4 |
| 6. Share it | 3:05 | letitglow.app/ahg/share | Your best version in the collection, in your name |
| 7. Take it home | 3:40 | /my-30-day-plan | A 30-day plan for your campus |

## What is in this folder

This list follows the folders in the Explorer, top to bottom.

| Folder or file | What it is |
|---|---|
| `.github/` | The commands above, as agent skills in `skills/`, beside all 113 Accessibility Agents skills; the office coordinator in `agents/`; and the workshop's rules for Copilot. You do not need to open it |
| `.vscode/` | Settings for larger text and screen readers. You do not need to open it |
| `any-assistant/` | One text per block for the browser path, to paste into any AI assistant; the review text; and four Accessibility Agents texts, `aa-*.txt` |
| `examples/` | Finished work for every step. Maria, Jordan and Sam's stories, and six ready-made agents in `examples/agents/` |
| `my-agent/SKILL.md` | Your agent. Seven headings: Role, Task, Trusted guidance, Output format, Example, Human review, Never |
| `office-team/` | The accessibility office: eight specialists your agent joins this afternoon |
| `sample-course/` | PSY 101, the course everyone works on, with barriers planted on purpose, and `evidence/` with each file's checker report |
| `step-cards/` | One card per block, as Markdown and as large print Word files |
| `share-my-agent.html` | The offline copy of the share page |
| `ahg-2026.code-profile` | The AHG 2026 VS Code profile, if you need to import it again |
| `accessibility-agents.md` | Accessibility Agents after today: the six entry points, and how to keep using it |
| `accessibility-agents-in-the-kit.md` | Which Accessibility Agents skills work fully in this kit, and what the rest do instead |
| `accessibility-agents-LICENSE.txt` | Accessibility Agents' MIT licence, which travels with its skills |
| `agent-file-principles.md` | What makes a good agent file, and the twelve review questions /review-my-agent uses |

## You cannot fall behind

Every step has a finished version in `examples/`. If anything goes wrong,
start from one of the six ready-made agents in `examples/agents/`, put your
name on it, and carry on. That is still your agent, and it still goes into
the open-source project with your name on it. If VS Code gives you trouble,
switch to the browser path and carry on from the same block.

## Keys worth knowing

These work in every part of VS Code, on a computer and at vscode.dev.

| To | Windows | Mac |
|---|---|---|
| Open Copilot Chat | Control+Alt+I | Control+Command+I |
| Read Copilot's last answer as plain text | Alt+F2 | Option+F2 |
| Open any file by name | Control+P | Command+P |
| Find any command | Control+Shift+P | Command+Shift+P |
| Move between parts of the window | F6 | F6 |
| Accessibility help for where you are | Alt+F1 | Option+F1 |

## The two rules

1. Never paste anything private into any AI: student records, health or
   disability information, or anyone's name. Use the sample course.
2. Every agent ends with a person checking its work.

Help, before or after the day: support@community-access.org.
