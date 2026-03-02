"""
Synthwave / Outrun Artist Name Generator
==========================================
Generates artist/producer names for the synthwave/outrun genre.

Style Distribution (~0% Japanese, ~5% French, ~95% English):
  1. Compound Power Word     (25%)  - "Lazerhawk", "Dynatron", "Waveshaper"
  2. Name + Year/Number      (15%)  - "Timecop1983", "FM-84", "Miami Nights 1984"
  3. "The ___" Format        (12%)  - "The Midnight", "The Outrunners"
  4. Human Name              (12%)  - "Robert Parker", "Mitch Murder"
  5. ALL CAPS Stylized       (10%)  - "PYLOT", "DEADLIFE", "MEGAFORCE"
  6. Single Dark/Tech Word   (10%)  - "Gunship", "Kalax", "Scandroid"
  7. French-Influenced        (5%)  - "Le Matos", "Carpenter Brut"
  8. Multi-Word Conceptual    (6%)  - "Electric Youth", "Dance With the Dead"
  9. Punctuated / Symbol      (5%)  - "Futurecop!", "Com Truise", "Betamaxx"

All names are appended with " (feat. mujin 無人)".
"""
import random
from dataclasses import dataclass, field
from typing import Optional

FEAT_SUFFIX = " (feat. mujin 無人)"

# ============================================================================
# WORD POOLS
# ============================================================================

# --- Compound power word building blocks ---
TECH_PREFIXES = [
    "laser", "mega", "dyna", "turbo", "hyper", "power", "star", "night",
    "dead", "cyber", "dark", "ultra", "neo", "proto", "synth", "retro",
    "chrome", "iron", "steel", "neon", "volt", "phase", "pulse", "wave",
    "grid", "data", "code", "byte", "pixel", "vector", "plasma", "ion",
    "solar", "lunar", "astro", "cosmo", "galact", "stellar", "quantum",
    "fury", "thunder", "storm", "blaze", "frost", "shadow", "phantom",
    "ghost", "skull", "blood", "war", "battle", "cross", "over", "auto",
]

POWER_SUFFIXES = [
    "hawk", "tron", "rider", "glove", "drive", "wave", "grid", "blade",
    "force", "cop", "shaper", "runner", "hunter", "killer", "master",
    "lord", "born", "fire", "storm", "strike", "bolt", "cade", "droid",
    "mech", "bot", "oid", "matic", "izer", "flux", "core", "pulse",
    "sync", "lock", "jack", "shift", "link", "bridge", "gate", "port",
    "smith", "craft", "forge", "works", "light", "glow", "beam", "ray",
]

