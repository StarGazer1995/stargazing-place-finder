import { describe, it, expect } from 'vitest';
import { buildAnalysisRequest } from '../../../js/features/stargazing/analyzer';

// Minimal mock polygon (Leaflet-like getLatLngs)
function mockPolygon(latlngs: Array<{ lat: number; lng: number }>) {
  return {
    getLatLngs: () => [latlngs],
  };
}

describe('buildAnalysisRequest', () => {
  it('builds a correct bbox from polygon coordinates', () => {
    const poly = mockPolygon([
      { lat: 30, lng: 110 },
      { lat: 40, lng: 110 },
      { lat: 40, lng: 120 },
      { lat: 30, lng: 120 },
    ]);

    const req = buildAnalysisRequest(poly, 50, 'drive', true, true);

    expect(req.bbox).toEqual({ south: 30, west: 110, north: 40, east: 120 });
  });

  it('passes max_locations through correctly', () => {
    const poly = mockPolygon([
      { lat: 30, lng: 110 },
      { lat: 31, lng: 111 },
    ]);

    expect(buildAnalysisRequest(poly, 30, 'drive', true, true).max_locations).toBe(30);
    expect(buildAnalysisRequest(poly, 100, 'walk', false, false).max_locations).toBe(100);
    expect(buildAnalysisRequest(poly, 1, 'drive', true, false).max_locations).toBe(1);
  });

  it('passes network_type through', () => {
    const poly = mockPolygon([{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }]);

    expect(buildAnalysisRequest(poly, 30, 'drive', true, true).network_type).toBe('drive');
    expect(buildAnalysisRequest(poly, 30, 'walk', true, true).network_type).toBe('walk');
    expect(buildAnalysisRequest(poly, 30, 'bike', true, true).network_type).toBe('bike');
  });

  it('passes boolean flags through', () => {
    const poly = mockPolygon([{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }]);

    const withBoth = buildAnalysisRequest(poly, 30, 'drive', true, true);
    expect(withBoth.include_light_pollution).toBe(true);
    expect(withBoth.include_road_connectivity).toBe(true);

    const withNeither = buildAnalysisRequest(poly, 30, 'drive', false, false);
    expect(withNeither.include_light_pollution).toBe(false);
    expect(withNeither.include_road_connectivity).toBe(false);
  });

  it('always sets fixed road_radius_km and max_distance_to_road_km', () => {
    const poly = mockPolygon([{ lat: 1, lng: 2 }, { lat: 3, lng: 4 }]);
    const req = buildAnalysisRequest(poly, 30, 'drive', true, true);
    expect(req.road_radius_km).toBe(10.0);
    expect(req.max_distance_to_road_km).toBe(0.2);
  });

  it('handles a single-point polygon (degenerate)', () => {
    const poly = mockPolygon([{ lat: 35, lng: 115 }]);
    const req = buildAnalysisRequest(poly, 10, 'drive', false, false);

    // Single point → south=north, west=east
    expect(req.bbox.south).toBe(35);
    expect(req.bbox.north).toBe(35);
    expect(req.bbox.west).toBe(115);
    expect(req.bbox.east).toBe(115);
  });
});
