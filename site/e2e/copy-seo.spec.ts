/**
 * S15 (briefs/site-s15-copy-seo-2026-11-11.md; master-designer, docs/proposals/your-room-copy-2026-11-11.md):
 *  - SEO per house (§4): each house's room page has its own title, description, canonical and ItemList. The bug it
 *    fixes: the canonical of ?style=warm-modern named the Nordic page, and its ItemList listed the Nordic products.
 *  - The meta description of a product page is cut where a sentence ends, never in the middle of a word (§5).
 *  - The words on the stage (§2, §5): the customer's names of the sets, "כריות ושמיכה" without the catalog's "(סט)",
 *    "גרסאות" or "סטים" and never the studio's "וריאציות", the house's line under the room and its description.
 * Runs on the build behind the flag (both houses); the public build is checked by tools/check-image-rights.ts and the
 * evidence run (qa/reports/2026-11-07-site-track/s15/).
 */
import { test, expect, type APIRequestContext } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { metaDescription } from '@hd/shared/meta-text';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const gen = <T>(f: string): T => JSON.parse(readFileSync(resolve(SITE, '.generated', f), 'utf8')) as T;
type Pub = {
  rooms: { id: string; slots: { id: string; name_he: string }[] }[];
  products: { id: string; room: string; name_he: string; description_he: string }[];
};
const pub = gen<Pub>('catalog.public.json');
const house = gen<{
  place_he: string;
  intro_he: string;
  alt_he: string;
  room: { slots: { id: string; name_he: string }[] };
  sets: { label_he: string; items: { product_id: string | null }[] }[];
  products: { id: string; name_he: string }[];
}>('house.living-room.warm-modern.json');
const ORIGIN = 'https://example.co.il';
const HOUSE = '/rooms/living-room/?style=warm-modern';

/** the page's <head>: title, meta description, canonical and its JSON-LD blocks */
async function headOf(request: APIRequestContext, url: string) {
  const r = await request.get(url);
  expect(r.status(), url).toBe(200);
  const html = await r.text();
  const unesc = (s: string) => s.replace(/&#(\d+);/g, (_, n: string) => String.fromCharCode(Number(n)));
  const ld = [...html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g)].map((m) => JSON.parse(m[1]!) as Record<string, unknown>);
  return {
    title: unesc(/<title>([^<]*)<\/title>/.exec(html)?.[1] ?? ''),
    description: unesc(/<meta name="description" content="([^"]*)"/.exec(html)?.[1] ?? ''),
    canonical: unesc(/<link rel="canonical" href="([^"]*)"/.exec(html)?.[1] ?? ''),
    list: ld.find((o) => o['@type'] === 'ItemList') as { itemListElement: { position: number; name: string; url?: string }[] } | undefined,
    crumbs: ld.find((o) => o['@type'] === 'BreadcrumbList') as { itemListElement: { name: string; item: string }[] } | undefined,
  };
}

