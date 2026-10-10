---
title: "AHG 2026 workshop plan: Accessibility Agents for higher education"
lang: en
author: "Jeff Bishop, BITS"
description: "How the AHG 2026 Accessibility Agents workshop keeps every promise in its published session description."
---

# AHG 2026 workshop plan: Accessibility Agents for higher education

Status: built 9 October 2026, ready for review and testing. Everything in
this plan exists except what section 16 says must be proven by a person, and
the Accessibility Agents folder, which is ready to copy in from
`for-accessibility-agents/`.

This plan replaces the September plan, kept as `plan-2026-09-glow-only.md`.
That plan was built around a different promise: no AI, no development tools,
a phone is enough. The program AHG published says otherwise. The rule now:
keep every promise the program makes, in the simplest way that keeps it.

## 1. What the program promises

From the session page on accessinghigherground.org (session 42876), which is
what participants read when they registered:

- Title: Accessibility Agents: Building Human-Centered AI Workflows for
  Trusted Accessibility Automation at Scale.
- Monday 16 November 2026, 10:30 AM, room Matchless, Hilton Denver City
  Center. One day. The page also says "2-day"; that is the conference's error
  and we will ask them to correct it.
- Bring a Windows or Mac laptop, and headphones if you use a screen reader.
  Beginner level.
- The problem: higher education accessibility teams facing WCAG 2.2 and the
  new Title II requirements, who need to scale while keeping quality,
  accountability and transparency.
- Agents analyze content, identify barriers and generate remediation guidance
  grounded in authoritative standards. They extend professionals; they do
  not replace them.
- Participants "learn to build agent teams using Visual Studio Code, GitHub
  and Copilot", and "explore how accessibility agents can be created using
  modern development tools such as Visual Studio Code and GitHub Copilot while
  collaborating through open-source workflows on GitHub".
- axe-core and Accessibility Insights keep the analysis grounded in trusted
  standards.
- Agent teams: coordinated specialists that analyze, gather evidence and cite
  authoritative resources.
- Capstone: each participant designs an accessibility agent and commits it to
  the open-source Accessibility Agents repository.
- Key points: cognitive and learning accessibility, student success,
  alternate formats.

## 2. Who is in the room

Disability resource staff, IT accessibility staff, instructional designers,
faculty developers, communications and web staff, and some managers. Most are
not developers. Some use screen readers or magnification.

Four rules follow from that.

1. Meet people where they are. An agent is a set of plain-English
   instructions. Writing one is writing, not coding. No installs, no
   terminal, no code.
2. Show the destination first. People see the finished outcome before they
   start every step, and always know where they are on the journey.
3. Never start from a blank page. Every step starts from a worked example and
   has a catch-up file.
4. Real higher education work. The material is a course full of documents,
   because that is where most campus accessibility work is.

## 3. What a participant needs

Keeping every promise means every participant builds with VS Code, GitHub and
Copilot. We make that as small as it can be.

1. A laptop with a browser, and headphones if they use a screen reader.
2. A free GitHub account, with Copilot Free turned on. Copilot is their AI
   for the whole day, in the browser and in VS Code.
3. VS Code, plus the AHG 2026 profile, which installs everything else in one
   step: Copilot Chat, GitHub Pull Requests, GitHub Repositories (so nobody
   needs Git), and the axe Accessibility Linter, with large text and screen
   reader settings already on.

That is all. No terminal, no command line, no Git install, no code. Anyone
who prefers another AI assistant for the morning, such as their campus
Copilot or free ChatGPT, may use it; the afternoon is in VS Code with GitHub
Copilot for everyone.

Anyone who cannot install VS Code pairs with a neighbor for the afternoon
and still submits their own agent from the browser.

## 4. Decisions

These replace L1 to L14 in the September plan.

