/**
 * Room-to-room transition overlay (T-E0 today: hall → living room, and back).
 *
 * Into a room it is one continuous camera move, not a cut and not a zoom:
 *   1. a short cross-fade from what is on screen to the first frame;
 *   2. the walk: the frame sequence with a speed ramp (it accelerates and never slows down inside the footage),
 *      frame blending and a light motion trail; the room page mounts underneath and composes M0 meanwhile;
 *   3. the end lock: while the footage still moves, the overlay dissolves into the composed room, which the engine
 *      flies the last metre as a depth-parallax dolly (RoomEngine.arrive) and lands exactly on its rest camera.
 *      The final frame is the room itself, so there is no jump in position or scale at the end.
 * Leaving a room plays the same move backwards. With prefers-reduced-motion the router navigates directly.
 *
 * Temporary footage: the prototype walk-in ends in an older room (it does not end on M0), so the end lock dissolves
 * between two different pictures while both move. With the final T-E0 (last frame identical to M0) the same code
 * dissolves between identical pictures. See site/README.md, "מעבר T-E0".
 */
import { signal } from '@preact/signals';
import { useEffect, useRef } from 'preact/hooks';
import { scene } from '../catalog';
import { Loader } from '../engine/loader';
import { SequencePlayer, preloadTransition, tween } from '../engine/sequence';
import { easeInOutCubic, easeOutCubic } from '../engine/camera';
import { navigate } from '../router';
import { arrival, stageEngine } from '../state/room';
import { prefersReducedMotion } from '../motion';

export const sharedLoader = new Loader(4);
export const activeTransition = signal<{ id: string; reverse: boolean; to: string } | null>(null);

export function preload(id: string): void {
  const t = scene.transitions[id];
  if (t) void preloadTransition(sharedLoader, t).catch(() => undefined);
}

export function go(id: string, to: string, reverse = false): void {
  if (prefersReducedMotion() || !scene.transitions[id]) {
    navigate(to);
    return;
  }
  activeTransition.value = { id, reverse, to };
}

const nextFrame = () => new Promise<number>((r) => requestAnimationFrame(r));

/** Timings (ms). The walk is set by the footage length; the hand-off overlaps the engine's landing. */
const FADE_IN = 260;
const HANDOFF = 650; // overlay dissolves into the room
const LANDING = 1100; // engine dolly, starts with the hand-off
const ENGINE_WAIT = 3000; // longest we keep crawling while the room composes
const HAND_AT = 0.84; // fraction of the footage played at full motion before the hand-off

export function TransitionOverlay() {
  const ref = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const t = activeTransition.value;
  useEffect(() => {
    if (!t || !ref.current || !canvas.current) return;
    const el = ref.current;
    const def = scene.transitions[t.id]!;
    const toRoom = t.to.startsWith('/rooms/');
    let cancelled = false;
    const opacity = (v: number) => (el.style.opacity = v.toFixed(3));
    void (async () => {
      const frames = await preloadTransition(sharedLoader, def, 0);
      if (cancelled) return;
      const portrait = innerWidth / innerHeight < 1.1;
      const player = new SequencePlayer(canvas.current!, frames, portrait ? scene.mobile_center_u : 0.5);
      const last = player.length - 1;
      const hand = Math.round(last * HAND_AT);
      const frameMs = 1000 / def.fps;

      if (!t.reverse) {
        // 1. from the page to the first frame
        player.draw(0);
        await tween(FADE_IN, (k) => opacity(easeOutCubic(k)));
        if (toRoom) arrival.value = 'pending';
        navigate(t.to);
        // 2. the walk: speed ramp 0.65× → 1.35× of the footage rate, no deceleration before the hand-off
        let pos = 0;
        await tween(hand * frameMs * 1.05, (k) => {
          pos = (k - 0.35 * k * (1 - k)) * hand;
          const speed = 0.65 + 0.7 * k;
          player.draw(pos, { trail: 0.22 * speed });
        });
        // the room is still composing (slow network): keep moving, slowly, through the remaining footage
        const t0 = performance.now();
        while (toRoom && !stageEngine.value && performance.now() - t0 < ENGINE_WAIT && !cancelled) {
          pos = Math.min(last - 2, pos + 0.25);
          player.draw(pos, { trail: 0.15 });
          await nextFrame();
        }
        // 3. end lock: dissolve into the composed room while the engine lands the dolly on the rest camera
        const engine = toRoom ? stageEngine.value : null;
        if (engine) arrival.value = 'landing';
        const landing = engine?.arrive(LANDING) ?? Promise.resolve();
        const from = pos;
        await tween(HANDOFF, (k) => {
          const e = easeOutCubic(k);
          player.draw(from + (last - from) * e, { trail: 0.3 * (1 - k), push: 1 + 0.06 * e });
          opacity(1 - easeInOutCubic(k));
        });
        activeTransition.value = null;
        await landing;
        if (arrival.value) arrival.value = null;
        return;
      }

      // leaving a room: the engine pulls back (the arrival in reverse) while the footage fades in from its last frame
      const engine = stageEngine.value;
      const leaving = engine?.arrive(LANDING * 0.7, { reverse: true }) ?? Promise.resolve();
      let pos = last;
      await tween(HANDOFF, (k) => {
        const e = k * k;
        pos = last - (last - hand) * 0.25 * e;
        player.draw(pos, { trail: 0.3 * k, push: 1.06 - 0.06 * e });
        opacity(easeInOutCubic(k));
      });
      await leaving;
      navigate(t.to);
      const from = pos;
      // walk back out, decelerating into the hall
      await tween(from * frameMs * 1.05, (k) => {
        const e = easeOutCubic(k);
        player.draw(from * (1 - e), { trail: 0.25 * (1 - k) });
      });
      await tween(420, (k) => opacity(1 - easeInOutCubic(k)));
      activeTransition.value = null;
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);
  if (!t) return null;
  return (
    <div class="seq-overlay" ref={ref} style={{ opacity: 0 }} aria-hidden="true">
      <canvas ref={canvas} />
    </div>
  );
}
