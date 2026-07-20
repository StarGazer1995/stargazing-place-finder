import { describe, it, expect } from 'vitest';
import { estimateBortleClass } from '../../js/utils/geo';

describe('estimateBortleClass', () => {
  it('returns 7 for eastern China (e.g. Beijing, Shanghai)', () => {
    expect(estimateBortleClass(39.9, 116.4)).toBe(7); // Beijing
    expect(estimateBortleClass(31.2, 121.5)).toBe(7); // Shanghai
  });

  it('returns 2 for western China (e.g. Xinjiang, Tibet)', () => {
    expect(estimateBortleClass(43.8, 87.6)).toBe(2);  // Ürümqi
    expect(estimateBortleClass(38.0, 80.0)).toBe(2);  // Western Xinjiang
  });

  it('returns 5 for other Chinese regions', () => {
    expect(estimateBortleClass(23.1, 113.3)).toBe(5); // Guangzhou (south, outside eastern band)
    expect(estimateBortleClass(45.8, 126.5)).toBe(5); // Harbin (north of eastern band)
  });

  it('returns 4 for locations outside China', () => {
    expect(estimateBortleClass(48.8, 2.3)).toBe(4);   // Paris
    expect(estimateBortleClass(40.7, -74.0)).toBe(4); // New York
    expect(estimateBortleClass(-33.9, 151.2)).toBe(4); // Sydney
  });

  it('returns 4 for boundary cases just outside China', () => {
    expect(estimateBortleClass(17.0, 73.0)).toBe(4);  // below latitude range
    expect(estimateBortleClass(55.0, 73.0)).toBe(4);  // above latitude range
    expect(estimateBortleClass(35.0, 72.0)).toBe(4);  // west of longitude range
    expect(estimateBortleClass(35.0, 136.0)).toBe(4); // east of longitude range
  });
});
