"""Background worker for track cleanup based on age and size thresholds."""

import logging
import os
from pathlib import Path

from src.config import DOWNLOADS_DIR
from src.database import get_db, get_setting

logger = logging.getLogger(__name__)

CLEANUP_INTERVAL = 300  # 5 minutes


def run_cleanup(current_track_id=None):
    """Run a single cleanup pass. Called periodically by the buffer worker.

    Args:
        current_track_id: ID of the currently playing track (skip deletion).
    """
    if get_setting("library_mode", False):
        return

    db = get_db()
    deleted_count = 0

    deleted_count += _cleanup_disliked(db, current_track_id)
    deleted_count += _cleanup_expired(db, current_track_id)
    deleted_count += _cleanup_oversized(db, current_track_id)

    if deleted_count > 0:
        logger.info("Cleanup pass deleted %d tracks", deleted_count)


def _cleanup_disliked(db, current_track_id):
    """Delete disliked tracks (if setting enabled), skipping current track."""
    if not get_setting("delete_disliked_tracks", True):
        return 0

    query = "SELECT id, filepath FROM tracks WHERE status = 'disliked'"
    params = []
    if current_track_id:
        query += " AND id != ?"
        params.append(current_track_id)

    rows = db.execute(query, params).fetchall()
    count = 0
    for row in rows:
        _delete_track(db, row["id"], row["filepath"])
        count += 1
    return count


def _cleanup_expired(db, current_track_id):
    """Delete active tracks older than preservation_time hours."""
    hours = get_setting("preservation_time", 24)
    if hours < 0:
        return 0  # Disabled

    query = """SELECT id, filepath FROM tracks
               WHERE status = 'active'
               AND played_at IS NOT NULL
               AND created_at < datetime('now', ? || ' hours')"""
    params = [f"-{hours}"]
    if current_track_id:
        query += " AND id != ?"
        params.append(current_track_id)

    rows = db.execute(query, params).fetchall()
    count = 0
    for row in rows:
        _delete_track(db, row["id"], row["filepath"])
        count += 1
    return count


def _cleanup_oversized(db, current_track_id):
    """Delete oldest active tracks if total file size exceeds limit."""
    limit_mb = get_setting("file_size_limit_mb", 500)
    if limit_mb < 0:
        return 0  # Disabled

    total_size = _get_total_download_size_mb()
    if total_size <= limit_mb:
        return 0

    # Get active tracks ordered by oldest first
    query = "SELECT id, filepath FROM tracks WHERE status = 'active' AND played_at IS NOT NULL"
    params = []
    if current_track_id:
        query += " AND id != ?"
        params.append(current_track_id)
    query += " ORDER BY created_at ASC"

    rows = db.execute(query, params).fetchall()
    count = 0
    for row in rows:
        if _get_total_download_size_mb() <= limit_mb:
            break
        _delete_track(db, row["id"], row["filepath"])
        count += 1
    return count


def _delete_track(db, track_id, filepath):
    """Delete a track from DB and filesystem."""
    # Remove from playlists first
    db.execute("DELETE FROM playlist_tracks WHERE track_id = ?", (track_id,))
    # Delete track record
    db.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
    db.commit()

    # Delete file
    if filepath:
        path = Path(filepath)
        if path.exists():
            try:
                path.unlink()
                logger.debug("Deleted file: %s", path.name)
            except OSError as e:
                logger.warning("Failed to delete file %s: %s", path, e)


def _get_total_download_size_mb():
    """Calculate total size of all files in downloads directory in MB."""
    total = 0
    if DOWNLOADS_DIR.exists():
        for f in DOWNLOADS_DIR.iterdir():
            if f.is_file():
                total += f.stat().st_size
    return total / (1024 * 1024)
