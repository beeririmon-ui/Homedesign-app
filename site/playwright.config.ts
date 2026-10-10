import { defineConfig, devices } from '@playwright/test';

/**
 * e2e and a11y run against the local production build: `npm run build`, then `npm run preview` (wrangler dev serving
 * web/dist and the Worker API with a local D1, mock payments and mock supplier). No account, no network.
 * Chromium comes from /opt/pw-browsers (never `playwright install` here); CI sets PW_CHROMIUM to its own path.
 */
const executablePath = process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium';
const launchOptions = { executablePath, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] };
const BASE = process.env.HD_BASE_URL ?? 'http://127.0.0.1:8788';

export default defineConfig({
  testDir: 'e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : [['list']],
  use: { baseURL: BASE, locale: 'he-IL', trace: 'retain-on-failure', launchOptions },
  webServer: process.env.HD_BASE_URL
    ? undefined
    : { command: 'npm run preview', url: `${BASE}/api/health`, reuseExistingServer: true, timeout: 120_000, stdout: 'ignore' },
  projects: [
    { name: 'e2e', testMatch: /(flow|perf|swap-diff|hotspots)\.spec\.ts/, use: { ...devices['Desktop Chrome'], launchOptions } },
    { name: 'a11y', testMatch: /a11y\.spec\.ts/, use: { ...devices['Desktop Chrome'], launchOptions } },
  ],
});
