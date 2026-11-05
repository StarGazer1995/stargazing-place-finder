import { test, expect, type Page } from '@playwright/test';

const target = {
  name: 'M 31',
  ra: 10.6847,
  dec: 41.2688,
  type: 'Gx',
  surface_brightness: 13.5,
  angular_size_arcmin: 199.5,
  angular_size_min_arcmin: 70.8,
  suitability_score: 88,
  fov_fit_score: 1,
  filter_match_score: 1,
  mosaic_recommended: true,
  altitude_curve: [
    { time: 1793871600, alt: 35 },
    { time: 1793896800, alt: 75 },
  ],
};

const plan = {
  date: '2026-11-05',
  dusk: '2026-11-05T09:39:00.000',
  dawn: '2026-11-05T22:21:00.000',
  moon_phase: 'Waning Crescent',
  moon_illumination: 0.13,
  moon_delay_min: 0,
  slots: [{
    start_time: '2026-11-05T11:18:00+00:00',
    end_time: '2026-11-05T13:16:00+00:00',
    target_name: 'M 31',
    target_type: 'Gx',
    start_alt: 25.1,
    end_alt: 47.1,
    duration_min: 118,
    fov_fit_score: 1,
    suitability_score: 88,
    mosaic_recommended: true,
    notes: [],
  }],
  total_dark_min: 762,
  used_min: 652,
  warnings: [],
};

async function mockPageApi(page: Page) {
  const bodies: Record<'targets' | 'mosaic' | 'plan', unknown[]> = {
    targets: [],
    mosaic: [],
    plan: [],
  };
  const telescopeUrls: string[] = [];

  await page.route('**/api/health', (route) =>
    route.fulfill({ status: 200, json: { status: 'healthy', analyzer_initialized: true } }),
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
  await page.route('**/api/telescope/targets', (route) => {
    telescopeUrls.push(route.request().url());
    bodies.targets.push(route.request().postDataJSON());
    return route.fulfill({
      status: 200,
      json: { targets: [target], moon: { phase: 'Waning Crescent', illumination: 0.13 }, total: 1 },
    });
  });
  await page.route('**/api/telescope/mosaic', (route) => {
    telescopeUrls.push(route.request().url());
    bodies.mosaic.push(route.request().postDataJSON());
    return route.fulfill({
      status: 200,
      json: {
        grid: {
          target_name: 'M 31',
          rows: 1,
          cols: 1,
          total_panels: 1,
          overlap: 0.15,
          fov_width_deg: 1.5,
          fov_height_deg: 1,
          panels: [{
            row: 1,
            col: 1,
            ra_center: 10.6847,
            dec_center: 41.2688,
            corners: [[10, 41.5], [11, 41.5], [11, 41], [10, 41]],
          }],
        },
      },
    });
  });
  await page.route('**/api/telescope/plan', (route) => {
    telescopeUrls.push(route.request().url());
    bodies.plan.push(route.request().postDataJSON());
    return route.fulfill({
      status: 200,
      json: {
        targets: [target],
        moon: { phase: 'Waning Crescent', illumination: 0.13 },
        plan,
      },
    });
  });

  return { bodies, telescopeUrls };
}

test('telescope mode opens without any external HTTPS dependency', async ({ page }) => {
  await page.route('https://**', (route) => route.abort());
  await mockPageApi(page);

  await page.goto('/index-vite.html', { waitUntil: 'domcontentloaded' });
  await page.locator('#telescope-toggle-btn').click();

  await expect(page.locator('#aladin-container')).toBeVisible();
  await expect(page.locator('#aladin-lite-div canvas').first()).toBeVisible();
  await expect(page.locator('#telescope-control-panel')).toBeVisible();
  await expect(page.locator('#telescope-toggle-btn')).toHaveAttribute('aria-pressed', 'true');

  await page.locator('#telescope-toggle-btn').click();
  await expect(page.locator('#aladin-container')).toBeHidden();
  await expect(page.locator('#telescope-control-panel')).toBeHidden();
  await expect(page.locator('#telescope-toggle-btn')).toHaveAttribute('aria-pressed', 'false');
});

test('telescope mode drives same-origin target, mosaic and plan contracts', async ({ page }) => {
  await page.route('https://**', (route) => route.abort());
  const { bodies, telescopeUrls } = await mockPageApi(page);
  const pageErrors: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(String(error)));

  await page.goto('/index-vite.html', { waitUntil: 'domcontentloaded' });
  await page.locator('#telescope-toggle-btn').click();
  await expect(page.locator('#aladin-container')).toBeVisible();

  await page.locator('#match-targets-btn').click();
  await expect(page.locator('.target-card')).toContainText('M 31');
  await expect(page.locator('#moon-card')).toContainText('13%');

  await page.locator('.target-card').click();
  await expect(page.locator('#altitude-chart-panel')).toBeVisible();
  await expect(page.locator('#altitude-chart-title')).toContainText('M 31');
  await expect(page.locator('#mosaic-panel')).toBeVisible();

  await page.locator('#plan-btn').click();
  await expect(page.locator('#plan-panel')).toBeVisible();
  await expect(page.locator('#plan-panel-body')).toContainText('652 / 762');

  const pageOrigin = new URL(page.url()).origin;
  expect(telescopeUrls).toHaveLength(3);
  expect(telescopeUrls.every((url) => new URL(url).origin === pageOrigin)).toBe(true);

  expect(bodies.targets).toHaveLength(1);
  expect(bodies.targets[0]).toMatchObject({
    focal_length_mm: 250,
    sensor_width_mm: 23.5,
    sensor_height_mm: 15.7,
    time_zone: expect.any(String),
    limit: 100,
  });

  expect(bodies.mosaic).toHaveLength(1);
  expect(bodies.mosaic[0]).toMatchObject({
    target: {
      name: 'M 31',
      ra: 10.6847,
      dec: 41.2688,
      angular_size_arcmin: 199.5,
    },
    config: {
      focal_length_mm: 250,
      sensor_width_mm: 23.5,
      sensor_height_mm: 15.7,
    },
    overlap: 0.15,
  });

  expect(bodies.plan).toHaveLength(1);
  expect(bodies.plan[0]).toEqual(bodies.targets[0]);
  expect(pageErrors).toEqual([]);
});
