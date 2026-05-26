# GLOW Amazon SES Implementation Walkthrough

**Project:** GLOW  
**Umbrella domain:** `letitglow.app`  
**DNS provider:** Namecheap  
**Identity provider:** Keycloak  
**Transactional email provider:** Amazon SES  
**Recommended SES Region:** `us-east-1`  
**Recommended SES sender identity:** `notify.letitglow.app`  
**Recommended MAIL FROM / bounce domain:** `bounce.notify.letitglow.app`  
**Recommended future agent inbox domain:** `agents.letitglow.app`  
**Document type:** Hand-holding implementation guide  
**Last updated:** May 25, 2026

---

## 1. Purpose of This Guide

This guide walks through the practical, step-by-step setup for Amazon SES transactional email for GLOW under the `letitglow.app` umbrella domain.

It covers:

- What to configure in Amazon SES.
- What to configure in Namecheap DNS.
- How to configure Keycloak to send through SES.
- How to prepare the AWS production-access request.
- How to test safely.
- How to monitor bounces, complaints, and deliverability.
- How to avoid the mistakes that can cause SES approval delays or reputation problems.

This guide assumes GLOW will use:

```text
Keycloak -> Amazon SES SMTP
for identity email, such as email verification, password reset, required actions, and account notices.

GLOW application -> Amazon SES API v2
for application-specific transactional email, such as feedback confirmations, admin notices, and optional future job-completion notices.

AgentMail, if used later
for future AI-agent inboxes only, not for core authentication or transactional delivery.
```

---

## 2. Important Scope Decisions

### 2.1 What Amazon SES will be used for

Use Amazon SES for controlled, low-volume transactional email only.

Approved initial message types:

```text
Keycloak identity email:
- Email verification
- Password reset
- Required action email
- Account update or administrator-triggered account notices

GLOW application email:
- Feedback confirmation
- Feedback notification to administrators
- Security alerts
- System error alerts
- Optional future job-completion notices, only if the user explicitly opts in
```

### 2.2 What Amazon SES will not be used for

Do not use this SES configuration for:

```text
- Newsletters
- BITS announcements
- GLOW marketing
- Convention promotions
- Fundraising blasts
- Bulk community email
- Purchased lists
- Rented lists
- Scraped addresses
- Cold outreach
- Sending uploaded files
- Sending converted files
- Sending extracted document text
- Sending full accessibility reports by default
```

This matters because AWS reviews SES production-access requests carefully. The cleanest and strongest story is:

> GLOW uses SES for low-volume transactional service email. Keycloak generates identity email. GLOW generates application-specific service email. No marketing. No bulk lists. No uploaded files or private results are emailed.

---

## 3. Domain Plan

Use separate subdomains so each email function has a clear purpose.

| Purpose | Domain or Address |
|---|---|
| Public GLOW site | `https://letitglow.app` |
| SES sending identity | `notify.letitglow.app` |
| Default From address | `no-reply@notify.letitglow.app` |
| Security From address | `security@notify.letitglow.app` |
| Feedback From address | `feedback@notify.letitglow.app` |
| Reply-To address | `support@letitglow.app` if this mailbox exists |
| Custom MAIL FROM domain | `bounce.notify.letitglow.app` |
| Envelope From address for Keycloak | `bounces@bounce.notify.letitglow.app` |
| Future agent inbox domain | `agents.letitglow.app` |

Important distinction:

```text
From address:
no-reply@notify.letitglow.app

MAIL FROM / Return-Path / bounce address:
bounces@bounce.notify.letitglow.app
```

Do not use the bounce domain as a visible From address.

---

## 4. Before You Touch AWS or DNS

### 4.1 Confirm Namecheap is actually managing DNS

In Namecheap:

1. Sign in to Namecheap.
2. Go to **Domain List**.
3. Find `letitglow.app`.
4. Choose **Manage**.
5. Check **Nameservers**.

If the domain uses Namecheap BasicDNS or PremiumDNS, you will manage records in Namecheap under **Advanced DNS**.

If the domain uses custom nameservers, Namecheap will not be the active DNS provider. In that case, add the records wherever those nameservers are hosted.

Namecheap’s own guidance says that if the Advanced DNS host-records area is not available, the domain is likely pointed to third-party or hosting nameservers, so records must be added at the active DNS provider instead.

### 4.2 Decide the SES Region

Recommended:

```text
us-east-1
```

Use the same Region consistently for:

```text
- SES domain identity
- SMTP credentials
- SES production access
- Configuration set
- Suppression settings
- SNS/EventBridge event publishing
- Keycloak SMTP endpoint
```

The SMTP endpoint for this guide will be:

```text
email-smtp.us-east-1.amazonaws.com
```

### 4.3 Prepare your AWS account

Before using SES:

- Enable MFA on the root account.
- Enable MFA for administrator accounts.
- Do not use root credentials for daily work.
- Use least-privilege IAM users or roles.
- Enable CloudTrail.
- Create a billing alert.
- Make sure you have access to the Namecheap DNS account.

### 4.4 Create your AWS account (exact onboarding sequence)

If you do not already have an AWS account, use this sequence exactly.

#### 4.4.1 Account creation

1. Open AWS sign-up:

```text
https://portal.aws.amazon.com/billing/signup
```

2. Enter an email address dedicated to operations access.
3. Set an AWS account name, for example:

```text
GLOW Production
```

4. Create a strong root password and store it in your password manager.
5. Complete contact details and payment profile.
6. Complete phone verification.
7. Choose support plan:

```text
Basic support (sufficient for initial setup)
```

