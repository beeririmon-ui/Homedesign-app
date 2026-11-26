/**
 * FB20 (2026-11-26, briefs/site-wheel-3d-2026-11-26.md): the 3D product wheel of the tour. The options are round cards
 * on a ring seen from above (30–45°), the front arc nearest the viewer; cards behind recede, dim and blur. Drag, swipe,
 * the mouse's wheel or the keys turn it, with inertia and a gentle snap to the nearest card; it closes on itself, for 3
 * to 12 options. It replaces the arc (VariantWheel) and the scroll-snap carousel (ScrollWheel) in the tour; the room
 * page keeps the arc.
 *
 * Turning the ring never changes the room: the room stays dimmed under it, and only the card the ring rests on is
 * announced (`onPreview`, which the tour uses to fetch that option's layer ahead). Choosing a card (a tap on the front
 * card, Enter, or "בחירה") hands its position to `onChoose`: the tour lifts the dim as the product appears in the room.
 *
 * Semantics as the arc: a modal dialog with a radio group; ← and → (and ↓ ↑) move, Home and End, Escape cancels.
 * prefers-reduced-motion: the ring turns at once, no inertia.
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'preact/hooks';
import { prefersReducedMotion } from '../motion';
import { IconClose, IconLeft, IconRight } from './Icons';
import { RingPhysics, cardPose, ringGeom, ringIndex, type RingGeom } from './ring-wheel';
import { wheelCountHe } from '../set-copy';
import type { WheelProps } from './VariantWheel';

/** how long the ring rests on a card before it is announced (a fling passes cards without fetching them) */
const REST_MS = 140;

