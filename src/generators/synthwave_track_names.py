"""
Synthwave / Outrun Track Name Generator
=========================================
Generates track names in the style of Kavinsky, Perturbator, Carpenter Brut,
The Midnight, FM-84, Gunship, Lazerhawk, Timecop1983, Mitch Murder, Com Truise.

Style Distribution:
  1. Single Tech/Power Word  (22%)  - "Overdrive", "Interceptor", "Sentient"
  2. Driving / Highway       (18%)  - "Turbo Killer", "Night Drive", "Redline"
  3. 80s Nostalgia / VHS     (13%)  - "VHS Dream", "Laser Grid", "Tracking Error"
  4. City / Location         (10%)  - "Miami Disco", "Ocean Drive", "Neon City"
  5. Night / Dark            (10%)  - "Nightcall", "Shadowrunner", "Blood Moon"
  6. Action Phrase            (8%)  - "Burn the Night", "Running in the Night"
  7. Female Name              (5%)  - "Gloria", "Selene", "Roxanne"
  8. Cosmic / Sci-Fi          (5%)  - "Andromeda", "Event Horizon", "Warp Drive"
  9. Year / Number            (2%)  - "198XAD", "Streets of 2043"
 10. Three-Word Combo         (7%)  - cubic volume path

Conventions: Title Case (~80%), ALL CAPS (~10%), compounds common,
sharp consonants (k,x,z,t), neon/chrome/speed vocabulary, French occasionally.
"""
import random
from dataclasses import dataclass, field
from typing import Optional

# ============================================================================
# WORD POOLS
# ============================================================================

# --- Single power words (aggressive, tech, kinetic) ---
POWER_WORDS = [
    "Overdrive", "Interceptor", "Turbo", "Afterburner", "Redline", "Burnout",
    "Nitro", "Throttle", "Piston", "Chassis", "Dragster", "Roadster",
    "Stallion", "Mustang", "Corvette", "Testarossa", "Countach",
    "Mainframe", "Protocol", "Override", "Interface", "Terminal", "Circuit",
    "Matrix", "Vector", "Codec", "Binary", "Sequence", "Algorithm",
    "Firmware", "Kernel", "Proxy", "Relay", "Node", "Sector", "Bitmap",
    "Datalink", "Hardwired", "Encrypted", "Firewall", "Gateway",
    "Interceptor", "Sentinel", "Decoy", "Fugitive", "Outlaw", "Operative",
    "Banshee", "Riot", "Arsenal", "Caliber", "Barrage", "Salvo",
    "Tracer", "Recon", "Vanguard", "Fortress", "Bastion", "Citadel",
    "Andromeda", "Nebula", "Singularity", "Parallax", "Zenith", "Photon",
    "Ion", "Plasma", "Neutron", "Quasar", "Pulsar", "Retrograde",
    "Eclipse", "Supernova", "Stardust", "Void", "Abyss", "Horizon",
    "Accelerated", "Sentient", "Overload", "Protovision", "Hyperdrive",
    "Ultraviolet", "Inferno", "Vendetta", "Nemesis", "Phantom",
    "Wraith", "Specter", "Predator", "Juggernaut", "Colossus",
    "Neon", "Chrome", "Laser", "Hologram", "Prism", "Fluorescent",
    "Phosphor", "Mercury", "Argon", "Xenon", "Halogen", "Tungsten",
]

# --- Driving / Highway ---
VEHICLE_NOUNS = [
    "testarossa", "stallion", "interceptor", "cruiser", "mustang", "corvette",
    "turbo", "nitro", "piston", "throttle", "engine", "chassis", "coupe",
    "roadster", "dragster", "charger", "firebird", "camaro", "bronco",
    "stingray", "barracuda", "viper", "cobra", "pantera", "diablo",
]

SPEED_ADJ = [
    "overdrive", "redline", "burnout", "turbo", "nitro", "hyper",
    "supersonic", "hypersonic", "max", "ultra", "warp", "boost",
    "full-throttle", "high-speed", "breakneck", "blazing", "screaming",
]