#### 4.4.2 Secure the root user immediately

1. Sign in as root user one time.
2. Turn on MFA for root user:
  - Console path: Account menu -> Security credentials -> Multi-factor authentication (MFA).
3. Use an authenticator app or FIDO2 security key.
4. Do not use the root user for daily operations after this step.

#### 4.4.3 Create an admin operator account (recommended)

Preferred method:

1. Enable IAM Identity Center.
2. Create an administrative permission set.
3. Create your first human admin user and assign that permission set.

Alternative method (if Identity Center is deferred):

1. Create one IAM user for human admin access.
2. Attach `AdministratorAccess` for initial bootstrap only.
3. Enable MFA on that user.
4. Use this IAM user for console and CLI work.

#### 4.4.4 Configure CLI access for the admin account

1. Install AWS CLI v2.
2. Create access keys for the admin user only if CLI is required.
3. Configure a named profile:

```bash
aws configure --profile glow-admin
```

4. Enter:

```text
AWS Access Key ID:     <admin access key>
AWS Secret Access Key: <admin secret key>
Default region name:   us-east-1
Default output format: json
```

5. Validate identity:

```bash
aws sts get-caller-identity --profile glow-admin
```

#### 4.4.5 Baseline account guardrails before SES setup

1. Turn on CloudTrail in all needed regions.
2. Turn on GuardDuty (recommended).
3. Create a billing alarm in CloudWatch.
4. Confirm SES work will be done in:

```text
us-east-1
```

5. Continue to Section 6 only after the above is complete.

---

## 5. Recommended Names and Settings

Use these exact names unless you have a strong reason to change them.

```text
AWS Region:
us-east-1

SES identity:
notify.letitglow.app

Custom MAIL FROM domain:
bounce.notify.letitglow.app

SES configuration set:
glow-transactional-production

Keycloak SMTP host:
email-smtp.us-east-1.amazonaws.com

Keycloak SMTP port:
587

Keycloak SMTP encryption:
STARTTLS

Keycloak visible From:
no-reply@notify.letitglow.app

Keycloak Reply-To:
support@letitglow.app

Keycloak Envelope From:
bounces@bounce.notify.letitglow.app
```

---

# Part A: Amazon SES Console Setup

## 6. Open Amazon SES

1. Sign in to the AWS Console.
2. Search for **Amazon SES**.
3. Open **Amazon Simple Email Service**.
4. Make sure the Region selector is set to:

```text
US East (N. Virginia) us-east-1
```

Everything in this guide assumes `us-east-1`.

---

## 7. Create the SES Configuration Set First

This lets you attach the configuration set to the domain identity later.

1. In Amazon SES, go to **Configuration**.
2. Choose **Configuration sets**.
3. Choose **Create set**.
4. Name it:

```text
glow-transactional-production
```

5. For tracking options, do not enable open or click tracking at this stage.
6. Enable reputation metrics if available.
7. Leave dedicated IP pool unset unless you specifically purchased dedicated IPs.
8. Save the configuration set.

Recommended privacy choice:

```text
Do not enable open tracking.
Do not enable click tracking.
```

GLOW’s trust story is stronger if transactional email is minimal and privacy-forward.

---

## 8. Create the SES Domain Identity

1. In Amazon SES, go to **Configuration**.
2. Choose **Identities**.
3. Choose **Create identity**.
4. Select **Domain**.
5. Enter:

```text
notify.letitglow.app
```

6. Enable **Easy DKIM**.
7. Use the default DKIM key length unless you have a reason to change it.
8. If there is an option to assign a default configuration set, select:

```text
glow-transactional-production
```

9. Create the identity.

Amazon SES will now show DKIM DNS records. Usually these are three CNAME records.

Do not close the page until you have copied the DKIM records.

---

# Part B: Namecheap DNS Setup

## 9. How Namecheap Host Values Work

When entering records for `letitglow.app`, Namecheap usually expects the **Host** field to be relative to the root domain.

For example:

| Full DNS name | Namecheap Host field |
|---|---|
| `notify.letitglow.app` | `notify` |
| `_dmarc.notify.letitglow.app` | `_dmarc.notify` |
| `bounce.notify.letitglow.app` | `bounce.notify` |
| `abc123._domainkey.notify.letitglow.app` | `abc123._domainkey.notify` |

If you paste the full domain into the Host field and Namecheap appends `letitglow.app` again, you may accidentally create a broken record like:

```text
abc123._domainkey.notify.letitglow.app.letitglow.app
```

Use the relative Host values shown in this guide unless Namecheap clearly indicates that it accepts fully qualified names.

### 9.1 Namecheap field-by-field matrix (exact values)

Use this matrix in Namecheap **Advanced DNS -> Host Records**.

