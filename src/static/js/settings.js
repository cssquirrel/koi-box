/** Settings view logic and form bindings. */

import * as api from './api.js';
import { $ } from './utils.js';
import { refreshWeather } from './weather.js';
import { getThemeMode, setThemeMode } from './theme.js';

/** Initialize the settings view by loading and rendering all settings. */
export async function initSettings() {
  const container = $('settingsScroll');
  if (!container) return;

  try {
    const [settings, genres, categories, installedPacks] = await Promise.all([
      api.getSettings(),
      api.getGenres(),
      api.getCategories(),
      api.getInstalledPacks().catch(() => ({})),
    ]);
    renderSettings(container, settings, genres, categories, installedPacks);
  } catch (e) {
    container.innerHTML = '<div style="padding:20px;color:var(--fg-dim);font-size:12px">Failed to load settings.</div>';
  }
}

function renderSettings(container, settings, genres, categories, installedPacks) {
  const map = {};
  settings.forEach(s => { map[s.key] = JSON.parse(s.value); });

  const tempUnit = map.weather_temp_unit || 'fahrenheit';
  const themeMode = getThemeMode();

  // Build category lookup
  const catMap = {};
  categories.forEach(c => { catMap[c.id] = c; });
  const catIds = categories.map(c => c.id);

  let html = `
    <!-- Location -->
    <div class="settings-section">
      <div class="settings-section-head">Location</div>
      <div class="settings-row">
        <span class="settings-label">Theme</span>
        <div class="format-picker">
          <button class="format-btn theme-mode-btn ${themeMode === 'light' ? 'active' : ''}" data-theme-mode="light">LIGHT</button>
          <button class="format-btn theme-mode-btn ${themeMode === 'dark' ? 'active' : ''}" data-theme-mode="dark">DARK</button>
          <button class="format-btn theme-mode-btn ${themeMode === 'auto' ? 'active' : ''}" data-theme-mode="auto">AUTO</button>
        </div>
      </div>
      <div class="settings-row">
        <span class="settings-label">Temperature unit</span>
        <div class="format-picker">
          <button class="format-btn temp-unit-btn ${tempUnit === 'fahrenheit' ? 'active' : ''}" data-unit="fahrenheit">&deg;F</button>
          <button class="format-btn temp-unit-btn ${tempUnit === 'celsius' ? 'active' : ''}" data-unit="celsius">&deg;C</button>
        </div>
      </div>
      <div style="margin-top:8px">
        <label class="genre-field-label">CITY</label>
        <div style="position:relative">
          <input class="settings-input settings-input-full" id="settLocationSearch" placeholder="Search city..." autocomplete="off">
          <div class="location-dropdown" id="locationDropdown"></div>
        </div>
      </div>
      <div class="location-current" id="locationCurrent" style="margin-top:8px;font-size:11px;color:var(--fg-dim);font-family:var(--font-mono)"></div>
    </div>
    <!-- Connection -->
    <div class="settings-section">
      <div class="settings-section-head">Connection</div>
      <div style="margin-bottom:10px">
        <label class="genre-field-label">API HTTP</label>
        <input class="settings-input settings-input-full" id="settApiUrl" value="${escapeAttr(map.api_url || '')}" placeholder="http://127.0.0.1:8001">
      </div>
      <div>
        <label class="genre-field-label">API KEY <span style="color:var(--fg-ghost)">(optional)</span></label>
        <input class="settings-input settings-input-full" id="settApiKey" type="password" value="${escapeAttr(map.api_key || '')}">
      </div>
    </div>
    <!-- Track Management -->
    <div class="settings-section">
      <div class="settings-section-head">Track Management</div>
      <div class="settings-row">
        <span class="settings-label">Delete disliked tracks</span>
        ${renderToggle('settDeleteDisliked', map.delete_disliked_tracks)}
      </div>
      <div class="settings-row">
        <span class="settings-label">Preservation time (hours)</span>
        <input class="settings-input settings-input-sm" id="settPreservation" type="number" value="${map.preservation_time ?? 24}">
      </div>
      <div class="settings-row">
        <span class="settings-label">File size limit (MB)</span>
        <input class="settings-input settings-input-sm" id="settFileSize" type="number" value="${map.file_size_limit_mb ?? 500}">
      </div>
      <div class="settings-row">
        <span class="settings-label">Buffer max (tracks)</span>
        <input class="settings-input settings-input-sm" id="settBufferMax" type="number" min="1" value="${map.buffer_max ?? 5}">
      </div>
      <div class="settings-note">Unfavorited tracks are deleted when the first applicable condition is met. Set -1 to disable a condition.</div>
    </div>
    <!-- Artists -->
    <div class="settings-section">
      <div class="settings-section-head">Artists</div>
      <div class="settings-row">
        <span class="settings-label">Generate artist bios</span>
        ${renderToggle('settArtistBios', map.artist_bios_enabled)}
      </div>
      <div class="settings-note">When enabled, opening an artist page will generate a short bio using the local LLM. Requires the Qwen model to be downloaded.</div>
    </div>
    <!-- Generation LM -->
    <div class="settings-section">
      <div class="settings-section-head">Generation - LM</div>
      <div class="settings-row"><span class="settings-label">Thinking</span>${renderToggle('settThinking', map.lm_thinking)}</div>
      <div class="settings-row"><span class="settings-label">Use COT caption</span>${renderToggle('settCotCaption', map.lm_use_cot_caption)}</div>
      <div class="settings-row"><span class="settings-label">Use COT language</span>${renderToggle('settCotLanguage', map.lm_use_cot_language)}</div>
      <div class="settings-row"><span class="settings-label">Constrained decoding</span>${renderToggle('settConstrained', map.lm_constrained_decoding)}</div>
      <div class="settings-row"><span class="settings-label">LM CFG scale</span><input class="settings-input settings-input-sm" id="settCfgScale" type="number" value="${map.lm_lm_cfg_scale ?? 2.0}" step="0.1"></div>
    </div>
    <!-- Generation Output -->
    <div class="settings-section">
      <div class="settings-section-head">Generation - Output</div>
      <div class="settings-row"><span class="settings-label">Use format</span>${renderToggle('settUseFormat', map.output_use_format)}</div>
      <div class="settings-row"><span class="settings-label">Inference steps</span><input class="settings-input settings-input-sm" id="settInfSteps" type="number" value="${map.output_inference_steps ?? 8}"></div>
      <div class="settings-row">
        <span class="settings-label">Audio format</span>
        <div class="format-picker">
          <button class="format-btn ${map.output_audio_format === 'mp3' ? 'active' : ''}" data-format="mp3">MP3</button>
          <button class="format-btn ${map.output_audio_format === 'wav' ? 'active' : ''}" data-format="wav">WAV</button>
        </div>
      </div>
    </div>
    <!-- Genre Packs -->
    <div class="settings-section">
      <div class="settings-section-head">Genre Packs</div>
      <div id="packCards"></div>
      <div style="display:flex;gap:6px;margin-top:10px">
        <button class="bar-btn" id="browsePacksBtn" style="flex:1;height:30px;font-size:9px;letter-spacing:1px">BROWSE PACKS</button>
        <button class="bar-btn" id="installUrlBtn" style="flex:1;height:30px;font-size:9px;letter-spacing:1px">INSTALL FROM URL</button>
      </div>
    </div>
    <!-- Categories -->
    <div class="settings-section">
      <div class="settings-section-head">Categories</div>
      <div id="categoryCards">`;

  categories.forEach(c => {
    html += renderCategoryCard(c);
  });

  html += `</div>
      <button class="bar-btn" id="addCategoryBtn" style="margin-top:10px;width:100%;height:30px;font-size:9px;letter-spacing:1px">+ NEW CATEGORY</button>
    </div>
    <!-- Genres -->
    <div class="settings-section">
      <div class="settings-section-head">Genre Stations</div>
      <div id="genreCards">`;

  // Group genres by category
  catIds.forEach(catId => {
    const catGenres = genres.filter(g => g.category === catId);
    if (catGenres.length === 0) return;
    const displayName = catMap[catId]?.display_name || catId;
    html += `<div class="genre-category-group" data-category="${catId}">
      <div class="genre-category-label">${escapeAttr(displayName)}</div>`;
    catGenres.forEach(g => { html += renderGenreCard(g); });
    html += `</div>`;
  });

  // Uncategorized genres (if any)
  const categorized = new Set(catIds);
  const uncategorized = genres.filter(g => !categorized.has(g.category));
  if (uncategorized.length > 0) {
    html += `<div class="genre-category-group">
      <div class="genre-category-label">Other</div>`;
    uncategorized.forEach(g => { html += renderGenreCard(g); });
    html += `</div>`;
  }

  html += `</div>
      <button class="bar-btn" id="addGenreBtn" style="margin-top:10px;width:100%;height:30px;font-size:9px;letter-spacing:1px">+ NEW GENRE</button>
    </div>`;

  container.innerHTML = html;

  // Render installed pack cards
  renderInstalledPacks(installedPacks);

  // Bind pack buttons
  $('browsePacksBtn')?.addEventListener('click', () => showBrowsePacksModal());
  $('installUrlBtn')?.addEventListener('click', () => showInstallUrlModal());

  // Bind toggle clicks
  container.querySelectorAll('.settings-section .toggle-track').forEach(toggle => {
    toggle.addEventListener('click', () => {
      toggle.classList.toggle('on');
      saveAllSettings(container);
    });
  });

  // Bind format pickers (scoped per picker group)
  container.querySelectorAll('.format-picker').forEach(picker => {
    picker.querySelectorAll('.format-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        picker.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        saveAllSettings(container);
      });
    });
  });

  // Bind settings input changes
  container.querySelectorAll('.settings-section > .settings-row input, .settings-section > div > input').forEach(input => {
    input.addEventListener('change', () => saveAllSettings(container));
  });

  // Bind temp unit toggle — refresh weather on change
  container.querySelectorAll('.temp-unit-btn').forEach(btn => {
    btn.addEventListener('click', () => refreshWeather());
  });

  // Bind theme mode buttons
  container.querySelectorAll('.theme-mode-btn').forEach(btn => {
    btn.addEventListener('click', () => setThemeMode(btn.dataset.themeMode));
  });

  // Bind location search with debounce
  bindLocationSearch();

  // Load current weather location display
  loadWeatherLocation();

  // Bind category accordion expand/collapse
  container.querySelectorAll('.category-header').forEach(header => {
    header.addEventListener('click', () => {
      const card = header.closest('.category-card');
      card.classList.toggle('expanded');
      const body = card.querySelector('.category-body');
      body.style.display = card.classList.contains('expanded') ? 'grid' : 'none';
    });
  });

  // Bind category field changes
  container.querySelectorAll('.category-card input, .category-card select').forEach(el => {
    el.addEventListener('change', () => {
      const card = el.closest('.category-card');
      saveCategory(card);
    });
  });

  // Bind genre accordion expand/collapse (skip category cards)
  container.querySelectorAll('.genre-header').forEach(header => {
    if (header.closest('.category-card')) return;
    header.addEventListener('click', () => {
      const card = header.closest('.genre-card');
      card.classList.toggle('expanded');
      const body = card.querySelector('.genre-body');
      body.style.display = card.classList.contains('expanded') ? 'grid' : 'none';
    });
  });

  // Bind genre field changes — save on blur/change (skip category cards)
  container.querySelectorAll('.genre-card:not(.category-card) input, .genre-card:not(.category-card) textarea').forEach(el => {
    el.addEventListener('change', () => {
      const card = el.closest('.genre-card');
      saveGenre(card);
    });
  });

  // New category button
  $('addCategoryBtn')?.addEventListener('click', () => addNewCategory(container));

  // New genre button
  $('addGenreBtn')?.addEventListener('click', () => addNewGenre(container, catIds));
}

