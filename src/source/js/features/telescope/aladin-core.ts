// =============================================================================
// Telescope mode — Aladin Lite bridge (coverage-exempt)
// =============================================================================
//
// Aladin Lite is bundled with the frontend. Runtime integration requires WebGL
// and a live sky survey, so the initialisation path remains coverage-exempt.
// =============================================================================

import {
  aladinInstance, aladinInitPromise,
  fovCanvas, fovCanvasCtx, fovAnimFrame,
  setAladinInstance, setAladinInitialized, setAladinInitPromise,
  setFovCanvas, setFovCanvasCtx, setFovAnimFrame,
} from '../../state';
import { TELESCOPE_PRESETS, selectedOpticalConfig } from './presets';
export { TELESCOPE_PRESETS } from './presets';

// The CDS-hosted Aladin script and default survey are unreachable from the
// deployment network. The npm package removes the script dependency; ESA's
// public HiPS mirror supplies the survey imagery.
let Aladin: any = null;
export function getAladin(): any {
  return Aladin;
}
export const SKY_SURVEY_URL = 'https://skies.esac.esa.int/DSSColor';

// ---------------------------------------------------------------------------
// Telescope presets (pure data — testable)
// ---------------------------------------------------------------------------



// ---------------------------------------------------------------------------
// Aladin Lite initialisation (coverage-exempt)
// ---------------------------------------------------------------------------

/* c8 ignore start — Aladin Lite: requires WebGL + live survey */
export async function ensureAladinReady(): Promise<any> {
  if (aladinInstance) return aladinInstance;
  if (aladinInitPromise) return aladinInitPromise;

  const promise = (async () => {
    const module = await import('aladin-lite');
    Aladin = module.default;
    await Aladin.init;

    const initialFov = calculateFovFromInputs();
    const instance = Aladin.aladin('#aladin-lite-div', {
      target: '00:42:44.3 +41:16:09',
      fov: Number.isFinite(initialFov.fovW) && initialFov.fovW > 0 ? initialFov.fovW * 1.3 : 6,
      survey: Aladin.imageHiPS(SKY_SURVEY_URL, { name: 'DSS Color (ESA mirror)' }),
      cooFrame: 'equatorial',
      mode: 'dark',
      log: false,
      showCooGridControl: false,
      showSimbadPointerControl: false,
      showProjectionControl: false,
      showFullscreenControl: false,
    });

    initAladinInstance(instance);
    const root = document.getElementById('aladin-lite-div');
    if (root) {
      // Aladin exposes control tooltips as text but omits button names.
      const nameControls = () => root.querySelectorAll<HTMLButtonElement>('button:not([aria-label])').forEach((button) => {
        const tooltip = button.closest('.aladin-tooltip-container')?.textContent?.trim();
        if (tooltip) button.setAttribute('aria-label', tooltip);
      });
      nameControls();
      new MutationObserver(nameControls).observe(root, { childList: true, subtree: true });
    }
    setAladinInitialized(true);
    return instance;
  })();

  void promise.catch(() => setAladinInitPromise(null));
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
  const config = selectedOpticalConfig();
  return calculateFov(fl * (config?.reducer_factor ?? 1) * (config?.barlow_factor ?? 1), sw, sh);
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
    const showFrame = (document.getElementById('show-fov-checkbox') as HTMLInputElement | null)?.checked ?? true;
    if (!showFrame || !Number.isFinite(fovW + fovH) || fovW <= 0 || fovH <= 0) { setFovAnimFrame(requestAnimationFrame(draw)); return; }
    const raDec = aladinInstance.getRaDec();
    const tl = aladinInstance.world2pix(raDec[0] - fovW / 2, raDec[1] + fovH / 2);
    const br = aladinInstance.world2pix(raDec[0] + fovW / 2, raDec[1] - fovH / 2);
    if (!tl || !br) { setFovAnimFrame(requestAnimationFrame(draw)); return; }
    ctx.strokeStyle = 'rgba(52,152,219,0.8)';
    ctx.lineWidth = 2;
    ctx.save();
    ctx.translate(w / 2, h / 2);
    const rotation = Number((document.getElementById('telescope-rotation') as HTMLInputElement | null)?.value || 0);
    ctx.rotate(rotation * Math.PI / 180);
    ctx.strokeRect(tl[0] - w / 2, tl[1] - h / 2, br[0] - tl[0], br[1] - tl[1]);
    ctx.restore();
    setFovAnimFrame(requestAnimationFrame(draw));
  };
  setFovAnimFrame(requestAnimationFrame(draw));
}

export function updateFovOverlay(): void {
  const { fovW, fovH } = calculateFovFromInputs();
  const label = document.getElementById('fov-display');
  if (label) label.textContent = Number.isFinite(fovW + fovH) && fovW > 0 && fovH > 0
    ? `${fovW.toFixed(1)}° × ${fovH.toFixed(1)}°` : '未核实';
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

  const camera = document.getElementById('telescope-camera-type') as HTMLSelectElement | null;
  if (camera) camera.value = preset.config?.camera_type ?? 'unknown';

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
