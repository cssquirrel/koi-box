/** Genre band tuner interactions with two-tier selection.
 *
 * Top: segmented category switch (LOFI / SYNTHWAVE / CITYPOP)
 * Bottom: variant tuner bar with needle, including ALL as first entry.
 */

import { $, emit } from './utils.js';

let allGenres = [];          // full genre list from API
let categories = [];         // ordered category names
let genresByCategory = {};   // { category: [genre, ...] }
let currentCategory = '';
let currentVariantIdx = 0;   // index in current category's variant list (0 = ALL)
let isTuning = false;
let categoryVariants = {};   // { category: variantIdx } per-category memory
let categoryColors = {};     // { category: '#hex' } built from genre data
let categoryOledColors = {}; // { category: 'hex' } built from genre data
let motorized = false;       // slower transitions when autopilot is driving

// The variant list for the current category, with ALL prepended
function currentVariants() {
  const variants = genresByCategory[currentCategory] || [];
  return [{ id: 'all', category: currentCategory, _isAll: true }, ...variants];
}

/** Initialize with full genre list (includes category field).
 *  savedState: optional { category, variantIdx, categoryVariants } for restore. */
export function initBand(genreList, savedState = null) {
  allGenres = genreList;

  // Group by category, preserving order; extract category-level colors
  genresByCategory = {};
  categories = [];
  categoryColors = {};
  categoryOledColors = {};
  for (const g of genreList) {
    const cat = g.category || 'other';
    if (!genresByCategory[cat]) {
      genresByCategory[cat] = [];
      categories.push(cat);
    }
    genresByCategory[cat].push(g);
    if (g.genre_selector_color && !categoryColors[cat]) {
      categoryColors[cat] = '#' + g.genre_selector_color;
    }
    if (g.oled_color && !categoryOledColors[cat]) {
      categoryOledColors[cat] = g.oled_color;
    }
  }

  // Restore saved state or use defaults
  if (savedState && savedState.category && categories.includes(savedState.category)) {
    currentCategory = savedState.category;
    categoryVariants = savedState.categoryVariants || {};
    const maxIdx = currentVariants().length - 1;
    const savedIdx = savedState.variantIdx ?? 0;
    currentVariantIdx = savedIdx <= maxIdx ? savedIdx : 0;
  } else {
    currentCategory = categories[0] || '';
    currentVariantIdx = 1; // first real variant (skip ALL)
  }

  renderCategorySwitch();
  renderBand();
}

/** Get the currently active genre (or null for ALL). */
export function getCurrentGenre() {
  const variants = currentVariants();
  return variants[currentVariantIdx] || null;
}

export function getCurrentGenreIdx() {
  return currentVariantIdx;
}

export function getCurrentCategory() {
  return currentCategory;
}

export function isAllMode() {
  const v = currentVariants()[currentVariantIdx];
  return v && v._isAll;
}

export function setCurrentGenreIdx(idx) {
  currentVariantIdx = idx;
  renderBand();
}

export function getIsTuning() {
  return isTuning;
}

export function getCategoryVariants() {
  return { ...categoryVariants };
}

export function getAllGenres() {
  return allGenres;
}

/** Find the variant index (in the tuner bar, 0=ALL) for a genre ID within a category. */
export function getVariantIndex(category, genreId) {
  const variants = genresByCategory[category] || [];
  for (let i = 0; i < variants.length; i++) {
    if (variants[i].id === genreId) return i + 1; // +1 because ALL is index 0
  }
  return -1;
}

/** Toggle motorized mode — slower transitions for autopilot-driven movement. */
export function setMotorized(on) {
  motorized = on;
  const needle = $('bandNeedle');
  const win = $('bandWindow');
  if (needle) needle.classList.toggle('motorized', on);
  if (win) win.classList.toggle('motorized', on);
  document.querySelectorAll('.category-btn').forEach(b => b.classList.toggle('motorized', on));
}

// ── Category switch ──

function renderCategorySwitch() {
  const container = $('categorySwitch');
  if (!container) return;
  container.innerHTML = '';

  categories.forEach(cat => {
    const isActive = cat === currentCategory;
    const color = categoryColors[cat] || '#B0AAA4';

    const btn = document.createElement('button');
    btn.className = 'category-btn' + (isActive ? ' active' : '');
    btn.dataset.category = cat;

    const indicator = document.createElement('div');
    indicator.className = 'category-indicator';
    indicator.style.background = isActive ? color : '#B0AAA4';
    indicator.style.boxShadow = isActive ? `0 0 8px ${color}55` : 'none';

    const label = document.createElement('span');
    label.textContent = cat.toUpperCase();

    btn.appendChild(indicator);
    btn.appendChild(label);
    btn.addEventListener('click', () => { emit('band:manual-interact'); switchCategory(cat); });
    container.appendChild(btn);
  });
}