COMPOUND_COMPAT = {
    "laser":    ["hawk", "grid", "blade", "wave", "force", "beam", "light", "strike", "bolt", "lock", "drive", "runner", "hunter", "rider", "master", "core", "pulse", "flux", "sync", "port", "gate", "forge", "storm", "fire", "glow"],
    "mega":     ["drive", "force", "tron", "wave", "storm", "bolt", "strike", "blast", "core", "flux", "pulse", "grid", "lock", "shift", "link", "gate", "port", "forge", "smith", "craft", "works", "light", "fire", "hunter", "runner"],
    "dyna":     ["tron", "mech", "force", "wave", "core", "pulse", "flux", "bolt", "strike", "blast", "drive", "shift", "link", "grid", "lock", "gate", "port", "forge", "smith", "craft", "light", "fire", "storm", "rider", "runner"],
    "turbo":    ["drive", "force", "rider", "racer", "hawk", "wolf", "blade", "strike", "bolt", "blast", "core", "flux", "pulse", "shift", "link", "grid", "lock", "gate", "charge", "boost", "fire", "storm", "killer", "hunter", "glove"],
    "hyper":    ["drive", "space", "sonic", "nova", "bolt", "charge", "link", "wave", "light", "blast", "force", "storm", "flux", "beam", "core", "grid", "loop", "zone", "lane", "port", "gate", "deck", "cell", "net", "active"],
    "power":    ["glove", "drive", "grid", "surge", "core", "force", "bolt", "strike", "blast", "wave", "pulse", "flux", "shift", "link", "lock", "gate", "forge", "smith", "craft", "works", "house", "play", "slide", "rider", "runner"],
    "star":     ["cadian", "light", "wave", "fire", "dust", "born", "gate", "forge", "rider", "runner", "hunter", "child", "lord", "fall", "ship", "fleet", "port", "field", "dome", "hawk", "blade", "strike", "bolt", "force", "storm"],
    "night":    ["rider", "runner", "hawk", "wolf", "stop", "drive", "call", "fall", "shift", "watch", "crawler", "stalker", "blade", "force", "fire", "storm", "shadow", "walker", "breaker", "master", "lord", "born", "hunter", "strike", "flight"],
    "dead":     ["life", "cruiser", "bolt", "lock", "eye", "zone", "drop", "light", "fall", "weight", "beat", "end", "run", "silence", "pool", "line", "ringer", "pan", "shot", "heat", "cold", "stop", "man", "horse", "bird"],
    "cyber":    ["punk", "wave", "grid", "space", "net", "core", "ware", "deck", "jack", "drive", "zone", "realm", "forge", "blade", "storm", "pulse", "flux", "link", "sync", "hack", "lock", "port", "ghost", "wolf", "hawk"],
    "dark":     ["wave", "synth", "star", "rider", "force", "lord", "blade", "fire", "storm", "heart", "angel", "matter", "side", "room", "ling", "ness", "en", "wing", "rain", "throne", "tooth", "moon", "web", "city", "age"],
    "ultra":    ["neon", "drive", "wave", "force", "sonic", "violet", "marine", "nova", "core", "flux", "pulse", "bolt", "strike", "blast", "light", "beam", "grid", "lock", "shift", "link", "gate", "port", "forge", "chrome", "hawk"],
    "neo":      ["wave", "chrome", "tokyo", "noir", "drive", "light", "grid", "core", "flux", "pulse", "storm", "blade", "forge", "gate", "port", "shift", "link", "lock", "sync", "rider", "runner", "hunter", "born", "dawn", "dusk"],
    "chrome":   ["hawk", "rider", "blade", "heart", "angel", "dream", "skull", "fist", "thunder", "lightning", "fire", "ice", "rain", "storm", "shadow", "ghost", "wolf", "fox", "cobra", "viper", "stallion", "mustang", "dawn", "dusk", "star"],
    "shadow":   ["runner", "walker", "hawk", "blade", "dancer", "hunter", "stalker", "fire", "storm", "rain", "heart", "soul", "lord", "king", "knight", "fist", "gate", "zone", "realm", "broker", "play", "land", "boxing", "cast", "smith"],
    "phantom":  ["rider", "drive", "blade", "force", "hawk", "wolf", "gate", "zone", "realm", "lord", "king", "knight", "hunter", "stalker", "fire", "storm", "rain", "light", "shadow", "heart", "soul", "eye", "fist", "strike", "bolt"],
    "wave":     ["shaper", "rider", "runner", "hawk", "blade", "form", "length", "crest", "break", "front", "pool", "guide", "maker", "smith", "craft", "forge", "works", "master", "lord", "born", "fire", "storm", "light", "flux", "pulse"],
    "synth":    ["wave", "rider", "runner", "hawk", "blade", "lord", "born", "fire", "storm", "light", "master", "forge", "craft", "smith", "works", "pulse", "flux", "core", "grid", "lock", "shift", "link", "gate", "port", "jack"],
    "pulse":    ["wave", "driver", "rider", "hawk", "blade", "fire", "storm", "light", "core", "grid", "lock", "shift", "link", "gate", "forge", "smith", "craft", "works", "master", "lord", "born", "force", "flux", "sync", "beam"],
    "frost":    ["byte", "wave", "blade", "fire", "hawk", "wolf", "bite", "burn", "lock", "gate", "core", "grid", "pulse", "flux", "shift", "link", "forge", "smith", "craft", "works", "light", "storm", "born", "rider", "runner"],
}

# --- Name + Year pools ---
YEAR_CONCEPTS = [
    "Timecop", "Nightwatch", "Stargazer", "Wavecatcher", "Neonlight",
    "Darksynth", "Retrograde", "Cyberdream", "Laserdisc", "Synthmaster",
    "Gridrunner", "Datastorm", "Pulsedriver", "Voltcharge", "Chromehawk",
    "Nightshift", "Deadlock", "Overload", "Mainframe", "Terminal",
    "Broadcast", "Frequency", "Spectrum", "Archive", "Protocol",
]

EIGHTIES_YEARS = list(range(1982, 1990))

CONCEPT_CITY = [
    "Miami", "Tokyo", "L.A.", "Berlin", "Detroit", "Chicago",
    "Dallas", "Houston", "Vegas", "Atlantic City", "Malibu",
]

