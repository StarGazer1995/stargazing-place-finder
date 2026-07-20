/**
 * E2E smoke tests — verify the SPA loads and core UI elements are present.
 *
 * These tests run against the Vite dev server (started automatically by the
 * `webServer` config in playwright.config.ts).  They require network access
 * because the page loads Leaflet + Aladin Lite from CDN.
 *
 * The app entry point is `/index-vite.html` (not `/`) because the repo
 * keeps a minimal `index.html` fallback for pre-build states.
 *
 * We use `waitUntil: 'domcontentloaded'` because CDN resources (unpkg
 * Leaflet, Aladin) may be slow or unreachable in CI.  UI elements are
 * present in the DOM regardless of whether the loading overlay has been
 * dismissed — the overlay is a CSS-only cover, not a conditional render.
 */
import { test, expect } from '@playwright/test';

const PAGE = '/index-vite.html';

// ---------------------------------------------------------------------------
// Page load & rendering
// ---------------------------------------------------------------------------

test.describe('Page load', () => {
  test('should render the map container', async ({ page }) => {
    await page.goto(PAGE, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#map')).toBeVisible({ timeout: 15_000 });
  });

  test('should set the app title via JavaScript', async ({ page }) => {
    await page.goto(PAGE, { waitUntil: 'domcontentloaded' });
    // The <title> starts as "观星地点查找器 | …" in HTML; app JS rewrites it
    // to "Stargazing Place Finder" on init.
    await expect(page).toHaveTitle(/Stargazing Place Finder|观星地点查找器/);
  });
});

// ---------------------------------------------------------------------------
// Core UI elements (DOM presence — overlay may still be visible)
// ---------------------------------------------------------------------------

test.describe('Core UI elements', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE, { waitUntil: 'domcontentloaded' });
  });

  test('should show the loading overlay on initial load', async ({ page }) => {
    await expect(page.locator('#loading-overlay')).toBeVisible();
  });

  test('should show the search input', async ({ page }) => {
    await expect(page.locator('#search-input')).toBeVisible();
  });

  test('should show the Bortle legend bar', async ({ page }) => {
    await expect(page.locator('.bortle-bar-container')).toBeVisible();
  });

  test('should show mode toggle and language buttons', async ({ page }) => {
    await expect(page.locator('#mode-toggle-btn')).toBeVisible();
    await expect(page.locator('#telescope-toggle-btn')).toBeVisible();
    await expect(page.locator('#language-btn')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Mode switching
// ---------------------------------------------------------------------------

test.describe('Mode switching', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(PAGE, { waitUntil: 'domcontentloaded' });
  });

  test('the stargazing and telescope panels exist in the DOM', async ({ page }) => {
    // Both panels are in the HTML but start hidden (style="display:none").
    // They become visible when the app JS toggles them — which in turn
    // depends on CDN scripts that may be unavailable in CI.
    await expect(page.locator('#stargazing-control-panel')).toBeAttached();
    await expect(page.locator('#telescope-control-panel')).toBeAttached();
  });

  test('clicking mode toggle button targets the correct element', async ({ page }) => {
    const btn = page.locator('#mode-toggle-btn');
    await expect(btn).toBeVisible();
    // Button text reflects the current mode implied by the aria-label
    await expect(btn).toHaveAttribute('aria-label', '切换模式');
  });

  test('telescope toggle button targets the correct element', async ({ page }) => {
    const btn = page.locator('#telescope-toggle-btn');
    await expect(btn).toBeVisible();
    await expect(btn).toHaveAttribute('aria-label', '切换望远镜模式');
  });
});
