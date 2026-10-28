// Keyboard-only smoke test for GLOW's core flows.
//
// This is the automated half of the keyboard checks documented in
// docs/accessibility-testing.md (Open Source Accessibility Framework, Testing
// action 2). Every step uses the keyboard: Tab and Shift+Tab to move, Enter and
// Space to act. Nothing is clicked, and no control is filled in by selector.
//
// For each page in a flow it walks the whole tab sequence and checks the five
// things the framework names:
//
// 1. Focusable: every visible link and control in the page is reached by Tab
//    (for a radio group, one radio of the group, which is how the browser does
//    it).
// 2. Invocable: each flow is completed by keyboard -- the file chooser
//    is opened with Space, the form is submitted with Enter, and the result is
//    downloaded with Enter.
// 3. Visible focus: each element reached has a focus style that differs from
//    its unfocused style (an outline, a box shadow, a border, a background or
//    an underline change). This is a style comparison, not a judgement of
//    contrast; docs/accessibility-testing.md keeps a person's check for that.
// 4. Logical order: no positive tabindex, and the tab sequence follows the
//    document (reading) order.
// 5. No trap: the sequence comes back round to its start, and Tab never
//    leaves focus where it was.
//
// What it cannot judge, a person still checks: whether the visual order makes
// sense, whether the focus indicator is easy to see, and whether the task feels
// right to someone who uses a keyboard every day.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, expect } from '@playwright/test';

const uploadDocx = process.env.E2E_UPLOAD_DOCX || path.resolve(
  path.dirname(fileURLToPath(import.meta.url)), '../../../samples/GLOW_Test_2-fixed.docx',
);
if (!fs.existsSync(uploadDocx)) {
  throw new Error(`Document regression fixture is missing: ${uploadDocx}`);
}

// Elements the browser can put in the tab sequence.
const FOCUSABLE = [
  'a[href]', 'area[href]', 'button', 'input:not([type="hidden"])', 'select',
  'textarea', 'summary', 'iframe', 'audio[controls]', 'video[controls]',
  '[contenteditable=""]', '[contenteditable="true"]', '[tabindex]',
].join(',');

// Mark every element that should be reachable, and remember how it looks
// before it has focus, so the walk can compare.
async function inventory(page) {
  return page.evaluate((selector) => {
    const items = [];
    const positiveTabindex = [];
    const all = Array.from(document.querySelectorAll(selector));
    all.forEach((el, domIndex) => {
      el.setAttribute('data-kbd-dom', String(domIndex));
      const tabindexAttr = el.getAttribute('tabindex');
      if (tabindexAttr !== null && Number(tabindexAttr) > 0) {
        positiveTabindex.push(el.outerHTML.slice(0, 120));
      }
      const disabled = el.matches(':disabled') || el.closest('[inert]') !== null;
      const removed = tabindexAttr !== null && Number(tabindexAttr) < 0;
      const visible = el.checkVisibility({ checkVisibilityCSS: true, checkOpacity: false })
        && el.closest('[aria-hidden="true"]') === null;
      const rect = el.getBoundingClientRect();
      const hasBox = rect.width > 0 && rect.height > 0;
      // A <summary> is only interactive as the first summary of its <details>.
      const strayedSummary = el.tagName === 'SUMMARY'
        && !(el.parentElement && el.parentElement.tagName === 'DETAILS');
      if (disabled || removed || !visible || !hasBox || strayedSummary) {
        return;
      }
      const cs = getComputedStyle(el);
      el.setAttribute('data-kbd-rest', JSON.stringify({
        outline: `${cs.outlineStyle} ${cs.outlineWidth} ${cs.outlineColor}`,
        boxShadow: cs.boxShadow,
        border: `${cs.borderTopWidth} ${cs.borderTopColor} ${cs.borderBottomWidth} ${cs.borderBottomColor}`,
        background: cs.backgroundColor,
        textDecoration: cs.textDecorationLine,
      }));
      items.push({
        dom: domIndex,
        radioGroup: el.matches('input[type="radio"]') ? (el.name || `#${domIndex}`) : null,
        label: describe(el),
      });
    });
    return { items, positiveTabindex };

    function describe(el) {
      const name = (el.getAttribute('aria-label') || el.textContent || el.getAttribute('value')
        || el.getAttribute('name') || el.id || '').trim().replace(/\s+/g, ' ').slice(0, 60);
      return `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ''} "${name}"`;
    }
  }, FOCUSABLE);
}

