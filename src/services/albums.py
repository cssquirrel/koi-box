"""Album creation and interleaved track assignment."""

import logging
import random

from src.config import ALBUM_COVERS_DIR
from src.database import get_db

logger = logging.getLogger(__name__)

TARGET_COUNT_MIN = 4
TARGET_COUNT_MAX = 8
OPEN_ALBUMS_PER_GENRE = 3


def assign_track_to_album(genre_id, artist_name):
    """Assign a track to an open album for the given genre.

    Returns the album row dict, creating new albums as needed.
    """
    db = get_db()
    album = _pick_open_album(db, genre_id, artist_name)
    return album


def _pick_open_album(db, genre_id, artist_name):
    """Pick a random open album for the genre, creating if needed."""
    open_albums = db.execute(
        "SELECT * FROM albums WHERE genre_id = ? AND is_open = 1",
        (genre_id,),
    ).fetchall()

    # Ensure we have enough open albums
    while len(open_albums) < OPEN_ALBUMS_PER_GENRE:
        new_album = _create_album(db, genre_id, artist_name)
        open_albums.append(new_album)

    # Pick one at random
    album = random.choice(open_albums)
    return dict(album)


def increment_album_track_count(album_id):
    """Increment an album's track count and close it if target reached."""
    db = get_db()
    db.execute(
        "UPDATE albums SET track_count = track_count + 1 WHERE id = ?",
        (album_id,),
    )
    db.commit()

    album = db.execute("SELECT * FROM albums WHERE id = ?", (album_id,)).fetchone()
    if album and album["track_count"] >= album["target_count"]:
        db.execute("UPDATE albums SET is_open = 0 WHERE id = ?", (album_id,))
        db.commit()
        logger.info("Album '%s' closed at %d tracks", album["name"], album["track_count"])


def _create_album(db, genre_id, artist_name):
    """Create a new open album for a genre."""
    album_name = _generate_album_name(genre_id)
    cover_url = _pick_cover_path(genre_id)
    target = random.randint(TARGET_COUNT_MIN, TARGET_COUNT_MAX)

    cursor = db.execute(
        """INSERT INTO albums (name, artist, cover_url, genre_id, target_count, track_count, is_open)
           VALUES (?, ?, ?, ?, ?, 0, 1)""",
        (album_name, artist_name, cover_url, genre_id, target),
    )
    db.commit()

    album = db.execute("SELECT * FROM albums WHERE id = ?", (cursor.lastrowid,)).fetchone()
    logger.info("Created album '%s' for genre %s (target=%d)", album_name, genre_id, target)
    return album


def _get_genre_category(genre_id):
    """Look up the category for a genre_id. Returns 'lofi' as default."""
    try:
        db = get_db()
        genre = db.execute(
            "SELECT category FROM genres WHERE id = ?", (genre_id,)
        ).fetchone()
        if genre:
            return genre["category"] or "lofi"
    except Exception:
        pass
    return "lofi"


def _generate_album_name(genre_id=None):
    """Generate an album name appropriate for the genre's category."""
    category = _get_genre_category(genre_id) if genre_id else "lofi"

    # Check for profile-based generator
    from src.config import get_category_config
    cat_config = get_category_config(category)
    gen_type = cat_config.get("generator", "custom")
    profile = cat_config.get("generator_profile", "")

    if gen_type == "profile" and profile:
        try:
            from src.generators.generic import generate_album_name
            return generate_album_name(category, profile)
        except Exception as e:
            logger.warning("Generic album name generation failed: %s", e)

    # Custom generator dispatch
    try:
        from src.generators.album_names import generate_album_name
        return generate_album_name(category)
    except Exception:
        pass

    # Fallback: simple album name patterns
    prefixes = [
        "Late Night", "Early Morning", "Afternoon", "Midnight",
        "Sunday", "Golden", "Quiet", "Soft", "Warm", "Distant",
        "Fading", "Gentle", "Slow", "Last", "First",
    ]
    suffixes = [
        "Sessions", "Tapes", "Letters", "Memories", "Dreams",
        "Hours", "Moments", "Pages", "Sketches", "Waves",
        "Echoes", "Fragments", "Notes", "Drifts", "Horizons",
    ]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"


def _pick_cover_path(genre_id):
    """Pick a random local cover image for the genre's category.

    Returns a relative path like 'lofi/lofi-0042.jpg', or None if
    no images are found.
    """
    db = get_db()
    row = db.execute(
        "SELECT album_cover_directory FROM genres WHERE id = ?", (genre_id,)
    ).fetchone()
    directory = row["album_cover_directory"] if row else ""

    if not directory:
        # Fallback to category name
        cat_row = db.execute(
            "SELECT category FROM genres WHERE id = ?", (genre_id,)
        ).fetchone()
        directory = cat_row["category"] if cat_row else "lofi"

    cover_dir = ALBUM_COVERS_DIR / directory
    if not cover_dir.is_dir():
        logger.warning("Album cover directory not found: %s", cover_dir)
        return None

    images = list(cover_dir.glob("*.jpg")) + list(cover_dir.glob("*.png"))
    if not images:
        logger.warning("No cover images in %s", cover_dir)
        return None

    pick = random.choice(images)
    return f"{directory}/{pick.name}"
