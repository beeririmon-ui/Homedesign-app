/**
 * Image loading with priorities: 0 = what the first frame needs, 1 = other variants, 2 = transitions, 3 = hi-res.
 * Decoding happens off the main thread (createImageBitmap); bitmaps are premultiplied for the compositors.
 *
 * Two kinds of load: `load` fetches and decodes (room layers: a few images that stay); `fetch` only fetches and keeps
 * the compressed bytes (frame sequences: hundreds of frames, decoded later in a window around the playhead, see
 * sequence.ts). A decoded 1280-wide frame is ~3.7 MB; a WebP frame is ~50 KB.
 */
export type Decoded = ImageBitmap | HTMLImageElement;

type Job = { url: string; priority: number; run: () => Promise<unknown>; resolve: (v: never) => void; reject: (e: unknown) => void };

export class Loader {
  private queue: Job[] = [];
  private active = 0;
  private cache = new Map<string, Promise<Decoded>>();
  private blobs = new Map<string, Promise<Blob>>();
  bytes = 0;

  constructor(private concurrency = 6) {}

  load(url: string, priority = 1): Promise<Decoded> {
    const hit = this.cache.get(url);
    if (hit) return hit;
    const p = this.enqueue(url, priority, () => this.fetchDecode(url));
    this.cache.set(url, p);
    p.catch(() => this.cache.delete(url));
    return p;
  }

  /** The compressed bytes only (cached); decode with decodeBlob when the frame is about to be drawn. */
  fetch(url: string, priority = 2): Promise<Blob> {
    const hit = this.blobs.get(url);
    if (hit) return hit;
    const p = this.enqueue(url, priority, () => this.fetchBlob(url));
    this.blobs.set(url, p);
    p.catch(() => this.blobs.delete(url));
    return p;
  }

  /** Decode an <img> already on the page (the poster), so the first frame costs no second download. */
  adopt(url: string, img: HTMLImageElement): Promise<Decoded> {
    const p = img
      .decode()
      .then((): Promise<Decoded> | Decoded => (typeof createImageBitmap === 'function' ? createImageBitmap(img, { premultiplyAlpha: 'premultiply' }) : img));
    this.cache.set(url, p);
    return p;
  }

  private enqueue<T>(url: string, priority: number, run: () => Promise<T>): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      this.queue.push({ url, priority, run, resolve: resolve as (v: never) => void, reject });
      this.queue.sort((a, b) => a.priority - b.priority);
      this.pump();
    });
  }

  private pump(): void {
    while (this.active < this.concurrency && this.queue.length) {
      const job = this.queue.shift()!;
      this.active++;
      job
        .run()
        .then(job.resolve as (v: unknown) => void, job.reject)
        .finally(() => {
          this.active--;
          this.pump();
        });
    }
  }

  private async fetchBlob(url: string): Promise<Blob> {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${res.status} ${url}`);
    const blob = await res.blob();
    this.bytes += blob.size;
    return blob;
  }

  private async fetchDecode(url: string): Promise<Decoded> {
    if (typeof createImageBitmap === 'function' && typeof fetch === 'function') {
      return decodeBlob(await this.fetchBlob(url));
    }
    const img = new Image();
    img.decoding = 'async';
    img.src = url;
    await img.decode();
    return img;
  }
}

/** Decodes compressed bytes to a drawable (off the main thread where createImageBitmap exists). */
export async function decodeBlob(blob: Blob): Promise<Decoded> {
  if (typeof createImageBitmap === 'function') return createImageBitmap(blob, { premultiplyAlpha: 'premultiply' });
  const url = URL.createObjectURL(blob);
  try {
    const img = new Image();
    img.decoding = 'async';
    img.src = url;
    await img.decode();
    return img;
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function release(d: Decoded | undefined): void {
  if (d && 'close' in d) d.close();
}
