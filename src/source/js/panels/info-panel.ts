// =============================================================================
// Info Panel — map-click popups, coordinate analysis, info panel display
// =============================================================================

import L from 'leaflet';
import { map, dataCache, isAnalysisMode, isTelescopeMode } from '../state';
import { API_CONFIG } from '../core/api';
import { getText } from '../core/i18n';
import { estimateBortleClass, getIntensityRadius } from '../map/layers';
import type { SuitabilityLevel, LightPollutionPoint } from '../types/stargazing';

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

/** Map a Bortle class to a suitability label. */
export function getSuitabilityLevel(bortleClass: number): SuitabilityLevel | 'verypoor' {
  if (bortleClass <= 2) return 'excellent';
  if (bortleClass <= 4) return 'good';
  if (bortleClass <= 6) return 'fair';
  if (bortleClass <= 7) return 'poor';
  return 'verypoor';
}

/** Look up observation tips for a given Bortle class. */
function getTips(bortleClass: number): string[] {
  const raw = getText(`tips.${bortleClass}`);
  return Array.isArray(raw) ? raw : [];
}

// ---------------------------------------------------------------------------
// Popup HTML generation (pure string builders — testable without DOM)
// ---------------------------------------------------------------------------

/** Build popup HTML for a Bortle class without API data (fallback path). */
export function createPopupContent(lat: number, lng: number, bortleClass: number): string {
  const suitability = getSuitabilityLevel(bortleClass);
  const tips = getTips(bortleClass);

  const tipsHTML = tips.length > 0
    ? `<div class="observation-tips"><h5>${getText('observationTips')}</h5><ul>${tips.map((t) => `<li>${t}</li>`).join('')}</ul></div>`
    : '';

  return `
    <div class="popup-content">
      <h4>${getText('lightPollutionInfo')}</h4>
      <p><strong>${getText('coordinates')}:</strong> ${lat.toFixed(4)}, ${lng.toFixed(4)}</p>
      <p><strong>${getText('bortleClass')}:</strong> ${getText(`bortleDescriptions.${bortleClass}`)}</p>
      <p><strong>${getText('observationSuitability')}:</strong> ${getText(`suitabilityLevels.${suitability}`)}</p>
      ${tipsHTML}
      <div class="popup-actions">
        <button class="btn-jump-telescope" data-action="jump-telescope" data-lat="${lat}" data-lng="${lng}" data-label="${lat.toFixed(4)}, ${lng.toFixed(4)}">🔭 ${getText('shootHere') || '在此拍摄'}</button>
      </div>
    </div>`;
}

// NOTE: The inline onclick has been replaced with data-action attributes.
// The event delegation handler in main.ts dispatches these clicks.
// This keeps the HTML generation testable (pure string) and decouples
// it from global function names.

/**
 * Build detailed popup HTML using data from the /api/coordinate_analysis endpoint.
 */
