---
title: "Accessibility Agents, after today"
lang: en
author: "Jeff Bishop, University of Arizona, IT Accessibility Consultant"
description: "What Accessibility Agents is, how to get it, and how to use it with your own agent after the AHG 2026 workshop."
---

# Accessibility Agents, after today

Accessibility Agents is the open-source project your agent joins at the end
of the day. It is a team of 113 accessibility skills, written in the same
format as yours, from Community Access:
github.com/Community-Access/accessibility-agents.

The office team you ran this afternoon is a small version of it. The full
project reviews web pages, Word, Excel, PowerPoint, PDF and ePub files,
Markdown, Python and desktop apps, NVDA add-ons and GitHub work, and it
cites WCAG 2.2 for every finding.

## How it is organized

You talk to six entry points. Each one calls the specialists it needs, so
you never have to know all 113.

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

This kit carries all 113 Accessibility Agents skills, in `.github/skills`,
with the project's MIT licence in `accessibility-agents-LICENSE.txt`.
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
3. Wait for the setup to finish: it installs the project, its scanners and
   a browser for the web scans, then copies the skills to where Copilot
   reads them. If VS Code asks whether to start the MCP server named
   accessibility-agents, choose to start it: that is the scanners.
4. Open Copilot Chat with Control+Alt+I and ask for an entry point by
   name, as above. The scanners run for you.

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

The full local install can run scanners on your laptop after their optional
dependencies are set up. Review hooks work only in apps that support them.
Each line is one way to install it.

| For | Run |
|---|---|
| VS Code with Copilot | Turn on the `chat.plugins.enabled` setting, then run Chat: Install Plugin from Source with `https://github.com/Community-Access/accessibility-agents` |
| GitHub Copilot on the command line | `copilot plugin marketplace add Community-Access/accessibility-agents`, then `copilot plugin install accessibility-agents@community-access` |
| Claude Code | `/plugin marketplace add Community-Access/accessibility-agents`, then `/plugin install accessibility-agents@community-access` |
| Codex | `codex plugin marketplace add Community-Access/accessibility-agents`, then `codex plugin add accessibility-agents@community-access` |
| Gemini CLI | `gemini extensions install https://github.com/Community-Access/accessibility-agents` |
| Every AI tool on the laptop | In a copy of the repository: `npm install`, then `npm run setup` |

The Codex plugin install supplies skills and server tools, but not the review
hook. To set up the hook for Codex, use `npm install` and `npm run setup` in
a copy of the repository.

Step-by-step setup for each app, written for people new to all of this, is
at community-access.org/start.html. The VS Code extension in the repository
is retired; use one of the ways above instead.

### In ChatGPT, Claude or another assistant in a browser

On letitglow.app/ahg/assistant, under "Accessibility Agents in any
assistant", copy the text for the entry point you want and paste it as your
first message. Each text carries the entry point and the specialists it
calls. Then give it your checker's results.
For the workshop, you do not need a ChatGPT or Claude plugin listing or an
external connector: the browser path works with these prepared texts.

### On the web, at letitglow.app/accessibility-agents

The Accessibility Agents page on GLOW works in any browser, with nothing to
install.

- Check something now, with no AI and no account: color contrast (WCAG and
  APCA), reading level, the headings, links and form labels in some HTML, and
  the guidelines for a component such as a modal or tabs.
- Ask a question with your own AI. Choose OpenAI, Google Gemini, Claude or
  OpenRouter, paste your key (or sign in with OpenRouter), and choose Show my
  models to pick a model. Your key stays in that browser tab and is gone when
  you close it. Gemini and OpenRouter both have free models.
- Review a document. Choose a Word, Excel, PowerPoint, PDF, ePub, Markdown or
  HTML file. The Accessibility Agents scanner checks the original file, then
  your AI reviews it as the matching specialist, such as the Word specialist
  for a .docx. The file is deleted as soon as it is scanned.
- Get alt text for an image. Choose a PNG, JPEG, GIF or WebP image, and the
  alt text specialist writes its alt text, a long description when it needs
  one, and any text in the image. Your AI must be one that can see images;
  most current models can.
- Get alt text for every picture in a document. After choosing a Word,
  PowerPoint, Excel, PDF or ePub file, choose "Write alt text for every
  image". Your AI drafts each one, you check and edit them on the page, and
  for a Word or PowerPoint file "Download the file with this alt text" gives
  you the file back with the alt text in place.

The answers come from your own AI, so they are a first draft: a person still
reviews everything an agent writes.

### Connect your assistant to the Accessibility Agents server

