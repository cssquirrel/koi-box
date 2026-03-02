"""
Lo-Fi Artist Name Generator
============================
Generates lo-fi producer/artist names using branching style paths modeled
after real naming conventions from the Chillhop, Lofi Girl, and broader
lo-fi hip-hop scene.

Approximately 1/3 of generated names are Japanese-inspired, reflecting
the genre's deep roots in Nujabes, anime culture, and East Asian aesthetics.

Styles:
  1. Compound Word          (Tomppabeats, Flamingosis, Birocratic)
  2. Misspelled Real Word   (Leavv, Kreatev, Aviino)
  3. Lowercase Cryptic      (potsu, auv, mtbrd, zake)
  4. Soft Two-Word Phrase   (Sleepy Fish, Blue Wednesday)
  5. Human Name             (Ian Ewing, Sebastian Kamae)
  6. Japanese-Inspired      (reversed names, Japanese words, romaji blends)
  7. Mood Single Word       (Idealism, Sweeps, Enluv)
  8. Playful/Surreal Combo  (Purrple Cat, Wun Two, Mama Aiuto)
  + Modifier layer: casing, punctuation (., _, :), optional "The" prefix

Every generated name is appended with " (feat. mujin 無人)".
"""

import random
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# WORD POOLS
# ============================================================================

# --- Style 1: Compound Word building blocks ---
COMPOUND_PREFIXES: list[str] = [
    "chill", "cloud", "drift", "dream", "dusk", "echo", "fern", "fog",
    "frost", "haze", "honey", "loop", "luna", "mellow", "mint", "moon",
    "moss", "mist", "night", "nova", "palm", "pine", "pixel", "plum",
    "rain", "reed", "sage", "silk", "sleep", "slow", "smoke", "snow",
    "soft", "soul", "star", "still", "stone", "sun", "tape", "tide",
    "tone", "vibe", "vinyl", "warm", "wave", "wool", "zen", "bloom",
]

COMPOUND_SUFFIXES: list[str] = [
    "beats", "wave", "drift", "loop", "tone", "craft", "fox", "cat",
    "fish", "bird", "moth", "flux", "pulse", "static", "grain", "dust",
    "bloom", "frost", "haze", "shade", "glow", "light", "field", "scape",
    "smith", "maker", "child", "soul", "mind", "heart", "song", "note",
    "keys", "strings", "brass", "wind", "leaf", "root", "seed", "grove",
    "surf", "coast", "port", "vale", "glen", "mere", "wick", "brook",
    "hop", "step", "osis", "onic", "ism", "ique", "ette", "ling",
]

# --- Style 2: Misspelling source words + transforms ---
MISSPELL_BASE_WORDS: list[str] = [
    "leaves", "creative", "visceral", "brilliant", "avian", "bloom",
    "crystal", "flicker", "gentle", "haven", "illusion", "jovial",
    "kinetic", "lucid", "mellow", "neural", "orbital", "pristine",
    "reverie", "serene", "tranquil", "velvet", "wistful", "zenith",
    "aurora", "breeze", "cipher", "delicate", "ethereal", "feline",
    "glacier", "harmony", "island", "jasmine", "lantern", "melody",
    "nebula", "opaque", "plume", "quartz", "ripple", "saffron",
    "timber", "umber", "violet", "willow", "floral", "peony",
]

# --- Style 3: Cryptic / abbreviated fragments ---
CRYPTIC_FRAGMENTS: list[str] = [
    "snt", "drp", "flx", "brk", "mnd", "vrl", "pls", "trk", "crk",
    "hzl", "frn", "wnd", "stm", "glm", "dft", "rst", "phn", "clm",
    "grv", "shd", "lft", "rfl", "srf", "cst", "thn", "wvr", "blm",
]

CRYPTIC_SHORT_WORDS: list[str] = [
    "potsu", "auv", "tulki", "enluv", "anbuu", "tesk", "hanz", "dne",
    "reph", "clou", "novu", "tomu", "liru", "selu", "kyev", "benu",
    "oku", "tavi", "zelu", "nosu", "pivu", "rilu", "fenu", "dalu",
    "vimu", "soku", "hiru", "pelu", "genu", "waku", "shou", "raku",
]

