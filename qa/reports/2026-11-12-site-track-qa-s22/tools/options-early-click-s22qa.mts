/**
 * QA S22: a customer's choice made before the product page hydrates. R fresh loads; as soon as the swatch is in the page
 * (domcontentloaded), a real mouse click on the next colour; then 4 s later: which colour is checked, which the price and
 * the legend say; then "הוספה לסל" and the cart line: which colour the customer gets. A choice the page shows but does
 * not hold is the user-facing side of the options.spec flake.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> --base=… --site=<copy>/site --runs=10 --out=<json>
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from '@playwright/test';
const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const BASE = arg('base')!, SITE = arg('site')!, RUNS = Number(arg('runs') ?? 10), OUT = arg('out')!;
const O_ = (await import(pathToFileURL(join(SITE, 'shared/src/options.ts')).href)) as any;
const U = (await import(pathToFileURL(join(SITE, 'shared/src/product-url.ts')).href)) as any;
const catalog = JSON.parse(readFileSync(join(SITE, '.generated/catalog.public.json'), 'utf8'));
const fits = (p: any) => !!p.options && p.options.axes.length >= 2 && p.options.axes[0].id === 'color' && p.options.axes[0].values.length <= 16 && p.options.axes[0].values.every(([, , hex]: string[]) => hex) && new Set(p.options.p).size > 1;
const P = catalog.products.find((p: any) => p.slot === 'cushions' && fits(p)) ?? catalog.products.find(fits);
const O = O_.expandOptions(P.id, P.options);
const room = O.skus.find((s: any) => s.in_room);
const roomSel = O_.selectionOf(O.axes, room);
const first = O.axes[0];
const ok = O_.availableValues(O.axes, O.skus, roomSel, 0);
const order = first.values.filter((v: any) => ok.has(v.id)).map((v: any) => v.id);
const next = order[(order.indexOf(roomSel[first.id]) + 1) % order.length];
const name = `opt-${P.id}-${first.id}`;
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const rows: any[] = [];
for (let i = 0; i < RUNS; i++) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 }, baseURL: BASE });
  await ctx.addInitScript({ content: 'window.__name = (f) => f;' });
  const page = await ctx.newPage();
  const t0 = Date.now();
  await page.goto(U.shopPath(P.id), { waitUntil: 'domcontentloaded' });
  const target = page.locator(`input[name="${name}"][value="${next}"]`);
  const busyAtClick = await page.locator('a[href="/cart/"][aria-busy="true"]').count();
  await target.click({ force: true });
  const tClick = Date.now() - t0;
  const right = await target.isChecked();
  await page.waitForTimeout(4000);
  const st = await page.evaluate((n) => ({ checked: (document.querySelector(`input[name="${n}"]:checked`) as HTMLInputElement | null)?.value ?? null, legend: (document.querySelector('.opt-legend') as HTMLElement | null)?.innerText ?? null, price: (document.querySelector('.price-row .price-big .num') as HTMLElement | null)?.innerText ?? null }), name);
  await page.getByRole('button', { name: 'הוספה לסל' }).click();
  await page.waitForTimeout(1500);
  await page.goto('/cart/');
  const cartLine = await page.locator('.cart-line').first().innerText({ timeout: 10_000 }).catch(() => null);
  rows.push({ cart_line: cartLine?.replace(/\s+/g, ' ').slice(0, 160) ?? null, run: i + 1, click_ms: tClick, cart_busy_at_click: busyAtClick > 0, checked_right_after: right, checked_4s: st.checked, kept: st.checked === next, legend: st.legend, price: st.price });
  console.log(`${st.checked === next ? 'kept    ' : 'REVERTED'} run ${i + 1}: click at ${tClick} ms (cart busy: ${busyAtClick > 0}); right after: ${right}; 4 s later checked ${st.checked}; legend "${st.legend}"; price ${st.price}; cart: ${rows[rows.length - 1].cart_line}`);
  await ctx.close();
}
await browser.close();
writeFileSync(OUT, JSON.stringify({ product: P.id, room: roomSel[first.id], next, rows }, null, 1) + '\n');
console.log(`kept ${rows.filter((r) => r.kept).length}/${RUNS}`);
