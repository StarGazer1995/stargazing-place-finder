// 全局变量定义
let map;
let currentOverlay = null;
let currentImageLayers = [];
let pollutionTileLayer = null;
let dataCache = new Map();
let currentLanguage = 'zh';
let isLoading = false;
let loadingIndicator;

// 观星区域选择器相关变量
let drawControl = null;
let drawnItems = null;
let currentPolygon = null;
let analysisResults = [];
let isAnalysisMode = false;
let statusIndicator = null;
let resultsPanel = null;

// ═══════════════════════════════════════════════════════════════════════
//  UI utilities
// ═══════════════════════════════════════════════════════════════════════

/**
 * Show a non-blocking toast notification that auto-dismisses.
 * @param {string} message - Message text
 * @param {'info'|'error'|'success'} type - Toast type
 * @param {number} duration - Auto-dismiss delay in ms (default 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);

    // Trigger reflow for transition
    void toast.offsetWidth;
    toast.classList.add('toast-visible');

    setTimeout(() => {
        toast.classList.remove('toast-visible');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

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

// 标记样式配置
const MARKER_STYLES = {
    stargazing: {
        className: 'stargazing-marker',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    },
    excellent: {
        className: 'stargazing-marker excellent-marker',
        iconSize: [16, 16],
        iconAnchor: [8, 8]
    },
    good: {
        className: 'stargazing-marker good-marker',
        iconSize: [14, 14],
        iconAnchor: [7, 7]
    },
    fair: {
        className: 'stargazing-marker fair-marker',
        iconSize: [12, 12],
        iconAnchor: [6, 6]
    },
    poor: {
        className: 'stargazing-marker poor-marker',
        iconSize: [10, 10],
        iconAnchor: [5, 5]
    }
};

/**
 * 检测用户浏览器语言偏好
 * @returns {string} 检测到的语言代码 ('zh' 或 'en')
 */
function detectUserLanguage() {
    // 获取浏览器语言设置
    const browserLang = navigator.language || navigator.userLanguage || navigator.browserLanguage;
    
    // 检查是否为英语
    if (browserLang.toLowerCase().startsWith('en')) {
        return 'en';
    }
    
    // 检查是否为中文
    if (browserLang.toLowerCase().startsWith('zh')) {
        return 'zh';
    }
    
    // 默认返回中文
    return 'zh';
}

// 多语言配置
const i18nConfig = {
    zh: {
        title: '观星地点查找器',
        searchPlaceholder: '搜索地点...',
        lightPollutionInfo: '光污染信息',
        coordinates: '坐标',
        bortleClass: '波特尔等级',
        lightPollutionLevel: '光污染程度',
        observationSuitability: '观测适宜性',
        darkSkyStats: '暗空区域统计',
        totalDarkSkyArea: '暗空区域总面积',
        darkSkyPercentage: '暗空区域占比',
        bortleDistribution: '波特尔等级分布',
        legend: '图例说明',
        observationTips: '观测建议',
        loadingData: '正在加载数据...',
        languageToggle: '中/EN',
        bortleDescriptions: {
            1: '1级 - 极佳暗空',
            2: '2级 - 典型暗空',
            3: '3级 - 乡村天空',
            4: '4级 - 乡村/郊区过渡',
            5: '5级 - 郊区天空',
            6: '6级 - 明亮郊区',
            7: '7级 - 郊区/城市过渡',
            8: '8级 - 城市天空',
            9: '9级 - 内城天空'
        },
        suitabilityLevels: {
            excellent: '极佳',
            good: '良好',
            fair: '一般',
            poor: '较差',
            verypoor: '很差'
        },
        tips: {
            1: ['银河清晰可见', '可观测暗弱天体', '最佳观星地点'],
            2: ['银河可见', '适合深空观测', '优秀观星地点'],
            3: ['银河部分可见', '适合行星观测', '良好观星地点'],
            4: ['银河微弱可见', '适合明亮天体', '一般观星地点'],
            5: ['银河难以看见', '仅适合行星月亮', '观星条件一般'],
            6: ['银河不可见', '仅适合明亮天体', '观星条件较差'],
            7: ['天空明亮', '观星条件差', '不推荐观星'],
            8: ['严重光污染', '观星条件很差', '不适合观星'],
            9: ['极严重光污染', '几乎无法观星', '完全不适合观星']
        }
    },
    en: {
        title: 'Stargazing Place Finder',
        searchPlaceholder: 'Search location...',
        lightPollutionInfo: 'Light Pollution Info',
        coordinates: 'Coordinates',
        bortleClass: 'Bortle Class',
        lightPollutionLevel: 'Light Pollution Level',
        observationSuitability: 'Observation Suitability',
        darkSkyStats: 'Dark Sky Statistics',
        totalDarkSkyArea: 'Total Dark Sky Area',
        darkSkyPercentage: 'Dark Sky Percentage',
        bortleDistribution: 'Bortle Class Distribution',
        legend: 'Legend',
        observationTips: 'Observation Tips',
        loadingData: 'Loading data...',
        languageToggle: 'EN/中',
        bortleDescriptions: {
            1: 'Class 1 - Excellent Dark Sky',
            2: 'Class 2 - Typical Dark Sky',
            3: 'Class 3 - Rural Sky',
            4: 'Class 4 - Rural/Suburban Transition',
            5: 'Class 5 - Suburban Sky',
            6: 'Class 6 - Bright Suburban',
            7: 'Class 7 - Suburban/Urban Transition',
            8: 'Class 8 - City Sky',
            9: 'Class 9 - Inner City Sky'
        },
        suitabilityLevels: {
            excellent: 'Excellent',
            good: 'Good',
            fair: 'Fair',
            poor: 'Poor',
            verypoor: 'Very Poor'
        },
        tips: {
            1: ['Milky Way clearly visible', 'Deep sky objects observable', 'Best stargazing location'],
            2: ['Milky Way visible', 'Good for deep sky observation', 'Excellent stargazing location'],
            3: ['Milky Way partially visible', 'Good for planetary observation', 'Good stargazing location'],
            4: ['Milky Way faintly visible', 'Suitable for bright objects', 'Fair stargazing location'],
            5: ['Milky Way hard to see', 'Only planets and moon', 'Average stargazing conditions'],
            6: ['Milky Way not visible', 'Only bright objects', 'Poor stargazing conditions'],
            7: ['Bright sky', 'Poor stargazing conditions', 'Not recommended for stargazing'],
            8: ['Severe light pollution', 'Very poor stargazing', 'Not suitable for stargazing'],
            9: ['Extreme light pollution', 'Nearly impossible to stargaze', 'Completely unsuitable for stargazing']
        }
    }
};

/**
 * 获取多语言文本
 * @param {string} key - 文本键值
 * @returns {string} 对应语言的文本
 */
function getText(key) {
    const keys = key.split('.');
    let value = i18nConfig[currentLanguage];
    for (const k of keys) {
        value = value?.[k];
    }
    return value || key;
}

/**
 * 更新页面元素的多语言文本
 */
function updateLanguageElements() {
    // 更新HTML根元素的lang属性
    const htmlRoot = document.getElementById('html-root');
    if (htmlRoot) {
        htmlRoot.setAttribute('lang', currentLanguage);
    }
    
    // 更新页面标题
    document.title = getText('title');
    
    // 更新搜索框占位符
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.placeholder = getText('searchPlaceholder');
        searchInput.setAttribute('aria-label', getText('searchPlaceholder'));
    }
    
    // 更新语言切换按钮
    const languageBtn = document.getElementById('language-btn');
    if (languageBtn) {
        languageBtn.textContent = getText('languageToggle');
        languageBtn.setAttribute('aria-label', currentLanguage === 'zh' ? '切换到英语' : 'Switch to Chinese');
    }
    
    // 更新加载覆盖层文本
    const loadingTitle = document.querySelector('.loading-title');
    if (loadingTitle) {
        loadingTitle.textContent = getText('title');
    }
    
    const loadingSubtitle = document.querySelector('.loading-subtitle');
    if (loadingSubtitle) {
        loadingSubtitle.textContent = getText('loadingData');
    }
    
    const loadingText = document.querySelector('.loading-text');
    if (loadingText) {
        loadingText.textContent = currentLanguage === 'zh' ? '请稍候' : 'Please wait';
    }
    
    // 更新加载指示器文本
    const loadingIndicatorText = document.querySelector('#loading-indicator span');
    if (loadingIndicatorText) {
        loadingIndicatorText.textContent = getText('loadingData');
    }
    
    // 更新面板标题
    const infoPanelTitle = document.querySelector('.info-panel h3');
    if (infoPanelTitle) {
        infoPanelTitle.textContent = getText('lightPollutionInfo');
    }
    
    const statsPanelTitle = document.querySelector('.stats-panel h3');
    if (statsPanelTitle) {
        statsPanelTitle.textContent = getText('darkSkyStats');
    }
    
    // 更新统计面板
    updateStatsPanel();
}

