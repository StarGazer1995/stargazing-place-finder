import { isTelescopeMode } from '../state';
import { getText } from './i18n';
import { API_CONFIG } from './api';
import { getMap } from '../map/map-instance';
import { ensureAladinReady, updateFovOverlay } from '../features/telescope/aladin-core';
import { showToast } from '../utils/dom';

let searchGeneration = 0;
let searchController: AbortController | undefined;

function setSearchStatus(message: string, busy: boolean): void {
  const status = document.getElementById('search-status');
  if (status) status.textContent = message;
  document.getElementById('search-input')?.setAttribute('aria-busy', String(busy));
}

/** Keep the single search field aligned with the active mode and language. */
export function syncSearchMode(): void {
  // Ignore replies to searches from a mode the user has already left.
  searchGeneration++;
  searchController?.abort();
  setSearchStatus('', false);
  const input = document.getElementById('search-input') as HTMLInputElement | null;
  if (!input) return;
  input.placeholder = getText(isTelescopeMode ? 'skySearchPlaceholder' : 'searchPlaceholder');
  input.setAttribute('aria-label', getText(isTelescopeMode ? 'skySearchLabel' : 'locationSearchLabel'));
}

/** Submit to exactly one resolver, selected by the current page mode. */
export async function submitSearch(query: string): Promise<void> {
  query = query.trim();
  if (!query) return;
  const generation = ++searchGeneration;
  searchController?.abort();
  const telescope = isTelescopeMode;
  const isCurrent = () => generation === searchGeneration;
  let failureMessage = telescope ? getText('skySearchFailed') : '地点搜索失败';

  try {
    if (telescope) {
      setSearchStatus(getText('skySearching'), true);
      const controller = new AbortController();
      searchController = controller;
      const timer = setTimeout(() => controller.abort(), 6500);
      try {
        // Resolve independently of Aladin's survey-loading promise. Common
        // catalog IDs never need a browser request to an external name service.
        const response = await fetch(`${API_CONFIG.baseUrl}/api/telescope/resolve?name=${encodeURIComponent(query)}`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          failureMessage = getText(response.status === 404 ? 'skyNotFound' : 'skyResolverUnavailable');
          throw new Error();
        }
        const target = await response.json();
        if (!Number.isFinite(target.ra) || !Number.isFinite(target.dec)
          || target.ra < 0 || target.ra >= 360 || target.dec < -90 || target.dec > 90) throw new Error();
        const sky = await ensureAladinReady();
        if (!isCurrent()) return;
        sky.gotoRaDec(target.ra, target.dec);
        updateFovOverlay();
        setSearchStatus(`${getText('skyLocated')}${target.name}`, false);
      } finally {
        clearTimeout(timer);
      }
      return;
    }

    const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const results = await response.json();
    if (!isCurrent()) return;
    if (results?.[0]) {
      const lat = parseFloat(results[0].lat);
      const lng = parseFloat(results[0].lon);
      getMap().setView([lat, lng], 13);
      showToast(`已定位到: ${results[0].display_name}`, 'success');
    } else {
      showToast('未找到地点: ' + query, 'error');
    }
  } catch (error: any) {
    if (isCurrent()) {
      if (error?.name === 'AbortError') failureMessage = getText('skySearchTimeout');
      setSearchStatus(failureMessage, false);
      showToast(failureMessage, 'error');
    }
  }
}

export function initSearch(): void {
  syncSearchMode();
  document.getElementById('search-input')?.addEventListener('keydown', (event) => {
    const e = event as KeyboardEvent;
    if (e.key !== 'Enter' || e.isComposing) return;
    e.preventDefault();
    void submitSearch((e.target as HTMLInputElement).value);
  });
}
