"""
City Pop Artist Name Generator
===============================
Generates artist/band names in the style of 1980s Japanese city pop.

Style Distribution (~70% Japanese identity, ~30% English-format):
  1. Full Japanese Name      (40%)  - "Mariya Takeuchi", "Tatsuro Yamashita"
  2. Single JP Stage Name    (15%)  - "Anri", "Yukika", "Miki"
  3. Japanese Band Name      (15%)  - "Omega Tribe", "Sugar Babe", "Casiopea"
  4. Modern Revival Producer (15%)  - "Night Tempo", "Future Girlfriend"
  5. Western Stage Name      (10%)  - "Cindy", "Tommy", "Sally"
  6. Hybrid / Stylized        (5%)  - "1986 Omega Tribe", "AB's"

All names are appended with " (feat. mujin 無人)".
"""
import random
from dataclasses import dataclass, field
from typing import Optional

FEAT_SUFFIX = " (feat. mujin 無人)"

# ============================================================================
# WORD POOLS
# ============================================================================

# --- Japanese given names (split by gender for weighting) ---
JP_FEMALE_GIVEN = [
    "Mariya", "Taeko", "Junko", "Miki", "Meiko", "Momoko", "Minako",
    "Akiko", "Yumi", "Eri", "Keiko", "Reiko", "Tomoko", "Yoko", "Kumiko",
    "Noriko", "Sachiko", "Takako", "Mayumi", "Kaori", "Naoko", "Atsuko",
    "Hiroko", "Chisato", "Rumi", "Satoko", "Nanako", "Yukiko", "Sayuri",
    "Midori", "Kyoko", "Harumi", "Kazumi", "Miho", "Chieko", "Miyuki",
    "Rina", "Mai", "Yui", "Saki", "Nana", "Hana", "Moe", "Risa",
    "Ayumi", "Asami", "Shiori", "Misaki", "Kanako", "Manami", "Ami",
    "Aoi", "Hinata", "Sakura", "Koharu", "Riko", "Miku", "Yuna",
    "Haruka", "Aiko", "Nozomi", "Hikari", "Chihiro", "Madoka", "Saya",
]

JP_MALE_GIVEN = [
    "Tatsuro", "Toshiki", "Haruomi", "Hiroshi", "Masayoshi", "Akira",
    "Tetsuya", "Takeshi", "Ryuichi", "Shigeru", "Kazumasa", "Toshinobu",
    "Masahiko", "Yuji", "Kenichi", "Koichi", "Shinichi", "Tsuyoshi",
    "Hideki", "Masaharu", "Takao", "Kazuo", "Nobuo", "Kiyotaka",
    "Jun", "Ryo", "Makoto", "Kenji", "Sho", "Yusuke", "Daisuke",
    "Naoto", "Takuya", "Shun", "Ren", "Kaito", "Hayato", "Sota",
    "Haruki", "Yuto", "Minato", "Ryota", "Daiki", "Kenta", "Itsuki",
]

JP_FAMILY_NAMES = [
    "Yamashita", "Takeuchi", "Ohnuki", "Ohashi", "Matsubara", "Nakahara",
    "Kikuchi", "Yoshida", "Kadomatsu", "Kubota", "Hosono", "Sakamoto",
    "Takahashi", "Sato", "Suzuki", "Tanaka", "Watanabe", "Ito",
    "Yamamoto", "Nakamura", "Kobayashi", "Kato", "Shimizu", "Hayashi",
    "Inoue", "Kimura", "Matsumoto", "Ogawa", "Fujita", "Okada",
    "Mori", "Saito", "Yamaguchi", "Sasaki", "Morita", "Nishida",
    "Aoki", "Kaneko", "Endo", "Miura", "Hara", "Ueda", "Takagi",
    "Onoda", "Shibuya", "Tsuchiya", "Noguchi", "Hamada", "Otsuka",
    "Kawai", "Fujioka", "Kamiya", "Kitamura", "Nishimura", "Miyake",
    "Ishikawa", "Maeda", "Taguchi", "Sugiyama", "Tamura", "Kurosawa",
]

