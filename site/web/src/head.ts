/** Per-route <head> for prerendering (SEO in Hebrew) and for client-side navigation (document.title). */
import { ilsNumber } from '@hd/shared/money';
import type { Route } from './router';
import { catalog, livingRoom, productBySegment, slotOf } from './catalog';
import { shopPath } from '@hd/shared/product-url';
import { mediaUrl } from './media';
import { scene } from './catalog';
import { galleryImages } from './components/Media';
import { optionsOf } from './variants';
import { HOUSES, NORDIC, houseNow, type House } from './house';
import { metaDescription } from '@hd/shared/meta-text';

export type Head = { title: string; description: string; canonical: string; jsonLd: object[]; noindex?: boolean; preload?: string };

const SITE = 'הבית';
export const ORIGIN = 'https://example.co.il'; // replaced when the domain is chosen (docs/architecture.md, open decisions)

/**
 * S15 (QA, master-designer §4): the house a room page shows. The address names it (?style=<id>, S10); a style that is
 * not a house of this build (every style but the Nordic one in a public build) is the Nordic page.
 */
export function houseOf(route: Extract<Route, { name: 'room' }>): string {
  return route.style && route.style !== NORDIC && HOUSES.some((h) => h.style === route.style) ? route.style : NORDIC;
}

/**
 * S15 (master-designer §4): each house's room page, its own title and description. The same shape in every house: the
 * style, then three words of material and light. The warm-modern house says what can be swapped there today (the set of
 * cushions and throw); once it has more slots on the wheel, the Nordic sentence.
 */
const ROOM_HEAD: Record<string, { title: string; crumb?: string; description: (h: House | null) => string }> = {
  'living-room/nordic': {
    title: 'סלון נורדי: לבן חם, אלון ואור חורף',
    description: () => 'סלון נורדי באור חורף של שלוש אחר הצהריים, בלבן חם, בשיבולת שועל ובאלון בהיר. נוגעים בפריט, מחליפים גרסה ורואים את החדר מתעדכן.',
  },
  'living-room/warm-modern': {
    title: 'סלון מודרני חם: בוקלה, אגוז ואבן',
    crumb: 'סלון מודרני חם',
    description: (h) =>
      `סלון מודרני חם: קירות טיח, ספת בוקלה, שולחן קפה מאגוז וספסל אבן בחלון, באור חורף של אחר הצהריים. ${
        (h?.room.slots.length ?? 1) > 1 ? 'נוגעים בפריט, מחליפים גרסה ורואים את החדר מתעדכן.' : 'בוחרים סט כריות ושמיכה ורואים אותו על הספה.'
      }`,
  },
};

export function canonicalPath(route: Route): string {
  switch (route.name) {
    case 'home':
      return '/';
    case 'room': {
      // S15: a house's page is its own page (its own title, its own products): the canonical names its house
      const style = houseOf(route);
      return `/rooms/${route.room}/${style === NORDIC ? '' : `?style=${style}`}`;
    }
    case 'product': {
      const hit = productBySegment(route.id);
      return hit ? shopPath(hit.product.id) : `/p/${route.id}/`;
    }
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
  // MOCK1: the tour's door, a mock-up behind the flag, never indexed (a public build folds this away: it has no such page)
  if (typeof __TOUR__ !== 'undefined' && __TOUR__ && route.name === 'tour')
    return { title: `סיור בבית · ${SITE}`, description: '', canonical, jsonLd: [], noindex: true };
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
      const style = houseOf(route);
      const house = houseNow(style);
      const copy = ROOM_HEAD[`${r.id}/${style}`] ?? ROOM_HEAD[`${r.id}/${NORDIC}`]!;
      // S15: the products of the house shown, never another house's: the Nordic room's products, or the pieces the
      // house sells (its sets); a product has its url when the shop has its page
      const sold = style === NORDIC ? catalog.products.filter((p) => p.room === r.id) : (house?.sold?.() ?? []);
      return {
        title: `${copy.title} · ${SITE}`,
        description: copy.description(house),
        canonical,
        jsonLd: [
          crumbs([
            ['בית', '/'],
            [copy.crumb ?? r.name_he, canonicalPath(route)],
          ]),
          {
            '@context': 'https://schema.org',
            '@type': 'ItemList',
            itemListElement: sold.map((p, i) => ({
              '@type': 'ListItem',
              position: i + 1,
              ...(productBySegment(p.id) ? { url: `${ORIGIN}${shopPath(p.id)}` } : {}),
              name: p.name_he,
            })),
          },
        ],
      };
    }
    case 'product': {
      const p = productBySegment(route.id)?.product;
      if (!p) return { title: `לא נמצא · ${SITE}`, description: '', canonical, jsonLd: [], noindex: true };
      const where = slotOf(p);
      // S15: a public build withholds a supplier photo without confirmed rights; a product with no picture left has no image
      const images = galleryImages(p).map((im) => new URL(im.src, `${ORIGIN}/`).href);
      const ld: Record<string, unknown> = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        name: p.name_he,
        description: p.description_he,
        sku: p.id,
        // FR-I: the render from the room first, the supplier's original photo after it
        image: images.length ? images : undefined,
        color: p.color_hex,
        material: p.materials_he.join(', ') || undefined,
      };
      // No offer markup while the price is provisional: search engines must never index a price we do not sell at.
      if (!p.price_provisional) {
        // supplier options (2026-10-11): one offer range over the options sold at a final price
        const sold = optionsOf(p)?.skus.filter((s) => s.available && !s.price_provisional) ?? [];
        const prices = sold.map((s) => s.price_agorot);
        ld.offers =
          sold.length > 1
            ? {
                '@type': 'AggregateOffer',
                lowPrice: ilsNumber(Math.min(...prices)),
                highPrice: ilsNumber(Math.max(...prices)),
                offerCount: sold.length,
                priceCurrency: 'ILS',
                availability: 'https://schema.org/InStock',
                url: canonical,
              }
            : { '@type': 'Offer', price: ilsNumber(p.price_agorot), priceCurrency: 'ILS', availability: 'https://schema.org/InStock', url: canonical };
      }
      return {
        title: `${p.name_he} · ${SITE}`,
        // S15 (§5): cut where a sentence ends, never in the middle of a word
        description: metaDescription(p.description_he),
        canonical,
        jsonLd: [
          ld,
          crumbs([
            ['בית', '/'],
            [livingRoom.name_he, `/rooms/${p.room}/`],
            [where?.slot.name_he ?? p.name_he, shopPath(p.id)],
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
