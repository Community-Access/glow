# GLOW Feedback-to-Support-Hub Automation Setup

## Quick Answer

- **Is PAT in the repo?** NO - for security, it must be configured manually
- **Are issues created?** YES - but only when `SUPPORT_HUB_GITHUB_TOKEN` is set in the environment

## Three-Minute Setup

### 1. Generate GitHub PAT
```
https://github.com/settings/tokens → Generate new token (classic)
Name: community-access-support-sync-dev
Scopes: repo, read:user
Copy token immediately
```

### 2. Set Environment Variable
```bash
export SUPPORT_HUB_GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
```

### 3. Test Locally
```bash
cd s:\code\glow\web
python3 -m flask --app src.acb_large_print_web.app run
# Visit http://localhost:5000/feedback
# Submit feedback with name/email
# Check Community-Access/support issues - it should appear automatically
```

## How It Works

### When PAT is Configured ✅
1. User submits feedback form with optional name/email
2. Feedback saved to SQLite immediately
3. GitHub issue created automatically in the Community Access support hub:
   - Title: `[Feedback] Rating | Task | Date`
   - Body includes name, email (if provided), rating, task, message
   - Routed to `Community-Access/support`
   - Labeled with the configured support-hub labels
   - User gets link to issue

### When PAT is NOT Configured (No Error) ✅
1. User submits feedback form
2. Feedback saved to SQLite
3. No GitHub issue created
4. `github_sync_error` field contains error message
5. Admin can retry sync later with `sync-feedback-to-github.py` script

## Environment Variables

```bash
# Required for issue creation
export SUPPORT_HUB_GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE

# Optional (defaults shown)
export SUPPORT_HUB_GITHUB_REPO=Community-Access/support
export SUPPORT_HUB_GITHUB_ASSIGNEE=
export SUPPORT_HUB_GITHUB_LABELS=needs-triage

# Optional for machine-to-machine app feedback submissions
export SUPPORT_HUB_API_TOKEN=replace-with-shared-secret

# Optional (for feedback review dashboard)
export FEEDBACK_PASSWORD=your-secure-password-here
```

## Local Development (.env File)

Create `web/.env`:
```
SECRET_KEY=dev-key-12345
FEEDBACK_PASSWORD=dev-password
SUPPORT_HUB_GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
SUPPORT_HUB_GITHUB_REPO=Community-Access/support
SUPPORT_HUB_GITHUB_ASSIGNEE=
SUPPORT_HUB_GITHUB_LABELS=needs-triage
SUPPORT_HUB_API_TOKEN=replace-with-shared-secret
LOG_LEVEL=DEBUG
```

**IMPORTANT:** Never commit `.env` to git!

## Production Deployment (Docker)

Set in `docker-compose.yml`:
```yaml
environment:
   SUPPORT_HUB_GITHUB_TOKEN: ${SUPPORT_HUB_GITHUB_TOKEN}
   SUPPORT_HUB_GITHUB_REPO: Community-Access/support
   SUPPORT_HUB_GITHUB_ASSIGNEE: ${SUPPORT_HUB_GITHUB_ASSIGNEE}
   SUPPORT_HUB_GITHUB_LABELS: needs-triage
   SUPPORT_HUB_API_TOKEN: ${SUPPORT_HUB_API_TOKEN}
```

Then deploy:
```bash
export SUPPORT_HUB_GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
docker-compose up
```

## Backfill Existing Feedback

If you have historical feedback that wasn't synced:

```bash
export SUPPORT_HUB_GITHUB_TOKEN=ghp_YOUR_TOKEN_HERE
python3 scripts/sync-feedback-to-github.py
```

This creates issues for all unssynced rows with name/email included.

## Verify Issue Creation

### Check GitHub
Visit [Community-Access/support Issues](https://github.com/Community-Access/support/issues) after submitting feedback.

### Check Feedback Database
```bash
# View sync status in review dashboard
export FEEDBACK_PASSWORD=dev-password
curl "http://localhost:5000/feedback/review?key=dev-password"
```

Fields to check:
- `github_issue_number` - Issue number (if synced)
- `github_issue_url` - Link to GitHub (if synced)
- `github_sync_status` - `synced`, `failed`, or NULL
- `github_sync_error` - Error message (if failed)

## Troubleshooting

### Issues Not Being Created

1. **Check token is set:**
   ```bash
   echo $SUPPORT_HUB_GITHUB_TOKEN  # Should print ghp_xxx...
   ```

2. **Check token has permissions:**
   - Visit https://github.com/settings/tokens - verify scopes include `repo`

3. **Check feedback submission:**
   - Visit `/feedback/review?key=YOUR_PASSWORD` dashboard
   - Look for `github_sync_error` column

4. **Check logs:**
   ```bash
   # In feedback review dashboard or:
   sqlite3 s:/code/glow/instance/feedback.db "SELECT id, github_sync_error FROM feedback WHERE github_sync_error IS NOT NULL;"
   ```

### Token Expired

Generate a new token:
```bash
# https://github.com/settings/tokens
export SUPPORT_HUB_GITHUB_TOKEN=ghp_NEW_TOKEN_HERE
```

### Rate Limited

GitHub API allows ~60 requests per hour unauthenticated, ~5000 per hour with token.

Backfill script includes retry/backoff:
```bash
python3 scripts/sync-feedback-to-github.py --limit 10  # Sync max 10 at a time
```

## See Also

- [CONTRIBUTING.md](CONTRIBUTING.md) - Full development setup
- [BRANCH_PROTECTION_RULES.md](BRANCH_PROTECTION_RULES.md) - Main branch rules
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) - Community standards
