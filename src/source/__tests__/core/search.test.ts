import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { setCurrentLanguage, setIsTelescopeMode } from '@/state';
import { initSearch, submitSearch, syncSearchMode } from '@/core/search';

const mocks = vi.hoisted(() => ({
  setView: vi.fn(), gotoRaDec: vi.fn(), ready: vi.fn(), overlay: vi.fn(), toast: vi.fn(),
}));
vi.mock('@/map/map-instance', () => ({ getMap: () => ({ setView: mocks.setView }) }));
vi.mock('@/features/telescope/aladin-core', () => ({
  ensureAladinReady: mocks.ready, updateFovOverlay: mocks.overlay,
}));
vi.mock('@/utils/dom', () => ({ showToast: mocks.toast }));
vi.mock('@/core/api', () => ({ API_CONFIG: { baseUrl: 'http://localhost:3000' } }));

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal('fetch', vi.fn());
  mocks.ready.mockResolvedValue({ gotoRaDec: mocks.gotoRaDec });
  document.body.innerHTML = '<input id="search-input"><div id="search-status"></div>';
  setCurrentLanguage('zh');
  setIsTelescopeMode(false);
  syncSearchMode();
});
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

function skyResponse(): Response {
  return new Response(JSON.stringify({ name: 'M 42', ra: 83.8201, dec: -5.3876, source: 'local_catalog' }));
}

