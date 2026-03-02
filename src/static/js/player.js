/** Playlist view logic: tracklist rendering, transport. */

import * as api from './api.js';
import * as audio from './audio.js';
import { setPlayIcons, isShuffleOn, isLoopOn } from './controls.js';
import { updatePlayerScreen, updatePlayerProgress, initWaveform, updateWaveformCursor, setWaveformPlaying } from './screen.js';
import { $, formatTime, on, emit, stripFeat } from './utils.js';

let activePlaylistId = null;
let activePlaylistName = '';
let playlistTracks = [];
let playerTrackIdx = 0;
let isPlaying = false;

// Track being targeted by the playlist picker
let pickerTargetTrack = null;

// Delete confirmation state
let pendingDeleteIdx = null;

export function getActivePlaylistId() { return activePlaylistId; }

/** Pick next track index: random if shuffle is on, otherwise sequential. */
function _nextTrackIdx() {
  const len = playlistTracks.length;
  if (len <= 1) return 0;
  if (isShuffleOn()) {
    let next;
    do { next = Math.floor(Math.random() * len); } while (next === playerTrackIdx);
    return next;
  }
  return (playerTrackIdx + 1) % len;
}

function getPlaylistType(id) {
  if (id === 'favorites') return 'favorites';
  if (typeof id === 'string' && id.startsWith('artist:')) return 'artist';
  if (typeof id === 'string' && id.startsWith('album:')) return 'album';
  return 'playlist';
}

function isReadOnlyPlaylist(id) {
  const t = getPlaylistType(id);
  return t === 'artist' || t === 'album';
}

/** Enter player mode with a specific playlist.
 *  @param {string|number} playlistId
 *  @param {string} playlistName
 *  @param {number} startIdx - track index to start at (default 0)
 *  @param {boolean} autoplay - whether to auto-play (default true)
 */
export async function enterPlayerMode(playlistId, playlistName, startIdx = 0, autoplay = true) {
  activePlaylistId = playlistId;
  activePlaylistName = playlistName;

  try {
    const plType = getPlaylistType(playlistId);
    if (plType === 'favorites') {
      playlistTracks = await api.getFavoritesTracks();
    } else if (plType === 'artist') {
      playlistTracks = await api.getArtistTracks(playlistId.slice(7));
    } else if (plType === 'album') {
      playlistTracks = await api.getAlbumTracks(parseInt(playlistId.slice(6), 10));
    } else {
      playlistTracks = await api.getPlaylistTracks(playlistId);
    }
  } catch (e) {
    console.error('Failed to load playlist tracks:', e);
    playlistTracks = [];
    return;
  }

  if (playlistTracks.length === 0) {
    playerTrackIdx = 0;
    updatePlayerScreen(null, playlistName, 0, 0);
    renderTracklist();
    savePlayerState();
    return;
  }

  playerTrackIdx = Math.min(startIdx, playlistTracks.length - 1);
  const track = playlistTracks[playerTrackIdx];

  updatePlayerScreen(track, playlistName, playerTrackIdx, playlistTracks.length);
  renderTracklist();

  const url = api.audioUrl(track.filename);
  audio.loadTrack(url, autoplay);
  isPlaying = autoplay;
  setPlayIcons(autoplay);
  initWaveform('playerWaveform', track.waveform);
  setWaveformPlaying('playerWaveform', autoplay);

  if (autoplay) {
    $('statusDot').classList.add('playing');
    $('powerLed').classList.remove('off');
  }

  savePlayerState();
}