# --- "The ___" pools ---
THE_NOUNS = [
    "Midnight", "Outrunners", "Encounter", "Reckoning", "Syndicate",
    "Collective", "Neon", "Machine", "Network", "Signal", "Broadcast",
    "Arcade", "Cassette", "VHS", "Frequency", "Voltage", "Algorithm",
    "Protocol", "Override", "Mainframe", "Terminal", "Gateway",
    "Nightwatch", "Vanguard", "Sentinels", "Phantoms", "Wolves",
]

THE_ADJ = [
    "Bad", "Lost", "Dark", "Neon", "Electric", "Toxic", "Digital",
    "Analog", "Magnetic", "Cosmic", "Stellar", "Nuclear", "Atomic",
    "Synthetic", "Holographic", "Chrome", "Iron", "Steel",
]

THE_TEMPLATES = [
    "The {TN}", "The {TA} {TN}", "The {TN}s",
]

# --- Human name pools (80s action hero energy) ---
HERO_FIRST = [
    "Robert", "Michael", "Trevor", "Mitch", "Kyle", "Derek", "Lance",
    "Brett", "Chad", "Brock", "Blade", "Max", "Rex", "Dirk", "Shane",
    "Logan", "Axel", "Jake", "Cole", "Vince", "Nash", "Colt", "Drake",
    "Zane", "Cliff", "Trent", "Blake", "Grant", "Kurt", "Rick",
    "Dana", "Morgan", "Jordan", "Casey", "Quinn", "Kelly", "Robin",
    "Alex", "Skylar", "Taylor", "Cameron", "Avery", "Parker", "Riley",
]

HERO_LAST = [
    "Parker", "Oakley", "Murder", "Something", "Phoenix", "Danger",
    "Steel", "Stone", "Storm", "Hawk", "Wolf", "Fox", "Cross",
    "Knight", "Savage", "Powers", "Justice", "Blaze", "Frost",
    "Thunder", "Lightning", "Vance", "Chase", "Hunter", "Archer",
    "Bishop", "Castle", "Cruz", "Steele", "Drake", "Kane",
    "Marshall", "Reeves", "Santiago", "West", "North", "Black",
    "Sinclair", "Chambers", "Preston", "Donovan", "Sullivan", "Blake",
]

HERO_MIDDLE = ["Jean", "Lee", "Ray", "James", "Marie", "Dean", "Scott"]

# --- ALL CAPS words ---
CAPS_COMPOUNDS = [
    "PYLOT", "DEADLIFE", "MEGAFORCE", "DEADSILENCE", "DROIDBISHOP",
    "WOLFCLUB", "STARCADIAN", "NIGHTSTOP", "DARKSYNTH", "NEONHAWK",
    "CHROMEVOID", "IRONGATE", "STEELWOLF", "VOLTCHARGE", "GRIDLOCK",
    "TURBOFORCE", "HYPERWAVE", "PULSECORE", "LASERBURN", "SYNTHKILL",
    "DEADBOLT", "BLOODMOON", "IRONFIST", "DARKWAVE", "NEONDREAM",
]

# --- Single dark/tech words ---
DARK_SINGLES = [
    "Gunship", "Kalax", "Fixions", "Scandroid", "Isidor", "Volkor",
    "Perturbator", "Dynatron", "Sellorekt", "Carpenter", "Lazerhawk",
    "Axiom", "Cipher", "Enigma", "Nexus", "Vertex", "Zenith",
    "Vortex", "Praxis", "Helix", "Onyx", "Phalanx", "Redux",
    "Apex", "Index", "Cortex", "Annex", "Reflex", "Complex",
    "Flux", "Lux", "Crux", "Nox", "Hex", "Plex",
    "Kodex", "Radix", "Matrix", "Phoenix", "Sphinx", "Lynx",
    "Krypton", "Argon", "Neon", "Xenon", "Radon", "Helion",
    "Oberon", "Triton", "Tethys", "Charon", "Phobos", "Deimos",
]

# --- French pools ---
FRENCH_ARTICLES = ["Le", "La", "Les"]
FRENCH_NOUNS = [
    "Matos", "Cassette", "Machine", "Néon", "Cristal", "Danse",
    "Nuit", "Mort", "Ombre", "Fantôme", "Mirage", "Ruine",
    "Monstre", "Chasseur", "Brut", "Rouge", "Noir", "Bleu",
    "Sang", "Fer", "Feu", "Froid", "Acier", "Chrome",
]

FRENCH_NAMES = [
    "Carpenter", "Laurent", "Pierre", "Jacques", "François", "Marcel",
    "André", "Henri", "Louis", "René", "Michel", "Claude",
]

