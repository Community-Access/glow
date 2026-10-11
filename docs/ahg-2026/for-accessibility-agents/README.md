---
title: "For the Accessibility Agents repository"
lang: en
author: "Jeff Bishop, BITS"
description: "What the Accessibility Agents repository needs for the AHG 2026 capstone."
---

# For the Accessibility Agents repository

The capstone promises that every participant commits an agent to the
Accessibility Agents repository. This folder is what that repository needs
before 16 November, ready to copy in: `community/ahg-2026/README.md`, the
landing folder the share page opens pull requests into.

Not yet applied. Before applying it, check that `scripts/validate-skills.mjs`,
the context budget check and `scripts/install.mjs` in that repository skip
`community/`, so beginner contributions neither fail its checks nor get
installed for every user. Then add a CODEOWNERS line making the workshop
facilitator the owner of `community/ahg-2026/`.
