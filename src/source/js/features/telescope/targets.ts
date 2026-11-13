// =============================================================================
// Telescope targets — API calls for target matching & shooting plan
// =============================================================================

import { lastMatchBody } from '../../state';
import {
  setLastMatchBody, setLastMoon, setLastTargets,
} from '../../state';
import { API_CONFIG, fetchWithTimeout } from '../../core/api';
import { renderTargetResults, renderMoonCard, overlayTargetsOnAladin, renderShootingPlan } from './target-renderer';
import { getText } from '../../core/i18n';
import { readObservationContext } from './observation-context';
import { selectedOpticalConfig } from './presets';
import type { TelescopeConfig, CameraType, TargetSort } from '../../types/telescope';
import type { TelescopeTargetRequest } from '../../types/api';

let requestGeneration = 0;
export function invalidateTargetRequests(): void {
  requestGeneration++;
  const button = document.getElementById('match-targets-btn') as HTMLButtonElement | null;
  if (button) { button.disabled = false; button.textContent = '匹配拍摄目标'; }
  if (!lastMatchBody) {
    const section = document.getElementById('target-results-section');
    if (section) section.style.display = 'none';
  }
  const planButton = document.getElementById('plan-btn') as HTMLButtonElement | null;
  if (planButton?.disabled) { const panel = document.getElementById('plan-panel'); if (panel) panel.style.display = 'none'; }
  if (planButton) { planButton.disabled = false; planButton.textContent = '拍摄计划'; }
}

// ---------------------------------------------------------------------------
// Request builder (pure — testable without DOM)
// ---------------------------------------------------------------------------

/** Build the telescope target-matching request from UI state. */
export function buildTargetRequest(
  focalLength: number,
  sensorW: number,
  sensorH: number,
  obsLat: number,
  obsLng: number,
  tz: string,
  timeStr: string,
  limit: number = 100,
  opticalConfig?: TelescopeConfig,
  sortBy: TargetSort = 'imaging_time',
  cameraType: CameraType = opticalConfig?.camera_type ?? 'unknown',
): TelescopeTargetRequest {
  return {
    ...opticalConfig,
    sort_by: sortBy,
    camera_type: cameraType,
    focal_length_mm: focalLength,
    sensor_width_mm: sensorW,
    sensor_height_mm: sensorH,
    lon: obsLng,
    lat: obsLat,
    time: timeStr,
    time_zone: tz,
    limit,
  };
}

