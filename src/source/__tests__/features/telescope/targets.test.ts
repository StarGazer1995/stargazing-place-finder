import { describe, it, expect } from 'vitest';
import { buildTargetRequest, buildTimeString } from '../../../js/features/telescope/targets';

describe('buildTargetRequest', () => {
  it('builds a request with all optical and location parameters', () => {
    const req = buildTargetRequest(250, 23.5, 15.7, 39.9, 116.4, 'Asia/Shanghai', '2026-07-19 20:00:00', 100);

    expect(req.focal_length_mm).toBe(250);
    expect(req.sensor_width_mm).toBe(23.5);
    expect(req.sensor_height_mm).toBe(15.7);
    expect(req.lon).toBe(116.4);
    expect(req.lat).toBe(39.9);
    expect(req.time).toBe('2026-07-19 20:00:00');
    expect(req.time_zone).toBe('Asia/Shanghai');
    expect(req.limit).toBe(100);
  });

  it('defaults limit to 100', () => {
    const req = buildTargetRequest(85, 36, 24, 40, 116, 'UTC', '2026-01-01 00:00:00');
    expect(req.limit).toBe(100);
  });

  it('allows overriding the limit', () => {
    const req = buildTargetRequest(200, 23.5, 15.7, 35, 115, 'UTC', '2026-01-01 00:00:00', 50);
    expect(req.limit).toBe(50);
  });

  it('handles UTC timezone', () => {
    const req = buildTargetRequest(250, 23.5, 15.7, 0, 0, 'UTC', '2026-06-15 12:00:00');
    expect(req.time_zone).toBe('UTC');
    expect(req.lat).toBe(0);
    expect(req.lon).toBe(0);
  });

  it('handles southern hemisphere coordinates', () => {
    const req = buildTargetRequest(250, 23.5, 15.7, -33.9, 151.2, 'Australia/Sydney', '2026-01-01 22:00:00');
    expect(req.lat).toBe(-33.9);
    expect(req.lon).toBe(151.2);
  });
});

describe('buildTimeString', () => {
  it('returns a formatted datetime string', () => {
    const result = buildTimeString();
    // Format: YYYY-MM-DD HH:mm:ss
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
  });
});