describe('single search field', () => {
  it('updates the hint and accessible label in each mode and language', () => {
    const input = document.querySelector('input')!;
    expect(input.placeholder).toBe('搜索地点，如上海、安吉（回车确认）');
    expect(input.getAttribute('aria-label')).toBe('搜索地点');
    setIsTelescopeMode(true); syncSearchMode();
    expect(input.placeholder).toContain('M31');
    expect(input.getAttribute('aria-label')).toBe('搜索天体');
    setCurrentLanguage('en'); syncSearchMode();
    expect(input.placeholder).toContain('Search sky objects');
    expect(input.getAttribute('aria-label')).toBe('Search sky objects');
    setIsTelescopeMode(false); syncSearchMode();
    expect(input.placeholder).toBe('Search location...');
    expect(input.getAttribute('aria-label')).toBe('Search location');
  });

  it('handles absent fields and ignores empty input and IME confirmation', async () => {
    document.body.innerHTML = ''; initSearch();
    document.body.innerHTML = '<input id="search-input" value="M31">'; initSearch();
    const input = document.querySelector('input')!;
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'a' }));
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', isComposing: true }));
    await submitSearch('   ');
    expect(fetch).not.toHaveBeenCalled();
    expect(mocks.ready).not.toHaveBeenCalled();
  });

  it('submits Enter to celestial search only', async () => {
    vi.mocked(fetch).mockResolvedValue(skyResponse());
    setIsTelescopeMode(true); initSearch();
    const input = document.querySelector('input')!; input.value = ' M42 ';
    const event = new KeyboardEvent('keydown', { key: 'Enter', cancelable: true });
    input.dispatchEvent(event);
    await vi.waitFor(() => expect(mocks.gotoRaDec).toHaveBeenCalledWith(83.8201, -5.3876));
    expect(event.defaultPrevented).toBe(true);
    expect(fetch).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledWith('http://localhost:3000/api/telescope/resolve?name=M42', {
      signal: expect.any(AbortSignal),
    });
    expect(mocks.overlay).toHaveBeenCalledOnce();
    expect(document.getElementById('search-status')!.textContent).toBe('已定位：M 42');
    expect(input.getAttribute('aria-busy')).toBe('false');
  });

  it('submits a place to geographic search only', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify([
      { lat: '31.23', lon: '121.47', display_name: '上海' },
    ])));
    await submitSearch(' 上海 ');
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('q=%E4%B8%8A%E6%B5%B7'));
    expect(mocks.setView).toHaveBeenCalledWith([31.23, 121.47], 13);
    expect(mocks.toast).toHaveBeenCalledWith('已定位到: 上海', 'success');
    expect(mocks.ready).not.toHaveBeenCalled();
  });

  it('reports missing places and HTTP/network errors', async () => {
    vi.mocked(fetch).mockResolvedValue(new Response('[]'));
    await submitSearch('missing');
    expect(mocks.toast).toHaveBeenCalledWith('未找到地点: missing', 'error');
    vi.mocked(fetch).mockResolvedValue(new Response('', { status: 503 }));
    await submitSearch('place');
    expect(mocks.toast).toHaveBeenLastCalledWith('地点搜索失败', 'error');
    setIsTelescopeMode(true); syncSearchMode();
    vi.mocked(fetch).mockResolvedValue(skyResponse());
    mocks.ready.mockRejectedValue(new Error('WebGL unavailable'));
    await submitSearch('M31');
    expect(mocks.toast).toHaveBeenLastCalledWith('天体搜索失败，请重试', 'error');
  });

  it('ignores a pending map response or failure after switching modes', async () => {
    let finish!: (response: Response) => void;
    vi.mocked(fetch).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
    const first = submitSearch('上海');
    setIsTelescopeMode(true); syncSearchMode();
    finish(new Response('[{"lat":"31","lon":"121"}]')); await first;
    expect(mocks.setView).not.toHaveBeenCalled();
    expect(mocks.toast).not.toHaveBeenCalled();
    setIsTelescopeMode(false); syncSearchMode();
    let fail!: (error: Error) => void;
    vi.mocked(fetch).mockImplementation(() => new Promise((_, reject) => { fail = reject; }));
    const second = submitSearch('上海');
    setIsTelescopeMode(true); syncSearchMode(); fail(new Error('offline')); await second;
    expect(mocks.toast).not.toHaveBeenCalled();
  });

  it('ignores a sky search if mode changes during initialization', async () => {
    vi.mocked(fetch).mockResolvedValue(skyResponse());
    let ready!: (sky: unknown) => void;
    mocks.ready.mockImplementation(() => new Promise((resolve) => { ready = resolve; }));
    setIsTelescopeMode(true); syncSearchMode();
    const search = submitSearch('M42');
    await vi.waitFor(() => expect(mocks.ready).toHaveBeenCalled());
    setIsTelescopeMode(false); syncSearchMode();
    ready({ gotoRaDec: mocks.gotoRaDec }); await search;
    expect(mocks.gotoRaDec).not.toHaveBeenCalled();
  });

  it.each([404, 503])('distinguishes a missing object from an unavailable resolver (%s)', async (status) => {
    setIsTelescopeMode(true); syncSearchMode();
    vi.mocked(fetch).mockResolvedValue(new Response('', { status }));
    await submitSearch('unknown');
    expect(mocks.toast).toHaveBeenLastCalledWith(
      status === 404 ? '未找到该天体，请检查名称或编号' : '天体名称服务暂不可用，可重试或使用 M、NGC、IC 编号', 'error',
    );
    expect(document.querySelector('input')!.getAttribute('aria-busy')).toBe('false');
  });

  it.each([
    { ra: null, dec: 0 }, { ra: 0, dec: null }, { ra: -1, dec: 0 },
    { ra: 360, dec: 0 }, { ra: 0, dec: -91 }, { ra: 0, dec: 91 },
  ])('rejects invalid coordinates before moving the sky: %j', async (target) => {
    setIsTelescopeMode(true); syncSearchMode();
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify(target)));
    await submitSearch('unknown');
    expect(mocks.gotoRaDec).not.toHaveBeenCalled();
    expect(mocks.toast).toHaveBeenCalledWith('天体搜索失败，请重试', 'error');
  });

  it('shows a bounded timeout instead of silently waiting', async () => {
    vi.useFakeTimers(); setIsTelescopeMode(true); syncSearchMode();
    vi.mocked(fetch).mockImplementation((_, options) => new Promise((_, reject) => {
      options!.signal!.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
    }));
    const search = submitSearch('unknown');
    expect(document.getElementById('search-status')!.textContent).toBe('正在搜索天体…');
    expect(document.querySelector('input')!.getAttribute('aria-busy')).toBe('true');
    await vi.advanceTimersByTimeAsync(6500); await search;
    expect(mocks.toast).toHaveBeenCalledWith('天体搜索超时，请重试或使用 M、NGC、IC 编号', 'error');
  });
});
