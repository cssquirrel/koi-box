/** Radio view logic: genre switching, now-playing, last-track, preview mode. */

import * as api from './api.js';
import * as audio from './audio.js';
import { initBand, getCurrentGenre, getCurrentGenreIdx, getCurrentCategory, isAllMode, setCurrentGenreIdx, getCategoryVariants, restorePreset, getOledColor } from './band.js';
import { setPlayIcons, refreshStatus, applyLibraryState } from './controls.js';
import { initAutopilot, isAutopilotOn, disengageAutopilot, onTrackEnd as autopilotTrackEnd } from './autopilot.js';
import { updateRadioScreen, updateRadioProgress, updateScreenGenre, initWaveform, updateWaveformCursor, setWaveformPlaying, updateSignalDots, setOledAccent } from './screen.js';
import { $, on, emit, formatTime, stripFeat } from './utils.js';

let genres = [];
let currentTrack = null;
let isPlaying = false;
let lastPlayedTrack = null;
let skipping = false; // lock to prevent concurrent skip calls

// Preview mode state
let previewMode = false;
let savedMainState = null; // { url, currentTime, track }

// Preset state
let presetData = [null, null, null, null, null, null];
let activePresetIdx = null;
let presetLoadInProgress = false;
let tooltipEl = null;

/** Initialize radio mode. */
export async function initRadio() {
  try {
    genres = await api.getGenres();
  } catch (e) {
    console.error('Failed to load genres:', e);
    genres = [];
  }

  // Try to restore saved genre selection
  let savedState = null;
  try {
    const result = await api.getSetting('last_genre_selection');
    if (result && result.value) {
      savedState = result.value;
    }
  } catch (e) { /* no saved state, use defaults */ }

  initBand(genres, savedState);
  const initOled = getOledColor();
  if (initOled) setOledAccent('#' + initOled);
  showBufferingOverlay();

  if (genres.length > 0) {
    const genre = getCurrentGenre();
    const cat = getCurrentCategory();
    const genreId = (genre && genre._isAll) ? 'all' : (genre ? genre.id : genres[0].id);
    try {
      await api.switchGenre(genreId, cat);
    } catch (e) {
      console.error('Failed to set initial genre:', e);
    }
    if (genre && genre._isAll) {
      $('screenGenre').textContent = cat.toUpperCase() + ' / SHUFFLE';
    } else if (genre) {
      updateScreenGenre(genre.id);
    }
  }

  initPresets();
  initWaveform('waveform');
  initLastTrackControls();
  initAutopilot();

  on('genre-switched', handleGenreSwitch);
  on('toggle-play', handleTogglePlay);
  on('skip-forward', handleSkipForward);
  on('skip-back', handleSkipBack);
  on('track-favorite', handleFavorite);
  on('track-dislike', handleDislike);
  on('audio-timeupdate', handleTimeUpdate);
  on('audio-ended', handleTrackEnded);
  on('volume-change', handleVolumeChange);
  on('add-to-playlist', handleAddToPlaylist);
  on('audio-autoplay-blocked', handleAutoplayBlocked);

  const closeBtn = $('playlistPickerClose');
  if (closeBtn) closeBtn.addEventListener('click', closePlaylistPicker);

  // Artist name click → virtual artist playlist
  $('trackArtist')?.addEventListener('click', () => {
    if (!currentTrack) return;
    const base = stripFeat(currentTrack.artist);
    if (base) emit('enter-virtual-playlist', { id: 'artist:' + base, name: base });
  });

  pollForTracks();
}

/** Wire up last-track section buttons. */
function initLastTrackControls() {
  $('lastTrackLike')?.addEventListener('click', () => toggleLastTrackStatus('favorited'));
  $('lastTrackDislike')?.addEventListener('click', () => toggleLastTrackStatus('disliked'));
  $('lastTrackReplay')?.addEventListener('click', togglePreview);
}

