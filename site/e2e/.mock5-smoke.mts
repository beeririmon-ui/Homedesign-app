import { chromium } from '@playwright/test';
const OUT = process.argv[2]!;
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
for (const [w, h] of [[1280, 720], [400, 860]] as const) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, locale: 'he-IL' });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.log('PAGEERROR', String(e)));
  for (const room of ['master-mb1', 'dining', 'dining-d2', 'work', 'bath-b1']) {
    await page.goto(`http://127.0.0.1:8788/tour/?skip=1&room=${room}`);
    await page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60000 });
    await page.waitForFunction(() => window.__hdTourState?.phase === 'room' && window.__hdTourState.busy === false && window.__hdTour?.busy === false, undefined, { timeout: 120000 });
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${OUT}/${room}-${w}.png` });
    console.log(room, w, await page.locator('.tour-sale').textContent(), await page.locator('.tour-spot').count());
  }
  await ctx.close();
}
await b.close();