ACCENT_CHARS: dict[str, str] = {
    "e": "\u00e8", "a": "\u00e0", "o": "\u00f2", "u": "\u00f9", "i": "\u00ec",
}

# --- Style 4: Soft Two-Word Phrase pools ---
SOFT_ADJECTIVES: list[str] = [
    "sleepy", "blue", "quiet", "lazy", "slow", "soft", "warm",
    "faded", "gentle", "pale", "dim", "still", "frozen", "hidden",
    "lost", "empty", "distant", "minor", "spare", "thin", "late",
    "idle", "hazy", "cloudy", "dusty", "mossy", "rainy", "misty",
    "tired", "young", "brief", "small", "sweet", "tender", "curled",
]

SOFT_NOUNS: list[str] = [
    "fish", "fox", "cat", "bird", "moth", "bear", "rabbit", "owl",
    "wolf", "deer", "fawn", "heron", "sparrow", "crane", "beetle",
    "wednesday", "morning", "evening", "midnight", "sunday", "november",
    "needle", "thread", "pencil", "eraser", "compass", "lantern",
    "garden", "meadow", "forest", "creek", "island", "shore", "ridge",
    "cereal", "honey", "bread", "cinnamon", "lavender", "jasmine",
    "spirit", "thought", "whisper", "signal", "static", "circuit",
    "epiphany", "paradox", "almanac", "atlas", "archive", "gazette",
]

# --- Style 5: Human Name pools ---
FIRST_NAMES: list[str] = [
    "Ian", "Luke", "Evan", "Owen", "Finn", "Noel", "Hugo", "Milo",
    "Leo", "Theo", "Ezra", "Arlo", "Jonah", "Silas", "Felix", "Ellis",
    "Ada", "Iris", "Nora", "Wren", "Cleo", "Mara", "Lena", "Elsa",
    "Maya", "Suki", "Rosa", "Vera", "Alma", "June", "Pearl", "Hazel",
    "Sam", "Robin", "Alex", "Quinn", "Sage", "Kit", "Rowan", "Ash",
    "Stefan", "Henrik", "Lars", "Oskar", "Emil", "Anton", "Kasper",
    "Mateo", "Rafael", "Santiago", "Luca", "Nico", "Marco", "Dante",
]

LAST_NAMES: list[str] = [
    "Ewing", "Forebee", "Kamae", "Berrigan", "McEvoy", "Gritton",
    "Mazuera", "Muschalle", "Morim", "Karud", "Catal\u00e1", "Pecoraro",
    "Albrecht", "Lindqvist", "Bergstr\u00f6m", "S\u00f8rensen", "Kowalski",
    "Nakamura", "Ishida", "Moreau", "Delacroix", "Dubois", "Laurent",
    "Sullivan", "Calloway", "Whitfield", "Ashworth", "Fernandez",
    "Oberman", "Holmgren", "Vieira", "Tanaka", "Watanabe", "Fujimoto",
    "Choi", "Reyes", "Oliveira", "Santos", "Ikeda", "Kimura",
    "Brennan", "Cavanaugh", "Gallagher", "Okafor", "Abrams", "Voss",
]

# --- Style 6: Japanese-Inspired pools ---
JP_GIVEN_NAMES: list[str] = [
    "Haruki", "Yuki", "Ren", "Sora", "Kaito", "Haru", "Riku", "Aoi",
    "Hinata", "Akira", "Takumi", "Naoki", "Shinji", "Kenji", "Daiki",
    "Yuto", "Sota", "Hayato", "Ryota", "Kenta", "Asuka", "Mio",
    "Sakura", "Yui", "Nana", "Mei", "Riko", "Hana", "Yuna", "Saki",
    "Koharu", "Miku", "Ayumi", "Kanna", "Itsuki", "Minato", "Tsubasa",
]