| # | Decision |
|---|---|
| D1 | One day, Monday 16 November, 10:30 AM to 4:30 PM Mountain Time. Lunch 12:15 to 1:15, to confirm with AHG |
| D2 | A Windows or Mac laptop, as the program says, with headphones for screen reader users |
| D3 | Every participant uses GitHub Copilot through their own free GitHub account. Other assistants are welcome in the morning. GLOW provides no AI and holds no AI key |
| D4 | Text only into an assistant, never an upload. Free tiers cap uploads and do not cap text, and a document's text report keeps the document itself out of the AI |
| D5 | No student records, accommodation details, health information or names go into any AI tool. All work uses the sample course |
| D6 | Grounding comes from checkers, not from the AI: GLOW for documents, Accessibility Insights FastPass and axe-core for the web page. Agents must cite WCAG and the sources the Accessibility Agents citation policy names |
| D7 | Every agent has a human review step the participant writes. Nothing an agent produces goes anywhere without a named person approving it |
| D8 | Every participant builds the agent team in VS Code with Copilot: they add their own specialist to the ready-made office and run the team across the sample course |
| D9 | Every participant commits their own agent to the Accessibility Agents repository from their own GitHub account, by pull request, using buttons only |
| D10 | The facilitator reviews and merges the room's pull requests live, so everyone sees the open-source workflow, then runs the merged team on the projector |
| D15 | Setup is one VS Code profile, the AHG 2026 profile, plus the agent kit. The kit's own settings recommend the same extensions, as a safety net if the profile does not import |
| D11 | Documents are the center of the day. The sample course is three documents and one web page |
| D12 | Nothing taught depends on GLOW. Every step names the general skill and shows it working with tools people already have, so the day still pays off if GLOW is never opened again |
| D13 | Support on request at support@community-access.org, before and after the day |
| D14 | The last five minutes are the AHG session evaluation |

## 5. Every promise, and where it is kept

If a block is cut, this table shows which promise breaks.

| Promise | Where it is kept |
|---|---|
| Higher education, WCAG 2.2, Title II, scale | Block 1 opens with it; the sample course is a course backlog in miniature |
| Agents analyze content, find barriers, generate remediation guidance | Blocks 2 and 3 |
| Grounded in authoritative standards; axe-core and Accessibility Insights | Block 4: evidence from GLOW, Accessibility Insights and axe-core, with citations required |
| Human-centered, extending experts | The review step in every agent, and the named reviewer in the team report |
| VS Code, GitHub and Copilot | Every participant: Copilot all day, VS Code in block 6, GitHub in block 5 |
| Learn to build agent teams | Block 6: each participant adds their specialist to the office team and runs the team themselves |
| Agent teams of coordinated specialists | Block 6: the coordinator routes the course to specialists, including the participant's own |
| At scale | Block 6: one team run across the whole course, one prioritized report |
| Quality, accountability, transparency | The team report: every finding has evidence, a citation and a named reviewer |
| Open-source collaboration; capstone commit | Block 5: each participant opens their own pull request; the facilitator merges them live |
| Cognitive and learning accessibility, alternate formats, student success | The alternate format role card, and the plain language specialist in the team |
| Beginner, bring a laptop | The setup message, the step cards, the helpers |

No promise depends on a demonstration alone. The live team run on the
projector is a bonus at the end, with everyone's merged agents in it, not a
substitute for anyone's own hands-on work.

## 6. The journey

One map, on the first slide and the first page of every handout, shown again
at the start of each block with "you are here".

1. The problem: a course full of barriers, and a team too small.
2. Your agent: five plain-English answers.
3. Your agent at work: your AI uses it on one course document.
4. Your agent, grounded: real evidence in, cited answers out.
5. Your agent, shared: committed to an open-source project with your name.
6. Your agent in the team: the whole course, at once.
7. Your campus: a 30-day plan.

## 7. The sample course

Built: `kit/sample-course/`, generated by `scripts/build_ahg_sample_course.py`,
with every planted barrier listed in `answer-key.md` (facilitators only, not
in the kit), and each file's checker report as text in
`kit/sample-course/evidence/`.

One course everyone works on: "PSY 101: Introduction to Psychology", Fall
2026, Dr. Dana Whitfield, Mesa Ridge State University. All fictional, all
original writing. The running joke is a course about memory and
procrastination that keeps forgetting things and running late.

