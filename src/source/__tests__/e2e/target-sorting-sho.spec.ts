import { test, expect } from '@playwright/test';

test('shows sorting intent and camera-aware SHO advice without treating unknown lines as measured', async ({page}, testInfo) => {
  await page.setViewportSize({width: 1440, height: 1000});
  await page.route('https://**', route => route.abort());
  await page.route('**/reverse?**', route => route.fulfill({json:{display_name:'示例观测点（测试数据）'}}));
  await page.route('**/api/health', route => route.fulfill({json:{status:'healthy', analyzer_initialized:true}}));
  await page.route('**/api/light_pollution**', route => route.fulfill({json:{success:true,data:[],metadata:{total_points:0}}}));
  await page.route('**/api/telescope/presets', route => route.fulfill({json:{
    hope_d60_asi2600mc_air: {focal_length_mm:280,sensor_width_mm:23.5,sensor_height_mm:15.7,aperture_mm:60,camera_type:'color'},
  }}));
  const requests: any[] = [];
  await page.route('**/api/telescope/targets', route => {
    const body = route.request().postDataJSON();
    requests.push(body);
    const common = {ra:83.8,dec:-5.4,angular_size_arcmin:66,suitability_score:80,fov_fit_score:0.6,filter_match_score:0.6,
      visibility:{total_minutes:180,longest_minutes:120,available_now:true,windows:[{start:1794312000,end:1794319200}]}};
    const nebula = {...common,name:'M 42',type:'HII',sho_advice:{status:'consider',label:'SHO：可考虑，先核实 SII',
      reason:'发射星云可考虑窄带；目录类型不能证明 SII 和 OIII 足够强。',
      camera_note:body.camera_type === 'mono' ? '单色相机：可分别采集 SII、Hα、OIII。' : '彩色相机：常见 Hα/OIII 双窄带缺少独立 SII；需额外 SII 或配对双窄带采集。',
      basis:'catalog_type_only',sii_strength:null}};
    const galaxy = {...common,name:'M 31',type:'AGN',sho_advice:{status:'not_primary',label:'SHO：不建议作为主体方案',reason:'主体优先宽带 RGB/LRGB。',camera_note:'完整 SHO 需要独立通道。',basis:'catalog_type_only',sii_strength:null}};
    return route.fulfill({json:{targets:body.sort_by === 'fov' ? [galaxy,nebula] : [nebula,galaxy],moon:{phase:'New Moon',illumination:0}}});
  });
  await page.goto('/index-vite.html', {waitUntil:'domcontentloaded'});
  await page.locator('#telescope-toggle-btn').click();
  await page.locator('#telescope-preset').selectOption('hope_d60_asi2600mc_air');
  await expect(page.locator('#telescope-camera-type')).toHaveValue('color');
  await expect(page.locator('#telescope-target-sort')).toHaveValue('imaging_time');
  await page.locator('#match-targets-btn').click();
  await expect(page.locator('.target-card').first()).toContainText('M 42');
  await expect(page.locator('#target-query-time')).toContainText('计算于');
  await expect(page.locator('.target-card').first()).toContainText('剩余 180 分钟 · 最长连续 120 分钟');
  await expect(page.locator('.target-sho-consider')).toContainText('先核实 SII');
  await expect(page.locator('.target-sho-not_primary')).toContainText('不建议');
  await page.locator('.target-sho-details summary').first().click();
  await expect(page.locator('.target-sho-details').first()).toContainText('配对双窄带');
  const cameraNote = page.locator('.target-sho-details').first().locator('p').nth(1);
  await cameraNote.scrollIntoViewIfNeeded();
  await expect(cameraNote).toBeInViewport({ratio: 1});
  expect(await page.locator('.target-card').first().evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await expect(page.locator('#altitude-chart-panel')).toBeHidden();
  expect(requests[0]).toMatchObject({sort_by:'imaging_time',camera_type:'color',focal_length_mm:280});
  await page.locator('#target-results-section').screenshot({path: testInfo.outputPath('target-sorting-sho.png')});
  await page.locator('#telescope-camera-type').selectOption('mono');
  await expect(page.locator('#target-results-section')).toBeHidden();
  await expect(page.locator('#plan-btn')).toBeHidden();
  await page.locator('#telescope-target-sort').selectOption('fov');
  await page.locator('#match-targets-btn').click();
  await expect(page.locator('.target-card').first()).toContainText('M 31');
  await page.locator('.target-sho-details summary').nth(1).click();
  await expect(page.locator('.target-sho-details').nth(1)).toContainText('单色相机');
  expect(requests[1]).toMatchObject({sort_by:'fov',camera_type:'mono'});
});
