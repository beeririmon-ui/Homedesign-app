import { signal } from '@preact/signals';
import type { RoomEngine } from '../engine/engine';
import { defaultSelection, livingRoom } from '../catalog';

/** Current option per slot in the living room (1-based positions), shared by the stage and the list below it. */
export const selection = signal<Record<string, number>>(defaultSelection(livingRoom));
/** Set by the room stage when its first composition is on screen (the transition overlay waits for it). */
export const roomReady = signal(false);
/** A slot to open in the picker when the room mounts (from "הצגה בחדר" on a product page). */
export const pendingOpen = signal<{ slot: string; option: number } | null>(null);
/**
 * A transition is landing in the room: 'pending' while its frames play (the stage starts its engine at once),
 * 'landing' while the engine flies the last metre, null otherwise.
 */
export const arrival = signal<'pending' | 'landing' | null>(null);
/** The stage's engine once its first composition is ready (the transition overlay drives the arrival with it). */
export const stageEngine = signal<RoomEngine | null>(null);
