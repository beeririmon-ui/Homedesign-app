/**
 * The design system measured in the browser (S5, 2026-11-07): the written gates of docs/ops/quality-gates-2026-11-02.md
 * that a page can be measured against, on every page type, at 400 and 1280.
 *
 *  - G5.18 fonts: only Frank Ruhl Libre and Assistant are loaded and named first on text
 *  - G5.19 type: letter-spacing 0, inputs at least 16 px, nothing justified; line length (a proposal: recorded)
 *  - G5.20 grid: at least 24 px margins on the phone (the stage and full-bleed pictures excepted)
 *  - G7.7 targets: every control at least 44 × 44 (an inline link in running text is WCAG 2.5.8's exception)
 *  - G5.16 focus: every stop of the Tab order shows a ring
 *  - G5.23 prices: "₪ 1,290" isolated left to right
 *  - G7.8 reflow: 320 px wide without a sideways scroll
 *
 * The magazine pages (the story, the detail pages, the story's shop) must pass; the shop and the room engine are
 * measured and recorded, and move to the magazine grid with §9. The table goes to .generated/system/ (untracked; Playwright clears test-results/ on every run);
 * the evidence step copies it to qa/reports/…/s5/.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { productPath, productSlug } from '@hd/shared/product-url';

type Row = { gate: string; page: string; width: number; ok: boolean; hard: boolean; value: unknown; where?: string[] };
const rows: Row[] = [];
const OUT = resolve(dirname(fileURLToPath(import.meta.url)), '../.generated/system/system-checklist.json');

const MAGAZINE = [
  '/story/',
  '/story/living-room/nordic/',
  '/story/living-room/japandi/',
  `/story/living-room/nordic/p/${productSlug('cushions-cj-boucle-teddy')}/`,
  '/story/checkout/',
  '/story/order/',
  '/story/living-room/warm-modern/tool/',
];
const SHOP = ['/rooms/living-room/', productPath('vase-cj-textured-white-stoneware'), '/cart/', '/checkout/'];

/** what one page measures as, in the page itself */
async function measure(page: Page) {
  return page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const visible = (el: Element) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return (
        r.width > 1 &&
        r.height > 1 &&
        s.visibility !== 'hidden' &&
        s.display !== 'none' &&
        Number(s.opacity) > 0 &&
        !el.closest('[hidden], dialog:not([open]), [aria-hidden="true"]')
      );
    };
    const name = (el: Element) => {
      const id = el.id ? `#${el.id}` : '';
      const cls = typeof el.className === 'string' && el.className ? `.${el.className.trim().split(/\s+/).slice(0, 2).join('.')}` : '';
      return `${el.tagName.toLowerCase()}${id}${cls}`;
    };
    const ownText = (el: Element) => Array.from(el.childNodes).some((n) => n.nodeType === 3 && (n.textContent ?? '').trim().length > 0);
    const texts = Array.from(document.querySelectorAll('body *')).filter((el) => ownText(el) && visible(el) && !el.closest('script, style, noscript, svg'));
    const onStage = (el: Element) => !!el.closest('.mag-stage, .st-td-stage, .stage, .mag-frame, .mag-cover');
    // G5.18
    const ALLOWED = ['Frank Ruhl Libre', 'Assistant'];
    const faces: FontFace[] = [];
    document.fonts.forEach((f) => faces.push(f));
    const loaded = [...new Set(faces.filter((f) => f.status === 'loaded').map((f) => f.family.replace(/["']/g, '')))];
    const firstFamily = texts.filter((el) => !ALLOWED.includes(getComputedStyle(el).fontFamily.split(',')[0]!.replace(/["']/g, '').trim()));
    // G5.19
    const spaced = texts.filter((el) => {
      const ls = getComputedStyle(el).letterSpacing;
      return ls !== 'normal' && parseFloat(ls) !== 0;
    });
    const justified = texts.filter((el) => getComputedStyle(el).textAlign === 'justify');
    const inputs = Array.from(document.querySelectorAll('input:not([type="radio"]):not([type="checkbox"]):not([type="hidden"]), select, textarea')).filter(
      visible,
    );
    const smallInputs = inputs.filter((el) => parseFloat(getComputedStyle(el).fontSize) < 16);
    const cpl = Array.from(document.querySelectorAll('p'))
      .filter((p) => visible(p) && (p.textContent ?? '').trim().length >= 140 && !onStage(p))
      .map((p) => {
        const range = document.createRange();
        range.selectNodeContents(p);
        const tops = new Set(Array.from(range.getClientRects()).map((r) => Math.round(r.top)));
        const lines = Math.max(1, tops.size);
        const len = (p.textContent ?? '').trim().length;
        return { at: name(p), cpl: Math.round(lines > 1 ? len / (lines - 0.5) : len) };
      });
    // G5.20 (the phone): text off the stage keeps 24 px from both edges
    const margins = texts
      .filter((el) => !onStage(el) && !el.closest('.mag-head, .site-header, .mag-live, .sr-only, .live-region, .mag-skip, .skip-link'))
      .map((el) => ({ el, r: el.getBoundingClientRect() }))
      .filter(({ r }) => r.left < 23.5 || r.right > vw - 23.5)
      .map(({ el, r }) => `${name(el)} ${Math.round(r.left)}–${Math.round(r.right)}`);
    // G7.7
    const inline = (el: Element) => {
      const p = el.closest('p, li, dd, td, label, span');
      if (!p || el.tagName !== 'A') return false;
      return (p.textContent ?? '').trim().length > (el.textContent ?? '').trim().length + 2;
    };
    const controls = Array.from(document.querySelectorAll('a[href], button, input, select, textarea, summary, [role="button"]')).filter(
      (el) =>
        visible(el) &&
        !inline(el) &&
        !el.closest('.sr-only, .mag-skip, .skip-link') &&
        !(el.matches('input[type="radio"], input[type="checkbox"]') && el.closest('label')),
    );
    const small = controls
      .map((el) => {
        const box = el.matches('input[type="radio"], input[type="checkbox"]') ? (el.closest('label') ?? el) : el;
        const r = box.getBoundingClientRect();
        return { el, w: r.width, h: r.height };
      })
      .filter((x) => x.w < 43.5 || x.h < 43.5)
      .map((x) => `${name(x.el)} "${(x.el.textContent ?? '').trim().slice(0, 24)}" ${Math.round(x.w)}×${Math.round(x.h)}`);
    // G5.23
    const priced = texts.filter((el) => Array.from(el.childNodes).some((n) => n.nodeType === 3 && (n.textContent ?? '').includes('₪')));
    const loose = priced
      .filter((el) => {
        const t = el.textContent ?? '';
        const isolated = /\u2066₪[\u00a0 ][\d,]+(\.\d\d)?\u2069/.test(t) || !!el.closest('[dir="ltr"]') || getComputedStyle(el).unicodeBidi.includes('isolate');
        return !isolated || !/₪[\u00a0 ]\d{1,3}(,\d{3})*(\.\d\d)?/.test(t);
      })
      .map((el) => `${name(el)} "${(el.textContent ?? '').trim().slice(0, 40)}"`);
    return {
      loaded,
      firstFamily: firstFamily.map(name).slice(0, 10),
      spaced: spaced.map(name).slice(0, 10),
      justified: justified.map(name).slice(0, 10),
      smallInputs: smallInputs.map(name),
      cpl,
      margins: margins.slice(0, 12),
      small: small.slice(0, 16),
      loose: loose.slice(0, 10),
      scroll: document.scrollingElement!.scrollWidth - document.documentElement.clientWidth,
    };
  });
}

/** every Tab stop shows a ring (an outline of at least 2 px, or a ring drawn with box-shadow) */
async function focusRing(page: Page, stops = 30): Promise<string[]> {
  const bad: string[] = [];
  await page
    .locator('body')
    .click({ position: { x: 1, y: 1 } })
    .catch(() => {});
  for (let i = 0; i < stops; i++) {
    await page.keyboard.press('Tab');
    const r = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el || el === document.body) return null;
      const s = getComputedStyle(el);
      const ring = (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 2) || (s.boxShadow !== 'none' && s.boxShadow !== '') || s.borderWidth === '2px';
      return {
        ring,
        at: `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ''}${typeof el.className === 'string' && el.className ? `.${el.className.split(' ')[0]}` : ''}`,
      };
    });
    if (r && !r.ring && !bad.includes(r.at)) bad.push(r.at);
  }
  return bad;
}

async function open(page: Page, url: string): Promise<void> {
  await page.goto(url);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(600);
}

function record(url: string, width: number, m: Awaited<ReturnType<typeof measure>>, ring: string[], hardAll: boolean): void {
  const ALLOWED = ['Frank Ruhl Libre', 'Assistant'];
  const add = (gate: string, ok: boolean, value: unknown, where?: string[], hard = hardAll) =>
    rows.push({ gate, page: url, width, ok, hard, value, ...(where?.length ? { where } : {}) });
  add(
    'G5.18 fonts loaded',
    m.loaded.every((f) => ALLOWED.includes(f)),
    m.loaded,
  );
  add('G5.18 fonts on text', !m.firstFamily.length, m.firstFamily.length, m.firstFamily);
  add('G5.19 letter-spacing 0', !m.spaced.length, m.spaced.length, m.spaced);
  add('G5.19 not justified', !m.justified.length, m.justified.length, m.justified);
  add('G5.19 inputs ≥ 16 px', !m.smallInputs.length, m.smallInputs.length, m.smallInputs);
  const [lo, hi] = width < 720 ? [38, 46] : [52, 68];
  const off = m.cpl.filter((x) => x.cpl < lo - 6 || x.cpl > hi + 4);
  add(
    `G5.19 line length ${lo}–${hi} (proposal)`,
    !off.length,
    m.cpl,
    off.map((x) => `${x.at} ${x.cpl}`),
    false,
  );
  if (width < 720) add('G5.20 margins ≥ 24 px', !m.margins.length, m.margins.length, m.margins);
  add('G7.7 targets ≥ 44 × 44', !m.small.length, m.small.length, m.small);
  add('G5.16 focus ring on every stop', !ring.length, ring.length, ring);
  add('G5.23 price "₪ 1,290", isolated', !m.loose.length, m.loose.length, m.loose);
}

test.describe('the design system, measured (S5)', () => {
  test.afterAll(() => {
    mkdirSync(dirname(OUT), { recursive: true });
    const failed = rows.filter((r) => !r.ok);
    writeFileSync(
      OUT,
      JSON.stringify(
        {
          date: new Date().toISOString().slice(0, 10),
          by: 'frontend-dev, e2e/system.spec.ts',
          gates: 'docs/ops/quality-gates-2026-11-02.md (G5.16, G5.18, G5.19, G5.20, G5.23, G7.7, G7.8)',
          pages: { magazine: MAGAZINE, shop_recorded: SHOP },
          summary: {
            rows: rows.length,
            passed: rows.length - failed.length,
            failed_hard: failed.filter((r) => r.hard).length,
            failed_recorded: failed.filter((r) => !r.hard).length,
          },
          rows,
        },
        null,
        1,
      ),
    );
  });

  for (const width of [400, 1280]) {
    test(`the magazine pages at ${width}`, async ({ page }) => {
      test.setTimeout(240_000);
      await page.setViewportSize({ width, height: width < 720 ? 860 : 800 });
      for (const url of MAGAZINE) {
        if (url === '/story/checkout/') {
          // the checkout with one line in its cart (the empty one is the order page's neighbour)
          await open(page, '/story/living-room/nordic/');
          await page.evaluate(() => window.__story!.openSheet('A-5'));
          await page.getByRole('button', { name: 'הוספה לסל' }).click();
        }
        await open(page, url);
        const m = await measure(page);
        const ring = await focusRing(page);
        record(url, width, m, ring, true);
      }
      const bad = rows.filter((r) => r.width === width && r.hard && !r.ok);
      expect(bad.map((r) => `${r.page} ${r.gate}: ${JSON.stringify(r.where ?? r.value)}`)).toEqual([]);
    });
    test(`the shop and the room engine at ${width}, recorded`, async ({ page }) => {
      test.setTimeout(240_000);
      await page.setViewportSize({ width, height: width < 720 ? 860 : 800 });
      for (const url of SHOP) {
        await open(page, url);
        record(url, width, await measure(page), await focusRing(page, 20), false);
      }
    });
  }

  test('reflow at 320 px: no sideways scroll on any page (WCAG 1.4.10, G7.8)', async ({ page }) => {
    test.setTimeout(240_000);
    await page.setViewportSize({ width: 320, height: 640 });
    for (const url of [...MAGAZINE, ...SHOP]) {
      await open(page, url);
      const m = await measure(page);
      const hard = MAGAZINE.includes(url);
      rows.push({ gate: 'G7.8 reflow at 320 px', page: url, width: 320, ok: m.scroll <= 0, hard, value: m.scroll });
      if (hard) expect(m.scroll, url).toBeLessThanOrEqual(0);
    }
  });
});
