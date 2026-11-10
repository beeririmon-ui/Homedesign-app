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

export type House = {
  style: string;
  name_he: string;
  /** the house's status on the stage while it is behind the flag; null for the house on the site */
  status_he: string | null;
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
};

export const NORDIC = 'nordic';
export const nordic: House = {
  style: NORDIC,
  name_he: catalog.styles.find((s) => s.id === NORDIC)?.name_he ?? 'נורדי',
  status_he: null,
  alt_he: null,
  scene,
  room: livingRoom,
  product,
};
/** the switch on the stage: the Nordic house, and the others behind the flag */
export const HOUSES: { style: string; name_he: string }[] = [
  { style: NORDIC, name_he: nordic.name_he },
  ...(__HD_PUBLIC__ ? [] : [{ style: 'warm-modern', name_he: 'מודרני חם' }]),
];

const loading = new Map<string, Promise<House | null>>();
/** The house of a style (cached); null for a style without one, and always in a public build. */
export function loadHouse(style: string): Promise<House | null> {
  if (style === NORDIC) return Promise.resolve(nordic);
  if (__HD_PUBLIC__ || style !== 'warm-modern') return Promise.resolve(null);
  let p = loading.get(style);
  if (!p)
    loading.set(
      style,
      (p = import('./houses/warm-modern').then(
        (m) => m.house,
        () => (loading.delete(style), null),
      )),
    );
  return p;
}
