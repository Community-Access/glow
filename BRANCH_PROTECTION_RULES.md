# Branch Protection Rules

The Community-Access/glow repository enforces branch protection rules on the `main` branch to ensure code quality and security for open source contributions.

## Rules Enforced

### Status Checks
- **Required:** All CI workflows must pass before merge (strict mode)
- **Tests:** "Run tests" must complete successfully. This check is produced by
  `.github/workflows/tests.yml`, which runs on `pull_request` **and** on pushes
  to `main`.
- **Branch must be up-to-date:** New commits to base branch require re-sync before merge

> **Why "Run tests" has its own workflow.** It previously lived only in
> `deploy.yml`, which triggers on push and `workflow_dispatch` but never on
> `pull_request`. A pull request could therefore never produce the check it was
> required to pass, so every PR blocked indefinitely and admin enforcement was
> switched off so work could land by pushing directly to `main`. If this check
> is ever moved or renamed, update the required-status-check context at the same
> time, and keep it free of a `paths:` filter — a path-filtered required check
> silently reintroduces the same deadlock for PRs that touch other paths.

### Code Review
- **Minimum reviews:** 1 approving review required before merge
- **Stale review dismissal:** Old reviews are dismissed when new commits are pushed
- **Conversation resolution:** All discussions must be resolved before merge
- **Code owner reviews:** Not required (optional for faster iteration)

### Admin & Merge Rules
- **Enforce on admins:** Rules apply to repository administrators
- **No force pushes:** Force push is disabled
- **No branch deletion:** Branches cannot be deleted after protection is enabled
- **Require linear history:** Not required (allows merge commits)

## Why These Rules Exist

1. **Quality assurance** — CI must pass for every merge
2. **Community oversight** — At least one code review ensures community feedback
3. **Transparency** — Discussions resolve questions before code is merged
4. **Accident prevention** — Prevents accidental branch deletion or history rewriting
5. **Consistency** — All contributors follow the same review process

## Workflow for Contributors

1. Fork the repository
2. Create a feature branch
3. Make changes and push
4. Open a Pull Request (automated GitHub Actions run)
5. Wait for status checks to pass
6. Request code review from maintainers
7. Address feedback and respond to discussions
8. Maintainer approves and merges when all checks pass

## Bypassing Rules (Maintainers Only)

Admins can dismiss protection to perform emergency fixes by temporarily disabling the rule on GitHub (Settings > Branches > Branch protection rules > main). Re-enable immediately after.

## Questions?

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details on the contribution process.
