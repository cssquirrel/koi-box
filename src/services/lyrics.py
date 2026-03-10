"""Dynamic lyrics generation using a local LLM (Qwen 2.5-3B Instruct).

Generates Japanese lyrics for city pop variants with dynamic_lyrics=true,
fills template placeholders, and returns completed lyrics ready for ACE-Step.

Adapted from prototype/lyrics/lyrics_generator.py — made data-driven so
prompts are built from genre.yaml fields rather than hardcoded.
"""

import gc
import json
import logging
import random
import re
import unicodedata
from pathlib import Path
from typing import Optional

import requests
from tqdm import tqdm

from src.config import MODELS_DIR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

MODEL_REPO = "Qwen/Qwen2.5-3B-Instruct-GGUF"
MODEL_FILE = "qwen2.5-3b-instruct-q5_k_m.gguf"
MODEL_URL = f"https://huggingface.co/{MODEL_REPO}/resolve/main/{MODEL_FILE}"
MODEL_PATH = MODELS_DIR / MODEL_FILE

# Default morae limits (used when no category config provides overrides)
_DEFAULT_MORAE_MIN = 4
_DEFAULT_MORAE_MAX = 14
_DEFAULT_MAX_CHARS = 25

# Default placeholder lyrics (used when no category config provides overrides)
_DEFAULT_PLACEHOLDER_LYRICS = [
    "ああ夜が来る",
    "風が呼んでる",
    "夢の続きを",
    "光の中へ",
    "このまま二人",
    "街が眠る頃",
    "遠い記憶に",
    "瞳を閉じて",
]

# Hardcoded fallback system prompt (used only if prompt file is missing)
_FALLBACK_SYSTEM_PROMPT = """\
You are a Japanese lyricist specializing in 1980s City Pop songwriting.

RULES:
1. Write all lyrics in Japanese using natural hiragana, katakana, and kanji.
2. Each line should be SHORT — aim for 3 to 7 Japanese characters. This is critical.
3. Chorus lines must be singable and emotionally direct.
4. Maintain ONE core image per song. Do not mix unrelated imagery.
5. Include at most 1-2 English loanwords per song (e.g. ドライブ, ネオン).
6. AVOID: long sentences, excessive loanwords, abstract stacking.

EXAMPLE of correct line lengths:
LYRICS_VERSE_1_LINE_1: 雨の街角で
LYRICS_VERSE_1_LINE_2: 君を待ってた
LYRICS_VERSE_1_LINE_3: ネオンが揺れる
LYRICS_VERSE_1_LINE_4: 息が白くて
LYRICS_CHORUS_LINE_1: 夜に溶けたい
LYRICS_CHORUS_LINE_2: 踊り続けて
LYRICS_CHORUS_LINE_3: この手離さないで
LYRICS_CHORUS_LINE_4: 朝まで二人

OUTPUT FORMAT — return ONLY lines in this exact format, nothing else:
LYRICS_SLOT_NAME: (short japanese text)

Do NOT include any explanation, markdown, or extra text. ONLY the key: value lines."""


def _load_lyrics_config(category):
    """Load lyrics configuration for a category from categories.yaml.

    Returns dict with: system_prompt, language, morae_min, morae_max,
    max_chars, placeholder_lyrics.
    """
    from src.config import get_category_config, load_prompt_file

    cat_config = get_category_config(category)
    lyrics_config = cat_config.get("lyrics_config", {})

    # Load system prompt from file
    prompt_file = lyrics_config.get("system_prompt_file", "")
    system_prompt = None
    if prompt_file:
        system_prompt = load_prompt_file(prompt_file)
    if not system_prompt:
        system_prompt = _FALLBACK_SYSTEM_PROMPT

    return {
        "system_prompt": system_prompt,
        "language": lyrics_config.get("language", "japanese"),
        "morae_min": lyrics_config.get("morae_min", _DEFAULT_MORAE_MIN),
        "morae_max": lyrics_config.get("morae_max", _DEFAULT_MORAE_MAX),
        "max_chars": lyrics_config.get("max_chars", _DEFAULT_MAX_CHARS),
        "placeholder_lyrics": lyrics_config.get("placeholder_lyrics", _DEFAULT_PLACEHOLDER_LYRICS),
    }

