"""Audio file serving and waveform data endpoints."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.config import DOWNLOADS_DIR
from src.database import get_db

router = APIRouter(tags=["audio"])


@router.get("/audio/{filename}")
def serve_audio(filename: str):
    """Serve an audio file from the downloads directory."""
    filepath = DOWNLOADS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Determine media type from extension
    suffix = filepath.suffix.lower()
    media_types = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".ogg": "audio/ogg",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(
        path=str(filepath),
        media_type=media_type,
        filename=filename,
    )


@router.get("/audio/{filename}/waveform")
def get_waveform(filename: str):
    """Return pre-computed waveform data for a track."""
    import json

    db = get_db()
    row = db.execute(
        "SELECT waveform FROM tracks WHERE filename = ?", (filename,)
    ).fetchone()

    if not row or not row["waveform"]:
        raise HTTPException(status_code=404, detail="Waveform not found")

    return {"waveform": json.loads(row["waveform"])}
