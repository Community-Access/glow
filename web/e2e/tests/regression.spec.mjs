import fs from 'node:fs';
import path from 'node:path';
import { test, expect } from '@playwright/test';

const uploadDocx = process.env.E2E_UPLOAD_DOCX || 'd:/code/test.docx';
const hasUploadDocx = fs.existsSync(uploadDocx);
const uploadAudio = process.env.E2E_UPLOAD_AUDIO || 'S:/code/bw/Samples/ronaldreaganchallengeraddressatt3232.mp3';
const hasUploadAudio = fs.existsSync(uploadAudio);

function skipIfMissingUploadFile() {
  test.skip(
    !hasUploadDocx,
    `Upload regression tests require a DOCX file. Set E2E_UPLOAD_DOCX or place a file at ${uploadDocx}`,
  );
}

function skipIfMissingAudioFile() {
  test.skip(
    !hasUploadAudio,
    `Whisperer regression test requires an audio file. Set E2E_UPLOAD_AUDIO or place a file at ${uploadAudio}`,
  );
}

async function ensureConsent(page) {
  if (!page.url().includes('/consent')) {
    return;
  }

  const agree = page.locator('input[name="agreed"][value="yes"]');
  if (await agree.count()) {
    await agree.check();
  }

  const continueBtn = page.getByRole('button', { name: /Continue to GLOW/i });
  if (await continueBtn.count()) {
    await Promise.all([
      page.waitForURL((url) => !url.pathname.startsWith('/consent'), { timeout: 15000 }),
      continueBtn.click(),
    ]);
  }
}

