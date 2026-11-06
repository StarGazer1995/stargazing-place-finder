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

test('telescope controls initialize while external HTTPS requests stay pending', async ({ page }) => {
  let release!: () => void;
  const pending = new Promise<void>((resolve) => { release = resolve; });
  await page.route('https://**', async (route) => {
    await pending;
    await route.abort();
  });
  await page.route('**/api/**', (route) =>
    route.fulfill({ status: 503, json: { error: 'fixture unavailable' } }),
  );

  try {
    // DOMContentLoaded itself can wait for blocking remote stylesheets.
    await page.goto('/index-vite.html', { waitUntil: 'commit' });
    await expect(page.locator('#telescope-toggle-btn')).toBeAttached();
    await expect(page.locator('link[rel="stylesheet"][href^="https://"]')).toHaveCount(0);
    await expect(page.locator('#loading-overlay')).toHaveClass(/\bhidden\b/);
    await page.locator('#telescope-toggle-btn').click();
    await expect(page.locator('#telescope-toggle-btn')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#telescope-control-panel')).toBeVisible();
    await expect(page.locator('#aladin-lite-div canvas').first()).toBeVisible();
  } finally {
    release();
  }
});
