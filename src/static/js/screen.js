/** OLED screen updates: title, artist, progress, waveform, signal LEDs. */

import { $, formatTime, stripFeat } from './utils.js';

/** Update the radio OLED screen with track info. */
export function updateRadioScreen(track) {
  if (!track) {
    $('trackTitle').textContent = '---';
    $('trackArtist').textContent = '---';
    $('screenAlbumImg').removeAttribute('src');
    $('progressFill').style.width = '0%';
    $('progressTime').textContent = '0:00 / 0:00';
    return;
  }
  $('trackTitle').textContent = track.title;
  $('trackArtist').textContent = stripFeat(track.artist);
  if (track.album_cover_url) {
    $('screenAlbumImg').src = track.album_cover_url;
  } else {
    $('screenAlbumImg').removeAttribute('src');
  }
}

/** Update the genre label on screen. */
export function updateScreenGenre(genreId) {
  $('screenGenre').textContent = genreId
    ? genreId.replace(/-/g, ' ').toUpperCase()
    : '---';
}

/** Update progress bar and time display for radio view. */
export function updateRadioProgress(currentTime, duration) {
  const pct = duration > 0 ? (currentTime / duration) * 100 : 0;
  $('progressFill').style.width = pct + '%';
  $('progressTime').textContent = formatTime(currentTime) + ' / ' + formatTime(duration);
}

/** Update progress bar and time display for player view. */
export function updatePlayerProgress(currentTime, duration) {
  const pct = duration > 0 ? (currentTime / duration) * 100 : 0;
  $('playerProgressFill').style.width = pct + '%';
  $('playerProgressTime').textContent = formatTime(currentTime) + ' / ' + formatTime(duration);
}

/** Update the player OLED screen with track info. */
export function updatePlayerScreen(track, playlistName, trackIdx, trackCount) {
  $('playerGenreLabel').textContent = playlistName ? playlistName.toUpperCase() : 'PLAYLIST';
  $('playerCounter').textContent = trackCount > 0 ? (trackIdx + 1) + ' / ' + trackCount : 'EMPTY';
  const progressBar = $('playerProgressBar');
  const progressTime = $('playerProgressTime');
  const albumImg = $('playerAlbumImg');
  if (!track) {
    $('playerTrackTitle').textContent = 'No tracks yet';
    $('playerTrackArtist').textContent = '---';
    $('playerTrackAlbum').textContent = '';
    albumImg.removeAttribute('src');
    albumImg.style.display = 'none';
    if (progressBar) progressBar.style.display = 'none';
    if (progressTime) progressTime.style.display = 'none';
    return;
  }
  albumImg.style.display = '';
  if (progressBar) progressBar.style.display = '';
  if (progressTime) progressTime.style.display = '';
  $('playerTrackTitle').textContent = track.title;
  $('playerTrackArtist').textContent = stripFeat(track.artist);
  $('playerTrackAlbum').textContent = track.album_name || '';
  if (track.album_cover_url) {
    albumImg.src = track.album_cover_url;
  } else {
    albumImg.removeAttribute('src');
  }
}

/** Update signal strength LEDs. */
export function updateSignalDots(status) {
  const dots = $('signalDots');
  if (!dots) return;
  const children = dots.querySelectorAll('.signal-dot');
  const count = (status === 'healthy' || status === 'strong') ? 5
    : status === 'degraded' ? 3
    : status === 'offline' ? 0
    : 2;
  children.forEach((dot, i) => {
    dot.classList.toggle('active', i < count);
  });
}

/** Initialize waveform bars in a container. */
export function initWaveform(containerId, waveformData = null) {
  const wf = $(containerId);
  if (!wf) return;
  wf.innerHTML = '';

  if (waveformData && waveformData.length > 0) {
    // Render from pre-computed data — fill the container width
    const maxBars = 40;
    const step = Math.max(1, Math.floor(waveformData.length / maxBars));
    for (let i = 0; i < waveformData.length; i += step) {
      const bar = document.createElement('div');
      bar.className = 'wave-bar';
      bar.style.height = Math.max(10, waveformData[i] * 100) + '%';
      bar.style.animationDelay = (Math.random() * 2).toFixed(2) + 's';
      bar.style.animationDuration = (0.8 + Math.random() * 1.2).toFixed(2) + 's';
      wf.appendChild(bar);
    }
  } else {
    // Render animated placeholder bars
    for (let i = 0; i < 40; i++) {
      const bar = document.createElement('div');
      bar.className = 'wave-bar playing';
      bar.style.height = (15 + Math.random() * 85) + '%';
      bar.style.animationDelay = (Math.random() * 2).toFixed(2) + 's';
      bar.style.animationDuration = (0.8 + Math.random() * 1.2).toFixed(2) + 's';
      wf.appendChild(bar);
    }
  }
}

/** Update waveform playback cursor position with bounce on played bars. */
export function updateWaveformCursor(containerId, progress) {
  const wf = $(containerId);
  if (!wf) return;
  const bars = wf.querySelectorAll('.wave-bar');
  const cursorIdx = Math.floor(progress * bars.length);
  const active = wf.classList.contains('is-playing');
  bars.forEach((bar, i) => {
    const played = i <= cursorIdx;
    bar.style.opacity = played ? '1' : '0.35';
    bar.classList.toggle('playing', played && active);
  });
}

/** Toggle waveform animation on/off. */
export function setWaveformPlaying(containerId, isPlaying) {
  const wf = $(containerId);
  if (!wf) return;
  wf.classList.toggle('is-playing', isPlaying);
  wf.querySelectorAll('.wave-bar').forEach(bar => {
    if (isPlaying) {
      if (bar.style.opacity === '1') bar.classList.add('playing');
    } else {
      bar.classList.remove('playing');
    }
  });
}

/** Set the OLED screen accent color dynamically (applies to all screens). */
export function setOledAccent(color) {
  document.querySelectorAll('.screen').forEach(el => {
    el.style.setProperty('--oled-accent', color);
  });
}
