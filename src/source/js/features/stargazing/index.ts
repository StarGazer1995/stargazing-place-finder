// =============================================================================
// Stargazing Index — mode toggling and status bar
// =============================================================================

import {
  isAnalysisMode, isTelescopeMode, drawControl,
  setIsAnalysisMode,
} from '../../state';
import { clearAll, initializeDrawControls, startDrawing, stopDrawing } from './draw';
import { analyzeStargazingArea, cancelAreaAnalysis, checkApiHealth } from './analyzer';

import { toggleTelescopeMode } from '../telescope/telescope-ui';
import { getText } from '../../core/i18n';

// ---------------------------------------------------------------------------
// Status bar
// ---------------------------------------------------------------------------

export type StatusType = 'info' | 'loading' | 'success' | 'error';

/** Update the floating status bar text and style. */
/* c8 ignore start — DOM mode toggling + event binding: requires full browser environment */
export function updateStatus(message: string, type: StatusType = 'info'): void {
  const el = document.getElementById('status-indicator');
  if (!el) return;

  el.textContent = message;
  el.className = `status-indicator ${type}`;
  el.style.display = 'block';
}

// ---------------------------------------------------------------------------
// Mode toggle
// ---------------------------------------------------------------------------

/** Toggle analysis mode on/off, showing/hiding the draw control. */
export async function toggleMode(): Promise<void> {
  if (isTelescopeMode) {
    await toggleTelescopeMode();
    if (isAnalysisMode) return;
  }

  setIsAnalysisMode(!isAnalysisMode);
  const panel = document.getElementById('stargazing-control-panel');
  const button = document.getElementById('mode-toggle-btn');

  if (isAnalysisMode) {
    if (drawControl) {
      map.addControl(drawControl);
    }
    if (panel) panel.style.display = 'block';
    button?.classList.add('active');
    button?.setAttribute('aria-pressed', 'true');
    updateStatus(getText('ui.drawPrompt'), 'info');
  } else {
    if (drawControl) {
      map.removeControl(drawControl);
    }
    stopDrawing();
    cancelAreaAnalysis();
    document.getElementById('status-indicator')!.style.display = 'none';
    if (panel) panel.style.display = 'none';
    button?.classList.remove('active');
    button?.setAttribute('aria-pressed', 'false');
  }
}

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------

/**
 * Initialize the stargazing analysis subsystem.
 * Called once at page load.
 */
export function initializeStargazingSelector(): void {
  // Wire up the analyze button
  const analyzeBtn = document.getElementById('analyze-button');
  if (analyzeBtn) {
    analyzeBtn.addEventListener('click', analyzeStargazingArea);
  }

  // Wire up the clear button
  const clearBtn = document.getElementById('clear-button');
  if (clearBtn) {
    clearBtn.addEventListener('click', clearAll);
  }

  // Wire up the mode toggle
  const modeBtn = document.getElementById('mode-toggle-btn');
  if (modeBtn) {
    modeBtn.addEventListener('click', toggleMode);
  }

  document.getElementById('draw-area-button')?.addEventListener('click', startDrawing);
  document.getElementById('cancel-draw-button')?.addEventListener('click', stopDrawing);
  document.getElementById('cancel-analysis-button')?.addEventListener('click', () => cancelAreaAnalysis(true));

  // Initialize draw controls
  initializeDrawControls();

  // Pre-flight health check
  checkApiHealth();
}

// Import needed for toggleMode
import { map } from '../../state';
