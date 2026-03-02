"""
City Pop Track Name Generator
==============================
Generates track names in the style of 1980s Japanese city pop:
Tatsuro Yamashita, Mariya Takeuchi, Anri, Taeko Ohnuki, Junko Ohashi,
Toshiki Kadomatsu, Omega Tribe, plus modern revival (Night Tempo).

Style Distribution:
  1. Romantic Phrase     (25%)  - "Stay With Me", "Magic Ways"
  2. Summer / Coastal    (17%)  - "Last Summer Whisper", "Ocean Breeze"
  3. Urban Nightlife     (13%)  - "Midnight Pretenders", "City Lights"
  4. Single Word         (10%)  - "Sparkle", "Fantasy", "Neon"
  5. Japanese Phrase     (10%)  - "Kaze no Melody", "Mayonaka no Door"
  6. Character Reference  (5%)  - "Dreaming Girl", "Paper Doll"
  7. Dance/Music Ref      (5%)  - "Disco Communication", "Let's Dance Baby"
  8. Color / Material     (3%)  - "Champagne", "Crystal", "Velvet"
  9. Three-Word Combo    (12%)  - cubic volume path

Conventions: Title Case (~85%), apostrophe gerunds, warm/romantic tone,
English-primary with Japanese romanization, never dark or aggressive.
"""
import random
from dataclasses import dataclass, field
from typing import Optional

# ============================================================================
# WORD POOLS
# ============================================================================

ROMANTIC_VERBS = [
    "stay", "love", "hold", "kiss", "dance", "dream", "remember", "forget",
    "whisper", "touch", "fly", "run", "take", "give", "say", "tell", "call",
    "wait", "miss", "want", "need", "feel", "try", "find", "keep", "let",
    "come", "go", "believe", "smile", "cry", "shine", "glow", "sparkle",
    "promise", "wish", "hope", "trust", "reach", "catch", "follow",
]

ROMANTIC_NOUNS = [
    "love", "heart", "kiss", "dream", "night", "summer", "memory", "girl",
    "boy", "lady", "baby", "angel", "star", "moon", "sun", "eyes", "smile",
    "tears", "rain", "wind", "time", "morning", "magic", "music", "dance",
    "secret", "paradise", "heaven", "fantasy", "desire", "romance", "passion",
    "feeling", "emotion", "moment", "destiny", "chance", "fever", "melody",
    "rhythm", "story", "mystery", "wonder", "miracle", "treasure", "jewel",
    "flower", "petal", "rose", "perfume", "silk", "champagne", "diamond",
]

ROMANTIC_ADJ = [
    "sweet", "magic", "lonely", "tender", "gentle", "soft", "golden",
    "silver", "midnight", "moonlit", "starlit", "beautiful", "precious",
    "lovely", "dreamy", "misty", "rainy", "sunny", "warm", "cool",
    "secret", "silent", "quiet", "wild", "crazy", "endless", "eternal",
    "final", "last", "first", "new", "true", "real", "perfect",
    "special", "wonderful", "fantastic", "incredible", "amazing",
    "electric", "tropical", "cosmic", "crystal", "velvet", "satin",
]

APOSTROPHE_GERUNDS = [
    "Dancin'", "Talkin'", "Lovin'", "Dreamin'", "Cruisin'", "Runnin'",
    "Callin'", "Feelin'", "Groovin'", "Movin'", "Shakin'", "Makin'",
    "Takin'", "Givin'", "Livin'", "Drivin'", "Flyin'", "Cryin'",
    "Shinin'", "Burnin'", "Turnin'", "Reachin'", "Searchin'", "Wishin'",
    "Hopin'", "Waitin'", "Missin'", "Kissin'", "Touchin'", "Smilin'",
]

