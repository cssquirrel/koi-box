"""Radio mode endpoints: now-playing, genre switch, skip, queue status."""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

from src.database import get_all_genres, get_db, get_genres_by_category, get_setting
from src.models import GenreCreateRequest, GenreOut, GenreSwitchRequest, GenreUpdateRequest, NowPlayingOut
from src.services.buffer import (
    clear_prebuffer,
    set_current_category,
    set_current_genre,
    set_current_track_id,
    set_prebuffer_genre,
)
from src.services.generation import check_health

router = APIRouter(tags=["radio"])

# In-memory radio state
_radio_state = {
    "genre_id": None,
    "category": None,
    "all_mode": False,
    "current_track_id": None,
    "is_playing": False,
    "position": 0.0,
}


@router.get("/radio/now-playing", response_model=NowPlayingOut)
def get_now_playing():
    """Return current radio state and now-playing track."""
    db = get_db()
    track = None
    queue_size = 0

    if _radio_state["current_track_id"]:
        row = db.execute(
            "SELECT * FROM tracks WHERE id = ?",
            (_radio_state["current_track_id"],),
        ).fetchone()
        if row:
            track = _track_row_to_dict(db, row)

    lib_mode = bool(get_setting("library_mode", False))
    genre_ids = _active_genre_ids()
    if genre_ids:
        placeholders = ",".join("?" * len(genre_ids))
        if lib_mode:
            queue_size = db.execute(
                f"""SELECT COUNT(*) FROM tracks
                    WHERE genre_id IN ({placeholders})
                    AND status IN ('active', 'favorited')""",
                genre_ids,
            ).fetchone()[0]
        else:
            queue_size = db.execute(
                f"""SELECT COUNT(*) FROM tracks
                    WHERE genre_id IN ({placeholders})
                    AND status IN ('active', 'favorited')
                    AND played_at IS NULL""",
                genre_ids,
            ).fetchone()[0]

    healthy = check_health()
    signal = "strong" if healthy else "offline"

    return NowPlayingOut(
        track=track,
        genre_id=_radio_state["genre_id"] or "",
        is_playing=_radio_state["is_playing"],
        position=_radio_state["position"],
        queue_size=queue_size,
        signal_status=signal,
        library_mode=lib_mode,
    )


@router.post("/radio/switch-genre")
def switch_genre(req: GenreSwitchRequest):
    """Switch the radio to a different genre or ALL mode.

    For ALL mode: genre_id="all", category="lofi" (etc.)
    For specific variant: genre_id="rainy-day" (category optional)
    """
    # Mark the outgoing track as played so it doesn't re-enter the queue
    db = get_db()
    outgoing_id = _radio_state["current_track_id"]
    if outgoing_id:
        db.execute(
            "UPDATE tracks SET played_at = CURRENT_TIMESTAMP WHERE id = ?",
            (outgoing_id,),
        )
        db.commit()

    _radio_state["current_track_id"] = None
    _radio_state["is_playing"] = False
    _radio_state["position"] = 0.0
    set_current_track_id(None)

    if req.genre_id == "all" and req.category:
        _radio_state["genre_id"] = None
        _radio_state["category"] = req.category
        _radio_state["all_mode"] = True
        set_current_category(req.category, all_mode=True)
        return {"ok": True, "genre_id": "all", "category": req.category}

    _radio_state["genre_id"] = req.genre_id
    _radio_state["category"] = req.category
    _radio_state["all_mode"] = False
    set_current_genre(req.genre_id)
    return {"ok": True, "genre_id": req.genre_id}


@router.post("/radio/prebuffer")
def prebuffer(req: GenreSwitchRequest):
    """Hint the buffer worker to pre-fill tracks for an upcoming genre.

    Called by autopilot to look ahead at the next variant it plans to
    switch to, so tracks are ready when the switch happens.
    """
    if req.genre_id:
        set_prebuffer_genre(req.genre_id)
    else:
        clear_prebuffer()
    return {"ok": True}


@router.post("/radio/play")
def play():
    """Start or resume playback."""
    _radio_state["is_playing"] = True
    return {"ok": True}


@router.post("/radio/pause")
def pause():
    """Pause playback."""
    _radio_state["is_playing"] = False
    return {"ok": True}