test.describe('GLOW web regression suite', () => {
  test('home page loads and references WCAG 2.2', async ({ page }) => {
    await page.goto('/');
    await ensureConsent(page);
    await expect(page.getByRole('heading', { level: 1, name: /GLOW/i })).toBeVisible();
    await expect(page.getByText(/WCAG\s*2\.2(?:\s*AA)?/i).first()).toBeVisible();
  });

  test('audit flow uploads docx and returns report', async ({ page }) => {
    skipIfMissingUploadFile();

    await page.goto('/audit/');
    await ensureConsent(page);
    await page.locator('#document').setInputFiles(uploadDocx);
    await page.getByRole('button', { name: /Run Audit/i }).click();

    await expect(page.getByRole('heading', { level: 1, name: /Audit Report/i })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: /Compliance Score/i })).toBeVisible();
  });

  test('fix flow uploads docx and returns fix results', async ({ page }) => {
    skipIfMissingUploadFile();

    await page.goto('/fix/');
    await ensureConsent(page);
    await page.locator('#document').setInputFiles(uploadDocx);

    const detectHeadings = page.locator('#detect-headings');
    if (await detectHeadings.count()) {
      await detectHeadings.uncheck();
    }

    await page.getByRole('button', { name: /Fix Document/i }).click();

    await expect(page.getByRole('heading', { level: 1, name: /Fix Results/i })).toBeVisible();
    await expect(page.getByRole('heading', { level: 2, name: /Before and After/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /Download/i })).toBeVisible();
  });

  test('export-via-convert flow uploads docx and downloads CMS html', async ({ page }) => {
    skipIfMissingUploadFile();

    // Export was folded into Convert in v2.7.0. /export/ now redirects to
    // /convert/ and the format is selected via the "direction" radios.
    await page.goto('/convert/');
    await ensureConsent(page);
    await page.locator('#document').setInputFiles(uploadDocx);

    const cmsRadio = page.locator('input[name="direction"][value="to-html-cms"]');
    if (await cmsRadio.count()) {
      await cmsRadio.check();
    }

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: /Convert My Document/i }).click(),
    ]);

    const suggested = download.suggestedFilename();
    expect(suggested.toLowerCase()).toContain('.html');
  });

  test('convert flow uploads docx and downloads markdown', async ({ page }) => {
    skipIfMissingUploadFile();

    await page.goto('/convert/');
    await ensureConsent(page);
    await page.locator('#document').setInputFiles(uploadDocx);

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: /Convert My Document/i }).click(),
    ]);

    const suggested = download.suggestedFilename();
    expect(suggested.toLowerCase()).toContain('.md');
  });

  test('template flow downloads dotx', async ({ page }) => {
    await page.goto('/template/');
    await ensureConsent(page);

    const downloadPromise = page.waitForEvent('download', { timeout: 30000 }).catch(() => null);
    const jobRedirectPromise = page
      .waitForURL((url) => url.pathname.includes('/job/'), { timeout: 30000 })
      .then(() => true)
      .catch(() => false);

    await page.getByRole('button', { name: /Create Template/i }).click();

    const directDownload = await downloadPromise;
    if (directDownload) {
      const suggested = directDownload.suggestedFilename();
      expect(suggested.toLowerCase()).toContain('.dotx');
      return;
    }

    const onJobPage = await jobRedirectPromise;
    if (onJobPage) {
      await expect(page.getByRole('link', { name: /Download result/i })).toBeVisible({ timeout: 120000 });
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        page.getByRole('link', { name: /Download result/i }).click(),
      ]);
      const suggested = download.suggestedFilename();
      expect(suggested.toLowerCase()).toContain('.dotx');
      return;
    }

    throw new Error('Template flow produced neither direct download nor job progress redirect');
  });

  test('site-audit flow scans local page and renders artifact links', async ({ page, baseURL }) => {
    test.setTimeout(120000);

    await page.goto('/site-audit/');
    await ensureConsent(page);

    const targetUrl = `${baseURL}/about/`;
    await page.locator('#sources').fill(targetUrl);

    const crawlLinks = page.locator('input[name="crawl_links"]');
    if (await crawlLinks.count()) {
      await crawlLinks.uncheck();
    }

    // Keep this flow deterministic for CI: background mode renders a job page,
    // while this regression asserts the final results page and artifact links.
    const runInBackground = page.locator('input[name="run_in_background"]');
    if (await runInBackground.count()) {
      await runInBackground.uncheck();
    }

    await page.locator('#max_pages').fill('1');
    await page.getByRole('button', { name: /Run Site Audit/i }).click();

    await expect(page.getByRole('heading', { level: 1, name: /Site Audit Results/i })).toBeVisible({ timeout: 90000 });
    await expect(page.getByRole('heading', { level: 2, name: /Run Summary/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Download JSON summary/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Download findings CSV/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /Download complete bundle \(ZIP\)/i })).toBeVisible();
  });

  test('static reference pages load', async ({ page }) => {
    const pages = [
      ['/guidelines/', /Guidelines/i],
      ['/guide/', /User Guide/i],
      ['/about/', /About/i],
      ['/changelog/', /Changelog/i],
      ['/feedback/', /Feedback/i],
    ];

    for (const [url, headingPattern] of pages) {
      await page.goto(url);
      await ensureConsent(page);
      await expect(page.locator('h1', { hasText: headingPattern }).first()).toBeVisible();
    }
  });

  test('whisperer flow uploads sample audio and downloads transcript', async ({ page }) => {
    skipIfMissingAudioFile();
    test.setTimeout(16 * 60 * 1000);

    const response = await page.goto('/whisperer/');
    test.skip(response && response.status() === 404, 'Whisperer is gated off in this environment.');

    await ensureConsent(page);
    await expect(page.getByRole('heading', { level: 1, name: /BITS Whisperer/i })).toBeVisible();

    const unavailableBanner = page.getByText(/BITS Whisperer is not available on this server/i);
    test.skip(await unavailableBanner.count(), 'Whisperer is not installed in this test environment.');

    await page.locator('#audio').setInputFiles(uploadAudio);

    // Auto-estimate runs on file selection, but click refresh for explicit regression coverage.
    await page.getByRole('button', { name: /Calculate estimate now/i }).click();
    await expect(page.locator('#estimate-value')).toContainText(/about|under 1 minute/i, {
      timeout: 30000,
    });

    const roughEstimateConfirm = page.locator('#confirm-uncertain-estimate');
    if (await roughEstimateConfirm.count()) {
      const required = await roughEstimateConfirm.evaluate((el) => el.required);
      if (required) {
        await roughEstimateConfirm.check();
      }
    }

    await page.locator('input[name="confirm_estimate"][value="yes"]').check();

    const downloadPromise = page.waitForEvent('download', { timeout: 15 * 60 * 1000 });
    await page.getByRole('button', { name: /Transcribe Audio/i }).click();
    const download = await downloadPromise;

    const suggested = download.suggestedFilename().toLowerCase();
    expect(suggested).toContain('.md');

    const savePath = path.join('artifacts', `whisperer-${Date.now()}.md`);
    await download.saveAs(savePath);
    const content = fs.readFileSync(savePath, 'utf8');
    expect(content.trim().length).toBeGreaterThan(20);
  });
});
