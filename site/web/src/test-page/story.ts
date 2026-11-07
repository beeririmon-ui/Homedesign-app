/**
 * The story-first prototype (/test/story/, briefs/site-story-prototype-2026-11-07.md). Static HTML first: the frames,
 * their LQIPs, the dots and the product lists are in the page before this runs (tools/make-story-page.ts). This module
 * adds the frame layout (the cover crop on desktop, the 4:5 crop at full width on the phone), the frames
 * developing from their LQIP, the dots (nothing at rest; on movement, touch or keyboard focus; gone 2.5 s later; a
 * hint once per frame, ו.4), the wall label, the "קנה את המראה" sheet (a modal dialog: Esc, the backdrop and × close it,
 * the focus returns to the dot or row that opened it), the browse through the look, and the test cart.
 * Every duration and curve is a token of magazine.css (§7.1). `window.__story` exposes the timeline for the evidence
 * tool (tools/screens-story.ts) and the e2e suite.
 */
import './fonts.css';
import './magazine.css';
import './story.css';
import { prefersReducedMotion } from '../motion';
import { priceHe, storyCart, type StoryVariant } from './story-cart';

type Item = {
  id: string;
  frame: string;
  n: number;
  product: string;
  u: number;
  v: number;
  dot: boolean;
  phone: { u: number; v: number } | null;
  name_he: string;
  detail_he: string;
  price_he: string | null;
  price_agorot: number | null;
  variant_id: string | null;
  option_he: string | null;
  status: 'available' | 'unavailable' | 'unpriced';
  set_qty: number;
  notes_he: string[];
  image: { src: string; srcset: string; w: number; h: number } | null;
  thumb: string | null;
  swatch: string;
  href: string | null;
  try_href: string | null;
};
type FrameData = { id: string; u0: number; v0: number; aspect: number; crop: [number, number]; title_he: string; items: string[] };
type Data = { mark_he: string; items: Record<string, Item>; frames: FrameData[] };

const data = JSON.parse(document.getElementById('st-data')!.textContent ?? '{}') as Data;
const root = document.body;
const reduce = prefersReducedMotion();
const phone = () => innerWidth < 720;
const ms = (name: string, fallback: number): number => {
  const v = getComputedStyle(root).getPropertyValue(name).trim();
  const n = parseFloat(v);
  return Number.isFinite(n) ? (v.endsWith('ms') ? n : n * 1000) : fallback;
};
const wait = (t: number) => new Promise<void>((r) => setTimeout(r, t));

// ---------- the timeline (evidence) and the live region ----------
const events: { t: number; name: string; detail?: unknown }[] = [];
const mark = (name: string, detail?: unknown) => events.push({ t: performance.now(), name, detail });
const live = document.getElementById('mag-live')!;
function announce(text: string): void {
  live.textContent = '';
  void live.offsetHeight;
  live.textContent = text;
}

// ---------- the running head: transparent on a frame, paper with a hairline on paper ----------
const head = document.getElementById('mag-head')!;
const run = document.getElementById('mag-run')!;
const io = new IntersectionObserver(
  (entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const el = e.target as HTMLElement;
      run.textContent = el.dataset.head ?? '';
      head.dataset.on = el.classList.contains('mag-paper') ? 'paper' : 'stage';
      if (el.classList.contains('st-spread')) firstEntry(el);
    }
  },
  { threshold: 0.55 },
);
for (const s of document.querySelectorAll<HTMLElement>('[data-head]')) io.observe(s);
void Promise.race([document.fonts.ready, wait(800)]).then(() => {
  root.classList.add('is-brand');
  mark('brand');
});

