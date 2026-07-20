// =============================================================================
// DOM — utility functions (toast, loading indicator, debounce)
// =============================================================================

import { isLoading, loadingIndicator, setIsLoading, setLoadingIndicator } from '../state';

// ---------------------------------------------------------------------------
// Toast notifications
// ---------------------------------------------------------------------------

export type ToastType = 'info' | 'error' | 'success';

/**
 * Show a non-blocking toast notification that auto-dismisses.
 * @param message  Message text
 * @param type     Toast variant (default 'info')
 * @param duration Auto-dismiss delay in ms (default 3000)
 */
export function showToast(message: string, type: ToastType = 'info', duration: number = 3000): void {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  document.body.appendChild(toast);

  // Force reflow so the CSS transition triggers
  void toast.offsetWidth;
  toast.classList.add('toast-visible');

  setTimeout(() => {
    toast.classList.remove('toast-visible');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ---------------------------------------------------------------------------
// Loading indicator
// ---------------------------------------------------------------------------

/** Show the global loading indicator overlay. */
export function showLoadingIndicator(): void {
  if (!loadingIndicator) {
    setLoadingIndicator(document.querySelector('.loading-indicator'));
  }
  if (loadingIndicator) {
    loadingIndicator.classList.add('show');
  }
  setIsLoading(true);
}

/** Hide the global loading indicator overlay. */
export function hideLoadingIndicator(): void {
  if (loadingIndicator) {
    loadingIndicator.classList.remove('show');
  }
  setIsLoading(false);
}

// ---------------------------------------------------------------------------
// Debounce
// ---------------------------------------------------------------------------

/**
 * Create a debounced version of a function.
 * The returned function delays invoking `func` until `wait` ms have elapsed
 * since the last invocation.
 */
export function debounce<T extends (...args: any[]) => void>(
  func: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | undefined;
  return function executedFunction(...args: Parameters<T>): void {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
