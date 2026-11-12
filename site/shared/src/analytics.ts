/**
 * S17 (AN1, the owner 2026-11-12): site analytics with Cloudflare Web Analytics, cookieless (launch checklist 6.1).
 *
 * - **The beacon** is one deferred script from Cloudflare (`BEACON_SRC`) with the site's token in `data-cf-beacon`. It
 *   sets no cookie and keeps no local storage; it sends the page's address, the referrer, the browser and timings,
 *   nothing the customer typed. We add nothing to it.
 * - **Only in the public build, and only with a token:** the build reads `CF_ANALYTICS_TOKEN` (the site's token from the
 *   Cloudflare dashboard, set where the public build runs; docs/ops/deploy-runbook.md). Without it, no page has the beacon.
 * - **Only on the pages people read:** the home page, the rooms and their houses, the products and the legal pages. Never
 *   the cart, the checkout, the order page or the 404 (scripts/prerender.ts), and never the admin (the Worker's own
 *   screen, with its own CSP, which does not allow Cloudflare's host at all). `spa: false`: a move inside the site (to
 *   the cart, say) is not reported as a page view.
 * - **The CSP** allows Cloudflare's two hosts (`BEACON_SCRIPT_HOST` to load the script, `BEACON_REPORT_HOST` for its
 *   reports) on the pages that may carry it; the cart, checkout and order pages get a second, stricter policy.
 */
export const BEACON_SCRIPT_HOST = 'https://static.cloudflareinsights.com';
export const BEACON_REPORT_HOST = 'https://cloudflareinsights.com';
export const BEACON_SRC = `${BEACON_SCRIPT_HOST}/beacon.min.js`;

/** a site token as Cloudflare issues it: 32 hex characters (scripts/prerender.ts stops a public build on anything else) */
export const ANALYTICS_TOKEN = /^[0-9a-f]{32}$/i;

/** the pages that never carry the beacon: the purchase and the order, the admin, and the 404 */
export const NO_ANALYTICS = /^\/(?:cart|checkout|order|admin|api|404)(?:\/|$)/;

/**
 * The beacon's tag for a page, or '' when it has none: not a public build, no token (or not a token), or a page that
 * never carries it.
 */
export function analyticsTag(o: { publicBuild: boolean; token: string | null | undefined; path: string }): string {
  const token = o.token?.trim() ?? '';
  if (!o.publicBuild || !ANALYTICS_TOKEN.test(token) || NO_ANALYTICS.test(o.path)) return '';
  const config = JSON.stringify({ token: token.toLowerCase(), spa: false });
  return `<script defer src="${BEACON_SRC}" data-cf-beacon='${config}'></script>`;
}
