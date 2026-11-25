/**
 * MOCK6 (2026-11-25): the wheel of many options (8–12: the kids' art sets to come, FB12), in the 3D arc's place from
 * MANY_FROM options on. A scroll-snap carousel of cards: a swipe on a phone, the mouse's wheel or a drag on a wide
 * screen, the keys (← → ↑ ↓, Home, End, Page Up / Down), and the previous / next buttons; a counter says where it rests
 * ("3 / 10"). The same dialog as the arc (VariantWheel): a radio group, Enter or "בחירה" confirms, Escape cancels.
 *
 * Lazy (the brief: "lazy-load only the patch for the selected option"): the wheel asks for an option (onPreview) only
 * when it comes to rest on it — a swipe across six cards asks for the sixth, never the five it passed — and the room's
 * engine loads that option's patch then (data.ts `behind` never loads a many-option slot ahead). The cards draw their
 * pictures only near the one it rests on (scroll-wheel.ts inReach).
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'preact/hooks';
import { IconClose, IconLeft, IconRight } from './Icons';
import { prefersReducedMotion } from '../motion';
import { wheelCountHe } from '../set-copy';
import type { WheelProps } from './VariantWheel';
import { cardLabelHe, counterHe, inReach, keyStep, nearest } from './scroll-wheel';

/** how long a scroll is still before the wheel calls it a rest (where `scrollend` is not fired) */
const REST_MS = 140;

