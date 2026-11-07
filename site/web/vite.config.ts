import { defineConfig } from 'vite';
import { viteSingleFile } from 'vite-plugin-singlefile';
import { fileURLToPath } from 'node:url';

const r = (p: string) => fileURLToPath(new URL(p, import.meta.url));

export default defineConfig(({ mode }) => {
  const artifact = mode === 'artifact';
  return {
    root: r('.'),
    publicDir: artifact ? false : 'public',
    esbuild: { jsx: 'automatic', jsxImportSource: 'preact', legalComments: 'none' },
    define: {
      __ARTIFACT__: JSON.stringify(artifact),
      __MEDIA_BASE__: JSON.stringify(artifact ? 'media/' : '/media/'),
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
          // so is the story prototype (tools/make-story-page.ts writes test/story/index.html)
          rollupOptions: { input: { main: r('index.html'), test: r('test/index.html'), story: r('test/story/index.html') } },
        },
    plugins: artifact ? [viteSingleFile({ removeViteModuleLoader: true })] : [],
  };
});
