# Reply to David

Hi David,

Thank you — all three of your points are fixed and live. And your first one did
far more good than you probably realised, so let me start there.

**That error message was never about your page.** It was GLOW's own deep
scanner failing to start, on every page of every scan, since the Site Audit
feature launched in May. The two findings you were seeing — missing alt text
and the missing language tag — were the *only* checks that had ever actually
run. You were getting a fraction of the picture, next to an error you had no
way to act on.

That kind of bug can hide forever, because a scanner reporting *fewer* problems
just looks like a clean page. It surfaced only because you told us a message
was confusing instead of scrolling past it.

---

## What the scan will feel like now

**You'll see a lot more.** The deep scan now actually runs, which adds around
ninety checks you were never getting — colour contrast, form labels, ARIA,
link names, touch target sizes. On the Stow Lions page, a scan that used to
return two findings now returns eleven, including two rated critical: a form
field with no label, and images with no alternative text.

**Errors will read like English, and appear once.** If the scanner ever fails
again, you won't get a technical trace attached to every page. You'll get a
single, plain notice at the top:

> **Some automated checks could not run**
>
> The deep scanner could not start because of a problem on the GLOW server.
> Nothing is wrong with your page.
>
> The checks listed below still ran, but this scan did not include the deeper
> automated tests. Re-run the scan later, or report this to the GLOW
> administrator if it keeps happening.

The technical text still exists for whoever maintains the server, but it's
tucked inside a collapsed "technical details" section, out of your way.

**Headings are now checked** — your suggestion, and it works on exactly the page
you flagged. There's a new **"Check heading structure"** checkbox, on by
default, that catches pages with no headings, missing or repeated heading 1s,
skipped levels, headings that announce nothing, pages with far more content
than headings, and graphics that appear to be doing the visual job of section
headings. That last one is precisely what you described, and it fires on the
projects page.

**Page titles are now checked too.** A second checkbox flags generic titles,
titles that don't describe their page, and — the one that catches that site —
several pages sharing an identical title. Every page we scanned there is called
"Stow Lions Club - Lions e-Clubhouse", so nothing in a tab, bookmark, or
history entry tells them apart. One thing worth knowing: this needs at least
two pages to compare, so let the crawl pick up a few rather than scanning a
single page.

**Nothing will be mislabelled as a legal failure.** You were right that heading
and title quality are best practice rather than strict WCAG requirements, so
they're marked **"(Best practice)"** in the results and in the CSV export. A
conformance report stays a conformance report.

**And every finding now tells you what to do.** Alongside the rule name and
WCAG number, there's a plain-language line — for example: *"Add alt text
describing what each image shows. If an image is purely decorative, give it an
empty alt so screen readers skip it."* The rule number tells a specialist what
happened; that line is meant for everyone else.

---

Please keep sending these. And thank you for talking about GLOW at the Carroll
Center — it genuinely means a lot.

Best regards,
Jeff
