/**
 * Opens dist-artifact/ in Chromium (served by `python3 -m http.server`, wrapped in a document skeleton the way the
 * Artifact host does) at 1280 and 400 px, walks the main flow and saves screenshots to site/screens/.
 * Fails on page errors, failed same-origin requests, or requests to hosts other than Google Fonts.
 */
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync } from 'node:fs';
import { chromium, type Page } from '@playwright/test';
import { sitePath } from './lib/paths';

const PORT = 5199;
const ORIGIN = `http://127.0.0.1:${PORT}`;
const OUT = sitePath('screens');
mkdirSync(OUT, { recursive: true });

const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1', '-d', sitePath('dist-artifact')], { stdio: 'ignore' });
const stop = () => server.kill();
process.on('exit', stop);
await new Promise((r) => setTimeout(r, 700));

const page_html = readFileSync(sitePath('dist-artifact/index.html'), 'utf8');
const wrapped = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>${page_html}</body></html>`;

const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const problems: string[] = [];
const stats: string[] = [];

async function run(width: number, height: number, mobile: boolean) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: mobile ? 2 : 1, isMobile: mobile, hasTouch: mobile, locale: 'he-IL' });
  const page = await ctx.newPage();
  let bytes = 0;
  page.on('pageerror', (e) => problems.push(`[${width}] pageerror: ${e.message}`));
  page.on('console', (m) => m.type() === 'error' && !/Failed to load resource/.test(m.text()) && problems.push(`[${width}] console: ${m.text()}`));
  page.on('requestfailed', (r) => !/fonts\.(googleapis|gstatic)/.test(r.url()) && problems.push(`[${width}] failed: ${r.url()}`));
  page.on('response', async (r) => {
    if (r.url().startsWith(ORIGIN)) bytes += Number((await r.headerValue('content-length')) ?? 0);
  });
  page.on('request', (r) => {
    const u = new URL(r.url());
    if (u.origin !== ORIGIN && !/^fonts\.(googleapis|gstatic)\.com$/.test(u.hostname) && u.protocol.startsWith('http')) problems.push(`[${width}] external request: ${r.url()}`);
  });
  await page.route(`${ORIGIN}/`, (route) => route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: wrapped }));
  const shot = (name: string) => page.screenshot({ path: `${OUT}/artifact-${width}-${name}.png` });

  await page.goto(`${ORIGIN}/`, { waitUntil: 'load' });
  await page.getByRole('heading', { level: 1 }).first().waitFor();
  await page.waitForTimeout(600);
  await shot('1-home');

  await page.getByRole('link', { name: 'היכנסו לסלון' }).click();
  await page.locator('button.hotspot:not([hidden])').first().waitFor({ timeout: 20_000 });
  await page.waitForTimeout(900);
  stats.push(`[${width}] room ready, same-origin bytes so far: ${(bytes / 1048576).toFixed(2)} MB, compositor: ${await page.evaluate(() => window.__hdEngine?.kind)}`);
  await shot('2-room');

  await page.locator('button.hotspot[data-slot="vase"]').click();
  await page.getByRole('dialog').waitFor();
  await page.keyboard.press('ArrowLeft');
  await page.waitForTimeout(1200);
  await shot('3-wheel');
  await page.getByRole('button', { name: 'הוספה לסל' }).click();
  await page.waitForTimeout(400);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(1300);

  await page.getByRole('link', { name: /^סל הקניות/ }).click();
  await page.getByRole('heading', { name: 'סל הקניות' }).waitFor();
  await shot('4-cart');
  await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
  await page.getByLabel('שם מלא').fill('ישראלה ישראלי');
  await page.getByLabel('אימייל').fill('buyer@example.com');
  await page.getByLabel('טלפון').fill('050-1234567');
  await page.getByLabel('עיר').fill('תל אביב');
  await page.getByLabel('רחוב').fill('הרצל');
  await page.getByLabel('מספר בית').fill('10');
  await page.getByRole('checkbox', { name: /קראתי ואני מסכים/ }).check();
  await shot('5-checkout');
  await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
  await page.getByRole('button', { name: 'אישור תשלום (מדומה)' }).click();
  await page.getByText('הועברה לספק').waitFor();
  await shot('6-order');

  const first = (await page.evaluate(() => (window as unknown as { __hdFrames?: number[] }).__hdFrames ?? [])) as number[];
  if (first.length) {
    const avg = first.reduce((s, x) => s + x, 0) / first.length;
    stats.push(`[${width}] engine animation frames: ${first.length}, mean ${avg.toFixed(1)} ms (headless SwiftShader, not a device measurement)`);
  }
  await ctx.close();
}

try {
  await run(1280, 800, false);
  await run(400, 860, true);
} catch (e) {
  problems.push(`flow failed: ${e instanceof Error ? e.message : String(e)}`);
} finally {
  await browser.close();
  stop();
}
for (const s of stats) console.log(s);
console.log(`screenshots: ${OUT}/artifact-{1280,400}-*.png`);
if (problems.length) {
  for (const p of problems) console.error(`FAIL  ${p}`);
  process.exit(1);
}
