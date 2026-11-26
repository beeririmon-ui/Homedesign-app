/**
 * MOCK5 (2026-11-24): every frame of the tour's rooms built from render folders (tools/tour/frames.json), each by
 * tools/make-tour-room.ts in a process of its own (a frame holds its folder's layers in memory while it builds).
 */
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { sitePath } from './lib/paths';

const index = JSON.parse(readFileSync(sitePath('tools/tour/frames.json'), 'utf8')) as {
  style: string;
  living_room?: string;
  rooms: { id: string; frames: string[] }[];
};
const tsx = sitePath('node_modules/.bin/tsx');
// MOCK7: the living room, when frames.json names a rooms' config for it (M0-W); the phase 2 one is tools/make-tour.ts's
if (index.living_room && index.living_room !== 'living-room')
  execFileSync(tsx, [sitePath('tools/make-tour-room.ts'), `tools/tour/${index.living_room}.${index.style}.json`], { cwd: sitePath(), stdio: 'inherit' });
for (const r of index.rooms)
  for (const f of r.frames)
    execFileSync(tsx, [sitePath('tools/make-tour-room.ts'), `tools/tour/${f}.${index.style}.json`], { cwd: sitePath(), stdio: 'inherit' });
