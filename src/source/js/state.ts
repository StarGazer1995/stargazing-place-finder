// =============================================================================
// Centralized application state — replaces 48 scattered global variables
// =============================================================================
//
// Every module that previously read/wrote global variables now imports from
// this module.  The state object is mutable for now (Phase 1); a future phase
// can layer Proxy/watch for reactive change detection without changing the
// module's public API.
// =============================================================================

import type { LightPollutionPoint, StargazingLocation, DrawnPolygon } from './types/stargazing';
import type { TelescopeTarget, MoonData, MosaicGrid } from './types/telescope';
import type { Language } from './types/i18n';

// ---------------------------------------------------------------------------
// Map state
// ---------------------------------------------------------------------------

export let map: any = null;
export let currentOverlay: any = null;
export let currentImageLayers: any[] = [];
export let pollutionTileLayer: any = null;
export let dataCache = new Map<string, LightPollutionPoint[]>();
export let isLoading = false;
export let loadingIndicator: HTMLElement | null = null;

export function setMap(m: any): void { map = m; }
export function setCurrentOverlay(o: any): void { currentOverlay = o; }
export function setCurrentImageLayers(layers: any[]): void { currentImageLayers = layers; }
export function setPollutionTileLayer(l: any): void { pollutionTileLayer = l; }
export function setIsLoading(v: boolean): void { isLoading = v; }
export function setLoadingIndicator(el: HTMLElement | null): void { loadingIndicator = el; }

// ---------------------------------------------------------------------------
// Analysis mode state
// ---------------------------------------------------------------------------

export let drawControl: any = null;
export let drawnItems: any = null;
export let currentPolygon: DrawnPolygon | null = null;
export let analysisResults: StargazingLocation[] = [];
export let isAnalysisMode = false;
export let statusIndicator: HTMLElement | null = null;
export let resultsPanel: HTMLElement | null = null;

export function setDrawControl(c: any): void { drawControl = c; }
export function setDrawnItems(items: any): void { drawnItems = items; }
export function setCurrentPolygon(p: DrawnPolygon | null): void { currentPolygon = p; }
export function setAnalysisResults(r: StargazingLocation[]): void { analysisResults = r; }
export function setIsAnalysisMode(v: boolean): void { isAnalysisMode = v; }
export function setStatusIndicator(el: HTMLElement | null): void { statusIndicator = el; }
export function setResultsPanel(el: HTMLElement | null): void { resultsPanel = el; }

// ---------------------------------------------------------------------------
// Telescope mode state
// ---------------------------------------------------------------------------

export let isTelescopeMode = false;
export let aladinInstance: any = null;
export let aladinInitialized = false;
export let aladinInitPromise: Promise<void> | null = null;
export let aladinScriptLoaded = false;
export let aladinScriptPromise: Promise<void> | null = null;
export let fovCanvas: HTMLCanvasElement | null = null;
export let fovCanvasCtx: CanvasRenderingContext2D | null = null;
export let fovAnimFrame: number | null = null;

export function setIsTelescopeMode(v: boolean): void { isTelescopeMode = v; }
export function setAladinInstance(instance: any): void { aladinInstance = instance; }
export function setAladinInitialized(v: boolean): void { aladinInitialized = v; }
export function setAladinInitPromise(p: Promise<void> | null): void { aladinInitPromise = p; }
export function setAladinScriptLoaded(v: boolean): void { aladinScriptLoaded = v; }
export function setAladinScriptPromise(p: Promise<void> | null): void { aladinScriptPromise = p; }
export function setFovCanvas(c: HTMLCanvasElement | null): void { fovCanvas = c; }
export function setFovCanvasCtx(ctx: CanvasRenderingContext2D | null): void { fovCanvasCtx = ctx; }
export function setFovAnimFrame(id: number | null): void { fovAnimFrame = id; }

// ---------------------------------------------------------------------------
// Cross-module telescope state (replaces window._lastMatchBody etc.)
// ---------------------------------------------------------------------------

export let lastMatchBody: any = null;
export let lastMosaicTarget: TelescopeTarget | null = null;
export let lastMoon: MoonData | null = null;
export let telescopeTargetLocation: { lat: number; lng: number } | null = null;
export let lastTargets: TelescopeTarget[] = [];
export let targetCatalog: any = null;

export function setLastMatchBody(body: any): void { lastMatchBody = body; }
export function setLastMosaicTarget(t: TelescopeTarget | null): void { lastMosaicTarget = t; }
export function setLastMoon(m: MoonData | null): void { lastMoon = m; }
export function setTelescopeTargetLocation(loc: { lat: number; lng: number } | null): void { telescopeTargetLocation = loc; }
export function setLastTargets(targets: TelescopeTarget[]): void { lastTargets = targets; }
export function setTargetCatalog(cat: any): void { targetCatalog = cat; }

// ---------------------------------------------------------------------------
// Mosaic state
// ---------------------------------------------------------------------------

export let mosaicGrid: MosaicGrid | null = null;
export let mosaicOverlay: HTMLCanvasElement | null = null;

export function setMosaicGrid(g: MosaicGrid | null): void { mosaicGrid = g; }
export function setMosaicOverlay(c: HTMLCanvasElement | null): void { mosaicOverlay = c; }

// ---------------------------------------------------------------------------
// i18n state
// ---------------------------------------------------------------------------

export let currentLanguage: Language = 'zh';

export function setCurrentLanguage(lang: Language): void {
  currentLanguage = lang;
  try {
    localStorage.setItem('stargazing-language', lang);
  } catch { /* localStorage may be unavailable */ }
}