ROAD_NOUNS = [
    "highway", "boulevard", "avenue", "freeway", "interstate", "turnpike",
    "overpass", "strip", "lane", "route", "drive", "coast", "bridge",
    "tunnel", "ramp", "crossing", "junction", "detour", "bypass",
]

DRIVING_TEMPLATES = [
    "Night{Vsuf}", "Dead{Vsuf}", "Auto{Vsuf}", "Hyper{Vsuf}",
    "Turbo{Vsuf}", "Road{Vsuf}", "Speed{Vsuf}", "Steel{Vsuf}",
    "Chrome{Vsuf}", "Iron{Vsuf}", "Neon{Vsuf}", "Black{Vsuf}",
    "{SpAdj} {Vsuf}", "Night {Vsuf}", "Midnight {Vsuf}",
    "Street {Vsuf}", "{Vsuf} {Road}", "Pacific Coast {Road}",
    "Ocean {Road}", "Sunset {Road}", "Coastal {Road}",
    "Chrome {Vehicle}", "Steel {Vehicle}", "Neon {Vehicle}",
    "Pedal to the Metal", "Full Throttle", "Flat Out",
    "Point of No Return",
]

VEHICLE_SUFFIXES = [
    "rider", "driver", "cruiser", "racer", "runner", "chaser",
    "hunter", "killer", "blaster", "hawk", "wolf", "glider",
    "drifter", "stalker", "striker", "seeker", "breaker",
]

# --- 80s Nostalgia / VHS ---
VHS_NOUNS = [
    "tracking", "static", "rewind", "pause", "playback", "eject",
    "record", "fast-forward", "scan", "channel", "signal", "broadcast",
    "frequency", "antenna", "interference", "distortion", "feedback",
    "snow", "grain", "flicker", "dropout", "glitch", "artifact",
]

RETRO_NOUNS = [
    "arcade", "console", "cartridge", "joystick", "pixel", "sprite",
    "bitmap", "cassette", "tape", "deck", "reel", "dial", "knob",
    "synth", "drum machine", "sampler", "sequencer", "vocoder",
    "modem", "floppy", "diskette", "cathode", "tube", "monitor",
]

RETRO_ADJ = [
    "neon", "electric", "laser", "digital", "analog", "magnetic",
    "chrome", "holographic", "fluorescent", "phosphor", "infrared",
    "ultraviolet", "synthetic", "automated", "programmed", "encoded",
]

FILM_NOUNS = [
    "noir", "thriller", "scene", "credits", "sequel", "premiere",
    "montage", "climax", "finale", "score", "cut", "take",
    "trailer", "poster", "reel", "frame", "shot", "angle",
]

VHS_TEMPLATES = [
    "{RetroAdj} {RetroN}", "VHS {Noun}", "{RetroN} {FilmN}",
    "Tracking {Noun}", "Static {Noun}", "{RetroAdj} {FilmN}",
    "{VhsN} Error", "{VhsN} Signal", "Channel {Num}",
    "{RetroAdj} Palace", "{RetroAdj} Grid", "Danger {FilmN}",
    "Dangerous {Noun}", "Tech {FilmN}", "Video {Noun}",
]

# --- City / Location ---
EIGHTIES_CITIES = [
    "Miami", "Los Angeles", "Tokyo", "Las Vegas", "New York", "Chicago",
    "Detroit", "San Francisco", "Hong Kong", "Berlin", "Paris",
    "Rio", "Bangkok", "Singapore", "Sydney", "Dallas", "Houston",
    "Phoenix", "Atlantic City", "Osaka", "Honolulu", "Seoul",
    "Malibu", "Santa Monica", "Venice Beach", "Palm Springs",
]

CITY_NOUNS = [
    "city", "downtown", "district", "precinct", "sector", "zone",
    "strip", "boulevard", "skyline", "harbor", "waterfront", "plaza",
    "arcade", "mall", "motel", "diner", "garage", "penthouse",
]

