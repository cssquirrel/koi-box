# Configuration Guide

This document explains how koi-box's config system works, how to add new categories and genres, and how to create generator profiles for fully data-driven music generation.

## Architecture Overview

YAML files in `config/` are the **source of truth**. The SQLite database is a runtime cache that is rebuilt from YAML on every app startup. This means:

- Edit a YAML file → restart the app → changes appear in the UI and affect generation
- Edit settings in the UI → changes are written back to YAML + applied to the DB immediately
- The database can be deleted and rebuilt from config at any time

## File Map

```
config/
  categories.yaml          # Category metadata (colors, generator type, lyrics engine)
  genre.yaml               # Genre variants grouped by category
  generation.yaml          # ACE-Step connection settings (API URL, output format, etc.)
  generators/
    profiles/              # Generic generator profile YAMLs (template-based name generation)
      dreamy-chill.yaml    # Example profile
    pools/                 # Word pool .txt files (one word per line)
      _shared/             # Pools usable by any category
      example/             # Example pools for reference
    prompts/               # Lyrics system prompt .txt files
      citypop_lyrics.txt   # City Pop Japanese lyrics prompt
```

## Categories — `config/categories.yaml`

Each category is a top-level music style (e.g. Lo-Fi, Synthwave, City Pop). Categories control:

- **Display properties**: colors used in the genre selector and OLED screen
- **Generator type**: how track/artist/album names are produced
- **Lyrics engine**: whether tracks get LLM-generated lyrics or are instrumental

### Structure

```yaml
categories:
  lofi:
    display_name: Lo-Fi
    genre_selector_color: "6B8F7A" # hex color for the tuner band buttons
    oled_color: "4EDB8A" # hex color for the OLED now-playing screen
    album_cover_directory: lofi # subdirectory under album_covers/
    generator: custom # "custom" or "profile"
    lyrics_engine: none # "none" or "llm"

  citypop:
    display_name: City Pop
    genre_selector_color: "C47832"
    oled_color: "ff5b1a"
    album_cover_directory: citypop
    generator: custom
    lyrics_engine: llm
    lyrics_config: # only needed when lyrics_engine: llm
      system_prompt_file: citypop_lyrics.txt
      language: japanese # "japanese" or "any"
      morae_min: 4
      morae_max: 14
      max_chars: 25
      placeholder_lyrics: # fallback lines for unfilled slots
        - ああ夜が来る
        - 風が呼んでる
```

### Field Reference

| Field                   | Required | Description                                                         |
| ----------------------- | -------- | ------------------------------------------------------------------- |
| `display_name`          | Yes      | Human-readable name shown in the UI                                 |
| `genre_selector_color`  | No       | Hex color (no `#`) for genre selector buttons                       |
| `oled_color`            | No       | Hex color (no `#`) for the OLED player screen accent                |
| `album_cover_directory` | No       | Folder name under `album_covers/` for random cover images           |
| `generator`             | No       | `"custom"` (Python generators) or `"profile"` (generic YAML-driven) |
| `generator_profile`     | No       | Profile name (without `.yaml`) when `generator: profile`            |
| `lyrics_engine`         | No       | `"none"` (instrumental) or `"llm"` (LLM-generated lyrics)           |
| `lyrics_config`         | No       | Sub-object with lyrics engine settings (see above)                  |

## Genres — `config/genre.yaml`

Each genre is a specific music variant within a category (e.g. "rainy-day" under lofi). Genres define the ACE-Step generation parameters.

### Structure

```yaml
genres:
  lofi:
    variants:
      rainy-day:
        prefix: rainy
        description: Rainy day lo-fi with gentle piano and rain sounds
        caption: |
          lo-fi hip hop, mellow piano, rain sounds,
          soft vinyl crackle, cozy atmosphere
        lyrics: ""
        dynamic_lyrics: false
        bpm_min: 70
        bpm_max: 90
        key_scale: D Minor
        duration_min: 120
        duration_max: 180
        theme_seeds: []
        lyrics_guidance: ""

  citypop:
    variants:
      citypop-groove:
        prefix: cpop
        description: Classic city pop with funky bass and brass
        caption: |
          city pop, funky bass, brass section,
          80s japanese pop, upbeat groove
        lyrics: |
          [verse 1]
          {LYRICS_VERSE_1_LINE_1}
          {LYRICS_VERSE_1_LINE_2}
          ...
        dynamic_lyrics: true
        bpm_min: 110
        bpm_max: 130
        key_scale: G Major
        duration_min: 180
        duration_max: 240
        theme_seeds:
          - 夜の街角で
          - ネオンの下を
        lyrics_guidance: |
          Focus on nightlife imagery — neon, rain on asphalt,
          driving through the city at night.
```

### Field Reference

