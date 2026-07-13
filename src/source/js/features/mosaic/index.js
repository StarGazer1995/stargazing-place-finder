// ═══════════════════════════════════════════════════════════════════════
//  Mosaic planning — grid calculation, Aladin overlay & panel UI
// ═══════════════════════════════════════════════════════════════════════

var _mosaicGrid = null;       // current MosaicGrid
var _mosaicOverlay = null;    // canvas for mosaic FOV rectangles

/**
 * Initialize mosaic UI bindings (runs once at page load).
 */
function initMosaic() {
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

    // ── Overlap slider ──
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
