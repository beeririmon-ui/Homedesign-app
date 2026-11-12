/**
 * S19, QA ת55: the cart, the checkout and the order page always load as a document of their own, never as an in-site
 * move, so the analytics beacon of the page before them is never present while the customer types their details.
 * The router's two doors: a click on a site link (`onLinkClick`) and a navigation from code (`navigate`).
 */
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { loadsAsDocument, NO_ANALYTICS } from '@hd/shared/analytics';

type Router = typeof import('../src/router');
let router: Router;
beforeAll(async () => {
  // the site's build (vite defines it): a real URL bar, not the artifact's memory router
  (globalThis as { __ARTIFACT__?: boolean }).__ARTIFACT__ = false;
  router = await import('../src/router');
});
afterEach(() => {
  vi.unstubAllGlobals();
});

/** a left click on <a href> as the browser hands it to the document's listener */
function click(href: string): { prevented: boolean } {
  const a = { target: '', hasAttribute: () => false, getAttribute: (k: string) => (k === 'href' ? href : null) };
  const out = { prevented: false };
  router.onLinkClick({
    defaultPrevented: false,
    button: 0,
    metaKey: false,
    ctrlKey: false,
    shiftKey: false,
    altKey: false,
    target: { closest: () => a },
    preventDefault: () => void (out.prevented = true),
  } as unknown as MouseEvent);
  return out;
}

describe('ת55: the pages without the beacon load as their own document', () => {
  it('which pages: every page that never carries the beacon, whatever its query or hash', () => {
    for (const p of ['/cart/', '/cart', '/checkout/', '/checkout/?failed=1', '/checkout/#f-name', '/order/1234567890/', '/admin/'])
      expect(loadsAsDocument(p), p).toBe(true);
    for (const p of ['/', '/rooms/living-room/', '/rooms/living-room/?style=warm-modern', '/p/vase-x/', '/privacy/', '/carts/', '/checkouts'])
      expect(loadsAsDocument(p), p).toBe(false);
    // the same list as the build's: a page the beacon is kept off is a page entered by a full load
    for (const p of ['/cart/', '/checkout/', '/order/1/', '/admin/', '/api/x', '/404']) expect(NO_ANALYTICS.test(p), p).toBe(loadsAsDocument(p));
  });

  it('a click on a link to the cart or the checkout is left to the browser (a full page load); a link to a product stays in the site', () => {
    vi.stubGlobal('history', { pushState: vi.fn(), replaceState: vi.fn() });
    for (const href of ['/cart/', '/checkout/', '/checkout/?failed=1', '/order/1234567890/']) expect(click(href).prevented, href).toBe(false);
    expect(click('/p/vase-x/').prevented).toBe(true);
    expect(router.path.value).toBe('/p/vase-x/');
    expect(click('/rooms/living-room/').prevented).toBe(true);
  });

  it('a navigation from code to the cart or the checkout loads the page (location.assign / replace), and pushes no history entry', () => {
    const location = { assign: vi.fn(), replace: vi.fn(), pathname: '/p/vase-x/', search: '' };
    const history = { pushState: vi.fn(), replaceState: vi.fn() };
    vi.stubGlobal('location', location);
    vi.stubGlobal('history', history);
    const before = router.path.value;
    router.navigate('/checkout/');
    router.navigate('/cart/', { replace: true });
    expect(location.assign).toHaveBeenCalledWith('/checkout/');
    expect(location.replace).toHaveBeenCalledWith('/cart/');
    expect(history.pushState).not.toHaveBeenCalled();
    expect(router.path.value).toBe(before);
    router.navigate('/rooms/living-room/');
    expect(history.pushState).toHaveBeenCalledWith(null, '', '/rooms/living-room/');
    expect(location.assign).toHaveBeenCalledTimes(1);
  });
});
