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
import { test, expect } from '@playwright/test';
import { AxeBuilder } from '@axe-core/playwright';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const ARTIFACTS_DIR = path.resolve('e2e/artifacts');

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
  // Wait for the page to settle (no pending network requests, no animation)
  await page.waitForLoadState('networkidle');
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
