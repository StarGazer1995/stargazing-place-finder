// =============================================================================
// Stargazing Index — mode toggling and status bar
// =============================================================================

import {
  isAnalysisMode, isTelescopeMode, drawControl,
  statusIndicator,
  setIsAnalysisMode, setStatusIndicator,
} from '../../state';
import { clearAll, initializeDrawControls } from './draw';
import { analyzeStargazingArea, checkApiHealth } from './analyzer';

// ---------------------------------------------------------------------------
// Status bar
// ---------------------------------------------------------------------------

export type StatusType = 'info' | 'loading' | 'success' | 'error';

/** Update the floating status bar text and style. */
/* c8 ignore start — DOM mode toggling + event binding: requires full browser environment */
export function updateStatus(message: string, type: StatusType = 'info'): void {
  const el = document.getElementById('analysis-status');
  if (!el) return;

  el.textContent = message;
  el.className = `status-bar status-${type}`;
}

// ---------------------------------------------------------------------------
// Mode toggle
// ---------------------------------------------------------------------------

/** Toggle analysis mode on/off, showing/hiding the draw control. */
export function toggleMode(): void {
  if (isTelescopeMode) return; // Don't toggle analysis while telescope is active

  setIsAnalysisMode(!isAnalysisMode);

  if (isAnalysisMode) {
    if (drawControl) {
      map.addControl(drawControl);
    }
  } else {
    if (drawControl) {
      map.removeControl(drawControl);
    }
    clearAll();
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
  const modeBtn = document.getElementById('mode-toggle');
  if (modeBtn) {
    modeBtn.addEventListener('click', toggleMode);
  }

  // Initialize draw controls
  initializeDrawControls();

  // Pre-flight health check
  checkApiHealth();
}

// Import needed for toggleMode
import { map } from '../../state';
