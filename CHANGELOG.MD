# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.0] - 2026-03-14

### Added

- **Auto-update system**: The app now checks GitHub for new releases on startup (with a 6-hour cooldown to avoid redundant requests). If an update is available, a pulsing UPDATE badge appears in the bottom toolbar. Clicking it opens a modal showing the new version and release notes. Users can install the update with one click (`git pull`), then restart to apply. Pre-flight checks warn if git is unavailable or local files have been modified.
- **What's New modal**: After restarting with a new version, a one-time "What's New" panel displays the release notes from the update that was just installed.
- **Version detection from changelog**: The app reads its own version by parsing the first `## [X.Y.Z]` header from `CHANGELOG.MD` — no separate version file to maintain.

### Fixed

- **Non-City Pop lyrics generation failing silently**: The lyrics user prompt was hardcoded to say "Generate Japanese City Pop lyrics" and "3-7 Japanese characters" for all categories, contradicting the system prompt for non-Japanese categories. This caused the 3B LLM to produce garbled output in some circumstances, fail all retries, and fall back to instrumental with no lyrics. The user prompt is now language-neutral — the system prompt handles language and style specificity.
- **Missing section hints for rap-heavy genres**: `_SECTION_HINTS` only covered VERSE, CHORUS, PRECHORUS, and BRIDGE. Added RAP, RAP2, RAP3, and BREAKDOWN so genres with them get creative direction hints in the LLM prompt.

### Changed

- **Configuration docs updated**: `docs/configuration.md` now covers user sidecar files, the `packs/` generator directory, `bio_config` field, pool resolution order (core → packs → shared), ACE-Step autostart settings, and pack developer guidance.

## [1.6.0] - 2026-03-11

### Added

- **ACE-Step auto-start**: Optional setting to launch the ACE-Step 1.5 REST API server automatically at app startup. Requires path to the ACE-Step repo. Configurable via a toggle and path input in Settings under a new "ACE-Step Server" section.
- **ACE-Step process management**: `src/services/ace_step_process.py` manages the subprocess lifecycle — port collision detection, Windows process-tree kill via `taskkill /F /T`, graceful shutdown on app close.

### Changed

- **Pack deletion preserves favorites**: Uninstalling a genre pack no longer blocks on existing favorited tracks. Non-favorited tracks are deleted; favorited tracks and their albums are retained. Genres with surviving favorites are archived (invisible to radio and generation) rather than deleted outright.
- **Album covers reassigned on pack removal**: Albums retaining favorited tracks after pack uninstall have their cover image reassigned to a random core-genre image before pack files are deleted, preventing broken cover paths.
- **Pack generator files isolated**: Pack-installed generator files (pools, profiles, prompts) now write to `config/generators/packs/` instead of the shared core generator directories. Loaders check the core directories first, then fall back to `packs/`.
- **Pack YAML configs isolated**: Pack category and genre entries are merged into gitignored `config/categories.user.yaml` and `config/genre.user.yaml` sidecars rather than the tracked `categories.yaml` and `genre.yaml`. Both files are merged at load time.
- **Pack modal language**: Delete confirmation updated to reflect that favorites are preserved. Browse and install modals use correct button labels (CLOSE, INSTALL, REMOVE).

### Fixed

- **ACE-Step not killed on app close**: Moved process start/stop to wrap `webview.start()` in `main()`, the reliable blocking boundary. Previous `atexit`-based approach was bypassed by pywebview's `os._exit()` call.
- **New settings not seeded on existing databases**: `ace_step_autostart` and `ace_step_path` settings are now inserted via `INSERT OR IGNORE` on startup so existing installs receive the new defaults.

### Migration notes

- On first startup, `migrate_generator_files()` automatically moves any pack generator files from the old flat locations into `config/generators/packs/` and updates `installed_packs.json`.
- Pack entries in `categories.yaml` and `genre.yaml` are automatically extracted to `categories.user.yaml` and `genre.user.yaml` on first startup.
- `config/generators/packs/`, `config/categories.user.yaml`, `config/genre.user.yaml`, `config/installed_packs.json`, `config/autopilot_weights.json`, and `album_covers/` subdirectories outside the three core genres are now gitignored.

## [1.5.0] - 2026-03-10

### Added