| Field                           | Required | Description                                                   |
| ------------------------------- | -------- | ------------------------------------------------------------- |
| `prefix`                        | Yes      | Short prefix for generated filenames (e.g. `rainy`, `cpop`)   |
| `description`                   | Yes      | Human-readable description shown in settings                  |
| `caption`                       | Yes      | ACE-Step style tags — multi-line, comma-separated descriptors |
| `lyrics`                        | No       | Lyrics template with `{LYRICS_*}` placeholders for LLM fill   |
| `dynamic_lyrics`                | No       | `true` to enable LLM lyrics generation for this variant       |
| `bpm_min` / `bpm_max`           | Yes      | BPM range for generation                                      |
| `key_scale`                     | Yes      | Musical key (e.g. `"C Major"`, `"D Minor"`)                   |
| `duration_min` / `duration_max` | Yes      | Track duration range in seconds                               |
| `theme_seeds`                   | No       | List of opening lines for lyrics thematic consistency         |
| `lyrics_guidance`               | No       | Additional creative direction appended to the LLM prompt      |

### Lyrics Template Placeholders

Templates use `{PLACEHOLDER}` syntax:

- `{THEME_SEED}` — filled with a random entry from `theme_seeds` (or a placeholder lyric)
- `{LYRICS_VERSE_1_LINE_1}` through `{LYRICS_VERSE_1_LINE_4}` — verse lines
- `{LYRICS_CHORUS_LINE_1}` through `{LYRICS_CHORUS_LINE_4}` — chorus lines
- `{LYRICS_BRIDGE_LINE_1}` etc. — bridge lines

The LLM is given the slot names and asked to generate appropriate content for each.

## Generator Profiles

For new categories that don't have custom Python generators, you can use the **profile-based generic generator**. This generates track names, artist names, and album names by filling random templates from word pools.

### Creating a Profile

Create a YAML file in `config/generators/profiles/`:

```yaml
# config/generators/profiles/dreamy-chill.yaml

track_names:
  templates:
    - "{adj} {noun}"
    - "{noun} {noun}"
    - "{adj} {noun} {suffix}"
    - "{time} {noun}"
  pools:
    adj: adjectives.txt
    noun: nouns.txt
    suffix: suffixes.txt
    time: time_of_day.txt

artist_names:
  templates:
    - "{prefix}{suffix}"
    - "{word} {word2}"
    - "{solo}"
  feat_chance: 0.15 # 15% chance of adding a "feat. X" collaborator
  feat_templates:
    - "{solo}"
  pools:
    prefix: artist_prefixes.txt
    suffix: artist_suffixes.txt
    word: artist_words.txt
    word2: artist_words.txt
    solo: artist_solo.txt

album_names:
  templates:
    - "{adj} {noun}"
    - "{noun} {suffix}"
  pools:
    adj: adjectives.txt
    noun: album_nouns.txt
    suffix: album_suffixes.txt
```

### How Templates Work

Each template is a string with `{slot}` placeholders. When generating a name:

1. A random template is picked
2. Each `{slot}` is replaced with a random line from the corresponding pool file
3. The result is title-cased

### Connecting a Profile to a Category

In `categories.yaml`:

```yaml
categories:
  ambient:
    display_name: Ambient
    generator: profile
    generator_profile: dreamy-chill
    # ...
```

## Word Pools

Pool files are plain `.txt` files with one word/phrase per line. They live in `config/generators/pools/`.

### Directory Resolution

When a profile references `adjectives.txt`, the system looks for:

1. `pools/{category}/adjectives.txt` (category-specific)
2. `pools/_shared/adjectives.txt` (shared fallback)

This lets you have category-specific word pools that override shared defaults.

### Creating Pools

```
config/generators/pools/
  _shared/
    colors.txt           # "amber", "crimson", "azure", ...
    emotions.txt         # "longing", "bliss", "melancholy", ...
    time_of_day.txt      # "midnight", "dawn", "dusk", ...
  ambient/
    adjectives.txt       # "ethereal", "floating", "glacial", ...
    nouns.txt            # "echoes", "currents", "whispers", ...
```

## Lyrics Prompts

For categories with `lyrics_engine: llm`, you need a system prompt file in `config/generators/prompts/`.

The prompt should instruct the LLM on:

- Language and style
- Line length constraints
- Output format (must use `LYRICS_SLOT_NAME: text` format)

See `config/generators/prompts/citypop_lyrics.txt` for a working example.

### Lyrics Config Reference

```yaml
lyrics_config:
  system_prompt_file: my_prompt.txt # file in config/generators/prompts/
  language: japanese # "japanese" (morae validation) or "any" (length only)
  morae_min: 4 # minimum morae per line (japanese only)
  morae_max: 14 # maximum morae per line (japanese only)
  max_chars: 25 # maximum characters per line
  placeholder_lyrics: # fallback lines for unfilled LLM slots
    - "fallback line one"
    - "fallback line two"
```

## Generation Settings — `config/generation.yaml`

Controls the ACE-Step connection and output parameters. These are seeded into the DB on first run and editable in the Settings panel.

