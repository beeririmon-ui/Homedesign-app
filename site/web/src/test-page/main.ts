/**
 * The Nordic test page in the magazine language (briefs/site-test-page-2026-11-03.md). Static HTML first (the cover and
 * its LQIP are in the page before this runs); this module adds the designed loading (art direction §8), the running head,
 * the marks and the wall label (§6.4), focus mode (focus spec §2–§4, display-only on the temporary frame), the paper
 * transition (§6.3), the P-D pan player (the frame player after the fixes of 2026-11-03: no push, a decode window), and
 * the states demo (§6.8). Every duration and curve is a token of §7.1 (CSS) or the manifest's walk easing (JS).
 * `window.__mag` exposes the timeline for the evidence tool (tools/screens-test-page.ts).
 */
import './fonts.css';
import './magazine.css';
import { Loader } from '../engine/loader';
import { FrameWindow, SequencePlayer, tween } from '../engine/sequence';
import { prefersReducedMotion } from '../motion';
import { supportsAvif } from '../media';

type Credit = { id: string; name_he: string; detail_he: string; price_he: string; unavailable: boolean; thumb: string | null; href: string | null };
type Hotspot = { slot: string; name_he: string; box: [number, number, number, number]; u: number; v: number; credit: Credit | null; variants: Credit[] };
type FrameData = { aspect: number; u0: number; v0: number; srcset: string[]; window: { u0: number; u1: number }; hotspots: Hotspot[]; room?: string };
type PanData = {
  src: string;
  frames: number;
  fps: number;
  play_s: number;
  easing: { accel: number; land: number };
  variants: Record<string, { w: number; h: number; avif: number; webp: number }>;
};
type Data = { frames: Record<string, FrameData>; pan: PanData; focus_phone_closeup: string };

const data = JSON.parse(document.getElementById('mag-data')!.textContent ?? '{}') as Data;
if (new URLSearchParams(location.search).has('notes')) document.body.dataset.notes = '';
const reduce = prefersReducedMotion();
const root = document.body;
const phone = () => innerWidth < 720;
const ms = (name: string, fallback: number): number => {
  const v = getComputedStyle(root).getPropertyValue(name).trim();
  const n = parseFloat(v);
  return Number.isFinite(n) ? (v.endsWith('ms') ? n : n * 1000) : fallback;
};
const wait = (t: number) => new Promise<void>((r) => setTimeout(r, t));
const nextFrame = () => new Promise<void>((r) => requestAnimationFrame(() => r()));

// ---------- the timeline for the evidence tool ----------
const events: { t: number; name: string; detail?: unknown }[] = [];
const mark = (name: string, detail?: unknown) => events.push({ t: performance.now(), name, detail });
const live = document.getElementById('mag-live')!;
const announce = (text: string) => {
  live.textContent = '';
  void live.offsetHeight;
  live.textContent = text;
};

// ---------- the running head: on the stage transparent, on paper with a hairline ----------
const head = document.getElementById('mag-head')!;
const run = document.getElementById('mag-run')!;
let headHidden = false;
const sections = [...document.querySelectorAll<HTMLElement>('[data-head]')];
const io = new IntersectionObserver(
  (entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const el = e.target as HTMLElement;
      run.textContent = el.dataset.head ?? '';
      if (!headHidden) head.dataset.on = el.classList.contains('mag-paper') ? 'paper' : 'stage';
      head.dataset.frame = el.querySelector<HTMLElement>('.mag-stage[data-frame]')?.dataset.frame ?? '';
      if (el.classList.contains('mag-spread')) firstEntry(el);
    }
  },
  { threshold: 0.55 },
);
for (const s of sections) io.observe(s);

// ---------- the cover (§8.1): LQIP → the image develops → the brand → the title → the invitation ----------
const cover = document.getElementById('cover')!;
const coverFrame = cover.querySelector<HTMLElement>('.mag-frame')!;
const coverImg = cover.querySelector<HTMLImageElement>('.mag-pic img')!;
function developed(frame: HTMLElement, img: HTMLImageElement, name: string): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      frame.classList.add('is-developed');
      mark(name);
      resolve();
    };
    if (img.complete && img.naturalWidth) done();
    else {
      img.addEventListener('load', done, { once: true });
      img.addEventListener('error', done, { once: true });
    }
  });
}
void (async () => {
  mark('cover:lqip');
  await developed(coverFrame, coverImg, 'cover:developed');
  await Promise.race([document.fonts.ready, wait(800)]);
  mark('cover:fonts');
  await wait(200);
  root.classList.add('is-brand');
  mark('cover:brand');
  await wait(400);
  root.classList.add('is-title');
  mark('cover:title');
  await wait(800);
  root.classList.add('is-invite');
  mark('cover:invite');
})();

