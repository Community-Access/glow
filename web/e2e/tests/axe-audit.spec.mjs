/**
 * axe-audit.spec.mjs — GLOW comprehensive accessibility audit
 *
 * Scans every public route with @axe-core/playwright at WCAG 2.2 AA level.
 * Runs after consent is granted so the real page content is scanned, not
 * just the consent gate.
 *
 * Results are written to artifacts/axe-results.json in the same list format
 * expected by .github/scripts/axe_json_to_sarif.py so the CI SARIF upload
 * step works unchanged.
 *
 * Fail conditions (hard test failure):
 *   - Any critical or serious violation on any page
 *
 * Advisory (warning in output, no failure):
 *   - moderate / minor violations — surfaced in the artifact for review
 */

import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { test, expect } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ARTIFACTS_DIR = path.resolve('e2e/artifacts');

// Flask's instance path for the server Playwright starts. Resolved from this
// file rather than process.cwd() so it holds wherever the suite is invoked.
const E2E_INSTANCE_DIR = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '..',
  'instance',
);

const DEFAULT_AXE_TAGS = [
  'wcag2a',
  'wcag2aa',
  'wcag21a',
  'wcag21aa',
  'wcag22aa',
];

const AXE_TAGS = (process.env.E2E_AXE_TAGS || DEFAULT_AXE_TAGS.join(','))
  .split(',')
  .map((entry) => entry.trim())
  .filter(Boolean);

const AXE_STRICT = process.env.E2E_AXE_STRICT === '1';
const AXE_FAIL_INCOMPLETE = process.env.E2E_AXE_FAIL_INCOMPLETE === '1';

/**
 * Grant consent once for the given page so subsequent navigations within the
 * same browser context skip the gate.
 */
async function ensureConsent(page) {
  const url = page.url();
  if (!url.includes('/consent')) return;

  const agree = page.locator('input[name="agreed"][value="yes"]');
  if (await agree.count()) await agree.check();

  const continueBtn = page.getByRole('button', { name: /Continue to GLOW/i });
  if (await continueBtn.count()) {
    await Promise.all([
      page.waitForURL((u) => !u.pathname.startsWith('/consent'), { timeout: 15_000 }),
      continueBtn.click(),
    ]);
  }
}

/**
 * Create the Workshop Mode session used by the session-scoped audits and save
 * one activity response, so the gallery, personal-content and follow-through
 * pages are scanned with real content in them.
 *
 * Every step is tolerant of Workshop Mode being disabled by feature flag: in
 * that case the routes 404 and the workshop audits simply report the 404 page.
 */
async function completeActivity(page, sessionCode, activityKey, answer) {
  await page.goto(
    `/workshop/session/${encodeURIComponent(sessionCode)}/activity/${activityKey}`,
  );
  await ensureConsent(page);
  const textareas = page.locator('form textarea');
  const count = await textareas.count();
  for (let i = 0; i < count; i += 1) {
    await textareas.nth(i).fill(answer);
  }
  // "Save activity response" finishes the activity; "Save draft" would leave
  // it incomplete, and the champion-skill page only compiles finished work.
  const save = page.getByRole('button', { name: /^Save activity response/i });
  if (await save.count()) {
    await save.click();
    await page.waitForLoadState('networkidle');
  }
}

async function seedWorkshop(page, sessionCode) {
  await page.goto(`/workshop/?code=${encodeURIComponent(sessionCode)}`);
  await ensureConsent(page);

  const nameField = page.locator('#display_name');
  if (await nameField.count()) {
    await nameField.fill('Axe Participant');
    const enter = page.getByRole('button', { name: /Enter workshop/i });
    if (await enter.count()) {
      await enter.click();
      await page.waitForLoadState('networkidle');
    }
  }

  await completeActivity(
    page,
    sessionCode,
    'journey_check_in',
    'Sample workshop response captured for the accessibility audit.',
  );

  // The Champion Studio is what the champion-skill page compiles. Without a
  // finished response that route renders its 404 template and the audit would
  // silently pass against the wrong page.
  await completeActivity(
    page,
    sessionCode,
    'champion_studio',
    'Sample champion workflow captured for the accessibility audit. A human reviews every draft before it is sent.',
  );
}

