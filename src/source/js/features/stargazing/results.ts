// =============================================================================
// Stargazing Results — analysis result rendering and markers
// =============================================================================

import L from 'leaflet';
import {
  map, drawnItems, analysisResults, resultsPanel,
  setAnalysisResults, setResultsPanel,
} from '../../state';
import { getText } from '../../core/i18n';
import { clearAnalysisResults } from './draw';
import type { StargazingLocation, LocationStats } from '../../types/stargazing';
import type { MarkerStyle } from '../../types/telescope';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MARKER_STYLES: Record<string, MarkerStyle> = {
  stargazing: { className: 'stargazing-marker', iconSize: [20, 20], iconAnchor: [10, 10] },
  excellent: { className: 'stargazing-marker excellent-marker', iconSize: [16, 16], iconAnchor: [8, 8] },
  good: { className: 'stargazing-marker good-marker', iconSize: [14, 14], iconAnchor: [7, 7] },
  fair: { className: 'stargazing-marker fair-marker', iconSize: [12, 12], iconAnchor: [6, 6] },
  poor: { className: 'stargazing-marker poor-marker', iconSize: [10, 10], iconAnchor: [5, 5] },
};

// ---------------------------------------------------------------------------
// Pure calculations
// ---------------------------------------------------------------------------

/** Compute statistical summary of a list of stargazing locations. */
export function calculateLocationStats(locations: StargazingLocation[]): LocationStats {
  const total = locations.length;
  if (total === 0) {
    return { totalLocations: 0, avgScore: 0, excellentCount: 0, goodCount: 0, fairCount: 0, poorCount: 0, excellentPercentage: '0', goodPercentage: '0', fairPercentage: '0', poorPercentage: '0' };
  }

  const excellent = locations.filter((l) => l.score >= 80).length;
  const good = locations.filter((l) => l.score >= 60 && l.score < 80).length;
  const fair = locations.filter((l) => l.score >= 40 && l.score < 60).length;
  const poor = locations.filter((l) => l.score < 40).length;
  const avgScore = locations.reduce((sum, l) => sum + l.score, 0) / total;

  return {
    totalLocations: total,
    avgScore: Math.round(avgScore),
    excellentCount: excellent,
    goodCount: good,
    fairCount: fair,
    poorCount: poor,
    excellentPercentage: ((excellent / total) * 100).toFixed(1),
    goodPercentage: ((good / total) * 100).toFixed(1),
    fairPercentage: ((fair / total) * 100).toFixed(1),
    poorPercentage: ((poor / total) * 100).toFixed(1),
  };
}

/** Determine the quality tier for a score. */
export function scoreClass(score: number): string {
  if (score >= 80) return 'excellent';
  if (score >= 60) return 'good';
  if (score >= 40) return 'fair';
  return 'poor';
}

// ---------------------------------------------------------------------------
// Marker creation
// ---------------------------------------------------------------------------

/** Create a Leaflet marker styled by suitability tier. */
/* c8 ignore start — Leaflet marker creation + DOM display: requires map */

export function createStargazingMarker(location: StargazingLocation): L.Marker {
  const tier = scoreClass(location.score);
  const style = MARKER_STYLES[tier] ?? MARKER_STYLES.stargazing!;

  const icon = L.divIcon({
    className: style.className,
    iconSize: style.iconSize,
    iconAnchor: style.iconAnchor,
  });

  const marker = L.marker([location.lat, location.lng], { icon });
  marker.bindPopup(`
    <div class="popup-content">
      <h4>${location.name || 'Unnamed'}</h4>
      <p>⭐ 评分: ${location.score}</p>
      <p>🌃 Bortle: ${location.bortleClass}</p>
      <p>📏 SQM: ${location.sqm} mag/arcsec²</p>
      ${location.elevation_m ? `<p>⛰️ 海拔: ${location.elevation_m}m</p>` : ''}
      <button class="btn-jump-telescope" data-action="jump-telescope" data-lat="${location.lat}" data-lng="${location.lng}" data-label="${location.name || ''}">🔭 ${getText('shootHere') || '在此拍摄'}</button>
    </div>`);

  return marker;
}

