// ═══════════════════════════════════════════════════════════════════════
//  Telescope targets — API calls for target matching & shooting plan
// ═══════════════════════════════════════════════════════════════════════

var _targetCatalog = null;

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
        window._lastMoon = moon;

        countEl.textContent = '(' + targets.length + ' 个目标)';
        renderTargetResults(targets, list);
        renderMoonCard(moon);
        overlayTargetsOnAladin(targets);
        var planBtn = document.getElementById('plan-btn');
        if (planBtn) planBtn.style.display = '';
        window._lastMatchBody = body;
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
