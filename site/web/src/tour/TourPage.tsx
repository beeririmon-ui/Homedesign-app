/**
 * MOCK1 (2026-11-12): the wow-tour mock-up, behind HD_PUBLIC=0 (rules TOUR1, TOUR2, MOCK1; the designer's brief
 * docs/proposals/wow-tour-experience-2026-11-12.md). The page opens at the door (temporary, in code): a portal with the
 * real empty living room of the warm-modern house in it. "היכנסו לסלון" grows the portal into the room, the products are
 * revealed (three concepts, switchable), a product opens its close-up and the wheel, and the house changes to the Nordic
 * one and back. The engine and the effects are a chunk of their own (./stage), loaded after the door is painted.
 *
 * MOCK3 (2026-11-13), the owner's feedback FB2 and FB3 (docs/proposals/tour-whole-frame-phone-2026-11-13.md):
 *  - one 16:9 window in every phase, never cropped; the door, the way in, the reveal, the style change and the close-up
 *    all happen inside it, and the window never changes size while anything moves;
 *  - on the picture, only the products' marks. The title, the counter, the list of products (a strip under the window)
 *    and the wheel sit in the bands round the window; the rooms, the style and the mock-up's switches fold into one
 *    control, "המשך הסיור", and its panel;
 *  - the visitor may zoom (a pinch, a button), up to ×2.5, and comes back to the whole frame;
 *  - everything round the window is in the page from the start and changes by opacity and transform only.
 */
import { useEffect, useRef, useState } from 'preact/hooks';
import type { CatalogSlot } from '@hd/shared';
import { formatIls } from '@hd/shared/money';
import { shopPath } from '@hd/shared/product-url';
import '../styles/tour.css';
import { clampCam, coverSize, frameToScreen, screenToFrame } from '../engine/camera';
import type { Cam } from '../engine/types';
import { product } from '../catalog';
import type { House } from '../house';
import { mediaUrl } from '../media';
import { prefersReducedMotion, timeScale } from '../motion';
import { announce } from '../state/ui';
import { NOT_FOR_SALE_HE } from '../set-copy';
import { IconDoor } from '../components/Icons';
import { Price } from '../components/Media';
import type { VariantWheel as WheelComponent } from '../components/VariantWheel';
import { NORDIC, NORDIC_NAME_HE, WM, cardUrl, tour, type HouseId, type TourOption, type TourSlot } from './data';
import type { TourEngine } from './engine';
import { metrics, report, statLine } from './metrics';
import type { Reveal, Style, Swap, Ui } from './fx';
import { MQ, ZOOM, closeReserve, doorRect, pinchZoom, rubber, tapRule, wheelArc, type Layout, type Mark } from './layout';

type Stage = typeof import('./stage');
declare global {
  interface Window {
    __hdTour?: TourEngine;
    /** the page's state for the tests and the evidence: where the visitor is, and whether anything is moving */
    __hdTourState?: { phase: Phase; busy: boolean; house: HouseId };
    /** the effects and the page's marks, for the tests and the frame-rate evidence (they run an effect on its own) */
    __hdTourFx?: Stage & { ui: Ui };
  }
}
type Phase = 'door' | 'entering' | 'room';
type Cfg = {
  fx: Reveal;
  sw: Swap;
  st: Style;
  way: 'empty' | 'full';
  skip: boolean;
  /** MOCK3, the temporary switches: the whole frame or "מילוי וגרירה" (the earlier mode), the strip or the dots
   *  alone, a double tap that zooms, the paper or a dark page round the window, and the sharper canvas while zoomed */
  frame: 'whole' | 'fill';
  pick: 'list' | 'dots';
  zoom: 'pinch' | 'double';
  bg: 'paper' | 'dark';
  sharp: boolean;
};
const DEFAULTS: Cfg = { fx: 'b', sw: 's1', st: 'y1', way: 'empty', skip: false, frame: 'whole', pick: 'list', zoom: 'pinch', bg: 'paper', sharp: false };
const pick = <T extends string>(v: string | null, of: readonly T[], d: T): T => (of.includes(v as T) ? (v as T) : d);
function readCfg(): Cfg {
  const q = new URLSearchParams(location.search);
  return {
    fx: pick(q.get('fx'), ['a', 'b', 'c'] as const, DEFAULTS.fx),
    sw: pick(q.get('sw'), ['s1', 's2', 's3'] as const, DEFAULTS.sw),
    st: pick(q.get('st'), ['y1', 'y2'] as const, DEFAULTS.st),
    way: pick(q.get('way'), ['empty', 'full'] as const, DEFAULTS.way),
    skip: q.get('skip') === '1',
    frame: pick(q.get('frame'), ['whole', 'fill'] as const, DEFAULTS.frame),
    pick: pick(q.get('pick'), ['list', 'dots'] as const, DEFAULTS.pick),
    zoom: pick(q.get('zoom'), ['pinch', 'double'] as const, DEFAULTS.zoom),
    bg: pick(q.get('bg'), ['paper', 'dark'] as const, DEFAULTS.bg),
    sharp: q.get('sharp') === '1',
  };
}

export { doorRect };

/** where the camera looks from the door on a narrow screen: the window and its light (the room's rest is on the sofa) */
export const DOOR_CU = 0.2;

const optionOf = (s: TourSlot, sel: Record<string, number>): TourOption => s.options[(sel[s.id] ?? 1) - 1]!;
/** PRE1: a product the shop has and cannot sell now says so; a card the shop does not have yet is "עוד לא במכירה" */
const OUT_HE = 'המלאי אינו זמין כעת';
const priceHe = (o: TourOption): string => (o.set ? '' : !o.product_id ? NOT_FOR_SALE_HE : o.price_agorot && o.available ? formatIls(o.price_agorot) : OUT_HE);
const nameHe = (s: TourSlot, o: TourOption): string => o.name_he ?? s.name_he;
/** the slot as the wheel reads it: its options by name; the price and the way to the product are the panel's */
const wheelSlot = (s: TourSlot): CatalogSlot =>
  ({
    id: s.id,
    name_he: s.name_he,
    on_hold: null,
    options: s.options.map((o) => ({ position: o.position, product_id: null, placeholder: false, label_he: nameHe(s, o), is_default: o.position === 1 })),
  }) as unknown as CatalogSlot;
function wheelHouse(s: TourSlot): House {
  return {
    style: WM,
    name_he: tour.name_he,
    status_he: null,
    place_he: '',
    alt_he: null,
    scene: null as never,
    room: null as never,
    sets: s.options[0]!.set,
    product: () => undefined,
    drawn: () => [],
    // MOCK2 (FB1): the product on its own — our own studio picture where one passed QA, else its layer trimmed to it
    thumb: (pos) => cardUrl(s.options[pos - 1]!),
    cardGround: s.ground,
    info: (pos) => {
      const o = s.options[pos - 1]!;
      // the product's own page, when the shop has one
      const page = o.product_id && product(o.product_id) ? shopPath(o.product_id) : null;
      return (
        <p class="specs tour-info" key={pos}>
          {o.price_agorot && o.available ? <Price agorot={o.price_agorot} provisional={o.price_provisional} /> : o.set ? null : <span>{priceHe(o)}</span>}
          {page ? <a href={page}>לעמוד המוצר</a> : null}
        </p>
      );
    },
  };
}

