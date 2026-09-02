# Deployment Guide: ACB Large Print Web Application

> **Version 2** -- April 2026. Production deployment on a RackNerd Ubuntu VPS with Docker Compose and Caddy.

## Quick Reference

> **Production deploys are automatic.** Pushing to `main` (or `release/**`) with
> changes under `web/`, `mcp_server/`, `desktop/src/`, the deploy scripts, or
> `CHANGELOG.md` triggers the **Deploy Web App** workflow, which runs
> `deploy-app.sh` on the server over SSH. In the normal case you do not need to
> log in and deploy anything by hand.
>
> **Do not run `deploy-app.sh` manually while an Actions deploy may be running.**
> The workflow's `concurrency: deploy-production` group serialises Actions runs
> against each other, but it cannot see a person on SSH. Two concurrent runs
> collide in `docker compose up` and the deploy fails with
> `Conflict. The container name "..._web-web-1" is already in use` — this has
> happened. Before any manual deploy, check the Actions tab (or
> `gh run list --workflow=deploy.yml`) and wait for in-flight runs to finish.
> Manual deploys are for recovery, a `workflow_dispatch` re-run, or when Actions
> itself is unavailable.

- **Automated Deployment Script:** `bash ~/app/scripts/deploy-app.sh`
- **Manual Maintenance Toggle:** `bash ~/app/scripts/maintenance-mode.sh {on|off|status}`
- **Complete Strategy & Troubleshooting:** The full deployment strategy is maintained in the repository documentation for operators working from the source tree.
- **Shared-core retrofit rollout checklist:** `docs/shared-core-retrofit.md` (server deployment readiness and smoke tests)

---

## Overview

This guide walks you through deploying the ACB Large Print web application on a single VPS. When you finish, you will have:

- `csedesigns.com` and `www.csedesigns.com` serving a static website (or placeholder)
- `glow.bits-acb.org` serving the Flask/Gunicorn application behind a reverse proxy
- Caddy handling TLS certificates automatically for all hostnames
- Automated daily backups of the feedback database
- A hardened server with firewall, fail2ban, and automatic security updates

The entire stack runs on one RackNerd VPS using Docker Compose.

---

## Before You Begin

### Prerequisites Checklist

Confirm you have all of the following before starting:

- [ ] A RackNerd VPS running Ubuntu 24.04 LTS with root SSH access
- [ ] The RackNerd welcome email containing: server IP, root password, and SolusVM credentials
- [ ] A registered domain (`csedesigns.com`) with access to its DNS settings
- [ ] A terminal or SSH client on your local machine
- [ ] An SSH key pair on your local machine (only if choosing SSH key login -- see Phase 2 for alternatives)
- [ ] 30--60 minutes of uninterrupted time

### Local Workstation Requirements

You need an SSH client and an SFTP client on your local machine.

**SSH clients by operating system:**

| OS | Built-in | Alternatives |
|----|----------|--------------|
| Windows 10/11 | `ssh` in PowerShell or Command Prompt (OpenSSH client) | PuTTY, Windows Terminal, Git Bash |
| macOS | `ssh` in Terminal | iTerm2 |
| Linux | `ssh` in any terminal | -- |

**SFTP clients:**

| Client | Platform | Notes |
|--------|----------|-------|
| Built-in `sftp` | macOS, Linux, Windows 10/11 | Terminal command, uses your SSH config |
| WinSCP | Windows | Free GUI. Import your SSH key in Connection, SSH, Authentication. |
| FileZilla | Windows, macOS, Linux | Free GUI. Use protocol SFTP (not FTP). Add key in Edit, Settings, SFTP. |
| Cyberduck | Windows, macOS | Free GUI. Supports OpenSSH keys directly. |

**If you do not have an SSH key pair yet**, create one:

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

This works on Windows PowerShell, macOS Terminal, and Linux. Accept the default file location. Set a passphrase if desired.

### DNS Requirement

DNS A records for your domain must point to the VPS IP address **before** Caddy can issue TLS certificates. Configure DNS early (Phase 1) because propagation can take minutes to hours.

---

## RackNerd-Specific Notes

Your RackNerd welcome email contains everything you need to get started. The key details are:

- **Server IP address** -- used for SSH connections and DNS A records
- **Root password** -- used for initial SSH login only (you will disable root login after setup)
- **SolusVM / NerdVM credentials** -- for the server control panel at `https://nerdvm.racknerd.com/`

**SolusVM / NerdVM control panel** is your emergency access path. Use it to:

- **Restart** the VPS if it becomes unresponsive
- **Access the HTML5 VNC console** if SSH is locked out (this is your lifeline)
- **Reinstall the OS** if the server is unrecoverable (destroys all data)
- View bandwidth usage and server status

> **Recovery note:** If you lose SSH access at any point in this guide, log into `https://nerdvm.racknerd.com/` with your SolusVM credentials. Select your VPS, then click the **VNC** or **HTML5 Console** button. This gives you a terminal session directly on the server, bypassing SSH entirely. From there you can fix SSH configuration, firewall rules, or user accounts.

**Optional: IPv6.** Some RackNerd locations support IPv6. If you need it, submit a support ticket. Availability varies by plan and location -- verify in the RackNerd portal or by support ticket.

**Optional: SSH port change.** Some operators change the SSH port from 22 to a non-standard port as a minor hardening step. This guide uses port 22 throughout. If you change it, adjust all SSH/SFTP commands and UFW rules accordingly.

---

## Phase 1: DNS Configuration

Before touching the server, configure DNS so records have time to propagate.

### 1.1 Create A records

Log into your domain registrar's DNS management panel and create three A records, all pointing to your VPS IP address:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | `@` (or blank) | `YOUR_SERVER_IP` | 300 (5 min) or Auto |
| A | `www` | `YOUR_SERVER_IP` | 300 or Auto |
| A | `lp` | `YOUR_SERVER_IP` | 300 or Auto |

Replace `YOUR_SERVER_IP` with the IP address from your RackNerd welcome email.

- The `@` record handles `csedesigns.com`
- The `www` record handles `www.csedesigns.com`
- The `lp` record handles `lp.csedesigns.com`

> **`glow.bits-acb.org` requires a separate DNS record.** Log into the registrar for `bits-acb.org` and add an A record with host `glow` pointing to `YOUR_SERVER_IP`. This is a different DNS zone and cannot be configured through the `csedesigns.com` registrar.

### 1.1b Additional DNS records (recommended)

Beyond the three A records, add these records for TLS security and email anti-spoofing. These are included in the BIND zone file at `csedesigns.com.zone` in the repository root.

| Type | Name | Value | Purpose |
|------|------|-------|---------|
| CAA | `@` | `0 issue "letsencrypt.org"` | Only Let's Encrypt may issue TLS certificates |
| CAA | `@` | `0 issuewild ";"` | Block wildcard certificate issuance |
| TXT | `@` | `v=spf1 -all` | No mail servers authorized (prevents spoofing) |
| TXT | `_dmarc` | `v=DMARC1; p=reject; sp=reject; adkim=s; aspf=s` | Reject unauthenticated mail |

**Why CAA?** Without a CAA record, any certificate authority can issue certificates for your domain. The CAA record restricts issuance to Let's Encrypt only, which is what Caddy uses. Subdomains like `glow.bits-acb.org` inherit the CAA policy -- Let's Encrypt walks up the domain tree and finds the permission at `csedesigns.com`. The `issuewild ";"` entry blocks wildcard certificates (`*.csedesigns.com`), which are not needed in this deployment.

**Why SPF and DMARC with no mail server?** If you do not send email from this domain, attackers can still forge the `From:` address in spam. An SPF `-all` record tells receiving mail servers that no server is authorized to send mail for `csedesigns.com`, and the DMARC `reject` policy instructs receivers to discard any mail that claims to be from your domain.

> **If you later add a mail server**, update the SPF record to include it (e.g., `v=spf1 mx -all`) and adjust the DMARC policy accordingly.

### 1.1c Zone file alternative

The repository includes a BIND zone file at `csedesigns.com.zone` with all the records above pre-configured for IP address `107.175.91.158`. You can use it in two ways:

**Option A: Import** -- If your DNS provider supports BIND zone file import, upload `csedesigns.com.zone` directly. WordPress.com DNS may or may not support BIND import -- if it fails, use Option B.

**Option B: Manual reference** -- Open `csedesigns.com.zone` and add each record manually through your registrar's DNS panel using the values in the file.

After adding records by either method, continue with Step 1.2 to verify propagation.

### 1.2 Verify DNS propagation

After creating the records, wait a few minutes and verify from your local machine:

```bash
# On macOS/Linux:
dig +short csedesigns.com
dig +short www.csedesigns.com
dig +short glow.bits-acb.org

# On Windows PowerShell:
Resolve-DnsName csedesigns.com
Resolve-DnsName www.csedesigns.com
Resolve-DnsName glow.bits-acb.org
```

All three should return your VPS IP address. If they do not, wait and check again. DNS propagation typically takes 5--30 minutes but can take longer depending on TTL and registrar.

You can also check from multiple locations using `https://dnschecker.org`.

> **Do not proceed to Phase 5 (Build and Launch) until DNS is verified.** Caddy will fail to issue TLS certificates if DNS does not resolve to your server.

---

## Phase 2: Server Bootstrap (One-Time)

This phase hardens the server and prepares it for Docker. Run these steps once when setting up a new VPS.

> **Automation available:** The `scripts/bootstrap-server.sh` script (see Appendix A) automates most of this phase. You can run it after connecting as root, or follow the manual steps below.

### 2.1 Connect as root

Using the IP address and root password from your RackNerd welcome email:

```bash
ssh root@YOUR_SERVER_IP
```

Accept the host key fingerprint when prompted. Enter the root password.

### 2.2 Update the system and install base packages

```bash
apt update

DEBIAN_FRONTEND=noninteractive apt-get \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold" \
  -y full-upgrade

apt-get -y autoremove --purge
apt-get -y autoclean
```

`full-upgrade` promotes held-back packages (unlike `upgrade`). The `Dpkg` options keep existing config files when a package ships a new default, preventing interactive prompts. `autoremove --purge` cleans up orphaned packages and their config files.

Install packages that this guide's commands require:

```bash
apt install -y \
  git \
  curl \
  ca-certificates \
  unzip \
  dnsutils \
  python3 \
  software-properties-common \
  gnupg \
  lsb-release
```

These provide: `git` (code checkout), `curl` (HTTP testing), `dig` (DNS verification), `python3` (secret generation), and dependencies for Docker installation.

Reboot to pick up any kernel updates, then reconnect:

```bash
reboot
```

Wait 30--60 seconds, then:

```bash
ssh root@YOUR_SERVER_IP
```

> **Fix "unable to resolve host" warnings:** If you changed the server's hostname (e.g., via `hostnamectl set-hostname bishoplink`) and every `sudo` command prints `sudo: unable to resolve host yourname: Name or service not known`, the new hostname is not in `/etc/hosts`. Fix it:
>
> ```bash
> echo "127.0.1.1 $(hostname)" >> /etc/hosts
> ```
>
> Verify the warning is gone:
>
> ```bash
> sudo whoami
> ```
>
> This should print `root` with no warning. If you have not changed the hostname, you can skip this.

### 2.3 Create a non-root deploy user

```bash
adduser deploy
```

This prompts for a password and optional user details. Set a strong password and press Enter through the optional fields.

Then add the user to the sudo group:

```bash
usermod -aG sudo deploy
```

### Choose Your Authentication Method

Steps 2.4 through 2.6 set up **SSH key authentication** and then disable password login. This is the most secure path. However, if you prefer to keep using password login, follow the **Password-Only Alternative** instead.