function renderCategoryCard(c) {
  const id = c.id;
  return `
    <div class="category-card genre-card" data-category-id="${id}">
      <div class="category-header genre-header">
        <span class="genre-chevron">\u25B6</span>
        <span class="genre-key">${escapeAttr(c.display_name || id)}</span>
        <span class="genre-bpm" style="opacity:0.5">${escapeAttr(id)}</span>
      </div>
      <div class="category-body genre-body" style="display:none">
        <div>
          <label class="genre-field-label">DISPLAY NAME</label>
          <input class="settings-input settings-input-full" data-cat-field="display_name" value="${escapeAttr(c.display_name)}">
        </div>
        <div class="genre-row-2">
          <div>
            <label class="genre-field-label">SELECTOR COLOR</label>
            <input class="settings-input" data-cat-field="genre_selector_color" value="${escapeAttr(c.genre_selector_color)}" placeholder="6B8F7A">
          </div>
          <div>
            <label class="genre-field-label">OLED COLOR</label>
            <input class="settings-input" data-cat-field="oled_color" value="${escapeAttr(c.oled_color)}" placeholder="4EDB8A">
          </div>
        </div>
        <div>
          <label class="genre-field-label">ALBUM COVER DIRECTORY</label>
          <input class="settings-input settings-input-full" data-cat-field="album_cover_directory" value="${escapeAttr(c.album_cover_directory)}" placeholder="lofi">
        </div>
        <div class="genre-row-2">
          <div>
            <label class="genre-field-label">GENERATOR</label>
            <select class="settings-input" data-cat-field="generator">
              <option value="custom" ${c.generator === 'custom' ? 'selected' : ''}>Custom</option>
              <option value="profile" ${c.generator === 'profile' ? 'selected' : ''}>Profile</option>
            </select>
          </div>
          <div>
            <label class="genre-field-label">LYRICS ENGINE</label>
            <select class="settings-input" data-cat-field="lyrics_engine">
              <option value="none" ${c.lyrics_engine === 'none' ? 'selected' : ''}>None</option>
              <option value="llm" ${c.lyrics_engine === 'llm' ? 'selected' : ''}>LLM</option>
            </select>
          </div>
        </div>
        <div>
          <label class="genre-field-label">GENERATOR PROFILE <span style="color:var(--fg-ghost)">(for profile generator)</span></label>
          <input class="settings-input settings-input-full" data-cat-field="generator_profile" value="${escapeAttr(c.generator_profile || '')}" placeholder="dreamy-chill">
        </div>
      </div>
    </div>`;
}

