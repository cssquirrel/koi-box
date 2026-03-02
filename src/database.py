"""SQLite database setup, schema creation, and seeding."""

import json
import logging
import sqlite3
from pathlib import Path

from src.config import (
    DB_PATH,
    flatten_generation_config,
    flatten_genre_config,
    load_generation_config,
    load_genre_config,
)

_connection: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    """Return the shared database connection, creating it if needed."""
    global _connection
    if _connection is None:
        _connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        _connection.execute("PRAGMA journal_mode=WAL")
        _connection.execute("PRAGMA foreign_keys=ON")
    return _connection


def close_db():
    """Close the shared database connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None


def init_db():
    """Create all tables and seed initial data if the DB is fresh."""
    db = get_db()
    _create_tables(db)
    _migrate_genres_schema(db)
    _seed_if_empty(db)
    _clear_stale_tasks(db)
    _migrate_album_covers_to_local(db)


def _clear_stale_tasks(db: sqlite3.Connection):
    """Mark any pending/processing generation tasks as failed on startup.

    These are orphaned from a previous session — the API server won't
    know about them, so they would block the buffer worker forever.
    """
    updated = db.execute(
        """UPDATE generation_tasks
           SET status = 'failed', completed_at = CURRENT_TIMESTAMP
           WHERE status IN ('pending', 'processing')"""
    ).rowcount
    if updated:
        db.commit()
        logging.getLogger(__name__).info(
            "Cleared %d stale generation tasks from previous session", updated
        )


def _migrate_album_covers_to_local(db: sqlite3.Connection):
    """Replace HTTP cover URLs on open albums with local cover paths.

    Runs on every startup. Albums with Unsplash URLs get reassigned a
    random local cover from album_covers/<category>/.
    """
    import random as _rand
    from src.config import ALBUM_COVERS_DIR

    logger = logging.getLogger(__name__)
    rows = db.execute(
        "SELECT a.id, a.genre_id, g.album_cover_directory, g.category "
        "FROM albums a JOIN genres g ON a.genre_id = g.id "
        "WHERE a.cover_url LIKE 'http%'"
    ).fetchall()

    if not rows:
        return

    for row in rows:
        directory = row["album_cover_directory"] or row["category"] or "lofi"
        cover_dir = ALBUM_COVERS_DIR / directory
        if not cover_dir.is_dir():
            continue
        images = list(cover_dir.glob("*.jpg")) + list(cover_dir.glob("*.png"))
        if not images:
            continue
        pick = _rand.choice(images)
        local_path = f"{directory}/{pick.name}"
        db.execute(
            "UPDATE albums SET cover_url = ? WHERE id = ?",
            (local_path, row["id"]),
        )

    db.commit()
    logger.info("Migrated %d album covers from URLs to local paths", len(rows))


def _create_tables(db: sqlite3.Connection):
    """Create all application tables."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS genres (
            id              TEXT PRIMARY KEY,
            category        TEXT NOT NULL DEFAULT '',
            description     TEXT NOT NULL DEFAULT '',
            prefix          TEXT NOT NULL,
            caption         TEXT NOT NULL,
            lyrics          TEXT NOT NULL DEFAULT '',
            dynamic_lyrics  INTEGER NOT NULL DEFAULT 0,
            lyrics_guidance TEXT NOT NULL DEFAULT '',
            theme_seeds     TEXT NOT NULL DEFAULT '[]',
            album_cover_directory TEXT NOT NULL DEFAULT '',
            genre_selector_color TEXT NOT NULL DEFAULT '',
            oled_color      TEXT NOT NULL DEFAULT '',
            bpm_min         INTEGER NOT NULL,
            bpm_max         INTEGER NOT NULL,
            key_scale       TEXT NOT NULL,
            duration_min    INTEGER NOT NULL,
            duration_max    INTEGER NOT NULL,
            sort_order      INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS albums (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            artist        TEXT NOT NULL,
            cover_url     TEXT,
            genre_id      TEXT NOT NULL REFERENCES genres(id),
            target_count  INTEGER NOT NULL DEFAULT 6,
            track_count   INTEGER NOT NULL DEFAULT 0,
            is_open       INTEGER NOT NULL DEFAULT 1,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tracks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            artist        TEXT NOT NULL,
            album_id      INTEGER REFERENCES albums(id),
            genre_id      TEXT NOT NULL REFERENCES genres(id),
            filename      TEXT NOT NULL,
            filepath      TEXT NOT NULL,
            duration      REAL,
            waveform      TEXT,
            status        TEXT NOT NULL DEFAULT 'active',
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            played_at     TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS playlists (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS playlist_tracks (
            playlist_id   INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
            track_id      INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
            position      INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (playlist_id, track_id)
        );

        CREATE TABLE IF NOT EXISTS presets (
            slot      INTEGER PRIMARY KEY,
            genre_id  TEXT REFERENCES genres(id)
        );

        CREATE TABLE IF NOT EXISTS generation_tasks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id       TEXT NOT NULL,
            genre_id      TEXT NOT NULL REFERENCES genres(id),
            status        TEXT NOT NULL DEFAULT 'pending',
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at  TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_tracks_genre ON tracks(genre_id);
        CREATE INDEX IF NOT EXISTS idx_tracks_status ON tracks(status);
        CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album_id);
        CREATE INDEX IF NOT EXISTS idx_albums_genre ON albums(genre_id);
        CREATE INDEX IF NOT EXISTS idx_generation_tasks_status ON generation_tasks(status);
    """)
    db.commit()


def _migrate_genres_schema(db: sqlite3.Connection):
    """Add new columns to genres table if missing (preserves existing data)."""
    logger = logging.getLogger(__name__)
    columns = {r[1] for r in db.execute("PRAGMA table_info(genres)").fetchall()}
    migrations = {
        "category": "TEXT NOT NULL DEFAULT ''",
        "dynamic_lyrics": "INTEGER NOT NULL DEFAULT 0",
        "lyrics_guidance": "TEXT NOT NULL DEFAULT ''",
        "theme_seeds": "TEXT NOT NULL DEFAULT '[]'",
        "album_cover_directory": "TEXT NOT NULL DEFAULT ''",
        "genre_selector_color": "TEXT NOT NULL DEFAULT ''",
        "oled_color": "TEXT NOT NULL DEFAULT ''",
        "generator_type": "TEXT NOT NULL DEFAULT 'custom'",
    }
    for col, typedef in migrations.items():
        if col not in columns:
            db.execute(f"ALTER TABLE genres ADD COLUMN {col} {typedef}")
            logger.info("Added column genres.%s", col)
    db.commit()

    # Re-seed genre data if new columns were added (updates existing rows)
    if migrations.keys() - columns:
        _reseed_genres(db)


def _seed_if_empty(db: sqlite3.Connection):
    """Seed the database with initial data from config files if tables are empty."""
    _seed_genres(db)
    _seed_settings(db)
    _seed_presets(db)


def _seed_genres(db: sqlite3.Connection):
    """Sync genres from genre.yaml on every startup.

    Always runs INSERT OR REPLACE to keep genre data in sync with the YAML,
    and removes stale genres that no longer exist in config.
    """
    _reseed_genres(db)


def _reseed_genres(db: sqlite3.Connection):
    """Update existing genre rows with data from the current genre.yaml.

    Uses INSERT OR REPLACE to update existing genres and add new ones.
    Removes old genre rows whose IDs no longer appear in the YAML, but
    only if no tracks/albums reference them (preserves user data).
    """
    logger = logging.getLogger(__name__)
    flat = flatten_genre_config()
    current_ids = {entry["id"] for entry in flat}

    # Find DB genre IDs not in the current YAML
    db_ids = {r[0] for r in db.execute("SELECT id FROM genres").fetchall()}
    stale_ids = db_ids - current_ids

    for stale_id in stale_ids:
        # Only delete if no tracks or albums reference this genre
        track_count = db.execute(
            "SELECT COUNT(*) FROM tracks WHERE genre_id = ?", (stale_id,)
        ).fetchone()[0]
        album_count = db.execute(
            "SELECT COUNT(*) FROM albums WHERE genre_id = ?", (stale_id,)
        ).fetchone()[0]
        if track_count == 0 and album_count == 0:
            db.execute("DELETE FROM generation_tasks WHERE genre_id = ?", (stale_id,))
            db.execute("DELETE FROM presets WHERE genre_id = ?", (stale_id,))
            db.execute("DELETE FROM genres WHERE id = ?", (stale_id,))
            logger.info("Removed stale genre '%s' (not in YAML, no tracks)", stale_id)
        else:
            logger.warning(
                "Keeping stale genre '%s' — still referenced by %d tracks, %d albums",
                stale_id, track_count, album_count,
            )

    _insert_genres(db)
    db.commit()
    logger.info("Re-seeded genres with updated schema fields")


def _insert_genres(db: sqlite3.Connection):
    """Insert or replace all genres from the flattened genre config."""
    flat = flatten_genre_config()
    for sort_order, entry in enumerate(flat):
        theme_seeds = json.dumps(entry.get("theme_seeds", []), ensure_ascii=False)
        db.execute(
            """INSERT OR REPLACE INTO genres
               (id, category, description, prefix, caption, lyrics,
                dynamic_lyrics, lyrics_guidance, theme_seeds,
                album_cover_directory, genre_selector_color, oled_color,
                bpm_min, bpm_max, key_scale, duration_min, duration_max,
                sort_order, generator_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entry["id"],
                entry["category"],
                entry.get("description", "").strip(),
                entry["prefix"],
                entry["caption"].strip(),
                entry.get("lyrics", "").strip(),
                1 if entry.get("dynamic_lyrics") else 0,
                entry.get("lyrics_guidance", "").strip(),
                theme_seeds,
                entry.get("album_cover_directory", ""),
                entry.get("genre_selector_color", ""),
                entry.get("oled_color", ""),
                entry["bpm_min"],
                entry["bpm_max"],
                entry["key_scale"],
                entry["duration_min"],
                entry["duration_max"],
                sort_order,
                entry.get("generator_type", "custom"),
            ),
        )
    db.commit()


