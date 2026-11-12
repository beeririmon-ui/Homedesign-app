/**
 * Supplier options on the product page (studio rules ג, 2026-10-11, "כל האפשרויות של הספק בדף המוצר"): every option of
 * the supplier can be chosen, the price follows the chosen SKU, combinations that do not exist are disabled, the keyboard
 * works, the cart gets the chosen SKU, and the room's render stays the room's option. Screenshots for review by eye:
 * site/screens/product-options-{1280,400}.png.
 */
import { test, expect, devices, type Page } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { PublicCatalog, PublicProduct } from '../shared/src/catalog';
import { availableValues, expandOptions, pickSku, selectionOf } from '../shared/src/options';
import { shopPath } from '@hd/shared/product-url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// the review screenshots go to an untracked folder; HD_QA_SHOTS=1 writes the tracked ones for review by eye
const OUT = resolve(SITE, process.env.HD_QA_SHOTS === '1' ? 'screens' : 'test-results/qa-shots/options');
const catalog = JSON.parse(readFileSync(resolve(SITE, '.generated/catalog.public.json'), 'utf8')) as PublicCatalog;

// colour swatches first, at least two axes, and options that differ in price; a cushion when there is one
const fits = (p: PublicProduct) =>
  !!p.options &&
  p.options.axes.length >= 2 &&
  p.options.axes[0]!.id === 'color' &&
  p.options.axes[0]!.values.length <= 16 &&
  p.options.axes[0]!.values.every(([, , hex]) => hex) &&
  new Set(p.options.p).size > 1;
const P = catalog.products.find((p) => p.slot === 'cushions' && fits(p)) ?? catalog.products.find(fits)!;
const O = expandOptions(P.id, P.options!);
const room = O.skus.find((s) => s.in_room)!;
const roomSel = selectionOf(O.axes, room);
// the option to buy: available, another price than the room's, and a different colour
const target =
  O.skus.find((s) => s.available && s.price_agorot !== room.price_agorot && s.values.color !== room.values.color) ??
  O.skus.find((s) => s.available && s.price_agorot !== room.price_agorot)!;
const label = (values: Record<string, string>) => O.axes.map((a) => a.values.find((v) => v.id === values[a.id])!.label_he).join(', ');
const shekels = (agorot: number) => (agorot / 100).toLocaleString('en-US');
const fid = (axis: string) => `opt-${P.id}-${axis}`;

/** For a full-page screenshot: nothing focused (no skip link, no focus ring) and the page at the top (sticky header). */
async function settle(page: Page) {
  await page.evaluate(() => {
    (document.activeElement as HTMLElement | null)?.blur();
    window.scrollTo(0, 0);
  });
}

/** One axis: a native select for a long list, else the radio (swatch or chip). */
async function choose(page: Page, axis: string, value: string) {
  const select = page.locator(`select#${fid(axis)}`);
  if (await select.count()) await select.selectOption(value);
  else await page.locator(`input[name="${fid(axis)}"][value="${value}"]`).check();
}

