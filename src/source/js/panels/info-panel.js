// ═══════════════════════════════════════════════════════════════════════
//  Info Panel — 地图点击弹窗、信息面板、坐标分析
// ═══════════════════════════════════════════════════════════════════════

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
            <div class="popup-actions">
                <button class="btn-jump-telescope" onclick="event.stopPropagation(); jumpToTelescopeMode(${lat}, ${lng}, '${lat.toFixed(4)}, ${lng.toFixed(4)}')">🔭 ${getText('shootHere') || '在此拍摄'}</button>
            </div>
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
            <div class="popup-actions">
                <button class="btn-jump-telescope" onclick="event.stopPropagation(); jumpToTelescopeMode(${lat}, ${lng}, '${lat.toFixed(4)}, ${lng.toFixed(4)}')">🔭 ${getText('shootHere') || '在此拍摄'}</button>
            </div>
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

    // Show panel only in browse mode
    if (!isAnalysisMode && !isTelescopeMode) {
        infoPanel.style.display = 'block';
    }
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