// ---------- the frames: develop from the LQIP, then the title ----------
type Stage = {
  id: string;
  section: HTMLElement;
  el: HTMLElement;
  frame: HTMLElement;
  scroller: HTMLElement;
  img: HTMLImageElement;
  label: HTMLElement;
  marks: HTMLButtonElement[];
  d: FrameData;
  idle: ReturnType<typeof setTimeout> | undefined;
  hinted: boolean;
};
const stages = new Map<string, Stage>();
function developed(st: Stage): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      st.frame.classList.add('is-developed');
      mark(`${st.id}:developed`);
      resolve();
    };
    if (st.img.complete && st.img.naturalWidth) done();
    else {
      st.img.addEventListener('load', done, { once: true });
      st.img.addEventListener('error', done, { once: true });
    }
  });
}
for (const d of data.frames) {
  const section = document.getElementById(`frame-${d.id}`);
  const el = section?.querySelector<HTMLElement>('.mag-stage');
  if (!section || !el) continue;
  const st: Stage = {
    id: d.id,
    section,
    el,
    frame: el.querySelector('.mag-frame')!,
    scroller: el.querySelector('.mag-scroller')!,
    img: el.querySelector('.mag-pic img')!,
    label: el.querySelector('.mag-label')!,
    marks: [...el.querySelectorAll<HTMLButtonElement>('.st-mark')],
    d,
    idle: undefined,
    hinted: false,
  };
  stages.set(d.id, st);
  mark(`${d.id}:lqip`);
  void developed(st).then(async () => {
    await wait(reduce ? 0 : ms('--d-develop', 600) / 3);
    section.classList.add('is-title');
    mark(`${d.id}:title`);
  });
  layout(st);
  // the stage is the frame's row above the paper band: its height settles with the fonts and follows the window
  new ResizeObserver(() => layout(st)).observe(el);
  const onMove = () => showMarks(st);
  el.addEventListener('pointermove', onMove);
  el.addEventListener('pointerdown', onMove);
  for (const m of st.marks) {
    const id = m.dataset.item!;
    m.addEventListener('pointerenter', () => wallLabel(st, id));
    m.addEventListener('pointerleave', () => wallLabel(st, null));
    m.addEventListener('focus', () => wallLabel(st, id));
    m.addEventListener('blur', () => wallLabel(st, null));
    m.addEventListener('click', () => void openSheet(id, m));
  }
}

/**
 * The frame's box is the picture's drawn rectangle, so a dot at (u, v) sits on the picture's (u, v):
 *  - phone: the 4:5 crop at full width (CSS; the dots use the crop's own --pu, --pv, and a product the crop does not
 *    carry has no dot there, G-ED.17)
 *  - desktop up to 2.4:1: the frame covers the stage at its focal point (u0, v0), like object-fit: cover
 *  - desktop wider: the frame at the stage's full height with paper at the sides, a print on a page
 */
