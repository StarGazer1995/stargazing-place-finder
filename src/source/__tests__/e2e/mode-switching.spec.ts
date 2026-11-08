import { test, expect, type Page } from '@playwright/test';

async function mockBaseApis(page: Page): Promise<void> {
  await page.route('https://**', (route) => route.abort());
  await page.route('**/api/health', (route) =>
    route.fulfill({
      status: 200,
      json: { status: 'healthy', analyzer_initialized: true },
    }),
  );
  await page.route('**/api/light_pollution*', (route) => {
    if (new URL(route.request().url()).pathname.includes('/tiles/')) {
      return route.fulfill({ status: 200, contentType: 'image/png', body: '' });
    }
    return route.fulfill({
      status: 200,
      json: {
        success: true,
        data: [{ lat: 39.9, lng: 116.4, bortle: 6, intensity: 0.4, sqm: 18.5 }],
        metadata: { total_points: 1 },
      },
    });
  });
}

async function openApp(page: Page): Promise<void> {
  await mockBaseApis(page);
  await page.goto('/index-vite.html', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#loading-overlay')).toHaveClass(/\bhidden\b/);
  await expect(page.locator('#map')).toHaveClass(/leaflet-container/);
}

async function expectBrowseMode(page: Page): Promise<void> {
  await expect(page.locator('#mode-toggle-btn')).toHaveAttribute('aria-pressed', 'false');
  await expect(page.locator('#telescope-toggle-btn')).toHaveAttribute('aria-pressed', 'false');
  await expect(page.locator('#stargazing-control-panel')).toBeHidden();
  await expect(page.locator('#telescope-control-panel')).toBeHidden();
  await expect(page.locator('#aladin-container')).toBeHidden();
  await expect(page.locator('#map')).toBeVisible();
  await expect(page.locator('#search-input')).toBeVisible();
}

async function expectAnalysisMode(page: Page): Promise<void> {
  await expect(page.locator('#mode-toggle-btn')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#telescope-toggle-btn')).toHaveAttribute('aria-pressed', 'false');
  await expect(page.locator('#stargazing-control-panel')).toBeVisible();
  await expect(page.locator('#telescope-control-panel')).toBeHidden();
  await expect(page.locator('#aladin-container')).toBeHidden();
  await expect(page.locator('#map')).toBeVisible();
  await expect(page.locator('#search-input')).toBeVisible();
}

async function expectTelescopeMode(
  page: Page,
  analysisWasActive = false,
): Promise<void> {
  await expect(page.locator('#mode-toggle-btn')).toHaveAttribute(
    'aria-pressed',
    String(analysisWasActive),
  );
  await expect(page.locator('#telescope-toggle-btn')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#stargazing-control-panel')).toBeHidden();
  await expect(page.locator('#telescope-control-panel')).toBeVisible();
  await expect(page.locator('#aladin-container')).toBeVisible();
  await expect(page.locator('#aladin-lite-div canvas').first()).toBeVisible();
  await expect(page.locator('#search-input')).toBeVisible();
}

test('browse, analysis and telescope modes switch in either direction', async ({ page }) => {
  // Analysis keeps its selected state while telescope is active. Going back from
  // telescope therefore returns to analysis before returning to browse.
  await openApp(page);
  await expectBrowseMode(page);

  await page.locator('#mode-toggle-btn').click();
  await expectAnalysisMode(page);

  await page.locator('#telescope-toggle-btn').click();
  await expectTelescopeMode(page, true);

  const languageBefore = await page.locator('#language-btn').innerText();
  await page.locator('#language-btn').click();
  await expect(page.locator('#language-btn')).not.toHaveText(languageBefore);
  await expectTelescopeMode(page, true);

  await page.locator('#telescope-toggle-btn').click();
  await expectAnalysisMode(page);

  await page.locator('#mode-toggle-btn').click();
  await expectBrowseMode(page);
});

test('telescope mode opens and closes without disturbing analysis state', async ({ page }) => {
  await openApp(page);
  await expectBrowseMode(page);

  await page.locator('#telescope-toggle-btn').click();
  await expectTelescopeMode(page);

  await page.locator('#mode-toggle-btn').click();
  await expectTelescopeMode(page);

  await page.locator('#telescope-toggle-btn').click();
  await expectBrowseMode(page);

  await page.locator('#mode-toggle-btn').click();
  await expectAnalysisMode(page);

  await page.locator('#telescope-toggle-btn').click();
  await expectTelescopeMode(page, true);

  await page.locator('#telescope-toggle-btn').click();
  await expectAnalysisMode(page);
});
