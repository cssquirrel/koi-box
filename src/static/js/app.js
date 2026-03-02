/** App initialization and view routing. */

import { initAudio } from './audio.js';
import { initControls, getVolume, applyVolumeState, applyLibraryState } from './controls.js';
import { initRadio, saveRadioState, restoreRadioState } from './radio.js';
import { initPlayer, enterPlayerMode, getActivePlaylistId, clearPlayerState } from './player.js';
import { initPlaylistPicker } from './playlist-picker.js';
import { initSettings } from './settings.js';
import { initWaveform } from './screen.js';
import { initWeather } from './weather.js';
import { initTheme } from './theme.js';
import * as api from './api.js';
import { $, on } from './utils.js';
import * as audio from './audio.js';

let mode = 'radio'; // 'radio' | 'player' | 'settings'
let drawerOpen = false;
let pendingDeletePlaylist = null; // { id, name } awaiting confirmation

/** Switch between radio, player, and settings views. */
function setView(v) {
  // Save radio state when leaving radio mode
  if (mode === 'radio' && v !== 'radio') {
    saveRadioState();
  }
  mode = v;
  $('radioView').classList.toggle('active', v === 'radio');
  $('playerView').classList.toggle('active', v === 'player');
  $('settingsView').classList.toggle('active', v === 'settings');
  $('radioReturnBtn').style.display = (v === 'player') ? '' : 'none';

  // Top bar: hide presets + weather in settings
  const hideInSettings = [$('presetGroup'), $('ambBtn'), $('libBtn'), $('autoBtn'), $('sunArc')];
  hideInSettings.forEach(el => { if (el) el.style.display = v === 'settings' ? 'none' : ''; });
  // Weather chip: only restore to 'flex' if it had content (i.e. was configured)
  const chip = $('weatherChip');
  if (chip) {
    if (v === 'settings') {
      chip.style.display = 'none';
    } else if ($('weatherTemp')?.textContent) {
      chip.style.display = 'flex';
    }
  }

  $('settingsBtn').classList.toggle('active', v === 'settings');
  $('statusText').textContent = v === 'settings' ? 'CONFIG' : v === 'player' ? 'PLAYER' : 'RADIO';

  if (v === 'settings') {
    $('statusDot').style.background = 'var(--fg-dim)';
  } else {
    $('statusDot').style.background = '';
  }
}

// ── New Playlist Modal ──

function openNewPlaylistModal() {
  const modal = $('newPlaylistModal');
  const input = $('newPlaylistInput');
  input.value = '';
  modal.classList.add('open');
  input.focus();
}

function closeNewPlaylistModal() {
  $('newPlaylistModal').classList.remove('open');
}

async function submitNewPlaylist() {
  const input = $('newPlaylistInput');
  const name = input.value.trim();
  if (!name) return;

  try {
    await api.createPlaylist(name);
    closeNewPlaylistModal();
    renderDrawer();
  } catch (e) {
    console.error('Failed to create playlist:', e);
  }
}

/** Render the playlist drawer. */
async function renderDrawer() {
  const scroll = $('drawerScroll');
  if (!scroll) return;

  try {
    const playlists = await api.getPlaylists();
    scroll.innerHTML = '';

    // Favorites auto-playlist (always first)
    const favItem = document.createElement('div');
    favItem.className = 'drawer-item' + (getActivePlaylistId() === 'favorites' && mode === 'player' ? ' active-pl' : '');
    favItem.innerHTML =
      '<div class="drawer-icon" style="background:linear-gradient(135deg,rgba(255,91,26,0.15),rgba(255,91,26,0.04));border:1px solid rgba(255,91,26,0.2);color:var(--accent)">\u2661</div>' +
      '<div class="drawer-item-info">' +
        '<div class="drawer-item-name">Favorites</div>' +
        '<div class="drawer-item-meta"><span class="drawer-item-auto">AUTO</span></div>' +
      '</div>';
    favItem.addEventListener('click', () => {
      drawerOpen = false;
      $('drawer').classList.remove('open');
      $('playlistsBtn').classList.remove('active');
      enterPlayerMode('favorites', 'Favorites');
      setView('player');
      renderDrawer();
    });
    scroll.appendChild(favItem);

    playlists.forEach(pl => {
      const d = document.createElement('div');
      d.className = 'drawer-item' + (getActivePlaylistId() === pl.id && mode === 'player' ? ' active-pl' : '');
      d.innerHTML =
        '<div class="drawer-icon" style="background:linear-gradient(135deg,rgba(255,91,26,0.2),rgba(255,91,26,0.06));border:1px solid rgba(255,91,26,0.2);color:var(--accent)">&#9834;</div>' +
        '<div class="drawer-item-info">' +
          '<div class="drawer-item-name">' + escapeHtml(pl.name) + '</div>' +
          '<div class="drawer-item-meta">' + pl.track_count + ' track' + (pl.track_count !== 1 ? 's' : '') + '</div>' +
        '</div>' +
        '<button class="drawer-item-delete" title="Delete playlist">&times;</button>';
      d.querySelector('.drawer-item-delete').addEventListener('click', (e) => {
        e.stopPropagation();
        showDeletePlaylistConfirm(pl);
      });
      d.addEventListener('click', () => {
        drawerOpen = false;
        $('drawer').classList.remove('open');
        $('playlistsBtn').classList.remove('active');
        enterPlayerMode(pl.id, pl.name);
        setView('player');
        renderDrawer();
      });
      scroll.appendChild(d);
    });
  } catch (e) {
    scroll.innerHTML = '<div style="padding:12px;font-size:11px;color:var(--fg-dim)">No playlists yet.</div>';
  }
}

