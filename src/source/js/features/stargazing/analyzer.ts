// =============================================================================
// Stargazing Analyzer — area analysis API calls
// =============================================================================

import { map, currentPolygon, drawnItems } from '../../state';
import { API_CONFIG } from '../../core/api';
import { displayAnalysisResults } from './results';
import { updateStatus } from './index';
import type { AnalysisRequest } from '../../types/api';

// ---------------------------------------------------------------------------
// Request builder (pure — testable without DOM)
// ---------------------------------------------------------------------------

/** Build the analysis request body from the current UI state and polygon. */
export function buildAnalysisRequest(
  polygon: any, // DrawnPolygon (Leaflet layer)
  maxLocations: number,
  transportMode: string,
  includeLightPollution: boolean,
  includeRoadConnectivity: boolean,
): AnalysisRequest {
  const coordinates: L.LatLng[] = polygon.getLatLngs()[0];
  const lats = coordinates.map((c) => c.lat);
  const lngs = coordinates.map((c) => c.lng);

  return {
    bbox: {
      south: Math.min(...lats),
      west: Math.min(...lngs),
      north: Math.max(...lats),
      east: Math.max(...lngs),
    },
    max_locations: maxLocations,
    network_type: transportMode,
    include_light_pollution: includeLightPollution,
    include_road_connectivity: includeRoadConnectivity,
    road_radius_km: 10.0,
    max_distance_to_road_km: 0.2,
  };
}

// ---------------------------------------------------------------------------
// Main API call
// ---------------------------------------------------------------------------

/** Send the analysis request to the backend and display results. */
/* c8 ignore start — API call + DOM form reading: requires full browser environment */
export async function analyzeStargazingArea(): Promise<void> {
  if (!currentPolygon) {
    updateStatus('请先绘制一个分析区域', 'error');
    return;
  }

  const analyzeBtn: HTMLButtonElement | null = document.getElementById('analyze-button') as any;
  if (analyzeBtn) {
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="loading-spinner"></span>分析中...';
  }

  updateStatus('正在分析观星区域...', 'loading');

  try {
    const maxLocations = parseInt((document.getElementById('max-locations') as HTMLInputElement)?.value || '30', 10);
    const transportMode = (document.getElementById('network-type') as HTMLSelectElement)?.value || 'drive';
    const includeLightPollution = (document.getElementById('include-light-pollution') as HTMLInputElement)?.checked ?? true;
    const includeRoadConnectivity = (document.getElementById('include-road-connectivity') as HTMLInputElement)?.checked ?? true;

    const requestData = buildAnalysisRequest(
      currentPolygon.layer,
      maxLocations,
      transportMode,
      includeLightPollution,
      includeRoadConnectivity,
    );

    console.log('Sending analysis request:', requestData);

    const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.analyze}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API request failed: ${response.status} - ${errorText}`);
    }

    const result = await response.json();
    console.log('Analysis result:', result);

    displayAnalysisResults(result);
    updateStatus(`分析完成，找到 ${result.locations?.length || 0} 个观星地点`, 'success');
  } catch (error: any) {
    console.error('Analysis failed:', error);
    updateStatus(`分析失败: ${error.message}`, 'error');
  } finally {
    if (analyzeBtn) {
      analyzeBtn.disabled = false;
      analyzeBtn.innerHTML = '分析观星区域';
    }
  }
}

// ---------------------------------------------------------------------------
// Health check (re-exported for convenience)
// ---------------------------------------------------------------------------

export { checkApiHealth } from '../../core/api';
