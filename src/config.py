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
DB_PATH = PROJECT_ROOT / "koibokksu.db"
MODELS_DIR = PROJECT_ROOT / "models"
GENRE_CONFIG_PATH = CONFIG_DIR / "genre.yaml"
GENERATION_CONFIG_PATH = CONFIG_DIR / "generation.yaml"
CATEGORIES_CONFIG_PATH = CONFIG_DIR / "categories.yaml"
GENERATORS_DIR = CONFIG_DIR / "generators"
ALBUM_COVERS_DIR = PROJECT_ROOT / "album_covers"

# Ensure directories exist
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Categories config
# ---------------------------------------------------------------------------


def load_categories_config():
    """Load category definitions from categories.yaml.

    Returns dict: {category_name: {display_name, colors, generator, ...}}.
    """
    if not CATEGORIES_CONFIG_PATH.exists():
        return {}
    with open(CATEGORIES_CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("categories", {})


def get_category_config(category):
    """Return config dict for a single category, or empty dict."""
    return load_categories_config().get(category, {})


# ---------------------------------------------------------------------------
# Genre config
# ---------------------------------------------------------------------------


def load_genre_config():
    """Load genre definitions from genre.yaml.

    Returns the nested structure: {category: {variants: {variant_id: data}}}.
    """
    with open(GENRE_CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("genres", {})


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
    """Remove a category from both categories.yaml and genre.yaml."""
    # Remove from categories.yaml
    ry, data = _load_ruamel_yaml(CATEGORIES_CONFIG_PATH)
    cats = data.get("categories", {})
    cats.pop(category_id, None)
    _save_ruamel_yaml(CATEGORIES_CONFIG_PATH, ry, data)

    # Remove from genre.yaml
    gry, gdata = _load_ruamel_yaml(GENRE_CONFIG_PATH)
    genres = gdata.get("genres", {})
    genres.pop(category_id, None)
    _save_ruamel_yaml(GENRE_CONFIG_PATH, gry, gdata)


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
    """Load a generator profile YAML from config/generators/profiles/."""
    path = GENERATORS_DIR / "profiles" / f"{profile_name}.yaml"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_pool_file(category, filename):
    """Load a word pool .txt file, checking category dir then _shared.

    Returns a list of non-empty lines.
    """
    pools_dir = GENERATORS_DIR / "pools"

    # Try category-specific first
    cat_path = pools_dir / category / filename
    if cat_path.exists():
        return _read_pool(cat_path)

    # Fall back to shared
    shared_path = pools_dir / "_shared" / filename
    if shared_path.exists():
        return _read_pool(shared_path)

    logger.warning("Pool file not found: %s (category: %s)", filename, category)
    return []


def _read_pool(path):
    """Read a pool .txt file into a list of non-empty stripped lines."""
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_prompt_file(filename):
    """Load a prompt .txt file from config/generators/prompts/."""
    path = GENERATORS_DIR / "prompts" / filename
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()
