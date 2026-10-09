/**
 * Image loading with priorities: 0 = what the first frame needs, 1 = other variants, 2 = transitions, 3 = hi-res.
 * Decoding happens off the main thread (createImageBitmap); bitmaps are premultiplied for the compositors.
 */
export type Decoded = ImageBitmap | HTMLImageElement;

type Job = { url: string; priority: number; resolve: (b: Decoded) => void; reject: (e: unknown) => void };

export class Loader {
  private queue: Job[] = [];
  private active = 0;
  private cache = new Map<string, Promise<Decoded>>();
  bytes = 0;

  constructor(private concurrency = 6) {}

  load(url: string, priority = 1): Promise<Decoded> {
    const hit = this.cache.get(url);
    if (hit) return hit;
    const p = new Promise<Decoded>((resolve, reject) => {
      this.queue.push({ url, priority, resolve, reject });
      this.queue.sort((a, b) => a.priority - b.priority);
      this.pump();
    });
    this.cache.set(url, p);
    p.catch(() => this.cache.delete(url));
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

  private pump(): void {
    while (this.active < this.concurrency && this.queue.length) {
      const job = this.queue.shift()!;
      this.active++;
      this.fetchDecode(job.url)
        .then(job.resolve, job.reject)
        .finally(() => {
          this.active--;
          this.pump();
        });
    }
  }

  private async fetchDecode(url: string): Promise<Decoded> {
    if (typeof createImageBitmap === 'function' && typeof fetch === 'function') {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`${res.status} ${url}`);
      const blob = await res.blob();
      this.bytes += blob.size;
      return createImageBitmap(blob, { premultiplyAlpha: 'premultiply' });
    }
    const img = new Image();
    img.decoding = 'async';
    img.src = url;
    await img.decode();
    return img;
  }
}

export function release(d: Decoded | undefined): void {
  if (d && 'close' in d) d.close();
}