CITY_ADJ = [
    "neon", "electric", "chrome", "midnight", "sunset", "vice",
    "neon-lit", "rain-soaked", "fog-covered", "steam-filled",
]

CITY_TEMPLATES = [
    "{ECity}", "{ECity} Nights", "{ECity} {CityN}",
    "{CAdj} {CityN}", "Streets of {Year}", "{CAdj} Downtown",
    "Welcome to {ECity}", "{ECity} After Dark", "{ECity} Vice",
    "{ECity} Sunset", "Sunset {CityN}", "Ocean Drive",
]

# --- Night / Dark ---
DARK_NOUNS = [
    "shadow", "void", "abyss", "phantom", "specter", "wraith",
    "reaper", "hunter", "stalker", "predator", "vampire", "demon",
    "ghoul", "wolf", "serpent", "raven", "crow", "bat",
    "eclipse", "blood moon", "dark matter", "black hole",
]

DARK_ADJ = [
    "dark", "black", "midnight", "shadow", "night", "dead",
    "blood", "iron", "steel", "cold", "deep", "silent",
    "hollow", "grim", "bleak", "savage", "feral", "sinister",
]

DARK_TEMPLATES = [
    "Night{DkSuf}", "Dark {Noun}", "Midnight {Noun}",
    "{DkAdj} {DkN}", "{DkAdj} Ice", "Deep Cover",
    "Dead of Night", "After Dark", "Pitch {DkAdj}",
    "{DkN}runner", "{DkN}stalker", "{DkN}hunter",
    "Blood {Noun}", "Black {Noun}",
]

DARK_SUFFIXES = [
    "call", "fall", "run", "ride", "watch", "shift", "walk",
    "crawl", "flight", "strike", "blade", "force",
]

DARK_GENERIC_NOUNS = [
    "ice", "steel", "iron", "chrome", "glass", "rain", "frost",
    "fire", "flame", "smoke", "ash", "dust", "stone", "bone",
    "moon", "sun", "sky", "storm", "thunder", "lightning",
]

# --- Action Phrases ---
ACTION_VERBS = [
    "Run", "Chase", "Fight", "Burn", "Escape", "Break", "Crash",
    "Strike", "Blast", "Hunt", "Race", "Surge", "Charge", "Slam",
    "Smash", "Tear", "Rip", "Shatter", "Crush", "Destroy",
    "Fly", "Drive", "Ride", "Shoot", "Kill",
]

ACTION_NOUNS = [
    "Night", "Silence", "Machine", "System", "Grid", "City",
    "Law", "Rules", "Chains", "Walls", "Limit", "Barrier",
    "Sound", "Record", "Code", "Time", "Light", "Dark",
    "Dawn", "Dusk", "Horizon", "Void", "Speed", "Line",
]

ACTION_TEMPLATES = [
    "{AV} the {AN}", "{AV} for Your Life",
    "On the {AV2}", "{Ger} in the {AN}",
    "{AV} Against {AN}", "{AV} Another Day",
    "Never Stop {Ger}", "Keep {Ger}",
    "{AV} or Die", "No {AN}", "Beyond the {AN}",
]

ACTION_GERUNDS = [
    "Running", "Driving", "Racing", "Fighting", "Burning",
    "Chasing", "Hunting", "Flying", "Riding", "Shooting",
    "Crashing", "Breaking", "Blasting", "Surging", "Charging",
]

# --- Female Names (80s noir character energy) ---
FEMALE_NAMES = [
    "Gloria", "Jessica", "Selene", "Diana", "Roxanne", "Nikita",
    "Elektra", "Natasha", "Crystal", "Vanessa", "Veronica", "Monique",
    "Dominique", "Sabrina", "Tiffany", "Heather", "Brooke", "Destiny",
    "Raven", "Jade", "Amber", "Carmen", "Valentina", "Bianca",
    "Cassandra", "Anastasia", "Katarina", "Scarlett", "Victoria",
    "Isabella", "Gabriella", "Adriana", "Tatiana", "Angelica",
    "Francesca", "Alessandra", "Vivienne", "Genevieve", "Delilah",
    "Seraphina", "Josephine", "Evangeline", "Cleopatra", "Pandora",
    "Athena", "Artemis", "Persephone", "Aphrodite", "Calypso",
    "Siren", "Valkyrie", "Phoenix", "Nova", "Luna",
]