| Purpose | Type | Host | Value / Target | Priority | TTL | Value source |
|---|---|---|---|---:|---|---|
| Public apex site | A Record | `@` | `107.175.91.158` | n/a | Automatic | Known server IP |
| Public www host | A Record | `www` | `107.175.91.158` | n/a | Automatic | Known server IP |
| SES DKIM #1 | CNAME Record | `[SES_TOKEN_1]._domainkey.notify` | `[SES_TOKEN_1].dkim.amazonses.com` | n/a | Automatic | Generated by SES identity |
| SES DKIM #2 | CNAME Record | `[SES_TOKEN_2]._domainkey.notify` | `[SES_TOKEN_2].dkim.amazonses.com` | n/a | Automatic | Generated by SES identity |
| SES DKIM #3 | CNAME Record | `[SES_TOKEN_3]._domainkey.notify` | `[SES_TOKEN_3].dkim.amazonses.com` | n/a | Automatic | Generated by SES identity |
| MAIL FROM MX | MX Record | `bounce.notify` | `feedback-smtp.us-east-1.amazonses.com` | `10` | Automatic | Known for SES region `us-east-1` |
| MAIL FROM SPF | TXT Record | `bounce.notify` | `v=spf1 include:amazonses.com -all` | n/a | Automatic | Static value |
| DMARC for sender subdomain | TXT Record | `_dmarc.notify` | `v=DMARC1; p=none; rua=mailto:dmarc@letitglow.app; adkim=s; aspf=r` | n/a | Automatic | Static value |
| Optional root DMARC | TXT Record | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@letitglow.app` | n/a | Automatic | Static value |

Notes:

- The only values you cannot pre-fill are the three DKIM token pairs. Those come from SES after creating `notify.letitglow.app` identity.
- For A records, do not use `http://` or `https://` in the value.
- For CNAME records, the value must be a domain name, not an IP.
- Do not create a CNAME for `bounce.notify`; MX and CNAME must not coexist on the same host.

---

## 10. Add the SES DKIM CNAME Records in Namecheap

In Namecheap:

1. Sign in.
2. Go to **Domain List**.
3. Select **Manage** for `letitglow.app`.
4. Open the **Advanced DNS** tab.
5. Scroll to **Host Records**.
6. Choose **Add New Record**.

Amazon SES will give you three DKIM CNAME records.

They will look something like this:

```text
Name:
abc123def456._domainkey.notify.letitglow.app

Value:
abc123def456.dkim.amazonses.com
```

In Namecheap, enter it like this:

| Type | Host | Value | TTL |
|---|---|---|---|
| CNAME Record | `abc123def456._domainkey.notify` | `abc123def456.dkim.amazonses.com` | Automatic |

Repeat for all three SES DKIM records.

Important:

- Use the exact tokens Amazon SES gives you.
- Do not invent the DKIM values.
- Do not include quotation marks.
- If SES shows a trailing dot at the end of the value, Namecheap may accept it with or without the dot. If Namecheap rejects the value, remove only the trailing dot.

After adding the records, return to SES and wait for the identity to verify. DNS can verify quickly, but AWS documentation notes DNS changes can take up to 72 hours to propagate.

---

## 11. Configure the Custom MAIL FROM Domain in SES

Back in Amazon SES:

1. Go to **Identities**.
2. Select:

```text
notify.letitglow.app
```

3. Find **Custom MAIL FROM domain**.
4. Choose **Edit** or **Set custom MAIL FROM domain**.
5. Enter:

```text
bounce.notify.letitglow.app
```

6. For behavior on MX failure, choose:

```text
Reject message
```

Why reject?

Because if the MAIL FROM domain breaks, you want GLOW email to fail loudly rather than silently falling back to an Amazon-owned MAIL FROM domain. This protects your authentication posture.

SES will give you an MX record and SPF TXT record for the custom MAIL FROM domain.

---

## 12. Add the MAIL FROM MX Record in Namecheap

In Namecheap **Advanced DNS**, add:

| Type | Host | Value / Mail Server | Priority | TTL |
|---|---|---|---:|---|
| MX Record | `bounce.notify` | `feedback-smtp.us-east-1.amazonses.com` | `10` | Automatic |

Important:

- Use `feedback-smtp.us-east-1.amazonses.com` for `us-east-1`.
- If you chose a different SES Region, use the feedback SMTP domain for that Region.
- Do not create a CNAME record for `bounce.notify`; MX and CNAME cannot safely coexist for the same host.

---

## 13. Add the MAIL FROM SPF TXT Record in Namecheap

In Namecheap **Advanced DNS**, add:

| Type | Host | Value | TTL |
|---|---|---|---|
| TXT Record | `bounce.notify` | `v=spf1 include:amazonses.com -all` | Automatic |

This tells receiving mail systems that Amazon SES is allowed to send mail for the bounce domain.

---

## 14. Add DMARC for the SES Sending Subdomain

Add this TXT record in Namecheap:

| Type | Host | Value | TTL |
|---|---|---|---|
| TXT Record | `_dmarc.notify` | `v=DMARC1; p=none; rua=mailto:dmarc@letitglow.app; adkim=s; aspf=r` | Automatic |

Recommended starting policy:

```text
p=none
```

This means “monitor only.” It does not reject or quarantine messages yet.

Why `adkim=s`?

```text
adkim=s
```

means strict DKIM alignment. Since SES will sign using the `notify.letitglow.app` identity, this is appropriate once DKIM is working.

Why `aspf=r`?

```text
aspf=r
```

means relaxed SPF alignment. This is helpful because the visible From domain is `notify.letitglow.app`, while the custom MAIL FROM domain is `bounce.notify.letitglow.app`. Relaxed SPF alignment avoids unnecessary SPF alignment failures.

Later, after stable sending, you can move to:

```text
p=quarantine
```

And eventually:

```text
p=reject
```

Do not jump straight to `p=reject` until you have verified DKIM, SPF, DMARC, and all application mail flows.

---

## 15. Optional: Add Root DMARC for letitglow.app

If `letitglow.app` will also send email from the root domain, add a root DMARC record too.

