// =============================================================================
// Geo — geographic heuristics (pure functions, zero dependencies)
// =============================================================================

/**
 * Coarse geographic heuristic to estimate the Bortle class at a given
 * latitude / longitude when no actual measurement is available.
 *
 * Currently models rough light-pollution zones within mainland China;
 * returns a conservative default for coordinates outside that region.
 */
export function estimateBortleClass(lat: number, lng: number): number {
  // Mainland China rough bounding box
  if (lat >= 18 && lat <= 54 && lng >= 73 && lng <= 135) {
    if (lng >= 110 && lng <= 125 && lat >= 30 && lat <= 42) return 7; // Eastern developed
    if (lng >= 75 && lng <= 95 && lat >= 35 && lat <= 50) return 2;   // Western remote
    return 5; // Other Chinese regions
  }
  return 4; // Outside China — conservative default
}