/** Toggle favorite/dislike on the last played track. */
async function toggleLastTrackStatus(targetStatus) {
  if (!lastPlayedTrack) return;
  const current = lastPlayedTrack.status;
  const newStatus = (current === targetStatus) ? 'active' : targetStatus;
  try {
    await api.updateTrackStatus(lastPlayedTrack.id, newStatus);
    lastPlayedTrack.status = newStatus;
    updateLastTrackUI();
  } catch (e) {
    console.error('Failed to update last track status:', e);
  }
}

/** Update the last-track strip UI. */
function updateLastTrackUI() {
  const titleEl = $('lastTrackTitle');
  const likeBtn = $('lastTrackLike');
  const dislikeBtn = $('lastTrackDislike');

  if (!lastPlayedTrack) {
    if (titleEl) titleEl.textContent = '--';
    likeBtn?.classList.remove('active');
    dislikeBtn?.classList.remove('active');
    return;
  }

  if (titleEl) titleEl.textContent = lastPlayedTrack.title || '--';
  likeBtn?.classList.toggle('active', lastPlayedTrack.status === 'favorited');
  dislikeBtn?.classList.toggle('active', lastPlayedTrack.status === 'disliked');
}

/** Update the BUF count display. */
function updateBufCount(count) {
  const el = $('lastTrackBufCount');
  if (el) el.textContent = count;
}

// ── Preview mode ──

function togglePreview() {
  if (previewMode) {
    stopPreview();
  } else {
    startPreview();
  }
}

function startPreview() {
  if (!lastPlayedTrack || !currentTrack) return;
  previewMode = true;

  // Save main track state
  savedMainState = {
    url: api.audioUrl(currentTrack.filename),
    currentTime: audio.getCurrentTime(),
    track: currentTrack,
  };

  // Pause main track
  audio.pause();
  isPlaying = false;

  // Load and play preview track
  const url = api.audioUrl(lastPlayedTrack.filename);
  audio.loadTrack(url, true);

  // Update replay button to stop icon
  const replayBtn = $('lastTrackReplay');
  if (replayBtn) {
    replayBtn.textContent = '\u25A0'; // ■ stop icon
    replayBtn.classList.add('active');
  }

  // Show timer
  const timer = $('lastTrackTimer');
  if (timer) {
    timer.textContent = '0:00';
    timer.classList.add('active');
  }
}

function stopPreview() {
  if (!previewMode || !savedMainState) return;
  previewMode = false;

  // Stop preview audio
  audio.pause();

  // Restore main track at saved position
  audio.loadTrackAt(savedMainState.url, savedMainState.currentTime, true);
  isPlaying = true;
  setPlayIcons(true);
  $('statusDot')?.classList.add('playing');
  $('powerLed')?.classList.remove('off');
  setWaveformPlaying('waveform', true);

  // Reset replay button
  const replayBtn = $('lastTrackReplay');
  if (replayBtn) {
    replayBtn.textContent = '\u25C0\u25C0'; // ◀◀
    replayBtn.classList.remove('active');
  }

  // Hide timer
  const timer = $('lastTrackTimer');
  if (timer) timer.classList.remove('active');

  savedMainState = null;
}

// ── Overlays ──

function showBufferingOverlay() {
  const overlay = $('tuningOverlay');
  if (!overlay) return;
  overlay.classList.add('active');
  $('tuningText').textContent = 'BUFFERING';
  $('tuningSignal').textContent = 'WAITING FOR TRACKS...';
  $('tuningFill').style.width = '100%';
}

function hideOverlay() {
  const overlay = $('tuningOverlay');
  if (overlay) overlay.classList.remove('active');
}

// ── Presets ──

async function initPresets() {
  const group = $('presetGroup');
  if (!group) return;
  group.innerHTML = '';

  try {
    const result = await api.getSetting('radio_presets');
    if (result && result.value && Array.isArray(result.value)) {
      presetData = result.value;
      while (presetData.length < 6) presetData.push(null);
    }
  } catch (e) { /* no saved presets */ }

  for (let i = 0; i < 6; i++) {
    createPresetButton(group, i);
  }
}

