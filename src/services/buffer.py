"""Background worker that keeps the radio buffer filled with generated tracks.

Generates one track at a time: submit -> poll until done -> process -> repeat.
"""

import asyncio
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import random as _random

from src.config import DOWNLOADS_DIR, flatten_genre_config
from src.database import get_all_genres, get_db, get_genre, get_genres_by_category, get_setting
from src.services.cleanup import run_cleanup

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 5  # seconds between buffer level checks
POLL_INTERVAL = 5  # seconds between result polls for active task
CLEANUP_INTERVAL = 300  # 5 minutes

_executor = ThreadPoolExecutor(max_workers=2)
_current_genre_id = None
_current_category = None
_all_mode = False
_current_track_id = None
_prebuffer_genre_id = None
_last_cleanup = 0
_valid_genre_ids = None

PREBUFFER_TARGET = 2  # tracks to pre-buffer for autopilot's next pick
MAX_POLL_ERRORS = 5  # consecutive transient errors before giving up on a task


def _get_valid_genre_ids():
    """Return the set of genre IDs from the current config (cached)."""
    global _valid_genre_ids
    if _valid_genre_ids is None:
        _valid_genre_ids = {e["id"] for e in flatten_genre_config()}
    return _valid_genre_ids


def set_current_genre(genre_id):
    """Set the genre the buffer should be filling (specific variant mode)."""
    global _current_genre_id, _current_category, _all_mode
    _current_genre_id = genre_id
    _all_mode = False
    _current_category = None


def set_current_category(category, all_mode=True):
    """Set the category for ALL mode buffering."""
    global _current_genre_id, _current_category, _all_mode
    _current_category = category
    _all_mode = all_mode
    _current_genre_id = None


def set_current_track_id(track_id):
    """Set the currently playing track ID (for cleanup protection)."""
    global _current_track_id
    _current_track_id = track_id


def set_prebuffer_genre(genre_id):
    """Hint the buffer worker to pre-fill tracks for an upcoming genre switch."""
    global _prebuffer_genre_id
    _prebuffer_genre_id = genre_id


def clear_prebuffer():
    """Clear the pre-buffer hint (e.g. when autopilot disengages)."""
    global _prebuffer_genre_id
    _prebuffer_genre_id = None


async def start_buffer_worker():
    """Start the async background buffer loop."""
    loop = asyncio.get_event_loop()
    logger.info("Buffer worker started")

    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)

            # Library mode: skip generation and cleanup entirely
            lib_mode = await loop.run_in_executor(
                _executor, lambda: get_setting("library_mode", False)
            )
            if lib_mode:
                continue

            genre_to_fill = await loop.run_in_executor(
                _executor, _pick_genre_to_fill
            )
            if genre_to_fill:
                await _generate_one_track(loop, genre_to_fill)

            # Periodic cleanup
            await loop.run_in_executor(_executor, _maybe_cleanup)

        except Exception as e:
            logger.error("Buffer worker error: %s", e)
            await asyncio.sleep(CHECK_INTERVAL)


def _genre_buffer_counts(db, genre_id):
    """Return (unplayed, pending) counts for a genre.

    Excludes the currently playing track from the unplayed count so it
    doesn't inflate the buffer level and block generation.
    """
    current_tid = _current_track_id

    if current_tid:
        unplayed = db.execute(
            """SELECT COUNT(*) FROM tracks
               WHERE genre_id = ? AND status IN ('active', 'favorited')
               AND played_at IS NULL AND id != ?""",
            (genre_id, current_tid),
        ).fetchone()[0]
    else:
        unplayed = db.execute(
            """SELECT COUNT(*) FROM tracks
               WHERE genre_id = ? AND status IN ('active', 'favorited')
               AND played_at IS NULL""",
            (genre_id,),
        ).fetchone()[0]

    pending = db.execute(
        """SELECT COUNT(*) FROM generation_tasks
           WHERE genre_id = ? AND status IN ('pending', 'processing')""",
        (genre_id,),
    ).fetchone()[0]

    return unplayed, pending


