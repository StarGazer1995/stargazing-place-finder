import { test, expect } from '@playwright/test';

const hope = {
  focal_length_mm: 280, aperture_mm: 60, sensor_width_mm: 23.5, sensor_height_mm: 15.7,
  sensor_pixel_size_um: 3.76, mount_type: 'equatorial', guiding_supported: false,
  reducer_factor: 1, barlow_factor: 1, central_obstruction_pct: 0, filter_type: null,
};

test('backend-only HOPE preset reaches matching, plan and mosaic without losing optics', async ({ page }) => {
  await page.route('https://**', route => route.abort());
  await page.route('**/api/health', route => route.fulfill({json: {status:'healthy', analyzer_initialized: true}}));
  await page.route('**/api/light_pollution**', route => route.fulfill({json: {success:true, data:[], metadata:{total_points:0}}}));
  await page.route('**/api/telescope/presets', route => route.fulfill({json: {hope_d60_asi2600mc_air: hope}}));
  const target = {
    name:'M 31', ra:10.6847, dec:41.2688, angular_size_arcmin:199.5,
    angular_size_min_arcmin:70.8, suitability_score:80, fov_fit_score:1,
    filter_match_score:1, mosaic_recommended:true,
    altitude_curve:[{time:1793871600,alt:35},{time:1793896800,alt:75}],
  };
  const requests: Record<string, any> = {};
  await page.route('**/api/telescope/targets', route => {
    requests.targets = route.request().postDataJSON();
    return route.fulfill({json:{targets:[target],moon:{phase:'New Moon',illumination:0},total:1}});
  });
  await page.route('**/api/telescope/plan', route => {
    requests.plan = route.request().postDataJSON();
    return route.fulfill({json:{targets:[target],plan:{slots:[], warnings:[]}}});
  });
  await page.route('**/api/telescope/mosaic', route => {
    requests.mosaic = route.request().postDataJSON();
    return route.fulfill({json:{grid:{rows:1,cols:1,total_panels:1,panels:[]}}});
  });
  await page.goto('/index-vite.html', {waitUntil:'domcontentloaded'});
  await page.locator('#telescope-toggle-btn').click();
  await expect(page.locator('#telescope-preset option')).toHaveCount(2);
  await page.locator('#telescope-preset').selectOption('hope_d60_asi2600mc_air');
  await expect(page.locator('#telescope-focal-length')).toHaveValue('280');
  await expect(page.locator('#fov-display')).toHaveText('4.8° × 3.2°');
  await page.locator('#match-targets-btn').click();
  await expect(page.locator('.target-card')).toContainText('M 31');
  expect(requests.targets).toMatchObject(hope);
  await page.locator('.target-card').click();
  await expect.poll(() => requests.mosaic?.config).toMatchObject(hope);
  await page.locator('#plan-btn').click();
  await expect.poll(() => requests.plan).toMatchObject(hope);
  await page.locator('#telescope-config-details > summary').click();
  await page.locator('#telescope-focal-length').fill('300');
  await expect(page.locator('#telescope-preset')).toHaveValue('custom');
  await page.locator('#match-targets-btn').click();
  await expect.poll(() => requests.targets?.focal_length_mm).toBe(300);
  expect(requests.targets).not.toHaveProperty('aperture_mm');
});
