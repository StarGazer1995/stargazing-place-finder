// =============================================================================
// Mosaic planning — grid calculation, Aladin overlay & panel UI
// =============================================================================

import { aladinInstance, mosaicGrid, mosaicOverlay, lastMatchBody, lastMosaicTarget } from '../../state';
import { setMosaicGrid, setMosaicOverlay, setLastMosaicTarget } from '../../state';
import { API_CONFIG } from '../../core/api';
import { onAladinReady } from '../telescope/aladin-core';
import type { MosaicGrid, MosaicPanel, TelescopeTarget } from '../../types/telescope';

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

/** Wire up mosaic panel UI (runs once at page load). */
export function initMosaic(): void {
  const mosaicHeader = document.getElementById('mosaic-panel-header');
  if (mosaicHeader) {
    mosaicHeader.addEventListener('click', () => {
      const body = document.getElementById('mosaic-panel-body');
      const arrow = mosaicHeader.querySelector('.collapse-arrow');
      if (body) {
        const collapsed = body.style.display === 'none';
        body.style.display = collapsed ? 'block' : 'none';
        if (arrow) arrow.textContent = collapsed ? '▼' : '▶';
      }
    });
  }

  const slider = document.getElementById('mosaic-overlap') as HTMLInputElement | null;
  if (slider) {
    slider.addEventListener('input', function (this: HTMLInputElement) {
      const val = document.getElementById('mosaic-overlap-val');
      if (val) val.textContent = this.value + '%';
      if (mosaicGrid && lastMosaicTarget) {
        fetchMosaicGrid(lastMosaicTarget);
      }
    });
  }
}

// ---------------------------------------------------------------------------
// API call
// ---------------------------------------------------------------------------

/** Fetch mosaic grid from the backend and render it. */
export async function fetchMosaicGrid(target: TelescopeTarget): Promise<void> {
  const panel = document.getElementById('mosaic-panel') as HTMLElement | null;
  const body = document.getElementById('mosaic-panel-body') as HTMLElement | null;
  const slider = document.getElementById('mosaic-overlap') as HTMLInputElement | null;
  const overlap = slider ? parseFloat(slider.value) / 100 : 0.15;

  if (!lastMatchBody || !body) return;

  setLastMosaicTarget(target);

  body.innerHTML = '<p class="target-loading">计算马赛克网格...</p>';
  if (panel) panel.style.display = 'block';
  const controls = document.getElementById('mosaic-controls');
  if (controls) controls.style.display = 'flex';

  const reqBody = {
    target: {
      name: target.name,
      ra: target.ra,
      dec: target.dec,
      angular_size_arcmin: target.angular_size_arcmin,
      angular_size_min_arcmin: target.angular_size_min_arcmin,
    },
    config: lastMatchBody,
    overlap,
  };

  try {
    const resp = await fetch(`${API_CONFIG.baseUrl}/api/telescope/mosaic`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reqBody),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    if (data.error) { body.innerHTML = `<p class="target-error">${data.error}</p>`; return; }
    setMosaicGrid(data.grid);
    renderMosaicOnAladin(data.grid);
    renderMosaicPanel(data.grid, body);
  } catch (e: any) {
    console.error('Mosaic failed:', e);
    body.innerHTML = `<p class="target-error">马赛克计算失败: ${e.message}</p>`;
  }
}

// ---------------------------------------------------------------------------
// Canvas overlay (coverage-exempt — visual output via Aladin API)
// ---------------------------------------------------------------------------

/* c8 ignore start — Aladin world2pix + Canvas: integration-only */
function renderMosaicOnAladin(grid: MosaicGrid): void {
  if (!aladinInstance) return;
  clearMosaicOverlay();

  let canvas = document.getElementById('mosaic-fov-canvas') as HTMLCanvasElement | null;
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'mosaic-fov-canvas';
    canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:11;';
    const container = document.getElementById('aladin-lite-div');
    if (container) container.appendChild(canvas);
  }
  setMosaicOverlay(canvas);

  setTimeout(() => {
    const ctx = canvas!.getContext('2d')!;
    const w = canvas!.width = canvas!.clientWidth;
    const h = canvas!.height = canvas!.clientHeight;
    ctx.clearRect(0, 0, w, h);

    grid.panels.forEach((p: MosaicPanel) => {
      const corners = p.corners;
      if (!corners || corners.length < 4) return;

      const pts = corners.map((c) => aladinInstance.world2pix(c[0], c[1]));

      ctx.strokeStyle = 'rgba(52,152,219,0.7)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 3]);
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      for (let j = 1; j < 4; j++) ctx.lineTo(pts[j][0], pts[j][1]);
      ctx.closePath();
      ctx.stroke();
      ctx.setLineDash([]);

      const cp = aladinInstance.world2pix(p.ra_center, p.dec_center);
      ctx.fillStyle = 'rgba(52,152,219,0.9)';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`[${p.row},${p.col}]`, cp[0], cp[1] - 8);
    });
  }, 100);
}

function clearMosaicOverlay(): void {
  if (mosaicOverlay) {
    const ctx = mosaicOverlay.getContext('2d');
    if (ctx) ctx.clearRect(0, 0, mosaicOverlay.width, mosaicOverlay.height);
  }
}
/* c8 ignore stop */

// ---------------------------------------------------------------------------
// DOM rendering (testable — returns HTML, applies to container)
// ---------------------------------------------------------------------------

/** Render the mosaic panel UI below the target list. */
export function renderMosaicPanel(grid: MosaicGrid, container: HTMLElement): void {
  container.innerHTML = `
    <div class="mosaic-summary">
      网格 ${grid.rows}×${grid.cols} = ${grid.total_panels} 面板
      | 重叠 ${Math.round(grid.overlap * 100)}%
      | FOV ${grid.fov_width_deg.toFixed(2)}°×${grid.fov_height_deg.toFixed(2)}°
    </div>
    <div class="mosaic-panel-list">
      ${grid.panels.map((p) => `
        <div class="mosaic-panel-item">
          <span class="mp-label">[${p.row},${p.col}]</span>
          <span class="mp-coord">RA ${p.ra_center.toFixed(3)}° Dec ${p.dec_center.toFixed(3)}°</span>
        </div>`).join('')}
    </div>
    <p class="mosaic-hint">💡 蓝色虚线框为拼接面板范围。拖动重叠率滑块实时调整。</p>`;
}

// Register with Aladin ready callback
onAladinReady(() => {
  // Mosaic bridge is ready — mosaic grid can now render overlays
  console.log('[Mosaic] Aladin ready — mosaic overlay bridge active');
});