# ---------------------------------------------------------------------------
# Morae counting (improved from prototype with kanji lookup)
# ---------------------------------------------------------------------------

_COMBO_KANA = set("ゃゅょャュョぁぃぅぇぉァィゥェォ")

_MORA_CHARS = set()
for _start, _end in [
    (0x3041, 0x3096),  # Hiragana
    (0x30A1, 0x30F6),  # Katakana
]:
    for _c in range(_start, _end + 1):
        _MORA_CHARS.add(chr(_c))
_MORA_CHARS.update({"ん", "ン", "っ", "ッ", "ー"})

# Mora counts for common kanji found in city pop lyrics.
# Without MeCab we can't know the reading, so this covers the most
# frequent kanji with their most common standalone reading length.
# Unlisted kanji fall back to the 1.5 estimate (rounded down to 1).
_KANJI_MORAE = {
    # 1-mora kanji (single kana reading)
    "目": 1, "手": 1, "日": 1, "火": 1, "木": 1, "気": 1, "血": 1,
    "歯": 1, "葉": 1, "名": 1, "字": 1, "戸": 1, "身": 1, "実": 1,
    "絵": 1, "根": 1, "瀬": 1, "背": 1, "矢": 1, "湯": 1, "尾": 1,
    "帆": 1, "穂": 1, "井": 1, "蚊": 1, "藻": 1,
    # 2-mora kanji (common readings)
    "夜": 2, "雨": 2, "風": 2, "空": 2, "海": 2, "星": 2, "月": 2,
    "花": 2, "雪": 2, "声": 2, "色": 2, "音": 2, "影": 2, "街": 2,
    "波": 2, "朝": 2, "春": 2, "夏": 2, "秋": 2, "冬": 2, "恋": 2,
    "愛": 2, "夢": 2, "人": 2, "君": 2, "僕": 2, "私": 2, "今": 2,
    "酒": 2, "道": 2, "窓": 2, "駅": 2, "雲": 2, "嘘": 2, "胸": 2,
    "腕": 2, "指": 2, "顔": 2, "口": 2, "耳": 2, "首": 2, "足": 2,
    "傘": 2, "橋": 2, "島": 2, "森": 2, "川": 2, "山": 2, "石": 2,
    "鳥": 2, "猫": 2, "犬": 2, "魚": 2, "歌": 2, "踊": 2, "光": 2,
    "闇": 2, "白": 2, "黒": 2, "赤": 2, "青": 2, "上": 2, "下": 2,
    "中": 2, "前": 2, "後": 2, "北": 2, "南": 2, "東": 2, "西": 2,
    "町": 2, "村": 2, "国": 2, "店": 2, "部": 2, "車": 2, "船": 2,
    "水": 2, "砂": 2, "塩": 2, "肩": 2, "涙": 2, "汗": 2, "息": 2,
    "泣": 1, "笑": 1, "走": 1, "飛": 1, "乗": 1, "待": 1, "合": 1,
    "降": 1, "持": 1, "知": 1, "見": 1, "聞": 1, "言": 1, "思": 1,
    "信": 2, "号": 2, "線": 2, "煙": 2, "鏡": 2, "壁": 2, "扉": 2,
    "鍵": 2, "時": 2, "場": 2, "力": 2, "心": 2,
    # 3-mora kanji
    "光": 3, "鏡": 3, "心": 3, "緑": 3, "命": 3, "姿": 3, "港": 3,
    "桜": 3, "嵐": 3, "形": 3, "力": 3, "昔": 3, "体": 3, "頭": 3,
    "眠": 3,
}


def count_morae(text: str) -> int:
    """Count morae in a Japanese text string.

    Uses a lookup table for common kanji. Unlisted kanji default to 1
    mora (deliberately conservative to avoid over-rejection).
    """
    morae = 0
    for char in text:
        if char in _COMBO_KANA:
            continue
        if char in _MORA_CHARS:
            morae += 1
        elif unicodedata.category(char).startswith("Lo"):
            morae += _KANJI_MORAE.get(char, 1)
    return morae


# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------


