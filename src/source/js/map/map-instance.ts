/* c8 ignore start — integration code: requires full browser environment */
// =============================================================================
// Map — Leaflet map instance creation
// =============================================================================

import L from 'leaflet';
import { map, pollutionTileLayer, setMap, setPollutionTileLayer } from '../state';
import { API_CONFIG } from '../core/api';
import { debounce } from '../utils/dom';
import { loadCurrentViewData } from './layers';
import { onMapClick } from '../panels/info-panel';

/**
 * Initialize the Leaflet map with OSM base tiles and the VIIRS light-pollution
 * tile layer.  Binds moveend/zoomend (debounced) and click events, then triggers
 * the initial data load.
 */
export function initializeMap(): void {
  console.log('Initializing map...');

  const instance = L.map('map', {
    center: [39.9042, 116.4074], // Beijing
    zoom: 8,
    zoomControl: false,
    attributionControl: false,
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18,
  }).addTo(instance);

  const tileLayer = L.tileLayer(
    `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.lightPollutionTiles}`,
    {
      maxZoom: 18,
      opacity: 0.75,
      attribution: 'VIIRS DNB 2025',
    },
  ).addTo(instance);

  setMap(instance);
  setPollutionTileLayer(tileLayer);

  instance.on('moveend zoomend', debounce(loadCurrentViewData, 300));
  instance.on('click', onMapClick);

  console.log('Starting initial light-pollution data load...');
  loadCurrentViewData();

  console.log('Map initialization complete');
}
/** Return the current map instance (throws if not yet initialized). */
export function getMap(): any {
  if (!map) throw new Error('Map not initialized — call initializeMap() first');
  return map;
}
/* c8 ignore stop */
