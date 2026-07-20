// =============================================================================
// Stargazing / light-pollution domain types
// =============================================================================

import type { GeoBounds } from './api';

/** A single light-pollution data point from the map grid. */
export interface LightPollutionPoint {
  lat: number;
  lng: number;
  intensity: number;
  bortleClass: number;
  sqm?: number;
}

/** A scored stargazing location returned by the analysis pipeline. */
export interface StargazingLocation {
  lat: number;
  lng: number;
  name?: string;
  bortleClass: number;
  sqm: number;
  elevation_m: number;
  score: number;
  road_distance_km?: number;
  location_type?: string;
}

/** Statistical summary of a set of light-pollution data points. */
export interface StatsResult {
  darkSkyArea: number;
  darkSkyPercentage: string;
  bortleDistribution: Record<number, { count: number; percentage: string }>;
}

/** Statistical summary of analysis results. */
export interface LocationStats {
  totalLocations: number;
  avgScore: number;
  excellentCount: number;
  goodCount: number;
  fairCount: number;
  poorCount: number;
  excellentPercentage: string;
  goodPercentage: string;
  fairPercentage: string;
  poorPercentage: string;
}

/** Observation suitability classification. */
export type SuitabilityLevel = 'excellent' | 'good' | 'fair' | 'poor';

/** Application mode. */
export type AppMode = 'browse' | 'analysis' | 'telescope';

/** Polygon drawn by the user for area analysis. */
export interface DrawnPolygon {
  /** Leaflet polygon layer reference. */
  layer: any;
  /** Coordinates as [lng, lat][] pairs (GeoJSON order). */
  coordinates: Array<[number, number]>;
  /** Computed bounding box. */
  bbox: GeoBounds;
}