/** the next animation frame: the page has rendered and laid out what was just asked of it */
const frame = (): Promise<void> => new Promise((r) => requestAnimationFrame(() => r()));
/** a tiny plan of the house, three cells; the room the visitor is in is brass (FB3: "ריבוע קטן למטה שיסמן את המשך הסיור") */
const PlanIcon = ({ at }: { at: 'entry' | 'living' | 'rest' }) => (
  <svg class="tour-plan" viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">
    <rect x="2" y="2" width="9" height="16" data-on={at === 'living' ? '' : undefined} />
    <rect x="11" y="2" width="7" height="8" data-on={at === 'rest' ? '' : undefined} />
    <rect x="11" y="10" width="7" height="8" data-on={at === 'entry' ? '' : undefined} />
  </svg>
);
const IconZoom = ({ out }: { out: boolean }) => (
  <svg
    viewBox="0 0 24 24"
    width="22"
    height="22"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    aria-hidden="true"
    focusable="false"
  >
    {out ? <path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5" /> : <path d="M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13zM15.5 15.5 20 20M8 10.5h5M10.5 8v5" />}
  </svg>
);
type Eye = HouseId | 'rotate';

export function TourPage() {
  const stage = useRef<HTMLElement>(null);
  const win = useRef<HTMLDivElement>(null);
  const top = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const fold = useRef<HTMLButtonElement>(null);
  const engine = useRef<TourEngine | null>(null);
  const mod = useRef<Stage | null>(null);
  const starting = useRef<Promise<TourEngine | null> | null>(null);
  const spots = useRef(new Map<string, HTMLButtonElement>());
  const tiles = useRef(new Map<string, HTMLButtonElement>());
  const rings = useRef(new Map<string, HTMLSpanElement>());
  /** MOCK2: one Animation per ring, played again rather than built again */
  const anims = useRef(new Map<HTMLElement, { a: Animation; flat: number; ms: number; size: number }>());
  /** a phone, upright or on its side: no labels over the room, and a ring of 32 px at most (tour.css: the same query) */
  const narrow = useRef(typeof matchMedia === 'function' ? matchMedia('(max-width: 700px), (max-height: 500px)') : null);
  const dimEls = useRef(new Map<string, HTMLSpanElement>());
  const title = useRef<HTMLHeadingElement>(null);
  const [phase, setPhaseState] = useState<Phase>('door');
  const [busy, setBusyState] = useState(false);
  const [ready, setReady] = useState(false);
  /** MOCK2: the room can be animated with nothing left to load (the door waits for it) */
  const [warm, setWarm] = useState(false);
  const [noGl, setNoGl] = useState(false);
  const [house, setHouse] = useState<HouseId>(WM);
  const [cfg, setCfgState] = useState<Cfg>(DEFAULTS);
  const [sel, setSel] = useState<Record<string, number>>(() => Object.fromEntries(tour.slots.map((s) => [s.id, 1])));
  const [open, setOpenState] = useState<{ slot: TourSlot; before: number } | null>(null);
  const [Wheel, setWheel] = useState<typeof WheelComponent | null>(null);
  const countEl = useRef<HTMLParagraphElement>(null);
  const [stat, setStat] = useState('');
  /** MOCK3: which of the three layouts the screen gets, and the window's size — measured on load, resize and rotation */
  const [lay, setLay] = useState<Layout>('desk');
  const [winSize, setWinSize] = useState({ w: 1280, h: 720, vh: 800 });
  const [zoomed, setZoomedState] = useState(false);
  const [more, setMoreState] = useState(false);
  /** the line over the room's name: the house, or once a visit the invitation to turn the phone */
  const [eye, setEyeState] = useState<Eye>(WM);
  // what the engine's callbacks and the queued presses read (they outlive a render)
  const live = useRef({ phase, busy, house, cfg, sel, open, lay, zoomed, more });
  live.current = { phase, busy, house, cfg, sel, open, lay, zoomed, more };
  /** the window's place in the page (CSS px), from the same measurement */
  const box = useRef({ x: 0, y: 0, w: 1, h: 1 });
  const queued = useRef<(() => void) | null>(null);
  const hint = useRef(0);
  const idleLoad = useRef(0);
  const resized = useRef(false);
  const tell = () => (window.__hdTourState = { phase: live.current.phase, busy: live.current.busy, house: live.current.house });
  const setPhase = (p: Phase) => {
    live.current.phase = p;
    setPhaseState(p);
    tell();
  };
  const setBusy = (b: boolean) => {
    live.current.busy = b;
    setBusyState(b);
    tell();
    if (b) return;
    // the phone was turned while something moved: the camera is put where the new window wants it
    if (resized.current) relayout();
    // a press made while something moved is done when it ends (the designer's order)
    if (queued.current) {
      const fn = queued.current;
      queued.current = null;
      fn();
    }
  };
  const setCfg = (c: Partial<Cfg>) => {
    live.current.cfg = { ...live.current.cfg, ...c };
    setCfgState(live.current.cfg);
  };
  const setOpen = (o: { slot: TourSlot; before: number } | null) => {
    live.current.open = o;
    setOpenState(o);
  };
  const setZoomed = (z: boolean) => {
    if (z) everZoomed.current = true;
    if (live.current.zoomed === z) return;
    live.current.zoomed = z;
    setZoomedState(z);
  };
  const everZoomed = useRef(false);
  /** written to the page directly as well: it changes in the middle of a style change, and that is not a render */
  const setEye = (k: Eye) => {
    top.current?.setAttribute('data-eye', k);
    setEyeState(k);
  };
  useEffect(() => {
    live.current.house = house;
    tell();
  }, [house]);
  const whole = () => live.current.cfg.frame === 'whole';
  /** a phone's rules: the marks are decoration, the window is the touch target and the strip is the list */
  const phoneRules = () => live.current.lay !== 'desk' && whole();

  // ---------- the window's size: on load, on a resize, on a rotation — never while anything of ours moves ----------
  function measure() {
    const el = win.current;
    if (!el) return;
    const m = metrics.dom(() => {
      const r = el.getBoundingClientRect();
      return {
        x: r.left + scrollX,
        y: r.top + scrollY,
        w: r.width,
        h: r.height,
        vh: innerHeight,
        lay: (matchMedia(MQ.portrait).matches ? 'portrait' : matchMedia(MQ.rails).matches ? 'rails' : 'desk') as Layout,
      };
    });
    box.current = m;
    live.current.lay = m.lay;
    setLay(m.lay);
    setWinSize((was) => (was.w === m.w && was.h === m.h && was.vh === m.vh ? was : { w: m.w, h: m.h, vh: m.vh }));
  }
  /** the camera for the window as it is now: a close-up is put back, a zoom is dropped, the door stays the door */
  function relayout() {
    resized.current = false;
    const e = engine.current;
    if (!e) return;
    const o = live.current.open;
    e.cam = o ? closeCam(e, o.slot) : live.current.phase === 'door' ? e.atDoor() : { ...e.rest };
    setZoomed(false);
    place();
    e.render();
  }

  // ---------- the marks over the room (DOM, placed when the camera lands) ----------
  /**
   * MOCK2 (FB1): this runs when the camera lands and on a resize — never on the frames of a move. It writes a
   * transform for every mark, and doing that inside an animation is a style recalculation in the middle of the frame.
   * The marks are invisible while the camera travels anyway. MOCK3: it measures nothing; the window's size is the
   * engine's (measured on load and on a resize), and a label's width is measured once, at rest.
   */
  function place() {
    const st = stage.current;
    const e = engine.current;
    if (!st || !e) return;
    const { vp, cam } = e;
    const d = doorRect(vp.w, vp.h, whole());
    st.style.setProperty('--tk', String(timeScale()));
    for (const [k, v] of Object.entries({ '--dx': d.cx, '--dy': d.cy, '--dw': d.hw * 2, '--dh': d.hh * 2, '--dr': d.r }))
      st.style.setProperty(k, `${v.toFixed(1)}px`);
    if (live.current.phase === 'door' && !live.current.busy) {
      e.d.door = [d.cx, d.cy, d.hw, d.hh];
      e.d.doorR = d.r;
      e.doorCu = DOOR_CU;
    }
    for (const s of tour.slots) {
      s.anchors.forEach(([u, v], i) => {
        const p = frameToScreen(u, v, cam, vp, tour.aspect);
        const ring = rings.current.get(`${s.id}:${i}`);
        if (ring) ring.style.transform = `translate(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px)`;
        if (i) return;
        const el = spots.current.get(s.id);
        if (!el) return;
        el.style.transform = `translate(${(p.x - 23).toFixed(1)}px, ${(p.y - 23).toFixed(1)}px)`;
        el.style.visibility = p.x > 12 && p.x < vp.w - 12 && p.y > 12 && p.y < vp.h - 12 ? 'visible' : 'hidden';
        // the label opens toward the room's middle
        el.toggleAttribute('data-flip', p.x < vp.w * 0.3);
      });
      const dim = dimEls.current.get(s.id);
      if (dim) {
        const b = optionOf(s, live.current.sel).box;
        const a = frameToScreen(b[0], b[3], cam, vp, tour.aspect);
        const z = frameToScreen(b[1], b[3], cam, vp, tour.aspect);
        dim.style.transform = `translate(${a.x.toFixed(1)}px, ${Math.min(vp.h - 30, a.y + 6).toFixed(1)}px)`;
        dim.style.width = `${Math.max(0, z.x - a.x).toFixed(1)}px`;
      }
    }
    if (cam.z < 1.001 && !live.current.busy) spread();
  }
  /** where a slot's mark is in the window now (CSS px), or null when it is out of view */
  function markOf(s: TourSlot, e: TourEngine): Mark | null {
    const [u, v] = s.anchors[0]!;
    const p = frameToScreen(u, v, e.cam, e.vp, tour.aspect);
    return p.x > 0 && p.x < e.vp.w && p.y > 0 && p.y < e.vp.h ? { id: s.id, x: p.x, y: p.y } : null;
  }
  /** the labels never cover one another: a label that would is moved up or down a row (wide screens; a phone has none) */
  const tagW = useRef(new Map<string, number>());
  function spread() {
    if (narrow.current?.matches) return;
    const placed: [number, number, number, number][] = [];
    for (const s of tour.slots) {
      const el = spots.current.get(s.id);
      const tag = el?.querySelector<HTMLElement>('.tag');
      if (!el || !tag || el.style.visibility === 'hidden') continue;
      const text = tag.textContent ?? '';
      let w = tagW.current.get(text);
      // measured once per label, and only at rest (MOCK2: a measurement is what forces a layout)
      if (w === undefined) tagW.current.set(text, (w = metrics.dom(() => tag.offsetWidth)));
      const m = /translate\(([-\d.]+)px, ([-\d.]+)px\)/.exec(el.style.transform);
      if (!m || !w) continue;
      const cx = Number(m[1]) + 23;
      const cy = Number(m[2]) + 23;
      const x0 = el.hasAttribute('data-flip') ? cx + 13 : cx - 13 - w;
      const hit = (y: number) => placed.some((r) => x0 < r[1] + 6 && x0 + w! > r[0] - 6 && y - 15 < r[3] && y + 15 > r[2]);
      const dy = [0, -30, 30, -60, 60, -90].find((d) => !hit(cy + d)) ?? 0;
      el.style.setProperty('--ty', `${dy}px`);
      placed.push([x0, x0 + w, cy + dy - 15, cy + dy + 15]);
    }
  }
  const k = () => timeScale();
  /**
   * MOCK2: the first time a ring is animated the browser resolves its style and sets up a compositor animation, and
   * that landed inside the reveal's first frames. Every ring is given its animation — and has it cancelled — while
   * the visitor is still at the door.
   */
  function primeRings() {
    if (prefersReducedMotion()) return;
    for (const el of rings.current.values()) {
      const i = el.firstElementChild as HTMLElement | null;
      if (!i) continue;
      i.style.setProperty('--ring', '8px');
      i.animate([{ opacity: 0 }, { opacity: 0 }], { duration: 1 }).cancel();
    }
  }
  /** the strip's tile of a product rises with it, and leaves with it (opacity and a few pixels; tour.css) */
  function tile(id: string, on: boolean, delay = 0) {
    const el = tiles.current.get(id);
    if (!el) return;
    el.style.transitionDelay = delay ? `${delay * k()}ms` : '';
    el.toggleAttribute('data-on', on);
  }
  const ui: Ui = {
    ring(s, kind) {
      if (prefersReducedMotion()) return;
      const [full, ms] = kind === 'burst' ? [132, 620] : kind === 'small' ? [72, 480] : kind === 'tile' ? [32, 320] : [56, 420];
      // the phone: a ring of 32 px at the most (the designer; the whole frame is small there)
      const size = narrow.current?.matches ? Math.min(full, 32) : full;
      s.anchors.forEach((_, i) => {
        const el = rings.current.get(`${s.id}:${i}`)?.firstElementChild as HTMLElement | null;
        if (!el) return;
        // MOCK2: one custom property for the size (the CSS does the rest) and one Animation per ring, played again
        // instead of built again — a ring fires inside the reveal, on a product's own frame
        const flat = kind === 'touch' ? 0.34 : 1;
        const was = anims.current.get(el);
        if (was && was.flat === flat && was.ms === ms && was.size === size) {
          was.a.currentTime = 0;
          was.a.play();
          return;
        }
        el.style.setProperty('--ring', `${size}px`);
        was?.a.cancel();
        const a = el.animate(
          [
            { opacity: 0.95, transform: `scale(0.08) scaleY(${flat})` },
            { opacity: 0, transform: `scale(1) scaleY(${flat})` },
          ],
          { duration: ms * k(), easing: 'cubic-bezier(0.16, 1, 0.3, 1)' },
        );
        anims.current.set(el, { a, flat, ms, size });
      });
    },
    label(s, on) {
      // MOCK3: the product's tile in the strip rises at the moment the product takes form (one attribute, its own)
      if (s && on) tile(s.id, true);
      // MOCK2: on a phone the labels are not shown at all (tour.css, the designer's rule), so the attribute is not
      // written either — thirteen style recalculations inside the reveal, for something invisible
      if (narrow.current?.matches) return;
      for (const el of s ? [spots.current.get(s.id)] : spots.current.values()) el?.toggleAttribute('data-label', on);
      if (s && on) spots.current.get(s.id)?.setAttribute('data-on', '');
    },
    spots(on) {
      for (const el of spots.current.values()) el.toggleAttribute('data-on', on);
      // the strip follows the room: whole when the room rests; gathered from the far wall to the near side, 70 ms apart
      const order = on ? tour.slots : [...tour.slots].sort((a, b) => b.depth_m - a.depth_m);
      order.forEach((s, i) => tile(s.id, on, on || prefersReducedMotion() ? 0 : i * 70));
    },
    /**
     * MOCK2: the counter is written into the page, not through the component's state. It changes once per product
     * while the room fills, and a state change there re-rendered the whole page — thirteen times, inside the effect
     * (that was most of the script time of the depth scan: FB1, smoothness). MOCK3: it sits in its own row under the
     * window, always in the page; it appears and goes by opacity.
     */
    count(n, final = false) {
      const el = countEl.current;
      if (!el) return;
      el.toggleAttribute('data-on', n !== null);
      if (n === null) return;
      el.toggleAttribute('data-final', final);
      const [a, mid, sep, b, tail] = [...el.children] as HTMLElement[];
      if (final) {
        a!.textContent = String(n);
        mid!.textContent = ' פריטים';
        sep!.textContent = ' · ';
        b!.textContent = `${Math.round(tour.cover * 100)}%`;
        b!.removeAttribute('dir');
        tail!.textContent = ' מהחדר';
      } else {
        a!.textContent = '';
        mid!.textContent = 'פריטים ';
        sep!.textContent = '';
        b!.textContent = `${n}/${tour.slots.length}`;
        b!.setAttribute('dir', 'ltr');
        tail!.textContent = '';
      }
    },
    dims(on) {
      if (narrow.current?.matches) return;
      for (const el of dimEls.current.values())
        if (on) el.animate([{ opacity: 0 }, { opacity: 1, offset: 0.2 }, { opacity: 1, offset: 0.8 }, { opacity: 0 }], { duration: 1300 * k() });
    },
    house(to) {
      setEye(to);
    },
  };

  // ---------- the pictures the strip and the wheel show: fetched and decoded while the visitor is at the door ----------
  const held = useRef<HTMLImageElement[]>([]);
  const decoded = (img: HTMLImageElement): Promise<void> =>
    Promise.race([
      img.decode().then(
        () => metrics.count('decode'),
        () => undefined,
      ),
      new Promise<void>((r) => setTimeout(r, 4000)),
    ]);
  /** the strip's thirteen (the default option of every slot): the door waits for them, as it does for the room */
  const stripReady = (): Promise<unknown> => Promise.all([...tiles.current.values()].map((b) => b.querySelector('img')).map((i) => (i ? decoded(i) : null)));
  /** the wheel's other cards, one at a time and only between effects, once the room rests */
  const cardsStarted = useRef(false);
  function otherCards(e: TourEngine) {
    if (cardsStarted.current) return;
    cardsStarted.current = true;
    const urls = tour.slots.flatMap((s) => s.options.slice(1).map(cardUrl));
    const next = () => {
      const url = urls.shift();
      if (!url || !engine.current) return;
      if (e.busy) return void setTimeout(next, 400);
      const img = new Image();
      img.src = url;
      held.current.push(img);
      void decoded(img).then(() => setTimeout(next, 30));
    };
    setTimeout(next, 600);
  }

  // ---------- the engine ----------
  function ensure(): Promise<TourEngine | null> {
    return (starting.current ??= import('./stage').then(async (m) => {
      const c = canvas.current;
      if (!c) return null;
      mod.current = m;
      const e = m.TourEngine.create({
        canvas: c,
        reduceMotion: prefersReducedMotion(),
        onCamera: place,
        onResize: () => (live.current.busy ? (resized.current = true) : relayout()),
      });
      if (!e) {
        setNoGl(true);
        return null;
      }
      engine.current = e;
      window.__hdTour = e;
      window.__hdTourFx = { ...m, ui };
      e.observe();
      const { skip, way } = live.current.cfg;
      e.d.doorAmt = skip ? 0 : 1;
      e.doorCu = DOOR_CU;
      await e.start();
      if (!skip) e.cam = e.atDoor();
      place();
      e.render();
      setReady(true);
      if (skip || way === 'full') {
        await e.products();
        tour.slots.forEach((s) => e.settle(s.id, true));
        e.mask();
        e.render();
      }
      if (skip) {
        setPhase('room');
        ui.spots(true);
        ui.count(tour.slots.length, true);
        e.background();
        otherCards(e);
      } else {
        // MOCK2 (FB1): the door waits until the room can be animated — every layer of it fetched, decoded, uploaded
        // and composed once, every program compiled. Until then the button says so and nothing moves: even the slow
        // push of the door starts afterwards, so the room's own decodes never land inside it. MOCK3: and the strip's
        // pictures, and the wheel's code, so nothing of them arrives inside the reveal or the first close-up.
        void Promise.all([e.whenWarm(), stripReady(), (wheelChunk ??= import('../components/VariantWheel').then((x) => x.VariantWheel))]).then(() => {
          setWarm(true);
          primeRings();
          m.doorPush(e);
          // a visitor who stays at the door: the rest of the house loads behind it, once the room itself is ready
          idleLoad.current = window.setTimeout(() => e.background(), 5000);
        });
      }
      return e;
    }));
  }
  useEffect(() => {
    setCfg(readCfg());
    measure();
    // the page's own measurement of the window: a resize or a rotation, never an animation (the window keeps its size)
    const ro = new ResizeObserver(() => measure());
    if (win.current) ro.observe(win.current);
    // a pinch is ours, not the browser's: the page neither scrolls nor zooms under two fingers, or under a zoomed picture
    const w = win.current;
    const hold = (ev: TouchEvent) => {
      if (live.current.phase === 'room' && (ev.touches.length > 1 || gest.current || (engine.current?.cam.z ?? 1) > 1.001)) ev.preventDefault();
    };
    const noGesture = (ev: Event) => ev.preventDefault();
    w?.addEventListener('touchmove', hold, { passive: false });
    w?.addEventListener('gesturestart', noGesture);
    // after the door is painted: the engine's chunk, the empty room, then the products behind it
    let idle = 0;
    const later = () => (idle = window.setTimeout(() => void ensure(), 60));
    if (document.readyState === 'complete') later();
    else addEventListener('load', later, { once: true });
    return () => {
      ro.disconnect();
      w?.removeEventListener('touchmove', hold);
      w?.removeEventListener('gesturestart', noGesture);
      removeEventListener('load', later);
      clearTimeout(idle);
      clearTimeout(hint.current);
      clearTimeout(idleLoad.current);
      clearTimeout(turn.current);
      clearTimeout(tapWait.current);
      engine.current?.destroy();
      engine.current = null;
      starting.current = null;
      delete window.__hdTour;
    };
  }, []);

  /** runs one beat: nothing else starts while it moves; a press made meanwhile is done at its end */
  async function beat(fn: (e: TourEngine, m: Stage) => Promise<void>, again?: () => void): Promise<void> {
    if (live.current.busy) {
      if (again) queued.current = again;
      return;
    }
    setBusy(true);
    clearTimeout(hint.current);
    const e = await ensure();
    try {
      if (e && mod.current) await fn(e, mod.current);
    } finally {
      // the last effect's numbers, for whoever holds the phone (the temporary panel; MOCK2 counts the interruptions)
      if (e?.stat?.frames) setStat(statLine(e.stat));
      setBusy(false);
    }
  }
  const quiet = (e: TourEngine) => e.wait(200);

  // ---------- MOCK2: the report the owner copies off his own phone ----------
  const [copied, setCopied] = useState('');
  async function copyReport() {
    const e = engine.current;
    const gl = (canvas.current?.getContext('webgl2') ?? null) as WebGL2RenderingContext | null;
    const dbg = gl?.getExtension('WEBGL_debug_renderer_info');
    const text = report(metrics, {
      when: new Date().toISOString().slice(0, 16).replace('T', ' '),
      browser: navigator.userAgent,
      screen: `${innerWidth}×${innerHeight} CSS, DPR ${devicePixelRatio}`,
      layout: `${live.current.lay}, frame ${live.current.cfg.frame}`,
      canvas: e ? `${Math.round(e.vp.w)}×${Math.round(e.vp.h)} CSS, drawing ${canvas.current?.width}×${canvas.current?.height}` : '—',
      composition: e ? `${e.gl.width} px wide` : '—',
      card: dbg ? String(gl?.getParameter(dbg.UNMASKED_RENDERER_WEBGL)) : String(gl?.getParameter(gl.RENDERER) ?? '—'),
      textures: e ? `${(e.gl.vram / 1048576).toFixed(1)} MB` : '—',
    });
    try {
      await navigator.clipboard.writeText(text);
      setCopied('הועתק');
    } catch {
      // a browser that will not copy from script: the text goes on the page, selected, to copy by hand
      const el = document.getElementById('tour-report') as HTMLTextAreaElement | null;
      if (el) {
        el.value = text;
        el.hidden = false;
        el.select();
      }
      setCopied('בחרו והעתיקו');
    }
    setTimeout(() => setCopied(''), 4000);
  }
  /** the room rests: its marks are on; the labels fold after a moment; one ring on the hero if nobody touches */
  const turn = useRef(0);
  const rested = useRef(false);
  function atRest(e: TourEngine) {
    e.background();
    otherCards(e);
    if (e.house !== WM) return;
    ui.spots(true);
    void e.wait(800).then(() => !live.current.busy && ui.label(null, false));
    clearTimeout(hint.current);
    hint.current = window.setTimeout(() => {
      const hero = tour.slots.find((s) => s.hero);
      if (hero && !live.current.busy && !live.current.open && live.current.phase === 'room') ui.ring(hero, 'burst');
    }, 6000);
    if (rested.current) return;
    rested.current = true;
    // once, after the first reveal: the folded control's arrow moves, to say there is more under it
    fold.current?.setAttribute('data-hint', '');
    // and once a visit, on a phone held upright: the quiet invitation to turn it (never a blocking screen)
    turn.current = window.setTimeout(() => {
      const L = live.current;
      if (L.lay !== 'portrait' || !narrow.current?.matches || !whole() || everZoomed.current || L.open || L.busy || L.more || L.phase !== 'room') return;
      try {
        if (sessionStorage.getItem('hd-tour-turn')) return;
        sessionStorage.setItem('hd-tour-turn', '1');
      } catch {
        // a browser without storage shows it once per load
      }
      setEye('rotate');
      turn.current = window.setTimeout(() => setEye(live.current.house), 4000);
    }, 1200);
  }

  // ---------- the folded control and its panel (FB3) ----------
  /** opens or closes the panel; resolves when it has finished moving (the engine holds its rule over it: e.ui) */
  function setMore(on: boolean, focus = true): Promise<void> {
    if (on === live.current.more) return Promise.resolve();
    live.current.more = on;
    setMoreState(on);
    const moved = engine.current?.ui(on ? 'panel-open' : 'panel-close', on ? 320 : 160) ?? Promise.resolve();
    if (on) void frame().then(() => panel.current?.querySelector<HTMLElement>('.tour-room')?.focus({ preventScroll: true }));
    else if (focus) fold.current?.focus({ preventScroll: true });
    return moved;
  }
  const toggleMore = () => {
    if (live.current.busy && !live.current.more) queued.current = () => void setMore(true);
    else void setMore(!live.current.more);
  };
  /** a choice in the panel: the panel closes first, and the action starts after 0.2 s of quiet */
  async function shut(e: TourEngine) {
    if (!live.current.more) return;
    await setMore(false);
    await quiet(e);
  }
  /** before a room or a style: back to the whole frame */
  async function wholeFrame(e: TourEngine) {
    if (e.cam.z <= 1.001) return;
    stage.current?.classList.add('moving');
    await e.moveCam('zoom-back', e.rest, ZOOM.ms);
    stage.current?.classList.remove('moving');
    setZoomed(false);
  }
  const swipe = useRef<{ x: number; y: number; t: number } | null>(null);
  function onPanelDown(ev: PointerEvent) {
    const p = panel.current;
    // a list that was scrolled is being scrolled back, not closed
    const scrolled = p && p.querySelector('details[open]') ? metrics.dom(() => p.scrollTop > 0) : false;
    swipe.current = scrolled ? null : { x: ev.clientX, y: ev.clientY, t: performance.now() };
  }
  function onPanelUp(ev: PointerEvent) {
    const s = swipe.current;
    swipe.current = null;
    if (!s || ev.type === 'pointercancel') return;
    // upright the panel leaves downward; on its side it leaves to the side it came from (the start side: the right)
    const d = live.current.lay === 'rails' ? ev.clientX - s.x : ev.clientY - s.y;
    const v = d / Math.max(1, performance.now() - s.t);
    if (d >= 48 || (d > 16 && v > 0.5)) void setMore(false);
  }

  // ---------- the beats ----------
  const goIn = () =>
    live.current.phase === 'door' &&
    beat(async (e, m) => {
      await shut(e);
      // nothing starts moving before the room is ready (the button is held until then; a keyboard press waits here)
      await e.whenWarm();
      setPhase('entering');
      await m.enter(e);
      await quiet(e);
      await m.reveal(e, ui, live.current.cfg.way === 'full' ? 'c' : live.current.cfg.fx);
      setPhase('room');
      atRest(e);
      announce(`${tour.slots.length} פריטים בסלון`);
      title.current?.focus({ preventScroll: true });
    }, goIn);
  const goOut = () =>
    live.current.phase === 'room' &&
    !live.current.open &&
    beat(async (e, m) => {
      await shut(e);
      await wholeFrame(e);
      if (e.house !== WM) await m.style(e, ui, WM, 'y2', 'b');
      setHouse(WM);
      if (live.current.cfg.way === 'empty') await m.collect(e, ui);
      else {
        ui.spots(false);
        ui.label(null, false);
        ui.count(null);
      }
      setPhase('entering');
      await m.leave(e, doorRect(e.vp.w, e.vp.h, whole()));
      setPhase('door');
      m.doorPush(e);
    }, goOut);
  const replay = (fx?: Reveal) =>
    live.current.phase === 'room' &&
    live.current.house === WM &&
    !live.current.open &&
    beat(
      async (e, m) => {
        await shut(e);
        await wholeFrame(e);
        const kind = fx ?? live.current.cfg.fx;
        if (kind !== 'c') await m.collect(e, ui);
        else ui.label(null, false);
        await quiet(e);
        await m.reveal(e, ui, kind);
        atRest(e);
      },
      () => replay(fx),
    );
  const switchTo = (to: HouseId) =>
    live.current.phase === 'room' &&
    !live.current.open &&
    to !== live.current.house &&
    beat(
      async (e, m) => {
        await shut(e);
        await wholeFrame(e);
        clearTimeout(turn.current);
        await m.style(e, ui, to, live.current.cfg.st, live.current.cfg.fx);
        setHouse(to);
        setEye(to);
        atRest(e);
        announce(`הסלון, ${to === WM ? tour.name_he : NORDIC_NAME_HE}`);
      },
      () => switchTo(to),
    );

  // ---------- zoom (FB2: the whole frame first; the visitor zooms if he wants to) ----------
  const zoomTo = (z: number, at?: { u: number; v: number }) =>
    live.current.phase === 'room' &&
    !live.current.open &&
    beat(async (e) => {
      stage.current?.classList.add('moving');
      const to = z <= 1 ? e.rest : clampCam({ cu: at?.u ?? e.cam.cu, cv: at?.v ?? e.cam.cv, z }, e.vp, tour.aspect);
      // the marks are placed again when the camera lands (onCamera), and come back there
      await e.moveCam(z <= 1 ? 'zoom-back' : 'zoom', to, ZOOM.ms);
      stage.current?.classList.remove('moving');
      setZoomed(e.cam.z > 1.001);
      sharpen(e);
    });
  /** the sharpness switch (temporary): while the picture rests zoomed, the canvas is drawn at the screen's own pixels */
  const sharpen = (e: TourEngine) => e.setDprCap(live.current.cfg.sharp && e.cam.z > 1.001 ? 3 : 2);

  // ---------- the close-up and the wheel ----------
  const opener = useRef<HTMLElement | null>(null);
  const closing = useRef(false);
  /** the camera of a product's close-up: the product fills about 60% of what the layout leaves free of the window */
  function closeCam(e: TourEngine, s: TourSlot): Cam {
    const b = optionOf(s, e.selection).box;
    const g = [(b[1] - b[0]) / 3, (b[3] - b[2]) / 3];
    return e.camFor(
      [Math.max(0, b[0] - g[0]!), Math.min(1, b[1] + g[0]!), Math.max(0, b[2] - g[1]!), Math.min(1, b[3] + g[1]!)],
      closeReserve(live.current.lay, e.vp.h, !whole()),
    );
  }
  const picker = () => stage.current?.querySelector<HTMLElement>('.picker') ?? null;
  const openSlot = (s: TourSlot, from?: HTMLElement | null) =>
    live.current.phase === 'room' &&
    live.current.house === WM &&
    !live.current.open &&
    beat(async (e) => {
      opener.current = from ?? (document.activeElement as HTMLElement | null);
      const W = await (wheelChunk ??= import('../components/VariantWheel').then((x) => x.VariantWheel));
      clearTimeout(turn.current);
      if (live.current.lay !== 'desk') setEye(live.current.house);
      ui.label(null, false);
      stage.current?.classList.add('zoomed');
      // frame 0, before anything moves: the wheel enters the page unseen, and this is where the page is laid out.
      // The camera starts on the frame after it, so no layout lands inside the move (the designer's order).
      setWheel(() => W);
      setOpen({ slot: s, before: e.selection[s.id] ?? 1 });
      await frame();
      await frame();
      let rise: Promise<void> | null = null;
      const show = () => {
        picker()?.setAttribute('data-in', '');
        return e.ui('wheel-in', 320);
      };
      await e.moveCam('zoom-in', closeCam(e, s), 1000, (ease, t) => {
        e.d.vig = 0.1 * ease;
        e.d.vigBox = s.rect;
        // the wheel rises 0.15 s before the camera lands
        if (t >= 0.85 && !rise) rise = show();
      });
      await (rise ?? show());
      sharpen(e);
    });
  /** the wheel stopped on an option: the product in the room changes; a newer stop overtakes one still waiting */
  const wanted = useRef<number | null>(null);
  function preview(s: TourSlot, pos: number) {
    const moving = wanted.current !== null;
    wanted.current = pos;
    if (moving) return;
    void (async () => {
      const e = engine.current;
      const m = mod.current;
      while (e && m && wanted.current !== null && wanted.current !== e.selection[s.id]) {
        const to = wanted.current;
        await m.swap(e, ui, s, to, to > e.selection[s.id]! ? 1 : -1, live.current.cfg.sw);
        setSel({ ...e.selection });
      }
      wanted.current = null;
    })();
  }
  function close(chosen: boolean): void {
    const o = live.current.open;
    if (!o || closing.current) return;
    void beat(
      async (e) => {
        closing.current = true;
        if (!chosen) preview(o.slot, o.before);
        while (wanted.current !== null) await new Promise((r) => setTimeout(r, 30));
        // the wheel leaves (160 ms) as the camera starts back; always to the whole frame
        picker()?.removeAttribute('data-in');
        e.setDprCap(2);
        await e.moveCam('zoom-out', e.rest, live.current.lay === 'desk' || !whole() ? 1000 : ZOOM.ms, (ease) => (e.d.vig = 0.1 * (1 - ease)));
        stage.current?.classList.remove('zoomed');
        setOpen(null);
        setZoomed(false);
        closing.current = false;
        // the strip, the counter and the folded control come back in their own cells
        void e.ui('closeup-out', 320);
        atRest(e);
        if (chosen) announce(`${o.slot.name_he}: ${nameHe(o.slot, optionOf(o.slot, e.selection))} מוצג בחדר`);
        const back = phoneRules() && live.current.cfg.pick === 'list' ? tiles.current.get(o.slot.id) : spots.current.get(o.slot.id);
        void frame().then(() => (back ?? opener.current)?.focus({ preventScroll: true }));
      },
      () => close(chosen),
    );
  }

  // ---------- the window under a finger: a tap chooses, two fingers zoom, one drags a zoomed picture ----------
  type Ptr = { x: number; y: number; moved: number };
  const ptrs = useRef(new Map<number, Ptr>());
  const origin = useRef({ x: 0, y: 0 });
  type Gesture = { kind: 'pinch'; d0: number; z0: number; u: number; v: number } | { kind: 'drag'; u: number; v: number } | { kind: 'pan' };
  const gest = useRef<Gesture | null>(null);
  const tapWait = useRef(0);
  const two = () => {
    const [a, b] = [...ptrs.current.values()];
    return { x: (a!.x + b!.x) / 2, y: (a!.y + b!.y) / 2, d: Math.max(24, Math.hypot(a!.x - b!.x, a!.y - b!.y)) };
  };
  /** the rubber: the camera never leaves its limits; what is asked beyond them moves the picture itself, and springs back */
  function stretch(transform: string, ox = 0, oy = 0) {
    const c = canvas.current;
    if (!c) return;
    win.current?.classList.toggle('spring', !transform);
    if (transform) c.style.transformOrigin = `${ox.toFixed(0)}px ${oy.toFixed(0)}px`;
    c.style.transform = transform;
  }
  function begin(e: TourEngine, g: Gesture, label: string) {
    gest.current = g;
    stage.current?.classList.add('moving');
    e.setDprCap(2);
    e.hold(label);
  }
  function end(e: TourEngine, label: string) {
    gest.current = null;
    e.stop(label);
    stretch('');
    // a pinch that ends just over the whole frame goes back to it
    if (e.cam.z > 1.0001 && e.cam.z < ZOOM.snap) return void zoomTo(1);
    if (e.cam.z <= 1.0001) e.cam = { ...e.rest };
    place();
    e.render();
    stage.current?.classList.remove('moving');
    setZoomed(e.cam.z > 1.001);
    sharpen(e);
  }
  function onPointerDown(ev: PointerEvent) {
    clearTimeout(hint.current);
    const L = live.current;
    const e = engine.current;
    if (!e || L.phase !== 'room' || L.busy || (ev.target as Element).closest('button, a')) return;
    // the window's place on the glass now (the page may have scrolled since it was measured): read once, at the touch
    if (!ptrs.current.size) origin.current = metrics.dom(() => ({ x: box.current.x - scrollX, y: box.current.y - scrollY }));
    ptrs.current.set(ev.pointerId, { x: ev.clientX - origin.current.x, y: ev.clientY - origin.current.y, moved: 0 });
    if (ptrs.current.size !== 2 || L.open || !whole()) return;
    // two fingers: the point of the room between them stays between them
    if (gest.current?.kind === 'drag') e.stop('drag');
    const f = two();
    begin(e, { kind: 'pinch', d0: f.d, z0: e.cam.z, ...screenToFrame(f.x, f.y, e.cam, e.vp, tour.aspect) }, 'pinch');
    for (const id of ptrs.current.keys()) win.current?.setPointerCapture(id);
  }
  function onPointerMove(ev: PointerEvent) {
    const p = ptrs.current.get(ev.pointerId);
    const e = engine.current;
    if (!p || !e) return;
    const x = ev.clientX - origin.current.x;
    const y = ev.clientY - origin.current.y;
    const dx = x - p.x;
    const dy = y - p.y;
    p.x = x;
    p.y = y;
    p.moved += Math.abs(dx) + Math.abs(dy);
    const { fw, fh } = coverSize(e.vp, tour.aspect);
    let g = gest.current;
    if (g?.kind === 'pinch') {
      if (ptrs.current.size < 2) return;
      const f = two();
      const { z, stretch: s } = pinchZoom((g.z0 * f.d) / g.d0);
      e.cam = clampCam({ z, cu: g.u - (f.x - e.vp.w / 2) / (fw * z), cv: g.v - (f.y - e.vp.h / 2) / (fh * z) }, e.vp, tour.aspect);
      stretch(s === 1 ? 'none' : `scale(${s.toFixed(4)})`, f.x, f.y);
      return;
    }
    if (live.current.open || live.current.busy) return;
    if (!g && p.moved > 6) {
      if (e.cam.z > 1.001 && whole()) begin(e, (g = { kind: 'drag', u: e.cam.cu, v: e.cam.cv }), 'drag');
      else if (!whole()) g = gest.current = { kind: 'pan' };
      if (g) win.current?.setPointerCapture(ev.pointerId);
    }
    if (g?.kind === 'drag') {
      // one finger moves a zoomed picture, as far as the frame's edge; past it, 24 px of rubber at the most
      g.u -= dx / (fw * e.cam.z);
      g.v -= dy / (fh * e.cam.z);
      e.cam = clampCam({ cu: g.u, cv: g.v, z: e.cam.z }, e.vp, tour.aspect);
      const ox = rubber((e.cam.cu - g.u) * fw * e.cam.z);
      const oy = rubber((e.cam.cv - g.v) * fh * e.cam.z);
      stretch(ox || oy ? `translate(${ox.toFixed(1)}px, ${oy.toFixed(1)}px)` : 'none');
    } else if (g?.kind === 'pan') e.panBy(dx);
  }
  function onPointerUp(ev: PointerEvent) {
    const p = ptrs.current.get(ev.pointerId);
    ptrs.current.delete(ev.pointerId);
    const e = engine.current;
    const g = gest.current;
    if (!p || !e) return;
    if (g?.kind === 'pinch') {
      if (ptrs.current.size >= 2) return;
      // the finger that stays is not a tap and not a drag
      for (const q of ptrs.current.values()) q.moved = 1e6;
      return end(e, 'pinch');
    }
    if (g?.kind === 'drag') return end(e, 'drag');
    if (g?.kind === 'pan') return void (gest.current = null);
    if (ev.type === 'pointercancel' || p.moved > 6 || live.current.busy) return;
    // "גם הקשה כפולה" (a switch): a second tap inside 250 ms zooms; a single one waits that long, and says so with a ring
    if (live.current.cfg.zoom === 'double' && phoneRules() && !live.current.open) {
      const at = screenToFrame(p.x, p.y, e.cam, e.vp, tour.aspect);
      if (tapWait.current) {
        clearTimeout(tapWait.current);
        tapWait.current = 0;
        return void zoomTo(e.cam.z > 1.001 ? 1 : ZOOM.step, at);
      }
      const r = tapRule(p.x, p.y, marks(e));
      if (r && 'open' in r) ui.ring(e.slot(r.open), 'tile');
      tapWait.current = window.setTimeout(() => {
        tapWait.current = 0;
        tap(p.x, p.y);
      }, 250);
      return;
    }
    tap(p.x, p.y);
  }
  const marks = (e: TourEngine): Mark[] => tour.slots.flatMap((s) => (e.visible.has(s.id) ? (markOf(s, e) ?? []) : []));
  function tap(x: number, y: number) {
    const e = engine.current;
    const L = live.current;
    if (!e || L.busy || L.phase !== 'room') return;
    const at = screenToFrame(x, y, e.cam, e.vp, tour.aspect);
    if (L.open) {
      // in the close-up: a tap in the window outside the product closes it (the phone; a wide screen has the wheel there)
      const b = optionOf(L.open.slot, e.selection).box;
      if (phoneRules() && (at.u < b[0] || at.u > b[1] || at.v < b[2] || at.v > b[3])) close(false);
      return;
    }
    if (L.house !== WM) return;
    if (!phoneRules()) {
      // a wide screen, and "מילוי וגרירה": the product under the pointer, by the mask, as before
      const hit = e.slotAt(at.u, at.v);
      if (hit) void openSlot(hit, spots.current.get(hit.id));
      return;
    }
    // "נקודות בלבד" (a switch): the first tap always zooms ×2 to the place, the second opens the product
    if (L.cfg.pick === 'dots' && e.cam.z < ZOOM.snap) return void zoomTo(ZOOM.step, at);
    const r = tapRule(x, y, marks(e));
    if (!r) return;
    const from = (id: string) => (L.cfg.pick === 'list' ? tiles.current.get(id) : spots.current.get(id));
    if ('open' in r) return void openSlot(e.slot(r.open), from(r.open));
    // two marks too close to tell apart: ×2 to the point, where they stand apart (and once more, up to the limit)
    const z = e.cam.z < ZOOM.step - 0.01 ? ZOOM.step : e.cam.z < ZOOM.max - 0.01 ? ZOOM.max : 0;
    if (z) void zoomTo(z, at);
    else void openSlot(e.slot(r.nearest), from(r.nearest));
  }

  const inRoom = phase === 'room';
  const wm = house === WM;
  const phone = lay !== 'desk' && cfg.frame === 'whole';
  /** the strip is the way to choose (and the screen reader's list); the marks are then decoration */
  const strip = phone && cfg.pick === 'list';
  const listOn = strip && inRoom && wm && !open;
  // MOCK2: the first paint is the width the engine will compose at on this screen (data.ts widthFor: a phone takes
  // `lo`), so the picture the browser already holds is the one the room is built from, not a second download
  const WIDE = '(min-width: 901px)';
  const poster = (w: number, ext: 'avif' | 'webp') => mediaUrl(tour.base.src, w, ext);
  const off = { inert: true, 'aria-hidden': 'true' } as const;
  const radios = <T extends string>(name: string, legend: string, value: T, options: [T, string][], set: (v: T) => void) => (
    <fieldset>
      <legend>{legend}</legend>
      {options.map(([v, label]) => (
        <label key={v}>
          <input type="radio" name={`tour-${name}`} value={v} checked={value === v} onChange={() => set(v)} />
          {label}
        </label>
      ))}
    </fieldset>
  );
  const rooms: { id?: string; name: string; at: 'entry' | 'living' | 'rest'; here?: boolean; go?: () => void }[] = [
    { id: 'tour-out', name: 'כניסה', at: 'entry', here: phase === 'door', go: () => void goOut() },
    { id: 'tour-living', name: 'סלון', at: 'living', here: inRoom, go: () => void goIn() },
    { name: 'פינת אוכל', at: 'rest' },
    { name: 'חדר שינה', at: 'rest' },
  ];
  // "קנה את המראה": the style's own magazine page on the site; the Artifact preview has no such page, and shows the
  // list of the room's products under the tour instead
  const lookHref = __ARTIFACT__ ? null : `/story/${tour.room}/${house}/`;
  return (
    <>
      <section
        class={`stage tour${noGl ? ' tour-nogl' : ''}`}
        ref={stage}
        data-phase={phase}
        data-house={house}
        data-ready={ready ? '' : undefined}
        data-frame={cfg.frame}
        data-pick={cfg.pick}
        data-bg={cfg.bg}
        data-close={open ? '' : undefined}
        data-more={more ? '' : undefined}
        data-zoomed={zoomed ? '' : undefined}
        style={{ '--cu': String(phase === 'door' ? (prefersReducedMotion() ? tour.mobile_center_u : DOOR_CU) : tour.mobile_center_u) }}
        aria-labelledby="tour-title"
        onKeyDown={(ev) => {
          if (ev.key !== 'Escape' || !live.current.more) return;
          ev.preventDefault();
          void setMore(false);
        }}
      >
        <div class="tour-g">
          {/* the band over the window: the house and the room. Both pairs are in the page from the start, in one cell */}
          <div class="tour-top" ref={top} data-eye={eye}>
            <div class="tour-t t-door" {...(phase === 'door' ? {} : off)}>
              <p class="eyebrow">סיור</p>
              {phase === 'door' ? (
                <h1 id="tour-title" tabIndex={-1}>
                  {tour.name_he}
                </h1>
              ) : (
                <p class="h">{tour.name_he}</p>
              )}
            </div>
            <div class="tour-t t-room" {...(phase !== 'door' && !(open && phone) ? {} : off)}>
              <p class="eyebrow tour-eyes">
                <span data-k={WM} aria-hidden={eye === WM ? undefined : 'true'}>
                  {tour.name_he}
                </span>
                <span data-k={NORDIC} aria-hidden={eye === NORDIC ? undefined : 'true'}>
                  {NORDIC_NAME_HE}
                  <span class="stage-status">תמונות זמניות</span>
                </span>
                <span data-k="rotate" aria-hidden="true">
                  ↻ לחדר גדול יותר, סובבו את הטלפון
                </span>
              </p>
              {phase === 'door' ? (
                <p class="h">סלון</p>
              ) : (
                <h1 id="tour-title" tabIndex={-1} ref={title}>
                  סלון
                  <span class="sr-only"> · {wm ? tour.name_he : NORDIC_NAME_HE}</span>
                </h1>
              )}
            </div>
          </div>

          {/* the window: one 16:9 frame in every phase. On it, the products' marks and nothing else. */}
          <div class="tour-win" ref={win} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}>
            {/* the first paint, before the engine: the same empty room behind the same portal (CSS), never a dark stage */}
            <picture>
              {__ARTIFACT__ ? null : <source media={WIDE} srcset={poster(tour.widths.hi, 'avif')} type="image/avif" />}
              {__ARTIFACT__ ? null : <source srcset={poster(tour.widths.lo, 'avif')} type="image/avif" />}
              {__ARTIFACT__ ? null : <source media={WIDE} srcset={poster(tour.widths.hi, 'webp')} type="image/webp" />}
              <img
                class="poster tour-poster"
                src={poster(tour.widths.lo, 'webp')}
                alt=""
                fetchpriority="high"
                style={{ backgroundImage: `url("${tour.base.placeholder}")` }}
              />
            </picture>
            <span class="tour-portal-line" aria-hidden="true" />
            <canvas
              ref={canvas}
              class="room-canvas"
              // eslint-disable-next-line jsx-a11y/no-interactive-element-to-noninteractive-role
              role="img"
              aria-label={
                phase === 'door'
                  ? 'דלת הכניסה: פתח מעוגל בקיר טיח, ודרכו הסלון של הבית המודרני החם, עוד בלי המוצרים.'
                  : wm
                    ? `הסלון בבית המודרני החם, עם ${tour.slots.length} פריטים. הרשימה שמתחת לחדר מפרטת אותם.`
                    : 'הסלון בבית הנורדי, בתמונות זמניות.'
              }
            />
            <div class="tour-rings" aria-hidden="true">
              {tour.slots.flatMap((s) =>
                s.anchors.map((_, i) => (
                  <span
                    key={`${s.id}:${i}`}
                    class="tour-ring"
                    ref={(el) => {
                      if (el) rings.current.set(`${s.id}:${i}`, el);
                    }}
                  >
                    <i />
                  </span>
                )),
              )}
              {tour.slots
                .filter((s) => s.options.some((o) => o.dims_he))
                .map((s) => (
                  <span
                    key={s.id}
                    class="tour-dim"
                    ref={(el) => {
                      if (el) dimEls.current.set(s.id, el);
                    }}
                  >
                    <b>{optionOf(s, sel).dims_he}</b>
                  </span>
                ))}
            </div>
            {/* the marks: buttons on a wide screen (and when the strip is switched off); decoration beside the strip */}
            <div class="hotspots tour-spots" role="group" aria-label="פריטים בחדר" hidden={phase === 'door' || !wm} {...(strip ? off : {})}>
              {tour.slots.map((s) => {
                const o = optionOf(s, sel);
                const price = priceHe(o);
                return (
                  <button
                    key={s.id}
                    type="button"
                    class="tour-spot"
                    data-slot={s.id}
                    ref={(el) => {
                      if (el) spots.current.set(s.id, el);
                    }}
                    style={{ left: 0, top: 0 }}
                    tabIndex={strip ? -1 : undefined}
                    aria-label={`${s.name_he}: ${nameHe(s, o)}${price ? `, ${price}` : ''}. ${s.options.length > 1 ? `פתיחת ${s.options.length} גרסאות` : 'תקריב'}`}
                    disabled={busy || !!open}
                    onClick={(ev) => void openSlot(s, ev.currentTarget)}
                  >
                    <span class="mark" aria-hidden="true" />
                    <span class="tag" aria-hidden="true">
                      {nameHe(s, o)}
                      {price ? <span class="num"> · {price}</span> : null}
                    </span>
                  </button>
                );
              })}
            </div>
            {noGl ? (
              <p class="glass tour-nogl-note" role="status">
                הסיור צריך דפדפן עם WebGL2. <a href="/rooms/living-room/?style=warm-modern">לסלון בכלי העיצוב</a>
              </p>
            ) : null}
          </div>

          {/* the band under the window: the counter and the zoom, the strip of products (the door's button in its
              place at the door), and the folded control. Every cell keeps its size; what is in it changes by opacity. */}
          <div class="tour-bot">
            <div class="tour-row">
              {/* MOCK2: always in the page, filled by ui.count through the DOM (no render inside an effect) */}
              <p class="tour-count" aria-hidden="true" ref={countEl}>
                <span class="num" />
                <span />
                <span class="x" />
                <span class="num x" />
                <span class="x" />
              </p>
              <button
                type="button"
                id="tour-zoom"
                class="tour-zoom"
                aria-label={zoomed ? 'כל החדר' : 'הגדלה'}
                title={zoomed ? 'כל החדר' : 'הגדלה'}
                disabled={!inRoom || !!open}
                onClick={() => void zoomTo(live.current.zoomed ? 1 : ZOOM.step)}
              >
                <IconZoom out={zoomed} />
              </button>
            </div>
            <div class="tour-cell">
              {/* the role is said outright: a list without markers loses it in Safari's screen reader */}
              {/* eslint-disable-next-line jsx-a11y/no-redundant-roles */}
              <ul class="tour-strip" role="list" aria-label="פריטים בחדר" {...(listOn ? {} : off)}>
                {tour.slots.map((s) => {
                  const o = optionOf(s, sel);
                  const price = priceHe(o);
                  return (
                    <li key={s.id}>
                      <button
                        type="button"
                        class="tour-tile"
                        data-slot={s.id}
                        ref={(el) => {
                          if (el) tiles.current.set(s.id, el);
                        }}
                        aria-label={`${s.name_he}: ${nameHe(s, o)}${price ? `, ${price}` : ''}. ${s.options.length > 1 ? `פתיחת ${s.options.length} גרסאות` : 'תקריב'}`}
                        disabled={busy || !!open}
                        // the touch itself answers in the room: one ring on the product's mark ties the list to the picture
                        onPointerDown={() => !live.current.busy && ui.ring(s, 'tile')}
                        onClick={(ev) => void openSlot(s, ev.currentTarget)}
                      >
                        <span class="pic">
                          <img src={cardUrl(o)} alt="" width={72} height={72} draggable={false} />
                        </span>
                        <span class="nm">{nameHe(s, o)}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
              <p class="tour-none" {...(inRoom && !wm ? {} : off)}>
                החדר הזה עוד בלי מוצרים
              </p>
              {/* the door's one button (temporary door), in the strip's place */}
              <div class="tour-door-act" {...(phase === 'door' ? {} : off)}>
                <button
                  type="button"
                  class="btn btn-primary"
                  id="tour-enter"
                  onClick={() => void goIn()}
                  aria-busy={busy || (ready && !warm) ? 'true' : undefined}
                >
                  היכנסו לסלון
                </button>
                {/* MOCK2: the room is made ready before anything moves; the quiet line says so while it is (FB1) */}
                <span class="tour-temp" role="status">
                  {ready && !warm ? 'מכינים את החדר…' : 'הדלת זמנית'}
                </span>
              </div>
            </div>
            <button
              type="button"
              id="tour-fold"
              class="tour-fold"
              ref={fold}
              aria-label="המשך הסיור"
              aria-expanded={more ? 'true' : 'false'}
              aria-controls="tour-more"
              {...(open ? off : {})}
              onClick={toggleMore}
            >
              <PlanIcon at={phase === 'door' ? 'entry' : 'living'} />
              <span class="long">המשך הסיור</span>
              <span class="short">הסיור</span>
              <svg
                class="arr"
                viewBox="0 0 24 24"
                width="18"
                height="18"
                fill="none"
                stroke="currentColor"
                stroke-width="1.7"
                stroke-linecap="round"
                aria-hidden="true"
              >
                <path d="M6 14l6-6 6 6" />
              </svg>
            </button>
          </div>

          {/* a tap outside the open panel closes it, and is swallowed: it never reaches a product */}
          <div class="tour-veil" aria-hidden="true" onClick={() => void setMore(false)} />
          <div
            id="tour-more"
            class="tour-more"
            role="region"
            aria-label="המשך הסיור"
            ref={panel}
            {...(more ? {} : { inert: true })}
            onPointerDown={onPanelDown}
            onPointerUp={onPanelUp}
            onPointerCancel={onPanelUp}
          >
            <div class="tour-more-head">
              <span class="grip" aria-hidden="true" />
              <button type="button" class="tour-more-x" onClick={() => void setMore(false)}>
                סגירה
              </button>
            </div>
            {/* a button per room (TOUR1): the door and the living room are here; a room that is not built yet says so */}
            <nav class="tour-rooms" aria-label="חדרים">
              <h2>חדרים</h2>
              <div>
                {rooms.map((r) => (
                  <button
                    key={r.name}
                    type="button"
                    id={r.id}
                    class={r.go ? 'tour-room' : undefined}
                    aria-current={r.here ? 'true' : undefined}
                    aria-disabled={r.go ? undefined : 'true'}
                    onClick={r.go}
                  >
                    {r.at === 'entry' ? <IconDoor /> : <PlanIcon at={r.at} />}
                    <span>{r.name}</span>
                    {r.go ? null : <small>בקרוב</small>}
                  </button>
                ))}
              </div>
            </nav>
            <div class="tour-style" role="group" aria-label="סגנון">
              <h2>סגנון</h2>
              <div class="segmented">
                {(
                  [
                    [NORDIC, NORDIC_NAME_HE],
                    [WM, tour.name_he],
                  ] as const
                ).map(([id, name]) => (
                  <button key={id} type="button" data-house={id} aria-pressed={house === id} disabled={!inRoom} onClick={() => void switchTo(id)}>
                    {name}
                  </button>
                ))}
              </div>
            </div>
            <p class="tour-links">
              {lookHref ? (
                <a class="btn btn-ghost" id="tour-look" href={lookHref}>
                  קנה את המראה
                </a>
              ) : (
                <a
                  class="btn btn-ghost"
                  id="tour-look"
                  href="#tour-items"
                  onClick={(ev) => {
                    ev.preventDefault();
                    void setMore(false, false);
                    const h = document.getElementById('tour-items');
                    h?.scrollIntoView({ block: 'start', behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
                    h?.focus({ preventScroll: true });
                  }}
                >
                  קנה את המראה
                </a>
              )}
              <a class="btn btn-ghost tour-home" href="/">
                לדף הבית
              </a>
            </p>

            {/* the mock-up's own switches (temporary): the owner chooses between the concepts while they move */}
            <details class="tour-panel">
              <summary>בקרה זמנית</summary>
              {radios(
                'fx',
                'חשיפה',
                cfg.fx,
                [
                  ['a', 'פרץ'],
                  ['b', 'סריקת עומק'],
                  ['c', 'הדגשה'],
                ],
                (fx) => {
                  setCfg({ fx });
                  void replay(fx);
                },
              )}
              {radios(
                'sw',
                'החלפה בגלגל',
                cfg.sw,
                [
                  ['s1', 'מגב סריקה'],
                  ['s2', 'מהמתאר'],
                  ['s3', 'הרמה והנחה'],
                ],
                (sw) => setCfg({ sw }),
              )}
              {radios(
                'st',
                'מעבר סגנון',
                cfg.st,
                [
                  ['y1', 'פירוק והלבשה'],
                  ['y2', 'גל חומר'],
                ],
                (st) => setCfg({ st }),
              )}
              {radios(
                'way',
                'בדרך לחדר',
                cfg.way,
                [
                  ['empty', 'בית ריק'],
                  ['full', 'בית מלא'],
                ],
                (way) => setCfg({ way }),
              )}
              {/* MOCK3: the designer's switches, so the owner can compare on his own phone */}
              {radios(
                'frame',
                'פריים בטלפון',
                cfg.frame,
                [
                  ['whole', 'כל הפריים'],
                  ['fill', 'מילוי וגרירה'],
                ],
                (v) => {
                  if (live.current.open || live.current.busy) return;
                  setCfg({ frame: v });
                },
              )}
              {radios(
                'pick',
                'בחירת מוצר',
                cfg.pick,
                [
                  ['list', 'רשימה ונקודות'],
                  ['dots', 'נקודות בלבד'],
                ],
                (v) => setCfg({ pick: v }),
              )}
              {radios(
                'zoom',
                'זום',
                cfg.zoom,
                [
                  ['pinch', 'צביטה וכפתור'],
                  ['double', 'גם הקשה כפולה'],
                ],
                (v) => setCfg({ zoom: v }),
              )}
              {radios(
                'bg',
                'רקע',
                cfg.bg,
                [
                  ['paper', 'נייר'],
                  ['dark', 'כהה'],
                ],
                (v) => setCfg({ bg: v }),
              )}
              <label class="tour-check">
                <input
                  type="checkbox"
                  id="tour-sharp"
                  checked={cfg.sharp}
                  onChange={(ev) => {
                    setCfg({ sharp: ev.currentTarget.checked });
                    const e = engine.current;
                    if (e && !live.current.busy) sharpen(e);
                  }}
                />
                חדות בזום
              </label>
              <button type="button" class="btn btn-ghost" id="tour-replay" disabled={!inRoom || !wm || !!open} onClick={() => void replay()}>
                הצגה מחדש
              </button>
              {/* MOCK2: one tap copies the device, the browser, the screen, the card and the table of every effect that
                  ran, as plain text the owner pastes into the chat. That is how the frame rate on a real phone is read. */}
              <button type="button" class="btn btn-ghost" id="tour-copy" onClick={() => void copyReport()}>
                {copied || 'העתקת דוח'}
              </button>
              <p class="specs" id="tour-stat" dir="ltr">
                {stat}
              </p>
              <textarea id="tour-report" class="tour-report" dir="ltr" readOnly hidden aria-label="דוח הפריימים" />
            </details>
          </div>

          {open && Wheel ? (
            <Wheel
              house={wheelHouse(open.slot)}
              slot={wheelSlot(open.slot)}
              roomId={tour.room}
              initial={sel[open.slot.id] ?? 1}
              onPreview={(pos) => preview(open.slot, pos)}
              onChoose={() => close(true)}
              onCancel={() => close(false)}
              arc={wheelArc(lay, winSize, winSize.vh, cfg.frame === 'fill')}
              inline
              chooseLabel={phone ? 'בחירה' : undefined}
              closeLabel="סגירת התקריב"
            />
          ) : null}
        </div>
      </section>
      <section class="wrap page tour-list" aria-labelledby="tour-items">
        <div class="room-intro">
          <h2 id="tour-items" tabIndex={-1}>
            מה יש בחדר
          </h2>
        </div>
        <ul class="slot-list">
          {tour.slots.map((s) => {
            const o = optionOf(s, sel);
            return (
              <li key={s.id} class="card slot-item">
                <img class="thumb" src={cardUrl(o)} alt="" loading="lazy" width={64} height={64} />
                <div class="meta">
                  <strong>{s.name_he}</strong>
                  <span class="small">{o.name_he ?? <span class="muted">{NOT_FOR_SALE_HE}</span>}</span>
                  <span class="row">
                    {o.price_agorot && o.available ? (
                      <Price agorot={o.price_agorot} provisional={o.price_provisional} />
                    ) : o.product_id ? (
                      <span class="small muted">{OUT_HE}</span>
                    ) : null}
                  </span>
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </>
  );
}
let wheelChunk: Promise<typeof WheelComponent> | null = null;
