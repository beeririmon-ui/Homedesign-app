import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

/** site/ */
export const SITE = resolve(here, '../..');
/** repository root */
export const REPO = resolve(SITE, '..');
export const GENERATED = resolve(SITE, '.generated');
export const WEB = resolve(SITE, 'web');
export const MEDIA_OUT = resolve(WEB, 'public/media');

export const repoPath = (...p: string[]): string => resolve(REPO, ...p);
export const sitePath = (...p: string[]): string => resolve(SITE, ...p);
