"""Track endpoints: CRUD, favorites, dislikes, history."""

import json
import logging
import re

from fastapi import APIRouter, HTTPException

from src.database import get_db
from src.models import TrackOut, TrackStatusRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["tracks"])


@router.get("/tracks", response_model=list[TrackOut])
def list_tracks(genre_id: str | None = None, status: str | None = None, limit: int = 50):
    """List tracks with optional genre and status filters."""
    db = get_db()
    query = "SELECT * FROM tracks WHERE 1=1"
    params = []

    if genre_id:
        query += " AND genre_id = ?"
        params.append(genre_id)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = db.execute(query, params).fetchall()
    return [_row_to_track(db, r) for r in rows]


@router.get("/tracks/history/recent", response_model=list[TrackOut])
def get_history(limit: int = 20):
    """Return recently played tracks."""
    db = get_db()
    rows = db.execute(
        """SELECT * FROM tracks
           WHERE played_at IS NOT NULL
           ORDER BY played_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [_row_to_track(db, r) for r in rows]


@router.get("/tracks/{track_id}", response_model=TrackOut)
def get_track(track_id: int):
    """Get a single track by ID."""
    db = get_db()
    row = db.execute("SELECT * FROM tracks WHERE id = ?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Track not found")
    return _row_to_track(db, row)


@router.patch("/tracks/{track_id}/status")
def update_track_status(track_id: int, req: TrackStatusRequest):
    """Update track status (active, favorited, disliked)."""
    if req.status not in ("active", "favorited", "disliked"):
        raise HTTPException(status_code=400, detail="Invalid status")

    db = get_db()
    track = db.execute(
        "SELECT id, artist, genre_id, album_id FROM tracks WHERE id = ?",
        (track_id,),
    ).fetchone()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    db.execute("UPDATE tracks SET status = ? WHERE id = ?", (req.status, track_id))
    db.commit()

    if req.status == "favorited":
        _on_track_favorited(db, track)

    return {"ok": True, "track_id": track_id, "status": req.status}


def _strip_feat(artist: str) -> str:
    """Remove (feat. ...) suffix from artist name."""
    return re.sub(r"\s*\(feat\..*?\)", "", artist, flags=re.IGNORECASE).strip()


def _on_track_favorited(db, track):
    """Handle side effects when a track is favorited: artist pool + album claim."""
    base_artist = _strip_feat(track["artist"])
    genre_id = track["genre_id"]
    album_id = track["album_id"]

    # Upsert into favorite_artists pool
    db.execute(
        """INSERT INTO favorite_artists (artist_name, genre_id, like_count)
           VALUES (?, ?, 1)
           ON CONFLICT(artist_name, genre_id)
           DO UPDATE SET like_count = like_count + 1""",
        (base_artist, genre_id),
    )
    db.commit()
    logger.info("Favorite artist pool: %s +1 for %s", base_artist, genre_id)

    # Claim album ownership if unclaimed
    if not album_id:
        return

    album = db.execute(
        "SELECT id, owner_artist, genre_id FROM albums WHERE id = ?",
        (album_id,),
    ).fetchone()
    if not album:
        return

    if album["owner_artist"] == "":
        _claim_album(db, album, base_artist)


def _claim_album(db, album, owner_artist):
    """Set the album's owner and reassign other artists' unfavorited tracks."""
    album_id = album["id"]
    genre_id = album["genre_id"]

    db.execute(
        "UPDATE albums SET owner_artist = ? WHERE id = ?",
        (owner_artist, album_id),
    )
    db.commit()
    logger.info("Album %d claimed by %s", album_id, owner_artist)

    # Find unfavorited tracks by OTHER artists in this album
    other_tracks = db.execute(
        """SELECT id, artist FROM tracks
           WHERE album_id = ? AND status != 'favorited'""",
        (album_id,),
    ).fetchall()

    from src.services.albums import assign_track_to_album, increment_album_track_count

    moved = 0
    for t in other_tracks:
        t_base = _strip_feat(t["artist"])
        if t_base == owner_artist:
            continue

        # Assign to a different album
        new_album = assign_track_to_album(genre_id, t_base)
        if new_album["id"] == album_id:
            continue  # couldn't find another album, skip

        db.execute(
            "UPDATE tracks SET album_id = ? WHERE id = ?",
            (new_album["id"], t["id"]),
        )
        increment_album_track_count(new_album["id"])
        moved += 1

    if moved:
        # Update original album's track count
        actual = db.execute(
            "SELECT COUNT(*) FROM tracks WHERE album_id = ?", (album_id,)
        ).fetchone()[0]
        db.execute(
            "UPDATE albums SET track_count = ? WHERE id = ?",
            (actual, album_id),
        )
        db.commit()
        logger.info("Moved %d tracks out of album %d", moved, album_id)


def _row_to_track(db, row) -> dict:
    """Convert a track DB row to TrackOut dict."""
    album_name = None
    album_cover = None
    if row["album_id"]:
        album = db.execute(
            "SELECT name, cover_url FROM albums WHERE id = ?",
            (row["album_id"],),
        ).fetchone()
        if album:
            album_name = album["name"]
            cover = album["cover_url"]
            if cover and not cover.startswith("http"):
                album_cover = "/album-covers/" + cover
            else:
                album_cover = cover

    waveform = None
    if row["waveform"]:
        waveform = json.loads(row["waveform"])

    return {
        "id": row["id"],
        "title": row["title"],
        "artist": row["artist"],
        "album_id": row["album_id"],
        "album_name": album_name,
        "album_cover_url": album_cover,
        "genre_id": row["genre_id"],
        "filename": row["filename"],
        "duration": row["duration"],
        "waveform": waveform,
        "status": row["status"],
        "created_at": row["created_at"],
        "played_at": row["played_at"],
    }