# --- Cosmic / Sci-Fi ---
SCIFI_NOUNS = [
    "nebula", "quasar", "pulsar", "singularity", "hyperspace", "wormhole",
    "android", "cyborg", "hologram", "photon", "ion", "plasma",
    "neural", "quantum", "parallax", "zenith", "orbit", "galaxy",
    "void", "horizon", "matrix", "vector", "protocol", "algorithm",
    "dimension", "paradox", "anomaly", "rift", "portal", "gateway",
]

SCIFI_ADJ = [
    "quantum", "neural", "stellar", "cosmic", "galactic", "orbital",
    "hyper", "ultra", "mega", "nano", "bio", "cyber", "techno",
    "proto", "neo", "retro", "meta", "para", "sub", "super",
]

SCIFI_TEMPLATES = [
    "{SFN}", "{SFAdj} {SFN}", "{SFN} {SFN2}",
    "Event {SFN}", "{SFAdj} Net", "{SFAdj} Drive",
    "{SFAdj} Storm", "{SFN} Protocol", "Deep {SFN}",
    "Warp {SFN}", "{SFN} Array", "{SFN} Cascade",
]

# --- Year / Number ---
RETRO_YEARS = ["198X", "1984", "1985", "1986", "1987", "1988", "1989",
               "2019", "2049", "2077", "2084", "2099"]
FUTURE_YEARS = list(range(2030, 2100, 7))

# --- French flavor (Carpenter Brut lineage) ---
FRENCH_ARTICLES = ["Le", "La", "Les"]
FRENCH_NOUNS = [
    "Perv", "Nuit", "Mort", "Sang", "Fer", "Feu", "Ombre",
    "Noir", "Rouge", "Bleu", "Chasseur", "Fantôme", "Danse",
    "Machine", "Monstre", "Mirage", "Ruine", "Néon", "Cristal",
]

# --- Compatibility matrices ---
DRIVING_COMPAT = {
    "night":     ["rider", "driver", "cruiser", "racer", "runner", "hawk", "wolf", "stalker", "drifter", "chaser", "call", "run", "drive", "shift", "watch", "fall", "flight", "blade", "force", "strike", "walk", "crawl", "glider", "seeker", "breaker"],
    "dead":      ["cruiser", "runner", "driver", "racer", "zone", "drop", "lock", "end", "bolt", "weight", "line", "light", "heat", "cold", "eye", "shot", "fall", "stop", "pan", "beat", "ringer", "breaker", "hunter", "stalker", "striker"],
    "turbo":     ["killer", "racer", "rider", "driver", "boost", "charge", "blast", "force", "shot", "strike", "fire", "hawk", "wolf", "glider", "seeker", "breaker", "drifter", "chaser", "runner", "cruiser", "hunter", "stalker", "blaster", "flight", "surge"],
    "chrome":    ["stallion", "rider", "cruiser", "hawk", "wolf", "blade", "heart", "angel", "dream", "ghost", "skull", "fist", "thunder", "lightning", "fire", "ice", "rain", "storm", "shadow", "light", "star", "moon", "sun", "dawn", "dusk"],
    "steel":     ["rider", "runner", "hawk", "wolf", "blade", "heart", "nerve", "fist", "thunder", "lightning", "rain", "storm", "shadow", "curtain", "trap", "cage", "chain", "wire", "mill", "works", "horse", "dragon", "serpent", "viper", "cobra"],
    "neon":      ["rider", "cruiser", "drifter", "racer", "dream", "ghost", "angel", "devil", "city", "night", "rain", "glow", "blade", "light", "fire", "heart", "soul", "blood", "tears", "eyes", "sky", "moon", "sun", "star", "dawn"],
    "black":     ["rider", "hawk", "wolf", "ice", "rain", "heart", "out", "bird", "mail", "list", "dog", "cat", "jack", "flag", "hole", "box", "sheep", "smith", "top", "belt", "market", "board", "pearl", "diamond", "mirror"],
    "hyper":     ["drive", "space", "sonic", "active", "bolt", "charge", "link", "wave", "light", "nova", "blast", "force", "storm", "flux", "beam", "core", "grid", "loop", "zone", "lane", "port", "gate", "deck", "cell", "net"],
    "auto":      ["drive", "pilot", "cruise", "maton", "matic", "graph", "crat", "scape", "route", "run", "track", "path", "way", "lane", "glide", "surf", "scan", "pilot", "nav", "sync", "tune", "play", "start", "stop", "lock"],
    "road":      ["blaster", "runner", "warrior", "racer", "hawk", "wolf", "kill", "rage", "burn", "trip", "house", "side", "block", "work", "map", "sign", "test", "way", "master", "king", "star", "show", "crew", "gang", "dog"],
}

