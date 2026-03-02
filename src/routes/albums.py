"""Album and artist endpoints: listing, detail, tracks by artist."""

import re

from fastapi import APIRouter, HTTPException

from src.database import get_db
from src.models import AlbumOut
from src.routes.playlists import _track_with_album

router = APIRouter(tags=["albums"])


@router.get("/albums", response_model=list[AlbumOut])
def list_albums(genre_id: str | None = None):
    """Return all albums, optionally filtered by genre."""
    db = get_db()
    if genre_id:
        rows = db.execute(
            "SELECT * FROM albums WHERE genre_id = ? ORDER BY created_at DESC",
            (genre_id,),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM albums ORDER BY created_at DESC"
        ).fetchall()

    return [
        AlbumOut(
            id=r["id"],
            name=r["name"],
            artist=r["artist"],
            cover_url=r["cover_url"],
            genre_id=r["genre_id"],
            track_count=r["track_count"],
            is_open=bool(r["is_open"]),
        )
        for r in rows
    ]


@router.get("/albums/{album_id}", response_model=AlbumOut)
def get_album(album_id: int):
    """Get a single album by ID."""
    db = get_db()
    r = db.execute("SELECT * FROM albums WHERE id = ?", (album_id,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Album not found")

    return AlbumOut(
        id=r["id"],
        name=r["name"],
        artist=r["artist"],
        cover_url=r["cover_url"],
        genre_id=r["genre_id"],
        track_count=r["track_count"],
        is_open=bool(r["is_open"]),
    )


@router.get("/albums/{album_id}/tracks")
def get_album_tracks(album_id: int):
    """Return all tracks in an album with album info."""
    db = get_db()
    rows = db.execute(
        """SELECT t.*, a.name as album_name, a.cover_url as album_cover_url
           FROM tracks t
           LEFT JOIN albums a ON t.album_id = a.id
           WHERE t.album_id = ?
           ORDER BY t.created_at""",
        (album_id,),
    ).fetchall()
    if not rows:
        album = db.execute(
            "SELECT id FROM albums WHERE id = ?", (album_id,)
        ).fetchone()
        if not album:
            raise HTTPException(status_code=404, detail="Album not found")
    return [_track_with_album(r) for r in rows]


@router.get("/artists/{artist_name}/tracks")
def get_artist_tracks(artist_name: str):
    """Return all tracks by a base artist (stripped of feat. suffixes)."""
    base = re.sub(r"\s*\(feat\..*?\)", "", artist_name, flags=re.IGNORECASE).strip()
    if not base:
        raise HTTPException(status_code=400, detail="Empty artist name")

    db = get_db()
    rows = db.execute(
        """SELECT t.*, a.name as album_name, a.cover_url as album_cover_url
           FROM tracks t
           LEFT JOIN albums a ON t.album_id = a.id
           WHERE TRIM(
             CASE
               WHEN INSTR(t.artist, ' (feat.') > 0
               THEN SUBSTR(t.artist, 1, INSTR(t.artist, ' (feat.') - 1)
               ELSE t.artist
             END
           ) = ?
           ORDER BY t.created_at DESC""",
        (base,),
    ).fetchall()
    return [_track_with_album(r) for r in rows]