// ---------- the paper transition (§6.3): paper 150 ms, hold 200 ms, the room dissolves in over 400 ms ----------
const veil = document.getElementById('mag-veil')!;
let paperBusy = false;
async function paperTo(selector: string): Promise<void> {
  const target = document.querySelector<HTMLElement>(selector);
  if (!target || paperBusy) return;
  paperBusy = true;
  mark('paper:out', selector);
  veil.classList.add('is-in');
  await wait(ms('--d-page-out', 150) + ms('--d-paper-hold', 200));
  target.scrollIntoView({ behavior: 'instant', block: 'start' });
  await nextFrame();
  veil.classList.remove('is-in');
  mark('paper:in', selector);
  await wait(ms('--d-paper-in', 400));
  paperBusy = false;
  const h = target.querySelector<HTMLElement>('h2, h1');
  (h ?? target).setAttribute('tabindex', '-1');
  (h ?? target).focus({ preventScroll: true });
}
function enter(): void {
  mark('enter');
  // the walk T-E0 exists only for the prototype frames: for these frames the art direction's paper transition, never a fake walk
  void paperTo('#room-living-room');
}
document.getElementById('mag-enter')!.addEventListener('click', enter);
const coverInView = () => cover.getBoundingClientRect().bottom > innerHeight * 0.5;
addEventListener(
  'wheel',
  (e) => {
    if (coverInView() && e.deltaY > 8 && !paperBusy) {
      e.preventDefault();
      enter();
    }
  },
  { passive: false },
);
addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && coverInView() && document.activeElement === document.body) enter();
});
let touchY: number | null = null;
cover.addEventListener('touchstart', (e) => (touchY = e.touches[0]?.clientY ?? null), { passive: true });
cover.addEventListener(
  'touchmove',
  (e) => {
    const y = e.touches[0]?.clientY ?? null;
    if (touchY !== null && y !== null && touchY - y > 40) {
      touchY = null;
      enter();
    }
  },
  { passive: true },
);
for (const a of document.querySelectorAll<HTMLAnchorElement>('a.mag-toc-link[data-room]')) {
  a.addEventListener('click', (e) => {
    e.preventDefault();
    void paperTo(`#room-${a.dataset.room}`);
  });
}