def download_model(force: bool = False) -> Path:
    """Download the GGUF model if not already present."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists() and not force:
        logger.info("Model already downloaded: %s", MODEL_PATH)
        return MODEL_PATH

    logger.info("Downloading model from %s ...", MODEL_URL)
    response = requests.get(MODEL_URL, stream=True, timeout=30)
    response.raise_for_status()
    total = int(response.headers.get("content-length", 0))

    tmp_path = MODEL_PATH.with_suffix(".part")
    with open(tmp_path, "wb") as f:
        with tqdm(total=total, unit="B", unit_scale=True, desc=MODEL_FILE) as pbar:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                pbar.update(len(chunk))

    tmp_path.rename(MODEL_PATH)
    logger.info("Model saved to %s", MODEL_PATH)
    return MODEL_PATH


def _load_model(n_gpu_layers: int = -1, n_ctx: int = 2048):
    """Load the Qwen model. Returns a Llama instance."""
    from llama_cpp import Llama

    if not MODEL_PATH.exists():
        download_model()

    logger.info("Loading lyrics LLM (GPU layers: %s) ...", n_gpu_layers)
    llm = Llama(
        model_path=str(MODEL_PATH),
        n_gpu_layers=n_gpu_layers,
        n_ctx=n_ctx,
        verbose=False,
    )
    logger.info("Lyrics LLM loaded.")
    return llm


def _unload_model(llm) -> None:
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
    logger.info("Lyrics LLM unloaded, VRAM released.")


# ---------------------------------------------------------------------------
# Prompt building (data-driven from genre YAML fields)
# ---------------------------------------------------------------------------


def _detect_slots(lyrics_template: str) -> list[str]:
    """Extract {LYRICS_*} placeholder names from a lyrics template."""
    # Use a set to deduplicate (chorus lines repeat in templates)
    seen = set()
    slots = []
    for match in re.finditer(r"\{(LYRICS_[A-Z0-9_]+)\}", lyrics_template):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            slots.append(name)
    return slots


# Section descriptions to give the LLM creative direction per section type
_SECTION_HINTS = {
    "VERSE_1": "scene-setting, narrative setup",
    "VERSE_2": "narrative development, deepening",
    "CHORUS": "catchy singable hook, emotional core",
    "PRECHORUS": "building tension, anticipation",
    "PRECHORUS_1": "building tension, anticipation",
    "PRECHORUS_2": "building tension, varied from prechorus 1",
    "BRIDGE": "intimate, vulnerable, contrast",
}


def _build_slot_instructions(slots: list[str]) -> str:
    """Build human-readable slot fill instructions from slot names."""
    sections: dict[str, list[str]] = {}
    for slot in slots:
        parts = slot.replace("LYRICS_", "").rsplit("_LINE_", 1)
        section = parts[0] if len(parts) == 2 else slot.replace("LYRICS_", "")
        sections.setdefault(section, []).append(slot)

    lines = ["Fill these slots (each line should be 3-7 Japanese characters):"]
    for section, section_slots in sections.items():
        first = section_slots[0]
        last = section_slots[-1]
        count = len(section_slots)
        hint = _SECTION_HINTS.get(section, "")
        hint_str = f" — {hint}" if hint else ""
        lines.append(f"{first} through {last} ({count} lines{hint_str})")
    return "\n".join(lines)


def _build_user_prompt(genre_row, slots: list[str], theme_seed: str | None) -> str:
    """Build the complete user prompt from genre data and detected slots."""
    variant_id = genre_row["id"]
    guidance = genre_row["lyrics_guidance"] if genre_row["lyrics_guidance"] else ""
    caption = genre_row["caption"]

    parts = [
        f"Generate Japanese City Pop lyrics for the {variant_id} template.",
        f"STYLE TAGS: {caption}",
    ]
    if guidance:
        parts.append(guidance)

    parts.append(_build_slot_instructions(slots))

    if theme_seed:
        parts.append(
            f"The verse opens with the line: 「{theme_seed}」\n"
            "Continue from this image — all lines should feel connected to this opening."
        )

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Generation and parsing
# ---------------------------------------------------------------------------


def _generate_raw(llm, genre_row, slots, theme_seed=None, temperature=0.9,
                  max_tokens=512, system_prompt=None) -> str:
    """Run the LLM and return raw text output."""
    user_msg = _build_user_prompt(genre_row, slots, theme_seed)
    prompt = system_prompt or _FALLBACK_SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": user_msg},
    ]

    response = llm.create_chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=0.92,
        repeat_penalty=1.1,
    )
    return response["choices"][0]["message"]["content"]


def _parse_lyrics(raw_output: str, expected_slots: set[str]) -> dict[str, str]:
    """Parse LLM output into {slot_name: lyric_line} dict."""
    result = {}
    cleaned = raw_output.strip()
    cleaned = re.sub(r"^```[a-z]*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```$", "", cleaned)
    cleaned = cleaned.strip()

    for line in cleaned.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^(LYRICS_[A-Z0-9_]+)\s*[:：]\s*(.+)$", line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            if key in expected_slots:
                result[key] = value
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationError:
    """A single validation failure."""

    def __init__(self, slot: str, issue: str, value: str = ""):
        self.slot = slot
        self.issue = issue
        self.value = value

    def __repr__(self):
        return f"ValidationError({self.slot}: {self.issue})"


def _validate_lyrics(lyrics: dict[str, str], expected_slots: list[str],
                     morae_min: int = _DEFAULT_MORAE_MIN,
                     morae_max: int = _DEFAULT_MORAE_MAX,
                     max_chars: int = _DEFAULT_MAX_CHARS,
                     language: str = "japanese") -> tuple[bool, list[ValidationError]]:
    """Validate parsed lyrics against constraints.

    language="japanese" enforces Japanese character checks and morae counting.
    language="any" skips language-specific validation (only checks emptiness/length).
    """
    errors = []

    for slot in expected_slots:
        if slot not in lyrics:
            errors.append(ValidationError(slot, "missing"))

    for slot, line in lyrics.items():
        if not line.strip():
            errors.append(ValidationError(slot, "empty", line))
            continue

        if language == "japanese":
            has_japanese = any(
                "\u3040" <= c <= "\u309f"
                or "\u30a0" <= c <= "\u30ff"
                or "\u4e00" <= c <= "\u9fff"
                for c in line
            )
            if not has_japanese:
                errors.append(ValidationError(slot, "no_japanese", line))
                continue

            morae = count_morae(line)
            if morae < morae_min:
                errors.append(ValidationError(slot, f"too_short ({morae} morae)", line))
            elif morae > morae_max:
                errors.append(ValidationError(slot, f"too_long ({morae} morae)", line))

        if len(line) > max_chars:
            errors.append(ValidationError(slot, f"too_many_chars ({len(line)})", line))

    return len(errors) == 0, errors


# ---------------------------------------------------------------------------
# Template filling
# ---------------------------------------------------------------------------


def _fill_template(template_lyrics: str, lyrics: dict[str, str]) -> str:
    """Replace {PLACEHOLDER} slots in a lyrics template with actual lyrics."""
    filled = template_lyrics
    for key, value in lyrics.items():
        filled = filled.replace(f"{{{key}}}", value)
    return filled


def _has_unfilled_slots(lyrics_text: str) -> list[str]:
    """Check for any remaining {LYRICS_*} placeholders."""
    return re.findall(r"\{(LYRICS_[A-Z0-9_]+)\}", lyrics_text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_lyrics_for_genre(genre_row, max_retries: int = 3,
                              temperature: float = 0.9,
                              category: str | None = None) -> str:
    """Generate lyrics for a dynamic_lyrics genre, returning filled lyrics string.

    Full cycle: load model -> pick theme seed -> generate -> validate ->
    fill template -> unload model.

    Args:
        genre_row: Database row (or dict) with genre fields including
                   lyrics, lyrics_guidance, theme_seeds, caption, id.
        max_retries: Max generation attempts on validation failure.
        temperature: Starting sampling temperature.
        category: Category name for loading lyrics config. If None, looked
                  up from the genre's category field.

    Returns:
        Filled lyrics string ready for ACE-Step submission.

    Raises:
        RuntimeError: If all retries fail.
    """
    # Load category-specific lyrics config
    try:
        cat = category or genre_row["category"]
    except (KeyError, IndexError):
        cat = "citypop"
    lyrics_config = _load_lyrics_config(cat)
    placeholder_lyrics = lyrics_config["placeholder_lyrics"]

    template_lyrics = genre_row["lyrics"]

    # Pick a random theme seed
    theme_seeds_raw = genre_row["theme_seeds"]
    if isinstance(theme_seeds_raw, str):
        theme_seeds = json.loads(theme_seeds_raw)
    else:
        theme_seeds = theme_seeds_raw or []
    theme_seed = random.choice(theme_seeds) if theme_seeds else None

    # Pre-fill {THEME_SEED} in the template (not an LLM-generated slot)
    if "{THEME_SEED}" in template_lyrics:
        seed = theme_seed or random.choice(placeholder_lyrics)
        template_lyrics = template_lyrics.replace("{THEME_SEED}", seed)

    # Detect remaining LYRICS_* slots for LLM to fill
    slots = _detect_slots(template_lyrics)

    if not slots:
        logger.info("No LYRICS_* placeholders found, returning template as-is.")
        return template_lyrics

    logger.info("Generating lyrics for %s (theme: %s, slots: %d)",
                genre_row["id"], theme_seed, len(slots))

    from src.services.llm_lock import llm_lock

    with llm_lock:
        llm = _load_model()
        try:
            filled = _generate_with_retries(
                llm, genre_row, slots, template_lyrics, theme_seed,
                max_retries, temperature, lyrics_config
            )
        finally:
            _unload_model(llm)

    return filled


def _generate_with_retries(llm, genre_row, slots, template_lyrics,
                           theme_seed, max_retries, temperature,
                           lyrics_config=None):
    """Generate and validate lyrics with retry logic and best-effort fallback.

    If strict validation passes, returns immediately. Otherwise, tracks the
    best attempt (fewest errors) and uses it as a fallback after all retries.
    """
    if lyrics_config is None:
        lyrics_config = _load_lyrics_config("citypop")

    system_prompt = lyrics_config["system_prompt"]
    morae_min = lyrics_config["morae_min"]
    morae_max = lyrics_config["morae_max"]
    max_chars = lyrics_config["max_chars"]
    language = lyrics_config["language"]
    placeholder_lyrics = lyrics_config["placeholder_lyrics"]

    expected_set = set(slots)
    best_lyrics = None
    best_error_count = float("inf")

    for attempt in range(max_retries):
        temp = min(temperature + (attempt * 0.05), 1.2)
        logger.info("Lyrics attempt %d/%d (temp=%.2f)", attempt + 1, max_retries, temp)

        raw = _generate_raw(llm, genre_row, slots, theme_seed=theme_seed,
                            temperature=temp, system_prompt=system_prompt)
        logger.debug("Raw LLM output:\n%s", raw)

        lyrics = _parse_lyrics(raw, expected_set)
        logger.info("Parsed %d/%d slots", len(lyrics), len(slots))

        is_valid, errors = _validate_lyrics(
            lyrics, slots,
            morae_min=morae_min, morae_max=morae_max,
            max_chars=max_chars, language=language,
        )

        # Track best attempt (fewest errors, most slots filled)
        if len(errors) < best_error_count and len(lyrics) >= len(slots) // 2:
            best_lyrics = lyrics
            best_error_count = len(errors)

        if is_valid:
            filled = _fill_template(template_lyrics, lyrics)
            unfilled = _has_unfilled_slots(filled)
            if unfilled:
                logger.warning("Unfilled slots remain: %s", unfilled)
                continue
            logger.info("Lyrics generated and validated successfully.")
            return filled

        logger.warning("Attempt %d failed: %d errors: %s",
                       attempt + 1, len(errors), errors)

    # Best-effort fallback: use the best attempt even if not perfect
    if best_lyrics:
        logger.warning(
            "Strict validation failed after %d attempts. "
            "Using best-effort lyrics (%d errors).",
            max_retries, best_error_count,
        )
        filled = _fill_template(template_lyrics, best_lyrics)
        unfilled = _has_unfilled_slots(filled)
        if unfilled:
            for slot in unfilled:
                filled = filled.replace(
                    f"{{{slot}}}", random.choice(placeholder_lyrics)
                )
            logger.warning("Filled %d missing slots with placeholder.", len(unfilled))
        return filled

    raise RuntimeError(
        f"Failed to generate any usable lyrics after {max_retries} attempts."
    )
