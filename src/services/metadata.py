"""MP3 ID3 tag writing using mutagen."""

import logging
from pathlib import Path

from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1, TPE2, TRCK
from mutagen.mp3 import MP3

logger = logging.getLogger(__name__)


def write_id3_tags(filepath, title, artist, album, track_number=1, genre_name="Lo-Fi"):
    """Write ID3v2 tags to an MP3 file."""
    filepath = Path(filepath)
    if not filepath.exists() or filepath.suffix.lower() != ".mp3":
        logger.warning("Cannot write ID3 tags to %s", filepath)
        return False

    try:
        audio = MP3(str(filepath))

        # Create ID3 tag if it doesn't exist
        if audio.tags is None:
            audio.add_tags()

        tags = audio.tags
        tags.add(TIT2(encoding=3, text=title))
        tags.add(TPE1(encoding=3, text=artist))
        tags.add(TPE2(encoding=3, text=artist))
        tags.add(TALB(encoding=3, text=album))
        tags.add(TRCK(encoding=3, text=str(track_number)))

        audio.save()
        logger.info("Wrote ID3 tags to %s", filepath.name)
        return True
    except Exception as e:
        logger.error("Failed to write ID3 tags to %s: %s", filepath, e)
        return False


def embed_cover_art(filepath, image_data, mime_type="image/jpeg"):
    """Embed album cover art into an MP3 file."""
    filepath = Path(filepath)
    if not filepath.exists() or filepath.suffix.lower() != ".mp3":
        return False

    try:
        audio = MP3(str(filepath))
        if audio.tags is None:
            audio.add_tags()

        audio.tags.add(
            APIC(
                encoding=3,
                mime=mime_type,
                type=3,  # Cover (front)
                desc="Cover",
                data=image_data,
            )
        )
        audio.save()
        logger.info("Embedded cover art in %s", filepath.name)
        return True
    except Exception as e:
        logger.error("Failed to embed cover art in %s: %s", filepath, e)
        return False


def embed_local_cover(filepath, cover_relative_path):
    """Read a local cover image and embed it in the MP3.

    cover_relative_path: e.g. 'lofi/lofi-0042.jpg' relative to ALBUM_COVERS_DIR.
    """
    from src.config import ALBUM_COVERS_DIR

    cover_file = ALBUM_COVERS_DIR / cover_relative_path
    if not cover_file.exists():
        logger.warning("Local cover not found: %s", cover_file)
        return False

    try:
        image_data = cover_file.read_bytes()
        suffix = cover_file.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        return embed_cover_art(filepath, image_data, mime)
    except Exception as e:
        logger.error("Failed to embed local cover %s: %s", cover_file, e)
        return False


def download_and_embed_cover(filepath, cover_url):
    """Download cover image from URL and embed it in the MP3."""
    import requests

    try:
        resp = requests.get(cover_url + "?w=400&h=400&fit=crop", timeout=15)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/jpeg")
        return embed_cover_art(filepath, resp.content, content_type)
    except Exception as e:
        logger.warning("Failed to download cover art from %s: %s", cover_url, e)
        return False