# --- Single stage name pools ---
JP_STAGE_NAMES_F = [
    "Anri", "Yukika", "Miki", "Junko", "Taeko", "Meiko", "Akina",
    "Seiko", "Momoe", "Miyuki", "Yumi", "Ami", "Risa", "Mao",
    "Rio", "Aya", "Nao", "Rui", "Mei", "Emi", "Rei", "Sei",
    "Sae", "Rin", "Ran", "Kou", "You", "Miu", "Rie", "Chie",
]

JP_STAGE_NAMES_M = [
    "Taro", "Ken", "Char", "Alan", "Tommy", "Jun", "Ryo", "Sho",
    "Ren", "Kai", "Jin", "Gen", "Shin", "Masa", "Hiro", "Yuu",
    "Taku", "Nao", "Kou", "Shu", "Mako", "Aki", "Tetsu", "Riku",
]

STAGE_CAPS = ["EPO", "AI", "UA", "MEG", "YUI"]

# --- Band name building blocks ---
BAND_COSMIC = [
    "Omega", "Casiopea", "Nova", "Orion", "Cosmos", "Galaxy", "Pulsar",
    "Nebula", "Aurora", "Stellar", "Quasar", "Solar", "Lunar", "Venus",
    "Mercury", "Pleiades", "Lyra", "Sirius", "Vega", "Polaris",
]

BAND_GROUP_NOUNS = [
    "Tribe", "Club", "Stars", "Orchestra", "Ensemble", "Band", "Crew",
    "Express", "Connection", "Machine", "System", "Project", "Unit",
    "Collective", "Network", "Alliance", "Society", "Association",
]

BAND_PLAYFUL_ADJ = [
    "Sugar", "Crystal", "Silk", "Velvet", "Golden", "Silver", "Neon",
    "Electric", "Sweet", "Cool", "Smooth", "Fresh", "Southern",
    "Northern", "Pacific", "Tropical", "Sunset", "Moonlight",
]

BAND_PLAYFUL_NOUNS = [
    "Babe", "Lounge", "Piper", "Rose", "Butter", "Peach", "Cherry",
    "Honey", "Mint", "Cream", "Dream", "Wave", "Breeze", "Light",
    "Groove", "Rhythm", "Soul", "Spirit", "Magic", "Spell", "Kiss",
]

BAND_TEMPLATES = [
    "{Cosmic} {Group}",
    "{Adj} {PNoun}",
    "{PNoun} & {PNoun2}",
    "{Adj} All {Group}",
    "{Cosmic}",
    "{Adj} {Group}",
    "The {Adj} {PNoun}",
]

# --- Modern revival producer names ---
REVIVAL_TIME = [
    "Night", "Midnight", "Dawn", "Sunset", "Twilight", "Evening",
    "Morning", "Afternoon", "Golden Hour", "Blue Hour", "Late Night",
]

REVIVAL_NOUNS = [
    "Tempo", "Groove", "Wave", "Dream", "Signal", "Station", "Frequency",
    "Channel", "Broadcast", "Transmission", "Pulse", "Drive", "Cruise",
    "Voyage", "Escape", "Fantasy", "Vision", "Memory", "Illusion",
]

REVIVAL_MODIFIER = [
    "Future", "Neo", "Retro", "New", "Digital", "Virtual", "Cyber",
    "Synth", "Analog", "Stereo", "Mono", "Hi-Fi", "Lo-Fi",
]

REVIVAL_NAMES = [
    "Girlfriend", "Boyfriend", "Lover", "Stranger", "Angel", "Star",
    "Princess", "Prince", "Queen", "King", "Lady", "Girl", "Boy",
]

REVIVAL_TEMPLATES = [
    "{Time} {Noun}",
    "{Mod} {Name}",
    "{Mod} {Noun}",
    "{Time} {Name}",
]

# --- Western stage names ---
WESTERN_SHORT = [
    "Cindy", "Sally", "Lyn", "Tommy", "Alan", "Char", "Holly", "Candy",
    "Sandy", "Jenny", "Bobby", "Danny", "Ricky", "Billy", "Johnny",
    "Freddy", "Teddy", "Wendy", "Mandy", "Nancy", "Terry", "Jerry",
    "Kenny", "Benny", "Donny", "Ronny", "Tammy", "Peggy", "Kitty",
]