| Item | Format | A few of its planted barriers | GLOW score |
|---|---|---|---|
| Syllabus | Word | Bold text instead of headings, a layout table, "click here" links, required readings shown only in red, the accommodations statement last in 8pt gray and contradicted in capitals | 0 |
| Week 3 lecture | PowerPoint | Untitled slides, reading order 3-2-1, "image.png" as alt text, a chart that is only a picture, myth or fact answered by red and green | 58 |
| Gradebook | Excel | Merged headers, status shown only by fill color, sheets named "Sheet" and "Sheet2" | 54 |
| Required reading | Scanned PDF | Pictures of text with no text layer: the alternate format case | 50 |
| Lab handout | PDF with a form | Untagged, unlabeled form fields, and an exercise that depends on seeing color | 50 |
| Course announcement | Web page | Low contrast, vague links, a clickable div for a button, an image with no alt | axe: 6 rules fail |
| Lecture captions | WebVTT | "herman ebb in house" for Hermann Ebbinghaus, no speaker labels, an undescribed graph | none |

Documents are five of the seven items, on purpose.

Every file has at least one barrier no checker finds, so the day shows why
grounding needs judgment and a human reviewer on top.

## 8. Three role cards

Each participant picks one. Each card has a finished example agent, a sample
input from the course, and the output it produces.

| Card | The problem | The agent they write | What they see it produce |
|---|---|---|---|
| Documents and alternate formats | A student's accommodation needs the scanned reading in large print and plain language; the backlog is Word and PowerPoint | Alternate format planner, or document triage | A plan for the reading with a review checklist, or a prioritized fix list for the lecture |
| Course content and faculty coaching | Faculty make the content, and fixing it all yourself does not scale | Faculty coach | A short, kind note to the syllabus owner that teaches the one habit behind the barriers |
| Compliance and procurement | Title II needs evidence, and vendors say their products are accessible | Remediation log keeper, or vendor report reader | A dated, prioritized log for the course, or questions to send a vendor |

## 9. The worked examples

Built: `kit/examples/`, one per role card, each with all seven artifacts:
Maria Alvarez (alternate formats), Jordan Lee (faculty coaching) and Sam
Okafor (compliance). Each shows a weak answer before grounding and a good one
after, using GLOW's real findings on the sample course.

Maria, from disability resources, works one step ahead of the room all day.
Her finished work is shown before anyone starts theirs.

1. Her problem: a student needs the scanned reading in large print.
2. Her five answers.
3. Her agent, and her AI's first answer.
4. Her agent's answer before grounding and after, side by side.
5. Her agent in the repository.
6. Her agent's section of the team report.
7. Her 30-day plan.

Each role card has the same seven artifacts.

## 10. The day

10:30 AM to 4:30 PM, 300 working minutes, lunch 12:15 to 1:15 (to confirm).

| Time | Minutes | Block | What the participant has at the end |
|---|---|---|---|
| 10:30 | 20 | 1. Why we are here, and the finished result shown first | The journey, and the team report they are working toward |
| 10:50 | 60 | 2. Design your agent | Five answers, and the agent file built from them |
| 11:50 | 25 | 3. Your agent at work | Copilot's answer, using their agent, on one course document |
| 12:15 | 60 | Lunch | |
| 1:15 | 55 | 4. Ground it | A before and after: the same agent, with evidence and citations |
| 2:10 | 10 | Break | |
| 2:20 | 40 | 5. Share it | Their own pull request in the Accessibility Agents repository |
| 3:00 | 45 | 6. Build the office, at scale | In VS Code: their specialist added to the team, the team run across the course, then everyone's merged agents run once on the projector |
| 3:45 | 30 | 7. Take it home | A 30-day plan and a one-page artifact |
| 4:15 | 10 | Commitments | The commitment wall, anonymous |
| 4:25 | 5 | Session evaluation | |

## 11. Tone

Warm, a little funny, and professional. The humor is aimed at situations
everyone in higher education recognizes: the broken coffee machine, the
spreadsheet named FINAL_final_v3, the syllabus that says late work is fine
because the procrastination unit needs data. It is never aimed at a student,
a disability, a colleague, or the people in the room. Every joke sits next
to a real point, and the examples always end with real work done.

## 11a. How every block runs

The same seven steps every time, so nobody learns a new way of working twice.

