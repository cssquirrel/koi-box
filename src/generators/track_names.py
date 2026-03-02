"""
Lo-Fi Track Name Generator
===========================
Generates evocative lo-fi track names via:
  1. Three-word phrase generation (cubic combos)
  2. Compound word fusion path
  3. 40+ multi-slot fragment templates
  4. Expanded word pools (100-150 words each)
  5. Wider compatibility matrices (25-30 partners per key)
  6. Micro-modifier layer (parentheticals, numbers, tags)

Architecture:
  Branch A: Template-based (single, pair, triple, compound, fragment, place)
  Branch B: Theme-based (mood -> structure)
  Branch C: Modifier layer (case, punct, suffix, micro-modifiers)
"""

import random
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# EXPANDED WORD POOLS
# ============================================================================

POOLS: dict[str, list[str]] = {
    "nature_nouns": [
        "rain", "mist", "fog", "dew", "frost", "snow", "haze", "cloud",
        "petal", "bloom", "moss", "fern", "cedar", "willow", "birch", "ivy",
        "meadow", "grove", "creek", "brook", "pond", "tide", "reef", "shore",
        "ridge", "valley", "hillside", "canyon", "lagoon", "basin", "inlet",
        "ember", "ash", "stone", "sand", "clay", "dust", "silt", "pebble",
        "breeze", "gust", "drizzle", "flurry", "thaw", "aurora", "horizon",
        "river", "lake", "ocean", "field", "garden", "forest", "island",
        "lichen", "bark", "thorn", "root", "vine", "bough", "canopy",
        "clearing", "marsh", "delta", "bluff", "cove", "dune", "glacier",
        "plateau", "ravine", "summit", "tundra", "prairie", "steppe",
        "oasis", "estuary", "fjord", "atoll", "geyser", "rapids", "shoal",
        "clover", "heather", "thistle", "yarrow", "aster", "dahlia",
        "orchid", "lotus", "magnolia", "wisteria", "poppy", "marigold",
        "lavender", "jasmine", "rosemary", "thyme", "sage", "basil",
        "cypress", "aspen", "elm", "oak", "pine", "spruce", "maple",
        "sycamore", "juniper", "hazel", "alder", "larch", "yew",
        "pollen", "nectar", "sap", "resin", "lichen", "spore",
        "dewdrop", "raindrop", "snowflake", "icicle", "hailstone",
        "puddle", "rivulet", "cascade", "waterfall", "spring",
        "current", "undertow", "eddy", "ripple", "wake",
    ],
    "nature_adj": [
        "mossy", "misty", "dewy", "frosted", "hazy", "clouded", "sunlit",
        "overgrown", "windswept", "weathered", "faded", "scattered", "still",
        "quiet", "hushed", "drifting", "fallen", "distant", "gentle", "soft",
        "tangled", "wild", "barren", "lush", "verdant", "parched", "damp",
        "soggy", "crisp", "brisk", "balmy", "humid", "arid", "temperate",
        "wintry", "vernal", "autumnal", "coastal", "alpine", "riparian",
        "brackish", "silty", "peaty", "chalky", "loamy", "sandy",
        "sheltered", "exposed", "secluded", "hidden", "open",
    ],
    "weather": [
        "rainfall", "downpour", "overcast", "drizzle", "snowfall", "flurry",
        "sunshower", "cloudbreak", "fog bank", "morning dew", "first frost",
        "light rain", "late snow", "thin ice", "warm front", "grey skies",
        "sleet", "hail", "thunder", "lightning", "monsoon", "typhoon",
        "squall", "gale", "calm", "clearing", "rainbow", "frost bite",
        "black ice", "wind chill", "heat haze", "sea fog", "mist roll",
    ],
    "seasons": [
        "spring", "summer", "autumn", "fall", "winter", "solstice", "equinox",
        "monsoon", "harvest", "thaw", "april", "november", "february",
        "march", "october", "december", "january", "september", "june",
        "may", "midsummer", "midwinter", "early spring", "late autumn",
    ],
    "time_nouns": [
        "dawn", "dusk", "twilight", "midnight", "noon", "daybreak", "sundown",
        "nightfall", "sunrise", "sunset", "evening", "morning", "afternoon",
        "golden hour", "blue hour", "last light", "first light",
        "daylight", "moonrise", "moonset", "witching hour", "small hours",
        "closing time", "opening hour", "rush hour", "quiet hour",
    ],
    "time_phrases": [
        "3am", "4am", "5pm", "7pm", "11pm", "2:30", "6am",
        "late morning", "early hours", "small hours", "closing time",
        "before sunrise", "after dark", "almost midnight",
        "quarter past", "half past", "just before", "right after",
    ],
    "real_places": [
        "Kyoto", "Lisbon", "Porto", "Oslo", "Helsinki", "Rotterdam", "Bruges",
        "Yokohama", "Osaka", "Shibuya", "Montmartre", "Belleville", "Havana",
        "Marrakech", "Tangier", "Reykjavik", "Queenstown", "Patagonia",
        "Hokkaido", "Okinawa", "Amalfi", "Cinque Terre", "Santorini",
        "Hanoi", "Saigon", "Taipei", "Seoul", "Busan", "Kamakura",
        "Nagano", "Nara", "Kobe", "Sapporo", "Jeju", "Chiang Mai",
        "Dubrovnik", "Ghent", "Antwerp", "Copenhagen", "Malmö", "Bergen",
        "Salzburg", "Lucerne", "Zurich", "Florence", "Siena", "Bologna",
        "Seville", "Granada", "Valencia", "Marseille", "Lyon", "Bordeaux",
        "Prague", "Vienna", "Budapest", "Tallinn", "Riga", "Vilnius",
        "Luang Prabang", "Ubud", "Penang", "Hoi An", "Vientiane",
    ],
    "place_suffixes": [
        "road", "street", "lane", "avenue", "hill", "park", "bridge",
        "station", "pier", "terrace", "alley", "square", "market", "harbour",
        "coast", "shore", "district", "quarter", "crossing", "pass",
        "heights", "point", "gate", "walk", "way", "row", "court",
        "wharf", "dock", "canal", "plaza", "promenade", "arcade",
    ],
    "imagined_places": [
        "Moonvale", "Cedarwick", "Stillwater", "Ashgrove", "Ferndale",
        "Misthollow", "Dewpoint", "Cloudrest", "Tidepool", "Emberglen",
        "Hazelbrook", "Willowmere", "Stonebridge", "Foxglove", "Heathrow",
        "Copperfield", "Birchwood", "Ravenhill", "Ivywood", "Maplecrest",
        "Thornbury", "Aldermere", "Pinereach", "Briarcliff", "Mosshaven",
        "Driftmoor", "Ashvale", "Cedarlake", "Hollowpine", "Frostwick",
    ],
    "emotions": [
        "solitude", "serenity", "nostalgia", "longing", "tenderness",
        "melancholy", "contentment", "reverie", "gratitude", "patience",
        "surrender", "acceptance", "affection", "comfort", "stillness",
        "warmth", "yearning", "wonder", "clarity", "resilience",
        "bliss", "sorrow", "empathy", "grace", "hope", "peace",
        "devotion", "kinship", "restlessness", "wistfulness", "awe",
        "relief", "remorse", "forgiveness", "compassion", "vulnerability",
        "reverence", "humility", "innocence", "elation", "calm",
    ],
    "abstract_adj": [
        "gentle", "quiet", "soft", "slow", "faint", "dim", "pale",
        "hush", "calm", "easy", "simple", "brief", "small", "slight",
        "subtle", "tender", "distant", "familiar", "fleeting", "lasting",
        "fragile", "delicate", "hollow", "muted", "faded", "worn",
        "thin", "deep", "wide", "narrow", "open", "closed",
        "near", "far", "early", "late", "young", "old",
        "bare", "plain", "clear", "vague", "certain", "uncertain",
        "patient", "restless", "steady", "wavering", "silent", "still",
    ],
    "abstract_nouns": [
        "echo", "silence", "shadow", "memory", "dream", "thought",
        "moment", "breath", "whisper", "gesture", "glance", "pause",
        "chapter", "letter", "note", "sketch", "outline", "fragment",
        "loop", "cycle", "orbit", "drift", "arc", "thread", "trace",
        "edge", "margin", "border", "threshold", "passage", "interval",
        "imprint", "residue", "remnant", "vestige", "relic", "fossil",
        "signal", "pulse", "frequency", "wavelength", "static", "noise",
        "texture", "grain", "fiber", "layer", "fold", "crease",
        "notion", "instinct", "reflex", "impulse", "habit", "ritual",
    ],
    "cozy_nouns": [
        "coffee", "tea", "cocoa", "blanket", "candle", "fireplace",
        "bookshelf", "windowsill", "doorstep", "rooftop", "balcony",
        "record", "vinyl", "cassette", "radio", "headphones", "notebook",
        "armchair", "lamplight", "curtain", "pillow", "quilt", "sweater",
        "mug", "kettle", "toast", "honey", "cinnamon", "lavender",
        "bookmark", "envelope", "postcard", "diary", "journal", "almanac",
        "thermos", "matchbox", "inkwell", "typewriter", "gramophone",
        "porch", "attic", "cellar", "pantry", "hearth", "mantle",
        "stairwell", "hallway", "vestibule", "alcove", "nook", "loft",
    ],
    "cozy_adj": [
        "warm", "cozy", "soft", "sleepy", "lazy", "rainy", "snowy",
        "quiet", "homemade", "handmade", "worn", "old", "familiar",
        "comfortable", "tucked", "nested", "curled",
        "frosty", "breezy", "cloudy", "starry", "moonlit", "candlelit",
        "dusky", "misty", "foggy", "hazy", "dewy", "sunlit",
    ],
    "colors": [
        "indigo", "amber", "ivory", "coral", "sage", "slate", "mauve",
        "ochre", "sienna", "cerulean", "cobalt", "crimson", "rust",
        "peach", "lilac", "lavender", "charcoal", "teal", "copper",
        "gold", "silver", "bronze", "pearl", "opal", "jade",
        "burgundy", "maroon", "taupe", "beige", "cream", "bone",
        "pewter", "graphite", "onyx", "obsidian", "sapphire", "emerald",
        "topaz", "garnet", "citrine", "umber", "sepia", "khaki",
    ],
    "light_nouns": [
        "glow", "shimmer", "gleam", "flicker", "spark", "ray", "beam",
        "halo", "prism", "spectrum", "reflection", "refraction", "luster",
        "sunbeam", "moonlight", "starlight", "lamplight", "candlelight",
        "twilight", "daylight", "firelight", "flashpoint", "afterglow",
        "backlight", "highlight", "sidelight", "penumbra", "umbra",
    ],
    "textures": [
        "velvet", "silk", "linen", "cotton", "wool", "grain", "weave",
        "patina", "enamel", "glaze", "lacquer", "porcelain", "ceramic",
        "denim", "corduroy", "suede", "gauze", "paper", "parchment",
        "burlap", "tweed", "satin", "chiffon", "muslin", "felt",
        "leather", "canvas", "bamboo", "rattan", "wicker", "cork",
    ],
    "movement_nouns": [
        "drift", "float", "cruise", "stroll", "wander", "voyage", "passage",
        "detour", "shortcut", "transit", "crossing", "departure", "arrival",
        "return", "orbit", "spiral", "current", "flow", "ripple", "wave",
        "descent", "ascent", "glide", "sweep", "turn", "bend",
        "meander", "ramble", "trek", "jaunt", "sojourn", "exodus",
    ],
    "movement_verbs": [
        "drifting", "floating", "wandering", "cruising", "coasting",
        "gliding", "swaying", "spinning", "turning", "folding",
        "unraveling", "dissolving", "fading", "settling", "resting",
        "meandering", "cascading", "ebbing", "flowing", "receding",
    ],
    "prepositions": [
        "of", "in", "on", "by", "for", "from", "near", "past",
        "through", "under", "over", "between", "beyond", "within",
        "after", "before", "along", "across", "beneath", "beside",
    ],
    "conjunctions": ["and", "or", "nor", "then", "but"],
}


