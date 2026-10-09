/**
 * Room-to-room transition overlay. Starts with a short cross-fade from what is on screen to the first frame,
 * plays the frame sequence, then cross-fades into the destination room once it is composed.
 */
import { signal } from '@preact/signals';
import { useEffect, useRef } from 'preact/hooks';
import { scene } from '../catalog';
import { Loader } from '../engine/loader';
import { playSequence, preloadTransition } from '../engine/sequence';
import { navigate } from '../router';
import { roomReady } from '../state/room';
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

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function TransitionOverlay() {
  const ref = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const t = activeTransition.value;
  useEffect(() => {
    if (!t || !ref.current || !canvas.current) return;
    const el = ref.current;
    const def = scene.transitions[t.id]!;
    let cancelled = false;
    void (async () => {
      const frames = await preloadTransition(sharedLoader, def, 0);
      if (cancelled) return;
      el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 260, fill: 'forwards', easing: 'ease-out' });
      const playing = playSequence(canvas.current!, frames, { durationMs: (def.frames / def.fps) * 1000 * 1.25, reverse: t.reverse, centerU: scene.mobile_center_u });
      await wait(260);
      roomReady.value = false;
      await playing;
      navigate(t.to);
      const t0 = performance.now();
      while (!roomReady.value && performance.now() - t0 < 2500 && t.to.startsWith('/rooms/')) await wait(40);
      await el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 420, fill: 'forwards', easing: 'ease-in-out' }).finished;
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