1. Where we are: the journey map, this step marked.
2. What you will have at the end: the finished outcome, shown first.
3. Watch me: a live demo, every step said out loud, every visual described.
4. Your turn: a step card in the order things appear on screen, with
   keyboard and screen reader keys, and what you should see after each step.
5. Check: "you are on track if", with one clear sign.
6. Catch-up: the finished result for this step, so nobody falls off.
7. Without GLOW: the same step with tools you already have, and where it
   goes on Monday.

## 12. Value without GLOW

The day has to be worth it to someone who never opens GLOW again. What they
take away is a way of working, not a product.

| They learn | They can do it Monday with |
|---|---|
| Writing an agent: role, task, trusted guidance, output format, human review | Any AI assistant, including the Copilot their campus licenses |
| Grounding: give the AI a checker's findings, not just the file, and make it cite the standard | Word's, PowerPoint's and Acrobat's built-in checkers, Accessibility Insights, axe |
| Human review as a written step, with a name on it | Their own office's process |
| Agent teams: split a big job into specialists and a coordinator | Any assistant, one specialist at a time, or Accessibility Agents in VS Code |
| Triage at scale: what to fix first, and why, with a defensible log | A spreadsheet |
| Their agent | Kept in the open-source repository, where anyone can use and improve it |

Block 4 shows grounding twice: once with GLOW's report and once with Word's
own Accessibility Checker, so people see the skill is the evidence, not the
tool.

## 13. What GLOW provides

No AI and no key. Built on 9 October.

1. The setup page, letitglow.app/workshop/ahg-2026: the four setup steps,
   the kit download, the profile and the step cards in one place.
2. The kit, served as a zip from that page, so nobody clones anything.
3. The AHG 2026 profile at a stable address, for VS Code's Import Profile.
4. The share page, letitglow.app/workshop/ahg-2026/share: it opens GitHub
   with the participant's agent already filled in, in
   `community/ahg-2026/` of the Accessibility Agents repository. They press
   "Propose changes" and "Create pull request" on their own account; GitHub
   makes the fork for them. GLOW holds no GitHub token. An offline copy is in
   the kit.
5. The evidence: GLOW's audit of every course document, as text in the kit,
   generated by `scripts/build_ahg_kit.py`.
6. The commitment wall, through the existing Workshop Mode session.

Copilot, not GLOW, turns the five answers into the agent file, through the
kit's /design-my-agent command, in the Accessibility Agents skill format.

## 14. The agent kit and the profile

Built: `kit/`, what participants download and open in VS Code.

| Part | What it is |
|---|---|
| `ahg-2026.code-profile` | The AHG 2026 VS Code profile: GitHub Copilot Chat, GitHub Pull Requests, GitHub Repositories and the axe Accessibility Linter, with 18pt text, word wrap and screen reader support |
| `.vscode/` | The same settings and recommendations, the safety net if the profile was skipped |
| `.github/copilot-instructions.md` | The workshop's rules for Copilot: plain language, encouragement, evidence only, cite WCAG 2.2, never "compliant", nothing private |
| `.github/prompts/` | One command per block: /ready-check, /design-my-agent, /try-my-agent, /ground-my-agent, /run-the-office, /my-30-day-plan |
| `.github/agents/office-coordinator.agent.md` | The coordinator that routes the course to the specialists, the participant's agent included, and writes the team report |
| `office-team/` | Eight specialists adapted from the Accessibility Agents project: Word, PowerPoint, Excel, PDF, web pages, captions and media, plain language, and a standards reviewer |
| `my-agent/SKILL.md` | The participant's agent, from a template with the never-do list built in |
| `examples/` | Maria, Jordan and Sam's stories, and six ready-made agents, two per role card, so everyone has a fallback that still lets them finish the day |
| `sample-course/` | PSY 101 and its evidence |
| `step-cards/` | One card per block, and one for setup, as Markdown and as ACB large print Word files |
| `share-my-agent.html` | The offline share page |
| `README.md` | The welcome page VS Code opens first |

The generated parts are rebuilt by `scripts/build_ahg_kit.py`, which also
writes the downloadable zip.

## 14a. The hand-holding kit

