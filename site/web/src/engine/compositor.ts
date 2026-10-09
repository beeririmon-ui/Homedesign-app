import type { Blend, Box, Cam, Viewport } from './types';
import type { Decoded } from './loader';

export type DrawLayer = { key: string; rect: Box; blend: Blend; opacity: number };

export type DisplayState = {
  cam: Cam;
  vp: Viewport;
  aspect: number;
  /** 0 = previous composition, 1 = next */
  mix: number;
  /** dolly parallax strength (0 at rest), focus depth, ambient drift */
  parallax: number;
  focus: number;
  drift: [number, number];
};

export interface Compositor {
  readonly kind: 'webgl2' | 'canvas2d';
  upload(key: string, img: Decoded): void;
  has(key: string): boolean;
  setDepth(img: Decoded): void;
  /** Composite into the "next" buffer. Call swap() first to keep the current image as "prev". */
  compose(layers: DrawLayer[], width: number): void;
  swap(): void;
  display(s: DisplayState): void;
  resize(cssW: number, cssH: number, dpr: number): void;
  destroy(): void;
}
