/**
 * S17 (AN1, the owner 2026-11-12): Cloudflare Web Analytics. No beacon without a token or behind the flag; with a token,
 * only on the pages people read; never on the cart, checkout, order page, 404 or admin.
 */
import { describe, expect, it } from 'vitest';
import { analyticsTag, BEACON_SRC, NO_ANALYTICS } from '../src/analytics';

const TOKEN = '0123456789abcdef0123456789abcdef'; // a dummy of the right shape, never a real token
describe('AN1: the analytics beacon', () => {
  it('no token, a placeholder, or a build behind the flag: no beacon', () => {
    for (const token of [undefined, null, '', '  ', '<the site token>', 'abc'])
      expect(analyticsTag({ publicBuild: true, token, path: '/' }), String(token)).toBe('');
    expect(analyticsTag({ publicBuild: false, token: TOKEN, path: '/' })).toBe('');
  });
  it('the public build with a token: one deferred script from Cloudflare, cookieless, no SPA page views', () => {
    const tag = analyticsTag({ publicBuild: true, token: TOKEN, path: '/rooms/living-room/' });
    expect(tag).toBe(`<script defer src="${BEACON_SRC}" data-cf-beacon='{"token":"${TOKEN}","spa":false}'></script>`);
    for (const path of ['/', '/p/vase-white-plum-hand-thrown-karts/', '/privacy/', '/accessibility/'])
      expect(analyticsTag({ publicBuild: true, token: TOKEN, path })).toContain(BEACON_SRC);
  });
  it('never on the cart, the checkout, the order page, the 404 or the admin', () => {
    for (const path of ['/cart/', '/checkout/', '/order/', '/order/1234567890/', '/404', '/admin/', '/admin/orders/1234567890', '/api/orders/1'])
      expect(analyticsTag({ publicBuild: true, token: TOKEN, path }), path).toBe('');
    expect(NO_ANALYTICS.test('/cartography/')).toBe(false);
  });
});
