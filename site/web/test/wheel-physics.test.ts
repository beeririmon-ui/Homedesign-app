/**
 * The variant arc's spring (web/src/engine/wheel-physics.ts), stepped by real time (QA on S4): at 12 frames a second
 * it settles as fast as at 60, and a long pause does not throw it past its target.
 */
import { describe, expect, it } from 'vitest';
import { ArcPhysics } from '../src/engine/wheel-physics';

const settleTime = (fps: number) => {
  const p = new ArcPhysics(3);
  p.setIndex(0);
  p.goTo(2);
  let t = 0;
  while (p.step(1 / fps)) {
    t += 1 / fps;
    if (t > 10) break;
  }
  return { t, pos: p.pos };
};

describe('the variant arc spring', () => {
  it('settles on its target in about the same real time at 12 and at 60 frames a second', () => {
    const slow = settleTime(12);
    const fast = settleTime(60);
    expect(slow.pos).toBe(2);
    expect(fast.pos).toBe(2);
    expect(fast.t).toBeLessThan(1.5);
    expect(Math.abs(slow.t - fast.t)).toBeLessThan(0.2);
  });

  it('a long pause (a background tab) counts as a quarter second, and never overshoots past the ends', () => {
    const p = new ArcPhysics(3);
    p.setIndex(0);
    p.goTo(2);
    p.step(5);
    expect(p.pos).toBeGreaterThan(0);
    expect(p.pos).toBeLessThanOrEqual(2.05);
  });

  it('release picks where the inertia will land, so the option can be chosen at once', () => {
    const p = new ArcPhysics(3, 100);
    p.setIndex(0);
    p.startDrag(0);
    p.drag(60, 16);
    p.drag(60, 32);
    expect(p.release()).toBeGreaterThanOrEqual(1);
  });
});