# ============================================================================
# COMPOUND WORD POOLS (for fused single-word names)
# ============================================================================

COMPOUND_PREFIXES: list[str] = [
    "rain", "mist", "fog", "dew", "frost", "snow", "cloud", "moon",
    "sun", "star", "night", "dawn", "dusk", "tide", "wave", "stone",
    "moss", "fern", "pine", "elm", "oak", "ash", "sage", "mint",
    "silk", "dust", "sand", "clay", "salt", "rust", "ember", "smoke",
    "dream", "sleep", "haze", "bloom", "drift", "still", "soft",
    "cool", "warm", "pale", "deep", "slow", "half", "hush", "lull",
    "honey", "amber", "ivory", "coral", "jade", "pearl", "opal",
    "copper", "silver", "gold", "iron", "glass", "paper", "wool",
    "velvet", "cotton", "linen", "cedar", "willow", "birch", "maple",
]

COMPOUND_SUFFIXES: list[str] = [
    "fall", "light", "glow", "shade", "drift", "bloom", "frost",
    "field", "scape", "wood", "grove", "vale", "glen", "mere",
    "brook", "creek", "pool", "lake", "shore", "coast", "cove",
    "stone", "dust", "grain", "leaf", "root", "seed", "vine",
    "song", "note", "tone", "bell", "hum", "loop", "beat",
    "walk", "step", "path", "trail", "gate", "bridge", "arch",
    "work", "craft", "weave", "fold", "press", "cast", "mark",
    "watch", "keep", "hold", "rest", "nest", "den", "burrow",
    "wash", "rinse", "melt", "drip", "pour", "spill", "soak",
]


# ============================================================================
# COMPOUND COMPATIBILITY MATRIX
# ============================================================================

