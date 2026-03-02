"""ACE-Step API client: submit tasks, poll results, download audio."""

import json
import logging
import random
import time

import requests

from src.database import get_db, get_setting

logger = logging.getLogger(__name__)

POLL_INTERVAL = 10  # seconds between poll attempts

# Cached health status to avoid blocking the API on every frontend poll
_health_cache = {"healthy": False, "checked_at": 0}
HEALTH_CACHE_TTL = 10  # seconds


def get_api_base():
    """Return the configured ACE-Step API base URL."""
    return get_setting("api_url", "http://127.0.0.1:8001")


def get_api_key():
    """Return the configured API key, or None."""
    key = get_setting("api_key", "")
    return key if key and key != "# optional api key here" else None


def check_health():
    """Check if the ACE-Step API is reachable. Returns cached result."""
    now = time.time()
    if now - _health_cache["checked_at"] < HEALTH_CACHE_TTL:
        return _health_cache["healthy"]

    healthy = _do_health_check()
    _health_cache["healthy"] = healthy
    _health_cache["checked_at"] = now
    return healthy


def _do_health_check():
    """Perform the actual HTTP health check. Returns True/False."""
    try:
        url = f"{get_api_base()}/health"
        resp = requests.get(url, timeout=3)
        resp.raise_for_status()
        data = resp.json()
        status = (data.get("data") or {}).get("status", "unknown")
        return status == "running" or resp.status_code == 200
    except Exception as e:
        logger.warning("ACE-Step health check failed: %s", e)
        return False


def submit_task(genre_row, filled_lyrics=None, instrumental=None):
    """Submit a generation task to ACE-Step. Returns task_id or None.

    Args:
        genre_row: Genre database row.
        filled_lyrics: If provided, use these lyrics instead of the genre's
                       static template. Used for dynamic_lyrics genres.
        instrumental: Override instrumental flag. If None, defaults to True.
    """
    api_base = get_api_base()
    url = f"{api_base}/release_task"

    bpm = random.randint(genre_row["bpm_min"], genre_row["bpm_max"])
    duration = random.randint(genre_row["duration_min"], genre_row["duration_max"])

    lyrics = filled_lyrics if filled_lyrics else genre_row["lyrics"]
    is_instrumental = instrumental if instrumental is not None else True
    vocal_lang = "ja" if not is_instrumental else "unknown"

    payload = {
        "prompt": genre_row["caption"],
        "lyrics": lyrics,
        "instrumental": is_instrumental,
        "bpm": bpm,
        "key_scale": genre_row["key_scale"],
        "time_signature": "4",
        "audio_duration": duration,
        "vocal_language": vocal_lang,
        # LM settings from DB
        "thinking": get_setting("lm_thinking", True),
        "use_cot_caption": get_setting("lm_use_cot_caption", True),
        "use_cot_language": get_setting("lm_use_cot_language", True),
        "constrained_decoding": get_setting("lm_constrained_decoding", True),
        "lm_cfg_scale": get_setting("lm_lm_cfg_scale", 2.0),
        # Output settings from DB
        "use_format": get_setting("output_use_format", True),
        "inference_steps": get_setting("output_inference_steps", 8),
        "infer_method": "ode",
        "audio_format": get_setting("output_audio_format", "mp3"),
        "batch_size": 1,
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        task_id = (body.get("data") or {}).get("task_id") or body.get("task_id")
        if not task_id:
            logger.error("No task_id in response: %s", body)
            return None
        logger.info("Submitted task %s for genre %s (bpm=%d, dur=%ds)",
                     task_id, genre_row["id"], bpm, duration)
        return task_id
    except Exception as e:
        logger.error("Failed to submit task: %s", e)
        return None


def poll_result(task_id):
    """Poll for task result. Returns (status, result_list).

    status: 'processing', 'success', 'failed', or 'error'
    - 'failed' = API explicitly reported the task failed (permanent)
    - 'error'  = transient HTTP/network error (caller should retry)
    result_list: parsed result on success, None otherwise
    """
    api_base = get_api_base()
    url = f"{api_base}/query_result"
    payload = {"task_id_list": [task_id]}

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        body = resp.json()

        task_data = _extract_task_data(body)
        status = task_data.get("status", 0)

        if status == 1:
            result = _parse_result_field(task_data.get("result", "[]"))
            return "success", result
        if status == 2:
            logger.error("Task %s failed: %s", task_id, task_data)
            return "failed", None

        return "processing", None
    except Exception as e:
        logger.warning("Poll error for task %s: %s", task_id, e)
        return "error", None


def download_audio(file_path, dest_path):
    """Download audio file from ACE-Step to local path. Returns True/False."""
    api_base = get_api_base()
    url = f"{api_base}{file_path}"

    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        dest_path.write_bytes(resp.content)
        size_kb = len(resp.content) / 1024
        logger.info("Downloaded audio: %s (%.1f KB)", dest_path.name, size_kb)
        return True
    except Exception as e:
        logger.error("Failed to download audio: %s", e)
        return False


def _extract_task_data(body):
    """Pull the first matching task entry from query_result response."""
    data = body.get("data", body)
    if isinstance(data, list) and data:
        return data[0]
    return data or {}


def _parse_result_field(result_raw):
    """Parse the result field (may be a JSON string) into a list."""
    if isinstance(result_raw, str):
        return json.loads(result_raw)
    return result_raw