/**
 * Navigate to *url*, handle consent redirect if needed, then run axe.
 * Returns { url, violations, passes, incomplete } shaped like axe CLI output.
 */
async function auditPage(page, url) {
  await page.goto(url);
  await ensureConsent(page);
  // Wait for the page to settle. Deliberately not 'networkidle': the live
  // gallery and facilitator pages hold a Server-Sent Events connection open
  // for the life of the page, so the network is never idle and the audit
  // would hang until the test timed out. 'load' means stylesheets have
  // arrived, which is what a colour-contrast pass needs; the short wait
  // covers anything the page defers to the next frame.
  await page.waitForLoadState('load');
  await page.waitForTimeout(400);
  const resolvedPath = new URL(page.url()).pathname;

  let builder = new AxeBuilder({ page }).withTags(AXE_TAGS);

  // Exclude hidden script/template stubs that can pollute rule matching.
  // Also exclude the diagnostic raw JSON blob on /status where axe can
  // intermittently report a color-contrast incomplete false positive.
  const excludeSelector = resolvedPath === '/status/'
    ? 'script, template, [hidden], #status-raw-json'
    : 'script, template, [hidden]';
  builder = builder.exclude(excludeSelector);

  if (!AXE_STRICT) {
    // Non-strict mode keeps the historical compatibility profile.
    builder = builder.disableRules([
      'color-contrast',
    ]);
  }

  const results = await builder.analyze();

  return {
    url: page.url(),
    testEnvironment: 'playwright-chromium',
    violations: results.violations,
    passes: results.passes,
    incomplete: results.incomplete,
    inapplicable: results.inapplicable,
  };
}

/**
 * A Site Audit summary.json exercising every branch of the results template:
 * the run-level scanner notice with its collapsed technical detail, a WCAG
 * conformance finding, and a best-practice finding with its "(Best practice)"
 * marker and plain-language guidance. Mirrors the shape written by
 * site_audit.run_site_audit().
 */
function seededRunSummary(runId) {
  const pageUrl = 'https://example.org/projects';
  return {
    run_id: runId,
    started_utc: '2026-01-01T00:00:00Z',
    elapsed_ms: 4200,
    options: {
      max_pages: 10,
      crawl_links: true,
      crawl_depth: 1,
      include_subdomains: false,
      same_path_only: false,
      exclude_url_patterns: [],
      strict_open_source_only: false,
      force: false,
      check_heading_structure: true,
      check_title_quality: true,
    },
    totals: { pages_total: 1, scanned: 1, failed: 0, skipped: 0, findings: 2 },
    cancelled: false,
    notices: [
      {
        id: 'deep-scan-unavailable',
        level: 'warning',
        title: 'Some automated checks could not run',
        message:
          'The deep scanner could not start because of a file-permission problem on the '
          + 'GLOW server. Nothing is wrong with your page. This affected 1 page in this scan.',
        consequence:
          'The checks listed below still ran, but this scan did not include the deeper '
          + 'automated tests (colour contrast, form labels, ARIA, and similar).',
        detail: 'npm ERR! code EACCES npm ERR! syscall mkdir npm ERR! path /app/.npm',
        affected_pages: 1,
      },
    ],
    wcag_rollup: { wcag111: 4, wcag2410: 1 },
    pages: [
      {
        url: pageUrl,
        final_url: pageUrl,
        result: 'ok',
        status_code: 200,
        title: 'Example Projects',
        doc_lang: 'en',
        index: 1,
        finding_count: 2,
        wcag_tags: { wcag111: 4 },
        deep_scan: { ok: false },
        findings: [
          {
            page_url: pageUrl,
            rule_id: 'HEURISTIC-IMG-ALT',
            severity: 'serious',
            message: 'Detected 4 image element(s) missing alt text.',
            location: 'img',
            help_url: '',
            wcag_criteria: ['1.1.1'],
            guidance:
              'Add alt text describing what each image shows. If an image is purely '
              + 'decorative, give it an empty alt="" so screen readers skip it.',
            best_practice: false,
            resources: [
              {
                title: 'W3C Understanding SC 1.1.1',
                url: 'https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html',
                source: 'W3C',
              },
            ],
          },
          {
            page_url: pageUrl,
            rule_id: 'HEURISTIC-HEADING-SPARSE',
            severity: 'moderate',
            message:
              'This page has roughly 960 words of content but only 2 heading(s). A page '
              + 'this size normally needs at least 4 to be skimmed or navigated by section.',
            location: 'body',
            help_url: '',
            wcag_criteria: ['2.4.10'],
            guidance:
              'This page has a lot of content but almost no headings, so there is no way '
              + 'to skim or skip ahead. Add an <h2> at the start of each section.',
            best_practice: true,
            resources: [
              {
                title: 'W3C Tutorial: Headings',
                url: 'https://www.w3.org/WAI/tutorials/page-structure/headings/',
                source: 'W3C',
              },
            ],
          },
        ],
      },
    ],
  };
}

