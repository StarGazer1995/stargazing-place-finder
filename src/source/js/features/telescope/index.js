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

        // Update FOV and mosaic overlays when view changes — capture DOM events
        var aladinDiv = document.getElementById('aladin-lite-div');
        var scheduleFovUpdate = function () {
            setTimeout(function () {
                updateFovOverlay();
                if (_mosaicGrid) renderMosaicOnAladin(_mosaicGrid);
            }, 100);
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

    // ── Match targets button ──
    var matchBtn = document.getElementById('match-targets-btn');
    if (matchBtn) {
        matchBtn.addEventListener('click', matchTelescopeTargets);
    }
    var planBtn = document.getElementById('plan-btn');
    if (planBtn) {
        planBtn.addEventListener('click', fetchShootingPlan);
    }

    // ── Collapsible plan panel ──
    var planHeader = document.getElementById('plan-panel-header');
    if (planHeader) {
        planHeader.addEventListener('click', function () {
            var body = document.getElementById('plan-panel-body');
            if (body) {
                var collapsed = body.style.display === 'none';
                body.style.display = collapsed ? 'block' : 'none';
                planHeader.querySelector('.collapse-arrow').textContent = collapsed ? '▼' : '▶';
            }
        });
    }

    // ── Collapsible mosaic panel ──
    var mosaicHeader = document.getElementById('mosaic-panel-header');
    if (mosaicHeader) {
        mosaicHeader.addEventListener('click', function () {
            var body = document.getElementById('mosaic-panel-body');
            if (body) {
                var collapsed = body.style.display === 'none';
                body.style.display = collapsed ? 'block' : 'none';
                mosaicHeader.querySelector('.collapse-arrow').textContent = collapsed ? '▼' : '▶';
            }
        });
    }

    // ── Collapsible target results ──
    var targetHeader = document.getElementById('target-results-header');
    if (targetHeader) {
        targetHeader.addEventListener('click', function () {
            var section = document.getElementById('target-results-section');
            if (section) section.classList.toggle('collapsed');
        });
    }
}

/**
 * Toggle between map mode and telescope (sky chart) mode.
 */
/**
 * Sync panel visibility based on current mode (browse / analysis / telescope).
 *
 * This is the SINGLE SOURCE OF TRUTH for all panel visibility.
 * Each mode shows ONLY its own panels — no overlap, no leakage.
 *
 * Browse mode:
 *   Visible: map, search, bortle-bar (legend), top-right buttons
 *   Data-driven: .stats-panel (shown by updateStatsPanel), .info-panel (shown by updateInfoPanel)
 *   Hidden: analysis panels, telescope panels, draw control
 *
 * Analysis mode:
 *   Visible: map, search, .control-panel, bortle-bar (legend), draw control, top-right buttons
 *   Data-driven: .status-indicator (shown by updateStatus), .results-panel (shown by displayAnalysisResults)
 *   Hidden: browse panels (.stats-panel, .info-panel, .bortle-bar-container), telescope panels
 *
 * Telescope mode:
 *   Visible: Aladin sky chart, telescope config panel, telescope status, top-right buttons
 *   Data-driven: altitude chart (shown by showAltitudeChart), target results (shown by matchTelescopeTargets)
 *   Hidden: map, search (uses Aladin search), browse panels, analysis panels, draw control, mode-toggle-btn
 */