JP_FAMILY_NAMES: list[str] = [
    "Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito",
    "Yamamoto", "Nakamura", "Kobayashi", "Kato", "Yoshida", "Yamada",
    "Sasaki", "Yamaguchi", "Matsumoto", "Inoue", "Kimura", "Shimizu",
    "Hayashi", "Saito", "Morita", "Ogawa", "Fujita", "Okada", "Mori",
]

JP_WORDS: list[str] = [
    # Nature
    "kumo", "ame", "yuki", "kaze", "tsuki", "hoshi", "sora", "umi",
    "kawa", "mori", "hana", "sakura", "take", "sugi", "matsu", "fuji",
    "nami", "shima", "yama", "tani", "ike", "mizu", "hi", "tsuchi",
    # Time/Season
    "aki", "natsu", "fuyu", "haru", "asa", "yoru", "y\u016bgata", "akatsuki",
    # Feelings/Abstract
    "yasuragi", "nagori", "komorebi", "wabi", "sabi", "mono", "aware",
    "ukiyo", "ikigai", "yugen", "natsukashii", "shinrin", "boketto",
    # Objects
    "ocha", "sensu", "fude", "tatami", "shoji", "noren", "chawan",
    "kasa", "fue", "koto", "shamisen", "taiko",
]

JP_PLACE_FRAGMENTS: list[str] = [
    "shibu", "shina", "naka", "kami", "shimo", "kita", "minami",
    "higashi", "nishi", "oka", "saka", "machi", "bashi", "zaka",
    "dori", "gawa", "yama", "hama", "zaki", "jima", "dera", "ji",
]

JP_SUFFIXES_FOR_BLEND: list[str] = [
    "beats", "wave", "loop", "tone", "flux", ".wav", "sound",
    "tape", "keys", "dust", "mist", "fog", "dew", "ash",
]

JP_PREFIXES_FOR_BLEND: list[str] = [
    "lo", "hi", "neo", "sub", "re", "un", "de", "pre",
]

# --- Style 7: Mood Single Word pools ---
MOOD_WORDS: list[str] = [
    "idealism", "reverie", "solace", "serenity", "patience", "absence",
    "refuge", "tremor", "echoes", "remains", "sweeps", "drifts",
    "currents", "tides", "phases", "orbits", "layers", "traces",
    "blurs", "folds", "curves", "angles", "edges", "loops",
    "stillness", "warmth", "distance", "clarity", "hush", "murmur",
    "presence", "flicker", "glimmer", "shimmer", "whisper", "linger",
    "ether", "aether", "liminal", "penumbra", "patina", "residue",
    "vapor", "mirage", "verve", "meridian", "haven", "alcove",
]

# --- Style 8: Playful/Surreal Combo pools ---
PLAYFUL_ANIMALS: list[str] = [
    "cat", "fox", "bear", "owl", "moth", "swan", "pug", "wolf",
    "fawn", "hare", "crane", "finch", "otter", "seal", "dove",
    "badger", "robin", "wren", "toad", "newt", "gecko", "panda",
]

PLAYFUL_TITLES: list[str] = [
    "Mr.", "Dr.", "Captain", "King", "Saint", "Professor", "Mama",
    "Papa", "Uncle", "Aunt", "Baron", "Count", "Sir", "Lady",
]

PLAYFUL_SURNAMES: list[str] = [
    "Loops", "Beats", "Toast", "Biscuit", "Slipz", "Breezy",
    "Pudding", "Muffin", "Noodle", "Pickle", "Crumble", "Fudge",
    "Marmalade", "Cheddar", "Waffle", "Pretzel", "Brownie", "Cobbler",
]

PLAYFUL_ABSTRACTS: list[str] = [
    "Anonymous", "Invisible", "Impossible", "Unstoppable", "Peculiar",
    "Reluctant", "Accidental", "Notorious", "Legendary", "Inevitable",
    "Whimsical", "Spontaneous", "Nonchalant", "Sympathetic", "Divine",
]

