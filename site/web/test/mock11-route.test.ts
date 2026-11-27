/**
 * MOCK11 (2026-11-27, briefs/site-mock11-route-legs-2026-11-27.md): the real route legs, the pure parts.
 *
 *  1. every leg the config names is real (legs 1–5; leg 6 waits for the owner), from its manifest: the files' sizes,
 *     rates and ease frames; the wide screen's file at most 8 MB and the phone's at most 2.5 MB; a poster for each;
 *  2. the legs chain: a leg's last frame is the next leg's first (the room's display frame), as the manifests say;
 *  3. a jump through the real legs skips the ease frames between them; a leg without its clip stays in the trip (the
 *     page fades it through the light).
 */
import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { LEGS, legFile, span, trip } from '../src/tour/route';

const read = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8')) as T;
const cfg = read<{ order: string[]; legs: Record<string, string | null> }>('../../tools/tour/route.json');
type Manifest = {
  chain: { first_frame: string; last_frame: string; ease_in_frames: Record<string, [number, number]>; ease_out_frames: Record<string, [number, number]> };
  variants: Record<string, { w: number; h: number; frames: number; fps: number }>;
};
const dirs = Object.values(cfg.legs);
const manifest = (i: number) => read<Manifest>(`../../../${dirs[i]}/manifest.json`);

describe('MOCK11: the real route legs', () => {
  it('legs 1–5 are real; each is its manifest, within the size limits, with a poster', () => {
    expect(['leg1', 'leg2', 'leg3', 'leg4', 'leg5'].filter((id) => !LEGS.find((l) => l.id === id)?.real)).toEqual([]);
    LEGS.forEach((l, i) => {
      if (!dirs[i]) return expect(l.real).toBeNull();
      const m = manifest(i);
      expect(dirs[i]).toBe(`assets/video/transitions/warm-modern/route-fb21/leg${i + 1}/final`);
      for (const [k, key] of [
        ['desktop', '1920'],
        ['phone', '1080'],
      ] as const) {
        const v = l.real![k];
        expect(v).toMatchObject({ w: m.variants[key]!.w, h: m.variants[key]!.h, fps: m.variants[key]!.fps, frames: m.variants[key]!.frames });
        expect(v.ease_in).toEqual(m.chain.ease_in_frames[key]);
        expect(v.ease_out).toEqual(m.chain.ease_out_frames[key]);
        expect(v.src).toBe(`tour/route/${l.id}.${key}.${v.fps}.mp4`);
        expect(existsSync(new URL(`../public/media/${v.poster}`, import.meta.url))).toBe(true);
      }
      expect(l.real!.desktop.bytes).toBeLessThanOrEqual(8 * 1048576);
      expect(l.real!.phone.bytes).toBeLessThanOrEqual(2.5 * 1048576);
    });
  });

  it('the legs chain: each one’s last frame is the next one’s first, the room’s display frame', () => {
    for (let i = 0; i + 1 < dirs.length; i++) {
      if (!dirs[i] || !dirs[i + 1]) continue;
      expect(manifest(i).chain.last_frame, `leg${i + 1} → leg${i + 2}`).toBe(manifest(i + 1).chain.first_frame);
    }
  });

  it('a jump through real legs skips the ease frames between them; a leg without its clip stays in the trip', () => {
    const t = trip('dining', 'girl');
    if (t.kind !== 'ahead') throw new Error('ahead');
    expect(t.rate).toBe(3);
    expect(t.hops.map((h) => h.leg.id)).toEqual(['leg2', 'leg3', 'leg4', 'leg5']);
    const v2 = legFile(t.hops[0]!.leg, 1280)!;
    expect(span(v2, t.hops[0]!)).toEqual({ start: 0, end: (v2.ease_out[0] - 2) / 60 });
    const v5 = legFile(t.hops[3]!.leg, 1280)!;
    expect(span(v5, t.hops[3]!)).toEqual({ start: v5.ease_in[1] / 60, end: (v5.frames - 1) / 60 });
    // the last leg waits for its clip (an owner's decision): one station of it is a trip with no file
    const w = trip('girl', 'work');
    if (w.kind !== 'ahead') throw new Error('ahead');
    expect(w.hops.map((h) => legFile(h.leg, 1280))).toEqual([null]);
  });
});