function toggleDrawer() {
  drawerOpen = !drawerOpen;
  $('drawer').classList.toggle('open', drawerOpen);
  $('playlistsBtn').classList.toggle('active', drawerOpen);
  if (drawerOpen) renderDrawer();
}

function showDeletePlaylistConfirm(pl) {
  pendingDeletePlaylist = pl;
  const modal = $('deletePlaylistModal');
  const text = $('deletePlaylistText');
  if (!modal || !text) return;
  text.innerHTML =
    'Delete <span class="delete-confirm-track">' + escapeHtml(pl.name) + '</span>' +
    ' and remove all track associations?';
  modal.classList.add('open');
}

async function confirmDeletePlaylist() {
  const modal = $('deletePlaylistModal');
  if (modal) modal.classList.remove('open');
  if (!pendingDeletePlaylist) return;
  const pl = pendingDeletePlaylist;
  pendingDeletePlaylist = null;
  try {
    await api.deletePlaylist(pl.id);
    // If this playlist was playing, return to radio
    if (getActivePlaylistId() === pl.id && mode === 'player') {
      returnToRadio();
    }
    renderDrawer();
  } catch (e) {
    console.error('Failed to delete playlist:', e);
  }
}

function cancelDeletePlaylist() {
  const modal = $('deletePlaylistModal');
  if (modal) modal.classList.remove('open');
  pendingDeletePlaylist = null;
}

function returnToRadio() {
  setView('radio');
  drawerOpen = false;
  $('drawer').classList.remove('open');
  $('playlistsBtn').classList.remove('active');
  clearPlayerState();
  restoreRadioState();
}

/** Initialize the entire application. */
async function init() {
  // Theme first — prevents flash of wrong color scheme
  await initTheme();

  // Audio system
  initAudio();

  // UI controls (then restore saved volume)
  initControls();
  try {
    const volResult = await api.getSetting('volume_state');
    if (volResult && volResult.value) {
      applyVolumeState(volResult.value.volume, volResult.value.muted);
    }
  } catch (e) { /* use defaults */ }
  audio.setVolume(getVolume());

  // Restore library mode
  try {
    const libResult = await api.getSetting('library_mode');
    if (libResult && libResult.value) applyLibraryState(libResult.value);
  } catch (e) { /* use defaults */ }

  // View switching
  $('playlistsBtn').addEventListener('click', toggleDrawer);
  $('settingsBtn').addEventListener('click', () => {
    if (mode === 'settings') {
      setView('radio');
      restoreRadioState();
    } else {
      setView('settings');
      drawerOpen = false;
      $('drawer').classList.remove('open');
      $('playlistsBtn').classList.remove('active');
      initSettings();
    }
  });
  $('radioReturnBtn').addEventListener('click', returnToRadio);

  // Virtual playlist navigation (artist/album pages from radio)
  on('enter-virtual-playlist', (e) => {
    const { id, name } = e.detail;
    drawerOpen = false;
    $('drawer').classList.remove('open');
    $('playlistsBtn').classList.remove('active');
    saveRadioState();
    enterPlayerMode(id, name, 0, true);
    setView('player');
  });

  // New playlist modal
  $('newPlaylistBtn').addEventListener('click', () => openNewPlaylistModal());
  $('newPlaylistCancel').addEventListener('click', () => closeNewPlaylistModal());
  $('newPlaylistCancelBtn').addEventListener('click', () => closeNewPlaylistModal());
  $('newPlaylistCreateBtn').addEventListener('click', () => submitNewPlaylist());
  $('newPlaylistInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitNewPlaylist();
    if (e.key === 'Escape') closeNewPlaylistModal();
  });

  // Delete playlist modal
  $('deletePlaylistOk').addEventListener('click', () => confirmDeletePlaylist());
  $('deletePlaylistCancel').addEventListener('click', () => cancelDeletePlaylist());

  // Player subsystem
  initPlayer();
  initPlaylistPicker();

  // Radio mode (loads genres, presets, starts polling)
  await initRadio();

  // Restore player mode if app was closed with a playlist open
  try {
    const plResult = await api.getSetting('player_state');
    if (plResult && plResult.value && plResult.value.playlistId) {
      const { playlistId, playlistName, trackIdx } = plResult.value;
      await enterPlayerMode(playlistId, playlistName, trackIdx, false);
      setView('player');
    }
  } catch (e) { /* start in radio */ }

  // Weather chip (non-blocking)
  initWeather();

  // Progress bar seek (radio)
  $('radioProgressBar')?.addEventListener('click', (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    audio.seekTo(pct);
  });

  // Progress bar seek (player)
  $('playerProgressBar')?.addEventListener('click', (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    audio.seekTo(pct);
  });

  // Window controls (frameless mode)
  $('winMinBtn')?.addEventListener('click', () => {
    if (window.pywebview) window.pywebview.api.minimize();
  });
  $('winCloseBtn')?.addEventListener('click', () => {
    if (window.pywebview) window.pywebview.api.close();
    else window.close();
  });

  console.log('koibokksu v2 initialized');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', init);
