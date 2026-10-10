import { test, expect, type Page } from '@playwright/test';

async function roomReady(page: Page) {
  await page.goto('/rooms/living-room/');
  await expect(page.locator('button.hotspot:visible').first()).toBeVisible({ timeout: 20_000 });
}

test.describe('SEO: prerendered Hebrew pages', () => {
  test('room and product pages are complete HTML before any script runs', async ({ request }) => {
    const room = await (await request.get('/rooms/living-room/')).text();
    expect(room).toContain('<html lang="he" dir="rtl">');
    expect(room).toMatch(/<title>סלון נורדי/);
    expect(room).toContain('rel="canonical"');
    expect(room).toMatch(/<h1[^>]*>סלון/);
    const href = /href="(\/p\/[^"]+\/)"/.exec(room)?.[1];
    expect(href).toBeTruthy();
    const product = await (await request.get(href!)).text();
    expect(product).toContain('"@type":"Product"');
    expect(product).toMatch(/<h1[^>]*id="product-title"/);
    expect((await request.get('/no-such-page/')).status()).toBe(404);
  });
});

test.describe('room experience', () => {
  test('hotspots are buttons; the wheel works with the keyboard and restores focus', async ({ page }) => {
    await roomReady(page);
    const vase = page.locator('button.hotspot[data-slot="vase"]');
    await expect(vase).toHaveAttribute('type', 'button');
    await vase.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog', { name: 'אגרטל' });
    await expect(dialog).toBeVisible();
    const radios = dialog.getByRole('radio');
    await expect(radios).toHaveCount(3);
    await expect(radios.nth(0)).toHaveAttribute('aria-checked', 'true');
    await page.keyboard.press('ArrowLeft'); // RTL: next option
    await expect(radios.nth(1)).toHaveAttribute('aria-checked', 'true');
    await expect(radios.nth(1)).toBeFocused();
    await page.keyboard.press('End');
    await expect(radios.nth(2)).toHaveAttribute('aria-checked', 'true');
    await page.keyboard.press('Escape'); // cancel: back to the option shown before
    await expect(dialog).toBeHidden();
    await expect(vase).toBeFocused({ timeout: 5000 });
    expect(await page.evaluate(() => window.__hdEngine?.getSelection().vase)).toBe(1);
  });

  test('product marks: 44 px targets that never overlap, no pulsing, focus lights the product outline, reduced motion respected', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await roomReady(page);
    const spots = page.locator('button.hotspot:visible');
    const n = await spots.count();
    expect(n).toBeGreaterThan(5);
    const boxes = [];
    for (let i = 0; i < n; i++) {
      const b = { ...(await spots.nth(i).boundingBox())!, slot: await spots.nth(i).getAttribute('data-slot') };
      expect(Math.min(b.width, b.height)).toBeGreaterThanOrEqual(44);
      boxes.push(b);
    }
    for (let i = 0; i < n; i++)
      for (let j = i + 1; j < n; j++) {
        const a = boxes[i]!;
        const b = boxes[j]!;
        expect(Math.hypot(a.x - b.x, a.y - b.y), `mark targets overlap: ${a.slot} ${a.x},${a.y} / ${b.slot} ${b.x},${b.y}`).toBeGreaterThanOrEqual(44);
      }
    const vase = page.locator('button.hotspot[data-slot="vase"]');
    expect(await vase.evaluate((el) => getComputedStyle(el.querySelector('.mark')!).animationName)).toBe('none');
    // keyboard focus: a solid outline on the target, and the product's own outline glows
    await page.keyboard.press('Tab');
    for (let i = 0; i < 40 && !(await vase.evaluate((el) => el === document.activeElement)); i++) await page.keyboard.press('Tab');
    await expect(vase).toBeFocused();
    const focusStyle = () =>
      vase.evaluate((el) => {
        const s = getComputedStyle(el);
        const path = document.querySelector<SVGPathElement>('.outlines path[data-slot="vase"]')!;
        const p = getComputedStyle(path);
        return `${s.outlineStyle} ${parseFloat(s.outlineWidth) >= 2} outline:${p.opacity} ${parseFloat(p.transitionDuration) <= 0.01}`;
      });
    await expect.poll(focusStyle, { timeout: 5000 }).toBe('solid true outline:1 true');
    // only the focused product is lit
    await expect(page.locator('.outlines path[data-on="true"]')).toHaveCount(1);
  });

  test('hovering the product itself lights its outline, and a click on it opens its variants', async ({ page }) => {
    await roomReady(page);
    const box = (await page.locator('canvas.room-canvas').boundingBox())!;
    const at = await page.evaluate(() => {
      const r = document.querySelector('canvas.room-canvas')!.getBoundingClientRect();
      const b = document.querySelector('button.hotspot[data-slot="pouf"]')!.getBoundingClientRect();
      return { x: b.x + b.width / 2 - r.x, y: b.y + b.height / 2 - r.y };
    });
    // a point on the pouf, away from its mark
    await page.mouse.move(box.x + at.x + 30, box.y + at.y + 10);
    await expect(page.locator('.outlines path[data-slot="pouf"]')).toHaveAttribute('data-on', 'true');
    await page.mouse.click(box.x + at.x + 30, box.y + at.y + 10);
    await expect(page.getByRole('dialog', { name: 'פוף' })).toBeVisible();
  });

  test('drag with inertia moves the wheel (mouse)', async ({ page }) => {
    await roomReady(page);
    await page.locator('button.hotspot[data-slot="vase"]').click();
    const arc = page.locator('.arc');
    await expect(arc).toBeVisible();
    const box = (await arc.boundingBox())!;
    const y = box.y + box.height / 2;
    await page.mouse.move(box.x + box.width * 0.3, y);
    await page.mouse.down();
    for (let i = 1; i <= 8; i++) await page.mouse.move(box.x + box.width * (0.3 + i * 0.05), y);
    await page.mouse.up();
    await expect(page.getByRole('radio', { checked: true })).not.toHaveAccessibleName(/^1 מתוך/, { timeout: 5000 });
  });
});

