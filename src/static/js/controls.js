/** Transport buttons, volume knob/bar, and preset interactions. */

import { $, PAUSE_SVG, PLAY_SVG, emit, on } from "./utils.js";
import { engageAutopilot, disengageAutopilot, isAutopilotOn } from "./autopilot.js";
import { getSunTimes } from "./weather.js";
import * as api from "./api.js";

// -- Volume state --
let volume = 0.75;
let isMuted = false;
let knobDragging = false;
let _volSaveTimer = null;

const KNOB_MIN_ANGLE = -135;
const KNOB_MAX_ANGLE = 135;
const VOL_SEGS = 16; // kept for knob step math

// -- Shuffle / Loop state --
let shuffleOn = false;
let loopOn = false;
let ambOn = false;
let libOn = false;

export function getVolume() {
  return isMuted ? 0 : volume;
}

/** Restore saved volume + mute state from settings. */
export function applyVolumeState(vol, muted) {
  volume = Math.max(0, Math.min(1, vol));
  isMuted = !!muted;
  renderKnob();
  renderVolume();
}

function saveVolumeState() {
  clearTimeout(_volSaveTimer);
  _volSaveTimer = setTimeout(() => {
    api.updateSetting("volume_state", { volume, muted: isMuted }).catch(() => {});
  }, 500);
}
export function isShuffleOn() {
  return shuffleOn;
}
export function isLoopOn() {
  return loopOn;
}
export function isLibraryOn() {
  return libOn;
}

/** Apply library mode state (called from app.js restore and radio.js poll sync). */
export function applyLibraryState(on) {
  libOn = !!on;
  const btn = $('libBtn');
  if (btn) btn.classList.toggle('active', libOn);
  updateStatus();
}

// -- Knob --

function knobAngleFromVolume(vol) {
  return KNOB_MIN_ANGLE + vol * (KNOB_MAX_ANGLE - KNOB_MIN_ANGLE);
}

function renderKnob() {
  const angle = knobAngleFromVolume(isMuted ? 0 : volume);
  $("knob").style.transform = "rotate(" + angle + "deg)";
}

function initKnob() {
  const wrap = $("knobWrap");

  function knobFromEvent(e) {
    const rect = wrap.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const angle =
      Math.atan2(e.clientX - cx, -(e.clientY - cy)) * (180 / Math.PI);
    const clamped = Math.max(KNOB_MIN_ANGLE, Math.min(KNOB_MAX_ANGLE, angle));
    volume = (clamped - KNOB_MIN_ANGLE) / (KNOB_MAX_ANGLE - KNOB_MIN_ANGLE);
    if (isMuted) isMuted = false;
    renderKnob();
    renderVolume();
    emit("volume-change", { volume: getVolume() });
    saveVolumeState();
  }

  wrap.addEventListener("mousedown", (e) => {
    knobDragging = true;
    knobFromEvent(e);
    e.preventDefault();
  });
  document.addEventListener("mousemove", (e) => {
    if (knobDragging) knobFromEvent(e);
  });
  document.addEventListener("mouseup", () => {
    knobDragging = false;
  });

  renderKnob();
}

// -- Volume Meter --

const METER_TICKS = 20;

function initVolumeBar() {
  const ticks = $("volMeterTicks");
  for (let i = 0; i <= METER_TICKS; i++) {
    const tick = document.createElement("div");
    tick.className = "vol-tick";
    const line = document.createElement("div");
    line.className = "vol-tick-line";
    tick.appendChild(line);
    ticks.appendChild(tick);
  }
  renderVolume();

  const meter = $("volMeter");
  meter.addEventListener("mousedown", volumeInteract);
  meter.addEventListener("mousemove", (e) => {
    if (e.buttons === 1) volumeInteract(e);
  });

  $("muteBtn").addEventListener("click", () => {
    isMuted = !isMuted;
    renderVolume();
    renderKnob();
    emit("volume-change", { volume: getVolume() });
    saveVolumeState();
  });
}

function volumeInteract(e) {
  const ticks = $("volMeterTicks");
  const rect = ticks.getBoundingClientRect();
  volume = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
  if (isMuted) isMuted = false;
  renderVolume();
  renderKnob();
  emit("volume-change", { volume: getVolume() });
  saveVolumeState();
}

function renderVolume() {
  const displayVol = isMuted ? 0 : volume;
  const filled = Math.round(displayVol * METER_TICKS);

  // Update tick colors and heights
  const lines = $("volMeterTicks").querySelectorAll(".vol-tick-line");
  lines.forEach((line, i) => {
    const major = i % 5 === 0;
    const h = major ? 14 : 8;
    line.style.height = h + "px";
    if (i < filled) {
      line.style.background =
        i >= METER_TICKS * 0.8 ? "var(--accent)" : "var(--fg-dim)";
    } else {
      line.style.background = "var(--border-light)";
    }
  });

  // Position needle over ticks area
  const needle = $("volNeedle");
  const ticks = $("volMeterTicks");
  const offset = ticks.offsetLeft + displayVol * ticks.offsetWidth;
  needle.style.left = offset + "px";

  // Update percentage
  $("volumePct").innerHTML =
    Math.round(displayVol * 100) + '<span class="pct-sign">%</span>';

  // Update mute button
  $("muteBtn").classList.toggle("muted", isMuted);
  $("muteCross").style.display = isMuted ? "" : "none";
  $("muteWave1").style.display = isMuted ? "none" : "";
  $("muteWave2").style.display = isMuted || displayVol < 0.5 ? "none" : "";
}

// -- Play/Pause Icons --

export function setPlayIcons(isPlaying) {
  const svg = isPlaying ? PAUSE_SVG : PLAY_SVG;
  $("playIcon").innerHTML = svg;
  $("plPlayIcon").innerHTML = svg;
}

