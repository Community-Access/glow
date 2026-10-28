// Zoom and reflow check for GLOW's core pages.
//
// The automated half of the zoom and reflow checks in
// docs/accessibility-testing.md (Open Source Accessibility Framework, Testing
// action 4). Two settings, each the layout a browser produces at that zoom:
//
// - 400 percent: a 320 CSS pixel wide viewport, the width WCAG 2.2 success
//   criterion 1.4.10 (Reflow) uses, which is 1280 pixels at 400 percent zoom.
// - 200 percent: a 640 CSS pixel wide viewport, which is 1280 pixels at 200
//   percent zoom.
//
// At each width the page must not scroll sideways, and the page's main
// heading, the primary navigation (through its menu button where the layout
// collapses it) and the form's submit button must still be there and usable.
// Content that WCAG allows to scroll in two dimensions -- data tables and code
// blocks -- may scroll inside its own box; the page itself may not.
//
// What it cannot check, a person still does: real browser zoom and text-only
// resizing, clipped or overlapping text, and whether the reading order still
// makes sense when the layout collapses.

import { test, expect } from '@playwright/test';

const PAGES = [
  { label: 'home', path: '/', submit: null },
  { label: 'audit form', path: '/audit/', submit: /Run Audit/i },
  { label: 'fix form', path: '/fix/', submit: /Fix Document/i },
  { label: 'convert form', path: '/convert/', submit: /Convert My Document/i },
  { label: 'template form', path: '/template/', submit: /Create Template/i },
  { label: 'user guide', path: '/guide/', submit: null },
];

const WIDTHS = [
  { zoom: '400 percent', width: 320, height: 256 },
  { zoom: '200 percent', width: 640, height: 400 },
];

for (const { zoom, width, height } of WIDTHS) {
  test.describe(`GLOW reflow at ${zoom} (${width} CSS pixels)`, () => {
    test.use({ viewport: { width, height } });

    for (const { label, path, submit } of PAGES) {
      test(`${label}: no sideways scrolling, content and controls available`, async ({ page }) => {
        await page.goto(path);

        const overflow = await page.evaluate(() => {
          const root = document.scrollingElement || document.documentElement;
          const excess = root.scrollWidth - root.clientWidth;
          // Name the widest elements that push past the viewport, skipping
          // those inside a box that scrolls on its own (tables, code).
          const culprits = [];
          if (excess > 1) {
            for (const el of document.body.querySelectorAll('*')) {
              const rect = el.getBoundingClientRect();
              if (rect.right <= root.clientWidth + 1 || rect.width === 0) continue;
              let scrollsOnItsOwn = false;
              for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
                const ox = getComputedStyle(p).overflowX;
                if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') { scrollsOnItsOwn = true; break; }
              }
              if (!scrollsOnItsOwn) culprits.push(`${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ''}.${el.className}`.slice(0, 80));
              if (culprits.length >= 5) break;
            }
          }
          return { excess, culprits };
        });
        expect(overflow.excess, `${label} scrolls sideways by ${overflow.excess}px: ${overflow.culprits.join(', ')}`).toBeLessThanOrEqual(1);

        await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();

        const menuButton = page.locator('#sidebar-toggle');
        if (await menuButton.isVisible()) {
          await menuButton.focus();
          await page.keyboard.press('Enter');
          await expect(menuButton).toHaveAttribute('aria-expanded', 'true');
        }
        const nav = page.getByRole('navigation', { name: 'Primary navigation' });
        await expect(nav.getByRole('link').first()).toBeVisible();

        if (submit) {
          if (await menuButton.isVisible()) {
            await page.keyboard.press('Escape');
          }
          const button = page.getByRole('button', { name: submit }).first();
          await button.scrollIntoViewIfNeeded();
          await expect(button).toBeVisible();
          const box = await button.boundingBox();
          expect(box && box.x >= 0 && box.x + box.width <= width + 1, `${label}: submit button is cut off`).toBe(true);
        }
      });
    }
  });
}
