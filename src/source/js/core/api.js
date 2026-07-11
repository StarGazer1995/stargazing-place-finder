// ═══════════════════════════════════════════════════════════════════════
//  API — HTTP 请求封装与接口配置
// ═══════════════════════════════════════════════════════════════════════

/**
 * Fetch wrapper with AbortController timeout and one automatic retry.
 * @param {string} url - Request URL
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @param {number} timeoutMs - Timeout in ms (default 10000)
 * @returns {Promise<Response>}
 */
async function fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        if (!response.ok && response.status >= 500) {
            throw new Error(`Server error: ${response.status}`);
        }
        return response;
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error('Request timed out');
        }
        // One retry for transient failures
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

/**
 * 删除 URL 末尾的斜杠，避免后续拼接接口路径时出现双斜杠。
 * @param {string} url - 原始 URL
 * @returns {string} 标准化后的 URL
 */
function normalizeBaseUrl(url) {
    return url.replace(/\/+$/, '');
}

/**
 * 解析前端应使用的 API 基地址。
 * 优先级:
 * 1. URL 查询参数 `apiBaseUrl`
 * 2. 全局配置 `window.APP_CONFIG.apiBaseUrl`
 * 3. 当前页面主机名 + 默认 API 端口
 * 4. 本地开发默认值
 * @returns {string} API 基地址
 */
function resolveApiBaseUrl() {
    const searchParams = new URLSearchParams(window.location.search);
    const queryBaseUrl = searchParams.get('apiBaseUrl');
    const globalBaseUrl = window.APP_CONFIG?.apiBaseUrl;
    const configuredBaseUrl = queryBaseUrl || globalBaseUrl;

    if (configuredBaseUrl) {
        return normalizeBaseUrl(configuredBaseUrl);
    }

    const { protocol, hostname } = window.location;
    if (hostname) {
        const resolvedProtocol = protocol === 'https:' ? 'https:' : 'http:';
        const resolvedHost = hostname === 'localhost' ? '127.0.0.1' : hostname;
        return `${resolvedProtocol}//${resolvedHost}:5001`;
    }

    return 'http://127.0.0.1:5001';
}

// API配置
const API_CONFIG = {
    baseUrl: resolveApiBaseUrl(),
    endpoints: {
        analyze: '/api/analyze_stargazing_area',
        health: '/api/health',
        lightPollution: '/api/light_pollution',
        lightPollutionTiles: '/api/light_pollution/tiles/{z}/{x}/{y}.png',
        coordinateAnalysis: '/api/coordinate_analysis'
    }
};

console.info('[Stargazing] API base URL:', API_CONFIG.baseUrl);
