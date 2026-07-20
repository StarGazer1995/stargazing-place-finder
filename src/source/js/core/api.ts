// =============================================================================
// API — HTTP request helpers and endpoint configuration
// =============================================================================

import type { ApiConfig } from '../types/api';

// ---------------------------------------------------------------------------
// URL helpers
// ---------------------------------------------------------------------------

/** Strip trailing slashes from a URL to avoid double-slash path segments. */
export function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, '');
}

/**
 * Resolve the API base URL using a cascading fallback chain:
 *  1. URL query parameter `?apiBaseUrl=`
 *  2. Global config `window.APP_CONFIG.apiBaseUrl`
 *  3. Current page hostname with default API port (5001)
 *  4. Hardcoded fallback for local development
 */
export function resolveApiBaseUrl(): string {
  const searchParams = new URLSearchParams(window.location.search);
  const queryBaseUrl = searchParams.get('apiBaseUrl');
  const globalBaseUrl = window.APP_CONFIG?.apiBaseUrl;
  const configuredBaseUrl = queryBaseUrl || globalBaseUrl;

  if (configuredBaseUrl) return normalizeBaseUrl(configuredBaseUrl);

  const { protocol, hostname } = window.location;
  if (hostname) {
    const resolvedProtocol = protocol === 'https:' ? 'https:' : 'http:';
    const resolvedHost = hostname === 'localhost' ? '127.0.0.1' : hostname;
    return `${resolvedProtocol}//${resolvedHost}:5001`;
  }

  return 'http://127.0.0.1:5001';
}

// ---------------------------------------------------------------------------
// API configuration
// ---------------------------------------------------------------------------

export const API_CONFIG: ApiConfig = {
  baseUrl: resolveApiBaseUrl(),
  endpoints: {
    analyze: '/api/analyze_stargazing_area',
    health: '/api/health',
    lightPollution: '/api/light_pollution',
    lightPollutionTiles: '/api/light_pollution/tiles/{z}/{x}/{y}.png',
    coordinateAnalysis: '/api/coordinate_analysis',
    telescopeTargets: '/api/telescope/targets',
    telescopePlan: '/api/telescope/plan',
    telescopeMosaic: '/api/telescope/mosaic',
    telescopePresets: '/api/telescope/presets',
  },
};

console.info('[Stargazing] API base URL:', API_CONFIG.baseUrl);

// ---------------------------------------------------------------------------
// Fetch wrapper
// ---------------------------------------------------------------------------

/**
 * Fetch with AbortController timeout and one automatic retry for 5xx / transient errors.
 */
export async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = 10000,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    if (!response.ok && response.status >= 500) {
      throw new Error(`Server error: ${response.status}`);
    }
    return response;
  } catch (error: any) {
    if (error?.name === 'AbortError') throw new Error('Request timed out');

    // One automatic retry for transient failures
    const retryController = new AbortController();
    const retryTimer = setTimeout(() => retryController.abort(), timeoutMs);
    try {
      return await fetch(url, { ...options, signal: retryController.signal });
    } finally {
      clearTimeout(retryTimer);
    }
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------------------
// Health check
// ---------------------------------------------------------------------------

/** Ping the backend health endpoint. Returns true when healthy. */
export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.health}`);
    if (response.ok) {
      const data = await response.json();
      console.log('API health check OK:', data);
      return true;
    }
  } catch (error) {
    console.warn('API health check failed:', error);
  }
  return false;
}
