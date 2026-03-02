"""
Genre-aware Album Name Generator
==================================
Dispatches to category-specific album naming based on genre category.

- lofi: Uses the existing track name generator (warm, cozy, ambient)
- citypop: Warm, romantic, seasonal — mirrors citypop track vocabulary
- synthwave: Hard-edged, tech, cinematic — mirrors synthwave track vocabulary
"""
import random
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# CITYPOP ALBUM POOLS
# ============================================================================

# Season / Time of Day (25%)
CP_SEASON_ADJ = [
    "Summer", "Winter", "Autumn", "Spring", "Midnight", "Twilight",
    "Evening", "Morning", "Late Night", "Early Morning", "Golden Hour",
    "September", "August", "July", "June",
]
CP_SEASON_NOUNS = [
    "Collection", "Serenade", "Rendezvous", "Memories", "Stories",
    "Letters", "Diary", "Journal", "Melodies", "Sessions",
    "Dreams", "Whispers", "Moments", "Portraits", "Pages",
]

# Location (20%)
CP_LOCATIONS = [
    "Tokyo", "Yokohama", "Osaka", "Shibuya", "Roppongi", "Ginza",
    "Shinjuku", "Kobe", "Kamakura", "Harajuku", "Aoyama", "Ebisu",
    "Daikanyama", "Waikiki", "Malibu", "Monaco", "Cannes", "Rio",
]
CP_LOCATION_NOUNS = [
    "Serenade", "Stories", "Nights", "Boulevard", "Diary",
    "Postcards", "Letters", "Sessions", "Memories", "Dreams",
    "Connection", "Rendezvous", "Affair", "Collection", "Souvenir",
]

# Romantic (20%)
CP_ROMANTIC_ADJ = [
    "Sweet", "Tender", "Gentle", "Lovely", "Dreamy", "Moonlit",
    "Starlit", "Magic", "Secret", "Endless", "Crystal", "Velvet",
    "Golden", "Silent", "Precious", "Beautiful",
]
CP_ROMANTIC_NOUNS = [
    "Memories", "Moments", "Dreams", "Hearts", "Melodies",
    "Feelings", "Whispers", "Promises", "Kisses", "Letters",
    "Confessions", "Fantasies", "Illusions", "Desires", "Portraits",
]

# Material / Luxury (10%)
CP_MATERIAL_ADJ = [
    "Champagne", "Crystal", "Velvet", "Silk", "Satin", "Diamond",
    "Pearl", "Gold", "Silver", "Coral", "Jade", "Ivory",
]
CP_MATERIAL_NOUNS = [
    "Collection", "Sessions", "Suite", "Affair", "Edition",
    "Anthology", "Treasury", "Archives", "Gallery", "Selection",
]

# Japanese phrase (15%)
CP_JP_WORDS = [
    "Kaze", "Umi", "Sora", "Yume", "Hana", "Natsu", "Tsuki",
    "Hoshi", "Nami", "Hikari", "Kokoro", "Sakura", "Ame", "Yoru",
]
CP_JP_EN_NOUNS = [
    "Album", "Melody", "Story", "Collection", "Dream", "Memory",
    "Fantasy", "Paradise", "Season", "Diary", "Letter", "Serenade",
]

# Single evocative word (10%)
CP_SINGLE_WORDS = [
    "Fascination", "Nostalgia", "Rendezvous", "Silhouette", "Serenade",
    "Carousel", "Kaleidoscope", "Masquerade", "Interlude", "Overture",
    "Champagne", "Prism", "Mirage", "Euphoria", "Devotion",
    "Tenderness", "Escapade", "Cabaret", "Encore", "Bijou",
]


# ============================================================================
# SYNTHWAVE ALBUM POOLS
# ============================================================================

# Tech compound (25%)
SW_TECH_PREFIXES = [
    "Chrome", "Neon", "Laser", "Cyber", "Turbo", "Hyper", "Ultra",
    "Dark", "Steel", "Iron", "Pulse", "Grid", "Data", "Volt",
]
SW_TECH_SUFFIXES = [
    "drive", "core", "wave", "grid", "flux", "pulse", "forge",
    "gate", "zone", "force", "storm", "blade", "lock", "sync",
]

