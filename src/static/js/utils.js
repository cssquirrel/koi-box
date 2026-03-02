/** Shared utility functions. */

/** Format seconds as m:ss */
export function formatTime(seconds) {
  if (!seconds || seconds < 0) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m + ':' + String(s).padStart(2, '0');
}

/** Get element by ID (short alias). */
export function $(id) {
  return document.getElementById(id);
}

/** Pick a random element from an array. */
export function randomChoice(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

/** SVG strings for play/pause icons (vidstack/icons, MIT). */
export const PAUSE_SVG = '<svg class="play-icon-svg" viewBox="0 0 32 32" fill="none"><path d="M8.667 6.667a.667.667 0 00-.667.666v17.334c0 .368.298.666.667.666h4c.368 0 .666-.298.666-.666V7.333a.667.667 0 00-.666-.666h-4zM19.333 6.667a.667.667 0 00-.666.666v17.334c0 .368.298.666.666.666h4c.369 0 .667-.298.667-.666V7.333a.667.667 0 00-.667-.666h-4z" fill="currentColor"/></svg>';
export const PLAY_SVG = '<svg class="play-icon-svg" viewBox="0 0 32 32" fill="none"><path d="M10.667 6.655c0-.547.622-.861 1.062-.536l12.648 9.345c.36.266.36.806 0 1.072L11.73 25.881c-.44.325-1.063.011-1.063-.536V6.655z" fill="currentColor"/></svg>';

/** Dispatch a custom event on document. */
export function emit(name, detail = {}) {
  document.dispatchEvent(new CustomEvent(name, { detail }));
}

/** Listen for a custom event on document. */
export function on(name, handler) {
  document.addEventListener(name, handler);
}

/** Strip "(feat. ...)" suffix from artist name. */
export function stripFeat(artist) {
  if (!artist) return '';
  return artist.replace(/\s*\(feat\..*?\)/gi, '').trim();
}

/** Debounce a function. */
export function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
