// ═══════════════════════════════════════════════════════════════════════
//  Analyzer — API calls for stargazing area analysis
// ═══════════════════════════════════════════════════════════════════════

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
        const coordinates = currentPolygon.getLatLngs()[0].map(latlng => [latlng.lng, latlng.lat]);

        const lats = coordinates.map(coord => coord[1]);
        const lngs = coordinates.map(coord => coord[0]);
        const bbox = {
            south: Math.min(...lats),
            west: Math.min(...lngs),
            north: Math.max(...lats),
            east: Math.max(...lngs)
        };

        const maxLocations = parseInt(document.getElementById('max-locations').value) || 30;
        const transportMode = document.getElementById('network-type').value || 'drive';
        const analyzeLightPollution = document.getElementById('include-light-pollution').checked;
        const checkRoadConnectivity = document.getElementById('include-road-connectivity').checked;

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

        const response = await fetch(`${API_CONFIG.baseUrl}${API_CONFIG.endpoints.analyze}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`API请求失败: ${response.status} - ${errorText}`);
        }

        const result = await response.json();
        console.log('分析结果:', result);

        displayAnalysisResults(result);
        updateStatus(`分析完成，找到 ${result.locations?.length || 0} 个观星地点`, 'success');

    } catch (error) {
        console.error('分析失败:', error);
        updateStatus(`分析失败: ${error.message}`, 'error');
    } finally {
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '分析观星区域';
        }
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
