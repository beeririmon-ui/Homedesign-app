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

  test('product rings: 44 px targets, no pulsing, visible keyboard focus with a glow, reduced motion respected', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await roomReady(page);
    const spots = page.locator('button.hotspot:visible');
    const n = await spots.count();
    expect(n).toBeGreaterThan(5);
    for (let i = 0; i < n; i++) {
      const b = (await spots.nth(i).boundingBox())!;
      expect(Math.min(b.width, b.height)).toBeGreaterThanOrEqual(44);
    }
    const vase = page.locator('button.hotspot[data-slot="vase"]');
    expect(await vase.evaluate((el) => getComputedStyle(el.querySelector('.ring')!).animationName)).toBe('none');
    // keyboard focus: a solid outline and the halo, with no transition time under reduced motion
    await page.keyboard.press('Tab');
    for (let i = 0; i < 40 && !(await vase.evaluate((el) => el === document.activeElement)); i++) await page.keyboard.press('Tab');
    await expect(vase).toBeFocused();
    const focusStyle = () =>
      vase.evaluate((el) => {
        const s = getComputedStyle(el);
        const halo = getComputedStyle(el, '::after');
        return `${s.outlineStyle} ${parseFloat(s.outlineWidth) >= 2} halo:${halo.opacity} ${parseFloat(halo.transitionDuration) <= 0.01}`;
      });
    await expect.poll(focusStyle, { timeout: 5000 }).toBe('solid true halo:1 true');
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
});
