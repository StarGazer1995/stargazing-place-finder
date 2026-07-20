import { describe, it, expect, beforeEach } from 'vitest';
import { renderTargetResults, renderMoonCard } from '../../../js/features/telescope/target-renderer';
import type { TelescopeTarget, MoonData } from '../../../js/types/telescope';

function makeTarget(
  name: string,
  score: number,
  fov: number = 0.8,
  overrides: Partial<TelescopeTarget> = {},
): TelescopeTarget {
  return {
    name, ra: 10, dec: 40, angular_size_arcmin: 30,
    suitability_score: score, fov_fit_score: fov, filter_match_score: 0.7,
    ...overrides,
  };
}

describe('renderTargetResults', () => {
  it('renders empty message when no targets', () => {
    const container = document.createElement('div');
    renderTargetResults([], container);
    expect(container.innerHTML).toContain('未找到匹配目标');
  });

  it('renders target cards with rank numbers', () => {
    const container = document.createElement('div');
    const targets = [makeTarget('M31', 85), makeTarget('M42', 75)];
    renderTargetResults(targets, container);

    expect(container.innerHTML).toContain('#1');
    expect(container.innerHTML).toContain('#2');
    expect(container.innerHTML).toContain('M31');
    expect(container.innerHTML).toContain('M42');
  });

  it('renders suitability scores', () => {
    const container = document.createElement('div');
    renderTargetResults([makeTarget('M31', 85)], container);
    expect(container.innerHTML).toContain('85');
  });

  it('renders FOV fit percentages', () => {
    const container = document.createElement('div');
    renderTargetResults([makeTarget('M31', 85, 0.75)], container);
    expect(container.innerHTML).toContain('75%');
  });

  it('renders surface brightness when present', () => {
    const container = document.createElement('div');
    renderTargetResults([makeTarget('M31', 85, 0.8, { surface_brightness: 13.5 })], container);
    expect(container.innerHTML).toContain('🌌');
    expect(container.innerHTML).toContain('13.5');
  });

  it('does not render surface brightness when absent', () => {
    const container = document.createElement('div');
    renderTargetResults([makeTarget('M31', 85)], container);
    expect(container.innerHTML).not.toContain('🌌');
  });

  it('renders optimal rotation when present', () => {
    const container = document.createElement('div');
    renderTargetResults([makeTarget('M31', 85, 0.8, { optimal_rotation_deg: 121 })], container);
    expect(container.innerHTML).toContain('🔄');
    expect(container.innerHTML).toContain('121°');
  });

  it('does not render rotation when absent', () => {
    const container = document.createElement('div');
    renderTargetResults([makeTarget('M31', 85)], container);
    expect(container.innerHTML).not.toContain('🔄');
  });
});

describe('renderMoonCard', () => {
  it('renders moon phase and illumination', () => {
    const el = document.createElement('div');
    el.id = 'moon-card';
    document.body.appendChild(el);

    const moon: MoonData = { phase: 'Full Moon', illumination: 0.98 };
    renderMoonCard(moon);

    expect(el.style.display).toBe('block');
    expect(el.innerHTML).toContain('Full Moon');
    expect(el.innerHTML).toContain('98%');

    document.body.removeChild(el);
  });

  it('hides the card when moon is null', () => {
    const el = document.createElement('div');
    el.id = 'moon-card';
    el.style.display = 'block';
    document.body.appendChild(el);

    renderMoonCard(null);
    expect(el.style.display).toBe('none');

    document.body.removeChild(el);
  });
});