def _pick_genre_to_fill():
    """Decide which genre to generate for next. Returns genre_id or None.

    Priority:
    1. ALL mode: check combined buffer across category, pick random variant.
    2. Current genre has 0 ready tracks (urgent — radio will stall).
    3. Prebuffer genre has 0 ready tracks AND current has >=1 ready
       (urgent — autopilot will stall on next switch).
    4. Current genre below buffer_max (normal refill).
    5. Prebuffer below PREBUFFER_TARGET (normal pre-fill).
    6. First other genre with 0 unplayed tracks and no pending tasks.
    7. None if everything is stocked.
    """
    db = get_db()
    buffer_max = get_setting("buffer_max", 5)

    # ALL mode: check buffer across all variants in the category
    if _all_mode and _current_category:
        category_genres = get_genres_by_category(_current_category)
        if category_genres:
            total_unplayed = 0
            total_pending = 0
            for g in category_genres:
                u, p = _genre_buffer_counts(db, g["id"])
                total_unplayed += u
                total_pending += p

            total = total_unplayed + total_pending
            if total < buffer_max:
                pick = _random.choice(category_genres)
                logger.info(
                    "Buffer ALL [%s]: %d unplayed + %d pending = %d (max %d), "
                    "generating for %s...",
                    _current_category, total_unplayed, total_pending, total,
                    buffer_max, pick["id"],
                )
                return pick["id"]

        # Category is stocked, fall through to background fill
        current = None
    else:
        current = _current_genre_id

    # Get current genre counts (used by multiple priority levels below)
    cur_unplayed, cur_pending = 0, 0
    if current:
        cur_unplayed, cur_pending = _genre_buffer_counts(db, current)

    # URGENT: current genre has no ready tracks — radio will stall
    if current and cur_unplayed == 0 and cur_pending == 0:
        logger.info(
            "Buffer [%s]: 0 ready, urgent fill...", current,
        )
        return current

    # PREBUFFER PRIORITY: autopilot's next genre has no ready tracks,
    # but current genre has at least 1 — spend this cycle on prebuffer
    # to prevent a stall when autopilot switches.
    if _prebuffer_genre_id and current and cur_unplayed >= 1:
        pb_unplayed, pb_pending = _genre_buffer_counts(db, _prebuffer_genre_id)
        if pb_unplayed == 0 and pb_pending == 0:
            logger.info(
                "Pre-buffer URGENT [%s]: 0 ready, current [%s] has %d — "
                "prioritizing prebuffer...",
                _prebuffer_genre_id, current, cur_unplayed,
            )
            return _prebuffer_genre_id

    # Normal refill: current genre below buffer_max
    if current:
        cur_total = cur_unplayed + cur_pending
        if cur_total < buffer_max:
            logger.info(
                "Buffer [%s]: %d unplayed + %d pending = %d (max %d), generating...",
                current, cur_unplayed, cur_pending, cur_total, buffer_max,
            )
            return current

    # Normal pre-fill: prebuffer genre below PREBUFFER_TARGET
    if _prebuffer_genre_id:
        pb_unplayed, pb_pending = _genre_buffer_counts(db, _prebuffer_genre_id)
        pb_total = pb_unplayed + pb_pending
        if pb_total < PREBUFFER_TARGET:
            logger.info(
                "Pre-buffer [%s]: %d unplayed + %d pending = %d (target %d), "
                "generating...",
                _prebuffer_genre_id, pb_unplayed, pb_pending, pb_total,
                PREBUFFER_TARGET,
            )
            return _prebuffer_genre_id

    # Background fill: any genre with 0 ready tracks.
    # Only consider genres that exist in the current config (skip stale DB entries).
    valid_ids = _get_valid_genre_ids()
    all_genres = get_all_genres()
    active_ids = set()
    if _all_mode and _current_category:
        active_ids = {g["id"] for g in get_genres_by_category(_current_category)}
    elif current:
        active_ids = {current}

    for genre_row in all_genres:
        gid = genre_row["id"]
        if gid not in valid_ids or gid in active_ids:
            continue

        unplayed, pending = _genre_buffer_counts(db, gid)
        if unplayed > 0 or pending > 0:
            continue

        logger.info("Buffer [%s]: 0 tracks ready, pre-generating...", gid)
        return gid

    return None


def _is_active_genre(genre_id):
    """Check if a genre_id is currently active or pre-buffered.

    Includes the prebuffer target so autopilot look-ahead tasks
    are not abandoned when the user hasn't switched away.
    """
    if genre_id == _prebuffer_genre_id:
        return True
    if _all_mode and _current_category:
        category_genres = get_genres_by_category(_current_category)
        return any(g["id"] == genre_id for g in category_genres)
    return genre_id == _current_genre_id


