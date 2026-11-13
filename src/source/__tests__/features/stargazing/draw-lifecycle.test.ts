import L from 'leaflet';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { initializeDrawControls, startDrawing, stopDrawing, shouldIgnoreMapClick, clearAll } from '../../../js/features/stargazing/draw';
import { cancelAreaAnalysis } from '../../../js/features/stargazing/analyzer';
import { clearResultMarkers, displayAnalysisResults } from '../../../js/features/stargazing/results';
import { invalidateTargetRequests } from '../../../js/features/telescope/targets';
import { setMap, setCurrentPolygon, setLastMatchBody } from '../../../js/state';

let map: L.Map;
beforeEach(() => {
  document.body.innerHTML = `<div id="map"></div><button id="cancel-draw-button" hidden></button>
    <span id="selection-status"></span><button id="analyze-button"></button><button id="cancel-analysis-button"></button>
    <div id="status-indicator"></div><button id="match-targets-btn" disabled></button>
    <button id="plan-btn" disabled></button><div id="plan-panel"></div><div id="target-results-section"></div><div id="results-panel" class="results-panel"></div>`;
  const el = document.getElementById('map')!;
  Object.defineProperty(el, 'clientWidth', { value: 800 });
  Object.defineProperty(el, 'clientHeight', { value: 600 });
  map = L.map(el, { zoomControl: false }).setView([30, 120], 8);
  setMap(map); setCurrentPolygon(null); setLastMatchBody(null);
  initializeDrawControls();
});
afterEach(() => { stopDrawing(); clearAll(); map.remove(); vi.useRealTimers(); });

it('starts and stops real Leaflet drawing and briefly suppresses its trailing click', () => {
  vi.useFakeTimers();
  startDrawing();
  expect(document.body.classList.contains('drawing-area')).toBe(true);
  expect(shouldIgnoreMapClick()).toBe(true);
  expect(document.getElementById('cancel-draw-button')!.hidden).toBe(false);
  stopDrawing();
  expect(document.body.classList.contains('drawing-area')).toBe(false);
  expect(shouldIgnoreMapClick()).toBe(true);
  vi.advanceTimersByTime(351);
  expect(shouldIgnoreMapClick()).toBe(false);
  setCurrentPolygon({ layer: {} as any, coordinates: [], bbox: { south: 0, west: 0, north: 1, east: 1 } });
  stopDrawing();
  expect(document.getElementById('selection-status')!.textContent).toContain('已选好');
  cancelAreaAnalysis(true);
  expect(document.getElementById('status-indicator')!.textContent).toContain('已停止等待');
});

it('clears separate result markers and resets pending UI requests', () => {
  displayAnalysisResults({ locations: [{ lat: 30, lng: 120, name: '测试地点', score: 80, bortleClass: 3, sqm: 21 }] });
  clearResultMarkers(); clearResultMarkers();
  invalidateTargetRequests();
  expect(document.getElementById('target-results-section')!.style.display).toBe('none');
  expect(document.getElementById('plan-panel')!.style.display).toBe('none');
  setLastMatchBody({ time: '2026-11-12' });
  invalidateTargetRequests();
  expect((document.getElementById('match-targets-btn') as HTMLButtonElement).disabled).toBe(false);
  document.getElementById('selection-status')!.remove(); stopDrawing();
  document.getElementById('cancel-draw-button')!.remove(); stopDrawing();
  document.getElementById('analyze-button')!.remove();
  document.getElementById('cancel-analysis-button')!.remove(); cancelAreaAnalysis();
  document.getElementById('plan-btn')!.remove();
  document.getElementById('match-targets-btn')!.remove(); invalidateTargetRequests();
});
