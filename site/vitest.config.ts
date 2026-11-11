import { defineConfig } from 'vitest/config';

export default defineConfig({
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
