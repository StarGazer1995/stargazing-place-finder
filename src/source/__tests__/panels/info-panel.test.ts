import { describe, it, expect, beforeEach } from 'vitest';
import { createPopupContent, createDetailedPopupContent, getSuitabilityLevel } from '../../js/panels/info-panel';
import { setCurrentLanguage } from '../../js/state';

describe('getSuitabilityLevel', () => {
  it('returns excellent for Bortle 1-2', () => {
    expect(getSuitabilityLevel(1)).toBe('excellent');
    expect(getSuitabilityLevel(2)).toBe('excellent');
  });

  it('returns good for Bortle 3-4', () => {
    expect(getSuitabilityLevel(3)).toBe('good');
    expect(getSuitabilityLevel(4)).toBe('good');
  });

  it('returns fair for Bortle 5-6', () => {
    expect(getSuitabilityLevel(5)).toBe('fair');
    expect(getSuitabilityLevel(6)).toBe('fair');
  });

  it('returns poor for Bortle 7', () => {
    expect(getSuitabilityLevel(7)).toBe('poor');
  });

  it('returns verypoor for Bortle 8-9+', () => {
    expect(getSuitabilityLevel(8)).toBe('verypoor');
    expect(getSuitabilityLevel(9)).toBe('verypoor');
    expect(getSuitabilityLevel(10)).toBe('verypoor');
  });
});

describe('createPopupContent', () => {
  beforeEach(() => {
    setCurrentLanguage('zh');
  });

  it('returns an HTML string containing coordinates', () => {
    const html = createPopupContent(39.9042, 116.4074, 3);
    expect(html).toContain('39.9042');
    expect(html).toContain('116.4074');
  });

  it('returns an HTML string containing Bortle class description', () => {
    const html = createPopupContent(35, 115, 4);
    expect(html).toContain('波特尔等级');
    expect(html).toContain('4级');
  });

  it('includes the shoot-here button with data-action attribute', () => {
    const html = createPopupContent(30, 120, 2);
    expect(html).toContain('data-action="jump-telescope"');
    expect(html).toContain('🔭');
  });

  it('includes observation tips for known Bortle classes', () => {
    const html = createPopupContent(35, 115, 1);
    expect(html).toContain('observation-tips');
    expect(html).toContain('银河清晰可见');
  });
});

describe('createDetailedPopupContent', () => {
  beforeEach(() => {
    setCurrentLanguage('zh');
  });

  const mockApiData = {
    light_pollution: {
      bortle_class: 3,
      sqm_value: 21.5,
      intensity: 0.3,
      description: '乡村天空',
    },
  };

  it('returns an HTML string with SQM and intensity', () => {
    const html = createDetailedPopupContent(39.9, 116.4, mockApiData);
    expect(html).toContain('21.5');
    expect(html).toContain('30.0%'); // 0.3 * 100
    expect(html).toContain('乡村天空');
  });

  it('includes the shoot-here data-action button', () => {
    const html = createDetailedPopupContent(30, 120, mockApiData);
    expect(html).toContain('data-action="jump-telescope"');
  });

  it('contains coordinates in the output', () => {
    const html = createDetailedPopupContent(31.23, 121.47, mockApiData);
    expect(html).toContain('31.2300');
    expect(html).toContain('121.4700');
  });
});