/**
 * 切换语言
 */
function toggleLanguage() {
    currentLanguage = currentLanguage === 'zh' ? 'en' : 'zh';
    console.log(`语言已切换到: ${currentLanguage}`);
    updateLanguageElements();
    
    // 重新加载当前视图的数据以更新弹窗等
    if (map) {
        loadCurrentViewData();
    }
}









/**
 * 渲染光污染图层
 * @param {Array} data - 光污染数据
 */
function renderLightPollutionLayer(data) {
    // 清除现有标记图层，但保留图像图层
    if (currentOverlay) {
        map.removeLayer(currentOverlay);
        currentOverlay = null;
    }
    
    if (!data || data.length === 0) return;
    
    // 创建热力图数据
    const heatData = data.map(point => [
        point.lat,
        point.lng,
        point.intensity
    ]);
    
    // 创建标记聚类组
    const markers = L.markerClusterGroup({
        maxClusterRadius: 50,
        iconCreateFunction: function(cluster) {
            const childCount = cluster.getChildCount();
            const avgBortle = cluster.getAllChildMarkers()
                .reduce((sum, marker) => sum + marker.options.bortleClass, 0) / childCount;
            
            return L.divIcon({
                html: `<div style="background-color: ${getBortleColor(Math.round(avgBortle))}; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold;">${childCount}</div>`,
                className: 'custom-cluster-icon',
                iconSize: [40, 40]
            });
        }
    });
    
    // 添加标记
    data.forEach(point => {
        const marker = L.circleMarker([point.lat, point.lng], {
            radius: 5,
            fillColor: getBortleColor(point.bortleClass),
            color: '#64b5f6',
            weight: 1.5,
            opacity: 0.9,
            fillOpacity: 0.6,
            bortleClass: point.bortleClass
        });
        
        const popupContent = `
            <div class="location-popup">
                <h4>${getText('coordinates')}</h4>
                <p>${point.lat.toFixed(4)}, ${point.lng.toFixed(4)}</p>
                <h4>${getText('bortleClass')}</h4>
                <p>${getText(`bortleDescriptions.${point.bortleClass}`)}</p>
            </div>
        `;
        
        marker.bindPopup(popupContent);
        markers.addLayer(marker);
    });
    
    currentOverlay = markers;
    map.addLayer(currentOverlay);
}

/**
 * 初始化地图
 */
function initializeMap() {
    console.log('正在初始化地图...');
    
    // 创建地图实例 - 关闭所有控件
    map = L.map('map', {
        center: [39.9042, 116.4074], // 北京坐标
        zoom: 8,
        zoomControl: false,  // 关闭缩放控件
        attributionControl: false  // 关闭版权控件
    });
    
    // 添加底图
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
    
    // 添加动态光污染瓦片图层（直接从GeoTIFF采样渲染）
    pollutionTileLayer = L.tileLayer(
        `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.lightPollutionTiles}`,
        {
            maxZoom: 18,
            opacity: 0.75,
            attribution: 'VIIRS DNB 2025'
        }
    ).addTo(map);
    
    // 不添加任何控件（按用户要求关闭所有控件）
    
    // 监听地图移动和缩放事件
    map.on('moveend zoomend', debounce(loadCurrentViewData, 300));
    
    // 监听地图点击事件
    map.on('click', onMapClick);
    
    // 初始加载数据
    console.log('开始加载光污染数据...');
    loadCurrentViewData();
    
    console.log('地图初始化完成');
}

/**
 * 显示加载指示器
 */
function showLoadingIndicator() {
    if (!loadingIndicator) {
        loadingIndicator = document.querySelector('.loading-indicator');
    }
    if (loadingIndicator) {
        loadingIndicator.classList.add('show');
    }
    isLoading = true;
}

/**
 * 隐藏加载指示器
 */
function hideLoadingIndicator() {
    if (loadingIndicator) {
        loadingIndicator.classList.remove('show');
    }
    isLoading = false;
}

/**
 * 获取波特尔等级对应的颜色
 * @param {number} bortleClass - 波特尔等级 (1-9)
 * @returns {string} 颜色值
 */
function getBortleColor(bortleClass) {
    const colors = {
        1: '#000000', // 黑色 - 极佳暗空
        2: '#1a1a1a', // 深灰色 - 典型暗空
        3: '#2d2d2d', // 灰色 - 乡村天空
        4: '#4a4a00', // 深黄绿色 - 乡村/郊区过渡
        5: '#666600', // 黄绿色 - 郊区天空
        6: '#cc6600', // 橙色 - 明亮郊区
        7: '#cc3300', // 红橙色 - 郊区/城市过渡
        8: '#ff0066', // 品红色 - 城市天空
        9: '#ff00ff'  // 紫红色 - 内城天空
    };
    return colors[bortleClass] || '#888888';
}

/**
 * 根据波特尔等级获取强度半径
 * @param {number} bortleClass - 波特尔等级
 * @returns {number} 强度半径
 */
function getIntensityRadius(bortleClass) {
    // 波特尔等级越高，光污染越严重，影响范围越大
    const baseRadius = 0.5;
    return baseRadius * (bortleClass / 3);
}

/**
 * 清除现有图层
 */
function clearLayers() {
    if (currentOverlay) {
        map.removeLayer(currentOverlay);
        currentOverlay = null;
    }
    // 清除图像图层
    clearImageLayers();
}

/**
 * 清除所有图像图层
 */
function clearImageLayers() {
    currentImageLayers.forEach(layer => {
        if (map.hasLayer(layer)) {
            map.removeLayer(layer);
        }
    });
    currentImageLayers = [];
}

/**
 * 加载光污染图像图层
 * @param {Object} bounds - 地图边界对象
 */
async function loadLightPollutionDataPoints() {
    try {
        console.log('正在加载光污染统计...');
        
        if (!map) {
            console.warn('地图尚未初始化，无法加载数据');
            return;
        }
        
        const bounds = map.getBounds();
        
        const apiUrl = `${API_CONFIG.baseUrl}/api/light_pollution?` +
            `north=${bounds.getNorth()}&south=${bounds.getSouth()}&` +
            `east=${bounds.getEast()}&west=${bounds.getWest()}` +
            `&zoom=${map.getZoom()}`;
        
        const response = await fetch(apiUrl);
        if (!response.ok) {
            console.warn('无法获取光污染数据:', response.statusText);
            return;
        }
        
        const json = await response.json();
        
        if (!json.success || !json.data || !Array.isArray(json.data)) {
            console.log('没有获取到光污染数据');
            return;
        }
        
        // 更新统计面板（瓦片图层由 Leaflet 自动管理）
        const points = json.data.map(d => ({
            lat: d.lat,
            lng: d.lng,
            bortleClass: d.bortle,
            intensity: d.intensity,
            sqm: d.sqm
        }));
        const stats = calculateStats(points);
        updateStatsPanel(stats);
        
        console.log(`✅ 统计面板已更新，${json.data.length} 个采样点`);
        
    } catch (error) {
        console.error('加载光污染统计数据失败:', error);
    }
}

// 保持向后兼容
const loadLightPollutionImageLayers = loadLightPollutionDataPoints;

/**
 * 计算数据统计
 * @param {Array} data - 光污染数据
 * @returns {Object} 统计信息
 */
function calculateStats(data) {
    if (!data || data.length === 0) {
        return {
            darkSkyArea: 0,
            darkSkyPercentage: 0,
            bortleDistribution: {}
        };
    }
    
    const totalPoints = data.length;
    const darkSkyPoints = data.filter(point => point.bortleClass <= 3).length;
    const darkSkyPercentage = (darkSkyPoints / totalPoints * 100).toFixed(1);
    
    // 计算波特尔等级分布
    const bortleDistribution = {};
    for (let i = 1; i <= 9; i++) {
        const count = data.filter(point => point.bortleClass === i).length;
        bortleDistribution[i] = {
            count: count,
            percentage: (count / totalPoints * 100).toFixed(1)
        };
    }
    
    return {
        darkSkyArea: darkSkyPoints,
        darkSkyPercentage: darkSkyPercentage,
        bortleDistribution: bortleDistribution
    };
}

