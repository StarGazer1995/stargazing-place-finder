// ═══════════════════════════════════════════════════════════════════════
//  Telescope mode — target matching, shooting plan & altitude chart
// ═══════════════════════════════════════════════════════════════════════

var _targetCatalog = null;

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