function createPresetButton(container, slotIdx) {
  const wrap = document.createElement('div');
  wrap.className = 'preset-wrap';

  const btn = document.createElement('button');
  btn.className = 'preset-btn';
  btn.dataset.preset = slotIdx;
  btn.textContent = slotIdx + 1;
  applyPresetVisual(btn, slotIdx);

  let pressTimer = null;
  let longFired = false;

  btn.addEventListener('pointerdown', () => {
    longFired = false;
    pressTimer = setTimeout(() => {
      longFired = true;
      saveToPreset(slotIdx, btn);
    }, 800);
  });
  btn.addEventListener('pointerup', () => {
    clearTimeout(pressTimer);
    if (!longFired) loadPreset(slotIdx);
  });
  btn.addEventListener('pointerleave', () => clearTimeout(pressTimer));

  btn.addEventListener('mouseenter', () => showPresetTooltip(btn, slotIdx));
  btn.addEventListener('mouseleave', hidePresetTooltip);

  wrap.appendChild(btn);
  container.appendChild(wrap);
}

function applyPresetVisual(btn, slotIdx) {
  const saved = !!presetData[slotIdx];
  btn.classList.toggle('preset-empty', !saved);
  btn.classList.toggle('preset-saved', saved);
  btn.classList.toggle('active', activePresetIdx === slotIdx);
}

function refreshAllPresetVisuals() {
  document.querySelectorAll('.preset-btn').forEach(btn => {
    applyPresetVisual(btn, parseInt(btn.dataset.preset, 10));
  });
}

function loadPreset(slotIdx) {
  const data = presetData[slotIdx];
  if (!data) return;

  // Loading a preset is a manual action — disengage autopilot
  if (isAutopilotOn()) {
    disengageAutopilot();
    $('autoBtn').classList.remove('active');
    refreshStatus();
  }

  presetLoadInProgress = true;
  const switched = restorePreset(data.category, data.variantIdx);

  activePresetIdx = slotIdx;
  refreshAllPresetVisuals();

  if (switched) {
    const clear = () => { presetLoadInProgress = false; };
    // genre-switched fires after tuning animation; listen once to clear flag
    const handler = () => { clear(); document.removeEventListener('genre-switched', handler); };
    document.addEventListener('genre-switched', handler);
    // safety fallback in case event never fires
    setTimeout(clear, 5000);
  } else {
    presetLoadInProgress = false;
  }
}

function saveToPreset(slotIdx, btn) {
  const existing = presetData[slotIdx];
  const currentCat = getCurrentCategory();
  const currentIdx = getCurrentGenreIdx();

  // If this preset already matches the current station, clear it
  if (existing && existing.category === currentCat && existing.variantIdx === currentIdx) {
    presetData[slotIdx] = null;
    if (activePresetIdx === slotIdx) activePresetIdx = null;
    savePresetsToSettings();

    btn.textContent = '\u2715';
    btn.classList.add('preset-saving');
    refreshAllPresetVisuals();

    setTimeout(() => {
      btn.textContent = slotIdx + 1;
      btn.classList.remove('preset-saving');
    }, 1000);
    return;
  }

  presetData[slotIdx] = {
    category: currentCat,
    variantIdx: currentIdx,
    allMode: isAllMode(),
  };
  activePresetIdx = slotIdx;
  savePresetsToSettings();

  btn.textContent = '\u2713';
  btn.classList.add('preset-saving');
  refreshAllPresetVisuals();

  setTimeout(() => {
    btn.textContent = slotIdx + 1;
    btn.classList.remove('preset-saving');
  }, 1000);
}

function savePresetsToSettings() {
  api.updateSetting('radio_presets', presetData).catch(e => {
    console.error('Failed to save presets:', e);
  });
}

function showPresetTooltip(btn, slotIdx) {
  hidePresetTooltip();
  const data = presetData[slotIdx];

  tooltipEl = document.createElement('div');
  tooltipEl.className = 'preset-tooltip';
  tooltipEl.textContent = data
    ? (data.allMode ? data.category.toUpperCase() + '/SHUFFLE' : data.category.toUpperCase())
    : 'HOLD TO SAVE';

  const arrow = document.createElement('div');
  arrow.className = 'preset-tooltip-arrow';
  tooltipEl.appendChild(arrow);

  btn.parentElement.appendChild(tooltipEl);
}

