/** Track picker overlay for add-to-playlist. */

import * as api from './api.js';
import { $, formatTime, on } from './utils.js';

/** Initialize the track picker. */
export function initPlaylistPicker() {
  $('trackPickerClose').addEventListener('click', close);
  on('open-track-picker', (e) => open(e.detail ? e.detail.playlistId : null));
}

async function open(playlistId) {
  const picker = $('trackPicker');
  const scroll = $('trackPickerScroll');
  if (!picker || !scroll) return;

  scroll.innerHTML = '<div style="padding:20px;text-align:center;color:var(--fg-dim);font-size:12px">Loading tracks...</div>';
  picker.classList.add('open');

  try {
    // Fetch available tracks and current playlist tracks in parallel
    const [allTracks, playlistTracks] = await Promise.all([
      api.getTracks({ status: 'favorited', limit: 50 }),
      playlistId ? api.getPlaylistTracks(playlistId) : Promise.resolve([]),
    ]);

    const existingIds = new Set(playlistTracks.map(t => t.id));
    scroll.innerHTML = '';

    if (allTracks.length === 0) {
      scroll.innerHTML = '<div style="padding:20px;text-align:center;color:var(--fg-dim);font-size:12px">No favorited tracks available.</div>';
      return;
    }

    allTracks.forEach(t => {
      const isAdded = existingIds.has(t.id);
      const item = document.createElement('div');
      item.className = 'track-picker-item' + (isAdded ? ' added' : '');

      const artStyle = t.album_cover_url
        ? 'background-image:url(' + t.album_cover_url + ')'
        : 'background:var(--screen-dim)';

      item.innerHTML =
        '<div class="track-picker-item-art" style="' + artStyle + '"></div>' +
        '<div class="track-picker-item-info">' +
          '<div class="track-picker-item-title">' + escapeHtml(t.title) + '</div>' +
          '<div class="track-picker-item-artist">' + escapeHtml(t.artist) + '</div>' +
        '</div>' +
        '<span class="track-picker-item-dur">' + formatTime(t.duration) + '</span>' +
        (isAdded ? '<span class="track-picker-item-added">ADDED</span>' : '');

      if (!isAdded) {
        item.addEventListener('click', () => {
          document.dispatchEvent(new CustomEvent('picker-track-selected', { detail: { track: t } }));
          item.classList.add('added');
          const badge = document.createElement('span');
          badge.className = 'track-picker-item-added';
          badge.textContent = 'ADDED';
          item.appendChild(badge);
          existingIds.add(t.id);
        });
      }

      scroll.appendChild(item);
    });
  } catch (e) {
    scroll.innerHTML = '<div style="padding:20px;text-align:center;color:var(--fg-dim);font-size:12px">Failed to load tracks.</div>';
  }
}

function close() {
  $('trackPicker').classList.remove('open');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}
