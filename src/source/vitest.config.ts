import { defineConfig } from 'vitest/config';
import { resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(__dirname, 'js'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['__tests__/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['js/**/*.ts'],
      exclude: [
        // Type declarations (no runtime code)
        'js/vite-env.d.ts',
        'js/types/**/*.ts',
        // Entry point — thin orchestrator, verified by smoke test
        'js/index.ts',
        // Aladin Lite CDN bridge — cannot unit-test without browser + network
        'js/features/telescope/aladin-core.ts',
      ],
      // No global thresholds — per-PR enforcement is done by diff-cover in CI
      reporter: ['text', 'cobertura', 'html'],
      reportsDirectory: './coverage',
    },
  },
});
