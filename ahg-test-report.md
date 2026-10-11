---
title: "AHG 2026 workshop: test report, 10 October 2026"
lang: en
author: "Jeff Bishop, BITS"
description: "Results of the first test pass of the AHG 2026 Accessibility Agents workshop on Windows, the defects found and fixed, and what remains."
---

# AHG 2026 workshop: test report, 10 October 2026

This reports the first test pass of the Accessing Higher Ground 2026
workshop, "Accessibility Agents: Building Human-Centered AI Workflows for
Trusted Accessibility Automation at Scale", against the test plan in
`ahg.md`. The test plan is the source of truth for every case; this file
records what was run, what was found, what was fixed and what is left.

## 1. Summary

Every test case that can run without a signed-in Copilot account, without
listening with a screen reader and without a Mac was run on 10 October 2026,
and every one passes. The pass found five defects. All five are fixed and
re-tested. One of them, D-002, is live on letitglow.app today and affects
every page on a phone or at high zoom; its fix is in PR #117, waiting to be
merged.

What remains is the part only a person can do: the Copilot commands with a
real account, the NVDA and JAWS passes by ear, the real GitHub fork and
pull request, the fallback drills and the timed dry run. Section 6 lists
them in order.

## 2. Scope and environment

The pass was run on the branch `feat/ahg-2026-workshop` (PR #116), with GLOW
running locally from that branch as described in `ahg.md` section 1.7.

| Item | Value |
|---|---|
| Date | 10 October 2026 |
| Tester | Claude, for Jeff Bishop |
| Operating system | Windows 11 |
| Browser | Chrome, driven by Playwright, at 320px and 1280px wide |
| Office | Word, PowerPoint and Excel, opened through Office automation |
| VS Code | 1.141.0, extensions installed into a throwaway folder |
| Accessibility engine | axe-core 4.11.4 |
| Not covered | Mac and VoiceOver (Env-4, Env-5): Jeff tests on Windows only, so these need a separate tester with a Mac |

## 3. Results by area

Each row summarizes an area of the test plan; the per-case results are in
the Result column of `ahg.md`.

| Area | Cases run | Result | Notes |
|---|---|---|---|
| Automated checks | Auto-01 to Auto-05, Auto-07, Auto-08 | Pass | 1112 web tests passed, 31 skipped; Markdown auditor tests 16 passed; materials conform; 34 of 34 documents pass GLOW's audit; 42 of 42 sample course barriers present; every CI check on PR #116 green |
| Setup page | Setup-01, Setup-11, Setup-12, Setup-13 | Pass | Every link and both rules present; one H1, four H2s; no axe violations; the kit and profile download without the consent page, the pages themselves show it first |
| Profile extensions | Part of Setup-04 | Pass | All four install in VS Code 1.141; GitHub Copilot Chat is built into that version |
| Deck | Deck-01, Deck-02, Deck-03, Deck-06 | Pass | 26 slides, program title; Home, End and arrow keys move focus to each slide heading; notes toggle; one-file download works offline; no axe violations |
| Share page | Share-01, Share-02, Share-05 to Share-08 | Pass | Loads the agent file and its name; opens GitHub's new-file page in the right folder of a test fork; empty agent, missing name and over-long agent are all handled with focus moved to the field; the offline copy works the same way; no axe violations |
| Keyboard | A11y-01 on the share page | Pass | Every control reachable by Tab |
| Reflow | A11y-02 | Pass after fixes | No sideways scrolling at 320px on the home, privacy, workshop, setup, share, deck, audit and convert pages |
| Sample course | Mat-01, Mat-02 | Pass | Every file opens in Word, PowerPoint or Excel; every barrier in the answer key is present |
| Load | Load-01 | Pass | 40 simultaneous kit downloads, 40 succeeded |

## 4. Defects found and fixed

Each defect was fixed on the branch, re-tested, and logged in `ahg.md`
section 2.14.

| Defect | Found by | What happened | Fix | Re-test |
|---|---|---|---|---|
| D-001 | Auto-07, the Vale prose check in CI | Six ready-made agents had author lines like "Example: Maria Alvarez", which is not valid YAML. Vale stopped on it, and VS Code and the Agent Skills tools would have misread those headers | The kit build quotes header text; the template and the /design-my-agent command keep the quotes; a test parses every front matter block | Pass |
| D-002 | A11y-02 | On every GLOW page at 320px wide, a phone or 400 percent zoom, the page content was 0px wide. The AI usage meter was included after the sidebar and became a column of its own. This fails WCAG 2.2, 1.4.10 Reflow, and is live on letitglow.app now | The meter moved inside the sidebar, as a named group. PR #117 carries the fix for production; the same commits are on this branch | Pass |
| D-003 | A11y-02 | The home, privacy, audit and convert pages scrolled sideways at 320px: by 397, 91, 15 and 66 pixels | Main content wraps long addresses; fieldsets, inputs and selects stay inside the page; the home grid and quick start button wrap. In PR #117 | Pass |
| D-004 | A11y-02 and the deck's axe scan | The setup page's profile address and the deck's slide picker overflowed at 320px; the deck's controls sat outside any landmark; the slide count said "of 30" before the script ran | Address wraps; slide picker shrinks; controls are a named region; count comes from the deck | Pass |
| D-005 | Setup-04 inspection | The six Copilot commands used the older `mode:` header; VS Code 1.141 reads `agent:` | All six now use `agent: agent` | Pass by inspection; Setup-09 confirms it in use |

## 5. Changes made during the pass

These commits are on `feat/ahg-2026-workshop`; the first three are also on
`fix/ai-meter-layout` (PR #117) for production.

| Commit | Change |
|---|---|
| `eb69a8a` | AI meter inside the sidebar, so pages reflow |
| `cc4cfe8` | No nested complementary landmark; long text wraps |
| `14810b7` | Home grid, quick start button and form controls reflow |
| `1d4f1fd` | Agent header text quoted so a colon cannot break the YAML |
| `41f1fd7` | Deck controls in a named region, slide count from the deck, setup page wraps the profile address |
| Later commits | Deck regenerated; prompt files use `agent:`; test plan results recorded; this report |

New scripts make every check in this report repeatable.

| Script | What it checks |
|---|---|
| `scripts/ahg_browser_checks.py` | The 35 browser checks in section 3, against a running GLOW: setup page, deck, share page, keyboard, axe, reflow and load |
| `scripts/check_ahg_sample_course.py` | That all 42 planted barriers are in the sample course |
| `scripts/audit_ahg_docs.py` | That every document a person reads passes GLOW's own audit |
| `scripts/check_material_conformance.py` | That the materials keep the program's promises |

Run the browser checks with GLOW started as in `ahg.md` section 1.7:

```text
python scripts/ahg_browser_checks.py --base http://127.0.0.1:5000 --axe web/node_modules/axe-core/axe.min.js
python scripts/check_ahg_sample_course.py
python scripts/audit_ahg_docs.py
python scripts/check_material_conformance.py
```

## 6. What remains, for Jeff on Windows

In this order. Each item names its cases in `ahg.md`.

1. Setup with a brand-new GitHub account: turn on Copilot Free, import the
   profile, open the kit, run `/ready-check` (Setup-02 to Setup-10). This
   also confirms D-005 in real use.
2. Every block's Copilot command, with the three role cards and the
   fallbacks (Design-01 to Design-09, Try-01 to Try-04, Ground-01 to
   Ground-11, Office-01 to Office-08, Plan-01, Plan-02). Record Copilot
   Free usage for a whole day in Office-08.
3. Word's and PowerPoint's own Accessibility Checker on `slides.docx` and
   `slides.pptx` (Deck-07, Deck-09). GLOW's audits already score both 100.
4. NVDA and JAWS by ear, Env-2 and Env-3: every step from setup to the
   team report, plus Setup-11, Deck-08, Design-08 and Share-10.
5. The real GitHub path with a test fork, using `?repo=` on the share page:
   Share-03 and Share-04; then Share-09 and Share-11 once the
   `community/ahg-2026` folder is in the Accessibility Agents repository.
6. The commitment wall: Wall-01 to Wall-03.
7. Fallback drills Fall-01 to Fall-05, A11y-03 and A11y-04, and the timed
   dry run, Dry-01.
8. Find a Mac tester for Env-4 and Env-5.

## 7. Decisions needed

These are not test steps, but testing cannot finish without them.

| Decision | Why it matters |
|---|---|
| Merge PR #117 | D-002 makes every GLOW page unusable on a phone today. Merging deploys |
| Merge PR #116 | The setup page, kit, profile and share page exist in production only after it. Merging deploys |
| Copy the `community/ahg-2026` folder into the Accessibility Agents repository | Share-09 and Share-11, and the capstone itself, need it |
| A Mac tester | Env-4 and Env-5 cannot be signed off without one |
