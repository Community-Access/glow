# PRD: Transactional Email Architecture for GLOW Using Amazon SES, Keycloak, and Optional AgentMail

**Product:** GLOW — Guided Layout & Output Workflow  
**Primary umbrella domain:** `letitglow.app`  
**Primary public site:** `https://letitglow.app`  
**Primary owner:** Blind Information Technology Solutions (BITS) / GLOW project leadership  
**Prepared for:** Jeff Bishop  
**Prepared on:** May 25, 2026  
**Document status:** Implementation-ready draft  
**Recommended first milestone:** Keycloak identity email + GLOW feedback/admin transactional email through Amazon SES

---

## 1. Executive Summary

GLOW needs a reliable, privacy-conscious, accessible, and governable email architecture for service-related transactional messages. The recommended architecture is:

```text
Keycloak + Amazon SES SMTP
  Identity email:
  - email verification
  - password reset
  - required actions
  - administrative account notifications

GLOW application + Amazon SES API v2
  Application transactional email:
  - feedback confirmations
  - feedback routing to administrators
  - operational alerts
  - optional future job-completion notices

AgentMail
  Future optional module only:
  - agent-owned inboxes
  - AI support triage
  - threaded agent conversations
  - inbound workflow intake
```

Amazon SES should be presented to AWS as a **low-volume, controlled, transactional email system** for GLOW. It should not be represented as a newsletter system, campaign platform, convention promotion tool, fundraising blast tool, or general BITS community mailing service.

Keycloak improves the design because it moves identity email into a mature identity provider, while SES remains the delivery, authentication, reputation, bounce, complaint, and suppression layer.

AgentMail can be valuable later, but it should remain **out of scope for Phase 1**. It is an inbox API for AI agents, not the right foundation for Keycloak password resets or GLOW transactional notices.

### 1.1 Domain refactor decision: letitglow.app

This PRD has been refactored so that `letitglow.app` is the public and technical umbrella domain for GLOW. BITS remains the sponsoring organization and governance home, but GLOW transactional email, Keycloak identity email, future agent inboxes, DNS authentication, bounce handling, and AWS SES production-access language should be aligned under the `letitglow.app` domain family.

Recommended domain layout:

```text
letitglow.app
  Primary public site and application entry point

notify.letitglow.app
  Amazon SES verified identity for transactional email

bounce.notify.letitglow.app
  Amazon SES custom MAIL FROM and bounce domain

agents.letitglow.app
  Future AgentMail/agent-inbox subdomain, out of scope for Phase 1
```

If `glow.bits-acb.org` remains active during transition, it should be treated as a legacy or redirect domain, not the primary SES sending identity. Avoid mixing sender reputation between `bits-acb.org` and `letitglow.app` unless there is a specific governance reason to do so.

---

## 2. Product Problem

GLOW needs to send important service email without creating deliverability, privacy, accessibility, or abuse-management problems.

Current and future GLOW workflows may require:

- Account verification and password reset messages.
- Administrator sign-in and required-action messages.
- Feedback confirmations.
- Feedback routing to GLOW maintainers or administrators.
- Security and operational alerts.
- Optional job-completion notices when a user explicitly requests notification.
- Future receipts or acknowledgments if GLOW adds donations, sponsorship workflows, paid services, or institutional access.

Without a governed architecture, email can become a risk:

- Poor deliverability.
- Bounces and complaints damaging sender reputation.
- AWS SES production access denial.
- Privacy concerns if files, reports, or generated outputs are emailed.
- Inaccessible email templates.
- Uncontrolled email paths inside application code.
- Confusion between transactional email and BITS communications.

---

## 3. Goals

### 3.1 Business and mission goals

1. Support GLOW’s accessibility mission with reliable transactional email.
2. Protect the reputation of GLOW, BITS, and the `letitglow.app` domain, while preserving BITS as the sponsoring organization.
3. Preserve GLOW’s privacy-forward posture.
4. Make the Amazon SES production-access request honest, clear, and low-risk.
5. Keep the system simple enough to operate by a small team.
6. Support future growth without starting with an overbuilt or risky architecture.

### 3.2 Technical goals

1. Use Amazon SES as the primary transactional delivery provider.
2. Use Keycloak for identity-related email.
3. Use a dedicated GLOW transactional sending subdomain.
4. Implement DKIM, SPF, DMARC, and a custom MAIL FROM domain.
5. Use SES configuration sets for monitoring and event publishing.
6. Enable bounce and complaint suppression.
7. Store email events in an audit log.
8. Build accessible email templates.
9. Prevent direct email sending outside the approved service layer.
10. Separate future agent inboxes from transactional email.

### 3.3 Compliance and trust goals

1. Do not send unsolicited email.
2. Do not send marketing through the transactional SES identity.
3. Do not use purchased, scraped, rented, or third-party lists.
4. Do not email uploaded files, converted documents, extracted text, or private accessibility reports.
5. Suppress hard bounces and complaints.
6. Maintain clear public privacy and notification language.

---

## 4. Non-Goals

This project does **not** include:

```text
BITS newsletters
GLOW promotional campaigns
ACB convention announcements
Fundraising blasts
Marketing automation
Cold outreach
Imported mailing lists
Purchased or scraped lists
Bulk community email
Emailing user-uploaded files
Emailing converted output files
Emailing private accessibility audit results by default
Using AgentMail for Keycloak password resets
Using AgentMail for core transactional delivery
```

If newsletters, convention announcements, or broad community outreach are needed, use a separate, opt-in email marketing platform with its own consent, unsubscribe, and reputation model.

---

## 5. Key Design Decision

### 5.1 Three-lane email architecture

```text
Lane 1: Identity Email
Provider path: Keycloak → Amazon SES SMTP
Purpose: account verification, password reset, required actions, account security messages
Domain: notify.letitglow.app
Out of scope: marketing, newsletters, document delivery

Lane 2: GLOW Application Transactional Email
Provider path: GLOW → Amazon SES API v2
Purpose: feedback confirmations, admin notifications, system alerts, optional job-completion notices
Domain: notify.letitglow.app
Out of scope: identity flows already handled by Keycloak

Lane 3: Future Agent Inboxes
Provider path: GLOW agents → AgentMail
Purpose: future AI-agent inboxes, support triage, inbound workflow classification, threaded agent conversations
Domain: agents.letitglow.app
Out of scope for Phase 1
```

### 5.2 Why this split matters

Keycloak should own identity email because it already controls accounts, realms, password reset, required actions, and account security flows.

GLOW should own application email because it understands feedback, jobs, workflows, and operational alerts.

Amazon SES should own deliverability and reputation controls.

AgentMail should only be introduced if GLOW later needs **email inboxes for AI agents**, not merely a way to send transactional messages.

---

## 6. Domain and Identity Strategy