export function RingWheel({ house, slot, initial, onPreview, onChoose, onCancel, chooseLabel, closeLabel }: WheelProps) {
  const n = slot.options.length;
  const physics = useRef(new RingPhysics(n));
  const arc = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const cards = useRef<(HTMLButtonElement | null)[]>([]);
  const [index, setIndexState] = useState(initial - 1);
  const indexRef = useRef(initial - 1);
  const [geom, setGeom] = useState<RingGeom | null>(null);
  const g = useRef<RingGeom | null>(null);
  const raf = useRef(0);
  const restTimer = useRef(0);
  const announced = useRef(initial - 1);
  const reduce = prefersReducedMotion();

  const setIndex = (i: number) => {
    if (i === indexRef.current) return;
    indexRef.current = i;
    setIndexState(i);
  };
  /** the ring rests on card `i`: announced once it has stayed there a moment */
  const rest = (i: number) => {
    clearTimeout(restTimer.current);
    restTimer.current = window.setTimeout(() => {
      if (i === announced.current) return;
      announced.current = i;
      onPreview(i + 1);
    }, REST_MS);
  };

  // the cell's size, once when the dialog enters (frame 0, before the camera moves) and when the window changes
  useLayoutEffect(() => {
    const el = arc.current;
    if (!el) return;
    physics.current.setIndex(initial - 1);
    const measure = () => {
      const next = ringGeom(n, el.clientWidth, el.clientHeight);
      g.current = next;
      setGeom(next);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  useEffect(
    () => () => {
      cancelAnimationFrame(raf.current);
      clearTimeout(restTimer.current);
    },
    [],
  );
  useEffect(() => {
    cards.current[initial - 1]?.focus({ preventScroll: true });
  }, []);

  /** every card where the ring is now: transform and opacity only (the blurred copy and the veil are opacities) */
  function paint() {
    const G = g.current;
    if (!G) return;
    const pos = physics.current.pos;
    cards.current.forEach((c, i) => {
      if (!c) return;
      const p = cardPose(i, pos, G);
      c.style.transform = p.transform;
      c.style.opacity = p.opacity.toFixed(3);
      c.style.setProperty('--veil', p.veil.toFixed(3));
      c.style.setProperty('--soft', p.soft.toFixed(3));
      c.style.pointerEvents = p.live ? '' : 'none';
    });
  }
  useLayoutEffect(paint, [geom]);

  function run() {
    cancelAnimationFrame(raf.current);
    let last = performance.now();
    const tick = (now: number) => {
      const moving = physics.current.step((now - last) / 1000);
      last = now;
      paint();
      if (moving) raf.current = requestAnimationFrame(tick);
      else {
        setIndex(physics.current.index);
        rest(physics.current.index);
      }
    };
    raf.current = requestAnimationFrame(tick);
  }

  function goTo(i: number, focus = true) {
    const k = ((i % n) + n) % n;
    if (reduce) {
      physics.current.setIndex(k);
      paint();
    } else {
      physics.current.goTo(k);
      run();
    }
    setIndex(k);
    rest(k);
    if (focus) cards.current[k]?.focus({ preventScroll: true });
  }

  // ---- a finger or the mouse: drag with inertia; a tap is the card's own click ----
  const drag = useRef<{ x: number; moved: number; id: number } | null>(null);
  const pxPerItem = () => Math.max(90, (g.current?.cw ?? 120) * 1.15);
  function onPointerDown(e: PointerEvent) {
    drag.current = { x: e.clientX, moved: 0, id: e.pointerId };
    physics.current.startDrag(performance.now());
    cancelAnimationFrame(raf.current);
    clearTimeout(restTimer.current);
  }
  function onPointerMove(e: PointerEvent) {
    const d = drag.current;
    if (!d || d.id !== e.pointerId) return;
    const dx = e.clientX - d.x;
    d.x = e.clientX;
    d.moved += Math.abs(dx);
    if (d.moved > 6 && !arc.current?.hasPointerCapture(e.pointerId)) arc.current?.setPointerCapture(e.pointerId);
    physics.current.pxPerItem = pxPerItem();
    // RTL: dragging right brings the next (left) card to the front
    physics.current.drag(dx, performance.now());
    if (reduce) physics.current.setIndex(Math.round(physics.current.pos));
    paint();
    setIndex(ringIndex(physics.current.pos, n));
  }
  function onPointerUp(e: PointerEvent) {
    const d = drag.current;
    drag.current = null;
    if (!d || d.id !== e.pointerId) return;
    if (d.moved <= 6) return;
    // the card it will rest on is known at release (where the inertia lands)
    const t = physics.current.release();
    setIndex(t);
    if (reduce) {
      physics.current.setIndex(t);
      paint();
      rest(t);
    } else run();
  }
  // ---- the mouse's wheel (and a trackpad's swipe): it turns the ring, and snaps once the wheel is still ----
  const wheelIdle = useRef(0);
  function onWheel(e: WheelEvent) {
    const dx = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    if (!dx) return;
    e.preventDefault();
    cancelAnimationFrame(raf.current);
    clearTimeout(restTimer.current);
    if (reduce) {
      // one gesture, one card: the ring turns at once, and the rest of the gesture is let go
      if (!wheelIdle.current) goTo(indexRef.current + Math.sign(dx), false);
      clearTimeout(wheelIdle.current);
      wheelIdle.current = window.setTimeout(() => (wheelIdle.current = 0), 220);
      return;
    }
    physics.current.pxPerItem = pxPerItem();
    const px = e.deltaMode === 1 ? dx * 32 : dx;
    physics.current.pos += px / physics.current.pxPerItem / 1.6;
    physics.current.vel = 0;
    physics.current.target = null;
    paint();
    setIndex(ringIndex(physics.current.pos, n));
    clearTimeout(wheelIdle.current);
    wheelIdle.current = window.setTimeout(() => {
      physics.current.goTo(ringIndex(physics.current.pos, n));
      run();
    }, 120);
  }
  useEffect(() => () => clearTimeout(wheelIdle.current), []);

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
      e.preventDefault();
      goTo(indexRef.current + 1);
    } else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
      e.preventDefault();
      goTo(indexRef.current - 1);
    } else if (e.key === 'Home') {
      e.preventDefault();
      goTo(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      goTo(n - 1);
    } else if (e.key === 'Tab') {
      const f = [...(dialog.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], [tabindex="0"], input:checked') ?? [])];
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
    }
  }

  const headingId = `picker-${slot.id}`;
  const opt = slot.options[index]!;
  const G = geom;
  return (
    <div class="picker" data-ring="" role="dialog" aria-modal="true" aria-labelledby={headingId} ref={dialog} onKeyDown={onKeyDown}>
      <div class="picker-head">
        <div>
          <p class="eyebrow">{wheelCountHe(n, house?.sets ?? !!house?.info)}</p>
          <h2 id={headingId}>{slot.name_he}</h2>
        </div>
        <button type="button" class="glass close-btn" onClick={onCancel} aria-label={closeLabel ?? 'סגירה וחזרה לחדר בלי שינוי'}>
          <IconClose />
        </button>
      </div>
      <div
        class="arc ring"
        ref={arc}
        data-ground={house?.cardGround ? '' : undefined}
        role="radiogroup"
        aria-labelledby={headingId}
        style={G ? { perspective: `${G.p.toFixed(0)}px`, perspectiveOrigin: `${G.cx.toFixed(0)}px ${G.cy.toFixed(0)}px` } : undefined}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onWheel={onWheel}
      >
        <div
          class="arc-ring"
          ref={ring}
          style={
            G ? { '--cw': `${G.cw.toFixed(1)}px`, left: `${G.cx.toFixed(1)}px`, top: `${G.cy.toFixed(1)}px`, transform: `rotateX(${-G.tilt}deg)` } : undefined
          }
        >
          {/* the ring itself: a thin line round the cards' feet, lying in the ring's plane (an ellipse in perspective) */}
          {G ? <span class="ring-track" aria-hidden="true" style={{ width: `${(2 * G.r).toFixed(0)}px`, height: `${(2 * G.r).toFixed(0)}px` }} /> : null}
          {slot.options.map((o, i) => {
            const node = house?.thumbNode?.(o.position) ?? null;
            const img = node ? null : (house?.thumb?.(o.position) ?? null);
            const pic = node ?? (img ? <img src={img} alt="" draggable={false} /> : null);
            return (
              <button
                key={o.position}
                type="button"
                class="arc-card"
                role="radio"
                aria-checked={i === index}
                aria-label={`${i + 1} מתוך ${n}: ${o.label_he}`}
                tabIndex={i === index ? 0 : -1}
                ref={(el) => {
                  cards.current[i] = el;
                }}
                onClick={() => (i === index ? onChoose(i + 1) : goTo(i))}
              >
                <span class="disc" aria-hidden="true" />
                {pic}
                {/* the card behind goes soft: a blurred copy fades in (an opacity, never a filter per frame) */}
                {pic ? (
                  <span class="soft" aria-hidden="true">
                    {node ? (house?.thumbNode?.(o.position) ?? null) : <img src={img!} alt="" draggable={false} />}
                  </span>
                ) : (
                  <span class="ph" aria-hidden="true">
                    <span>{o.label_he}</span>
                  </span>
                )}
                <span class="veil" aria-hidden="true" />
              </button>
            );
          })}
        </div>
      </div>
      <div class="picker-info">
        {n > 3 ? (
          <p class="ring-count" aria-hidden="true">
            {index + 1} / {n}
          </p>
        ) : (
          <div class="pips" aria-hidden="true">
            {slot.options.map((_, i) => (
              <i key={i} class={i === index ? 'on' : ''} />
            ))}
          </div>
        )}
        <p class="name" aria-live="polite">
          {opt.label_he}
        </p>
        {house?.info ? house.info(index + 1) : null}
        <div class="picker-actions">
          <div class="arc-nav">
            <button type="button" class="glass" onClick={() => goTo(index - 1)} aria-label="הגרסה הקודמת">
              <IconRight />
            </button>
            <button type="button" class="glass" onClick={() => goTo(index + 1)} aria-label="הגרסה הבאה">
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
