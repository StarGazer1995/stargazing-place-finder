// =============================================================================
// Color — Bortle scale color mapping (pure functions, zero dependencies)
// =============================================================================

/** Bortle class → display color mapping. */
export const BORTLE_COLORS: Record<number, string> = {
  1: '#000000', // Excellent dark sky
  2: '#1a1a1a', // Typical dark sky
  3: '#2d2d2d', // Rural sky
  4: '#4a4a00', // Rural/suburban transition
  5: '#666600', // Suburban sky
  6: '#cc6600', // Bright suburban
  7: '#cc3300', // Suburban/urban transition
  8: '#ff0066', // City sky
  9: '#ff00ff', // Inner-city sky
};

/** Map a Bortle class (1–9) to its display color. Falls back to grey for out-of-range values. */
export function getBortleColor(bortleClass: number): string {
  return BORTLE_COLORS[bortleClass] ?? '#888888';
}

/** Return an intensity radius that scales linearly with the Bortle class. */
export function getIntensityRadius(bortleClass: number): number {
  return 0.5 * (bortleClass / 3);
}
