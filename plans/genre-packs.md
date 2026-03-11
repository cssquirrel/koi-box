# Genre Packs Feature

## Overview
Allow users to install/delete genre packs from a GitHub repository or custom URL.
Autopilot weights are auto-generated via Qwen at install time.

## Pack Source
- Default repo: `cssquirrel/koi-box-genre-packs` on GitHub
- `index.json` at repo root lists available packs
- Packs live as directories: `packs/[user]/[pack-name]/`
- Download via repo zipball, extract specific pack directory

## Pack Structure
```
pack-name/
  pack.manifest          # JSON: id, name, description, version, author, category_id, variants
  album_covers/{dir}/    # Cover images
  config/
    category_info.yaml   # Merges into categories.yaml
    genre_info.yaml      # Merges into genre.yaml
    generators/
      pools/{cat}/       # Word pool .txt files
      profiles/          # Generator profile .yaml
      prompts/           # LLM prompt .txt files
```

## Install Flow
1. Download repo zipball (or custom URL zip)
2. Extract to temp dir, locate pack.manifest
3. Validate: category_id not already installed
4. Copy album_covers, generator pools/profiles/prompts
5. Merge category_info.yaml into categories.yaml
6. Merge genre_info.yaml into genre.yaml
7. Record in config/installed_packs.json
8. Reseed genres DB
9. Generate autopilot weights via Qwen (fallback: neutral 5s)
10. Clean up temp dir

## Delete Flow
1. Reject core categories (lofi, citypop, synthwave)
2. Check for existing tracks/albums (block if present)
3. Look up installed_packs.json for file manifest
4. Remove: pools dir, profile yaml, prompt files, album covers dir
5. Remove from categories.yaml and genre.yaml
6. Remove autopilot weights
7. Remove from installed_packs.json
8. Reseed DB

## Autopilot Weight Generation
- At install: feed each variant description to Qwen
- Output: time-of-day (0-10) and weather-mood (0-10) scores
- Stored in config/autopilot_weights.json
- Autopilot.js fetches via GET /autopilot/weights
- Merges with hardcoded weights; unknown genres get neutral 5

## Files
- NEW: src/services/packs.py
- NEW: src/routes/packs.py
- MOD: src/config.py (YAML merge helpers)
- MOD: src/models.py (pack models)
- MOD: src/app.py (register router)
- MOD: src/routes/categories.py (pack cleanup on delete)
- MOD: src/static/js/api.js (pack + weights wrappers)
- MOD: src/static/js/autopilot.js (dynamic weight loading)
- MOD: src/static/js/settings.js (Genre Packs UI)
