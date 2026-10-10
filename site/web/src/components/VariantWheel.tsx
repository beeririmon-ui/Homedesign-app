/**
 * Variant wheel: a 3D arc (CSS perspective) with drag, inertia and snap (pointer events: touch and mouse),
 * arrow keys, and visible previous/next buttons. Semantics: a modal dialog with a radio group; moving between
 * options previews them live in the room behind, Enter or "בחירה" confirms, Escape cancels.
 */
import { useEffect, useLayoutEffect, useRef, useState } from 'preact/hooks';
import type { CatalogSlot, Pack } from '@hd/shared';
import { packLabelHe } from '@hd/shared/packs';
import { formatIls } from '@hd/shared/money';
import { product } from '../catalog';
import { ArcPhysics } from '../engine/wheel-physics';
import { optionImage, Price } from './Media';
import { IconClose, IconLeft, IconRight } from './Icons';
import { addToCart, cartBusy } from '../state/cart';
import { prefersReducedMotion } from '../motion';
import { PackPicker, packPrice } from './PackPicker';

const STEP_DEG = 34;

type Props = {
  slot: CatalogSlot;
  initial: number; // 1-based position
  onPreview: (position: number) => void;
  onChoose: (position: number) => void;
  onCancel: () => void;
};

export function VariantWheel({ slot, initial, onPreview, onChoose, onCancel }: Props) {
  const n = slot.options.length;
  const physics = useRef(new ArcPhysics(n));
  const ring = useRef<HTMLDivElement>(null);
  const arc = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const cards = useRef<(HTMLButtonElement | null)[]>([]);
  const [index, setIndex] = useState(initial - 1);
  const [cw, setCw] = useState(150);
  const raf = useRef(0);
  const reduce = prefersReducedMotion();

  const opt = slot.options[index]!;
  const p = product(opt.product_id);
  // P1: set (default) or one piece; every option starts at its set
  const [pack, setPack] = useState<Pack>('set');
  useEffect(() => setPack('set'), [index]);

  // layout: card width from the arc height
  useLayoutEffect(() => {
    const el = arc.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setCw(Math.max(104, Math.min(200, el.clientHeight * 0.78, el.clientWidth * 0.34))));
    ro.observe(el);
    physics.current.setIndex(initial - 1);
    paint();
    return () => ro.disconnect();
  }, []);

  // focus the current option when the dialog opens; trap Tab inside
  useEffect(() => {
    cards.current[initial - 1]?.focus({ preventScroll: true });
  }, []);

  const R = cw * 1.9;
  function paint() {
    const r = ring.current;
    if (!r) return;
    const pos = physics.current.pos;
    r.style.transform = `translateZ(${-R}px)`;
    cards.current.forEach((c, i) => {
      if (!c) return;
      const d = i - pos;
      // RTL: the next option sits to the left
      c.style.transform = `rotateY(${-d * STEP_DEG}deg) translateZ(${R}px)`;
      const f = Math.max(0, 1 - Math.abs(d) / 2.2);
      c.style.opacity = String(0.25 + 0.75 * f);
      c.style.filter = `brightness(${0.6 + 0.4 * f}) blur(${(1 - f) * 2}px)`;
    });
  }
  useLayoutEffect(paint, [cw]);

  function run() {
    cancelAnimationFrame(raf.current);
    let last = performance.now();
    const tick = (now: number) => {
      const moving = physics.current.step((now - last) / 1000);
      last = now;
      paint();
      if (moving) raf.current = requestAnimationFrame(tick);
      else settle();
    };
    raf.current = requestAnimationFrame(tick);
  }

  function settle() {
    const i = physics.current.clampIndex(physics.current.pos);
    if (i !== index) {
      setIndex(i);
      onPreview(i + 1);
    }
  }

  function goTo(i: number, focus = true) {
    const k = physics.current.clampIndex(i);
    if (reduce) {
      physics.current.setIndex(k);
      paint();
      if (k !== index) {
        setIndex(k);
        onPreview(k + 1);
      }
    } else {
      physics.current.goTo(k);
      run();
      if (k !== index) {
        setIndex(k);
        onPreview(k + 1);
      }
    }
    if (focus) cards.current[k]?.focus({ preventScroll: true });
  }

  // ---- pointer drag with inertia ----
  const drag = useRef<{ x: number; moved: number; id: number } | null>(null);
  function onPointerDown(e: PointerEvent) {
    drag.current = { x: e.clientX, moved: 0, id: e.pointerId };
    physics.current.startDrag(performance.now());
    cancelAnimationFrame(raf.current);
  }
  function onPointerMove(e: PointerEvent) {
    const d = drag.current;
    if (!d || d.id !== e.pointerId) return;
    const dx = e.clientX - d.x;
    d.x = e.clientX;
    d.moved += Math.abs(dx);
    if (d.moved > 6 && !arc.current?.hasPointerCapture(e.pointerId)) arc.current?.setPointerCapture(e.pointerId);
    physics.current.pxPerItem = Math.max(120, cw * 1.1);
    physics.current.drag(dx, performance.now()); // RTL: dragging right brings the next (left) option in
    paint();
  }
  function onPointerUp(e: PointerEvent) {
    const d = drag.current;
    drag.current = null;
    if (!d || d.id !== e.pointerId) return;
    if (d.moved <= 6) return; // a tap: the card's click handler decides
    physics.current.release();
    run();
  }

  function onKeyDown(e: KeyboardEvent) {
    // the set / single radios use the arrow keys themselves
    const inRadio = (e.target as HTMLElement).matches?.('input[type="radio"]');
    if (inRadio && e.key !== 'Escape' && e.key !== 'Tab') return;
    if (e.key === 'Escape') {
      e.preventDefault();
      onCancel();
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
      e.preventDefault();
      goTo(index + 1);
    } else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
      e.preventDefault();
      goTo(index - 1);
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
  const specs: [string, string][] = [];
  if (p?.materials_he.length) specs.push(['חומר', p.materials_he.join(', ')]);
  const dims = p ? [p.dimensions_cm.width, p.dimensions_cm.depth, p.dimensions_cm.height].filter((x): x is number => typeof x === 'number') : [];
  if (dims.length) specs.push(['מידות', `${dims.join(' × ')} ס"מ`]);

  return (
    <div class="picker" role="dialog" aria-modal="true" aria-labelledby={headingId} ref={dialog} onKeyDown={onKeyDown}>
      <div class="picker-head">
        <div>
          <p class="eyebrow">
            {n} וריאציות · {slot.hotspot?.provisional ? 'מיקום זמני' : 'בחדר'}
          </p>
          <h2 id={headingId}>{slot.name_he}</h2>
        </div>
        <button type="button" class="glass close-btn" onClick={onCancel} aria-label="סגירה וחזרה לחדר בלי שינוי">
          <IconClose />
        </button>
      </div>
      <div
        class="arc"
        ref={arc}
        role="radiogroup"
        aria-labelledby={headingId}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div class="arc-ring" ref={ring} style={{ '--cw': `${cw}px` }}>
          {slot.options.map((o, i) => {
            const prod = product(o.product_id);
            const img = optionImage(slot.id, o.position);
            const label = `${i + 1} מתוך ${n}: ${
              prod ? `${prod.name_he}, ${prod.pack ? `${packLabelHe('set', prod.pack.set_qty)} ` : ''}${formatIls(prod.price_agorot)}` : o.label_he
            }`;
            return (
              <button
                key={o.position}
                type="button"
                class="arc-card"
                role="radio"
                aria-checked={i === index}
                aria-label={label}
                tabIndex={i === index ? 0 : -1}
                ref={(el) => {
                  cards.current[i] = el;
                }}
                onClick={() => (i === index ? onChoose(i + 1) : goTo(i))}
              >
                <span class="disc" aria-hidden="true" />
                {img ? <img src={img} alt="" draggable={false} /> : null}
                {!img || o.placeholder ? (
                  <span class="ph" aria-hidden="true">
                    <span>
                      <i style={{ background: prod?.color_hex ?? 'rgba(244,241,236,.5)' }} />
                      {o.placeholder ? 'ממתינה למוצר' : ''}
                    </span>
                  </span>
                ) : null}
                <span class="num-tag" aria-hidden="true">
                  {i + 1}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      <div class="picker-info">
        <div class="pips" aria-hidden="true">
          {slot.options.map((_, i) => (
            <i key={i} class={i === index ? 'on' : ''} />
          ))}
        </div>
        <p class="name" aria-live="polite">
          {p ? p.name_he : opt.label_he}
        </p>
        {specs.length ? (
          <p class="specs">
            {specs.map(([k, v]) => (
              <span key={k}>
                {k}: {v}
              </span>
            ))}
          </p>
        ) : null}
        {p ? (
          <>
            <Price class="price" agorot={packPrice(p, pack)} provisional={p.price_provisional} />
            <PackPicker p={p} value={pack} onChange={setPack} id={`wheel-pack-${slot.id}`} onStage />
          </>
        ) : (
          <p class="specs">אין עדיין מוצר בעמדה הזו. התצוגה בחדר זמנית.</p>
        )}
        <div class="picker-actions">
          <div class="arc-nav">
            <button type="button" class="glass" onClick={() => goTo(index - 1)} disabled={index === 0} aria-label="הווריאציה הקודמת">
              <IconRight />
            </button>
            <button type="button" class="glass" onClick={() => goTo(index + 1)} disabled={index === n - 1} aria-label="הווריאציה הבאה">
              <IconLeft />
            </button>
          </div>
          <button type="button" class="btn btn-primary" onClick={() => onChoose(index + 1)}>
            בחירה והצגה בחדר
          </button>
          {p ? (
            <>
              <button
                type="button"
                class="btn btn-ghost"
                disabled={cartBusy.value}
                onClick={() => void addToCart(p.variants[0]!.id, p.name_he, 1, pack, p.pack ? packLabelHe(pack, p.pack.set_qty) : undefined)}
              >
                הוספה לסל
              </button>
              <a class="btn btn-ghost" href={`/p/${p.id}/`}>
                לעמוד המוצר
              </a>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}