PLAYFUL_FOODS: list[str] = [
    "Lemon", "Peach", "Mango", "Cocoa", "Honey", "Ginger",
    "Vanilla", "Cinnamon", "Sesame", "Wasabi", "Matcha", "Tofu",
]

PLAYFUL_ENOUGH_NOUNS: list[str] = [
    "Cereals", "Pillows", "Blankets", "Postcards", "Candles",
    "Records", "Cassettes", "Sketches", "Letters", "Chapters",
    "Sundays", "Mornings", "Evenings", "Winters", "Summers",
]

WUN_TWO_PATTERNS: list[tuple[str, str]] = [
    ("Wun", "Two"), ("Too", "Chill"), ("Half", "Past"), ("Day", "One"),
    ("Two", "Tone"), ("One", "Take"), ("Low", "Key"), ("No", "Rush"),
    ("Slow", "Mo"), ("Big", "Hush"), ("Lil", "Fog"), ("Kid", "Rain"),
    ("Old", "Tape"), ("New", "Leaf"), ("Dub", "Step"), ("Sub", "Zero"),
]

MAMA_PATTERNS: list[str] = [
    "Mama {}", "Papa {}", "Uncle {}", "Auntie {}",
]

MAMA_WORDS: list[str] = [
    "Aiuto", "Bongo", "Fresco", "Gelato", "Calma", "Dolce",
    "Bravo", "Piano", "Cielo", "Mondo", "Porto", "Luna",
    "Noche", "Tierra", "Fuego", "Dulce", "Estrella", "Alma",
]

# Suffix appended to every generated name
FEAT_SUFFIX: str = " (feat. mujin \u7121\u4eba)"


# ============================================================================
# MISSPELLING ENGINE
# ============================================================================

