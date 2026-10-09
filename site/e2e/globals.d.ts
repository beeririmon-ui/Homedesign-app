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
  }
}
