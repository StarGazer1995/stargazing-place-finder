// =============================================================================
// API request / response types
// =============================================================================

import type { StargazingLocation } from './stargazing';
import type { TelescopeTarget, MoonData, ShootingPlan, MosaicGrid } from './telescope';

/** Geographic bounding box (WSG84). */
export interface GeoBounds {
  south: number;
  west: number;
  north: number;
  east: number;
}

/** Stargazing area analysis request body. */
export interface AnalysisRequest {
  bbox: GeoBounds;
  max_locations: number;
  network_type: string;
  include_light_pollution: boolean;
  include_road_connectivity: boolean;
  road_radius_km: number;
  max_distance_to_road_km: number;
}

/** Analysis response from /api/analyze_stargazing_area. */
export interface AnalysisResponse {
  locations?: StargazingLocation[];
  error?: string;
}

/** Light-pollution tile request params. */
export interface LightPollutionRequest {
  north: number;
  south: number;
  east: number;
  west: number;
  zoom: number;
}

/** Coordinate analysis response. */
export interface CoordinateAnalysisResponse {
  bortleClass: number;
  sqm: number;
  radiance?: number;
  lat: number;
  lng: number;
}

/** API configuration (matches window.APP_CONFIG or auto-resolved). */
export interface ApiConfig {
  baseUrl: string;
  endpoints: {
    analyze: string;
    health: string;
    lightPollution: string;
    lightPollutionTiles: string;
    coordinateAnalysis: string;
    telescopeTargets?: string;
    telescopePlan?: string;
    telescopeMosaic?: string;
    telescopePresets?: string;
  };
}

/** Telescope target matching request body. */
export interface TelescopeTargetRequest {
  focal_length_mm: number;
  sensor_width_mm: number;
  sensor_height_mm: number;
  lon: number;
  lat: number;
  time: string;
  time_zone: string;
  limit?: number;
}

/** Telescope target matching response. */
export interface TelescopeTargetResponse {
  targets?: TelescopeTarget[];
  moon?: MoonData;
  error?: string;
}

/** Shooting plan response. */
export interface ShootingPlanResponse {
  plan?: ShootingPlan;
  targets?: TelescopeTarget[];
  moon?: MoonData;
  error?: string;
}

/** Mosaic grid request body. */
export interface MosaicRequest {
  target: {
    name: string;
    ra: number;
    dec: number;
    angular_size_arcmin: number;
    angular_size_min_arcmin?: number;
  };
  config: TelescopeTargetRequest;
  overlap: number;
}

/** Mosaic grid response. */
export interface MosaicResponse {
  grid?: MosaicGrid;
  error?: string;
}