ROMANTIC_TEMPLATES = [
    "{V} With Me", "{V} Me {Adj}", "{V} to Me", "{V} Your {N}",
    "Let Me {V}", "Don't {V}", "Can't Stop {Ger}", "Never {V}",
    "{V} Me Far Away", "{V} Me Tonight", "{V} All Night",
    "{V} Back in {N}", "I {V} You So", "You Make Me {V}",
    "{Adj} {N}", "{N} {N2}", "Last {N}", "First {N}",
    "Sweet {N}", "Midnight {N}", "Summer {N}",
    "{N} of {N2}", "A {N} for You", "My {Adj} {N}", "Your {N}",
    "{Ger} All Night", "{Ger} in the {N}", "{Ger} With You",
    "{Ger} on the {N}", "Keep {Ger}",
    "{N} Is Forever", "Every {N}", "Only {N}", "One More {N}",
    "Say {N}", "After the {N}", "Before the {N}",
    "{Adj} Ways", "{N} Talk", "{Adj} Rendezvous",
    "{N} Story", "{Adj} Feeling", "{N} Connection", "{Adj} Nights",
]

# --- Summer / Coastal ---
SUMMER_NOUNS = [
    "summer", "beach", "ocean", "sea", "wave", "breeze", "palm", "sand",
    "sunset", "sunrise", "coast", "bay", "island", "reef", "shore", "tide",
    "surf", "paradise", "lagoon", "yacht", "marina", "harbor",
    "boardwalk", "pier", "promenade", "sail", "horizon",
    "coral", "seashell", "dolphin", "mermaid", "current", "swell",
]

SUMMER_ADJ = [
    "windy", "sunny", "tropical", "golden", "warm", "cool", "lazy",
    "endless", "last", "first", "late", "early", "hot", "hazy",
    "breezy", "balmy", "shimmering", "sparkling", "crystal",
    "turquoise", "cerulean", "sapphire", "azure", "pacific",
]

COASTAL_NOUNS = [
    "sea", "ocean", "bay", "beach", "shore", "coast", "reef", "island",
    "lagoon", "harbor", "marina", "cove", "cape", "pier", "boardwalk",
    "tide", "wave", "surf", "palm", "sand", "shell", "coral",
]

WIND_NOUNS = ["wind", "breeze", "gale", "gust", "zephyr", "trade wind"]

SUMMER_TEMPLATES = [
    "Summer {N}", "Summer {Adj}", "{Adj} Summer", "Last Summer {N}",
    "Remember Summer {N}", "Endless Summer",
    "{Coastal} {N}", "{Adj} {Coastal}", "Sea {N}", "Ocean {N}",
    "Bay {N}", "{Coastal} Line", "{Wind} {N}", "{Adj} {Wind}",
    "Caribbean {Wind}", "{Coastal} Serenade", "{Coastal} Dreams",
    "{Adj} Day by the {Coastal}", "Sailing to {Coastal}",
]

# --- Urban Nightlife ---
NIGHT_NOUNS = [
    "midnight", "moonlight", "starlight", "twilight", "evening", "dusk",
    "neon", "city", "lights", "street", "downtown", "tower", "rooftop",
    "highway", "boulevard", "avenue", "taxi", "skyline", "bridge",
    "station", "plaza", "disco", "club", "bar", "lounge", "terrace",
    "harbor", "cruise", "ride", "drive", "pretender", "confession",
]

NIGHT_ADJ = [
    "midnight", "neon", "electric", "downtown", "urban", "late",
    "all-night", "velvet", "smoky", "starlit", "moonlit",
    "city", "funky", "groovy", "cool", "slick",
]

NIGHT_CITIES = [
    "Tokyo", "Yokohama", "Osaka", "Shibuya", "Roppongi", "Ginza",
    "Shinjuku", "New York", "L.A.", "Paris", "Hong Kong", "Singapore",
    "Hawaii", "Monaco", "Waikiki", "Malibu", "Manhattan", "Rio",
    "Cannes", "Aoyama", "Ebisu", "Daikanyama", "Kobe", "Nagoya",
]

NIGHT_TIMES = [
    "4:00 A.M.", "3:00 A.M.", "2 A.M.", "Midnight", "11 P.M.",
    "After 5", "Quarter to 12", "Last Call",
]

NIGHT_DAYS = ["Friday", "Saturday", "Sunday", "Monday"]

NIGHT_TEMPLATES = [
    "Night {N}", "Midnight {N}", "{Adj} Night", "City {N}",
    "Night in {City}", "Rainy Night in {City}", "{N} at {Time}",
    "{Adj} {N}", "Friday {N}", "Saturday {N}", "After {Time}",
    "{City} Nights", "Downtown {N}", "{City} After Dark",
    "Neon {N}", "{City} {N}", "{Time}", "{Day} {N}",
]

