/**
 * The story-first prototype (/test/story/, briefs/site-story-prototype-2026-11-07.md): the opening frame develops and
 * carries its title and story line with the visible test mark; no dot at rest, dots on movement; a dot or a list row
 * opens "קנה את המראה" (a modal dialog, keyboard and screen reader), add to the test cart, Esc returns the focus; the
 * tool entry opens the room engine; reduced motion; the phone's 4:5 crop; and zero axe violations (WCAG 2.0/2.1 A + AA)
 * at rest, with the sheet open and with the cart open. Exact timings are in the evidence tool (tools/screens-story.ts).
 */
import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

type Ev = { t: number; name: string; detail?: unknown };
/** the hooks web/src/test-page/story.ts exposes */
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

test.describe('the story prototype', () => {
  test('the opening develops, then the title; every frame carries the visible test mark', async ({ page }) => {
    await page.goto('/test/story/');
    await expect(page.locator('h1')).toHaveText('דירה ישנה, שמש של פברואר');
    await expect(page.locator('#frame-nordic-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    const evs = await events(page);
    for (const n of ['nordic-A:lqip', 'nordic-A:developed', 'nordic-A:title'])
      expect(
        evs.some((e) => e.name === n),
        n,
      ).toBe(true);
    await expect(page.locator('#frame-nordic-A .st-line')).toContainText('פברואר');
    await expect(page.locator('.st-draft')).toHaveCount(3);
    await expect(page.locator('#frame-nordic-A .st-draft')).toBeVisible();
    await expect(page.locator('#frame-nordic-A .st-draft')).toHaveText('טיוטה / בדיקה');
    await expect(page.locator('#frame-warm-modern-A .st-draft')).toContainText('טיוטה');
    await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content', /noindex/);
  });

  test('a clean frame at rest; dots on movement; a dot opens the sheet with the card, adds to the test cart, Esc returns', async ({ page }) => {
    await page.goto('/test/story/');
    await expect(page.locator('#frame-nordic-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    await page.waitForTimeout(2200); // the first-entry hint has gone
    const dot = page.locator('#frame-nordic-A .st-mark').first().locator('.mag-dot');
    await expect(dot).toHaveCSS('opacity', '0');
    await page.mouse.move(640, 420);
    await page.mouse.move(660, 430);
    await expect(dot).toHaveCSS('opacity', '1', { timeout: 2_000 });
    const bowl = page.locator('#frame-nordic-A .st-mark[aria-label^="קערה"]');
    await bowl.click();
    await expect(sheet(page)).toHaveAttribute('open', '');
    await expect(sheet(page)).toHaveClass(/is-on/);
    await expect(page.locator('#st-sheet-name')).toHaveText(/^קערה/);
    await expect(page.locator('#st-sheet-name')).toBeFocused();
    await expect(page.locator('#st-sheet-detail')).toContainText('₪');
    await expect(page.locator('#st-sheet-img')).toBeVisible();
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('#st-add')).toHaveText('נוסף לסל');
    await expect(page.locator('#st-cart-count')).toHaveText('1');
    await expect(page.locator('#mag-live')).toContainText('נוסף לסל');
    await page.keyboard.press('Escape');
    await expect(sheet(page)).not.toHaveAttribute('open', '');
    await expect(bowl).toBeFocused();
  });

  test('the keyboard: Tab to a dot shows the dots, Enter opens the sheet, the page behind is inert, Esc back', async ({ page }) => {
    await page.goto('/test/story/');
    await expect(page.locator('#frame-nordic-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    const first = page.locator('#frame-nordic-A .st-mark').first();
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
    await expect(page.locator('#st-pos')).toHaveText(/^2 \//);
    await page.keyboard.press('Escape');
    await expect(sheet(page)).not.toHaveAttribute('open', '');
    expect(await page.evaluate(() => (document.activeElement as HTMLElement | null)?.dataset.item)).toBe('nordic-A-2');
  });

  test('the list opens the same sheet; a product without a price says so, with no add button', async ({ page }) => {
    await page.goto('/test/story/#list-nordic-A');
    const rows = page.locator('#list-nordic-A .st-credit');
    await expect(rows).toHaveCount(13);
    await page.locator('#list-nordic-A .st-open', { hasText: /^מנורת תקרה/ }).click();
    await expect(sheet(page)).toHaveAttribute('open', '');
    await expect(page.locator('#st-add')).toBeHidden();
    await expect(page.locator('#st-why')).toContainText('המחיר עוד לא נקבע');
    await page.locator('#st-sheet-close').click();
    await expect(sheet(page)).not.toHaveAttribute('open', '');
    await expect(page.locator('#list-nordic-A .st-open', { hasText: /^מנורת תקרה/ })).toBeFocused();
    // the rug: QA "partly" in this frame, so no dot; listed, with the reason
    await expect(page.locator('#list-nordic-A .st-no-dot')).toHaveCount(1);
  });

  test('"עצב בעצמך" opens the room engine', async ({ page }) => {
    await page.goto('/test/story/#tool');
    await page.getByRole('link', { name: 'לעיצוב הסלון' }).click();
    await expect(page).toHaveURL(/\/rooms\/living-room\/$/);
    await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
  });

  test('reduced motion: the sheet only fades, nothing rises', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/test/story/');
    await page.evaluate(() => window.__story!.openSheet('nordic-A-1'));
    await expect(sheet(page)).toHaveClass(/is-on/);
    expect(await sheet(page).evaluate((el) => getComputedStyle(el).transform)).toBe('none');
    expect(await page.locator('#frame-nordic-A .st-title-line').evaluate((el) => getComputedStyle(el).transform)).toBe('none');
  });

  test('zero axe violations: at rest, with the sheet open, with the cart open (1280)', async ({ page }) => {
    await page.goto('/test/story/');
    await expect(page.locator('#frame-nordic-A')).toHaveClass(/is-title/, { timeout: 15_000 });
    await audit(page, 'story at rest');
    await page.evaluate(() => window.__story!.openSheet('nordic-A-5'));
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

test.describe('the story prototype on a phone (400)', () => {
  test.use({ viewport: { width: 400, height: 800 }, hasTouch: true, isMobile: true });

  test('the 4:5 crop at full width, dots inside it, the sheet from the bottom, zero axe violations', async ({ page }) => {
    await page.goto('/test/story/');
    const stage = page.locator('#frame-nordic-A .mag-stage');
    const box = (await stage.boundingBox())!;
    expect(Math.round(box.width)).toBe(400);
    expect(Math.round(box.height)).toBe(500);
    // every dot shown on the phone sits inside the crop; a dot the crop does not carry is not offered
    for (const m of await page.locator('#frame-nordic-A .st-mark:visible').all()) {
      const b = (await m.boundingBox())!;
      expect(b.x).toBeGreaterThanOrEqual(box.x - 1);
      expect(b.x + b.width).toBeLessThanOrEqual(box.x + box.width + 1);
    }
    await expect(page.locator('#frame-nordic-A .st-no-phone')).toHaveCount(3);
    await audit(page, 'phone at rest');
    await page.locator('#frame-nordic-A .st-mark:visible').first().tap();
    await expect(sheet(page)).toHaveClass(/is-on/);
    const s = (await sheet(page).boundingBox())!;
    expect(Math.round(s.y + s.height)).toBe(800);
    await page.waitForTimeout(300);
    await audit(page, 'phone, the sheet open');
  });
});
