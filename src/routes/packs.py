"""Genre pack management endpoints — browse, install, uninstall."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.services.packs import (
    browse_packs,
    get_autopilot_weights,
    get_installed_packs,
    install_from_repo,
    install_from_url,
    uninstall_pack,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["packs"])


class InstallRequest(BaseModel):
    pack_path: Optional[str] = None
    url: Optional[str] = None


@router.get("/packs/browse")
def browse():
    """List available packs from the index, marking installed ones."""
    try:
        return browse_packs()
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/packs/installed")
def installed():
    """List currently installed packs."""
    return get_installed_packs()


@router.post("/packs/install")
def install(req: InstallRequest):
    """Install a genre pack from repo or custom URL."""
    if not req.pack_path and not req.url:
        raise HTTPException(
            status_code=400, detail="Provide pack_path or url"
        )

    try:
        if req.pack_path:
            return install_from_repo(req.pack_path)
        else:
            return install_from_url(req.url)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Pack install failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/packs/{category_id}")
def uninstall(category_id: str):
    """Uninstall a genre pack by its category ID."""
    try:
        return uninstall_pack(category_id)
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Pack uninstall failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/autopilot/weights")
def autopilot_weights():
    """Return all dynamic autopilot weights for installed packs."""
    return get_autopilot_weights()
