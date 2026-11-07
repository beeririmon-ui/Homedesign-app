/**
 * The test cart of the story prototype (/test/story/): an in-browser mock of the store API's cart (StoreApi in
 * ../api/types: createCart, getCart, setItem), with the rules of the site's mock (../api/mock.ts): a line per variant,
 * the set by default, 0–20, only what is for sale. Its prices come from the page's data block (the site's pricing code,
 * tools/make-story-page.ts) and not from the bundled site catalog: most products of the story frames are not in the
 * site's room yet. State lives under one key, read and written in try/catch with an in-memory fallback.
 */
import type { Cart, Pack } from '@hd/shared';
import type { StoreApi } from '../api/types';

/** The same shape as the site's ApiError (../api/types), kept here so the test page shares no chunk with the room page. */
export class StoryCartError extends Error {
  constructor(
    public status: number,
    public code: string,
    public messageHe?: string,
  ) {
    super(code);
  }
}

export type StoryVariant = {
  variant_id: string;
  product_id: string;
  name_he: string;
  option_he: string | null;
  price_agorot: number;
  set_qty: number;
  available: boolean;
};
export type KeyValue = { get(k: string): string | null; set(k: string, v: string): void; remove(k: string): void };
type Saved = { id: string; items: { variant_id: string; pack: Pack; qty: number }[] };

export function memoryStore(): KeyValue {
  const m = new Map<string, string>();
  return { get: (k) => m.get(k) ?? null, set: (k, v) => void m.set(k, v), remove: (k) => void m.delete(k) };
}
/** localStorage when it works (it can throw, or be missing, in a private window or a preview), else memory */
export function browserStore(): KeyValue {
  const mem = memoryStore();
  const ls = (): Storage | null => {
    try {
      return typeof localStorage === 'undefined' ? null : localStorage;
    } catch {
      return null;
    }
  };
  return {
    get(k) {
      try {
        return ls()?.getItem(k) ?? mem.get(k);
      } catch {
        return mem.get(k);
      }
    },
    set(k, v) {
      try {
        const s = ls();
        if (s) s.setItem(k, v);
        else mem.set(k, v);
      } catch {
        mem.set(k, v);
      }
    },
    remove(k) {
      try {
        ls()?.removeItem(k);
      } catch {
        /* storage unavailable */
      }
      mem.remove(k);
    },
  };
}

/**
 * The site's price format (@hd/shared/money formatIls: "₪ 1,290" in an LTR isolate, no agorot when whole), repeated here
 * so the test page shares no chunk with the room page; web/test/story-cart.test.ts holds the two equal.
 */
export function priceHe(agorot: number): string {
  const whole = agorot % 100 === 0;
  const n = (agorot / 100).toLocaleString('en-US', { minimumFractionDigits: whole ? 0 : 2, maximumFractionDigits: 2 });
  return `\u2066₪\u00a0${n}\u2069`;
}

export const MAX_QTY = 20;
const rid = () => [...crypto.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, '0')).join('');

export type StoryCart = Pick<StoreApi, 'kind' | 'createCart' | 'getCart' | 'setItem'> & {
  /** adds one more of the variant (a new cart when there is none); the line is capped at MAX_QTY */
  add(variantId: string, qty?: number): Promise<Cart>;
  /** the cart as it stands, or null before the first add */
  current(): Cart | null;
  clear(): void;
};

export function storyCart(variants: StoryVariant[], store: KeyValue = browserStore(), key = 'hd.story.cart'): StoryCart {
  const byId = new Map(variants.map((v) => [v.variant_id, v]));
  // the cart as this page last saved it: the store can drop a write (a private window), and the page keeps working
  let mine: Saved | null = null;
  const load = (): Saved | null => {
    try {
      const s = JSON.parse(store.get(key) ?? 'null') as Saved | null;
      return s && typeof s.id === 'string' && Array.isArray(s.items) ? s : mine && structuredClone(mine);
    } catch {
      return mine && structuredClone(mine);
    }
  };
  const save = (s: Saved) => {
    mine = structuredClone(s);
    try {
      store.set(key, JSON.stringify(s));
    } catch {
      /* kept for this page only */
    }
  };
  const view = (s: Saved): Cart => {
    const lines = s.items.flatMap((i) => {
      const v = byId.get(i.variant_id);
      if (!v || !v.available) return []; // a variant that left the page or stopped being sold drops out, as on the site
      return [
        {
          variant_id: v.variant_id,
          product_id: v.product_id,
          name_he: v.name_he,
          option_he: v.option_he,
          pack: i.pack,
          pack_qty: v.set_qty,
          qty: i.qty,
          unit_price_agorot: v.price_agorot,
          line_total_agorot: v.price_agorot * i.qty,
          price_provisional: true,
        },
      ];
    });
    return { id: s.id, lines, subtotal_agorot: lines.reduce((n, l) => n + l.line_total_agorot, 0), count: lines.reduce((n, l) => n + l.qty, 0) };
  };
  const open = (id: string): Saved => {
    const s = load();
    if (!s || s.id !== id) throw new StoryCartError(404, 'cart_not_found');
    return s;
  };
  const api: StoryCart = {
    kind: 'mock',
    async createCart() {
      const s: Saved = { id: rid(), items: [] };
      save(s);
      return view(s);
    },
    async getCart(id) {
      return view(open(id));
    },
    async setItem(cartId, variantId, pack, qty) {
      const s = open(cartId);
      const v = byId.get(variantId);
      if (!v || !v.available) throw new StoryCartError(404, 'variant_not_found', 'המוצר לא זמין.');
      if (pack !== 'set') throw new StoryCartError(422, 'pack_unavailable', 'בעמוד הבדיקה המוצר נמכר כפי שהוא בתמונה.');
      if (!Number.isInteger(qty) || qty < 0 || qty > MAX_QTY) throw new StoryCartError(422, 'invalid_body');
      const at = s.items.findIndex((i) => i.variant_id === variantId && i.pack === pack);
      if (qty === 0) s.items = s.items.filter((_, i) => i !== at);
      else if (at >= 0) s.items[at] = { variant_id: variantId, pack, qty };
      else s.items.push({ variant_id: variantId, pack, qty });
      save(s);
      return view(s);
    },
    async add(variantId, qty = 1) {
      const id = load()?.id ?? (await api.createCart()).id;
      const now = load()?.items.find((i) => i.variant_id === variantId && i.pack === 'set')?.qty ?? 0;
      return api.setItem(id, variantId, 'set', Math.min(MAX_QTY, now + qty));
    },
    current() {
      const s = load();
      return s ? view(s) : null;
    },
    clear() {
      mine = null;
      try {
        store.remove(key);
      } catch {
        /* storage unavailable */
      }
    },
  };
  return api;
}
