/**
 * QA S22, the options.spec fix (S22: wait for the header's cart to stop being aria-busy, then focus + ArrowDown repeated
 * until the next value holds, up to 30 s), against my own server. Same product and same values as the spec.
 * - R runs, the spec's wait, then ONE press: how often does a single press after the wait hold within 3 s / 10 s?
 * - The masking check: an init script swallows the FIRST ArrowDown that reaches the page after the app has mounted
 *   (a lost key: the bug a retry could hide). Then (a) the spec's retry logic, as written; (b) a single press with a long
 *   timeout. A test that guards the keyboard should FAIL on a lost key; one that passes hides it.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> --base=http://127.0.0.1:8840 --site=<copy>/site --runs=12 --out=<json>
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium, expect, type Page } from '@playwright/test';

const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const BASE = arg('base')!;
const SITE = arg('site')!;
const RUNS = Number(arg('runs') ?? 12);
const OUT = arg('out')!;
const O_ = (await import(pathToFileURL(join(SITE, 'shared/src/options.ts')).href)) as typeof import('../build-s22/site/shared/src/options');
const U = (await import(pathToFileURL(join(SITE, 'shared/src/product-url.ts')).href)) as typeof import('../build-s22/site/shared/src/product-url');
const catalog = JSON.parse(readFileSync(join(SITE, '.generated/catalog.public.json'), 'utf8'));
// the spec's choice of product (options.spec.ts, `fits`)
const fits = (p: any) =>
  !!p.options && p.options.axes.length >= 2 && p.options.axes[0].id === 'color' && p.options.axes[0].values.length <= 16 && p.options.axes[0].values.every(([, , hex]: string[]) => hex) && new Set(p.options.p).size > 1;
const P = catalog.products.find((p: any) => p.slot === 'cushions' && fits(p)) ?? catalog.products.find(fits);
const O = O_.expandOptions(P.id, P.options);
const room = O.skus.find((s) => s.in_room)!;
const roomSel = O_.selectionOf(O.axes, room);
const first = O.axes[0]!;
const ok = O_.availableValues(O.axes, O.skus, roomSel, 0);
const order = first.values.filter((v) => ok.has(v.id)).map((v) => v.id);
const next = order[(order.indexOf(roomSel[first.id]!) + 1) % order.length]!;
const fid = (axis: string) => `opt-${P.id}-${axis}`;
const radio = (p: Page, v: string) => p.locator(`input[name="${fid(first.id)}"][value="${v}"]`);
const SWALLOW = `(() => {
  let armed = false, eaten = 0;
  const arm = () => { if (!document.querySelector('a[href="/cart/"][aria-busy="true"]')) armed = true; };
  setInterval(arm, 20);
  window.addEventListener('keydown', (e) => { if (armed && e.key === 'ArrowDown' && eaten === 0) { eaten++; e.preventDefault(); e.stopImmediatePropagation(); } }, true);
  window.__eaten = () => eaten;
})();`;

const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
async function fresh(swallow: boolean) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 }, baseURL: BASE });
  await ctx.addInitScript({ content: 'window.__name = (f) => f;' });
  if (swallow) await ctx.addInitScript({ content: SWALLOW });
  const page = await ctx.newPage();
  await page.goto(U.shopPath(P.id));
  await page.locator(`input[name="${fid(first.id)}"]:checked`).focus();
  await expect(page.locator('a[href="/cart/"][aria-busy="true"]')).toHaveCount(0, { timeout: 30_000 });
  return { ctx, page };
}
const single: { run: number; held3: boolean; held10: boolean; ms: number | null }[] = [];
for (let i = 0; i < RUNS; i++) {
  const { ctx, page } = await fresh(false);
  await radio(page, roomSel[first.id]!).focus();
  const t = Date.now();
  await page.keyboard.press('ArrowDown');
  const held3 = await expect(radio(page, next)).toBeChecked({ timeout: 3_000 }).then(() => true).catch(() => false);
  const held10 = held3 || (await expect(radio(page, next)).toBeChecked({ timeout: 7_000 }).then(() => true).catch(() => false));
  single.push({ run: i + 1, held3, held10, ms: held10 ? Date.now() - t : null });
  await ctx.close();
}
console.log(`one press after the spec's wait: held within 3 s ${single.filter((s) => s.held3).length}/${RUNS}, within 10 s ${single.filter((s) => s.held10).length}/${RUNS}; ms ${single.map((s) => s.ms).join(', ')}`);
// the masking check
const mask: Record<string, unknown> = {};
{
  const { ctx, page } = await fresh(true);
  let presses = 0;
  const t = Date.now();
  const passed = await expect(async () => {
    if (!(await radio(page, next).isChecked())) {
      await radio(page, roomSel[first.id]!).focus();
      presses++;
      await page.keyboard.press('ArrowDown');
    }
    await expect(radio(page, next)).toBeChecked({ timeout: 3_000 });
  })
    .toPass({ timeout: 30_000 })
    .then(() => true)
    .catch(() => false);
  mask.spec_logic = { passed, presses, eaten: await page.evaluate(() => (window as any).__eaten()), ms: Date.now() - t };
  await ctx.close();
}
{
  const { ctx, page } = await fresh(true);
  await radio(page, roomSel[first.id]!).focus();
  await page.keyboard.press('ArrowDown');
  const passed = await expect(radio(page, next)).toBeChecked({ timeout: 15_000 }).then(() => true).catch(() => false);
  mask.single_press = { passed, eaten: await page.evaluate(() => (window as any).__eaten()) };
  await ctx.close();
}
console.log(`a lost first key after mount: the spec's retry ${JSON.stringify(mask.spec_logic)}; one press, 15 s ${JSON.stringify(mask.single_press)}`);
await browser.close();
writeFileSync(OUT, JSON.stringify({ product: P.id, axis: first.id, room: roomSel[first.id], next, single, mask }, null, 1) + '\n');
