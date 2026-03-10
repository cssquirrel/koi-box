"""Playlist endpoints: CRUD, add/remove tracks, favorites."""

import json
import logging

from fastapi import APIRouter, HTTPException

from src.database import get_db
from src.models import PlaylistAddTrackRequest, PlaylistCreateRequest, PlaylistOut
from src.routes.tracks import _on_track_favorited

logger = logging.getLogger(__name__)

router = APIRouter(tags=["playlists"])


@router.get("/playlists", response_model=list[PlaylistOut])
def list_playlists():
    """Return all playlists with track counts."""
    db = get_db()
    rows = db.execute(
        """SELECT p.*, COUNT(pt.track_id) as track_count
           FROM playlists p
           LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
           GROUP BY p.id
           ORDER BY p.created_at DESC"""
    ).fetchall()
    return [
        PlaylistOut(
            id=r["id"],
            name=r["name"],
            track_count=r["track_count"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/playlists", response_model=PlaylistOut)
def create_playlist(req: PlaylistCreateRequest):
    """Create a new playlist."""
    db = get_db()
    cursor = db.execute("INSERT INTO playlists (name) VALUES (?)", (req.name,))
    db.commit()
    return PlaylistOut(
        id=cursor.lastrowid,
        name=req.name,
        track_count=0,
        created_at=None,
    )


@router.get("/playlists/favorites/tracks")
def get_favorites_tracks():
    """Return all favorited tracks as a virtual favorites playlist."""
    db = get_db()
    rows = db.execute(
        """SELECT t.*, a.name as album_name, a.cover_url as album_cover_url
           FROM tracks t
           LEFT JOIN albums a ON t.album_id = a.id
           WHERE t.status = 'favorited'
           ORDER BY t.favorited_at DESC"""
    ).fetchall()
    return [_track_with_album(r) for r in rows]


@router.delete("/playlists/{playlist_id}")
def delete_playlist(playlist_id: int):
    """Delete a playlist and its track associations."""
    db = get_db()
    row = db.execute("SELECT id FROM playlists WHERE id = ?", (playlist_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Playlist not found")

    db.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))
    db.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
    db.commit()
    return {"ok": True}


@router.get("/playlists/{playlist_id}/tracks")
def get_playlist_tracks(playlist_id: int):
    """Return all tracks in a playlist, ordered by position."""
    db = get_db()
    rows = db.execute(
        """SELECT t.*, pt.position, a.name as album_name, a.cover_url as album_cover_url
           FROM tracks t
           JOIN playlist_tracks pt ON t.id = pt.track_id
           LEFT JOIN albums a ON t.album_id = a.id
           WHERE pt.playlist_id = ?
           ORDER BY pt.position""",
        (playlist_id,),
    ).fetchall()
    result = []
    for r in rows:
        d = _track_with_album(r)
        d["position"] = r["position"]
        result.append(d)
    return result


@router.post("/playlists/{playlist_id}/tracks")
def add_track_to_playlist(playlist_id: int, req: PlaylistAddTrackRequest):
    """Add a track to a playlist."""
    db = get_db()

    existing = db.execute(
        "SELECT 1 FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
        (playlist_id, req.track_id),
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Track already in playlist")

    max_pos = db.execute(
        "SELECT COALESCE(MAX(position), -1) FROM playlist_tracks WHERE playlist_id = ?",
        (playlist_id,),
    ).fetchone()[0]

    db.execute(
        "INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)",
        (playlist_id, req.track_id, max_pos + 1),
    )

    # Auto-favorite the track when added to a playlist
    track = db.execute(
        "SELECT id, artist, genre_id, album_id, status FROM tracks WHERE id = ?",
        (req.track_id,),
    ).fetchone()
    if track and track["status"] != "favorited":
        db.execute(
            "UPDATE tracks SET status = 'favorited', favorited_at = CURRENT_TIMESTAMP WHERE id = ?",
            (req.track_id,),
        )
        db.commit()
        _on_track_favorited(db, track)
        logger.info("Auto-favorited track %d on playlist add", req.track_id)
    else:
        db.commit()

    return {"ok": True}


@router.delete("/playlists/{playlist_id}/tracks/{track_id}")
def remove_track_from_playlist(playlist_id: int, track_id: int):
    """Remove a track from a playlist."""
    db = get_db()
    db.execute(
        "DELETE FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?",
        (playlist_id, track_id),
    )
    db.commit()
    return {"ok": True}


def _track_with_album(row, db=None):
    """Convert a track row with joined album info to a dict."""
    if db is None:
        db = get_db()

    waveform = None
    if row["waveform"]:
        waveform = json.loads(row["waveform"])

    cover = row["album_cover_url"]
    if cover and not cover.startswith("http"):
        cover = "/album-covers/" + cover

    in_playlist = bool(db.execute(
        "SELECT 1 FROM playlist_tracks WHERE track_id = ? LIMIT 1",
        (row["id"],),
    ).fetchone())

    return {
        "id": row["id"],
        "title": row["title"],
        "artist": row["artist"],
        "album_id": row["album_id"],
        "album_name": row["album_name"],
        "album_cover_url": cover,
        "genre_id": row["genre_id"],
        "filename": row["filename"],
        "duration": row["duration"],
        "waveform": waveform,
        "status": row["status"],
        "created_at": row["created_at"],
        "in_playlist": in_playlist,
    }
