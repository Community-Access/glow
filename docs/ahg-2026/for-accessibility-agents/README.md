---
title: "For the Accessibility Agents repository"
lang: en
author: "Jeff Bishop, BITS"
description: "What the Accessibility Agents repository needs for the AHG 2026 capstone."
---

# For the Accessibility Agents repository

The capstone promises that every participant commits an agent to the
Accessibility Agents repository. On the day, participants share into the
workshop repository, Community-Access/ahg-2026, where each agent is
committed in its author's name. At the end of the day,
`scripts/promote_to_accessibility_agents.py` in that repository copies every
agent here, into `community/ahg-2026/`, in one pull request with every author
credited as a co-author. This folder is what that pull request lands in:
`community/ahg-2026/README.md`.

Not yet applied. Before applying it, check that `scripts/validate-skills.mjs`,
the context budget check and `scripts/install.mjs` in that repository skip
`community/`, so beginner contributions neither fail its checks nor get
installed for every user. Then add a CODEOWNERS line making the workshop
facilitator the owner of `community/ahg-2026/`.