async function saveCategory(card) {
  const catId = card.dataset.categoryId;
  const data = {};

  card.querySelectorAll('[data-cat-field]').forEach(el => {
    data[el.dataset.catField] = el.value;
  });

  try {
    await api.updateCategory(catId, data);
  } catch (e) {
    console.error('Failed to save category:', catId, e);
  }
}

function addNewCategory() {
  const view = $('settingsView');
  if (!view) return;

  const modal = _createModal(view, 'NEW CATEGORY', `
    <div>
      <label class="genre-field-label">CATEGORY ID</label>
      <input class="settings-input settings-input-full" id="modalCatId" placeholder="ambient" autocomplete="off" spellcheck="false">
    </div>
    <div>
      <label class="genre-field-label">DISPLAY NAME</label>
      <input class="settings-input settings-input-full" id="modalCatName" placeholder="Ambient" autocomplete="off" spellcheck="false">
    </div>
  `, async () => {
    const raw = $('modalCatId')?.value || '';
    const cleanId = raw.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    if (!cleanId) return;
    const displayName = $('modalCatName')?.value?.trim() || cleanId;

    try {
      const result = await api.createCategory({ id: cleanId, display_name: displayName });
      if (result.ok) {
        _removeModal(modal);
        initSettings();
      } else {
        _showModalError(modal, result.error || 'Failed to create category.');
      }
    } catch (e) {
      _showModalError(modal, 'Failed to create category.');
    }
  });

  $('modalCatId')?.focus();
}

