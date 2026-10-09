/** Frame ↔ screen mapping for a 16:9 frame shown "cover" in any viewport, with pan and zoom. Pure functions. */
import type { Box, Cam, Viewport } from './types';

export const MAX_ZOOM = 4;

/** Size of the whole frame in CSS px at zoom 1 (cover fit). */
export function coverSize(vp: Viewport, aspect: number): { fw: number; fh: number } {
  const fw = Math.max(vp.w, vp.h * aspect);
  return { fw, fh: fw / aspect };
}

export function clampCam(cam: Cam, vp: Viewport, aspect: number): Cam {
  const z = Math.min(MAX_ZOOM, Math.max(1, cam.z));
  const { fw, fh } = coverSize(vp, aspect);
  const hu = Math.min(0.5, vp.w / (2 * fw * z));
  const hv = Math.min(0.5, vp.h / (2 * fh * z));
  return { z, cu: Math.min(1 - hu, Math.max(hu, cam.cu)), cv: Math.min(1 - hv, Math.max(hv, cam.cv)) };
}

export function defaultCam(vp: Viewport, aspect: number, mobileCenterU: number): Cam {
  const portrait = vp.w / vp.h < 1.1;
  return clampCam({ cu: portrait ? mobileCenterU : 0.5, cv: 0.5, z: 1 }, vp, aspect);
}

export function frameToScreen(u: number, v: number, cam: Cam, vp: Viewport, aspect: number): { x: number; y: number } {
  const { fw, fh } = coverSize(vp, aspect);
  return { x: vp.w / 2 + (u - cam.cu) * fw * cam.z, y: vp.h / 2 + (v - cam.cv) * fh * cam.z };
}

export function screenToFrame(x: number, y: number, cam: Cam, vp: Viewport, aspect: number): { u: number; v: number } {
  const { fw, fh } = coverSize(vp, aspect);
  return { u: cam.cu + (x - vp.w / 2) / (fw * cam.z), v: cam.cv + (y - vp.h / 2) / (fh * cam.z) };
}

/** Camera that frames a zoom box. `reserve` keeps the lower part of the screen free for the wheel UI. */
export function camForBox(box: Box, vp: Viewport, aspect: number, reserve = 0): Cam {
  const { fw, fh } = coverSize(vp, aspect);
  const usableH = vp.h * (1 - reserve);
  const z = Math.min(vp.w / ((box[1] - box[0]) * fw), usableH / ((box[3] - box[2]) * fh));
  const cu = (box[0] + box[1]) / 2;
  // shift the centre so the box sits in the upper (usable) part of the screen
  const cv = (box[2] + box[3]) / 2 + (vp.h * reserve) / 2 / (fh * Math.max(1, z));
  return clampCam({ cu, cv, z: Math.max(1, z) }, vp, aspect);
}

/** Interpolates zoom in log space (constant perceived speed) and the centre linearly. */
export function lerpCam(a: Cam, b: Cam, t: number): Cam {
  return { cu: a.cu + (b.cu - a.cu) * t, cv: a.cv + (b.cv - a.cv) * t, z: a.z * Math.pow(b.z / a.z, t) };
}

export const easeInOutCubic = (t: number): number => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const easeOutQuart = (t: number): number => 1 - Math.pow(1 - t, 4);