The operational rule is simple: **all GLOW-generated transactional mail should live under `letitglow.app`, not under personal addresses or the broader BITS organizational domain.** This keeps GLOW deliverability, privacy, governance, and reputation management clean.

### 6.1 Recommended sending subdomain

```text
notify.letitglow.app
```

### 6.2 Recommended MAIL FROM / bounce domain

```text
bounce.notify.letitglow.app
```

### 6.3 Recommended future AgentMail subdomain

```text
agents.letitglow.app
```

### 6.4 Recommended sender addresses

```text
no-reply@notify.letitglow.app
security@notify.letitglow.app
support@notify.letitglow.app
feedback@notify.letitglow.app
alerts@notify.letitglow.app
```

### 6.5 Recommended human support addresses

Use these for user-facing replies, website contact forms, and internal administration. These do not need to be the primary SES From addresses unless explicitly verified and governed.

```text
support@letitglow.app
admin@letitglow.app
dmarc@letitglow.app
```

### 6.6 Recommended display names

```text
GLOW
GLOW Security
GLOW Support
GLOW Feedback
GLOW System Alerts
```

### 6.7 Domain separation policy

Use the dedicated GLOW notification subdomain only for transactional email.

Do not use:

```text
jeff@...
personal addresses
general BITS list addresses
individual officer addresses
board or committee list addresses
```

for system-generated GLOW email. Human support addresses such as `support@letitglow.app` or `admin@letitglow.app` may be used for replies and contact workflows, but automated From addresses should remain under `notify.letitglow.app` unless a new sender identity is intentionally approved.

---

## 7. Amazon SES Production Access Strategy

### 7.1 Desired AWS framing

The AWS request should be honest and specific:

> GLOW uses Amazon SES for low-volume transactional email. Identity email is generated by Keycloak and delivered through SES SMTP. Application-specific email is generated by GLOW and delivered through SES API v2. Recipients are users or administrators who initiated an action, have an account relationship, submitted feedback, or requested a service notification. GLOW does not use SES for marketing, newsletters, purchased lists, scraped lists, convention announcements, fundraising blasts, or unsolicited outreach.

### 7.2 Avoid the phrase “full access”

Use:

```text
production access
move out of the SES sandbox
transactional sending access
modest initial sending quota
```

Avoid:

```text
full access
unrestricted sending
bulk email capability
send to everyone
campaigns
blasts
mailing lists
```

### 7.3 Initial quota recommendation

Request a conservative quota:

```text
Daily quota: 1,000 recipients/day
Maximum send rate: 1 to 5 recipients/second
Mail type: Transactional
Primary Region: us-east-1, unless hosting or operations require another Region
```

This is enough for early GLOW use while avoiding the appearance of a bulk sender.

### 7.4 Production access request text

Use this as the core request narrative:

```text
GLOW, Guided Layout & Output Workflow, is a free accessibility workflow tool sponsored by Blind Information Technology Solutions. GLOW helps users and administrators work with accessibility-related workflows such as auditing, fixing, converting, and preparing digital content.

We are requesting Amazon SES production access for low-volume transactional email only.

GLOW uses Keycloak as its identity and access management provider. Identity-related transactional messages, such as email verification, password reset, required actions, and account-related administrative notices, are generated by Keycloak and delivered through Amazon SES SMTP.

The GLOW application itself sends only limited service-related transactional messages, such as feedback confirmations, feedback routing to administrators, operational alerts, and future optional job-completion notices requested by users.

We will not use this SES configuration for newsletters, promotional campaigns, convention announcements, fundraising blasts, cold outreach, or unsolicited bulk email. We do not use purchased, rented, scraped, or third-party mailing lists.

Uploaded files, converted documents, extracted text, private accessibility reports, and user API keys are not emailed. Transactional messages contain only minimal service information necessary for the specific action.

Recipients are administrators of the service, users who initiated an action on the site, or individuals who submitted feedback and provided an email address for confirmation.

We will configure a verified sending domain, DKIM, SPF, DMARC, a custom MAIL FROM domain, SES configuration sets, event notifications, CloudWatch monitoring, and account-level suppression for bounces and complaints.

Initial expected volume is modest: approximately 50 to 300 messages per day, with occasional peaks during workshops, testing events, or public demonstrations. We are requesting a conservative initial quota and will request increases only after establishing healthy sending history.
```

### 7.5 If AWS asks for more information

Respond with concrete answers:

```text
Message types:
- Keycloak verification emails
- Keycloak password reset emails
- Keycloak required-action emails
- feedback confirmations
- admin feedback notices
- operational alerts
- optional user-requested job-completion notices

Recipient source:
- GLOW administrators
- authenticated users
- users who request account actions
- users who submit feedback and provide an email address
- users who explicitly request job-completion notification

List policy:
- no purchased lists
- no scraped lists
- no rented lists
- no imported third-party lists
- no bulk marketing lists

Bounce handling:
- hard bounces are suppressed
- complaints are suppressed
- SES account-level suppression is enabled
- application-level suppression prevents future sends
- admins review unusual events

Privacy:
- no uploaded files
- no generated files
- no extracted document text
- no private accessibility report content
- no API keys
- no sensitive stack traces
```

---

## 8. Authoritative Source Notes

The implementation plan in this PRD is based on current documentation from AWS, Keycloak, and AgentMail.

Key points:

- Amazon SES production access is required to move out of the sandbox; once in production, you may send to arbitrary recipients, but sender identities still must be verified.  
  Source: <https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html>

- SES sandbox accounts are limited to verified recipients, 200 messages per 24-hour period, and 1 message per second.  
  Source: <https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html>

- SES verified identities can be domains, subdomains, or email addresses; domain verification requires DNS access.  
  Source: <https://docs.aws.amazon.com/ses/latest/dg/creating-identities.html>

- A custom MAIL FROM domain requires DNS records including MX and SPF/TXT records.  
  Source: <https://docs.aws.amazon.com/ses/latest/dg/mail-from.html>

- DMARC uses SPF and DKIM to detect spoofing and phishing; using both provides stronger protection.  
  Source: <https://docs.aws.amazon.com/ses/latest/dg/send-email-authentication-dmarc.html>

- SES account-level suppression can be configured for bounces and complaints.  
  Source: <https://docs.aws.amazon.com/ses/latest/dg/sending-email-suppression-list.html>

- SES SMTP credentials are not the same as normal AWS credentials and are Region-specific.  
  Source: <https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html>

- SES supports STARTTLS on ports 25, 587, or 2587 and TLS Wrapper on ports 465 or 2465.  
  Source: <https://docs.aws.amazon.com/ses/latest/dg/smtp-connect.html>

- Keycloak sends email for verification, forgotten passwords, and server-event/admin notifications when SMTP settings are configured for a realm.  
  Source: <https://www.keycloak.org/docs/latest/server_admin/index.html>