COMPOUND_COMPAT: dict[str, list[str]] = {
    "rain":   ["fall", "light", "glow", "shade", "drift", "wash", "drop", "song", "coat", "pool", "watch", "walk", "forest", "bloom", "stone", "field", "water", "cloud", "bow", "beat", "melt", "pour", "creek", "cove", "trail"],
    "mist":   ["fall", "light", "glow", "shade", "wood", "vale", "field", "walk", "born", "flower", "stone", "pool", "weave", "bloom", "song", "trail", "grove", "lake", "creek", "shore", "gate", "tone", "bell", "leaf", "rest"],
    "fog":    ["light", "glow", "shade", "drift", "horn", "bank", "vale", "field", "wood", "bloom", "stone", "bell", "song", "watch", "gate", "trail", "grove", "lake", "creek", "shore", "tone", "note", "leaf", "rest", "fall"],
    "dew":    ["fall", "light", "glow", "drop", "bloom", "field", "song", "pool", "leaf", "vine", "frost", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "seed"],
    "frost":  ["light", "glow", "bloom", "field", "bite", "work", "fall", "stone", "bell", "song", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "wood", "vale", "pool"],
    "snow":   ["fall", "light", "glow", "drift", "field", "flake", "melt", "bloom", "shade", "stone", "bell", "song", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "cove"],
    "cloud":  ["fall", "light", "drift", "burst", "break", "shade", "bloom", "rest", "song", "field", "gate", "walk", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "path", "leaf", "cove", "glow"],
    "moon":   ["light", "glow", "fall", "shade", "rise", "stone", "bloom", "walk", "song", "beam", "dust", "pool", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "path", "rest", "leaf", "field"],
    "sun":    ["light", "glow", "fall", "rise", "stone", "bloom", "field", "song", "beam", "burn", "flower", "set", "dial", "shade", "shore", "pool", "bell", "note", "tone", "grove", "lake", "creek", "trail", "gate", "walk"],
    "star":   ["light", "glow", "fall", "dust", "bloom", "field", "song", "gaze", "born", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "shade", "pool"],
    "night":  ["fall", "light", "glow", "shade", "bloom", "song", "watch", "walk", "cap", "shift", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "path", "rest", "leaf", "field", "pool", "cove"],
    "dawn":   ["light", "glow", "bloom", "song", "break", "field", "walk", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "path", "rest", "leaf", "shade", "pool", "cove", "fall", "stone", "watch"],
    "dusk":   ["light", "glow", "fall", "shade", "bloom", "song", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "field", "pool", "cove", "stone", "watch", "drift"],
    "tide":   ["light", "pool", "mark", "fall", "drift", "song", "line", "water", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "field", "cove", "stone", "glow"],
    "wave":   ["light", "fall", "drift", "song", "pool", "crest", "break", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "field", "cove", "stone", "glow", "length"],
    "stone":  ["light", "fall", "field", "song", "wall", "work", "grove", "pool", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "cove", "glow", "bloom", "bell", "note", "tone", "cold", "wash", "bridge"],
    "moss":   ["light", "bloom", "field", "grove", "stone", "wood", "song", "bell", "note", "tone", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "glow", "fall", "shade", "vale"],
    "dream":  ["light", "fall", "drift", "field", "scape", "song", "state", "walk", "pool", "bloom", "shade", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "path", "rest", "leaf", "cove"],
    "sleep":  ["light", "fall", "walk", "song", "field", "bloom", "shade", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "path", "rest", "leaf", "pool", "cove", "glow", "drift", "vale"],
    "haze":   ["light", "glow", "bloom", "field", "wood", "song", "shade", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "fall", "drift"],
    "bloom":  ["field", "light", "glow", "song", "shade", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "fall", "drift", "vale", "wood"],
    "drift":  ["wood", "light", "glow", "fall", "song", "shade", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "field", "bloom", "vale"],
    "honey":  ["light", "glow", "bloom", "comb", "dew", "field", "song", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "fall", "shade"],
    "amber":  ["light", "glow", "fall", "field", "stone", "song", "bloom", "shade", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "dust", "grain"],
    "velvet": ["light", "glow", "bloom", "shade", "song", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "field", "fall", "dust", "grain"],
    "cedar":  ["light", "wood", "grove", "bloom", "field", "song", "shade", "stone", "bell", "note", "tone", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "fall", "glow", "vale"],
    "willow": ["light", "wood", "grove", "bloom", "field", "song", "shade", "stone", "bell", "note", "tone", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "fall", "glow", "vale"],
    "copper": ["light", "glow", "tone", "field", "bell", "leaf", "stone", "dust", "bloom", "shade", "song", "note", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "pool", "cove", "fall", "grain"],
    "silver": ["light", "glow", "tone", "bell", "leaf", "stone", "dust", "bloom", "shade", "song", "note", "grove", "lake", "creek", "shore", "trail", "field", "gate", "walk", "path", "rest", "pool", "cove", "fall", "lining"],
    "glass":  ["light", "glow", "fall", "work", "bloom", "shade", "song", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "field", "house"],
}


# ============================================================================
# ADJECTIVE-NOUN COMPATIBILITY MATRIX
# ============================================================================

ADJ_NOUN_COMPAT: dict[str, list[str]] = {
    "mossy":      ["stone", "creek", "grove", "wall", "ridge", "pebble", "cedar", "bridge", "rooftop", "doorstep", "path", "log", "bank", "cliff", "arch", "ruin", "well", "gate", "stair", "ledge", "root", "trunk", "bark", "boulder", "outcrop"],
    "misty":      ["morning", "valley", "harbour", "shore", "meadow", "hillside", "creek", "garden", "ridge", "forest", "lake", "mountain", "pier", "trail", "dawn", "hollow", "canyon", "plateau", "clearing", "estuary", "cove", "inlet", "bluff", "pass", "fjord"],
    "dewy":       ["morning", "meadow", "petal", "fern", "garden", "bloom", "field", "grass", "windowsill", "balcony", "leaf", "vine", "rose", "orchid", "lawn", "clover", "cobweb", "bough", "branch", "thicket", "glade", "clearing", "hillside", "slope", "terrace"],
    "frosted":    ["glass", "windowsill", "morning", "breath", "petal", "cedar", "lake", "shore", "rooftop", "field", "leaf", "branch", "pine", "meadow", "path", "gate", "bench", "rail", "edge", "rim", "peak", "ridge", "cobblestone", "lantern", "hedge"],
    "hazy":       ["afternoon", "memory", "summer", "horizon", "shore", "dream", "skyline", "morning", "dusk", "coastline", "sunset", "outline", "silhouette", "distance", "film", "warmth", "glow", "light", "window", "view", "recollection", "daydream", "reverie", "portrait", "landscape"],
    "clouded":    ["glass", "memory", "mirror", "morning", "thought", "horizon", "lake", "reflection", "sky", "noon", "judgment", "vision", "window", "surface", "crystal", "lens", "pool", "water", "eye", "mind", "diamond", "amber", "jade", "quartz", "ice"],
    "sunlit":     ["meadow", "dust", "morning", "windowsill", "balcony", "doorstep", "porch", "garden", "creek", "shore", "room", "path", "clearing", "terrace", "courtyard", "hallway", "attic", "loft", "stairwell", "corridor", "canopy", "grove", "orchard", "hillside", "plateau"],
    "overgrown":  ["garden", "field", "path", "grove", "meadow", "terrace", "courtyard", "balcony", "rooftop", "bridge", "ruin", "wall", "gate", "arch", "staircase", "fountain", "well", "cemetery", "churchyard", "orchard", "vineyard", "trail", "railway", "station", "greenhouse"],
    "windswept":  ["shore", "hillside", "ridge", "field", "coast", "meadow", "rooftop", "terrace", "crossing", "dune", "cliff", "bluff", "plain", "moor", "heath", "prairie", "steppe", "plateau", "summit", "lighthouse", "pier", "dock", "harbour", "headland", "cape"],
    "weathered":  ["stone", "record", "letter", "doorstep", "bridge", "notebook", "bench", "pier", "cassette", "vinyl", "wood", "sign", "fence", "gate", "shutter", "wall", "dock", "hull", "rope", "canvas", "leather", "boot", "journal", "map", "compass"],
    "faded":      ["letter", "memory", "photograph", "record", "echo", "dream", "notebook", "cassette", "vinyl", "curtain", "wallpaper", "poster", "stamp", "ticket", "receipt", "label", "ink", "denim", "flag", "banner", "postcard", "painting", "mural", "tapestry", "blueprint"],
    "scattered":  ["light", "thought", "petal", "rain", "cloud", "note", "dust", "ash", "ember", "shadow", "leaf", "seed", "star", "snowflake", "fragment", "shard", "bead", "droplet", "crumb", "grain", "feather", "page", "memory", "whisper", "echo"],
    "still":      ["water", "morning", "moment", "pond", "lake", "air", "night", "life", "reflection", "silence", "frame", "image", "surface", "pool", "harbor", "room", "forest", "mind", "heart", "hour", "afternoon", "winter", "dawn", "dusk", "garden"],
    "quiet":      ["morning", "night", "moment", "street", "room", "thought", "shore", "rain", "whisper", "garden", "house", "village", "town", "corner", "alley", "courtyard", "library", "café", "harbor", "cove", "inlet", "valley", "meadow", "forest", "clearing"],
    "hushed":     ["morning", "whisper", "tone", "room", "moment", "prayer", "breath", "evening", "snow", "forest", "library", "gallery", "chapel", "corridor", "garden", "conversation", "voice", "crowd", "village", "harbour", "cathedral", "cloister", "chamber", "sanctuary", "alcove"],
    "drifting":   ["cloud", "thought", "snow", "ash", "petal", "boat", "memory", "smoke", "leaf", "dream", "seed", "feather", "fog", "mist", "lantern", "kite", "balloon", "ember", "dust", "pollen", "tide", "current", "wave", "shadow", "light"],
    "fallen":     ["leaf", "petal", "snow", "ash", "rain", "star", "ember", "branch", "bloom", "feather", "fruit", "angel", "kingdom", "tree", "fence", "bridge", "tower", "wall", "gate", "sign", "log", "stone", "needle", "acorn", "chestnut"],
    "distant":    ["shore", "memory", "thunder", "light", "horizon", "mountain", "bell", "echo", "dream", "star", "city", "train", "harbor", "island", "village", "tower", "lighthouse", "music", "voice", "figure", "signal", "radio", "church", "coastline", "silhouette"],
    "gentle":     ["rain", "breeze", "morning", "wave", "touch", "glow", "drift", "current", "light", "murmur", "slope", "curve", "bend", "hill", "stream", "whisper", "hum", "rustle", "sway", "pulse", "rhythm", "tide", "wind", "warmth", "reminder"],
    "soft":       ["rain", "light", "glow", "snow", "echo", "landing", "morning", "breath", "focus", "loop", "ground", "earth", "clay", "sand", "fur", "wool", "linen", "cotton", "moss", "grass", "murmur", "hum", "whisper", "rustle", "breeze"],
    "fragile":    ["morning", "light", "bloom", "thread", "glass", "ice", "frost", "petal", "wing", "shell", "bone", "web", "net", "lace", "film", "membrane", "echo", "silence", "trust", "peace", "balance", "hope", "dream", "memory", "truce"],
    "delicate":   ["bloom", "frost", "lace", "thread", "petal", "wing", "glass", "porcelain", "crystal", "chain", "web", "net", "film", "balance", "flavor", "scent", "aroma", "touch", "gesture", "brushstroke", "stitch", "note", "tone", "shade", "hue"],
    "hollow":     ["tree", "log", "bone", "shell", "cave", "echo", "sound", "voice", "drum", "reed", "pipe", "chamber", "valley", "hill", "mountain", "promise", "victory", "laugh", "feeling", "space", "room", "ground", "stone", "trunk", "nest"],
    "muted":      ["tone", "color", "light", "glow", "trumpet", "horn", "bell", "voice", "echo", "hue", "shade", "palette", "morning", "afternoon", "sunset", "warmth", "gold", "amber", "crimson", "blue", "green", "purple", "orange", "conversation", "response"],
    "deep":       ["water", "forest", "sleep", "breath", "blue", "green", "purple", "night", "winter", "silence", "thought", "pool", "well", "cave", "canyon", "valley", "ocean", "lake", "river", "snow", "root", "bass", "tone", "current", "shadow"],
    "slow":       ["morning", "dance", "burn", "drift", "tide", "fade", "wave", "rain", "walk", "bloom", "motion", "train", "river", "pulse", "breath", "drip", "pour", "melt", "crawl", "turn", "roll", "swing", "sway", "climb", "descent"],
    "faint":      ["glow", "memory", "echo", "light", "whisper", "trace", "outline", "pulse", "signal", "star", "smile", "scent", "aroma", "breeze", "warmth", "hum", "rustle", "shimmer", "flicker", "blush", "murmur", "heartbeat", "shadow", "impression", "mark"],
    "tender":     ["morning", "thought", "rain", "glow", "moment", "night", "gesture", "pause", "bloom", "note", "touch", "word", "look", "memory", "feeling", "mercy", "care", "age", "green", "shoot", "sprout", "bud", "leaf", "heart", "soul"],
    "familiar":   ["warmth", "place", "feeling", "face", "glow", "scent", "street", "echo", "dream", "shore", "voice", "song", "path", "road", "room", "corner", "sound", "taste", "touch", "rhythm", "pattern", "routine", "stranger", "comfort", "silence"],
    "fleeting":   ["moment", "thought", "glimpse", "light", "dream", "shadow", "warmth", "memory", "echo", "joy", "smile", "glance", "visit", "season", "youth", "beauty", "fame", "peace", "calm", "breeze", "cloud", "rain", "snow", "touch", "feeling"],
}


