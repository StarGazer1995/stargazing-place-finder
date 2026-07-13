// ═══════════════════════════════════════════════════════════════════════
//  Telescope mode — Aladin Lite core
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
                if (typeof _mosaicGrid !== 'undefined' && _mosaicGrid) renderMosaicOnAladin(_mosaicGrid);
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
