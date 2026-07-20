import { describe, it, expect } from 'vitest';
import {
  TELESCOPE_PRESETS,
  calculateFov,
} from '../../../js/features/telescope/aladin-core';

describe('calculateFov', () => {
  it('computes FOV for a typical APS-C setup', () => {
    const { fovW, fovH } = calculateFov(250, 23.5, 15.7);
    // 2 * atan(23.5 / 500) * 180/π ≈ 5.38°
    // 2 * atan(15.7 / 500) * 180/π ≈ 3.60°
    expect(fovW).toBeCloseTo(5.38, 1);
    expect(fovH).toBeCloseTo(3.60, 1);
  });

  it('computes FOV for a full-frame setup', () => {
    const { fovW, fovH } = calculateFov(200, 36, 24);
    expect(fovW).toBeCloseTo(10.28, 1);
    expect(fovH).toBeCloseTo(6.86, 1);
  });

  it('computes FOV for Seestar S50', () => {
    const { fovW, fovH } = calculateFov(250, 7.6, 5.7);
    expect(fovW).toBeCloseTo(1.74, 1);
    expect(fovH).toBeCloseTo(1.31, 1);
  });

  it('returns larger FOV for shorter focal length (same sensor)', () => {
    const short = calculateFov(85, 36, 24);
    const long = calculateFov(500, 36, 24);
    expect(short.fovW).toBeGreaterThan(long.fovW);
    expect(short.fovH).toBeGreaterThan(long.fovH);
  });

  it('returns larger FOV for larger sensor (same focal length)', () => {
    const small = calculateFov(250, 7.6, 5.7);
    const large = calculateFov(250, 36, 24);
    expect(large.fovW).toBeGreaterThan(small.fovW);
    expect(large.fovH).toBeGreaterThan(small.fovH);
  });

  it('handles extreme focal lengths', () => {
    const wide = calculateFov(10, 36, 24);
    expect(wide.fovW).toBeGreaterThan(90); // nearly 180° FOV
  });
});

describe('TELESCOPE_PRESETS', () => {
  it('has at least 4 presets', () => {
    expect(Object.keys(TELESCOPE_PRESETS)).toHaveLength(5);
  });

  it('has a "custom" preset with no optical params', () => {
    const custom = TELESCOPE_PRESETS.custom;
    expect(custom).toBeDefined();
    expect(custom!.name).toBe('自定义');
    expect(custom!.focalLength).toBeUndefined();
  });

  it('Seestar S50 preset has correct specs', () => {
    const s50 = TELESCOPE_PRESETS['seestar-s50'];
    expect(s50).toBeDefined();
    expect(s50!.focalLength).toBe(250);
    expect(s50!.sensorWidth).toBe(7.6);
    expect(s50!.sensorHeight).toBe(5.7);
  });

  it('RedCat51 preset has correct specs', () => {
    const rc = TELESCOPE_PRESETS['redcat51-asi2600'];
    expect(rc).toBeDefined();
    expect(rc!.focalLength).toBe(250);
    expect(rc!.sensorWidth).toBe(23.5);
    expect(rc!.sensorHeight).toBe(15.7);
  });

  it('all presets have a name', () => {
    Object.values(TELESCOPE_PRESETS).forEach((p) => {
      expect(p!.name).toBeTruthy();
    });
  });
});