# --- Hybrid/Stylized ---
HYBRID_YEARS = list(range(1978, 1990))

HYBRID_INITIALS = [
    "AB", "YM", "TK", "KS", "MN", "HT", "RK", "SY", "JN", "DM",
    "ST", "RM", "KN", "HM", "NK", "SM", "YK", "TM", "AK", "MS",
]

HYBRID_SUFFIXES = ["'s", "-Square", "-Wave", "-Sound", "-Beat", "-Tone"]


# ============================================================================
# GENERATOR
# ============================================================================

@dataclass
class CitypopArtistGenerator:
    seed: Optional[int] = None
    rng: random.Random = field(default_factory=random.Random, init=False)

    def __post_init__(self):
        self.rng = random.Random(self.seed) if self.seed is not None else random.Random()

    def _pick(self, lst): return self.rng.choice(lst)

    def gen_full_jp(self):
        if self.rng.random() < 0.60:
            given = self._pick(JP_FEMALE_GIVEN)
        else:
            given = self._pick(JP_MALE_GIVEN)
        family = self._pick(JP_FAMILY_NAMES)
        return f"{given} {family}", "full_jp"

    def gen_stage_jp(self):
        roll = self.rng.random()
        if roll < 0.10:
            return self._pick(STAGE_CAPS), "stage_jp/caps"
        elif roll < 0.55:
            return self._pick(JP_STAGE_NAMES_F), "stage_jp/female"
        else:
            return self._pick(JP_STAGE_NAMES_M), "stage_jp/male"

    def gen_band(self):
        t = self._pick(BAND_TEMPLATES); r = t
        if "{Cosmic}" in r: r = r.replace("{Cosmic}", self._pick(BAND_COSMIC), 1)
        if "{Group}" in r: r = r.replace("{Group}", self._pick(BAND_GROUP_NOUNS), 1)
        if "{Adj}" in r: r = r.replace("{Adj}", self._pick(BAND_PLAYFUL_ADJ), 1)
        if "{PNoun}" in r: r = r.replace("{PNoun}", self._pick(BAND_PLAYFUL_NOUNS), 1)
        if "{PNoun2}" in r: r = r.replace("{PNoun2}", self._pick(BAND_PLAYFUL_NOUNS), 1)
        return r, "band"

    def gen_revival(self):
        t = self._pick(REVIVAL_TEMPLATES); r = t
        if "{Time}" in r: r = r.replace("{Time}", self._pick(REVIVAL_TIME), 1)
        if "{Noun}" in r: r = r.replace("{Noun}", self._pick(REVIVAL_NOUNS), 1)
        if "{Mod}" in r: r = r.replace("{Mod}", self._pick(REVIVAL_MODIFIER), 1)
        if "{Name}" in r: r = r.replace("{Name}", self._pick(REVIVAL_NAMES), 1)
        return r, "revival"

    def gen_western(self):
        if self.rng.random() < 0.60:
            return self._pick(WESTERN_SHORT), "western/solo"
        else:
            return f"{self._pick(WESTERN_SHORT)} {self._pick(JP_FAMILY_NAMES)}", "western/hybrid"

    def gen_hybrid(self):
        roll = self.rng.random()
        if roll < 0.35:
            year = self._pick(HYBRID_YEARS)
            band, _ = self.gen_band()
            return f"{year} {band}", "hybrid/year_band"
        elif roll < 0.70:
            initials = self._pick(HYBRID_INITIALS)
            suffix = self._pick(HYBRID_SUFFIXES)
            return f"{initials}{suffix}", "hybrid/initials"
        else:
            initials = self._pick(HYBRID_INITIALS)
            return f"{initials}'s", "hybrid/possessive"

    def generate(self, count=1):
        STYLES = [("full_jp", 0.40), ("stage_jp", 0.15), ("band", 0.15),
                  ("revival", 0.15), ("western", 0.10), ("hybrid", 0.05)]
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
    """Generate city pop artist names.

    Returns:
        List of dicts, each with 'name' and 'style' keys.
        Every name is appended with " (feat. mujin 無人)".
    """
    gen = CitypopArtistGenerator(seed=seed)
    return gen.generate(count=count)
