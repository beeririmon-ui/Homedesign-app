/**
 * The room stage: poster (prerendered, no-JS and LCP) → WebGL composition on top, real <button> hotspots
 * positioned from frame coordinates, horizontal pan on narrow screens, zoom with parallax into the variant wheel.
 */
import { useEffect, useRef, useState } from 'preact/hooks';
import type { CatalogRoom, CatalogSlot } from '@hd/shared';
import { catalog, defaultSelection, product, scene } from '../catalog';
import { RoomEngine } from '../engine/engine';
import { coverSize, defaultCam, frameToScreen } from '../engine/camera';
import { slotSources } from '../engine/layers';
import { mediaUrl, supportsAvif } from '../media';
import { Picture } from './Media';
import { VariantWheel } from './VariantWheel';
import { IconDoor, IconLeft, IconRight } from './Icons';
import { arrival, pendingOpen, roomReady, selection, stageEngine } from '../state/room';
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

  const [placed, setPlaced] = useState(false);
  const starting = useRef<Promise<RoomEngine | null> | null>(null);

  /** Hotspot positions: from the engine's camera once it runs, before that from the same camera math on the poster. */
  function placeHotspots() {
    const e = engine.current;
    const c = canvas.current;
    if (!c) return;
    const vp = e?.vp ?? { w: Math.max(1, c.clientWidth), h: Math.max(1, c.clientHeight) };
    const cam = e?.cam ?? defaultCam(vp, scene.aspect, scene.mobile_center_u);
    // the poster under the canvas follows the same camera, so the engine fades in without a shift
    const img = poster.current;
    if (img && cam.z < 1.001) {
      const { fw, fh } = coverSize(vp, scene.aspect);
      img.style.objectPosition = `${(vp.w / 2 - cam.cu * fw).toFixed(1)}px ${(vp.h / 2 - cam.cv * fh).toFixed(1)}px`;
    }
    const pts: { el: HTMLButtonElement; x: number; y: number; rx: number; ry: number }[] = [];
    for (const s of room.slots) {
      const el = spots.current.get(s.id);
      if (!el || !s.hotspot || !s.hotspot.visible) continue;
      const ring = ringOf(s);
      const c = frameToScreen(ring.cu, ring.cv, cam, vp, scene.aspect);
      const { fw, fh } = coverSize(vp, scene.aspect);
      pts.push({ el, ...c, ...ringRadii(ring.ru * fw * cam.z, ring.rv * fh * cam.z) });
    }
    // keep the centres of neighbouring rings apart (each target is at least 44 px, WCAG 2.5.8): a few relaxation passes
    const MIN = 48;
    for (let pass = 0; pass < 4; pass++)
      for (let i = 0; i < pts.length; i++)
        for (let j = i + 1; j < pts.length; j++) {
          const a = pts[i]!;
          const b = pts[j]!;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const d = Math.hypot(dx, dy);
          if (d >= MIN) continue;
          const k = (MIN - d) / 2 / (d || 1);
          const [ux, uy] = d ? [dx * k, dy * k] : [MIN / 2, 0];
          a.x -= ux;
          a.y -= uy;
          b.x += ux;
          b.y += uy;
        }
    // smaller rings sit above larger ones, so every product stays reachable where rings overlap
    const order = [...pts].sort((a, b) => b.rx * b.ry - a.rx * a.ry);
    order.forEach((p, i) => (p.el.style.zIndex = String(i + 1)));
    // keep targets clear of the controls on the stage (style switch, pan, back to the hall, the room label)
    const sr = stage.current?.getBoundingClientRect();
    const blocked = sr
      ? [...stage.current!.querySelectorAll<HTMLElement>('.stage-ui .glass, .stage-temp-note')].map((c) => {
          const r = c.getBoundingClientRect();
          return { l: r.left - sr.left - 26, r: r.right - sr.left + 26, t: r.top - sr.top - 26, b: r.bottom - sr.top + 26 };
        })
      : [];
    for (const { el, x, y, rx, ry } of pts) {
      const inside = x > 8 && x < vp.w - 8 && y > 8 && y < vp.h - 8 && !blocked.some((b) => x > b.l && x < b.r && y > b.t && y < b.b);
      el.style.width = `${(2 * rx).toFixed(1)}px`;
      el.style.height = `${(2 * ry).toFixed(1)}px`;
      el.style.transform = `translate(${(x - rx).toFixed(1)}px, ${(y - ry).toFixed(1)}px)`;
      el.style.visibility = inside ? 'visible' : 'hidden';
    }
    setCanPan(vp.w < vp.h * scene.aspect - 1);
    setPlaced(true);
  }

  /**
   * The WebGL engine starts on the first sign of intent (pointer over or on the stage, focus inside it, a hotspot,
   * a pending "show in room"), not on page load: until then the prerendered poster is the same default composition,
   * so the first paint costs no GPU work and no main-thread time (Lighthouse mobile ≥ 90).
   */
  function ensureEngine(): Promise<RoomEngine | null> {
    if (starting.current) return starting.current;
    if (!canvas.current) return Promise.resolve(null);
    window.__hdFrames = window.__hdFrames ?? [];
    const e = new RoomEngine({
      canvas: canvas.current,
      scene,
      room,
      selection: selection.value,
      reduceMotion: prefersReducedMotion(),
      poster: poster.current,
      onCamera: placeHotspots,
      onFrame: (dt) => window.__hdFrames?.push(dt),
      onReady: () => {
        setReady(true);
        stageEngine.value = e;
        placeHotspots();
      },
    });
    engine.current = e;
    window.__hdEngine = e;
    e.observe();
    starting.current = e.start().then(() => (engine.current === e ? e : null));
    return starting.current;
  }

  useEffect(() => {
    const c = canvas.current;
    if (!c) return;
    placeHotspots();
    roomReady.value = true;
    const ro = new ResizeObserver(() => !engine.current && placeHotspots());
    ro.observe(c);
    // a selection that differs from the poster (changed earlier in this visit) needs the engine right away
    const def = defaultSelection(room);
    // and so does an arriving transition: it lands on the composed room, not on the poster
    if (arrival.value || Object.entries(selection.value).some(([k, v]) => def[k] !== v)) void ensureEngine();
    // after the room is shown: the only reachable transition (back to the hall), then the variant layers (HTTP cache)
    let idle = 0;
    const later = () => {
      idle = requestIdleCallbackSafe(() => {
        preload('T-E0');
        prefetchVariants(room);
      });
    };
    // only after the page has fully loaded, so background bytes never compete with the first paint
    if (document.readyState === 'complete') later();
    else addEventListener('load', later, { once: true });
    return () => {
      ro.disconnect();
      removeEventListener('load', later);
      cancelIdle(idle);
      engine.current?.destroy();
      engine.current = null;
      stageEngine.value = null;
      starting.current = null;
      roomReady.value = false;
    };
  }, [room.id]);

  // rings and controls wait until the arrival has landed
  const arriving = arrival.value !== null;
  useEffect(() => {
    stage.current?.classList.toggle('arriving', arriving);
    if (!arriving) placeHotspots();
  }, [arriving]);

  // "הצגה בחדר" from a product page, or "החלפה" in the list under the stage
  const pending = pendingOpen.value;
  useEffect(() => {
    if (!placed || !pending) return;
    pendingOpen.value = null;
    const s = room.slots.find((x) => x.id === pending.slot);
    if (s) void openSlot(s, pending.option);
  }, [placed, pending]);

  async function openSlot(slot: CatalogSlot, previewOption?: number) {
    if (busy || open) return;
    setBusy(true);
    opener.current = document.activeElement as HTMLElement | null;
    const e = await ensureEngine();
    if (!e) return setBusy(false);
    const before = selection.value[slot.id] ?? 1;
    const zoom = slot.zoom_frame ?? [0.3, 0.7, 0.3, 0.7];
    // the touched product keeps its glow while the rings fade out and the camera moves in
    spots.current.get(slot.id)?.setAttribute('data-active', 'true');
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
    spots.current.get(o.slot.id)?.removeAttribute('data-active');
    stage.current?.classList.remove('zoomed');
    setBusy(false);
    if (chosen) {
      const pos = selection.value[o.slot.id] ?? 1;
      const p = product(o.slot.options[pos - 1]?.product_id);
      announce(`${o.slot.name_he}: ${p ? p.name_he : `וריאציה ${pos}`} מוצג בחדר`);
    }
    // focus returns after the re-render that re-enables the hotspots (a disabled button cannot take focus)
    focusAfter.current = spots.current.get(o.slot.id) ?? opener.current;
  }
  const focusAfter = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (busy || open || !focusAfter.current) return;
    focusAfter.current.focus({ preventScroll: true });
    focusAfter.current = null;
  }, [busy, open]);

  // horizontal pan (touch and mouse) on narrow screens; pointer drift on desktop
  const panState = useRef<{ x: number; id: number; moved: number } | null>(null);
  function onPointerDown(ev: PointerEvent) {
    void ensureEngine();
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
  const panBy = (dx: number) => void ensureEngine().then((e) => e?.panBy(dx));

  const styles = catalog.styles;
  return (
    <section
      class="stage"
      ref={stage}
      style={{ '--cu': String(scene.mobile_center_u) }}
      aria-labelledby="room-title"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <Picture
        src={scene.base[0]!.src}
        widths={scene.base[0]!.widths}
        sizes="(max-aspect-ratio: 1/1) min(calc((100svh - 60px) * 1.78), 1080px), 100vw"
        alt=""
        class="poster"
        loading="eager"
        fetchpriority="high"
        imgRef={poster}
      />
      {/* the composed room is a picture, not a control: the hotspot buttons and the list below are the interactive parts */}
      <canvas
        ref={canvas}
        class="room-canvas"
        // eslint-disable-next-line jsx-a11y/no-interactive-element-to-noninteractive-role
        role="img"
        aria-label={`${room.name_he} בסגנון נורדי: ספה בכיסוי בהיר, שולחן קפה מאלון, כורסה ליד החלון ועץ זית בפינה. ${room.slots.length} פריטים לבחירה, ברשימה שמתחת לחדר ובנקודות על התמונה.`}
        style={{ opacity: ready ? 1 : 0, transition: arriving ? 'none' : 'opacity .5s' }}
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
              hidden={!placed || !s.hotspot.visible}
              ref={(el) => {
                if (el) spots.current.set(s.id, el);
              }}
              style={{ left: 0, top: 0 }}
              aria-label={`${s.name_he}: ${p ? p.name_he : 'וריאציה זמנית'}. פתיחת ${s.options.length} וריאציות`}
              onClick={() => void openSlot(s)}
              disabled={busy}
              aria-busy={busy && !ready ? 'true' : undefined}
            >
              <span class="ring" aria-hidden="true" />
              <span class="tag" aria-hidden="true">
                {s.name_he}
              </span>
            </button>
          );
        })}
      </div>
      {!placed ? (
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

/**
 * The ring around a product, in frame coordinates: the product's own box from the scene (for split products such as
 * the curtains or the sconce pair, the part the zoom shows), else a small circle at the hotspot.
 */
function ringOf(s: CatalogSlot): { cu: number; cv: number; ru: number; rv: number } {
  const b = scene.slots[s.id]?.ring;
  if (b) return { cu: (b[0] + b[1]) / 2, cv: (b[2] + b[3]) / 2, ru: (b[1] - b[0]) / 2, rv: (b[3] - b[2]) / 2 };
  return { cu: s.hotspot!.u, cv: s.hotspot!.v, ru: 0.02, rv: 0.035 };
}

/** Screen radii of a ring: just outside the product (an ellipse around a box needs ×√2), a 44 px target at least, capped. */
function ringRadii(halfW: number, halfH: number): { rx: number; ry: number } {
  let rx = Math.min(150, Math.max(22, halfW * 1.3 + 4));
  let ry = Math.min(150, Math.max(22, halfH * 1.3 + 4));
  if (rx > ry * 1.8) ry = rx / 1.8;
  if (ry > rx * 1.8) rx = ry / 1.8;
  return { rx, ry };
}

function requestIdleCallbackSafe(fn: () => void): number {
  if (typeof requestIdleCallback === 'function') return requestIdleCallback(fn, { timeout: 4000 });
  return setTimeout(fn, 1500) as unknown as number;
}
function cancelIdle(id: number): void {
  if (typeof cancelIdleCallback === 'function') cancelIdleCallback(id);
  clearTimeout(id);
}

/** Warms the HTTP cache with every variant layer (fetch only: decoding and GPU upload happen when the engine needs them). */
function prefetchVariants(room: CatalogRoom): void {
  const w = innerWidth <= 900 ? scene.widths.lo : scene.widths.hi;
  const ext = scene.formats.includes('avif') && !__ARTIFACT__ ? null : 'webp';
  void supportsAvif().then((avif) => {
    for (const s of room.slots)
      for (const src of slotSources(scene, s.id))
        void fetch(mediaUrl(src, w, ext ?? (avif ? 'avif' : 'webp')), { priority: 'low' } as RequestInit).catch(() => undefined);
  });
}
