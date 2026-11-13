import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';
import { fileURLToPath } from 'node:url';
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
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
/**
 * S15 (the owner's launch item "supplier image rights"): the public build ships only the supplier pictures whose rights
 * are confirmed. Its code reads .generated/supplier-images.public.json (the alias below), and every other file under
 * dist/media/products is removed here; tools/check-image-rights.ts fails the build if one is left or named.
 */
const PUBLIC_SUPPLIER = r('../.generated/supplier-images.public.json');
function shippedSupplierFiles(): Set<string> {
  type M = { width: number; products: Record<string, { src: string }>; options?: Record<string, { files: { name: string }[] }> };
  const m = JSON.parse(readFileSync(PUBLIC_SUPPLIER, 'utf8')) as M;
  return new Set([
    ...Object.values(m.products).map((p) => `${p.src}.webp`),
    ...Object.entries(m.options ?? {}).flatMap(([id, o]) => o.files.map((f) => `products/${id}/${f.name}.${m.width}.webp`)),
  ]);
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
      for (const d of ['test', 'story', 'tour', 'media/test', 'media/story', 'media/house', 'media/tour'])
        rmSync(resolve(outDir, d), { recursive: true, force: true });
      // S15: a supplier picture the public manifest does not list (its rights are not confirmed) does not ship
      const media = resolve(outDir, 'media');
      const dir = resolve(media, 'products');
      if (!existsSync(dir)) return;
      const keep = shippedSupplierFiles();
      for (const id of readdirSync(dir)) {
        const folder = resolve(dir, id);
        if (!statSync(folder).isDirectory()) continue;
        for (const f of readdirSync(folder)) if (!keep.has(`products/${id}/${f}`)) rmSync(resolve(folder, f), { force: true });
        if (!readdirSync(folder).length) rmSync(folder, { recursive: true, force: true });
      }
      if (!readdirSync(dir).length) rmSync(dir, { recursive: true, force: true });
    },
  };
}

/**
 * S16, QA ת44: the client build's chunk graph, by content (tools/lib/bundle-graph.ts): each chunk's rendered modules,
 * static and dynamic imports. tools/check-budget.ts follows the room entry's static imports and fails if a page that must
 * be its own chunk is carried there, whatever the chunk is called. Written beside the generated data, never into dist.
 */
function bundleGraph(): Plugin {
  let ssr = false;
  let root = '';
  return {
    name: 'hd-bundle-graph',
    apply: 'build',
    configResolved(c) {
      ssr = !!c.build.ssr;
      root = c.root;
    },
    generateBundle(_opts, bundle) {
      if (ssr) return;
      const chunks: Record<string, { isEntry: boolean; imports: string[]; dynamicImports: string[]; modules: string[] }> = {};
      for (const out of Object.values(bundle)) {
        if (out.type !== 'chunk') continue;
        chunks[out.fileName] = {
          isEntry: out.isEntry,
          imports: out.imports,
          dynamicImports: out.dynamicImports,
          modules: Object.entries(out.modules)
            .filter(([, m]) => m.renderedLength > 0)
            .map(([id]) => relative(root, id.replace(/\?.*$/, '')).split('\\').join('/')),
        };
      }
      const file = r('../.generated/bundle-graph.json');
      mkdirSync(dirname(file), { recursive: true });
      writeFileSync(file, JSON.stringify({ chunks }, null, 1));
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
      // MOCK1: the wow-tour mock-up is in every build but the public one; the Artifact preview opens on it
      __TOUR__: JSON.stringify(!PUBLIC),
    },
    resolve: {
      alias: [
        // S15: the public build reads the supplier pictures it may ship, never the full manifest
        ...(PUBLIC ? [{ find: /^@generated\/supplier-images\.json$/, replacement: PUBLIC_SUPPLIER }] : []),
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
    plugins: artifact ? [viteSingleFile({ removeViteModuleLoader: true })] : PUBLIC ? [bundleGraph(), withoutTestPages()] : [bundleGraph()],
  };
});
