/** Autopilot: context-aware genre steering based on time, weather, and temperature.
 *
 * When engaged, crosses category boundaries to pick the best-fitting variant
 * using a weighted random pool. Visual behavior mimics motorized radio hardware.
 */

import { $, on, emit } from './utils.js';
import { getSunTimes } from './weather.js';
import * as band from './band.js';
import * as api from './api.js';

// ── State ──

let active = false;
let firstPick = true;
let lastVariantId = null;
let nextVariant = null;   // pre-picked genre for look-ahead buffering
let weatherData = null;
let bufferStatus = {};    // cached: { genreId: readyCount }
let dynamicWeights = {};  // from installed packs: { variantId: { time: {...}, weather: {...} } }

export function isAutopilotOn() { return active; }

// ── Time windows ──

function getTimeWindow() {
  const now = new Date();
  const hour = now.getHours() + now.getMinutes() / 60;
  const { sunrise, sunset } = getSunTimes();

  let goldenStart = 16, nightStart = 21, earlyStart = 5;

  if (sunrise && sunset) {
    const riseH = toHourFrac(sunrise);
    const setH = toHourFrac(sunset);
    if (riseH !== null) earlyStart = Math.max(3, riseH - 1);
    if (setH !== null) {
      goldenStart = Math.max(14, setH - 2);
      nightStart = setH + 1;
    }
  }

  if (hour < earlyStart) return 'late-night';
  if (hour < 7)          return 'early-morning';
  if (hour < 10)         return 'morning';
  if (hour < 13)         return 'midday';
  if (hour < goldenStart) return 'afternoon';
  if (hour < goldenStart + 2) return 'golden-hour';
  if (hour < nightStart) return 'evening';
  if (hour < 24)         return 'night';
  return 'late-night';
}

function toHourFrac(isoStr) {
  if (!isoStr) return null;
  const d = new Date(isoStr);
  if (isNaN(d)) return null;
  return d.getHours() + d.getMinutes() / 60;
}

// ── Weight maps ──

