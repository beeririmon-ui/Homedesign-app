/**
 * S22 in the browser.
 * - ת70: "בדף המוצר אפשר לבקש עדכון" leads to a working form. On a scratch site (e2e/scratch-site.ts) whose provider sends
 *   the back-in-stock message, every unavailable item of every story page links, from its sheet, to the shop's product
 *   page (/p/<id>/); from there the customer opens the waiting list, leaves an address, and the API stores it (201).
 *   On the suite's own build (no provider) the sheet says the status alone, and no link.
 * - ה23: with contact details, a page shows one contact block (the page's own, or the footer's), at 1280 and 400; under
 *   "אין גישה" the contact line keeps the system's space from the error box.
 * With HD_SHOTS_DIR set, it also writes the ה23 screens to <dir>/screens (the evidence of the sprint).
 */
import { mkdirSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { placeOrder } from './ops';
import { startScratchSite, type ScratchSite } from './scratch-site';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const PORT = 8790;
const BIS = `http://127.0.0.1:${PORT}`;
/** samples, on purpose: behind the flag a sample contact is a warning (the public build refuses it) */
const CONTACT = { email: 'shop@hd-test.co.il', phone: '03-1234567' };
const NOTE = (JSON.parse(readFileSync(join(SITE, 'copy/promises.he.json'), 'utf8')) as { strings: Record<string, { email: string }> }).strings[
  'story.unavailable_note'
]!.email;
const SHOTS = process.env.HD_SHOTS_DIR ?? '';

type Unavailable = { path: string; item: string; product: string; shop_href: string | null };
/** every unavailable item of every story page, from the pages the build made */
function unavailableItems(): Unavailable[] {
  const out: Unavailable[] = [];
  const walk = (d: string): string[] =>
    readdirSync(d).flatMap((e) => (statSync(join(d, e)).isDirectory() ? walk(join(d, e)) : e === 'index.html' ? [join(d, e)] : []));
  for (const f of walk(join(SITE, 'web/story'))) {
    const m = /<script[^>]*id="st-data"[^>]*>([\s\S]*?)<\/script>/.exec(readFileSync(f, 'utf8'));
    if (!m) continue;
    const d = JSON.parse(m[1]!) as { items?: Record<string, { status: string; product: string; shop_href?: string | null }> };
    for (const [id, it] of Object.entries(d.items ?? {}))
      if (it.status === 'unavailable')
        out.push({
          path: `/story/${relative(join(SITE, 'web/story'), dirname(f)).split('\\').join('/')}/`,
          item: id,
          product: it.product,
          shop_href: it.shop_href ?? null,
        });
  }
  return out;
}
async function openSheet(page: Page, path: string, item: string): Promise<void> {
  await page.goto(path);
  await page.waitForFunction(() => !!(window as unknown as { __story?: unknown }).__story);
  await page.evaluate((i) => (window as unknown as { __story: { openSheet: (x: string) => Promise<void> } }).__story.openSheet(i), item);
  await expect(page.locator('dialog[open]')).toBeVisible();
}

test.describe.configure({ mode: 'serial' });

test.describe('ת70 on the suite build: no provider, the status alone', () => {
  test('every unavailable item has its shop page in the data, and the sheet shows no link without a provider', async ({ page }) => {
    const items = unavailableItems();
    expect(items.length).toBeGreaterThan(0);
    for (const it of items) expect(it.shop_href, `${it.path} ${it.item}`).toBe(`/p/${it.product}/`);
    const first = items[0]!;
    await openSheet(page, first.path, first.item);
    await expect(page.locator('#st-why')).toHaveText('המלאי אינו זמין כעת.');
    await expect(page.locator('#st-why a')).toHaveCount(0);
  });
});

test.describe('a scratch site: a back_in_stock provider and contact details', () => {
  test.use({ baseURL: BIS });
  let site: ScratchSite | undefined;
  test.beforeAll(async () => {
    test.setTimeout(900_000);
    site = await startScratchSite({ port: PORT, contact: CONTACT, keep: !!process.env.HD_KEEP_SCRATCH });
  });
  test.afterAll(async () => {
    await site?.stop();
  });

  test('ת70: from every sheet, the line leads to the shop page, and its form stores the request', async ({ page }) => {
    test.setTimeout(240_000);
    const items = unavailableItems();
    for (const it of items) {
      await openSheet(page, it.path, it.item);
      const link = page.locator('#st-why a');
      await expect(link, `${it.path} ${it.item}`).toHaveText(NOTE);
      await expect(link).toHaveAttribute('href', `/p/${it.product}/`);
      await expect(page.locator('#st-why')).toHaveText(`המלאי אינו זמין כעת. ${NOTE}`);
    }
    // follow it, once per product, and use the form
    const seen = new Set<string>();
    for (const it of items) {
      if (seen.has(it.product)) continue;
      seen.add(it.product);
      await openSheet(page, it.path, it.item);
      await page.locator('#st-why a').click();
      await expect(page).toHaveURL(new RegExp(`/p/${it.product}/$`));
      const wl = page.locator('.waitlist').first();
      await expect(wl.locator('.waitlist-status')).toHaveText('המלאי אינו זמין כעת');
      await wl.getByRole('button', { name: 'עדכנו אותי כשחוזר' }).click();
      await wl.getByLabel('אימייל').fill(`waitlist.${seen.size}@example.com`);
      const stored = page.waitForResponse((r) => r.url().endsWith('/api/waitlist') && r.request().method() === 'POST');
      await wl.getByRole('button', { name: 'עדכנו אותי', exact: true }).click();
      expect((await stored).status(), it.product).toBe(201);
      await expect(wl.getByRole('status')).toHaveText('נרשמתם. נשלח הודעה אחת כשהמוצר חוזר.');
    }
    // the story's own detail page has no form: the sheet never sends the customer there for it
    const first = items[0]!;
    await openSheet(page, first.path, first.item);
    const detail = await page.locator('#st-page').getAttribute('href');
    if (detail) {
      await page.goto(detail);
      await expect(page.locator('form.waitlist-form, .waitlist button')).toHaveCount(0);
    }
  });

  for (const w of [1280, 400] as const)
    test(`ה23 at ${w}: one contact block on a page; space under "אין גישה"`, async ({ browser, request }) => {
      test.setTimeout(120_000);
      const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, locale: 'he-IL', baseURL: BIS });
      const page = await ctx.newPage();
      for (const [path, own] of [
        ['/returns/', true],
        ['/accessibility/', true],
        ['/privacy/', false],
        ['/', false],
      ] as const) {
        await page.goto(path);
        const blocks = page.locator('[data-contact]');
        await expect(blocks.first()).toBeAttached();
        await expect(blocks.filter({ visible: true }), `${path} at ${w}`).toHaveCount(1);
        await expect(page.locator('.site-footer [data-contact]'), path).toBeVisible({ visible: !own });
        if (SHOTS && own) {
          mkdirSync(join(SHOTS, 'screens'), { recursive: true });
          await page.screenshot({ path: join(SHOTS, 'screens', `h23-${path.replace(/\//g, '')}-${w}.png`), fullPage: true });
        }
      }
      const order = await placeOrder(request, `10.22.0.${w === 400 ? 4 : 12}`);
      const other = await browser.newContext({ viewport: { width: w, height: 900 }, locale: 'he-IL', baseURL: BIS });
      const p2 = await other.newPage();
      await p2.goto(`/order/${order.id}/`);
      await expect(p2.getByRole('alert')).toBeVisible();
      const box = (await p2.locator('.notice.error').boundingBox())!;
      const line = (await p2.locator('.order-no-access-contact').boundingBox())!;
      expect(line.y - (box.y + box.height), 'the space under the error box').toBeGreaterThanOrEqual(24);
      await expect(p2.locator('[data-contact]').filter({ visible: true })).toHaveCount(1);
      if (SHOTS) await p2.screenshot({ path: join(SHOTS, 'screens', `h23-order-no-access-${w}.png`), fullPage: true });
      await other.close();
      await ctx.close();
    });
});
