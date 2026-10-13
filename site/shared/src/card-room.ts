/**
 * The room of a product card. Since card schema 1.1 (2026-10-13, user decision Q2) the card names it in `room`
 * (the id of data/slots/<room>.json), and `room` + `slot` resolve to exactly one slot. Cards written before 1.1
 * fall back to the room their folder implies:
 *   data/products/<slot>/<card>.json          living-room (the first room keeps its slots at the top level)
 *   data/products/dining/<slot>/<card>.json   dining-room
 *   data/products/entrance/<slot>/...         hall
 *   data/products/<room>/<slot>/...           <room> (bath, corridor, kids, master, work)
 *   data/products/pool/..., .../leads/...     no room
 */
import { ProductCardSchema } from './schema/product-card.gen';

export const CARD_ROOMS = ProductCardSchema.shape.room.options;
export type CardRoomId = (typeof CARD_ROOMS)[number];

const FOLDER_ROOM: Record<string, CardRoomId> = { dining: 'dining-room', entrance: 'hall' };
const NO_ROOM_FOLDERS = new Set(['pool', 'leads']);

const isRoom = (v: unknown): v is CardRoomId => typeof v === 'string' && (CARD_ROOMS as readonly string[]).includes(v);

/** The room a card's path implies (path relative to the repo or absolute), or null. */
export function roomFromPath(path: string): CardRoomId | null {
  const parts = path.split(/[\\/]/);
  const i = parts.lastIndexOf('products');
  if (i < 1 || parts[i - 1] !== 'data') return null;
  const rest = parts.slice(i + 1);
  if (NO_ROOM_FOLDERS.has(rest[0]!)) return null; // checked first: a lead sits at data/products/leads/<card>.json
  if (rest.length === 2) return 'living-room';
  if (rest.length !== 3) return null;
  const room = FOLDER_ROOM[rest[0]!] ?? rest[0];
  return isRoom(room) ? room : null;
}

/** The card's own `room`, else the room its folder implies (path fallback for cards written before schema 1.1). */
export function cardRoom(card: { room?: unknown }, path: string): CardRoomId | null {
  return isRoom(card.room) ? card.room : roomFromPath(path);
}
