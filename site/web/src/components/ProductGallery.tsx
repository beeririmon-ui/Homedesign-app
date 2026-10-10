/**
 * Product page gallery (FR-I, docs/studio-rules.md ג.0, 2026-10-10): the render from the room leads, says it is a
 * render, and the supplier's original photo follows. A scroll-snap strip (swipe on touch) with previous / next
 * buttons, thumbnails and a live region, after the WAI-ARIA carousel pattern; the buttons stay enabled at the ends
 * (aria-disabled) so keyboard focus is never lost. The strip itself is focusable: it is a scrollable region.
 */
import { useEffect, useRef, useState } from 'preact/hooks';
import { IconLeft, IconRight } from './Icons';
import { prefersReducedMotion } from '../motion';

export type GalleryImage = {
  kind: 'render' | 'supplier';
  src: string;
  alt: string;
  width: number;
  height: number;
  /** short name of the picture for the slide label and the live region */
  label: string;
  /** the visible note under the picture */
  caption: string;
};

export function ProductGallery({ images, id }: { images: GalleryImage[]; id: string }) {
  const track = useRef<HTMLDivElement>(null);
  const slides = useRef<(HTMLElement | null)[]>([]);
  const [index, setIndex] = useState(0);
  const [live, setLive] = useState('');
  const n = images.length;

  // the slide in view (swipe or scroll) becomes the current one
  useEffect(() => {
    const root = track.current;
    if (!root || n < 2 || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries)
          if (e.isIntersecting) {
            const i = slides.current.indexOf(e.target as HTMLElement);
            if (i >= 0) setIndex(i);
          }
      },
      { root, threshold: 0.6 },
    );
    for (const s of slides.current) if (s) io.observe(s);
    return () => io.disconnect();
  }, [n]);

  useEffect(() => {
    if (n < 2) return;
    setLive(`תמונה ${index + 1} מתוך ${n}: ${images[index]!.label}`);
  }, [index]);

  function goTo(i: number) {
    const to = Math.min(n - 1, Math.max(0, i));
    if (to === index) return;
    slides.current[to]?.scrollIntoView({ inline: 'center', block: 'nearest', behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
    setIndex(to);
  }
  function onKey(ev: KeyboardEvent) {
    // RTL: the next picture is to the left
    const map: Record<string, number> = { ArrowLeft: index + 1, ArrowRight: index - 1, Home: 0, End: n - 1 };
    if (!(ev.key in map)) return;
    ev.preventDefault();
    goTo(map[ev.key]!);
  }

  return (
    <section class="gallery" aria-roledescription="carousel" aria-label="תמונות המוצר">
      <div
        class="gallery-track"
        ref={track}
        role="group"
        aria-label={n > 1 ? 'תמונות: גללו הצידה, או השתמשו בחיצים ובכפתורים' : undefined}
        tabIndex={n > 1 ? 0 : undefined}
        onKeyDown={n > 1 ? onKey : undefined}
      >
        {images.map((im, i) => (
          <figure
            key={im.src}
            class="gallery-slide"
            data-kind={im.kind}
            role="group"
            aria-roledescription="slide"
            aria-label={`${i + 1} מתוך ${n}: ${im.label}`}
            ref={(el) => {
              slides.current[i] = el;
            }}
          >
            <div class="gallery-img">
              <img src={im.src} alt={im.alt} width={im.width} height={im.height} loading={i === 0 ? 'eager' : 'lazy'} decoding="async" />
            </div>
            <figcaption class="gallery-caption">
              {im.kind === 'render' ? <span class="badge badge-temp">הדמיה</span> : null}
              <span>{im.caption}</span>
            </figcaption>
          </figure>
        ))}
      </div>
      {n > 1 ? (
        <div class="gallery-nav">
          <button type="button" class="gallery-btn" aria-label="התמונה הקודמת" aria-disabled={index === 0 ? 'true' : undefined} onClick={() => goTo(index - 1)}>
            <IconRight />
          </button>
          <div class="gallery-thumbs" role="group" aria-label="בחירת תמונה">
            {images.map((im, i) => (
              <button
                key={im.src}
                type="button"
                class="gallery-thumb"
                data-kind={im.kind}
                aria-label={`תמונה ${i + 1}: ${im.label}`}
                aria-current={i === index ? 'true' : undefined}
                onClick={() => goTo(i)}
              >
                <img src={im.src} alt="" width={56} height={56} loading="lazy" decoding="async" />
              </button>
            ))}
          </div>
          <button
            type="button"
            class="gallery-btn"
            aria-label="התמונה הבאה"
            aria-disabled={index === n - 1 ? 'true' : undefined}
            onClick={() => goTo(index + 1)}
          >
            <IconLeft />
          </button>
          <p class="sr-only" aria-live="polite" id={`${id}-gallery-live`}>
            {live}
          </p>
        </div>
      ) : null}
    </section>
  );
}
