// =============================================================================
// Stargazing Draw — Leaflet.Draw integration for area selection
// =============================================================================

import L from 'leaflet';
import 'leaflet-draw';
import {
  map, drawnItems, drawControl, currentPolygon,
  analysisResults, resultsPanel, isAnalysisMode,
  setDrawnItems, setDrawControl, setCurrentPolygon, setAnalysisResults,
} from '../../state';
import type { GeoBounds } from '../../types/api';

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Initialize the Leaflet.Draw rectangle control on the map. */
export function initializeDrawControls(): void {
  const items = new L.FeatureGroup();
  setDrawnItems(items);
  map.addLayer(drawnItems);

  const control = new (L.Control as any).Draw({
    edit: { featureGroup: drawnItems },
    draw: {
      polygon: false,
      polyline: false,
      circle: false,
      circlemarker: false,
      marker: false,
      rectangle: {
        shapeOptions: {
          color: '#4a90e2',
          weight: 2,
          fillOpacity: 0.1,
        },
      },
    },
  });

  setDrawControl(control);
  map.addControl(drawControl);

  bindDrawEventListeners();
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

function bindDrawEventListeners(): void {
  map.on((L as any).Draw.Event.CREATED, handleDrawCreated);
  map.on((L as any).Draw.Event.DELETED, handleDrawDeleted);
}

function handleDrawCreated(e: any): void {
  const layer = e.layer;
  drawnItems.addLayer(layer);

  const latlngs = layer.getLatLngs()[0];
  const coordinates: Array<[number, number]> = latlngs.map((ll: L.LatLng) => [ll.lng, ll.lat]);

  const lats = coordinates.map((c) => c[1]);
  const lngs = coordinates.map((c) => c[0]);

  const bbox: GeoBounds = {
    south: Math.min(...lats),
    west: Math.min(...lngs),
    north: Math.max(...lats),
    east: Math.max(...lngs),
  };

  setCurrentPolygon({ layer, coordinates, bbox });
}

function handleDrawDeleted(_e: any): void {
  setCurrentPolygon(null);
}

// ---------------------------------------------------------------------------
// Cleanup
// ---------------------------------------------------------------------------

/** Clear all analysis results and drawn shapes. */
export function clearAnalysisResults(): void {
  setAnalysisResults([]);
  if (resultsPanel) {
    resultsPanel.style.display = 'none';
    resultsPanel.innerHTML = '';
  }
}

/** Remove drawn items and reset analysis state. */
export function clearAll(): void {
  if (drawnItems) drawnItems.clearLayers();
  setCurrentPolygon(null);
  clearAnalysisResults();
}
