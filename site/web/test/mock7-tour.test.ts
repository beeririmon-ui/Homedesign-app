/**
 * MOCK7 (2026-11-26, briefs/site-mock7-tour-transitions-2026-11-26.md and the coordinator's update): the full tour in
 * design C, with the walks between rooms in code.
 *
 *  - the living room is M0-W (tools/tour/living-room-m0w.warm-modern.json, tools/make-tour-room.ts): its own camera
 *    (35 mm), its lights on lossy pages, no wheel, no style change, and none of the old phase 2 files;
 *  - every room has a depth for the push, and the rooms follow the house route;
 *  - the push's geometry (web/src/tour/push.ts): the turn's side, the point walked toward, the still's map;
 *  - the arrival stops in the hall before the old table enters the opening;
 *  - design C is the preview's default, and ?design=0 keeps the look before FB13.
 */
import { readFileSync } from 'node:fs';
import { beforeAll, describe, expect, it } from 'vitest';
import { coverMap, pushGeometry, type PushCamera } from '../src/tour/push';

const read = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8')) as T;
type Room = {
  room: string;
  frame?: string;
  source: string;
  styles?: boolean;
  sample?: string;
  depth?: string | null;
  camera: PushCamera & { ky: number };
  atlas?: Record<string, { product: { src: string }[]; shadow: { src: string }[] }>;
  lights?: unknown[];
  slots: { id: string; options: { product_id: string | null; price_agorot: number | null }[] }[];
};
const frames = read<{ living_room: string; rooms: { id: string; frames: string[] }[] }>('../../tools/tour/frames.json');
const room = (id: string) => read<Room>(`../../.generated/tour.${id}.warm-modern.json`);
const living = room('living-room');

describe('MOCK7: the living room is M0-W', () => {
  it('built from the new folder by the rooms’ tool, with its own camera (35 mm at 1.05 m)', () => {
    expect(frames.living_room).toBe('living-room-m0w');
    expect(living.source).toBe('wm-living-room-m0w-fb13-stage-a-2026-11-26');
    expect(living.frame).toBe('M0-W');
    expect(living.camera.loc).toEqual([0.95, 5.55, 1.05]);
    expect(living.camera.yaw_deg_left).toBe(14);
    // the plan's 24 mm projection scaled by the lens
    expect(living.camera.kx).toBeCloseTo((0.6667 * 35) / 24, 3);
    expect(living.atlas).toBeTruthy();
  });

  it('13 products, the coffee table among them and not sold yet; no wheel and no style change', () => {
    expect(living.slots.map((s) => s.id).sort()).toEqual(
      [
        'accent-sconces',
        'basket',
        'bowl',
        'candle-holders',
        'coffee-table',
        'cushions',
        'floor-lamp',
        'framed-art',
        'magazine-holder',
        'pendant',
        'planter',
        'rug',
        'vase',
      ].sort(),
    );
    const table = living.slots.find((s) => s.id === 'coffee-table')!;
    expect(table.options).toHaveLength(1);
    expect(table.options[0]!.product_id).toBeNull();
    expect(table.options[0]!.price_agorot).toBeNull();
    expect(living.sample).toBeUndefined();
    expect(living.slots.every((s) => s.options.length === 1)).toBe(true);
    expect(living.styles).toBe(false);
  });

  it('nothing of the old room: no phase 2 file, and the pin is M0-W’s', () => {
    const pin = read<{ manifest: string; hash: string; files: Record<string, string> }>('../../tools/tour/living-room.pin.json');
    expect(pin.manifest).toBe('assets/renders/living-room/warm-modern/fb13-2026-11-25/layers/manifest.json');
    expect(pin.hash).toBe('sha256');
    expect(Object.keys(pin.files).every((f) => f.startsWith('assets/renders/living-room/warm-modern/fb13-2026-11-25/'))).toBe(true);
    const text = JSON.stringify(living);
    expect(text).not.toMatch(/phase2-2026-11-10|pilot-phase1|base\.png|manifest-r9|M0\/slots/);
    // the rollback stays one line away, pinned to its own files
    const p2 = read<{ manifest: string }>('../../tools/tour/living-room.warm-modern.json');
    expect(p2.manifest).toBe('assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/manifest-basket.json');
  });
});

