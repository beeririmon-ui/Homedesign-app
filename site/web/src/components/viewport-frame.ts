/**
 * QA S6–S7 ת7: the wheel opens where the person can see it. Its frame is the stage's box clipped to the visual viewport
 * (what is on the glass: the page's scroll, a pinch zoom and the phone's toolbars included), in the layout viewport's
 * coordinates that `position: fixed` uses. Never the stage's own scroll coordinates: a scrolled stage put the wheel and
 * the room 362 px off screen on a phone.
 */
export type Box = { left: number; top: number; width: number; height: number };
export type VisualViewportLike = { offsetLeft: number; offsetTop: number; width: number; height: number };

/** The smallest frame the wheel needs: less than this of the stage on screen, and the wheel takes the visible glass. */
export const MIN_FRAME = { width: 280, height: 360 };

/**
 * The part of `stage` (from getBoundingClientRect) inside the visual viewport, or the visual viewport itself when too
 * little of the stage shows. `layout` is the layout viewport's size (innerWidth × innerHeight), used without a visual
 * viewport API.
 */
export function visibleFrame(stage: Box, vv: VisualViewportLike | null, layout: { width: number; height: number }): Box {
  const view: Box = vv ? { left: vv.offsetLeft, top: vv.offsetTop, width: vv.width, height: vv.height } : { left: 0, top: 0, ...layout };
  const left = Math.max(stage.left, view.left);
  const top = Math.max(stage.top, view.top);
  const right = Math.min(stage.left + stage.width, view.left + view.width);
  const bottom = Math.min(stage.top + stage.height, view.top + view.height);
  const width = right - left;
  const height = bottom - top;
  if (width < Math.min(MIN_FRAME.width, view.width) || height < Math.min(MIN_FRAME.height, view.height)) return view;
  return { left, top, width, height };
}

/** The frame as inline style for the wheel (`position: fixed`), rounded to whole CSS pixels. */
export function frameStyle(f: Box): Record<string, string> {
  return {
    position: 'fixed',
    inset: 'auto',
    left: `${Math.round(f.left)}px`,
    top: `${Math.round(f.top)}px`,
    width: `${Math.round(f.width)}px`,
    height: `${Math.round(f.height)}px`,
  };
}