# --- Single words (bright, energetic) ---
SINGLE_WORDS = [
    "Sparkle", "Fantasy", "Fragile", "Adventure", "September", "Neon",
    "Telephone", "Mermaid", "Timely", "Denim", "Flapper", "Lovesick",
    "Bomber", "Hurricane", "Silhouette", "Carousel", "Fascination",
    "Rendezvous", "Prism", "Mirage", "Illusion", "Masquerade",
    "Serenade", "Interlude", "Overture", "Encore", "Champagne",
    "Crystal", "Velvet", "Satin", "Silk", "Coral", "Diamond", "Gold",
    "Silver", "Pearl", "Emerald", "Ruby", "Sapphire", "Topaz", "Amber",
    "Ivory", "Jade", "Opal", "Twilight", "Daybreak", "Moonrise",
    "Stardust", "Sunbeam", "Kaleidoscope", "Pendulum", "Satellite",
    "Compass", "Voyager", "Cruiser", "Getaway", "Escapade", "Cabaret",
    "Tenderness", "Sweetness", "Loneliness", "Happiness", "Jealousy",
    "Nostalgia", "Ecstasy", "Euphoria", "Melancholy", "Devotion",
    "Affection", "Infatuation", "Temptation", "Hibiscus", "Jasmine",
    "Orchid", "Magnolia", "Gardenia", "Plumeria", "Freesia", "Camellia",
    "Azalea", "Wisteria", "Chanson", "Bijou", "Bravo", "Dolce",
    "Amore", "Bella", "Ciao", "Vogue", "Chic",
]

# --- Japanese phrase pools ---
JP_NOUNS = [
    "kaze", "umi", "sora", "yume", "ai", "hana", "natsu", "haru",
    "tsuki", "machi", "yoru", "ame", "hikari", "kokoro", "namida",
    "hoshi", "kumo", "niji", "kawa", "tori", "nami", "koi",
    "yuki", "aki", "fuyu", "hi", "mizu", "kage", "oto", "kaori",
    "tobira", "mado", "tegami", "hanabi", "sakura", "asa", "yuhi",
]

JP_EN_NOUNS = [
    "Melody", "Season", "Energy", "Door", "Telephone", "Lady", "Boy",
    "Night", "Summer", "Dream", "Paradise", "Fantasy", "Dance",
    "Music", "Story", "Magic", "Time", "Love", "Heart", "Star",
    "Boogie", "Disco", "Groove", "Rhythm", "Feeling", "Memory",
]

JP_EN_ADJ = [
    "Sweet", "Lovely", "Dreamy", "Funky", "Groovy", "Happy",
    "Cool", "Hot", "Special", "Beautiful", "Fantastic",
]

JP_TEMPLATES = [
    "{jp1} no {jp2}", "{jp1} no {en}", "Mayonaka no {jp2}",
    "Mayonaka no {en}", "{jp1} wa {en}", "{en_adj} na {jp1}",
    "Ai no {en}", "Koi no {en}", "{jp1} yo", "Koibito yo",
    "{jp1} Monogatari", "{jp1} no Naka e", "{jp1} e no {en}",
]

# --- Character / archetype ---
CHAR_ADJ = [
    "Dreaming", "Lonely", "Dancing", "Shining", "Crying", "Smiling",
    "Running", "Flying", "Falling", "Waiting", "Secret", "Mysterious",
    "Beautiful", "Pretty", "Lovely", "Sweet", "Wild", "Shy", "Cool",
    "Innocent", "Lucky", "Tender", "Gentle",
]

CHAR_ARCHETYPES = [
    "Girl", "Boy", "Lady", "Woman", "Princess", "Queen",
    "Doll", "Angel", "Mermaid", "Cat", "Butterfly", "Bird", "Dancer",
    "Singer", "Dreamer", "Lover", "Stranger", "Rider", "Traveler",
]

CHAR_MATERIALS = [
    "Paper", "Glass", "Velvet", "Crystal", "Silk", "Satin", "Neon",
    "Porcelain", "Golden", "Silver", "Moonlight", "Starlight",
]