function hidePresetTooltip() {
  if (tooltipEl) { tooltipEl.remove(); tooltipEl = null; }
}

// ── Event handlers ──

/** Save current genre selection to settings for persistence across restarts. */
function saveGenreSelection() {
  const selection = {
    category: getCurrentCategory(),
    variantIdx: getCurrentGenreIdx(),
    categoryVariants: getCategoryVariants(),
  };
  api.updateSetting('last_genre_selection', selection).catch(e => {
    console.error('Failed to save genre selection:', e);
  });
}

async function handleGenreSwitch(e) {
  // Clear active preset on manual genre change (not preset-triggered)
  if (!presetLoadInProgress) {
    activePresetIdx = null;
    refreshAllPresetVisuals();
  }

  const { genre, category, allMode } = e.detail;
  try {
    await api.switchGenre(genre.id, category || genre.category);
  } catch (err) {
    console.error('Failed to switch genre:', err);
  }

  saveGenreSelection();

  // Update OLED accent color for the new category
  const oledColor = getOledColor();
  if (oledColor) setOledAccent('#' + oledColor);

  // If in preview mode, cancel it
  if (previewMode) {
    previewMode = false;
    savedMainState = null;
    const replayBtn = $('lastTrackReplay');
    if (replayBtn) {
      replayBtn.textContent = '\u25C0\u25C0';
      replayBtn.classList.remove('active');
    }
    const timer = $('lastTrackTimer');
    if (timer) timer.classList.remove('active');
  }

  // Current track becomes last played
  if (currentTrack) {
    lastPlayedTrack = currentTrack;
    updateLastTrackUI();
  }

  audio.stop();
  isPlaying = false;
  setPlayIcons(false);

  currentTrack = null;
  updateRadioScreen(null);
  initWaveform('waveform');
  updateBufCount(0);

  showBufferingOverlay();
  pollForTracks();
}

function handleTogglePlay() {
  if (!$('radioView').classList.contains('active')) return;
  if (previewMode) return; // Don't toggle main play during preview
  isPlaying = audio.togglePlay();
  setPlayIcons(isPlaying);
  $('statusDot').classList.toggle('playing', isPlaying);
  $('powerLed').classList.toggle('off', !isPlaying);
  setWaveformPlaying('waveform', isPlaying);
}

async function handleSkipForward() {
  if (skipping) return;

  // If in preview mode, stop it first
  if (previewMode) stopPreview();

  // Autopilot: let it pick the next variant before normal skip
  if (isAutopilotOn()) {
    const switched = autopilotTrackEnd();
    if (switched) return;
  }

  const outgoing = currentTrack;
  skipping = true;
  try {
    const result = await api.radioSkip();
    if (result.ok && result.track) {
      // Skip succeeded — update LAST only now
      if (outgoing) {
        lastPlayedTrack = outgoing;
        updateLastTrackUI();
      }
      playTrack(result.track);
      refreshBufCount();
    } else {
      // Queue empty — stop playback, show buffering
      audio.stop();
      isPlaying = false;
      currentTrack = null;
      setPlayIcons(false);
      updateRadioScreen(null);
      showBufferingOverlay();
      pollForTracks();
    }
  } catch (e) {
    console.error('Skip failed:', e);
  } finally {
    skipping = false;
  }
}

async function handleSkipBack() {
  // Still wired but button is hidden in radio mode.
  // Kept for potential player-mode reuse or keyboard shortcuts.
}

async function handleFavorite() {
  if (!currentTrack) return;
  try {
    await api.updateTrackStatus(currentTrack.id, 'favorited');
    currentTrack.status = 'favorited';
  } catch (e) {
    console.error('Favorite failed:', e);
  }
}

async function handleDislike() {
  if (!currentTrack) return;
  try {
    await api.updateTrackStatus(currentTrack.id, 'disliked');
    currentTrack.status = 'disliked';
  } catch (e) {
    console.error('Dislike failed:', e);
  }
}

