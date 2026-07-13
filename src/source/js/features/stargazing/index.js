// ═══════════════════════════════════════════════════════════════════════
//  Stargazing selector — mode switching, status, init
// ═══════════════════════════════════════════════════════════════════════

/**
 * 更新状态指示器
 */
function updateStatus(message, type = 'info') {
    // Guard: status indicator must NEVER be shown outside analysis mode
    if (!isAnalysisMode || isTelescopeMode) return;

    let indicator = document.getElementById('status-indicator');
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.id = 'status-indicator';
        indicator.className = 'status-indicator';
        document.body.appendChild(indicator);
    }

    indicator.textContent = message;
    indicator.className = `status-indicator ${type}`;
    indicator.style.display = 'block';
    statusIndicator = indicator;

    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            if (indicator.textContent === message) {
                indicator.style.display = 'none';
            }
        }, 3000);
    } else {
        indicator.style.display = 'block';
    }
}

/**
 * 切换模式（浏览 / 分析）
 */
function toggleMode() {
    isAnalysisMode = !isAnalysisMode;
    const modeBtn = document.getElementById('mode-toggle-btn');

    if (isAnalysisMode) {
        modeBtn.textContent = '切换到浏览模式';
        modeBtn.classList.add('active');
        if (!drawControl) initializeDrawControls();
        updateStatus('已切换到分析模式，请绘制分析区域', 'info');
    } else {
        modeBtn.textContent = '切换到分析模式';
        modeBtn.classList.remove('active');
        clearAll();
    }

    syncPanelVisibility();
}

/**
 * 初始化观星区域选择器
 */
function initializeStargazingSelector() {
    const analyzeBtn = document.getElementById('analyze-button');
    const clearBtn = document.getElementById('clear-button');
    const modeToggleBtn = document.getElementById('mode-toggle-btn');

    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', analyzeStargazingArea);
        analyzeBtn.disabled = true;
    }
    if (clearBtn) {
        clearBtn.addEventListener('click', clearAll);
    }
    if (modeToggleBtn) {
        modeToggleBtn.addEventListener('click', toggleMode);
    }

    const controlPanel = document.querySelector('.control-panel');
    if (controlPanel) {
        controlPanel.style.display = 'none';
    }

    checkApiHealth();
}
