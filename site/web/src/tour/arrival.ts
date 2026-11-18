/**
 * MOCK4 (2026-11-18): the arrival v2, from the door through the hall to the living room (motion-agent's QA-passed walk,
 * qa/reports/2026-11-18-arrival-v2), as tools/make-arrival.ts encodes it for the web. Route ch. 11.1 (FB7, FB8): one
 * flowing walk, always facing forward; at the one rest, on HC, the names land on the doors one after another (ARR-M1);
 * the first arrival has the labels and "דלג", and no buttons. The labels are drawn here, in HTML, over the clean walk:
 * each is a hairline along its door's lintel and the room's name, anchored to the lintel's 3D points through the
 * camera of the frame on screen (camera.json), so they turn with the camera.
 */
import data from '@generated/arrival.json';
import { MEDIA_BASE } from '../media';

export type ArrivalLabel = { id: string; name_he: string; pts: [[number, number, number], [number, number, number]]; u: [number, number] };
export type Arrival = {
  land_s: number;
  land_60: number;
  hc_60: number;
  rest_60: [number, number];
  videos: Record<'desktop' | 'phone', { src: string; w: number; h: number; fps: number; frames: number; bytes: number }>;
  door: { src: string; widths: number[] };
  hc: { src: string; width: number };
  proj: { kx: number; ky: number };
  labels: ArrivalLabel[];
  cams: { from: number; f: [number, number, number, number, number, number][] };
};
export const arrival = data as unknown as Arrival;

/** the walk's file for this screen: a phone (900 CSS px or less, the room engine's own rule) takes the 30 fps one */
export const walkFor = (cssWidth: number): Arrival['videos']['desktop'] => (cssWidth <= 900 ? arrival.videos.phone : arrival.videos.desktop);
export const walkUrl = (v: { src: string }): string => `${MEDIA_BASE}${v.src}`;
export const doorUrl = (cssWidth: number): string => {
  const w = cssWidth <= 900 ? arrival.door.widths[0]! : arrival.door.widths[arrival.door.widths.length - 1]!;
  return `${MEDIA_BASE}${arrival.door.src}.${w}.webp`;
};
export const hcUrl = (): string => `${MEDIA_BASE}${arrival.hc.src}.${arrival.hc.width}.webp`;

/** the frame of the 60 fps master on screen at a time of the walk (1-based; the phone's 30 fps file maps the same) */
export const frameAt = (t: number): number => Math.round(t * 60) + 1;

/**
 * A 3D point of the plan through a frame's camera: docs/house-plan.json conventions (f = (−sin yaw, −cos yaw),
 * r = (cos yaw, −sin yaw); u = u0 + kx · x/d, v = v0 + ky · (hc − Z)/d), in the frame's own [0, 1]. Null behind it.
 */
export function project(p: readonly number[], cam: readonly number[], proj = arrival.proj): { u: number; v: number } | null {
  const [x, y, z, yawDeg, u0, v0] = cam as [number, number, number, number, number, number];
  const yaw = (yawDeg * Math.PI) / 180;
  const dx = p[0]! - x;
  const dy = p[1]! - y;
  const d = dx * -Math.sin(yaw) + dy * -Math.cos(yaw);
  if (d < 0.05) return null;
  const r = dx * Math.cos(yaw) + dy * -Math.sin(yaw);
  return { u: u0 + (proj.kx * r) / d, v: v0 - (proj.ky * (p[2]! - z)) / d };
}
/** the camera of a frame of the walk, where the labels are on screen (null outside that window) */
export function camAt(f60: number): readonly number[] | null {
  const i = Math.round(f60) - arrival.cams.from;
  return i >= 0 && i < arrival.cams.f.length ? arrival.cams.f[i]! : null;
}

/**
 * When each label is on screen (frames of the 60 fps walk). Route ch. 11.1: the names land one after another, 0.12 s
 * apart, from 0.3 s before the camera stops on HC (bath, the boy's room, the girl's, the bedroom); the QA-passed `.ui`
 * walk lets them go 0.2 s into the turn to the right (frames 412–424), and they turn with the camera until then.
 */
export const LABEL_T = { first: arrival.rest_60[0] - 18, step: 7.2, rise: 15, out: [412, 424] as const };
export function labelOpacity(i: number, f60: number): number {
  const a = (f60 - (LABEL_T.first + i * LABEL_T.step)) / LABEL_T.rise;
  const b = (LABEL_T.out[1] - f60) / (LABEL_T.out[1] - LABEL_T.out[0]);
  return Math.max(0, Math.min(1, a, b));
}

/** a label's place in the frame's own [0, 1]: its lintel, and the point its name stands over */
export type LabelPose = { a: { u: number; v: number }; b: { u: number; v: number }; at: { u: number; v: number } };
export function labelPose(l: ArrivalLabel, cam: readonly number[]): LabelPose | null {
  const a = project(l.pts[0], cam);
  const b = project(l.pts[1], cam);
  if (!a || !b) return null;
  // the name stands over the lintel's higher end (a side door, seen along the corridor), or over its middle (the
  // bedroom's door, square to the camera at the corridor's end)
  const level = Math.abs(a.v - b.v) < 0.004;
  const at = level ? { u: (a.u + b.u) / 2, v: Math.min(a.v, b.v) } : a.v < b.v ? a : b;
  return { a, b, at };
}

/**
 * Where each name's box goes at the rest on HC (CSS px over its point), so that no name covers another: a name that
 * would is lifted, with a hairline down to its door (the girl's room, beside the bedroom's door in the frame). Laid out
 * once, at the rest, and kept through the turns: the names move with the camera and never jump.
 */
export function layoutLabels(sizes: { w: number; h: number }[], winW: number, winH: number): number[] {
  const cam = camAt(arrival.hc_60)!;
  const placed: [number, number, number, number][] = [];
  const order = arrival.labels.map((l, i) => ({ i, p: labelPose(l, cam)! })).sort((x, y) => y.p.at.v - x.p.at.v);
  const lift: number[] = arrival.labels.map(() => 0);
  for (const { i, p } of order) {
    const { w, h } = sizes[i]!;
    const x0 = p.at.u * winW - w / 2;
    const y1 = p.at.v * winH - 8;
    let dy = 0;
    const hit = (d: number) => placed.some((r) => x0 < r[2] + 6 && x0 + w > r[0] - 6 && y1 - d - h < r[3] + 4 && y1 - d > r[1] - 4);
    while (hit(dy) && dy < 200) dy += 6;
    // never over the window's top edge (a narrow window: the names are close together there)
    dy = Math.max(0, Math.min(dy, y1 - h - 2));
    lift[i] = dy;
    placed.push([x0, y1 - dy - h, x0 + w, y1 - dy]);
  }
  return lift;
}
