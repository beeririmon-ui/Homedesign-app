/**
 * S17, the evidence (qa/reports/2026-11-07-site-track/s17/screens):
 * - the customer's page of an order in supplier_error (master-designer §7): the progress line stays on "בהכנה", with the
 *   one line under it, announced once (aria-live polite, not role=alert), no fifth status, no email sentence;
 * - the same order once it is sent: the line is gone, with no "resolved" message.
 * Runs only as `HD_SHOTS_DIR=<dir> npx --no-install playwright test --project=evidence e2e/shots-s17.spec.ts`, against the
 * local build with its Worker (npm run preview).
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { ORDER_DELAY_HE } from '@hd/shared/constants';
import { openCustomerOrder, placeOrder, waitStatus, type Placed } from './ops';

const DIR = process.env.HD_SHOTS_DIR ?? '';
const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');
test.describe.configure({ mode: 'serial', timeout: 180_000 });

const WIDTHS = [1280, 400] as const;
async function shot(page: Page, name: string) {
  mkdirSync(join(DIR, 'screens'), { recursive: true });
  await page.screenshot({ path: join(DIR, 'screens', `${name}.png`), fullPage: true });
}
/** the preview's own D1 (api: wrangler dev --persist-to ../.wrangler-state) */
function d1(sql: string) {
  execFileSync('npx', ['--no-install', 'wrangler', 'd1', 'execute', 'DB', '--local', '--persist-to', '../.wrangler-state', '--command', sql], {
    cwd: join(SITE, 'api'),
    stdio: 'pipe',
  });
}

let stuck: Placed;
test('setup: an order in supplier_error', async ({ request }) => {
  stuck = await placeOrder(request, '10.17.0.1');
  await waitStatus(request, stuck, 'sent_to_supplier');
  d1(
    `UPDATE supplier_shipments SET status = 'failed', supplier_order_id = NULL, reach = 'none', attempts = 5, last_error = 'refused' WHERE order_id = '${stuck.id}'; UPDATE orders SET status = 'supplier_error' WHERE id = '${stuck.id}';`,
  );
});

for (const w of WIDTHS)
  test(`the delayed order: "בהכנה" and the line, ${w}`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: 900 }, locale: 'he-IL' });
    const page = await ctx.newPage();
    await openCustomerOrder(page, stuck);
    const line = page.locator('.order-delay');
    await expect(line).toHaveText(ORDER_DELAY_HE);
    await expect(line).toHaveAttribute('aria-live', 'polite');
    expect(await line.getAttribute('role')).toBeNull();
    await expect(page.locator('.order-steps')).toHaveAttribute('aria-label', 'מצב ההזמנה: בהכנה');
    await expect(page.locator('.order-steps li[aria-current="step"]')).toHaveText('בהכנה');
    // the status and its line: no fifth status, no supplier, no email promise (the rest of the sheet is the order's lines)
    const text = `${await page.locator('.order-steps').innerText()} ${await line.innerText()}`;
    expect(text).not.toMatch(/מתעכבת|מייל|ספק|תקלה/);
    expect(await page.locator('.order-sheet').innerText()).not.toMatch(/מתעכבת|נעדכן אותך במייל/);
    await expect
      .poll(() =>
        page.locator('figure.your-room img').evaluateAll((is) => is.every((i) => (i as HTMLImageElement).complete && (i as HTMLImageElement).naturalWidth > 0)),
      )
      .toBe(true);
    const axe = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(axe.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
    await shot(page, `order-delayed-${w}`);
    await ctx.close();
  });

test('once it is sent, the line goes, with no "resolved" message', async ({ browser }) => {
  d1(
    `UPDATE orders SET status = 'sent_to_supplier' WHERE id = '${stuck.id}'; UPDATE supplier_shipments SET status = 'submitted', supplier_order_id = 'MOCK-${stuck.id}' WHERE order_id = '${stuck.id}';`,
  );
  const ctx = await browser.newContext({ viewport: { width: 400, height: 900 }, locale: 'he-IL' });
  const page = await ctx.newPage();
  await openCustomerOrder(page, stuck);
  await expect(page.locator('.order-steps li[aria-current="step"]')).toHaveText('בהכנה');
  await expect(page.locator('.order-delay')).toHaveText('');
  expect(await page.locator('.order-sheet').innerText()).not.toMatch(/נפתר|חזרה למסלול|ההכנה נמשכת/);
  await shot(page, 'order-sent-400');
  await ctx.close();
});
