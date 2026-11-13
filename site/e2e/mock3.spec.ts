/**
 * MOCK3 (2026-11-13), the owner's feedback FB2 and FB3 (briefs/site-mock3-whole-frame-2026-11-13.md; the designer's
 * spec docs/proposals/tour-whole-frame-phone-2026-11-13.md), behind HD_PUBLIC=0:
 *
 *  1. the whole frame is seen first: at rest the window is 16:9, inside the screen, at the size the spec gives, and the
 *     camera shows the whole picture — a phone upright, a phone on its side, a wide screen;
 *  2. at rest nothing is over the window but the products' marks (bounding boxes), and in the close-up nothing covers it
 *     upright;
 *  3. the zero-counter rule covers the new effects: the panel opening and closing, zoom by the button and by a pinch, a
 *     drag, the wheel entering, the return — no decode, upload, compile, read-back or measurement inside any of them;
 *  4. the folded control: a button with a name and aria-expanded; it opens with the focus on the first room, closes in
 *     the four ways, and the focus comes back to it;
 *  5. the tap rules on the window (the nearest mark; ×2 when two marks are too close; nothing away from them), and a
 *     tile of the strip opens the same close-up as its mark;
 *  6. zoom: the limits, the rubber, the snap, and the return to ×1;
 *  7. on its side the arc sits on the window's bottom edge and the product stays clear of it;
 *  8. the temporary switches that were built, and reduced motion (opacity only);
 *  9. every touch target on the phone is 44 × 44 at least, and axe finds nothing.
 *
 * The numbers go to the evidence when HD_EVIDENCE_DIR is set.
 */
import { test, expect, type Browser, type BrowserContext, type CDPSession, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { ARC, ZOOM, overArc, windowBox, type Layout } from '../web/src/tour/layout';

const note = (name: string, data: unknown) => {
  const dir = process.env.HD_EVIDENCE_DIR;
  if (!dir) return;
  mkdirSync(join(dir, 'data'), { recursive: true });
  writeFileSync(join(dir, 'data', name), JSON.stringify(data, null, 1));
};
const HEADER = 60;
const ready = (page: Page) => page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60_000 });
/** the page is not in a beat, and no effect of the engine's (the page's own included) is running */
const atRest = (page: Page, phase: 'door' | 'room' = 'room') =>
  page.waitForFunction((p) => window.__hdTourState?.phase === p && window.__hdTourState.busy === false && window.__hdTour?.busy === false, phase, {
    timeout: 120_000,
  });
const phone = (browser: Browser, width = 390, height = 844, more: Parameters<Browser['newContext']>[0] = {}) =>
  browser.newContext({ locale: 'he-IL', viewport: { width, height }, deviceScaleFactor: 3, hasTouch: true, isMobile: true, ...more });
async function room(ctx: BrowserContext, query = ''): Promise<Page> {
  const page = await ctx.newPage();
  await page.goto(`/tour/?skip=1${query}`);
  await ready(page);
  await atRest(page);
  return page;
}
const state = (page: Page) =>
  page.evaluate(() => {
    const e = window.__hdTour!;
    return { ...window.__hdTourState!, cam: { ...e.cam }, rest: { ...e.rest }, vp: { ...e.vp } };
  });
const box = (page: Page, sel: string) =>
  page.locator(sel).evaluate((el) => {
    const r = el.getBoundingClientRect();
    return { x: r.x, y: r.y, w: r.width, h: r.height };
  });
/** the marks as the page placed them, in the window's CSS px */
const marks = (page: Page) =>
  page.evaluate(() =>
    Array.from(document.querySelectorAll<HTMLElement>('.tour-spot')).flatMap((el) => {
      const m = /translate\(([-\d.]+)px, ([-\d.]+)px\)/.exec(el.style.transform);
      return m && el.style.visibility !== 'hidden' ? [{ id: el.dataset.slot!, x: Number(m[1]) + 23, y: Number(m[2]) + 23 }] : [];
    }),
  );
/** everything in the tour that is seen and whose box reaches into the window, but the picture and its marks */
const overWindow = (page: Page, also = '') =>
  page.evaluate((extra) => {
    const stage = document.querySelector('.tour')!;
    const win = document.querySelector('.tour-win')!;
    const W = win.getBoundingClientRect();
    const allowed = `canvas, picture, picture *, .tour-portal-line, .tour-rings, .tour-rings *, .tour-spots, .tour-spots *${extra}`;
    const seen = (el: Element): boolean => {
      for (let n: Element | null = el; n && n !== stage.parentElement; n = n.parentElement) {
        const cs = getComputedStyle(n);
        if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) return false;
      }
      return true;
    };
    const out: string[] = [];
    for (const el of Array.from(stage.querySelectorAll('*'))) {
      if (el === win || el.contains(win) || el.matches(allowed) || !seen(el)) continue;
      const b = el.getBoundingClientRect();
      if (!b.width || !b.height) continue;
      const ix = Math.min(b.right, W.right) - Math.max(b.left, W.left);
      const iy = Math.min(b.bottom, W.bottom) - Math.max(b.top, W.top);
      if (ix > 0.5 && iy > 0.5) out.push(`${el.tagName.toLowerCase()}.${String(el.className).split(' ').join('.')} ${Math.round(ix)}×${Math.round(iy)}`);
    }
    return out;
  }, also);
async function audit(page: Page, label: string) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const summary = r.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')} — ${v.help}`);
  expect(summary, `${label}\n${summary.join('\n')}`).toEqual([]);
}
// ---------- fingers ----------
type Pt = { x: number; y: number };
const fingers = (client: CDPSession, type: 'touchStart' | 'touchMove' | 'touchEnd', pts: Pt[]) =>
  client.send('Input.dispatchTouchEvent', { type, touchPoints: pts.map((p, id) => ({ x: Math.round(p.x), y: Math.round(p.y), id })) });
