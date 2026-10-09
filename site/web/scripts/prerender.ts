/**
 * Writes a static, crawlable HTML page per public route into web/dist (then the client hydrates it).
 * Routes: home, built rooms, every shown product, legal pages, cart/checkout shells, the order shell and 404.
 */
import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, '../dist');
const ssrDir = resolve(here, '../.ssr');
const { render, ORIGIN } = (await import(pathToFileURL(resolve(ssrDir, 'entry-server.js')).href)) as typeof import('../src/entry-server');
const catalog = JSON.parse(readFileSync(resolve(here, '../../.generated/catalog.public.json'), 'utf8')) as {
  rooms: { id: string; built: boolean }[];
  products: { id: string }[];
};

const template = readFileSync(resolve(dist, 'index.html'), 'utf8');
const routes = [
  '/',
  ...catalog.rooms.filter((r) => r.built).map((r) => `/rooms/${r.id}/`),
  ...catalog.products.map((p) => `/p/${p.id}/`),
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
// /order/<id>/ is served by the Worker from this shell (client-rendered: the id and token live in the browser)
mkdirSync(resolve(dist, 'order'), { recursive: true });
writeFileSync(resolve(dist, 'order/index.html'), page('/order/HD-00000000/').replace(/HD-00000000/g, ''));
writeFileSync(resolve(dist, '404.html'), page('/404'));
// robots.txt and sitemap.xml (absolute URLs; ORIGIN changes when the domain is chosen)
const indexable = routes.filter((u) => !['/cart/', '/checkout/'].includes(u));
writeFileSync(
  resolve(dist, 'sitemap.xml'),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${indexable.map((u) => `  <url><loc>${ORIGIN}${u}</loc></url>`).join('\n')}\n</urlset>\n`,
);
writeFileSync(
  resolve(dist, 'robots.txt'),
  ['User-agent: *', 'Disallow: /api/', 'Disallow: /cart/', 'Disallow: /checkout/', 'Disallow: /order/', 'Disallow: /mock-pay/', '', `Sitemap: ${ORIGIN}/sitemap.xml`, ''].join('\n'),
);
rmSync(ssrDir, { recursive: true, force: true });
console.log(`prerendered ${routes.length} pages + order shell + 404`);