| Type | Host | Value | TTL |
|---|---|---|---|
| TXT Record | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@letitglow.app` | Automatic |

Do this carefully if the root domain already has email services such as Google Workspace, Microsoft 365, Fastmail, Namecheap Private Email, or another mail host.

Only one DMARC TXT record should exist per domain/subdomain.

---

## 16. DNS Record Summary for Namecheap

Use this as your working checklist.

### 16.1 DKIM records from SES

You will have three records like this:

| Type | Host | Value |
|---|---|---|
| CNAME | `[SES_TOKEN_1]._domainkey.notify` | `[SES_TOKEN_1].dkim.amazonses.com` |
| CNAME | `[SES_TOKEN_2]._domainkey.notify` | `[SES_TOKEN_2].dkim.amazonses.com` |
| CNAME | `[SES_TOKEN_3]._domainkey.notify` | `[SES_TOKEN_3].dkim.amazonses.com` |

Use the actual SES values.

### 16.2 MAIL FROM records

| Type | Host | Value / Mail Server | Priority |
|---|---|---|---:|
| MX | `bounce.notify` | `feedback-smtp.us-east-1.amazonses.com` | `10` |
| TXT | `bounce.notify` | `v=spf1 include:amazonses.com -all` | n/a |

### 16.3 DMARC records

| Type | Host | Value |
|---|---|---|
| TXT | `_dmarc.notify` | `v=DMARC1; p=none; rua=mailto:dmarc@letitglow.app; adkim=s; aspf=r` |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@letitglow.app` |

The root DMARC record is optional but recommended if the root domain will send email.

---

# Part C: Verify SES Identity and MAIL FROM

## 17. Verify the Identity in SES

In Amazon SES:

1. Go to **Configuration**.
2. Choose **Identities**.
3. Select:

```text
notify.letitglow.app
```

Confirm:

```text
Identity status: Verified
DKIM status: Successful
```

If it is not verified:

- Wait longer.
- Recheck the Namecheap Host fields.
- Make sure you did not accidentally duplicate the domain name.
- Make sure no CNAME host conflicts exist.
- Confirm you are looking at the same SES Region where you created the identity.

---

## 18. Verify Custom MAIL FROM

In the same SES identity screen, confirm:

```text
Custom MAIL FROM status: Successful
```

If it is not successful:

- Confirm the MX record exists at `bounce.notify.letitglow.app`.
- Confirm the SPF TXT record exists at `bounce.notify.letitglow.app`.
- Confirm the MX value uses the correct SES Region.
- Confirm the Host field in Namecheap is `bounce.notify`, not the full domain with the root accidentally duplicated.

---

# Part D: AWS CLI Setup Option

You can do the setup through the console, but these commands are helpful for verification and repeatability.

## 19. Configure Shell Variables

Linux, macOS, or WSL:

```bash
export AWS_PROFILE=glow-admin
export AWS_REGION=us-east-1
export SES_IDENTITY=notify.letitglow.app
export MAIL_FROM_DOMAIN=bounce.notify.letitglow.app
export CONFIG_SET=glow-transactional-production
```

PowerShell:

```powershell
$env:AWS_PROFILE = "glow-admin"
$env:AWS_REGION = "us-east-1"
$env:SES_IDENTITY = "notify.letitglow.app"
$env:MAIL_FROM_DOMAIN = "bounce.notify.letitglow.app"
$env:CONFIG_SET = "glow-transactional-production"
```

---

## 20. Create the Configuration Set with AWS CLI

```bash
aws sesv2 create-configuration-set \
  --configuration-set-name "$CONFIG_SET" \
  --region "$AWS_REGION"
```

If it already exists, AWS will return an error. That is fine; do not create a duplicate.

---

## 21. Create the Email Identity with AWS CLI

```bash
aws sesv2 create-email-identity \
  --email-identity "$SES_IDENTITY" \
  --region "$AWS_REGION"
```

Then retrieve its status and DKIM details:

```bash
aws sesv2 get-email-identity \
  --email-identity "$SES_IDENTITY" \
  --region "$AWS_REGION"
```

Use the DKIM tokens from the output or from the SES console to create the Namecheap CNAME records.

---

## 22. Associate the Default Configuration Set with the Identity

This is especially important for Keycloak, because Keycloak may not let you add SES-specific message headers.

```bash
aws sesv2 put-email-identity-configuration-set-attributes \
  --email-identity "$SES_IDENTITY" \
  --configuration-set-name "$CONFIG_SET" \
  --region "$AWS_REGION"
```

This makes the configuration set apply by default when no other configuration set is specified.

---

## 23. Configure Custom MAIL FROM with AWS CLI

```bash
aws sesv2 put-email-identity-mail-from-attributes \
  --email-identity "$SES_IDENTITY" \
  --mail-from-domain "$MAIL_FROM_DOMAIN" \
  --behavior-on-mx-failure REJECT_MESSAGE \
  --region "$AWS_REGION"
```

Then check the identity again:

```bash
aws sesv2 get-email-identity \
  --email-identity "$SES_IDENTITY" \
  --region "$AWS_REGION"
```

---

## 24. Enable Account-Level Suppression

```bash
aws sesv2 put-account-suppression-attributes \
  --suppressed-reasons BOUNCE COMPLAINT \
  --region "$AWS_REGION"
```

This tells SES to automatically suppress addresses that hard bounce or complain.

---

## 25. Enable Configuration Set Suppression

```bash
aws sesv2 put-configuration-set-suppression-options \
  --configuration-set-name "$CONFIG_SET" \
  --suppressed-reasons BOUNCE COMPLAINT \
  --region "$AWS_REGION"
```

This keeps the GLOW transactional configuration set aligned with account-level suppression.

---

# Part E: Event Publishing for Bounces and Complaints

