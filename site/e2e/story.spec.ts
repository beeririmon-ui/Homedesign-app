/**
 * Layer 1, the story, as real routes (briefs/site-interface-track-2026-11-07.md S1; built only without HD_PUBLIC=1):
 *  - /story/: the contents, every room × style; a picture only for a pair QA let in, type for the others
 *  - /story/living-room/nordic/: the opening frame develops and carries its title and story line with the visible test
 *    mark; no dot at rest, dots on movement; a dot or a list row opens "קנה את המראה" (a modal dialog, keyboard and
 *    screen reader), add to the test cart, Esc returns the focus; the tool entry opens the room engine; reduced motion;
 *    the phone's 4:5 crop
 *  - /story/living-room/modern-country/: an "almost" frame, marked so; boho: a frame QA's register let in
 *  - /story/living-room/mediterranean/: a pair whose frame QA has not let in is a typographic page, with no frame at all
 *  - /story/<room>/<style>/p/<product>/, layer 2: the card, the options (price, picture and address follow the
 *    choice), the empty close-up slot (G-ED.18), the frames that show it, the way into the tool at its slot
 *  - the test cart is one across the story pages; /test/story/ goes on to the Nordic living room
 *  - zero axe violations (WCAG 2.0/2.1 A + AA) on each kind of page, with the sheet open and with the cart open
 * Exact timings are in the evidence tool (tools/screens-story.ts).
 */
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { productSlug } from '@hd/shared/product-url';

type Ev = { t: number; name: string; detail?: unknown };
/** the hooks web/src/story/story.ts exposes */
declare global {
  interface Window {
    __story?: {
      events: Ev[];
      reduce: boolean;
      openSheet: (id: string) => Promise<void>;
      closeSheet: () => Promise<void>;
      showMarks: (frame: string) => void;
      cartCount: () => number;
    };
  }
}
const events = (page: Page) => page.evaluate(() => window.__story?.events ?? []) as Promise<Ev[]>;
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];
async function audit(page: Page, label: string) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0]).withTags(TAGS).analyze();
  const summary = r.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')} — ${v.help}`);
  expect(summary, `${label}\n${summary.join('\n')}`).toEqual([]);
}
const sheet = (page: Page) => page.locator('#st-sheet');
/** QA's register decides a frame's state (it moves round by round): the tests read what the build resolved */
const resolved = JSON.parse(readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), '../.generated/story.json'), 'utf8')) as Record<
  string,
  {
    states?: [string, string, string][];
    held?: { state: string; why_he: string }[];
    items?: Record<string, { dot: boolean; status?: string; variant_id?: string | null; units?: number }>;
  }
>;
const stateOf = (href: string) => resolved[href]?.states?.[0]?.[2] ?? null;
const MARK: Record<string, string> = { final_test: 'טיוטה / בדיקה', almost: 'טיוטה / בדיקה · כמעט מוכן', approved_for_site: 'בדיקה · מאושר לאתר' };
const NORDIC = '/story/living-room/nordic/';
const COUNTRY = '/story/living-room/modern-country/';
const WARM = '/story/living-room/warm-modern/';
const BOHO = '/story/living-room/boho/';
const MED = '/story/living-room/mediterranean/';
const JAPANDI = '/story/living-room/japandi/';

test.describe('the story contents', () => {
  test('every room, every house: a picture only where QA let a frame in, type for the rest, and links to each page', async ({ page }) => {
    await page.goto('/story/');
    await expect(page.locator('h1')).toHaveText('הבית');
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', /noindex/);
    await expect(page.locator('.st-room')).toHaveCount(9);
    await expect(page.locator('.st-room.is-next')).toHaveCount(8);
    const living = page.locator('#room-living-room .st-tile');
    await expect(living).toHaveCount(6);
    await expect(page.locator('#room-living-room .st-tile-pic')).toHaveCount(
      Object.entries(resolved).filter(([h, r]) => /^\/story\/living-room\/[^/]+\/$/.test(h) && r.states?.length).length,
    );
    await expect(page.locator('#room-living-room .st-tile-link')).toHaveCount(6);
    // every picture on the contents is a frame QA let in: the three typographic houses have none
    const srcs = await page.locator('img').evaluateAll((els) => els.map((e) => (e as HTMLImageElement).currentSrc || (e as HTMLImageElement).src));
    // a house whose frame is held (QA, or the points still to come) shows no picture of it
    const held = Object.entries(resolved)
      .filter(([h, r]) => /^\/story\/[^/]+\/[^/]+\/$/.test(h) && !r.states?.length)
      .map(([h]) => h.split('/')[3]);
    for (const s of srcs) for (const h of held) expect(s, s).not.toContain(`/${h}/`);
    await page.locator('#room-living-room .st-tile-link', { hasText: 'כפרי מודרני' }).click();
    await expect(page).toHaveURL(new RegExp(`${COUNTRY}$`));
    await expect(page.locator('h1')).toHaveText('קוטג׳ בבוקר גשום');
    await page.getByRole('link', { name: 'תוכן', exact: true }).click();
    await expect(page).toHaveURL(/\/story\/$/);
  });

  test('zero axe violations on the contents (1280)', async ({ page }) => {
    await page.goto('/story/');
    await page.waitForTimeout(800);
    await audit(page, 'contents');
  });
});

