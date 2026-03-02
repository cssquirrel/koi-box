"""One-time migration script to fix legacy tracks.

Targets all tracks that are favorited or belong to a playlist.
Two passes:
  1. Fix broken album cover references (missing files, old URLs).
  2. Re-generate metadata for synthwave/citypop tracks that were
     named by the old lofi generator.

Usage:
    python -m src.services.migrate_tracks           # dry-run (default)
    python -m src.services.migrate_tracks --apply    # actually apply changes
"""

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from src.config import ALBUM_COVERS_DIR, DOWNLOADS_DIR
from src.database import get_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_target_track_ids(db):
    """Return set of track IDs that are favorited or in any playlist."""
    favorited = db.execute(
        "SELECT id FROM tracks WHERE status = 'favorited'"
    ).fetchall()
    in_playlist = db.execute(
        "SELECT DISTINCT track_id FROM playlist_tracks"
    ).fetchall()
    ids = {r["id"] for r in favorited}
    ids.update(r["track_id"] for r in in_playlist)
    return ids


def _get_genre_category(db, genre_id):
    """Look up category for a genre_id."""
    row = db.execute(
        "SELECT category FROM genres WHERE id = ?", (genre_id,)
    ).fetchone()
    return row["category"] if row else "lofi"


def _cover_exists(cover_url):
    """Check whether an album cover_url points to a valid local file."""
    if not cover_url:
        return False
    # Old-style HTTP URLs are definitely broken
    if cover_url.startswith("http://") or cover_url.startswith("https://"):
        return False
    cover_path = ALBUM_COVERS_DIR / cover_url
    return cover_path.is_file()


def _pick_cover_for_category(category):
    """Pick a random local cover image for a category."""
    import random
    cover_dir = ALBUM_COVERS_DIR / category
    if not cover_dir.is_dir():
        return None
    images = list(cover_dir.glob("*.jpg")) + list(cover_dir.glob("*.png"))
    if not images:
        return None
    pick = random.choice(images)
    return f"{category}/{pick.name}"


def _generate_track_name(category):
    """Generate a track name using the correct category generator."""
    if category == "citypop":
        from src.generators.citypop_track_names import generate_track_names
    elif category == "synthwave":
        from src.generators.synthwave_track_names import generate_track_names
    else:
        from src.generators.track_names import generate_track_names

    result = generate_track_names(count=1)
    return result[0]["name"] if result else "Untitled"


def _generate_artist_name(category):
    """Generate an artist name using the correct category generator."""
    if category == "citypop":
        from src.generators.citypop_artist_names import generate_artist_names
    elif category == "synthwave":
        from src.generators.synthwave_artist_names import generate_artist_names
    else:
        from src.generators.artist_names import generate_artist_names

    result = generate_artist_names(count=1)
    return result[0]["name"] if result else "Unknown Artist"


def _generate_album_name(category):
    """Generate an album name using the correct category generator."""
    from src.generators.album_names import generate_album_name
    return generate_album_name(category)


def _sanitize_filename(name):
    """Make a string safe for use as a filename."""
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    safe = re.sub(r'\s+', '-', safe.strip())
    safe = re.sub(r'-+', '-', safe)
    return safe[:80] or "untitled"


# ---------------------------------------------------------------------------
# Pass 1: Fix broken album covers
# ---------------------------------------------------------------------------

def fix_covers(db, target_ids, dry_run=True):
    """Fix broken album cover references for target tracks."""
    if not target_ids:
        return 0

    placeholders = ",".join("?" * len(target_ids))
    albums = db.execute(
        f"""SELECT DISTINCT a.id, a.cover_url, a.genre_id
            FROM albums a
            JOIN tracks t ON t.album_id = a.id
            WHERE t.id IN ({placeholders})""",
        list(target_ids),
    ).fetchall()

    fixed = 0
    for album in albums:
        if _cover_exists(album["cover_url"]):
            continue

        category = _get_genre_category(db, album["genre_id"])
        new_cover = _pick_cover_for_category(category)
        if not new_cover:
            print(f"  [WARN] No covers available for category '{category}', "
                  f"album #{album['id']}")
            continue

        old = album["cover_url"] or "(none)"
        print(f"  Album #{album['id']}: cover {old} -> {new_cover}")

        if not dry_run:
            db.execute(
                "UPDATE albums SET cover_url = ? WHERE id = ?",
                (new_cover, album["id"]),
            )
            # Re-embed cover in all tracks belonging to this album
            # that are in our target set
            tracks = db.execute(
                f"""SELECT filepath FROM tracks
                    WHERE album_id = ? AND id IN ({placeholders})""",
                [album["id"]] + list(target_ids),
            ).fetchall()
            from src.services.metadata import embed_local_cover
            for t in tracks:
                fp = Path(t["filepath"])
                if fp.exists() and fp.suffix.lower() == ".mp3":
                    embed_local_cover(str(fp), new_cover)

        fixed += 1

    if not dry_run and fixed > 0:
        db.commit()

    return fixed


# ---------------------------------------------------------------------------
# Pass 2: Re-generate metadata for synthwave/citypop tracks
# ---------------------------------------------------------------------------