/** Render the tracklist in the player view. */
function renderTracklist() {
  const tl = $('tracklist');
  if (!tl) return;
  tl.innerHTML = '';

  const totalSecs = playlistTracks.reduce((sum, t) => sum + (t.duration || 0), 0);
  const tracklistMeta = $('tracklistMeta');
  if (tracklistMeta) {
    tracklistMeta.textContent = Math.floor(totalSecs / 60) + ' MIN';
  }

  const readOnly = isReadOnlyPlaylist(activePlaylistId);

  playlistTracks.forEach((t, i) => {
    const isCur = i === playerTrackIdx;
    const row = document.createElement('div');
    row.className = 'tracklist-item' + (isCur ? ' playing-track' : '');
    row.innerHTML =
      '<div class="tracklist-num ' + (isCur ? 'active-num' : '') + '">' +
        (isCur && isPlaying
          ? '<div class="tracklist-bars"><div style="height:7px;animation-duration:1s"></div><div style="height:11px;animation-duration:1.3s"></div><div style="height:5px;animation-duration:0.8s"></div></div>'
          : (i + 1)) +
      '</div>' +
      '<div class="tracklist-title-col">' +
        '<div class="tracklist-title ' + (isCur ? 'active-title' : '') + '">' + escapeHtml(t.title) + '</div>' +
      '</div>' +
      '<span class="tracklist-artist">' + escapeHtml(stripFeat(t.artist)) + '</span>' +
      '<span class="tracklist-album">' + (t.album_name ? escapeHtml(t.album_name) : '') + '</span>' +
      '<span class="tracklist-dur">' + formatTime(t.duration) + '</span>' +
      '<div class="tracklist-actions">' +
        '<button class="tracklist-add-pl" title="Add to playlist" data-idx="' + i + '">+</button>' +
        (readOnly ? '' : '<button class="tracklist-remove" title="Remove" data-idx="' + i + '">&times;</button>') +
      '</div>';

    row.addEventListener('click', (e) => {
      if (e.target.closest('.tracklist-actions')
          || e.target.closest('.tracklist-artist') || e.target.closest('.tracklist-album')) return;
      playerTrackIdx = i;
      playCurrentTrack();
    });

    if (!readOnly) {
      row.querySelector('.tracklist-remove').addEventListener('click', (e) => {
        e.stopPropagation();
        showDeleteConfirm(i);
      });
    }

    row.querySelector('.tracklist-add-pl').addEventListener('click', (e) => {
      e.stopPropagation();
      openPlayerPlaylistPicker(t);
    });

    // Clickable artist name → artist page
    const artistEl = row.querySelector('.tracklist-artist');
    if (artistEl) {
      artistEl.addEventListener('click', (e) => {
        e.stopPropagation();
        const base = stripFeat(t.artist);
        if (base) enterPlayerMode('artist:' + base, base, 0, true);
      });
    }

    // Clickable album name → album page
    const albumEl = row.querySelector('.tracklist-album');
    if (albumEl && t.album_id) {
      albumEl.addEventListener('click', (e) => {
        e.stopPropagation();
        enterPlayerMode('album:' + t.album_id, t.album_name, 0, true);
      });
    }

    tl.appendChild(row);
  });

  // Add track row (only for regular playlists)
  if (getPlaylistType(activePlaylistId) === 'playlist') {
    const addRow = document.createElement('div');
    addRow.className = 'tracklist-add-row';
    addRow.innerHTML = '<span class="plus-icon">+</span> ADD TRACK';
    addRow.addEventListener('click', () => emit('open-track-picker', { playlistId: activePlaylistId }));
    tl.appendChild(addRow);
  }
}

function playCurrentTrack() {
  const track = playlistTracks[playerTrackIdx];
  if (!track) return;
  updatePlayerScreen(track, activePlaylistName, playerTrackIdx, playlistTracks.length);
  renderTracklist();
  const url = api.audioUrl(track.filename);
  audio.loadTrack(url, true);
  isPlaying = true;
  setPlayIcons(true);
  initWaveform('playerWaveform', track.waveform);
  setWaveformPlaying('playerWaveform', true);
  savePlayerState();
}

async function removeTrack(idx) {
  const track = playlistTracks[idx];

  if (activePlaylistId === 'favorites') {
    // Unfavorite the track
    try {
      await api.updateTrackStatus(track.id, 'active');
    } catch (e) {
      console.error('Failed to unfavorite track:', e);
      return;
    }
  } else {
    // Remove from playlist
    try {
      await api.removeTrackFromPlaylist(activePlaylistId, track.id);
    } catch (e) {
      console.error('Failed to remove track:', e);
      return;
    }
  }

  const wasPlaying = idx === playerTrackIdx;
  playlistTracks.splice(idx, 1);

  if (playlistTracks.length === 0) {
    updatePlayerScreen(null, activePlaylistName, 0, 0);
    renderTracklist();
    audio.stop();
    isPlaying = false;
    setPlayIcons(false);
    savePlayerState();
    return;
  }

  if (wasPlaying) {
    playerTrackIdx = Math.min(playerTrackIdx, playlistTracks.length - 1);
    playCurrentTrack();
  } else if (idx < playerTrackIdx) {
    playerTrackIdx--;
  }

  renderTracklist();
  savePlayerState();
}

