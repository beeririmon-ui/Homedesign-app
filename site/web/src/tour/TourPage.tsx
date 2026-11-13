/**
 * MOCK1 (2026-11-12): the wow-tour mock-up, behind HD_PUBLIC=0 (rules TOUR1, TOUR2, MOCK1; the designer's brief
 * docs/proposals/wow-tour-experience-2026-11-12.md). The page opens at the door (temporary, in code): a portal with the
 * real empty living room of the warm-modern house in it. "היכנסו לסלון" grows the portal into the room, the products are
 * revealed (three concepts, switchable), a product opens its close-up and the wheel, and the house changes to the Nordic
 * one and back. The engine and the effects are a chunk of their own (./stage), loaded after the door is painted.
 */
import { useEffect, useRef, useState } from 'preact/hooks';
import type { CatalogSlot } from '@hd/shared';
import { formatIls } from '@hd/shared/money';
import { shopPath } from '@hd/shared/product-url';
import '../styles/tour.css';
import { defaultCam, frameToScreen, screenToFrame } from '../engine/camera';
import { product } from '../catalog';
import type { House } from '../house';
import { mediaUrl } from '../media';
import { prefersReducedMotion, timeScale } from '../motion';
import { announce } from '../state/ui';
import { NOT_FOR_SALE_HE } from '../set-copy';
import { IconDoor, IconLeft, IconRight } from '../components/Icons';
import { Price } from '../components/Media';
import type { VariantWheel as WheelComponent } from '../components/VariantWheel';
import { NORDIC, NORDIC_NAME_HE, WM, cardUrl, tour, type HouseId, type TourOption, type TourSlot } from './data';
import type { TourEngine } from './engine';
import { metrics, report, statLine } from './metrics';
import type { Reveal, Style, Swap, Ui } from './fx';

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
type Cfg = { fx: Reveal; sw: Swap; st: Style; way: 'empty' | 'full'; skip: boolean };
const DEFAULTS: Cfg = { fx: 'b', sw: 's1', st: 'y1', way: 'empty', skip: false };
const pick = <T extends string>(v: string | null, of: readonly T[], d: T): T => (of.includes(v as T) ? (v as T) : d);
function readCfg(): Cfg {
  const q = new URLSearchParams(location.search);
  return {
    fx: pick(q.get('fx'), ['a', 'b', 'c'] as const, DEFAULTS.fx),
    sw: pick(q.get('sw'), ['s1', 's2', 's3'] as const, DEFAULTS.sw),
    st: pick(q.get('st'), ['y1', 'y2'] as const, DEFAULTS.st),
    way: pick(q.get('way'), ['empty', 'full'] as const, DEFAULTS.way),
    skip: q.get('skip') === '1',
  };
}

/** the portal on the wall, in the stage's CSS px (tour.css holds the same numbers for the first paint) */
export function doorRect(w: number, h: number): { cx: number; cy: number; hw: number; hh: number; r: number } {
  const portrait = w / h < 1.1;
  // a wide screen: the opening on the left third (the designer's H0: the living room through it, the window's light),
  // the words beside it; a phone: the opening in the middle, the words above and under it
  const ph = h * (portrait ? 0.54 : 0.74);
  const pw = Math.min(w * (portrait ? 0.66 : 0.36), ph * (portrait ? 0.62 : 0.7));
  return { cx: w * (portrait ? 0.5 : 0.31), cy: h * (portrait ? 0.42 : 0.47), hw: pw / 2, hh: ph / 2, r: Math.min(pw * 0.14, 44) };
}

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