| Path | Steps | Result |
|------|-------|--------|
| **SSH key login** (recommended) | Follow 2.4, 2.5, 2.6 as written | Key-based login only, no passwords accepted |
| **Password login** | Skip to 2.4b, 2.5b, 2.6b below | Password login for `deploy`, root SSH disabled |

> **Security note:** SSH keys are stronger than passwords because they cannot be brute-forced remotely. If you choose password login, use a strong password and rely on fail2ban (Step 2.8) to limit brute-force attempts.

---

#### Path A: SSH Key Login (Steps 2.4 -- 2.6)

Follow Steps 2.4, 2.5, and 2.6 below. After completing Step 2.6, skip ahead to Step 2.7.

### 2.4 Copy your SSH key to the deploy user

**From your local machine** (not the server), copy your public key:

On macOS or Linux:

```bash
ssh-copy-id deploy@YOUR_SERVER_IP
```

On Windows PowerShell (`ssh-copy-id` is not available by default):

```powershell
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh deploy@YOUR_SERVER_IP "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

If your key is `id_rsa.pub` instead of `id_ed25519.pub`, adjust the filename.

**Alternative: paste the key manually on the server.** If the above commands fail, stay connected as root on the server and run:

```bash
mkdir -p /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
nano /home/deploy/.ssh/authorized_keys
```

Paste your public key (the contents of `~/.ssh/id_ed25519.pub` from your local machine) into the file, save, then:

```bash
chmod 600 /home/deploy/.ssh/authorized_keys
chown -R deploy:deploy /home/deploy/.ssh
```

### 2.5 Verify key-based login in a second terminal

> **WARNING: Do not skip this step.** The next step disables password login. If your key is not working, you will be locked out of the server.

**Open a new, separate terminal window** on your local machine and verify:

```bash
ssh deploy@YOUR_SERVER_IP
```

This must connect **without asking for a password**. If it asks for a password, your key was not copied correctly. Go back to Step 2.4 and fix it before proceeding.

Once connected, verify sudo works:

```bash
sudo whoami
```

Expected output: `root`

**Keep this second terminal open** as a safety net while you harden SSH in the next step.

### 2.6 Harden SSH configuration

> **WARNING: These commands disable password authentication and root login over SSH. If your SSH key is not working (Step 2.5), you will be locked out. Use the SolusVM VNC console at `https://nerdvm.racknerd.com/` to recover if this happens.**

Back in your original root terminal:

```bash
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd
```

**Immediately test** by opening yet another terminal on your local machine:

```bash
ssh deploy@YOUR_SERVER_IP
```

If this works with key authentication (no password prompt), SSH hardening is complete. If it fails, use the SolusVM HTML5 VNC console to edit `/etc/ssh/sshd_config` and restore `PasswordAuthentication yes` temporarily.

After completing Step 2.6, skip ahead to Step 2.7.

---

#### Path B: Password-Only Login (Steps 2.4b -- 2.6b)

Use this path if you do **not** want to set up SSH keys. You will log in as the `deploy` user with a password.

> **If you chose Path A (SSH key login), skip this entire section and continue at Step 2.7.**

### 2.4b Verify password login as deploy

**From Windows PowerShell** on your local machine (not the server):

```powershell
ssh deploy@YOUR_SERVER_IP
```

Enter the password you created for `deploy` in Step 2.3 when prompted.

Once connected, verify sudo works:

```bash
sudo whoami
```

Expected output: `root`

If this works, the `deploy` user is correctly set up. Type `exit` to return to your local machine.

---

## Admin Bootstrap (password-only)

When you need quick, local-only administrative access without configuring email or SSO, the application supports a bootstrap password. This is intended for emergency or short-term operator access only — use a strong secret and rotate it regularly.

- **Env var names (priority):** `ADMIN_PASSWORD` → `ADMIN_LOCAL_PASSWORD` → fallback to `ssh_password` in `server.credentials`.
- **How it works:** On first access to the admin routes (or when the app is restarted and the admin login page is visited), the app runs a bootstrap helper that will create or update an approved admin account for the bootstrap email configured via `ADMIN_LOCAL_EMAIL` and store a hashed password in `instance/admin_auth.db`.

Examples (set for current shell):

PowerShell (temporary for current session):
```powershell
$env:ADMIN_PASSWORD = "YourStr0ngSecretHere"
# restart the Flask app or rebuild/start your container after setting this
```

WSL / bash (temporary for current session):
```bash
export ADMIN_PASSWORD="YourStr0ngSecretHere"
# restart the Flask app or rebuild/start your container after setting this
```

Persisting in Docker Compose (recommended for dev):
```yaml
services:
  web:
    environment:
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
```
Or place `ADMIN_PASSWORD=YourStr0ngSecretHere` in a `.env` file consumed by `docker compose`.

Verification (does not reveal the password):

1. Confirm a local admin account exists and whether it has a password hash (shows `1` when present):
```bash
python - <<'PY'
import sqlite3, pathlib
from pathlib import Path
p = Path('instance') / 'admin_auth.db'
conn = sqlite3.connect(p)
for row in conn.execute("SELECT email, approved, password_hash IS NOT NULL as has_pw FROM admin_accounts"):
    print(row)
conn.close()
PY
```

2. Visit `/admin/login` in your browser and use the bootstrap email (configurable via `ADMIN_LOCAL_EMAIL`) and the password you set.

Security notes:
- Treat `ADMIN_PASSWORD` like any secret; do not check it into git or log it.
- Use environment variables or secret managers in production (e.g., systemd drop-ins, Docker secrets, or cloud secret stores).
- Rotate the bootstrap password regularly and remove it from environment files when not needed.


### 2.5b Harden SSH for password login

> **WARNING: Keep your current root terminal open as a safety net while making these changes. If something goes wrong, use the SolusVM VNC console at `https://nerdvm.racknerd.com/` to recover.**

In your **root** terminal on the server, disable root SSH login but keep password authentication enabled:

```bash
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart ssh || systemctl restart sshd
```

### 2.6b Verify hardened SSH

**Open a new terminal** on your local machine and test:

```powershell
ssh deploy@YOUR_SERVER_IP
```

This should connect after you enter the `deploy` password.

Now confirm root login is blocked:

```powershell
ssh root@YOUR_SERVER_IP
```

This should be rejected with `Permission denied`. If root login still works, re-check `/etc/ssh/sshd_config` and restart sshd.

> **Important:** Never share your `deploy` password in chat, email, or any insecure channel. Type it only when your SSH client prompts for it.

After completing Step 2.6b, continue with Step 2.7.

---

### 2.7 Configure the firewall

From your deploy user session (or the root session):

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
sudo ufw status verbose
```

Expected output should show rules for OpenSSH, 80/tcp, and 443/tcp with status `active`.

> **If you changed the SSH port**, replace `sudo ufw allow OpenSSH` with `sudo ufw allow YOUR_PORT/tcp`.

### 2.8 Install and configure fail2ban

Fail2ban monitors logs and temporarily blocks IP addresses with repeated failed login attempts.

```bash
sudo apt install -y fail2ban
```

Create a local configuration:

```bash
sudo tee /etc/fail2ban/jail.local > /dev/null << 'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 3600
findtime = 600
EOF
```

Start and enable:

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
sudo fail2ban-client status sshd
```

Expected output: the jail is active with 0 currently banned IPs.

### 2.9 Enable automatic security updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Select **Yes** when prompted. This enables automatic installation of security patches.

### 2.10 Create a swap file

A swap file prevents out-of-memory kills when Docker builds or document processing temporarily spike memory usage. Recommended for VPS plans with 4 GB RAM or less. Still useful on 8 GB plans as a safety net.

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Verify:

```bash
free -h
```

Expected: the Swap line shows `2.0Gi` total.

### 2.11 Create the directory structure

```bash
sudo -u deploy mkdir -p /home/deploy/app
sudo -u deploy mkdir -p /home/deploy/backups
```

Or if already logged in as deploy:

```bash
mkdir -p ~/app
mkdir -p ~/backups
```

### Phase 2 Validation

At this point you should have:

- [ ] Login as `deploy` via SSH key (Path A) or password (Path B)
- [ ] Root SSH login disabled
- [ ] Password authentication disabled (Path A) or enabled (Path B)
- [ ] UFW active with ports 22, 80, 443 open
- [ ] fail2ban protecting SSH
- [ ] Automatic security updates enabled
- [ ] Swap file active

---

## Phase 3: Install Docker (One-Time)

### 3.1 Install Docker Engine and Compose plugin

Log in as the deploy user:

```bash
ssh deploy@YOUR_SERVER_IP
```

Install Docker using the official repository:

```bash
# Add Docker's official GPG key and repository
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 3.2 Allow the deploy user to run Docker

```bash
sudo usermod -aG docker deploy
```

**You must log out and back in** for the group change to take effect:

```bash
exit
ssh deploy@YOUR_SERVER_IP
```

### 3.3 Verify Docker works

```bash
docker run --rm hello-world
docker compose version
```

Both commands should succeed. The `hello-world` output confirms the Docker engine is running. The `compose version` output confirms the Compose plugin is installed.

Enable Docker to start on boot (usually already enabled, but confirm):

```bash
sudo systemctl enable docker
```

### Phase 3 Validation

- [ ] `docker run --rm hello-world` succeeds without sudo
- [ ] `docker compose version` prints a version number

---

## Phase 4: Upload and Configure the Application

### 4.1 Upload files to the server

The application code must be present on the server before building. Choose one method.

#### Option A: Git clone (recommended if the repository is accessible)

```bash
ssh deploy@YOUR_SERVER_IP
cd ~
git clone https://github.com/Community-Access/glow.git app
cd app
```

If the repository is private, configure SSH keys for GitHub or use a personal access token.

#### Option B: SFTP upload

Use this method if you prefer not to use git on the server, or if you are deploying from a local copy.

The Docker build requires these directories from the repository:

```
app/
  web/
    Dockerfile
    docker-compose.prod.yml
    pyproject.toml
    requirements.txt
    src/
  desktop/
    pyproject.toml
    src/
  scripts/
    bootstrap-server.sh
    deploy-app.sh
    backup-feedback.sh
    restore-feedback.sh
```

**From your local machine** (terminal SFTP example):

```bash
# Connect
sftp deploy@YOUR_SERVER_IP

# Create directories if they do not already exist
sftp> mkdir app
sftp> mkdir app/web
sftp> mkdir app/desktop
sftp> mkdir app/scripts

# Upload the web directory
sftp> put -r web/ app/web/

# Upload the desktop directory (needed for Docker build)
sftp> put -r desktop/ app/desktop/

# Upload scripts
sftp> put -r scripts/ app/scripts/

sftp> exit
```

**With WinSCP or another GUI client:** Connect using SFTP protocol, navigate to `/home/deploy/`, and drag the `web/`, `desktop/`, and `scripts/` folders into the `app/` directory.

After uploading, set scripts as executable via SSH:

```bash
ssh deploy@YOUR_SERVER_IP "chmod 700 ~/app/scripts/*.sh"
```

Verify the upload:

```bash
ssh deploy@YOUR_SERVER_IP "ls -la ~/app/web/ && ls -la ~/app/desktop/"
```

You should see `Dockerfile`, `docker-compose.prod.yml`, `pyproject.toml`, and `src/` in the web directory, and `pyproject.toml` and `src/` in the desktop directory.

### 4.2 Create the production environment file (.env)

The `.env` file contains secrets and configuration that the Flask application reads at runtime. Docker Compose injects these into the container via the `env_file:` directive in the production compose file.

If the server does not already have `web/.env`, `scripts/deploy-app.sh` now seeds it from `web/.env.example` and generates fresh values for `SECRET_KEY`, `KEYCLOAK_CLIENT_SECRET`, and `KEYCLOAK_ADMIN_PASSWORD` so the stack can start cleanly instead of failing at compose time. Review the generated file before enabling optional features such as feedback-to-GitHub sync or OpenRouter-backed AI features.

Keycloak now runs as part of the production Compose stack at `https://lp.csedesigns.com/auth`. The deploy script renders `web/keycloak/import/glow-realm.json` from `web/keycloak/realm.template.json`, and Compose mounts the entire generated import directory so stale template files in the persistent volume are never imported.

