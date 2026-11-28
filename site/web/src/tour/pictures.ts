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
/**
 * MOCK12 (FB29, "בדף שמחוץ לתצוגה בחדר... תמונה שהיא לא חתוכה"): what a product is shown by outside the room — the strip
 * under the room, the wheel and the product's card — in this order:
 *  - `studio`: its studio picture (the product as sold, on the studio's cream), wherever one exists;
 *  - `card`: until then, its layer trimmed to it, with its rim hardened (no feathered rim: tools/make-tour-room.ts);
 *  - `name`: where the room cuts that layer (an occluder over it, the frame's edge), the slot's name on the same cream.
 * Never a crop of the room, never a feathered one, never one an occluder cuts.
 */
export type Outside = { kind: 'studio'; card: TourCard } | { kind: 'card'; card: TourCard } | { kind: 'name'; text: string };
export function outside(s: TourSlot, o: TourOption): Outside {
  const studio = pictures(s, o).studio;
  if (studio) return { kind: 'studio', card: studio };
  return o.cut ? { kind: 'name', text: s.name_he } : { kind: 'card', card: o.card };
}
/** FB20: the wheel's card of an option: its studio picture where there is one, else today's thumbnail; MOCK12: none
 *  where the room cuts it (the wheel names it) */
export const wheelCard = (s: TourSlot, o: TourOption): TourCard | null => {
  const p = outside(s, o);
  return p.kind === 'name' ? null : p.card;
};
