/**
 * Layer order for a room and a selection, straight from data/slots/<room>.json (via the catalog):
 * base layers at their z, each product at its slot z, its shadow at z-1 (multiply) unless the slot has
 * has_shadow_layer: false, and light layers at the room's light z (screen). Ties keep slot order.
 */
import type { CatalogRoom } from '@hd/shared';
import type { LayerSpec, Scene } from './types';

export const LIGHT_Z = 90;

export function buildLayers(room: CatalogRoom, scene: Scene, selection: Record<string, number>): LayerSpec[] {
  const out: (LayerSpec & { order: number })[] = [];
  let order = 0;
  for (const b of scene.base) {
    const z = room.base_layers.find((x) => x.id === b.id)?.z ?? b.z;
    out.push({ key: b.src, src: b.src, kind: 'base', slot: null, rect: [0, 1, 0, 1], blend: b.blend, z, order: order++ });
  }
  for (const slot of room.slots) {
    const s = scene.slots[slot.id];
    if (!s) continue;
    const n = Math.max(1, Math.min(slot.options.length, selection[slot.id] ?? 1)) - 1;
    if (s.shadow && slot.has_shadow) {
      const src = s.shadow.src[n] ?? s.shadow.src[0]!;
      out.push({ key: src, src, kind: 'shadow', slot: slot.id, rect: s.shadow.rect, blend: 'multiply', z: slot.z - 1, order: order++ });
    }
    if (s.product) {
      const src = s.product.src[n] ?? s.product.src[0]!;
      out.push({ key: src, src, kind: 'product', slot: slot.id, rect: s.product.rect, blend: 'normal', z: slot.z, order: order++ });
    }
    if (s.light && slot.has_light) {
      const src = s.light.src[n] ?? s.light.src[0]!;
      out.push({ key: src, src, kind: 'light', slot: slot.id, rect: s.light.rect, blend: 'screen', z: LIGHT_Z, order: order++ });
    }
  }
  return out.sort((a, b) => a.z - b.z || a.order - b.order).map(({ order: _o, ...l }) => l);
}

/** Every layer source a slot can need (all options), for background preloading. */
export function slotSources(scene: Scene, slotId: string): string[] {
  const s = scene.slots[slotId];
  if (!s) return [];
  return [...new Set([...(s.product?.src ?? []), ...(s.shadow?.src ?? []), ...(s.light?.src ?? [])])];
}