// ---------- the stages: the phone window, the marks, the wall label, focus mode ----------
type Stage = {
  el: HTMLElement;
  id: string;
  frame: HTMLElement;
  scroller: HTMLElement;
  img: HTMLImageElement;
  outline: HTMLElement;
  label: HTMLElement;
  strip: HTMLElement;
  close: HTMLButtonElement;
  marks: HTMLButtonElement[];
  d: FrameData;
  idle: ReturnType<typeof setTimeout> | undefined;
  hinted: boolean;
  focus: { slot: string; index: number; before: number } | null;
};
const stages = new Map<string, Stage>();
for (const el of document.querySelectorAll<HTMLElement>('.mag-spread .mag-stage[data-frame]')) {
  const id = el.dataset.frame!;
  const d = data.frames[id];
  if (!d) continue;
  const st: Stage = {
    el,
    id,
    frame: el.querySelector('.mag-frame')!,
    scroller: el.querySelector('.mag-scroller')!,
    img: el.querySelector('.mag-pic img')!,
    outline: el.querySelector('.mag-outline')!,
    label: el.querySelector('.mag-label')!,
    strip: el.querySelector('.mag-strip')!,
    close: el.querySelector('.mag-close')!,
    marks: [...el.querySelectorAll<HTMLButtonElement>('.mag-mark')],
    d,
    idle: undefined,
    hinted: false,
    focus: null,
  };
  stages.set(id, st);
  st.frame.style.setProperty('--aspect', String(d.aspect));
  void developed(st.frame, st.img, `${id}:developed`);
  // the frame's box is exactly the picture's drawn rectangle, so a mark at (u, v) sits on the picture's (u, v):
  //  - the phone: the frame at full height in a horizontal scroller (CSS); the view starts on the frame's window
  //  - desktop up to 2:1: the frame covers the stage like object-fit: cover at the frame's focal point (u0, v0); the
  //    first paint (before this runs) is the same picture through object-fit, so nothing moves
  //  - desktop over 2:1: the frame at full height on paper (CSS)
  const layout = () => {
    if (st.focus) return;
    const fs = st.frame.style;
    if (phone() || st.el.clientWidth / Math.max(1, st.el.clientHeight) >= 2) {
      fs.position = fs.width = fs.height = fs.left = fs.top = '';
      if (phone()) st.scroller.scrollLeft = d.window.u0 * st.frame.offsetWidth;
      keepMarksInView(st, 0, 1);
      return;
    }
    const sw = st.el.clientWidth;
    const sh = st.el.clientHeight;
    const fw = Math.max(sw, sh * d.aspect);
    const fh = fw / d.aspect;
    fs.position = 'absolute';
    fs.width = `${fw}px`;
    fs.height = `${fh}px`;
    fs.left = `${(sw - fw) * d.u0}px`;
    fs.top = `${(sh - fh) * d.v0}px`;
    // the part of the frame the stage shows, less half a target and its ring (29 px) on each side
    const left = (sw - fw) * d.u0;
    keepMarksInView(st, (29 - left) / fw, (sw - 29 - left) / fw);
  };
  layout();
  addEventListener('resize', layout);
  // marks: on pointer movement or a touch, gone 2.5 s after the last movement (ו.4)
  const onMove = () => showMarks(st);
  el.addEventListener('pointermove', onMove);
  el.addEventListener('pointerdown', onMove);
  for (const m of st.marks) {
    const slot = m.dataset.slot!;
    m.addEventListener('pointerenter', () => light(st, slot));
    m.addEventListener('pointerleave', () => light(st, null));
    m.addEventListener('focus', () => light(st, slot));
    m.addEventListener('blur', () => light(st, null));
    m.addEventListener('click', () => void openFocus(id, slot));
  }
  st.close.addEventListener('click', () => void cancelFocus(id));
  // focus mode on the phone: a horizontal swipe browses, a swipe down cancels (focus spec §3.3)
  let sx: number | null = null;
  let sy: number | null = null;
  el.addEventListener(
    'touchstart',
    (e) => {
      sx = e.touches[0]?.clientX ?? null;
      sy = e.touches[0]?.clientY ?? null;
    },
    { passive: true },
  );
  el.addEventListener(
    'touchend',
    (e) => {
      const x = e.changedTouches[0]?.clientX ?? null;
      const y = e.changedTouches[0]?.clientY ?? null;
      if (!st.focus || sx === null || sy === null || x === null || y === null) return;
      const dx = x - sx;
      const dy = y - sy;
      if (dy > 60 && Math.abs(dy) > Math.abs(dx)) void cancelFocus(id);
      else if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) browse(id, dx < 0 ? 1 : -1); // RTL: a swipe to the left brings the next
    },
    { passive: true },
  );
}
/**
 * A mark stays where its whole target and focus ring are on screen (art direction §10.3, §10.16): when the cover crop
 * cuts the side of the frame, a mark near the cut moves inside its own product box; a product of which less than half
 * is on screen gets no mark (the counting rule of the hotspots).
 */