function renderGenreCard(g) {
  const id = g.id;
  return `
    <div class="genre-card" data-genre-id="${id}">
      <div class="genre-header">
        <span class="genre-chevron">\u25B6</span>
        <span class="genre-key">${escapeAttr(id)}</span>
        <span class="genre-bpm">${g.bpm_min}\u2013${g.bpm_max} BPM</span>
      </div>
      <div class="genre-body" style="display:none">
        <div>
          <label class="genre-field-label">DESCRIPTION</label>
          <textarea class="settings-textarea" data-field="description" rows="2">${escapeAttr(g.description)}</textarea>
        </div>
        <div>
          <label class="genre-field-label">CAPTION</label>
          <textarea class="settings-textarea" data-field="caption" rows="2">${escapeAttr(g.caption)}</textarea>
        </div>
        <div>
          <label class="genre-field-label">LYRICS / ARRANGEMENT</label>
          <textarea class="settings-textarea" data-field="lyrics" rows="6" style="min-height:100px">${escapeAttr(g.lyrics)}</textarea>
        </div>
        <div class="genre-row-3">
          <div>
            <label class="genre-field-label">BPM MIN</label>
            <input class="settings-input" data-field="bpm_min" type="number" value="${g.bpm_min}">
          </div>
          <div>
            <label class="genre-field-label">BPM MAX</label>
            <input class="settings-input" data-field="bpm_max" type="number" value="${g.bpm_max}">
          </div>
          <div>
            <label class="genre-field-label">KEY</label>
            <input class="settings-input" data-field="key_scale" value="${escapeAttr(g.key_scale)}">
          </div>
        </div>
        <div class="genre-row-2">
          <div>
            <label class="genre-field-label">DURATION MIN (s)</label>
            <input class="settings-input" data-field="duration_min" type="number" value="${g.duration_min}">
          </div>
          <div>
            <label class="genre-field-label">DURATION MAX (s)</label>
            <input class="settings-input" data-field="duration_max" type="number" value="${g.duration_max}">
          </div>
        </div>
      </div>
    </div>`;
}