NIGHT_DARK_COMPAT = {
    "dark":      ["rider", "wave", "heart", "angel", "star", "matter", "side", "room", "web", "city", "all day", "water", "horse", "age", "ling", "ness", "en", "force", "lord", "wing", "blade", "fire", "storm", "rain", "throne"],
    "blood":     ["moon", "line", "bath", "hound", "sport", "lust", "stone", "born", "red", "shot", "stain", "diamond", "orange", "rain", "rush", "thirst", "curse", "oath", "pact", "rite", "trail", "hunt", "bank", "count", "debt"],
    "shadow":    ["dancer", "walker", "runner", "play", "land", "boxing", "cast", "realm", "zone", "broker", "hawk", "blade", "fire", "storm", "rain", "heart", "soul", "lord", "king", "knight", "hunter", "stalker", "strike", "fist", "gate"],
    "midnight":  ["run", "rider", "chase", "express", "mass", "oil", "sun", "shift", "hour", "caller", "cruiser", "angel", "wolf", "hawk", "blade", "fire", "storm", "rain", "heart", "soul", "special", "blue", "train", "cowboy", "confession"],
    "iron":      ["heart", "fist", "curtain", "horse", "maiden", "wolf", "blade", "throne", "gate", "fortress", "grip", "will", "side", "clad", "work", "monger", "smith", "born", "core", "lung", "jaw", "hide", "bound", "wrought", "cast"],
    "cold":      ["blood", "heart", "steel", "front", "wave", "snap", "shoulder", "storage", "case", "war", "comfort", "fusion", "fire", "rain", "night", "dawn", "light", "dark", "iron", "chrome", "blade", "silence", "shadow", "breath", "sweat"],
}

SCIFI_COMPAT = {
    "quantum":   ["leap", "field", "flux", "storm", "break", "lock", "drive", "gate", "bridge", "core", "pulse", "wave", "shift", "link", "mesh", "thread", "weave", "realm", "void", "rift", "cascade", "surge", "bloom", "echo", "phantom"],
    "neural":    ["net", "link", "path", "web", "storm", "pulse", "wave", "drive", "core", "grid", "map", "scan", "probe", "spike", "burst", "bloom", "cascade", "sync", "flux", "field", "zone", "realm", "space", "gate", "bridge"],
    "stellar":   ["drift", "wind", "core", "gate", "fire", "storm", "blade", "dawn", "dusk", "pulse", "wave", "flux", "field", "zone", "realm", "bridge", "path", "drive", "forge", "lance", "shield", "crown", "throne", "dust", "rain"],
    "cosmic":    ["ray", "dust", "storm", "gate", "wave", "pulse", "drift", "dawn", "dusk", "fire", "wind", "rain", "snow", "ice", "blade", "forge", "crown", "throne", "eye", "heart", "soul", "mind", "dream", "voyage", "explorer"],
    "cyber":     ["punk", "space", "net", "grid", "core", "ware", "deck", "jack", "drive", "zone", "realm", "forge", "blade", "storm", "pulse", "wave", "flux", "link", "sync", "hack", "lock", "port", "ghost", "wolf", "hawk"],
    "hyper":     ["drive", "space", "sonic", "nova", "bolt", "charge", "link", "wave", "light", "blast", "force", "storm", "flux", "beam", "core", "grid", "loop", "zone", "lane", "port", "gate", "deck", "cell", "net", "active"],
}


