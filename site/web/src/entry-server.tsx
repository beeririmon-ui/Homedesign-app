/** Prerender entry (vite build --ssr): HTML for a URL plus its <head> tags, for SEO in Hebrew. */
import renderToString from 'preact-render-to-string';
import { App } from './App';
import { headFor } from './head';
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
