// =============================================================================
// Telescope mode — Aladin Lite CDN bridge (coverage-exempt)
// =============================================================================
//
// This module dynamically loads the Aladin Lite v3 script from CDN and provides
// typed wrappers around the global `A` API.  Because Aladin Lite is loaded at
// runtime via a <script> injection, the integration code (loadAladinScript,
// ensureAladinReady) cannot be unit-tested — these sections are marked with
// c8 ignore comments.
// =============================================================================

import {
  aladinInstance, aladinInitialized, aladinInitPromise,
  aladinScriptLoaded, aladinScriptPromise,
  fovCanvas, fovCanvasCtx, fovAnimFrame, mosaicGrid,
  setAladinInstance, setAladinInitialized, setAladinInitPromise,
  setAladinScriptLoaded, setAladinScriptPromise,
  setFovCanvas, setFovCanvasCtx, setFovAnimFrame,
} from '../../state';
import type { TelescopePreset } from '../../types/telescope';

// ---------------------------------------------------------------------------
// Telescope presets (pure data — testable)
// ---------------------------------------------------------------------------

export const TELESCOPE_PRESETS: Record<string, TelescopePreset> = {
  custom: { name: '自定义' },
  'seestar-s50': { name: 'Seestar S50', focalLength: 250, sensorWidth: 7.6, sensorHeight: 5.7 },
  'redcat51-asi2600': { name: 'RedCat51 + ASI2600', focalLength: 250, sensorWidth: 23.5, sensorHeight: 15.7 },
  'fullframe-200mm': { name: '全画幅 + 200mm', focalLength: 200, sensorWidth: 36, sensorHeight: 24 },
  'fullframe-85mm': { name: '全画幅 + 85mm', focalLength: 85, sensorWidth: 36, sensorHeight: 24 },
};

// ---------------------------------------------------------------------------
// Aladin Lite dynamic loading (coverage-exempt)
// ---------------------------------------------------------------------------

/* c8 ignore start — Aladin Lite CDN: cannot test without browser + network */
function loadAladinScript(): Promise<void> {
  if (aladinScriptLoaded) return aladinScriptPromise!;
  if (aladinScriptPromise) return aladinScriptPromise;

  const promise = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js';
    script.onload = () => { setAladinScriptLoaded(true); resolve(); };
    script.onerror = () => reject(new Error('Aladin Lite script failed to load'));
    document.head.appendChild(script);
  });

  setAladinScriptPromise(promise);
  return promise;
}

export async function ensureAladinReady(): Promise<any> {
  if (aladinInstance) return aladinInstance;
  if (aladinInitPromise) return aladinInitPromise;

  const promise = (async () => {
    await loadAladinScript();
    const A = (window as any).A;
    if (!A) throw new Error('Aladin Lite global (A) not found');

    await A.init();

    const instance = A.aladin('#aladin-lite-div', {
      target: 'M31',
      fov: 2,
      survey: 'P/DSS2/color',
      cooFrame: 'equatorial',
      showCooGridControl: false,
      showSimbadPointerControl: false,
      showProjectionControl: false,
      showFullscreenControl: false,
    });

    initAladinInstance(instance);
    setAladinInitialized(true);
    return instance;
  })();

  setAladinInitPromise(promise);
  return promise;
}
/* c8 ignore stop */

// ---------------------------------------------------------------------------
// FOV canvas
// ---------------------------------------------------------------------------

/** Pure math: compute FOV dimensions from optical parameters. */
export function calculateFov(
  focalLength: number,
  sensorW: number,
  sensorH: number,
): { fovW: number; fovH: number } {
  const fovW = 2 * Math.atan(sensorW / (2 * focalLength)) * (180 / Math.PI);
  const fovH = 2 * Math.atan(sensorH / (2 * focalLength)) * (180 / Math.PI);
  return { fovW, fovH };
}