function keepMarksInView(st: Stage, uMin: number, uMax: number): void {
  for (const m of st.marks) {
    const h = hotspotOf(st, m.dataset.slot!);
    if (!h) continue;
    const [x0, x1] = h.box;
    const shown = Math.max(0, Math.min(x1, uMax) - Math.max(x0, uMin)) / Math.max(1e-6, x1 - x0);
    m.hidden = shown < 0.5;
    const u = Math.min(Math.max(h.u, Math.max(x0, uMin)), Math.min(x1, uMax));
    m.style.setProperty('--u', String(u));
  }
}
function showMarks(st: Stage): void {
  if (st.focus) return;
  if (st.el.dataset.marks !== 'on') {
    st.el.dataset.marks = 'on';
    mark(`${st.id}:marks:on`);
  }
  clearTimeout(st.idle);
  st.idle = setTimeout(
    () => {
      st.el.dataset.marks = 'off';
      mark(`${st.id}:marks:off`);
    },
    ms('--t-mark-idle', 2500),
  );
}
function firstEntry(section: HTMLElement): void {
  const st = [...stages.values()].find((s) => section.contains(s.el));
  if (!st || st.hinted) return;
  st.hinted = true;
  prefetchMaster(st);
  // the hint, once per room per visit: the marks appear and go after 1.2 s (§6.4)
  setTimeout(() => {
    if (st.focus) return;
    st.el.dataset.marks = 'on';
    mark(`${st.id}:hint:on`);
    setTimeout(() => {
      if (st.el.dataset.marks === 'on' && !st.idle) {
        st.el.dataset.marks = 'off';
        mark(`${st.id}:hint:off`);
      }
    }, 1200);
  }, 400);
}
/** The largest rendition of the frame, for the focus layers (a camera at ×3 on the 1280 file would show its pixels). */
const masters = new Map<string, HTMLImageElement>();
function masterUrl(st: Stage): string {
  const ext = (st.img.currentSrc || st.img.src).endsWith('.avif') ? 'avif' : 'webp';
  return `${st.d.srcset[st.d.srcset.length - 1]}.${ext}`;
}
function prefetchMaster(st: Stage): void {
  if (masters.has(st.id)) return;
  const img = new Image();
  img.decoding = 'async';
  img.src = masterUrl(st);
  masters.set(st.id, img);
  img.decode().catch(() => undefined); // decoded in the background, after the room is on screen
}
function hotspotOf(st: Stage, slot: string): Hotspot | undefined {
  return st.d.hotspots.find((h) => h.slot === slot);
}
function light(st: Stage, slot: string | null): void {
  const h = slot ? hotspotOf(st, slot) : undefined;
  if (!h || st.focus) {
    st.outline.classList.remove('is-on');
    st.label.classList.remove('is-on');
    return;
  }
  const [x0, x1, y0, y1] = h.box;
  st.outline.style.setProperty('--x0', String(x0));
  st.outline.style.setProperty('--x1', String(x1));
  st.outline.style.setProperty('--y0', String(y0));
  st.outline.style.setProperty('--y1', String(y1));
  st.outline.classList.add('is-on');
  if (phone()) return;
  const c = h.credit;
  st.label.innerHTML = c
    ? `<span class="mag-credit-name"></span><span class="mag-credit-detail"></span>`
    : `<span class="mag-credit-name"></span><span class="mag-credit-detail">ממתינה למוצר</span>`;
  st.label.querySelector('.mag-credit-name')!.textContent = c ? c.name_he : h.name_he;
  if (c) st.label.querySelector('.mag-credit-detail')!.textContent = c.unavailable ? `${c.detail_he} · המלאי אינו זמין כעת` : c.detail_he;
  const fw = st.frame.offsetWidth;
  const fh = st.frame.offsetHeight;
  const fr = st.frame.getBoundingClientRect();
  const sr = st.el.getBoundingClientRect();
  const headH = parseFloat(getComputedStyle(root).getPropertyValue('--head-h')) || 56;
  const x = fr.left - sr.left + h.u * fw;
  const y = Math.max(headH + 8 + 60, fr.top - sr.top + y0 * fh - 12);
  st.label.style.left = `${Math.min(Math.max(x, 180), st.el.clientWidth - 180)}px`;
  st.label.style.top = `${y}px`;
  st.label.classList.add('is-on');
}

