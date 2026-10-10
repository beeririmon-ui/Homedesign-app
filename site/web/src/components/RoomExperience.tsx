/**
 * The room stage: poster (prerendered, no-JS and LCP) → WebGL composition on top, real <button> hotspots
 * positioned from frame coordinates, horizontal pan on narrow screens, zoom with parallax into the variant wheel.
 */
import { useEffect, useRef, useState } from 'preact/hooks';
import type { CatalogRoom, CatalogSlot } from '@hd/shared';
import { catalog, defaultSelection, product, scene } from '../catalog';
import { RoomEngine } from '../engine/engine';
import { coverSize, defaultCam, frameToScreen, screenToFrame } from '../engine/camera';
import { slotSources } from '../engine/layers';
import { mediaUrl } from '../media';
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
  const outlineSvg = useRef<SVGSVGElement>(null);
  const outlinePaths = useRef(new Map<string, SVGPathElement>());
  const lit = useRef<string | null>(null);
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
    const { fw, fh } = coverSize(vp, scene.aspect);
    // the outlines follow the same camera: the SVG is the whole frame, scaled and shifted like the picture
    const svg = outlineSvg.current;
    if (svg) {
      const o = frameToScreen(0, 0, cam, vp, scene.aspect);
      svg.style.width = `${(fw * cam.z).toFixed(1)}px`;
      svg.style.height = `${(fh * cam.z).toFixed(1)}px`;
      svg.style.transform = `translate(${o.x.toFixed(1)}px, ${o.y.toFixed(1)}px)`;
    }
    const pts: { el: HTMLButtonElement; x: number; y: number }[] = [];
    for (const s of room.slots) {
      const el = spots.current.get(s.id);
      if (!el || !s.hotspot || !s.hotspot.visible) continue;
      const [u, v] = anchorOf(s);
      pts.push({ el, ...frameToScreen(u, v, cam, vp, scene.aspect) });
    }
    // one mark per product, never overlapping: neighbouring 44 px targets (WCAG 2.5.8) are pushed apart a little
    const MIN = 48;
    for (let pass = 0; pass < 12; pass++)
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
    // keep targets clear of the controls on the stage (style switch, pan, back to the hall, the room label)
    const sr = stage.current?.getBoundingClientRect();
    const blocked = sr
      ? [...stage.current!.querySelectorAll<HTMLElement>('.stage-ui .glass, .stage-temp-note')].map((c) => {
          const r = c.getBoundingClientRect();
          return { l: r.left - sr.left - 22, r: r.right - sr.left + 22, t: r.top - sr.top - 22, b: r.bottom - sr.top + 22 };
        })
      : [];
    for (const { el, x, y } of pts) {
      const inside = x > 8 && x < vp.w - 8 && y > 8 && y < vp.h - 8 && !blocked.some((b) => x > b.l && x < b.r && y > b.t && y < b.b);
      el.style.transform = `translate(${(x - 23).toFixed(1)}px, ${(y - 23).toFixed(1)}px)`;
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
  /** Lights one product: its outline glows and its mark grows (hover, touch, keyboard focus). */
  function light(id: string | null) {
    if (lit.current === id) return;
    if (lit.current) {
      outlinePaths.current.get(lit.current)?.removeAttribute('data-on');
      spots.current.get(lit.current)?.removeAttribute('data-hover');
    }
    lit.current = id;
    if (id) {
      outlinePaths.current.get(id)?.setAttribute('data-on', 'true');
      spots.current.get(id)?.setAttribute('data-hover', 'true');
    }
  }

  /** The product under a point of the stage (its silhouette, frontmost first), for pointer hover and taps. */
  function slotAt(clientX: number, clientY: number): CatalogSlot | null {
    const c = canvas.current;
    if (!c) return null;
    const r = c.getBoundingClientRect();
    // until the engine has measured the stage, the poster's camera (the same math) is the truth
    const e = engine.current?.ready ? engine.current : null;
    const vp = e?.vp ?? { w: Math.max(1, c.clientWidth), h: Math.max(1, c.clientHeight) };
    const cam = e?.cam ?? defaultCam(vp, scene.aspect, scene.mobile_center_u);
    const { u, v } = screenToFrame(clientX - r.left, clientY - r.top, cam, vp, scene.aspect);
    for (let i = room.slots.length - 1; i >= 0; i--) {
      const s = room.slots[i]!;
      if (!s.hotspot?.visible) continue;
      if ((scene.slots[s.id]?.outline ?? []).some((poly) => inPolygon(u, v, poly))) return s;
    }
    return null;
  }

  // horizontal pan (touch and mouse) on narrow screens; pointer drift on desktop; hover and tap on a product itself
  const panState = useRef<{ x: number; id: number; moved: number; onControl: boolean } | null>(null);
  function onPointerDown(ev: PointerEvent) {
    void ensureEngine();
    if (open || busy) return;
    const onControl = !!(ev.target as Element).closest('button, a');
    panState.current = { x: ev.clientX, id: ev.pointerId, moved: 0, onControl };
    if (!onControl) light(slotAt(ev.clientX, ev.clientY)?.id ?? null);
  }
  function onPointerMove(ev: PointerEvent) {
    const e = engine.current;
    const p = panState.current;
    if (e && p && p.id === ev.pointerId && !p.onControl) {
      const dx = ev.clientX - p.x;
      p.x = ev.clientX;
      p.moved += Math.abs(dx);
      if (p.moved > 4) {
        light(null);
        e.panBy(dx);
      }
    } else if (ev.pointerType === 'mouse' && !open && !busy) {
      if (e) {
        const r = stage.current!.getBoundingClientRect();
        e.setDrift((ev.clientX - r.left) / r.width - 0.5, (ev.clientY - r.top) / r.height - 0.5);
      }
      if (!(ev.target as Element).closest('button, a')) {
        const hit = slotAt(ev.clientX, ev.clientY);
        light(hit?.id ?? null);
        if (hit) stage.current?.setAttribute('data-pointing', 'true');
        else stage.current?.removeAttribute('data-pointing');
      }
    }
  }
  function onPointerUp(ev: PointerEvent) {
    const p = panState.current;
    panState.current = null;
    // a tap or click on the product itself opens it, like its mark does (the mark stays the accessible control)
    if (p && !p.onControl && p.moved <= 4 && !open && !busy) {
      const hit = slotAt(ev.clientX, ev.clientY);
      if (hit) void openSlot(hit);
    }
    if (ev.pointerType !== 'mouse') light(null);
  }
  function onPointerLeave() {
    light(null);
    stage.current?.removeAttribute('data-pointing');
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
      onPointerLeave={onPointerLeave}
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
      <svg class="outlines" ref={outlineSvg} viewBox="0 0 1600 900" preserveAspectRatio="none" aria-hidden="true" focusable="false">
        {room.slots.map((s) => {
          const o = scene.slots[s.id]?.outline;
          return o?.length ? (
            <path
              key={s.id}
              data-slot={s.id}
              d={outlinePath(o)}
              ref={(el) => {
                if (el) outlinePaths.current.set(s.id, el);
              }}
            />
          ) : null;
        })}
      </svg>
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
              onPointerEnter={() => light(s.id)}
              onPointerLeave={() => light(null)}
              onFocus={() => light(s.id)}
              onBlur={() => light(null)}
              disabled={busy}
              aria-busy={busy && !ready ? 'true' : undefined}
            >
              <span class="mark" aria-hidden="true" />
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

/** Where a product's mark rests: the deepest point inside its silhouette (scene anchor), else the slot's hotspot. */
function anchorOf(s: CatalogSlot): [number, number] {
  return scene.slots[s.id]?.anchor ?? [s.hotspot!.u, s.hotspot!.v];
}

/** SVG path of a silhouette outline in the 1600 × 900 frame box. */
function outlinePath(polys: [number, number][][]): string {
  return polys.map((p) => `M${p.map(([u, v]) => `${(u * 1600).toFixed(1)} ${(v * 900).toFixed(1)}`).join('L')}Z`).join('');
}

/** Even-odd point-in-polygon test in frame coordinates. */
function inPolygon(u: number, v: number, poly: [number, number][]): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [ui, vi] = poly[i]!;
    const [uj, vj] = poly[j]!;
    if (vi > v !== vj > v && u < ((uj - ui) * (v - vi)) / (vj - vi) + ui) inside = !inside;
  }
  return inside;
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
  // layers are WebP only (lossless alpha)
  for (const s of room.slots)
    for (const src of slotSources(scene, s.id)) void fetch(mediaUrl(src, w, 'webp'), { priority: 'low' } as RequestInit).catch(() => undefined);
}