async function saveGenre(card) {
  const genreId = card.dataset.genreId;
  const data = {};

  card.querySelectorAll('[data-field]').forEach(el => {
    const field = el.dataset.field;
    const val = el.value;
    if (el.type === 'number') {
      data[field] = parseInt(val, 10) || 0;
    } else {
      data[field] = val;
    }
  });

  try {
    await api.updateGenre(genreId, data);
    // Update the BPM display in the header
    const bpmLabel = card.querySelector('.genre-bpm');
    if (bpmLabel && data.bpm_min != null && data.bpm_max != null) {
      bpmLabel.textContent = data.bpm_min + '\u2013' + data.bpm_max + ' BPM';
    }
  } catch (e) {
    console.error('Failed to save genre:', genreId, e);
  }
}

async function saveAllSettings(container) {
  const saves = [
    ['api_url', gv('settApiUrl')],
    ['api_key', gv('settApiKey')],
    ['delete_disliked_tracks', isToggleOn('settDeleteDisliked')],
    ['preservation_time', parseNum(gv('settPreservation'), 24)],
    ['file_size_limit_mb', parseNum(gv('settFileSize'), 500)],
    ['buffer_max', parseNum(gv('settBufferMax'), 5)],
    ['artist_bios_enabled', isToggleOn('settArtistBios')],
    ['lm_thinking', isToggleOn('settThinking')],
    ['lm_use_cot_caption', isToggleOn('settCotCaption')],
    ['lm_use_cot_language', isToggleOn('settCotLanguage')],
    ['lm_constrained_decoding', isToggleOn('settConstrained')],
    ['lm_lm_cfg_scale', parseFloat(gv('settCfgScale')) || 2.0],
    ['output_use_format', isToggleOn('settUseFormat')],
    ['output_inference_steps', parseNum(gv('settInfSteps'), 8)],
    ['output_audio_format', container.querySelector('[data-format].active')?.dataset.format || 'mp3'],
    ['weather_temp_unit', container.querySelector('.temp-unit-btn.active')?.dataset.unit || 'fahrenheit'],
    ['theme_mode', container.querySelector('.theme-mode-btn.active')?.dataset.themeMode || 'auto'],
  ];

  for (const [key, value] of saves) {
    try {
      await api.updateSetting(key, value);
    } catch (e) {
      console.error('Failed to save setting:', key, e);
    }
  }
}

function renderToggle(id, isOn) {
  return `<div class="toggle-track ${isOn ? 'on' : ''}" id="${id}"><div class="toggle-thumb"></div></div>`;
}

function isToggleOn(id) {
  const el = $(id);
  return el ? el.classList.contains('on') : false;
}

function gv(id) {
  const el = $(id);
  return el ? el.value : '';
}

function parseNum(val, fallback) {
  const n = parseInt(val, 10);
  return isNaN(n) ? fallback : n;
}

