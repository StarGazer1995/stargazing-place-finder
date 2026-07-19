/// <reference types="vite/client" />

// =============================================================================
// External library type declarations for packages without official @types
// =============================================================================

// Leaflet.Draw — community types are incomplete; declare as loose module
declare module 'leaflet-draw' {
  const draw: any;
  export default draw;
}

// Leaflet.MarkerCluster — community types exist but may be incomplete
declare module 'leaflet.markercluster' {
  import * as L from 'leaflet';

  export class MarkerClusterGroup extends L.FeatureGroup {
    constructor(options?: any);
    addLayer(layer: L.Layer): this;
    removeLayer(layer: L.Layer): this;
    clearLayers(): this;
    getChildCount(): number;
    getAllChildMarkers(): L.Marker[];
    refreshClusters(): void;
  }
}

// Aladin Lite v3 — loaded dynamically from CDN (no npm package available)
declare var A: any;

// Application config injected by the server (if any)
interface Window {
  APP_CONFIG?: {
    apiBaseUrl?: string;
  };
}
