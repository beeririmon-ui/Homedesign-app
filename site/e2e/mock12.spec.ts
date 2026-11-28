/**
 * MOCK12 (2026-11-28, briefs/site-mock12-wheels-studio-2026-11-28.md), behind HD_PUBLIC=0, design C:
 *
 *  1. several wheels in one frame (plan wm-wheels 7.2): the fixture frame of two wheels (tools/make-fixture-wheels.ts:
 *     numbered swatches, never a product), opened with `?fixture=wheels2`. A choice on each wheel, and both compose on
 *     the stack together: each wheel's rectangle shows its own choice, and nothing outside the two changes. The room's
 *     choices go with it to its other frame and back;
 *  2. FB29: the strip under the room shows a product as sold — its studio picture where one exists (the bedroom's throw,
 *     the bath's towel), else its card with a clean rim, else, where the room cuts the card, its name; never a cut card;
 *  3. no feathered crop: no mask on a picture outside the room; the wheel's studio round is a clean circle.
 *
 * The numbers go to the evidence when HD_EVIDENCE_DIR is set; the screens when HD_SHOTS_DIR is set.
 */
import { test, expect, type Page } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
const note = (name: string, data: unknown) => {
  const dir = process.env.HD_EVIDENCE_DIR;
  if (!dir) return;
  mkdirSync(join(dir, 'data'), { recursive: true });
  writeFileSync(join(dir, 'data', name), JSON.stringify(data, null, 1));
};
const shot = async (page: Page, name: string) => {
  const dir = process.env.HD_SHOTS_DIR;
  if (!dir) return;
  mkdirSync(dir, { recursive: true });
  await page.screenshot({ path: join(dir, name) });
};
const atRest = (page: Page) =>
  page.waitForFunction(() => window.__hdTourState?.phase === 'room' && window.__hdTourState.busy === false && window.__hdTour?.busy === false, undefined, {
    timeout: 120_000,
  });
const noIntro = (page: Page) => page.addInitScript(() => sessionStorage.setItem('hd-intro', '1'));
/** the composition, RGBA, top row first */
const composition = (page: Page) =>
  page.evaluate(() => {
    const e = window.__hdTour!;
    const a = e.read([0, 0, e.gl.width, e.gl.height]);
    let s = '';
    for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode(...a.subarray(i, i + 0x8000));
    return { w: e.gl.width, h: e.gl.height, b64: btoa(s) };
  });
const FIX = 'fixture-wheels2';
type Opt = { position: number; studio?: { src: string } | null; cut?: string };
type Frame = { wheels?: string[]; slots: { id: string; fixed?: boolean; rect: [number, number, number, number]; options: Opt[] }[] };
const frame = (id: string) => read<Frame>(join(SITE, '.generated', `tour.${id}.warm-modern.json`));

