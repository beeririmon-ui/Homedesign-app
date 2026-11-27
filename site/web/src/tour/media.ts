/**
 * MOCK10 (2026-11-27, briefs/site-mock10-ui-polish-2026-11-27.md; FB26): no play icon, ever.
 *
 * The owner saw a play sign at the start of the preview. A <video> the page shows before it has a frame, or one whose
 * play() the browser refused, is drawn by the browser itself: Android's WebView (the in-app browsers) paints its default
 * poster, a grey play icon, on a video without a `poster`; WebKit draws its start button over a video that has not
 * played when inline playback is not allowed (an app's web view); and a browser that wants a gesture first (a web view,
 * iOS Low Power Mode, a data saver) refuses a play() that was not made inside one. So every video of the tour:
 *  - is muted, inline, without controls, picture-in-picture or remote playback, and has a poster that is its first
 *    frame (the page sets it); the stylesheet hides WebKit's own buttons (styles/tour.css);
 *  - is played through `play()` here: a refusal is kept, the video stays still on its frame (the page freezes what
 *    drives it, `blocked`), and the next gesture anywhere plays it, inside that gesture;
 *  - is unlocked by the first gesture on the page (a play() and a pause() inside it), so a later play() made from a
 *    frame callback is allowed even where every play() needs a gesture.
 * A stage attribute (`data-blocked`, through `onBlocked`) lets the page say "געו כדי להמשיך" while one waits.
 */
const tracked = new Set<HTMLVideoElement>();
const unlocked = new WeakSet<HTMLVideoElement>();
const waiting = new Set<HTMLVideoElement>();
let listener: ((blocked: boolean) => void) | null = null;
let armed = false;

declare global {
  interface Window {
    /** the tests' view: refused plays, videos unlocked by a gesture, and the ones waiting for one now */
    __hdMedia?: { refused: number; unlocked: number; waiting: number };
  }
}
const stats = () => (window.__hdMedia ??= { refused: 0, unlocked: 0, waiting: 0 });
const tell = () => {
  stats().waiting = waiting.size;
  listener?.(waiting.size > 0);
};

/** the page's stage attribute while a video waits for a gesture */
export function onBlocked(fn: ((blocked: boolean) => void) | null): void {
  listener = fn;
}

/** a video of the tour: its attributes, and the gesture that unlocks it */
export function track(v: HTMLVideoElement | null): void {
  if (!v || tracked.has(v)) return;
  tracked.add(v);
  v.controls = false;
  v.muted = true;
  v.defaultMuted = true;
  v.playsInline = true;
  v.disablePictureInPicture = true;
  v.disableRemotePlayback = true;
  // the attributes too: WebKit reads `playsinline` and `muted` from the element, some web views only the old prefix
  v.setAttribute('muted', '');
  v.setAttribute('playsinline', '');
  v.setAttribute('webkit-playsinline', '');
  v.setAttribute('disableremoteplayback', '');
  v.setAttribute('controlslist', 'nodownload nofullscreen noremoteplayback');
  arm();
}

/** whether this video's play was refused and it waits for a gesture (what drives it holds still meanwhile) */
export const blocked = (v: HTMLVideoElement): boolean => waiting.has(v);

/** plays a video that should be playing; a refusal keeps it still on its frame until the next gesture */
export function play(v: HTMLVideoElement): void {
  if (!v.paused || waiting.has(v)) return;
  let p: Promise<void> | undefined;
  try {
    p = v.play();
  } catch {
    p = undefined;
  }
  p?.then(
    () => {
      if (waiting.delete(v)) tell();
    },
    (err: unknown) => {
      // a pause() or a new source in between (AbortError) is the page's own doing, not a refusal
      if ((err as DOMException | null)?.name !== 'NotAllowedError') return;
      stats().refused++;
      waiting.add(v);
      tell();
    },
  );
}

/** a video that no longer needs to play (its stretch is over, or the page took it away) */
export function release(v: HTMLVideoElement): void {
  if (waiting.delete(v)) tell();
}

function gesture(): void {
  for (const v of tracked) {
    if (!v.isConnected) {
      tracked.delete(v);
      waiting.delete(v);
      continue;
    }
    if (waiting.has(v)) {
      // inside the gesture: this play is allowed, and it unlocks the element for the plays after it
      waiting.delete(v);
      unlocked.add(v);
      play(v);
      continue;
    }
    if (unlocked.has(v)) continue;
    unlocked.add(v);
    stats().unlocked++;
    if (!v.paused) continue;
    // a play and a pause in the same task: nothing is shown or moved, and the element may play later without a gesture
    try {
      const p = v.play();
      v.pause();
      p?.catch(() => undefined);
    } catch {
      // an element without a source: nothing to unlock yet
    }
  }
  tell();
}

function arm(): void {
  if (armed || typeof addEventListener === 'undefined') return;
  armed = true;
  // the events a browser counts as a user's activation (a scroll or a swipe is not one)
  const opts = { capture: true, passive: true } as const;
  for (const t of ['pointerdown', 'pointerup', 'touchend', 'click', 'keydown'] as const) addEventListener(t, gesture, opts);
}
