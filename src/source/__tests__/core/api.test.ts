import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { normalizeBaseUrl, resolveApiBaseUrl, fetchWithTimeout, API_CONFIG } from '../../js/core/api';

describe('normalizeBaseUrl', () => {
  it('removes trailing slashes', () => {
    expect(normalizeBaseUrl('http://example.com/')).toBe('http://example.com');
    expect(normalizeBaseUrl('http://example.com//')).toBe('http://example.com');
    expect(normalizeBaseUrl('http://example.com/api/')).toBe('http://example.com/api');
  });

  it('does not modify URLs without trailing slashes', () => {
    expect(normalizeBaseUrl('http://example.com')).toBe('http://example.com');
    expect(normalizeBaseUrl('http://example.com/api')).toBe('http://example.com/api');
  });

  it('handles empty string', () => {
    expect(normalizeBaseUrl('')).toBe('');
  });
});

describe('resolveApiBaseUrl', () => {
  const originalLocation = { ...window.location };

  beforeEach(() => {
    // Reset window.location for each test
    Object.defineProperty(window, 'location', {
      value: {
        search: '',
        protocol: 'http:',
        hostname: 'localhost',
      },
      writable: true,
      configurable: true,
    });
    delete (window as any).APP_CONFIG;
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
      configurable: true,
    });
    delete (window as any).APP_CONFIG;
  });

  it('uses query parameter apiBaseUrl when present', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '?apiBaseUrl=http://myserver:9000/', protocol: 'http:', hostname: 'localhost' },
      writable: true, configurable: true,
    });
    expect(resolveApiBaseUrl()).toBe('http://myserver:9000');
  });

  it('falls back to window.APP_CONFIG.apiBaseUrl', () => {
    (window as any).APP_CONFIG = { apiBaseUrl: 'https://config.example.com/api/' };
    expect(resolveApiBaseUrl()).toBe('https://config.example.com/api');
  });

  it('prefers query param over window.APP_CONFIG', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '?apiBaseUrl=http://query:8080', protocol: 'http:', hostname: 'localhost' },
      writable: true, configurable: true,
    });
    (window as any).APP_CONFIG = { apiBaseUrl: 'https://config.example.com' };
    expect(resolveApiBaseUrl()).toBe('http://query:8080');
  });

  it('uses localhost hostname with port 5001 when no config', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '', protocol: 'http:', hostname: 'localhost' },
      writable: true, configurable: true,
    });
    expect(resolveApiBaseUrl()).toBe('http://127.0.0.1:5001');
  });

  it('preserves non-localhost hostname', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '', protocol: 'https:', hostname: 'stargazing.example.com' },
      writable: true, configurable: true,
    });
    expect(resolveApiBaseUrl()).toBe('https://stargazing.example.com:5001');
  });

  it('falls back to hardcoded default when hostname is empty', () => {
    Object.defineProperty(window, 'location', {
      value: { search: '', protocol: 'http:', hostname: '' },
      writable: true, configurable: true,
    });
    expect(resolveApiBaseUrl()).toBe('http://127.0.0.1:5001');
  });
});

describe('fetchWithTimeout', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns the response on a successful fetch', async () => {
    const mockResponse = new Response(JSON.stringify({ ok: true }), { status: 200 });
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockResponse);

    const promise = fetchWithTimeout('http://example.com/api');
    const result = await promise;

    expect(result).toBe(mockResponse);
    expect(fetchSpy).toHaveBeenCalledTimes(1);

    fetchSpy.mockRestore();
  });

  it('retries once on server error (5xx)', async () => {
    const errorResponse = new Response('Server Error', { status: 500 });
    const successResponse = new Response(JSON.stringify({ ok: true }), { status: 200 });
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(errorResponse)
      .mockResolvedValueOnce(successResponse);

    const result = await fetchWithTimeout('http://example.com/api');

    expect(result).toBe(successResponse);
    expect(fetchSpy).toHaveBeenCalledTimes(2);

    fetchSpy.mockRestore();
  });

  it('does not retry on client error (4xx)', async () => {
    const errorResponse = new Response('Not Found', { status: 404 });
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(errorResponse);

    const result = await fetchWithTimeout('http://example.com/api');

    expect(result).toBe(errorResponse);
    expect(fetchSpy).toHaveBeenCalledTimes(1); // no retry

    fetchSpy.mockRestore();
  });

  it('throws on timeout when AbortController fires before fetch settles', async () => {
    // AbortController uses its own internal timing, not setTimeout.
    // We simulate the abort by making fetch reject with an AbortError.
    const abortError = new DOMException('The operation was aborted.', 'AbortError');

    // First call: fetch rejects with AbortError (simulating timeout abort)
    // Second call (retry): also rejects with AbortError
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
      .mockRejectedValueOnce(abortError)
      .mockRejectedValueOnce(abortError);

    const promise = fetchWithTimeout('http://example.com/api', {}, 1000);
    await expect(promise).rejects.toThrow('Request timed out');

    fetchSpy.mockRestore();
  });
});

describe('API_CONFIG', () => {
  it('has all expected endpoint keys', () => {
    expect(API_CONFIG.endpoints.analyze).toBe('/api/analyze_stargazing_area');
    expect(API_CONFIG.endpoints.health).toBe('/api/health');
    expect(API_CONFIG.endpoints.lightPollution).toBe('/api/light_pollution');
    expect(API_CONFIG.endpoints.coordinateAnalysis).toBe('/api/coordinate_analysis');
    expect(API_CONFIG.endpoints.telescopeTargets).toBe('/api/telescope/targets');
    expect(API_CONFIG.endpoints.telescopePlan).toBe('/api/telescope/plan');
    expect(API_CONFIG.endpoints.telescopeMosaic).toBe('/api/telescope/mosaic');
    expect(API_CONFIG.endpoints.telescopePresets).toBe('/api/telescope/presets');
  });

  it('has a baseUrl that is a non-empty string', () => {
    expect(API_CONFIG.baseUrl).toBeTruthy();
    expect(typeof API_CONFIG.baseUrl).toBe('string');
  });
});
