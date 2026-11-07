/**
 * The story prototype's hotspot map (tools/test-page/story-hotspots.json): temporary points placed by eye, checked here
 * for what can be checked without eyes (qa-agent verifies each point on the frame, G-ED.17): the frames are the ones QA
 * let in, every starring product QA lists has a point, every point sits in its own box on the frame, and no two desktop
 * targets overlap.
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { repoPath, sitePath } from '../lib/paths';
import { cardOf, qaReader, type QaState } from '../lib/qa-frames';

type Point = {
  product: string;
  u: number;
  v: number;
  box: [number, number, number, number];
  by_eye: boolean;
  option?: Record<string, string>;
  phone_at?: [number, number];
};
const hot = JSON.parse(readFileSync(sitePath('tools/test-page/story-hotspots.json'), 'utf8')) as {
  status: string;
  frames: Record<string, { src: string; qa_key: string; points: Point[] }>;
};
const story = JSON.parse(readFileSync(sitePath('tools/test-page/story.json'), 'utf8')) as {
  qa_records: string[];
  allowed_states: QaState[];
  names_he: Record<string, string>;
  frames: Record<string, { phone_crop_u: number; u0: number; v0: number }>;
};
const qaOf = qaReader(story.qa_records);
const walk = (d: string): string[] => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [n]));
const cards = new Set(
  walk(repoPath('data/products'))
    .filter((n) => n.endsWith('.json'))
    .map((n) => n.slice(0, -5)),
);

describe('the story hotspot map', () => {
  it('is marked temporary, by eye, point by point', () => {
    expect(hot.status).toBe('temporary-by-eye');
    for (const f of Object.values(hot.frames)) for (const p of f.points) expect(p.by_eye, p.product).toBe(true);
  });

  it('holds only the frames QA called final test or almost, and the same frames as the page manifest', () => {
    expect(Object.keys(hot.frames).sort()).toEqual(Object.keys(story.frames).sort());
    for (const [id, f] of Object.entries(hot.frames)) {
      expect(existsSync(repoPath(f.src)), f.src).toBe(true);
      const q = qaOf(f.qa_key);
      expect(q && story.allowed_states.includes(q.state), `${id}: ${q?.state ?? 'not in the QA records'}`).toBe(true);
    }
  });

  it('has a point for every starring product QA lists in the frame, and every point is a product card', () => {
    for (const [id, f] of Object.entries(hot.frames)) {
      const listed = qaOf(f.qa_key)!
        .rows.filter((r) => r.present && !r.card.startsWith('fixed furniture'))
        .map(cardOf);
      for (const c of listed)
        expect(
          f.points.some((p) => p.product === c),
          `${id}: ${c}`,
        ).toBe(true);
      for (const p of f.points) {
        expect(cards.has(p.product), `${id}: no card ${p.product}`).toBe(true);
        expect(listed, `${id}: ${p.product} is not in QA's table for the frame`).toContain(p.product);
      }
    }
  });

  it('puts every point inside its own box, inside the frame', () => {
    for (const [id, f] of Object.entries(hot.frames))
      for (const p of f.points) {
        const [u0, u1, v0, v1] = p.box;
        expect(0 <= u0 && u0 < u1 && u1 <= 1 && 0 <= v0 && v0 < v1 && v1 <= 1, `${id}: ${p.product} box`).toBe(true);
        expect(u0 <= p.u && p.u <= u1 && v0 <= p.v && p.v <= v1, `${id}: ${p.product} point outside its box`).toBe(true);
        if (p.phone_at)
          expect(u0 <= p.phone_at[0] && p.phone_at[0] <= u1 && v0 <= p.phone_at[1] && p.phone_at[1] <= v1, `${id}: ${p.product} phone dot`).toBe(true);
      }
  });

  it('keeps every two 46 px desktop targets apart on the frame at 1280 × 720', () => {
    for (const [id, f] of Object.entries(hot.frames))
      for (const a of f.points)
        for (const b of f.points) {
          if (a === b) continue;
          const apart = Math.abs(a.u - b.u) * 1280 >= 48 || Math.abs(a.v - b.v) * 720 >= 48;
          expect(apart, `${id}: ${a.product} and ${b.product}`).toBe(true);
        }
  });

  it('names every product with the designer name (story-page design notes §4)', () => {
    for (const f of Object.values(hot.frames)) for (const p of f.points) expect(story.names_he[p.product], p.product).toBeTruthy();
  });
});
