// =============================================================================
// Altitude chart — Canvas-drawn altitude curve for the selected target
// =============================================================================

import type { TelescopeTarget } from '../../types/telescope';

// ---------------------------------------------------------------------------
// Pure math helpers (testable)
// ---------------------------------------------------------------------------

export interface ChartLayout {
  pad: { top: number; right: number; bottom: number; left: number };
  pw: number; // plot width
  ph: number; // plot height
}

export function computeChartLayout(w: number, h: number): ChartLayout {
  const pad = { top: 15, right: 10, bottom: 25, left: 40 };
  return { pad, pw: w - pad.left - pad.right, ph: h - pad.top - pad.bottom };
}

export function scaleAltitudeToPixel(
  altitude: number,
  ph: number,
  padTop: number,
  altMin = 0,
  altMax = 90,
): number {
  return padTop + ph * (1 - (altitude - altMin) / (altMax - altMin));
}

export function formatTimeLabel(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}:${String(m).padStart(2, '0')}`;
}

// ---------------------------------------------------------------------------
// Canvas rendering (coverage-exempt — visual output)
// ---------------------------------------------------------------------------

/* c8 ignore start — Canvas 2D rendering: visual correctness verified manually */
export function showAltitudeChart(target: TelescopeTarget): void {
  const panel = document.getElementById('altitude-chart-panel') as HTMLElement | null;
  const canvas = document.getElementById('altitude-chart-canvas') as HTMLCanvasElement | null;
  const title = document.getElementById('altitude-chart-title') as HTMLElement | null;
  if (!panel || !canvas || !target) return;

  const curve = target.altitude_curve;
  if (!curve || curve.length < 2) { panel.style.display = 'none'; return; }

  const sc = target.suitability_score != null ? target.suitability_score.toFixed(0) : '?';
  const fov = target.fov_fit_score != null ? (target.fov_fit_score * 100).toFixed(0) : '?';
  const flt = target.filter_match_score != null ? (target.filter_match_score * 100).toFixed(0) : '?';
  if (title) title.textContent = `📈 ${target.name} — 综合${sc} | FOV${fov}% | 滤镜${flt}%`;
  panel.style.display = 'block';

  requestAnimationFrame(() => {
    const w = panel.clientWidth - 20 || 280;
    const h = 100;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    const ctx = canvas.getContext('2d')!;
    ctx.scale(dpr, dpr);

    const { pad, pw, ph } = computeChartLayout(w, h);

    // Background
    ctx.fillStyle = 'rgba(26,26,46,0.9)';
    ctx.fillRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 0.5;
    for (let alt = 0; alt <= 90; alt += 15) {
      const y = scaleAltitudeToPixel(alt, ph, pad.top);
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
      ctx.fillStyle = 'rgba(255,255,255,0.5)';
      ctx.font = '9px sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(`${alt}°`, pad.left - 4, y + 3);
    }

    // X-axis time labels
    const times = curve.map(p => p.time);
    const step = Math.max(1, Math.floor(times.length / 6));
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'center';
    for (let i = 0; i < times.length; i += step) {
      const x = pad.left + (i / (times.length - 1)) * pw;
      ctx.fillText(times[i]!, x, h - 2);
    }

    // Altitude curve
    ctx.strokeStyle = '#4a90e2';
    ctx.lineWidth = 2;
    ctx.beginPath();
    curve.forEach((p, i) => {
      const x = pad.left + (i / (curve.length - 1)) * pw;
      const y = scaleAltitudeToPixel(p.altitude, ph, pad.top);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Endpoints
    curve.forEach((p, i) => {
      const x = pad.left + (i / (curve.length - 1)) * pw;
      const y = scaleAltitudeToPixel(p.altitude, ph, pad.top);
      ctx.fillStyle = '#4a90e2';
      ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
    });
  });
}
/* c8 ignore stop */
