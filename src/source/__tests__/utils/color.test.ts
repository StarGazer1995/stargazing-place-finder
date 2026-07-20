import { describe, it, expect } from 'vitest';
import { getBortleColor, getIntensityRadius, BORTLE_COLORS } from '../../js/utils/color';

describe('getBortleColor', () => {
  it('returns the correct color for each Bortle class 1–9', () => {
    expect(getBortleColor(1)).toBe('#000000');
    expect(getBortleColor(2)).toBe('#1a1a1a');
    expect(getBortleColor(3)).toBe('#2d2d2d');
    expect(getBortleColor(4)).toBe('#4a4a00');
    expect(getBortleColor(5)).toBe('#666600');
    expect(getBortleColor(6)).toBe('#cc6600');
    expect(getBortleColor(7)).toBe('#cc3300');
    expect(getBortleColor(8)).toBe('#ff0066');
    expect(getBortleColor(9)).toBe('#ff00ff');
  });

  it('returns #888888 for out-of-range values', () => {
    expect(getBortleColor(0)).toBe('#888888');
    expect(getBortleColor(10)).toBe('#888888');
    expect(getBortleColor(-1)).toBe('#888888');
    expect(getBortleColor(999)).toBe('#888888');
  });

  it('returns #888888 for NaN and non-integer edge cases', () => {
    expect(getBortleColor(NaN)).toBe('#888888');
    expect(getBortleColor(3.7)).toBe('#888888'); // only integer keys
  });
});

describe('getIntensityRadius', () => {
  it('scales linearly with Bortle class', () => {
    expect(getIntensityRadius(3)).toBeCloseTo(0.5);
    expect(getIntensityRadius(6)).toBeCloseTo(1.0);
    expect(getIntensityRadius(9)).toBeCloseTo(1.5);
  });

  it('returns 0 for Bortle class 0', () => {
    expect(getIntensityRadius(0)).toBe(0);
  });
});

describe('BORTLE_COLORS', () => {
  it('has exactly 9 entries', () => {
    expect(Object.keys(BORTLE_COLORS)).toHaveLength(9);
  });

  it('all values are valid hex color strings', () => {
    Object.values(BORTLE_COLORS).forEach((color) => {
      expect(color).toMatch(/^#[0-9a-fA-F]{6}$/);
    });
  });
});