Accessibility Agents runs a public server at
[GLOW accessibility server (letitglow.app/a11y/mcp)](https://letitglow.app/a11y/mcp). It offers twelve tools: eight checks for
colors, text, HTML and component guidelines, plus document scanning,
specialist instructions, picture extraction and alt-text editing. It can scan
Word, Excel, PowerPoint, PDF, ePub, Markdown and HTML files up to 20 MB. It
can also show pictures from a document and, for Word, PowerPoint, Excel and
ePub, return a copy with alt text added.

Send the file contents, or give the assistant a public sharing link. A link
must let anyone with the link view the file; only use files you are allowed
to share that way. The server temporarily stores a copy while it works, then
deletes it before answering. A file with alt text added is available through
its download link for one hour. The server cannot open files on your computer
unless you send them.

- ChatGPT, on a paid plan: Settings, Apps and Connectors, Advanced settings,
  turn on Developer mode, then Create a connector with that address and no
  authentication. On a campus plan, an administrator may have to allow it.
- Claude: Settings, Connectors, Add custom connector, with that address.

This is optional on the day. A free account and the pasted texts are enough
for every workshop activity. Public directory listings are separate from
these prepared texts and are not needed for class. Step-by-step instructions
for each assistant are on letitglow.app/accessibility-agents, under "Connect
your AI assistant".

### Where Accessibility Agents is available, as of 7 November 2026

Each row is one place you might use it, whether it works there today, and how.

| Where | Available now | How |
|---|---|---|
| VS Code, on a computer or at vscode.dev | Yes, all 113 skills | Already in this kit, or copy the `skills` folders into `.github/skills` |
| GitHub Codespaces | Yes, with the scanners | codespaces.new/Community-Access/accessibility-agents |
| GitHub Copilot CLI, Claude Code, Gemini CLI | Yes, with scanners after optional setup and supported review hooks | The install lines above |
| Codex | Yes, with skills and server tools; the plugin install does not include review hooks | Use `npm run setup` in a local repository copy to set up the hook |
| ChatGPT, on a free or paid account | Yes, by pasting | The texts on letitglow.app/ahg/assistant, as above |
| Any browser, with your own AI key | Yes | letitglow.app/accessibility-agents: checks, questions, document review, and alt text for an image or every picture in a document |
| ChatGPT or Claude, with the server connected | Yes, on plans that allow custom connectors | Connect the [GLOW accessibility server (letitglow.app/a11y/mcp)](https://letitglow.app/a11y/mcp) for twelve tools, including checks, document scans and alt-text editing on files you send |
| ChatGPT's app directory | Not listed; not needed for class | The browser path uses prepared texts; a custom connector is a separate option |
| Claude's plugin directory | Full plugin refused by directory policy; skills-only follow-up pending as of 6 November 2026 | Not needed for class: use the prepared texts or configure the separate custom connector |
| Claude, Gemini, Copilot on github.com, a campus assistant | Yes, by pasting | The same texts |

Sign in to your campus-approved assistant before you start. Free accounts
have usage and message-length limits that can change. Save your latest agent
after each revision. If a limit interrupts you, ask a helper to continue
with a written example or another approved assistant.

On the web and on a phone, use the prepared texts on
letitglow.app/ahg/assistant. A ChatGPT app-directory listing is not required
for the workshop. A custom connector is a separate, optional way to use the
hosted server. If a skill needs a scanner, it asks you for your checker's
results instead.

## Using it with your own agent

- Keep your agent beside the others: put it in `.github/skills/<name>/`, next
  to the Accessibility Agents folders. It is the same format, so it works the
  same way.
- Revise it the way you did today: try it, read where it guessed, change one
  thing. The principles are in `agent-file-principles.md` in this kit, and
  `write-your-own-agent.md` walks through writing a new one from a blank
  file.
- Your shared agent is in the AHG 2026 collection, and goes into
  Accessibility Agents in `community/ahg-2026/` with your name on it.

## Getting help, and helping

- Questions about the workshop: jeffbis@arizona.edu.
- A rule an agent gets wrong, or a pattern it should catch: open an issue on
  github.com/Community-Access/accessibility-agents.
- The two rules still apply: nothing private goes into any AI, and a person
  reviews everything an agent writes.

## Thanks

This workshop is by Jeff Bishop, [University of Arizona](https://accessibility.arizona.edu), IT Accessibility
Consultant, in collaboration with [Blind Information Technology Solutions (BITS)](https://www.bits-acb.org)
and [Techopolis](https://www.techopolis.app). Special thanks to Taylor Arndt, who helped dream up
and build Accessibility Agents.

## Sources

Checked on 7 November 2026.

- [Accessibility Agents README](https://github.com/Community-Access/accessibility-agents#readme):
  the six entry points and the install line for each tool. The kit carries
  the skills from the commit named in `accessibility-agents-skills.json`.
- [VS Code: agent plugins](https://code.visualstudio.com/docs/copilot/customization/agent-plugins):
  installing a plugin from a repository, and the `chat.plugins.enabled`
  setting it needs.
- [GitHub Docs: finding and installing Copilot CLI plugins](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-finding-installing):
  the `copilot plugin marketplace add` and `copilot plugin install`
  commands.
- [VS Code: use Agent Skills](https://code.visualstudio.com/docs/copilot/customization/agent-skills):
  why copying the skills into `.github/skills` is all an install needs.
- [GitHub Docs: Codespaces billing](https://docs.github.com/en/billing/concepts/product-billing/github-codespaces):
  the free monthly hours for a personal account.
