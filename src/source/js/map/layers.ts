// =============================================================================
// Map Layers — light-pollution rendering, data loading, layer management
// =============================================================================

import L from 'leaflet';
import 'leaflet.markercluster';
import {
  map, currentOverlay, currentImageLayers, isLoading,
  setCurrentOverlay, setCurrentImageLayers,
} from '../state';
import { API_CONFIG } from '../core/api';
import { getText } from '../core/i18n';
import { showLoadingIndicator, hideLoadingIndicator } from '../utils/dom';
import { calculateStats, updateStatsPanel } from '../panels/stats-panel';
import type { LightPollutionPoint } from '../types/stargazing';

// Re-export pure utilities (extracted for testability)
export { getBortleColor, getIntensityRadius } from '../utils/color';
export { estimateBortleClass } from '../utils/geo';

// Also import for internal use within this module
import { getBortleColor } from '../utils/color';

// ---------------------------------------------------------------------------
// Layer rendering
// ---------------------------------------------------------------------------

/** Render light-pollution data points as a marker-cluster layer. */
/* c8 ignore start — Leaflet layer API: requires full browser map instance */
export function renderLightPollutionLayer(data: LightPollutionPoint[]): void {
  if (currentOverlay) {
    map.removeLayer(currentOverlay);
    setCurrentOverlay(null);
  }

  if (!data || data.length === 0) return;

  const markers = (L as any).markerClusterGroup({
    maxClusterRadius: 50,
    iconCreateFunction(cluster: any) {
      const childCount: number = cluster.getChildCount();
      const avgBortle: number =
        cluster.getAllChildMarkers().reduce((sum: number, m: any) => sum + (m.options.bortleClass || 0), 0) /
        childCount;
      return L.divIcon({
        html: `<div style="background-color:${getBortleColor(Math.round(avgBortle))};color:white;border-radius:50%;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-weight:bold">${childCount}</div>`,
        className: 'custom-cluster-icon',
        iconSize: [40, 40],
      });
    },
  });

  data.forEach((point) => {
    const marker = (L as any).circleMarker([point.lat, point.lng], {
      radius: 5,
      fillColor: getBortleColor(point.bortleClass),
      color: '#64b5f6',
      weight: 1.5,
      opacity: 0.9,
      fillOpacity: 0.6,
      bortleClass: point.bortleClass,
    });

    const popupContent = `
      <div class="location-popup">
        <h4>${getText('coordinates')}</h4>
        <p>${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}</p>
        <h4>${getText('bortleClass')}</h4>
        <p>${getText(`bortleDescriptions.${point.bortleClass}`)}</p>
      </div>`;

    marker.bindPopup(popupContent);
    markers.addLayer(marker);
  });

  setCurrentOverlay(markers);
  map.addLayer(currentOverlay);
}

// ---------------------------------------------------------------------------
// Layer cleanup
// ---------------------------------------------------------------------------

/** Remove the current overlay layer from the map. */
export function clearLayers(): void {
  if (currentOverlay) {
    map.removeLayer(currentOverlay);
    setCurrentOverlay(null);
  }
  clearImageLayers();
}

/** Remove all image overlay layers from the map. */
export function clearImageLayers(): void {
  currentImageLayers.forEach((layer: any) => {
    if (map.hasLayer(layer)) map.removeLayer(layer);
  });
  setCurrentImageLayers([]);
}

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

/** Fetch light-pollution data points for the current map view and update stats. */
export async function loadLightPollutionDataPoints(): Promise<void> {
  try {
    console.log('Loading light-pollution statistics...');

    if (!map) {
      console.warn('Map not initialized — cannot load data');
      return;
    }

    const bounds = map.getBounds();
    const apiUrl =
      `${API_CONFIG.baseUrl}/api/light_pollution?` +
      `north=${bounds.getNorth()}&south=${bounds.getSouth()}&` +
      `east=${bounds.getEast()}&west=${bounds.getWest()}&` +
      `zoom=${map.getZoom()}`;

    const response = await fetch(apiUrl);
    if (!response.ok) {
      console.warn('Failed to fetch light-pollution data:', response.statusText);
      return;
    }

    const json = await response.json();

    if (!json.success || !json.data || !Array.isArray(json.data)) {
      console.log('No light-pollution data returned');
      return;
    }

    const points: LightPollutionPoint[] = json.data.map((d: any) => ({
      lat: d.lat,
      lng: d.lng,
      bortleClass: d.bortle,
      intensity: d.intensity,
      sqm: d.sqm,
    }));

    const stats = calculateStats(points);
    updateStatsPanel(stats);

    console.log(`✅ Stats panel updated — ${json.data.length} sample points`);
  } catch (error) {
    console.error('Failed to load light-pollution data:', error);
  }
}

/** Backward-compat alias. */
export const loadLightPollutionImageLayers = loadLightPollutionDataPoints;

// ---------------------------------------------------------------------------
// Orchestration
// ---------------------------------------------------------------------------

/** Refresh both layers and stats with the given data. */
export function updateLayersAndStats(data: LightPollutionPoint[]): void {
  console.log('Updating layers and stats — data length:', data?.length ?? 0);

  clearLayers();

  if (!data || data.length === 0) {
    updateStatsPanel();
    return;
  }

  const stats = calculateStats(data);
  updateStatsPanel(stats);

  console.log('Rendering light-pollution layer...');
  renderLightPollutionLayer(data);

  console.log('Layers and stats update complete');
}

/** Load data for the current map view (debounced entry point). */
export async function loadCurrentViewData(): Promise<void> {
  if (isLoading) return;

  showLoadingIndicator();

  try {
    // Connectivity check
    try {
      const testResp = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.health}`);
      if (testResp.ok) {
        console.log('API health OK:', await testResp.json());
      }
    } catch (apiError) {
      console.error('API connectivity check failed:', apiError);
    }

    // Clear existing point overlay (keep tile layers)
    if (currentOverlay) {
      map.removeLayer(currentOverlay);
      setCurrentOverlay(null);
    }

    await loadLightPollutionDataPoints();
  } catch (error) {
    console.error('Failed to load view data:', error);
  } finally {
    hideLoadingIndicator();
  }
}
/* c8 ignore stop */
