import { test, expect, type Page } from '@playwright/test';

async function setup(page: Page) {
  await page.route('https://**', route => route.abort());
  await page.route('**/api/health', route => route.fulfill({json:{status:'healthy'}}));
  await page.route('**/api/light_pollution**', route => route.fulfill({json:{success:true,data:[]}}));
  await page.route('**/api/telescope/presets', route => route.fulfill({json:{}}));
  await page.goto('/index-vite.html');
}

async function selectArea(page: Page) {
  await page.locator('#mode-toggle-btn').click();
  await page.locator('#draw-area-button').click();
  await page.mouse.move(150, 200);
  await page.mouse.down();
  await page.mouse.move(280, 290, {steps:8});
  await page.mouse.up();
  await expect(page.locator('#analyze-button')).toBeEnabled();
  await expect(page.locator('.leaflet-popup')).toHaveCount(0);
}

test('direct selection suppresses point popups; switching workspaces preserves area and clears hints', async ({page}) => {
  await setup(page);
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  await selectArea(page);
  expect(errors).toEqual([]);
  await page.locator('#telescope-toggle-btn').click();
  await expect(page.locator('#mode-toggle-btn')).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('#status-indicator')).toBeHidden();
  await expect(page.locator('.bortle-bar-container')).toBeHidden();
  await page.locator('#mode-toggle-btn').click();
  await expect(page.locator('#telescope-toggle-btn')).toHaveAttribute('aria-pressed','false');
  await expect(page.locator('#stargazing-control-panel')).toBeVisible();
  await expect(page.locator('#analyze-button')).toBeEnabled();
});

test('cancelled analysis cannot publish late results, and the same area can be retried', async ({page}) => {
  await setup(page);
  let release!: () => void;
  const pending = new Promise<void>(resolve => {release = resolve;});
  let calls = 0;
  await page.route('**/api/analyze_stargazing_area', async route => {
    if (++calls === 1) await pending;
    await route.fulfill({json:{locations:[]}}).catch(() => {});
  });
  await selectArea(page);
  await page.locator('#analyze-button').click();
  await expect.poll(() => calls).toBe(1);
  await page.locator('#cancel-analysis-button').click();
  await expect(page.locator('#analyze-button')).toBeEnabled();
  release();
  await expect(page.locator('#results-panel')).toBeHidden();
  await page.locator('#analyze-button').click();
  await expect(page.locator('#results-panel')).toContainText('未找到');
  await expect(page.locator('#analyze-button')).toBeEnabled();
});

for (const width of [390, 768, 1280]) {
  test(`planner actions remain reachable and send explicit observer context at ${width}px`, async ({page}, info) => {
    await page.setViewportSize({width,height:844});
    await setup(page);
    let body: any;
    await page.route('**/api/telescope/targets', route => {
      body = route.request().postDataJSON();
      return route.fulfill({json:{targets:[],moon:null}});
    });
    await page.locator('#telescope-toggle-btn').click();
    await page.locator('#observation-details > summary').click();
    await page.locator('#observation-lat').fill('31.23');
    await page.locator('#observation-lng').fill('121.47');
    await page.locator('#observation-time').fill('2026-11-12T21:30');
    await page.locator('#observation-timezone').fill('Asia/Shanghai');
    const button = page.locator('#match-targets-btn');
    await expect(button).toBeInViewport({ratio:1});
    await button.click();
    await expect(page.locator('#target-results-list')).toContainText('未找到匹配目标');
    expect(body).toMatchObject({lat:31.23,lon:121.47,time:'2026-11-12 21:30:00',time_zone:'Asia/Shanghai'});
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(button).toBeInViewport({ratio:1});
    await expect(page.locator('#telescope-panel-header')).toBeInViewport({ratio:1});
    await page.screenshot({path:info.outputPath(`planner-${width}.png`)});
  });
}

test('changing observer invalidates a pending match and prevents stale publication', async ({page}) => {
  await setup(page);
  let release!: () => void;
  const pending = new Promise<void>(resolve => {release = resolve;});
  let calls = 0;
  await page.route('**/api/telescope/targets', async route => {
    calls++;
    await pending;
    await route.fulfill({json:{targets:[{name:'OLD',ra:10,dec:20}],moon:null}});
  });
  await page.locator('#telescope-toggle-btn').click();
  await page.locator('#match-targets-btn').click();
  await expect.poll(() => calls).toBe(1);
  await page.locator('#observation-details > summary').click();
  await page.locator('#observation-lat').fill('30');
  release();
  await expect(page.locator('#target-results-section')).toBeHidden();
  await expect(page.locator('#plan-btn')).toBeHidden();
  await expect(page.locator('#match-targets-btn')).toBeEnabled();
});

test('invalid observation input blocks matching, and a failed match can be retried', async ({page}) => {
  await setup(page);
  let calls = 0;
  await page.route('**/api/telescope/targets', route => {
    calls++;
    return route.fulfill({status: calls <= 2 ? 503 : 200,json:{targets:[],moon:null}});
  });
  await page.locator('#telescope-toggle-btn').click();
  await page.locator('#observation-details > summary').click();
  await page.locator('#observation-lat').fill('91');
  await page.locator('#match-targets-btn').click();
  await expect(page.locator('.target-error')).toBeVisible();
  expect(calls).toBe(0);
  await page.locator('#observation-lat').fill('30');
  await page.locator('#match-targets-btn').click();
  await expect(page.locator('.target-error')).toBeVisible();
  await expect(page.locator('#match-targets-btn')).toBeEnabled();
  await page.locator('#match-targets-btn').click();
  await expect(page.locator('#target-results-list')).toContainText('未找到匹配目标');
});


test('toolbar rectangle drawing also stays error-free in a module bundle', async ({page}) => {
  await setup(page);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.locator('#mode-toggle-btn').click();
  await expect(page.locator('.leaflet-draw-draw-rectangle')).not.toHaveCSS('background-image', 'none');
  await page.locator('.leaflet-draw-draw-rectangle').click();
  await page.mouse.move(150,200); await page.mouse.down();
  await page.mouse.move(280,290,{steps:10}); await page.mouse.up();
  await expect(page.locator('#analyze-button')).toBeEnabled();
  expect(errors).toEqual([]);
});