/**
 * 更新统计面板
 * @param {Object} stats - 统计数据
 */
function updateStatsPanel(stats = null) {
    const darkSkyStatsDiv = document.querySelector('.dark-sky-stats');
    const bortleDistributionDiv = document.querySelector('.bortle-distribution');
    
    if (!darkSkyStatsDiv || !bortleDistributionDiv) return;
    
    if (!stats) {
        darkSkyStatsDiv.innerHTML = `
            <h4>${getText('darkSkyStats')}</h4>
            <p>${getText('totalDarkSkyArea')}: --</p>
            <p>${getText('darkSkyPercentage')}: --%</p>
        `;
        
        bortleDistributionDiv.innerHTML = `
            <h4>${getText('bortleDistribution')}</h4>
            <p>暂无数据</p>
        `;
        return;
    }
    
    // 更新暗空区域统计
    darkSkyStatsDiv.innerHTML = `
        <h4>${getText('darkSkyStats')}</h4>
        <p>${getText('totalDarkSkyArea')}: ${stats.darkSkyArea} 个区域</p>
        <p>${getText('darkSkyPercentage')}: ${stats.darkSkyPercentage}%</p>
    `;
    
    // 更新波特尔等级分布
    let distributionHTML = `<h4>${getText('bortleDistribution')}</h4>`;
    for (let i = 1; i <= 9; i++) {
        const dist = stats.bortleDistribution[i] || { count: 0, percentage: '0.0' };
        const color = getBortleColor(i);
        distributionHTML += `
            <div class="bortle-bar">
                <span class="label">Class ${i}</span>
                <div class="bar">
                    <div class="fill" style="width: ${dist.percentage}%; background-color: ${color};"></div>
                </div>
                <span class="percentage">${dist.percentage}%</span>
            </div>
        `;
    }
    bortleDistributionDiv.innerHTML = distributionHTML;
}

/**
 * 使用新数据更新图层和统计
 * @param {Array} data - 光污染数据
 */
function updateLayersAndStats(data) {
    console.log('更新图层和统计信息，数据长度:', data ? data.length : 0);
    
    // 清除现有图层
    clearLayers();
    
    if (!data || data.length === 0) {
        console.log('没有数据，更新空统计面板');
        updateStatsPanel();
        return;
    }
    
    // 计算统计信息
    const stats = calculateStats(data);
    updateStatsPanel(stats);
    
    // 渲染光污染图层
    console.log('开始渲染光污染图层');
    renderLightPollutionLayer(data);
    
    console.log('图层和统计信息更新完成');
}

/**
 * 加载当前视图的数据
 */
