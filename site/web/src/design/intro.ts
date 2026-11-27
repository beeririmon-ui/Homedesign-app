/**
 * MOCK9 (2026-11-27, FB19): the logo intro. On the first load of a session the wordmark appears in the middle, large
 * and quiet, over a veil; then it rises gently to its place in the header (the top right) and becomes the header's
 * wordmark, small. Once per session (sessionStorage; a browser without storage: once per load). With reduced motion
 * there is none: the wordmark is simply in the header. Decoration only (aria-hidden): the header's link is the same
 * throughout, and nothing under the veil is blocked (it takes no pointer). Behind HD_PUBLIC=0, in a design direction.
 * A press, a key or a scroll during it plays the rest quickly.
 */
import './intro.css';
import { BRAND_HE } from './Wordmark';
import { design } from './design';
import { prefersReducedMotion, timeScale } from '../motion';

const KEY = 'hd-intro';
declare global {
  interface Window {
    /** the tests' view of the intro: playing, done, or none this load */
    __hdIntro?: 'playing' | 'done' | 'none';
  }
}

/** whether this load plays the intro (decided once, before the first render: the header's wordmark waits for it) */
export function introWanted(): boolean {
  if (typeof __TOUR__ === 'undefined' || !__TOUR__ || !design || prefersReducedMotion()) return false;
  try {
    if (sessionStorage.getItem(KEY)) return false;
    sessionStorage.setItem(KEY, '1');
  } catch {
    // no storage: once per load
  }
  return true;
}

const EASE_IN = 'cubic-bezier(0.16, 1, 0.3, 1)';
const EASE_MOVE = 'cubic-bezier(0.65, 0, 0.25, 1)';

/** plays it; the page has rendered (the header's wordmark is where the mark goes) */
export async function playIntro(): Promise<void> {
  const html = document.documentElement;
  window.__hdIntro = 'playing';
  const k = timeScale();
  const root = document.createElement('div');
  root.className = 'intro';
  root.setAttribute('aria-hidden', 'true');
  root.innerHTML = `<div class="intro-veil"></div><div class="intro-mark"><span class="wordmark"></span><i class="intro-rule"></i></div>`;
  root.querySelector('.wordmark')!.textContent = BRAND_HE;
  document.body.appendChild(root);
  const veil = root.querySelector<HTMLElement>('.intro-veil')!;
  const mark = root.querySelector<HTMLElement>('.intro-mark')!;
  const word = root.querySelector<HTMLElement>('.wordmark')!;
  const rule = root.querySelector<HTMLElement>('.intro-rule')!;
  const anims: Animation[] = [];
  const go = (el: HTMLElement, frames: Keyframe[], ms: number, delay = 0, easing = EASE_IN) => {
    const a = el.animate(frames, { duration: ms * k, delay: delay * k, easing, fill: 'both' });
    anims.push(a);
    return a.finished.catch(() => undefined);
  };
  // a press, a key or a scroll: the rest plays quickly
  const hurry = () => anims.forEach((a) => (a.playbackRate = 4));
  const opts = { once: true, passive: true, capture: true } as const;
  addEventListener('pointerdown', hurry, opts);
  addEventListener('keydown', hurry, opts);
  addEventListener('wheel', hurry, opts);
  // the serif first (a second at most), so the mark is never drawn in a fallback face
  await Promise.race([document.fonts?.ready, new Promise((r) => setTimeout(r, 1200))]);
  // 1. the mark appears: it comes into focus and settles; the hairline draws under it
  void go(
    word,
    [
      { opacity: 0, transform: 'translateY(14px)', filter: 'blur(8px)' },
      { opacity: 1, transform: 'none', filter: 'blur(0)' },
    ],
    1100,
  );
  await go(rule, [{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }], 900, 450);
  await go(mark, [{ opacity: 1 }, { opacity: 1 }], 350);
  // 2. it rises to the header: the measured move from here to the header's wordmark, as one transform
  const to = document.querySelector<HTMLElement>('.site-header .brand .wordmark');
  const a = word.getBoundingClientRect();
  const b = to?.getBoundingClientRect();
  void go(rule, [{ opacity: 1 }, { opacity: 0 }], 360, 0, 'linear');
  void go(veil, [{ opacity: 1 }, { opacity: 0 }], 1000, 120, 'cubic-bezier(0.4, 0, 0.2, 1)');
  if (b && b.width > 0 && a.width > 0) {
    const s = parseFloat(getComputedStyle(to!).fontSize) / parseFloat(getComputedStyle(word).fontSize);
    const dx = b.left + b.width / 2 - (a.left + a.width / 2);
    const dy = b.top + b.height / 2 - (a.top + a.height / 2);
    await go(mark, [{ transform: 'none' }, { transform: `translate(${dx}px, ${dy}px) scale(${s})` }], 1150, 0, EASE_MOVE);
  } else await go(mark, [{ opacity: 1 }, { opacity: 0 }], 600, 0, 'linear');
  // 3. the header's own wordmark takes over where the mark stands, and the mark goes
  html.removeAttribute('data-intro');
  await go(word, [{ opacity: 1 }, { opacity: 0 }], 220, 0, 'linear');
  removeEventListener('pointerdown', hurry, opts);
  removeEventListener('keydown', hurry, opts);
  removeEventListener('wheel', hurry, opts);
  root.remove();
  window.__hdIntro = 'done';
}