- **Genre pack system**: Browse, install, and delete genre packs from a GitHub-hosted index or custom URL. Packs include categories, generator profiles, word pools, album covers, and prompt files.
- **Pack management API**: New `/packs` routes for listing available packs, installing from URL, and removing installed packs.
- **Pack settings UI**: Animated install progress indicator in the Settings screen with a restart prompt on completion.
- **Autopilot weight generation on install**: Qwen LLM generates autopilot weights for newly installed genre categories during pack installation.
- **Core category protection**: Built-in categories (lofi, citypop, synthwave) are protected from deletion via the pack removal flow.

## [1.2.0] - 2026-03-10

### Added

- **Buffer status endpoint**: `GET /radio/buffer-status` exposes per-genre buffer fill counts for autopilot readiness checks.
- **Autopilot readiness constraint**: Genre switching now skips genres with empty buffers to prevent stalls during autopilot transitions.
- **Category display names**: Categories support a `display_name` field rendered on genre buttons (e.g., config name `kalt` displays as `K-ALT`).
- **Shared LLM lock**: `llm_lock` module provides a shared `threading.Lock` for Qwen model access, preventing concurrent bio and lyrics generation from colliding.
- **`favorited_at` column**: Tracks table gains a `favorited_at` timestamp with migration and backfill for correct favorites sort ordering.

### Changed

- **Buffer worker priority order**: Prebuffer urgent and normal fills are now promoted above current-genre normal refill to prevent autopilot stalls on genre switch.
- **Bio generation trigger**: Bio generation now fires on the first favorite action (background thread) with a fallback on artist page visit. `get_artist_bio` simplified to a read-only lookup.

## [1.1.0] - 2026-03-04

### Added

- **Favorite artist pool**: Favoriting a track builds a persistent artist pool per genre variant. Liked artists have a 40% chance to reappear in future generated tracks, weighted by like count.
- **Album ownership**: Favoriting a track claims its album for that artist. Other artists' unfavorited tracks are reassigned to open albums. Album assignment respects ownership boundaries.
- **Artist bios**: On-demand bio generation using Qwen 2.5-3B when opening a favorited artist's page. Configurable per category via system prompt files. Gated behind `artist_bios_enabled` setting.
- **Artist profile page**: Full profile view with bio, albums grid, playlists grid, stats, and track listing. Accessible by clicking any artist name in radio or player.
- **Artist bios setting**: Toggle in settings under a new "Artists" section to enable/disable LLM bio generation.
- **Category bio prompts**: Genre-specific system prompts for City Pop, Lo-Fi, and Synthwave bio generation.
- **Player transport thumbs**: Favorite/dislike buttons in the player transport bar. Locked with tooltip when a track belongs to a playlist.
- **Heart icons on artist/album pages**: Visual indicator for saved vs ephemeral tracks with click-to-toggle favoriting.
- **Ephemeral track dimming**: Unfavorited tracks on artist/album pages display at reduced opacity to signal they are temporary.
- **Auto-favorite on playlist add**: Adding a track to any playlist automatically favorites it and triggers artist pool and album ownership updates.
- **`in_playlist` track field**: Track data now includes whether the track belongs to any playlist, used to lock status controls.
- **Clickable album art**: Album cover in the player OLED screen navigates to the album page.
- **Tracklist summary label**: Section header now shows track count and total duration instead of static "TRACKLIST" text.
- **Album track count startup audit**: Corrects any count drift in the albums table on every application start.

### Changed

- **Buffer priority order**: Reordered genre fill priority to prevent radio stalls — urgent current genre first, then urgent prebuffer, then normal refill, then background fill.
- **Bio prompts**: Updated to prevent name-dropping real artists/films and to ensure bios start with self-contained sentences. Post-processing strips artist name fragments from LLM output.
- **Player layout**: Transport controls pushed to bottom of player view with scrollable tracklist filling available space.
- **Contextual column hiding**: Artist column hidden on artist pages, album column hidden on album pages — title column expands into freed space.

### Removed

- `scripts/generate_icon.py` and `server.cmd` (stale files).

### Fixed

- **Album track count on cleanup**: Track deletion now correctly decrements the parent album's track count.
- **Tooltip on locked buttons**: Removed `pointer-events: none` that prevented hover tooltips from appearing on locked transport buttons.
- **Rounded corner issue**: Fixed border radius at edge of main container.
- **Player scrolling**: Added `min-height: 0` at multiple flex chain levels to restore scrolling in player view.

## Unreleased

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security