async function loadCurrentViewData() {
    if (isLoading) return;
    
    const bounds = map.getBounds();
    const zoom = map.getZoom();
    
    const boundsObj = {
        north: bounds.getNorth(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        west: bounds.getWest()
    };
    
    showLoadingIndicator();
    
    try {
        // 添加调试：测试API连接
        console.log('测试API连接...');
        try {
            const testResponse = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.health}`);
            console.log('API健康检查响应:', testResponse.status, testResponse.statusText);
            if (testResponse.ok) {
                const healthData = await testResponse.json();
                console.log('API健康检查数据:', healthData);
            }
        } catch (apiError) {
            console.error('API连接测试失败:', apiError);
        }
        
        // 清除现有的点数据图层（但保留光污染图像图层）
        if (currentOverlay) {
            map.removeLayer(currentOverlay);
            currentOverlay = null;
        }
        
        // 加载光污染数据点
        await loadLightPollutionDataPoints();
    } catch (error) {
        console.error('加载数据失败:', error);
    } finally {
        hideLoadingIndicator();
    }
}

/**
 * 创建弹窗内容
 * @param {number} lat - 纬度
 * @param {number} lng - 经度
 * @param {number} bortleClass - 波特尔等级
 * @returns {string} HTML内容
 */
function createPopupContent(lat, lng, bortleClass) {
    const suitability = getSuitabilityLevel(bortleClass);
    const tips = getText(`tips.${bortleClass}`) || [];
    
    let tipsHTML = '';
    if (tips.length > 0) {
        tipsHTML = `
            <div class="observation-tips">
                <h5>${getText('observationTips')}</h5>
                <ul>
                    ${tips.map(tip => `<li>${tip}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    return `
        <div class="popup-content">
            <h4>${getText('lightPollutionInfo')}</h4>
            <p><strong>${getText('coordinates')}:</strong> ${lat.toFixed(4)}, ${lng.toFixed(4)}</p>
            <p><strong>${getText('bortleClass')}:</strong> ${getText(`bortleDescriptions.${bortleClass}`)}</p>
            <p><strong>${getText('observationSuitability')}:</strong> ${getText(`suitabilityLevels.${suitability}`)}</p>
            ${tipsHTML}
        </div>
    `;
}

/**
 * 获取观测适宜性等级
 * @param {number} bortleClass - 波特尔等级
 * @returns {string} 适宜性等级
 */
function getSuitabilityLevel(bortleClass) {
    if (bortleClass <= 2) return 'excellent';
    if (bortleClass <= 4) return 'good';
    if (bortleClass <= 6) return 'fair';
    if (bortleClass <= 7) return 'poor';
    return 'verypoor';
}

/**
 * 防抖函数
 * @param {Function} func - 要防抖的函数
 * @param {number} wait - 等待时间
 * @returns {Function} 防抖后的函数
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 地图点击事件处理
 * @param {Object} e - 点击事件对象
 */
async function onMapClick(e) {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    
    // 显示加载中的弹窗
    const loadingPopup = L.popup()
        .setLatLng(e.latlng)
        .setContent('<div style="text-align: center;">🔍 正在分析坐标点...</div>')
        .openOn(map);
    
    try {
        // 调用坐标分析API获取真实数据
        const analysisResult = await analyzeCoordinate(lat, lng);
        
        if (analysisResult && analysisResult.success) {
            const bortleClass = analysisResult.data.light_pollution.bortle_class;
            const popupContent = createDetailedPopupContent(lat, lng, analysisResult.data);
            
            // 更新弹窗内容
            loadingPopup.setContent(popupContent);
            
            // 更新信息面板
            updateInfoPanel(lat, lng, bortleClass);
        } else {
            // API调用失败，使用本地数据作为备选
            console.warn('API调用失败，使用本地数据:', analysisResult?.error);
            const nearestData = getNearestLightPollutionData(lat, lng);
            
            if (nearestData) {
                const popupContent = createPopupContent(lat, lng, nearestData.bortleClass);
                loadingPopup.setContent(popupContent);
                updateInfoPanel(lat, lng, nearestData.bortleClass);
            } else {
                loadingPopup.setContent('<div style="color: red;">❌ 无法获取该位置的光污染数据</div>');
            }
        }
    } catch (error) {
        console.error('坐标分析失败:', error);
        
        // 出错时使用本地数据作为备选
        const nearestData = getNearestLightPollutionData(lat, lng);
        
        if (nearestData) {
            const popupContent = createPopupContent(lat, lng, nearestData.bortleClass);
            loadingPopup.setContent(popupContent);
            updateInfoPanel(lat, lng, nearestData.bortleClass);
        } else {
            loadingPopup.setContent('<div style="color: red;">❌ 网络错误，无法获取光污染数据</div>');
        }
    }
}

/**
 * 调用坐标分析API
 * @param {number} lat - 纬度
 * @param {number} lng - 经度
 * @returns {Promise<Object>} API响应结果
 */
async function analyzeCoordinate(lat, lng) {
    try {
        const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.coordinateAnalysis}?lat=${lat}&lng=${lng}`);
        
        if (!response.ok) {
            throw new Error(`API请求失败: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('坐标分析结果:', result);
        return result;
    } catch (error) {
        console.error('坐标分析API调用失败:', error);
        throw error;
    }
}

/**
 * 创建详细的弹窗内容（基于API数据）
 * @param {number} lat - 纬度
 * @param {number} lng - 经度
 * @param {Object} data - API返回的分析数据
 * @returns {string} HTML内容
 */
function createDetailedPopupContent(lat, lng, data) {
    const lightPollution = data.light_pollution;
    const bortleClass = lightPollution.bortle_class;
    const sqmValue = lightPollution.sqm_value;
    const intensity = lightPollution.intensity;
    const description = lightPollution.description;
    
    const suitability = getSuitabilityLevel(bortleClass);
    const tips = getText('tips')[bortleClass] || [];
    
    return `
        <div class="popup-content">
            <h4>🌟 ${getText('lightPollutionInfo')}</h4>
            <div class="popup-section">
                <p><strong>📍 ${getText('coordinates')}:</strong> ${lat.toFixed(4)}, ${lng.toFixed(4)}</p>
                <p><strong>🌃 ${getText('bortleClass')}:</strong> ${bortleClass} - ${description}</p>
                <p><strong>✨ SQM值:</strong> ${sqmValue} mag/arcsec²</p>
                <p><strong>💡 光污染强度:</strong> ${(intensity * 100).toFixed(1)}%</p>
                <p><strong>🔭 ${getText('observationSuitability')}:</strong> 
                    <span class="suitability-${suitability}">${getText('suitabilityLevels')[suitability]}</span>
                </p>
            </div>
            ${tips.length > 0 ? `
            <div class="popup-section">
                <h5>💡 ${getText('observationTips')}:</h5>
                <ul>
                    ${tips.map(tip => `<li>${tip}</li>`).join('')}
                </ul>
            </div>
            ` : ''}
        </div>
    `;
}

/**
 * 更新信息面板
 * @param {number} lat - 纬度
 * @param {number} lng - 经度
 * @param {number} bortleClass - 波特尔等级
 */
function updateInfoPanel(lat, lng, bortleClass) {
    const infoPanel = document.querySelector('.info-panel');
    if (!infoPanel) return;
    
    const suitability = getSuitabilityLevel(bortleClass);
    
    infoPanel.innerHTML = `
        <h3>${getText('lightPollutionInfo')}</h3>
        <p><strong>${getText('coordinates')}:</strong> ${lat.toFixed(4)}, ${lng.toFixed(4)}</p>
        <p><strong>${getText('bortleClass')}:</strong> ${getText(`bortleDescriptions.${bortleClass}`)}</p>
        <p><strong>${getText('observationSuitability')}:</strong> ${getText(`suitabilityLevels.${suitability}`)}</p>
    `;
}

/**
 * 获取最近的光污染数据点
 * @param {number} lat - 目标纬度
 * @param {number} lng - 目标经度
 * @returns {Object|null} 最近的数据点
 */
function getNearestLightPollutionData(lat, lng) {
    // 从缓存中查找最近的数据点
    let nearestData = null;
    let minDistance = Infinity;
    
    dataCache.forEach(data => {
        data.forEach(point => {
            const distance = Math.sqrt(
                Math.pow(lat - point.lat, 2) + Math.pow(lng - point.lng, 2)
            );
            
            if (distance < minDistance) {
                minDistance = distance;
                nearestData = point;
            }
        });
    });
    
    // 如果没有找到数据，使用插值估算
    if (!nearestData || minDistance > 0.1) {
        const estimatedBortleClass = estimateBortleClass(lat, lng);
        nearestData = {
            lat: lat,
            lng: lng,
            bortleClass: estimatedBortleClass,
            intensity: getIntensityRadius(estimatedBortleClass)
        };
    }
    
    return nearestData;
}

/**
 * 估算波特尔等级
 * @param {number} lat - 纬度
 * @param {number} lng - 经度
 * @returns {number} 估算的波特尔等级
 */
function estimateBortleClass(lat, lng) {
    // 简单的基于地理位置的估算
    if (lat >= 18 && lat <= 54 && lng >= 73 && lng <= 135) {
        // 中国大陆
        if (lng >= 110 && lng <= 125 && lat >= 30 && lat <= 42) {
            return 7; // 东部发达地区
        } else if (lng >= 75 && lng <= 95 && lat >= 35 && lat <= 50) {
            return 2; // 西部偏远地区
        } else {
            return 5; // 其他地区
        }
    } else {
        return 4; // 国外地区默认值
    }
}

/**
 * 初始化搜索功能
 */
function initializeSearch() {
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;
    
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            // In telescope mode, celestial search is handled by initTelescopeMode
            if (isTelescopeMode) return;
            const query = this.value.trim();
            if (query) {
                searchLocation(query);
            }
        }
    });
}

/**
 * 搜索位置
 * @param {string} query - 搜索查询
 */
async function searchLocation(query) {
    try {
        // 使用Nominatim API进行地理编码
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`, {
            headers: {
                'User-Agent': 'StargazingPlaceFinder/0.6 (zhao.gong@outlook.com)'
            }
        });
        const results = await response.json();
        
        if (results && results.length > 0) {
            const result = results[0];
            const lat = parseFloat(result.lat);
            const lng = parseFloat(result.lon);
            
            map.setView([lat, lng], 10);
            
            // 添加标记
            L.marker([lat, lng])
                .addTo(map)
                .bindPopup(`${result.display_name}<br>${getText('coordinates')}: ${lat.toFixed(4)}, ${lng.toFixed(4)}`)
                .openPopup();
        } else {
            showToast('未找到该位置，请尝试其他搜索词', 'info');
        }
    } catch (error) {
        console.error('搜索失败:', error);
        showToast('搜索失败，请检查网络连接', 'error');
    }
}

/**
 * 更新图例
 */
function updateLegend() {
    const legendPanel = document.querySelector('.legend-panel');
    if (!legendPanel) return;
    
    let legendHTML = `<h3>${getText('legend')}</h3>`;
    
    for (let i = 1; i <= 9; i++) {
        const color = getBortleColor(i);
        const description = getText(`bortleDescriptions.${i}`);
        
        legendHTML += `
            <div class="legend-item">
                <div class="legend-color" style="background-color: ${color};"></div>
                <div class="legend-text">${description}</div>
            </div>
        `;
    }
    
    legendPanel.innerHTML = legendHTML;
}

/**
 * 应用程序初始化
 */
function initializeApp() {
    console.log('正在初始化观星地点查找器应用...');
    
    // 自动检测用户语言偏好
    currentLanguage = detectUserLanguage();
    console.log(`检测到用户语言偏好: ${currentLanguage}`);
    
    // 初始化多语言支持
    updateLanguageElements();
    
    // 初始化地图
    initializeMap();
    
    // 初始化搜索功能
    initializeSearch();
    
    // 绑定语言切换按钮事件
    const languageBtn = document.getElementById('language-btn');
    if (languageBtn) {
        languageBtn.addEventListener('click', toggleLanguage);
        console.log('语言切换按钮事件已绑定');
    }
    
    // 添加键盘快捷键支持 (Ctrl+J 或 Cmd+J 切换语言)
    document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 'j') {
            event.preventDefault();
            toggleLanguage();
        }
    });
    
    // 初始化完成后隐藏加载覆盖层，保留核心交互控件
    setTimeout(() => {
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.classList.add('hidden');
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
            }, 500);
        }

        // 初始隐藏仅数据驱动的面板（无数据时不展示）
        const statsPanel = document.querySelector('.stats-panel');
        if (statsPanel) statsPanel.style.display = 'none';

        const infoPanel = document.querySelector('.info-panel');
        if (infoPanel) infoPanel.style.display = 'none';

        console.log('应用初始化完成');
    }, 1000);
}

// ==================== 观星区域选择器功能 ====================

/**
 * 初始化绘制控件
 */
function initializeDrawControls() {
    drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

    drawControl = new L.Control.Draw({
        position: 'topleft',
        draw: {
            polygon: false,
            rectangle: {
                shapeOptions: {
                    color: '#4a90e2',
                    weight: 3,
                    opacity: 0.8,
                    fillOpacity: 0.2
                }
            },
            polyline: false,
            circle: false,
            marker: false,
            circlemarker: false
        },
        edit: false
    });

    map.addControl(drawControl);
    bindDrawEventListeners();
}

/**
 * 绑定绘制事件监听器
 */
