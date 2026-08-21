# The GLOW passport

**Status: shipped 21 August 2026.** Optional at every point. GLOW works
exactly as it always has for anyone who never touches it.

## What it is

One identity for the whole product: an opaque id in a cookie, an optional
email address, a settings blob, and two explicit opt-ins. No password, no
account creation, no sign-up wall. A person saves their settings, gets one
link by email, and opening that link anywhere restores them.

## Why it exists

The people most likely to have carefully tuned a type scale, a contrast mode,
reduced motion and the cognitive-accessibility profile are exactly the people
GLOW is built for. Until now those settings lived in one browser's local
storage and nowhere else, so they evaporated on a phone, on a library
machine, or after a routine cookie clear.

Asking somebody to rebuild their own accessibility configuration on every
device is a small, repeated, avoidable insult. That is the reason this exists;
convenience is a side effect.

## What is stored

| Field | Contents | Default |
|---|---|---|
| `passport_id` | Opaque random id, also the cookie value | Created only on request |
| `email` | Optional, only to send the owner their own link | Empty |
| `display_name` | Whatever name they last gave a workshop | Empty |
| `settings_json` | The preferences blob the browser already keeps | `{}` |
| `notify_enabled` | "Email me when a long job finishes" | Off |
| `history_enabled` | "Remember the documents I audit" | Off |
| timestamps | created, updated, last seen | — |

Two side tables: `passport_links` (hashed single-use tokens) and
`passport_history` (only ever written when `history_enabled` is on, capped at
the 25 most recent entries).

Everything lives in `instance/passport.db`, alongside the other GLOW SQLite
stores.

## Privacy rules, as implemented

- **Nothing is stored for anyone who does not ask.** No passport is created by
  browsing, and a visitor without one has no server-side record at all.
- **History is opt-in, and only opt-in.** Saving settings never switches it
  on. Turning it off deletes what it collected, because a switch that leaves
  the data behind is a lie.
- **Deleting means deleting.** One control removes the passport, the address,
  the history and every outstanding link, and the page then says exactly what
  was deleted rather than claiming success in the abstract.
- **Retention is 90 days from last use, sliding.** A returning visitor resets
  the clock; a passport nobody has used for three months is deleted with
  everything in it. Purging happens opportunistically on save, so retention is
  a behaviour rather than a promise about a cron job somebody has to remember.
- **The address is never displayed to anyone else**, never exported, and never
  written to a log line.
- **Tokens are single use, hashed at rest, and time-boxed** (14 days by
  default). A copy of the database yields no working links.
- **Return links land only on an allow-listed destination**, so a link in an
  email can never be turned into an open redirect.

## How it behaves in the product

**Settings page.** A "Keep these settings" section: an optional address, a
checkbox for the link, and the two opt-ins. If the browser already carries a
passport whose stored settings differ from the local ones, a control appears
offering to apply them — never automatically, because applying settings
changes type size and contrast and doing that underneath somebody mid-task is
precisely what this tool exists to prevent.

**Passport page (`/passport/`).** What is stored, in plain words; the recent
audits if history is on; the link form; and the delete control.

**Workshop Mode.** One passport serves both. Joining a workshop attaches the
participant to the passport this browser carries, and the display name given
there is remembered for next time. Without a passport the column stays NULL
and every workshop surface behaves exactly as before. Gallery anonymity is
untouched: the display name and the share-anonymously choice remain per
session, because "who I am to this room" is a different question from "which
browser is mine".

**Whisperer.** With notifications on, the notification address is prefilled
from the passport instead of being retyped for every job.

**Audit.** With history on, each audit records the filename, score and grade
so a document can be measured against its own past. With history off, nothing
about the document is recorded anywhere server-side.

## Configuration

| Variable | Meaning | Default |
|---|---|---|
| `GLOW_PASSPORT_RETENTION_DAYS` | Days of inactivity before deletion | 90 |
| `GLOW_PASSPORT_LINK_TTL_DAYS` | Lifetime of one emailed link | 14 |
| `POSTMARK_SERVER_TOKEN` | Required only for the emailed link; everything else works without it | unset |

With no Postmark token the passport still works — settings save, the cookie
persists, the page explains that no link can be sent. See `x.md` section 6 for
the Postmark setup path.

## Operations

Check a deployment:

```bash
docker compose -f docker-compose.prod.yml exec -T web python -c \
  "from acb_large_print_web.passport_store import retention_days, link_ttl_days; \
   print('retention', retention_days(), 'link ttl', link_ttl_days())"
```

Purge on demand (normally unnecessary — saves purge opportunistically):

```bash
docker compose -f docker-compose.prod.yml exec -T web python -c \
  "from acb_large_print_web.app import create_app; \
   from acb_large_print_web.passport_store import purge_expired; \
   app=create_app({}); ctx=app.app_context(); ctx.push(); print(purge_expired(), 'deleted')"
```

Back up `instance/passport.db` with the other instance data. Losing it costs
people their saved settings, not their work.

## Support answers

**"I clicked my link and it says already used."** Each link works once. Send
another from the passport page on any device that still has the cookie. The
settings themselves are untouched.

**"I lost my link and my cookie."** If the address is still on file, ask an
administrator to send a fresh link; otherwise the settings are unreachable and
a new passport takes a minute to create. This is deliberate — no password
means no recovery question, and no recovery question means nothing to
compromise.

**"Delete everything about me."** The delete control on `/passport/`, or an
administrator can run `forget_passport(passport_id)`.

## Testing

`web/tests/test_passport.py` — 28 tests covering: nothing stored without a
request; save and restore across devices; single-use, expiry and refusal
wording; the allow-listed destination; history being opt-in, deleted when
switched off and capped; delete reporting what it deleted; retention and its
sliding clock; and the workshop attaching to a passport when one exists while
still working when it does not.
