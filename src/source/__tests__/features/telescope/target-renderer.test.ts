import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  bindTargetInteractions,
  formatPlanTime,
  renderMoonCard,
  renderShootingPlan,
  renderTargetResults,
} from '../../../js/features/telescope/target-renderer';
import { setAladinInstance, setLastTargets } from '../../../js/state';
import type { TelescopeTarget, MoonData, ShootingPlan } from '../../../js/types/telescope';

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

  it('marks large targets as mosaic candidates', () => {
    const container = document.createElement('div');
    renderTargetResults([makeTarget('M31', 85, 0.8, { mosaic_recommended: true })], container);
    expect(container.innerHTML).toContain('🧩');
  });
});

describe('bindTargetInteractions', () => {
  beforeEach(() => {
    setLastTargets([]);
    setAladinInstance(null);
  });

  it('navigates to the selected target and opens mosaic for recommended targets', () => {
    const target = makeTarget('M31', 85, 0.8, { mosaic_recommended: true });
    const gotoRaDec = vi.fn();
    const showAltitude = vi.fn();
    const fetchMosaic = vi.fn().mockResolvedValue(undefined);
    const container = document.createElement('div');
    container.innerHTML = '<div data-target-name="M31"><span>select</span></div>';

    setLastTargets([target]);
    setAladinInstance({ gotoRaDec });
    bindTargetInteractions(container, { showAltitude, fetchMosaic });
    container.querySelector('span')?.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    expect(gotoRaDec).toHaveBeenCalledWith(target.ra, target.dec);
    expect(showAltitude).toHaveBeenCalledWith(target);
    expect(fetchMosaic).toHaveBeenCalledWith(target);
  });

  it('does not request a mosaic for ordinary targets', () => {
    const target = makeTarget('M42', 75);
    const showAltitude = vi.fn();
    const fetchMosaic = vi.fn().mockResolvedValue(undefined);
    const container = document.createElement('div');
    container.innerHTML = '<div data-target-name="M42">select</div>';

    setLastTargets([target]);
    bindTargetInteractions(container, { showAltitude, fetchMosaic });
    container.querySelector('div')?.click();

    expect(showAltitude).toHaveBeenCalledWith(target);
    expect(fetchMosaic).not.toHaveBeenCalled();
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

describe('renderShootingPlan', () => {
  const plan: ShootingPlan = {
    date: '2026-11-05',
    dusk: '2026-11-05T09:39:00.000',
    dawn: '2026-11-05T22:21:00.000',
    moon_phase: 'Waning Crescent',
    moon_illumination: 0.13,
    moon_delay_min: 0,
    slots: [{
      start_time: '2026-11-05T11:18:00+00:00',
      end_time: '2026-11-05T13:16:00+00:00',
      target_name: 'M 31',
      target_type: 'Gx',
      start_alt: 25.1,
      end_alt: 47.1,
      duration_min: 118,
      fov_fit_score: 1,
      suitability_score: 88,
      mosaic_recommended: true,
      notes: [],
    }],
    total_dark_min: 762,
    used_min: 652,
    warnings: ['110 min of dark time unallocated'],
  };

  it('renders backend start_alt/end_alt and dark-time totals', () => {
    const container = document.createElement('div');
    renderShootingPlan(plan, [makeTarget('M 31', 88)], container);

    expect(container.textContent).toContain('25°→47°');
    expect(container.textContent).toContain('652 / 762');
    expect(container.textContent).toContain('13%');
    expect(container.textContent).toContain('110 min of dark time unallocated');
  });

  it('renders an empty state when the backend returns no slots', () => {
    const container = document.createElement('div');
    renderShootingPlan({ ...plan, slots: [] }, [], container);
    expect(container.textContent).toContain('无可用拍摄计划');
  });
});


describe('plan wall times', () => {
  it('uses the observer timezone and makes the day rollover visible', () => {
    expect(formatPlanTime('2026-11-12T17:30:00+00:00', 'Asia/Shanghai')).toBe('11-13 01:30');
    expect(formatPlanTime('2026-11-12T17:30:00+00:00')).toBe('11-12 17:30');
    expect(formatPlanTime('unknown')).toBe('时间未核实');
  });
});