- Keycloak’s realm email settings include From, Reply-To, Envelope from, Host, Port, encryption, authentication, username, and password/token settings; AWS SMTP requires password authentication rather than XOAUTH2.  
  Source: <https://www.keycloak.org/docs/latest/server_admin/index.html>

- AgentMail describes itself as an email inbox API for AI agents and supports API-managed inboxes, threads/replies, attachments, realtime events, custom domains, SDKs/MCP, semantic search, and data extraction.  
  Source: <https://www.agentmail.to/>

---

## 9. Functional Requirements

### 9.1 Keycloak identity email requirements

Keycloak shall send:

```text
email_verification
password_reset
required_action
account_update_notice
admin_initiated_action
```

Keycloak shall not send:

```text
newsletters
announcements
marketing
BITS community messages
campaigns
document outputs
audit reports
```

### 9.2 GLOW application email requirements

GLOW shall send:

```text
feedback_confirmation
feedback_admin_notice
system_error_alert
security_alert_for_application_events
optional_job_completion_notice
future_receipt_or_acknowledgment
```

GLOW shall not send:

```text
identity email owned by Keycloak
uploaded files
converted files
private audit reports
API keys
document extraction content
bulk messages
```

### 9.3 AgentMail future requirements

AgentMail may be considered later for:

```text
agent-owned inboxes
support triage
threaded agent conversations
inbound request classification
workshop intake
AI accessibility-agent communication
```

AgentMail shall not be used for Phase 1.

AgentMail shall not be used for:

```text
Keycloak account verification
Keycloak password reset
core transactional sending
bulk outreach
marketing
newsletters
automatic document-processing intake without privacy review
```

---

## 10. Privacy and Data Handling Requirements

### 10.1 Prohibited email content

No GLOW transactional email may include:

```text
uploaded files
converted files
Braille output files
audio output files
PDF output files
Word output files
extracted text
private accessibility reports
full audit results
document screenshots
API keys
temporary storage paths
internal job IDs that expose infrastructure
server stack traces containing user data
long-lived public download links
```

### 10.2 Allowed email content

Emails may include:

```text
service name
reason for message
date and approximate time
generic workflow type
short-lived identity link from Keycloak
feedback ticket/reference number
support instructions
privacy reminder
```

### 10.3 Job-completion notices

Optional job-completion notices must be:

```text
opt-in per job
off by default
minimal
no attachments
no output links in Phase 1
no file content
no extracted text
no full reports
```

Suggested content:

```text
Your requested GLOW process has completed.

For your privacy, GLOW does not attach uploaded files, converted files, document text, or private accessibility results to email. Please return to the same browser session to download your result.
```

### 10.4 Public privacy language to add to GLOW

Add a section to GLOW’s privacy or help page:

```text
Transactional Email

GLOW may send limited transactional email related to use or administration of the service, such as account verification, password reset messages, administrator notices, feedback confirmations, security notices, and optional user-requested job-completion notices.

GLOW does not send uploaded files, converted documents, extracted text, private accessibility reports, user API keys, or generated outputs by email.

GLOW does not use this notification system for marketing, newsletters, campaign messages, convention announcements, fundraising blasts, purchased lists, scraped lists, or unsolicited bulk email.
```

---

## 11. Accessibility Requirements for Email

All user-facing email must be accessible.

### 11.1 Plain text

Every template shall have a plain-text version.

### 11.2 HTML email

HTML email shall:

```text
use semantic headings
use short paragraphs
place the purpose near the top
use meaningful link text
avoid image-only meaning
avoid color-only meaning
avoid tiny text
avoid unexplained symbols
avoid emoji as required meaning
avoid dense tables
include support/contact information
```

### 11.3 Link text

Good:

```text
Sign in to GLOW
Reset your GLOW password
View your feedback confirmation
Contact GLOW support
```

Bad:

```text
Click here
Here
Read more
This link
```

### 11.4 Screen reader review

Each template shall be reviewed with:

```text
keyboard only
screen reader reading order
plain-text mode
mobile email client if practical
```

---

## 12. Technical Architecture

### 12.1 High-level architecture

```text
Keycloak Realm
  ↓ SMTP
Amazon SES SMTP endpoint
  ↓
SES verified identity: notify.letitglow.app
  ↓
Default SES configuration set: glow-transactional-production
  ↓
SES event destinations
  ↓
SNS/EventBridge
  ↓
Webhook/Lambda event processor
  ↓
GLOW email_events + email_suppressions
  ↓
Admin monitoring dashboard
```

```text
GLOW Application
  ↓
Internal email service/module
  ↓
Queue + rate limiter
  ↓
Amazon SES API v2
  ↓
SES configuration set: glow-transactional-production
  ↓
Same event and suppression pipeline
```

```text
Future AgentMail Module
  ↓
AgentMail inboxes on agents.letitglow.app
  ↓
Human-approved or policy-controlled agent responses
  ↓
Separate logs and privacy review
```

### 12.2 Configuration set strategy

Create one initial configuration set:

```text
glow-transactional-production
```

Assign it as the default configuration set to:

```text
notify.letitglow.app
```

This matters because Keycloak may not easily add custom SES headers. A default configuration set at the verified identity helps ensure Keycloak-generated mail is still covered by SES event processing.

### 12.3 Event processing strategy

Capture at least:

```text
SEND
DELIVERY
BOUNCE
COMPLAINT
REJECT
RENDERING_FAILURE
DELIVERY_DELAY
```

Do not enable open or click tracking in Phase 1 unless there is a strong operational reason. GLOW should prioritize privacy and minimalism over engagement analytics.

---

## 13. Data Model

### 13.1 `email_messages`

```sql
CREATE TABLE email_messages (
    id BIGSERIAL PRIMARY KEY,
    message_uuid UUID NOT NULL UNIQUE,
    ses_message_id TEXT,
    provider TEXT NOT NULL DEFAULT 'ses',
    source_system TEXT NOT NULL, -- keycloak or glow
    recipient_email TEXT NOT NULL,
    recipient_hash TEXT NOT NULL,
    sender_email TEXT NOT NULL,
    email_type TEXT NOT NULL,
    template_name TEXT NOT NULL,
    template_version TEXT NOT NULL,
    subject TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    configuration_set TEXT,
    triggering_event TEXT,
    related_object_type TEXT,
    related_object_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    queued_at TIMESTAMP,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    bounced_at TIMESTAMP,
    complained_at TIMESTAMP,
    rejected_at TIMESTAMP,
    failed_at TIMESTAMP,
    last_error TEXT
);
```

### 13.2 `email_events`

