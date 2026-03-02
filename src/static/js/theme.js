/** Theme manager: applies light/dark theme based on user setting. */

import * as api from './api.js';
import { on } from './utils.js';
import { getSunTimes } from './weather.js';

let _mode = 'auto'; // 'light' | 'dark' | 'auto'

/**
 * Determine if it should be dark right now.
 * Uses sunrise/sunset from weather data, falls back to 7pm-7am.
 */
function shouldBeDark() {
  const now = new Date();
  const { sunrise, sunset } = getSunTimes();

  if (sunrise && sunset) {
    const rise = new Date(sunrise);
    const set = new Date(sunset);
    return now < rise || now >= set;
  }

  // Fallback: dark between 7pm (19:00) and 7am (07:00)
  const hour = now.getHours();
  return hour >= 19 || hour < 7;
}

/** Apply the data-theme attribute to <html>. */
function applyTheme() {
  let dark = false;
  if (_mode === 'dark') {
    dark = true;
  } else if (_mode === 'auto') {
    dark = shouldBeDark();
  }
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
}

/** Set theme mode and persist to backend. */
export async function setThemeMode(mode) {
  _mode = mode;
  applyTheme();
  try {
    await api.updateSetting('theme_mode', mode);
  } catch (e) {
    console.error('Failed to save theme_mode:', e);
  }
}

/** Get the current theme mode string. */
export function getThemeMode() {
  return _mode;
}

/** Initialize theme: load saved mode, apply, start auto-check timer. */
export async function initTheme() {
  try {
    const saved = await api.getSetting('theme_mode');
    if (saved.value && ['light', 'dark', 'auto'].includes(saved.value)) {
      _mode = saved.value;
    }
  } catch (e) {
    // Default to 'auto'
  }

  applyTheme();

  // Re-check every 60s for auto mode sunrise/sunset transitions
  setInterval(applyTheme, 60_000);

  // Re-apply when weather data refreshes (sunrise/sunset may have updated)
  on('weather:updated', applyTheme);
}
