import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';
import { fileURLToPath } from 'node:url';
import { existsSync, readdirSync, rmSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import type { Plugin } from 'vite';

const r = (p: string) => fileURLToPath(new URL(p, import.meta.url));

/**
 * TODO(deploy): the test page (/test/), the story layer (/story/, tools/make-story.ts; /test/story/ redirects to it) and
 * their test frames (media/test/, media/story/) are built into dist for review. A public deploy builds with
 * HD_PUBLIC=1: their entries are left out, and dist/test, dist/story, dist/media/test and dist/media/story are removed
 * once the bundle is written (studio rules ו.7: an asset that did not pass QA never reaches the site); so are the houses
 * beside the Nordic one in the room engine (S10, media/house, and __HD_PUBLIC__ in the code). The story comes
 * out from behind the flag when its frames pass "approved for the site" (G-ED).
 */
const PUBLIC = process.env.HD_PUBLIC === '1';
/** every generated story page (web/story/**\/index.html) is an entry; none yet is not an error */
function storyPages(): Record<string, string> {
  const root = r('story');
  if (!existsSync(root)) return {};
  const out: Record<string, string> = {};
  const walk = (dir: string): void => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name === 'index.html') out[`story/${relative(root, dir).split('\\').join('/')}`.replace(/\/$/, '')] = p;
    }
  };
  walk(root);
  return out;
}
function withoutTestPages(): Plugin {
  let outDir = '';
  return {
    name: 'hd-without-test-pages',
    apply: 'build',
    configResolved(c) {
      outDir = resolve(c.root, c.build.outDir);
    },
    closeBundle() {
      for (const d of ['test', 'story', 'media/test', 'media/story', 'media/house']) rmSync(resolve(outDir, d), { recursive: true, force: true });
    },
  };
}

export default defineConfig(({ mode }) => {
  const artifact = mode === 'artifact';
  return {
    root: r('.'),
    publicDir: artifact ? false : 'public',
    esbuild: { jsx: 'automatic', jsxImportSource: 'preact', legalComments: 'none' },
    define: {
      __ARTIFACT__: JSON.stringify(artifact),
      __MEDIA_BASE__: JSON.stringify(artifact ? 'media/' : '/media/'),
      // S10: the houses beside the Nordic one (DIR2) are behind the flag: a public build has no code path to them
      __HD_PUBLIC__: JSON.stringify(PUBLIC || artifact),
    },
    resolve: {
      alias: [
        { find: /^@generated\/(.*)$/, replacement: r('../.generated/$1') },
        // The artifact loads fonts from Google Fonts (allowed there); the site self-hosts them.
        ...(artifact ? [{ find: /^\.\/styles\/fonts\.css$/, replacement: r('src/styles/empty.css') }] : []),
      ],
    },
    server: {
      host: '127.0.0.1',
      port: 5180,
      strictPort: true,
      proxy: { '/api': 'http://127.0.0.1:8787', '/mock-pay': 'http://127.0.0.1:8787' },
    },
    preview: { host: '127.0.0.1', port: 5181, strictPort: true },
    build: artifact
      ? {
          outDir: r('../dist-artifact'),
          emptyOutDir: true,
          target: 'es2022',
          assetsInlineLimit: 100_000_000,
          cssCodeSplit: false,
          modulePreload: false,
          reportCompressedSize: false,
        }
      : {
          outDir: r('dist'),
          emptyOutDir: true,
          target: 'es2022',
          sourcemap: false,
          reportCompressedSize: true,
          // the test page in the magazine language (tools/make-test-page.ts writes test/index.html) is its own entry:
          // its code is not part of the room pages' first load (tools/check-budget.ts counts the entry index.html loads);
          // so is every story page (tools/make-story.ts writes story/**/index.html, and test/story/ as a redirect)
          rollupOptions: {
            input: (PUBLIC
              ? { main: r('index.html') }
              : {
                  main: r('index.html'),
                  test: r('test/index.html'),
                  'test/story': r('test/story/index.html'),
                  ...storyPages(),
                }) as Record<string, string>,
          },
        },
    plugins: artifact ? [viteSingleFile({ removeViteModuleLoader: true })] : PUBLIC ? [withoutTestPages()] : [],
  };
});
