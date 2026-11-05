/* c8 ignore start — integration code: requires full browser environment */
// =============================================================================
// Telescope UI — panel bindings, mode switching, preset handling
// =============================================================================

import { isTelescopeMode, isAnalysisMode, aladinInstance } from '../../state';
import { setIsTelescopeMode, setTelescopeTargetLocation } from '../../state';
import { showToast } from '../../utils/dom';
import { ensureAladinReady, updateFovOverlay, applyPreset } from './aladin-core';
import { matchTelescopeTargets, fetchShootingPlan } from './targets';
import { bindTargetInteractions } from './target-renderer';

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

/** Wire up telescope panel interactions (runs once at page load). */
export function initTelescopeMode(): void {
  // ── Preset selector ──
  const presetSelect = document.getElementById('telescope-preset') as HTMLSelectElement | null;
  if (presetSelect) {
    presetSelect.addEventListener('change', function (this: HTMLSelectElement) {
      applyPreset(this.value);
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
        updateFovOverlay();
      });
    }
  });

  // ── Match button ──
  const matchBtn = document.getElementById('match-targets-btn');
  if (matchBtn) matchBtn.addEventListener('click', matchTelescopeTargets);

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

  // ── Celestial search via unified search bar ──
  const searchInput = document.getElementById('search-input') as HTMLInputElement | null;
  if (searchInput) {
    searchInput.addEventListener('keypress', async function (this: HTMLInputElement, e: KeyboardEvent) {
      if (e.key !== 'Enter' || !isTelescopeMode || !aladinInstance) return;
      const query = this.value.trim();
      if (!query) return;
      aladinInstance.gotoObject(query, {
        success: () => setTimeout(() => updateFovOverlay(), 300),
        error: () => showToast('未找到天体: ' + query, 'error'),
      });
    });
  }
}

// ---------------------------------------------------------------------------
// Mode toggle
// ---------------------------------------------------------------------------

/** Toggle telescope mode on/off. */
export async function toggleTelescopeMode(): Promise<void> {
  const newMode = !isTelescopeMode;
  setIsTelescopeMode(newMode);

  const panel = document.getElementById('telescope-control-panel');
  const aladinContainer = document.getElementById('aladin-container');
  const status = document.getElementById('telescope-status');
  const toggleBtn = document.getElementById('telescope-toggle-btn');

  if (newMode) {
    if (panel) panel.style.display = 'block';
    if (aladinContainer) aladinContainer.style.display = 'block';
    if (status) status.style.display = 'block';
    toggleBtn?.classList.add('active');
    toggleBtn?.setAttribute('aria-pressed', 'true');
    try {
      await ensureAladinReady();
      updateFovOverlay();
    } catch (e: any) {
      showToast('Aladin Lite 加载失败: ' + e.message, 'error');
      setIsTelescopeMode(false);
      if (panel) panel.style.display = 'none';
      if (aladinContainer) aladinContainer.style.display = 'none';
      if (status) status.style.display = 'none';
      toggleBtn?.classList.remove('active');
      toggleBtn?.setAttribute('aria-pressed', 'false');
      return;
    }
  } else {
    if (panel) panel.style.display = 'none';
    if (aladinContainer) aladinContainer.style.display = 'none';
    if (status) status.style.display = 'none';
    toggleBtn?.classList.remove('active');
    toggleBtn?.setAttribute('aria-pressed', 'false');
  }

  syncPanelVisibility();
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
  setTelescopeTargetLocation({ lat, lng });

  if (!isTelescopeMode) {
    await toggleTelescopeMode();
  }

  if (aladinInstance) {
    aladinInstance.gotoRaDec(lng, lat);
    setTimeout(() => updateFovOverlay(), 300);
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
  } else {
    // Browse mode — info/stats shown on demand by their respective update functions
  }
}

/* c8 ignore stop */
