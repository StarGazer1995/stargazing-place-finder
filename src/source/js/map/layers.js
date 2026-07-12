// ═══════════════════════════════════════════════════════════════════════
//  Map Layers — 光污染图层渲染、数据加载、图层管理
// ═══════════════════════════════════════════════════════════════════════

/**
 * 渲染光污染数据图层
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
 * 加载光污染统计数据
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
