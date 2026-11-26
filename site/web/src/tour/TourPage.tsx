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
import { prefersReducedMotion, timeScale } from '../motion';
import { announce } from '../state/ui';
import { NOT_FOR_SALE_HE } from '../set-copy';
import { IconDoor } from '../components/Icons';
import { Price } from '../components/Media';
import type { VariantWheel as WheelComponent } from '../components/VariantWheel';
import { Waitlist } from '../components/Waitlist';
import { DIM, REVEAL_MS } from '../components/ring-wheel';
import { wheelCard } from './pictures';
import {
  FRAMES,
  GROUP_HE,
  GROUP_IDS,
  NORDIC,
  NORDIC_NAME_HE,
  ROOMS,
  ROOM_HE,
  ROOM_IDS,
  WM,
  cardUrl,
  cardFileUrl,
  groupOf,
  roomCount,
  roomHeld,
  saleLine,
  setRoom,
  tour,
  type GroupId,
  type HouseId,
  type RoomId,
  type TourCard,
  type TourOption,
  type TourSlot,
} from './data';
import { arrival, camAt, doorUrl, frameAt, hcUrl, labelOpacity, labelPose, layoutLabels, stillUrl, walkFor, walkUrl } from './arrival';
import { GESTURE, Gesture, WALK, WalkPlay } from './walk';
import type { TourEngine } from './engine';
import { metrics, report, statLine } from './metrics';
import { coverMap } from './push';
import type { Reveal, Style, Swap, Ui } from './fx';
import { MQ, ZOOM, closeReserve, doorRect, overArc, padded, pinchZoom, rubber, tapRule, wheelArc, type Layout, type Mark } from './layout';
import { design as DESIGN, type Design } from '../design/design';
import { BandChrome, PlanBig, WinChrome, two as dz2, type ChromeData } from '../design/Chrome';

type Stage = typeof import('./stage');
declare global {
  interface Window {
    __hdTour?: TourEngine;
    /** the page's state for the tests and the evidence: where the visitor is, and whether anything is moving */
    __hdTourState?: {
      phase: Phase;
      busy: boolean;
      house: HouseId;
      open: string | null;
      zoomed: boolean;
      more: boolean;
      lay: Layout;
      room: RoomId;
      walk: number;
      /** MOCK8: the walk rests between two pushes; how many pushes it took */
      walkRest?: boolean;
      walkPushes?: number;
    };
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
  /** MOCK4: with ?skip=1, the room the tour starts in (the tests and the evidence) */
  room: RoomId;
  /** MOCK6: ?fixture=wheel10 opens the fixture of the wheel of many options over the room at rest (never in the
   *  Artifact; numbered swatches said to be a demo, no product and no art: tour/fixture-wheel.ts) */
  fixture: 'wheel10' | null;
};
const DEFAULTS: Cfg = {
  fx: 'b',
  sw: 's1',
  st: 'y1',
  way: 'empty',
  skip: false,
  frame: 'whole',
  pick: 'list',
  zoom: 'pinch',
  bg: 'paper',
  sharp: false,
  room: 'living-room',
  fixture: null,
};
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
    room: pick(q.get('room'), ROOM_IDS, DEFAULTS.room),
    fixture: !__ARTIFACT__ && q.get('fixture') === 'wheel10' ? 'wheel10' : null,
  };
}

export { doorRect };

/** where the camera looks from the door on a narrow screen: the window and its light (the room's rest is on the sofa) */
export const DOOR_CU = 0.2;

// MOCK8: a choice made in another room's slot of the same name (the living room's cushion set 2, then the bedroom's
// cushions of one option) is not this slot's: its first option until the page's selection is the room's own
const optionOf = (s: TourSlot, sel: Record<string, number>): TourOption => s.options[(sel[s.id] ?? 1) - 1] ?? s.options[0]!;
/** MOCK4: the products of the room the visitor is in (furniture that is not sold has no mark, no tile, no line) */
const items = (): TourSlot[] => tour.slots.filter((s) => !s.fixed);
/** a mark's place: a point in the window, kept 6 px inside its edges (the dot is drawn whole); `on`: in the window */
const inWin = (p: { x: number; y: number }, vp: { w: number; h: number }) => ({
  on: p.x > 0 && p.x < vp.w && p.y > 0 && p.y < vp.h,
  x: Math.min(vp.w - 6, Math.max(6, p.x)),
  y: Math.min(vp.h - 6, Math.max(6, p.y)),
});
/**
 * MOCK4: the move between two rooms was a plain dissolve of this long (rule ו.6: never a zoom-in). MOCK7: it stays for
 * reduced motion and for the way back to the door; between rooms the camera walks (PUSH_MS).
 */
const ROOM_FADE_MS = 900;
/**
 * MOCK7 (briefs/site-mock7-tour-transitions-2026-11-26.md): the walk between two rooms, in code (2.5D, tour/gl.ts
 * PUSH), until the real camera clips: 1.25 s between rooms, 0.95 s (and a shorter walk) between two frames of a room,
 * 1.3 s from the hall into the living room. The brief's 0.8–1.4 s; always forward (FB8).
 */
export const PUSH_MS = { room: 1250, frame: 950, arrive: 1300 } as const;
/** how far a walk goes: between two rooms, and between two frames of one room */
const PUSH_AMP = { room: 1, frame: 0.55 } as const;
/**
 * MOCK5, TEMPORARY: the move between two frames of one room (MB0 / MB1, B2 / B1, D1 / D2) is a short plain dissolve
 * (rule ו.6: never a zoom-in), like the move between rooms, until the in-room moves have clips of their own.
 */
const FRAME_FADE_MS = 600;
/** a card: its own file, or (MOCK4) its place on its room's sheet of cards, as an SVG that shows only that place.
 *  MOCK6: the place is clipped (an inner svg is its own viewport): a card much taller or wider than the square it is
 *  shown in (the kids' pendant on its cord) no longer shows its neighbours on the sheet beside it */
function CardPic({ o, cls, size, card }: { o: TourOption; cls?: string; size?: number; card?: TourCard }) {
  const c = card ?? o.card;
  const url = card ? cardFileUrl(card) : cardUrl(o);
  if (c.sprite && c.sheet) {
    const [x, y, w, h] = c.sprite;
    return (
      <svg class={`sprite${cls ? ` ${cls}` : ''}`} viewBox={`${x} ${y} ${w} ${h}`} width={size} height={size} aria-hidden="true" focusable="false">
        <svg x={x} y={y} width={w} height={h} viewBox={`${x} ${y} ${w} ${h}`}>
          <image href={url} width={c.sheet[0]} height={c.sheet[1]} />
        </svg>
      </svg>
    );
  }
  return <img class={cls} src={url} alt="" width={size} height={size} draggable={false} loading={cls === 'thumb' ? 'lazy' : undefined} />;
}
/** PRE1: a product the shop has and cannot sell now says so; a card the shop does not have yet is "עוד לא במכירה".
 *  MOCK6: a product the safety rule holds says why first ("לא במכירה", "לא במכירה לחדר ילדים", "ממתין לתקן EN 71") */
const OUT_HE = 'המלאי אינו זמין כעת';
const priceHe = (s: TourSlot, o: TourOption): string =>
  saleLine(s) ?? (o.set ? '' : !o.product_id ? NOT_FOR_SALE_HE : o.price_agorot && o.available ? formatIls(o.price_agorot) : OUT_HE);
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
    // FB20: the product as sold — the option's studio picture (pictures().studio) where there is one, else today's card
    // (MOCK2, FB1: its layer trimmed to it, never a crop of the room)
    thumb: (pos) => cardFileUrl(wheelCard(s, s.options[pos - 1]!)),
    // MOCK4: a card on its room's sheet is drawn from its place there
    thumbNode: (pos) => {
      const o = s.options[pos - 1]!;
      const c = wheelCard(s, o);
      return c.sprite ? <CardPic o={o} card={c} /> : null;
    },
    cardGround: s.ground,
    info: (pos) => {
      const o = s.options[pos - 1]!;
      // the product's own page, when the shop has one
      const page = o.product_id && product(o.product_id) ? shopPath(o.product_id) : null;
      // MOCK6, the safety rule: the line, why, and for a toy waiting for EN 71 the waiting list (PRE1: its offer shows
      // once an email provider sends it, S18; until then the line alone)
      if (s.sale)
        return (
          <div class="tour-info tour-held" key={pos} data-sale={s.sale.state}>
            <p class="specs">
              <span class="held">{s.sale.label_he}</span>
            </p>
            <p class="small muted">{s.sale.why_he}</p>
            {s.sale.state === 'notify' ? <Waitlist room={groupOf(tour.room as RoomId)} slot={s.id} id={`wl-tour-${s.id}`} onStage status={null} /> : null}
          </div>
        );
      return (
        <p class="specs tour-info" key={pos}>
          {o.price_agorot && o.available ? <Price agorot={o.price_agorot} provisional={o.price_provisional} /> : o.set ? null : <span>{priceHe(s, o)}</span>}
          {page ? <a href={page}>לעמוד המוצר</a> : null}
        </p>
      );
    },
  };
}

