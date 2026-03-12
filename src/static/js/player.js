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

// Artist profile data (populated when viewing an artist page)
let artistProfile = null;

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
  artistProfile = null;

  try {
    const plType = getPlaylistType(playlistId);
    if (plType === 'favorites') {
      playlistTracks = await api.getFavoritesTracks();
    } else if (plType === 'artist') {
      const artistName = playlistId.slice(7);
      const [tracks, profile] = await Promise.all([
        api.getArtistTracks(artistName),
        api.getArtistProfile(artistName).catch(() => null),
      ]);
      playlistTracks = tracks;
      artistProfile = profile;
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
  updatePlayerThumbs();

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

  const plType = getPlaylistType(activePlaylistId);
  const isArtistPage = artistProfile && plType === 'artist';
  const isAlbumPage = plType === 'album';
  const hideArtistCol = isArtistPage;
  const hideAlbumCol = isAlbumPage;

  // Render artist profile header if available
  if (isArtistPage) {
    renderArtistProfileHeader(tl);
  }

  // Update section label: hide on artist pages, show summary otherwise
  const sectionLabel = tl.closest('.tracklist-section')?.querySelector('.section-label');
  if (sectionLabel) {
    if (isArtistPage) {
      sectionLabel.style.display = 'none';
    } else {
      sectionLabel.style.display = '';
      const totalSecs = playlistTracks.reduce((sum, t) => sum + (t.duration || 0), 0);
      const mins = Math.floor(totalSecs / 60);
      const labelSpan = sectionLabel.querySelector('span:first-child');
      const metaSpan = $('tracklistMeta');
      if (labelSpan) labelSpan.textContent = playlistTracks.length + ' TRACKS';
      if (metaSpan) metaSpan.textContent = mins > 0 ? mins + ' MIN' : '';
    }
  }

  const readOnly = isReadOnlyPlaylist(activePlaylistId);

  const showHearts = readOnly; // artist/album pages

  playlistTracks.forEach((t, i) => {
    const isCur = i === playerTrackIdx;
    const isFav = t.status === 'favorited';
    const isEphemeral = showHearts && !isFav;
    const row = document.createElement('div');
    row.className = 'tracklist-item' + (isCur ? ' playing-track' : '') + (isEphemeral ? ' tracklist-ephemeral' : '');

    // Track number column: bars when playing, number otherwise
    let numHtml;
    if (isCur && isPlaying) {
      numHtml = '<div class="tracklist-bars"><div style="height:7px;animation-duration:1s"></div><div style="height:11px;animation-duration:1.3s"></div><div style="height:5px;animation-duration:0.8s"></div></div>';
    } else {
      numHtml = '' + (i + 1);
    }

    // Heart icon for artist/album pages (placed in actions area so it's always visible)
    let heartHtml = '';
    if (showHearts) {
      heartHtml = isFav
        ? '<span class="tracklist-heart saved" title="' + (t.in_playlist ? 'In playlist' : 'Click to unsave') + '" data-idx="' + i + '">\u2665</span>'
        : '<span class="tracklist-heart" title="Click to save" data-idx="' + i + '">\u2661</span>';
    }

    // Adjust grid columns based on which columns are visible
    if (hideArtistCol) {
      row.style.gridTemplateColumns = '18px 5fr 70px 36px auto';
    } else if (hideAlbumCol) {
      row.style.gridTemplateColumns = '18px 3fr 2fr 36px auto';
    }

    row.innerHTML =
      '<div class="tracklist-num ' + (isCur ? 'active-num' : '') + '">' + numHtml + '</div>' +
      '<div class="tracklist-title-col">' +
        '<div class="tracklist-title ' + (isCur ? 'active-title' : '') + '">' + escapeHtml(t.title) + '</div>' +
      '</div>' +
      (hideArtistCol ? '' : '<span class="tracklist-artist">' + escapeHtml(stripFeat(t.artist)) + '</span>') +
      (hideAlbumCol ? '' : '<span class="tracklist-album">' + (t.album_name ? escapeHtml(t.album_name) : '') + '</span>') +
      '<span class="tracklist-dur">' + formatTime(t.duration) + '</span>' +
      '<div class="tracklist-actions">' +
        heartHtml +
        '<button class="tracklist-add-pl" title="Add to playlist" data-idx="' + i + '">+</button>' +
        (readOnly ? '' : '<button class="tracklist-remove" title="Remove" data-idx="' + i + '">&times;</button>') +
      '</div>';

    row.addEventListener('click', (e) => {
      if (e.target.closest('.tracklist-actions') || e.target.closest('.tracklist-heart')
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

    // Quick-favorite/unfavorite via heart click
    const heart = row.querySelector('.tracklist-heart');
    if (heart) {
      heart.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (t.in_playlist) return;
        const newStatus = t.status === 'favorited' ? 'active' : 'favorited';
        try {
          await api.updateTrackStatus(t.id, newStatus);
          t.status = newStatus;
          renderTracklist();
          updatePlayerThumbs();
        } catch (err) {
          console.error('Heart toggle failed:', err);
        }
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

/** Render the artist profile header above the tracklist. */
function renderArtistProfileHeader(container) {
  const p = artistProfile;
  if (!p) return;

  const header = document.createElement('div');
  header.className = 'artist-profile-header';

  // Artist name + stats
  const variant = p.genre_id ? p.genre_id.replace(/-/g, ' ') : '';
  const statsText = [
    p.track_count + ' track' + (p.track_count !== 1 ? 's' : ''),
    p.like_count > 0 ? p.like_count + ' like' + (p.like_count !== 1 ? 's' : '') : '',
    variant,
  ].filter(Boolean).join(' \u00B7 ');

  let html =
    '<div class="artist-profile-name">' + escapeHtml(p.name) + '</div>' +
    '<div class="artist-profile-stats">' + escapeHtml(statsText) + '</div>';

  // Bio
  if (p.bio) {
    html += '<div class="artist-profile-bio">' + escapeHtml(p.bio) + '</div>';
  }

  // Albums grid
  if (p.albums && p.albums.length > 0) {
    html += '<div class="artist-profile-albums-label">ALBUMS</div>';
    html += '<div class="artist-profile-albums">';
    for (const album of p.albums) {
      const cover = album.cover_url || '';
      html +=
        '<div class="artist-album-card" data-album-id="' + album.id + '" data-album-name="' + escapeAttr(album.name) + '">' +
          (cover
            ? '<img class="artist-album-cover" src="' + escapeAttr(cover) + '" alt="">'
            : '<div class="artist-album-cover artist-album-cover-empty"></div>') +
          '<div class="artist-album-name">' + escapeHtml(album.name) + '</div>' +
          '<div class="artist-album-meta">' + album.track_count + ' tracks</div>' +
        '</div>';
    }
    html += '</div>';
  }

  // Playlists grid
  if (p.playlists && p.playlists.length > 0) {
    html += '<div class="artist-profile-albums-label">PLAYLISTS</div>';
    html += '<div class="artist-profile-albums">';
    for (const pl of p.playlists) {
      html +=
        '<div class="artist-playlist-card" data-playlist-id="' + pl.id + '" data-playlist-name="' + escapeAttr(pl.name) + '">' +
          '<div class="artist-album-cover artist-playlist-icon">\u266B</div>' +
          '<div class="artist-album-name">' + escapeHtml(pl.name) + '</div>' +
        '</div>';
    }
    html += '</div>';
  }

  // Tracks divider
  html += '<div class="artist-profile-tracks-label">TRACKS</div>';

  header.innerHTML = html;

  // Bind album clicks
  header.querySelectorAll('.artist-album-card').forEach(card => {
    card.addEventListener('click', () => {
      const albumId = card.dataset.albumId;
      const albumName = card.dataset.albumName;
      enterPlayerMode('album:' + albumId, albumName, 0, true);
    });
  });

  // Bind playlist clicks
  header.querySelectorAll('.artist-playlist-card').forEach(card => {
    card.addEventListener('click', () => {
      const plId = parseInt(card.dataset.playlistId, 10);
      const plName = card.dataset.playlistName;
      enterPlayerMode(plId, plName, 0, true);
    });
  });

  container.appendChild(header);
}

function escapeAttr(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;');
}

/** Update player thumbs buttons to reflect current track status. */
function updatePlayerThumbs() {
  const up = $('plThumbsUpBtn');
  const down = $('plThumbsDownBtn');
  if (!up || !down) return;

  const track = playlistTracks[playerTrackIdx];
  const isFav = track && track.status === 'favorited';
  const isDis = track && track.status === 'disliked';
  const locked = track && track.in_playlist;

  up.classList.toggle('active', isFav);
  up.querySelector('.emoji').classList.toggle('active', isFav);
  down.classList.toggle('active', isDis);
  down.querySelector('.emoji').classList.toggle('active', isDis);

  up.disabled = !!locked;
  down.disabled = !!locked;
  up.title = locked ? 'Remove from playlist to change' : 'Like';
  down.title = locked ? 'Remove from playlist to change' : 'Dislike';
  up.classList.toggle('hw-key-locked', !!locked);
  down.classList.toggle('hw-key-locked', !!locked);
}

function playCurrentTrack() {
  const track = playlistTracks[playerTrackIdx];
  if (!track) return;
  updatePlayerScreen(track, activePlaylistName, playerTrackIdx, playlistTracks.length);
  renderTracklist();
  updatePlayerThumbs();
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

  // Player thumbs (favorite / dislike)
  $('plThumbsUpBtn')?.addEventListener('click', async function () {
    const track = playlistTracks[playerTrackIdx];
    if (!track || track.in_playlist) return;
    const on = track.status !== 'favorited';
    const newStatus = on ? 'favorited' : 'active';
    try {
      await api.updateTrackStatus(track.id, newStatus);
      track.status = newStatus;
      updatePlayerThumbs();
      renderTracklist();
    } catch (e) {
      console.error('Player favorite failed:', e);
    }
  });

  $('plThumbsDownBtn')?.addEventListener('click', async function () {
    const track = playlistTracks[playerTrackIdx];
    if (!track || track.in_playlist) return;
    const on = track.status !== 'disliked';
    const newStatus = on ? 'disliked' : 'active';
    try {
      await api.updateTrackStatus(track.id, newStatus);
      track.status = newStatus;
      updatePlayerThumbs();
      renderTracklist();
    } catch (e) {
      console.error('Player dislike failed:', e);
    }
  });

  // OLED artist/album/art click → virtual playlist
  $('playerTrackArtist')?.addEventListener('click', () => {
    const track = playlistTracks[playerTrackIdx];
    if (!track) return;
    const base = stripFeat(track.artist);
    if (base) enterPlayerMode('artist:' + base, base, 0, true);
  });

  const albumNav = () => {
    const track = playlistTracks[playerTrackIdx];
    if (!track) return;
    if (track.album_name && track.album_id) {
      enterPlayerMode('album:' + track.album_id, track.album_name, 0, true);
    }
  };
  $('playerTrackAlbum')?.addEventListener('click', albumNav);
  $('playerAlbumArt')?.addEventListener('click', albumNav);

  on('toggle-play', () => {
    if (!$('playerView').classList.contains('active')) return;
    isPlaying = audio.togglePlay();
    setPlayIcons(isPlaying);
    $('statusDot').classList.toggle('playing', isPlaying);
    $('powerLed').classList.toggle('off', !isPlaying);
    setWaveformPlaying('playerWaveform', isPlaying);
  });

  on('audio-play-failed', () => {
    if (!$('playerView').classList.contains('active')) return;
    isPlaying = false;
    setPlayIcons(false);
    $('statusDot').classList.remove('playing');
    $('powerLed').classList.add('off');
    setWaveformPlaying('playerWaveform', false);
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