// ---------------------------------------------------------------------------
// Pages to audit
// ---------------------------------------------------------------------------

const STATIC_PAGES = [
  { label: 'home', path: '/' },
  { label: 'audit form', path: '/audit/' },
  { label: 'fix form', path: '/fix/' },
  { label: 'convert form', path: '/convert/' },
  { label: 'template form', path: '/template/' },
  { label: 'speech studio', path: '/speech/' },
  { label: 'braille studio', path: '/braille/' },
  // GLOW's own accessibility scanner. Its results are read by the people least
  // able to work around a broken page, yet these routes were the last tool
  // surface absent from this suite. The results and job pages need a run to
  // exist first, so they are audited in the interactive-states block below.
  { label: 'site audit form', path: '/site-audit/' },
  { label: 'settings', path: '/settings/' },
  { label: 'guidelines', path: '/guidelines/' },
  { label: 'user guide', path: '/guide/' },
  { label: 'about', path: '/about/' },
  { label: 'changelog', path: '/changelog/' },
  { label: 'faq', path: '/faq/' },
  { label: 'rules reference', path: '/rules/' },
  { label: 'feedback', path: '/feedback/' },
  { label: 'privacy policy', path: '/privacy/' },
  { label: 'status', path: '/status/' },
  // The passport page in its no-passport state, which is what most
  // visitors will ever see of it.
  { label: 'passport', path: '/passport/' },
];

// Workshop Mode. These pages are the hands-on surface used to *teach*
// accessibility in conference workshops, so they carry a higher bar than the
// rest of the app -- yet until now they were the only routes absent from this
// suite. Session-scoped pages need a session to exist first; seedWorkshop()
// creates one and saves a response so the gallery and personal pages are
// audited populated rather than in their empty state.
const WORKSHOP_SESSION = process.env.E2E_WORKSHOP_SESSION || 'axe-workshop';