# ============================================================================
# NOUN-NOUN COMPATIBILITY MATRIX
# ============================================================================

NOUN_NOUN_COMPAT: dict[str, list[str]] = {
    "rain":       ["shadow", "garden", "letter", "memory", "glass", "dance", "cycle", "light", "song", "loop", "cloud", "forest", "dream", "prayer", "whisper", "watch", "coat", "drop", "bow", "pool", "storm", "water", "fall", "maker", "bird"],
    "mist":       ["valley", "harbour", "shore", "garden", "morning", "hollow", "lake", "forest", "breath", "veil", "walker", "flower", "weaver", "dancer", "singer", "rider", "catcher", "born", "child", "song", "trail", "gate", "bell", "light", "fall"],
    "frost":      ["bloom", "morning", "glass", "petal", "breath", "light", "garden", "crystal", "silence", "ember", "bite", "work", "flower", "heave", "line", "fall", "song", "bell", "tone", "note", "lake", "creek", "shore", "trail", "gate"],
    "snow":       ["light", "globe", "drift", "silence", "fall", "bloom", "crystal", "field", "cap", "melt", "flake", "storm", "blind", "bird", "drop", "shoe", "line", "bank", "plow", "angel", "bell", "song", "lake", "trail", "gate"],
    "cloud":      ["break", "drift", "nine", "shadow", "rest", "cover", "garden", "burst", "layer", "bank", "gate", "walk", "song", "forest", "atlas", "map", "line", "top", "base", "seed", "light", "fall", "bell", "tone", "note"],
    "petal":      ["drift", "rain", "fall", "storm", "dance", "dust", "glow", "crush", "float", "trace", "song", "light", "shower", "carpet", "bloom", "wave", "trail", "gate", "bell", "tone", "note", "lake", "creek", "shore", "field"],
    "ember":      ["glow", "light", "drift", "trace", "fall", "warmth", "rest", "bloom", "dust", "haze", "song", "bell", "tone", "note", "lake", "creek", "shore", "trail", "gate", "field", "grove", "pool", "cove", "vale", "path"],
    "tide":       ["pool", "mark", "line", "drift", "turn", "song", "change", "loop", "flow", "break", "water", "gate", "bell", "tone", "note", "lake", "creek", "shore", "trail", "field", "grove", "cove", "vale", "path", "light"],
    "echo":       ["chamber", "loop", "drift", "garden", "lake", "trace", "pulse", "shore", "valley", "bloom", "song", "bell", "tone", "note", "field", "grove", "pool", "cove", "vale", "path", "light", "fall", "gate", "trail", "creek"],
    "silence":    ["bloom", "garden", "gold", "break", "keeper", "pool", "drift", "weave", "shore", "bell", "song", "tone", "note", "field", "grove", "lake", "creek", "trail", "gate", "vale", "path", "light", "fall", "cove", "watch"],
    "shadow":     ["dance", "play", "garden", "drift", "bloom", "cast", "rest", "puppet", "trace", "work", "song", "bell", "tone", "note", "field", "grove", "lake", "creek", "shore", "trail", "gate", "vale", "path", "light", "fall"],
    "memory":     ["lane", "loop", "foam", "garden", "bank", "trace", "drift", "palace", "well", "dust", "song", "bell", "tone", "note", "field", "grove", "lake", "creek", "shore", "trail", "gate", "vale", "path", "light", "fall"],
    "dream":      ["state", "drift", "catcher", "garden", "scape", "loop", "pool", "weaver", "land", "coast", "song", "bell", "tone", "note", "field", "grove", "lake", "creek", "shore", "trail", "gate", "vale", "path", "light", "fall"],
    "whisper":    ["rain", "field", "gallery", "wind", "thread", "garden", "trail", "tone", "drift", "grass", "song", "bell", "note", "grove", "lake", "creek", "shore", "gate", "vale", "path", "light", "fall", "pool", "cove", "wood"],
    "moment":     ["drift", "keeper", "glass", "garden", "pause", "loop", "capsule", "frame", "flash", "bloom", "song", "bell", "tone", "note", "field", "grove", "lake", "creek", "shore", "trail", "gate", "vale", "path", "light", "fall"],
    "drift":      ["wood", "light", "glow", "fall", "song", "shade", "stone", "bell", "note", "tone", "grove", "lake", "creek", "shore", "trail", "gate", "walk", "path", "rest", "leaf", "pool", "cove", "field", "bloom", "vale"],
    "flow":       ["state", "chart", "garden", "line", "stone", "bed", "drift", "rate", "cycle", "path", "song", "bell", "tone", "note", "field", "grove", "lake", "creek", "shore", "trail", "gate", "vale", "light", "fall", "pool"],
    "coffee":     ["table", "morning", "stain", "break", "shop", "ring", "filter", "steam", "bean", "bloom", "song", "bell", "tone", "note", "field", "grove", "house", "grounds", "pot", "cup", "mug", "press", "drip", "roast", "mill"],
    "candle":     ["light", "flame", "wax", "wick", "glow", "holder", "lit", "smoke", "drip", "warm", "song", "bell", "tone", "note", "field", "grove", "maker", "end", "stick", "power", "side", "night", "mass", "shade", "vigil"],
    "vinyl":      ["crackle", "static", "dust", "spin", "groove", "scratch", "hiss", "pop", "warmth", "tone", "song", "bell", "note", "field", "grove", "press", "cut", "side", "record", "player", "shop", "age", "days", "floor", "wrap"],
    "radio":      ["static", "wave", "tower", "dial", "signal", "silence", "hum", "crackle", "drift", "glow", "song", "bell", "tone", "note", "field", "head", "show", "play", "host", "star", "days", "city", "love", "garden", "active"],
    "glow":       ["worm", "stick", "stone", "cloud", "dust", "drift", "fade", "pulse", "trace", "ring", "song", "bell", "tone", "note", "field", "grove", "lake", "creek", "shore", "trail", "light", "fall", "pool", "cove", "vale"],
    "moonlight":  ["garden", "sonata", "swim", "dance", "shadow", "drift", "shore", "path", "walk", "bay", "song", "bell", "serenade", "drive", "mile", "kiss", "scene", "glow", "gleam", "pool", "lake", "creek", "trail", "gate", "field"],
    "starlight":  ["garden", "lounge", "drift", "swim", "path", "gaze", "dust", "shore", "cruise", "mile", "song", "bell", "tone", "note", "field", "grove", "lake", "creek", "trail", "gate", "vale", "glow", "pool", "cove", "express"],
    "lamplight":  ["glow", "halo", "shadow", "reading", "warmth", "corner", "pool", "haze", "flicker", "dust", "song", "bell", "tone", "note", "field", "grove", "lake", "creek", "shore", "trail", "gate", "vale", "path", "fall", "cove"],
}