function layout(st: Stage): void {
  const fs = st.frame.style;
  const { d } = st;
  if (phone()) {
    fs.position = fs.width = fs.height = fs.left = fs.top = '';
    for (const m of st.marks) m.hidden = false;
    return;
  }
  const sw = st.el.clientWidth;
  const sh = st.el.clientHeight;
  if (!sw || !sh) return;
  const cover = sw / sh <= 2.4;
  const fw = cover ? Math.max(sw, sh * d.aspect) : sh * d.aspect;
  const fh = fw / d.aspect;
  const left = cover ? (sw - fw) * d.u0 : (sw - fw) / 2;
  const top = cover ? (sh - fh) * d.v0 : 0;
  fs.position = 'absolute';
  fs.width = `${fw}px`;
  fs.height = `${fh}px`;
  fs.left = `${left}px`;
  fs.top = `${top}px`;
  st.el.classList.toggle('is-print', !cover);
  // the part of the frame on screen, less half a target and its ring (29 px) on each side; at the top, a dot's centre
  // stays clear of the top band (which lies over the frame), or a click there would land on the band (QA 2026-11-07)
  const band = (parseFloat(getComputedStyle(root).getPropertyValue('--head-h')) || 64) + 4;
  keepMarksInView(st, [(29 - left) / fw, (sw - 29 - left) / fw], [(Math.max(29, band) - top) / fh, (sh - 29 - top) / fh]);
}
/** A dot whose target would leave the screen (the cover crop cuts the frame) is not offered there; the list has it. */
function keepMarksInView(st: Stage, [uMin, uMax]: [number, number], [vMin, vMax]: [number, number]): void {
  for (const m of st.marks) {
    const it = data.items[m.dataset.item!];
    if (it) m.hidden = it.u < uMin || it.u > uMax || it.v < vMin || it.v > vMax;
  }
}
function showMarks(st: Stage): void {
  if (st.el.dataset.marks !== 'on') {
    st.el.dataset.marks = 'on';
    mark(`${st.id}:marks:on`);
  }
  clearTimeout(st.idle);
  st.idle = setTimeout(
    () => {
      st.el.dataset.marks = 'off';
      st.idle = undefined;
      mark(`${st.id}:marks:off`);
    },
    ms('--t-mark-idle', 2500),
  );
}
/** the hint, once per frame per visit: the dots appear and go after 1.2 s (art direction §6.4) */
function firstEntry(section: HTMLElement): void {
  const st = [...stages.values()].find((s) => s.section === section);
  if (!st || st.hinted) return;
  st.hinted = true;
  setTimeout(() => {
    if (st.el.dataset.marks === 'on') return;
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
/** the wall label (desktop, art direction §6.4): the credit, 12 px above the dot; on the phone the sheet carries it */
function wallLabel(st: Stage, id: string | null): void {
  const it = id ? data.items[id] : undefined;
  if (!it || phone()) {
    st.label.classList.remove('is-on');
    return;
  }
  st.label.innerHTML = '<span class="mag-credit-name"></span><span class="mag-credit-detail"></span>';
  st.label.querySelector('.mag-credit-name')!.textContent = it.name_he;
  st.label.querySelector('.mag-credit-detail')!.textContent = it.status === 'unavailable' ? `${it.detail_he} · המלאי אינו זמין כעת` : it.detail_he;
  const fr = st.frame.getBoundingClientRect();
  const sr = st.el.getBoundingClientRect();
  const headH = parseFloat(getComputedStyle(root).getPropertyValue('--head-h')) || 64;
  const x = fr.left - sr.left + it.u * st.frame.offsetWidth;
  const y = fr.top - sr.top + it.v * st.frame.offsetHeight - 23 - 12;
  st.label.style.left = `${Math.min(Math.max(x, 190), st.el.clientWidth - 190)}px`;
  st.label.style.top = `${Math.max(headH + 8 + 60, y)}px`;
  st.label.classList.add('is-on');
}

// ---------- the test cart ----------
const variants: StoryVariant[] = Object.values(data.items).flatMap((it) =>
  it.variant_id && it.price_agorot !== null
    ? [
        {
          variant_id: it.variant_id,
          product_id: it.product,
          name_he: it.name_he,
          option_he: it.option_he,
          price_agorot: it.price_agorot,
          set_qty: it.set_qty,
          available: it.status === 'available',
        },
      ]
    : [],
);
const cart = storyCart([...new Map(variants.map((v) => [v.variant_id, v])).values()]);
const countEl = document.getElementById('st-cart-count')!;
function showCount(animate: boolean): void {
  const n = cart.current()?.count ?? 0;
  if (!animate || reduce) {
    countEl.textContent = String(n);
    return;
  }
  // the figure changes in a 120 ms dissolve (art direction §7.2)
  countEl.classList.add('is-changing');
  setTimeout(
    () => {
      countEl.textContent = String(n);
      countEl.classList.remove('is-changing');
    },
    ms('--d-micro', 120),
  );
}
showCount(false);

// ---------- the sheet: "קנה את המראה" ----------
const sheet = document.getElementById('st-sheet') as HTMLDialogElement;
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const nameEl = $('st-sheet-name');
const detailEl = $('st-sheet-detail');
const notesEl = $('st-sheet-notes');
const imgEl = $<HTMLImageElement>('st-sheet-img');
const noneEl = $('st-sheet-none');
const capEl = $('st-sheet-cap');
const addBtn = $<HTMLButtonElement>('st-add');
const whyEl = $('st-why');
const pageLink = $<HTMLAnchorElement>('st-page');
const tryLink = $<HTMLAnchorElement>('st-try');
const sepEl = sheet.querySelector<HTMLElement>('.st-sep')!;
const posEl = $('st-pos');
const kickerEl = $('st-sheet-kicker');
const inCartEl = $('st-in-cart');
const items = (n: number) => (n === 1 ? 'פריט אחד' : `${n} פריטים`);
/** what the test cart holds, under the action: on desktop the sheet covers the top band's count */
function showInCart(): void {
  const c = cart.current();
  inCartEl.hidden = !c?.count;
  inCartEl.textContent = c?.count ? `בסל: ${items(c.count)} · ${priceHe(c.subtotal_agorot)}` : '';
}
let current: Item | null = null;
let opener: HTMLElement | null = null;
let addTimer: ReturnType<typeof setTimeout> | undefined;

function fill(it: Item): void {
  current = it;
  const fr = data.frames.find((f) => f.id === it.frame)!;
  kickerEl.textContent = `קנה את המראה · ${fr.title_he}`;
  nameEl.textContent = it.name_he;
  detailEl.textContent = it.detail_he;
  notesEl.replaceChildren(
    ...it.notes_he.map((t) => {
      const li = document.createElement('li');
      li.textContent = t;
      return li;
    }),
  );
  if (it.image) {
    imgEl.hidden = false;
    noneEl.hidden = true;
    imgEl.srcset = it.image.srcset;
    imgEl.sizes = '(max-width: 719px) calc(100vw - 48px), 26rem';
    imgEl.src = it.image.src;
    imgEl.width = it.image.w;
    imgEl.height = it.image.h;
    imgEl.alt = `צילום הספק: ${it.name_he}`;
    capEl.textContent = it.option_he ? `צילום הספק, בגוון שבתמונה (${it.option_he}).` : 'צילום הספק.';
  } else {
    imgEl.hidden = true;
    imgEl.removeAttribute('src');
    imgEl.removeAttribute('srcset');
    noneEl.hidden = false;
    noneEl.style.setProperty('--swatch', it.swatch);
    capEl.textContent = 'בינתיים: הגוון העיקרי של המוצר, מהכרטיס.';
  }
  // the action: add to the test cart; not for sale: a caption that says why, never a disabled button (§6.8)
  clearTimeout(addTimer);
  addBtn.textContent = 'הוספה לסל';
  const sold = it.status === 'available' && !!it.variant_id;
  addBtn.hidden = !sold;
  whyEl.hidden = sold;
  whyEl.textContent =
    it.status === 'unavailable'
      ? `המלאי אינו זמין כעת.${it.href ? ' בדף המוצר אפשר לבקש עדכון כשהוא חוזר.' : ''}`
      : sold
        ? ''
        : 'המחיר עוד לא נקבע, ולכן המוצר עוד לא במכירה.';
  pageLink.hidden = !it.href;
  if (it.href) pageLink.href = it.href;
  tryLink.hidden = !it.try_href;
  if (it.try_href) tryLink.href = it.try_href;
  sepEl.hidden = !it.href || !it.try_href;
  const list = fr.items;
  const at = list.indexOf(it.id);
  posEl.textContent = `${at + 1} מתוך ${list.length}`;
  // the ends stay focusable and say so (no loop; like the product gallery's buttons)
  $('st-prev').setAttribute('aria-disabled', String(at === 0));
  $('st-next').setAttribute('aria-disabled', String(at === list.length - 1));
  showInCart();
}
async function openSheet(id: string, from: HTMLElement): Promise<void> {
  const it = data.items[id];
  if (!it) return;
  opener = from;
  fill(it);
  mark('sheet:open:start', id);
  if (!sheet.open) {
    sheet.showModal();
    // the closed style is resolved now, so the fade starts in this very frame (response ≤ 100 ms, art direction §10.7)
    void getComputedStyle(sheet).opacity;
    sheet.classList.add('is-on');
  }
  nameEl.focus({ preventScroll: true });
  mark('sheet:open', id);
  announce(`קנה את המראה: ${it.name_he}. ${it.detail_he}`);
}
async function closeSheet(): Promise<void> {
  if (!sheet.open) return;
  mark('sheet:close:start');
  sheet.classList.remove('is-on');
  await wait(ms('--d-ui-out', 150));
  sheet.close();
  mark('sheet:close');
  // back to the dot or the row it was opened from (a dot hidden by the crop: its row in the list)
  const back = opener && !opener.hidden ? opener : document.querySelector<HTMLElement>(`.st-open[data-item="${current?.id ?? ''}"]`);
  back?.focus({ preventScroll: false });
}
function step(dir: 1 | -1): void {
  if (!current) return;
  const list = data.frames.find((f) => f.id === current!.frame)!.items;
  const i = list.indexOf(current.id) + dir;
  if (i < 0 || i >= list.length) return;
  const next = data.items[list[i]!]!;
  fill(next);
  opener = document.querySelector<HTMLElement>(`.st-mark[data-item="${next.id}"]`);
  mark('sheet:step', next.id);
  announce(`${next.name_he}. ${next.detail_he}`);
}
$('st-sheet-close').addEventListener('click', () => void closeSheet());
$('st-prev').addEventListener('click', () => step(-1));
$('st-next').addEventListener('click', () => step(1));
sheet.addEventListener('cancel', (e) => {
  e.preventDefault();
  void closeSheet();
});
// the backdrop: a click on the dialog's own box outside its content
sheet.addEventListener('click', (e) => {
  if (e.target === sheet) void closeSheet();
});
addBtn.addEventListener('click', async () => {
  const it = current;
  if (!it?.variant_id || it.status !== 'available') return;
  try {
    const c = await cart.add(it.variant_id);
    mark('cart:add', it.variant_id);
    showCount(true);
    showInCart();
    // the confirmation is in the button itself, 2.5 s, and said aloud; no toast (art direction §7.2)
    addBtn.textContent = 'נוסף לסל';
    clearTimeout(addTimer);
    addTimer = setTimeout(() => (addBtn.textContent = 'הוספה לסל'), 2500);
    announce(`נוסף לסל: ${it.name_he}. בסל ${items(c.count)}, ${priceHe(c.subtotal_agorot)}.`);
  } catch {
    announce('לא הצלחנו להוסיף לסל.');
  }
});
for (const b of document.querySelectorAll<HTMLButtonElement>('.st-open')) b.addEventListener('click', () => void openSheet(b.dataset.item!, b));
// on the phone a vertical swipe down on the sheet's top closes it (the sheet comes from the bottom)
let sy: number | null = null;
sheet.addEventListener('touchstart', (e) => (sy = sheet.scrollTop <= 0 ? (e.touches[0]?.clientY ?? null) : null), { passive: true });
sheet.addEventListener(
  'touchend',
  (e) => {
    const y = e.changedTouches[0]?.clientY ?? null;
    if (sy !== null && y !== null && y - sy > 80 && phone()) void closeSheet();
    sy = null;
  },
  { passive: true },
);

// ---------- the cart dialog ----------
const cartDlg = $<HTMLDialogElement>('st-cart');
function renderCart(): void {
  const c = cart.current();
  const lines = c?.lines ?? [];
  $('st-cart-lines').replaceChildren(
    ...lines.map((l) => {
      const li = document.createElement('li');
      li.className = 'mag-credit st-cart-line';
      const name = document.createElement('span');
      name.className = 'mag-credit-name';
      name.textContent = l.name_he;
      const detail = document.createElement('span');
      detail.className = 'mag-credit-detail';
      detail.textContent = `${l.qty} × ${priceHe(l.unit_price_agorot)} · ${priceHe(l.line_total_agorot)}`;
      const body = document.createElement('span');
      body.className = 'mag-credit-body';
      body.append(name, detail);
      li.append(body);
      return li;
    }),
  );
  $('st-cart-empty').hidden = lines.length > 0;
  $('st-cart-total').textContent = lines.length ? `סכום ביניים: ${priceHe(c!.subtotal_agorot)} · ${items(c!.count)}` : '';
}
$('st-cart-open').addEventListener('click', async () => {
  renderCart();
  cartDlg.showModal();
  void getComputedStyle(cartDlg).opacity;
  cartDlg.classList.add('is-on');
  $('st-cart-title').focus({ preventScroll: true });
});
async function closeCart(): Promise<void> {
  cartDlg.classList.remove('is-on');
  await wait(ms('--d-ui-out', 150));
  cartDlg.close();
  $('st-cart-open').focus();
}
$('st-cart-close').addEventListener('click', () => void closeCart());
cartDlg.addEventListener('cancel', (e) => {
  e.preventDefault();
  void closeCart();
});
cartDlg.addEventListener('click', (e) => {
  if (e.target === cartDlg) void closeCart();
});
$('st-cart-clear').addEventListener('click', () => {
  cart.clear();
  renderCart();
  showCount(true);
  announce('הסל רוקן.');
});

declare global {
  interface Window {
    __story?: {
      events: typeof events;
      reduce: boolean;
      openSheet: (id: string) => Promise<void>;
      closeSheet: typeof closeSheet;
      showMarks: (frame: string) => void;
      cartCount: () => number;
    };
  }
}
window.__story = {
  events,
  reduce,
  openSheet: (id) => openSheet(id, document.querySelector<HTMLElement>(`.st-mark[data-item="${id}"]`) ?? document.body),
  closeSheet,
  showMarks: (id) => {
    const st = stages.get(id);
    if (st) showMarks(st);
  },
  cartCount: () => cart.current()?.count ?? 0,
};
mark('ready');
