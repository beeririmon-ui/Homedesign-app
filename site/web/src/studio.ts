/**
 * MOCK2 (FB1): our own studio picture of a product, where one exists and passed QA (tools/make-studio.ts writes both
 * the pictures and this manifest from render-agent's pilot record). The wheel prefers it over any layer.
 *
 * The pictures are still waiting for the designer's written eye, so they live under media/tour/ — a folder a public
 * build deletes — and are only ever asked for behind the flag.
 */
import studioJson from '@generated/studio-images.json';
import { mediaUrl } from './media';

type Manifest = { width: number; products: Record<string, { src: string; w: number; h: number }> };
const manifest = studioJson as Manifest;

export type StudioImage = { src: string; w: number; h: number };

/** our own picture of a product, or null (a public build has none) */
export function studioImage(productId: string | null | undefined): StudioImage | null {
  if (__HD_PUBLIC__ || !productId) return null;
  const s = manifest.products[productId];
  return s ? { src: mediaUrl(s.src), w: s.w, h: s.h } : null;
}
