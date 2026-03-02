"""Track endpoints: CRUD, favorites, dislikes, history."""

import json

from fastapi import APIRouter, HTTPException

from src.database import get_db
from src.models import TrackOut, TrackStatusRequest

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
    row = db.execute("SELECT id FROM tracks WHERE id = ?", (track_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Track not found")

    db.execute("UPDATE tracks SET status = ? WHERE id = ?", (req.status, track_id))
    db.commit()
    return {"ok": True, "track_id": track_id, "status": req.status}


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