CHAR_TEMPLATES = [
    "{Adj} {A}", "{Mat} {A}", "The {Adj} {A}",
    "{A} in the {N}", "My {Adj} {A}",
]

# --- Dance / Music ---
DANCE_VERBS = [
    "Dance", "Groove", "Boogie", "Swing", "Step", "Shuffle",
    "Sway", "Glide", "Spin", "Twist", "Shake", "Bounce",
]

DANCE_GENRES = [
    "Disco", "Funk", "Boogie", "Jazz", "Soul", "Bossa Nova",
    "Reggae", "Samba", "Salsa", "Tango", "Swing",
]

MUSIC_NOUNS = [
    "Music", "Song", "Melody", "Rhythm", "Beat", "Groove", "Tune",
    "Note", "Chord", "Harmony", "Bass", "Piano", "Guitar",
    "Saxophone", "Synthesizer", "Record", "Vinyl", "Radio",
]

DANCE_TEMPLATES = [
    "Let's {DV}", "Let's {DV} Baby", "Let's {DV} Tonight",
    "{G} {MN}", "{G} Night", "{DV} the Night Away", "{DV} With Me",
    "{MN} Box", "{MN} Book", "Groove {MN}", "Funky {N}",
    "Boogie {N}", "Disco {N}", "{G} Fever", "{G} Connection",
]

# --- Materials (standalone) ---
MATERIAL_SINGLES = [
    "Neon", "Chrome", "Velvet", "Satin", "Silk", "Crystal", "Champagne",
    "Diamond", "Gold", "Silver", "Pearl", "Coral", "Jade", "Ivory",
    "Amber", "Ruby", "Sapphire", "Emerald", "Opal", "Topaz", "Platinum",
    "Porcelain", "Marble", "Copper", "Bronze", "Glass", "Mirror",
    "Prism", "Stardust", "Moonstone", "Sunstone",
]

