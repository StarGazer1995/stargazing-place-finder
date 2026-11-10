import { describe, it, expect } from 'vitest';
import {
  SKY_SURVEY_URL,
  TELESCOPE_PRESETS,
  calculateFov,
} from '../../../js/features/telescope/aladin-core';

describe('sky survey configuration', () => {
  it('uses the reachable ESA DSS mirror instead of the blocked CDS default', () => {
    const survey = new URL(SKY_SURVEY_URL);
    expect(survey.protocol).toBe('https:');
    expect(survey.hostname).toBe('skies.esac.esa.int');
    expect(survey.pathname).toBe('/DSSColor');
  });
});

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
  it('starts with custom optics until backend presets load', () => {
    expect(TELESCOPE_PRESETS.custom).toEqual({ name: '自定义' });
  });
});