const WORKSHOP_PAGES = [
  { label: 'workshop home', path: '/workshop/' },
  { label: 'workshop guide', path: '/workshop/guide' },
  { label: 'workshop exercises', path: '/workshop/exercises' },
  { label: 'workshop utilization guide', path: '/workshop/utilization' },
  { label: 'workshop activity', path: `/workshop/session/${WORKSHOP_SESSION}/activity/journey_check_in` },
  { label: 'workshop launchpad', path: `/workshop/session/${WORKSHOP_SESSION}/launchpad` },
  { label: 'workshop my content', path: `/workshop/session/${WORKSHOP_SESSION}/me` },
  { label: 'workshop gallery', path: `/workshop/session/${WORKSHOP_SESSION}/gallery` },
  { label: 'workshop follow-through', path: `/workshop/session/${WORKSHOP_SESSION}/follow-through` },
  { label: 'workshop coach mode', path: `/workshop/session/${WORKSHOP_SESSION}/coach` },
  { label: 'workshop review mode', path: `/workshop/session/${WORKSHOP_SESSION}/review` },
  { label: 'workshop share mode', path: `/workshop/session/${WORKSHOP_SESSION}/share` },
  // The Tier 3 door: optional, outside the agenda, and still audited.
  { label: 'workshop optional lab', path: `/workshop/session/${WORKSHOP_SESSION}/activity/lab_run_your_agent` },
  // What people leave with, and what the room sees at the close.
  { label: 'workshop artifact', path: `/workshop/session/${WORKSHOP_SESSION}/artifact` },
  { label: 'workshop commitment wall', path: `/workshop/session/${WORKSHOP_SESSION}/wall` },
  // Badge collection, and the printable room signage with its QR codes.
  { label: 'workshop badges', path: `/workshop/session/${WORKSHOP_SESSION}/badges` },
  { label: 'workshop signage', path: `/workshop/session/${WORKSHOP_SESSION}/signage` },
  // Compiled from the seeded Champion Studio response above: the page that
  // hands each participant their generated agent skill.
  { label: 'workshop champion skill', path: `/workshop/session/${WORKSHOP_SESSION}/champion-skill` },
  // The page a participant lands on when a return link is stale or mistyped.
  // Rendered for any unknown token, so no seeding is needed.
  { label: 'workshop return link refused', path: '/workshop/return/axe-not-a-real-token' },
  // Renders the facilitator unlock prompt for an unauthenticated visitor.
  { label: 'workshop facilitator gate', path: `/workshop/session/${WORKSHOP_SESSION}/facilitator` },
];

const ALL_PAGES = [...STATIC_PAGES, ...WORKSHOP_PAGES];

const AXE_PATH_FILTER = (process.env.E2E_AXE_PATHS || '')
  .split(',')
  .map((entry) => entry.trim())
  .filter(Boolean);

const ACTIVE_PAGES = AXE_PATH_FILTER.length
  ? ALL_PAGES.filter((page) => AXE_PATH_FILTER.includes(page.path))
  : ALL_PAGES;

// ---------------------------------------------------------------------------
// Accumulated results — written to artifact after all tests complete
// ---------------------------------------------------------------------------

const allPageResults = [];

test.afterAll(async () => {
  fs.mkdirSync(ARTIFACTS_DIR, { recursive: true });
  const outPath = path.join(ARTIFACTS_DIR, 'axe-results.json');
  fs.writeFileSync(outPath, JSON.stringify(allPageResults, null, 2), 'utf-8');

  // Emit a human-readable violation summary to stdout for CI log readability
  const blocking = allPageResults.flatMap((r) =>
    r.violations
      .filter((v) => ['critical', 'serious'].includes(v.impact))
      .map((v) => `  [${v.impact}] ${v.id} (${v.nodes.length} node${v.nodes.length === 1 ? '' : 's'}) on ${r.url}`)
  );
  const advisory = allPageResults.flatMap((r) =>
    r.violations
      .filter((v) => ['moderate', 'minor'].includes(v.impact))
      .map((v) => `  [${v.impact}] ${v.id} (${v.nodes.length} node${v.nodes.length === 1 ? '' : 's'}) on ${r.url}`)
  );

  if (blocking.length) {
    console.error('\n=== AXE: BLOCKING violations (critical/serious) ===\n' + blocking.join('\n'));
  }
  if (advisory.length) {
    if (AXE_FAIL_INCOMPLETE) {
      const incompleteBlocking = allPageResults.flatMap((r) =>
        r.incomplete
          .filter((v) => ['critical', 'serious'].includes((v.impact || '').toLowerCase()))
          .map((v) => `  [${v.impact}] ${v.id} (${v.nodes.length} node${v.nodes.length === 1 ? '' : 's'}) on ${r.url}`)
      );
      if (incompleteBlocking.length) {
        console.error('\n=== AXE: BLOCKING incomplete checks (strict mode) ===\n' + incompleteBlocking.join('\n'));
      }
    }

    console.warn('\n=== AXE: Advisory violations (moderate/minor) ===\n' + advisory.join('\n'));
  }
  if (!blocking.length && !advisory.length) {
    console.log('\n=== AXE: No violations found across all pages ===');
  }

  const totalPages = allPageResults.length;
  const totalViolations = allPageResults.reduce((s, r) => s + r.violations.length, 0);
  const totalPasses = allPageResults.reduce((s, r) => s + r.passes.length, 0);
  console.log(`\nAxe summary: ${totalPages} pages, ${totalViolations} violation rule(s), ${totalPasses} passing rule(s)`);
});