# ============================================================================
# GENERATOR
# ============================================================================

@dataclass
class SynthwaveTrackGenerator:
    seed: Optional[int] = None
    rng: random.Random = field(default_factory=random.Random, init=False)

    def __post_init__(self):
        self.rng = random.Random(self.seed) if self.seed is not None else random.Random()

    def _pick(self, lst): return self.rng.choice(lst)
    def _pick_compat(self, m):
        k = self._pick(list(m.keys())); return k, self._pick(m[k])

    def gen_power(self):
        return self._pick(POWER_WORDS)

    def gen_driving(self):
        t = self._pick(DRIVING_TEMPLATES); r = t
        if "{Vsuf}" in r:
            prefix_part = r.split("{Vsuf}")[0]
            key = prefix_part.lower().strip()
            if key in DRIVING_COMPAT:
                suf = self._pick(DRIVING_COMPAT[key])
            else:
                suf = self._pick(VEHICLE_SUFFIXES)
            r = r.replace("{Vsuf}", suf.capitalize(), 1)
        for tag, pool in [("{SpAdj}", SPEED_ADJ), ("{Road}", ROAD_NOUNS),
                          ("{Vehicle}", VEHICLE_NOUNS)]:
            if tag in r: r = r.replace(tag, self._pick(pool).capitalize(), 1)
        return r

    def gen_vhs(self):
        t = self._pick(VHS_TEMPLATES); r = t
        for tag, pool in [("{RetroAdj}", RETRO_ADJ), ("{RetroN}", RETRO_NOUNS),
                          ("{Noun}", VHS_NOUNS + RETRO_NOUNS), ("{FilmN}", FILM_NOUNS),
                          ("{VhsN}", VHS_NOUNS)]:
            if tag in r: r = r.replace(tag, self._pick(pool).capitalize(), 1)
        if "{Num}" in r: r = r.replace("{Num}", str(self.rng.randint(1, 99)), 1)
        return r

    def gen_city(self):
        t = self._pick(CITY_TEMPLATES); r = t
        if "{ECity}" in r: r = r.replace("{ECity}", self._pick(EIGHTIES_CITIES), 1)
        if "{CityN}" in r: r = r.replace("{CityN}", self._pick(CITY_NOUNS).capitalize(), 1)
        if "{CAdj}" in r: r = r.replace("{CAdj}", self._pick(CITY_ADJ).capitalize(), 1)
        if "{Year}" in r: r = r.replace("{Year}", str(self._pick(FUTURE_YEARS)), 1)
        return r

    def gen_dark(self):
        t = self._pick(DARK_TEMPLATES); r = t
        if "{DkSuf}" in r:
            r = r.replace("{DkSuf}", self._pick(DARK_SUFFIXES), 1)
        if "{DkAdj}" in r and "{DkN}" in r:
            a, n = self._pick_compat(NIGHT_DARK_COMPAT)
            r = r.replace("{DkAdj}", a.capitalize(), 1).replace("{DkN}", n.capitalize(), 1)
        if "{DkAdj}" in r: r = r.replace("{DkAdj}", self._pick(DARK_ADJ).capitalize(), 1)
        if "{DkN}" in r: r = r.replace("{DkN}", self._pick(DARK_NOUNS).capitalize(), 1)
        if "{Noun}" in r: r = r.replace("{Noun}", self._pick(DARK_GENERIC_NOUNS).capitalize(), 1)
        return r

    def gen_action(self):
        t = self._pick(ACTION_TEMPLATES); r = t
        if "{AV}" in r: r = r.replace("{AV}", self._pick(ACTION_VERBS), 1)
        if "{AV2}" in r: r = r.replace("{AV2}", self._pick(ACTION_VERBS), 1)
        if "{AN}" in r: r = r.replace("{AN}", self._pick(ACTION_NOUNS), 1)
        if "{Ger}" in r: r = r.replace("{Ger}", self._pick(ACTION_GERUNDS), 1)
        return r

    def gen_female(self): return self._pick(FEMALE_NAMES)

    def gen_scifi(self):
        t = self._pick(SCIFI_TEMPLATES); r = t
        if "{SFAdj}" in r and "{SFN}" in r:
            a, n = self._pick_compat(SCIFI_COMPAT)
            r = r.replace("{SFAdj}", a.capitalize(), 1).replace("{SFN}", n.capitalize(), 1)
        if "{SFAdj}" in r: r = r.replace("{SFAdj}", self._pick(SCIFI_ADJ).capitalize(), 1)
        if "{SFN}" in r: r = r.replace("{SFN}", self._pick(SCIFI_NOUNS).capitalize(), 1)
        if "{SFN2}" in r: r = r.replace("{SFN2}", self._pick(SCIFI_NOUNS).capitalize(), 1)
        return r

    def gen_year(self):
        roll = self.rng.random()
        if roll < 0.40:
            return self._pick(RETRO_YEARS)
        elif roll < 0.70:
            return f"Streets of {self._pick(FUTURE_YEARS)}"
        elif roll < 0.85:
            return f"Level {self.rng.randint(1, 9)}"
        else:
            return f"Stage {self.rng.randint(1, 5)}"

    def gen_three_word(self):
        roll = self.rng.random()
        if roll < 0.30:
            a, n1 = self._pick_compat(DRIVING_COMPAT)
            n2 = self._pick(DARK_GENERIC_NOUNS)
            return f"{a.capitalize()} {n1.capitalize()} {n2.capitalize()}"
        elif roll < 0.55:
            a, n1 = self._pick_compat(NIGHT_DARK_COMPAT)
            n2 = self._pick(DARK_GENERIC_NOUNS)
            return f"{a.capitalize()} {n1.capitalize()} {n2.capitalize()}"
        elif roll < 0.75:
            a, n1 = self._pick_compat(SCIFI_COMPAT)
            n2 = self._pick(SCIFI_NOUNS)
            return f"{a.capitalize()} {n1.capitalize()} {n2.capitalize()}"
        else:
            art = self._pick(FRENCH_ARTICLES)
            n = self._pick(FRENCH_NOUNS)
            n2 = self._pick(DARK_GENERIC_NOUNS)
            return f"{art} {n} {n2.capitalize()}"

    def apply_modifiers(self, name):
        roll = self.rng.random()
        if roll < 0.80:
            name = name.title()
        elif roll < 0.90:
            name = name.upper()
        if " " in name and name.count(" ") == 1 and self.rng.random() < 0.15:
            parts = name.split()
            if len(parts[0]) + len(parts[1]) <= 14:
                name = parts[0] + parts[1].lower()
        if self.rng.random() < 0.03:
            name += " " + self._pick(["II", "III", "IV"])
        return name

    def generate(self, count=1):
        STYLES = [("power", 0.22), ("driving", 0.18), ("vhs", 0.13),
                  ("city", 0.10), ("dark", 0.10), ("action", 0.08),
                  ("female", 0.05), ("scifi", 0.05), ("year", 0.02),
                  ("three_word", 0.07)]
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
    """Generate synthwave track names.

    Returns:
        A list of dicts, each with "name" and "style" keys.
    """
    generator = SynthwaveTrackGenerator(seed=seed)
    return generator.generate(count=count)
