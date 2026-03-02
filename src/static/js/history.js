/** Queue strip rendering: played <- current -> upcoming + generating. */

import { $, emit } from './utils.js';

/** Render the queue strip with history, current, upcoming, and generating. */
export function renderQueueStrip(history, currentTrack, upcoming, generating, progress) {
  const strip = $('historyStrip');
  if (!strip) return;
  strip.innerHTML = '';

  // Played tracks (reversed so most recent is closest to current)
  const played = (history || []).slice(0, 3).reverse();
  played.forEach(t => {
    const card = makeCard(t, 'played');
    card.addEventListener('click', () => emit('queue-track-click', { track: t }));
    strip.appendChild(card);
  });

  // Current track
  if (currentTrack) {
    strip.appendChild(makeCard(currentTrack, 'current', progress));
  }

  // Upcoming tracks (exclude current track if it appears in upcoming)
  const currentId = currentTrack ? currentTrack.id : null;
  (upcoming || []).forEach(t => {
    if (t.id !== currentId) {
      const card = makeCard(t, 'upcoming');
      card.addEventListener('click', () => emit('queue-track-click', { track: t }));
      strip.appendChild(card);
    }
  });

  // Generating placeholders
  for (let i = 0; i < (generating || 0); i++) {
    strip.appendChild(makeGeneratingCard());
  }

  // Update count label
  const total = (upcoming || []).filter(t => t.id !== currentId).length + (generating || 0);
  const label = total > 0 ? total + ' UPCOMING' : (currentTrack ? 'NOW PLAYING' : '0 TRACKS');
  $('historyCount').textContent = label;

  // Scroll to keep current card visible
  const cur = strip.querySelector('.queue-card.current');
  if (cur) {
    const stripRect = strip.getBoundingClientRect();
    const cardRect = cur.getBoundingClientRect();
    if (cardRect.left < stripRect.left || cardRect.right > stripRect.right) {
      cur.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }
  }
}

function makeCard(track, type, progress) {
  const card = document.createElement('div');
  card.className = 'queue-card ' + type;

  let html =
    '<div class="queue-card-title">' + escapeHtml(track.title) + '</div>' +
    '<div class="queue-card-artist">' + escapeHtml(track.artist) + '</div>';

  if (type === 'current' && typeof progress === 'number') {
    html += '<div class="queue-card-progress"><div class="queue-card-progress-fill" style="width:' + (progress * 100) + '%"></div></div>';
  }

  card.innerHTML = html;
  return card;
}

function makeGeneratingCard() {
  const card = document.createElement('div');
  card.className = 'queue-card generating';
  card.innerHTML =
    '<div class="queue-card-label">GENERATING</div>' +
    '<div class="queue-card-artist" style="margin-top:2px">\u2026</div>';
  return card;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str || '';
  return div.innerHTML;
}
