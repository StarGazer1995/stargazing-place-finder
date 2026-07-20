// =============================================================================
// Stats Panel — dark-sky statistics and Bortle distribution
// =============================================================================

import { isAnalysisMode, isTelescopeMode } from '../state';
import { getText } from '../core/i18n';
import { getBortleColor } from '../map/layers';
import type { LightPollutionPoint } from '../types/stargazing';
import type { StatsResult } from '../types/stargazing';

// ---------------------------------------------------------------------------
// Pure calculation
// ---------------------------------------------------------------------------

/** Compute dark-sky statistics from a set of light-pollution data points. */
export function calculateStats(data: LightPollutionPoint[]): StatsResult {
  if (!data || data.length === 0) {
    return { darkSkyArea: 0, darkSkyPercentage: '0.0', bortleDistribution: {} };
  }

  const totalPoints = data.length;
  const darkSkyPoints = data.filter((p) => p.bortleClass <= 3).length;
  const darkSkyPercentage = ((darkSkyPoints / totalPoints) * 100).toFixed(1);

  const bortleDistribution: Record<number, { count: number; percentage: string }> = {};
  for (let i = 1; i <= 9; i++) {
    const count = data.filter((p) => p.bortleClass === i).length;
    bortleDistribution[i] = {
      count,
      percentage: ((count / totalPoints) * 100).toFixed(1),
    };
  }

  return { darkSkyArea: darkSkyPoints, darkSkyPercentage, bortleDistribution };
}

// ---------------------------------------------------------------------------
// DOM rendering
// ---------------------------------------------------------------------------

/* c8 ignore start — DOM panel update with i18n */
/** Update the stats panel with computed data (or clear it when null). */
export function updateStatsPanel(stats: StatsResult | null = null): void {
  const darkSkyStatsDiv = document.querySelector('.dark-sky-stats');
  const bortleDistributionDiv = document.querySelector('.bortle-distribution');

  if (!darkSkyStatsDiv || !bortleDistributionDiv) return;

  if (!stats) {
    darkSkyStatsDiv.innerHTML = `
      <h4>${getText('darkSkyStats')}</h4>
      <p>${getText('totalDarkSkyArea')}: --</p>
      <p>${getText('darkSkyPercentage')}: --%</p>`;
    bortleDistributionDiv.innerHTML = `
      <h4>${getText('bortleDistribution')}</h4>
      <p>暂无数据</p>`;
    return;
  }

  darkSkyStatsDiv.innerHTML = `
    <h4>${getText('darkSkyStats')}</h4>
    <p>${getText('totalDarkSkyArea')}: ${stats.darkSkyArea} 个区域</p>
    <p>${getText('darkSkyPercentage')}: ${stats.darkSkyPercentage}%</p>`;

  let distributionHTML = `<h4>${getText('bortleDistribution')}</h4>`;
  for (let i = 1; i <= 9; i++) {
    const dist = stats.bortleDistribution[i] || { count: 0, percentage: '0.0' };
    const color = getBortleColor(i);
    distributionHTML += `
      <div class="bortle-bar">
        <span class="label">Class ${i}</span>
        <div class="bar"><div class="fill" style="width:${dist.percentage}%;background-color:${color}"></div></div>
        <span class="percentage">${dist.percentage}%</span>
      </div>`;
  }
  bortleDistributionDiv.innerHTML = distributionHTML;

  // Show panel in browse mode when data is available
  if (!isAnalysisMode && !isTelescopeMode) {
    const statsPanel: HTMLElement | null = document.querySelector('.stats-panel');
    if (statsPanel) statsPanel.style.display = 'block';
  }
}
/* c8 ignore stop */