Keycloak/OIDC login is configured through `KEYCLOAK_HOSTNAME`, `KEYCLOAK_BASE_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`, `KEYCLOAK_REDIRECT_URI`, and `KEYCLOAK_ADMIN_PASSWORD`. Those values are used by the web app and Keycloak container at startup.

```bash
cd ~/app/web
nano .env
```

Paste the following, replacing the placeholder values:

```
SECRET_KEY=PASTE_GENERATED_KEY_HERE
FEEDBACK_PASSWORD=CHOOSE_A_STRONG_PASSWORD
FEEDBACK_GITHUB_TOKEN=PASTE_GITHUB_TOKEN_FOR_ISSUE_SYNC
FEEDBACK_GITHUB_REPO=Community-Access/glow
FEEDBACK_GITHUB_ASSIGNEE=accesswatch
FEEDBACK_GITHUB_LABELS=feedback,user-feedback
OPENROUTER_API_KEY=PASTE_OPENROUTER_KEY_HERE
POSTMARK_SERVER_TOKEN=PASTE_POSTMARK_SERVER_TOKEN
POSTMARK_FROM_EMAIL=reports@glow.bits-acb.org
ADMIN_LOCAL_EMAIL=jeff@jeffbishop.com
ADMIN_LOCAL_PASSWORD=CHOOSE_A_STRONG_PASSWORD
ADMIN_BOOTSTRAP_EMAILS=jeff@jeffbishop.com
ADMIN_MAGIC_LINK_TTL_MINUTES=20
LOG_LEVEL=INFO
KEYCLOAK_HOSTNAME=lp.csedesigns.com
KEYCLOAK_BASE_URL=https://lp.csedesigns.com/auth
KEYCLOAK_REALM=glow
KEYCLOAK_CLIENT_ID=glow-web
KEYCLOAK_CLIENT_SECRET=PASTE_GENERATED_KEY_HERE
KEYCLOAK_REDIRECT_URI=https://lp.csedesigns.com/authorize
KEYCLOAK_ADMIN_PASSWORD=PASTE_GENERATED_KEY_HERE
```

Optional resilience tuning for AI-heavy workloads (recommended for large files and peak traffic):

```
OPENROUTER_MAX_RETRIES=2
OPENROUTER_RETRY_BASE_SECONDS=1.0
GLOW_AI_QUEUE_WAIT_SECONDS=25
GLOW_VISION_QUEUE_WAIT_SECONDS=20
GLOW_AUDIO_QUEUE_WAIT_SECONDS=0
```

- `OPENROUTER_MAX_RETRIES` and `OPENROUTER_RETRY_BASE_SECONDS` control transient retry/backoff for OpenRouter chat and vision calls.
- `GLOW_AI_QUEUE_WAIT_SECONDS` and `GLOW_VISION_QUEUE_WAIT_SECONDS` allow short bounded queue waits instead of immediate 503 responses under burst load.
- `GLOW_AUDIO_QUEUE_WAIT_SECONDS` defaults to `0` because BITS Whisperer already has an explicit job queue and background processing flow.

If you are deploying from a trusted local checkout that includes `server.credentials`, use it only as a source to manually copy the OpenRouter key and bootstrap password into `.env`. Do not upload `server.credentials` to the server, do not commit it, and do not reference it from Docker Compose in production.

Generate a secure `SECRET_KEY`:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as the `SECRET_KEY` value in the `.env` file.

Save and restrict permissions:

```bash
chmod 600 ~/app/web/.env
```

> **How .env works with Docker Compose:** Docker Compose has two `.env` mechanisms. First, it automatically reads a `.env` file next to the compose file for variable interpolation (`${VAR}` syntax inside the compose file itself). Second, the `env_file:` directive passes all variables from the specified file into the container as actual environment variables. This guide uses the second mechanism. The `env_file: .env` line in `docker-compose.prod.yml` injects `SECRET_KEY`, `FEEDBACK_PASSWORD`, `FEEDBACK_GITHUB_TOKEN`, `FEEDBACK_GITHUB_REPO`, `FEEDBACK_GITHUB_ASSIGNEE`, `FEEDBACK_GITHUB_LABELS`, `OPENROUTER_API_KEY`, `POSTMARK_SERVER_TOKEN`, `POSTMARK_FROM_EMAIL`, `ADMIN_LOCAL_EMAIL`, `ADMIN_LOCAL_PASSWORD`, `ADMIN_BOOTSTRAP_EMAILS`, `ADMIN_MAGIC_LINK_TTL_MINUTES`, and `LOG_LEVEL` directly into the running container, where the Flask app reads them via `os.environ.get()`.

### 4.2a OpenRouter wiring

1. Create or obtain an OpenRouter API key from the operator account.
2. Paste it into `.env` as `OPENROUTER_API_KEY`.
3. Leave the web compose file unchanged; the application reads this value automatically at runtime for chat and Whisperer transcription.
4. Restart the stack after updating `.env`:

```bash
cd ~/app/web
docker compose -f docker-compose.prod.yml up -d --build
```

6. Verify provider reachability:

```bash
curl -s https://glow.bits-acb.org/health
```

The JSON should show `services.openrouter.status` as `ok`, `services.keycloak.status` as `ok`, and, if Whisper is configured, `services.whisper.status` as `ok`.

### 4.2b Bootstrap the Jeff Bishop admin account

Set these values in `.env`:

```
ADMIN_LOCAL_EMAIL=jeff@jeffbishop.com
ADMIN_LOCAL_PASSWORD=YOUR_BOOTSTRAP_PASSWORD
```

On first app start, GLOW creates or updates this approved admin account and stores only the password hash in the admin database. Use the password sign-in form at `/admin/login` to access the admin queue and settings areas.

> **Important:** The `.env` file contains secrets. Do not commit it to version control. If you cloned the repository, verify that `.env` is listed in `.gitignore`.

### 4.3 Create the Caddyfile

The Caddyfile configures Caddy to serve both the main website and the Flask application.

If the repository includes `web/Caddyfile.example`, copy and edit it:

```bash
cp ~/app/web/Caddyfile.example ~/app/web/Caddyfile
nano ~/app/web/Caddyfile
```

Otherwise, create it from scratch:

```bash
nano ~/app/web/Caddyfile
```

Paste the following content. If your domains differ from `csedesigns.com` and `glow.bits-acb.org`, replace them:

```
# Main website -- static files
csedesigns.com, www.csedesigns.com {
    root * /srv/www
    file_server
    encode gzip

    header {
        X-Content-Type-Options nosniff
        X-Frame-Options SAMEORIGIN
        Referrer-Policy strict-origin-when-cross-origin
    }
}

# ACB Large Print web application -- reverse proxy to Flask/Gunicorn
glow.bits-acb.org {
    reverse_proxy web:8000
    encode gzip

    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
        Permissions-Policy "geolocation=(), microphone=(), camera=()"
        Content-Security-Policy "default-src 'none'; style-src 'self'; img-src 'self'; font-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        Strict-Transport-Security "max-age=63072000; includeSubDomains"
    }
}
```

**Key details:**

- Caddy obtains separate TLS certificates for each hostname automatically.
- The main site block serves static files from `/srv/www` inside the Caddy container, which maps to `~/app/web/www/` on the host (via the Docker volume mount).
- The app site block reverse-proxies to the `web` container on the Docker network. `web:8000` is the Docker service name and internal port -- not a public address.
- If the main site is not yet built, the placeholder from Step 4.4 is served. You can replace it later without restarting Caddy.

> **Note on HSTS preload:** The HSTS header above does not include `preload`. Adding `preload` and submitting to the HSTS preload list is a serious, hard-to-reverse commitment. Only add it after you are confident HTTPS will always be available for all subdomains.

### 4.4 Create a placeholder for the main website

Caddy serves `csedesigns.com` from a `www/` directory. Create it with a placeholder page:

```bash
mkdir -p ~/app/web/www

cat > ~/app/web/www/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CSE Designs</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            font-size: 1.125rem;
            line-height: 1.5;
            max-width: 40rem;
            margin: 2rem auto;
            padding: 0 1rem;
            color: #1a1a1a;
        }
        h1 { font-size: 1.5rem; }
    </style>
</head>
<body>
    <h1>CSE Designs</h1>
    <p>Site coming soon.</p>
</body>
</html>
EOF
```

Replace this file with your real site content at any time. Caddy serves files from this directory without needing a restart.

### 4.5 Understand the Docker Compose configuration

The repository includes `web/docker-compose.prod.yml`, which defines the production stack. Here is the complete file for reference:

```yaml
# Production Docker Compose -- Caddy reverse proxy + Flask/Gunicorn
# File: web/docker-compose.prod.yml
#
# Usage:
#   cd ~/app/web
#   docker compose -f docker-compose.prod.yml up -d --build

services:
  web:
    build:
      context: ..
      dockerfile: web/Dockerfile
    expose:
      - "8000"
    env_file: .env
    environment:
      - FLASK_DEBUG=0
    volumes:
      - feedback-data:/app/instance
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
      - "443:443/udp"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./www:/srv/www:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      web:
        condition: service_healthy

volumes:
  feedback-data:
  caddy_data:
  caddy_config:
```

**Key points about this configuration:**

- **`expose: ["8000"]`** makes port 8000 available to other containers on the Docker network, but **not** to the public internet. Only Caddy can reach the Flask app. This is intentional -- do not change it to `ports:` in production.
- **`env_file: .env`** injects all variables from `.env` into the container as environment variables. The `environment:` block adds `FLASK_DEBUG=0` as a non-secret default.
- **`depends_on: web: condition: service_healthy`** prevents Caddy from starting until the Flask health check passes.
- **`feedback-data`** is a Docker named volume that persists the SQLite database across container restarts and rebuilds. Do not delete this volume unless you intend to lose all feedback data.
- **`caddy_data`** stores TLS certificates. Do not delete this volume or you may hit Let's Encrypt rate limits when re-issuing certificates.
- **`context: ..`** means the Docker build context is the parent of `web/` (the repository root). This is why `desktop/` must also be present on the server at `~/app/desktop/`.
- The `healthcheck` command runs **inside** the web container, so `http://localhost:8000/health` refers to the Gunicorn process in that container. This works correctly regardless of whether the port is published to the host.

---

## Phase 5: Build and Launch

### 5.1 Build and start containers

```bash
cd ~/app/web
docker compose -f docker-compose.prod.yml up -d --build
```

This builds the Flask/Gunicorn image and pulls the Caddy image. The first build takes 1--3 minutes depending on VPS speed and network.

### 5.2 Validate the deployment

**Check container status:**

```bash
docker compose -f docker-compose.prod.yml ps
```

Expected: both `web` and `caddy` show status `Up` (web may show `Up (healthy)` after the health check passes).

**Check the web container health directly:**

```bash
docker compose -f docker-compose.prod.yml exec web python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
```

Expected output: `ok`

> **Why not `curl http://localhost:8000/health` from the host?** Because the web container uses `expose:` instead of `ports:`, port 8000 is not published to the host network. Use the `docker compose exec` command above, or test through Caddy as shown below.

**Check through Caddy** (requires DNS to be propagated):

```bash
curl -s https://glow.bits-acb.org/health
```

Expected output: `ok`

**Check the main site:**

```bash
curl -s https://csedesigns.com/ | head -5
```