```sql
CREATE TABLE email_events (
    id BIGSERIAL PRIMARY KEY,
    message_uuid UUID,
    ses_message_id TEXT,
    provider TEXT NOT NULL DEFAULT 'ses',
    event_type TEXT NOT NULL,
    event_payload JSONB NOT NULL,
    recipient_email TEXT,
    recipient_hash TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 13.3 `email_suppressions`

```sql
CREATE TABLE email_suppressions (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    email_hash TEXT NOT NULL,
    reason TEXT NOT NULL, -- bounce, complaint, manual, unsubscribe, abuse
    source TEXT NOT NULL, -- ses, admin, user, migration
    provider_message_id TEXT,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    manually_reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT
);
```

### 13.4 `email_templates`

```sql
CREATE TABLE email_templates (
    id BIGSERIAL PRIMARY KEY,
    template_name TEXT NOT NULL,
    template_version TEXT NOT NULL,
    subject_template TEXT NOT NULL,
    text_body_template TEXT NOT NULL,
    html_body_template TEXT,
    source_system TEXT NOT NULL, -- keycloak or glow
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(template_name, template_version)
);
```

### 13.5 `email_policy_audit`

```sql
CREATE TABLE email_policy_audit (
    id BIGSERIAL PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target_email_hash TEXT,
    details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

---

## 14. Step-by-Step Implementation Walkthrough

## Phase 0: Decisions and Preparation

### Step 0.1: Choose one AWS Region

Recommended:

```text
us-east-1
```

Record the decision:

```text
GLOW_SES_REGION=us-east-1
```

Important: SES identities, SMTP credentials, production access status, quotas, and configuration are Region-specific. Do not split the initial implementation across multiple Regions.

### Step 0.2: Confirm scope

Phase 1 includes:

```text
Keycloak email verification
Keycloak password reset
Keycloak required action
Keycloak administrative notices
GLOW feedback confirmation
GLOW feedback admin notice
GLOW system alerts
SES bounce and complaint processing
SES suppression
CloudWatch monitoring
```

Phase 1 excludes:

```text
job-completion notices
attachments
download links
audit reports by email
AgentMail
newsletters
marketing
bulk email
```

### Step 0.3: Confirm DNS control

You need access to DNS for:

```text
letitglow.app
notify.letitglow.app
bounce.notify.letitglow.app
```

If DNS is managed outside AWS Route 53, confirm who can add CNAME, MX, and TXT records.

### Step 0.4: Prepare public site language

Before requesting production access, add or update pages for:

```text
About GLOW
Contact
Privacy
Transactional Email
Support
```

AWS reviewers should see a real, legitimate, non-placeholder site.

---

## Phase 1: AWS Account Hygiene

### Step 1.1: Secure the AWS account

Required:

```text
MFA enabled for root
MFA enabled for admin users
No root access keys
CloudTrail enabled
Billing alerts enabled
Least-privilege IAM
No SES credentials in GitHub
No SES credentials in public config
```

### Step 1.2: Create a budget alert

Create a modest AWS budget alert, for example:

```text
Monthly budget alert: $25 or $50
Alert at: 50%, 80%, 100%
```

### Step 1.3: Create IAM structure

Recommended IAM identities:

```text
glow-ses-api-sender
glow-keycloak-ses-smtp
glow-ses-admin-readonly
```

Use separate credentials for Keycloak SMTP and GLOW API sending. This improves rotation and incident response.

---

## Phase 2: Create SES Domain Identity

### Step 2.1: Open SES

Go to:

```text
Amazon SES → Configuration → Identities → Create identity
```

### Step 2.2: Create domain identity

Identity type:

```text
Domain
```

Domain:

```text
notify.letitglow.app
```

Enable:

```text
Easy DKIM
DKIM signing
```

### Step 2.3: Assign default configuration set later

If the configuration set already exists, assign it during identity creation. If not, return after creating the configuration set.

### Step 2.4: Publish DKIM DNS records

SES will provide DKIM CNAME records. Add all provided CNAME records to DNS.

### Step 2.5: Wait for verification

SES identity status should become:

```text
Verified
```

---

## Phase 3: Create SES Configuration Set

### Step 3.1: Create configuration set

Name:

```text
glow-transactional-production
```

AWS CLI example:

```bash
aws sesv2 create-configuration-set \
  --configuration-set-name glow-transactional-production \
  --region us-east-1
```

### Step 3.2: Assign default configuration set to identity

```bash
aws sesv2 put-email-identity-configuration-set-attributes \
  --email-identity notify.letitglow.app \
  --configuration-set-name glow-transactional-production \
  --region us-east-1
```

### Step 3.3: Disable open/click tracking in Phase 1

Do not configure open/click tracking initially. GLOW does not need engagement analytics for identity and service email.

---

## Phase 4: Configure Custom MAIL FROM

### Step 4.1: Set MAIL FROM domain

MAIL FROM domain:

```text
bounce.notify.letitglow.app
```

### Step 4.2: Add MX record

For `us-east-1`:

```text
Name: bounce.notify.letitglow.app
Type: MX
Value: 10 feedback-smtp.us-east-1.amazonses.com
```

If you choose a different Region, use the correct Regional feedback SMTP host.

### Step 4.3: Add SPF record for MAIL FROM

```text
Name: bounce.notify.letitglow.app
Type: TXT
Value: "v=spf1 include:amazonses.com -all"
```

### Step 4.4: Verify MAIL FROM status

SES should show custom MAIL FROM as successful.

---

## Phase 5: Configure DMARC

### Step 5.1: Start with monitoring mode

```text
Name: _dmarc.notify.letitglow.app
Type: TXT
Value: "v=DMARC1; p=none; rua=mailto:CHANGE-ME-DMARC-REPORTING-ADDRESS; adkim=s; aspf=r"
```

Replace `CHANGE-ME-DMARC-REPORTING-ADDRESS` with an address or DMARC reporting service you control. Use relaxed SPF alignment because the custom MAIL FROM domain is `bounce.notify.letitglow.app`, while the visible From domain is `notify.letitglow.app`. DKIM should still be strictly aligned to the visible From domain.

### Step 5.2: Monitor reports

Review DMARC aggregate reports for:

```text
alignment failures
unexpected senders
spoofing attempts
misconfigured subdomains
```

### Step 5.3: Move to stricter policy after stabilization

After stable sending:

```text
p=quarantine
```

Long-term, after confidence:

```text
p=reject
```

---

## Phase 6: Configure Suppression

### Step 6.1: Enable account-level suppression

```bash
aws sesv2 put-account-suppression-attributes \
  --suppressed-reasons BOUNCE COMPLAINT \
  --region us-east-1
```

### Step 6.2: Configure suppression for the configuration set

```bash
aws sesv2 put-configuration-set-suppression-options \
  --configuration-set-name glow-transactional-production \
  --suppressed-reasons BOUNCE COMPLAINT \
  --region us-east-1
```

### Step 6.3: Build application-level suppression

Before GLOW sends any app-specific email:

```text
Check local suppression table.
Check message type eligibility.
Check rate limits.
Check whether user opted in for optional notices.
Reject send if suppression applies.
```

### Step 6.4: Suppression rules

```text
Hard bounce:
  suppress immediately

Complaint:
  suppress immediately

Repeated soft bounce:
  suppress after threshold

Manual suppression:
  admin may suppress with reason

Manual removal:
  allowed only with documented reason

Complaint removal:
  require strong evidence of user consent or correction
```

---

## Phase 7: Configure Event Publishing

### Step 7.1: Choose event destination

Recommended Phase 1:

```text
SNS topic: glow-ses-events
```

Alternative:

```text
EventBridge
```

SNS is simple and works well with either a Lambda processor or HTTPS webhook.

### Step 7.2: Create SNS topic

```bash
aws sns create-topic \
  --name glow-ses-events \
  --region us-east-1
```

### Step 7.3: Add SES event destination

Configure `glow-transactional-production` to publish these events:

```text
SEND
DELIVERY
BOUNCE
COMPLAINT
REJECT
RENDERING_FAILURE
DELIVERY_DELAY
```

### Step 7.4: Create event processor

Options:

```text
Option A: SNS → AWS Lambda → GLOW database
Option B: SNS → HTTPS webhook → GLOW application
Option C: EventBridge → Lambda → GLOW database
```

Recommended for simplicity:

```text
SNS → Lambda → GLOW API endpoint or database
```

### Step 7.5: Event processor responsibilities

```text
Validate incoming event authenticity.
Parse SES event type.
Store raw event payload.
Map SES message ID to local email record.
Update email status.
Suppress hard bounces.
Suppress complaints.
Notify administrator on complaint.
Notify administrator on unusual bounce spike.
```

---

## Phase 8: Create SES SMTP Credentials for Keycloak

### Step 8.1: Create SMTP credentials

Go to:

```text
Amazon SES → SMTP settings → Create SMTP credentials
```

Name:

```text
glow-keycloak-ses-smtp
```

Save:

```text
SMTP username
SMTP password
```

Important: SES SMTP credentials are not the same as normal AWS access keys and are Region-specific.

### Step 8.2: Store credentials securely

Preferred:

```text
environment variables
container secrets
server secret manager
Keycloak vault if configured
```

Avoid:

```text
source code
GitHub
plain text deployment notes
shared documents
WordPress admin fields unless unavoidable
```

---

## Phase 9: Configure Keycloak Email

### Step 9.1: Open the correct realm

In Keycloak Admin Console:

```text
Select GLOW realm
Realm settings
Email tab
```

### Step 9.2: Configure template fields

```text
From:
no-reply@notify.letitglow.app

From display name:
GLOW

Reply to:
support@letitglow.app

Reply to display name:
GLOW Support

Envelope from:
bounce.notify.letitglow.app
```

### Step 9.3: Configure SMTP connection

For `us-east-1`:

```text
Host:
email-smtp.us-east-1.amazonaws.com

Port:
587

Encryption:
StartTLS

Authentication:
On

Authentication Type:
Password

Username:
[SES SMTP username]

Password:
[SES SMTP password]
```

If port 587 fails, test TLS Wrapper:

```text
Port:
465

Encryption:
SSL/TLS
```

### Step 9.4: Send Keycloak test email

Use Keycloak’s test connection feature.

Expected result:

```text
Test email delivered.
SES event logged.
Configuration set applied.
No bounce or complaint.
```

### Step 9.5: Enable forgot password if desired

In Keycloak:

```text
Realm settings
Login tab
Forgot password: ON
```

Confirm that email settings are configured before enabling or testing reset flows.

### Step 9.6: Review Keycloak email templates

Review or customize Keycloak email theme templates for:

```text
plain language
GLOW branding
meaningful links
minimal content
no marketing language
no unnecessary graphics
accessibility
```

---

## Phase 10: Create GLOW SES API Sender

### Step 10.1: Create IAM user or role

Name:

```text
glow-ses-api-sender
```

### Step 10.2: Least-privilege policy concept

Start with this concept and narrow by verified identity ARN if practical:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SendGlowTransactionalEmail",
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail"
      ],
      "Resource": "*"
    }
  ]
}
```

Avoid allowing unrelated AWS services.

### Step 10.3: Store credentials securely

Preferred:

```text
IAM role attached to server
environment variables
secret manager
restricted deployment secret
```

Avoid:

```text
hard-coded keys
GitHub repository secrets that are over-broad
logs
admin UI display
```

---

## Phase 11: Build GLOW Internal Email Module

### Step 11.1: Suggested module structure

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
  validators.py
```

