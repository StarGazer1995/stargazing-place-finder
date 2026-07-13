// ═══════════════════════════════════════════════════════════════════════
//  Results — markers, stats, results panel rendering
// ═══════════════════════════════════════════════════════════════════════

/**
 * 显示分析结果
 */
function displayAnalysisResults(result) {
    clearAnalysisResults();

    if (!result.locations || result.locations.length === 0) {
        updateStatus('未找到合适的观星地点', 'error');
        return;
    }

    analysisResults = result.locations;

    analysisResults.forEach(function (location, index) {
        try {
            var marker = createStargazingMarker(location);
            drawnItems.addLayer(marker);
        } catch (err) {
            console.error('创建标记失败:', location.name, err);
        }
    });

    if (analysisResults.length > 0) {
        const group = new L.featureGroup(drawnItems.getLayers());
        map.fitBounds(group.getBounds().pad(0.1));
    }
}

/**
 * 创建观星地点标记
 */
function createStargazingMarker(location) {
    const {
        lat, lon, stargazing_score, name, elevation,
        light_pollution_level, light_pollution_brightness,
        road_accessible, distance_to_road_km, recommendation_level,
        analysis_notes, prominence, distance_to_nearest_town,
        nearest_town_name
    } = location;

    const score = stargazing_score || 0;

    let styleKey = 'poor';
    if (score >= 8) styleKey = 'excellent';
    else if (score >= 6) styleKey = 'good';
    else if (score >= 4) styleKey = 'fair';

    const style = MARKER_STYLES[styleKey];

    const icon = L.divIcon({
        className: style.className,
        iconSize: style.iconSize,
        iconAnchor: style.iconAnchor,
        html: `<div class="marker-inner">⭐</div>`
    });

    const marker = L.marker([lat, lon], { icon });

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
                </div>` : ''}
                ${analysis_notes ? `
                <div class="info-section">
                    <h5>📝 分析说明</h5>
                    <p class="analysis-notes">${analysis_notes}</p>
                </div>` : ''}
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
 * 计算观星地点统计信息
 */
function calculateLocationStats(locations) {
    if (!locations || locations.length === 0) {
        return {
            avgScore: 'N/A',
            excellentCount: 0, goodCount: 0, fairCount: 0, poorCount: 0,
            excellentPercent: 0, goodPercent: 0, fairPercent: 0, poorPercent: 0
        };
    }

    let excellentCount = 0, goodCount = 0, fairCount = 0, poorCount = 0, totalScore = 0;

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
        avgScore, excellentCount, goodCount, fairCount, poorCount,
        excellentPercent: total > 0 ? (excellentCount / total * 100).toFixed(1) : 0,
        goodPercent: total > 0 ? (goodCount / total * 100).toFixed(1) : 0,
        fairPercent: total > 0 ? (fairCount / total * 100).toFixed(1) : 0,
        poorPercent: total > 0 ? (poorCount / total * 100).toFixed(1) : 0
    };
}

/**
 * 显示结果面板
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
    const stats = calculateLocationStats(locations);

    panel.innerHTML = `
        <div class="results-header">
            <h4>🌟 观星地点分析结果</h4>
            <button class="close-btn" onclick="clearAnalysisResults()">×</button>
        </div>
        <div class="summary-stats">
            <div class="stat-item"><div class="stat-value">${locations.length}</div><div class="stat-label">观星地点</div></div>
            <div class="stat-item"><div class="stat-value">${stats.avgScore}</div><div class="stat-label">平均评分</div></div>
            <div class="stat-item excellent"><div class="stat-value">${stats.excellentCount}</div><div class="stat-label">优秀地点</div></div>
            <div class="stat-item good"><div class="stat-value">${stats.goodCount}</div><div class="stat-label">良好地点</div></div>
        </div>
        <div class="quality-distribution">
            <h5>📊 质量分布</h5>
            <div class="distribution-bars">
                ${renderDistributionBar('优秀 (8-10分)', 'excellent', stats.excellentPercent, stats.excellentCount)}
                ${renderDistributionBar('良好 (6-8分)', 'good', stats.goodPercent, stats.goodCount)}
                ${renderDistributionBar('一般 (4-6分)', 'fair', stats.fairPercent, stats.fairCount)}
                ${renderDistributionBar('较差 (<4分)', 'poor', stats.poorPercent, stats.poorCount)}
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
                            <div class="detail-row"><span class="detail-icon">📍</span><span>坐标: ${location.lat.toFixed(4)}, ${location.lon.toFixed(4)}</span></div>
                            ${location.elevation ? `<div class="detail-row"><span class="detail-icon">⛰️</span><span>海拔: ${location.elevation.toFixed(0)}m</span></div>` : ''}
                            ${location.light_pollution_level ? `<div class="detail-row"><span class="detail-icon">🌃</span><span>光污染: ${location.light_pollution_level}</span></div>` : ''}
                            ${location.recommendation_level ? `<div class="detail-row"><span class="detail-icon">⭐</span><span>推荐: ${location.recommendation_level}</span></div>` : ''}
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
    `;

    panel.style.display = 'block';
    resultsPanel = panel;
}

function renderDistributionBar(label, cls, percent, count) {
    return `<div class="bar-item">
        <span class="bar-label">${label}</span>
        <div class="bar-container">
            <div class="bar ${cls}" style="width: ${percent}%"></div>
            <span class="bar-text">${count}</span>
        </div>
    </div>`;
}

/**
 * 聚焦到指定的观星地点
 */
function focusOnLocation(lat, lng) {
    if (map) {
        map.setView([lat, lng], 15);
        drawnItems.eachLayer(layer => {
            if (layer.getLatLng && layer.getLatLng().lat === lat && layer.getLatLng().lng === lng) {
                layer.openPopup();
            }
        });
    }
}