function addNewGenre(container, catIds) {
  const view = $('settingsView');
  if (!view) return;

  const options = catIds.map(c =>
    `<option value="${escapeAttr(c)}">${escapeAttr(c)}</option>`
  ).join('');

  const modal = _createModal(view, 'NEW GENRE', `
    <div>
      <label class="genre-field-label">CATEGORY</label>
      <select class="settings-input settings-input-full" id="modalGenreCat">${options}</select>
    </div>
    <div>
      <label class="genre-field-label">GENRE ID</label>
      <input class="settings-input settings-input-full" id="modalGenreId" placeholder="chill-vibes" autocomplete="off" spellcheck="false">
    </div>
  `, async () => {
    const category = $('modalGenreCat')?.value;
    const raw = $('modalGenreId')?.value || '';
    const id = raw.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    if (!id || !category) return;

    const prefix = id.split('-')[0].slice(0, 6);
    try {
      const result = await api.createGenre({ id, category, prefix });
      if (result.ok) {
        _removeModal(modal);
        initSettings();
      } else {
        _showModalError(modal, result.error || 'Failed to create genre.');
      }
    } catch (e) {
      _showModalError(modal, 'Failed to create genre.');
    }
  });

  $('modalGenreId')?.focus();
}

function bindLocationSearch() {
  const input = $('settLocationSearch');
  if (!input) return;
  let debounceTimer;
  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (q.length < 2) {
      $('locationDropdown').innerHTML = '';
      $('locationDropdown').style.display = 'none';
      return;
    }
    debounceTimer = setTimeout(() => searchLocation(q), 300);
  });
}

async function searchLocation(query) {
  const dropdown = $('locationDropdown');
  try {
    const data = await api.geocodeSearch(query);
    if (!data.results || data.results.length === 0) {
      dropdown.innerHTML = '<div class="location-dropdown-empty">No results</div>';
      dropdown.style.display = 'block';
      return;
    }
    dropdown.innerHTML = data.results.map(r => {
      const label = [r.name, r.admin1, r.country_code].filter(Boolean).join(', ');
      return `<div class="location-dropdown-item" data-lat="${r.latitude}" data-lng="${r.longitude}" data-label="${escapeAttr(label)}">${escapeAttr(label)}</div>`;
    }).join('');
    dropdown.style.display = 'block';

    dropdown.querySelectorAll('.location-dropdown-item').forEach(item => {
      item.addEventListener('click', () => pickLocation(item));
    });
  } catch (e) {
    dropdown.style.display = 'none';
  }
}

async function pickLocation(item) {
  const lat = parseFloat(item.dataset.lat);
  const lng = parseFloat(item.dataset.lng);
  const label = item.dataset.label;

  try {
    await api.saveWeatherLocation(lat, lng, label);
    $('locationDropdown').style.display = 'none';
    $('settLocationSearch').value = '';
    $('locationCurrent').textContent = '\u2713 ' + label;
    refreshWeather();
  } catch (e) {
    console.error('Failed to save location:', e);
  }
}

async function loadWeatherLocation() {
  try {
    const loc = await api.getWeatherLocation();
    const el = $('locationCurrent');
    if (loc.configured && el) {
      el.textContent = '\u2713 ' + loc.display_name;
    }
  } catch (e) { /* ignore */ }
}

// ---------------------------------------------------------------------------
// Styled modal helpers (replaces browser prompt/alert)
// ---------------------------------------------------------------------------

function _createModal(parent, title, bodyHtml, onConfirm) {
  // Remove any existing settings modal
  parent.querySelector('.settings-modal-overlay')?.remove();

  const overlay = document.createElement('div');
  overlay.className = 'settings-modal-overlay';
  overlay.innerHTML = `
    <div class="settings-modal-box">
      <div class="settings-modal-header">
        <span class="settings-modal-title">${title}</span>
        <button class="settings-modal-close">&times;</button>
      </div>
      <div class="settings-modal-body">${bodyHtml}</div>
      <div class="settings-modal-error" style="display:none"></div>
      <div class="settings-modal-actions">
        <button class="new-playlist-btn settings-modal-cancel">CANCEL</button>
        <button class="new-playlist-btn new-playlist-create settings-modal-confirm">CREATE</button>
      </div>
    </div>`;

  parent.appendChild(overlay);

  // Bind close
  const close = () => _removeModal(overlay);
  overlay.querySelector('.settings-modal-close').addEventListener('click', close);
  overlay.querySelector('.settings-modal-cancel').addEventListener('click', close);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

  // Bind confirm
  overlay.querySelector('.settings-modal-confirm').addEventListener('click', onConfirm);

  // Enter key submits
  overlay.querySelectorAll('input').forEach(input => {
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') onConfirm(); });
  });

  return overlay;
}