function bindDrawEventListeners() {
    map.on(L.Draw.Event.CREATED, function(e) {
        const layer = e.layer;
        
        // 清除之前的多边形
        drawnItems.clearLayers();
        
        // 添加新的多边形
        drawnItems.addLayer(layer);
        currentPolygon = layer;
        
        // 启用分析按钮
        const analyzeBtn = document.getElementById('analyze-button');
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
        }
        
        updateStatus('已绘制分析区域，点击"分析观星区域"开始分析', 'success');
    });

    map.on(L.Draw.Event.DELETED, function(e) {
        currentPolygon = null;
        
        // 禁用分析按钮
        const analyzeBtn = document.getElementById('analyze-button');
        if (analyzeBtn) {
            analyzeBtn.disabled = true;
        }
        
        // 清除分析结果
        clearAnalysisResults();
        updateStatus('已清除绘制区域', 'success');
    });
}

/**
 * 分析观星区域
 */
async function analyzeStargazingArea() {
    if (!currentPolygon) {
        updateStatus('请先绘制一个分析区域', 'error');
        return;
    }

    const analyzeBtn = document.getElementById('analyze-button');
    if (analyzeBtn) {
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="loading-spinner"></span>分析中...';
    }

    updateStatus('正在分析观星区域...', 'loading');

    try {
        // 获取多边形坐标
        const coordinates = currentPolygon.getLatLngs()[0].map(latlng => [latlng.lng, latlng.lat]);
        
        // 计算边界框
        const lats = coordinates.map(coord => coord[1]);
        const lngs = coordinates.map(coord => coord[0]);
        const bbox = {
            south: Math.min(...lats),
            west: Math.min(...lngs),
            north: Math.max(...lats),
            east: Math.max(...lngs)
        };
        
        // 获取表单数据
        const maxLocations = parseInt(document.getElementById('max-locations').value) || 30;
        const transportMode = document.getElementById('network-type').value || 'drive';
        const analyzeLightPollution = document.getElementById('include-light-pollution').checked;
        const checkRoadConnectivity = document.getElementById('include-road-connectivity').checked;

        // 构建请求数据
        var requestData = {
            bbox: bbox,
            max_locations: maxLocations,
            network_type: transportMode,
            include_light_pollution: analyzeLightPollution,
            include_road_connectivity: checkRoadConnectivity,
            road_radius_km: 10.0,
            max_distance_to_road_km: 0.2
        };

        console.log('发送分析请求:', requestData);

        // 发送API请求
        const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.analyze}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API请求失败: ${response.status} - ${errorText}`);
        }

        const result = await response.json();
        console.log('分析结果:', result);

        // 显示分析结果
        displayAnalysisResults(result);
        updateStatus(`分析完成，找到 ${result.locations?.length || 0} 个观星地点`, 'success');

    } catch (error) {
        console.error('分析失败:', error);
        updateStatus(`分析失败: ${error.message}`, 'error');
    } finally {
        // 恢复按钮状态
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '分析观星区域';
        }
    }
}

/**
 * 显示分析结果
 */
function displayAnalysisResults(result) {
    // 清除之前的结果
    clearAnalysisResults();
    
    if (!result.locations || result.locations.length === 0) {
        updateStatus('未找到合适的观星地点', 'error');
        return;
    }

    // 保存结果
    analysisResults = result.locations;

    // 在地图上添加标记
    analysisResults.forEach(function (location, index) {
        try {
            var marker = createStargazingMarker(location);
            drawnItems.addLayer(marker);
        } catch (err) {
            console.error('创建标记失败:', location.name, err);
        }
    });

    // 显示结果面板 - 已注释，只显示标记
    // showResultsPanel(result);

    // 调整地图视图以包含所有标记
    if (analysisResults.length > 0) {
        const group = new L.featureGroup(drawnItems.getLayers());
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

/**
 * 创建观星地点标记
 * 根据分析结果创建带有详细信息的地图标记
 */
function createStargazingMarker(location) {
    const { 
        lat, lon, stargazing_score, name, elevation,
        light_pollution_level, light_pollution_brightness,
        road_accessible, distance_to_road_km, recommendation_level,
        analysis_notes, prominence, distance_to_nearest_town,
        nearest_town_name
    } = location;
    
    // 使用stargazing_score而不是score
    const score = stargazing_score || 0;
    
    // 根据评分选择标记样式
    let styleKey = 'poor';
    if (score >= 8) styleKey = 'excellent';
    else if (score >= 6) styleKey = 'good';
    else if (score >= 4) styleKey = 'fair';
    
    const style = MARKER_STYLES[styleKey];
    
    // 创建自定义图标
    const icon = L.divIcon({
        className: style.className,
        iconSize: style.iconSize,
        iconAnchor: style.iconAnchor,
        html: `<div class="marker-inner">⭐</div>`
    });
    
    // 创建标记
    const marker = L.marker([lat, lon], { icon });
    
    // 构建详细的弹出窗口内容
    const popupContent = `
        <div class="stargazing-popup">
            <div class="popup-header">
                <h4>${name || '观星地点'}</h4>
                <div class="score-badge ${styleKey}">${score.toFixed(1)}/10</div>
            </div>
            
            <div class="popup-content">
                <div class="info-section">
                    <h5>📍 位置信息</h5>
                    <p><strong>坐标:</strong> ${lat.toFixed(4)}, ${lon.toFixed(4)}</p>
                    <p><strong>海拔:</strong> ${elevation ? elevation.toFixed(0) + 'm' : '未知'}</p>
                    ${prominence ? `<p><strong>地形突出度:</strong> ${prominence.toFixed(0)}m</p>` : ''}
                    ${nearest_town_name ? `<p><strong>最近城镇:</strong> ${nearest_town_name} (${distance_to_nearest_town ? distance_to_nearest_town.toFixed(1) + 'km' : '未知距离'})</p>` : ''}
                </div>
                
                <div class="info-section">
                    <h5>🌃 光污染情况</h5>
                    ${light_pollution_level ? `<p><strong>光污染等级:</strong> ${light_pollution_level}</p>` : ''}
                    ${light_pollution_brightness ? `<p><strong>亮度值:</strong> ${light_pollution_brightness}</p>` : ''}
                </div>
                
                <div class="info-section">
                    <h5>🚗 交通可达性</h5>
                    <p><strong>道路可达:</strong> ${road_accessible ? '是' : '否'}</p>
                    ${distance_to_road_km ? `<p><strong>距离道路:</strong> ${distance_to_road_km.toFixed(1)}km</p>` : ''}
                </div>
                
                ${recommendation_level ? `
                <div class="info-section">
                    <h5>⭐ 推荐等级</h5>
                    <p class="recommendation-level ${recommendation_level.toLowerCase()}">${recommendation_level}</p>
                </div>
                ` : ''}
                
                ${analysis_notes ? `
                <div class="info-section">
                    <h5>📝 分析说明</h5>
                    <p class="analysis-notes">${analysis_notes}</p>
                </div>
                ` : ''}
            </div>
        </div>
    `;
    
    marker.bindPopup(popupContent, {
        maxWidth: 350,
        className: 'stargazing-popup-container'
    });
    
    return marker;
}

/**
 * 显示结果面板
 */
/**
 * 显示分析结果面板
 * 展示观星地点分析的统计信息和详细列表
 */
function showResultsPanel(result) {
    let panel = document.getElementById('results-panel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'results-panel';
        panel.className = 'results-panel';
        document.body.appendChild(panel);
    }
    
    const locations = result.locations || [];
    const summary = result.summary || {};
    
    // 计算统计信息
    const stats = calculateLocationStats(locations);
    
    panel.innerHTML = `
        <div class="results-header">
            <h4>🌟 观星地点分析结果</h4>
            <button class="close-btn" onclick="clearAnalysisResults()">×</button>
        </div>
        
        <div class="summary-stats">
            <div class="stat-item">
                <div class="stat-value">${locations.length}</div>
                <div class="stat-label">观星地点</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">${stats.avgScore}</div>
                <div class="stat-label">平均评分</div>
            </div>
            <div class="stat-item excellent">
                <div class="stat-value">${stats.excellentCount}</div>
                <div class="stat-label">优秀地点</div>
            </div>
            <div class="stat-item good">
                <div class="stat-value">${stats.goodCount}</div>
                <div class="stat-label">良好地点</div>
            </div>
        </div>
        
        <div class="quality-distribution">
            <h5>📊 质量分布</h5>
            <div class="distribution-bars">
                <div class="bar-item">
                    <span class="bar-label">优秀 (8-10分)</span>
                    <div class="bar-container">
                        <div class="bar excellent" style="width: ${stats.excellentPercent}%"></div>
                        <span class="bar-text">${stats.excellentCount}</span>
                    </div>
                </div>
                <div class="bar-item">
                    <span class="bar-label">良好 (6-8分)</span>
                    <div class="bar-container">
                        <div class="bar good" style="width: ${stats.goodPercent}%"></div>
                        <span class="bar-text">${stats.goodCount}</span>
                    </div>
                </div>
                <div class="bar-item">
                    <span class="bar-label">一般 (4-6分)</span>
                    <div class="bar-container">
                        <div class="bar fair" style="width: ${stats.fairPercent}%"></div>
                        <span class="bar-text">${stats.fairCount}</span>
                    </div>
                </div>
                <div class="bar-item">
                    <span class="bar-label">较差 (<4分)</span>
                    <div class="bar-container">
                        <div class="bar poor" style="width: ${stats.poorPercent}%"></div>
                        <span class="bar-text">${stats.poorCount}</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="locations-list">
            <h5>🎯 推荐地点 (前5名)</h5>
            ${locations.slice(0, 5).map((location, index) => {
                const score = location.stargazing_score || 0;
                const scoreClass = score >= 8 ? 'excellent' : score >= 6 ? 'good' : score >= 4 ? 'fair' : 'poor';
                return `
                    <div class="location-item ${scoreClass}" onclick="focusOnLocation(${location.lat}, ${location.lon})">
                        <div class="location-header">
                            <div class="location-name">${location.name || `观星地点 ${index + 1}`}</div>
                            <div class="location-score ${scoreClass}">${score.toFixed(1)}/10</div>
                        </div>
                        <div class="location-details">
                            <div class="detail-row">
                                <span class="detail-icon">📍</span>
                                <span>坐标: ${location.lat.toFixed(4)}, ${location.lon.toFixed(4)}</span>
                            </div>
                            ${location.elevation ? `
                            <div class="detail-row">
                                <span class="detail-icon">⛰️</span>
                                <span>海拔: ${location.elevation.toFixed(0)}m</span>
                            </div>
                            ` : ''}
                            ${location.light_pollution_level ? `
                            <div class="detail-row">
                                <span class="detail-icon">🌃</span>
                                <span>光污染: ${location.light_pollution_level}</span>
                            </div>
                            ` : ''}
                            ${location.recommendation_level ? `
                            <div class="detail-row">
                                <span class="detail-icon">⭐</span>
                                <span>推荐: ${location.recommendation_level}</span>
                            </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
    
    panel.style.display = 'block';
    resultsPanel = panel;
}

/**
 * 计算观星地点统计信息
 */
function calculateLocationStats(locations) {
    if (!locations || locations.length === 0) {
        return {
            avgScore: 'N/A',
            excellentCount: 0,
            goodCount: 0,
            fairCount: 0,
            poorCount: 0,
            excellentPercent: 0,
            goodPercent: 0,
            fairPercent: 0,
            poorPercent: 0
        };
    }
    
    let excellentCount = 0;
    let goodCount = 0;
    let fairCount = 0;
    let poorCount = 0;
    let totalScore = 0;
    
    locations.forEach(location => {
        const score = location.stargazing_score || 0;
        totalScore += score;
        
        if (score >= 8) excellentCount++;
        else if (score >= 6) goodCount++;
        else if (score >= 4) fairCount++;
        else poorCount++;
    });
    
    const total = locations.length;
    const avgScore = (totalScore / total).toFixed(1);
    
    return {
        avgScore,
        excellentCount,
        goodCount,
        fairCount,
        poorCount,
        excellentPercent: total > 0 ? (excellentCount / total * 100).toFixed(1) : 0,
        goodPercent: total > 0 ? (goodCount / total * 100).toFixed(1) : 0,
        fairPercent: total > 0 ? (fairCount / total * 100).toFixed(1) : 0,
        poorPercent: total > 0 ? (poorCount / total * 100).toFixed(1) : 0
    };
}

/**
 * 聚焦到指定的观星地点
 */
function focusOnLocation(lat, lng) {
    if (map) {
        map.setView([lat, lng], 15);
        // 找到对应的标记并打开弹出窗口
        drawnItems.eachLayer(layer => {
            if (layer.getLatLng && layer.getLatLng().lat === lat && layer.getLatLng().lng === lng) {
                layer.openPopup();
            }
        });
    }
}

/**
 * 清除分析结果
 */
function clearAnalysisResults() {
    // 清除标记（保留多边形）
    if (drawnItems) {
        drawnItems.eachLayer(layer => {
            if (layer !== currentPolygon) {
                drawnItems.removeLayer(layer);
            }
        });
    }
    
    // 隐藏结果面板
    if (resultsPanel) {
        resultsPanel.style.display = 'none';
    }
    
    // 清空结果数组
    analysisResults = [];
}

/**
 * 清除所有内容
 */
function clearAll() {
    // 清除绘制的图层
    if (drawnItems) {
        drawnItems.clearLayers();
    }
    
    // 重置变量
    currentPolygon = null;
    analysisResults = [];
    
    // 隐藏结果面板
    if (resultsPanel) {
        resultsPanel.style.display = 'none';
    }
    
    // 禁用分析按钮
    const analyzeBtn = document.getElementById('analyze-button');
    if (analyzeBtn) {
        analyzeBtn.disabled = true;
    }
    
    // 确保绘制控件仍然可用
    if (isAnalysisMode && drawControl && map) {
        if (!map.hasControl(drawControl)) {
            map.addControl(drawControl);
        }
    }
    
    updateStatus('已清除所有内容', 'success');
}

/**
 * 更新状态指示器
 */
function updateStatus(message, type = 'info') {
    let indicator = document.getElementById('status-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'status-indicator';
        indicator.className = 'status-indicator';
        document.body.appendChild(indicator);
    }
    
    indicator.textContent = message;
    indicator.className = `status-indicator ${type}`;
    indicator.style.display = 'block';
    statusIndicator = indicator;
    
    // 3秒后自动隐藏成功和错误消息
    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            if (indicator.textContent === message) {
                indicator.style.display = 'none';
            }
        }, 3000);
    } else {
        indicator.style.display = 'block';
    }
}

