// qa-agent, S19: the empty state a full load of the cart shows while the cart loads (the cart GET held 1.5 s), at 400 and
// 1280: a screenshot 400 ms after the click, and one when the line is there. Public build. QA_COPY=<copy>/site node flash-shot.mjs <base> <dir>
import { createRequire } from 'node:module';
import { join } from 'node:path';
const { chromium } = createRequire(join(process.env.QA_COPY, 'package.json'))('playwright-core');
const [BASE, DIR] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
for (const [w, h] of [[400, 860], [1280, 800]]) {
  const ctx = await b.newContext({ locale: 'he-IL', viewport: { width: w, height: h } });
  await ctx.route('**/*', async (r) => {
    const u = new URL(r.request().url());
    if (u.hostname !== '127.0.0.1') return r.abort();
    if (r.request().method() === 'GET' && /^\/api\/cart\/[^/]+\/?$/.test(u.pathname)) await new Promise((x) => setTimeout(x, 1500));
    return r.continue();
  });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
  await p.getByRole('link', { name: /^אגרטל/ }).first().click();
  await p.getByRole('button', { name: 'הוספה לסל' }).click();
  await p.waitForFunction(() => /סל הקניות, [1-9]/.test(document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-label') ?? ''));
  await p.getByRole('link', { name: /^סל הקניות/ }).first().click();
  await p.waitForURL(/\/cart\/$/);
  await p.waitForTimeout(400);
  const txt = await p.locator('.cart-empty h2').textContent().catch(() => null);
  await p.screenshot({ path: join(DIR, `cart-full-load-while-loading-${w}.png`) });
  await p.locator('.cart-line').first().waitFor();
  await p.screenshot({ path: join(DIR, `cart-full-load-loaded-${w}.png`) });
  console.log(`${w}: 400 ms after the click the page says ${JSON.stringify(txt)}; then the line`);
  await ctx.close();
}
await b.close();