# ============================================================================
# COLOR-NOUN COMPATIBILITY MATRIX
# ============================================================================

COLOR_NOUN_COMPAT: dict[str, list[str]] = {
    "indigo":     ["night", "hour", "dream", "dusk", "sky", "tide", "haze", "drift", "rain", "shadow", "ocean", "velvet", "ink", "mood", "dawn", "winter", "silence", "depth", "current", "horizon", "canvas", "thread", "bloom", "pool", "cove"],
    "amber":      ["glow", "light", "afternoon", "hour", "warmth", "leaf", "ember", "dusk", "tone", "haze", "ale", "wave", "sunset", "resin", "field", "honey", "grain", "dust", "autumn", "lamp", "glass", "bottle", "bead", "flame", "stream"],
    "ivory":      ["tower", "key", "morning", "coast", "bloom", "dust", "dream", "light", "snow", "glow", "lace", "silk", "bone", "stone", "moon", "pearl", "cloud", "petal", "shade", "tusk", "gate", "hall", "arch", "column", "pillar"],
    "coral":      ["reef", "dawn", "bloom", "shore", "dust", "light", "sunset", "bay", "garden", "glow", "sea", "pink", "island", "sand", "shell", "branch", "formation", "castle", "cave", "atoll", "lagoon", "tide", "water", "bed", "grove"],
    "sage":       ["garden", "hill", "morning", "wisdom", "brush", "field", "smoke", "leaf", "tea", "tone", "advice", "green", "plant", "herb", "bush", "grove", "meadow", "forest", "valley", "mountain", "creek", "shore", "trail", "path", "bloom"],
    "slate":      ["sky", "morning", "grey", "roof", "path", "tone", "coast", "cold", "rain", "dusk", "blue", "board", "stone", "mountain", "cliff", "wall", "floor", "tile", "quarry", "mine", "ledge", "ridge", "peak", "tower", "cave"],
    "mauve":      ["dusk", "sky", "dream", "haze", "morning", "bloom", "twilight", "hour", "tone", "mist", "silk", "velvet", "shadow", "cloud", "sunset", "petal", "orchid", "lavender", "wine", "scarf", "curtain", "dress", "ribbon", "dust", "light"],
    "ochre":      ["dust", "field", "light", "warmth", "clay", "path", "tone", "earth", "sun", "haze", "wall", "sand", "stone", "canyon", "desert", "mesa", "bluff", "ridge", "plateau", "terrain", "soil", "pigment", "wash", "stain", "glaze"],
    "sienna":     ["dust", "earth", "warmth", "clay", "sunset", "tone", "hill", "field", "ember", "glow", "burnt", "raw", "sky", "wall", "stone", "canyon", "desert", "mesa", "bluff", "ridge", "plateau", "terrace", "pigment", "wash", "stain"],
    "cerulean":   ["sky", "dream", "coast", "bay", "morning", "drift", "lake", "tide", "shimmer", "hour", "sea", "wave", "pool", "ocean", "water", "blue", "horizon", "depth", "surface", "glass", "ice", "crystal", "gem", "eye", "dome"],
    "cobalt":     ["hour", "night", "sky", "dream", "depth", "tone", "dusk", "shade", "chill", "drift", "blue", "sea", "glass", "bottle", "mine", "ore", "vein", "crystal", "ice", "flame", "spark", "light", "glow", "shadow", "moon"],
    "crimson":    ["dusk", "ember", "leaf", "sunset", "bloom", "dawn", "glow", "sky", "hour", "tide", "rose", "wine", "velvet", "silk", "thread", "ribbon", "flame", "fire", "autumn", "petal", "blood", "sun", "moon", "star", "cloud"],
    "rust":       ["belt", "tone", "leaf", "autumn", "dust", "glow", "ember", "garden", "warmth", "light", "color", "stain", "patch", "fence", "gate", "rail", "bridge", "chain", "lock", "key", "nail", "wire", "pipe", "bucket", "roof"],
    "peach":      ["bloom", "dawn", "glow", "light", "sky", "morning", "summer", "fuzz", "haze", "tone", "tree", "orchard", "cobbler", "pit", "seed", "blossom", "nectar", "juice", "skin", "flesh", "sunset", "cloud", "petal", "garden", "field"],
    "lilac":      ["dream", "dusk", "haze", "bloom", "morning", "breeze", "garden", "mist", "sky", "hour", "bush", "tree", "petal", "scent", "perfume", "spring", "field", "meadow", "lane", "path", "shade", "twilight", "wine", "silk", "lace"],
    "lavender":   ["field", "dream", "haze", "dusk", "mist", "rain", "morning", "breeze", "bloom", "tone", "oil", "scent", "perfume", "garden", "meadow", "hill", "valley", "path", "lane", "row", "bush", "plant", "herb", "tea", "soap"],
    "charcoal":   ["sketch", "morning", "sky", "rain", "dusk", "tone", "shadow", "dust", "night", "smoke", "drawing", "pencil", "filter", "grill", "fire", "ember", "ash", "grey", "dark", "black", "smudge", "stain", "mark", "line", "stroke"],
    "teal":       ["water", "coast", "dream", "drift", "bay", "tide", "morning", "tone", "pool", "shimmer", "sea", "ocean", "lake", "river", "green", "blue", "glass", "gem", "eye", "light", "shadow", "mist", "fog", "haze", "dusk"],
    "copper":     ["glow", "tone", "light", "wire", "warmth", "leaf", "ember", "autumn", "dusk", "bell", "pipe", "pot", "kettle", "pan", "coin", "penny", "mine", "ore", "vein", "roof", "dome", "sunset", "sunrise", "age", "patina"],
    "gold":       ["hour", "light", "leaf", "dust", "glow", "morning", "thread", "ember", "coast", "warmth", "mine", "rush", "field", "ring", "chain", "coin", "bar", "standard", "age", "en", "fish", "finch", "crest", "gate", "lock"],
    "silver":     ["lining", "light", "moon", "thread", "rain", "frost", "stream", "tone", "bell", "lake", "screen", "fox", "fish", "mine", "coin", "tongue", "spoon", "needle", "birch", "willow", "fern", "dust", "hair", "age", "arrow"],
    "bronze":     ["light", "glow", "tone", "warmth", "autumn", "bell", "hour", "leaf", "ember", "dusk", "age", "statue", "medal", "coin", "shield", "gate", "door", "skin", "sunset", "patina", "cast", "figure", "horse", "eagle", "star"],
    "pearl":      ["morning", "glow", "coast", "dive", "light", "moon", "tone", "harbour", "mist", "dawn", "oyster", "necklace", "string", "drop", "gate", "white", "grey", "river", "harbor", "bay", "island", "diver", "fisher", "dust", "shimmer"],
    "opal":       ["dream", "light", "glow", "shimmer", "morning", "dusk", "tone", "sky", "coast", "mist", "fire", "mine", "eye", "gem", "stone", "glass", "ice", "crystal", "lake", "pool", "sea", "wave", "cloud", "moon", "star"],
    "jade":       ["garden", "dream", "temple", "pool", "coast", "stone", "light", "tone", "morning", "mist", "green", "plant", "tree", "mountain", "river", "emperor", "dragon", "pendant", "bracelet", "carving", "gate", "palace", "tower", "bridge", "fountain"],
}