// ---------------------------------------------------------------------------
// Test: audit each static page
// ---------------------------------------------------------------------------

test.describe('GLOW axe-core WCAG 2.2 AA audit', () => {
  // Use a single shared browser context so consent is granted once and
  // all subsequent navigations within the suite skip the gate.
  let sharedPage;

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    sharedPage = await context.newPage();
    // Grant consent once by visiting home and accepting
    await sharedPage.goto('/');
    await ensureConsent(sharedPage);
    await seedWorkshop(sharedPage, WORKSHOP_SESSION);
  });

  test.afterAll(async () => {
    await sharedPage?.context().close();
  });

  for (const { label, path: pagePath } of ACTIVE_PAGES) {
    test(`${label} — no critical/serious axe violations`, async () => {
      const result = await auditPage(sharedPage, pagePath);
      allPageResults.push(result);

      const blocking = result.violations.filter((v) =>
        ['critical', 'serious'].includes(v.impact)
      );

      const incompleteBlocking = AXE_FAIL_INCOMPLETE
        ? result.incomplete.filter((v) => ['critical', 'serious'].includes((v.impact || '').toLowerCase()))
        : [];

      if (blocking.length || incompleteBlocking.length) {
        const details = blocking.map((v) => {
          const nodeDetails = v.nodes.slice(0, 3).map((n) =>
            `    selector: ${(n.target || []).join(' > ')}\n    html: ${n.html?.slice(0, 120)}`
          ).join('\n');
          return `[${v.impact}] ${v.id}: ${v.help}\n  ${v.helpUrl}\n${nodeDetails}`;
        });
        const incompleteDetails = incompleteBlocking.map((v) => {
          const nodeDetails = (v.nodes || []).slice(0, 5).map((n) =>
            `    selector: ${(n.target || []).join(' > ')}\n    html: ${n.html?.slice(0, 200)}`
          ).join('\n');
          return `[${v.impact || 'incomplete'}] ${v.id}: ${v.help}\n  ${v.helpUrl}\n${nodeDetails}`;
        });

        throw new Error(
          `${blocking.length} blocking axe violation(s) and ${incompleteBlocking.length} strict incomplete check(s) on ${pagePath}:\n\n` +
          [...details, ...incompleteDetails].join('\n\n')
        );
      }

      // Advisory violations — log but do not fail
      const advisory = result.violations.filter((v) =>
        ['moderate', 'minor'].includes(v.impact)
      );
      if (advisory.length) {
        console.warn(
          `[advisory] ${advisory.length} moderate/minor violation(s) on ${pagePath}: ` +
          advisory.map((v) => v.id).join(', ')
        );
      }
    });
  }
});

// ---------------------------------------------------------------------------
// Test: interactive state — speech studio with engines unavailable
// ---------------------------------------------------------------------------

