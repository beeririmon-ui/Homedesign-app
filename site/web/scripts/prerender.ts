/**
 * Writes a static, crawlable HTML page per public route into web/dist (then the client hydrates it).
 * Routes: home, built rooms, every shown product, legal pages, cart/checkout shells, the order shell and 404.
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { shopPath } from '@hd/shared/product-url';

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, '../dist');
const ssrDir = resolve(here, '../.ssr');
const { render, ORIGIN, HOUSES, NORDIC, loadHouses } = (await import(
  pathToFileURL(resolve(ssrDir, 'entry-server.js')).href
)) as typeof import('../src/entry-server');
const catalog = JSON.parse(readFileSync(resolve(here, '../../.generated/catalog.public.json'), 'utf8')) as {
  rooms: { id: string; built: boolean }[];
  products: { id: string }[];
};

// S7: the old addresses by card id (only in the full catalog, never shipped) move to the public ids
const cardIds = (
  JSON.parse(readFileSync(resolve(here, '../../.generated/catalog.full.json'), 'utf8')) as { products: { id: string; card_id?: string }[] }
).products.filter((p): p is { id: string; card_id: string } => !!p.card_id && p.card_id !== p.id);
const template = readFileSync(resolve(dist, 'index.html'), 'utf8');
const routes = [
  '/',
  ...catalog.rooms.filter((r) => r.built).map((r) => `/rooms/${r.id}/`),
  // S5: the neutral address (@hd/shared/product-url); the old one by card id moves there (_redirects below)
  ...catalog.products.map((p) => shopPath(p.id)),
  '/accessibility/',
  '/terms/',
  '/privacy/',
  '/returns/',
  '/cart/',
  '/checkout/',
];

function page(url: string): string {
  const { html, head } = render(url);
  return template.replace('<!--app-head-->', head).replace('<!--app-html-->', html);
}

for (const url of routes) {
  const file = resolve(dist, `.${url}`, 'index.html');
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, page(url));
}
// S10 question 7 (S11): a page per house of the room engine besides the Nordic one, rendered at its own address
// (/rooms/<room>/?style=<id>): it carries no Nordic poster; S14 (ת29): it is that house, its poster from the first
// paint. The Worker serves it for that address (api/src/app.ts); a public build lists no other house, so writes none
const houses = HOUSES.filter((h) => h.style !== NORDIC);
// S14, QA ת29: the house's chunk first, so its page is rendered as that house (its poster, its slot), not as a wait
await loadHouses();
for (const h of houses)
  for (const r of catalog.rooms.filter((x) => x.built)) {
    const file = resolve(dist, `house/${r.id}/${h.style}/index.html`);
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, page(`/rooms/${r.id}/?style=${h.style}`));
  }
// /order/<id>/ is served by the Worker from this shell (client-rendered: the id and token live in the browser)
mkdirSync(resolve(dist, 'order'), { recursive: true });
writeFileSync(resolve(dist, 'order/index.html'), page('/order/HD-00000000/').replace(/HD-00000000/g, ''));
writeFileSync(resolve(dist, '404.html'), page('/404'));
// the old product addresses (by card id) move to the neutral ones, permanently; the story's own lines are appended by
// tools/make-story.ts's list (.generated/story-redirects.txt) when it exists
const storyRedirects = (() => {
  try {
    return readFileSync(resolve(here, '../../.generated/story-redirects.txt'), 'utf8').trim();
  } catch {
    return '';
  }
})();
writeFileSync(
  resolve(dist, '_redirects'),
  [...cardIds.map((p) => `/p/${p.card_id}/ ${shopPath(p.id)} 301`), ...(storyRedirects && process.env.HD_PUBLIC !== '1' ? [storyRedirects] : [])].join('\n') +
    '\n',
);
// robots.txt and sitemap.xml (absolute URLs; ORIGIN changes when the domain is chosen)
const indexable = routes.filter((u) => !['/cart/', '/checkout/'].includes(u));
writeFileSync(
  resolve(dist, 'sitemap.xml'),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${indexable.map((u) => `  <url><loc>${ORIGIN}${u}</loc></url>`).join('\n')}\n</urlset>\n`,
);
writeFileSync(
  resolve(dist, 'robots.txt'),
  [
    'User-agent: *',
    'Disallow: /api/',
    'Disallow: /cart/',
    'Disallow: /checkout/',
    'Disallow: /order/',
    'Disallow: /mock-pay/',
    '',
    `Sitemap: ${ORIGIN}/sitemap.xml`,
    '',
  ].join('\n'),
);
rmSync(ssrDir, { recursive: true, force: true });
console.log(`prerendered ${routes.length} pages + ${houses.length} house page(s) + order shell + 404`);