# Driving / Road (20%)
SW_DRIVING_ADJ = [
    "Midnight", "Neon", "Chrome", "Night", "Sunset", "Pacific",
    "Coastal", "Redline", "Turbo", "Overdrive", "Full Throttle",
]
SW_DRIVING_NOUNS = [
    "Highway", "Boulevard", "Sessions", "Tapes", "Drive", "Cruise",
    "Run", "Chase", "Pursuit", "Express", "Roadside", "Circuit",
]

# Retro / VHS (15%)
SW_RETRO_ADJ = [
    "Analog", "Digital", "Magnetic", "Electric", "Neon", "Laser",
    "Holographic", "Fluorescent", "Synthetic", "Chrome", "VHS",
]
SW_RETRO_NOUNS = [
    "Archives", "Volumes", "Tapes", "Recordings", "Sessions",
    "Transmissions", "Broadcasts", "Signals", "Frequencies", "Reels",
]

# Sci-fi (15%)
SW_SCIFI_ADJ = [
    "Quantum", "Neural", "Stellar", "Cosmic", "Galactic", "Orbital",
    "Cyber", "Hyper", "Proto", "Neo", "Retro", "Meta",
]
SW_SCIFI_NOUNS = [
    "Protocol", "Array", "Matrix", "Vector", "Cascade", "Nexus",
    "Codex", "Archive", "Index", "Sequence", "Algorithm", "Paradox",
]

# Dark / Night (15%)
SW_DARK_ADJ = [
    "Blood Moon", "Shadow", "Midnight", "Dark", "Black", "Iron",
    "Cold", "Dead", "Silent", "Phantom", "Void", "Abyssal",
]
SW_DARK_NOUNS = [
    "Sessions", "Archives", "Chronicles", "Rites", "Protocols",
    "Transmissions", "Dossier", "Files", "Records", "Anthology",
]

# City / Location (10%)
SW_CITIES = [
    "Miami", "Tokyo", "L.A.", "Berlin", "Detroit", "Chicago",
    "Las Vegas", "New York", "Hong Kong", "Malibu", "Singapore",
]
SW_CITY_SUFFIXES = [
    "Vice Tapes", "After Dark", "Nights", "Sessions", "Connection",
    "Broadcast", "Transmission", "Archives", "Files", "Dossier",
]

# Retro years for synthwave albums
SW_YEARS = ["1984", "1985", "1986", "1987", "1988", "198X", "2049", "2077"]


# ============================================================================
# GENERATORS
# ============================================================================

@dataclass
class CitypopAlbumGenerator:
    seed: Optional[int] = None
    rng: random.Random = field(default_factory=random.Random, init=False)

    def __post_init__(self):
        self.rng = random.Random(self.seed) if self.seed is not None else random.Random()

    def _pick(self, lst): return self.rng.choice(lst)

    def gen_season(self):
        return f"{self._pick(CP_SEASON_ADJ)} {self._pick(CP_SEASON_NOUNS)}"

    def gen_location(self):
        return f"{self._pick(CP_LOCATIONS)} {self._pick(CP_LOCATION_NOUNS)}"

    def gen_romantic(self):
        return f"{self._pick(CP_ROMANTIC_ADJ)} {self._pick(CP_ROMANTIC_NOUNS)}"

    def gen_material(self):
        return f"{self._pick(CP_MATERIAL_ADJ)} {self._pick(CP_MATERIAL_NOUNS)}"

    def gen_japanese(self):
        roll = self.rng.random()
        if roll < 0.50:
            return f"{self._pick(CP_JP_WORDS)} no {self._pick(CP_JP_EN_NOUNS)}"
        else:
            return f"{self._pick(CP_JP_WORDS)} no {self._pick(CP_JP_WORDS)}"

    def gen_single(self):
        return self._pick(CP_SINGLE_WORDS)

    def generate(self, count=1):
        STYLES = [("season", 0.25), ("location", 0.20), ("romantic", 0.20),
                  ("material", 0.10), ("japanese", 0.15), ("single", 0.10)]
        names, weights = zip(*STYLES)
        results = []
        for _ in range(count):
            s = self.rng.choices(names, weights=weights, k=1)[0]
            raw = getattr(self, f"gen_{s}")()
            results.append({"name": raw.title() if self.rng.random() < 0.85 else raw, "style": s})
        return results