test.describe('GLOW axe-core — interactive states', () => {
  test('speech studio unavailable banner is accessible', async ({ page }) => {
    await page.goto('/speech/');
    await ensureConsent(page);
    await page.waitForLoadState('networkidle');

    let builder = new AxeBuilder({ page }).withTags(AXE_TAGS);
    if (!AXE_STRICT) builder = builder.disableRules(['color-contrast']);
    const result = await builder.analyze();

    const blocking = result.violations.filter((v) =>
      ['critical', 'serious'].includes(v.impact)
    );
    expect(blocking, `Speech unavailable state has ${blocking.length} blocking violation(s): ${blocking.map((v) => v.id).join(', ')}`).toHaveLength(0);
  });

  test('braille studio unavailable state is accessible', async ({ page }) => {
    await page.goto('/braille/');
    await ensureConsent(page);
    await page.waitForLoadState('networkidle');

    let builder = new AxeBuilder({ page }).withTags(AXE_TAGS);
    if (!AXE_STRICT) builder = builder.disableRules(['color-contrast']);
    const result = await builder.analyze();

    const blocking = result.violations.filter((v) =>
      ['critical', 'serious'].includes(v.impact)
    );
    expect(blocking, `Braille unavailable state has ${blocking.length} blocking violation(s): ${blocking.map((v) => v.id).join(', ')}`).toHaveLength(0);
  });

  test('audit form — help accordions expanded state is accessible', async ({ page }) => {
    await page.goto('/audit/');
    await ensureConsent(page);

    // Expand all help accordions
    const summaries = page.locator('details > summary');
    const count = await summaries.count();
    for (let i = 0; i < count; i++) {
      const detail = summaries.nth(i).locator('..');
      const isOpen = await detail.evaluate((el) => el.open);
      if (!isOpen) await summaries.nth(i).click();
    }
    await page.waitForLoadState('networkidle');

    let builder = new AxeBuilder({ page }).withTags(AXE_TAGS);
    if (!AXE_STRICT) builder = builder.disableRules(['color-contrast']);
    const result = await builder.analyze();

    const blocking = result.violations.filter((v) =>
      ['critical', 'serious'].includes(v.impact)
    );
    expect(blocking, `Audit form (accordions open) has ${blocking.length} blocking violation(s): ${blocking.map((v) => v.id).join(', ')}`).toHaveLength(0);
  });

  // The two Site Audit pages that only exist once a scan has been submitted.
  // Both carry markup no other page has -- the run-level notice banner, the
  // best-practice finding markers, and the live job status region -- so a
  // static sweep of the form alone would leave all of it unaudited.
  //
  // The results page is seeded from disk rather than by running a real scan.
  // The SSRF guard refuses private addresses, so a scan aimed at this test
  // server is always refused: the page renders, but with an empty findings
  // table and no notice, and an audit of it would pass without ever touching
  // the markup this test exists to cover.
  test('site audit results page is accessible (populated)', async ({ page }) => {
    const runId = randomUUID();
    const runDir = path.join(E2E_INSTANCE_DIR, 'site_audit_runs', runId);
    fs.mkdirSync(runDir, { recursive: true });
    fs.writeFileSync(
      path.join(runDir, 'summary.json'),
      JSON.stringify(seededRunSummary(runId), null, 2),
      'utf-8',
    );

    try {
      await page.goto(`/site-audit/runs/${runId}`);
      await ensureConsent(page);
      await expect(page.getByRole('heading', { level: 1, name: /Site Audit Results/i }))
        .toBeVisible({ timeout: 30000 });

      // Guard against a silently empty page: this test is only meaningful if
      // the notice banner and both finding kinds actually rendered.
      await expect(page.getByRole('heading', { level: 2, name: /Some automated checks could not run/i })).toBeVisible();
      await expect(page.getByText('(Best practice)').first()).toBeVisible();
      await expect(page.getByText(/What to do:/).first()).toBeVisible();

      // Expand every disclosure, including the notice's "technical details",
      // so collapsed content is audited rather than skipped as hidden.
      const summaries = page.locator('details > summary');
      const count = await summaries.count();
      for (let i = 0; i < count; i++) {
        const detail = summaries.nth(i).locator('..');
        const isOpen = await detail.evaluate((el) => el.open);
        if (!isOpen) await summaries.nth(i).click();
      }
      await page.waitForLoadState('load');

      let builder = new AxeBuilder({ page }).withTags(AXE_TAGS);
      builder = builder.exclude('script, template, [hidden]');
      if (!AXE_STRICT) builder = builder.disableRules(['color-contrast']);
      const result = await builder.analyze();

      const blocking = result.violations.filter((v) =>
        ['critical', 'serious'].includes(v.impact)
      );
      expect(blocking, `Site audit results page has ${blocking.length} blocking violation(s): ${blocking.map((v) => v.id).join(', ')}`).toHaveLength(0);
    } finally {
      fs.rmSync(runDir, { recursive: true, force: true });
    }
  });

  test('site audit background job page is accessible', async ({ page, baseURL }) => {
    test.setTimeout(120000);

    await page.goto('/site-audit/');
    await ensureConsent(page);

    // Background mode is checked by default, so this is the page most people
    // actually land on after submitting a scan.
    await page.locator('#sources').fill(`${baseURL}/about/`);
    const crawlLinks = page.locator('input[name="crawl_links"]');
    if (await crawlLinks.count()) await crawlLinks.uncheck();
    const runInBackground = page.locator('input[name="run_in_background"]');
    if (await runInBackground.count()) await runInBackground.check();
    await page.locator('#max_pages').fill('1');
    await page.getByRole('button', { name: /Run Site Audit/i }).click();

    // Assert the specific page, not just "a heading": if submission failed we
    // would still be on the form, and this test would pass against the wrong
    // page while reporting the job page as audited.
    await expect(page.getByRole('heading', { level: 1, name: /Site Audit Job Status/i }))
      .toBeVisible({ timeout: 60000 });
    await page.waitForLoadState('load');
    await page.waitForTimeout(400);

    let builder = new AxeBuilder({ page }).withTags(AXE_TAGS);
    builder = builder.exclude('script, template, [hidden]');
    if (!AXE_STRICT) builder = builder.disableRules(['color-contrast']);
    const result = await builder.analyze();

    const blocking = result.violations.filter((v) =>
      ['critical', 'serious'].includes(v.impact)
    );
    expect(blocking, `Site audit job page has ${blocking.length} blocking violation(s): ${blocking.map((v) => v.id).join(', ')}`).toHaveLength(0);
  });

  test('dark mode — no critical/serious violations', async ({ browser }) => {
    // Simulate prefers-color-scheme: dark
    const context = await browser.newContext({
      colorScheme: 'dark',
    });
    const page = await context.newPage();
    await page.goto('/');
    await ensureConsent(page);
    await page.waitForLoadState('networkidle');

    let builder = new AxeBuilder({ page }).withTags(AXE_TAGS);
    if (!AXE_STRICT) builder = builder.disableRules(['color-contrast']);
    const result = await builder.analyze();

    const blocking = result.violations.filter((v) =>
      ['critical', 'serious'].includes(v.impact)
    );
    expect(blocking, `Dark mode home has ${blocking.length} blocking violation(s): ${blocking.map((v) => v.id).join(', ')}`).toHaveLength(0);

    await context.close();
  });

  test('mobile viewport — no critical/serious violations on home', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 375, height: 812 }, // iPhone 14 Pro
      userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
    });
    const page = await context.newPage();
    await page.goto('/');
    await ensureConsent(page);
    await page.waitForLoadState('networkidle');

    let builder = new AxeBuilder({ page }).withTags(AXE_TAGS);
    if (!AXE_STRICT) builder = builder.disableRules(['color-contrast']);
    const result = await builder.analyze();

    const blocking = result.violations.filter((v) =>
      ['critical', 'serious'].includes(v.impact)
    );
    expect(blocking, `Mobile home has ${blocking.length} blocking violation(s): ${blocking.map((v) => v.id).join(', ')}`).toHaveLength(0);

    await context.close();
  });
});
