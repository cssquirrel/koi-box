"""Artist bio generation using Qwen 2.5-3B (same model as lyrics)."""

import gc
import logging

from src.config import MODELS_DIR, get_category_config, load_prompt_file
from src.database import get_db, get_setting

logger = logging.getLogger(__name__)

MODEL_FILE = "qwen2.5-3b-instruct-q5_k_m.gguf"
MODEL_PATH = MODELS_DIR / MODEL_FILE

_FALLBACK_SYSTEM_PROMPT = """\
You write short artist bios for fictional musicians in the style of Spotify artist descriptions.

RULES:
1. Write 2-3 sentences in English.
2. Reference the artist's sound and aesthetic.
3. Keep the tone evocative and concise.
4. Do NOT use quotation marks.
5. Do NOT include the artist's name anywhere in the bio.
6. The bio must start with a complete sentence that makes sense on its own — do NOT begin with a verb or phrase that continues off the artist's name.
7. Do NOT name-drop other artists, musicians, bands, directors, or films. Describe the sound without referencing specific people or works.

OUTPUT: Return ONLY the bio text, nothing else."""


def _load_bio_config(category):
    """Load bio configuration for a category from categories.yaml."""
    cat_config = get_category_config(category)
    bio_config = cat_config.get("bio_config", {})

    prompt_file = bio_config.get("system_prompt_file", "")
    system_prompt = load_prompt_file(prompt_file) if prompt_file else None
    if not system_prompt:
        system_prompt = _FALLBACK_SYSTEM_PROMPT

    return {
        "system_prompt": system_prompt,
        "max_tokens": bio_config.get("max_tokens", 200),
    }


def _load_model():
    """Load the Qwen model for bio generation."""
    from llama_cpp import Llama

    if not MODEL_PATH.exists():
        logger.error("Model not found: %s — cannot generate bio", MODEL_PATH)
        return None

    logger.info("Loading bio LLM...")
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_gpu_layers=-1,
        n_ctx=2048,
        verbose=False,
    )
    logger.info("Bio LLM loaded.")
    return llm


def _unload_model(llm):
    """Free model resources and VRAM."""
    if llm is not None:
        del llm
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass
    logger.info("Bio LLM unloaded.")


def get_artist_bio(artist_name):
    """Return an existing bio if one has been generated.

    Returns bio string or None.  Generation is triggered separately
    when an artist's first track is favorited.
    """
    db = get_db()
    row = db.execute(
        "SELECT bio FROM artist_bios WHERE artist_name = ?",
        (artist_name,),
    ).fetchone()
    return row["bio"] if row else None


def generate_artist_bio(artist_name, genre_id, category):
    """Generate a bio using Qwen and store it in the DB."""
    from src.services.llm_lock import llm_lock

    config = _load_bio_config(category)

    # Get genre caption for context
    db = get_db()
    genre = db.execute(
        "SELECT caption, description FROM genres WHERE id = ?",
        (genre_id,),
    ).fetchone()
    caption = genre["caption"] if genre else category

    with llm_lock:
        llm = _load_model()
        if not llm:
            return None

        try:
            bio = _generate_raw(
                llm, artist_name, caption,
                config["system_prompt"], config["max_tokens"],
            )
            if bio:
                db.execute(
                    """INSERT OR REPLACE INTO artist_bios
                       (artist_name, bio, genre_id) VALUES (?, ?, ?)""",
                    (artist_name, bio, genre_id),
                )
                db.commit()
                logger.info("Generated bio for %s (%d chars)", artist_name, len(bio))
                return bio
        except Exception as e:
            logger.warning("Bio generation failed for %s: %s", artist_name, e)
        finally:
            _unload_model(llm)

    return None


def _generate_raw(llm, artist_name, caption, system_prompt, max_tokens):
    """Run the LLM and return the bio text."""
    user_msg = (
        f"Write a bio for the fictional artist: {artist_name}\n"
        f"Genre style: {caption}\n"
        f"Do NOT include the artist's name in the bio. "
        f"Start with a complete, self-contained sentence."
    )

    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.85,
        max_tokens=max_tokens,
        top_p=0.92,
    )

    raw = response["choices"][0]["message"]["content"].strip()

    # Clean up common LLM artifacts
    raw = raw.strip('"').strip("'")
    raw = _strip_leading_name(raw, artist_name)

    return raw if len(raw) > 20 else None


def _strip_leading_name(text, artist_name):
    """Remove artist name from the start and fix dangling continuations."""
    import re

    # Strip exact name prefix
    if text.lower().startswith(artist_name.lower()):
        text = text[len(artist_name):].lstrip(" :-–—,").strip()

    # Also try first/last name fragments
    parts = artist_name.split()
    for part in parts:
        if len(part) > 2 and text.lower().startswith(part.lower()):
            after = text[len(part):]
            if after and after[0] in " :-–—,":
                text = after.lstrip(" :-–—,").strip()

    # If the result starts with a lowercase word (dangling verb/adjective),
    # capitalize it to form a proper sentence
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    return text