async def _generate_one_track(loop, genre_id):
    """Submit one task, poll until complete, then process the result."""
    genre = get_genre(genre_id)
    if not genre:
        return

    was_active = _is_active_genre(genre_id)

    # Step 1: Generate lyrics if needed, then submit
    task_id = await loop.run_in_executor(_executor, _submit_one, genre)
    if not task_id:
        return

    # Step 2: Poll until done
    poll_errors = 0
    while True:
        await asyncio.sleep(POLL_INTERVAL)

        # Abandon only if this was an active-genre task and user switched away.
        # Background genre tasks always run to completion.
        if was_active and not _is_active_genre(genre_id):
            logger.info("Genre changed during generation, abandoning task %s", task_id)
            _mark_task_failed(task_id)
            return

        status, result_list = await loop.run_in_executor(
            _executor, _poll_one, task_id
        )

        if status == "success" and result_list:
            await loop.run_in_executor(
                _executor, _process_completed_task, genre_id, result_list
            )
            _mark_task_done(task_id)
            logger.info("Task %s completed for genre %s", task_id, genre_id)
            return

        if status == "failed":
            _mark_task_failed(task_id)
            logger.warning("Task %s failed for genre %s", task_id, genre_id)
            return

        if status == "error":
            poll_errors += 1
            if poll_errors >= MAX_POLL_ERRORS:
                logger.error(
                    "Task %s: %d consecutive poll errors, giving up",
                    task_id, poll_errors,
                )
                _mark_task_failed(task_id)
                return
            logger.warning(
                "Task %s: poll error %d/%d, will retry...",
                task_id, poll_errors, MAX_POLL_ERRORS,
            )
            continue

        # Still processing — connection is fine, reset error counter
        poll_errors = 0
        logger.debug("Task %s still processing...", task_id)


def _submit_one(genre):
    """Submit a single generation task. Returns task_id or None.

    Checks the category's lyrics_engine config (or the genre's dynamic_lyrics
    flag as fallback) to decide whether to generate lyrics first.
    """
    from src.services.generation import submit_task

    db = get_db()
    filled_lyrics = None
    instrumental = True

    # Determine if lyrics generation is needed
    try:
        category = genre["category"]
    except (KeyError, IndexError):
        category = ""
    needs_lyrics = False
    if category:
        from src.config import get_category_config
        cat_config = get_category_config(category)
        needs_lyrics = cat_config.get("lyrics_engine", "none") != "none"
    if not needs_lyrics:
        # Fallback to per-genre flag for backward compatibility
        needs_lyrics = bool(genre["dynamic_lyrics"])

    if needs_lyrics:
        try:
            from src.services.lyrics import generate_lyrics_for_genre
            filled_lyrics = generate_lyrics_for_genre(genre, category=category)
            instrumental = False
            logger.info("Dynamic lyrics generated for %s", genre["id"])
        except Exception as e:
            logger.error("Lyrics generation failed for %s: %s — "
                         "falling back to instrumental", genre["id"], e)
            filled_lyrics = None
            instrumental = True

    task_id = submit_task(genre, filled_lyrics=filled_lyrics,
                          instrumental=instrumental)
    if not task_id:
        return None

    db.execute(
        """INSERT INTO generation_tasks (task_id, genre_id, status)
           VALUES (?, ?, 'pending')""",
        (task_id, genre["id"]),
    )
    db.commit()
    return task_id


def _poll_one(task_id):
    """Poll a single task. Returns (status, result_list)."""
    from src.services.generation import poll_result

    db = get_db()
    status, result_list = poll_result(task_id)

    if status == "processing":
        db.execute(
            "UPDATE generation_tasks SET status = 'processing' WHERE task_id = ?",
            (task_id,),
        )
        db.commit()

    return status, result_list


def _mark_task_done(task_id):
    """Mark a generation task as succeeded."""
    db = get_db()
    db.execute(
        """UPDATE generation_tasks
           SET status = 'success', completed_at = CURRENT_TIMESTAMP
           WHERE task_id = ?""",
        (task_id,),
    )
    db.commit()


def _mark_task_failed(task_id):
    """Mark a generation task as failed."""
    db = get_db()
    db.execute(
        """UPDATE generation_tasks
           SET status = 'failed', completed_at = CURRENT_TIMESTAMP
           WHERE task_id = ?""",
        (task_id,),
    )
    db.commit()


