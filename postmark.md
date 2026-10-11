# Community Access mail and help desk

One operations manual for every piece of email and support in this estate:
Postmark, the FreeScout help desk, the mailboxes for QUILL, GLOW, Community
Access, Git Going with GitHub and BITS, the GitHub escalation path, and GLOW's
own two-way mail.

**Sources merged into this file.** The Postmark walkthrough that was `magic.md`
item 3 in `s:\quill`, and the whole of `s:\helpdesk.md` (the Unified Help Desk
Plan, 11 September 2026). Both are superseded by this document.

---

## 0. How to use this document

It is long because it is the only one. Nothing here has to be read in a single
sitting, and the parts are ordered by what you should do first.

| Part | What it covers | When |
| --- | --- | --- |
| [One](#part-one--get-mail-flowing-do-this-first) | Get Postmark working so the help desk can send and receive at all | **Now.** Everything else waits on it |
| [Two](#part-two--the-help-desk-platform) | The FreeScout platform: mailboxes, modules, fields, workflows, portals, knowledge bases | After part one |
| [Three](#part-three--github-escalation) | Getting a confirmed defect from a ticket into GitHub without dragging the customer there | After part two |
| [Four](#part-four--glows-own-mail) | GLOW's own sending and its two-way conversations | Independent; any time |
| [Five](#part-five--operations) | Accessibility, privacy, backups, monitoring, governance | Before launch |
| [Six](#part-six--delivery) | Phases, checklists, agent procedure, philosophy | The plan of record |
| [Seven](#part-seven--reference) | What is already running, troubleshooting, what changed in the code | Look things up |

**Priority.** QUILL comes first throughout — in the mailbox list, the custom
fields, the knowledge base. GLOW, Git Going with GitHub and BITS are all here
in full, just not at the front.

**A convention worth knowing.** Where a step says "click X", X is exactly what
you should see on screen. If it is not there, stop and re-read the step before
it rather than guessing.

### 0.1 The map

```
                         a person needs help
                                  |
       +--------------+-----------+-----------+---------------+
       |              |           |           |               |
   QUILL app      GLOW web    an email    a portal form   Git Going class
   Report a Bug   /feedback   to support@  on the web       question
       |              |           |           |               |
       +--------------+-----------+-----------+---------------+
                                  |
                          FreeScout conversation
                          (one instance, many mailboxes)
                                  |
                    +-------------+-------------+
                    |                           |
            answered by a person        confirmed software defect
                    |                           |
                 customer                 GitHub escalation
                                          (human decision)
```

Two different things are both called a "bridge" in these notes, and confusing
them will waste a day:

| Name here | What it is | Status |
| --- | --- | --- |
| **The mail bridge** (`helpdesk-mailbridge`) | Postmark's inbound webhook to a Maildir that FreeScout reads over IMAP | **Built, deployed, proven.** Section 6 |
| **The GitHub bridge** | A service that turns a FreeScout escalation into a sanitised GitHub issue, and GitHub events into internal notes | **Not built.** Part three |

Throughout this document they are always called the *mail bridge* and the
*GitHub bridge*.

### 0.2 Four decisions to make before you start

These came out of checking the live DNS and the running server on 11 September
2026. Each one is a real fork, not a detail.

**1. `help.` or `helpdesk.`?** The plan names
`https://help.community-access.org` as the canonical FreeScout URL. What is
actually deployed, with DNS, a Caddy block and a valid certificate, is
`https://helpdesk.community-access.org`. `help.community-access.org` does not
resolve at all today.

- *Keep `helpdesk.`* — nothing to do. It works now, and FreeScout's `APP_URL`
  already matches, which is what keeps sessions, portal links, generated ticket
  URLs and the inbound webhook path consistent.
- *Move to `help.`* — add an A record, add a Caddy block, change `APP_URL`, and
  re-point the Postmark inbound webhook. Doable, but do it **before** anybody
  has bookmarked a portal or received a ticket link, not after.

Recommendation: keep `helpdesk.` unless somebody feels strongly. The shorter
name is nicer; it is not worth a migration once links exist.

**2. `bits-acb.org` is not like the others.** Checked:

```
bits-acb.org    MX  0 bitsacb-org01b.mail.protection.outlook.com.
                SPF v=spf1 include:spf.protection.outlook.com
                    include:_spf.wpcloud.com -all
```

That is **Microsoft 365**, not registrar forwarding. So `support@bits-acb.org`
and `gitgoing@bits-acb.org` are real Exchange mailboxes. The Namecheap
forwarding trick in section 5 does not apply to them. Two ways in:

- **FreeScout connects directly over IMAP or OAuth** to the Microsoft 365
  mailbox. This is what the original plan recommended for the general case, it
  needs no bridge, and for this domain it is the right answer.
- Or add an Exchange rule forwarding the mailbox to Postmark's inbound address,
  and let the mail bridge carry it like the rest.

Recommendation: IMAP/OAuth straight to Microsoft 365 for the BITS mailboxes,
the mail bridge for everything on a registrar-forwarded domain. FreeScout
supports both at once, per mailbox. See section 13.

**3. `glow.bits-acb.org` looks like a CNAME, which cannot hold mail.** Checked:

```
glow.bits-acb.org   MX  letitglow.app. 10 eforward1.registrar-servers.com. ...
                    A   letitglow.app. 107.175.91.158
```

The name resolving through `letitglow.app` in both answers is the signature of
a CNAME. A CNAME cannot coexist with MX or any other record at the same name,
so `support@glow.bits-acb.org` would inherit whatever `letitglow.app` does with
mail — which is registrar forwarding, on a different domain, for a different
purpose.

Recommendation: use the plan's own alternative, **`glow@community-access.org`**,
for the GLOW mailbox. It sits on a domain whose mail you control the same way
as everything else in part one. Keep `support.glow.bits-acb.org` as a *web*
redirect to the GLOW portal, which is all it was ever needed for.

**4. Every new mailbox address must be added to the mail bridge's allow-list.**
This is the single easiest thing to get wrong. The bridge currently serves
exactly one address:

```
MAILBRIDGE_RECIPIENTS=support@community-access.org
```

An address that is not on that list gets a **403**, and Postmark treats 403 as
"stop retrying" — so the message is gone, deliberately and permanently. Every
time you add a mailbox in section 12, add its address here too. Section 13 has
the command.

---

# Part one — get mail flowing (do this first)

## 1. What you are building

`support@community-access.org` is answered by **FreeScout**, a help desk
already installed and running on `lp.csedesigns.com`, reachable at
<https://helpdesk.community-access.org>. The website works today. It cannot
send or receive email yet, and until it can, nobody can write to support and
get an answer.

Postmark fixes both halves:

- **Receiving.** Mail sent to `support@community-access.org` reaches Postmark,
  which posts it to the mail bridge on the server, which writes it into a
  mailbox FreeScout reads.
- **Sending.** FreeScout sends replies through Postmark's SMTP, so they arrive
  authenticated and land in an inbox rather than a spam folder.

The chain, once it works:

```
someone emails support@community-access.org
  -> Namecheap forwarding
  -> Postmark (inbound)
  -> helpdesk-mailbridge          (writes the raw message to a Maildir)
  -> Dovecot                      (serves that Maildir over IMAP)
  -> FreeScout                    (a conversation, in a queue, with agents)
  -> an agent replies
  -> Postmark (SMTP)
  -> back to the person, in the same email thread
```

**Everything from the mail bridge rightwards is already built, deployed and
proven.** This part is the two ends: getting Postmark an account, and telling
each side about the other.

### Why this is the priority, for QUILL

Report a Bug in every QUILL app currently files a GitHub issue through the
submission server. Once this works, that can be switched to open a FreeScout
conversation instead — **a change on the server only**, with no app release and
no version skew, because the apps post to a URL rather than calling GitHub
themselves. That seam was the point of building it that way. See section 9.

### Before you start, have ready

- A browser, logged into whatever account manages billing for this project.
- The Namecheap login that manages `community-access.org` DNS. This is the same
  login used for the help desk's DNS record. If you do not have it, get it
  before continuing; everything below needs it.
- A terminal with SSH to the server as `jeffbis` (one command, in section 6).
- A payment card. Section 2 is the only thing in this document that costs
  money.

---

## 2. Postmark account and plan

1. Go to `postmarkapp.com` in your browser.
2. Click **Sign Up** (or **Get Started**) and create an account with an email
   address you control.
3. Once inside, look for **Plans** or **Billing** in the account settings.
4. **Choose a plan that includes inbound email.** At the time this was
   researched that was the **Pro** plan at **$16.50/month** including 10,000
   messages, and neither the free Developer plan nor the $15 Basic plan
   included inbound.

   Inbound is the entire reason for doing this. Pick a plan without it and you
   will get as far as section 5 and discover it silently does not work.

   **Check the current pricing page rather than trusting this paragraph.** Plan
   names and prices move; the only thing that matters is the line item saying
   inbound is included.
5. Enter payment details and confirm the subscription.

---

## 3. Create the server and verify the domain

Postmark's dashboard organises everything under a **Server**, which is their
word for a project inside your account. It has nothing to do with a physical
machine.

1. In the Postmark dashboard, click **Servers** in the top navigation.
2. Click **Create Server**.
3. Name it `Community Access Help Desk`. Click **Create**.
4. Click into the server you just created.
5. In the left sidebar, click **Sending**, then **Domains**.
6. Click **Add Domain**.
7. In the field asking for a domain name, type exactly:

   ```
   community-access.org
   ```

   Do **not** type `helpdesk.community-access.org`, and do **not** type
   `www.community-access.org`. Only the plain domain.

   *Why:* verifying this one domain covers every address at it, including
   `support@community-access.org`. Verifying the help desk's own hostname would
   create DNS records that do nothing, because nothing ever sends mail *from*
   that name — it is only where the website lives.
8. Click **Add**. Postmark now shows a page titled **DNS Settings** with two
   records to add.

**Keep this browser tab open.** You copy values out of it in the next section.

*(You will come back and add `quillforall.org` here too, in section 13, once
the QUILL mailbox exists. One server can verify several sending domains.)*

---

## 4. Two DNS records at Namecheap

These make outbound mail authentic, so replies from the help desk are not
treated as forgeries.

1. Open a new browser tab, go to `namecheap.com`, and log in.
2. Click **Domain List** in the left sidebar.
3. Find `community-access.org` and click **Manage**.
4. Click the **Advanced DNS** tab near the top.
5. You will see a table of existing records. **Do not delete or edit any
   existing row.** You are only adding two new ones.
6. Click **Add New Record**. For the first record:
   - **Type**: `TXT Record`
   - **Host**: copy this exactly from the Postmark tab. It looks like
     `20260827123456pm._domainkey` — the numbers will differ, so use whatever
     Postmark shows you, not this example.
   - **Value**: copy the long string from Postmark starting `k=rsa; p=...`.
     Copy the whole thing; it is long.
   - **TTL**: leave at Automatic.
   - Click the green checkmark to save the row.
7. Click **Add New Record** again. For the second record:
   - **Type**: `CNAME Record`
   - **Host**: `pm_bounces`
   - **Value**: `pm.mtasv.net`
   - Click the green checkmark.

   **If Namecheap refuses this** because of the underscore or for any other
   reason: go back to the Postmark tab, find the setting for the "Return-Path"
   or "bounce" hostname, change it from `pm_bounces` to `pm-bounces` (hyphen),
   and repeat this step with `pm-bounces` as the Host.
8. Leave the page. Namecheap saves each row as you add it; there is no separate
   Save button for the page as a whole.
9. Go back to the Postmark tab and click **Verify** on the domain page. This
   usually takes a few minutes. Postmark says it can take up to 48 hours in the
   worst case, so come back and click Verify again later if it is not done
   immediately.

**Both DKIM and Return-Path must show Verified before you continue to
section 7.**

### Three warnings about this domain specifically

**Do not touch the existing SPF record.** `community-access.org` already has
one:

```
v=spf1 include:spf.efwd.registrar-servers.com ~all
```

It belongs to the Namecheap email forwarding that other addresses at this
domain rely on, and it must stay exactly as it is. Postmark does not need an
SPF record when the Return-Path CNAME above is in place, because the
Return-Path domain carries its own.

If your own policy later requires Postmark to be named in SPF, **merge** it
into the existing record rather than adding a second one:

```
v=spf1 include:spf.efwd.registrar-servers.com include:spf.mtasv.net ~all
```

Two SPF records on one host is a permanent error, and it fails silently.

**DMARC is optional here.** Skip it for now; it is a separate, harmless TXT
record you can add later. The recommended progression, when you get to it, is
`p=none` → read the reports and fix alignment → `p=quarantine` → `p=reject`.
Do not change email DNS blindly on a production domain; inventory the existing
records first.

**Watch for a doubled zone suffix.** Some DNS hosts append the domain name to
whatever you type in the Host field. If yours does, entering the full
`..._domainkey.community-access.org` produces
`..._domainkey.community-access.org.community-access.org`, which verifies
never. Namecheap expects the short form, which is what Postmark shows you.

---

## 5. Route support@ into Postmark, without touching MX

This is the step with a trap in it. Read the warning before doing anything.

### The trap

Postmark's normal instructions tell you to point your domain's MX records at
Postmark. **Do not do this for `community-access.org`.**

That domain already has five MX records pointing at Namecheap's own email
forwarding:

```
$ dig +short MX community-access.org
10 eforward1.registrar-servers.com.
10 eforward2.registrar-servers.com.
10 eforward3.registrar-servers.com.
15 eforward4.registrar-servers.com.
20 eforward5.registrar-servers.com.
```

Replace those with Postmark's and **every email address at this domain that
currently forwards somewhere silently stops working**, with no error message
anywhere.

### The safe way — forward one address, touch no DNS

1. Go back to the Postmark tab. In the left sidebar of your server, click
   **Message Streams**.
2. Click the stream named **Inbound** (or **Default Inbound Stream**).
3. Find the **inbound email address** on that page. It is a long random string
   followed by `@inbound.postmarkapp.com`, for example
   `abc123def456@inbound.postmarkapp.com`. Copy it.
4. Switch to the Namecheap tab. Click **Domain List**, then **Manage** next to
   `community-access.org`.
5. Find the **Email Forwarding** tab or section. It is usually a separate tab
   from Advanced DNS — look along the top of the domain management page.
6. Add a new forwarding rule:
   - **Mailbox / alias**: `support`
   - **Forwards to**: paste the `@inbound.postmarkapp.com` address from step 3.
   - Save the rule.
7. That is it. No DNS record was touched. Mail to
   `support@community-access.org` is now forwarded, unchanged, to Postmark,
   which hands it to the mail bridge already waiting on the server.

**What forwarding does and does not change.** It rewrites the envelope, which
is invisible to everyone, and leaves the `From:` header alone — so FreeScout
still sees the real person as the customer. That is the behaviour the whole
design depends on, so prove it with one real message in section 8 rather than
assuming it.

This same pattern is how you add every later mailbox on a registrar-forwarded
domain. Section 13 does the rest of them.

### Two alternatives, if you outgrow this

- **An inbound subdomain.** Add `MX inbound.community-access.org ->
  inbound.postmarkapp.com` and forward `support@` to
  `anything@inbound.community-access.org`. More moving parts, and it buys a
  readable inbound address nobody outside the system ever sees. Worth it only
  if you want several distinct inbound addresses.
- **Repoint the domain's MX.** Only if the domain has no other mail you care
  about. Check the forwarding list in Namecheap before even considering it.

---

## 6. The inbound webhook

Postmark now receives the mail. This tells it where to send it.

1. Open a terminal and connect to the server:

   ```bash
   ssh jeffbis@lp.csedesigns.com
   ```
2. Run:

   ```bash
   cd ~/feedback-hub
   ./deploy/helpdesk/make-credentials.sh
   ```
3. This prints two things: a webhook URL containing a username and password,
   and IMAP settings for FreeScout. Copy the whole webhook URL:

   ```text
   https://<user>:<password>@helpdesk.community-access.org/postmark/inbound
   ```

   The script is idempotent and **refuses to overwrite a value that is already
   set**, because regenerating the credential would break inbound mail until
   Postmark is updated to match — and mail that stops arriving is the hardest
   kind of failure to notice.
4. Switch back to the Postmark tab, still on **Message Streams > Inbound**.
5. Find the field labelled **Webhook URL**. It is sometimes under a "Settings"
   or "Webhook" sub-tab on that same page.
6. Paste the entire URL from step 3 — the `https://`, the username, the colon,
   the password, the `@`, all of it, as one string.
7. Click **Save**. If Postmark offers to send a test webhook call, take it and
   confirm you see a success response.

### Why this has to be exactly right

If the username or password in that URL is wrong by one character, the server
returns `401 Unauthorized`. Postmark documents that only a `403` stops retries
outright — a `401` is retried, up to ten attempts on a growing schedule over
several hours. So a wrong password does not lose mail instantly. But once the
attempts are used up, the message is marked **Inbound Error** in Postmark and
goes no further on its own. It does not retry forever, and it never appears in
FreeScout, so it can sit unnoticed for hours before anybody realises mail is
not arriving.

Run the test sequence in section 8 before telling anyone the address exists,
rather than relying on the retry window to cover a typo.

### What the mail bridge does, and deliberately does not do

It is a **delivery adapter, not a second help desk**. It writes the raw RFC-822
message out byte for byte and never parses it, rewrites a header, strips quoted
text, or touches `Message-ID`, `In-Reply-To` or `References`. Everything that
looks like mail handling — threading, duplicate detection, customer-versus-agent
replies, attachments, auto-replies, bounces, reactivating a closed conversation
— is FreeScout's, which is the entire reason for feeding it real email.

Three behaviours worth knowing before reading its logs:

- **A retry is answered 200 and writes nothing.** The bridge is idempotent on
  Postmark's message id, falling back to a hash of the message. The Maildir
  filename is derived from that hash, so even a crash between the write and the
  database update cannot produce a second copy.
- **Status codes are instructions to Postmark.** `403` stops retries and is
  used only for a recipient the bridge does not serve. Everything an
  administrator could fix — a missing raw email, a full disk, an unwritable
  mailbox — is a `5xx`, so the retry lands once it is fixed. A `4xx` there would
  discard the message before anybody noticed.
- **It is deliberately not rate limited.** Postmark's retry schedule is what
  protects mail from a transient failure, and a limiter is exactly the thing
  that would turn a busy hour into silently lost support requests. Its
  protections are the size cap, the credentials, and the recipient allow-list.

---

## 7. Tell FreeScout how to send

Outbound is configured **inside FreeScout**, not in any `.env` file, so
rotating the token later never needs a container restart.

1. Go to `https://helpdesk.community-access.org/login` and sign in as the admin
   account (`jeff@jeffbishop.com`).
2. Click **Manage** in the top menu, then **Settings**, then **Mail**.

   Depending on the FreeScout version this may instead be **Mailboxes**, then
   the support mailbox, then its mail settings. You are looking for outgoing /
   SMTP settings.
3. Go back to the Postmark tab. In the left sidebar click **API Tokens**
   (sometimes under "Credentials" or the server's "Settings").
4. Copy the **Server API Token** — a long string of letters and numbers.
5. Back in FreeScout, fill in:

   ```
   Driver:     SMTP
   Host:       smtp.postmarkapp.com
   Port:       587
   Encryption: TLS            (sometimes labelled STARTTLS)
   Username:   <the Server API Token>
   Password:   <the same Server API Token again>
   From:       support@community-access.org
   ```

   Both the username and password fields get the identical string. That is how
   Postmark's SMTP works; it is not a mistake.
6. Click **Save**.

---

## 8. The test sequence

Do these in order and do not skip ahead. Each proves a single thing, so a
failure tells you immediately which piece is broken.

1. **DNS.** On the Postmark domain page from section 3, confirm **DKIM:
   Verified** and **Return-Path: Verified**. If either says Pending, wait and
   refresh before continuing.

2. **Outbound.** In FreeScout, send a test email to your own address. There is
   usually a "send test email" option in the mail settings you were just in;
   otherwise create a conversation addressed to yourself. Open the email and
   view its full headers — most clients call this "show original" or "view
   source". Confirm:
   - a `DKIM-Signature:` line mentioning `community-access.org`
   - a `Return-Path:` line mentioning `pm.mtasv.net`

   Both present means outbound works.

3. **Inbound.** From a completely different account (a personal Gmail is
   fine), send a plain email to `support@community-access.org`. Wait a minute,
   then check both:
   - In Postmark, click **Activity**; the message should be listed as received.
   - In FreeScout, refresh the conversations list; a new conversation should
     have appeared with that subject and body, **from the real sender**, not
     from Namecheap or Postmark.

   Both present means inbound works end to end.

4. **Round trip.** Open that conversation in FreeScout and click **Reply**.
   Send anything. Check the account you sent from in step 3 — the reply should
   arrive there, and it should appear in the **same email thread** as the
   original, not as an unrelated new message.

5. **Duplicates.** Send the exact same email again from step 3: same subject,
   same body, same account. It should **not** create a second conversation or a
   duplicate message.

If all five pass, Postmark is working for the help desk.

If any one fails, stop, and re-read the section above that matches what failed.
Do not move on and do not guess at a workaround.

---

## 9. Publish the address, and what that unblocks

Once all five checks pass:

1. `support@community-access.org` is safe to tell people about. It is already
   referenced in the QUILL apps' **Help > About** screens and in the
   documentation, so there is nothing to change in any app.

2. **QUILL's Report a Bug can move off GitHub.** Every QUILL app routes bug
   reports through the submission server on `lp.csedesigns.com`, which files a
   GitHub issue. Because the apps post to a URL rather than calling GitHub
   themselves, changing where a report lands is a change on the server only —
   no release, no version skew, no installed copy left behind still filing into
   the wrong place.

3. **The bundled GitHub token can then be retired.** Every QUILL installer has
   an issues-only token baked in as the fallback from before the server
   existed. Removing it is gated on a released build having been *observed*
   working through the server path — until then it is the only safety net, and
   removing it early removes exactly that. The steps are in `magic.md` item 7.

4. **GLOW's feedback form can start filing tickets.** That path does not use
   Postmark at all; see section 39. It needs only three environment variables.

### One thing not to do before this is finished

Do **not** use FreeScout's "Forgot password" link to test account recovery
until the walkthrough above is complete. It sends an email, and until Postmark
is carrying mail that email has nowhere to go.

If you are locked out of the admin account before then, the only way back in is
from the terminal:

```bash
ssh jeffbis@lp.csedesigns.com
cd ~/helpdesk
docker compose exec -u nginx app sh -c \
  'cd /www/html && php artisan freescout:create-user --role=admin \
     --firstName=X --lastName=Y --email=x@example.org --password=...'
```

Replace `X`, `Y`, `x@example.org` and `...` with real values first. It creates
a second admin account with whatever you put there.

### The FreeScout trap worth knowing before you touch the container

FreeScout encrypts its stored mailbox passwords with `APP_KEY`. The container
image rewrites its own `.env` on **recreate** — which `docker compose up -d`
performs after any compose change, and which every image update performs — and
on the first-install path it writes `APP_KEY` **empty**.

An emptied `APP_KEY` makes the saved Postmark credentials undecryptable, so
**inbound mail stops silently**, at a moment that looks unrelated to whatever
was updated. In a help desk that is mail nobody knows they are not receiving.

The deployment already defends against this: `docker-compose.yml` bind-mounts
`./freescout.env` over `/www/html/.env`, so the host copy is authoritative and
the image's init script takes its *update* path instead, touching only the
handful of keys it manages.

- Do not undo that bind mount.
- Do not "tidy up" a `freescout.env` you cannot read. It is owned by uid 80 at
  mode 600 deliberately. Read it with
  `docker exec helpdesk-app cat /www/html/.env`.
- The same image also writes a database driver name Laravel 5.5 does not
  define, whose only symptom is an endless redirect to `install.php`. The
  repair is `~/helpdesk/fix-db-driver.sh`.

Both are documented in full in `~/feedback-hub/deploy/helpdesk/README.md`.

---

# Part two — the help desk platform

## 10. Architecture: one instance, many mailboxes

The recommended architecture, and the one this document assumes:

> **One FreeScout instance, one canonical application URL, many mailboxes, many
> support email addresses, several public support domains, one knowledge and
> workflow strategy, and one GitHub integration layer.**

FreeScout is treated as a **shared service platform**, not merely an email
inbox. The objectives:

- One administrative and support environment.
- Each program gets its own public-facing support identity.
- One FreeScout instance and one set of module licences.
- Different teams and volunteers work only in the areas they need.
- Consistent intake, triage, escalation, reporting and knowledge management.
- Technical issues integrate with GitHub without forcing customers to use it.
- Accessibility is a first-class design and acceptance requirement.
- New Community Access and BITS initiatives can be added without
  rearchitecting.

---

## 11. The canonical URL

Use **one** canonical application URL and configure it as FreeScout's `APP_URL`.

Today that is:

```
https://helpdesk.community-access.org
```

The plan originally proposed `help.community-access.org`; see decision 1 in
section 0.2 for the trade-off. Whichever you choose, choose once.

**Do not run the same installation as independent applications under several
hostnames.** One canonical hostname is used for authentication, agent access,
portal links, API calls, and application-generated URLs. A single canonical URL
avoids problems with login sessions and cookies, CSRF protections, portal
authentication, generated ticket links, API integrations, webhooks, embedded
images and attachments, browser password managers, certificates, and any future
SSO.

Additional branded support domains **redirect** users to the appropriate portal
inside the canonical installation. FreeScout's End-User Portal gives each
mailbox its own portal address; the branded domains point at those.

| Public support identity | Purpose | Destination |
| --- | --- | --- |
| `helpdesk.community-access.org` | Canonical help desk | FreeScout front door |
| `support.quillforall.org` | QUILL Support | QUILL portal or knowledge base |
| `support.glow.bits-acb.org` | GLOW Support | GLOW portal or knowledge base |
| `support.bits-acb.org` | BITS Support | BITS portal or knowledge base |
| `gitgoing.bits-acb.org` | Git Going with GitHub | Git Going portal or knowledge base |

These aliases can change later without moving FreeScout. Note that
`support.glow.bits-acb.org` is a **web** redirect only — see decision 3 in
section 0.2 for why it should not carry mail.

---

## 12. Mailboxes

Create separate mailboxes for distinct support programs, but **do not create a
separate mailbox for every QUILL application.**

Recommended starting mailboxes, in priority order:

1. **QUILL Support**
2. **GLOW Support**
3. **Community Access**
4. **Git Going with GitHub**
5. **BITS Support**

Future mailboxes can be added without changing the architecture — possible
areas include Training Support, Accessibility Testing, Community Access
Projects, Event Support, Partner Support, Internal Operations.

### 12.1 QUILL Support

Recommended public address: **`support@quillforall.org`**

Use **one QUILL mailbox for the entire product family.** Do not create separate
mailboxes for QUILL Editor, Lite, Radio, Cast, Weather and future products
unless different organisations or entirely separate support teams eventually
own them.

Use a required **Product** custom field instead. Reasons:

- Customers have one obvious support destination.
- Agents have one QUILL queue.
- Product reporting can still be separated.
- Workflows can route by product.
- Tags can generate product-specific folders.
- GitHub escalation can choose a repository based on product.
- **FreeScout custom-field values are not preserved when a conversation is
  moved between mailboxes**, so avoiding unnecessary mailbox movement is
  directly valuable.

Suggested **Product** values — update as the family evolves:

QUILL Editor · QUILL Lite · QUILL Radio · QUILL Cast · QUILL Weather ·
QUILL Book / Library · QUILL Bookmarks · QUILL Sync · QUILL Website ·
Other QUILL Product

### 12.2 GLOW Support

Recommended public address: **`glow@community-access.org`**

The plan's first choice was `support@glow.bits-acb.org`; decision 3 in section
0.2 explains why `glow@community-access.org` is the safer one. Keep
`support.glow.bits-acb.org` as a web redirect to the GLOW portal.

Purpose: GLOW Audit, Fix, Convert, Templates, Hub; login and authentication
problems; accessibility testing questions; interpreting results; feature
requests; bug reports.

This is also where GLOW's own feedback-form tickets land — see section 39.

### 12.3 Community Access

Recommended public address: **`help@community-access.org`**

Purpose: general questions; anything that does not clearly belong to another
program; Community Access site or account questions; requests involving several
projects; partner or organisational questions; and a safe front door for
somebody who does not know where to begin.

Avoid making this a dumping ground. Workflows should route or retag requests
once their destination is clear.

*(`support@community-access.org`, the address set up in part one, can either
stay as the general support address or become an alias feeding this mailbox.
Decide when you create it; both are fine, but pick one and put the other in
the allow-list as an alias rather than a second mailbox.)*

### 12.4 Git Going with GitHub

Recommended public address: **`gitgoing@bits-acb.org`**

Purpose: Git Going training questions; Git installation and configuration;
GitHub account questions; repositories, pull requests, issues, branches;
GitHub Desktop; GitHub CLI; VS Code Git and GitHub workflows; screen-reader
specific Git and GitHub questions; course and workshop exercises.

This is a **support and education mailbox, not a substitute for GitHub
itself.** When a training issue exposes a genuine defect in training materials
or software, escalate it using part three.

Note: this address is on `bits-acb.org`, which is Microsoft 365. See decision 2
in section 0.2 and section 13.

### 12.5 BITS Support

Recommended public address: **`support@bits-acb.org`**

Purpose: BITS membership questions; programs and services; training; website
support; BITS Connect; event and convention technology; program-specific
technology support; general BITS technical assistance.

Where a question is organisational rather than technical, FreeScout is still
useful as the structured point of intake.

Also on Microsoft 365; see section 13.

---

## 13. Email architecture, domain by domain

Each mailbox needs a real support address, and FreeScout supports a separate
sender address per mailbox. What differs between them is **how mail gets in**,
and that depends entirely on who runs the domain's MX. Checked 11 September
2026:

| Address | Domain's mail | Inbound route | Sending domain to verify in Postmark |
| --- | --- | --- | --- |
| `support@quillforall.org` | Namecheap forwarding | Forward to Postmark, mail bridge | `quillforall.org` |
| `glow@community-access.org` | Namecheap forwarding | Forward to Postmark, mail bridge | `community-access.org` (already done) |
| `help@community-access.org` | Namecheap forwarding | Forward to Postmark, mail bridge | `community-access.org` (already done) |
| `support@community-access.org` | Namecheap forwarding | Already working (part one) | `community-access.org` (done) |
| `support@bits-acb.org` | **Microsoft 365** | **FreeScout IMAP/OAuth direct** | `bits-acb.org` |
| `gitgoing@bits-acb.org` | **Microsoft 365** | **FreeScout IMAP/OAuth direct** | `bits-acb.org` |

### 13.1 Adding a registrar-forwarded address

For `quillforall.org`, `community-access.org` and any other domain on
`eforward*.registrar-servers.com`:

1. In Postmark, **Sending > Domains > Add Domain** for that domain, and add its
   DKIM TXT and Return-Path CNAME at Namecheap, exactly as section 4. Each
   sending domain needs its own pair.
2. Check for an existing SPF record on that domain before touching anything.
   `quillforall.org` has one:
   `v=spf1 include:spf.efwd.registrar-servers.com ~all`. **Merge, never add a
   second.**
3. In Namecheap's **Email Forwarding** for that domain, forward the alias to
   the Postmark server's inbound address — the same `@inbound.postmarkapp.com`
   address from section 5. One Postmark server can receive for all of them.
4. **Add the address to the mail bridge's allow-list.** This is the step people
   forget:

   ```bash
   ssh jeffbis@lp.csedesigns.com
   cd ~/feedback-hub/deploy/helpdesk
   # edit .env, extend MAILBRIDGE_RECIPIENTS to a comma-separated list:
   #   MAILBRIDGE_RECIPIENTS=support@community-access.org,support@quillforall.org,...
   docker compose up -d mailbridge
   ```

   An address not on that list gets a **403**, and Postmark treats 403 as "stop
   retrying". The message is gone, deliberately and permanently.
5. In FreeScout, create the mailbox with that address as its sender, and point
   its fetching at the same Dovecot IMAP settings `make-credentials.sh` printed.
6. Send one real message to the new address and confirm it becomes a
   conversation, before telling anybody it exists.

### 13.2 Adding a Microsoft 365 address

For `support@bits-acb.org` and `gitgoing@bits-acb.org`:

FreeScout retrieves directly. No Postmark inbound, no mail bridge, no
forwarding rule.

1. In Microsoft 365, confirm the mailbox or shared mailbox exists.
2. In FreeScout, create the mailbox and configure **incoming** mail as IMAP or
   OAuth against Microsoft 365. OAuth is preferable where the tenant allows it;
   basic-auth IMAP is being retired by Microsoft.
3. Configure **outgoing** mail for that mailbox. Two options:
   - Send through Postmark, which needs `bits-acb.org` verified as a sending
     domain **and** `include:spf.mtasv.net` merged into its existing SPF
     (`v=spf1 include:spf.protection.outlook.com include:_spf.wpcloud.com
     -all` — note the `-all`, which is strict, so an unmerged Postmark send
     will be rejected outright rather than merely flagged).
   - Or send through Microsoft 365's own SMTP, which needs no DNS change at
     all. For a mailbox whose mail already lives in M365, this is the simpler
     answer.
4. Nothing goes in the mail bridge allow-list for these.

### 13.3 Aliases

Aliases may be added later, such as `help@quillforall.org`,
`bugs@quillforall.org`, `accessibility@quillforall.org`. **An alias should feed
an existing mailbox, not become a new FreeScout mailbox.** Add each alias to
the bridge allow-list the same way.

### 13.4 The plan's original advice on inbound, resolved

The source plan said: *"Do not assume that an outbound email provider such as
Postmark is also an IMAP mailbox host. If you already have a reliable
FreeScout/Postmark inbound bridge, document it separately before changing it."*

That bridge exists, is deployed, and is proven. Sections 1 and 6 are that
documentation. The plan's fallback — obtain a separate IMAP mailbox host for
every address — is not needed for the registrar-forwarded domains. It *is* the
right answer for `bits-acb.org`, where a real IMAP host already exists in the
form of Microsoft 365.

---

## 14. Modules: purchase and install

### 14.1 Purchase in one transaction

The FreeScout module catalogue uses a shared **Add to cart / Checkout** flow.
Go to <https://freescout.net/modules/> and add all the paid modules you want to
the cart **before checking out**. Payments are one-time lifetime licences for
one FreeScout instance. Module FAQ: <https://freescout.net/modules-faq/>.

Before submitting payment:

- Confirm every desired module is in the cart.
- Confirm the order is for the one production instance.
- Save the purchase confirmation.
- Save all licence keys in the organisation's password manager.
- Record who owns the purchasing account, the purchase date, and the canonical
  instance name.

### 14.2 Recommended set

**Core — install immediately**

Tags · Saved Replies · Workflows · Ticket Number · API & Webhooks ·
Custom Fields · End-User Portal · Custom Folders · Reports · Knowledge Base ·
Mentions · Two-Factor Authentication · Customization & Rebranding ·
Widgets White-Labeling · Spam Filter · Satisfaction Ratings

**Strong operational additions**

Teams · Global Mailbox · Checklists · Export Conversations · Office Hours ·
Send & Close · Sent Folder · Extended Attachments

**Free**

AI Integration

**Consider later**

Time Tracking · Mobile Notifications · OAuth & Social Login · SAML SSO ·
Slack Integration · Ticket Translator · Dark Mode · Out of Office · Kanban ·
Keyboard Shortcuts

Do not buy modules merely because they exist. Buy the operational set and add
others when a defined use case appears.

### 14.3 Installation order

Install in dependency order so a problem is easy to attribute:

1. Tags
2. Custom Fields
3. Saved Replies
4. Ticket Number
5. Workflows
6. API & Webhooks
7. Custom Folders
8. End-User Portal
9. Knowledge Base
10. Reports
11. Mentions
12. Teams
13. Global Mailbox
14. Two-Factor Authentication
15. Customization & Rebranding
16. Widgets White-Labeling
17. Spam Filter
18. Satisfaction Ratings
19. Checklists
20. Export Conversations
21. Office Hours
22. Send & Close
23. Sent Folder
24. Extended Attachments
25. AI Integration

**After each installation:** confirm the module activates; confirm FreeScout
still loads; test with keyboard only; test one basic module function; record
the licence key and version.

Do not install twenty modules and only then discover which one caused a
problem.

---

## 15. Server baseline

Before extensive configuration, confirm:

- FreeScout is on the current supported stable version.
- PHP requirements are met.
- Database health.
- Application storage permissions.
- HTTPS.
- Outbound network access to FreeScout's module service.
- Backup and restore capability.
- **Cron runs every minute.** It is what fetches mail and sends replies.
- Background jobs are operating.
- Email retrieval works.
- Email sending works.
- A test ticket can complete a full round trip.

FreeScout's installation guide requires a scheduler cron similar to:

```text
* * * * * php /path/to/freescout/artisan schedule:run
```

On this deployment the image's own cron does this and is already on.

---

## 16. Users, teams and permissions

Create access intentionally. Suggested functional groups:

System Administrators · Help Desk Administrators · QUILL Support ·
GLOW Support · BITS Support · Git Going Support · Developer Liaisons ·
Knowledge Base Editors

Use FreeScout mailbox access and Teams to implement the separation.

**Least privilege.** An agent should see only the mailboxes their role needs. A
QUILL volunteer does not automatically need BITS organisational tickets. A Git
Going instructor does not need private BITS membership correspondence. A
developer does not need administrator permissions merely to review technical
escalations.

**Administrator accounts.** Keep the number small. Require Two-Factor
Authentication for administrators, program leads, anyone with API configuration
access, and anyone with broad multi-mailbox permissions. Prefer requiring it
for every agent if operationally practical.

**No shared accounts.** Each person gets their own login, their own 2FA, their
own activity trail, and only the permissions they require.

---

## 17. Ticket numbering

Enable **Ticket Number** and use a consistent human-readable identifier in
outbound subjects:

```
[CA-1842] QUILL Radio stops during playback
```

Use one common prefix — `CA`, for Community Access — across the unified
instance. Do not make prefixes so product-specific that moving or reclassifying
an issue makes the number misleading.

---

## 18. Tagging strategy

FreeScout tags are **global across mailboxes**, so adopt a controlled naming
convention and stick to it.

**Service** — `svc:quill` · `svc:glow` · `svc:community` · `svc:gitgoing` ·
`svc:bits`

**Issue type** — `type:bug` · `type:a11y` · `type:howto` · `type:feature` ·
`type:account` · `type:content` · `type:training` · `type:security`

**State** — `state:triage` · `state:waiting` · `state:github` · `state:dev` ·
`state:kb` · `state:blocked` · `state:overdue`

**Impact** — `impact:blocker` · `impact:high` · `impact:normal` ·
`impact:low`

**Source** — `src:email` · `src:portal` · `src:web`

**QUILL product** — `quill:editor` · `quill:lite` · `quill:radio` ·
`quill:cast` · `quill:weather` · `quill:books` · `quill:bookmarks`

Do not create uncontrolled synonyms — bug, bugs, defect, problem, software bug.
Pick one taxonomy and use it consistently.

---

## 19. Custom fields

Capture structured information useful for triage, reporting, automation and
GitHub escalation. **Avoid requiring too many fields; every required field adds
friction.**

### 19.1 Common fields

**Issue Type** (dropdown): Question · Bug · Accessibility · Feature Request ·
Documentation · Account · Training · Security / Privacy · Other

**Impact** (dropdown): Blocker · High · Normal · Low

Define impact by **effect**, not by who submitted the ticket:

- **Blocker** — user cannot complete a critical task and no reasonable
  workaround exists.
- **High** — major function unavailable or substantially impaired.
- **Normal** — meaningful problem with a workaround, or limited impact.
- **Low** — cosmetic, minor inconvenience, suggestion, non-urgent improvement.

An accessibility issue should be **evaluated** for impact, not automatically
assigned the highest severity.

**Operating System**: Windows 11 · Windows 10 · macOS · iOS · Android · Linux ·
Web / Browser · Other · Unknown

**Assistive Technology** (multiselect): JAWS · NVDA · Narrator · VoiceOver ·
TalkBack · ZoomText · Magnification · Voice Control · Keyboard Only · None ·
Other · Unknown

**Version** (single line)

**Reproducible**: Yes · No · Sometimes · Unknown

### 19.2 QUILL fields

**Product** (required dropdown): QUILL Editor · QUILL Lite · QUILL Radio ·
QUILL Cast · QUILL Weather · QUILL Book / Library · QUILL Bookmarks ·
QUILL Sync · QUILL Website · Other

**Application Version** (single line)

**Installation Type** (optional): Installed · Portable · Unknown

**GitHub Repository** · **GitHub Issue Number** · **GitHub Issue URL** —
internal fields, written by the GitHub bridge.

**Developer Status** (internal dropdown): Not Escalated · Ready for GitHub ·
GitHub Open · Developer Reviewing · Fix in Progress · Fixed Pending Release ·
Released · Closed / Not Planned

### 19.3 GLOW fields

**GLOW Area**: Audit · Fix · Convert · Templates · Hub · Authentication ·
Reporting · Website · Other

**Browser**: Edge · Chrome · Firefox · Safari · Other

**Content Type**: Web · PDF · Word · PowerPoint · Spreadsheet · Other

**URL or Resource** (optional single line). Do not encourage customers to
submit confidential document URLs without appropriate privacy instructions.

*GLOW's feedback form already supplies most of this in the ticket body — see
section 39 — so these fields are for tickets that arrive by email.*

### 19.4 Git Going fields

**Topic**: Git Basics · Git Configuration · GitHub Account · Repository ·
Clone · Commit · Branch · Merge · Pull Request · Issues · GitHub Desktop ·
GitHub CLI · VS Code · Authentication · Accessibility · Training Exercise ·
Other

**Course / Session** (optional) · **Repository URL** (optional)

**Git Client**: Command Line · GitHub Desktop · VS Code · Other · Unknown

### 19.5 BITS fields

**BITS Area**: Membership · Training · Website · BITS Connect · Technology
Support · Events · RIM Support · Education · Other

**Request Type**: Question · Technical Support · Membership · Account ·
Training · Accessibility · Feedback · Other

**Avoid collecting disability or medical information** unless it is actually
necessary to resolve the request.

---

## 20. Custom folders

The Custom Folders module works well with tags. FreeScout limits folder names
to **15 characters** and does not support nesting.

Recommended: `Overdue` · `Waiting` · `GitHub` · `A11y` · `Security` ·
`Blockers` · `Needs Triage` · `KB Candidate`

Keep names short. Folders should represent **actionable queues**, not every
possible category.

---

## 21. Workflows

Workflows are configured **per mailbox**. Build one master worksheet and
reproduce the applicable workflows in each mailbox.
Documentation: <https://freescout.net/module/workflows/>

Workflows can change status, assign users, add notes, add and remove tags, set
custom fields, move conversations, and trigger webhooks when API & Webhooks is
installed.

**New ticket classification.** Add the applicable `svc:` tag; add
`state:triage`; leave unassigned unless a reliable routing rule applies.
QUILL mailbox → `svc:quill`.

**Product routing (QUILL).** If Product = QUILL Radio, add `quill:radio` and
optionally assign to the Radio support team or lead. Repeat for major products.
Do not auto-assign to a single individual unless there is backup coverage.

**Accessibility intake.** If Issue Type = Accessibility, add `type:a11y` and
show it in the `A11y` folder; notify the accessibility lead if appropriate. **Do
not automatically mark all accessibility issues as blockers** — use Impact.

**Security / privacy.** If Issue Type = Security / Privacy, add
`type:security`, notify designated administrators, **do not automatically send
into public GitHub**, keep sensitive data out of public repositories, and
restrict mailbox access where practical. For serious vulnerability reporting,
consider a separate confidential procedure rather than normal support email.

**First-response aging.** If no staff response after one business day, add
`state:overdue`, place in `Overdue`, notify the assignee or team lead. Escalate
after another business day. Treat these as operational targets, not contractual
SLAs, unless the organisation intentionally establishes one.

**Waiting on customer.** Add `state:waiting` and set status Pending. After 3–5
business days send a polite reminder; after 7–10 send a closing notice and
close. If the customer replies later, let the ticket reopen — the mail bridge
and FreeScout already handle reactivation.

**Knowledge-base candidate.** When an agent spots a repeated question, add
`state:kb` so it appears in `KB Candidate`. Review recurring themes monthly.
This turns support volume into documentation improvement.

---

## 22. Saved replies

Create shared saved replies for consistent, accessible communication:

Welcome / acknowledgment · Need more information · Need application version ·
Need operating-system version · Need screen reader / AT information ·
Request reproduction steps · Request log file · Accessibility issue
acknowledgment · Known issue response · Feature request acknowledgment ·
GitHub escalation notice · Fix available · Fix included in release ·
Waiting for customer reminder · Closing due to no response · Resolution
confirmation · Knowledge-base link response · Security/privacy redirection

**Avoid robotic wording.** Saved replies are a starting point, not a
replacement for responding like a human.

---

## 23. End-user portals

Enable an End-User Portal for each major mailbox. FreeScout gives each mailbox
its own portal URL. Module: <https://freescout.net/module/end-user-portal/>

The portal lets users submit a ticket, authenticate by email, view their
tickets and reply to them. Custom fields can be exposed on portal and contact
forms where appropriate.

**Design principle.** Each portal should ask only for information useful to
that service. QUILL can ask for Product and Version; BITS Membership should not
ask for a software version.

**Branded entry points.** Use branded public domains that redirect to the
appropriate portal — `support.quillforall.org` → the QUILL portal URL. The
user's browser ultimately operates at the canonical FreeScout host, which is
what keeps sessions and links working.

---

## 24. Knowledge bases

Enable a Knowledge Base per mailbox where useful. FreeScout's KB operates per
mailbox. Module: <https://freescout.net/module/knowledge-base/>

**QUILL** — Getting Started · Installation · QUILL Editor · QUILL Lite ·
QUILL Radio · QUILL Cast · QUILL Weather · Keyboard Commands · Screen Readers ·
Troubleshooting · Known Issues · Release Notes · Reporting a Bug ·
Feature Requests · Privacy and Data

**GLOW** — Getting Started · GLOW Audit · GLOW Fix · GLOW Convert · Templates ·
Authentication · Understanding Results · Accessibility Review · Privacy ·
Troubleshooting · Known Issues

**Git Going** — Getting Started · Installing Git · Git Basics · GitHub Basics ·
Repositories · Commits · Branches · Pull Requests · Issues · GitHub Desktop ·
GitHub CLI · VS Code · Authentication · Screen Reader Tips ·
Keyboard Workflows · Course Exercises · Troubleshooting

**BITS** — Membership · Training · BITS Connect · Technology Support · Events ·
Programs · Frequently Asked Questions · Contact BITS

Section 53 lists the specific articles to publish before launch.

---

# Part three — GitHub escalation

## 25. The flow

The integration should protect customers from having to understand GitHub while
giving developers a clean engineering workflow.

```text
Customer
   |
   v
FreeScout ticket
   |
   v
Support triage
   |
   +---- resolved by support ----> Customer
   |
   +---- confirmed software issue
              |
              v
       Escalate to GitHub          <- a human decision, always
              |
              v
        GitHub issue
              |
              v
       Developer activity
              |
              v
       FreeScout internal updates
              |
              v
          Customer
```

**The support ticket remains the customer communication record. The GitHub
issue remains the engineering record.**

---

## 26. Method, and the two bridges

Use the FreeScout **API & Webhooks** module, a **manual** FreeScout workflow, a
small integration service called here the **GitHub bridge**, a **GitHub App**,
and GitHub webhooks.

**This is not the mail bridge.** The mail bridge (`helpdesk-mailbridge`) is
built and carries Postmark inbound into FreeScout. The GitHub bridge does not
exist yet. They share a word and nothing else.

**Avoid a personal access token for the permanent production integration.**
GitHub recommends GitHub Apps, minimum required permissions, webhook secrets
and limited subscriptions.

- App best practices:
  <https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/best-practices-for-creating-a-github-app>
- Webhooks with Apps:
  <https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/using-webhooks-with-github-apps>

**A note on what already exists.** The submission server
(`feedback-hub-submit:8095`, from the `feedback-hub` repository) already holds a
GitHub credential and files issues on behalf of accountless clients — QUILL's
Report a Bug, the picks suggestion form, and GLOW's feedback route. When you
build the GitHub bridge, look there first: the credential handling, the
sanitisation and the deployment pattern are solved, and a second service
holding a second GitHub token is worth avoiding.

---

## 27. GitHub bridge responsibilities

A small Python, Node.js or serverless service exposing two endpoints.

### 27.1 FreeScout to GitHub — `POST /freescout/github`

When an agent runs **Escalate to GitHub**:

1. FreeScout triggers a custom webhook.
2. The bridge receives the event.
3. It identifies the FreeScout conversation.
4. It retrieves structured ticket data through the FreeScout API.
5. **It checks whether a GitHub issue already exists.**
6. **It removes or excludes private customer information.**
7. It chooses the correct repository.
8. It creates the GitHub issue.
9. It records the issue number and URL back in FreeScout.
10. It adds an internal FreeScout note.
11. It adds `state:github`.

### 27.2 GitHub to FreeScout — `POST /github/freescout`

GitHub sends signed webhook events. React to: issue opened, labelled, assigned,
closed, reopened; selected comments; milestone or release changes if useful.

The bridge then locates the associated conversation, adds an **internal note**,
updates Developer Status, and changes tags where appropriate.

**Do not automatically send every GitHub comment to the customer.** Developer
conversations may contain implementation detail, security context or internal
discussion. Use internal notes first; a support agent decides what should be
communicated externally.

---

## 28. The issue template

An issue generated from support should look approximately like this:

```markdown
## Support Reference

FreeScout ticket: CA-1842

## Product

QUILL Radio

## Version

2.x

## Environment

- OS: Windows 11
- Assistive technology: JAWS
- Installation: Installed

## Problem

Concise technical summary written by support.

## Steps to Reproduce

1.
2.
3.

## Expected Result

...

## Actual Result

...

## Impact

High

## Accessibility

Yes

## Additional Technical Notes

Sanitized information useful to developers.

## Privacy

Customer name, email address, and private transcript intentionally omitted.
```

**Do not dump the complete support conversation into a public GitHub issue.**

---

## 29. Repository mapping

Maintain product-to-repository mapping in the bridge's configuration:

```text
QUILL Editor    -> organization/repository
QUILL Lite      -> organization/repository
QUILL Radio     -> organization/repository
QUILL Cast      -> organization/repository
GLOW            -> organization/repository
Git Going       -> training-materials repository
```

If several QUILL applications share one repository, the bridge can set
product-specific labels instead: `product:editor`, `product:radio`,
`product:cast`, `accessibility`, `support-escalation`, `bug`, `feature`.

---

## 30. Preventing duplicate issues

Before creating an issue:

1. Check the FreeScout **GitHub Issue Number** field.
2. If present, do not create another issue.
3. Add an internal note pointing at the existing one.
4. Optionally search GitHub for a ticket-reference label or support reference.

*(The submission server already implements a related idea for crash reports —
a fingerprint that deduplicates a live report against one filed later from a
saved traceback. Worth reading before writing this from scratch.)*

---

## 31. GitHub security and API credentials

Create a **dedicated GitHub App** and grant only required repository
permissions — likely **Issues: read and write**, **Metadata: read**. Request
more only if genuinely required.

- Store the App private key securely.
- Store FreeScout API credentials securely.
- Use HTTPS.
- Use a GitHub webhook secret, and **validate webhook signatures**.
- Log integration failures.
- Do not log full ticket bodies unnecessarily.
- Rotate secrets.
- Restrict the App to required repositories.

**Do not embed API keys** in source code, repositories, JavaScript delivered to
browsers, documentation, or ticket notes. Store secrets in environment
variables or a managed secret store.

For every credential, document: who owns it; what it can access; where it is
stored; the rotation procedure; the revocation procedure.

---

# Part four — GLOW's own mail

## 32. A second Postmark server, and why

GLOW sends its own mail — audit reports, admin sign-in links, workshop
artifacts, return links, Whisperer notices — and, with this work, receives
replies to it.

**It needs its own Postmark server.** A server has exactly one inbound webhook
URL and one inbound domain, and these are not the same thing:

| Server | Sends as | Receives at | Inbound webhook |
| --- | --- | --- | --- |
| `Community Access Help Desk` | the support addresses | those addresses | `helpdesk.community-access.org/postmark/inbound` |
| `GLOW production` | `no-reply@notify.letitglow.app` | `reply@inbound.letitglow.app` | `letitglow.app/mail/webhook/inbound` |

Separate on the merits too: different sending domains, different reputations,
and a token that can be rotated for one without stopping the other.

Create it as in section 3 — **Servers > Create Server**, named
`GLOW production` — then copy its **Server API Token** from **Settings > API
Tokens**. It is a server token, not an account token; GLOW never needs the
account token. Make a `GLOW staging` server too if you want somewhere safe to
test.

### Message streams

Confirm the server has two streams. A new one is created with both:

- **Default Transactional Stream**, stream ID `outbound`
- **Default Broadcast Stream**, stream ID `broadcast`

The stream **ID** is what the API wants, not the display name. GLOW uses
`outbound` for everything a person just asked for, and `broadcast` for the
30-day workshop nudge — a follow-up nobody asked for, which belongs on the
stream carrying a real unsubscribe link.

If either is missing, create it under **Message Streams > Create stream** with
exactly that ID.

### Account approval

A new Postmark account can only send to addresses on its own domain until
approved. Workshop participants and audit users are not on your domain, so
**request approval before your first event**. The honest answer to Postmark's
question is short:

> Transactional mail for an accessibility tool: audit reports the user asked
> for, sign-in links, and workshop materials sent to the participant who
> created them. Recipients are people who typed their own address into a form.
> One monthly follow-up to workshop attendees goes on a broadcast stream with
> an unsubscribe link.

Approval takes hours to a day. Do not leave it until the morning of a workshop.

---

## 33. DNS for sending: `notify.letitglow.app`

Two subdomains of `letitglow.app` are involved, and using subdomains rather
than the root is deliberate: a sending subdomain keeps transactional reputation
separate, and an inbound subdomain can take an MX record without disturbing the
root. That matters here, because the root already uses Namecheap forwarding:

```
$ dig +short MX letitglow.app
10 eforward1.registrar-servers.com.       (and four more)
```

On the `GLOW production` server: **Sender Signatures > Add Domain**, enter
`notify.letitglow.app`, create the records it shows.

**DKIM (required)**

```
Type:  TXT
Host:  <selector>._domainkey.notify.letitglow.app
Value: k=rsa;p=MIGfMA0GCSq...          (Postmark shows the real value)
```

**Return-Path (required for GLOW)**

```
Type:  CNAME
Host:  pm-bounces.notify.letitglow.app
Value: pm.mtasv.net
```

Postmark calls this optional. It is **not optional here.** It makes the
envelope sender a `letitglow.app` address, which makes SPF align with the From
address, which makes DMARC pass. Without it, a recipient domain with a strict
DMARC policy rejects or quarantines GLOW's mail and the only symptom is
silence.

**SPF** — not needed with the Return-Path CNAME in place. If required anyway,
`v=spf1 include:spf.mtasv.net ~all` on `notify.letitglow.app`. Never a second
record on a host that already has one.

**DMARC** — recommended, not required. Start at `p=none` with
`rua=mailto:dmarc@letitglow.app`, read the reports, then tighten.

Click **Verify**. DKIM and Return-Path must both show verified. More than a few
hours means a typo or a doubled zone suffix, not propagation.

---

## 34. DNS for receiving: `inbound.letitglow.app`

This is the half that makes GLOW's conversations two-way.

1. On the GLOW server, open **Settings > Inbound**. It shows an address like
   `a1b2c3d4e5f6@inbound.postmarkapp.com`. **That address already works**, so
   you can test everything today without touching DNS.
2. For a readable address of your own, set **Inbound Domain** to
   `inbound.letitglow.app` and add:

```
Type:     MX
Host:     inbound.letitglow.app
Value:    inbound.postmarkapp.com
Priority: 10
```

Once that resolves, `reply@inbound.letitglow.app` is what GLOW should use.

Three things to know:

- **The inbound domain must be a subdomain with no other MX record.** Do not
  point `letitglow.app` itself at Postmark; that would break the existing
  forwarding exactly as it would for `community-access.org` in section 5.
- **Postmark splits anything after a `+`** out of the local part and hands it
  to GLOW as `MailboxHash`. That is how
  `reply+9f3c...@inbound.letitglow.app` finds its conversation.
- **A reply is never discarded.** If the hash is missing, GLOW falls back to
  `In-Reply-To`, then to the sender's most recent open conversation, and files
  anything still unrouted as a new conversation an admin can see.

---

## 35. GLOW's webhooks

### The shared secret

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

The same value goes in the webhook URLs and in `POSTMARK_WEBHOOK_TOKEN`. Both
routes reject a request without it, and **return 503 if the variable is
unset**, so an unconfigured deployment cannot accidentally accept anonymous
posts.

### Inbound

**Settings > Inbound**, set the **Inbound Webhook** URL to:

```
https://letitglow.app/mail/webhook/inbound?token=YOUR_WEBHOOK_SECRET
```

GLOW also accepts the secret as HTTP basic auth or in an
`X-Postmark-Webhook-Token` header.

### Events

**Message Streams > Default Transactional Stream > Webhooks**:

```
https://letitglow.app/mail/webhook/events?token=YOUR_WEBHOOK_SECRET
```

Tick **Bounce**, **Spam Complaint**, **Delivery**, **Subscription Change**.

Leave **Open** and **Click** unticked. GLOW does not use them, and open
tracking means embedding a tracking pixel in mail sent to people who use screen
readers and text-only clients — worth avoiding on principle as well as on
privacy grounds.

**Add the same webhook to the Default Broadcast Stream**, so an unsubscribe
from the 30-day nudge is honoured everywhere.

---

## 36. Environment variables

Set these in the `.env` that `web/docker-compose.prod.yml` loads, then restart
the web container.

### 36.1 The whole block, to paste

Delete lines you do not want yet. Each feature checks its own variables and
reports itself unavailable rather than failing.

```sh
# --- Postmark: sending -------------------------------------------------
POSTMARK_SERVER_TOKEN=
POSTMARK_FROM_EMAIL=no-reply@notify.letitglow.app
POSTMARK_MESSAGE_STREAM=outbound
POSTMARK_BROADCAST_STREAM=broadcast

# --- Postmark: two-way conversations -----------------------------------
POSTMARK_INBOUND_ADDRESS=reply@inbound.letitglow.app
POSTMARK_WEBHOOK_TOKEN=
POSTMARK_WEBHOOK_ALLOWED_IPS=

# --- Addresses shown to people -----------------------------------------
GLOW_SUPPORT_EMAIL=glow@community-access.org

# --- Help desk: support tickets into FreeScout -------------------------
HELPDESK_BRIDGE_URL=http://helpdesk-mailbridge:8096/postmark/inbound
HELPDESK_BRIDGE_USER=
HELPDESK_BRIDGE_PASSWORD=
HELPDESK_SUPPORT_EMAIL=glow@community-access.org
HELPDESK_URL=https://helpdesk.community-access.org
HELPDESK_CATEGORIES=bug,accessibility,regression,support
HELPDESK_MESSAGE_DOMAIN=letitglow.app
```

**`HELPDESK_SUPPORT_EMAIL` must be in the mail bridge's
`MAILBRIDGE_RECIPIENTS`** (section 13.1), or every ticket gets a 403. Until the
GLOW mailbox exists, point it at `support@community-access.org`, which is
already allowed.

**`.env.example` has not been updated.** It is a credentials file and was left
untouched deliberately. Copy the block above with empty values if you want the
names in it.

### 36.2 Every variable

| Variable | Default | Without it |
| --- | --- | --- |
| `POSTMARK_SERVER_TOKEN` | unset | Nothing sends. Every mail feature reports itself unavailable |
| `POSTMARK_FROM_EMAIL` | `no-reply@notify.letitglow.app` | Uses the default, which must be a verified sender |
| `POSTMARK_MESSAGE_STREAM` | `outbound` | Uses `outbound` |
| `POSTMARK_BROADCAST_STREAM` | `broadcast` | Uses `broadcast`; only the 30-day nudge uses it |
| `POSTMARK_INBOUND_ADDRESS` | unset | GLOW sends but cannot be answered. Conversations report unavailable |
| `POSTMARK_WEBHOOK_TOKEN` | unset | Both webhook routes return 503. Nothing inbound is accepted |
| `POSTMARK_WEBHOOK_ALLOWED_IPS` | unset | No source-address check; the secret is the only control |
| `GLOW_SUPPORT_EMAIL` | unset | The conversations page has no address to offer when replies are off |
| `HELPDESK_BRIDGE_URL` | unset | No tickets filed. Feedback still stored, still reaches GitHub |
| `HELPDESK_BRIDGE_USER` | unset | As above |
| `HELPDESK_BRIDGE_PASSWORD` | unset | As above |
| `HELPDESK_SUPPORT_EMAIL` | `support@community-access.org` | Uses the default |
| `HELPDESK_URL` | `https://helpdesk.community-access.org` | Uses the default; display only |
| `HELPDESK_CATEGORIES` | `bug,accessibility,regression,support` | Uses the default. `all` files everything |
| `HELPDESK_MESSAGE_DOMAIN` | `letitglow.app` | Uses the default; only affects generated Message-IDs |

`POSTMARK_WEBHOOK_ALLOWED_IPS` is a second lock on the webhook routes. The
shared secret is the primary control; the allow-list is belt and braces, and is
empty by default because an allow-list that goes stale rejects real mail
silently. If you set it, take the addresses from Postmark's own documentation
rather than from this file.

Nothing is read at import time. A change needs a container restart because the
process holds the environment, not because anything is cached.

---

## 37. Proving GLOW's mail works

### 37.1 Sending

1. Sign in at `/admin`.
2. On the admin queue page, the email panel should say Postmark is configured,
   name the sender address, and name the `outbound` stream.
3. Send a test email to yourself.
4. Check the headers for `DKIM=pass` and `SPF=pass`.

If it lands in spam, DKIM or Return-Path is the first thing to check, not the
message content.

### 37.2 Receiving

1. Reply to that test email from an ordinary mail client.
2. Open `/mail/admin`. The reply should appear as a new conversation within
   seconds.
3. In Postmark, **Activity > Inbound** shows every message received and the
   HTTP status GLOW returned. 403 means the secret does not match; 503 means
   `POSTMARK_WEBHOOK_TOKEN` is unset.

### 37.3 A real round trip

1. From `/mail/admin`, open the conversation and send a reply.
2. Check it arrives, with a Reply-To of
   `reply+<something>@inbound.letitglow.app`.
3. Reply to that. It should land on the same conversation, in order.
4. Open `/mail/conversations` in a browser carrying the participant or passport
   cookie. Same conversation, same order, with a box to answer in.

### 37.4 Bounces

1. Send a test email to an address you know does not exist.
2. Within a minute, `/mail/admin` should list it on the do-not-send list.
3. Try again. GLOW refuses and says why.
4. Clear the suppression from `/mail/admin` when you want to re-enable it.

### 37.5 Machine-readable check

`GET /mail/admin/health` (admin session required):

```json
{
  "sending_configured": true,
  "inbound_address": "reply@inbound.letitglow.app",
  "webhook_secret_set": true,
  "conversations_available": true,
  "open_threads": 3,
  "unread_for_staff": 1,
  "suppressed": 0,
  "inbound_webhook_url": "https://letitglow.app/mail/webhook/inbound",
  "events_webhook_url": "https://letitglow.app/mail/webhook/events",
  "helpdesk": {
    "configured": true,
    "support_email": "glow@community-access.org",
    "helpdesk_url": "https://helpdesk.community-access.org",
    "credentials_set": true,
    "categories": ["bug", "accessibility", "regression", "support"]
  }
}
```

---

## 38. What this gives each part of GLOW

### Accounts

GLOW has no passwords and no sign-up wall, by design. "Accounts" means three
identities, and mail makes each portable:

- **Admin accounts** (`/admin`). Email sign-in links, access requests, approval
  notices. OAuth still works without mail; the email route does not.
- **Passports** (`/passport`). A single-use link that restores somebody's
  settings on another device. Somebody who has tuned contrast, type scale,
  reduced motion and the cognitive profile can get that back on a phone.
- **Workshop participants**. Return links, the end-of-day artifact, the agent
  package, and the 30-day follow-up.

Admin mail and workshop mail now carry a reply path: the address on the message
is monitored, and an answer reaches a person.

**Audit report delivery is deliberately left one-way.** That email tells the
recipient "your email address was not stored", and that is true — opening a
conversation would store it. The sender accepts an optional conversation
(`reply_thread=`) if you later decide otherwise, but nothing passes one today,
and the promise in the message should change first.

### Two-way conversations

- A participant replies to any GLOW email. It lands on the right conversation,
  visible at `/mail/admin`.
- Staff answer from `/mail/admin`. The participant receives ordinary email and
  can reply again.
- Either side can work in the browser: `/mail/conversations` shows the same
  thread to the person who owns it, identified by the passport or workshop
  cookie they already have. No new account, no password.
- A participant can start a conversation from inside GLOW without opening a
  mail client.

### The training platform

- The workshop artifact email carries a per-participant Reply-To, so "one
  question about step 3" reaches a facilitator rather than a no-reply address.
- Conversations carry the session code, so a facilitator can see which session
  a question came from.
- The 30-day nudge goes on the broadcast stream with a working unsubscribe,
  honoured across every GLOW feature at once.

### Reputation

- Hard bounces, spam complaints and unsubscribes are recorded and honoured
  everywhere. Without this, one feature suppresses an address and the next one
  mails it again, which is how a sending domain gets itself blocked.
- Soft and transient bounces are recorded but not suppressed. A full mailbox on
  Tuesday is not a reason to stop mailing somebody on Friday.
- Out-of-office replies are recorded as events rather than filed as messages,
  so a vacation responder does not appear in somebody's conversation.

---

## 39. GLOW tickets into the help desk

GLOW's feedback form files support tickets into the same FreeScout help desk.
**This path does not go through Postmark at all.**

```
Postmark inbound --webhook--> mail bridge --> Maildir --> Dovecot --> FreeScout
GLOW feedback form ----------/
```

GLOW posts to the same bridge, with the same payload shape. The bridge is
attached to the `web_default` Docker network that GLOW already runs on, so it
is reachable as `helpdesk-mailbridge:8096` with no public round trip, no
Postmark send, and no second inbound domain.

### Why not the other two options

**Not FreeScout's API.** That means reimplementing the part of FreeScout worth
having: `Message-ID` and `In-Reply-To` matching, duplicate detection,
customer-versus-agent replies, auto-reply and bounce handling, reactivating a
closed conversation.

**Not sending through Postmark.** Postmark only sends from a verified domain,
so the ticket would arrive `From: no-reply@notify.letitglow.app` and FreeScout
would file every ticket raised in the product against GLOW rather than against
the person who raised it.

### What GLOW sends

An ordinary RFC-822 message:

- `From:` the submitter's name and address, so they are the customer.
- `To:` the GLOW support address.
- `Subject:` their short summary, or `GLOW <category> request`.
- Body: what they wrote, then the context an agent needs — application,
  version, platform, category, the task in progress, the GLOW feedback id, and
  the tracker issue URL when one was filed.
- `X-GLOW-Address-Verified: no`, and a line in the body saying the same thing
  in words.

That last one is not decoration. Anyone can type anyone's address into a
feedback form, and a help desk that replies to it is a way to send mail to a
stranger over Community Access's signature. **Do not remove that line.**

### What opens a ticket

Both conditions must hold:

- The category is `bug`, `accessibility`, `regression` or `support`. Praise and
  general comments are still stored and still reach the admin feedback list;
  they do not open a ticket somebody has to close. `HELPDESK_CATEGORIES=all`
  changes that.
- The person left an email address. A ticket is a promise somebody will answer;
  without an address there is nobody to answer.

### What it cannot break

Nothing here can lose a bug report. The feedback entry is stored, and the
GitHub issue filed, before the ticket is attempted. A help desk that is
unconfigured, unreachable or refusing costs a ticket, never a submission. The
outcome is recorded per entry in `helpdesk_status` and `helpdesk_error`, so a
failure is visible rather than silent.

### Setting it up

```bash
ssh lp.csedesigns.com
docker inspect helpdesk-mailbridge --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep MAILBRIDGE_WEBHOOK
```

Put the pair into GLOW's `.env` as `HELPDESK_BRIDGE_USER` and
`HELPDESK_BRIDGE_PASSWORD`, with the other variables in section 36.1, and
restart.

Two things that will catch you out:

- **`HELPDESK_SUPPORT_EMAIL` must be in `MAILBRIDGE_RECIPIENTS`.** A recipient
  the bridge does not serve gets a 403.
- **`MAILBRIDGE_TRUSTED_IPS` must stay empty**, or include GLOW's container
  address. It is empty today, which is what makes this work; the credential is
  the control. Setting it to Postmark's source addresses to lock down the
  public webhook will start failing GLOW's posts with a 403, and the cause will
  not be obvious.

### Checking it

1. Submit a bug report at `/feedback` with an address you can read.
2. The thank-you page should say a conversation has been opened.
3. The ticket appears in FreeScout, **from your address, not from GLOW**.
4. Reply as an agent. The reply goes out through FreeScout's Postmark SMTP from
   section 7, straight to the submitter.
5. `GET /mail/admin/health` includes a `helpdesk` block; `/mail/admin` shows
   the same thing in words.

### The boundary between the two systems

A help desk ticket is **not** a GLOW conversation:

- **Help desk tickets** (`/feedback`, and QUILL's Report a Bug) are for
  support: a person needs an answer from a human, and FreeScout has the queue,
  the agents and the history. Once filed, GLOW is out of the loop.
- **GLOW conversations** (`/mail/conversations`) are for mail GLOW itself
  started — a workshop artifact, a return link — where the reply belongs next
  to the work it is about.

Running one question through both would mean two places to answer it and two
answers that can disagree. When GLOW cannot hold a conversation itself, the
conversations page points at the help desk address instead of apologising.

### Picks suggestions do not move here

A station or podcast suggestion goes straight to GitHub and stays there. It has
no customer relationship to preserve and nothing personal in it — the *point* is
that it becomes public — and it is already consumed by a workflow. Routing
structured data through a mailbox would mean a person retyping it. Support and
content contribution both produce issues, and should not be conflated because
of it.

---

# Part five — operations

## 40. Reports, satisfaction and AI

### Reports

Use Reports to measure **service quality, not to rank volunteers
competitively.** Recommended monthly metrics: new tickets; tickets by mailbox;
by product; by issue type; accessibility-related tickets; average first
response time; tickets waiting more than one business day; resolved; reopened;
GitHub escalations; top recurring problems; knowledge-base candidates;
satisfaction rating; unassigned backlog.

Use trends to improve documentation, training, product design, accessibility,
staffing and automation.

### Satisfaction ratings

Enable after basic operation is stable. Keep the survey simple; do not make
users complete a long form after every interaction. Use feedback to identify
poor explanations, delays, difficult workflows, documentation gaps, product
frustrations — and excellent practices worth repeating.

### AI integration

The official module is free: <https://freescout.net/module/ai-integration/>

Use AI initially for **drafting a response, summarising a long ticket, and
improving grammar and clarity.**

Do **not** initially use it for automatic customer replies, autonomous ticket
closure, autonomous GitHub escalation, decisions about accessibility severity,
or security and privacy decisions.

**Establish a data policy before enabling an external provider.** Support
tickets may contain names, email addresses, logs, uploaded documents, account
information, accessibility information and confidential organisational
information. Determine what may be sent to an external provider. A local
provider such as Ollama may be appropriate where privacy needs justify it — and
GLOW already runs an Ollama-first AI configuration, so the pattern exists here.

**Human review remains required** before sending AI-generated customer
communication.

---

## 41. Accessibility

Accessibility is not merely another ticket category. **The help desk itself
must be usable.** FreeScout identifies screen-reader support as a core feature,
but the production configuration must still be tested, because modules, custom
CSS, widgets, forms and branding all affect usability.

### What to test

Base FreeScout · agent interface · login · 2FA · End-User Portal · contact form
· Knowledge Base · custom fields · saved replies · reports · workflow dialogs ·
GitHub escalation controls · error messages · file upload · satisfaction survey

### Test matrix

**Screen readers** — JAWS + Edge or Chrome; NVDA + Firefox; NVDA + Chrome or
Edge; Narrator + Edge; VoiceOver + Safari for the public portal where
practical.

**Input** — keyboard only; screen-reader keyboard navigation; no mouse; browser
zoom at 200 percent, and higher where practical; Windows high-contrast and
forced-colors behaviour.

**Validate** — logical heading structure; meaningful page titles; form labels;
required-field identification; error identification; error recovery; visible
keyboard focus; predictable focus movement; accessible dialogs; status changes
announced where needed; link purpose; button names; table navigation; no
colour-only meaning; sufficient contrast; accessible file upload; accessible
knowledge-base articles.

### Three mechanisms that were found not to work

Discovered while building the suggestion form, and worth knowing before relying
on any of them in a portal form:

- `role="alert"` plus focus reads the whole error list twice with the first
  reading clipped, and an unchanged alert may not fire at all — so resubmitting
  the same errors announces nothing.
- Clearing and rebuilding a live region in one task announces nothing either,
  which would silence every repeated rate-limit refusal a server produces *by
  design*.
- Disabling the focused submit button strands the keyboard many tab stops away,
  announced by nothing.

All three were replaced in that form. Do not reintroduce them here.

---

## 42. CAPTCHA

**Do not add CAPTCHA simply because a security module provides it.**

Start with 2FA for agents, strong passwords, rate limiting and server
protections, the Spam Filter, email authentication, and monitoring.

Add CAPTCHA only if abuse demonstrates a need. If one is introduced, test the
complete customer experience with assistive technology before production
deployment.

**Turnstile, never reCAPTCHA.** The submission server already supports
Turnstile and has it switched off, because a challenge nobody needs is a
barrier nobody asked for. reCAPTCHA's image grids are precisely the barrier
this organisation exists to remove: a spam control that locks out blind users to
keep out bots has failed at the only job that matters here.

---

## 43. Branding and customer-facing language

Use Customization & Rebranding to make the service feel intentional.

Primary identity: **Community Access Help Desk**. Sub-services: QUILL Support ·
GLOW Support · BITS Support · Git Going with GitHub.

Use restrained customization. Do not sacrifice contrast, focus indication,
semantic structure, readability, browser zoom or forced-colors support. **A
clean accessible interface is preferable to elaborate visual branding.**

Recommended front door:

> Welcome to the Community Access Help Desk. Choose the service you need help
> with, or contact Community Access if you are not sure where to begin.

Service links: Get Help with QUILL · Get Help with GLOW · Get Help with Git
Going with GitHub · Get Help with BITS · General Community Access Help

**Avoid forcing customers to understand internal organisational structure.**

---

## 44. Privacy and attachments

### Privacy notice

Publish a concise support privacy notice explaining: what information support
tickets collect; why; who may see it; how long support records are retained;
whether AI may be used; whether technical information may be escalated to
GitHub; that personally identifying information will not normally be copied
into public GitHub issues; and how a user can request deletion where
applicable.

**Do not request information merely because a field can be created.**

### What GLOW's side does

- Conversations are deleted 180 days after their last message; `/mail/admin`
  has a button to apply that now.
- Deleting a conversation deletes its messages and the stored address
  immediately.
- Inbound attachments are recorded by name only; GLOW does not store contents.
- Open and click tracking are deliberately not enabled anywhere.
- A participant's conversations are readable only by the cookie identity that
  owns them; there is no way to enumerate somebody else's by guessing an id.

### The mail bridge's audit trail

A SQLite file in the `bridge-state` volume records the Postmark message id, the
Maildir filename, the spam score, and the **length** of the subject rather than
the subject itself. An administrator reads that table, and message content
belongs in the help desk where access is controlled, not in a second store that
would also have to be secured and backed up.

### Spam

**Spam is scored, logged, and delivered anyway.** A support inbox for
accessibility work is full of long quoted threads, unusual markup and
assistive-technology jargon — the shapes a filter mistrusts — so agents mark
spam by hand until there is evidence for a threshold.

### Attachment policy

Define accepted types, and allow only those actually needed. Consider: TXT,
LOG, JSON, PNG, JPG, PDF, DOCX.

Warn users not to upload passwords, API keys, private SSH keys, authentication
tokens, or highly confidential documents unless explicitly requested through an
approved process.

---

## 45. Backup and recovery

Before launch, document backups for: the FreeScout database; `.env`;
application configuration; module configuration; uploaded attachments; custom
code; the GitHub bridge; reverse-proxy configuration. On the GLOW side, add
`instance/email_threads.db` and `instance/feedback.db`.

**Do not rely solely on VM or server snapshots. Test restore procedures.** A
backup that has never been restored is an assumption, not a recovery plan.

Recommended: automated daily database backup; regular attachment backup; an
off-server copy; a retention policy; a periodic restore test.

### What GLOW's work stores

| Where | What | Retention |
| --- | --- | --- |
| `instance/email_threads.db` | Conversations, messages, do-not-send list, webhook events | Conversations 180 days from last message; suppressions and events until deleted |
| `instance/feedback.db` | Four new columns: `helpdesk_message_id`, `helpdesk_status`, `helpdesk_error`, `helpdesk_filed_at` | As the existing feedback table |

The schema migration is automatic and additive, so an existing `feedback.db`
upgrades in place with no migration step and no downtime.

**The do-not-send list is the one worth protecting.** Losing
`email_threads.db` loses conversation history, which is unfortunate; it also
loses every suppression, which means GLOW starts mailing hard-bounced and
spam-complained addresses again, and that costs sending reputation for every
other user.

---

## 46. Logging and monitoring

Monitor: FreeScout application errors; failed email retrieval; failed outbound
email; cron failures; queue failures; API errors; GitHub webhook failures;
bridge failures (both bridges); disk usage; database availability; TLS
certificate expiration.

**Send administrative alerts somewhere independent of the help desk.** If the
help desk is down, an alert that exists only inside the help desk is not
useful.

`GET /mail/admin/health` on GLOW is suitable for an uptime monitor.

### Rate limits on the new GLOW routes

| Route | Limit |
| --- | --- |
| `POST /mail/webhook/inbound` | 120 per minute |
| `POST /mail/webhook/events` | 240 per minute |
| `POST /mail/conversations/<id>/reply` | 20 per hour |
| `POST /mail/conversations/start` | 10 per hour |

Webhook limits are generous on purpose, for the reason in section 6. They are
per process, so with N workers the effective limit is N times these numbers.

---

## 47. Update policy

Before major updates:

1. Read FreeScout release notes.
2. Read installed module requirements.
3. Create a backup.
4. Confirm a restore point.
5. Update FreeScout.
6. Update modules.
7. Clear cache if required.
8. Test agent login.
9. Test an inbound ticket.
10. Test a reply.
11. Test the portal.
12. Test the GitHub bridge.
13. Perform a brief accessibility regression check.

**Avoid customizing official module code** unless necessary; local
modifications complicate upgrades.

On this deployment, `ENABLE_AUTO_UPDATE` and FreeScout's in-app updater are
both **off** deliberately: an unattended upgrade of a help desk is how a Monday
morning starts badly. And re-read the `APP_KEY` warning in section 9 before any
update, because an update is a recreate.

---

## 48. Governance and review

### Roles

**Platform Owner** — FreeScout server, modules, backups, updates, security, DNS
coordination, API credentials.

**Help Desk Administrator** — mailboxes, users, fields, tags, workflows, saved
replies, reports.

**Program Leads** — QUILL, GLOW, BITS, Git Going.

**Developer Liaison** — GitHub escalation quality, issue mapping,
developer-status updates, preventing duplicate issues.

**Accessibility Lead** — portal acceptance testing, agent-interface testing,
accessibility workflow, periodic regression testing.

**Knowledge Manager** — knowledge-base quality, removing stale articles,
converting recurring tickets into documentation.

One person may initially perform several roles, but the responsibilities should
still be written down.

### Monthly

1. Review overdue tickets.
2. Review unassigned tickets.
3. Review top ticket categories.
4. Review accessibility tickets.
5. Review open GitHub escalations.
6. Review satisfaction feedback.
7. Review spam and abuse.
8. Review failed integrations.
9. Review knowledge-base candidates.
10. Publish or update documentation.
11. Review agent access.
12. Review module and FreeScout updates.

### Quarterly

- Test backup restoration.
- Review API credentials.
- Review GitHub App permissions.
- Review DMARC posture.
- Conduct accessibility regression testing.
- Review retention and privacy practices.

---

# Part six — delivery

## 49. Deployment phases

### Phase 1 — Foundation

- [ ] Confirm production server.
- [ ] Confirm the canonical hostname (decision 1, section 0.2).
- [ ] Configure HTTPS.
- [ ] Confirm current FreeScout version.
- [ ] Confirm cron.
- [ ] Confirm backup.
- [ ] Confirm outbound mail.
- [ ] Confirm inbound mail.
- [ ] Create administrator accounts.

### Phase 2 — Purchase modules

- [ ] Open <https://freescout.net/modules/>
- [ ] Add recommended paid modules to the shared cart.
- [ ] Review cart before checkout.
- [ ] Complete one checkout transaction.
- [ ] Save receipt; store licence keys; document the purchasing account.
- [ ] Install modules in the recommended order.
- [ ] Install the free AI Integration module, leaving external AI disabled
      until the policy review in section 40.

### Phase 3 — Domains and email

- [ ] Configure the canonical help domain.
- [ ] Configure branded support aliases.
- [ ] Obtain TLS certificates for web aliases.
- [ ] Configure support mailboxes.
- [ ] Configure Postmark SMTP where appropriate.
- [ ] Validate SPF for every sending domain (merge, never duplicate).
- [ ] Validate DKIM.
- [ ] Configure DMARC.
- [ ] **Extend `MAILBRIDGE_RECIPIENTS` for every new address.**
- [ ] Test replies from every mailbox.
- [ ] Confirm Reply-To / From behaviour.

### Phase 4 — Mailboxes

- [ ] Create QUILL Support.
- [ ] Create GLOW Support.
- [ ] Create Community Access.
- [ ] Create Git Going with GitHub.
- [ ] Create BITS Support.
- [ ] Configure signatures.
- [ ] Configure auto replies.
- [ ] Configure mailbox permissions.
- [ ] Configure Teams.

### Phase 5 — Classification

- [ ] Create the tag taxonomy.
- [ ] Create common custom fields.
- [ ] Create mailbox-specific custom fields.
- [ ] Create the impact model.
- [ ] Create custom folders.
- [ ] Configure ticket numbering.
- [ ] Document naming standards.

### Phase 6 — Workflows

- [ ] New-ticket service tagging.
- [ ] Product tagging.
- [ ] Accessibility routing.
- [ ] Security/privacy routing.
- [ ] First-response aging.
- [ ] Waiting-on-customer reminder.
- [ ] Overdue escalation.
- [ ] Knowledge-base candidate workflow.
- [ ] GitHub escalation manual workflow.

### Phase 7 — Portal and knowledge base

- [ ] Configure the End-User Portal for each service.
- [ ] Configure public redirect domains.
- [ ] Add appropriate intake fields.
- [ ] Build knowledge-base categories.
- [ ] Publish the initial articles from section 53.
- [ ] Configure branding.
- [ ] Test widgets if used.
- [ ] Perform an accessibility review.

### Phase 8 — GitHub bridge

- [ ] Create the GitHub App.
- [ ] Restrict repository permissions.
- [ ] Configure the webhook secret.
- [ ] Deploy the GitHub bridge.
- [ ] Store secrets securely.
- [ ] Configure the FreeScout API key.
- [ ] Configure the FreeScout custom webhook.
- [ ] Build the repository mapping.
- [ ] Build the sanitised issue template.
- [ ] Write the issue URL back to FreeScout.
- [ ] Process GitHub status webhooks.
- [ ] Test duplicate prevention.
- [ ] Test security/privacy exclusions.
- [ ] Add integration logging.

### Phase 9 — Accessibility acceptance

- [ ] JAWS testing.
- [ ] NVDA testing.
- [ ] Narrator testing.
- [ ] Keyboard-only testing.
- [ ] Portal testing.
- [ ] Knowledge-base testing.
- [ ] Form validation testing.
- [ ] 200 percent zoom.
- [ ] Forced-colors / high-contrast testing.
- [ ] Mobile public-portal testing.
- [ ] Document discovered issues.
- [ ] Remediate launch blockers.

### Phase 10 — Pilot

Start with a small group of agents, piloting QUILL, GLOW, Git Going and BITS.

Measure: misrouted tickets; missing fields; excessive required fields; workflow
errors; email deliverability; accessibility barriers; GitHub duplication; agent
confusion; knowledge-base gaps.

Adjust before public launch.

---

## 50. Launch checklist

A production launch is ready when all of the following are true:

- [ ] One canonical FreeScout URL is stable.
- [ ] HTTPS is valid.
- [ ] Backups are working.
- [ ] The restore procedure is documented **and has been tested**.
- [ ] Cron is healthy.
- [ ] Each mailbox receives email.
- [ ] Each mailbox sends email.
- [ ] SPF, DKIM and DMARC are validated for every sending domain.
- [ ] Every mailbox address is in `MAILBRIDGE_RECIPIENTS` (or uses IMAP direct).
- [ ] Agent permissions are correct.
- [ ] 2FA is enabled.
- [ ] Required modules are installed.
- [ ] Tags are standardized.
- [ ] Custom fields are documented.
- [ ] Workflows have been tested.
- [ ] Portals work.
- [ ] Knowledge bases work.
- [ ] Branded domains redirect correctly.
- [ ] The GitHub bridge works.
- [ ] Public GitHub issues do not leak customer data.
- [ ] Accessibility testing is complete.
- [ ] The privacy notice is published.
- [ ] Support staff have training.
- [ ] An outage contact method exists **outside** FreeScout.

---

## 51. Agent operating procedure

Every new ticket should follow approximately this path:

1. Read the customer's entire request.
2. Confirm the correct mailbox and service.
3. Set Issue Type.
4. Set Impact.
5. Set Product or Area where applicable.
6. Capture Version, OS and AT **only when relevant**.
7. Assign, or leave in the correct team queue.
8. Reply promptly.
9. Troubleshoot.
10. Use internal notes for staff discussion.
11. Escalate confirmed product defects to GitHub.
12. **Keep the customer in FreeScout.**
13. Resolve or close when complete.
14. Mark recurring topics as knowledge-base candidates.

**Do not require customers to move to GitHub to receive support.**

---

## 52. Support philosophy

### Meet people where they are

Users should be able to begin with a simple email or an accessible form. They
should not need to understand GitHub, repository structure, issue labels,
internal teams, product ownership or technical terminology.

**Support owns the complexity.**

### Accessibility is the floor; usability is the goal

A technically conforming portal that is confusing or difficult to navigate is
not good enough. The measure of success is whether people can effectively and
independently get help.

### Preserve human judgment

Automation should categorize, remind, route, surface and integrate.

Automation should **not** replace judgment about severity, privacy,
accessibility impact, customer communication, security, or whether a problem
belongs in public GitHub.

---

## 53. Initial knowledge-base articles

Publish these before launch.

**Universal**

1. How to Contact Support
2. What Information Helps Us Solve a Problem
3. How We Handle Your Support Information
4. How Accessibility Issues Are Reported
5. What Happens When a Bug Is Sent to GitHub

**QUILL**

1. Installing QUILL
2. Portable Versus Installed Versions
3. Finding Your QUILL Version
4. Reporting a QUILL Bug
5. QUILL Keyboard Basics
6. QUILL and JAWS
7. QUILL and NVDA
8. Known Issues
9. Release Notes

**GLOW**

1. What GLOW Does
2. Getting Started
3. Understanding Audit Results
4. Human Review Still Matters
5. Reporting a GLOW Problem
6. Privacy and Uploaded Content

**Git Going**

1. Installing Git
2. Git Versus GitHub
3. Creating a Repository
4. Cloning a Repository
5. Commit and Push
6. Pulling Changes
7. Branch Basics
8. Pull Requests
9. Screen Reader Tips for GitHub
10. Common Authentication Problems

---

## 54. Final topology

```text
                    Internet
                       |
      +----------+-----+------+-----------+
      |          |            |           |
  QUILL      GLOW         BITS        Git Going
  Support    Support      Support
      |          |            |           |
      +----------+-----+------+-----------+
                       |
               Branded redirects
                       |
                       v
        helpdesk.community-access.org
                       |
                  FreeScout
                       |
      +----------------+------------------+
      |        |        |        |        |
   QUILL     GLOW   Community  Git Going  BITS
      |        |        |        |        |
      +----------------+------------------+
                       |
          Tags / Fields / Workflows
                       |
       +---------------+---------------+
       |                               |
 Knowledge Bases                API & Webhooks
                                       |
                                       v
                               GitHub bridge
                                       |
                                       v
                                  GitHub App
                                       |
                                       v
                              GitHub Repositories

Mail in:   Namecheap forwarding -> Postmark -> mail bridge -> Dovecot
           Microsoft 365 -> FreeScout IMAP/OAuth  (bits-acb.org only)
           GLOW /feedback -> mail bridge          (no Postmark)
Mail out:  FreeScout -> Postmark SMTP
```

**Final recommendation.** Build one Community Access FreeScout service and let
programs have distinct identities inside it. Keep one canonical application
URL, one module-licence set, one security model, one reporting strategy, one
support philosophy. Separate programs using mailboxes, teams, permissions,
portal entry points, knowledge bases, custom fields, tags and workflows. Use
GitHub only after human triage, with FreeScout remaining the customer's source
of truth.

---

# Part seven — reference

## 55. What is already running, and what is not

Observed on lp.csedesigns.com on 11 September 2026. Checked, not assumed.
Re-check before relying on it; a server moves on and a document does not.

### Already done

| | |
| --- | --- |
| `helpdesk.community-access.org` DNS | Resolves to `107.175.91.158` |
| Caddy site block | Live, `/postmark/*` routed to the mail bridge ahead of the catch-all |
| TLS certificate | Issued, valid |
| FreeScout | Running as `helpdesk-app`, tiredofit/freescout 1.8.219, pinned by digest |
| MariaDB, Dovecot, mail bridge | `helpdesk-db`, `helpdesk-imap`, `helpdesk-mailbridge` |
| Mail bridge health | Answering `/health` every minute |
| Bridge reachable from GLOW | Yes — `helpdesk-mailbridge:8096` returns 401 without credentials, the correct refusal |
| `MAILBRIDGE_RECIPIENTS` | `support@community-access.org` **only** |
| `MAILBRIDGE_TRUSTED_IPS` | Empty, which is what lets GLOW post to it |
| `MAILBRIDGE_PATH` | `/postmark/inbound` |
| Submission server | `feedback-hub-submit:8095`, live, filing GitHub issues |

The mail bridge is attached to **both** `helpdesk_default` and `web_default`.
GLOW (`web-web-1`, from `/home/jeffbis/app/web`) is on `web_default`. That
shared network is why the ticket path needs no public round trip. If either
container is moved off `web_default`, GLOW's tickets stop, and the symptom is a
connection error in the feedback log rather than a visible outage.

### Not done

| | |
| --- | --- |
| Postmark account | Not created, or not wired to this deployment |
| `support@community-access.org` into Postmark | No. Namecheap forwarding today |
| FreeScout outbound SMTP | Not configured |
| `help.community-access.org` | Does not resolve |
| Other mailboxes | None created |
| Modules | Not purchased |
| GitHub bridge | Not built |
| `inbound.letitglow.app` MX | Does not exist. GLOW cannot receive replies yet |
| GLOW's `.env` | Untouched |

### DNS as measured

| Domain | MX | Notes |
| --- | --- | --- |
| `community-access.org` | Namecheap forwarding (5 records) | GitHub Pages A records |
| `quillforall.org` | Namecheap forwarding (5 records) | GitHub Pages A records |
| `letitglow.app` | Namecheap forwarding (5 records) | Root; GLOW uses subdomains |
| `quillville.org` | Namecheap forwarding (5 records) | Parked |
| `bits-acb.org` | **Microsoft 365**, strict `-all` SPF | Different handling; section 13.2 |
| `glow.bits-acb.org` | Resolves via `letitglow.app` — **looks like a CNAME** | Cannot carry its own mail; decision 3 |
| `inbound.letitglow.app` | None | Needs the MX in section 34 |
| `help.community-access.org` | Does not resolve | Decision 1 |

### Where things stand, by route

| Route | Account needed? | Status |
| --- | --- | --- |
| Quill Radio, Suggest a Station or Podcast | No | Working. Files an issue with the bundled issues-only token |
| `quillforall.org/picks/suggest/` | No | Posts to the submission server, which files the issue |
| `lp.csedesigns.com/submit/picks` | — | Live. feedback-hub 1.2.0 |
| Help desk website | — | Reachable and serving. Waiting only on Postmark |
| Inbound mail, Postmark to FreeScout | — | Built and proven. Waiting only on Postmark credentials |
| Report a Bug, every QUILL app | No | Routed through the server, so a build needs no token. Still files a GitHub issue until Postmark lands |
| GLOW feedback to FreeScout | No | Code complete. Waiting on three `HELPDESK_BRIDGE_*` variables |
| GLOW two-way conversations | No | Code complete. Waiting on sections 32 to 36 |

---

## 56. Troubleshooting

### Postmark and the help desk

| Symptom | Cause | Fix |
| --- | --- | --- |
| Inbound silently does nothing | Plan without inbound email | Section 2 |
| Postmark shows **Inbound Error** | Webhook credentials wrong | Re-run `make-credentials.sh`, re-paste the whole URL |
| Webhook returns 401 | Username or password off by a character | Postmark retries ~10 times over several hours, then gives up |
| Webhook returns 403 | Recipient not in `MAILBRIDGE_RECIPIENTS` | 403 stops retries by design. Section 13.1 |
| Every other address at the domain stopped forwarding | The domain's MX was repointed at Postmark | Restore the five `eforward*` records. Section 5 |
| Domain never verifies | Doubled zone suffix, or a wrapped DKIM value | Re-copy from Postmark; use the short Host form |
| Namecheap refuses `pm_bounces` | Underscore | Change the Return-Path hostname in Postmark to `pm-bounces` |
| Mail to a `bits-acb.org` address never arrives | It is Microsoft 365, not forwarding | Section 13.2 |
| Sending from `bits-acb.org` is rejected | Its SPF ends `-all` and does not include Postmark | Merge `include:spf.mtasv.net`, or send via M365 |
| A duplicate conversation appears | Should not happen | The bridge dedups on message id and content hash. Report it |
| FreeScout stops receiving after an update | `APP_KEY` reset | Section 9. Do not undo the `freescout.env` bind mount |
| FreeScout redirects endlessly to `install.php` | Image wrote a DB driver Laravel 5.5 does not define | `~/helpdesk/fix-db-driver.sh` |
| Custom field values vanished | The conversation was moved between mailboxes | FreeScout does not preserve them. Section 12.1 |

### GLOW's own mail

| Symptom | Cause | Fix |
| --- | --- | --- |
| Everything reports "not configured" | `POSTMARK_SERVER_TOKEN` unset | Set it and restart |
| Sends return HTTP 422 | Stream id does not exist | The id is `outbound`, not `transactional` |
| Sends return HTTP 401 | Account token used instead of server token | Use the server's own API token |
| Mail sends but nobody receives it | Domain not verified, or approval not granted | Check Sender Signatures and account approval |
| Mail lands in spam | DKIM or Return-Path missing | Both must show verified |
| Replies never arrive | Inbound webhook URL or secret wrong | **Activity > Inbound** shows the status GLOW returned |
| Webhook shows 503 | `POSTMARK_WEBHOOK_TOKEN` unset | Set it and restart. It fails closed on purpose |
| Webhook shows 403 | Secret mismatch, or source IP not in the allow-list | Compare the URL value with the variable |
| Reply lands on the wrong conversation | Mail client stripped the plus-address and headers | Falls back to the sender's most recent open conversation. Reassign from `/mail/admin` |
| An address stops receiving anything | It is suppressed | `/mail/admin` shows why, and can clear it |

### GLOW tickets into the help desk

| Symptom | Cause | Fix |
| --- | --- | --- |
| No ticket filed, no error | Category not in `HELPDESK_CATEGORIES`, or no address given | Recorded as `skipped`. Nothing is wrong |
| "does not accept mail for ..." | `HELPDESK_SUPPORT_EMAIL` not in `MAILBRIDGE_RECIPIENTS` | Match them |
| "rejected the credentials" | `HELPDESK_BRIDGE_USER`/`PASSWORD` wrong | Re-read from the container |
| "unreachable" | GLOW and the bridge are not on the same Docker network | Both must be on `web_default` |
| Ticket arrives from GLOW, not the person | Something is sending through Postmark instead of the bridge | Check `HELPDESK_BRIDGE_URL` is set |

### The Caddyfile trap on this server

**`sed -i` silently disconnects the Caddyfile from the running Caddy.**

Docker bind-mounts a *single file* by inode. `sed -i` does not edit in place
despite its name — it writes a temporary file and renames it over the target,
producing a **new inode**. The container keeps the old one. From that moment the
host file and the running configuration are two different files, and nothing
says so.

Worse, every check still passes. `caddy validate` reads the host file and says
*Valid configuration*. `caddy reload` re-reads the container's inode — the old
one — and reports success. The edit is confirmed twice and applied never.

Two rules follow:

- **Append with `>>`, rewrite with `>`.** Both keep the inode. To edit,
  transform to a temp file then `cat tmp > Caddyfile`. Never `sed -i`, never
  `mv` a new file over it.
- **Repairing a split needs a container recreate**, because a bind mount can
  only be re-bound that way — and that restarts the Caddy fronting every site on
  the box, so it is a deliberate act, not a reflex.

As of the last note, the host file and the container's copy were made
byte-identical, so the divergence cannot change behaviour and a recreate is a
no-op whenever convenient. **The inodes are still split until that recreate
happens**, so the next person to edit the Caddyfile must do the recreate first
or their change will vanish.

Always back the file up first:

```bash
cp ~/app/web/Caddyfile ~/app/web/Caddyfile.bak.$(date +%Y-%m-%d)
```

A related trap, already fixed: **a bare `redir` shadows every handler in its
Caddy block.** Caddy sorts directives by a fixed order and `redir` ranks above
`handle`, so a redirect written at the foot of a site block runs *first*. Wrap
redirects in `handle { }`.

---

## 57. What changed in the repositories

### GLOW (`s:\code\glow`)

New:

- `web/src/acb_large_print_web/email_threads.py` — conversations, messages, the
  do-not-send list, webhook events, reply-address routing, retention.
- `web/src/acb_large_print_web/routes/postmark.py` — the two webhook routes, the
  participant conversation views, and the staff console.
- `web/src/acb_large_print_web/helpdesk.py` — composes a support ticket as
  RFC-822 and posts it to the mail bridge.
- `web/src/acb_large_print_web/templates/conversations.html`,
  `conversation.html`, `mail_admin.html`, `mail_admin_thread.html`.
- `web/tests/test_email_two_way.py` — 28 tests: the reply path, webhook
  authentication, routing, bounce handling, view scoping.
- `web/tests/test_helpdesk.py` — 18 tests: the `From` header, what opens a
  ticket, the unverified-address notice, the bridge's status codes, and that a
  help desk failure never costs a bug report.

Changed:

- `web/src/acb_large_print_web/email.py` — the message stream is configurable
  and defaults to `outbound` rather than the non-existent `transactional`; the
  30-day nudge moved to the broadcast stream; sends check the do-not-send list
  first and capture the Postmark message id; `send_thread_message()` and
  `conversations_available()` added; the audit report and workshop artifact
  senders accept an optional conversation.
- `web/src/acb_large_print_web/app.py` — registers the blueprint at `/mail`.
- `web/src/acb_large_print_web/routes/workshop.py` — the artifact email opens a
  conversation so a participant can reply.
- `web/src/acb_large_print_web/routes/passport.py` — uses the configurable
  stream; the passport page links to messages.
- `web/src/acb_large_print_web/routes/feedback.py` — files a help desk ticket
  alongside the GitHub issue, recording the outcome in four new columns.
  `_save_feedback_entry` returns a `_SaveResult` rather than a four-tuple.
- `web/src/acb_large_print_web/templates/admin_queue.html`, `passport.html`,
  `workshop/artifact.html`, `feedback_thanks.html`.
- `web/docker-compose.prod.yml` — the new variables, documented in comments.
- `web/tests/test_email.py`, `test_email_layer.py` — two assertions updated from
  `transactional` to `outbound`.

Full suite: 1058 passed, 31 skipped.

### QUILL (`s:\quill`)

- `magic.md` — item 3, the Postmark walkthrough, moved here. The item keeps its
  number and points at this file, so links from earlier notes still land
  somewhere useful. A backup of the original is at
  `zquill_magic_backup_2026-09-11.md` (gitignored, like `magic.md` itself).
- No code changed.

### `s:\helpdesk.md`

- Merged into this file in full. Nothing from it was dropped; the reordering is
  QUILL-first, and section 0.2 records where the plan and the live estate
  disagreed.

### feedback-hub (on the server)

- Nothing changed. `feedback_hub.mailbridge` is used exactly as built.

### One behaviour change worth knowing

The message stream was hardcoded to `transactional`. Postmark's id for the
transactional stream every server is created with is `outbound`; `transactional`
is the stream's *type*, not its id. A send to a stream id that does not exist
returns HTTP 422, which GLOW reported to users as "a validation error, contact
the site administrator". If you had already created a custom stream with the id
`transactional`, set `POSTMARK_MESSAGE_STREAM=transactional` to keep using it.

---

## 58. Routes

### Added to GLOW

| Route | Who | Purpose |
| --- | --- | --- |
| `POST /mail/webhook/inbound` | Postmark | Receives replies |
| `POST /mail/webhook/events` | Postmark | Bounces, complaints, deliveries, subscription changes |
| `GET /mail/conversations` | Participant | Their conversations |
| `GET /mail/conversations/<id>` | Participant | One conversation |
| `POST /mail/conversations/<id>/reply` | Participant | Answer from in-app |
| `POST /mail/conversations/start` | Participant | Start a conversation |
| `GET /mail/admin` | Admin | Conversations, suppressions, events, help desk state |
| `GET /mail/admin/<id>` | Admin | One conversation |
| `POST /mail/admin/<id>/reply` | Admin | Answer a participant |
| `POST /mail/admin/<id>/status` | Admin | Close or reopen |
| `POST /mail/admin/<id>/assign` | Admin | Anchor an unrouted conversation |
| `POST /mail/admin/<id>/delete` | Admin | Delete a conversation |
| `POST /mail/admin/suppressions/clear` | Admin | Allow an address again |
| `POST /mail/admin/purge` | Admin | Apply retention now |
| `GET /mail/admin/health` | Admin | JSON status |

### Existing elsewhere

| Route | Host | Purpose |
| --- | --- | --- |
| `POST /postmark/inbound` | `helpdesk.community-access.org` | The mail bridge |
| `POST /submit/picks` | `lp.csedesigns.com` | The submission server |
| `POST /freescout/github` | not built | GitHub bridge, part three |
| `POST /github/freescout` | not built | GitHub bridge, part three |

---

## 59. Turning it off

Every piece fails soft, so there is no uninstall.

- **Stop GLOW sending:** unset `POSTMARK_SERVER_TOKEN` and restart. Every mail
  feature reports itself unavailable and the on-screen paths still work.
- **Stop GLOW receiving:** unset `POSTMARK_WEBHOOK_TOKEN`. Both webhook routes
  return 503, and Postmark retries for hours before giving up, so do this
  deliberately rather than as a debugging step.
- **Stop offering conversations without stopping mail:** unset
  `POSTMARK_INBOUND_ADDRESS`.
- **Stop filing tickets:** unset `HELPDESK_BRIDGE_URL`. Feedback is still stored
  and still reaches GitHub.
- **Roll back the stream change:** `POSTMARK_MESSAGE_STREAM=transactional`.
- **Stop the help desk entirely:** `cd ~/helpdesk && docker compose down`.
  Nothing else on the box is affected.

Nothing above needs a code change or a redeploy, only an `.env` edit and a
restart. That is deliberate: these are the failure modes you want to be able to
stop at 4pm on a Friday.

---

## 60. What was not done

- **`.env` and `.env.example` are untouched** in GLOW. Section 36.1 is the block
  to paste.
- **Nothing was committed** in either repository.
- **Nothing was sent.** No test email, no ticket into the live FreeScout queue,
  no change of any kind on lp.csedesigns.com — section 55 is the result of
  reading only.
- **No Postmark account, server, domain or DNS record was created.**
- **Audit report delivery is still one-way**, deliberately.
- **Report a Bug still files GitHub issues.**
- **The bundled GitHub token still ships.** Removal is gated on a release
  proving the server path; `magic.md` item 7.
- **No FreeScout module was purchased or installed.**
- **The GitHub bridge does not exist.**

---

## 61. Authoritative references

### FreeScout

- Modules catalogue — <https://freescout.net/modules/>
- Module licensing FAQ — <https://freescout.net/modules-faq/>
- Installation guide —
  <https://github.com/freescout-help-desk/freescout/wiki/Installation-Guide>
- Sending emails —
  <https://github.com/freescout-help-desk/freescout/wiki/Sending-Emails>
- Workflows — <https://freescout.net/module/workflows/>
- API & Webhooks — <https://freescout.net/module/api-webhooks/>
- Tags — <https://freescout.net/module/tags/>
- Custom Fields — <https://freescout.net/module/custom-fields/>
- End-User Portal — <https://freescout.net/module/end-user-portal/>
- Knowledge Base — <https://freescout.net/module/knowledge-base/>
- Reports — <https://freescout.net/module/reports/>
- Custom Folders — <https://freescout.net/module/custom-folders/>
- AI Integration — <https://freescout.net/module/ai-integration/>

### GitHub

- Creating GitHub Apps — <https://docs.github.com/en/apps/creating-github-apps>
- App best practices —
  <https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/best-practices-for-creating-a-github-app>
- Webhooks with Apps —
  <https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/using-webhooks-with-github-apps>

### On the server

- `~/feedback-hub/deploy/README.md` — the submission server runbook
- `~/feedback-hub/deploy/helpdesk/README.md` — the help desk runbook, including
  the full `APP_KEY` and database-driver accounts
- `~/feedback-hub/INTEGRATING.md` — how each app reaches the submission server

---

## 62. Order of operations, condensed

If only one checklist is used, use this one.

### Get mail working (do this first)

1. Sign up for Postmark on a plan that **includes inbound**.
2. Create the server `Community Access Help Desk`; add the domain
   `community-access.org`.
3. Add the DKIM TXT and `pm_bounces` CNAME at Namecheap. Touch nothing else,
   especially not the existing SPF record.
4. Wait for both to show **Verified**.
5. Copy the Postmark inbound address; forward `support@` to it in Namecheap's
   **Email Forwarding**. **Do not change the MX records.**
6. On the server, run `./deploy/helpdesk/make-credentials.sh`; paste the whole
   webhook URL into Postmark's inbound stream.
7. Configure FreeScout's SMTP with the Server API Token in **both** the
   username and password fields.
8. Run all five checks in section 8, in order.
9. Only then tell anybody the address exists.

### Build the help desk

10. Back up FreeScout; confirm the canonical hostname decision.
11. Purchase the recommended modules in one checkout; install in dependency
    order; enable 2FA.
12. Create the five mailboxes, QUILL first. **Add every new address to
    `MAILBRIDGE_RECIPIENTS`**, except the `bits-acb.org` pair, which use IMAP
    direct.
13. Verify each new sending domain in Postmark; merge SPF, never duplicate.
14. Create Teams and permissions; configure Ticket Number.
15. Create tags, custom fields and custom folders.
16. Create the core workflows and saved replies.
17. Configure End-User Portals, knowledge bases and branded redirects.

### Connect GitHub

18. Build the GitHub App with minimum permissions and a webhook secret.
19. Build the GitHub bridge; configure the FreeScout API key and custom webhook.
20. Build the repository mapping and the sanitised issue template.
21. Test end-to-end escalation, duplicate prevention and privacy exclusions.

### GLOW's own mail (independent; any time)

22. Create a second Postmark server, `GLOW production`.
23. Verify `notify.letitglow.app`; add the `inbound.letitglow.app` MX.
24. Generate a webhook secret; set both webhook URLs.
25. Paste the Postmark half of section 36.1 into `.env`; restart; run the checks
    in section 37.

### Tickets from GLOW (any time after step 6)

26. Read the bridge credentials off the server.
27. Paste the `HELPDESK_*` half of section 36.1 into the same `.env`; restart.
28. Submit a bug report at `/feedback` and confirm the ticket appears in
    FreeScout **from your address**, not from GLOW.

### Finish

29. Configure Reports and Satisfaction Ratings.
30. Conduct accessibility acceptance testing.
31. Pilot with a small support team; correct what the pilot finds.
32. Launch.
33. Switch QUILL's Report a Bug from GitHub to FreeScout, on the server only.
34. Once a release has proven that path, retire the bundled token.
35. Review monthly. Expand only when a defined need appears.