function switchCategory(cat) {
  if (cat === currentCategory || isTuning) return;
  currentCategory = cat;
  currentVariantIdx = -1; // nothing active during transition

  renderCategorySwitch();
  renderBand();

  // Restore last variant for this category and start playback
  const savedIdx = categoryVariants[cat] ?? 0;
  switchVariant(savedIdx, true);
}

// ── Variant tuner bar ──

function renderBand() {
  const container = $('bandGenres');
  if (!container) return;
  container.innerHTML = '';

  const variants = currentVariants();
  variants.forEach((g, i) => {
    const div = document.createElement('div');
    div.className = 'band-genre' + (i === currentVariantIdx ? ' active' : '');
    if (g._isAll) div.classList.add('band-genre-all');

    const label = g._isAll ? 'SHUFFLE' : g.id.replace(/-/g, ' ').toUpperCase();
    div.innerHTML = '<div class="genre-tick"></div><span class="genre-label">' + label + '</span>';
    div.addEventListener('click', () => { emit('band:manual-interact'); switchVariant(i); });
    container.appendChild(div);
  });

  requestAnimationFrame(updateNeedle);
}

function updateNeedle() {
  const container = $('bandGenres');
  if (!container) return;
  const genreEls = container.querySelectorAll('.band-genre');
  if (!genreEls[currentVariantIdx]) return;

  const cr = container.getBoundingClientRect();
  const gr = genreEls[currentVariantIdx].getBoundingClientRect();
  $('bandNeedle').style.left = (gr.left + gr.width / 2 - cr.left) + 'px';

  const w = $('bandWindow');
  const pad = 6;
  const wLeft = Math.max(0, gr.left - cr.left - pad);
  const wRight = Math.min(cr.width, gr.right - cr.left + pad);
  w.style.left = wLeft + 'px';
  w.style.width = (wRight - wLeft) + 'px';

  genreEls.forEach((el, i) => {
    const tick = el.querySelector('.genre-tick');
    el.classList.toggle('active', i === currentVariantIdx);
    el.classList.remove('in-range');
    tick.style.background = i === currentVariantIdx ? 'var(--accent)' : '';
  });
}

function switchVariant(idx, force = false) {
  if ((!force && idx === currentVariantIdx) || isTuning) return;
  currentVariantIdx = idx;
  categoryVariants[currentCategory] = idx;
  isTuning = true;

  $('tuningOverlay').classList.add('active');
  $('tuningFill').style.width = '0%';
  updateNeedle();

  const variant = currentVariants()[currentVariantIdx];
  const displayLabel = variant._isAll
    ? currentCategory.toUpperCase() + ' / SHUFFLE'
    : variant.id.replace(/-/g, ' ').toUpperCase();
  $('screenGenre').textContent = displayLabel;

  let pct = 0;
  const iv = setInterval(() => {
    pct += 4 + Math.random() * 6;
    if (pct > 100) pct = 100;
    $('tuningFill').style.width = pct + '%';
    $('tuningSignal').textContent = 'SIGNAL ' + Math.round(pct) + '%';
    $('tuningText').textContent = 'TUNING' + '.'.repeat(Math.floor(Date.now() / 350) % 4);

    if (pct >= 100) {
      clearInterval(iv);
      isTuning = false;
      $('tuningText').textContent = 'BUFFERING';
      $('tuningSignal').textContent = 'WAITING FOR TRACKS...';
      emit('genre-switched', {
        genre: variant,
        genreIdx: currentVariantIdx,
        category: currentCategory,
        allMode: !!variant._isAll,
      });
    }
  }, 80);
}

/**
 * Programmatically restore a category + variant from a preset.
 * Returns true if a switch was triggered, false if invalid or already there.
 */
export function restorePreset(category, variantIdx) {
  if (!genresByCategory[category]) return false;
  const maxIdx = [{ _isAll: true }, ...genresByCategory[category]].length - 1;
  if (variantIdx < 0 || variantIdx > maxIdx) return false;
  if (isTuning) return false;
  if (category === currentCategory && variantIdx === currentVariantIdx) return false;

  if (category !== currentCategory) {
    currentCategory = category;
    currentVariantIdx = -1;
    renderCategorySwitch();
    renderBand();
    switchVariant(variantIdx, true);
  } else {
    switchVariant(variantIdx, true);
  }
  return true;
}

/** Return the OLED accent color hex (without #) for the current category. */
export function getOledColor() {
  return categoryOledColors[currentCategory] || '';
}

/** Listen for window resize to reposition needle. */
window.addEventListener('resize', () => requestAnimationFrame(updateNeedle));