# --- Compatibility matrices for quality two-word pairs ---
ROMANTIC_COMPAT = {
    "sweet":     ["memory", "melody", "dream", "kiss", "smile", "love", "paradise", "surrender", "escape", "music", "tears", "rain", "perfume", "desire", "magic", "romance", "feeling", "moment", "angel", "baby", "heart", "night", "fantasy", "heaven", "illusion"],
    "magic":     ["ways", "night", "touch", "kiss", "love", "moment", "feeling", "hour", "dance", "eyes", "summer", "melody", "dream", "time", "destiny", "music", "star", "moon", "rain", "wind", "spell", "paradise", "secret", "girl", "lady"],
    "lonely":    ["night", "heart", "girl", "boy", "star", "eyes", "tears", "rain", "feeling", "dream", "road", "summer", "city", "street", "wind", "moon", "shadow", "angel", "melody", "dance", "memory", "morning", "sunset", "voyage", "rider"],
    "tender":    ["love", "heart", "kiss", "night", "rain", "dream", "memory", "feeling", "touch", "moment", "melody", "eyes", "smile", "whisper", "morning", "evening", "summer", "breeze", "flower", "petal", "romance", "desire", "secret", "promise", "paradise"],
    "golden":    ["sun", "summer", "dream", "time", "hour", "moment", "morning", "sunset", "coast", "beach", "sand", "memory", "heart", "love", "star", "paradise", "melody", "rain", "wind", "eyes", "smile", "treasure", "age", "evening", "feeling"],
    "midnight":  ["love", "kiss", "dance", "dream", "rain", "wind", "star", "moon", "city", "drive", "cruise", "feeling", "secret", "rendezvous", "romance", "melody", "eyes", "tears", "heart", "angel", "fantasy", "escape", "pretender", "memory", "confession"],
    "moonlit":   ["night", "beach", "shore", "bay", "dream", "dance", "kiss", "love", "garden", "terrace", "balcony", "drive", "walk", "cruise", "memory", "feeling", "moment", "melody", "fantasy", "escape", "paradise", "romance", "ocean", "summer", "serenade"],
    "electric":  ["love", "night", "dream", "feeling", "dance", "kiss", "city", "summer", "fantasy", "desire", "romance", "eyes", "touch", "fever", "melody", "rhythm", "beat", "groove", "paradise", "escape", "heart", "star", "moon", "magic", "moment"],
    "endless":   ["summer", "night", "love", "dream", "rain", "road", "sky", "ocean", "dance", "feeling", "melody", "memory", "kiss", "star", "fantasy", "paradise", "desire", "romance", "heart", "time", "moment", "horizon", "coast", "voyage", "journey"],
    "secret":    ["love", "kiss", "night", "dream", "garden", "dance", "feeling", "desire", "romance", "rendezvous", "paradise", "escape", "fantasy", "heart", "eyes", "tears", "memory", "melody", "moment", "star", "moon", "place", "letter", "whisper", "meeting"],
    "crystal":   ["love", "night", "dream", "rain", "tear", "heart", "eyes", "memory", "moment", "feeling", "melody", "fantasy", "star", "moon", "ocean", "sky", "kiss", "touch", "paradise", "palace", "ball", "chandelier", "clear", "lake", "tower"],
    "velvet":    ["night", "moon", "dream", "kiss", "touch", "voice", "eyes", "rain", "sky", "love", "feeling", "melody", "memory", "romance", "desire", "paradise", "escape", "fantasy", "heart", "star", "city", "lounge", "curtain", "shadow", "whisper"],
    "wild":      ["heart", "love", "night", "dance", "dream", "eyes", "kiss", "summer", "feeling", "desire", "romance", "fantasy", "escape", "paradise", "wind", "rain", "ocean", "wave", "fever", "passion", "flower", "rose", "fire", "flame", "adventure"],
    "rainy":     ["night", "morning", "city", "street", "memory", "dream", "love", "feeling", "melody", "kiss", "heart", "tears", "window", "afternoon", "evening", "walk", "drive", "mood", "taxi", "boulevard", "bridge", "harbor", "balcony", "day", "season"],
    "first":     ["love", "kiss", "dance", "dream", "summer", "night", "morning", "feeling", "touch", "time", "step", "star", "rain", "date", "meeting", "impression", "sight", "light", "day", "memory", "moment", "chance", "flight", "voyage", "snow"],
    "last":      ["summer", "night", "dance", "kiss", "love", "dream", "chance", "train", "flight", "call", "feeling", "memory", "moment", "rain", "song", "waltz", "tango", "rendezvous", "goodbye", "whisper", "resort", "paradise", "cruise", "letter", "time"],
    "dreamy":    ["night", "summer", "love", "eyes", "kiss", "feeling", "melody", "memory", "paradise", "fantasy", "escape", "romance", "desire", "heart", "star", "moon", "rain", "breeze", "ocean", "beach", "sunset", "moment", "dance", "girl", "lady"],
    "tropical":  ["night", "breeze", "paradise", "island", "rain", "summer", "sunset", "beach", "ocean", "lagoon", "escape", "dream", "fever", "cruise", "resort", "bay", "cove", "harbor", "garden", "flower", "storm", "cocktail", "bird", "fish", "love"],
    "cosmic":    ["love", "dream", "dance", "feeling", "melody", "night", "star", "moon", "fantasy", "desire", "romance", "paradise", "escape", "heart", "eyes", "ray", "wave", "energy", "voyage", "rider", "adventure", "connection", "rendezvous", "explorer", "traveler"],
    "silent":    ["night", "love", "kiss", "tears", "rain", "dream", "memory", "feeling", "melody", "whisper", "moment", "heart", "star", "moon", "ocean", "breeze", "morning", "evening", "street", "city", "shadow", "promise", "prayer", "letter", "serenade"],
}

