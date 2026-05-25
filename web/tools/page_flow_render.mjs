#!/usr/bin/env node
/*
 Optional rendered-page adapter for PageFlow parity on JS-heavy sites.
 Emits JSON:
 {
   text: string,
   next_candidates: string[]
 }
*/

import { chromium } from '@playwright/test';

function parseArgs(argv) {
  const args = { url: '', timeoutMs: 20000 };
  for (let i = 2; i < argv.length; i += 1) {
    const cur = argv[i];
    if (cur === '--url') {
      args.url = argv[i + 1] || '';
      i += 1;
    } else if (cur === '--timeout-ms') {
      const v = Number(argv[i + 1] || '20000');
      args.timeoutMs = Number.isFinite(v) ? Math.max(5000, v) : 20000;
      i += 1;
    }
  }
  return args;
}

async function run() {
  const { url, timeoutMs } = parseArgs(process.argv);
  if (!url) {
    process.stdout.write(JSON.stringify({ text: '', next_candidates: [] }));
    process.exit(0);
  }

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
    await page.waitForTimeout(1200);

    const result = await page.evaluate(() => {
      const bodyText = (document.body && document.body.innerText) ? document.body.innerText : '';
      const normalize = (s) => (s || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();

      const anchors = Array.from(document.querySelectorAll('a[href]'));
      const nextCandidates = [];

      for (const a of anchors) {
        const href = a.getAttribute('href') || '';
        const text = [
          a.textContent || '',
          a.getAttribute('aria-label') || '',
          a.getAttribute('title') || '',
        ].join(' ').trim().toLowerCase();
        if (!href) continue;
        if (!text) continue;
        if (/\bnext\b|\bcontinue\b|\bmore\b|\bpage\s*2\b|[»›>]+/.test(text)) {
          nextCandidates.push(href);
        }
      }

      return {
        text: normalize(bodyText),
        next_candidates: Array.from(new Set(nextCandidates)).slice(0, 30),
      };
    });

    process.stdout.write(JSON.stringify(result));
    process.exit(0);
  } catch {
    process.stdout.write(JSON.stringify({ text: '', next_candidates: [] }));
    process.exit(0);
  } finally {
    if (browser) {
      await browser.close();
    }
  }
}

run();