// ---------- focus mode (focus spec; display-only on the temporary frame: no close-up render, no alpha layers yet) ----------
function stripHtml(h: Hotspot, index: number): string {
  const c = h.variants[index] ?? h.credit;
  const thumbs = h.variants
    .map(
      (v, i) =>
        `<button type="button" class="mag-thumb" role="radio" aria-checked="${i === index}" aria-label="${v.name_he}, ${v.price_he}" data-i="${i}" tabindex="${i === index ? 0 : -1}">${v.thumb ? `<img src="${v.thumb}" alt="" width="52" height="50" decoding="async" />` : ''}</button>`,
    )
    .join('');
  const buy = !c
    ? ''
    : c.unavailable
      ? `<span class="mag-cap">המלאי אינו זמין כעת · <a class="mag-link" href="#toc">עדכנו אותי כשחוזר</a></span>`
      : `<button type="button" class="mag-link mag-add" style="background:none;border:0;padding:0;font:inherit;cursor:pointer">הוספה לסל</button>`;
  return `<div class="mag-thumbs" role="radiogroup" aria-label="${h.name_he}: הווריאציות">${thumbs || '<span class="mag-cap">אין עדיין וריאציות בעמדה הזו</span>'}</div>
<div class="mag-strip-row"><span class="mag-strip-credit" aria-live="polite"><a class="mag-credit-name mag-credit-link"></a><span class="mag-credit-detail"></span></span>${buy}<button type="button" class="mag-btn mag-btn-primary mag-choose">בחירה</button></div>`;
}
function fillCredit(st: Stage, h: Hotspot, index: number): void {
  const c = h.variants[index] ?? h.credit;
  const name = st.strip.querySelector<HTMLAnchorElement>('.mag-credit-name')!;
  const detail = st.strip.querySelector('.mag-credit-detail')!;
  name.textContent = c ? c.name_he : h.name_he;
  // the name is the link to the product page (§6.5), where the product has one
  if (c?.href) name.href = c.href;
  else name.removeAttribute('href');
  detail.textContent = c ? c.detail_he : 'ממתינה למוצר';
}
async function openFocus(stageId: string, slot: string): Promise<void> {
  const st = stages.get(stageId);
  const h = st ? hotspotOf(st, slot) : undefined;
  if (!st || !h || st.focus) return;
  light(st, null);
  clearTimeout(st.idle);
  st.idle = undefined;
  st.el.dataset.marks = 'off';
  st.focus = { slot, index: 0, before: st.scroller.scrollLeft };
  st.el.dataset.focus = 'approach';
  headHidden = true;
  head.dataset.on = 'hidden';
  mark(`${stageId}:focus:start`, slot);
  // the camera: the product fills about 60% of the free height (skeleton: "zoom targets"); on the phone the cushions
  // close-up (FOC2) can be wider than the window: a reframe, not a zoom (focus spec §4.4)
  const [x0, x1, y0, y1] = h.box;
  const fw = st.frame.offsetWidth;
  const fh = st.frame.offsetHeight;
  const sw = st.el.clientWidth;
  const sh = st.el.clientHeight;
  const bw = (x1 - x0) * fw;
  const bh = (y1 - y0) * fh;
  const free = sh * (phone() ? 0.66 : 0.7);
  const s = Math.min(6.5, Math.max(1, Math.min((0.6 * sw) / bw, (0.6 * free) / bh)));
  const cx = ((x0 + x1) / 2) * fw;
  const cy = ((y0 + y1) / 2) * fh;
  // the frame's own offset in the stage (the cover crop on desktop, the scroll on the phone)
  const ox = st.frame.offsetLeft - st.scroller.scrollLeft;
  const oy = st.frame.offsetTop;
  const tx = sw / 2 - ox - s * cx;
  const ty = sh * 0.42 - oy - s * cy;
  const transform = `translate(${tx.toFixed(2)}px, ${ty.toFixed(2)}px) scale(${s.toFixed(4)})`;
  const approach = ms('--d-approach', 1600);
  // the look (display-only on the temporary frame, focus spec §2): the room uniformly soft (0.5% of the screen width,
  // so the radius is divided by the camera's scale) and a third of a stop darker; the product's box sharp and a quarter
  // stop lifter. Built with the move: on the approach it comes in over the deceleration (CSS, data-look='in').
  //  - the soft room is the picture already on screen (decoded), blurred and dimmed by CSS
  //  - the sharp product is an ellipse around its box, cut from the largest rendition (at ×3 the 1280 file would
  //    show its pixels; an ellipse costs far less to paint than a second full frame). It is the room's own light, not
  //    lifted: without the product's alpha a +1/4 stop lift lights the wall behind it too, a halo the spec forbids
  //    (focus spec §2.5); the lift comes with the final focus layers
  const soft = document.createElement('img');
  soft.className = 'mag-soft';
  soft.alt = '';
  soft.setAttribute('aria-hidden', 'true');
  soft.decoding = 'sync';
  soft.src = st.img.currentSrc || st.img.src;
  const master = masters.get(stageId);
  const sharpSrc = master?.complete && master.naturalWidth ? master.src : soft.src;
  // the pool around the box: 70% of the box on every side, so the box sits inside the (almost) opaque part of the
  // ellipse and the falloff to the soft room is long, a pool of light and not a spot
  const mx = (x1 - x0) * 0.7;
  const my = (y1 - y0) * 0.7;
  const bx0 = Math.max(0, x0 - mx);
  const bx1 = Math.min(1, x1 + mx);
  const by0 = Math.max(0, y0 - my);
  const by1 = Math.min(1, y1 + my);
  const sharp = document.createElement('div');
  sharp.className = 'mag-sharp';
  sharp.setAttribute('aria-hidden', 'true');
  const ss = sharp.style;
  ss.left = `${(bx0 * fw).toFixed(2)}px`;
  ss.top = `${(by0 * fh).toFixed(2)}px`;
  ss.width = `${((bx1 - bx0) * fw).toFixed(2)}px`;
  ss.height = `${((by1 - by0) * fh).toFixed(2)}px`;
  ss.backgroundImage = `url("${sharpSrc}")`;
  ss.backgroundSize = `${fw}px ${fh}px`;
  ss.backgroundPosition = `${(-bx0 * fw).toFixed(2)}px ${(-by0 * fh).toFixed(2)}px`;
  st.frame.style.setProperty('--soft', `${((0.005 * sw) / s).toFixed(2)}px`);
  st.img.insertAdjacentElement('afterend', soft);
  soft.insertAdjacentElement('afterend', sharp);
  // the strip and its thumbs are built now, inert and transparent, so their first paint is not the frame they appear
  st.strip.innerHTML = stripHtml(h, 0);
  fillCredit(st, h, 0);
  st.strip.inert = true;
  st.close.inert = true;
  st.strip.hidden = false;
  st.close.hidden = false;
  if (reduce) {
    // reduced motion: a 300 ms dissolve between the room and the focus state, nothing moves (§7.4)
    st.el.classList.add('is-dissolve');
    st.scroller.style.opacity = '0';
    await wait(ms('--d-swap', 300) / 2);
    st.frame.style.transform = transform;
    st.el.dataset.look = 'in';
    st.scroller.style.opacity = '1';
    await wait(ms('--d-swap', 300) / 2);
  } else {
    st.frame.classList.add('is-moving', 'is-approach');
    void st.frame.offsetHeight; // the rest transform is the transition's start: the camera moves on the next frame
    st.frame.style.transform = transform;
    st.el.dataset.look = 'in';
    await wait(approach);
    // the camera stopped: the frame keeps its layer, rastered at this scale, so the strip's frame repaints nothing else
    st.frame.classList.add('is-held');
  }
  mark(`${stageId}:focus:camera:stop`, { scale: s });
  st.el.dataset.focus = 'on';
  // the interface, 100 ms after the camera stops, in 200 ms (focus spec §3.4)
  await wait(ms('--d-ui-wait', 100));
  // the strip was laid out (inert, transparent) while the camera moved: showing it is one class, no layout, no decode
  st.strip.inert = false;
  st.close.inert = false;
  st.strip.classList.add('is-on');
  st.close.classList.add('is-on');
  mark(`${stageId}:focus:ui:in`);
  st.strip.querySelectorAll<HTMLButtonElement>('.mag-thumb').forEach((b) => b.addEventListener('click', () => select(stageId, Number(b.dataset.i))));
  st.strip.querySelector('.mag-choose')?.addEventListener('click', () => void closeFocus(stageId, true));
  st.strip.querySelector('.mag-add')?.addEventListener('click', (e) => {
    const b = e.currentTarget as HTMLButtonElement;
    b.textContent = 'נוסף לסל';
    announce(`נוסף לסל: ${h.variants[st.focus!.index]?.name_he ?? ''}`);
    setTimeout(() => (b.textContent = 'הוספה לסל'), 2500);
  });
  (st.strip.querySelector<HTMLElement>('.mag-thumb[aria-checked="true"]') ?? st.close).focus({ preventScroll: true });
  announce(`${h.name_he}: ${h.variants[0]?.name_he ?? ''}. ${h.variants.length} וריאציות`);
}
function select(stageId: string, index: number): void {
  const st = stages.get(stageId);
  const h = st?.focus ? hotspotOf(st, st.focus.slot) : undefined;
  if (!st || !st.focus || !h) return;
  const n = h.variants.length;
  if (index < 0 || index >= n) {
    // no loop: the edge nudges 120 ms and the picture does not move (focus spec §3.3)
    const row = st.strip.querySelector<HTMLElement>('.mag-thumbs');
    if (row) {
      row.style.transition = `transform ${ms('--d-micro', 120)}ms var(--e-standard)`;
      row.style.transform = `translateX(${index < 0 ? 4 : -4}px)`;
      setTimeout(() => (row.style.transform = ''), ms('--d-micro', 120));
    }
    return;
  }
  st.focus.index = index;
  st.strip.querySelectorAll<HTMLButtonElement>('.mag-thumb').forEach((b, i) => {
    b.setAttribute('aria-checked', String(i === index));
    b.tabIndex = i === index ? 0 : -1;
    if (i === index) b.focus({ preventScroll: true });
  });
  // the swap in the room waits for the final layers; here the credit dissolves (300 ms, --d-swap)
  const credit = st.strip.querySelector<HTMLElement>('.mag-strip-credit')!;
  credit.style.transition = `opacity ${ms('--d-swap', 300) / 2}ms var(--e-standard)`;
  credit.style.opacity = '0';
  setTimeout(
    () => {
      fillCredit(st, h, index);
      credit.style.opacity = '1';
    },
    ms('--d-swap', 300) / 2,
  );
  mark(`${stageId}:focus:select`, index);
  announce(h.variants[index]?.name_he ?? '');
}
function browse(stageId: string, dir: 1 | -1): void {
  const st = stages.get(stageId);
  if (!st?.focus) return;
  select(stageId, st.focus.index + dir);
}
async function closeFocus(stageId: string, chosen: boolean): Promise<void> {
  const st = stages.get(stageId);
  if (!st?.focus) return;
  const f = st.focus;
  mark(`${stageId}:focus:ui:out`, { chosen });
  st.strip.classList.remove('is-on');
  st.close.classList.remove('is-on');
  await wait(ms('--d-ui-out', 150));
  st.strip.hidden = true;
  st.close.hidden = true;
  st.el.dataset.focus = 'return';
  mark(`${stageId}:return:start`);
  const ret = ms('--d-return', 1800);
  if (reduce) {
    st.scroller.style.opacity = '0';
    await wait(ms('--d-swap', 300) / 2);
    st.el.dataset.look = 'out';
    st.frame.style.transform = '';
    st.scroller.style.opacity = '1';
    await wait(ms('--d-swap', 300) / 2);
  } else {
    st.frame.classList.remove('is-approach');
    st.frame.classList.add('is-moving', 'is-return');
    st.el.dataset.look = 'out';
    await nextFrame();
    st.frame.style.transform = '';
    await wait(ret);
  }
  // the landing: exactly the frame at rest, no dissolve, no settling (focus spec §4.3)
  st.frame.classList.remove('is-return', 'is-moving', 'is-held');
  st.frame.querySelectorAll('.mag-soft, .mag-sharp').forEach((e) => e.remove());
  delete st.el.dataset.focus;
  delete st.el.dataset.look;
  st.el.classList.remove('is-dissolve');
  st.focus = null;
  if (phone()) st.scroller.scrollLeft = f.before;
  headHidden = false;
  head.dataset.on = 'stage';
  mark(`${stageId}:landed`, { chosen, variant: f.index });
  const h = hotspotOf(st, f.slot);
  if (chosen && h) announce(`${h.name_he}: ${h.variants[f.index]?.name_he ?? ''} בחדר`);
  st.marks.find((m) => m.dataset.slot === f.slot)?.focus({ preventScroll: true });
}
const cancelFocus = (stageId: string) => closeFocus(stageId, false);
const chooseVariant = (stageId: string) => closeFocus(stageId, true);
addEventListener('keydown', (e) => {
  const st = [...stages.values()].find((s) => s.focus);
  if (!st) return;
  if (e.key === 'Escape') {
    e.preventDefault();
    void cancelFocus(st.id);
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault();
    browse(st.id, 1);
  } else if (e.key === 'ArrowRight') {
    e.preventDefault();
    browse(st.id, -1);
  } else if (e.key === 'Enter' && (e.target as HTMLElement).classList?.contains('mag-thumb')) {
    e.preventDefault();
    void chooseVariant(st.id);
  }
});

