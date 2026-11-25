/**
 * MOCK6 (2026-11-25), the kids' rooms in the tour and the wheel of many options (briefs/site-mock6-kids-rooms-2026-11-25.md),
 * behind HD_PUBLIC=0:
 *
 *  1. the boy's and the girl's rooms from the panel ("חדר הילד", "חדר הילדה"): at rest on the plain composition of
 *     their layers, a mark for each of their 13 / 12 products and none for the walnut bed, desk and chair, the owner's
 *     line with the products the safety rule holds, no zoom (the prints are ×1 only);
 *  2. the safety rule: the Roman blind "לא במכירה", the pendant "לא במכירה לחדר ילדים" (MOCK6 keeps its mark), the
 *     toys "ממתין לתקן EN 71"; none of them has a price or a cart, and no line promises an email (S18: the waiting
 *     list's offer shows only once a provider sends it);
 *  3. the throw's wheel in each room (V1–V3, the arc), and the encoding gate on its three compositions against the
 *     folders' own (K-<room>-defaults, -V2, -V3);
 *  4. the bath: B1 with its ledge planter, the room's line at 19;
 *  5. the wheel of many options with its fixture of ten (?fixture=wheel10): the counter, the keys, a swipe, and only
 *     the options it rests on asked for; the room under it unchanged;
 *  6. the living room is MOCK5's (the pin: the same generated room);
 *  7. a phone's first load of each kids' room under 3 MB;
 *  8. axe on the kids' rooms at rest (a wide screen and a phone), the throw's wheel, a held product's panel and the
 *     fixture's wheel.
 *
 * The numbers go to the evidence when HD_EVIDENCE_DIR is set.
 */
import { test, expect, devices, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import sharp from 'sharp';
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { failures, measure, type Measure } from '../tools/lib/encoding';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const REPO = resolve(SITE, '..');
const read = <T>(f: string): T => JSON.parse(readFileSync(f, 'utf8')) as T;
const note = (name: string, data: unknown) => {
  const dir = process.env.HD_EVIDENCE_DIR;
  if (!dir) return;
  mkdirSync(join(dir, 'data'), { recursive: true });
  writeFileSync(join(dir, 'data', name), JSON.stringify(data, null, 1));
};
type Frame = {
  room: string;
  camera_from: string;
  zoom: boolean;
  for_sale: number;
  sample?: string;
  avoid: [number, number, number, number][];
  slots: { id: string; fixed?: boolean; sale?: { state: string; label_he: string; why_he: string }; options: { price_agorot: number | null }[] }[];
};
const frame = (id: string) => read<Frame>(resolve(SITE, `.generated/tour.${id}.warm-modern.json`));
/** the brief's counts, and the products the safety rule holds in each */
const KIDS = {
  boy: { count: 13, held: 4, title: /^חדר הילד/, button: 'חדר הילד' },
  girl: { count: 12, held: 3, title: /^חדר הילדה/, button: 'חדר הילדה' },
} as const;
const HELD: Record<string, string> = {
  'roman-blind': 'לא במכירה',
  pendant: 'לא במכירה לחדר ילדים',
  'toy-cars': 'ממתין לתקן EN 71',
  'soft-toy': 'ממתין לתקן EN 71',
};
const saleLine = (room: keyof typeof KIDS) => `${KIDS[room].count} מוצרים למכירה בחדר · ${KIDS[room].held} מהם מחכים לתקן בטיחות`;

const ready = (page: Page) => page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60_000 });
const atRest = (page: Page) =>
  page.waitForFunction(() => window.__hdTourState?.phase === 'room' && window.__hdTourState.busy === false && window.__hdTour?.busy === false, undefined, {
    timeout: 120_000,
  });
async function more(page: Page) {
  if ((await page.locator('#tour-fold').getAttribute('aria-expanded')) !== 'true') await page.locator('#tour-fold').click();
  await page.waitForFunction(() => window.__hdTourState?.more === true && window.__hdTour?.busy === false);
}
const hashes = (page: Page) =>
  page.evaluate(() => {
    const fnv = (a: Uint8Array) => {
      let h = 0x811c9dc5;
      for (let i = 0; i < a.length; i++) h = Math.imul(h ^ a[i]!, 0x01000193) >>> 0;
      return h;
    };
    const e = window.__hdTour!;
    const composition = fnv(e.read([0, 0, e.gl.width, e.gl.height]));
    e.render();
    return { composition, screen: fnv(e.gl.readScreen().data) };
  });