function handleAutoplayBlocked() {
  isPlaying = false;
  setPlayIcons(false);
  setWaveformPlaying('waveform', false);
  $('statusDot').classList.remove('playing');
  $('powerLed').classList.add('off');
}

function handleTimeUpdate(e) {
  if (!$('radioView').classList.contains('active')) return;
  const { currentTime, duration } = e.detail;

  if (previewMode) {
    // Update preview timer only
    const timer = $('lastTrackTimer');
    if (timer) timer.textContent = formatTime(currentTime);
    return;
  }

  updateRadioProgress(currentTime, duration);
  if (duration > 0) {
    updateWaveformCursor('waveform', currentTime / duration);
  }
}

async function handleTrackEnded() {
  if (!$('radioView').classList.contains('active')) return;

  // If preview track ended, resume main track
  if (previewMode) {
    stopPreview();
    return;
  }

  if (skipping) return;

  // Autopilot: let it pick the next variant before normal advance
  if (isAutopilotOn()) {
    const switched = autopilotTrackEnd();
    if (switched) return; // genre switch triggers its own flow via genre-switched event
  }

  const outgoing = currentTrack;
  skipping = true;
  try {
    const result = await api.radioSkip();
    if (result.ok && result.track) {
      if (outgoing) {
        lastPlayedTrack = outgoing;
        updateLastTrackUI();
      }
      playTrack(result.track);
      refreshBufCount();
    } else {
      isPlaying = false;
      currentTrack = null;
      setPlayIcons(false);
      updateRadioScreen(null);
      showBufferingOverlay();
      pollForTracks();
    }
  } catch (e) {
    console.error('Auto-advance failed:', e);
  } finally {
    skipping = false;
  }
}

function handleVolumeChange(e) {
  audio.setVolume(e.detail.volume);
}

async function handleAddToPlaylist() {
  if (!currentTrack) return;
  showPlaylistPicker();
}

// ── Playlist picker ──

async function showPlaylistPicker() {
  const picker = $('playlistPicker');
  const scroll = $('playlistPickerScroll');
  if (!picker || !scroll) return;

  scroll.innerHTML = '<div style="padding:20px;text-align:center;color:var(--fg-dim);font-size:11px">Loading...</div>';
  picker.classList.add('open');

  try {
    const playlists = await api.getPlaylists();
    scroll.innerHTML = '';

    if (playlists.length === 0) {
      scroll.innerHTML = '<div style="padding:20px;text-align:center;color:var(--fg-dim);font-size:11px">No playlists yet. Create one first.</div>';
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
      item.addEventListener('click', async () => {
        try {
          await api.addTrackToPlaylist(pl.id, currentTrack.id);
          const badge = document.createElement('span');
          badge.className = 'playlist-picker-badge';
          badge.textContent = 'ADDED';
          item.appendChild(badge);
          setTimeout(closePlaylistPicker, 600);
        } catch (e) {
          if (e.message && e.message.includes('409')) {
            const badge = document.createElement('span');
            badge.className = 'playlist-picker-badge';
            badge.textContent = 'ALREADY IN';
            item.appendChild(badge);
          } else {
            console.error('Failed to add to playlist:', e);
          }
        }
      });
      scroll.appendChild(item);
    });
  } catch (e) {
    scroll.innerHTML = '<div style="padding:20px;text-align:center;color:var(--fg-dim);font-size:11px">Failed to load playlists.</div>';
  }
}

function closePlaylistPicker() {
  const picker = $('playlistPicker');
  if (picker) picker.classList.remove('open');
}

// ── Track playback ──

