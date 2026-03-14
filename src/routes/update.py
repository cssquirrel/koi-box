"""Update check and apply endpoints."""

from fastapi import APIRouter

from src.services.updater import check_for_update, perform_update

router = APIRouter(prefix="/update", tags=["update"])


@router.get("/check")
def update_check():
    """Check GitHub for a newer release (respects 6-hour cooldown)."""
    return check_for_update()


@router.post("/apply")
def update_apply(body: dict = None):
    """Apply an update via git pull."""
    release_notes = ""
    release_version = ""
    if body:
        release_notes = body.get("release_notes", "")
        release_version = body.get("release_version", "")
    return perform_update(
        release_notes=release_notes,
        release_version=release_version,
    )
