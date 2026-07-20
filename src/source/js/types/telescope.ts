// =============================================================================
// Telescope / astrophotography domain types
// =============================================================================

/** Telescope + camera preset definition. */
export interface TelescopePreset {
  name: string;
  focalLength?: number;
  sensorWidth?: number;
  sensorHeight?: number;
}

/** A matched astrophotography target returned by the backend. */
export interface TelescopeTarget {
  name: string;
  ra: number;
  dec: number;
  angular_size_arcmin: number;
  angular_size_min_arcmin?: number;
  suitability_score: number;
  fov_fit_score: number;
  filter_match_score: number;
  altitude_curve?: AltitudeCurvePoint[];
  surface_brightness?: number;
  type?: string;
  magnitude?: number;
}

/** Single point on an altitude-vs-time curve. */
export interface AltitudeCurvePoint {
  time: string;
  altitude: number;
}

/** Moon illumination data. */
export interface MoonData {
  phase: string;
  illumination: number;
  separation?: number;
  age_days?: number;
}

/** A single panel in a mosaic FOV grid. */
export interface MosaicPanel {
  row: number;
  col: number;
  ra_center: number;
  dec_center: number;
  corners: Array<[number, number]>;
}

/** Mosaic FOV grid returned by the backend. */
export interface MosaicGrid {
  rows: number;
  cols: number;
  total_panels: number;
  overlap: number;
  fov_width_deg: number;
  fov_height_deg: number;
  panels: MosaicPanel[];
}

/** A single slot in an optimized shooting schedule. */
export interface PlanSlot {
  start_time: string;
  end_time: string;
  target_name: string;
  exposure_count?: number;
  altitude_start?: number;
  altitude_end?: number;
}

/** Single-night shooting plan. */
export interface ShootingPlan {
  date: string;
  slots: PlanSlot[];
  total_exposure_min?: number;
}

/** Marker style configuration for a stargazing quality tier. */
export interface MarkerStyle {
  className: string;
  iconSize: [number, number];
  iconAnchor: [number, number];
}