function _removeModal(overlay) {
  overlay?.remove();
}

function _showModalError(overlay, msg) {
  const el = overlay.querySelector('.settings-modal-error');
  if (el) {
    el.textContent = msg;
    el.style.display = 'block';
  }
}

// ---------------------------------------------------------------------------
// Genre Packs UI
// ---------------------------------------------------------------------------

const CORE_CATEGORIES = new Set(['lofi', 'citypop', 'synthwave']);

function renderInstalledPacks(installedPacks) {
  const container = $('packCards');
  if (!container) return;

  const entries = Object.entries(installedPacks || {});
  if (entries.length === 0) {
    container.innerHTML = '<div style="font-size:11px;color:var(--fg-dim);font-family:var(--font-mono);padding:4px 0">No genre packs installed.</div>';
    return;
  }

  container.innerHTML = entries.map(([catId, info]) => {
    const m = info.manifest || {};
    const name = m.name || catId;
    const desc = m.description || '';
    const version = m.version || '';
    return `
      <div class="genre-card" data-pack-id="${escapeAttr(catId)}">
        <div class="genre-header" style="cursor:default">
          <span class="genre-key">${escapeAttr(name)}</span>
          <span class="genre-bpm" style="opacity:0.5">${escapeAttr(version)}</span>
          <button class="bar-btn pack-delete-btn" data-pack-id="${escapeAttr(catId)}" style="margin-left:auto;height:20px;font-size:8px;padding:0 8px;letter-spacing:0.5px">DELETE</button>
        </div>
        ${desc ? `<div style="font-size:10px;color:var(--fg-dim);font-family:var(--font-mono);padding:2px 10px 6px">${escapeAttr(desc)}</div>` : ''}
      </div>`;
  }).join('');

  container.querySelectorAll('.pack-delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      confirmDeletePack(btn.dataset.packId);
    });
  });
}

function confirmDeletePack(categoryId) {
  if (CORE_CATEGORIES.has(categoryId)) return;
  const view = $('settingsView');
  if (!view) return;

  const modal = _createModal(view, 'DELETE PACK', `
    <div style="font-size:11px;color:var(--fg-dim);font-family:var(--font-mono)">
      Remove pack <strong>${escapeAttr(categoryId)}</strong> and all its files?
      Tracks and albums must be deleted first.
    </div>
  `, async () => {
    try {
      const result = await api.uninstallPack(categoryId);
      if (result.ok) {
        _removeModal(modal);
        initSettings();
      } else {
        _showModalError(modal, result.error || 'Failed to delete pack.');
      }
    } catch (e) {
      _showModalError(modal, e.message || 'Failed to delete pack.');
    }
  });
}

function showBrowsePacksModal() {
  const view = $('settingsView');
  if (!view) return;

  const modal = _createModal(view, 'BROWSE GENRE PACKS', `
    <div>
      <input class="settings-input settings-input-full" id="packSearchInput" placeholder="Search packs..." autocomplete="off">
      <div id="packBrowseList" style="max-height:200px;overflow-y:auto;margin-top:8px">
        <div style="font-size:11px;color:var(--fg-dim);font-family:var(--font-mono)">Loading...</div>
      </div>
    </div>
  `, () => {});

  // Hide confirm button — install happens per-item
  const confirmBtn = modal.querySelector('.settings-modal-confirm');
  if (confirmBtn) confirmBtn.style.display = 'none';

  loadPackIndex(modal);
}