## 26. Why This Matters

Amazon SES expects you to monitor and handle bounces and complaints. This is not optional for a healthy production setup.

GLOW should know when:

```text
- An address hard bounced.
- A recipient complained.
- SES rejected a message.
- A message failed to render.
- A message was delivered.
```

At a minimum, hard bounces and complaints should suppress future sending.

---

## 27. Simple First-Version Event Design

For a first implementation, use this flow:

```text
Amazon SES configuration set
  -> SNS topic
  -> HTTPS webhook or Lambda
  -> GLOW email event table
  -> GLOW suppression table
```

Create one SNS topic:

```text
glow-ses-events
```

Subscribe either:

```text
- A Lambda function, or
- A secure HTTPS endpoint on the GLOW server
```

Recommended event types:

```text
SEND
DELIVERY
BOUNCE
COMPLAINT
REJECT
RENDERING_FAILURE
DELIVERY_DELAY
```

Avoid open/click tracking initially.

---

## 28. Minimum Suppression Logic

GLOW should implement local suppression in addition to SES suppression.

When a hard bounce occurs:

```text
1. Record the SES event.
2. Mark the message as bounced.
3. Add the recipient to local suppression with reason = bounce.
4. Do not send future non-critical email to that address.
```

When a complaint occurs:

```text
1. Record the SES event.
2. Mark the message as complained.
3. Add the recipient to local suppression with reason = complaint.
4. Do not send future email to that address unless a human-reviewed policy exception exists.
```

For temporary bounces:

```text
1. Record the event.
2. Do not immediately suppress.
3. Retry only if the message type is still relevant.
4. Suppress after a configured threshold if repeated failures occur.
```

---

# Part F: Create SES SMTP Credentials for Keycloak

## 29. Why Keycloak Uses SMTP

Keycloak’s email settings are SMTP-based. Keycloak should send identity email through SES SMTP.

Keycloak handles:

```text
- Email verification
- Forgotten password
- Required actions
- Admin-initiated account email
```

GLOW should not duplicate these identity email features in application code.

---

## 30. Create SES SMTP Credentials

In Amazon SES:

1. Open SES in `us-east-1`.
2. Go to **SMTP settings**.
3. Choose **Create SMTP credentials**.
4. Name the SMTP user something clear, such as:

```text
glow-keycloak-ses-smtp
```

5. Create the user.
6. Download the credentials CSV immediately.

Important:

- SES SMTP credentials are Region-specific.
- SES SMTP credentials are not the same as ordinary AWS access keys.
- You cannot view the SMTP password again after leaving the creation screen.
- Store the credentials securely.
- Do not commit them to GitHub.
- Do not paste them into documentation or tickets.

---

# Part G: Configure Keycloak Email

## 31. Open Keycloak Realm Email Settings

In the Keycloak admin console:

1. Sign in as a Keycloak administrator.
2. Select the GLOW realm.
3. Go to **Realm settings**.
4. Open the **Email** tab.

---

## 32. Enter Keycloak SMTP Settings

Use these values:

```text
From:
no-reply@notify.letitglow.app

From display name:
GLOW

Reply-To:
support@letitglow.app

Reply-To display name:
GLOW Support

Envelope From:
bounces@bounce.notify.letitglow.app

Host:
email-smtp.us-east-1.amazonaws.com

Port:
587

Encryption:
STARTTLS

Authentication:
Enabled

Authentication type:
Password

Username:
[SES SMTP username from downloaded CSV]

Password:
[SES SMTP password from downloaded CSV]
```

Notes:

- Only use `support@letitglow.app` if that mailbox actually exists and is monitored.
- The **Envelope From** should be an email address at the MAIL FROM domain, such as `bounces@bounce.notify.letitglow.app`.
- Do not put the SMTP username or password in the visible GLOW repository.
- If port 587 fails because of a network/firewall issue, try SES TLS Wrapper on port 465 if Keycloak and your server environment support it.

---

## 33. Send a Keycloak Test Email

In Keycloak’s Email tab:

1. Save the SMTP settings.
2. Use **Test connection** or **Send test email**, depending on your Keycloak version.
3. Send to a verified address if SES is still in sandbox.
4. Check whether the email arrives.
5. Inspect the headers.

Look for:

```text
DKIM: pass
SPF: pass
DMARC: pass
Return-Path: bounces@bounce.notify.letitglow.app or another address under bounce.notify.letitglow.app
From: no-reply@notify.letitglow.app
```

If SES is still in sandbox, the recipient must be verified in SES unless you are sending to the SES mailbox simulator.

---

# Part H: Configure GLOW Application Sending

## 34. Use SES API v2 for GLOW Application Email

For GLOW application email, prefer the SES API v2 over SMTP.

This gives better control over:

```text
- Configuration set
- Message tags
- Logging
- Retry behavior
- Template selection
- Event correlation
```

Example application-level message types:

```text
feedback_confirmation
feedback_admin_notice
system_error_alert
security_notice
optional_job_completion_notice
```

Do not let random parts of the GLOW codebase send email directly.

Create a central email service module.

---

## 35. Required Application Controls

Before GLOW sends any application email, it should check:

```text
1. Is this email type allowed?
2. Is the recipient suppressed?
3. Is the recipient allowed for this message type?
4. Has the recipient exceeded rate limits?
5. Does the template have a plain-text version?
6. Does the message contain prohibited content?
```

Prohibited content:

```text
- Uploaded files
- Converted files
- Extracted text
- Full accessibility reports
- API keys
- Internal file paths
- Stack traces with user data
- Long-lived download links
```