def _process_completed_task(genre_id, result_list):
    """Process a completed generation task: download, name, tag, store."""
    from src.services.generation import download_audio
    from src.services.metadata import embed_local_cover, write_id3_tags
    from src.services.waveform import compute_waveform, waveform_to_json
    from src.services.albums import assign_track_to_album, increment_album_track_count

    db = get_db()
    audio_entries = [r for r in result_list if r.get("file")]
    if not audio_entries:
        logger.warning("No audio files in generation result")
        return

    for entry in audio_entries:
        # Generate names (genre-aware)
        track_name = _generate_track_name(genre_id)
        artist_name = _generate_artist_name(genre_id)

        # Assign to album
        album = assign_track_to_album(genre_id, artist_name)

        # Build filename
        date_str = datetime.now().strftime("%m%d%Y")
        audio_format = get_setting("output_audio_format", "mp3")
        safe_name = _sanitize_filename(track_name)
        filename = f"{safe_name}-{date_str}-{genre_id}.{audio_format}"
        filepath = DOWNLOADS_DIR / filename

        # Ensure unique filename
        counter = 1
        while filepath.exists():
            filename = f"{safe_name}-{date_str}-{genre_id}-{counter}.{audio_format}"
            filepath = DOWNLOADS_DIR / filename
            counter += 1

        # Download audio
        file_path = entry["file"]
        if not download_audio(file_path, filepath):
            continue

        # Compute waveform
        waveform = compute_waveform(filepath)
        waveform_json = waveform_to_json(waveform)

        # Get duration from file
        duration = _get_audio_duration(filepath)

        # Write ID3 tags
        if audio_format == "mp3":
            write_id3_tags(
                filepath, track_name, artist_name,
                album["name"], album["track_count"] + 1,
            )
            # Embed cover art from local file
            if album.get("cover_url"):
                embed_local_cover(filepath, album["cover_url"])

        # Insert track into DB
        db.execute(
            """INSERT INTO tracks
               (title, artist, album_id, genre_id, filename, filepath, duration, waveform, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
            (
                track_name, artist_name, album["id"], genre_id,
                filename, str(filepath), duration, waveform_json,
            ),
        )
        db.commit()

        # Update album track count
        increment_album_track_count(album["id"])

        logger.info("Track '%s' by %s saved (%s)", track_name, artist_name, filename)


def _get_genre_category(genre_id):
    """Look up the category for a genre_id. Returns 'lofi' as default."""
    try:
        genre = get_genre(genre_id)
        if genre:
            return genre["category"] or "lofi"
    except Exception:
        pass
    return "lofi"


def _get_generator_info(genre_id):
    """Look up the generator type and profile for a genre from categories.yaml."""
    from src.config import get_category_config
    category = _get_genre_category(genre_id)
    cat_config = get_category_config(category)
    return cat_config.get("generator", "custom"), cat_config.get("generator_profile", ""), category


def _generate_track_name(genre_id=None):
    """Generate a track name, dispatching to the correct generator by category."""
    if genre_id:
        gen_type, profile, category = _get_generator_info(genre_id)
    else:
        gen_type, profile, category = "custom", "", "lofi"

    if gen_type == "profile" and profile:
        try:
            from src.generators.generic import generate_track_name
            return generate_track_name(category, profile)
        except Exception as e:
            logger.warning("Generic track name generation failed: %s", e)

    # Custom generator dispatch
    try:
        if category == "citypop":
            from src.generators.citypop_track_names import generate_track_names
        elif category == "synthwave":
            from src.generators.synthwave_track_names import generate_track_names
        else:
            from src.generators.track_names import generate_track_names

        result = generate_track_names(count=1)
        if result:
            return result[0]["name"]
    except Exception as e:
        logger.warning("Track name generation failed (%s): %s", category, e)

    import random
    fallback_names = [
        "Midnight Drift", "Foggy Windows", "Paper Lanterns",
        "Rooftop Rain", "Sunday Morning", "Neon Puddles",
        "Warm Static", "Late Bus Home", "Cobalt Hours",
    ]
    return random.choice(fallback_names)


def _generate_artist_name(genre_id=None):
    """Generate an artist name, dispatching to the correct generator by category."""
    if genre_id:
        gen_type, profile, category = _get_generator_info(genre_id)
    else:
        gen_type, profile, category = "custom", "", "lofi"

    if gen_type == "profile" and profile:
        try:
            from src.generators.generic import generate_artist_name
            return generate_artist_name(category, profile)
        except Exception as e:
            logger.warning("Generic artist name generation failed: %s", e)

    # Custom generator dispatch
    try:
        if category == "citypop":
            from src.generators.citypop_artist_names import generate_artist_names
        elif category == "synthwave":
            from src.generators.synthwave_artist_names import generate_artist_names
        else:
            from src.generators.artist_names import generate_artist_names

        result = generate_artist_names(count=1)
        if result:
            return result[0]["name"]
    except Exception as e:
        logger.warning("Artist name generation failed (%s): %s", category, e)

    import random
    fallback_artists = [
        "Kasumi (feat. mujin 無人)",
        "Slowtide (feat. mujin 無人)",
        "Moonsoup (feat. mujin 無人)",
    ]
    return random.choice(fallback_artists)


def _sanitize_filename(name):
    """Make a string safe for use as a filename."""
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    safe = re.sub(r'\s+', '-', safe.strip())
    safe = re.sub(r'-+', '-', safe)
    return safe[:80] or "untitled"


def _get_audio_duration(filepath):
    """Get audio duration in seconds."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(str(filepath))
        return audio.duration_seconds
    except Exception:
        try:
            from mutagen.mp3 import MP3
            audio = MP3(str(filepath))
            return audio.info.length
        except Exception:
            return None


def _maybe_cleanup():
    """Run cleanup if enough time has passed."""
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < CLEANUP_INTERVAL:
        return
    _last_cleanup = now
    run_cleanup(current_track_id=_current_track_id)
