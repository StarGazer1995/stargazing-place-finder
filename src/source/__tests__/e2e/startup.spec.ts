import { test, expect } from '@playwright/test';

for (const apiState of ['pending', 'unavailable'] as const) {
  test(`startup releases controls while data is ${apiState}`, async ({ page }) => {
    // This checks the UI shell, not the availability or validity of sky data.
    await page.route('https://**', (route) => route.abort());
    let release!: () => void;
    const pending = new Promise<void>((resolve) => { release = resolve; });
    await page.route('**/api/**', async (route) => {
      if (apiState === 'pending') await pending;
      await route.fulfill({ status: 503, json: { error: 'fixture unavailable' } });
    });

    try {
      await page.goto('/index-vite.html', { waitUntil: 'domcontentloaded' });
      await expect(page.locator('#map')).toHaveClass(/leaflet-container/);
      await expect(page.locator('#loading-overlay')).toHaveClass(/\bhidden\b/);
      await page.locator('#search-input').fill('M 31');
      await expect(page.locator('#search-input')).toHaveValue('M 31');
      const language = await page.locator('#language-btn').innerText();
      await page.locator('#language-btn').click();
      await expect(page.locator('#language-btn')).not.toHaveText(language);
    } finally {
      release();
    }
  });
}
