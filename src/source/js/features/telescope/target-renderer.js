// ═══════════════════════════════════════════════════════════════════════
//  Target renderer — DOM rendering for targets, moon card, shooting plan
// ═══════════════════════════════════════════════════════════════════════

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

    window._lastTargets = targets;

    var cards = container.querySelectorAll('.target-card');
    cards.forEach(function (card) {
        card.addEventListener('click', function (e) {
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

function renderShootingPlan(plan, targets, container) {
    if (!plan || !plan.slots || !plan.slots.length) {
        container.innerHTML = '<p class="target-empty">暂无拍摄计划</p>';
        return;
    }

    var html = '';
    if (plan.moon_delay_min > 0) {
        html += '<div class="plan-moon-delay">🌙 等月落 ' + plan.moon_delay_min + ' 分钟后开始拍摄</div>';
    }
    html += '<div class="plan-header-bar"><span>📸 目标</span><span>⏱️ 时段 / 时长</span><span>📐 高度角</span></div>';

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

    if (plan.warnings && plan.warnings.length) {
        html += '<div class="plan-warnings">';
        for (var w = 0; w < plan.warnings.length; w++) {
            html += '<div class="plan-warning">💡 ' + plan.warnings[w] + '</div>';
        }
        html += '</div>';
    }

    html += '<div class="plan-summary">🕐 暗夜 ' + plan.total_dark_min + 'min · 已分配 ' + plan.used_min + 'min</div>';
    container.innerHTML = html;

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

function renderMoonCard(moon) {
    var container = document.getElementById('target-results-list');
    if (!moon || !container) return;

    var old = container.querySelector('.moon-card');
    if (old) old.remove();

    var illum = moon.illumination * 100;
    var phaseEmoji = illum < 1 ? '\u{1F311}' : illum < 25 ? '\u{1F312}' : illum < 50 ? '\u{1F313}' : illum < 75 ? '\u{1F314}' : illum < 99 ? '\u{1F315}' : '\u{1F316}';

    var level, levelColor, tip;
    if (moon.always_down || illum <= 30) {
        level = '\u{1F7E2} 低干扰'; levelColor = '#2ecc71'; tip = '月光对拍摄影响很小';
    } else if (moon.dark_fraction > 0.5) {
        level = '\u{1F7E0} 中干扰'; levelColor = '#f39c12'; tip = '后半夜暗夜窗口较好';
    } else if (moon.dark_fraction > 0.15) {
        level = '\u{1F7E0} 中高干扰'; levelColor = '#e67e22'; tip = '暗夜窗口较短，拍窄带或早起拍';
    } else {
        level = '\u{1F534} 高干扰'; levelColor = '#e74c3c';
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

function overlayTargetsOnAladin(targets) {
    if (!aladinInstance) return;

    if (_targetCatalog) {
        try { aladinInstance.removeCatalogs(); } catch (e) {}
        _targetCatalog = null;
    }

    var sources = [];
    for (var i = 0; i < targets.length; i++) {
        var t = targets[i];
        if (t.ra == null || t.dec == null) continue;
        sources.push({ ra: t.ra, dec: t.dec, name: t.name, type: t.type, mag: t.magnitude, score: t.suitability_score });
    }
    if (!sources.length) return;

    try {
        _targetCatalog = A.catalog({
            name: '推荐目标', sourceSize: 14, color: '#f1c40f', shape: 'cross', limit: 200,
        });
        _targetCatalog.addSources(sources);
        aladinInstance.addCatalog(_targetCatalog);
    } catch (e) {
        console.warn('Aladin catalog overlay failed:', e);
        _targetCatalog = null;
    }
}
