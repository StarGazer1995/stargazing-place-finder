import { test, expect, type Page } from '@playwright/test';

async function expectSkyInViewport(page: Page): Promise<void> {
  // Aladin injects .aladin-container CSS at runtime. Offscreen canvases still
  // pass toBeVisible(), so verify screen coverage and hit testing as well.
  await expect(page.locator('#aladin-lite-div .aladin-css')).toBeAttached();
  await expect(page.locator('#aladin-container')).toBeInViewport({ ratio: 1 });
  await expect.poll(() => page.evaluate(() => {
    const sky = document.getElementById('aladin-lite-div')!;
    const rect = sky.getBoundingClientRect();
    const hit = document.elementFromPoint(window.innerWidth / 3, window.innerHeight / 2);
    return rect.x === 0 && rect.y === 0
      && rect.width === window.innerWidth && rect.height === window.innerHeight
      && !!hit && sky.contains(hit);
  })).toBe(true);
}

for (const network of ['unavailable', 'pending'] as const) {
  test(`sky covers the map after Aladin injects CSS with ${network} surveys`, async ({ page }) => {
    let release!: () => void;
    const pending = new Promise<void>((resolve) => { release = resolve; });
    await page.route('https://**', async (route) => {
      if (network === 'pending') await pending;
      await route.abort();
    });
    await page.route('**/api/health', (route) => route.fulfill({
      json: { status: 'healthy', analyzer_initialized: true },
    }));
    await page.route('**/api/light_pollution*', (route) => route.fulfill({
      json: { success: true, data: [], metadata: { total_points: 0 } },
    }));
    try {
      await page.setViewportSize({ width: 1500, height: 900 });
      await page.goto('/index-vite.html', { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#loading-overlay')).toHaveClass(/\bhidden\b/);
      await page.locator('#telescope-toggle-btn').click();
      await expectSkyInViewport(page);
      await page.setViewportSize({ width: 1024, height: 768 });
      await expectSkyInViewport(page);
      await page.locator('#telescope-toggle-btn').click();
      await expect(page.locator('#aladin-container')).toBeHidden();
      await expect(page.locator('#map')).toBeInViewport({ ratio: 1 });
      await page.locator('#telescope-toggle-btn').click();
      await expectSkyInViewport(page);
    } finally {
      release();
    }
  });
}