def _apply_misspell_transform(word: str, transform: str, rng: random.Random) -> str:
    """Apply a single misspelling transform to a lowercased word."""
    w = word

    if transform == "double_vowel":
        vowels_in = [(i, c) for i, c in enumerate(w) if c in "aeiou"]
        if vowels_in:
            idx, v = rng.choice(vowels_in)
            w = w[:idx] + v + w[idx:]

    elif transform == "double_consonant":
        cons_in = [(i, c) for i, c in enumerate(w) if c.isalpha() and c not in "aeiou"]
        if cons_in:
            idx, c = rng.choice(cons_in)
            w = w[:idx] + c + w[idx:]

    elif transform == "drop_vowel":
        vowels_in = [
            (i, c) for i, c in enumerate(w)
            if c in "aeiou" and i > 0 and i < len(w) - 1
        ]
        if vowels_in:
            idx, _ = rng.choice(vowels_in)
            w = w[:idx] + w[idx + 1:]

    elif transform == "swap_letter":
        swaps = {"c": "k", "s": "z", "ph": "f", "ck": "k", "x": "ks", "qu": "kw"}
        for old, new in swaps.items():
            if old in w:
                w = w.replace(old, new, 1)
                break

    elif transform == "truncate":
        cut = rng.randint(max(3, len(w) // 2), max(4, len(w) - 1))
        w = w[:cut]

    elif transform == "k_for_c":
        w = w.replace("c", "k", 1)

    elif transform == "z_for_s":
        w = w.replace("s", "z", 1)

    elif transform == "add_trailing_vowel":
        w = w.rstrip("aeiouy") + rng.choice(["a", "o", "i", "u"])

    return w


def misspell(word: str, rng: random.Random) -> str:
    """Apply lo-fi-style misspelling transforms to a word."""
    transforms = [
        "double_vowel", "double_consonant", "drop_vowel", "swap_letter",
        "truncate", "k_for_c", "z_for_s", "add_trailing_vowel",
    ]
    chosen = rng.choice(transforms)
    w = _apply_misspell_transform(word.lower(), chosen, rng)

    # Ensure it doesn't match the original
    if w == word.lower():
        w = w + rng.choice(["v", "x", "z", "q"])

    return w


# ============================================================================
# NAME REVERSAL ENGINE (Nujabes-style)
# ============================================================================

def reverse_name(name: str) -> str:
    """Reverse a name, Nujabes-style (Seba Jun -> Nujabes)."""
    return name[::-1].lower().capitalize()


# ============================================================================
# STYLE DISTRIBUTION
# ============================================================================

# Non-Japanese styles and their relative weights (share the ~67% slice)
_NON_JP_STYLES: list[tuple[str, float]] = [
    ("compound",    0.16),
    ("misspelled",  0.12),
    ("cryptic",     0.10),
    ("soft_phrase",  0.14),
    ("human_name",  0.10),
    ("mood_word",   0.12),
    ("playful",     0.14),
]


def _build_style_weights(japanese_ratio: float) -> tuple[list[str], list[float]]:
    """Build the weighted style selection lists, normalizing non-JP weights."""
    non_jp_total = sum(w for _, w in _NON_JP_STYLES)
    non_jp_share = 1.0 - japanese_ratio

    style_names: list[str] = []
    style_weights: list[float] = []
    for name, weight in _NON_JP_STYLES:
        style_names.append(name)
        style_weights.append((weight / non_jp_total) * non_jp_share)

    style_names.append("japanese")
    style_weights.append(japanese_ratio)

    return style_names, style_weights


# ============================================================================
# INDIVIDUAL STYLE GENERATORS
# ============================================================================

def _pick(rng: random.Random, lst: list) -> str:
    """Choose a random element from a list."""
    return rng.choice(lst)


def _pick_distinct_pair(rng: random.Random, lst: list) -> tuple[str, str]:
    """Pick two distinct elements from a list."""
    first = rng.choice(lst)
    second = rng.choice(lst)
    while second == first:
        second = rng.choice(lst)
    return first, second


# -- Style 1: Compound Word --------------------------------------------------

def generate_compound(rng: random.Random) -> tuple[str, str]:
    """Combine a prefix and suffix into a compound word name."""
    prefix = _pick(rng, COMPOUND_PREFIXES)
    suffix = _pick(rng, COMPOUND_SUFFIXES)
    return prefix + suffix, "compound"


# -- Style 2: Misspelled Real Word --------------------------------------------

def generate_misspelled(rng: random.Random) -> tuple[str, str]:
    """Misspell a real word in lo-fi style."""
    base = _pick(rng, MISSPELL_BASE_WORDS)
    return misspell(base, rng), "misspelled"


# -- Style 3: Lowercase Cryptic -----------------------------------------------

def _generate_cryptic_accented(rng: random.Random) -> str:
    """Take a short word and accent one vowel."""
    base = _pick(rng, CRYPTIC_SHORT_WORDS)
    for char, accented in ACCENT_CHARS.items():
        if char in base:
            return base.replace(char, accented, 1)
    return base


def generate_cryptic(rng: random.Random) -> tuple[str, str]:
    """Generate a cryptic lowercase/abbreviated name."""
    strategy = rng.choices(
        ["consonant_cluster", "short_word", "accented"],
        weights=[0.30, 0.50, 0.20],
    )[0]

    if strategy == "consonant_cluster":
        name = _pick(rng, CRYPTIC_FRAGMENTS)
    elif strategy == "short_word":
        name = _pick(rng, CRYPTIC_SHORT_WORDS)
    else:
        name = _generate_cryptic_accented(rng)

    return name, "cryptic"


# -- Style 4: Soft Two-Word Phrase ---------------------------------------------

def generate_soft_phrase(rng: random.Random) -> tuple[str, str]:
    """Pair a soft adjective with a noun."""
    adj = _pick(rng, SOFT_ADJECTIVES)
    noun = _pick(rng, SOFT_NOUNS)
    return f"{adj.capitalize()} {noun.capitalize()}", "soft_phrase"


# -- Style 5: Human Name ------------------------------------------------------

def generate_human_name(rng: random.Random) -> tuple[str, str]:
    """Combine a first and last name."""
    first = _pick(rng, FIRST_NAMES)
    last = _pick(rng, LAST_NAMES)
    return f"{first} {last}", "human_name"


# -- Style 6: Japanese-Inspired (sub-branches) --------------------------------

_JP_SUBS: list[str] = [
    "reversed", "jp_word", "jp_given", "romaji_blend",
    "jp_compound", "jp_place_name",
]
_JP_SUB_WEIGHTS: list[float] = [0.12, 0.22, 0.18, 0.20, 0.15, 0.13]


def _generate_jp_reversed(rng: random.Random) -> tuple[str, str]:
    """Reverse a Japanese name, Nujabes-style."""
    source = _pick(rng, JP_GIVEN_NAMES + JP_FAMILY_NAMES)
    return reverse_name(source), "japanese/reversed"


def _generate_jp_word(rng: random.Random) -> tuple[str, str]:
    """Use a Japanese word directly as the artist name."""
    return _pick(rng, JP_WORDS), "japanese/word"


def _generate_jp_given(rng: random.Random) -> tuple[str, str]:
    """Japanese given name, optionally with initial or lowercase styling."""
    given = _pick(rng, JP_GIVEN_NAMES)
    style = rng.choices(
        ["plain", "with_initial", "lowercase"],
        weights=[0.40, 0.30, 0.30],
    )[0]

    if style == "plain":
        name = given
    elif style == "with_initial":
        family = _pick(rng, JP_FAMILY_NAMES)
        name = f"{given} {family[0]}."
    else:
        name = given.lower()

    return name, "japanese/given_name"


def _generate_romaji_blend(rng: random.Random) -> tuple[str, str]:
    """Blend a Japanese word with an English prefix or suffix."""
    direction = rng.choice(["jp_first", "en_first"])
    if direction == "jp_first":
        jp = _pick(rng, JP_WORDS)
        en = _pick(rng, JP_SUFFIXES_FOR_BLEND)
        sep = rng.choice(["", ".", "_", " "])
        name = jp + sep + en
    else:
        en = _pick(rng, JP_PREFIXES_FOR_BLEND)
        jp = _pick(rng, JP_WORDS)
        name = en + jp

    return name, "japanese/romaji_blend"


def _generate_jp_compound(rng: random.Random) -> tuple[str, str]:
    """Combine two distinct Japanese words."""
    w1, w2 = _pick_distinct_pair(rng, JP_WORDS)
    return w1 + w2, "japanese/compound"


def _generate_jp_place_name(rng: random.Random) -> tuple[str, str]:
    """Combine place fragments into a plausible place-name alias."""
    p1, p2 = _pick_distinct_pair(rng, JP_PLACE_FRAGMENTS)
    return p1 + p2, "japanese/place_name"


_JP_SUB_GENERATORS = {
    "reversed": _generate_jp_reversed,
    "jp_word": _generate_jp_word,
    "jp_given": _generate_jp_given,
    "romaji_blend": _generate_romaji_blend,
    "jp_compound": _generate_jp_compound,
    "jp_place_name": _generate_jp_place_name,
}


def generate_japanese(rng: random.Random) -> tuple[str, str]:
    """Generate a Japanese-inspired name from one of six sub-branches."""
    sub = rng.choices(_JP_SUBS, weights=_JP_SUB_WEIGHTS)[0]
    return _JP_SUB_GENERATORS[sub](rng)


# -- Style 7: Mood Single Word ------------------------------------------------

def generate_mood_word(rng: random.Random) -> tuple[str, str]:
    """Pick a single evocative mood word."""
    return _pick(rng, MOOD_WORDS), "mood_word"


# -- Style 8: Playful/Surreal Combo -------------------------------------------

_PLAYFUL_SUBS: list[str] = [
    "animal_surname", "title_abstract", "adj_animal",
    "food_noun", "wun_two", "mama", "enough",
]
_PLAYFUL_SUB_WEIGHTS: list[float] = [0.15, 0.15, 0.15, 0.10, 0.15, 0.15, 0.15]


def _generate_playful_animal_surname(rng: random.Random) -> str:
    animal = _pick(rng, PLAYFUL_ANIMALS).capitalize()
    surname = _pick(rng, PLAYFUL_SURNAMES)
    return f"{animal} {surname}"


def _generate_playful_title_abstract(rng: random.Random) -> str:
    title = _pick(rng, PLAYFUL_TITLES)
    abstract = _pick(rng, PLAYFUL_ABSTRACTS)
    return f"{title} {abstract}"


def _generate_playful_adj_animal(rng: random.Random) -> str:
    adj = _pick(rng, SOFT_ADJECTIVES).capitalize()
    animal = _pick(rng, PLAYFUL_ANIMALS).capitalize()
    return f"{adj} {animal}"


def _generate_playful_food_noun(rng: random.Random) -> str:
    food = _pick(rng, PLAYFUL_FOODS)
    noun = _pick(rng, SOFT_NOUNS).capitalize()
    return f"{food} {noun}"


def _generate_playful_wun_two(rng: random.Random) -> str:
    pair = _pick(rng, WUN_TWO_PATTERNS)
    return f"{pair[0]} {pair[1]}"


def _generate_playful_mama(rng: random.Random) -> str:
    pattern = _pick(rng, MAMA_PATTERNS)
    word = _pick(rng, MAMA_WORDS)
    return pattern.format(word)


def _generate_playful_enough(rng: random.Random) -> str:
    adj = rng.choice(["Enough", "Too Many", "Extra", "Spare", "Last"])
    noun = _pick(rng, PLAYFUL_ENOUGH_NOUNS)
    return f"{adj} {noun}"


_PLAYFUL_SUB_GENERATORS: dict[str, callable] = {
    "animal_surname": _generate_playful_animal_surname,
    "title_abstract": _generate_playful_title_abstract,
    "adj_animal": _generate_playful_adj_animal,
    "food_noun": _generate_playful_food_noun,
    "wun_two": _generate_playful_wun_two,
    "mama": _generate_playful_mama,
    "enough": _generate_playful_enough,
}


def generate_playful(rng: random.Random) -> tuple[str, str]:
    """Generate a playful/surreal combo name from one of seven sub-branches."""
    sub = rng.choices(_PLAYFUL_SUBS, weights=_PLAYFUL_SUB_WEIGHTS)[0]
    name = _PLAYFUL_SUB_GENERATORS[sub](rng)
    return name, f"playful/{sub}"


# ============================================================================
# STYLE DISPATCH
# ============================================================================

_STYLE_GENERATORS: dict[str, callable] = {
    "compound": generate_compound,
    "misspelled": generate_misspelled,
    "cryptic": generate_cryptic,
    "soft_phrase": generate_soft_phrase,
    "human_name": generate_human_name,
    "japanese": generate_japanese,
    "mood_word": generate_mood_word,
    "playful": generate_playful,
}


# ============================================================================
# MODIFIER LAYER
# ============================================================================

# Styles that are rendered lowercase
_LOWERCASE_STYLES: frozenset[str] = frozenset({
    "cryptic", "japanese/word", "japanese/romaji_blend",
    "japanese/compound", "japanese/place_name", "mood_word",
})

# Styles eligible for the "The" prefix
_THE_PREFIX_STYLES: frozenset[str] = frozenset({
    "soft_phrase", "playful/adj_animal", "playful/enough",
})


def _apply_casing(name: str, style: str, rng: random.Random) -> str:
    """Apply lo-fi casing conventions based on style."""
    if style in _LOWERCASE_STYLES:
        return name.lower()

    if style == "misspelled":
        # ~70% lowercase, ~30% capitalized
        return name.lower() if rng.random() < 0.70 else name.capitalize()

    if style == "compound":
        # ~50% lowercase, ~30% capitalized, ~20% as-is
        roll = rng.random()
        if roll < 0.50:
            return name.lower()
        elif roll < 0.80:
            return name.capitalize()

    return name


def _apply_punctuation(name: str, rng: random.Random) -> str:
    """Apply lo-fi punctuation stylizations (trailing period, underscore, mid-name separator)."""
    roll = rng.random()
    if roll < 0.08:
        return name + "."
    elif roll < 0.12:
        return name + "_"
    elif roll < 0.14 and " " not in name and len(name) > 5:
        mid = len(name) // 2
        sep = rng.choice([":", "."])
        return name[:mid] + sep + name[mid:]
    return name


def _apply_the_prefix(name: str, style: str, rng: random.Random) -> str:
    """Optionally prepend 'The' (~5% chance, only for eligible styles)."""
    if rng.random() < 0.05 and style in _THE_PREFIX_STYLES:
        return "The " + name
    return name


def apply_modifiers(name: str, style: str, rng: random.Random) -> str:
    """Apply the full modifier chain: casing, punctuation, optional 'The' prefix."""
    name = _apply_casing(name, style, rng)
    name = _apply_punctuation(name, rng)
    name = _apply_the_prefix(name, style, rng)
    return name


# ============================================================================
# GENERATOR DATACLASS
# ============================================================================

@dataclass
class LofiArtistNameGenerator:
    """Generates lo-fi artist/producer names across multiple style branches."""

    seed: Optional[int] = None
    japanese_ratio: float = 0.33
    rng: random.Random = field(default_factory=random.Random, init=False, repr=False)

    _style_names: list[str] = field(default_factory=list, init=False, repr=False)
    _style_weights: list[float] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed) if self.seed is not None else random.Random()
        self._style_names, self._style_weights = _build_style_weights(self.japanese_ratio)

    def generate_one(self) -> dict[str, str]:
        """Generate a single artist name dict with 'name' and 'style' keys."""
        style = self.rng.choices(self._style_names, weights=self._style_weights, k=1)[0]
        generator = _STYLE_GENERATORS.get(style, generate_compound)
        name, sub_style = generator(self.rng)
        name = apply_modifiers(name, sub_style, self.rng)
        name += FEAT_SUFFIX
        return {"name": name, "style": sub_style}

    def generate(self, count: int = 1) -> list[dict[str, str]]:
        """Generate multiple artist names. Returns a list of dicts with 'name' and 'style'."""
        return [self.generate_one() for _ in range(count)]


# ============================================================================
# PUBLIC API
# ============================================================================

def generate_artist_names(
    count: int = 1,
    seed: Optional[int] = None,
    japanese_ratio: float = 0.33,
) -> list[dict[str, str]]:
    """
    Generate lo-fi artist names.

    Args:
        count: Number of names to generate.
        seed: Optional RNG seed for reproducibility.
        japanese_ratio: Target fraction of Japanese-inspired names (~0.33 by default).

    Returns:
        List of dicts, each with 'name' and 'style' keys.
        Every name is appended with " (feat. mujin 無人)".
    """
    gen = LofiArtistNameGenerator(seed=seed, japanese_ratio=japanese_ratio)
    return gen.generate(count=count)


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    print("=" * 90)
    print("  LO-FI ARTIST NAME GENERATOR -- 20 SIMULATED BATCHES (15 names each)")
    print("=" * 90)

    for run in range(1, 21):
        results = generate_artist_names(count=15, seed=run * 37 + 13)
        jp_count = sum(1 for r in results if r["style"].startswith("japanese"))

        print(f"\n{'-' * 90}")
        print(f"  RUN {run:02d}  |  {jp_count}/15 Japanese-inspired ({jp_count / 15 * 100:.0f}%)")
        print(f"{'-' * 90}")
        print(f"  {'#':<4} {'Artist Name':<55} {'Style':<35}")
        print(f"  {'---':<4} {'---':<55} {'---':<35}")

        for i, r in enumerate(results, 1):
            jp_tag = " [JP]" if r["style"].startswith("japanese") else ""
            print(f"  {i:<4} {r['name']:<55} {r['style']}{jp_tag}")

    print(f"\n{'=' * 90}")
    print("  END OF SIMULATION")
    print(f"{'=' * 90}")