/** the next animation frame: the page has rendered and laid out what was just asked of it */
const frame = (): Promise<void> => new Promise((r) => requestAnimationFrame(() => r()));
/**
 * a tiny plan of the house; the room the visitor is in is brass (FB3: "ריבוע קטן למטה שיסמן את המשך הסיור"). MOCK5: six
 * cells, as the plan lies — the living room and the kitchen at the front, the work room, the entrance and the bath in
 * the middle, the bedroom at the back. MOCK6: eight — the boy's and the girl's rooms between the work room and the
 * bedroom, on the plan's west side, the bath across the corridor from the boy's (docs/house-plan.json rooms)
 */
type At = 'entry' | 'living' | 'kitchen' | 'work' | 'bed' | 'bath' | 'boy' | 'girl';
const PlanIcon = ({ at }: { at: At }) => (
  <svg class="tour-plan" viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">
    <rect x="2" y="2" width="8" height="5" data-on={at === 'living' ? '' : undefined} />
    <rect x="10" y="2" width="8" height="5" data-on={at === 'kitchen' ? '' : undefined} />
    <rect x="2" y="7" width="5" height="3" data-on={at === 'work' ? '' : undefined} />
    <rect x="7" y="7" width="5" height="3" data-on={at === 'entry' ? '' : undefined} />
    <rect x="2" y="10" width="6.5" height="2.75" data-on={at === 'boy' ? '' : undefined} />
    <rect x="11" y="10" width="7" height="2.75" data-on={at === 'bath' ? '' : undefined} />
    <rect x="2" y="12.75" width="6.5" height="2.75" data-on={at === 'girl' ? '' : undefined} />
    <rect x="2" y="15.5" width="9" height="2.5" data-on={at === 'bed' ? '' : undefined} />
  </svg>
);
const AT: Record<GroupId, At> = { 'living-room': 'living', master: 'bed', bath: 'bath', dining: 'kitchen', work: 'work', boy: 'boy', girl: 'girl' };
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
/** the house's name beside the window (the designer's words); the style's own short name is the shop's (tour.name_he) */
const HOUSE_HE: Record<HouseId, string> = { [WM]: 'הבית המודרני החם', [NORDIC]: 'הבית הנורדי' };
/** MOCK4: a room as a sentence names it ("חדר השינה בבית …"); the article goes on the room's own word */
const PLACE_HE: Record<GroupId, string> = {
  'living-room': 'הסלון',
  master: 'חדר השינה',
  bath: 'חדר הרחצה',
  dining: 'המטבח ופינת האוכל',
  work: 'חדר העבודה',
  boy: 'חדר הילד',
  girl: 'חדר הילדה',
};

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
  /** MOCK4: the arrival's walk, its labels, and the rest on HC for reduced motion */
  const video = useRef<HTMLVideoElement>(null);
  const hcImg = useRef<HTMLImageElement>(null);
  const walkLabels = useRef<HTMLDivElement>(null);
  const lift = useRef<number[] | null>(null);
  const walkEnd = useRef<(() => void) | null>(null);
  /** the part of the walk's frame the window shows (all of it, but in "מילוי וגרירה"): its left edge and its width */
  const walkView = useRef({ left: 0, vis: 1 });
  /** "דלג": offered while the walk plays (set on the page directly: nothing renders at the walk's two ends) */
  const walkAct = useRef<HTMLDivElement>(null);
  const offerSkip = (on: boolean) => {
    const el = walkAct.current;
    if (!el) return;
    el.inert = !on;
    el.toggleAttribute('aria-hidden', !on);
  };
  /** the walk's file for this screen, chosen in the browser (the page is prerendered: no screen there) */
  const [walkSrc, setWalkSrc] = useState<(typeof arrival.videos)['desktop'] | null>(null);
  const [room, setRoomState] = useState<RoomId>('living-room');
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
  /** MOCK6: the fixture of the wheel of many options, open over the room at rest (?fixture=wheel10) */
  const [fixture, setFixture] = useState<{ W: typeof WheelComponent; mod: typeof import('./fixture-wheel'); load: (pos: number) => void } | null>(null);
  const fixtureDone = useRef(false);
  useEffect(() => {
    if (!loadFixture || cfg.fixture !== 'wheel10' || fixtureDone.current || phase !== 'room' || busy) return;
    fixtureDone.current = true;
    void loadFixture().then(([W, mod]) => setFixture({ W, mod, load: mod.fixtureLoader() }));
  }, [cfg.fixture, phase, busy]);
  const countEl = useRef<HTMLParagraphElement>(null);
  const [stat, setStat] = useState('');
  /** MOCK3: which of the three layouts the screen gets, and the window's size — measured on load, resize and rotation */
  const [lay, setLay] = useState<Layout>('desk');
  const [winSize, setWinSize] = useState({ w: 1280, h: 720, vh: 800 });
  const [zoomed, setZoomedState] = useState(false);
  const [more, setMoreState] = useState(false);
  /** the line over the room's name: the house, or once a visit the invitation to turn the phone */
  const [eye, setEyeState] = useState<Eye>(WM);
  /** FB13: the design direction (?design=a|b|c), after the first paint so the prerendered page hydrates as it is */
  const [dz, setDz] = useState<Design | null>(null);
  useEffect(() => setDz(DESIGN), []);
  // what the engine's callbacks and the queued presses read (they outlive a render)
  const live = useRef({ phase, busy, house, cfg, sel, open, lay, zoomed, more, room, walk: 0 });
  live.current = { phase, busy, house, cfg, sel, open, lay, zoomed, more, room, walk: live.current?.walk ?? 0 };
  /** the window's place in the page (CSS px), from the same measurement */
  const box = useRef({ x: 0, y: 0, w: 1, h: 1 });
  const queued = useRef<(() => void) | null>(null);
  const hint = useRef(0);
  const idleLoad = useRef(0);
  const resized = useRef(false);
  const tell = () => {
    const L = live.current;
    window.__hdTourState = {
      phase: L.phase,
      busy: L.busy,
      house: L.house,
      open: L.open?.slot.id ?? null,
      zoomed: L.zoomed,
      more: L.more,
      lay: L.lay,
      room: L.room,
      walk: L.walk,
      // MOCK8: the walk's rest and its pushes are kept across renders
      walkRest: window.__hdTourState?.walkRest,
      walkPushes: window.__hdTourState?.walkPushes,
    };
  };
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
  /** MOCK4: the room the page shows; the engine's `tour` changed already (tour/engine.ts toRoom) */
  const setRoomUi = (r: RoomId) => {
    live.current.room = r;
    setRoomState(r);
    tell();
  };
  const setCfg = (c: Partial<Cfg>) => {
    live.current.cfg = { ...live.current.cfg, ...c };
    setCfgState(live.current.cfg);
  };
  const setOpen = (o: { slot: TourSlot; before: number } | null) => {
    live.current.open = o;
    setOpenState(o);
    tell();
  };
  const setZoomed = (z: boolean) => {
    if (z) everZoomed.current = true;
    if (live.current.zoomed === z) return;
    live.current.zoomed = z;
    setZoomedState(z);
    tell();
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
  /** "מילוי וגרירה" is a phone's switch: a wide screen always shows the whole frame */
  const whole = () => live.current.cfg.frame === 'whole' || live.current.lay === 'desk';
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
    tell();
    setWinSize((was) => (was.w === m.w && was.h === m.h && was.vh === m.vh ? was : { w: m.w, h: m.h, vh: m.vh }));
  }
  /** the camera for the window as it is now: a close-up is put back, a zoom is dropped, the door stays the door */
  function relayout() {
    resized.current = false;
    const e = engine.current;
    if (!e) return;
    const o = live.current.open;
    // (the door's own camera only while the door's wall is drawn: ?skip=1 starts in the room)
    e.cam = o ? closeCam(e, o.slot) : e.d.doorAmt > 0 && live.current.phase === 'door' ? e.atDoor() : { ...e.rest };
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
    // MOCK4: the walk shows what the room's rest shows: in "מילוי וגרירה" the same part of the frame as the camera
    const rv = video.current;
    if (rv) {
      const { fw } = coverSize(vp, tour.aspect);
      const f = tour.camera.frame;
      const vis = Math.min(1, vp.w / (fw * e.rest.z) / (f[1] - f[0]));
      const left = (e.rest.cu - vp.w / (2 * fw * e.rest.z) - f[0]) / (f[1] - f[0]);
      const pos = vis < 0.999 ? Math.min(1, Math.max(0, left / (1 - vis))) : 0.5;
      rv.style.objectPosition = `${(pos * 100).toFixed(2)}% 50%`;
      walkView.current = { left: vis < 0.999 ? pos * (1 - vis) : 0, vis };
      if (hcImg.current) hcImg.current.style.objectPosition = rv.style.objectPosition;
    }
    lift.current = null;
    for (const s of tour.slots) {
      s.anchors.forEach(([u, v], i) => {
        const p = frameToScreen(u, v, cam, vp, tour.aspect);
        const ring = rings.current.get(`${s.id}:${i}`);
        if (ring) ring.style.transform = `translate(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px)`;
        if (i) return;
        const el = spots.current.get(s.id);
        if (!el) return;
        // MOCK4: a mark whose point is in the window is drawn whole inside it (at the rest, the camera's own frame, a
        // product's point can fall a few pixels from the window's edge); a point out of the window has no mark
        const q = inWin(p, vp);
        el.style.transform = `translate(${(q.x - 23).toFixed(1)}px, ${(q.y - 23).toFixed(1)}px)`;
        el.style.visibility = q.on ? 'visible' : 'hidden';
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
  }
  /** where a slot's mark is in the window now (CSS px), or null when it is out of view */
  function markOf(s: TourSlot, e: TourEngine): Mark | null {
    const [u, v] = s.anchors[0]!;
    const q = inWin(frameToScreen(u, v, e.cam, e.vp, tour.aspect), e.vp);
    return q.on ? { id: s.id, x: q.x, y: q.y } : null;
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
      // measured once per label, and never inside an effect (MOCK2: a measurement is what forces a layout): before
      // the way in starts, and when the room rests. A label that is not laid out yet is asked again next time.
      if (!w) {
        w = metrics.dom(() => tag.offsetWidth);
        if (w) tagW.current.set(text, w);
      }
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
      const order = on ? items() : [...items()].sort((a, b) => b.depth_m - a.depth_m);
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
        // MOCK4: a room built from its render folder has no measure of how much the products fill (yet)
        sep!.textContent = tour.cover ? ' · ' : '';
        b!.textContent = tour.cover ? `${Math.round(tour.cover * 100)}%` : '';
        b!.removeAttribute('dir');
        tail!.textContent = tour.cover ? ' מהחדר' : '';
      } else {
        a!.textContent = '';
        mid!.textContent = 'פריטים ';
        sep!.textContent = '';
        b!.textContent = `${n}/${items().length}`;
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
    const urls = [...new Set(tour.slots.flatMap((s) => s.options.slice(1).map(cardUrl)))];
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
      // MOCK4: ?skip=1&room=…: the tour starts in that room (the tests and the evidence)
      const first = live.current.cfg.skip ? live.current.cfg.room : 'living-room';
      if (first !== tour.room) {
        setRoom(first);
        setRoomUi(first);
      }
      const e = m.TourEngine.create({
        canvas: c,
        reduceMotion: prefersReducedMotion(),
        onCamera: place,
        onResize: () => (live.current.busy ? (resized.current = true) : relayout()),
        // the sharpness evidence: the same phone composing at the layers' own width, to compare with (never the default)
        width: !__ARTIFACT__ && new URLSearchParams(location.search).get('w') === 'hi' ? tour.widths.hi : undefined,
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
      // MOCK4: the door is the arrival's first frame (DOOR2), in the page over the room; the engine draws no door
      e.d.doorAmt = 0;
      e.doorCu = DOOR_CU;
      await e.start();
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
        ui.count(items().length, true);
        e.background();
        otherCards(e);
      } else {
        // MOCK2 (FB1): the door waits until the room can be animated — every layer of it fetched, decoded, uploaded
        // and composed once, every program compiled. Until then the button says so and nothing moves: even the slow
        // push of the door starts afterwards, so the room's own decodes never land inside it. MOCK3: and the strip's
        // pictures, and the wheel's code, so nothing of them arrives inside the reveal or the first close-up.
        void Promise.all([e.whenWarm(), stripReady(), wheelFor()]).then(() => {
          setWarm(true);
          primeRings();
          // MOCK4: the walk is fetched once the room it lands in is ready (the room first: the door waits for it)
          if (video.current) video.current.preload = 'auto';
          // a visitor who stays at the door: the rest of the house loads behind it, once the room itself is ready
          idleLoad.current = window.setTimeout(() => e.background(), 5000);
        });
      }
      return e;
    }));
  }
  useEffect(() => {
    setCfg(readCfg());
    setWalkSrc(walkFor(innerWidth));
    measure();
    // the page's own measurement of the window: a resize or a rotation, never an animation (the window keeps its size)
    const ro = new ResizeObserver(() => measure());
    if (win.current) ro.observe(win.current);
    // a pinch is ours, not the browser's: the page neither scrolls nor zooms under two fingers, or under a zoomed picture
    const w = win.current;
    const hold = (ev: TouchEvent) => {
      if (live.current.phase === 'room' && (ev.touches.length > 1 || gest.current || engine.current?.zoomed)) ev.preventDefault();
    };
    const noGesture = (ev: Event) => ev.preventDefault();
    w?.addEventListener('touchmove', hold, { passive: false });
    w?.addEventListener('gesturestart', noGesture);
    // MOCK8 (FB19): at the door and on the walk, a scroll, a swipe up or ↓ walks on (the door's first one goes in)
    const walking = () => live.current.phase === 'door' || live.current.phase === 'entering';
    const go = (k: number, fresh: boolean) => {
      if (live.current.phase === 'door') {
        if (fresh && !live.current.busy) void goIn();
      } else walkPush(k, fresh);
    };
    const onWheel = (ev: WheelEvent) => {
      if (!walking()) return;
      ev.preventDefault();
      const px = ev.deltaMode === 1 ? ev.deltaY * 40 : ev.deltaMode === 2 ? ev.deltaY * 800 : ev.deltaY;
      const g = gesture.current.wheel(px, ev.timeStamp);
      if (g.k > 0) go(g.k, g.fresh);
    };
    let touchY: number | null = null;
    const onTouchStart = (ev: TouchEvent) => void (touchY = ev.touches.length === 1 ? ev.touches[0]!.clientY : null);
    const onTouchMove = (ev: TouchEvent) => {
      if (!walking()) return;
      if (live.current.phase === 'entering') ev.preventDefault();
      if (touchY === null || ev.touches.length !== 1) return;
      if (touchY - ev.touches[0]!.clientY > GESTURE.swipePx) {
        touchY = null;
        go(1, true);
      }
    };
    const onKey = (ev: KeyboardEvent) => {
      if (live.current.phase !== 'entering' || !walkCtl.current) return;
      if (!['ArrowDown', 'PageDown', ' '].includes(ev.key) || ev.target instanceof HTMLButtonElement) return;
      ev.preventDefault();
      walkPush(1, true);
    };
    w?.addEventListener('wheel', onWheel, { passive: false });
    w?.addEventListener('touchstart', onTouchStart, { passive: true });
    w?.addEventListener('touchmove', onTouchMove, { passive: false });
    addEventListener('keydown', onKey);
    // after the door is painted: the engine's chunk, the empty room, then the products behind it
    let idle = 0;
    const later = () => (idle = window.setTimeout(() => void ensure(), 60));
    if (document.readyState === 'complete') later();
    else addEventListener('load', later, { once: true });
    return () => {
      ro.disconnect();
      w?.removeEventListener('touchmove', hold);
      w?.removeEventListener('gesturestart', noGesture);
      w?.removeEventListener('wheel', onWheel);
      w?.removeEventListener('touchstart', onTouchStart);
      w?.removeEventListener('touchmove', onTouchMove);
      removeEventListener('keydown', onKey);
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
    if (!e.zoomed) spread();
    void e.wait(800).then(() => !live.current.busy && ui.label(null, false));
    clearTimeout(hint.current);
    hint.current = window.setTimeout(() => {
      const hero = items().find((s) => s.hero);
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
    tell();
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
    if (!e.zoomed) return;
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

  // ---------- MOCK4: the arrival (route ch. 11.1), the labels at the rest on HC, and "דלג" ----------
  /** the names' places at the rest, laid out once: a measurement, made before the walk moves (never inside it) */
  function layLabels() {
    const root = walkLabels.current;
    if (lift.current || !root) return;
    const tags = [...root.querySelectorAll<HTMLElement>('.tour-door-name')];
    const sizes = metrics.dom(() => tags.map((t) => ({ w: t.offsetWidth, h: t.offsetHeight })));
    lift.current = layoutLabels(sizes, box.current.w, box.current.h);
  }
  /** the labels' pixels for a frame of the walk: each lintel's hairline, each name over its door, and its opacity */
  function drawLabels(f60: number, force = false) {
    const root = walkLabels.current;
    if (!root) return;
    const cam = camAt(f60);
    const on = !!cam && arrival.labels.some((_, i) => labelOpacity(i, f60) > 0);
    root.toggleAttribute('data-on', on || force);
    if (!cam || (!on && !force)) return;
    const { w, h } = box.current;
    const { left, vis } = walkView.current;
    const x = (u: number) => ((u - left) / vis) * w;
    layLabels();
    const lines = root.querySelectorAll<SVGLineElement>('line');
    const names = root.querySelectorAll<HTMLElement>('.tour-door-name');
    arrival.labels.forEach((l, i) => {
      const p = labelPose(l, cam);
      const o = force ? 1 : labelOpacity(i, f60);
      const line = lines[i];
      const name = names[i];
      if (!line || !name) return;
      if (!p || o <= 0) {
        line.style.opacity = '0';
        name.style.opacity = '0';
        return;
      }
      line.setAttribute('x1', (x(p.a.u) / w).toFixed(4));
      line.setAttribute('y1', p.a.v.toFixed(4));
      line.setAttribute('x2', (x(p.b.u) / w).toFixed(4));
      line.setAttribute('y2', p.b.v.toFixed(4));
      line.style.opacity = o.toFixed(3);
      const up = lift.current![i] ?? 0;
      name.style.setProperty('--lead', `${up}px`);
      name.style.transform = `translate(${x(p.at.u).toFixed(1)}px, ${(p.at.v * h - 8 - up + (1 - o) * 6).toFixed(1)}px)`;
      name.style.opacity = o.toFixed(3);
    });
  }
  /**
   * The walk itself (MOCK8, FB19): from the door it advances by gentle scroll impulses with inertia (tour/walk.ts): the
   * press of "היכנסו" is the first push, every scroll, swipe, ↓ or "המשך" another; each plays a stretch and eases to a
   * stop, and two or three reach the end. The video plays at the rate the impulses give it (forward only, FB8). At the
   * end: a still (ka2: HT2, the push into the living room starts from it, pixel for pixel) or the room's own frame
   * (fb19). Resolves there. Reduced motion: a short fade, the door to the hall (HDx2 fb19) to the room.
   */
  function walk(e: TourEngine): Promise<void> {
    const v = video.current;
    if (!v) return Promise.resolve();
    const reduce = prefersReducedMotion();
    return new Promise<void>((resolve) => {
      let done = false;
      let raf = 0;
      const finish = () => {
        if (done) return;
        done = true;
        cancelAnimationFrame(raf);
        v.onended = null;
        v.pause();
        walkEnd.current = null;
        walkCtl.current = null;
        e.stop('arrival');
        walkLabels.current?.removeAttribute('data-on');
        stage.current?.removeAttribute('data-rest');
        if (window.__hdTourState) window.__hdTourState.walkRest = false;
        v.onplaying = null;
        // ka2: the walk's last frame is the hall's still; it goes on the canvas exactly where the video shows it (the
        // same picture, the exact file), the video gives way over it, and the push into the living room starts from it
        const img = endStill.current;
        if (!reduce && arrival.end === 'still' && img && img.naturalWidth) {
          const pos = parseFloat(v.style.objectPosition || '50') / 100;
          stilled.current = e.holdStill(img, coverMap(img.naturalWidth, img.naturalHeight, e.vp.w, e.vp.h, Number.isFinite(pos) ? pos : 0.5));
        }
        offerSkip(false);
        stage.current?.removeAttribute('data-walk');
        stage.current?.removeAttribute('data-played');
        resolve();
      };
      walkEnd.current = finish;
      stage.current?.setAttribute('data-walk', '');
      offerSkip(true);
      if (reduce) {
        // reduced motion: a short fade, the door → the hall with the living room through the opening → the room
        stage.current?.setAttribute('data-hc', '');
        stage.current?.setAttribute('data-played', '');
        announce('המבואה');
        window.setTimeout(finish, 1100 * timeScale());
        return;
      }
      // the walk is an effect like any other: nothing is uploaded, decoded or measured while it moves (FB1)
      e.walk('arrival');
      const dur = Math.max(0.1, (arrival.frames - 1) / 60);
      const ctl = new WalkPlay({ duration: dur, impulse: arrival.impulse, snap: arrival.snap });
      walkCtl.current = ctl;
      let last = performance.now();
      let rest = true;
      const loop = (now: number) => {
        if (done) return;
        const dt = Math.min(0.1, (now - last) / 1000) / timeScale();
        last = now;
        const t = v.currentTime;
        const f = frameAt(Math.min(t, dur));
        live.current.walk = f;
        if (window.__hdTourState) window.__hdTourState.walk = f;
        // a walk with names on its doors draws them (MOCK4's; FB19's has none)
        if (arrival.labels.length) drawLabels(f);
        if (v.ended || t >= dur - 0.5 / 60) return finish();
        const r = ctl.step(t, dt);
        if (r > 0) {
          // (the evidence's slow motion stretches the walk like every other duration)
          const rate = Math.min(4, Math.max(WALK.min, r / timeScale()));
          if (Math.abs(v.playbackRate - rate) > 0.01) v.playbackRate = rate;
          if (v.paused) void v.play().catch(() => undefined);
        } else if (!v.paused) v.pause();
        if ((r === 0) !== rest) {
          rest = r === 0;
          stage.current?.toggleAttribute('data-rest', rest);
          if (window.__hdTourState) window.__hdTourState.walkRest = rest;
          if (rest) announce('גללו כדי להמשיך');
        }
        raf = requestAnimationFrame(loop);
      };
      v.onended = finish;
      // the door's picture gives way when the walk's first frame is on screen (the same frame: D0)
      v.onplaying = () => stage.current?.setAttribute('data-played', '');
      v.currentTime = 0;
      v.playbackRate = WALK.min;
      // the press that started the walk is its first push
      ctl.push(0, GESTURE.first);
      walkPushes.current = 1;
      if (window.__hdTourState) window.__hdTourState.walkPushes = 1;
      raf = requestAnimationFrame(loop);
    });
  }
  /** MOCK8: one push of the walk (a scroll, a swipe, ↓ or "המשך"), `k` impulses; a new gesture counts as a push */
  const walkPush = (k: number, fresh: boolean) => {
    const ctl = walkCtl.current;
    const v = video.current;
    if (!ctl || !v || k <= 0) return;
    ctl.push(v.currentTime, k);
    if (fresh) {
      walkPushes.current++;
      if (window.__hdTourState) window.__hdTourState.walkPushes = walkPushes.current;
    }
  };
  const walkCtl = useRef<WalkPlay | null>(null);
  const walkPushes = useRef(0);
  const gesture = useRef(new Gesture());
  /** MOCK8: the walk's last frame (ka2), decoded before the walk starts: the push into the living room starts from it */
  const endStill = useRef<HTMLImageElement | null>(null);
  /** MOCK7: the walk's last frame is on the canvas (the push into the living room starts from it) */
  const stilled = useRef(false);
  /** the walk's file has enough to play through (or 6 s have passed: it plays as it comes) */
  const canPlay = (v: HTMLVideoElement): Promise<void> =>
    v.readyState >= 3
      ? Promise.resolve()
      : new Promise((r) => {
          const t = window.setTimeout(r, 6000);
          v.preload = 'auto';
          v.addEventListener(
            'canplay',
            () => {
              clearTimeout(t);
              r();
            },
            { once: true },
          );
        });
  const skipWalk = () => walkEnd.current?.();
  /** MOCK8: the walk's last frame as a picture (ka2), decoded; null when the walk ends on the room */
  async function loadStill(): Promise<HTMLImageElement | null> {
    const url = stillUrl();
    if (!url) return null;
    if (endStill.current?.complete && endStill.current.naturalWidth) return endStill.current;
    const img = new Image();
    img.src = url;
    try {
      await img.decode();
      return img;
    } catch {
      return null;
    }
  }

  // ---------- the beats ----------
  const goIn = () =>
    live.current.phase === 'door' &&
    beat(async (e, m) => {
      await shut(e);
      // nothing starts moving before the room is ready (the button is held until then; a keyboard press waits here)
      await e.whenWarm();
      if (video.current && !prefersReducedMotion()) await canPlay(video.current);
      // MOCK8: the walk's last frame (ka2: the hall), decoded before anything moves: the push starts from it
      endStill.current = await loadStill();
      // MOCK8: a walk that lands on the room's own frame (fb19) lands on the room with its products in it
      const inRoom = arrival.end === 'room';
      if (inRoom) {
        await e.products();
        tour.slots.forEach((s) => e.settle(s.id, true));
        e.mask();
      }
      setPhase('entering');
      // a wide screen: the labels of the reveal are given their rows now, before anything moves
      await frame();
      spread();
      // MOCK8 (FB19): the walk from the door, by scroll impulses; the canvas under it holds the room it lands in
      e.cam = { ...e.rest };
      e.render();
      layLabels();
      stilled.current = false;
      await walk(e);
      // MOCK7: from the hall into the living room, walking in code (until the rest of the FB19 walk is made)
      if (stilled.current) await e.fromStill('arrive-living', PUSH_MS.arrive, arrival.land.cam);
      stilled.current = false;
      stage.current?.removeAttribute('data-hc');
      if (inRoom) {
        ui.spots(true);
        ui.count(items().length, true);
      } else await m.reveal(e, ui, live.current.cfg.way === 'full' ? 'c' : live.current.cfg.fx);
      setPhase('room');
      atRest(e);
      announce(`${items().length} פריטים בסלון`);
      title.current?.focus({ preventScroll: true });
    }, goIn);
  /** MOCK4: back to the door (in the panel, "כניסה"): the door's frame comes over the window (a dissolve, temporary),
   *  and behind it the living room is made ready, empty, for the next arrival's reveal */
  const goOut = () =>
    live.current.phase === 'room' &&
    !live.current.open &&
    beat(async (e) => {
      await shut(e);
      await wholeFrame(e);
      ui.spots(false);
      ui.label(null, false);
      ui.count(null);
      setPhase('door');
      if (video.current) video.current.currentTime = 0;
      await e.ui('door-in', ROOM_FADE_MS);
      await e.toRoom('living-room', 0, false);
      setHouse(WM);
      setEye(WM);
      setRoomUi('living-room');
      fold.current?.focus({ preventScroll: true });
    }, goOut);
  /**
   * MOCK4: to a room of the house (the panel's "חדרים"). TEMPORARY: a dissolve between the two rooms at rest (engine
   * toRoom), until the T-C* clips exist. From the door, the door's frame dissolves into the room.
   * MOCK5: and to another frame of the room the visitor is in (the frame control): the same, a shorter dissolve.
   */
  const goRoom = (id: RoomId, inRoom = false) =>
    (live.current.phase === 'room' || live.current.phase === 'door') &&
    !live.current.open &&
    !(live.current.phase === 'room' && live.current.room === id) &&
    beat(
      async (e) => {
        await shut(e);
        await wholeFrame(e);
        clearTimeout(turn.current);
        const fromDoor = live.current.phase === 'door';
        ui.spots(false);
        ui.label(null, false);
        ui.count(null);
        setEye(WM);
        // the next room's sheet of cards (its strip, its wheel) is fetched and decoded before anything moves
        const sheet = ROOMS[id].slots.find((x) => x.options[0]?.card.sprite)?.options[0];
        if (sheet) {
          const img = new Image();
          img.src = cardUrl(sheet);
          held.current.push(img);
          await decoded(img);
        }
        // MOCK7: a walk between rooms and between the frames of a room (2.5D, in code, until the real clips); reduced
        // motion keeps the dissolve
        const walkIt = !fromDoor && !e.reduce;
        await e.toRoom(
          id,
          fromDoor ? 0 : walkIt ? (inRoom ? PUSH_MS.frame : PUSH_MS.room) : inRoom ? FRAME_FADE_MS : ROOM_FADE_MS,
          true,
          inRoom ? `frame-${id}` : `room-${id}`,
          walkIt ? (inRoom ? PUSH_AMP.frame : PUSH_AMP.room) : 0,
        );
        setHouse(WM);
        setRoomUi(id);
        if (fromDoor) {
          setPhase('room');
          await e.ui('door-out', ROOM_FADE_MS);
        } else setPhase('room');
        await frame();
        place();
        ui.count(items().length, true);
        atRest(e);
        announce(inRoom && tour.frame_he ? `${ROOM_HE[id]}, ${tour.frame_he}` : `${ROOM_HE[id]}, ${roomCount(groupOf(id)).total} מוצרים למכירה בחדר`);
        // the frame control keeps the focus where it was (the visitor may switch back); a room's button gives it to the title
        if (!inRoom) title.current?.focus({ preventScroll: true });
      },
      () => goRoom(id, inRoom),
    );
  const replay = (fx?: Reveal) =>
    live.current.phase === 'room' &&
    live.current.room === 'living-room' &&
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
    live.current.room === 'living-room' &&
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
  /** MOCK4: whether the visitor may zoom in this room (the bedroom: the art 776445 is ×1 only, its rights) */
  const canZoom = () => tour.zoom !== false;
  const zoomTo = (z: number, at?: { u: number; v: number }) =>
    live.current.phase === 'room' &&
    !live.current.open &&
    (z <= 1 || canZoom()) &&
    beat(async (e) => {
      stage.current?.classList.add('moving');
      const to = z <= 1 ? e.rest : clampCam({ cu: at?.u ?? e.cam.cu, cv: at?.v ?? e.cam.cv, z }, e.vp, tour.aspect);
      // the marks are placed again when the camera lands (onCamera), and come back there
      await e.moveCam(z <= 1 ? 'zoom-back' : 'zoom', to, ZOOM.ms);
      stage.current?.classList.remove('moving');
      setZoomed(e.zoomed);
      sharpen(e);
    });
  /** the sharpness switch (temporary): while the picture rests zoomed, the canvas is drawn at the screen's own pixels */
  const sharpen = (e: TourEngine) => e.setDprCap(live.current.cfg.sharp && e.zoomed ? 3 : 2);

  // ---------- the close-up and the wheel ----------
  const opener = useRef<HTMLElement | null>(null);
  const closing = useRef(false);
  /** the camera of a product's close-up: the product fills about 60% of what the layout leaves free of the window */
  function closeCam(e: TourEngine, s: TourSlot): Cam {
    // MOCK4: a product shown at ×1 only (its rights) opens its card where it is: the camera stays at the rest
    if (s.closeup === false) return { ...e.rest };
    const b = optionOf(s, e.selection).box;
    let cam = e.camFor(padded(b), closeReserve(live.current.lay, e.vp.h, !whole()));
    // on its side the arc is on the window's bottom edge: the product ends 16 px over it wherever the frame allows
    if (live.current.lay === 'rails' && whole()) cam = overArc(cam, b, e.vp, tour.aspect);
    if (cam.z < e.rest.z) cam = clampCam({ ...cam, z: e.rest.z }, e.vp, tour.aspect);
    return clear(e, cam, b) ?? { ...e.rest };
  }
  /**
   * MOCK4: a close-up never shows the room's ×1-only boxes (prints whose rights are unclear: the bedroom's 776445, and
   * MOCK5's 386242 in the bedroom, the kitchen and the work room). A view that would show one is moved past it — below,
   * above or to a side, and closer if it must be — while the product stays whole in it; of the views that show none, the
   * one nearest the close-up wins. If the product cannot be seen without a box, there is no close-up (null).
   */
  function clear(e: TourEngine, cam: Cam, b: [number, number, number, number]): Cam | null {
    const boxes = tour.avoid ?? [];
    if (!boxes.length) return cam;
    const { fw, fh } = coverSize(e.vp, tour.aspect);
    const half = (c: Cam) => [e.vp.w / (2 * fw * c.z), e.vp.h / (2 * fh * c.z)] as const;
    const view = (c: Cam) => {
      const [hu, hv] = half(c);
      return [c.cu - hu, c.cu + hu, c.cv - hv, c.cv + hv] as const;
    };
    const m = 0.008;
    const hits = (c: Cam) => {
      const v = view(c);
      return boxes.some((a) => v[0] < a[1] + m && v[1] > a[0] - m && v[2] < a[3] + m && v[3] > a[2] - m);
    };
    // the product stays in the view about as whole as the close-up had it: 85% of what it showed (the bedroom's throw,
    // pushed under the prints, keeps 95%; a pendant's box runs up its cord to the ceiling, which no close-up shows whole)
    const seen = (c: Cam) => {
      const v = view(c);
      return Math.max(0, Math.min(v[1], b[1]) - Math.max(v[0], b[0])) * Math.max(0, Math.min(v[3], b[3]) - Math.max(v[2], b[2]));
    };
    const want = seen(cam) * 0.85;
    const keeps = (c: Cam) => seen(c) >= want;
    if (!hits(cam)) return cam;
    // pushed a little further than the test, so the view's edge is clearly past the box
    const p = m * 1.5;
    const kv = e.vp.h / (2 * fh);
    const ku = e.vp.w / (2 * fw);
    const tries: Cam[] = [];
    for (const a of boxes) {
      // below the box: the view's top edge under its bottom (MOCK4's one move), closer if the frame's height asks it
      const top = a[3] + p;
      if (b[2] >= top) {
        const z = Math.max(cam.z, (2 * kv) / (1 - top));
        tries.push({ cu: cam.cu, cv: Math.max(cam.cv, top + kv / z), z });
      }
      // above it: the view's bottom edge over its top
      const bottom = a[2] - p;
      if (b[3] <= bottom) {
        const z = Math.max(cam.z, (2 * kv) / bottom);
        tries.push({ cu: cam.cu, cv: Math.min(cam.cv, bottom - kv / z), z });
      }
      // beside it: the view's edge past its left or right side; the view's top edge stays where the close-up had it
      // (the product sits in the upper part, the wheel under it)
      const top0 = cam.cv - half(cam)[1];
      const left = a[0] - p;
      if (b[1] <= left) {
        const z = Math.max(cam.z, (2 * ku) / left);
        tries.push({ cu: Math.min(cam.cu, left - ku / z), cv: top0 + kv / z, z });
      }
      const right = a[1] + p;
      if (b[0] >= right) {
        const z = Math.max(cam.z, (2 * ku) / (1 - right));
        tries.push({ cu: Math.max(cam.cu, right + ku / z), cv: top0 + kv / z, z });
      }
    }
    const ok = tries.map((c) => clampCam(c, e.vp, tour.aspect)).filter((c) => !hits(c) && keeps(c));
    if (!ok.length) return null;
    const cost = (c: Cam) => Math.abs(Math.log(c.z / cam.z)) * 2 + Math.hypot(c.cu - cam.cu, c.cv - cam.cv);
    return ok.sort((x, y) => cost(x) - cost(y))[0]!;
  }
  const picker = () => stage.current?.querySelector<HTMLElement>('.picker') ?? null;
  const openSlot = (s: TourSlot, from?: HTMLElement | null) =>
    live.current.phase === 'room' &&
    live.current.house === WM &&
    !live.current.open &&
    beat(async (e) => {
      opener.current = from ?? (document.activeElement as HTMLElement | null);
      // FB20: every slot, 3 to 12 options, takes the 3D ring (the arc stays the room page's; the scroll-snap carousel is retired)
      const W = await wheelFor();
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
        // FB20: the room dims under the wheel while it is open (and darker away from the product)
        e.d.ev = DIM.ev * ease;
        e.d.vig = DIM.vig * ease;
        e.d.vigBox = s.rect;
        // the wheel rises 0.15 s before the camera lands
        if (t >= 0.85 && !rise) rise = show();
      });
      await (rise ?? show());
      sharpen(e);
    });
  /**
   * FB20: the ring rests on an option. The room does not change under the open wheel; the option's layer (a patch, in a
   * wheel of many) is fetched now, so the selection's reveal starts at once.
   */
  function preview(s: TourSlot, pos: number) {
    const e = engine.current;
    if (e && pos !== e.selection[s.id]) void e.option(s.id, pos);
  }
  /**
   * The wheel closes: `chosen` is the option picked (a position), or null (Escape, X, a tap outside: nothing changes).
   * FB20, the selection moment: the wheel leaves, and the dim lifts as the chosen product's layer cross-fades into the
   * room (fx.select, REVEAL_MS); the camera starts back to the whole frame as the reveal ends, so the product is seen
   * in place and then in the room around it. A cancel only lifts the dim on the way back.
   */
  function close(chosen: number | null): void {
    const o = live.current.open;
    if (!o || closing.current) return;
    void beat(
      async (e) => {
        closing.current = true;
        const m = mod.current;
        picker()?.removeAttribute('data-in');
        e.setDprCap(2);
        // the camera back to the whole frame; a cancel lifts the dim on the way (a choice: the reveal lifts it)
        const back = (lift: boolean) => {
          const ev0 = e.d.ev;
          const vig0 = e.d.vig;
          const also = (ease: number) => {
            e.d.ev = ev0 * (1 - ease);
            e.d.vig = vig0 * (1 - ease);
          };
          return e.moveCam('zoom-out', e.rest, live.current.lay === 'desk' || !whole() ? 1000 : ZOOM.ms, lift ? also : undefined);
        };
        if (chosen !== null && m) {
          // the reveal, then the camera back: its last stretch runs under the first of the move
          const reveal = m.select(e, o.slot, chosen, REVEAL_MS);
          await e.wait(REVEAL_MS * 0.7);
          await Promise.all([reveal, back(false)]);
          setSel({ ...e.selection });
        } else await back(true);
        e.d.ev = 0;
        e.d.vig = 0;
        stage.current?.classList.remove('zoomed');
        setOpen(null);
        setZoomed(false);
        closing.current = false;
        atRest(e);
        // the strip, the counter and the folded control come back in their own cells
        void e.ui('closeup-out', 320);
        if (chosen !== null) announce(`${o.slot.name_he}: ${nameHe(o.slot, optionOf(o.slot, e.selection))} מוצג בחדר`);
        const to = phoneRules() && live.current.cfg.pick === 'list' ? tiles.current.get(o.slot.id) : spots.current.get(o.slot.id);
        void frame().then(() => (to ?? opener.current)?.focus({ preventScroll: true }));
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
    if (e.zoomed && e.cam.z < e.rest.z * ZOOM.snap) return void zoomTo(1);
    if (!e.zoomed) e.cam = { ...e.rest };
    place();
    e.render();
    stage.current?.classList.remove('moving');
    setZoomed(e.zoomed);
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
    if (ptrs.current.size !== 2 || L.open || !whole() || !canZoom()) return;
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
      const { z: raw, stretch: s } = pinchZoom((g.z0 * f.d) / g.d0);
      // MOCK4: never less than the frame at rest (the camera's own frame, not the canvas round it)
      const z = Math.max(raw, e.rest.z);
      e.cam = clampCam({ z, cu: g.u - (f.x - e.vp.w / 2) / (fw * z), cv: g.v - (f.y - e.vp.h / 2) / (fh * z) }, e.vp, tour.aspect);
      stretch(s === 1 ? 'none' : `scale(${s.toFixed(4)})`, f.x, f.y);
      return;
    }
    if (live.current.open || live.current.busy) return;
    if (!g && p.moved > 6) {
      if (e.zoomed && whole()) begin(e, (g = { kind: 'drag', u: e.cam.cu, v: e.cam.cv }), 'drag');
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
    if (live.current.cfg.zoom === 'double' && phoneRules() && !live.current.open && canZoom()) {
      const at = screenToFrame(p.x, p.y, e.cam, e.vp, tour.aspect);
      if (tapWait.current) {
        clearTimeout(tapWait.current);
        tapWait.current = 0;
        return void zoomTo(e.zoomed ? 1 : ZOOM.step, at);
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
  const marks = (e: TourEngine): Mark[] => items().flatMap((s) => (e.visible.has(s.id) ? (markOf(s, e) ?? []) : []));
  function tap(x: number, y: number) {
    const e = engine.current;
    const L = live.current;
    if (!e || L.busy || L.phase !== 'room') return;
    const at = screenToFrame(x, y, e.cam, e.vp, tour.aspect);
    if (L.open) {
      // in the close-up: a tap in the window outside the product closes it (the phone; a wide screen has the wheel there)
      const b = optionOf(L.open.slot, e.selection).box;
      if (phoneRules() && (at.u < b[0] || at.u > b[1] || at.v < b[2] || at.v > b[3])) close(null);
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
    if (L.cfg.pick === 'dots' && canZoom() && e.cam.z < e.rest.z * ZOOM.snap) return void zoomTo(ZOOM.step, at);
    const r = tapRule(x, y, marks(e));
    if (!r) return;
    const from = (id: string) => (L.cfg.pick === 'list' ? tiles.current.get(id) : spots.current.get(id));
    if ('open' in r) return void openSlot(e.slot(r.open), from(r.open));
    // two marks too close to tell apart: ×2 to the point, where they stand apart (and once more, up to the limit);
    // MOCK4: in a room without zoom, the nearer one opens
    const z = !canZoom() ? 0 : e.cam.z < ZOOM.step - 0.01 ? ZOOM.step : e.cam.z < ZOOM.max - 0.01 ? ZOOM.max : 0;
    if (z) void zoomTo(z, at);
    else void openSlot(e.slot(r.nearest), from(r.nearest));
  }

  const inRoom = phase === 'room';
  const wm = house === WM;
  const phone = lay !== 'desk' && cfg.frame === 'whole';
  /** the strip is the way to choose (and the screen reader's list); the marks are then decoration */
  const strip = phone && cfg.pick === 'list';
  const listOn = strip && inRoom && wm && !open;
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
  // MOCK4: the rooms of the house that are built (a button each, TOUR1); the move between rooms is a temporary
  // dissolve until the T-C* clips exist. MOCK5: every room the owner approved — the living room, the bedroom, the bath,
  // the kitchen and the work room; a room's button lands on its rest frame (FRAMES[room][0])
  const group = groupOf(room);
  const here = (g: GroupId) => inRoom && group === g;
  const toRoomBtn = (g: GroupId) => () => void (here(g) ? setMore(false) : phase === 'door' && g === 'living-room' ? goIn() : goRoom(FRAMES[g][0]!));
  const rooms: { id?: string; name: string; at: At; here?: boolean; go?: () => void; n?: number }[] = [
    // the room the visitor is in: its button only closes the panel
    { id: 'tour-out', name: 'כניסה', at: 'entry', here: phase === 'door', go: () => void (phase === 'door' ? setMore(false) : goOut()) },
    ...GROUP_IDS.map((g) => ({
      id: g === 'living-room' ? 'tour-living' : `tour-${g}`,
      name: GROUP_HE[g],
      at: AT[g],
      here: here(g),
      go: toRoomBtn(g),
      // FB13: a direction shows how many products each room sells (the owner's line)
      n: dz ? roomCount(g).total : undefined,
    })),
  ];
  /** MOCK5: the frames of the room the visitor is in (the frame control, when it has more than one) */
  const frames = FRAMES[group];
  const count = roomCount(group);
  // MOCK6: how many of them the safety rule holds (shown, not sold here or waiting for their standard)
  const heldN = roomHeld(group);
  // "קנה את המראה": the style's own magazine page on the site; the Artifact preview has no such page, and shows the
  // list of the room's products under the tour instead. MOCK4: only the living room has a magazine page so far
  // MOCK7: the story is the old living room's (the old table, the old camera): no link from M0-W
  const lookHref = __ARTIFACT__ || room !== 'living-room' || tour.styles === false ? null : `/story/${tour.room}/${house}/`;
  const living = room === 'living-room';
  const shown = items();
  // FB13: what the chosen direction draws round the tour (design/Chrome.tsx), all of it from the tour's own data
  const chrome: ChromeData | null = dz
    ? {
        d: dz,
        phase,
        stop: phase === 'door' ? 0 : GROUP_IDS.indexOf(group) + 1,
        stops: GROUP_IDS.length + 1,
        roomHe: ROOM_HE[room],
        houseHe: HOUSE_HE[house],
        frame: tour.frame ?? 'M0',
        camH: tour.camera?.loc?.[2] ?? null,
        items: shown.length,
        sale: count.total,
        total: GROUP_IDS.reduce((n, g) => n + roomCount(g).total, 0),
        open: open ? { n: shown.findIndex((s) => s.id === open.slot.id) + 1, of: shown.length, name: open.slot.name_he } : null,
      }
    : null;
  return (
    <>
      <section
        class={`stage tour${noGl ? ' tour-nogl' : ''}`}
        ref={stage}
        data-phase={phase}
        data-house={house}
        data-design={dz ?? undefined}
        data-ready={ready ? '' : undefined}
        data-frame={cfg.frame}
        data-pick={cfg.pick}
        data-bg={cfg.bg}
        data-close={open || fixture ? '' : undefined}
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
                  {HOUSE_HE[WM]}
                </h1>
              ) : (
                <p class="h">{HOUSE_HE[WM]}</p>
              )}
            </div>
            <div class="tour-t t-room" {...(phase !== 'door' && !(open && phone) ? {} : off)}>
              <p class="eyebrow tour-eyes">
                <span data-k={WM} aria-hidden={eye === WM ? undefined : 'true'}>
                  {HOUSE_HE[WM]}
                </span>
                <span data-k={NORDIC} aria-hidden={eye === NORDIC ? undefined : 'true'}>
                  {HOUSE_HE[NORDIC]}
                  <span class="stage-status">תמונות זמניות</span>
                </span>
                <span data-k="rotate" aria-hidden="true">
                  ↻ לחדר גדול יותר, סובבו את הטלפון
                </span>
              </p>
              {phase === 'door' ? (
                <p class="h">{ROOM_HE[room]}</p>
              ) : (
                <h1 id="tour-title" tabIndex={-1} ref={title}>
                  {ROOM_HE[room]}
                  <span class="sr-only"> · {HOUSE_HE[house]}</span>
                </h1>
              )}
              {/* MOCK4, temporary, for the owner: how many products the room sells; MOCK5: the room's, every frame of it,
                  a product once (in the frame where it is biggest) */}
              <span class="tour-sale" data-temp="" {...(inRoom && wm ? {} : { hidden: true })}>
                {count.total} מוצרים למכירה בחדר
                {heldN ? <span class="tour-held-n"> · {heldN} מהם מחכים לתקן בטיחות</span> : null}
              </span>
              {/* MOCK5: the frames of the room (TEMPORARY: a dissolve between them, never a zoom-in) */}
              {frames.length > 1 ? (
                <div class="tour-frames segmented" role="group" aria-label="נקודת מבט בחדר" {...(inRoom && wm ? {} : { hidden: true })}>
                  {frames.map((f) => (
                    <button
                      key={f}
                      type="button"
                      data-frame={f}
                      aria-pressed={room === f}
                      disabled={busy || !!open}
                      onClick={() => void (room === f ? undefined : goRoom(f, true))}
                    >
                      {ROOMS[f].frame_he ?? ROOMS[f].frame}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
          {chrome ? <BandChrome c={chrome} /> : null}

          {/* the window: one 16:9 frame in every phase. On it, the products' marks and nothing else. */}
          <div class="tour-win" ref={win} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}>
            <canvas
              ref={canvas}
              class="room-canvas"
              // eslint-disable-next-line jsx-a11y/no-interactive-element-to-noninteractive-role
              role="img"
              aria-label={
                phase === 'door'
                  ? 'דלת הכניסה של הבית המודרני החם: דלת אגוז בקיר אבן בהיר, מנורת קיר, ואדנית עם לבנדר.'
                  : wm
                    ? `${PLACE_HE[group]} בבית המודרני החם${tour.frame_he ? ` (${tour.frame_he})` : ''}, עם ${shown.length} פריטים. הרשימה שמתחת לחדר מפרטת אותם.`
                    : 'הסלון בבית הנורדי, בתמונות זמניות.'
              }
            />
            {/* MOCK4: the door (DOOR2: the arrival's first frame, the page's first paint) and the arrival's walk over
                the canvas; the rest on HC for reduced motion; the names on the doors at that rest (ARR-M1) */}
            <picture>
              <source media="(max-width: 900px)" srcset={doorUrl(900)} />
              <img class="tour-door-img" src={doorUrl(1920)} alt="" fetchpriority="high" />
            </picture>
            <video
              ref={video}
              class="tour-video"
              src={walkSrc ? walkUrl(walkSrc) : undefined}
              width={walkSrc?.w ?? 1920}
              height={walkSrc?.h ?? 1080}
              muted
              playsInline
              preload="metadata"
              disablePictureInPicture
              aria-hidden="true"
              tabIndex={-1}
            />
            <img ref={hcImg} class="tour-hc" src={hcUrl()} alt="" loading="lazy" aria-hidden="true" />
            <div class="tour-doors" ref={walkLabels} aria-hidden="true">
              <svg viewBox="0 0 1 1" preserveAspectRatio="none" focusable="false">
                {arrival.labels.map((l) => (
                  <line key={l.id} x1="0" y1="0" x2="0" y2="0" />
                ))}
              </svg>
              {arrival.labels.map((l) => (
                <span key={l.id} class="tour-door-name">
                  {l.name_he}
                </span>
              ))}
            </div>
            {chrome ? <WinChrome c={chrome} replay={`${room}:${phase}`} /> : null}
            <div class="tour-rings" aria-hidden="true" key={`rings-${room}`}>
              {shown.flatMap((s) =>
                s.anchors.map((_, i) => (
                  <span
                    key={`${s.id}:${i}`}
                    class="tour-ring"
                    ref={(el) => {
                      if (el) rings.current.set(`${s.id}:${i}`, el);
                      else rings.current.delete(`${s.id}:${i}`);
                    }}
                  >
                    <i />
                  </span>
                )),
              )}
              {shown
                .filter((s) => s.options.some((o) => o.dims_he))
                .map((s) => (
                  <span
                    key={s.id}
                    class="tour-dim"
                    ref={(el) => {
                      if (el) dimEls.current.set(s.id, el);
                      else dimEls.current.delete(s.id);
                    }}
                  >
                    <b>{optionOf(s, sel).dims_he}</b>
                  </span>
                ))}
            </div>
            {/* the marks: buttons on a wide screen (and when the strip is switched off); decoration beside the strip */}
            <div
              class="hotspots tour-spots"
              role="group"
              aria-label="פריטים בחדר"
              hidden={phase === 'door' || !wm || !!fixture}
              {...(strip ? off : {})}
              key={`spots-${room}`}
            >
              {shown.map((s, i) => {
                const o = optionOf(s, sel);
                const price = priceHe(s, o);
                return (
                  <button
                    key={s.id}
                    type="button"
                    class="tour-spot"
                    data-slot={s.id}
                    data-n={dz ? dz2(i + 1) : undefined}
                    ref={(el) => {
                      if (el) spots.current.set(s.id, el);
                      else spots.current.delete(s.id);
                    }}
                    style={dz ? { left: 0, top: 0, '--n': String(i) } : { left: 0, top: 0 }}
                    tabIndex={strip ? -1 : undefined}
                    aria-label={`${s.name_he}: ${nameHe(s, o)}${price ? `, ${price}` : ''}. ${s.options.length > 1 ? `פתיחת ${s.options.length} גרסאות` : s.closeup === false ? 'פרטים' : 'תקריב'}`}
                    disabled={busy || !!open}
                    onClick={(ev) => void openSlot(s, ev.currentTarget)}
                  >
                    <span class="mark" aria-hidden="true" />
                    <span class="tag" aria-hidden="true">
                      {dz ? <span class="dz-i">{dz2(i + 1)}</span> : null}
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
                hidden={tour.zoom === false}
                onClick={() => void zoomTo(live.current.zoomed ? 1 : ZOOM.step)}
              >
                <IconZoom out={zoomed} />
              </button>
            </div>
            <div class="tour-cell">
              {/* the role is said outright: a list without markers loses it in Safari's screen reader */}
              {/* eslint-disable-next-line jsx-a11y/no-redundant-roles */}
              <ul class="tour-strip" role="list" aria-label="פריטים בחדר" {...(listOn ? {} : off)} key={`strip-${room}`}>
                {shown.map((s, i) => {
                  const o = optionOf(s, sel);
                  const price = priceHe(s, o);
                  return (
                    <li key={s.id}>
                      <button
                        type="button"
                        class="tour-tile"
                        data-slot={s.id}
                        data-n={dz ? dz2(i + 1) : undefined}
                        ref={(el) => {
                          if (el) tiles.current.set(s.id, el);
                          else tiles.current.delete(s.id);
                        }}
                        aria-label={`${s.name_he}: ${nameHe(s, o)}${price ? `, ${price}` : ''}. ${s.options.length > 1 ? `פתיחת ${s.options.length} גרסאות` : s.closeup === false ? 'פרטים' : 'תקריב'}`}
                        disabled={busy || !!open}
                        // the touch itself answers in the room: one ring on the product's mark ties the list to the picture
                        onPointerDown={() => !live.current.busy && ui.ring(s, 'tile')}
                        onClick={(ev) => void openSlot(s, ev.currentTarget)}
                      >
                        <span class="pic">
                          <CardPic o={o} size={72} />
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
                  היכנסו
                </button>
                {/* MOCK2: the room is made ready before anything moves; the quiet line says so while it is (FB1) */}
                <span class="tour-temp" role="status">
                  {ready && !warm ? 'מכינים את החדר…' : ''}
                </span>
              </div>
              {/* MOCK4 (route ch. 11.1): the first arrival has its labels and "דלג", and no other button */}
              <div class="tour-walk-act" ref={walkAct} {...off}>
                {/* MOCK8 (FB19): the walk goes on by a scroll, a swipe or ↓; "המשך" is the same push, for every hand */}
                <span class="tour-walk-hint" aria-hidden="true">
                  גללו כדי להמשיך
                </span>
                <button type="button" class="btn btn-ghost" id="tour-walk-next" onClick={() => walkPush(1, true)}>
                  המשך
                </button>
                <button type="button" class="btn btn-ghost" id="tour-skip" onClick={skipWalk}>
                  דלג
                </button>
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
              <PlanIcon at={phase === 'door' ? 'entry' : AT[group]} />
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
            {dz === 'b' ? <PlanBig at={phase === 'door' ? 'entry' : AT[group]} /> : null}
            <nav class="tour-rooms" aria-label="חדרים">
              <h2>חדרים</h2>
              <div>
                {rooms.map((r, i) => (
                  <button
                    key={r.name}
                    type="button"
                    id={r.id}
                    data-n={dz ? dz2(i) : undefined}
                    class={r.go ? 'tour-room' : undefined}
                    aria-current={r.here ? 'true' : undefined}
                    aria-disabled={r.go ? undefined : 'true'}
                    onClick={r.go}
                  >
                    {r.at === 'entry' ? <IconDoor /> : <PlanIcon at={r.at} />}
                    <span>{r.name}</span>
                    {r.n != null ? <small class="dz-n">{r.n} מוצרים</small> : null}
                    {r.go ? null : <small>בקרוב</small>}
                  </button>
                ))}
              </div>
            </nav>
            {/* MOCK7: no style change in the living room M0-W (the Nordic house is the old M0's camera) */}
            {tour.styles === false ? null : (
              <div class="tour-style" role="group" aria-label="סגנון">
                <h2>סגנון</h2>
                <div class="segmented">
                  {(
                    [
                      [NORDIC, NORDIC_NAME_HE],
                      [WM, tour.name_he],
                    ] as const
                  ).map(([id, name]) => (
                    <button key={id} type="button" data-house={id} aria-pressed={house === id} disabled={!inRoom || !living} onClick={() => void switchTo(id)}>
                      {name}
                    </button>
                  ))}
                </div>
              </div>
            )}
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
              <button type="button" class="btn btn-ghost" id="tour-replay" disabled={!inRoom || !wm || !living || !!open} onClick={() => void replay()}>
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
              onChoose={(pos) => close(pos)}
              onCancel={() => close(null)}
              arc={wheelArc(lay, winSize, winSize.vh, cfg.frame === 'fill')}
              inline
              chooseLabel={phone ? 'בחירה' : undefined}
              closeLabel="סגירת התקריב"
            />
          ) : null}
          {/* MOCK6: the fixture of the wheel of many options (a demo: ten numbered swatches, nothing in the room changes) */}
          {fixture && !open ? (
            <div
              class="tour-fixture"
              ref={(el) => {
                const p = el?.querySelector('.picker');
                if (p && !p.hasAttribute('data-in')) requestAnimationFrame(() => p.setAttribute('data-in', ''));
              }}
            >
              <fixture.W
                house={fixture.mod.fixtureHouse()}
                slot={fixture.mod.fixtureSlot()}
                roomId={tour.room}
                initial={1}
                onPreview={fixture.load}
                onChoose={(pos) => {
                  window.__hdWheelFixture!.chosen = pos;
                  setFixture(null);
                }}
                onCancel={() => {
                  window.__hdWheelFixture!.cancelled = true;
                  setFixture(null);
                }}
                inline
                chooseLabel={phone ? 'בחירה' : undefined}
                closeLabel="סגירת ההדגמה"
              />
            </div>
          ) : null}
        </div>
      </section>
      <section class="wrap page tour-list" aria-labelledby="tour-items">
        <div class="room-intro">
          <h2 id="tour-items" tabIndex={-1}>
            מה יש בחדר
          </h2>
        </div>
        <ul class="slot-list" key={`list-${room}`}>
          {shown.map((s) => {
            const o = optionOf(s, sel);
            return (
              <li key={s.id} class="card slot-item">
                <CardPic o={o} cls="thumb" size={64} />
                <div class="meta">
                  <strong>{s.name_he}</strong>
                  <span class="small">{o.name_he ?? <span class="muted">{s.sale ? s.sale.label_he : NOT_FOR_SALE_HE}</span>}</span>
                  <span class="row">
                    {s.sale ? (
                      o.name_he ? (
                        <span class="small muted">{s.sale.label_he}</span>
                      ) : null
                    ) : o.price_agorot && o.available ? (
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
/** FB20: the wheel of the tour for any number of options (3 to 12): the 3D ring */
const wheelFor = (): Promise<typeof WheelComponent> => (wheelChunk ??= import('../components/RingWheel').then((x) => x.RingWheel));
/** MOCK6: the fixture of the wheel of many options and its wheel; never in the Artifact (the build drops the import) */
const loadFixture = __ARTIFACT__ ? null : () => Promise.all([wheelFor(), import('./fixture-wheel')]);
