// =============================================================================
// Application state type — the shape of the centralized store
// =============================================================================

import type { Language, I18nConfig } from './i18n';
import type { LightPollutionPoint, StargazingLocation, AppMode, DrawnPolygon } from './stargazing';
import type { TelescopeTarget, MoonData, MosaicGrid, TelescopePreset } from './telescope';

/** Central application state — the single source of truth. */
export interface AppState {
  // ── Map ──
  map: any; // L.Map — imported lazily to avoid circular type dependency
  currentOverlay: any; // L.LayerGroup | null
  currentImageLayers: any[]; // image overlay array
  pollutionTileLayer: any; // L.TileLayer | null
  dataCache: Map<string, LightPollutionPoint[]>;
  isLoading: boolean;
  loadingIndicator: HTMLElement | null;

  // ── Analysis mode ──
  drawControl: any; // L.Control.Draw | null
  drawnItems: any; // L.FeatureGroup | null
  currentPolygon: DrawnPolygon | null;
  analysisResults: StargazingLocation[];
  isAnalysisMode: boolean;
  statusIndicator: HTMLElement | null;
  resultsPanel: HTMLElement | null;

  // ── Telescope mode ──
  isTelescopeMode: boolean;
  aladinInstance: any; // AladinInstance | null
  aladinInitialized: boolean;
  fovCanvas: HTMLCanvasElement | null;
  fovCanvasCtx: CanvasRenderingContext2D | null;

  // ── Telescope cross-module state ──
  lastMatchBody: any; // TelescopeTargetRequest | null
  lastMosaicTarget: TelescopeTarget | null;
  lastMoon: MoonData | null;
  telescopeTargetLocation: { lat: number; lng: number } | null;
  lastTargets: TelescopeTarget[];

  // ── Mosaic ──
  mosaicGrid: MosaicGrid | null;
  mosaicOverlay: HTMLCanvasElement | null;

  // ── i18n ──
  language: Language;
}
