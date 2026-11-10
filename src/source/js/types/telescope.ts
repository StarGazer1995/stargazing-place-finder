// =============================================================================
// Telescope / astrophotography domain types
// =============================================================================

export type CameraType = 'unknown' | 'color' | 'mono';
export type TargetSort = 'imaging_time' | 'setting_soon' | 'fov' | 'heuristic';

/** Shared optics contract returned by /api/telescope/presets. */
export interface TelescopeConfig {
  focal_length_mm: number;
  camera_type?: CameraType;
  sensor_width_mm?: number | null;
  sensor_height_mm?: number | null;
  aperture_mm?: number | null;
  sensor_pixel_size_um?: number | null;
  central_obstruction_pct?: number;
  reducer_factor?: number;
  barlow_factor?: number;
  mount_type?: string;
  guiding_supported?: boolean;
  filter_type?: string | null;
}

/** Telescope + camera preset definition. */
export interface TelescopePreset {
  name: string;
  config?: TelescopeConfig;
  focalLength?: number;
  sensorWidth?: number;
  sensorHeight?: number;
}

/** A matched astrophotography target returned by the backend. */
export interface TelescopeTarget {
  name: string;
  visibility?: {
    total_minutes: number | null;
    longest_minutes: number | null;
    available_now: boolean | null;
    windows: Array<{start: number; end: number}>;
  };
  sho_advice?: {
    status: 'consider' | 'not_primary' | 'verify';
    label: string;
    reason: string;
    camera_note: string;
    basis: 'catalog_type_only';
    sii_strength: null;
  };
  ra: number;
  dec: number;
  angular_size_arcmin: number;
  angular_size_min_arcmin?: number;
  angular_size_pa_deg?: number;
  optimal_rotation_deg?: number;
  suitability_score: number;
  fov_fit_score: number;
  filter_match_score: number;
  altitude_curve?: AltitudeCurvePoint[];
  /** UTC unix timestamp when the target rises above the horizon (null if already up at dusk). */
  rise_time?: number | null;
  /** UTC unix timestamp when the target sets below the horizon (null if still up at dawn). */
  set_time?: number | null;
  /** UTC unix timestamp of culmination (highest altitude). */
  transit_time?: number | null;
  /** Altitude in degrees at culmination. */
  transit_alt?: number | null;
  surface_brightness?: number;
  surface_brightness_score?: number;
  type?: string;
  magnitude?: number;
  mosaic_recommended?: boolean;
}

/** Single point on an altitude-vs-time curve. */
export interface AltitudeCurvePoint {
  /** UTC unix timestamp in seconds. */
  time: number;
  /** Altitude above the horizon in degrees. */
  alt: number;
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
  target_type: string;
  start_alt: number;
  end_alt: number;
  duration_min: number;
  fov_fit_score: number;
  suitability_score: number;
  mosaic_recommended: boolean;
  notes: string[];
}

/** Single-night shooting plan. */
export interface ShootingPlan {
  date: string;
  dusk: string;
  dawn: string;
  moon_phase: string;
  moon_illumination: number;
  moon_delay_min: number;
  slots: PlanSlot[];
  total_dark_min: number;
  used_min: number;
  warnings: string[];
}

/** Marker style configuration for a stargazing quality tier. */
export interface MarkerStyle {
  className: string;
  iconSize: [number, number];
  iconAnchor: [number, number];
}