function syncPanelVisibility() {
    var mapEl = document.getElementById('map');
    var aladinContainer = document.getElementById('aladin-container');
    var telescopePanel = document.getElementById('telescope-control-panel');
    var telescopeBtn = document.getElementById('telescope-toggle-btn');
    var telescopeStatus = document.getElementById('telescope-status');
    var chartPanel = document.getElementById('altitude-chart-panel');
    var modeBtn = document.getElementById('mode-toggle-btn');
    var searchInput = document.getElementById('search-input');
    var searchContainer = document.getElementById('search-container');

    // ── Browse-mode panels ──
    var statsPanel = document.querySelector('.stats-panel');
    var infoPanel = document.querySelector('.info-panel');
    var bortleBar = document.querySelector('.bortle-bar-container');

    // ── Analysis-mode panels ──
    var controlPanel = document.querySelector('.control-panel');
    var resultsPanel = document.querySelector('.results-panel');
    var statusIndicator = document.querySelector('.status-indicator');

    if (isTelescopeMode) {
        // ═══════════════════════════════════════════════════════════════
        //  Telescope mode
        // ═══════════════════════════════════════════════════════════════
        if (mapEl) mapEl.style.display = 'none';
        if (aladinContainer) aladinContainer.style.display = 'block';
        if (telescopePanel) telescopePanel.style.display = 'block';
        if (telescopeStatus) telescopeStatus.style.display = 'block';
        if (telescopeBtn) { telescopeBtn.textContent = '🗺️ 返回地图'; telescopeBtn.classList.add('active'); }
        if (modeBtn) modeBtn.style.display = 'none';
        if (searchContainer) searchContainer.style.display = 'none';
        if (searchInput) { searchInput.dataset.mapPlaceholder = searchInput.placeholder; searchInput.placeholder = '搜索天体 (如 M31, M42, NGC 7000)...'; }

        // Restore location display if set
        var locDisplay = document.getElementById('telescope-location-display');
        if (locDisplay && window._telescopeTargetLocation) {
            locDisplay.style.display = 'block';
        }

        // Hide browse panels
        if (statsPanel) statsPanel.style.display = 'none';
        if (infoPanel) infoPanel.style.display = 'none';
        if (bortleBar) bortleBar.style.display = 'none';

        // Hide analysis panels
        if (controlPanel) controlPanel.style.display = 'none';
        if (resultsPanel) resultsPanel.style.display = 'none';
        if (statusIndicator) statusIndicator.style.display = 'none';

        // Lazy-init Aladin
        ensureAladinReady().then(function () {
            setTimeout(function () { updateFovOverlay(); }, 400);
        }).catch(function (err) {
            console.error('Aladin init failed:', err);
            showToast('星图加载失败，请刷新页面重试', 'error');
        });
    } else if (isAnalysisMode) {
        // ═══════════════════════════════════════════════════════════════
        //  Analysis mode
        // ═══════════════════════════════════════════════════════════════
        if (mapEl) mapEl.style.display = 'block';
        if (aladinContainer) aladinContainer.style.display = 'none';
        if (telescopePanel) telescopePanel.style.display = 'none';
        if (telescopeStatus) telescopeStatus.style.display = 'none';
        if (chartPanel) chartPanel.style.display = 'none';
        if (telescopeBtn) { telescopeBtn.textContent = '🔭 望远镜模式'; telescopeBtn.classList.remove('active'); }
        if (modeBtn) modeBtn.style.display = '';
        if (searchInput && searchInput.dataset.mapPlaceholder) { searchInput.placeholder = searchInput.dataset.mapPlaceholder; }
        if (searchContainer) searchContainer.style.display = '';

        // Clean up FOV canvas
        if (fovCanvas && fovCanvas.parentNode) { fovCanvas.parentNode.removeChild(fovCanvas); fovCanvas = null; fovCanvasCtx = null; }

        // Clear jump-to-telescope location display
        var locDisplayA = document.getElementById('telescope-location-display');
        if (locDisplayA) locDisplayA.style.display = 'none';

        // Show analysis panels
        if (controlPanel) controlPanel.style.display = 'block';
        // resultsPanel is shown by displayAnalysisResults() only when results exist

        // Hide browse-only panels (bortleBar is shared with analysis — keep visible)
        if (statsPanel) statsPanel.style.display = 'none';
        if (infoPanel) infoPanel.style.display = 'none';
        if (bortleBar) bortleBar.style.display = '';

        // Show draw control
        try {
            if (!drawControl) initializeDrawControls();
            if (drawControl && map && !map.hasControl(drawControl)) map.addControl(drawControl);
        } catch (e) {}

        if (map) setTimeout(function () { map.invalidateSize(); }, 100);
    } else {
        // ═══════════════════════════════════════════════════════════════
        //  Browse mode (default)
        // ═══════════════════════════════════════════════════════════════
        if (mapEl) mapEl.style.display = 'block';
        if (aladinContainer) aladinContainer.style.display = 'none';
        if (telescopePanel) telescopePanel.style.display = 'none';
        if (telescopeStatus) telescopeStatus.style.display = 'none';
        if (chartPanel) chartPanel.style.display = 'none';
        if (telescopeBtn) { telescopeBtn.textContent = '🔭 望远镜模式'; telescopeBtn.classList.remove('active'); }
        if (modeBtn) modeBtn.style.display = '';
        if (searchInput && searchInput.dataset.mapPlaceholder) { searchInput.placeholder = searchInput.dataset.mapPlaceholder; }
        if (searchContainer) searchContainer.style.display = '';

        // Clean up FOV canvas
        if (fovCanvas && fovCanvas.parentNode) { fovCanvas.parentNode.removeChild(fovCanvas); fovCanvas = null; fovCanvasCtx = null; }

        // Clear jump-to-telescope location display
        var locDisplayB = document.getElementById('telescope-location-display');
        if (locDisplayB) locDisplayB.style.display = 'none';

        // Hide analysis panels
        if (controlPanel) controlPanel.style.display = 'none';
        if (resultsPanel) resultsPanel.style.display = 'none';
        if (statusIndicator) statusIndicator.style.display = 'none';

        // Show browse panels (stats/info are data-driven — shown by updateStatsPanel/updateInfoPanel)
        if (bortleBar) bortleBar.style.display = '';

        // Remove and destroy draw control
        try {
            if (drawControl && map) map.removeControl(drawControl);
        } catch (e) {}
        drawControl = null;
        drawnItems = null;
        currentPolygon = null;

        if (map) setTimeout(function () { map.invalidateSize(); }, 100);
    }
}

