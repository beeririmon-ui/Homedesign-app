/**
 * The story layer's data file (data/story/story.json): its hotspot points are temporary, placed by eye, and checked here
 * for what can be checked without eyes (qa-agent verifies each point on the frame, G-ED.17): every pair names a listed
 * room and style, a frame with points is one QA let in, every starring product QA lists has a point, every point sits in
 * its own box on the frame, no two desktop targets overlap, and every product has the designer's name.
 */
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { repoPath } from '../lib/paths';
import { cardOf, registerReader, type QaState } from '../lib/qa-frames';

type Point = {
  product: string;
  u: number;
  v: number;
  box: [number, number, number, number];
  by_eye: boolean;
  option?: Record<string, string>;
  phone_at?: [number, number];
};
type Frame = { id: string; src: string; qa_key: string; title_he?: string; alt_he?: string; phone_crop_u?: number; points: Point[] };
const story = JSON.parse(readFileSync(repoPath('data/story/story.json'), 'utf8')) as {
  allowed_states: QaState[];
  rooms: { id: string }[];
  styles: { id: string }[];
  names_he: Record<string, string>;
  names_he_proposed: string[];
  pairs: Record<string, { concept_he: string; tool: string | null; frames: Frame[] }>;
};
const qaOf = registerReader().read;
/** every frame of every pair, by "room/style frame" */
const frames = Object.entries(story.pairs).flatMap(([key, p]) => p.frames.map((f) => [`${key} ${f.id}`, f] as const));
/** the frames with a hotspot map: the ones the pages show when QA lets them in */
const mapped = frames.filter(([, f]) => f.points.length > 0);
const walkPaths = (d: string): string[] => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walkPaths(join(d, n)) : [join(d, n)]));
// a card is known by its id (a file may be named otherwise, e.g. planter/zendrop-2784524.json)
const cards = new Set(
  walkPaths(repoPath('data/products'))
    .filter((n) => n.endsWith('.json'))
    .map((n) => (JSON.parse(readFileSync(n, 'utf8')) as { id?: string }).id ?? ''),
);

describe('the story data file', () => {
  it('declares every pair on a listed room and style, with its concept, and frames of unique ids that exist', () => {
    const rooms = new Set(story.rooms.map((r) => r.id));
    const styles = new Set(story.styles.map((s) => s.id));
    for (const [key, p] of Object.entries(story.pairs)) {
      const [room, style] = key.split('/');
      expect(rooms.has(room!) && styles.has(style!), key).toBe(true);
      expect(p.concept_he, key).toBeTruthy();
      expect(new Set(p.frames.map((f) => f.id)).size, key).toBe(p.frames.length);
      for (const f of p.frames) expect(existsSync(repoPath(f.src)), `${key} ${f.id}: ${f.src}`).toBe(true);
    }
  });

  it('marks every point temporary, by eye', () => {
    for (const [id, f] of mapped) for (const p of f.points) expect(p.by_eye, `${id}: ${p.product}`).toBe(true);
  });

  it('maps only frames the QA register knows (the gate holds the ones it does not let in), each with its title and alt text', () => {
    expect(mapped.length).toBeGreaterThan(0);
    for (const [id, f] of mapped) {
      const q = qaOf(f.qa_key);
      expect(q, `${id}: ${f.qa_key} is not in the register`).toBeTruthy();
      expect(f.title_he && f.alt_he, `${id}: title and alt`).toBeTruthy();
    }
  });

  it('has a point for every starring product QA lists in the frame, and every point is a product card', () => {
    for (const [id, f] of mapped) {
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
    for (const [id, f] of mapped)
      for (const p of f.points) {
        const [u0, u1, v0, v1] = p.box;
        expect(0 <= u0 && u0 < u1 && u1 <= 1 && 0 <= v0 && v0 < v1 && v1 <= 1, `${id}: ${p.product} box`).toBe(true);
        expect(u0 <= p.u && p.u <= u1 && v0 <= p.v && p.v <= v1, `${id}: ${p.product} point outside its box`).toBe(true);
        if (p.phone_at)
          expect(u0 <= p.phone_at[0] && p.phone_at[0] <= u1 && v0 <= p.phone_at[1] && p.phone_at[1] <= v1, `${id}: ${p.product} phone dot`).toBe(true);
      }
  });

  it('keeps every two 46 px desktop targets apart on the frame at 1280 × 720', () => {
    for (const [id, f] of mapped)
      for (const a of f.points)
        for (const b of f.points) {
          if (a === b) continue;
          const apart = Math.abs(a.u - b.u) * 1280 >= 48 || Math.abs(a.v - b.v) * 720 >= 48;
          expect(apart, `${id}: ${a.product} and ${b.product}`).toBe(true);
        }
  });

  it('names every product with the designer name (story-page design notes §4); a proposed name is listed as one', () => {
    for (const [id, f] of mapped) for (const p of f.points) expect(story.names_he[p.product], `${id}: ${p.product}`).toBeTruthy();
    for (const id of story.names_he_proposed) expect(story.names_he[id], id).toBeTruthy();
  });
});
