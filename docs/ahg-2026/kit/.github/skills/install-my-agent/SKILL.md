---
name: install-my-agent
description: "Install your agent in VS Code, so it becomes its own command, exactly as Accessibility Agents installs its skills. Use when your agent has a name."
disable-model-invocation: true
---
Install the participant's agent as a skill in this folder.

1. Read `my-agent/SKILL.md`. Check its `name`: lowercase letters, numbers
   and hyphens, at most 64 characters, and not `my-agent-name`. If it is
   not, suggest a name from its title and ask before changing it.
2. Copy the whole file to `.github/skills/<name>/SKILL.md`, creating the
   folder. If it already exists, replace it.
3. Explain in three short lines:
   - VS Code finds skills in `.github/skills`, one folder per skill, the
     folder named after the skill. That is all installing is.
   - Accessibility Agents is 113 skills installed exactly the same way.
   - Every time you revise `my-agent/SKILL.md`, /review-my-agent installs
     the new version for you.
4. Tell them to try it: type /<name> followed by a request, for example
   /<name> plan the scanned reading. If the command does not appear, check
   that the folder name and the `name` in the header match exactly (VS Code
   skips a skill whose name does not match its folder), then start a New
   Chat and try again.