# ============================================================================
# THREE-WORD PHRASE TEMPLATES
# ============================================================================

THREE_WORD_TEMPLATES: list[tuple[str, float]] = [
    ("adj_noun_noun", 0.25),
    ("color_adj_noun", 0.15),
    ("noun_prep_noun", 0.30),
    ("noun_conj_noun", 0.15),
    ("adj_noun_prep_noun", 0.15),
]


# ============================================================================
# EXPANDED FRAGMENT TEMPLATES (40+ total, many multi-slot)
# ============================================================================

FRAGMENT_TEMPLATES: list[str] = [
    # 1-slot templates
    "for when it's {cozy_adj}",
    "i wish it would never stop {gerund}",
    "the last {abstract_nouns}",
    "before the {nature_nouns}",
    "after the {weather_word}",
    "nothing like {abstract_nouns}",
    "almost {time_single}",
    "somewhere near {real_places}",
    "letters from {real_places}",
    "waiting for {nature_nouns}",
    "so {abstract_adj} it hurts",
    "if only for a {time_unit}",
    "at first there was {nature_nouns}",
    "{abstract_adj} enough",
    "the sound of {nature_nouns}",
    "days like {seasons}",
    "when the {nature_nouns} comes",
    "slowly, {adverb}",
    "still {gerund}",
    "how it {verb_simple}",
    "things i never {verb_past}",
    "everything {abstract_adj}",
    "not yet {gerund}",
    "always {gerund}",
    "no more {nature_nouns}",
    "one last {abstract_nouns}",
    "half-remembered {abstract_nouns}",
    "left on the {cozy_nouns}",
    "the weight of {abstract_nouns}",
    "just before {time_single}",
    "{gerund} alone",
    "miles from {real_places}",
    "the color of {nature_nouns}",
    # 2-slot templates
    "a {abstract_adj} kind of {emotions}",
    "{cozy_adj} {time_single} in {real_places}",
    "the {abstract_adj} side of {abstract_nouns}",
    "{nature_nouns} after {nature_nouns}",
    "somewhere between {abstract_nouns} and {abstract_nouns2}",
    "i left my {cozy_nouns} in {real_places}",
    "the way {nature_nouns} {verb_simple}s",
    "{abstract_adj} {nature_nouns}, {abstract_adj2} {nature_nouns2}",
    "{gerund} through {nature_nouns}",
    "{colors} sky over {real_places}",
    "the {abstract_nouns} i keep in {cozy_nouns}",
    "{time_single} tastes like {nature_nouns}",
    "{nature_nouns} on the {cozy_nouns}",
    "from {real_places} with {emotions}",
    "{seasons} in {real_places}",
    "what {nature_nouns} sounds like at {time_single}",
    # 3-slot templates
    "{abstract_adj} {nature_nouns} on a {cozy_adj} {time_single}",
    "{gerund} past the {nature_nouns} in {real_places}",
    "a {colors} {abstract_nouns} near the {nature_nouns}",
]

GERUNDS: list[str] = [
    "raining", "snowing", "drifting", "floating", "fading", "glowing",
    "falling", "settling", "blooming", "melting", "dissolving", "turning",
    "humming", "breathing", "sleeping", "dreaming", "waking", "listening",
    "waiting", "watching", "walking", "running", "sitting", "standing",
    "reading", "writing", "thinking", "hoping", "wishing", "wondering",
    "spinning", "swaying", "flickering", "shimmering", "crackling",
]

TIME_UNITS: list[str] = [
    "day", "moment", "night", "while", "season", "week",
    "morning", "lifetime", "second", "heartbeat", "hour", "minute",
]

SIMPLE_VERBS: list[str] = [
    "was", "is", "feels", "ends", "starts", "begins", "stays",
    "goes", "fades", "breaks", "bends", "turns", "falls", "grows", "changes",
]

PAST_VERBS: list[str] = [
    "said", "sent", "kept", "found", "lost", "wrote", "heard", "felt",
    "meant", "knew", "held", "gave", "took", "made", "told", "read",
    "sang", "played", "built", "left",
]

ADVERBS: list[str] = [
    "gently", "quietly", "softly", "slowly", "carefully", "patiently",
    "surely", "lightly", "kindly", "easily", "simply", "tenderly",
    "gracefully", "steadily", "calmly", "warmly", "sweetly", "briefly",
]


# ============================================================================
# MICRO-MODIFIER POOLS
# ============================================================================

MICRO_SUFFIXES: list[str] = [
    "(dawn edit)", "(rain version)", "(slow)", "(acoustic)", "(piano)",
    "(late night)", "(early morning)", "(ambient)", "(tape)", "(demo)",
    "(extended)", "(reprise)", "(interlude)", "(outro)", "(intro)",
    "(moonlit)", "(frost mix)", "(dew mix)", "(haze)", "(mist)",
]

MICRO_PREFIXES: list[str] = [
    "no. 1", "no. 2", "no. 3", "no. 4", "no. 5", "no. 7", "no. 9",
    "side a:", "side b:", "track 01:", "track 02:", "track 03:",
]


# ============================================================================
# THEME DEFINITIONS
# ============================================================================

ThemeConfig = dict[str, any]

THEMES: dict[str, ThemeConfig] = {
    "rainy_melancholy": {
        "primary_pools": ["weather", "emotions", "nature_nouns", "abstract_nouns"],
        "adj_pools": ["nature_adj", "abstract_adj", "cozy_adj"],
        "weights": {
            "single": 0.15, "pair": 0.20, "triple": 0.15,
            "compound": 0.10, "fragment": 0.25, "place": 0.05, "micro": 0.10,
        },
        "preferred_case": "lower",
    },
    "cozy_domestic": {
        "primary_pools": ["cozy_nouns", "light_nouns", "textures"],
        "adj_pools": ["cozy_adj", "abstract_adj", "colors"],
        "weights": {
            "single": 0.15, "pair": 0.25, "triple": 0.10,
            "compound": 0.15, "fragment": 0.20, "place": 0.05, "micro": 0.10,
        },
        "preferred_case": "lower",
    },
    "wanderlust_travel": {
        "primary_pools": ["real_places", "imagined_places", "movement_nouns", "place_suffixes"],
        "adj_pools": ["nature_adj", "abstract_adj"],
        "weights": {
            "single": 0.10, "pair": 0.15, "triple": 0.15,
            "compound": 0.10, "fragment": 0.15, "place": 0.25, "micro": 0.10,
        },
        "preferred_case": "title",
    },
    "nocturnal": {
        "primary_pools": ["time_nouns", "time_phrases", "light_nouns", "abstract_nouns"],
        "adj_pools": ["abstract_adj", "colors"],
        "weights": {
            "single": 0.15, "pair": 0.20, "triple": 0.15,
            "compound": 0.10, "fragment": 0.25, "place": 0.05, "micro": 0.10,
        },
        "preferred_case": "lower",
    },
    "pastoral_nature": {
        "primary_pools": ["nature_nouns", "seasons", "nature_adj"],
        "adj_pools": ["nature_adj", "colors"],
        "weights": {
            "single": 0.15, "pair": 0.20, "triple": 0.15,
            "compound": 0.15, "fragment": 0.15, "place": 0.10, "micro": 0.10,
        },
        "preferred_case": "mixed",
    },
}

