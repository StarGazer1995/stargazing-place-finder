// =============================================================================
// Telescope UI — panel bindings, mode switching, preset handling
// =============================================================================

import { isTelescopeMode, isAnalysisMode, aladinInstance, map, drawControl, resultsPanel } from '../../state';
import { setIsTelescopeMode, setLastMatchBody, setLastTargets } from '../../state';
import { showToast } from '../../utils/dom';
import { syncSearchMode } from '../../core/search';
import { ensureAladinReady, updateFovOverlay, applyPreset } from './aladin-core';
import { initObservationContext, setObservationLocation, syncObserverFromMap } from './observation-context';
import { stopDrawing } from '../stargazing/draw';
import { cancelAreaAnalysis } from '../stargazing/analyzer';
import { loadTelescopePresets } from './presets';
import { matchTelescopeTargets, fetchShootingPlan, invalidateTargetRequests } from './targets';
import { bindTargetInteractions } from './target-renderer';

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

export function invalidateTargetResults(): void {
  invalidateTargetRequests();
  try { aladinInstance?.removeCatalogs(); } catch { /* sky may be initializing */ }
  setLastMatchBody(null);
  setLastTargets([]);
  ['target-results-section', 'plan-btn', 'plan-panel', 'moon-card', 'mosaic-panel', 'mosaic-controls', 'altitude-chart-panel'].forEach((id) => {
    const element = document.getElementById(id);
    if (element) element.style.display = 'none';
  });
}

/** Wire up telescope panel interactions (runs once at page load). */
export function initTelescopeMode(): void {
  initObservationContext(invalidateTargetResults);
  // ── Preset selector ──
  const presetSelect = document.getElementById('telescope-preset') as HTMLSelectElement | null;
  if (presetSelect) {
    void loadTelescopePresets(presetSelect).catch(() => {
      showToast('设备列表加载失败，可使用自定义参数。刷新页面可重试。', 'error');
    });
    presetSelect.addEventListener('change', function (this: HTMLSelectElement) {
      applyPreset(this.value);
      invalidateTargetResults();
      updateFovOverlay();
    });
  }

  // ── Manual input changes ──
  ['telescope-focal-length', 'telescope-sensor-width', 'telescope-sensor-height'].forEach((id) => {
    const el = document.getElementById(id) as HTMLInputElement | null;
    if (el) {
      el.addEventListener('input', () => {
        const ps = document.getElementById('telescope-preset') as HTMLSelectElement | null;
        if (ps) ps.value = 'custom';
        invalidateTargetResults();
        updateFovOverlay();
      });
    }
  });

  // ── Match button ──
  const matchBtn = document.getElementById('match-targets-btn');
  if (matchBtn) matchBtn.addEventListener('click', matchTelescopeTargets);

  // Controls apply to the next match; do not silently reorder a stale result pool.
  ['telescope-target-sort', 'telescope-camera-type'].forEach((id) => {
    document.getElementById(id)?.addEventListener('change', () => {
      invalidateTargetResults();
      showToast('选项已更新，请重新匹配目标。', 'info');
    });
  });

  // ── Plan button ──
  const planBtn = document.getElementById('plan-btn');
  if (planBtn) planBtn.addEventListener('click', fetchShootingPlan);

  // ── Mode toggle ──
  const toggleBtn = document.getElementById('telescope-toggle-btn');
  if (toggleBtn) toggleBtn.addEventListener('click', toggleTelescopeMode);

  // ── Rotation slider ──
  const rotSlider = document.getElementById('telescope-rotation') as HTMLInputElement | null;
  if (rotSlider) {
    rotSlider.addEventListener('input', () => {
      const value = document.getElementById('rotation-value');
      if (value) value.textContent = `${rotSlider.value}°`;
      updateFovOverlay();
    });
  }

  const targetList = document.getElementById('target-results-list');
  if (targetList) bindTargetInteractions(targetList);

}

// ---------------------------------------------------------------------------
// Mode toggle
// ---------------------------------------------------------------------------

let modeGeneration = 0;