@router.post("/radio/skip")
def skip():
    """Skip to the next track in the queue.

    Marks the OUTGOING (current) track as played, then finds the next
    unplayed track. In ALL mode, pulls from any variant in the category.
    """
    db = get_db()
    genre_ids = _active_genre_ids()
    if not genre_ids:
        return {"ok": False, "error": "No genre selected"}

    # Mark outgoing track as played
    outgoing_id = _radio_state["current_track_id"]
    if outgoing_id:
        db.execute(
            "UPDATE tracks SET played_at = CURRENT_TIMESTAMP WHERE id = ?",
            (outgoing_id,),
        )

    # Find next track
    placeholders = ",".join("?" * len(genre_ids))
    if get_setting("library_mode", False):
        next_track = _pick_random_library_track(db, genre_ids, outgoing_id)
    else:
        next_track = db.execute(
            f"""SELECT * FROM tracks
                WHERE genre_id IN ({placeholders})
                AND status IN ('active', 'favorited')
                AND played_at IS NULL
                ORDER BY created_at ASC LIMIT 1""",
            genre_ids,
        ).fetchone()

    if next_track:
        _radio_state["current_track_id"] = next_track["id"]
        _radio_state["position"] = 0.0
        _radio_state["is_playing"] = True
        set_current_track_id(next_track["id"])
        db.commit()
        return {"ok": True, "track": _track_row_to_dict(db, next_track)}

    db.commit()
    return {"ok": False, "error": "No tracks in queue"}


@router.post("/radio/navigate/{track_id}")
def navigate_to_track(track_id: int):
    """Navigate to a specific track (skip back or queue click).

    Does NOT mark the outgoing track as played — only skip() consumes
    tracks.  Clears played_at on the target so it becomes the active
    current track and won't be skipped by future skip() calls.
    """
    db = get_db()

    # Verify target track exists
    target = db.execute(
        "SELECT * FROM tracks WHERE id = ?", (track_id,)
    ).fetchone()
    if not target:
        return {"ok": False, "error": "Track not found"}

    # Clear played_at on the target so it won't be skipped later
    db.execute(
        "UPDATE tracks SET played_at = NULL WHERE id = ?",
        (track_id,),
    )

    _radio_state["current_track_id"] = track_id
    _radio_state["position"] = 0.0
    _radio_state["is_playing"] = True
    set_current_track_id(track_id)
    db.commit()

    return {"ok": True, "track": _track_row_to_dict(db, target)}


@router.get("/radio/queue")
def get_radio_queue():
    """Return upcoming tracks and generating task count for queue strip."""
    db = get_db()
    genre_ids = _active_genre_ids()
    if not genre_ids:
        return {"upcoming": [], "generating": 0}

    lib_mode = get_setting("library_mode", False)
    placeholders = ",".join("?" * len(genre_ids))

    if lib_mode:
        upcoming = db.execute(
            f"""SELECT * FROM tracks
                WHERE genre_id IN ({placeholders})
                AND status IN ('active', 'favorited')
                ORDER BY RANDOM() LIMIT 5""",
            genre_ids,
        ).fetchall()
        generating = 0
    else:
        upcoming = db.execute(
            f"""SELECT * FROM tracks
                WHERE genre_id IN ({placeholders})
                AND status IN ('active', 'favorited')
                AND played_at IS NULL
                ORDER BY created_at ASC LIMIT 5""",
            genre_ids,
        ).fetchall()
        generating = db.execute(
            f"""SELECT COUNT(*) FROM generation_tasks
                WHERE genre_id IN ({placeholders})
                AND status IN ('pending', 'processing')""",
            genre_ids,
        ).fetchone()[0]

    return {
        "upcoming": [_track_row_to_dict(db, r) for r in upcoming],
        "generating": generating,
    }


@router.get("/radio/genres", response_model=list[GenreOut])
def list_genres():
    """Return all available genres for the tuner band."""
    from src.config import load_categories_config

    rows = get_all_genres()
    cols = {col[1] for col in get_db().execute("PRAGMA table_info(genres)").fetchall()}
    has_gen_type = "generator_type" in cols
    valid_categories = set(load_categories_config().keys())
    return [
        GenreOut(
            id=r["id"],
            category=r["category"],
            description=r["description"],
            prefix=r["prefix"],
            caption=r["caption"],
            lyrics=r["lyrics"],
            dynamic_lyrics=bool(r["dynamic_lyrics"]),
            genre_selector_color=r["genre_selector_color"],
            oled_color=r["oled_color"],
            bpm_min=r["bpm_min"],
            bpm_max=r["bpm_max"],
            key_scale=r["key_scale"],
            duration_min=r["duration_min"],
            duration_max=r["duration_max"],
            sort_order=r["sort_order"],
            generator_type=r["generator_type"] if has_gen_type else "custom",
        )
        for r in rows
        if r["category"] in valid_categories
    ]