const pair = (c: Pt, d: number): Pt[] => [
  { x: c.x - d / 2, y: c.y },
  { x: c.x + d / 2, y: c.y },
];
/** two fingers from `from` px apart to `to` px apart round `c`; `held` runs while they are still down */
async function pinch(page: Page, client: CDPSession, c: Pt, from: number, to: number, held?: () => Promise<void>) {
  await fingers(client, 'touchStart', pair(c, from));
  for (let i = 1; i <= 12; i++) {
    await fingers(client, 'touchMove', pair(c, from + ((to - from) * i) / 12));
    await page.waitForTimeout(20);
  }
  await page.waitForTimeout(80);
  await held?.();
  await fingers(client, 'touchEnd', []);
}
/** one finger from a to b; `held` runs while it is still down */
async function drag(page: Page, client: CDPSession, a: Pt, b: Pt, held?: () => Promise<void>) {
  await fingers(client, 'touchStart', [a]);
  for (let i = 1; i <= 10; i++) {
    await fingers(client, 'touchMove', [{ x: a.x + ((b.x - a.x) * i) / 10, y: a.y + ((b.y - a.y) * i) / 10 }]);
    await page.waitForTimeout(20);
  }
  await page.waitForTimeout(80);
  await held?.();
  await fingers(client, 'touchEnd', []);
}
const canvasTransform = (page: Page) => page.locator('canvas.room-canvas').evaluate((c) => (c as HTMLElement).style.transform);

