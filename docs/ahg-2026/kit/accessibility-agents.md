---
title: "Accessibility Agents, after today"
lang: en
author: "Jeff Bishop, BITS"
description: "What Accessibility Agents is, how to get it, and how to use it with your own agent after the AHG 2026 workshop."
---

# Accessibility Agents, after today

Accessibility Agents is the open-source project your agent joins at the end
of the day. It is a team of 108 accessibility agents, written in the same
format as yours, from Community Access:
github.com/Community-Access/accessibility-agents.

The office team you ran this afternoon is a small version of it. The full
project reviews web pages, Word, Excel, PowerPoint, PDF and ePub files,
Markdown, and GitHub work, and it cites WCAG 2.2 for every finding.

## How it is organized

You talk to six entry points. Each one calls the specialists it needs, so
you never have to know all 108.

| You are working on | Ask for |
|---|---|
| A web page, a form, a template or a component | `accessibility-lead` |
| A whole site or app, not one change | `web-accessibility-wizard` |
| Word, Excel, PowerPoint, PDF or ePub files | `document-accessibility-wizard` |
| Markdown documentation | `markdown-a11y-assistant` |
| Python, desktop apps, NVDA add-ons, accessibility tools | `developer-hub` |
| GitHub issues, pull requests, releases and projects | `github-hub` |

## Getting it

There are three ways, from no effort to the full version.

### Already in this kit

This kit carries all 108 Accessibility Agents skills, in `.github/skills`.
Open the kit in VS Code, on a computer or at vscode.dev, start a new chat,
and ask for one of the six entry points by name, for example:
use document-accessibility-wizard to review psy101-syllabus.docx, using
sample-course/evidence/psy101-syllabus.txt.

The kit cannot carry the project's scanner tools, scripts or hooks, so a few
skills work differently here: `accessibility-agents-in-the-kit.md` lists
every one and what it does instead. In short, give them your checker's
results, the way you gave your own agent evidence today.

### The full version, in your browser, with one click

GitHub Codespaces opens the whole project, scanners included, in VS Code in
your browser, using the GitHub account you made for today.

1. Go to codespaces.new/Community-Access/accessibility-agents and sign in.
2. Choose Create codespace. The first start takes a few minutes; later
   starts are quicker.
3. When VS Code opens, open Copilot Chat with Control+Alt+I and ask for an
   entry point by name, as above. The scanners run for you.

Personal GitHub accounts include a monthly allowance of free Codespaces
time. Stop the codespace when you finish, from github.com/codespaces, so it
does not use your allowance while idle.

### In your own projects in VS Code, with nothing to install

VS Code uses any skill in the `.github/skills` folder of the folder you have
open. This is how your own agent became `/<name>` today, with
`/install-my-agent`.

1. On github.com/Community-Access/accessibility-agents, choose Code, then
   Download ZIP, and unzip it.
2. In the project folder you work in, make a `.github/skills` folder if it
   does not have one.
3. Copy every folder from the unzipped `skills` folder into `.github/skills`.
   Copy all of them: the six entry points call the others by name.
4. Start a new chat in Copilot Chat and ask for one of the six entry points.

### With your IT team, on a laptop

The full install adds the scanners and the review hooks on your own laptop.
Each line is one way to install it.

| For | Run |
|---|---|
| Every AI tool on the laptop | `npm install`, then `node scripts/install.mjs`, in a copy of the repository |
| GitHub Copilot on the command line | `copilot plugin install accessibility-agents` |
| Claude Code | `/plugin marketplace add Community-Access/accessibility-agents` |

The VS Code extension in the repository is retired; use one of the ways
above instead.

### In ChatGPT, Claude or another assistant in a browser

On letitglow.app/ahg/assistant, under "Accessibility Agents in any
assistant", copy the text for the entry point you want and paste it as your
first message. Each text carries the entry point and the specialists it
calls. Then give it your checker's results.

## Using it with your own agent

- Keep your agent beside the others: put it in `.github/skills/<name>/`, next
  to the Accessibility Agents folders. It is the same format, so it works the
  same way.
- Revise it the way you did today: try it, read where it guessed, change one
  thing. The principles are in `agent-file-principles.md` in this kit.
- Your shared agent is in the AHG 2026 collection, and goes into
  Accessibility Agents in `community/ahg-2026/` with your name on it.

## Getting help, and helping

- Questions about the workshop: support@community-access.org.
- A rule an agent gets wrong, or a pattern it should catch: open an issue on
  github.com/Community-Access/accessibility-agents.
- The two rules still apply: nothing private goes into any AI, and a person
  reviews everything an agent writes.
