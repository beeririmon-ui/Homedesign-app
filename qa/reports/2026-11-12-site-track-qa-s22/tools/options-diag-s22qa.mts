/**
 * QA S22: why a single ArrowDown after options.spec's hydration signal (the header cart no longer aria-busy) sometimes
 * does not hold. R fresh loads; one press each; on a miss: where the focus is, which value is checked, whether the radio
 * node that was focused is still in the document (a re-render), and the time since navigation.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> --base=… --site=<copy>/site --runs=20 --out=<json>
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium, expect } from '@playwright/test';
const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const BASE = arg('base')!, SITE = arg('site')!, RUNS = Number(arg('runs') ?? 20), OUT = arg('out')!;
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
  await page.goto(U.shopPath(P.id));
  await page.locator(`input[name="${name}"]:checked`).focus();
  await expect(page.locator('a[href="/cart/"][aria-busy="true"]')).toHaveCount(0, { timeout: 30_000 });
  const tSignal = Date.now() - t0;
  await page.evaluate(([n, v]) => { const el = document.querySelector(`input[name="${n}"][value="${v}"]`) as HTMLInputElement; el.focus(); (window as any).__focused = el; }, [name, roomSel[first.id]]);
  await page.keyboard.press('ArrowDown');
  const held = await expect(page.locator(`input[name="${name}"][value="${next}"]`)).toBeChecked({ timeout: 5_000 }).then(() => true).catch(() => false);
  const st = await page.evaluate((n) => ({
    active: document.activeElement ? `${document.activeElement.tagName.toLowerCase()}[name=${(document.activeElement as HTMLInputElement).name ?? ''}][value=${(document.activeElement as HTMLInputElement).value ?? ''}]` : null,
    checked: (document.querySelector(`input[name="${n}"]:checked`) as HTMLInputElement | null)?.value ?? null,
    focusedStillInDoc: document.contains((window as any).__focused),
  }), name);
  rows.push({ run: i + 1, held, t_signal_ms: tSignal, ...st });
  console.log(`${held ? 'held' : 'MISS'} run ${i + 1}: signal after ${tSignal} ms; active ${st.active}; checked ${st.checked}; the focused node still in the page: ${st.focusedStillInDoc}`);
  await ctx.close();
}
await browser.close();
writeFileSync(OUT, JSON.stringify({ product: P.id, room: roomSel[first.id], next, rows }, null, 1) + '\n');
console.log(`held ${rows.filter((r) => r.held).length}/${RUNS}`);
