import { test, expect } from '@playwright/test';

test('one search field routes places and sky objects by mode', async ({ page }) => {
  const places: string[] = [];
  const objects: string[] = [];
  await page.route(/^https:\/\//, (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === 'nominatim.openstreetmap.org' && url.pathname === '/search') {
      places.push(url.searchParams.get('q')!);
      return route.fulfill({ json: [{ lat: '31.23', lon: '121.47', display_name: '上海' }] });
    }
    if (url.pathname.endsWith('/properties')) {
      return route.fulfill({ contentType: 'text/plain', body: [
        'hips_version=1.4', 'hips_frame=equatorial', 'hips_order=3',
        'hips_tile_width=512', 'hips_tile_format=jpeg', 'dataproduct_type=image',
        'obs_title=Test survey',
      ].join('\n') });
    }
    return route.abort();
  });
  await page.route('**/api/telescope/resolve?*', (route) => {
    objects.push(new URL(route.request().url()).searchParams.get('name')!);
    return route.fulfill({ json: { name: 'M 42', ra: 83.8201, dec: -5.3876, source: 'local_catalog' } });
  });
  await page.route('**/api/health', (route) => route.fulfill({
    json: { status: 'healthy', analyzer_initialized: true },
  }));
  await page.route('**/api/light_pollution*', (route) => route.fulfill({
    json: { success: true, data: [], metadata: { total_points: 0 } },
  }));
  await page.goto('/index-vite.html', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#loading-overlay')).toHaveClass(/\bhidden\b/);
  const input = page.locator('#search-input');
  await expect(input).toHaveAttribute('aria-label', /搜索地点|Search location/);
  await input.fill('上海'); await input.press('Enter');
  await expect.poll(() => places).toEqual(['上海']);
  expect(objects).toEqual([]);

  await page.locator('#telescope-toggle-btn').click();
  await expect(page.locator('#aladin-lite-div .aladin-css')).toBeAttached();
  await expect(page.locator('#aladin-search-input')).toHaveCount(0);
  await expect(page.locator('#search-container input')).toHaveCount(1);
  await expect(input).toHaveAttribute('aria-label', /搜索天体|Search sky objects/);
  await expect(input).toHaveAttribute('placeholder', /M31/);
  await expect.poll(() => input.evaluate((el) => {
    const r = el.getBoundingClientRect();
    return document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2) === el;
  })).toBe(true);
  const coordinates = page.locator('.aladin-location input');
  const previousCoordinates = await coordinates.inputValue();
  await input.fill('M42'); await input.press('Enter');
  await expect.poll(() => objects).toEqual(['M42']);
  await expect(coordinates).not.toHaveValue(previousCoordinates);
  await expect(page.locator('#search-status')).toContainText('M 42');
  expect(places).toEqual(['上海']);

  await page.locator('#language-btn').click();
  await expect(input).toHaveAttribute('placeholder', /M31/);
  await expect(input).toHaveAttribute('aria-label', /搜索天体|Search sky objects/);
  await page.locator('#telescope-toggle-btn').click();
  await page.locator('#mode-toggle-btn').click();
  await expect(input).toHaveAttribute('aria-label', /搜索地点|Search location/);
  await input.fill('北京'); await input.press('Enter');
  await expect.poll(() => places).toEqual(['上海', '北京']);
  expect(objects).toEqual(['M42']);
});

test('catalog search moves the sky while all external survey requests are pending', async ({ page }) => {
  let release!: () => void;
  const pending = new Promise<void>((resolve) => { release = resolve; });
  await page.route(/^https:\/\//, async (route) => { await pending; await route.abort(); });
  await page.route('**/api/telescope/resolve?*', (route) => route.fulfill({
    json: { name: 'M 42', ra: 83.8201, dec: -5.3876, source: 'local_catalog' },
  }));
  await page.route('**/api/health', (route) => route.fulfill({
    json: { status: 'healthy', analyzer_initialized: true },
  }));
  await page.route('**/api/light_pollution*', (route) => route.fulfill({
    json: { success: true, data: [], metadata: { total_points: 0 } },
  }));
  try {
    await page.goto('/index-vite.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#loading-overlay')).toHaveClass(/\bhidden\b/);
    await page.locator('#telescope-toggle-btn').click();
    const coordinates = page.locator('.aladin-location input');
    await expect(coordinates).toBeVisible();
    const previous = await coordinates.inputValue();
    await page.locator('#search-input').fill('M42');
    await page.locator('#search-input').press('Enter');
    await expect(page.locator('#search-status')).toContainText('M 42');
    await expect(coordinates).not.toHaveValue(previous);
    await expect(page.locator('#search-input')).toHaveAttribute('aria-busy', 'false');
  } finally {
    release();
  }
});
