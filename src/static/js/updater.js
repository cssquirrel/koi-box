/** Auto-update: badge notification, update modal, and What's New display. */

import * as api from './api.js';
import { _createModal, _removeModal, _showModalError } from './settings.js';
import { $ } from './utils.js';

let _updateInfo = null;

// ---------------------------------------------------------------------------
// Update check + badge
// ---------------------------------------------------------------------------

export async function checkForUpdate() {
  try {
    const result = await api.checkUpdate();
    if (result.available) {
      _updateInfo = result;
      _showBadge(result.latest_version);
    }
  } catch {
    // Silent — offline or API error
  }
}

function _showBadge(version) {
  const badge = $('updateBadge');
  if (!badge) return;
  badge.style.display = '';
  badge.title = `Update available: v${version}`;
  badge.addEventListener('click', _openUpdateModal, { once: true });
}

// ---------------------------------------------------------------------------
// Update modal
// ---------------------------------------------------------------------------

function _openUpdateModal() {
  if (!_updateInfo) return;

  const { latest_version, current_version, release_notes } = _updateInfo;

  const notesHtml = _escapeAndFormat(release_notes);
  const body = `
    <div class="update-modal-content">
      <p class="update-modal-versions">
        <span class="update-modal-dim">Current:</span> v${current_version}
        <span class="update-modal-arrow">&rarr;</span>
        <span class="update-modal-dim">New:</span> v${latest_version}
      </p>
      <div class="update-modal-notes">${notesHtml}</div>
    </div>`;

  const parent = document.body;
  const overlay = _createModal(
    parent,
    `UPDATE AVAILABLE — v${latest_version}`,
    body,
    () => _applyUpdate(overlay),
    'INSTALL',
    'CANCEL',
  );
}

async function _applyUpdate(overlay) {
  if (!_updateInfo) return;

  const confirmBtn = overlay.querySelector('.settings-modal-confirm');
  const cancelBtn = overlay.querySelector('.settings-modal-cancel');
  if (confirmBtn) {
    confirmBtn.textContent = 'INSTALLING...';
    confirmBtn.disabled = true;
  }
  if (cancelBtn) cancelBtn.style.display = 'none';

  try {
    const result = await api.applyUpdate(
      _updateInfo.release_notes || '',
      _updateInfo.latest_version || '',
    );
    if (result.ok) {
      _showSuccess(overlay);
    } else {
      _showModalError(overlay, result.error || 'Update failed.');
      _resetButtons(overlay);
    }
  } catch (e) {
    _showModalError(overlay, e.message || 'Update request failed.');
    _resetButtons(overlay);
  }
}

function _showSuccess(overlay) {
  const body = overlay.querySelector('.settings-modal-body');
  if (body) {
    body.innerHTML = `
      <div class="update-modal-content">
        <p class="update-modal-success">Update installed successfully.</p>
        <p class="update-modal-dim">Restart koi-box to apply the changes.</p>
      </div>`;
  }
  // Hide error if shown
  const err = overlay.querySelector('.settings-modal-error');
  if (err) err.style.display = 'none';

  // Replace action buttons with a single CLOSE
  const actions = overlay.querySelector('.settings-modal-actions');
  if (actions) {
    actions.innerHTML = `
      <button class="new-playlist-btn new-playlist-create settings-modal-close-final">CLOSE</button>`;
    actions.querySelector('.settings-modal-close-final')
      .addEventListener('click', () => _removeModal(overlay));
  }

  // Hide the badge
  const badge = $('updateBadge');
  if (badge) badge.style.display = 'none';
}

function _resetButtons(overlay) {
  const confirmBtn = overlay.querySelector('.settings-modal-confirm');
  const cancelBtn = overlay.querySelector('.settings-modal-cancel');
  if (confirmBtn) {
    confirmBtn.textContent = 'INSTALL';
    confirmBtn.disabled = false;
  }
  if (cancelBtn) cancelBtn.style.display = '';
}

// ---------------------------------------------------------------------------
// What's New (post-update)
// ---------------------------------------------------------------------------

export async function showWhatsNew() {
  try {
    const settings = await api.getSettings();
    const notesSetting = settings.find(s => s.key === 'update_release_notes');
    const versionSetting = settings.find(s => s.key === 'update_release_version');

    const notes = notesSetting ? JSON.parse(notesSetting.value) : '';
    const version = versionSetting ? JSON.parse(versionSetting.value) : '';

    if (!notes) return;

    const notesHtml = _escapeAndFormat(notes);
    const body = `
      <div class="update-modal-content">
        <div class="update-modal-notes">${notesHtml}</div>
      </div>`;

    const parent = document.body;
    const overlay = _createModal(
      parent,
      `WHAT'S NEW IN v${version || '?'}`,
      body,
      () => {
        _clearWhatsNew();
        _removeModal(overlay);
      },
      'GOT IT',
      'CLOSE',
    );

    // Also clear on cancel/close
    overlay.querySelector('.settings-modal-cancel')
      ?.addEventListener('click', _clearWhatsNew);
    overlay.querySelector('.settings-modal-close')
      ?.addEventListener('click', _clearWhatsNew);
  } catch {
    // Silent
  }
}

async function _clearWhatsNew() {
  try {
    await api.updateSetting('update_release_notes', '');
    await api.updateSetting('update_release_version', '');
  } catch {
    // Silent
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function _escapeAndFormat(text) {
  if (!text) return '<em>No release notes available.</em>';
  const div = document.createElement('div');
  div.textContent = text;
  // Convert line breaks to <br> for basic readability
  return div.innerHTML.replace(/\n/g, '<br>');
}