FRENCH_DARK = [
    "Brut", "Noir", "Mort", "Sang", "Feu", "Fer", "Froid",
    "Acier", "Chrome", "Néon", "Cristal", "Ombre", "Fantôme",
]

# --- Multi-word conceptual ---
CONCEPT_ADJ = [
    "Electric", "Magic", "Lost", "Dark", "Neon", "Digital", "Analog",
    "Midnight", "Chrome", "Iron", "Steel", "Crystal", "Cosmic",
    "Nuclear", "Atomic", "Synthetic", "Holographic", "Virtual",
    "Phantom", "Shadow", "Ghost", "Silent", "Frozen", "Burning",
]

CONCEPT_NOUNS = [
    "Youth", "Sword", "Years", "Dreams", "Arcades", "Runners",
    "Riders", "Wolves", "Hawks", "Machines", "Signals", "Nights",
    "Glove", "Drive", "Zone", "Light", "Shadow", "Force",
    "Vision", "Horizon", "Frontier", "Empire", "Dynasty", "Legacy",
]

CONCEPT_TEMPLATES = [
    "{CAdj} {CN}", "Dance With the {CN}", "Night {CN}",
    "New {CN}", "Lost {CN}", "Last {CN}", "Dead {CN}",
    "{CN} of the Night", "Satellite {CN}",
]

# --- Punctuation pools ---
PUNCT_WORDS = [
    "Futurecop", "Nightforce", "Laserblast", "Turbocharge",
    "Megapower", "Hyperwave", "Pulsedriver", "Voltcharge",
    "Chromehawk", "Ironwolf", "Steelblade", "Darksynth",
    "Neonlight", "Cyberdream", "Retrograde", "Datastream",
]

MISSPELL_BASES = [
    "computer", "satellite", "synthesizer", "frequency", "terminal",
    "broadcast", "algorithm", "protocol", "hologram", "spectrum",
    "electric", "magnetic", "automatic", "cybernetic", "chromatic",
    "mechanic", "robotic", "galactic", "fantastic", "hypnotic",
]


# ============================================================================
# MISSPELLING ENGINE
# ============================================================================

