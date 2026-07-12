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

                <div class="popup-actions">
                    <button class="btn-jump-telescope" onclick="event.stopPropagation(); jumpToTelescopeMode(${lat}, ${lon}, '${(name || '').replace(/'/g, "\\'")}')">🔭 在此拍摄</button>
                </div>
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
    // Guard: status indicator must NEVER be shown outside analysis mode
    if (!isAnalysisMode || isTelescopeMode) return;

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

    if (isAnalysisMode) {
        modeBtn.textContent = '切换到浏览模式';
        modeBtn.classList.add('active');
        if (!drawControl) initializeDrawControls();
        updateStatus('已切换到分析模式，请绘制分析区域', 'info');
    } else {
        modeBtn.textContent = '切换到分析模式';
        modeBtn.classList.remove('active');
        clearAll();
    }

    syncPanelVisibility();
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
