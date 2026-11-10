import { beforeEach, expect, it, vi } from 'vitest';
import { setIsTelescopeMode, setIsAnalysisMode, isTelescopeMode } from '@/state';
import { toggleTelescopeMode } from '@/features/telescope/telescope-ui';
const mocks = vi.hoisted(() => ({ sync: vi.fn(), ready: vi.fn(), overlay: vi.fn(), toast: vi.fn() }));
vi.mock('@/core/search', () => ({ syncSearchMode: mocks.sync }));
vi.mock('@/features/telescope/aladin-core', () => ({ ensureAladinReady: mocks.ready, updateFovOverlay: mocks.overlay, applyPreset: vi.fn() }));
vi.mock('@/features/telescope/targets', () => ({ matchTelescopeTargets: vi.fn(), fetchShootingPlan: vi.fn() }));
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