def synthwave_misspell(word, rng):
    """Apply a synthwave-style misspelling to a word."""
    w = word.lower()
    transforms = ["double_consonant", "x_ending", "k_swap", "truncate_blend", "vowel_drop"]
    t = rng.choice(transforms)
    if t == "double_consonant":
        cons = [(i, c) for i, c in enumerate(w) if c.isalpha() and c not in "aeiou"]
        if cons:
            idx, c = rng.choice(cons)
            w = w[:idx] + c + w[idx:]
    elif t == "x_ending":
        w = w.rstrip("aeiouy") + "x"
    elif t == "k_swap":
        for old, new in [("c", "k"), ("s", "z"), ("ph", "f"), ("ck", "k")]:
            if old in w: w = w.replace(old, new, 1); break
    elif t == "truncate_blend":
        cut = rng.randint(max(3, len(w) // 2), max(5, len(w) - 2))
        w = w[:cut]
    elif t == "vowel_drop":
        vs = [(i, c) for i, c in enumerate(w) if c in "aeiou" and 0 < i < len(w) - 1]
        if vs:
            idx, _ = rng.choice(vs)
            w = w[:idx] + w[idx + 1:]
    if w == word.lower():
        w += rng.choice(["x", "xx", "k", "z"])
    return w.capitalize()


# ============================================================================
# GENERATOR
# ============================================================================

@dataclass
class SynthwaveArtistGenerator:
    seed: Optional[int] = None
    rng: random.Random = field(default_factory=random.Random, init=False)

    def __post_init__(self):
        self.rng = random.Random(self.seed) if self.seed is not None else random.Random()

    def _pick(self, lst): return self.rng.choice(lst)
    def _pick_compat(self, m):
        k = self._pick(list(m.keys())); return k, self._pick(m[k])

    def gen_compound(self):
        prefix, suffix = self._pick_compat(COMPOUND_COMPAT)
        name = prefix + suffix
        if self.rng.random() < 0.60:
            name = name.capitalize()
        return name, "compound"

    def gen_year(self):
        roll = self.rng.random()
        if roll < 0.45:
            concept = self._pick(YEAR_CONCEPTS)
            year = self._pick(EIGHTIES_YEARS)
            return f"{concept}{year}", "year/concept"
        elif roll < 0.70:
            abbrev = self._pick(["FM", "AM", "VHS", "VCR", "CRT", "RGB", "LCD", "LED", "DAT", "DX"])
            num = self.rng.choice([84, 85, 86, 87, 88, 89, 101, 200, 404, 808])
            sep = self.rng.choice(["-", " "])
            return f"{abbrev}{sep}{num}", "year/abbreviation"
        else:
            city = self._pick(CONCEPT_CITY)
            year = self._pick(EIGHTIES_YEARS)
            return f"{city} Nights {year}", "year/city"

    def gen_the(self):
        t = self._pick(THE_TEMPLATES); r = t
        if "{TN}" in r: r = r.replace("{TN}", self._pick(THE_NOUNS), 1)
        if "{TA}" in r: r = r.replace("{TA}", self._pick(THE_ADJ), 1)
        return r, "the"

    def gen_human(self):
        roll = self.rng.random()
        if roll < 0.55:
            return f"{self._pick(HERO_FIRST)} {self._pick(HERO_LAST)}", "human/two"
        elif roll < 0.80:
            return f"{self._pick(HERO_FIRST)} {self._pick(HERO_MIDDLE)} {self._pick(HERO_LAST)}", "human/three"
        else:
            first = self._pick(HERO_FIRST)
            last = self._pick(["Something", "Nobody", "Nowhere", "Nothing", "Everywhere", "Anyone", "Anything"])
            return f"{first} {last}", "human/unusual"

    def gen_caps(self):
        roll = self.rng.random()
        if roll < 0.50:
            return self._pick(CAPS_COMPOUNDS), "caps/preset"
        elif roll < 0.80:
            prefix, suffix = self._pick_compat(COMPOUND_COMPAT)
            name = (prefix + suffix).upper()
            return name, "caps/generated"
        else:
            prefix, suffix = self._pick_compat(COMPOUND_COMPAT)
            word = (prefix + suffix).upper()
            if len(word) <= 10:
                return " ".join(word), "caps/spaced"
            return word, "caps/generated"

    def gen_single(self):
        return self._pick(DARK_SINGLES), "single"

    def gen_french(self):
        roll = self.rng.random()
        if roll < 0.40:
            art = self._pick(FRENCH_ARTICLES)
            noun = self._pick(FRENCH_NOUNS)
            return f"{art} {noun}", "french/article"
        elif roll < 0.70:
            name = self._pick(FRENCH_NAMES)
            dark = self._pick(FRENCH_DARK)
            return f"{name} {dark}", "french/name"
        else:
            return self._pick(FRENCH_NOUNS), "french/single"

    def gen_concept(self):
        t = self._pick(CONCEPT_TEMPLATES); r = t
        if "{CAdj}" in r: r = r.replace("{CAdj}", self._pick(CONCEPT_ADJ), 1)
        if "{CN}" in r: r = r.replace("{CN}", self._pick(CONCEPT_NOUNS), 1)
        return r, "concept"

    def gen_punctuated(self):
        roll = self.rng.random()
        if roll < 0.35:
            word = self._pick(PUNCT_WORDS)
            return f"{word}!", "punct/exclaim"
        elif roll < 0.65:
            base = self._pick(MISSPELL_BASES)
            return synthwave_misspell(base, self.rng), "punct/misspell"
        else:
            prefix, suffix = self._pick_compat(COMPOUND_COMPAT)
            word = prefix + suffix
            word = word.capitalize() + self.rng.choice(["xx", "x", "z", "k"])
            return word, "punct/modified"

    def generate(self, count=1):
        STYLES = [("compound", 0.25), ("year", 0.15), ("the", 0.12),
                  ("human", 0.12), ("caps", 0.10), ("single", 0.10),
                  ("french", 0.05), ("concept", 0.06), ("punctuated", 0.05)]
        names, weights = zip(*STYLES)
        results = []
        for _ in range(count):
            s = self.rng.choices(names, weights=weights, k=1)[0]
            name, sub = getattr(self, f"gen_{s}")()
            results.append({"name": name + FEAT_SUFFIX, "style": sub})
        return results


# ============================================================================
# PUBLIC API
# ============================================================================

def generate_artist_names(
    count: int = 1,
    seed: Optional[int] = None,
) -> list[dict[str, str]]:
    """Generate synthwave artist names.

    Returns:
        List of dicts, each with 'name' and 'style' keys.
        Every name is appended with " (feat. mujin 無人)".
    """
    gen = SynthwaveArtistGenerator(seed=seed)
    return gen.generate(count=count)
