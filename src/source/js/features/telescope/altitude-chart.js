// ═══════════════════════════════════════════════════════════════════════
//  Altitude chart — Canvas-drawn altitude curve for selected target
// ═══════════════════════════════════════════════════════════════════════

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

    requestAnimationFrame(function () {
    var w = panel.clientWidth - 20;
    if (w <= 0) { w = 280; }
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

    ctx.clearRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.lineWidth = 1;
    for (var a = minAlt; a <= maxAlt; a += 10) {
        var y = yScale(a);
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
        ctx.fillStyle = '#888'; ctx.font = '10px sans-serif'; ctx.textAlign = 'right';
        ctx.fillText(a + '°', pad.left - 4, y + 4);
    }

    // Time labels (every 2 hours)
    ctx.textAlign = 'center'; ctx.fillStyle = '#888'; ctx.font = '10px sans-serif';
    for (var i = 0; i < curve.length; i += 8) {
        var d = new Date(curve[i].time * 1000);
        ctx.fillText(String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'), xScale(i), h - pad.bottom + 14);
    }

    // Horizon line
    ctx.strokeStyle = 'rgba(255,80,80,0.3)'; ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    var hy = yScale(0);
    ctx.beginPath(); ctx.moveTo(pad.left, hy); ctx.lineTo(w - pad.right, hy); ctx.stroke();
    ctx.setLineDash([]);

    // Altitude curve
    ctx.strokeStyle = '#f1c40f'; ctx.lineWidth = 2;
    ctx.beginPath();
    for (var i2 = 0; i2 < curve.length; i2++) {
        var px = xScale(i2), py = yScale(curve[i2].alt);
        if (i2 === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();

    // Moon altitude curve (dashed gray)
    if (hasMoon) {
        ctx.strokeStyle = 'rgba(200,200,220,0.6)'; ctx.lineWidth = 1.5;
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        for (var i3 = 0; i3 < moonCurve.length; i3++) {
            var px3 = xScale(i3), py3 = yScale(moonCurve[i3].alt);
            if (i3 === 0) ctx.moveTo(px3, py3); else ctx.lineTo(px3, py3);
        }
        ctx.stroke(); ctx.setLineDash([]);
        var labelIdx = Math.floor(moonCurve.length * 0.65);
        ctx.fillStyle = 'rgba(200,200,220,0.75)'; ctx.font = '10px sans-serif'; ctx.textAlign = 'left';
        ctx.fillText('\u{1F319} Moon', xScale(labelIdx), yScale(moonCurve[labelIdx].alt) - 8);
    }

    // Suitability score curve (green dot-dash, right Y-axis)
    var fovS = (target.fov_fit_score || 0) * 40;
    var sbS = (target.surface_brightness_score || 0) * 30;
    var fltS = (target.filter_match_score || 0) * 20;
    var scoreStatic = fovS + sbS + fltS;
    var scoreVals = curve.map(function (p) { return scoreStatic + (p.alt / 90) * 10; });
    var minScore = Math.max(0, Math.floor(Math.min.apply(null, scoreVals) / 5) * 5);
    var maxScore = Math.min(100, Math.ceil(Math.max.apply(null, scoreVals) / 5) * 5);
    if (maxScore - minScore < 10) { maxScore = minScore + 10; }
    var yScore = function (s) { return pad.top + (1 - (s - minScore) / (maxScore - minScore)) * ph; };

    ctx.strokeStyle = 'rgba(46,204,113,0.7)'; ctx.lineWidth = 1.5;
    ctx.setLineDash([3, 5]);
    ctx.beginPath();
    for (var i4 = 0; i4 < curve.length; i4++) {
        var px4 = xScale(i4), py4 = yScore(scoreVals[i4]);
        if (i4 === 0) ctx.moveTo(px4, py4); else ctx.lineTo(px4, py4);
    }
    ctx.stroke(); ctx.setLineDash([]);

    // Score axis labels
    ctx.fillStyle = 'rgba(46,204,113,0.6)'; ctx.font = '9px sans-serif'; ctx.textAlign = 'left';
    for (var s2 = minScore; s2 <= maxScore; s2 += 10) {
        ctx.fillText(s2, w - pad.right + 4, yScore(s2) + 3);
    }
    ctx.fillText('⭐ Score', w - pad.right + 4, pad.top - 2);

    // Dusk/dawn markers
    if (target.civil_dusk) {
        ctx.fillStyle = '#e67e22'; ctx.font = 'bold 11px sans-serif'; ctx.textAlign = 'left';
        ctx.fillText('\u{1F31A} Dusk', pad.left, pad.top - 2);
    }
    if (target.civil_dawn) {
        ctx.fillStyle = '#3498db'; ctx.textAlign = 'right';
        ctx.fillText('Dawn \u{1F305}', w - pad.right, pad.top - 2);
    }
    });  // end requestAnimationFrame
}