describe('MOCK7: the rooms, their depth and their order', () => {
  it('the route’s order: the living room, the kitchen, the boy, the girl, the bath (B1 first), the bedroom, the work room', () => {
    expect(frames.rooms.map((r) => r.id)).toEqual(['dining', 'boy', 'girl', 'bath', 'master', 'work']);
    expect(frames.rooms.find((r) => r.id === 'bath')!.frames).toEqual(['bath-b1', 'bath']);
  });

  it('every frame has a depth map for the push (a small inlined picture)', () => {
    for (const id of ['living-room', ...frames.rooms.flatMap((r) => r.frames)]) {
      const r = room(id);
      expect(r.depth, id).toMatch(/^data:image\/webp;base64,/);
      expect(r.depth!.length, id).toBeLessThan(16_000);
    }
  });

  it('the FB15 rooms are built from their -fb15 manifests', () => {
    for (const id of ['boy', 'girl', 'bath-b1', 'dining', 'dining-d2', 'master', 'master-mb1', 'work']) {
      const cfg = read<{ manifest: string; truth: string; gate?: { kind: string } }>(`../../tools/tour/${id}.warm-modern.json`);
      expect(cfg.manifest, id).toMatch(/fb15\.json$/);
      expect(cfg.truth, id).toMatch(/fb15\.png$/);
      expect(cfg.gate?.kind, id).toBe('finish');
    }
  });
});

describe('MOCK7: the push between rooms (web/src/tour/push.ts)', () => {
  const cam = (loc: number[], yaw: number): PushCamera => ({ frame: [0, 1, 0, 1], u0: 0.5, v0: 0.5, kx: 0.6667, loc, yaw_deg_left: yaw });
  it('a room ahead is walked toward where it stands in the frame', () => {
    // yaw 0 looks toward −y; a camera 3 m ahead and 1 m to the right
    const g = pushGeometry(cam([0, 0, 1.2], 0), cam([1, -3, 1.2], 0));
    expect(g.dir).toBe(0);
    expect(g.fa[0]).toBeCloseTo(0.5 + 0.6667 / 3, 3);
    expect(g.fb).toEqual([0.5, 0.5]);
  });
  it('a turn to the right moves the picture left (dir > 0); to the left, dir < 0; behind: toward the turn’s side', () => {
    expect(pushGeometry(cam([0, 0, 1], 25), cam([0, -3, 1], -35)).dir).toBeCloseTo(60 / 90, 3);
    expect(pushGeometry(cam([0, 0, 1], 0), cam([0, -3, 1], 45)).dir).toBeCloseTo(-0.5, 3);
    const back = pushGeometry(cam([0, 0, 1], 0), cam([0, 4, 1], -170));
    expect(back.dir).toBe(1);
    expect(back.fa[0]).toBeCloseTo(0.84, 3);
  });
  it('the still’s map is object-fit: cover at its object-position', () => {
    // a 16:9 video in a 16:9 window: the identity in UV
    const [sx, sy, ox, oy] = coverMap(1920, 1080, 960, 540, 0.5);
    expect([960 * sx + ox, 540 * sy + oy]).toEqual([1, 1]);
    expect([ox, oy]).toEqual([-0, -0]);
    // a phone in portrait shows the part of the frame at its position
    const m = coverMap(1080, 608, 400, 800, 0.3);
    const left = 0 * m[0] + m[2];
    const right = 400 * m[0] + m[2];
    expect(left).toBeGreaterThan(0);
    expect(right).toBeLessThan(1);
    expect(left / (1 - (right - left))).toBeCloseTo(0.3, 5);
  });
});

describe('MOCK7: the arrival stops in the hall', () => {
  it('at frame 490 of the walk (the old table enters the opening at 493), with its camera for the push', () => {
    const a = read<{ land: { frame: number; cam: number[] }; videos: Record<string, { frames: number }> }>('../../.generated/arrival.json');
    expect(a.land.frame).toBe(490);
    expect(a.land.cam).toHaveLength(6);
    expect(a.videos.desktop!.frames).toBe(490);
    expect(a.videos.phone!.frames).toBe(245);
  });
});

describe('MOCK7: design C is the preview’s default', () => {
  const load = async (search: string, stored: string | null = null) => {
    const store = new Map<string, string>(stored ? [['hd-design', stored]] : []);
    Object.assign(globalThis, {
      __TOUR__: true,
      location: { search },
      sessionStorage: {
        getItem: (k: string) => store.get(k) ?? null,
        setItem: (k: string, v: string) => void store.set(k, v),
        removeItem: (k: string) => void store.delete(k),
      },
    });
    const { vi } = await import('vitest');
    vi.resetModules();
    const m = await import('../src/design/design');
    return { design: m.design, stored: store.get('hd-design') ?? null };
  };
  beforeAll(() => undefined);
  it('no flag: C', async () => expect((await load('')).design).toBe('c'));
  it('?design=a|b: that one, kept for the tab', async () => expect(await load('?design=b')).toEqual({ design: 'b', stored: 'b' }));
  it('?design=0: the look before FB13, kept for the tab', async () => {
    expect(await load('?design=0')).toEqual({ design: null, stored: '0' });
    expect((await load('', '0')).design).toBeNull();
  });
});