/**
 * 切换模式
 */
function toggleMode() {
    isAnalysisMode = !isAnalysisMode;
    
    const modeBtn = document.getElementById('mode-toggle-btn');
    const controlPanel = document.querySelector('.control-panel');
    
    if (isAnalysisMode) {
        // 切换到分析模式
        modeBtn.textContent = '切换到浏览模式';
        modeBtn.classList.add('active');
        controlPanel.style.display = 'block';
        
        // 初始化绘制控件
        if (!drawControl) {
            initializeDrawControls();
        } else {
            // 确保绘制控件已添加到地图
            if (map && !map.hasControl(drawControl)) {
                map.addControl(drawControl);
            }
        }
        
        updateStatus('已切换到分析模式，请绘制分析区域', 'info');
    } else {
        // 切换到浏览模式
        modeBtn.textContent = '切换到分析模式';
        modeBtn.classList.remove('active');
        controlPanel.style.display = 'none';
        
        // 移除绘制控件
        if (window._drawBtn && map && map.hasControl(window._drawBtn)) {
            map.removeControl(window._drawBtn);
        }
        
        // 清除所有分析内容
        clearAll();

        // Hide status
        var statusEl = document.querySelector('.status-indicator');
        if (statusEl) statusEl.style.display = 'none';
    }
}

/**
 * 检查API健康状态
 */
