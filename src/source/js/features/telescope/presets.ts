import { API_CONFIG, fetchWithTimeout } from '../../core/api';
import type { TelescopeConfig, TelescopePreset } from '../../types/telescope';

// The API owns presets; custom optics remain usable when it is unavailable.
export const TELESCOPE_PRESETS: Record<string, TelescopePreset> = {
  custom: { name: '自定义' },
};

export async function loadTelescopePresets(select: HTMLSelectElement): Promise<void> {
  const response = await fetchWithTimeout(`${API_CONFIG.baseUrl}/api/telescope/presets`, {}, 10_000);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const configs: Record<string, TelescopeConfig> = await response.json();
  const entries = Object.entries(configs).map(([key, config]) => {
    if (!(config.focal_length_mm > 0 && (config.sensor_width_mm ?? 0) > 0 && (config.sensor_height_mm ?? 0) > 0)) {
      throw new Error(`无效的设备预设: ${key}`);
    }
    const name = key === 'hope_d60_asi2600mc_air'
      ? 'HOPE D60 + ASI2600MC Air' : key.replace(/[_-]/g, ' ');
    return [key, {
      name, config,
      focalLength: config.focal_length_mm,
      sensorWidth: config.sensor_width_mm!, sensorHeight: config.sensor_height_mm!,
    }] as const;
  });
  const selected = select.value;
  for (const key of Object.keys(TELESCOPE_PRESETS)) {
    if (key !== 'custom') delete TELESCOPE_PRESETS[key];
  }
  const custom = new Option('自定义', 'custom');
  select.replaceChildren(custom);
  for (const [key, preset] of entries) {
    TELESCOPE_PRESETS[key] = preset;
    select.add(new Option(`${preset.name} (${preset.focalLength}mm / ${preset.sensorWidth}×${preset.sensorHeight}mm)`, key));
  }
  select.value = TELESCOPE_PRESETS[selected] ? selected : 'custom';
}

export function selectedOpticalConfig(): TelescopeConfig | undefined {
  const select = document.getElementById('telescope-preset') as HTMLSelectElement | null;
  return TELESCOPE_PRESETS[select?.value ?? 'custom']?.config;
}