@router.post("/radio/genres")
def create_genre(req: GenreCreateRequest):
    """Create a new genre — writes to DB and genre.yaml."""
    db = get_db()
    existing = db.execute("SELECT id FROM genres WHERE id = ?", (req.id,)).fetchone()
    if existing:
        return {"ok": False, "error": "Genre ID already exists"}

    max_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) FROM genres").fetchone()[0]
    db.execute(
        """INSERT INTO genres (id, category, prefix, description, caption, lyrics,
           bpm_min, bpm_max, key_scale, duration_min, duration_max, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (req.id, req.category, req.prefix, req.description, req.caption, req.lyrics,
         req.bpm_min, req.bpm_max, req.key_scale, req.duration_min,
         req.duration_max, max_order + 1),
    )
    db.commit()

    # Write to genre.yaml
    from src.config import add_genre_variant_to_yaml
    variant_data = {
        "prefix": req.prefix,
        "description": req.description,
        "caption": req.caption,
        "lyrics": req.lyrics,
        "bpm_min": req.bpm_min,
        "bpm_max": req.bpm_max,
        "key_scale": req.key_scale,
        "duration_min": req.duration_min,
        "duration_max": req.duration_max,
    }
    try:
        add_genre_variant_to_yaml(req.category, req.id, variant_data)
    except Exception as e:
        logger.warning("Failed to write genre to YAML: %s", e)

    return {"ok": True, "genre_id": req.id}


@router.put("/radio/genres/{genre_id}")
def update_genre(genre_id: str, req: GenreUpdateRequest):
    """Update a genre's editable fields — writes to DB and genre.yaml."""
    db = get_db()
    fields = []
    values = []
    yaml_fields = {}
    for field in ("description", "caption", "lyrics", "bpm_min", "bpm_max",
                  "key_scale", "duration_min", "duration_max"):
        val = getattr(req, field)
        if val is not None:
            fields.append(f"{field} = ?")
            values.append(val)
            yaml_fields[field] = val

    if not fields:
        return {"ok": False, "error": "No fields to update"}

    values.append(genre_id)
    db.execute(
        f"UPDATE genres SET {', '.join(fields)} WHERE id = ?",
        values,
    )
    db.commit()

    # Write back to genre.yaml
    genre_row = db.execute(
        "SELECT category FROM genres WHERE id = ?", (genre_id,)
    ).fetchone()
    if genre_row and genre_row["category"]:
        from src.config import save_genre_variant
        try:
            save_genre_variant(genre_row["category"], genre_id, yaml_fields)
        except Exception as e:
            logger.warning("Failed to write genre update to YAML: %s", e)

    return {"ok": True, "genre_id": genre_id}


@router.get("/radio/presets")
def get_presets():
    """Return all 6 preset slots."""
    db = get_db()
    rows = db.execute(
        "SELECT slot, genre_id FROM presets ORDER BY slot"
    ).fetchall()
    return [{"slot": r["slot"], "genre_id": r["genre_id"]} for r in rows]


@router.post("/radio/presets/{slot}")
def set_preset(slot: int, req: GenreSwitchRequest):
    """Set a preset slot to a genre."""
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO presets (slot, genre_id) VALUES (?, ?)",
        (slot, req.genre_id),
    )
    db.commit()
    return {"ok": True}


def _active_genre_ids() -> list[str]:
    """Return list of genre IDs currently active for radio playback.

    In ALL mode, returns all variant IDs in the active category.
    In specific mode, returns a single-element list.
    """
    if _radio_state["all_mode"] and _radio_state["category"]:
        rows = get_genres_by_category(_radio_state["category"])
        return [r["id"] for r in rows]
    if _radio_state["genre_id"]:
        return [_radio_state["genre_id"]]
    return []


def _pick_random_library_track(db, genre_ids, exclude_id=None):
    """Pick a random active/favorited track from the given genres."""
    import random

    placeholders = ",".join("?" * len(genre_ids))
    params = list(genre_ids)
    exclude_clause = ""
    if exclude_id:
        exclude_clause = " AND id != ?"
        params.append(exclude_id)
    rows = db.execute(
        f"""SELECT * FROM tracks
            WHERE genre_id IN ({placeholders})
            AND status IN ('active', 'favorited')
            {exclude_clause}""",
        params,
    ).fetchall()
    if not rows:
        return None
    return random.choice(rows)


def _track_row_to_dict(db, row):
    """Convert a track DB row to a TrackOut-compatible dict."""
    import json

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
            # Normalize: local paths get prefixed, URLs pass through
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
