// ═══════════════════════════════════════════════════════════════════════
//  DOM — 工具函数（toast、loading、防抖）
// ═══════════════════════════════════════════════════════════════════════

/**
 * Show a non-blocking toast notification that auto-dismisses.
 * @param {string} message - Message text
 * @param {'info'|'error'|'success'} type - Toast type
 * @param {number} duration - Auto-dismiss delay in ms (default 3000)
 */
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);

    // Trigger reflow for transition
    void toast.offsetWidth;
    toast.classList.add('toast-visible');

    setTimeout(() => {
        toast.classList.remove('toast-visible');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * 显示加载指示器
 */
function showLoadingIndicator() {
    if (!loadingIndicator) {
        loadingIndicator = document.querySelector('.loading-indicator');
    }
    if (loadingIndicator) {
        loadingIndicator.classList.add('show');
    }
    isLoading = true;
}

/**
 * 隐藏加载指示器
 */
function hideLoadingIndicator() {
    if (loadingIndicator) {
        loadingIndicator.classList.remove('show');
    }
    isLoading = false;
}

/**
 * 防抖函数
 * @param {Function} func - 需要防抖的函数
 * @param {number} wait - 等待时间（毫秒）
 * @returns {Function} 防抖后的函数
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
