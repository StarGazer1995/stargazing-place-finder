import { beforeEach, expect, it, vi } from 'vitest';
import { setIsTelescopeMode, setIsAnalysisMode, isTelescopeMode, setMap, setDrawControl, setResultsPanel, lastMatchBody, setLastMatchBody } from '@/state';
import { toggleTelescopeMode, jumpToTelescopeMode } from '@/features/telescope/telescope-ui';
const mocks = vi.hoisted(() => ({ sync: vi.fn(), ready: vi.fn(), overlay: vi.fn(), toast: vi.fn() }));
vi.mock('@/core/search', () => ({ syncSearchMode: mocks.sync }));
vi.mock('@/features/telescope/aladin-core', () => ({ ensureAladinReady: mocks.ready, updateFovOverlay: mocks.overlay, applyPreset: vi.fn() }));
vi.mock('@/features/telescope/targets', () => ({ matchTelescopeTargets: vi.fn(), fetchShootingPlan: vi.fn(), invalidateTargetRequests: vi.fn() }));
vi.mock('@/features/telescope/target-renderer', () => ({ bindTargetInteractions: vi.fn() }));
vi.mock('@/utils/dom', () => ({ showToast: mocks.toast }));
beforeEach(() => {
  vi.resetAllMocks(); setIsTelescopeMode(false); setIsAnalysisMode(false);
  document.body.innerHTML = '<div id="telescope-control-panel"></div><div id="aladin-container"></div><div id="telescope-status"></div><button id="telescope-toggle-btn"></button>';
  mocks.ready.mockResolvedValue({});
});
it('synchronizes search routing when entering and leaving telescope mode', async () => {
  await toggleTelescopeMode();
  expect(isTelescopeMode).toBe(true); expect(mocks.sync).toHaveBeenCalledOnce();
  expect(mocks.overlay).toHaveBeenCalledOnce();
  expect(document.getElementById('telescope-toggle-btn')!.getAttribute('aria-pressed')).toBe('true');
  await toggleTelescopeMode();
  expect(isTelescopeMode).toBe(false); expect(mocks.sync).toHaveBeenCalledTimes(2);
  expect(document.getElementById('aladin-container')!.style.display).toBe('none');
});
it('restores geographic search when sky initialization fails', async () => {
  mocks.ready.mockRejectedValue(new Error('WebGL unavailable'));
  await toggleTelescopeMode();
  expect(isTelescopeMode).toBe(false); expect(mocks.sync).toHaveBeenCalledTimes(2);
  expect(mocks.toast).toHaveBeenCalledWith('Aladin Lite 加载失败: WebGL unavailable', 'error');
  expect(document.getElementById('telescope-toggle-btn')!.getAttribute('aria-pressed')).toBe('false');
});


it('restores analysis controls and results while keeping only one workspace pressed', async () => {
  const removeControl = vi.fn(), addControl = vi.fn();
  setMap({closePopup:vi.fn(),removeControl,addControl,invalidateSize:vi.fn()});
  const control = {}; setDrawControl(control); setIsAnalysisMode(true);
  document.body.insertAdjacentHTML('beforeend', '<button id="mode-toggle-btn"></button><div class="bortle-bar-container"></div><div id="status-indicator"></div><div class="info-panel"></div><div id="stargazing-control-panel"></div><div id="results-panel">selected results</div>');
  setResultsPanel(document.getElementById('results-panel'));
  await toggleTelescopeMode();
  expect(document.getElementById('mode-toggle-btn')!.getAttribute('aria-pressed')).toBe('false');
  expect(document.getElementById('results-panel')!.style.display).toBe('none');
  await toggleTelescopeMode();
  expect(addControl).toHaveBeenCalledWith(control);
  expect(document.getElementById('results-panel')!.style.display).toBe('block');
  expect(document.querySelector<HTMLElement>('.bortle-bar-container')!.hidden).toBe(false);
  setDrawControl(null); setMap(null); setResultsPanel(null);
});

it('sets the geographic observer without slewing the star chart to geographic coordinates', async () => {
  document.body.insertAdjacentHTML('beforeend', '<input id="observation-lat"><input id="observation-lng">');
  setLastMatchBody({lat:0,lon:0});
  await jumpToTelescopeMode(31.23,121.47,'selected site');
  expect(lastMatchBody).toBeNull();
  expect((document.getElementById('observation-lat') as HTMLInputElement).value).toBe('31.23000');
  expect((document.getElementById('observation-lng') as HTMLInputElement).value).toBe('121.47000');
  expect(isTelescopeMode).toBe(true);
});