// -- Status --

function updateStatus() {
  const parts = [];
  if (isAutopilotOn()) parts.push("AP");
  if (libOn) parts.push("LIB");
  if (ambOn) parts.push("AMB");
  if (loopOn) parts.push("LOOP");
  if (shuffleOn) parts.push("SHUF");
  $("statusExtra").textContent = parts.length
    ? "\u00B7 " + parts.join(" \u00B7 ")
    : "";
}

// -- Transport Buttons --

function initTransport() {
  // Play/Pause
  $("playBtn").addEventListener("click", () => emit("toggle-play"));
  $("plPlayBtn").addEventListener("click", () => emit("toggle-play"));

  // Skip
  $("skipFwdBtn").addEventListener("click", () => emit("skip-forward"));
  $("skipBackBtn").addEventListener("click", () => emit("skip-back"));
  $("plSkipFwdBtn").addEventListener("click", () => emit("pl-skip-forward"));
  $("plSkipBackBtn").addEventListener("click", () => emit("pl-skip-back"));

  // Shuffle
  $("shuffleBtn").addEventListener("click", function () {
    shuffleOn = !shuffleOn;
    this.classList.toggle("active", shuffleOn);
    $("plShuffleBtn").classList.toggle("active", shuffleOn);
    updateStatus();
  });
  $("plShuffleBtn").addEventListener("click", function () {
    shuffleOn = !shuffleOn;
    this.classList.toggle("active", shuffleOn);
    $("shuffleBtn").classList.toggle("active", shuffleOn);
    updateStatus();
  });

  // Loop
  $("loopBtn").addEventListener("click", function () {
    loopOn = !loopOn;
    this.classList.toggle("active", loopOn);
    $("plLoopBtn").classList.toggle("active", loopOn);
    updateStatus();
  });
  $("plLoopBtn").addEventListener("click", function () {
    loopOn = !loopOn;
    this.classList.toggle("active", loopOn);
    $("loopBtn").classList.toggle("active", loopOn);
    updateStatus();
  });

  // Ambient / Auto
  $("ambBtn").addEventListener("click", function () {
    ambOn = !ambOn;
    this.classList.toggle("active", ambOn);
    updateStatus();
  });
  $("autoBtn").addEventListener("click", function () {
    if (isAutopilotOn()) {
      disengageAutopilot();
      this.classList.remove("active");
    } else {
      engageAutopilot();
      this.classList.add("active");
    }
    updateStatus();
  });

  // Library mode
  $("libBtn").addEventListener("click", function () {
    libOn = !libOn;
    this.classList.toggle("active", libOn);
    api.updateSetting("library_mode", libOn).catch(() => {});
    updateStatus();
  });

  // Thumbs
  $("thumbsDownBtn").addEventListener("click", function () {
    const on = !this.classList.contains("active");
    this.classList.toggle("active", on);
    this.querySelector(".emoji").classList.toggle("active", on);
    $("thumbsUpBtn").classList.remove("active");
    $("thumbsUpBtn").querySelector(".emoji").classList.remove("active");
    if (on) emit("track-dislike");
  });
  $("thumbsUpBtn").addEventListener("click", function () {
    const on = !this.classList.contains("active");
    this.classList.toggle("active", on);
    this.querySelector(".emoji").classList.toggle("active", on);
    $("thumbsDownBtn").classList.remove("active");
    $("thumbsDownBtn").querySelector(".emoji").classList.remove("active");
    if (on) emit("track-favorite");
  });

  // Add to playlist
  $("addToPlaylistBtn").addEventListener("click", () =>
    emit("add-to-playlist"),
  );
}

// -- Sun / Moon Arc --

function toHourFrac(isoStr) {
  if (!isoStr) return null;
  const d = new Date(isoStr);
  if (isNaN(d)) return null;
  return d.getHours() + d.getMinutes() / 60;
}

function updateSunArc() {
  const dot = $("sunDot");
  if (!dot) return;

  const now = new Date();
  const hour = now.getHours() + now.getMinutes() / 60;
  const { sunrise, sunset } = getSunTimes();

  const riseH = toHourFrac(sunrise) ?? 6;
  const setH = toHourFrac(sunset) ?? 19;

  const isNight = hour < riseH || hour >= setH;

  if (isNight) {
    // Night: track from sunset to next sunrise
    const nightLen = (24 - setH) + riseH;
    const elapsed = hour >= setH ? (hour - setH) : (hour + 24 - setH);
    const progress = Math.max(0, Math.min(1, elapsed / nightLen));
    const angle = -90 + progress * 180;

    dot.style.transform = "translateX(-50%) rotate(" + angle + "deg)";
    dot.style.background = "#7A8FA3";
    dot.style.boxShadow = "0 0 6px rgba(122,143,163,0.4)";
    dot.classList.add("moon");
  } else {
    // Day: track from sunrise to sunset
    const dayLen = setH - riseH;
    const progress = Math.max(0, Math.min(1, (hour - riseH) / dayLen));
    const angle = -90 + progress * 180;

    dot.style.transform = "translateX(-50%) rotate(" + angle + "deg)";
    dot.style.background = "var(--accent)";
    dot.style.boxShadow = "0 0 5px rgba(255,91,26,0.35)";
    dot.classList.remove("moon");
  }
}

function initSunArc() {
  updateSunArc();
  setInterval(updateSunArc, 60000);
  on("weather:updated", updateSunArc);
}

// -- Init --

export function refreshStatus() { updateStatus(); }

// Keep status bar in sync when autopilot disengages itself (e.g. manual override)
on('autopilot:changed', () => updateStatus());

export function initControls() {
  initKnob();
  initVolumeBar();
  initTransport();
  initSunArc();
}