/** Read FOV from DOM inputs, compute dimensions, and return them. */
export function calculateFovFromInputs(): { fovW: number; fovH: number } {
  const fl = parseFloat((document.getElementById('telescope-focal-length') as HTMLInputElement)?.value || '250');
  const sw = parseFloat((document.getElementById('telescope-sensor-width') as HTMLInputElement)?.value || '23.5');
  const sh = parseFloat((document.getElementById('telescope-sensor-height') as HTMLInputElement)?.value || '15.7');
  return calculateFov(fl, sw, sh);
}

/* c8 ignore start — Canvas rendering — visual correctness requires manual/e2e verification */
export function setupFovCanvas(): void {
  const container = document.getElementById('aladin-lite-div');
  if (!container) return;

  let canvas = document.getElementById('fov-overlay-canvas') as HTMLCanvasElement | null;
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'fov-overlay-canvas';
    canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:10;';
    container.appendChild(canvas);
  }
  setFovCanvas(canvas);
  setFovCanvasCtx(canvas.getContext('2d'));

  if (fovAnimFrame) cancelAnimationFrame(fovAnimFrame);
  const draw = () => {
    const el = fovCanvas;
    const ctx = fovCanvasCtx;
    if (!el || !ctx || !aladinInstance) return;
    const w = el.width = el.clientWidth;
    const h = el.height = el.clientHeight;
    ctx.clearRect(0, 0, w, h);
    const { fovW, fovH } = calculateFovFromInputs();
    if (fovW <= 0 || fovH <= 0) { setFovAnimFrame(requestAnimationFrame(draw)); return; }
    const raDec = aladinInstance.getRaDec();
    const tl = aladinInstance.world2pix(raDec[0] - fovW / 2, raDec[1] + fovH / 2);
    const br = aladinInstance.world2pix(raDec[0] + fovW / 2, raDec[1] - fovH / 2);
    if (!tl || !br) { setFovAnimFrame(requestAnimationFrame(draw)); return; }
    ctx.strokeStyle = 'rgba(52,152,219,0.8)';
    ctx.lineWidth = 1;
    ctx.strokeRect(tl[0], tl[1], br[0] - tl[0], br[1] - tl[1]);
    setFovAnimFrame(requestAnimationFrame(draw));
  };
  setFovAnimFrame(requestAnimationFrame(draw));
}

export function updateFovOverlay(): void {
  if (fovCanvasCtx && fovCanvas) {
    fovCanvasCtx.clearRect(0, 0, fovCanvas.width, fovCanvas.height);
  }
  if (!fovAnimFrame) setupFovCanvas();
}
/* c8 ignore stop */

// ---------------------------------------------------------------------------
// Preset application
// ---------------------------------------------------------------------------

/** Apply a telescope preset to the form inputs. */
export function applyPreset(presetKey: string): void {
  const preset = TELESCOPE_PRESETS[presetKey];
  if (!preset || presetKey === 'custom') return;

  const fl = document.getElementById('telescope-focal-length') as HTMLInputElement | null;
  const sw = document.getElementById('telescope-sensor-width') as HTMLInputElement | null;
  const sh = document.getElementById('telescope-sensor-height') as HTMLInputElement | null;

  if (fl && preset.focalLength != null) fl.value = String(preset.focalLength);
  if (sw && preset.sensorWidth != null) sw.value = String(preset.sensorWidth);
  if (sh && preset.sensorHeight != null) sh.value = String(preset.sensorHeight);
}

// ---------------------------------------------------------------------------
// Mosaic integration callback (breaks circular dependency)
// ---------------------------------------------------------------------------

type AladinReadyCallback = (instance: any) => void;
const onReadyCallbacks: AladinReadyCallback[] = [];

/** Register a callback to be invoked when the Aladin instance becomes ready. */
export function onAladinReady(fn: AladinReadyCallback): void {
  if (aladinInstance) {
    fn(aladinInstance);
  } else {
    onReadyCallbacks.push(fn);
  }
}

// Wrapper that both stores the instance and fires registered callbacks.
// (ES module imports are read-only, so we wrap rather than monkey-patch.)
export function initAladinInstance(instance: any): void {
  setAladinInstance(instance);
  onReadyCallbacks.forEach((fn) => fn(instance));
  onReadyCallbacks.length = 0;
}
