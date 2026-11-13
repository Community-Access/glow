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