```yaml
api_url: "http://127.0.0.1:8001"
api_key: ""
buffer_max: 5
delete_disliked_tracks: true
preservation_time: 24
file_size_limit_mb: 500
lm:
  thinking: true
  use_cot_caption: true
  use_cot_language: true
  constrained_decoding: true
  lm_cfg_scale: 2.0
output:
  use_format: true
  inference_steps: 8
  audio_format: mp3
```

## How-To: Add a New Category

1. **Add category metadata** to `config/categories.yaml`:

   ```yaml
   categories:
     ambient:
       display_name: Ambient
       genre_selector_color: "5B7FA5"
       oled_color: "4DA6FF"
       album_cover_directory: ambient
       generator: profile
       generator_profile: dreamy-chill
       lyrics_engine: none
   ```

2. **Add an empty variants section** to `config/genre.yaml`:

   ```yaml
   genres:
     ambient:
       variants: {}
   ```

3. **Create album cover directory** (optional):

   ```
   album_covers/ambient/
     ambient-001.jpg
     ambient-002.jpg
   ```

4. **Create word pools** (if using `generator: profile`):

   ```
   config/generators/pools/ambient/
     adjectives.txt
     nouns.txt
     ...
   ```

5. **Create a generator profile** (if using `generator: profile`):

   ```
   config/generators/profiles/dreamy-chill.yaml
   ```

6. **Restart the app** — the new category appears in the Settings panel and the category switch bar.

Alternatively, you can create a category directly from the Settings panel using the "+ NEW CATEGORY" button.

## How-To: Add a New Genre Variant

1. **Add the variant** under its category in `config/genre.yaml`:

   ```yaml
   genres:
     lofi:
       variants:
         coffee-shop:
           prefix: coffee
           description: Warm coffee shop vibes with acoustic guitar
           caption: |
             lo-fi, acoustic guitar, warm ambience,
             coffee shop sounds, gentle percussion
           bpm_min: 75
           bpm_max: 95
           key_scale: G Major
           duration_min: 120
           duration_max: 180
   ```

2. **Restart the app** — the new variant appears in the tuner bar under its category.

You can also create genres from the Settings panel using the "+ NEW GENRE" button (requires selecting a category).

## How-To: Add Lyrics to a Category

1. **Write a system prompt** file in `config/generators/prompts/`:

   ```
   config/generators/prompts/my_lyrics.txt
   ```

   The prompt must instruct the LLM to output lines in this exact format:

   ```
   LYRICS_SLOT_NAME: (text here)
   ```

2. **Set lyrics_engine** in the category config:

   ```yaml
   categories:
     mycategory:
       lyrics_engine: llm
       lyrics_config:
         system_prompt_file: my_lyrics.txt
         language: any
         max_chars: 40
         placeholder_lyrics:
           - "placeholder line"
   ```

3. **Add lyrics templates** to the genre variants that should use dynamic lyrics:
   ```yaml
   variants:
     my-variant:
       dynamic_lyrics: true
       lyrics: |
         [verse]
         {LYRICS_VERSE_1_LINE_1}
         {LYRICS_VERSE_1_LINE_2}
         [chorus]
         {LYRICS_CHORUS_LINE_1}
         {LYRICS_CHORUS_LINE_2}
   ```

## Backend File Reference

| File                                      | Purpose                                                        |
| ----------------------------------------- | -------------------------------------------------------------- |
| `src/config.py`                           | Loads/saves YAML configs, path constants, pool/profile loading |
| `src/database.py`                         | SQLite schema, migration, seeding from YAML on startup         |
| `src/models.py`                           | Pydantic request/response models for the API                   |
| `src/routes/categories.py`                | Category CRUD API endpoints                                    |
| `src/routes/radio.py`                     | Genre CRUD, radio state, queue, presets                        |
| `src/services/buffer.py`                  | Background worker that generates tracks, dispatches generators |
| `src/services/lyrics.py`                  | LLM lyrics generation with configurable prompts and validation |
| `src/services/albums.py`                  | Album assignment and name generation                           |
| `src/generators/generic.py`               | Template-based generic name generator engine                   |
| `src/generators/track_names.py`           | Custom Lo-Fi track name generator                              |
| `src/generators/artist_names.py`          | Custom Lo-Fi artist name generator                             |
| `src/generators/synthwave_track_names.py` | Custom Synthwave track name generator                          |
| `src/generators/citypop_track_names.py`   | Custom City Pop track name generator                           |

## Frontend File Reference

| File                        | Purpose                                                    |
| --------------------------- | ---------------------------------------------------------- |
| `src/static/js/api.js`      | Fetch wrapper for all backend API endpoints                |
| `src/static/js/settings.js` | Settings panel rendering, categories/genres UI, save logic |
| `src/static/js/band.js`     | Category switch bar and variant tuner band                 |
| `src/static/js/radio.js`    | Radio state management and polling                         |
| `src/static/js/audio.js`    | Audio playback and crossfade                               |
| `src/static/js/screen.js`   | OLED player screen rendering                               |
| `src/static/css/styles.css` | All application styles                                     |
