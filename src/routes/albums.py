"""Album and artist endpoints: listing, detail, tracks by artist, artist profile."""

import logging
import re

from fastapi import APIRouter, HTTPException

from src.database import get_db
from src.models import AlbumOut
from src.routes.playlists import _track_with_album

logger = logging.getLogger(__name__)

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
    base = _strip_feat(artist_name)
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


@router.get("/artists/{artist_name}/profile")
def get_artist_profile(artist_name: str):
    """Return full artist profile: bio, albums, stats."""
    base = _strip_feat(artist_name)
    if not base:
        raise HTTPException(status_code=400, detail="Empty artist name")

    db = get_db()

    # Get track count and determine the artist's primary genre
    track_stats = db.execute(
        """SELECT genre_id, COUNT(*) as cnt FROM tracks
           WHERE TRIM(
             CASE
               WHEN INSTR(artist, ' (feat.') > 0
               THEN SUBSTR(artist, 1, INSTR(artist, ' (feat.') - 1)
               ELSE artist
             END
           ) = ?
           GROUP BY genre_id ORDER BY cnt DESC""",
        (base,),
    ).fetchall()

    track_count = sum(r["cnt"] for r in track_stats)
    genre_id = track_stats[0]["genre_id"] if track_stats else None

    # Get bio — return existing, or generate on the spot if favorited artist lacks one
    from src.services.bios import get_artist_bio, generate_artist_bio
    from src.database import get_setting
    bio = get_artist_bio(base)
    if not bio and genre_id and get_setting("artist_bios_enabled", False):
        if db.execute(
            "SELECT 1 FROM favorite_artists WHERE artist_name = ?", (base,)
        ).fetchone():
            genre = db.execute(
                "SELECT category FROM genres WHERE id = ?", (genre_id,)
            ).fetchone()
            category = genre["category"] if genre else "lofi"
            bio = generate_artist_bio(base, genre_id, category)

    # Get albums the artist appears in
    album_rows = db.execute(
        """SELECT DISTINCT a.id, a.name, a.cover_url, a.genre_id, a.track_count
           FROM albums a
           JOIN tracks t ON t.album_id = a.id
           WHERE TRIM(
             CASE
               WHEN INSTR(t.artist, ' (feat.') > 0
               THEN SUBSTR(t.artist, 1, INSTR(t.artist, ' (feat.') - 1)
               ELSE t.artist
             END
           ) = ?
           ORDER BY a.created_at DESC""",
        (base,),
    ).fetchall()

    albums = []
    for r in album_rows:
        cover = r["cover_url"]
        if cover and not cover.startswith("http"):
            cover = "/album-covers/" + cover
        albums.append({
            "id": r["id"],
            "name": r["name"],
            "cover_url": cover,
            "genre_id": r["genre_id"],
            "track_count": r["track_count"],
        })

    # Get playlists containing tracks by this artist
    playlist_rows = db.execute(
        """SELECT DISTINCT p.id, p.name
           FROM playlists p
           JOIN playlist_tracks pt ON p.id = pt.playlist_id
           JOIN tracks t ON t.id = pt.track_id
           WHERE TRIM(
             CASE
               WHEN INSTR(t.artist, ' (feat.') > 0
               THEN SUBSTR(t.artist, 1, INSTR(t.artist, ' (feat.') - 1)
               ELSE t.artist
             END
           ) = ?
           ORDER BY p.name""",
        (base,),
    ).fetchall()
    playlists = [{"id": r["id"], "name": r["name"]} for r in playlist_rows]

    # Get like count from favorite_artists
    fav_row = db.execute(
        "SELECT SUM(like_count) as total FROM favorite_artists WHERE artist_name = ?",
        (base,),
    ).fetchone()
    like_count = fav_row["total"] if fav_row and fav_row["total"] else 0

    return {
        "name": base,
        "bio": bio,
        "genre_id": genre_id,
        "albums": albums,
        "playlists": playlists,
        "track_count": track_count,
        "like_count": like_count,
    }


def _strip_feat(artist_name: str) -> str:
    """Remove (feat. ...) suffix from artist name."""
    return re.sub(r"\s*\(feat\..*?\)", "", artist_name, flags=re.IGNORECASE).strip()