Expected: the first few lines of your placeholder `index.html`.

**View container logs if anything looks wrong:**

```bash
# Flask/Gunicorn logs
docker compose -f docker-compose.prod.yml logs web --tail 30

# Caddy logs
docker compose -f docker-compose.prod.yml logs caddy --tail 30

# All logs
docker compose -f docker-compose.prod.yml logs --tail 30
```

### 5.3 Test from a browser

Open these URLs in a browser:

1. `https://csedesigns.com/` -- should show your main site (or placeholder)
2. `https://www.csedesigns.com/` -- should show the same content
3. `https://glow.bits-acb.org/` -- should show the ACB Large Print Tool landing page
4. `https://glow.bits-acb.org/health` -- should show `ok`
5. `http://glow.bits-acb.org/` -- should redirect to HTTPS automatically

### Phase 5 Validation

- [ ] Both containers running (`docker compose ps` shows `Up`)
- [ ] Health endpoint returns `ok` through Caddy
- [ ] Main site loads over HTTPS
- [ ] Flask app loads over HTTPS
- [ ] HTTP redirects to HTTPS

---

## Phase 6: TLS Certificates

Caddy handles TLS automatically. No manual certificate management is required.

### 6.1 How Caddy handles TLS

When Caddy starts with real domain names in the Caddyfile:

1. It requests free TLS certificates from Let's Encrypt via the ACME protocol
2. It configures TLS 1.2+ with strong cipher suites
3. It redirects all HTTP (port 80) traffic to HTTPS (port 443)
4. It renews certificates automatically 30 days before expiry
5. It enables HTTP/2, HTTP/3 (QUIC), and OCSP stapling

Caddy obtains separate certificates for each hostname: `csedesigns.com`, `www.csedesigns.com`, and `glow.bits-acb.org`.

### 6.2 Verify TLS is working

After starting the containers, wait 30--60 seconds for certificate issuance, then:

```bash
# Check certificate details
curl -vI https://glow.bits-acb.org 2>&1 | grep -E 'subject:|expire|issuer:'

# Verify HTTP-to-HTTPS redirect
curl -sI http://glow.bits-acb.org | head -5
```

Expected: the issuer line contains "Let's Encrypt" and the HTTP request returns a `301` redirect to `https://`.

To check your TLS grade externally, test at `https://www.ssllabs.com/ssltest/analyze.html?d=glow.bits-acb.org`.

### 6.3 Using Let's Encrypt staging (for testing)

If you want to test certificate issuance without hitting Let's Encrypt production rate limits (5 certificates per registered domain per week), add this global block at the **top** of your Caddyfile:

```
{
    acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
}
```

Staging certificates are not trusted by browsers (you will see a security warning), but they confirm the ACME flow works. **Remove this block and restart Caddy** to switch back to production certificates:

```bash
cd ~/app/web
docker compose -f docker-compose.prod.yml restart caddy
```

### 6.4 Custom certificates (optional)