def fix_metadata(db, target_ids, dry_run=True):
    """Re-generate names for synthwave/citypop tracks (all assumed lofi-named)."""
    if not target_ids:
        return 0

    placeholders = ",".join("?" * len(target_ids))
    tracks = db.execute(
        f"""SELECT t.id, t.title, t.artist, t.genre_id, t.filename,
                   t.filepath, t.album_id,
                   a.name AS album_name, a.cover_url
            FROM tracks t
            LEFT JOIN albums a ON t.album_id = a.id
            WHERE t.id IN ({placeholders})""",
        list(target_ids),
    ).fetchall()

    updated = 0
    album_renames = {}  # album_id -> new_name (avoid renaming same album twice)

    for track in tracks:
        category = _get_genre_category(db, track["genre_id"])

        # Only re-generate for synthwave and citypop
        if category not in ("synthwave", "citypop"):
            continue

        old_title = track["title"]
        old_artist = track["artist"]
        old_filename = track["filename"]
        old_filepath = Path(track["filepath"])

        # Generate new names
        new_title = _generate_track_name(category)
        new_artist = _generate_artist_name(category)

        # Build new filename preserving the date-genre convention
        # Original pattern: {safe_name}-{date}-{genre_id}.{ext}
        # Extract date and genre_id from old filename
        match = re.search(r'-(\d{8})-(.+?)(?:-\d+)?\.(\w+)$', old_filename)
        if match:
            date_str = match.group(1)
            genre_id = match.group(2)
            ext = match.group(3)
        else:
            # Fallback: use today's date and track's genre_id
            date_str = datetime.now().strftime("%m%d%Y")
            genre_id = track["genre_id"]
            ext = old_filepath.suffix.lstrip(".") if old_filepath.suffix else "mp3"

        safe_name = _sanitize_filename(new_title)
        new_filename = f"{safe_name}-{date_str}-{genre_id}.{ext}"
        new_filepath = DOWNLOADS_DIR / new_filename

        # Ensure unique
        counter = 1
        while new_filepath.exists() and new_filepath != old_filepath:
            new_filename = f"{safe_name}-{date_str}-{genre_id}-{counter}.{ext}"
            new_filepath = DOWNLOADS_DIR / new_filename
            counter += 1

        # Album rename (once per album)
        album_id = track["album_id"]
        new_album_name = track["album_name"]
        if album_id and album_id not in album_renames:
            new_album_name = _generate_album_name(category)
            album_renames[album_id] = new_album_name
        elif album_id:
            new_album_name = album_renames[album_id]

        print(f"  Track #{track['id']} ({category}):")
        print(f"    title:  '{old_title}' -> '{new_title}'")
        print(f"    artist: '{old_artist}' -> '{new_artist}'")
        print(f"    file:   {old_filename} -> {new_filename}")
        if album_id and new_album_name != track["album_name"]:
            print(f"    album:  '{track['album_name']}' -> '{new_album_name}'")

        if not dry_run:
            # Rename physical file
            if old_filepath.exists():
                old_filepath.rename(new_filepath)
            else:
                print(f"    [WARN] File not found: {old_filepath}")

            # Update DB
            db.execute(
                """UPDATE tracks
                   SET title = ?, artist = ?, filename = ?, filepath = ?
                   WHERE id = ?""",
                (new_title, new_artist, new_filename, str(new_filepath),
                 track["id"]),
            )

            # Update album name
            if album_id and album_id in album_renames:
                db.execute(
                    "UPDATE albums SET name = ? WHERE id = ?",
                    (album_renames[album_id], album_id),
                )

            # Rewrite ID3 tags + re-embed cover
            actual_path = new_filepath if new_filepath.exists() else old_filepath
            if actual_path.exists() and actual_path.suffix.lower() == ".mp3":
                from src.services.metadata import embed_local_cover, write_id3_tags
                write_id3_tags(
                    str(actual_path), new_title, new_artist,
                    new_album_name or "Unknown Album",
                )
                cover = track["cover_url"]
                if cover and _cover_exists(cover):
                    embed_local_cover(str(actual_path), cover)

        updated += 1

    if not dry_run and updated > 0:
        db.commit()

    return updated


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_migration(dry_run=True):
    """Run the full migration."""
    db = get_db()
    target_ids = _get_target_track_ids(db)

    mode = "DRY RUN" if dry_run else "APPLYING"
    print(f"\n=== Track Migration ({mode}) ===")
    print(f"Target tracks (favorited or in playlist): {len(target_ids)}")

    if not target_ids:
        print("Nothing to migrate.")
        return

    # Pass 1
    print(f"\n--- Pass 1: Fix broken album covers ---")
    cover_fixes = fix_covers(db, target_ids, dry_run)
    print(f"Covers fixed: {cover_fixes}")

    # Pass 2
    print(f"\n--- Pass 2: Re-generate synthwave/citypop metadata ---")
    meta_fixes = fix_metadata(db, target_ids, dry_run)
    print(f"Tracks re-named: {meta_fixes}")

    print(f"\n=== Migration complete ===")
    if dry_run and (cover_fixes > 0 or meta_fixes > 0):
        print("Run with --apply to commit these changes.")


if __name__ == "__main__":
    # Force UTF-8 output on Windows consoles
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(level=logging.INFO)
    apply = "--apply" in sys.argv
    run_migration(dry_run=not apply)