/** Toggle telescope mode on/off. */
export async function toggleTelescopeMode(): Promise<void> {
  const generation = ++modeGeneration;
  const newMode = !isTelescopeMode;
  setIsTelescopeMode(newMode);
  syncSearchMode();

  const panel = document.getElementById('telescope-control-panel');
  const aladinContainer = document.getElementById('aladin-container');
  const status = document.getElementById('telescope-status');
  const toggleBtn = document.getElementById('telescope-toggle-btn');

  stopDrawing();
  cancelAreaAnalysis();
  map?.closePopup();
  const areaStatus = document.getElementById('status-indicator');
  if (areaStatus) areaStatus.style.display = 'none';
  const areaBtn = document.getElementById('mode-toggle-btn');
  areaBtn?.classList.toggle('active', !newMode && isAnalysisMode);
  areaBtn?.setAttribute('aria-pressed', String(!newMode && isAnalysisMode));
  document.body.classList.toggle('telescope-workspace', newMode);
  const legend = document.querySelector<HTMLElement>('.bortle-bar-container');
  if (legend) legend.hidden = newMode;
  if (drawControl) {
    map.removeControl(drawControl);
    if (!newMode && isAnalysisMode) map.addControl(drawControl);
  }
  if (newMode) {
    syncObserverFromMap();
    if (panel) panel.style.display = 'block';
    if (aladinContainer) aladinContainer.style.display = 'block';
    if (status) status.style.display = 'block';
    toggleBtn?.classList.add('active');
    toggleBtn?.setAttribute('aria-pressed', 'true');
    try {
      await ensureAladinReady();
      if (generation !== modeGeneration) return;
      updateFovOverlay();
    } catch (e: any) {
      if (generation !== modeGeneration) return;
      showToast('Aladin Lite 加载失败: ' + e.message, 'error');
      setIsTelescopeMode(false);
      document.body.classList.remove('telescope-workspace');
      if (legend) legend.hidden = false;
      areaBtn?.classList.toggle('active', isAnalysisMode);
      areaBtn?.setAttribute('aria-pressed', String(isAnalysisMode));
      if (drawControl && isAnalysisMode) map.addControl(drawControl);
      syncPanelVisibility();
      syncSearchMode();
      if (panel) panel.style.display = 'none';
      if (aladinContainer) aladinContainer.style.display = 'none';
      if (status) status.style.display = 'none';
      toggleBtn?.classList.remove('active');
      toggleBtn?.setAttribute('aria-pressed', 'false');
      return;
    }
  } else {
    invalidateTargetRequests();
    if (panel) panel.style.display = 'none';
    if (aladinContainer) aladinContainer.style.display = 'none';
    if (status) status.style.display = 'none';
    toggleBtn?.classList.remove('active');
    toggleBtn?.setAttribute('aria-pressed', 'false');
  }

  syncPanelVisibility();
  if (!newMode) map?.invalidateSize();
}

// ---------------------------------------------------------------------------
// Jump-to-telescope (called from map popup actions)
// ---------------------------------------------------------------------------

/** Jump from browse/analysis mode into telescope mode at a given location. */
export async function jumpToTelescopeMode(
  lat: number,
  lng: number,
  label: string,
): Promise<void> {
  invalidateTargetResults();
  setObservationLocation(lat, lng);

  if (!isTelescopeMode) {
    await toggleTelescopeMode();
  }

  showToast(`🔭 望远镜模式已定位到: ${label}`, 'info');
}

// ---------------------------------------------------------------------------
// Panel visibility
// ---------------------------------------------------------------------------

/**
 * Synchronize panel visibility across browse / analysis / telescope modes.
 * Ensures only panels relevant to the active mode are shown.
 */
export function syncPanelVisibility(): void {
  const info = document.querySelector('.info-panel') as HTMLElement | null;
  const stats = document.querySelector('.stats-panel') as HTMLElement | null;
  const analysis = document.getElementById('stargazing-control-panel');
  const results = document.getElementById('results-panel');

  if (isTelescopeMode) {
    if (info) info.style.display = 'none';
    if (stats) stats.style.display = 'none';
    if (analysis) analysis.style.display = 'none';
    if (results) results.style.display = 'none';
  } else if (isAnalysisMode) {
    if (info) info.style.display = 'none';
    if (analysis) analysis.style.display = 'block';
    if (results && resultsPanel?.innerHTML) results.style.display = 'block';
  } else {
    // Browse mode — info/stats shown on demand by their respective update functions
  }
}
