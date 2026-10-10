import { test, expect, devices, type Page } from '@playwright/test';

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
    // FR-I: the render leads, the supplier's photo follows, in the markup and in the Product schema
    const image = /"image":\["([^"]+)","([^"]+)"\]/.exec(product);
    expect(image, 'Product.image: render, then supplier photo').toBeTruthy();
    expect(image![1]).toMatch(/^https:\/\/[^/]+\/media\/rooms\/living-room\/.*\.product\.\d+\.webp$/);
    expect(image![2]).toMatch(/^https:\/\/[^/]+\/media\/products\/[a-z0-9-]+\/supplier\.800\.webp$/);
    expect(product).toContain('המוצר מרונדר');
    expect(product.indexOf('data-kind="render"')).toBeLessThan(product.indexOf('data-kind="supplier"'));
    expect(product).toMatch(/alt="תמונת הספק: [^"]+"/);
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

  test('product marks rest hidden: a first-visit hint, then they show on pointer movement, fade ~3 s later, and stay with keyboard focus', async ({ page }) => {
    await roomReady(page);
    const stage = page.locator('.stage');
    const mark = page.locator('button.hotspot[data-slot="vase"] .mark');
    // the hint: the marks appear once on the first visit, then the room is clean
    await expect(stage).toHaveAttribute('data-marks', 'on');
    await expect(stage).not.toHaveAttribute('data-marks', 'on', { timeout: 8000 });
    await expect(mark).toHaveCSS('opacity', '0');
    // the buttons stay in the DOM and keep their names (only the mark's opacity changes)
    await expect(page.locator('button.hotspot[data-slot="vase"]')).toHaveAccessibleName(/^אגרטל/);
    // pointer movement over the room shows them...
    const box = (await page.locator('canvas.room-canvas').boundingBox())!;
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.12);
    await page.mouse.move(box.x + box.width * 0.52, box.y + box.height * 0.13);
    await expect(stage).toHaveAttribute('data-marks', 'on');
    await expect(mark).toHaveCSS('opacity', '1');
    // ...and they fade about 3 s after the last movement
    await expect(stage).not.toHaveAttribute('data-marks', 'on', { timeout: 8000 });
    await expect(mark).toHaveCSS('opacity', '0');
    // keyboard: focus on a mark shows them, and they stay while focus is inside the stage
    await page.locator('button.hotspot[data-slot="vase"]').focus();
    await expect(mark).toHaveCSS('opacity', '1');
    await page.waitForTimeout(3600);
    await expect(stage).toHaveAttribute('data-marks', 'on');
    await expect(mark).toHaveCSS('opacity', '1');
    await page.locator('button.hotspot[data-slot="vase"]').blur();
    await expect(stage).not.toHaveAttribute('data-marks', 'on');
    await expect(mark).toHaveCSS('opacity', '0');
  });

  test('product marks: a touch shows them too, and the list under the room is unchanged', async ({ page }) => {
    await roomReady(page);
    const stage = page.locator('.stage');
    await expect(stage).not.toHaveAttribute('data-marks', 'on', { timeout: 8000 });
    await stage.dispatchEvent('pointerdown', { pointerId: 2, pointerType: 'touch', isPrimary: true, clientX: 300, clientY: 300 });
    await expect(stage).toHaveAttribute('data-marks', 'on');
    await expect(page.locator('.slot-list li')).toHaveCount(await page.locator('button.hotspot').count());
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

test.describe('product gallery (FR-I)', () => {
  const PRODUCT = '/p/vase-cj-textured-white-stoneware/';

  test('the render leads with a visible note, the supplier photo follows; buttons, keys and the live region move between them', async ({ page }) => {
    await page.goto(PRODUCT);
    const gallery = page.getByRole('region', { name: 'תמונות המוצר' });
    await expect(gallery).toBeVisible();
    const slides = gallery.locator('.gallery-slide');
    await expect(slides).toHaveCount(2);
    await expect(slides.nth(0)).toHaveAttribute('data-kind', 'render');
    await expect(slides.nth(0).getByRole('img')).toHaveAttribute('alt', /^הדמיה: /);
    const caption = gallery.locator('.gallery-caption');
    await expect(caption).toContainText('הדמיה');
    await expect(caption).toContainText('המוצר מרונדר');
    await expect(slides.nth(1)).toHaveAttribute('data-kind', 'supplier');
    await expect(slides.nth(1).getByRole('img')).toHaveAttribute('alt', /^תמונת הספק: /);
    const next = gallery.getByRole('button', { name: 'התמונה הבאה' });
    const prev = gallery.getByRole('button', { name: 'התמונה הקודמת' });
    await expect(prev).toHaveAttribute('aria-disabled', 'true');
    await next.click();
    await expect(slides.nth(1)).toBeInViewport({ ratio: 0.9 });
    await expect(gallery.locator('[aria-live="polite"]')).toHaveText('תמונה 2 מתוך 2: תמונת הספק');
    await expect(caption).toHaveText('התמונה המקורית מהספק.');
    await expect(gallery.getByRole('button', { name: 'תמונה 2: תמונת הספק' })).toHaveAttribute('aria-current', 'true');
    await expect(next).toHaveAttribute('aria-disabled', 'true');
    // focus stays on the button at the end (aria-disabled, never disabled)
    await expect(next).toBeFocused();
    // keyboard on the strip: ArrowRight goes back in RTL
    await gallery.locator('.gallery-track').focus();
    await page.keyboard.press('ArrowRight');
    await expect(slides.nth(0)).toBeInViewport({ ratio: 0.9 });
    await expect(gallery.locator('[aria-live="polite"]')).toHaveText('תמונה 1 מתוך 2: הדמיה בחדר');
    await expect(prev).toHaveAttribute('aria-disabled', 'true');
    // the supplier photo is served from our media, never from the supplier
    const src = await slides.nth(1).getByRole('img').getAttribute('src');
    expect(src).toMatch(/^\/media\/products\/vase-cj-textured-white-stoneware\/supplier\.800\.webp$/);
    expect((await page.request.get(src!)).headers()['content-type']).toContain('image/webp');
  });

  test.describe('mobile', () => {
    const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];
    test.use(pixel);
    test('the strip scrolls sideways within the screen, and the buttons work', async ({ page }) => {
      await page.goto(PRODUCT);
      const gallery = page.getByRole('region', { name: 'תמונות המוצר' });
      await expect(gallery).toBeVisible();
      // no horizontal page scroll: the strip scrolls, the page does not
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
      const track = gallery.locator('.gallery-track');
      expect(await track.evaluate((el) => el.scrollWidth > el.clientWidth)).toBe(true);
      await gallery.getByRole('button', { name: 'התמונה הבאה' }).tap();
      await expect(gallery.locator('.gallery-slide').nth(1)).toBeInViewport({ ratio: 0.9 });
      await expect(gallery.locator('[aria-live="polite"]')).toHaveText('תמונה 2 מתוך 2: תמונת הספק');
    });
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