- Step cards for every block, in large print, as accessible Word files and
  web pages, tested with NVDA, JAWS and VoiceOver.
- The outcome gallery: every finished example output on one page.
- Catch-up results for every step and every role card.
- The answer key for the sample course, for facilitators.
- Helpers: at least one per ten participants.
- A help table from 10:00.

## 15. Before the day

The setup message goes out by 20 October, again on 6 November, and two days
before. It is a short numbered list.

1. Make a free GitHub account, and turn on Copilot Free.
2. Install VS Code. On Windows it installs without administrator rights.
3. Open the AHG 2026 profile link, and press Import. That installs everything
   else.
4. Download the agent kit and open it in VS Code. A welcome page appears.
5. Open the ready check page. It takes two minutes and tells you that you
   are set.
6. Stuck? Write to support@community-access.org, or come to the setup table
   from 10:00 on the day.

It says, plainly, that nobody needs to know VS Code or GitHub already, and
that every step on the day comes with a step card and a helper.

## 16. What has to be proven first

Before anything participant-facing is written, a walkthrough of the exact
path:

1. The AHG 2026 profile imports cleanly on Windows and Mac, and the kit's
   recommended extensions are the fallback if it does not.
2. Copilot in VS Code picks up the office team and the participant's agent
   from the kit, with no command line. Some Accessibility Agents specialists
   may expect scanning tools to be installed; any that do not work are
   dropped from the office.
3. A GLOW audit report, pasted into Copilot with a sample agent, gives cited,
   useful answers, inside Copilot Free's monthly allowance.
4. The share button, the automatic fork and the pull request, start to
   finish, with GitHub Repositories instead of Git.
5. Every participant step with NVDA, JAWS and VoiceOver.

## 17. What carries over from the September build

Each row pairs a September piece with what it became.

| September | Now |
|---|---|
| Problem statement | Block 1 and the role cards |
| Fix it for me, or teach me | The faculty coach card |
| Helpful, risky or human required | The review step in every agent |
| Agent formula and the skill builder | Block 2, unchanged at heart |
| Prompt cards | The worked examples, refreshed |
| 30-day plan, commitment wall, take-home artifact | Block 7 |
| Agenda module, deck renderer, GLOW audit tests, conformance checker | Kept, with the content and the checker's rules rewritten |

The privacy rule, the session evaluation, the ACB large print fixes and the
AHG speaker guidance mapping from 9 October all stay.

## 18. Risks

Each row is one risk and what we do about it.

| Risk | What we do |
|---|---|
| Accessibility Agents specialists do not run well under Copilot on documents | Proven first; the live team is trimmed to what works |
| Free AI tools give different answers | Checks ask "did it find these barriers and cite the standard", not "does it match the screen" |
| Free AI tools keep what is pasted | No private data, ever; we show where to turn training off |
| Thirty pull requests at once | Pull requests open from 2:20; merges batched and shown live; everyone's own team run does not wait for a merge |
| People arrive without setup done | Three setup messages, the ready check, the setup table at 10:00, pairing |
| The profile does not import on someone's laptop | The kit recommends the same extensions when it opens; a helper installs them with the person |
| Wifi | Sample course and audit text downloadable in advance; the live team run is on the facilitator's laptop |
| Screen reader barriers | Found in the walkthrough; step cards route around them |

## 19. Open decisions

1. Lunch time: assumed 12:15 to 1:15. Confirm with AHG.
2. The folder in the Accessibility Agents repository for workshop
   contributions, its checks, and who merges.
3. Helpers: who, and how many.
4. Maria as the persona, or someone else.

## 20. Order of work

Each row is a date and what must be done by then.

| By | What |
|---|---|
| 13 October | Plan approved; note to AHG about the length and lunch |
| 16 October | The walkthrough in section 16; the sample course and answer key |
| 20 October | First setup message; ready check page live |
| 27 October | GLOW additions in section 13; worked examples and the outcome gallery |
| 31 October | Step cards; the deck rebuilt from the agenda; the repository folder |
| 6 November | Second setup message; screen reader passes of the whole day |
| 9 November | Timed dry run with a second person; freeze |
| 14 November | Last setup message |
| 16 November | The day |
