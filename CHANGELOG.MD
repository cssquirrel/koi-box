# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