test.describe('SEO per house (§4)', () => {
  test('the Nordic page: its own title and description, its canonical, its products', async ({ request }) => {
    const h = await headOf(request, '/rooms/living-room/');
    expect(h.title).toBe('סלון נורדי: לבן חם, אלון ואור חורף · הבית');
    expect(h.description).toBe(
      'סלון נורדי באור חורף של שלוש אחר הצהריים, בלבן חם, בשיבולת שועל ובאלון בהיר. נוגעים בפריט, מחליפים גרסה ורואים את החדר מתעדכן.',
    );
    expect(h.canonical).toBe(`${ORIGIN}/rooms/living-room/`);
    const nordic = pub.products.filter((p) => p.room === 'living-room');
    expect(h.list!.itemListElement.map((i) => i.name)).toEqual(nordic.map((p) => p.name_he));
    for (const i of h.list!.itemListElement) expect(i.url, i.name).toMatch(/^https:\/\/example\.co\.il\/p\/[a-z0-9-]+\/$/);
    // a style that is not a house is the Nordic page, with the Nordic canonical
    expect((await headOf(request, '/rooms/living-room/?style=no-such-house')).canonical).toBe(`${ORIGIN}/rooms/living-room/`);
  });

  test('the warm-modern page: its own canonical (the bug), its title and description, and only its own products', async ({ request }) => {
    const h = await headOf(request, HOUSE);
    expect(h.title).toBe('סלון מודרני חם: בוקלה, אגוז ואבן · הבית');
    // phase 1: only the set of cushions and throw is swapped there, so the second sentence says that
    expect(house.room.slots).toHaveLength(1);
    expect(h.description).toBe(
      'סלון מודרני חם: קירות טיח, ספת בוקלה, שולחן קפה מאגוז וספסל אבן בחלון, באור חורף של אחר הצהריים. בוחרים סט כריות ושמיכה ורואים אותו על הספה.',
    );
    expect(h.canonical).toBe(`${ORIGIN}${HOUSE}`);
    expect(h.crumbs!.itemListElement.at(-1)).toEqual({ '@type': 'ListItem', position: 2, name: 'סלון מודרני חם', item: `${ORIGIN}${HOUSE}` });
    // the ItemList: the pieces of the house's sets, each product once, in the wheel's order; never a Nordic-only product
    const ids = [...new Set(house.sets.flatMap((s) => s.items.flatMap((i) => (i.product_id ? [i.product_id] : []))))];
    const names = ids.map((id) => house.products.find((p) => p.id === id)!.name_he);
    expect(h.list!.itemListElement.map((i) => i.name)).toEqual(names);
    const nordicOnly = pub.products.filter((p) => p.room === 'living-room' && !ids.includes(p.id)).map((p) => p.name_he);
    for (const i of h.list!.itemListElement) expect(nordicOnly, i.name).not.toContain(i.name);
    // a url only where the shop has the product's page, and that page answers
    for (const i of h.list!.itemListElement.filter((x) => x.url)) expect((await request.get(new URL(i.url!).pathname)).status(), i.url).toBe(200);
    // the sitemap lists the house's page beside the Nordic one
    const sitemap = await (await request.get('/sitemap.xml')).text();
    expect(sitemap).toContain(`<loc>${ORIGIN}/rooms/living-room/</loc>`);
    expect(sitemap).toContain(`<loc>${ORIGIN}${HOUSE}</loc>`);
  });

  test('in the browser: the title follows the house, the switch included', async ({ page }) => {
    await page.goto(HOUSE);
    await expect(page).toHaveTitle('סלון מודרני חם: בוקלה, אגוז ואבן · הבית');
    await page.getByRole('group', { name: 'הבית' }).locator('button[data-house="nordic"]').click();
    await expect(page).toHaveURL(/\/rooms\/living-room\/$/);
    await expect(page).toHaveTitle('סלון נורדי: לבן חם, אלון ואור חורף · הבית');
  });
});

test('every product page: its meta description is whole sentences of its description, never a cut word (§5)', async ({ request }) => {
  test.setTimeout(120_000);
  let cut = 0;
  for (const p of pub.products) {
    const h = await headOf(request, `/p/${p.id}/`);
    expect(h.description, p.id).toBe(metaDescription(p.description_he));
    expect(h.description.length, p.id).toBeLessThanOrEqual(155);
    if (h.description !== p.description_he) {
      cut++;
      const kept = h.description.replace(/…$/, '');
      expect(p.description_he.startsWith(kept), p.id).toBe(true);
      expect(p.description_he.charAt(kept.length), `${p.id}: the cut is at a word's end`).toMatch(/[\s,;:·–-]/);
    }
  }
  const morandi = pub.products.find((p) => p.id.startsWith('framed-art-morandi-triptych-sage'));
  if (morandi) {
    const h = await headOf(request, `/p/${morandi.id}/`);
    expect(h.description).toBe(
      'שלושה הדפסים מופשטים במרקם מובלט על גב סיבית, כל אחד במסגרת שחורה דקה. חמישה דגמים בארבע מידות, מ-40×60 עד 70×90 ס"מ לכל הדפס.',
    );
  }
  console.log(`product pages: ${pub.products.length}, meta descriptions cut at a sentence: ${cut}`);
});