### Step 11.2: Required central send function

```python
def send_transactional_email(
    recipient: str,
    email_type: str,
    template_name: str,
    context: dict,
    triggering_event: str,
    related_object_type: str | None = None,
    related_object_id: str | None = None,
) -> str:
    """
    Sends approved GLOW transactional email through Amazon SES.
    Rejects unknown types, suppressed recipients, and disallowed content.
    Returns local message UUID.
    """
```

### Step 11.3: Approved email type registry

```python
ALLOWED_EMAIL_TYPES = {
    "feedback_confirmation",
    "feedback_admin_notice",
    "system_error_alert",
    "application_security_alert",
    "optional_job_completion_notice",
}
```

### Step 11.4: Explicitly rejected types

```python
REJECTED_EMAIL_TYPES = {
    "newsletter",
    "marketing",
    "fundraising_blast",
    "convention_announcement",
    "community_update",
    "bulk_import",
    "document_attachment",
    "audit_report_delivery",
}
```

### Step 11.5: Content safety validator

Before sending, scan context for prohibited fields:

```python
PROHIBITED_CONTEXT_KEYS = {
    "uploaded_file",
    "uploaded_file_path",
    "converted_file",
    "converted_file_path",
    "extracted_text",
    "api_key",
    "access_token",
    "refresh_token",
    "stack_trace",
    "document_contents",
    "audit_report_body",
}
```

If prohibited fields are present, reject the send and log a policy violation.

---

## Phase 12: Build Queue and Rate Limiting

### Step 12.1: Queue requirement

All application email should go through a queue.

Recommended queue options:

```text
database-backed queue
Redis queue
Celery/RQ if Python-based
SQS if staying in AWS
```

### Step 12.2: Rate limits

Initial limits:

```text
Global GLOW app email: 1 message/second
Feedback confirmation: 3 per recipient per hour
Feedback admin notice: grouped if spam detected
System alerts: deduplicate within 10-minute windows
Job-completion notice: 1 per job, only if opted in
```

### Step 12.3: Retry policy

```text
Transient SES error:
  retry with exponential backoff

Throttling:
  retry with backoff and respect quota

Hard bounce:
  no retry

Complaint:
  no retry

Suppressed recipient:
  no send

Policy violation:
  no send, alert admin
```

---

## Phase 13: Templates

### Step 13.1: Initial GLOW templates

```text
feedback_confirmation.txt
feedback_confirmation.html
feedback_admin_notice.txt
feedback_admin_notice.html
system_error_alert.txt
system_error_alert.html
application_security_alert.txt
application_security_alert.html
```

