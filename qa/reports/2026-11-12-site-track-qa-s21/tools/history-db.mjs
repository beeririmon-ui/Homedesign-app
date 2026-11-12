/**
 * qa-agent, S21 (ת63, "no storage"): does the cart id in the fragment reach the BROWSER's own history (the profile's
 * History database: the address bar's suggestions, and what a synced browser uploads), beyond the tab's session history?
 * A persistent Chromium profile in my scratch; localStorage and sessionStorage refused (as with "block all site data",
 * where the browser history is still kept); product → "הוספה לסל" → the header's cart → "להמשך לתשלום"; the profile is
 * closed and its History database read (by the caller, python3 -I with sqlite3).
 *   QA_COPY=<copy>/site node history-db.mjs <base> <profile dir> [storage: 'refused' | 'kept']
 */
import { createRequire } from 'node:module';
import { join } from 'node:path';
const { chromium } = createRequire(join(process.env.QA_COPY, 'package.json'))('playwright-core');
const [BASE, PROFILE, MODE = 'refused'] = process.argv.slice(2);
const ctx = await chromium.launchPersistentContext(PROFILE, { executablePath: '/opt/pw-browsers/chromium', headless: true, locale: 'he-IL', viewport: { width: 1280, height: 800 } });
if (MODE === 'refused')
  await ctx.addInitScript(() => {
    const deny = () => {
      throw new DOMException('The operation is insecure.', 'SecurityError');
    };
    Object.defineProperty(window, 'localStorage', { get: deny, configurable: true });
    Object.defineProperty(window, 'sessionStorage', { get: deny, configurable: true });
  });
await ctx.route('**/*', (r) => (new URL(r.request().url()).hostname === '127.0.0.1' ? r.continue() : r.abort()));
const page = ctx.pages()[0] ?? (await ctx.newPage());
await page.goto(`${BASE}/p/vase-textured-white-stoneware-w90r9/`, { waitUntil: 'load' });
await page.getByRole('button', { name: 'הוספה לסל' }).click();
await page.waitForFunction(() => /סל \(1\)/.test(document.querySelector('header a[href="/cart/"]')?.innerText ?? ''));
await page.locator('header a[href="/cart/"]').first().click();
await page.waitForURL(/\/cart\//);
await page.locator('.cart-line').first().waitFor();
await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
await page.waitForURL(/\/checkout\//);
await page.locator('.summary li').first().waitFor();
console.log(JSON.stringify({ final_url: page.url().replace(BASE, ''), mode: MODE }));
await page.waitForTimeout(1500);
await ctx.close();