If you need to use a certificate from a different CA (not Let's Encrypt), update the relevant site block in your Caddyfile:

```
glow.bits-acb.org {
    tls /etc/caddy/certs/cert.pem /etc/caddy/certs/key.pem
    reverse_proxy web:8000
    encode gzip
    # ... rest of headers
}
```

Place your certificate files in `~/app/web/certs/` and add a volume mount to the `caddy` service in the compose file:

```yaml
  caddy:
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - ./certs:/etc/caddy/certs:ro
      - ./www:/srv/www:ro
      - caddy_data:/data
      - caddy_config:/config
```

---

## Phase 7: Auto-Restart on Reboot

Docker's `restart: unless-stopped` policy in the compose file handles automatic container restarts. Confirm Docker itself starts on boot:

```bash
sudo systemctl enable docker
```

Test by rebooting:

```bash
sudo reboot
```

After reconnecting (wait 30--60 seconds):

```bash
ssh deploy@YOUR_SERVER_IP
docker compose -f ~/app/web/docker-compose.prod.yml ps
```

Both containers should show `Up`. If they do not:

```bash
cd ~/app/web
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs --tail 30
```

---

## Phase 8: Monitoring

### 8.1 UptimeRobot (recommended)

UptimeRobot provides free external uptime monitoring with email and SMS alerts.

1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. Add a new monitor:
   - **Type:** HTTP(s)
   - **URL:** `https://glow.bits-acb.org/health`
   - **Interval:** 5 minutes
3. Optionally add a second monitor for `https://csedesigns.com/`
4. Configure alert contacts (email, SMS, or webhook)

### 8.2 Disk usage monitoring

Add a simple disk check to the deploy user's crontab:

```bash
crontab -e
```

Add this line to log a warning if root filesystem usage exceeds 80%:

```
0 6 * * * df -h / | awk 'NR==2 && int($5)>80' >> /home/deploy/disk-alerts.log 2>&1
```

Check the log periodically:

```bash
cat ~/disk-alerts.log
```

> **Want email alerts?** Install a lightweight SMTP relay like `msmtp`:
>
> ```bash
> sudo apt install -y msmtp msmtp-mta
> ```
>
> Then configure `/etc/msmtprc` with your outbound mail provider's SMTP settings (Gmail App Password, SendGrid, Mailgun, etc.). This requires an external SMTP account and is optional. A full mail server setup is outside the scope of this guide.

---

## SFTP Operations Reference

SFTP (SSH File Transfer Protocol) runs over your existing SSH connection. No additional software, passwords, or open ports are needed.

> **Never use FTP or FTPS.** Plain FTP transmits credentials in cleartext. SFTP is encrypted and uses your existing SSH key.

### Connecting via SFTP

```bash
sftp deploy@YOUR_SERVER_IP
```

This uses the same SSH credentials from Phase 2 (key or password). Once connected, you see the `sftp>` prompt.

### Common operations

| Task | Command |
|------|---------|
| Upload a single file | `sftp> put local-file.txt /home/deploy/app/web/` |
| Upload a folder recursively | `sftp> put -r ./web /home/deploy/app/web` |
| Download a single file | `sftp> get /home/deploy/backups/feedback-20260411.db ./` |
| Download a folder | `sftp> get -r /home/deploy/backups ./local-backups` |
| List remote directory | `sftp> ls -la /home/deploy/app/web/` |
| Change remote directory | `sftp> cd /home/deploy/app/web` |
| Show current remote directory | `sftp> pwd` |
| Create remote directory | `sftp> mkdir /home/deploy/app/web/www` |
| Delete a remote file | `sftp> rm /home/deploy/app/web/old-file.txt` |
| Exit | `sftp> exit` |

### Uploading updated app files

When deploying a code update without git:

```bash
sftp deploy@YOUR_SERVER_IP
sftp> put -r ./web/src /home/deploy/app/web/src
sftp> put ./web/pyproject.toml /home/deploy/app/web/
sftp> put ./web/requirements.txt /home/deploy/app/web/
sftp> exit
```

Then rebuild via SSH:

```bash
ssh deploy@YOUR_SERVER_IP "cd ~/app/web && docker compose -f docker-compose.prod.yml up -d --build"
```

### Uploading and running scripts

```bash
sftp deploy@YOUR_SERVER_IP
sftp> put -r ./scripts /home/deploy/app/scripts
sftp> exit
```

Then set permissions via SSH:

```bash
ssh deploy@YOUR_SERVER_IP "chmod 700 ~/app/scripts/*.sh"
```

> **Why use SSH for permissions?** Some SFTP clients support setting file permissions during upload, but behavior varies by client and platform. Using SSH commands after upload is consistent and verifiable. Always confirm permissions with `ls -l` or `stat` after upload.

### Downloading a backup

```bash
sftp deploy@YOUR_SERVER_IP
sftp> cd /home/deploy/backups
sftp> ls -la
sftp> get feedback-20260411-020000.db ./local-backups/
sftp> exit
```

### Replacing a configuration file

```bash
sftp deploy@YOUR_SERVER_IP
sftp> put ./Caddyfile /home/deploy/app/web/Caddyfile
sftp> exit
```

Then restart Caddy to pick up the change:

```bash
ssh deploy@YOUR_SERVER_IP "cd ~/app/web && docker compose -f docker-compose.prod.yml restart caddy"
```

### Checking ownership and permissions

After uploading files, verify they are owned by the deploy user and have correct permissions:

```bash
ssh deploy@YOUR_SERVER_IP

# List files with ownership and permissions
ls -la ~/app/web/

# Detailed info for a specific file
stat ~/app/web/.env

# Fix ownership if needed (e.g., after uploading as a different user)
sudo chown -R deploy:deploy ~/app/

# Secrets should be readable only by the owner
chmod 600 ~/app/web/.env
```

### GUI client connection settings

For WinSCP, FileZilla, Cyberduck, or any SFTP-capable client:

| Setting | Value |
|---------|-------|
| Protocol | SFTP (SSH File Transfer Protocol) |
| Host | YOUR_SERVER_IP |
| Port | 22 |
| Username | deploy |
| Authentication | SSH private key (Path A) or password (Path B) |

### Directory reference

| Remote path | Contents |
|-------------|----------|
| `/home/deploy/app/` | Repository root (git clone or SFTP upload root) |
| `/home/deploy/app/web/` | Flask app, Dockerfile, compose files, Caddyfile, .env |
| `/home/deploy/app/web/src/` | Flask application source code |
| `/home/deploy/app/web/www/` | Static files for csedesigns.com |
| `/home/deploy/app/desktop/` | Python core library (needed for Docker build) |
| `/home/deploy/app/scripts/` | Deployment helper scripts |
| `/home/deploy/backups/` | Feedback database backups |

### Restricting SFTP to a specific directory (optional)

If you want to allow SFTP access only to the app directory (not the full filesystem), create a restricted user with a chroot jail. Add to `/etc/ssh/sshd_config`:

```bash
Match User sftponly
    ChrootDirectory /home/deploy/app
    ForceCommand internal-sftp
    AllowTcpForwarding no
    X11Forwarding no
```

Then create the restricted user:

```bash
sudo adduser sftponly --shell /usr/sbin/nologin
sudo usermod -aG docker sftponly
sudo chown root:root /home/deploy/app
sudo chmod 755 /home/deploy/app
sudo systemctl restart sshd
```

This is optional -- the default `deploy` user with full SSH access is sufficient for most deployments.

---

## Routine Operations

All commands below assume you are logged in as the `deploy` user via SSH. For commands involving the compose file, either `cd ~/app/web` first or use the `-f` flag:

```bash
# Short form (after cd):
cd ~/app/web
docker compose -f docker-compose.prod.yml ps

# Long form (from anywhere):
docker compose -f ~/app/web/docker-compose.prod.yml ps
```

### Deploying updates

**With Git:**

```bash
ssh deploy@YOUR_SERVER_IP
cd ~/app
git pull origin main
cd web
docker compose -f docker-compose.prod.yml up -d --build
```

**With SFTP:** Upload changed files (see SFTP Operations Reference), then:

```bash
ssh deploy@YOUR_SERVER_IP
cd ~/app/web
docker compose -f docker-compose.prod.yml up -d --build
```

**Using the deploy script:**

```bash
ssh deploy@YOUR_SERVER_IP
~/app/scripts/deploy-app.sh
```

`deploy-app.sh` now performs a pre-deploy feedback backup by default and runs a health-check-gated rollback to the previous Git commit when the new revision fails to become healthy.

Control flags:

```bash
# Skip the automatic pre-deploy backup
ENABLE_PREDEPLOY_BACKUP=0 ~/app/scripts/deploy-app.sh
```

The build takes 30--90 seconds. There is a brief downtime (a few seconds) during container restart.

After deploying, verify:

```bash
docker compose -f docker-compose.prod.yml ps
curl -s https://glow.bits-acb.org/health
```

### Viewing logs

```bash
cd ~/app/web

# Flask/Gunicorn logs
docker compose -f docker-compose.prod.yml logs web --tail 50 -f

# Caddy logs
docker compose -f docker-compose.prod.yml logs caddy --tail 50 -f

# All logs
docker compose -f docker-compose.prod.yml logs --tail 50 -f
```

Press `Ctrl+C` to stop following logs.

### Restarting services

```bash
cd ~/app/web

# Restart just the Flask app (Caddy stays up)
docker compose -f docker-compose.prod.yml restart web

# Restart just Caddy (e.g., after a Caddyfile change)
docker compose -f docker-compose.prod.yml restart caddy

# Restart everything
docker compose -f docker-compose.prod.yml restart
```

### Stopping everything

```bash
cd ~/app/web
docker compose -f docker-compose.prod.yml down
```

This stops and removes containers but **preserves volumes** (feedback data and TLS certificates).

> **Do not use `docker compose down -v`** unless you intend to delete all volumes, including the feedback database and TLS certificates.

### Checking disk usage

```bash
# Overall filesystem
df -h /

# Docker-specific (images, containers, volumes)
docker system df

# Detailed Docker disk usage
docker system df -v
```

### Backing up feedback data

Feedback is stored in a SQLite database inside the `feedback-data` Docker volume.

**Manual backup:**

```bash
cd ~/app/web
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
docker compose -f docker-compose.prod.yml cp web:/app/instance/feedback.db ~/backups/feedback-$TIMESTAMP.db
echo "Backup saved: ~/backups/feedback-$TIMESTAMP.db"
```

**Automated daily backups (recommended):**

Use the `backup-feedback.sh` script. Schedule it with cron:

```bash
crontab -e
```

Add this line to run daily at 2 AM:

```
0 2 * * * /home/deploy/app/scripts/backup-feedback.sh >> /home/deploy/backups/backup.log 2>&1
```

The script creates timestamped backups and removes backups older than 30 days. See Appendix A for the full script.

**Download backups to your local machine:**

```bash
sftp deploy@YOUR_SERVER_IP
sftp> cd /home/deploy/backups
sftp> ls -la
sftp> get feedback-20260411-020000.db ./local-backups/
sftp> exit
```

### Restoring feedback data

> **WARNING: Restoring replaces the current feedback database. The web container will be stopped briefly during the restore.**

**Manual restore:**

```bash
cd ~/app/web

# Stop the web container
docker compose -f docker-compose.prod.yml stop web

# Copy the backup into the volume
docker compose -f docker-compose.prod.yml cp ~/backups/feedback-20260411-020000.db web:/app/instance/feedback.db

# Start the web container
docker compose -f docker-compose.prod.yml start web

# Verify
docker compose -f docker-compose.prod.yml exec web python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
```

Expected: `ok`

**Using the restore script:**

```bash
~/app/scripts/restore-feedback.sh ~/backups/feedback-20260411-020000.db
```

The script validates the backup file, stops the container, copies the backup, starts the container, and verifies health. See Appendix A for the full script.

### Reviewing feedback

Set `FEEDBACK_PASSWORD` in your `.env` file (see Phase 4.2), then rebuild and visit:

```
https://glow.bits-acb.org/feedback/review?key=YOUR_PASSWORD
```

### Syncing feedback to GitHub issues

When `FEEDBACK_GITHUB_TOKEN` is configured, each new feedback submission is automatically filed as an issue in `FEEDBACK_GITHUB_REPO`, assigned to `FEEDBACK_GITHUB_ASSIGNEE`, and labeled with `FEEDBACK_GITHUB_LABELS`.

To backfill existing feedback rows from `feedback.db`, run:

```bash
cd ~/app
python3 scripts/sync-feedback-to-github.py --db ~/app/instance/feedback.db --repo Community-Access/glow --assignee accesswatch
```

If your token is not already in the environment, export it first:

```bash
export FEEDBACK_GITHUB_TOKEN=YOUR_TOKEN_HERE
```

### Cleaning up old Docker images

```bash
docker image prune -a --filter "until=720h"
```

This removes images older than 30 days that are not in use by a running container.

### Renewing TLS certificates

Caddy renews certificates automatically 30 days before expiry. No manual action needed. To check certificate expiry:

```bash
curl -vI https://glow.bits-acb.org 2>&1 | grep "expire date"
```

### Updating the server OS

Automatic security updates are enabled (Phase 2.9). Run this monthly for non-security updates:

```bash
sudo apt update && sudo apt upgrade -y
```

Reboot if the kernel was updated:

```bash
sudo reboot
```

After reconnecting, verify containers restarted:

```bash
docker compose -f ~/app/web/docker-compose.prod.yml ps
```

### Updating Docker Engine

```bash
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

---

## Troubleshooting

### DNS not propagated

**Symptom:** `curl https://glow.bits-acb.org` fails with "Could not resolve host" or Caddy logs show certificate issuance failure.

**Diagnosis:**

```bash
dig +short glow.bits-acb.org
dig +short csedesigns.com
```

If the output does not match your VPS IP, DNS has not propagated.

**Fix:** Wait. Propagation typically takes 5--30 minutes but can take up to 48 hours with high TTL values. Verify at your registrar that the A records are correct. Check from multiple locations at `https://dnschecker.org`.

### Caddy certificate issuance failed

**Symptom:** Browser shows "Your connection is not private" or Caddy logs show ACME errors.

**Diagnosis:**

```bash
cd ~/app/web
docker compose -f docker-compose.prod.yml logs caddy --tail 50
```

**Common causes and fixes:**

| Cause | Fix |
|-------|-----|
| DNS not pointing to this server | Verify: `dig +short YOUR_DOMAIN` must return your VPS IP |
| Ports 80/443 blocked by firewall | `sudo ufw status` -- must show 80 and 443 ALLOW |
| Rate limited by Let's Encrypt | Wait 1 hour. Use staging CA for testing (Phase 6.3). |
| Caddy not running | `docker compose -f docker-compose.prod.yml ps` and restart if needed |
| Another process using port 80/443 | `sudo ss -tlnp \| grep -E ':80\|:443'` -- only Caddy should be listening |

After fixing the cause, restart Caddy:

```bash
docker compose -f docker-compose.prod.yml restart caddy
```

### Container exits immediately

**Symptom:** `docker compose ps` shows the web container as `Exited`.

**Diagnosis:**

```bash
docker compose -f docker-compose.prod.yml logs web --tail 50
```

**Common causes:**

- **Missing `.env` file:** If `env_file: .env` is specified but the file does not exist, the container will not start. Run `scripts/deploy-app.sh` or create it per Phase 4.2 from `web/.env.example`.
- **Python import error:** A dependency is missing or broken. The traceback will identify the module.
- **Syntax error in app code:** The traceback will show the file and line.

**Quick test (bypasses .env requirement temporarily):**

```bash
docker compose -f docker-compose.prod.yml run --rm --no-deps web python -c \
  "from acb_large_print_web.app import create_app; print('OK')"
```

### Firewall mistakes

**Symptom:** Cannot connect on port 80, 443, or 22 from outside, but the server is running.

**Diagnosis:**

```bash
sudo ufw status verbose
```

**Fix:** If ports are missing:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

**If you accidentally blocked SSH:**

Log into `https://nerdvm.racknerd.com/`, select your VPS, and click the **VNC** or **HTML5 Console** button. From the console:

```bash
sudo ufw allow OpenSSH
sudo ufw reload
```

### Disk full

**Symptom:** Builds fail, containers crash, or logs show "No space left on device."

**Diagnosis:**

```bash
df -h /
docker system df
```

**Fix:**

```bash
# Remove unused Docker resources (images, stopped containers, networks)
docker system prune -a

# Clean apt cache
sudo apt clean

# Find large files
sudo du -sh /var/log/* | sort -rh | head -10

# Truncate a large log file if needed
sudo truncate -s 0 /var/log/syslog
```

### Health endpoint failing

**Symptom:** `curl https://glow.bits-acb.org/health` returns an error or times out.

**Step-by-step diagnosis:**

```bash
cd ~/app/web

# 1. Is the web container running?
docker compose -f docker-compose.prod.yml ps web

# 2. Can the health check pass inside the container?
docker compose -f docker-compose.prod.yml exec web python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"

# 3. Is Caddy running and healthy?
docker compose -f docker-compose.prod.yml ps caddy

# 4. What does Caddy say?
docker compose -f docker-compose.prod.yml logs caddy --tail 20

# 5. Is the firewall allowing traffic?
sudo ufw status
```

If step 2 fails, the Flask app has a problem (check web logs). If step 2 succeeds but external access fails, check Caddy logs and firewall rules.

### SSH access lost

**Cannot connect via SSH at all:**

1. Log into `https://nerdvm.racknerd.com/`
2. Select your VPS
3. Click the **VNC** or **HTML5 Console** button
4. Log in as `deploy` (or `root` if root login was not yet disabled)
5. Check and fix:
   - `sudo ufw status` -- is SSH allowed?
   - `sudo systemctl status sshd` -- is SSH running?
   - `cat /etc/ssh/sshd_config | grep -E 'PasswordAuth|PermitRoot'` -- are settings correct?
   - `sudo systemctl restart sshd` -- restart SSH after any changes
6. Try connecting via SSH again from your local machine

**Server completely unresponsive (VNC console also hangs):**

1. In SolusVM / NerdVM, click **Reboot**
2. Wait 2 minutes, then try SSH
3. If still unresponsive, click **Shutdown**, wait 30 seconds, then **Boot**
4. **Last resort:** Use the **Reinstall** option in SolusVM to reinstall the OS. This destroys all data. Download backups via SFTP first if possible.

### Upload fails with 413 error

The file exceeds the 500 MB upload limit configured in the Flask app (`MAX_CONTENT_LENGTH`). This is by design. Upload a smaller file.

### "sudo: unable to resolve host" warnings

**Symptom:** Every `sudo` command prints `sudo: unable to resolve host yourname: Name or service not known`. Commands still work, but the warning is noisy.

**Cause:** The server's hostname was changed (e.g., via `hostnamectl set-hostname`) but the new name was not added to `/etc/hosts`.

**Fix:**

```bash
echo "127.0.1.1 $(hostname)" >> /etc/hosts
```

Verify:

```bash
sudo whoami
```

Should print `root` with no warning.

### Permission denied in container

The container runs as user `app` (non-root). Only `/app/instance/` and `/tmp/` are writable inside the container. The Dockerfile creates and `chown`s the instance directory. If you see permission errors, check that the Docker image was built correctly:

```bash
docker compose -f docker-compose.prod.yml run --rm web ls -la /app/instance/
```

The owner should be `app`.

### Connection refused on ports 80/443

```bash
# Check firewall
sudo ufw status verbose

# Check what is listening
sudo ss -tlnp | grep -E ':80|:443'

# Check container status
cd ~/app/web
docker compose -f docker-compose.prod.yml ps
```

If `ss` shows nothing listening on 80/443, Caddy is not running. Check its logs and restart.

---

## Smoke Test Checklist

Run through this checklist after initial deployment or after a major change. Every item should pass.

| # | Test | Command or Action | Expected |
|---|------|-------------------|----------|
| 1 | SSH login as deploy | `ssh deploy@YOUR_SERVER_IP` | Connects with key (Path A) or password (Path B) |
| 2 | Firewall is active | `sudo ufw status` | Active; 22, 80, 443 allowed |
| 3 | Docker works | `docker ps` | Shows running containers |
| 4 | Both containers healthy | `docker compose -f ~/app/web/docker-compose.prod.yml ps` | web: Up (healthy), caddy: Up |
| 5 | HTTPS is live (app primary) | `curl -s https://lp.csedesigns.com/health` | `ok` |
| 6 | HTTPS is live (main) | `curl -s https://csedesigns.com/` | HTML content |
| 7 | HTTPS is live (app alias, optional) | `curl -s https://glow.bits-acb.org/health` | `ok` |
| 8 | HTTP redirects to HTTPS (primary) | `curl -sI http://lp.csedesigns.com` | `301` redirect to `https://` |
| 9 | TLS certificate valid (primary) | `curl -vI https://lp.csedesigns.com 2>&1 \| grep issuer` | Contains "Let's Encrypt" |
| 10 | App landing page loads (primary) | Open `https://lp.csedesigns.com/` in browser | Landing page with audit/fix/template links |
| 11 | App landing page loads (alias, optional) | Open `https://glow.bits-acb.org/` in browser | Same landing page and both domains remain live |
| 12 | Backup can be created | `~/app/scripts/backup-feedback.sh` | Backup file created in `~/backups/` |
| 13 | Backup can be restored | `~/app/scripts/restore-feedback.sh ~/backups/LATEST.db` | Restores and health check passes |
| 14 | Reboot recovery | `sudo reboot`, wait 60s, reconnect, `docker compose ps` | Both containers Up |

---

## Environment Variables Reference

These variables are set in `~/app/web/.env` and injected into the container via the `env_file:` directive:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | **Yes** | Random per-start | Flask session and CSRF secret. **Set a fixed value in production** or sessions and CSRF tokens will not survive container restarts. |
| `FEEDBACK_PASSWORD` | No | (unset) | Set to enable feedback review at `/feedback/review?key=<password>`. When unset, the review endpoint is disabled. |
| `POSTMARK_SERVER_TOKEN` | No | (unset) | Postmark server token used for audit-report emails, Whisperer notifications, and admin magic-link sign-in emails. Required for email-based admin auth. |
| `POSTMARK_FROM_EMAIL` | No | `reports@glow.bits-acb.org` | Sender email address used by Postmark-delivered app emails. |
| `LOG_LEVEL` | No | `INFO` | Python logging level: DEBUG, INFO, WARNING, ERROR. |
| `KEYCLOAK_HOSTNAME` | No | `lp.csedesigns.com` | Hostname used by the Keycloak container when generating URLs. |
| `KEYCLOAK_BASE_URL` | No | `https://lp.csedesigns.com/auth` | Public Keycloak base URL used by the app health probe and OIDC issuer discovery. |
| `KEYCLOAK_REALM` | No | `glow` | Keycloak realm name used to build the issuer and endpoint URLs. |
| `KEYCLOAK_CLIENT_ID` | No | `glow-web` | OIDC client ID registered in Keycloak. |
| `KEYCLOAK_CLIENT_SECRET` | No | generated | OIDC client secret registered in Keycloak. |
| `KEYCLOAK_REDIRECT_URI` | No | `https://lp.csedesigns.com/authorize` | Absolute redirect URI registered in Keycloak. |
| `KEYCLOAK_ADMIN_PASSWORD` | Yes | generated if missing | Keycloak admin password for the bundled container. |
| `OIDC_SCOPES` | No | `openid email profile` | OIDC scopes requested during login. |
| `SESSION_TIMEOUT_MINUTES` | No | `240` | Session lifetime in minutes. Increase for very long interactive workflows. |
| `UPLOAD_MAX_AGE_HOURS` | No | `1` | Retention window for abandoned upload workspaces before cleanup. Active Whisper jobs keep their workspace alive while running. |
| `WHISPER_MAX_AUDIO_MB` | No | `500` | Maximum accepted audio file size for BITS Whisperer uploads. |
| `WHISPER_MAX_AUDIO_MINUTES` | No | `120` | Maximum accepted audio duration for BITS Whisperer. Longer recordings are rejected with guidance to split files. |
| `GLOW_MAX_AUDIO_QUEUE_DEPTH` | No | `5` | Maximum number of queued Whisperer jobs waiting for audio capacity. New requests are rejected gracefully when full. |
| `WHISPER_BACKGROUND_THRESHOLD_MINUTES` | No | `30` | Minimum estimated audio length required before background mode is offered in the UI. |
| `WHISPER_RETRIEVAL_HOURS` | No | `4` | Secure retrieval window after background job completion. Unretrieved content is cleared after this period. |
| `ADMIN_BOOTSTRAP_EMAILS` | No | (unset) | Comma-separated emails automatically approved as admin accounts on first sign-in flow. |
| `ADMIN_MAGIC_LINK_TTL_MINUTES` | No | `20` | Admin email magic-link expiration window in minutes. |
| `ADMIN_AUTH0_DOMAIN` | No | (unset) | Auth0 tenant domain used to derive authorize/token/userinfo endpoints for admin SSO. |
| `ADMIN_OAUTH_GOOGLE_CLIENT_ID` | No | (unset) | Google OAuth client ID for admin-only SSO. |
| `ADMIN_OAUTH_GOOGLE_CLIENT_SECRET` | No | (unset) | Google OAuth client secret for admin-only SSO. |
| `ADMIN_OAUTH_GITHUB_CLIENT_ID` | No | (unset) | GitHub OAuth client ID for admin-only SSO. |
| `ADMIN_OAUTH_GITHUB_CLIENT_SECRET` | No | (unset) | GitHub OAuth client secret for admin-only SSO. |
| `ADMIN_OAUTH_MICROSOFT_CLIENT_ID` | No | (unset) | Microsoft OAuth client ID for admin-only SSO. |
| `ADMIN_OAUTH_MICROSOFT_CLIENT_SECRET` | No | (unset) | Microsoft OAuth client secret for admin-only SSO. |
| `ADMIN_OAUTH_APPLE_CLIENT_ID` | No | (unset) | Apple OAuth client ID for admin-only SSO. |
| `ADMIN_OAUTH_APPLE_CLIENT_SECRET` | No | (unset) | Apple OAuth client secret for admin-only SSO. |
| `ADMIN_OAUTH_WORDPRESS_CLIENT_ID` | No | (unset) | WordPress OAuth/OIDC client ID for admin-only SSO. |
| `ADMIN_OAUTH_WORDPRESS_CLIENT_SECRET` | No | (unset) | WordPress OAuth/OIDC client secret for admin-only SSO. |
| `ADMIN_OAUTH_WORDPRESS_AUTH_URL` | No | (unset) | WordPress authorize endpoint for generic OIDC/OAuth configuration. |
| `ADMIN_OAUTH_WORDPRESS_TOKEN_URL` | No | (unset) | WordPress token endpoint for generic OIDC/OAuth configuration. |
| `ADMIN_OAUTH_WORDPRESS_USERINFO_URL` | No | (unset) | WordPress userinfo endpoint for generic OIDC/OAuth configuration. |

These are set directly in the compose file `environment:` block (not secrets):

| Variable | Value | Description |
|----------|-------|-------------|
| `FLASK_DEBUG` | `0` | Disables Flask debug mode. Never set to `1` in production. |

The Flask app also reads `MAX_CONTENT_LENGTH` (default: 500 MB) for upload file size limits, configured in the application source code.

---

## Appendix A: Shell Scripts

These scripts are located in `scripts/` in the repository. Upload them to `~/app/scripts/` on the server and make them executable:

```bash
chmod 700 ~/app/scripts/*.sh
```

### bootstrap-server.sh

Run this **as root** on a fresh Ubuntu 24.04 VPS to install base packages, Docker, and configure security. Does **not** modify SSH settings -- that remains a manual step to avoid lockouts.

```bash
#!/usr/bin/env bash
# bootstrap-server.sh -- One-time server setup for Ubuntu 24.04 VPS
#
# Run as root:  bash bootstrap-server.sh
#
# This script:
#   - Updates the system
#   - Installs base packages (git, curl, dnsutils, python3, etc.)
#   - Installs Docker Engine and Compose plugin
#   - Installs fail2ban and configures it for SSH
#   - Installs unattended-upgrades for automatic security patches
#   - Configures UFW firewall (SSH, HTTP, HTTPS)
#   - Creates a swap file (if none exists)
#   - Creates the deploy user (if not exists)
#
# This script does NOT:
#   - Modify SSH configuration (too risky to automate -- do it manually)
#   - Copy SSH keys (must be done from your local machine)
#   - Create .env or Caddyfile (environment-specific)
#
# After running this script, follow the manual steps in deployment.md:
#   Path A (SSH key login):
#     1. Copy your SSH key to the deploy user
#     2. Verify key-based login in a second terminal
#     3. Harden SSH (disable password auth and root login)
#   Path B (password login only):
#     1. Verify password login as deploy
#     2. Harden SSH (disable root login, keep password auth)
set -euo pipefail

# --- Configuration ---
DEPLOY_USER="deploy"
SWAP_SIZE="2G"

# --- Pre-flight checks ---
if [[ "$(id -u)" -ne 0 ]]; then
    echo "ERROR: This script must be run as root."
    exit 1
fi

echo "=== GLOW -- Server Bootstrap ==="
echo ""

# --- Step 1: Update system ---
echo "--- Updating system packages ---"
apt update && apt upgrade -y

# --- Step 2: Install base packages ---
echo "--- Installing base packages ---"
apt install -y \
    git \
    curl \
    ca-certificates \
    unzip \
    dnsutils \
    python3 \
    software-properties-common \
    gnupg \
    lsb-release

# --- Step 3: Install Docker ---
echo "--- Installing Docker Engine and Compose plugin ---"
install -m 0755 -d /etc/apt/keyrings

if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
fi

if [[ ! -f /etc/apt/sources.list.d/docker.list ]]; then
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null
fi

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker

echo "--- Docker installed: $(docker --version) ---"
echo "--- Compose installed: $(docker compose version) ---"

# --- Step 4: Install and configure fail2ban ---
echo "--- Installing fail2ban ---"
apt install -y fail2ban

tee /etc/fail2ban/jail.local > /dev/null << 'EOF'
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 5
bantime = 3600
findtime = 600
EOF

systemctl enable fail2ban
systemctl restart fail2ban

# --- Step 5: Install unattended-upgrades ---
echo "--- Enabling automatic security updates ---"
apt install -y unattended-upgrades
echo 'Unattended-Upgrade::Automatic-Reboot "false";' > /etc/apt/apt.conf.d/51auto-reboot-off
dpkg-reconfigure -plow unattended-upgrades

# --- Step 6: Configure UFW ---
echo "--- Configuring firewall ---"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "--- Firewall status ---"
ufw status verbose

# --- Step 7: Create swap file ---
if [[ ! -f /swapfile ]]; then
    echo "--- Creating ${SWAP_SIZE} swap file ---"
    fallocate -l "$SWAP_SIZE" /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    if ! grep -q '/swapfile' /etc/fstab; then
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi
    echo "--- Swap enabled ---"
else
    echo "--- Swap file already exists, skipping ---"
fi

# --- Step 8: Create deploy user ---
if id "$DEPLOY_USER" &>/dev/null; then
    echo "--- User '$DEPLOY_USER' already exists ---"
else
    echo "--- Creating user '$DEPLOY_USER' ---"
    adduser --disabled-password --gecos "" "$DEPLOY_USER"
    usermod -aG sudo "$DEPLOY_USER"
    echo "--- Set a password for $DEPLOY_USER ---"
    passwd "$DEPLOY_USER"
fi

usermod -aG docker "$DEPLOY_USER"

# --- Step 9: Create directory structure ---
echo "--- Creating directories ---"
sudo -u "$DEPLOY_USER" mkdir -p "/home/$DEPLOY_USER/app"
sudo -u "$DEPLOY_USER" mkdir -p "/home/$DEPLOY_USER/backups"

# --- Done ---
echo ""
echo "=== Bootstrap complete ==="
echo ""
echo "NEXT STEPS (do these manually -- see deployment.md):"
echo ""
echo "  PATH A (SSH key login -- recommended):"
echo "  1. From your LOCAL machine, copy your SSH key:"
echo "       ssh-copy-id ${DEPLOY_USER}@$(hostname -I | awk '{print $1}')"
echo "  2. In a SECOND terminal, verify key-based login:"
echo "       ssh ${DEPLOY_USER}@$(hostname -I | awk '{print $1}')"
echo "  3. ONLY after step 2 succeeds, harden SSH:"
echo "       sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config"
echo "       sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config"
echo "       systemctl restart sshd"
echo ""
echo "  PATH B (password login only):"
echo "  1. From your LOCAL machine, verify password login:"
echo "       ssh ${DEPLOY_USER}@$(hostname -I | awk '{print $1}')"
echo "  2. Harden SSH (disable root, keep password auth):"
echo "       sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config"
echo "       sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config"
echo "       systemctl restart ssh || systemctl restart sshd"
echo ""
echo "WARNING: Do NOT disable PasswordAuthentication unless you have verified key-based login works."
echo "         If locked out, use SolusVM VNC console at https://nerdvm.racknerd.com/"
```

### deploy-app.sh

Run this as the deploy user to build and start (or update) the application.

```bash
#!/usr/bin/env bash
# deploy-app.sh -- Build and deploy the ACB Large Print web application
#
# Run as deploy user:  bash ~/app/scripts/deploy-app.sh
#
# This script:
#   - Validates that required files exist
#   - Optionally pulls latest code from Git (if .git directory exists)
#   - Creates a pre-deploy feedback DB backup (optional)
#   - Builds and starts Docker containers
#   - Waits for health check
#   - Rolls back to the previous Git revision on failed health check (when available)
#   - Shows status and URLs to test
set -euo pipefail

# --- Configuration ---
APP_ROOT="${APP_ROOT:-$HOME/app}"
WEB_ROOT="${WEB_ROOT:-$APP_ROOT/web}"
COMPOSE_FILE="docker-compose.prod.yml"
APP_DOMAIN="${APP_DOMAIN:-lp.csedesigns.com}"
APP_ALIAS_DOMAIN="${APP_ALIAS_DOMAIN:-}"
MAIN_DOMAIN="${MAIN_DOMAIN:-csedesigns.com}"
ENABLE_PREDEPLOY_BACKUP="${ENABLE_PREDEPLOY_BACKUP:-1}"

PRE_DEPLOY_COMMIT=""
ROLLED_BACK=0

# --- Pre-flight checks ---
if [[ "$(whoami)" == "root" ]]; then
    echo "ERROR: Do not run this script as root. Run as the deploy user."
    exit 1
fi

if ! command -v docker &>/dev/null; then
    echo "ERROR: Docker is not installed. Run bootstrap-server.sh first."
    exit 1
fi

if ! docker info &>/dev/null 2>&1; then
    echo "ERROR: Cannot connect to Docker. Is your user in the docker group?"
    echo "       Run: sudo usermod -aG docker $(whoami)"
    echo "       Then log out and back in."
    exit 1
fi

echo "=== GLOW -- Deploy ==="
echo ""
echo "App root:     $APP_ROOT"
echo "Web root:     $WEB_ROOT"
echo "Compose file: $COMPOSE_FILE"
echo ""

# Check required files
MISSING=0
for F in "$WEB_ROOT/$COMPOSE_FILE" "$WEB_ROOT/.env" "$WEB_ROOT/Caddyfile" "$WEB_ROOT/Dockerfile"; do
    if [[ ! -f "$F" ]]; then
        echo "ERROR: Required file missing: $F"
        MISSING=1
    fi
done

if [[ ! -d "$APP_ROOT/desktop/src/acb_large_print" ]]; then
  echo "ERROR: desktop/src/acb_large_print/ directory missing (needed for Docker build)."
    MISSING=1
fi

if [[ "$MISSING" -eq 1 ]]; then
    echo ""
    echo "Fix the missing files and re-run this script."
    exit 1
fi

# --- Optional: pull latest from Git ---
if [[ -d "$APP_ROOT/.git" ]]; then
  PRE_DEPLOY_COMMIT=$(cd "$APP_ROOT" && git rev-parse HEAD)
    echo "--- Git repository detected. Pulling latest code ---"
    cd "$APP_ROOT"
    git pull origin main
fi

# --- Optional: pre-deploy feedback DB backup ---
if [[ "$ENABLE_PREDEPLOY_BACKUP" == "1" ]]; then
  if [[ -x "$APP_ROOT/scripts/backup-feedback.sh" ]]; then
    echo "--- Creating pre-deploy feedback backup ---"
    bash "$APP_ROOT/scripts/backup-feedback.sh"
  else
    echo "--- Skipping pre-deploy backup (backup-feedback.sh not executable) ---"
  fi
fi

# --- Build and start ---
cd "$WEB_ROOT"

echo "--- Building and starting containers ---"
docker compose -f "$COMPOSE_FILE" up -d --build

echo "--- Waiting for containers to become healthy ---"
ATTEMPTS=0
MAX_ATTEMPTS=20
HEALTHY=0
while [[ "$ATTEMPTS" -lt "$MAX_ATTEMPTS" ]]; do
    if docker compose -f "$COMPOSE_FILE" exec -T web python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
        HEALTHY=1
        break
    fi
    ATTEMPTS=$((ATTEMPTS + 1))
    printf "."
    sleep 3
done
echo ""

if [[ "$HEALTHY" -eq 1 ]]; then
    echo "--- Health check: PASSED ---"
else
    echo "--- Health check: DID NOT PASS after ${MAX_ATTEMPTS} attempts ---"
    echo "    Check logs: docker compose -f $COMPOSE_FILE logs web --tail 30"

  # Best-effort rollback to previous known-good code revision when Git is available.
  if [[ -n "$PRE_DEPLOY_COMMIT" && -d "$APP_ROOT/.git" ]]; then
    echo "--- Attempting rollback to previous commit: $PRE_DEPLOY_COMMIT ---"
    cd "$APP_ROOT"
    git checkout -f "$PRE_DEPLOY_COMMIT"

    cd "$WEB_ROOT"
    docker compose -f "$COMPOSE_FILE" up -d --build

    echo "--- Waiting for rollback health check ---"
    ATTEMPTS=0
    MAX_ATTEMPTS=40
    while [[ "$ATTEMPTS" -lt "$MAX_ATTEMPTS" ]]; do
      if docker compose -f "$COMPOSE_FILE" exec -T web python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
        ROLLED_BACK=1
        break
      fi
      ATTEMPTS=$((ATTEMPTS + 1))
      printf "."
      sleep 3
    done
    echo ""

    if [[ "$ROLLED_BACK" -eq 1 ]]; then
      echo "--- Rollback health check: PASSED ---"
    else
      echo "--- Rollback health check: FAILED ---"
      echo "    Manual intervention required."
      exit 1
    fi
  else
    echo "--- Rollback unavailable (no Git commit baseline). ---"
    exit 1
  fi
fi

# --- Status ---
echo ""
echo "--- Container status ---"
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "=== Deployment complete ==="
echo ""
if [[ "$ROLLED_BACK" -eq 1 ]]; then
  echo "NOTE: Deploy failed health checks and was rolled back to $PRE_DEPLOY_COMMIT."
  echo "      Investigate the failed revision before retrying deployment."
  echo ""
fi
echo "Test these URLs:"
echo "  https://${APP_DOMAIN}/"
echo "  https://${APP_DOMAIN}/health"
if [[ -n "$APP_ALIAS_DOMAIN" ]]; then
  echo "  https://${APP_ALIAS_DOMAIN}/"
  echo "  https://${APP_ALIAS_DOMAIN}/health"
fi
echo "  https://${MAIN_DOMAIN}/"
echo ""
echo "View logs:"
echo "  cd $WEB_ROOT && docker compose -f $COMPOSE_FILE logs --tail 50 -f"
```

### Dual-Domain Deployment (No Redirect Required)

You can serve both hostnames at the same time without redirecting one to the other:

- `APP_DOMAIN` (default primary): `lp.csedesigns.com`
- `APP_ALIAS_DOMAIN` (optional branded alias): for example `glow.bits-acb.org`

Run deploy and post-deploy checks with alias validation enabled:

```bash
APP_ALIAS_DOMAIN=glow.bits-acb.org bash ~/app/scripts/deploy-app.sh
APP_ALIAS_DOMAIN=glow.bits-acb.org bash ~/app/scripts/post-deploy-check.sh
```

When `APP_ALIAS_DOMAIN` is set, health checks must pass for both domains.

### Post-Deploy Regression Testing (Playwright)

After deployment, run browser regression tests from the `web` directory:

```bash
cd ~/app/web
npm install
npx playwright install
```

Set a DOCX file for upload-flow tests:

```bash
export E2E_UPLOAD_DOCX=/path/to/test.docx
```

Run tests and generate issue artifacts:

```bash
npm run test:e2e:report
```

Artifacts are written to `web/e2e/artifacts/`:

- `ISSUES.md` (failure summary)
- `results.json` (machine-readable)
- `junit.xml` (CI-friendly)
- `html-report/index.html` (interactive report)

---

## WSL Staging Lane (Pre-Production Gate)

Before pushing a release to the live server, validate it against a local Docker stack running inside Windows Subsystem for Linux (WSL). This catches environment-specific regressions that unit tests and Windows-local runs can miss.

### Why WSL staging?

- The production server runs Ubuntu + Docker. WSL provides an identical Linux container runtime on your Windows dev machine.
- AI features are gated off by default in the WSL compose override, matching the production default before opt-in.
- The staging stack is ephemeral -- it starts clean and tears down after the regression run, leaving no persistent state.

---

### Step 1: Enable Docker Desktop WSL Integration

Docker Desktop must expose its daemon inside the Ubuntu WSL distro before the staging scripts will work.

1. Open **Docker Desktop** on Windows.
2. Go to **Settings** (gear icon, top-right).
3. Select **Resources** > **WSL Integration**.
4. Toggle **Ubuntu** (or your distro name) to **On**.
5. Click **Apply & Restart**.
6. Verify from PowerShell:

```powershell
wsl -d Ubuntu -- docker --version
# Expected: Docker version 27.x.x, build ...
```

If this fails, Docker Desktop WSL integration is not active. Re-check the toggle and restart Docker Desktop.

---

### Step 2: Recommended WSL Tooling

Install the following inside the Ubuntu WSL distro. Open a WSL shell with `wsl -d Ubuntu` and run:

```bash
# Core utilities (usually pre-installed; confirm they are present)
sudo apt-get update
sudo apt-get install -y curl git jq unzip

# Python 3 and pip (needed if running tests directly inside WSL)
sudo apt-get install -y python3 python3-pip python3-venv

# Node.js 22 LTS (for Playwright inside WSL, if needed)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# PowerShell (pwsh) -- install via Microsoft APT repo
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | \
  sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] \
  https://packages.microsoft.com/ubuntu/24.04/prod noble main" | \
  sudo tee /etc/apt/sources.list.d/microsoft-prod.list
sudo apt-get update
sudo apt-get install -y powershell
pwsh --version
# Expected: PowerShell 7.x.x
```

**Why PowerShell in WSL?**
The staging orchestrator (`scripts/wsl-stage-regression.ps1`) runs from Windows PowerShell and shells into WSL. Having `pwsh` available inside the distro lets you run the same orchestration scripts natively inside WSL for CI or pipeline scenarios, and ensures scripting parity between environments.

---

### Step 3: Run the WSL Staging Regression

From a Windows PowerShell terminal at the repo root:

```powershell
# Basic run -- pytest + Playwright, AI gated off (default)
.\scripts\wsl-stage-regression.ps1

# Specify a DOCX file for upload-flow tests
.\scripts\wsl-stage-regression.ps1 -DocxPath "C:\path\to\test.docx"

# Keep the stack running after the test run (for manual inspection)
.\scripts\wsl-stage-regression.ps1 -KeepRunning

# Enable AI features in the staging stack (opt-in)
.\scripts\wsl-stage-regression.ps1 -EnableAI

# Run only pytest (skip Playwright browser tests)
.\scripts\wsl-stage-regression.ps1 -SkipE2E

# Run only Playwright (skip pytest)
.\scripts\wsl-stage-regression.ps1 -SkipPytest

# Target a non-default distro or port
.\scripts\wsl-stage-regression.ps1 -Distro "Ubuntu-24.04" -Port 8001
```

**Script parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-Distro` | `Ubuntu` | WSL distro name to use |
| `-Port` | `8000` | Host port mapped to the container |
| `-SkipPytest` | `$false` | Skip pytest suite |
| `-SkipE2E` | `$false` | Skip Playwright suite |
| `-KeepRunning` | `$false` | Leave stack up after tests |
| `-EnableAI` | `$false` | Set `GLOW_ENABLE_AI=1` in the staging stack |
| `-DocxPath` | _(none)_ | Path to a DOCX file for upload-flow tests |
| `-AudioPath` | _(none)_ | Path to an audio file for whisperer tests |

---

### Step 4: What the Script Tests

The staging regression covers the same assertions as the production post-deploy check:

1. **Health check** -- `/health` returns `200 OK`
2. **Pytest suite** -- all 146+ unit and integration tests against the running container
3. **Playwright e2e suite** -- browser-based regression across all major routes:
   - Home page loads
   - Audit form submits and returns results
   - Fix form submits and returns results
   - Convert form submits
   - Template builder loads
   - Feedback form submits
   - Whisperer endpoint -- skipped automatically if AI is gated off (404 response)

---

### Step 5: Expected Output (Clean Pass)

```
[WSL-STAGE] Checking WSL distro: Ubuntu ... OK
[WSL-STAGE] Starting stack inside WSL...
[WSL-STAGE] Waiting for /health on http://localhost:8000 ...
[WSL-STAGE] Stack is up after 12s
[WSL-STAGE] Running pytest...
=============== 146 passed in 18.4s ===============
[WSL-STAGE] Running Playwright...
  14 passed (42.1s)
[WSL-STAGE] Tearing down stack...
[WSL-STAGE] PASS -- all checks green. Safe to deploy.
```

If any step fails, the script exits non-zero and prints which phase failed. The Docker stack is torn down automatically unless `-KeepRunning` was specified.

---

### Step 6: Troubleshooting

**"Docker is not available inside WSL distro"**
Docker Desktop WSL integration is not enabled for that distro. Follow Step 1 above.

**"Cannot connect to the Docker daemon"**
Docker Desktop is not running on Windows. Start it and wait for the whale icon to appear in the system tray.

**Stack starts but health check times out**
Run `wsl -d Ubuntu -- docker compose -f web/docker-compose.yml -f web/docker-compose.wsl.yml logs` to inspect container logs for startup errors.

**Pytest failures on imports or missing modules**
The container builds from the repo's `Dockerfile`. If you have local changes that are not committed, rebuild: add `-Rebuild` support or run `docker compose build` manually inside WSL before re-running the script.

**Port already in use**
Another service is using port 8000. Pass `-Port 8001` (or any free port) to the staging script.

---

### Step 7: WSL Staging in the Pre-Production Workflow

```
[ Your feature branch ]
        |
        v
[ pytest + mypy locally ] --> all green
        |
        v
[ wsl-stage-regression.ps1 ] --> all green   <-- NEW GATE
        |
        v
[ git push + deploy-app.sh to server ] --> post-deploy-check.sh
```

Run the WSL staging gate every time before pushing a release that touches routes, templates, Docker configuration, or AI feature flags. Skip it only for documentation-only changes.

---

### backup-feedback.sh

Run manually or via cron to create timestamped backups of the feedback database.

```bash
#!/usr/bin/env bash
# backup-feedback.sh -- Back up the feedback SQLite database
#
# Run as deploy user:  bash ~/app/scripts/backup-feedback.sh
#
# Schedule via cron (daily at 2 AM):
#   0 2 * * * /home/deploy/app/scripts/backup-feedback.sh >> /home/deploy/backups/backup.log 2>&1
#
# This script:
#   - Copies the feedback database out of the Docker volume
#   - Saves it with a timestamp in the backups directory
#   - Removes backups older than KEEP_DAYS
set -euo pipefail

# --- Configuration ---
WEB_ROOT="${WEB_ROOT:-$HOME/app/web}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups}"
COMPOSE_FILE="docker-compose.prod.yml"
KEEP_DAYS=30

# --- Pre-flight checks ---
if [[ "$(whoami)" == "root" ]]; then
    echo "$(date -Iseconds) ERROR: Do not run this script as root."
    exit 1
fi

mkdir -p "$BACKUP_ROOT"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="$BACKUP_ROOT/feedback-$TIMESTAMP.db"

# Check if the compose file exists
if [[ ! -f "$WEB_ROOT/$COMPOSE_FILE" ]]; then
    echo "$(date -Iseconds) ERROR: Compose file not found: $WEB_ROOT/$COMPOSE_FILE"
    exit 1
fi

# --- Create backup ---
echo "$(date -Iseconds) Backing up feedback database..."
docker compose -f "$WEB_ROOT/$COMPOSE_FILE" cp web:/app/instance/feedback.db "$BACKUP_FILE"

if [[ -f "$BACKUP_FILE" ]]; then
    SIZE=$(stat --format='%s' "$BACKUP_FILE" 2>/dev/null || stat -f'%z' "$BACKUP_FILE" 2>/dev/null || echo "unknown")
    echo "$(date -Iseconds) Backup created: $BACKUP_FILE ($SIZE bytes)"
else
    echo "$(date -Iseconds) ERROR: Backup file was not created."
    exit 1
fi

# --- Rotate old backups ---
find "$BACKUP_ROOT" -name "feedback-*.db" -type f -mtime "+$KEEP_DAYS" -print -delete | while read -r OLD; do
    echo "$(date -Iseconds) Deleted old backup: $OLD"
done

# --- Summary ---
TOTAL=$(find "$BACKUP_ROOT" -name "feedback-*.db" -type f | wc -l)
echo "$(date -Iseconds) Total backups on disk: $TOTAL"
```

### restore-feedback.sh

Restore the feedback database from a backup file. Prompts for confirmation before proceeding.

```bash
#!/usr/bin/env bash
# restore-feedback.sh -- Restore the feedback database from a backup
#
# Usage:  bash ~/app/scripts/restore-feedback.sh /path/to/backup.db
#
# This script:
#   - Validates the backup file exists and looks like a SQLite database
#   - Asks for confirmation
#   - Stops the web container
#   - Copies the backup into the Docker volume
#   - Starts the web container
#   - Verifies the health check passes
set -euo pipefail

# --- Configuration ---
WEB_ROOT="${WEB_ROOT:-$HOME/app/web}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups}"
COMPOSE_FILE="docker-compose.prod.yml"

# --- Usage ---
if [[ $# -lt 1 ]]; then
    echo "Usage: restore-feedback.sh <backup-file>"
    echo ""
    echo "Available backups:"
    if [[ -d "$BACKUP_ROOT" ]]; then
        ls -lh "$BACKUP_ROOT"/feedback-*.db 2>/dev/null || echo "  (none found in $BACKUP_ROOT)"
    else
        echo "  Backup directory does not exist: $BACKUP_ROOT"
    fi
    exit 1
fi

BACKUP_FILE="$1"

# --- Pre-flight checks ---
if [[ "$(whoami)" == "root" ]]; then
    echo "ERROR: Do not run this script as root."
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

if [[ ! -f "$WEB_ROOT/$COMPOSE_FILE" ]]; then
    echo "ERROR: Compose file not found: $WEB_ROOT/$COMPOSE_FILE"
    exit 1
fi

# Basic check that the file looks like a SQLite database
if ! head -c 16 "$BACKUP_FILE" | grep -q "SQLite format 3"; then
    echo "ERROR: File does not appear to be a SQLite database: $BACKUP_FILE"
    exit 1
fi

SIZE=$(stat --format='%s' "$BACKUP_FILE" 2>/dev/null || stat -f'%z' "$BACKUP_FILE" 2>/dev/null || echo "unknown")

echo "=== Feedback Database Restore ==="
echo ""
echo "Backup file: $BACKUP_FILE"
echo "Size:        $SIZE bytes"
echo ""
echo "WARNING: This will replace the current feedback database."
echo "         The web container will be stopped briefly."
echo ""
read -rp "Type 'yes' to continue: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted."
    exit 0
fi

cd "$WEB_ROOT"

# --- Stop web container ---
echo "--- Stopping web container ---"
docker compose -f "$COMPOSE_FILE" stop web

# --- Copy backup into volume ---
echo "--- Restoring database ---"
docker compose -f "$COMPOSE_FILE" cp "$BACKUP_FILE" web:/app/instance/feedback.db

# --- Start web container ---
echo "--- Starting web container ---"
docker compose -f "$COMPOSE_FILE" start web

# --- Wait and verify ---
echo "--- Waiting for health check ---"
ATTEMPTS=0
MAX_ATTEMPTS=10
HEALTHY=0
while [[ "$ATTEMPTS" -lt "$MAX_ATTEMPTS" ]]; do
    if docker compose -f "$COMPOSE_FILE" exec -T web python -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" 2>/dev/null; then
        HEALTHY=1
        break
    fi
    ATTEMPTS=$((ATTEMPTS + 1))
    sleep 2
done

if [[ "$HEALTHY" -eq 1 ]]; then
    echo "--- Health check: PASSED ---"
    echo ""
    echo "=== Restore complete ==="
else
    echo "--- Health check: FAILED ---"
    echo "    Check logs: docker compose -f $COMPOSE_FILE logs web --tail 30"
    exit 1
fi
```

---

## Appendix B: Reference Files

### Production Docker Compose (docker-compose.prod.yml)

This file ships with the repository at `web/docker-compose.prod.yml`. See Phase 4.5 for a full listing and explanation.

### Caddyfile template (Caddyfile.example)

This file ships with the repository at `web/Caddyfile.example`. Copy it to `Caddyfile` and replace the domain names. See Phase 4.3.

### Dockerfile

The Dockerfile ships with the repository at `web/Dockerfile`:

```dockerfile
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY desktop/pyproject.toml desktop/
COPY desktop/src/ desktop/src/
RUN pip install --no-cache-dir ./desktop

COPY web/pyproject.toml web/requirements.txt web/
COPY web/src/ web/src/
RUN pip install --no-cache-dir ./web

RUN addgroup --system app && adduser --system --ingroup app app
RUN mkdir -p /app/instance && chown app:app /app/instance

USER app
EXPOSE 8000

CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "acb_large_print_web.app:create_app()"]
```

**Image pinning (optional):** For fully reproducible builds, pin the base image digest:

```dockerfile
FROM python:3.13-slim@sha256:<digest> AS base
```

Run `docker pull python:3.13-slim` and note the digest. Update periodically for security patches.

### Development Docker Compose (docker-compose.yml)

The development compose file at `web/docker-compose.yml` publishes port 8000 directly to the host without Caddy. Use it for local development only:

```yaml
services:
  web:
    build:
      context: ..
      dockerfile: web/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - FLASK_DEBUG=0
    volumes:
      - feedback-data:/app/instance
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

volumes:
  feedback-data:
```

For production deployment, always use `docker-compose.prod.yml`.