// What has focus now, and does it show it?
async function focusState(page) {
  return page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body || el === document.documentElement) {
      return { kind: 'none' };
    }
    const dom = el.getAttribute('data-kbd-dom');
    const label = `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ''}`;
    const restRaw = el.getAttribute('data-kbd-rest');
    if (dom === null || restRaw === null) {
      // Chromium also stops on scrollable regions; they are allowed.
      return { kind: 'extra', label };
    }
    const rest = JSON.parse(restRaw);
    const cs = getComputedStyle(el);
    const now = {
      outline: `${cs.outlineStyle} ${cs.outlineWidth} ${cs.outlineColor}`,
      boxShadow: cs.boxShadow,
      border: `${cs.borderTopWidth} ${cs.borderTopColor} ${cs.borderBottomWidth} ${cs.borderBottomColor}`,
      background: cs.backgroundColor,
      textDecoration: cs.textDecorationLine,
    };
    const hasOutline = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0;
    const changed = Object.keys(now).some((key) => now[key] !== rest[key]);
    return { kind: 'tracked', dom: Number(dom), label, visibleFocus: hasOutline || changed };
  });
}

// Walk the tab sequence from the top of the page until it comes back round.
async function walkTabSequence(page) {
  // Let late scripts (toasts, enhancements) settle before taking stock.
  await page.waitForLoadState('networkidle');
  const { items, positiveTabindex } = await inventory(page);
  await page.evaluate(() => {
    if (document.activeElement && document.activeElement !== document.body) {
      document.activeElement.blur();
    }
    window.scrollTo(0, 0);
  });
  const limit = items.length * 2 + 40;
  const stops = [];
  let first = null;
  let returned = false;
  let stuckAt = null;
  let previous = null;
  let repeats = 0;
  for (let step = 0; step < limit; step += 1) {
    await page.keyboard.press('Tab');
    const state = await focusState(page);
    if (state.kind === 'tracked') {
      if (first === null) {
        first = state.dom;
      } else if (state.dom === first) {
        returned = true;
        break;
      }
      if (previous !== null && previous === state.dom) {
        // A media element's own controls (play, seek, volume) are separate
        // tab stops inside one element, so a few repeats are expected. Focus
        // that stays put for longer than any built-in control set is a trap.
        repeats += 1;
        if (repeats > 12) {
          stuckAt = state.label;
          break;
        }
        continue;
      }
      repeats = 0;
      previous = state.dom;
      stops.push(state);
    } else if (state.kind === 'none' && first !== null) {
      // Focus left the document (to the browser), which is the end of the
      // sequence; the next Tab should start it again.
      previous = null;
    }
  }
  // An element that disappeared during the walk (a toast that timed out, a
  // message that was replaced) was never there to reach; keep only those that
  // are still on the page and visible.
  const reachedNow = new Set(stops.map((s) => s.dom));
  const gone = await page.evaluate((doms) => doms.filter((dom) => {
    const el = document.querySelector(`[data-kbd-dom="${dom}"]`);
    return !el || !el.isConnected || !el.checkVisibility({ checkVisibilityCSS: true, checkOpacity: false });
  }), items.filter((i) => !reachedNow.has(i.dom)).map((i) => i.dom));
  const stillThere = items.filter((i) => !gone.includes(i.dom));
  return { items: stillThere, positiveTabindex, stops, returned, stuckAt };
}

function assertKeyboardContract(result, where) {
  const { items, positiveTabindex, stops, returned, stuckAt } = result;
  // Recorded in the report so a run is evidence, not just a green tick.
  test.info().annotations.push({
    type: 'keyboard',
    description: `${where}: ${items.length} focusable elements, ${stops.length} tab stops, `
      + `${stops.filter((s) => s.visibleFocus).length} with a visible focus style, `
      + `sequence ${returned ? 'returned to start' : 'did not return'}`,
  });
  expect(items.length, `${where}: found no focusable elements`).toBeGreaterThan(0);

  expect(positiveTabindex, `${where}: positive tabindex reorders focus`).toEqual([]);
  expect(stuckAt, `${where}: Tab did not move focus away from ${stuckAt}`).toBeNull();
  expect(returned, `${where}: the tab sequence never came back to its start (possible keyboard trap)`).toBe(true);

  const reached = new Set(stops.map((s) => s.dom));
  const reachedGroups = new Set(items.filter((i) => i.radioGroup && reached.has(i.dom)).map((i) => i.radioGroup));
  const unreached = items.filter((i) => (i.radioGroup ? !reachedGroups.has(i.radioGroup) : !reached.has(i.dom)));
  expect(unreached.map((i) => i.label), `${where}: not reachable by Tab`).toEqual([]);

  const noIndicator = stops.filter((s) => !s.visibleFocus).map((s) => s.label);
  expect([...new Set(noIndicator)], `${where}: no visible focus style`).toEqual([]);

  const outOfOrder = [];
  for (let i = 1; i < stops.length; i += 1) {
    if (stops[i].dom < stops[i - 1].dom) {
      outOfOrder.push(`${stops[i - 1].label} -> ${stops[i].label}`);
    }
  }
  expect(outOfOrder, `${where}: focus order does not follow reading order`).toEqual([]);
}

// Press Tab until the element matching `selector` has focus.
async function tabTo(page, selector, where) {
  const target = (typeof selector === 'string' ? page.locator(selector) : selector).first();
  await expect(target, `${where}: ${selector} is missing`).toHaveCount(1);
  for (let step = 0; step < 400; step += 1) {
    await page.keyboard.press('Tab');
    if (await target.evaluate((el) => el === document.activeElement)) {
      return;
    }
  }
  throw new Error(`${where}: could not reach ${selector} with Tab`);
}