async function checkApiHealth() {
    try {
        const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.health}`);
        if (response.ok) {
            const data = await response.json();
            console.log('API健康检查通过:', data);
            return true;
        }
    } catch (error) {
        console.warn('API健康检查失败:', error);
    }
    return false;
}

/**
 * 初始化观星区域选择器
 */
function initializeStargazingSelector() {
    // 绑定按钮事件
    const analyzeBtn = document.getElementById('analyze-button');
    const clearBtn = document.getElementById('clear-button');
    const modeToggleBtn = document.getElementById('mode-toggle-btn');
    
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeStargazingArea);
        analyzeBtn.disabled = true; // 初始状态禁用
    }
    
    if (clearBtn) {
        clearBtn.addEventListener('click', clearAll);
    }
    
    if (modeToggleBtn) {
        modeToggleBtn.addEventListener('click', toggleMode);
    }
    
    // 初始隐藏控制面板
    const controlPanel = document.querySelector('.control-panel');
    if (controlPanel) {
        controlPanel.style.display = 'none';
    }
    
    // 检查API健康状态
    checkApiHealth();
}

// ═══════════════════════════════════════════════════════════════════════
//  Telescope mode
// ═══════════════════════════════════════════════════════════════════════

let isTelescopeMode = false;
let aladinInstance = null;
let aladinInitialized = false;
let aladinInitPromise = null;
let aladinScriptLoaded = false;
let aladinScriptPromise = null;

// FOV canvas overlay (drawn via CSS on top of Aladin, using world2pix)
let fovCanvas = null;
let fovCanvasCtx = null;
let fovAnimFrame = null;

/**
 * Dynamically load the Aladin Lite script (only when telescope mode is first
 * activated).  Returns a promise that resolves when the A global is ready.
 */
function loadAladinScript() {
    if (aladinScriptLoaded) return aladinScriptPromise;
    if (aladinScriptPromise) return aladinScriptPromise;

    aladinScriptPromise = new Promise(function (resolve, reject) {
        var script = document.createElement('script');
        script.src = 'https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js';
        script.onload = function () {
            aladinScriptLoaded = true;
            resolve();
        };
        script.onerror = function () {
            reject(new Error('Aladin Lite 脚本加载失败'));
        };
        document.head.appendChild(script);
    });
    return aladinScriptPromise;
}

// 设备预设
const TELESCOPE_PRESETS = {
    'custom': { name: '自定义' },
    'seestar-s50': {
        name: 'Seestar S50',
        focalLength: 250,
        sensorWidth: 7.6,
        sensorHeight: 5.7,
    },
    'redcat51-asi2600': {
        name: 'RedCat51 + ASI2600',
        focalLength: 250,
        sensorWidth: 23.5,
        sensorHeight: 15.7,
    },
    'fullframe-200mm': {
        name: '全画幅 + 200mm',
        focalLength: 200,
        sensorWidth: 36,
        sensorHeight: 24,
    },
    'sct14-reducer': {
        name: '14" SCT + 减焦',
        focalLength: 2500,
        sensorWidth: 23.5,
        sensorHeight: 15.7,
    },
};

/**
 * Calculate FOV angles from sensor dimensions and focal length.
 * @returns {{ fovW: number, fovH: number }} FOV width and height in degrees
 */
function calculateFov() {
    const focalLength = parseFloat(document.getElementById('telescope-focal-length').value) || 250;
    const sensorW = parseFloat(document.getElementById('telescope-sensor-width').value) || 23.5;
    const sensorH = parseFloat(document.getElementById('telescope-sensor-height').value) || 15.7;

    // FOV = 2 * atan(sensor_dim / (2 * focal_length))
    const fovW_rad = 2 * Math.atan(sensorW / (2 * focalLength));
    const fovH_rad = 2 * Math.atan(sensorH / (2 * focalLength));

    return {
        fovW: (fovW_rad * 180) / Math.PI,
        fovH: (fovH_rad * 180) / Math.PI,
    };
}

/**
 * Create the transparent canvas overlay that sits on top of Aladin.
 */
function setupFovCanvas() {
    const container = document.getElementById('aladin-lite-div');
    if (!container) return;

    // Remove old canvas if any
    if (fovCanvas && fovCanvas.parentNode) {
        fovCanvas.parentNode.removeChild(fovCanvas);
    }

    fovCanvas = document.createElement('canvas');
    fovCanvas.id = 'fov-canvas';
    fovCanvas.style.cssText =
        'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:10;';
    container.appendChild(fovCanvas);
    fovCanvasCtx = fovCanvas.getContext('2d');
}

/**
 * Draw the FOV rectangle on the canvas overlay using world2pix.
 */
function updateFovOverlay() {
    if (!aladinInstance) return;

    // Check if FOV overlay is enabled
    var showFov = document.getElementById('show-fov-checkbox');
    var fovEnabled = showFov ? showFov.checked : true;

    // Update FOV display text regardless
    var { fovW, fovH } = calculateFov();
    var display = document.getElementById('fov-display');
    if (display) {
        display.textContent = fovW.toFixed(1) + '° × ' + fovH.toFixed(1) + '°';
    }

    // Clear and exit if FOV is disabled
    if (!fovEnabled) {
        if (fovCanvas && fovCanvasCtx) {
            var r = fovCanvas.getBoundingClientRect();
            fovCanvasCtx.clearRect(0, 0, r.width, r.height);
        }
        return;
    }

    if (!fovCanvasCtx) setupFovCanvas();
    if (!fovCanvasCtx) return;

    const canvas = fovCanvas;
    const ctx = fovCanvasCtx;

    // Match canvas resolution to display size
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // Clear
    ctx.clearRect(0, 0, rect.width, rect.height);
    if (rect.width === 0 || rect.height === 0) return;

    var coords = aladinInstance.getRaDec();
    var raCenter = coords[0], decCenter = coords[1];
    if (raCenter == null || decCenter == null) return;
    if (isNaN(raCenter) || isNaN(decCenter)) return;

    // Build FOV corners in celestial coords
    const decRad = (decCenter * Math.PI) / 180;
    const cosDec = Math.max(Math.cos(decRad), 0.01);
    const halfW = (fovW / 2) / cosDec;
    const halfH = fovH / 2;

    const wrapRa = (ra) => ((ra % 360) + 360) % 360;
    const corners = [
        [wrapRa(raCenter - halfW), decCenter + halfH],
        [wrapRa(raCenter + halfW), decCenter + halfH],
        [wrapRa(raCenter + halfW), decCenter - halfH],
        [wrapRa(raCenter - halfW), decCenter - halfH],
    ];

    // Convert celestial to screen coords
    const screenPts = [];
    for (let i = 0; i < 4; i++) {
        const pt = aladinInstance.world2pix(corners[i][0], corners[i][1]);
        if (!pt) { screenPts.length = 0; break; }
        screenPts.push(pt);
    }
    if (screenPts.length < 4) return;

    // Apply screen-space rotation
    var rotSlider = document.getElementById('telescope-rotation');
    var rotDeg = rotSlider ? parseFloat(rotSlider.value) || 0 : 0;
    if (Math.abs(rotDeg) > 0.01) {
        var rotRad = (-rotDeg * Math.PI) / 180;  // negative = clockwise
        var cosR = Math.cos(rotRad), sinR = Math.sin(rotRad);
        // Compute screen center
        var scx = 0, scy = 0;
        for (var j = 0; j < 4; j++) { scx += screenPts[j][0]; scy += screenPts[j][1]; }
        scx /= 4; scy /= 4;
        // Rotate each corner around center
        for (var k = 0; k < 4; k++) {
            var dx = screenPts[k][0] - scx;
            var dy = screenPts[k][1] - scy;
            screenPts[k] = [scx + dx * cosR - dy * sinR, scy + dx * sinR + dy * cosR];
        }
    }

    // Draw filled semi-transparent rectangle
    ctx.beginPath();
    ctx.moveTo(screenPts[0][0], screenPts[0][1]);
    for (let i = 1; i < 4; i++) {
        ctx.lineTo(screenPts[i][0], screenPts[i][1]);
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(74, 144, 226, 0.12)';
    ctx.fill();
    ctx.strokeStyle = '#4a90e2';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Draw corner circles
    for (let i = 0; i < 4; i++) {
        ctx.beginPath();
        ctx.arc(screenPts[i][0], screenPts[i][1], 5, 0, Math.PI * 2);
        ctx.fillStyle = '#87ceeb';
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    // Crosshair at center
    const centerPt = aladinInstance.world2pix(raCenter, decCenter);
    if (centerPt) {
        const cx = centerPt[0], cy = centerPt[1];
        ctx.strokeStyle = 'rgba(255,255,255,0.4)';
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(cx - 12, cy); ctx.lineTo(cx + 12, cy); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(cx, cy - 12); ctx.lineTo(cx, cy + 12); ctx.stroke();
    }

    // Draw FOV label above the topmost edge
    if (screenPts.length === 4) {
        // Find the top two corners by screen Y (lowest Y = highest on screen)
        var sorted = screenPts.slice().sort(function (a, b) { return a[1] - b[1]; });
        var midTopX = (sorted[0][0] + sorted[1][0]) / 2;
        var midTopY = sorted[0][1] - 14;
        ctx.font = '12px sans-serif';
        ctx.fillStyle = '#87ceeb';
        ctx.textAlign = 'center';
        ctx.fillText(fovW.toFixed(1) + '° × ' + fovH.toFixed(1) + '°', midTopX, Math.max(14, midTopY));
    }

}

/**
 * Apply a preset configuration to the input fields.
 */
function applyPreset(presetKey) {
    const preset = TELESCOPE_PRESETS[presetKey];
    if (!preset || presetKey === 'custom') return;

    document.getElementById('telescope-focal-length').value = preset.focalLength;
    document.getElementById('telescope-sensor-width').value = preset.sensorWidth;
    document.getElementById('telescope-sensor-height').value = preset.sensorHeight;
}

/**
 * Initialize Aladin Lite (lazy — only when telescope mode is first activated).
 * Returns a promise that resolves when Aladin is ready.
 */
function ensureAladinReady() {
    if (aladinInitialized) {
        return aladinInitPromise;
    }
    if (aladinInitPromise) {
        return aladinInitPromise;
    }

    aladinInitPromise = loadAladinScript().then(function () {
        return A.init;
    }).then(function () {
        aladinInstance = A.aladin('#aladin-lite-div', {
            target: 'M 31',
            fov: 2.5,
            survey: 'P/DSS2/color',
            cooFrame: 'equatorial',
            showCooGridControl: true,
            showSimbadPointerControl: true,
            showProjectionControl: false,
            showFullscreenControl: false,
        });

        // Update FOV when view changes — capture DOM events before Aladin's canvas
        var aladinDiv = document.getElementById('aladin-lite-div');
        var scheduleFovUpdate = function () {
            setTimeout(function () { updateFovOverlay(); }, 100);
        };
        if (aladinDiv) {
            aladinDiv.addEventListener('pointerup', scheduleFovUpdate, true);
            aladinDiv.addEventListener('wheel', scheduleFovUpdate, true);
            aladinDiv.addEventListener('touchend', scheduleFovUpdate, true);
        }

        aladinInitialized = true;
        return aladinInstance;
    });

    return aladinInitPromise;
}

/**
 * Wire up telescope panel interactions (runs once at page load).
 */
function initTelescopeMode() {
    // ── Telescope preset selector ──
    const presetSelect = document.getElementById('telescope-preset');
    if (presetSelect) {
        presetSelect.addEventListener('change', function () {
            applyPreset(this.value);
            updateFovOverlay();
        });
    }

    // ── Manual input changes ──
    ['telescope-focal-length', 'telescope-sensor-width', 'telescope-sensor-height']
        .forEach(function (id) {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('input', function () {
                    const presetSelect = document.getElementById('telescope-preset');
                    if (presetSelect) presetSelect.value = 'custom';
                    updateFovOverlay();
                });
            }
        });

    // ── Aladin object search ──
    // ── Celestial search via the unified search bar ──
    var searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keypress', function (e) {
            if (e.key !== 'Enter' || !isTelescopeMode || !aladinInstance) return;
            var query = this.value.trim();
            if (!query) return;
            aladinInstance.gotoObject(query, {
                success: function () {
                    setTimeout(function () { updateFovOverlay(); }, 300);
                },
                error: function () {
                    showToast('未找到天体: ' + query, 'error');
                },
            });
        });
    }

    // ── Rotation slider ──
    var rotSlider = document.getElementById('telescope-rotation');
    var rotLabel = document.getElementById('rotation-value');
    if (rotSlider) {
        rotSlider.addEventListener('input', function () {
            if (rotLabel) rotLabel.textContent = this.value + '°';
            updateFovOverlay();
        });
    }

    // ── Show FOV checkbox ──
    var showFovCb = document.getElementById('show-fov-checkbox');
    if (showFovCb) {
        showFovCb.addEventListener('change', function () {
            updateFovOverlay();
        });
    }

    // ── Collapsible panel ──
    var panelHeader = document.getElementById('telescope-panel-header');
    var telescopePanel = document.getElementById('telescope-control-panel');
    if (panelHeader && telescopePanel) {
        panelHeader.addEventListener('click', function () {
            telescopePanel.classList.toggle('collapsed');
        });
    }

    // ── Telescope toggle button ──
    const telescopeBtn = document.getElementById('telescope-toggle-btn');
    if (telescopeBtn) {
        telescopeBtn.addEventListener('click', toggleTelescopeMode);
    }
}

/**
 * Toggle between map mode and telescope (sky chart) mode.
 */
function toggleTelescopeMode() {
    isTelescopeMode = !isTelescopeMode;

    const mapEl = document.getElementById('map');
    const aladinContainer = document.getElementById('aladin-container');
    const telescopePanel = document.getElementById('telescope-control-panel');
    const telescopeBtn = document.getElementById('telescope-toggle-btn');
    // Map-only panels — hide in telescope mode, restore in map mode
    const mapPanelSelectors = [
        '.bortle-bar-container',
        '.stats-panel',
        '.info-panel',
        '.status-indicator',
        '.results-panel',
        '.control-panel',
    ];

    if (isTelescopeMode) {
        // Switch to telescope mode
        if (mapEl) mapEl.style.display = 'none';
        if (aladinContainer) aladinContainer.style.display = 'block';
        if (telescopePanel) telescopePanel.style.display = 'block';
        if (telescopeBtn) {
            telescopeBtn.textContent = '🗺️ 返回地图';
            telescopeBtn.classList.add('active');
        }
        const modeBtn = document.getElementById('mode-toggle-btn');
        if (modeBtn) modeBtn.style.display = 'none';

        // Hide the separate aladin search (we reuse the main search bar)
        var aladinSearch = document.getElementById('aladin-search-container');
        if (aladinSearch) aladinSearch.style.display = 'none';

        // Remove analysis draw control while in telescope mode
        if (drawControl && map && map.hasControl(drawControl)) {
            map.removeControl(drawControl);
        }

        // Repurpose main search bar for celestial objects
        var searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.dataset.mapPlaceholder = searchInput.placeholder;
            searchInput.placeholder = '搜索天体 (如 M31, M42, NGC 7000)...';
        }

        // Hide all map-specific panels
        mapPanelSelectors.forEach(function (sel) {
            var el = document.querySelector(sel);
            if (el) el.style.display = 'none';
        });

        // Lazy-init Aladin on first activation
        ensureAladinReady().then(function () {
            setTimeout(function () { updateFovOverlay(); }, 400);
        }).catch(function (err) {
            console.error('Aladin init failed:', err);
            showToast('星图加载失败，请刷新页面重试', 'error');
        });
    } else {
        // Switch back to map mode
        if (mapEl) mapEl.style.display = 'block';
        if (aladinContainer) aladinContainer.style.display = 'none';
        if (telescopePanel) telescopePanel.style.display = 'none';
        if (telescopeBtn) {
            telescopeBtn.textContent = '🔭 望远镜模式';
            telescopeBtn.classList.remove('active');
        }
        if (document.getElementById('mode-toggle-btn')) {
            document.getElementById('mode-toggle-btn').style.display = '';
        }

        // Restore analysis draw control if in analysis mode
        if (isAnalysisMode && drawControl && map && !map.hasControl(drawControl)) {
            map.addControl(drawControl);
        }

        // Restore search bar
        var searchInput = document.getElementById('search-input');
        if (searchInput && searchInput.dataset.mapPlaceholder) {
            searchInput.placeholder = searchInput.dataset.mapPlaceholder;
        }

        // Restore map panels
        mapPanelSelectors.forEach(function (sel) {
            var el = document.querySelector(sel);
            if (el) el.style.display = '';
        });

        // Clean up FOV canvas
        if (fovCanvas && fovCanvas.parentNode) {
            fovCanvas.parentNode.removeChild(fovCanvas);
            fovCanvas = null;
            fovCanvasCtx = null;
        }
    }
}

// ==================== 应用初始化 ====================

// 初始化应用
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initializeApp();
        initializeStargazingSelector();
        initTelescopeMode();
    });
} else {
    initializeApp();
    initializeStargazingSelector();
    initTelescopeMode();
}