### Step 13.2: Future templates

```text
optional_job_completion_notice.txt
optional_job_completion_notice.html
receipt_acknowledgment.txt
receipt_acknowledgment.html
```

### Step 13.3: Universal footer for user-facing GLOW email

```text
You are receiving this message because you or an administrator initiated an action in GLOW.

GLOW does not send uploaded files, converted files, extracted document text, private accessibility results, or user API keys by email.

GLOW is a project sponsored by Blind Information Technology Solutions.
```

### Step 13.4: Universal footer for optional job-completion notice

```text
You requested this job-completion notice. For your privacy, GLOW does not attach your files or generated outputs to email.
```

---

## Phase 14: Test in SES Sandbox

### Step 14.1: Verify test recipients

While in sandbox, verify test recipient addresses or use the SES mailbox simulator.

### Step 14.2: Test Keycloak flows

Test:

```text
email verification
password reset
required action
administrator-initiated action email
test SMTP connection
```

### Step 14.3: Test GLOW app flows

Test:

```text
feedback confirmation
feedback admin notice
system alert
policy rejection for prohibited content
suppressed recipient rejection
rate-limit rejection
```

### Step 14.4: Test SES event handling

Use simulator/test patterns to confirm:

```text
delivery event captured
bounce event captured
complaint event captured
reject event captured
suppression update performed
admin alert triggered
```

### Step 14.5: Accessibility testing

For every template:

```text
plain-text version exists
HTML has semantic structure
links have meaningful text
purpose is near top
screen reader order is logical
no image-only meaning
```

---

## Phase 15: Request SES Production Access

### Step 15.1: Pre-request checklist

```text
[ ] Website identifies GLOW clearly.
[ ] Privacy page includes transactional email language.
[ ] Contact/support information is available.
[ ] SES identity is verified.
[ ] DKIM records are verified.
[ ] Custom MAIL FROM is verified.
[ ] SPF is configured.
[ ] DMARC exists.
[ ] Configuration set exists.
[ ] Default configuration set is assigned to identity.
[ ] Account-level suppression is enabled.
[ ] Event pipeline is tested.
[ ] Keycloak test email works.
[ ] GLOW test email works.
[ ] No marketing language appears in the request.
```

### Step 15.2: Submit request

In SES:

```text
Account dashboard
Request production access
Mail type: Transactional
Website URL: https://letitglow.app
Use case description: use Section 7.4
Requested daily quota: 1,000 recipients/day
Requested send rate: 1 to 5 recipients/second
```

### Step 15.3: If denied

Do not resubmit the same text.

Improve:

```text
website public legitimacy
privacy language
specific message types
specific recipient sources
lower quota
bounce/complaint proof
suppression description
DNS authentication proof
```

Then respond with:

```text
We have clarified that GLOW sends only transactional identity and service email. We have verified the domain, configured DKIM, SPF, DMARC, custom MAIL FROM, event notifications, and suppression for bounces and complaints. We do not send marketing, newsletters, purchased lists, scraped lists, or user files by email.
```

---

## Phase 16: Production Rollout

### Step 16.1: Enable Keycloak first

Enable:

```text
Keycloak verification email
Keycloak password reset email
Keycloak required-action email
```

Monitor for 3 to 7 days.

### Step 16.2: Enable GLOW feedback mail

Enable:

```text
feedback confirmation
feedback admin notice
```

Monitor for 1 to 2 weeks.

### Step 16.3: Enable system alerts

Enable:

```text
system_error_alert
application_security_alert
```

Group alerts to avoid noisy bursts.

### Step 16.4: Defer job-completion email

Enable only after stable metrics and explicit design review.

---

## 15. Monitoring and Operations

### 15.1 Daily monitoring during first month

Review:

```text
messages sent
deliveries
bounces
complaints
rejects
rendering failures
suppressed recipients
quota usage
unexpected volume spikes
Keycloak SMTP failures
GLOW API send failures
```

### 15.2 Weekly monitoring after stabilization

Review:

```text
bounce rate
complaint rate
suppression list
template failures
CloudWatch alarms
credential age
IAM policy scope
unusual recipient patterns
```

### 15.3 Alert triggers

Immediate review if:

```text
any complaint occurs
bounce rate spikes
send volume spikes unexpectedly
SES rejects increase
Keycloak password reset abuse appears
CloudWatch alarm fires
AWS sends reputation warning
unknown sender appears in DMARC reports
```

---

## 16. Admin Dashboard Requirements

Create:

```text
/admin/email
```

### 16.1 Dashboard sections

```text
Recent messages
Keycloak message events
GLOW app message events
Bounces
Complaints
Suppressed addresses
Template versions
Quota usage
CloudWatch health summary
Manual test email
Policy violations
```

### 16.2 Admin actions

```text
view message metadata
view event history
manually suppress address
remove suppression with documented reason
send test email to verified admin
export event log
view template version
```

### 16.3 Admin restrictions

Admins must not be able to:

```text
send bulk email
upload recipient lists
send marketing through this system
attach user files
email audit reports by default
override complaint suppressions casually
```

---

## 17. Security Requirements

### 17.1 Credential rules

```text
No AWS keys in source code.
No AWS keys in GitHub.
No AWS keys in downloadable logs.
No AWS keys in email.
No AWS keys visible in admin UI.
Use least privilege.
Rotate SES SMTP credentials.
Rotate API credentials.
Prefer IAM roles over long-lived keys where hosting supports it.
```

### 17.2 Keycloak security

```text
Use HTTPS.
Configure secure frontend URL.
Enable brute-force protection where appropriate.
Use short-lived reset links.
Review required actions.
Review email update workflow.
Limit admin privileges.
Audit admin events.
```

### 17.3 GLOW app security

```text
Centralize sending.
Reject unknown email types.
Reject prohibited content.
Rate-limit by recipient and workflow.
Log policy violations.
Protect webhooks.
Validate SNS signatures if using SNS HTTPS.
```

---

## 18. AgentMail Future Module

### 18.1 Decision

AgentMail is out of scope for Phase 1.

### 18.2 Why AgentMail is not Phase 1

AgentMail is designed for AI-agent inboxes and two-way agent email workflows. GLOW currently needs reliable transactional delivery and Keycloak identity email. SES is the better foundation for that.

### 18.3 Future AgentMail use cases

Potentially valuable later:

```text
GLOW support triage agent
GLOW accessibility audit intake agent
GLOW workshop intake agent
GLOW documentation assistant inbox
GLOW issue classification agent
```

### 18.4 Future AgentMail requirements

If implemented later:

```text
Use agents.letitglow.app.
Do not use AgentMail for Keycloak identity email.
Do not use AgentMail for SES production-access justification.
Do not use AgentMail for bulk mail.
Require human approval for outbound free-form agent replies.
Require templates or allow-lists for automated replies.
Do not allow automatic processing of sensitive attachments without privacy review.
Do not forward GLOW uploads or outputs into AgentMail by default.
```

