// =============================================================================
// Vite entry point — explicit import chain (no side-effect-only imports)
// =============================================================================

// State & foundation modules
import { currentLanguage, setCurrentLanguage } from './state';

// Core
import { detectUserLanguage, getText, toggleLanguage } from './core/i18n';
import { API_CONFIG } from './core/api';
import { showToast } from './utils/dom';

// Map
import { getBortleColor } from './utils/color';
import { estimateBortleClass } from './utils/geo';
import { initializeMap, getMap } from './map/map-instance';

// Panels
import { calculateStats, updateStatsPanel } from './panels/stats-panel';
import {
  getSuitabilityLevel, createPopupContent, createDetailedPopupContent,
  analyzeCoordinate, getNearestLightPollutionData, updateInfoPanel, onMapClick,
} from './panels/info-panel';

// Layers (re-exports utils + adds rendering)
import {
  renderLightPollutionLayer, clearLayers, clearImageLayers,
  loadLightPollutionDataPoints, loadLightPollutionImageLayers,
  updateLayersAndStats, loadCurrentViewData,
} from './map/layers';

// Stargazing features
import { initializeDrawControls, clearAll, clearAnalysisResults } from './features/stargazing/draw';
import { buildAnalysisRequest, analyzeStargazingArea, checkApiHealth } from './features/stargazing/analyzer';
import {
  calculateLocationStats, createStargazingMarker,
  displayAnalysisResults, focusOnLocation,
} from './features/stargazing/results';
import { updateStatus, toggleMode, initializeStargazingSelector } from './features/stargazing/index';

// Telescope features
import {
  TELESCOPE_PRESETS, calculateFov, calculateFovFromInputs,
  setupFovCanvas, updateFovOverlay, applyPreset,
  ensureAladinReady, onAladinReady,
} from './features/telescope/aladin-core';
import { buildTargetRequest, matchTelescopeTargets, fetchShootingPlan } from './features/telescope/targets';
import {
  computeChartLayout, scaleAltitudeToPixel, formatTimeLabel, showAltitudeChart,
} from './features/telescope/altitude-chart';
import {
  renderTargetResults, renderMoonCard, renderShootingPlan, overlayTargetsOnAladin,
} from './features/telescope/target-renderer';
import {
  initTelescopeMode, toggleTelescopeMode, jumpToTelescopeMode, syncPanelVisibility,
} from './features/telescope/telescope-ui';

// Mosaic
import { initMosaic, fetchMosaicGrid, renderMosaicPanel } from './features/mosaic/index';

// =============================================================================
// Bootstrap — explicit call chain that Rollup cannot tree-shake
// =============================================================================

function initLanguage(): void {
  const detected = detectUserLanguage();
  setCurrentLanguage(detected);

  document.documentElement.lang = currentLanguage;

  const langBtn = document.getElementById('language-btn');
  if (langBtn) {
    langBtn.addEventListener('click', () => {
      toggleLanguage();
      updateLanguageElements();
    });
  }

  updateLanguageElements();
}

/** Update all UI text after a language switch. */
function updateLanguageElements(): void {
  document.documentElement.lang = currentLanguage;
  document.title = getText('title');

  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (key) {
      if (el instanceof HTMLInputElement) {
        el.placeholder = getText(key);
      } else {
        el.textContent = getText(key);
      }
    }
  });

  const langBtn = document.getElementById('language-btn');
  if (langBtn) langBtn.textContent = currentLanguage === 'zh' ? '中/EN' : 'EN/中';

  updateLegend();
}

function updateLegend(): void {
  const legendPanel = document.querySelector('.legend-panel');
  if (!legendPanel) return;

  let html = `<h3>${getText('legend')}</h3>`;
  for (let i = 1; i <= 9; i++) {
    const description = getText(`bortleDescriptions.${i}`);
    html += `<div class="legend-item"><span class="legend-color" style="background:${getBortleColor(i)}"></span>${description}</div>`;
  }
  legendPanel.innerHTML = html;
}

function initSearch(): void {
  const input = document.getElementById('search-input') as HTMLInputElement | null;
  if (!input) return;

  input.addEventListener('keypress', async function (this: HTMLInputElement, e: KeyboardEvent) {
    if (e.key !== 'Enter') return;
    const query = this.value.trim();
    if (!query) return;

    try {
      const resp = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`);
      const results = await resp.json();
      if (results?.[0]) {
        const lat = parseFloat(results[0].lat);
        const lng = parseFloat(results[0].lon);
        getMap().setView([lat, lng], 13);
        showToast(`已定位到: ${results[0].display_name}`, 'success');
      }
    } catch (err) {
      console.error('Search failed:', err);
      showToast('搜索失败', 'error');
    }
  });
}

// Global event delegation (replaces inline onclick handlers)
document.addEventListener('click', (e) => {
  const el = (e.target as HTMLElement).closest('[data-action]') as HTMLElement | null;
  if (!el) return;

  const action = el.dataset.action;
  const lat = el.dataset.lat ? parseFloat(el.dataset.lat) : 0;
  const lng = el.dataset.lng ? parseFloat(el.dataset.lng) : 0;
  const label = el.dataset.label || '';

  switch (action) {
    case 'jump-telescope':
      e.stopPropagation();
      jumpToTelescopeMode(lat, lng, label);
      break;
    case 'focus-location':
      focusOnLocation(lat, lng);
      break;
    case 'clear-results':
      clearAnalysisResults();
      break;
  }
});

// =============================================================================
// App bootstrap
// =============================================================================

function boot(): void {
  initLanguage();
  initializeMap();
  initSearch();
  initializeStargazingSelector();
  initTelescopeMode();
  initMosaic();
  syncPanelVisibility();
  console.log('[Stargazing] App initialized');
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}

// Re-export everything for potential external consumers
export {
  // state
  currentLanguage, setCurrentLanguage,
  // core
  detectUserLanguage, getText, toggleLanguage, API_CONFIG, showToast,
  // map
  initializeMap, getMap, getBortleColor, estimateBortleClass,
  // panels
  calculateStats, updateStatsPanel, getSuitabilityLevel,
  createPopupContent, createDetailedPopupContent,
  analyzeCoordinate, getNearestLightPollutionData, updateInfoPanel, onMapClick,
  // layers
  renderLightPollutionLayer, clearLayers, clearImageLayers,
  loadLightPollutionDataPoints, loadLightPollutionImageLayers,
  updateLayersAndStats, loadCurrentViewData,
  // stargazing
  initializeDrawControls, clearAll, clearAnalysisResults,
  buildAnalysisRequest, analyzeStargazingArea, checkApiHealth,
  calculateLocationStats, createStargazingMarker, displayAnalysisResults, focusOnLocation,
  updateStatus, toggleMode, initializeStargazingSelector,
  // telescope
  TELESCOPE_PRESETS, calculateFov, calculateFovFromInputs,
  setupFovCanvas, updateFovOverlay, applyPreset, ensureAladinReady, onAladinReady,
  buildTargetRequest, matchTelescopeTargets, fetchShootingPlan,
  computeChartLayout, scaleAltitudeToPixel, formatTimeLabel, showAltitudeChart,
  renderTargetResults, renderMoonCard, renderShootingPlan, overlayTargetsOnAladin,
  initTelescopeMode, toggleTelescopeMode, jumpToTelescopeMode, syncPanelVisibility,
  // mosaic
  initMosaic, fetchMosaicGrid, renderMosaicPanel,
};
