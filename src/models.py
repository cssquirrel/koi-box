"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel


class TrackOut(BaseModel):
    id: int
    title: str
    artist: str
    album_id: int | None
    album_name: str | None = None
    album_cover_url: str | None = None
    genre_id: str
    filename: str
    duration: float | None
    waveform: list[float] | None = None
    status: str
    created_at: str | None
    played_at: str | None = None


class NowPlayingOut(BaseModel):
    track: TrackOut | None
    genre_id: str
    is_playing: bool
    position: float = 0.0
    queue_size: int = 0
    signal_status: str = "unknown"
    library_mode: bool = False


class GenreOut(BaseModel):
    id: str
    category: str = ""
    description: str
    prefix: str
    caption: str
    lyrics: str = ""
    dynamic_lyrics: bool = False
    genre_selector_color: str = ""
    oled_color: str = ""
    bpm_min: int
    bpm_max: int
    key_scale: str
    duration_min: int
    duration_max: int
    sort_order: int
    generator_type: str = "custom"


class GenreCreateRequest(BaseModel):
    id: str
    category: str
    prefix: str
    description: str = ""
    caption: str = ""
    lyrics: str = ""
    bpm_min: int = 80
    bpm_max: int = 120
    key_scale: str = "C Major"
    duration_min: int = 120
    duration_max: int = 180


class GenreUpdateRequest(BaseModel):
    description: str | None = None
    caption: str | None = None
    lyrics: str | None = None
    bpm_min: int | None = None
    bpm_max: int | None = None
    key_scale: str | None = None
    duration_min: int | None = None
    duration_max: int | None = None


# -- Categories --


class CategoryOut(BaseModel):
    id: str
    display_name: str = ""
    genre_selector_color: str = ""
    oled_color: str = ""
    album_cover_directory: str = ""
    generator: str = "custom"
    generator_profile: str = ""
    lyrics_engine: str = "none"


class CategoryCreateRequest(BaseModel):
    id: str
    display_name: str
    genre_selector_color: str = ""
    oled_color: str = ""
    album_cover_directory: str = ""
    generator: str = "custom"
    generator_profile: str = ""
    lyrics_engine: str = "none"


class CategoryUpdateRequest(BaseModel):
    display_name: str | None = None
    genre_selector_color: str | None = None
    oled_color: str | None = None
    album_cover_directory: str | None = None
    generator: str | None = None
    generator_profile: str | None = None
    lyrics_engine: str | None = None


class PlaylistOut(BaseModel):
    id: int
    name: str
    track_count: int = 0
    created_at: str | None


class AlbumOut(BaseModel):
    id: int
    name: str
    artist: str
    cover_url: str | None
    genre_id: str
    track_count: int
    is_open: bool


class SettingOut(BaseModel):
    key: str
    value: str


class GenreSwitchRequest(BaseModel):
    genre_id: str
    category: str | None = None


class TrackStatusRequest(BaseModel):
    status: str


class PlaylistCreateRequest(BaseModel):
    name: str


class PlaylistAddTrackRequest(BaseModel):
    track_id: int


class SettingUpdateRequest(BaseModel):
    value: str


class PresetSetRequest(BaseModel):
    genre_id: str


class WeatherLocationRequest(BaseModel):
    latitude: float
    longitude: float
    display_name: str
