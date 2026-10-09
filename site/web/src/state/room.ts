import { signal } from '@preact/signals';
import { defaultSelection, livingRoom } from '../catalog';

/** Current option per slot in the living room (1-based positions), shared by the stage and the list below it. */
export const selection = signal<Record<string, number>>(defaultSelection(livingRoom));
/** Set by the room stage when its first composition is on screen (the transition overlay waits for it). */
export const roomReady = signal(false);
/** A slot to open in the picker when the room mounts (from "הצגה בחדר" on a product page). */
export const pendingOpen = signal<{ slot: string; option: number } | null>(null);