---

## 36. Recommended GLOW Email Module Structure

```text
glow_email/
  __init__.py
  client.py
  queue.py
  templates.py
  suppression.py
  events.py
  audit.py
  rate_limit.py
```

Everything goes through one function:

```python
send_transactional_email(
    recipient_email,
    email_type,
    template_name,
    template_context,
    triggering_event,
    related_object_type=None,
    related_object_id=None
)
```

---

# Part I: Testing Before Production Access

## 37. Understand the SES Sandbox

Before production access, SES is in sandbox mode.

In sandbox mode:

```text
- You can send only to verified recipient addresses or simulator addresses.
- You can send only from verified identities.
- You have low sending limits.
```

Production access lets you send to unverified recipients, but you still must verify the identities you send from.

---

## 38. Use SES Mailbox Simulator

Use the SES mailbox simulator to test without damaging reputation metrics.

Common simulator addresses:

```text
success@simulator.amazonses.com
bounce@simulator.amazonses.com
complaint@simulator.amazonses.com
ooto@simulator.amazonses.com
suppressionlist@simulator.amazonses.com
```

Suggested tests:

```text
1. Send a success test.
2. Send a bounce test.
3. Confirm bounce event reaches SNS/webhook.
4. Confirm local suppression table updates.
5. Send a complaint test.
6. Confirm complaint event reaches SNS/webhook.
7. Confirm complaint suppression happens.
```

Do not test bounces by emailing fake addresses. Use the simulator.

---

## 39. Test DNS Authentication

After receiving a real test email, inspect headers.

You want:

```text
SPF: PASS
DKIM: PASS
DMARC: PASS
```

If you use Gmail to inspect:

1. Open the message.
2. Choose **Show original**.
3. Look for SPF, DKIM, and DMARC results.

If results fail:

- Recheck DKIM CNAMEs.
- Recheck MAIL FROM MX and SPF.
- Recheck DMARC host and policy.
- Confirm the From address is under `notify.letitglow.app`.
- Confirm the Return-Path is under `bounce.notify.letitglow.app`.
- Confirm you are using the same SES Region.

---

# Part J: Request SES Production Access

## 40. Prerequisites Before Requesting Production Access

Do not request production access until these are complete:

```text
[ ] SES identity notify.letitglow.app is verified.
[ ] DKIM is successful.
[ ] Custom MAIL FROM is successful.
[ ] SPF record exists for bounce.notify.letitglow.app.
[ ] DMARC exists for notify.letitglow.app.
[ ] Configuration set exists.
[ ] Default configuration set is attached to the SES identity.
[ ] Account-level suppression is enabled.
[ ] Configuration-set suppression is enabled.
[ ] Keycloak test email works.
[ ] GLOW application test email works or is ready.
[ ] Bounce/complaint event processing is planned or implemented.
[ ] Website has privacy/contact information.
[ ] GLOW email policy language is published or ready to publish.
```

---

## 41. Recommended Production Access Request

In Amazon SES:

1. Go to **Account dashboard**.
2. Choose **Request production access**.
3. Choose:

```text
Mail type: Transactional
```

4. Website URL:

```text
https://letitglow.app
```

5. Use case description:

```text
GLOW, Guided Layout & Output Workflow, is an accessibility workflow platform under the letitglow.app umbrella domain. It helps users and organizations work with accessibility-focused document, audio, and workflow tools.

We are requesting Amazon SES production access for low-volume transactional email only. GLOW uses Keycloak as its identity and access management provider. Keycloak generates identity-related transactional email such as account verification, password reset, required-action email, and administrator-triggered account notices. GLOW’s application code sends only limited application-specific transactional messages, such as feedback confirmations, feedback routing to administrators, operational alerts, security notices, and future optional job-completion notices requested by users.

This SES configuration will not be used for newsletters, promotional campaigns, convention announcements, fundraising blasts, cold outreach, or unsolicited bulk email. We do not use purchased, rented, scraped, or third-party mailing lists.

Uploaded files, converted files, extracted document text, private accessibility findings, generated reports, and user API keys are not sent by email. Transactional emails contain only minimal service information needed for the specific user-triggered or administrator-triggered action.

Recipients are users who initiated an action on the site, administrators of the service, or individuals who submitted feedback and provided an email address for confirmation. We have configured or are configuring a dedicated transactional sending identity, DKIM, SPF, DMARC, a custom MAIL FROM domain, a configuration set, bounce and complaint handling, monitoring, and suppression for bounces and complaints.

Initial expected volume is modest: approximately 50 to 300 messages per day, with occasional peaks during workshops, testing events, or public demonstrations. We are requesting a conservative initial quota and will request increases only after establishing healthy sending history.
```

Recommended initial quota request:

```text
1,000 messages per day
1 to 5 messages per second
```

If AWS asks for more detail, provide exact message types and the bounce/complaint handling workflow.

---

## 42. What Not to Say in the AWS Request

Avoid wording like:

```text
- We need bulk email.
- We will email BITS members.
- We will send announcements.
- We may import lists.
- We want unrestricted sending.
- We want to email documents to users.
- We are still figuring out bounce handling.
```

Use wording like:

```text
- Low-volume transactional email.
- User-triggered identity and service messages.
- Keycloak-generated account email.
- GLOW-generated service email.
- No marketing.
- No bulk lists.
- No uploaded files or private results by email.
- Automatic suppression for bounces and complaints.
```

---

# Part K: After Production Approval

## 43. Roll Out Slowly

Do not enable every message type at once.