const TIME_WEIGHTS = {
  'early-morning': {
    'rainy-day': 8, 'jazzy-nights': 4, 'lofi-girl': 6, 'study-time': 9, 'kyoto-beats': 7,
    'blade-runner': 3, 'outrun-drive': 1, 'outrun-chase': 0, 'outrun-sunset': 2, 'dark-synth': 1,
    'citypop-groove': 1, 'kamakura-breeze': 5, 'tokyo-nights': 6, 'osaka-fusion': 2, 'ginza-jazz': 5,
  },
  'morning': {
    'rainy-day': 3, 'jazzy-nights': 3, 'lofi-girl': 5, 'study-time': 4, 'kyoto-beats': 4,
    'blade-runner': 2, 'outrun-drive': 5, 'outrun-chase': 1, 'outrun-sunset': 5, 'dark-synth': 1,
    'citypop-groove': 6, 'kamakura-breeze': 8, 'tokyo-nights': 3, 'osaka-fusion': 9, 'ginza-jazz': 3,
  },
  'midday': {
    'rainy-day': 2, 'jazzy-nights': 2, 'lofi-girl': 4, 'study-time': 2, 'kyoto-beats': 3,
    'blade-runner': 3, 'outrun-drive': 7, 'outrun-chase': 4, 'outrun-sunset': 5, 'dark-synth': 2,
    'citypop-groove': 8, 'kamakura-breeze': 7, 'tokyo-nights': 2, 'osaka-fusion': 8, 'ginza-jazz': 1,
  },
  'afternoon': {
    'rainy-day': 4, 'jazzy-nights': 4, 'lofi-girl': 8, 'study-time': 5, 'kyoto-beats': 6,
    'blade-runner': 3, 'outrun-drive': 4, 'outrun-chase': 1, 'outrun-sunset': 7, 'dark-synth': 1,
    'citypop-groove': 5, 'kamakura-breeze': 8, 'tokyo-nights': 4, 'osaka-fusion': 5, 'ginza-jazz': 3,
  },
  'golden-hour': {
    'rainy-day': 4, 'jazzy-nights': 5, 'lofi-girl': 5, 'study-time': 3, 'kyoto-beats': 7,
    'blade-runner': 5, 'outrun-drive': 4, 'outrun-chase': 1, 'outrun-sunset': 10, 'dark-synth': 2,
    'citypop-groove': 4, 'kamakura-breeze': 8, 'tokyo-nights': 6, 'osaka-fusion': 3, 'ginza-jazz': 6,
  },
  'evening': {
    'rainy-day': 3, 'jazzy-nights': 6, 'lofi-girl': 4, 'study-time': 2, 'kyoto-beats': 4,
    'blade-runner': 7, 'outrun-drive': 5, 'outrun-chase': 3, 'outrun-sunset': 4, 'dark-synth': 5,
    'citypop-groove': 8, 'kamakura-breeze': 3, 'tokyo-nights': 8, 'osaka-fusion': 5, 'ginza-jazz': 8,
  },
  'night': {
    'rainy-day': 5, 'jazzy-nights': 8, 'lofi-girl': 4, 'study-time': 5, 'kyoto-beats': 4,
    'blade-runner': 8, 'outrun-drive': 3, 'outrun-chase': 2, 'outrun-sunset': 2, 'dark-synth': 7,
    'citypop-groove': 4, 'kamakura-breeze': 2, 'tokyo-nights': 8, 'osaka-fusion': 3, 'ginza-jazz': 7,
  },
  'late-night': {
    'rainy-day': 7, 'jazzy-nights': 6, 'lofi-girl': 5, 'study-time': 8, 'kyoto-beats': 5,
    'blade-runner': 6, 'outrun-drive': 2, 'outrun-chase': 1, 'outrun-sunset': 1, 'dark-synth': 6,
    'citypop-groove': 2, 'kamakura-breeze': 1, 'tokyo-nights': 8, 'osaka-fusion': 1, 'ginza-jazz': 6,
  },
};

const WEATHER_MOOD_WEIGHTS = {
  'clear':         { 'outrun-sunset': 4, 'kamakura-breeze': 4, 'osaka-fusion': 3, 'citypop-groove': 2 },
  'partly-cloudy': { 'lofi-girl': 2, 'kamakura-breeze': 2, 'outrun-sunset': 2 },
  'overcast':      { 'lofi-girl': 3, 'jazzy-nights': 3, 'tokyo-nights': 2, 'study-time': 2, 'ginza-jazz': 3 },
  'foggy':         { 'blade-runner': 4, 'kyoto-beats': 3, 'study-time': 3, 'rainy-day': 2, 'ginza-jazz': 2 },
  'rainy':         { 'rainy-day': 6, 'tokyo-nights': 4, 'jazzy-nights': 3, 'blade-runner': 3, 'lofi-girl': 2, 'ginza-jazz': 3 },
  'snowy':         { 'study-time': 4, 'kyoto-beats': 3, 'rainy-day': 3, 'tokyo-nights': 2 },
  'stormy':        { 'dark-synth': 5, 'outrun-chase': 4, 'blade-runner': 3, 'rainy-day': 2 },
};

const COLD_BOOST = { 'rainy-day': 2, 'study-time': 2, 'tokyo-nights': 2, 'jazzy-nights': 1, 'lofi-girl': 1, 'blade-runner': 1, 'ginza-jazz': 2 };
const WARM_BOOST = { 'kamakura-breeze': 2, 'citypop-groove': 2, 'osaka-fusion': 1, 'outrun-sunset': 2, 'outrun-drive': 1 };

// ── Weather helpers ──

function getWeatherMood(code) {
  if (code === 0) return 'clear';
  if (code <= 2)  return 'partly-cloudy';
  if (code === 3) return 'overcast';
  if (code <= 48) return 'foggy';
  if (code <= 67) return 'rainy';
  if (code <= 77) return 'snowy';
  if (code <= 82) return 'rainy';
  if (code <= 86) return 'snowy';
  if (code <= 99) return 'stormy';
  return 'clear';
}

