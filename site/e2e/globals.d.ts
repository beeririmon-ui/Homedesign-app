/** Test hooks the room stage exposes on window (web/src/components/RoomExperience.tsx). */
export {};
declare global {
  interface Window {
    __hdEngine?: {
      ready: boolean;
      kind: string;
      cam: { cu: number; cv: number; z: number };
      vp: { w: number; h: number };
      aspect: number;
      getSelection(): Record<string, number>;
      setSelection(slot: string, position: number, durationMs?: number): Promise<void>;
    };
    __hdFrames?: number[];
    /** S12 ת15: e2e/house.spec.ts reads what the display pass draws (installProbe) */
    __hdProbe?: { grab(mix: number): number[]; record(on: boolean): { mix: number; mean: number }[]; restore(): void };
  }
}

declare global {
  interface Window {
    __mag?: {
      events: { t: number; name: string; detail?: unknown }[];
      reduce: boolean;
      openFocus: (stage: string, slot: string) => Promise<void>;
      chooseVariant: (stage: string) => Promise<void>;
      cancelFocus: (stage: string) => Promise<void>;
      browse: (stage: string, dir: 1 | -1) => void;
      showMarks: (stage: string) => void;
      enter: () => void;
      paperTo: (selector: string) => Promise<void>;
      pan: { ready: boolean; playing: boolean; pos: number; samples: { t: number; p: number }[]; play: (dir: 1 | -1) => Promise<void> };
    };
  }
}

/** MOCK1: the hooks of the wow-tour mock-up (web/src/tour/TourPage.tsx), as the tests and the evidence tools use them */
type TourBox = [number, number, number, number];
/** MOCK2: what an effect cost and what it interrupted (web/src/tour/metrics.ts) */
type TourCounts = { decode: number; upload: number; compile: number; readback: number; layout: number };
type TourStat = {
  label: string;
  frames: number;
  ms: number;
  fps: number;
  dt_p50: number;
  dt_p95: number;
  dt_max: number;
  long20: number;
  long34: number;
  long_run: number;
  js_mean: number;
  js_p95: number;
  js_max: number;
  step_mean: number;
  step_p95: number;
  step_max: number;
  step_over8: number;
  mpx: number;
  mpx_max: number;
  counts: TourCounts;
  min_scale: number;
};
type TourSlotT = { id: string; rect: TourBox; depth_m: number; options: { position: number; box: TourBox }[] };
type TourUi = { ring(): void; label(): void; spots(): void; count(): void; dims(): void };
type TourCamT = { cu: number; cv: number; z: number };
type TourEngineT = {
  ready: boolean;
  sync: boolean;
  reduce: boolean;
  house: string;
  lastLabel: string;
  seams: { label: string; first: { max: number; px: number }; last: { max: number; px: number } }[];
  frames: Record<string, { dt: number[]; js: number[]; px: number[] }>;
  selection: Record<string, number>;
  visible: Set<string>;
  cam: TourCamT;
  rest: TourCamT;
  vp: { w: number; h: number };
  d: { vig: number; vigBox: TourBox; door: TourBox; doorR: number; doorAmt: number };
  gl: { width: number; height: number; vram: number; bytes: number; readScreen(): { w: number; h: number; data: Uint8Array } };
  read(r: TourBox): Uint8Array;
  render(): number;
  mask(all?: boolean): void;
  slot(id: string): TourSlotT;
  products(): Promise<void>;
  /** MOCK2: resolves once the room can be animated with nothing left to load */
  whenWarm(): Promise<void>;
  warmReady: boolean;
  stat: TourStat | null;
  otherHouse(): Promise<void>;
  option(slot: string, pos: number): Promise<void>;
  camFor(box: TourBox, reserve: number): TourCamT;
  moveCam(label: string, to: TourCamT, ms: number, also?: (e: number, t: number) => void): Promise<void>;
  wait(ms: number): Promise<void>;
};
declare global {
  interface Window {
    __hdTour?: TourEngineT;
    __hdTourState?: { phase: 'door' | 'entering' | 'room'; busy: boolean; house: string };
    __hdTourFx?: {
      ui: TourUi;
      /** MOCK2: the counters, per effect (web/src/tour/metrics.ts) */
      metrics: { total: TourCounts; effects: Record<string, TourStat>; order: string[]; reset(): void };
      LEGACY: boolean;
      enter(e: TourEngineT): Promise<void>;
      leave(e: TourEngineT, d: { cx: number; cy: number; hw: number; hh: number; r: number }): Promise<void>;
      doorPush(e: TourEngineT): void;
      reveal(e: TourEngineT, ui: TourUi, kind: 'a' | 'b' | 'c', short?: boolean): Promise<void>;
      collect(e: TourEngineT, ui: TourUi): Promise<void>;
      swap(e: TourEngineT, ui: TourUi, s: TourSlotT, to: number, dir: 1 | -1, kind: 's1' | 's2' | 's3'): Promise<void>;
      style(e: TourEngineT, ui: TourUi, to: 'nordic' | 'warm-modern', kind: 'y1' | 'y2', how: 'a' | 'b' | 'c'): Promise<void>;
    };
  }
}
export {};
