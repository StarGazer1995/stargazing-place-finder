// ═══════════════════════════════════════════════════════════════════════
//  Telescope mode — UI panel bindings & mode switching
// ═══════════════════════════════════════════════════════════════════════

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
