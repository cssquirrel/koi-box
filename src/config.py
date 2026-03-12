"""Application configuration and path management."""

import logging
import sys
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def get_project_root():
    """Return the project root directory, handling both dev and PyInstaller."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


PROJECT_ROOT = get_project_root()
CONFIG_DIR = PROJECT_ROOT / "config"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
STATIC_DIR = Path(__file__).parent / "static"
DB_PATH = PROJECT_ROOT / "koi-box.db"
MODELS_DIR = PROJECT_ROOT / "models"
GENRE_CONFIG_PATH = CONFIG_DIR / "genre.yaml"
GENRE_USER_CONFIG_PATH = CONFIG_DIR / "genre.user.yaml"
GENERATION_CONFIG_PATH = CONFIG_DIR / "generation.yaml"
CATEGORIES_CONFIG_PATH = CONFIG_DIR / "categories.yaml"
CATEGORIES_USER_CONFIG_PATH = CONFIG_DIR / "categories.user.yaml"
GENERATORS_DIR = CONFIG_DIR / "generators"
GENERATORS_PACKS_DIR = GENERATORS_DIR / "packs"
ALBUM_COVERS_DIR = PROJECT_ROOT / "album_covers"

# Ensure directories exist
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Categories config
# ---------------------------------------------------------------------------


def load_categories_config():
    """Load category definitions, merging core and user (pack-installed) YAMLs.

    Returns dict: {category_name: {display_name, colors, generator, ...}}.
    """
    result = {}
    for path in (CATEGORIES_CONFIG_PATH, CATEGORIES_USER_CONFIG_PATH):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            result.update(data.get("categories", {}))
    return result


def get_category_config(category):
    """Return config dict for a single category, or empty dict."""
    return load_categories_config().get(category, {})


# ---------------------------------------------------------------------------
# Genre config
# ---------------------------------------------------------------------------


def load_genre_config():
    """Load genre definitions, merging core and user (pack-installed) YAMLs.

    Returns the nested structure: {category: {variants: {variant_id: data}}}.
    """
    result = {}
    for path in (GENRE_CONFIG_PATH, GENRE_USER_CONFIG_PATH):
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            result.update(data.get("genres", {}))
    return result


def flatten_genre_config(genres_nested=None):
    """Flatten nested genre config into a list of variant dicts for DB seeding.

    Merges category-level metadata from categories.yaml into each variant.
    Each variant dict gets 'category' and 'id' fields injected.
    """
    if genres_nested is None:
        genres_nested = load_genre_config()

    categories = load_categories_config()

    flat = []
    for category, category_data in genres_nested.items():
        variants = category_data.get("variants", {})
        cat_meta = categories.get(category, {})

        inherited = {
            "album_cover_directory": cat_meta.get("album_cover_directory", ""),
            "genre_selector_color": cat_meta.get("genre_selector_color", ""),
            "oled_color": cat_meta.get("oled_color", ""),
        }

        generator_type = cat_meta.get("generator", "custom")

        for variant_id, variant_data in variants.items():
            entry = dict(variant_data)
            entry["id"] = variant_id
            entry["category"] = category
            entry["generator_type"] = generator_type
            entry.update(inherited)
            flat.append(entry)
    return flat


# ---------------------------------------------------------------------------
# Generation config
# ---------------------------------------------------------------------------


def load_generation_config():
    """Load generation settings from generation.yaml."""
    with open(GENERATION_CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def flatten_generation_config(config):
    """Flatten nested generation config into key-value pairs for settings DB.

    Turns nested keys like lm.thinking into 'lm_thinking'.
    """
    flat = {}
    for key, value in config.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat[f"{key}_{sub_key}"] = sub_value
        else:
            flat[key] = value
    return flat


# ---------------------------------------------------------------------------
# YAML write-back (requires ruamel.yaml)
# ---------------------------------------------------------------------------


def _load_ruamel_yaml(filepath):
    """Load a YAML file preserving comments and formatting."""
    from ruamel.yaml import YAML

    ry = YAML()
    ry.preserve_quotes = True
    with open(filepath, encoding="utf-8") as f:
        return ry, ry.load(f)


def _load_or_create_ruamel_yaml(filepath, default: dict):
    """Load a YAML file if it exists, otherwise return a fresh instance with default data."""
    if filepath.exists():
        return _load_ruamel_yaml(filepath)
    from ruamel.yaml import YAML
    ry = YAML()
    ry.preserve_quotes = True
    return ry, default


def _save_ruamel_yaml(filepath, ry, data):
    """Save a YAML file preserving comments and formatting."""
    with open(filepath, "w", encoding="utf-8") as f:
        ry.dump(data, f)


def save_categories_config(categories_dict):
    """Write the full categories dict back to categories.yaml."""
    ry, data = _load_ruamel_yaml(CATEGORIES_CONFIG_PATH)
    data["categories"] = categories_dict
    _save_ruamel_yaml(CATEGORIES_CONFIG_PATH, ry, data)


def update_category_field(category_id, field, value):
    """Update a single field on a category in categories.yaml."""
    ry, data = _load_ruamel_yaml(CATEGORIES_CONFIG_PATH)
    cats = data.get("categories", {})
    if category_id not in cats:
        return False
    cats[category_id][field] = value
    _save_ruamel_yaml(CATEGORIES_CONFIG_PATH, ry, data)
    return True


def add_category_to_yaml(category_id, category_data):
    """Add a new category to both categories.yaml and genre.yaml."""
    # Add to categories.yaml
    ry, data = _load_ruamel_yaml(CATEGORIES_CONFIG_PATH)
    cats = data.get("categories", {})
    cats[category_id] = category_data
    _save_ruamel_yaml(CATEGORIES_CONFIG_PATH, ry, data)

    # Add empty variants section to genre.yaml
    gry, gdata = _load_ruamel_yaml(GENRE_CONFIG_PATH)
    genres = gdata.get("genres", {})
    if category_id not in genres:
        genres[category_id] = {"variants": {}}
        _save_ruamel_yaml(GENRE_CONFIG_PATH, gry, gdata)


def remove_category_from_yaml(category_id):
    """Remove a category from categories and genre YAMLs (user and core)."""
    for path in (CATEGORIES_USER_CONFIG_PATH, CATEGORIES_CONFIG_PATH):
        if not path.exists():
            continue
        ry, data = _load_ruamel_yaml(path)
        cats = data.get("categories", {})
        if category_id in cats:
            cats.pop(category_id)
            _save_ruamel_yaml(path, ry, data)

    for path in (GENRE_USER_CONFIG_PATH, GENRE_CONFIG_PATH):
        if not path.exists():
            continue
        ry, data = _load_ruamel_yaml(path)
        genres = data.get("genres", {})
        if category_id in genres:
            genres.pop(category_id)
            _save_ruamel_yaml(path, ry, data)


def update_category_in_yaml(category_id, fields):
    """Update multiple fields on a category in categories.yaml."""
    ry, data = _load_ruamel_yaml(CATEGORIES_CONFIG_PATH)
    cats = data.get("categories", {})
    if category_id not in cats:
        return False
    for key, value in fields.items():
        cats[category_id][key] = value
    _save_ruamel_yaml(CATEGORIES_CONFIG_PATH, ry, data)
    return True


def save_genre_variant(category, variant_id, fields):
    """Update fields on a genre variant in genre.yaml."""
    ry, data = _load_ruamel_yaml(GENRE_CONFIG_PATH)
    genres = data.get("genres", {})
    if category not in genres:
        return False
    variants = genres[category].get("variants", {})
    if variant_id not in variants:
        return False
    for key, value in fields.items():
        variants[variant_id][key] = value
    _save_ruamel_yaml(GENRE_CONFIG_PATH, ry, data)
    return True


def add_genre_variant_to_yaml(category, variant_id, variant_data):
    """Add a new genre variant to genre.yaml under the given category."""
    ry, data = _load_ruamel_yaml(GENRE_CONFIG_PATH)
    genres = data.get("genres", {})
    if category not in genres:
        genres[category] = {"variants": {}}
    variants = genres[category].get("variants", {})
    variants[variant_id] = variant_data
    if "variants" not in genres[category]:
        genres[category]["variants"] = variants
    _save_ruamel_yaml(GENRE_CONFIG_PATH, ry, data)


# ---------------------------------------------------------------------------
# Generator profile and pool loading
# ---------------------------------------------------------------------------


def load_generator_profile(profile_name):
    """Load a generator profile YAML, checking core then packs directories."""
    for base in (GENERATORS_DIR, GENERATORS_PACKS_DIR):
        path = base / "profiles" / f"{profile_name}.yaml"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)
    return None


def load_pool_file(category, filename):
    """Load a word pool .txt file, checking core, packs, then _shared.

    Returns a list of non-empty lines.
    """
    for pools_dir in (GENERATORS_DIR / "pools", GENERATORS_PACKS_DIR / "pools"):
        cat_path = pools_dir / category / filename
        if cat_path.exists():
            return _read_pool(cat_path)

    shared_path = GENERATORS_DIR / "pools" / "_shared" / filename
    if shared_path.exists():
        return _read_pool(shared_path)

    logger.warning("Pool file not found: %s (category: %s)", filename, category)
    return []


def _read_pool(path):
    """Read a pool .txt file into a list of non-empty stripped lines."""
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_prompt_file(filename):
    """Load a prompt .txt file, checking core then packs directories."""
    for base in (GENERATORS_DIR, GENERATORS_PACKS_DIR):
        path = base / "prompts" / filename
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return f.read()
    return None
