"""Compute waveform amplitude data from audio files."""

import json
import logging
import struct
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

WAVEFORM_BINS = 150


def compute_waveform(filepath, bins=WAVEFORM_BINS):
    """Compute RMS amplitude waveform from an audio file.

    Returns a list of floats (0.0 to 1.0) representing amplitude bins.
    Falls back to pydub for MP3, uses stdlib wave for WAV.
    """
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    try:
        if suffix == ".wav":
            return _waveform_from_wav(filepath, bins)
        else:
            return _waveform_from_pydub(filepath, bins)
    except Exception as e:
        logger.error("Failed to compute waveform for %s: %s", filepath, e)
        return _default_waveform(bins)


def _waveform_from_wav(filepath, bins):
    """Compute waveform from a WAV file using stdlib."""
    with wave.open(str(filepath), "rb") as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sample_width == 2:
        fmt = "<" + "h" * (len(raw) // 2)
        samples = list(struct.unpack(fmt, raw))
    elif sample_width == 1:
        samples = [s - 128 for s in raw]
    else:
        return _default_waveform(bins)

    # Mix to mono
    if n_channels > 1:
        samples = [
            sum(samples[i:i + n_channels]) // n_channels
            for i in range(0, len(samples), n_channels)
        ]

    return _rms_bins(samples, bins)


def _waveform_from_pydub(filepath, bins):
    """Compute waveform from MP3/other using pydub."""
    from pydub import AudioSegment

    audio = AudioSegment.from_file(str(filepath))
    samples = audio.get_array_of_samples()

    # Mix to mono
    if audio.channels > 1:
        samples = [
            sum(samples[i:i + audio.channels]) // audio.channels
            for i in range(0, len(samples), audio.channels)
        ]

    return _rms_bins(list(samples), bins)


def _rms_bins(samples, bins):
    """Divide samples into bins and compute RMS for each."""
    if not samples:
        return _default_waveform(bins)

    chunk_size = max(1, len(samples) // bins)
    amplitudes = []

    for i in range(bins):
        start = i * chunk_size
        end = min(start + chunk_size, len(samples))
        chunk = samples[start:end]
        if not chunk:
            amplitudes.append(0.0)
            continue
        rms = (sum(s * s for s in chunk) / len(chunk)) ** 0.5
        amplitudes.append(rms)

    # Normalize to 0.0 - 1.0
    max_amp = max(amplitudes) if amplitudes else 1.0
    if max_amp == 0:
        max_amp = 1.0

    return [round(a / max_amp, 3) for a in amplitudes]


def _default_waveform(bins):
    """Return a flat waveform as fallback."""
    return [0.3] * bins


def waveform_to_json(waveform):
    """Serialize waveform list to JSON string for DB storage."""
    return json.dumps(waveform)
