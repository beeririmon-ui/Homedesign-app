/** Prerender entry (vite build --ssr): HTML for a URL plus its <head> tags, for SEO in Hebrew. */
import renderToString from 'preact-render-to-string';
import { App } from './App';
import { headFor } from './head';
import { registerPages } from './pages/lazy';
import { Product } from './pages/Product';
import { CartPage } from './pages/Cart';
import { Checkout } from './pages/Checkout';
import { OrderPage } from './pages/Order';
import { MockPay } from './pages/MockPay';
import { Legal } from './pages/Legal';

// S13: the prerender renders every page in full; the browser loads a page's chunk before it hydrates (main.tsx)
registerPages({ product: Product, cart: CartPage, checkout: Checkout, order: OrderPage, 'mock-pay': MockPay, legal: Legal });

export { ORIGIN } from './head';
// S10 question 7 (S11): the houses of the room engine, for a prerendered page per house (scripts/prerender.ts)
export { HOUSES, NORDIC } from './house';
import { HOUSES as ALL, NORDIC as N, loadHouse } from './house';
/** S14, QA ת29: every house's chunk, loaded before its page is rendered, so the page is that house from its first paint */
export const loadHouses = () => Promise.all(ALL.filter((h) => h.style !== N).map((h) => loadHouse(h.style)));
import { match } from './router';

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => `&#${c.charCodeAt(0)};`);

export function render(url: string): { html: string; head: string; status: number } {
  const route = match(url);
  const h = headFor(route);
  const html = renderToString(<App url={url} />);
  const tags = [
    `<title>${esc(h.title)}</title>`,
    h.description ? `<meta name="description" content="${esc(h.description)}" />` : '',
    `<link rel="canonical" href="${esc(h.canonical)}" />`,
    h.noindex ? '<meta name="robots" content="noindex" />' : '',
    `<meta property="og:title" content="${esc(h.title)}" />`,
    h.description ? `<meta property="og:description" content="${esc(h.description)}" />` : '',
    '<meta property="og:locale" content="he_IL" />',
    h.preload ? `<link rel="preload" as="image" href="${esc(h.preload)}" fetchpriority="high" />` : '',
    ...h.jsonLd.map((o) => `<script type="application/ld+json">${JSON.stringify(o).replace(/</g, '\\u003c')}</script>`),
  ];
  return { html, head: tags.filter(Boolean).join('\n    '), status: route.name === 'not-found' ? 404 : 200 };
}