def _seed_settings(db: sqlite3.Connection):
    """Seed settings from generation.yaml if the settings table is empty."""
    count = db.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
    if count > 0:
        return

    config = load_generation_config()
    flat = flatten_generation_config(config)
    for key, value in flat.items():
        db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )
    db.commit()


def _seed_presets(db: sqlite3.Connection):
    """Seed preset slots 1-6 with the first genres available."""
    count = db.execute("SELECT COUNT(*) FROM presets").fetchone()[0]
    if count > 0:
        return

    genres = db.execute(
        "SELECT id FROM genres ORDER BY sort_order LIMIT 6"
    ).fetchall()
    for slot, row in enumerate(genres, start=1):
        db.execute(
            "INSERT INTO presets (slot, genre_id) VALUES (?, ?)",
            (slot, row["id"]),
        )
    db.commit()


# -- Query helpers used across routes --


def get_setting(key: str, default=None):
    """Get a single setting value, JSON-decoded."""
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return json.loads(row["value"])


def set_setting(key: str, value):
    """Set a single setting value, JSON-encoded."""
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, json.dumps(value)),
    )
    db.commit()


def get_all_genres():
    """Return all genres ordered by sort_order."""
    db = get_db()
    return db.execute("SELECT * FROM genres ORDER BY sort_order").fetchall()


def get_genre(genre_id: str):
    """Return a single genre by ID."""
    db = get_db()
    return db.execute("SELECT * FROM genres WHERE id = ?", (genre_id,)).fetchone()


def get_genres_by_category(category: str):
    """Return all genres in a category, ordered by sort_order."""
    db = get_db()
    return db.execute(
        "SELECT * FROM genres WHERE category = ? ORDER BY sort_order",
        (category,),
    ).fetchall()
