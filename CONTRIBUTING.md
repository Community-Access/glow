# Contributing to GLOW

Thank you for your interest in contributing to the GLOW. We welcome contributions from the community, whether you're fixing bugs, adding features, improving documentation, or sharing feedback.

## Quick Start for Contributors

### 1. Report Issues or Feedback

**Found a bug?** Use [GitHub Issues](https://github.com/Community-Access/glow/issues) to report it.

**Have feedback or a feature request?** Use the [Feedback form](https://glow.bits-acb.org/feedback) on the web app. When support-hub sync is configured, your feedback is automatically converted into a tracked issue in [Community-Access/support](https://github.com/Community-Access/support/issues).

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
- **Accessibility:** WCAG 2.2 AA for all UI
- **Documentation:** Markdown with clear examples

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

```
glow/
├── web/                     # Flask web app
│   ├── src/                 # Application source
│   │   └── acb_large_print_web/
│   │       ├── routes/      # API and page routes
│   │       ├── templates/   # Jinja2 HTML templates
│   │       └── static/      # CSS, JS, assets
│   ├── tests/               # Test suite
│   └── pyproject.toml       # Python dependencies
├── docs/                    # User and deployment documentation
├── scripts/                 # Deployment and utility scripts
├── .github/workflows/       # CI/CD workflows
└── README.md
```

## Reporting Security Issues

Please do NOT open a public issue for security vulnerabilities. Instead, email security concerns to the BITS team (contact details in [SECURITY.md](SECURITY.md)).

## Code of Conduct

This project adheres to the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Questions?

- Open a [GitHub Discussion](https://github.com/Community-Access/glow/discussions)
- Submit feedback via the [web app](https://glow.bits-acb.org/feedback)
- Email the BITS team

Thank you for contributing to accessible technology.