// ---------------------------------------------------------------------------
// DOM rendering
// ---------------------------------------------------------------------------

/** Display the analysis results panel and markers on the map. */
export function displayAnalysisResults(result: any): void {
  const locations: StargazingLocation[] = result.locations || [];
  setAnalysisResults(locations);

  // Clear old markers
  if (drawnItems) drawnItems.clearLayers();

  // Render markers
  const featureGroup = L.featureGroup();
  locations.forEach((loc) => {
    featureGroup.addLayer(createStargazingMarker(loc));
  });
  if (drawnItems) {
    drawnItems.addLayer(featureGroup);
  }

  if (locations.length > 0) {
    const lats = locations.map((l) => l.lat);
    const lngs = locations.map((l) => l.lng);
    map.fitBounds([
      [Math.min(...lats), Math.min(...lngs)],
      [Math.max(...lats), Math.max(...lngs)],
    ], { padding: [50, 50] });
  }

  showResultsPanel(locations);
}

/** Render the results side panel. */
function showResultsPanel(locations: StargazingLocation[]): void {
  const panel = document.querySelector('.results-panel') as HTMLElement | null;
  if (!panel) return;

  setResultsPanel(panel);

  if (locations.length === 0) {
    panel.innerHTML = '<p>未找到符合条件的观星地点</p>';
    panel.style.display = 'block';
    return;
  }

  const stats = calculateLocationStats(locations);

  panel.innerHTML = `
    <h3>📊 分析结果</h3>
    <div class="results-summary">
      <p>📍 地点总数: <strong>${stats.totalLocations}</strong></p>
      <p>⭐ 平均评分: <strong>${stats.avgScore}</strong></p>
    </div>
    <div class="quality-distribution">
      ${renderDistributionBar('极佳', stats.excellentCount, stats.excellentPercentage, 'excellent')}
      ${renderDistributionBar('良好', stats.goodCount, stats.goodPercentage, 'good')}
      ${renderDistributionBar('一般', stats.fairCount, stats.fairPercentage, 'fair')}
      ${renderDistributionBar('较差', stats.poorCount, stats.poorPercentage, 'poor')}
    </div>
    <div class="results-list">
      ${locations.slice(0, 20).map((loc) => renderLocationCard(loc)).join('')}
      ${locations.length > 20 ? `<p>... 还有 ${locations.length - 20} 个结果</p>` : ''}
    </div>
    <button class="btn-clear" data-action="clear-results">清除结果</button>`;

  panel.style.display = 'block';
}

function renderDistributionBar(label: string, count: number, pct: string, tier: string): string {
  return `
    <div class="dist-bar">
      <span class="dist-label">${label}</span>
      <div class="dist-fill-wrap"><div class="dist-fill dist-${tier}" style="width:${pct}%"></div></div>
      <span class="dist-count">${count} (${pct}%)</span>
    </div>`;
}

function renderLocationCard(loc: StargazingLocation): string {
  const tier = scoreClass(loc.score);
  return `
    <div class="location-card card-${tier}">
      <span class="loc-score">${loc.score}</span>
      <span class="loc-name">${loc.name || `${loc.lat.toFixed(3)}, ${loc.lng.toFixed(3)}`}</span>
      <span class="loc-bortle">Bortle ${loc.bortleClass}</span>
      <button class="btn-focus" data-action="focus-location" data-lat="${loc.lat}" data-lng="${loc.lng}">📍</button>
    </div>`;
}

// ---------------------------------------------------------------------------
// Map navigation
// ---------------------------------------------------------------------------

/** Pan the map to focus on a specific location. */
export function focusOnLocation(lat: number, lng: number): void {
  map.setView([lat, lng], 14);
}

/* c8 ignore stop */