test.describe('the words on the stage (§2, §5)', () => {
  test('the Nordic house: "כריות ושמיכה" and "3 גרסאות" on the wheel; no "(סט)" and no "וריאציות" on the page', async ({ page }) => {
    await page.goto('/rooms/living-room/');
    const spot = page.locator('button.hotspot[data-slot="cushions"]');
    await expect(spot).toBeAttached({ timeout: 20_000 });
    await expect(spot).toHaveAttribute('aria-label', /^כריות ושמיכה: .+\. פתיחת 3 גרסאות$/);
    await spot.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog', { name: 'כריות ושמיכה' });
    await expect(dialog).toBeVisible({ timeout: 15_000 });
    await expect(dialog.locator('.picker-head .eyebrow')).toHaveText('3 גרסאות');
    await expect(dialog.getByRole('button', { name: 'הגרסה הבאה' })).toBeVisible();
    await dialog.getByRole('button', { name: 'סגירה וחזרה לחדר בלי שינוי' }).click();
    const text = await page.locator('body').innerText();
    expect(text).not.toContain('(סט)');
    expect(text).not.toMatch(/וריאצי/);
    const sr = await page.locator('.slot-list .sr-only').allTextContents();
    expect(sr.join(' ')).not.toMatch(/וריאצי/);
    expect(sr.join(' ')).toContain('(3 גרסאות)');
  });

  test('the warm-modern house: the set names, "3 סטים", its line under the room and its description', async ({ page }) => {
    await page.setExtraHTTPHeaders({ 'cf-connecting-ip': '198.51.100.150' });
    await page.goto(HOUSE);
    await expect(page.locator('section.stage[data-house="warm-modern"]')).toBeVisible({ timeout: 20_000 });
    await expect(page.locator('canvas.room-canvas')).toHaveAttribute('aria-label', house.alt_he);
    expect(house.alt_he).not.toMatch(/מתחלפות|סטים/);
    await expect(page.locator('.room-intro p')).toHaveText(house.intro_he);
    expect(house.intro_he).not.toMatch(/גלגל|בשלב הבא/);
    const spot = page.locator('button.hotspot[data-slot="cushions"]');
    await expect(spot).toBeAttached({ timeout: 20_000 });
    await expect(spot).toHaveAttribute('aria-label', `כריות ושמיכה: ${house.sets[0]!.label_he}. פתיחת 3 סטים`);
    await spot.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog', { name: 'כריות ושמיכה' });
    await expect(dialog).toBeVisible({ timeout: 15_000 });
    await expect(dialog.locator('.picker-head .eyebrow')).toHaveText('3 סטים');
    expect(house.sets.map((s) => s.label_he)).toEqual(['סט קאמל ופקאן', 'סט לבן חם ותה חלב', 'סט קפה כהה וחימר']);
    const radios = dialog.getByRole('radio');
    for (const [i, s] of house.sets.entries()) await expect(radios.nth(i)).toHaveAttribute('aria-label', `${i + 1} מתוך 3: ${s.label_he}`);
    await expect(dialog.locator('.set-items')).toHaveAttribute('aria-label', `בסט ${house.sets[0]!.items.length} פריטים`);
    // a piece's own button: "לסל: {name} בלבד" for a screen reader
    const add = dialog.locator('.set-add').first();
    if (await add.count()) expect(await add.evaluate((b) => b.textContent)).toMatch(/^לסל: .+ בלבד$/);
    const body = await dialog.innerText();
    expect(body).not.toMatch(/סט [ABC]\b|וריאצי|\(סט\)|עוד בלי מחיר/);
  });
});
