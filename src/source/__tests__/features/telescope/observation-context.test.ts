import { beforeEach, describe, expect, it, vi } from 'vitest';
import { initObservationContext, localTimeValue, readObservationContext, refreshObservationSummary, setObservationLocation, syncObserverFromMap } from '../../../js/features/telescope/observation-context';
import { setMap, setTelescopeTargetLocation, setCurrentLanguage } from '../../../js/state';

const input = (id: string) => document.getElementById(id) as HTMLInputElement;
const change = () => input('observation-lat').dispatchEvent(new Event('input'));
let center = {lat:31.23,lng:121.47};
let onChange: ReturnType<typeof vi.fn>;

beforeEach(() => {
  setCurrentLanguage('zh');
  setTelescopeTargetLocation(null);
  center = {lat:31.23,lng:121.47};
  setMap({getCenter:() => center});
  document.body.innerHTML = `<div id="telescope-location-display"></div><p id="observation-summary"></p>
    <details><input id="observation-lat" type="number" min="-90" max="90" step="any" required>
    <input id="observation-lng" type="number" min="-180" max="180" step="any" required>
    <input id="observation-time" type="datetime-local" required><input id="observation-timezone" required></details>
    <details><input id="telescope-focal-length" type="number" min="1" value="250">
    <input id="telescope-sensor-width" type="number" min="0.1" step="any" value="23.5">
    <input id="telescope-sensor-height" type="number" min="0.1" step="any" value="15.7"></details>
    <button id="use-map-center"></button><button id="use-current-time"></button>`;
  onChange = vi.fn();
  initObservationContext(onChange);
});

describe('explicit observation context', () => {
  it('formats wall time without accidentally treating it as UTC', () => {
    expect(localTimeValue(new Date(2026,10,12,9,5))).toBe('2026-11-12T09:05');
    expect(localTimeValue()).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    input('observation-time').value = '2026-11-12T21:30';
    input('observation-timezone').value = 'Asia/Shanghai';
    expect(readObservationContext()).toEqual({lat:31.23,lng:121.47,time:'2026-11-12 21:30:00',timezone:'Asia/Shanghai'});
  });
  it('follows map center until explicitly selected, and never follows sky coordinates', () => {
    center = {lat:30,lng:120}; syncObserverFromMap();
    expect(input('observation-lat').value).toBe('30.00000');
    setObservationLocation(40,116);
    syncObserverFromMap();
    expect(readObservationContext().lat).toBe(40);
    document.getElementById('use-map-center')!.click();
    expect(readObservationContext().lat).toBe(30);
    expect(onChange).toHaveBeenCalled();
  });
  it('preserves a manually edited observer and updates the summary', () => {
    input('observation-lat').value = '35'; change();
    center = {lat:0,lng:0}; syncObserverFromMap();
    expect(readObservationContext().lat).toBe(35);
    expect(document.getElementById('telescope-location-display')!.textContent).toContain('35');
    document.getElementById('use-current-time')!.click();
    window.dispatchEvent(new Event('languagechange'));
    expect(document.getElementById('observation-summary')!.textContent).toContain(input('observation-timezone').value);
  });
  it('rejects invalid and empty fields and exposes the containing settings', () => {
    for (const [id,value] of [['observation-lat','91'],['observation-lng','181'],['observation-time',''],['telescope-focal-length','0']]) {
      const field = input(id!); const before = field.value;
      field.value = value!;
      expect(() => readObservationContext()).toThrow('有效值');
      expect(field.closest('details')!.open).toBe(true);
      change();
      field.value = before;
    }
    input('telescope-sensor-width').remove();
    expect(() => readObservationContext()).toThrow();
  });
  it('rejects invalid timezones and trims valid timezone values', () => {
    input('observation-timezone').value = 'bad/timezone';
    expect(() => readObservationContext()).toThrow('有效时区');
    input('observation-timezone').value = ' UTC ';
    expect(readObservationContext().timezone).toBe('UTC');
  });
  it('tolerates absent summary elements and reuses an existing selected place', () => {
    setTelescopeTargetLocation({lat:25,lng:110});
    initObservationContext(onChange);
    expect(readObservationContext().lat).toBe(25);
    document.getElementById('telescope-location-display')!.remove();
    document.getElementById('observation-summary')!.remove();
    refreshObservationSummary();
    input('observation-lat').remove(); refreshObservationSummary();
    input('observation-lng').remove(); refreshObservationSummary();
  });
});
