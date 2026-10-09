/** Test hooks the room stage exposes on window (web/src/components/RoomExperience.tsx). */
export {};
declare global {
  interface Window {
    __hdEngine?: { ready: boolean; kind: string; getSelection(): Record<string, number> };
    __hdFrames?: number[];
  }
}
