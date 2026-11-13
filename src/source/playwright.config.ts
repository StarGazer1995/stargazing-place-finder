import { defineConfig, devices } from '@playwright/test';

const production = process.env.SPF_E2E_PRODUCTION === '1' || process.env.SPF_E2E_PREVIEW === '1';

export default defineConfig({
  testDir: '__tests__/e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],

  webServer: {
    command: production
      ? 'npm run build && npx vite preview --port 5173 --strictPort'
      : 'npx vite --port 5173 --strictPort',
    port: 5173,
    reuseExistingServer: !process.env.CI && !production,
    timeout: production ? 60_000 : 15_000,
  },
});
