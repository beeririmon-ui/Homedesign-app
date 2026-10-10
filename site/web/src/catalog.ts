/** The public catalog and the room scene, bundled at build time from site/.generated (built from the repo). */
import type { CatalogRoom, CatalogSlot, PublicCatalog, PublicProduct, SlotOption, SupplierImage, SupplierImageManifest } from '@hd/shared';
import catalogJson from '@generated/catalog.public.json';
import sceneJson from '@generated/scene.living-room.nordic.json';
import supplierJson from '@generated/supplier-images.json';
import type { Scene } from './engine/types';

export const catalog = catalogJson as unknown as PublicCatalog;
/** The supplier's original photo of a product, served from our media (FR-I; tools/supplier-images.ts). */
const supplierImages = (supplierJson as unknown as SupplierImageManifest).products;
export const supplierImage = (id: string): SupplierImage | null => supplierImages[id] ?? null;
const fullScene = sceneJson as unknown as Scene;
/**
 * The artifact preview ships a reduced media set (≤ 200 files, ≤ 12 MB): WebP only, layers at one width (lo),
 * shell and hall at ≤ lo. tools/finalize-artifact.ts copies exactly these files.
 */
export const scene: Scene = __ARTIFACT__
  ? {
      ...fullScene,
      formats: ['webp'],
      widths: { lo: fullScene.widths.lo, hi: fullScene.widths.lo },
      base: fullScene.base.map((b) => ({ ...b, widths: b.widths.filter((w) => w <= fullScene.widths.lo) })),
      hall: { ...fullScene.hall, widths: fullScene.hall.widths.filter((w) => w <= fullScene.widths.lo) },
    }
  : fullScene;

const byId = new Map(catalog.products.map((p) => [p.id, p]));
export const product = (id: string | null | undefined): PublicProduct | undefined => (id ? byId.get(id) : undefined);
export const room = (id: string): CatalogRoom | undefined => catalog.rooms.find((r) => r.id === id);
export const livingRoom = room('living-room')!;

export function slotOf(p: PublicProduct): { room: CatalogRoom; slot: CatalogSlot; option: SlotOption } | undefined {
  const r = room(p.room);
  const s = r?.slots.find((x) => x.id === p.slot);
  const o = s?.options.find((x) => x.product_id === p.id);
  return r && s && o ? { room: r, slot: s, option: o } : undefined;
}

/** Default selection: position of the default option for each slot (1-based). */
export function defaultSelection(r: CatalogRoom): Record<string, number> {
  return Object.fromEntries(r.slots.map((s) => [s.id, s.options.find((o) => o.is_default)?.position ?? 1]));
}
