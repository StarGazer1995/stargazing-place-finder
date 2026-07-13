// ═══════════════════════════════════════════════════════════════════════
//  Draw controls — Leaflet.Draw rectangle tool for area selection
// ═══════════════════════════════════════════════════════════════════════

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
        drawnItems.clearLayers();
        drawnItems.addLayer(layer);
        currentPolygon = layer;

        const analyzeBtn = document.getElementById('analyze-button');
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
        }
        updateStatus('已绘制分析区域，点击"分析观星区域"开始分析', 'success');
    });

    map.on(L.Draw.Event.DELETED, function(e) {
        currentPolygon = null;
        const analyzeBtn = document.getElementById('analyze-button');
        if (analyzeBtn) {
            analyzeBtn.disabled = true;
        }
        clearAnalysisResults();
        updateStatus('已清除绘制区域', 'success');
    });
}

/**
 * 清除分析结果（保留绘制区域）
 */
function clearAnalysisResults() {
    if (drawnItems) {
        drawnItems.eachLayer(layer => {
            if (layer !== currentPolygon) {
                drawnItems.removeLayer(layer);
            }
        });
    }
    if (resultsPanel) {
        resultsPanel.style.display = 'none';
    }
    analysisResults = [];
}

/**
 * 清除所有内容（包括绘制区域）
 */
function clearAll() {
    if (drawnItems) {
        drawnItems.clearLayers();
    }
    currentPolygon = null;
    analysisResults = [];

    if (resultsPanel) {
        resultsPanel.style.display = 'none';
    }

    const analyzeBtn = document.getElementById('analyze-button');
    if (analyzeBtn) {
        analyzeBtn.disabled = true;
    }

    if (isAnalysisMode && drawControl && map) {
        if (!map.hasControl(drawControl)) {
            map.addControl(drawControl);
        }
    }
    updateStatus('已清除所有内容', 'success');
}