### 18.5 Suggested future inboxes

```text
support-triage@agents.letitglow.app
feedback-agent@agents.letitglow.app
training-agent@agents.letitglow.app
audit-intake@agents.letitglow.app
```

---

## 19. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| AWS denies production access | Launch delay | Submit narrow transactional request with verified domain and controls |
| High bounce rate | SES review or pause | Validate addresses, suppress hard bounces, monitor events |
| Complaint event | Reputation damage | Send only expected mail, suppress immediately, review message type |
| Credential compromise | Abuse of SES | Least privilege, MFA, key rotation, no keys in GitHub |
| Keycloak SMTP misconfiguration | Password resets fail | Test SMTP, monitor errors, document settings |
| Configuration set not applied to Keycloak mail | Missing events | Assign default configuration set to identity |
| GLOW accidentally sends private content | Trust and privacy harm | Content validator, prohibited keys, template review |
| AgentMail introduced too early | Scope creep and privacy risk | Keep out of Phase 1 |
| Inaccessible email templates | User harm | Plain text and semantic HTML review |
| Email volume spikes during workshops | Quota/reputation issue | Queue, throttle, alert on spikes |

---

## 20. Acceptance Criteria

### 20.1 SES setup

```text
[ ] SES domain identity verified.
[ ] DKIM enabled and passing.
[ ] Custom MAIL FROM verified.
[ ] SPF configured.
[ ] DMARC configured.
[ ] Configuration set created.
[ ] Default configuration set assigned to identity.
[ ] Suppression enabled for bounces and complaints.
[ ] Event publishing configured.
[ ] CloudWatch alerts configured.
```

### 20.2 Keycloak setup

```text
[ ] Keycloak realm email settings configured.
[ ] Keycloak uses SES SMTP credentials.
[ ] From address uses notify.letitglow.app.
[ ] Envelope from uses bounce.notify.letitglow.app.
[ ] Password reset email works.
[ ] Verification email works.
[ ] Required-action email works.
[ ] Keycloak email events appear in SES event pipeline.
```

### 20.3 GLOW application setup

```text
[ ] Central email module created.
[ ] Queue implemented.
[ ] Rate limits implemented.
[ ] Approved email type registry implemented.
[ ] Unknown types rejected.
[ ] Suppressed recipients rejected.
[ ] Prohibited content rejected.
[ ] Templates have text and HTML versions.
[ ] Email events logged.
```

### 20.4 Privacy

```text
[ ] No uploaded files are emailed.
[ ] No converted files are emailed.
[ ] No extracted text is emailed.
[ ] No private audit reports are emailed.
[ ] No API keys are emailed.
[ ] Privacy page describes transactional email.
```

### 20.5 Accessibility

```text
[ ] Plain text version exists for every template.
[ ] HTML templates use semantic structure.
[ ] Link text is meaningful.
[ ] Purpose appears near top.
[ ] Templates work with screen readers.
```

### 20.6 Production access

```text
[ ] SES production request submitted as Transactional.
[ ] Request includes Keycloak identity-email explanation.
[ ] Request excludes marketing and bulk outreach.
[ ] Request includes bounce/complaint/suppression handling.
[ ] Initial quota request is conservative.
```

---

## 21. Implementation Backlog

### Epic 1: DNS and SES Identity

```text
Task 1.1: Choose AWS Region.
Task 1.2: Create notify.letitglow.app identity.
Task 1.3: Add DKIM records.
Task 1.4: Configure custom MAIL FROM.
Task 1.5: Add SPF record.
Task 1.6: Add DMARC record.
Task 1.7: Verify all DNS statuses.
```

### Epic 2: SES Monitoring and Suppression

```text
Task 2.1: Create configuration set.
Task 2.2: Assign configuration set to identity.
Task 2.3: Create SNS/EventBridge event destination.
Task 2.4: Enable account-level suppression.
Task 2.5: Enable configuration-set suppression.
Task 2.6: Create CloudWatch alarms.
Task 2.7: Build event processor.
```

### Epic 3: Keycloak Integration

```text
Task 3.1: Create SES SMTP credentials.
Task 3.2: Store credentials securely.
Task 3.3: Configure Keycloak realm Email tab.
Task 3.4: Test password reset.
Task 3.5: Test verification email.
Task 3.6: Review Keycloak templates.
Task 3.7: Confirm SES events are captured.
```

### Epic 4: GLOW Email Module

```text
Task 4.1: Create email module.
Task 4.2: Create allowed email type registry.
Task 4.3: Create content safety validator.
Task 4.4: Create queue.
Task 4.5: Create rate limiter.
Task 4.6: Create templates.
Task 4.7: Create event log.
Task 4.8: Create suppression checks.
```

### Epic 5: Admin Dashboard

```text
Task 5.1: Recent message list.
Task 5.2: Bounce and complaint list.
Task 5.3: Suppression management.
Task 5.4: Policy violation log.
Task 5.5: Manual test email.
Task 5.6: Export audit log.
```

### Epic 6: SES Production Access

```text
Task 6.1: Update public privacy language.
Task 6.2: Verify website completeness.
Task 6.3: Gather DNS/authentication proof.
Task 6.4: Submit production access request.
Task 6.5: Respond to AWS follow-up.
Task 6.6: Enable production sending gradually.
```

### Epic 7: Future AgentMail Review

```text
Task 7.1: Defer AgentMail until transactional email is stable.
Task 7.2: Define agent inbox privacy policy.
Task 7.3: Define human approval rules.
Task 7.4: Pilot one support triage inbox if needed.
```

---

## 22. Deployment Checklist

```text
[ ] AWS account secured.
[ ] SES Region chosen.
[ ] DNS access confirmed.
[ ] notify.letitglow.app identity created.
[ ] DKIM records published.
[ ] custom MAIL FROM configured.
[ ] bounce.notify.letitglow.app MX record published.
[ ] bounce.notify.letitglow.app SPF record published.
[ ] DMARC record published.
[ ] configuration set created.
[ ] default configuration set assigned.
[ ] SNS/EventBridge event destination configured.
[ ] account-level suppression enabled.
[ ] configuration-set suppression enabled.
[ ] Keycloak SMTP credentials created.
[ ] Keycloak Email tab configured.
[ ] Keycloak test email successful.
[ ] GLOW SES API credentials created.
[ ] GLOW email module built.
[ ] templates reviewed for accessibility.
[ ] content safety checks implemented.
[ ] event processor tested.
[ ] admin dashboard minimally available.
[ ] privacy page updated.
[ ] SES production access request submitted.
[ ] rollout begins with Keycloak only.
[ ] feedback email enabled after initial monitoring.
[ ] job-completion notices deferred.
[ ] AgentMail deferred.
```

---