async function plain(page: Page, room: string) {
  await page.goto(`/tour/?skip=1&room=${room}`);
  await ready(page);
  await atRest(page);
  return hashes(page);
}
const view = (page: Page) =>
  page.evaluate(() => {
    const e = window.__hdTour!;
    const fw = Math.max(e.vp.w, e.vp.h * (16 / 9));
    const fh = fw / (16 / 9);
    const hu = e.vp.w / (2 * fw * e.cam.z);
    const hv = e.vp.h / (2 * fh * e.cam.z);
    return { z: e.cam.z, rest: e.rest.z, u: [e.cam.cu - hu, e.cam.cu + hu], v: [e.cam.cv - hv, e.cam.cv + hv] };
  });
const shows = (v: { u: number[]; v: number[] }, a: number[]) => v.u[0]! < a[1]! && v.u[1]! > a[0]! && v.v[0]! < a[3]! && v.v[1]! > a[2]!;
async function openSpot(page: Page, slot: string) {
  // the strip's tile on a phone, the mark on a wide screen (as e2e/mock5.spec.ts opens a slot)
  const tile = page.locator(`.tour-tile[data-slot="${slot}"]`);
  if (await tile.isVisible()) await tile.click();
  else await page.locator(`.tour-spot[data-slot="${slot}"]`).click({ force: true });
  await expect(page.getByRole('dialog')).toBeVisible();
  await atRest(page);
}
async function closeSpot(page: Page) {
  await page.getByRole('button', { name: 'סגירת התקריב' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await atRest(page);
}
async function audit(page: Page, label: string) {
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== 'running'), undefined, { timeout: 10_000 });
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const summary = r.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')} — ${v.help}`);
  expect(summary, `${label}\n${summary.join('\n')}`).toEqual([]);
}
/** the fixture's record (tour/fixture-wheel.ts) */
const fixtureState = (page: Page) => page.evaluate(() => window.__hdWheelFixture!);

