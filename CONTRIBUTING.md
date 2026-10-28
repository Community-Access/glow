# Contributing to GLOW

Thank you for your interest in contributing to the GLOW. We welcome contributions from the community, whether you're fixing bugs, adding features, improving documentation, or sharing feedback.

## Quick Start for Contributors

### 1. Report Issues or Feedback

**Found a bug?** Use [GitHub Issues](https://github.com/Community-Access/glow/issues) to report it.

**Found an accessibility barrier?** Use the [accessibility issue form](https://github.com/Community-Access/glow/issues/new?template=accessibility.yml), or see [Accessibility](#accessibility) below for other ways to tell us.

**Have feedback or a feature request?** Use the [Feedback form](https://letitglow.app/feedback/) on the web app. When support-hub sync is configured, your feedback is automatically converted into a tracked issue in [Community-Access/support](https://github.com/Community-Access/support/issues).

### 2. Set Up Your Development Environment

#### Prerequisites
- Python 3.13+
- Node.js 20+ (for web frontend tooling, if applicable)
- Git
- Docker & Docker Compose (for local deployment testing)

#### Clone and Install

```bash
git clone https://github.com/Community-Access/glow.git
cd glow
cd web
pip install -e ".[dev]"
pytest
```

Note: before installing, run `pip show acb-large-print` and check the
`Location`/`Editable project location` fields. A stale editable install from
an old checkout silently shadows the current code (an editable 7.5.0 once
masked the 8.0.0 wheel and broke the MCP server on a dev machine). If the
path points at a checkout you no longer use, `pip uninstall acb-large-print`
first, and consider deleting the dead checkout.

#### Set Environment Variables

Create a `.env` file in the `web/` directory for local development:

```bash
SECRET_KEY=dev-key-change-in-production
FEEDBACK_PASSWORD=dev-password-for-feedback-review
SUPPORT_HUB_GITHUB_TOKEN=your-github-pat-here
SUPPORT_HUB_GITHUB_REPO=Community-Access/support
SUPPORT_HUB_GITHUB_ASSIGNEE=
SUPPORT_HUB_GITHUB_LABELS=needs-triage
SUPPORT_HUB_API_TOKEN=replace-with-shared-secret
LOG_LEVEL=DEBUG
```

To generate a secure `SECRET_KEY`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. GitHub Token Setup (for Support-Hub Sync)

If you're working on feedback features or testing the full workflow:

1. **Generate a Personal Access Token (PAT):**
   - Go to [GitHub Settings > Personal Access Tokens](https://github.com/settings/tokens)
   - Click **Generate new token** (classic)
   - Give it a descriptive name (e.g., `glow-feedback-sync-dev`)
   - Grant these scopes:
     - `repo` (full control of private repositories)
     - `read:user` (read your profile)
   - Copy the token immediately (you won't see it again)

2. **Set it in your environment:**
   ```bash
   export SUPPORT_HUB_GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
   ```
   Or add it to your `.env` file (do NOT commit `.env` to git).

3. **Test the feedback-to-support-hub workflow:**
   ```bash
   cd web
   python3 -m flask --app src.acb_large_print_web.app run
   # Visit http://localhost:5000/feedback and submit test feedback
   # Check Community-Access/support issues to see the created issue
   ```

### 4. Backfill Existing Feedback

If you have historical feedback in your local `feedback.db`, sync it to GitHub issues:

```bash
export SUPPORT_HUB_GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
python3 scripts/sync-feedback-to-github.py
```

### 5. Make Your Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Write code and tests:**
   ```bash
   pytest  # run the test suite
   ruff check .  # lint
   ruff format .  # auto-format
   ```

3. **Commit with clear messages:**
   ```bash
   git commit -m "feat: add new accessibility rule for headings"
   ```

4. **Push and open a pull request:**
   ```bash
   git push origin feat/your-feature-name
   ```

## Code Standards

- **Python:** PEP 8 via Ruff
- **Accessibility:** WCAG 2.2 AA for all UI, as a goal; see [Accessibility](#accessibility)
- **Documentation:** Markdown with clear examples, following the documentation rules in [ACCESSIBILITY.md](ACCESSIBILITY.md#contributor-expectations)

## Accessibility

Every contribution follows the
[contributor expectations in ACCESSIBILITY.md](ACCESSIBILITY.md#contributor-expectations):
the checks to run, what to test for any interface change, and the rules for
documentation. The pull request template turns them into a checklist.

The accessibility checks you can run yourself, from `web/`:

```bash
pytest                    # includes the template accessibility guardrails
npm ci                    # once, then: npx playwright install chromium
npm run test:axe          # axe-core, WCAG 2.2 AA tags, every public page
npm run test:keyboard     # keyboard-only smoke test of the core flows
npm run test:reflow       # 200 and 400 percent zoom, no sideways scrolling
```

What each check covers, and the keyboard, screen reader and manual checks
that need a person, are in
[docs/accessibility-testing.md](docs/accessibility-testing.md).

### Reporting an accessibility barrier

Use the
[accessibility issue form](https://github.com/Community-Access/glow/issues/new?template=accessibility.yml).
If GitHub is a barrier for you, or you would rather not post publicly, use the
[feedback form](https://letitglow.app/feedback/) in GLOW or email
[support@community-access.org](mailto:support@community-access.org). How we
triage and respond is in
[ACCESSIBILITY.md](ACCESSIBILITY.md#reporting-accessibility-issues).

### Accessibility work you can pick up

- [Accessibility issues for new contributors](https://github.com/Community-Access/glow/issues?q=is%3Aissue+is%3Aopen+label%3Aaccessibility+label%3A%22good+first+issue%22),
  labelled `accessibility` and `good first issue`.
- [Accessibility issues where we need specialist help](https://github.com/Community-Access/glow/issues?q=is%3Aissue+is%3Aopen+label%3Aaccessibility+label%3A%22help+wanted%22),
  labelled `accessibility` and `help wanted`; each says what experience it
  needs.
- [All open accessibility issues](https://github.com/Community-Access/glow/issues?q=is%3Aissue+is%3Aopen+label%3Aaccessibility).

Not all of it is code. Testing GLOW with a screen reader, magnifier, voice
control or the keyboard, reproducing a report someone else filed, reviewing
the user guide, or checking that a document GLOW produced reads well are all
contributions we value and credit.

### Ways to take part

Everything in GLOW's development happens asynchronously and in text: issues,
pull requests and review comments on GitHub, the feedback form in the web app,
and email to [support@community-access.org](mailto:support@community-access.org).
No meeting or call is required to contribute. When we hold a project meeting,
the agenda is posted in advance, notes are posted to an issue afterwards, and
joining with a camera or by speaking is never required.

If a tool or process we use is a barrier for you, or you need an accommodation
to contribute, email
[support@community-access.org](mailto:support@community-access.org) or
[jeff@jeffbishop.com](mailto:jeff@jeffbishop.com) privately. You do not need to
explain why, and we will not discuss it in public. How we reviewed the tools we
use is in [docs/accessibility-framework.md](docs/accessibility-framework.md#community-phase).

## Testing

Run the full test suite:

```bash
pytest -v
```

Run with coverage:

```bash
pytest --cov=src
```

## Documentation

- **User-facing docs** are in `docs/` (Markdown)
- **API docs** are in docstrings (Google-style format)
- **Deployment guide** is in `docs/deployment.md`
- **Product requirements** are in `docs/prd.md`

## Architecture

GLOW is organized as:

```text
glow/
  web/                     Flask web app
    src/                   Application source
      acb_large_print_web/
        routes/            API and page routes
        templates/         Jinja2 HTML templates
        static/            CSS, JS, assets
    tests/                 Test suite
    e2e/                   Playwright suites, including accessibility
    pyproject.toml         Python dependencies
  docs/                    User and deployment documentation
  scripts/                 Deployment and utility scripts
  .github/workflows/       CI/CD workflows
  README.md
```

## Reporting Security Issues

Please do NOT open a public issue for security vulnerabilities. Instead, email security concerns to the BITS team (contact details in [SECURITY.md](SECURITY.md)).

## Code of Conduct

This project adheres to the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Questions?

- Open a [GitHub issue](https://github.com/Community-Access/glow/issues)
- Submit feedback via the [web app](https://letitglow.app/feedback/)
- Email [support@community-access.org](mailto:support@community-access.org)

Thank you for contributing to accessible technology.