## 23. Recommended Phase 1 Definition of Done

Phase 1 is complete when:

```text
Keycloak can send verification and password reset email through SES.
GLOW can send feedback confirmation and admin notices through SES API.
SES event publishing is working.
Bounces and complaints are suppressed.
Email templates are accessible.
No prohibited private content can be sent.
The public privacy page explains transactional email.
AWS production access has been requested or approved.
Monitoring and alerting are active.
```

---

## 24. Recommended Final Architecture Statement

Use this in internal documentation:

> GLOW uses Keycloak for identity management and Amazon SES for transactional email delivery. Keycloak sends account verification, password reset, and required-action messages through SES SMTP. GLOW sends limited application-specific transactional notices through SES API v2. SES provides sender authentication, configuration sets, event publishing, bounce and complaint monitoring, and suppression controls. AgentMail is reserved for future AI-agent inbox workflows and is not part of the core transactional email system.

---

## 25. Appendix A: DNS Record Examples

### DKIM

SES provides these. They will look similar to:

```text
[random]._domainkey.notify.letitglow.app CNAME [random].dkim.amazonses.com
[random]._domainkey.notify.letitglow.app CNAME [random].dkim.amazonses.com
[random]._domainkey.notify.letitglow.app CNAME [random].dkim.amazonses.com
```

Use the exact values from SES.

### MAIL FROM MX

```text
bounce.notify.letitglow.app MX 10 feedback-smtp.us-east-1.amazonses.com
```

### MAIL FROM SPF

```text
bounce.notify.letitglow.app TXT "v=spf1 include:amazonses.com -all"
```

### DMARC monitoring

```text
_dmarc.notify.letitglow.app TXT "v=DMARC1; p=none; rua=mailto:CHANGE-ME-DMARC-REPORTING-ADDRESS; adkim=s; aspf=r"
```

---

## 26. Appendix B: Keycloak Email Settings Snapshot

```text
Realm:
GLOW

Path:
Realm settings → Email

From:
no-reply@notify.letitglow.app

From display name:
GLOW

Reply to:
support@letitglow.app

Reply to display name:
GLOW Support

Envelope from:
bounce.notify.letitglow.app

Host:
email-smtp.us-east-1.amazonaws.com

Port:
587

Encryption:
StartTLS

Authentication:
On

Authentication Type:
Password

Username:
[SES SMTP username]

Password:
[SES SMTP password]
```

---

## 27. Appendix C: AWS CLI Command Summary

```bash
# Create configuration set
aws sesv2 create-configuration-set \
  --configuration-set-name glow-transactional-production \
  --region us-east-1

# Assign default configuration set to identity
aws sesv2 put-email-identity-configuration-set-attributes \
  --email-identity notify.letitglow.app \
  --configuration-set-name glow-transactional-production \
  --region us-east-1

# Enable account-level suppression
aws sesv2 put-account-suppression-attributes \
  --suppressed-reasons BOUNCE COMPLAINT \
  --region us-east-1

# Enable configuration-set suppression
aws sesv2 put-configuration-set-suppression-options \
  --configuration-set-name glow-transactional-production \
  --suppressed-reasons BOUNCE COMPLAINT \
  --region us-east-1

# Create SNS topic
aws sns create-topic \
  --name glow-ses-events \
  --region us-east-1
```

---

## 28. Appendix D: Message Type Governance

### Approved in Phase 1

```text
keycloak_email_verification
keycloak_password_reset
keycloak_required_action
keycloak_admin_action
glow_feedback_confirmation
glow_feedback_admin_notice
glow_system_error_alert
glow_application_security_alert
```

### Approved later only after review

```text
glow_optional_job_completion_notice
glow_receipt_acknowledgment
glow_institution_invitation
glow_workshop_account_notice
```

### Not approved

```text
newsletter
marketing
fundraising_blast
campaign
convention_announcement
bulk_list_send
document_delivery
audit_report_delivery
agent_freeform_outbound_without_review
```

---

## 29. Appendix E: AgentMail Future Scope Language

Use this language if adding AgentMail to roadmap documentation:

> AgentMail may be evaluated in a future phase as an email inbox API for GLOW accessibility agents. Its purpose would be to support controlled agent-owned inboxes for support triage, inbound issue classification, and threaded accessibility-agent workflows. AgentMail is not part of the Phase 1 Amazon SES implementation and will not be used for Keycloak identity email, password resets, core transactional delivery, bulk mail, or marketing. Any future AgentMail workflow must undergo privacy review before handling attachments, document content, accessibility reports, or user-submitted files.

---

## 30. Appendix F: SES Production Access Narrative

```text
GLOW, Guided Layout & Output Workflow, is a free accessibility workflow tool sponsored by Blind Information Technology Solutions. GLOW helps users and administrators work with accessibility-related workflows such as auditing, fixing, converting, and preparing digital content.

We are requesting Amazon SES production access for low-volume transactional email only.

GLOW uses Keycloak as its identity and access management provider. Identity-related transactional messages, such as email verification, password reset, required actions, and account-related administrative notices, are generated by Keycloak and delivered through Amazon SES SMTP.

The GLOW application itself sends only limited service-related transactional messages, such as feedback confirmations, feedback routing to administrators, operational alerts, and future optional job-completion notices requested by users.

We will not use this SES configuration for newsletters, promotional campaigns, convention announcements, fundraising blasts, cold outreach, or unsolicited bulk email. We do not use purchased, rented, scraped, or third-party mailing lists.

Uploaded files, converted documents, extracted text, private accessibility reports, and user API keys are not emailed. Transactional messages contain only minimal service information necessary for the specific action.

Recipients are administrators of the service, users who initiated an action on the site, or individuals who submitted feedback and provided an email address for confirmation.

We will configure a verified sending domain, DKIM, SPF, DMARC, a custom MAIL FROM domain, SES configuration sets, event notifications, CloudWatch monitoring, and account-level suppression for bounces and complaints.

Initial expected volume is modest: approximately 50 to 300 messages per day, with occasional peaks during workshops, testing events, or public demonstrations. We are requesting a conservative initial quota and will request increases only after establishing healthy sending history.
```

---

## 31. Appendix G: Plain-Language Summary for Stakeholders

GLOW should use Amazon SES carefully and professionally. Keycloak should handle account-related email, such as password resets and verification messages. GLOW should handle only service-specific email, such as feedback confirmations and administrator alerts. Amazon SES should provide reliable delivery, sender authentication, bounce handling, complaint handling, and monitoring. AgentMail should be saved for a future phase if GLOW later needs AI agents with their own inboxes.

The system should not be used for newsletters, convention announcements, fundraising blasts, or community marketing. It should never email uploaded files, converted documents, extracted text, private accessibility reports, or API keys.

This keeps the architecture clean, protects GLOW’s privacy promise, improves the likelihood of Amazon SES approval, and gives the team a scalable foundation for future accessibility work.
