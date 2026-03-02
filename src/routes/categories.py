"""Category CRUD endpoints — manages categories.yaml as the source of truth."""

from fastapi import APIRouter, HTTPException

from src.config import (
    add_category_to_yaml,
    load_categories_config,
    remove_category_from_yaml,
    update_category_in_yaml,
)
from src.database import get_db
from src.models import CategoryCreateRequest, CategoryOut, CategoryUpdateRequest

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories():
    """Return all categories from categories.yaml."""
    cats = load_categories_config()
    return [
        CategoryOut(
            id=cat_id,
            display_name=data.get("display_name", cat_id),
            genre_selector_color=data.get("genre_selector_color", ""),
            oled_color=data.get("oled_color", ""),
            album_cover_directory=data.get("album_cover_directory", ""),
            generator=data.get("generator", "custom"),
            generator_profile=data.get("generator_profile", ""),
            lyrics_engine=data.get("lyrics_engine", "none"),
        )
        for cat_id, data in cats.items()
    ]


@router.post("/categories")
def create_category(req: CategoryCreateRequest):
    """Create a new category — writes to categories.yaml and genre.yaml."""
    cats = load_categories_config()
    if req.id in cats:
        raise HTTPException(status_code=409, detail="Category already exists")

    cat_data = {
        "display_name": req.display_name,
        "genre_selector_color": req.genre_selector_color,
        "oled_color": req.oled_color,
        "album_cover_directory": req.album_cover_directory,
        "generator": req.generator,
        "lyrics_engine": req.lyrics_engine,
    }
    if req.generator_profile:
        cat_data["generator_profile"] = req.generator_profile

    add_category_to_yaml(req.id, cat_data)

    # Reseed DB to pick up changes
    from src.database import _reseed_genres
    _reseed_genres(get_db())

    return {"ok": True, "category_id": req.id}


@router.put("/categories/{category_id}")
def update_category(category_id: str, req: CategoryUpdateRequest):
    """Update a category's metadata — writes to categories.yaml and reseeds DB."""
    cats = load_categories_config()
    if category_id not in cats:
        raise HTTPException(status_code=404, detail="Category not found")

    fields = {}
    for field in ("display_name", "genre_selector_color", "oled_color",
                  "album_cover_directory", "generator", "generator_profile",
                  "lyrics_engine"):
        val = getattr(req, field)
        if val is not None:
            fields[field] = val

    if not fields:
        return {"ok": False, "error": "No fields to update"}

    update_category_in_yaml(category_id, fields)

    # Reseed DB so genres pick up new category metadata (colors, etc.)
    from src.database import _reseed_genres
    _reseed_genres(get_db())

    return {"ok": True, "category_id": category_id}


@router.delete("/categories/{category_id}")
def delete_category(category_id: str):
    """Delete a category — only if no tracks or albums reference its genres."""
    cats = load_categories_config()
    if category_id not in cats:
        raise HTTPException(status_code=404, detail="Category not found")

    # Check for tracks/albums referencing any genre in this category
    db = get_db()
    genres = db.execute(
        "SELECT id FROM genres WHERE category = ?", (category_id,)
    ).fetchall()

    for genre_row in genres:
        gid = genre_row["id"]
        tracks = db.execute(
            "SELECT COUNT(*) FROM tracks WHERE genre_id = ?", (gid,)
        ).fetchone()[0]
        albums = db.execute(
            "SELECT COUNT(*) FROM albums WHERE genre_id = ?", (gid,)
        ).fetchone()[0]
        if tracks > 0 or albums > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete: genre '{gid}' still has {tracks} tracks and {albums} albums",
            )

    # Remove genres from DB
    for genre_row in genres:
        db.execute("DELETE FROM genres WHERE id = ?", (genre_row["id"],))
        db.execute("DELETE FROM presets WHERE genre_id = ?", (genre_row["id"],))
    db.commit()

    # Remove from YAML files
    remove_category_from_yaml(category_id)

    return {"ok": True}