export function buildTimeString(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** Match telescope targets against the current optical config and location. */
/* c8 ignore start — API calls + DOM: requires full browser environment */
export async function matchTelescopeTargets(): Promise<void> {
  const generation = ++requestGeneration;
  setLastMatchBody(null);
  setLastTargets([]);
  for (const id of ['plan-btn', 'plan-panel', 'moon-card', 'altitude-chart-panel', 'mosaic-panel', 'mosaic-controls']) {
    const el = document.getElementById(id); if (el) el.style.display = 'none';
  }
  const btn = document.getElementById('match-targets-btn') as HTMLButtonElement | null;
  const section = document.getElementById('target-results-section') as HTMLElement | null;
  const list = document.getElementById('target-results-list') as HTMLElement | null;
  const countEl = section?.querySelector('.target-count') as HTMLElement | null;

  if (countEl) countEl.textContent = '';
  const queryTime = document.getElementById('target-query-time');
  if (queryTime) queryTime.textContent = '';
  if (btn) { btn.disabled = true; btn.textContent = '⏳ 匹配中...'; }
  if (list) list.innerHTML = '<p class="target-loading">正在分析最佳拍摄目标...</p>';
  if (section) section.style.display = 'block';

  try {
    const fl = parseFloat((document.getElementById('telescope-focal-length') as HTMLInputElement)?.value || '250');
    const sw = parseFloat((document.getElementById('telescope-sensor-width') as HTMLInputElement)?.value || '23.5');
    const sh = parseFloat((document.getElementById('telescope-sensor-height') as HTMLInputElement)?.value || '15.7');

    const context = readObservationContext();
    const body = buildTargetRequest(fl, sw, sh, context.lat, context.lng, context.timezone, context.time, 100, selectedOpticalConfig(),
      (document.getElementById('telescope-target-sort') as HTMLSelectElement)?.value as TargetSort || 'imaging_time',
      (document.getElementById('telescope-camera-type') as HTMLSelectElement)?.value as CameraType || 'unknown');

    const resp = await fetchWithTimeout(`${API_CONFIG.baseUrl}/api/telescope/targets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }, 60_000);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (generation !== requestGeneration) return;
    const targets = data.targets || [];
    const moon = data.moon || null;

    setLastMoon(moon);
    setLastMatchBody(body);
    setLastTargets(targets);
    const queryTime = document.getElementById('target-query-time');
    if (queryTime) queryTime.textContent = `观测时间 ${body.time} · ${body.time_zone}`;

    if (countEl) countEl.textContent = `（${targets.length} 个目标）`;
    if (list) renderTargetResults(targets, list);
    renderMoonCard(moon);
    overlayTargetsOnAladin(targets);

    const planBtn = document.getElementById('plan-btn');
    if (planBtn) planBtn.style.display = '';
    (document.getElementById('observation-details') as HTMLDetailsElement).open = false;
    (document.getElementById('telescope-config-details') as HTMLDetailsElement).open = false;
    const scroll = section?.closest<HTMLElement>('.workspace-scroll');
    if (scroll && section) scroll.scrollTop = section.offsetTop - scroll.offsetTop;
  } catch (e: any) {
    if (generation !== requestGeneration) return;
    console.error('Target matching failed:', e);
    if (list) {
      const error = document.createElement('p');
      error.className = 'target-error';
      error.textContent = [getText('ui.invalidObservation'), getText('ui.invalidTimezone')].includes(e.message) ? e.message : '未能完成匹配，请稍后重试。';
      list.replaceChildren(error);
    }
    if (countEl) countEl.textContent = '';
  } finally {
    if (btn && generation === requestGeneration) { btn.disabled = false; btn.textContent = '匹配拍摄目标'; }
  }
}

/** Fetch and display a single-night shooting plan. */
export async function fetchShootingPlan(): Promise<void> {
  const generation = requestGeneration;
  const btn = document.getElementById('plan-btn') as HTMLButtonElement | null;
  const panel = document.getElementById('plan-panel') as HTMLElement | null;
  const bodyEl = document.getElementById('plan-panel-body') as HTMLElement | null;
  const label = panel?.querySelector('.plan-night-label') as HTMLElement | null;
  if (!lastMatchBody) return;

  if (btn) { btn.disabled = true; btn.textContent = '⏳ 生成计划...'; }
  if (bodyEl) bodyEl.innerHTML = '<p class="target-loading">正在生成拍摄计划...</p>';
  if (panel) panel.style.display = 'block';

  try {
    const resp = await fetchWithTimeout(`${API_CONFIG.baseUrl}/api/telescope/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lastMatchBody),
    }, 60_000);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (generation !== requestGeneration) return;
    const plan = data.plan;
    const targets = data.targets || [];

    if (plan?.date && label) label.textContent = `${plan.date} · ${lastMatchBody.time_zone}`;
    if (bodyEl) {
      renderShootingPlan(plan, targets, bodyEl);
      const scroll = panel?.closest<HTMLElement>('.workspace-scroll');
      if (scroll && panel) scroll.scrollTop = panel.offsetTop - scroll.offsetTop;
    }
  } catch (e: any) {
    if (generation !== requestGeneration) return;
    console.error('Shooting plan failed:', e);
    if (bodyEl) bodyEl.innerHTML = `<p class="target-error">计划生成失败: ${e.message}</p>`;
    if (label) label.textContent = '';
  } finally {
    if (btn && generation === requestGeneration) { btn.disabled = false; btn.textContent = '📋 拍摄计划'; }
  }
}
