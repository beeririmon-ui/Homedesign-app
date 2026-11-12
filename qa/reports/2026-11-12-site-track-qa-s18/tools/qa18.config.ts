// QA S18: my own Playwright run inside the scratchpad copy (site/qa18/), against my server (HD_BASE_URL). Same browser
// and launch options as the copy's playwright.config.ts.
import { defineConfig, devices } from '@playwright/test';
const launchOptions = { executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] };
export default defineConfig({
  testDir: '.',
  testMatch: /qa-s18\.spec\.ts/,
  timeout: 180_000,
  expect: { timeout: 10_000 },
  workers: 1,
  reporter: [['list']],
  use: { baseURL: process.env.HD_BASE_URL, locale: 'he-IL', ...devices['Desktop Chrome'], launchOptions },
});