### Week 1

Enable only:

```text
- Keycloak verification email
- Keycloak password reset
- Keycloak required-action email
- Admin security notices
```

### Week 2

Enable:

```text
- Feedback confirmation
- Feedback admin routing
- System error alerts
```

### Later

Consider:

```text
- Optional job-completion notice
```

Only enable job-completion notices if:

```text
- User explicitly opts in.
- No files are attached.
- No extracted text is included.
- No full report is included.
- Any link is short-lived and privacy-reviewed.
```

---

## 44. Daily Monitoring During First Month

Check every day for the first month:

```text
- Sends
- Deliveries
- Bounces
- Complaints
- Rejects
- Rendering failures
- Suppressed recipients
- Unexpected volume spikes
- Keycloak test failures
- DNS authentication failures
```

Investigate immediately if:

```text
- Any complaint appears.
- Bounce rate rises unexpectedly.
- SES rejects messages.
- Custom MAIL FROM fails.
- DKIM status changes.
- Keycloak cannot send.
- Volume spikes beyond expected use.
```

---

## 45. Bounce and Complaint Targets

Keep bounce and complaint rates extremely low.

Operational rule:

```text
Hard bounce: suppress immediately.
Complaint: suppress immediately.
Repeated temporary failure: suppress after threshold.
Unknown recipient source: investigate before further sending.
```

Amazon indicates that bounce rates below 2% are best; higher rates can trigger review, and severe bounce rates can lead to sending pauses.

---

# Part L: Troubleshooting

## 46. SES Identity Not Verified

Likely causes:

```text
- DKIM CNAME host was entered incorrectly in Namecheap.
- Full domain was pasted and duplicated.
- CNAME value has a typo.
- DNS has not propagated yet.
- You are checking the wrong AWS Region.
```

Fix:

```text
1. Compare each SES DKIM record with Namecheap.
2. Use relative Host names.
3. Wait for DNS propagation.
4. Recheck the SES identity status.
```

---

## 47. Custom MAIL FROM Failed

Likely causes:

```text
- MX record missing.
- MX record has wrong host.
- MX record points to wrong SES Region.
- SPF TXT record missing.
- Host was entered as full domain and duplicated.
- CNAME exists at the same host.
```

Correct Namecheap records:

```text
MX host:
bounce.notify

MX value:
feedback-smtp.us-east-1.amazonses.com

TXT host:
bounce.notify

TXT value:
v=spf1 include:amazonses.com -all
```

---

## 48. Keycloak Test Email Fails

Check:

```text
- SES SMTP username and password are correct.
- SMTP credentials were created in us-east-1.
- Host is email-smtp.us-east-1.amazonaws.com.
- Port is 587 with STARTTLS.
- Server firewall allows outbound TCP 587.
- From address is no-reply@notify.letitglow.app.
- SES identity is verified.
- Recipient is verified if SES is still in sandbox.
```

If 587 fails:

```text
Try port 465 with TLS Wrapper if supported by your Keycloak version and server environment.
```

---

## 49. SPF Passes but DMARC Fails

Check:

```text
- DKIM is signing with notify.letitglow.app.
- From address is under notify.letitglow.app.
- DMARC record is at _dmarc.notify.letitglow.app.
- MAIL FROM domain is bounce.notify.letitglow.app.
- aspf is relaxed, not strict.
```

For this setup, DKIM should be the strongest DMARC alignment path.

---

## 50. DKIM Fails

Check:

```text
- The three SES DKIM CNAME records exist.
- CNAME Host values use [token]._domainkey.notify.
- CNAME Values point to [token].dkim.amazonses.com.
- No TXT record was accidentally created instead of CNAME.
- No quotes were added around CNAME values.
- You are sending from the same SES identity.
```

---

## 51. Emails Go to Spam

Check:

```text
- Is DKIM passing?
- Is SPF passing?
- Is DMARC passing?
- Is the content too promotional?
- Is the From address recognizable?
- Are you sending to people who expect the message?
- Are you sending too many test messages to the same provider?
- Are bounces and complaints being suppressed?
```

Improve:

```text
- Keep subject lines simple.
- Avoid marketing language.
- Include plain-text versions.
- Include a clear reason for the message.
- Use consistent From names.
- Avoid attachments.
```

---

# Part M: GLOW Privacy Language to Publish

Add a short email section to GLOW’s privacy or help page:

```text
GLOW sends limited transactional email related to use or administration of the service. Examples include account verification, password reset, security notices, feedback confirmations, administrator notifications, and optional user-requested job-completion notices.

GLOW does not use this notification system for newsletters, marketing, campaign messages, fundraising blasts, or unsolicited bulk email.

GLOW does not send uploaded files, converted files, extracted document text, private accessibility findings, generated reports, or user API keys by email. Transactional emails contain only the minimum information needed for the requested service or administrative action.
```

---

# Part N: AgentMail Boundary

AgentMail is out of scope for the Amazon SES implementation.

If used later, keep it separate:

```text
agents.letitglow.app
```

Use AgentMail only for future agent inboxes, such as:

```text
- Support triage agents
- Feedback classification agents
- Accessibility issue intake agents
- Workshop intake agents
```

Do not use AgentMail for:

```text
- Keycloak account verification
- Password reset
- Security email
- Core transactional email
- SES production access justification
- Bulk sending
```

Do not mention AgentMail in the initial SES production-access request unless AWS specifically asks about other mail systems.

---

# Part O: Final Checklist

## O.1 AWS SES

