Yes — **have a fallback**, and the fallback I would look at first is **Postmark**, not “OpenMark.”

I searched for **OpenMark** in the transactional email/SMTP context and did not find evidence that it is an email delivery provider. What I did find was **OpenMark AI**, which appears to be about benchmarking AI models, not sending transactional email. So I suspect you may mean **Postmark**.

## My honest recommendation

Use this fallback order:

```text
Plan A: Amazon SES
Best if AWS approves you. Lowest cost, strong infrastructure, good fit if you are already using AWS.

Plan B: Postmark
Best fallback if AWS rejects or delays you. Easier operationally, very strong transactional-email posture, works with SMTP and API.

Plan C: SMTP2GO or Mailgun
Good alternates if Postmark does not fit pricing, policy, or approval needs.
```

For **GLOW / letitglow.app**, Postmark may actually be the cleaner short-term path if Amazon SES becomes a fight.

## Why Postmark makes sense for GLOW

Postmark is specifically positioned around reliable email delivery through both **SMTP and API**, and its own site emphasizes that transactional and promotional messages are routed through separate infrastructure so critical transactional mail is protected from bulk/promotional reputation problems. ([Postmark][1])

That is exactly the story we want for GLOW:

```text
Keycloak identity email:
verification, password resets, required actions

GLOW application email:
feedback confirmations, admin notices, optional job-completion notices

Not included:
newsletters, BITS announcements, convention promotions, fundraising blasts, uploaded files, converted files, reports by email
```

Postmark also supports SMTP, which means it can work with **Keycloak** in the same architectural role SES would have played. Their SMTP setup uses:

```text
Host: smtp.postmarkapp.com
Port: 587
Username: Postmark server or message stream API token
Password: same API token
Encryption: TLS
```

Postmark’s own SMTP guide says to use the transactional message stream’s API token as both the SMTP username and password. ([Postmark][2])

## DNS comparison: SES vs Postmark

With SES, you would configure:

```text
notify.letitglow.app
bounce.notify.letitglow.app
DKIM CNAME records
SPF
DMARC
custom MAIL FROM MX/TXT
```

With Postmark, you would still configure the domain, but the model is a little simpler:

```text
notify.letitglow.app
DKIM TXT record
Return-Path CNAME record
SPF / DMARC as appropriate
```

Postmark’s docs say DKIM records are added as TXT records and Return-Path records are added as CNAME records at your DNS provider, which in your case would be Namecheap. ([Postmark][3])

## Bounce and complaint handling

Postmark is strong here. It supports webhooks for bounces, deliveries, opens, clicks, and spam complaints. ([Postmark][4]) Its bounce webhook sends JSON to your application when Postmark processes a bounce. ([Postmark][5])

So the same GLOW governance model still works:

```text
Postmark webhook
  ↓
GLOW webhook endpoint
  ↓
email_events table
  ↓
email_suppressions table
  ↓
admin dashboard / alerting
```

## Cost difference

SES is usually cheaper at scale. Postmark is more expensive but much easier to operationalize.

Postmark’s current pricing page lists a free developer tier with **100 emails/month**, and paid plans starting at **$15/month for 10,000 emails/month**, with overage pricing after that. ([Postmark][6])

For GLOW’s early transactional use, that is probably acceptable. We are not talking about a large newsletter list; we are talking about identity and system email.

## Where I would not use Postmark

I would not use Postmark to blur the lanes.

Do **not** use it for:

```text
BITS Bytes
ACB convention announcements
general GLOW marketing
fundraising campaigns
imported member lists
bulk community announcements
```

Keep those outside the GLOW transactional infrastructure.

## Updated fallback architecture

```text
Primary path:
Keycloak → Amazon SES SMTP
GLOW → Amazon SES API
DNS: notify.letitglow.app / bounce.notify.letitglow.app

Fallback path:
Keycloak → Postmark SMTP
GLOW → Postmark API
DNS: notify.letitglow.app / Postmark Return-Path
Webhooks: Postmark → GLOW suppression/event processor
```

## My final take

If AWS SES approves you, use SES.

If AWS SES rejects or stalls you, **Postmark is the best fallback I would choose first** for GLOW because it is transactional-first, easy to connect to Keycloak by SMTP, supports API sending for GLOW, has good webhook coverage, and keeps the story clean.

I would not use **OpenMark** unless you mean something different than what I found. For email delivery, the product you probably want is **Postmark**.

[1]: https://postmarkapp.com/?utm_source=chatgpt.com "Postmark: Fast, Reliable Email Delivery Service | SMTP | API"
[2]: https://postmarkapp.com/developer/user-guide/send-email-with-smtp?utm_source=chatgpt.com "Sending email with SMTP"
[3]: https://postmarkapp.com/support/article/resources-for-adding-dkim-and-return-path-records-to-dns-for-common-hosts-and-dns-providers?utm_source=chatgpt.com "Resources for adding DKIM and Return-Path records to ..."
[4]: https://postmarkapp.com/email-webhooks?utm_source=chatgpt.com "Webhooks"
[5]: https://postmarkapp.com/developer/webhooks/bounce-webhook?utm_source=chatgpt.com "Bounce webhook | Postmark Developer Documentation"
[6]: https://postmarkapp.com/pricing?utm_source=chatgpt.com "Postmark Pricing and Free Trial"
