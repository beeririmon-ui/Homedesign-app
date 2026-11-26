/**
 * MOCK7 (2026-11-26): where the push between two rooms walks (web/src/tour/gl.ts, PUSH), from the two cameras of the
 * house plan (docs/house-plan.json conventions: f = (−sin yaw, −cos yaw), r = (cos yaw, −sin yaw), u = u0 + kx · x / d).
 *
 *  - the room left is walked toward the next room's camera, where it is in the frame (its opening, roughly); a room
 *    behind or beside the camera is walked toward the side it turns to (the route: always facing forward, FB8);
 *  - the turn is the change of the cameras' yaw: a turn to the right moves the picture to the left, and the room
 *    reached slides in from the right, slowing to its rest;
 *  - the room reached is walked along its own axis, to its own principal point (the camera arrives straight).
 */
import type { Box } from '../engine/types';

export type PushCamera = { frame: Box; u0: number; v0: number; kx: number; loc: readonly number[]; yaw_deg_left: number };
export type PushGeometry = {
  /** the turn, −1 (left) … 1 (right) */
  dir: number;
  /** the point the room left is walked toward, in its canvas UV */
  fa: [number, number];
  /** the point the room reached is walked to, in its canvas UV */
  fb: [number, number];
};

const wrap = (deg: number): number => ((((deg + 180) % 360) + 360) % 360) - 180;
const clamp = (x: number, a: number, b: number): number => Math.min(b, Math.max(a, x));
const inFrame = (c: PushCamera, u: number, v: number): [number, number] => [
  +(c.frame[0] + u * (c.frame[1] - c.frame[0])).toFixed(5),
  +(c.frame[2] + v * (c.frame[3] - c.frame[2])).toFixed(5),
];

export function pushGeometry(a: PushCamera, b: PushCamera): PushGeometry {
  // yaw is measured to the left: a larger yaw in the next room is a turn to the left
  const turn = wrap(b.yaw_deg_left - a.yaw_deg_left);
  const dir = +clamp(-turn / 90, -1, 1).toFixed(4);
  const yaw = (a.yaw_deg_left * Math.PI) / 180;
  const dx = b.loc[0]! - a.loc[0]!;
  const dy = b.loc[1]! - a.loc[1]!;
  const d = dx * -Math.sin(yaw) + dy * -Math.cos(yaw);
  const x = dx * Math.cos(yaw) + dy * -Math.sin(yaw);
  // ahead: where the next camera stands in this frame; behind or beside: the side the walk turns to
  const u = d > 0.4 ? a.u0 + (a.kx * x) / d : 0.5 + 0.34 * Math.sign(dir);
  return { dir, fa: inFrame(a, clamp(u, 0.14, 0.86), a.v0), fb: inFrame(b, b.u0, b.v0) };
}

/**
 * The still (a video shown with object-fit: cover and object-position `pos`% 50%) as the display reads it: CSS px of
 * the window → the still's own UV, [scale x, scale y, offset x, offset y].
 */
export function coverMap(vw: number, vh: number, ww: number, wh: number, pos: number): [number, number, number, number] {
  const s = Math.max(ww / vw, wh / vh);
  const dw = vw * s;
  const dh = vh * s;
  const ox = (ww - dw) * pos;
  const oy = (wh - dh) * 0.5;
  return [1 / dw, 1 / dh, -ox / dw, -oy / dh];
}