test.describe('the Nordic living room', () => {
  test('the opening develops, then the title; every frame carries the visible test mark', async ({ page }) => {
    await page.goto(NORDIC);
    await expect(page.locator('h1')).toHaveText('דירה ישנה, שמש של פברואר');
    await expect(page.locator('#frame-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    const evs = await events(page);
    for (const n of ['A:lqip', 'A:developed', 'A:title'])
      expect(
        evs.some((e) => e.name === n),
        n,
      ).toBe(true);
    await expect(page.locator('#frame-A .st-line')).toContainText('פברואר');
    await expect(page.locator('.st-draft')).toHaveCount(2);
    await expect(page.locator('#frame-A .st-draft')).toBeVisible();
    await expect(page.locator('#frame-A .st-draft')).toHaveText('טיוטה / בדיקה');
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', /noindex/);
    // the same room in the other houses: this one is marked, the others are links
    await expect(page.locator('#houses .st-tile')).toHaveCount(6);
    await expect(page.locator('#houses .st-tile[aria-current="page"]')).toContainText('נורדי');
    await expect(page.locator('#houses .st-tile-link')).toHaveCount(5);
  });

  test('a clean frame at rest; dots on movement; a dot opens the sheet with the card, adds to the test cart, Esc returns', async ({ page }) => {
    await page.goto(NORDIC);
    await expect(page.locator('#frame-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    await page.waitForTimeout(2200); // the first-entry hint has gone
    const dot = page.locator('#frame-A .st-mark').first().locator('.mag-dot');
    await expect(dot).toHaveCSS('opacity', '0');
    await page.mouse.move(640, 420);
    await page.mouse.move(660, 430);
    await expect(dot).toHaveCSS('opacity', '1', { timeout: 2_000 });
    // the charcoal cushion: priced, for sale, and its card photo is cached
    const cushion = page.locator('#frame-A .st-mark[data-item="A-5"]');
    await cushion.click();
    await expect(sheet(page)).toHaveAttribute('open', '');
    await expect(sheet(page)).toHaveClass(/is-on/);
    await expect(page.locator('#st-sheet-name')).toHaveText(/פשתן, פחם$/);
    await expect(page.locator('#st-sheet-name')).toBeFocused();
    await expect(page.locator('#st-sheet-detail')).toContainText('₪');
    await expect(page.locator('#st-sheet-img')).toBeVisible();
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('#st-add')).toHaveText('נוסף לסל');
    await expect(page.locator('#st-cart-count')).toHaveText('1');
    await expect(page.locator('#mag-live')).toContainText('נוסף לסל');
    await page.keyboard.press('Escape');
    await expect(sheet(page)).not.toHaveAttribute('open', '');
    await expect(cushion).toBeFocused();
  });

  test('the keyboard: Tab to a dot shows the dots, Enter opens the sheet, the page behind is inert, Esc back', async ({ page }) => {
    await page.goto(NORDIC);
    await expect(page.locator('#frame-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    // the first dot shown (at 1280 × 720 the pendant's would sit under the top band, so it is not offered there)
    const first = page.locator('#frame-A .st-mark:visible').first();
    const n = Number((await first.getAttribute('data-item'))!.split('-').pop());
    await first.focus();
    await expect(first.locator('.mag-dot')).toHaveCSS('opacity', '1');
    await page.keyboard.press('Enter');
    await expect(sheet(page)).toHaveAttribute('open', '');
    await expect(page.locator('#st-sheet-name')).toBeFocused();
    // Tab stays inside the modal sheet
    for (let i = 0; i < 8; i++) {
      await page.keyboard.press('Tab');
      // inside the sheet, or past its end (the browser's own UI): never on the page behind it
      expect(
        await page.evaluate(() => !document.activeElement || document.activeElement === document.body || !!document.activeElement.closest('#st-sheet')),
      ).toBe(true);
    }
    await page.locator('#st-next').click();
    await expect(page.locator('#st-pos')).toHaveText(new RegExp(`^${n + 1} מתוך`));
    await page.keyboard.press('Escape');
    await expect(sheet(page)).not.toHaveAttribute('open', '');
    expect(await page.evaluate(() => (document.activeElement as HTMLElement | null)?.dataset.item)).toBe(`A-${n + 1}`);
  });

  test('the list opens the same sheet; a product without a price says so, with no add button', async ({ page }) => {
    await page.goto(`${NORDIC}#list-A`);
    const rows = page.locator('#list-A .st-credit');
    await expect(rows).toHaveCount(13);
    await page.locator('#list-A .st-open', { hasText: /^מנורת תלייה דלעת/ }).click();
    await expect(sheet(page)).toHaveAttribute('open', '');
    await expect(page.locator('#st-add')).toBeHidden();
    await expect(page.locator('#st-why')).toContainText('המחיר עוד לא נקבע');
    await page.locator('#st-sheet-close').click();
    await expect(sheet(page)).not.toHaveAttribute('open', '');
    await expect(page.locator('#list-A .st-open', { hasText: /^מנורת תלייה דלעת/ })).toBeFocused();
    // the rug: QA "partly" in this frame, so no dot; listed, with the reason
    await expect(page.locator('#list-A .st-no-dot')).toHaveCount(1);
  });

  test('"עצב בעצמך" opens the room engine', async ({ page }) => {
    await page.goto(`${NORDIC}#tool`);
    await page.getByRole('link', { name: 'לעיצוב הסלון' }).click();
    await expect(page).toHaveURL(/\/rooms\/living-room\/\?from=%2Fstory%2Fliving-room%2Fnordic%2F$/);
    await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
  });

  for (const [w, h] of [
    [1280, 800],
    [1440, 900],
  ] as const)
    test(`every dot shown on the opening takes its own click at ${w}, the pendant's too (clear of the top band)`, async ({ page }) => {
      await page.setViewportSize({ width: w, height: h });
      await page.goto(NORDIC);
      await expect(page.locator('#frame-A')).toHaveClass(/is-title/, { timeout: 15_000 });
      await page.evaluate(() => window.__story!.showMarks('A'));
      await expect(page.locator('#frame-A .st-mark[data-item="A-1"]')).toBeVisible();
      const hits = await page.evaluate(() =>
        Array.from(document.querySelectorAll<HTMLElement>('#frame-A .st-mark'))
          .filter((m) => !m.hidden)
          .map((m) => {
            const r = m.getBoundingClientRect();
            const at = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
            return { item: m.dataset.item, hit: (at?.closest('.st-mark') as HTMLElement | null)?.dataset.item ?? at?.tagName ?? null };
          }),
      );
      expect(hits.length).toBeGreaterThanOrEqual(11);
      for (const x of hits) expect(x.hit, x.item).toBe(x.item);
    });

  test('reduced motion: the sheet only fades, nothing rises', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(NORDIC);
    await page.evaluate(() => window.__story!.openSheet('A-1'));
    await expect(sheet(page)).toHaveClass(/is-on/);
    expect(await sheet(page).evaluate((el) => getComputedStyle(el).transform)).toBe('none');
    expect(await page.locator('#frame-A .st-title-line').evaluate((el) => getComputedStyle(el).transform)).toBe('none');
  });

  test('zero axe violations: at rest, with the sheet open, with the cart open (1280)', async ({ page }) => {
    await page.goto(NORDIC);
    await expect(page.locator('#frame-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    await page.waitForTimeout(1200); // the title lines and the brand have finished fading in
    await audit(page, 'story at rest');
    await page.evaluate(() => window.__story!.openSheet('A-5'));
    await expect(sheet(page)).toHaveClass(/is-on/);
    await page.waitForTimeout(300);
    await audit(page, 'story, the sheet open');
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await page.keyboard.press('Escape');
    await expect(sheet(page)).not.toHaveAttribute('open', '');
    await page.locator('#st-cart-open').click();
    await expect(page.locator('#st-cart')).toHaveClass(/is-on/);
    await page.waitForTimeout(300);
    await audit(page, 'story, the cart open');
  });
});

test.describe('the other houses', () => {
  test("modern country: the mark says the register's state; every product QA called faithful has its dot", async ({ page }) => {
    await page.goto(COUNTRY);
    await expect(page.locator('#frame-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    await expect(page.locator('#frame-A .st-draft')).toHaveText(MARK[stateOf(COUNTRY)!]!);
    await expect(page.locator('#list-A .st-credit')).toHaveCount(7);
    // fix4: QA's register calls all seven faithful, so all seven have a dot
    await expect(page.locator('#frame-A .st-mark')).toHaveCount(7);
    await expect(page.locator('#list-A .st-no-dot')).toHaveCount(0);
    // the curtain is sold as the option the frame shows, and the credit says which
    await page.locator('#list-A .st-open', { hasText: 'סרט קפלים' }).click();
    await expect(page.locator('#st-sheet-notes')).toContainText('בתמונה: האפשרות "סרט קפלים"');
    await page.keyboard.press('Escape');
    // this house has no tool of its own yet: the way in goes to the Nordic living room, and says so
    await expect(page.locator('#st-tool')).toHaveText('לסלון בבית הנורדי');
    await expect(page.locator('#houses .st-tile[aria-current="page"]')).toContainText('כפרי מודרני');
    await page.waitForTimeout(800);
    await audit(page, 'modern country at rest');
  });

  test('japandi: QA has not let its frame in, so the page is type only, with no frame and no picture', async ({ page }) => {
    await page.goto(JAPANDI);
    await expect(page.locator('h1')).toHaveText('שעה כחולה, בית שקט');
    await expect(page.locator('.mag-stage')).toHaveCount(0);
    await expect(page.locator('.st-mark')).toHaveCount(0);
    await expect(page.locator('.st-type-status')).toContainText('הפריים עוד בבדיקה');
    const srcs = await page.locator('img').evaluateAll((els) => els.map((e) => (e as HTMLImageElement).src));
    for (const s of srcs) expect(s, s).not.toMatch(/\/japandi\//);
    // and the frame is not on the server at all
    expect((await page.request.get('/media/story/living-room/japandi/A/1920.webp')).status()).toBe(404);
    await page.waitForTimeout(800);
    await audit(page, 'japandi, typographic');
  });

  test('boho fin7: its frame, a dot where the register puts one, the mark of its state, two rust cushions', async ({ page }) => {
    await page.goto(BOHO);
    await expect(page.locator('h1')).toHaveText('בית אבן ישן בנמל, 16:00');
    await expect(page.locator('#frame-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    expect(resolved[BOHO]!.states![0]![1]).toBe('boho-A-fin7');
    await expect(page.locator('#frame-A .st-draft')).toHaveText(MARK[stateOf(BOHO)!]!);
    // the register says which products have a dot (v4: the planter's base is natural now, so all nine)
    await expect(page.locator('#frame-A .st-mark')).toHaveCount(Object.values(resolved[BOHO]!.items!).filter((x) => x.dot).length);
    await expect(page.locator('#list-A .st-credit')).toHaveCount(9);
    // register v4 (G-ED.6): the second rust cushion is a second unit of ours: the credit says so, and the look adds two
    const rust = page.locator('#list-A .st-credit', { hasText: 'חלודה' });
    await expect(rust).toContainText('בתמונה: שתי יחידות.');
    await page.evaluate((id) => window.__story!.openSheet(id), (await rust.getAttribute('data-item'))!);
    await expect(page.getByRole('dialog')).toContainText('בתמונה: שתי יחידות.');
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).toBeHidden();
    await expect(page.locator('#list-A .st-look-units')).toContainText('שתי יחידות');
    await page.locator('#look-A').click();
    const want = Object.values(resolved[BOHO]!.items!).filter((x) => x.dot && x.status === 'available' && x.variant_id);
    const units = want.reduce((n, x) => n + (x.units ?? 1), 0);
    expect(units).toBe(want.length + 1);
    await expect(page.locator('#st-cart-count')).toHaveText(String(units));
    await page.locator('#st-cart-open').click();
    await expect(page.locator('#st-cart-lines li', { hasText: 'חלודה' })).toContainText('2');
  });

  test('one test cart across the story pages, and the old prototype address goes on to the Nordic living room', async ({ page }) => {
    await page.goto('/test/story/');
    await expect(page).toHaveURL(new RegExp(`${NORDIC}$`));
    await page.evaluate(() => window.__story!.openSheet('A-5'));
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('#st-cart-count')).toHaveText('1');
    await page.goto(COUNTRY);
    await expect(page.locator('#st-cart-count')).toHaveText('1');
    await page.locator('#st-cart-open').click();
    await expect(page.locator('#st-cart-lines li')).toHaveCount(1);
    await expect(page.locator('#st-cart-lines')).toContainText('פחם');
    await page.keyboard.press('Escape');
    await page.goto('/story/');
    await expect(page.locator('#st-cart-count')).toHaveText('1');
  });
});

/** S7: the site's real checkout, filled and paid with the mock payment, to its order page */
async function orderOnSite(page: Page): Promise<void> {
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
}
const DETAIL = (style: string, product: string) => `/story/living-room/${style}/p/${productSlug(product)}/`;
test.describe('the detail page (layer 2, "הפרט")', () => {
  test('the sheet leads to it: the card, the price, the empty close-up slot, the frame it came from, and the test cart', async ({ page }) => {
    await page.goto(NORDIC);
    await page.evaluate(() => window.__story!.openSheet('A-5'));
    await page.locator('#st-page').click();
    await expect(page).toHaveURL(new RegExp(`${DETAIL('nordic', 'cushions-cj-linen-look-charcoal')}$`));
    await expect(page.locator('h1')).toHaveText('ציפית כרית במראה פשתן, פחם');
    await expect(page.locator('#st-pd-price')).toContainText('₪');
    await expect(page.locator('#st-pd-img')).toBeVisible();
    // G-ED.18: the close-up of the house has its slot, honest while QA has let none in
    await expect(page.locator('#st-pd-cu-empty')).toBeVisible();
    await expect(page.locator('#st-pd-cu-empty')).toContainText('תקריב באור של הבית');
    await expect(page.locator('#here .st-tile-link').first()).toHaveAttribute('href', `${NORDIC}#frame-A`);
    await expect(page.locator('nav[aria-label="פירורי לחם"] [aria-current="page"]')).toHaveText('ציפית כרית במראה פשתן, פחם');
    await page.locator('#st-pd-add').click();
    await expect(page.locator('#st-pd-add')).toHaveText('נוסף לסל');
    await expect(page.locator('#st-cart-count')).toHaveText('1');
    await page.locator('#here .st-tile-link').first().click();
    await expect(page).toHaveURL(new RegExp(`${NORDIC}#frame-A$`));
    await expect(page.locator('#st-cart-count')).toHaveText('1');
  });

  test('options: the choice moves the price, the picture and the address; the story option is one step back', async ({ page }) => {
    const href = DETAIL('nordic', 'cushions-cj-boucle-teddy');
    await page.goto(href);
    await expect(page.locator('h1')).toHaveText('ציפית כרית בוקלה, לבן חם');
    await expect(page.locator('#st-pd-price')).toHaveText(/59/);
    await expect(page.locator('#st-pd-story-note')).toBeHidden();
    await page.locator('.st-pd-axis[data-axis="size"] label', { hasText: '30×50' }).click();
    await expect(page.locator('#st-pd-price')).toHaveText(/49/);
    // the title follows the choice (design notes §6): the 30×50 has its own shape name, and never a size
    await expect(page.locator('h1')).toHaveText('ציפית כרית מותן בוקלה, לבן חם');
    await expect(page).toHaveURL(/size=30x50/);
    await expect(page.locator('#st-pd-story-note')).toContainText('בסיפור מוצגת האפשרות');
    await expect(page.locator('[data-spec="מידות"]')).toContainText('30×50');
    // the address names the option: a reload keeps it
    await page.reload();
    await expect(page.locator('#st-pd-price')).toHaveText(/49/);
    await expect(page.locator('.st-pd-axis[data-axis="size"] input:checked')).toHaveValue('30x50');
    await page.locator('#st-pd-add').click();
    // S7: the cart is the server's: the count follows its answer
    await expect(page.locator('#st-cart-count')).toHaveText('1');
    await page.locator('#st-cart-open').click();
    await expect(page.locator('#st-cart-lines')).toContainText('30×50');
    await page.keyboard.press('Escape');
    await page.locator('#st-pd-back').click();
    await expect(page.locator('#st-pd-price')).toHaveText(/59/);
    await expect(page.locator('h1')).toHaveText('ציפית כרית בוקלה, לבן חם');
    await expect(page).toHaveURL(new RegExp(`${href}$`));
    // the same product in another house
    await page.goto(DETAIL('nordic', 'table-runner-cj-linen-look-sage-fringe'));
    await expect(page.locator('#elsewhere .st-tile-link')).toHaveAttribute('href', DETAIL('modern-country', 'table-runner-cj-linen-look-sage-fringe'));
  });

  test('a product without a price, and one not sold now: no add button, the reason instead', async ({ page }) => {
    await page.goto(DETAIL('nordic', 'pendant-cj-silk-ribbed-pumpkin-40'));
    await expect(page.locator('#st-pd-add')).toBeHidden();
    await expect(page.locator('#st-pd-why')).toContainText('המחיר עוד לא נקבע');
    await expect(page.locator('#st-pd-price')).toBeHidden();
    await page.goto(DETAIL('nordic', 'rug-cj-braided-wool-natural'));
    await expect(page.locator('#st-pd-add')).toBeHidden();
    await expect(page.locator('#st-pd-why')).toHaveText('המלאי אינו זמין כעת.');
  });

  test('"לנסות בחדר" opens the room engine on the product\'s slot', async ({ page }) => {
    await page.goto(DETAIL('nordic', 'cushions-cj-boucle-teddy'));
    // QA on S3–S5 (ה3): the way in carries the way back
    await expect(page.locator('#st-pd-try')).toHaveAttribute('href', '/rooms/living-room/?slot=cushions&option=1&from=%2Fstory%2Fliving-room%2Fnordic%2F');
    await page.locator('#st-pd-try').click();
    await expect(page).toHaveURL(/\/rooms\/living-room\/\?slot=cushions&option=1&from=/);
    await expect(page.getByRole('dialog').first()).toBeVisible({ timeout: 20_000 });
    await expect(page.locator('#back-to-story')).toHaveAttribute('href', '/story/living-room/nordic/');
    // a house whose tool is still being built says so
    await page.goto(DETAIL('boho', 'cushions-cj-washed-cotton-frayed'));
    await expect(page.locator('#st-pd-try-none')).toContainText('בבנייה');
  });

  test('zero axe violations on a detail page with options (1280), and after a choice', async ({ page }) => {
    await page.goto(DETAIL('nordic', 'cushions-cj-boucle-teddy'));
    await page.waitForTimeout(800);
    await audit(page, 'detail at rest');
    await page.locator('.st-pd-axis[data-axis="color"] label').first().click();
    await page.waitForTimeout(300);
    await audit(page, 'detail after a choice');
  });
});

test.describe('the detail page, after the designer (§6)', () => {
  test("no supplier photo: the product's crop from the frame says so; another option shows its colour, never the crop", async ({ page }) => {
    await page.goto(DETAIL('modern-country', 'curtains-aliexpress-linen-blend-s-fold-180502'));
    await expect(page.locator('#st-pd-img')).toHaveClass(/is-frame/);
    await expect(page.locator('#st-pd-photo-cap')).toContainText('זו לא תמונת מוצר');
    await expect(page.locator('#st-pd-photo-cap')).toContainText('סרט קפלים');
    // never enlarged: drawn no wider than its own pixels
    const [drawn, own] = await page.locator('#st-pd-img').evaluate((el: HTMLImageElement) => [el.getBoundingClientRect().width, el.naturalWidth]);
    expect(drawn).toBeLessThanOrEqual(own + 0.5);
    await page.locator('.st-pd-axis[data-axis="style"] label', { hasText: 'ווים' }).click();
    await expect(page.locator('#st-pd-img')).toBeHidden();
    await expect(page.locator('#st-pd-none')).toContainText('אין עדיין צילום לאפשרות הזו');
    await expect(page.locator('h1')).toHaveText('זוג וילונות שקופים במראה פשתן, ווים');
  });

  test("QA on S2: a dot of another option opens the detail page on that option (the Mediterranean's terracotta cushion)", async ({ page }) => {
    await page.goto(MED);
    await page.evaluate(() => window.__story!.openSheet('A-7'));
    await expect(page.locator('#st-page')).toHaveAttribute(
      'href',
      new RegExp(`/p/${productSlug('cushions-cj-washed-cotton-frayed')}/\\?size=50x50&other=earthy-orange$`),
    );
    await page.locator('#st-page').click();
    await expect(page.locator('h1')).toHaveText('ציפית כרית כותנה רחוצה עם שוליים פרומים, טרקוטה');
    await expect(page.locator('#st-pd-story-note')).toContainText('לבן');
  });

  test('a set sells as a set by default, and as a single piece where the supplier offers one (SET1)', async ({ page }) => {
    await page.goto(DETAIL('nordic', 'candle-holders-cj-travertine-pedestal'));
    await expect(page.locator('input[name="st-pack"][value="set"]')).toBeChecked();
    await page.locator('label', { has: page.locator('input[name="st-pack"][value="unit"]') }).click();
    await expect(page.locator('#st-pd-price')).toContainText('משוער');
    await expect(page.locator('#st-pd-credit')).toContainText('יחידה בודדת');
    await page.locator('#st-pd-add').click();
    await page.locator('#st-cart-open').click();
    await expect(page.locator('#st-cart-lines')).toContainText('יחידה בודדת');
  });
});

test.describe('the shop (S4)', () => {
  test('"קנה את המראה" whole: every product for sale, once; the cart edits a line; the rest is named', async ({ page }) => {
    await page.goto(`${NORDIC}#list-A`);
    await expect(page.locator('#list-A .st-look-left')).toContainText('בלי מחיר');
    await page.locator('#look-A').click();
    await expect(page.locator('#st-cart-count')).toHaveText('10');
    await expect(page.locator('#mag-live')).toContainText('נוספו לסל 10 פריטים');
    await page.locator('#st-cart-open').click();
    const lines = page.locator('#st-cart-lines .st-cart-line');
    await expect(lines).toHaveCount(10);
    const first = lines.first();
    await first.getByRole('button', { name: /^הגדלת הכמות/ }).click();
    await expect(page.locator('#st-cart-count')).toHaveText('11');
    await expect(lines.first().locator('output')).toHaveText('2');
    // the focus stays on the control that was used
    await expect(lines.first().getByRole('button', { name: /^הגדלת הכמות/ })).toBeFocused();
    await lines
      .first()
      .getByRole('button', { name: /^הסרה מהסל/ })
      .click();
    await expect(lines).toHaveCount(9);
    await expect(page.locator('#st-cart-count')).toHaveText('9');
    await audit(page, 'the cart, edited');
  });

  test('S7: from the whole look to the order, through the shop’s own cart and its real checkout', async ({ page }) => {
    await page.goto(`${BOHO}#list-A`);
    await page.locator('#look-A').click();
    await expect(page.locator('#st-cart-count')).not.toHaveText('0');
    const n = Number(await page.locator('#st-cart-count').textContent());
    await page.locator('#st-cart-open').click();
    await page.locator('#st-cart-pay').click();
    // the real checkout of the site, with the same cart (the API's, by the id in 'hd.cart')
    await expect(page).toHaveURL(/\/checkout\/$/);
    await expect(page.locator('.cart-count')).toHaveText(String(n));
    await expect(page.locator('.summary')).toContainText('חלודה');
    await orderOnSite(page);
    await expect(page.locator('.order-steps [aria-current="step"]')).toHaveText(/התקבלה|בהכנה/, { timeout: 20_000 });
    await expect(page.locator('body')).toContainText('חלודה');
    // back in the story the cart starts again: the ordered one is closed on the server
    await page.goto(BOHO);
    await expect(page.locator('#st-cart-count')).toHaveText('0');
  });

  test('PRE1 / MED1 in the tool: an option out of stock stays on the wheel, said, and never sold', async ({ page }) => {
    await page.goto('/rooms/living-room/?slot=rug&option=1');
    const dialog = page.getByRole('dialog').first();
    await expect(dialog).toBeVisible({ timeout: 20_000 });
    const card = dialog.locator('.arc-card').first();
    await expect(card.locator('.oos-tag')).toHaveText('אינו במלאי');
    await expect(card).toHaveAttribute('aria-label', /המלאי אינו זמין כעת$/);
    await expect(dialog.getByText('המלאי אינו זמין כעת', { exact: true })).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'הוספה לסל' })).toHaveCount(0);
  });
});

test.describe('the shop after QA on S4', () => {
  test('S7: the server sells only what is for sale, in 1–20 whole units (PRE1; QA on S3–S5, ת3)', async ({ page }) => {
    const rug = Object.values(resolved[NORDIC]!.items!).find((x) => x.status === 'unavailable' && x.variant_id);
    const sold = Object.values(resolved[NORDIC]!.items!).find((x) => x.status === 'available' && x.variant_id)!;
    const cart = (await (await page.request.post('/api/cart')).json()) as { id: string };
    const put = (variant_id: string, qty: unknown) => page.request.put(`/api/cart/${cart.id}/items`, { data: { variant_id, pack: 'set', qty } });
    if (rug) expect((await put(rug.variant_id!, 1)).ok()).toBe(false);
    for (const qty of [-2, 2.5, '3', 21, 999]) expect((await put(sold.variant_id!, qty)).status(), String(qty)).toBe(422);
    const ok = (await (await put(sold.variant_id!, 20)).json()) as { lines: { qty: number }[]; subtotal_agorot: number };
    expect(ok.lines[0]!.qty).toBe(20);
    expect(ok.subtotal_agorot).toBeGreaterThan(0);
  });

  test("the whole look twice adds nothing the second time; another tab's order empties this one", async ({ page, context }) => {
    await page.goto(`${NORDIC}#list-A`);
    await page.locator('#look-A').click();
    await expect(page.locator('#st-cart-count')).not.toHaveText('0');
    const n = await page.locator('#st-cart-count').textContent();
    await page.waitForTimeout(2700); // the button's confirmation has gone back to its label
    await page.locator('#look-A').click();
    await expect(page.locator('#look-A')).toHaveText('המראה כבר בסל');
    await expect(page.locator('#st-cart-count')).toHaveText(n!);
    // another tab orders on the site: this tab's count follows, and its next add starts a new cart
    const other = await context.newPage();
    await other.goto('/checkout/');
    await orderOnSite(other);
    await expect(other.locator('.order-steps')).toBeVisible({ timeout: 20_000 });
    await expect(page.locator('#st-cart-count')).toHaveText('0');
    await page.evaluate(() => window.__story!.openSheet('A-5'));
    await page.locator('#st-add').click();
    await expect(page.locator('#st-cart-count')).toHaveText('1');
  });

  test('the triptych sells as its set of three different prints only: no print to choose, no single print', async ({ page }) => {
    await page.goto(DETAIL('nordic', 'framed-art-aliexpress-minimal-geometric-triptych-prints'));
    await expect(page.locator('.st-pd-axis[data-axis="color"]')).toHaveCount(0);
    await expect(page.locator('#st-pd-pack')).toHaveCount(0);
    await expect(page.locator('#detail .st-notes')).toContainText('שלושה הדפסים שונים');
  });

  test('the build read the highest QA register version (rebuild when a new one lands)', async ({ page }) => {
    const dir = resolve(dirname(fileURLToPath(import.meta.url)), '../../qa/reports');
    const top = Math.max(
      ...readdirSync(dir)
        .filter((n) => /^ged-register-.*\.json$/.test(n))
        .map((n) => (JSON.parse(readFileSync(resolve(dir, n), 'utf8')) as { version: number }).version),
    );
    await page.goto('/story/');
    await expect(page.locator('meta[name="hd-qa-register"]')).toHaveAttribute('content', String(top));
  });
});

test.describe('from the story into the tool (S3)', () => {
  test('the Nordic house: the tool opens with the way back to the story', async ({ page }) => {
    await page.goto(`${NORDIC}#tool`);
    await expect(page.locator('#st-tool')).toHaveAttribute('href', '/rooms/living-room/?from=%2Fstory%2Fliving-room%2Fnordic%2F');
    await page.locator('#st-tool').click();
    await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
    await expect(page.locator('#back-to-story')).toHaveAttribute('href', NORDIC);
    // S5: it sits on the stage, inside the frame, a 44 px target at the top end
    const stage = (await page.locator('section.stage').boundingBox())!;
    const back = (await page.locator('#back-to-story').boundingBox())!;
    expect(back.y - stage.y).toBeLessThan(40);
    expect(back.height).toBeGreaterThanOrEqual(44);
    expect(back.x).toBeLessThan(stage.x + stage.width / 2); // the end is the left in RTL
    // a "from" that is not a story page is ignored
    await page.goto('/rooms/living-room/?from=https%3A%2F%2Fexample.com%2F');
    await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
    await expect(page.locator('#back-to-story')).toHaveCount(0);
  });

  test("warm modern: the house's own tool, a draft, and the soft switch between two houses at one camera", async ({ page }) => {
    await page.goto(`${WARM}#tool`);
    await page.locator('#st-tool-draft').click();
    await expect(page).toHaveURL(/\/story\/living-room\/warm-modern\/tool\/$/);
    await expect(page.locator('.st-td .st-draft')).toHaveText('טיוטה / בדיקה · הכלי בבנייה');
    const warm = page.locator('.st-td-house[data-house="warm-modern"]');
    await expect(warm.locator('.st-td-layer')).toHaveCount(3);
    // QA on S3–S5 (ת5): the other house is not fetched until it is asked for
    const nordicSrc = () =>
      page
        .locator('.st-td-house[data-house="nordic"] img')
        .first()
        .evaluate((i: HTMLImageElement) => i.getAttribute('src'));
    expect(await nordicSrc()).toBeNull();
    expect(await warm.locator('.st-td-layer.is-multiply').evaluate((el) => getComputedStyle(el).mixBlendMode)).toBe('multiply');
    // every layer of both houses in the same frame: one box
    const boxes = await page.locator('.st-td-layer img').evaluateAll((els) => els.map((e) => JSON.stringify(e.getBoundingClientRect())));
    expect(new Set(boxes).size).toBe(1);
    expect(await warm.evaluate((el) => getComputedStyle(el).transitionDuration)).toBe('1s');
    await page.locator('.st-td-btn[data-house="nordic"]').click();
    await expect(page.locator('.st-td-btn[data-house="nordic"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('.st-td-house[data-house="nordic"]')).toHaveClass(/is-on/);
    await expect(warm).toHaveAttribute('aria-hidden', 'true');
    await expect(page).toHaveURL(/\?house=nordic$/);
    await page.waitForTimeout(1200);
    await audit(page, 'the draft tool, the Nordic house shown');
  });

  test('reduced motion: the switch is a short dissolve, nothing moves', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/story/living-room/warm-modern/tool/?house=nordic');
    await expect(page.locator('.st-td-house[data-house="nordic"]')).toHaveClass(/is-on/);
    expect(
      await page
        .locator('.st-td-house')
        .first()
        .evaluate((el) => getComputedStyle(el).transitionDuration),
    ).toBe('0.3s');
  });
});

test.describe('the story on a phone (400)', () => {
  test.use({ viewport: { width: 400, height: 800 }, hasTouch: true, isMobile: true });

  test('the 4:5 crop at full width, dots inside it, the sheet from the bottom, zero axe violations', async ({ page }) => {
    await page.goto(NORDIC);
    const stage = page.locator('#frame-A .mag-stage');
    const box = (await stage.boundingBox())!;
    expect(Math.round(box.width)).toBe(400);
    expect(Math.round(box.height)).toBe(500);
    // every dot shown on the phone sits inside the crop; a dot the crop does not carry is not offered
    for (const m of await page.locator('#frame-A .st-mark:visible').all()) {
      const b = (await m.boundingBox())!;
      expect(b.x).toBeGreaterThanOrEqual(box.x - 1);
      expect(b.x + b.width).toBeLessThanOrEqual(box.x + box.width + 1);
    }
    await expect(page.locator('#frame-A .st-no-phone')).toHaveCount(3);
    // Nordic B's throw: the dot placed by hand on the fold (frame u 0.765, v 0.677), not on the armchair's seat
    const throwDot = page.locator('#frame-B .st-mark[data-item="B-4"]');
    expect(await throwDot.evaluate((el) => [el.style.getPropertyValue('--pu'), el.style.getPropertyValue('--pv')])).toEqual(['0.8225', '0.677']);
    await expect(page.locator('#frame-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    await page.waitForTimeout(1200);
    await audit(page, 'phone at rest');
    await page.locator('#frame-A .st-mark:visible').first().tap();
    await expect(sheet(page)).toHaveClass(/is-on/);
    await page.waitForTimeout(300); // the 8 px rise has landed
    const s = (await sheet(page).boundingBox())!;
    expect(Math.round(s.y + s.height)).toBe(800);
    await page.waitForTimeout(300);
    await audit(page, 'phone, the sheet open');
  });

  test('the contents, a typographic page and a detail page fit the phone: no sideways scroll, zero axe violations', async ({ page }) => {
    for (const path of ['/story/', MED, DETAIL('modern-country', 'curtains-aliexpress-linen-blend-s-fold-180502')]) {
      await page.goto(path);
      await page.waitForTimeout(800);
      expect(await page.evaluate(() => document.documentElement.scrollWidth), path).toBeLessThanOrEqual(400);
      await audit(page, `phone ${path}`);
    }
  });
});

test.describe('the magazine design system (S5)', () => {
  test('neutral addresses: no supplier in a product address; the old address moves to the new one', async ({ page }) => {
    const slug = productSlug('vase-aliexpress-vintage-distressed-clay-vase-589009');
    expect(slug).not.toMatch(/aliexpress|cj|zendrop|589009/);
    // the story's detail page, by its old address (the card id)
    await page.goto('/story/living-room/nordic/p/vase-aliexpress-vintage-distressed-clay-vase-589009/');
    await expect(page).toHaveURL(new RegExp(`/story/living-room/nordic/p/${slug}/$`));
    await expect(page.locator('h1')).toContainText('כד');
    // every link on a story page names products by the neutral address
    await page.goto(NORDIC);
    const hrefs = [...(await page.content()).matchAll(/\/story\/[a-z-]+\/[a-z-]+\/p\/[^/"?]+\//g)].map((m) => m[0]);
    expect(hrefs.length).toBeGreaterThan(5);
    expect(hrefs.filter((h) => /-(cj|aliexpress|zendrop)-|\d{6}/.test(h))).toEqual([]);
    // the shop: the old address by card id moves too
    await page.goto('/p/vase-cj-textured-white-stoneware/');
    await expect(page).toHaveURL(/\/p\/vase-textured-white-stoneware-[0-9a-z]{5}\/$/);
    await expect(page.locator('h1')).toBeVisible();
  });

  test('a frame that does not load says so on paper; the list under it is whole', async ({ page }) => {
    await page.route(/\/media\/story\/living-room\/nordic\/A\/[^/?]*\.(webp|avif|jpg)(\?|$)/, (r) => r.abort());
    await page.goto(NORDIC);
    await expect(page.locator('#frame-A .st-img-error')).toContainText('התמונה לא נטענה');
    await page.setViewportSize({ width: 1200, height: 800 }); // a layout after the failure keeps the dots off
    await expect(page.locator('#frame-A .st-mark:visible')).toHaveCount(0);
    await expect(page.locator('#list-A .st-credit').first()).toBeVisible();
    await page.waitForTimeout(800); // the title's develop transition has settled
    await audit(page, 'a frame that did not load');
  });
});