export function createDetailedPopupContent(lat: number, lng: number, data: any): string {
  const lp = data.light_pollution;
  const bortleClass: number = lp.bortle_class;
  const sqmValue: number = lp.sqm_value;
  const intensity: number = lp.intensity;
  const description: string = lp.description;
  const suitability = getSuitabilityLevel(bortleClass);
  const tips = getTips(bortleClass);

  return `
    <div class="popup-content">
      <h4>🌟 ${getText('lightPollutionInfo')}</h4>
      <div class="popup-section">
        <p><strong>📍 ${getText('coordinates')}:</strong> ${lat.toFixed(4)}, ${lng.toFixed(4)}</p>
        <p><strong>🌃 ${getText('bortleClass')}:</strong> ${bortleClass} - ${description}</p>
        <p><strong>✨ SQM值:</strong> ${sqmValue} mag/arcsec²</p>
        <p><strong>💡 光污染强度:</strong> ${(intensity * 100).toFixed(1)}%</p>
        <p><strong>🔭 ${getText('observationSuitability')}:</strong>
          <span class="suitability-${suitability}">${getText(`suitabilityLevels.${suitability}`)}</span></p>
      </div>
      ${tips.length > 0 ? `<div class="popup-section"><h5>💡 ${getText('observationTips')}:</h5><ul>${tips.map((t) => `<li>${t}</li>`).join('')}</ul></div>` : ''}
      <div class="popup-actions">
        <button class="btn-jump-telescope" data-action="jump-telescope" data-lat="${lat}" data-lng="${lng}" data-label="${lat.toFixed(4)}, ${lng.toFixed(4)}">🔭 ${getText('shootHere') || '在此拍摄'}</button>
      </div>
    </div>`;
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** Call the /api/coordinate_analysis endpoint for a single point. */
export async function analyzeCoordinate(lat: number, lng: number): Promise<any> {
  const response = await fetch(
    `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.coordinateAnalysis}?lat=${lat}&lng=${lng}`,
  );

  if (!response.ok) throw new Error(`API request failed: ${response.status}`);

  const result = await response.json();
  console.log('Coordinate analysis result:', result);
  return result;
}

// ---------------------------------------------------------------------------
// Nearest-data lookup
// ---------------------------------------------------------------------------

/**
 * Find the nearest light-pollution data point from the in-memory cache.
 * Falls back to a geographic estimate when no data is nearby.
 */
export function getNearestLightPollutionData(
  lat: number,
  lng: number,
): LightPollutionPoint {
  let nearest: LightPollutionPoint | null = null;
  let minDistance = Infinity;

  dataCache.forEach((data) => {
    data.forEach((point) => {
      const distance = Math.sqrt((lat - point.lat) ** 2 + (lng - point.lng) ** 2);
      if (distance < minDistance) {
        minDistance = distance;
        nearest = point;
      }
    });
  });

  if (!nearest || minDistance > 0.1) {
    const estimated = estimateBortleClass(lat, lng);
    return { lat, lng, bortleClass: estimated, intensity: getIntensityRadius(estimated) };
  }

  return nearest;
}

// ---------------------------------------------------------------------------
// Info panel DOM update
// ---------------------------------------------------------------------------

/** Update the side info panel with a clicked location's details. */
export function updateInfoPanel(lat: number, lng: number, bortleClass: number): void {
  const infoPanel: HTMLElement | null = document.querySelector('.info-panel');
  if (!infoPanel) return;

  const suitability = getSuitabilityLevel(bortleClass);

  infoPanel.innerHTML = `
    <h3>${getText('lightPollutionInfo')}</h3>
    <p><strong>${getText('coordinates')}:</strong> ${lat.toFixed(4)}, ${lng.toFixed(4)}</p>
    <p><strong>${getText('bortleClass')}:</strong> ${getText(`bortleDescriptions.${bortleClass}`)}</p>
    <p><strong>${getText('observationSuitability')}:</strong> ${getText(`suitabilityLevels.${suitability}`)}</p>`;

  // Show panel only in browse mode
  if (!isAnalysisMode && !isTelescopeMode) {
    infoPanel.style.display = 'block';
  }
}

// ---------------------------------------------------------------------------
// Map click handler
// ---------------------------------------------------------------------------

/**
 * Handle a map click: fetch coordinate analysis and display a popup.
 * Falls back to cached / estimated data when the API is unreachable.
 */
export async function onMapClick(e: L.LeafletMouseEvent): Promise<void> {
  const { lat, lng } = e.latlng;

  const loadingPopup = L.popup()
    .setLatLng(e.latlng)
    .setContent('<div style="text-align:center">🔍 正在分析坐标点...</div>')
    .openOn(map);

  try {
    const result = await analyzeCoordinate(lat, lng);

    if (result?.success) {
      const bortleClass: number = result.data.light_pollution.bortle_class;
      loadingPopup.setContent(createDetailedPopupContent(lat, lng, result.data));
      updateInfoPanel(lat, lng, bortleClass);
    } else {
      console.warn('API call returned error:', result?.error);
      const nearest = getNearestLightPollutionData(lat, lng);
      loadingPopup.setContent(createPopupContent(lat, lng, nearest.bortleClass));
      updateInfoPanel(lat, lng, nearest.bortleClass);
    }
  } catch (error) {
    console.error('Coordinate analysis failed:', error);
    const nearest = getNearestLightPollutionData(lat, lng);
    loadingPopup.setContent(createPopupContent(lat, lng, nearest.bortleClass));
    updateInfoPanel(lat, lng, nearest.bortleClass);
  }
}