/** choose option `pos` on the wheel of `slot` (its mark, the ring, "בחירה") */
async function choose(page: Page, slot: string, pos: number, name: string) {
  await page.locator(`.tour-spot[data-slot="${slot}"]`).click({ force: true });
  await expect(page.getByRole('dialog')).toBeVisible();
  await atRest(page);
  for (let k = 1; k < pos; k++) await page.keyboard.press('ArrowLeft');
  await expect(page.locator('.arc-card[aria-checked="true"]')).toHaveAttribute('aria-label', new RegExp(`^${pos} מתוך 3`));
  if (name) await shot(page, name);
  await page.getByRole('button', { name: 'בחירה והצגה בחדר' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await atRest(page);
}

test.describe('MOCK12: several wheels in a frame, and the studio pictures outside the room', () => {
  test.describe.configure({ timeout: 300_000 });

  test('two wheels in one frame: each choice in its own rectangle, both together on the stack; the room keeps them', async ({ page }) => {
    await noIntro(page);
    await page.goto(`/tour/?skip=1&room=work&fixture=wheels2`);
    await page.waitForFunction((id) => window.__hdTourState?.room === id, FIX, { timeout: 120_000 });
    await atRest(page);
    const d = frame(FIX);
    expect(d.wheels).toEqual(['fx-square', 'fx-disc']);
    const before = await composition(page);
    await choose(page, 'fx-square', 2, 'mock12-wheel-a-1280.png');
    await choose(page, 'fx-disc', 3, 'mock12-wheel-b-1280.png');
    expect(await page.evaluate(() => ({ ...window.__hdTour!.selection }))).toMatchObject({ 'fx-square': 2, 'fx-disc': 3 });
    const after = await composition(page);
    const A = Buffer.from(before.b64, 'base64');
    const B = Buffer.from(after.b64, 'base64');
    const { w, h } = after;
    const px = (buf: Buffer, x: number, y: number) => [...buf.subarray((y * w + x) * 4, (y * w + x) * 4 + 3)];
    // the fixture's own tones (make-fixture-wheels.ts): the square's second, the disc's third, at their middles
    const near = (a: number[], b: number[]) => a.every((v, i) => Math.abs(v - b[i]!) <= 2);
    const sq = d.slots.find((s) => s.id === 'fx-square')!.rect;
    const dc = d.slots.find((s) => s.id === 'fx-disc')!.rect;
    expect(near(px(B, Math.round(w * 0.28125), Math.round(h * 0.6042)), [127, 143, 106]), 'the square shows its second option').toBe(true);
    expect(near(px(B, Math.round(w * 0.7852), Math.round(h * 0.5625)), [139, 111, 85]), 'the disc shows its third option').toBe(true);
    let inA = 0;
    let inB = 0;
    let outside = 0;
    const within = (r: [number, number, number, number], x: number, y: number) =>
      x >= r[0] * w - 2 && x <= r[1] * w + 2 && y >= r[2] * h - 2 && y <= r[3] * h + 2;
    for (let y = 0; y < h; y++)
      for (let x = 0; x < w; x++) {
        const i = (y * w + x) * 4;
        if (A[i] === B[i] && A[i + 1] === B[i + 1] && A[i + 2] === B[i + 2]) continue;
        if (within(sq, x, y)) inA++;
        else if (within(dc, x, y)) inB++;
        else outside++;
      }
    note('wheels2-mock12.json', { inA, inB, outside, sq, dc });
    expect(inA, 'the square changed').toBeGreaterThan(20_000);
    expect(inB, 'the disc changed').toBeGreaterThan(15_000);
    expect(outside, 'nothing outside the two wheels changed').toBe(0);
    // the room keeps its choices between its frames: to the work room's W0 and back
    await page.evaluate(() => window.__hdTour!.toRoom('work', 0));
    expect(await page.evaluate(() => window.__hdTour!.selection['framed-art'])).toBe(1);
    await page.evaluate((id) => window.__hdTour!.toRoom(id, 0), FIX);
    expect(await page.evaluate(() => ({ ...window.__hdTour!.selection }))).toMatchObject({ 'fx-square': 2, 'fx-disc': 3 });
    // outside the room: the hidden picture is named, the box is its card, never a cut
    await expect(page.locator('.slot-item [data-pic="name"]')).toHaveCount(1);
    await expect(page.locator('.slot-item .pic-name')).toContainText('הדגמה: תמונה');
  });

  test('the strip (a phone at 400): studio pictures where they exist, a clean card or a name otherwise, never a cut', async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: 400, height: 860 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'he-IL' });
    const page = await ctx.newPage();
    await noIntro(page);
    const seen: Record<string, Record<string, string>> = {};
    for (const [room, studio] of [
      ['master', 'throw'],
      ['bath', 'hand-towel'],
    ] as const) {
      await page.goto(`/tour/?skip=1&room=${room}`);
      await atRest(page);
      await page.waitForFunction(() => document.querySelectorAll('.tour-tile[data-on]').length > 0, undefined, { timeout: 30_000 });
      const d = frame(room);
      const kinds = await page
        .locator('.tour-tile')
        .evaluateAll((els) => Object.fromEntries(els.map((e) => [e.getAttribute('data-slot')!, e.querySelector('.pic')!.getAttribute('data-pic')!])));
      seen[room] = kinds;
      for (const s of d.slots.filter((x) => !x.fixed)) {
        const o = s.options[0]!;
        const want = o.studio ? 'studio' : o.cut ? 'name' : 'card';
        expect(kinds[s.id], `${room} ${s.id}`).toBe(want);
      }
      // the slot with studio pictures: the studio's sheet, in a tile of the studio's cream
      const tile = page.locator(`.tour-tile[data-slot="${studio}"] .pic`);
      await expect(tile).toHaveAttribute('data-pic', 'studio');
      expect(await tile.locator('image').getAttribute('href')).toMatch(/studio(-\d+)?\.512\.webp$/);
      expect(await tile.evaluate((e) => getComputedStyle(e).backgroundImage)).toContain('241, 232, 220');
      await page.locator('.tour-strip').scrollIntoViewIfNeeded();
      await shot(page, `mock12-strip-${room}-400.png`);
    }
    note('strip-mock12.json', seen);
    // a wheel on the phone: its studio rounds
    await page.locator('.tour-tile[data-slot="hand-towel"]').tap();
    await expect(page.getByRole('dialog')).toBeVisible();
    await atRest(page);
    await shot(page, 'mock12-wheel-bath-400.png');
    await ctx.close();
  });

  test('no feathered crop: no mask on a picture outside the room, and the wheel’s studio round is a clean circle', async ({ page }) => {
    await noIntro(page);
    await page.goto('/tour/?skip=1&room=master');
    await atRest(page);
    await page.locator('.tour-spot[data-slot="throw"]').click({ force: true });
    await expect(page.getByRole('dialog')).toBeVisible();
    await atRest(page);
    const styles = await page.locator('.arc-card > svg.sprite').evaluateAll((els) =>
      els.map((e) => {
        const cs = getComputedStyle(e);
        return { mask: cs.maskImage || cs.webkitMaskImage, clip: cs.clipPath, studio: e.classList.contains('studio') };
      }),
    );
    expect(styles.length).toBe(3);
    for (const s of styles) {
      expect(s.studio).toBe(true);
      expect(s.mask).toBe('none');
      expect(s.clip).toContain('circle');
    }
    await shot(page, 'mock12-wheel-master-1280.png');
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toBeHidden();
    // every picture of the list under the room: no mask either, and a cut card is never shown (its name is)
    const d = frame('master');
    const cut = d.slots.filter((s) => !s.fixed && !s.options[0]!.studio && s.options[0]!.cut).length;
    expect(cut, 'the bedroom has products its room cuts').toBeGreaterThan(0);
    await expect(page.locator('.slot-item .pic-name')).toHaveCount(cut);
    const masks = await page.locator('.slot-item .thumb').evaluateAll((els) => els.map((e) => getComputedStyle(e).maskImage));
    for (const m of masks) expect(m).toBe('none');
  });
});