/**
 * Jump from map mode to telescope mode for a specific location.
 * Preserves analysis state so the user can return to their results.
 * @param {number} lat - Observer latitude
 * @param {number} lng - Observer longitude
 * @param {string} [name] - Location name for context display
 */
function jumpToTelescopeMode(lat, lng, name) {
    // Store the target location for the telescope panel
    window._telescopeTargetLocation = { lat: lat, lng: lng, name: name || null };

    // Switch to telescope mode without destroying analysis state
    if (!isTelescopeMode) {
        isTelescopeMode = true;
        syncPanelVisibility();
    }

    // Update the location display in the telescope panel
    var locDisplay = document.getElementById('telescope-location-display');
    if (locDisplay) {
        locDisplay.textContent = name
            ? '📍 ' + name + ' (' + lat.toFixed(4) + ', ' + lng.toFixed(4) + ')'
            : '📍 ' + lat.toFixed(4) + ', ' + lng.toFixed(4);
        locDisplay.style.display = 'block';
    }
}

function toggleTelescopeMode() {
    isTelescopeMode = !isTelescopeMode;
    syncPanelVisibility();
}

// ==================== 望远镜目标匹配 ====================

/**
 * Call the SPF backend telescope-targets endpoint and render results.
 */
async function matchTelescopeTargets() {
    var btn = document.getElementById('match-targets-btn');
    var section = document.getElementById('target-results-section');
    var list = document.getElementById('target-results-list');
    var countEl = section.querySelector('.target-count');

    btn.disabled = true;
    btn.textContent = '⏳ 匹配中...';
    list.innerHTML = '<p class="target-loading">正在分析最佳拍摄目标...</p>';
    section.style.display = 'block';

    try {
        var focalLength = parseFloat(document.getElementById('telescope-focal-length').value) || 250;
        var sensorW = parseFloat(document.getElementById('telescope-sensor-width').value) || 23.5;
        var sensorH = parseFloat(document.getElementById('telescope-sensor-height').value) || 15.7;
        var preset = document.getElementById('telescope-preset').value;

        // Use Aladin center as observing direction; observer from jump target or map center
        var raDec = aladinInstance ? aladinInstance.getRaDec() : [0, 0];
        var obsLat, obsLng;
        if (window._telescopeTargetLocation) {
            obsLat = window._telescopeTargetLocation.lat;
            obsLng = window._telescopeTargetLocation.lng;
        } else if (typeof map !== 'undefined' && map) {
            var mc = map.getCenter();
            obsLat = mc.lat;
            obsLng = mc.lng;
        } else {
            obsLat = 40;
            obsLng = 116;
        }
        var now = new Date();
        var timeStr = now.getFullYear() + '-' +
            String(now.getMonth() + 1).padStart(2, '0') + '-' +
            String(now.getDate()).padStart(2, '0') + ' ' +
            String(now.getHours()).padStart(2, '0') + ':' +
            String(now.getMinutes()).padStart(2, '0') + ':' +
            String(now.getSeconds()).padStart(2, '0');

        var tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

        var body = {
            focal_length_mm: focalLength,
            sensor_width_mm: sensorW,
            sensor_height_mm: sensorH,
            lon: obsLng,
            lat: obsLat,
            time: timeStr,
            time_zone: tz,
            limit: 100,
        };

        // Reverse geocode: show place name above results
        var placeName = '';
        try {
            var geoResp = await fetch(
                'https://nominatim.openstreetmap.org/reverse?format=json&lat=' +
                obsLat + '&lon=' + obsLng + '&zoom=10'
            );
            var geoData = await geoResp.json();
            placeName = geoData.display_name || '';
        } catch (e) { /* ignore */ }
        countEl.textContent = '';
        if (placeName) {
            countEl.textContent = '📍 ' + placeName + ' ';
        }

        var resp = await fetch(API_CONFIG.baseUrl + '/api/telescope/targets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var data = await resp.json();
        var targets = data.targets || [];
        var moon = data.moon || null;
        window._lastMoon = moon;  // shared with altitude chart

        countEl.textContent = '(' + targets.length + ' 个目标)';
        renderTargetResults(targets, list);
        renderMoonCard(moon);  // after renderTargetResults (which resets innerHTML)
        overlayTargetsOnAladin(targets);
        // Show plan button now that we have targets
        var planBtn = document.getElementById('plan-btn');
        if (planBtn) planBtn.style.display = '';
        window._lastMatchBody = body;  // stash for plan fetch
    } catch (e) {
        console.error('Target matching failed:', e);
        list.innerHTML = '<p class="target-error">匹配失败: ' + e.message + '</p>';
        countEl.textContent = '';
    } finally {
        btn.disabled = false;
        btn.textContent = '🎯 匹配拍摄目标';
    }
}

/**
 * Fetch and render a shooting plan from the matched targets.
 */
async function fetchShootingPlan() {
    var btn = document.getElementById('plan-btn');
    var panel = document.getElementById('plan-panel');
    var body = document.getElementById('plan-panel-body');
    var label = panel.querySelector('.plan-night-label');
    if (!window._lastMatchBody) return;

    btn.disabled = true;
    btn.textContent = '⏳ 生成计划...';
    body.innerHTML = '<p class="target-loading">正在生成拍摄计划...</p>';
    panel.style.display = 'block';

    try {
        var resp = await fetch(API_CONFIG.baseUrl + '/api/telescope/plan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(window._lastMatchBody),
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var data = await resp.json();
        var plan = data.plan;
        var targets = data.targets || [];

        if (plan && plan.date) {
            label.textContent = plan.date + '  ' + data.moon.phase;
        }
        renderShootingPlan(plan, targets, body);
    } catch (e) {
        console.error('Shooting plan failed:', e);
        body.innerHTML = '<p class="target-error">计划生成失败: ' + e.message + '</p>';
        label.textContent = '';
    } finally {
        btn.disabled = false;
        btn.textContent = '📋 拍摄计划';
    }
}

function renderShootingPlan(plan, targets, container) {
    if (!plan || !plan.slots || !plan.slots.length) {
        container.innerHTML = '<p class="target-empty">暂无拍摄计划</p>';
        return;
    }

    // Moon delay banner
    var html = '';
    if (plan.moon_delay_min > 0) {
        html += '<div class="plan-moon-delay">🌙 等月落 ' + plan.moon_delay_min + ' 分钟后开始拍摄</div>';
    }
    html += '<div class="plan-header-bar"><span>📸 目标</span><span>⏱️ 时段 / 时长</span><span>📐 高度角</span></div>';

    // Build name → target lookup for click-to-goto
    var targetByName = {};
    for (var ti = 0; ti < targets.length; ti++) {
        targetByName[targets[ti].name] = targets[ti];
    }

    for (var i = 0; i < plan.slots.length; i++) {
        var s = plan.slots[i];
        var startH = new Date(s.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        var endH = new Date(s.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        var badge = s.mosaic_recommended ? ' 🧩' : '';
        var fit = Math.round(s.fov_fit_score * 100);

        html += '<div class="plan-slot" data-plan-target="' + s.target_name + '" style="cursor:pointer">' +
            '<div class="plan-slot-info">' +
            '<div class="plan-slot-name">' + (i + 1) + '. ' + s.target_name + badge + '</div>' +
            '<div class="plan-slot-type">' + s.target_type + ' · FOV ' + fit + '%</div>' +
            (s.notes.length ? '<div class="plan-slot-notes">' + s.notes.join(' · ') + '</div>' : '') +
            '</div>' +
            '<div class="plan-slot-time"><div>' + startH + ' → ' + endH + '</div>' +
            '<div class="plan-slot-dur">' + s.duration_min + ' min</div></div>' +
            '<div class="plan-slot-alt"><span class="alt-start">' + s.start_alt.toFixed(0) + '°</span>' +
            ' → <span class="alt-end">' + s.end_alt.toFixed(0) + '°</span></div></div>';
    }

    // Warnings
    if (plan.warnings && plan.warnings.length) {
        html += '<div class="plan-warnings">';
        for (var w = 0; w < plan.warnings.length; w++) {
            html += '<div class="plan-warning">💡 ' + plan.warnings[w] + '</div>';
        }
        html += '</div>';
    }

    html += '<div class="plan-summary">🕐 暗夜 ' + plan.total_dark_min + 'min · 已分配 ' + plan.used_min + 'min</div>';
    container.innerHTML = html;

    // Click to jump Aladin + show altitude chart
    var planSlots = container.querySelectorAll('.plan-slot');
    planSlots.forEach(function (card) {
        card.addEventListener('click', function () {
            var name = card.getAttribute('data-plan-target');
            var t = targetByName[name];
            if (!t) return;
            if (aladinInstance && t.ra != null && t.dec != null) {
                aladinInstance.gotoRaDec(t.ra, t.dec);
            }
            showAltitudeChart(t);
        });
    });
}

/**
 * Render moon phase card above target results.
 * @param {Object|null} moon — moon data from API {illumination, phase, altitude_curve, always_down, always_up, dark_fraction}
 */
function renderMoonCard(moon) {
    var container = document.getElementById('target-results-list');
    if (!moon || !container) return;

    // Remove any existing moon card before rendering a new one
    var old = container.querySelector('.moon-card');
    if (old) old.remove();

    var illum = moon.illumination * 100;
    var phaseEmoji = illum < 1 ? '\u{1F311}' : illum < 25 ? '\u{1F312}' : illum < 50 ? '\u{1F313}' : illum < 75 ? '\u{1F314}' : illum < 99 ? '\u{1F315}' : '\u{1F316}';

    var level, levelColor, tip;
    if (moon.always_down || illum <= 30) {
        level = '\u{1F7E2} 低干扰';
        levelColor = '#2ecc71';
        tip = '月光对拍摄影响很小';
    } else if (moon.dark_fraction > 0.5) {
        level = '\u{1F7E0} 中干扰';
        levelColor = '#f39c12';
        tip = '后半夜暗夜窗口较好';
    } else if (moon.dark_fraction > 0.15) {
        level = '\u{1F7E0} 中高干扰';
        levelColor = '#e67e22';
        tip = '暗夜窗口较短，拍窄带或早起拍';
    } else {
        level = '\u{1F534} 高干扰';
        levelColor = '#e74c3c';
        tip = moon.always_up ? '月球整晚可见，建议窄带滤镜' : '暗夜窗口极短，优先窄带拍摄';
    }

    var html = '<div class="moon-card">' +
        '<div class="moon-card-header">' +
            '<span class="moon-emoji">' + phaseEmoji + '</span>' +
            '<span class="moon-phase">' + moon.phase + '</span>' +
            '<span class="moon-illum">' + illum.toFixed(0) + '%</span>' +
        '</div>' +
        '<div class="moon-card-body">' +
            '<div class="moon-level" style="color:' + levelColor + '">' + level + '</div>' +
            '<div class="moon-tip">\u{1F4A1} ' + tip + '</div>' +
        '</div>' +
        '</div>';

    container.insertAdjacentHTML('afterbegin', html);
}
function renderTargetResults(targets, container) {
    if (!targets.length) {
        container.innerHTML = '<p class="target-empty">当前天区未找到适合拍摄的目标</p>';
        return;
    }
    var html = '';
    for (var i = 0; i < targets.length; i++) {
        var t = targets[i];
        var scoreColor = t.suitability_score >= 70 ? '#2ecc71' : t.suitability_score >= 40 ? '#f39c12' : '#e74c3c';
        var badge = t.mosaic_recommended
            ? ' <span class="mosaic-badge" data-mosaic-idx="' + i + '" title="点击计算马赛克拼接">🧩</span>'
            : '';
        html += '<div class="target-card" data-target-index="' + i + '" data-has-mosaic="' + (t.mosaic_recommended ? '1' : '0') + '">' +
            '<div class="target-rank">' + (i + 1) + '</div>' +
            '<div class="target-info">' +
                '<div class="target-name">' + t.name + badge + '</div>' +
                '<div class="target-type">' + t.type + ' | 星等 ' + (t.magnitude != null ? t.magnitude.toFixed(1) : '?') + '</div>' +
                '<div class="target-detail">FOV适配 ' + (t.fov_fit_score != null ? (t.fov_fit_score * 100).toFixed(0) + '%' : '-') +
                ' | 滤镜 ' + (t.filter_match_score != null ? (t.filter_match_score * 100).toFixed(0) + '%' : '-') +
                '</div>' +
            '</div>' +
            '<div class="target-score" style="color:' + scoreColor + '">' + t.suitability_score.toFixed(0) + '</div>' +
            '</div>';
    }
    container.innerHTML = html;

    // Store for chart access
    window._lastTargets = targets;

    // Click to goto target on Aladin + show altitude chart
    var cards = container.querySelectorAll('.target-card');
    cards.forEach(function (card) {
        card.addEventListener('click', function (e) {
            // If the mosaic badge was clicked, open mosaic instead
            var badge = e.target.closest('.mosaic-badge');
            if (badge) {
                e.stopPropagation();
                var midx = parseInt(badge.getAttribute('data-mosaic-idx'));
                var mt = targets[midx];
                if (mt) {
                    window._lastMosaicTarget = mt;
                    fetchMosaicGrid(mt);
                }
                return;
            }
            var idx = parseInt(card.getAttribute('data-target-index'));
            var target = targets[idx];
            if (aladinInstance && target.ra != null && target.dec != null) {
                aladinInstance.gotoRaDec(target.ra, target.dec);
            }
            showAltitudeChart(target);
        });
    });
}

/**
 * Overlay matched targets on Aladin as a catalog.
 */
var _targetCatalog = null;
/**
 * Draw altitude curve for the selected target at the bottom of the screen.
 */
function showAltitudeChart(target) {
    var panel = document.getElementById('altitude-chart-panel');
    var canvas = document.getElementById('altitude-chart-canvas');
    var title = document.getElementById('altitude-chart-title');
    if (!panel || !canvas || !target) return;

    var curve = target.altitude_curve;
    if (!curve || curve.length < 2) {
        panel.style.display = 'none';
        return;
    }

    var sc = target.suitability_score != null ? target.suitability_score.toFixed(0) : '?';
    var fov = target.fov_fit_score != null ? (target.fov_fit_score * 100).toFixed(0) : '?';
    var flt = target.filter_match_score != null ? (target.filter_match_score * 100).toFixed(0) : '?';
    title.textContent = '\u{1F4C8} ' + target.name + ' — 综合' + sc + ' | FOV' + fov + '% | 滤镜' + flt + '%';
    panel.style.display = 'block';

    // Defer to next frame so the browser can lay out the newly-visible panel
    requestAnimationFrame(function () {
    // Size canvas to panel width
    var w = panel.clientWidth - 20;
    if (w <= 0) { w = 280; }  // fallback minimum width
    var h = 100;
    canvas.width = w * (window.devicePixelRatio || 1);
    canvas.height = h * (window.devicePixelRatio || 1);
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
    var ctx = canvas.getContext('2d');
    ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);

    var pad = { top: 15, right: 10, bottom: 25, left: 40 };
    var pw = w - pad.left - pad.right;
    var ph = h - pad.top - pad.bottom;

    // Find alt range (include moon if available)
    var alts = curve.map(function (p) { return p.alt; });
    var minAlt = Math.max(0, Math.floor(Math.min.apply(null, alts) / 5) * 5);
    var maxAlt = Math.min(90, Math.ceil(Math.max.apply(null, alts) / 5) * 5);
    var moonCurve = window._lastMoon ? window._lastMoon.altitude_curve : null;
    var hasMoon = moonCurve && moonCurve.length > 1;
    if (hasMoon) {
        var moonMin = Math.max(0, Math.floor(Math.min.apply(null, moonCurve.map(function (p) { return p.alt; })) / 5) * 5);
        var moonMax = Math.min(90, Math.ceil(Math.max.apply(null, moonCurve.map(function (p) { return p.alt; })) / 5) * 5);
        minAlt = Math.min(minAlt, moonMin);
        maxAlt = Math.max(maxAlt, moonMax);
    }
    if (maxAlt - minAlt < 10) { maxAlt = minAlt + 10; }

    var xScale = function (i) { return pad.left + (i / (curve.length - 1)) * pw; };
    var yScale = function (alt) { return pad.top + (1 - (alt - minAlt) / (maxAlt - minAlt)) * ph; };

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.lineWidth = 1;
    for (var a = minAlt; a <= maxAlt; a += 10) {
        var y = yScale(a);
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
        ctx.fillStyle = '#888';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'right';
        ctx.fillText(a + '°', pad.left - 4, y + 4);
    }

    // Time labels (every 2 hours, local time)
    ctx.textAlign = 'center';
    ctx.fillStyle = '#888';
    ctx.font = '10px sans-serif';
    for (var i = 0; i < curve.length; i += 8) {
        var d = new Date(curve[i].time * 1000);
        var hh = String(d.getHours()).padStart(2, '0');
        var mm = String(d.getMinutes()).padStart(2, '0');
        ctx.fillText(hh + ':' + mm, xScale(i), h - pad.bottom + 14);
    }

    // Horizon line
    ctx.strokeStyle = 'rgba(255,80,80,0.3)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    var hy = yScale(0);
    ctx.beginPath(); ctx.moveTo(pad.left, hy); ctx.lineTo(w - pad.right, hy); ctx.stroke();
    ctx.setLineDash([]);

    // Altitude curve
    ctx.strokeStyle = '#f1c40f';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (var i = 0; i < curve.length; i++) {
        var px = xScale(i);
        var py = yScale(curve[i].alt);
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();

    // Moon altitude curve (dashed gray)
    if (hasMoon) {
        ctx.strokeStyle = 'rgba(200,200,220,0.6)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        for (var i4 = 0; i4 < moonCurve.length; i4++) {
            var px4 = xScale(i4);
            var py4 = yScale(moonCurve[i4].alt);
            if (i4 === 0) ctx.moveTo(px4, py4); else ctx.lineTo(px4, py4);
        }
        ctx.stroke();
        ctx.setLineDash([]);

        // Moon label
        var labelIdx = Math.floor(moonCurve.length * 0.65);
        ctx.fillStyle = 'rgba(200,200,220,0.75)';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('\u{1F319} Moon', xScale(labelIdx), yScale(moonCurve[labelIdx].alt) - 8);
    }

    // Dynamic suitability score curve (green dot-dash, right Y-axis)
    var fovS = (target.fov_fit_score || 0) * 40;
    var sbS = (target.surface_brightness_score || 0) * 30;
    var fltS = (target.filter_match_score || 0) * 20;
    var scoreStatic = fovS + sbS + fltS;
    var scoreVals = curve.map(function (p) { return scoreStatic + (p.alt / 90) * 10; });
    var minScore = Math.max(0, Math.floor(Math.min.apply(null, scoreVals) / 5) * 5);
    var maxScore = Math.min(100, Math.ceil(Math.max.apply(null, scoreVals) / 5) * 5);
    if (maxScore - minScore < 10) { maxScore = minScore + 10; }
    var yScore = function (s) { return pad.top + (1 - (s - minScore) / (maxScore - minScore)) * ph; };

    ctx.strokeStyle = 'rgba(46,204,113,0.7)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 5]);
    ctx.beginPath();
    for (var i5 = 0; i5 < curve.length; i5++) {
        var px5 = xScale(i5);
        var py5 = yScore(scoreVals[i5]);
        if (i5 === 0) ctx.moveTo(px5, py5); else ctx.lineTo(px5, py5);
    }
    ctx.stroke();
    ctx.setLineDash([]);

    // Score axis labels (right side)
    ctx.fillStyle = 'rgba(46,204,113,0.6)';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'left';
    for (var s2 = minScore; s2 <= maxScore; s2 += 10) {
        ctx.fillText(s2, w - pad.right + 4, yScore(s2) + 3);
    }
    // Score label
    ctx.fillText('⭐ Score', w - pad.right + 4, pad.top - 2);

    // Dusk/dawn markers
    if (target.civil_dusk) {
        ctx.fillStyle = '#e67e22';
        ctx.font = 'bold 11px sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('\u{1F31A} Dusk', pad.left, pad.top - 2);
    }
    if (target.civil_dawn) {
        ctx.fillStyle = '#3498db';
        ctx.textAlign = 'right';
        ctx.fillText('Dawn \u{1F305}', w - pad.right, pad.top - 2);
    }
    });  // end requestAnimationFrame
}

function overlayTargetsOnAladin(targets) {
    if (!aladinInstance) return;

    // Remove previous catalog
    if (_targetCatalog) {
        try { aladinInstance.removeCatalogs(); } catch (e) {}
        _targetCatalog = null;
    }

    var sources = [];
    for (var i = 0; i < targets.length; i++) {
        var t = targets[i];
        if (t.ra == null || t.dec == null) continue;
        sources.push({
            ra: t.ra,
            dec: t.dec,
            name: t.name,
            type: t.type,
            mag: t.magnitude,
            score: t.suitability_score,
        });
    }
    if (!sources.length) return;

    try {
        _targetCatalog = A.catalog({
            name: '推荐目标',
            sourceSize: 14,
            color: '#f1c40f',
            shape: 'cross',
            limit: 200,
        });
        _targetCatalog.addSources(sources);
        aladinInstance.addCatalog(_targetCatalog);
    } catch (e) {
        console.warn('Aladin catalog overlay failed:', e);
        _targetCatalog = null;
    }
}

// ── Mosaic planning ─────────────────────────────────────────────────────

var _mosaicGrid = null;       // current MosaicGrid
var _mosaicOverlay = null;    // canvas for mosaic FOV rectangles

/**
 * Fetch mosaic grid from the backend and render it on Aladin + UI panel.
 */
async function fetchMosaicGrid(target) {
    var panel = document.getElementById('mosaic-panel');
    var body = document.getElementById('mosaic-panel-body');
    var overlapSlider = document.getElementById('mosaic-overlap');
    var overlap = overlapSlider ? parseFloat(overlapSlider.value) / 100 : 0.15;

    if (!window._lastMatchBody) return;

    body.innerHTML = '<p class="target-loading">计算马赛克网格...</p>';
    panel.style.display = 'block';
    var controls = document.getElementById('mosaic-controls');
    if (controls) controls.style.display = 'flex';

    var reqBody = {
        target: {
            name: target.name,
            ra: target.ra,
            dec: target.dec,
            angular_size_arcmin: target.angular_size_arcmin,
            angular_size_min_arcmin: target.angular_size_min_arcmin,
        },
        config: window._lastMatchBody,
        overlap: overlap,
    };

    try {
        var resp = await fetch(API_CONFIG.baseUrl + '/api/telescope/mosaic', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(reqBody),
        });
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var data = await resp.json();
        if (data.error) {
            body.innerHTML = '<p class="target-error">' + data.error + '</p>';
            return;
        }
        _mosaicGrid = data.grid;
        renderMosaicOnAladin(_mosaicGrid);
        renderMosaicPanel(_mosaicGrid, body);
    } catch (e) {
        console.error('Mosaic failed:', e);
        body.innerHTML = '<p class="target-error">马赛克计算失败: ' + e.message + '</p>';
    }
}

/**
 * Draw mosaic panel FOV rectangles on a semi-transparent canvas over Aladin.
 */
function renderMosaicOnAladin(grid) {
    if (!aladinInstance) return;
    clearMosaicOverlay();

    var canvas = document.getElementById('mosaic-fov-canvas');
    if (!canvas) {
        canvas = document.createElement('canvas');
        canvas.id = 'mosaic-fov-canvas';
        canvas.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:11;';
        var container = document.getElementById('aladin-lite-div');
        if (container) container.appendChild(canvas);
    }
    _mosaicOverlay = canvas;

    // Delay to let Aladin settle
    setTimeout(function () {
        var ctx = canvas.getContext('2d');
        var w = canvas.width = canvas.clientWidth;
        var h = canvas.height = canvas.clientHeight;
        ctx.clearRect(0, 0, w, h);

        for (var i = 0; i < grid.panels.length; i++) {
            var p = grid.panels[i];
            var corners = p.corners;
            if (!corners || corners.length < 4) continue;

            // Convert celestial corners to screen pixels
            var pts = [];
            for (var j = 0; j < 4; j++) {
                var pix = aladinInstance.world2pix(corners[j][0], corners[j][1]);
                pts.push(pix);
            }

            // Draw panel rectangle
            ctx.strokeStyle = 'rgba(52,152,219,0.7)';
            ctx.lineWidth = 1.5;
            ctx.setLineDash([4, 3]);
            ctx.beginPath();
            ctx.moveTo(pts[0][0], pts[0][1]);
            for (var j2 = 1; j2 < 4; j2++) ctx.lineTo(pts[j2][0], pts[j2][1]);
            ctx.closePath();
            ctx.stroke();
            ctx.setLineDash([]);

            // Panel label at centre
            var cp = aladinInstance.world2pix(p.ra_center, p.dec_center);
            ctx.fillStyle = 'rgba(52,152,219,0.9)';
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('[' + p.row + ',' + p.col + ']', cp[0], cp[1] - 8);
        }
    }, 100);
}

function clearMosaicOverlay() {
    if (_mosaicOverlay) {
        var ctx = _mosaicOverlay.getContext('2d');
        ctx.clearRect(0, 0, _mosaicOverlay.width, _mosaicOverlay.height);
    }
}

/**
 * Render the mosaic panel UI below the target list.
 */
function renderMosaicPanel(grid, container) {
    var html = '<div class="mosaic-summary">' +
        '网格 ' + grid.rows + '×' + grid.cols + ' = ' + grid.total_panels + ' 面板' +
        ' | 重叠 ' + Math.round(grid.overlap * 100) + '%' +
        ' | FOV ' + grid.fov_width_deg.toFixed(2) + '°×' + grid.fov_height_deg.toFixed(2) + '°' +
        '</div>';

    html += '<div class="mosaic-panel-list">';
    for (var i = 0; i < grid.panels.length; i++) {
        var p = grid.panels[i];
        html += '<div class="mosaic-panel-item">' +
            '<span class="mp-label">[' + p.row + ',' + p.col + ']</span>' +
            '<span class="mp-coord">RA ' + p.ra_center.toFixed(3) + '°  Dec ' + p.dec_center.toFixed(3) + '°</span>' +
            '</div>';
    }
    html += '</div>';

    html += '<p class="mosaic-hint">💡 蓝色虚线框为拼接面板范围。拖动重叠率滑块实时调整。</p>';
    container.innerHTML = html;
}

// Re-render mosaic when overlap slider changes
function initMosaicSlider() {
    var slider = document.getElementById('mosaic-overlap');
    if (!slider) return;
    slider.addEventListener('input', function () {
        var val = document.getElementById('mosaic-overlap-val');
        if (val) val.textContent = slider.value + '%';
        // If mosaic is showing, re-fetch with new overlap
        if (_mosaicGrid && window._lastMosaicTarget) {
            fetchMosaicGrid(window._lastMosaicTarget);
        }
    });
}