function getTempModifier(variantId) {
  if (!weatherData || !weatherData.configured) return 0;
  const t = weatherData.temperature;
  const tempF = weatherData.unit === 'celsius' ? (t * 9 / 5 + 32) : t;
  if (tempF < 45) return COLD_BOOST[variantId] || 0;
  if (tempF > 80) return WARM_BOOST[variantId] || 0;
  return 0;
}

// ── Weighted pool ──

function getTimeWeight(variantId, timeWindow) {
  // Check hardcoded first, then dynamic weights from packs
  const hardcoded = TIME_WEIGHTS[timeWindow];
  if (hardcoded && variantId in hardcoded) return hardcoded[variantId];
  const dw = dynamicWeights[variantId];
  if (dw && dw.time && timeWindow in dw.time) return dw.time[timeWindow];
  return 1; // unknown genre default
}

function getWeatherWeight(variantId, mood) {
  const hardcoded = WEATHER_MOOD_WEIGHTS[mood];
  if (hardcoded && variantId in hardcoded) return hardcoded[variantId];
  const dw = dynamicWeights[variantId];
  if (dw && dw.weather && mood in dw.weather) return dw.weather[mood];
  return 0;
}

function pickVariant(allGenres) {
  const timeWindow = getTimeWindow();

  const mood = (weatherData && weatherData.configured && weatherData.weather_code !== undefined)
    ? getWeatherMood(weatherData.weather_code) : null;

  const scored = allGenres.map(genre => {
    let weight = getTimeWeight(genre.id, timeWindow);
    weight += mood ? getWeatherWeight(genre.id, mood) : 0;
    weight += getTempModifier(genre.id);
    if (genre.id === lastVariantId) weight = 0; // no-repeat
    return { genre, weight: Math.max(0, weight) };
  });

  return weightedRandomPick(scored);
}

function weightedRandomPick(scored) {
  const total = scored.reduce((sum, s) => sum + s.weight, 0);
  if (total === 0) {
    // All weights zero (only possible if single variant = lastVariantId) — pick randomly
    return scored[Math.floor(Math.random() * scored.length)]?.genre || null;
  }
  let r = Math.random() * total;
  for (const s of scored) {
    r -= s.weight;
    if (r <= 0) return s.genre;
  }
  return scored[scored.length - 1]?.genre || null;
}

function pickReadyVariant(allGenres) {
  const readyGenres = allGenres.filter(g => (bufferStatus[g.id] || 0) > 0);
  if (readyGenres.length === 0) return pickVariant(allGenres);
  return pickVariant(readyGenres);
}

// ── Look-ahead pre-buffer ──

function schedulePrePick() {
  if (!active) return;
  api.getBufferStatus().then(status => { bufferStatus = status || {}; }).catch(() => {});
  const genre = pickVariant(band.getAllGenres());
  if (genre) {
    nextVariant = genre;
    api.prebuffer(genre.id).catch(() => {});
  }
}

// ── Motorized switching ──

function executeAutopilotSwitch(genre) {
  const targetCategory = genre.category;
  const targetIdx = band.getVariantIndex(targetCategory, genre.id);
  if (targetIdx === -1) return;

  band.setMotorized(true);

  // After the switch completes: clear motorized mode.
  // Pre-pick is handled by the track-started event (fires when
  // the first track plays), giving the buffer worker lead time.
  document.addEventListener('genre-switched', () => {
    band.setMotorized(false);
  }, { once: true });

  if (firstPick) {
    firstPick = false;
    runScanSweep(() => band.restorePreset(targetCategory, targetIdx));
  } else {
    band.restorePreset(targetCategory, targetIdx);
  }

  lastVariantId = genre.id;
}

// ── Scanning sweep (first engagement only) ──

