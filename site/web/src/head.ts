/** Per-route <head> for prerendering (SEO in Hebrew) and for client-side navigation (document.title). */
import { ilsNumber } from '@hd/shared/money';
import type { Route } from './router';
import { catalog, livingRoom, product, slotOf } from './catalog';
import { mediaUrl } from './media';
import { scene } from './catalog';

export type Head = { title: string; description: string; canonical: string; jsonLd: object[]; noindex?: boolean; preload?: string };

const SITE = 'הבית';
export const ORIGIN = 'https://example.co.il'; // replaced when the domain is chosen (docs/architecture.md, open decisions)

export function canonicalPath(route: Route): string {
  switch (route.name) {
    case 'home':
      return '/';
    case 'room':
      return `/rooms/${route.room}/`;
    case 'product':
      return `/p/${route.id}/`;
    case 'legal':
      return `/${route.page}/`;
    case 'cart':
      return '/cart/';
    case 'checkout':
      return '/checkout/';
    case 'order':
      return `/order/${route.id}/`;
    default:
      return '/404';
  }
}

export function headFor(route: Route): Head {
  const canonical = `${ORIGIN}${canonicalPath(route)}`;
  const crumbs = (items: [string, string][]) => ({
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map(([name, path], i) => ({ '@type': 'ListItem', position: i + 1, name, item: `${ORIGIN}${path}` })),
  });
  switch (route.name) {
    case 'home':
      return {
        title: `${SITE} · בית אחד, עיצוב נורדי, כל פריט נמכר`,
        description: 'סיור בבית מעוצב: נוגעים בכל פריט בחדר, בוחרים גרסה ורואים את החדר מתעדכן. מתחילים בסלון הנורדי.',
        canonical,
        jsonLd: [{ '@context': 'https://schema.org', '@type': 'WebSite', name: SITE, url: `${ORIGIN}/`, inLanguage: 'he' }],
        preload: mediaUrl(scene.hall.src, 1920, 'webp'),
      };
    case 'room': {
      const r = livingRoom;
      return {
        title: `${r.name_he} נורדי · ${SITE}`,
        description: `סלון נורדי עם ${r.slots.length} עמדות מוצר: וילונות, שטיח, תאורה, טקסטיל וקרמיקה. בחרו גרסה לכל פריט וראו אותה בחדר.`,
        canonical,
        jsonLd: [
          crumbs([
            ['בית', '/'],
            [r.name_he, `/rooms/${r.id}/`],
          ]),
          {
            '@context': 'https://schema.org',
            '@type': 'ItemList',
            itemListElement: catalog.products
              .filter((p) => p.room === r.id)
              .map((p, i) => ({ '@type': 'ListItem', position: i + 1, url: `${ORIGIN}/p/${p.id}/`, name: p.name_he })),
          },
        ],
      };
    }
    case 'product': {
      const p = product(route.id);
      if (!p) return { title: `לא נמצא · ${SITE}`, description: '', canonical, jsonLd: [], noindex: true };
      const where = slotOf(p);
      const ld: Record<string, unknown> = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        name: p.name_he,
        description: p.description_he,
        sku: p.id,
        color: p.color_hex,
        material: p.materials_he.join(', ') || undefined,
      };
      // No offer markup while the price is provisional: search engines must never index a price we do not sell at.
      if (!p.price_provisional)
        ld.offers = { '@type': 'Offer', price: ilsNumber(p.price_agorot), priceCurrency: 'ILS', availability: 'https://schema.org/InStock', url: canonical };
      return {
        title: `${p.name_he} · ${SITE}`,
        description: p.description_he.slice(0, 155),
        canonical,
        jsonLd: [
          ld,
          crumbs([
            ['בית', '/'],
            [livingRoom.name_he, `/rooms/${p.room}/`],
            [where?.slot.name_he ?? p.name_he, `/p/${p.id}/`],
          ]),
        ],
      };
    }
    case 'cart':
      return { title: `סל הקניות · ${SITE}`, description: '', canonical, jsonLd: [], noindex: true };
    case 'checkout':
      return { title: `תשלום · ${SITE}`, description: '', canonical, jsonLd: [], noindex: true };
    case 'order':
      return { title: `סטטוס הזמנה · ${SITE}`, description: '', canonical, jsonLd: [], noindex: true };
    case 'mock-pay':
      return { title: `תשלום מדומה · ${SITE}`, description: '', canonical, jsonLd: [], noindex: true };
    case 'legal': {
      const t = { accessibility: 'הצהרת נגישות', terms: 'תקנון', privacy: 'מדיניות פרטיות', returns: 'ביטולים והחזרות' }[route.page];
      return { title: `${t} · ${SITE}`, description: `${t} (טיוטה).`, canonical, jsonLd: [] };
    }
    default:
      return { title: `הדף לא נמצא · ${SITE}`, description: '', canonical, jsonLd: [], noindex: true };
  }
}