# All generation paths (micro is applied post-hoc, not a separate path)
GENERATION_PATHS: list[str] = ["single", "pair", "triple", "compound", "fragment", "place"]


# ============================================================================
# GENERATOR CLASS
# ============================================================================

@dataclass
class TrackNameGenerator:
    """Generates lo-fi track names with theme-aware weighted path selection."""

    seed: Optional[int] = None
    rng: random.Random = field(default_factory=random.Random, init=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed) if self.seed is not None else random.Random()

    # -- RNG helpers ---------------------------------------------------------

    def _pick_from_pool(self, pool_name: str) -> str:
        """Pick a random word from a named pool in POOLS."""
        return self.rng.choice(POOLS[pool_name])

    def _pick_from_list(self, lst: list[str]) -> str:
        """Pick a random element from an arbitrary list."""
        return self.rng.choice(lst)

    # -- Single Word ---------------------------------------------------------

    def _generate_single(self, pools: Optional[list[str]] = None) -> str:
        """Generate a single word from the given pool names."""
        if pools is None:
            pools = [
                "nature_nouns", "emotions", "abstract_nouns", "colors",
                "movement_nouns", "light_nouns", "cozy_nouns", "seasons",
            ]
        return self._pick_from_pool(self.rng.choice(pools))

    # -- Two-Word Pair (compat matrix) ---------------------------------------

    def _generate_pair(
        self,
        adj_pools: Optional[list[str]] = None,
        noun_pools: Optional[list[str]] = None,
    ) -> str:
        """Generate a two-word name using compatibility matrices."""
        strategy = self.rng.choices(
            ["adj_noun", "noun_noun", "color_noun"],
            weights=[0.50, 0.30, 0.20],
        )[0]

        if strategy == "adj_noun":
            return self._pair_adj_noun(adj_pools)
        elif strategy == "noun_noun":
            return self._pair_noun_noun(noun_pools)
        return self._pair_color_noun()

    def _pair_adj_noun(self, adj_pools: Optional[list[str]] = None) -> str:
        """Pick an adjective with a compatible noun from ADJ_NOUN_COMPAT."""
        pools = adj_pools or ["nature_adj", "abstract_adj", "cozy_adj"]
        for _ in range(30):
            adj = self._pick_from_pool(self.rng.choice(pools))
            if adj in ADJ_NOUN_COMPAT:
                return f"{adj} {self._pick_from_list(ADJ_NOUN_COMPAT[adj])}"
        adj = self._pick_from_list(list(ADJ_NOUN_COMPAT.keys()))
        return f"{adj} {self._pick_from_list(ADJ_NOUN_COMPAT[adj])}"

    def _pair_noun_noun(self, noun_pools: Optional[list[str]] = None) -> str:
        """Pick two nouns using NOUN_NOUN_COMPAT."""
        pools = noun_pools or ["nature_nouns", "abstract_nouns", "light_nouns", "cozy_nouns"]
        for _ in range(30):
            n1 = self._pick_from_pool(self.rng.choice(pools))
            if n1 in NOUN_NOUN_COMPAT:
                return f"{n1} {self._pick_from_list(NOUN_NOUN_COMPAT[n1])}"
        n1 = self._pick_from_list(list(NOUN_NOUN_COMPAT.keys()))
        return f"{n1} {self._pick_from_list(NOUN_NOUN_COMPAT[n1])}"

    def _pair_color_noun(self) -> str:
        """Pick a color with a compatible noun from COLOR_NOUN_COMPAT."""
        for _ in range(30):
            c = self._pick_from_pool("colors")
            if c in COLOR_NOUN_COMPAT:
                return f"{c} {self._pick_from_list(COLOR_NOUN_COMPAT[c])}"
        c = self._pick_from_list(list(COLOR_NOUN_COMPAT.keys()))
        return f"{c} {self._pick_from_list(COLOR_NOUN_COMPAT[c])}"

    # -- Three-Word Combo ----------------------------------------------------

    def _generate_triple(self) -> str:
        """Generate a three-word phrase from weighted templates."""
        templates = [t for t, _ in THREE_WORD_TEMPLATES]
        weights = [w for _, w in THREE_WORD_TEMPLATES]
        tmpl = self.rng.choices(templates, weights=weights)[0]

        dispatch = {
            "adj_noun_noun": self._triple_adj_noun_noun,
            "color_adj_noun": self._triple_color_adj_noun,
            "noun_prep_noun": self._triple_noun_prep_noun,
            "noun_conj_noun": self._triple_noun_conj_noun,
            "adj_noun_prep_noun": self._triple_adj_noun_prep_noun,
        }
        return dispatch[tmpl]()

    def _triple_adj_noun_noun(self) -> str:
        adj = self._pick_from_list(list(ADJ_NOUN_COMPAT.keys()))
        n1 = self._pick_from_list(ADJ_NOUN_COMPAT[adj])
        if n1 in NOUN_NOUN_COMPAT:
            n2 = self._pick_from_list(NOUN_NOUN_COMPAT[n1])
        else:
            n2 = self._pick_from_pool("abstract_nouns")
        return f"{adj} {n1} {n2}"

    def _triple_color_adj_noun(self) -> str:
        c = self._pick_from_list(list(COLOR_NOUN_COMPAT.keys()))
        adj = self._pick_from_list(list(ADJ_NOUN_COMPAT.keys()))
        noun = self._pick_from_list(ADJ_NOUN_COMPAT[adj])
        return f"{c} {adj} {noun}"

    def _triple_noun_prep_noun(self) -> str:
        n1_key = self._pick_from_list(list(NOUN_NOUN_COMPAT.keys()))
        prep = self._pick_from_pool("prepositions")
        n2_key = self._pick_from_list(list(NOUN_NOUN_COMPAT.keys()))
        return f"{n1_key} {prep} {n2_key}"

    def _triple_noun_conj_noun(self) -> str:
        n1 = self._pick_from_pool("nature_nouns")
        conj = self._pick_from_pool("conjunctions")
        n2 = self._pick_from_pool("abstract_nouns")
        return f"{n1} {conj} {n2}"

    def _triple_adj_noun_prep_noun(self) -> str:
        adj = self._pick_from_list(list(ADJ_NOUN_COMPAT.keys()))
        n1 = self._pick_from_list(ADJ_NOUN_COMPAT[adj])
        prep = self._pick_from_list(["on", "in", "by", "near", "under", "over", "through"])
        n2 = self._pick_from_pool("nature_nouns")
        return f"{adj} {n1} {prep} {n2}"

    # -- Compound Word -------------------------------------------------------

    def _generate_compound(self) -> str:
        """Generate a compound word by fusing a prefix and suffix."""
        for _ in range(30):
            prefix = self._pick_from_list(COMPOUND_PREFIXES)
            if prefix in COMPOUND_COMPAT:
                suffix = self._pick_from_list(COMPOUND_COMPAT[prefix])
                return prefix + suffix
        prefix = self._pick_from_list(list(COMPOUND_COMPAT.keys()))
        suffix = self._pick_from_list(COMPOUND_COMPAT[prefix])
        return prefix + suffix

    # -- Fragment ------------------------------------------------------------

    def _generate_fragment(self) -> str:
        """Generate a name from a fragment template with slot filling."""
        template = self._pick_from_list(FRAGMENT_TEMPLATES)
        return self._fill_template_slots(template)

    def _extract_weather_word(self) -> str:
        """Get a single weather word (first word of multi-word weather terms)."""
        w = self._pick_from_pool("weather")
        return w.split()[0] if " " in w else w

    def _extract_time_single(self) -> str:
        """Get a single time word (first word of multi-word time nouns)."""
        t = self._pick_from_pool("time_nouns")
        return t.split()[0] if " " in t else t

    def _fill_template_slots(self, template: str) -> str:
        """Replace all {slot} placeholders in a template string."""
        # Map slot names to callables that produce a replacement string.
        # Slots with a trailing "2" (e.g. abstract_nouns2) draw from the same
        # pool as their base name, allowing two independent picks.
        slot_resolvers: dict[str, callable] = {
            "cozy_adj":        lambda: self._pick_from_pool("cozy_adj"),
            "gerund":          lambda: self._pick_from_list(GERUNDS),
            "abstract_nouns2": lambda: self._pick_from_pool("abstract_nouns"),
            "abstract_nouns":  lambda: self._pick_from_pool("abstract_nouns"),
            "nature_nouns2":   lambda: self._pick_from_pool("nature_nouns"),
            "nature_nouns":    lambda: self._pick_from_pool("nature_nouns"),
            "weather_word":    self._extract_weather_word,
            "time_single":     self._extract_time_single,
            "real_places":     lambda: self._pick_from_pool("real_places"),
            "abstract_adj2":   lambda: self._pick_from_pool("abstract_adj"),
            "abstract_adj":    lambda: self._pick_from_pool("abstract_adj"),
            "adverb":          lambda: self._pick_from_list(ADVERBS),
            "time_unit":       lambda: self._pick_from_list(TIME_UNITS),
            "emotions":        lambda: self._pick_from_pool("emotions"),
            "seasons":         lambda: self._pick_from_pool("seasons"),
            "verb_simple":     lambda: self._pick_from_list(SIMPLE_VERBS),
            "verb_past":       lambda: self._pick_from_list(PAST_VERBS),
            "cozy_nouns":      lambda: self._pick_from_pool("cozy_nouns"),
            "colors":          lambda: self._pick_from_pool("colors"),
        }

        result = template
        replacements = 0
        while "{" in result and replacements < 10:
            replacements += 1
            replaced = False
            for slot_name, resolver in slot_resolvers.items():
                tag = "{" + slot_name + "}"
                if tag in result:
                    result = result.replace(tag, resolver(), 1)
                    replaced = True
                    break
            if not replaced:
                break
        return result

    # -- Place Name ----------------------------------------------------------

    def _generate_place(self) -> str:
        """Generate a place-based name from real, real+suffix, or imagined places."""
        strategy = self.rng.choices(
            ["real", "real_suffix", "imagined"],
            weights=[0.35, 0.40, 0.25],
        )[0]

        if strategy == "real":
            return self._pick_from_pool("real_places")
        elif strategy == "real_suffix":
            return f"{self._pick_from_pool('real_places')} {self._pick_from_pool('place_suffixes')}"
        return self._pick_from_pool("imagined_places")

    # -- Modifier Layer ------------------------------------------------------

    def _apply_case(self, name: str, style: str = "auto") -> str:
        """Apply casing: lower, title, sentence, or auto (weighted random)."""
        if style == "auto":
            style = self.rng.choices(
                ["lower", "title", "sentence"],
                weights=[0.55, 0.30, 0.15],
            )[0]

        if style == "lower":
            return name.lower()
        elif style == "title":
            return name.title()
        return name[0].upper() + name[1:].lower() if name else name

    def _apply_punctuation(self, name: str) -> str:
        """Occasionally append a period or ellipsis."""
        roll = self.rng.random()
        if roll < 0.06:
            return name + "."
        elif roll < 0.09:
            return name + "..."
        return name

    def _apply_suffix(self, name: str) -> str:
        """Occasionally append a part/volume indicator."""
        roll = self.rng.random()
        if roll < 0.03:
            return name + " Pt. 2"
        elif roll < 0.05:
            return name + " Vol. II"
        return name

    def _apply_micro_modifier(self, name: str) -> str:
        """Occasionally add a parenthetical tag or numeric prefix."""
        roll = self.rng.random()
        if roll < 0.06:
            return name + " " + self._pick_from_list(MICRO_SUFFIXES)
        elif roll < 0.09:
            return self._pick_from_list(MICRO_PREFIXES) + " " + name
        return name

    def _apply_modifiers(self, name: str, case_style: str) -> str:
        """Run the full modifier pipeline: case, punctuation, suffix, micro."""
        if case_style == "mixed":
            case_style = "auto"

        name = self._apply_case(name, style=case_style)
        name = self._apply_punctuation(name)
        name = self._apply_suffix(name)
        name = self._apply_micro_modifier(name)
        return name

    # -- Path Selection & Dispatch -------------------------------------------

    def _select_path(self, theme_weights: dict[str, float]) -> str:
        """Select a generation path based on theme weights."""
        weights = [theme_weights[p] for p in GENERATION_PATHS]
        return self.rng.choices(GENERATION_PATHS, weights=weights)[0]

    def _generate_by_path(self, path: str, theme_config: ThemeConfig) -> str:
        """Dispatch to the appropriate generation function for the path."""
        if path == "single":
            return self._generate_single(theme_config["primary_pools"])
        elif path == "pair":
            return self._generate_pair(theme_config["adj_pools"], theme_config["primary_pools"])
        elif path == "triple":
            return self._generate_triple()
        elif path == "compound":
            return self._generate_compound()
        elif path == "fragment":
            return self._generate_fragment()
        else:
            return self._generate_place()

    # -- Main Generate -------------------------------------------------------

    def generate(self, theme: Optional[str] = None, count: int = 1) -> list[dict]:
        """Generate one or more track names, returning dicts with name/theme/method."""
        results: list[dict] = []
        for _ in range(count):
            chosen_theme = theme or self._pick_from_list(list(THEMES.keys()))
            config = THEMES[chosen_theme]

            path = self._select_path(config["weights"])
            raw = self._generate_by_path(path, config)
            name = self._apply_modifiers(raw, config.get("preferred_case", "auto"))

            results.append({
                "name": name,
                "theme": chosen_theme,
                "method": path,
            })
        return results