test.describe('supplier options on the product page', () => {
  test('defaults to the room’s option; another option has its own price; the cart gets that SKU; the render stays', async ({ page }) => {
    await page.goto(shopPath(P.id));
    const picker = page.locator('.opt-picker');
    await expect(picker).toBeVisible();
    const price = page.locator('.price-row .price-big .num');
    await expect(price).toContainText(shekels(room.price_agorot));
    // the room's option is selected on every axis
    for (const a of O.axes) {
      const select = page.locator(`select#${fid(a.id)}`);
      if (await select.count()) await expect(select).toHaveValue(roomSel[a.id]!);
      else await expect(page.locator(`input[name="${fid(a.id)}"][value="${roomSel[a.id]}"]`)).toBeChecked();
    }
    // values that do not exist with the choices above them are disabled
    const disabledExpected = O.axes.some((a, i) => a.values.some((v) => !availableValues(O.axes, O.skus, roomSel, i).has(v.id)));
    if (disabledExpected) expect(await picker.locator('input:disabled, option:disabled').count()).toBeGreaterThan(0);

    const render = page.locator('.gallery-slide[data-kind="render"] img');
    const renderSrc = await render.getAttribute('src');
    // choose the target option, axis by axis (each choice may move the axes below it)
    for (const a of O.axes) await choose(page, a.id, target.values[a.id]!);
    await expect(price).toContainText(shekels(target.price_agorot));
    await expect(page.locator('.opt-room-note')).toContainText(`בחדר מוצגת האפשרות ${label(room.values)}`);
    // the room's render is still the room's option; the supplier photo is the chosen option's when there is one
    expect(await render.getAttribute('src')).toBe(renderSrc);
    await expect(page.locator('.gallery-caption')).toContainText(label(room.values));

    mkdirSync(OUT, { recursive: true });
    await page.setViewportSize({ width: 1280, height: 900 });
    await settle(page);
    await page.screenshot({ path: resolve(OUT, 'product-options-1280.png'), fullPage: true, animations: 'disabled' });
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.cart-count')).toHaveText('1');

    await page.goto('/cart/');
    const line = page.locator('.cart-line').first();
    await expect(line).toContainText(label(target.values));
    await expect(line).toContainText(shekels(target.price_agorot));
  });

  test('the keyboard: arrows move within an axis, the price and the legend follow; back to the room’s option', async ({ page }) => {
    await page.goto(shopPath(P.id));
    const first = O.axes[0]!;
    const checked = page.locator(`input[name="${fid(first.id)}"]:checked`);
    await checked.focus();
    const ok = availableValues(O.axes, O.skus, roomSel, 0);
    const order = first.values.filter((v) => ok.has(v.id)).map((v) => v.id);
    const next = order[(order.indexOf(roomSel[first.id]!) + 1) % order.length]!;
    // S22: on a busy runner the press can land before the page hydrates. S23 (QA S22 ת84, as ת77 for house.spec): the
    // options form says it has hydrated (`data-hydrated`, OptionPicker; the header's cart is not the form's own sign),
    // then the press is made once, so a press lost after hydration fails
    await expect(page.locator('.opt-picker[data-hydrated]')).toHaveCount(1, { timeout: 30_000 });
    await page.locator(`input[name="${fid(first.id)}"][value="${roomSel[first.id]!}"]`).focus();
    await page.keyboard.press('ArrowDown');
    await expect(page.locator(`input[name="${fid(first.id)}"][value="${next}"]`)).toBeChecked({ timeout: 15_000 });
    await expect(page.locator(`input[name="${fid(first.id)}"][value="${next}"]`)).toBeChecked();
    await expect(page.locator(`input[name="${fid(first.id)}"][value="${next}"]`)).toBeFocused();
    const expected = pickSku(O.axes, O.skus, roomSel, 0, next).sku!;
    await expect(page.locator('.price-row .price-big .num')).toContainText(shekels(expected.price_agorot));
    await expect(page.locator('.opt-legend').first()).toContainText(first.values.find((v) => v.id === next)!.label_he);
    await page.getByRole('button', { name: 'חזרה לאפשרות שבחדר' }).click();
    await expect(page.locator('.price-row .price-big .num')).toContainText(shekels(room.price_agorot));
    await expect(page.locator('.opt-room-note')).toHaveCount(0);
  });

  test.describe('mobile', () => {
    const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];
    test.use({ ...pixel, viewport: { width: 400, height: 860 } });
    test('fits the screen (no sideways scroll), 44 px targets, screenshot', async ({ page }) => {
      await page.goto(shopPath(P.id));
      await choose(page, O.axes[0]!.id, target.values[O.axes[0]!.id]!);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
      for (const box of await page.locator('.opt-value').evaluateAll((els) => els.map((e) => e.getBoundingClientRect())))
        expect(Math.min(box.width, box.height)).toBeGreaterThanOrEqual(44);
      mkdirSync(OUT, { recursive: true });
      await settle(page);
      await page.screenshot({ path: resolve(OUT, 'product-options-400.png'), fullPage: true, animations: 'disabled' });
    });
  });
});

/**
 * S23, QA S22 ת83: a colour chosen before the product page hydrates (a real click as soon as the swatch is in the page)
 * is what the page shows and what the cart gets: the checked swatch, the legend and the cart line name the same colour
 * (QA saw "אפור" checked and "לבן חם" in the cart, 4 loads in 10). Phone (a tap) and desktop, 3 loads each.
 */
test.describe('S23 ת83: a choice made before hydration', () => {
  const first = O.axes[0]!;
  const ok = availableValues(O.axes, O.skus, roomSel, 0);
  const order = first.values.filter((v) => ok.has(v.id)).map((v) => v.id);
  const next = order[(order.indexOf(roomSel[first.id]!) + 1) % order.length]!;
  const nameOf = (id: string) => first.values.find((v) => v.id === id)!.label_he;
  for (const view of ['desktop', 'phone'] as const)
    test(`the shown colour is the one in the cart (${view})`, async ({ browser }) => {
      for (let run = 0; run < 3; run++) {
        const ctx = await browser.newContext(
          view === 'phone'
            ? { ...devices['Pixel 5'], locale: 'he-IL', viewport: { width: 400, height: 860 } }
            : { locale: 'he-IL', viewport: { width: 1280, height: 900 } },
        );
        const page = await ctx.newPage();
        await page.goto(shopPath(P.id), { waitUntil: 'domcontentloaded' });
        const swatch = page.locator(`input[name="${fid(first.id)}"][value="${next}"]`);
        if (view === 'phone') await swatch.tap({ force: true });
        else await swatch.click({ force: true });
        await expect(page.locator('.opt-picker[data-hydrated]')).toHaveCount(1, { timeout: 30_000 });
        const checked = await page.locator(`input[name="${fid(first.id)}"]:checked`).getAttribute('value');
        const shown = nameOf(checked!);
        await expect(page.locator('.opt-legend').first(), `run ${run + 1}`).toContainText(shown);
        await page.getByRole('button', { name: 'הוספה לסל' }).click();
        await expect(page.locator('.cart-count')).toHaveText('1');
        await page.goto('/cart/');
        await expect(page.locator('.cart-line').first(), `run ${run + 1}: checked ${shown}`).toContainText(shown);
        await ctx.close();
      }
    });
});
