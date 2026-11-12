/**
 * S20 (QA S18), as the build runs in the browser and its Worker (no email provider, no contact details: CONTACT1):
 * - ת56: the story's sheet on every item, in every story page behind the flag: "המלאי אינו זמין כעת." with no "אפשר לבקש
 *   עדכון", and no promise anywhere in the story (its data included), read the widened way (e2e/promises-dom.ts).
 * - ת57: `/api/waitlist` refuses and stores nothing; `/api/checkout` with "marketing": true records no consent.
 * - ת61: no contact block and no "כתבו לנו" on the pages that would offer contact (the footer, the delivered order,
 *   "אין גישה", the cancellation and accessibility pages); their lines are the wording without contact.
 */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { walk } from '../tools/lib/promise-scan';
import { promisesOn } from './promises-dom';
import { openCustomerOrder, placeOrder, supplierSays, waitStatus } from './ops';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const built = JSON.parse(readFileSync(join(SITE, '.generated/copy.he.json'), 'utf8')) as {
  capabilities: string[];
  contact: unknown;
  strings: Record<string, string | null>;
};
const line = (k: string): string => {
  const l = built.strings[k];
  if (typeof l !== 'string') throw new Error(`the copy has no line ${k}`);
  return l;
};
/** the preview's own D1, as JSON rows */
function d1<T>(sql: string): T[] {
  const out = execFileSync('npx', ['--no-install', 'wrangler', 'd1', 'execute', 'DB', '--local', '--persist-to', '../.wrangler-state', '--json', '--command', sql], {
    cwd: join(SITE, 'api'),
    stdio: 'pipe',
    encoding: 'utf8',
  });
  return (JSON.parse(out) as { results: T[] }[])[0]!.results;
}
const NO_CONTACT = /mailto:|tel:|כתבו לנו|פנו אלינו|לכתוב לנו/;
async function noContactOffered(page: Page): Promise<void> {
  await expect(page.locator('[data-contact]')).toHaveCount(0);
  expect(await page.content()).not.toMatch(NO_CONTACT);
}

test.describe.configure({ mode: 'serial', timeout: 180_000 });

test('the build: no email provider, no contact details', () => {
  expect(built.capabilities).toEqual([]);
  expect(built.contact).toBeNull();
  expect(built.strings['story.unavailable_note']).toBeNull();
  expect(built.strings['order.no_access_contact']).toBeNull();
});

test('ת56: every story page and every sheet: the status alone, no promise', async ({ page }) => {
  const pages = walk(join(SITE, 'web/dist/story'), (r) => r.endsWith('index.html')).map((p) => `/story/${p.slice(join(SITE, 'web/dist/story').length + 1).replace(/index\.html$/, '')}`);
  expect(pages.length).toBeGreaterThan(5);
  const found: string[] = [];
  let unavailable = 0;
  for (const path of pages) {
    await page.goto(path);
    const ids = await page.evaluate(() => {
      const el = document.getElementById('st-data');
      return el ? Object.keys((JSON.parse(el.textContent ?? '{}') as { items?: Record<string, unknown> }).items ?? {}) : [];
    });
    if (!ids.length) {
      for (const f of await promisesOn(page)) found.push(`${path} ${f}`);
      continue;
    }
    await page.waitForFunction(() => !!(window as unknown as { __story?: unknown }).__story);
    for (const f of await promisesOn(page)) found.push(`${path} ${f}`);
    for (const id of ids) {
      await page.evaluate((i) => (window as unknown as { __story: { openSheet: (x: string) => Promise<void> } }).__story.openSheet(i), id);
      const why = page.locator('#st-why');
      const text = await page.locator('dialog[open]').innerText();
      if (/המלאי אינו זמין כעת/.test(text)) {
        unavailable++;
        expect(text, `${path} ${id}`).not.toMatch(/לבקש עדכון/);
        await expect(why).toHaveText('המלאי אינו זמין כעת.');
      }
      for (const f of await promisesOn(page)) found.push(`${path} ${id} ${f}`);
    }
  }
  // QA counted 4 items on hold in the story; any number but none is fine as the data moves
  expect(unavailable).toBeGreaterThan(0);
  expect([...new Set(found)]).toEqual([]);
});

test('ת57: the waiting list refuses and stores nothing', async ({ request }) => {
  const before = d1<{ n: number }>('SELECT COUNT(*) AS n FROM waitlist')[0]!.n;
  for (const data of [
    { email: 'buyer@example.com', product_id: 'nope' },
    { email: 'buyer@example.com', room: 'living-room', slot: 'vase' },
  ]) {
    const r = await request.post('/api/waitlist', { data, headers: { 'cf-connecting-ip': '10.20.0.1' } });
    expect(r.status()).toBe(409);
    expect(((await r.json()) as { error: string }).error).toBe('waitlist_closed');
  }
  expect(d1<{ n: number }>('SELECT COUNT(*) AS n FROM waitlist')[0]!.n).toBe(before);
});

test('ת57: a checkout that says yes to marketing records no consent; the order goes on', async ({ request }) => {
  const placed = await placeOrder(request, '10.20.0.2', 'vase', { marketing: true });
  const row = d1<{ marketing_consent: number; marketing_consent_at: string | null }>(
    `SELECT c.marketing_consent, c.marketing_consent_at FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = '${placed.id}'`,
  );
  expect(row).toEqual([{ marketing_consent: 0, marketing_consent_at: null }]);
});

test('ת61: no contact offered where there is none: footer, legal pages, the delivered order, "אין גישה"', async ({ page, request, browser }) => {
  for (const path of ['/', '/returns/', '/accessibility/', '/privacy/', '/terms/']) {
    await page.goto(path);
    await noContactOffered(page);
  }
  await page.goto('/returns/');
  await expect(page.getByText(line('legal.returns_notice'))).toBeVisible();
  await page.goto('/accessibility/');
  await expect(page.getByText(line('legal.accessibility_contact'))).toBeVisible();
  await expect(page.locator('.notice.warn')).toHaveText(line('legal.draft'));

  const o = await placeOrder(request, '10.20.0.3');
  await waitStatus(request, o, 'sent_to_supplier');
  await supplierSays(request, o, 'shipped');
  await supplierSays(request, o, 'delivered');
  await waitStatus(request, o, 'delivered');
  await openCustomerOrder(page, o);
  await expect(page.locator('.order-sheet > p.small.muted')).toHaveText(line('order.next.delivered'));
  await noContactOffered(page);
  expect(await promisesOn(page)).toEqual([]);

  const other = await browser.newContext({ locale: 'he-IL' });
  const p2 = await other.newPage();
  await p2.goto(`/order/${o.id}/`);
  await expect(p2.getByRole('alert')).toHaveText(line('order.no_access'));
  await expect(p2.locator('.order-no-access-contact')).toHaveCount(0);
  await noContactOffered(p2);
  await other.close();
});
