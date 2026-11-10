import { beforeEach, expect, it, vi } from 'vitest';
import { initTelescopeMode } from '@/features/telescope/telescope-ui';
import { lastMatchBody, lastTargets, setLastMatchBody, setLastTargets } from '@/state';
const mocks = vi.hoisted(() => ({ load: vi.fn(), apply: vi.fn(), overlay: vi.fn(), toast: vi.fn(), match: vi.fn(), plan: vi.fn(), bind: vi.fn() }));
vi.mock('@/core/search', () => ({ syncSearchMode: vi.fn() }));
vi.mock('@/features/telescope/presets', () => ({ loadTelescopePresets: mocks.load }));
vi.mock('@/features/telescope/aladin-core', () => ({ ensureAladinReady: vi.fn(), updateFovOverlay: mocks.overlay, applyPreset: mocks.apply }));
vi.mock('@/features/telescope/targets', () => ({ matchTelescopeTargets: mocks.match, fetchShootingPlan: mocks.plan }));
vi.mock('@/features/telescope/target-renderer', () => ({ bindTargetInteractions: mocks.bind }));
vi.mock('@/utils/dom', () => ({ showToast: mocks.toast }));
beforeEach(() => {
  vi.resetAllMocks(); mocks.load.mockResolvedValue(undefined);
  document.body.innerHTML = '<select id="telescope-preset"><option value="custom">Custom</option><option value="hope">HOPE</option></select><input id="telescope-focal-length"><input id="telescope-sensor-width"><input id="telescope-sensor-height"><select id="telescope-target-sort"><option value="fov">FOV</option></select><select id="telescope-camera-type"><option value="color">Color</option></select><button id="match-targets-btn"></button><button id="plan-btn"></button><input id="telescope-rotation"><span id="rotation-value"></span><div id="target-results-list"></div><div id="target-results-section"></div><div id="plan-panel"></div>';
});
function oldResult() {
  setLastMatchBody({ focal_length: 250, sensor_width: 23.5, sensor_height: 15.7, longitude: 120, latitude: 30, time: '2026-11-10', time_zone: 'UTC' });
  setLastTargets([{ name: 'old' } as any]);
  ['target-results-section', 'plan-btn', 'plan-panel'].forEach(id => document.getElementById(id)!.style.display = 'block');
}
function expectInvalidated() {
  expect(lastMatchBody).toBeNull(); expect(lastTargets).toEqual([]);
  ['target-results-section', 'plan-btn', 'plan-panel'].forEach(id => expect(document.getElementById(id)!.style.display).toBe('none'));
}
it('loads equipment and applies a preset while clearing previous matches', () => {
  initTelescopeMode(); oldResult();
  const select = document.getElementById('telescope-preset') as HTMLSelectElement;
  select.value = 'hope'; select.dispatchEvent(new Event('change'));
  expect(mocks.load).toHaveBeenCalledWith(select); expect(mocks.apply).toHaveBeenCalledWith('hope');
  expect(mocks.overlay).toHaveBeenCalledOnce(); expectInvalidated();
});
it('switches manual optics to custom and clears previous matches', () => {
  initTelescopeMode(); oldResult();
  (document.getElementById('telescope-preset') as HTMLSelectElement).value = 'hope';
  document.getElementById('telescope-focal-length')!.dispatchEvent(new Event('input'));
  expect((document.getElementById('telescope-preset') as HTMLSelectElement).value).toBe('custom');
  expect(mocks.overlay).toHaveBeenCalledOnce(); expectInvalidated();
});
it('invalidates matches and plans when camera or sorting changes', () => {
  initTelescopeMode();
  for (const id of ['telescope-target-sort', 'telescope-camera-type']) {
    oldResult(); document.getElementById(id)!.dispatchEvent(new Event('change')); expectInvalidated();
  }
  expect(mocks.toast).toHaveBeenCalledWith('选项已更新，请重新匹配目标。', 'info');
});
it('binds matching, planning, rotation and target interactions', () => {
  initTelescopeMode();
  document.getElementById('match-targets-btn')!.click(); document.getElementById('plan-btn')!.click();
  expect(mocks.match).toHaveBeenCalledOnce(); expect(mocks.plan).toHaveBeenCalledOnce();
  const rotation = document.getElementById('telescope-rotation') as HTMLInputElement;
  rotation.value = '90'; rotation.dispatchEvent(new Event('input'));
  expect(document.getElementById('rotation-value')!.textContent).toBe('90°');
  expect(mocks.overlay).toHaveBeenCalledOnce(); expect(mocks.bind).toHaveBeenCalledWith(document.getElementById('target-results-list'));
});
it('keeps custom matching available when catalog loading fails', async () => {
  mocks.load.mockRejectedValue(new Error('offline')); initTelescopeMode();
  await vi.waitFor(() => expect(mocks.toast).toHaveBeenCalledWith(expect.stringContaining('可使用自定义参数'), 'error'));
  document.getElementById('match-targets-btn')!.click(); expect(mocks.match).toHaveBeenCalledOnce();
});
it('tolerates absent telescope controls', () => {
  document.body.innerHTML = ''; expect(() => initTelescopeMode()).not.toThrow(); expect(mocks.load).not.toHaveBeenCalled();
});
