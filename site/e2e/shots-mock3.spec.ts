/**
 * MOCK3, the evidence (qa/reports/2026-11-07-site-track/mock3/screens): the tour at a phone held upright (390×844), a
 * phone on its side (844×390) and a wide screen (1440×900) — the door, the room at rest, zoomed, the close-up with the
 * wheel, and the panel of "המשך הסיור" open; and the temporary switches on the phone.
 * Runs only as `HD_SHOTS_DIR=<dir> npx --no-install playwright test --project=evidence e2e/shots-mock3.spec.ts`, against
 * the local build (npm run preview).
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { test, type Browser, type Page } from '@playwright/test';

const DIR = process.env.HD_SHOTS_DIR ?? '';
test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');
test.describe.configure({ mode: 'serial', timeout: 300_000 });

const SIZES = [
  { name: '390x844-portrait', width: 390, height: 844, dpr: 3, touch: true },
  { name: '844x390-landscape', width: 844, height: 390, dpr: 3, touch: true },
  { name: '1440x900-desktop', width: 1440, height: 900, dpr: 1, touch: false },
] as const;
type Size = (typeof SIZES)[number];
const ready = (page: Page) => page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60_000 });
const atRest = (page: Page, phase: 'door' | 'room' = 'room') =>
  page.waitForFunction((p) => window.__hdTourState?.phase === p && window.__hdTourState.busy === false, phase, { timeout: 120_000 });
const settle = (page: Page, ms = 500) => page.waitForTimeout(ms);
async function shot(page: Page, name: string) {
  mkdirSync(join(DIR, 'screens'), { recursive: true });
  await page.screenshot({ path: join(DIR, 'screens', `${name}.png`) });
}
const open = (browser: Browser, s: Size) =>
  browser.newContext({ locale: 'he-IL', viewport: { width: s.width, height: s.height }, deviceScaleFactor: s.dpr, hasTouch: s.touch, isMobile: s.touch });
/** where the window and everything round it sit, for the README's numbers */
const boxes = (page: Page) =>
  page.evaluate(() => {
    const r = (sel: string) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const b = el.getBoundingClientRect();
      return { x: +b.x.toFixed(1), y: +b.y.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) };
    };
    return { viewport: { w: innerWidth, h: innerHeight }, window: r('.tour-win'), top: r('.tour-top'), strip: r('.tour-strip'), fold: r('#tour-fold'), zoom: r('#tour-zoom') };
  });

for (const s of SIZES) {
  test(`the tour at ${s.name}`, async ({ browser }) => {
    const ctx = await open(browser, s);
    const page = await ctx.newPage();
    await page.goto('/tour/');
    await ready(page);
    await page.waitForFunction(() => window.__hdTour?.warmReady === true, undefined, { timeout: 120_000 });
    await settle(page, 800);
    await shot(page, `${s.name}-1-door`);
    const layout: Record<string, unknown> = { door: await boxes(page) };
    await page.locator('#tour-enter').click();
    await atRest(page);
    await settle(page, 1200);
    await shot(page, `${s.name}-2-room`);
    layout.room = await boxes(page);
    if (s.touch) {
      await page.locator('#tour-zoom').click();
      await atRest(page);
      await settle(page);
      await shot(page, `${s.name}-3-zoomed`);
      await page.locator('#tour-zoom').click();
      await atRest(page);
      await settle(page);
      await page.locator('.tour-tile[data-slot="vase"]').click();
    } else await page.locator('.tour-spot[data-slot="vase"]').click();
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    await settle(page, 700);
    await shot(page, `${s.name}-4-closeup-wheel`);
    await page.keyboard.press('Escape');
    await atRest(page);
    await settle(page);
    await page.locator('#tour-fold').click();
    await settle(page, 900);
    await shot(page, `${s.name}-5-panel`);
    mkdirSync(join(DIR, 'data'), { recursive: true });
    writeFileSync(join(DIR, 'data', `layout-${s.name}.json`), JSON.stringify(layout, null, 1));
    await ctx.close();
  });
}

test('the phone: the temporary switches', async ({ browser }) => {
  const s = SIZES[0];
  for (const [name, query] of [
    ['fill', 'frame=fill'],
    ['dots', 'pick=dots'],
    ['dark', 'bg=dark'],
  ] as const) {
    const ctx = await open(browser, s);
    const page = await ctx.newPage();
    await page.goto(`/tour/?skip=1&${query}`);
    await ready(page);
    await atRest(page);
    await settle(page, 1200);
    await shot(page, `${s.name}-switch-${name}`);
    await ctx.close();
  }
});