function runScanSweep(callback) {
  const needle = $('bandNeedle');
  if (!needle) { callback(); return; }

  needle.classList.add('scanning');

  // Force needle to left edge instantly
  needle.style.transition = 'none';
  needle.style.left = '2px';

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      // Restore scanning transition and sweep to right
      needle.style.transition = '';
      needle.style.left = 'calc(100% - 2px)';

      needle.addEventListener('transitionend', () => {
        setTimeout(() => {
          needle.classList.remove('scanning');
          callback();
        }, 200);
      }, { once: true });
    });
  });
}

// ── Engage / Disengage ──

export function engageAutopilot() {
  if (active) return;
  active = true;
  firstPick = true;
  lastVariantId = band.getCurrentGenre()?.id || null;

  // Light up AP lamp
  const lampDot = document.querySelector('#apLamp .led-dot');
  if (lampDot) lampDot.classList.remove('off');

  // Fetch weather + buffer status + dynamic weights then make first pick
  Promise.all([
    fetchWeather(),
    api.getBufferStatus().then(status => { bufferStatus = status || {}; }).catch(() => {}),
    fetchDynamicWeights(),
  ]).then(() => {
    if (!active) return; // disengaged while fetching
    const genre = pickReadyVariant(band.getAllGenres());
    if (genre) executeAutopilotSwitch(genre);
  });
}

export function disengageAutopilot() {
  if (!active) return;
  active = false;
  firstPick = true;
  lastVariantId = null;
  nextVariant = null;
  bufferStatus = {};
  api.clearPrebuffer().catch(() => {});

  // Dim AP lamp
  const lampDot = document.querySelector('#apLamp .led-dot');
  if (lampDot) lampDot.classList.add('off');

  band.setMotorized(false);

  // Update auto button visual + notify controls to refresh status bar
  const autoBtn = $('autoBtn');
  if (autoBtn) autoBtn.classList.remove('active');
  emit('autopilot:changed');
}

/** Called by radio.js when a track ends. Returns true if autopilot triggered a genre switch. */
export function onTrackEnd() {
  if (!active) return false;

  let genre = nextVariant;
  nextVariant = null;

  // Validate pre-pick against cached buffer status; fall back if empty
  if (genre && (bufferStatus[genre.id] || 0) === 0) {
    genre = pickReadyVariant(band.getAllGenres());
  }
  if (!genre) {
    genre = pickReadyVariant(band.getAllGenres());
  }
  if (!genre) return false;

  const current = band.getCurrentGenre();
  if (current && genre.id === current.id) {
    // Same variant continues — let radio.js do normal advance.
    // Pre-pick is handled by the track-started event when the next track plays.
    lastVariantId = genre.id;
    return false;
  }

  executeAutopilotSwitch(genre);
  return true;
}

// ── Weather ──

function fetchWeather() {
  return api.getWeather().then(data => { weatherData = data; }).catch(() => { weatherData = null; });
}

// ── Dynamic weights (installed packs) ──

function fetchDynamicWeights() {
  return api.getAutopilotWeights()
    .then(data => { dynamicWeights = data || {}; })
    .catch(() => { dynamicWeights = {}; });
}

// ── Init ──

export function initAutopilot() {
  // Inject AP lamp into band tuner
  const tuner = $('bandTuner');
  if (tuner) {
    const lamp = document.createElement('div');
    lamp.className = 'ap-lamp';
    lamp.id = 'apLamp';
    lamp.innerHTML = '<div class="led-dot off"></div><span class="led-label">AP</span>';
    tuner.appendChild(lamp);
  }

  // Load dynamic weights from installed packs
  fetchDynamicWeights();

  // When a track starts playing, pre-pick the next genre and send
  // the prebuffer hint.  This gives the buffer worker the full song
  // duration to generate at least one track for the upcoming switch.
  on('track-started', () => {
    if (active) schedulePrePick();
  });

  // Manual override: any user interaction with band controls disengages autopilot
  on('band:manual-interact', () => {
    if (active) disengageAutopilot();
  });

  // Keep weather cache fresh
  on('weather:updated', () => {
    fetchWeather();
  });
}
