/**
 * The room stage: poster (prerendered, no-JS and LCP) → WebGL composition on top, real <button> hotspots
 * positioned from frame coordinates, horizontal pan on narrow screens, zoom with parallax into the variant wheel.
 */
import { useEffect, useRef, useState } from 'preact/hooks';
import type { CatalogRoom, CatalogSlot } from '@hd/shared';
import { catalog, product, scene } from '../catalog';
import { RoomEngine } from '../engine/engine';
import { Picture } from './Media';
import { VariantWheel } from './VariantWheel';
import { IconDoor, IconLeft, IconRight } from './Icons';
import { pendingOpen, roomReady, selection } from '../state/room';
import { announce } from '../state/ui';
import { prefersReducedMotion } from '../motion';
import { go, preload } from './Transition';

declare global {
  interface Window {
    __hdEngine?: RoomEngine;
    __hdFrames?: number[];
  }
}

export function RoomExperience({ room }: { room: CatalogRoom }) {
  const stage = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const poster = useRef<HTMLImageElement>(null);
  const engine = useRef<RoomEngine | null>(null);
  const spots = useRef(new Map<string, HTMLButtonElement>());
  const opener = useRef<HTMLElement | null>(null);
  const [ready, setReady] = useState(false);
  const [open, setOpen] = useState<{ slot: CatalogSlot; before: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [canPan, setCanPan] = useState(false);

  function placeHotspots() {
    const e = engine.current;
    if (!e) return;
    for (const s of room.slots) {
      const el = spots.current.get(s.id);
      if (!el || !s.hotspot) continue;
      const { x, y } = e.frameToScreen(s.hotspot.u, s.hotspot.v);
      const inside = x > 8 && x < e.vp.w - 8 && y > 8 && y < e.vp.h - 8;
      el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
      el.style.visibility = inside ? 'visible' : 'hidden';
    }
    setCanPan(e.vp.w < e.vp.h * scene.aspect - 1);
  }

  useEffect(() => {
    if (!canvas.current) return;
    const reduce = prefersReducedMotion();
    window.__hdFrames = [];
    const e = new RoomEngine({
      canvas: canvas.current,
      scene,
      room,
      selection: selection.value,
      reduceMotion: reduce,
      poster: poster.current,
      onCamera: placeHotspots,
      onFrame: (dt) => window.__hdFrames?.push(dt),
      onReady: () => {
        setReady(true);
        roomReady.value = true;
        placeHotspots();
        // the only transition reachable from here (back to the hall); kitchen-dining is not built yet
        requestIdleCallbackSafe(() => preload('T-E0'));
      },
    });
    engine.current = e;
    window.__hdEngine = e;
    e.observe();
    void e.start();
    return () => {
      e.destroy();
      engine.current = null;
      roomReady.value = false;
    };
  }, [room.id]);

  // "הצגה בחדר" from a product page, or "החלפה" in the list under the stage
  const pending = pendingOpen.value;
  useEffect(() => {
    if (!ready || !pending) return;
    pendingOpen.value = null;
    const s = room.slots.find((x) => x.id === pending.slot);
    if (s) void openSlot(s, pending.option);
  }, [ready, pending]);

  async function openSlot(slot: CatalogSlot, previewOption?: number) {
    const e = engine.current;
    if (!e || busy || open) return;
    setBusy(true);
    opener.current = document.activeElement as HTMLElement | null;
    const before = selection.value[slot.id] ?? 1;
    const zoom = slot.zoom_frame ?? [0.3, 0.7, 0.3, 0.7];
    stage.current?.classList.add('zoomed');
    await e.zoomToBox(zoom, scene.slots[slot.id]?.depth ?? 0.4, { durationMs: 1000, reserve: e.vp.h > 520 ? 0.44 : 0.36 });
    if (previewOption && previewOption !== before) await preview(slot, previewOption);
    setOpen({ slot, before });
    setBusy(false);
  }

  async function preview(slot: CatalogSlot, position: number) {
    selection.value = { ...selection.value, [slot.id]: position };
    await engine.current?.setSelection(slot.id, position, 300);
  }

  async function close(chosen: boolean) {
    const o = open;
    const e = engine.current;
    if (!o || !e) return;
    setOpen(null);
    setBusy(true);
    if (!chosen && selection.value[o.slot.id] !== o.before) await preview(o.slot, o.before);
    await e.zoomOut(1000);
    stage.current?.classList.remove('zoomed');
    setBusy(false);
    if (chosen) {
      const pos = selection.value[o.slot.id] ?? 1;
      const p = product(o.slot.options[pos - 1]?.product_id);
      announce(`${o.slot.name_he}: ${p ? p.name_he : `וריאציה ${pos}`} מוצג בחדר`);
    }
    (spots.current.get(o.slot.id) ?? opener.current)?.focus({ preventScroll: true });
  }

  // horizontal pan (touch and mouse) on narrow screens; pointer drift on desktop
  const panState = useRef<{ x: number; id: number; moved: number } | null>(null);
  function onPointerDown(ev: PointerEvent) {
    if (open || busy || (ev.target as Element).closest('button, a')) return;
    panState.current = { x: ev.clientX, id: ev.pointerId, moved: 0 };
  }
  function onPointerMove(ev: PointerEvent) {
    const e = engine.current;
    const p = panState.current;
    if (e && p && p.id === ev.pointerId) {
      const dx = ev.clientX - p.x;
      p.x = ev.clientX;
      p.moved += Math.abs(dx);
      if (p.moved > 4) e.panBy(dx);
    } else if (e && ev.pointerType === 'mouse' && !open) {
      const r = stage.current!.getBoundingClientRect();
      e.setDrift((ev.clientX - r.left) / r.width - 0.5, (ev.clientY - r.top) / r.height - 0.5);
    }
  }
  function onPointerUp() {
    panState.current = null;
  }
  const panBy = (dx: number) => engine.current?.panBy(dx);

  const styles = catalog.styles;
  return (
    <section class="stage" ref={stage} aria-labelledby="room-title" onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}>
      <Picture
        src={scene.base[0]!.src}
        widths={scene.base[0]!.widths}
        sizes="(max-aspect-ratio: 1/1) calc((100svh - 60px) * 1.78), 100vw"
        alt=""
        class="poster"
        loading="eager"
        fetchpriority="high"
        imgRef={poster}
      />
      <canvas
        ref={canvas}
        class="room-canvas"
        role="img"
        aria-label={`${room.name_he} בסגנון נורדי: ספה בכיסוי בהיר, שולחן קפה מאלון, כורסה ליד החלון ועץ זית בפינה. ${room.slots.length} פריטים לבחירה, ברשימה שמתחת לחדר ובנקודות על התמונה.`}
        style={{ opacity: ready ? 1 : 0, transition: 'opacity .5s' }}
      />
      <div class="stage-vignette" aria-hidden="true" />
      <h1 id="room-title" class="glass stage-temp-note" tabIndex={-1}>
        {room.name_he} · נורדי{scene.temporary ? ' · תמונות זמניות' : ''}
      </h1>
      <div class="hotspots" role="group" aria-label="פריטים בחדר">
        {room.slots.map((s) => {
          if (!s.hotspot) return null;
          const pos = selection.value[s.id] ?? 1;
          const p = product(s.options[pos - 1]?.product_id);
          return (
            <button
              key={s.id}
              type="button"
              class="hotspot"
              data-slot={s.id}
              data-temp={String(s.hotspot.provisional)}
              hidden={!ready || !s.hotspot.visible}
              ref={(el) => {
                if (el) spots.current.set(s.id, el);
              }}
              style={{ left: 0, top: 0 }}
              aria-label={`${s.name_he}: ${p ? p.name_he : 'וריאציה זמנית'}. פתיחת ${s.options.length} וריאציות`}
              onClick={() => void openSlot(s)}
              disabled={!ready || busy}
            >
              <span class="tag" aria-hidden="true">
                {s.name_he}
              </span>
            </button>
          );
        })}
      </div>
      {!ready ? (
        <p class="stage-loading" role="status">
          <span class="glass" style={{ padding: '8px 14px' }}>
            טוען את החדר…
          </span>
        </p>
      ) : null}
      <div class="stage-ui">
        <div class="glass segmented" role="group" aria-label="סגנון">
          {styles.map((s) => (
            <button
              key={s.id}
              type="button"
              aria-pressed={s.id === room.style}
              aria-disabled={!s.available}
              onClick={() => (s.available ? undefined : announce(`סגנון ${s.name_he} יגיע בהמשך`))}
            >
              {s.name_he}
              {!s.available ? <small>בקרוב</small> : null}
            </button>
          ))}
        </div>
        <div class="stage-actions">
          {canPan ? (
            <>
              <button type="button" class="glass glass-btn" onClick={() => panBy(120)} aria-label="הזזת המבט ימינה">
                <IconRight />
              </button>
              <button type="button" class="glass glass-btn" onClick={() => panBy(-120)} aria-label="הזזת המבט שמאלה">
                <IconLeft />
              </button>
            </>
          ) : null}
          <button type="button" class="glass glass-btn" onClick={() => go('T-E0', '/', true)}>
            <IconDoor />
            <span>לכניסה</span>
          </button>
        </div>
      </div>
      {open ? (
        <VariantWheel
          slot={open.slot}
          initial={selection.value[open.slot.id] ?? 1}
          onPreview={(pos) => void preview(open.slot, pos)}
          onChoose={() => void close(true)}
          onCancel={() => void close(false)}
        />
      ) : null}
    </section>
  );
}

function requestIdleCallbackSafe(fn: () => void): void {
  if ('requestIdleCallback' in window) window.requestIdleCallback(fn, { timeout: 4000 });
  else setTimeout(fn, 1500);
}
