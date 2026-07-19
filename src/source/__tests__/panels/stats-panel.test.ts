import { describe, it, expect } from 'vitest';
import { calculateStats } from '../../js/panels/stats-panel';
import type { LightPollutionPoint } from '../../js/types/stargazing';

function makePoint(bortleClass: number): LightPollutionPoint {
  return { lat: 35, lng: 115, bortleClass, intensity: 0.5 };
}

describe('calculateStats', () => {
  it('returns zeros for empty data', () => {
    expect(calculateStats([])).toEqual({
      darkSkyArea: 0,
      darkSkyPercentage: '0.0',
      bortleDistribution: {},
    });
  });

  it('returns zeros for null/undefined input', () => {
    // The function checks !data — null is falsy
    expect(calculateStats(null as any)).toEqual({
      darkSkyArea: 0,
      darkSkyPercentage: '0.0',
      bortleDistribution: {},
    });
  });

  it('counts dark-sky points (Bortle ≤ 3) correctly', () => {
    const data = [
      makePoint(1), makePoint(2), makePoint(3),
      makePoint(4), makePoint(5),
    ];
    const stats = calculateStats(data);
    expect(stats.darkSkyArea).toBe(3);
    expect(stats.darkSkyPercentage).toBe('60.0');
  });

  it('returns 100% when all points are dark sky', () => {
    const data = [makePoint(1), makePoint(2), makePoint(2)];
    const stats = calculateStats(data);
    expect(stats.darkSkyArea).toBe(3);
    expect(stats.darkSkyPercentage).toBe('100.0');
  });

  it('returns 0% when all points are bright sky', () => {
    const data = [makePoint(7), makePoint(8), makePoint(9)];
    const stats = calculateStats(data);
    expect(stats.darkSkyArea).toBe(0);
    expect(stats.darkSkyPercentage).toBe('0.0');
  });

  it('builds a correct Bortle distribution for all 9 classes', () => {
    // 2 of each class = 18 total
    const data: LightPollutionPoint[] = [];
    for (let i = 1; i <= 9; i++) {
      data.push(makePoint(i), makePoint(i));
    }

    const stats = calculateStats(data);
    expect(Object.keys(stats.bortleDistribution)).toHaveLength(9);

    for (let i = 1; i <= 9; i++) {
      const dist = stats.bortleDistribution[i];
      expect(dist).toBeDefined();
      expect(dist!.count).toBe(2);
      expect(dist!.percentage).toBe('11.1'); // 2/18 ≈ 11.1%
    }
  });

  it('returns zero-count entries for classes with no data', () => {
    const data = [makePoint(5), makePoint(5), makePoint(5)]; // only class 5
    const stats = calculateStats(data);

    expect(stats.bortleDistribution[5]!.count).toBe(3);
    expect(stats.bortleDistribution[1]!.count).toBe(0);
    expect(stats.bortleDistribution[9]!.count).toBe(0);
  });

  it('handles a single data point', () => {
    const data = [makePoint(3)];
    const stats = calculateStats(data);

    expect(stats.darkSkyArea).toBe(1);
    expect(stats.darkSkyPercentage).toBe('100.0');
    expect(stats.bortleDistribution[3]!.count).toBe(1);
    expect(stats.bortleDistribution[3]!.percentage).toBe('100.0');
  });
});