// ---------- the P-D pan: the frame player after the fixes (scale 1.000, a decode window, constant speed) ----------
/** The Bible's walk: smoothstep ramps over the first `accel` and the last `land` of the time, constant between (manifest). */
function walkEase(accel: number, land: number): (t: number) => number {
  const N = 400;
  const v = (t: number) => {
    const s = (x: number) => x * x * (3 - 2 * x);
    if (t < accel) return s(t / accel);
    if (t > 1 - land) return s((1 - t) / land);
    return 1;
  };
  const acc: number[] = [0];
  for (let i = 1; i <= N; i++) acc.push(acc[i - 1]! + v((i - 0.5) / N) / N);
  const total = acc[N]!;
  return (t: number) => {
    const x = Math.min(N, Math.max(0, t * N));
    const i = Math.floor(x);
    const a = acc[i]!;
    const b = acc[Math.min(N, i + 1)]!;
    return (a + (b - a) * (x - i)) / total;
  };
}
const pan = { ready: false, playing: false, pos: 0, samples: [] as { t: number; p: number }[], play: (_dir: 1 | -1) => Promise.resolve() };
const panEl = document.getElementById('mag-pan');
if (panEl && data.pan) {
  const canvas = panEl.querySelector<HTMLCanvasElement>('canvas')!;
  const status = document.getElementById('mag-pan-status')!;
  const playBtn = document.getElementById('mag-pan-play') as HTMLButtonElement;
  const backBtn = document.getElementById('mag-pan-back') as HTMLButtonElement;
  const bar = panEl.querySelector<HTMLElement>('.mag-pan-progress span')!;
  let player: SequencePlayer | null = null;
  let last = 0;
  const ease = walkEase(data.pan.easing.accel, data.pan.easing.land);
  const setPos = (p: number) => {
    pan.pos = Math.min(last, Math.max(0, p));
    player?.draw(pan.pos);
    bar.style.setProperty('--p', String(last ? pan.pos / last : 0));
  };
  async function load(): Promise<void> {
    const variant = phone() ? 'mobile' : '1920';
    const avif = await supportsAvif();
    const v = data.pan.variants[variant]!;
    const count = avif ? v.avif : v.webp;
    const ext = avif ? 'avif' : 'webp';
    status.textContent = 'הקליפ נטען…';
    const loader = new Loader(4);
    const blobs = await Promise.all(
      Array.from({ length: count }, (_, i) => loader.fetch(`${data.pan.src}/${variant}/${String(i + 1).padStart(4, '0')}.${ext}`, 2)),
    );
    player = new SequencePlayer(canvas, new FrameWindow(blobs), 0.5);
    last = player.length - 1;
    await player.prime(0, 1);
    setPos(0);
    pan.ready = true;
    status.textContent = `מוכן: ${count} פריימים, ${data.pan.play_s} ש׳`;
    mark('pan:ready', { variant, count, ext });
  }
  const io2 = new IntersectionObserver(
    (es) => {
      if (es.some((e) => e.isIntersecting)) {
        io2.disconnect();
        void load();
      }
    },
    { rootMargin: '600px' },
  );
  io2.observe(panEl);
  pan.play = async (dir: 1 | -1) => {
    if (!player || pan.playing) return;
    pan.playing = true;
    pan.samples = [];
    mark('pan:play', dir);
    const from = pan.pos;
    const to = dir > 0 ? last : 0;
    if (reduce) {
      // reduced motion: a 300 ms dissolve between the two ends, nothing moves (the player resets its own alpha, so the
      // dissolve goes through the canvas: out over the first half, the far end drawn, in over the second)
      const half = ms('--d-swap', 300) / 2;
      await tween(half, (k) => (canvas.style.opacity = String(1 - k)));
      await player.prime(to, dir);
      setPos(to);
      await tween(half, (k) => (canvas.style.opacity = String(k)));
      canvas.style.opacity = '';
    } else {
      await tween((data.pan.play_s * 1000 * Math.abs(to - from)) / Math.max(1, last), (k) => {
        const p = from + (to - from) * ease(k);
        pan.samples.push({ t: performance.now(), p });
        player!.draw(p, { dir });
        pan.pos = p;
        bar.style.setProperty('--p', String(p / last));
      });
      setPos(to);
    }
    pan.playing = false;
    mark('pan:end', dir);
    playBtn.disabled = dir > 0;
    playBtn.setAttribute('aria-disabled', String(dir > 0));
    backBtn.disabled = dir < 0;
    backBtn.setAttribute('aria-disabled', String(dir < 0));
  };
  playBtn.addEventListener('click', () => void pan.play(1));
  backBtn.addEventListener('click', () => void pan.play(-1));
  // scrubbing by a drag (the picture follows the finger) and by the arrows
  let dragX: number | null = null;
  canvas.addEventListener('pointerdown', (e) => {
    dragX = e.clientX;
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener('pointermove', (e) => {
    if (dragX === null || !player || pan.playing) return;
    setPos(pan.pos - ((e.clientX - dragX) / canvas.clientWidth) * last * 1.4);
    dragX = e.clientX;
  });
  canvas.addEventListener('pointerup', () => (dragX = null));
  canvas.tabIndex = 0;
  canvas.addEventListener('keydown', (e) => {
    if (!player || pan.playing) return;
    if (e.key === 'ArrowLeft') setPos(pan.pos + 2);
    else if (e.key === 'ArrowRight') setPos(pan.pos - 2);
    else if (e.key === 'Enter' || e.key === ' ') void pan.play(pan.pos >= last ? -1 : 1);
    else return;
    e.preventDefault();
  });
}

// ---------- the states demo (§6.8) ----------
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
document.getElementById('st-primary')?.addEventListener('click', (e) => {
  const b = e.currentTarget as HTMLButtonElement;
  b.textContent = 'נוסף לסל';
  announce('נוסף לסל');
  setTimeout(() => (b.textContent = b.dataset.label ?? 'הוספה לסל'), 2500);
});
document.getElementById('st-loading')?.addEventListener('click', (e) => {
  const b = e.currentTarget as HTMLButtonElement;
  const label = b.textContent;
  b.textContent = 'רגע…';
  b.setAttribute('aria-busy', 'true');
  b.style.setProperty('--progress', '0.3');
  setTimeout(() => b.style.setProperty('--progress', '0.9'), 500);
  setTimeout(() => {
    b.textContent = label;
    b.removeAttribute('aria-busy');
    b.style.removeProperty('--progress');
  }, 1500);
});
document.getElementById('st-form')?.addEventListener('submit', (e) => {
  e.preventDefault();
  const input = document.getElementById('st-email') as HTMLInputElement;
  const err = document.getElementById('st-email-err')!;
  const ok = EMAIL.test(input.value.trim());
  err.hidden = ok;
  input.setAttribute('aria-invalid', ok ? 'false' : 'true');
  if (!ok) input.focus();
});

declare global {
  interface Window {
    __mag?: {
      events: typeof events;
      reduce: boolean;
      openFocus: typeof openFocus;
      chooseVariant: typeof chooseVariant;
      cancelFocus: typeof cancelFocus;
      browse: typeof browse;
      showMarks: (stage: string) => void;
      enter: typeof enter;
      paperTo: typeof paperTo;
      pan: typeof pan;
    };
  }
}
window.__mag = {
  events,
  reduce,
  openFocus,
  chooseVariant,
  cancelFocus,
  browse,
  showMarks: (id) => {
    const st = stages.get(id);
    if (st) showMarks(st);
  },
  enter,
  paperTo,
  pan,
};
mark('ready');
