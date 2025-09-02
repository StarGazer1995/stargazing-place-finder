// 全局变量定义
let map;
let currentOverlay = null;
let currentImageLayers = [];
let dataCache = new Map();
let imageCache = new Map();
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

// API配置
const API_CONFIG = {
    baseUrl: 'http://127.0.0.1:5001',
    endpoints: {
        analyze: '/api/analyze_stargazing_area',
        health: '/api/health',
        lightPollution: '/api/light_pollution_images'
    }
};

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
    
    const legendPanelTitle = document.querySelector('.legend-panel h3');
    if (legendPanelTitle) {
        legendPanelTitle.textContent = getText('legend');
    }
    
    // 更新图例
    updateLegend();
    
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
 * 计算自适应方块大小
 * @param {number} zoom - 地图缩放级别
 * @returns {number} 方块大小
 */
function getAdaptiveSquareSize(zoom) {
    // 根据缩放级别调整方块大小
    if (zoom <= 6) return 0.1;
    if (zoom <= 8) return 0.05;
    if (zoom <= 10) return 0.02;
    if (zoom <= 12) return 0.01;
    return 0.005;
}

/**
 * 获取光污染数据
 * @param {Object} bounds - 地图边界
 * @param {number} zoom - 缩放级别
 * @returns {Promise<Array>} 光污染数据数组
 */
async function getLightPollutionData(bounds, zoom) {
    const cacheKey = `${bounds.north}_${bounds.south}_${bounds.east}_${bounds.west}_${zoom}`;
    
    // 检查缓存
    if (dataCache.has(cacheKey)) {
        return dataCache.get(cacheKey);
    }
    
    try {
        // 这里应该是实际的API调用
        // const response = await fetch(`/api/light-pollution?bounds=${JSON.stringify(bounds)}&zoom=${zoom}`);
        // const data = await response.json();
        
        // 模拟API调用延迟
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // 使用模拟数据
        const data = generateMockData(bounds, zoom);
        
        // 缓存数据
        dataCache.set(cacheKey, data);
        
        return data;
    } catch (error) {
        console.error('获取光污染数据失败:', error);
        // 返回模拟数据作为后备
        const mockData = generateMockData(bounds, zoom);
        dataCache.set(cacheKey, mockData);
        return mockData;
    }
}

/**
 * 生成模拟光污染数据
 * @param {Object} bounds - 地图边界
 * @param {number} zoom - 缩放级别
 * @returns {Array} 模拟数据数组
 */
