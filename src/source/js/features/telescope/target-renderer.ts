// =============================================================================
// Target renderer — DOM rendering and Aladin overlay for telescope targets
// =============================================================================

import { aladinInstance, targetCatalog, lastMosaicTarget } from '../../state';
import { setTargetCatalog, setLastMosaicTarget } from '../../state';
import { showAltitudeChart } from './altitude-chart';
import { fetchMosaicGrid } from '../mosaic/index';
import type { TelescopeTarget, MoonData, ShootingPlan, PlanSlot } from '../../types/telescope';

// ---------------------------------------------------------------------------
// Target list rendering (testable — returns HTML strings)
// ---------------------------------------------------------------------------

/** Render the matched-target list into a DOM element. */
export function renderTargetResults(targets: TelescopeTarget[], container: HTMLElement): void {
  container.innerHTML = targets.length === 0
    ? '<p class="target-empty">未找到匹配目标，尝试调整参数</p>'
    : targets.map((t, i) => renderTargetCard(t, i + 1)).join('');
}

function renderTargetCard(t: TelescopeTarget, rank: number): string {
  const sc = t.suitability_score?.toFixed(0) ?? '?';
  return `
    <div class="target-card" data-target-name="${t.name}" data-ra="${t.ra}" data-dec="${t.dec}">
      <span class="tc-rank">#${rank}</span>
      <span class="tc-name">${t.name}</span>
      <span class="tc-score">${sc}</span>
      <span class="tc-fov">FOV ${((t.fov_fit_score ?? 0) * 100).toFixed(0)}%</span>
    </div>`;
}

// ---------------------------------------------------------------------------
// Moon card
// ---------------------------------------------------------------------------

/** Render the moon-info card. */
export function renderMoonCard(moon: MoonData | null): void {
  const el = document.getElementById('moon-card');
  if (!el) return;
  if (!moon) { el.style.display = 'none'; return; }
  el.style.display = 'block';
  el.innerHTML = `🌙 ${moon.phase} (${(moon.illumination * 100).toFixed(0)}%)`;
}

// ---------------------------------------------------------------------------
// Shooting plan rendering
// ---------------------------------------------------------------------------

/** Render the shooting plan table into a DOM element. */
/* c8 ignore start — complex DOM rendering with plan data */
export function renderShootingPlan(
  plan: ShootingPlan | null,
  targets: TelescopeTarget[],
  container: HTMLElement,
): void {
  if (!plan || !plan.slots?.length) {
    container.innerHTML = '<p class="target-empty">无可用拍摄计划</p>';
    return;
  }

  const targetMap = new Map(targets.map((t) => [t.name, t]));
  const slots = plan.slots.map((s) => {
    const t = targetMap.get(s.target_name);
    return { ...s, target: t };
  });

  container.innerHTML = `
    <div class="plan-table">
      <div class="plan-header">
        <span>时间</span><span>目标</span><span>高度</span>
      </div>
      ${slots.map((s) => `
        <div class="plan-row">
          <span>${s.start_time}–${s.end_time}</span>
          <span>${s.target_name}</span>
          <span>${s.altitude_start?.toFixed(0) ?? '?'}°→${s.altitude_end?.toFixed(0) ?? '?'}°</span>
        </div>`).join('')}
      ${plan.total_exposure_min ? `<p class="plan-total">总曝光: ${plan.total_exposure_min} min</p>` : ''}
    </div>`;
}
/* c8 ignore stop */

// ---------------------------------------------------------------------------
// Aladin overlay (coverage-exempt — depends on runtime Aladin instance)
// ---------------------------------------------------------------------------

/**
 * Overlay telescope targets as catalog markers on the Aladin Lite view.
 */

/* c8 ignore start — Aladin catalog API */
export function overlayTargetsOnAladin(targets: TelescopeTarget[]): void {

  if (!aladinInstance) return;

  try {
    aladinInstance.removeCatalogs();
  } catch { /* ignore */ }

  const A = (window as any).A;
  if (!A?.catalog) return;

  const catalog = A.catalog({
    name: 'Targets',
    sourceSize: 8,
    shape: 'circle',
    color: '#00ff88',
    onClick: 'showTable',
  });

  targets.forEach((t) => {
    catalog.addSources([{ ra: t.ra, dec: t.dec, name: t.name }]);
  });

  aladinInstance.addCatalog(catalog);
  setTargetCatalog(catalog);
}
