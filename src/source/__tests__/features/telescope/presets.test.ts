import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { loadTelescopePresets, selectedOpticalConfig, TELESCOPE_PRESETS } from '../../../js/features/telescope/presets';
import { applyPreset, calculateFovFromInputs, calculateFov } from '../../../js/features/telescope/aladin-core';
import { buildTargetRequest } from '../../../js/features/telescope/targets';

const hope = {
  focal_length_mm: 280, aperture_mm: 60, sensor_width_mm: 23.5, sensor_height_mm: 15.7,
  sensor_pixel_size_um: 3.76, mount_type: 'equatorial', guiding_supported: false,
  reducer_factor: 0.8, barlow_factor: 1, central_obstruction_pct: 0, filter_type: 'Hα',
};
let select: HTMLSelectElement;
beforeEach(() => {
  document.body.innerHTML = '<select id="telescope-preset"><option value="custom">自定义</option></select><input id="telescope-focal-length" value="250"><input id="telescope-sensor-width" value="23.5"><input id="telescope-sensor-height" value="15.7">';
  select = document.querySelector('select')!;
  for (const key of Object.keys(TELESCOPE_PRESETS)) if (key !== 'custom') delete TELESCOPE_PRESETS[key];
});
afterEach(() => vi.unstubAllGlobals());

function reply(configs: unknown, ok = true) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok, status: ok ? 200 : 503, json: async () => configs }));
}

describe('server-owned equipment presets', () => {
  it('loads new server equipment, applies the optics, and sends the complete config', async () => {
    reply({ hope_d60_asi2600mc_air: hope });
    await loadTelescopePresets(select);
    expect(select.options.length).toBe(2);
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/telescope/presets'), expect.any(Object));
    select.value = 'hope_d60_asi2600mc_air';
    applyPreset(select.value);
    expect((document.getElementById('telescope-focal-length') as HTMLInputElement).value).toBe('280');
    expect(calculateFovFromInputs()).toEqual(calculateFov(224, 23.5, 15.7));
    expect(buildTargetRequest(280, 23.5, 15.7, 30, 120, 'UTC', '2024-01-01', 20, selectedOpticalConfig())).toMatchObject(hope);
    select.value = 'custom';
    expect(selectedOpticalConfig()).toBeUndefined();
    expect(buildTargetRequest(100, 10, 10, 30, 120, 'UTC', '2024-01-01', 20, selectedOpticalConfig())).not.toHaveProperty('aperture_mm');
  });

  it('preserves a selected preset on refresh and removes retired entries', async () => {
    reply({ one: hope, two: hope });
    await loadTelescopePresets(select);
    select.value = 'one';
    reply({ one: hope });
    await loadTelescopePresets(select);
    expect(select.value).toBe('one');
    expect(TELESCOPE_PRESETS.two).toBeUndefined();
    reply({ three: hope });
    await loadTelescopePresets(select);
    expect(select.value).toBe('custom');
  });

  it('renders equipment names as text', async () => {
    reply({ '<img src=x onerror=alert(1)>': hope });
    await loadTelescopePresets(select);
    expect(select.querySelector('img')).toBeNull();
    expect(select.options[1]!.textContent).toContain('<img');
  });

  it('keeps custom optics usable after HTTP, network, JSON or invalid-data failures', async () => {
    reply({}, false);
    await expect(loadTelescopePresets(select)).rejects.toThrow('503');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    await expect(loadTelescopePresets(select)).rejects.toThrow('offline');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok: true, json: async () => {throw new Error('JSON');}}));
    await expect(loadTelescopePresets(select)).rejects.toThrow('JSON');
    reply({ broken: {focal_length_mm: 0} });
    await expect(loadTelescopePresets(select)).rejects.toThrow('无效');
    expect(select.options.length).toBe(1);
    expect(selectedOpticalConfig()).toBeUndefined();
  });

  it('ignores unknown and custom presets when applying inputs', () => {
    applyPreset('missing');
    applyPreset('custom');
    expect((document.getElementById('telescope-focal-length') as HTMLInputElement).value).toBe('250');
    document.body.innerHTML = '';
    expect(selectedOpticalConfig()).toBeUndefined();
  });
});