```text
[ ] Region selected: us-east-1.
[ ] Configuration set created: glow-transactional-production.
[ ] Domain identity created: notify.letitglow.app.
[ ] Easy DKIM enabled.
[ ] DKIM CNAMEs copied from SES.
[ ] Default configuration set attached to identity.
[ ] Custom MAIL FROM configured: bounce.notify.letitglow.app.
[ ] Account-level suppression enabled for BOUNCE and COMPLAINT.
[ ] Configuration-set suppression enabled for BOUNCE and COMPLAINT.
[ ] SMTP credentials created for Keycloak.
[ ] SES production-access request prepared.
```

## O.2 Namecheap DNS

```text
[ ] Three SES DKIM CNAME records added.
[ ] MAIL FROM MX record added at bounce.notify.
[ ] MAIL FROM SPF TXT record added at bounce.notify.
[ ] DMARC TXT record added at _dmarc.notify.
[ ] Optional root DMARC record reviewed.
[ ] No conflicting CNAME records exist.
[ ] DNS propagation verified.
```

## O.3 Keycloak

```text
[ ] From address set to no-reply@notify.letitglow.app.
[ ] Reply-To set to monitored support mailbox.
[ ] Envelope From set to bounces@bounce.notify.letitglow.app.
[ ] SMTP host set to email-smtp.us-east-1.amazonaws.com.
[ ] Port set to 587.
[ ] STARTTLS enabled.
[ ] SES SMTP username entered.
[ ] SES SMTP password entered.
[ ] Test email succeeds.
[ ] Headers show SPF, DKIM, and DMARC pass.
```

## O.4 GLOW Application

```text
[ ] Central email module exists.
[ ] No direct SES calls outside the email module.
[ ] Allowed message types are defined.
[ ] Local suppression table exists.
[ ] Bounce/complaint event handling exists or is scheduled.
[ ] Plain-text email templates exist.
[ ] No private files or results are emailed.
[ ] Optional job-completion notices are disabled until production metrics are stable.
```

## O.5 Production Access

```text
[ ] Website URL ready: https://letitglow.app.
[ ] Privacy/email policy published or ready.
[ ] Use case description says transactional only.
[ ] No marketing or bulk sending described.
[ ] Initial quota request is conservative.
[ ] Bounce and complaint handling is clearly described.
```

---

# Part P: Reference Links

These are the primary references used to build this guide.

## AWS SES

- Request production access / move out of sandbox:  
  https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html

- Creating and verifying identities:  
  https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html

- Custom MAIL FROM domain:  
  https://docs.aws.amazon.com/ses/latest/dg/mail-from.html

- DMARC with Amazon SES:  
  https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dmarc.html

- Connecting to an SES SMTP endpoint:  
  https://docs.aws.amazon.com/ses/latest/dg/smtp-connect.html

- Obtaining SES SMTP credentials:  
  https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html

- Configuration sets:  
  https://docs.aws.amazon.com/ses/latest/dg/creating-configuration-sets.html

- Account-level suppression list:  
  https://docs.aws.amazon.com/ses/latest/dg/sending-email-suppression-list.html

- SES mailbox simulator:  
  https://docs.aws.amazon.com/ses/latest/dg/send-an-email-from-console.html

- SES sending review process and bounce guidance:  
  https://docs.aws.amazon.com/ses/latest/dg/faqs-enforcement.html

## Keycloak

- Keycloak Server Administration Guide, realm email configuration:  
  https://www.keycloak.org/docs/latest/server_admin/index.html

## Namecheap DNS

- How to set up host records:  
  https://www.namecheap.com/support/knowledgebase/article.aspx/434/2237/how-do-i-set-up-host-records-for-a-domain/

- How to add TXT, SPF, DKIM, and DMARC records:  
  https://www.namecheap.com/support/knowledgebase/article.aspx/317/2237/how-do-i-add-txtspfdkimdmarc-records-for-my-domain/

- How to set up MX records:  
  https://www.namecheap.com/support/knowledgebase/article.aspx/322/2237/how-can-i-set-up-mx-records-required-for-mail-service/

---

# Part Q: One-Page Operational Summary

Use this when you need the short version.

```text
1. In SES us-east-1, create configuration set:
   glow-transactional-production

2. In SES us-east-1, create domain identity:
   notify.letitglow.app

3. Copy the three SES DKIM CNAME records.

4. In Namecheap Advanced DNS for letitglow.app, add the three CNAME records.
   Host format:
   [token]._domainkey.notify

5. In SES, configure custom MAIL FROM:
   bounce.notify.letitglow.app

6. In Namecheap, add:
   MX bounce.notify -> feedback-smtp.us-east-1.amazonses.com priority 10
   TXT bounce.notify -> v=spf1 include:amazonses.com -all

7. In Namecheap, add DMARC:
   TXT _dmarc.notify -> v=DMARC1; p=none; rua=mailto:dmarc@letitglow.app; adkim=s; aspf=r

8. In SES, attach default configuration set to notify.letitglow.app.

9. In SES, enable suppression for BOUNCE and COMPLAINT.

10. Create SES SMTP credentials for Keycloak.

11. Configure Keycloak:
    From: no-reply@notify.letitglow.app
    Envelope From: bounces@bounce.notify.letitglow.app
    Host: email-smtp.us-east-1.amazonaws.com
    Port: 587
    STARTTLS: enabled
    Auth: SES SMTP username/password

12. Test Keycloak email.

13. Use SES mailbox simulator to test delivery, bounce, and complaint flows.

14. Request SES production access as transactional only.

15. Roll out slowly and monitor daily.
```