export function ScrollWheel({ house, slot, initial, onPreview, onChoose, onCancel, chooseLabel, closeLabel }: WheelProps) {
  const n = slot.options.length;
  const dialog = useRef<HTMLDivElement>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const cards = useRef<(HTMLButtonElement | null)[]>([]);
  const [index, setIndexState] = useState(initial - 1);
  const indexRef = useRef(initial - 1);
  const [seen, setSeen] = useState<Set<number>>(() => inReach(initial - 1, n));
  const reduce = prefersReducedMotion();
  const restTimer = useRef(0);
  /** a move the wheel makes itself (a key, a button, a tap): the cards it passes on the way are not rests, until it
   *  lands or the visitor takes over (a second after it started at the latest) */
  const steering = useRef<{ to: number; until: number } | null>(null);

  const setIndex = (i: number) => {
    indexRef.current = i;
    setIndexState(i);
    setSeen((s) => {
      const next = new Set(s);
      for (const k of inReach(i, n)) next.add(k);
      return next.size === s.size ? s : next;
    });
  };
  const centerOf = (el: Element) => {
    const r = el.getBoundingClientRect();
    return r.left + r.width / 2;
  };
  /** the card in the scroller's middle */
  const resting = (): number => {
    const sc = scroller.current;
    if (!sc) return indexRef.current;
    return nearest(
      cards.current.map((c) => (c ? centerOf(c) : Infinity)),
      centerOf(sc),
    );
  };
  /** the scroller brings card `i` to its middle */
  const bring = (i: number, smooth: boolean) => {
    const sc = scroller.current;
    const c = cards.current[i];
    if (!sc || !c) return;
    sc.scrollBy({ left: centerOf(c) - centerOf(sc), behavior: smooth && !reduce ? 'smooth' : 'instant' });
  };

  // the wheel opens on the option the room shows, in the middle, and that card has the focus
  useLayoutEffect(() => {
    bring(initial - 1, false);
    cards.current[initial - 1]?.focus({ preventScroll: true });
  }, []);
  useEffect(() => () => clearTimeout(restTimer.current), []);

  /** the wheel came to rest on `i`: the room shows it (its patch is asked for now, and only now) */
  function rest(i: number) {
    if (i === indexRef.current) return;
    setIndex(i);
    onPreview(i + 1);
  }
  function goTo(i: number, focus = true) {
    const k = Math.max(0, Math.min(n - 1, i));
    steering.current = { to: k, until: performance.now() + 1000 };
    bring(k, true);
    rest(k);
    if (focus) cards.current[k]?.focus({ preventScroll: true });
  }
  function onScrolled() {
    clearTimeout(restTimer.current);
    restTimer.current = window.setTimeout(settle, REST_MS);
  }
  function settle() {
    clearTimeout(restTimer.current);
    const i = resting();
    // the wheel's own move ends where it was sent (a smooth scroll passes the cards between)
    const st = steering.current;
    if (st) {
      const now = performance.now();
      // still on its way (or a stop between frames): look again once it should have landed
      if (i !== st.to && now < st.until) {
        restTimer.current = window.setTimeout(settle, st.until - now + 20);
        return;
      }
      steering.current = null;
    }
    rest(i);
  }

  // a drag with the mouse (a finger scrolls the carousel itself): the cards follow, and the wheel rests where they stop
  const drag = useRef<{ x: number; id: number; moved: number } | null>(null);
  /** the visitor takes over (a finger, the mouse's wheel, a drag): the wheel's own move no longer counts */
  const takeOver = () => {
    steering.current = null;
  };
  function onPointerDown(e: PointerEvent) {
    takeOver();
    if (e.pointerType !== 'mouse' || e.button !== 0) return;
    drag.current = { x: e.clientX, id: e.pointerId, moved: 0 };
  }
  function onPointerMove(e: PointerEvent) {
    const d = drag.current;
    const sc = scroller.current;
    if (!d || !sc || d.id !== e.pointerId) return;
    const dx = e.clientX - d.x;
    d.x = e.clientX;
    d.moved += Math.abs(dx);
    if (d.moved > 6 && !sc.hasPointerCapture(e.pointerId)) {
      sc.setPointerCapture(e.pointerId);
      sc.dataset.drag = '';
    }
    if (d.moved > 6) sc.scrollBy({ left: -dx, behavior: 'instant' });
  }
  function onPointerUp(e: PointerEvent) {
    const d = drag.current;
    const sc = scroller.current;
    drag.current = null;
    if (!d || !sc || d.id !== e.pointerId || d.moved <= 6) return;
    delete sc.dataset.drag;
    steering.current = null;
    // the snap takes the cards to the nearest; the rest is read when they stop
    const i = resting();
    bring(i, true);
    onScrolled();
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
      return;
    }
    if (e.key === 'Tab') {
      const f = [...(dialog.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], [tabindex="0"]') ?? [])];
      if (!f.length) return;
      const first = f[0]!;
      const last = f[f.length - 1]!;
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
      return;
    }
    // the keys move the wheel when its cards have the focus (a button of the panel keeps its own keys)
    if (!(e.target as HTMLElement).closest?.('.snap')) return;
    const k = keyStep(e.key, indexRef.current, n);
    if (k === null) return;
    e.preventDefault();
    goTo(k);
  }

  const headingId = `picker-${slot.id}`;
  const opt = slot.options[index]!;
  return (
    <div class="picker picker-many" role="dialog" aria-modal="true" aria-labelledby={headingId} ref={dialog} onKeyDown={onKeyDown}>
      <div class="picker-head">
        <div>
          <p class="eyebrow">{wheelCountHe(n, house?.sets ?? false)}</p>
          <h2 id={headingId}>{slot.name_he}</h2>
        </div>
        <button type="button" class="glass close-btn" onClick={onCancel} aria-label={closeLabel ?? 'סגירה וחזרה לחדר בלי שינוי'}>
          <IconClose />
        </button>
      </div>
      {/* the arc's place in the dialog's grid; in it, the carousel and its counter */}
      <div class="arc snap-wrap" data-ground={house?.cardGround ? '' : undefined}>
        <div
          class="snap"
          ref={scroller}
          role="radiogroup"
          aria-labelledby={headingId}
          onScroll={onScrolled}
          onWheel={takeOver}
          onTouchStart={takeOver}
          // where the browser says so, a scroll's end is its rest at once
          {...{ onScrollEnd: settle }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
        >
          {slot.options.map((o, i) => {
            const near = seen.has(i);
            const node = near ? (house?.thumbNode?.(o.position) ?? null) : null;
            const img = near && !node && house?.thumb ? house.thumb(o.position) : null;
            return (
              <button
                key={o.position}
                type="button"
                class="snap-card"
                role="radio"
                aria-checked={i === index}
                aria-label={cardLabelHe(i, n, o.label_he ?? slot.name_he)}
                tabIndex={i === index ? 0 : -1}
                data-near={near ? '' : undefined}
                ref={(el) => {
                  cards.current[i] = el;
                }}
                onClick={() => (i === index ? onChoose(i + 1) : goTo(i))}
              >
                <span class="disc" aria-hidden="true" />
                {node ?? (img ? <img src={img} alt="" draggable={false} decoding="async" /> : null)}
              </button>
            );
          })}
        </div>
        {/* "3 / 10", read left to right as a count is (each card's name says "3 מתוך 10" to a screen reader) */}
        <p class="snap-count" dir="ltr" aria-hidden="true">
          {counterHe(index, n)}
        </p>
      </div>
      <div class="picker-info">
        <p class="name" aria-live="polite">
          {opt.label_he}
        </p>
        {house?.info ? house.info(index + 1) : null}
        <div class="picker-actions">
          <div class="arc-nav">
            <button type="button" class="glass" onClick={() => goTo(index - 1)} disabled={index === 0} aria-label="הגרסה הקודמת">
              <IconRight />
            </button>
            <button type="button" class="glass" onClick={() => goTo(index + 1)} disabled={index === n - 1} aria-label="הגרסה הבאה">
              <IconLeft />
            </button>
          </div>
          <button type="button" class="btn btn-primary" onClick={() => onChoose(index + 1)}>
            {chooseLabel ?? 'בחירה והצגה בחדר'}
          </button>
        </div>
      </div>
    </div>
  );
}