async function loadPackIndex(modal) {
  const list = modal.querySelector('#packBrowseList');
  const search = modal.querySelector('#packSearchInput');

  try {
    const packs = await api.browsePacks();
    if (!packs || packs.length === 0) {
      list.innerHTML = '<div style="font-size:11px;color:var(--fg-dim);font-family:var(--font-mono)">No packs available.</div>';
      return;
    }

    function renderList(filter) {
      const filtered = filter
        ? packs.filter(p => (p.name || p.id || '').toLowerCase().includes(filter) || (p.path || '').toLowerCase().includes(filter))
        : packs;

      if (filtered.length === 0) {
        list.innerHTML = '<div style="font-size:11px;color:var(--fg-dim);font-family:var(--font-mono)">No matches.</div>';
        return;
      }

      list.innerHTML = filtered.map(p => {
        const name = p.name || p.id || 'unknown';
        const path = p.path || '';
        const installed = p.installed;
        return `
          <div class="genre-card" style="margin-bottom:4px" data-pack-path="${escapeAttr(path)}">
            <div class="genre-header" style="cursor:default;padding:6px 10px">
              <span class="genre-key" style="font-size:11px">${escapeAttr(name)}</span>
              <span class="genre-bpm" style="opacity:0.5;font-size:9px">${escapeAttr(path)}</span>
              ${installed
                ? '<span style="margin-left:auto;font-size:8px;color:var(--fg-dim);letter-spacing:0.5px">INSTALLED</span>'
                : `<button class="bar-btn pack-install-btn" data-pack-path="${escapeAttr(path)}" style="margin-left:auto;height:20px;font-size:8px;padding:0 8px;letter-spacing:0.5px">INSTALL</button>`
              }
            </div>
          </div>`;
      }).join('');

      list.querySelectorAll('.pack-install-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          installPackFromBrowse(btn, btn.dataset.packPath, modal);
        });
      });
    }

    renderList('');

    let debounce;
    search?.addEventListener('input', () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => renderList((search.value || '').trim().toLowerCase()), 150);
    });
  } catch (e) {
    list.innerHTML = `<div style="font-size:11px;color:var(--accent-red,#c44);font-family:var(--font-mono)">Failed to load pack index.</div>`;
  }
}

async function installPackFromBrowse(btn, packPath, modal) {
  btn.disabled = true;
  btn.innerHTML = '<span class="spin-dots">INSTALLING</span>';

  try {
    const result = await api.installPack(packPath);
    if (result.ok) {
      btn.innerHTML = 'INSTALLED';
      btn.style.opacity = '0.5';
      _showModalError(modal, 'Pack installed. Restart the app to load the new genre.');
    } else {
      _showModalError(modal, result.error || 'Install failed.');
      btn.textContent = 'INSTALL';
      btn.disabled = false;
    }
  } catch (e) {
    _showModalError(modal, e.message || 'Install failed.');
    btn.textContent = 'INSTALL';
    btn.disabled = false;
  }
}

function showInstallUrlModal() {
  const view = $('settingsView');
  if (!view) return;

  const modal = _createModal(view, 'INSTALL FROM URL', `
    <div>
      <label class="genre-field-label">ZIP URL</label>
      <input class="settings-input settings-input-full" id="packUrlInput" placeholder="https://example.com/pack.zip" autocomplete="off">
    </div>
  `, async () => {
    const url = $('packUrlInput')?.value?.trim();
    if (!url) return;

    const confirmBtn = modal.querySelector('.settings-modal-confirm');
    if (confirmBtn) {
      confirmBtn.disabled = true;
      confirmBtn.innerHTML = '<span class="spin-dots">INSTALLING</span>';
    }

    try {
      const result = await api.installPack(null, url);
      if (result.ok) {
        _showModalError(modal, 'Pack installed. Restart the app to load the new genre.');
        if (confirmBtn) { confirmBtn.textContent = 'INSTALLED'; confirmBtn.style.opacity = '0.5'; }
      } else {
        _showModalError(modal, result.error || 'Install failed.');
        if (confirmBtn) { confirmBtn.disabled = false; confirmBtn.textContent = 'INSTALL'; }
      }
    } catch (e) {
      _showModalError(modal, e.message || 'Install failed.');
      if (confirmBtn) { confirmBtn.disabled = false; confirmBtn.textContent = 'INSTALL'; }
    }
  });

  $('packUrlInput')?.focus();
}

function escapeAttr(str) {
  return (str || '').replace(/"/g, '&quot;').replace(/</g, '&lt;');
}
