import { test, expect } from '@playwright/test';

for (const width of [390, 1280]) {
  test(`coordinate popup keeps readable text and a working planner action at ${width}px`, async ({page}, info) => {
    await page.setViewportSize({width, height:844});
    await page.route('https://**', route => route.abort());
    await page.route('**/api/health', route => route.fulfill({json:{status:'healthy'}}));
    await page.route('**/api/light_pollution**', route => route.fulfill({json:{success:true,data:[]}}));
    await page.route('**/api/telescope/presets', route => route.fulfill({json:{}}));
    await page.route('**/api/coordinate_analysis?**', route => route.fulfill({json:{
      success:true, data:{light_pollution:{bortle_class:4,sqm_value:20.4,intensity:0.263,description:'乡村/郊区过渡'}},
    }}));
    await page.goto('/index-vite.html');
    await expect(page.locator('#loading-overlay')).toBeHidden();
    await page.locator('#map').click({position:{x:width / 2, y:350}});
    const popup = page.locator('.leaflet-popup');
    await expect(popup).toContainText('20.4');
    await expect(popup.getByRole('button',{name:/在此拍摄/})).toBeVisible();

    const colors = await popup.evaluate(root => {
      const rgb = (value:string) => value.match(/[\d.]+/g)!.map(Number);
      const luminance = (value:string) => {
        const [r,g,b] = rgb(value).slice(0,3).map(v => {
          const s = v! / 255;
          return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
        });
        return r! * 0.2126 + g! * 0.7152 + b! * 0.0722;
      };
      const contrast = (foreground:string, background:string) => {
        const a=luminance(foreground), b=luminance(background);
        return (Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
      };
      const background = (element:Element):string => {
        const color = getComputedStyle(element).backgroundColor;
        const values = rgb(color);
        if (values.length === 3 || values[3] === 1) return color;
        return element.parentElement ? background(element.parentElement) : 'rgb(255,255,255)';
      };
      const wrapper = root.querySelector('.leaflet-popup-content-wrapper')!;
      return {
        wrapper:getComputedStyle(wrapper).backgroundColor,
        tip:getComputedStyle(root.querySelector('.leaflet-popup-tip')!).backgroundColor,
        text:Array.from(root.querySelectorAll('h4,h5,p,strong,li,button,a.leaflet-popup-close-button'))
          .filter(e => !!e.textContent?.trim())
          .map(e => ({text:e.textContent!.trim(), ratio:contrast(getComputedStyle(e).color,background(e))})),
      };
    });
    expect(colors.wrapper).toBe(colors.tip);
    expect(colors.text.length).toBeGreaterThan(8);
    for (const sample of colors.text) expect(sample.ratio, sample.text).toBeGreaterThanOrEqual(4.5);
    await popup.screenshot({path:info.outputPath(`popup-${width}.png`)});
    const action = popup.getByRole('button',{name:/在此拍摄/});
    const latitude = Number(await action.getAttribute('data-lat'));
    await action.click();
    await expect(page.locator('#telescope-control-panel')).toBeVisible();
    await expect(page.locator('#observation-lat')).toHaveValue(latitude.toFixed(5));
  });
}