@dataclass
class SynthwaveAlbumGenerator:
    seed: Optional[int] = None
    rng: random.Random = field(default_factory=random.Random, init=False)

    def __post_init__(self):
        self.rng = random.Random(self.seed) if self.seed is not None else random.Random()

    def _pick(self, lst): return self.rng.choice(lst)

    def gen_tech(self):
        prefix = self._pick(SW_TECH_PREFIXES)
        suffix = self._pick(SW_TECH_SUFFIXES)
        return f"{prefix}{suffix}"

    def gen_driving(self):
        return f"{self._pick(SW_DRIVING_ADJ)} {self._pick(SW_DRIVING_NOUNS)}"

    def gen_retro(self):
        return f"{self._pick(SW_RETRO_ADJ)} {self._pick(SW_RETRO_NOUNS)}"

    def gen_scifi(self):
        return f"{self._pick(SW_SCIFI_ADJ)} {self._pick(SW_SCIFI_NOUNS)}"

    def gen_dark(self):
        return f"{self._pick(SW_DARK_ADJ)} {self._pick(SW_DARK_NOUNS)}"

    def gen_city(self):
        roll = self.rng.random()
        if roll < 0.60:
            return f"{self._pick(SW_CITIES)} {self._pick(SW_CITY_SUFFIXES)}"
        else:
            return f"{self._pick(SW_CITIES)} {self._pick(SW_YEARS)}"

    def generate(self, count=1):
        STYLES = [("tech", 0.25), ("driving", 0.20), ("retro", 0.15),
                  ("scifi", 0.15), ("dark", 0.15), ("city", 0.10)]
        names, weights = zip(*STYLES)
        results = []
        for _ in range(count):
            s = self.rng.choices(names, weights=weights, k=1)[0]
            raw = getattr(self, f"gen_{s}")()
            # Synthwave: 75% Title Case, 15% ALL CAPS, 10% as-is
            roll = self.rng.random()
            if roll < 0.75:
                name = raw.title()
            elif roll < 0.90:
                name = raw.upper()
            else:
                name = raw
            results.append({"name": name, "style": s})
        return results


# ============================================================================
# PUBLIC API
# ============================================================================

def generate_album_name(category: str, seed: Optional[int] = None) -> str:
    """Generate an album name appropriate for the given genre category.

    Args:
        category: One of "lofi", "citypop", "synthwave".
        seed: Optional RNG seed.

    Returns:
        A single album name string.
    """
    if category == "citypop":
        gen = CitypopAlbumGenerator(seed=seed)
        results = gen.generate(count=1)
        return results[0]["name"]

    if category == "synthwave":
        gen = SynthwaveAlbumGenerator(seed=seed)
        results = gen.generate(count=1)
        return results[0]["name"]

    # Lofi: delegate to the existing track name generator
    try:
        from src.generators.track_names import generate_track_names
        result = generate_track_names(count=1)
        if result:
            return result[0]["name"]
    except Exception:
        pass

    # Fallback
    prefixes = [
        "Late Night", "Early Morning", "Afternoon", "Midnight",
        "Sunday", "Golden", "Quiet", "Soft", "Warm", "Distant",
        "Fading", "Gentle", "Slow", "Last", "First",
    ]
    suffixes = [
        "Sessions", "Tapes", "Letters", "Memories", "Dreams",
        "Hours", "Moments", "Pages", "Sketches", "Waves",
        "Echoes", "Fragments", "Notes", "Drifts", "Horizons",
    ]
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"