SUMMER_COMPAT = {
    "windy":      ["summer", "beach", "shore", "coast", "bay", "island", "boulevard", "boardwalk", "pier", "afternoon", "morning", "day", "evening", "sail", "harbor", "marina", "promenade", "terrace", "balcony", "drive", "cruise", "lady", "hill", "road", "girl"],
    "sunny":      ["morning", "day", "afternoon", "beach", "coast", "shore", "island", "side", "terrace", "balcony", "boardwalk", "drive", "cruise", "getaway", "escape", "holiday", "paradise", "feeling", "smile", "girl", "boy", "spot", "parade", "outlook", "disposition"],
    "tropical":   ["night", "breeze", "paradise", "island", "rain", "summer", "sunset", "beach", "ocean", "lagoon", "getaway", "escape", "dream", "fever", "storm", "cruise", "resort", "bay", "cove", "harbor", "cocktail", "garden", "bird", "flower", "fish"],
    "golden":     ["sunset", "sunrise", "beach", "sand", "coast", "shore", "summer", "afternoon", "evening", "hour", "wave", "light", "age", "time", "dream", "memory", "moment", "paradise", "bay", "cove", "harbor", "sail", "cruise", "horizon", "ray"],
    "endless":    ["summer", "beach", "shore", "coast", "ocean", "sea", "wave", "horizon", "sky", "sunset", "drive", "cruise", "voyage", "road", "highway", "boulevard", "night", "dream", "feeling", "love", "paradise", "blue", "sand", "tide", "current"],
    "lazy":       ["summer", "afternoon", "day", "morning", "beach", "cruise", "drift", "breeze", "tide", "wave", "hammock", "sunday", "holiday", "vacation", "getaway", "river", "bay", "cove", "harbor", "boardwalk", "stroll", "float", "swim", "sail", "sunset"],
    "crystal":    ["water", "sea", "ocean", "wave", "blue", "bay", "cove", "lagoon", "beach", "shore", "reef", "pool", "lake", "stream", "spring", "rain", "drop", "tear", "prism", "light", "clear", "palace", "ball", "glass", "chandelier"],
    "pacific":    ["coast", "ocean", "breeze", "dream", "sunset", "sunrise", "shore", "wave", "island", "cruise", "highway", "boulevard", "horizon", "blue", "current", "tide", "wind", "summer", "paradise", "bay", "cove", "harbor", "drive", "escape", "voyage"],
    "shimmering": ["ocean", "sea", "wave", "water", "light", "sun", "moon", "star", "sand", "heat", "mirage", "horizon", "surface", "pool", "lagoon", "bay", "coast", "shore", "reef", "pearl", "jewel", "silk", "satin", "dress", "tear"],
    "azure":      ["sky", "ocean", "sea", "coast", "bay", "dream", "horizon", "water", "wave", "lagoon", "pool", "cove", "paradise", "summer", "afternoon", "morning", "breeze", "shore", "island", "reef", "tide", "current", "light", "crystal", "blue"],
}

NIGHT_COMPAT = {
    "midnight":   ["pretender", "cruise", "rendezvous", "dance", "kiss", "rain", "drive", "run", "express", "lover", "dream", "city", "blue", "train", "girl", "hour", "show", "moon", "special", "confession", "caller", "rider", "sun", "cowboy", "oil"],
    "neon":       ["city", "lights", "sign", "dream", "night", "street", "glow", "rain", "love", "dance", "club", "boulevard", "district", "paradise", "fantasy", "heart", "fever", "angel", "rider", "cruise", "tower", "bridge", "highway", "skyline", "lounge"],
    "electric":   ["night", "city", "dream", "love", "dance", "feeling", "heart", "eyes", "kiss", "downtown", "paradise", "fantasy", "fever", "groove", "beat", "rhythm", "pulse", "shock", "slide", "blue", "lady", "avenue", "boulevard", "skyline", "tower"],
    "downtown":   ["boy", "girl", "lady", "night", "lights", "dance", "love", "groove", "beat", "fever", "club", "bar", "lounge", "street", "avenue", "boulevard", "disco", "funk", "jazz", "blues", "scene", "crowd", "life", "vibe", "soul"],
    "velvet":     ["night", "moon", "lounge", "curtain", "voice", "dream", "touch", "kiss", "eyes", "rain", "shadow", "city", "sky", "club", "room", "rope", "underground", "evening", "dusk", "twilight", "dark", "smooth", "soul", "heart", "bar"],
    "smoky":      ["night", "bar", "lounge", "club", "room", "voice", "eyes", "dream", "city", "street", "jazz", "blues", "soul", "feeling", "memory", "atmosphere", "mirror", "glass", "amber", "evening", "dusk", "twilight", "rain", "quartz", "topaz"],
    "starlit":    ["night", "sky", "dance", "dream", "love", "kiss", "beach", "shore", "ocean", "drive", "cruise", "walk", "garden", "terrace", "balcony", "rooftop", "boulevard", "highway", "city", "feeling", "memory", "moment", "romance", "rendezvous", "paradise"],
    "funky":      ["night", "town", "groove", "beat", "soul", "feeling", "dance", "lady", "girl", "boy", "love", "dream", "street", "boulevard", "downtown", "disco", "bass", "rhythm", "step", "shuffle", "slide", "drummer", "guitar", "horn", "brass"],
    "slick":      ["night", "city", "ride", "drive", "cruise", "love", "moves", "groove", "beat", "step", "style", "dream", "talk", "operator", "player", "cat", "back", "surface", "road", "rain", "streets", "downtown", "boulevard", "highway", "dealer"],
    "all-night":  ["dance", "party", "cruise", "drive", "love", "dream", "feeling", "groove", "beat", "rhythm", "session", "jam", "disco", "funk", "radio", "show", "flight", "train", "express", "confession", "conversation", "romance", "adventure", "escape", "fever"],
}

