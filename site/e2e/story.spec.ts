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
import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

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
const NORDIC = '/story/living-room/nordic/';
const COUNTRY = '/story/living-room/modern-country/';
const BOHO = '/story/living-room/boho/';
const MED = '/story/living-room/mediterranean/';

test.describe('the story contents', () => {
  test('every room, every house: a picture only where QA let a frame in, type for the rest, and links to each page', async ({ page }) => {
    await page.goto('/story/');
    await expect(page.locator('h1')).toHaveText('הבית');
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', /noindex/);
    await expect(page.locator('.st-room')).toHaveCount(9);
    await expect(page.locator('.st-room.is-next')).toHaveCount(8);
    const living = page.locator('#room-living-room .st-tile');
    await expect(living).toHaveCount(6);
    await expect(page.locator('#room-living-room .st-tile-pic')).toHaveCount(4);
    await expect(page.locator('#room-living-room .st-tile-link')).toHaveCount(6);
    // every picture on the contents is a frame QA let in: the three typographic houses have none
    const srcs = await page.locator('img').evaluateAll((els) => els.map((e) => (e as HTMLImageElement).currentSrc || (e as HTMLImageElement).src));
    for (const s of srcs) expect(s, s).not.toMatch(/\/(mediterranean|japandi)\//);
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
    await expect(page).toHaveURL(/\/rooms\/living-room\/$/);
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
  test('modern country: an "almost" frame says so; a product QA did not call faithful is listed without a dot', async ({ page }) => {
    await page.goto(COUNTRY);
    await expect(page.locator('#frame-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    await expect(page.locator('#frame-A .st-draft')).toHaveClass(/is-almost/);
    await expect(page.locator('#frame-A .st-draft')).toHaveText('טיוטה / בדיקה · כמעט מוכן');
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

  test('the Mediterranean: QA has not let its frame in, so the page is type only, with no frame and no picture', async ({ page }) => {
    await page.goto(MED);
    await expect(page.locator('h1')).toHaveText('בית מסויד, צהרי יוני');
    await expect(page.locator('.mag-stage')).toHaveCount(0);
    await expect(page.locator('.st-mark')).toHaveCount(0);
    await expect(page.locator('.st-type-status')).toContainText('הפריים עוד בבדיקה');
    const srcs = await page.locator('img').evaluateAll((els) => els.map((e) => (e as HTMLImageElement).src));
    for (const s of srcs) expect(s, s).not.toMatch(/\/mediterranean\//);
    // and the frame is not on the server at all
    expect((await page.request.get('/media/story/living-room/mediterranean/A/1920.webp')).status()).toBe(404);
    await page.waitForTimeout(800);
    await audit(page, 'the Mediterranean, typographic');
  });

  test('boho fin6 (QA register: final test): its frame, nine dots, the test mark', async ({ page }) => {
    await page.goto(BOHO);
    await expect(page.locator('h1')).toHaveText('בית אבן ישן בנמל, 16:00');
    await expect(page.locator('#frame-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    await expect(page.locator('#frame-A .st-draft')).toHaveText('טיוטה / בדיקה');
    await expect(page.locator('#frame-A .st-mark')).toHaveCount(9);
    await expect(page.locator('#list-A .st-credit')).toHaveCount(9);
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

const DETAIL = (style: string, product: string) => `/story/living-room/${style}/p/${product}/`;
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
    const href = DETAIL('warm-modern', 'cushions-cj-boucle-teddy');
    await page.goto(href);
    await expect(page.locator('h1')).toHaveText('ציפית כרית בוקלה, תה חלב');
    await expect(page.locator('#st-pd-price')).toHaveText(/59/);
    await expect(page.locator('#st-pd-story-note')).toBeHidden();
    await page.locator('.st-pd-axis[data-axis="size"] label', { hasText: '30×50' }).click();
    await expect(page.locator('#st-pd-price')).toHaveText(/49/);
    await expect(page).toHaveURL(/size=30x50/);
    await expect(page.locator('#st-pd-story-note')).toContainText('בסיפור מוצגת האפשרות');
    await expect(page.locator('[data-spec="מידות"]')).toContainText('30×50');
    // the address names the option: a reload keeps it
    await page.reload();
    await expect(page.locator('#st-pd-price')).toHaveText(/49/);
    await expect(page.locator('.st-pd-axis[data-axis="size"] input:checked')).toHaveValue('30x50');
    await page.locator('#st-pd-add').click();
    await page.locator('#st-cart-open').click();
    await expect(page.locator('#st-cart-lines')).toContainText('30×50');
    await page.keyboard.press('Escape');
    await page.locator('#st-pd-back').click();
    await expect(page.locator('#st-pd-price')).toHaveText(/59/);
    await expect(page).toHaveURL(new RegExp(`${href}$`));
    // the same product in another house
    await expect(page.locator('#elsewhere .st-tile-link')).toHaveAttribute('href', DETAIL('nordic', 'cushions-cj-boucle-teddy'));
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
    await expect(page.locator('#st-pd-try')).toHaveAttribute('href', '/rooms/living-room/?slot=cushions&option=1');
    await page.locator('#st-pd-try').click();
    await expect(page).toHaveURL(/\/rooms\/living-room\/\?slot=cushions&option=1$/);
    await expect(page.getByRole('dialog').first()).toBeVisible({ timeout: 20_000 });
    // a house whose tool is still being built says so
    await page.goto(DETAIL('warm-modern', 'cushions-cj-boucle-teddy'));
    await expect(page.locator('#st-pd-try-none')).toContainText('בבנייה');
  });

  test('zero axe violations on a detail page with options (1280), and after a choice', async ({ page }) => {
    await page.goto(DETAIL('warm-modern', 'cushions-cj-boucle-teddy'));
    await page.waitForTimeout(800);
    await audit(page, 'detail at rest');
    await page.locator('.st-pd-axis[data-axis="color"] label').first().click();
    await page.waitForTimeout(300);
    await audit(page, 'detail after a choice');
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
