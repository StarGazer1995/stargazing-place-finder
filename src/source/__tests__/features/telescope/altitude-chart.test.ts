import { describe, it, expect } from 'vitest';
import {
  computeChartLayout,
  scaleAltitudeToPixel,
  formatTimeLabel,
} from '../../../js/features/telescope/altitude-chart';

describe('computeChartLayout', () => {
  it('returns correct padding and plot dimensions', () => {
    const layout = computeChartLayout(300, 150);
    expect(layout.pad).toEqual({ top: 15, right: 10, bottom: 25, left: 40 });
    expect(layout.pw).toBe(250); // 300 - 40 - 10
    expect(layout.ph).toBe(110); // 150 - 15 - 25
  });

  it('handles very small dimensions', () => {
    const layout = computeChartLayout(70, 50);
    expect(layout.pw).toBe(20); // 70 - 40 - 10
    expect(layout.ph).toBe(10); // 50 - 15 - 25
  });

  it('handles zero-size canvas gracefully', () => {
    const layout = computeChartLayout(50, 40);
    expect(layout.pw).toBe(0);  // 50 - 40 - 10
    expect(layout.ph).toBe(0);  // 40 - 15 - 25
  });
});

describe('scaleAltitudeToPixel', () => {
  const ph = 100;
  const padTop = 15;

  it('maps altitude 90° to the top of the plot area', () => {
    const y = scaleAltitudeToPixel(90, ph, padTop);
    expect(y).toBeCloseTo(padTop); // top of plot
  });

  it('maps altitude 0° to the bottom of the plot area', () => {
    const y = scaleAltitudeToPixel(0, ph, padTop);
    expect(y).toBeCloseTo(padTop + ph); // bottom of plot
  });

  it('maps altitude 45° to the middle', () => {
    const y = scaleAltitudeToPixel(45, ph, padTop);
    expect(y).toBeCloseTo(padTop + ph / 2);
  });

  it('handles altitude above 90° gracefully', () => {
    const y = scaleAltitudeToPixel(100, ph, padTop);
    expect(y).toBeLessThan(padTop); // above the plot
  });

  it('handles altitude below 0° gracefully', () => {
    const y = scaleAltitudeToPixel(-10, ph, padTop);
    expect(y).toBeGreaterThan(padTop + ph); // below the plot
  });
});

describe('formatTimeLabel', () => {
  it('formats whole hours', () => {
    expect(formatTimeLabel(0)).toBe('0:00');
    expect(formatTimeLabel(60)).toBe('1:00');
    expect(formatTimeLabel(120)).toBe('2:00');
    expect(formatTimeLabel(180)).toBe('3:00');
  });

  it('formats fractional minutes with zero-padding', () => {
    expect(formatTimeLabel(5)).toBe('0:05');
    expect(formatTimeLabel(65)).toBe('1:05');
    expect(formatTimeLabel(125)).toBe('2:05');
  });

  it('handles large values', () => {
    expect(formatTimeLabel(600)).toBe('10:00');
    expect(formatTimeLabel(1439)).toBe('23:59');
  });
});
