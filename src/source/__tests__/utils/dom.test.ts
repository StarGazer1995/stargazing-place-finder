import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { debounce, showToast } from '../../js/utils/dom';

describe('debounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('delays function execution until after the wait period', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced();
    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(99);
    expect(fn).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('resets the timer on subsequent calls', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced();
    vi.advanceTimersByTime(50);
    debounced(); // reset
    vi.advanceTimersByTime(50);
    expect(fn).not.toHaveBeenCalled(); // still waiting

    vi.advanceTimersByTime(50);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('passes arguments to the original function', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    debounced('a', 1, { key: 'val' });
    vi.advanceTimersByTime(100);

    expect(fn).toHaveBeenCalledWith('a', 1, { key: 'val' });
  });

  it('only executes once for rapid successive calls', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);

    for (let i = 0; i < 20; i++) {
      debounced(i);
      vi.advanceTimersByTime(10);
    }
    // After all rapid calls, only the last should be pending
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith(19);
  });

  it('clears previous timeout before setting new one', () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);
    const clearSpy = vi.spyOn(globalThis, 'clearTimeout');

    debounced();
    debounced();
    expect(clearSpy).toHaveBeenCalled();

    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe('showToast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    document.body.innerHTML = '';
  });

  it('creates a toast element with the correct class and message', () => {
    showToast('Test message', 'info');

    const toast = document.querySelector('.toast.toast-info') as HTMLElement;
    expect(toast).not.toBeNull();
    expect(toast.textContent).toBe('Test message');
    expect(toast.getAttribute('role')).toBe('status');
    expect(toast.getAttribute('aria-live')).toBe('polite');
  });

  it('defaults to type "info" when not specified', () => {
    showToast('Default type');

    const toast = document.querySelector('.toast.toast-info');
    expect(toast).not.toBeNull();
  });

  it('adds toast-visible class after creation (via reflow)', () => {
    showToast('Visible toast', 'success');

    const toast = document.querySelector('.toast.toast-success') as HTMLElement;
    expect(toast.classList.contains('toast-visible')).toBe(true);
  });

  it('removes the toast after the specified duration', () => {
    showToast('Ephemeral', 'error', 1000);

    let toast = document.querySelector('.toast');
    expect(toast).not.toBeNull();

    // Fast-forward past the visibility timeout
    vi.advanceTimersByTime(1000);
    // toast-visible removed
    expect(toast!.classList.contains('toast-visible')).toBe(false);

    // Fast-forward past the remove timeout (300ms)
    vi.advanceTimersByTime(300);
    toast = document.querySelector('.toast');
    expect(toast).toBeNull();
  });
});