# ============================================================================
# PUBLIC API
# ============================================================================

def generate_track_names(
    theme: Optional[str] = None,
    count: int = 1,
    seed: Optional[int] = None,
) -> list[dict]:
    """Generate lo-fi track names.

    Args:
        theme: One of the 5 themes, or None for random theme per name.
               Valid themes: rainy_melancholy, cozy_domestic, wanderlust_travel,
               nocturnal, pastoral_nature
        count: Number of names to generate.
        seed: Optional RNG seed for reproducible output.

    Returns:
        A list of dicts, each with "name", "theme", and "method" keys.
    """
    generator = TrackNameGenerator(seed=seed)
    return generator.generate(theme=theme, count=count)


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    print("=" * 95)
    print("  LO-FI TRACK NAME GENERATOR -- 20 SIMULATED BATCHES")
    print("=" * 95)

    for run in range(1, 21):
        gen = TrackNameGenerator(seed=run * 42 + 7)
        theme_options: list[Optional[str]] = [None] + list(THEMES.keys())
        chosen = gen._pick_from_list(theme_options)
        label = chosen or "mixed"
        results = gen.generate(theme=chosen, count=10)

        print(f"\n{'─' * 95}")
        print(f"  RUN {run:02d}  |  Theme: {label}")
        print(f"{'─' * 95}")
        print(f"  {'#':<4} {'Track Name':<55} {'Path':<15} {'Theme'}")
        print(f"  {'─'*3}  {'─'*53}  {'─'*13}  {'─'*20}")

        for i, r in enumerate(results, 1):
            print(f"  {i:<4} {r['name']:<55} {r['method']:<15} {r['theme']}")

    print(f"\n{'=' * 95}")
    print("  END OF SIMULATION")
    print(f"{'=' * 95}")
