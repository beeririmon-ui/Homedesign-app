/**
 * QA S6–S7 ת8 (and ת12): a line in the cart, the checkout and the order names what was bought, by the manager's rule:
 * the base name without a colour · the Hebrew option labels (master-designer's data). The nine variants QA listed (eight
 * and the designer's ninth, the corduroy of ת10) go into one cart through the API, then through the site's cart, its
 * checkout and the mock payment to the order page. Each line must read exactly as the designer's table, and no line may
 * carry Latin letters. Screens for the evidence when HD_SHOTS_DIR is set.
 */
import { test, expect, type Page } from '@playwright/test';
import { existsSync, mkdirSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SHOTS = process.env.HD_SHOTS_DIR ?? null;
type Full = { products: { id: string; card_id?: string; variants_full?: { id: string; active: boolean }[] }[] };
const read = (f: string): Full => JSON.parse(readFileSync(resolve(SITE, '.generated', f), 'utf8')) as Full;
const LABELS = resolve(SITE, '../data/catalog/option-labels-he.json');

// the designer's table (docs/proposals/names-labels-he-2026-11-10.md): card, its option's value ids, the line
const NINE: [string, string[], string][] = [
  ['cushions-cj-washed-cotton-frayed', ['50x50', 'white'], 'ציפית כרית כותנה רחוצה עם שוליים פרומים · 50×50 ס"מ, לבן'],
  ['cushions-cj-washed-cotton-frayed', ['50x50', 'earthy-orange'], 'ציפית כרית כותנה רחוצה עם שוליים פרומים · 50×50 ס"מ, טרקוטה'],
  ['cushions-cj-washed-cotton-frayed', ['30x50', 'moss-green'], 'ציפית כרית מותן כותנה רחוצה עם שוליים פרומים · 30×50 ס"מ, ירוק טחב'],
  ['sofa-cover-cj-washed-hemp-throw', ['150x200', 'raw-jute-color'], 'שמיכת קנבוס רחוצה · 150×200 ס"מ, חום יוטה'],
  ['sofa-cover-cj-cotton-muslin-fringe', ['150x200', 'flax-brown'], 'שמיכת מוסלין כותנה עם פרנזים · 150×200 ס"מ, חום פשתן'],
  ['cushions-cj-boucle-teddy', ['milk-tea-color', '50x50'], 'ציפית כרית בוקלה · תה חלב, 50×50 ס"מ'],
  ['cushions-cj-boucle-teddy', ['white', '50x50'], 'ציפית כרית בוקלה · לבן חם, 50×50 ס"מ'],
  ['planter-cj-seagrass-belly', ['yellow', '35x37-cm'], 'סל-עציץ בטן מקש ים · דבש, 35×37 ס"מ'],
  ['cushions-cj-wide-stripe-corduroy-light-green', ['camel'], 'ציפית כרית קורדרוי בדוגמת שיבולים · קאמל'],
];

/** the public variant id of a card's option (the full catalogs of the build: the shop's, then the story's) */
function variantOf(card: string, values: string[]): string {
  for (const f of ['catalog.full.json', 'catalog.story.full.json']) {
    const p = read(f).products.find((x) => x.card_id === card);
    const v = p?.variants_full?.find((x) => x.active && [...x.id.slice(x.id.indexOf(':') + 1).split('+')].sort().join() === [...values].sort().join());
    if (v) return v.id;
  }
  throw new Error(`${card} ${values.join('+')}: no sold variant in the build`);
}
const latin = (s: string) => /[A-Za-z]/.test(s.replace(/\d+\s*K\b/g, ''));
async function shot(page: Page, name: string) {
  if (!SHOTS) return;
  mkdirSync(SHOTS, { recursive: true });
  await page.screenshot({ path: join(SHOTS, `${name}.png`), fullPage: true });
}

test.describe('ת8: the line names what was bought (base name · Hebrew labels)', () => {
  test.skip(!existsSync(LABELS), "turns on with master-designer's labels (data/catalog/option-labels-he.json)");

  test('the nine variants: the API cart, the cart page, the checkout and the order read as the designer’s table', async ({ page, request }) => {
    test.setTimeout(120_000);
    // its own rate-limit bucket (the API counts 60 cart writes a minute per client)
    const ip = { 'cf-connecting-ip': '198.51.100.81' };
    await page.setExtraHTTPHeaders(ip);
    const cart = (await (await request.post('/api/cart', { headers: ip })).json()) as { id: string };
    const want = new Map(NINE.map(([card, values, line]) => [variantOf(card, values), line]));
    for (const id of want.keys()) {
      const r = await request.put(`/api/cart/${cart.id}/items`, { headers: ip, data: { variant_id: id, qty: 1 } });
      expect(r.status(), `${id} is sold`).toBe(200);
    }
    // the API: name_he is the base, option_he the Hebrew labels
    const api = (await (await request.get(`/api/cart/${cart.id}`, { headers: ip })).json()) as {
      lines: { variant_id: string; name_he: string; option_he: string | null }[];
    };
    expect(api.lines).toHaveLength(9);
    for (const l of api.lines) {
      expect(l.option_he ? `${l.name_he} · ${l.option_he}` : l.name_he).toBe(want.get(l.variant_id));
      expect(latin(`${l.name_he} ${l.option_he ?? ''}`), l.variant_id).toBe(false);
    }

    // the site's cart: the base as the line's title, the labels under it
    await page.goto('/');
    await page.evaluate((id) => localStorage.setItem('hd.cart', id), cart.id);
    await page.goto('/cart/');
    await expect(page.locator('.cart-line')).toHaveCount(9);
    const shown = await page
      .locator('.cart-line')
      .evaluateAll((lis) =>
        lis.map((li) =>
          [li.querySelector('.title')?.textContent?.trim() ?? '', li.querySelector('.pack-line')?.textContent?.trim() ?? ''].filter(Boolean).join(' · '),
        ),
      );
    expect([...shown].sort()).toEqual([...want.values()].sort());
    await shot(page, 'cart-nine-lines');

    // the checkout's summary: one line each, "base · labels × 1"
    await page.goto('/checkout/');
    const summary = page.locator('aside.summary li');
    await expect(summary).toHaveCount(9);
    const sum = (await summary.allTextContents()).map((t) => t.replace(/\s+× 1$/, '').trim());
    expect([...sum].sort()).toEqual([...want.values()].sort());

    // the order: paid with the mock, the snapshot (and so the invoice) carries the same lines
    await page.getByLabel('שם מלא').fill('נועה כהן');
    await page.getByLabel('אימייל').fill('noa@example.com');
    await page.getByLabel('טלפון').fill('050-1234567');
    await page.getByLabel('עיר').fill('חיפה');
    await page.getByLabel('רחוב').fill('הנמל');
    await page.getByLabel('מספר בית').fill('12');
    await page.getByRole('checkbox', { name: /קראתי ואני מסכים/ }).check();
    await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
    await expect(page).toHaveURL(/\/mock-pay\/ms_/);
    await page.getByRole('button', { name: 'אישור תשלום (מדומה)' }).click();
    await expect(page).toHaveURL(/\/order\/\d+\/$/);
    const lines = page.locator('ul.order-lines li');
    await expect(lines).toHaveCount(9);
    const ordered = (await lines.allTextContents()).map((t) => t.replace(/\s+× 1 · .*$/s, '').trim());
    expect([...ordered].sort()).toEqual([...want.values()].sort());
    await shot(page, 'order-nine-lines');
  });
});
