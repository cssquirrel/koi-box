"""Genre pack installation and management service.

Handles downloading packs from GitHub or custom URLs, extracting them,
and installing their contents into the app's config directories.
"""

import io
import json
import logging
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

import requests
import yaml

from src.config import (
    ALBUM_COVERS_DIR,
    CATEGORIES_CONFIG_PATH,
    CONFIG_DIR,
    GENERATORS_DIR,
    GENRE_CONFIG_PATH,
    PROJECT_ROOT,
    _load_ruamel_yaml,
    _save_ruamel_yaml,
)

logger = logging.getLogger(__name__)

GITHUB_REPO = "cssquirrel/koi-box-genre-packs"
GITHUB_BRANCH = "main"
INDEX_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/index.json"
ZIPBALL_URL = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/{GITHUB_BRANCH}.zip"

INSTALLED_PACKS_PATH = CONFIG_DIR / "installed_packs.json"
AUTOPILOT_WEIGHTS_PATH = CONFIG_DIR / "autopilot_weights.json"

CORE_CATEGORIES = {"lofi", "citypop", "synthwave"}


# ---------------------------------------------------------------------------
# Installed packs registry
# ---------------------------------------------------------------------------


def _load_installed_packs():
    """Load the installed packs registry."""
    if not INSTALLED_PACKS_PATH.exists():
        return {}
    with open(INSTALLED_PACKS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_installed_packs(data):
    """Save the installed packs registry."""
    with open(INSTALLED_PACKS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_installed_packs():
    """Return list of installed pack entries."""
    return _load_installed_packs()


# ---------------------------------------------------------------------------
# Autopilot weights
# ---------------------------------------------------------------------------


def _load_autopilot_weights():
    """Load dynamic autopilot weights."""
    if not AUTOPILOT_WEIGHTS_PATH.exists():
        return {}
    with open(AUTOPILOT_WEIGHTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_autopilot_weights(data):
    """Save dynamic autopilot weights."""
    with open(AUTOPILOT_WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_autopilot_weights():
    """Return all dynamic autopilot weights."""
    return _load_autopilot_weights()


# ---------------------------------------------------------------------------
# Browse available packs
# ---------------------------------------------------------------------------


def browse_packs():
    """Fetch the pack index from GitHub and filter out already-installed packs."""
    try:
        # Cache-bust to avoid stale GitHub CDN responses
        bust = f"?_={int(time.time())}"
        headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
        resp = requests.get(INDEX_URL + bust, timeout=15, headers=headers)
        resp.raise_for_status()
        index = resp.json()
    except Exception as e:
        logger.warning("Failed to fetch pack index: %s", e)
        raise RuntimeError(f"Failed to fetch pack index: {e}")

    installed = _load_installed_packs()
    packs = index.get("packs", [])

    result = []
    for pack in packs:
        pack_id = pack.get("id", "")
        pack["installed"] = pack_id in installed
        result.append(pack)

    return result


# ---------------------------------------------------------------------------
# Install pack
# ---------------------------------------------------------------------------


def install_from_repo(pack_path: str):
    """Install a pack from the default GitHub repository.

    pack_path: the path field from index.json, e.g. "packs/cssquirrel/kalt"
    """
    logger.info("Downloading repo zipball for pack: %s", pack_path)
    bust = f"?_={int(time.time())}"
    headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
    resp = requests.get(ZIPBALL_URL + bust, timeout=120, stream=True, headers=headers)
    resp.raise_for_status()

    zip_bytes = io.BytesIO(resp.content)
    return _install_from_zip(zip_bytes, pack_path)


def install_from_url(url: str):
    """Install a pack from a custom zip URL."""
    logger.info("Downloading pack from URL: %s", url)
    resp = requests.get(url, timeout=120, stream=True)
    resp.raise_for_status()

    zip_bytes = io.BytesIO(resp.content)
    return _install_from_zip(zip_bytes, pack_path=None)


def _install_from_zip(zip_bytes: io.BytesIO, pack_path: str | None):
    """Extract and install a pack from a zip file.

    For repo zips, pack_path identifies which subdirectory to extract.
    For custom URL zips, pack_path is None and the root is used.
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="koibox-pack-"))

    try:
        with zipfile.ZipFile(zip_bytes) as zf:
            zf.extractall(tmpdir)

        pack_dir = _find_pack_dir(tmpdir, pack_path)
        if not pack_dir:
            raise RuntimeError("Could not locate pack directory in zip")

        manifest_path = pack_dir / "pack.manifest"
        if not manifest_path.exists():
            raise RuntimeError("pack.manifest not found in pack directory")

        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)

        category_id = manifest.get("category_id")
        if not category_id:
            raise RuntimeError("pack.manifest missing category_id")

        # Check if already installed
        installed = _load_installed_packs()
        if category_id in installed:
            raise RuntimeError(f"Pack '{category_id}' is already installed")

        # Check if category already exists in config
        from src.config import load_categories_config
        if category_id in load_categories_config():
            raise RuntimeError(
                f"Category '{category_id}' already exists in config"
            )

        # Install files
        logger.info("Copying pack files for '%s'...", category_id)
        file_manifest = _copy_pack_files(pack_dir, category_id)
        logger.info("Pack files copied: %d covers, %d pools, %d profiles, %d prompts",
                     len(file_manifest["album_covers"]), len(file_manifest["pools"]),
                     len(file_manifest["profiles"]), len(file_manifest["prompts"]))

        # Merge YAML configs
        logger.info("Merging YAML configs...")
        _merge_category_yaml(pack_dir)
        _merge_genre_yaml(pack_dir)

        # Record installation
        installed[category_id] = {
            "manifest": manifest,
            "files": file_manifest,
        }
        _save_installed_packs(installed)
        logger.info("Installation recorded in installed_packs.json")

        # Reseed DB
        from src.database import get_db, _reseed_genres
        _reseed_genres(get_db())
        logger.info("Genres reseeded in DB")

        # Generate autopilot weights (non-blocking: use neutral if LLM busy)
        try:
            _generate_autopilot_weights(pack_dir, manifest)
        except Exception as e:
            logger.warning("Autopilot weight generation failed (pack still installed): %s", e)

        logger.info("Pack '%s' installed successfully", category_id)
        return {"ok": True, "category_id": category_id}

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def _find_pack_dir(tmpdir: Path, pack_path: str | None) -> Path | None:
    """Locate the pack directory inside the extracted zip.

    GitHub zipballs have a top-level directory like 'repo-name-branch/'.
    For repo installs, we look for pack_path inside that.
    For custom URL installs, we look for pack.manifest at root or one level down.
    """
    # List top-level entries
    entries = list(tmpdir.iterdir())

    if pack_path:
        # Repo zip: top-level is something like 'koi-box-genre-packs-main/'
        for entry in entries:
            if entry.is_dir():
                candidate = entry / pack_path
                if candidate.exists() and (candidate / "pack.manifest").exists():
                    return candidate
        # Fallback: try direct path
        direct = tmpdir / pack_path
        if direct.exists() and (direct / "pack.manifest").exists():
            return direct
        # Fallback: walk for pack.manifest anywhere and match by last path segment
        pack_leaf = Path(pack_path).name
        for root_entry in entries:
            if not root_entry.is_dir():
                continue
            for manifest in root_entry.rglob("pack.manifest"):
                if manifest.parent.name == pack_leaf:
                    logger.info("Found pack via fallback walk: %s", manifest.parent)
                    return manifest.parent
    else:
        # Custom URL zip: manifest at root or one level down
        if (tmpdir / "pack.manifest").exists():
            return tmpdir
        for entry in entries:
            if entry.is_dir() and (entry / "pack.manifest").exists():
                return entry

    return None


def _copy_pack_files(pack_dir: Path, category_id: str) -> dict:
    """Copy pack files into the app's directories. Returns a file manifest."""
    copied = {"album_covers": [], "pools": [], "profiles": [], "prompts": []}

    # Album covers
    covers_src = pack_dir / "album_covers"
    if covers_src.exists():
        for subdir in covers_src.iterdir():
            if subdir.is_dir():
                dest = ALBUM_COVERS_DIR / subdir.name
                dest.mkdir(parents=True, exist_ok=True)
                for img in subdir.iterdir():
                    if img.is_file():
                        shutil.copy2(img, dest / img.name)
                        copied["album_covers"].append(
                            str(dest / img.name)
                        )
                logger.info(
                    "Copied %d album covers to %s",
                    len(list(subdir.iterdir())), dest,
                )

    # Generator pools
    pools_src = pack_dir / "config" / "generators" / "pools"
    if pools_src.exists():
        for pool_dir in pools_src.iterdir():
            if pool_dir.is_dir():
                dest = GENERATORS_DIR / "pools" / pool_dir.name
                dest.mkdir(parents=True, exist_ok=True)
                for txt in pool_dir.iterdir():
                    if txt.is_file():
                        shutil.copy2(txt, dest / txt.name)
                        copied["pools"].append(str(dest / txt.name))

    # Generator profiles
    profiles_src = pack_dir / "config" / "generators" / "profiles"
    if profiles_src.exists():
        for profile in profiles_src.iterdir():
            if profile.is_file():
                dest = GENERATORS_DIR / "profiles" / profile.name
                shutil.copy2(profile, dest)
                copied["profiles"].append(str(dest))

    # Prompt files
    prompts_src = pack_dir / "config" / "generators" / "prompts"
    if prompts_src.exists():
        for prompt in prompts_src.iterdir():
            if prompt.is_file():
                dest = GENERATORS_DIR / "prompts" / prompt.name
                shutil.copy2(prompt, dest)
                copied["prompts"].append(str(dest))

    return copied


def _merge_category_yaml(pack_dir: Path):
    """Merge pack's category_info.yaml into the app's categories.yaml."""
    cat_src = pack_dir / "config" / "category_info.yaml"
    if not cat_src.exists():
        logger.warning("No category_info.yaml in pack")
        return

    with open(cat_src, encoding="utf-8") as f:
        pack_cats = yaml.safe_load(f) or {}

    ry, data = _load_ruamel_yaml(CATEGORIES_CONFIG_PATH)
    cats = data.get("categories", {})

    for cat_id, cat_data in pack_cats.items():
        if cat_id not in cats:
            cats[cat_id] = cat_data
            logger.info("Added category '%s' to categories.yaml", cat_id)

    _save_ruamel_yaml(CATEGORIES_CONFIG_PATH, ry, data)


def _merge_genre_yaml(pack_dir: Path):
    """Merge pack's genre_info.yaml into the app's genre.yaml."""
    genre_src = pack_dir / "config" / "genre_info.yaml"
    if not genre_src.exists():
        logger.warning("No genre_info.yaml in pack")
        return

    with open(genre_src, encoding="utf-8") as f:
        pack_genres = yaml.safe_load(f) or {}

    ry, data = _load_ruamel_yaml(GENRE_CONFIG_PATH)
    genres = data.get("genres", {})

    for cat_id, cat_data in pack_genres.items():
        if cat_id not in genres:
            genres[cat_id] = cat_data
            logger.info("Added genre category '%s' to genre.yaml", cat_id)
        else:
            # Merge variants into existing category
            existing_variants = genres[cat_id].get("variants", {})
            new_variants = cat_data.get("variants", {})
            for vid, vdata in new_variants.items():
                if vid not in existing_variants:
                    existing_variants[vid] = vdata

    _save_ruamel_yaml(GENRE_CONFIG_PATH, ry, data)


# ---------------------------------------------------------------------------
# Autopilot weight generation via Qwen
# ---------------------------------------------------------------------------

WEIGHT_PROMPT = """Given this music genre description, rate its suitability (0-10) for each context.
Higher numbers mean better fit. Be decisive — avoid all-5s.

Description: "{description}"

Return ONLY valid JSON, no explanation:
{{"time": {{"early-morning": N, "morning": N, "midday": N, "afternoon": N, "golden-hour": N, "evening": N, "night": N, "late-night": N}}, "weather": {{"clear": N, "partly-cloudy": N, "overcast": N, "foggy": N, "rainy": N, "snowy": N, "stormy": N}}}}"""


def _generate_autopilot_weights(pack_dir: Path, manifest: dict):
    """Generate autopilot weights for each variant using Qwen."""
    genre_src = pack_dir / "config" / "genre_info.yaml"
    if not genre_src.exists():
        return

    with open(genre_src, encoding="utf-8") as f:
        pack_genres = yaml.safe_load(f) or {}

    weights = _load_autopilot_weights()
    variants_to_classify = []

    for cat_data in pack_genres.values():
        for vid, vdata in cat_data.get("variants", {}).items():
            desc = vdata.get("description", "")
            if desc and vid not in weights:
                variants_to_classify.append((vid, desc.strip()))

    if not variants_to_classify:
        return

    # Try Qwen classification (non-blocking — fall back to neutral if LLM busy)
    try:
        from src.services.llm_lock import llm_lock
        acquired = llm_lock.acquire(timeout=5)
        if not acquired:
            logger.info("LLM busy, using neutral weights for autopilot")
            _apply_neutral_weights(variants_to_classify, weights)
        else:
            try:
                _classify_with_llm(variants_to_classify, weights)
            finally:
                llm_lock.release()
    except Exception as e:
        logger.warning("LLM weight generation failed, using neutral defaults: %s", e)
        _apply_neutral_weights(variants_to_classify, weights)

    _save_autopilot_weights(weights)
    logger.info(
        "Generated autopilot weights for %d variants",
        len(variants_to_classify),
    )


def _classify_with_llm(variants: list, weights: dict):
    """Use the local Qwen LLM to classify variants."""
    from src.services.bios import _load_model, _unload_model

    llm = _load_model()
    if not llm:
        raise RuntimeError("Could not load Qwen model")

    try:
        for vid, desc in variants:
            prompt = WEIGHT_PROMPT.format(description=desc)
            result = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": "You are a music classification assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.3,
            )
            text = result["choices"][0]["message"]["content"].strip()
            parsed = _parse_weight_json(text)
            if parsed:
                weights[vid] = parsed
                logger.info("Generated weights for %s: %s", vid, parsed)
            else:
                logger.warning("Failed to parse weights for %s, using neutral", vid)
                weights[vid] = _neutral_weight()
    finally:
        _unload_model(llm)


def _parse_weight_json(text: str) -> dict | None:
    """Parse LLM output into weight dict, handling markdown fences."""
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
        if "time" in data and "weather" in data:
            # Validate values are numeric 0-10
            for section in ("time", "weather"):
                for key, val in data[section].items():
                    data[section][key] = max(0, min(10, int(val)))
            return data
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    return None


def _neutral_weight():
    """Return neutral autopilot weights (all 5s)."""
    return {
        "time": {
            "early-morning": 5, "morning": 5, "midday": 5, "afternoon": 5,
            "golden-hour": 5, "evening": 5, "night": 5, "late-night": 5,
        },
        "weather": {
            "clear": 5, "partly-cloudy": 5, "overcast": 5, "foggy": 5,
            "rainy": 5, "snowy": 5, "stormy": 5,
        },
    }


def _apply_neutral_weights(variants: list, weights: dict):
    """Apply neutral weights to all variants."""
    for vid, _ in variants:
        weights[vid] = _neutral_weight()


# ---------------------------------------------------------------------------
# Uninstall pack
# ---------------------------------------------------------------------------


def uninstall_pack(category_id: str):
    """Remove an installed genre pack and all its files."""
    if category_id in CORE_CATEGORIES:
        raise RuntimeError(f"Cannot delete core category '{category_id}'")

    installed = _load_installed_packs()
    pack_info = installed.get(category_id)

    # Check for tracks/albums (same safety check as categories.py)
    from src.database import get_db
    db = get_db()
    genres = db.execute(
        "SELECT id FROM genres WHERE category = ?", (category_id,)
    ).fetchall()

    for genre_row in genres:
        gid = genre_row["id"]
        tracks = db.execute(
            "SELECT COUNT(*) FROM tracks WHERE genre_id = ?", (gid,)
        ).fetchone()[0]
        albums = db.execute(
            "SELECT COUNT(*) FROM albums WHERE genre_id = ?", (gid,)
        ).fetchone()[0]
        if tracks > 0 or albums > 0:
            raise RuntimeError(
                f"Cannot delete: genre '{gid}' has {tracks} tracks and {albums} albums. "
                "Delete or dislike all tracks first."
            )

    # Remove genres from DB
    for genre_row in genres:
        db.execute("DELETE FROM genres WHERE id = ?", (genre_row["id"],))
        db.execute("DELETE FROM presets WHERE genre_id = ?", (genre_row["id"],))
    db.commit()

    # Remove from YAML configs
    from src.config import remove_category_from_yaml
    remove_category_from_yaml(category_id)

    # Clean up installed files
    if pack_info and "files" in pack_info:
        _cleanup_pack_files(pack_info["files"], category_id)

    # Remove autopilot weights for this pack's variants
    weights = _load_autopilot_weights()
    if pack_info and "manifest" in pack_info:
        for vid in pack_info["manifest"].get("variants", []):
            weights.pop(vid, None)
        _save_autopilot_weights(weights)

    # Remove from installed packs registry
    installed.pop(category_id, None)
    _save_installed_packs(installed)

    logger.info("Pack '%s' uninstalled successfully", category_id)
    return {"ok": True}


def _cleanup_pack_files(file_manifest: dict, category_id: str):
    """Remove files installed by a pack."""
    # Remove individual tracked files
    for key in ("profiles", "prompts"):
        for filepath in file_manifest.get(key, []):
            p = Path(filepath)
            if p.exists():
                p.unlink()
                logger.info("Removed: %s", p)

    # Remove pool directory
    pools_dir = GENERATORS_DIR / "pools" / category_id
    if pools_dir.exists():
        shutil.rmtree(pools_dir)
        logger.info("Removed pool directory: %s", pools_dir)

    # Remove album covers directory
    # Find the cover dir name from the manifest files
    cover_dirs = set()
    for filepath in file_manifest.get("album_covers", []):
        p = Path(filepath)
        if p.parent.parent == ALBUM_COVERS_DIR:
            cover_dirs.add(p.parent)

    for cover_dir in cover_dirs:
        if cover_dir.exists():
            shutil.rmtree(cover_dir)
            logger.info("Removed album covers: %s", cover_dir)