async function chooseFileByKeyboard(page, where) {
  await tabTo(page, '#document', where);
  // Space and Enter both open a native file input's chooser. Headless
  // Chromium occasionally drops the first key press on a file input, so try
  // each key up to twice before calling it a failure.
  for (const key of ['Space', 'Enter', 'Space', 'Enter']) {
    const [chooser] = await Promise.all([
      page.waitForEvent('filechooser', { timeout: 5000 }).catch(() => null),
      page.keyboard.press(key),
    ]);
    if (chooser) {
      await chooser.setFiles(uploadDocx);
      return;
    }
    await expect(page.locator('#document'), `${where}: focus left the file input`).toBeFocused();
  }
  throw new Error(`${where}: neither Space nor Enter opened the file chooser`);
}

test.describe('GLOW keyboard-only smoke test', () => {
  test('skip link is first and moves focus to the main content', async ({ page }) => {
    await page.goto('/');
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toHaveText(/Skip to main content/i);
    await page.keyboard.press('Enter');
    await expect(page.locator('main#main')).toBeFocused();
  });

  for (const { label, path: route } of [
    { label: 'home', path: '/' },
    { label: 'audit form', path: '/audit/' },
    { label: 'fix form', path: '/fix/' },
    { label: 'convert form', path: '/convert/' },
    { label: 'template form', path: '/template/' },
  ]) {
    test(`${label}: every control reachable, visible focus, logical order, no trap`, async ({ page }) => {
      await page.goto(route);
      assertKeyboardContract(await walkTabSequence(page), label);
    });
  }

  test('audit a document by keyboard alone', async ({ page }) => {
    await page.goto('/audit/');
    await chooseFileByKeyboard(page, 'audit form');
    await tabTo(page, '#submit-btn', 'audit form');
    await page.keyboard.press('Enter');
    await expect(page.getByRole('heading', { level: 1, name: /Audit Report/i })).toBeVisible();
    assertKeyboardContract(await walkTabSequence(page), 'audit report');
  });

  test('fix a document and download it by keyboard alone', async ({ page }) => {
    await page.goto('/fix/');
    await chooseFileByKeyboard(page, 'fix form');
    await tabTo(page, 'form button[type="submit"]:has-text("Fix Document")', 'fix form');
    await page.keyboard.press('Enter');
    await expect(page.getByRole('heading', { level: 1, name: /Fix Results/i })).toBeVisible();
    assertKeyboardContract(await walkTabSequence(page), 'fix results');

    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    const download = page.getByRole('button', { name: /Download/i }).first();
    await tabTo(page, 'main button:has-text("Download")', 'fix results');
    await expect(download).toBeFocused();
    const [file] = await Promise.all([
      page.waitForEvent('download'),
      page.keyboard.press('Enter'),
    ]);
    expect(file.suggestedFilename().toLowerCase()).toMatch(/\.docx$/);
  });

  test('convert a document and download it by keyboard alone', async ({ page }) => {
    await page.goto('/convert/');
    await chooseFileByKeyboard(page, 'convert form');
    await tabTo(page, 'form button[type="submit"]:has-text("Convert My Document")', 'convert form');
    await page.keyboard.press('Enter');
    await expect(page.getByRole('heading', { level: 1, name: 'Conversion Complete' })).toBeVisible();
    assertKeyboardContract(await walkTabSequence(page), 'conversion complete');

    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    await tabTo(page, page.getByRole('link', { name: /^Download .*\.md$/i }), 'conversion complete');
    const [file] = await Promise.all([
      page.waitForEvent('download'),
      page.keyboard.press('Enter'),
    ]);
    expect(file.suggestedFilename().toLowerCase()).toContain('.md');
  });

  test('create a template by keyboard alone', async ({ page }) => {
    await page.goto('/template/');
    await tabTo(page, '#template-submit-btn', 'template form');
    // The template is either downloaded at once or built as a background job,
    // depending on the deployment; both are a completed task.
    const downloadPromise = page.waitForEvent('download', { timeout: 30000 }).catch(() => null);
    const jobPromise = page
      .waitForURL((url) => url.pathname.includes('/job/'), { timeout: 30000 })
      .then(() => true)
      .catch(() => false);
    await page.keyboard.press('Enter');
    const direct = await downloadPromise;
    if (direct) {
      expect(direct.suggestedFilename().toLowerCase()).toContain('.dotx');
      return;
    }
    expect(await jobPromise, 'template form: Enter produced neither a download nor a job page').toBe(true);
    const result = page.getByRole('link', { name: /Download result/i });
    await expect(result).toBeVisible({ timeout: 120000 });
    await page.evaluate(() => document.activeElement && document.activeElement.blur());
    await tabTo(page, result, 'template job page');
    await expect(result).toBeFocused();
  });
});