test.describe('MOCK3: the whole frame first, and the folded control', () => {
  test.describe.configure({ timeout: 300_000 });

  const SCREENS: { name: string; w: number; h: number; lay: Layout; touch: boolean }[] = [
    { name: 'a phone upright (390×844)', w: 390, h: 844, lay: 'portrait', touch: true },
    { name: 'a small phone upright (360×640)', w: 360, h: 640, lay: 'portrait', touch: true },
    { name: 'a phone on its side (844×390)', w: 844, h: 390, lay: 'rails', touch: true },
    // a tablet falls out of the two layouts: upright it is the phone's (with larger tiles), on its side the wide screen's
    { name: 'a tablet upright (768×1024)', w: 768, h: 1024, lay: 'portrait', touch: true },
    { name: 'a tablet on its side (1024×768)', w: 1024, h: 768, lay: 'desk', touch: true },
    { name: 'a wide screen (1440×900)', w: 1440, h: 900, lay: 'desk', touch: false },
  ];
  for (const s of SCREENS)
    test(`the whole frame is seen first, and only the marks are over it: ${s.name}`, async ({ browser }) => {
      const ctx = s.touch ? await phone(browser, s.w, s.h) : await browser.newContext({ locale: 'he-IL', viewport: { width: s.w, height: s.h } });
      const page = await ctx.newPage();
      await page.goto('/tour/');
      await ready(page);
      await page.waitForFunction(() => window.__hdTour?.warmReady === true, undefined, { timeout: 120_000 });
      const expectWindow = async (label: string) => {
        const w = await box(page, '.tour-win');
        // the stage is the screen under the site's header; on its side there is no header
        const top0 = s.lay === 'rails' ? 0 : HEADER;
        const want = windowBox(s.lay, s.w, s.h - top0);
        expect(w.w / w.h, `${label}: 16:9`).toBeCloseTo(16 / 9, 2);
        expect(Math.abs(w.w - want.w), `${label}: width ${w.w} for ${want.w}`).toBeLessThanOrEqual(1);
        expect(Math.abs(w.h - want.h), `${label}: height ${w.h} for ${want.h}`).toBeLessThanOrEqual(1);
        expect(Math.abs(w.y - top0 - want.top), `${label}: top ${w.y} for ${top0 + want.top}`).toBeLessThanOrEqual(1);
        // whole, on the glass
        expect(w.x, label).toBeGreaterThanOrEqual(-0.5);
        expect(w.y, label).toBeGreaterThanOrEqual(-0.5);
        expect(w.x + w.w, label).toBeLessThanOrEqual(s.w + 0.5);
        expect(w.y + w.h, label).toBeLessThanOrEqual(s.h + 0.5);
        return w;
      };
      const atDoor = await expectWindow('the door');
      // upright nothing is over the window at the door either (a wide screen keeps the door's words on its wall)
      if (s.lay === 'portrait') expect(await overWindow(page), 'the door').toEqual([]);
      await page.locator('#tour-enter').click();
      await atRest(page);
      const w = await expectWindow('the room at rest');
      // the window did not move or change size between the door and the room
      expect(w).toEqual(atDoor);
      const st = await state(page);
      expect(st.lay).toBe(s.lay);
      // the camera shows the whole frame: nothing of it is outside the window
      expect(st.cam).toEqual({ cu: 0.5, cv: 0.5, z: 1 });
      expect(Math.abs(st.vp.w / st.vp.h - 16 / 9)).toBeLessThan(0.02);
      expect(await overWindow(page), 'the room at rest').toEqual([]);
      // every product has its mark, inside the window
      const m = await marks(page);
      expect(m.length).toBe(13);
      for (const k of m) expect(k.x > 0 && k.x < w.w && k.y > 0 && k.y < w.h, `${k.id} is in the window`).toBe(true);
      // the page does not scroll sideways
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      note(`window-${s.w}x${s.h}.json`, { screen: s, window: w, state: st });
      await ctx.close();
    });

  test('the strip fills with the reveal and is the list; a tile opens the same close-up as its mark; the tap rules', async ({ browser }) => {
    const ctx = await phone(browser);
    const page = await ctx.newPage();
    await page.goto('/tour/');
    await ready(page);
    // before the reveal the strip is there and empty: its cell keeps its size
    await expect(page.locator('.tour-tile')).toHaveCount(13);
    await expect(page.locator('.tour-tile[data-on]')).toHaveCount(0);
    const stripBefore = await box(page, '.tour-strip');
    await page.locator('#tour-enter').click();
    await atRest(page);
    await expect(page.locator('.tour-tile[data-on]')).toHaveCount(13);
    expect(await box(page, '.tour-strip')).toEqual(stripBefore);
    await expect(page.locator('.tour-count')).toHaveText(/13 פריטים · \d+% מהחדר/);
    // the list for a screen reader: a list of buttons with a name each; the marks are decoration here
    await expect(page.getByRole('list', { name: 'פריטים בחדר' }).getByRole('button')).toHaveCount(13);
    await expect(page.locator('.tour-tile[data-slot="vase"]')).toHaveAttribute('aria-label', /^אגרטל: .+\. פתיחת 3 גרסאות$/);
    expect(await page.locator('.tour-spots').getAttribute('aria-hidden')).toBe('true');
    // 4.5 tiles show, so the strip says there is more
    const tile = await box(page, '.tour-tile[data-slot="vase"]');
    expect([tile.w, tile.h]).toEqual([72, 108]);
    const win = await box(page, '.tour-win');
    const all = await marks(page);
    const at = (id: string) => all.find((m) => m.id === id)!;
    const others = (id: string) => Math.min(...all.filter((m) => m.id !== id).map((m) => Math.hypot(m.x - at(id).x, m.y - at(id).y)));
    // a mark on its own (the nearest other one is out of reach): a tap 20 px off it opens it
    const lone = all.filter((m) => others(m.id) > 60).sort((a, b) => others(b.id) - others(a.id))[0]!;
    await page.touchscreen.tap(win.x + lone.x + 14, win.y + lone.y + 14);
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    const byMark = await state(page);
    expect(byMark.open).toBe(lone.id);
    // in the close-up nothing covers the window: the wheel is under it, its name over it
    expect(await overWindow(page, ', .picker'), 'the close-up').toEqual([]);
    const arc = await box(page, '.picker .arc');
    expect(arc.y).toBeGreaterThanOrEqual(win.y + win.h - 0.5);
    // a tap in the window outside the product closes it; one on the product does not
    const inFrame = (id: string) =>
      page.evaluate((slot) => {
        const e = window.__hdTour!;
        const b = e.slot(slot).options[e.selection[slot]! - 1]!.box;
        const x = (u: number) => e.vp.w / 2 + (u - e.cam.cu) * e.vp.w * e.cam.z;
        const y = (v: number) => e.vp.h / 2 + (v - e.cam.cv) * ((e.vp.w * 9) / 16) * e.cam.z;
        return { x0: x(b[0]), x1: x(b[1]), y0: y(b[2]), y1: y(b[3]) };
      }, id);
    const pb = await inFrame(lone.id);
    await page.touchscreen.tap(win.x + (pb.x0 + pb.x1) / 2, win.y + (pb.y0 + pb.y1) / 2);
    await page.waitForTimeout(400);
    expect((await state(page)).open).toBe(lone.id);
    const out = pb.x1 < win.w - 12 ? { x: win.w - 6, y: win.h / 2 } : { x: 6, y: win.h / 2 };
    await page.touchscreen.tap(win.x + out.x, win.y + out.y);
    await expect(page.getByRole('dialog')).toBeHidden();
    await atRest(page);
    expect((await state(page)).cam.z).toBe(1);
    // the same product from the strip: the same close-up
    await page.locator(`.tour-tile[data-slot="${lone.id}"]`).tap();
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    const byTile = await state(page);
    expect(byTile.open).toBe(lone.id);
    expect(byTile.cam).toEqual(byMark.cam);
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toBeHidden();
    await atRest(page);
    // the focus is back on the tile
    await expect(page.locator(`.tour-tile[data-slot="${lone.id}"]`)).toBeFocused();
    // a product in the middle of the frame fills 60% of the window in its longer direction (the camera never leaves
    // the frame, so one that reaches the frame's edge fills more)
    await page.locator('.tour-tile[data-slot="vase"]').tap();
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    const vb = await inFrame('vase');
    expect(vb.y0).toBeGreaterThan(0);
    expect(vb.y1).toBeLessThan(win.h);
    await page.keyboard.press('Escape');
    await atRest(page);
    // every product, by the camera its close-up takes: 60% of the window in its longer direction. A small one stops
    // at the engine's ×4 (it fills less), and one that reaches the frame's edge has less air on that side (more).
    const fills = await page.evaluate(() => {
      const e = window.__hdTour!;
      return Object.keys(e.selection).map((id) => {
        const b = e.slot(id).options[e.selection[id]! - 1]!.box;
        const g = [(b[1] - b[0]) / 3, (b[3] - b[2]) / 3];
        const cut = b[0] - g[0]! < 0 || b[1] + g[0]! > 1 || b[2] - g[1]! < 0 || b[3] + g[1]! > 1;
        const cam = e.camFor([Math.max(0, b[0] - g[0]!), Math.min(1, b[1] + g[0]!), Math.max(0, b[2] - g[1]!), Math.min(1, b[3] + g[1]!)], 0);
        return { id, z: +cam.z.toFixed(3), fill: +(Math.max(b[1] - b[0], b[3] - b[2]) * cam.z).toFixed(3), cut };
      });
    });
    note('portrait-closeups.json', fills);
    for (const f of fills) {
      expect(f.z, f.id).toBeLessThanOrEqual(4);
      if (f.z < 3.999 && !f.cut) expect(f.fill, `${f.id} fills 60%`).toBeCloseTo(0.6, 2);
      else if (!f.cut) expect(f.fill, `${f.id} at ×4`).toBeLessThanOrEqual(0.6);
    }
    expect(fills.filter((f) => Math.abs(f.fill - 0.6) < 0.005).length).toBeGreaterThanOrEqual(3);
    // a tap away from every mark does nothing
    const far = { x: win.w - 8, y: 8 };
    expect(Math.min(...all.map((m) => Math.hypot(m.x - far.x, m.y - far.y)))).toBeGreaterThan(28);
    await page.touchscreen.tap(win.x + far.x, win.y + far.y);
    await page.waitForTimeout(400);
    expect(await state(page)).toMatchObject({ open: null, zoomed: false, busy: false });
    // two marks too close to tell apart: a tap between them zooms ×2 to the point, and there they stand apart
    let pairOf: [(typeof all)[number], (typeof all)[number]] | null = null;
    for (const a of all) for (const b of all) if (a.id < b.id && Math.hypot(a.x - b.x, a.y - b.y) < 40) pairOf ??= [a, b];
    expect(pairOf, 'two marks within 40 px of each other at this width').not.toBeNull();
    const [a, b] = pairOf!;
    await page.touchscreen.tap(win.x + (a.x + b.x) / 2, win.y + (a.y + b.y) / 2);
    await page.waitForFunction(() => window.__hdTourState?.zoomed === true);
    await atRest(page);
    const zoomed = await state(page);
    expect(zoomed.open).toBeNull();
    expect(zoomed.cam.z).toBe(ZOOM.step);
    const apart = await marks(page);
    const a2 = apart.find((m) => m.id === a.id)!;
    const b2 = apart.find((m) => m.id === b.id)!;
    expect(Math.hypot(a2.x - b2.x, a2.y - b2.y)).toBeGreaterThan(Math.hypot(a.x - b.x, a.y - b.y) * 1.9);
    // now a tap on one of them opens it, from the zoom it is in
    await page.touchscreen.tap(win.x + a2.x, win.y + a2.y);
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    expect((await state(page)).open).toBe(a.id);
    // and leaving the close-up always goes back to the whole frame
    await page.keyboard.press('Escape');
    await atRest(page);
    expect(await state(page)).toMatchObject({ open: null, zoomed: false, cam: { cu: 0.5, cv: 0.5, z: 1 } });
    note('taps.json', { lone, pair: [a, b], closeup: byMark.cam });
    await ctx.close();
  });

  test('zoom: the button, a pinch and its limits, the rubber, a drag, the snap, and the return to ×1', async ({ browser }) => {
    const ctx = await phone(browser);
    const page = await room(ctx);
    const client = await ctx.newCDPSession(page);
    const win = await box(page, '.tour-win');
    const mid = { x: win.x + win.w / 2, y: win.y + win.h / 2 };
    const zoom = page.locator('#tour-zoom');
    const touchAction = () => page.locator('.tour-win').evaluate((el) => getComputedStyle(el).touchAction);
    // ×1: the page scrolls under a finger; the button says what it will do
    expect(await touchAction()).toBe('pan-y');
    await expect(zoom).toHaveAttribute('aria-label', 'הגדלה');
    const size = await box(page, '#tour-zoom');
    await zoom.tap();
    await page.waitForFunction(() => window.__hdTourState?.zoomed === true);
    await atRest(page);
    expect((await state(page)).cam).toEqual({ cu: 0.5, cv: 0.5, z: ZOOM.step });
    // the same cell and the same size, the other name; the picture is the finger's now
    await expect(zoom).toHaveAttribute('aria-label', 'כל החדר');
    expect(await box(page, '#tour-zoom')).toEqual(size);
    expect(await touchAction()).toBe('none');
    // the window itself did not grow
    expect(await box(page, '.tour-win')).toEqual(win);
    // one finger moves the zoomed picture, to the frame's edge and no further; past it the picture gives 24 px at most
    let held = { cam: { cu: 0, cv: 0, z: 0 }, t: '' };
    await drag(page, client, mid, { x: mid.x + 900, y: mid.y }, async () => {
      held = { cam: (await state(page)).cam, t: await canvasTransform(page) };
    });
    expect(held.cam.z).toBe(ZOOM.step);
    expect(held.cam.cu).toBeCloseTo(0.25, 5);
    const shift = /translate\(([-\d.]+)px/.exec(held.t);
    expect(shift, `the rubber: ${held.t}`).not.toBeNull();
    expect(Number(shift![1])).toBeGreaterThan(0);
    expect(Number(shift![1])).toBeLessThanOrEqual(ZOOM.over);
    await atRest(page);
    expect(await canvasTransform(page)).toBe('');
    expect((await state(page)).cam.cu).toBeCloseTo(0.25, 5);
    // the marks are placed again where the picture rests
    const m = await marks(page);
    expect(m.length).toBeGreaterThan(0);
    expect(m.length).toBeLessThan(13);
    // "כל החדר": back to the whole frame
    await zoom.tap();
    await page.waitForFunction(() => window.__hdTourState?.zoomed === false);
    await atRest(page);
    expect((await state(page)).cam).toEqual({ cu: 0.5, cv: 0.5, z: 1 });
    expect(await touchAction()).toBe('pan-y');
    // a pinch far past the limit: the camera stops at ×2.5, the picture stretches to ×2.75 in all and no more
    await pinch(page, client, mid, 50, 400, async () => {
      held = { cam: (await state(page)).cam, t: await canvasTransform(page) };
    });
    expect(held.cam.z).toBe(ZOOM.max);
    const stretch = Number(/scale\(([\d.]+)\)/.exec(held.t)?.[1]);
    expect(stretch).toBeGreaterThan(1);
    expect(held.cam.z * stretch).toBeLessThanOrEqual(ZOOM.rubber + 1e-6);
    await atRest(page);
    expect((await state(page)).cam.z).toBe(ZOOM.max);
    expect(await canvasTransform(page)).toBe('');
    expect((await state(page)).zoomed).toBe(true);
    // a pinch out past ×1: the camera never shows less than the frame, and the room is back whole
    await pinch(page, client, mid, 300, 40, async () => {
      held = { cam: (await state(page)).cam, t: await canvasTransform(page) };
    });
    expect(held.cam.z).toBe(1);
    await atRest(page);
    expect(await state(page)).toMatchObject({ zoomed: false, cam: { cu: 0.5, cv: 0.5, z: 1 } });
    // a pinch that ends just over the whole frame (under ×1.15) goes back to it
    await pinch(page, client, mid, 200, 220);
    await page.waitForTimeout(200);
    await atRest(page);
    expect(await state(page)).toMatchObject({ zoomed: false, cam: { cu: 0.5, cv: 0.5, z: 1 } });
    // a pinch to about ×1.6 stays where it was left, round the point between the fingers
    const off = { x: win.x + win.w * 0.75, y: win.y + win.h * 0.6 };
    await pinch(page, client, off, 100, 160);
    await atRest(page);
    const kept = await state(page);
    expect(kept.cam.z).toBeCloseTo(1.6, 1);
    expect(kept.cam.cu).toBeGreaterThan(0.5);
    // a room or a style button first goes back to the whole frame
    await page.locator('#tour-fold').tap();
    await page.waitForFunction(() => window.__hdTourState?.more === true);
    await page.locator('.tour-style button[data-house="nordic"]').tap();
    await expect.poll(() => page.evaluate(() => window.__hdTourState?.house), { timeout: 60_000 }).toBe('nordic');
    await atRest(page);
    expect(await state(page)).toMatchObject({ zoomed: false, more: false, cam: { cu: 0.5, cv: 0.5, z: 1 } });
    const ran = await page.evaluate(() => window.__hdTourFx!.metrics.order);
    expect(ran).toEqual(expect.arrayContaining(['zoom', 'drag', 'pinch', 'zoom-back', 'panel-open', 'panel-close']));
    // the house's name beside the window changed with it, and the strip says the room has no products of its own
    await expect(page.locator('.tour-top')).toHaveAttribute('data-eye', 'nordic');
    await expect(page.locator('.tour-none')).toBeVisible();
    await ctx.close();
  });

  test('the folded control: a named button; it opens, closes in the four ways, and the focus comes back', async ({ browser }) => {
    const ctx = await phone(browser);
    const page = await room(ctx);
    const client = await ctx.newCDPSession(page);
    const fold = page.locator('#tour-fold');
    const panel = page.locator('#tour-more');
    const isOpen = async (open: boolean) => {
      await page.waitForFunction((o) => window.__hdTourState?.more === o && window.__hdTour?.busy === false, open);
      await expect(fold).toHaveAttribute('aria-expanded', String(open));
      expect(await panel.evaluate((el) => (el as HTMLElement).inert)).toBe(!open);
      if (open) await expect(panel).toBeVisible();
      else await expect(panel).toBeHidden();
    };
    await expect(page.getByRole('button', { name: 'המשך הסיור' })).toHaveCount(1);
    await expect(fold).toHaveAttribute('aria-controls', 'tour-more');
    await expect(page.getByRole('region', { name: 'המשך הסיור' })).toHaveCount(0);
    await isOpen(false);
    const foldBox = await box(page, '#tour-fold');
    expect(foldBox.h).toBe(56);
    expect(foldBox.w).toBeGreaterThanOrEqual(132);
    const win = await box(page, '.tour-win');
    const opened = async () => {
      await fold.tap();
      await isOpen(true);
      // the focus moves in, to the first room
      await expect(page.locator('#tour-out')).toBeFocused();
    };
    // 1. "סגירה"
    await opened();
    await expect(page.getByRole('region', { name: 'המשך הסיור' })).toBeVisible();
    // it rises over the strip and never over the window
    const p = await box(page, '#tour-more');
    expect(p.y).toBeGreaterThanOrEqual(win.y + win.h - 0.5);
    expect(p.w).toBe(390);
    // its order: the rooms, the style, "קנה את המראה", and the temporary switches last and closed
    const order = await panel.evaluate((el) => Array.from(el.children).map((c) => c.className.split(' ')[0]));
    expect(order).toEqual(['tour-more-head', 'tour-rooms', 'tour-style', 'tour-links', 'tour-panel']);
    expect(await page.locator('.tour-panel').evaluate((d) => (d as HTMLDetailsElement).open)).toBe(false);
    await expect(page.locator('.tour-rooms button')).toHaveText([/כניסה/, /סלון/, /פינת אוכל.*בקרוב/, /חדר שינה.*בקרוב/]);
    await expect(page.locator('#tour-living')).toHaveAttribute('aria-current', 'true');
    await expect(page.locator('#tour-copy')).toHaveCount(1);
    await audit(page, 'the panel open');
    await page.locator('.tour-more-x').tap();
    await isOpen(false);
    await expect(fold).toBeFocused();
    // 2. Escape
    await opened();
    await page.keyboard.press('Escape');
    await isOpen(false);
    await expect(fold).toBeFocused();
    // 3. a tap outside it: swallowed — it closes the panel and opens no product (the tap is on a mark)
    await opened();
    const m = (await marks(page)).find((k) => k.id === 'pendant')!;
    await page.touchscreen.tap(win.x + m.x, win.y + m.y);
    await isOpen(false);
    await page.waitForTimeout(300);
    expect((await state(page)).open).toBeNull();
    await expect(fold).toBeFocused();
    // 4. a swipe down of 48 px or more, on the panel
    await opened();
    const head = await box(page, '.tour-more-head');
    await drag(page, client, { x: head.x + head.w / 2, y: head.y + 12 }, { x: head.x + head.w / 2, y: head.y + 12 + 70 });
    await isOpen(false);
    await expect(fold).toBeFocused();
    // a short one does not close it
    await opened();
    await drag(page, client, { x: head.x + head.w / 2, y: head.y + 12 }, { x: head.x + head.w / 2, y: head.y + 12 + 10 });
    await page.waitForTimeout(400);
    await isOpen(true);
    // a choice closes it first, and then acts
    await page.locator('#tour-out').tap();
    await isOpen(false);
    await atRest(page, 'door');
    await expect(page.locator('#tour-enter')).toBeVisible();
    // the control is there at the door as well, and the living room's button walks in
    await opened();
    await expect(page.locator('#tour-out')).toHaveAttribute('aria-current', 'true');
    await page.locator('#tour-living').tap();
    await atRest(page);
    await isOpen(false);
    await ctx.close();
  });

  test('nothing interrupts the new effects either (a phone, CPU ×4): the panel, zoom, a pinch, a drag, the wheel, the return', async ({ browser }) => {
    const ctx = await phone(browser, 412, 915, { deviceScaleFactor: 2.625 });
    const page = await ctx.newPage();
    const client = await ctx.newCDPSession(page);
    await client.send('Emulation.setCPUThrottlingRate', { rate: 4 });
    await page.goto('/tour/');
    await ready(page);
    await page.waitForFunction(() => window.__hdTour?.warmReady === true, undefined, { timeout: 180_000 });
    await page.locator('#tour-enter').tap();
    await atRest(page);
    // the way in and the reveal, with the strip filling inside it, as the visitor gets them
    const first = await page.evaluate(() => window.__hdTourFx!.metrics.order.map((l) => window.__hdTourFx!.metrics.effects[l]!));
    // everything the visitor may ask for next is loaded before the rest is measured (it loads between effects, one at
    // a time; here it is simply waited for, so that no load is still in flight when an effect starts)
    await page.evaluate(async () => {
      const e = window.__hdTour!;
      await e.otherHouse();
      for (const id of Object.keys(e.selection)) for (const o of e.slot(id).options) await e.option(id, o.position);
    });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2500);
    await atRest(page);
    await page.evaluate(() => window.__hdTourFx!.metrics.reset());
    const win = await box(page, '.tour-win');
    const mid = { x: win.x + win.w / 2, y: win.y + win.h / 2 };
    const more = async (on: boolean) => {
      await page.waitForFunction((o) => window.__hdTourState?.more === o && window.__hdTour?.busy === false, on);
      await page.waitForTimeout(150);
    };
    // the panel
    await page.locator('#tour-fold').tap();
    await more(true);
    await page.locator('.tour-more-x').tap();
    await more(false);
    // zoom by the button, a drag, and back; then by a pinch, and back
    await page.locator('#tour-zoom').tap();
    await page.waitForFunction(() => window.__hdTourState?.zoomed === true);
    await atRest(page);
    await drag(page, client, mid, { x: mid.x - 60, y: mid.y + 20 });
    await atRest(page);
    await page.locator('#tour-zoom').tap();
    await page.waitForFunction(() => window.__hdTourState?.zoomed === false);
    await atRest(page);
    await pinch(page, client, mid, 80, 170);
    await atRest(page);
    await page.locator('#tour-zoom').tap();
    await page.waitForFunction(() => window.__hdTourState?.zoomed === false);
    await atRest(page);
    // a product from the strip: the wheel enters; an option; "בחירה": the return
    await page.locator('.tour-tile[data-slot="vase"]').tap();
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    await page.keyboard.press('ArrowLeft');
    await expect.poll(() => page.evaluate(() => window.__hdTour!.selection['vase'])).toBe(2);
    await atRest(page);
    await page.locator('.picker .btn-primary').tap();
    await expect(page.getByRole('dialog')).toBeHidden();
    await atRest(page);
    await page.waitForTimeout(400);
    // a style from the panel, and back: the strip is gathered and comes up again with the short reveal
    for (const h of ['nordic', 'warm-modern']) {
      await page.locator('#tour-fold').tap();
      await more(true);
      await page.locator(`.tour-style button[data-house="${h}"]`).tap();
      await expect.poll(() => page.evaluate(() => window.__hdTourState?.house), { timeout: 60_000 }).toBe(h);
      await atRest(page);
      await page.waitForTimeout(300);
    }
    await expect(page.locator('.tour-tile[data-on]')).toHaveCount(13);
    const stats = await page.evaluate(() => window.__hdTourFx!.metrics.order.map((l) => window.__hdTourFx!.metrics.effects[l]!));
    note('counters-mock3.json', { first, stats });
    const labels = stats.map((s) => s.label);
    for (const l of [
      'panel-open',
      'panel-close',
      'zoom',
      'drag',
      'zoom-back',
      'pinch',
      'zoom-in',
      'wheel-in',
      'swap-s1',
      'zoom-out',
      'closeup-out',
      'collect',
      'style-y1',
      'reveal-b',
    ])
      expect(labels, `${l} ran`).toContain(l);
    const interrupted = [...first, ...stats]
      .filter((s) => s.counts.decode + s.counts.upload + s.counts.compile + s.counts.readback + s.counts.layout > 0)
      .map((s) => `${s.label}: ${JSON.stringify(s.counts)}`);
    expect(interrupted, interrupted.join('\n')).toEqual([]);
    // the script time of a frame, as in MOCK2: 4 ms on average, and one frame at the most over 8 ms
    const slow = stats
      .filter((s) => s.frames > 2 && (s.step_mean > 4 || s.step_over8 > 1))
      .map((s) => `${s.label}: mean ${s.step_mean} ms, ${s.step_over8} frames over 8 ms (worst ${s.step_max} ms)`);
    expect(slow, slow.join('\n')).toEqual([]);
    await ctx.close();
  });

  test('on its side: two rails, the arc on the window’s bottom edge, the product clear of it, the panel from the start side', async ({ browser }) => {
    const ctx = await phone(browser, 844, 390);
    const page = await room(ctx);
    const win = await box(page, '.tour-win');
    // the site's header is not shown here; the rails are 88 each
    await expect(page.locator('.site-header')).toBeHidden();
    expect(Math.round(win.x)).toBe(88);
    expect(Math.round(844 - win.x - win.w)).toBe(88);
    // the start rail (the right): the house and the room, and the folded square; the end rail: the counter, the strip, the zoom
    const top = await box(page, '.tour-top');
    const fold = await box(page, '#tour-fold');
    const strip = await box(page, '.tour-strip');
    const zoom = await box(page, '#tour-zoom');
    expect(top.x).toBeGreaterThanOrEqual(win.x + win.w - 0.5);
    expect(fold.x).toBeGreaterThanOrEqual(win.x + win.w - 0.5);
    expect([fold.w, fold.h]).toEqual([72, 72]);
    await expect(page.locator('#tour-fold .short')).toBeVisible();
    expect(strip.x + strip.w).toBeLessThanOrEqual(win.x + 0.5);
    expect(zoom.x + zoom.w).toBeLessThanOrEqual(win.x + 0.5);
    expect((await page.locator('.tour-count').innerText()).trim()).toBe('13 פריטים');
    const tile = await box(page, '.tour-tile[data-slot="vase"]');
    expect([tile.w, tile.h]).toEqual([64, 64]);
    // the close-up: the arc on the bottom 128 px of the window; the product's box 16 px clear of it at the least
    await page.locator('.tour-tile[data-slot="vase"]').tap();
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    const arc = await box(page, '.picker .arc');
    const name = await box(page, '.picker .name');
    expect(Math.round(win.y + win.h - arc.y)).toBe(128);
    expect(name.y + name.h).toBeLessThanOrEqual(win.y + win.h + 0.5);
    // every product, by the camera its close-up takes here: a third of the product's size round it, 38% of the window
    // kept free under it, and then lifted over the arc where the frame allows (tour/layout.ts overArc)
    const framed = await page.evaluate(() => {
      const e = window.__hdTour!;
      return {
        vp: { ...e.vp },
        open: { id: window.__hdTourState!.open, cam: { ...e.cam } },
        slots: Object.keys(e.selection).map((id) => {
          const b = e.slot(id).options[e.selection[id]! - 1]!.box;
          const g = [(b[1] - b[0]) / 3, (b[3] - b[2]) / 3];
          return { id, b, cam: e.camFor([Math.max(0, b[0] - g[0]!), Math.min(1, b[1] + g[0]!), Math.max(0, b[2] - g[1]!), Math.min(1, b[3] + g[1]!)], 0.38) };
        }),
      };
    });
    const fh = (framed.vp.w * 9) / 16;
    const limit = framed.vp.h - ARC.h - ARC.clear;
    expect(Math.abs(arc.y - win.y - (framed.vp.h - ARC.h))).toBeLessThanOrEqual(1);
    const clear = framed.slots.map((x) => {
      const cam = overArc(x.cam, x.b, framed.vp, 16 / 9);
      const y = (v: number) => framed.vp.h / 2 + (v - cam.cv) * fh * cam.z;
      return {
        id: x.id,
        z: +cam.z.toFixed(3),
        top: +y(x.b[2]).toFixed(1),
        bottom: +y(x.b[3]).toFixed(1),
        frame_bottom: +x.b[3].toFixed(3),
        lifted: cam !== x.cam,
        cam,
      };
    });
    // a product that reaches the bottom of the frame cannot be lifted over the arc without showing what is under the
    // frame; the camera stays in the frame, and the README lists these for the designer
    const under = clear.filter((c) => c.bottom > limit + 0.5);
    note('landscape-closeups.json', {
      arc_top: framed.vp.h - ARC.h,
      limit,
      products: clear.map(({ cam: _c, ...r }) => r),
      under_the_arc: under.map((c) => c.id),
    });
    for (const c of clear) {
      expect(c.top, `${c.id}: its top is in the window`).toBeGreaterThanOrEqual(-0.5);
      if (c.frame_bottom < 0.8) expect(c.bottom, `${c.id} is clear of the arc`).toBeLessThanOrEqual(limit + 0.5);
    }
    expect(under.length, under.map((c) => c.id).join(', ')).toBeLessThanOrEqual(5);
    // and the close-up that is open is that camera
    expect(framed.open.id).toBe('vase');
    const mine = clear.find((c) => c.id === 'vase')!;
    expect(framed.open.cam.z).toBeCloseTo(mine.cam.z, 6);
    expect(framed.open.cam.cv).toBeCloseTo(mine.cam.cv, 6);
    expect(mine.bottom).toBeLessThanOrEqual(limit + 0.5);
    // "בחירה" in the end rail, the X in the start rail
    const go = await box(page, '.picker .btn-primary');
    const x = await box(page, '.picker .close-btn');
    expect(go.x + go.w).toBeLessThanOrEqual(win.x + 0.5);
    expect(x.x).toBeGreaterThanOrEqual(win.x + win.w - 0.5);
    await expect(page.locator('.picker .btn-primary')).toHaveText('בחירה');
    await page.locator('.picker .close-btn').tap();
    await atRest(page);
    // the panel: 280 from the start side, with the way home in it
    await page.locator('#tour-fold').tap();
    await page.waitForFunction(() => window.__hdTourState?.more === true && window.__hdTour?.busy === false);
    const p = await box(page, '#tour-more');
    expect(Math.round(p.w)).toBe(280);
    expect(Math.round(p.x + p.w)).toBe(844);
    // every room's button is whole inside it
    for (const b of await page.locator('.tour-rooms button').evaluateAll((els) => els.map((el) => el.getBoundingClientRect().x)))
      expect(b).toBeGreaterThanOrEqual(p.x);
    await expect(page.locator('.tour-home')).toBeVisible();
    await audit(page, 'on its side, the panel open');
    await ctx.close();
  });

  test('every touch target on the phone is 44 × 44 at least; axe finds nothing at rest and in the close-up', async ({ browser }) => {
    for (const [w, h] of [
      [390, 844],
      [844, 390],
    ] as const) {
      const ctx = await phone(browser, w, h);
      const page = await room(ctx);
      const small = () =>
        page.evaluate(() => {
          const stage = document.querySelector('.tour')!;
          const out: string[] = [];
          for (const el of Array.from(stage.querySelectorAll<HTMLElement>('button, a[href], summary, .tour-panel label'))) {
            if (el.closest('[inert]') || el.matches('.tour-spot')) continue;
            const cs = getComputedStyle(el);
            // what a finger cannot land on is not a target (the wheel's card two steps away is reached through its neighbour)
            if (cs.visibility === 'hidden' || cs.display === 'none' || cs.pointerEvents === 'none') continue;
            const b = el.getBoundingClientRect();
            if (!b.width || !b.height) continue;
            const min = 44;
            if (b.width < min - 0.5 || b.height < min - 0.5)
              out.push(`${el.tagName.toLowerCase()}#${el.id}.${el.className} ${Math.round(b.width)}×${Math.round(b.height)}`);
          }
          return out;
        });
      expect(await small(), `at rest, ${w}×${h}`).toEqual([]);
      await audit(page, `at rest, ${w}×${h}`);
      await page.locator('#tour-fold').tap();
      await page.waitForFunction(() => window.__hdTourState?.more === true && window.__hdTour?.busy === false);
      await page.locator('.tour-panel summary').tap();
      expect(await small(), `the panel, ${w}×${h}`).toEqual([]);
      await page.keyboard.press('Escape');
      await page.waitForFunction(() => window.__hdTourState?.more === false && window.__hdTour?.busy === false);
      // the vase: an option with a price and a way to its page
      await page.locator('.tour-tile[data-slot="vase"]').tap();
      await page.getByRole('dialog').waitFor();
      await atRest(page);
      await expect(page.locator('.picker .tour-info a')).toHaveCount(1);
      expect(await small(), `the close-up, ${w}×${h}`).toEqual([]);
      await audit(page, `the close-up, ${w}×${h}`);
      await ctx.close();
    }
  });

  test('the temporary switches: "מילוי וגרירה" still works; the dots alone; a double tap; the dark page', async ({ browser }) => {
    // today's mode, kept: the window fills the stage, a finger drags the picture, a product opens under the finger
    let ctx = await phone(browser);
    let page = await room(ctx, '&frame=fill');
    let client = await ctx.newCDPSession(page);
    const stage = await box(page, '.tour');
    let win = await box(page, '.tour-win');
    expect(win).toEqual(stage);
    const before = await state(page);
    expect(before.vp.w / before.vp.h).toBeLessThan(1);
    await drag(page, client, { x: 200, y: 400 }, { x: 80, y: 400 });
    await atRest(page);
    const after = await state(page);
    expect(after.cam.cu).toBeGreaterThan(before.cam.cu);
    expect(after.cam.z).toBe(1);
    const spot = await box(page, '.tour-spot[data-slot="cushions"]');
    await page.touchscreen.tap(spot.x + spot.w / 2, spot.y + spot.h / 2);
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    expect((await state(page)).open).toBe('cushions');
    await page.keyboard.press('Escape');
    await atRest(page);
    // and the switch itself, from the panel: back to the whole frame without a reload
    await page.locator('#tour-fold').tap();
    await page.waitForFunction(() => window.__hdTourState?.more === true && window.__hdTour?.busy === false);
    await page.locator('.tour-panel summary').tap();
    await page.locator('input[name="tour-frame"][value="whole"]').check();
    await expect.poll(async () => (await state(page)).vp.w / (await state(page)).vp.h).toBeCloseTo(16 / 9, 1);
    expect((await state(page)).cam).toEqual({ cu: 0.5, cv: 0.5, z: 1 });
    await ctx.close();

    // the dots alone: no strip; the first tap always zooms ×2 to the place, the second opens the product
    ctx = await phone(browser);
    page = await room(ctx, '&pick=dots');
    await expect(page.locator('.tour-strip')).toBeHidden();
    expect(await page.locator('.tour-spots').getAttribute('aria-hidden')).toBeNull();
    win = await box(page, '.tour-win');
    const m = (await marks(page)).find((k) => k.id === 'pendant')!;
    await page.touchscreen.tap(win.x + m.x, win.y + m.y);
    await page.waitForFunction(() => window.__hdTourState?.zoomed === true);
    await atRest(page);
    expect(await state(page)).toMatchObject({ open: null, cam: { z: ZOOM.step } });
    const m2 = (await marks(page)).find((k) => k.id === 'pendant')!;
    await page.touchscreen.tap(win.x + m2.x, win.y + m2.y);
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    expect((await state(page)).open).toBe('pendant');
    await ctx.close();

    // a double tap zooms to the point and back; a single tap still opens, a moment later
    ctx = await phone(browser);
    page = await room(ctx, '&zoom=double');
    client = await ctx.newCDPSession(page);
    win = await box(page, '.tour-win');
    const at = { x: win.x + win.w * 0.7, y: win.y + win.h * 0.5 };
    const twice = async () => {
      for (let i = 0; i < 2; i++) {
        await fingers(client, 'touchStart', [at]);
        await fingers(client, 'touchEnd', []);
        await page.waitForTimeout(70);
      }
    };
    await twice();
    await page.waitForFunction(() => window.__hdTourState?.zoomed === true);
    await atRest(page);
    expect((await state(page)).cam.z).toBe(ZOOM.step);
    expect((await state(page)).cam.cu).toBeGreaterThan(0.5);
    await twice();
    await page.waitForFunction(() => window.__hdTourState?.zoomed === false);
    await atRest(page);
    const k = (await marks(page)).find((x) => x.id === 'pendant')!;
    await page.touchscreen.tap(win.x + k.x, win.y + k.y);
    await page.getByRole('dialog').waitFor();
    await ctx.close();

    // the dark page round the window: the same layout, light words on it
    ctx = await phone(browser);
    page = await room(ctx, '&bg=dark');
    expect(await page.locator('.tour').evaluate((el) => getComputedStyle(el).backgroundColor)).toBe('rgb(14, 13, 12)');
    expect(await box(page, '.tour-win')).toEqual(win);
    await audit(page, 'the dark page');
    await ctx.close();
  });

  test('reduced motion: opacity only — nothing slides or rises round the window', async ({ browser }) => {
    const ctx = await phone(browser, 390, 844, { reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    await page.goto('/tour/');
    await ready(page);
    const moved = (sel: string) =>
      page
        .locator(sel)
        .first()
        .evaluate((el) => getComputedStyle(el).transform);
    // the tiles and the closed panel are not moved off their place: they are only unseen
    expect(await moved('.tour-tile')).toBe('none');
    expect(await moved('#tour-more')).toBe('none');
    await expect(page.locator('#tour-more')).toBeHidden();
    await page.locator('#tour-enter').tap();
    await atRest(page);
    await expect(page.locator('.tour-tile[data-on]')).toHaveCount(13);
    await page.locator('#tour-fold').tap();
    await page.waitForFunction(() => window.__hdTourState?.more === true);
    await expect(page.locator('#tour-more')).toBeVisible();
    await page.keyboard.press('Escape');
    await page.locator('.tour-tile[data-slot="vase"]').tap();
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    for (const sel of ['.picker .arc', '.picker .name', '.picker .btn-primary']) expect(await moved(sel), sel).toBe('none');
    await expect(page.locator('.picker .btn-primary')).toBeVisible();
    // the zoom jumps, without travelling
    await page.keyboard.press('Escape');
    await atRest(page);
    await page.locator('#tour-zoom').tap();
    await page.waitForFunction(() => window.__hdTourState?.zoomed === true);
    const ran = await page.evaluate(() =>
      Object.fromEntries(Object.entries(window.__hdTour!.frames).map(([k, v]) => [k, Math.round(v.dt.reduce((a, b) => a + b, 0))])),
    );
    for (const l of ['zoom', 'zoom-in', 'zoom-out', 'wheel-in', 'panel-open', 'panel-close']) expect(ran[l] ?? 0, l).toBeLessThanOrEqual(20);
    await ctx.close();
  });
});
