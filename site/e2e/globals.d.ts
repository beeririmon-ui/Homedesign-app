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
export {};
