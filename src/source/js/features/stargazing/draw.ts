// =============================================================================
// Stargazing Draw — Leaflet.Draw integration for area selection
// =============================================================================

import L from 'leaflet';
import 'leaflet-draw';
import {
  map, drawnItems, drawControl, currentPolygon,
  resultsPanel,
  setDrawnItems, setDrawControl, setCurrentPolygon, setAnalysisResults,
} from '../../state';
import type { GeoBounds } from '../../types/api';
import { getText } from '../../core/i18n';
import { cancelAreaAnalysis } from './analyzer';
import { clearResultMarkers } from './results';

let rectangle: any = null;
let drawing = false;
let suppressClickUntil = 0;

export function shouldIgnoreMapClick(): boolean {
  return drawing || Date.now() < suppressClickUntil;
}

export function startDrawing(): void {
  cancelAreaAnalysis();
  map.closePopup();
  rectangle?.disable();
  // Leaflet.Draw 1.0.4's metric area tooltip references an undeclared `type`
  // in strict bundles. Area is not needed to select a bbox; keep drawing usable.
  rectangle = new (L as any).Draw.Rectangle(map, { showArea: false, shapeOptions: { color: '#4a90e2', weight: 2 } });
  rectangle.enable();
}

export function stopDrawing(): void {
  rectangle?.disable();
  // Also disable tools activated from the Leaflet toolbar.
  const toolbars = drawControl?._toolbars || {};
  Object.values(toolbars).forEach((toolbar: any) => toolbar.disable());
  setDrawing(false);
}

function setDrawing(active: boolean): void {
  drawing = active;
  if (!active) suppressClickUntil = Date.now() + 350;
  document.body.classList.toggle('drawing-area', active);
  const cancel = document.getElementById('cancel-draw-button');
  if (cancel) cancel.hidden = !active;
  const label = document.getElementById('selection-status');
  if (label) label.textContent = getText(active ? 'ui.dragPrompt' : currentPolygon ? 'ui.selected' : 'ui.noSelection');
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** Initialize the Leaflet.Draw rectangle control on the map. */
/* c8 ignore start — Leaflet.Draw: requires full browser environment */
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
        showArea: false,
        shapeOptions: {
          color: '#4a90e2',
          weight: 2,
          fillOpacity: 0.1,
        },
      },
    },
  });

  setDrawControl(control);

  bindDrawEventListeners();
}

// ---------------------------------------------------------------------------
// Event listeners
// ---------------------------------------------------------------------------

function bindDrawEventListeners(): void {
  map.on('draw:drawstart draw:editstart draw:deletestart', () => {
    cancelAreaAnalysis();
    map.closePopup();
    setDrawing(true);
  });
  map.on('draw:drawstop draw:editstop draw:deletestop', () => setDrawing(false));
  map.on((L as any).Draw.Event.CREATED, handleDrawCreated);
  map.on((L as any).Draw.Event.DELETED, handleDrawDeleted);
  map.on('draw:edited', (event: any) => event.layers.eachLayer((layer: any) => handleDrawCreated({ layer })));
}

function handleDrawCreated(e: any): void {
  const layer = e.layer;
  cancelAreaAnalysis();
  drawnItems.clearLayers();
  clearAnalysisResults();
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
  setDrawing(false);
  const clear = document.getElementById('clear-button') as HTMLButtonElement | null;
  if (clear) clear.disabled = false;

  const analyzeBtn = document.getElementById('analyze-button') as HTMLButtonElement | null;
  if (analyzeBtn) analyzeBtn.disabled = false;
  const status = document.getElementById('status-indicator');
  if (status) status.textContent = '区域已选好，点击“分析观星地点”';
}

function handleDrawDeleted(_e: any): void {
  cancelAreaAnalysis();
  setCurrentPolygon(null);
  setDrawing(false);
  const analyzeBtn = document.getElementById('analyze-button') as HTMLButtonElement | null;
  if (analyzeBtn) analyzeBtn.disabled = true;
}

// ---------------------------------------------------------------------------
// Cleanup
// ---------------------------------------------------------------------------

/** Clear all analysis results and drawn shapes. */
export function clearAnalysisResults(): void {
  cancelAreaAnalysis();
  clearResultMarkers();
  setAnalysisResults([]);
  if (resultsPanel) {
    resultsPanel.style.display = 'none';
    resultsPanel.innerHTML = '';
  }
}

/** Remove drawn items and reset analysis state. */
export function clearAll(): void {
  stopDrawing();
  if (drawnItems) drawnItems.clearLayers();
  setCurrentPolygon(null);
  clearAnalysisResults();
  const analyzeBtn = document.getElementById('analyze-button') as HTMLButtonElement | null;
  if (analyzeBtn) analyzeBtn.disabled = true;
  const clear = document.getElementById('clear-button') as HTMLButtonElement | null;
  if (clear) clear.disabled = true;
  setDrawing(false);
}
