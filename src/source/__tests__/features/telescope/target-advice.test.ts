import { describe, expect, it, vi } from 'vitest';
import { renderTargetResults, bindTargetInteractions } from '../../../js/features/telescope/target-renderer';
import { buildTargetRequest } from '../../../js/features/telescope/targets';
import { setLastTargets } from '../../../js/state';
import type { TelescopeTarget } from '../../../js/types/telescope';

const target: TelescopeTarget = {
  name: 'M 42', ra: 83.8, dec: -5.4, type: 'HII', angular_size_arcmin: 66,
  suitability_score: 80, fov_fit_score: 0.6, filter_match_score: 0.6,
  visibility: { total_minutes: 180, longest_minutes: 120, available_now: true,
    windows: [{start: 1700000000, end: 1700007200}] },
  sho_advice: {status: 'consider', label: 'SHO：可考虑，先核实 SII',
    reason: '发射星云可考虑窄带；SII 强度待核实。',
    camera_note: '彩色相机需要额外 SII 数据，单个 Hα/OIII 双窄带不等于完整 SHO。',
    basis: 'catalog_type_only', sii_strength: null},
};

describe('target explanations', () => {
  it('shows total versus continuous time and separates SHO advice from the reference score', () => {
    const container = document.createElement('div');
    renderTargetResults([target], container);
    expect(container.textContent).toContain('剩余 180 分钟 · 最长连续 120 分钟');
    expect(container.textContent).toContain('当前');
    expect(container.textContent).toContain('SHO：可考虑，先核实 SII');
    expect(container.textContent).toContain('额外 SII');
    expect(container.querySelector('.target-score')?.textContent).toContain('参考分');
    expect(container.querySelector('.target-sho-consider')).not.toBeNull();
  });

  it('keeps missing timing and SHO evidence unknown', () => {
    const container = document.createElement('div');
    renderTargetResults([{...target, visibility: undefined, sho_advice: undefined}], container);
    expect(container.textContent).toContain('可拍时段未核实');
    expect(container.textContent).toContain('SHO：资料不足，待核实');
    renderTargetResults([{...target, visibility: {total_minutes: 0, longest_minutes: 0, available_now: false, windows: []}}], container);
    expect(container.textContent).toContain('无剩余时段');
    renderTargetResults([{...target, visibility: {...target.visibility!, available_now: false}}], container);
    expect(container.textContent).toContain('下个');
  });

  it('escapes advice and target names; opening advice never slews or opens another panel', () => {
    const container = document.createElement('div');
    const value = {...target, name: '<img src=x onerror=alert(1)>',
      sho_advice: {...target.sho_advice!, reason: '<script>alert(1)</script>'}};
    renderTargetResults([value], container);
    expect(container.querySelector('img, script')).toBeNull();
    setLastTargets([value]);
    const showAltitude = vi.fn();
    bindTargetInteractions(container, {showAltitude});
    container.querySelector('summary')!.click();
    expect(showAltitude).not.toHaveBeenCalled();
  });

  it('passes sorting intent and explicit camera type independently of optical data', () => {
    const request = buildTargetRequest(280, 23.5, 15.7, 30, 120, 'UTC', '2026-11-10', 20,
      {focal_length_mm: 280, camera_type: 'color'}, 'setting_soon', 'mono');
    expect(request.sort_by).toBe('setting_soon');
    expect(request.camera_type).toBe('mono');
  });
});