function generateMockData(bounds, zoom) {
    const data = [];
    const squareSize = getAdaptiveSquareSize(zoom);
    const density = Math.max(1, Math.floor(20 - zoom)); // 根据缩放级别调整密度
    
    for (let lat = bounds.south; lat < bounds.north; lat += squareSize * density) {
        for (let lng = bounds.west; lng < bounds.east; lng += squareSize * density) {
            let bortleClass;
            
            // 根据地理位置生成不同的波特尔等级
            if (lat >= 18 && lat <= 54 && lng >= 73 && lng <= 135) {
                // 中国大陆范围内
                if (lng >= 110 && lng <= 125 && lat >= 30 && lat <= 42) {
                    // 东部发达地区（如北京、上海、广州等）
                    bortleClass = Math.floor(Math.random() * 3) + 6; // 6-8级
                } else if (lng >= 75 && lng <= 95 && lat >= 35 && lat <= 50) {
                    // 西部偏远地区（如新疆、西藏等）
                    bortleClass = Math.floor(Math.random() * 3) + 1; // 1-3级
                } else {
                    // 其他地区
                    bortleClass = Math.floor(Math.random() * 5) + 3; // 3-7级
                }
            } else {
                // 国外地区
                if (lat > 60 || lat < -60) {
                    // 极地地区
                    bortleClass = Math.floor(Math.random() * 2) + 1; // 1-2级
                } else if ((lng >= -125 && lng <= -65 && lat >= 25 && lat <= 50) || 
                          (lng >= -10 && lng <= 40 && lat >= 35 && lat <= 70)) {
                    // 北美和欧洲发达地区
                    bortleClass = Math.floor(Math.random() * 4) + 5; // 5-8级
                } else {
                    // 其他地区
                    bortleClass = Math.floor(Math.random() * 6) + 2; // 2-7级
                }
            }
            
            data.push({
                lat: lat,
                lng: lng,
                bortleClass: bortleClass,
                intensity: getIntensityRadius(bortleClass)
            });
        }
    }
    
    return data;
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
async function loadLightPollutionImageLayers() {
    try {
        console.log('正在加载光污染图像图层...');
        
        // 检查地图是否已初始化
        if (!map) {
            console.warn('地图尚未初始化，无法加载图像图层');
            return;
        }
        
        // 获取当前地图边界
        const bounds = map.getBounds();
        
        // 构建API请求URL
        const apiUrl = `${API_CONFIG.baseUrl}${API_CONFIG.endpoints.lightPollution}?` +
            `north=${bounds.getNorth()}&south=${bounds.getSouth()}&` +
            `east=${bounds.getEast()}&west=${bounds.getWest()}`;
        
        console.log('API请求URL:', apiUrl);
        
        const response = await fetch(apiUrl);
        if (!response.ok) {
            console.warn('无法获取光污染图像数据:', response.statusText);
            return;
        }
        
        const data = await response.json();
        console.log('获取到的API响应数据:', data);
        
        // 清除现有图像图层
        clearImageLayers();
        
        // 检查返回的数据结构
        if (data.success && data.images && Array.isArray(data.images)) {
            console.log('获取到图像数据:', data.images.length, '个图像');
            console.log('查询边界:', data.query_bounds);
            
            // 添加每个图像作为图层
            data.images.forEach((item, index) => {
                console.log(`处理图像 ${index + 1}:`, {
                    name: item.name,
                    exists: item.exists,
                    hasImageData: !!item.image_data,
                    imageDataLength: item.image_data ? item.image_data.length : 0
                });
                
                if (item.exists && item.image_data) {
                    try {
                        // 创建图像URL
                        const imageUrl = `data:image/jpeg;base64,${item.image_data}`;
                        console.log(`创建图像URL，长度: ${imageUrl.length}`);
                        
                        // 创建图像边界 - API返回的bounds是数组格式 [west, south, east, north]
                        let west, south, east, north;
                        if (Array.isArray(item.bounds)) {
                            [west, south, east, north] = item.bounds;
                        } else {
                            // 兼容对象格式
                            west = item.bounds.west;
                            south = item.bounds.south;
                            east = item.bounds.east;
                            north = item.bounds.north;
                        }
                        const imageBounds = L.latLngBounds(
                            [south, west],
                            [north, east]
                        );
                        console.log('图像边界:', imageBounds);
                        console.log('图像边界详细信息:', {
                            southwest: imageBounds.getSouthWest(),
                            northeast: imageBounds.getNorthEast(),
                            center: imageBounds.getCenter()
                        });
                        
                        // 检查当前地图边界
                        const currentBounds = map.getBounds();
                        console.log('当前地图边界:', currentBounds);
                        console.log('图像边界与地图边界是否重叠:', currentBounds.intersects(imageBounds));
                        
                        // 创建图像覆盖层
                        const imageOverlay = L.imageOverlay(imageUrl, imageBounds, {
                            opacity: 0.3,
                            interactive: false,
                            pane: 'overlayPane',
                            crossOrigin: 'anonymous',
                            zIndex: 1000
                        });
                        
                        console.log(`创建图像覆盖层对象:`, imageOverlay);
                        
                        // 添加错误处理
                        imageOverlay.on('load', () => {
                            console.log(`✅ 图像图层 ${index + 1} 加载成功: ${item.name}`);
                            console.log('图像覆盖层已显示在地图上');
                        });
                        
                        imageOverlay.on('error', (e) => {
                            console.error(`❌ 图像图层 ${index + 1} 加载失败: ${item.name}`, e);
                        });
                        
                        // 添加到地图
                        console.log('正在将图像覆盖层添加到地图...');
                        imageOverlay.addTo(map);
                        currentImageLayers.push(imageOverlay);
                        
                        console.log(`✅ 已添加图像图层 ${index + 1}: ${item.name}`);
                        console.log('当前图像图层数量:', currentImageLayers.length);
                        
                        // 强制设置样式确保可见性
                        setTimeout(() => {
                            const element = imageOverlay.getElement();
                            if (element) {
                                element.style.zIndex = '1000';
                                element.style.opacity = '0.3';
                                element.style.display = 'block';
                                element.style.visibility = 'visible';
                                console.log('✅ 强制设置图像元素样式:', {
                                    zIndex: element.style.zIndex,
                                    opacity: element.style.opacity,
                                    display: element.style.display,
                                    visibility: element.style.visibility,
                                    src: element.src ? element.src.substring(0, 50) + '...' : 'no src'
                                });
                            } else {
                                console.warn('⚠️ 无法获取图像元素');
                            }
                        }, 100);
                        

                        
                        // 检查地图上的图层
                        console.log('地图上的所有图层:', map._layers);
                        console.log('图像覆盖层的Z-Index:', imageOverlay.getElement()?.style.zIndex);
                    } catch (error) {
                        console.error(`添加图像图层失败 ${item.name}:`, error);
                    }
                } else {
                    console.warn(`跳过图像 ${index + 1}: exists=${item.exists}, hasImageData=${!!item.image_data}`);
                }
            });
            
            console.log(`成功加载 ${currentImageLayers.length} 个光污染图像图层`);
        } else {
            console.log('没有找到图像数据或数据格式不正确');
        }
        
    } catch (error) {
        console.error('加载光污染图像图层失败:', error);
    }
}

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
 * 合并相邻的同色方块区域
 * @param {Array} data - 原始数据
 * @returns {Array} 合并后的区域数据
 */
function mergeAdjacentAreas(data) {
    if (!data || data.length === 0) return [];
    
    const merged = [];
    const processed = new Set();
    
    data.forEach((point, index) => {
        if (processed.has(index)) return;
        
        const region = {
            bortleClass: point.bortleClass,
            points: [point],
            bounds: {
                north: point.lat,
                south: point.lat,
                east: point.lng,
                west: point.lng
            }
        };
        
        // 查找相邻的同等级点
        const queue = [index];
        processed.add(index);
        
        while (queue.length > 0) {
            const currentIndex = queue.shift();
            const currentPoint = data[currentIndex];
            
            // 查找相邻点
            data.forEach((otherPoint, otherIndex) => {
                if (processed.has(otherIndex)) return;
                if (otherPoint.bortleClass !== point.bortleClass) return;
                
                const distance = Math.sqrt(
                    Math.pow(currentPoint.lat - otherPoint.lat, 2) +
                    Math.pow(currentPoint.lng - otherPoint.lng, 2)
                );
                
                // 如果距离足够近，认为是相邻的
                if (distance < 0.02) {
                    region.points.push(otherPoint);
                    processed.add(otherIndex);
                    queue.push(otherIndex);
                    
                    // 更新边界
                    region.bounds.north = Math.max(region.bounds.north, otherPoint.lat);
                    region.bounds.south = Math.min(region.bounds.south, otherPoint.lat);
                    region.bounds.east = Math.max(region.bounds.east, otherPoint.lng);
                    region.bounds.west = Math.min(region.bounds.west, otherPoint.lng);
                }
            });
        }
        
        // 计算区域中心点
        const avgLat = region.points.reduce((sum, p) => sum + p.lat, 0) / region.points.length;
        const avgLng = region.points.reduce((sum, p) => sum + p.lng, 0) / region.points.length;
        
        region.center = { lat: avgLat, lng: avgLng };
        merged.push(region);
    });
    
    return merged;
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
        
        // 只加载图像图层，不加载点数据
        await loadLightPollutionImageLayers();
        
        console.log('只加载图像图层，跳过点数据渲染');
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
 * 更新现有图层的大小
 * @param {number} zoom - 新的缩放级别
 */
function updateExistingLayerSizes(zoom) {
    if (!currentOverlay) return;
    
    const newSquareSize = getAdaptiveSquareSize(zoom);
    
    currentOverlay.eachLayer(layer => {
        if (layer instanceof L.Rectangle) {
            const bounds = layer.getBounds();
            const center = bounds.getCenter();
            
            const newBounds = [
                [center.lat - newSquareSize/2, center.lng - newSquareSize/2],
                [center.lat + newSquareSize/2, center.lng + newSquareSize/2]
            ];
            
            layer.setBounds(newBounds);
        }
    });
}

/**
 * 地图点击事件处理
 * @param {Object} e - 点击事件对象
 */
function onMapClick(e) {
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;
    
    // 获取最近的光污染数据点
    const nearestData = getNearestLightPollutionData(lat, lng);
    
    if (nearestData) {
        const popupContent = createPopupContent(lat, lng, nearestData.bortleClass);
        
        L.popup()
            .setLatLng(e.latlng)
            .setContent(popupContent)
            .openOn(map);
        
        // 更新信息面板
        updateInfoPanel(lat, lng, nearestData.bortleClass);
    }
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
 * 预加载邻近区域的图像数据
 * @param {Object} bounds - 当前边界
 * @param {number} zoom - 缩放级别
 */
async function preloadNearbyImageData(bounds, zoom) {
    const latRange = bounds.north - bounds.south;
    const lngRange = bounds.east - bounds.west;
    
    // 预加载周围8个区域的数据
    const offsets = [
        [-latRange, -lngRange], [-latRange, 0], [-latRange, lngRange],
        [0, -lngRange], [0, lngRange],
        [latRange, -lngRange], [latRange, 0], [latRange, lngRange]
    ];
    
    const preloadPromises = offsets.map(([latOffset, lngOffset]) => {
        const nearbyBounds = {
            north: bounds.north + latOffset,
            south: bounds.south + latOffset,
            east: bounds.east + lngOffset,
            west: bounds.west + lngOffset
        };
        
        return getLightPollutionData(nearbyBounds, zoom).catch(error => {
            console.warn('预加载邻近数据失败:', error);
        });
    });
    
    await Promise.allSettled(preloadPromises);
}

/**
 * 初始化搜索功能
 */
function initializeSearch() {
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;
    
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
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
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`);
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
            alert('未找到该位置，请尝试其他搜索词');
        }
    } catch (error) {
        console.error('搜索失败:', error);
        alert('搜索失败，请检查网络连接');
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
    
    // 添加键盘快捷键支持 (Ctrl+L 或 Cmd+L 切换语言)
    document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === 'l') {
            event.preventDefault();
            toggleLanguage();
        }
    });
    
    // 隐藏不需要的控件
    setTimeout(() => {
        // 隐藏加载覆盖层
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.classList.add('hidden');
            setTimeout(() => {
                loadingOverlay.style.display = 'none';
            }, 500);
        }
        
        // 隐藏统计面板
        const statsPanel = document.querySelector('.stats-panel');
        if (statsPanel) {
            statsPanel.style.display = 'none';
            console.log('已隐藏统计面板');
        }
        
        // 隐藏信息面板
        const infoPanel = document.querySelector('.info-panel');
        if (infoPanel) {
            infoPanel.style.display = 'none';
            console.log('已隐藏信息面板');
        }
        
        // 隐藏图例面板
        const legendPanel = document.querySelector('.legend-panel');
        if (legendPanel) {
            legendPanel.style.display = 'none';
            console.log('已隐藏图例面板');
        }
        
        // 隐藏搜索容器
        const searchContainer = document.getElementById('search-container');
        if (searchContainer) {
            searchContainer.style.display = 'none';
            console.log('已隐藏搜索容器');
        }
        
        // 隐藏语言切换按钮
        const languageButton = document.getElementById('language-btn');
        if (languageButton) {
            languageButton.style.display = 'none';
            console.log('已隐藏语言切换按钮');
        }
        
        console.log('应用初始化完成，所有控件已隐藏');
    }, 1000);
}

// ==================== 观星区域选择器功能 ====================

/**
 * 初始化绘制控件
 */
function initializeDrawControls() {
    // 创建绘制图层组
    drawnItems = new L.FeatureGroup();
    map.addLayer(drawnItems);

    // 创建绘制控件
    drawControl = new L.Control.Draw({
        position: 'topleft',
        draw: {
            polygon: {
                allowIntersection: false,
                drawError: {
                    color: '#e1e100',
                    message: '<strong>错误:</strong> 形状边缘不能交叉!'
                },
                shapeOptions: {
                    color: '#4a90e2',
                    weight: 3,
                    opacity: 0.8,
                    fillOpacity: 0.2
                }
            },
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
        edit: {
            featureGroup: drawnItems,
            remove: true
        }
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
        const maxPeaks = parseInt(document.getElementById('max-peaks').value) || 10;
        const transportMode = document.getElementById('network-type').value || 'drive';
        const analyzeLightPollution = document.getElementById('include-light-pollution').checked;
        const checkRoadConnectivity = document.getElementById('include-road-connectivity').checked;

        // 构建请求数据
        const requestData = {
            bbox: bbox,
            max_locations: maxPeaks,
            network_type: transportMode,
            include_light_pollution: analyzeLightPollution,
            include_road_connectivity: checkRoadConnectivity
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
    analysisResults.forEach((location, index) => {
        const marker = createStargazingMarker(location);
        drawnItems.addLayer(marker);
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
        latitude, longitude, stargazing_score, name, elevation, 
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
    const marker = L.marker([latitude, longitude], { icon });
    
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
                    <p><strong>坐标:</strong> ${latitude.toFixed(4)}, ${longitude.toFixed(4)}</p>
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
                    <div class="location-item ${scoreClass}" onclick="focusOnLocation(${location.latitude}, ${location.longitude})">
                        <div class="location-header">
                            <div class="location-name">${location.name || `观星地点 ${index + 1}`}</div>
                            <div class="location-score ${scoreClass}">${score.toFixed(1)}/10</div>
                        </div>
                        <div class="location-details">
                            <div class="detail-row">
                                <span class="detail-icon">📍</span>
                                <span>坐标: ${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}</span>
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
        if (drawControl && map && map.hasControl(drawControl)) {
            map.removeControl(drawControl);
        }
        
        // 清除所有分析内容
        clearAll();
        
        updateStatus('已切换到浏览模式', 'info');
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

// ==================== 应用初始化 ====================

// 初始化应用
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initializeApp();
        initializeStargazingSelector();
    });
} else {
    initializeApp();
    initializeStargazingSelector();
}