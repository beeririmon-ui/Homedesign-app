import type { Ref } from 'preact';
import { formatIls } from '@hd/shared/money';
import { mediaUrl } from '../media';
import { scene, slotOf, product as productById } from '../catalog';

const FORMATS: ('avif' | 'webp')[] = __ARTIFACT__ ? ['webp'] : scene.formats;

export function srcset(src: string, widths: number[], ext: 'avif' | 'webp'): string {
  return widths.map((w) => `${mediaUrl(src, w, ext)} ${w}w`).join(', ');
}

type PictureProps = {
  src: string;
  widths: number[];
  alt: string;
  sizes: string;
  class?: string;
  loading?: 'eager' | 'lazy';
  fetchpriority?: 'high' | 'low' | 'auto';
  imgRef?: Ref<HTMLImageElement>;
  width?: number;
  height?: number;
};

export function Picture(p: PictureProps) {
  const fallbackW = p.widths.includes(1920) ? 1920 : p.widths[p.widths.length - 1]!;
  return (
    <picture>
      {FORMATS.filter((f) => f !== 'webp').map((f) => (
        <source key={f} type={`image/${f}`} srcset={srcset(p.src, p.widths, f)} sizes={p.sizes} />
      ))}
      <img
        ref={p.imgRef}
        class={p.class}
        src={mediaUrl(p.src, fallbackW, 'webp')}
        srcset={srcset(p.src, p.widths, 'webp')}
        sizes={p.sizes}
        alt={p.alt}
        loading={p.loading ?? 'lazy'}
        decoding="async"
        fetchpriority={p.fetchpriority}
        width={p.width}
        height={p.height}
      />
    </picture>
  );
}

/** Temporary product image: the option's cut-out layer from the room (no studio shots yet). */
export function optionImage(slotId: string, position: number): string | null {
  const s = scene.slots[slotId]?.product;
  const src = s?.src[position - 1] ?? null;
  return src ? mediaUrl(src, scene.widths.lo, 'webp') : null; // layers are WebP only (lossless alpha)
}

export function productImage(id: string): string | null {
  const p = productById(id);
  const where = p ? slotOf(p) : undefined;
  return where ? optionImage(where.slot.id, where.option.position) : null;
}

export function Price({ agorot, provisional, class: cls }: { agorot: number; provisional?: boolean; class?: string }) {
  return (
    <span class={cls}>
      <span class="num">{formatIls(agorot)}</span>
      {provisional ? (
        <>
          {' '}
          <span class="badge badge-temp">מחיר זמני</span>
        </>
      ) : null}
    </span>
  );
}
