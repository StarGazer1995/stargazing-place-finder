import { map, telescopeTargetLocation, setTelescopeTargetLocation } from '../../state';
import { getText } from '../../core/i18n';

const input = (id: string) => document.getElementById(id) as HTMLInputElement;
let locationExplicit = false;
let timeExplicit = false;

/** A wall-clock value paired with the explicitly displayed IANA timezone. */
export function localTimeValue(now = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

export function refreshObservationSummary(): void {
  const lat = input('observation-lat');
  const lng = input('observation-lng');
  if (!lat || !lng) return;
  const place = document.getElementById('telescope-location-display');
  if (place) place.textContent = `${getText('ui.observationPlace')} · ${lat.value}, ${lng.value}`;
  const summary = document.getElementById('observation-summary');
  if (summary) summary.textContent = `${input('observation-time').value.replace('T', ' ')} · ${input('observation-timezone').value}`;
}

export function setObservationLocation(lat: number, lng: number, explicit = true): void {
  locationExplicit = explicit;
  setTelescopeTargetLocation({ lat, lng });
  input('observation-lat').value = lat.toFixed(5);
  input('observation-lng').value = lng.toFixed(5);
  refreshObservationSummary();
}

export function syncObserverFromMap(): void {
  if (!input('observation-time')) return;
  if (!timeExplicit) {
    input('observation-time').value = localTimeValue();
    input('observation-timezone').value = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  }
  if (!locationExplicit) {
    const center = map.getCenter();
    setObservationLocation(center.lat, center.lng, false);
  }
  refreshObservationSummary();
}

export function readObservationContext(): { lat: number; lng: number; time: string; timezone: string } {
  const ids = ['observation-lat', 'observation-lng', 'observation-time', 'observation-timezone',
    'telescope-focal-length', 'telescope-sensor-width', 'telescope-sensor-height'];
  for (const id of ids) {
    const field = input(id);
    if (!field || !field.value || !field.checkValidity()) {
      const details = field?.closest('details');
      if (details) details.open = true;
      field?.reportValidity();
      throw new Error(getText('ui.invalidObservation'));
    }
  }
  const timezone = input('observation-timezone').value.trim();
  try { new Intl.DateTimeFormat('en', { timeZone: timezone }); }
  catch { throw new Error(getText('ui.invalidTimezone')); }
  return {
    lat: Number(input('observation-lat').value), lng: Number(input('observation-lng').value),
    time: `${input('observation-time').value.replace('T', ' ')}:00`, timezone,
  };
}

/** Initialize once. Moving the sky never changes the terrestrial observer. */
export function initObservationContext(onChange: () => void): void {
  if (!input('observation-time')) return;
  const now = () => {
    timeExplicit = false;
    input('observation-time').value = localTimeValue();
    input('observation-timezone').value = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    refreshObservationSummary();
  };
  now();
  const center = telescopeTargetLocation || map.getCenter();
  setObservationLocation(center.lat, center.lng, !!telescopeTargetLocation);
  for (const id of ['observation-lat', 'observation-lng', 'observation-time', 'observation-timezone']) {
    input(id).addEventListener('input', () => {
      onChange();
      if (id === 'observation-time' || id === 'observation-timezone') timeExplicit = true;
      if (id === 'observation-lat' || id === 'observation-lng') locationExplicit = true;
      if (input('observation-lat').checkValidity() && input('observation-lng').checkValidity()) {
        setTelescopeTargetLocation({ lat: Number(input('observation-lat').value), lng: Number(input('observation-lng').value) });
      }
      refreshObservationSummary();
    });
  }
  document.getElementById('use-map-center')?.addEventListener('click', () => {
    onChange();
    const center = map.getCenter();
    setObservationLocation(center.lat, center.lng);
  });
  document.getElementById('use-current-time')?.addEventListener('click', () => { onChange(); now(); });
  window.addEventListener('languagechange', refreshObservationSummary);
}
