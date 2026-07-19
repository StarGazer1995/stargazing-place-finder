// =============================================================================
// Telescope targets — API calls for target matching & shooting plan
// =============================================================================

import { aladinInstance, map, telescopeTargetLocation, lastMatchBody, lastMoon, lastTargets } from '../../state';
import {
  setLastMatchBody, setLastMoon, setLastTargets, setTelescopeTargetLocation,
} from '../../state';
import { API_CONFIG } from '../../core/api';
import { renderTargetResults, renderMoonCard, overlayTargetsOnAladin, renderShootingPlan } from './target-renderer';
import { showAltitudeChart } from './altitude-chart';
import type { TelescopeTargetRequest } from '../../types/api';

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
): TelescopeTargetRequest {
  return {
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

function buildTimeString(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/** Match telescope targets against the current optical config and location. */
export async function matchTelescopeTargets(): Promise<void> {
  const btn = document.getElementById('match-targets-btn') as HTMLButtonElement | null;
  const section = document.getElementById('target-results-section') as HTMLElement | null;
  const list = document.getElementById('target-results-list') as HTMLElement | null;
  const countEl = section?.querySelector('.target-count') as HTMLElement | null;

  if (btn) { btn.disabled = true; btn.textContent = '⏳ 匹配中...'; }
  if (list) list.innerHTML = '<p class="target-loading">正在分析最佳拍摄目标...</p>';
  if (section) section.style.display = 'block';

  try {
    const fl = parseFloat((document.getElementById('telescope-focal-length') as HTMLInputElement)?.value || '250');
    const sw = parseFloat((document.getElementById('telescope-sensor-width') as HTMLInputElement)?.value || '23.5');
    const sh = parseFloat((document.getElementById('telescope-sensor-height') as HTMLInputElement)?.value || '15.7');

    const raDec = aladinInstance ? aladinInstance.getRaDec() : [0, 0];
    let obsLat: number, obsLng: number;
    if (telescopeTargetLocation) {
      obsLat = telescopeTargetLocation.lat;
      obsLng = telescopeTargetLocation.lng;
    } else if (map) {
      const mc = map.getCenter();
      obsLat = mc.lat;
      obsLng = mc.lng;
    } else {
      obsLat = 40; obsLng = 116;
    }

    const body = buildTargetRequest(fl, sw, sh, obsLat, obsLng, Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC', buildTimeString());

    // Reverse-geocode for display
    let placeName = '';
    try {
      const geoResp = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${obsLat}&lon=${obsLng}&zoom=10`);
      const geoData = await geoResp.json();
      placeName = geoData.display_name || '';
    } catch { /* ignore */ }
    if (countEl) countEl.textContent = placeName ? `📍 ${placeName} ` : '';

    const resp = await fetch(`${API_CONFIG.baseUrl}/api/telescope/targets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const targets = data.targets || [];
    const moon = data.moon || null;

    setLastMoon(moon);
    setLastMatchBody(body);
    setLastTargets(targets);

    if (countEl) countEl.textContent += `(${targets.length} 个目标)`;
    if (list) renderTargetResults(targets, list);
    renderMoonCard(moon);
    overlayTargetsOnAladin(targets);

    const planBtn = document.getElementById('plan-btn');
    if (planBtn) planBtn.style.display = '';
  } catch (e: any) {
    console.error('Target matching failed:', e);
    if (list) list.innerHTML = `<p class="target-error">匹配失败: ${e.message}</p>`;
    if (countEl) countEl.textContent = '';
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🎯 匹配拍摄目标'; }
  }
}

/** Fetch and display a single-night shooting plan. */
export async function fetchShootingPlan(): Promise<void> {
  const btn = document.getElementById('plan-btn') as HTMLButtonElement | null;
  const panel = document.getElementById('plan-panel') as HTMLElement | null;
  const bodyEl = document.getElementById('plan-panel-body') as HTMLElement | null;
  const label = panel?.querySelector('.plan-night-label') as HTMLElement | null;
  if (!lastMatchBody) return;

  if (btn) { btn.disabled = true; btn.textContent = '⏳ 生成计划...'; }
  if (bodyEl) bodyEl.innerHTML = '<p class="target-loading">正在生成拍摄计划...</p>';
  if (panel) panel.style.display = 'block';

  try {
    const resp = await fetch(`${API_CONFIG.baseUrl}/api/telescope/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(lastMatchBody),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const plan = data.plan;
    const targets = data.targets || [];

    if (plan?.date && label) label.textContent = `${plan.date}  ${data.moon?.phase || ''}`;
    if (bodyEl) {
      renderShootingPlan(plan, targets, bodyEl);
    }
  } catch (e: any) {
    console.error('Shooting plan failed:', e);
    if (bodyEl) bodyEl.innerHTML = `<p class="target-error">计划生成失败: ${e.message}</p>`;
    if (label) label.textContent = '';
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '📋 拍摄计划'; }
  }
}
