/**
 * S19, QA ת55: on the site's own links the room, the product, the cart and the checkout were one document, so the
 * analytics beacon loaded on the room kept running while the customer typed a name, a phone and an address at the
 * checkout. Now the cart and the checkout always load as a document of their own: no beacon, and their own policy.
 *
 * The beacon is Cloudflare's script, which this machine cannot fetch: a stub is served in its place (it counts its loads
 * and records the fields typed while it runs). A public build with a token carries the tag on the pages that may have
 * it; behind the flag the build has none, so the test adds the same tag (`analyticsTag`) to those pages as they load.
 * With CF_ANALYTICS_TOKEN set (the public build), the build's own tag is used.
 */
import { expect, test, type Page } from '@playwright/test';
import { analyticsTag } from '@hd/shared/analytics';

const TOKEN = process.env.CF_ANALYTICS_TOKEN?.trim() || '0123456789abcdef0123456789abcdef';
type Probe = { __hdBeacon?: number; __hdBeaconSaw?: string[]; __hdDoc?: string };
const STUB = `(() => {
  window.__hdBeacon = (window.__hdBeacon || 0) + 1;
  window.__hdBeaconSaw = [];
  document.addEventListener('input', (e) => window.__hdBeaconSaw.push((e.target && (e.target.name || e.target.id)) || '?'), true);
})();`;

/** the beacon stubbed, and the pages that may carry it served with its tag; returns the pages it loaded on and the documents */
async function withBeacon(page: Page) {
  const loads: string[] = [];
  const documents: { path: string; csp: string; tagged: boolean }[] = [];
  await page.route('https://static.cloudflareinsights.com/beacon.min.js', (r) => {
    loads.push(new URL(page.url()).pathname);
    return r.fulfill({ contentType: 'application/javascript', body: STUB });
  });
  await page.route('https://cloudflareinsights.com/**', (r) => r.fulfill({ status: 204, body: '' }));
  await page.route('**/*', async (route) => {
    if (route.request().resourceType() !== 'document') return route.fallback();
    const res = await route.fetch();
    const path = new URL(route.request().url()).pathname;
    let body = await res.text();
    const tag = analyticsTag({ publicBuild: true, token: TOKEN, path });
    if (tag && !body.includes('cloudflareinsights.com/beacon.min.js')) body = body.replace('</head>', `${tag}</head>`);
    const headers = { ...res.headers() };
    delete headers['content-length'];
    delete headers['content-encoding'];
    documents.push({ path, csp: headers['content-security-policy'] ?? '', tagged: body.includes('cloudflareinsights.com/beacon.min.js') });
    await route.fulfill({ status: res.status(), headers, body });
  });
  return { loads, documents };
}
const probe = (page: Page) =>
  page.evaluate(() => {
    const w = window as unknown as Probe;
    return {
      doc: w.__hdDoc ?? null,
      beacon: w.__hdBeacon ?? null,
      saw: w.__hdBeaconSaw ?? null,
      tags: document.querySelectorAll('script[src*="cloudflareinsights"]').length,
      navigation: (performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined)?.name ?? '',
    };
  });

test.describe('S19 (QA ת55): the cart and the checkout load as their own document', () => {
  test('room → product → cart → checkout by the site’s links: the beacon of the room is gone at the cart and the checkout, and sees nothing typed', async ({
    page,
  }) => {
    const { loads, documents } = await withBeacon(page);
    await page.goto('/rooms/living-room/');
    await expect.poll(() => page.evaluate(() => (window as unknown as Probe).__hdBeacon)).toBe(1);
    await page.evaluate(() => void ((window as unknown as Probe).__hdDoc = 'room'));

    // the product: an in-site move, the same document (the beacon of the room still runs there, as on any page it may)
    await page
      .getByRole('link', { name: /^אגרטל/ })
      .first()
      .click();
    await expect(page.locator('#product-title')).toBeVisible();
    expect((await probe(page)).doc).toBe('room');
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.cart-count')).toHaveText('1');

    // the cart: a document of its own
    await page.getByRole('link', { name: /^סל הקניות/ }).click();
    await expect(page.getByRole('heading', { name: 'סל הקניות' })).toBeVisible();
    const cart = await probe(page);
    expect(cart).toMatchObject({ doc: null, beacon: null, tags: 0 });
    expect(cart.navigation).toMatch(/\/cart\/$/);

    // the checkout: a document of its own; what the customer types is typed with no beacon in the page
    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
    await expect(page.getByRole('heading', { name: 'פרטים לתשלום' })).toBeVisible();
    await page.getByLabel('שם מלא').fill('ישראלה ישראלי');
    await page.getByLabel('טלפון').fill('050-1234567');
    await page.getByLabel('עיר').fill('תל אביב');
    await page.getByLabel('רחוב').fill('הרצל');
    const checkout = await probe(page);
    expect(checkout).toMatchObject({ doc: null, beacon: null, saw: null, tags: 0 });
    expect(checkout.navigation).toMatch(/\/checkout\/$/);

    // the beacon loaded once, on the room; the documents were the room, the cart and the checkout, with their policies
    expect(loads).toEqual(['/rooms/living-room/']);
    expect(documents.map((d) => [d.path, d.tagged])).toEqual([
      ['/rooms/living-room/', true],
      ['/cart/', false],
      ['/checkout/', false],
    ]);
    for (const d of documents.slice(1)) {
      expect(d.csp, d.path).toContain("script-src 'self'; connect-src 'self'");
      expect(d.csp.split(',').at(-1), d.path).not.toContain('cloudflareinsights');
    }
  });

  test('other ways in from a page that may carry the beacon are full loads too: the header’s cart, a link to the checkout with a query', async ({ page }) => {
    const { loads } = await withBeacon(page);
    await page.goto('/privacy/');
    await expect.poll(() => page.evaluate(() => (window as unknown as Probe).__hdBeacon)).toBe(1);
    await page.evaluate(() => void ((window as unknown as Probe).__hdDoc = 'privacy'));
    // the header's cart link on any page
    await page.getByRole('link', { name: /^סל הקניות/ }).click();
    await expect(page.getByRole('heading', { name: 'סל הקניות' })).toBeVisible();
    expect(await probe(page)).toMatchObject({ doc: null, beacon: null, tags: 0 });
    // a link inside a page without the beacon, to one that may have it, and back to the cart: each a document of its own
    await page.goto('/');
    await expect.poll(() => page.evaluate(() => (window as unknown as Probe).__hdBeacon)).toBe(1);
    await page.evaluate(() => {
      (window as unknown as Probe).__hdDoc = 'home';
      const a = document.createElement('a');
      a.href = '/checkout/?failed=1';
      a.textContent = 'checkout';
      a.id = 'go-checkout';
      document.body.append(a);
    });
    await page.locator('#go-checkout').click();
    await expect(page).toHaveURL(/\/checkout\/\?failed=1$/);
    await expect(page.getByRole('heading', { name: 'פרטים לתשלום' })).toBeVisible();
    expect(await probe(page)).toMatchObject({ doc: null, beacon: null, tags: 0 });
    expect(loads).toEqual(['/privacy/', '/']);
  });
});
