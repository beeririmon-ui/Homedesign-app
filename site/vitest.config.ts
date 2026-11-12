import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  // S20: the web's generated data, as web/vite.config.ts resolves it (web/src/copy.ts reads .generated/copy.he.json)
  resolve: { alias: [{ find: /^@generated\/(.*)$/, replacement: fileURLToPath(new URL('./.generated/$1', import.meta.url)) }] },
  test: {
    include: ['shared/test/**/*.test.ts', 'api/test/**/*.test.ts', 'web/test/**/*.test.ts', 'tools/test/**/*.test.ts'],
    environment: 'node',
    pool: 'forks',
    testTimeout: 20_000,
    // S13: the Worker's structured info rows (api/src/lib/log.ts) are not printed in the test run; warnings and errors are
    // eslint-disable-next-line no-control-regex -- the printed object carries colour codes
    onConsoleLog: (log) => !/level: (?:\u001b\[\d+m)?'info'/.test(log),
  },
});
