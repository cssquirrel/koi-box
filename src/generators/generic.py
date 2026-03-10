"""Generic name generator — driven by YAML profiles and .txt pool files.

Used by categories with generator: profile in categories.yaml.
Loads a profile from config/generators/profiles/ and word pools from
config/generators/pools/{category}/ (falling back to _shared/).
"""

import logging
import random
import re
from functools import lru_cache

from src.config import load_generator_profile, load_pool_file

logger = logging.getLogger(__name__)


@lru_cache(maxsize=16)
def _cached_profile(profile_name):
    """Load and cache a generator profile."""
    return load_generator_profile(profile_name)


def _load_pools(category, pool_refs):
    """Load all pool files referenced by a profile section.

    Returns dict: {slot_name: [words...]}.
    """
    pools = {}
    for slot_name, filename in pool_refs.items():
        words = load_pool_file(category, filename)
        if words:
            pools[slot_name] = words
        else:
            logger.warning("Empty pool for slot '%s' (file: %s)", slot_name, filename)
    return pools


def _fill_template(template, pools):
    """Fill a template string with random picks from pools.

    Template uses {slot_name} placeholders.
    Returns None if any slot can't be filled.
    """
    def replacer(match):
        slot = match.group(1)
        if slot not in pools or not pools[slot]:
            return None
        return random.choice(pools[slot])

    result = template
    slots = re.findall(r"\{(\w+)\}", template)
    for slot in slots:
        if slot not in pools or not pools[slot]:
            return None
        result = result.replace("{" + slot + "}", random.choice(pools[slot]), 1)
    return result


def _title_case(text):
    """Title-case a name, preserving short words and all-caps tokens."""
    small = {"a", "an", "the", "of", "in", "on", "at", "to", "for", "and", "but", "or"}
    words = text.split()
    result = []
    for i, w in enumerate(words):
        # Preserve all-caps tokens (roman numerals, acronyms)
        if w.isupper() and len(w) > 1:
            result.append(w)
        elif i == 0 or w.strip("(").lower() not in small:
            # Capitalize first alpha char, handling leading punctuation
            caps = ""
            for j, ch in enumerate(w):
                if ch.isalpha():
                    caps = w[:j] + ch.upper() + w[j + 1:]
                    break
            result.append(caps or w)
        else:
            result.append(w.lower())
    return " ".join(result)


def _romanize_korean(text):
    """Append romanization if text contains Korean characters.

    Returns the original text unchanged if no Korean is detected,
    so non-Korean categories are unaffected.  For feat. strings,
    only the Korean portion before the parenthetical is romanized.
    """
    if not re.search(r"[\uAC00-\uD7AF\u3130-\u318F]", text):
        return text
    try:
        from korean_romanizer.romanizer import Romanizer
        # Split off feat. suffix so we don't double-parenthetical
        feat_match = re.match(r"^(.+?)(\s*\(feat\..+\))$", text, re.IGNORECASE)
        if feat_match:
            base, feat_part = feat_match.group(1), feat_match.group(2)
            romanized = Romanizer(base).romanize().strip()
            return f"{base} ({_title_case(romanized)}){feat_part}"
        romanized = Romanizer(text).romanize().strip()
        return f"{text} ({_title_case(romanized)})"
    except Exception:
        return text


def generate_track_name(category, profile_name):
    """Generate a track name using a generic profile.

    Returns a title-cased track name string.
    """
    profile = _cached_profile(profile_name)
    if not profile or "track_names" not in profile:
        return _fallback("Untitled Track")

    section = profile["track_names"]
    templates = section.get("templates", [])
    pool_refs = section.get("pools", {})

    if not templates:
        return _fallback("Untitled Track")

    pools = _load_pools(category, pool_refs)

    # Try up to 5 times to fill a template
    for _ in range(5):
        template = random.choice(templates)
        result = _fill_template(template, pools)
        if result:
            return _title_case(result)

    return _fallback("Untitled Track")


def generate_artist_name(category, profile_name):
    """Generate an artist name using a generic profile.

    Handles feat. collaborations based on feat_chance.
    """
    profile = _cached_profile(profile_name)
    if not profile or "artist_names" not in profile:
        return _fallback("Unknown Artist")

    section = profile["artist_names"]
    templates = section.get("templates", [])
    pool_refs = section.get("pools", {})
    feat_chance = section.get("feat_chance", 0.0)
    feat_templates = section.get("feat_templates", [])

    if not templates:
        return _fallback("Unknown Artist")

    pools = _load_pools(category, pool_refs)

    # Generate base name
    base_name = None
    for _ in range(5):
        template = random.choice(templates)
        result = _fill_template(template, pools)
        if result:
            base_name = _title_case(result)
            break

    if not base_name:
        return _fallback("Unknown Artist")

    # Optionally add feat.
    if feat_templates and random.random() < feat_chance:
        feat_pools = dict(pools)
        feat_pools["name"] = [base_name]
        for _ in range(3):
            ft = random.choice(feat_templates)
            result = _fill_template(ft, feat_pools)
            if result:
                return _romanize_korean(result)

    return _romanize_korean(base_name)


def generate_album_name(category, profile_name):
    """Generate an album name using a generic profile."""
    profile = _cached_profile(profile_name)
    if not profile or "album_names" not in profile:
        return _fallback("Untitled Album")

    section = profile["album_names"]
    templates = section.get("templates", [])
    pool_refs = section.get("pools", {})

    if not templates:
        return _fallback("Untitled Album")

    pools = _load_pools(category, pool_refs)

    for _ in range(5):
        template = random.choice(templates)
        result = _fill_template(template, pools)
        if result:
            return _title_case(result)

    return _fallback("Untitled Album")


def _fallback(default):
    """Return a simple fallback name."""
    fallbacks = [
        "Midnight Drift", "Foggy Windows", "Paper Lanterns",
        "Rooftop Rain", "Neon Puddles", "Late Bus Home",
    ]
    return random.choice(fallbacks) if default == "Untitled Track" else default
