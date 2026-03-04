/** Fetch wrapper for all backend API endpoints. */

const BASE = '/api';

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== null) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(BASE + path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${method} ${path}: ${res.status} ${text}`);
  }
  return res.json();
}

// -- Radio --

export function getNowPlaying() {
  return request('GET', '/radio/now-playing');
}

export function switchGenre(genreId, category = null) {
  const body = { genre_id: genreId };
  if (category) body.category = category;
  return request('POST', '/radio/switch-genre', body);
}

export function radioPlay() {
  return request('POST', '/radio/play');
}

export function radioPause() {
  return request('POST', '/radio/pause');
}

export function radioSkip() {
  return request('POST', '/radio/skip');
}

export function radioNavigate(trackId) {
  return request('POST', `/radio/navigate/${trackId}`);
}

export function getGenres() {
  return request('GET', '/radio/genres');
}

export function createGenre(data) {
  return request('POST', '/radio/genres', data);
}

export function updateGenre(genreId, data) {
  return request('PUT', `/radio/genres/${genreId}`, data);
}

export function getPresets() {
  return request('GET', '/radio/presets');
}

export function setPreset(slot, genreId) {
  return request('POST', `/radio/presets/${slot}`, { genre_id: genreId });
}

// -- Tracks --

export function getTracks(params = {}) {
  const q = new URLSearchParams(params).toString();
  return request('GET', '/tracks' + (q ? '?' + q : ''));
}

export function getTrack(trackId) {
  return request('GET', `/tracks/${trackId}`);
}

export function updateTrackStatus(trackId, status) {
  return request('PATCH', `/tracks/${trackId}/status`, { status });
}

export function getHistory(limit = 20) {
  return request('GET', `/tracks/history/recent?limit=${limit}`);
}

// -- Playlists --

export function getPlaylists() {
  return request('GET', '/playlists');
}

export function createPlaylist(name) {
  return request('POST', '/playlists', { name });
}

export function deletePlaylist(playlistId) {
  return request('DELETE', `/playlists/${playlistId}`);
}

export function getPlaylistTracks(playlistId) {
  return request('GET', `/playlists/${playlistId}/tracks`);
}

export function addTrackToPlaylist(playlistId, trackId) {
  return request('POST', `/playlists/${playlistId}/tracks`, { track_id: trackId });
}

export function removeTrackFromPlaylist(playlistId, trackId) {
  return request('DELETE', `/playlists/${playlistId}/tracks/${trackId}`);
}

// -- Autopilot Pre-buffer --

export function prebuffer(genreId) {
  return request('POST', '/radio/prebuffer', { genre_id: genreId });
}

export function clearPrebuffer() {
  return request('POST', '/radio/prebuffer', { genre_id: null });
}

// -- Radio Queue --

export function getRadioQueue() {
  return request('GET', '/radio/queue');
}

// -- Favorites --

export function getFavoritesTracks() {
  return request('GET', '/playlists/favorites/tracks');
}

// -- Albums --

export function getAlbums(genreId = null) {
  const q = genreId ? `?genre_id=${genreId}` : '';
  return request('GET', '/albums' + q);
}

export function getAlbumTracks(albumId) {
  return request('GET', `/albums/${albumId}/tracks`);
}

// -- Artists --

export function getArtistTracks(artistName) {
  return request('GET', `/artists/${encodeURIComponent(artistName)}/tracks`);
}

export function getArtistProfile(artistName) {
  return request('GET', `/artists/${encodeURIComponent(artistName)}/profile`);
}

// -- Categories --

export function getCategories() {
  return request('GET', '/categories');
}

export function createCategory(data) {
  return request('POST', '/categories', data);
}

export function updateCategory(categoryId, data) {
  return request('PUT', `/categories/${categoryId}`, data);
}

export function deleteCategory(categoryId) {
  return request('DELETE', `/categories/${categoryId}`);
}

// -- Settings --

export function getSettings() {
  return request('GET', '/settings');
}

export function getSetting(key) {
  return request('GET', `/settings/${key}`);
}

export function updateSetting(key, value) {
  return request('PUT', `/settings/${key}`, { value: JSON.stringify(value) });
}

// -- Weather --

export function getWeather() {
  return request('GET', '/weather');
}

export function getWeatherLocation() {
  return request('GET', '/weather/location');
}

export function saveWeatherLocation(latitude, longitude, displayName) {
  return request('POST', '/weather/location', {
    latitude,
    longitude,
    display_name: displayName,
  });
}

export function geocodeSearch(query) {
  return request('GET', `/weather/geocode?q=${encodeURIComponent(query)}`);
}

// -- Audio --

export function audioUrl(filename) {
  return `${BASE}/audio/${encodeURIComponent(filename)}`;
}
