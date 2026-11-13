// =============================================================================
// Target renderer — DOM rendering and Aladin overlay for telescope targets
// =============================================================================

import { aladinInstance, lastTargets, lastMatchBody, currentLanguage } from '../../state';
import { setTargetCatalog } from '../../state';
import { showAltitudeChart } from './altitude-chart';
import { fetchMosaicGrid } from '../mosaic/index';
import { getAladin } from './aladin-core';
import type { TelescopeTarget, MoonData, ShootingPlan } from '../../types/telescope';

// ---------------------------------------------------------------------------
// Target list rendering (testable — returns HTML strings)
// ---------------------------------------------------------------------------

/** Render the matched-target list into a DOM element. */
export function renderTargetResults(targets: TelescopeTarget[], container: HTMLElement): void {
  container.innerHTML = targets.length === 0
    ? '<p class="target-empty">未找到匹配目标，尝试调整参数</p>'
    : targets.map((t, i) => renderTargetCard(t, i + 1)).join('');
}

function escapeHtml(value: string): string {
  const escapes: Record<string, string> = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'};
  return value.replace(/[&<>"']/g, (char) => escapes[char]!);
}

function windowDescription(target: TelescopeTarget): string {
  const visibility = target.visibility;
  if (visibility?.total_minutes == null || visibility.longest_minutes == null) return '可拍时段未核实';
  const time = (stamp: number) => new Date(stamp * 1000).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', hour12: false, timeZone: lastMatchBody?.time_zone});
  const next = visibility.windows[0];
  return `剩余 ${visibility.total_minutes.toFixed(0)} 分钟 · 最长连续 ${visibility.longest_minutes.toFixed(0)} 分钟`
    + (next ? ` · ${visibility.available_now ? '当前' : '下个'} ${time(next.start)}–${time(next.end)}` : ' · 无剩余时段');
}

function renderTargetCard(t: TelescopeTarget, rank: number): string {
  const sc = t.suitability_score?.toFixed(0) ?? '?';
  const sb = t.surface_brightness != null ? t.surface_brightness.toFixed(1) : null;
  const rot = t.optimal_rotation_deg != null ? `${t.optimal_rotation_deg.toFixed(0)}°` : null;
  const types: Record<string, string> = { OpC: '疏散星团', Gx: '星系', G: '星系', Gb: '球状星团', GlC: '球状星团', HII: '电离氢区', PN: '行星状星云', SNR: '超新星遗迹', RfN: '反射星云', EmN: '发射星云' };
  const type = !t.type || ['err', '?'].includes(t.type) ? '类型待核实' : types[t.type] || t.type;
  return `
    <div class="target-card" data-target-name="${escapeHtml(t.name)}" data-ra="${t.ra}" data-dec="${t.dec}">
      <span class="target-rank">#${rank}</span>
      <div class="target-info">
        <button type="button" class="target-name target-select" aria-label="查看 ${escapeHtml(t.name)} 构图与高度曲线">${escapeHtml(t.name)}${t.mosaic_recommended ? ' 🧩' : ''} <span>查看构图 →</span></button>
        <span class="target-type">${escapeHtml(type)}</span>
        <span class="target-detail">
          画幅适配 ${t.fov_fit_score == null ? '未核实' : `${(t.fov_fit_score * 100).toFixed(0)}%`}
          ${sb ? ` · 🌌 SB ${sb}` : ''}
          ${rot ? ` · 🔄 ${rot}` : ''}
        </span>
        <span class="target-window">${escapeHtml(windowDescription(t))}</span>
        <span class="target-sho target-sho-${t.sho_advice?.status || 'verify'}">${escapeHtml(t.sho_advice?.label || 'SHO：资料不足，待核实')}</span>
        <details class="target-sho-details"><summary>依据与参考分</summary>
          <span class="target-score" title="旧启发式分数，不是成片成功率">参考分 ${sc} · 非排序依据（按参考分排序时除外）</span>
          ${t.sho_advice ? `<p>${escapeHtml(t.sho_advice.reason)}</p><p>${escapeHtml(t.sho_advice.camera_note)}</p><p>依据：目录类型；SII 强度未核实。</p>` : '<p>滤镜依据未核实</p>'}
        </details>
      </div>
    </div>`;
}

/** Bind target-card clicks to the altitude and mosaic views. */
export function bindTargetInteractions(
  container: HTMLElement,
  handlers: {
    showAltitude?: (target: TelescopeTarget) => void;
    fetchMosaic?: (target: TelescopeTarget) => Promise<void>;
  } = {
    showAltitude: showAltitudeChart,
    fetchMosaic: fetchMosaicGrid,
  },
): void {
  container.addEventListener('click', (event) => {
    if ((event.target as HTMLElement).closest('details')) return;
    const card = (event.target as HTMLElement).closest<HTMLElement>('[data-target-name]');
    if (!card) return;

    const target = lastTargets.find((item) => item.name === card.dataset.targetName);
    if (!target) return;

    if (aladinInstance) {
      try {
        aladinInstance.gotoRaDec(target.ra, target.dec);
      } catch { /* Aladin may still be settling after mode activation */ }
    }

    handlers.showAltitude?.(target);
    if (target.mosaic_recommended) void handlers.fetchMosaic?.(target);
  });
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
  const phases: Record<string, string> = { 'New Moon': '新月', 'Waxing Crescent': '娥眉月', 'First Quarter': '上弦月', 'Waxing Gibbous': '盈凸月', 'Full Moon': '满月', 'Waning Gibbous': '亏凸月', 'Last Quarter': '下弦月', 'Third Quarter': '下弦月', 'Waning Crescent': '残月' };
  const label = currentLanguage === 'zh' ? phases[moon.phase] || moon.phase : moon.phase;
  el.innerHTML = `<span title="${escapeHtml(moon.phase)}">${escapeHtml(label)} · ${(moon.illumination * 100).toFixed(0)}%</span>`;
}

// ---------------------------------------------------------------------------
// Shooting plan rendering
// ---------------------------------------------------------------------------

/** Compact plan timestamps in the same timezone as the observing request. */
export function formatPlanTime(value: string, timezone = 'UTC'): string {
  if (!Number.isFinite(Date.parse(value))) return '时间未核实';
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: timezone, month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(value));
  const part = (type: string) => parts.find((item) => item.type === type)!.value;
  return `${part('month')}-${part('day')} ${part('hour')}:${part('minute')}`;
}

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
          <span>${formatPlanTime(s.start_time, lastMatchBody?.time_zone)}<br>– ${formatPlanTime(s.end_time, lastMatchBody?.time_zone)}</span>
          <span>${escapeHtml(s.target_name)}</span>
          <span>${s.start_alt.toFixed(0)}°→${s.end_alt.toFixed(0)}°</span>
        </div>`).join('')}
      <p class="plan-summary">已安排 ${plan.used_min} / ${plan.total_dark_min} 分钟 · 月面 ${Math.round(plan.moon_illumination * 100)}%</p>
      ${plan.warnings.map((warning) => `<p class="plan-warning">⚠️ ${escapeHtml(warning)}</p>`).join('')}
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

  const Aladin = getAladin();
  if (!Aladin?.catalog) return;

  const catalog = Aladin.catalog({
    name: 'Targets',
    sourceSize: 8,
    shape: 'circle',
    color: '#00ff88',
    onClick: 'showTable',
  });

  catalog.addSources(
    targets.map((target) => Aladin.source(target.ra, target.dec, { name: target.name })),
  );

  aladinInstance.addCatalog(catalog);
  setTargetCatalog(catalog);
}