// ── Per-track playlist picker ──

async function openPlayerPlaylistPicker(track) {
  pickerTargetTrack = track;
  const picker = $('playerPlaylistPicker');
  const scroll = $('playerPlaylistPickerScroll');
  if (!picker || !scroll) return;

  scroll.innerHTML = '<div style="padding:20px;text-align:center;color:var(--fg-dim);font-size:11px">Loading...</div>';
  picker.classList.add('open');

  try {
    const playlists = await api.getPlaylists();
    scroll.innerHTML = '';

    if (playlists.length === 0) {
      scroll.innerHTML = '<div style="padding:20px;text-align:center;color:var(--fg-dim);font-size:11px">No playlists yet.</div>';
      return;
    }

    playlists.forEach(pl => {
      const item = document.createElement('div');
      item.className = 'playlist-picker-item';
      item.innerHTML =
        '<div class="playlist-picker-icon">\u266B</div>' +
        '<div class="playlist-picker-info">' +
          '<div class="playlist-picker-name">' + escapeHtml(pl.name) + '</div>' +
          '<div class="playlist-picker-meta">' + pl.track_count + ' track' + (pl.track_count !== 1 ? 's' : '') + '</div>' +
        '</div>';
      item.addEventListener('click', () => addTrackToPickedPlaylist(pl, item));
      scroll.appendChild(item);
    });

    // Also show Favorites option
    const favItem = document.createElement('div');
    favItem.className = 'playlist-picker-item';
    favItem.innerHTML =
      '<div class="playlist-picker-icon">\u2661</div>' +
      '<div class="playlist-picker-info">' +
        '<div class="playlist-picker-name">Favorites</div>' +
        '<div class="playlist-picker-meta">AUTO</div>' +
      '</div>';
    favItem.addEventListener('click', async () => {
      if (!pickerTargetTrack) return;
      try {
        await api.updateTrackStatus(pickerTargetTrack.id, 'favorited');
        const badge = document.createElement('span');
        badge.className = 'playlist-picker-badge';
        badge.textContent = 'FAVORITED';
        favItem.appendChild(badge);
        setTimeout(closePlayerPlaylistPicker, 600);
      } catch (e) {
        console.error('Failed to favorite track:', e);
      }
    });
    // Insert favorites at the top
    scroll.insertBefore(favItem, scroll.firstChild);
  } catch (e) {
    scroll.innerHTML = '<div style="padding:20px;text-align:center;color:var(--fg-dim);font-size:11px">Failed to load playlists.</div>';
  }
}

async function addTrackToPickedPlaylist(pl, itemEl) {
  if (!pickerTargetTrack) return;
  try {
    await api.addTrackToPlaylist(pl.id, pickerTargetTrack.id);
    const badge = document.createElement('span');
    badge.className = 'playlist-picker-badge';
    badge.textContent = 'ADDED';
    itemEl.appendChild(badge);
    setTimeout(closePlayerPlaylistPicker, 600);
  } catch (e) {
    if (e.message && e.message.includes('409')) {
      const badge = document.createElement('span');
      badge.className = 'playlist-picker-badge';
      badge.textContent = 'ALREADY IN';
      itemEl.appendChild(badge);
    } else {
      console.error('Failed to add track to playlist:', e);
    }
  }
}

function closePlayerPlaylistPicker() {
  const picker = $('playerPlaylistPicker');
  if (picker) picker.classList.remove('open');
  pickerTargetTrack = null;
}

// ── Player state persistence ──

function savePlayerState() {
  api.updateSetting('player_state', {
    playlistId: activePlaylistId,
    playlistName: activePlaylistName,
    trackIdx: playerTrackIdx,
  }).catch(() => {});
}

