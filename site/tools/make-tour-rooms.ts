/**
 * MOCK5 (2026-11-24): every frame of the tour's rooms built from render folders (tools/tour/frames.json), each by
 * tools/make-tour-room.ts in a process of its own (a frame holds its folder's layers in memory while it builds).
 *
 * MOCK12 (2026-11-28, FB29): then the list of the products still shown outside the room without a studio picture
 * (.generated/studio-missing.json), for the designer's list of stills: each product once, where it is seen, and what the
 * strip, the wheel and the card show in its place (its card with a clean rim, or its name where the room cuts it).
 */
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { GENERATED, sitePath } from './lib/paths';

const index = JSON.parse(readFileSync(sitePath('tools/tour/frames.json'), 'utf8')) as {
  style: string;
  living_room?: string;
  rooms: { id: string; frames: string[] }[];
};
const tsx = sitePath('node_modules/.bin/tsx');
const built: string[] = [];
// MOCK7: the living room, when frames.json names a rooms' config for it (M0-W); the phase 2 one is tools/make-tour.ts's
if (index.living_room && index.living_room !== 'living-room') {
  execFileSync(tsx, [sitePath('tools/make-tour-room.ts'), `tools/tour/${index.living_room}.${index.style}.json`], { cwd: sitePath(), stdio: 'inherit' });
  built.push('living-room');
}
for (const r of index.rooms)
  for (const f of r.frames) {
    execFileSync(tsx, [sitePath('tools/make-tour-room.ts'), `tools/tour/${f}.${index.style}.json`], { cwd: sitePath(), stdio: 'inherit' });
    built.push(f);
  }

// ---------- MOCK12: the products still on the fallback outside the room ----------
type Opt = { position: number; variant?: string; card_id?: string | null; name_he: string | null; studio?: unknown; cut?: 'occluded' | 'frame' };
type Frame = { room: string; group?: string; frame?: string; slots: { id: string; name_he: string; fixed?: boolean; options: Opt[] }[] };
type Seen = { room: string; frame: string; slot: string; position: number; wheel: boolean; shown: 'card' | 'name'; cut: 'occluded' | 'frame' | null };
const rows = new Map<string, { variant: string; card_id: string | null; name_he: string | null; slot_he: string; seen: Seen[] }>();
for (const id of built) {
  const d = JSON.parse(readFileSync(join(GENERATED, `tour.${id}.${index.style}.json`), 'utf8')) as Frame;
  for (const s of d.slots)
    for (const o of s.fixed ? [] : s.options) {
      if (o.studio) continue;
      const key = `${o.card_id ?? '-'}|${o.variant ?? `${id}:${s.id}:${o.position}`}`;
      const row = rows.get(key) ?? { variant: o.variant ?? '', card_id: o.card_id ?? null, name_he: o.name_he, slot_he: s.name_he, seen: [] };
      row.seen.push({
        room: d.group ?? d.room,
        frame: d.frame ?? id,
        slot: s.id,
        position: o.position,
        wheel: s.options.length > 1,
        shown: o.cut ? 'name' : 'card',
        cut: o.cut ?? null,
      });
      rows.set(key, row);
    }
}
const products = [...rows.values()].sort((a, b) => a.seen[0]!.room.localeCompare(b.seen[0]!.room) || a.variant.localeCompare(b.variant));
const byRoom: Record<string, number> = {};
for (const p of products) for (const r of new Set(p.seen.map((s) => s.room))) byRoom[r] = (byRoom[r] ?? 0) + 1;
writeFileSync(
  join(GENERATED, 'studio-missing.json'),
  JSON.stringify(
    {
      note:
        'MOCK12 (FB29): the tour products shown outside the room (the strip, the wheel, the product card) without a studio still in assets/renders/wheel-studio/<style>/manifest.json. Until one is rendered and passes QA, the page shows the product\'s card (its layer trimmed, its rim hardened: no feathered rim) or, where the room cuts it (an occluder over it: `cut` "occluded"; the frame\'s edge: "frame"), its name. One row a product (its layer\'s `variant` and its card), with every frame it is seen in. Written by tools/make-tour-rooms.ts.',
      generated_at: new Date().toISOString(),
      style: index.style,
      count: products.length,
      by_name: products.filter((p) => p.seen.some((s) => s.shown === 'name')).length,
      by_room: byRoom,
      products,
    },
    null,
    1,
  ) + '\n',
);
console.log(
  `studio-missing: ${products.length} products still without a studio picture outside the room (${products.filter((p) => p.seen.some((s) => s.shown === 'name')).length} shown by name, the room cuts them) → .generated/studio-missing.json`,
);
