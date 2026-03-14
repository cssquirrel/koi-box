"""Auto-update service: version detection, GitHub release check, and git pull."""

import json
import logging
import re
import subprocess
import time

import requests

from src.config import PROJECT_ROOT
from src.database import get_setting, set_setting

logger = logging.getLogger(__name__)

GITHUB_REPO = "cssquirrel/koi-box"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"
REQUEST_TIMEOUT = 8
CHECK_COOLDOWN_SECONDS = 6 * 60 * 60  # 6 hours

_cached_version = None


def get_app_version() -> str:
    """Parse current version from CHANGELOG.MD (first ## [X.Y.Z] header)."""
    global _cached_version
    if _cached_version is not None:
        return _cached_version

    changelog = PROJECT_ROOT / "CHANGELOG.MD"
    if changelog.exists():
        for line in changelog.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^## \[(\d+\.\d+\.\d+)\]", line)
            if m:
                _cached_version = m.group(1)
                return _cached_version
    _cached_version = "0.0.0"
    return _cached_version


def _parse_version(v: str) -> tuple:
    """Convert version string to comparable tuple: '1.6.0' → (1, 6, 0)."""
    return tuple(int(x) for x in v.lstrip("v").split("."))


def check_for_update() -> dict:
    """Check GitHub for a newer release, respecting a 6-hour cooldown.

    Returns dict with at minimum { available: bool, current_version: str }.
    On update available, also includes: latest_version, release_notes, published_at.
    """
    current = get_app_version()
    base = {"available": False, "current_version": current}

    # Cooldown check — skip network if checked recently
    last_check = get_setting("last_update_check", 0)
    cached_result = get_setting("last_update_result", None)
    if time.time() - last_check < CHECK_COOLDOWN_SECONDS and cached_result:
        logger.debug("Update check skipped (cooldown), returning cached result.")
        return cached_result

    try:
        resp = requests.get(
            RELEASES_URL,
            timeout=REQUEST_TIMEOUT,
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.debug("GitHub release check failed: %s", e)
        set_setting("last_update_check", time.time())
        set_setting("last_update_result", base)
        return base

    tag = data.get("tag_name", "")
    if not tag:
        set_setting("last_update_check", time.time())
        set_setting("last_update_result", base)
        return base

    latest = tag.lstrip("v")
    available = _parse_version(latest) > _parse_version(current)

    result = {
        "available": available,
        "current_version": current,
        "latest_version": latest,
        "release_notes": data.get("body", ""),
        "published_at": data.get("published_at", ""),
    }

    set_setting("last_update_check", time.time())
    set_setting("last_update_result", result)
    logger.info(
        "Update check: current=%s, latest=%s, available=%s",
        current, latest, available,
    )
    return result


def _git_available() -> bool:
    """Check if git is on PATH."""
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True, check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _has_local_changes() -> bool:
    """Check for uncommitted changes in the working tree."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    return bool(result.stdout.strip())


def _git_pull() -> tuple[bool, str]:
    """Run git pull origin main. Returns (success, message)."""
    result = subprocess.run(
        ["git", "pull", "origin", "main"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, result.stderr.strip() or result.stdout.strip()


def perform_update(release_notes: str = "", release_version: str = "") -> dict:
    """Apply an update via git pull.

    Pre-flight checks: git available, no local modifications.
    Saves release notes before pulling so 'What's New' survives the restart.

    Returns { ok: bool, message: str }.
    """
    if not _git_available():
        return {
            "ok": False,
            "error": (
                "Git is required for auto-updates. "
                f"Download the latest release manually at {RELEASES_PAGE}"
            ),
        }

    if _has_local_changes():
        return {
            "ok": False,
            "error": (
                "Local files have been modified. "
                "Back up your changes or run 'git stash' before updating."
            ),
        }

    # Save release notes before pulling so they survive the file update
    if release_notes:
        set_setting("update_release_notes", release_notes)
    if release_version:
        set_setting("update_release_version", release_version)

    success, message = _git_pull()
    if success:
        # Clear cached version so it's re-parsed from updated CHANGELOG
        global _cached_version
        _cached_version = None
        # Clear the update check cache so badge disappears on next check
        set_setting("last_update_result", None)
        logger.info("Update applied successfully: %s", message)
        return {"ok": True, "message": message}

    logger.error("Git pull failed: %s", message)
    return {"ok": False, "error": message}
