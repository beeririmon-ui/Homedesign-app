/** FB20 (2026-11-26, briefs/site-wheel-3d-2026-11-26.md): the option's two pictures, apart from the tour's data (no
 *  import runs here: the unit tests read it on its own) */
import type { TourCard, TourOption, TourSlot } from './data';

/**
 * FB20: the two pictures of an option (the contract of the 3D wheel, site/README.md):
 *  - `studio`: what the wheel shows — the option's studio picture (`TourOption.studio`, or a `card` that already is one),
 *    else null and the wheel shows `card`;
 *  - `in_room`: the product in use, as the room draws it — the option's layer on its room's atlas pages, or (MOCK6, a
 *    wheel of many) its patch file; the selection's reveal cross-fades it in. It is the engine's own layer, never a
 *    second picture.
 */
export type OptionPictures = {
  studio: TourCard | null;
  in_room: { kind: 'layer' | 'patch'; slot: string; position: number };
};
export const pictures = (s: TourSlot, o: TourOption): OptionPictures => ({
  studio: o.studio ?? (o.card.source === 'studio' ? o.card : null),
  in_room: { kind: s.lazy ? 'patch' : 'layer', slot: s.id, position: o.position },
});
/** FB20: the wheel's card of an option: its studio picture where there is one, else today's thumbnail */
export const wheelCard = (s: TourSlot, o: TourOption): TourCard => pictures(s, o).studio ?? o.card;
