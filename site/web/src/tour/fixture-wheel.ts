/**
 * MOCK6 (briefs/site-mock6-kids-rooms-2026-11-25.md ch. 3): the fixture of ten options for the wheel of many options
 * (ScrollWheel). The kids' art sets (FB12, ten a room) come later, and no real art is faked into the build: the fixture's
 * options are numbered swatches, said to be a demo ("הדגמה טכנית"), never a product, never a price. It opens only with
 * `?fixture=wheel10` in a build behind the flag that is not the Artifact (TourPage), over the room at rest, and changes
 * nothing in the room.
 *
 * Its "patches" are the contract the many-option wheel keeps: the wheel asks for an option only when it rests on it,
 * and a loader (scroll-wheel.ts RestLoader, as the tour's swap does it) loads the newest rest only. What it was asked
 * for is kept on `window.__hdWheelFixture` for the e2e test and the walkthrough.
 */
import { h } from 'preact';
import type { CatalogSlot } from '@hd/shared';
import type { House } from '../house';
import { RestLoader } from '../components/scroll-wheel';

export const FIXTURE_N = 10;
/** quiet, distinct tones of the house's palette, so the swatches read as swatches and nothing else */
const TONES = ['#C9B8A3', '#A8A88E', '#E8D5CC', '#8B6F55', '#D8C8AE', '#B9A48C', '#9FA79A', '#D9B9A8', '#6B4A33', '#ECE5DA', '#A0663A', '#C4C9BD'];

declare global {
  interface Window {
    /** MOCK6: what the fixture's wheel asked for (its "patches"), chose and cancelled */
    __hdWheelFixture?: { loads: number[]; shown: number; chosen: number | null; cancelled: boolean };
  }
}

export function fixtureSlot(n = FIXTURE_N): CatalogSlot {
  return {
    id: 'fixture-wheel',
    name_he: `הדגמה: גלגל של ${n} אפשרויות`,
    on_hold: null,
    options: Array.from({ length: n }, (_, i) => ({
      position: i + 1,
      product_id: null,
      placeholder: false,
      label_he: `דוגמה ${i + 1} (לא מוצר)`,
      is_default: i === 0,
    })),
  } as unknown as CatalogSlot;
}

/** the swatch of option `pos`: a disc of a tone and its number, drawn inline (no file, nothing to load) */
const swatch = (pos: number) =>
  h(
    'svg',
    { class: 'sprite', viewBox: '0 0 100 100', 'aria-hidden': 'true', focusable: 'false' },
    h('circle', { cx: 50, cy: 50, r: 40, fill: TONES[(pos - 1) % TONES.length] }),
    h('text', { x: 50, y: 58, 'text-anchor': 'middle', 'font-size': 26, 'font-weight': 600, fill: '#1E1B18' }, String(pos)),
  );

export function fixtureHouse(): House {
  return {
    style: 'fixture',
    name_he: 'הדגמה',
    status_he: null,
    place_he: '',
    alt_he: null,
    scene: null as never,
    room: null as never,
    sets: false,
    product: () => undefined,
    drawn: () => [],
    thumbNode: (pos) => swatch(pos),
    info: () => h('p', { class: 'specs tour-info' }, h('span', null, 'הדגמה טכנית: אפשרויות פיקטיביות, בלי מחיר')),
  };
}

/** the fixture's loader: what the wheel asks for is recorded, as a patch that takes a moment to come */
export function fixtureLoader(initial = 1, ms = 60): (pos: number) => void {
  const state = { loads: [] as number[], shown: initial, chosen: null as number | null, cancelled: false };
  window.__hdWheelFixture = state;
  const loader = new RestLoader(async (pos) => {
    state.loads.push(pos);
    await new Promise((r) => setTimeout(r, ms));
    state.shown = pos;
  }, initial);
  return (pos) => void loader.rest(pos);
}