export function clearPlayerState() {
  api.updateSetting('player_state', null).catch(() => {});
}

// ── Delete confirmation ──

function showDeleteConfirm(idx) {
  const track = playlistTracks[idx];
  if (!track) return;
  pendingDeleteIdx = idx;
  const modal = $('deleteConfirmModal');
  const text = $('deleteConfirmText');
  if (!modal || !text) return;

  const action = activePlaylistId === 'favorites' ? 'Unfavorite' : 'Remove';
  text.innerHTML =
    '<span class="delete-confirm-action">' + action + '</span> ' +
    '<span class="delete-confirm-track">' + escapeHtml(track.title) + '</span>' +
    '<span class="delete-confirm-by"> by ' + escapeHtml(stripFeat(track.artist)) + '</span>?';
  modal.classList.add('open');
}

function confirmDelete() {
  const modal = $('deleteConfirmModal');
  if (modal) modal.classList.remove('open');
  if (pendingDeleteIdx !== null) {
    removeTrack(pendingDeleteIdx);
    pendingDeleteIdx = null;
  }
}

function cancelDelete() {
  const modal = $('deleteConfirmModal');
  if (modal) modal.classList.remove('open');
  pendingDeleteIdx = null;
}

/** Handle player-specific events. */
export function initPlayer() {
  // Handle track added from picker overlay
  document.addEventListener('picker-track-selected', async (e) => {
    const { track } = e.detail;
    if (!activePlaylistId || !track) return;
    try {
      await api.addTrackToPlaylist(activePlaylistId, track.id);
      playlistTracks = await api.getPlaylistTracks(activePlaylistId);
      renderTracklist();
    } catch (err) {
      console.error('Failed to add track to playlist:', err);
    }
  });

  // Close per-track playlist picker
  $('playerPlaylistPickerClose')?.addEventListener('click', closePlayerPlaylistPicker);

  // Delete confirmation modal
  $('deleteConfirmOk')?.addEventListener('click', confirmDelete);
  $('deleteConfirmCancel')?.addEventListener('click', cancelDelete);

  // OLED artist/album click → virtual playlist
  $('playerTrackArtist')?.addEventListener('click', () => {
    const track = playlistTracks[playerTrackIdx];
    if (!track) return;
    const base = stripFeat(track.artist);
    if (base) enterPlayerMode('artist:' + base, base, 0, true);
  });

  $('playerTrackAlbum')?.addEventListener('click', () => {
    const track = playlistTracks[playerTrackIdx];
    if (!track) return;
    if (track.album_name && track.album_id) {
      enterPlayerMode('album:' + track.album_id, track.album_name, 0, true);
    }
  });

  on('toggle-play', () => {
    if (!$('playerView').classList.contains('active')) return;
    isPlaying = audio.togglePlay();
    setPlayIcons(isPlaying);
    $('statusDot').classList.toggle('playing', isPlaying);
    $('powerLed').classList.toggle('off', !isPlaying);
    setWaveformPlaying('playerWaveform', isPlaying);
  });

  on('pl-skip-forward', () => {
    if (playlistTracks.length === 0) return;
    playerTrackIdx = _nextTrackIdx();
    playCurrentTrack();
  });

  on('pl-skip-back', () => {
    if (playlistTracks.length === 0) return;
    playerTrackIdx = playerTrackIdx > 0 ? playerTrackIdx - 1 : playlistTracks.length - 1;
    playCurrentTrack();
  });

  on('audio-timeupdate', (e) => {
    if ($('playerView').classList.contains('active')) {
      const { currentTime, duration } = e.detail;
      updatePlayerProgress(currentTime, duration);
      if (duration > 0) {
        updateWaveformCursor('playerWaveform', currentTime / duration);
      }
    }
  });

  on('audio-ended', () => {
    if (!$('playerView').classList.contains('active')) return;
    if (playlistTracks.length === 0) return;
    if (isLoopOn()) {
      playCurrentTrack();
      return;
    }
    playerTrackIdx = _nextTrackIdx();
    playCurrentTrack();
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