test.describe('MOCK6: the kids’ rooms and the wheel of many options', () => {
  test.describe.configure({ timeout: 400_000 });

  for (const room of ['boy', 'girl'] as const) {
    test(`${room}: from the panel; the plain composition at rest; 13 / 12 marks, none on the furniture; the owner’s line; no zoom`, async ({ page }) => {
      const d = frame(room);
      const k = KIDS[room];
      expect(d.camera_from).toBe(`style_shells_1_3_1.warm-modern.kids.cameras.K-${room}`);
      expect(d.for_sale).toBe(k.count);
      const want = await plain(page, room);
      await page.goto('/tour/?skip=1');
      await ready(page);
      await atRest(page);
      await more(page);
      const btn = page.locator(`#tour-${room}`);
      await expect(btn).toContainText(k.button);
      await btn.click();
      await page.waitForFunction((x) => window.__hdTourState?.room === x, room);
      await atRest(page);
      expect(await hashes(page), `${room} rests on the plain composition of its layers`).toEqual(want);
      await expect(page.locator('.tour-spot')).toHaveCount(k.count);
      for (const id of ['bed', 'desk', 'desk-chair']) await expect(page.locator(`.tour-spot[data-slot="${id}"]`)).toHaveCount(0);
      await expect(page.locator('.tour-sale')).toHaveText(saleLine(room));
      await expect(page.locator('#tour-title')).toHaveText(k.title);
      // the prints' rights are unclear: ×1 only, no zoom in the frame
      expect(d.zoom).toBe(false);
      await expect(page.locator('#tour-zoom')).toBeHidden();
      // one frame: no frame control
      await expect(page.locator('.tour-frames')).toHaveCount(0);
    });
  }

  test('the safety rule: the blind and the pendant shown and not sold, the toys waiting for EN 71; no price, no cart, no promise', async ({ page }) => {
    const seen: Record<string, unknown> = {};
    for (const room of ['boy', 'girl'] as const) {
      const d = frame(room);
      await page.goto(`/tour/?skip=1&room=${room}`);
      await ready(page);
      await atRest(page);
      const held = d.slots.filter((s) => s.sale);
      expect(held.map((s) => s.id).sort()).toEqual(
        Object.keys(HELD)
          .filter((id) => room === 'boy' || id !== 'toy-cars')
          .sort(),
      );
      for (const s of held) {
        expect(s.sale!.label_he).toBe(HELD[s.id]);
        // its mark says it in the price's place (the pendant keeps its mark: MOCK6's choice)
        const spot = page.locator(`.tour-spot[data-slot="${s.id}"]`);
        await expect(spot).toHaveCount(1);
        await expect(spot).toHaveAttribute('aria-label', new RegExp(`, ${HELD[s.id]}\\.`));
        await expect(page.locator(`.tour-tile[data-slot="${s.id}"]`)).toHaveAttribute('aria-label', new RegExp(`, ${HELD[s.id]}\\.`));
      }
      // a held product's panel: the line and why, no price, no cart
      for (const id of ['pendant', 'soft-toy']) {
        await openSpot(page, id);
        const panel = page.locator('.picker .tour-held');
        await expect(panel).toBeVisible();
        await expect(panel).toContainText(HELD[id]!);
        await expect(panel).toContainText(d.slots.find((s) => s.id === id)!.sale!.why_he);
        await expect(page.locator('.picker')).not.toContainText('₪');
        await expect(page.locator('.picker').getByRole('button', { name: 'הוספה לסל' })).toHaveCount(0);
        seen[`${room} ${id}`] = await panel.innerText();
        await closeSpot(page);
      }
      // textiles are sold as usual: the bedspread's and the pillowcases' marks carry no hold (a card the shop cannot
      // price yet says "עוד לא במכירה", as in every room)
      for (const id of ['bedspread', 'pillowcase', 'cushions', 'bedding'])
        await expect(page.locator(`.tour-spot[data-slot="${id}"]`)).not.toHaveAttribute('aria-label', /, (לא במכירה|לא במכירה לחדר ילדים|ממתין לתקן EN 71)\./);
      // S18: nothing promises an email while no provider sends it (the waiting list's offer is the copy's)
      await expect(page.locator('body')).not.toContainText('עדכנו אותי');
    }
    note('held.json', seen);
  });

  test('the throw’s wheel in each room (V1–V3, the arc, a close-up that keeps out of the prints)', async ({ page }) => {
    const seen: Record<string, unknown> = {};
    for (const room of ['boy', 'girl'] as const) {
      const d = frame(room);
      expect(d.sample).toBe('bedspread');
      await page.goto(`/tour/?skip=1&room=${room}`);
      await ready(page);
      await atRest(page);
      await openSpot(page, 'bedspread');
      await expect(page.locator('.arc-card')).toHaveCount(3);
      await expect(page.locator('.snap-card')).toHaveCount(0);
      const v = await view(page);
      seen[room] = v;
      expect(v.z, `${room}: the close-up comes closer`).toBeGreaterThan(v.rest * 1.2);
      for (const a of d.avoid) expect(shows(v, a), `${room}: the close-up never shows the prints`).toBe(false);
      for (let pos = 2; pos <= 3; pos++) {
        await page.keyboard.press('ArrowLeft');
        await expect.poll(() => page.evaluate(() => window.__hdTour!.selection['bedspread'])).toBe(pos);
      }
      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).toBeHidden();
      await atRest(page);
      expect(await page.evaluate(() => window.__hdTour!.selection['bedspread'])).toBe(1);
    }
    note('throw-wheels.json', seen);
  });

  test('the encoding gate on the kids’ rooms: the throw’s three compositions against the folders’ own', async ({ page }) => {
    const out: Record<string, Measure & { pass: boolean; identical: number }> = {};
    const bad: string[] = [];
    for (const id of ['boy', 'girl'] as const) {
      type Cfg = { layers: string; manifest: string; truth: string; sample: string };
      const cfg = read<Cfg>(resolve(SITE, `tools/tour/${id}.warm-modern.json`));
      const dir = resolve(REPO, cfg.layers);
      type L = { slot: string; layer: string; default?: boolean };
      const lm = read<{ layers: L[] }>(join(dir, cfg.manifest));
      const defaults = lm.layers.filter((l) => l.default !== false);
      const alt = lm.layers.filter((l) => l.default === false);
      const cases = [
        { pos: 1, truth: cfg.truth, alpha: defaults.map((l) => l.layer) },
        ...[`K-${id}-V2.png`, `K-${id}-V3.png`].map((t, i) => ({
          pos: i + 2,
          truth: t,
          alpha: defaults
            .filter((l) => l.slot !== cfg.sample)
            .map((l) => l.layer)
            .concat(alt[i]!.layer),
        })),
      ];
      await page.goto(`/tour/?skip=1&room=${id}`);
      await ready(page);
      await atRest(page);
      expect(await page.evaluate(() => window.__hdTour!.gl.width), 'a wide screen composes at the layers’ own width').toBe(2720);
      for (const c of cases) {
        const b64 = await page.evaluate(
          async ([slot, pos]) => {
            const e = window.__hdTour!;
            const m = window.__hdTourFx!;
            e.sync = true;
            if (pos > 1) {
              const ui = { ring() {}, label() {}, spots() {}, count() {}, dims() {} };
              await e.option(slot, pos);
              if (e.selection[slot] !== pos) await m.swap(e, ui, e.slot(slot), pos, pos > e.selection[slot]! ? 1 : -1, 's1');
            }
            const a = e.read([0, 0, e.gl.width, e.gl.height]);
            let s = '';
            for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode(...a.subarray(i, i + 0x8000));
            return btoa(s);
          },
          [cfg.sample, c.pos] as const,
        );
        const enc = Buffer.from(b64, 'base64');
        const truth = await sharp(join(dir, c.truth)).ensureAlpha().raw().toBuffer();
        const keep = new Uint8Array(2720 * 1530);
        for (const f of c.alpha) {
          const al = await sharp(join(dir, f)).ensureAlpha().extractChannel(3).raw().toBuffer();
          for (let i = 0; i < al.length; i++) if (al[i] === 255) keep[i] = 1;
        }
        const idx: number[] = [];
        for (let i = 0; i < keep.length; i++) if (keep[i]) idx.push(i);
        const A = new Uint8Array(idx.length * 4);
        const B = new Uint8Array(idx.length * 4);
        idx.forEach((k, j) => {
          A.set(truth.subarray(k * 4, k * 4 + 4), j * 4);
          B.set(enc.subarray(k * 4, k * 4 + 4), j * 4);
        });
        let same = 0;
        for (let i = 0; i < truth.length; i += 4) if (truth[i] === enc[i] && truth[i + 1] === enc[i + 1] && truth[i + 2] === enc[i + 2]) same++;
        const mm = measure(A, B, false);
        const f = failures(mm);
        out[`${id} ${c.pos} (${c.truth})`] = { ...mm, pass: f.length === 0, identical: +(same / (truth.length / 4)).toFixed(4) };
        for (const x of f) bad.push(`${id} ${c.pos}: ${x}`);
      }
    }
    note('encoding-mock6.json', out);
    console.log(
      Object.entries(out)
        .map(([k, m]) => `${k}: ΔE00 p99 ${m.de00_p99}, p99 ${m.p99}, identical ${(m.identical * 100).toFixed(1)}%`)
        .join('\n'),
    );
    expect(bad, bad.join('\n')).toEqual([]);
  });

  test('the bath: B1 with its ledge planter, the room at 19', async ({ page }) => {
    const d = frame('bath-b1');
    expect(d.slots.some((s) => s.id === 'ledge-planter')).toBe(true);
    await page.goto('/tour/?skip=1&room=bath-b1');
    await ready(page);
    await atRest(page);
    await expect(page.locator('.tour-spot[data-slot="ledge-planter"]')).toHaveCount(1);
    await expect(page.locator('.tour-spot')).toHaveCount(d.for_sale);
    await expect(page.locator('.tour-sale')).toHaveText('19 מוצרים למכירה בחדר');
  });

  test('the wheel of many options, a fixture of ten: the counter, the keys, a swipe; only the options it rests on are asked for', async ({ page }) => {
    const want = await plain(page, 'boy');
    await page.goto('/tour/?skip=1&room=boy&fixture=wheel10');
    await ready(page);
    await atRest(page);
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole('heading')).toHaveText('הדגמה: גלגל של 10 אפשרויות');
    await expect(page.locator('.snap-card')).toHaveCount(10);
    await expect(page.locator('.arc-card')).toHaveCount(0);
    const count = page.locator('.snap-count');
    await expect(count).toHaveText('1 / 10');
    await expect(page.locator('.snap-card[aria-checked="true"]')).toHaveAttribute('aria-label', '1 מתוך 10: דוגמה 1 (לא מוצר)');
    // it draws the cards near the one it rests on: five of ten at most
    expect(await page.locator('.snap-card[data-near] svg').count()).toBeLessThanOrEqual(5);
    expect((await fixtureState(page)).loads).toEqual([]);
    // the keys: ← the next (right to left), End the last
    await page.keyboard.press('ArrowLeft');
    await expect(count).toHaveText('2 / 10');
    await expect.poll(async () => (await fixtureState(page)).loads).toEqual([2]);
    await page.keyboard.press('End');
    await expect(count).toHaveText('10 / 10');
    await expect.poll(async () => (await fixtureState(page)).shown).toBe(10);
    await page.keyboard.press('Home');
    await expect(count).toHaveText('1 / 10');
    await expect.poll(async () => (await fixtureState(page)).shown).toBe(1);
    // the wheel's own move back to the first card has landed
    await expect.poll(() => page.locator('.snap').evaluate((el) => Math.round(el.scrollLeft))).toBe(0);
    const afterKeys = (await fixtureState(page)).loads.length;
    // a swipe across five cards (the scroller scrolls by itself): one rest, one patch asked for
    const step = await page
      .locator('.snap-card')
      .nth(1)
      .evaluate((el) => {
        const a = el.getBoundingClientRect();
        const b = el.previousElementSibling!.getBoundingClientRect();
        return Math.abs(a.left - b.left);
      });
    await page.locator('.snap').evaluate((el, dx) => el.scrollBy({ left: -dx, behavior: 'smooth' }), step * 5);
    await expect(count).toHaveText('6 / 10', { timeout: 10_000 });
    await expect.poll(async () => (await fixtureState(page)).shown).toBe(6);
    const s = await fixtureState(page);
    const swipe = s.loads.slice(afterKeys);
    expect(swipe, 'the cards passed on the way are never asked for').toEqual([6]);
    // the room under it never changed
    expect(await hashes(page)).toEqual(want);
    note('fixture-wheel.json', s);
    // Escape cancels
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
    expect((await fixtureState(page)).cancelled).toBe(true);
  });

  test('the living room is MOCK5’s (pinned: the same generated room)', () => {
    const sha = createHash('sha256')
      .update(readFileSync(resolve(SITE, '.generated/tour.living-room.warm-modern.json')))
      .digest('hex');
    expect(sha).toBe('fa031c4aa2c1fd168d9b2da5a1a9e3ef949abc4643a516a38e28ed3ba2f428b4');
    const t = read<{ pin?: string; layers: string; manifest: string }>(resolve(SITE, 'tools/tour/living-room.warm-modern.json'));
    expect(t.pin).toBe('tools/tour/living-room.pin.json');
    expect(t.manifest).toBe('manifest-r9.json');
    const pin = read<{ files: Record<string, string> }>(resolve(SITE, t.pin!));
    expect(Object.keys(pin.files)).toContain(`${t.layers}/base.png`);
    expect(Object.keys(pin.files)).toContain(`${t.layers}/${t.manifest}`);
  });

  test('a phone’s first load of each kids’ room stays under 3 MB', async ({ browser }) => {
    const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];
    const sizes: Record<string, number> = {};
    for (const id of ['boy', 'girl']) {
      const ctx = await browser.newContext({ ...pixel, locale: 'he-IL' });
      const page = await ctx.newPage();
      let bytes = 0;
      const client = await ctx.newCDPSession(page);
      await client.send('Network.enable');
      const urls = new Map<string, string>();
      client.on('Network.requestWillBeSent', (e) => void urls.set(e.requestId, e.request.url));
      const behind = (u: string) => /\/media\/tour\/arrival\//.test(u) || /\/media\/rooms\//.test(u);
      client.on('Network.loadingFinished', (e) => void (!behind(urls.get(e.requestId) ?? '') && (bytes += e.encodedDataLength)));
      await page.goto(`/tour/?skip=1&room=${id}`);
      await ready(page);
      await atRest(page);
      sizes[id] = bytes;
      await ctx.close();
    }
    note('first-load-mock6.json', sizes);
    console.log(
      Object.entries(sizes)
        .map(([k, b]) => `${k}: ${(b / 1048576).toFixed(2)} MB`)
        .join(', '),
    );
    for (const b of Object.values(sizes)) expect(b).toBeLessThanOrEqual(3 * 1024 * 1024);
  });

  test('axe finds nothing: the kids’ rooms at rest, the throw’s wheel, a held product’s panel, the fixture’s wheel (a wide screen and a phone)', async ({
    browser,
  }) => {
    for (const vp of [
      { width: 1280, height: 800, touch: false },
      { width: 390, height: 844, touch: true },
    ]) {
      const ctx = await browser.newContext({
        locale: 'he-IL',
        viewport: { width: vp.width, height: vp.height },
        ...(vp.touch ? { deviceScaleFactor: 3, hasTouch: true, isMobile: true } : {}),
      });
      const page = await ctx.newPage();
      for (const id of ['boy', 'girl']) {
        await page.goto(`/tour/?skip=1&room=${id}`);
        await ready(page);
        await atRest(page);
        await audit(page, `${vp.width}: ${id} at rest`);
      }
      await openSpot(page, 'bedspread');
      await audit(page, `${vp.width}: the girl's throw wheel`);
      await closeSpot(page);
      await openSpot(page, 'pendant');
      await audit(page, `${vp.width}: the girl's pendant, held`);
      await closeSpot(page);
      await page.goto('/tour/?skip=1&room=boy&fixture=wheel10');
      await ready(page);
      await atRest(page);
      await expect(page.getByRole('dialog')).toBeVisible();
      await audit(page, `${vp.width}: the fixture's wheel of ten`);
      await ctx.close();
    }
  });
});
