/**
 * S10: the houses of the room engine (DIR2: every style its own house in the tool). A house is a scene (its layers and
 * camera), a room (the slots on the wheel) and the shop's records of what it sells. The Nordic house ships with the
 * page; another house is a lazy chunk (its data and its set panel), loaded when it is asked for, and only behind the flag
 * (a public build lists none: __HD_PUBLIC__ folds the import away). The address names the house shown: ?style=<id>.
 */
import type { ComponentChildren } from 'preact';
import type { CatalogRoom, PublicProduct } from '@hd/shared';
import type { Scene } from './engine/types';
import { catalog, livingRoom, product, scene } from './catalog';
import { defaultVariantId } from './variants';

export type House = {
  style: string;
  name_he: string;
  /** the house's status on the stage while it is behind the flag; null for the house on the site. S15: a working label,
   *  never public (RoomExperience shows it only in a build behind the flag) */
  status_he: string | null;
  /** S15 (master-designer §1): the room in this house, as a sentence names it ("הסלון בבית הנורדי"): a fixed string,
   *  since in Hebrew the article goes on every word of the phrase */
  place_he: string;
  /** the composed room's description; null: the Nordic one, written in the stage */
  alt_he: string | null;
  /** the line above the list under the room, when the house has its own */
  intro_he?: string;
  scene: Scene;
  room: CatalogRoom;
  product: (id: string | null | undefined) => PublicProduct | undefined;
  /** the wheel's picture of an option, when the house has its own (a set on the sofa) */
  thumb?: (position: number) => string | null;
  /** the wheel's panel for an option sold as a set of pieces, in place of the one product's */
  info?: (position: number) => ComponentChildren;
  /** MOCK1: whether the options on the wheel are sets ("3 סטים"); absent: a house with a panel of its own has sets */
  sets?: boolean;
  /** S12, ת21: the variants the layer of a slot's option draws (a set: every piece of it), as rendered; [] for none */
  drawn: (slotId: string, position: number) => string[];
  /** S15: the products the house sells, in its own order (for the page's ItemList); absent: the room's slots say it */
  sold?: () => PublicProduct[];
  /** S14, ת28: how "החדר שלך" names an option whose layer draws more than one piece (a set: "סט קאמל ופקאן", S15); absent: none does */
  drawnLabel?: (slotId: string, position: number) => string | null;
};

export const NORDIC = 'nordic';
export const nordic: House = {
  style: NORDIC,
  name_he: catalog.styles.find((s) => s.id === NORDIC)?.name_he ?? 'נורדי',
  status_he: null,
  place_he: 'הסלון בבית הנורדי',
  alt_he: null,
  scene,
  room: livingRoom,
  product,
  // the room's layer of an option is its product in the option the room shows (default_sku), never another colour
  drawn: (slotId, position) => {
    const p = product(livingRoom.slots.find((s) => s.id === slotId)?.options.find((o) => o.position === position)?.product_id);
    return p ? [defaultVariantId(p)] : [];
  },
};
/** the switch on the stage: the Nordic house, and the others behind the flag */
export const HOUSES: { style: string; name_he: string }[] = [
  { style: NORDIC, name_he: nordic.name_he },
  ...(__HD_PUBLIC__ ? [] : [{ style: 'warm-modern', name_he: 'מודרני חם' }]),
];

const loading = new Map<string, Promise<House | null>>();
const loaded = new Map<string, House>();
/** The house of a style (cached); null for a style without one, and always in a public build. */
export function loadHouse(style: string): Promise<House | null> {
  if (style === NORDIC) return Promise.resolve(nordic);
  if (__HD_PUBLIC__ || style !== 'warm-modern') return Promise.resolve(null);
  let p = loading.get(style);
  if (!p)
    loading.set(
      style,
      (p = import('./houses/warm-modern').then(
        (m) => (loaded.set(style, m.house), m.house),
        () => (loading.delete(style), null),
      )),
    );
  return p;
}
/**
 * S14, QA ת29: the house of a style when its chunk is already here (the prerender loads it before it renders the
 * house's page, the browser before it hydrates that page), so the page's first render, and so its first paint, is that
 * house's poster: never a stage waiting for it, never another house's picture.
 */
export function houseNow(style: string): House | null {
  return style === NORDIC ? nordic : (loaded.get(style) ?? null);
}
