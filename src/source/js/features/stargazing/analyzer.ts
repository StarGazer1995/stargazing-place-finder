// =============================================================================
// Stargazing Analyzer — area analysis API calls
// =============================================================================

import { map, currentPolygon, drawnItems } from '../../state';
import { API_CONFIG } from '../../core/api';
import { displayAnalysisResults } from './results';
import { updateStatus } from './index';
import type { AnalysisRequest } from '../../types/api';
let activeAnalysis: AbortController | null = null;

/** Cancels waiting and ignores any late response; server work may still drain. */
export function cancelAreaAnalysis(announce = false): void {
  activeAnalysis?.abort();
  activeAnalysis = null;
  const button = document.getElementById('analyze-button') as HTMLButtonElement | null;
  if (button) { button.disabled = !currentPolygon; button.textContent = '分析观星地点'; }
  const cancel = document.getElementById('cancel-analysis-button');
  if (cancel) cancel.hidden = true;
  if (announce) updateStatus('已停止等待，所选区域已保留。后台查询可能仍在完成。', 'info');
}

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
  if (activeAnalysis) return;
  if (!currentPolygon) {
    updateStatus('请先绘制一个分析区域', 'error');
    return;
  }
  const maxInput = document.getElementById('max-locations') as HTMLInputElement;
  if (!maxInput.checkValidity()) {
    const details = maxInput.closest('details');
    if (details) details.open = true;
    maxInput.reportValidity();
    return;
  }
  const controller = new AbortController();
  activeAnalysis = controller;
  let timedOut = false;
  const timeout = setTimeout(() => { timedOut = true; controller.abort(); }, 90_000);
  const cancel = document.getElementById('cancel-analysis-button');
  if (cancel) cancel.hidden = false;

  const analyzeBtn: HTMLButtonElement | null = document.getElementById('analyze-button') as any;
  if (analyzeBtn) {
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="loading-spinner"></span>分析中...';
  }

  updateStatus('正在查询地点与道路，可取消等待；外部地图服务可能较慢。', 'loading');

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
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API request failed: ${response.status} - ${errorText}`);
    }

    const result = await response.json();
    if (activeAnalysis !== controller) return;
    console.log('Analysis result:', result);

    displayAnalysisResults(result);
    updateStatus(`分析完成，找到 ${result.locations?.length || 0} 个观星地点`, 'success');
  } catch (error: any) {
    if (activeAnalysis !== controller) return;
    console.error('Analysis failed:', error);
    updateStatus(timedOut ? '查询超时，区域已保留。请缩小范围或稍后重试。' : `分析失败: ${error.message}`, 'error');
  } finally {
    clearTimeout(timeout);
    if (activeAnalysis === controller) cancelAreaAnalysis();
  }
}

// ---------------------------------------------------------------------------
// Health check (re-exported for convenience)
// ---------------------------------------------------------------------------

export { checkApiHealth } from '../../core/api';
