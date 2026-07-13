// 全局变量定义
let currentOverlay = null;
let currentImageLayers = [];
let pollutionTileLayer = null;
let dataCache = new Map();
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


// ==================== 应用初始化 ====================

// 初始化应用
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initializeApp();
        initializeStargazingSelector();
        initTelescopeMode();
        initMosaic();
    });
} else {
    initializeApp();
    initializeStargazingSelector();
    initTelescopeMode();
    initMosaic();
}
