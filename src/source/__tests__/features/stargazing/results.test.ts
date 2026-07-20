import { describe, it, expect } from 'vitest';
import { calculateLocationStats, scoreClass } from '../../../js/features/stargazing/results';
import type { StargazingLocation } from '../../../js/types/stargazing';

function makeLoc(score: number, bortle: number = 4): StargazingLocation {
  return {
    lat: 35, lng: 115, bortleClass: bortle, sqm: 21.5,
    elevation_m: 500, score, name: `Loc-${score}`,
  };
}

describe('calculateLocationStats', () => {
  it('returns zeros for empty array', () => {
    expect(calculateLocationStats([])).toEqual({
      totalLocations: 0,
      avgScore: 0,
      excellentCount: 0,
      goodCount: 0,
      fairCount: 0,
      poorCount: 0,
      excellentPercentage: '0',
      goodPercentage: '0',
      fairPercentage: '0',
      poorPercentage: '0',
    });
  });

  it('classifies locations correctly by score tier', () => {
    const data = [
      makeLoc(90), // excellent (≥80)
      makeLoc(70), // good (60-79)
      makeLoc(50), // fair (40-59)
      makeLoc(30), // poor (<40)
    ];
    const stats = calculateLocationStats(data);
    expect(stats.totalLocations).toBe(4);
    expect(stats.excellentCount).toBe(1);
    expect(stats.goodCount).toBe(1);
    expect(stats.fairCount).toBe(1);
    expect(stats.poorCount).toBe(1);
  });

  it('calculates correct percentages', () => {
    const data = [
      makeLoc(85), makeLoc(85), // 2 excellent
      makeLoc(65), // 1 good
      makeLoc(35), // 1 poor
    ];
    const stats = calculateLocationStats(data);
    expect(stats.excellentPercentage).toBe('50.0');
    expect(stats.goodPercentage).toBe('25.0');
    expect(stats.fairPercentage).toBe('0.0');
    expect(stats.poorPercentage).toBe('25.0');
  });

  it('calculates average score correctly', () => {
    const data = [makeLoc(80), makeLoc(60), makeLoc(40), makeLoc(20)];
    const stats = calculateLocationStats(data);
    expect(stats.avgScore).toBe(50); // (80+60+40+20)/4 = 50
  });

  it('handles boundary scores', () => {
    const data = [
      makeLoc(80), // excellent boundary (≥80)
      makeLoc(79), // good (60-79)
      makeLoc(60), // good boundary (≥60)
      makeLoc(59), // fair (40-59)
      makeLoc(40), // fair boundary (≥40)
      makeLoc(39), // poor (<40)
    ];
    const stats = calculateLocationStats(data);
    expect(stats.excellentCount).toBe(1);
    expect(stats.goodCount).toBe(2);
    expect(stats.fairCount).toBe(2);
    expect(stats.poorCount).toBe(1);
  });

  it('rounds average score to integer', () => {
    const data = [makeLoc(85), makeLoc(82), makeLoc(79)];
    const stats = calculateLocationStats(data);
    expect(stats.avgScore).toBe(82); // Math.round((85+82+79)/3) = Math.round(82) = 82
  });
});

describe('scoreClass', () => {
  it('returns excellent for score >= 80', () => {
    expect(scoreClass(80)).toBe('excellent');
    expect(scoreClass(95)).toBe('excellent');
    expect(scoreClass(100)).toBe('excellent');
  });
  it('returns good for 60-79', () => {
    expect(scoreClass(60)).toBe('good');
    expect(scoreClass(70)).toBe('good');
    expect(scoreClass(79)).toBe('good');
  });
  it('returns fair for 40-59', () => {
    expect(scoreClass(40)).toBe('fair');
    expect(scoreClass(50)).toBe('fair');
    expect(scoreClass(59)).toBe('fair');
  });
  it('returns poor for < 40', () => {
    expect(scoreClass(39)).toBe('poor');
    expect(scoreClass(0)).toBe('poor');
    expect(scoreClass(-10)).toBe('poor');
  });
});
