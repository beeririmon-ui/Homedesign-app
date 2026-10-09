/** Media URLs. Site: /media/... (later R2 behind a custom domain). Artifact: relative media/... next to the page. */
export const MEDIA_BASE = __MEDIA_BASE__;

let avif: boolean | null = __ARTIFACT__ ? false : null;

/** AVIF decode support (Safari 16+, Chrome, Firefox). Cached. */
export async function supportsAvif(): Promise<boolean> {
  if (avif !== null) return avif;
  if (typeof Image === 'undefined') return (avif = false);
  const probe =
    'data:image/avif;base64,AAAAHGZ0eXBhdmlmAAAAAG1pZjFhdmlmbWlhZgAAANZtZXRhAAAAAAAAACFoZGxyAAAAAAAAAABwaWN0AAAAAAAAAAAAAAAAAAAAAA5waXRtAAAAAAABAAAAImlsb2MAAAAAREAAAQABAAAAAAD6AAEAAAAAAAAAGgAAACNpaW5mAAAAAAABAAAAFWluZmUCAAAAAAEAAGF2MDEAAAAAVmlwcnAAAAA4aXBjbwAAAAxhdjFDgSACAAAAABRpc3BlAAAAAAAAAAIAAAACAAAAEHBpeGkAAAAAAwgICAAAABZpcG1hAAAAAAAAAAEAAQOBAgMAAAAibWRhdBIACgc4ADYQENBpMg0bABpppoQAAK/1OBXM';
  avif = await new Promise<boolean>((res) => {
    const img = new Image();
    img.onload = () => res(img.width > 0);
    img.onerror = () => res(false);
    img.src = probe;
  });
  return avif;
}

export function mediaUrl(rel: string, width?: number, ext: 'avif' | 'webp' = 'webp'): string {
  return `${MEDIA_BASE}${rel}${width ? `.${width}` : ''}.${ext}`;
}
