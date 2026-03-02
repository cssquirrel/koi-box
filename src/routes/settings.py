"""Settings endpoints: read and update app configuration."""

import json

from fastapi import APIRouter

from src.database import get_db, get_setting, set_setting
from src.models import SettingOut, SettingUpdateRequest

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=list[SettingOut])
def list_settings():
    """Return all settings."""
    db = get_db()
    rows = db.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
    return [SettingOut(key=r["key"], value=r["value"]) for r in rows]


@router.get("/settings/{key}")
def get_setting_endpoint(key: str):
    """Get a single setting by key."""
    value = get_setting(key)
    if value is None:
        return {"key": key, "value": None}
    return {"key": key, "value": value}


@router.put("/settings/{key}")
def update_setting(key: str, req: SettingUpdateRequest):
    """Update a single setting."""
    set_setting(key, json.loads(req.value))
    return {"ok": True, "key": key}
