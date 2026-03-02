/** HTML5 Audio controller with event emission. */

import { $, emit, on } from './utils.js';

let audioEl = null;

/** Initialize the audio controller. */
export function initAudio() {
  audioEl = $('audioPlayer');
  if (!audioEl) return;

  audioEl.addEventListener('timeupdate', () => {
    emit('audio-timeupdate', {
      currentTime: audioEl.currentTime,
      duration: audioEl.duration || 0,
    });
  });

  audioEl.addEventListener('ended', () => {
    emit('audio-ended');
  });

  audioEl.addEventListener('error', (e) => {
    console.error('Audio error:', e);
    emit('audio-error', { error: e });
  });

  audioEl.addEventListener('loadedmetadata', () => {
    emit('audio-loaded', {
      duration: audioEl.duration,
    });
  });

  audioEl.addEventListener('canplay', () => {
    emit('audio-canplay');
  });
}

/** Load and optionally play an audio source URL. */
export function loadTrack(url, autoplay = true) {
  if (!audioEl) return;
  audioEl.src = url;
  audioEl.load();
  if (autoplay) {
    audioEl.play().catch(() => emit('audio-autoplay-blocked'));
  }
}

/** Play the current track. */
export function play() {
  if (!audioEl) return;
  audioEl.play().catch(() => {});
}

/** Pause the current track. */
export function pause() {
  if (!audioEl) return;
  audioEl.pause();
}

/** Stop playback and clear the source. */
export function stop() {
  if (!audioEl) return;
  audioEl.pause();
  audioEl.removeAttribute('src');
  audioEl.load();
}

/** Toggle play/pause, returns new playing state. */
export function togglePlay() {
  if (!audioEl) return false;
  if (audioEl.paused) {
    audioEl.play().catch(() => {});
    return true;
  } else {
    audioEl.pause();
    return false;
  }
}

/** Seek to a position (0.0 to 1.0). */
export function seekTo(fraction) {
  if (!audioEl || !audioEl.duration) return;
  audioEl.currentTime = fraction * audioEl.duration;
}

/** Set volume (0.0 to 1.0). */
export function setVolume(vol) {
  if (!audioEl) return;
  audioEl.volume = Math.max(0, Math.min(1, vol));
}

/** Get current playback state. */
export function isPlaying() {
  return audioEl && !audioEl.paused;
}

/** Get current time in seconds. */
export function getCurrentTime() {
  return audioEl ? audioEl.currentTime : 0;
}

/** Get duration in seconds. */
export function getDuration() {
  return audioEl ? (audioEl.duration || 0) : 0;
}

/** Load a track and seek to a specific position once ready. */
export function loadTrackAt(url, position, autoplay = true) {
  if (!audioEl) return;
  audioEl.src = url;
  audioEl.load();
  const onLoaded = () => {
    audioEl.currentTime = position;
    if (autoplay) audioEl.play().catch(() => {});
    audioEl.removeEventListener('loadedmetadata', onLoaded);
  };
  audioEl.addEventListener('loadedmetadata', onLoaded);
}