# Citypop prepositions for three-word combos
CITYPOP_PREPS = ["in", "on", "by", "for", "of", "with", "to", "from", "under", "after", "before"]

# Micro-modifier pools
MICRO_SUFFIXES = [
    "(Night Tempo Edit)", "(Remix)", "(Extended Mix)", "(Live)",
    "(Reprise)", "(Instrumental)", "(Single Version)", "(Album Version)",
    "(Radio Edit)", "(Dance Mix)", "(12\" Mix)", "(7\" Version)",
]


# ============================================================================
# GENERATOR
# ============================================================================

@dataclass
class CitypopTrackGenerator:
    seed: Optional[int] = None
    rng: random.Random = field(default_factory=random.Random, init=False)

    def __post_init__(self):
        self.rng = random.Random(self.seed) if self.seed is not None else random.Random()

    def _pick(self, lst): return self.rng.choice(lst)
    def _pick_compat(self, m):
        k = self._pick(list(m.keys())); return k, self._pick(m[k])

    def gen_romantic(self):
        t = self._pick(ROMANTIC_TEMPLATES); r = t
        if "{Adj}" in r and "{N}" in r:
            a, n = self._pick_compat(ROMANTIC_COMPAT)
            r = r.replace("{Adj}", a.capitalize(), 1).replace("{N}", n.capitalize(), 1)
        for tag, pool in [("{Adj}", ROMANTIC_ADJ), ("{Adj2}", ROMANTIC_ADJ),
                          ("{N}", ROMANTIC_NOUNS), ("{N2}", ROMANTIC_NOUNS),
                          ("{V}", ROMANTIC_VERBS)]:
            if tag in r: r = r.replace(tag, self._pick(pool).capitalize(), 1)
        if "{Ger}" in r: r = r.replace("{Ger}", self._pick(APOSTROPHE_GERUNDS), 1)
        return r

    def gen_summer(self):
        t = self._pick(SUMMER_TEMPLATES); r = t
        if "{Adj}" in r and "{Coastal}" in r:
            a, c = self._pick_compat(SUMMER_COMPAT)
            r = r.replace("{Adj}", a.capitalize(), 1).replace("{Coastal}", c.capitalize(), 1)
        for tag, pool in [("{Adj}", SUMMER_ADJ), ("{N}", SUMMER_NOUNS),
                          ("{N2}", SUMMER_NOUNS), ("{Coastal}", COASTAL_NOUNS),
                          ("{Wind}", WIND_NOUNS)]:
            if tag in r: r = r.replace(tag, self._pick(pool).capitalize(), 1)
        return r

    def gen_night(self):
        t = self._pick(NIGHT_TEMPLATES); r = t
        if "{Adj}" in r and "{N}" in r:
            a, n = self._pick_compat(NIGHT_COMPAT)
            r = r.replace("{Adj}", a.capitalize(), 1).replace("{N}", n.capitalize(), 1)
        for tag, pool in [("{Adj}", NIGHT_ADJ), ("{N}", NIGHT_NOUNS)]:
            if tag in r: r = r.replace(tag, self._pick(pool).capitalize(), 1)
        if "{City}" in r: r = r.replace("{City}", self._pick(NIGHT_CITIES), 1)
        if "{Time}" in r: r = r.replace("{Time}", self._pick(NIGHT_TIMES), 1)
        if "{Day}" in r: r = r.replace("{Day}", self._pick(NIGHT_DAYS), 1)
        return r

    def gen_single(self): return self._pick(SINGLE_WORDS)

    def gen_japanese(self):
        t = self._pick(JP_TEMPLATES); r = t
        if "{jp1}" in r: r = r.replace("{jp1}", self._pick(JP_NOUNS).capitalize(), 1)
        if "{jp2}" in r: r = r.replace("{jp2}", self._pick(JP_NOUNS).capitalize(), 1)
        if "{en}" in r: r = r.replace("{en}", self._pick(JP_EN_NOUNS), 1)
        if "{en_adj}" in r: r = r.replace("{en_adj}", self._pick(JP_EN_ADJ), 1)
        return r

    def gen_character(self):
        t = self._pick(CHAR_TEMPLATES); r = t
        if "{Adj}" in r: r = r.replace("{Adj}", self._pick(CHAR_ADJ), 1)
        if "{A}" in r: r = r.replace("{A}", self._pick(CHAR_ARCHETYPES), 1)
        if "{Mat}" in r: r = r.replace("{Mat}", self._pick(CHAR_MATERIALS), 1)
        if "{N}" in r: r = r.replace("{N}", self._pick(ROMANTIC_NOUNS).capitalize(), 1)
        return r

    def gen_dance(self):
        t = self._pick(DANCE_TEMPLATES); r = t
        if "{DV}" in r: r = r.replace("{DV}", self._pick(DANCE_VERBS), 1)
        if "{G}" in r: r = r.replace("{G}", self._pick(DANCE_GENRES), 1)
        if "{MN}" in r: r = r.replace("{MN}", self._pick(MUSIC_NOUNS), 1)
        if "{N}" in r: r = r.replace("{N}", self._pick(ROMANTIC_NOUNS).capitalize(), 1)
        return r

    def gen_material(self): return self._pick(MATERIAL_SINGLES)

    def gen_three_word(self):
        roll = self.rng.random()
        if roll < 0.35:
            a, n1 = self._pick_compat(ROMANTIC_COMPAT)
            n2 = self._pick(ROMANTIC_NOUNS)
            return f"{a.capitalize()} {n1.capitalize()} {n2.capitalize()}"
        elif roll < 0.60:
            n1 = self._pick(ROMANTIC_NOUNS)
            p = self._pick(CITYPOP_PREPS)
            n2 = self._pick(ROMANTIC_NOUNS)
            return f"{n1.capitalize()} {p.capitalize()} {n2.capitalize()}"
        elif roll < 0.80:
            a, n1 = self._pick_compat(SUMMER_COMPAT)
            n2 = self._pick(SUMMER_NOUNS)
            return f"{a.capitalize()} {n1.capitalize()} {n2.capitalize()}"
        else:
            a, n1 = self._pick_compat(NIGHT_COMPAT)
            n2 = self._pick(NIGHT_NOUNS)
            return f"{a.capitalize()} {n1.capitalize()} {n2.capitalize()}"

    def apply_modifiers(self, name):
        if self.rng.random() < 0.85: name = name.title()
        elif self.rng.random() < 0.5: name = name[0].upper() + name[1:] if name else name
        if self.rng.random() < 0.04: name += " " + self._pick(MICRO_SUFFIXES)
        return name

    def generate(self, count=1):
        STYLES = [("romantic", 0.25), ("summer", 0.17), ("night", 0.13),
                  ("single", 0.10), ("japanese", 0.10), ("character", 0.05),
                  ("dance", 0.05), ("material", 0.03), ("three_word", 0.12)]
        names, weights = zip(*STYLES)
        results = []
        for _ in range(count):
            s = self.rng.choices(names, weights=weights, k=1)[0]
            raw = getattr(self, f"gen_{s}")()
            results.append({"name": self.apply_modifiers(raw), "style": s})
        return results


# ============================================================================
# PUBLIC API
# ============================================================================

def generate_track_names(
    count: int = 1,
    seed: Optional[int] = None,
) -> list[dict]:
    """Generate city pop track names.

    Returns:
        A list of dicts, each with "name" and "style" keys.
    """
    generator = CitypopTrackGenerator(seed=seed)
    return generator.generate(count=count)