function playTrack(track, autoplay = true) {
  currentTrack = track;
  hideOverlay();
  updateRadioScreen(track);
  emit('track-started', { track });
  updateScreenGenre(track.genre_id);
  if (track.waveform) {
    initWaveform('waveform', track.waveform);
  } else {
    initWaveform('waveform');
  }
  const url = api.audioUrl(track.filename);
  audio.loadTrack(url, autoplay);
  isPlaying = autoplay;
  setPlayIcons(autoplay);
  $('statusDot').classList.toggle('playing', autoplay);
  $('powerLed').classList.toggle('off', !autoplay);
  setWaveformPlaying('waveform', autoplay);

  // Reflect track's actual status in thumbs
  const isFav = track.status === 'favorited';
  const isDis = track.status === 'disliked';
  $('thumbsDownBtn').classList.toggle('active', isDis);
  $('thumbsDownBtn').querySelector('.emoji').classList.toggle('active', isDis);
  $('thumbsUpBtn').classList.toggle('active', isFav);
  $('thumbsUpBtn').querySelector('.emoji').classList.toggle('active', isFav);
}

// ── Polling ──

let pollTimer = null;

/** Fetch queue and update BUF count immediately. */
async function refreshBufCount() {
  try {
    const queue = await api.getRadioQueue();
    const upcoming = queue.upcoming || [];
    const currentId = currentTrack ? currentTrack.id : null;
    const bufCount = upcoming.filter(t => t.id !== currentId).length;
    updateBufCount(bufCount);
  } catch (e) {
    updateBufCount(0);
  }
}

async function pollForTracks() {
  if (pollTimer) clearTimeout(pollTimer);

  try {
    const np = await api.getNowPlaying();
    updateSignalDots(np.signal_status);
    applyLibraryState(np.library_mode);
    showNoSignal(np.signal_status === 'offline' && np.queue_size === 0 && !currentTrack);

    if (!currentTrack && !skipping && np.queue_size > 0
        && $('radioView').classList.contains('active')) {
      skipping = true;
      try {
        const result = await api.radioSkip();
        if (result.ok && result.track) {
          playTrack(result.track, true);
        }
      } finally {
        skipping = false;
      }
    }

    await refreshBufCount();
  } catch (e) {
    updateSignalDots('offline');
    showNoSignal(true);
  }

  pollTimer = setTimeout(pollForTracks, 5000);
}

function showNoSignal(offline) {
  const el = $('noSignalOverlay');
  if (el) el.classList.toggle('active', offline);
}

export function getCurrentTrack() {
  return currentTrack;
}

// ── Save / Restore state (for mode switching) ──

let savedRadioState = null;

/** Save current radio playback state before switching away. */
export function saveRadioState() {
  if (previewMode) stopPreview();
  if (!currentTrack) {
    savedRadioState = null;
    return;
  }
  savedRadioState = {
    track: currentTrack,
    currentTime: audio.getCurrentTime(),
    wasPlaying: isPlaying,
  };
}

/** Restore radio playback state when returning to radio. */
export function restoreRadioState() {
  if (!savedRadioState) {
    // No saved state (e.g. cold-start player restore) — immediately poll
    // so radio loads a track instead of waiting up to 5s.
    pollForTracks();
    return;
  }
  const { track, currentTime, wasPlaying } = savedRadioState;
  savedRadioState = null;

  currentTrack = track;
  hideOverlay();
  updateRadioScreen(track);
  updateScreenGenre(track.genre_id);
  if (track.waveform) {
    initWaveform('waveform', track.waveform);
  } else {
    initWaveform('waveform');
  }

  const url = api.audioUrl(track.filename);
  audio.loadTrackAt(url, currentTime, wasPlaying);
  isPlaying = wasPlaying;
  setPlayIcons(isPlaying);
  $('statusDot').classList.toggle('playing', isPlaying);
  $('powerLed').classList.toggle('off', !isPlaying);
  setWaveformPlaying('waveform', isPlaying);

  // Restore thumbs state for current track
  $('thumbsDownBtn').classList.toggle('active', track.status === 'disliked');
  $('thumbsDownBtn').querySelector('.emoji').classList.toggle('active', track.status === 'disliked');
  $('thumbsUpBtn').classList.toggle('active', track.status === 'favorited');
  $('thumbsUpBtn').querySelector('.emoji').classList.toggle('active', track.status === 'favorited');

  updateLastTrackUI();
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}