test.describe('store', () => {
  test('product → cart → checkout validation → mock hosted page → paid order', async ({ page }) => {
    await page.goto('/rooms/living-room/');
    await page
      .getByRole('link', { name: /^אגרטל/ })
      .first()
      .click();
    await expect(page.locator('#product-title')).toBeVisible();
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.cart-count')).toHaveText('1');
    await page.getByRole('link', { name: /^סל הקניות/ }).click();
    await expect(page.getByRole('heading', { name: 'סל הקניות' })).toBeVisible();
    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();

    await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
    const summary = page.locator('.error-summary');
    await expect(summary).toBeVisible();
    await expect(summary.getByRole('link')).toHaveCount(7);
    await expect(page.getByLabel('שם מלא')).toHaveAttribute('aria-invalid', 'true');

    await page.getByLabel('שם מלא').fill('ישראלה ישראלי');
    await page.getByLabel('אימייל').fill('buyer@example.com');
    await page.getByLabel('טלפון').fill('050-1234567');
    await page.getByLabel('עיר').fill('תל אביב');
    await page.getByLabel('רחוב').fill('הרצל');
    await page.getByLabel('מספר בית').fill('10');
    await page.getByRole('checkbox', { name: /קראתי ואני מסכים/ }).check();
    await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();

    await expect(page).toHaveURL(/\/mock-pay\/ms_/);
    await page.getByRole('button', { name: 'אישור תשלום (מדומה)' }).click();
    await expect(page).toHaveURL(/\/order\/HD-[A-Z0-9]{8}\/$/);
    await expect(page.locator('.status-pill')).toHaveText(/שולמה|הועברה לספק/, { timeout: 20_000 });
  });

  test('a declined payment returns to checkout with a clear message', async ({ page }) => {
    await page.goto('/rooms/living-room/');
    await page
      .getByRole('link', { name: /^אגרטל/ })
      .first()
      .click();
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.cart-count')).toHaveText('1');
    await page.goto('/checkout/');
    await page.getByLabel('שם מלא').fill('ישראל ישראלי');
    await page.getByLabel('אימייל').fill('buyer@example.com');
    await page.getByLabel('טלפון').fill('03-1234567');
    await page.getByLabel('עיר').fill('חיפה');
    await page.getByLabel('רחוב').fill('הנמל');
    await page.getByLabel('מספר בית').fill('3');
    await page.getByRole('checkbox', { name: /קראתי ואני מסכים/ }).check();
    await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
    await page.getByRole('button', { name: 'דחיית תשלום (מדומה)' }).click();
    await expect(page).toHaveURL(/\/checkout\/\?failed=1/);
    await expect(page.getByRole('alert').first()).toContainText('התשלום לא הושלם');
  });

  test('set or single piece (P1): the set is the default, one piece has its own price, the cart keeps both apart', async ({ page }) => {
    const SET = '/p/candle-holders-cj-travertine-pedestal/';
    await page.goto(SET);
    const group = page.getByRole('radiogroup', { name: 'איך לקנות' });
    await expect(group).toBeVisible();
    const set = group.getByRole('radio', { name: /^סט של 2/ });
    const unit = group.getByRole('radio', { name: /^יחידה אחת/ });
    await expect(set).toBeChecked();
    const priceRow = page.locator('.price-row');
    const setPrice = (await priceRow.locator('.price-big').innerText()).replace(/\D/g, '');
    // keyboard: arrow keys move between the two radios
    await set.focus();
    await page.keyboard.press('ArrowLeft');
    await expect(unit).toBeChecked();
    await expect(priceRow).toContainText('מחיר משוער');
    const unitPrice = (await priceRow.locator('.price-big').innerText()).replace(/\D/g, '');
    expect(Number(unitPrice)).toBeLessThan(Number(setPrice));
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.cart-count')).toHaveText('1');
    await set.check();
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.cart-count')).toHaveText('2');

    await page.goto('/cart/');
    const lines = page.locator('.cart-line');
    await expect(lines).toHaveCount(2);
    await expect(lines.filter({ hasText: 'יחידה אחת' })).toHaveCount(1);
    await expect(lines.filter({ hasText: 'סט של 2' })).toHaveCount(1);
    await expect(page.getByRole('group', { name: /כמות של .*, יחידה אחת/ })).toBeVisible();
    // removing the single piece keeps the set
    await page.getByRole('button', { name: /הסרה של .*, יחידה אחת/ }).click();
    await expect(lines).toHaveCount(1);
    await expect(lines.first()).toContainText('סט של 2');
    await page.goto('/checkout/');
    await expect(page.locator('.summary')).toContainText('(סט של 2) × 1');

    // a product sold as one unit shows no choice, and no standards row without data in its card
    await page.goto('/rooms/living-room/');
    await page
      .getByRole('link', { name: /^אגרטל/ })
      .first()
      .click();
    await expect(page.locator('#product-title')).toBeVisible();
    await expect(page.getByRole('radiogroup', { name: 'איך לקנות' })).toHaveCount(0);
    await expect(page.getByText('תקנים ובטיחות')).toHaveCount(0);
  });

  test('the variant wheel offers set or single piece; its arrow keys stay with the radios', async ({ page }) => {
    await roomReady(page);
    await page.locator('button.hotspot[data-slot="candle-holders"]').click();
    const dialog = page.getByRole('dialog', { name: 'פמוטים' });
    await expect(dialog).toBeVisible();
    const group = dialog.getByRole('radiogroup', { name: 'איך לקנות' });
    await expect(group).toBeVisible();
    const before = await dialog.getByRole('radio', { checked: true }).first().getAttribute('aria-label');
    await group.getByRole('radio', { name: /^סט של 2/ }).focus();
    await page.keyboard.press('ArrowLeft');
    await expect(group.getByRole('radio', { name: /^יחידה אחת/ })).toBeChecked();
    // the wheel did not move
    expect(await dialog.locator('.arc-card[aria-checked="true"]').getAttribute('aria-label')).toBe(before);
    await dialog.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.cart-count')).toHaveText('1');
  });
});
