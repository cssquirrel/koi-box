/** Weather chip logic: fetch + display current weather in top bar. */

import * as api from './api.js';
import { $, emit } from './utils.js';

const POLL_MS = 10 * 60 * 1000; // 10 minutes
let pollTimer = null;
let _sunrise = null;
let _sunset = null;

/** Map WMO weather code to a Unicode icon. */
function weatherIcon(code) {
  if (code === 0) return '\u2600';        // ☀ clear sky
  if (code <= 2) return '\u26C5';         // ⛅ partly cloudy
  if (code === 3) return '\u2601';        // ☁ overcast
  if (code <= 48) return '\u2601';        // ☁ fog
  if (code <= 57) return '\uD83C\uDF27';  // 🌧 drizzle
  if (code <= 67) return '\uD83C\uDF27';  // 🌧 rain
  if (code <= 77) return '\u2744';        // ❄ snow
  if (code <= 82) return '\uD83C\uDF27';  // 🌧 rain showers
  if (code <= 86) return '\u2744';        // ❄ snow showers
  if (code <= 99) return '\u26A1';        // ⚡ thunderstorm
  return '\u2601';                        // ☁ fallback
}

/** Fetch weather from backend and update the chip. */
async function updateWeatherChip() {
  try {
    const data = await api.getWeather();
    const chip = $('weatherChip');
    if (!chip) return;

    if (!data.configured) {
      chip.style.display = 'none';
      return;
    }
    if (data.error) return; // keep previous display on transient error

    const icon = weatherIcon(data.weather_code);
    const deg = data.unit === 'celsius' ? 'C' : 'F';
    const temp = Math.round(data.temperature);

    chip.querySelector('.weather-icon').textContent = icon;
    $('weatherTemp').textContent = `${temp}\u00B0${deg}`;
    chip.style.display = 'flex';

    _sunrise = data.sunrise || null;
    _sunset = data.sunset || null;
    emit('weather:updated');
  } catch (e) {
    // Weather is non-critical — fail silently
  }
}

/** Start weather polling if location is configured. */
export async function initWeather() {
  await updateWeatherChip();
  pollTimer = setInterval(updateWeatherChip, POLL_MS);
}

/** Force an immediate refresh (called after location/unit change in settings). */
export function refreshWeather() {
  updateWeatherChip();
}

/** Return stored sunrise/sunset ISO strings (or null if unavailable). */
export function getSunTimes() {
  return { sunrise: _sunrise, sunset: _sunset };
}