export function TourPage() {
  const stage = useRef<HTMLElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const engine = useRef<TourEngine | null>(null);
  const mod = useRef<Stage | null>(null);
  const starting = useRef<Promise<TourEngine | null> | null>(null);
  const spots = useRef(new Map<string, HTMLButtonElement>());
  const rings = useRef(new Map<string, HTMLSpanElement>());
  /** MOCK2: one Animation per ring, played again rather than built again */
  const anims = useRef(new Map<HTMLElement, { a: Animation; flat: number; ms: number }>());
  /** MOCK2: a phone, where the labels over the room are not shown (tour.css) */
  const narrow = useRef(typeof matchMedia === 'function' ? matchMedia('(max-width: 700px)') : null);
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
  const [open, setOpen] = useState<{ slot: TourSlot; before: number } | null>(null);
  const [Wheel, setWheel] = useState<typeof WheelComponent | null>(null);
  const countEl = useRef<HTMLParagraphElement>(null);
  const [canPan, setCanPan] = useState(false);
  const [stat, setStat] = useState('');
  // reduced motion: the door looks where the room rests (the wall only fades); known on the client only
  const [doorCu, setDoorCu] = useState(DOOR_CU);
  // what the engine's callbacks and the queued presses read (they outlive a render)
  const live = useRef({ phase, busy, house, cfg, sel, open });
  live.current = { phase, busy, house, cfg, sel, open };
  const queued = useRef<(() => void) | null>(null);
  const hint = useRef(0);
  const idleLoad = useRef(0);
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
    // a press made while something moved is done when it ends (the designer's order)
    if (!b && queued.current) {
      const fn = queued.current;
      queued.current = null;
      fn();
    }
  };
  const setCfg = (c: Partial<Cfg>) => {
    live.current.cfg = { ...live.current.cfg, ...c };
    setCfgState(live.current.cfg);
  };
  useEffect(() => {
    live.current.house = house;
    tell();
  }, [house]);

  // ---------- the marks over the room (DOM, placed when the camera lands) ----------
  /**
   * MOCK2 (FB1): this runs when the camera lands, on a pan, and on a resize — never on the frames of a move. It writes
   * a transform for every mark and measures a label, and doing that inside an animation is a style recalculation and a
   * forced layout in the middle of the frame. The marks are invisible while the camera travels anyway.
   */
  function place() {
    const st = stage.current;
    const c = canvas.current;
    if (!st || !c) return;
    const e = engine.current;
    const vp = e?.vp ?? metrics.dom(() => ({ w: Math.max(1, c.clientWidth), h: Math.max(1, c.clientHeight) }));
    const cam = e?.cam ?? defaultCam(vp, tour.aspect, tour.mobile_center_u);
    const d = doorRect(vp.w, vp.h);
    st.style.setProperty('--tk', String(timeScale()));
    for (const [k, v] of Object.entries({ '--dx': d.cx, '--dy': d.cy, '--dw': d.hw * 2, '--dh': d.hh * 2, '--dr': d.r }))
      st.style.setProperty(k, `${v.toFixed(1)}px`);
    if (e && live.current.phase === 'door' && !live.current.busy) {
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
    setCanPan(vp.w < vp.h * tour.aspect - 1);
    if (cam.z < 1.001) spread(vp.w);
  }
  /** the labels never cover one another: a label that would is moved up or down a row (wide screens; a phone has none) */
  const tagW = useRef(new Map<string, number>());
  function spread(vw: number) {
    if (vw <= 700) return;
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
  const ui: Ui = {
    ring(s, kind) {
      if (prefersReducedMotion()) return;
      const [size, ms] = kind === 'burst' ? [132, 620] : kind === 'small' ? [72, 480] : [56, 420];
      s.anchors.forEach((_, i) => {
        const el = rings.current.get(`${s.id}:${i}`)?.firstElementChild as HTMLElement | null;
        if (!el) return;
        // MOCK2: one custom property for the size (the CSS does the rest) and one Animation per ring, played again
        // instead of built again — a ring fires inside the reveal, on a product's own frame
        el.style.setProperty('--ring', `${size}px`);
        const flat = kind === 'touch' ? 0.34 : 1;
        const was = anims.current.get(el);
        if (was && was.flat === flat && was.ms === ms) {
          was.a.currentTime = 0;
          was.a.play();
          return;
        }
        was?.a.cancel();
        const a = el.animate(
          [
            { opacity: 0.95, transform: `scale(0.08) scaleY(${flat})` },
            { opacity: 0, transform: `scale(1) scaleY(${flat})` },
          ],
          { duration: ms * k(), easing: 'cubic-bezier(0.16, 1, 0.3, 1)' },
        );
        anims.current.set(el, { a, flat, ms });
      });
    },
    label(s, on) {
      // MOCK2: on a phone the labels are not shown at all (tour.css, the designer's rule), so the attribute is not
      // written either — thirteen style recalculations inside the reveal, for something invisible
      if (narrow.current?.matches) return;
      for (const el of s ? [spots.current.get(s.id)] : spots.current.values()) el?.toggleAttribute('data-label', on);
      if (s && on) spots.current.get(s.id)?.setAttribute('data-on', '');
    },
    spots(on) {
      for (const el of spots.current.values()) el.toggleAttribute('data-on', on);
    },
    /**
     * MOCK2: the counter is written into the page, not through the component's state. It changes once per product
     * while the room fills, and a state change there re-rendered the whole page — thirteen times, inside the effect
     * (that was most of the script time of the depth scan: FB1, smoothness).
     */
    count(n, final = false) {
      const el = countEl.current;
      if (!el) return;
      el.hidden = n === null;
      if (n === null) return;
      const [a, mid, b, tail] = [...el.children] as HTMLElement[];
      if (final) {
        a!.textContent = String(n);
        mid!.textContent = ' פריטים · ';
        b!.textContent = `${Math.round(tour.cover * 100)}%`;
        b!.removeAttribute('dir');
        tail!.textContent = ' מהחדר';
      } else {
        a!.textContent = '';
        mid!.textContent = 'פריטים ';
        b!.textContent = `${n}/${tour.slots.length}`;
        b!.setAttribute('dir', 'ltr');
        tail!.textContent = '';
      }
    },
    dims(on) {
      for (const el of dimEls.current.values())
        if (on) el.animate([{ opacity: 0 }, { opacity: 1, offset: 0.2 }, { opacity: 1, offset: 0.8 }, { opacity: 0 }], { duration: 1300 * k() });
    },
  };

  // ---------- the engine ----------
  function ensure(): Promise<TourEngine | null> {
    return (starting.current ??= import('./stage').then(async (m) => {
      const c = canvas.current;
      if (!c) return null;
      mod.current = m;
      const e = m.TourEngine.create({ canvas: c, reduceMotion: prefersReducedMotion(), onCamera: place });
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
        e.background();
      } else {
        // MOCK2 (FB1): the door waits until the room can be animated — every layer of it fetched, decoded, uploaded
        // and composed once, every program compiled. Until then the button says so and nothing moves: even the slow
        // push of the door starts afterwards, so the room's own decodes never land inside it.
        void e.whenWarm().then(() => {
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
    if (prefersReducedMotion()) setDoorCu(tour.mobile_center_u);
    place();
    const ro = new ResizeObserver(() => !engine.current && place());
    if (canvas.current) ro.observe(canvas.current);
    // after the door is painted: the engine's chunk, the empty room, then the products behind it
    let idle = 0;
    const later = () => (idle = window.setTimeout(() => void ensure(), 60));
    if (document.readyState === 'complete') later();
    else addEventListener('load', later, { once: true });
    return () => {
      ro.disconnect();
      removeEventListener('load', later);
      clearTimeout(idle);
      clearTimeout(hint.current);
      clearTimeout(idleLoad.current);
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
  function atRest(e: TourEngine) {
    e.background();
    if (e.house !== WM) return;
    ui.spots(true);
    void e.wait(800).then(() => !live.current.busy && ui.label(null, false));
    clearTimeout(hint.current);
    hint.current = window.setTimeout(() => {
      const hero = tour.slots.find((s) => s.hero);
      if (hero && !live.current.busy && !live.current.open && live.current.phase === 'room') ui.ring(hero, 'burst');
    }, 6000);
  }

  // ---------- the beats ----------
  const goIn = () =>
    live.current.phase === 'door' &&
    beat(async (e, m) => {
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
    });
  const goOut = () =>
    live.current.phase === 'room' &&
    !live.current.open &&
    beat(async (e, m) => {
      if (e.house !== WM) await m.style(e, ui, WM, 'y2', 'b');
      setHouse(WM);
      if (live.current.cfg.way === 'empty') await m.collect(e, ui);
      else {
        ui.spots(false);
        ui.label(null, false);
        ui.count(null);
      }
      setPhase('entering');
      await m.leave(e, doorRect(e.vp.w, e.vp.h));
      setPhase('door');
      m.doorPush(e);
    }, goOut);
  const replay = (fx?: Reveal) =>
    live.current.phase === 'room' &&
    live.current.house === WM &&
    !live.current.open &&
    beat(
      async (e, m) => {
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
        await m.style(e, ui, to, live.current.cfg.st, live.current.cfg.fx);
        setHouse(to);
        atRest(e);
        announce(`הסלון, ${to === WM ? tour.name_he : NORDIC_NAME_HE}`);
      },
      () => switchTo(to),
    );

  // ---------- the close-up and the wheel ----------
  const opener = useRef<HTMLElement | null>(null);
  const openSlot = (s: TourSlot) =>
    live.current.phase === 'room' &&
    live.current.house === WM &&
    !live.current.open &&
    beat(async (e) => {
      opener.current = document.activeElement as HTMLElement | null;
      const wheel = (wheelChunk ??= import('../components/VariantWheel').then((x) => x.VariantWheel));
      ui.label(null, false);
      stage.current?.classList.add('zoomed');
      const b = optionOf(s, live.current.sel).box;
      // the product fills about 60% of the view (the skeleton); the lower part of the screen is the wheel's
      const g = [(b[1] - b[0]) / 3, (b[3] - b[2]) / 3];
      const box = [Math.max(0, b[0] - g[0]!), Math.min(1, b[1] + g[0]!), Math.max(0, b[2] - g[1]!), Math.min(1, b[3] + g[1]!)] as [
        number,
        number,
        number,
        number,
      ];
      let shown = false;
      await e.moveCam('zoom-in', e.camFor(box, e.vp.h > 520 ? 0.52 : 0.46), 1000, (ease, t) => {
        e.d.vig = 0.1 * ease;
        e.d.vigBox = s.rect;
        // the wheel rises 0.15 s before the camera lands
        if (t >= 0.85 && !shown) {
          shown = true;
          void wheel.then((W) => {
            setWheel(() => W);
            setOpen({ slot: s, before: live.current.sel[s.id] ?? 1 });
          });
        }
      });
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
  async function close(chosen: boolean) {
    const o = live.current.open;
    const e = engine.current;
    if (!o || !e) return;
    setOpen(null);
    live.current.open = null;
    await beat(async () => {
      if (!chosen) preview(o.slot, o.before);
      while (wanted.current !== null) await new Promise((r) => setTimeout(r, 30));
      await e.moveCam('zoom-out', e.rest, 1000, (ease) => (e.d.vig = 0.1 * (1 - ease)));
      stage.current?.classList.remove('zoomed');
      atRest(e);
      if (chosen) announce(`${o.slot.name_he}: ${nameHe(o.slot, optionOf(o.slot, e.selection))} מוצג בחדר`);
    });
    (spots.current.get(o.slot.id) ?? opener.current)?.focus({ preventScroll: true });
  }

  // ---------- pointer: a tap on a product opens it; a drag pans a narrow screen ----------
  const drag = useRef<{ x: number; id: number; moved: number; onControl: boolean } | null>(null);
  function onPointerDown(ev: PointerEvent) {
    clearTimeout(hint.current);
    drag.current = { x: ev.clientX, id: ev.pointerId, moved: 0, onControl: !!(ev.target as Element).closest('button, a, details, input, label') };
  }
  function onPointerMove(ev: PointerEvent) {
    const p = drag.current;
    const e = engine.current;
    if (!p || p.id !== ev.pointerId || p.onControl || !e || live.current.phase !== 'room' || live.current.busy || live.current.open) return;
    const dx = ev.clientX - p.x;
    p.x = ev.clientX;
    p.moved += Math.abs(dx);
    if (p.moved > 4) e.panBy(dx);
  }
  function onPointerUp(ev: PointerEvent) {
    const p = drag.current;
    drag.current = null;
    const e = engine.current;
    const c = canvas.current;
    if (!p || p.onControl || p.moved > 4 || !e || !c || live.current.phase !== 'room' || live.current.busy || live.current.open) return;
    const r = metrics.dom(() => c.getBoundingClientRect());
    const { u, v } = screenToFrame(ev.clientX - r.left, ev.clientY - r.top, e.cam, e.vp, tour.aspect);
    const hit = e.slotAt(u, v);
    if (hit) void openSlot(hit);
  }

  const inRoom = phase === 'room';
  const wm = house === WM;
  // MOCK2: the first paint is the width the engine will compose at on this screen (data.ts widthFor: a phone takes
  // `lo`), so the picture the browser already holds is the one the room is built from, not a second download
  const WIDE = '(min-width: 901px)';
  const poster = (w: number, ext: 'avif' | 'webp') => mediaUrl(tour.base.src, w, ext);
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
  return (
    <>
      <section
        class={`stage tour${noGl ? ' tour-nogl' : ''}`}
        ref={stage}
        data-phase={phase}
        data-house={house}
        data-ready={ready ? '' : undefined}
        style={{ '--cu': String(phase === 'door' ? doorCu : tour.mobile_center_u) }}
        aria-labelledby="tour-title"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
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
                : 'הסלון בבית הנורדי, בשכבות זמניות.'
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
        <div class="hotspots tour-spots" role="group" aria-label="פריטים בחדר" hidden={phase === 'door' || !wm}>
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
                aria-label={`${s.name_he}: ${nameHe(s, o)}${price ? `, ${price}` : ''}. ${s.options.length > 1 ? `פתיחת ${s.options.length} גרסאות` : 'תקריב'}`}
                disabled={busy || !!open}
                onClick={() => void openSlot(s)}
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

        {/* the door's own words (temporary): the house, the one button, and the rooms that are not built yet */}
        <div class="tour-door" {...(phase === 'door' ? {} : { inert: true, 'aria-hidden': 'true' })}>
          <div class="tour-door-head">
            <p class="eyebrow">סיור בבית</p>
            <h1 id={phase === 'door' ? 'tour-title' : undefined} tabIndex={-1}>
              הבית המודרני החם
            </h1>
          </div>
          <div class="tour-door-act">
            <button type="button" class="btn btn-primary" id="tour-enter" onClick={() => void goIn()} aria-busy={busy || (ready && !warm) ? 'true' : undefined}>
              היכנסו לסלון
            </button>
            {/* MOCK2: the room is made ready before anything moves; the quiet line says so while it is (FB1) */}
            <span class="tour-temp" role="status">
              {ready && !warm ? 'מכינים את החדר…' : 'הדלת זמנית'}
            </span>
          </div>
        </div>

        {phase !== 'door' ? (
          <h1 id="tour-title" class="glass stage-temp-note" tabIndex={-1} ref={title}>
            סלון · {wm ? tour.name_he : NORDIC_NAME_HE}
            {wm ? null : <span class="stage-status">שכבות זמניות</span>}
          </h1>
        ) : null}
        {/* MOCK2: always in the page, filled by ui.count through the DOM (no render inside an effect) */}
        <p class="glass tour-count" aria-hidden="true" ref={countEl} hidden>
          <span class="num" />
          <span />
          <span class="num" />
          <span />
        </p>
        {noGl ? (
          <p class="glass tour-nogl-note" role="status">
            הסיור צריך דפדפן עם WebGL2. <a href="/rooms/living-room/?style=warm-modern">לסלון בכלי העיצוב</a>
          </p>
        ) : null}

        <div class="stage-ui">
          {inRoom ? (
            <div class="glass segmented" role="group" aria-label="הבית">
              {(
                [
                  [NORDIC, NORDIC_NAME_HE],
                  [WM, tour.name_he],
                ] as const
              ).map(([id, name]) => (
                <button key={id} type="button" data-house={id} aria-pressed={house === id} onClick={() => void switchTo(id)}>
                  {name}
                </button>
              ))}
            </div>
          ) : null}
          {canPan && inRoom ? (
            <div class="stage-actions">
              <button type="button" class="glass glass-btn" onClick={() => engine.current?.panBy(120)} aria-label="הזזת המבט ימינה">
                <IconRight />
              </button>
              <button type="button" class="glass glass-btn" onClick={() => engine.current?.panBy(-120)} aria-label="הזזת המבט שמאלה">
                <IconLeft />
              </button>
            </div>
          ) : null}
          {/* a button per room (TOUR1): the door and the living room are here; a room that is not built yet says so */}
          <nav class="glass segmented tour-rooms" aria-label="חדרים">
            <button type="button" id="tour-out" aria-current={phase === 'door' ? 'true' : undefined} onClick={() => void goOut()}>
              <IconDoor />
              <span>כניסה</span>
            </button>
            <button type="button" id="tour-living" aria-current={inRoom ? 'true' : undefined} onClick={() => void goIn()}>
              סלון
            </button>
            {['פינת אוכל', 'חדר שינה'].map((name) => (
              <button key={name} type="button" aria-disabled="true">
                {name} <small>בקרוב</small>
              </button>
            ))}
          </nav>
        </div>

        {/* the mock-up's own switches (temporary): the owner chooses between the concepts while they move */}
        <details class="glass tour-panel">
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

        {open && Wheel ? (
          <Wheel
            house={wheelHouse(open.slot)}
            slot={wheelSlot(open.slot)}
            roomId={tour.room}
            initial={sel[open.slot.id] ?? 1}
            onPreview={(pos) => preview(open.slot, pos)}
            onChoose={() => void close(true)}
            onCancel={() => void close(false)}
          />
        ) : null}
      </section>
      <section class="wrap page" aria-labelledby="tour-items">
        <div class="room-intro">
          <h2 id="tour-items">מה יש בחדר</h2>
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
